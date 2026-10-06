"""Run machinery: window gating, after-tax checkpoints, benchmark, CPU slots.

THE CHECKPOINT TRICK
--------------------
A site backtest from S to E clips the data at E and reports the after-tax value
"as if everything were sold on E" (Backtest.run's terminal tax). Because no
strategy can see the future, the portfolio state on E is the same whether or not
the run continues past E. So ONE engine run started at S can report the exact
after-tax liquidation value at every later date: at the end of each checkpoint
day we recompute the engine's terminal tax (final partial year's realized gains
plus the tax on all unrealized gains, with the loss carryforward) from the
portfolio's own lots. That turns "every window length from every start date"
into one run per start date. verify_checkpoints() proves the equivalence
against independent clipped runs.

Windows are gated like the site's WarmUpGate: the strategy sees all history
before S (warm signals) but cannot trade until S.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from backtester import Backtest, Strategy, TaxPolicy
from backtester.tax import compute_year_tax

from . import data

LAB = Path(__file__).resolve().parent
CACHE_DIR = LAB / "cache"
SLOT_DIR = LAB / ".slots"

CASH = 100_000.0
COMMISSION = 0.0005   # site default: 5 bps per side
SLIPPAGE = 0.0005     # site default: 5 bps per side

# Tax regimes. CA = California single filer ~$300k (the site's "Beat the S&P
# (CA)" preset): short 35% fed + 3.8% NIIT + 9.3% CA, long 15% + 3.8% + 9.3%.
# FED = the site's default rates. NONE = a tax-deferred account (IRA/401k).
REGIMES: dict[str, tuple[float, float] | None] = {
    "CA": (0.481, 0.281),
    "FED": (0.35, 0.15),
    "NONE": None,
}


def policy_for(regime: str) -> TaxPolicy | None:
    r = REGIMES[regime]
    return None if r is None else TaxPolicy(short_term_rate=r[0], long_term_rate=r[1])


# --------------------------------------------------------------------------
# Protocols: which start dates and checkpoints a config is evaluated on.
# --------------------------------------------------------------------------
def _quarter_starts(a: str, b: str) -> list[pd.Timestamp]:
    return list(pd.date_range(a, b, freq="QS"))


@dataclass(frozen=True)
class Protocol:
    name: str
    starts: tuple            # window start dates (calendar dates)
    checkpoints: tuple       # window end dates (calendar dates)
    benchmark: str = "SPY"
    data_end: str = data.DATA_END
    lengths: tuple = (3, 5, 10, 15, 20)

    @property
    def first_start(self) -> pd.Timestamp:
        return self.starts[0]


def _mk(name, start_a, start_b, ck_a, benchmark="SPY", step="QS"):
    starts = tuple(pd.date_range(start_a, start_b, freq=step))
    cks = tuple(pd.date_range(ck_a, data.DATA_END, freq="QS"))
    return Protocol(name, starts, cks, benchmark)


PROTOCOLS: dict[str, Protocol] = {
    # Full protocol: quarterly starts 2000-01 .. 2023-07, quarterly checkpoints.
    "full": _mk("full", "2000-01-01", "2023-07-01", "2000-04-01"),
    # Screening protocol: yearly starts (Jan 1) 2000 .. 2023, same checkpoints.
    "screen": _mk("screen", "2000-01-01", "2023-01-01", "2000-04-01", step="YS"),
    # Long-history protocol on mutual-fund proxies (benchmark VFINX, the S&P
    # 500 index fund): quarterly starts 1986-01 .. 2023-07. Starts in 1986
    # because most 1980s fund series only become genuinely daily in late 1985
    # (earlier values are stale month-end prints).
    "long": _mk("long", "1986-01-01", "2023-07-01", "1986-04-01", benchmark="VFINX"),
    "long_screen": _mk("long_screen", "1986-01-01", "2023-01-01", "1986-04-01",
                       benchmark="VFINX", step="YS"),
}


# --------------------------------------------------------------------------
# After-tax liquidation value of the engine's current state.
# --------------------------------------------------------------------------
def liquidation_value(engine, policy: TaxPolicy | None) -> tuple[float, float]:
    """(after-tax liquidation value, pre-liquidation equity) right now.

    Mirrors Backtest.run's terminal tax exactly: settle the current year's
    realized gains against the loss carryforward, then tax all unrealized gains
    (short vs long by each lot's age) against what is left of it.
    """
    pf = engine.portfolio
    prices = engine.current_prices()
    equity = pf.cash + pf.holdings_value(prices)
    if policy is None:
        return equity, equity
    year = engine._date.year
    carry = 0.0
    for y in sorted(k for k in pf.realized if k < year):
        r = pf.realized[y]
        _, carry = compute_year_tax(r["st"], r["lt"], carry, policy)
    r = pf.realized.get(year, {"st": 0.0, "lt": 0.0})
    fy_tax, carry2 = compute_year_tax(r["st"], r["lt"], carry, policy)
    st_u, lt_u = pf.unrealized_gains(engine._date, prices, policy)
    unreal_tax, _ = compute_year_tax(st_u, lt_u, carry2, policy)
    return equity - fy_tax - unreal_tax, equity


class Gate(Strategy):
    """Hold cash until `start`, then run `inner`; record checkpoint values.

    `checkpoints` are calendar dates E; each maps to the last trading day <= E
    (what a site run with end=E would end on). Month-end liquidation values are
    recorded too when `monthly` is set (used for bootstrap / PBO statistics).
    """

    def __init__(self, inner: Strategy, start, checkpoints, policy, monthly: bool = False):
        self.inner = inner
        self.start = pd.Timestamp(start)
        self.checkpoints = list(checkpoints)
        self.policy = policy
        self.monthly = monthly

    def initialize(self, ctx) -> None:
        eng = ctx._engine
        cal = eng.market.calendar
        i0 = int(cal.searchsorted(self.start, side="left"))
        self.t0 = cal[i0] if i0 < len(cal) else None
        self._ck: dict = {}
        for e in self.checkpoints:
            j = int(cal.searchsorted(pd.Timestamp(e), side="right")) - 1
            if j >= i0 and pd.Timestamp(e) > self.start:
                self._ck.setdefault(cal[j], []).append(pd.Timestamp(e))
        self._month_end: set = set()
        if self.monthly and i0 < len(cal):
            c = cal[i0:]
            m = c.to_period("M")
            last = np.r_[m[1:] != m[:-1], True]
            self._month_end = set(c[last])
        self.values: dict = {}     # E -> (liq, equity, trading_day)
        self.months: dict = {}     # trading_day -> (liq, equity)
        self.inner.initialize(ctx)

    def on_day(self, ctx) -> None:
        d = ctx.date
        if d < self.start:
            return
        self.inner.on_day(ctx)
        labels = self._ck.get(d)
        is_me = d in self._month_end
        if labels or is_me:
            liq, eq = liquidation_value(ctx._engine, self.policy)
            if labels:
                for e in labels:
                    self.values[e] = (liq, eq, d)
            if is_me:
                self.months[d] = (liq, eq)


class BuyHoldOne(Strategy):
    """Put all cash into one ticker on the first day it trades; never trade again.
    Equivalent to the site's SPY benchmark (BuyAndHold on a SPY-only market)."""

    def __init__(self, ticker: str = "SPY"):
        self.ticker = ticker

    def initialize(self, ctx) -> None:
        self.done = False

    def on_day(self, ctx) -> None:
        if not self.done and ctx.price(self.ticker) is not None:
            ctx.order_target_percent(self.ticker, 1.0)
            self.done = True


# --------------------------------------------------------------------------
# Global CPU slots: many agents may run sweeps at once; at most N backtest
# tasks execute concurrently machine-wide. Heavy (whole stock universe) tasks
# also take one of a smaller pool of memory slots.
# --------------------------------------------------------------------------
N_SLOTS = int(os.environ.get("LAB_SLOTS", "12"))
N_HEAVY = int(os.environ.get("LAB_HEAVY_SLOTS", "4"))


@contextmanager
def _flock_slot(prefix: str, n: int):
    SLOT_DIR.mkdir(exist_ok=True)
    fds = []
    try:
        while True:
            for i in range(n):
                fd = os.open(SLOT_DIR / f"{prefix}{i}", os.O_CREAT | os.O_RDWR)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fds.append(fd)
                    break
                except BlockingIOError:
                    os.close(fd)
            if fds:
                break
            time.sleep(0.05 + (os.getpid() % 7) * 0.01)
        yield
    finally:
        for fd in fds:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


@contextmanager
def cpu_slot(heavy: bool = False):
    if heavy:
        with _flock_slot("heavy", N_HEAVY):
            with _flock_slot("cpu", N_SLOTS):
                yield
    else:
        with _flock_slot("cpu", N_SLOTS):
            yield


# --------------------------------------------------------------------------
# Running one config over a protocol.
# --------------------------------------------------------------------------
def _ts(x) -> str:
    return pd.Timestamp(x).strftime("%Y-%m-%d")


def run_backtest(strategy, market, policy, comm=COMMISSION, slip=SLIPPAGE):
    return Backtest(strategy, market=market, cash=CASH, commission_pct=comm,
                    slippage_pct=slip, tax_policy=policy).run()


def run_starts(make_strategy, market, policy, protocol: Protocol, starts=None,
               comm=COMMISSION, slip=SLIPPAGE, full_stats: bool = True) -> dict:
    """Run `make_strategy()` once per start date; return checkpoint values.

    Output (JSON-ready):
      starts: {start: {"t0": first trading day, "ck": {E: [liq, equity]}}}
      monthly: {day: [liq, equity]} for the first start (full-period run)
      full: summary stats of the first start's run (trades, tax, drawdown, ...)
    """
    starts = list(protocol.starts if starts is None else starts)
    out = {"starts": {}, "monthly": {}, "full": None}
    if not starts:
        return out
    for k, s in enumerate(starts):
        first = (k == 0)
        gate = Gate(make_strategy(), s, protocol.checkpoints, policy, monthly=first)
        res = run_backtest(gate, market, policy, comm, slip)
        if gate.t0 is None:
            continue
        out["starts"][_ts(s)] = {
            "t0": _ts(gate.t0),
            "ck": {_ts(e): [v[0], v[1], _ts(v[2])] for e, v in gate.values.items()},
        }
        if first:
            out["monthly"] = {_ts(d): [v[0], v[1]] for d, v in gate.months.items()}
            if full_stats:
                out["full"] = run_stats(res, gate.t0)
    return out


def run_stats(res, t0) -> dict:
    eq = res.equity["total"]
    eq = eq[eq.index >= t0]
    r = eq.pct_change().dropna()
    trades = res.trades
    n_tr = 0 if trades.empty else int(len(trades[trades.index >= t0]))
    turnover = None
    if not trades.empty:
        tv = trades[trades.index >= t0]
        sells = float(tv.loc[tv["side"] == "SELL", "value"].sum())
        yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
        turnover = sells / float(eq.mean()) / yrs
    dd = float((eq / eq.cummax() - 1.0).min()) if len(eq) else 0.0
    vol = float(r.std() * np.sqrt(252)) if len(r) > 1 else 0.0
    sharpe = float(np.sqrt(252) * r.mean() / r.std()) if len(r) > 1 and r.std() > 0 else 0.0
    return {
        "trades": n_tr,
        "turnover": turnover,
        "taxes_paid": res.taxes_paid,
        "terminal_tax": res.terminal_tax,
        "max_drawdown": dd,
        "vol": vol,
        "sharpe": sharpe,
        "commission": 0.0 if trades.empty else float(trades["commission"].sum()),
        "avg_cash_frac": float((res.equity["cash"][res.equity.index >= t0] / eq).mean()) if len(eq) else 0.0,
    }


# --------------------------------------------------------------------------
# Benchmark (cached per protocol x regime, in-process and on disk).
# --------------------------------------------------------------------------
_BENCH: dict = {}


def benchmark(protocol: Protocol | str, regime: str, comm=COMMISSION, slip=SLIPPAGE) -> dict:
    if isinstance(protocol, str):
        protocol = PROTOCOLS[protocol]
    key = (protocol.name, regime, protocol.benchmark, comm, slip)
    if key in _BENCH:
        return _BENCH[key]
    h = hashlib.sha1(json.dumps([*map(str, key), "bench-v2"]).encode()).hexdigest()[:16]
    path = CACHE_DIR / "bench" / f"{h}.json"
    if path.exists():
        out = json.loads(path.read_text())
    else:
        m = data.market([protocol.benchmark])
        out = run_starts(lambda: BuyHoldOne(protocol.benchmark), m, policy_for(regime),
                         protocol, comm=comm, slip=slip)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(out))
        tmp.replace(path)
    _BENCH[key] = out
    return out


def benchmark_monthly(protocol: Protocol | str, regime: str, start: str,
                      comm=COMMISSION, slip=SLIPPAGE) -> dict:
    """Month-end liquidation values of the benchmark bought on `start` (for
    strategies whose first valid start is not the protocol's first start)."""
    if isinstance(protocol, str):
        protocol = PROTOCOLS[protocol]
    key = (protocol.name, regime, protocol.benchmark, comm, slip, start)
    if key in _BENCH:
        return _BENCH[key]
    h = hashlib.sha1(json.dumps([*map(str, key), "benchm-v1"]).encode()).hexdigest()[:16]
    path = CACHE_DIR / "bench" / f"m{h}.json"
    if path.exists():
        out = json.loads(path.read_text())
    else:
        m = data.market([protocol.benchmark])
        r = run_starts(lambda: BuyHoldOne(protocol.benchmark), m, policy_for(regime),
                       protocol, starts=[pd.Timestamp(start)], comm=comm, slip=slip,
                       full_stats=False)
        out = r["monthly"]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(out))
        tmp.replace(path)
    _BENCH[key] = out
    return out

"""Round 2, gap 4 (family 'r2_gap4'): other ways a taxable position ends.

The lab protocol (and the site) scores every window as if the whole book were
SOLD on the window's last day and the tax on every unrealized gain paid at once.
A buy-and-hold SPY investor rarely does that: the position can end in a
step-up at death, a gift of appreciated shares to charity, or a slow sale over a
retirement. This module re-runs a config through a recorder that values the
SAME engine state, at every checkpoint and month end, under several
end-of-window treatments, for the strategy and for the benchmark alike:

  liq     the protocol's number: equity - tax(this calendar year's realized
          gains) - tax(every unrealized gain, short/long by lot age, after the
          loss carryforward). Bit-identical to core.liquidation_value.
  eq      pre-liquidation equity (cash + holdings). The critic's cache-only
          "step-up" proxy; it forgets the tax still owed on gains realized
          earlier in the same calendar year.
  step    step-up at death: equity - tax(this year's realized gains, net of the
          carryforward). Unrealized gains AND losses vanish at death, and an
          unused carryforward dies with the taxpayer.
  donate  the appreciated lots go to charity (deduction at market value, no gain
          realized: same as an equal cash gift) after the loss lots are sold
          (their losses offset this year's realized gains; leftover
          carryforward is given no value). >= step.
  ret     gradual liquidation in retirement: from the window's end, the book is
          sold in N equal annual slices (1/N of the shares each year, at the end
          of years 1..N, so every sale is long-term), lots in minimum-tax order
          (highest basis/value first = losses first, then the smallest gains; the
          multi-ticker generalisation of HIFO), taxed at the long-term rate with
          losses netted and carried forward (the carryforward left at the
          window's end is used). After the window every asset is assumed to earn
          the same return g (so the comparison depends only on the books' tax
          state, not on what each happened to hold), and g is also the discount
          rate. The value reported is the CASH-EQUIVALENT at the window's end:
          the amount of fresh (fully-taxed) money that, decumulated the same
          way, gives the same present value of after-tax proceeds:
              ret = cash - fy_tax + (H - PV(taxes on the book's sales)) / f,
              f   = 1 - t_lt * (1 - a/N),   a = sum_k (1+g)^-k,
          where H is the holdings' value. A book with no embedded gain is worth
          H; with g = 0 the value is liquidation with every lot at the
          long-term rate; as g grows it tends to the step-up value.

Everything is computed from the engine's own lots (FIFO in the engine), so the
liq column is the site's number and the other columns differ only in how the
position ends.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from backtester import Strategy
from backtester.tax import compute_year_tax

from .. import core, data, registry
from ..registry import register_kind

HERE = Path(__file__).resolve()
SCRATCH = HERE.parents[1] / "scratch" / "r2_gap4"
CACHE = SCRATCH / "cache"

# (g, N) specs for the retirement treatment; the first is the headline.
RET_SPECS: tuple = ((0.07, 20), (0.0, 20), (0.04, 20), (0.10, 20), (0.07, 10), (0.07, 30))
# column layout of a recorded value row
COLS = ["liq", "eq", "fy", "fy_don"] + [f"ret_g{int(round(g * 100))}_n{n}" for g, n in RET_SPECS]


def _code_hash() -> str:
    return hashlib.sha1(HERE.read_bytes()).hexdigest()[:12]


_HASH = _code_hash()


# --------------------------------------------------------------------------
# valuation of one engine state under every treatment
# --------------------------------------------------------------------------
def retire_value(cash_after_fy: float, v: np.ndarray, b: np.ndarray, pool: float,
                 t_lt: float, g: float, n: int) -> float:
    """Cash-equivalent value of a book sold in n equal annual slices (see module doc)."""
    if len(v) == 0:
        return cash_after_fy
    V = float(v.sum())
    if V <= 0:
        return cash_after_fy
    order = np.argsort(-(b / v), kind="stable")
    cv = np.r_[0.0, np.cumsum(v[order])]
    cb = np.r_[0.0, np.cumsum(b[order])]
    edges = np.linspace(0.0, cv[-1], n + 1)
    basis_k = np.diff(np.interp(edges, cv, cb))
    growth = (1.0 + g) ** np.arange(1, n + 1)
    gain_k = growth * (V / n) - basis_k
    pv = 0.0
    for k in range(n):
        x = float(gain_k[k])
        if x <= 0.0:
            pool += -x
            continue
        used = min(pool, x)
        pool -= used
        pv += (x - used) * t_lt / growth[k]
    a = float((1.0 / growth).sum())
    f = 1.0 - t_lt * (1.0 - a / n)
    return cash_after_fy + (V - pv) / f


def term_values(eng, policy, specs=RET_SPECS) -> list:
    """[liq, eq, fy_tax, fy_tax_donate, ret_spec...] for the engine's current state."""
    pf = eng.portfolio
    prices = eng.current_prices()
    equity = pf.cash + pf.holdings_value(prices)
    if policy is None:
        return [equity, equity, 0.0, 0.0] + [equity] * len(specs)
    date = eng._date
    year = date.year
    carry = 0.0
    for y in sorted(k for k in pf.realized if k < year):
        r = pf.realized[y]
        _, carry = compute_year_tax(r["st"], r["lt"], carry, policy)
    r = pf.realized.get(year, {"st": 0.0, "lt": 0.0})
    fy_tax, carry2 = compute_year_tax(r["st"], r["lt"], carry, policy)
    st_u, lt_u = pf.unrealized_gains(date, prices, policy)          # engine's own sums
    unreal_tax, _ = compute_year_tax(st_u, lt_u, carry2, policy)
    liq = equity - fy_tax - unreal_tax                               # == core.liquidation_value
    vs, bs = [], []
    st_loss = lt_loss = 0.0
    for ticker, lots in pf.lots.items():
        px = prices.get(ticker)
        if px is None:
            continue
        for lot in lots:
            if lot.shares <= 0:
                continue
            gain = (px - lot.cost_per_share) * lot.shares
            vs.append(px * lot.shares)
            bs.append(lot.cost_per_share * lot.shares)
            if gain < 0:
                if policy.is_long_term((date - lot.date).days):
                    lt_loss += gain
                else:
                    st_loss += gain
    fy_don, _ = compute_year_tax(r["st"] + st_loss, r["lt"] + lt_loss, carry, policy)
    v = np.asarray(vs, float)
    b = np.asarray(bs, float)
    cash_after = equity - float(v.sum()) - fy_tax
    t_lt = policy.long_term_rate
    rets = [retire_value(cash_after, v, b, carry2, t_lt, g, n) for g, n in specs]
    return [liq, equity, fy_tax, fy_don] + rets


class TermGate(core.Gate):
    """core.Gate that records every treatment at checkpoints and month ends.
    `monthly` may be True/False or a set of start dates handled by the caller."""

    def __init__(self, inner, start, checkpoints, policy, monthly=False, specs=RET_SPECS):
        super().__init__(inner, start, checkpoints, policy, monthly=monthly)
        self.specs = specs

    def on_day(self, ctx) -> None:
        d = ctx.date
        if d < self.start:
            return
        self.inner.on_day(ctx)
        labels = self._ck.get(d)
        is_me = d in self._month_end
        if labels or is_me:
            vals = term_values(ctx._engine, self.policy, self.specs)
            if labels:
                for e in labels:
                    self.values[e] = (vals, d)
            if is_me:
                self.months[d] = vals


# --------------------------------------------------------------------------
# running a config / the benchmark over a protocol (mirrors sweep.run_one)
# --------------------------------------------------------------------------
def _monthly_starts(starts: list, n_monthly: int) -> set:
    """The first start plus the next yearly anniversaries (n_monthly in all)."""
    if not starts:
        return set()
    s0 = pd.Timestamp(starts[0])
    want = {s0 + pd.DateOffset(years=k) for k in range(n_monthly)}
    return {s for s in starts if pd.Timestamp(s) in want}


def run_starts_terms(make_strategy, market, policy, protocol, starts, monthly_set,
                     comm=core.COMMISSION, slip=core.SLIPPAGE, specs=RET_SPECS) -> dict:
    out = {"starts": {}, "monthly": {}, "cols": COLS}
    for k, s in enumerate(starts):
        mon = s in monthly_set
        gate = TermGate(make_strategy(), s, protocol.checkpoints, policy, monthly=mon, specs=specs)
        res = core.run_backtest(gate, market, policy, comm, slip)
        if gate.t0 is None:
            continue
        key = core._ts(s)
        out["starts"][key] = {
            "t0": core._ts(gate.t0),
            "ck": {core._ts(e): [core._ts(v[1])] + [float(x) for x in v[0]] for e, v in gate.values.items()},
        }
        if mon:
            out["monthly"][key] = {core._ts(dd): [float(x) for x in v] for dd, v in gate.months.items()}
        if k == 0:
            out["full"] = core.run_stats(res, gate.t0)
    return out


def _key(payload) -> str:
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20]


def run_terms(cfg: dict, regime: str = "CA", protocol: str = "full", n_monthly: int = 5,
              comm=core.COMMISSION, slip=core.SLIPPAGE, use_cache: bool = True,
              starts_override=None) -> dict:
    registry.load_families()
    prot = core.PROTOCOLS[protocol]
    key = _key([cfg, regime, protocol, comm, slip, registry.code_version(cfg), _HASH, n_monthly,
                [core._ts(s) for s in starts_override] if starts_override else None])
    path = CACHE / "runs" / key[:2] / f"{key}.json"
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    kind = registry.kind_of(cfg)
    t_start = time.time()
    with core.cpu_slot(heavy=kind.heavy(cfg)):
        universe = kind.universe(cfg)
        tick = kind.tickers(cfg)
        missing = [t for t in tick if data.path_for(t) is None]
        if missing:
            raise ValueError(f"no data for {missing}")
        mkt = data.market(tick, universe=universe)
        ms = registry.min_start(cfg)
        starts = list(starts_override) if starts_override else [s for s in prot.starts if ms is None or s >= ms]
        mset = _monthly_starts(starts, n_monthly)
        out = run_starts_terms(lambda: kind.build(cfg), mkt, core.policy_for(regime), prot,
                               starts, mset, comm, slip)
    rec = {"cfg": cfg, "regime": regime, "protocol": protocol, "comm": comm, "slip": slip,
           "elapsed": time.time() - t_start, **out}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    if kind.heavy(cfg):
        data.clear_markets()
    return rec


def bench_terms(protocol: str = "full", regime: str = "CA", comm=core.COMMISSION,
                slip=core.SLIPPAGE, ticker: str | None = None) -> dict:
    """The protocol's buy-and-hold benchmark under every treatment, monthly rows
    for EVERY start (so any strategy's first start has a matching series)."""
    prot = core.PROTOCOLS[protocol]
    tk = ticker or prot.benchmark
    key = _key(["bench", protocol, regime, comm, slip, tk, _HASH])
    path = CACHE / "bench" / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    m = data.market([tk])
    starts = list(prot.starts)
    with core.cpu_slot():
        out = run_starts_terms(lambda: core.BuyHoldOne(tk), m, core.policy_for(regime), prot,
                               starts, set(starts), comm, slip)
    rec = {"bench": tk, "regime": regime, "protocol": protocol, **out}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    return rec


# --------------------------------------------------------------------------
# statistics per treatment
# --------------------------------------------------------------------------
TREATMENTS = {
    "liq": lambda r: r[1],
    "eq": lambda r: r[2],
    "step": lambda r: r[2] - r[3],
    "donate": lambda r: r[2] - r[4],
}
for _i, (_g, _n) in enumerate(RET_SPECS):
    TREATMENTS[f"ret_g{int(round(_g * 100))}_n{_n}"] = (lambda i: (lambda r: r[5 + i]))(_i)
# monthly rows have no leading day string
MTREAT = {k: (lambda f: (lambda row: f([None] + row)))(f) for k, f in TREATMENTS.items()}


def _cagr(v, t0, day):
    days = (pd.Timestamp(day) - pd.Timestamp(t0)).days
    if days <= 0 or v <= 0:
        return None
    return (v / core.CASH) ** (365.25 / days) - 1.0


def windows(rec: dict, bench: dict, treat: str, lengths=(3, 5, 10, 15, 20)) -> pd.DataFrame:
    f = TREATMENTS[treat]
    prot = core.PROTOCOLS[rec["protocol"]]
    end_all = core._ts(prot.checkpoints[-1])
    rows = []
    for s, st in rec["starts"].items():
        bst = bench["starts"].get(s)
        if not bst:
            continue
        for L in list(lengths) + ["end"]:
            e = end_all if L == "end" else (pd.Timestamp(s) + pd.DateOffset(years=L)).strftime("%Y-%m-%d")
            if pd.Timestamp(e) > pd.Timestamp(end_all):
                continue
            a, b = st["ck"].get(e), bst["ck"].get(e)
            if not a or not b:
                continue
            ca, cb = _cagr(f(a), st["t0"], a[0]), _cagr(f(b), bst["t0"], b[0])
            if ca is None or cb is None:
                continue
            rows.append((s, e, L, ca, cb, ca - cb))
    return pd.DataFrame(rows, columns=["start", "end", "length", "cagr", "bench", "excess"])


def monthly_excess(rec: dict, bench: dict, treat: str, start: str) -> pd.Series:
    f = MTREAT[treat]
    am = rec["monthly"].get(start)
    bm = bench["monthly"].get(start)
    if not am or not bm:
        return pd.Series(dtype=float)
    a = pd.Series({pd.Timestamp(k): f(v) for k, v in am.items()}).sort_index()
    b = pd.Series({pd.Timestamp(k): f(v) for k, v in bm.items()}).sort_index()
    a.index = a.index.to_period("M")
    b.index = b.index.to_period("M")
    j = a.index.intersection(b.index)
    a, b = a[j], b[j]
    if (a <= 0).any() or (b <= 0).any():
        return pd.Series(dtype=float)
    la = np.log(np.r_[core.CASH, a.values])
    lb = np.log(np.r_[core.CASH, b.values])
    return pd.Series(np.diff(la) - np.diff(lb), index=j)


def summary(rec: dict, bench: dict, treat: str, n_boot: int = 1000) -> dict:
    from .. import metrics
    w = windows(rec, bench, treat)
    out: dict = {}
    if w.empty:
        return out
    starts = sorted(rec["starts"])
    first = starts[0]
    out["first_start"] = first
    full = w[(w.start == first) & (w.length == "end")]
    if len(full):
        out["full_excess"] = float(full.excess.iloc[0])
    ends = w[w.length == "end"].set_index("start").excess
    # to-end excess averaged over the first 16 quarterly starts (4 years of starts)
    out["full_excess_avg16"] = float(ends.reindex(starts[:16]).dropna().mean())
    for L in (5, 10, 15, 20):
        x = w[w.length == L].excess
        if len(x):
            out[f"ex{L}_mean"] = float(x.mean())
            out[f"ex{L}_beat"] = float((x > metrics.BEAT_EPS).mean())
            out[f"ex{L}_min"] = float(x.min())
            out[f"ex{L}_n"] = int(len(x))
    xs = [out.get(f"ex{L}_mean") for L in (5, 10, 15)]
    xs = [x for x in xs if x is not None]
    out["score"] = float(np.mean(xs)) if xs else float("nan")
    ps = {}
    for s in sorted(rec.get("monthly", {})):
        x = monthly_excess(rec, bench, treat, s)
        if len(x) >= 24:
            bs = metrics.boot_stats(x, n_boot=n_boot)
            ps[s] = bs.get("boot_p")
            if s == first:
                out["boot_p"] = bs.get("boot_p")
                out["boot_mean"] = bs.get("boot_mean")
    if ps:
        out["boot_p_starts"] = ps
        out["boot_p_mean"] = float(np.mean(list(ps.values())))
        out["boot_p_max"] = float(np.max(list(ps.values())))
    return out


def bar_1_3(s: dict) -> dict:
    """Bar items 1-3 (score>0 & full>0; 10y beat>=.75 & 15y beat>=.85; boot_p<=.10)."""
    i1 = (s.get("score", -1) > 0) and (s.get("full_excess", -1) > 0)
    b10, b15 = s.get("ex10_beat"), s.get("ex15_beat")
    i2 = (b10 is None or b10 >= 0.75) and (b15 is None or b15 >= 0.85)
    i3 = s.get("boot_p") is not None and s["boot_p"] <= 0.10
    return {"i1": bool(i1), "i2": bool(i2), "i3": bool(i3), "pass": bool(i1 and i2 and i3)}


# --------------------------------------------------------------------------
# calibration control: SPY with forced realization (no signal at all)
# --------------------------------------------------------------------------
class Churn(Strategy):
    """Hold `ticker`; every `every_days` days sell the whole position and buy it
    straight back (same close), realizing the gain. every_days=366 realizes only
    long-term gains, 182 only short-term ones. A cash deficit left by the January
    tax payment is covered on the first trading day of each month. Pure tax-
    structure control: same pre-tax exposure as the benchmark."""

    def __init__(self, ticker: str = "SPY", every_days: int = 366):
        self.ticker = ticker
        self.every_days = int(every_days)

    def initialize(self, ctx) -> None:
        self.t_buy = None
        self._m = None

    def on_day(self, ctx) -> None:
        t = self.ticker
        if ctx.price(t) is None:
            return
        if self.t_buy is None:
            ctx.order_target_percent(t, 1.0)
            self.t_buy = ctx.date
            return
        if (ctx.date - self.t_buy).days >= self.every_days:
            ctx.liquidate(t)
            ctx.order_target_percent(t, 1.0)
            self.t_buy = ctx.date
            self._m = (ctx.date.year, ctx.date.month)
            return
        m = (ctx.date.year, ctx.date.month)
        if m != self._m:
            self._m = m
            if ctx.cash < 0:
                ctx.order_target_percent(t, 1.0)


register_kind("r2_gap4.churn",
              lambda c: Churn(c.get("ticker", "SPY"), c.get("every_days", 366)),
              lambda c: list(dict.fromkeys([c.get("ticker", "SPY"), "SPY"])))

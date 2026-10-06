"""Round 2, gap 1: Section 1256 index futures for the timing and leverage rules
(family 'r2_gap1'; research only -- the website cannot run any of this).

WHAT IS MODELLED
----------------
An account that holds T-bill collateral and k x notional of S&P 500 futures
(ES / MES) instead of a k x daily-reset leveraged ETF.

* Futures excess return (one synthetic "rolled" contract):
      r_F(t) = r_U(t) - irx(t-1)/100/252 - basis/252
  r_U = the underlying's total-return close-to-close return (SPY, VFINXR or the
  S&P 500 TR index, so the comparison with the ETF version uses the SAME
  underlying), irx = 13-week T-bill rate known at the previous close (the same
  financing convention as the lab's SYN_* leveraged series), basis = roll and
  implied-financing cost above T-bills (0.1-0.3%/yr; stressed up to 1%).
* Collateral: cash earns irx(t-1)/100/252 - bill_fee/252 (bill_fee 0.10%/yr like
  the lab's SYN_TBILL), credited daily; negative cash pays the same rate.
* Variation margin: the futures P&L of each day is settled in cash at that
  day's close; the notional drifts with the contract (N *= 1 + r_F) and is
  re-set to target when it drifts more than `lev_band` (0 = every day, i.e. the
  exposure path of a daily-reset leveraged ETF). Trades in notional cost
  `fut_cost` per side (default 2 bps; real ES/MES all-in cost is ~0.2-0.5 bp).
* ETF legs (off-state Treasuries, a never-sold SPY core) trade through the
  engine exactly as on the site (5+5 bps, FIFO lots).

TAX (federal + NIIT and California kept as separate ledgers)
------------------------------------------------------------
* Section 1256: the year's futures P&L (net of futures trading costs) is marked
  to market at year end and split 40% short-term / 60% long-term regardless of
  holding period; it then nets with the year's other capital gains exactly as
  the engine nets them (one loss pool applied to short-term gains first).
* Loss carryback (IRC 1212(c), federal only): a net section-1256 loss that
  leaves a net capital loss for the year is carried back to the 3 prior years
  (earliest first), each limited to that year's net 1256 gain and its net
  capital gain; the refund (at that year's federal+NIIT rates) is credited with
  the January settlement. The unabsorbed part carries forward as a 1256 loss
  (re-split 40/60 next year). California does not allow the carryback: its
  ledger keeps the loss as an ordinary carryforward.
* Collateral interest: ordinary income, taxed yearly (CA regime: 35% federal
  + 3.8% NIIT, exempt from California tax as Treasury interest; FED: 35%).
* Everything else (ETF lots, the January payment from cash, the after-tax
  liquidation value at every checkpoint, the engine's two-step terminal tax)
  mirrors backtester.Backtest / research.lab.core exactly: with no futures and
  no interest the ledger reproduces the engine to the cent (validate.py).

Regimes: CA = federal (38.8/18.8, ordinary 38.8) + state 9.3% flat (combined
48.1/28.1 = the lab's CA); FED = 35/15, ordinary 35, no NIIT, no state (the
lab's FED); NONE = untaxed.

RUNNING
-------
The engine's own Backtest has no futures, so configs of kind "r2_gap1.fut"
must run through run_cfg()/run_many() here (FutBacktest + FutGate), not
sweep.run. run_cfg also runs ordinary lab configs (weights/combo kinds) in
FutBacktest with futures and interest off, which reproduces sweep.run exactly
and lets both versions record month-end values for several start dates.
Records have the sweep format, so metrics.summary / report work on them.

Config (kind "r2_gap1.fut"):
  rule      {"type": "sma", "sig", "n", "band", "check", "lag", "ma"}   (the
            verify_lev_robust.trend state machine, replicated exactly), or
            {"type": "timing", "params": {...trend_timing.timing params}}, or
            {"type": "on"} (always on: constant leverage)
  x_on      total equity exposure while on (core included), e.g. 2.0
  x_off     total exposure while off (default 0; with a core, x_off < core
            weight would need SHORT futures -> only with "hedge": true)
  off       off-state asset fallback list (e.g. ["VFITX"]); [] = T-bill cash
  core      {"SPY": 0.8}: bought on day one and never sold except to restore
            cash below `cash_floor` x equity; cash above core gap + cash_band
            is swept into the core on monthly rebalance days
  under     underlying of the futures (ticker), basis, bill_fee, fut_cost,
  lev_band, carryback (default true), requires (as in the lab)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from backtester import Backtest, Strategy, TaxPolicy

from .. import core, data, registry
from ..blocks import Signal, WeightStrategy, np_closes, period_key
from ..registry import register_kind

HERE = Path(__file__).resolve()
LAB = HERE.parents[1]
SCRATCH = LAB / "scratch" / "r2_gap1"
CACHE = SCRATCH / "cache"

# federal (incl. NIIT where the regime has it) and state parts of each regime
TAXR = {
    "CA": {"fed": (0.388, 0.188), "ord": 0.388, "state": 0.093},
    "FED": {"fed": (0.35, 0.15), "ord": 0.35, "state": 0.0},
    "FEDN": {"fed": (0.388, 0.188), "ord": 0.388, "state": 0.0},
    "NONE": None,
}
for _rg in ("CA", "FED"):            # must add up to the lab's combined rates
    _a = TAXR[_rg]
    assert abs(_a["fed"][0] + _a["state"] - core.REGIMES[_rg][0]) < 1e-12
    assert abs(_a["fed"][1] + _a["state"] - core.REGIMES[_rg][1]) < 1e-12


def policy_for(regime: str):
    if regime == "NONE":
        return None
    r = TAXR[regime]
    return TaxPolicy(short_term_rate=r["fed"][0] + r["state"], long_term_rate=r["fed"][1] + r["state"])


# --------------------------------------------------------------------------
# tax ledger
# --------------------------------------------------------------------------
def _net(st: float, lt: float, carry: float):
    """The engine's netting (backtester.tax.compute_year_tax): one loss pool,
    applied to short-term gains first. Returns (taxable st, taxable lt, carry out)."""
    pool = carry + max(0.0, -st) + max(0.0, -lt)
    gs, gl = max(0.0, st), max(0.0, lt)
    u = min(pool, gs)
    gs -= u
    pool -= u
    u = min(pool, gl)
    gl -= u
    pool -= u
    return gs, gl, pool


class Ledger:
    """Federal (+NIIT) and state ledgers with Section 1256 mark-to-market,
    60/40 character, the federal 3-year carryback and yearly interest tax."""

    def __init__(self, regime: str, carryback: bool = True):
        r = TAXR[regime]
        self.fst, self.flt = r["fed"]
        self.ford = r["ord"]
        self.srate = r["state"]
        self.carryback = carryback
        self.pool_f = 0.0          # federal regular loss carryforward (engine-style pool)
        self.pool_s = 0.0          # state loss carryforward (flat rate; includes 1256 losses)
        self.cf1256 = 0.0          # federal net 1256 loss carried forward (magnitude)
        self.hist: dict = {}       # year -> [taxable st, taxable lt, net 1256 gain capacity]
        self.f1256 = defaultdict(float)
        self.interest = defaultdict(float)
        self.log: list = []        # per settled year: dict of the components

    def _ftax(self, s, l):
        return s * self.fst + l * self.flt

    def year(self, y: int, st_o: float, lt_o: float, unreal=None, commit: bool = False):
        """Tax and carryback refund for year y. st_o/lt_o: the engine's realized
        short/long-term gains on ordinary (non-1256) sales; unreal: (st, lt)
        unrealized gains when liquidating (engine two-step: realized first, then
        unrealized with the remaining pool). Returns (tax, refund)."""
        f = self.f1256.get(y, 0.0)
        it = self.interest.get(y, 0.0)
        # ---- federal capital gains
        f_tot = f - (self.cf1256 if self.carryback else 0.0)
        st1 = st_o + 0.4 * f_tot
        lt1 = lt_o + 0.6 * f_tot
        ts, tl, p1 = _net(st1, lt1, self.pool_f)
        tax_f = self._ftax(ts, tl)
        if unreal is not None:
            ts2, tl2, p2 = _net(unreal[0], unreal[1], p1)
            tax_f += self._ftax(ts2, tl2)
        else:
            p2 = p1
        refund = 0.0
        absorbed = []
        L = 0.0
        rem = 0.0
        if self.carryback:
            loss = max(0.0, -f_tot)
            L = min(max(0.0, p2 - self.pool_f), loss)       # the year's NCL attributable to 1256
            rem = L
            for yy in (y - 3, y - 2, y - 1):
                h = self.hist.get(yy)
                if h is None or rem <= 1e-9:
                    continue
                cap = min(h[2], h[0] + h[1])
                a = min(rem, cap)
                if a <= 1e-9:
                    continue
                s1, l1, _ = _net(h[0] - 0.4 * a, h[1] - 0.6 * a, 0.0)
                refund += self._ftax(h[0], h[1]) - self._ftax(s1, l1)
                absorbed.append((yy, a, s1, l1))
                rem -= a
        # ---- ordinary interest (federal; T-bill interest is CA-exempt)
        tax_i = max(0.0, it) * self.ford
        # ---- state: flat rate on net capital gain, no carryback
        tax_s = 0.0
        ps2 = self.pool_s
        if self.srate > 0.0:
            s_net = st_o + lt_o + f
            g = max(0.0, s_net - self.pool_s)
            ps1 = max(0.0, self.pool_s - s_net)
            tax_s = g * self.srate
            if unreal is not None:
                u = unreal[0] + unreal[1]
                tax_s += max(0.0, u - ps1) * self.srate
                ps2 = max(0.0, ps1 - u)
            else:
                ps2 = ps1
        tax = tax_f + tax_i + tax_s
        if commit:
            for yy, a, s1, l1 in absorbed:
                h = self.hist[yy]
                h[0], h[1] = s1, l1
                h[2] -= a
            if self.carryback:
                self.pool_f = p2 - L
                self.cf1256 = rem
            else:
                self.pool_f = p2
            self.pool_s = ps2
            self.hist[y] = [ts, tl, max(0.0, f_tot)]
            self.log.append({"year": y, "st_o": st_o, "lt_o": lt_o, "f1256": f, "interest": it,
                             "tax_cap_fed": tax_f, "tax_int": tax_i, "tax_state": tax_s,
                             "refund": refund, "carryback": L - rem, "cf1256": rem,
                             "pool_f": self.pool_f, "pool_s": self.pool_s})
        return tax, refund


# --------------------------------------------------------------------------
# futures / collateral return arrays on a market calendar
# --------------------------------------------------------------------------
_ARR: dict = {}


def _irx_prev(index: pd.DatetimeIndex) -> pd.Series:
    irx = data.frame("^IRX")["Close"].astype(float)
    full = irx.reindex(irx.index.union(index)).ffill()
    return (full.shift(1).reindex(index) / 100.0 / 252.0).fillna(0.0)


# Approximate 3-month LIBOR minus 3-month T-bill (TED spread), annual averages:
# verify_lev_mech's table for 2000-2008, extended back to 1986 (FRED TEDRATE, rounded).
TED = {1986: 0.0065, 1987: 0.010, 1988: 0.009, 1989: 0.0085, 1990: 0.007, 1991: 0.0055,
       1992: 0.0045, 1993: 0.003, 1994: 0.004, 1995: 0.005, 1996: 0.004, 1997: 0.0045, 1998: 0.006,
       1999: 0.005, 2000: 0.005, 2001: 0.004, 2002: 0.0025, 2003: 0.002, 2004: 0.0025, 2005: 0.0035,
       2006: 0.0045, 2007: 0.009, 2008: 0.015}


def basis_cme(year: int) -> float:
    """Period-calibrated S&P futures financing cost above T-bills (approximate):
    futures financed at about LIBOR flat until 2009 (= the TED spread, capped at
    1%), LIBOR+0-0.3% in 2010-16 (0.25%), rich rolls in 2017-19 (up to LIBOR+0.73%:
    0.60%), SOFR+~0.3% in 2020-23 (0.35-0.40%), SOFR+0.6-1.4% since 2024 (1.00%);
    plus 0.03%/yr for the four rolls' spread and commissions."""
    if year <= 2008:
        b = min(TED.get(year, 0.005), 0.010)
    elif year == 2009:
        b = 0.004
    elif year <= 2016:
        b = 0.0025
    elif year <= 2019:
        b = 0.006
    elif year == 2020:
        b = 0.004
    elif year <= 2023:
        b = 0.0035
    else:
        b = 0.010
    return b + 0.0003


def fut_arrays(market, under: str, basis, bill_fee: float):
    """(r_F, r_bill, ok) aligned to market.calendar: day i's futures excess
    return and collateral accrual (close i-1 -> close i); ok = underlying exists.
    basis: a constant (per year) or "cme" (basis_cme by calendar year)."""
    key = (id(market), under, basis, bill_fee)
    hit = _ARR.get(key)
    if hit is not None:
        return hit
    cal = market.calendar
    u = data.frame(under)["Close"].astype(float)
    uu = u.reindex(u.index.union(cal)).ffill().reindex(cal)
    ru = uu.pct_change().fillna(0.0).to_numpy()
    ok = uu.notna().to_numpy()
    fin = _irx_prev(cal).to_numpy()
    if isinstance(basis, str):
        if basis != "cme":
            raise ValueError(f"unknown basis schedule {basis!r}")
        b = np.array([basis_cme(d.year) for d in cal])
    else:
        b = float(basis)
    rF = ru - fin - b / 252.0
    rB = fin - bill_fee / 252.0
    rF[0] = 0.0
    out = (rF, rB, ok)
    _ARR[key] = out
    return out


# --------------------------------------------------------------------------
# the engine subclass
# --------------------------------------------------------------------------
class FutBacktest(Backtest):
    """backtester.Backtest + one futures position settled daily in cash,
    interest on cash (once the strategy activates it), and the Ledger taxes."""

    def __init__(self, strategy, market, regime: str, under: str | None = None,
                 basis: float = 0.002, bill_fee: float = 0.001, fut_cost: float = 0.0002,
                 carryback: bool = True, comm: float = core.COMMISSION, slip: float = core.SLIPPAGE,
                 cash: float = core.CASH, idle: float = 0.0):
        super().__init__(strategy, market=market, cash=cash, commission_pct=comm,
                         slippage_pct=slip, tax_policy=policy_for(regime))
        self.regime = regime
        self.ledger = None if regime == "NONE" else Ledger(regime, carryback=carryback)
        self.fut_cost = fut_cost
        self.idle = float(idle)          # share of |notional| held as margin cash earning nothing
        self.notional = 0.0
        self.collateral_on = False       # interest accrues only once the strategy starts
        if under is not None:
            self.rF, self.rB, self.fok = fut_arrays(market, under, basis, bill_fee)
        else:
            self.rF = self.rB = self.fok = None
        # statistics
        self.fut_trades = 0
        self.fut_traded = 0.0
        self.fut_cost_paid = 0.0
        self.fut_pnl = 0.0
        self.interest_total = 0.0
        self.refunds = 0.0

    # ---- futures orders (fill at today's close) -----------------------------
    def can_futures(self) -> bool:
        return self.rF is not None and bool(self.fok[self._i])

    def set_notional(self, x: float) -> None:
        if self.rF is None:
            raise RuntimeError("no futures series in this backtest")
        if x != 0.0 and not self.fok[self._i]:
            return
        d = abs(x - self.notional)
        if d < self.min_order_value:
            return
        c = d * self.fut_cost
        self.portfolio.cash -= c
        if self.ledger is not None:
            self.ledger.f1256[self._date.year] -= c       # costs reduce the 1256 gain
        self.notional = x
        self.fut_trades += 1
        self.fut_traded += d
        self.fut_cost_paid += c

    # ---- after-tax liquidation value now (the lab's checkpoint value) -------
    def liq_value(self) -> tuple[float, float]:
        pf = self.portfolio
        prices = self.current_prices()
        equity = pf.cash + pf.holdings_value(prices)
        if self.ledger is None:
            return equity, equity
        y = self._date.year
        r = pf.realized.get(y, {"st": 0.0, "lt": 0.0})
        st_u, lt_u = pf.unrealized_gains(self._date, prices, self.tax_policy)
        tax, refund = self.ledger.year(y, r["st"], r["lt"], unreal=(st_u, lt_u), commit=False)
        return equity - tax + refund, equity

    # ---- the day loop (backtester.Backtest.run + carry + Ledger settlement) --
    def run(self):
        from backtester.result import Result
        self.strategy.initialize(self.ctx)
        market = self.market
        calendar = self.calendar
        cal_values = market.cal_values
        total_days = market.n
        eq_c, eq_h, eq_t = [], [], []
        led = self.ledger
        prev_year = None
        taxes_paid = 0.0
        cash_prev = self.portfolio.cash
        rF, rB = self.rF, self.rB
        for i in range(total_days):
            self._i = i
            self._dv = cal_values[i]
            date = calendar[i]
            self._date = date
            self.today_prices = market.today_tradable[i]
            # 1) overnight carry: variation margin and collateral interest
            if i > 0 and rF is not None:
                n_prev = self.notional
                if self.notional != 0.0:
                    pnl = self.notional * rF[i]
                    self.portfolio.cash += pnl
                    self.fut_pnl += pnl
                    if led is not None:
                        led.f1256[date.year] += pnl
                    self.notional *= 1.0 + rF[i]
                if self.collateral_on and cash_prev != 0.0:
                    base = cash_prev
                    if self.idle > 0.0 and cash_prev > 0.0:
                        base -= min(cash_prev, self.idle * abs(n_prev))
                    it = base * rB[i]
                    self.portfolio.cash += it
                    self.interest_total += it
                    if led is not None:
                        led.interest[date.year] += it
            # 2) settle last year's taxes on the first trading day of a new year
            if led is not None and prev_year is not None and date.year != prev_year:
                r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
                tax, refund = led.year(prev_year, r["st"], r["lt"], commit=True)
                self.portfolio.cash -= tax - refund
                taxes_paid += tax - refund
                self.refunds += refund
            prev_year = date.year
            # 3) the strategy (orders fill at today's close)
            self.ctx.date = date
            self.strategy.on_day(self.ctx)
            cash_prev = self.portfolio.cash
            holdings = self.portfolio.holdings_value(self.current_prices())
            tot = cash_prev + holdings
            eq_c.append(cash_prev)
            eq_h.append(holdings)
            eq_t.append(tot)
        equity = pd.DataFrame({"cash": eq_c, "holdings": eq_h, "total": eq_t},
                              index=pd.DatetimeIndex(calendar, name="date"))
        trades = pd.DataFrame([t.as_dict() for t in self.portfolio.trades])
        if not trades.empty:
            trades = trades.set_index("date")
        terminal_tax = None
        if led is not None:
            r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
            st_u, lt_u = self.portfolio.unrealized_gains(self._date, self.current_prices(), self.tax_policy)
            tax, refund = led.year(prev_year, r["st"], r["lt"], unreal=(st_u, lt_u), commit=False)
            terminal_tax = tax - refund
        return Result(equity=equity, trades=trades, starting_cash=self.starting_cash,
                      taxes_paid=(taxes_paid if led is not None else None), terminal_tax=terminal_tax)


class FutGate(core.Gate):
    """core.Gate whose checkpoint values come from FutBacktest.liq_value."""

    def on_day(self, ctx) -> None:
        d = ctx.date
        if d < self.start:
            return
        self.inner.on_day(ctx)
        labels = self._ck.get(d)
        is_me = d in self._month_end
        if labels or is_me:
            liq, eq = ctx._engine.liq_value()
            if labels:
                for e in labels:
                    self.values[e] = (liq, eq, d)
            if is_me:
                self.months[d] = (liq, eq)


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------
def _closes(ctx, t: str, n: int, lag: int) -> np.ndarray:
    if lag <= 0:
        return np_closes(ctx, t, n)
    c = np_closes(ctx, t, n + lag)
    return c[:-lag] if len(c) > lag else c[:0]


def _ema_last(x: np.ndarray, n: int) -> float:
    a = 2.0 / (n + 1.0)
    e = float(x[0])
    for v in x[1:]:
        e = a * float(v) + (1.0 - a) * e
    return e


class SmaBand:
    """verify_lev_robust.Trend's state machine, replicated: on check days,
    margin m = sig / MA(n) - 1; first evaluation sets on = m > 0, then on once
    m > +band, off once m < -band."""

    def __init__(self, sig="SPY", n=175, band=0.03, check="D", lag=0, ma="sma"):
        self.sig, self.n, self.band, self.check, self.lag, self.ma = sig, int(n), float(band), check, int(lag), ma

    def initialize(self, ctx):
        self.state = None
        self._last = None

    def _margin(self, ctx):
        n = self.n
        if self.ma == "ema":
            c = _closes(ctx, self.sig, 4 * n, self.lag)
            if len(c) < 2 * n:
                return None
            return c[-1] / _ema_last(c, n) - 1.0
        c = _closes(ctx, self.sig, n, self.lag)
        if len(c) < n:
            return None
        return c[-1] / c.mean() - 1.0

    def update(self, ctx):
        pk = period_key(ctx.date, self.check)
        if pk != self._last:
            self._last = pk
            m = self._margin(ctx)
            if m is not None:
                if self.state is None:
                    self.state = m > 0
                elif m > self.band:
                    self.state = True
                elif m < -self.band:
                    self.state = False
        return self.state


class TimingRule:
    """trend_timing.timing's rule engine (warm replay, bands, crosses): on
    while its exposure is >= 0.5."""

    def __init__(self, params):
        from .trend_timing import Timing
        self.t = Timing(**params)

    def initialize(self, ctx):
        self.t.initialize(ctx)

    def update(self, ctx):
        return self.t.exposure(ctx) >= 0.5


class AlwaysOn:
    def initialize(self, ctx):
        pass

    def update(self, ctx):
        return True


def make_rule(spec: dict):
    t = spec.get("type", "sma")
    if t == "sma":
        return SmaBand(**{k: v for k, v in spec.items() if k != "type"})
    if t == "timing":
        return TimingRule(spec["params"])
    if t == "on":
        return AlwaysOn()
    raise ValueError(f"unknown rule type {t!r}")


def rule_tickers(spec: dict) -> list:
    t = spec.get("type", "sma")
    if t == "sma":
        return [spec.get("sig", "SPY")]
    if t == "timing":
        from .trend_timing import _timing_tickers
        p = dict(spec["params"])
        out = [x for x in _timing_tickers(p) if x != p.get("risk")]
        sig = p.get("sig")
        if sig and not sig.startswith("^"):
            out.append(sig)
        return out
    return []


# --------------------------------------------------------------------------
# the strategy
# --------------------------------------------------------------------------
class _NoSignal(Signal):
    def weights(self, ctx, rebalance_day):
        return None


class FutStrat(Strategy):
    def __init__(self, rule, x_on=2.0, x_off=0.0, off=None, core=None, lev_band=0.0,
                 rebalance="M", cash_floor=0.02, cash_band=0.10, hedge=False, sticky=False,
                 hybrid=False, **_):
        self.rule = make_rule(rule)
        self.x_on, self.x_off = float(x_on), float(x_off)
        self.off = [off] if isinstance(off, str) else list(off or [])
        self.core = dict(core or {})
        self.lev_band = float(lev_band)
        self.rebalance = rebalance
        self.cash_floor = float(cash_floor)
        self.cash_band = float(cash_band)
        self.hedge = bool(hedge)
        self.sticky = bool(sticky)     # trend_timing convention: keep a held safe asset
        self.hybrid = bool(hybrid)     # core sold when the rule is off (futures = the increment only)

    def initialize(self, ctx):
        eng = ctx._engine
        if not hasattr(eng, "set_notional"):
            raise RuntimeError("kind r2_gap1.fut must run in r2_gap1.FutBacktest (use r2_gap1.run_cfg)")
        self.rule.initialize(ctx)
        self.ws = WeightStrategy(_NoSignal(), execution="standard")
        self._started = False
        self._state = None
        self._off_t = None
        self._last_reb = None
        self.switches = 0
        self.days_on = 0
        self.days = 0
        self.expo_sum = 0.0
        self._core_bought = False

    # helpers
    def _pv(self, ctx):
        return ctx.portfolio_value

    def _off_asset(self, ctx):
        if self.sticky:
            pos = ctx.positions
            for t in self.off:
                if pos.get(t, 0.0) > 0 and ctx.price(t) is not None:
                    return t
        for t in self.off:
            if ctx.price(t) is not None:
                return t
        return None

    def _set_fut(self, ctx, target, force):
        eng = ctx._engine
        cur = eng.notional
        if force or self.lev_band <= 0.0:
            if abs(target - cur) > 1e-9 * max(1.0, abs(target)):
                eng.set_notional(target)
            return
        if target == 0.0:
            if cur != 0.0:
                eng.set_notional(0.0)
            return
        if cur == 0.0 or abs(cur - target) > self.lev_band * abs(target):
            eng.set_notional(target)

    def on_day(self, ctx):
        eng = ctx._engine
        if not self._started:
            self._started = True
            eng.collateral_on = True
        on = self.rule.update(ctx)
        if on is None:
            return
        rk = period_key(ctx.date, self.rebalance)
        reb = rk != self._last_reb
        if reb:
            self._last_reb = rk
        changed = on != self._state
        if self._state is not None and changed:
            self.switches += 1
        self._state = on
        self.days += 1
        self.days_on += 1 if on else 0
        if self.core and self.hybrid:
            self._hybrid_day(ctx, on, changed, reb)
        elif self.core:
            self._core_day(ctx, on, changed, reb)
        else:
            self._timing_day(ctx, on, changed, reb)
        pv = self._pv(ctx)
        if pv > 0:
            self.expo_sum += (eng.notional + (self._core_value(ctx) if self.core else 0.0)) / pv

    # ---- pure timing: k x futures + bills when on, off asset when off --------
    def _timing_day(self, ctx, on, changed, reb):
        eng = ctx._engine
        if on:
            if ctx.positions:
                self.ws._execute(ctx, {})            # sell the off asset first
                self._off_t = None
            if not eng.can_futures():
                return
            pv = self._pv(ctx)
            self._set_fut(ctx, self.x_on * pv, changed)
            return
        # off
        pv = self._pv(ctx)
        tgt_n = self.x_off * pv
        if eng.notional != 0.0 or tgt_n != 0.0:
            self._set_fut(ctx, tgt_n, changed)
        t = self._off_asset(ctx)
        if not self.off:
            return
        if t is None:
            return
        w = {t: 1.0}
        if changed or t != self._off_t:
            self._off_t = t
            self.ws._execute(ctx, w)
            return
        if reb:                    # verify_lev_robust.trend with sdrift = 0: re-target monthly
            from .verify_lev_robust import _cur_weights
            cur = _cur_weights(ctx)
            ab = max(abs(cur.get(k, 0.0) - w.get(k, 0.0)) for k in set(cur) | set(w))
            if ab > 0.0:
                self.ws._execute(ctx, w)

    # ---- never-sold core + futures overlay ----------------------------------
    def _core_value(self, ctx):
        v = 0.0
        for t in self.core:
            px = ctx.price(t)
            if px is None:
                eng = ctx._engine
                cp = eng.current_prices()
                px = cp.get(t)
            if px:
                v += ctx.shares(t) * px
        return v

    def _core_day(self, ctx, on, changed, reb):
        eng = ctx._engine
        c_w = sum(self.core.values())
        if not self._core_bought:
            live = all(ctx.price(t) is not None for t in self.core)
            if not live:
                return
            self.ws._execute(ctx, dict(self.core))
            self._core_bought = True
        pv = self._pv(ctx)
        if pv <= 0:
            return
        cash = ctx.cash
        gap = max(0.0, 1.0 - c_w)
        # margin / tax call: restore cash by selling core (realizes gains)
        if cash < self.cash_floor * pv:
            need = gap * pv - cash
            self._sell_core(ctx, need)
        elif reb and cash > (gap + self.cash_band) * pv:
            self._buy_core(ctx, cash - gap * pv)
        pv = self._pv(ctx)
        cv = self._core_value(ctx)
        x = self.x_on if on else self.x_off
        tgt = x * pv - cv
        if not self.hedge:
            tgt = max(0.0, tgt)
        if not eng.can_futures():
            return
        self._set_fut(ctx, tgt, changed)

    # ---- hybrid: SPY for the first c of exposure + futures for the increment,
    #      everything sold to the off asset when the rule is off -------------
    def _hybrid_day(self, ctx, on, changed, reb):
        eng = ctx._engine
        if on:
            if changed or not self._core_bought:
                if not all(ctx.price(t) is not None for t in self.core):
                    return
                self.ws._execute(ctx, dict(self.core))     # sells the off asset, buys the core
                self._core_bought = True
                self._off_t = None
            pv = self._pv(ctx)
            if pv <= 0:
                return
            c_w = sum(self.core.values())
            gap = max(0.0, 1.0 - c_w)
            cash = ctx.cash
            if cash < self.cash_floor * pv:
                self._sell_core(ctx, gap * pv - cash)
            elif reb and cash > (gap + self.cash_band) * pv:
                self._buy_core(ctx, cash - gap * pv)
            pv = self._pv(ctx)
            tgt = max(0.0, self.x_on * pv - self._core_value(ctx))
            if eng.can_futures():
                self._set_fut(ctx, tgt, changed)
            return
        # off: no futures, everything in the off asset (or T-bill cash)
        if eng.notional != 0.0:
            eng.set_notional(0.0)
        self._core_bought = False
        t = self._off_asset(ctx)
        w = {t: 1.0} if (self.off and t is not None) else {}
        if changed or (self.off and t != self._off_t):
            self._off_t = t
            self.ws._execute(ctx, w)
            return
        if reb and w:
            from .verify_lev_robust import _cur_weights
            cur = _cur_weights(ctx)
            ab = max(abs(cur.get(k, 0.0) - w.get(k, 0.0)) for k in set(cur) | set(w))
            if ab > 0.0:
                self.ws._execute(ctx, w)

    def _sell_core(self, ctx, amount):
        tot = self._core_value(ctx)
        if tot <= 0 or amount <= 0:
            return
        f = min(1.0, amount / (tot * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)))
        for t in self.core:
            sh = ctx.shares(t)
            if sh > 0 and ctx.price(t) is not None:
                ctx.order(t, -sh * f)

    def _buy_core(self, ctx, amount):
        s = sum(self.core.values())
        cm = (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)
        for t, w in self.core.items():
            px = ctx.price(t)
            if px:
                ctx.order(t, amount * w / s / (px * cm) * 0.999999)


def _fut_tickers(c: dict) -> list:
    out = list(rule_tickers(c["rule"]))
    out += list(c.get("off") or [])
    out += list((c.get("core") or {}).keys())
    if c.get("under"):
        out.append(c["under"])
    out.append("SPY")
    return list(dict.fromkeys(t for t in out if not t.startswith("^")))


def _fut_build(c: dict) -> Strategy:
    keys = ("x_on", "x_off", "off", "core", "lev_band", "rebalance", "cash_floor", "cash_band", "hedge",
            "sticky", "hybrid")
    return FutStrat(c["rule"], **{k: c[k] for k in keys if k in c})


register_kind("r2_gap1.fut", _fut_build, _fut_tickers)


# --------------------------------------------------------------------------
# runner (sweep-format records, own cache)
# --------------------------------------------------------------------------
# Cache key = an explicit version of THIS module's semantics (bump it whenever a
# change could alter any existing config's result; adding an option that is off
# by default does not) + the bytes of the lab/engine files it builds on.
CODE_VERSION = "r2g1-v1"
_SRC_FILES = [LAB / "core.py", LAB / "blocks.py", LAB / "registry.py", LAB / "data.py",
              LAB / "families" / "trend_timing.py", LAB / "families" / "verify_lev_robust.py",
              LAB / "families" / "leverage.py"] + sorted((LAB.parents[1] / "backtester").glob("*.py"))
_SNAP = {str(p): (p.read_bytes() if p.exists() else b"") for p in _SRC_FILES}


def code_hash() -> str:
    h = hashlib.sha1(CODE_VERSION.encode())
    for k in sorted(_SNAP):
        h.update(_SNAP[k])
    return h.hexdigest()[:12]


FUT_DEFAULTS = {"basis": 0.002, "bill_fee": 0.001, "fut_cost": 0.0002, "carryback": True, "idle": 0.0}


def _key(cfg, regime, protocol, comm, slip, mstarts) -> str:
    payload = json.dumps([cfg, regime, protocol, comm, slip, sorted(mstarts or []), code_hash()],
                         sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:20]


def cfg_id(cfg: dict) -> str:
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:14]


def run_cfg(cfg: dict, regime: str = "CA", protocol: str = "full", comm: float = core.COMMISSION,
            slip: float = core.SLIPPAGE, monthly_starts=(), use_cache: bool = True,
            starts=None) -> dict:
    """Run one config (kind r2_gap1.fut, or any lab kind) on every protocol start
    in FutBacktest; returns a sweep-format record (+ extras)."""
    registry.load_families()
    mstarts = sorted(core._ts(s) for s in monthly_starts)
    key = _key(cfg, regime, protocol, comm, slip, mstarts + (["S:" + ",".join(map(core._ts, starts))] if starts else []))
    path = CACHE / key[:2] / f"{key}.json"
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    kind = registry.kind_of(cfg)
    prot = core.PROTOCOLS[protocol]
    fut = cfg["kind"] == "r2_gap1.fut"
    fp = {k: cfg.get(k, v) for k, v in FUT_DEFAULTS.items()}
    t_start = time.time()
    with core.cpu_slot():
        tick = kind.tickers(cfg)
        missing = [t for t in tick if data.path_for(t) is None]
        if missing:
            raise ValueError(f"no data for {missing}")
        mkt = data.market(tick, universe=kind.universe(cfg))
        ms = registry.min_start(cfg)
        st_list = list(prot.starts if starts is None else [pd.Timestamp(s) for s in starts])
        st_list = [s for s in st_list if ms is None or s >= ms]
        out = {"starts": {}, "monthly": {}, "full": None, "monthly_by_start": {}, "extra": None}
        for k, s in enumerate(st_list):
            first = k == 0
            want_m = first or core._ts(s) in mstarts
            gate = FutGate(kind.build(cfg), s, prot.checkpoints, policy_for(regime), monthly=want_m)
            eng = FutBacktest(gate, mkt, regime, under=(cfg.get("under") if fut else None),
                              basis=fp["basis"], bill_fee=fp["bill_fee"], fut_cost=fp["fut_cost"],
                              carryback=fp["carryback"], comm=comm, slip=slip, idle=fp["idle"])
            res = eng.run()
            if gate.t0 is None:
                continue
            out["starts"][core._ts(s)] = {
                "t0": core._ts(gate.t0),
                "ck": {core._ts(e): [v[0], v[1], core._ts(v[2])] for e, v in gate.values.items()},
            }
            mon = {core._ts(d): [v[0], v[1]] for d, v in gate.months.items()}
            if first:
                out["monthly"] = mon
                out["full"] = core.run_stats(res, gate.t0)
                ex = {"fut_trades": eng.fut_trades, "fut_cost_paid": eng.fut_cost_paid,
                      "fut_pnl": eng.fut_pnl, "interest": eng.interest_total, "refunds": eng.refunds}
                eqm = float(res.equity["total"][res.equity.index >= gate.t0].mean())
                yrs = max((res.equity.index[-1] - gate.t0).days / 365.25, 1e-9)
                ex["fut_turnover"] = eng.fut_traded / eqm / yrs if eqm > 0 else None
                inner = gate.inner
                if isinstance(inner, FutStrat):
                    ex["switches"] = inner.switches
                    ex["share_on"] = inner.days_on / inner.days if inner.days else None
                    ex["avg_exposure"] = inner.expo_sum / inner.days if inner.days else None
                if eng.ledger is not None:
                    ex["tax_log"] = eng.ledger.log
                out["extra"] = ex
            elif want_m:
                out["monthly_by_start"][core._ts(s)] = mon
    rec = {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol, "comm": comm,
           "slip": slip, "elapsed": time.time() - t_start, **out}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    return rec


def _task(args):
    cfg, regime, protocol, comm, slip, mstarts = args
    import traceback
    try:
        return run_cfg(cfg, regime, protocol, comm, slip, monthly_starts=mstarts)
    except Exception as e:  # noqa: BLE001
        return {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol,
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}


def run_many(configs, protocol="full", regimes=("CA",), workers=4, comm=core.COMMISSION,
             slip=core.SLIPPAGE, monthly_starts=(), verbose=True) -> list:
    """run_cfg over configs x regimes in parallel (fork), cached."""
    import multiprocessing as mp
    import warnings
    from concurrent.futures import ProcessPoolExecutor, as_completed
    registry.load_families()
    mst = tuple(monthly_starts)
    jobs = [(c, rg, protocol, comm, slip, mst) for c in configs for rg in regimes]
    recs, todo = [], []
    for j in jobs:
        mstarts = sorted(core._ts(s) for s in mst)
        key = _key(j[0], j[1], j[2], j[3], j[4], mstarts)
        p = CACHE / key[:2] / f"{key}.json"
        if p.exists():
            try:
                recs.append(json.loads(p.read_text()))
                continue
            except json.JSONDecodeError:
                pass
        todo.append(j)
    if verbose:
        print(f"[r2_gap1] {len(recs)} cached, {len(todo)} to run ({protocol}, {regimes})", flush=True)
    if not todo:
        return recs
    t0 = time.time()
    if workers <= 1:
        for j in todo:
            recs.append(_task(j))
        return recs
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*fork.*")
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as ex:
        futs = [ex.submit(_task, j) for j in todo]
        for n, f in enumerate(as_completed(futs), 1):
            recs.append(f.result())
            if verbose and (n % max(1, len(todo) // 10) == 0 or n == len(todo)):
                el = time.time() - t0
                print(f"[r2_gap1] {n}/{len(todo)} {el:.0f}s", flush=True)
    errs = [r for r in recs if "error" in r]
    if errs and verbose:
        print(f"[r2_gap1] {len(errs)} errors; first: {errs[0]['error']}\n{errs[0].get('trace','')[-1500:]}",
              flush=True)
    return recs

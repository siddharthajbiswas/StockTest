"""Round 2, gap 2: allocation by valuation (family 'r2_gap2').

Equity exposure is set by how expensive the US market is (Shiller CAPE, earnings
yield, the excess CAPE yield, the earnings yield minus the 10-year yield), the
rest goes to a safe asset (intermediate Treasuries or T-bills); exposure above 1
uses a daily-reset 2x fund. Optionally combined with the round-1 daily SMA trend
switch (2x / safe asset) as a gate.

DATA (research/lab/data/R2G2_*, built by scratch/r2_gap2/build_data.py)
-----------------------------------------------------------------------
R2G2_shiller_monthly.csv: Robert Shiller's monthly series as published
(shillerdata.com ie_data.xls, saved 2026-09-02): P = monthly AVERAGE S&P
composite price, D / E = 12-month trailing dividends / earnings (quarterly
totals, linearly interpolated to months), CPI, GS10 (monthly average 10-year
yield), and his CAPE / TR CAPE / ECY columns.

CAUSALITY: everything used on a day of decision month M is known at the start of M
-------------------------------------------------------------------------------
* price      P(M-1): last month's average price (known at the close of M-1);
* earnings   E through qE(M) = the latest quarter-end month <= M-3 (quarterly
             as-reported earnings are complete about 3 months after the quarter;
             interpolated months up to qE only need quarter-ends <= qE);
* CPI        CPI(M-2) (CPI for a month is released mid-way through the next);
* GS10       GS10(M-1) (monthly average, known at the end of M-1).
Measures (decision month M):
  cape   = (P(M-1)/CPI(M-2)) / mean_{k=qE-119..qE} E(k)/CPI(k)    (real-time CAPE)
  ey     = E(qE)/P(M-1)                (trailing earnings yield)
  dy     = D(qE)/P(M-1)                (trailing dividend yield)
  ecy    = 1/cape - (GS10(M-1)/100 - 10y CPI inflation to M-2)   (Shiller's ECY, real-time)
  fed    = ey - GS10(M-1)/100          ("Fed model": earnings yield minus the 10-year)
  cape_sh2 / trcape_sh2 / ecy_sh2 = Shiller's published CAPE / TR-CAPE / ECY of month M-2
         (the critic's literal "lagged 2 months" spec; their 10-year earnings average
         can include 1-2 months whose interpolation needs a quarter not yet reported --
         a <1% weight in a 120-month mean).
Percentiles compare the measure in month M with its own causal history
{X(m): m <= M} -- expanding from 1881 ("exp"), from 1926 ("exp1926"), or over the
trailing 20/30/40 years ("r20"/"r30"/"r40"). "expensiveness" v = percentile for
price-type measures (cape*), 1 - percentile for yield-type ones (ey, dy, ecy, fed).

SIGNAL r2_gap2.val  (params)
---------------------------
measure, hist      as above; hist "raw" uses the measure's level directly
map                {"e_cheap": 1.0, "e_exp": 0.6, "v0": 0.0, "v1": 1.0}: exposure moves
                   linearly from e_cheap (v <= v0) to e_exp (v >= v1);  or
                   {"x": [x1, x2], "e": [e1, e2]} on the raw level (linear, clipped);
                   or {"const": e}.
q, hyst            exposure is rounded to steps of q; it changes only when the raw
                   exposure is >= q*(0.5+hyst) away from the current target.
drift              between target changes, trade back only when a weight drifted more
                   than this (0.10 = 10 pp) on a calendar rebalance day.
eq, lev, safe      tickers: equity, its daily-reset 2x version, safe asset(s) (first
                   tradable of the list). exposure e <= 1: {eq: e, safe: 1-e};
                   1 < e <= 2: {eq: 2-e, lev: e-1}.
trend              optional {"sig", "n", "band", "check", "off_map"}: an SMA(n) band switch
                   on `sig` (state on while sig/SMA-1 > +band, off once < -band, decided on
                   each day's close, the round-1 rule). On -> exposure from `map`; off ->
                   from `off_map` (default {"const": 0}).

Kinds: configs use the lab's "weights" kind (signal "r2_gap2.val") on site/fund
data, and "r2_gap2.wx" (the same WeightStrategy, but a market WITHOUT the
automatically added SPY) for the synthetic 1928-1985 world, whose calendar must
end in 1985.

Protocols added here: "r2g2_pre" (yearly starts 1930..1975, windows ending by
1985-12-31, benchmark R2G2_PEQ), "r2g2_pre_q" (quarterly starts 1930..1980-10),
"r2g2_splice" (yearly starts 1930..2016 to 2026-07, benchmark R2G2_SEQ).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .. import core as _core
from ..blocks import Signal, WeightStrategy, np_closes, period_key
from ..registry import _WS_KEYS, register_kind, register_signal

DATA_VERSION = "2026-10-05a"        # bump whenever R2G2_ data files are rebuilt
TABLE = Path(__file__).resolve().parents[1] / "data" / "R2G2_shiller_monthly.csv"

PRICE_TYPE = {"cape", "cape_sh2", "trcape_sh2"}
YIELD_TYPE = {"ey", "dy", "ecy", "fed", "ecy_sh2"}


# --------------------------------------------------------------------------
# causal monthly valuation table
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def raw_table() -> pd.DataFrame:
    t = pd.read_csv(TABLE)
    t.index = pd.PeriodIndex(pd.to_datetime(t["Date"]), freq="M")
    return t


@lru_cache(maxsize=1)
def valuation_table() -> pd.DataFrame:
    """One row per DECISION month M; every value known at the start of M."""
    t = raw_table()
    P = t["P"].astype(float).values
    D = t["D"].astype(float).values
    E = t["E"].astype(float).values
    CPI = t["CPI"].astype(float).values
    GS = t["GS10"].astype(float).values / 100.0
    n = len(t)
    months = t.index
    re = pd.Series(E / CPI)
    e10 = re.rolling(120, min_periods=120).mean().values       # mean over k-119..k
    out = {k: np.full(n, np.nan) for k in ("cape", "ey", "dy", "ecy", "fed", "P1", "qE_pos")}
    mnum = months.month.values
    for p in range(3, n):
        q = p - 3 - (mnum[p - 3] % 3)                          # latest quarter-end <= M-3
        if q < 0:
            continue
        P1 = P[p - 1]
        cpi2 = CPI[p - 2]
        out["P1"][p] = P1
        out["qE_pos"][p] = q
        if np.isfinite(e10[q]) and e10[q] > 0:
            out["cape"][p] = (P1 / cpi2) / e10[q]
        if np.isfinite(E[q]):
            out["ey"][p] = E[q] / P1
            out["fed"][p] = E[q] / P1 - GS[p - 1]
        if np.isfinite(D[q]):
            out["dy"][p] = D[q] / P1
        if p >= 122 and np.isfinite(out["cape"][p]):
            infl10 = (CPI[p - 2] / CPI[p - 122]) ** 0.1 - 1.0
            out["ecy"][p] = 1.0 / out["cape"][p] - (GS[p - 1] - infl10)
    df = pd.DataFrame(out, index=months)
    df["cape_sh2"] = t["CAPE_sh"].astype(float).shift(2).values
    df["trcape_sh2"] = t["TRCAPE_sh"].astype(float).shift(2).values
    df["ecy_sh2"] = t["ECY_sh"].astype(float).shift(2).values
    return df


def _percentile_hist(x: np.ndarray, months: pd.PeriodIndex, hist: str) -> np.ndarray:
    """Mid-rank percentile of x[i] among x[j], j <= i (window by `hist`), finite only."""
    n = len(x)
    out = np.full(n, np.nan)
    ok = np.isfinite(x)
    yrs = months.year.values
    if hist == "exp":
        lo_fn = lambda i: 0  # noqa: E731
        min_n = 120
    elif hist == "exp1926":
        first = int(np.argmax(yrs >= 1926))
        lo_fn = lambda i: first  # noqa: E731
        min_n = 36
    elif hist.startswith("r") and hist[1:].isdigit():
        w = 12 * int(hist[1:])
        lo_fn = lambda i: max(0, i - w + 1)  # noqa: E731
        min_n = 120
    else:
        raise ValueError(f"unknown hist {hist!r}")
    for i in range(n):
        if not ok[i]:
            continue
        lo = lo_fn(i)
        if lo > i:
            continue
        h = x[lo:i + 1]
        h = h[np.isfinite(h)]
        if len(h) < min_n:
            continue
        out[i] = ((h < x[i]).sum() + 0.5 * ((h == x[i]).sum() - 1)) / max(1, len(h) - 1)
    return np.clip(out, 0.0, 1.0)


@lru_cache(maxsize=None)
def expensiveness(measure: str, hist: str) -> pd.Series:
    """v(M) in [0, 1]: 1 = the most expensive in its causal history (by month)."""
    vt = valuation_table()
    x = vt[measure].values.astype(float)
    pct = _percentile_hist(x, vt.index, hist)
    v = pct if measure in PRICE_TYPE else 1.0 - pct
    return pd.Series(v, index=vt.index)


@lru_cache(maxsize=None)
def level(measure: str) -> pd.Series:
    vt = valuation_table()
    return vt[measure].astype(float)


def map_exposure(m: dict, v: float | None, x: float | None) -> float | None:
    if "const" in m:
        return float(m["const"])
    if "x" in m:
        if x is None or not np.isfinite(x):
            return None
        (x1, x2), (e1, e2) = m["x"], m["e"]
        if x2 == x1:
            return float(e1)
        f = min(1.0, max(0.0, (x - x1) / (x2 - x1)))
        return float(e1 + (e2 - e1) * f)
    if v is None or not np.isfinite(v):
        return None
    e_cheap, e_exp = float(m.get("e_cheap", 1.0)), float(m.get("e_exp", 0.6))
    v0, v1 = float(m.get("v0", 0.0)), float(m.get("v1", 1.0))
    if v1 <= v0:
        f = 1.0 if v >= v1 else 0.0
    else:
        f = min(1.0, max(0.0, (v - v0) / (v1 - v0)))
    return e_cheap + (e_exp - e_cheap) * f


def _cur_weights(ctx) -> dict:
    eng = ctx._engine
    prices = eng.current_prices()
    pos = eng.portfolio.positions
    pv = eng.portfolio.cash + sum(q * prices.get(t, 0.0) for t, q in pos.items())
    if pv <= 0:
        return {}
    return {t: q * prices.get(t, 0.0) / pv for t, q in pos.items()}


class Val(Signal):
    def __init__(self, measure="cape", hist="exp", map=None, q=0.1, hyst=0.25, drift=0.10,
                 eq="VFINXR", lev=None, safe=("VFITX", "FGOVX"), trend=None, data_version=None):
        self.measure = measure
        self.hist = hist
        self.map = dict(map or {"e_cheap": 1.0, "e_exp": 0.6, "v0": 0.0, "v1": 1.0})
        self.q = float(q)
        self.hyst = float(hyst)
        self.drift = drift
        self.eq = eq
        self.lev = lev
        self.safe = [safe] if isinstance(safe, str) else list(safe)
        self.trend = dict(trend) if trend else None
        self.daily = bool(self.trend)
        uses_val = any("const" not in mm for mm in [self.map] + ([self.trend.get("off_map", {"const": 0})]
                                                               if self.trend else []))
        self._vd: dict = {}
        self._xd: dict = {}
        if uses_val and hist != "raw":
            s = expensiveness(measure, hist)
            self._vd = {(p.year, p.month): float(v) for p, v in s.items() if np.isfinite(v)}
        if uses_val:
            s = level(measure)
            self._xd = {(p.year, p.month): float(v) for p, v in s.items() if np.isfinite(v)}

    def initialize(self, ctx):
        self._e = None          # current target exposure
        self._key = None        # (exposure, safe ticker) of the last returned target
        self._state = None      # trend state
        self._last_check = None

    # ---- valuation inputs for the decision month of `date`
    def _vx(self, date):
        k = (date.year, date.month)
        return self._vd.get(k), self._xd.get(k)

    def _trend_state(self, ctx):
        tr = self.trend
        pk = period_key(ctx.date, tr.get("check", "D"))
        if pk == self._last_check:
            return self._state
        self._last_check = pk
        n = int(tr.get("n", 175))
        c = np_closes(ctx, tr["sig"], n)
        if len(c) < n:
            return self._state
        mg = c[-1] / c.mean() - 1.0
        band = float(tr.get("band", 0.03))
        if self._state is None:
            self._state = mg > 0
        elif mg > band:
            self._state = True
        elif mg < -band:
            self._state = False
        return self._state

    def _weights_for(self, ctx, e: float) -> dict:
        safe = next((t for t in self.safe if ctx.price(t) is not None), None)
        w: dict = {}
        if e <= 1.0 + 1e-9:
            e = max(0.0, e)
            if e > 1e-9:
                w[self.eq] = e
            if 1.0 - e > 1e-9 and safe is not None:
                w[safe] = 1.0 - e
        else:
            e = min(2.0, e)
            if self.lev is None or ctx.price(self.lev) is None:
                w[self.eq] = 1.0
            else:
                if 2.0 - e > 1e-9:
                    w[self.eq] = 2.0 - e
                w[self.lev] = e - 1.0
        return w

    def weights(self, ctx, rebalance_day):
        if ctx.price(self.eq) is None:
            return None
        if self.trend:
            st = self._trend_state(ctx)
            if st is None:
                return None
            m = self.map if st else self.trend.get("off_map", {"const": 0.0})
        else:
            if not rebalance_day:
                return None
            m = self.map
        v, x = self._vx(ctx.date)
        raw = map_exposure(m, v, x)
        if raw is None:
            if self._e is None:
                return None
            raw = self._e
        if "const" in m:
            new = raw
        elif self._e is None or abs(raw - self._e) >= self.q * (0.5 + self.hyst) - 1e-12:
            new = round(raw / self.q) * self.q
        else:
            new = self._e
        self._e = new
        tgt = self._weights_for(ctx, new)
        if not tgt:
            return None
        key = (round(new, 6), tuple(sorted(tgt)))
        if key != self._key:
            self._key = key
            return tgt
        if rebalance_day:
            # The engine pays each January's tax from cash; never keep the resulting
            # negative cash (it would be an interest-free loan): rebalance to target.
            pf = ctx._engine.portfolio
            if pf.cash < -1e-6 * max(1.0, ctx.portfolio_value):
                return tgt
            if self.drift is not None:
                cur = _cur_weights(ctx)
                dev = max(abs(cur.get(t, 0.0) - tgt.get(t, 0.0)) for t in set(cur) | set(tgt))
                if dev > self.drift:
                    return tgt
        return None


def _tickers(p: dict) -> list:
    out = [p.get("eq", "VFINXR")]
    if p.get("lev"):
        out.append(p["lev"])
    safe = p.get("safe", ["VFITX", "FGOVX"])
    out += [safe] if isinstance(safe, str) else list(safe)
    tr = p.get("trend")
    if tr and not str(tr.get("sig", "")).startswith("^"):
        out.append(tr["sig"])
    return list(dict.fromkeys(out))


def _factory(p: dict) -> Val:
    return Val(**p)


register_signal("r2_gap2.val", _factory, _tickers)


# --------------------------------------------------------------------------
# kind without the automatically added SPY (synthetic 1928-1985 world)
# --------------------------------------------------------------------------
def _wx_build(c: dict):
    kw = {k: c[k] for k in _WS_KEYS if k in c}
    return WeightStrategy(_factory(c.get("params", {})), **kw)


def _wx_tickers(c: dict) -> list:
    return _tickers(c.get("params", {}))


register_kind("r2_gap2.wx", _wx_build, _wx_tickers)


# --------------------------------------------------------------------------
# protocols on the synthetic world
# --------------------------------------------------------------------------
def _proto(name, sa, sb, step, ca, cb, bench):
    return _core.Protocol(name, tuple(pd.date_range(sa, sb, freq=step)),
                          tuple(pd.date_range(ca, cb, freq="QS")), bench)


_core.PROTOCOLS.setdefault("r2g2_pre", _proto("r2g2_pre", "1930-01-01", "1975-01-01", "YS",
                                              "1930-04-01", "1986-01-01", "R2G2_PEQ"))
_core.PROTOCOLS.setdefault("r2g2_pre_q", _proto("r2g2_pre_q", "1930-01-01", "1980-10-01", "QS",
                                                "1930-04-01", "1986-01-01", "R2G2_PEQ"))
_core.PROTOCOLS.setdefault("r2g2_splice", _proto("r2g2_splice", "1930-01-01", "2016-01-01", "YS",
                                                 "1930-04-01", "2026-07-01", "R2G2_SEQ"))

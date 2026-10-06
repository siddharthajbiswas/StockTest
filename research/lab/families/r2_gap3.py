"""Round 2, gap 3: crash protection that never sells the core (family 'r2_gap3').
Research only -- the website cannot run any of this.

WHAT IS MODELLED
----------------
A taxable account holds an S&P 500 core (SPY; VFINXR on the 1986+ protocol)
that is bought on the first day and never sold except when cash runs out, a
cash reserve that earns T-bills, and an overlay of exchange-listed S&P 500
index options (SPX / XSP: Section 1256 contracts):

* protective puts, put spreads, collars (puts paid for by short calls), on a
  monthly or quarterly roll (CBOE convention: options expire at the SOQ on the
  third Friday; new ones are opened at that day's close);
* optionally only while a condition holds (trend down / VIX below a level);
* a "series" overlay that adds the daily return of a CBOE strategy index over
  the S&P 500 total return (model-free: VXTH = VIX calls, PPUT = 5% puts);
* a short-futures hedge (comparator; the same futures model as r2_gap1).

Option prices: Black-Scholes on the forward with an implied-vol smile anchored to
VIX/VIX3M (pricing inputs of the day of the trade; decisions use only data
available at the decision close).  The smile and a half-spread were calibrated
to 10 CBOE strategy indices (scratch/r2_gap3/calib.py; parameters in
scratch/r2_gap3/out/calib_params*.json).  1986-1989 (no VIX) use a realised-
volatility proxy.

TAX (federal+NIIT and state ledgers, like r2_gap1)
---------------------------------------------------
* Overlay P&L is Section 1256: marked to market on the last trading day of each
  year, 60% long-term / 40% short-term, netted with the year's other gains the
  way the engine nets them; federal 3-year carryback of net 1256 losses
  (IRC 1212(c)); California keeps them as a carryforward.
* tax "T1": the above (the optimistic textbook treatment the critic proposed).
* tax "T2": the STRADDLE rules (IRC 1092) that apply when the hedged asset is an
  S&P 500 fund and the hedge is S&P 500 index options/futures ("substantially
  similar or related property", Reg. 1.246-5): a year's net overlay LOSS is
  deferred to the extent of the core's unrecognised gain at year end (released
  when the core is sold, i.e. at liquidation); gains are taxed at once; core
  lots younger than a year when a hedge is put on lose their holding period
  (their purchase date is reset to the hedge date: approximation of Temp. Reg.
  1.1092(b)-2T).  Hedging normally starts only after `delay` days (366 for T2)
  so the first core lot is long-term first.
* Reserve interest is ordinary income taxed every year (federal; T-bill interest
  is California-exempt).
* The ETF core trades through the engine (5+5 bps, FIFO lots); liquidation at
  every checkpoint mirrors research.lab.core (no exit costs; open options at mid).

RUNNING: run_cfg()/run_many() here (OptBacktest + OptGate); sweep.run cannot run
this kind.  Records have the sweep format, so metrics.summary/report work.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

from backtester import Backtest, Strategy, TaxPolicy

from .. import core, data, registry
from ..registry import register_kind

HERE = Path(__file__).resolve()
LAB = HERE.parents[1]
SCRATCH = LAB / "scratch" / "r2_gap3"
CACHE = SCRATCH / "cache"
CBOE_DIR = SCRATCH / "cboe"

# federal (incl. NIIT where the regime has it) and state parts of each regime
TAXR = {
    "CA": {"fed": (0.388, 0.188), "ord": 0.388, "state": 0.093},
    "FED": {"fed": (0.35, 0.15), "ord": 0.35, "state": 0.0},
    "NONE": None,
}
for _rg in ("CA", "FED"):
    _a = TAXR[_rg]
    assert abs(_a["fed"][0] + _a["state"] - core.REGIMES[_rg][0]) < 1e-12
    assert abs(_a["fed"][1] + _a["state"] - core.REGIMES[_rg][1]) < 1e-12


def policy_for(regime: str):
    if regime == "NONE":
        return None
    r = TAXR[regime]
    return TaxPolicy(short_term_rate=r["fed"][0] + r["state"], long_term_rate=r["fed"][1] + r["state"])


# ==========================================================================
# option model
# ==========================================================================
DEFAULT_PARAMS = {"a": 0.835, "a1": 0.0, "a3": 1.05, "b": 0.207, "b1": 0.0, "cp": 0.026,
                  "cc": 0.068, "h_rel": 0.036, "h_abs": 0.00005}
SKEW_REF = 125.0          # CBOE SKEW reference level for the a1/b1 terms


def load_params(name: str = "full") -> dict:
    p = dict(DEFAULT_PARAMS)
    f = SCRATCH / "out" / ("calib_params.json" if name == "full" else f"calib_params_{name}.json")
    if f.exists():
        p.update(json.loads(f.read_text()))
    return p


def bs(cp, S, K, T, r, q, sig):
    """Black-Scholes price (cp=+1 call, -1 put); vectorised; T in years."""
    S = np.asarray(S, float); K = np.asarray(K, float); T = np.asarray(T, float)
    sig = np.asarray(sig, float); r = np.asarray(r, float); q = np.asarray(q, float)
    shape = np.broadcast(S, K, T, sig, r, q).shape
    S, K, T, sig, r, q = (np.broadcast_to(x, shape).ravel() for x in (S, K, T, sig, r, q))
    out = np.maximum(cp * (S - K), 0.0)
    live = (T > 1e-9) & (sig > 1e-9)
    if np.any(live):
        S_, K_, T_, s_, r_, q_ = S[live], K[live], T[live], sig[live], r[live], q[live]
        sq = s_ * np.sqrt(T_)
        d1 = (np.log(S_ / K_) + (r_ - q_ + 0.5 * s_ * s_) * T_) / sq
        d2 = d1 - sq
        dfq, dfr = np.exp(-q_ * T_), np.exp(-r_ * T_)
        if cp > 0:
            v = S_ * dfq * ndtr(d1) - K_ * dfr * ndtr(d2)
        else:
            v = K_ * dfr * ndtr(-d2) - S_ * dfq * ndtr(-d1)
        out[live] = v
    return out.reshape(shape) if shape else float(out[0])


def bs_delta(cp, S, K, T, r, q, sig):
    sq = sig * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sig * sig) * T) / sq
    return np.exp(-q * T) * (ndtr(d1) if cp > 0 else ndtr(d1) - 1.0)


def atm_vol(T, vix, vix3m, p, skew=SKEW_REF):
    T = np.asarray(T, float)
    t1, t3 = 30.0 / 365.0, 91.0 / 365.0
    a = p["a"] + p.get("a1", 0.0) * (np.asarray(skew, float) - SKEW_REF) / 10.0
    v1 = a * np.asarray(vix, float)
    v3 = a * p.get("a3", 1.0) * np.asarray(vix3m, float)
    w1, w3 = v1 * v1 * t1, v3 * v3 * t3
    w = np.where(T <= t1, v1 * v1 * T,
                 np.where(T >= t3, v3 * v3 * T, w1 + (w3 - w1) * (T - t1) / (t3 - t1)))
    return np.sqrt(np.maximum(w, 1e-12) / np.maximum(T, 1e-9))


def iv(K, S, T, r, q, vix, vix3m, p, skew=SKEW_REF):
    sa = atm_vol(T, vix, vix3m, p, skew)
    F = S * np.exp((r - q) * T)
    z = np.log(K / F) / (sa * np.sqrt(np.maximum(T, 1e-9)))
    b = p["b"] + p.get("b1", 0.0) * (np.asarray(skew, float) - SKEW_REF) / 10.0
    m = 1.0 - b * z + np.where(z < 0, p["cp"], p["cc"]) * z * z
    return sa * np.clip(m, 0.5, 4.0)


def price(cp, K, S, T, r, q, vix, vix3m, p, skew=SKEW_REF):
    return bs(cp, S, K, T, r, q, iv(K, S, T, r, q, vix, vix3m, p, skew))


def trade_price(mid, S, side, p):
    """Price paid for one option when buying (side > 0) / received when selling."""
    if side > 0:
        return mid * (1.0 + p["h_rel"]) + p["h_abs"] * S
    return np.maximum(mid * (1.0 - p["h_rel"]) - p["h_abs"] * S, 0.0)


def pick_strike(S, pct, mode="below", grid=5.0):
    x = S * pct / grid
    if mode == "below":
        return float(np.floor(x + 1e-9) * grid)
    if mode == "above":
        return float(np.ceil(x - 1e-9) * grid)
    return float(np.round(x) * grid)


def roll_days(idx: pd.DatetimeIndex) -> np.ndarray:
    """Positions of the monthly SPX expirations: third Friday of each month (the
    preceding trading day if that Friday is a holiday)."""
    out = []
    for mth in pd.period_range(idx[0], idx[-1], freq="M"):
        d = mth.start_time
        tf = d + pd.Timedelta(days=(4 - d.weekday()) % 7 + 14)
        j = int(idx.searchsorted(tf, side="right")) - 1
        if j >= 0 and idx[j].to_period("M") == mth and (tf - idx[j]).days < 7:
            out.append(j)
    return np.array(sorted(set(out)), dtype=int)


# --------------------------------------------------------------------------
# market inputs on a calendar
# --------------------------------------------------------------------------
def _spxtr() -> pd.Series:
    tr = data.frame("^SP500TR", end=None)["Close"].astype(float)
    v = data.frame("VFINXR", end=None)["Close"].astype(float)
    t0 = tr.index[0]
    rv = (v.pct_change() + 0.0020 / 252).dropna()
    rt = tr.pct_change().dropna()
    r = pd.concat([rv[rv.index <= t0], rt[rt.index > t0]]).sort_index()
    lvl = (1.0 + r).cumprod()
    lvl = lvl * (tr.loc[t0] / lvl.loc[t0])
    first = pd.Series([lvl.iloc[0] / (1.0 + r.iloc[0])], index=[v.index[0]])
    return pd.concat([first, lvl]).sort_index()


USE_VIXIMP = True


@lru_cache(maxsize=4)
def _inputs_gspc() -> pd.DataFrame:
    g = data.frame("^GSPC", end=None)
    S = g["Close"].astype(float)
    S = S[S.index >= pd.Timestamp("1984-01-01")]
    O = g["Open"].astype(float).reindex(S.index)
    spy = data.frame("SPY", end=None)
    gap = (spy["Open"] / spy["Close"].shift(1)).reindex(S.index)
    stale = (O - S.shift(1)).abs() < 1e-6
    use_spy = stale & gap.notna() & (S.index >= pd.Timestamp("1993-02-01"))
    O = O.where(~use_spy, S.shift(1) * gap)
    tr = _spxtr().reindex(S.index).ffill()
    irx = data.frame("^IRX", end=None)["Close"].astype(float).reindex(S.index).ffill()
    r = np.log1p(irx / 100.0)
    q = (np.log(tr) - np.log(S)).diff(252).clip(lower=0.0).bfill()
    vix = data.frame("^VIX", end=None)["Close"].astype(float).reindex(S.index)
    v3 = data.frame("^VIX3M", end=None)["Close"].astype(float).reindex(S.index)
    lr = np.log(S).diff()
    rv21 = lr.rolling(21).std() * np.sqrt(252)
    rv63 = lr.rolling(63).std() * np.sqrt(252)
    X = pd.DataFrame({"l21": np.log(rv21), "l63": np.log(rv63), "y": np.log(vix / 100.0)}).dropna()
    A = np.c_[np.ones(len(X)), X.l21.values, X.l63.values]
    coef, *_ = np.linalg.lstsq(A, X.y.values, rcond=None)
    proxy = np.exp(coef[0] + coef[1] * np.log(rv21) + coef[2] * np.log(rv63)) * 100.0
    is_proxy = vix.isna()
    # 1986-1989: implied level backed out of CBOE PPUT/BXMD roll returns
    # (scratch/r2_gap3/imp8689.py) where available, else the realised-vol proxy
    fimp = data.EXTRA_DIR / "R2G3_VIXIMP.csv"
    if USE_VIXIMP and fimp.exists():
        imp = pd.read_csv(fimp, parse_dates=["Date"], index_col="Date")["Close"].astype(float)
        vix = vix.fillna(imp.reindex(S.index))
    vix = vix.fillna(proxy).ffill()
    Y = pd.DataFrame({"v": vix, "v3": v3}).dropna()
    B = np.c_[np.ones(len(Y)), Y.v.values, Y.v.values ** 2]
    c3, *_ = np.linalg.lstsq(B, Y.v3.values, rcond=None)
    v3 = v3.fillna(c3[0] + c3[1] * vix + c3[2] * vix ** 2).ffill()
    sk = cboe_series("SKEW").reindex(S.index)
    pre = float(sk.loc["1990-01-01":"1994-12-31"].mean())
    sk = sk.ffill().fillna(pre)
    df = pd.DataFrame({"S": S, "O": O, "TR": tr, "r": r, "q": q, "vix": vix / 100.0,
                       "vix3m": v3 / 100.0, "skew": sk, "proxy": is_proxy.astype(float),
                       "vix_rvproxy": proxy / 100.0})
    return df


class Inputs:
    """Option-model inputs aligned to an engine calendar (forward filled)."""

    def __init__(self, calendar: pd.DatetimeIndex):
        df = _inputs_gspc().reindex(calendar).ffill()
        self.idx = calendar
        for c in df.columns:
            setattr(self, c, df[c].to_numpy(dtype=float))
        self.dord = np.array([d.toordinal() for d in calendar], dtype=float)
        self.ok = ~np.isnan(self.S)
        self.rolls = roll_days(calendar)
        self.roll_pos = {int(j): k for k, j in enumerate(self.rolls)}

    def tau(self, i: int, j_exp: int) -> float:
        return max(self.dord[j_exp] - self.dord[i] - 0.27, 0.0) / 365.0


_INPUTS: dict = {}


def inputs_for(calendar: pd.DatetimeIndex) -> Inputs:
    key = (len(calendar), str(calendar[0]), str(calendar[-1]))
    x = _INPUTS.get(key)
    if x is None:
        x = _INPUTS[key] = Inputs(calendar)
    return x


# --------------------------------------------------------------------------
# CBOE strategy indices (model-free overlays)
# --------------------------------------------------------------------------
@lru_cache(maxsize=16)
def cboe_series(name: str) -> pd.Series:
    f = data.EXTRA_DIR / f"R2G3_{name}.csv"
    if f.exists():
        df = pd.read_csv(f, parse_dates=["Date"], index_col="Date")
        return df["Close"].astype(float)
    df = pd.read_csv(CBOE_DIR / f"{name}.csv")
    df.columns = [c.strip().upper() for c in df.columns]
    df["DATE"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
    col = "CLOSE" if "CLOSE" in df.columns else df.columns[1]
    s = df.set_index("DATE")[col].astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def series_rel_returns(name: str, calendar: pd.DatetimeIndex) -> np.ndarray:
    """Daily return of CBOE index `name` minus the S&P 500 total return, on the
    engine calendar (0 where the index has no value)."""
    s = cboe_series(name)
    tr = _spxtr()
    j = s.index.intersection(tr.index)
    rel = (s.loc[j].pct_change() - tr.loc[j].pct_change()).dropna()
    out = rel.reindex(calendar).fillna(0.0).to_numpy()
    first = s.index[0]
    ok = np.asarray(calendar > first)
    return out, ok


# ==========================================================================
# tax ledger
# ==========================================================================
def _net(st: float, lt: float, carry: float):
    """The engine's netting: one loss pool, applied to short-term gains first."""
    pool = carry + max(0.0, -st) + max(0.0, -lt)
    gs, gl = max(0.0, st), max(0.0, lt)
    u = min(pool, gs); gs -= u; pool -= u
    u = min(pool, gl); gl -= u; pool -= u
    return gs, gl, pool


class Ledger:
    """Federal (+NIIT) and state ledgers: Section 1256 mark-to-market 60/40,
    federal 3-year carryback, yearly interest tax and (tax="T2") the straddle
    loss deferral.  Adapted from r2_gap1.Ledger (same netting conventions)."""

    def __init__(self, regime: str, carryback: bool = True, straddle: bool = False):
        r = TAXR[regime]
        self.fst, self.flt = r["fed"]
        self.ford = r["ord"]
        self.srate = r["state"]
        self.carryback = carryback
        self.straddle = straddle
        self.pool_f = 0.0
        self.pool_s = 0.0
        self.cf1256 = 0.0
        self.deferred = 0.0           # straddle-deferred overlay losses (magnitude)
        self.hist: dict = {}
        self.f1256 = defaultdict(float)
        self.interest = defaultdict(float)
        self.core_unrec: dict = {}    # year -> core unrecognised gain at year end (T2)
        self.log: list = []

    def _ftax(self, s, l):
        return s * self.fst + l * self.flt

    def year(self, y: int, st_o: float, lt_o: float, unreal=None, commit: bool = False,
             f_extra: float = 0.0):
        f = self.f1256.get(y, 0.0) + f_extra
        it = self.interest.get(y, 0.0)
        deferred_out = 0.0
        if self.straddle:
            f_raw = f - self.deferred
            if unreal is None and f_raw < 0.0:
                cu = max(0.0, self.core_unrec.get(y, 0.0))
                allowed = max(0.0, -f_raw - cu)
                deferred_out = -f_raw - allowed
                f = -allowed
            else:
                f = f_raw
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
            L = min(max(0.0, p2 - self.pool_f), loss)
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
        tax_i = max(0.0, it) * self.ford
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
            self.deferred = deferred_out
            self.hist[y] = [ts, tl, max(0.0, f_tot)]
            self.log.append({"year": y, "st_o": st_o, "lt_o": lt_o, "f1256": self.f1256.get(y, 0.0),
                             "f_used": f, "deferred": deferred_out, "interest": it,
                             "tax_cap_fed": tax_f, "tax_int": tax_i, "tax_state": tax_s,
                             "refund": refund, "cf1256": rem, "pool_f": self.pool_f, "pool_s": self.pool_s})
        return tax, refund


# ==========================================================================
# the options book: per-roll legs, independent of the portfolio
# ==========================================================================
class Book:
    """Lazily computed option legs for a config on an Inputs calendar.

    leg spec: {"cp": -1|1, "side": 1|-1, "tenor": months to expiry (1, 2, 3, 6),
               "every": open a new one every N months (1 or 3; default = tenor if
               tenor>=3 and roll 'Q' else 1), "K": ["pct", 0.95, "below"] |
               ["delta", -0.25] | ["match"] (call strike whose premium pays for
               the other legs), "q": contracts per unit of hedged notional}
    """

    def __init__(self, inp: Inputs, legs: list, p: dict):
        self.inp = inp
        self.legs = legs
        self.p = p
        self._cache: dict = {}

    def expiry(self, k: int, tenor: int) -> int | None:
        r = self.inp.rolls
        kk = k + int(tenor)
        if kk >= len(r):
            return None
        return int(r[kk])

    def due(self, k: int, leg: dict) -> bool:
        every = int(leg.get("every", 1))
        if every <= 1:
            return True
        m = self.inp.idx[self.inp.rolls[k]].month
        return (m % every) == (3 % every)          # quarterly cycle: Mar/Jun/Sep/Dec

    def get(self, k: int):
        """For roll k: list of (leg_index, K, j_exp, path, trade_px) for the legs
        due that month (path = mids from the roll close to the day before expiry,
        then the SOQ settlement value)."""
        hit = self._cache.get(k)
        if hit is not None:
            return hit
        inp, p = self.inp, self.p
        i = int(inp.rolls[k])
        S = inp.S[i]
        out = []
        ks = {}
        for n, lg in enumerate(self.legs):
            if not self.due(k, lg):
                continue
            j = self.expiry(k, lg.get("tenor", 1))
            if j is None:
                continue
            rule = lg["K"]
            T = inp.tau(i, j)
            if rule[0] == "pct":
                K = pick_strike(S, rule[1], rule[2] if len(rule) > 2 else "nearest")
            elif rule[0] == "delta":
                g = 5.0
                grid = np.arange(np.floor(S * 0.4 / g) * g, np.ceil(S * 1.6 / g) * g + g, g)
                sig = iv(grid, S, T, inp.r[i], inp.q[i], inp.vix[i], inp.vix3m[i], p, inp.skew[i])
                d = bs_delta(lg["cp"], S, grid, T, inp.r[i], inp.q[i], sig)
                K = float(grid[int(np.argmin(np.abs(d - rule[1])))])
            else:
                K = None
            ks[n] = (K, j, T)
        # "match" legs: call strike whose sale pays for the rest
        for n, (K, j, T) in list(ks.items()):
            if K is not None:
                continue
            debit = 0.0
            for n2, (K2, j2, T2) in ks.items():
                if n2 == n or K2 is None:
                    continue
                lg2 = self.legs[n2]
                mid = price(lg2["cp"], K2, S, T2, inp.r[i], inp.q[i], inp.vix[i], inp.vix3m[i], p,
                            inp.skew[i])
                debit += lg2["side"] * lg2.get("q", 1.0) * trade_price(mid, S, lg2["side"], p)
            g = 5.0
            grid = np.arange(np.ceil(S / g) * g, S * 1.6, g)
            mids = price(+1, grid, S, T, inp.r[i], inp.q[i], inp.vix[i], inp.vix3m[i], p, inp.skew[i])
            proceeds = trade_price(mids, S, -1, p) * self.legs[n].get("q", 1.0)
            ok = np.nonzero(proceeds >= debit)[0]
            ks[n] = (float(grid[ok[-1]]) if len(ok) else float(grid[0]), j, T)
        for n, (K, j, T) in ks.items():
            lg = self.legs[n]
            ii = np.arange(i, j)
            Tt = np.maximum(inp.dord[j] - inp.dord[ii] - 0.27, 0.0) / 365.0
            mids = price(lg["cp"], K, inp.S[ii], Tt, inp.r[ii], inp.q[ii], inp.vix[ii], inp.vix3m[ii], p,
                         inp.skew[ii])
            soq = inp.O[j] if np.isfinite(inp.O[j]) and inp.O[j] > 0 else inp.S[j - 1]
            settle = max(0.0, lg["cp"] * (soq - K))
            path = np.r_[mids, settle]
            tp = float(trade_price(path[0], S, lg["side"], p))
            out.append((n, K, j, path, tp))
        self._cache[k] = out
        return out


_BOOKS: dict = {}


def book_for(inp: Inputs, legs: list, pname: str) -> Book:
    key = (id(inp), json.dumps(legs, sort_keys=True), pname)
    b = _BOOKS.get(key)
    if b is None:
        b = _BOOKS[key] = Book(inp, legs, load_params(pname))
    return b


# ==========================================================================
# the engine subclass
# ==========================================================================
class Position:
    __slots__ = ("leg", "K", "cp", "qty", "basis", "j0", "jexp", "path", "side")

    def __init__(self, leg, K, cp, qty, basis, j0, jexp, path, side):
        self.leg, self.K, self.cp, self.qty, self.basis = leg, K, cp, qty, basis
        self.j0, self.jexp, self.path, self.side = j0, jexp, path, side

    def mid(self, i: int) -> float:
        return float(self.path[min(i, self.jexp) - self.j0])


class OptBacktest(Backtest):
    """backtester.Backtest + an options book, a series overlay, a futures hedge,
    interest on cash and the Ledger taxes."""

    def __init__(self, strategy, market, regime: str, cfg: dict, comm=core.COMMISSION,
                 slip=core.SLIPPAGE, cash=core.CASH):
        super().__init__(strategy, market=market, cash=cash, commission_pct=comm,
                         slippage_pct=slip, tax_policy=policy_for(regime))
        self.regime = regime
        tax = cfg.get("tax", "T1")
        self.tax_mode = tax
        self.ledger = None if regime == "NONE" else Ledger(
            regime, carryback=(tax != "T1nocb" and cfg.get("carryback", True)), straddle=(tax == "T2"))
        self.inp = inputs_for(market.calendar)
        self.book = book_for(self.inp, cfg.get("legs", []), cfg.get("params", "full")) if cfg.get("legs") else None
        cal = market.calendar
        fin = data.frame("^IRX")["Close"].astype(float)
        full = fin.reindex(fin.index.union(cal)).ffill()
        self.rB = ((full.shift(1).reindex(cal) / 100.0 - cfg.get("bill_fee", 0.001)) / 252.0).fillna(0.0).to_numpy()
        self.positions: list[Position] = []
        self.ser = None
        if cfg.get("series"):
            self.ser, self.ser_ok = series_rel_returns(cfg["series"]["name"], cal)
        self.ser_notional = 0.0
        self.fut = cfg.get("fut")
        self.fut_notional = 0.0
        self.lev = cfg.get("lev")            # long futures (hedged-leverage variants)
        self.lev_notional = 0.0
        if self.fut or self.lev:
            ct = cfg.get("core", "SPY")
            u = data.frame(ct)["Close"].astype(float).reindex(cal).ffill()
            ru = u.pct_change().fillna(0.0).to_numpy()
            self.rF = ru - (full.shift(1).reindex(cal) / 100.0 / 252.0).fillna(0.0).to_numpy() \
                - (self.fut or self.lev).get("basis", 0.002) / 252.0
            self.rF[0] = 0.0
        self.bond = (self.fut or {}).get("bond")     # long Treasury futures while hedged
        self.bond_notional = 0.0
        if self.bond:
            # excess return of an intermediate-Treasury fund over T-bills (IEF;
            # VFITX before IEF existed; FGOVX before VFITX -- the round-1 safe
            # chain) minus a roll/basis cost; zero excess where none exists
            bill = (full.shift(1).reindex(cal) / 100.0 / 252.0).fillna(0.0)
            rb = pd.Series(np.nan, index=cal)
            for t in ("FGOVX", "VFITX", "IEF"):          # later funds override earlier ones
                x = data.frame(t)["Close"].astype(float).reindex(cal)
                ok = x.notna() & x.shift(1).notna()
                rb = rb.where(~ok, x.pct_change())
            rb = rb.fillna(bill)
            self.rBd = (rb - bill).to_numpy() - self.bond.get("basis", 0.001) / 252.0
            self.rBd[0] = 0.0
        self.interest_on = False
        last = np.r_[cal.year[1:] != cal.year[:-1], False]
        self.year_end = last
        # statistics
        self.st = defaultdict(float)

    # ---- option API used by the strategy -------------------------------------
    def roll_k(self) -> int | None:
        return self.inp.roll_pos.get(self._i)

    def book_value(self) -> float:
        i = self._i
        return sum(p.qty * p.mid(i) for p in self.positions)

    def open_legs(self, k: int, notional: float, scale: float = 1.0) -> float:
        """Open the legs due at roll k for `notional` dollars of S&P exposure;
        returns the net premium paid (negative = received)."""
        if self.book is None or notional <= 0:
            return 0.0
        i = self._i
        S = self.inp.S[i]
        paid = 0.0
        for n, K, j, path, tp in self.book.get(k):
            lg = self.book.legs[n]
            qty = lg["side"] * lg.get("q", 1.0) * notional / S * scale
            if abs(qty) < 1e-12:
                continue
            cost = qty * tp
            self.portfolio.cash -= cost
            paid += cost
            # spread cost already inside tp; record for statistics
            self.st["spread_cost"] += abs(qty) * abs(tp - path[0])
            self.positions.append(Position(n, K, lg["cp"], qty, tp, i, j, path, lg["side"]))
            if cost > 0:
                self.st["premium_paid"] += cost
            else:
                self.st["premium_recv"] += -cost
        return paid

    def quote_legs(self, k: int, notional: float) -> float:
        """Net premium that open_legs(k, notional) would pay (no trade)."""
        if self.book is None or notional <= 0:
            return 0.0
        S = self.inp.S[self._i]
        return sum(self.book.legs[n]["side"] * self.book.legs[n].get("q", 1.0) * notional / S * tp
                   for n, K, j, path, tp in self.book.get(k))

    def hedged(self) -> bool:
        return any(p.side > 0 and p.cp < 0 for p in self.positions) or self.fut_notional > 0 \
            or self.ser_notional > 0

    def set_lev(self, x: float) -> None:
        d = abs(x - self.lev_notional)
        if d < self.min_order_value:
            return
        c = d * self.lev.get("cost", 0.0002)
        self.portfolio.cash -= c
        if self.ledger is not None:
            self.ledger.f1256[self._date.year] -= c
        self.lev_notional = x
        self.st["lev_trades"] += 1

    def set_bond(self, x: float) -> None:
        d = abs(x - self.bond_notional)
        if d < self.min_order_value:
            return
        c = d * self.bond.get("cost", 0.0001)
        self.portfolio.cash -= c
        if self.ledger is not None:
            self.ledger.f1256[self._date.year] -= c
        self.bond_notional = x

    def constructive_sale(self, ticker: str) -> None:
        """IRC 1259 deemed sale of every appreciated lot of `ticker` at today's
        close (net of selling costs, as the engine nets a sale): the gain is
        realised now (short/long-term by lot age) and the lot restarts with a
        basis equal to the deemed price and a new holding period."""
        pf = self.portfolio
        px = self.today_prices.get(ticker)
        if px is None or self.tax_policy is None:
            return
        net = px * (1.0 - self.slippage_pct) * (1.0 - pf.commission_pct)
        for lot in pf.lots.get(ticker, []):
            g = (net - lot.cost_per_share) * lot.shares
            if g <= 0:
                continue
            lt = self.tax_policy.is_long_term((self._date - lot.date).days)
            pf._record_realized(self._date.year, g, lt)
            lot.cost_per_share = net
            lot.date = self._date
            self.st["cs_gain"] += g

    def set_fut(self, x: float) -> None:
        d = abs(x - self.fut_notional)
        if d < self.min_order_value:
            return
        c = d * self.fut.get("cost", 0.0002)
        self.portfolio.cash -= c
        if self.ledger is not None:
            self.ledger.f1256[self._date.year] -= c
        self.fut_notional = x
        self.st["fut_trades"] += 1

    # ---- liquidation value now -----------------------------------------------
    def _open_mtm(self) -> float:
        i = self._i
        return sum(p.qty * (p.mid(i) - p.basis) for p in self.positions)

    def liq_value(self) -> tuple[float, float]:
        pf = self.portfolio
        prices = self.current_prices()
        equity = pf.cash + pf.holdings_value(prices) + self.book_value()
        if self.ledger is None:
            return equity, equity
        y = self._date.year
        r = pf.realized.get(y, {"st": 0.0, "lt": 0.0})
        st_u, lt_u = pf.unrealized_gains(self._date, prices, self.tax_policy)
        tax, refund = self.ledger.year(y, r["st"], r["lt"], unreal=(st_u, lt_u), commit=False,
                                       f_extra=self._open_mtm())
        return equity - tax + refund, equity

    def _core_unrec(self) -> float:
        pf = self.portfolio
        prices = self.current_prices()
        st_u, lt_u = pf.unrealized_gains(self._date, prices, self.tax_policy)
        return st_u + lt_u

    # ---- the day loop ----------------------------------------------------------
    def run(self):
        from backtester.result import Result
        self.strategy.initialize(self.ctx)
        market = self.market
        calendar = self.calendar
        cal_values = market.cal_values
        n = market.n
        eq_c, eq_h, eq_t = [], [], []
        led = self.ledger
        prev_year = None
        taxes_paid = 0.0
        cash_prev = self.portfolio.cash
        cal_list = list(calendar)
        for i in range(n):
            self._i = i
            self._dv = cal_values[i]
            date = cal_list[i]
            self._date = date
            self.today_prices = market.today_tradable[i]
            # 1) overnight: interest on cash, series overlay, futures variation margin
            if i > 0:
                if self.interest_on and cash_prev != 0.0:
                    it = cash_prev * self.rB[i]
                    self.portfolio.cash += it
                    self.st["interest"] += it
                    if led is not None:
                        led.interest[date.year] += it
                if self.ser is not None and self.ser_notional != 0.0:
                    pnl = self.ser_notional * self.ser[i]
                    self.portfolio.cash += pnl
                    self.st["series_pnl"] += pnl
                    if led is not None:
                        led.f1256[date.year] += pnl
                if self.lev and self.lev_notional != 0.0:
                    pnl = self.lev_notional * self.rF[i]
                    self.portfolio.cash += pnl
                    self.st["lev_pnl"] += pnl
                    if led is not None:
                        led.f1256[date.year] += pnl
                    self.lev_notional *= 1.0 + self.rF[i]
                if self.bond and self.bond_notional != 0.0:
                    pnl = self.bond_notional * self.rBd[i]
                    self.portfolio.cash += pnl
                    self.st["bond_pnl"] += pnl
                    if led is not None:
                        led.f1256[date.year] += pnl
                    self.bond_notional *= 1.0 + self.rBd[i]
                if self.fut and self.fut_notional != 0.0:
                    pnl = -self.fut_notional * self.rF[i]
                    self.portfolio.cash += pnl
                    self.st["fut_pnl"] += pnl
                    if led is not None:
                        led.f1256[date.year] += pnl
                    self.fut_notional *= 1.0 + self.rF[i]
            # 2) last year's taxes on the first trading day of a new year
            if led is not None and prev_year is not None and date.year != prev_year:
                r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
                tax, refund = led.year(prev_year, r["st"], r["lt"], commit=True)
                self.portfolio.cash -= tax - refund
                taxes_paid += tax - refund
                self.st["refunds"] += refund
            prev_year = date.year
            # 3) expiring options settle at the SOQ
            if self.positions:
                keep = []
                for p in self.positions:
                    if p.jexp == i:
                        v = p.qty * p.path[-1]
                        self.portfolio.cash += v
                        g = p.qty * (p.path[-1] - p.basis)
                        self.st["opt_pnl"] += g
                        if p.qty > 0:
                            self.st["payoff_long"] += v
                        else:
                            self.st["payoff_short"] += -v
                        if led is not None:
                            led.f1256[date.year] += g
                    else:
                        keep.append(p)
                self.positions = keep
            # 4) the strategy (orders fill at today's close)
            self.ctx.date = date
            self.strategy.on_day(self.ctx)
            # 5) year end: Section 1256 mark to market (and the core's unrecognised gain)
            if self.year_end[i]:
                if led is not None:
                    for p in self.positions:
                        m = p.mid(i)
                        led.f1256[date.year] += p.qty * (m - p.basis)
                        p.basis = m
                    if led.straddle:
                        led.core_unrec[date.year] = self._core_unrec()
            cash_prev = self.portfolio.cash
            holdings = self.portfolio.holdings_value(self.current_prices())
            bv = self.book_value() if self.positions else 0.0
            eq_c.append(cash_prev)
            eq_h.append(holdings + bv)
            eq_t.append(cash_prev + holdings + bv)
        equity = pd.DataFrame({"cash": eq_c, "holdings": eq_h, "total": eq_t},
                              index=pd.DatetimeIndex(calendar, name="date"))
        trades = pd.DataFrame([t.as_dict() for t in self.portfolio.trades])
        if not trades.empty:
            trades = trades.set_index("date")
        terminal_tax = None
        if led is not None:
            r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
            st_u, lt_u = self.portfolio.unrealized_gains(self._date, self.current_prices(), self.tax_policy)
            tax, refund = led.year(prev_year, r["st"], r["lt"], unreal=(st_u, lt_u), commit=False,
                                   f_extra=self._open_mtm())
            terminal_tax = tax - refund
        return Result(equity=equity, trades=trades, starting_cash=self.starting_cash,
                      taxes_paid=(taxes_paid if led is not None else None), terminal_tax=terminal_tax)


class OptGate(core.Gate):
    """core.Gate whose checkpoint values come from OptBacktest.liq_value."""

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


# ==========================================================================
# the strategy
# ==========================================================================
class Cond:
    """When may new hedge legs be opened (evaluated on roll days)?

    {"type": "trend", "n": 200, "band": 0.0, "ma": "sma"|"ema", "when": "off"|"on", "lag": 0}
        daily hysteresis state on the core's total-return close vs its moving
        average (the trend rules' convention: today's close decides today's
        trade; lag=1 uses yesterday's close); "off" = hedge while the trend is down
    {"type": "vix", "max": 20} / {"type": "vix", "min": 20}: VIX at the previous close
    """

    def __init__(self, spec: dict | None, core_ticker: str):
        self.spec = spec or None
        self.core = core_ticker
        self.state = None
        self.ema = None
        self.ema_n = 0
        self.tt = None
        if self.spec and self.spec.get("type") == "tt":
            # the round-1 trend_timing signal itself (identical state machine)
            from .trend_timing import Timing
            prm = dict(self.spec.get("params", {}))
            prm["risk"] = core_ticker
            prm.pop("safe", None)
            self.tt = Timing(**prm)
        self._tt_init = False

    def _margin(self, ctx):
        from ..blocks import np_closes
        s = self.spec
        n = int(s.get("n", 200))
        lag = int(s.get("lag", 0))
        if s.get("ma") == "ema":
            a = 2.0 / (n + 1.0)
            if self.ema is None:
                c = np_closes(ctx, self.core, 4 * n + lag)
                if lag:
                    c = c[:-lag] if len(c) > lag else c[:0]
                if len(c) < 2 * n:
                    return None
                e = float(c[0])
                for v in c[1:]:
                    e = a * float(v) + (1.0 - a) * e
                self.ema = e
                self.last = float(c[-1])
            else:
                c = np_closes(ctx, self.core, 1 + lag)
                x = float(c[0]) if lag else float(c[-1])
                self.ema = a * x + (1.0 - a) * self.ema
                self.last = x
            return self.last / self.ema - 1.0
        c = np_closes(ctx, self.core, n + lag)
        if lag:
            c = c[:-lag] if len(c) > lag else c[:0]
        if len(c) < n:
            return None
        return c[-1] / c.mean() - 1.0

    def update(self, ctx) -> None:
        s = self.spec
        if s and s.get("type") == "tt":
            if not self._tt_init:
                self.tt.initialize(ctx)
                self._tt_init = True
            self.state = self.tt.exposure(ctx) > 0.5
            return
        if not s or s.get("type") != "trend":
            return
        m = self._margin(ctx)
        if m is None:
            return
        b = float(s.get("band", 0.0))
        if self.state is None:
            self.state = m > 0
        elif m > b:
            self.state = True
        elif m < -b:
            self.state = False

    def ok(self, ctx) -> bool:
        s = self.spec
        if not s:
            return True
        if s["type"] in ("trend", "tt"):
            if self.state is None:
                return False
            up = self.state
            return (not up) if s.get("when", "off") == "off" else up
        if s["type"] == "vix":
            eng = ctx._engine
            v = eng.inp.vix[eng._i - 1] * 100.0 if eng._i > 0 else np.nan
            if not np.isfinite(v):
                return False
            if "max" in s and v >= s["max"]:
                return False
            if "min" in s and v < s["min"]:
                return False
            return True
        raise ValueError(s)


class OverlayStrategy(Strategy):
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.core = cfg.get("core", "SPY")
        self.r0 = float(cfg.get("r0", 0.03))
        self.cap = float(cfg.get("cap", max(2 * self.r0, 0.01)))
        self.fund = cfg.get("fund", "core")
        self.h = float(cfg.get("h", 1.0))
        self.budget = cfg.get("budget")
        self.delay = int(cfg.get("delay", 366 if cfg.get("tax") == "T2" else 0))
        self.cond = Cond(cfg.get("cond"), self.core)
        self.ser = cfg.get("series")
        self.fut = cfg.get("fut")
        self.fcond = Cond((self.fut or {}).get("cond"), self.core) if self.fut else None
        self.lev = cfg.get("lev")
        self.lcond = Cond((self.lev or {}).get("cond"), self.core) if self.lev else None
        self.h_on = cfg.get("h_on", "core")          # hedge notional base: core | exposure

    def initialize(self, ctx):
        self.started = None
        self.n_hedge_rolls = 0
        self.n_rolls = 0
        self.hedge_frac_sum = 0.0
        self.core_sales = 0
        self.sweeps = 0

    # helpers
    def _px(self, ctx):
        return ctx.price(self.core)

    def _core_value(self, ctx):
        px = self._px(ctx)
        return ctx.shares(self.core) * px if px else 0.0

    def _equity(self, ctx):
        eng = ctx._engine
        return eng.portfolio.cash + self._core_value(ctx) + eng.book_value()

    def _buy_core(self, ctx, amount):
        px = self._px(ctx)
        if px and amount > 1.0:
            ctx.order(self.core, amount / (px * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)) * 0.999999)

    def _sell_core(self, ctx, amount):
        px = self._px(ctx)
        if px and amount > 0:
            q = min(ctx.shares(self.core), amount / (px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)))
            if q > 0:
                ctx.order(self.core, -q)
                self.core_sales += 1

    def _reset_young_lots(self, ctx):
        """T2: core lots younger than the long-term period lose their holding period
        while a hedge is on (the purchase date moves to today)."""
        lots = ctx._engine.portfolio.lots.get(self.core, [])
        for lot in lots:
            if not ctx.is_long_term(lot.date):
                lot.date = ctx.date

    def on_day(self, ctx):
        eng = ctx._engine
        if self.started is None:
            if self._px(ctx) is None:
                return
            self.started = ctx.date
            eng.interest_on = True
            if self.r0 <= 0.0:
                ctx.order_target_percent(self.core, 1.0)      # exactly the lab's BuyHoldOne
            else:
                px = self._px(ctx)
                ctx.order(self.core, eng.portfolio.cash * (1.0 - self.r0)
                          / (px * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)))
        self.cond.update(ctx)
        if self.fcond is not None:
            self.fcond.update(ctx)
        if self.lcond is not None:
            self.lcond.update(ctx)
        k = eng.roll_k()
        if k is not None:
            self.n_rolls += 1
            pv = self._equity(ctx)
            cash = eng.portfolio.cash
            # monetise: sweep surplus cash into the core
            if cash > self.cap * pv:
                self._buy_core(ctx, cash - self.r0 * pv)
                self.sweeps += 1
            active = (ctx.date - self.started).days >= self.delay
            # long-futures leverage: notional reset on roll days
            if self.lev:
                lon = self.lcond.ok(ctx)
                eng.set_lev(float(self.lev.get("x", 0.5)) * self._core_value(ctx) if lon else 0.0)
            if eng.book is not None and active and self.cond.ok(ctx):
                N = self.h * (self._core_value(ctx) + (eng.lev_notional if self.h_on == "exposure" else 0.0))
                debit = eng.quote_legs(k, N)
                scale = 1.0
                lim = None
                if self.budget is not None:
                    lim = float(self.budget) * pv
                if self.fund == "reserve":
                    avail = max(0.0, eng.portfolio.cash)
                    lim = avail if lim is None else min(lim, avail)
                if lim is not None and debit > lim:
                    scale = max(0.0, lim / debit) if debit > 0 else 1.0
                if scale > 1e-6:
                    if eng.tax_mode == "T2":
                        self._reset_young_lots(ctx)
                    eng.open_legs(k, N, scale)
                    self.n_hedge_rolls += 1
                    self.hedge_frac_sum += scale
            # model-free series overlay: notional reset monthly
            if self.ser:
                on = active and self.cond.ok(ctx)
                if self.fund == "reserve" and eng.portfolio.cash <= 0:
                    on = False
                if on and eng.tax_mode == "T2":
                    self._reset_young_lots(ctx)
                eng.ser_notional = float(self.ser.get("h", 1.0)) * self._core_value(ctx) if on else 0.0
        # futures hedge: state can change any day; notional reset on change / roll days
        if self.fut:
            active = (ctx.date - self.started).days >= self.delay
            want = active and self.fcond.ok(ctx)
            tgt = float(self.fut.get("h", 1.0)) * self._core_value(ctx) if want else 0.0
            if (want != (eng.fut_notional > 0)) or (k is not None and want):
                if want and eng.tax_mode == "T2":
                    self._reset_young_lots(ctx)
                if want and eng.fut_notional <= 0 and self.fut.get("cs") and eng.tax_mode != "NONE":
                    eng.constructive_sale(self.core)        # IRC 1259 deemed sale on entry
                eng.set_fut(tgt)
                if eng.bond:
                    eng.set_bond(float(eng.bond.get("h", 1.0)) * self._core_value(ctx) if want else 0.0)
        # never borrow: cover negative cash by selling core (FIFO); a deficit
        # under the engine's $1 minimum order is left (negligible)
        if eng.portfolio.cash < -1.0:
            self._sell_core(ctx, -eng.portfolio.cash)


def _build(c):
    raise NotImplementedError("r2_gap3.overlay runs only through r2_gap3.run_cfg (OptBacktest)")


def _tickers(c):
    return [c.get("core", "SPY")]


register_kind("r2_gap3.overlay", _build, _tickers)


# ==========================================================================
# running (cached, sweep-format records)
# ==========================================================================
_SNAP: dict = {}


def _snap(path: Path) -> bytes:
    k = str(path)
    if k not in _SNAP:
        try:
            _SNAP[k] = Path(path).read_bytes()
        except OSError:
            _SNAP[k] = b""
    return _SNAP[k]


for _f in [HERE, LAB / "core.py", LAB / "data.py", LAB / "blocks.py"]:
    _snap(_f)


def code_hash(cfg: dict) -> str:
    h = hashlib.sha1()
    for k in sorted(_SNAP):
        h.update(_SNAP[k])
    pf = SCRATCH / "out" / ("calib_params.json" if cfg.get("params", "full") == "full"
                            else f"calib_params_{cfg.get('params')}.json")
    if cfg.get("legs") and pf.exists():
        h.update(pf.read_bytes())
    return h.hexdigest()[:12]


def cfg_id(cfg: dict) -> str:
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:14]


def _key(cfg, regime, protocol, comm, slip, mstarts, starts) -> str:
    payload = json.dumps([cfg, regime, protocol, comm, slip, sorted(mstarts or []),
                          [core._ts(s) for s in starts] if starts else None, code_hash(cfg)],
                         sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:20]


def run_cfg(cfg: dict, regime: str = "CA", protocol: str = "full", comm: float = core.COMMISSION,
            slip: float = core.SLIPPAGE, monthly_starts=(), use_cache: bool = True,
            starts=None, all_monthly: bool = False) -> dict:
    """Run one r2_gap3.overlay config on every protocol start in OptBacktest."""
    registry.load_families()
    mstarts = sorted(core._ts(s) for s in monthly_starts)
    if all_monthly:
        mstarts = ["ALL"]
    key = _key(cfg, regime, protocol, comm, slip, mstarts, starts)
    path = CACHE / key[:2] / f"{key}.json"
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    prot = core.PROTOCOLS[protocol]
    t_start = time.time()
    with core.cpu_slot():
        tick = _tickers(cfg)
        mkt = data.market(tick)
        ms = registry.min_start(cfg)
        st_list = list(prot.starts if starts is None else [pd.Timestamp(s) for s in starts])
        st_list = [s for s in st_list if ms is None or s >= ms]
        out = {"starts": {}, "monthly": {}, "full": None, "monthly_by_start": {}, "extra": None}
        for kk, s in enumerate(st_list):
            first = kk == 0
            want_m = first or all_monthly or core._ts(s) in mstarts
            strat = OverlayStrategy(cfg)
            gate = OptGate(strat, s, prot.checkpoints, policy_for(regime), monthly=want_m)
            eng = OptBacktest(gate, mkt, regime, cfg, comm=comm, slip=slip)
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
                ex = dict(eng.st)
                ex.update({"n_rolls": strat.n_rolls, "hedge_rolls": strat.n_hedge_rolls,
                           "avg_scale": strat.hedge_frac_sum / strat.n_hedge_rolls if strat.n_hedge_rolls else 0.0,
                           "core_sales": strat.core_sales, "sweeps": strat.sweeps})
                eqm = float(res.equity["total"][res.equity.index >= gate.t0].mean())
                ex["eq_mean"] = eqm
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
    cfg, regime, protocol, comm, slip, mstarts, all_m = args
    import traceback
    try:
        return run_cfg(cfg, regime, protocol, comm, slip, monthly_starts=mstarts, all_monthly=all_m)
    except Exception as e:  # noqa: BLE001
        return {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol,
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}


def run_many(configs, protocol="full", regimes=("CA",), workers=4, comm=core.COMMISSION,
             slip=core.SLIPPAGE, monthly_starts=(), all_monthly=False, verbose=True) -> list:
    """run_cfg over configs x regimes in parallel (fork), cached."""
    import multiprocessing as mp
    import warnings
    from concurrent.futures import ProcessPoolExecutor, as_completed
    registry.load_families()
    mst = tuple(monthly_starts)
    jobs = [(c, rg, protocol, comm, slip, mst, all_monthly) for c in configs for rg in regimes]
    recs, todo = [], []
    for j in jobs:
        mstarts = ["ALL"] if all_monthly else sorted(core._ts(s) for s in mst)
        key = _key(j[0], j[1], j[2], j[3], j[4], mstarts, None)
        p = CACHE / key[:2] / f"{key}.json"
        if p.exists():
            try:
                recs.append(json.loads(p.read_text()))
                continue
            except json.JSONDecodeError:
                pass
        todo.append(j)
    if verbose:
        print(f"[r2_gap3] {len(recs)} cached, {len(todo)} to run ({protocol}, {regimes})", flush=True)
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
                print(f"[r2_gap3] {n}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    errs = [r for r in recs if "error" in r]
    if errs and verbose:
        print(f"[r2_gap3] {len(errs)} errors; first: {errs[0]['error']}\n{errs[0].get('trace', '')[-1500:]}",
              flush=True)
    return recs

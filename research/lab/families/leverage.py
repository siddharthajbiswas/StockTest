"""Leveraged-ETF strategies (family 'leverage').

Leveraged ETFs are the only leverage the engine allows (no margin). Every
signal here returns target weights for ordinary instruments: real leveraged
ETFs (SSO, UPRO, QLD, TQQQ, TMF, ...; 2006+/2009+) or the clearly labelled
SYNTHETIC research-only series SYN_* built by
research/lab/scratch/leverage/build_synthetic.py (daily-reset L x total-return
underlying minus (L-1) x T-bill financing minus 0.9%/yr; the "C" variants add
the 0.6%/yr swap spread that matches the real funds over their overlap).

Signals (register names "leverage.*")
-------------------------------------
leverage.bandmix   fixed mix; full rebalance on calendar days and/or whenever a
                   weight drifts more than `abs_band` (or `rel_band` x target).
leverage.regime    regime switch: a list of conditions (sma / ema / sma_cross /
                   tsmom / vol / vix / curve / dd), each with hysteresis, mapped
                   (by the string of 0/1 states, or by how many are true) to a
                   target allocation; checked daily/weekly/monthly; optional
                   confirmation days; drift rebalancing inside a state.
leverage.voltarget exposure = target_vol / realised vol (capped), implemented
                   with a 1x fund + a leveraged fund (mode "base") or the
                   leveraged fund + T-bills (mode "safe"); optional trend cap.
leverage.dualmom   dual momentum on unleveraged signal tickers; hold the
                   leveraged version of the winner(s) when absolute momentum is
                   positive, else a safe asset.
leverage.overlay   a never-sold core (e.g. 70% SPY) + a satellite switched by a
                   regime (e.g. UPRO when SPY > SMA200, T-bills otherwise).

Nothing looks ahead: prices come from ctx (up to today's close, the engine's
fill price, same convention as the site); index series (^VIX, ^TNX, ^IRX) are
read with blocks.asof(lag_days=1).
"""
from __future__ import annotations

import math

import numpy as np

from ..blocks import Signal, asof, np_closes, normalize, period_key
from ..registry import register_signal

try:
    from scipy.signal import lfilter
except Exception:  # pragma: no cover
    lfilter = None


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _c(ctx, t: str, n: int, lag: int = 0) -> np.ndarray:
    """Last n closes of t, ending `lag` trading days before today. Index
    series ("^GSPC", "^NDX", ...) are signal-only side channels: read with
    blocks.asof, always lagged at least one day."""
    if t.startswith("^"):
        v = asof(ctx, t, lag_days=max(1, lag), n=max(int(n), 2))
        v = np.asarray(v, dtype=float)
        return v[-int(n):] if n >= 1 else v
    if lag <= 0:
        return np_closes(ctx, t, n)
    c = np_closes(ctx, t, n + lag)
    return c[:-lag] if len(c) > lag else c[:0]


def _live(ctx, w: dict) -> dict:
    """Keep tradable names; if some are not tradable today, scale the rest up
    (same convention as common.mix)."""
    if not w:
        return {}
    live = {t: v for t, v in w.items() if v > 0 and ctx.price(t) is not None}
    if not live:
        return {}
    return normalize(live, sum(v for v in w.values() if v > 0))


def _cur_weights(ctx) -> tuple[dict, float]:
    eng = ctx._engine
    prices = eng.current_prices()
    pos = eng.portfolio.positions
    pv = eng.portfolio.cash + sum(q * prices.get(t, 0.0) for t, q in pos.items())
    if pv <= 0:
        return {}, pv
    return {t: q * prices.get(t, 0.0) / pv for t, q in pos.items()}, pv


def _drift(cur: dict, tgt: dict) -> tuple[float, float]:
    """(max absolute drift, max drift relative to target weight)."""
    names = set(cur) | set(tgt)
    ab = 0.0
    rel = 0.0
    for t in names:
        c, g = cur.get(t, 0.0), tgt.get(t, 0.0)
        d = abs(c - g)
        ab = max(ab, d)
        if g > 0:
            rel = max(rel, d / g)
        elif c > 1e-6:
            rel = max(rel, 1e9)
    return ab, rel


def _ema_last(x: np.ndarray, n: int) -> float:
    a = 2.0 / (n + 1.0)
    if lfilter is not None:
        y, _ = lfilter([a], [1.0, a - 1.0], x[1:], zi=[(1.0 - a) * x[0]])
        return float(y[-1])
    e = x[0]
    for v in x[1:]:
        e = a * v + (1 - a) * e
    return float(e)


def _rvol(c: np.ndarray, n: int) -> float | None:
    if len(c) < n + 1:
        return None
    r = np.diff(np.log(c[-(n + 1):]))
    s = r.std()
    return float(s * math.sqrt(252)) if s > 0 else None


def _ewvol(c: np.ndarray, lam: float, n: int) -> float | None:
    if len(c) < n + 1:
        return None
    r = np.diff(np.log(c[-(n + 1):]))
    w = lam ** np.arange(len(r))[::-1]
    v = float((w * r * r).sum() / w.sum())
    return math.sqrt(v * 252) if v > 0 else None


def _tbill_ret(ctx, lookback_days: int) -> float:
    """Approximate T-bill return over `lookback_days` trading days from ^IRX
    (lag 1 day): mean yield over the period, compounded."""
    v = asof(ctx, "^IRX", lag_days=1, n=lookback_days)
    if v is None or len(v) == 0:
        return 0.0
    y = float(np.nanmean(v)) / 100.0
    return (1.0 + y) ** (lookback_days / 252.0) - 1.0


# --------------------------------------------------------------------------
# conditions (each returns a margin m: positive = condition true)
# --------------------------------------------------------------------------
class Cond:
    """One regime condition with hysteresis.

    spec keys: type, plus per type:
      sma        ticker, n                     m = px / SMA(n) - 1
      ema        ticker, n                     m = px / EMA(n) - 1
      sma_cross  ticker, fast, slow            m = SMA(fast) / SMA(slow) - 1
      tsmom      ticker, lookback, skip, excess (subtract T-bill return)
                                               m = return over lookback
      vol        ticker, n, max [, ewma lam]   m = (max - vol) / max   (true = calm)
      vix        max                           m = (max - VIX) / max   (true = calm)
      curve      min (pct points)              m = (TNX - IRX) - min   (true = normal curve)
      dd         ticker, n (high window), depth  m = (-drawdown) - depth (true = in a dip)
      above_high ticker, n, depth             m = depth - (-drawdown) (true = near high)
    ticker may be an index ("^GSPC", "^NDX"): read via asof, lagged >= 1 day.
    default: state to assume while a condition lacks history (False).
    band: hysteresis half-width in units of m (state flips only when |m| > band).
    lag:  use closes ending `lag` days before today (0 = the lab/site convention:
          decide on today's close, fill at today's close).
    """

    def __init__(self, spec: dict):
        self.s = dict(spec)
        self.type = self.s["type"]
        self.band = float(self.s.get("band", 0.0))
        self.state = None
        self.lag = int(self.s.get("lag", 0))

    def margin(self, ctx):
        s = self.s
        t = self.type
        lag = self.lag
        if t == "sma":
            n = int(s["n"])
            c = _c(ctx, s["ticker"], n, lag)
            if len(c) < n:
                return None
            return c[-1] / c.mean() - 1.0
        if t == "ema":
            n = int(s["n"])
            c = _c(ctx, s["ticker"], 4 * n, lag)
            if len(c) < 2 * n:
                return None
            return c[-1] / _ema_last(c, n) - 1.0
        if t == "sma_cross":
            f, sl = int(s["fast"]), int(s["slow"])
            c = _c(ctx, s["ticker"], sl, lag)
            if len(c) < sl:
                return None
            return c[-f:].mean() / c.mean() - 1.0
        if t == "tsmom":
            lb, sk = int(s.get("lookback", 252)), int(s.get("skip", 0))
            c = _c(ctx, s["ticker"], lb + sk + 1, lag)
            if len(c) < lb + sk + 1:
                return None
            r = c[len(c) - 1 - sk] / c[0] - 1.0
            if s.get("excess"):
                r -= _tbill_ret(ctx, lb)
            return r
        if t == "vol":
            n = int(s.get("n", 20))
            c = _c(ctx, s["ticker"], n + 1, lag)
            v = _ewvol(c, float(s["lam"]), n) if s.get("lam") else _rvol(c, n)
            if v is None:
                return None
            return (float(s["max"]) - v) / float(s["max"])
        if t == "vix":
            v = asof(ctx, "^VIX", lag_days=1)
            if v is None:
                return None
            return (float(s["max"]) - v) / float(s["max"])
        if t == "curve":
            a = asof(ctx, "^TNX", lag_days=1)
            b = asof(ctx, "^IRX", lag_days=1)
            if a is None or b is None:
                return None
            return (a - b) - float(s.get("min", 0.0))
        if t in ("dd", "above_high"):
            n = int(s.get("n", 252))
            c = _c(ctx, s["ticker"], n, lag)
            if len(c) < 2:
                return None
            dd = c[-1] / c.max() - 1.0             # <= 0
            depth = float(s["depth"])
            return (-dd) - depth if t == "dd" else depth - (-dd)
        raise ValueError(f"unknown condition type {t!r}")

    def update(self, ctx):
        m = self.margin(ctx)
        if m is None:
            if self.state is None:
                self.state = bool(self.s.get("default", False))
            return self.state
        if self.state is None:
            self.state = m > 0
        elif m > self.band:
            self.state = True
        elif m < -self.band:
            self.state = False
        return self.state


# --------------------------------------------------------------------------
# leverage.bandmix
# --------------------------------------------------------------------------
class BandMix(Signal):
    """Fixed mix. Rebalanced fully to target on calendar rebalance days
    (mode "calendar"), or whenever a weight drifts beyond the band (mode
    "band", checked daily), or both. abs_band: absolute weight drift (0.05 =
    5 pp); rel_band: drift relative to the target weight (0.25 = 25%)."""

    daily = True

    def __init__(self, weights, mode="band", abs_band=0.05, rel_band=None):
        self.w = dict(weights)
        self.mode = mode
        self.abs_band = abs_band
        self.rel_band = rel_band

    def initialize(self, ctx):
        self._started = False

    def weights(self, ctx, rebalance_day):
        tgt = _live(ctx, self.w)
        if not tgt:
            return None
        if not self._started:
            self._started = True
            return tgt
        if self.mode in ("calendar", "both") and rebalance_day:
            return tgt
        if self.mode in ("band", "both"):
            cur, pv = _cur_weights(ctx)
            ab, rel = _drift(cur, tgt)
            if (self.abs_band is not None and ab > self.abs_band) or \
               (self.rel_band is not None and rel > self.rel_band):
                return tgt
        return None


# --------------------------------------------------------------------------
# leverage.regime
# --------------------------------------------------------------------------
class Regime(Signal):
    """Conditions -> state -> allocation.

    params:
      conds   list of condition specs (see Cond)
      map     {"<bits>": weights} keyed by the 0/1 string of condition states
              (e.g. "1"/"0", or "11","10","01","00"), or by "n<k>" = number of
              true conditions (e.g. "n2","n1","n0"); "default" as fallback.
      check   "D" | "W" | "M"  -- how often conditions are evaluated
      confirm consecutive evaluations a new state must persist before acting
      drift   on calendar rebalance days, re-balance a multi-asset state only
              if some weight drifted more than this (0 = always, None = never)
    """

    daily = True

    def __init__(self, conds, map, check="D", confirm=1, drift=0.0):
        self.specs = [dict(c) for c in conds]
        self.map = {str(k): dict(v) for k, v in map.items()}
        self.check = check
        self.confirm = int(confirm)
        self.drift = drift

    def initialize(self, ctx):
        self.conds = [Cond(s) for s in self.specs]
        self._key = None           # acted-upon state key
        self._pend = None
        self._pend_n = 0
        self._last_check = None
        self._w = None

    def _alloc(self, key: str) -> dict:
        if key in self.map:
            return self.map[key]
        n = "n%d" % key.count("1")
        if n in self.map:
            return self.map[n]
        return self.map.get("default", {})

    def weights(self, ctx, rebalance_day):
        pk = period_key(ctx.date, self.check)
        evaluate = pk != self._last_check
        if evaluate:
            self._last_check = pk
            key = "".join("1" if c.update(ctx) else "0" for c in self.conds)
            if self._key is None:
                self._key = key
                self._pend, self._pend_n = None, 0
                self._w = _live(ctx, self._alloc(key))
                return self._w
            if key != self._key:
                if key == self._pend:
                    self._pend_n += 1
                else:
                    self._pend, self._pend_n = key, 1
                if self._pend_n >= self.confirm:
                    self._key = key
                    self._pend, self._pend_n = None, 0
                    self._w = _live(ctx, self._alloc(key))
                    return self._w
            else:
                self._pend, self._pend_n = None, 0
        if self._key is None:
            return None
        if rebalance_day and self.drift is not None:
            tgt = _live(ctx, self._alloc(self._key))
            if len(tgt) > 1 or self.drift == 0:
                cur, _ = _cur_weights(ctx)
                ab, _ = _drift(cur, tgt)
                if ab > self.drift:
                    self._w = tgt
                    return tgt
        return None


# --------------------------------------------------------------------------
# leverage.voltarget
# --------------------------------------------------------------------------
class VolTarget(Signal):
    """Target a portfolio volatility with leveraged ETFs.

    exposure e = clip(target / vol(ticker), min_exp, max_exp), vol = realised
    (window days) or EWMA (lam). Optional trend cap: when `trend` (a Cond spec)
    is false, e = min(e, trend_cap).
    mode "base": e <= 1 -> one:e + safe:1-e; e > 1 -> lev:(e-1)/(L-1) + one:rest
    mode "safe": lev:e/L + safe:1-e/L (the leveraged fund plus T-bills)
    Rebalanced on calendar days only if |e - e_last| > eband (or first time).
    """

    daily = False

    def __init__(self, ticker="SPY", target=0.15, window=20, lam=None, min_exp=0.0,
                 max_exp=2.0, one="SPY", lev="SSO", L=2.0, safe=None, mode="base",
                 eband=0.1, trend=None, trend_cap=1.0):
        self.ticker = ticker
        self.target = target
        self.window = window
        self.lam = lam
        self.min_exp, self.max_exp = min_exp, max_exp
        self.one, self.lev, self.L = one, lev, float(L)
        self.safe = safe
        self.mode = mode
        self.eband = eband
        self.trend = trend
        self.trend_cap = trend_cap

    def initialize(self, ctx):
        self._e = None
        self._cond = Cond(self.trend) if self.trend else None

    def _exposure(self, ctx):
        c = _c(ctx, self.ticker, self.window + 1)
        v = _ewvol(c, self.lam, self.window) if self.lam else _rvol(c, self.window)
        if v is None:
            return None
        e = min(self.max_exp, max(self.min_exp, self.target / v))
        if self._cond is not None and not self._cond.update(ctx):
            e = min(e, self.trend_cap)
        return e

    def _map(self, e):
        w = {}
        if self.mode == "safe":
            wl = min(1.0, e / self.L)
            if wl > 0:
                w[self.lev] = wl
            if self.safe and 1 - wl > 1e-9:
                w[self.safe] = 1 - wl
            return w
        if e <= 1.0:
            if e > 0:
                w[self.one] = e
            if self.safe and 1 - e > 1e-9:
                w[self.safe] = 1 - e
            return w
        wl = min(1.0, (e - 1.0) / (self.L - 1.0))
        w[self.lev] = wl
        if 1 - wl > 1e-9:
            w[self.one] = 1 - wl
        return w

    def weights(self, ctx, rebalance_day):
        e = self._exposure(ctx)
        if e is None:
            return None
        if self._e is not None and abs(e - self._e) <= self.eband:
            return None
        self._e = e
        return _live(ctx, self._map(e))


# --------------------------------------------------------------------------
# leverage.dualmom
# --------------------------------------------------------------------------
class LevDualMom(Signal):
    """Relative + absolute momentum on unleveraged signal tickers; hold the
    mapped (leveraged) instrument of each pick.

      menu      signal tickers (e.g. ["SPY","QQQ","MDY"])
      lev_map   {signal ticker: instrument to hold} (default: itself)
      lookback  int or list (blended by mean return), skip
      top_n     picks; abs filter: pick's return must beat T-bills (excess=True)
                or 0 (excess=False)
      safe      held for slots whose pick failed the absolute filter
                (a ticker, or "best_bond" from bond_menu by momentum)
    """

    daily = False

    def __init__(self, menu, lev_map=None, lookback=252, skip=0, top_n=1, excess=True,
                 safe=None, bond_menu=None, bond_lookback=126):
        self.menu = list(menu)
        self.lev_map = dict(lev_map or {})
        self.lbs = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = skip
        self.top_n = top_n
        self.excess = excess
        self.safe = safe
        self.bond_menu = list(bond_menu or [])
        self.bond_lookback = bond_lookback

    def _ret(self, ctx, t, lb):
        c = _c(ctx, t, lb + self.skip + 1)
        if len(c) < lb + self.skip + 1 or c[0] <= 0:
            return None
        return c[len(c) - 1 - self.skip] / c[0] - 1.0

    def _safe(self, ctx):
        if self.safe == "best_bond" and self.bond_menu:
            best, br = None, -1e9
            for b in self.bond_menu:
                r = self._ret(ctx, b, self.bond_lookback)
                if r is not None and ctx.price(b) is not None and r > br:
                    best, br = b, r
            return best
        return self.safe

    def weights(self, ctx, rebalance_day):
        sc = {}
        for t in self.menu:
            inst = self.lev_map.get(t, t)
            if ctx.price(inst) is None:
                continue
            rs = [self._ret(ctx, t, lb) for lb in self.lbs]
            if any(r is None for r in rs):
                continue
            sc[t] = float(np.mean(rs))
        if not sc:
            s = self._safe(ctx)
            return {s: 1.0} if s and ctx.price(s) is not None else {}
        order = sorted(sc, key=lambda t: (-sc[t], t))[: self.top_n]
        hurdle = _tbill_ret(ctx, int(np.mean(self.lbs))) if self.excess else 0.0
        w = {}
        slot = 1.0 / self.top_n
        for t in order:
            if sc[t] > hurdle:
                inst = self.lev_map.get(t, t)
                w[inst] = w.get(inst, 0.0) + slot
            else:
                s = self._safe(ctx)
                if s and ctx.price(s) is not None:
                    w[s] = w.get(s, 0.0) + slot
        empty = 1.0 - len(order) * slot
        if empty > 1e-9:
            s = self._safe(ctx)
            if s and ctx.price(s) is not None:
                w[s] = w.get(s, 0.0) + empty
        return w


# --------------------------------------------------------------------------
# leverage.overlay
# --------------------------------------------------------------------------
class Overlay(Signal):
    """Core (never sold) + satellite run by a Regime.

    core      {ticker: weight} bought on day one and never sold (tax deferral)
    sat       Regime params (conds/map/check/confirm); its allocation fills the
              rest of the portfolio, whatever weight the core has drifted to.
    """

    daily = True

    def __init__(self, core, sat):
        self.core = dict(core)
        self.sat = Regime(**sat)

    def initialize(self, ctx):
        self.sat.initialize(ctx)
        self._started = False

    def weights(self, ctx, rebalance_day):
        sw = self.sat.weights(ctx, rebalance_day)
        if self._started and sw is None:
            return None
        if sw is None:
            sw = self.sat._w or {}
        cur, pv = _cur_weights(ctx)
        if not self._started:
            self._started = True
            core = dict(self.core)
        else:
            core = {t: cur.get(t, 0.0) for t in self.core}
        rest = max(0.0, 1.0 - sum(core.values()))
        s = sum(sw.values())
        w = dict(core)
        for t, v in sw.items():
            if s > 0:
                w[t] = w.get(t, 0.0) + rest * v / s
        return w


# --------------------------------------------------------------------------
# registration
# --------------------------------------------------------------------------
def _cond_tickers(conds):
    out = []
    for c in conds or []:
        if c.get("ticker"):
            out.append(c["ticker"])
    return out


def _map_tickers(m):
    out = []
    for v in (m or {}).values():
        out.extend(v.keys())
    return out


register_signal("leverage.bandmix", lambda p: BandMix(**p), lambda p: list(p["weights"]))
register_signal("leverage.regime", lambda p: Regime(**p),
                lambda p: list(dict.fromkeys(_map_tickers(p["map"]) + _cond_tickers(p["conds"]))))
register_signal("leverage.voltarget", lambda p: VolTarget(**p),
                lambda p: list(dict.fromkeys(
                    [p.get("ticker", "SPY"), p.get("one", "SPY"), p.get("lev", "SSO")]
                    + ([p["safe"]] if p.get("safe") else [])
                    + _cond_tickers([p["trend"]] if p.get("trend") else []))))
register_signal("leverage.dualmom", lambda p: LevDualMom(**p),
                lambda p: list(dict.fromkeys(
                    list(p["menu"]) + list((p.get("lev_map") or {}).values())
                    + ([p["safe"]] if p.get("safe") and p["safe"] != "best_bond" else [])
                    + list(p.get("bond_menu") or []))))
register_signal("leverage.overlay", lambda p: Overlay(**p),
                lambda p: list(dict.fromkeys(
                    list(p["core"]) + _map_tickers(p["sat"]["map"])
                    + _cond_tickers(p["sat"]["conds"]))))

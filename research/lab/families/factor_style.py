"""Factor and style tilts and rotation (family key: factor_style).

Signals (all registered as "factor_style.<name>", used with kind "weights"):

  rotate     Rank a menu of style funds by trailing return and hold the top_n
             (direction=+1: relative momentum) or the bottom_n (direction=-1:
             style mean reversion). Options: blended lookbacks, skip, risk-
             adjusted scores, score-gap hysteresis, a benchmark filter ("factor
             momentum": only styles beating SPY qualify, the rest goes to a
             fallback), a static core held alongside the tilt, and long-history
             signal proxies (e.g. compute the value signal on VIVAX while
             trading IWD) so long lookbacks work from 2000.
  ratio      Trend or reversion on the price ratio A/B: hold A while the ratio
             is above (trend) / below (revert) its n-day mean, else B; or a
             continuous z-score tilt between A and B.
  lowvol     Hold the k lowest- (direction=+1) or highest- (direction=-1)
             volatility / beta names of a menu (low-volatility factor built
             from ETFs that existed in 2000).
  composite  Multi-factor rank composite over a menu: momentum, low volatility
             and long-term reversal ranks, weighted; hold the top k.
  season     Calendar style timing: hold style A in the listed months, B
             otherwise (e.g. small caps around January).

Signal-only proxy series (mutual funds / indices) are read strictly before
today (lag 1 day), so nothing can see the future. Traded instruments are read
through the lab's np_closes (closes up to today; orders fill at today's close,
exactly as the site's own pickers do).
"""
from __future__ import annotations

import numpy as np

from ..blocks import Signal, np_closes, normalize, side_series
from ..registry import register_signal

# --------------------------------------------------------------------------
# data helpers
# --------------------------------------------------------------------------
_SIDE_NP: dict = {}


def _side_np(t):
    v = _SIDE_NP.get(t)
    if v is None:
        s = side_series(t)
        v = _SIDE_NP[t] = (s.index.values.astype("datetime64[ns]"), s.to_numpy(dtype=float))
    return v


def side_closes(ctx, t, n):
    """Last n closes of signal-only series t dated strictly before today."""
    idx, vals = _side_np(t)
    today = np.datetime64(ctx.date.to_datetime64(), "ns")
    pos = int(np.searchsorted(idx, today, side="left"))
    if pos <= 0:
        return np.empty(0)
    return vals[max(0, pos - n):pos]


def sig_closes(ctx, t, n, proxies=None):
    p = proxies.get(t) if proxies else None
    if p is None:
        return np_closes(ctx, t, n)
    return side_closes(ctx, p, n)


def _ret(c, lb, skip=0):
    need = lb + skip + 1
    if len(c) < need:
        return None
    a = c[len(c) - need]
    b = c[len(c) - 1 - skip]
    if a <= 0:
        return None
    return b / a - 1.0


def _vol(c, n):
    if len(c) < n + 1:
        return None
    x = c[-(n + 1):]
    r = np.diff(x) / x[:-1]
    s = r.std()
    return float(s * np.sqrt(252)) if s > 0 else None


def _live(ctx, ts):
    return [t for t in ts if ctx.price(t) is not None]


def _blend_core(core, core_w, picks_w, ctx):
    """core_w of `core` (static weights) + (1-core_w) of picks."""
    if not core or core_w <= 0:
        return picks_w
    live = {t: w for t, w in core.items() if ctx.price(t) is not None}
    out = {}
    if live:
        for t, w in normalize(live, core_w).items():
            out[t] = out.get(t, 0.0) + w
        rest = 1.0 - core_w
    else:
        rest = 1.0
    for t, w in normalize(picks_w, rest).items():
        out[t] = out.get(t, 0.0) + w
    return out


# --------------------------------------------------------------------------
# rotate: relative momentum / mean reversion among styles
# --------------------------------------------------------------------------
class StyleRotation(Signal):
    def __init__(self, menu, lookback=252, skip=0, top_n=1, direction=1,
                 proxies=None, hyst=0.0, risk_adj=False, vol_window=126,
                 bench_filter=None, bench_margin=0.0, fallback=None,
                 core=None, core_w=0.0, weighting="equal", neutral=None):
        self.menu = list(menu)
        self.lbs = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = skip
        self.top_n = top_n
        self.direction = direction
        self.proxies = dict(proxies or {})
        self.hyst = hyst
        self.risk_adj = risk_adj
        self.vol_window = vol_window
        self.bench_filter = bench_filter
        self.bench_margin = bench_margin
        self.fallback = fallback
        self.core = dict(core or {})
        self.core_w = core_w
        self.weighting = weighting
        # what to hold before any signal exists (default: equal weight menu)
        self.neutral = neutral

    def initialize(self, ctx):
        self._held = []

    def _score(self, ctx, t):
        need = max(self.lbs) + self.skip + 1
        if self.risk_adj:
            need = max(need, self.vol_window + 1)
        c = sig_closes(ctx, t, need, self.proxies)
        rs = [_ret(c, lb, self.skip) for lb in self.lbs]
        if any(r is None for r in rs):
            return None
        s = float(np.mean(rs))
        if self.risk_adj:
            v = _vol(c, self.vol_window)
            if not v:
                return None
            s = s / v
        return s

    def weights(self, ctx, rebalance_day):
        live = _live(ctx, self.menu)
        sc = {}
        for t in live:
            s = self._score(ctx, t)
            if s is not None:
                sc[t] = self.direction * s
        if not sc:
            neu = self.neutral if self.neutral is not None else {t: 1.0 for t in live}
            neu = {t: w for t, w in neu.items() if ctx.price(t) is not None}
            return _blend_core(self.core, self.core_w, normalize(neu), ctx) if neu else {}
        order = sorted(sc, key=lambda t: (-sc[t], t))
        k = min(self.top_n, len(order))
        picks = order[:k]
        # score-gap hysteresis: an incumbent is only replaced by a challenger
        # whose score beats the incumbent's by more than `hyst`
        if self.hyst > 0 and self._held:
            inc = [t for t in self._held if t in sc]
            new = list(picks)
            for t in inc:
                if t in new:
                    continue
                weakest = min((p for p in new if p not in inc), key=lambda p: sc[p], default=None)
                if weakest is not None and sc[weakest] - sc[t] <= self.hyst:
                    new[new.index(weakest)] = t
            picks = new
        # benchmark filter (factor momentum): only styles beating the bench
        slots = k
        if self.bench_filter:
            bs = self._score(ctx, self.bench_filter)
            if bs is not None:
                bs = self.direction * bs
                picks = [t for t in picks if sc[t] > bs + self.bench_margin]
        self._held = list(picks)
        w = {}
        for t in picks:
            if self.weighting == "invvol":
                c = np_closes(ctx, t, self.vol_window + 1)
                v = _vol(c, self.vol_window)
                w[t] = 1.0 / v if v else 0.0
            else:
                w[t] = 1.0
        w = normalize(w, len(picks) / slots) if w else {}
        if len(picks) < slots:
            fb = self.fallback
            if fb and ctx.price(fb) is not None:
                w[fb] = w.get(fb, 0.0) + (1.0 - len(picks) / slots)
        return _blend_core(self.core, self.core_w, w, ctx)


def _tick_rotate(p):
    out = list(p["menu"])
    for k in ("fallback", "bench_filter"):
        if p.get(k):
            out.append(p[k])
    out += list((p.get("core") or {}))
    out += list((p.get("neutral") or {}))
    return list(dict.fromkeys(out))


register_signal("factor_style.rotate", lambda p: StyleRotation(**p), _tick_rotate)


# --------------------------------------------------------------------------
# ratio: trend / reversion / z-score tilt on the A/B price ratio
# --------------------------------------------------------------------------
class RatioSignal(Signal):
    def __init__(self, a, b, n=200, mode="trend", band=0.0, proxies=None,
                 z_k=0.5, z_cap=1.0, core=None, core_w=0.0):
        self.a, self.b = a, b
        self.n = n
        self.mode = mode           # trend | revert | ztilt (revert, continuous) | ztrend
        self.band = band
        self.proxies = dict(proxies or {})
        self.z_k = z_k
        self.z_cap = z_cap
        self.core = dict(core or {})
        self.core_w = core_w

    def initialize(self, ctx):
        self._state = None

    def _ratio(self, ctx):
        ca = sig_closes(ctx, self.a, self.n + 1, self.proxies)
        cb = sig_closes(ctx, self.b, self.n + 1, self.proxies)
        m = min(len(ca), len(cb))
        if m < self.n + 1:
            return None
        return np.log(ca[-m:]) - np.log(cb[-m:])

    def weights(self, ctx, rebalance_day):
        la, lb = ctx.price(self.a) is not None, ctx.price(self.b) is not None
        if not (la and lb):
            only = self.a if la else (self.b if lb else None)
            return _blend_core(self.core, self.core_w, {only: 1.0} if only else {}, ctx)
        r = self._ratio(ctx)
        if r is None:
            return _blend_core(self.core, self.core_w, {self.a: 0.5, self.b: 0.5}, ctx)
        x = r[-1]
        mu = r[-self.n:].mean()
        if self.mode in ("trend", "revert"):
            up = x > mu + self.band
            dn = x < mu - self.band
            if self._state is None:
                st = bool(up or not dn)
            elif self._state and dn:
                st = False
            elif (not self._state) and up:
                st = True
            else:
                st = self._state
            self._state = st
            hold_a = st if self.mode == "trend" else (not st)
            w = {self.a: 1.0} if hold_a else {self.b: 1.0}
        else:
            sd = r[-self.n:].std()
            z = (x - mu) / sd if sd > 0 else 0.0
            sgn = -1.0 if self.mode == "ztilt" else 1.0
            fa = 0.5 + sgn * float(np.clip(self.z_k * z, -self.z_cap, self.z_cap)) * 0.5
            fa = float(np.clip(fa, 0.0, 1.0))
            w = {self.a: fa, self.b: 1.0 - fa}
            w = {t: v for t, v in w.items() if v > 1e-6}
        return _blend_core(self.core, self.core_w, w, ctx)


register_signal("factor_style.ratio", lambda p: RatioSignal(**p),
                lambda p: list(dict.fromkeys([p["a"], p["b"]] + list((p.get("core") or {})))))


# --------------------------------------------------------------------------
# lowvol: low-volatility / low-beta (or high-beta) selection
# --------------------------------------------------------------------------
class LowVolSelect(Signal):
    def __init__(self, menu, k=3, window=126, metric="vol", direction=1,
                 weighting="equal", bench="SPY", core=None, core_w=0.0):
        self.menu = list(menu)
        self.k = k
        self.window = window
        self.metric = metric
        self.direction = direction
        self.weighting = weighting
        self.bench = bench
        self.core = dict(core or {})
        self.core_w = core_w

    def weights(self, ctx, rebalance_day):
        live = _live(ctx, self.menu)
        n = self.window
        rb = None
        if self.metric == "beta":
            cb = np_closes(ctx, self.bench, n + 1)
            if len(cb) < n + 1:
                return _blend_core(self.core, self.core_w, normalize({t: 1.0 for t in live}), ctx)
            rb = np.diff(cb) / cb[:-1]
        sc, vols = {}, {}
        for t in live:
            c = np_closes(ctx, t, n + 1)
            if len(c) < n + 1:
                continue
            r = np.diff(c) / c[:-1]
            v = r.std()
            if v <= 0:
                continue
            vols[t] = v
            if self.metric == "beta":
                var = rb.var()
                sc[t] = float(np.cov(r, rb, ddof=0)[0, 1] / var) if var > 0 else 1.0
            else:
                sc[t] = float(v)
        if not sc:
            return _blend_core(self.core, self.core_w, normalize({t: 1.0 for t in live}), ctx)
        order = sorted(sc, key=lambda t: (self.direction * sc[t], t))
        picks = order[: self.k]
        if self.weighting == "invvol":
            w = {t: 1.0 / vols[t] for t in picks}
        else:
            w = {t: 1.0 for t in picks}
        return _blend_core(self.core, self.core_w, normalize(w), ctx)


register_signal("factor_style.lowvol", lambda p: LowVolSelect(**p),
                lambda p: list(dict.fromkeys(list(p["menu"]) + [p.get("bench", "SPY")]
                                             + list((p.get("core") or {})))))


# --------------------------------------------------------------------------
# composite: multi-factor rank composite
# --------------------------------------------------------------------------
class Composite(Signal):
    def __init__(self, menu, k=3, w_mom=1.0, w_lowvol=0.0, w_rev=0.0,
                 mom_lb=252, mom_skip=21, vol_lb=126, rev_lb=1008, proxies=None,
                 core=None, core_w=0.0):
        self.menu = list(menu)
        self.k = k
        self.w_mom, self.w_lowvol, self.w_rev = w_mom, w_lowvol, w_rev
        self.mom_lb, self.mom_skip = mom_lb, mom_skip
        self.vol_lb, self.rev_lb = vol_lb, rev_lb
        self.proxies = dict(proxies or {})
        self.core = dict(core or {})
        self.core_w = core_w

    def weights(self, ctx, rebalance_day):
        live = _live(ctx, self.menu)
        feats = {}
        for t in live:
            f = []
            if self.w_mom:
                c = sig_closes(ctx, t, self.mom_lb + self.mom_skip + 1, self.proxies)
                f.append(_ret(c, self.mom_lb, self.mom_skip))
            if self.w_lowvol:
                c = np_closes(ctx, t, self.vol_lb + 1)
                v = _vol(c, self.vol_lb)
                f.append(-v if v else None)
            if self.w_rev:
                c = sig_closes(ctx, t, self.rev_lb + 1, self.proxies)
                r = _ret(c, self.rev_lb, 0)
                f.append(-r if r is not None else None)
            if any(x is None for x in f):
                continue
            feats[t] = f
        if len(feats) < 2:
            return _blend_core(self.core, self.core_w, normalize({t: 1.0 for t in live}), ctx)
        names = sorted(feats)
        arr = np.array([feats[t] for t in names])
        ranks = arr.argsort(axis=0).argsort(axis=0) / max(1, len(names) - 1)
        wts = np.array([w for w in (self.w_mom, self.w_lowvol, self.w_rev) if w])
        score = ranks @ wts
        order = sorted(range(len(names)), key=lambda i: (-score[i], names[i]))
        picks = [names[i] for i in order[: self.k]]
        return _blend_core(self.core, self.core_w, normalize({t: 1.0 for t in picks}), ctx)


register_signal("factor_style.composite", lambda p: Composite(**p),
                lambda p: list(dict.fromkeys(list(p["menu"]) + list((p.get("core") or {})))))


# --------------------------------------------------------------------------
# season: calendar style timing
# --------------------------------------------------------------------------
class SeasonStyle(Signal):
    daily = True

    def __init__(self, a, b, months=(11, 12, 1)):
        self.a, self.b = a, b
        self.months = set(months)

    def initialize(self, ctx):
        self._cur = None

    def weights(self, ctx, rebalance_day):
        want = self.a if ctx.date.month in self.months else self.b
        if ctx.price(want) is None:
            want = self.b if want == self.a else self.a
        if want == self._cur and not rebalance_day:
            return None
        self._cur = want
        return {want: 1.0}


register_signal("factor_style.season", lambda p: SeasonStyle(**p),
                lambda p: [p["a"], p["b"]])


# --------------------------------------------------------------------------
# macro: choose between two styles by a market-state rule
# --------------------------------------------------------------------------
class MacroStyle(Signal):
    """Hold A while a condition is on, else B.

    rule="drawdown": bench is more than `thr` below its `n`-day high (small /
                     value caps lead recoveries), with a minimum stay of
                     `stay` calendar days once switched on;
    rule="curve":    10y - 3m Treasury slope (^TNX - ^IRX, lagged 1 day) > thr;
    rule="vix":      ^VIX (lagged 1 day) > thr.
    """

    def __init__(self, a, b, rule="drawdown", thr=0.2, n=252, bench="SPY", stay=0):
        self.a, self.b = a, b
        self.rule = rule
        self.thr = thr
        self.n = n
        self.bench = bench
        self.stay = stay

    def initialize(self, ctx):
        self._on_since = None

    def _cond(self, ctx):
        if self.rule == "drawdown":
            c = np_closes(ctx, self.bench, self.n)
            if len(c) < 20:
                return None
            return c[-1] / c.max() - 1.0 < -self.thr
        if self.rule == "curve":
            t = side_closes(ctx, "^TNX", 1)
            i = side_closes(ctx, "^IRX", 1)
            if len(t) == 0 or len(i) == 0:
                return None
            return float(t[-1] - i[-1]) > self.thr
        if self.rule == "vix":
            v = side_closes(ctx, "^VIX", 1)
            if len(v) == 0:
                return None
            return float(v[-1]) > self.thr
        raise ValueError(self.rule)

    def weights(self, ctx, rebalance_day):
        on = self._cond(ctx)
        if on:
            self._on_since = ctx.date
        elif self._on_since is not None and (ctx.date - self._on_since).days <= self.stay:
            on = True
        want = self.a if on else self.b
        if ctx.price(want) is None:
            want = self.b if want == self.a else self.a
        return {want: 1.0} if ctx.price(want) is not None else {}


register_signal("factor_style.macro", lambda p: MacroStyle(**p),
                lambda p: list(dict.fromkeys([p["a"], p["b"], p.get("bench", "SPY")])))

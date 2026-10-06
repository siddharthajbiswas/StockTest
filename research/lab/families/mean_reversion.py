"""Mean reversion, dip-buying and volatility signals (FAMILY_KEY = mean_reversion).

Everything here reads only history up to today (the engine fills at today's
close) and side-channel index series (^VIX, ^VIX3M) strictly before today
(blocks.asof lag-1 semantics). Indicator arrays are precomputed once per ticker
over the full series, but every value at bar i is a function of bars <= i only
(rolling / recursive filters), so indexing them at today's bar is causal.

Registered signals (kind "weights")
-----------------------------------
mean_reversion.timer    one signal ticker drives an on/off state machine:
                        entry = ALL of a list of conditions, exit = ANY of a list
                        (plus max_hold time stop, stop-loss, min_hold that blocks
                        exits of winning trades until they are long-term). "on"
                        and "off" are arbitrary weight dicts (e.g. SPY vs SHY, or
                        SPY vs SSO for a leveraged dip overlay). Ticker keys may be
                        chains "SHY|VFISX" = first one tradable today.
mean_reversion.basket   the same rule run independently on every name of a menu;
                        each name that is "on" gets a slot, the rest sits in
                        `base` (cash proxy or SPY).
mean_reversion.xs       cross-sectional reversal: hold the N worst performers of
                        a menu over a lookback (short-term 1w-1m reversal or long-
                        term 3-5y reversal), optional trend filter.
mean_reversion.volscale exposure = clip(target / vol, floor, cap) using realized
                        vol or lagged VIX; >1x via a leveraged ETF.

Registered kind
---------------
mean_reversion.ladder   tax-aware dip ladder: start in a core mix, deploy tranches
                        from a funding asset into a dip asset when drawdown/
                        oversold levels fire, hold each tranche >= min_hold days
                        (366 = long-term), release it when a condition holds.

Condition syntax: {"i": <indicator>, <params>, "lt"|"le"|"gt"|"ge": x,
                   "src": ticker (default: the rule's signal ticker),
                   "for": k (must hold on k consecutive bars)}
Indicators: close, rsi(n), crsi(a,b,c), cumrsi(n,m), streak, ret(n), dsma(n),
            dema(n), pctb(n,k), stoch(n), dd(n; 0 = all-time), rv(n),
            rvratio(n,m), smaslope(n,k), vix, vixsma(n), vixpct(n), vixrsi(n),
            vixchg(n), vixterm(n = smoothing), vrp(n).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from backtester import Strategy

from ..blocks import Signal, side_series
from ..registry import register_kind, register_signal

FAMILY = "mean_reversion"
_EPS = 1e-12


# --------------------------------------------------------------------------
# indicator engine (numpy, causal), cached per (ticker, spec)
# --------------------------------------------------------------------------
_SER: dict = {}
_IND: dict = {}


def _base(ctx, t):
    """(dates ndarray[datetime64], closes ndarray) of t's full series in this market."""
    m = ctx._engine.market
    s = m.series(t, "Close")
    if s is None:
        return None
    key = (t, len(s), s.index[0], s.index[-1])
    v = _SER.get(key)
    if v is None:
        v = _SER[key] = (s.index.values, s.to_numpy(dtype=float), key)
    return v


def _sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def _rsi(x, n):
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(x) < n + 1:
        return out
    d = np.diff(x)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(up).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    ad = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(ad <= 0, 100.0, 100.0 - 100.0 / (1.0 + au / np.where(ad <= 0, 1.0, ad)))
    out[1:] = r
    out[: n] = np.nan
    return out


def _streak(c):
    s = np.zeros(len(c))
    for i in range(1, len(c)):
        if c[i] > c[i - 1]:
            s[i] = s[i - 1] + 1 if s[i - 1] > 0 else 1
        elif c[i] < c[i - 1]:
            s[i] = s[i - 1] - 1 if s[i - 1] < 0 else -1
    return s


def _pct_rank_prev(x, n):
    """Share of the previous n values strictly below today's value."""
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(x[:-1], n)            # w[j] = x[j .. j+n-1]
    cur = x[n:]                                   # today's value for window j
    out[n:] = (w < cur[:, None]).mean(axis=1)
    return out


def _roll_rank_incl(x, n):
    """Share of the last n values (incl. today) <= today's value."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(x, n)
    out[n - 1:] = (w <= w[:, -1:]).mean(axis=1)
    return out


def _align_side(dates, side: pd.Series):
    """Value of a side series on the last date strictly before each date."""
    sd = side.index.values
    j = np.searchsorted(sd, dates, side="left") - 1
    v = side.to_numpy(dtype=float)
    out = np.where(j >= 0, v[np.clip(j, 0, None)], np.nan)
    return out


def _vix_frame():
    v = side_series("^VIX")
    return v[v > 0]


def _compute(dates, c, spec):
    name = spec[0]
    p = dict(spec[1:])
    n = int(p.get("n", 0) or 0)
    if name == "close":
        return c
    if name == "rsi":
        return _rsi(c, n or 2)
    if name == "crsi":
        a, b, k = int(p.get("a", 3)), int(p.get("b", 2)), int(p.get("k", 100))
        r1 = _rsi(c, a)
        r2 = _rsi(_streak(c), b)
        roc = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
        pr = _pct_rank_prev(roc, k) * 100.0
        return (r1 + r2 + pr) / 3.0
    if name == "cumrsi":
        r = _rsi(c, n or 2)
        m = int(p.get("m", 2))
        return pd.Series(r).rolling(m, min_periods=m).sum().to_numpy()
    if name == "streak":
        return _streak(c)
    if name == "ret":
        out = np.full(len(c), np.nan)
        out[n:] = c[n:] / c[:-n] - 1.0
        return out
    if name == "dsma":
        return c / _sma(c, n) - 1.0
    if name == "dema":
        e = pd.Series(c).ewm(span=n, adjust=False).mean().to_numpy().copy()
        e[: n] = np.nan
        return c / e - 1.0
    if name == "pctb":
        k = float(p.get("k", 2.0))
        s = pd.Series(c)
        m = s.rolling(n, min_periods=n).mean().to_numpy()
        sd = s.rolling(n, min_periods=n).std(ddof=0).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            return (c - (m - k * sd)) / (2.0 * k * sd)
    if name == "stoch":
        s = pd.Series(c)
        lo = s.rolling(n, min_periods=n).min().to_numpy()
        hi = s.rolling(n, min_periods=n).max().to_numpy()
        rng = hi - lo
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(rng > 0, (c - lo) / np.where(rng > 0, rng, 1.0), 0.5)
    if name == "dd":
        s = pd.Series(c)
        hi = (s.cummax() if n == 0 else s.rolling(n, min_periods=1).max()).to_numpy()
        return c / hi - 1.0
    if name == "rv":
        lr = np.r_[np.nan, np.diff(np.log(c))]
        return pd.Series(lr).rolling(n, min_periods=n).std(ddof=0).to_numpy() * math.sqrt(252)
    if name == "rvratio":
        m = int(p.get("m", 100))
        lr = pd.Series(np.r_[np.nan, np.diff(np.log(c))])
        a = lr.rolling(n, min_periods=n).std(ddof=0).to_numpy()
        b = lr.rolling(m, min_periods=m).std(ddof=0).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            return a / b
    if name == "smaslope":
        k = int(p.get("k", 20))
        s = _sma(c, n)
        out = np.full(len(c), np.nan)
        out[k:] = s[k:] / s[:-k] - 1.0
        return out
    # ---- side-channel volatility indices (always lagged: value strictly before today)
    if name.startswith("vix") or name == "vrp":
        v = _vix_frame()
        vv = v.to_numpy(dtype=float)
        if name == "vix":
            ser = v
        elif name == "vixsma":
            ser = pd.Series(vv / _sma(vv, n) - 1.0, index=v.index)
        elif name == "vixpct":
            ser = pd.Series(_roll_rank_incl(vv, n), index=v.index)
        elif name == "vixrsi":
            ser = pd.Series(_rsi(vv, n or 2), index=v.index)
        elif name == "vixchg":
            out = np.full(len(vv), np.nan)
            out[n:] = vv[n:] / vv[:-n] - 1.0
            ser = pd.Series(out, index=v.index)
        elif name == "vixterm":
            v3 = side_series("^VIX3M")
            v3 = v3[v3 > 0]
            j = v.index.intersection(v3.index)
            r = (v[j] / v3[j]).astype(float)
            if n and n > 1:
                r = r.rolling(n, min_periods=n).mean()
            ser = r
        elif name == "vrp":
            al = _align_side(dates, v)
            lr = np.r_[np.nan, np.diff(np.log(c))]
            rv = pd.Series(lr).rolling(n or 21, min_periods=n or 21).std(ddof=0).to_numpy() * math.sqrt(252)
            return al - rv * 100.0
        else:
            raise ValueError(f"unknown indicator {name!r}")
        return _align_side(dates, ser)
    raise ValueError(f"unknown indicator {name!r}")


_COND_KEYS = ("lt", "le", "gt", "ge", "src", "for", "i", "den")


def _spec(cond):
    sp = (cond["i"],) + tuple(sorted((k, v) for k, v in cond.items() if k not in _COND_KEYS))
    if cond.get("den"):
        sp = sp + (("__den", cond["den"]),)
    return sp


def ind_array(ctx, t, spec):
    b = _base(ctx, t)
    if b is None:
        return None, None
    dates, c, key = b
    k = (key, spec)
    a = _IND.get(k)
    if a is None:
        den = dict(spec[1:]).get("__den")
        core_spec = tuple(x for x in spec if not (isinstance(x, tuple) and x[0] == "__den"))
        if den:
            bd = _base(ctx, den)
            if bd is None:
                return None, None
            j = np.searchsorted(bd[0], dates, side="right") - 1      # den's last close <= date
            dv = np.where(j >= 0, bd[1][np.clip(j, 0, None)], np.nan)
            c = c / dv
        a = _IND[k] = _compute(dates, c, core_spec)
    return a, dates


def _bar(ctx, t):
    """Index of today's (or the latest prior) bar of t; -1 if none yet."""
    return ctx._engine.market.rows_upto(t, ctx._engine._dv) - 1


class Cond:
    __slots__ = ("spec", "src", "op", "x", "k")

    def __init__(self, d, default_src):
        self.spec = _spec(d)
        self.src = d.get("src", default_src)
        self.k = int(d.get("for", 1))
        for op in ("lt", "le", "gt", "ge"):
            if op in d:
                self.op, self.x = op, float(d[op])
                break
        else:
            raise ValueError(f"condition needs lt/le/gt/ge: {d}")

    def value(self, ctx, lag=0, src=None):
        t = src or self.src
        a, _ = ind_array(ctx, t, self.spec)
        if a is None:
            return None
        i = _bar(ctx, t) - lag
        if i < 0:
            return None
        v = a[i]
        return None if v != v else float(v)

    def holds(self, ctx, lag=0, src=None) -> bool:
        t = src or self.src
        a, _ = ind_array(ctx, t, self.spec)
        if a is None:
            return False
        i = _bar(ctx, t) - lag
        if i - self.k + 1 < 0:
            return False
        for j in range(i - self.k + 1, i + 1):
            v = a[j]
            if v != v:
                return False
            op, x = self.op, self.x
            if op == "lt":
                ok = v < x
            elif op == "le":
                ok = v <= x
            elif op == "gt":
                ok = v > x
            else:
                ok = v >= x
            if not ok:
                return False
        return True


def _conds(lst, src):
    return [Cond(d, src) for d in (lst or [])]


def _resolve(ctx, w: dict) -> dict:
    """Weights with chain keys "A|B" resolved to the first tradable ticker."""
    out: dict = {}
    for k, v in w.items():
        if v <= 0:
            continue
        for t in k.split("|"):
            if ctx.price(t) is not None:
                out[t] = out.get(t, 0.0) + float(v)
                break
    return out


def _chain_tickers(w) -> list:
    out = []
    for k in (w or {}):
        out.extend(k.split("|"))
    return out


def _cond_srcs(lst) -> list:
    return [d[k] for d in (lst or []) for k in ("src", "den") if d.get(k)]


# --------------------------------------------------------------------------
# 1. on/off timer
# --------------------------------------------------------------------------
class MRTimer(Signal):
    daily = True

    def __init__(self, on, off=None, sig=None, entry=(), exit=(), max_hold=0, min_hold=0,
                 min_hold_gain_only=True, stop=0.0, lag=0, init="off", rebal=False,
                 cooldown=0, exit_on_entry_fail=False):
        self.on = dict(on)
        self.off = dict(off or {})
        self.sig = sig or next(iter(self.on)).split("|")[0]
        self.entry = _conds(entry, self.sig)
        self.exit = _conds(exit, self.sig)
        self.max_hold = int(max_hold or 0)
        self.min_hold = int(min_hold or 0)
        self.gain_only = bool(min_hold_gain_only)
        self.stop = float(stop or 0.0)
        self.lag = int(lag)
        self.init = init
        self.rebal = rebal
        self.cooldown = int(cooldown or 0)
        self.exit_on_entry_fail = exit_on_entry_fail

    def initialize(self, ctx):
        self.state = None
        self.entry_date = None
        self.entry_px = None
        self.bars = 0
        self.since_exit = 10 ** 9

    def _entry_ok(self, ctx):
        return bool(self.entry) and all(c.holds(ctx, self.lag) for c in self.entry)

    def _exit_ok(self, ctx):
        return any(c.holds(ctx, self.lag) for c in self.exit)

    def _sig_px(self, ctx):
        c = _base(ctx, self.sig)
        i = _bar(ctx, self.sig)
        return None if c is None or i < 0 else float(c[1][i])

    def weights(self, ctx, rebalance_day):
        if self.state is None:
            if self.init == "on":
                st = not self._exit_ok(ctx)
            else:
                st = self._entry_ok(ctx)
            self._set(ctx, st)
            return _resolve(ctx, self.on if st else self.off)
        changed = False
        if self.state:
            self.bars += 1
            want_exit = False
            px = self._sig_px(ctx)
            if self.stop > 0 and px is not None and self.entry_px and px < self.entry_px * (1 - self.stop):
                want_exit = True                       # stop-loss: always allowed
            else:
                ex = self._exit_ok(ctx) or (self.max_hold and self.bars >= self.max_hold) \
                    or (self.exit_on_entry_fail and not all(c.holds(ctx, self.lag) for c in self.entry))
                if ex:
                    held_days = (ctx.date - self.entry_date).days if self.entry_date is not None else 10 ** 6
                    if self.min_hold and held_days < self.min_hold:
                        losing = px is not None and self.entry_px and px <= self.entry_px
                        want_exit = bool(self.gain_only and losing)
                    else:
                        want_exit = True
            if want_exit:
                self._set(ctx, False)
                changed = True
        else:
            self.since_exit += 1
            if self.since_exit > self.cooldown and self._entry_ok(ctx):
                self._set(ctx, True)
                changed = True
        if changed or (rebalance_day and self.rebal):
            return _resolve(ctx, self.on if self.state else self.off)
        return None

    def _set(self, ctx, st):
        if st and not self.state:
            self.entry_date = ctx.date
            self.entry_px = self._sig_px(ctx)
            self.bars = 0
        if not st and self.state:
            self.since_exit = 0
        self.state = st


def _timer_tickers(p):
    return list(dict.fromkeys(_chain_tickers(p["on"]) + _chain_tickers(p.get("off"))
                              + ([p["sig"]] if p.get("sig") else [])
                              + _cond_srcs(p.get("entry")) + _cond_srcs(p.get("exit"))))


register_signal("mean_reversion.timer", lambda p: MRTimer(**p), _timer_tickers)


# --------------------------------------------------------------------------
# 2. per-asset basket: the same rule on every menu name
# --------------------------------------------------------------------------
class MRBasket(Signal):
    daily = True

    def __init__(self, menu, base=None, slot=None, entry=(), exit=(), max_hold=0, lag=0,
                 max_on=None, rank="rsi2", map_to=None, min_hold=0, rebal=False):
        self.menu = list(menu)
        self.base = dict(base or {})
        self.slot = slot
        self.entry_d, self.exit_d = list(entry), list(exit)
        self.max_hold = int(max_hold or 0)
        self.lag = int(lag)
        self.max_on = max_on
        self.rank = rank
        self.map_to = dict(map_to or {})      # traded instrument per signal name
        self.min_hold = int(min_hold or 0)
        self.rebal = rebal

    def initialize(self, ctx):
        self.entry = {t: [Cond(d, t) for d in self.entry_d] for t in self.menu}
        self.exit = {t: [Cond(d, t) for d in self.exit_d] for t in self.menu}
        self.on: dict = {}            # t -> (entry_date, bars)
        self.started = False
        self._r2 = Cond({"i": "rsi", "n": 2, "lt": 0}, None)

    def weights(self, ctx, rebalance_day):
        changed = not self.started
        self.started = True
        for t in list(self.on):
            d0, bars = self.on[t]
            bars += 1
            self.on[t] = (d0, bars)
            ex = any(c.holds(ctx, self.lag) for c in self.exit[t]) or (self.max_hold and bars >= self.max_hold)
            if ex and (not self.min_hold or (ctx.date - d0).days >= self.min_hold):
                del self.on[t]
                changed = True
        cands = []
        for t in self.menu:
            if t in self.on or ctx.price(self.map_to.get(t, t)) is None:
                continue
            if self.entry[t] and all(c.holds(ctx, self.lag) for c in self.entry[t]):
                r = self._r2.value(ctx, self.lag, src=t)
                cands.append((r if r is not None else 50.0, t))
        cands.sort()
        cap = self.max_on or len(self.menu)
        for _, t in cands:
            if len(self.on) >= cap:
                break
            self.on[t] = (ctx.date, 0)
            changed = True
        if not (changed or (rebalance_day and self.rebal)):
            return None
        live = [t for t in self.menu if ctx.price(self.map_to.get(t, t)) is not None]
        slot = self.slot if self.slot is not None else (1.0 / max(1, len(live)))
        w: dict = {}
        for t in self.on:
            tt = self.map_to.get(t, t)
            w[tt] = w.get(tt, 0.0) + slot
        rest = max(0.0, 1.0 - sum(w.values()))
        if rest > 1e-9 and self.base:
            b = _resolve(ctx, self.base)
            s = sum(b.values())
            for k, v in b.items():
                w[k] = w.get(k, 0.0) + rest * v / s
        return w


register_signal("mean_reversion.basket", lambda p: MRBasket(**p),
                lambda p: list(dict.fromkeys(list(p["menu"]) + list((p.get("map_to") or {}).values())
                                             + _chain_tickers(p.get("base")))))


# --------------------------------------------------------------------------
# 3. cross-sectional reversal (short- or long-horizon losers)
# --------------------------------------------------------------------------
class XSReversal(Signal):
    def __init__(self, menu, n=21, skip=0, bottom=3, filter=None, fallback=None, mode="losers",
                 weighting="equal", vol_n=63, require_n=None):
        self.menu = list(menu)
        self.n, self.skip, self.bottom = int(n), int(skip), int(bottom)
        self.filter = list(filter or [])
        self.fallback = fallback
        self.mode = mode
        self.weighting = weighting
        self.vol_n = vol_n
        self.require_n = require_n

    def initialize(self, ctx):
        self.f = {t: [Cond(d, t) for d in self.filter] for t in self.menu}

    def weights(self, ctx, rebalance_day):
        if not rebalance_day:
            return None
        sc = []
        for t in self.menu:
            if ctx.price(t) is None:
                continue
            b = _base(ctx, t)
            i = _bar(ctx, t)
            need = self.n + self.skip
            if b is None or i - need < 0:
                continue
            c = b[1]
            r = c[i - self.skip] / c[i - need] - 1.0
            sc.append((r, t))
        if not sc:
            return _resolve(ctx, {self.fallback: 1.0}) if self.fallback else {}
        sc.sort(reverse=(self.mode == "winners"))
        picks = []
        for r, t in sc[: self.bottom]:
            if all(c.holds(ctx, 0) for c in self.f[t]):
                picks.append(t)
        slots = min(self.bottom, len(sc))
        w = {t: 1.0 / slots for t in picks}
        if self.weighting == "invvol" and picks:
            iv = {}
            for t in picks:
                a, _ = ind_array(ctx, t, ("rv", ("n", self.vol_n)))
                v = a[_bar(ctx, t)] if a is not None else np.nan
                iv[t] = 1.0 / v if v == v and v > 0 else 0.0
            s = sum(iv.values())
            if s > 0:
                tot = len(picks) / slots
                w = {t: tot * iv[t] / s for t in picks}
        rest = 1.0 - sum(w.values())
        if rest > 1e-9 and self.fallback:
            fb = _resolve(ctx, {self.fallback: rest})
            for k, v in fb.items():
                w[k] = w.get(k, 0.0) + v
        return w


register_signal("mean_reversion.xs", lambda p: XSReversal(**p),
                lambda p: list(dict.fromkeys(list(p["menu"]) + (p["fallback"].split("|") if p.get("fallback") else []))))


# --------------------------------------------------------------------------
# 4. volatility-scaled exposure (realized vol or lagged VIX)
# --------------------------------------------------------------------------
class VolScale(Signal):
    def __init__(self, risk="SPY", safe=None, lev=None, lev_mult=2.0, measure=None, target=0.15,
                 cap=1.0, floor=0.0, sig=None, step=0.0, daily=False, thresh=0.0):
        self.risk, self.safe, self.lev = risk, safe, lev
        self.lev_mult = float(lev_mult)
        self.measure = dict(measure or {"i": "rv", "n": 21, "gt": 0})
        self.measure.setdefault("gt", 0)
        self.target, self.cap, self.floor = float(target), float(cap), float(floor)
        self.sig = sig or risk
        self.step = float(step)
        self.daily = daily
        self.thresh = float(thresh)

    def initialize(self, ctx):
        self.cond = Cond(self.measure, self.sig)
        self.cur = None

    def weights(self, ctx, rebalance_day):
        v = self.cond.value(ctx)
        if v is None or v <= 0:
            e = 1.0
        else:
            if self.measure["i"].startswith("vix"):
                v = v / 100.0
            e = min(self.cap, max(self.floor, self.target / v))
        if self.step > 0:
            e = round(e / self.step) * self.step
        if not rebalance_day:
            if self.cur is None or abs(e - self.cur) < max(self.thresh, 1e-9):
                return None
        self.cur = e
        w: dict = {}
        if e <= 1.0 or not self.lev:
            e = min(e, 1.0)
            w[self.risk] = e
            if self.safe and e < 1.0:
                w[self.safe] = 1.0 - e
        else:
            x = (e - 1.0) / (self.lev_mult - 1.0)
            x = min(1.0, x)
            w[self.lev] = x
            if x < 1.0:
                w[self.risk] = 1.0 - x
        return _resolve(ctx, w)


register_signal("mean_reversion.volscale", lambda p: VolScale(**p),
                lambda p: list(dict.fromkeys([p.get("risk", "SPY")] + ([p["lev"]] if p.get("lev") else [])
                                             + (p["safe"].split("|") if p.get("safe") else [])
                                             + ([p["sig"]] if p.get("sig") else []))))


# --------------------------------------------------------------------------
# 5. tax-aware dip ladder (custom strategy kind)
# --------------------------------------------------------------------------
class DipLadder(Strategy):
    """Start in `core` weights. Each `levels[k]` (a list of conditions, all
    must hold) fires at most once per episode and moves `tranche[k]` x portfolio
    value from the `fund` asset into the `dip` asset. A tranche is released
    (sold back into the fund asset) once it is >= `min_hold` calendar days old
    and any `release` condition holds; with no release conditions tranches are
    held forever. All levels re-arm when any `rearm` condition holds."""

    def __init__(self, core, fund, dip, levels, tranche, sig="SPY", min_hold=366, release=(),
                 rearm=(), lag=0, release_mode="any", max_hold=0):
        self.core = dict(core)
        self.fund = fund
        self.dip = dip
        self.levels_d = [list(l) for l in levels]
        self.tranche = list(tranche)
        self.sig = sig
        self.min_hold = int(min_hold)
        self.release_d = list(release or [])
        self.rearm_d = list(rearm or [])
        self.lag = int(lag)
        self.max_hold = int(max_hold or 0)

    def initialize(self, ctx):
        self.levels = [_conds(l, self.sig) for l in self.levels_d]
        self.release = _conds(self.release_d, self.sig)
        self.rearm = _conds(self.rearm_d, self.sig)
        self.fired = [False] * len(self.levels)
        self.tranches: list = []          # [date, shares, dip_ticker]
        self.started = False

    def _cost(self, ctx):
        return (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)

    def _buy_value(self, ctx, t, value):
        px = ctx.price(t)
        if px is None or value <= 0:
            return 0.0
        q = value / (px * self._cost(ctx)) * 0.999999
        before = ctx.shares(t)
        ctx.order(t, q)
        return ctx.shares(t) - before

    def _fund_tickers(self):
        return self.fund.split("|")

    def _settle_cash(self, ctx):
        """The engine pays each January's tax bill from cash; a fully invested
        book would go negative. Sell the funding asset (then the core) to cover."""
        if ctx.cash >= -1.0:
            return
        for ft in self._fund_tickers() + sorted(_resolve(ctx, self.core)):
            if ctx.cash >= -1.0:
                break
            sh, px = ctx.shares(ft), ctx.price(ft)
            if sh <= 0 or px is None:
                continue
            need = -ctx.cash / (px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)) * 1.0001
            ctx.order(ft, -min(sh, need))

    def on_day(self, ctx):
        if not self.started:
            self.started = True
            w = _resolve(ctx, self.core)
            pv = ctx.portfolio_value
            for t, v in sorted(w.items()):
                self._buy_value(ctx, t, pv * v)
        self._settle_cash(ctx)
        # releases
        if self.tranches:
            rel_ok = any(c.holds(ctx, self.lag) for c in self.release) if self.release else False
            keep = []
            for tr in self.tranches:
                age = (ctx.date - tr[0]).days
                if age >= self.min_hold and (rel_ok or (self.max_hold and age >= self.max_hold)) \
                        and ctx.price(tr[2]) is not None:
                    q = min(tr[1], ctx.shares(tr[2]))
                    if q > 0:
                        before = ctx.cash
                        ctx.order(tr[2], -q)
                        got = ctx.cash - before
                        f = _resolve(ctx, {self.fund: 1.0})
                        if f:
                            self._buy_value(ctx, next(iter(f)), got)
                else:
                    keep.append(tr)
            self.tranches = keep
        # re-arm
        if any(self.fired) and self.rearm and any(c.holds(ctx, self.lag) for c in self.rearm):
            self.fired = [False] * len(self.levels)
        # new tranches
        for k, conds in enumerate(self.levels):
            if self.fired[k]:
                continue
            if conds and all(c.holds(ctx, self.lag) for c in conds):
                self.fired[k] = True
                dip = next(iter(_resolve(ctx, {self.dip: 1.0})), None)
                if dip is None:
                    continue
                pv = ctx.portfolio_value
                want = self.tranche[k] * pv
                raised = 0.0
                for ft in self._fund_tickers():
                    if raised >= want - 1e-6:
                        break
                    sh = ctx.shares(ft)
                    px = ctx.price(ft)
                    if sh <= 0 or px is None:
                        continue
                    need_sh = (want - raised) / (px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct))
                    q = min(sh, need_sh)
                    before = ctx.cash
                    ctx.order(ft, -q)
                    raised += ctx.cash - before
                spend = min(ctx.cash, raised)
                got = self._buy_value(ctx, dip, spend)
                if got > 0:
                    self.tranches.append([ctx.date, got, dip])


def _ladder_build(c):
    keys = ("core", "fund", "dip", "levels", "tranche", "sig", "min_hold", "release", "rearm", "lag",
            "max_hold")
    return DipLadder(**{k: c[k] for k in keys if k in c})


def _ladder_tickers(c):
    t = _chain_tickers(c["core"]) + c["fund"].split("|") + c["dip"].split("|") + [c.get("sig", "SPY")]
    for lv in c["levels"]:
        t += _cond_srcs(lv)
    t += _cond_srcs(c.get("release")) + _cond_srcs(c.get("rearm"))
    return list(dict.fromkeys(t + ["SPY"]))


register_kind("mean_reversion.ladder", _ladder_build, _ladder_tickers)

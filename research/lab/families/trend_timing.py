"""Market timing / trend following on broad US equity (family: trend_timing).

One signal, ``Timing``, holds a risk allocation (SPY, VFINX, ...) while a trend
rule -- or the combination of several -- says "on", and a safe asset (bills,
bonds, gold; a fallback *chain* for funds that launched later) otherwise.

Rules (vectorised once per price series, then read at today's bar)
------------------------------------------------------------------
  sma     close vs SMA(n)                      {"r": "sma", "n": 200}
  ema     close vs EMA(n)                      {"r": "ema", "n": 200}
  cross   MA(fast) vs MA(slow), ma sma|ema     {"r": "cross", "fast": 50, "slow": 200}
  msma    Faber: last month-end close vs the mean of the last k month-end closes
                                               {"r": "msma", "k": 10}
  tsmom   L-bar total return vs a hurdle: "zero", "tbill" (^IRX, lagged a day)
          or a ticker's own L-bar return       {"r": "tsmom", "L": 252, "hurdle": "tbill"}
  mtsmom  same on month-end closes (k months)  {"r": "mtsmom", "k": 12}
  donch   Donchian: on at an `entry`-bar closing high, off at an `exit`-bar
          closing low                          {"r": "donch", "entry": 252, "exit": 126}
  macd    MACD(fast, slow) vs its signal line ("signal") or vs 0 ("zero")
                                               {"r": "macd", "fast": 12, "slow": 26, "sp": 9}
  ddsma   crash filter: off only if close < SMA(n) AND the close is more than
          `dd` below its `hi`-bar high; on when close > SMA(n)
                                               {"r": "ddsma", "n": 200, "dd": 0.1, "hi": 252}
  volsma  off only if close < SMA(n) AND realized vol(m) > v; on above SMA
                                               {"r": "volsma", "n": 200, "m": 21, "v": 0.2}
  Every rule takes "band" (or "bu"/"bd": separate entry/exit hysteresis) and
  "k_on"/"k_off": the condition must hold on that many consecutive evaluations
  before the state flips (confirmation delay).

Signal options
--------------
  every     "D" (daily), "W" / "M" (first trading day of the week / month)
  lag       evaluate on the bar `lag` days before today (execution-delay check)
  combine   "mean" (partial exposure = share of rules on), "all", "any", "vote"
  base      always keep this much in the risk asset: e = base + (1 - base) * e
  sig       ticker the rules read (default: the first risk ticker); "^GSPC" etc.
            are read lagged one day (blocks.asof convention)
  safe      None (cash, 0%), a ticker, or a list = fallback chain (the first one
            already trading; once held, it is kept -- "sticky")
  warm      on the first day of a window the rule states are replayed over the
            previous `warm` bars, so a window starts in the state a follower of
            the rule would actually be in (matters for bands / Donchian / delays)

Nothing reads the future: a bar i is used only once the engine is on or after
its date (index series: strictly after), and every indicator at bar i uses
closes <= bar i only. Orders fill at today's close (the engine convention).

Kind ``trend_timing.taxaware``: the same signal with a tax-aware exit. On an
exit it sells (FIFO, the engine's lot order) only the lots that are long-term
or at a loss (st_rule "hold"), or whose short-term gain is below `st_small` of
their cost (st_rule "small"); short-term-gain lots are kept and re-checked
every `recheck` period until they turn long-term or the signal turns back on.
`wash`: "ignore" (engine default: re-buy freely), "sub" (re-enter through a
different-index substitute such as VTI if the risk asset was sold at a loss in
the last 31 days), "wait" (stay out until 31 days after the loss sale).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from backtester import Strategy

from ..blocks import Signal, period_key, side_series
from ..registry import register_kind, register_signal

FAMILY = "trend_timing"


# ---------------------------------------------------------------------------
# Price sources with cached indicator arrays
# ---------------------------------------------------------------------------
class _Src:
    """Full close series of one ticker. `index=True` (a ^ series): bar i is
    usable only strictly after its date; otherwise on its date (engine
    convention: today's close is known when today's orders fill)."""

    def __init__(self, dates: np.ndarray, closes: np.ndarray, index: bool):
        self.d = dates
        self.c = closes
        self.index = index
        self.k: dict = {}

    def pos(self, dv) -> int:
        return int(self.d.searchsorted(dv, side="left" if self.index else "right"))

    def _get(self, key, fn):
        v = self.k.get(key)
        if v is None:
            v = self.k[key] = fn()
        return v

    def sma(self, n):
        def f():
            c = self.c
            out = np.full(len(c), np.nan)
            if len(c) >= n:
                cs = np.cumsum(np.r_[0.0, c])
                out[n - 1:] = (cs[n:] - cs[:-n]) / n
            return out
        return self._get(("sma", n), f)

    def ema_raw(self, n):
        return self._get(("ema_raw", n),
                         lambda: pd.Series(self.c).ewm(span=n, adjust=False).mean().to_numpy())

    def ema(self, n):
        def f():
            out = self.ema_raw(n).copy()
            out[:min(n, len(out))] = np.nan          # warm-up
            return out
        return self._get(("ema", n), f)

    def rmax(self, n):
        return self._get(("rmax", n), lambda: pd.Series(self.c).rolling(n).max().to_numpy())

    def rmin(self, n):
        return self._get(("rmin", n), lambda: pd.Series(self.c).rolling(n).min().to_numpy())

    def ret(self, L):
        def f():
            c = self.c
            out = np.full(len(c), np.nan)
            if len(c) > L:
                out[L:] = c[L:] / c[:-L] - 1.0
            return out
        return self._get(("ret", L), f)

    def vol(self, m):
        return self._get(("vol", m), lambda: (pd.Series(self.c).pct_change()
                                               .rolling(m).std(ddof=0) * math.sqrt(252)).to_numpy())

    def month_ends(self):
        """Positions of the last bar of each month (a bar is known to be a
        month end only once the next bar, in a new month, exists)."""
        def f():
            p = pd.DatetimeIndex(self.d).to_period("M")
            m = np.asarray(p.asi8)
            return np.nonzero(m[1:] != m[:-1])[0]
        return self._get(("me",), f)

    def n_me_before(self):
        """For each bar i: number of month ends strictly before i."""
        return self._get(("nme",), lambda: np.searchsorted(self.month_ends(), np.arange(len(self.c)),
                                                            side="left"))

    def first_of(self, cadence):
        """Bool array: bar i is the first bar of its week / month."""
        def f():
            idx = pd.DatetimeIndex(self.d)
            if cadence == "W":
                iso = idx.isocalendar()
                key = (iso.year.to_numpy().astype(np.int64) * 100 + iso.week.to_numpy().astype(np.int64))
            elif cadence == "M":
                key = np.asarray(idx.to_period("M").asi8)
            elif cadence == "Q":
                key = np.asarray(idx.to_period("Q").asi8)
            else:
                return np.ones(len(idx), bool)
            out = np.ones(len(idx), bool)
            out[1:] = key[1:] != key[:-1]
            return out
        return self._get(("first", cadence), f)


_INDEX_SRC: dict = {}


def _src_for(ctx, t: str) -> _Src | None:
    if t.startswith("^"):
        s = _INDEX_SRC.get(t)
        if s is None:
            ser = side_series(t)
            s = _INDEX_SRC[t] = _Src(ser.index.values, ser.to_numpy(dtype=float), True)
        return s
    m = ctx._engine.market
    cache = m.__dict__.setdefault("_tt_src", {})
    s = cache.get(t)
    if s is None:
        if "/" in t:                  # relative-strength series A/B (market tickers)
            a, b = t.split("/", 1)
            sa, sb = m.series(a, "Close"), m.series(b, "Close")
            if sa is None or sb is None:
                return None
            k = np.searchsorted(sb.index.values, sa.index.values, side="right")
            ok = k > 0
            bv = sb.to_numpy(dtype=float)
            ratio = sa.to_numpy(dtype=float)[ok] / bv[k[ok] - 1]
            s = cache[t] = _Src(sa.index.values[ok], ratio, False)
            return s
        ser = m.series(t, "Close")
        if ser is None:
            return None
        s = cache[t] = _Src(ser.index.values, ser.to_numpy(dtype=float), False)
    return s


def _bar_map(market, src: _Src, t: str) -> np.ndarray:
    """For every engine calendar day: how many bars of `t` are usable that
    day (market tickers: dated on/before the day; ^ series: strictly before)."""
    cache = market.__dict__.setdefault("_tt_map", {})
    m = cache.get(t)
    if m is None:
        m = cache[t] = np.searchsorted(src.d, market.cal_values,
                                       side="left" if src.index else "right")
    return m


def _tbill_growth(src: _Src) -> np.ndarray:
    """Cumulative log T-bill growth known before each bar's date (^IRX, lagged
    one day, accrued per trading day)."""
    def f():
        irx = side_series("^IRX")
        y = irx.to_numpy(dtype=float)
        y = np.where(np.isfinite(y), y, 0.0)
        g = np.cumsum(np.log1p(np.clip(y, 0.0, None) / 100.0 / 252.0))
        k = np.searchsorted(irx.index.values, src.d, side="left")     # obs strictly before
        out = np.where(k > 0, g[np.maximum(k - 1, 0)], np.nan)
        return out
    return src._get(("tbillG",), f)


def _aligned_ret(ctx, src: _Src, t: str, L: int) -> np.ndarray:
    """L-bar return of ticker `t` as known on each of src's bar dates."""
    def f():
        o = _src_for(ctx, t)
        r = o.ret(L)
        side = "left" if o.index else "right"
        k = np.searchsorted(o.d, src.d, side=side)
        return np.where(k > 0, r[np.maximum(k - 1, 0)], np.nan)
    return src._get(("aret", t, L), f)


# ---------------------------------------------------------------------------
# Rule arrays: (valid, up, dn, mid) booleans per bar
# ---------------------------------------------------------------------------
def _rule_arrays(ctx, src: _Src, spec: dict):
    key = ("rule", json.dumps(spec, sort_keys=True))
    hit = src.k.get(key)
    if hit is not None:
        return hit
    c = src.c
    r = spec["r"]
    band = spec.get("band", 0.0)
    bu = spec.get("bu", band)
    bd = spec.get("bd", band)
    if r == "pair":                   # enter on one rule, exit on another
        ev, eu, _ed, _em = _rule_arrays(ctx, src, spec["entry"])
        xv, _xu, xd, xm = _rule_arrays(ctx, src, spec["exit"])
        out = (ev & xv, eu.copy(), xd.copy(), xm.copy())
        src.k[key] = out
        return out
    with np.errstate(invalid="ignore", divide="ignore"):
        if r in ("sma", "ema"):
            ref = src.sma(spec["n"]) if r == "sma" else src.ema(spec["n"])
            valid = np.isfinite(ref)
            up, dn, mid = c > ref * (1 + bu), c < ref * (1 - bd), c > ref
        elif r == "cross":
            ma = src.ema if spec.get("ma", "sma") == "ema" else src.sma
            f, s = ma(spec["fast"]), ma(spec["slow"])
            valid = np.isfinite(f) & np.isfinite(s)
            up, dn, mid = f > s * (1 + bu), f < s * (1 - bd), f > s
        elif r in ("msma", "mtsmom"):
            k = spec["k"]
            me = src.month_ends()
            nb = src.n_me_before()
            cm = c[me]
            n = len(c)
            val = np.full(n, np.nan)
            has = nb >= 1
            val[has] = cm[nb[has] - 1]
            if r == "msma":
                cs = np.cumsum(np.r_[0.0, cm])
                ref = np.full(n, np.nan)
                ok = nb >= k
                ref[ok] = (cs[nb[ok]] - cs[nb[ok] - k]) / k
                valid = np.isfinite(ref) & np.isfinite(val)
                up, dn, mid = val > ref * (1 + bu), val < ref * (1 - bd), val > ref
            else:
                base = np.full(n, np.nan)
                ok = nb >= k + 1
                base[ok] = cm[nb[ok] - 1 - k]
                ret = val / base - 1.0
                h = np.zeros(n)
                hurdle = spec.get("hurdle", "zero")
                if hurdle == "tbill":
                    G = _tbill_growth(src)
                    gme = np.full(n, np.nan)
                    gme[ok] = np.exp(G[me[nb[ok] - 1]] - G[me[nb[ok] - 1 - k]]) - 1.0
                    h = gme
                ex = ret - h
                valid = np.isfinite(ex)
                up, dn, mid = ex > bu, ex < -bd, ex > 0
        elif r == "tsmom":
            L = spec["L"]
            ret = src.ret(L)
            hurdle = spec.get("hurdle", "zero")
            if hurdle == "zero":
                h = np.zeros(len(c))
            elif hurdle == "tbill":
                G = _tbill_growth(src)
                h = np.full(len(c), np.nan)
                h[L:] = np.exp(G[L:] - G[:-L]) - 1.0
            else:
                h = _aligned_ret(ctx, src, hurdle, L)
            ex = ret - h
            valid = np.isfinite(ex)
            up, dn, mid = ex > bu, ex < -bd, ex > 0
        elif r == "donch":
            hi, lo = src.rmax(spec["entry"]), src.rmin(spec["exit"])
            valid = np.isfinite(hi) & np.isfinite(lo)
            up, dn, mid = c >= hi, c <= lo, c > (hi + lo) / 2.0
        elif r == "macd":
            f, s, g = spec.get("fast", 12), spec.get("slow", 26), spec.get("sp", 9)
            m = src.ema_raw(f) - src.ema_raw(s)
            sg = pd.Series(m).ewm(span=g, adjust=False).mean().to_numpy()
            valid = np.zeros(len(c), bool)
            valid[min(len(c), s + 3 * g):] = True
            if spec.get("mode", "signal") == "zero":
                up, dn, mid = m > 0, m < 0, m > 0
            else:
                up, dn, mid = m > sg, m < sg, m > sg
        elif r == "ddsma":
            ref = src.sma(spec["n"])
            dd = c / src.rmax(spec.get("hi", 252)) - 1.0
            valid = np.isfinite(ref) & np.isfinite(dd)
            up = c > ref * (1 + bu)
            dn = (c < ref * (1 - bd)) & (dd < -spec["dd"])
            mid = c > ref
        elif r == "volsma":
            ref = src.sma(spec["n"])
            v = src.vol(spec.get("m", 21))
            valid = np.isfinite(ref) & np.isfinite(v)
            up = c > ref * (1 + bu)
            dn = (c < ref * (1 - bd)) & (v > spec["v"])
            mid = c > ref
        else:
            raise ValueError(f"unknown rule {r!r}")
    out = (np.asarray(valid, bool), np.asarray(up, bool), np.asarray(dn, bool), np.asarray(mid, bool))
    src.k[key] = out
    return out


# ---------------------------------------------------------------------------
# The signal
# ---------------------------------------------------------------------------
_RULE_KEYS = ("r", "n", "fast", "slow", "ma", "k", "L", "hurdle", "entry", "exit", "sp",
              "mode", "dd", "hi", "m", "v", "band", "bu", "bd", "k_on", "k_off")


class Timing(Signal):
    daily = True

    def __init__(self, risk="SPY", safe=None, rules=None, sig=None, every="D", lag=0,
                 combine="mean", base=0.0, warm=504, rule=None, confirm=1,
                 safe2=None, safe_sig=None, safe_rule=None, safe_every="M", **kw):
        self.risk = {risk: 1.0} if isinstance(risk, str) else dict(risk)
        self.safe = [] if not safe else ([safe] if isinstance(safe, str) else list(safe))
        # optional trend switch on the safe side: hold `safe` while `safe_rule`
        # (read on `safe_sig`) is on, else `safe2` (None = cash)
        self.safe2 = [] if not safe2 else ([safe2] if isinstance(safe2, str) else list(safe2))
        self.safe_rule = dict(safe_rule) if safe_rule else None
        self.safe_sig = safe_sig or (self.safe[-1] if self.safe else None)
        self._safe_t = (Timing(risk=self.safe_sig, rules=[self.safe_rule], every=safe_every, warm=warm)
                        if self.safe_rule and self.safe_sig else None)
        if rules is None:                              # single-rule shorthand
            spec = {"r": rule or "sma"}
            for k2, v in kw.items():
                spec[k2] = v
            rules = [spec]
        elif kw:
            raise TypeError(f"unexpected params {sorted(kw)}")
        self.rules = []
        for s in rules:
            s = dict(s)
            s.setdefault("k_on", confirm)
            s.setdefault("k_off", confirm)
            self.rules.append(s)
        self.sig = sig or next(iter(self.risk))
        self.every = every
        self.lag = int(lag)
        self.combine = combine
        self.base = float(base)
        self.warm = int(warm)

    # ---- lifecycle ----
    def initialize(self, ctx):
        self._on = None          # per-rule state (list of bool)
        self._cnt = None
        self._last_i = None
        self._pk = None
        self._e = None           # exposure from the latest evaluation
        self._e_traded = None    # exposure of the last weights handed out
        self._arrs = None        # rule arrays (fixed for a run: one market)
        self._map = None         # engine day index -> number of usable signal bars
        self._srcobj = None
        self._sst = True         # safe-side trend state (True: primary safe chain)
        self._safe_traded = None
        if self._safe_t is not None:
            self._safe_t.initialize(ctx)

    # ---- state machine ----
    def _step(self, arrs, j):
        for q, (valid, up, dn, _mid) in enumerate(arrs):
            if not valid[j]:
                continue
            spec = self.rules[q]
            if self._on[q]:
                self._cnt[q] = self._cnt[q] + 1 if dn[j] else 0
                if self._cnt[q] >= spec["k_off"]:
                    self._on[q], self._cnt[q] = False, 0
            else:
                self._cnt[q] = self._cnt[q] + 1 if up[j] else 0
                if self._cnt[q] >= spec["k_on"]:
                    self._on[q], self._cnt[q] = True, 0

    def _combine(self):
        on = self._on
        n_on = sum(1 for x in on if x)
        if self.combine == "all":
            e = 1.0 if n_on == len(on) else 0.0
        elif self.combine == "any":
            e = 1.0 if n_on > 0 else 0.0
        elif self.combine == "vote":
            e = 1.0 if n_on * 2 > len(on) else 0.0
        else:
            e = n_on / len(on)
        return self.base + (1.0 - self.base) * e

    def exposure(self, ctx):
        """Advance the rule states if today is an evaluation day; return the
        current risk exposure in [0, 1] (1.0 when no rule can be evaluated)."""
        eng = ctx._engine
        bar = self._map
        if bar is None:
            src = _src_for(ctx, self.sig)
            if src is None:
                return 1.0
            self._srcobj = src
            bar = self._map = _bar_map(eng.market, src, self.sig)
        i = int(bar[eng._i]) - 1 - self.lag
        if i < 0:
            return 1.0 if self._e is None else self._e
        if self._on is not None and i == self._last_i:
            return self._e                          # no new bar: nothing to do
        src = self._srcobj
        arrs = self._arrs
        if arrs is None:
            arrs = self._arrs = [_rule_arrays(ctx, src, s) for s in self.rules]
        if self._on is None:
            # first evaluation of this window: replay the rule over `warm` bars
            j0 = max(0, i - self.warm)
            self._on, self._cnt = [], []
            for (valid, _up, _dn, mid) in arrs:
                # first valid bar at/after j0
                vj = np.nonzero(valid[j0:i + 1])[0]
                self._on.append(bool(mid[j0 + vj[0]]) if len(vj) else True)
                self._cnt.append(0)
            if self.every in ("W", "M", "Q"):
                fo = src.first_of(self.every)
                js = np.nonzero(fo[j0 + 1:i])[0] + j0 + 1
            else:
                js = range(j0 + 1, i)
            for j in js:
                self._step(arrs, j)
            self._step(arrs, i)
            self._last_i = i
            self._pk = period_key(ctx.date, self.every) if self.every != "D" else None
        else:
            due = True
            if self.every != "D":
                pk = period_key(ctx.date, self.every)
                due = pk != self._pk
                if due:
                    self._pk = pk
            if not due:
                return self._e
            self._step(arrs, i)
            self._last_i = i
        self._e = self._combine()
        return self._e

    # ---- weights ----
    def _launched(self, ctx, t):
        m = ctx._engine.market
        return m.rows_upto(t, ctx._engine._dv) > 0

    def pick_safe(self, ctx):
        """(ticker or None, ok). ok=False: the preferred safe asset exists but
        does not trade today -- defer."""
        chain = self.safe if self._sst else self.safe2
        if not chain:
            return None, True
        pos = ctx.positions
        for t in chain:
            if pos.get(t, 0.0) > 0 and ctx.price(t) is not None:
                return t, True
        for t in chain:
            if ctx.price(t) is not None:
                return t, True
            if self._launched(ctx, t):
                return None, False
        return None, True

    def target(self, ctx, e):
        w = {}
        if e > 0:
            tot = sum(self.risk.values())
            for t, x in self.risk.items():
                if ctx.price(t) is None:
                    return None
                w[t] = e * x / tot
        if e < 1.0:
            s, ok = self.pick_safe(ctx)
            if not ok:
                return None
            if s:
                w[s] = w.get(s, 0.0) + (1.0 - e)
        return w

    def weights(self, ctx, rebalance_day):
        e = self.exposure(ctx)
        changed = e != self._e_traded
        if self._safe_t is not None:
            self._sst = self._safe_t.exposure(ctx) >= 0.5
            changed = changed or (e < 1.0 and self._sst != self._safe_traded)
        if not changed and not rebalance_day:
            return None
        w = self.target(ctx, e)
        if w is None:
            return None
        self._e_traded = e
        self._safe_traded = self._sst
        return w


def _timing_tickers(p: dict) -> list:
    risk = p.get("risk", "SPY")
    out = [risk] if isinstance(risk, str) else list(risk)
    safe = p.get("safe")
    if safe:
        out += [safe] if isinstance(safe, str) else list(safe)
    sig = p.get("sig")
    if sig and not sig.startswith("^"):
        out += sig.split("/")
    s2 = p.get("safe2")
    if s2:
        out += [s2] if isinstance(s2, str) else list(s2)
    if p.get("safe_rule"):
        ss = p.get("safe_sig") or ((p["safe"] if isinstance(p["safe"], str) else p["safe"][-1])
                                   if p.get("safe") else None)
        if ss and not ss.startswith("^"):
            out.append(ss)
    specs = p.get("rules") or [p]
    for s in specs:
        h = s.get("hurdle")
        if h and h not in ("zero", "tbill") and not h.startswith("^"):
            out.append(h)
    return list(dict.fromkeys(out))


register_signal(f"{FAMILY}.timing", lambda p: Timing(**p), _timing_tickers)


# ---------------------------------------------------------------------------
# Tax-aware exit kind
# ---------------------------------------------------------------------------
class TaxAwareTiming(Strategy):
    """Single risk ticker + optional substitute; see module docstring."""

    def __init__(self, timing: Timing, st_rule="hold", st_small=0.0, recheck="W",
                 wash="ignore", sub=None, wash_days=31, tol=0.005):
        if len(timing.risk) != 1:
            raise ValueError("taxaware timing needs exactly one risk ticker")
        if timing.safe_rule:
            raise NotImplementedError("taxaware timing does not support a safe-side switch")
        self.sig = timing
        self.risk = next(iter(timing.risk))
        self.st_rule = st_rule
        self.st_small = float(st_small)
        self.recheck = recheck
        self.wash = wash
        self.sub = sub
        self.wash_days = int(wash_days)
        self.tol = float(tol)

    def initialize(self, ctx):
        self.sig.initialize(ctx)
        self._e = None
        self._pending = False
        self._loss_sale: dict = {}
        self._rk = None
        self._mk = None

    # -- helpers
    def _risk_names(self):
        return [self.risk] + ([self.sub] if self.sub else [])

    def _net(self, ctx, px):
        return px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)

    def _sellable(self, ctx, t, force=False):
        held = ctx.shares(t)
        if held <= 0:
            return 0.0
        if force or self.st_rule == "none" or ctx._engine.tax_policy is None:
            return held
        net = self._net(ctx, ctx.price(t))
        q = 0.0
        for d, sh, cost in ctx.lots(t):
            g = net / cost - 1.0
            ok = g <= 0 or ctx.is_long_term(d) or (self.st_rule == "small" and g < self.st_small)
            if not ok:
                break
            q += sh
        return min(q, held)

    def _sell(self, ctx, t, q):
        if q <= 1e-12:
            return
        px = ctx.price(t)
        net = self._net(ctx, px)
        # realized gain of the FIFO prefix (to remember loss sales for the wash rule)
        rem, gain = q, 0.0
        for d, sh, cost in ctx.lots(t):
            if rem <= 1e-12:
                break
            take = min(rem, sh)
            gain += (net - cost) * take
            rem -= take
        ctx.order(t, -q)
        if gain < 0:
            self._loss_sale[t] = ctx.date

    def _blocked(self, ctx, t):
        d = self._loss_sale.get(t)
        return d is not None and (ctx.date - d).days <= self.wash_days

    def _buy(self, ctx, t, value):
        px = ctx.price(t)
        if px is None or value <= 0:
            return
        cm = (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)
        ctx.order(t, value / (px * cm) * 0.999999)

    # -- main
    def on_day(self, ctx):
        e = self.sig.exposure(ctx)
        changed = e != self._e
        d = ctx.date
        mk = (d.year, d.month)
        monthly = mk != self._mk
        self._mk = mk
        recheck = False
        if self._pending:
            rk = period_key(d, self.recheck)
            recheck = rk != self._rk
            self._rk = rk
        if not (changed or monthly or recheck):
            return
        names = self._risk_names()
        if any(ctx.shares(t) > 0 and ctx.price(t) is None for t in names):
            return
        if ctx.price(self.risk) is None:
            return
        safe, ok = self.sig.pick_safe(ctx)
        if not ok:
            return
        self._e = e
        pv = ctx.portfolio_value
        tol = self.tol * pv
        rv = sum(ctx.shares(t) * ctx.price(t) for t in names if ctx.shares(t) > 0)
        want = e * pv
        self._pending = False
        if rv > want + tol:                              # reduce risk, tax-aware
            need = rv - want
            for t in sorted(names, key=lambda x: (x != self.sub, x)):   # substitute first
                if need <= tol:
                    break
                px = ctx.price(t)
                if px is None or ctx.shares(t) <= 0:
                    continue
                q = min(self._sellable(ctx, t), need / px)
                self._sell(ctx, t, q)
                need -= q * px
            self._pending = need > tol
        # cash bookkeeping: cover a negative balance (January tax) from the safe
        # asset, then from sellable risk lots, finally by a forced sale.
        if ctx.cash < 0:
            short = -ctx.cash
            for t in ([safe] if safe else []) + [x for x in self.sig.safe if x != safe]:
                if short <= 0:
                    break
                px = ctx.price(t)
                if px and ctx.shares(t) > 0:
                    q = min(ctx.shares(t), short / self._net(ctx, px) * 1.0001)
                    self._sell(ctx, t, q)
                    short = -ctx.cash
            for force in (False, True):
                for t in names:
                    if ctx.cash >= 0:
                        break
                    px = ctx.price(t)
                    if px and ctx.shares(t) > 0:
                        q = min(self._sellable(ctx, t, force), -ctx.cash / self._net(ctx, px) * 1.0001)
                        self._sell(ctx, t, q)
        rv = sum(ctx.shares(t) * ctx.price(t) for t in names if ctx.shares(t) > 0)
        if rv < want - tol:                              # add risk: cash first, then safe
            need = want - rv
            if ctx.cash < need:
                for t in [x for x in self.sig.safe if ctx.shares(x) > 0]:
                    px = ctx.price(t)
                    if px is None:
                        continue
                    q = min(ctx.shares(t), (need - ctx.cash) / self._net(ctx, px))
                    self._sell(ctx, t, q)
                    if ctx.cash >= need:
                        break
            tgt = self.risk
            if self._blocked(ctx, self.risk):
                if self.wash == "sub" and self.sub and ctx.price(self.sub) is not None:
                    tgt = self.sub
                elif self.wash == "wait":
                    tgt = None
                    self._pending = True
            if tgt:
                self._buy(ctx, tgt, min(need, ctx.cash))
        # park the rest in the safe asset (keep a whisker of cash)
        if safe and ctx.cash > tol:
            self._buy(ctx, safe, ctx.cash)


def _taxaware_build(c: dict) -> Strategy:
    return TaxAwareTiming(Timing(**c["params"]), st_rule=c.get("st_rule", "hold"),
                          st_small=c.get("st_small", 0.0), recheck=c.get("recheck", "W"),
                          wash=c.get("wash", "ignore"), sub=c.get("sub"),
                          wash_days=c.get("wash_days", 31), tol=c.get("tol", 0.005))


def _taxaware_tickers(c: dict) -> list:
    out = _timing_tickers(c["params"])
    if c.get("sub"):
        out.append(c["sub"])
    return list(dict.fromkeys(out + ["SPY"]))


register_kind(f"{FAMILY}.taxaware", _taxaware_build, _taxaware_tickers)


# ---------------------------------------------------------------------------
# Labels for tables
# ---------------------------------------------------------------------------
def _rule_label(s: dict) -> str:
    r = s["r"]
    if r in ("sma", "ema"):
        x = f"{r}{s['n']}"
    elif r == "cross":
        x = f"{s.get('ma', 'sma')}x{s['fast']}/{s['slow']}"
    elif r == "msma":
        x = f"msma{s['k']}m"
    elif r == "tsmom":
        x = f"tsm{s['L']}{'' if s.get('hurdle', 'zero') == 'zero' else '-' + s['hurdle']}"
    elif r == "mtsmom":
        x = f"mtsm{s['k']}m{'' if s.get('hurdle', 'zero') == 'zero' else '-' + s['hurdle']}"
    elif r == "donch":
        x = f"donch{s['entry']}/{s['exit']}"
    elif r == "macd":
        x = f"macd{s.get('fast', 12)}/{s.get('slow', 26)}/{s.get('sp', 9)}{'z' if s.get('mode') == 'zero' else ''}"
    elif r == "ddsma":
        x = f"ddsma{s['n']}dd{s['dd']}"
    elif r == "volsma":
        x = f"volsma{s['n']}v{s['v']}"
    elif r == "pair":
        x = f"in:{_rule_label(s['entry'])}/out:{_rule_label(s['exit'])}"
    else:
        x = r
    b = s.get("band", 0)
    if "bu" in s or "bd" in s:
        x += f" b{s.get('bu', b)}/{s.get('bd', b)}"
    elif b:
        x += f" b{b}"
    ko, kf = s.get("k_on", 1), s.get("k_off", 1)
    if ko != 1 or kf != 1:
        x += f" k{ko}" if ko == kf else f" k{ko}/{kf}"
    return x


def label(cfg: dict) -> str:
    if cfg.get("kind") == "buyhold":
        return "buyhold " + "+".join(f"{k}{v:g}" for k, v in cfg["weights"].items())
    if cfg.get("kind") == "combo":
        return f"combo {cfg.get('picker')}/{cfg.get('timer')}"
    p = cfg.get("params", {})
    risk = p.get("risk", "SPY")
    risk = risk if isinstance(risk, str) else "+".join(f"{k}{v:g}" for k, v in risk.items())
    safe = p.get("safe")
    safe = "cash" if not safe else (safe if isinstance(safe, str) else ">".join(safe))
    specs = p.get("rules")
    if specs is None:
        sp = {k: v for k, v in p.items() if k in _RULE_KEYS}
        sp["r"] = p.get("rule", "sma")
        if p.get("confirm", 1) != 1:
            sp.setdefault("k_on", p["confirm"])
            sp.setdefault("k_off", p["confirm"])
        specs = [sp]
    else:
        specs = [dict(s, **({} if p.get("confirm", 1) == 1 else
                            {"k_on": s.get("k_on", p["confirm"]), "k_off": s.get("k_off", p["confirm"])}))
                 for s in specs]
    rl = ",".join(_rule_label(s) for s in specs)
    if len(specs) > 1:
        rl = f"{p.get('combine', 'mean')}[{rl}]"
    x = f"{risk}|{rl}|{p.get('every', 'D')}"
    if p.get("sig") and p.get("sig") != (risk if isinstance(risk, str) else None):
        x += f"|sig={p['sig']}"
    if p.get("lag"):
        x += f"|lag{p['lag']}"
    if p.get("base"):
        x += f"|base{p['base']}"
    x += f"|->{safe}"
    if p.get("safe_rule"):
        s2 = p.get("safe2")
        s2 = "cash" if not s2 else (s2 if isinstance(s2, str) else ">".join(s2))
        x += f"~{_rule_label(p['safe_rule'])}@{p.get('safe_sig', 'safe')}?{s2}"
    if cfg.get("kind") == f"{FAMILY}.taxaware":
        x += f"|TA:{cfg.get('st_rule', 'hold')}"
        if cfg.get("st_rule") == "small":
            x += f"{cfg.get('st_small')}"
        if cfg.get("wash", "ignore") != "ignore":
            x += f",wash={cfg['wash']}"
            if cfg.get("sub"):
                x += f">{cfg['sub']}"
    else:
        ex = cfg.get("execution", "standard")
        if ex == "tax":
            x += f"|tax gb{cfg.get('gain_budget', 0.01)}{'' if cfg.get('st_gains', True) else ' noST'}"
        if cfg.get("band"):
            x += f"|rb{cfg['band']}"
        if cfg.get("rebalance", "M") != "M":
            x += f"|reb{cfg['rebalance']}"
    return x

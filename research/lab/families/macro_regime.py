"""Macro and cross-asset regime signals (family: macro_regime).

One generic signal, ``macro_regime.switch``: a list of regime *indicators*
(each a causal 0/1 -- or [0,1] -- "risk-on" series computed from price or
yield data), combined into a risk-on fraction f, mapped to an equity weight

    eq = off_eq + (on_eq - off_eq) * f

and allocated  eq * risk + (1 - eq) * safe   (optionally next to a "core"
that is bought once and never sold, so only a sleeve is timed).

    {"kind": "weights", "signal": "macro_regime.switch",
     "params": {"risk": {"SPY": 1.0}, "safe": {"VFITX": 1.0},
                "ind": [{"type": "curve", "thr": 0.0}],
                "combine": "all", "check": "D"},
     "rebalance": "M", "execution": "standard"}

NO LOOK-AHEAD. Every indicator is computed causally on the full history of
its inputs (trailing windows, sequential state machines only) and is read with
a lag of >= 1 day: on day d the strategy uses the last indicator value dated
strictly before d (`lag` = 1, the default; lag 0 is refused). Inputs are read
straight from the data files (index series, ETFs, mutual-fund NAVs alike), so
signal-only instruments never enter the tradable market or its calendar.

Indicator types ("type"):
  curve    slope = long - short yield (default ^TNX - ^IRX), optionally
           smoothed; inversion episodes (slope < thr for `confirm` days, end
           when slope > thr + hyst for `confirm` days). Risk-off interval per
           episode: anchor="start": [start + delay, end + after) (ongoing
           episode -> open-ended), optional `cap` days; anchor="end":
           [end + delay, end + after). `min_len`: ignore shorter episodes.
  level    a series vs a fixed threshold (on_when "above"/"below").
  mom      change of a series over `look` observations: "ret" (price) or
           "diff" (yields, in points) vs `thr` (on_when "above"/"below").
  sma      a series vs its `n`-observation SMA (on_when "above"/"below"),
           hysteresis `band` (multiplicative; additive for "add": true).
  cross    fast SMA vs slow SMA of a series.
  ratio    num/den of two price series, then rule sma | mom | cross on it.
  breadth  share of `members` above their `n`-SMA (or with positive `look`
           momentum, rule "mom"); on when share >= thr ("cont": share itself).
  canary   members' 13612W momentum (or `look` return); risk-off when at least
           `k` members are negative.
Every indicator accepts "confirm" (a flip needs that many consecutive
observations) and "invert" (swap on/off). Unknown (not yet computable) values
are excluded from the vote; if nothing is known the strategy is risk-on.

Series specs: "TICKER" | {"chain": [t1, t2, ...]} (daily returns of t1 where
it exists, else t2, ...: a return-spliced proxy) | {"basket": [...]} (equal-
weight, daily-rebalanced basket of the members' returns).

combine: "all" (risk-off if any indicator is off), "any" (off only if all are
off), "vote" (off if at least `k` indicators are off), "mean" (f = average,
a proportional tilt).

Allocation extras:
  fallback  {primary: substitute}: hold the substitute while the primary does
            not trade yet (e.g. VFITX before its 1991 launch -> FGOVX); sticky:
            once held, the substitute is kept rather than swapped (no tax event).
  core      {ticker: weight}: bought on the first day, then never traded by the
            signal (its target is always its current value); the regime only
            moves the remaining sleeve between risk and safe.
  check     how often the regime is re-evaluated between rebalances
            ("D", "W", "M"); a change triggers an immediate trade.
  min_hold  calendar days that must pass after a switch before the next one.
  risk_signal {"signal": name, "params": {...}}: the risk sleeve is another
            registered signal's target weights (e.g. common.momentum), asked
            on rebalance days; the regime scales it by eq (an overlay).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .. import data
from ..blocks import Signal, normalize, period_key
from ..registry import register_signal

FAMILY = "macro_regime"

_PX: dict = {}
_IND: dict = {}


def _k(spec) -> str:
    return json.dumps(spec, sort_keys=True)


# --------------------------------------------------------------------------
# input series
# --------------------------------------------------------------------------
def _close(t: str) -> pd.Series:
    s = data.frame(t)["Close"].astype(float)
    s = s[~s.index.duplicated(keep="last")].dropna()
    if not t.startswith("^"):
        s = s[s > 0]
    return s


def series(spec) -> pd.Series:
    """Close-like series for a spec (ticker, chain or basket), causal."""
    key = _k(spec)
    s = _PX.get(key)
    if s is not None:
        return s
    if isinstance(spec, str):
        s = _close(spec)
    elif "chain" in spec or "basket" in spec:
        members = spec.get("chain") or spec.get("basket")
        rets = {t: _close(t).pct_change() for t in members}   # own-calendar returns
        df = pd.concat(rets, axis=1, sort=True)
        if "chain" in spec:
            # each member covers [its first return, the next-preferred member's
            # first return); inside its own span a missing day is a zero move
            r = pd.Series(np.nan, index=df.index)
            lim = None
            for t in members:
                col = df[t]
                f = col.first_valid_index()
                if f is None:
                    continue
                m = df.index >= f
                if lim is not None:
                    m &= df.index < lim
                r[m] = col[m].fillna(0.0)
                lim = f if lim is None else min(lim, f)
        else:
            mn = int(spec.get("min_members", 1))
            cnt = df.notna().sum(axis=1)
            r = df.mean(axis=1, skipna=True).where(cnt >= mn)
        first = r.first_valid_index()
        r = r.loc[first:]
        s = (1.0 + r.fillna(0.0)).cumprod()
    else:
        raise ValueError(f"bad series spec {spec!r}")
    _PX[key] = s
    return s


def _tickers_in(spec) -> list:
    if isinstance(spec, str):
        return [spec]
    return list(spec.get("chain") or spec.get("basket") or [])


# --------------------------------------------------------------------------
# state machines
# --------------------------------------------------------------------------
def _hyst(up: np.ndarray, dn: np.ndarray, valid: np.ndarray, confirm: int = 1) -> np.ndarray:
    """1/0 state from 'up' / 'down' conditions (NaN while invalid).

    Starts in (up or not dn) at the first valid observation; flips off after
    `confirm` consecutive dn observations, on after `confirm` consecutive up.
    """
    n = len(up)
    out = np.full(n, np.nan)
    st = None
    cu = cd = 0
    for i in range(n):
        if not valid[i]:
            if st is not None:
                out[i] = st
            continue
        if st is None:
            st = 1.0 if (up[i] or not dn[i]) else 0.0
            out[i] = st
            continue
        cu = cu + 1 if up[i] else 0
        cd = cd + 1 if dn[i] else 0
        if st == 1.0 and cd >= confirm:
            st = 0.0
        elif st == 0.0 and cu >= confirm:
            st = 1.0
        out[i] = st
    return out


def _rule_on(x: pd.Series, p: dict) -> pd.Series:
    """Apply an sma / mom / cross / level rule to series x -> 1/0/NaN series."""
    rule = p.get("rule", p.get("type"))
    above = p.get("on_when", "above") == "above"
    band = float(p.get("band", 0.0))
    add = bool(p.get("add", False))
    confirm = int(p.get("confirm", 1))
    v = x.to_numpy(dtype=float)
    if rule == "sma":
        n = int(p.get("n", 200))
        ref = x.rolling(n, min_periods=n).mean().to_numpy()
        valid = ~np.isnan(ref) & ~np.isnan(v)
        hi = ref + band if add else ref * (1 + band)
        lo = ref - band if add else ref * (1 - band)
        a, b = v > hi, v < lo
    elif rule == "cross":
        f = x.rolling(int(p.get("fast", 50)), min_periods=int(p.get("fast", 50))).mean().to_numpy()
        n = int(p.get("slow", 200))
        ref = x.rolling(n, min_periods=n).mean().to_numpy()
        valid = ~np.isnan(ref) & ~np.isnan(f)
        hi = ref + band if add else ref * (1 + band)
        lo = ref - band if add else ref * (1 - band)
        a, b = f > hi, f < lo
    elif rule == "mom":
        look = int(p.get("look", 126))
        skip = int(p.get("skip", 0))
        base = x.shift(look + skip)
        end = x.shift(skip) if skip else x
        if p.get("kind", "ret") == "diff":
            m = (end - base).to_numpy()
        else:
            m = (end / base - 1.0).to_numpy()
        thr = float(p.get("thr", 0.0))
        valid = ~np.isnan(m)
        a, b = m > thr + band, m < thr - band
    elif rule == "level":
        thr = float(p.get("thr", 0.0))
        valid = ~np.isnan(v)
        a, b = v > thr + band, v < thr - band
    else:
        raise ValueError(f"unknown rule {rule!r}")
    if not above:
        a, b = b, a
    a = np.where(valid, a, False)
    b = np.where(valid, b, False)
    return pd.Series(_hyst(a, b, valid, confirm), index=x.index)


# --------------------------------------------------------------------------
# indicators
# --------------------------------------------------------------------------
def _curve(p: dict) -> pd.Series:
    L = series(p.get("long", "^TNX"))
    S = series(p.get("short", "^IRX"))
    df = pd.concat({"L": L, "S": S}, axis=1, sort=True).ffill().dropna()
    sp = df["L"] - df["S"]
    sm = int(p.get("smooth", 1))
    if sm > 1:
        sp = sp.rolling(sm, min_periods=sm).mean()
    thr = float(p.get("thr", 0.0))
    hyst = float(p.get("hyst", 0.0))
    confirm = int(p.get("confirm", 1))
    v = sp.to_numpy()
    valid = ~np.isnan(v)
    # inverted state (1 = inverted): enters when v < thr, exits when v > thr + hyst
    inv = _hyst(np.where(valid, v < thr, False), np.where(valid, v > thr + hyst, False),
                valid, confirm)
    idx = sp.index
    # episodes from the (causal) inverted state
    eps = []
    cur = None
    for i in range(len(v)):
        s_i = inv[i]
        if s_i != s_i:
            continue
        if s_i == 1.0 and cur is None:
            cur = i
        elif s_i == 0.0 and cur is not None:
            eps.append((cur, i))
            cur = None
    if cur is not None:
        eps.append((cur, None))
    anchor = p.get("anchor", "start")
    delay = pd.Timedelta(days=int(p.get("delay", 0)))
    after = pd.Timedelta(days=int(p.get("after", 0)))
    cap = p.get("cap")
    min_len = pd.Timedelta(days=int(p.get("min_len", 0)))
    off = np.zeros(len(v), dtype=bool)
    end_all = idx[-1] + pd.Timedelta(days=1)
    for a, b in eps:
        ts = idx[a]
        te = idx[b] if b is not None else None
        if anchor == "start":
            beg = max(ts + delay, ts + min_len)
            if te is not None and te - ts < min_len:
                continue
            fin = (te + after) if te is not None else end_all
        else:                                   # anchor at un-inversion
            if te is None or te - ts < min_len:
                continue
            beg = te + delay
            fin = te + after
        if cap is not None:
            fin = min(fin, beg + pd.Timedelta(days=int(cap)))
        if fin <= beg:
            continue
        lo = idx.searchsorted(beg, side="left")
        hi = idx.searchsorted(fin, side="left")
        off[lo:hi] = True
    out = np.where(off, 0.0, 1.0)
    out = np.where(valid | off, out, np.nan)
    return pd.Series(out, index=idx)


def _breadth(p: dict) -> pd.Series:
    members = p["members"]
    n = int(p.get("n", 200))
    rule = p.get("rule", "sma")
    cols = {}
    for t in members:
        x = series(t)
        if rule == "sma":
            ref = x.rolling(n, min_periods=n).mean()
            st = (x > ref).astype(float).where(ref.notna())
        else:
            look = int(p.get("look", 252))
            m = x / x.shift(look) - 1.0
            st = (m > 0).astype(float).where(m.notna())
        cols[_k(t)] = st
    df = pd.concat(cols, axis=1, sort=True).ffill(limit=5)
    cnt = df.notna().sum(axis=1)
    share = df.mean(axis=1, skipna=True).where(cnt >= int(p.get("min_members", 3)))
    if p.get("cont"):
        return share
    q = dict(p)
    q.update(rule="level", thr=float(p.get("thr", 0.5)) - 1e-9, on_when="above")
    return _rule_on(share, q)


def _mom13612(x: pd.Series) -> pd.Series:
    r = lambda m: x / x.shift(21 * m) - 1.0   # noqa: E731
    return (12 * r(1) + 4 * r(3) + 2 * r(6) + r(12)) / 4.0


def _canary(p: dict) -> pd.Series:
    members = p["members"]
    look = p.get("look", "13612W")
    cols = {}
    for t in members:
        x = series(t)
        m = _mom13612(x) if look == "13612W" else x / x.shift(int(look)) - 1.0
        cols[_k(t)] = (m < 0).astype(float).where(m.notna())
    df = pd.concat(cols, axis=1, sort=True).ffill(limit=5)
    cnt = df.notna().sum(axis=1)
    bad = df.sum(axis=1, skipna=True)
    k = int(p.get("k", 1))
    out = (bad < k).astype(float).where(cnt >= int(p.get("min_members", 1)))
    return out


def indicator(p: dict) -> pd.Series:
    key = _k(p)
    s = _IND.get(key)
    if s is not None:
        return s
    t = p["type"]
    if t == "curve":
        s = _curve(p)
    elif t in ("sma", "mom", "cross", "level"):
        s = _rule_on(series(p["series"]), p)
    elif t == "ratio":
        a, b = series(p["num"]), series(p["den"])
        df = pd.concat({"a": a, "b": b}, axis=1, sort=True).dropna()
        q = dict(p)
        q.setdefault("rule", "sma")
        s = _rule_on(df["a"] / df["b"], q)
    elif t == "breadth":
        s = _breadth(p)
    elif t == "canary":
        s = _canary(p)
    elif t == "const":
        s = pd.Series([float(p.get("value", 1.0))], index=[pd.Timestamp("1900-01-01")])
    else:
        raise ValueError(f"unknown indicator type {t!r}")
    if p.get("invert"):
        s = 1.0 - s
    s = s.dropna()
    _IND[key] = s
    return s


def indicator_tickers(p: dict) -> list:
    t = p["type"]
    if t == "curve":
        return _tickers_in(p.get("long", "^TNX")) + _tickers_in(p.get("short", "^IRX"))
    if t in ("sma", "mom", "cross", "level"):
        return _tickers_in(p["series"])
    if t == "ratio":
        return _tickers_in(p["num"]) + _tickers_in(p["den"])
    if t in ("breadth", "canary"):
        out = []
        for m in p["members"]:
            out += _tickers_in(m)
        return out
    return []


class _Reader:
    """Fast lagged lookups into an indicator series."""

    def __init__(self, s: pd.Series):
        self.idx = s.index.values.astype("datetime64[ns]")
        self.val = s.to_numpy(dtype=float)

    def at(self, date: pd.Timestamp, lag: int):
        cut = np.datetime64(date - pd.Timedelta(days=lag - 1), "ns")
        pos = int(self.idx.searchsorted(cut, side="left"))
        if pos <= 0:
            return None
        v = self.val[pos - 1]
        return None if v != v else float(v)


# --------------------------------------------------------------------------
# the signal
# --------------------------------------------------------------------------
class MacroSwitch(Signal):
    def __init__(self, risk, safe=None, ind=(), combine="all", k=1, on_eq=1.0, off_eq=0.0,
                 check="D", lag=1, min_hold=0, fallback=None, core=None, steps=None,
                 risk_signal=None):
        self.risk = ({risk: 1.0} if isinstance(risk, str) else dict(risk)) if risk else {}
        self.risk_signal = None
        if risk_signal:
            from ..registry import SIGNALS
            self.risk_signal = SIGNALS[risk_signal["signal"]][0](risk_signal.get("params", {}))
        self.safe = ({safe: 1.0} if isinstance(safe, str) else dict(safe)) if safe else {}
        self.specs = list(ind)
        self.combine = combine
        self.k = int(k)
        self.on_eq = float(on_eq)
        self.off_eq = float(off_eq)
        self.check = check
        if int(lag) < 1:
            raise ValueError("lag must be >= 1 (no same-day use of signal inputs)")
        self.lag = int(lag)
        self.min_hold = int(min_hold)
        self.fallback = dict(fallback or {})
        self.core = dict(core or {})
        self.steps = steps
        self.daily = check is not None

    def initialize(self, ctx):
        self._readers = [_Reader(indicator(p)) for p in self.specs]
        self._eq = None
        self._last_switch = None
        self._last_check = None
        self._core_bought = False
        self._risk_w = None
        if self.risk_signal is not None:
            self.risk_signal.initialize(ctx)

    def _risk_book(self, ctx, rebalance_day):
        if self.risk_signal is None:
            return self.risk
        if rebalance_day or self._risk_w is None:
            w = self.risk_signal.weights(ctx, True)
            if w is not None:
                self._risk_w = dict(w)
        return self._risk_w or {}

    # risk-on fraction in [0, 1] (None: nothing known)
    def frac(self, date):
        vals = [r.at(date, self.lag) for r in self._readers]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        if self.combine == "all":
            return 1.0 if all(v >= 0.5 for v in vals) else 0.0
        if self.combine == "any":
            return 1.0 if any(v >= 0.5 for v in vals) else 0.0
        if self.combine == "vote":
            bad = sum(1 for v in vals if v < 0.5)
            return 0.0 if bad >= self.k else 1.0
        if self.combine == "mean":
            return float(np.mean(vals))
        raise ValueError(self.combine)

    def _target_eq(self, ctx):
        f = self.frac(ctx.date)
        if f is None:
            return self._eq if self._eq is not None else self.on_eq
        eq = self.off_eq + (self.on_eq - self.off_eq) * f
        if self.steps:
            eq = round(eq * self.steps) / self.steps
        return eq

    def _pick(self, ctx, t):
        fb = self.fallback.get(t)
        if fb is None:
            return t
        if ctx.shares(fb) > 0 and ctx.price(fb) is not None:
            return fb                              # sticky: keep the substitute
        if ctx.price(t) is not None:
            return t
        return fb if ctx.price(fb) is not None else t

    def _alloc(self, ctx, eq, rebalance_day=True):
        w: dict = {}
        sleeve = 1.0
        if self.core:
            pv = ctx.portfolio_value
            held = {t: ctx.shares(t) for t in self.core}
            if not self._core_bought or pv <= 0:
                cw = {t: x for t, x in self.core.items() if ctx.price(t) is not None}
                if len(cw) == len(self.core):
                    self._core_bought = True
            else:
                cw = {}
                for t, sh in held.items():
                    px = ctx.price(t)
                    if px is None or sh <= 0:
                        continue
                    cw[t] = sh * px / pv
            for t, x in cw.items():
                w[t] = w.get(t, 0.0) + x
            sleeve = max(0.0, 1.0 - sum(cw.values()))
        for book, frac in ((self._risk_book(ctx, rebalance_day), eq), (self.safe, 1.0 - eq)):
            if frac <= 0 or not book:
                continue
            live = {}
            for t, x in book.items():
                u = self._pick(ctx, t)
                if ctx.price(u) is not None:
                    live[u] = live.get(u, 0.0) + x
            tot = sum(book.values())
            for t, x in normalize(live, tot).items():
                w[t] = w.get(t, 0.0) + sleeve * frac * x
        return w

    def weights(self, ctx, rebalance_day):
        key = period_key(ctx.date, self.check) if self.check else None
        if not rebalance_day and key == self._last_check:
            return None
        self._last_check = key
        eq = self._target_eq(ctx)
        if (self._eq is not None and eq != self._eq and self.min_hold > 0
                and self._last_switch is not None
                and (ctx.date - self._last_switch).days < self.min_hold):
            eq = self._eq
        changed = eq != self._eq
        if changed:
            if self._eq is not None:
                self._last_switch = ctx.date
            self._eq = eq
        if not rebalance_day and not changed:
            return None
        return self._alloc(ctx, eq, rebalance_day)


def _switch_tickers(p):
    out = []
    for book in (p.get("risk"), p.get("safe"), p.get("core")):
        if not book:
            continue
        out += [book] if isinstance(book, str) else list(book)
    out += list((p.get("fallback") or {}).values())
    rs = p.get("risk_signal")
    if rs:
        from ..registry import SIGNALS
        out += list(SIGNALS[rs["signal"]][1](rs.get("params", {})))
    return list(dict.fromkeys(out))


def _switch_factory(p):
    for spec in p.get("ind", []):
        for t in indicator_tickers(spec):
            if data.path_for(t) is None:
                raise ValueError(f"no data for signal input {t}")
    return MacroSwitch(**p)


register_signal(f"{FAMILY}.switch", _switch_factory, _switch_tickers)


# --------------------------------------------------------------------------
# research helpers (not used by the strategies)
# --------------------------------------------------------------------------
def off_periods(spec, start="1986-01-01", min_days=1):
    """List the risk-off intervals of one indicator (for sanity checks)."""
    s = indicator(spec)
    s = s[s.index >= pd.Timestamp(start)]
    out = []
    cur = None
    for d, v in s.items():
        if v < 0.5 and cur is None:
            cur = d
        elif v >= 0.5 and cur is not None:
            if (d - cur).days >= min_days:
                out.append((cur.date(), d.date(), (d - cur).days))
            cur = None
    if cur is not None:
        out.append((cur.date(), None, None))
    return out


def time_off(spec, start="2000-01-01", end=data.DATA_END) -> float:
    s = indicator(spec)
    s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    return float((s < 0.5).mean()) if len(s) else float("nan")

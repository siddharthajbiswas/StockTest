"""Calendar and seasonality strategies (family 'seasonal').

Every rule here decides, at today's close (the engine's fill price), what to
hold for the NEXT trading day -- so "hold the last trading day of the month"
means buying at the close of the day before it. Which day is "next", and where
it sits in its month/quarter/year, comes from a SCHEDULED NYSE calendar built
from the exchange's published holiday rules (New Year, MLK from 1998,
Presidents', Good Friday, Memorial, Juneteenth from 2022, July 4, Labor,
Thanksgiving, Christmas, 1980 Election Day), never from the realized data
calendar. It matches the data exactly except for unscheduled closures (9/11,
Hurricane Sandy, state funerals), which a real trader could not have known in
advance either (on those days the position simply carries to the next open
day).

Signals (registered as "seasonal.*")
------------------------------------
seasonal.cal        Layered calendar switch. `layers` is an ordered list of
                    {"rule": <rule spec>, "w": <weights>}; the first layer whose
                    rule is on for the next trading day sets the target, else
                    `default`. Weights map tickers to fractions; a key "A|B|C"
                    means "the first of A, B, C that trades today" (so a series
                    of proxies can stand in before a fund existed). Optional
                    `core` = {ticker: weight} bought once and never traded again
                    (the switched satellite gets the rest of the portfolio).
                    Trades only when the state changes (plus, with
                    `rebalance_states`, on the WeightStrategy rebalance days).
seasonal.samemonth  Same-calendar-month seasonality (Heston-Sadka 2008,
                    Keloharju-Linnainmaa-Nyberg 2016): at each month turn, hold
                    the `top` menu assets with the best average return in the
                    coming calendar month over the previous `years` years
                    (optionally measured on long-history proxy series).

Rule specs ({"type": ...})
--------------------------
Calendar only (precomputed boolean masks over the scheduled calendar):
  window   {"start": [m, d], "end": [m, d]}   on from start date to end date
           (wraps the year end; Halloween = start [11,1] end [5,1])
  months   {"m": [..]}                         on in these calendar months
  kday     {"first": [a, b], "last": [c, d]}   trading day of month k (1-based)
           in [a, b], or k-th from the month end in [c, d] (turn of month =
           last [1, N] + first [1, M]); "qkday"/"ykday" = same per quarter/year
  holiday  {"pre": n, "post": m}               last n days before / first m
           days after an exchange holiday
  santa    {"dec": n, "jan": m}                last n days of Dec + first m of Jan
  pres     {"on": [a, b]}                      presidential-cycle month
           c = (year % 4) * 12 + month - 1 (0 = Jan of election year) in [a, b)
  dow      {"days": [0..4]}                    weekday of the next day (0 = Mon)
  opex     {"weeks": [k..]}                    k weeks after the monthly options
           expiration week (0 = the week containing the third Friday)
  decade   {"y": [..]}                         year % 10 in the list
  learned  {"src", "years", "thr", "min_years", "fallback", "top"}
           month m of year Y is on if the average return of month m of the
           `src` series over the previous `years` years (0 = all prior years)
           beats the threshold ("zero", or "excess" = above T-bills via ^IRX),
           or (with "top": k) if month m is among the k best months. Uses only
           years < Y, so no look-ahead.
  not / all / any                            {"r": spec} / {"rs": [spec, ...]}
Price dependent (precomputed per instrument from its own history, then read at
today's bar -- every value depends only on closes up to that bar):
  trend     {"t", "n", "mode": "sma"|"tsmom", "band"} close above its n-day SMA
            (or n-day return > 0)
  harding   {"t", "entry": [m, d], "exit": [m, d], "fast", "slow", "sig"}
            Sy Harding's Seasonal Timing Strategy: enter on the first MACD buy
            (MACD above its signal line) on/after `entry`, exit on the first
            MACD sell on/after `exit`
  barometer {"t", "kind": "jan"|"first5"|"santa", "until": [m, d]|null}
            ON (= bearish) from the barometer's last day until `until`
            (default year end) when the barometer period's return was < 0
  pension   {"eq", "bond", "last": K, "thr"} ON in the last K trading days of
            a quarter when the equity fund beat the bond fund quarter-to-date
            by more than thr (pension-rebalancing selling pressure); computed
            at runtime from closes up to today
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from ..blocks import Signal, side_series
from ..registry import register_signal

FAMILY = "seasonal"


# =============================================================================
# Scheduled NYSE calendar (rules only)
# =============================================================================
def _easter(y: int) -> dt.date:
    a = y % 19
    b, c = divmod(y, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(y, month, day)


def _nth_weekday(y, m, wd, n):
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(y, m, wd):
    d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def _observed(d: dt.date) -> dt.date:
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(y: int) -> set:
    h = set()
    ny = dt.date(y, 1, 1)
    if ny.weekday() == 6:
        h.add(dt.date(y, 1, 2))
    elif ny.weekday() < 5:
        h.add(ny)                      # Saturday New Year: no Friday closure (NYSE rule)
    if y >= 1998:
        h.add(_nth_weekday(y, 1, 0, 3))
    h.add(_nth_weekday(y, 2, 0, 3))
    h.add(_easter(y) - dt.timedelta(days=2))
    h.add(_last_weekday(y, 5, 0))
    if y >= 2022:
        h.add(_observed(dt.date(y, 6, 19)))
    h.add(_observed(dt.date(y, 7, 4)))
    h.add(_nth_weekday(y, 9, 0, 1))
    h.add(_nth_weekday(y, 11, 3, 4))
    h.add(_observed(dt.date(y, 12, 25)))
    if y == 1980:
        h.add(dt.date(1980, 11, 4))    # presidential Election Day (scheduled closure)
    return h


class _Calendar:
    def __init__(self):
        days = pd.bdate_range("1979-01-02", "2027-12-31")
        hol = set()
        for y in range(1978, 2029):
            hol |= nyse_holidays(y)
        keep = np.array([d.date() not in hol for d in days])
        S = days[keep]
        self.idx = S
        self.S = S.values.astype("datetime64[ns]")
        self.Y = S.year.values.astype(int)
        self.M = S.month.values.astype(int)
        self.D = S.day.values.astype(int)
        self.DOW = S.dayofweek.values.astype(int)
        n = len(S)

        def ranks(key):
            s = pd.Series(np.arange(n), index=key)
            g = s.groupby(level=0)
            ks = g.cumcount().values + 1
            ke = g.cumcount(ascending=False).values + 1
            return ks, ke

        self.KS, self.KE = ranks(self.Y * 12 + self.M - 1)
        self.QKS, self.QKE = ranks(self.Y * 4 + (self.M - 1) // 3)
        self.YKS, self.YKE = ranks(self.Y)
        d64 = self.S.astype("datetime64[D]")
        gap = np.busday_count(d64[:-1], d64[1:])          # weekdays in [S_i, S_i+1)
        self.PRE1 = np.r_[gap > 1, False]                  # a weekday holiday follows
        self.POST1 = np.r_[False, gap > 1]                 # a weekday holiday precedes
        self.PCM = (self.Y % 4) * 12 + (self.M - 1)
        self.MD = self.M * 100 + self.D
        # weeks after the monthly options-expiration week (third Friday)
        mon = S - pd.to_timedelta(S.dayofweek, unit="D")
        f3 = pd.DatetimeIndex([pd.Timestamp(_nth_weekday(y, m, 4, 3)) for y, m in zip(self.Y, self.M)])
        f3mon = f3 - pd.Timedelta(days=4)
        off = ((mon - f3mon).days // 7).values.astype(int)
        # days before this month's OpEx week belong to the previous month's cycle
        prev = np.where(self.M == 1, self.Y - 1, self.Y), np.where(self.M == 1, 12, self.M - 1)
        f3p = pd.DatetimeIndex([pd.Timestamp(_nth_weekday(y, m, 4, 3)) for y, m in zip(*prev)])
        offp = ((mon - (f3p - pd.Timedelta(days=4))).days // 7).values.astype(int)
        self.OPEXW = np.where(off < 0, offp, off)

    def next_index(self, dv) -> int:
        """Index of the first scheduled trading day strictly after `dv`."""
        return int(np.searchsorted(self.S, dv, side="right"))


_CAL: _Calendar | None = None


def cal() -> _Calendar:
    global _CAL
    if _CAL is None:
        _CAL = _Calendar()
    return _CAL


# =============================================================================
# Rules
# =============================================================================
_MASKS: dict = {}
_ARRS: dict = {}


def _key(spec) -> str:
    return json.dumps(spec, sort_keys=True)


class _Rule:
    tickers: tuple = ()

    def initialize(self, ctx):
        pass

    def on(self, ctx, i: int) -> bool:
        raise NotImplementedError


class _Mask(_Rule):
    def __init__(self, mask: np.ndarray):
        self.mask = mask

    def on(self, ctx, i):
        return bool(self.mask[i])


def _in_window(md: np.ndarray, start, end) -> np.ndarray:
    a = start[0] * 100 + start[1]
    b = end[0] * 100 + end[1]
    if a < b:
        return (md >= a) & (md < b)
    return (md >= a) | (md < b)


def _range(k: np.ndarray, r) -> np.ndarray:
    if not r:
        return np.zeros(len(k), bool)
    return (k >= r[0]) & (k <= r[1])


def _monthly_table(t: str) -> pd.DataFrame:
    """year x month table of monthly returns of a (side-loaded) series."""
    k = ("mt", t)
    if k not in _ARRS:
        s = side_series(t).dropna()
        me = s.groupby([s.index.year, s.index.month]).last()
        idx = me.index
        prev_ok = np.r_[False, [(a[0] * 12 + a[1]) - (b[0] * 12 + b[1]) == 1
                                for a, b in zip(idx[1:], idx[:-1])]]
        r = me.pct_change().where(prev_ok)
        _ARRS[k] = r.unstack()
    return _ARRS[k]


def _tbill_table() -> pd.DataFrame:
    k = ("tb",)
    if k not in _ARRS:
        s = side_series("^IRX").dropna()
        m = s.groupby([s.index.year, s.index.month]).mean() / 1200.0
        _ARRS[k] = m.unstack()
    return _ARRS[k]


def _learned_mask(spec) -> np.ndarray:
    c = cal()
    tab = _monthly_table(spec.get("src", "^GSPC"))
    years = int(spec.get("years", 0))
    thr = spec.get("thr", "zero")
    min_years = int(spec.get("min_years", 10))
    top = spec.get("top")
    fallback = bool(spec.get("fallback", True))
    margin = float(spec.get("margin", 0.0))
    if thr == "excess":
        tb = _tbill_table().reindex(index=tab.index, columns=tab.columns)
        tab = tab - tb
    out = np.zeros(len(c.S), bool)
    decision: dict = {}
    for Y in range(int(c.Y.min()), int(c.Y.max()) + 1):
        lo = Y - years if years > 0 else -10**9
        past = tab[(tab.index >= lo) & (tab.index < Y)]
        cnt = past.notna().sum()
        mean = past.mean()
        for m in range(1, 13):
            ok_hist = m in cnt.index and cnt[m] >= min_years
            if not ok_hist:
                decision[(Y, m)] = fallback
                continue
            if top:
                full = mean.reindex(range(1, 13))
                if full.isna().any() or (cnt.reindex(range(1, 13)) < min_years).any():
                    decision[(Y, m)] = fallback
                    continue
                order = full.sort_values(ascending=False).index[: int(top)]
                decision[(Y, m)] = m in set(order)
            else:
                decision[(Y, m)] = bool(mean[m] > margin)
    for j in range(len(c.S)):
        out[j] = decision[(c.Y[j], c.M[j])]
    return out


def _calendar_mask(spec) -> np.ndarray | None:
    """Boolean mask over the scheduled calendar, or None if `spec` needs prices."""
    k = _key(spec)
    if k in _MASKS:
        return _MASKS[k]
    c = cal()
    t = spec["type"]
    if t == "window":
        m = _in_window(c.MD, spec["start"], spec["end"])
    elif t == "months":
        m = np.isin(c.M, spec["m"])
    elif t == "kday":
        m = _range(c.KS, spec.get("first")) | _range(c.KE, spec.get("last"))
    elif t == "qkday":
        m = _range(c.QKS, spec.get("first")) | _range(c.QKE, spec.get("last"))
    elif t == "ykday":
        m = _range(c.YKS, spec.get("first")) | _range(c.YKE, spec.get("last"))
    elif t == "holiday":
        n_pre, n_post = int(spec.get("pre", 1)), int(spec.get("post", 0))
        m = np.zeros(len(c.S), bool)
        for s in range(n_pre):                  # the last n_pre days before a holiday
            m |= np.r_[c.PRE1[s:], np.zeros(s, bool)]
        for s in range(n_post):                 # the first n_post days after one
            m |= np.r_[np.zeros(s, bool), c.POST1[: len(c.S) - s]]
    elif t == "santa":
        m = ((c.M == 12) & (c.KE <= int(spec.get("dec", 5)))) | \
            ((c.M == 1) & (c.KS <= int(spec.get("jan", 2))))
    elif t == "pres":
        a, b = spec["on"]
        m = (c.PCM >= a) & (c.PCM < b) if a < b else (c.PCM >= a) | (c.PCM < b)
    elif t == "dow":
        m = np.isin(c.DOW, spec["days"])
    elif t == "opex":
        m = np.isin(c.OPEXW, spec["weeks"])
    elif t == "decade":
        m = np.isin(c.Y % 10, spec["y"])
    elif t == "learned":
        m = _learned_mask(spec)
    elif t == "not":
        sub = _calendar_mask(spec["r"])
        if sub is None:
            return None
        m = ~sub
    elif t in ("all", "any"):
        subs = [_calendar_mask(s) for s in spec["rs"]]
        if any(s is None for s in subs):
            return None
        m = subs[0].copy()
        for s in subs[1:]:
            m = (m & s) if t == "all" else (m | s)
    else:
        return None
    m = np.asarray(m, bool)
    _MASKS[k] = m
    return m


class _PerTicker(_Rule):
    """A rule precomputed over one market instrument's own bars."""

    def __init__(self, spec):
        self.spec = spec
        self.t = spec["t"]
        self.tickers = (self.t,)
        self.default = bool(spec.get("default", False))

    def initialize(self, ctx):
        m = ctx._engine.market
        s = m.series(self.t, "Close")
        if s is None:
            self.arr = None
            return
        k = (_key(self.spec), len(s), str(s.index[0]))
        arr = _ARRS.get(k)
        if arr is None:
            arr = _ARRS[k] = self.build(s)
        self.arr = arr
        self.market = m

    def on(self, ctx, i):
        if self.arr is None:
            return self.default
        pos = self.market.rows_upto(self.t, ctx._engine._dv) - 1
        if pos < 0:
            return self.default
        return bool(self.arr[pos])

    def build(self, s: pd.Series) -> np.ndarray:
        raise NotImplementedError


def _next_md(dates: pd.DatetimeIndex) -> np.ndarray:
    """month*100+day of the next scheduled trading day after each date."""
    c = cal()
    j = np.searchsorted(c.S, dates.values.astype("datetime64[ns]"), side="right")
    j = np.minimum(j, len(c.S) - 1)
    return c.MD[j]


class _Trend(_PerTicker):
    def build(self, s):
        x = s.to_numpy(float)
        n = int(self.spec.get("n", 200))
        band = float(self.spec.get("band", 0.0))
        if self.spec.get("mode", "sma") == "tsmom":
            ref = np.r_[np.full(n, np.nan), x[:-n]] if len(x) > n else np.full(len(x), np.nan)
        else:
            ref = pd.Series(x).rolling(n).mean().to_numpy()
        on = x > ref * (1 + band)
        on[np.isnan(ref)] = True
        return on


class _Harding(_PerTicker):
    def build(self, s):
        x = pd.Series(s.to_numpy(float))
        f, sl, sg = int(self.spec.get("fast", 12)), int(self.spec.get("slow", 26)), int(self.spec.get("sig", 9))
        macd = x.ewm(span=f, adjust=False).mean() - x.ewm(span=sl, adjust=False).mean()
        hist = (macd - macd.ewm(span=sg, adjust=False).mean()).to_numpy()
        fav = _in_window(_next_md(s.index), self.spec.get("entry", [10, 16]), self.spec.get("exit", [4, 20]))
        out = np.zeros(len(x), bool)
        on = False
        for j in range(len(x)):
            if j < sl * 3:                       # MACD needs a warm-up
                on = bool(fav[j])
            elif not on and fav[j] and hist[j] > 0:
                on = True
            elif on and not fav[j] and hist[j] < 0:
                on = False
            out[j] = on
        return out


class _Barometer(_PerTicker):
    def build(self, s):
        idx = s.index
        x = s.to_numpy(float)
        yrs = idx.year.values
        kind = self.spec.get("kind", "jan")
        until = self.spec.get("until")
        nmd = _next_md(idx)
        out = np.zeros(len(x), bool)
        for Y in np.unique(yrs):
            cur = np.nonzero(yrs == Y)[0]
            prv = np.nonzero(yrs == Y - 1)[0]
            if len(prv) < 10 or len(cur) < 10:
                continue
            if kind == "jan":
                jan = cur[idx.month.values[cur] == 1]
                if len(jan) == 0:
                    continue
                base, end = prv[-1], jan[-1]
            elif kind == "first5":
                base, end = prv[-1], cur[4]
            elif kind == "santa":
                base, end = prv[-6], cur[1]
            else:
                raise ValueError(kind)
            if x[end] / x[base] - 1.0 >= 0:
                continue
            for j in cur[cur >= end]:
                if until is not None and nmd[j] >= until[0] * 100 + until[1]:
                    break
                if j == cur[-1] and until is None:
                    break                        # last bar of the year: next day is a new year
                out[j] = True
        return out


class _Pension(_Rule):
    """In the last K trading days of a quarter, ON when the equity fund beat
    the bond fund quarter-to-date by more than `thr` (computed from closes up
    to today)."""

    def __init__(self, spec):
        self.eq, self.bond = spec["eq"], spec["bond"]
        self.k = int(spec.get("last", 5))
        self.thr = float(spec.get("thr", 0.0))
        self.side = spec.get("side", "eq")      # "eq": eq beat bond; "bond": bond beat eq
        self.tickers = (self.eq, self.bond)

    def initialize(self, ctx):
        self.m = ctx._engine.market
        self._q = None
        self._val = False

    def _qtd(self, ctx, t, qstart):
        s = self.m.series(t, "Close")
        if s is None:
            return None
        pos = self.m.rows_upto(t, ctx._engine._dv)
        iv = s.index.values
        b = int(np.searchsorted(iv, qstart, side="left")) - 1   # last bar before the quarter
        if b < 0 or pos - 1 <= b:
            return None
        return float(s.iloc[pos - 1]) / float(s.iloc[b]) - 1.0

    def on(self, ctx, i):
        c = cal()
        if c.QKE[i] > self.k:
            return False
        q0 = pd.Timestamp(int(c.Y[i]), int((c.M[i] - 1) // 3 * 3 + 1), 1).to_datetime64()
        a, b = self._qtd(ctx, self.eq, q0), self._qtd(ctx, self.bond, q0)
        if a is None or b is None:
            return False
        d = (a - b) if self.side == "eq" else (b - a)
        return d > self.thr


class _Combo(_Rule):
    def __init__(self, kind, subs):
        self.kind = kind
        self.subs = subs
        self.tickers = tuple(t for s in subs for t in s.tickers)

    def initialize(self, ctx):
        for s in self.subs:
            s.initialize(ctx)

    def on(self, ctx, i):
        vals = [s.on(ctx, i) for s in self.subs]       # evaluate all (stateless reads)
        if self.kind == "not":
            return not vals[0]
        return all(vals) if self.kind == "all" else any(vals)


def make_rule(spec) -> _Rule:
    m = _calendar_mask(spec)
    if m is not None:
        return _Mask(m)
    t = spec["type"]
    if t == "trend":
        return _Trend(spec)
    if t == "harding":
        return _Harding(spec)
    if t == "barometer":
        return _Barometer(spec)
    if t == "pension":
        return _Pension(spec)
    if t == "not":
        return _Combo("not", [make_rule(spec["r"])])
    if t in ("all", "any"):
        return _Combo(t, [make_rule(s) for s in spec["rs"]])
    raise ValueError(f"unknown seasonal rule {t!r}")


def rule_tickers(spec) -> list:
    t = spec.get("type")
    if t in ("trend", "harding", "barometer"):
        return [spec["t"]]
    if t == "pension":
        return [spec["eq"], spec["bond"]]
    if t == "not":
        return rule_tickers(spec["r"])
    if t in ("all", "any"):
        return [x for s in spec["rs"] for x in rule_tickers(s)]
    return []


# =============================================================================
# Signals
# =============================================================================
def _pick(ctx, key: str):
    for t in key.split("|"):
        if ctx.price(t) is not None:
            return t
    return None


def _resolve(ctx, w: dict) -> dict:
    out: dict = {}
    for key, wt in w.items():
        t = _pick(ctx, key)
        if t is not None and wt > 0:
            out[t] = out.get(t, 0.0) + float(wt)
    return out


class CalSignal(Signal):
    daily = True

    def __init__(self, layers, default, core=None, rebalance_states=False, cover_tax=False):
        self.layer_specs = list(layers)
        self.ws = [dict(L["w"]) for L in layers] + [dict(default)]
        self.core = dict(core or {})
        self.reb_states = bool(rebalance_states)
        # The engine pays each January's tax bill from cash even when the
        # portfolio is fully invested, i.e. it lends the tax at 0% until the
        # next sale. cover_tax=True instead sells pro rata the next day to
        # bring cash back to zero (a stricter, more realistic variant).
        self.cover_tax = bool(cover_tax)

    def initialize(self, ctx):
        self.rules = [make_rule(L["rule"]) for L in self.layer_specs]
        for r in self.rules:
            r.initialize(ctx)
        self._code = None
        self._core_done = False
        self.c = cal()

    def state(self, ctx) -> int:
        i = self.c.next_index(ctx._engine._dv)
        code = len(self.rules)
        for k, r in enumerate(self.rules):
            if r.on(ctx, i):
                code = k
                break
        return code

    def weights(self, ctx, rebalance_day):
        code = self.state(ctx)
        cover = self.cover_tax and ctx.cash < -1e-4 * max(ctx.portfolio_value, 1.0)
        if code == self._code and not (rebalance_day and self.reb_states) and not cover:
            return None
        self._code = code
        w = _resolve(ctx, self.ws[code])
        if not self.core:
            return w
        # Core: bought once, never traded again; the satellite gets the rest.
        pv = ctx.portfolio_value
        if not self._core_done:
            core = _resolve(ctx, self.core)
            if not core:
                return w
            self._core_done = True
            rest = max(0.0, 1.0 - sum(core.values()))
        else:
            core = {}
            for key in self.core:
                t = _pick(ctx, key) or key.split("|")[0]
                px = ctx.price(t)
                sh = ctx.shares(t)
                if px and sh > 0 and pv > 0:
                    core[t] = sh * px / pv
            rest = max(0.0, 1.0 - sum(core.values()))
        out = dict(core)
        for t, x in w.items():
            out[t] = out.get(t, 0.0) + x * rest
        return out


def _w_tickers(w: dict) -> list:
    return [t for k in w for t in k.split("|")]


def _cal_tickers(p) -> list:
    out = []
    for L in p["layers"]:
        out += _w_tickers(L["w"]) + rule_tickers(L["rule"])
    out += _w_tickers(p["default"]) + _w_tickers(p.get("core") or {})
    return list(dict.fromkeys(out))


class SameMonth(Signal):
    """Hold the `top` menu assets whose average return in the coming calendar
    month, over the previous `years` years, is highest. History is read from
    `proxies[t]` (a long-history series, e.g. a Fidelity Select fund for a
    sector SPDR) when given, else from t itself; only years before the current
    one are used. `min_years` of history are required, else `default` is held.
    `abs_filter`: drop picks whose seasonal average is <= 0 (their slot goes to
    `safe`). `vs`: score = average minus the same-month average of `vs`."""

    daily = True

    def __init__(self, menu, proxies=None, years=10, min_years=5, top=3,
                 default=None, abs_filter=False, safe=None, vs=None):
        self.menu = list(menu)
        self.proxies = dict(proxies or {})
        self.years = int(years)
        self.min_years = int(min_years)
        self.top = int(top)
        self.default = dict(default or {})
        self.abs_filter = bool(abs_filter)
        self.safe = safe
        self.vs = vs

    def initialize(self, ctx):
        self.c = cal()
        self._ym = None

    def _score(self, src, Y, m):
        tab = _monthly_table(src)
        if m not in tab.columns:
            return None
        lo = Y - self.years if self.years > 0 else -10**9
        col = tab.loc[(tab.index >= lo) & (tab.index < Y), m].dropna()
        if len(col) < self.min_years:
            return None
        return float(col.mean())

    def weights(self, ctx, rebalance_day):
        i = self.c.next_index(ctx._engine._dv)
        ym = (int(self.c.Y[i]), int(self.c.M[i]))
        if ym == self._ym:
            return None
        self._ym = ym
        Y, m = ym
        base = 0.0
        if self.vs:
            base = self._score(self.vs, Y, m)
            if base is None:
                return _resolve(ctx, self.default)
        sc = {}
        for t in self.menu:
            if ctx.price(t) is None:
                continue
            v = self._score(self.proxies.get(t, t), Y, m)
            if v is not None:
                sc[t] = v - base
        if len(sc) < self.top:
            return _resolve(ctx, self.default)
        picks = sorted(sc, key=lambda t: (-sc[t], t))[: self.top]
        w = {}
        for t in picks:
            if self.abs_filter and sc[t] <= 0:
                if self.safe:
                    s = _pick(ctx, self.safe)
                    if s:
                        w[s] = w.get(s, 0.0) + 1.0 / self.top
                continue
            w[t] = w.get(t, 0.0) + 1.0 / self.top
        return w


def _sm_tickers(p) -> list:
    out = list(p["menu"]) + _w_tickers(p.get("default") or {})
    if p.get("safe"):
        out += p["safe"].split("|")
    return list(dict.fromkeys(out))


register_signal(f"{FAMILY}.cal", lambda p: CalSignal(**p), _cal_tickers)
register_signal(f"{FAMILY}.samemonth", lambda p: SameMonth(**p), _sm_tickers)

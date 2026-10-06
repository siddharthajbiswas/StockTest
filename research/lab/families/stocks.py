"""Individual-stock strategies on the point-in-time S&P 500 universe
(family key: stocks).

READ THIS FIRST -- survivorship bias
-------------------------------------
The site's per-stock price files exist only for companies that still trade
(essentially today's S&P 500). The point-in-time (PIT) membership filter stops
a picker from buying a stock before it joined the index, but it cannot bring
back the members that were later acquired, went bankrupt or were dropped: on
2000-01-01 only ~39% of the index has price data, ~55% in 2010, ~78% in 2020.
Every number this family produces is therefore an UPPER BOUND. The quantity of
interest is never "strategy vs SPY" alone but

    strategy  -  random control  (same universe, same machinery)

next to calibration against real, survivorship-free funds that implement the
same rule on the real index (RSP, SPLV, SPHB, SPMO, MTUM, PDP, XLG, OEF ...).

Kinds
-----
"stocks.combo"    The site's own Combo / TaxManagedCombo classes (unchanged)
                  driven by a vectorized picker from this module over the
                  sp500-pit market:
                    {"kind": "stocks.combo", "signal": "mom",
                     "params": {"lookback": 252, "skip": 21},
                     "top_n": 20, "rebalance": "Q",
                     "trade_rule": "standard" | "tax_managed",
                     "gain_budget": 0.01, "wash_days": 31,
                     "timer": "buy_hold" | "mkt_sma" | "stock_sma" | <site timer>,
                     "timer_params": {...},
                     "shadow_seed": null | int}
"stocks.weights"  The lab's WeightStrategy (standard / tax execution, bands,
                  harvesting) driven by the same pickers; adds unequal
                  weights, partial exposure and a safe-asset fallback:
                    {"kind": "stocks.weights", "signal": ..., "params": ...,
                     "top_n": 20, "weighting": "equal"|"invvol"|"beta",
                     "vol_window": 63, "fallback": null|"AGG"|"TLT",
                     "mkt_sma": null|200, "mkt_band": 0.0, "slot": false,
                     "daily": false, "rebalance": "Q", "execution": "tax", ...}

Signals ("signal", tuning in "params")
---------------------------------------
mom      trailing return; lookback/skip may be lists -> blend ("rank", "z",
         or "mean" with "wts"); risk_adj divides by realized vol; fip=True
         keeps the n smoothest paths among the top 3n (frog-in-the-pan).
rev      short-term reversal: the biggest losers over `lookback` (default 21).
high52   proximity to the `window`-day high (George-Hwang 52-week high).
vol      lowest realized volatility over `window` (reverse=True: highest).
beta     lowest beta vs SPY over `window` (reverse=True: highest).
resmom   residual momentum (Blitz-Huij-Martens): 36 monthly returns regressed
         on SPY, score = sum / std of the residuals over months t-12..t-2.
dvol     average dollar volume over `window` (a size proxy; reverse=smallest).
season   same-calendar-month return averaged over the past `years` years
         (Heston-Sadka seasonality).
random   the site's RandomPicker rule (random.Random(seed).sample(universe, n)).
all      every selectable name (equal weight of the whole PIT universe).
Common params: reverse (flip the score), sma (only names above their n-day
SMA), absmom [lookback, skip, threshold] (only names whose return beats the
threshold), mkt_sma (pick nothing while SPY is below its n-day SMA).
Universe / robustness params (all default off): size_top (keep the K largest
names by dollar volume), exclude (drop tickers, e.g. the 'stars'),
subset_frac + subset_seed (a fixed pseudo-random share of the universe: the
'random menu' hindsight check), lag (signals read the close `lag` days before
the trade). stocks.combo also takes offset_days (shift rebalance boundaries).

"shadow_seed" wraps any picker in ShadowRandom: a TURNOVER-MATCHED random
control. Each rebalance it keeps exactly as many of its own current names as
the real picker kept of its, and fills the rest at random from the universe.
So it trades as often as the strategy but picks without any signal.

No look-ahead: every signal reads rows <= today of a forward-filled close
matrix aligned to the market calendar (the same data the engine marks
positions with); orders fill at today's close exactly as the site's pickers.
"""
from __future__ import annotations

import hashlib
import random

import numpy as np
import pandas as pd

from backtester import Combo, Picker, TaxManagedCombo, Timer

from ..blocks import Signal, WeightStrategy, normalize
from ..registry import register_kind

NAN = float("nan")


# ==========================================================================
# Dense numpy view of the market (one per MarketData, built lazily)
# ==========================================================================
class _Panel:
    def __init__(self, m):
        self.m = m
        self.col = dict(m._col)
        self.C = m.mark_values                         # days x tickers, ffilled
        with np.errstate(divide="ignore", invalid="ignore"):
            self.L = np.log(np.where(self.C > 0, self.C, np.nan))
        self.spy = self.col.get("SPY")
        self._adv = {}

    def adv(self, window: int) -> np.ndarray:
        """Rolling mean dollar volume (close x volume) over `window` rows."""
        a = self._adv.get(window)
        if a is None:
            import pandas as pd
            m = self.m
            vols = {}
            for t in m._cols:
                s = m.series(t, "Volume")
                if s is not None:
                    vols[t] = s
            V = pd.DataFrame(vols).reindex(m.calendar).reindex(columns=m._cols)
            closes = pd.DataFrame({t: m.series(t, "Close") for t in m._cols}).reindex(m.calendar)
            dv = (closes * V).rolling(window, min_periods=max(5, window * 2 // 3)).mean()
            a = self._adv[window] = dv.to_numpy(dtype=np.float32)
        return a


def panel(ctx) -> _Panel:
    m = ctx._engine.market
    p = m.__dict__.get("_stocks_panel")
    if p is None:
        p = m.__dict__["_stocks_panel"] = _Panel(m)
    return p


def _nan(k: int) -> np.ndarray:
    return np.full(k, np.nan)


_H01: dict = {}


def _h01(ticker: str, seed) -> float:
    """Stable pseudo-random number in [0, 1) for (seed, ticker) -- md5, not
    Python's per-process salted hash(), so every worker agrees."""
    k = (seed, ticker)
    v = _H01.get(k)
    if v is None:
        v = _H01[k] = int(hashlib.md5(f"{seed}:{ticker}".encode()).hexdigest()[:12], 16) / float(16 ** 12)
    return v


def _ret(P, i, J, lb, sk):
    a = i - sk - lb
    if a < 0:
        return _nan(len(J))
    return np.expm1(P.L[i - sk, J] - P.L[a, J])


def _rets(P, i, J, n):
    """Daily log returns over the last n days (n x len(J)); NaN if short."""
    if i - n < 0:
        return None
    return np.diff(P.L[i - n:i + 1][:, J], axis=0)


def _vol(P, i, J, n):
    r = _rets(P, i, J, n)
    if r is None:
        return _nan(len(J))
    return r.std(axis=0) * np.sqrt(252.0)


def _beta(P, i, J, n):
    r = _rets(P, i, J, n)
    if r is None or P.spy is None:
        return _nan(len(J))
    x = np.diff(P.L[i - n:i + 1, P.spy])
    if np.isnan(x).any():
        return _nan(len(J))
    xm = x - x.mean()
    den = float(xm @ xm)
    if den <= 0:
        return _nan(len(J))
    return (xm @ (r - r.mean(axis=0))) / den


def _rank(x):
    """Percentile ranks of the finite entries (NaN stays NaN), 0..1."""
    out = np.full(len(x), np.nan)
    ok = ~np.isnan(x)
    k = int(ok.sum())
    if k:
        o = x[ok].argsort(kind="stable").argsort(kind="stable")
        out[ok] = o / max(k - 1, 1)
    return out


def _mkt_on(P, i, n, band=0.0, prev=None, ticker_col=None):
    j = P.spy if ticker_col is None else ticker_col
    if j is None or i - n + 1 < 0:
        return True if prev is None else prev
    c = P.C[i, j]
    s = P.C[i - n + 1:i + 1, j].mean()
    if not (c == c and s == s):
        return True if prev is None else prev
    if prev is None:
        return bool(c >= s)
    if prev:
        return bool(c >= s * (1 - band))
    return bool(c > s * (1 + band))


# ==========================================================================
# The picker
# ==========================================================================
class StockPicker(Picker):
    """Vectorized cross-sectional stock ranking (see module docstring)."""

    name = "stocks"

    def __init__(self, signal="mom", lookback=252, skip=21, blend="rank", wts=None,
                 risk_adj=False, vol_window=252, window=252, reverse=False, sma=None,
                 absmom=None, mkt_sma=None, fip=False, months=36, form=12, skip_m=1,
                 years=5, seed=0, min_hist=0, parts=None, size_top=None, size_window=63,
                 exclude=None, lag=0, subset_frac=None, subset_seed=0):
        self.signal = signal
        self.lookback = lookback
        self.skip = skip
        self.blend = blend
        self.wts = wts
        self.risk_adj = risk_adj
        self.vol_window = vol_window
        self.window = window
        self.reverse = reverse
        self.sma = sma
        self.absmom = absmom
        self.mkt_sma = mkt_sma
        self.fip = fip
        self.months = months
        self.form = form
        self.skip_m = skip_m
        self.years = years
        self.seed = seed
        self.min_hist = min_hist
        self.parts = parts or []
        self.size_top = size_top
        self.size_window = size_window
        self.exclude = frozenset(exclude or ())
        self.lag = int(lag)
        self.subset_frac = subset_frac
        self.subset_seed = subset_seed
        self._rng = random.Random(seed)

    def _row(self, ctx) -> int:
        """The market row signals may read: today, or `lag` days earlier."""
        return max(0, ctx._engine._i - self.lag)

    def _restricted(self) -> bool:
        return bool(self.size_top or self.exclude or self.subset_frac is not None)

    def initialize(self, ctx):
        self._rng = random.Random(self.seed)

    # ---- scores (NaN = not eligible) --------------------------------------
    def _mom(self, P, i, J):
        lbs = list(self.lookback) if isinstance(self.lookback, (list, tuple)) else [self.lookback]
        sks = list(self.skip) if isinstance(self.skip, (list, tuple)) else [self.skip] * len(lbs)
        R = [_ret(P, i, J, lb, sk) for lb, sk in zip(lbs, sks)]
        if len(R) == 1:
            s = R[0]
        else:
            A = np.vstack(R)
            bad = np.isnan(A).any(axis=0)
            if self.blend == "mean":
                w = np.asarray(self.wts if self.wts else [1.0] * len(R), float)
                s = (w[:, None] * A).sum(axis=0) / w.sum()
            elif self.blend == "z":
                Z = []
                for row in A:
                    v = row[~bad]
                    sd = v.std() if len(v) > 1 else 0.0
                    Z.append((row - v.mean()) / sd if sd > 0 else row * 0.0)
                s = np.mean(Z, axis=0)
            else:                                   # rank
                B = A.copy()
                B[:, bad] = np.nan
                s = np.mean([_rank(row) for row in B], axis=0)
            s = np.where(bad, np.nan, s)
        if self.risk_adj:
            v = _vol(P, i, J, self.vol_window)
            s = np.where(v > 0, s / v, np.nan)
        return s

    def _resmom(self, P, i, J):
        step = 21
        k = self.months
        idx = i - step * np.arange(k, -1, -1)
        if idx[0] < 0 or P.spy is None:
            return _nan(len(J))
        Y = np.diff(P.L[idx][:, J], axis=0)           # k x nJ monthly log returns
        x = np.diff(P.L[idx, P.spy])
        if np.isnan(x).any():
            return _nan(len(J))
        xm = x - x.mean()
        Ym = Y - Y.mean(axis=0)
        beta = (xm @ Ym) / float(xm @ xm)
        resid = Ym - np.outer(xm, beta)
        F = resid[k - self.form:k - self.skip_m]
        sd = F.std(axis=0, ddof=1)
        return np.where(sd > 0, F.sum(axis=0) / sd, np.nan)

    def _season(self, P, i, J):
        acc = []
        for y in range(1, self.years + 1):
            a = i - 252 * y
            if a < 0:
                return _nan(len(J))
            acc.append(P.L[a + 21, J] - P.L[a, J])
        return np.mean(acc, axis=0)

    def score(self, P, i, J):
        sig = self.signal
        if sig == "mom":
            s = self._mom(P, i, J)
        elif sig == "rev":
            s = -_ret(P, i, J, self.lookback, 0)
        elif sig == "high52":
            w = self.window
            if i - w + 1 < 0:
                s = _nan(len(J))
            else:
                s = P.L[i, J] - P.L[i - w + 1:i + 1][:, J].max(axis=0)
        elif sig == "vol":
            s = -_vol(P, i, J, self.window)
        elif sig == "beta":
            s = -_beta(P, i, J, self.window)
        elif sig == "resmom":
            s = self._resmom(P, i, J)
        elif sig == "dvol":
            s = P.adv(self.window)[i, J].astype(float)
        elif sig == "season":
            s = self._season(P, i, J)
        elif sig == "all":
            s = np.zeros(len(J))
        elif sig == "composite":
            # rank-average of sub-signals: parts = [[signal, params, weight], ...]
            acc, wsum = None, 0.0
            for sub, prm, wt in self.parts:
                sp = StockPicker(sub, **(prm or {}))
                r = _rank(np.asarray(sp.score(P, i, J), float))
                acc = r * wt if acc is None else acc + r * wt
                wsum += wt
            s = acc / wsum
        else:
            raise ValueError(f"unknown stocks signal {sig!r}")
        if self.reverse:
            s = -s
        return s

    # ---- selection ---------------------------------------------------------
    def pool(self, ctx, universe):
        """The names this picker may choose from (minus `exclude`, size-restricted if asked)."""
        if self.exclude:
            universe = [t for t in universe if t not in self.exclude]
        if self.subset_frac is not None:
            fr = float(self.subset_frac)
            universe = [t for t in universe if _h01(t, self.subset_seed) < fr]
        if not self.size_top or not universe:
            return list(universe)
        P = panel(ctx)
        i = self._row(ctx)
        names = list(universe)
        J = np.fromiter((P.col[t] for t in names), dtype=np.int64, count=len(names))
        a = np.nan_to_num(P.adv(int(self.size_window))[i, J].astype(float), nan=-1.0)
        order = sorted(range(len(names)), key=lambda k: (-a[k], names[k]))
        keep = set(order[: int(self.size_top)])
        return [t for k, t in enumerate(names) if k in keep]

    def select(self, ctx, universe, n):
        if not universe or n <= 0:
            return []
        if self._restricted():
            universe = self.pool(ctx, universe)
            if not universe:
                return []
        if self.signal == "random":
            k = max(1, min(n, len(universe)))
            return self._rng.sample(list(universe), k)
        P = panel(ctx)
        i = self._row(ctx)
        if self.mkt_sma and not _mkt_on(P, i, int(self.mkt_sma)):
            return []
        names = list(universe)
        J = np.fromiter((P.col[t] for t in names), dtype=np.int64, count=len(names))
        s = np.asarray(self.score(P, i, J), float)
        if self.sma:
            w = int(self.sma)
            if i - w + 1 >= 0:
                ma = P.C[i - w + 1:i + 1][:, J].mean(axis=0)
                s = np.where(P.C[i, J] > ma, s, np.nan)
        if self.absmom:
            lb, sk, thr = self.absmom
            r = _ret(P, i, J, int(lb), int(sk))
            s = np.where(r > thr, s, np.nan)
        if self.min_hist:
            a = i - int(self.min_hist)
            if a < 0:
                return []
            s = np.where(np.isnan(P.L[a, J]), np.nan, s)
        ok = np.nonzero(~np.isnan(s))[0]
        if len(ok) == 0:
            return []
        if self.signal == "high52":
            # many names sit exactly AT their high in a bull market: break
            # those ties by the 12-month return, not alphabetically
            r12 = np.nan_to_num(_ret(P, i, J, 252, 0), nan=-1.0)
            order = sorted(ok.tolist(), key=lambda k: (-s[k], -r12[k], names[k]))
        else:
            order = sorted(ok.tolist(), key=lambda k: (-s[k], names[k]))
        if self.fip and self.signal == "mom":
            pre = order[: 3 * n]
            lb = self.lookback[0] if isinstance(self.lookback, (list, tuple)) else self.lookback
            sk = self.skip[0] if isinstance(self.skip, (list, tuple)) else self.skip
            if i - sk - lb >= 0:
                Jp = J[pre]
                r = np.diff(P.L[i - sk - lb:i - sk + 1][:, Jp], axis=0)
                pos = (r > 0).mean(axis=0)
                neg = (r < 0).mean(axis=0)
                tot = P.L[i - sk, Jp] - P.L[i - sk - lb, Jp]
                ident = np.sign(tot) * (neg - pos)          # low = smooth
                rank = {pre[q]: (ident[q], -s[pre[q]], names[pre[q]]) for q in range(len(pre))}
                order = sorted(pre, key=lambda k: rank[k])
        return [names[k] for k in order[:n]]


class ShadowRandom(Picker):
    """Turnover-matched random control for any picker.

    Runs the real picker only to learn how many of its names it KEPT from
    one rebalance to the next (and how many it holds); keeps that many of
    its own names (chosen at random) and fills the rest at random from the
    selectable universe. Same exposure, same churn, no signal."""

    name = "shadow_random"

    def __init__(self, inner: Picker, seed: int = 0):
        self.inner = inner
        self.seed = seed

    def initialize(self, ctx):
        self.inner.initialize(ctx)
        self._rng = random.Random(10_007 * self.seed + 17)
        self._prev = None
        self._mine: list = []

    def select(self, ctx, universe, n):
        b = self.inner.select(ctx, universe, n)
        m = len(b)
        if hasattr(self.inner, "pool"):
            universe = self.inner.pool(ctx, universe)
        keep_n = 0 if self._prev is None else len(set(b) & set(self._prev))
        self._prev = list(b)
        us = set(universe)
        cand = [t for t in self._mine if t in us]
        keep = self._rng.sample(cand, min(keep_n, len(cand)))
        ks = set(keep)
        pool = [t for t in universe if t not in ks]
        add = self._rng.sample(pool, max(0, min(m - len(keep), len(pool))))
        self._mine = keep + add
        return list(self._mine)


# ==========================================================================
# Timers
# ==========================================================================
class MktSmaTimer(Timer):
    """Long every basket name while SPY is above its n-day SMA (with an
    optional hysteresis band); flat (cash) otherwise."""

    name = "mkt_sma"

    def __init__(self, n=200, band=0.0, ticker="SPY"):
        self.n = int(n)
        self.band = float(band)
        self.ticker = ticker

    def initialize(self, ctx):
        self._day = None
        self._on = None

    def want_long(self, ctx, ticker, *, held, entry_price):
        if ctx.price(ticker) is None:
            return False
        i = ctx._engine._i
        if self._day != i:
            self._day = i
            P = panel(ctx)
            self._on = _mkt_on(P, i, self.n, self.band, self._on, P.col.get(self.ticker))
        return bool(self._on)


class StockSmaTimer(Timer):
    """Long a name while its own close is above its n-day SMA."""

    name = "stock_sma"

    def __init__(self, n=200, band=0.0):
        self.n = int(n)
        self.band = float(band)

    def want_long(self, ctx, ticker, *, held, entry_price):
        px = ctx.price(ticker)
        if px is None:
            return False
        P = panel(ctx)
        i = ctx._engine._i
        j = P.col[ticker]
        if i - self.n + 1 < 0:
            return True
        ma = P.C[i - self.n + 1:i + 1, j].mean()
        if ma != ma:
            return True
        if held:
            return px >= ma * (1 - self.band)
        return px > ma * (1 + self.band)


def _make_timer(c):
    name = c.get("timer", "buy_hold")
    tp = c.get("timer_params") or {}
    if name == "mkt_sma":
        return MktSmaTimer(**tp)
    if name == "stock_sma":
        return StockSmaTimer(**tp)
    from strategies.timers import TIMERS
    return TIMERS[name](**tp)


def _make_picker(c):
    p = StockPicker(signal=c.get("signal", "mom"), **(c.get("params") or {}))
    if c.get("shadow_seed") is not None:
        p = ShadowRandom(p, seed=int(c["shadow_seed"]))
    return p


# ==========================================================================
# Weight-based execution: unequal weights, partial exposure, safe asset
# ==========================================================================
class StockSignal(Signal):
    def __init__(self, picker, top_n=20, weighting="equal", vol_window=63, beta_window=252,
                 fallback=None, mkt_sma=None, mkt_band=0.0, slot=False, daily=False):
        self.picker = picker
        self.top_n = int(top_n)
        self.weighting = weighting
        self.vol_window = int(vol_window)
        self.beta_window = int(beta_window)
        self.fallback = fallback
        self.mkt_sma = mkt_sma
        self.mkt_band = mkt_band
        self.slot = slot
        self.daily = bool(daily and mkt_sma)

    def initialize(self, ctx):
        self.picker.initialize(ctx)
        self._on = None

    def _safe(self, ctx, frac):
        fb = self.fallback
        if fb and frac > 1e-9 and ctx.price(fb) is not None:
            return {fb: frac}
        return {}

    def weights(self, ctx, rebalance_day):
        if self.mkt_sma:
            P = panel(ctx)
            on = _mkt_on(P, ctx._engine._i, int(self.mkt_sma), self.mkt_band, self._on)
            changed = on != self._on
            self._on = on
            if not rebalance_day and not changed:
                return None
            if not on:
                return self._safe(ctx, 1.0)
        elif not rebalance_day:
            return None
        picks = self.picker.select(ctx, ctx.universe, self.top_n)
        if not picks:
            return self._safe(ctx, 1.0)
        P = panel(ctx)
        i = ctx._engine._i
        if self.weighting == "equal":
            raw = {t: 1.0 for t in picks}
        else:
            J = np.fromiter((P.col[t] for t in picks), dtype=np.int64, count=len(picks))
            if self.weighting == "invvol":
                v = _vol(P, i, J, self.vol_window)
                raw = {t: (1.0 / v[k] if v[k] == v[k] and v[k] > 0 else 0.0) for k, t in enumerate(picks)}
            elif self.weighting == "beta":
                b = _beta(P, i, J, self.beta_window)
                raw = {t: (max(float(b[k]), 0.05) if b[k] == b[k] else 0.0) for k, t in enumerate(picks)}
            else:
                raise ValueError(self.weighting)
        if self.slot:
            tot = min(1.0, len(picks) / self.top_n)
            w = normalize(raw, tot)
            w.update({k: w.get(k, 0.0) + v for k, v in self._safe(ctx, 1.0 - tot).items()})
            return w
        return normalize(raw, 1.0)


class StockWeightStrategy(WeightStrategy):
    """WeightStrategy whose loss harvesting can park the proceeds of ANY
    harvested stock in one default substitute (e.g. SPY: an index fund is not
    'substantially identical' to a single stock, so no wash sale), held until
    the next rebalance swaps it back (subject to the gain budget)."""

    def __init__(self, signal, harvest_sub=None, **kw):
        super().__init__(signal, **kw)
        self.harvest_sub = harvest_sub

    def _harvest(self, ctx):
        if self.harvest_sub:
            for t in ctx.positions:
                if t != self.harvest_sub and t not in self.substitutes:
                    self.substitutes[t] = self.harvest_sub
        return super()._harvest(ctx)


# ==========================================================================
# Kinds
# ==========================================================================
_WS_KEYS = ("rebalance", "execution", "band", "gain_budget", "wash_days", "st_gains",
            "harvest", "harvest_freq", "substitutes", "min_trade_frac")


def _shifted(base, off: int):
    """`base` (Combo / TaxManagedCombo) with every rebalance-period boundary
    moved `off` calendar days later (rebalance-timing luck)."""
    class Shifted(base):
        def _period_key(self, date):
            return base._period_key(self, date - pd.Timedelta(days=off))
    Shifted.__name__ = f"{base.__name__}Off{off}"
    return Shifted


def _combo_build(c):
    picker = _make_picker(c)
    timer = _make_timer(c)
    kw = dict(top_n=int(c.get("top_n", 20)), rebalance=c.get("rebalance", "Q"))
    off = int(c.get("offset_days", 0) or 0)
    if c.get("trade_rule", "standard") == "tax_managed":
        cls = _shifted(TaxManagedCombo, off) if off else TaxManagedCombo
        return cls(picker, timer, gain_budget=c.get("gain_budget", 0.01),
                   wash_days=c.get("wash_days", 31), **kw)
    cls = _shifted(Combo, off) if off else Combo
    return cls(picker, timer, **kw)


def _weights_build(c):
    sig = StockSignal(_make_picker(c), top_n=c.get("top_n", 20),
                      weighting=c.get("weighting", "equal"),
                      vol_window=c.get("vol_window", 63), beta_window=c.get("beta_window", 252),
                      fallback=c.get("fallback"), mkt_sma=c.get("mkt_sma"),
                      mkt_band=c.get("mkt_band", 0.0), slot=c.get("slot", False),
                      daily=c.get("daily", False))
    kw = {k: c[k] for k in _WS_KEYS if k in c}
    if c.get("harvest_sub"):
        return StockWeightStrategy(sig, harvest_sub=c["harvest_sub"], **kw)
    return WeightStrategy(sig, **kw)


def _tickers(c):
    t = ["SPY"]
    if c.get("fallback"):
        t.append(c["fallback"])
    if c.get("harvest_sub"):
        t.append(c["harvest_sub"])
    t += list((c.get("substitutes") or {}).values())
    return list(dict.fromkeys(t))


register_kind("stocks.combo", _combo_build, _tickers,
              heavy=lambda c: True, universe=lambda c: "sp500-pit")
register_kind("stocks.weights", _weights_build, _tickers,
              heavy=lambda c: True, universe=lambda c: "sp500-pit")

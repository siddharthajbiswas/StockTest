"""International and global rotation (family key "global").

Every signal here returns target weights for the lab's WeightStrategy, so
costs, tax lots, the annual settlement and the terminal liquidation tax are
the site engine's.  Nothing reads the future: prices come from np_closes /
ctx.history (clipped to today by the engine) and the T-bill hurdle from ^IRX
via blocks.asof (observations dated strictly before today).

Signals
-------
global.rot    Relative (+ optional absolute) momentum over a menu: US vs
              international (GEM-style), country rotation, regional rotation,
              "cheap country" long-term reversal, value+momentum blends.

              score       "ret"    blended trailing return (lookback list,
                                   blend "mean" or "rank"), skipping `skip` bars
                          "sharpe" blended return / realised vol(vol_window)
                          "lt_rev" minus the return over lt_lookback (skip
                                   lt_skip): buy the long-term LOSERS
                          "lt_mom" the return over lt_lookback (contrast)
                          "valmom" mean of the rank of lt_rev and of "ret"
                          "52wh"   close / max close over hi_window
              top_n       names held; `hysteresis` is added to the score of a
                          name already held (fewer, later switches)
              abs_mode    None | "zero" | "tbill" | "ticker": a pick must beat
                          0 / the T-bill return (^IRX) / abs_ticker's return
                          over abs_lookback (default: the blended momentum
                          horizon) by abs_threshold, else its slot goes to the
                          safe asset.  With `abs_signal` (e.g. "SPY") the test
                          is applied to that one asset instead and failing it
                          sends the whole rotation sleeve to safety (Antonacci's
                          Global Equities Momentum).
              safe        fallback ticker or chain (first tradable), or with
                          safe_select="mom" the best of the list by trailing
                          return over safe_lookback.  None = cash (earns 0).
              core        fixed weights held outside the rotation (e.g.
                          {"SPY": 0.5}); the rotation fills the rest.
              trend       {"ticker", "n"} SMA gate (or {"rule": "tsmom",
                          "lookback"}) on the rotation sleeve.
              breadth     "gate": sleeve to safety unless >= breadth_min of the
                          menu passes the absolute test; "scale": risky share
                          of the sleeve = share of the menu that passes.
              weighting   "equal" | "invvol" | "score"

global.ratio  US-vs-international relative-strength switch on the price ratio
              away/home: rule "sma" (ratio vs its n-day SMA, +-band), "cross"
              (fast vs slow SMA of the ratio) or "mom" (ratio return over
              lookback, +-band).  State persists between rebalances
              (hysteresis).  tilt=1 switches fully; tilt=0.7 holds 70/30 in
              favour of the leader.  Optional absolute gate to `safe`.

Execution, cadence, tax handling: the WeightStrategy keys of the config
("execution": "standard" | "tax", "gain_budget", "st_gains", "band", ...).
"""
from __future__ import annotations

import numpy as np

from ..blocks import Signal, asof, np_closes
from ..registry import register_signal

TBILL = "^IRX"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _ret(ctx, t, lookback, skip=0):
    c = np_closes(ctx, t, lookback + skip + 1)
    if len(c) < lookback + skip + 1 or c[0] <= 0:
        return None
    return float(c[len(c) - 1 - skip] / c[0] - 1.0)


def _vol(ctx, t, n):
    c = np_closes(ctx, t, n + 1)
    if len(c) < n + 1:
        return None
    r = np.diff(c) / c[:-1]
    s = float(r.std())
    return s * np.sqrt(252) if s > 0 else None


def _tbill_ret(ctx, lookback, skip=0):
    """Compounded T-bill return over `lookback` trading days ending `skip` days
    ago, from the 13-week bill yield (^IRX, percent), lagged one day."""
    a = asof(ctx, TBILL, lag_days=1, n=lookback + skip)
    if a is None or len(a) == 0:
        return None
    if skip:
        a = a[: max(0, len(a) - skip)]
    a = a[~np.isnan(a)]
    if len(a) < max(5, lookback // 3):
        return None
    y = float(np.mean(a)) / 100.0
    return (1.0 + y) ** (lookback / 252.0) - 1.0


def _as_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def _ranks01(vals: dict) -> dict:
    """Ranks scaled to [0, 1] (1 = highest value); ties broken by ticker."""
    names = sorted(vals, key=lambda t: (vals[t], t))
    n = len(names)
    if n == 1:
        return {names[0]: 1.0}
    return {t: i / (n - 1) for i, t in enumerate(names)}


def _add(w: dict, t: str, x: float) -> None:
    if x > 0:
        w[t] = w.get(t, 0.0) + x


# --------------------------------------------------------------------------
# global.rot
# --------------------------------------------------------------------------
class Rotation(Signal):
    def __init__(self, menu, lookback=252, skip=21, blend="mean", top_n=1,
                 score="ret", vol_window=63, lt_lookback=1260, lt_skip=0, hi_window=252,
                 weighting="equal", wvol_window=63,
                 abs_mode=None, abs_ticker=None, abs_threshold=0.0, abs_lookback=None,
                 abs_skip=0, abs_signal=None,
                 safe=None, safe_select=None, safe_lookback=126,
                 hysteresis=0.0, core=None, trend=None, breadth=None, breadth_min=0.5):
        self.menu = list(menu)
        self.lookbacks = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = skip
        self.blend = blend
        self.top_n = top_n
        self.score = score
        self.vol_window = vol_window
        self.lt_lookback = lt_lookback
        self.lt_skip = lt_skip
        self.hi_window = hi_window
        self.weighting = weighting
        self.wvol_window = wvol_window
        self.abs_mode = abs_mode
        self.abs_ticker = abs_ticker
        self.abs_threshold = abs_threshold
        self.abs_lookback = abs_lookback
        self.abs_skip = abs_skip
        self.abs_signal = abs_signal
        self.safe = _as_list(safe)
        self.safe_select = safe_select
        self.safe_lookback = safe_lookback
        self.hysteresis = hysteresis
        self.core = dict(core or {})
        self.trend = dict(trend) if trend else None
        self.breadth = breadth
        self.breadth_min = breadth_min

    # ---- pieces -----------------------------------------------------------
    def _mom(self, ctx, t):
        rs = [_ret(ctx, t, lb, self.skip) for lb in self.lookbacks]
        if any(r is None for r in rs):
            return None
        return rs

    def _abs_value(self, ctx, t, rs):
        if self.abs_lookback is None:
            if rs is None:
                rs = self._mom(ctx, t)
            if rs is None:
                return None, None
            hor = [(lb, self.skip) for lb in self.lookbacks]
            return float(np.mean(rs)), hor
        r = _ret(ctx, t, self.abs_lookback, self.abs_skip)
        return r, [(self.abs_lookback, self.abs_skip)]

    def _hurdle(self, ctx, hor):
        if self.abs_mode == "zero":
            return self.abs_threshold
        if self.abs_mode == "tbill":
            xs = [_tbill_ret(ctx, lb, sk) for lb, sk in hor]
            if any(x is None for x in xs):
                return self.abs_threshold        # no bill data: test vs zero
            return float(np.mean(xs)) + self.abs_threshold
        if self.abs_mode == "ticker":
            xs = [_ret(ctx, self.abs_ticker, lb, sk) for lb, sk in hor]
            if any(x is None for x in xs):
                return self.abs_threshold
            return float(np.mean(xs)) + self.abs_threshold
        raise ValueError(f"unknown abs_mode {self.abs_mode!r}")

    def _passes(self, ctx, t, rs=None):
        """Absolute-momentum test for one asset (True when no filter)."""
        if self.abs_mode is None:
            return True
        v, hor = self._abs_value(ctx, t, rs)
        if v is None:
            return True                           # no information: do not block
        return v > self._hurdle(ctx, hor)

    def _safe_w(self, ctx, amount):
        out = {}
        if amount <= 1e-12 or not self.safe:
            return out
        live = [t for t in self.safe if ctx.price(t) is not None]
        if not live:
            return out
        if self.safe_select == "mom" and len(live) > 1:
            best = None
            for t in live:
                r = _ret(ctx, t, self.safe_lookback, 0)
                if r is not None and (best is None or r > best[0]):
                    best = (r, t)
            pick = best[1] if best else live[0]
        else:
            pick = live[0]
        out[pick] = amount
        return out

    def _trend_on(self, ctx):
        tr = self.trend
        if not tr:
            return True
        t = tr.get("ticker", "SPY")
        if tr.get("rule", "sma") == "tsmom":
            lb = int(tr.get("lookback", 252))
            r = _ret(ctx, t, lb, int(tr.get("skip", 0)))
            if r is None:
                return True
            hurdle = 0.0
            if tr.get("vs") == "tbill":
                h = _tbill_ret(ctx, lb, int(tr.get("skip", 0)))
                hurdle = h if h is not None else 0.0
            return r > hurdle
        n = int(tr.get("n", 200))
        c = np_closes(ctx, t, n)
        if len(c) < n:
            return True
        return c[-1] > c.mean() * (1.0 + float(tr.get("band", 0.0)))

    def _scores(self, ctx, live):
        moms, scores = {}, {}
        if self.score in ("ret", "sharpe", "valmom"):
            for t in live:
                rs = self._mom(ctx, t)
                if rs is not None:
                    moms[t] = rs
        if self.score == "ret":
            names = list(moms)
            if not names:
                return moms, scores
            if len(self.lookbacks) == 1 or self.blend == "mean":
                scores = {t: float(np.mean(moms[t])) for t in names}
            else:                                 # rank blend, scaled to [0,1]
                per = [_ranks01({t: moms[t][k] for t in names}) for k in range(len(self.lookbacks))]
                scores = {t: float(np.mean([p[t] for p in per])) for t in names}
        elif self.score == "sharpe":
            for t, rs in moms.items():
                v = _vol(ctx, t, self.vol_window)
                if v:
                    scores[t] = float(np.mean(rs)) / v
        elif self.score in ("lt_rev", "lt_mom"):
            sgn = -1.0 if self.score == "lt_rev" else 1.0
            for t in live:
                r = _ret(ctx, t, self.lt_lookback, self.lt_skip)
                if r is not None:
                    scores[t] = sgn * r
        elif self.score == "valmom":
            lt = {}
            for t in moms:
                r = _ret(ctx, t, self.lt_lookback, self.lt_skip)
                if r is not None:
                    lt[t] = -r
            names = [t for t in moms if t in lt]
            if names:
                rv = _ranks01({t: lt[t] for t in names})
                rm = _ranks01({t: float(np.mean(moms[t])) for t in names})
                scores = {t: 0.5 * (rv[t] + rm[t]) for t in names}
        elif self.score == "52wh":
            for t in live:
                c = np_closes(ctx, t, self.hi_window)
                if len(c) >= self.hi_window and c.max() > 0:
                    scores[t] = float(c[-1] / c.max())
        else:
            raise ValueError(f"unknown score {self.score!r}")
        return moms, scores

    # ---- the signal ---------------------------------------------------------
    def weights(self, ctx, rebalance_day):
        w: dict = {}
        core_total = sum(self.core.values())
        live_core = {t: x for t, x in self.core.items() if ctx.price(t) is not None}
        if live_core:
            s = sum(live_core.values())
            for t, x in live_core.items():
                _add(w, t, core_total * x / s)
        sleeve = max(0.0, 1.0 - (core_total if live_core else 0.0))
        if sleeve <= 1e-12:
            return w

        live = [t for t in self.menu if ctx.price(t) is not None]
        moms, scores = self._scores(ctx, live)
        if not scores:
            for t, x in self._safe_w(ctx, sleeve).items():
                _add(w, t, x)
            return w

        # sleeve-level gates
        risky = sleeve
        if not self._trend_on(ctx):
            risky = 0.0
        if risky > 0 and self.abs_signal is not None and self.abs_mode is not None:
            if not self._passes(ctx, self.abs_signal):
                risky = 0.0
        if risky > 0 and self.breadth is not None and self.abs_mode is not None:
            ok = [self._passes(ctx, t, moms.get(t)) for t in scores]
            frac = float(np.mean(ok)) if ok else 0.0
            if self.breadth == "gate" and frac < self.breadth_min:
                risky = 0.0
            elif self.breadth == "scale":
                risky = sleeve * min(1.0, frac / max(self.breadth_min, 1e-9))

        if risky <= 1e-12:
            for t, x in self._safe_w(ctx, sleeve).items():
                _add(w, t, x)
            return w

        held = {t for t, sh in ctx.positions.items() if sh > 0}
        adj = {t: s + (self.hysteresis if t in held else 0.0) for t, s in scores.items()}
        order = sorted(adj, key=lambda t: (-adj[t], t))
        n_slots = min(self.top_n, len(order))
        picks = order[:n_slots]
        if self.abs_mode is not None and self.abs_signal is None:
            picks = [t for t in picks if self._passes(ctx, t, moms.get(t))]

        if picks:
            if self.weighting == "invvol":
                raw = {}
                for t in picks:
                    v = _vol(ctx, t, self.wvol_window)
                    raw[t] = 1.0 / v if v else 0.0
            elif self.weighting == "score" and self.score == "ret":
                raw = {t: max(scores[t], 0.0) + 1e-9 for t in picks}
            else:
                raw = {t: 1.0 for t in picks}
            tot = sum(raw.values())
            share = risky * len(picks) / n_slots
            if tot > 0:
                for t, x in raw.items():
                    _add(w, t, share * x / tot)
        else:
            share = 0.0
        for t, x in self._safe_w(ctx, sleeve - share).items():
            _add(w, t, x)
        return w


def _rot_tickers(p):
    out = list(p["menu"]) + list((p.get("core") or {}).keys()) + _as_list(p.get("safe"))
    if p.get("abs_ticker"):
        out.append(p["abs_ticker"])
    if p.get("abs_signal"):
        out.append(p["abs_signal"])
    if p.get("trend"):
        out.append(p["trend"].get("ticker", "SPY"))
    return [t for t in dict.fromkeys(out) if not t.startswith("^")]


register_signal("global.rot", lambda p: Rotation(**p), _rot_tickers)


# --------------------------------------------------------------------------
# global.ratio
# --------------------------------------------------------------------------
class RatioSwitch(Signal):
    def __init__(self, home="SPY", away="EFA", home_w=None, away_w=None,
                 sig_home=None, sig_away=None, rule="sma", n=200, fast=50,
                 lookback=252, skip=0, band=0.0, tilt=1.0, init="home",
                 abs_mode=None, abs_signal=None, abs_lookback=252, abs_threshold=0.0,
                 abs_ticker=None, safe=None):
        self.home_w = dict(home_w) if home_w else {home: 1.0}
        self.away_w = dict(away_w) if away_w else {away: 1.0}
        self.sig_home = sig_home or next(iter(self.home_w))
        self.sig_away = sig_away or next(iter(self.away_w))
        self.rule = rule
        self.n = n
        self.fast = fast
        self.lookback = lookback
        self.skip = skip
        self.band = band
        self.tilt = tilt
        self.init = init
        self.abs_mode = abs_mode
        self.abs_signal = abs_signal
        self.abs_lookback = abs_lookback
        self.abs_threshold = abs_threshold
        self.abs_ticker = abs_ticker
        self.safe = _as_list(safe)
        self._state = None

    def initialize(self, ctx):
        self._state = None

    def _ratio(self, ctx, n):
        a = ctx.history(self.sig_away, "Close", n + 15)
        h = ctx.history(self.sig_home, "Close", n + 15)
        if len(a) == 0 or len(h) == 0:
            return None
        j = a.index.intersection(h.index)
        r = (a.loc[j].to_numpy(dtype=float) / h.loc[j].to_numpy(dtype=float))
        return r[-n:] if len(r) >= n else None

    def _signal(self, ctx):
        """(up, down) for the away side, or None if not enough history."""
        if self.rule == "sma":
            r = self._ratio(ctx, self.n)
            if r is None:
                return None
            ref = r.mean()
            return r[-1] > ref * (1 + self.band), r[-1] < ref * (1 - self.band)
        if self.rule == "cross":
            r = self._ratio(ctx, self.n)
            if r is None:
                return None
            f, s = r[-self.fast:].mean(), r.mean()
            return f > s * (1 + self.band), f < s * (1 - self.band)
        if self.rule == "mom":
            r = self._ratio(ctx, self.lookback + self.skip + 1)
            if r is None:
                return None
            x = r[len(r) - 1 - self.skip] / r[0] - 1.0
            return x > self.band, x < -self.band
        raise ValueError(f"unknown rule {self.rule!r}")

    def _abs_ok(self, ctx):
        if self.abs_mode is None:
            return True
        sig = self.abs_signal or (self.sig_away if self._state == "away" else self.sig_home)
        r = _ret(ctx, sig, self.abs_lookback, 0)
        if r is None:
            return True
        if self.abs_mode == "zero":
            h = self.abs_threshold
        elif self.abs_mode == "tbill":
            x = _tbill_ret(ctx, self.abs_lookback, 0)
            h = (x if x is not None else 0.0) + self.abs_threshold
        else:
            x = _ret(ctx, self.abs_ticker, self.abs_lookback, 0)
            h = (x if x is not None else 0.0) + self.abs_threshold
        return r > h

    def weights(self, ctx, rebalance_day):
        sig = self._signal(ctx)
        if sig is not None:
            up, dn = sig
            if self._state is None:
                self._state = "away" if up else ("home" if dn else self.init)
            elif self._state == "home" and up:
                self._state = "away"
            elif self._state == "away" and dn:
                self._state = "home"
        state = self._state or self.init
        if not self._abs_ok(ctx):
            live = [t for t in self.safe if ctx.price(t) is not None]
            return {live[0]: 1.0} if live else {}
        fav, oth = (self.away_w, self.home_w) if state == "away" else (self.home_w, self.away_w)
        w: dict = {}
        for alloc, k in ((fav, self.tilt), (oth, 1.0 - self.tilt)):
            if k <= 1e-12:
                continue
            live = {t: x for t, x in alloc.items() if ctx.price(t) is not None}
            if not live:
                continue
            s = sum(live.values())
            for t, x in live.items():
                _add(w, t, k * x / s)
        tot = sum(w.values())
        if tot > 1.0 + 1e-9:
            w = {t: x / tot for t, x in w.items()}
        elif 0 < tot < 1.0 - 1e-9:
            w = {t: x / tot for t, x in w.items()}   # a missing sleeve: renormalise
        return w


def _ratio_tickers(p):
    hw = p.get("home_w") or {p.get("home", "SPY"): 1.0}
    aw = p.get("away_w") or {p.get("away", "EFA"): 1.0}
    out = list(hw) + list(aw) + _as_list(p.get("safe"))
    for k in ("sig_home", "sig_away", "abs_signal", "abs_ticker"):
        if p.get(k):
            out.append(p[k])
    return [t for t in dict.fromkeys(out) if not t.startswith("^")]


register_signal("global.ratio", lambda p: RatioSwitch(**p), _ratio_tickers)


# --------------------------------------------------------------------------
# Menus used by this family (pre-registered here so scripts share them).
# --------------------------------------------------------------------------
COUNTRIES_1996 = ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWM",
                  "EWN", "EWO", "EWP", "EWQ", "EWS", "EWU", "EWW"]
COUNTRIES_2000 = COUNTRIES_1996 + ["EWZ", "EWT", "EWY"]
DEVELOPED_1996 = ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWN",
                  "EWO", "EWP", "EWQ", "EWS", "EWU"]
EMERGING_2000 = ["EWM", "EWW", "EWZ", "EWT", "EWY"]
REGIONS_ETF = ["EFA", "EEM", "VGK", "VPL", "EWJ", "ILF", "EPP"]
REGIONS_MF = ["VEURX", "VPACX", "VEIEX"]          # Vanguard Europe / Pacific / EM index
INTL_MF = ["VGTSX", "PRITX", "VWIGX", "VTRIX", "FOSFX"]

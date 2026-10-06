"""Sector rotation with a pre-ETF holdout (family key: sector_deep).

One signal, `sector_deep.rotate`, covers every rule this family tests on any
sector menu (Fidelity Select / Vanguard sector mutual funds from the 1980s, the
SPDR / iShares / Vanguard sector ETFs, mixed menus):

  score       how a sector is ranked (higher = better):
                "mom"      trailing return over `lookback` days ending `skip`
                           days before the signal date (relative momentum)
                "rev"      minus that return (sector mean reversion)
                "lowvol"   minus the stdev of daily log returns over `lookback`
                "lowbeta"  minus the beta to `bench` over `lookback`
                "riskadj"  momentum / volatility over `lookback`
                "resid"    residual ("beta-adjusted") momentum: the sector's
                           return minus beta x bench return over the formation
                           window, divided by residual volatility; beta from
                           `beta_window` days
                "high52"   price / max(price over `lookback`) (52-week-high)
                "season"   mean return of the coming calendar month in each of
                           the last `season_years` years (sector seasonality)
                "random"   a reproducible random ranking per date (control)
                "ew"       every name equally (the menu itself, control)
              `lookback` may be a list: per-lookback scores are blended by
              average rank (blend="rank") or by average value (blend="mean").
  top_n       number of slots; each slot is 1/top_n of the satellite.
  filter      optional test a selected sector must also pass, else its slot
              goes to `fallback` (default: the benchmark fund):
                "abs"     own momentum > 0
                "bench"   own momentum > benchmark momentum (relative strength
                          vs the S&P 500 fund)
                "safe"    own momentum > the safe asset's momentum (dual mom.)
                "rs_sma"  price ratio sector/bench above its `sma` -day mean
                "sma"     own price above its `sma`-day mean
  fill        what fills slots when fewer than top_n names have enough
              history: "bench" (default), "cash", or "renorm" (spread over
              the names that do exist).
  keep_rank   hold buffer: a sector already held is kept while its rank is
              better than keep_rank (cuts turnover / realized gains).
  core        fraction of the portfolio permanently in `bench`
              (core-satellite).
  weighting   "equal" or "invvol" (inverse `vol_window` volatility).
  market_sma  optional market trend switch: when `bench` (lagged) is below
              its N-day mean, the whole portfolio goes to `safe`.

No look-ahead: every quantity is computed from the forward-filled close
matrix up to `lag` trading days BEFORE today (default lag=1: a mutual fund
order placed before today's 4pm cut-off can only know yesterday's NAV), and
orders fill at today's close like everything else in the engine.

Tickers in `fallback` / `safe` may be lists: the first one that trades today
is used (e.g. ["VFISX", "VFIIX"]: short-term Treasury fund from 1991-10, the
GNMA fund before that).
"""
from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd

from ..blocks import Signal, normalize
from ..registry import register_signal


# --------------------------------------------------------------------------
# Menus (documentation + convenience for sweep scripts; configs always carry
# their explicit ticker lists so every cfg is self-contained).
# --------------------------------------------------------------------------
FSEL28 = ["FSPTX", "FSELX", "FSCSX", "FBIOX", "FSPHX", "FSENX", "FSUTX", "FSRBX",
          "FSLBX", "FSPCX", "FSCPX", "FDFAX", "FSRPX", "FSDAX", "FSCHX", "FSAGX",
          "FSRFX", "FSHOX", "FIDSX", "FSTCX", "FDCPX", "FSAVX", "FSDPX", "FSLSX",
          "FBMPX", "FSHCX", "FSVLX", "FDLSX"]
VSEC4 = ["VGENX", "VGHCX", "VGPMX", "VGSIX"]
FSEL32 = FSEL28 + VSEC4
SPDR9 = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPDR11 = SPDR9 + ["XLRE", "XLC"]
ISHARES10 = ["IYW", "IYF", "IYH", "IYE", "IYC", "IYK", "IYJ", "IYM", "IDU", "IYZ"]
VANGUARD10 = ["VGT", "VHT", "VFH", "VDE", "VCR", "VDC", "VIS", "VAW", "VPU", "VOX"]
INCUMBENT22 = ["SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
               "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
# Industry-level ETFs that existed by 2001 (iShares/SPDR) -- a finer menu.
INDUSTRY_2001 = ["IBB", "IGV", "SMH", "SOXX", "IYR", "ICF", "IYZ", "IYE", "IYH", "IYF",
                 "IYK", "IYM", "IDU", "IYJ", "IYC", "IYW"]


def _first_tradable(ctx, tick):
    if tick is None:
        return None
    for t in ([tick] if isinstance(tick, str) else tick):
        if ctx.price(t) is not None:
            return t
    return None


def _as_list(x):
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


class SectorRotation(Signal):
    def __init__(self, menu, score="mom", lookback=252, skip=21, lag=1, blend="rank",
                 top_n=3, weighting="equal", vol_window=63, bench="VFINX", fill="bench",
                 filter=None, filter_lookback=None, filter_skip=None, fallback=None,
                 sma=200, core=0.0, keep_rank=None, market_sma=None, safe=None,
                 beta_window=756, season_years=10, seed=0, min_hist=None):
        self.menu = list(dict.fromkeys(menu))
        self.score = score
        self.lookbacks = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = int(skip)
        self.lag = int(lag)
        self.blend = blend
        self.top_n = int(top_n)
        self.weighting = weighting
        self.vol_window = int(vol_window)
        self.bench = bench
        self.fill = fill
        self.filter = filter
        self.filter_lookback = int(filter_lookback) if filter_lookback else self.lookbacks[0]
        self.filter_skip = int(filter_skip) if filter_skip is not None else self.skip
        self.fallback = fallback
        self.sma = int(sma)
        self.core = float(core)
        self.keep_rank = keep_rank
        self.market_sma = market_sma
        self.safe = safe
        self.beta_window = int(beta_window)
        self.season_years = int(season_years)
        self.seed = seed
        self.min_hist = min_hist

    # ---- aligned, lagged close matrix access -----------------------------
    def initialize(self, ctx):
        m = ctx._engine.market
        self._m = m
        self._mv = m.mark_values
        self._col = {t: m.col(t) for t in set(self.menu) | {self.bench}
                     | set(_as_list(self.safe)) | set(_as_list(self.fallback))}

    def _end(self, ctx):
        """Row index of the last observation the signal may use."""
        return ctx._engine._i - self.lag

    def _px(self, t, row):
        j = self._col.get(t)
        if j is None or row < 0:
            return float("nan")
        return float(self._mv[row, j])

    def _window(self, t, end, n):
        """Closes of t on rows end-n+1 .. end (n values), or None."""
        j = self._col.get(t)
        a = end - n + 1
        if j is None or a < 0:
            return None
        x = self._mv[a:end + 1, j]
        if len(x) < n or not np.isfinite(x[0]) or x[0] <= 0:
            return None
        return x

    def _ret(self, t, end, L, skip):
        e = end - skip
        a = e - L
        if a < 0:
            return None
        p1, p0 = self._px(t, e), self._px(t, a)
        if not (np.isfinite(p1) and np.isfinite(p0)) or p0 <= 0:
            return None
        return p1 / p0 - 1.0

    def _vol(self, t, end, n):
        x = self._window(t, end, n + 1)
        if x is None:
            return None
        r = np.diff(np.log(x))
        s = float(r.std())
        return s * math.sqrt(252) if s > 0 else None

    def _beta(self, t, end, n):
        x = self._window(t, end, n + 1)
        b = self._window(self.bench, end, n + 1)
        if x is None or b is None:
            return None
        r, rb = np.diff(np.log(x)), np.diff(np.log(b))
        v = float(rb.var())
        if v <= 0:
            return None
        return float(((r - r.mean()) * (rb - rb.mean())).mean() / v)

    def _resid(self, t, end, L, skip):
        n = max(self.beta_window, L)
        x = self._window(t, end, n + 1)
        b = self._window(self.bench, end, n + 1)
        if x is None or b is None:
            # fall back to the longest window both have, if >= L + 1
            return None
        r, rb = np.diff(np.log(x)), np.diff(np.log(b))
        v = float(rb.var())
        if v <= 0:
            return None
        beta = float(((r - r.mean()) * (rb - rb.mean())).mean() / v)
        e = r - beta * rb
        f = e[len(e) - L: len(e) - skip] if skip > 0 else e[len(e) - L:]
        s = float(f.std())
        if s <= 0:
            return None
        return float(f.mean() / s)

    def _season(self, ctx, t, end):
        """Mean log return of the coming calendar month over past years."""
        cal = self._m.calendar
        j = self._col.get(t)
        if j is None:
            return None
        today = ctx.date
        m = today.month
        vals = []
        for k in range(1, self.season_years + 1):
            y = today.year - k
            a = pd.Timestamp(year=y, month=m, day=1)
            b = a + pd.offsets.MonthBegin(1)
            ia = int(cal.searchsorted(a, side="left")) - 1   # last close before month
            ib = int(cal.searchsorted(b, side="left")) - 1   # last close of month
            if ia < 0 or ib > end or ib <= ia:
                continue
            p0, p1 = float(self._mv[ia, j]), float(self._mv[ib, j])
            if np.isfinite(p0) and np.isfinite(p1) and p0 > 0:
                vals.append(math.log(p1 / p0))
        need = max(3, self.season_years // 2)
        return float(np.mean(vals)) if len(vals) >= need else None

    def _one_score(self, ctx, t, end, L):
        s = self.score
        if s == "mom":
            return self._ret(t, end, L, self.skip)
        if s == "rev":
            r = self._ret(t, end, L, self.skip)
            return None if r is None else -r
        if s == "lowvol":
            v = self._vol(t, end, L)
            return None if v is None else -v
        if s == "lowbeta":
            b = self._beta(t, end, L)
            return None if b is None else -b
        if s == "riskadj":
            r = self._ret(t, end, L, self.skip)
            v = self._vol(t, end, L)
            return None if (r is None or v is None) else r / v
        if s == "resid":
            return self._resid(t, end, L, self.skip)
        if s == "high52":
            x = self._window(t, end - self.skip, L)
            if x is None:
                return None
            return float(x[-1] / np.nanmax(x))
        if s == "season":
            return self._season(ctx, t, end)
        if s == "random":
            x = self._window(t, end, L) if L else self._window(t, end, 1)
            if x is None:
                return None
            return random.Random(f"{self.seed}|{ctx.date.date()}|{t}").random()
        if s == "ew":
            x = self._window(t, end, max(1, L or 1))
            return None if x is None else 0.0
        raise ValueError(f"unknown score {s!r}")

    def _scores(self, ctx, names, end):
        per = {}
        for t in names:
            vals = [self._one_score(ctx, t, end, L) for L in self.lookbacks]
            if any(v is None or not np.isfinite(v) for v in vals):
                continue
            per[t] = vals
        if not per:
            return {}
        if len(self.lookbacks) == 1:
            return {t: v[0] for t, v in per.items()}
        ts = list(per)
        arr = np.array([per[t] for t in ts])
        if self.blend == "rank":
            ranks = arr.argsort(axis=0).argsort(axis=0)
            return {t: float(ranks[i].mean()) for i, t in enumerate(ts)}
        return {t: float(arr[i].mean()) for i, t in enumerate(ts)}

    def _passes(self, ctx, t, end):
        f = self.filter
        if f is None:
            return True
        L, sk = self.filter_lookback, self.filter_skip
        if f == "abs":
            r = self._ret(t, end, L, sk)
            return r is not None and r > 0
        if f == "bench":
            r, rb = self._ret(t, end, L, sk), self._ret(self.bench, end, L, sk)
            return r is not None and rb is not None and r > rb
        if f == "safe":
            r = self._ret(t, end, L, sk)
            s = _first_tradable(ctx, self.safe)
            rs = self._ret(s, end, L, sk) if s else 0.0
            return r is not None and r > (rs if rs is not None else 0.0)
        if f == "rs_sma":
            x = self._window(t, end, self.sma)
            b = self._window(self.bench, end, self.sma)
            if x is None or b is None:
                return False
            ratio = x / b
            return bool(ratio[-1] > ratio.mean())
        if f == "sma":
            x = self._window(t, end, self.sma)
            return x is not None and bool(x[-1] > x.mean())
        raise ValueError(f"unknown filter {f!r}")

    def _risk_off(self, ctx, end):
        if not self.market_sma:
            return False
        x = self._window(self.bench, end, int(self.market_sma))
        return x is not None and bool(x[-1] < x.mean())

    # ---- the target --------------------------------------------------------
    def weights(self, ctx, rebalance_day):
        end = self._end(ctx)
        bench = self.bench if ctx.price(self.bench) is not None else None
        if self._risk_off(ctx, end):
            s = _first_tradable(ctx, self.safe)
            return {s: 1.0} if s else {}
        live = [t for t in self.menu if ctx.price(t) is not None]
        sc = self._scores(ctx, live, end)
        order = sorted(sc, key=lambda t: (-sc[t], t))
        n = self.top_n if self.score != "ew" else max(1, len(order))
        if self.keep_rank and order:
            rank = {t: i for i, t in enumerate(order)}
            held = [t for t in order if ctx.shares(t) > 0 and rank[t] < int(self.keep_rank)]
            picks = held[:n]
            for t in order:
                if len(picks) >= n:
                    break
                if t not in picks:
                    picks.append(t)
        else:
            picks = order[:n]
        sat_w = 1.0 - self.core
        w: dict = {}
        if self.score == "ew":
            if picks:
                for t in picks:
                    w[t] = sat_w / len(picks)
            elif bench:
                w[bench] = sat_w
        else:
            fb = _first_tradable(ctx, self.fallback) if self.fallback else bench
            kept = [t for t in picks if self._passes(ctx, t, end)]
            n_fail = len(picks) - len(kept)
            n_missing = max(0, n - len(picks))
            slot = sat_w / n
            if self.fill == "renorm" and picks:
                slot = sat_w / len(picks)
                n_missing = 0
            if kept:
                if self.weighting == "invvol":
                    iv = {}
                    for t in kept:
                        v = self._vol(t, end, self.vol_window)
                        iv[t] = 1.0 / v if v else 0.0
                    iv = normalize(iv, slot * len(kept))
                    if not iv:
                        iv = {t: slot for t in kept}
                    w.update(iv)
                else:
                    for t in kept:
                        w[t] = slot
            if n_fail and fb:
                w[fb] = w.get(fb, 0.0) + slot * n_fail
            if n_missing and self.fill == "bench" and bench:
                w[bench] = w.get(bench, 0.0) + slot * n_missing
        if self.core > 0 and bench:
            w[bench] = w.get(bench, 0.0) + self.core
        return {t: v for t, v in w.items() if v > 1e-12}


def _tickers(p):
    out = list(p["menu"]) + [p.get("bench", "VFINX")]
    out += _as_list(p.get("fallback")) + _as_list(p.get("safe"))
    return list(dict.fromkeys(out))


register_signal("sector_deep.rotate", lambda p: SectorRotation(**p), _tickers)

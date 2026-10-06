"""Shared, tested signals every family can reuse (register under 'common.*').

    MomentumRotation  rank a menu by trailing return (single or blended
                      lookbacks), hold the top N (equal / inverse-vol / score
                      weighted), optional absolute-momentum filter with a
                      fallback asset.
    TrendSwitch       hold a risky allocation while a trend rule is on, a safe
                      asset (or cash) while it is off; SMA / SMA-cross / time-
                      series momentum / EMA rules, hysteresis band, optional
                      daily evaluation.
    FixedMix          a static allocation, rebalanced on the strategy cadence.
"""
from __future__ import annotations

import numpy as np

from ..blocks import Signal, np_closes, normalize
from ..registry import register_signal


def _ret(ctx, t, lookback, skip=0):
    c = np_closes(ctx, t, lookback + skip + 1)
    if len(c) < lookback + skip + 1 or c[0] <= 0:
        return None
    return c[len(c) - 1 - skip] / c[0] - 1.0


def _vol(ctx, t, n):
    c = np_closes(ctx, t, n + 1)
    if len(c) < n + 1:
        return None
    r = np.diff(c) / c[:-1]
    s = r.std()
    return s * np.sqrt(252) if s > 0 else None


class MomentumRotation(Signal):
    def __init__(self, menu, lookback=252, skip=21, top_n=5, weighting="equal",
                 vol_window=63, abs_filter=None, fallback=None, blend="rank"):
        self.menu = list(menu)
        self.lookbacks = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = skip
        self.top_n = top_n
        self.weighting = weighting
        self.vol_window = vol_window
        self.abs_filter = abs_filter
        self.fallback = fallback
        self.blend = blend

    def weights(self, ctx, rebalance_day):
        live = [t for t in self.menu if ctx.price(t) is not None]
        rets = {}
        for t in live:
            rs = [_ret(ctx, t, lb, self.skip) for lb in self.lookbacks]
            if any(r is None for r in rs):
                continue
            rets[t] = rs
        if not rets:
            fb = self.fallback
            return {fb: 1.0} if fb and ctx.price(fb) is not None else {}
        names = list(rets)
        if len(self.lookbacks) == 1:
            score = {t: rets[t][0] for t in names}
        elif self.blend == "rank":
            arr = np.array([rets[t] for t in names])           # n x k
            ranks = arr.argsort(axis=0).argsort(axis=0)        # higher = better
            score = {t: float(ranks[i].mean()) for i, t in enumerate(names)}
        else:                                                  # mean return
            score = {t: float(np.mean(rets[t])) for t in names}
        order = sorted(names, key=lambda t: (-score[t], t))
        picks = order[: self.top_n]
        w = {}
        for t in picks:
            if self.abs_filter is not None and np.mean(rets[t]) <= self.abs_filter:
                continue
            if self.weighting == "invvol":
                v = _vol(ctx, t, self.vol_window)
                w[t] = 1.0 / v if v else 0.0
            elif self.weighting == "score":
                w[t] = max(np.mean(rets[t]), 0.0) + 1e-9
            else:
                w[t] = 1.0
        n_slots = min(self.top_n, len(order))
        if not w:
            fb = self.fallback
            return {fb: 1.0} if fb and ctx.price(fb) is not None else {}
        kept = len(w)
        w = normalize(w, kept / n_slots if self.abs_filter is not None else 1.0)
        if self.abs_filter is not None and kept < n_slots:
            fb = self.fallback
            if fb and ctx.price(fb) is not None:
                w[fb] = w.get(fb, 0.0) + (1.0 - kept / n_slots)
        return w


class TrendSwitch(Signal):
    def __init__(self, risk, safe=None, rule="sma", n=200, fast=50, slow=200,
                 band=0.0, signal_ticker=None, daily=False, lookback=252):
        self.risk = {risk: 1.0} if isinstance(risk, str) else dict(risk)
        self.safe = safe
        self.rule = rule
        self.n, self.fast, self.slow = n, fast, slow
        self.band = band
        self.sig = signal_ticker or next(iter(self.risk))
        self.daily = daily
        self.lookback = lookback
        self._on = None

    def initialize(self, ctx):
        self._on = None

    def _state(self, ctx):
        c = np_closes(ctx, self.sig, max(self.n, self.slow, self.lookback) + 2)
        if len(c) == 0:
            return None
        px = c[-1]
        if self.rule == "sma":
            if len(c) < self.n:
                return None
            ref = c[-self.n:].mean()
            up, dn = px > ref * (1 + self.band), px < ref * (1 - self.band)
        elif self.rule == "sma_cross":
            if len(c) < self.slow:
                return None
            f, s = c[-self.fast:].mean(), c[-self.slow:].mean()
            up, dn = f > s * (1 + self.band), f < s * (1 - self.band)
        elif self.rule == "ema":
            if len(c) < self.n * 3:
                return None
            a = 2.0 / (self.n + 1)
            e = c[0]
            for x in c[1:]:
                e = a * x + (1 - a) * e
            up, dn = px > e * (1 + self.band), px < e * (1 - self.band)
        elif self.rule == "tsmom":
            if len(c) < self.lookback + 1:
                return None
            r = px / c[-self.lookback - 1] - 1.0
            up, dn = r > self.band, r < -self.band
        else:
            raise ValueError(self.rule)
        if self._on is None:
            return bool(up or not dn)
        if self._on and dn:
            return False
        if (not self._on) and up:
            return True
        return self._on

    def weights(self, ctx, rebalance_day):
        if not rebalance_day and not self.daily:
            return None
        st = self._state(ctx)
        if st is None:
            st = True if self._on is None else self._on
        changed = st != self._on
        self._on = st
        if not rebalance_day and not changed:
            return None
        if st:
            live = {t: w for t, w in self.risk.items() if ctx.price(t) is not None}
            return normalize(live, sum(self.risk.values())) if live else {}
        if self.safe and ctx.price(self.safe) is not None:
            return {self.safe: 1.0}
        return {}


class FixedMix(Signal):
    def __init__(self, weights):
        self.w = dict(weights)

    def weights(self, ctx, rebalance_day):
        live = {t: w for t, w in self.w.items() if ctx.price(t) is not None}
        return normalize(live, sum(self.w.values())) if live else {}


register_signal("common.momentum", lambda p: MomentumRotation(**p),
                lambda p: list(p["menu"]) + ([p["fallback"]] if p.get("fallback") else []))
register_signal("common.trend", lambda p: TrendSwitch(**p),
                lambda p: (list(p["risk"]) if isinstance(p["risk"], dict) else [p["risk"]])
                + ([p["safe"]] if p.get("safe") else [])
                + ([p["signal_ticker"]] if p.get("signal_ticker") else []))
register_signal("common.mix", lambda p: FixedMix(p["weights"]), lambda p: list(p["weights"]))


# --------------------------------------------------------------------------
# A fixed, pre-registered pool for hindsight checks: every non-leveraged,
# non-inverse ETF in the lab that had launched by 2003-12-31 (90 funds:
# broad/style/size, sectors, countries/regions, bonds, REITs). Draw random
# menus from it (e.g. random.Random(seed).sample(BROAD_POOL_2003, k)) to test
# whether a rule works on menus nobody chose. Do not edit it.
# --------------------------------------------------------------------------
BROAD_POOL_2003 = [
    "AGG", "DIA", "DVY", "EEM", "EFA", "EPP", "EWA", "EWC", "EWD", "EWG", "EWH", "EWI",
    "EWJ", "EWK", "EWL", "EWM", "EWN", "EWO", "EWP", "EWQ", "EWS", "EWT", "EWU", "EWW",
    "EWY", "EWZ", "EZU", "FVD", "IBB", "ICF", "IDU", "IEF", "IEV", "IGV", "IJH", "IJR",
    "IJS", "IJT", "ILF", "IUSG", "IUSV", "IVE", "IVV", "IVW", "IWB", "IWD", "IWF", "IWM",
    "IWN", "IWO", "IWP", "IWR", "IWS", "IWV", "IYC", "IYE", "IYF", "IYH", "IYJ", "IYK",
    "IYM", "IYR", "IYW", "IYZ", "LQD", "MDY", "OEF", "ONEQ", "QQQ", "RSP", "RWR", "SHY",
    "SMH", "SOXX", "SPY", "SPYG", "SPYV", "TIP", "TLT", "VTI", "VXF", "XLB", "XLE", "XLF",
    "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
]
# Equity-only subset (no bonds/REIT-only funds), same rule.
BROAD_EQUITY_POOL_2003 = [t for t in BROAD_POOL_2003
                          if t not in {"AGG", "IEF", "LQD", "SHY", "TIP", "TLT"}]

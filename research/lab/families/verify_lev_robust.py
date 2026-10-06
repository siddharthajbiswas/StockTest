"""Adversarial verification of the leveraged trend finalists (family 'verify_lev_robust').

One signal, written independently of families/leverage.py so the finalists can be
re-derived and stress-tested with a single, auditable rule:

verify_lev_robust.trend
    state = "risk on" while  sig / MA(n) - 1  > +band, "risk off" once it is < -band
    (hysteresis: in between, the previous state is kept). The rule is evaluated on
    the first trading day of every `check` period ("D" = every day, "W" = first
    trading day of each ISO week, "M" = first trading day of each month), on that
    day's close (`lag` = k evaluates on the close k trading days earlier).
    risk on  -> `risk` weights (e.g. {"SYN_SPY3XC": 1}, or {"SPY": .5, "SYN_SPY2XC": .5})
    risk off -> the first tradable ticker of `safe` (a list = fallback order).
    Inside a state the portfolio is re-balanced on calendar rebalance days only if a
    weight drifted more than `sdrift` (single-asset state; 0 = always, which covers
    the January tax payment exactly like leverage.regime with drift=0) or `mdrift`
    (multi-asset state, default 5 pp).
    ma: "sma" (default) or "ema".

Nothing looks ahead: closes come from ctx up to today (the lab convention: decide on
today's close, fill at today's close); index tickers ("^GSPC") are read lagged >= 1
day through blocks.asof.
"""
from __future__ import annotations

import numpy as np

from ..blocks import Signal, asof, np_closes, normalize, period_key
from ..registry import register_signal


def _closes(ctx, t: str, n: int, lag: int) -> np.ndarray:
    if t.startswith("^"):
        v = asof(ctx, t, lag_days=max(1, lag), n=max(int(n), 2))
        return np.asarray(v, dtype=float)[-int(n):]
    if lag <= 0:
        return np_closes(ctx, t, n)
    c = np_closes(ctx, t, n + lag)
    return c[:-lag] if len(c) > lag else c[:0]


def _ema_last(x: np.ndarray, n: int) -> float:
    a = 2.0 / (n + 1.0)
    e = float(x[0])
    for v in x[1:]:
        e = a * float(v) + (1.0 - a) * e
    return e


def _cur_weights(ctx) -> dict:
    eng = ctx._engine
    prices = eng.current_prices()
    pos = eng.portfolio.positions
    pv = eng.portfolio.cash + sum(q * prices.get(t, 0.0) for t, q in pos.items())
    if pv <= 0:
        return {}
    return {t: q * prices.get(t, 0.0) / pv for t, q in pos.items()}


class Trend(Signal):
    daily = True

    def __init__(self, sig="SPY", n=200, band=0.02, check="D", risk=None, safe=None,
                 lag=0, ma="sma", sdrift=0.0, mdrift=0.05):
        self.sig = sig
        self.n = int(n)
        self.band = float(band)
        self.check = check
        self.risk = dict(risk or {"SYN_SPY3XC": 1.0})
        self.safe = [safe] if isinstance(safe, str) else list(safe or ["VFITX"])
        self.lag = int(lag)
        self.ma = ma
        self.sdrift = sdrift
        self.mdrift = mdrift

    def initialize(self, ctx):
        self._state = None
        self._last_check = None
        self._tgt_key = None

    def _margin(self, ctx):
        n = self.n
        if self.ma == "ema":
            c = _closes(ctx, self.sig, 4 * n, self.lag)
            if len(c) < 2 * n:
                return None
            return c[-1] / _ema_last(c, n) - 1.0
        c = _closes(ctx, self.sig, n, self.lag)
        if len(c) < n:
            return None
        return c[-1] / c.mean() - 1.0

    def _alloc(self, ctx, on: bool) -> dict:
        if on:
            live = {t: v for t, v in self.risk.items() if v > 0 and ctx.price(t) is not None}
            if not live:
                return {}
            return normalize(live, sum(self.risk.values()))
        for t in self.safe:
            if ctx.price(t) is not None:
                return {t: 1.0}
        return {}

    def weights(self, ctx, rebalance_day):
        pk = period_key(ctx.date, self.check)
        if pk != self._last_check:
            self._last_check = pk
            m = self._margin(ctx)
            if m is not None:
                if self._state is None:
                    self._state = m > 0
                elif m > self.band:
                    self._state = True
                elif m < -self.band:
                    self._state = False
        if self._state is None:
            return None
        tgt = self._alloc(ctx, self._state)
        key = (self._state, tuple(sorted(tgt)))
        if key != self._tgt_key:
            if not tgt:
                return None
            self._tgt_key = key
            return tgt
        if rebalance_day and tgt:
            cur = _cur_weights(ctx)
            ab = max(abs(cur.get(t, 0.0) - tgt.get(t, 0.0)) for t in set(cur) | set(tgt))
            thr = self.mdrift if len(tgt) > 1 else self.sdrift
            if thr is not None and ab > thr:
                return tgt
        return None


def _tickers(p: dict) -> list:
    out = list((p.get("risk") or {"SYN_SPY3XC": 1.0}).keys())
    safe = p.get("safe") or ["VFITX"]
    out += [safe] if isinstance(safe, str) else list(safe)
    sig = p.get("sig", "SPY")
    if not sig.startswith("^"):
        out.append(sig)
    return list(dict.fromkeys(out))


register_signal("verify_lev_robust.trend", lambda p: Trend(**p), _tickers)

"""Robustness variants of existing strategies (for verifying finalists).

kind "weights_x": a "weights" config plus
    "offset_days": shift every rebalance-period boundary by N calendar days
                   (e.g. 14 -> monthly rebalances happen mid-month). Measures
                   "rebalance timing luck".
    "lag": 1 -> targets computed from today's close are executed at the NEXT
                   trading day's close (no same-close signal-and-trade).
kind "combo_x": a "combo" config (the site's classes) plus "offset_days".

Both build exactly the same strategy as the base kind when offset_days=0 and
lag=0.
"""
from __future__ import annotations

import pandas as pd

from backtester import Combo, TaxManagedCombo

from ..blocks import WeightStrategy, period_key
from ..registry import (SIGNALS, _combo_build, _combo_tickers, _weights_tickers, _WS_KEYS,
                        register_kind)


class XWeightStrategy(WeightStrategy):
    def __init__(self, signal, offset_days: int = 0, lag: int = 0, **kw):
        super().__init__(signal, **kw)
        self.offset_days = int(offset_days)
        self.lag = int(lag)

    def initialize(self, ctx) -> None:
        super().initialize(ctx)
        self._pending = None

    def on_day(self, ctx) -> None:
        if self.lag and self._pending is not None:
            w, self._pending = self._pending, None
            self._target = dict(w)
            self._execute(ctx, w)
        d = ctx.date - pd.Timedelta(days=self.offset_days)
        key = period_key(d, self.rebalance)
        reb = key != self._last
        if reb:
            self._last = key
        w = None
        if reb or self.signal.daily:
            w = self.signal.weights(ctx, reb)
        if w is not None:
            if self.lag:
                self._pending = w
            else:
                self._target = dict(w)
                self._execute(ctx, w)
        elif self.harvest is not None:
            hk = period_key(ctx.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(ctx)


def _wx_build(c):
    factory = SIGNALS[c["signal"]][0]
    kw = {k: c[k] for k in _WS_KEYS if k in c}
    return XWeightStrategy(factory(c.get("params", {})), offset_days=c.get("offset_days", 0),
                           lag=c.get("lag", 0), **kw)


register_kind("weights_x", _wx_build, _weights_tickers)


def _offset_combo(base_cls, offset_days):
    class Shifted(base_cls):
        def _period_key(self, date):
            return base_cls._period_key(self, date - pd.Timedelta(days=offset_days))
    return Shifted


def _cx_build(c):
    strat = _combo_build(c)
    off = int(c.get("offset_days", 0))
    if off:
        base = TaxManagedCombo if isinstance(strat, TaxManagedCombo) else Combo
        strat.__class__ = _offset_combo(base, off)
    return strat


register_kind(
    "combo_x", _cx_build, _combo_tickers,
    heavy=lambda c: not (c.get("tickers") or c.get("menu")),
    universe=lambda c: "menu" if (c.get("tickers") or c.get("menu")) else c.get("universe", "sp500-pit"),
)


# --------------------------------------------------------------------------
# Regime "ZERO": a tax-deferred account (no tax at all, like NONE) but with tax
# accounting switched ON at 0% rates, so lot-aware execution rules (the gain
# budget, loss-first selling, the wash guard) still operate. On the website this
# is "tax enabled, both rates 0%". It answers: is a tax-managed rule's
# discipline worth anything in an IRA? The benchmark is identical to NONE's.
# Registered here (not in core.REGIMES) so adding it does not change any cache
# key of existing results.
# --------------------------------------------------------------------------
from .. import core as _core  # noqa: E402

_core.REGIMES.setdefault("ZERO", (0.0, 0.0))

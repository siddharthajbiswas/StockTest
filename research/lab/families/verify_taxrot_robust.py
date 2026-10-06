"""Adversarial verification of the tax-managed rotations KX3 / KX1 (family key:
verify_taxrot_robust). Adds NO new strategy logic: it re-uses
tax_rotation.TRStrategy / tax_rotation.rank unchanged and only adds the two
robustness knobs the standard battery supplies for "weights" kinds but not for
custom kinds:

Kind "verify_taxrot_robust.ws"  = kind "tax_rotation.ws" plus
    offset_days  shift every rebalance-period boundary by N calendar days
                 (e.g. 14 -> quarterly rebalances fall mid-month) -- the
                 battery's "weights_x" offset test (rebalance timing luck);
    lag          1 -> targets computed from today's close are executed at the
                 NEXT trading day's close (no same-close signal-and-trade). For
                 mutual-fund menus (pre-2000 holdout) this is the realistic
                 setting: an order placed before the 4pm cut-off can only know
                 yesterday's NAV.
With offset_days=0 and lag=0 it builds exactly tax_rotation.TRStrategy
(checked in scratch/verify_taxrot_robust/v0_identity.py: identical records).
"""
from __future__ import annotations

import pandas as pd

from ..blocks import WeightStrategy, period_key
from ..registry import SIGNALS, register_kind
from .tax_rotation import _TR_KEYS, TRStrategy, _ShadowCtx, _tr_tickers


class XTRStrategy(TRStrategy):
    def __init__(self, signal, offset_days: int = 0, lag: int = 0, **kw):
        super().__init__(signal, **kw)
        self.offset_days = int(offset_days or 0)
        self.lag = int(lag or 0)

    def initialize(self, ctx) -> None:
        super().initialize(ctx)
        self._pending = None

    def on_day(self, ctx) -> None:
        c = ctx
        if self.shadow and ctx._engine.tax_policy is None:
            if self._sh is None:
                self._sh = _ShadowCtx(ctx)
            c = self._sh
        if not self.offset_days and not self.lag:
            return TRStrategy.on_day(self, ctx)
        # 1. yesterday's targets are executed today (lag)
        if self.lag and self._pending is not None:
            w, self._pending = self._pending, None
            self._target = dict(w)
            self._execute(c, w)
        # 2. today's rebalance decision, on shifted period boundaries
        d = c.date - pd.Timedelta(days=self.offset_days)
        key = self._key(d)
        reb = key != self._last
        if reb:
            self._last = key
        w = None
        if reb or self.signal.daily:
            w = self.signal.weights(c, reb)
        if w is not None:
            if self.lag:
                self._pending = w
            else:
                self._target = dict(w)
                self._execute(c, w)
        elif self.harvest is not None:
            hk = period_key(c.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(c)


def _build(c):
    factory, _, _ = SIGNALS[c["signal"]]
    sig = factory(c.get("params", {}))
    kw = {k: c[k] for k in _TR_KEYS if k in c}
    return XTRStrategy(sig, offset_days=c.get("offset_days", 0), lag=c.get("lag", 0), **kw)


register_kind("verify_taxrot_robust.ws", _build, _tr_tickers)

# keep a reference so linters do not drop the import used for documentation
_ = WeightStrategy

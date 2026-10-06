"""Adversarial verification helpers for the yield-curve un-inversion candidates
(family: verify_curve).  Nothing here changes macro_regime; it only adds:

  * signal "verify_curve.switch" -- exactly macro_regime.switch (same class,
    same lag / check / allocation logic) but with two extra indicator types:
      {"type": "mask", "off": [["YYYY-MM-DD", "YYYY-MM-DD"], ...]}
          risk-off on [a, b) for each interval, risk-on elsewhere.  Used for the
          permutation test (real risk-off spells moved to random dates) and for
          leave-one-event-out attribution.  The series lives on the same daily
          calendar as the ^TNX/^IRX curve indicator, so a mask built from the
          real indicator's off-intervals reproduces the real strategy exactly.
      {"type": "curve_bey", ...curve params...}
          the curve indicator with the 3-month leg converted from the ^IRX
          discount yield to a bond-equivalent yield (BEY = 365 d / (360 - 91 d)),
          i.e. closer to the constant-maturity 10y-3m spread the literature uses.
  * nothing else: the sweep/cache machinery is the lab's own.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..registry import register_signal
from . import macro_regime as mr

FAMILY = "verify_curve"
_IND2: dict = {}


def _calendar() -> pd.DatetimeIndex:
    """Daily calendar of the default curve indicator (^TNX/^IRX union)."""
    s = mr.indicator({"type": "curve", "thr": 0.0, "confirm": 5, "anchor": "end",
                      "after": 540, "min_len": 30})
    return s.index


def _mask(p: dict) -> pd.Series:
    idx = _calendar()
    off = np.zeros(len(idx), dtype=bool)
    for a, b in p.get("off", []):
        lo = idx.searchsorted(pd.Timestamp(a), side="left")
        hi = idx.searchsorted(pd.Timestamp(b), side="left") if b else len(idx)
        off[lo:hi] = True
    return pd.Series(np.where(off, 0.0, 1.0), index=idx)


def _bey_series(t: str = "^IRX") -> pd.Series:
    key = "bey:" + t
    s = mr._PX.get(key)
    if s is None:
        d = mr.series(t) / 100.0
        s = 100.0 * 365.0 * d / (360.0 - 91.0 * d)
        mr._PX[key] = s
    return s


def _curve_bey(p: dict) -> pd.Series:
    """Copy of macro_regime._curve with the short leg in bond-equivalent terms."""
    q = dict(p)
    q["type"] = "curve"
    S = _bey_series(q.get("short", "^IRX"))
    # route through macro_regime's own episode logic: cache the converted short
    # leg under a private series key that macro_regime.series() will look up
    key = json.dumps({"bey": q.get("short", "^IRX")}, sort_keys=True)
    mr._PX[key] = S
    q["short"] = {"bey": q.get("short", "^IRX")}
    return mr._curve(q)


def indicator2(p: dict) -> pd.Series:
    key = json.dumps(p, sort_keys=True)
    s = _IND2.get(key)
    if s is not None:
        return s
    t = p["type"]
    if t == "mask":
        s = _mask(p)
    elif t == "curve_bey":
        s = _curve_bey(p)
    else:
        return mr.indicator(p)
    if p.get("invert"):
        s = 1.0 - s
    s = s.dropna()
    _IND2[key] = s
    return s


class VSwitch(mr.MacroSwitch):
    """macro_regime.MacroSwitch plus the mask / curve_bey indicators and an
    optional `check_offset` (calendar days): the regime check happens when the
    month of (date - check_offset) changes, i.e. on the first trading day on or
    after day (1 + check_offset) of each month.  Pair it with kind "weights_x"
    and the same "offset_days" so the rebalance day moves too."""

    def __init__(self, check_offset=0, **kw):
        super().__init__(**kw)
        self.check_offset = int(check_offset)

    def weights(self, ctx, rebalance_day):
        if not self.check_offset:
            return super().weights(ctx, rebalance_day)
        from ..blocks import period_key
        d = ctx.date - pd.Timedelta(days=self.check_offset)
        key = period_key(d, self.check) if self.check else None
        if not rebalance_day and key == self._last_check:
            return None
        self._last_check = key
        eq = self._target_eq(ctx)
        changed = eq != self._eq
        if changed:
            if self._eq is not None:
                self._last_switch = ctx.date
            self._eq = eq
        if not rebalance_day and not changed:
            return None
        return self._alloc(ctx, eq, rebalance_day)

    def initialize(self, ctx):
        self._readers = [mr._Reader(indicator2(p)) for p in self.specs]
        self._eq = None
        self._last_switch = None
        self._last_check = None
        self._core_bought = False
        self._risk_w = None
        if self.risk_signal is not None:
            self.risk_signal.initialize(ctx)


def _factory(p):
    return VSwitch(**p)


register_signal(f"{FAMILY}.switch", _factory, mr._switch_tickers)


# --------------------------------------------------------------------------
# helpers for scripts
# --------------------------------------------------------------------------
def off_intervals(spec: dict, start="1960-01-01") -> list:
    """Risk-off intervals [a, b) of an indicator on its own calendar."""
    s = indicator2(spec)
    s = s[s.index >= pd.Timestamp(start)]
    v = s.to_numpy() < 0.5
    out = []
    cur = None
    for d, o in zip(s.index, v):
        if o and cur is None:
            cur = d
        elif not o and cur is not None:
            out.append((cur, d))
            cur = None
    if cur is not None:
        out.append((cur, None))
    return out

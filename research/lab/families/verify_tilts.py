"""Adversarial verification helpers for the style-switch and tax-managed
cyclical-season finalists (family key: verify_tilts).

Nothing here changes how existing configs run. It adds:

  verify_tilts.randpath   placebo signal: a random, date-determined path of
                          states (Markov chain over calendar months, seeded),
                          holding weights `ws[state]`. Every window start sees
                          the same path, exactly as with a real signal. Used to
                          ask whether a real switching rule beats random
                          switching between the same assets under the same
                          (tax-managed) execution.
  shifted protocols       "full_m1" / "full_m2": the `full` protocol with window
                          starts and checkpoints shifted by +1 / +2 months
                          (Feb/May/Aug/Nov and Mar/Jun/Sep/Dec quarters), so the
                          union with `full` covers every month 2000-2023. Tests
                          start-phase luck (e.g. a seasonal rule whose initial
                          holding depends on the start month). Registered with
                          setdefault, so no existing cache key changes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import core, data
from ..blocks import Signal, normalize
from ..registry import register_signal


# --------------------------------------------------------------------------
# shifted-start protocols
# --------------------------------------------------------------------------
def _shifted(name: str, months: int) -> core.Protocol:
    anchor = {1: "QS-FEB", 2: "QS-MAR"}[months]
    a = (pd.Timestamp("2000-01-01") + pd.DateOffset(months=months)).strftime("%Y-%m-%d")
    b = (pd.Timestamp("2023-07-01") + pd.DateOffset(months=months)).strftime("%Y-%m-%d")
    ck_a = (pd.Timestamp("2000-04-01") + pd.DateOffset(months=months)).strftime("%Y-%m-%d")
    starts = tuple(pd.date_range(a, b, freq=anchor))
    cks = tuple(pd.date_range(ck_a, data.DATA_END, freq=anchor))
    return core.Protocol(name, starts, cks, "SPY")


core.PROTOCOLS.setdefault("full_m1", _shifted("full_m1", 1))
core.PROTOCOLS.setdefault("full_m2", _shifted("full_m2", 2))


# --------------------------------------------------------------------------
# random-path placebo signal
# --------------------------------------------------------------------------
class RandPath(Signal):
    """Hold ws[s] where s is the state of a seeded Markov chain over calendar
    months (1980-01 .. 2027-12): each month the state moves to a different
    state with probability p_switch. The path depends only on the date, never
    on prices, so it carries no information."""

    def __init__(self, ws, seed=0, p_switch=0.05, cadence="M"):
        self.ws = [dict(w) for w in ws]
        rng = np.random.default_rng(int(seed))
        n = (2027 - 1980 + 1) * 12
        k = len(self.ws)
        st = np.empty(n, int)
        st[0] = int(rng.integers(k))
        for i in range(1, n):
            if rng.random() < p_switch:
                st[i] = (st[i - 1] + 1 + int(rng.integers(k - 1))) % k if k > 1 else 0
            else:
                st[i] = st[i - 1]
        self.path = st

    def weights(self, ctx, rebalance_day):
        d = ctx.date
        i = (d.year - 1980) * 12 + d.month - 1
        w = self.ws[int(self.path[min(max(i, 0), len(self.path) - 1)])]
        live = {t: x for t, x in w.items() if ctx.price(t) is not None}
        return normalize(live) if live else {}


register_signal("verify_tilts.randpath", lambda p: RandPath(**p),
                lambda p: list(dict.fromkeys([t for w in p["ws"] for t in w])))

"""Round 2, gap 6: the leveraged-trend plateau on other markets (family 'r2_gap6').

The trend rule itself is the verified one, `verify_lev_robust.trend` (SMA-band
switch: L x fund while sig / SMA(n) - 1 > +band, safe asset once it is < -band,
checked daily on the close, traded at the close). This module only adds what
the comparison needs:

r2_gap6.bh1   (kind)  buy-and-hold of ONE ticker, exactly the lab's/site's
              benchmark strategy (core.BuyHoldOne), so "the trend rule on market X"
              can be scored against buy-and-hold of X itself with the same engine,
              costs, tax regime and window starts (set the same "min_start").
              {"kind": "r2_gap6.bh1", "ticker": "EWJ", "min_start": "2000-01-01"}

Synthetic leveraged funds R2G6_<U><L>X (research/lab/data) are built by
research/lab/scratch/r2_gap6/build_syn.py: L r_U - (L-1)(T + a + b T) - 0.95%,
with (a, b) calibrated on 26 real leveraged ETFs by market class.
"""
from __future__ import annotations

from .. import core
from ..registry import register_kind


def _bh1_build(c: dict):
    return core.BuyHoldOne(c["ticker"])


register_kind("r2_gap6.bh1", _bh1_build, lambda c: [c["ticker"]])

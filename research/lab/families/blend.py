"""Blends: any weighted combination of registered signals, run as ONE portfolio.

    {"kind": "weights", "signal": "blend.mix",
     "params": {"parts": [
         {"w": 0.6, "signal": "common.mix", "params": {"weights": {"SPY": 1.0}}},
         {"w": 0.4, "signal": "common.momentum", "params": {...}}]},
     "rebalance": "Q", "execution": "tax"}

Target weights are sum_i w_i * weights_i (each part's weights scaled by its
sleeve weight). Because it is one portfolio, taxes, the gain budget and the
wash-sale guard apply to the combined holdings -- exactly what an investor
running a core-satellite or multi-strategy portfolio in one account faces.
Parts that are daily signals are asked every day; on days a part returns
None ("no change") its previous weights are reused.
"""
from __future__ import annotations

from ..blocks import Signal
from ..registry import SIGNALS, register_signal


class Blend(Signal):
    def __init__(self, parts):
        self.parts = []
        for p in parts:
            factory = SIGNALS[p["signal"]][0]
            self.parts.append((float(p["w"]), factory(p.get("params", {}))))
        self.daily = any(getattr(s, "daily", False) for _, s in self.parts)
        self._last: list = []

    def initialize(self, ctx):
        for _, s in self.parts:
            s.initialize(ctx)
        self._last = [None] * len(self.parts)

    def weights(self, ctx, rebalance_day):
        changed = False
        for i, (_, s) in enumerate(self.parts):
            if rebalance_day or getattr(s, "daily", False):
                w = s.weights(ctx, rebalance_day)
                if w is not None:
                    if w != self._last[i]:
                        changed = True
                    self._last[i] = w
        if not rebalance_day and not changed:
            return None
        out: dict = {}
        for (a, _), w in zip(self.parts, self._last):
            for t, x in (w or {}).items():
                out[t] = out.get(t, 0.0) + a * x
        return out


def _tickers(p):
    out = []
    for part in p["parts"]:
        out += list(SIGNALS[part["signal"]][1](part.get("params", {})))
    return list(dict.fromkeys(out))


register_signal("blend.mix", lambda p: Blend(p["parts"]), _tickers)


class Tranche(Signal):
    """Staggered sleeves ("tranching") to remove rebalance-timing luck.

    The portfolio is split into `k` equal sleeves of the same signal. Run the
    WeightStrategy at the base cadence divided by k (e.g. a quarterly signal
    with k=3 -> rebalance="M"): on each rebalance day ONE sleeve (in rotation)
    refreshes its weights from the signal; the target is the average of all
    sleeves. Every sleeve therefore holds its picks for k periods, but the
    portfolio's dependence on any single rebalance date is divided by k.
    """

    def __init__(self, part, k=3):
        factory = SIGNALS[part["signal"]][0]
        self.sig = factory(part.get("params", {}))
        self.k = int(k)
        self.daily = False

    def initialize(self, ctx):
        self.sig.initialize(ctx)
        self._sleeves = [None] * self.k
        self._n = 0

    def weights(self, ctx, rebalance_day):
        if not rebalance_day:
            return None
        w = self.sig.weights(ctx, True) or {}
        i = self._n % self.k
        self._n += 1
        self._sleeves[i] = w
        sl = [s if s is not None else w for s in self._sleeves]
        out: dict = {}
        for s in sl:
            for t, x in s.items():
                out[t] = out.get(t, 0.0) + x / self.k
        return out


register_signal("blend.tranche", lambda p: Tranche(p["part"], p.get("k", 3)),
                lambda p: list(SIGNALS[p["part"]["signal"]][1](p["part"].get("params", {}))))


class Switch(Signal):
    """Two allocations and a trend rule: hold `on` while the rule is on, `off`
    while it is off. Unlike common.trend (risk asset vs ONE safe asset), both
    states are arbitrary weight dicts -- e.g. a tax-aware hedge that never sells
    the core: on = {SPY: .7, SHY: .3}, off = {SPY: .7, SH: .3} (net exposure
    70% -> 40%), so only the small reserve sleeve ever realizes gains.
    Trend rule params are those of common.trend (rule, n, fast, slow, band,
    lookback, daily, signal_ticker -- default SPY)."""

    def __init__(self, on, off, **rule):
        from .common import TrendSwitch
        self.on, self.off = dict(on), dict(off)
        rule.setdefault("signal_ticker", "SPY")
        self.rule = TrendSwitch(risk=rule["signal_ticker"], safe=None, **rule)
        self.daily = self.rule.daily

    def initialize(self, ctx):
        self.rule.initialize(ctx)

    def weights(self, ctx, rebalance_day):
        w = self.rule.weights(ctx, rebalance_day)
        if w is None:
            return None
        src = self.on if self.rule._on else self.off
        live = {t: x for t, x in src.items() if ctx.price(t) is not None}
        return live


register_signal(
    "blend.switch",
    lambda p: Switch(p["on"], p["off"], **{k: v for k, v in p.items() if k not in ("on", "off")}),
    lambda p: list(dict.fromkeys(list(p["on"]) + list(p["off"]) + [p.get("signal_ticker", "SPY")])),
)

"""Verification variants of the tax_rotation "K-execution" (KX3 / KX1 audit).

kind "verify_taxrot_mech.ws_x": exactly `tax_rotation.ws` (TRStrategy) plus
    offset_days   shift every rebalance-period boundary by N calendar days
                  (the same definition as research.lab.families.variants'
                  weights_x / combo_x, so timing luck is measured identically
                  for this kind and for the site's combo).
    lag           1 -> targets computed from today's close are executed at
                  the NEXT trading day's close (prices, lots, budget and cash
                  are those of the execution day; the ranking used for
                  worst-ranked-first gain spending is the signal day's).
    exact_budget  True -> a budget-limited partial gain sale is sized on the
                  FIFO lots that will actually be sold, so the year's realized
                  gain never exceeds the budget. (TRStrategy / the site's
                  TaxManagedCombo size it as qty * room / gain, i.e. on the
                  position's AVERAGE gain per share; FIFO sells the oldest,
                  usually lowest-basis lots first, so the realized gain can
                  overshoot the budget.)

With offset_days=0, lag=0 and exact_budget=False it builds exactly the same
strategy as tax_rotation.ws (checked in scratch/verify_taxrot_mech).
Everything trades through ctx.order; nothing reads data after today's close.
"""
from __future__ import annotations

import pandas as pd

from ..registry import SIGNALS, register_kind
from .tax_rotation import _TR_KEYS, TRStrategy, _tr_tickers


class XTRStrategy(TRStrategy):
    def __init__(self, signal, offset_days: int = 0, lag: int = 0, exact_budget: bool = False, **kw):
        super().__init__(signal, **kw)
        if self.shadow:
            raise ValueError("ws_x does not support shadow lots")
        self.offset_days = int(offset_days or 0)
        self.lag = int(lag or 0)
        self.exact_budget = bool(exact_budget)

    def initialize(self, ctx) -> None:
        super().initialize(ctx)
        self._pending = None

    def on_day(self, ctx) -> None:
        if self.lag and self._pending is not None:
            w, self._pending = self._pending, None
            self._target = dict(w)
            self._execute(ctx, w)
        key = self._key(ctx.date - pd.Timedelta(days=self.offset_days))
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
            from ..blocks import period_key
            hk = period_key(ctx.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(ctx)

    # ---- exact FIFO sizing of the budget-limited partial sale -------------
    @staticmethod
    def _fifo_shares_for(ctx, t, qty, net, room):
        """Shares (<= qty) whose FIFO sale realizes a net gain of at most `room`."""
        sold, left = 0.0, room
        for _, sh, cost in ctx.lots(t):
            if sold >= qty - 1e-12:
                break
            take = min(sh, qty - sold)
            g = net - cost
            if g <= 0 or g * take <= left:
                sold += take
                left -= g * take
                continue
            sold += max(0.0, left / g)
            break
        return min(sold, qty)

    def _tax_sells(self, ctx, pv, tgt) -> None:
        if not self.exact_budget:
            return TRStrategy._tax_sells(self, ctx, pv, tgt)
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        cands = []
        for t, target in tgt.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held - 1e-12:
                continue
            if not self.trim and target > 1e-12:
                continue
            qty = held - target
            net = self._net_px(ctx, ctx.price(t))
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            cands.append((gain > 0, not all_lt, gain, t, qty, target))
        if self.gain_order == "rank":
            order = getattr(self.signal, "last_order", None) or []
            at = {t: i for i, t in enumerate(order)}
            worst = len(order)
            cands.sort(key=lambda c: (c[0], c[1], -at.get(c[3], worst) if c[0] else 0, c[2], c[3]))
        else:
            cands.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, is_short, gain, t, qty, target in cands:
            net = self._net_px(ctx, ctx.price(t))
            if not is_gain:
                if (self.strict_wash and gain < 0 and target > 1e-9
                        and self._recent_buy(ctx, t)):
                    continue
                sell = qty
            elif is_short and not self.st_gains:
                continue
            elif gain <= room + 1e-9:
                sell = qty
            elif room > 1e-9:
                if room / gain <= 0.02:
                    continue
                sell = self._fifo_shares_for(ctx, t, qty, net, room)
                if sell <= 1e-12:
                    continue
            else:
                continue
            g_real, _ = self._gain_if_sold(ctx, t, sell, net)
            room -= g_real
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date


_X_KEYS = _TR_KEYS + ("offset_days", "lag", "exact_budget")


def _x_build(c):
    factory, _, _ = SIGNALS[c["signal"]]
    sig = factory(c.get("params", {}))
    kw = {k: c[k] for k in _X_KEYS if k in c}
    return XTRStrategy(sig, **kw)


register_kind("verify_taxrot_mech.ws_x", _x_build, _tr_tickers)

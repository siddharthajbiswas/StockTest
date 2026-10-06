"""Adversarial verification of risk_alloc.taxvt (tax-aware levered vol targeting).

Kind "verify_levvt.taxvt": the exact risk_alloc.TaxVT logic plus switches that
the original cannot express:

  lag      (int, default 0)   the vol forecast uses the bar `lag` days before
                              today (lag=1: decide on yesterday's close, trade
                              at today's close -- the custom-kind equivalent of
                              verify's weights_x lag test).
  wash_pre (bool, default False)
                              enforce BOTH sides of the wash-sale rule: a lot is
                              never sold at a loss while the same fund holds
                              another lot bought within the last 30 days, and a
                              fund is barred from re-purchase for `wash_days`
                              after ANY lot of it was sold at a loss (the
                              original registers a block only if the sale's
                              aggregate result was a loss).
  rec      (no effect on results) -- diagnostics are captured by scratch scripts
                              through the class attribute RECORD.

Everything else (config keys, defaults) is identical to risk_alloc.taxvt, so
{"kind": "verify_levvt.taxvt", lag: 0, wash_pre: False, ...} reproduces the
original exactly (checked in scratch/verify_levvt).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..registry import register_kind
from .risk_alloc import TaxVT, VolTarget, _bar, _vol_arr, _chain_list


class VolTargetLag(VolTarget):
    def __init__(self, lag: int = 0, **kw):
        super().__init__(**kw)
        self.lag = int(lag)

    def forecast_vol(self, ctx):
        if self.lag <= 0 or self.est not in ("simple", "ewma", "semi"):
            return super().forecast_vol(ctx)
        p = _bar(ctx, self.vt) - self.lag
        if p < 0:
            return None
        v = _vol_arr(self.vt, self.est, self.window, self.halflife)[p]
        return None if not np.isfinite(v) or v <= 0 else float(v)


class TaxVTX(TaxVT):
    RECORD = None          # scratch scripts set a list here to capture daily state

    def __init__(self, signal: dict, lag: int = 0, wash_pre: bool = False, **kw):
        super().__init__(signal=signal, **kw)
        sp = dict(signal)
        sp.setdefault("cash", list(_chain_list(kw.get("cash", ("SHY", "VFISX")))))
        sp.pop("band", None)
        sp.pop("daily", None)
        self.sig = VolTargetLag(lag=lag, **sp)
        self.wash_pre = bool(wash_pre)

    # ---- wash-sale helpers -----------------------------------------------
    def _recent_buy(self, ctx, t, exclude_front: bool = True):
        lots = ctx.lots(t)
        rng = lots[1:] if exclude_front else lots
        for d, s, c in rng:
            if (ctx.date - d).days <= 30 and s > 1e-12:
                return True
        return False

    def _sell_amount(self, ctx, tickers, amount, rates, room):
        if not self.wash_pre or not rates:
            return super()._sell_amount(ctx, tickers, amount, rates, room)
        # same algorithm as TaxVT._sell_amount, plus: skip a loss lot whose fund
        # holds a younger lot bought <= 30 days ago (pre-sale wash window), and
        # register a wash block whenever any sold lot realizes a loss.
        if amount <= 1e-6:
            return 0.0, room
        fronts = {}
        for t in tickers:
            if ctx.shares(t) <= 0 or ctx.price(t) is None:
                continue
            lots = [list(l) for l in ctx.lots(t)]
            if not lots:
                lots = [[ctx.date, ctx.shares(t), 0.0]]
            fronts[t] = lots
        plan = {}
        left = amount
        while left > 1e-6 and fronts:
            best = None
            for t, lots in fronts.items():
                if not lots:
                    continue
                d, sh, cost = lots[0]
                px = ctx.price(t)
                net = px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
                lt = ctx.is_long_term(d)
                rate = rates[1] if lt else rates[0]
                c = (net - cost) / net * rate
                if net - cost > 0 and room is not None and room <= 1e-9:
                    continue
                if net - cost > 0 and not lt and not self.st_gains:
                    continue
                if net - cost < 0:
                    # replacement shares: any OTHER open lot bought in the last 30 days
                    if any((ctx.date - dd).days <= 30 and ss > 1e-12 for dd, ss, _ in lots[1:]):
                        continue
                if best is None or c < best[0]:
                    best = (c, t)
            if best is None:
                break
            t = best[1]
            d, sh, cost = fronts[t][0]
            px = ctx.price(t)
            net = px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
            take_sh = min(sh, left / px)
            gain = (net - cost) * take_sh
            if gain > 0 and room is not None and gain > room:
                take_sh = take_sh * max(room, 0.0) / gain
                gain = (net - cost) * take_sh
            if take_sh <= 1e-12:
                fronts[t].pop(0)
                continue
            plan[t] = plan.get(t, 0.0) + take_sh
            left -= take_sh * px
            if room is not None:
                room -= gain
            fronts[t][0][1] -= take_sh
            if fronts[t][0][1] <= 1e-12:
                fronts[t].pop(0)
        sold = 0.0
        for t, sh in plan.items():
            net = ctx.price(t) * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
            rem, anyloss = sh, False
            for d, s0, cost in ctx.lots(t):
                if rem <= 1e-12:
                    break
                k = min(rem, s0)
                if net < cost:
                    anyloss = True
                rem -= k
            if anyloss:
                self._loss_sale[t] = ctx.date
            sold += sh * ctx.price(t)
            ctx.order(t, -sh)
        return sold, room

    def on_day(self, ctx):
        super().on_day(ctx)
        rec = TaxVTX.RECORD
        if rec is not None:
            pv = ctx.portfolio_value
            if pv > 0:
                kmap = dict(self.lev)
                vals = {t: self._val(ctx, t) for t in list(self.veh) + list(kmap) + list(self.cash)}
                e_act = (sum(vals[t] for t in self.veh) + sum(kmap[t] * vals[t] for t in kmap)) / pv
                rec.append((ctx.date, pv, ctx.cash / pv, e_act, self.sig.exposure(ctx),
                            {t: v / pv for t, v in vals.items() if v > 0}))


def _build(c):
    return TaxVTX(signal=c["signal"], lag=c.get("lag", 0), wash_pre=c.get("wash_pre", False),
                  vehicles=c.get("vehicles", ["SPY"]), lever=c.get("lever"),
                  cash=c.get("cash", ["SHY", "VFISX"]), band=c.get("band", 0.1),
                  check=c.get("check", "D"), gain_budget=c.get("gain_budget"),
                  wash_days=c.get("wash_days", 31), harvest=c.get("harvest"),
                  harvest_freq=c.get("harvest_freq", "M"), st_gains=c.get("st_gains", True))


def _tickers(c):
    out = list(c.get("vehicles", ["SPY"])) + [t for t, _ in (c.get("lever") or [])]
    out += _chain_list(c.get("cash", ["SHY", "VFISX"]))
    vt_t = c["signal"].get("vol_ticker") or c["signal"].get("risk")
    if vt_t:
        out.append(vt_t)
    return list(dict.fromkeys(out + ["SPY"]))


register_kind("verify_levvt.taxvt", _build, _tickers)

"""Round 2, key rotation_final: the definitive unlevered tax-managed rotation test.

Re-uses tax_rotation.Rank / TRStrategy and verify_taxrot_mech.XTRStrategy (rebalance-boundary
offset, 1-day lag, FIFO-exact gain budget) unchanged, and adds only what round 2 needs:

Signal "r2_rotation_final.rank"  = tax_rotation.Rank plus
    menu_by_year  {"YYYY": [tickers]}: a menu rebuilt by a fixed rule each Jan 1 from data before
                  that Jan 1 (scratch/r2_rotation_final/menus.py). On a date, the menu in force is
                  the entry for that calendar year. A held fund that has left the menu is unranked:
                  an exit candidate (losses always sold, gains as the budget allows, worst first).
    anchor, margin
                  anchored rotation: the N slots hold `anchor` (e.g. SPY) by default. A menu fund
                  (the anchor itself excluded) takes a slot only if its score (trailing return)
                  beats the anchor's by at least `margin` (entry). A held fund keeps its slot while
                  it ranks within the top N + hold_buffer of the menu AND still beats the anchor
                  (stay). Unfilled slots hold the anchor, 1/N each.
    core          (tax_rotation.Rank) {ticker: weight} held fixed, the sleeve gets the rest. With
                  trim=False a core position is never sold.

Kind "r2_rotation_final.ws" = verify_taxrot_mech.ws_x (offset_days, lag, exact_budget) built on
this signal, plus
    trim_only     tickers that may be trimmed (sold down to a smaller, still positive target) even
                  when trim=False. The anchored rotation needs it for its anchor: a fund can only
                  take a slot if the anchor is sold down to pay for it (within the gain budget).
With none of the new options it builds exactly verify_taxrot_mech.ws_x.

Nothing here sees the future: scores read np_closes() (history up to today's close), menus for a
year are fixed from data before Jan 1 of that year, orders go through ctx.order.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..blocks import np_closes  # noqa: F401  (documentation: Rank reads it)
from ..registry import SIGNALS, register_kind, register_signal
from .tax_rotation import Rank, _rank_tickers, _tr_tickers
from .verify_taxrot_mech import _X_KEYS, XTRStrategy

# This module's results depend on two other family files that the cache key does not hash for a
# custom kind. Refuse to build if either changed since this module was validated against them.
_DEPS = {
    "tax_rotation.py": "041aa1893d2b8ce3a8c05b62ccb7778fc91605df",
    "verify_taxrot_mech.py": "ff0d130526f7f0cace40c6431f01a54db768b6d4",
}


def _check_deps() -> None:
    here = Path(__file__).resolve().parent
    for f, h in _DEPS.items():
        got = hashlib.sha1((here / f).read_bytes()).hexdigest()
        if got != h:
            raise RuntimeError(f"r2_rotation_final: {f} changed since validation ({got} != {h}); "
                               "cached results may be stale -- re-validate before running")


class R2Rank(Rank):
    def __init__(self, menu=None, menu_by_year=None, anchor=None, margin=0.0, **kw):
        self.menu_by_year = {int(y): list(m) for y, m in (menu_by_year or {}).items()}
        if menu is None:
            if not self.menu_by_year:
                raise ValueError("menu or menu_by_year required")
            menu = sorted({t for m in self.menu_by_year.values() for t in m})
        super().__init__(menu, **kw)
        self.anchor = anchor
        self.margin = float(margin or 0.0)
        if self.anchor and self.core:
            raise ValueError("anchor and core are exclusive")

    def _menu_now(self, ctx):
        if not self.menu_by_year:
            return self.menu
        return self.menu_by_year.get(ctx.date.year, [])

    def weights(self, ctx, rebalance_day):
        if self.menu_by_year:
            self.menu = self._menu_now(ctx)
        if not self.anchor:
            return Rank.weights(self, ctx, rebalance_day)
        return self._anchored(ctx)

    def _anchored(self, ctx):
        a = self.anchor
        if ctx.price(a) is None:
            return {}
        live = [t for t in self.menu if t != a and ctx.price(t) is not None]
        sc = self._scores(ctx, live + [a])
        sa = sc.pop(a, None)
        if sa is None:                         # anchor not scoreable yet: hold the anchor
            self.last_order = []
            return {a: 1.0}
        order = sorted(sc, key=lambda t: (-sc[t], t))
        self.last_order = list(order)
        held = {t for t, q in ctx.positions.items() if q > 0}
        n, top = self.top_n, self.top_n + self.hold_buffer
        keep = [t for t in order[:top] if t in held and sc[t] > sa][:n]
        enter = [t for t in order if t not in keep and sc[t] >= sa + self.margin]
        picks = keep + enter[: n - len(keep)]
        w = {t: 1.0 / n for t in picks}
        if len(picks) < n:
            w[a] = w.get(a, 0.0) + (n - len(picks)) / n
        return w


def _r2_tickers(p):
    q = dict(p)
    if q.get("menu") is None:
        q["menu"] = sorted({t for m in (p.get("menu_by_year") or {}).values() for t in m})
    out = _rank_tickers(q)
    if p.get("anchor"):
        out.append(p["anchor"])
    return list(dict.fromkeys(out))


register_signal("r2_rotation_final.rank", lambda p: R2Rank(**p), _r2_tickers)


class R2Strategy(XTRStrategy):
    def __init__(self, signal, trim_only=None, **kw):
        super().__init__(signal, **kw)
        self.trim_only = set(trim_only or ())

    def _tax_sells(self, ctx, pv, tgt) -> None:
        if not self.trim_only or self.trim:
            return XTRStrategy._tax_sells(self, ctx, pv, tgt)
        if not self.exact_budget:
            raise ValueError("trim_only requires exact_budget=True")
        # XTRStrategy's exact-budget branch, except that names in trim_only may be trimmed.
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        cands = []
        for t, target in tgt.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held - 1e-12:
                continue
            if target > 1e-12 and t not in self.trim_only:
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


def _build(c):
    _check_deps()
    factory, _, _ = SIGNALS[c["signal"]]
    sig = factory(c.get("params", {}))
    kw = {k: c[k] for k in _X_KEYS if k in c}
    if c.get("trim_only"):
        return R2Strategy(sig, trim_only=c["trim_only"], **kw)
    return XTRStrategy(sig, **kw)


register_kind("r2_rotation_final.ws", _build, _tr_tickers)

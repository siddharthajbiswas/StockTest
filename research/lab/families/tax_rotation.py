"""Tax-managed rotation family: refine the site's "Beat the S&P (CA)" preset.

The incumbent is TaxManagedCombo(momentum 12-1, top 5, quarterly, 1%/yr gain
budget) over 22 ETFs. This module adds what is needed to probe it from every
side, while staying inside the engine's ordinary order path:

Signal  "tax_rotation.rank"
    Rank a menu by a score and hold the top N.
      score    "ret"     trailing total return over `lookback` bars ending
                         `skip` bars ago; a list of lookbacks is blended by
                         average rank (blend="rank") or mean return ("mean")
               "riskadj" return / annualised daily vol over `vol_window`
                         (vol_window=None: the lookback itself)
               "high52"  close / max close of the last `lookback` bars
               "resid"   residual momentum: t-stat of the daily residuals vs
                         SPY over the lookback (skip excluded)
               "random"  a seeded random ranking (the control); names are
                         eligible on the same history rule (`min_hist`)
      top_n, weighting ("equal" | "invvol"), hold_buffer (keep a held name
      while it ranks within top_n + buffer), sell_losers (drop held names whose
      position is down more than this fraction -> sold for the loss),
      abs_filter + fallback (hold `fallback` instead of a pick whose return is
      <= abs_filter), core ({ticker: weight} held fixed; the sleeve gets the
      rest -> core-satellite).

Kind  "tax_rotation.ws"
    blocks.WeightStrategy plus:
      buy_order   "prop" (scale every buy to the cash available, the lab's
                  default) or "alpha" (fill buys in alphabetical order until
                  cash runs out -- exactly what the site's TaxManagedCombo
                  does), so the two executions can be compared like for like.
      shadow      [st_rate, lt_rate]: when the engine runs WITHOUT tax (the
                  NONE regime) keep shadow tax lots and make the very same
                  tax-managed decisions as in a taxable account ("let winners
                  run, cut losers" in an IRA). Ignored when taxes are on.
      wash_groups list of ticker groups treated as one security by the wash
                  guard (substantially identical funds: SPY/IVV/VOO, ...).
                  "default" uses IDENTICAL_GROUPS below.
      strict_wash also refuse a *partial* loss sale of a name bought within
                  the last `wash_days` (the wash-sale rule's look-back side,
                  which the engine does not model).
      buy_order   also "rank": fill buys best-ranked first until cash runs out.
      reb_offset  shift the Q/S/A/Mk rebalance months by this many months
                  (timing-luck check: Q in Feb/May/Aug/Nov, S in Apr/Oct...).
      max_weight  trim any position above this weight at each rebalance even
                  if the gain budget is exhausted (concentration cap).
      trim        False: never sell (down) a name the signal still wants, so
                  the gain budget is spent only on exits of names that left
                  the target list (winners run without being trimmed back to
                  equal weight). Default True (= TaxManagedCombo).
      gain_order  "small" (default, = TaxManagedCombo: losses, then long-term
                  gains smallest-first, then short-term) or "rank": losses,
                  then long- before short-term, then the WORST-ranked name
                  first, so a limited budget forces out the names that fell
                  furthest out of favour ("frozen winners" check). With
                  hold_buffer=N and st_gains=False this is "sell long-term
                  winners only when they fall out of the top 2N, budget
                  permitting".

Nothing here sees the future: every score reads np_closes() (history up to
today's close, at which orders fill).
"""
from __future__ import annotations

import math
import random as _random

import numpy as np

from ..blocks import Signal, WeightStrategy, np_closes, normalize, period_key
from ..registry import SIGNALS, register_kind, register_signal

# --------------------------------------------------------------------------
# menus (explicit lists are also written into every config, so configs are
# self-contained; these names are only conveniences for sweep scripts)
# --------------------------------------------------------------------------
INC22 = ["SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
         "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
BROAD11 = ["SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP"]
SECTORS11 = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
IY_SECTORS = ["IYM", "IYZ", "IYE", "IYF", "IYJ", "IYW", "IYK", "IYR", "IDU", "IYH", "IYC"]
COUNTRIES = ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWM", "EWN",
             "EWO", "EWP", "EWQ", "EWS", "EWT", "EWU", "EWW", "EWY", "EWZ"]
FACTORS = ["IWD", "IWF", "IWN", "IWO", "IWS", "IWP", "IJS", "IJT", "RPV", "RPG", "RZV",
           "RZG", "SPHQ", "DVY", "VIG", "SDY", "PKW", "PDP", "FVD", "XMMO", "SPY"]

# Different-index substitutes for tax-loss harvesting (never the same index:
# SPY->IWB is S&P 500 -> Russell 1000, XLK->IYW is S&P Tech Select -> DJ US Tech).
SUBS = {
    "SPY": "IWB", "QQQ": "ONEQ", "DIA": "OEF", "MDY": "IWR", "IWM": "IJR", "IJR": "IWM",
    "EFA": "VEA", "EEM": "VWO", "IWD": "IVE", "IWF": "IVW", "RSP": "VTI",
    "XLB": "IYM", "XLE": "IYE", "XLF": "IYF", "XLI": "IYJ", "XLK": "IYW", "XLP": "IYK",
    "XLU": "IDU", "XLV": "IYH", "XLY": "IYC", "XLRE": "IYR", "XLC": "IYZ",
}

# Substantially identical funds (same index): one security for the wash guard.
IDENTICAL_GROUPS = [
    ["SPY", "IVV", "VOO", "VFINX", "VFIAX"],
    ["MDY", "IJH"],
    ["IVW", "SPYG"],
    ["IVE", "SPYV"],
    ["GLD", "IAU", "GLDM"],
    ["VTI", "VTSMX"],
]

# Long-history (pre-ETF) analogue of the incumbent menu, for the "long"
# protocols (benchmark VFINX): S&P 500, small/extended/style index funds,
# international + EM, and Fidelity Select / Vanguard sector funds standing in
# for the sector SPDRs.
LONG_MENU = ["VFINX", "NAESX", "VEXMX", "VIVAX", "VIGRX", "PRITX", "VWIGX", "VEIEX",
             "FSPTX", "FSPHX", "FIDSX", "FSENX", "FSUTX", "FDFAX", "FSRPX", "FSCHX",
             "FSTCX", "FSDAX", "FSRFX", "FSDPX", "VGSIX"]


# --------------------------------------------------------------------------
# scores
# --------------------------------------------------------------------------
def _ret(c, lb, skip):
    i1 = len(c) - 1 - skip
    i0 = i1 - lb
    if i0 < 0 or c[i0] <= 0:
        return None
    return c[i1] / c[i0] - 1.0


def _vol(c, n):
    if len(c) < n + 1:
        return None
    x = c[-(n + 1):]
    r = np.diff(x) / x[:-1]
    s = r.std()
    return s * math.sqrt(252) if s > 0 else None


class Rank(Signal):
    def __init__(self, menu, score="ret", lookback=252, skip=21, top_n=5,
                 weighting="equal", vol_window=63, blend="rank", seed=None,
                 min_hist=None, hold_buffer=0, sell_losers=None, abs_filter=None,
                 fallback=None, core=None, market="SPY"):
        self.menu = list(menu)
        self.score = score
        self.lookbacks = list(lookback) if isinstance(lookback, (list, tuple)) else [lookback]
        self.skip = int(skip)
        self.top_n = int(top_n)
        self.weighting = weighting
        self.vol_window = vol_window
        self.blend = blend
        self.seed = seed
        self.hold_buffer = int(hold_buffer or 0)
        self.sell_losers = sell_losers
        self.abs_filter = abs_filter
        self.fallback = fallback
        self.core = dict(core or {})
        self.market = market
        if min_hist is None:
            if score == "high52":
                min_hist = max(self.lookbacks)
            else:
                min_hist = max(self.lookbacks) + self.skip + 1
        self.min_hist = int(min_hist)
        self._rng = _random.Random(seed) if score == "random" else None

    # ---- per-name raw scores ------------------------------------------
    def _scores(self, ctx, names):
        sc = {}
        need = self.min_hist
        if self.score == "random":
            for t in names:
                if len(np_closes(ctx, t, need)) >= need:
                    sc[t] = self._rng.random()
            return sc
        if self.score in ("ret",):
            rets = {}
            for t in names:
                c = np_closes(ctx, t, need)
                if len(c) < need:
                    continue
                rs = [_ret(c, lb, self.skip) for lb in self.lookbacks]
                if any(r is None for r in rs):
                    continue
                rets[t] = rs
            if not rets:
                return {}
            if len(self.lookbacks) == 1:
                return {t: v[0] for t, v in rets.items()}
            ks = list(rets)
            if self.blend == "rank":
                arr = np.array([rets[t] for t in ks])
                rk = arr.argsort(axis=0).argsort(axis=0)
                return {t: float(rk[i].mean()) for i, t in enumerate(ks)}
            return {t: float(np.mean(rets[t])) for t in ks}
        if self.score == "riskadj":
            lb = self.lookbacks[0]
            vw = self.vol_window or lb
            n = max(need, vw + 1)
            for t in names:
                c = np_closes(ctx, t, n)
                if len(c) < n:
                    continue
                r = _ret(c, lb, self.skip)
                v = _vol(c, vw)
                if r is None or not v:
                    continue
                sc[t] = r / v
            return sc
        if self.score == "high52":
            lb = self.lookbacks[0]
            for t in names:
                c = np_closes(ctx, t, lb)
                if len(c) < lb:
                    continue
                m = c.max()
                if m > 0:
                    sc[t] = c[-1] / m
            return sc
        if self.score == "resid":
            lb = self.lookbacks[0]
            cm = np_closes(ctx, self.market, need)
            if len(cm) < need:
                return {}
            rm = np.diff(np.log(cm))[: len(cm) - 1 - self.skip]
            for t in names:
                c = np_closes(ctx, t, need)
                if len(c) < need or (c <= 0).any():
                    continue
                ri = np.diff(np.log(c))[: len(c) - 1 - self.skip]
                vm = rm.var()
                beta = float(np.cov(ri, rm, ddof=0)[0, 1] / vm) if vm > 0 else 1.0
                e = ri - beta * rm
                s = e.std()
                if s > 0:
                    sc[t] = float(e.mean() / s * math.sqrt(len(e)))
            return sc
        raise ValueError(f"unknown score {self.score!r}")

    def _secondary(self, ctx, t):
        c = np_closes(ctx, t, 253)
        if len(c) < 2:
            return 0.0
        return c[-1] / c[0] - 1.0

    def _position_return(self, ctx, t):
        lots = ctx.lots(t)
        if not lots:
            return None
        basis = sum(sh * c for _, sh, c in lots)
        sh = sum(s for _, s, _ in lots)
        px = ctx.price(t)
        if basis <= 0 or px is None:
            return None
        net = px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
        return sh * net / basis - 1.0

    # ---- weights ---------------------------------------------------------
    def weights(self, ctx, rebalance_day):
        live = [t for t in self.menu if ctx.price(t) is not None]
        sc = self._scores(ctx, live)
        core = {t: w for t, w in self.core.items() if ctx.price(t) is not None}
        core_w = sum(self.core.values())
        sleeve = max(0.0, 1.0 - core_w)
        if not sc:
            if core:
                return normalize(core, 1.0)
            fb = self.fallback
            return {fb: 1.0} if fb and ctx.price(fb) is not None else {}
        if self.score == "high52":
            order = sorted(sc, key=lambda t: (-sc[t], -self._secondary(ctx, t), t))
        else:
            order = sorted(sc, key=lambda t: (-sc[t], t))
        held = {t for t, q in ctx.positions.items() if q > 0}
        if self.sell_losers is not None:
            losers = set()
            for t in held:
                if t in sc:
                    pr = self._position_return(ctx, t)
                    if pr is not None and pr < -self.sell_losers:
                        losers.add(t)
            order = [t for t in order if t not in losers]
        self.last_order = list(order)
        if self.hold_buffer > 0:
            keep = [t for t in order[: self.top_n + self.hold_buffer] if t in held][: self.top_n]
            rest = [t for t in order if t not in keep]
            picks = keep + rest[: self.top_n - len(keep)]
        else:
            picks = order[: self.top_n]
        w = {}
        for t in picks:
            if self.weighting == "invvol":
                c = np_closes(ctx, t, self.vol_window + 1)
                v = _vol(c, self.vol_window)
                w[t] = 1.0 / v if v else 0.0
            else:
                w[t] = 1.0
        w = normalize(w, 1.0)
        if self.abs_filter is not None and self.score == "ret":
            fb = self.fallback
            out, moved = {}, 0.0
            for t, x in w.items():
                c = np_closes(ctx, t, self.min_hist)
                r = np.mean([_ret(c, lb, self.skip) for lb in self.lookbacks])
                if r <= self.abs_filter:
                    moved += x
                else:
                    out[t] = x
            if moved > 0 and fb and ctx.price(fb) is not None:
                out[fb] = out.get(fb, 0.0) + moved
            w = out
        if not w and not core:
            return {}
        out = {t: x * sleeve for t, x in w.items()}
        if core:
            cw = normalize(core, core_w)
            for t, x in cw.items():
                out[t] = out.get(t, 0.0) + x
        if not w:
            return normalize(out, 1.0)
        return out


def _rank_tickers(p):
    out = list(p["menu"]) + list((p.get("core") or {}).keys())
    if p.get("fallback"):
        out.append(p["fallback"])
    if p.get("score") == "resid":
        out.append(p.get("market", "SPY"))
    return list(dict.fromkeys(out))


register_signal("tax_rotation.rank", lambda p: Rank(**p), _rank_tickers)


# --------------------------------------------------------------------------
# execution kind
# --------------------------------------------------------------------------
class _ShadowCtx:
    """Context proxy that keeps FIFO tax lots of its own (cost and proceeds net
    of slippage and commission, exactly as the engine books them) so the tax-
    managed rule can run unchanged in an untaxed account."""

    def __init__(self, ctx, lt_days=365):
        self._ctx = ctx
        self._lots: dict = {}
        self._real: dict = {}
        self._lt_days = lt_days

    def __getattr__(self, name):
        return getattr(self._ctx, name)

    def lots(self, t):
        return [(d, s, c) for d, s, c in self._lots.get(t, [])]

    def realized_this_year(self):
        r = self._real.get(self._ctx.date.year)
        return (r[0], r[1]) if r else (0.0, 0.0)

    def is_long_term(self, d):
        return (self._ctx.date - d).days > self._lt_days

    def order(self, t, qty):
        ctx = self._ctx
        before = ctx.shares(t)
        ctx.order(t, qty)
        filled = ctx.shares(t) - before
        if abs(filled) < 1e-12:
            return
        px = ctx.price(t)
        slip, comm = ctx.slippage_pct, ctx.commission_pct
        if filled > 0:
            self._lots.setdefault(t, []).append([ctx.date, filled, px * (1 + slip) * (1 + comm)])
            return
        proceeds = px * (1 - slip) * (1 - comm)
        rem = -filled
        lots = self._lots.get(t, [])
        while rem > 1e-12 and lots:
            lot = lots[0]
            take = min(rem, lot[1])
            g = (proceeds - lot[2]) * take
            lt = (ctx.date - lot[0]).days > self._lt_days
            r = self._real.setdefault(ctx.date.year, [0.0, 0.0])
            r[1 if lt else 0] += g
            lot[1] -= take
            rem -= take
            if lot[1] <= 1e-12:
                lots.pop(0)


class TRStrategy(WeightStrategy):
    def __init__(self, signal, buy_order="prop", shadow=None, wash_groups=None,
                 strict_wash=False, reb_offset=0, max_weight=None, trim=True,
                 gain_order="small", **kw):
        super().__init__(signal, **kw)
        if gain_order not in ("small", "rank"):
            raise ValueError(f"unknown gain_order {gain_order!r}")
        self.trim = bool(trim)
        self.gain_order = gain_order
        self.buy_order = buy_order
        self.shadow = shadow
        groups = IDENTICAL_GROUPS if wash_groups == "default" else (wash_groups or [])
        self._group = {}
        for g in groups:
            for t in g:
                self._group[t] = tuple(g)
        self.strict_wash = strict_wash
        self.reb_offset = int(reb_offset or 0)
        self.max_weight = max_weight

    def initialize(self, ctx):
        super().initialize(ctx)
        self._last_buy: dict = {}
        self._sh = None

    def _key(self, date):
        cad = self.rebalance
        if not self.reb_offset or cad in ("D", "W", "M"):
            return period_key(date, cad)
        k = {"Q": 3, "S": 6, "A": 12}.get(cad) or int(cad[1:])
        return (date.year * 12 + date.month - 1 - self.reb_offset) // k

    def on_day(self, ctx):
        c = ctx
        if self.shadow and ctx._engine.tax_policy is None:
            if self._sh is None:
                self._sh = _ShadowCtx(ctx)
            c = self._sh
        if not self.reb_offset:
            return WeightStrategy.on_day(self, c)
        # WeightStrategy.on_day with the rebalance months shifted by reb_offset
        key = self._key(c.date)
        reb = key != self._last
        if reb:
            self._last = key
        w = None
        if reb or self.signal.daily:
            w = self.signal.weights(c, reb)
        if w is not None:
            self._target = dict(w)
            self._execute(c, w)
        elif self.harvest is not None:
            hk = period_key(c.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(c)

    def _execute(self, ctx, w) -> None:
        if self.max_weight is None:
            return WeightStrategy._execute(self, ctx, w)
        pv = ctx.portfolio_value
        if pv <= 0:
            return
        # concentration cap: trim any position above max_weight first, whatever
        # the gain budget says (the realized gain still uses up this year's room)
        for t in sorted(ctx.positions):
            px = ctx.price(t)
            if px is None or px <= 0:
                continue
            held = ctx.shares(t)
            cap = pv * self.max_weight / px
            if held > cap * 1.0001:
                net = self._net_px(ctx, px)
                gain, _ = self._gain_if_sold(ctx, t, held - cap, net)
                ctx.order(t, cap - held)
                if gain < 0:
                    self._loss_sale[t] = ctx.date
        w2 = {}
        for t, x in w.items():
            w2[t] = min(x, self.max_weight)
        return WeightStrategy._execute(self, ctx, w2)

    # ---- wash guard over identical-index groups ---------------------------
    def _wash_blocked(self, ctx, t) -> bool:
        for u in self._group.get(t, (t,)):
            last = self._loss_sale.get(u)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                return True
        return False

    def _recent_buy(self, ctx, t) -> bool:
        for u in self._group.get(t, (t,)):
            last = self._last_buy.get(u)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                return True
        return False

    def _tax_sells(self, ctx, pv, tgt) -> None:
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        cands = []
        for t, target in tgt.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held - 1e-12:
                continue
            if not self.trim and target > 1e-12:
                continue                     # still wanted: never trimmed
            qty = held - target
            net = self._net_px(ctx, ctx.price(t))
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            cands.append((gain > 0, not all_lt, gain, t, qty, target))
        if self.gain_order == "rank":
            order = getattr(self.signal, "last_order", None) or []
            at = {t: i for i, t in enumerate(order)}
            worst = len(order)
            # losses first (as before), then long- before short-term gains,
            # then the worst-ranked (unranked = worst) name first
            cands.sort(key=lambda c: (c[0], c[1], -at.get(c[3], worst) if c[0] else 0,
                                      c[2], c[3]))
        else:
            cands.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, is_short, gain, t, qty, target in cands:
            if not is_gain:
                if (self.strict_wash and gain < 0 and target > 1e-9
                        and self._recent_buy(ctx, t)):
                    continue                 # partial loss sale after a recent buy
                sell = qty
            elif is_short and not self.st_gains:
                continue
            elif gain <= room + 1e-9:
                sell = qty
            elif room > 1e-9:
                frac = room / gain
                if frac <= 0.02:
                    continue
                sell = qty * frac
            else:
                continue
            room -= gain * (sell / qty)
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date

    def _buys(self, ctx, tgt) -> None:
        buys = []
        for t in sorted(tgt):
            delta = tgt[t] - ctx.shares(t)
            if delta <= 1e-12:
                continue
            if self.execution == "tax" and self._wash_blocked(ctx, t):
                continue
            buys.append((t, delta))
        if not buys:
            return
        if self.buy_order in ("alpha", "rank"):
            if self.buy_order == "rank":
                order = getattr(self.signal, "last_order", None) or []
                at = {t: i for i, t in enumerate(order)}
                buys.sort(key=lambda b: (at.get(b[0], len(order)), b[0]))
            for t, d in buys:
                before = ctx.shares(t)
                ctx.order(t, d)
                if ctx.shares(t) > before + 1e-12:
                    self._last_buy[t] = ctx.date
            return
        cost_mult = (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)
        need = sum(d * ctx.price(t) * cost_mult for t, d in buys)
        cash = ctx.cash
        if need <= 0 or cash <= 0:
            return
        scale = min(1.0, cash / need * 0.999999)
        for t, d in buys:
            before = ctx.shares(t)
            ctx.order(t, d * scale)
            if ctx.shares(t) > before + 1e-12:
                self._last_buy[t] = ctx.date

    def _harvest(self, ctx) -> None:
        pos = ctx.positions
        for t in sorted(pos):
            px = ctx.price(t)
            if px is None:
                continue
            lots = ctx.lots(t)
            if not lots:
                continue
            basis = sum(sh * c for _, sh, c in lots)
            shares = sum(sh for _, sh, _ in lots)
            if shares <= 0 or basis <= 0:
                continue
            val = shares * self._net_px(ctx, px)
            if val / basis - 1.0 > -self.harvest:
                continue
            ctx.order(t, -pos[t])
            self._loss_sale[t] = ctx.date
            sub = self.substitutes.get(t)
            if sub and ctx.price(sub) is not None and not self._wash_blocked(ctx, sub):
                q = val / (ctx.price(sub) * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)) * 0.999999
                before = ctx.shares(sub)
                ctx.order(sub, q)
                if ctx.shares(sub) > before + 1e-12:
                    self._last_buy[sub] = ctx.date


_TR_KEYS = ("rebalance", "execution", "band", "gain_budget", "wash_days", "st_gains",
            "harvest", "harvest_freq", "substitutes", "min_trade_frac",
            "buy_order", "shadow", "wash_groups", "strict_wash", "reb_offset", "max_weight",
            "trim", "gain_order")


def _tr_build(c):
    factory, _, _ = SIGNALS[c["signal"]]
    sig = factory(c.get("params", {}))
    kw = {k: c[k] for k in _TR_KEYS if k in c}
    return TRStrategy(sig, **kw)


def _tr_tickers(c):
    _, tick, _ = SIGNALS[c["signal"]]
    extra = list((c.get("substitutes") or {}).values())
    return list(dict.fromkeys(list(tick(c.get("params", {}))) + extra + ["SPY"]))


register_kind("tax_rotation.ws", _tr_build, _tr_tickers)

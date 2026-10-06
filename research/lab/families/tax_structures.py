"""Pure tax structures -- no return forecasting (FAMILY_KEY = tax_structures).

Question: how much after-tax alpha does tax management ALONE add while the
portfolio keeps market-like exposure?

Nothing in this module forecasts returns. Every strategy holds a fixed exposure
(one fund, a set of sector funds, or a static mix) and varies only HOW it is
held for tax purposes: whether and how it is rebalanced, under which realized-
gain budget, and whether losses are harvested into a fund that tracks a
DIFFERENT index of the same exposure.

Kind "tax_structures.slots"  (SlotPortfolio)
--------------------------------------------
The portfolio is a list of exposure *slots*. A slot is a chain of
interchangeable funds that track different indexes of the same exposure
(S&P 500 -> Russell 1000 -> CRSP US total market ...; XLK -> IYW -> VGT), so a
loss can be realized without leaving the exposure and without a wash sale.
The first fund of a chain is the slot's *home*; a slot is live from the first
day its home fund trades (XLRE's slot from 2015-10, XLC's from 2018-06).

    {"kind": "tax_structures.slots",
     "slots": [["SPY", "IWB", "VTI"]],    # chains; a ticker may appear in one chain only
     "weights": "equal" | [w1, w2, ...] | "fit",
     "fit_target": "SPY", "fit_days": 252, # "fit": non-negative least squares of the
                                           # target's trailing daily returns on the
                                           # live home funds' (a replica of SPY)
     "rebalance": null | "M" | "Q" | "S" | "A",   # null = drift, never rebalanced
     "reb_rule": "standard" | "tax",
     "gain_budget": 0.0,                  # "tax": losses always; gains only while the
     "st_gains": true,                    # year's net realized gain <= budget x PV
     "band": 0.0,                         # trade only slots off target by > band
     "refit": false,                      # "fit": re-estimate weights at each rebalance
     "harvest": null | 0.05,              # sell a fund whose position is down > 5% ...
     "harvest_freq": "D" | "W" | "M",     # ... checked on this cadence, and buy the
                                          # next fund of its chain with the proceeds
     "swap_back": null | "any" | "loss" | "lt" | "budget",
     "wash_days": 31,
     "cover_cash": true,
     "offset_days": 0}                    # shift rebalance boundaries by N calendar
                                          # days (rebalance-timing-luck checks)

Day by day (only from the window start; the lab's Gate holds cash before it):
  1. first day: buy each live slot's buy-fund at its target weight;
  2. if cash is negative (the engine settles last year's tax from cash in
     January) sell to cover it: losses first, then long-term gains smallest-
     first, then short-term -- so no strategy borrows its tax bill at 0%;
  3. on rebalance boundaries: trade slots back to target weight. Sells are
     taken losses first, then long-term gains smallest-first, then short-term;
     "tax" rations gains by the budget (TaxManagedCombo's rule), "standard"
     sells whatever it must. Buys go to the first fund of the chain that is
     tradable and not wash-blocked (so the slot drifts back to its home fund);
  4. on harvest boundaries: swap-back check, then harvest check.

Swap-back rules (after the home fund's 31-day wash window):
  "any"     always sell the substitute and rebuy the home fund (realizes
            whatever gain the substitute has, usually short-term);
  "loss"    only if the substitute is at a loss (a second harvest);
  "lt"      only if the substitute is at a loss or its gain is long-term;
  "budget"  only if at a loss or the gain fits the year's gain budget.

Wash-sale discipline (the engine itself does not enforce the rule):
  * a fund sold at a loss -- or any fund tracking the same index (IDENTICAL) --
    is not bought for `wash_days`;
  * a PARTIAL sale at a loss of a fund bought within `wash_days` is skipped
    (the look-back half of the rule) by the tax-aware paths ("tax" rebalancing
    and the cash cover); selling a whole position is fine; "standard"
    rebalancing is the plain, tax-blind baseline and does not check;
  * chains only pair funds that track different indexes.

In the NONE regime the engine keeps no tax lots, so nothing is ever "at a
loss": harvesting is off and "tax" rebalancing behaves like "standard" (that is
what one would do in an IRA). Use the lab's ZERO regime (tax accounting on,
0% rates; registered in families/variants.py) to run the very same decisions
without tax.

Nothing here can see the future: weights read np_closes() (closes up to
today's close, at which orders fill); everything else reads the portfolio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtester import Strategy

from ..blocks import np_closes, period_key
from ..registry import register_kind

# --------------------------------------------------------------------------
# instruments
# --------------------------------------------------------------------------
# Funds tracking the SAME index (substantially identical for the wash-sale
# rule): selling one at a loss blocks buying any of them for wash_days.
IDENTICAL = [
    ["SPY", "IVV", "VOO", "VFINX", "VFIAX"],
    ["VTI", "VTSMX"],
    ["MDY", "IJH"],
    ["IVW", "SPYG"],
    ["IVE", "SPYV"],
    ["GLD", "IAU", "GLDM"],
]

# S&P 500 exposure: home SPY, then other large-cap / total-market indexes.
#   IWB Russell 1000 (2000-05), VTI CRSP US Total Market (2001-06), VV CRSP US
#   Large Cap (2004-01), SCHX DJ US Large-Cap TSM (2009-11), IWV Russell 3000
#   (2000-05), SCHB DJ US Broad Market (2009-11), VTSMX = VTI's mutual fund.
SPY_CHAINS = {
    "mix": ["SPY", "IWB", "VTI", "VV", "SCHX", "IWV", "SCHB"],
    "large": ["SPY", "IWB", "VV", "SCHX"],
    "total": ["SPY", "VTI", "IWV", "SCHB"],
    "iwb": ["SPY", "IWB"],
    "vti": ["SPY", "VTI"],
    "mf": ["SPY", "VTSMX", "IWB"],              # VTSMX (1992) gives a 2000 substitute
}

# Sector "direct indexing": Select Sector SPDR -> iShares (Dow Jones US / Russell
# sector) -> Vanguard (MSCI US IMI sector). Different index families.
SECTOR_CHAINS = [
    ["XLB", "IYM", "VAW"],
    ["XLE", "IYE", "VDE"],
    ["XLF", "IYF", "VFH"],
    ["XLI", "IYJ", "VIS"],
    ["XLK", "IYW", "VGT"],
    ["XLP", "IYK", "VDC"],
    ["XLU", "IDU", "VPU"],
    ["XLV", "IYH", "VHT"],
    ["XLY", "IYC", "VCR"],
    ["XLRE", "IYR", "VNQ"],
    ["XLC", "VOX"],
]

# The incumbent's 22-ETF menu with a different-index substitute chain for each
# fund (tickers unique across chains; RSP has no different-index twin).
INC22_CHAINS = [
    ["SPY", "IWB", "VV"],
    ["QQQ", "ONEQ"],
    ["DIA", "OEF"],
    ["MDY", "IWR", "VO"],
    ["IWM", "VB"],
    ["IJR", "SCHA"],
    ["EFA", "VEA", "IEFA"],
    ["EEM", "VWO", "IEMG"],
    ["IWD", "IVE", "VTV"],
    ["IWF", "IVW", "VUG"],
    ["RSP"],
] + SECTOR_CHAINS

INC22 = ["SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
         "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
SECTORS11 = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
SECTORS9 = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

_GROUP = {}
for _g in IDENTICAL:
    for _t in _g:
        _GROUP[_t] = tuple(_g)


# --------------------------------------------------------------------------
# the strategy
# --------------------------------------------------------------------------
class SlotPortfolio(Strategy):
    def __init__(self, slots, weights="equal", fit_target="SPY", fit_days=252,
                 rebalance=None, reb_rule="standard", gain_budget=0.0, st_gains=True,
                 band=0.0, refit=False, harvest=None, harvest_freq="D", swap_back=None,
                 wash_days=31, cover_cash=True, offset_days=0):
        self.slots = [list(c) for c in slots]
        seen = set()
        for c in self.slots:
            for t in c:
                if t in seen:
                    raise ValueError(f"ticker {t!r} appears in two slot chains")
                seen.add(t)
        if isinstance(weights, (list, tuple)) and len(weights) != len(self.slots):
            raise ValueError("weights must have one entry per slot")
        if reb_rule not in ("standard", "tax"):
            raise ValueError(f"unknown reb_rule {reb_rule!r}")
        if swap_back not in (None, "any", "loss", "lt", "budget"):
            raise ValueError(f"unknown swap_back {swap_back!r}")
        self.weights = weights
        self.fit_target = fit_target
        self.fit_days = int(fit_days)
        self.rebalance = rebalance
        self.reb_rule = reb_rule
        self.gain_budget = float(gain_budget)
        self.st_gains = bool(st_gains)
        self.band = float(band)
        self.refit = bool(refit)
        self.harvest = harvest
        self.harvest_freq = harvest_freq
        self.swap_back = swap_back
        self.wash_days = int(wash_days)
        self.cover_cash = bool(cover_cash)
        self.offset = pd.Timedelta(days=int(offset_days or 0))
        self._slot_of = {t: i for i, c in enumerate(self.slots) for t in c}

    # ---- lifecycle --------------------------------------------------------
    def initialize(self, ctx) -> None:
        self._started = False
        self._loss_sale: dict = {}
        self._last_buy: dict = {}
        self._last_reb = None
        self._last_h = None
        self._fit_w = None

    def on_day(self, ctx) -> None:
        d = ctx.date
        if not self._started:
            if self._initial_buy(ctx):
                self._started = True
                if self.rebalance:
                    self._last_reb = period_key(d - self.offset, self.rebalance)
                self._last_h = period_key(d, self.harvest_freq)
            return
        if self.cover_cash and ctx.cash < 0:
            pv = ctx.portfolio_value
            if pv > 0 and -ctx.cash > 1e-6 * pv:
                self._cover(ctx, -ctx.cash)
        if self.rebalance:
            key = period_key(d - self.offset, self.rebalance)
            if key != self._last_reb:
                self._last_reb = key
                self._rebalance(ctx)
        if self.harvest is not None or self.swap_back:
            hk = period_key(d, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                if self.swap_back:
                    self._swap_back(ctx)
                if self.harvest is not None:
                    self._harvest(ctx)

    # ---- helpers ----------------------------------------------------------
    @staticmethod
    def _net(ctx, px):
        return px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)

    @staticmethod
    def _gross(ctx, px):
        return px * (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)

    @staticmethod
    def _gain_if_sold(ctx, t, qty, net_px):
        rem, gain, all_lt = qty, 0.0, True
        for dt, sh, cost in ctx.lots(t):
            if rem <= 1e-12:
                break
            take = min(rem, sh)
            gain += (net_px - cost) * take
            if not ctx.is_long_term(dt):
                all_lt = False
            rem -= take
        return gain, all_lt

    def _blocked(self, ctx, t) -> bool:
        for u in _GROUP.get(t, (t,)):
            last = self._loss_sale.get(u)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                return True
        return False

    def _recent_buy(self, ctx, t) -> bool:
        for u in _GROUP.get(t, (t,)):
            last = self._last_buy.get(u)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                return True
        return False

    def _buy_value(self, ctx, t, value) -> None:
        px = ctx.price(t)
        if px is None or value <= 0:
            return
        before = ctx.shares(t)
        ctx.order(t, value / self._gross(ctx, px) * 0.999999)
        if ctx.shares(t) > before + 1e-12:
            self._last_buy[t] = ctx.date

    def _sell(self, ctx, t, qty, gain) -> None:
        ctx.order(t, -qty)
        if gain < 0:
            self._loss_sale[t] = ctx.date

    def _live(self, ctx):
        return [i for i, c in enumerate(self.slots) if ctx.price(c[0]) is not None]

    def _buy_fund(self, ctx, s):
        for t in self.slots[s]:
            if ctx.price(t) is not None and not self._blocked(ctx, t):
                return t
        return None

    def _sub_for(self, ctx, s, t):
        ch = self.slots[s]
        i = ch.index(t)
        grp = set(_GROUP.get(t, (t,)))
        for u in ch[i + 1:] + ch[:i]:
            if u in grp or ctx.price(u) is None or self._blocked(ctx, u):
                continue
            return u
        return None

    # ---- target weights ---------------------------------------------------
    def _fit(self, ctx, live):
        from scipy.optimize import nnls
        n = self.fit_days + 1
        y = np_closes(ctx, self.fit_target, n)
        cols = [np_closes(ctx, self.slots[s][0], n) for s in live]
        m = min([len(y)] + [len(c) for c in cols])
        if m < 64:
            return {s: 1.0 / len(live) for s in live}
        yy = y[-m:]
        Y = np.diff(yy) / yy[:-1]
        X = np.column_stack([np.diff(c[-m:]) / c[-m:][:-1] for c in cols])
        w, _ = nnls(X, Y)
        if w.sum() <= 0:
            return {s: 1.0 / len(live) for s in live}
        return {s: float(x) for s, x in zip(live, w)}

    def _targets(self, ctx, refit=False):
        live = self._live(ctx)
        if not live:
            return {}
        if self.weights == "equal":
            raw = {s: 1.0 for s in live}
        elif self.weights == "fit":
            if self._fit_w is None or refit:
                self._fit_w = self._fit(ctx, live)
            raw = {s: self._fit_w.get(s, 0.0) for s in live}
        else:
            raw = {s: float(self.weights[s]) for s in live}
        tot = sum(v for v in raw.values() if v > 0)
        if tot <= 0:
            return {}
        return {s: v / tot for s, v in raw.items() if v > 0}

    # ---- actions ----------------------------------------------------------
    def _initial_buy(self, ctx) -> bool:
        w = self._targets(ctx)
        if not w:
            return False
        pv = ctx.portfolio_value
        for s in sorted(w):
            t = self._buy_fund(ctx, s)
            if t is not None:
                self._buy_value(ctx, t, pv * w[s])
        return True

    def _fund_rows(self, ctx, tickers):
        """(is_gain, is_short, gain_frac, t, shares, px, net) for held funds."""
        rows = []
        for t in tickers:
            q = ctx.shares(t)
            px = ctx.price(t)
            if q <= 1e-12 or px is None:
                continue
            net = self._net(ctx, px)
            lots = ctx.lots(t)
            basis = sum(sh * c for _, sh, c in lots)
            frac = (q * net / basis - 1.0) if basis > 0 else 0.0
            all_lt = all(ctx.is_long_term(dt) for dt, _, _ in lots) if lots else True
            rows.append((frac > 0, not all_lt, frac, t, q, px, net))
        rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
        return rows

    def _cover(self, ctx, need) -> None:
        need *= 1.002
        for is_gain, _, _, t, q, px, net in self._fund_rows(ctx, list(ctx.positions)):
            if need <= 1e-9:
                break
            qty = min(q, need / net)
            gain, _ = self._gain_if_sold(ctx, t, qty, net)
            if gain < 0 and qty < q - 1e-9 and self._recent_buy(ctx, t):
                continue
            self._sell(ctx, t, qty, gain)
            need -= qty * net

    def _rebalance(self, ctx) -> None:
        pv = ctx.portfolio_value
        if pv <= 0:
            return
        w = self._targets(ctx, refit=self.refit and self.weights == "fit")
        if not w:
            return
        vals = {}
        for t, q in ctx.positions.items():
            s = self._slot_of.get(t)
            px = ctx.price(t)
            if s is None or px is None:
                continue
            vals[s] = vals.get(s, 0.0) + q * px
        cands = []
        buys = {}
        for s in sorted(set(w) | set(vals)):
            tgt = w.get(s, 0.0) * pv
            cur = vals.get(s, 0.0)
            if s in w and self.band > 0 and abs(cur - tgt) < self.band * pv:
                continue
            if cur > tgt + 1e-6 * pv:
                rem = cur - tgt
                for is_gain, _, _, t, q, px, net in self._fund_rows(ctx, self.slots[s]):
                    if rem <= 1e-9:
                        break
                    qty = min(q, rem / px)
                    gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
                    cands.append((gain > 0, not all_lt, gain, t, qty, q))
                    rem -= qty * px
            elif tgt > cur + 1e-6 * pv:
                buys[s] = tgt - cur
        # sells: losses first, then long-term gains smallest-first, then short-term
        cands.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        if self.reb_rule == "tax":
            st, lt = ctx.realized_this_year()
            room = self.gain_budget * pv - (st + lt)
        for is_gain, is_short, gain, t, qty, held in cands:
            if (self.reb_rule == "tax" and gain < 0 and qty < held - 1e-9
                    and self._recent_buy(ctx, t)):
                continue                       # partial loss sale after a recent buy
            if self.reb_rule == "tax" and is_gain:
                if is_short and not self.st_gains:
                    continue
                if gain <= room + 1e-9:
                    pass
                elif room > 1e-9 and room / gain > 0.02:
                    qty, gain = qty * room / gain, room
                else:
                    continue
            if self.reb_rule == "tax":
                room -= gain
            self._sell(ctx, t, qty, gain)
        # buys, scaled to the cash actually available
        plan = []
        for s in sorted(buys):
            t = self._buy_fund(ctx, s)
            if t is not None:
                plan.append((t, buys[s]))
        need = sum(v for _, v in plan)
        cash = ctx.cash
        if need <= 0 or cash <= 0:
            return
        scale = min(1.0, cash / need)
        for t, v in plan:
            self._buy_value(ctx, t, v * scale)

    def _harvest(self, ctx) -> None:
        for t in sorted(ctx.positions):
            s = self._slot_of.get(t)
            if s is None:
                continue
            px = ctx.price(t)
            if px is None:
                continue
            lots = ctx.lots(t)
            if not lots:
                continue
            shares = sum(sh for _, sh, _ in lots)
            basis = sum(sh * c for _, sh, c in lots)
            if shares <= 0 or basis <= 0:
                continue
            val = shares * self._net(ctx, px)
            if val / basis - 1.0 > -self.harvest:
                continue
            sub = self._sub_for(ctx, s, t)
            if sub is None:
                continue                       # no clean substitute: keep the loss open
            self._sell(ctx, t, ctx.shares(t), val - basis)
            self._buy_value(ctx, sub, min(val, max(ctx.cash, 0.0)))

    def _swap_back(self, ctx) -> None:
        room = None
        for s, ch in enumerate(self.slots):
            home = ch[0]
            if ctx.price(home) is None or self._blocked(ctx, home):
                continue
            for t in ch[1:]:
                q = ctx.shares(t)
                px = ctx.price(t)
                if q <= 1e-12 or px is None:
                    continue
                net = self._net(ctx, px)
                gain, all_lt = self._gain_if_sold(ctx, t, q, net)
                rule = self.swap_back
                if gain <= 0:
                    ok = True
                elif rule == "any":
                    ok = True
                elif rule == "lt":
                    ok = all_lt
                elif rule == "budget":
                    if room is None:
                        st, lt = ctx.realized_this_year()
                        room = self.gain_budget * ctx.portfolio_value - (st + lt)
                    ok = gain <= room + 1e-9 and (self.st_gains or all_lt)
                    if ok:
                        room -= gain
                else:                          # "loss"
                    ok = False
                if not ok:
                    continue
                self._sell(ctx, t, q, gain)
                self._buy_value(ctx, home, min(q * net, max(ctx.cash, 0.0)))


_KEYS = ("weights", "fit_target", "fit_days", "rebalance", "reb_rule", "gain_budget",
         "st_gains", "band", "refit", "harvest", "harvest_freq", "swap_back", "wash_days",
         "cover_cash", "offset_days")


def _build(c):
    return SlotPortfolio(c["slots"], **{k: c[k] for k in _KEYS if k in c})


def _tickers(c):
    out = [t for ch in c["slots"] for t in ch]
    if c.get("weights") == "fit":
        out.append(c.get("fit_target", "SPY"))
    return list(dict.fromkeys(out + ["SPY"]))


register_kind("tax_structures.slots", _build, _tickers)

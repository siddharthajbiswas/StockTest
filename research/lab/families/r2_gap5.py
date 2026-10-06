"""r2_gap5: specific-lot sales, exact gain-budget sizing and IRS netting.

Research-only engine options. Nothing in backtester/ or the lab core is edited:
everything here is a subclass, used only through this module's own runner.

  lot      "fifo"    the engine's rule: oldest lot first (default)
           "hifo"    highest cost basis first (ties: oldest first)
           "mintax"  lowest tax per share first: (net price - basis) x the
                     lot's own rate (short-term rate if held <= 365 days, else
                     the long-term rate); losses (negative tax) go first
  net      "pooled"  the engine's rule (backtester/tax.py compute_year_tax):
                     one loss pool (this year's ST and LT losses plus the whole
                     carryforward) applied to short-term gains first; terminal
                     liquidation tax in two steps (this year's realized gains,
                     then the unrealized gains with what is left of the carry),
                     exactly as Backtest.run and core.liquidation_value do
           "irs"     Schedule D: ST gains net against ST losses, LT against LT,
                     then a net loss of one character offsets a net gain of the
                     other; a net capital loss carries forward WITH ITS
                     CHARACTER (ST carry = an ST loss next year, LT carry = an
                     LT loss). The terminal liquidation is one tax year: this
                     year's realized plus all unrealized gains, netted together
           "irs3k"   "irs" plus the $3,000/yr deduction of a net capital loss
                     against ordinary income (ST loss used first), credited at
                     the ordinary rate (CA 44.3% = 35% federal + 9.3% state, no
                     NIIT on wages; FED 35%). Scale-dependent: the lab starts
                     with $100,000, so $3,000 is 3% of starting capital
  wash     "none"    the engine's rule (wash sales not modelled)
           "irs"     a lot sold at a loss while shares of the same ticker that
                     were bought within the 30 days before are still held, or
                     that are bought within the 30 days after, is a wash sale:
                     the loss is disallowed, added to the replacement shares'
                     basis, and the sold lot's holding period is tacked on
                     (IRS Pub. 550). A disallowance reaching back into a tax
                     year already settled is paid at once (an amended return)
  size     "avg"     the strategies' rule (the site's TaxManagedCombo and the
                     lab's tax execution): the last, budget-limited gain sale
                     sells qty x room / gain, i.e. it assumes the position's
                     AVERAGE gain per share
           "exact"   shares counted lot by lot in the order the engine will sell
                     them (whatever `lot` is): the year lands on the budget

Every strategy's "what would this sale realize" planner reads lots in the same
order the engine sells them; for fifo it is the original loop.

Config: {"kind": "r2_gap5.x", "base": <tax_rotation.ws | combo (tax_managed) |
weights config>, "lot", "net", "wash", "size", "offset_days", "lag"}; options
at their defaults are omitted (use `xcfg`). With every option at its default
the run is identical to the lab's run of `base` (scratch/r2_gap5/v1_identity.py).

Runner: `run(cfgs, protocol, regimes, workers)` is sweep.run's twin (same record
format, so metrics.summary / report.score apply unchanged; the benchmark is the
lab's SPY buy-and-hold, which never sells and is identical under every option).
Records are cached in research/lab/scratch/r2_gap5/cache, keyed by the config
and a hash of the code imported at start-up. The kind is also registered so
sweep can see it, but it refuses to run outside this module's engine.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
import traceback
from pathlib import Path

import pandas as pd

from backtester import Backtest, Strategy, TaxManagedCombo
from backtester.portfolio import Portfolio
from backtester.result import Result
from backtester.tax import Lot, compute_year_tax

from .. import core
from ..blocks import WeightStrategy, period_key
from ..registry import SIGNALS, register_kind
from .tax_rotation import _TR_KEYS, TRStrategy

HERE = Path(__file__).resolve()
LAB = HERE.parents[1]
ROOT = LAB.parents[1]
SCR = LAB / "scratch" / "r2_gap5"
CACHE = SCR / "cache"

LOTS = ("fifo", "hifo", "mintax")
NETS = ("pooled", "irs", "irs3k")
WASH = ("none", "irs")
SIZES = ("avg", "exact")
ORD_RATE = {"CA": 0.443, "FED": 0.35}
WASH_DAYS = 30


# ==========================================================================
# 1. tax netting
# ==========================================================================
def year_tax_irs(st: float, lt: float, cst: float, clt: float, policy,
                 ord_cap: float = 0.0, ord_rate: float = 0.0):
    """One tax year under IRS netting with character-preserving carryforwards.

    st / lt: the year's net short- / long-term realized gain (negative = loss);
    cst / clt: short- / long-term loss carried in (non-negative magnitudes).
    Returns (tax, new_cst, new_clt); tax < 0 only with ord_cap > 0 (a refund).
    """
    rs, rl = policy.short_term_rate, policy.long_term_rate
    s = st - cst
    lg = lt - clt
    if s >= 0.0 and lg >= 0.0:
        return s * rs + lg * rl, 0.0, 0.0
    if s < 0.0 and lg < 0.0:
        ls, ll = -s, -lg
    elif s < 0.0:                       # net ST loss offsets the net LT gain
        n = lg + s
        if n >= 0.0:
            return n * rl, 0.0, 0.0
        ls, ll = -n, 0.0
    else:                               # net LT loss offsets the net ST gain
        n = s + lg
        if n >= 0.0:
            return n * rs, 0.0, 0.0
        ls, ll = 0.0, -n
    if ord_cap > 0.0:
        u = min(ord_cap, ls)
        ls -= u
        u2 = min(ord_cap - u, ll)
        ll -= u2
        return -(u + u2) * ord_rate, ls, ll
    return 0.0, ls, ll


class Netting:
    """Carryforward state plus the yearly and terminal tax of one netting rule."""

    def __init__(self, net: str, policy, ord_rate: float = 0.0):
        if net not in NETS:
            raise ValueError(f"unknown netting {net!r}")
        self.net = net
        self.policy = policy
        self.ord_cap = 3000.0 if net == "irs3k" else 0.0
        self.ord_rate = ord_rate
        self.reset()

    def reset(self):
        self.carry = 0.0            # pooled
        self.cst = self.clt = 0.0   # irs

    def state(self):
        return (self.carry, self.cst, self.clt)

    def set_state(self, s):
        self.carry, self.cst, self.clt = s

    def year(self, st: float, lt: float) -> float:
        """Settle one tax year (updates the carry); returns the tax."""
        if self.net == "pooled":
            tax, self.carry = compute_year_tax(st, lt, self.carry, self.policy)
            return tax
        tax, self.cst, self.clt = year_tax_irs(st, lt, self.cst, self.clt, self.policy,
                                               self.ord_cap, self.ord_rate)
        return tax

    def terminal(self, r_st, r_lt, u_st, u_lt) -> tuple[float, float]:
        """(tax on this year's realized, tax on the unrealized) if everything
        were sold now; the state is not changed. "irs" taxes them as one year
        and returns (tax, 0)."""
        if self.net == "pooled":
            fy, c2 = compute_year_tax(r_st, r_lt, self.carry, self.policy)
            ut, _ = compute_year_tax(u_st, u_lt, c2, self.policy)
            return fy, ut
        tax, _, _ = year_tax_irs(r_st + u_st, r_lt + u_lt, self.cst, self.clt, self.policy,
                                 self.ord_cap, self.ord_rate)
        return tax, 0.0

    def chain(self, realized: dict, upto_year: int) -> tuple[float, tuple]:
        """Recompute the settlements of every tax year < upto_year from the
        realized buckets, starting from zero carry (the same call sequence as
        core.liquidation_value for "pooled"). Returns (total tax, end state)."""
        saved = self.state()
        self.reset()
        years = [y for y in realized if y < upto_year]
        total = 0.0
        if years:
            for y in range(min(years), upto_year):
                r = realized.get(y)
                if r is None:
                    if self.ord_cap == 0.0:
                        continue
                    r = {"st": 0.0, "lt": 0.0}
                total += self.year(r["st"], r["lt"])
        end = self.state()
        self.set_state(saved)
        return total, end


# ==========================================================================
# 2. lot ordering (shared by the engine and every strategy's planner)
# ==========================================================================
def order_indices(dates, costs, method: str, net_px: float, date, policy) -> list[int]:
    """Indices of lots (purchase dates, cost per share) in the order a sale at
    net price `net_px` on `date` consumes them under `method`."""
    n = len(costs)
    if method == "fifo" or n <= 1:
        return list(range(n))
    if method == "hifo":
        return sorted(range(n), key=lambda i: (-costs[i], i))
    if method == "mintax":
        rs, rl = policy.short_term_rate, policy.long_term_rate
        lt_days = policy.long_term_days

        def key(i):
            g = net_px - costs[i]
            lt = (date - dates[i]).days > lt_days
            return (g * (rl if lt else rs), -costs[i], i)
        return sorted(range(n), key=key)
    raise ValueError(f"unknown lot method {method!r}")


class XLot(Lot):
    """A Lot that also remembers its real purchase date (`bought`; `date` is the
    holding-period start, which a wash-sale adjustment moves earlier) and how
    many of its shares may still serve as wash-sale replacement shares."""

    def __init__(self, date, shares, cost_per_share, bought=None, repl=None):
        super().__init__(date, shares, cost_per_share)
        self.bought = date if bought is None else bought
        self.repl = shares if repl is None else repl


# ==========================================================================
# 3. the portfolio: lot selection and wash sales
# ==========================================================================
class LotPortfolio(Portfolio):
    """backtester.Portfolio with a lot-selection method and optional IRS wash-
    sale accounting. lot="fifo", wash="none", no audit: the base class code."""

    def setup(self, lot: str, wash: str, audit: bool = False):
        if lot not in LOTS:
            raise ValueError(f"unknown lot method {lot!r}")
        if wash not in WASH:
            raise ValueError(f"unknown wash rule {wash!r}")
        self.lot_method = lot
        self.wash = wash
        self.amended_years: set = set()     # settled years whose realized changed
        self._pending: dict = {}            # ticker -> [[sale_date, shares, loss/sh, held_days, year, lt]]
        self.audit = [] if audit else None  # (date, ticker, shares, gain, lt, cost, bought, disallowed)
        self.wash_log = [] if audit else None
        return self

    def _plain(self) -> bool:
        return self.lot_method == "fifo" and self.wash == "none" and self.audit is None

    # ---- buys -------------------------------------------------------------
    def _open_lot(self, date, ticker, shares, cost_per_share):
        if self._plain():
            return Portfolio._open_lot(self, date, ticker, shares, cost_per_share)
        lots = self.lots.setdefault(ticker, [])
        lot = XLot(date, shares, cost_per_share)
        lots.append(lot)
        if self.wash == "none":
            return
        # after-side: loss sales of this ticker in the last 30 days not yet matched
        pend = self._pending.get(ticker)
        if not pend:
            return
        keep = []
        for p in pend:
            sale_date, sh, loss_ps, held_days, year, lt = p
            if (date - sale_date).days > WASH_DAYS or sh <= 1e-12:
                continue
            if lot.repl <= 1e-12:
                keep.append(p)
                continue
            m = min(sh, lot.repl)
            self._disallow_into(lots, lot, m, loss_ps, held_days)
            b = self.realized.setdefault(year, {"st": 0.0, "lt": 0.0})
            b["lt" if lt else "st"] += m * loss_ps          # reverse the booked loss
            if year < date.year:
                self.amended_years.add(year)
            if self.wash_log is not None:
                self.wash_log.append(("after", sale_date, date, ticker, m, m * loss_ps))
            p[1] = sh - m
            if p[1] > 1e-12:
                keep.append(p)
        self._pending[ticker] = keep

    @staticmethod
    def _disallow_into(lots, lot, m, loss_ps, held_days):
        """Carry a disallowed loss of `loss_ps` per share into `m` replacement
        shares of `lot` (split off as their own lot when m < lot.shares)."""
        if m >= lot.shares - 1e-12:
            tgt = lot
        else:
            tgt = XLot(lot.date, m, lot.cost_per_share, bought=lot.bought, repl=0.0)
            lot.shares -= m
            lot.repl = max(0.0, lot.repl - m)
            lots.insert(lots.index(lot), tgt)
        tgt.cost_per_share += loss_ps
        tgt.date = tgt.date - pd.Timedelta(days=int(held_days))
        tgt.repl = 0.0

    # ---- sells ------------------------------------------------------------
    def _close_lots(self, date, ticker, shares, proceeds_per_share, policy):
        if self._plain():
            return Portfolio._close_lots(self, date, ticker, shares, proceeds_per_share, policy)
        lots = self.lots.get(ticker, [])
        order = order_indices([x.date for x in lots], [x.cost_per_share for x in lots],
                              self.lot_method, proceeds_per_share, date, policy)
        plan = []
        remaining = shares
        for i in order:
            if remaining <= 1e-12:
                break
            lot = lots[i]
            take = min(remaining, lot.shares)
            plan.append((lot, take))
            remaining -= take
        # shares of each lot still held once this whole sale is done
        after = {id(x): x.shares for x in lots}
        for lot, take in plan:
            after[id(lot)] -= take
        for lot, take in plan:
            gain = (proceeds_per_share - lot.cost_per_share) * take
            lt = policy.is_long_term((date - lot.date).days)
            dis = 0.0
            if self.wash == "irs" and gain < 0.0:
                kept = self._wash_loss(date, ticker, lots, lot, take, gain, policy, after)
                dis = kept - gain
                gain = kept
            if self.audit is not None:
                self.audit.append((date, ticker, take, gain, lt, lot.cost_per_share,
                                   getattr(lot, "bought", lot.date), dis))
            self._record_realized(date.year, gain, lt)
            lot.shares -= take
        self.lots[ticker] = [x for x in lots if x.shares > 1e-12]

    def _wash_loss(self, date, ticker, lots, lot, take, gain, policy, after):
        """Before-side matching of one loss piece: replacement shares are other
        lots of the ticker bought within the last 30 days and still held after
        this sale (earliest bought first). Returns the loss that stays
        deductible now; the unmatched part also becomes a pending loss for
        purchases in the next 30 days (after-side)."""
        loss_ps = -gain / take
        held_days = (date - lot.date).days
        left = take
        cands = [o for o in lots if o is not lot and getattr(o, "repl", 0.0) > 1e-12]
        cands.sort(key=lambda o: o.bought)
        for o in cands:
            if left <= 1e-12:
                break
            if (date - o.bought).days > WASH_DAYS or o.bought > date:
                continue
            avail = min(o.repl, after.get(id(o), 0.0))
            if avail <= 1e-12:
                continue
            m = min(left, avail)
            n_before = len(lots)
            self._disallow_into(lots, o, m, loss_ps, held_days)
            after[id(o)] = after.get(id(o), 0.0) - m
            if len(lots) > n_before:        # split: the new lot is fully held
                for x in lots:
                    if id(x) not in after:
                        after[id(x)] = x.shares
            if self.wash_log is not None:
                self.wash_log.append(("before", date, o.bought, ticker, m, m * loss_ps))
            left -= m
        if left > 1e-12:
            lt = policy.is_long_term(held_days)
            self._pending.setdefault(ticker, []).append([date, left, loss_ps, held_days, date.year, lt])
        return -left * loss_ps


# ==========================================================================
# 4. the engine
# ==========================================================================
class XBacktest(Backtest):
    """backtester.Backtest with a LotPortfolio and a netting rule."""

    def __init__(self, strategy, *, lot="fifo", net="pooled", wash="none", ord_rate=0.0,
                 audit=False, **kw):
        super().__init__(strategy, **kw)
        old = self.portfolio
        pf = LotPortfolio(cash=old.cash, commission_per_share=old.commission_per_share,
                          commission_pct=old.commission_pct)
        self.portfolio = pf.setup(lot, wash, audit)
        self.netting = Netting(net, self.tax_policy, ord_rate) if self.tax_policy else None
        self.opts = {"lot": lot, "net": net, "wash": wash}
        self._paid_prior = 0.0
        self._taxes_paid = 0.0
        self.amend_paid = 0.0

    def place_order(self, ticker: str, shares: float) -> None:
        Backtest.place_order(self, ticker, shares)
        pf = self.portfolio
        if pf.amended_years and self.netting is not None:
            # a wash sale reached back into a settled year: amend and pay now
            pf.amended_years.clear()
            due, end = self.netting.chain(pf.realized, self._date.year)
            extra = due - self._paid_prior
            pf.cash -= extra
            self._paid_prior = due
            self._taxes_paid += extra
            self.amend_paid += extra
            self.netting.set_state(end)

    def liquidation_value(self) -> tuple[float, float]:
        """(after-tax liquidation value, equity) now under this engine's rules;
        for net="pooled" the arithmetic of core.liquidation_value exactly."""
        pf = self.portfolio
        prices = self.current_prices()
        equity = pf.cash + pf.holdings_value(prices)
        if self.tax_policy is None:
            return equity, equity
        nt = self.netting
        saved = nt.state()
        _, end = nt.chain(pf.realized, self._date.year)
        nt.set_state(end)
        r = pf.realized.get(self._date.year, {"st": 0.0, "lt": 0.0})
        st_u, lt_u = pf.unrealized_gains(self._date, prices, self.tax_policy)
        a, b = nt.terminal(r["st"], r["lt"], st_u, lt_u)
        nt.set_state(saved)
        return equity - a - b, equity

    def run(self) -> Result:
        """Backtest.run with the yearly settlement and the terminal tax
        delegated to the netting rule (identical arithmetic for "pooled")."""
        self.strategy.initialize(self.ctx)
        market = self.market
        calendar = self.calendar
        cal_values = market.cal_values
        total_days = market.n
        equity_cash, equity_holdings, equity_total = [], [], []
        policy = self.tax_policy
        nt = self.netting
        prev_year = None
        self._taxes_paid = 0.0
        for i in range(total_days):
            self._i = i
            self._dv = cal_values[i]
            date = calendar[i]
            self._date = date
            self.today_prices = market.today_tradable[i]
            if policy is not None and prev_year is not None and date.year != prev_year:
                r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
                tax = nt.year(r["st"], r["lt"])
                self.portfolio.cash -= tax
                self._taxes_paid += tax
                self._paid_prior += tax
            prev_year = date.year
            self.ctx.date = date
            self.strategy.on_day(self.ctx)
            holdings = self.portfolio.holdings_value(self.current_prices())
            equity_cash.append(self.portfolio.cash)
            equity_holdings.append(holdings)
            equity_total.append(self.portfolio.cash + holdings)
        equity = pd.DataFrame({"cash": equity_cash, "holdings": equity_holdings, "total": equity_total},
                              index=pd.DatetimeIndex(calendar, name="date"))
        trades = pd.DataFrame([t.as_dict() for t in self.portfolio.trades])
        if not trades.empty:
            trades = trades.set_index("date")
        terminal_tax = None
        if policy is not None:
            r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
            st_u, lt_u = self.portfolio.unrealized_gains(self._date, self.current_prices(), policy)
            a, b = nt.terminal(r["st"], r["lt"], st_u, lt_u)
            terminal_tax = a + b
        return Result(equity=equity, trades=trades, starting_cash=self.starting_cash,
                      taxes_paid=(self._taxes_paid if policy is not None else None),
                      terminal_tax=terminal_tax)


class XGate(core.Gate):
    """core.Gate with each checkpoint valued by the engine's own netting rule
    (net="pooled": core.liquidation_value's arithmetic)."""

    def on_day(self, ctx) -> None:
        d = ctx.date
        if d < self.start:
            return
        self.inner.on_day(ctx)
        labels = self._ck.get(d)
        is_me = d in self._month_end
        if labels or is_me:
            liq, eq = ctx._engine.liquidation_value()
            if labels:
                for e in labels:
                    self.values[e] = (liq, eq, d)
            if is_me:
                self.months[d] = (liq, eq)


# ==========================================================================
# 5. strategy planners that read lots in the engine's sale order
# ==========================================================================
def lot_method_of(ctx) -> str:
    return getattr(ctx._engine.portfolio, "lot_method", "fifo")


def ordered_lots(ctx, t, net):
    lots = ctx.lots(t)
    m = lot_method_of(ctx)
    if m == "fifo" or len(lots) <= 1:
        return lots
    idx = order_indices([x[0] for x in lots], [x[2] for x in lots], m, net, ctx.date,
                        ctx._engine.tax_policy)
    return [lots[i] for i in idx]


def gain_if_sold(ctx, t, qty, net):
    """(gain, all_long_term) that selling `qty` of `t` at `net` books, lots in
    the engine's sale order. For fifo this is the original loop exactly."""
    rem = qty
    gain = 0.0
    all_lt = True
    for d, sh, cost in ordered_lots(ctx, t, net):
        if rem <= 1e-12:
            break
        take = min(rem, sh)
        gain += (net - cost) * take
        if not ctx.is_long_term(d):
            all_lt = False
        rem -= take
    return gain, all_lt


def shares_for_room(ctx, t, qty, net, room):
    """Largest number of shares (<= qty) whose sale, lots in the engine's sale
    order, realizes a net gain of at most `room` (losses on the way refill it)."""
    sold, left = 0.0, room
    for _, sh, cost in ordered_lots(ctx, t, net):
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


class _Sizing:
    """Mixin: sizing of the budget-limited partial gain sale."""

    size = "avg"
    sales_log = None

    def _partial(self, ctx, t, qty, gain, room, net):
        """(shares to sell, gain charged to the room) or None (skip)."""
        frac = room / gain
        if frac <= 0.02:                          # not worth a trade (original rule)
            return None
        if self.size == "exact":
            sell = shares_for_room(ctx, t, qty, net, room)
            if sell <= 1e-12:
                return None
            g, _ = gain_if_sold(ctx, t, sell, net)
            return sell, g
        sell = qty * frac
        return sell, gain * (sell / qty)

    def _log_sale(self, ctx, t, sell, net, partial, room):
        if self.sales_log is not None:
            g, all_lt = gain_if_sold(ctx, t, sell, net)
            self.sales_log.append((ctx.date, t, sell, g, all_lt, partial, room))


class XTRStrategy(_Sizing, TRStrategy):
    """tax_rotation.TRStrategy + lot-order planning, exact sizing, a boundary
    offset and a 1-day lag (offset / lag as verify_taxrot_robust.ws)."""

    _gain_if_sold = staticmethod(gain_if_sold)

    def __init__(self, signal, size="avg", offset_days=0, lag=0, **kw):
        super().__init__(signal, **kw)
        if self.shadow:
            raise ValueError("r2_gap5 does not support shadow lots")
        self.size = size
        self.offset_days = int(offset_days or 0)
        self.lag = int(lag or 0)

    def initialize(self, ctx):
        super().initialize(ctx)
        self._pending = None

    def on_day(self, ctx):
        if not self.offset_days and not self.lag:
            return TRStrategy.on_day(self, ctx)
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
            hk = period_key(ctx.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(ctx)

    def _tax_sells(self, ctx, pv, tgt) -> None:
        # TRStrategy._tax_sells, with the partial sale delegated to _partial
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
            partial = False
            if not is_gain:
                if (self.strict_wash and gain < 0 and target > 1e-9
                        and self._recent_buy(ctx, t)):
                    continue
                sell, used = qty, gain
            elif is_short and not self.st_gains:
                continue
            elif gain <= room + 1e-9:
                sell, used = qty, gain
            elif room > 1e-9:
                p = self._partial(ctx, t, qty, gain, room, self._net_px(ctx, ctx.price(t)))
                if p is None:
                    continue
                sell, used = p
                partial = True
            else:
                continue
            if self.sales_log is not None:
                self._log_sale(ctx, t, sell, self._net_px(ctx, ctx.price(t)), partial, room)
            room -= used
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date


class XTaxManagedCombo(_Sizing, TaxManagedCombo):
    """The site's TaxManagedCombo + lot-order planning, exact sizing and a
    boundary offset (as variants.combo_x). on_day is the original with the
    partial sale delegated to _partial."""

    _gain_if_sold = staticmethod(gain_if_sold)
    offset_days = 0

    def _period_key(self, date):
        if self.offset_days:
            date = date - pd.Timedelta(days=self.offset_days)
        return TaxManagedCombo._period_key(self, date)

    def on_day(self, ctx) -> None:
        key = self._period_key(ctx.date)
        if key == self._last_period:
            return
        self._last_period = key
        self._basket = self.picker.select(ctx, self._candidates(ctx), self.top_n)
        longs = [
            t for t in self._basket
            if ctx.can_trade(t)
            and self.timer.want_long(ctx, t, held=ctx.shares(t) > 0, entry_price=self._entry.get(t))
        ]
        pv = ctx.portfolio_value
        if pv <= 0:
            return
        weight = 1.0 / len(longs) if longs else 0.0
        wanted = set(longs)
        targets: dict = {}
        for t in wanted | set(ctx.positions):
            px = ctx.price(t)
            if px is None or px <= 0:
                continue
            targets[t] = (pv * weight / px) if t in wanted else 0.0
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        candidates = []
        for t, target in targets.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held:
                continue
            qty = held - target
            px = ctx.price(t)
            net = px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            candidates.append((gain > 0, not all_lt, gain, t, qty))
        candidates.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, _is_short, gain, t, qty in candidates:
            partial = False
            px = ctx.price(t)
            net = px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
            if not is_gain:
                sell = qty
                used = gain * (sell / qty)
            elif gain <= room + 1e-9:
                sell = qty
                used = gain * (sell / qty)
            elif room > 1e-9:
                p = self._partial(ctx, t, qty, gain, room, net)
                if p is None:
                    continue
                sell, used = p
                partial = True
            else:
                continue
            if self.sales_log is not None:
                self._log_sale(ctx, t, sell, net, partial, room)
            room -= used
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date
            if ctx.shares(t) <= 0:
                self._entry.pop(t, None)
        for t in sorted(longs):
            last = self._loss_sale.get(t)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                continue
            target = targets.get(t)
            if target is None:
                continue
            delta = target - ctx.shares(t)
            if delta > 0:
                ctx.order(t, delta)
        self._members = {t for t in longs if ctx.shares(t) > 0}
        for t in longs:
            if t not in self._entry and ctx.shares(t) > 0:
                px = ctx.price(t)
                if px is not None:
                    self._entry[t] = px


class XWeightStrategy(_Sizing, WeightStrategy):
    """blocks.WeightStrategy + lot-order planning, exact sizing and offsets /
    lag (as variants.weights_x)."""

    _gain_if_sold = staticmethod(gain_if_sold)

    def __init__(self, signal, size="avg", offset_days=0, lag=0, **kw):
        super().__init__(signal, **kw)
        self.size = size
        self.offset_days = int(offset_days or 0)
        self.lag = int(lag or 0)

    def initialize(self, ctx):
        super().initialize(ctx)
        self._pending = None

    def on_day(self, ctx):
        if not self.offset_days and not self.lag:
            return WeightStrategy.on_day(self, ctx)
        if self.lag and self._pending is not None:
            w, self._pending = self._pending, None
            self._target = dict(w)
            self._execute(ctx, w)
        key = period_key(ctx.date - pd.Timedelta(days=self.offset_days), self.rebalance)
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
            hk = period_key(ctx.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(ctx)

    def _tax_sells(self, ctx, pv, tgt) -> None:
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        cands = []
        for t, target in tgt.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held - 1e-12:
                continue
            qty = held - target
            net = self._net_px(ctx, ctx.price(t))
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            cands.append((gain > 0, not all_lt, gain, t, qty))
        cands.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, is_short, gain, t, qty in cands:
            partial = False
            if not is_gain:
                sell, used = qty, gain
            elif is_short and not self.st_gains:
                continue
            elif gain <= room + 1e-9:
                sell, used = qty, gain
            elif room > 1e-9:
                p = self._partial(ctx, t, qty, gain, room, self._net_px(ctx, ctx.price(t)))
                if p is None:
                    continue
                sell, used = p
                partial = True
            else:
                continue
            if self.sales_log is not None:
                self._log_sale(ctx, t, sell, self._net_px(ctx, ctx.price(t)), partial, room)
            room -= used
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date


# ==========================================================================
# 6. configs and strategy construction
# ==========================================================================
DEFAULTS = {"lot": "fifo", "net": "pooled", "wash": "none", "size": "avg", "offset_days": 0, "lag": 0}


def opts_of(cfg: dict) -> dict:
    o = {k: cfg.get(k, v) for k, v in DEFAULTS.items()}
    if o["lot"] not in LOTS or o["net"] not in NETS or o["wash"] not in WASH or o["size"] not in SIZES:
        raise ValueError(f"bad r2_gap5 options {o}")
    return o


def xcfg(base: dict, **opts) -> dict:
    """An r2_gap5.x config; options at their defaults are left out so a
    config's cache key does not depend on how it was written."""
    c = {"kind": "r2_gap5.x", "base": copy.deepcopy(base)}
    for k, v in opts.items():
        if k not in DEFAULTS:
            raise ValueError(f"unknown option {k!r}")
        if v != DEFAULTS[k]:
            c[k] = v
    opts_of(c)
    return c


def build(cfg: dict):
    o = opts_of(cfg)
    base = cfg["base"]
    k = base["kind"]
    if k == "tax_rotation.ws":
        factory, _, _ = SIGNALS[base["signal"]]
        sig = factory(base.get("params", {}))
        kw = {kk: base[kk] for kk in _TR_KEYS if kk in base}
        return XTRStrategy(sig, size=o["size"], offset_days=o["offset_days"], lag=o["lag"], **kw)
    if k == "combo":
        from ..registry import _combo_build
        s = _combo_build(base)
        if not isinstance(s, TaxManagedCombo):
            raise ValueError("r2_gap5 wraps combo configs with trade_rule=tax_managed only")
        if o["lag"]:
            raise ValueError("combo has no lag option")
        s.__class__ = XTaxManagedCombo
        s.size = o["size"]
        s.offset_days = int(o["offset_days"])
        return s
    if k == "weights":
        from ..registry import _WS_KEYS
        factory, _, _ = SIGNALS[base["signal"]]
        kw = {kk: base[kk] for kk in _WS_KEYS if kk in base}
        return XWeightStrategy(factory(base.get("params", {})), size=o["size"],
                               offset_days=o["offset_days"], lag=o["lag"], **kw)
    raise ValueError(f"r2_gap5 cannot wrap kind {k!r}")


def tickers(cfg: dict) -> list:
    from ..registry import kind_of
    b = cfg["base"]
    return kind_of(b).tickers(b)


def min_start(cfg: dict):
    from ..registry import min_start as _ms
    return _ms(cfg["base"])


class _Guard(Strategy):
    """What sweep.run would build: it refuses to run outside XBacktest (the
    base engine would silently ignore lot / net / wash)."""

    def __init__(self, cfg):
        self.inner = build(cfg)

    def initialize(self, ctx):
        if not isinstance(ctx._engine, XBacktest):
            raise RuntimeError("r2_gap5.x configs run only through research.lab.families.r2_gap5.run")
        self.inner.initialize(ctx)

    def on_day(self, ctx):
        self.inner.on_day(ctx)


register_kind("r2_gap5.x", lambda c: _Guard(c), tickers)


# ==========================================================================
# 7. the runner (sweep.run's twin)
# ==========================================================================
def _snapshot_hash() -> str:
    """Hash of what an r2_gap5 run executes: this module, the lab core, the wrapped
    families, the engine files it subclasses or calls, and the SOURCE of the site
    picker / timer classes the combo configs use (not the whole site modules, which
    other work edits for unrelated presets)."""
    import inspect
    files = [HERE, LAB / "core.py", LAB / "blocks.py", LAB / "registry.py", LAB / "data.py",
             HERE.parent / "lab_extras.py", HERE.parent / "tax_rotation.py",
             HERE.parent / "verify_lev_robust.py"]
    files += [ROOT / "backtester" / f for f in ("composite.py", "engine.py", "market.py", "portfolio.py",
                                                "result.py", "strategy.py", "tax.py")]
    h = hashlib.sha1()
    for f in files:
        try:
            h.update(Path(f).read_bytes())
        except OSError:
            pass
    try:
        from strategies.pickers import PICKERS
        from strategies.timers import TIMERS
        import strategies.pickers as _pk
        h.update(inspect.getsource(PICKERS["momentum"]).encode())
        h.update(inspect.getsource(_pk.total_return).encode())
        h.update(inspect.getsource(TIMERS["buy_hold"]).encode())
    except Exception:  # noqa: BLE001
        h.update(b"no-site-strategies")
    return h.hexdigest()[:12]


CODE_HASH = _snapshot_hash()


def cfg_id(cfg) -> str:
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:14]


def _key(cfg, regime, protocol, comm, slip) -> str:
    payload = json.dumps([cfg, regime, protocol, comm, slip, CODE_HASH], sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:20]


def _path(key):
    return CACHE / key[:2] / f"{key}.json"


def run_starts(cfg, market, regime, protocol, starts, comm, slip, full_stats=True):
    """core.run_starts through XBacktest / XGate."""
    policy = core.policy_for(regime)
    o = opts_of(cfg)
    out = {"starts": {}, "monthly": {}, "full": None}
    for k, s in enumerate(starts):
        first = (k == 0)
        gate = XGate(build(cfg), s, protocol.checkpoints, policy, monthly=first)
        bt = XBacktest(gate, market=market, cash=core.CASH, commission_pct=comm, slippage_pct=slip,
                       tax_policy=policy, lot=o["lot"], net=o["net"], wash=o["wash"],
                       ord_rate=ORD_RATE.get(regime, 0.0))
        res = bt.run()
        if gate.t0 is None:
            continue
        out["starts"][core._ts(s)] = {"t0": core._ts(gate.t0),
                                      "ck": {core._ts(e): [v[0], v[1], core._ts(v[2])]
                                             for e, v in gate.values.items()}}
        if first:
            out["monthly"] = {core._ts(d): [v[0], v[1]] for d, v in gate.months.items()}
            if full_stats:
                fs = core.run_stats(res, gate.t0)
                fs["realized"] = {str(y): [b["st"], b["lt"]] for y, b in sorted(bt.portfolio.realized.items())}
                fs["amend_paid"] = bt.amend_paid
                out["full"] = fs
    return out


def run_one(cfg, regime="CA", protocol="full", comm=None, slip=None, use_cache=True) -> dict:
    from .. import data, registry
    registry.load_families()
    comm = core.COMMISSION if comm is None else comm
    slip = core.SLIPPAGE if slip is None else slip
    key = _key(cfg, regime, protocol, comm, slip)
    path = _path(key)
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    prot = core.PROTOCOLS[protocol]
    t0 = time.time()
    with core.cpu_slot(heavy=False):
        tick = tickers(cfg)
        missing = [t for t in tick if data.path_for(t) is None]
        if missing:
            raise ValueError(f"no data for {missing}")
        mkt = data.market(tick)
        ms = min_start(cfg)
        starts = [s for s in prot.starts if ms is None or s >= ms]
        out = run_starts(cfg, mkt, regime, prot, starts, comm, slip)
    rec = {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol, "comm": comm,
           "slip": slip, "elapsed": time.time() - t0, "code": CODE_HASH, **out}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    return rec


def cached(cfg, regime="CA", protocol="full", comm=None, slip=None):
    comm = core.COMMISSION if comm is None else comm
    slip = core.SLIPPAGE if slip is None else slip
    p = _path(_key(cfg, regime, protocol, comm, slip))
    return json.loads(p.read_text()) if p.exists() else None


def _task(args):
    cfg, regime, protocol, comm, slip = args
    try:
        return run_one(cfg, regime, protocol, comm, slip)
    except Exception as e:  # noqa: BLE001
        return {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol,
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}


def run(cfgs, protocol="full", regimes=("CA",), workers=4, comm=None, slip=None, verbose=True):
    """Run every config x regime through the r2_gap5 engine (cached)."""
    from .. import registry
    registry.load_families()
    jobs, recs = [], []
    for c in cfgs:
        for rg in regimes:
            r = cached(c, rg, protocol, comm, slip)
            if r is not None:
                recs.append(r)
            else:
                jobs.append((c, rg, protocol, comm, slip))
    if verbose:
        print(f"[r2_gap5] {len(recs)} cached, {len(jobs)} to run, workers={workers}", flush=True)
    if not jobs:
        return recs
    t0 = time.time()
    if workers <= 1:
        for j in jobs:
            recs.append(_task(j))
        return recs
    import multiprocessing as mp
    import warnings
    from concurrent.futures import ProcessPoolExecutor, as_completed
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*fork.*")
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as ex:
        futs = [ex.submit(_task, j) for j in jobs]
        for n, f in enumerate(as_completed(futs), 1):
            recs.append(f.result())
            if verbose and (n % max(1, len(jobs) // 20) == 0 or n == len(jobs)):
                el = time.time() - t0
                print(f"[r2_gap5] {n}/{len(jobs)} done, {el:.0f}s elapsed, "
                      f"~{el / n * (len(jobs) - n):.0f}s left", flush=True)
    errs = [r for r in recs if "error" in r]
    if errs and verbose:
        print(f"[r2_gap5] {len(errs)} errors; first: {errs[0]['error']}", flush=True)
    return recs


# ==========================================================================
# 8. one instrumented run (audits)
# ==========================================================================
def run_audit(cfg, start, regime="CA", end="2026-07-01", comm=None, slip=None, market=None):
    """One engine run from `start`, logging every lot the engine sells, every
    sale the strategy planned (with its predicted gain), every order and every
    wash-sale match."""
    from .. import data, registry
    registry.load_families()
    comm = core.COMMISSION if comm is None else comm
    slip = core.SLIPPAGE if slip is None else slip
    o = opts_of(cfg)
    policy = core.policy_for(regime)
    mkt = market or data.market(tickers(cfg))
    strat = build(cfg)
    strat.sales_log = []
    gate = XGate(strat, start, [pd.Timestamp(end)], policy)
    bt = XBacktest(gate, market=mkt, cash=core.CASH, commission_pct=comm, slippage_pct=slip,
                   tax_policy=policy, lot=o["lot"], net=o["net"], wash=o["wash"],
                   ord_rate=ORD_RATE.get(regime, 0.0), audit=True)
    orders = []
    orig = bt.place_order

    def place(t, sh):
        pf = bt.portfolio
        b_sh, b_cash = pf.shares(t), pf.cash
        pv = pf.total_value(bt.current_prices())
        orig(t, sh)
        orders.append((bt._date, t, sh, pf.shares(t) - b_sh, b_cash, pf.cash, pv))
    bt.place_order = place
    res = bt.run()
    return {"res": res, "bt": bt, "strat": strat, "gate": gate, "orders": orders,
            "lots": bt.portfolio.audit, "plans": strat.sales_log, "wash": bt.portfolio.wash_log}

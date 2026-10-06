"""Composable strategies: a Picker chooses *what* to hold, a Timer chooses *when*.

The insight behind this project is that most equity strategies factor into two
independent decisions:

  * **Picker** — given the tradable universe, which names do we even want to
    consider owning this month? (value, momentum, quality, ...)
  * **Timer** — for a name the picker likes, are we long *right now*, or flat?
    (MA crossover, RSI, breakout, ...)

`Combo` wires one Picker to one Timer so any of the picker x timer pairings can
be backtested from the same small set of building blocks. The picker runs on a
rebalance cadence (monthly by default); the timer is evaluated every day so it
can move in and out of the basket between rebalances.

None of these components can see the future: they only ever call `ctx.history`,
which the engine clips to the current day.
"""

from __future__ import annotations

import pandas as pd

from .strategy import Context, Strategy


class Picker:
    """Selects a target basket from the universe on each rebalance.

    Subclasses implement `select`. Return the tickers to consider holding,
    best-first, at most `n` of them. Returning fewer (or none) is fine.
    """

    name: str = "picker"

    def initialize(self, ctx: Context) -> None:
        """Optional one-time setup before the first trading day."""

    def select(self, ctx: Context, universe: list[str], n: int) -> list[str]:
        raise NotImplementedError


class Timer:
    """Decides, day by day, whether we want to be long a specific ticker.

    Subclasses implement `want_long`. `held` is whether we currently own the
    name (so hysteresis timers can use different entry vs. exit thresholds), and
    `entry_price` is the close at which the current position was opened (or None
    if flat) so stop-loss style timers can measure their drawdown.
    """

    name: str = "timer"

    def initialize(self, ctx: Context) -> None:
        """Optional one-time setup before the first trading day."""

    def want_long(
        self, ctx: Context, ticker: str, *, held: bool, entry_price: float | None
    ) -> bool:
        raise NotImplementedError


class Combo(Strategy):
    """Run a Picker and a Timer together as a single tradable Strategy.

    Each rebalance day the picker refreshes the basket of `top_n` candidates.
    Every day the timer is asked, for each basket name, whether to be long; the
    portfolio holds the intersection {basket names the timer wants long},
    equal-weighted. Weights are only rewritten when that set changes, which
    keeps commission churn down.
    """

    def __init__(
        self,
        picker: Picker,
        timer: Timer,
        top_n: int = 20,
        # "D" daily, "W" weekly, "M" monthly, "Q" quarterly, "S" semi-annual,
        # "A" annual. The slow cadences matter for a taxable account: a holding
        # has to survive more than a year for its gain to be taxed long-term.
        rebalance: str = "M",
        menu: list[str] | None = None,
    ):
        self.picker = picker
        self.timer = timer
        self.top_n = top_n
        self.rebalance = rebalance
        # Optional shortlist: the picker ranks only within these names instead
        # of the whole selectable universe. None = no restriction.
        self.menu = list(menu) if menu else None

    def _candidates(self, ctx: Context) -> list[str]:
        if self.menu is None:
            return ctx.universe
        tradable = set(ctx.universe)
        return [t for t in self.menu if t in tradable]

    # ---- lifecycle -------------------------------------------------------
    def initialize(self, ctx: Context) -> None:
        self.picker.initialize(ctx)
        self.timer.initialize(ctx)
        self._basket: list[str] = []
        self._members: set[str] = set()   # names currently targeted long
        self._entry: dict[str, float] = {}  # ticker -> entry close price
        self._last_period: object | None = None

    # ---- rebalance cadence ----------------------------------------------
    def _period_key(self, date: pd.Timestamp):
        if self.rebalance == "D":
            return date.date()
        if self.rebalance == "W":
            iso = date.isocalendar()
            return (iso.year, iso.week)
        if self.rebalance == "Q":
            return (date.year, (date.month - 1) // 3)
        if self.rebalance == "M":
            return (date.year, date.month)
        if self.rebalance == "S":
            return (date.year, (date.month - 1) // 6)
        if self.rebalance == "A":
            return (date.year,)
        raise ValueError(f"unknown rebalance cadence: {self.rebalance!r}")

    # ---- main loop -------------------------------------------------------
    def on_day(self, ctx: Context) -> None:
        key = self._period_key(ctx.date)
        if key != self._last_period:
            self._last_period = key
            self._basket = self.picker.select(ctx, self._candidates(ctx), self.top_n)

        # Ask the timer which basket names we want long today.
        longs: list[str] = []
        for ticker in self._basket:
            if not ctx.can_trade(ticker):
                continue
            held = ctx.shares(ticker) > 0
            if self.timer.want_long(
                ctx, ticker, held=held, entry_price=self._entry.get(ticker)
            ):
                longs.append(ticker)

        long_set = set(longs)

        # Close anything we hold that we no longer want.
        for ticker in list(ctx.positions):
            if ticker not in long_set:
                ctx.liquidate(ticker)
                self._entry.pop(ticker, None)

        # Rewrite weights only when membership changes (limits churn/commission).
        if long_set != self._members:
            weight = 1.0 / len(longs) if longs else 0.0
            for ticker in longs:
                ctx.order_target_percent(ticker, weight)
            self._members = long_set

        # Record an entry price for every newly opened name.
        for ticker in longs:
            if ticker not in self._entry:
                px = ctx.price(ticker)
                if px is not None:
                    self._entry[ticker] = px


class TaxManagedCombo(Combo):
    """A Combo whose *execution* is governed by a realized-gain budget.

    Same picker and same timer as a plain `Combo` — the difference is what the
    portfolio is allowed to sell. For a taxable investor that is the decision
    that actually moves the needle: on this engine an ordinary quarterly
    rotation gives up 3-4 percentage points a year to capital-gains tax, which
    is more than any of these signals earns before tax.

    Each rebalance the target is still "equal-weight the names the picker likes
    and the timer wants long". Getting there is rationed:

      * Selling at a LOSS is always allowed. It banks a deduction, and the
        pooled loss carryforward refills the budget for later gains.
      * Selling at a GAIN is allowed only while the year's *net* realized gain
        stays under `gain_budget` x portfolio value. Gains are taken
        smallest-first, long-term before short-term, and the last sale is
        part-filled so the year lands exactly on the budget.
      * A name sold at a loss is barred from repurchase for `wash_days`, so the
        harvested loss is not disallowed under the wash-sale rule. The cash goes
        to the next name the picker likes instead.

    `gain_budget=0.0` means "never end a trade run with a net realized gain";
    the default 1% of portfolio value a year leaves just enough room to keep
    rotating when no losses are available to harvest, which matters in a long
    bull run where nothing is ever underwater.

    The emergent behaviour is "let winners run, cut losers" — enforced by the
    tax code rather than by conviction. Turnover falls by roughly an order of
    magnitude and the tax drag falls with it.
    """

    def __init__(
        self,
        picker: Picker,
        timer: Timer,
        top_n: int = 20,
        rebalance: str = "M",
        menu: list[str] | None = None,
        gain_budget: float = 0.01,
        wash_days: int = 31,
    ):
        super().__init__(picker, timer, top_n, rebalance, menu)
        self.gain_budget = gain_budget
        self.wash_days = wash_days

    def initialize(self, ctx: Context) -> None:
        super().initialize(ctx)
        self._loss_sale: dict[str, object] = {}

    @staticmethod
    def _gain_if_sold(ctx: Context, ticker: str, shares: float, net_price: float):
        """(gain, all_long_term) that selling `shares` FIFO at `net_price` books."""
        remaining = shares
        gain = 0.0
        all_lt = True
        for date, lot_shares, cost in ctx.lots(ticker):
            if remaining <= 1e-12:
                break
            take = min(remaining, lot_shares)
            gain += (net_price - cost) * take
            if not ctx.is_long_term(date):
                all_lt = False
            remaining -= take
        return gain, all_lt

    def on_day(self, ctx: Context) -> None:
        key = self._period_key(ctx.date)
        if key == self._last_period:
            return
        self._last_period = key
        self._basket = self.picker.select(ctx, self._candidates(ctx), self.top_n)

        longs = [
            t for t in self._basket
            if ctx.can_trade(t)
            and self.timer.want_long(
                ctx, t, held=ctx.shares(t) > 0, entry_price=self._entry.get(t)
            )
        ]

        pv = ctx.portfolio_value
        if pv <= 0:
            return
        weight = 1.0 / len(longs) if longs else 0.0

        # Target share counts from ONE portfolio-value snapshot, so the plan
        # doesn't shift underneath itself as fills come in.
        wanted = set(longs)
        targets: dict[str, float] = {}
        for t in wanted | set(ctx.positions):
            px = ctx.price(t)
            if px is None or px <= 0:
                continue
            targets[t] = (pv * weight / px) if t in wanted else 0.0

        # ---- sells, rationed by the realized-gain budget
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)

        candidates = []
        for t, target in targets.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held:
                continue
            qty = held - target
            px = ctx.price(t)
            # The proceeds the engine will actually book: close, less slippage,
            # less commission. Matching it keeps the budget honest.
            net = px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            candidates.append((gain > 0, not all_lt, gain, t, qty))

        # Losses first (they refill the budget), then gains smallest-first,
        # long-term before short-term. Ticker breaks ties reproducibly.
        candidates.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, _is_short, gain, t, qty in candidates:
            if not is_gain:
                sell = qty
            elif gain <= room + 1e-9:
                sell = qty
            elif room > 1e-9:
                frac = room / gain
                if frac <= 0.02:      # not worth a trade for the last scrap
                    continue
                sell = qty * frac
            else:
                continue
            room -= gain * (sell / qty)
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date
            if ctx.shares(t) <= 0:
                self._entry.pop(t, None)

        # ---- buys, in a fixed order so runs are reproducible
        for t in sorted(longs):
            last = self._loss_sale.get(t)
            if last is not None and (ctx.date - last).days <= self.wash_days:
                continue                      # wash-sale window still open
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

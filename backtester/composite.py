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
        rebalance: str = "M",  # "M" monthly, "W" weekly, "D" daily, "Q" quarterly
    ):
        self.picker = picker
        self.timer = timer
        self.top_n = top_n
        self.rebalance = rebalance

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
        raise ValueError(f"unknown rebalance cadence: {self.rebalance!r}")

    # ---- main loop -------------------------------------------------------
    def on_day(self, ctx: Context) -> None:
        key = self._period_key(ctx.date)
        if key != self._last_period:
            self._last_period = key
            self._basket = self.picker.select(ctx, ctx.universe, self.top_n)

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

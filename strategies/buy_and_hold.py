"""Example algorithm: buy an equal-weight basket on day one and hold it."""

from backtester import Context, Strategy


class BuyAndHold(Strategy):
    def initialize(self, ctx: Context) -> None:
        self._invested = False

    def on_day(self, ctx: Context) -> None:
        if self._invested:
            return
        universe = ctx.universe
        if not universe:
            return
        weight = 1.0 / len(universe)
        for ticker in universe:
            ctx.order_target_percent(ticker, weight)
        self._invested = True


strategy = BuyAndHold()

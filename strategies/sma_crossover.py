"""Example algorithm: SMA crossover, equally weighted across the universe.

For each ticker, go long when its fast moving average is above its slow moving
average, and flat otherwise. Capital is split equally among the tickers that
are currently long.

The runner looks for a module-level `strategy` object (or any Strategy
subclass) — this file exposes both.
"""

from backtester import Context, Strategy


class SmaCrossover(Strategy):
    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow

    def on_day(self, ctx: Context) -> None:
        longs = []
        for ticker in ctx.universe:
            closes = ctx.history(ticker, "Close", window=self.slow)
            if len(closes) < self.slow:
                continue
            fast_ma = closes.iloc[-self.fast:].mean()
            slow_ma = closes.mean()
            if fast_ma > slow_ma:
                longs.append(ticker)

        # Exit anything no longer signalled long.
        for ticker in list(ctx.positions):
            if ticker not in longs:
                ctx.liquidate(ticker)

        # Equal-weight the current longs.
        weight = 1.0 / len(longs) if longs else 0.0
        for ticker in longs:
            ctx.order_target_percent(ticker, weight)


# Default instance the runner will pick up.
strategy = SmaCrossover()

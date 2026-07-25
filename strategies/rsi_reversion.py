"""Mean-reversion algorithm driven by Wilder's RSI.

The idea: an asset that gets oversold tends to snap back. For each ticker we
compute the RSI over a lookback window and go long when it dips below
`oversold`, then exit once it recovers above `exit_level`. Capital is split
equally among the tickers currently held.

The runner looks for a module-level `strategy` object (or any Strategy
subclass) — this file exposes both.
"""

from backtester import Context, Strategy


def wilder_rsi(closes, period: int) -> float | None:
    """RSI of the given close series using Wilder's smoothing.

    Returns None if there isn't enough history yet.
    """
    if len(closes) < period + 1:
        return None
    deltas = closes.diff().dropna()
    gains = deltas.clip(lower=0.0)
    losses = (-deltas).clip(lower=0.0)
    # Wilder's smoothing = an EWMA with alpha = 1/period.
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class RsiReversion(Strategy):
    def __init__(self, period: int = 14, oversold: float = 30.0, exit_level: float = 55.0):
        self.period = period
        self.oversold = oversold
        self.exit_level = exit_level

    def on_day(self, ctx: Context) -> None:
        holds = set(ctx.positions)

        for ticker in ctx.universe:
            closes = ctx.history(ticker, "Close", window=self.period * 5)
            rsi = wilder_rsi(closes, self.period)
            if rsi is None:
                continue
            if ticker in holds:
                # Exit once the bounce plays out.
                if rsi >= self.exit_level:
                    holds.discard(ticker)
            elif rsi <= self.oversold:
                # Enter on oversold.
                holds.add(ticker)

        # Close anything we no longer want to hold.
        for ticker in list(ctx.positions):
            if ticker not in holds:
                ctx.liquidate(ticker)

        # Equal-weight the current holdings.
        weight = 1.0 / len(holds) if holds else 0.0
        for ticker in holds:
            ctx.order_target_percent(ticker, weight)


# Default instance the runner will pick up.
strategy = RsiReversion()

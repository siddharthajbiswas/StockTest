"""Selective RSI mean-reversion: buy the dip on winners, hold only the best.

Two selection layers sit in front of the plain RSI signal:

  1. Trend filter — only consider a stock whose price is above its long-term
     moving average (a confirmed uptrend). Mean-reversion pays off on strong
     names that pull back, not on falling knives.
  2. Top-N cap — among the oversold uptrend names, hold only the `max_positions`
     most oversold (lowest RSI). This concentrates capital in the best setups
     and cuts the churn that commission punishes.

The result is self-selecting: each day it picks its own basket, no hand-picking.

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
    avg_gain = gains.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class RsiReversionSelective(Strategy):
    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        exit_level: float = 55.0,
        trend_window: int = 200,
        max_positions: int = 15,
    ):
        self.period = period
        self.oversold = oversold
        self.exit_level = exit_level
        self.trend_window = trend_window
        self.max_positions = max_positions

    def on_day(self, ctx: Context) -> None:
        held = set(ctx.positions)
        candidates: list[tuple[float, str]] = []  # (rsi, ticker), lowest RSI first

        for ticker in ctx.universe:
            closes = ctx.history(ticker, "Close", window=self.trend_window)
            if len(closes) < self.trend_window:
                continue
            rsi = wilder_rsi(closes, self.period)
            if rsi is None:
                continue
            price = closes.iloc[-1]
            in_uptrend = price > closes.mean()  # above long-term MA

            if ticker in held:
                # Exit once the bounce plays out or the uptrend breaks.
                if rsi >= self.exit_level or not in_uptrend:
                    held.discard(ticker)
            elif in_uptrend and rsi <= self.oversold:
                candidates.append((rsi, ticker))

        # Fill open slots with the most-oversold uptrend names.
        slots = self.max_positions - len(held)
        if slots > 0:
            candidates.sort(key=lambda x: x[0])
            for _, ticker in candidates[:slots]:
                held.add(ticker)

        # Close anything we no longer want to hold.
        for ticker in list(ctx.positions):
            if ticker not in held:
                ctx.liquidate(ticker)

        # Equal-weight the current holdings.
        weight = 1.0 / len(held) if held else 0.0
        for ticker in held:
            ctx.order_target_percent(ticker, weight)


# Default instance the runner will pick up.
strategy = RsiReversionSelective()

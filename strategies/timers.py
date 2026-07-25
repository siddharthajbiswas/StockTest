"""The 10 trading/timing strategies, each as a small `Timer`.

A timer answers one question per name per day: given the price history so far,
do we want to be long *right now*? It never picks which stocks to consider —
that is the Picker's job. Combine any timer with any picker via `Combo`.

Several timers use hysteresis (different entry vs. exit thresholds), which is
why `want_long` is told whether the name is currently `held`.
"""

from __future__ import annotations

from backtester import Context, Timer
from backtester.indicators import (
    bollinger,
    macd,
    realized_vol,
    sma,
    total_return,
    wilder_rsi,
)

# How much history to pull for indicators that warm up an EWMA (MACD). 150 bars
# is far more than enough for a 26-day EMA to converge, and keeps the per-day
# slice small. Timers needing a specific longer window ask for it explicitly.
_MAX_WINDOW = 150


def _closes(ctx: Context, ticker: str, window: int):
    return ctx.history(ticker, "Close", window=window)


class BuyHoldTimer(Timer):
    """Always long. Combined with a picker this just holds the picked basket,
    only changing when the picker rebalances. The timing baseline."""

    name = "buy_hold"

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        return ctx.price(ticker) is not None


class MaCrossTimer(Timer):
    """Classic 50/200 trend filter: long while the fast SMA is above the slow."""

    name = "ma_cross"

    def __init__(self, fast: int = 50, slow: int = 200):
        self.fast = fast
        self.slow = slow

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        closes = _closes(ctx, ticker, self.slow)
        fast_ma = sma(closes, self.fast)
        slow_ma = sma(closes, self.slow)
        if fast_ma is None or slow_ma is None:
            return False
        return fast_ma > slow_ma


class RsiTimer(Timer):
    """RSI mean reversion: enter when oversold, hold until it recovers."""

    name = "rsi"

    def __init__(self, period: int = 14, oversold: float = 30.0, exit_level: float = 70.0):
        self.period = period
        self.oversold = oversold
        self.exit_level = exit_level

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        rsi = wilder_rsi(_closes(ctx, ticker, self.period * 5), self.period)
        if rsi is None:
            return held  # not enough data: don't force a change
        if held:
            return rsi < self.exit_level
        return rsi <= self.oversold


class MacdTimer(Timer):
    """Momentum confirmation: long while the MACD line is above its signal."""

    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        out = macd(_closes(ctx, ticker, _MAX_WINDOW), self.fast, self.slow, self.signal)
        if out is None:
            return False
        macd_line, signal_line = out
        return macd_line > signal_line


class BollingerTimer(Timer):
    """Volatility band reversion: buy at the lower band, sell at the upper."""

    name = "bollinger"

    def __init__(self, window: int = 20, k: float = 2.0):
        self.window = window
        self.k = k

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        bands = bollinger(_closes(ctx, ticker, self.window), self.window, self.k)
        px = ctx.price(ticker)
        if bands is None or px is None:
            return held
        lower, mid, upper = bands
        if held:
            return px < upper       # exit once we ride back up to the top band
        return px <= lower          # enter at the lower band


class MomentumTimer(Timer):
    """Absolute 12-month momentum gate: only long names in a real uptrend."""

    name = "momentum12"

    def __init__(self, lookback: int = 252, threshold: float = 0.0):
        self.lookback = lookback
        self.threshold = threshold

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        ret = total_return(_closes(ctx, ticker, self.lookback + 1), self.lookback)
        if ret is None:
            return False
        return ret > self.threshold


class DualMomentumTimer(Timer):
    """Absolute momentum AND relative strength: long only when the name is up
    over the lookback *and* beating the benchmark over the same window."""

    name = "dual_momentum"

    def __init__(self, lookback: int = 252, benchmark: str = "SPY"):
        self.lookback = lookback
        self.benchmark = benchmark

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        ret = total_return(_closes(ctx, ticker, self.lookback + 1), self.lookback)
        bench = total_return(_closes(ctx, self.benchmark, self.lookback + 1), self.lookback)
        if ret is None or bench is None:
            return False
        return ret > 0.0 and ret > bench


class TurtleBreakoutTimer(Timer):
    """Donchian channel breakout: buy new highs, exit on the lower channel."""

    name = "turtle"

    def __init__(self, entry_window: int = 252, exit_window: int = 100):
        self.entry_window = entry_window
        self.exit_window = exit_window

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        px = ctx.price(ticker)
        if px is None:
            return held
        if held:
            lows = _closes(ctx, ticker, self.exit_window)
            if len(lows) < self.exit_window:
                return True
            return px > float(lows.min())          # stay long above channel low
        highs = _closes(ctx, ticker, self.entry_window)
        if len(highs) < self.entry_window:
            return False
        # Break out on a new high vs. the prior window (exclude today's bar).
        return px >= float(highs.iloc[:-1].max())


class VolReversionTimer(Timer):
    """Volatility mean reversion: buy after a volatility spike, betting the
    panic reverts. Long when short-window realized vol jumps above its own
    longer-run average by a margin; flat once vol calms back down."""

    name = "vol_reversion"

    def __init__(self, short: int = 20, long: int = 100, spike: float = 1.5):
        self.short = short
        self.long = long
        self.spike = spike

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        closes = _closes(ctx, ticker, self.long + 1)
        short_vol = realized_vol(closes, self.short)
        long_vol = realized_vol(closes, self.long)
        if short_vol is None or long_vol is None or long_vol == 0:
            return held
        ratio = short_vol / long_vol
        if held:
            return ratio > 1.0          # stay until vol reverts to its baseline
        return ratio >= self.spike      # enter on a genuine spike


class TrendStopTimer(Timer):
    """Trend following with a hard stop: long while price is above its long MA,
    but bail immediately if the position is down more than `stop` from entry."""

    name = "trend_stop"

    def __init__(self, ma_window: int = 200, stop: float = 0.08):
        self.ma_window = ma_window
        self.stop = stop

    def want_long(self, ctx, ticker, *, held, entry_price) -> bool:
        px = ctx.price(ticker)
        if px is None:
            return held
        if held and entry_price is not None and px <= entry_price * (1.0 - self.stop):
            return False                # stop-loss hit
        ma = sma(_closes(ctx, ticker, self.ma_window), self.ma_window)
        if ma is None:
            return held
        return px > ma


# Registry the grid runner sweeps over. Keys are stable short names.
TIMERS: dict[str, type[Timer]] = {
    "buy_hold": BuyHoldTimer,
    "ma_cross": MaCrossTimer,
    "rsi": RsiTimer,
    "macd": MacdTimer,
    "bollinger": BollingerTimer,
    "momentum12": MomentumTimer,
    "dual_momentum": DualMomentumTimer,
    "turtle": TurtleBreakoutTimer,
    "vol_reversion": VolReversionTimer,
    "trend_stop": TrendStopTimer,
}

"""Small, dependency-light technical indicators computed from a close series.

Every function takes a pandas Series of closes (oldest -> newest, already
clipped to "up to today" by the engine) and returns the latest value, or None
when there isn't enough history yet. Keeping them pure and stateless means both
timers and pickers can share them without worrying about look-ahead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(closes: pd.Series, window: int) -> float | None:
    if len(closes) < window:
        return None
    return float(closes.iloc[-window:].mean())


def wilder_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """Relative Strength Index using Wilder's smoothing."""
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
    return float(100.0 - (100.0 / (1.0 + rs)))


def macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float] | None:
    """Return (macd_line, signal_line) latest values, or None if too short."""
    if len(closes) < slow + signal:
        return None
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


def bollinger(
    closes: pd.Series, window: int = 20, k: float = 2.0
) -> tuple[float, float, float] | None:
    """Return (lower_band, middle, upper_band) latest values, or None."""
    if len(closes) < window:
        return None
    win = closes.iloc[-window:]
    mid = float(win.mean())
    sd = float(win.std(ddof=0))
    return mid - k * sd, mid, mid + k * sd


def total_return(closes: pd.Series, lookback: int) -> float | None:
    """Simple return over the last `lookback` bars: P_t / P_{t-lookback} - 1."""
    if len(closes) < lookback + 1:
        return None
    past = closes.iloc[-lookback - 1]
    if past <= 0:
        return None
    return float(closes.iloc[-1] / past - 1.0)


def realized_vol(closes: pd.Series, window: int = 20) -> float | None:
    """Annualized standard deviation of daily returns over `window` bars."""
    if len(closes) < window + 1:
        return None
    rets = closes.iloc[-window - 1:].pct_change().dropna()
    if rets.empty:
        return None
    return float(rets.std(ddof=0) * np.sqrt(252))

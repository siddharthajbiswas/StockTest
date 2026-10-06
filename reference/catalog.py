"""Strategy metadata for the API — the machine-readable form of STRATEGY_CATALOG.md.

These descriptions and parameter defaults are kept in lockstep with the actual
engine code (`strategies/pickers.py`, `strategies/timers.py`). The `_verify_*`
checks at the bottom assert, at import time, that every id here exists in the
engine registries — so this file can't silently drift out of sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the StockTest project root importable (reference -> project root).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from strategies.pickers import PICKERS, PRICE_ONLY_PICKERS  # noqa: E402
from strategies.timers import TIMERS  # noqa: E402


def _param(name: str, type_: str, default, description: str) -> dict:
    return {"name": name, "type": type_, "default": default, "description": description}


# ----------------------------------------------------------------------------
# Pickers (see STRATEGY_CATALOG.md §1). `look_ahead_risk` is True for the seven
# fundamental pickers, which read a non-point-in-time snapshot.
# ----------------------------------------------------------------------------
PICKER_CATALOG: list[dict] = [
    {
        "id": "momentum",
        "name": "Momentum",
        "data_source": "price",
        "look_ahead_risk": False,
        "description": (
            "Trend-following: ranks candidates by their trailing return and buys "
            "the strongest. In plain terms, back the horses that have been winning "
            "lately. Honest over any period."
        ),
        "params": [
            _param("lookback", "int", 126, "Trailing window in trading days (126 ≈ 6 months)."),
        ],
    },
    {
        "id": "relative_strength",
        "name": "Relative Strength",
        "data_source": "price",
        "look_ahead_risk": False,
        "description": (
            "Momentum with a benchmark filter: keeps only names actually beating "
            "the benchmark over the window, ranked by how much they beat it. In a "
            "broad downturn it can hold few names or none, going defensive."
        ),
        "params": [
            _param("benchmark", "str", "SPY", "Ticker to measure excess return against."),
            _param("lookback", "int", 126, "Trailing window in trading days."),
        ],
    },
    {
        "id": "random",
        "name": "Random (control)",
        "data_source": "price",
        "look_ahead_risk": False,
        "description": (
            "A control baseline that picks names at random, reshuffled each "
            "rebalance. Use it to check whether a real picker actually adds value."
        ),
        "params": [
            _param("seed", "int", 42, "RNG seed for reproducibility."),
            _param("fraction", "float | null", None,
                   "If set (e.g. 0.5), pick that share of the whole universe instead of top_n."),
        ],
    },
    {
        "id": "value_pe",
        "name": "Value (low P/E)",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Traditional value: buys the cheapest stocks by price-to-earnings "
            "(lowest P/E first). Non-positive P/E names are dropped."
        ),
        "params": [],
    },
    {
        "id": "price_to_book",
        "name": "Deep Value (low P/B)",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Deep-value proxy: buys stocks cheapest relative to book value "
            "(lowest price-to-book first)."
        ),
        "params": [],
    },
    {
        "id": "small_cap",
        "name": "Small Cap",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Small-cap tilt: buys the smallest companies by market capitalization, "
            "betting on the small-company return premium."
        ),
        "params": [],
    },
    {
        "id": "quality_roe",
        "name": "Quality (high ROE)",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Quality investing: buys the companies generating the most profit per "
            "dollar of shareholder equity (highest return-on-equity first)."
        ),
        "params": [],
    },
    {
        "id": "growth_revenue",
        "name": "Growth (revenue)",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": "Growth investing: buys the companies whose sales are growing fastest.",
        "params": [],
    },
    {
        "id": "high_dividend",
        "name": "High Dividend",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Income investing: buys the highest dividend-yielding stocks. "
            "Zero-yield names are dropped."
        ),
        "params": [],
    },
    {
        "id": "earnings_surprise",
        "name": "Earnings Surprise",
        "data_source": "fundamentals",
        "look_ahead_risk": True,
        "description": (
            "Post-earnings drift: buys the companies that most recently beat their "
            "earnings estimates by the widest margin."
        ),
        "params": [],
    },
]

# ----------------------------------------------------------------------------
# Timers (see STRATEGY_CATALOG.md §2). All are price-only (no look-ahead).
# ----------------------------------------------------------------------------
TIMER_CATALOG: list[dict] = [
    {
        "id": "buy_hold",
        "name": "Buy & Hold",
        "description": (
            "Always long. Holds the picked basket and only changes it when the "
            "picker rebalances — the timing baseline."
        ),
        "params": [],
    },
    {
        "id": "ma_cross",
        "name": "Moving-Average Cross",
        "description": (
            "The classic golden-cross trend filter: long only while the fast "
            "moving average is above the slow one."
        ),
        "params": [
            _param("fast", "int", 50, "Fast SMA window (days)."),
            _param("slow", "int", 200, "Slow SMA window (days)."),
        ],
    },
    {
        "id": "rsi",
        "name": "RSI Mean Reversion",
        "description": (
            "Enter when the stock is oversold (RSI ≤ oversold) and hold until it "
            "recovers above the exit level. Buys the dip."
        ),
        "params": [
            _param("period", "int", 14, "RSI lookback period."),
            _param("oversold", "float", 30.0, "Entry threshold — buy at/below this RSI."),
            _param("exit_level", "float", 70.0, "Exit threshold — sell once RSI rises above this."),
        ],
    },
    {
        "id": "macd",
        "name": "MACD",
        "description": (
            "Momentum confirmation: long while the MACD line is above its signal "
            "line, i.e. while upward momentum is accelerating."
        ),
        "params": [
            _param("fast", "int", 12, "Fast EMA span."),
            _param("slow", "int", 26, "Slow EMA span."),
            _param("signal", "int", 9, "Signal-line EMA span."),
        ],
    },
    {
        "id": "bollinger",
        "name": "Bollinger Bands",
        "description": (
            "Volatility-band reversion: buy at the lower band, hold until price "
            "climbs back to the upper band, then sell."
        ),
        "params": [
            _param("window", "int", 20, "Moving-average / std window."),
            _param("k", "float", 2.0, "Band width in standard deviations."),
        ],
    },
    {
        "id": "momentum12",
        "name": "12-Month Momentum Gate",
        "description": (
            "Absolute momentum gate: only long a name whose trailing return is "
            "above the threshold. A simple 'is this in an uptrend?' filter."
        ),
        "params": [
            _param("lookback", "int", 252, "Trailing window in trading days (252 ≈ 12 months)."),
            _param("threshold", "float", 0.0, "Minimum trailing return to be long."),
        ],
    },
    {
        "id": "dual_momentum",
        "name": "Dual Momentum",
        "description": (
            "Requires both absolute and relative strength: long only when the name "
            "is up over the lookback AND beating the benchmark over the same window."
        ),
        "params": [
            _param("lookback", "int", 252, "Trailing window in trading days."),
            _param("benchmark", "str", "SPY", "Ticker to compare against."),
        ],
    },
    {
        "id": "turtle",
        "name": "Turtle Breakout",
        "description": (
            "Donchian-channel breakout: buy new highs versus the entry window, "
            "hold until price falls below the exit-window low."
        ),
        "params": [
            _param("entry_window", "int", 252, "Lookback for the breakout high (days)."),
            _param("exit_window", "int", 100, "Lookback for the trailing-stop low (days)."),
        ],
    },
    {
        "id": "vol_reversion",
        "name": "Volatility Reversion",
        "description": (
            "Bets that panic reverts: enter when short-term volatility spikes to "
            "at least `spike`× its longer-run level, hold until volatility calms."
        ),
        "params": [
            _param("short", "int", 20, "Short realized-vol window."),
            _param("long", "int", 100, "Long realized-vol window."),
            _param("spike", "float", 1.5, "Vol-ratio needed to trigger an entry."),
        ],
    },
    {
        "id": "trend_stop",
        "name": "Trend + Hard Stop",
        "description": (
            "Trend-following with a safety stop: long while price is above its long "
            "moving average, but bail immediately if the position drops more than "
            "`stop` below the entry price."
        ),
        "params": [
            _param("ma_window", "int", 200, "Trend moving-average window."),
            _param("stop", "float", 0.08, "Hard stop-loss as a fraction below entry (0.08 = 8%)."),
        ],
    },
    {
        "id": "trend_switch",
        "name": "Trend Switch (2x / bonds)",
        "description": (
            "Meant for picking your own stocks with a leveraged S&P 500 ETF plus a "
            "bond ETF in the basket (e.g. SSO + IEF). Every day at the close it "
            "compares SPY with its 175-day average: once SPY is more than `band` "
            "above it, hold the risk ETF; once it is more than `band` below, switch "
            "to the bond ETF; in between, keep what you hold. Leverage magnifies "
            "losses — a 2x fund falls about twice as far as the index on a bad day."
        ),
        "params": [
            _param("signal", "str", "SPY",
                   "Ticker whose trend decides the switch — SPY, or one of your basket tickers."),
            _param("n", "int", 175, "Moving-average window in trading days (today's close included)."),
            _param("band", "float", 0.03,
                   "Switch to risk above +band, to safe below −band (0.03 = 3%); in between, hold."),
            _param("risk", "str", "SSO",
                   "Comma-separated tickers held while the trend is up (equal weight). Add them to your basket."),
            _param("safe", "str", "IEF",
                   "Comma-separated tickers held while the trend is down (equal weight). Add them to your basket."),
        ],
    },
]

# ----------------------------------------------------------------------------
# Universe modes (see STRATEGY_CATALOG.md §5).
# ----------------------------------------------------------------------------
UNIVERSE_OPTIONS: list[dict] = [
    {
        "id": "all",
        "name": "Full local dataset",
        "description": (
            "Every ticker with price data on disk is selectable each day. This is "
            "effectively today's S&P 500 survivors."
        ),
        "bias_caveat": (
            "Strong survivorship bias: winners are over-represented and delisted "
            "companies are missing entirely, so results are optimistically inflated."
        ),
    },
    {
        "id": "sp500-pit",
        "name": "S&P 500 point-in-time",
        "description": (
            "Restricts each day's selectable names to the stocks that were actually "
            "in the S&P 500 on that date (membership back to 1996). A position can "
            "still be sold after its name leaves the index — only new buys are gated."
        ),
        "bias_caveat": (
            "Corrects membership look-ahead only. It cannot resurrect delisted "
            "companies (free data lacks their prices), so results remain somewhat "
            "optimistic. A full fix needs paid PIT data (CRSP / Sharadar / Norgate)."
        ),
    },
]

# Fast lookups by id.
PICKER_BY_ID = {p["id"]: p for p in PICKER_CATALOG}
TIMER_BY_ID = {t["id"]: t for t in TIMER_CATALOG}
UNIVERSE_BY_ID = {u["id"]: u for u in UNIVERSE_OPTIONS}


def _verify_in_sync() -> None:
    """Fail loudly at import if the catalog and engine registries disagree."""
    cat_pickers = {p["id"] for p in PICKER_CATALOG}
    cat_timers = {t["id"] for t in TIMER_CATALOG}
    if cat_pickers != set(PICKERS):
        raise RuntimeError(
            f"Picker catalog out of sync with engine: {cat_pickers ^ set(PICKERS)}"
        )
    if cat_timers != set(TIMERS):
        raise RuntimeError(
            f"Timer catalog out of sync with engine: {cat_timers ^ set(TIMERS)}"
        )
    # look_ahead_risk must match the engine's price-only set exactly.
    for p in PICKER_CATALOG:
        expected = p["id"] not in PRICE_ONLY_PICKERS
        if p["look_ahead_risk"] != expected:
            raise RuntimeError(f"look_ahead_risk wrong for picker {p['id']!r}")


_verify_in_sync()

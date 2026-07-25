"""The 10 stock-selection strategies, each as a small `Picker`.

A picker answers: given today's tradable universe, which names do we want to
consider owning this rebalance? It never decides *when* to be in the market —
that is the Timer's job. Combine any picker with any timer via `Combo`.

Three pickers work purely from price history and are honest over any period:
    MomentumPicker, RelativeStrengthPicker, RandomPicker.

The other seven read a *current fundamentals snapshot* from data/fundamentals.csv
(produced by fetch_fundamentals.py). Because that snapshot is not point-in-time,
those pickers are only trustworthy over a recent window — see the warning in
fetch_fundamentals.py. They raise a clear error if the snapshot is missing.
"""

from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backtester import Context, Picker
from backtester.indicators import total_return

FUNDAMENTALS_PATH = Path(__file__).resolve().parent.parent / "data" / "fundamentals.csv"


# ======================================================================
# Price-only pickers (valid over any period)
# ======================================================================


class MomentumPicker(Picker):
    """Trend following: buy the strongest trailing-return names (default 6mo)."""

    name = "momentum"

    def __init__(self, lookback: int = 126):
        self.lookback = lookback

    def select(self, ctx: Context, universe: list[str], n: int) -> list[str]:
        scored: list[tuple[float, str]] = []
        for t in universe:
            r = total_return(ctx.history(t, "Close", self.lookback + 1), self.lookback)
            if r is not None:
                scored.append((r, t))
        scored.sort(reverse=True)              # highest momentum first
        return [t for _, t in scored[:n]]


class RelativeStrengthPicker(Picker):
    """Relative momentum with a benchmark filter: hold only names actually
    beating the benchmark (default SPY), ranked by excess return.

    The filter is what makes this genuinely different from absolute momentum:
    simply ranking by (return - benchmark) is order-identical to ranking by
    return, since the benchmark is a constant subtracted from every name. By
    instead *dropping* names that don't beat SPY, this picker holds fewer names
    (even nothing) in a broad downturn, going defensive when momentum would
    still buy the 'least bad' losers."""

    name = "relative_strength"

    def __init__(self, benchmark: str = "SPY", lookback: int = 126):
        self.benchmark = benchmark
        self.lookback = lookback

    def select(self, ctx: Context, universe: list[str], n: int) -> list[str]:
        bench = total_return(
            ctx.history(self.benchmark, "Close", self.lookback + 1), self.lookback
        )
        if bench is None:
            return []
        scored: list[tuple[float, str]] = []
        for t in universe:
            if t == self.benchmark:
                continue
            r = total_return(ctx.history(t, "Close", self.lookback + 1), self.lookback)
            if r is not None and r > bench:      # only names beating the benchmark
                scored.append((r - bench, t))
        scored.sort(reverse=True)
        return [t for _, t in scored[:n]]


class RandomPicker(Picker):
    """Control baseline: pick names at random, reshuffled each rebalance.

    By default picks `n` names (a fair control against the ranked pickers). Set
    `fraction` to instead pick that share of the universe (e.g. 0.5 = 'half the
    market at random', the classic 50% control)."""

    name = "random"

    def __init__(self, seed: int = 42, fraction: float | None = None):
        self.fraction = fraction
        self._rng = random.Random(seed)

    def select(self, ctx: Context, universe: list[str], n: int) -> list[str]:
        if not universe:
            return []
        k = round(len(universe) * self.fraction) if self.fraction else n
        k = max(1, min(k, len(universe)))
        return self._rng.sample(list(universe), k)


# ======================================================================
# Fundamental snapshot pickers (recent-window only — see module docstring)
# ======================================================================


@lru_cache(maxsize=1)
def _load_fundamentals() -> pd.DataFrame:
    if not FUNDAMENTALS_PATH.exists():
        raise FileNotFoundError(
            f"{FUNDAMENTALS_PATH} not found. Fundamental pickers need a snapshot — "
            "run:  python fetch_fundamentals.py  (see its header for the "
            "point-in-time-bias caveat)."
        )
    return pd.read_csv(FUNDAMENTALS_PATH, index_col="ticker")


class FundamentalPicker(Picker):
    """Rank the universe by one fundamental column and take the top `n`.

    `ascending=True` means small-is-good (P/E, P/B, market cap); `False` means
    large-is-good (ROE, yield, growth, surprise). `positive_only` drops rows
    whose value is <= 0 before ranking (e.g. a negative P/E is not 'cheap')."""

    field: str = ""
    ascending: bool = True
    positive_only: bool = True

    def initialize(self, ctx: Context) -> None:
        _load_fundamentals()  # fail fast with a helpful message if missing

    def select(self, ctx: Context, universe: list[str], n: int) -> list[str]:
        fund = _load_fundamentals()
        if self.field not in fund.columns:
            return []
        col = fund[self.field].dropna()
        col = col[col.index.isin(universe)]
        if self.positive_only:
            col = col[col > 0]
        if col.empty:
            return []
        ranked = col.sort_values(ascending=self.ascending)
        return list(ranked.index[:n])


class ValuePicker(FundamentalPicker):
    """Traditional value: lowest trailing P/E."""

    name = "value_pe"
    field = "trailingPE"
    ascending = True


class PriceToBookPicker(FundamentalPicker):
    """Deep-value proxy: lowest price-to-book."""

    name = "price_to_book"
    field = "priceToBook"
    ascending = True


class SmallCapPicker(FundamentalPicker):
    """Small-cap tilt: lowest market capitalization."""

    name = "small_cap"
    field = "marketCap"
    ascending = True


class QualityPicker(FundamentalPicker):
    """Quality: highest return on equity (profitable + efficient)."""

    name = "quality_roe"
    field = "returnOnEquity"
    ascending = False
    positive_only = False   # a name can be quality-ranked even below some peers


class GrowthPicker(FundamentalPicker):
    """Growth: fastest revenue growth."""

    name = "growth_revenue"
    field = "revenueGrowth"
    ascending = False
    positive_only = False


class DividendPicker(FundamentalPicker):
    """Income: highest dividend yield."""

    name = "high_dividend"
    field = "dividendYield"
    ascending = False
    positive_only = True    # no yield = not an income name


class EarningsSurprisePicker(FundamentalPicker):
    """Post-earnings drift: biggest recent positive earnings surprise."""

    name = "earnings_surprise"
    field = "earningsSurprisePct"
    ascending = False
    positive_only = False


# Registry the grid runner sweeps over. Keys are stable short names.
# `needs_fundamentals` flags the ones gated on the snapshot file.
PICKERS: dict[str, type[Picker]] = {
    "momentum": MomentumPicker,
    "relative_strength": RelativeStrengthPicker,
    "random": RandomPicker,
    "value_pe": ValuePicker,
    "price_to_book": PriceToBookPicker,
    "small_cap": SmallCapPicker,
    "quality_roe": QualityPicker,
    "growth_revenue": GrowthPicker,
    "high_dividend": DividendPicker,
    "earnings_surprise": EarningsSurprisePicker,
}

PRICE_ONLY_PICKERS = {"momentum", "relative_strength", "random"}

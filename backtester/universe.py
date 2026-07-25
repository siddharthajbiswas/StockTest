"""Point-in-time index membership, for survivorship-aware backtests.

Loads the historical S&P 500 constituents table (date -> the exact set of
tickers in the index on that date) and turns it into a per-trading-day list of
member sets aligned to a backtest calendar. Feeding that to `MarketData`
restricts what a strategy is allowed to *select* each day to the names that were
genuinely in the index then — so a picker can't buy a stock before it joined
(or after it left) just because it happens to be in today's index.

Important honesty note: this only corrects *membership look-ahead*. It does not
resurrect companies whose price data no longer exists (bankruptcies etc.), which
free data sources don't provide. A full survivorship correction needs a paid
point-in-time dataset (CRSP / Sharadar / Norgate) with delisted prices.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONSTITUENTS_PATH = DATA_DIR / "sp500_constituents.csv"


def _normalize(ticker: str) -> str:
    """Match the constituents file's symbols to our Yahoo-style CSV names.

    Yahoo writes class shares with a hyphen (BRK-B, BF-B) where the index table
    uses a dot (BRK.B, BF.B).
    """
    return ticker.strip().replace(".", "-")


def load_membership(path: Path | str = CONSTITUENTS_PATH) -> pd.Series:
    """Return a Series indexed by snapshot date, values = frozenset of tickers."""
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    out = {
        row.date: frozenset(_normalize(t) for t in str(row.tickers).split(",") if t)
        for row in df.itertuples()
    }
    return pd.Series(out).sort_index()


def members_by_calendar(
    membership: pd.Series,
    calendar: pd.DatetimeIndex,
    restrict_to: set[str] | None = None,
) -> list[frozenset]:
    """Align membership to `calendar`: for each day, the members as of that day.

    Uses the most recent snapshot on or before each calendar date (an as-of
    join). `restrict_to` intersects each set with the tickers you actually have
    price data for, so the returned sets only contain tradable names.
    """
    snap_dates = membership.index
    # For each calendar day, index of the latest snapshot <= that day.
    pos = snap_dates.searchsorted(calendar, side="right") - 1
    out: list[frozenset] = []
    for p in pos:
        if p < 0:
            out.append(frozenset())
            continue
        members = membership.iloc[p]
        if restrict_to is not None:
            members = frozenset(members & restrict_to)
        out.append(members)
    return out

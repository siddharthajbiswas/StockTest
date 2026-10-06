"""Price loading for the lab: the site's data/ first, research extras second.

* Site tickers (data/*.csv) load exactly as backtester.data.load_prices loads
  them, so a strategy that only uses site tickers sees the site's numbers.
* Research-only tickers (research/lab/data/*.csv, from fetch_extra.py) fill in
  everything else. Mutual funds and indices report zero volume, which the
  engine reads as "untradable"; their Volume column is dropped so the engine
  treats volume as unknown (tradable whenever there is a close).
* Index symbols are stored with '^' replaced by 'IDX_' (e.g. ^VIX -> IDX_VIX).
  Use the caret form everywhere in code; this module maps it.

Every frame is clipped at DATA_END (2026-07-01, the end of the site's data) so
research results line up with what the site can show.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from backtester import MarketData

ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "data"
EXTRA_DIR = Path(__file__).resolve().parent / "data"
DATA_END = "2026-07-01"
FIELDS = ["Open", "High", "Low", "Close", "Volume"]
NON_PRICE = {"fundamentals", "sp500_constituents", "company_names"}


def _fname(ticker: str) -> str:
    return ticker.replace("^", "IDX_")


def path_for(ticker: str) -> Path | None:
    p = SITE_DIR / f"{ticker}.csv"
    if p.exists():
        return p
    p = EXTRA_DIR / f"{_fname(ticker)}.csv"
    if p.exists():
        return p
    return None


def is_site_ticker(ticker: str) -> bool:
    return (SITE_DIR / f"{ticker}.csv").exists()


def site_tickers() -> list[str]:
    return sorted(p.stem for p in SITE_DIR.glob("*.csv") if p.stem not in NON_PRICE)


def extra_tickers() -> list[str]:
    return sorted(p.stem.replace("IDX_", "^") for p in EXTRA_DIR.glob("*.csv"))


@lru_cache(maxsize=None)
def _raw(ticker: str) -> pd.DataFrame:
    p = path_for(ticker)
    if p is None:
        raise FileNotFoundError(f"no price file for {ticker!r} in data/ or research/lab/data/")
    df = pd.read_csv(p, parse_dates=["Date"], index_col="Date")
    df = df[[c for c in FIELDS if c in df.columns]].sort_index()
    if p.parent == EXTRA_DIR and "Volume" in df.columns:
        vol = df["Volume"].fillna(0)
        # Funds and indices: no exchange volume at all -> volume "unknown".
        if ticker.startswith("^") or (vol > 0).mean() < 0.5:
            df = df.drop(columns=["Volume"])
    return df


def frame(ticker: str, start: str | None = None, end: str | None = DATA_END) -> pd.DataFrame:
    df = _raw(ticker)
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]
    return df


def first_date(ticker: str) -> pd.Timestamp:
    return _raw(ticker).index[0]


def prices(tickers, start: str | None = None, end: str | None = DATA_END) -> dict[str, pd.DataFrame]:
    out = {}
    for t in dict.fromkeys(tickers):
        df = frame(t, start, end)
        if not df.empty:
            out[t] = df
    return out


_MARKETS: dict[tuple, MarketData] = {}


def market(tickers, end: str = DATA_END, universe: str = "menu") -> MarketData:
    """A cached MarketData.

    universe="menu": exactly `tickers` (callers add SPY themselves when the
    strategy or the site would). This mirrors the site's menu/manual markets,
    which contain the menu plus SPY and nothing else.
    universe="all" / "sp500-pit": every site ticker (stocks + ETFs), optionally
    filtered to point-in-time S&P 500 members -- the site's strategy-mode market.
    """
    # Index series (^VIX, ^IRX, ...) are signals, not instruments: keep them out
    # of the tradable market (an index's odd holiday bar would otherwise add a
    # calendar day on which nothing else trades). Signals read them through
    # blocks.asof(), lagged one day.
    tickers = [t for t in tickers if not t.startswith("^")]
    key = (tuple(sorted(set(tickers))) if universe == "menu" else (), end, universe)
    m = _MARKETS.get(key)
    if m is None:
        if universe == "menu":
            m = MarketData(prices(sorted(set(tickers)), end=end))
        else:
            from grid_combos import build_market
            px = prices(site_tickers(), end=end)
            m = build_market(px, universe)
        _MARKETS[key] = m
    return m


def clear_markets() -> None:
    _MARKETS.clear()

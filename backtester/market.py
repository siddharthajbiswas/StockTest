"""Precomputed, strategy-independent market structure.

Building this is the expensive part of a backtest — laying out every ticker's
prices so the engine can advance one day at a time without ever doing a pandas
label lookup. Because none of it depends on the strategy, you build it *once*
and reuse it across many `Backtest` runs (e.g. a 100-combo grid), which is the
single biggest speedup for parameter sweeps.

What it precomputes:
  * `calendar`            — the union trading calendar (sorted DatetimeIndex).
  * `today_tradable[i]`   — {ticker: close} for names actually tradable on day i
                            (a real bar, non-NaN close, and volume>0 or unknown).
  * `mark_values`         — a dense (days x tickers) forward-filled close matrix
                            used to mark open positions, so a holding in a name
                            that didn't trade today is valued at its last close
                            instead of dropping to $0.
  * per-ticker Series + a numpy date index for `history()` slicing via
    `searchsorted` (O(log n)) instead of a full boolean mask.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import trading_calendar


class MarketData:
    def __init__(
        self,
        prices: dict[str, pd.DataFrame],
        members_by_day: list[frozenset] | None = None,
    ):
        """`members_by_day`, if given, is a per-calendar-day set of index
        members (aligned to this market's calendar). It restricts what a
        strategy may *select* each day (ctx.universe) to point-in-time members,
        without restricting what it may transact — so a position can still be
        sold after its name leaves the index."""
        if not prices:
            raise ValueError("MarketData needs at least one ticker.")
        self.prices = prices
        self.tickers = list(prices)
        self.calendar = trading_calendar(prices)
        self.cal_values = self.calendar.values  # np.datetime64[ns]
        self.n = len(self.calendar)

        # Per-ticker column Series (shared, zero-copy) and a numpy date index.
        self._series: dict[str, dict[str, pd.Series]] = {}
        self._index: dict[str, np.ndarray] = {}
        for t, df in prices.items():
            self._series[t] = {f: df[f] for f in df.columns}
            self._index[t] = df.index.values

        # Dense forward-filled close matrix for marking held positions.
        close_raw = pd.DataFrame(
            {t: s["Close"] for t, s in self._series.items()}
        ).reindex(self.calendar)
        self._cols = list(close_raw.columns)
        self._col = {t: j for j, t in enumerate(self._cols)}
        self.mark_values = close_raw.ffill().to_numpy()

        # Volume matrix (NaN where a ticker has no bar that day / no volume col).
        if any("Volume" in s for s in self._series.values()):
            vol_raw = pd.DataFrame(
                {t: s["Volume"] for t, s in self._series.items() if "Volume" in s}
            ).reindex(self.calendar).reindex(columns=self._cols)
        else:
            vol_raw = pd.DataFrame(np.nan, index=self.calendar, columns=self._cols)

        # Tradable if there's a real bar today (close not NaN) and volume is
        # either unknown (NaN) or strictly positive — a zero-volume bar is a
        # back-filled phantom we could not actually trade.
        cr = close_raw.to_numpy()
        vr = vol_raw.to_numpy()
        tradable = ~np.isnan(cr) & (np.isnan(vr) | (vr > 0))

        # Precompute the tradable snapshot for each day once.
        self.today_tradable: list[dict[str, float]] = []
        cols = self._cols
        for i in range(self.n):
            js = np.nonzero(tradable[i])[0]
            self.today_tradable.append({cols[j]: float(cr[i, j]) for j in js})

        # The selectable universe: tradable names filtered to point-in-time
        # index members (if membership was supplied), else everything tradable.
        if members_by_day is None:
            self.today_selectable: list[list[str]] = [
                list(d) for d in self.today_tradable
            ]
        else:
            if len(members_by_day) != self.n:
                raise ValueError("members_by_day must align to the market calendar.")
            self.today_selectable = [
                [t for t in d if t in members_by_day[i]]
                for i, d in enumerate(self.today_tradable)
            ]

    # ---- accessors used by the engine -----------------------------------
    def col(self, ticker: str) -> int | None:
        return self._col.get(ticker)

    def series(self, ticker: str, field: str) -> pd.Series | None:
        cols = self._series.get(ticker)
        return None if cols is None else cols.get(field)

    def rows_upto(self, ticker: str, dv: np.datetime64) -> int:
        """How many of `ticker`'s bars fall on or before date `dv`."""
        iv = self._index.get(ticker)
        if iv is None:
            return 0
        return int(iv.searchsorted(dv, side="right"))

    def trades_on(self, ticker: str, dv: np.datetime64) -> int | None:
        """Row position of `ticker`'s bar dated exactly `dv`, or None."""
        iv = self._index.get(ticker)
        if iv is None:
            return None
        pos = int(iv.searchsorted(dv, side="right")) - 1
        if pos < 0 or iv[pos] != dv:
            return None
        return pos

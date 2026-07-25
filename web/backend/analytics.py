"""Derived analytics over an engine Result — round-trip trades and curve helpers.

The engine's blotter records individual BUY/SELL fills. Users want *round trips*
(a buy matched to the sell that closed it, with P&L). We reconstruct those here
via FIFO matching, mirroring the engine's own FIFO tax-lot accounting so the
per-trade P&L is consistent with how gains are realized.
"""

from __future__ import annotations

from collections import defaultdict, deque

import pandas as pd


def round_trips(trades: pd.DataFrame) -> tuple[list[dict], float | None]:
    """Pair BUY fills to SELL fills FIFO per ticker; return (round_trips, win_rate).

    Each round trip: ticker, entry/exit date, shares, entry/exit price, pnl
    (net of both legs' commission), return_pct, holding_days. Open positions
    still held at the end are not round trips and don't count toward win rate.
    """
    if trades is None or trades.empty:
        return [], None

    open_lots: dict[str, deque] = defaultdict(deque)
    out: list[dict] = []

    for date, t in trades.iterrows():
        ticker = str(t["ticker"])
        shares = float(t["shares"])
        price = float(t["price"])
        commission = float(t["commission"])
        cps = commission / shares if shares else 0.0  # commission per share

        if str(t["side"]) == "BUY":
            open_lots[ticker].append(
                {"date": date, "shares": shares, "price": price, "cps": cps}
            )
            continue

        # SELL: consume open buy lots FIFO.
        remaining = shares
        lots = open_lots[ticker]
        while remaining > 1e-9 and lots:
            lot = lots[0]
            take = min(remaining, lot["shares"])
            buy_comm = lot["cps"] * take
            sell_comm = cps * take
            pnl = (price - lot["price"]) * take - buy_comm - sell_comm
            cost = lot["price"] * take + buy_comm
            out.append(
                {
                    "ticker": ticker,
                    "entry_date": lot["date"].date().isoformat(),
                    "exit_date": date.date().isoformat(),
                    "shares": round(take, 4),
                    "entry_price": round(lot["price"], 4),
                    "exit_price": round(price, 4),
                    "pnl": round(pnl, 2),
                    "return_pct": (pnl / cost) if cost > 0 else 0.0,
                    "holding_days": (date - lot["date"]).days,
                }
            )
            lot["shares"] -= take
            remaining -= take
            if lot["shares"] <= 1e-9:
                lots.popleft()

    wins = sum(1 for r in out if r["pnl"] > 0)
    win_rate = wins / len(out) if out else None
    return out, win_rate


def totals(res) -> list[float]:
    """The daily total-equity curve as a plain list."""
    return [float(v) for v in res.equity["total"]]


def align_totals(res, dates: pd.DatetimeIndex) -> list[float]:
    """Reindex a Result's equity curve onto `dates` (forward-filled), for
    overlaying a benchmark on a different-but-overlapping calendar."""
    s = res.equity["total"]
    aligned = s.reindex(dates).ffill().bfill()
    return [float(v) for v in aligned]

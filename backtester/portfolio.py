"""Cash / positions / trade-blotter accounting."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .tax import Lot, TaxPolicy


@dataclass
class Trade:
    date: pd.Timestamp
    ticker: str
    side: str          # "BUY" or "SELL"
    shares: float      # always positive
    price: float
    value: float       # shares * price (cash moved, excl. commission)
    commission: float

    def as_dict(self) -> dict:
        return {
            "date": self.date,
            "ticker": self.ticker,
            "side": self.side,
            "shares": self.shares,
            "price": self.price,
            "value": self.value,
            "commission": self.commission,
        }


@dataclass
class Portfolio:
    cash: float
    commission_per_share: float = 0.0
    commission_pct: float = 0.0            # fraction of trade value, e.g. 0.001 = 10bps
    positions: dict[str, float] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    # Tax lots per ticker (FIFO) and realized gains bucketed by calendar year.
    lots: dict[str, list[Lot]] = field(default_factory=dict)
    realized: dict[int, dict[str, float]] = field(default_factory=dict)

    def shares(self, ticker: str) -> float:
        return self.positions.get(ticker, 0.0)

    # ---- tax-lot accounting ---------------------------------------------
    def _record_realized(self, year: int, gain: float, long_term: bool) -> None:
        bucket = self.realized.setdefault(year, {"st": 0.0, "lt": 0.0})
        bucket["lt" if long_term else "st"] += gain

    def _open_lot(self, date, ticker: str, shares: float, cost_per_share: float) -> None:
        self.lots.setdefault(ticker, []).append(Lot(date, shares, cost_per_share))

    def _close_lots(
        self, date, ticker: str, shares: float, proceeds_per_share: float,
        policy: TaxPolicy,
    ) -> None:
        """Consume `shares` from `ticker`'s lots FIFO, realizing gains."""
        remaining = shares
        lots = self.lots.get(ticker, [])
        while remaining > 1e-12 and lots:
            lot = lots[0]
            take = min(remaining, lot.shares)
            gain = (proceeds_per_share - lot.cost_per_share) * take
            holding_days = (date - lot.date).days
            self._record_realized(date.year, gain, policy.is_long_term(holding_days))
            lot.shares -= take
            remaining -= take
            if lot.shares <= 1e-12:
                lots.pop(0)

    def unrealized_gains(self, date, prices: dict[str, float], policy: TaxPolicy) -> tuple[float, float]:
        """(short_term, long_term) unrealized gain across open lots, marked at
        `prices` as of `date` — used for the terminal liquidation tax."""
        st = lt = 0.0
        for ticker, lots in self.lots.items():
            px = prices.get(ticker)
            if px is None:
                continue
            for lot in lots:
                gain = (px - lot.cost_per_share) * lot.shares
                if policy.is_long_term((date - lot.date).days):
                    lt += gain
                else:
                    st += gain
        return st, lt

    def holdings_value(self, prices: dict[str, float]) -> float:
        """Mark-to-market value of open positions at the given close prices."""
        total = 0.0
        for ticker, qty in self.positions.items():
            px = prices.get(ticker)
            if px is not None:
                total += qty * px
        return total

    def total_value(self, prices: dict[str, float]) -> float:
        return self.cash + self.holdings_value(prices)

    def execute(
        self, date: pd.Timestamp, ticker: str, delta_shares: float, price: float,
        policy: TaxPolicy | None = None,
    ) -> Trade | None:
        """Fill an order of `delta_shares` (buy>0 / sell<0) at `price`.

        `price` already includes slippage (applied by the engine). Commission is
        folded into the tax lots so realized gains are net of all trading costs.
        Returns the recorded Trade, or None if the order was a no-op.
        """
        if delta_shares == 0:
            return None
        side = "BUY" if delta_shares > 0 else "SELL"
        qty = abs(delta_shares)
        value = qty * price
        commission = qty * self.commission_per_share + value * self.commission_pct
        per_share_commission = commission / qty if qty else 0.0

        # Cash: pay for buys (value + commission), receive for sells (value - commission).
        self.cash += -value - commission if delta_shares > 0 else value - commission
        self.positions[ticker] = self.shares(ticker) + delta_shares
        if abs(self.positions[ticker]) < 1e-9:
            self.positions.pop(ticker, None)

        # Tax lots: buys add cost (incl. commission); sells realize gains against
        # proceeds (net of commission), FIFO. Only tracked when taxes are on.
        if policy is not None:
            if delta_shares > 0:
                self._open_lot(date, ticker, qty, price + per_share_commission)
            else:
                self._close_lots(date, ticker, qty, price - per_share_commission, policy)

        trade = Trade(date, ticker, side, qty, price, value, commission)
        self.trades.append(trade)
        return trade

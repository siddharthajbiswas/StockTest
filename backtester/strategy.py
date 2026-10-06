"""The API your algorithm talks to.

Write a strategy by subclassing `Strategy` and implementing `on_day(ctx)`.
Everything the algorithm is allowed to see or do goes through the `Context`
(`ctx`) it receives each trading day. The context only exposes data up to and
including the current day, so strategies cannot peek at the future.

Orders placed during `on_day` fill immediately at the current day's close.
"""

from __future__ import annotations

import pandas as pd


class Context:
    """Per-day view of the world handed to the strategy.

    Bound by the engine to the current date; the engine refreshes it each step.
    """

    def __init__(self, engine):
        self._engine = engine
        self.date: pd.Timestamp | None = None

    # ---- portfolio state -------------------------------------------------
    @property
    def cash(self) -> float:
        return self._engine.portfolio.cash

    @property
    def positions(self) -> dict[str, float]:
        """{ticker: shares} for currently open positions (read-only copy)."""
        return dict(self._engine.portfolio.positions)

    @property
    def portfolio_value(self) -> float:
        return self._engine.portfolio.total_value(self._engine.current_prices())

    def shares(self, ticker: str) -> float:
        return self._engine.portfolio.shares(ticker)

    # ---- market data (no look-ahead) ------------------------------------
    @property
    def universe(self) -> list[str]:
        """Tickers that have a bar on the current day."""
        return self._engine.tradable_today()

    def can_trade(self, ticker: str) -> bool:
        return ticker in self._engine.today_prices

    def price(self, ticker: str, field: str = "Close") -> float | None:
        """Today's value of `field` for `ticker`, or None if it doesn't trade today."""
        return self._engine.field_today(ticker, field)

    def history(self, ticker: str, field: str = "Close", window: int | None = None) -> pd.Series:
        """Series of `field` for `ticker` up to and including today.

        `window` keeps only the last N observations. Empty if the ticker is
        unknown or has no data yet.
        """
        return self._engine.history(ticker, field, window)

    # ---- tax-lot state (only populated when a TaxPolicy is active) -------
    def lots(self, ticker: str) -> list[tuple]:
        """Open tax lots for `ticker` as (purchase_date, shares, cost_per_share).

        Cost per share already includes commission and slippage. Empty when the
        backtest is running without a TaxPolicy (no lots are tracked then).
        A strategy uses this to see what a sale would *realize* before placing
        it — which is what tax-aware trading rules are built on.
        """
        return [
            (lot.date, lot.shares, lot.cost_per_share)
            for lot in self._engine.portfolio.lots.get(ticker, [])
        ]

    def realized_this_year(self) -> tuple[float, float]:
        """(short_term, long_term) net realized gains booked so far this year."""
        bucket = self._engine.portfolio.realized.get(self.date.year)
        if bucket is None:
            return 0.0, 0.0
        return bucket["st"], bucket["lt"]

    @property
    def slippage_pct(self) -> float:
        """Half-spread the engine applies to fills (buys up, sells down)."""
        return self._engine.slippage_pct

    @property
    def commission_pct(self) -> float:
        """Commission as a fraction of trade value."""
        return self._engine.portfolio.commission_pct

    def is_long_term(self, purchase_date) -> bool:
        """Would a sale today of a lot bought on `purchase_date` be long-term?"""
        policy = self._engine.tax_policy
        if policy is None:
            return True
        return policy.is_long_term((self.date - purchase_date).days)

    # ---- orders (fill at today's close) ---------------------------------
    def order(self, ticker: str, shares: float) -> None:
        """Buy (shares>0) or sell (shares<0) an absolute number of shares."""
        self._engine.place_order(ticker, shares)

    def order_target_shares(self, ticker: str, target: float) -> None:
        """Move the position to exactly `target` shares."""
        self._engine.place_order(ticker, target - self.shares(ticker))

    def order_target_percent(self, ticker: str, pct: float) -> None:
        """Rebalance so `ticker` is `pct` (0..1) of current portfolio value."""
        px = self.price(ticker)
        if px is None or px <= 0:
            return
        target_value = self.portfolio_value * pct
        self.order_target_shares(ticker, target_value / px)

    def liquidate(self, ticker: str) -> None:
        """Close the position in `ticker`."""
        self.order_target_shares(ticker, 0)

    def log(self, *args) -> None:
        if self._engine.verbose:
            print(f"[{self.date.date()}]", *args)


class Strategy:
    """Base class for algorithms. Override the two hooks you need."""

    def initialize(self, ctx: Context) -> None:
        """Called once before the first trading day. Optional."""

    def on_day(self, ctx: Context) -> None:
        """Called once per trading day. Put your trading logic here."""
        raise NotImplementedError("Strategy must implement on_day(ctx).")

"""The day-by-day simulation loop."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .market import MarketData
from .portfolio import Portfolio
from .result import Result
from .strategy import Context, Strategy
from .tax import TaxPolicy, compute_year_tax


class Backtest:
    """Runs a Strategy over a set of price frames, one trading day at a time.

    Pass either `prices` ({ticker: DataFrame[Open,High,Low,Close,Volume]}) or a
    prebuilt `market` (backtester.market.MarketData). Reuse a single MarketData
    across many Backtests — e.g. a parameter sweep — to skip re-laying-out the
    data for every run, which is the dominant cost of a backtest.
    """

    def __init__(
        self,
        strategy: Strategy,
        prices: dict[str, pd.DataFrame] | None = None,
        cash: float = 100_000.0,
        commission_per_share: float = 0.0,
        commission_pct: float = 0.0,
        min_order_value: float = 1.0,
        verbose: bool = False,
        market: MarketData | None = None,
        slippage_pct: float = 0.0,
        tax_policy: TaxPolicy | None = None,
    ):
        if market is None:
            if prices is None:
                raise ValueError("Backtest needs either `prices` or `market`.")
            market = MarketData(prices)
        self.market = market
        self.strategy = strategy
        self.min_order_value = min_order_value
        self.slippage_pct = slippage_pct
        self.tax_policy = tax_policy
        self.calendar = market.calendar
        self.portfolio = Portfolio(
            cash=cash,
            commission_per_share=commission_per_share,
            commission_pct=commission_pct,
        )
        self.verbose = verbose
        self.starting_cash = cash

        self.ctx = Context(self)
        # State for the day currently being processed.
        self._i: int = -1
        self._date: pd.Timestamp | None = None
        self._dv: np.datetime64 | None = None
        self.today_prices: dict[str, float] = {}   # ticker -> today's Close (tradable)

    # ---- data access used by Context ------------------------------------
    def current_prices(self) -> dict[str, float]:
        # Mark-to-market open positions at their last known close (forward
        # filled), so holdings in names that didn't trade today aren't $0.
        mark = self.market.mark_values
        i = self._i
        out: dict[str, float] = {}
        for t in self.portfolio.positions:
            j = self.market.col(t)
            if j is not None:
                px = mark[i, j]
                if px == px:  # not NaN
                    out[t] = float(px)
        return out

    def tradable_today(self) -> list[str]:
        # The *selectable* universe (point-in-time members when a membership
        # filter is active); may be narrower than what's transactable today.
        return self.market.today_selectable[self._i]

    def field_today(self, ticker: str, field: str) -> float | None:
        if field == "Close":
            return self.today_prices.get(ticker)
        # Rare path: a non-Close field for a name that trades today.
        pos = self.market.trades_on(ticker, self._dv)
        if pos is None:
            return None
        s = self.market.series(ticker, field)
        if s is None:
            return None
        val = s.iloc[pos]
        return None if pd.isna(val) else float(val)

    def history(self, ticker: str, field: str, window: int | None) -> pd.Series:
        s = self.market.series(ticker, field)
        if s is None:
            return pd.Series(dtype=float)
        pos = self.market.rows_upto(ticker, self._dv)
        if pos == 0:
            return pd.Series(dtype=float)
        start = pos - window if (window and window < pos) else 0
        return s.iloc[start:pos]

    # ---- orders ----------------------------------------------------------
    def place_order(self, ticker: str, shares: float) -> None:
        px = self.today_prices.get(ticker)
        if px is None:
            if self.verbose:
                print(f"[{self._date.date()}] order rejected: {ticker} not tradable today")
            return

        # Slippage: buys fill above the close, sells below (crossing the spread).
        slip = self.slippage_pct
        fill = px * (1.0 + slip) if shares > 0 else px * (1.0 - slip)

        if shares > 0:
            # No leverage: never spend more cash than we hold. Cap the buy to
            # what the available cash can afford, including commission.
            per_share_cost = fill + self.portfolio.commission_per_share + fill * self.portfolio.commission_pct
            affordable = self.portfolio.cash / per_share_cost if per_share_cost > 0 else 0.0
            if affordable <= 0:
                return
            shares = min(shares, affordable)
        elif shares < 0:
            # No shorting: never sell more than we currently hold.
            held = self.portfolio.shares(ticker)
            shares = max(shares, -held)

        # Skip dust orders (e.g. tiny drift corrections from daily rebalancing).
        if abs(shares) * fill < self.min_order_value:
            return
        self.portfolio.execute(self._date, ticker, shares, fill, self.tax_policy)

    # ---- main loop -------------------------------------------------------
    def run(self) -> Result:
        self.strategy.initialize(self.ctx)

        market = self.market
        calendar = self.calendar
        cal_values = market.cal_values
        total_days = market.n

        equity_cash: list[float] = []
        equity_holdings: list[float] = []
        equity_total: list[float] = []

        # Optional progress heartbeat: set STOCKTEST_PROGRESS to a file path and
        # the loop writes "processed/total" to it periodically. No effect on the
        # simulation; used for monitoring long runs.
        progress_path = os.environ.get("STOCKTEST_PROGRESS")

        policy = self.tax_policy
        prev_year: int | None = None
        taxes_paid = 0.0        # taxes settled in-loop (reflected in the equity curve)
        carryforward = 0.0      # accumulated capital-loss carryforward

        for i in range(total_days):
            self._i = i
            self._dv = cal_values[i]
            date = calendar[i]
            self._date = date
            # Today's tradable snapshot is precomputed and shared across runs.
            self.today_prices = market.today_tradable[i]

            # On the first trading day of a new year, settle the prior year's
            # realized gains — paid from cash, so the tax drag compounds.
            if policy is not None and prev_year is not None and date.year != prev_year:
                r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
                tax, carryforward = compute_year_tax(r["st"], r["lt"], carryforward, policy)
                self.portfolio.cash -= tax
                taxes_paid += tax
            prev_year = date.year

            if progress_path and ((i + 1) % 100 == 0 or i + 1 == total_days):
                with open(progress_path, "w") as fh:
                    fh.write(f"{i + 1}/{total_days} {date.date()}\n")

            self.ctx.date = date
            self.strategy.on_day(self.ctx)

            holdings = self.portfolio.holdings_value(self.current_prices())
            equity_cash.append(self.portfolio.cash)
            equity_holdings.append(holdings)
            equity_total.append(self.portfolio.cash + holdings)

        equity = pd.DataFrame(
            {"cash": equity_cash, "holdings": equity_holdings, "total": equity_total},
            index=pd.DatetimeIndex(calendar, name="date"),
        )
        trades = pd.DataFrame([t.as_dict() for t in self.portfolio.trades])
        if not trades.empty:
            trades = trades.set_index("date")

        # Terminal tax: settle the final (partial) year's realized gains that the
        # in-loop settlement hasn't reached yet, then tax the remaining
        # unrealized gains as if everything were liquidated on the last day. This
        # makes a churn-heavy strategy and a defer-forever buy&hold comparable on
        # a fully-after-tax basis. Not deducted from the equity curve; surfaced
        # as `terminal_tax` and folded into the after-tax metrics on Result.
        terminal_tax: float | None = None
        if policy is not None:
            r = self.portfolio.realized.get(prev_year, {"st": 0.0, "lt": 0.0})
            fy_tax, carry2 = compute_year_tax(r["st"], r["lt"], carryforward, policy)
            st_u, lt_u = self.portfolio.unrealized_gains(
                self._date, self.current_prices(), policy
            )
            unreal_tax, _ = compute_year_tax(st_u, lt_u, carry2, policy)
            terminal_tax = fy_tax + unreal_tax

        return Result(
            equity=equity,
            trades=trades,
            starting_cash=self.starting_cash,
            taxes_paid=(taxes_paid if policy is not None else None),
            terminal_tax=terminal_tax,
        )

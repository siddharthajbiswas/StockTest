"""Backtest output: the equity curve, the trade blotter, and summary stats."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Result:
    equity: pd.DataFrame       # index=date, cols: cash, holdings, total
    trades: pd.DataFrame       # index=date, cols: ticker, side, shares, price, value, commission
    starting_cash: float
    # Tax accounting (None when taxes weren't modeled). `taxes_paid` is already
    # reflected in the equity curve; `terminal_tax` (final-year realized + a
    # liquidation tax on remaining unrealized gains) is not — it's applied only
    # to the after-tax metrics below, for an apples-to-apples net comparison.
    taxes_paid: float | None = None
    terminal_tax: float | None = None

    # ---- headline metrics ------------------------------------------------
    @property
    def final_value(self) -> float:
        return float(self.equity["total"].iloc[-1])

    @property
    def total_return(self) -> float:
        return self.final_value / self.starting_cash - 1.0

    # ---- after-tax metrics (fully liquidated) ---------------------------
    @property
    def after_tax_final_value(self) -> float:
        """Final value after also paying the terminal liquidation tax."""
        return self.final_value - (self.terminal_tax or 0.0)

    @property
    def after_tax_total_return(self) -> float:
        return self.after_tax_final_value / self.starting_cash - 1.0

    @property
    def after_tax_cagr(self) -> float:
        days = (self.equity.index[-1] - self.equity.index[0]).days
        if days <= 0:
            return 0.0
        years = days / 365.25
        return (self.after_tax_final_value / self.starting_cash) ** (1 / years) - 1.0

    @property
    def total_tax(self) -> float:
        return (self.taxes_paid or 0.0) + (self.terminal_tax or 0.0)

    @property
    def cagr(self) -> float:
        days = (self.equity.index[-1] - self.equity.index[0]).days
        if days <= 0:
            return 0.0
        years = days / 365.25
        return (self.final_value / self.starting_cash) ** (1 / years) - 1.0

    @property
    def daily_returns(self) -> pd.Series:
        return self.equity["total"].pct_change().dropna()

    @property
    def sharpe(self) -> float:
        r = self.daily_returns
        if r.std() == 0 or r.empty:
            return 0.0
        return float(np.sqrt(TRADING_DAYS) * r.mean() / r.std())

    @property
    def max_drawdown(self) -> float:
        curve = self.equity["total"]
        peak = curve.cummax()
        return float((curve / peak - 1.0).min())

    def since(self, date) -> "Result":
        """This result restricted to the window starting at `date`.

        For a run that was given extra history purely to warm up its indicators:
        the engine needs bars before the window, but the *scorecard* should only
        cover the window the user asked about. Valid exactly when nothing traded
        before `date` — the portfolio is still all cash there, so the sliced
        curve starts at the original starting cash and no tax has been paid yet.
        Raises if that precondition does not hold, rather than quietly reporting
        a mis-scaled return.
        """
        date = pd.Timestamp(date)
        equity = self.equity[self.equity.index >= date]
        if equity.empty:
            raise ValueError(f"no trading days on or after {date.date()}")
        if not self.trades.empty and (self.trades.index < date).any():
            raise ValueError(
                "Result.since() needs a window with no trades before it; "
                "the warm-up period must be untraded."
            )
        return Result(
            equity=equity,
            trades=self.trades,
            # Unchanged: nothing traded before `date`, so the portfolio is still
            # exactly the original cash on the window's first morning. Taking
            # equity[0] instead would use the first day's CLOSE — already net of
            # that day's commission and slippage — and quietly report the
            # strategy's entry costs as a smaller starting balance.
            starting_cash=self.starting_cash,
            taxes_paid=self.taxes_paid,
            terminal_tax=self.terminal_tax,
        )

    # ---- reporting -------------------------------------------------------
    def summary(self) -> None:
        n_trades = 0 if self.trades.empty else len(self.trades)
        commission = 0.0 if self.trades.empty else float(self.trades["commission"].sum())
        print("=" * 46)
        print("BACKTEST SUMMARY")
        print("=" * 46)
        print(f"Period            {self.equity.index[0].date()} -> {self.equity.index[-1].date()}")
        print(f"Trading days      {len(self.equity)}")
        print(f"Starting cash     ${self.starting_cash:,.2f}")
        print(f"Final value       ${self.final_value:,.2f}")
        print(f"Total return      {self.total_return * 100:,.2f}%")
        print(f"CAGR              {self.cagr * 100:,.2f}%")
        print(f"Sharpe (ann.)     {self.sharpe:,.2f}")
        print(f"Max drawdown      {self.max_drawdown * 100:,.2f}%")
        print(f"Trades            {n_trades}")
        print(f"Commission paid   ${commission:,.2f}")
        if self.taxes_paid is not None:
            print("-" * 46)
            print(f"Taxes paid (in-run) ${self.taxes_paid:,.2f}")
            print(f"Terminal tax        ${self.terminal_tax or 0.0:,.2f}")
            print(f"Total tax           ${self.total_tax:,.2f}")
            print(f"After-tax final   ${self.after_tax_final_value:,.2f}")
            print(f"After-tax return    {self.after_tax_total_return * 100:,.2f}%")
            print(f"After-tax CAGR      {self.after_tax_cagr * 100:,.2f}%")
        print("=" * 46)

    def trades_by_day(self) -> None:
        """Print the trade blotter grouped by day — the per-day trade log."""
        if self.trades.empty:
            print("No trades were made.")
            return
        for date, group in self.trades.groupby(level=0):
            print(f"\n{date.date()}")
            for _, t in group.iterrows():
                print(
                    f"  {t['side']:<4} {t['shares']:>10.2f} {t['ticker']:<6} "
                    f"@ ${t['price']:>10.2f}  = ${t['value']:>14,.2f}"
                )

    def save(self, out_dir: Path | str) -> None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.equity.to_csv(out_dir / "equity.csv")
        self.trades.to_csv(out_dir / "trades.csv")
        print(f"Saved equity.csv and trades.csv to {out_dir}")

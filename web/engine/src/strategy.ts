/**
 * The API a strategy talks to. Port of `backtester/strategy.py`.
 *
 * Everything an algorithm may see or do goes through the `Context` it receives
 * each trading day. The context only exposes data up to and including the
 * current day, so strategies cannot peek at the future. Orders placed during
 * `onDay` fill immediately at the current day's close.
 */

import type { Backtest } from "./engine.js";
import type { Field } from "./data.js";

export class Context {
  /** Current calendar day number; refreshed by the engine each step. */
  day = -1;

  constructor(private readonly engine: Backtest) {}

  get cash(): number {
    return this.engine.portfolio.cash;
  }

  /** {ticker: shares} for open positions — a copy, as in Python. */
  get positions(): Map<string, number> {
    return new Map(this.engine.portfolio.positions);
  }

  get portfolioValue(): number {
    return this.engine.portfolio.totalValue(this.engine.currentPrices());
  }

  shares(ticker: string): number {
    return this.engine.portfolio.shares(ticker);
  }

  /** Tickers selectable today (PIT members when a membership filter is active). */
  get universe(): string[] {
    return this.engine.tradableToday();
  }

  canTrade(ticker: string): boolean {
    return this.engine.todayPrices.has(ticker);
  }

  /** Today's value of `field`, or null if the ticker doesn't trade today. */
  price(ticker: string, field: Field = "Close"): number | null {
    return this.engine.fieldToday(ticker, field);
  }

  /** `field` for `ticker` up to and including today, last `window` values. */
  history(ticker: string, field: Field = "Close", window: number | null = null): Float64Array {
    return this.engine.history(ticker, field, window);
  }

  order(ticker: string, shares: number): void {
    this.engine.placeOrder(ticker, shares);
  }

  orderTargetShares(ticker: string, target: number): void {
    this.engine.placeOrder(ticker, target - this.shares(ticker));
  }

  /** Rebalance so `ticker` is `pct` (0..1) of current portfolio value. */
  orderTargetPercent(ticker: string, pct: number): void {
    const px = this.price(ticker);
    if (px === null || px <= 0) return;
    const targetValue = this.portfolioValue * pct;
    this.orderTargetShares(ticker, targetValue / px);
  }

  liquidate(ticker: string): void {
    this.orderTargetShares(ticker, 0);
  }
}

export interface Strategy {
  initialize(ctx: Context): void;
  onDay(ctx: Context): void;
}

/**
 * The API a strategy talks to. Port of `backtester/strategy.py`.
 *
 * Everything an algorithm may see or do goes through the `Context` it receives
 * each trading day. The context only exposes data up to and including the
 * current day, so strategies cannot peek at the future. Orders placed during
 * `onDay` fill immediately at the current day's close.
 */
export class Context {
  engine;
  /** Current calendar day number; refreshed by the engine each step. */
  day = -1;
  constructor(engine) {
    this.engine = engine;
  }
  get cash() {
    return this.engine.portfolio.cash;
  }
  /** {ticker: shares} for open positions — a copy, as in Python. */
  get positions() {
    return new Map(this.engine.portfolio.positions);
  }
  get portfolioValue() {
    return this.engine.portfolio.totalValue(this.engine.currentPrices());
  }
  shares(ticker) {
    return this.engine.portfolio.shares(ticker);
  }
  /** Tickers selectable today (PIT members when a membership filter is active). */
  get universe() {
    return this.engine.tradableToday();
  }
  canTrade(ticker) {
    return this.engine.todayPrices.has(ticker);
  }
  /** Today's value of `field`, or null if the ticker doesn't trade today. */
  price(ticker, field = "Close") {
    return this.engine.fieldToday(ticker, field);
  }
  /** `field` for `ticker` up to and including today, last `window` values. */
  history(ticker, field = "Close", window = null) {
    return this.engine.history(ticker, field, window);
  }
  order(ticker, shares) {
    this.engine.placeOrder(ticker, shares);
  }
  orderTargetShares(ticker, target) {
    this.engine.placeOrder(ticker, target - this.shares(ticker));
  }
  /** Rebalance so `ticker` is `pct` (0..1) of current portfolio value. */
  orderTargetPercent(ticker, pct) {
    const px = this.price(ticker);
    if (px === null || px <= 0) return;
    const targetValue = this.portfolioValue * pct;
    this.orderTargetShares(ticker, targetValue / px);
  }
  liquidate(ticker) {
    this.orderTargetShares(ticker, 0);
  }
}

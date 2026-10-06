/**
 * The API a strategy talks to. Port of `backtester/strategy.py`.
 *
 * Everything an algorithm may see or do goes through the `Context` it receives
 * each trading day. The context only exposes data up to and including the
 * current day, so strategies cannot peek at the future. Orders placed during
 * `onDay` fill immediately at the current day's close.
 */
import { isLongTerm } from "./tax.js";
import { yearOfDay } from "./result.js";

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
  // ---- tax-lot state (only populated when a tax policy is active) ------
  /**
   * Open tax lots for `ticker` as `{day, shares, costPerShare}`, FIFO order.
   * Cost already includes commission and slippage. Empty when the run has no
   * tax policy. Port of `Context.lots` in `backtester/strategy.py`.
   */
  lots(ticker) {
    const lots = this.engine.portfolio.lots.get(ticker);
    return lots === undefined ? [] : lots.map((l) => ({ ...l }));
  }
  /** [shortTerm, longTerm] net realized gains booked so far this year. */
  realizedThisYear() {
    const bucket = this.engine.portfolio.realized.get(yearOfDay(this.day));
    return bucket === undefined ? [0.0, 0.0] : [bucket.st, bucket.lt];
  }
  /** Would selling a lot bought on `purchaseDay` today be long-term? */
  isLongTerm(purchaseDay) {
    const policy = this.engine.taxPolicy;
    if (policy === null || policy === undefined) return true;
    return isLongTerm(policy, this.day - purchaseDay);
  }
  /** Half-spread the engine applies to fills (buys up, sells down). */
  get slippagePct() {
    return this.engine.slippagePct;
  }
  /** Commission as a fraction of trade value. */
  get commissionPct() {
    return this.engine.portfolio.commissionPct;
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

/**
 * Cash / positions / trade-blotter accounting. Port of `backtester/portfolio.py`.
 *
 * PARITY NOTE — iteration order matters.
 * `holdings_value` sums positions in Python dict order, which is insertion
 * order. Floating-point addition is not associative, so the sum depends on that
 * order. A JS `Map` has the same insertion-order semantics as a Python dict,
 * including the subtle part: re-inserting a key that was deleted moves it to
 * the end, while assigning to an existing key leaves its position alone. Using
 * a plain object here would be wrong (integer-like keys get reordered), and
 * sorting the keys would also be wrong. Keep the `Map`.
 */

import { isLongTerm, type Lot, type TaxPolicy } from "./tax.js";

export interface Trade {
  /** Calendar day number (days since 1970-01-01). */
  day: number;
  ticker: string;
  side: "BUY" | "SELL";
  /** Always positive. */
  shares: number;
  price: number;
  /** shares * price — cash moved, excluding commission. */
  value: number;
  commission: number;
}

interface RealizedBucket {
  st: number;
  lt: number;
}

export class Portfolio {
  cash: number;
  readonly commissionPerShare: number;
  readonly commissionPct: number;
  /** ticker -> shares. Insertion-ordered; see the parity note above. */
  readonly positions = new Map<string, number>();
  readonly trades: Trade[] = [];
  /** ticker -> FIFO tax lots. */
  readonly lots = new Map<string, Lot[]>();
  /** calendar year -> realized gains. */
  readonly realized = new Map<number, RealizedBucket>();

  constructor(cash: number, commissionPerShare = 0.0, commissionPct = 0.0) {
    this.cash = cash;
    this.commissionPerShare = commissionPerShare;
    this.commissionPct = commissionPct;
  }

  shares(ticker: string): number {
    return this.positions.get(ticker) ?? 0.0;
  }

  // ---- tax-lot accounting ------------------------------------------------
  private recordRealized(year: number, gain: number, longTerm: boolean): void {
    let bucket = this.realized.get(year);
    if (bucket === undefined) {
      bucket = { st: 0.0, lt: 0.0 };
      this.realized.set(year, bucket);
    }
    if (longTerm) bucket.lt += gain;
    else bucket.st += gain;
  }

  private openLot(day: number, ticker: string, shares: number, costPerShare: number): void {
    let lots = this.lots.get(ticker);
    if (lots === undefined) {
      lots = [];
      this.lots.set(ticker, lots);
    }
    lots.push({ day, shares, costPerShare });
  }

  /**
   * Consume `shares` from a ticker's lots FIFO, realizing gains.
   * The `1e-12` residual threshold and the `shift()` on exhaustion mirror
   * Python's `while remaining > 1e-12 and lots` / `lots.pop(0)`.
   */
  private closeLots(
    day: number,
    year: number,
    ticker: string,
    shares: number,
    proceedsPerShare: number,
    policy: TaxPolicy,
  ): void {
    let remaining = shares;
    const lots = this.lots.get(ticker);
    if (lots === undefined) return;
    while (remaining > 1e-12 && lots.length > 0) {
      const lot = lots[0];
      const take = Math.min(remaining, lot.shares);
      const gain = (proceedsPerShare - lot.costPerShare) * take;
      const holdingDays = day - lot.day;
      this.recordRealized(year, gain, isLongTerm(policy, holdingDays));
      lot.shares -= take;
      remaining -= take;
      if (lot.shares <= 1e-12) lots.shift();
    }
  }

  /**
   * (shortTerm, longTerm) unrealized gain across open lots, for the terminal
   * liquidation tax. Iterates `lots` in insertion order, as Python does.
   */
  unrealizedGains(
    day: number,
    prices: Map<string, number>,
    policy: TaxPolicy,
  ): { st: number; lt: number } {
    let st = 0.0;
    let lt = 0.0;
    for (const [ticker, lots] of this.lots) {
      const px = prices.get(ticker);
      if (px === undefined) continue;
      for (const lot of lots) {
        const gain = (px - lot.costPerShare) * lot.shares;
        if (isLongTerm(policy, day - lot.day)) lt += gain;
        else st += gain;
      }
    }
    return { st, lt };
  }

  /** Mark-to-market value of open positions. Insertion-ordered accumulation. */
  holdingsValue(prices: Map<string, number>): number {
    let total = 0.0;
    for (const [ticker, qty] of this.positions) {
      const px = prices.get(ticker);
      if (px !== undefined) total += qty * px;
    }
    return total;
  }

  totalValue(prices: Map<string, number>): number {
    return this.cash + this.holdingsValue(prices);
  }

  /**
   * Fill an order of `deltaShares` (buy > 0 / sell < 0) at `price`.
   *
   * `price` already includes slippage (applied by the engine). Commission is
   * folded into the tax lots so realized gains are net of all trading costs.
   */
  execute(
    day: number,
    year: number,
    ticker: string,
    deltaShares: number,
    price: number,
    policy: TaxPolicy | null,
  ): Trade | null {
    if (deltaShares === 0) return null;
    const side: "BUY" | "SELL" = deltaShares > 0 ? "BUY" : "SELL";
    const qty = Math.abs(deltaShares);
    const value = qty * price;
    const commission = qty * this.commissionPerShare + value * this.commissionPct;
    const perShareCommission = qty ? commission / qty : 0.0;

    this.cash += deltaShares > 0 ? -value - commission : value - commission;

    const next = this.shares(ticker) + deltaShares;
    this.positions.set(ticker, next);
    if (Math.abs(next) < 1e-9) this.positions.delete(ticker);

    if (policy !== null) {
      if (deltaShares > 0) {
        this.openLot(day, ticker, qty, price + perShareCommission);
      } else {
        this.closeLots(day, year, ticker, qty, price - perShareCommission, policy);
      }
    }

    const trade: Trade = { day, ticker, side, shares: qty, price, value, commission };
    this.trades.push(trade);
    return trade;
  }
}

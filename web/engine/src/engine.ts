/**
 * The day-by-day simulation loop. Port of `backtester/engine.py`.
 */

import type { Field } from "./data.js";
import type { MarketData } from "./market.js";
import { Portfolio } from "./portfolio.js";
import { Result, yearOfDay, type EquityCurve } from "./result.js";
import { Context, type Strategy } from "./strategy.js";
import { computeYearTax, type TaxPolicy } from "./tax.js";

export interface BacktestOptions {
  cash?: number;
  commissionPerShare?: number;
  commissionPct?: number;
  minOrderValue?: number;
  slippagePct?: number;
  taxPolicy?: TaxPolicy | null;
}

export class Backtest {
  readonly portfolio: Portfolio;
  readonly market: MarketData;
  readonly startingCash: number;

  private readonly strategy: Strategy;
  private readonly minOrderValue: number;
  private readonly slippagePct: number;
  private readonly taxPolicy: TaxPolicy | null;
  private readonly ctx: Context;

  /** State for the day currently being processed. */
  private i = -1;
  private curDay = -1;
  /** ticker -> today's close (tradable names only). */
  todayPrices = new Map<string, number>();

  constructor(strategy: Strategy, market: MarketData, opts: BacktestOptions = {}) {
    const {
      cash = 100_000.0,
      commissionPerShare = 0.0,
      commissionPct = 0.0,
      minOrderValue = 1.0,
      slippagePct = 0.0,
      taxPolicy = null,
    } = opts;

    this.strategy = strategy;
    this.market = market;
    this.minOrderValue = minOrderValue;
    this.slippagePct = slippagePct;
    this.taxPolicy = taxPolicy;
    this.startingCash = cash;
    this.portfolio = new Portfolio(cash, commissionPerShare, commissionPct);
    this.ctx = new Context(this);
  }

  // ---- data access used by Context --------------------------------------
  /**
   * Mark open positions at their last known (forward-filled) close, so a
   * holding in a name that didn't trade today isn't valued at zero.
   * Iterates `positions` in insertion order — see the portfolio parity note.
   */
  currentPrices(): Map<string, number> {
    const out = new Map<string, number>();
    const T = this.market.tickers.length;
    for (const ticker of this.portfolio.positions.keys()) {
      const j = this.market.col(ticker);
      if (j === undefined) continue;
      const px = this.market.markValues[this.i * T + j];
      if (!Number.isNaN(px)) out.set(ticker, px);
    }
    return out;
  }

  tradableToday(): string[] {
    return this.market.todaySelectable[this.i];
  }

  fieldToday(ticker: string, field: Field): number | null {
    if (field === "Close") {
      const v = this.todayPrices.get(ticker);
      return v === undefined ? null : v;
    }
    const pos = this.market.tradesOn(ticker, this.curDay);
    if (pos === null) return null;
    const s = this.market.get(ticker);
    const arr = s?.fields[field];
    if (arr === undefined) return null;
    const val = arr[pos];
    return Number.isNaN(val) ? null : val;
  }

  history(ticker: string, field: Field, window: number | null): Float64Array {
    const s = this.market.get(ticker);
    const arr = s?.fields[field];
    if (arr === undefined) return new Float64Array(0);
    const pos = this.market.rowsUpto(ticker, this.curDay);
    if (pos === 0) return new Float64Array(0);
    const start = window !== null && window < pos ? pos - window : 0;
    return arr.subarray(start, pos);
  }

  // ---- orders -----------------------------------------------------------
  placeOrder(ticker: string, sharesIn: number): void {
    const px = this.todayPrices.get(ticker);
    if (px === undefined) return;

    // Slippage: buys fill above the close, sells below (crossing the spread).
    const slip = this.slippagePct;
    const fill = sharesIn > 0 ? px * (1.0 + slip) : px * (1.0 - slip);

    let shares = sharesIn;
    if (shares > 0) {
      // No leverage: cap the buy to what available cash affords, incl. commission.
      const perShareCost =
        fill + this.portfolio.commissionPerShare + fill * this.portfolio.commissionPct;
      const affordable = perShareCost > 0 ? this.portfolio.cash / perShareCost : 0.0;
      if (affordable <= 0) return;
      shares = Math.min(shares, affordable);
    } else if (shares < 0) {
      // No shorting: never sell more than we hold.
      const held = this.portfolio.shares(ticker);
      shares = Math.max(shares, -held);
    }

    // Skip dust orders (e.g. tiny drift corrections from daily rebalancing).
    if (Math.abs(shares) * fill < this.minOrderValue) return;
    this.portfolio.execute(
      this.curDay, yearOfDay(this.curDay), ticker, shares, fill, this.taxPolicy,
    );
  }

  // ---- main loop --------------------------------------------------------
  run(): Result {
    this.strategy.initialize(this.ctx);

    const market = this.market;
    const total = market.n;
    const cashCurve = new Float64Array(total);
    const holdingsCurve = new Float64Array(total);
    const totalCurve = new Float64Array(total);

    const policy = this.taxPolicy;
    let prevYear: number | null = null;
    let taxesPaid = 0.0;
    let carryforward = 0.0;

    for (let i = 0; i < total; i++) {
      this.i = i;
      this.curDay = market.calendar[i];
      this.todayPrices = market.todayTradable[i];
      const year = yearOfDay(this.curDay);

      // On the first trading day of a new year, settle the prior year's
      // realized gains — paid from cash, so the tax drag compounds.
      if (policy !== null && prevYear !== null && year !== prevYear) {
        const r = this.portfolio.realized.get(prevYear) ?? { st: 0.0, lt: 0.0 };
        const { tax, carryforward: cf } = computeYearTax(r.st, r.lt, carryforward, policy);
        carryforward = cf;
        this.portfolio.cash -= tax;
        taxesPaid += tax;
      }
      prevYear = year;

      this.ctx.day = this.curDay;
      this.strategy.onDay(this.ctx);

      const holdings = this.portfolio.holdingsValue(this.currentPrices());
      cashCurve[i] = this.portfolio.cash;
      holdingsCurve[i] = holdings;
      totalCurve[i] = this.portfolio.cash + holdings;
    }

    const equity: EquityCurve = {
      days: market.calendar,
      cash: cashCurve,
      holdings: holdingsCurve,
      total: totalCurve,
    };

    // Terminal tax: settle the final (partial) year, then tax remaining
    // unrealized gains as if everything were liquidated on the last day. This
    // makes a churn-heavy strategy and a defer-forever buy&hold comparable on a
    // fully after-tax basis. Not deducted from the equity curve.
    let terminalTax: number | null = null;
    if (policy !== null) {
      const r = this.portfolio.realized.get(prevYear!) ?? { st: 0.0, lt: 0.0 };
      const fy = computeYearTax(r.st, r.lt, carryforward, policy);
      const u = this.portfolio.unrealizedGains(this.curDay, this.currentPrices(), policy);
      const unreal = computeYearTax(u.st, u.lt, fy.carryforward, policy);
      terminalTax = fy.tax + unreal.tax;
    }

    return new Result(
      equity,
      this.portfolio.trades,
      this.startingCash,
      policy !== null ? taxesPaid : null,
      terminalTax,
    );
  }
}

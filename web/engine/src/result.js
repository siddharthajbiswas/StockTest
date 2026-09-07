/**
 * Backtest output: equity curve, trade blotter, summary stats.
 * Port of `backtester/result.py`.
 */
import { cummax, nmean, nstd, nsum, pctChange } from "./numeric.js";
const TRADING_DAYS = 252;

/** Milliseconds per day, for converting day numbers to calendar years. */
const MS_PER_DAY = 86400000;

/** Calendar year of a day number (days since 1970-01-01 UTC). */
export function yearOfDay(day) {
  return new Date(day * MS_PER_DAY).getUTCFullYear();
}

/** ISO date (YYYY-MM-DD) of a day number. */
export function isoOfDay(day) {
  return new Date(day * MS_PER_DAY).toISOString().slice(0, 10);
}

export class Result {
  equity;
  trades;
  startingCash;
  taxesPaid;
  terminalTax;
  constructor(
    equity,
    trades,
    startingCash,
    /** null when taxes were not modeled. Already reflected in the equity curve. */
    taxesPaid = null,
    /** Final-year realized + liquidation tax on remaining unrealized gains.
     *  NOT reflected in the equity curve — applied only to after-tax metrics. */
    terminalTax = null,
  ) {
    this.equity = equity;
    this.trades = trades;
    this.startingCash = startingCash;
    this.taxesPaid = taxesPaid;
    this.terminalTax = terminalTax;
  }
  get finalValue() {
    const t = this.equity.total;
    return t[t.length - 1];
  }
  get totalReturn() {
    return this.finalValue / this.startingCash - 1.0;
  }
  get afterTaxFinalValue() {
    return this.finalValue - (this.terminalTax ?? 0.0);
  }
  get afterTaxTotalReturn() {
    return this.afterTaxFinalValue / this.startingCash - 1.0;
  }
  /** Elapsed calendar days between the first and last bar. */
  get spanDays() {
    const d = this.equity.days;
    return d[d.length - 1] - d[0];
  }
  get afterTaxCagr() {
    const days = this.spanDays;
    if (days <= 0) return 0.0;
    const years = days / 365.25;
    return (
      Math.pow(this.afterTaxFinalValue / this.startingCash, 1 / years) - 1.0
    );
  }
  get totalTax() {
    return (this.taxesPaid ?? 0.0) + (this.terminalTax ?? 0.0);
  }
  get cagr() {
    const days = this.spanDays;
    if (days <= 0) return 0.0;
    const years = days / 365.25;
    return Math.pow(this.finalValue / this.startingCash, 1 / years) - 1.0;
  }
  /** `equity["total"].pct_change().dropna()`. */
  get dailyReturns() {
    return pctChange(this.equity.total);
  }
  /**
   * Annualized Sharpe. Python guards `if r.std() == 0 or r.empty`, evaluating
   * std first — reproduced here so an empty series takes the same branch.
   */
  get sharpe() {
    const r = this.dailyReturns;
    if (r.length === 0) return 0.0;
    const sd = nstd(r, 1);
    if (sd === 0) return 0.0;
    return (Math.sqrt(TRADING_DAYS) * nmean(r)) / sd;
  }
  get maxDrawdown() {
    const curve = this.equity.total;
    const peak = cummax(curve);
    let min = Infinity;
    for (let i = 0; i < curve.length; i++) {
      const v = curve[i] / peak[i] - 1.0;
      if (v < min) min = v;
    }
    return min;
  }
  /**
   * Python does `res.trades["commission"].sum()` — a pandas reduction, so it
   * uses NumPy's pairwise summation, NOT a left-to-right loop. Must go through
   * `nsum` or the total drifts in the low bits.
   */
  get commissionPaid() {
    const c = new Float64Array(this.trades.length);
    for (let i = 0; i < this.trades.length; i++)
      c[i] = this.trades[i].commission;
    return nsum(c);
  }
}

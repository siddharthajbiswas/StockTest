/**
 * Composable strategies: a Picker chooses *what* to hold, a Timer chooses
 * *when*. Port of `backtester/composite.py`.
 *
 * The picker runs on a rebalance cadence (monthly by default); the timer is
 * evaluated every day, so it can move in and out of the basket between
 * rebalances. Neither can see the future — both only reach data through
 * `ctx.history`, which the engine clips to the current day.
 */
import { yearOfDay } from "./result.js";
const MS_PER_DAY = 86400000;

/**
 * ISO week key, matching `pd.Timestamp.isocalendar()` -> (year, week).
 * ISO weeks start Monday and week 1 is the week containing the first Thursday.
 */
function isoYearWeek(day) {
  const d = new Date(day * MS_PER_DAY);
  // Shift to the Thursday of this ISO week; its calendar year is the ISO year.
  const dow = (d.getUTCDay() + 6) % 7; // Monday = 0
  const thursday = new Date((day - dow + 3) * MS_PER_DAY);
  const isoYear = thursday.getUTCFullYear();
  const jan1 = Date.UTC(isoYear, 0, 1) / MS_PER_DAY;
  const week = Math.floor((day - dow + 3 - jan1) / 7) + 1;
  return `${isoYear}-${week}`;
}

function periodKey(day, rebalance) {
  const d = new Date(day * MS_PER_DAY);
  switch (rebalance) {
    case "D":
      return String(day);
    case "W":
      return isoYearWeek(day);
    case "Q":
      return `${d.getUTCFullYear()}-${Math.floor(d.getUTCMonth() / 3)}`;
    case "M":
      return `${d.getUTCFullYear()}-${d.getUTCMonth()}`;
    default:
      throw new Error(`unknown rebalance cadence: ${rebalance}`);
  }
}

/**
 * Run a Picker and a Timer together as one tradable Strategy.
 *
 * Each rebalance day the picker refreshes the basket of `topN` candidates.
 * Every day the timer is asked, for each basket name, whether to be long; the
 * portfolio holds the intersection, equal-weighted. Weights are rewritten only
 * when that set changes, which keeps commission churn down.
 */
export class Combo {
  picker;
  timer;
  topN;
  rebalance;
  basket = [];
  members = new Set();
  entry = new Map();
  lastPeriod = null;
  constructor(picker, timer, topN = 20, rebalance = "M") {
    this.picker = picker;
    this.timer = timer;
    this.topN = topN;
    this.rebalance = rebalance;
  }
  initialize(ctx) {
    this.picker.initialize(ctx);
    this.timer.initialize(ctx);
    this.basket = [];
    this.members = new Set();
    this.entry = new Map();
    this.lastPeriod = null;
  }
  onDay(ctx) {
    const key = periodKey(ctx.day, this.rebalance);
    if (key !== this.lastPeriod) {
      this.lastPeriod = key;
      this.basket = this.picker.select(ctx, ctx.universe, this.topN);
    }
    const longs = [];
    for (const ticker of this.basket) {
      if (!ctx.canTrade(ticker)) continue;
      const held = ctx.shares(ticker) > 0;
      const entryPrice = this.entry.has(ticker) ? this.entry.get(ticker) : null;
      if (this.timer.wantLong(ctx, ticker, held, entryPrice))
        longs.push(ticker);
    }
    const longSet = new Set(longs);
    // Close anything held that we no longer want. Python iterates
    // `list(ctx.positions)` — a snapshot of the keys — so mutation during the
    // loop is safe and order is the portfolio's insertion order.
    for (const ticker of [...ctx.positions.keys()]) {
      if (!longSet.has(ticker)) {
        ctx.liquidate(ticker);
        this.entry.delete(ticker);
      }
    }
    // Rewrite weights only when membership changes (limits churn/commission).
    if (!sameSet(longSet, this.members)) {
      const weight = longs.length > 0 ? 1.0 / longs.length : 0.0;
      for (const ticker of longs) ctx.orderTargetPercent(ticker, weight);
      this.members = longSet;
    }
    // Record an entry price for every newly opened name.
    for (const ticker of longs) {
      if (!this.entry.has(ticker)) {
        const px = ctx.price(ticker);
        if (px !== null) this.entry.set(ticker, px);
      }
    }
  }
}

function sameSet(a, b) {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}

export { yearOfDay };

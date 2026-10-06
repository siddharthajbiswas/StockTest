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
    case "S":
      return `${d.getUTCFullYear()}-s${Math.floor(d.getUTCMonth() / 6)}`;
    case "A":
      return `${d.getUTCFullYear()}`;
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
  /** Optional shortlist: the picker ranks only within these names. */
  menu = null;
  constructor(picker, timer, topN = 20, rebalance = "M", menu = null) {
    this.picker = picker;
    this.timer = timer;
    this.topN = topN;
    this.rebalance = rebalance;
    this.menu = menu === null || menu === undefined ? null : [...menu];
  }
  candidates(ctx) {
    if (this.menu === null) return ctx.universe;
    const tradable = new Set(ctx.universe);
    return this.menu.filter((t) => tradable.has(t));
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
      this.basket = this.picker.select(ctx, this.candidates(ctx), this.topN);
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

/**
 * A Combo whose *execution* is governed by a realized-gain budget.
 * Port of `TaxManagedCombo` in `backtester/composite.py` — see that docstring
 * for why this exists. Same picker, same timer; the difference is what the
 * portfolio is allowed to sell.
 */
export class TaxManagedCombo extends Combo {
  gainBudget;
  washDays;
  lossSale = new Map();
  constructor(
    picker,
    timer,
    topN = 20,
    rebalance = "M",
    menu = null,
    gainBudget = 0.01,
    washDays = 31,
  ) {
    super(picker, timer, topN, rebalance, menu);
    this.gainBudget = gainBudget;
    this.washDays = washDays;
  }
  initialize(ctx) {
    super.initialize(ctx);
    this.lossSale = new Map();
  }
  /** [gain, allLongTerm] that selling `shares` FIFO at `netPrice` books. */
  gainIfSold(ctx, ticker, shares, netPrice) {
    let remaining = shares;
    let gain = 0.0;
    let allLt = true;
    for (const lot of ctx.lots(ticker)) {
      if (remaining <= 1e-12) break;
      const take = Math.min(remaining, lot.shares);
      gain += (netPrice - lot.costPerShare) * take;
      if (!ctx.isLongTerm(lot.day)) allLt = false;
      remaining -= take;
    }
    return [gain, allLt];
  }
  onDay(ctx) {
    const key = periodKey(ctx.day, this.rebalance);
    if (key === this.lastPeriod) return;
    this.lastPeriod = key;
    this.basket = this.picker.select(ctx, this.candidates(ctx), this.topN);

    const longs = [];
    for (const t of this.basket) {
      if (!ctx.canTrade(t)) continue;
      const entryPrice = this.entry.has(t) ? this.entry.get(t) : null;
      if (this.timer.wantLong(ctx, t, ctx.shares(t) > 0, entryPrice))
        longs.push(t);
    }

    const pv = ctx.portfolioValue;
    if (pv <= 0) return;
    const weight = longs.length > 0 ? 1.0 / longs.length : 0.0;

    // Target share counts from ONE portfolio-value snapshot, so the plan does
    // not shift underneath itself as fills come in.
    const wanted = new Set(longs);
    const targets = new Map();
    const names = new Set([...wanted, ...ctx.positions.keys()]);
    for (const t of names) {
      const px = ctx.price(t);
      if (px === null || px <= 0) continue;
      targets.set(t, wanted.has(t) ? (pv * weight) / px : 0.0);
    }

    // ---- sells, rationed by the realized-gain budget
    const [st, lt] = ctx.realizedThisYear();
    let room = this.gainBudget * pv - (st + lt);

    const candidates = [];
    for (const [t, target] of targets) {
      const held = ctx.shares(t);
      if (held <= 0 || target >= held) continue;
      const qty = held - target;
      const px = ctx.price(t);
      const net = px * (1.0 - ctx.slippagePct) * (1.0 - ctx.commissionPct);
      const [gain, allLt] = this.gainIfSold(ctx, t, qty, net);
      candidates.push({ isGain: gain > 0, isShort: !allLt, gain, t, qty });
    }
    // Losses first (they refill the budget), then gains smallest-first,
    // long-term before short-term; ticker breaks ties reproducibly. Mirrors
    // Python's tuple sort, where False sorts before True.
    candidates.sort((a, b) => {
      if (a.isGain !== b.isGain) return a.isGain ? 1 : -1;
      if (a.isShort !== b.isShort) return a.isShort ? 1 : -1;
      if (a.gain !== b.gain) return a.gain - b.gain;
      if (a.t === b.t) return 0;
      return a.t < b.t ? -1 : 1;
    });
    for (const c of candidates) {
      let sell;
      if (!c.isGain) sell = c.qty;
      else if (c.gain <= room + 1e-9) sell = c.qty;
      else if (room > 1e-9) {
        const frac = room / c.gain;
        if (frac <= 0.02) continue;
        sell = c.qty * frac;
      } else continue;
      room -= c.gain * (sell / c.qty);
      ctx.order(c.t, -sell);
      if (c.gain < 0) this.lossSale.set(c.t, ctx.day);
      if (ctx.shares(c.t) <= 0) this.entry.delete(c.t);
    }

    // ---- buys, in a fixed order so runs are reproducible
    for (const t of [...longs].sort()) {
      const last = this.lossSale.get(t);
      if (last !== undefined && ctx.day - last <= this.washDays) continue;
      const target = targets.get(t);
      if (target === undefined) continue;
      const delta = target - ctx.shares(t);
      if (delta > 0) ctx.order(t, delta);
    }

    this.members = new Set(longs.filter((t) => ctx.shares(t) > 0));
    for (const t of longs) {
      if (!this.entry.has(t) && ctx.shares(t) > 0) {
        const px = ctx.price(t);
        if (px !== null) this.entry.set(t, px);
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

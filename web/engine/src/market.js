/**
 * Precomputed, strategy-independent market structure.
 * Port of `backtester/market.py`.
 *
 * Building this is the expensive part of a backtest, and none of it depends on
 * the strategy — so build once and reuse across runs (e.g. the gross/net pass
 * pair, or a parameter sweep).
 *
 * PARITY NOTE — column order is load-bearing.
 * Python builds the close matrix from `{t: series for t in prices}`, so column
 * order is the insertion order of the prices dict. `today_tradable[i]` is then
 * built by iterating column indices ascending, which fixes the insertion order
 * of that per-day dict — which in turn fixes the iteration order of
 * `ctx.universe` and (transitively) the order positions get created in. Since
 * float addition is not associative, that ordering reaches the equity curve.
 * The `tickers` array passed to the constructor MUST therefore match the
 * Python prices-dict order.
 */
import { searchsortedRight } from "./numeric.js";
export class MarketData {
  tickers;
  calendar;
  n;
  series = new Map();
  colIndex = new Map();
  /** Dense (days x tickers) forward-filled close matrix, row-major. */
  markValues;
  /** Per-day tradable snapshot: ticker -> today's close. Insertion-ordered. */
  todayTradable;
  /** Per-day selectable universe (PIT members when supplied). */
  todaySelectable;
  constructor(prices, membersByDay = null) {
    if (prices.size === 0)
      throw new Error("MarketData needs at least one ticker.");
    this.tickers = [...prices.keys()];
    for (const [t, s] of prices) this.series.set(t, s);
    // Union trading calendar.
    const all = new Set();
    for (const s of prices.values()) for (const d of s.days) all.add(d);
    this.calendar = Int32Array.from([...all].sort((a, b) => a - b));
    this.n = this.calendar.length;
    const T = this.tickers.length;
    for (let j = 0; j < T; j++) this.colIndex.set(this.tickers[j], j);
    // Scatter each ticker's bars into the dense matrix.
    const closeRaw = new Float64Array(this.n * T).fill(NaN);
    const tradable = new Uint8Array(this.n * T);
    for (let j = 0; j < T; j++) {
      const s = prices.get(this.tickers[j]);
      const close = s.fields.Close;
      for (let k = 0; k < s.days.length; k++) {
        const i = searchsortedRight(this.calendar, s.days[k]) - 1;
        closeRaw[i * T + j] = close[k];
        // Python: ~isnan(close) & (isnan(vol) | vol > 0), evaluated on float64
        // source at build time and shipped as a bit. A NaN close is never
        // tradable, matching the first clause.
        tradable[i * T + j] = Number.isNaN(close[k]) ? 0 : s.tradable[k];
      }
    }
    // Forward-fill each column so a holding in a name that did not trade today
    // is marked at its last known close instead of dropping to zero.
    this.markValues = new Float64Array(this.n * T);
    for (let j = 0; j < T; j++) {
      let last = NaN;
      for (let i = 0; i < this.n; i++) {
        const v = closeRaw[i * T + j];
        if (!Number.isNaN(v)) last = v;
        this.markValues[i * T + j] = last;
      }
    }
    // Per-day tradable snapshot, columns ascending (see parity note).
    this.todayTradable = new Array(this.n);
    for (let i = 0; i < this.n; i++) {
      const m = new Map();
      for (let j = 0; j < T; j++) {
        if (tradable[i * T + j]) m.set(this.tickers[j], closeRaw[i * T + j]);
      }
      this.todayTradable[i] = m;
    }
    this.todaySelectable = new Array(this.n);
    if (membersByDay === null) {
      for (let i = 0; i < this.n; i++)
        this.todaySelectable[i] = [...this.todayTradable[i].keys()];
    } else {
      if (membersByDay.length !== this.n) {
        throw new Error("membersByDay must align to the market calendar.");
      }
      for (let i = 0; i < this.n; i++) {
        const members = membersByDay[i];
        const out = [];
        for (const t of this.todayTradable[i].keys())
          if (members.has(t)) out.push(t);
        this.todaySelectable[i] = out;
      }
    }
  }
  col(ticker) {
    return this.colIndex.get(ticker);
  }
  get(ticker) {
    return this.series.get(ticker);
  }
  /** How many of `ticker`'s bars fall on or before `day`. */
  rowsUpto(ticker, day) {
    const s = this.series.get(ticker);
    if (s === undefined) return 0;
    return searchsortedRight(s.days, day);
  }
  /** Row position of `ticker`'s bar dated exactly `day`, or null. */
  tradesOn(ticker, day) {
    const s = this.series.get(ticker);
    if (s === undefined) return null;
    const pos = searchsortedRight(s.days, day) - 1;
    if (pos < 0 || s.days[pos] !== day) return null;
    return pos;
  }
}

/**
 * The 10 stock-selection strategies. Port of `strategies/pickers.py`.
 *
 * Three work purely from price history and are honest over any period
 * (momentum, relative_strength, random). The other seven read a *current*
 * fundamentals snapshot, so they are only trustworthy over a recent window —
 * the look-ahead caveat carried over from Python.
 *
 * PARITY NOTE — tie-breaking.
 * Python builds `(score, ticker)` tuples and calls `sort(reverse=True)`. Tuple
 * comparison is lexicographic, and `reverse=True` reverses the WHOLE
 * comparison, so equal scores break by ticker *descending* (Z before A). It is
 * easy to write this as "sort by score desc, ticker asc" and be silently wrong
 * on every tie.
 */
import { totalReturn } from "./indicators.js";
import { MT19937 } from "./mt19937.js";

/**
 * Compare `(score, ticker)` the way Python's `sort(reverse=True)` does.
 * Higher score first; on an exact tie, the lexicographically LARGER ticker
 * first.
 */
function byScoreDescTickerDesc(a, b) {
  if (a.s !== b.s) return b.s - a.s;
  if (a.t === b.t) return 0;
  return a.t > b.t ? -1 : 1;
}

/** Manual mode: hold a fixed, user-supplied basket. */
export class FixedListPicker {
  name = "manual";
  tickers;
  constructor(tickers) {
    this.tickers = [...tickers];
  }
  initialize(_ctx) {}
  select(_ctx, universe, _n) {
    const tradable = new Set(universe);
    return this.tickers.filter((t) => tradable.has(t));
  }
}

/**
 * Trend following: buy the strongest trailing-return names (default 6mo).
 *
 * `skip` drops the most recent `skip` bars from the window, so lookback=252
 * with skip=21 is the classic "12-1" momentum: the trailing year excluding the
 * latest month, which avoids the short-horizon reversal that contaminates a
 * window ending today. skip=0 is the plain trailing return.
 */
export class MomentumPicker {
  lookback;
  skip;
  name = "momentum";
  constructor(lookback = 126, skip = 0) {
    this.lookback = lookback;
    this.skip = skip;
  }
  initialize(_ctx) {}
  select(ctx, universe, n) {
    const scored = [];
    const need = this.lookback + this.skip + 1;
    for (const t of universe) {
      let closes = ctx.history(t, "Close", need);
      if (closes.length < need) continue;
      if (this.skip) closes = closes.slice(0, closes.length - this.skip);
      const r = totalReturn(closes, this.lookback);
      if (r !== null) scored.push({ s: r, t });
    }
    scored.sort(byScoreDescTickerDesc);
    return scored.slice(0, n).map((x) => x.t);
  }
}

/**
 * Relative momentum with a benchmark filter: hold only names actually beating
 * the benchmark, ranked by excess return. The filter is what distinguishes this
 * from plain momentum — ranking by (return - benchmark) alone would be
 * order-identical, since the benchmark is a constant.
 */
export class RelativeStrengthPicker {
  benchmark;
  lookback;
  name = "relative_strength";
  constructor(benchmark = "SPY", lookback = 126) {
    this.benchmark = benchmark;
    this.lookback = lookback;
  }
  initialize(_ctx) {}
  select(ctx, universe, n) {
    const bench = totalReturn(
      ctx.history(this.benchmark, "Close", this.lookback + 1),
      this.lookback,
    );
    if (bench === null) return [];
    const scored = [];
    for (const t of universe) {
      if (t === this.benchmark) continue;
      const r = totalReturn(
        ctx.history(t, "Close", this.lookback + 1),
        this.lookback,
      );
      if (r !== null && r > bench) scored.push({ s: r - bench, t });
    }
    scored.sort(byScoreDescTickerDesc);
    return scored.slice(0, n).map((x) => x.t);
  }
}

/**
 * Control baseline: pick names at random, reshuffled each rebalance.
 *
 * Uses the CPython-compatible MT19937 in `mt19937.js`, so this reproduces
 * `random.Random(seed).sample(...)` exactly rather than approximating it.
 * The RNG is constructed once per Picker instance, matching Python — the
 * stream carries across rebalances.
 */
export class RandomPicker {
  fraction;
  name = "random";
  rng;
  constructor(seed = 42, fraction = null) {
    this.fraction = fraction;
    this.rng = new MT19937(seed);
  }
  initialize(_ctx) {}
  select(_ctx, universe, n) {
    if (universe.length === 0) return [];
    // Python: round(len * fraction) if fraction else n. `fraction` of 0 is
    // falsy in Python too, so `|| null` semantics line up.
    let k = this.fraction
      ? pyRoundHalfEven(universe.length * this.fraction)
      : n;
    k = Math.max(1, Math.min(k, universe.length));
    return this.rng.sample(universe.slice(), k);
  }
}

/** Python's `round()` — banker's rounding (ties to even). */
function pyRoundHalfEven(x) {
  const f = Math.floor(x);
  const diff = x - f;
  if (diff > 0.5) return f + 1;
  if (diff < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

/**
 * Rank the universe by one fundamental column and take the top `n`.
 *
 * `ascending` true means small-is-good (P/E, P/B, market cap); false means
 * large-is-good (ROE, yield, growth, surprise). `positiveOnly` drops values
 * <= 0 before ranking (a negative P/E is not "cheap").
 *
 * TIE-BREAK CAVEAT: Python uses `Series.sort_values()`, which defaults to
 * quicksort and is therefore NOT stable. This implementation uses a stable sort
 * keyed on the snapshot's CSV row order. For columns with no duplicate values
 * the two agree exactly; `dividendYield` (110 tie groups) and `revenueGrowth`
 * (113) do have duplicates, so selection at the top-n cutoff can differ there.
 * `test/strategies.test.js` measures this against Python rather than assuming.
 */
export class FundamentalPicker {
  name;
  fund;
  field;
  ascending;
  positiveOnly;
  constructor(name, fund, field, ascending, positiveOnly) {
    this.name = name;
    this.fund = fund;
    this.field = field;
    this.ascending = ascending;
    this.positiveOnly = positiveOnly;
  }
  initialize(_ctx) {
    if (!this.fund.columns.includes(this.field)) {
      throw new Error(`fundamentals snapshot has no column ${this.field}`);
    }
  }
  select(_ctx, universe, n) {
    if (!this.fund.columns.includes(this.field)) return [];
    const inUniverse = new Set(universe);
    const rows = [];
    // Iterate in snapshot order so the stable sort reproduces pandas' pre-sort
    // arrangement (see caveat above).
    this.fund.order.forEach((t, i) => {
      const row = this.fund.rows[t];
      if (row === undefined) return;
      const v = row[this.field];
      if (v === null || v === undefined || Number.isNaN(v)) return; // dropna()
      if (!inUniverse.has(t)) return; // index.isin
      if (this.positiveOnly && !(v > 0)) return; // col[col > 0]
      rows.push({ t, v, i });
    });
    if (rows.length === 0) return [];
    const dir = this.ascending ? 1 : -1;
    rows.sort((a, b) => (a.v !== b.v ? dir * (a.v - b.v) : a.i - b.i));
    return rows.slice(0, n).map((r) => r.t);
  }
}

/** Field/direction table mirroring the Python subclasses. */
const FUNDAMENTAL_SPECS = {
  value_pe: { field: "trailingPE", ascending: true, positiveOnly: true },
  price_to_book: { field: "priceToBook", ascending: true, positiveOnly: true },
  small_cap: { field: "marketCap", ascending: true, positiveOnly: true },
  quality_roe: {
    field: "returnOnEquity",
    ascending: false,
    positiveOnly: false,
  },
  growth_revenue: {
    field: "revenueGrowth",
    ascending: false,
    positiveOnly: false,
  },
  high_dividend: {
    field: "dividendYield",
    ascending: false,
    positiveOnly: true,
  },
  earnings_surprise: {
    field: "earningsSurprisePct",
    ascending: false,
    positiveOnly: false,
  },
};
export const PRICE_ONLY_PICKERS = new Set([
  "momentum",
  "relative_strength",
  "random",
]);

/** Registry mirroring `strategies/pickers.py::PICKERS`. */
export function makePicker(id, params = {}, fundamentals = null) {
  const num = (k, d) => (params[k] === undefined ? d : Number(params[k]));
  switch (id) {
    case "momentum":
      return new MomentumPicker(num("lookback", 126), num("skip", 0));
    case "relative_strength":
      return new RelativeStrengthPicker(
        String(params.benchmark ?? "SPY"),
        num("lookback", 126),
      );
    case "random":
      return new RandomPicker(
        num("seed", 42),
        params.fraction === undefined || params.fraction === null
          ? null
          : Number(params.fraction),
      );
    default: {
      const spec = FUNDAMENTAL_SPECS[id];
      if (spec === undefined) throw new Error(`Unknown picker_id ${id}`);
      if (fundamentals === null) {
        throw new Error(`picker ${id} needs the fundamentals snapshot`);
      }
      return new FundamentalPicker(
        id,
        fundamentals,
        spec.field,
        spec.ascending,
        spec.positiveOnly,
      );
    }
  }
}

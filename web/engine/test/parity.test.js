/**
 * End-to-end parity: the TypeScript engine against the Phase 0 golden oracle.
 *
 * Runs every golden case through the ported engine, reading real data from the
 * Phase 1 binary bundle, and diffs the full result — metrics, both equity
 * curves, the trade blotter, round trips and the SPY benchmark — against the
 * JSON frozen from Python.
 *
 * Phase 3 extends this from the 4 manual cases to all 10, adding picker mode,
 * the point-in-time S&P 500 universe, and the seeded random control.
 */
import { strict as assert } from "node:assert";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import {
  Backtest,
  BuyAndHold,
  Combo,
  FixedListPicker,
  MarketData,
  alignTotals,
  clipSeries,
  dayFromIso,
  decodeCalendar,
  decodeTicker,
  decodeUniverse,
  makePicker,
  makeTaxPolicy,
  makeTimer,
  membersByCalendar,
  metricsDict,
  resultSince,
  roundTrips,
  totals,
  tradesList,
  TaxManagedCombo,
  UNIVERSE_EXCLUDE,
} from "../src/index.js";
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..");
const DATA = join(ROOT, "build", "webdata");
const GOLDEN = join(ROOT, "golden");
const BENCHMARK = "SPY";
const REL_TOL = 1e-9;
const ABS_TOL = 1e-9;
// ---------------------------------------------------------------------------
function readBuf(path) {
  const b = readFileSync(path);
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
}

const manifest = JSON.parse(readFileSync(join(DATA, "manifest.json"), "utf8"));
const calendar = decodeCalendar(readBuf(join(DATA, "calendar.bin")));
const fundamentals = JSON.parse(
  readFileSync(join(DATA, "fundamentals.json"), "utf8"),
);
const pit = JSON.parse(readFileSync(join(DATA, "sp500-pit.json"), "utf8"));

/** Lazily decoded per-ticker files (manual mode). */
const tickerCache = new Map();
function loadTicker(t) {
  let s = tickerCache.get(t);
  if (s === undefined) {
    s = decodeTicker(t, readBuf(join(DATA, "tickers", `${t}.bin`)), calendar);
    tickerCache.set(t, s);
  }
  return s;
}

/** The full-universe Close bundle (picker mode). Decoded once. */
let universeCache = null;
function loadUniverse() {
  if (universeCache === null) {
    universeCache = decodeUniverse(
      readBuf(join(DATA, "universe.bin")),
      manifest.universe.tickers,
      calendar,
    );
  }
  return universeCache;
}

/** Mirrors EngineService._resolve + run_backtest. */
function runCase(req) {
  const startDay = dayFromIso(req.start);
  const endDay = dayFromIso(req.end);
  // Warm-up: bars before the window, untraded, clipped back out of the result.
  const warmupDays = Number(req.warmup_days ?? 0) || 0;
  const dataStartDay = warmupDays ? startDay - warmupDays : startDay;
  const menu =
    Array.isArray(req.menu) && req.menu.length > 0 ? req.menu : null;
  const isManual =
    req.tickers !== undefined && req.tickers !== null && req.tickers.length > 0;
  const basket = isManual ? req.tickers : menu;
  const prices = new Map();
  let market;
  let tickersUsed = null;
  let topN;
  if (basket !== null) {
    // _manual_market: de-dup preserving order, append SPY if absent. This
    // ordering becomes the market's column order, so it must match Python.
    const wanted = [...new Set(basket)];
    const withSpy = wanted.includes(BENCHMARK)
      ? wanted
      : [...wanted, BENCHMARK];
    for (const t of withSpy) {
      const c = clipSeries(loadTicker(t), dataStartDay, endDay);
      if (c.days.length > 0) prices.set(t, c);
    }
    tickersUsed = wanted.filter((t) => prices.has(t));
    market = new MarketData(prices, null);
    topN = isManual ? Math.max(1, req.tickers.length) : (req.top_n ?? 15);
  } else {
    // _universe_market: sorted(self.available - UNIVERSE_EXCLUDE), clipped.
    const all = [...manifest.universe.tickers]
      .filter((t) => !UNIVERSE_EXCLUDE.has(t))
      .sort();
    const uni = loadUniverse();
    for (const t of all) {
      const s = uni.get(t);
      if (s === undefined) continue;
      const c = clipSeries(s, dataStartDay, endDay);
      if (c.days.length > 0) prices.set(t, c);
    }
    let members = null;
    if (req.universe === "sp500-pit") {
      // build_market computes the calendar from `prices`, which is exactly the
      // market calendar, then restricts membership to tickers we hold data for.
      const cal = new MarketData(prices, null).calendar;
      members = membersByCalendar(pit, cal, new Set(prices.keys()));
    }
    market = new MarketData(prices, members);
    topN = req.top_n ?? 15;
  }
  const policy = req.tax.enabled
    ? makeTaxPolicy(
        req.tax.short_term_rate,
        req.tax.long_term_rate,
        req.tax.long_term_days,
      )
    : null;
  // A fresh strategy per run: Combo and the pickers carry per-run state (and
  // RandomPicker carries an RNG stream), exactly as Python's `make_strat()`.
  const taxManaged = (req.trade_rule ?? "standard") === "tax_managed";
  const shortlist = !isManual && menu ? tickersUsed : null;
  const makeStrat = () => {
    const picker = isManual
      ? new FixedListPicker(req.tickers)
      : makePicker(req.picker_id, req.picker_params ?? {}, fundamentals);
    const timer = makeTimer(req.timer_id, req.timer_params ?? {});
    const inner = taxManaged
      ? new TaxManagedCombo(
          picker,
          timer,
          topN,
          req.rebalance,
          shortlist,
          req.gain_budget ?? 0.01,
          req.wash_days ?? 31,
        )
      : new Combo(picker, timer, topN, req.rebalance, shortlist);
    if (!warmupDays) return inner;
    return {
      initialize: (ctx) => inner.initialize(ctx),
      onDay: (ctx) => {
        if (ctx.day >= startDay) inner.onDay(ctx);
      },
    };
  };
  const clip = (res) => (warmupDays ? resultSince(res, startDay) : res);
  const run = (p) =>
    clip(
      new Backtest(makeStrat(), market, {
        cash: req.cash,
        commissionPct: req.commission_pct,
        slippagePct: req.slippage_pct,
        taxPolicy: p,
      }).run(),
    );
  const net = run(policy);
  const gross = policy !== null ? run(null) : net;
  let benchmark = null;
  const spy = prices.get(BENCHMARK);
  if (spy !== undefined) {
    // The benchmark covers the WINDOW, never the warm-up prefix.
    const spySeries = warmupDays ? clipSeries(spy, startDay, endDay) : spy;
    const spyMarket = new MarketData(new Map([[BENCHMARK, spySeries]]), null);
    const runSpy = (p) =>
      new Backtest(new BuyAndHold(), spyMarket, {
        cash: req.cash,
        commissionPct: req.commission_pct,
        slippagePct: req.slippage_pct,
        taxPolicy: p,
      }).run();
    const spyNet = runSpy(policy);
    const spyGross = policy !== null ? runSpy(null) : spyNet;
    const bm = {
      benchmark: BENCHMARK,
      metrics: metricsDict(spyNet),
      excess_cagr: net.cagr - spyNet.cagr,
      beats_spy: net.cagr > spyNet.cagr,
      excess_after_tax_cagr: null,
      beats_spy_after_tax: null,
    };
    if (net.taxesPaid !== null && spyNet.taxesPaid !== null) {
      bm.excess_after_tax_cagr = net.afterTaxCagr - spyNet.afterTaxCagr;
      bm.beats_spy_after_tax = net.afterTaxCagr > spyNet.afterTaxCagr;
    }
    bm.curve = {
      pretax: alignTotals(spyGross, net.equity.days),
      aftertax: alignTotals(spyNet, net.equity.days),
    };
    benchmark = bm;
  }
  const { rt, winRate } = roundTrips(net.trades);
  const metrics = { ...metricsDict(net) };
  metrics.pretax_cagr = gross.cagr;
  metrics.pretax_total_return = gross.totalReturn;
  metrics.final_value_pretax = gross.finalValue;
  metrics.tax_drag_value = gross.finalValue - net.afterTaxFinalValue;
  metrics.tax_drag_cagr = gross.cagr - net.afterTaxCagr;
  metrics.win_rate = winRate;
  metrics.n_round_trips = rt.length;
  const days = net.equity.days;
  return {
    mode: isManual ? "manual" : "picker",
    picker_id: isManual ? null : req.picker_id,
    timer_id: req.timer_id,
    universe: isManual || menu ? "all" : (req.universe ?? "all"),
    trade_rule: taxManaged ? "tax_managed" : "standard",
    period: { start: isoDay(days[0]), end: isoDay(days[days.length - 1]) },
    tickers_used: tickersUsed,
    metrics,
    equity_curve: {
      dates: Array.from(days, isoDay),
      pretax: totals(gross),
      aftertax: totals(net),
    },
    benchmark,
    trades: tradesList(net),
    round_trips: rt,
  };
}

function isoDay(day) {
  return new Date(day * 86400000).toISOString().slice(0, 10);
}
// ---------------------------------------------------------------------------
function compare(golden, actual, path, errors) {
  if (
    golden === null ||
    actual === null ||
    golden === undefined ||
    actual === undefined
  ) {
    if (golden !== actual) {
      errors.push(
        `${path}: ${JSON.stringify(actual)} != golden ${JSON.stringify(golden)}`,
      );
    }
    return;
  }
  if (Array.isArray(golden) && Array.isArray(actual)) {
    if (golden.length !== actual.length) {
      errors.push(
        `${path}: length ${actual.length} != golden ${golden.length}`,
      );
      return;
    }
    for (let i = 0; i < golden.length; i++)
      compare(golden[i], actual[i], `${path}[${i}]`, errors);
    return;
  }
  if (typeof golden === "object" && typeof actual === "object") {
    const g = golden;
    const a = actual;
    for (const k of new Set([...Object.keys(g), ...Object.keys(a)])) {
      if (!(k in g)) {
        errors.push(`${path}.${k}: unexpected in actual`);
        continue;
      }
      if (!(k in a)) {
        errors.push(`${path}.${k}: missing in actual`);
        continue;
      }
      compare(g[k], a[k], `${path}.${k}`, errors);
    }
    return;
  }
  if (typeof golden === "number" && typeof actual === "number") {
    if (golden === actual) return;
    const diff = Math.abs(golden - actual);
    if (
      diff <= ABS_TOL ||
      diff <= REL_TOL * Math.max(Math.abs(golden), Math.abs(actual))
    )
      return;
    errors.push(
      `${path}: ${actual} != golden ${golden} (diff ${diff.toExponential(3)})`,
    );
    return;
  }
  if (golden !== actual) {
    errors.push(
      `${path}: ${JSON.stringify(actual)} != golden ${JSON.stringify(golden)}`,
    );
  }
}

/** Every golden on disk — so a newly frozen case is picked up automatically. */
const CASES = readdirSync(GOLDEN)
  .filter((f) => f.endsWith(".json") && f !== "manifest.json")
  .map((f) => f.replace(/\.json$/, ""))
  .sort();
for (const id of CASES) {
  test(`parity: ${id}`, () => {
    const golden = JSON.parse(readFileSync(join(GOLDEN, `${id}.json`), "utf8"));
    const actual = runCase(golden.request);
    const errors = [];
    compare(golden.result, actual, "result", errors);
    assert.ok(
      errors.length === 0,
      `${id}: ${errors.length} mismatch(es) vs Python oracle\n` +
        errors
          .slice(0, 20)
          .map((e) => `  ${e}`)
          .join("\n") +
        (errors.length > 20 ? "\n  ..." : ""),
    );
  });
}
test("all 10 golden cases are covered", () => {
  assert.ok(
    CASES.length >= 23,
    `expected at least 23 goldens, found ${CASES.length}: ${CASES}`,
  );
});

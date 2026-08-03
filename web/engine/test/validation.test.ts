/**
 * Parity for out-of-sample validation (Phase 4).
 *
 * Runs the full combo sweep through the ported engine and diffs the resulting
 * validation payload — holdout ranking, Spearman persistence, every
 * walk-forward window, the most-picked table and the verdict — against the
 * Python oracle in `golden/validation/`.
 *
 * Also asserts that progress reporting actually reports: the sweep must emit
 * one callback per combo, monotonically, and reach 100%.
 */

import { strict as assert } from "node:assert";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";

import {
  Backtest, Combo, MarketData, clipSeries, dayFromIso, decodeCalendar,
  decodeUniverse, makePicker, makeTaxPolicy, makeTimer, membersByCalendar,
  runAllCurves, runValidation, spearman, rankdataAverage,
  type Fundamentals, type PitMembership, type Progress, type Rebalance,
  type TickerSeries,
} from "../src/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..", "..");
const DATA = join(ROOT, "build", "webdata");
const GOLDEN = join(ROOT, "golden", "validation");

const REL_TOL = 1e-9;
const ABS_TOL = 1e-9;

function readBuf(path: string): ArrayBuffer {
  const b = readFileSync(path);
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
}

const manifest = JSON.parse(readFileSync(join(DATA, "manifest.json"), "utf8"));
const calendar = decodeCalendar(readBuf(join(DATA, "calendar.bin")));
const fundamentals: Fundamentals = JSON.parse(
  readFileSync(join(DATA, "fundamentals.json"), "utf8"),
);
const pit: PitMembership = JSON.parse(readFileSync(join(DATA, "sp500-pit.json"), "utf8"));

let universeCache: Map<string, TickerSeries> | null = null;
function loadUniverse(): Map<string, TickerSeries> {
  if (universeCache === null) {
    universeCache = decodeUniverse(
      readBuf(join(DATA, "universe.bin")), manifest.universe.tickers, calendar,
    );
  }
  return universeCache;
}

// ---------------------------------------------------------------------------
function compare(golden: unknown, actual: unknown, path: string, errors: string[]): void {
  if (golden === null || actual === null || golden === undefined || actual === undefined) {
    if (golden !== actual) {
      errors.push(`${path}: ${JSON.stringify(actual)} != golden ${JSON.stringify(golden)}`);
    }
    return;
  }
  if (Array.isArray(golden) && Array.isArray(actual)) {
    if (golden.length !== actual.length) {
      errors.push(`${path}: length ${actual.length} != golden ${golden.length}`);
      return;
    }
    for (let i = 0; i < golden.length; i++) compare(golden[i], actual[i], `${path}[${i}]`, errors);
    return;
  }
  if (typeof golden === "object" && typeof actual === "object") {
    const g = golden as Record<string, unknown>;
    const a = actual as Record<string, unknown>;
    for (const k of new Set([...Object.keys(g), ...Object.keys(a)])) {
      if (!(k in g)) { errors.push(`${path}.${k}: unexpected in actual`); continue; }
      if (!(k in a)) { errors.push(`${path}.${k}: missing in actual`); continue; }
      compare(g[k], a[k], `${path}.${k}`, errors);
    }
    return;
  }
  if (typeof golden === "number" && typeof actual === "number") {
    if (golden === actual) return;
    const diff = Math.abs(golden - actual);
    if (diff <= ABS_TOL || diff <= REL_TOL * Math.max(Math.abs(golden), Math.abs(actual))) return;
    errors.push(`${path}: ${actual} != golden ${golden} (diff ${diff.toExponential(3)})`);
    return;
  }
  if (golden !== actual) {
    errors.push(`${path}: ${JSON.stringify(actual)} != golden ${JSON.stringify(golden)}`);
  }
}

// ---------------------------------------------------------------------------
interface Cfg {
  picker_id: string;
  picker_params: Record<string, never>;
  timer_id: string;
  timer_params: Record<string, number>;
  top_n: number;
  rebalance: Rebalance;
  universe: "all" | "sp500-pit";
  start: string;
  end: string;
  commission_pct: number;
  slippage_pct: number;
  tax: {
    enabled: boolean; short_term_rate: number;
    long_term_rate: number; long_term_days: number;
  };
}

/** Build the universe market the sweep runs on. */
function buildMarket(cfg: Cfg, universe: "all" | "sp500-pit") {
  const startDay = dayFromIso(cfg.start);
  const endDay = dayFromIso(cfg.end);
  const prices = new Map<string, TickerSeries>();
  const uni = loadUniverse();
  for (const t of [...(manifest.universe.tickers as string[])].sort()) {
    const s = uni.get(t);
    if (s === undefined) continue;
    const c = clipSeries(s, startDay, endDay);
    if (c.days.length > 0) prices.set(t, c);
  }
  let members: Array<Set<string>> | null = null;
  if (universe === "sp500-pit") {
    const cal = new MarketData(prices, null).calendar;
    members = membersByCalendar(pit, cal, new Set(prices.keys()));
  }
  const market = new MarketData(prices, members);
  const spy = prices.get("SPY");
  const spyMarket = spy === undefined ? null : new MarketData(new Map([["SPY", spy]]), null);
  return { market, spyMarket };
}

const CASES = ["validate_price_only", "validate_all_pickers"];

for (const id of CASES) {
  test(`validation parity: ${id}`, { timeout: 1_800_000 }, async () => {
    const path = join(GOLDEN, `${id}.json`);
    assert.ok(existsSync(path), `missing ${path} — run tools/gen_validation_golden.py`);
    const golden = JSON.parse(readFileSync(path, "utf8"));
    const cfg = golden.config as Cfg;
    const p = golden.params;

    // run_all_curves uses cfg.universe for picker mode.
    const { market, spyMarket } = buildMarket(cfg, cfg.universe);
    const policy = makeTaxPolicy(
      cfg.tax.enabled ? cfg.tax.short_term_rate : 0.35,
      cfg.tax.enabled ? cfg.tax.long_term_rate : 0.15,
      365,
    );

    // ---- progress instrumentation ----
    const seen: Progress[] = [];
    const sweep = await runAllCurves(
      {
        market, spyMarket, cash: 100_000.0,
        commissionPct: cfg.commission_pct, slippagePct: cfg.slippage_pct,
        policy, priceOnly: p.price_only as boolean, fundamentals,
      },
      (pr) => seen.push(pr),
    );

    const expectedCombos = (p.price_only ? 3 : 10) * 10;
    assert.equal(sweep.curves.size, expectedCombos, "combo count");
    assert.equal(seen.length, expectedCombos, "one progress callback per combo");
    for (let i = 0; i < seen.length; i++) {
      assert.equal(seen[i].completed, i + 1, `progress monotonic at ${i}`);
      assert.equal(seen[i].total, expectedCombos, "progress total");
    }
    assert.equal(seen[seen.length - 1].completed, seen[seen.length - 1].total, "reaches 100%");

    // ---- the user's exact configured combo (net of tax), on the same market ----
    const targetRes = new Backtest(
      new Combo(
        makePicker(cfg.picker_id, cfg.picker_params, fundamentals),
        makeTimer(cfg.timer_id, cfg.timer_params),
        cfg.top_n,
        cfg.rebalance,
      ),
      market,
      {
        cash: 100_000.0, commissionPct: cfg.commission_pct,
        slippagePct: cfg.slippage_pct,
        taxPolicy: cfg.tax.enabled
          ? makeTaxPolicy(cfg.tax.short_term_rate, cfg.tax.long_term_rate, cfg.tax.long_term_days)
          : null,
      },
    ).run();

    const actual = runValidation({
      sweep,
      targetDays: targetRes.equity.days,
      targetTotals: targetRes.equity.total,
      split: p.split as string | null,
      trainYears: p.train_years as number,
      stepYears: p.step_years as number,
      priceOnly: p.price_only as boolean,
    });

    const errors: string[] = [];
    compare(golden.result, actual, "result", errors);
    assert.ok(
      errors.length === 0,
      `${id}: ${errors.length} mismatch(es) vs Python oracle\n` +
        errors.slice(0, 20).map((e) => `  ${e}`).join("\n") +
        (errors.length > 20 ? "\n  ..." : ""),
    );
  });
}

// ---------------------------------------------------------------------------
test("spearman matches pandas/scipy, including ties", () => {
  const fx = JSON.parse(readFileSync(join(GOLDEN, "spearman.json"), "utf8"));
  for (const c of fx.cases) {
    const got = spearman(c.a, c.b);
    if (c.spearman === null) {
      assert.ok(!Number.isFinite(got), `${c.name}: expected non-finite, got ${got}`);
    } else {
      assert.ok(
        Math.abs(got - c.spearman) <= 1e-12 * Math.max(1, Math.abs(c.spearman)),
        `${c.name}: ${got} vs ${c.spearman}`,
      );
    }
  }
});

test("the sweep yields the event loop, so a progress UI can actually paint",
  { timeout: 900_000 }, async () => {
    // Firing a progress callback is not the same as being responsive: if the
    // sweep never returns to the event loop, the callback fires but no UI
    // update, timer or input event can run until the whole thing finishes.
    // This asserts the loop genuinely interleaves, by checking an independent
    // timer makes progress *while* the sweep runs.
    const cfg = {
      start: "2020-01-01", end: "2021-12-31", universe: "all" as const,
      commission_pct: 0.0005, slippage_pct: 0.0005,
    };
    const { market, spyMarket } = buildMarket(cfg as unknown as Cfg, "all");

    let ticks = 0;
    const timer = setInterval(() => { ticks++; }, 1);
    let combos = 0;
    try {
      await runAllCurves(
        {
          market, spyMarket, cash: 100_000.0,
          commissionPct: cfg.commission_pct, slippagePct: cfg.slippage_pct,
          policy: makeTaxPolicy(0.35, 0.15, 365), priceOnly: true, fundamentals,
        },
        () => { combos++; },
      );
    } finally {
      clearInterval(timer);
    }

    assert.equal(combos, 30, "sweep ran all combos");
    assert.ok(
      ticks >= 10,
      `event loop was starved: an independent 1ms timer fired only ${ticks} ` +
      `times across ${combos} combos. The sweep is not yielding.`,
    );
  });

test("rankdataAverage shares ranks across ties", () => {
  // scipy.stats.rankdata([1,2,2,3]) -> [1, 2.5, 2.5, 4]
  assert.deepEqual(rankdataAverage([1, 2, 2, 3]), [1, 2.5, 2.5, 4]);
  assert.deepEqual(rankdataAverage([5, 5, 5]), [2, 2, 2]);
  assert.deepEqual(rankdataAverage([3, 1, 2]), [3, 1, 2]);
});

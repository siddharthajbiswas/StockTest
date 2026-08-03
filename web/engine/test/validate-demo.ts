/**
 * Live demo of the validation sweep with progress reporting.
 *
 * Not a test — a runnable check that the progress stream is usable for a real
 * UI, and a convenient place to measure how long the heavy path actually takes
 * in JS versus Python.
 *
 *   node dist/test/validate-demo.js            # 30 combos (price-only)
 *   node dist/test/validate-demo.js --all      # 100 combos
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  Backtest, Combo, MarketData, clipSeries, dayFromIso, decodeCalendar,
  decodeUniverse, makePicker, makeTaxPolicy, makeTimer, membersByCalendar,
  runAllCurves, runValidation,
  type Fundamentals, type PitMembership, type Progress, type TickerSeries,
} from "../src/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..", "..");
const DATA = join(ROOT, "build", "webdata");

function readBuf(p: string): ArrayBuffer {
  const b = readFileSync(p);
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
}

const priceOnly = !process.argv.includes("--all");
const START = "2016-01-01";
const END = "2021-12-31";

const manifest = JSON.parse(readFileSync(join(DATA, "manifest.json"), "utf8"));
const calendar = decodeCalendar(readBuf(join(DATA, "calendar.bin")));
const fundamentals: Fundamentals = JSON.parse(
  readFileSync(join(DATA, "fundamentals.json"), "utf8"),
);
const pit: PitMembership = JSON.parse(readFileSync(join(DATA, "sp500-pit.json"), "utf8"));

const t0 = Date.now();
const uni = decodeUniverse(
  readBuf(join(DATA, "universe.bin")), manifest.universe.tickers, calendar,
);
const decodeMs = Date.now() - t0;

const startDay = dayFromIso(START);
const endDay = dayFromIso(END);
const prices = new Map<string, TickerSeries>();
for (const t of [...(manifest.universe.tickers as string[])].sort()) {
  const s = uni.get(t);
  if (s === undefined) continue;
  const c = clipSeries(s, startDay, endDay);
  if (c.days.length > 0) prices.set(t, c);
}
const cal0 = new MarketData(prices, null).calendar;
const members = membersByCalendar(pit, cal0, new Set(prices.keys()));
const market = new MarketData(prices, members);
const spy = prices.get("SPY")!;
const spyMarket = new MarketData(new Map([["SPY", spy]]), null);
const buildMs = Date.now() - t0 - decodeMs;

function bar(p: Progress): string {
  const frac = p.completed / p.total;
  const width = 32;
  const filled = Math.round(frac * width);
  const eta = p.completed > 0
    ? ((p.elapsedMs / p.completed) * (p.total - p.completed)) / 1000
    : 0;
  return `[${"#".repeat(filled)}${".".repeat(width - filled)}] ` +
    `${String(p.completed).padStart(3)}/${p.total}  ` +
    `${(frac * 100).toFixed(0).padStart(3)}%  ` +
    `eta ${eta.toFixed(0).padStart(3)}s  ${p.label}`;
}

console.log(`StockTest validation sweep — ${priceOnly ? 30 : 100} combos, ${START}..${END}`);
console.log(`decode universe.bin: ${decodeMs} ms   build market: ${buildMs} ms`);
console.log(`${prices.size} tickers, ${market.n} trading days\n`);

const sweepStart = Date.now();
const sweep = await runAllCurves(
  {
    market, spyMarket, cash: 100_000.0, commissionPct: 0.0005,
    slippagePct: 0.0005, policy: makeTaxPolicy(0.35, 0.15, 365),
    priceOnly, fundamentals,
  },
  (p) => {
    process.stdout.write("\r" + bar(p).padEnd(110));
  },
);
const sweepMs = Date.now() - sweepStart;
console.log(`\n\nsweep: ${(sweepMs / 1000).toFixed(1)}s ` +
  `(${(sweepMs / sweep.curves.size).toFixed(0)} ms/combo)`);

const target = new Backtest(
  new Combo(
    makePicker("momentum", {}, fundamentals), makeTimer("ma_cross", {}), 15, "M",
  ),
  market,
  {
    cash: 100_000.0, commissionPct: 0.0005, slippagePct: 0.0005,
    taxPolicy: makeTaxPolicy(0.35, 0.15, 365),
  },
).run();

const res = runValidation({
  sweep,
  targetDays: target.equity.days,
  targetTotals: target.equity.total,
  split: null,
  trainYears: 3,
  stepYears: 1,
  priceOnly,
});

console.log(`\nholdout   split ${res.holdout.split}  spearman ` +
  `${res.holdout.spearman?.toFixed(3)}  your rank ` +
  `${res.holdout.your_train_rank} -> ${res.holdout.your_test_rank} of ${res.holdout.n_ranked}`);
console.log(`walkfwd   ${res.walkforward.windows.length} windows  adaptive ` +
  `${((res.walkforward.adaptive_oos_cagr ?? 0) * 100).toFixed(1)}%  vs SPY ` +
  `${((res.walkforward.spy_oos_cagr ?? 0) * 100).toFixed(1)}%`);
for (const w of res.walkforward.windows) {
  console.log(`  ${w.start}..${w.end}  ${w.picked.padEnd(28)} ` +
    `${(((w.combo_return ?? 0)) * 100).toFixed(1).padStart(7)}%  ` +
    `spy ${(((w.spy_return ?? 0)) * 100).toFixed(1).padStart(6)}%`);
}
console.log(`verdict   ${res.verdict.level.toUpperCase()} (score ${res.verdict.score}/3)`);
console.log(`\ntotal wall clock: ${((Date.now() - t0) / 1000).toFixed(1)}s`);

/**
 * Out-of-sample validation. Port of `reference/oos_validation.py`.
 *
 * Two independent checks over the same run-once equity curves:
 *
 *   holdout      Split the span, rank combos by TRAIN return, then look at how
 *                those same combos do on the untouched TEST window. Reports
 *                rank persistence (Spearman) and the single non-cherry-picked
 *                out-of-sample result.
 *   walkforward  Roll through time: each step pick the best trailing-window
 *                combo, then earn the next step with it. Chain those
 *                out-of-sample chunks into one track record versus SPY.
 *
 * Honesty caveat carried over from Python: the walk-forward "switch to this
 * year's pick" approximation ignores the tax cost of switching baskets between
 * windows, so it slightly flatters the adaptive strategy.
 */

import { yearOfDay, isoOfDay } from "./result.js";
import { dayFromIso } from "./data.js";
import {
  comboLabel, getCurve, reindexFfillBfill, windowCagr, windowReturn,
  type ComboKey, type ProgressFn, type SweepResult,
} from "./walkforward.js";

/** JSON-safe: non-finite becomes null, as `_finite` does. */
function finite(x: number | null): number | null {
  if (x === null) return null;
  return Number.isFinite(x) ? x : null;
}

/**
 * Average ranks with ties shared, as `scipy.stats.rankdata` does — which is
 * what pandas' `corr(method="spearman")` uses under the hood. Ordinal ranks
 * would agree on distinct values but silently diverge whenever two combos post
 * exactly the same window CAGR.
 */
export function rankdataAverage(x: number[]): number[] {
  const idx = x.map((v, i) => i).sort((a, b) => (x[a] - x[b]) || (a - b));
  const out = new Array<number>(x.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && x[idx[j + 1]] === x[idx[i]]) j++;
    // Ranks are 1-based; tied entries all take the group's mean rank.
    const avg = (i + j + 2) / 2;
    for (let k = i; k <= j; k++) out[idx[k]] = avg;
    i = j + 1;
  }
  return out;
}

/** Spearman rank correlation: Pearson over average ranks. */
export function spearman(a: number[], b: number[]): number {
  const n = a.length;
  if (n < 2) return NaN;
  const ra = rankdataAverage(a);
  const rb = rankdataAverage(b);
  let ma = 0, mb = 0;
  for (let i = 0; i < n; i++) { ma += ra[i]; mb += rb[i]; }
  ma /= n; mb /= n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    const u = ra[i] - ma;
    const v = rb[i] - mb;
    num += u * v; da += u * u; db += v * v;
  }
  if (da === 0 || db === 0) return NaN;
  return num / Math.sqrt(da * db);
}

/** Python's `round(x, 1)` for the span-years display value. */
function round1(x: number): number {
  const scaled = x * 10;
  const r = Math.round(scaled);
  // Ties-to-even, matching Python; span_years is derived from a day count so an
  // exact .05 tie is possible.
  if (Math.abs(scaled - Math.trunc(scaled)) === 0.5) {
    const f = Math.floor(scaled);
    return (f % 2 === 0 ? f : f + 1) / 10;
  }
  return r / 10;
}

/** Day number for Jan 1 of a year. */
function jan1(year: number): number {
  return Math.floor(Date.UTC(year, 0, 1) / 86400000);
}

export interface HoldoutResult {
  split: string;
  spearman: number | null;
  n_ranked: number;
  spy_train_cagr: number | null;
  spy_test_cagr: number | null;
  your_train_cagr: number | null;
  your_test_cagr: number | null;
  your_train_rank: number;
  your_test_rank: number;
  beats_spy_test: boolean;
  rank_held: boolean;
}

export function holdout(
  sweep: SweepResult,
  target: Float64Array,
  split: string | null,
): HoldoutResult {
  const days = sweep.days;
  const first = days[0];
  const last = days[days.length - 1];
  // Python: dates[0] + (dates[-1] - dates[0]) / 2, then truncated to a date.
  // A half-day remainder floors away, so this is integer division.
  const splitDay = split === null ? first + Math.floor((last - first) / 2) : dayFromIso(split);

  const train: number[] = [];
  const test: number[] = [];
  for (const key of sweep.comboKeys) {
    const c = getCurve(sweep, key)!;
    const a = windowCagr(days, c, first, splitDay);
    const b = windowCagr(days, c, splitDay, last);
    if (!Number.isNaN(a) && !Number.isNaN(b)) { train.push(a); test.push(b); }
  }
  const sp = train.length >= 3 ? finite(spearman(train, test)) : null;

  const tgtTrain = windowCagr(days, target, first, splitDay);
  const tgtTest = windowCagr(days, target, splitDay, last);
  const spyTrain = windowCagr(days, sweep.spy, first, splitDay);
  const spyTest = windowCagr(days, sweep.spy, splitDay, last);

  const n = test.length;
  // NaN comparisons are false in both languages, so a NaN target ranks 1st.
  const trainRank = 1 + train.reduce((acc, v) => acc + (v > tgtTrain ? 1 : 0), 0);
  const testRank = 1 + test.reduce((acc, v) => acc + (v > tgtTest ? 1 : 0), 0);

  return {
    split: isoOfDay(splitDay),
    spearman: sp,
    n_ranked: n,
    spy_train_cagr: finite(spyTrain),
    spy_test_cagr: finite(spyTest),
    your_train_cagr: finite(tgtTrain),
    your_test_cagr: finite(tgtTest),
    your_train_rank: trainRank,
    your_test_rank: testRank,
    beats_spy_test: !Number.isNaN(tgtTest) && !Number.isNaN(spyTest) && tgtTest > spyTest,
    rank_held: n > 0 && testRank <= Math.max(1, Math.ceil(n / 3)),
  };
}

export interface WalkWindow {
  start: string;
  end: string;
  picked: string;
  combo_return: number | null;
  spy_return: number | null;
}

export interface WalkforwardResult {
  has_windows: boolean;
  adaptive_oos_cagr: number | null;
  spy_oos_cagr: number | null;
  adaptive_beats_spy: boolean;
  your_oos_cagr: number | null;
  your_oos_beats_spy: boolean;
  windows: WalkWindow[];
  most_picked: Array<{ combo: string; count: number }>;
}

export function walkforward(
  sweep: SweepResult,
  target: Float64Array,
  trainYears: number,
  stepYears: number,
  onProgress?: ProgressFn,
): WalkforwardResult {
  const days = sweep.days;
  const last = days[days.length - 1];
  const startY = yearOfDay(days[0]) + trainYears;
  const endY = yearOfDay(last);

  let oosGrowth = 1.0;
  let spyGrowth = 1.0;
  const picks: string[] = [];
  const windows: WalkWindow[] = [];
  const totalSteps = Math.max(0, Math.ceil((endY - startY) / stepYears));
  const t0 = Date.now();
  let step = 0;

  for (let y = startY; y < endY; y += stepYears) {
    const trStart = jan1(y - trainYears);
    const trEnd = jan1(y);
    const teEnd = jan1(Math.min(y + stepYears, endY + 1));

    // Python builds (value, combo) pairs then takes max(). Python's max returns
    // the FIRST maximal element, so ties resolve to registry order — a plain
    // reduce with `>` reproduces that; `>=` would not.
    let best: ComboKey | null = null;
    let bestVal = -Infinity;
    for (const key of sweep.comboKeys) {
      const v = windowCagr(days, getCurve(sweep, key)!, trStart, trEnd);
      if (Number.isNaN(v)) continue;
      if (best === null || v > bestVal) { best = key; bestVal = v; }
    }
    step++;
    if (best === null) continue;

    const r = windowReturn(days, getCurve(sweep, best)!, trEnd, teEnd);
    const sr = windowReturn(days, sweep.spy, trEnd, teEnd);
    if (!Number.isNaN(r) && !Number.isNaN(sr)) {
      oosGrowth *= 1 + r;
      spyGrowth *= 1 + sr;
      picks.push(comboLabel(best));
      windows.push({
        start: isoOfDay(trEnd),
        end: isoOfDay(teEnd),
        picked: comboLabel(best),
        combo_return: finite(r),
        spy_return: finite(sr),
      });
    }
    onProgress?.({
      phase: "walkforward",
      completed: step,
      total: totalSteps,
      label: `${isoOfDay(trEnd)}..${isoOfDay(teEnd)}`,
      elapsedMs: Date.now() - t0,
    });
  }

  const nYears = (last - jan1(startY)) / 365.25;
  const adaptiveCagr = nYears > 0 ? Math.pow(oosGrowth, 1 / nYears) - 1 : NaN;
  const spyCagr = nYears > 0 ? Math.pow(spyGrowth, 1 / nYears) - 1 : NaN;

  const oosStart = jan1(startY);
  const yourOos = windowCagr(days, target, oosStart, last);
  const spyOos = windowCagr(days, sweep.spy, oosStart, last);

  // Counter.most_common(3): sorted by count descending, ties keeping first-seen
  // order (heapq.nlargest is stable).
  const counts = new Map<string, number>();
  for (const p of picks) counts.set(p, (counts.get(p) ?? 0) + 1);
  const mostPicked = [...counts.entries()]
    .map(([combo, count], i) => ({ combo, count, i }))
    .sort((a, b) => (b.count - a.count) || (a.i - b.i))
    .slice(0, 3)
    .map(({ combo, count }) => ({ combo, count }));

  return {
    has_windows: windows.length > 0,
    adaptive_oos_cagr: finite(adaptiveCagr),
    spy_oos_cagr: finite(spyCagr),
    adaptive_beats_spy: !Number.isNaN(adaptiveCagr) && adaptiveCagr > spyCagr,
    your_oos_cagr: finite(yourOos),
    your_oos_beats_spy:
      !Number.isNaN(yourOos) && !Number.isNaN(spyOos) && yourOos > spyOos,
    windows,
    most_picked: mostPicked,
  };
}

export interface Verdict {
  level: "held" | "mixed" | "failed";
  score: number;
  beats_spy_out_of_sample: boolean;
  rank_held: boolean;
  walkforward_beats_spy: boolean;
}

export function verdict(h: HoldoutResult, w: WalkforwardResult): Verdict {
  const signals = [h.beats_spy_test, h.rank_held, w.your_oos_beats_spy];
  const score = signals.reduce((a, s) => a + (s ? 1 : 0), 0);
  const level = score >= 2 ? "held" : score === 0 ? "failed" : "mixed";
  return {
    level,
    score,
    beats_spy_out_of_sample: h.beats_spy_test,
    rank_held: h.rank_held,
    walkforward_beats_spy: w.your_oos_beats_spy,
  };
}

export interface ValidationResult {
  meta: {
    n_baseline_combos: number;
    price_only: boolean;
    period: { start: string; end: string };
    span_years: number;
    train_years: number;
    step_years: number;
  };
  holdout: HoldoutResult;
  walkforward: WalkforwardResult;
  verdict: Verdict;
}

export interface ValidationInput {
  sweep: SweepResult;
  /** The user's exact configured combo, from a separate net-of-tax run. */
  targetDays: Int32Array;
  targetTotals: Float64Array;
  split?: string | null;
  trainYears?: number;
  stepYears?: number;
  priceOnly: boolean;
}

/** Assemble the full validation payload from an already-computed sweep. */
export function runValidation(input: ValidationInput, onProgress?: ProgressFn): ValidationResult {
  const { sweep, priceOnly } = input;
  const days = sweep.days;
  const target = reindexFfillBfill(input.targetDays, input.targetTotals, days);

  const spanYears = (days[days.length - 1] - days[0]) / 365.25;
  let trainYears = input.trainYears ?? 3;
  trainYears = spanYears > 1
    ? Math.max(1, Math.min(trainYears, Math.trunc(spanYears) - 1))
    : 1;
  const stepYears = input.stepYears ?? 1;

  const h = holdout(sweep, target, input.split ?? null);
  const w = walkforward(sweep, target, trainYears, stepYears, onProgress);

  onProgress?.({
    phase: "done", completed: 1, total: 1, label: "validation complete", elapsedMs: 0,
  });

  return {
    meta: {
      n_baseline_combos: sweep.curves.size,
      price_only: priceOnly,
      period: { start: isoOfDay(days[0]), end: isoOfDay(days[days.length - 1]) },
      span_years: round1(spanYears),
      train_years: trainYears,
      step_years: stepYears,
    },
    holdout: h,
    walkforward: w,
    verdict: verdict(h, w),
  };
}

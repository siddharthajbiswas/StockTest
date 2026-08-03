/**
 * Technical indicators over a close series. Port of `backtester/indicators.py`.
 *
 * Every function takes closes oldest -> newest, already clipped to "up to
 * today" by the engine, and returns the latest value or `null` when there is
 * not enough history. Pure and stateless, so pickers and timers can share them
 * without look-ahead concerns.
 *
 * All reductions go through `numeric.ts`; see that file for why a naive sum is
 * not acceptable here.
 */

import { ewmMean, ewmSpanAlpha, nmean, nstd, pctChange } from "./numeric.js";

/** Simple moving average of the last `window` closes. */
export function sma(closes: ArrayLike<number>, window: number): number | null {
  if (closes.length < window) return null;
  const start = closes.length - window;
  const w = new Float64Array(window);
  for (let i = 0; i < window; i++) w[i] = closes[start + i];
  return nmean(w);
}

/** Relative Strength Index using Wilder's smoothing. */
export function wilderRsi(closes: ArrayLike<number>, period = 14): number | null {
  if (closes.length < period + 1) return null;
  const n = closes.length;
  // deltas = closes.diff().dropna() -> n-1 values
  const gains = new Float64Array(n - 1);
  const losses = new Float64Array(n - 1);
  for (let i = 1; i < n; i++) {
    const d = closes[i] - closes[i - 1];
    // Series.clip(lower=0) and (-d).clip(lower=0)
    gains[i - 1] = d > 0 ? d : 0.0;
    losses[i - 1] = -d > 0 ? -d : 0.0;
  }
  const alpha = 1.0 / period;
  const avgGain = ewmMean(gains, alpha);
  const avgLoss = ewmMean(losses, alpha);
  const g = avgGain[avgGain.length - 1];
  const l = avgLoss[avgLoss.length - 1];
  if (l === 0) return 100.0;
  const rs = g / l;
  return 100.0 - 100.0 / (1.0 + rs);
}

/** (macdLine, signalLine) latest values, or null if the series is too short. */
export function macd(
  closes: ArrayLike<number>,
  fast = 12,
  slow = 26,
  signal = 9,
): [number, number] | null {
  if (closes.length < slow + signal) return null;
  const emaFast = ewmMean(closes, ewmSpanAlpha(fast));
  const emaSlow = ewmMean(closes, ewmSpanAlpha(slow));
  const n = closes.length;
  const macdLine = new Float64Array(n);
  for (let i = 0; i < n; i++) macdLine[i] = emaFast[i] - emaSlow[i];
  const signalLine = ewmMean(macdLine, ewmSpanAlpha(signal));
  return [macdLine[n - 1], signalLine[n - 1]];
}

/** (lower, middle, upper) latest Bollinger band values, or null. */
export function bollinger(
  closes: ArrayLike<number>,
  window = 20,
  k = 2.0,
): [number, number, number] | null {
  if (closes.length < window) return null;
  const start = closes.length - window;
  const w = new Float64Array(window);
  for (let i = 0; i < window; i++) w[i] = closes[start + i];
  const mid = nmean(w);
  const sd = nstd(w, 0);
  return [mid - k * sd, mid, mid + k * sd];
}

/** Simple return over the last `lookback` bars: P_t / P_{t-lookback} - 1. */
export function totalReturn(closes: ArrayLike<number>, lookback: number): number | null {
  if (closes.length < lookback + 1) return null;
  const past = closes[closes.length - lookback - 1];
  if (past <= 0) return null;
  return closes[closes.length - 1] / past - 1.0;
}

/** Annualized stdev of daily returns over `window` bars. */
export function realizedVol(closes: ArrayLike<number>, window = 20): number | null {
  if (closes.length < window + 1) return null;
  const start = closes.length - window - 1;
  const slice = new Float64Array(closes.length - start);
  for (let i = 0; i < slice.length; i++) slice[i] = closes[start + i];
  const rets = pctChange(slice);
  if (rets.length === 0) return null;
  return nstd(rets, 0) * Math.sqrt(252);
}

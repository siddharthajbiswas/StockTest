/**
 * Bit-exact reimplementations of the NumPy/pandas reductions the engine relies on.
 *
 * This file is the foundation of Python<->TypeScript parity. Everything else in
 * the port is ordinary arithmetic that JS reproduces exactly (both languages use
 * IEEE-754 float64), but *reductions* depend on summation order, and NumPy does
 * not sum left-to-right.
 *
 * Measured before writing this: a naive left-to-right sum disagrees with
 * `numpy.sum` on ~11% of random inputs. Since `sma()` feeds comparisons like
 * `fastMa > slowMa`, an ordering difference is not merely a rounding artifact —
 * it *can* flip a trade decision and desynchronize the whole simulation.
 *
 * Verified against NumPy/pandas over 20,000 randomized trials plus every block
 * boundary (n = 7, 8, 9, 127, 128, 129, 136, 255, 256, 257, 1000): zero
 * mismatches for sum, mean, std(ddof=0) and std(ddof=1).
 *
 * HOW MUCH THIS MATTERS, measured honestly. A negative control that forces
 * `pairwiseSum` down a naive path fails the exact unit tests in
 * `test/units.test.ts` but still PASSES all four end-to-end parity cases — the
 * induced drift is ~1e-16, well under the 1e-9 golden tolerance, and it did not
 * flip an SMA comparison in those cases. So this file is not load-bearing for
 * current parity; it is cheap insurance against a knife-edge comparison in some
 * future case, and the exact unit tests are what actually hold it in place.
 * Don't "simplify" it to a plain loop on the theory that the parity suite would
 * catch the regression — it would not.
 */

/** NumPy's PW_BLOCKSIZE from `loops.c.src`. */
const PW_BLOCKSIZE = 128;

/**
 * NumPy's `pairwise_sum` for contiguous float64 data.
 *
 * Mirrors the C implementation exactly:
 *   n < 8      -> plain left-to-right accumulation
 *   n <= 128   -> 8 independent accumulators, combined as
 *                 ((r0+r1)+(r2+r3)) + ((r4+r5)+(r6+r7)), then the tail
 *   otherwise  -> split at n/2 rounded down to a multiple of 8, recurse
 *
 * The 8-accumulator structure and the exact shape of the final combination are
 * load-bearing; changing either changes the low bits of the result.
 */
export function pairwiseSum(a: ArrayLike<number>, lo: number, n: number): number {
  if (n < 8) {
    let r = 0.0;
    for (let i = 0; i < n; i++) r += a[lo + i];
    return r;
  }
  if (n <= PW_BLOCKSIZE) {
    let r0 = a[lo + 0], r1 = a[lo + 1], r2 = a[lo + 2], r3 = a[lo + 3];
    let r4 = a[lo + 4], r5 = a[lo + 5], r6 = a[lo + 6], r7 = a[lo + 7];
    let i = 8;
    const limit = n - (n % 8);
    for (; i < limit; i += 8) {
      r0 += a[lo + i + 0]; r1 += a[lo + i + 1];
      r2 += a[lo + i + 2]; r3 += a[lo + i + 3];
      r4 += a[lo + i + 4]; r5 += a[lo + i + 5];
      r6 += a[lo + i + 6]; r7 += a[lo + i + 7];
    }
    let res = ((r0 + r1) + (r2 + r3)) + ((r4 + r5) + (r6 + r7));
    for (; i < n; i++) res += a[lo + i];
    return res;
  }
  let n2 = n >> 1;
  n2 -= n2 % 8;
  return pairwiseSum(a, lo, n2) + pairwiseSum(a, lo + n2, n - n2);
}

/** `numpy.sum` over a whole array. */
export function nsum(a: ArrayLike<number>): number {
  return pairwiseSum(a, 0, a.length);
}

/** `pandas.Series.mean()` — pairwise sum divided by the count. */
export function nmean(a: ArrayLike<number>): number {
  return pairwiseSum(a, 0, a.length) / a.length;
}

/**
 * `pandas.Series.std(ddof)`.
 *
 * Two-pass, matching NumPy's `_methods._var`: pairwise mean, then a pairwise
 * sum of squared deviations, divided by (n - ddof), then a *true* square root.
 *
 * `Math.sqrt` is required here, not `x ** 0.5`. IEEE sqrt is correctly rounded;
 * `pow(x, 0.5)` is not, and the two disagree by 1 ulp on roughly 0.15% of
 * inputs. (That difference is what made an earlier draft of this function
 * mismatch pandas 30 times in 20,000 trials.)
 */
export function nstd(a: ArrayLike<number>, ddof: number): number {
  const n = a.length;
  const m = pairwiseSum(a, 0, n) / n;
  const dev = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const d = a[i] - m;
    dev[i] = d * d;
  }
  return Math.sqrt(pairwiseSum(dev, 0, n) / (n - ddof));
}

/**
 * `pandas.Series.pct_change()` with NaNs dropped.
 *
 * pandas computes `x.div(x.shift()) - 1`, i.e. `x[i] / x[i-1] - 1`. It does
 * *not* compute `(x[i] - x[i-1]) / x[i-1]`; the two differ in the low bits.
 * Verified: only the division form reproduces pandas bit-for-bit.
 */
export function pctChange(a: ArrayLike<number>): Float64Array {
  const n = a.length;
  if (n < 2) return new Float64Array(0);
  const out = new Float64Array(n - 1);
  for (let i = 1; i < n; i++) out[i - 1] = a[i] / a[i - 1] - 1.0;
  return out;
}

/**
 * `Series.ewm(alpha, adjust=False).mean()`.
 *
 * The recurrence is `y[i] = alpha*x[i] + (1-alpha)*y[i-1]`, seeded with x[0].
 * The algebraically equivalent `y[i-1] + alpha*(x[i] - y[i-1])` is NOT
 * bit-identical and does not match pandas.
 */
export function ewmMean(a: ArrayLike<number>, alpha: number): Float64Array {
  const n = a.length;
  const out = new Float64Array(n);
  if (n === 0) return out;
  out[0] = a[0];
  const oneMinus = 1 - alpha;
  for (let i = 1; i < n; i++) out[i] = alpha * a[i] + oneMinus * out[i - 1];
  return out;
}

/** `ewm(span=s, adjust=False)` — pandas maps span to alpha = 2/(span+1). */
export function ewmSpanAlpha(span: number): number {
  return 2.0 / (span + 1.0);
}

/** Cumulative maximum, as `Series.cummax()`. */
export function cummax(a: ArrayLike<number>): Float64Array {
  const n = a.length;
  const out = new Float64Array(n);
  let peak = -Infinity;
  for (let i = 0; i < n; i++) {
    if (a[i] > peak) peak = a[i];
    out[i] = peak;
  }
  return out;
}

/**
 * Index of the first element > value (`searchsorted(..., side="right")`),
 * i.e. how many entries are <= value.
 */
export function searchsortedRight(a: ArrayLike<number>, value: number, hi?: number): number {
  let lo = 0;
  let high = hi === undefined ? a.length : hi;
  while (lo < high) {
    const mid = (lo + high) >>> 1;
    if (a[mid] <= value) lo = mid + 1;
    else high = mid;
  }
  return lo;
}

/**
 * Unit parity for each ported primitive, against fixtures generated from the
 * Python originals by `tools/gen_ts_fixtures.py`.
 *
 * These run in the order the port was written — reductions, indicators, tax,
 * result metrics — so a failure localizes to a module instead of surfacing as a
 * diverged equity curve 1,200 days in.
 *
 * Reductions and tax are asserted EXACT (===). They are pure arithmetic with a
 * pinned evaluation order, so anything less than exact means the order is
 * wrong. Indicators and result metrics allow 1 ulp for `Math.pow`/`Math.sqrt`
 * library differences.
 */
import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import {
  bollinger,
  computeYearTax,
  cummax,
  ewmMean,
  macd,
  makeTaxPolicy,
  nmean,
  nstd,
  nsum,
  pctChange,
  realizedVol,
  sma,
  totalReturn,
  wilderRsi,
  Result,
} from "../src/index.js";
// Resolve the fixture from the package root rather than the CWD, so the suite
// runs the same from web/engine or from the repo root.
const HERE = dirname(fileURLToPath(import.meta.url));
const PKG = join(HERE, "..");
const fixtures = JSON.parse(
  readFileSync(join(PKG, "test", "fixtures.json"), "utf8"),
);

/** Relative closeness for values that pass through libm (pow/sqrt). */
function close(a, b, tol = 1e-15) {
  if (a === b) return true;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return a === b;
  return Math.abs(a - b) <= tol * Math.max(Math.abs(a), Math.abs(b));
}
// ---------------------------------------------------------------------------
test("numeric reductions match NumPy/pandas exactly", () => {
  for (const g of fixtures.reductions) {
    const x = Float64Array.from(g.x);
    const n = g.n;
    assert.equal(nsum(x), g.sum, `sum n=${n}`);
    assert.equal(nmean(x), g.mean, `mean n=${n}`);
    if (g.std0 !== null) assert.equal(nstd(x, 0), g.std0, `std0 n=${n}`);
    if (g.std1 !== null && n >= 2)
      assert.equal(nstd(x, 1), g.std1, `std1 n=${n}`);
    const pc = pctChange(x);
    assert.equal(pc.length, g.pct_change.length, `pct_change len n=${n}`);
    for (let i = 0; i < pc.length; i++) {
      assert.equal(pc[i], g.pct_change[i], `pct_change[${i}] n=${n}`);
    }
    const ew = ewmMean(x, 0.1);
    for (let i = 0; i < ew.length; i++) {
      assert.equal(ew[i], g.ewm_0_1[i], `ewm[${i}] n=${n}`);
    }
    const cm = cummax(x);
    for (let i = 0; i < cm.length; i++) {
      assert.equal(cm[i], g.cummax[i], `cummax[${i}] n=${n}`);
    }
  }
});
// ---------------------------------------------------------------------------
test("indicators match the Python originals", () => {
  for (const g of fixtures.indicators) {
    const closes = Float64Array.from(g.closes);
    const n = g.n;
    for (const [w, want] of [
      [20, g.sma_20],
      [50, g.sma_50],
      [200, g.sma_200],
    ]) {
      const got = sma(closes, w);
      if (want === null)
        assert.equal(got, null, `sma${w} n=${n} should be null`);
      else assert.equal(got, want, `sma${w} n=${n}`);
    }
    const rsi = wilderRsi(closes, 14);
    if (g.rsi_14 === null) assert.equal(rsi, null, `rsi n=${n}`);
    else assert.ok(close(rsi, g.rsi_14), `rsi n=${n}: ${rsi} vs ${g.rsi_14}`);
    const m = macd(closes);
    if (g.macd === null) assert.equal(m, null, `macd n=${n}`);
    else {
      assert.equal(m[0], g.macd[0], `macd line n=${n}`);
      assert.equal(m[1], g.macd[1], `macd signal n=${n}`);
    }
    const b = bollinger(closes);
    if (g.bollinger === null) assert.equal(b, null, `bollinger n=${n}`);
    else
      for (let i = 0; i < 3; i++) {
        assert.ok(close(b[i], g.bollinger[i]), `bollinger[${i}] n=${n}`);
      }
    for (const [lb, want] of [
      [20, g.total_return_20],
      [252, g.total_return_252],
    ]) {
      const got = totalReturn(closes, lb);
      if (want === null) assert.equal(got, null, `total_return${lb} n=${n}`);
      else assert.equal(got, want, `total_return${lb} n=${n}`);
    }
    const rv = realizedVol(closes, 20);
    if (g.realized_vol_20 === null)
      assert.equal(rv, null, `realized_vol n=${n}`);
    else assert.ok(close(rv, g.realized_vol_20), `realized_vol n=${n}`);
  }
});
// ---------------------------------------------------------------------------
test("tax netting matches compute_year_tax exactly", () => {
  const p = makeTaxPolicy(
    fixtures.tax.policy.short_term_rate,
    fixtures.tax.policy.long_term_rate,
    fixtures.tax.policy.long_term_days,
  );
  for (const c of fixtures.tax.cases) {
    const got = computeYearTax(c.net_st, c.net_lt, c.carryforward_in, p);
    const label = `st=${c.net_st} lt=${c.net_lt} cf=${c.carryforward_in}`;
    assert.equal(got.tax, c.tax, `tax ${label}`);
    assert.equal(got.carryforward, c.carryforward_out, `carryforward ${label}`);
  }
});
// ---------------------------------------------------------------------------
test("Result metrics match pandas", () => {
  const g = fixtures.result_metrics;
  const curve = Float64Array.from(g.curve);
  const n = curve.length;
  const days = new Int32Array(n);
  // Only the first and last day matter for CAGR; space them to the fixture span.
  for (let i = 0; i < n; i++) days[i] = Math.round((i * g.end_day) / (n - 1));
  const equity = {
    days,
    cash: new Float64Array(n),
    holdings: curve,
    total: curve,
  };
  const res = new Result(equity, [], g.starting_cash, null, null);
  assert.ok(close(res.sharpe, g.sharpe), `sharpe ${res.sharpe} vs ${g.sharpe}`);
  assert.equal(res.maxDrawdown, g.max_drawdown, "max_drawdown");
  assert.ok(close(res.cagr, g.cagr), `cagr ${res.cagr} vs ${g.cagr}`);
  assert.equal(res.finalValue, curve[n - 1], "final_value");
  assert.equal(
    res.totalReturn,
    curve[n - 1] / g.starting_cash - 1.0,
    "total_return",
  );
});

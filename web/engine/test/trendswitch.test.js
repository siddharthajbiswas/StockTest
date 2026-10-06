/**
 * TrendSwitchTimer's state machine and the UNIVERSE_EXCLUDE contract.
 *
 * End-to-end parity for the timer is the `manual_trendswitch_sso_ief` golden
 * (parity.test.js). These pin the pieces a 20-year golden can pass without
 * exercising: the undecided state, the once-per-day evaluation, and the
 * no-data branches. reference/tests/test_reference.py runs the same scenario
 * against the Python original with the same expected answers.
 */
import { strict as assert } from "node:assert";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import { TrendSwitchTimer, UNIVERSE_EXCLUDE, makeTimer } from "../src/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const DATA = join(HERE, "..", "..", "..", "build", "webdata");

/** A minimal Context: SPY closes by day; `null` = SPY has no bar that day. */
function fakeCtx(spy) {
  const ctx = {
    day: -1,
    price(t) {
      if (t !== "SPY") return null;
      const v = spy[ctx.day];
      return v === null || v === undefined ? null : v;
    },
    history(t, _field, window) {
      if (t !== "SPY") return new Float64Array(0);
      const bars = spy.slice(0, ctx.day + 1).filter((v) => v !== null);
      const start = window !== null && window < bars.length ? bars.length - window : 0;
      return Float64Array.from(bars.slice(start));
    },
  };
  return ctx;
}

const SPY = [100, 100, 100, 120, 110, 90, null, 96];
// day: 0-1 too little history -> undecided (nothing held); 2: first evaluation,
// margin 0 -> false (safe); 3: +12.5% > +10% -> risk; 4: margin 0 -> keep risk;
// 5: -15.6% < -10% -> safe; 6: no SPY bar -> keep safe; 7: [110, 90, 96] ->
// -2.7% inside the band -> keep safe.
const EXPECT = [null, null, false, true, true, false, false, false];

test("trend_switch: hysteresis, undecided start, no-data days", () => {
  const ctx = fakeCtx(SPY);
  const t = new TrendSwitchTimer("SPY", 3, 0.1, "SSO", "IEF");
  t.initialize(ctx);
  for (let d = 0; d < SPY.length; d++) {
    ctx.day = d;
    const risk = t.wantLong(ctx, "SSO", false, null);
    const safe = t.wantLong(ctx, "IEF", false, null);
    const other = t.wantLong(ctx, "SPY", false, null);
    assert.equal(other, false, `day ${d}: a ticker in neither list`);
    if (EXPECT[d] === null) {
      assert.deepEqual([risk, safe], [false, false], `day ${d}: undecided`);
    } else {
      assert.deepEqual([risk, safe], [EXPECT[d], !EXPECT[d]], `day ${d}`);
    }
  }
});

test("trend_switch: evaluated once per day, shared by every ticker", () => {
  const spy = [100, 100, 100, 100];
  const ctx = fakeCtx(spy);
  const t = new TrendSwitchTimer("SPY", 3, 0.1, "SSO", "IEF");
  t.initialize(ctx);
  for (let d = 0; d < 3; d++) {
    ctx.day = d;
    t.wantLong(ctx, "SSO", false, null);
  }
  assert.equal(t.state, false);
  ctx.day = 3;
  spy[3] = 150; // first call of the day sees a breakout -> risk on
  assert.equal(t.wantLong(ctx, "SSO", false, null), true);
  spy[3] = 50; // a second call on the SAME day must not re-evaluate
  assert.equal(t.wantLong(ctx, "IEF", false, null), false);
  assert.equal(t.state, true);
});

test("trend_switch: string params parse like Python's _ticker_list", () => {
  const t = makeTimer("trend_switch", {
    signal: " spy ",
    n: "175",
    band: "0.03",
    risk: " sso, qld ,SSO,,",
    safe: ["ief"],
  });
  assert.equal(t.signal, "SPY");
  assert.equal(t.n, 175);
  assert.equal(t.band, 0.03);
  assert.deepEqual(t.risk, ["SSO", "QLD"]);
  assert.deepEqual(t.safe, ["IEF"]);
  const d = makeTimer("trend_switch", {});
  assert.deepEqual(
    [d.signal, d.n, d.band, d.risk, d.safe],
    ["SPY", 175, 0.03, ["SSO"], ["IEF"]],
  );
});

test("UNIVERSE_EXCLUDE matches the bundle and keeps per-ticker files", () => {
  const path = join(DATA, "manifest.json");
  assert.ok(existsSync(path), "build/webdata missing — run tools/build_web_data.py");
  const manifest = JSON.parse(readFileSync(path, "utf8"));
  assert.deepEqual(
    [...UNIVERSE_EXCLUDE].sort(),
    manifest.universe_exclude,
    "web/engine UNIVERSE_EXCLUDE != backtester.data.UNIVERSE_EXCLUDE (via the manifest)",
  );
  for (const t of UNIVERSE_EXCLUDE) {
    assert.ok(!manifest.universe.tickers.includes(t), `${t} leaked into universe.bin`);
    assert.ok(manifest.tickers[t], `${t} has no per-ticker file`);
    assert.ok(existsSync(join(DATA, "tickers", `${t}.bin`)), `tickers/${t}.bin`);
  }
});

/**
 * The CPython Mersenne Twister port, pinned directly against Python 3.13.3.
 *
 * The random picker's golden case would catch a broken RNG, but only as "the
 * whole backtest diverged". These tests fail at the exact draw instead, and
 * cover both `sample()` branches — the pool-swap path (n <= setsize) and the
 * set-tracking path (n > setsize) — which consume the stream differently.
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";

import { MT19937 } from "../src/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const PKG = join(HERE, "..", "..");
const fx = JSON.parse(readFileSync(join(PKG, "test", "rng-fixtures.json"), "utf8"));

test("getrandbits(32) matches CPython for seed 42", () => {
  const r = new MT19937(42);
  const want: number[] = fx.getrandbits32_seed42;
  for (let i = 0; i < want.length; i++) {
    assert.equal(r.getrandbits(32), want[i], `draw ${i}`);
  }
});

test("getrandbits(9) matches CPython (the _randbelow width for ~500 names)", () => {
  const r = new MT19937(42);
  const want: number[] = fx.getrandbits9_seed42;
  for (let i = 0; i < want.length; i++) {
    assert.equal(r.getrandbits(9), want[i], `draw ${i}`);
  }
});

test("sample() matches CPython across both branches", () => {
  for (const c of fx.sample) {
    const r = new MT19937(c.seed);
    const pop = Array.from({ length: c.n }, (_, i) => `T${i}`);
    const got = r.sample(pop, c.k);
    assert.deepEqual(
      got, c.result,
      `seed=${c.seed} n=${c.n} k=${c.k} (setsize branch: ${c.n <= 21 + (c.k > 5 ? Math.pow(4, Math.ceil(Math.log(c.k * 3) / Math.log(4))) : 0) ? "pool" : "set"})`,
    );
  }
});

test("consecutive samples keep the stream in sync", () => {
  // A picker draws once per rebalance from one long-lived generator; if the
  // stream desynchronizes, only the second and later draws diverge.
  const r = new MT19937(42);
  const pop = Array.from({ length: 500 }, (_, i) => `T${i}`);
  const want: string[][] = fx.sample_stream;
  for (let i = 0; i < want.length; i++) {
    assert.deepEqual(r.sample(pop, 10), want[i], `rebalance ${i}`);
  }
});

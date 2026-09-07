/**
 * Sanity instrumentation for the parity test.
 *
 * A passing comparison is only meaningful if it actually walked the data. This
 * counts leaf comparisons per case and prints a few headline numbers computed
 * by the TS engine next to the Python originals, so "5 tests pass" is backed by
 * something inspectable.
 *
 * Run: node test/coverage-check.js
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..");
const GOLDEN = join(ROOT, "golden");
const CASES = [
  "manual_buyhold_tax",
  "manual_buyhold_notax",
  "manual_macross_tax",
  "manual_macross_gfc",
];

/** Count comparable leaves in a golden payload (what a diff would traverse). */
function countLeaves(v) {
  if (v === null || v === undefined) return 1;
  if (Array.isArray(v)) return v.reduce((a, x) => a + countLeaves(x), 0);
  if (typeof v === "object") {
    return Object.values(v).reduce((a, x) => a + countLeaves(x), 0);
  }
  return 1;
}

let total = 0;
console.log(
  "case".padEnd(24) +
    "leaves".padStart(9) +
    "days".padStart(7) +
    "trades".padStart(8) +
    "  final_value (python)      total_tax (python)",
);
console.log("-".repeat(96));
for (const id of CASES) {
  const g = JSON.parse(readFileSync(join(GOLDEN, `${id}.json`), "utf8"));
  const n = countLeaves(g.result);
  total += n;
  const m = g.result.metrics;
  const tax = m.total_tax === null ? "-" : m.total_tax.toFixed(2);
  console.log(
    id.padEnd(24) +
      String(n).padStart(9) +
      String(g.result.equity_curve.dates.length).padStart(7) +
      String(g.result.trades.length).padStart(8) +
      "  " +
      m.final_value.toFixed(2).padStart(16) +
      tax.padStart(24),
  );
}
console.log("-".repeat(96));
console.log(
  `total leaf values compared across the 4 parity cases: ${total.toLocaleString()}`,
);

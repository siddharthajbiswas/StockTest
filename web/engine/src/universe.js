/**
 * Point-in-time index membership. Port of `backtester/universe.py`.
 *
 * Restricts what a strategy may *select* each day to the names genuinely in the
 * index then, so a picker can't buy a stock before it joined (or after it left)
 * just because it's in today's index.
 *
 * Honesty note carried over from Python: this corrects *membership*
 * look-ahead only. It cannot resurrect companies whose price data no longer
 * exists (bankruptcies etc.), which free data sources don't provide.
 *
 * Symbol normalization (BRK.B -> BRK-B) is already applied by the Phase 1
 * builder, so `sp500-pit.json` ships Yahoo-style symbols and no mapping is
 * needed here.
 */
import { searchsortedRight } from "./numeric.js";
import { dayFromIso } from "./data.js";

/**
 * Tickers that ship per-ticker files (manual/menu mode, search) but are NOT in
 * the stock-picking universe. Mirrors `backtester/data.py::UNIVERSE_EXCLUDE`;
 * tools/build_web_data.py leaves them out of universe.bin and records the list
 * as `manifest.universe_exclude`, which a unit test holds equal to this set.
 */
export const UNIVERSE_EXCLUDE = new Set(["IEF", "SSO"]);

/**
 * Align membership to `calendar`: for each day, the members as of that day
 * (the most recent snapshot on or before it). Days before the first snapshot
 * get an empty set, matching Python's `p < 0` branch.
 *
 * `restrictTo` intersects each set with the tickers that actually have price
 * data, so the returned sets only contain tradable names.
 */
export function membersByCalendar(membership, calendar, restrictTo = null) {
  const snapDays = Int32Array.from(membership.dates, dayFromIso);
  // Cache one Set per snapshot index; many calendar days map to the same
  // snapshot, and rebuilding a 500-element set per day is pure waste.
  const cache = new Map();
  const setFor = (p) => {
    let s = cache.get(p);
    if (s === undefined) {
      s = new Set(membership.members[p]);
      if (restrictTo !== null) {
        const inter = new Set();
        for (const t of s) if (restrictTo.has(t)) inter.add(t);
        s = inter;
      }
      cache.set(p, s);
    }
    return s;
  };
  const out = new Array(calendar.length);
  const empty = new Set();
  for (let i = 0; i < calendar.length; i++) {
    const p = searchsortedRight(snapDays, calendar[i]) - 1;
    out[i] = p < 0 ? empty : setFor(p);
  }
  return out;
}

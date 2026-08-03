/**
 * Ticker discovery. Port of `reference/tickers.py::TickerIndex`.
 *
 * The ranking ladder is exact symbol > symbol prefix > symbol substring >
 * name prefix > name substring > fuzzy symbol, ties broken by symbol. The fuzzy
 * tier calls Python's `difflib.SequenceMatcher.ratio()`, which is reimplemented
 * below — swapping in a different string metric (Levenshtein, say) would return
 * a different result set for the same query.
 *
 * NOTE on names: the current fundamentals snapshot has no name column, so
 * `has_name_data` is false and every record's `name` is null, which makes the
 * two name tiers unreachable in practice. They are implemented anyway so adding
 * a name column to the snapshot doesn't silently change behaviour.
 */

/** Minimum SequenceMatcher ratio for a fuzzy symbol match. */
const FUZZY_THRESHOLD = 0.6;

export interface TickerRecord {
  symbol: string;
  name: string | null;
  has_fundamentals: boolean;
  market_cap: number | null;
  date_from: string | null;
  date_to: string | null;
}

/**
 * Total matched characters between two sequences, via difflib's recursive
 * longest-matching-block decomposition.
 *
 * `ratio()` only needs the total, so this skips building and merging the block
 * list — merging adjacent blocks and appending the sentinel never changes the
 * sum.
 */
function totalMatches(a: string, b: string): number {
  // b2j: character -> ascending indices in b.
  const b2j = new Map<string, number[]>();
  for (let j = 0; j < b.length; j++) {
    const c = b[j];
    let arr = b2j.get(c);
    if (arr === undefined) { arr = []; b2j.set(c, arr); }
    arr.push(j);
  }

  /** difflib's find_longest_match over a[alo:ahi] and b[blo:bhi]. */
  function longest(alo: number, ahi: number, blo: number, bhi: number):
    [number, number, number] {
    let besti = alo, bestj = blo, bestsize = 0;
    let j2len = new Map<number, number>();
    for (let i = alo; i < ahi; i++) {
      const newj2len = new Map<number, number>();
      const js = b2j.get(a[i]);
      if (js !== undefined) {
        for (const j of js) {
          if (j < blo) continue;
          if (j >= bhi) break;
          const k = (j2len.get(j - 1) ?? 0) + 1;
          newj2len.set(j, k);
          if (k > bestsize) { besti = i - k + 1; bestj = j - k + 1; bestsize = k; }
        }
      }
      j2len = newj2len;
    }
    // difflib then extends the block over adjacent equal elements. With no junk
    // (our sequences are far below the autojunk threshold of 200) the DP result
    // is already maximal, so these loops are no-ops — kept for fidelity.
    while (besti > alo && bestj > blo && a[besti - 1] === b[bestj - 1]) {
      besti--; bestj--; bestsize++;
    }
    while (besti + bestsize < ahi && bestj + bestsize < bhi
      && a[besti + bestsize] === b[bestj + bestsize]) {
      bestsize++;
    }
    return [besti, bestj, bestsize];
  }

  let total = 0;
  const queue: Array<[number, number, number, number]> = [[0, a.length, 0, b.length]];
  while (queue.length > 0) {
    const [alo, ahi, blo, bhi] = queue.pop()!;
    const [i, j, k] = longest(alo, ahi, blo, bhi);
    if (k > 0) {
      total += k;
      if (alo < i && blo < j) queue.push([alo, i, blo, j]);
      if (i + k < ahi && j + k < bhi) queue.push([i + k, ahi, j + k, bhi]);
    }
  }
  return total;
}

/**
 * `difflib.SequenceMatcher(None, a, b).ratio()` — 2*M/T, where M is total
 * matched characters and T the combined length. Empty vs empty is 1.0.
 */
export function sequenceMatcherRatio(a: string, b: string): number {
  const length = a.length + b.length;
  if (length === 0) return 1.0;
  return (2.0 * totalMatches(a, b)) / length;
}

export class TickerIndex {
  readonly records: TickerRecord[];
  readonly hasNameData: boolean;
  private readonly bySymbol = new Map<string, TickerRecord>();

  constructor(records: TickerRecord[], hasNameData: boolean) {
    // Python builds records from `sorted(prices)`; the shipped file preserves
    // that, but sort defensively so ordering never depends on JSON key order.
    this.records = [...records].sort((x, y) => (x.symbol < y.symbol ? -1 : x.symbol > y.symbol ? 1 : 0));
    this.hasNameData = hasNameData;
    for (const r of this.records) this.bySymbol.set(r.symbol, r);
  }

  all(): TickerRecord[] { return this.records; }
  count(): number { return this.records.length; }
  get(symbol: string): TickerRecord | undefined { return this.bySymbol.get(symbol); }

  /** Prefix/substring/fuzzy match, best first. */
  search(q: string, limit = 20): TickerRecord[] {
    q = (q ?? "").trim();
    if (q === "") return [];
    const qu = q.toUpperCase();
    const ql = q.toLowerCase();

    const scored: Array<{ score: number; sym: string; r: TickerRecord }> = [];
    for (const r of this.records) {
      const sym = r.symbol;
      const symu = sym.toUpperCase();
      const namel = r.name ? r.name.toLowerCase() : null;

      let score = 0.0;
      if (symu === qu) score = 1000.0;
      else if (symu.startsWith(qu)) score = 900.0 - symu.length;
      else if (symu.includes(qu)) score = 700.0;
      else if (namel && namel.startsWith(ql)) score = 600.0;
      else if (namel && namel.includes(ql)) score = 500.0;
      else {
        let ratio = sequenceMatcherRatio(ql, sym.toLowerCase());
        if (namel) ratio = Math.max(ratio, sequenceMatcherRatio(ql, namel));
        if (ratio >= FUZZY_THRESHOLD) score = 100.0 * ratio;
      }

      if (score > 0) scored.push({ score, sym, r });
    }

    // Python: sort(key=lambda t: (-score, symbol)).
    scored.sort((x, y) => (y.score - x.score) || (x.sym < y.sym ? -1 : x.sym > y.sym ? 1 : 0));
    return scored.slice(0, limit).map((s) => s.r);
  }
}

/**
 * Browser data layer — reads the binary bundle produced by
 * `tools/build_web_data.py` (Phase 1) and rebuilds the per-ticker series the
 * engine expects. Replaces `backtester/data.py` (CSV loading).
 *
 * The on-disk form is dense-over-span with NaN in gap cells, which is compact
 * but is NOT what the engine wants: pandas frames contain only real bars, and
 * `history()` slices those. So decoding compacts each ticker back to its real
 * bars plus their calendar indices, exactly reproducing the DataFrame.
 *
 * That compaction is only unambiguous because the source data has no NaN cells
 * on real rows — verified across all 528 tickers / 4.52M bars, and asserted by
 * the builder. If a future data refresh introduces NaN closes, the format needs
 * an explicit presence mask.
 */

import { searchsortedRight } from "./numeric.js";

export const FIELDS = ["Open", "High", "Low", "Close", "Volume"] as const;
export type Field = (typeof FIELDS)[number];

/** Bundle format version; must match tools/build_web_data.py::FORMAT_VERSION. */
export const FORMAT_VERSION = 2;

/** One ticker's real bars, mirroring a pandas OHLCV frame. */
export interface TickerSeries {
  ticker: string;
  /** Calendar day numbers (days since 1970-01-01), ascending, one per bar. */
  days: Int32Array;
  /** Present for per-ticker files; universe-only loads carry just `Close`. */
  fields: Partial<Record<Field, Float64Array>>;
  /** Per-bar tradability, precomputed by the builder from float64 source. */
  tradable: Uint8Array;
}

export interface Manifest {
  format_version: number;
  calendar: { file: string; n: number; start: string; end: string };
  universe: { file: string; tickers: string[]; n_tickers: number };
  tickers: Record<string, { file: string; first: number; n: number; bars: number }>;
  fundamentals: { file: string };
  sp500_pit: { file: string };
}

function readMagic(buf: ArrayBuffer, expect: string): void {
  const got = String.fromCharCode(...new Uint8Array(buf, 0, 4));
  if (got !== expect) throw new Error(`bad magic: expected ${expect}, got ${got}`);
}

/** Unpack an LSB-first bitmask (numpy packbits bitorder="little"). */
function unpackBits(bytes: Uint8Array, count: number): Uint8Array {
  const out = new Uint8Array(count);
  for (let i = 0; i < count; i++) {
    out[i] = (bytes[i >> 3] >> (i & 7)) & 1;
  }
  return out;
}

/** Decode `calendar.bin` — int32 days since 1970-01-01. */
export function decodeCalendar(buf: ArrayBuffer): Int32Array {
  return new Int32Array(buf.slice(0));
}

/**
 * Compact a dense-over-span slice down to its real bars.
 * A cell is a real bar iff its close is not NaN (see the module note).
 */
function compact(
  calendar: Int32Array,
  first: number,
  n: number,
  close: Float32Array,
  dense: Partial<Record<Field, Float32Array>>,
  tradableBits: Uint8Array,
): { days: Int32Array; fields: Partial<Record<Field, Float64Array>>; tradable: Uint8Array } {
  let count = 0;
  for (let i = 0; i < n; i++) if (!Number.isNaN(close[i])) count++;

  const days = new Int32Array(count);
  const tradable = new Uint8Array(count);
  const fields: Partial<Record<Field, Float64Array>> = {};
  for (const f of Object.keys(dense) as Field[]) fields[f] = new Float64Array(count);

  let k = 0;
  for (let i = 0; i < n; i++) {
    if (Number.isNaN(close[i])) continue;
    days[k] = calendar[first + i];
    tradable[k] = tradableBits[i];
    for (const f of Object.keys(dense) as Field[]) {
      // Float32 -> Number widens exactly; this is the same value JS would see
      // reading the Float32Array directly.
      fields[f]![k] = dense[f]![i];
    }
    k++;
  }
  return { days, fields, tradable };
}

/**
 * Decode a per-ticker `tickers/<T>.bin`.
 *
 * The file declares which fields it carries, so the set can change without a
 * decoder change. Current bundles ship Close only: the engine reads nothing
 * else, and publishing full OHLCV made the bundle three times larger for data
 * no strategy touches.
 */
export function decodeTicker(
  ticker: string,
  buf: ArrayBuffer,
  calendar: Int32Array,
): TickerSeries {
  readMagic(buf, "STK1");
  const head = new DataView(buf);
  const version = head.getUint32(4, true);
  if (version !== FORMAT_VERSION) {
    throw new Error(`${ticker}: unsupported format_version ${version}`);
  }
  const first = head.getUint32(8, true);
  const n = head.getUint32(12, true);
  const nfields = head.getUint32(16, true);

  let off = 20;
  const ids = new Uint8Array(buf, off, nfields);
  const names = Array.from(ids, (i) => FIELDS[i]);
  off += nfields;

  const dense: Partial<Record<Field, Float32Array>> = {};
  for (const f of names) {
    dense[f] = new Float32Array(buf.slice(off, off + 4 * n));
    off += 4 * n;
  }
  if (dense.Close === undefined) {
    throw new Error(`${ticker}: bundle has no Close series`);
  }
  const maskBytes = (n + 7) >> 3;
  const bits = unpackBits(new Uint8Array(buf, off, maskBytes), n);

  const { days, fields, tradable } = compact(calendar, first, n, dense.Close!, dense, bits);
  return { ticker, days, fields, tradable };
}

/**
 * Decode `universe.bin` — Close + tradability for every ticker.
 * Returns a map so callers can pick out the subset they need.
 */
export function decodeUniverse(
  buf: ArrayBuffer,
  tickers: string[],
  calendar: Int32Array,
): Map<string, TickerSeries> {
  readMagic(buf, "STKU");
  const head = new DataView(buf);
  const version = head.getUint32(4, true);
  if (version !== FORMAT_VERSION) {
    throw new Error(`universe: unsupported format_version ${version}`);
  }
  const nTickers = head.getUint32(8, true);
  if (nTickers !== tickers.length) {
    throw new Error(`universe: ${nTickers} tickers in binary, ${tickers.length} in manifest`);
  }

  let off = 16;
  const table: Array<[number, number]> = [];
  for (let i = 0; i < nTickers; i++) {
    table.push([head.getUint32(off, true), head.getUint32(off + 4, true)]);
    off += 8;
  }

  const closes: Float32Array[] = [];
  for (const [, n] of table) {
    closes.push(new Float32Array(buf.slice(off, off + 4 * n)));
    off += 4 * n;
  }

  const out = new Map<string, TickerSeries>();
  for (let i = 0; i < nTickers; i++) {
    const [first, n] = table[i];
    const maskBytes = (n + 7) >> 3;
    const bits = unpackBits(new Uint8Array(buf, off, maskBytes), n);
    off += maskBytes;
    const { days, fields, tradable } = compact(
      calendar, first, n, closes[i], { Close: closes[i] }, bits,
    );
    out.set(tickers[i], { ticker: tickers[i], days, fields, tradable });
  }
  if (off !== buf.byteLength) {
    throw new Error(`universe: ${buf.byteLength - off} trailing bytes`);
  }
  return out;
}

/** Clip a series to [start, end] day numbers inclusive, as `_clip` does. */
export function clipSeries(
  s: TickerSeries,
  startDay: number | null,
  endDay: number | null,
): TickerSeries {
  let lo = 0;
  let hi = s.days.length;
  if (startDay !== null) lo = searchsortedRight(s.days, startDay - 1);
  if (endDay !== null) hi = searchsortedRight(s.days, endDay);
  if (lo === 0 && hi === s.days.length) return s;
  const fields: Partial<Record<Field, Float64Array>> = {};
  for (const f of Object.keys(s.fields) as Field[]) {
    fields[f] = s.fields[f]!.slice(lo, hi);
  }
  return {
    ticker: s.ticker,
    days: s.days.slice(lo, hi),
    fields,
    tradable: s.tradable.slice(lo, hi),
  };
}

/** Days since 1970-01-01 for a YYYY-MM-DD string. */
export function dayFromIso(iso: string): number {
  return Math.floor(Date.parse(iso + "T00:00:00Z") / 86400000);
}

/**
 * Client-side persistence. Replaces `reference/`'s former store.py (a JSON file on the
 * server) now that there is no server.
 *
 * WHY BOTH BACKENDS — measured, not assumed:
 *
 *   saved strategy config      524 B     (100 of them = 51 KB)
 *   manual basket, 200 tickers 2.6 KB
 *   backtest result            0.14 – 1.22 MB
 *   localStorage origin quota  ~5 MB, and synchronous
 *
 * Configs are small enough that localStorage would genuinely do. Results are up
 * to 2,400x larger — four of them would blow the quota — and caching them is
 * exactly what makes re-running a saved strategy instant instead of a fresh
 * 1-3s sweep. So:
 *
 *   strategies -> IndexedDB, falling back to localStorage when IndexedDB is
 *                 unavailable (private browsing, older embedded webviews).
 *                 The fallback is safe precisely because configs are tiny.
 *   results    -> IndexedDB only, byte-budgeted with LRU eviction. If
 *                 IndexedDB is missing, caching degrades to a no-op and
 *                 everything still works, just slower.
 *
 * IndexedDB is also asynchronous, which matters more here than usual: Phase 5
 * moved all compute off the UI thread, and a synchronous multi-megabyte
 * localStorage write would have put a stall right back onto it.
 */

import type { BacktestRequest, BacktestResponse, SavedStrategy, StrategyConfig } from "./types";

const DB_NAME = "stocktest";
const DB_VERSION = 1;
const STRATEGIES = "strategies";
const RESULTS = "results";

/** Byte budget for the result cache. Well inside a typical IndexedDB quota
 *  (hundreds of MB), and enough for ~40 large results. */
const RESULT_CACHE_BUDGET = 48 * 1024 * 1024;

/** The Phase 5 localStorage key, migrated on first open. */
const LEGACY_KEY = "stocktest.strategies.v1";
/** localStorage key for the fallback path. */
const FALLBACK_KEY = "stocktest.strategies.v2";

// ---------------------------------------------------------------------------
// IndexedDB plumbing
// ---------------------------------------------------------------------------
function req<T>(r: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error ?? new Error("IndexedDB request failed"));
  });
}

function done(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed"));
    tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted"));
  });
}

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (dbPromise !== null) return dbPromise;
  dbPromise = new Promise<IDBDatabase | null>((resolve) => {
    if (typeof indexedDB === "undefined") {
      resolve(null);
      return;
    }
    let open: IDBOpenDBRequest;
    try {
      open = indexedDB.open(DB_NAME, DB_VERSION);
    } catch {
      resolve(null);
      return;
    }
    open.onupgradeneeded = () => {
      const db = open.result;
      if (!db.objectStoreNames.contains(STRATEGIES)) {
        db.createObjectStore(STRATEGIES, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(RESULTS)) {
        const s = db.createObjectStore(RESULTS, { keyPath: "key" });
        s.createIndex("lastUsed", "lastUsed");
      }
    };
    open.onsuccess = () => resolve(open.result);
    // Blocked or denied (Safari private mode historically rejects here).
    open.onerror = () => resolve(null);
    open.onblocked = () => resolve(null);
  });
  return dbPromise;
}

// ---------------------------------------------------------------------------
// localStorage fallback (strategies only)
// ---------------------------------------------------------------------------
function lsRead(key: string): SavedStrategy[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as SavedStrategy[]) : [];
  } catch {
    return []; // corrupt or unavailable storage must not break the app
  }
}

function lsWrite(items: SavedStrategy[]): void {
  try {
    localStorage.setItem(FALLBACK_KEY, JSON.stringify(items));
  } catch {
    /* quota or disabled storage — saving silently no-ops rather than throwing */
  }
}

function newId(): string {
  return (
    globalThis.crypto?.randomUUID?.().replace(/-/g, "").slice(0, 12) ??
    Math.random().toString(36).slice(2, 14)
  );
}

// ---------------------------------------------------------------------------
// Migration from the Phase 5 localStorage store
// ---------------------------------------------------------------------------
let migrated = false;

async function migrateLegacy(db: IDBDatabase): Promise<void> {
  if (migrated) return;
  migrated = true;
  const legacy = lsRead(LEGACY_KEY);
  if (legacy.length === 0) return;
  const tx = db.transaction(STRATEGIES, "readwrite");
  const store = tx.objectStore(STRATEGIES);
  for (const s of legacy) store.put(s);
  await done(tx);
  // Only drop the old key once the write has committed, so an interrupted
  // migration retries next load rather than losing the user's strategies.
  try {
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------
/** Newest first, matching the server store's `data.insert(0, entry)`. */
function byNewest(a: SavedStrategy, b: SavedStrategy): number {
  return b.created_at.localeCompare(a.created_at);
}

export async function listStrategies(): Promise<SavedStrategy[]> {
  const db = await openDb();
  if (db === null) return lsRead(FALLBACK_KEY).sort(byNewest);
  await migrateLegacy(db);
  const tx = db.transaction(STRATEGIES, "readonly");
  const all = await req(tx.objectStore(STRATEGIES).getAll() as IDBRequest<SavedStrategy[]>);
  return all.sort(byNewest);
}

export async function saveStrategy(
  name: string,
  config: StrategyConfig,
): Promise<SavedStrategy> {
  const entry: SavedStrategy = {
    id: newId(),
    name,
    // Seconds precision, matching the server store's isoformat(timespec="seconds").
    created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    config,
  };
  const db = await openDb();
  if (db === null) {
    lsWrite([entry, ...lsRead(FALLBACK_KEY)]);
    return entry;
  }
  await migrateLegacy(db);
  const tx = db.transaction(STRATEGIES, "readwrite");
  tx.objectStore(STRATEGIES).put(entry);
  await done(tx);
  return entry;
}

export async function deleteStrategy(id: string): Promise<void> {
  const db = await openDb();
  if (db === null) {
    lsWrite(lsRead(FALLBACK_KEY).filter((s) => s.id !== id));
    return;
  }
  const tx = db.transaction(STRATEGIES, "readwrite");
  tx.objectStore(STRATEGIES).delete(id);
  await done(tx);
}

// ---------------------------------------------------------------------------
// Result cache
// ---------------------------------------------------------------------------
interface CacheEntry {
  key: string;
  bytes: number;
  lastUsed: number;
  value: BacktestResponse;
}

/**
 * Deterministic JSON for cache keys. `JSON.stringify` preserves insertion
 * order, so two equivalent requests built by different code paths would
 * otherwise hash differently and silently miss.
 */
function canonical(v: unknown): string {
  if (v === null || typeof v !== "object") return JSON.stringify(v) ?? "null";
  if (Array.isArray(v)) return `[${v.map(canonical).join(",")}]`;
  const o = v as Record<string, unknown>;
  const keys = Object.keys(o).filter((k) => o[k] !== undefined).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonical(o[k])}`).join(",")}}`;
}

/**
 * Cache key for a backtest request.
 *
 * `dataFingerprint` namespaces the cache to the exact price bundle that
 * produced the result — re-download the data and every entry is invalidated
 * rather than silently serving numbers computed from prices that no longer
 * exist.
 */
export function resultKey(req: BacktestRequest, dataFingerprint: string): string {
  return `${dataFingerprint}:${canonical(req)}`;
}

export async function getCachedResult(key: string): Promise<BacktestResponse | null> {
  const db = await openDb();
  if (db === null) return null;
  const tx = db.transaction(RESULTS, "readwrite");
  const store = tx.objectStore(RESULTS);
  const hit = (await req(store.get(key) as IDBRequest<CacheEntry | undefined>)) ?? null;
  if (hit !== null) {
    hit.lastUsed = Date.now(); // touch for LRU
    store.put(hit);
  }
  await done(tx);
  return hit === null ? null : hit.value;
}

export async function putCachedResult(key: string, value: BacktestResponse): Promise<void> {
  const db = await openDb();
  if (db === null) return; // caching is an optimization, never a requirement
  const bytes = canonical(value).length;
  const entry: CacheEntry = { key, bytes, lastUsed: Date.now(), value };
  try {
    const tx = db.transaction(RESULTS, "readwrite");
    tx.objectStore(RESULTS).put(entry);
    await done(tx);
    await evictIfOverBudget(db);
  } catch {
    /* QuotaExceeded or similar — a failed cache write must not fail the run */
  }
}

/** Drop least-recently-used entries until the store is inside its budget. */
async function evictIfOverBudget(db: IDBDatabase): Promise<void> {
  const tx = db.transaction(RESULTS, "readwrite");
  const store = tx.objectStore(RESULTS);
  const all = await req(store.getAll() as IDBRequest<CacheEntry[]>);
  let total = all.reduce((a, e) => a + e.bytes, 0);
  if (total <= RESULT_CACHE_BUDGET) {
    await done(tx);
    return;
  }
  for (const e of all.sort((a, b) => a.lastUsed - b.lastUsed)) {
    if (total <= RESULT_CACHE_BUDGET) break;
    store.delete(e.key);
    total -= e.bytes;
  }
  await done(tx);
}

/** Number of cached results and their total bytes — for diagnostics. */
export async function cacheStats(): Promise<{ entries: number; bytes: number }> {
  const db = await openDb();
  if (db === null) return { entries: 0, bytes: 0 };
  const tx = db.transaction(RESULTS, "readonly");
  const all = await req(tx.objectStore(RESULTS).getAll() as IDBRequest<CacheEntry[]>);
  return { entries: all.length, bytes: all.reduce((a, e) => a + e.bytes, 0) };
}

/** Wipe cached results, keeping saved strategies. */
export async function clearResultCache(): Promise<void> {
  const db = await openDb();
  if (db === null) return;
  const tx = db.transaction(RESULTS, "readwrite");
  tx.objectStore(RESULTS).clear();
  await done(tx);
}

/** True when persistence is backed by IndexedDB rather than the fallback. */
export async function usingIndexedDb(): Promise<boolean> {
  return (await openDb()) !== null;
}

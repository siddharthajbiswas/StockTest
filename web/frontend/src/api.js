/**
 * Frontend data layer — backed by the in-browser engine worker.
 *
 * Phase 5 replaced the FastAPI backend with the ported TypeScript engine
 * running in a Web Worker. Every function below keeps the signature it had when
 * it was a `fetch` call, so no component changed: `App.jsx`, `Results.jsx` and
 * `TickerPicker.jsx` still import the same names.
 *
 * What actually changed:
 *   * There is no network. Requests go to a worker thread, which loads the
 *     binary price bundle and runs the engine locally.
 *   * `validateStrategy` no longer submits a job and polls. The worker streams
 *     progress, and cancellation is real — aborting terminates the thread
 *     instead of leaving a server churning through 100 backtests.
 *   * Saved strategies live in the browser (IndexedDB, see storage.js). They
 *     were per-user server state with no auth, so a local store is a closer
 *     match to what they always were.
 *   * Backtest results are cached locally, so re-running a saved strategy is
 *     instant instead of a fresh 1-3s run.
 */
import { EngineClient, EngineError } from "../../engine/src/worker/client";
import {
  getCachedResult,
  listStrategies as listSaved,
  putCachedResult,
  resultKey,
} from "./storage";

/**
 * Where the worker fetches the data bundle from. Defaults to `data/` relative
 * to the app's base path, which works for both the dev server and the
 * subfolder deploy at biswas.net/sid/stocktest.
 */
const DATA_BASE =
  import.meta.env.VITE_DATA_BASE ?? new URL("data/", document.baseURI).href;
const client = new EngineClient({
  // This literal is load-bearing: Vite detects and bundles a worker only from
  // exactly this `new Worker(new URL(..., import.meta.url), { type: "module" })`
  // shape. Hoisting the URL into a variable, or building it inside the client,
  // produces a build with no worker chunk that 404s at runtime.
  createWorker: () =>
    new Worker(new URL("../../engine/src/worker/worker.js", import.meta.url), {
      type: "module",
    }),
  dataBase: DATA_BASE,
});
export const fetchHealth = () => client.health();
export const fetchPickers = () => client.pickers();
export const fetchTimers = () => client.timers();
export const fetchUniverseOptions = () => client.universes();
export const fetchAllTickers = () => client.allTickers();
export const searchTickers = (q, limit = 12) => client.searchTickers(q, limit);

/**
 * One stock's close-price history, for the detail view opened from the trade
 * log. The worker reads the same per-ticker file the engine uses, so this is
 * free for any ticker a backtest already touched.
 */
export const fetchTickerHistory = (symbol, opts = {}) =>
  client.tickerHistory(symbol, opts);

/**
 * Run a backtest, serving an identical previous run from the local cache.
 *
 * Re-running a saved strategy is the common path — you open a saved config and
 * immediately backtest it again with the same parameters — and recomputing is
 * 1-3s of CPU for a byte-identical answer. Cache entries are namespaced by the
 * price bundle's fingerprint, so refreshing the data invalidates them all
 * instead of serving numbers derived from prices that no longer exist.
 */
export async function runBacktest(req) {
  const fingerprint = await dataFingerprint();
  const key = resultKey(req, fingerprint);
  const hit = await getCachedResult(key);
  if (hit !== null) return hit;
  const res = await client.backtest(req);
  void putCachedResult(key, res); // fire-and-forget: never delay the result
  return res;
}

/**
 * Identifies the exact price bundle in use, for namespacing the result cache.
 *
 * Comes from the worker, which already parses the manifest. Fetching
 * manifest.json from here instead would 404 in a deployed build: the published
 * bundle ships only pre-compressed `.gz` artifacts, and the fingerprint would
 * silently degrade to "unknown" — leaving cached results un-versioned and able
 * to survive a data refresh.
 */
let fingerprintPromise = null;
function dataFingerprint() {
  if (fingerprintPromise === null) {
    fingerprintPromise = client
      .health()
      .then((h) => h.data_fingerprint ?? "unknown")
      .catch(() => "unknown");
  }
  return fingerprintPromise;
}
// ----- saved strategies (IndexedDB, see storage.js) --------------------------
export { listStrategies, saveStrategy, deleteStrategy } from "./storage";

/**
 * Run an out-of-sample validation. Heavier than a backtest — it reruns every
 * combo over the span — so it reports progress and supports cancellation.
 *
 * `opts.onProgress` is new; callers that ignore it behave exactly as before.
 * `intervalMs` is accepted and ignored: it configured the old HTTP polling
 * loop, which no longer exists.
 */
export async function validateStrategy(req, opts = {}) {
  const cfg =
    req.config ??
    (await listSaved()).find((s) => s.id === req.strategy_id)?.config;
  if (!cfg) throw new Error("Validation needs a strategy config.");
  return client.validate(
    {
      picker_id: cfg.mode === "manual" ? null : cfg.picker_id,
      picker_params: cfg.picker_params,
      tickers: cfg.mode === "manual" ? cfg.tickers : null,
      timer_id: cfg.timer_id,
      timer_params: cfg.timer_params,
      top_n: cfg.top_n,
      rebalance: cfg.rebalance,
      universe: cfg.universe,
      start: cfg.start,
      end: cfg.end,
      commission_pct: cfg.commission_pct,
      slippage_pct: cfg.slippage_pct,
      tax: cfg.tax,
      split: req.split ?? null,
      train_years: req.train_years ?? 3,
      step_years: req.step_years ?? 1,
      price_only: req.price_only ?? true,
    },
    { signal: opts.signal, onProgress: opts.onProgress },
  );
}

export { EngineError };

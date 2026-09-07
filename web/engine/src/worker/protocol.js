/**
 * Message protocol between the UI thread and the engine worker.
 *
 * Deliberately request/response with an explicit `id`, rather than a
 * fire-and-forget stream: the UI issues concurrent calls (health, catalog and
 * ticker list all load on mount) and every reply must find its caller. Progress
 * messages reuse the same id, so a long validation can report without being
 * confused for a completion.
 *
 * This replaces an HTTP API, so the shapes mirror the old endpoints closely
 * enough that `web/frontend/src/api.js` keeps its signatures.
 *
 * There is nothing to execute here — the module exists so the wire format has
 * one written-down definition. Nothing enforces these shapes at runtime, so
 * treat a change here as a change to a contract with no compiler behind it:
 * `client.js` and `handler.js` must move together.
 *
 * @typedef {"configure" | "init" | "health" | "pickers" | "timers"
 *   | "universes" | "tickers" | "searchTickers" | "tickerHistory"
 *   | "backtest" | "validate"} RequestKind
 *
 * @typedef {object} WorkerRequest
 * @property {number} id
 * @property {RequestKind} kind
 * @property {unknown} [payload]
 *
 * @typedef {object} ProgressMessage
 * @property {number} id
 * @property {"progress"} type
 * @property {string} phase      Mirrors walkforward's Progress.
 * @property {number} completed
 * @property {number} total
 * @property {string} label
 * @property {number} elapsedMs
 *
 * @typedef {object} ResultMessage
 * @property {number} id
 * @property {"result"} type
 * @property {unknown} payload
 *
 * @typedef {object} ErrorMessage
 * @property {number} id
 * @property {"error"} type
 * @property {string} message
 * @property {string} name
 * @property {string[]} [unavailable]  Structured detail for unknown-ticker
 *   errors, as the API used to send.
 *
 * @typedef {ProgressMessage | ResultMessage | ErrorMessage} WorkerResponse
 *
 * Minimal port abstraction so the handler runs under both browser Workers
 * (`self`) and Node's `worker_threads` (`parentPort`) — which is what makes it
 * testable off-browser.
 *
 * @typedef {object} PortLike
 * @property {(msg: unknown) => void} postMessage
 * @property {(cb: (msg: unknown) => void) => void} onMessage
 */

export {};

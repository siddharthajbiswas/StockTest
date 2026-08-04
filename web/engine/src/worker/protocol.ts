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
 * enough that `web/frontend/src/api.ts` keeps its signatures.
 */

export type RequestKind =
  | "configure"
  | "init"
  | "health"
  | "pickers"
  | "timers"
  | "universes"
  | "tickers"
  | "searchTickers"
  | "tickerHistory"
  | "backtest"
  | "validate";

export interface WorkerRequest {
  id: number;
  kind: RequestKind;
  payload?: unknown;
}

export interface ProgressMessage {
  id: number;
  type: "progress";
  /** Mirrors walkforward's Progress. */
  phase: string;
  completed: number;
  total: number;
  label: string;
  elapsedMs: number;
}

export interface ResultMessage {
  id: number;
  type: "result";
  payload: unknown;
}

export interface ErrorMessage {
  id: number;
  type: "error";
  message: string;
  name: string;
  /** Structured detail for unknown-ticker errors, as the API used to send. */
  unavailable?: string[];
}

export type WorkerResponse = ProgressMessage | ResultMessage | ErrorMessage;

/** Minimal port abstraction so the handler runs under both browser Workers
 *  (`self`) and Node's `worker_threads` (`parentPort`) — which is what makes it
 *  testable off-browser. */
export interface PortLike {
  postMessage(msg: unknown): void;
  onMessage(cb: (msg: unknown) => void): void;
}

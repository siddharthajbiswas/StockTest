/**
 * UI-thread client for the engine worker.
 *
 * Presents a promise-based API shaped like the old HTTP client, so callers read
 * the same as before. Adds two things fetch couldn't give us: progress
 * callbacks for long runs, and real cancellation — aborting a validation
 * terminates the worker rather than leaving it churning, which mattered here
 * because the sweep is CPU-bound and there is no server to shed the load.
 */

import type {
  ProgressMessage, RequestKind, WorkerResponse,
} from "./protocol.js";

export interface CallOptions {
  onProgress?: (p: ProgressMessage) => void;
  signal?: AbortSignal;
}

interface Pending {
  resolve: (v: unknown) => void;
  reject: (e: Error) => void;
  onProgress?: (p: ProgressMessage) => void;
}

/** Error carrying the structured detail the API used to return for 404s. */
export class EngineError extends Error {
  constructor(message: string, readonly unavailable?: string[]) {
    super(message);
    this.name = "EngineError";
  }
}

export interface EngineClientOptions {
  /**
   * Constructs the worker. A FACTORY, not a URL, and that is deliberate:
   * bundlers only detect a worker from the literal
   * `new Worker(new URL("./worker.ts", import.meta.url), { type: "module" })`
   * pattern appearing at the call site. Taking a URL here and calling
   * `new Worker(url)` inside this class defeats that static analysis — Vite
   * silently emits no worker chunk and the app 404s at runtime.
   */
  createWorker: () => Worker;
  /** Base URL the worker fetches the data bundle from. */
  dataBase: string;
}

export class EngineClient {
  private worker: Worker | null = null;
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();

  constructor(private readonly opts: EngineClientOptions) {}

  private ensureWorker(): Worker {
    if (this.worker !== null) return this.worker;
    const w = this.opts.createWorker();
    w.onmessage = (e: MessageEvent) => this.onMessage(e.data as WorkerResponse);
    w.onerror = (e) => this.failAll(new Error(e.message || "Engine worker crashed"));
    // Configure before anything else. Messages are delivered in order and the
    // worker handles this one synchronously, so every later request sees the
    // data base already set. Passing it in the worker URL's query string would
    // be simpler but would require mutating that URL — see createWorker.
    w.postMessage({ id: 0, kind: "configure", payload: { dataBase: this.opts.dataBase } });
    this.worker = w;
    return w;
  }

  private onMessage(msg: WorkerResponse): void {
    const p = this.pending.get(msg.id);
    if (p === undefined) return;
    if (msg.type === "progress") { p.onProgress?.(msg); return; }
    this.pending.delete(msg.id);
    if (msg.type === "error") {
      p.reject(new EngineError(msg.message, msg.unavailable));
    } else {
      p.resolve(msg.payload);
    }
  }

  private failAll(err: Error): void {
    for (const [, p] of this.pending) p.reject(err);
    this.pending.clear();
  }

  /** Tear the worker down; any in-flight calls reject. Used by cancellation. */
  terminate(reason = "Engine worker terminated"): void {
    this.worker?.terminate();
    this.worker = null;
    this.failAll(new Error(reason));
  }

  private call<T>(kind: RequestKind, payload?: unknown, opts: CallOptions = {}): Promise<T> {
    const worker = this.ensureWorker();
    const id = this.nextId++;
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, {
        resolve: resolve as (v: unknown) => void,
        reject,
        onProgress: opts.onProgress,
      });
      if (opts.signal) {
        if (opts.signal.aborted) {
          this.pending.delete(id);
          reject(new DOMException("Cancelled", "AbortError"));
          return;
        }
        opts.signal.addEventListener("abort", () => {
          if (!this.pending.has(id)) return;
          this.pending.delete(id);
          // The worker is mid-sweep and cannot be interrupted cooperatively
          // without checking a flag on every combo; terminating is immediate
          // and the next call transparently spins up a fresh worker.
          this.terminate("Cancelled");
          reject(new DOMException("Cancelled", "AbortError"));
        }, { once: true });
      }
      worker.postMessage({ id, kind, payload });
    });
  }

  // ---- API surface (mirrors the old REST client) ----------------------
  init = () => this.call<HealthInfo>("init");
  health = () => this.call<HealthInfo>("health");
  pickers = () => this.call<{ pickers: unknown[] }>("pickers").then((d) => d.pickers);
  timers = () => this.call<{ timers: unknown[] }>("timers").then((d) => d.timers);
  universes = () =>
    this.call<{ universes: unknown[] }>("universes").then((d) => d.universes);
  allTickers = () => this.call<{ universe: unknown; tickers: unknown[] }>("tickers");
  searchTickers = (q: string, limit = 12) =>
    this.call<{ universe: unknown; results: unknown[] }>("searchTickers", { q, limit });
  backtest = <T>(req: unknown) => this.call<T>("backtest", req);
  validate = <T>(req: unknown, opts: CallOptions = {}) =>
    this.call<T>("validate", req, opts);
}

export interface HealthInfo {
  status: string;
  tickers_loaded: number;
  data_start?: string;
  data_end?: string;
}

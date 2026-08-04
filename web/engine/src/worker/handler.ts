/**
 * The worker's request dispatcher, independent of transport.
 *
 * Kept separate from the browser entry point so the same code can be driven
 * over Node's `worker_threads` in tests — the message handling and the
 * cross-thread behaviour get real coverage instead of being assumed.
 */

import { EngineService, InvalidStrategyError, UnknownTickersError, type Loader } from "../service.js";
import type { PortLike, WorkerRequest } from "./protocol.js";

export interface HandlerOptions {
  /** Fetches a bundle-relative path. */
  loader: Loader;
  /** Called for the `configure` message sent when the worker starts. Handled
   *  synchronously so later requests always see the configured base. */
  onConfigure?: (cfg: { dataBase: string }) => void;
}

export function createHandler(opts: HandlerOptions) {
  const svc = new EngineService(opts.loader);

  return async function handle(req: WorkerRequest, port: PortLike): Promise<void> {
    const reply = (payload: unknown) =>
      port.postMessage({ id: req.id, type: "result", payload });

    try {
      switch (req.kind) {
        case "configure":
          opts.onConfigure?.(req.payload as { dataBase: string });
          reply({ ok: true });
          break;
        case "init":
          await svc.init();
          reply(svc.health());
          break;
        case "health":
          await svc.init();
          reply(svc.health());
          break;
        case "pickers":
          await svc.init();
          reply({ pickers: svc.pickers() });
          break;
        case "timers":
          await svc.init();
          reply({ timers: svc.timers() });
          break;
        case "universes":
          await svc.init();
          reply({ universes: svc.universes() });
          break;
        case "tickers":
          await svc.init();
          reply(svc.allTickers());
          break;
        case "searchTickers": {
          await svc.init();
          const p = req.payload as { q: string; limit?: number };
          reply(svc.searchTickers(p.q, p.limit ?? 20));
          break;
        }
        case "tickerHistory": {
          const p = req.payload as {
            symbol: string; start?: string | null; end?: string | null; maxPoints?: number;
          };
          reply(await svc.tickerHistory(p.symbol, p.start ?? null, p.end ?? null, p.maxPoints));
          break;
        }
        case "backtest":
          reply(await svc.runBacktest(req.payload as any));
          break;
        case "validate": {
          const result = await svc.runValidation(req.payload as any, (pr) => {
            port.postMessage({
              id: req.id,
              type: "progress",
              phase: pr.phase,
              completed: pr.completed,
              total: pr.total,
              label: pr.label,
              elapsedMs: pr.elapsedMs,
            });
          });
          reply(result);
          break;
        }
        default:
          throw new Error(`Unknown request kind: ${(req as WorkerRequest).kind}`);
      }
    } catch (e) {
      const err = e as Error;
      port.postMessage({
        id: req.id,
        type: "error",
        name: err.name ?? "Error",
        message: err.message ?? String(e),
        ...(err instanceof UnknownTickersError ? { unavailable: err.missing } : {}),
      });
      // InvalidStrategyError and UnknownTickersError are expected user-input
      // failures and are reported, not rethrown — a worker that throws out of
      // its message handler tears down the whole thread.
      if (!(err instanceof InvalidStrategyError) && !(err instanceof UnknownTickersError)) {
        // Still surfaced to the client above; logged for diagnostics.
        console.error("[engine-worker]", err);
      }
    }
  };
}

/** Wire a handler to a port and start serving. */
export function serve(port: PortLike, opts: HandlerOptions): void {
  const handle = createHandler(opts);
  port.onMessage((msg) => {
    void handle(msg as WorkerRequest, port);
  });
}

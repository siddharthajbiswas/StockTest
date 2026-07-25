import type {
  BacktestRequest,
  BacktestResponse,
  Picker,
  SavedStrategy,
  StrategyConfig,
  TickerRecord,
  Timer,
  UniverseNote,
  UniverseOption,
  ValidateRequest,
  ValidationResult,
} from "./types";

// Base URL for the backend API. Empty in dev, where Vite proxies same-origin
// paths (see vite.config.ts) to localhost:8000. Set to the backend's absolute
// URL at build time (VITE_API_BASE) when the frontend is served from a
// different origin than the API — e.g. the app on GitHub Pages at
// biswas.net/sid/stocktest and the backend on stocktest-api.biswas.net.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const api = (path: string) => `${API_BASE}${path}`;

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(api(url));
  if (!res.ok) throw await toError(res);
  return res.json();
}

async function toError(res: Response): Promise<Error> {
  let detail: unknown;
  try {
    detail = (await res.json())?.detail;
  } catch {
    detail = res.statusText;
  }
  // The backend sends structured 404s for unknown tickers, etc.
  if (detail && typeof detail === "object") {
    const d = detail as { message?: string; unavailable?: string[] };
    const parts = [d.message ?? "Request failed"];
    if (d.unavailable?.length) parts.push(`Unavailable: ${d.unavailable.join(", ")}`);
    return new Error(parts.join(" — "));
  }
  return new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
}

export interface HealthInfo {
  status: string;
  tickers_loaded: number;
  data_start?: string;
  data_end?: string;
}

export const fetchHealth = () => getJSON<HealthInfo>("/health");

export const fetchPickers = () =>
  getJSON<{ pickers: Picker[] }>("/pickers").then((d) => d.pickers);

export const fetchTimers = () =>
  getJSON<{ timers: Timer[] }>("/timers").then((d) => d.timers);

export const fetchUniverseOptions = () =>
  getJSON<{ universes: UniverseOption[] }>("/universe/options").then((d) => d.universes);

export const fetchAllTickers = () =>
  getJSON<{ universe: UniverseNote; tickers: TickerRecord[] }>("/tickers");

export const searchTickers = (q: string, limit = 12) =>
  getJSON<{ universe: UniverseNote; results: TickerRecord[] }>(
    `/tickers/search?q=${encodeURIComponent(q)}&limit=${limit}`,
  );

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  const res = await fetch(api("/backtest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw await toError(res);
  return res.json();
}

export const listStrategies = () =>
  getJSON<{ strategies: SavedStrategy[] }>("/strategies/mine").then((d) => d.strategies);

export async function saveStrategy(name: string, config: StrategyConfig): Promise<SavedStrategy> {
  const res = await fetch(api("/strategies/mine"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, config }),
  });
  if (!res.ok) throw await toError(res);
  return res.json();
}

export async function deleteStrategy(id: string): Promise<void> {
  const res = await fetch(api(`/strategies/mine/${id}`), { method: "DELETE" });
  if (!res.ok) throw await toError(res);
}

// ----- out-of-sample validation (submit a job, then poll for the result) -----

async function startValidation(req: ValidateRequest): Promise<string> {
  const res = await fetch(api("/validate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw await toError(res);
  return (await res.json()).job_id as string;
}

interface ValidationJob {
  status: "running" | "done" | "error";
  result?: ValidationResult;
  error?: string;
}

/**
 * Run an out-of-sample validation end-to-end: submit the job, then poll until
 * it finishes. This is intentionally slower than a backtest (it reruns many
 * combos over many windows), so callers should show a loading state.
 */
export async function validateStrategy(
  req: ValidateRequest,
  opts: { intervalMs?: number; signal?: AbortSignal } = {},
): Promise<ValidationResult> {
  const { intervalMs = 1500, signal } = opts;
  const jobId = await startValidation(req);
  for (;;) {
    if (signal?.aborted) throw new DOMException("Validation cancelled", "AbortError");
    await new Promise((r) => setTimeout(r, intervalMs));
    if (signal?.aborted) throw new DOMException("Validation cancelled", "AbortError");
    const res = await fetch(api(`/validate/${jobId}`), { signal });
    if (!res.ok) throw await toError(res);
    const job = (await res.json()) as ValidationJob;
    if (job.status === "done" && job.result) return job.result;
    if (job.status === "error") throw new Error(job.error || "Validation failed");
  }
}

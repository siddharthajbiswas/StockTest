/**
 * The engine worker, over real cross-thread messaging (Phase 5).
 *
 * Uses Node's `worker_threads` to run the same handler the browser Worker runs,
 * so the protocol, the concurrency, the progress stream and the error paths are
 * all exercised for real rather than by calling the dispatcher in-process.
 *
 * The headline assertion is the one the phase exists for: while a 100-combo
 * sweep is running on the worker, the host thread must stay responsive.
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Worker } from "node:worker_threads";
import test from "node:test";

import type { WorkerResponse } from "../src/worker/protocol.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..", "..");
const DATA = join(ROOT, "build", "webdata");
const GOLDEN = join(ROOT, "golden");
const HOST = join(HERE, "worker-host.js");

/** Minimal stand-in for the browser client, over a Node worker. */
class TestClient {
  private readonly worker: Worker;
  private nextId = 1;
  private readonly pending = new Map<number, {
    resolve: (v: any) => void; reject: (e: Error) => void;
    onProgress?: (p: any) => void;
  }>();

  constructor() {
    this.worker = new Worker(HOST, { workerData: { base: DATA } });
    this.worker.on("message", (msg: WorkerResponse) => {
      const p = this.pending.get(msg.id);
      if (p === undefined) return;
      if (msg.type === "progress") { p.onProgress?.(msg); return; }
      this.pending.delete(msg.id);
      if (msg.type === "error") {
        const e = new Error(msg.message);
        e.name = msg.name;
        (e as any).unavailable = msg.unavailable;
        p.reject(e);
      } else p.resolve(msg.payload);
    });
    this.worker.on("error", (e) => {
      for (const [, p] of this.pending) p.reject(e);
      this.pending.clear();
    });
  }

  call<T>(kind: string, payload?: unknown, onProgress?: (p: any) => void): Promise<T> {
    const id = this.nextId++;
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onProgress });
      this.worker.postMessage({ id, kind, payload });
    });
  }

  async close(): Promise<void> { await this.worker.terminate(); }
}

// ---------------------------------------------------------------------------
test("worker serves catalog and discovery endpoints", async () => {
  const c = new TestClient();
  try {
    const health = await c.call<any>("init");
    assert.equal(health.status, "ok");
    assert.equal(health.tickers_loaded, 528);
    assert.ok(health.data_start && health.data_end, "data range reported");

    const { pickers } = await c.call<any>("pickers");
    const { timers } = await c.call<any>("timers");
    const { universes } = await c.call<any>("universes");
    assert.equal(pickers.length, 10);
    assert.equal(timers.length, 10);
    assert.equal(universes.length, 2);
    // The catalog is the UI's source of truth for the look-ahead warnings.
    assert.equal(pickers.filter((p: any) => p.look_ahead_risk).length, 7);

    const all = await c.call<any>("tickers");
    assert.equal(all.tickers.length, 528);
    assert.equal(all.universe.count, 528);
  } finally { await c.close(); }
});

test("ticker search matches the Python index", async () => {
  const c = new TestClient();
  try {
    const fx = JSON.parse(readFileSync(join(DATA, "search.json"), "utf8"));
    for (const q of fx.queries) {
      const got = await c.call<any>("searchTickers", { q: q.q, limit: q.limit });
      assert.deepEqual(
        got.results.map((r: any) => r.symbol), q.results,
        `search(${JSON.stringify(q.q)})`,
      );
    }
  } finally { await c.close(); }
});

test("ticker history serves a downsampled close series with names", async () => {
  const c = new TestClient();
  try {
    const full = await c.call<any>("tickerHistory", { symbol: "AAPL" });
    assert.equal(full.symbol, "AAPL");
    assert.equal(full.name, "Apple Inc.", "company name comes from the ticker index");
    assert.ok(full.n_bars > 5000, `AAPL should have deep history, got ${full.n_bars}`);
    // Downsampled to the cap, with the final bar always retained.
    assert.ok(full.dates.length <= 901, `expected <= 901 points, got ${full.dates.length}`);
    assert.equal(full.dates[full.dates.length - 1], full.last_date);
    assert.equal(full.dates[0], full.first_date);
    assert.equal(full.dates.length, full.closes.length);
    assert.ok(full.closes.every((v: number) => Number.isFinite(v) && v > 0));
    // Ascending, which the chart's binary search over dates depends on.
    for (let i = 1; i < full.dates.length; i++) {
      assert.ok(full.dates[i] > full.dates[i - 1], `dates must ascend at ${i}`);
    }

    // A clipped window returns fewer bars and no downsampling.
    const win = await c.call<any>("tickerHistory", {
      symbol: "AAPL", start: "2020-01-01", end: "2020-12-31",
    });
    assert.ok(win.n_bars > 240 && win.n_bars < 260, `2020 trading days, got ${win.n_bars}`);
    assert.equal(win.dates.length, win.n_bars, "under the cap, nothing is dropped");
    assert.ok(win.first_date >= "2020-01-01" && win.last_date <= "2020-12-31");

    // Unknown symbols are the same structured error the backtest path raises.
    await assert.rejects(() => c.call("tickerHistory", { symbol: "NOTREAL" }));
    // ...and the worker is still alive afterwards.
    assert.equal((await c.call<any>("tickerHistory", { symbol: "MSFT" })).symbol, "MSFT");
  } finally { await c.close(); }
});

test("backtest over the worker matches the golden oracle", async () => {
  const c = new TestClient();
  try {
    for (const id of ["manual_buyhold_tax", "momentum_macross_pit"]) {
      const golden = JSON.parse(readFileSync(join(GOLDEN, `${id}.json`), "utf8"));
      const res = await c.call<any>("backtest", golden.request);
      const gm = golden.result.metrics;
      // Spot-check the headline numbers; full-payload parity is covered by
      // parity.test.ts. What is under test here is the transport.
      for (const k of ["final_value", "total_tax", "sharpe", "max_drawdown", "cagr"]) {
        if (gm[k] === null) continue;
        const diff = Math.abs(res.metrics[k] - gm[k]);
        assert.ok(
          diff <= 1e-9 * Math.max(1, Math.abs(gm[k])),
          `${id}.${k}: ${res.metrics[k]} vs ${gm[k]}`,
        );
      }
      assert.equal(res.trades.length, golden.result.trades.length, `${id} trade count`);
    }
  } finally { await c.close(); }
});

test("unknown tickers come back as a structured error, worker survives", async () => {
  const c = new TestClient();
  try {
    await assert.rejects(
      () => c.call("backtest", {
        tickers: ["AAPL", "NOTAREALTICKER"], timer_id: "buy_hold",
        start: "2020-01-01", end: "2021-12-31",
      }),
      (e: any) => {
        assert.equal(e.name, "UnknownTickersError");
        assert.deepEqual(e.unavailable, ["NOTAREALTICKER"]);
        return true;
      },
    );
    // The worker must still be alive: a thrown handler would kill the thread.
    const health = await c.call<any>("health");
    assert.equal(health.status, "ok");
  } finally { await c.close(); }
});

test("concurrent requests are routed to the right callers", async () => {
  const c = new TestClient();
  try {
    const [h, p, t, s] = await Promise.all([
      c.call<any>("health"),
      c.call<any>("pickers"),
      c.call<any>("timers"),
      c.call<any>("searchTickers", { q: "AAPL", limit: 3 }),
    ]);
    assert.equal(h.status, "ok");
    assert.equal(p.pickers.length, 10);
    assert.equal(t.timers.length, 10);
    assert.equal(s.results[0].symbol, "AAPL");
  } finally { await c.close(); }
});

test("a 100-combo validation streams progress and leaves the host responsive",
  { timeout: 1_800_000 }, async () => {
    const c = new TestClient();
    try {
      // Keep the host thread measurably busy-free: a 5ms interval should tick
      // steadily throughout if the sweep really is on the worker thread.
      let ticks = 0;
      const timer = setInterval(() => { ticks++; }, 5);
      const progress: any[] = [];
      const t0 = Date.now();

      const res = await c.call<any>("validate", {
        picker_id: "relative_strength", picker_params: {},
        timer_id: "buy_hold", timer_params: {},
        top_n: 15, rebalance: "M", universe: "all",
        start: "2019-01-01", end: "2021-12-31",
        commission_pct: 0.0005, slippage_pct: 0.0005,
        tax: {
          enabled: true, short_term_rate: 0.35,
          long_term_rate: 0.15, long_term_days: 365,
        },
        split: "2020-07-01", train_years: 1, step_years: 1, price_only: false,
      }, (p) => progress.push(p));

      const elapsed = Date.now() - t0;
      clearInterval(timer);

      // Progress actually streamed, one message per combo plus the walk-forward.
      const curveMsgs = progress.filter((p) => p.phase === "curves");
      assert.equal(curveMsgs.length, 100, "one progress message per combo");
      assert.equal(curveMsgs[curveMsgs.length - 1].completed, 100, "reached 100%");
      assert.ok(progress.some((p) => p.phase === "done"), "signalled completion");

      // The host thread stayed live throughout. This is the whole point of the
      // phase: in-process, a 100-combo sweep blocks everything.
      const expected = elapsed / 5;
      assert.ok(
        ticks > expected * 0.5,
        `host thread was starved: ${ticks} ticks over ${elapsed}ms ` +
        `(expected ~${expected.toFixed(0)})`,
      );

      // And the result is the real thing.
      const golden = JSON.parse(
        readFileSync(join(GOLDEN, "validation", "validate_all_pickers.json"), "utf8"),
      );
      assert.equal(res.meta.n_baseline_combos, 100);
      assert.equal(
        res.verdict.level, golden.result.verdict.level,
        "verdict matches the Python oracle",
      );
      assert.ok(
        Math.abs(res.holdout.spearman - golden.result.holdout.spearman) < 1e-9,
        "spearman matches the Python oracle",
      );
    } finally { await c.close(); }
  });

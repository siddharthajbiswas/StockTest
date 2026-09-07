/**
 * In-browser parity + performance harness (Phase 9).
 *
 * The Node test suite already checks the ported engine against the Phase 0
 * golden oracle, but it runs on the filesystem with Node's module loader. This
 * runs the SAME golden cases through the shipped path instead: a real Web
 * Worker, in a real browser, decoding the real gzipped bundle over HTTP.
 *
 * That is the configuration users actually get, and it is the only place where
 * DecompressionStream, structured-clone of the response payload, and browser
 * float behaviour are all exercised together.
 *
 * Dev only — reachable at /verify.html via `npm run dev`. `vite build` emits
 * just index.html, so this never ships.
 */
import { EngineClient } from "../../engine/src/worker/client";
const REL_TOL = 1e-9;
const ABS_TOL = 1e-9;
const client = new EngineClient({
  createWorker: () =>
    new Worker(new URL("../../engine/src/worker/worker.js", import.meta.url), {
      type: "module",
    }),
  dataBase: new URL("data/", document.baseURI).href,
});
const out = document.getElementById("out");
function log(html) {
  out.insertAdjacentHTML("beforeend", html);
}
// ---------------------------------------------------------------------------

/** Same comparison contract as golden/test_golden_parity.py. */
function compare(golden, actual, path, errors) {
  if (
    golden === null ||
    actual === null ||
    golden === undefined ||
    actual === undefined
  ) {
    if (golden !== actual)
      errors.push(
        `${path}: ${JSON.stringify(actual)} != ${JSON.stringify(golden)}`,
      );
    return;
  }
  if (Array.isArray(golden) && Array.isArray(actual)) {
    if (golden.length !== actual.length) {
      errors.push(`${path}: length ${actual.length} != ${golden.length}`);
      return;
    }
    for (let i = 0; i < golden.length; i++)
      compare(golden[i], actual[i], `${path}[${i}]`, errors);
    return;
  }
  if (typeof golden === "object" && typeof actual === "object") {
    const g = golden;
    const a = actual;
    for (const k of new Set([...Object.keys(g), ...Object.keys(a)])) {
      if (!(k in g)) {
        errors.push(`${path}.${k}: unexpected`);
        continue;
      }
      if (!(k in a)) {
        errors.push(`${path}.${k}: missing`);
        continue;
      }
      compare(g[k], a[k], `${path}.${k}`, errors);
    }
    return;
  }
  if (typeof golden === "number" && typeof actual === "number") {
    if (golden === actual) return;
    const diff = Math.abs(golden - actual);
    if (
      diff <= ABS_TOL ||
      diff <= REL_TOL * Math.max(Math.abs(golden), Math.abs(actual))
    )
      return;
    errors.push(
      `${path}: ${actual} != ${golden} (diff ${diff.toExponential(3)})`,
    );
    return;
  }
  if (golden !== actual)
    errors.push(
      `${path}: ${JSON.stringify(actual)} != ${JSON.stringify(golden)}`,
    );
}

/** Count comparable leaves, so "passed" is backed by a number. */
function leaves(v) {
  if (v === null || v === undefined) return 1;
  if (Array.isArray(v)) return v.reduce((a, x) => a + leaves(x), 0);
  if (typeof v === "object") {
    return Object.values(v).reduce((a, x) => a + leaves(x), 0);
  }
  return 1;
}

const CASES = [
  "cover_picker_earnings_surprise",
  "cover_picker_growth_revenue",
  "cover_picker_high_dividend",
  "cover_picker_high_dividend_topn25",
  "cover_picker_price_to_book",
  "cover_picker_quality_roe",
  "cover_picker_small_cap",
  "cover_timer_bollinger",
  "cover_timer_dual_momentum",
  "cover_timer_macd",
  "cover_timer_momentum12",
  "cover_timer_turtle",
  "cover_timer_vol_reversion",
  "manual_buyhold_notax",
  "manual_buyhold_tax",
  "manual_macross_gfc",
  "manual_macross_tax",
  "momentum_buyhold_m",
  "momentum_daily_covid",
  "momentum_macross_pit",
  "random_seeded",
  "relstr_rsi_q",
  "value_trendstop_w",
];
async function run() {
  const t00 = performance.now();
  log(`<h2>1 · Golden parity — ${CASES.length} backtest cases</h2>
       <table><thead><tr><th>case</th><th>days</th><th>trades</th>
       <th>values compared</th><th>ms</th><th>result</th></tr></thead><tbody id="tb"></tbody></table>`);
  const tb = document.getElementById("tb");
  let pass = 0,
    fail = 0,
    totalLeaves = 0;
  const failures = [];
  for (const id of CASES) {
    const golden = await (await fetch(`/golden/${id}.json`)).json();
    const t0 = performance.now();
    let errors = [];
    let actual = null;
    try {
      actual = await client.backtest(golden.request);
      compare(golden.result, actual, "result", errors);
    } catch (e) {
      errors = [`threw: ${e.message}`];
    }
    const ms = Math.round(performance.now() - t0);
    const n = leaves(golden.result);
    totalLeaves += n;
    const ok = errors.length === 0;
    ok ? pass++ : fail++;
    if (!ok) failures.push(`${id}: ${errors.slice(0, 3).join("; ")}`);
    tb.insertAdjacentHTML(
      "beforeend",
      `<tr class="${ok ? "ok" : "bad"}"><td>${id}</td>
       <td>${actual?.equity_curve?.dates?.length ?? "-"}</td>
       <td>${actual?.trades?.length ?? "-"}</td>
       <td>${n.toLocaleString()}</td><td>${ms}</td>
       <td>${ok ? "PASS" : "FAIL"}</td></tr>`,
    );
    await new Promise((r) => setTimeout(r, 0));
  }
  // ---- validation goldens ----
  log(`<h2>2 · Golden parity — validation (out-of-sample)</h2>
       <table><thead><tr><th>case</th><th>combos</th><th>values</th><th>ms</th>
       <th>result</th></tr></thead><tbody id="vb"></tbody></table>`);
  const vb = document.getElementById("vb");
  for (const id of ["validate_price_only", "validate_all_pickers"]) {
    const golden = await (await fetch(`/golden/validation/${id}.json`)).json();
    const cfg = golden.config,
      p = golden.params;
    const t0 = performance.now();
    let errors = [];
    let actual = null;
    try {
      actual = await client.validate({
        picker_id: cfg.picker_id,
        picker_params: cfg.picker_params,
        tickers: null,
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
        split: p.split,
        train_years: p.train_years,
        step_years: p.step_years,
        price_only: p.price_only,
      });
      compare(golden.result, actual, "result", errors);
    } catch (e) {
      errors = [`threw: ${e.message}`];
    }
    const ms = Math.round(performance.now() - t0);
    const n = leaves(golden.result);
    totalLeaves += n;
    const ok = errors.length === 0;
    ok ? pass++ : fail++;
    if (!ok) failures.push(`${id}: ${errors.slice(0, 3).join("; ")}`);
    vb.insertAdjacentHTML(
      "beforeend",
      `<tr class="${ok ? "ok" : "bad"}"><td>${id}</td>
       <td>${actual?.meta?.n_baseline_combos ?? "-"}</td><td>${n.toLocaleString()}</td>
       <td>${ms}</td><td>${ok ? "PASS" : "FAIL"}</td></tr>`,
    );
  }
  log(`<p class="${fail ? "bad" : "ok"}"><strong>${pass} passed, ${fail} failed</strong> —
       ${totalLeaves.toLocaleString()} values compared against the Python oracle,
       in ${((performance.now() - t00) / 1000).toFixed(1)}s.</p>`);
  if (failures.length) log(`<pre class="bad">${failures.join("\n")}</pre>`);
  await benchmark();
}
// ---------------------------------------------------------------------------
async function benchmark() {
  log(
    `<h2>3 · Performance — the 100-combo sweep</h2><div id="bench">running…</div>`,
  );
  const bench = document.getElementById("bench");
  // A 10-year window over the point-in-time universe: the heaviest thing the
  // UI can ask for. price_only=false runs all 10 pickers x 10 timers.
  const req = {
    picker_id: "momentum",
    picker_params: {},
    tickers: null,
    timer_id: "buy_hold",
    timer_params: {},
    top_n: 15,
    rebalance: "M",
    universe: "sp500-pit",
    start: "2014-01-01",
    end: "2024-01-01",
    commission_pct: 0.0005,
    slippage_pct: 0.0005,
    tax: {
      enabled: true,
      short_term_rate: 0.35,
      long_term_rate: 0.15,
      long_term_days: 365,
    },
    split: null,
    train_years: 3,
    step_years: 1,
    price_only: false,
  };
  // Main-thread blocking, measured with the Long Tasks API.
  //
  // The obvious instrument — an interval timer that should keep ticking — is
  // WRONG in a background tab: Chrome clamps setInterval to ~1/s when
  // document.visibilityState is "hidden", which looks identical to a blocked
  // thread. (Measured: 3 ticks in 2.6 s with no work running at all.)
  // PerformanceObserver longtask entries record actual >50 ms blocks of the
  // main thread and are not throttled, so they answer the real question:
  // does the sweep freeze the UI?
  const longTasks = [];
  let observer = null;
  try {
    observer = new PerformanceObserver((list) => {
      for (const e of list.getEntries()) longTasks.push(e.duration);
    });
    observer.observe({ entryTypes: ["longtask"] });
  } catch {
    /* Long Tasks API unavailable */
  }
  let ticks = 0;
  const timer = setInterval(() => {
    ticks++;
  }, 10);
  let lastProgress = null;
  const t0 = performance.now();
  const res = await client.validate(req, {
    onProgress: (p) => {
      lastProgress = p;
      if (p.phase === "curves") {
        bench.textContent = `sweeping ${p.completed}/${p.total} — ${p.label}`;
      }
    },
  });
  const ms = performance.now() - t0;
  clearInterval(timer);
  observer?.disconnect();
  const blockedMs = longTasks.reduce((a, b) => a + b, 0);
  // Under 10% of wall clock spent in long tasks means the page stayed usable.
  const responsive = blockedMs < ms * 0.1;
  const hidden = document.visibilityState === "hidden";
  bench.innerHTML = `
    <table><tbody>
      <tr><td>combos swept</td><td><strong>${res.meta.n_baseline_combos}</strong></td></tr>
      <tr><td>window</td><td>${res.meta.period.start} → ${res.meta.period.end}
          (${res.meta.span_years}y, 528 tickers, point-in-time)</td></tr>
      <tr><td>total wall clock</td><td><strong>${(ms / 1000).toFixed(2)} s</strong></td></tr>
      <tr><td>per combo</td><td>${(ms / res.meta.n_baseline_combos).toFixed(0)} ms</td></tr>
      <tr><td>progress messages</td><td>${lastProgress ? "streamed to completion" : "none"}</td></tr>
      <tr class="${responsive ? "ok" : "bad"}"><td>main thread blocked</td>
          <td><strong>${longTasks.length} long task(s), ${blockedMs.toFixed(0)} ms total</strong>
          of ${(ms / 1000).toFixed(2)} s wall clock
          (${((blockedMs / ms) * 100).toFixed(1)}%) —
          <strong>${responsive ? "stayed responsive" : "BLOCKED"}</strong></td></tr>
      <tr><td class="sub">timer ticks (advisory)</td>
          <td class="sub">${ticks} ticks of a 10 ms interval${
            hidden
              ? " — tab is HIDDEN, so this is throttled to ~1/s and not meaningful"
              : ""
          }</td></tr>
      <tr><td>verdict</td><td>${res.verdict.level} (${res.verdict.score}/3)</td></tr>
    </tbody></table>`;
  // Single backtests, for the interactive path.
  log(
    `<h2>4 · Performance — single backtests</h2><div id="single">running…</div>`,
  );
  const rows = [];
  for (const [label, r] of [
    [
      "manual basket, 5 tickers, 6y",
      {
        tickers: ["AAPL", "MSFT", "JNJ", "XOM", "KO"],
        timer_id: "buy_hold",
        start: "2016-01-01",
        end: "2021-12-31",
        commission_pct: 0.0005,
        slippage_pct: 0.0005,
        tax: {
          enabled: true,
          short_term_rate: 0.35,
          long_term_rate: 0.15,
          long_term_days: 365,
        },
      },
    ],
    [
      "momentum, PIT universe, 10y",
      {
        picker_id: "momentum",
        picker_params: {},
        timer_id: "buy_hold",
        top_n: 15,
        rebalance: "M",
        universe: "sp500-pit",
        start: "2014-01-01",
        end: "2024-01-01",
        commission_pct: 0.0005,
        slippage_pct: 0.0005,
        tax: {
          enabled: true,
          short_term_rate: 0.35,
          long_term_rate: 0.15,
          long_term_days: 365,
        },
      },
    ],
    [
      "momentum, daily rebalance, 2y",
      {
        picker_id: "momentum",
        picker_params: {},
        timer_id: "buy_hold",
        top_n: 10,
        rebalance: "D",
        universe: "all",
        start: "2019-01-01",
        end: "2020-12-31",
        commission_pct: 0.0005,
        slippage_pct: 0.0005,
        tax: {
          enabled: true,
          short_term_rate: 0.35,
          long_term_rate: 0.15,
          long_term_days: 365,
        },
      },
    ],
  ]) {
    const t = performance.now();
    const out = await client.backtest(r);
    rows.push(`<tr><td>${label}</td><td>${out.trades.length} trades</td>
               <td><strong>${Math.round(performance.now() - t)} ms</strong></td></tr>`);
  }
  document.getElementById("single").innerHTML =
    `<table><tbody>${rows.join("")}</tbody></table>`;
  log(`<p class="ok"><strong>Done.</strong></p>`);
}
run().catch((e) => log(`<pre class="bad">${e.stack}</pre>`));

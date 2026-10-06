import { useEffect, useMemo, useState } from "react";
import {
  deleteStrategy,
  fetchAllTickers,
  fetchHealth,
  fetchPickers,
  fetchTimers,
  fetchUniverseOptions,
  listStrategies,
  runBacktest,
  saveStrategy,
} from "./api";
import { ModeCards } from "./components/ModeCards";
import { ConceptExplainer } from "./components/ConceptExplainer";
import { PickerGrid } from "./components/PickerGrid";
import { TimerGrid } from "./components/TimerGrid";
import { TickerPicker } from "./components/TickerPicker";
import { SettingsPanel } from "./components/SettingsPanel";
import { Results } from "./components/Results";
import { Onboarding } from "./components/Onboarding";
import { ParamEditor, defaultParams } from "./components/ParamEditor";
import { MyStrategies } from "./components/MyStrategies";
import { SaveDialog } from "./components/SaveDialog";
import { ParticleField } from "./components/ParticleField";
import { prettyId } from "./format";
const TOUR_KEY = "stocktest_tour_done_v1";
/**
 * The survivorship-free ETF menu the tax-managed preset ranks over. Mirrors
 * DEFAULT_MENU in strategies/tax_managed.py. Every fund on it still trades, so
 * unlike the per-stock data there is no survivor-only bias to discount.
 */
const TAX_MANAGED_MENU = [
  "SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
  "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
];
const DEFAULT_CONFIG = {
  start: "2014-01-01",
  end: "2024-01-01",
  universe: "sp500-pit",
  taxDefaults: true,
  stRatePct: 35,
  ltRatePct: 15,
  topN: 15,
  rebalance: "M",
  // How the portfolio is allowed to reach its target. "standard" rebalances
  // freely; "tax_managed" rations sales against a yearly realized-gain budget.
  tradeRule: "standard",
  gainBudgetPct: 1,
  // Extra price history loaded before the start date so long-lookback signals
  // are warm on day one. Clipped out of the reported curve and metrics.
  warmupDays: 450,
  commissionBps: 5,
  slippageBps: 5,
  // Seeds for the rate helper. A no-income-tax state is the neutral starting
  // point: it makes the state component visibly zero until you pick your own,
  // rather than quietly baking someone else's state tax into the default.
  taxStatus: "single",
  taxIncome: 120000,
  taxState: "TX",
};
const TOUR_STEPS = [
  {
    title: "Welcome to StockTest 👋",
    body: "Backtest a stock strategy in a few clicks and see how it would have performed historically — after taxes and trading costs, not just on paper.",
  },
  {
    title: "First, choose who picks the stocks",
    body: "Pick a basket yourself, or start from a proven strategy (momentum, value, quality…) and let it choose. This is the only decision you must make to begin.",
    targetId: "tour-mode",
  },
  {
    title: "Two choices: what, and when",
    body: "A strategy decides WHICH stocks you own — momentum buys the fastest risers, value buys the cheapest. A timer then decides WHEN to actually hold them — always (Buy & Hold), only while trending up, or only after a dip. You pick one of each, and they combine.",
  },
  {
    title: "Why they’re separate",
    body: "Because they fail differently. A strategy can choose good companies at bad moments; a timer can be perfectly disciplined about a basket of duds. Keeping them apart shows you which half is actually doing the work.",
  },
  {
    title: "Save and reuse your strategies",
    body: "Tune the parameters, then Save a strategy to re-run or edit it later from “My strategies” — no reconfiguring from scratch.",
  },
  {
    title: "Try an example",
    body: "New here? Run a sample momentum strategy over a 10-year window right now, then tweak it.",
    targetId: "tour-example",
  },
];
export default function App() {
  const [pickers, setPickers] = useState([]);
  const [timers, setTimers] = useState([]);
  const [universeOptions, setUniverseOptions] = useState([]);
  const [dataRange, setDataRange] = useState(null);
  const [universeNote, setUniverseNote] = useState(null);
  /** symbol -> company name, for trade-log hovers and the stock detail view. */
  const [tickerNames, setTickerNames] = useState(new Map());
  const [loadError, setLoadError] = useState(null);
  const [ready, setReady] = useState(false);
  const [mode, setMode] = useState(null);
  const [manualTickers, setManualTickers] = useState([]);
  const [pickerId, setPickerId] = useState(null);
  const [pickerParams, setPickerParams] = useState({});
  const [timerId, setTimerId] = useState(null);
  const [timerParams, setTimerParams] = useState({});
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  // The exact config that produced `result`, so the results sheet can validate
  // the same combo out-of-sample (not whatever the wizard currently shows).
  const [resultConfig, setResultConfig] = useState(null);
  const [runError, setRunError] = useState(null);
  const [saved, setSaved] = useState([]);
  const [showSave, setShowSave] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [showTour, setShowTour] = useState(false);
  useEffect(() => {
    Promise.all([
      fetchPickers(),
      fetchTimers(),
      fetchUniverseOptions(),
      fetchAllTickers(),
      listStrategies().catch(() => []),
      fetchHealth().catch(() => null),
    ])
      .then(([p, t, u, tk, st, h]) => {
        setPickers(p);
        setTimers(t);
        setUniverseOptions(u);
        setUniverseNote(tk.universe);
        setTickerNames(
          new Map(
            tk.tickers.flatMap((r) => (r.name ? [[r.symbol, r.name]] : [])),
          ),
        );
        setSaved(st);
        if (h?.data_start && h?.data_end) {
          setDataRange({ start: h.data_start, end: h.data_end });
        }
        setReady(true);
        if (!localStorage.getItem(TOUR_KEY)) setShowTour(true);
      })
      .catch((e) => setLoadError(String(e.message ?? e)));
  }, []);
  const update = (patch) => setConfig((c) => ({ ...c, ...patch }));
  const currentPicker = pickers.find((p) => p.id === pickerId);
  const currentTimer = timers.find((t) => t.id === timerId);
  const stocksReady = mode === "manual" ? manualTickers.length > 0 : !!pickerId;
  const canRun = !!mode && stocksReady && !!timerId && !running;
  // Picking a strategy pre-fills its default params.
  function selectPicker(id) {
    setPickerId(id);
    const p = pickers.find((x) => x.id === id);
    setPickerParams(p ? defaultParams(p.params) : {});
  }
  function selectTimer(id) {
    setTimerId(id);
    const t = timers.find((x) => x.id === id);
    setTimerParams(t ? defaultParams(t.params) : {});
  }
  function pickMode(m) {
    setMode(m);
    if (m === "manual") {
      setPickerId(null);
      setPickerParams({});
    } else {
      setManualTickers([]);
    }
  }
  const summaryText = useMemo(() => {
    if (!mode) return "Choose a mode to begin";
    const who =
      mode === "manual"
        ? `${manualTickers.length} stock${manualTickers.length === 1 ? "" : "s"}`
        : pickerId
          ? prettyId(pickerId)
          : "a strategy";
    const when = timerId ? ` · ${prettyId(timerId)}` : "";
    return `${who}${when} · ${config.start} → ${config.end}`;
  }, [mode, manualTickers, pickerId, timerId, config.start, config.end]);
  function taxSettings() {
    return config.taxDefaults
      ? {
          enabled: true,
          short_term_rate: 0.35,
          long_term_rate: 0.15,
          long_term_days: 365,
        }
      : {
          enabled: true,
          short_term_rate: config.stRatePct / 100,
          long_term_rate: config.ltRatePct / 100,
          long_term_days: 365,
        };
  }
  function buildConfig() {
    return {
      mode: mode === "manual" ? "manual" : "picker",
      picker_id: mode === "ai" ? pickerId : null,
      picker_params: mode === "ai" ? pickerParams : {},
      tickers: mode === "manual" ? manualTickers : null,
      timer_id: timerId,
      timer_params: timerParams,
      top_n: config.topN,
      rebalance: config.rebalance,
      universe: config.universe,
      menu: config.menu ?? null,
      trade_rule: config.tradeRule,
      gain_budget: config.gainBudgetPct / 100,
      wash_days: 31,
      start: config.start,
      end: config.end,
      warmup_days: config.warmupDays,
      commission_pct: config.commissionBps / 10000,
      slippage_pct: config.slippageBps / 10000,
      tax: taxSettings(),
    };
  }
  function toRequest(cfg) {
    const base = {
      timer_id: cfg.timer_id,
      timer_params: cfg.timer_params,
      start: cfg.start,
      end: cfg.end,
      warmup_days: cfg.warmup_days ?? 0,
      cash: 100000,
      commission_pct: cfg.commission_pct,
      slippage_pct: cfg.slippage_pct,
      trade_rule: cfg.trade_rule ?? "standard",
      gain_budget: cfg.gain_budget ?? 0.01,
      wash_days: cfg.wash_days ?? 31,
      tax: cfg.tax,
    };
    if (cfg.mode === "manual") return { ...base, tickers: cfg.tickers };
    return {
      ...base,
      picker_id: cfg.picker_id,
      picker_params: cfg.picker_params,
      top_n: cfg.top_n,
      rebalance: cfg.rebalance,
      universe: cfg.universe,
      menu: cfg.menu ?? null,
    };
  }
  async function runConfig(cfg) {
    setRunning(true);
    setRunError(null);
    try {
      setResult(await runBacktest(toRequest(cfg)));
      setResultConfig(cfg);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }
  const run = () => runConfig(buildConfig());
  // Load a saved/example config back into the wizard.
  function loadConfig(cfg) {
    const isManual = cfg.mode === "manual";
    setMode(isManual ? "manual" : "ai");
    setManualTickers(isManual ? (cfg.tickers ?? []) : []);
    setPickerId(isManual ? null : cfg.picker_id);
    setPickerParams(isManual ? {} : (cfg.picker_params ?? {}));
    setTimerId(cfg.timer_id);
    setTimerParams(cfg.timer_params ?? {});
    const usesDefaultTax =
      cfg.tax.enabled &&
      cfg.tax.short_term_rate === 0.35 &&
      cfg.tax.long_term_rate === 0.15;
    setConfig((prev) => ({
      start: cfg.start ?? DEFAULT_CONFIG.start,
      end: cfg.end ?? DEFAULT_CONFIG.end,
      universe: cfg.universe,
      taxDefaults: usesDefaultTax,
      stRatePct: Math.round(cfg.tax.short_term_rate * 10000) / 100,
      ltRatePct: Math.round(cfg.tax.long_term_rate * 10000) / 100,
      topN: cfg.top_n,
      rebalance: cfg.rebalance,
      menu: cfg.menu ?? null,
      tradeRule: cfg.trade_rule ?? "standard",
      gainBudgetPct: Math.round((cfg.gain_budget ?? 0.01) * 10000) / 100,
      warmupDays: cfg.warmup_days ?? 0,
      commissionBps: Math.round(cfg.commission_pct * 10000),
      slippageBps: Math.round(cfg.slippage_pct * 10000),
      // A saved strategy stores the resulting rates, not the income/state they
      // were derived from, so the helper's inputs stay as the user left them.
      // Read from `prev` rather than the closure: loadConfig is called back to
      // back with runConfig, and the closure's `config` would be a render stale.
      taxStatus: prev.taxStatus,
      taxIncome: prev.taxIncome,
      taxState: prev.taxState,
    }));
  }
  async function runExample() {
    const exampleCfg = {
      mode: "picker",
      picker_id: "momentum",
      picker_params: { lookback: 126 },
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
    };
    loadConfig(exampleCfg);
    await runConfig(exampleCfg);
  }
  /**
   * Preset: tax-managed ETF momentum at California rates. 12-1 momentum over
   * a menu of 22 large index ETFs, top 5, quarterly, traded under the
   * tax-managed rule (a yearly realized-gain budget). The ETF menu avoids the
   * survivorship bias of the per-stock data: every one of these funds still
   * trades. strategies/tax_managed.py documents the rule;
   * research/STRATEGY_SEARCH.md covers how it held up in testing.
   */
  async function runTaxManagedPreset() {
    const cfg = {
      mode: "picker",
      picker_id: "momentum",
      picker_params: { lookback: 252, skip: 21 },
      tickers: null,
      timer_id: "buy_hold",
      timer_params: {},
      top_n: 5,
      rebalance: "Q",
      universe: "all",
      menu: TAX_MANAGED_MENU,
      trade_rule: "tax_managed",
      gain_budget: 0.01,
      wash_days: 31,
      start: "2000-01-01",
      end: "2026-07-01",
      warmup_days: 450,
      commission_pct: 0.0005,
      slippage_pct: 0.0005,
      tax: {
        enabled: true,
        // California, single filer, ~$300k taxable income:
        // short 35% federal + 3.8% NIIT + 9.3% CA; long 15% + 3.8% + 9.3%.
        short_term_rate: 0.481,
        long_term_rate: 0.281,
        long_term_days: 365,
      },
    };
    loadConfig(cfg);
    setConfig((prev) => ({
      ...prev,
      taxStatus: "single",
      taxIncome: 300000,
      taxState: "CA",
    }));
    await runConfig(cfg);
  }

  /**
   * Preset: the 2x S&P trend switch (same rule as
   * research/lab/families/verify_lev_robust.py): hold SSO, a 2x S&P 500 ETF,
   * while SPY is more than 3% above its 175-day average, and IEF
   * (intermediate Treasuries) once it is more than 3% below — evaluated every
   * trading day at the close. Manual mode, so the basket is exactly the two
   * funds the rule switches between. Starts in 2007 because SSO only began
   * trading in mid-2006; the 400-day warm-up gives the 175-day average a full
   * window on day one.
   */
  async function runLeveragedTrendPreset() {
    const cfg = {
      mode: "manual",
      picker_id: null,
      picker_params: {},
      tickers: ["SSO", "IEF"],
      timer_id: "trend_switch",
      timer_params: { signal: "SPY", n: 175, band: 0.03, risk: "SSO", safe: "IEF" },
      top_n: 15,
      rebalance: "M",
      // Unused in manual mode; kept at the honest default for a later switch
      // to strategy mode.
      universe: "sp500-pit",
      menu: null,
      trade_rule: "standard",
      gain_budget: 0.01,
      wash_days: 31,
      start: "2007-01-01",
      end: "2026-07-01",
      warmup_days: 400,
      commission_pct: 0.0005,
      slippage_pct: 0.0005,
      tax: {
        enabled: true,
        // California, single filer, ~$300k taxable income (as the other preset).
        short_term_rate: 0.481,
        long_term_rate: 0.281,
        long_term_days: 365,
      },
    };
    loadConfig(cfg);
    setConfig((prev) => ({
      ...prev,
      taxStatus: "single",
      taxIncome: 300000,
      taxState: "CA",
    }));
    await runConfig(cfg);
  }

  async function refreshSaved() {
    setSaved(await listStrategies().catch(() => []));
  }
  async function doSave(name) {
    setSaving(true);
    setSaveError(null);
    try {
      await saveStrategy(name, buildConfig());
      await refreshSaved();
      setShowSave(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }
  async function onDeleteSaved(s) {
    await deleteStrategy(s.id).catch(() => {});
    await refreshSaved();
  }
  function closeTour() {
    setShowTour(false);
    localStorage.setItem(TOUR_KEY, "1");
  }
  const suggestedName =
    mode === "manual"
      ? `${manualTickers.slice(0, 3).join("/")}${manualTickers.length > 3 ? "…" : ""} · ${prettyId(timerId)}`
      : `${prettyId(pickerId)} · ${prettyId(timerId)}`;
  if (loadError) {
    // There is no server to be down: the engine runs in a Web Worker here, so
    // a failure at this point means the worker couldn't start or the price
    // bundle couldn't be fetched. Point at that instead of a dead API.
    return (
      <div className="container">
        <div className="error-banner">
          Couldn’t start the backtest engine — the price data bundle may be
          missing. Build it with <code>tools/build_web_data.py</code> and make
          sure it’s served at <code>/data</code>. ({loadError})
        </div>
      </div>
    );
  }
  if (!ready) return <div className="center-load">Loading strategies…</div>;
  return (
    <div className="app">
      <ParticleField />
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand" id="tour-brand">
            <span className="dot" /> StockTest
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              justifyContent: "flex-end",
            }}
          >
            <button className="btn ghost" onClick={() => setShowTour(true)}>
              Take a tour
            </button>
            <button
              className="btn ghost"
              onClick={runTaxManagedPreset}
              disabled={running}
              title="12-1 momentum over 22 index ETFs, top 5, quarterly, traded under a yearly realized-gain budget — at California tax rates"
            >
              Tax-managed ETF momentum (CA)
            </button>
            <button
              className="btn ghost"
              onClick={runLeveragedTrendPreset}
              disabled={running}
              title="Hold SSO (2x S&P 500) while SPY is more than 3% above its 175-day average, IEF (Treasuries) once it is more than 3% below — checked every trading day at the close, at California tax rates. Leverage magnifies losses."
            >
              2× S&amp;P trend switch (CA)
            </button>
            <button
              className="btn"
              id="tour-example"
              onClick={runExample}
              disabled={running}
            >
              Try an example
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="hero">
          <h1>Would this strategy have beaten the market?</h1>
          <p>
            Pick your stocks (or let a strategy pick), choose a timing rule, and
            see the honest, after-tax result.
          </p>
        </div>

        <MyStrategies
          strategies={saved}
          onRun={(s) => {
            loadConfig(s.config);
            runConfig(s.config);
          }}
          onEdit={(s) => {
            loadConfig(s.config);
            document
              .getElementById("tour-mode")
              ?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
          onDelete={onDeleteSaved}
          busy={running}
        />

        {/* Step 1 — mode */}
        <section className="section">
          <div className="section-head">
            <div className="step-kicker">
              <span className="step-num">1</span> How should stocks be chosen?
            </div>
            <p className="sub">
              This is your first choice. You can switch anytime.
            </p>
          </div>
          <ModeCards mode={mode} onPick={pickMode} />
        </section>

        {/* Step 2 — stocks */}
        {mode && (
          <section className="section">
            <div className="section-head">
              <div className="step-kicker">
                <span className="step-num">2</span>
                {mode === "manual"
                  ? " Choose your stocks"
                  : " Choose a strategy — what to own"}
              </div>
              <p className="sub">
                {mode === "manual"
                  ? "Search and add the companies you want to test. You'll choose when to hold them in the next step."
                  : "This decides WHICH stocks get bought. The next step decides WHEN to hold them. Green badges are safe for long-history tests; amber ones are only reliable over recent windows."}
              </p>
            </div>
            {mode === "ai" && <ConceptExplainer />}
            {mode === "manual" ? (
              <TickerPicker
                selected={manualTickers}
                onChange={setManualTickers}
                universeNote={universeNote}
              />
            ) : (
              <>
                <PickerGrid
                  pickers={pickers}
                  selected={pickerId}
                  onSelect={selectPicker}
                />
                {currentPicker && (
                  <details className="collapsible customize">
                    <summary>
                      <span className="caret">▸</span> Customize{" "}
                      {currentPicker.name} parameters
                    </summary>
                    <div className="body">
                      <ParamEditor
                        title={currentPicker.name}
                        specs={currentPicker.params}
                        values={pickerParams}
                        onChange={setPickerParams}
                      />
                    </div>
                  </details>
                )}
              </>
            )}
          </section>
        )}

        {/* Step 3 — timer */}
        {mode && stocksReady && (
          <section className="section" id="tour-timer">
            <div className="section-head">
              <div className="step-kicker">
                <span className="step-num">3</span> Choose a timing rule — when
                to hold it
              </div>
              <p className="sub">
                You’ve chosen <em>what</em> to own. A <strong>timer</strong> now
                decides, day by day, whether to actually be holding each of
                those stocks or sitting in cash. Pick “Buy &amp; Hold” to just
                hold them the whole time — that’s the baseline every other timer
                has to beat.
              </p>
            </div>
            {mode === "manual" && <ConceptExplainer />}
            <TimerGrid
              timers={timers}
              selected={timerId}
              onSelect={selectTimer}
            />
            {currentTimer && (
              <details className="collapsible customize">
                <summary>
                  <span className="caret">▸</span> Customize {currentTimer.name}{" "}
                  parameters
                </summary>
                <div className="body">
                  <ParamEditor
                    title={currentTimer.name}
                    specs={currentTimer.params}
                    values={timerParams}
                    onChange={setTimerParams}
                  />
                </div>
              </details>
            )}
          </section>
        )}

        {/* Step 4 — settings */}
        {mode && stocksReady && timerId && (
          <section className="section">
            <div className="section-head">
              <div className="step-kicker">
                <span className="step-num">4</span> When &amp; taxes
              </div>
              <p className="sub">
                Set the time window. Advanced options stay tucked away.
              </p>
            </div>
            <SettingsPanel
              mode={mode}
              config={config}
              update={update}
              universeOptions={universeOptions}
              dataRange={dataRange}
            />
          </section>
        )}

        {runError && (
          <div className="error-banner">Backtest failed: {runError}</div>
        )}
      </main>

      <div className="runbar">
        <div className="runbar-inner">
          <div className="summary">{summaryText}</div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              className="btn"
              disabled={!(mode && stocksReady && timerId) || running}
              onClick={() => setShowSave(true)}
            >
              ★ Save strategy
            </button>
            <button className="btn primary lg" disabled={!canRun} onClick={run}>
              {running ? (
                <>
                  <span className="spinner" /> Running…
                </>
              ) : (
                "Run backtest →"
              )}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <Results
          data={result}
          config={resultConfig}
          mode={result.mode === "manual" ? "manual" : "ai"}
          pickers={pickers}
          universeOptions={universeOptions}
          tickerNames={tickerNames}
          onClose={() => setResult(null)}
        />
      )}
      {showSave && (
        <SaveDialog
          defaultName={suggestedName}
          error={saveError}
          saving={saving}
          onCancel={() => {
            setShowSave(false);
            setSaveError(null);
          }}
          onSave={doSave}
        />
      )}
      {showTour && (
        <Onboarding
          steps={TOUR_STEPS}
          onClose={closeTour}
          onFinishExample={runExample}
        />
      )}
    </div>
  );
}

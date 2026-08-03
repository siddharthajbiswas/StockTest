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
import type {
  BacktestRequest,
  BacktestResponse,
  Mode,
  Picker,
  SavedStrategy,
  StrategyConfig,
  TaxSettings,
  Timer,
  UniverseNote,
  UniverseOption,
} from "./types";
import { ModeCards } from "./components/ModeCards";
import { PickerGrid } from "./components/PickerGrid";
import { TimerGrid } from "./components/TimerGrid";
import { TickerPicker } from "./components/TickerPicker";
import { SettingsPanel, type Config } from "./components/SettingsPanel";
import { Results } from "./components/Results";
import { Onboarding, type TourStep } from "./components/Onboarding";
import { ParamEditor, type Params, defaultParams } from "./components/ParamEditor";
import { MyStrategies } from "./components/MyStrategies";
import { SaveDialog } from "./components/SaveDialog";
import { ParticleField } from "./components/ParticleField";
import { prettyId } from "./format";

const TOUR_KEY = "stocktest_tour_done_v1";

const DEFAULT_CONFIG: Config = {
  start: "2014-01-01",
  end: "2024-01-01",
  universe: "sp500-pit",
  taxDefaults: true,
  stRatePct: 35,
  ltRatePct: 15,
  topN: 15,
  rebalance: "M",
  commissionBps: 5,
  slippageBps: 5,
};

const TOUR_STEPS: TourStep[] = [
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
    title: "What’s a “timer”?",
    body: "After you have stocks, a timer decides WHEN to hold each one — e.g. only while it’s trending up, or buying the dip. Buy & Hold just holds them the whole time.",
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
  const [pickers, setPickers] = useState<Picker[]>([]);
  const [timers, setTimers] = useState<Timer[]>([]);
  const [universeOptions, setUniverseOptions] = useState<UniverseOption[]>([]);
  const [dataRange, setDataRange] = useState<{ start: string; end: string } | null>(null);
  const [universeNote, setUniverseNote] = useState<UniverseNote | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const [mode, setMode] = useState<Mode | null>(null);
  const [manualTickers, setManualTickers] = useState<string[]>([]);
  const [pickerId, setPickerId] = useState<string | null>(null);
  const [pickerParams, setPickerParams] = useState<Params>({});
  const [timerId, setTimerId] = useState<string | null>(null);
  const [timerParams, setTimerParams] = useState<Params>({});
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  // The exact config that produced `result`, so the results sheet can validate
  // the same combo out-of-sample (not whatever the wizard currently shows).
  const [resultConfig, setResultConfig] = useState<StrategyConfig | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const [saved, setSaved] = useState<SavedStrategy[]>([]);
  const [showSave, setShowSave] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

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
        setSaved(st);
        if (h?.data_start && h?.data_end) {
          setDataRange({ start: h.data_start, end: h.data_end });
        }
        setReady(true);
        if (!localStorage.getItem(TOUR_KEY)) setShowTour(true);
      })
      .catch((e) => setLoadError(String(e.message ?? e)));
  }, []);

  const update = (patch: Partial<Config>) => setConfig((c) => ({ ...c, ...patch }));

  const currentPicker = pickers.find((p) => p.id === pickerId);
  const currentTimer = timers.find((t) => t.id === timerId);

  const stocksReady = mode === "manual" ? manualTickers.length > 0 : !!pickerId;
  const canRun = !!mode && stocksReady && !!timerId && !running;

  // Picking a strategy pre-fills its default params.
  function selectPicker(id: string) {
    setPickerId(id);
    const p = pickers.find((x) => x.id === id);
    setPickerParams(p ? defaultParams(p.params) : {});
  }
  function selectTimer(id: string) {
    setTimerId(id);
    const t = timers.find((x) => x.id === id);
    setTimerParams(t ? defaultParams(t.params) : {});
  }

  function pickMode(m: Mode) {
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

  function taxSettings(): TaxSettings {
    return config.taxDefaults
      ? { enabled: true, short_term_rate: 0.35, long_term_rate: 0.15, long_term_days: 365 }
      : {
          enabled: true,
          short_term_rate: config.stRatePct / 100,
          long_term_rate: config.ltRatePct / 100,
          long_term_days: 365,
        };
  }

  function buildConfig(): StrategyConfig {
    return {
      mode: mode === "manual" ? "manual" : "picker",
      picker_id: mode === "ai" ? pickerId : null,
      picker_params: mode === "ai" ? pickerParams : {},
      tickers: mode === "manual" ? manualTickers : null,
      timer_id: timerId!,
      timer_params: timerParams,
      top_n: config.topN,
      rebalance: config.rebalance,
      universe: config.universe,
      start: config.start,
      end: config.end,
      commission_pct: config.commissionBps / 10000,
      slippage_pct: config.slippageBps / 10000,
      tax: taxSettings(),
    };
  }

  function toRequest(cfg: StrategyConfig): BacktestRequest {
    const base: BacktestRequest = {
      timer_id: cfg.timer_id,
      timer_params: cfg.timer_params,
      start: cfg.start,
      end: cfg.end,
      cash: 100_000,
      commission_pct: cfg.commission_pct,
      slippage_pct: cfg.slippage_pct,
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
    };
  }

  async function runConfig(cfg: StrategyConfig) {
    setRunning(true);
    setRunError(null);
    try {
      setResult(await runBacktest(toRequest(cfg)));
      setResultConfig(cfg);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const run = () => runConfig(buildConfig());

  // Load a saved/example config back into the wizard.
  function loadConfig(cfg: StrategyConfig) {
    const isManual = cfg.mode === "manual";
    setMode(isManual ? "manual" : "ai");
    setManualTickers(isManual ? cfg.tickers ?? [] : []);
    setPickerId(isManual ? null : cfg.picker_id);
    setPickerParams(isManual ? {} : cfg.picker_params ?? {});
    setTimerId(cfg.timer_id);
    setTimerParams(cfg.timer_params ?? {});
    const usesDefaultTax =
      cfg.tax.enabled && cfg.tax.short_term_rate === 0.35 && cfg.tax.long_term_rate === 0.15;
    setConfig({
      start: cfg.start ?? DEFAULT_CONFIG.start,
      end: cfg.end ?? DEFAULT_CONFIG.end,
      universe: cfg.universe,
      taxDefaults: usesDefaultTax,
      stRatePct: Math.round(cfg.tax.short_term_rate * 100),
      ltRatePct: Math.round(cfg.tax.long_term_rate * 100),
      topN: cfg.top_n,
      rebalance: cfg.rebalance,
      commissionBps: Math.round(cfg.commission_pct * 10000),
      slippageBps: Math.round(cfg.slippage_pct * 10000),
    });
  }

  async function runExample() {
    const exampleCfg: StrategyConfig = {
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
      tax: { enabled: true, short_term_rate: 0.35, long_term_rate: 0.15, long_term_days: 365 },
    };
    loadConfig(exampleCfg);
    await runConfig(exampleCfg);
  }

  async function refreshSaved() {
    setSaved(await listStrategies().catch(() => []));
  }

  async function doSave(name: string) {
    setSaving(true);
    setSaveError(null);
    try {
      await saveStrategy(name, buildConfig());
      await refreshSaved();
      setShowSave(false);
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteSaved(s: SavedStrategy) {
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
          Couldn’t start the backtest engine — the price data bundle may be missing.
          Build it with <code>tools/build_web_data.py</code> and make sure it’s served
          at <code>/data</code>. ({loadError})
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
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn ghost" onClick={() => setShowTour(true)}>
              Take a tour
            </button>
            <button className="btn" id="tour-example" onClick={runExample} disabled={running}>
              Try an example
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="hero">
          <h1>Would this strategy have beaten the market?</h1>
          <p>Pick your stocks (or let a strategy pick), choose a timing rule, and see the honest, after-tax result.</p>
        </div>

        <MyStrategies
          strategies={saved}
          onRun={(s) => {
            loadConfig(s.config);
            runConfig(s.config);
          }}
          onEdit={(s) => {
            loadConfig(s.config);
            document.getElementById("tour-mode")?.scrollIntoView({ behavior: "smooth", block: "center" });
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
            <p className="sub">This is your first choice. You can switch anytime.</p>
          </div>
          <ModeCards mode={mode} onPick={pickMode} />
        </section>

        {/* Step 2 — stocks */}
        {mode && (
          <section className="section">
            <div className="section-head">
              <div className="step-kicker">
                <span className="step-num">2</span>
                {mode === "manual" ? " Choose your stocks" : " Choose a strategy"}
              </div>
              <p className="sub">
                {mode === "manual"
                  ? "Search and add the companies you want to test."
                  : "Each card explains itself. Green badges are safe for long-history tests; amber ones are only reliable over recent windows."}
              </p>
            </div>
            {mode === "manual" ? (
              <TickerPicker selected={manualTickers} onChange={setManualTickers} universeNote={universeNote} />
            ) : (
              <>
                <PickerGrid pickers={pickers} selected={pickerId} onSelect={selectPicker} />
                {currentPicker && (
                  <details className="collapsible customize">
                    <summary>
                      <span className="caret">▸</span> Customize {currentPicker.name} parameters
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
                <span className="step-num">3</span> Choose a timing rule
              </div>
              <p className="sub">
                A <strong>timer</strong> decides when to be in or out of each stock you’ve chosen.
                Pick “Buy &amp; Hold” to simply hold them.
              </p>
            </div>
            <TimerGrid timers={timers} selected={timerId} onSelect={selectTimer} />
            {currentTimer && (
              <details className="collapsible customize">
                <summary>
                  <span className="caret">▸</span> Customize {currentTimer.name} parameters
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
              <p className="sub">Set the time window. Advanced options stay tucked away.</p>
            </div>
            <SettingsPanel mode={mode} config={config} update={update} universeOptions={universeOptions} dataRange={dataRange} />
          </section>
        )}

        {runError && <div className="error-banner">Backtest failed: {runError}</div>}
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
      {showTour && <Onboarding steps={TOUR_STEPS} onClose={closeTour} onFinishExample={runExample} />}
    </div>
  );
}

import { useState } from "react";
import type {
  BacktestResponse,
  Mode,
  Picker,
  StrategyConfig,
  UniverseOption,
  ValidationResult,
} from "../types";
import { assessTrust } from "../content";
import { validateStrategy } from "../api";
import { money, pct, prettyId } from "../format";
import { LineChart, type Series } from "./LineChart";
import { DrawdownChart } from "./DrawdownChart";
import { MetricsPanel } from "./MetricsPanel";
import { TrustPanel } from "./TrustPanel";
import { ValidationPanel } from "./ValidationPanel";
import { TradeLog } from "./TradeLog";

interface Props {
  data: BacktestResponse;
  config: StrategyConfig | null;
  mode: Mode;
  pickers: Picker[];
  universeOptions: UniverseOption[];
  onClose: () => void;
}

export function Results({ data, config, mode, pickers, universeOptions, onClose }: Props) {
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [validateError, setValidateError] = useState<string | null>(null);

  async function runValidation() {
    if (!config) return;
    setValidating(true);
    setValidateError(null);
    try {
      setValidation(await validateStrategy({ config }));
    } catch (e: unknown) {
      setValidateError(e instanceof Error ? e.message : String(e));
    } finally {
      setValidating(false);
    }
  }

  const m = data.metrics;
  const b = data.benchmark;
  const taxed = m.after_tax_cagr != null; // taxes were modeled

  const stratAfter = taxed ? m.after_tax_cagr! : m.pretax_cagr ?? m.cagr;
  const beats = taxed ? b?.beats_spy_after_tax : b?.beats_spy;
  const excess = taxed ? b?.excess_after_tax_cagr : b?.excess_cagr;

  const subject =
    data.mode === "manual"
      ? `Your basket (${data.tickers_used?.join(", ") ?? ""})`
      : `${prettyId(data.picker_id)} + ${prettyId(data.timer_id)}`;

  // Equity chart series: strategy pre-tax, strategy after-tax, S&P 500 (after-tax).
  const eq = data.equity_curve;
  const series: Series[] = [
    { label: "Strategy (pre-tax)", color: "#98a2b3", values: eq.pretax, dashed: true },
    { label: taxed ? "Strategy (after-tax)" : "Strategy", color: "#8b7bff", values: eq.aftertax },
  ];
  if (b?.curve)
    series.push({
      label: taxed ? "S&P 500 (after-tax)" : "S&P 500",
      color: "#4ade9f",
      values: taxed ? b.curve.aftertax : b.curve.pretax,
    });

  // Trust items — chosen from picker/universe metadata, not hardcoded per result.
  const pickerUsed = pickers.find((p) => p.id === data.picker_id);
  const universeUsed = universeOptions.find((u) => u.id === data.universe);
  const trust = assessTrust({ mode, picker: pickerUsed, universeOption: universeUsed, period: data.period });

  return (
    <div className="results-overlay" onClick={onClose}>
      <div className="results-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="results-head">
          <div>
            <div className="step-kicker">Backtest result</div>
            <h2 style={{ fontSize: 22 }}>{subject}</h2>
            <p className="sub" style={{ color: "var(--muted)", marginTop: 6 }}>
              {data.period.start} → {data.period.end} · universe: {data.universe}
            </p>
            {b && (
              <div className={"verdict " + (beats ? "win" : "lose")}>
                {beats ? "✓ Beat" : "✕ Lagged"} the S&P 500
                {excess != null && ` by ${Math.abs(excess * 100).toFixed(1)}%/yr`}
                {taxed ? " (after tax)" : ""}
              </div>
            )}
          </div>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="results-body">
          {/* headline number */}
          <div className="headline">
            <div>
              <div className="k">{taxed ? "After-tax annual return" : "Annual return"}</div>
              <div className={"big " + (stratAfter >= 0 ? "pos" : "neg")}>{pct(stratAfter)}</div>
            </div>
            <div>
              <div className="k">Final value (from {money(m.starting_cash)})</div>
              <div className="big">{money(taxed ? m.after_tax_final_value : m.final_value)}</div>
            </div>
          </div>

          {/* equity chart */}
          <div className="chart-wrap">
            <h4 className="chart-title">Growth of {money(m.starting_cash)}</h4>
            <LineChart dates={eq.dates} series={series} />
          </div>

          {/* drawdown chart */}
          <div className="chart-wrap">
            <h4 className="chart-title">
              Drawdown <span className="chart-note">— how far below the prior peak, over time</span>
            </h4>
            <DrawdownChart dates={eq.dates} values={eq.aftertax} />
          </div>

          {/* metrics */}
          <h3 className="block-title">Metrics</h3>
          <MetricsPanel m={m} benchmark={b} taxed={taxed} />

          {/* trust */}
          <TrustPanel items={trust} />

          {/* out-of-sample validation */}
          <h3 className="block-title">Does this edge hold up out-of-sample?</h3>
          <p className="sub" style={{ marginTop: -4, marginBottom: 12 }}>
            A backtest can look great just because the strategy happened to fit this one stretch of
            history. This re-tests the same combo on data it wasn't chosen using — a much harder,
            more honest test. It reruns many windows, so it takes longer than a backtest.
          </p>

          {!validation && (
            <button
              className="btn primary"
              onClick={runValidation}
              disabled={validating || !config}
            >
              {validating ? "Validating… (this can take a bit)" : "Validate this strategy"}
            </button>
          )}
          {validating && (
            <div className="oos-loading" role="status">
              <span className="spinner" aria-hidden="true" />
              Rerunning the strategy across multiple out-of-sample windows…
            </div>
          )}
          {validateError && <div className="oos-error">Validation failed — {validateError}</div>}
          {validation && <ValidationPanel data={validation} />}

          {/* trade log */}
          <h3 className="block-title">Trade log</h3>
          <p className="sub" style={{ marginTop: -4, marginBottom: 12 }}>
            Completed round trips (a buy matched to the sell that closed it), most recent first.
          </p>
          <TradeLog trips={data.round_trips} />
        </div>
      </div>
    </div>
  );
}

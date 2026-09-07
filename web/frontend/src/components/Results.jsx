import { useEffect, useRef, useState } from "react";
import { assessTrust } from "../content";
import { validateStrategy } from "../api";
import { money, pct, prettyId } from "../format";
import { LineChart } from "./LineChart";
import { DrawdownChart } from "./DrawdownChart";
import { MetricsPanel } from "./MetricsPanel";
import { TrustPanel } from "./TrustPanel";
import { ValidationPanel } from "./ValidationPanel";
import { TradeLog } from "./TradeLog";

/** Rough time-remaining text from the sweep's own elapsed/completed counters. */
function etaText(p) {
  if (p.completed === 0) return "";
  const remaining =
    ((p.elapsedMs / p.completed) * (p.total - p.completed)) / 1000;
  if (remaining < 1) return "";
  return remaining < 60
    ? ` · about ${Math.ceil(remaining)}s left`
    : ` · about ${Math.ceil(remaining / 60)} min left`;
}

export function Results({
  data,
  config,
  mode,
  pickers,
  universeOptions,
  tickerNames,
  onClose,
}) {
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [validateError, setValidateError] = useState(null);
  const [progress, setProgress] = useState(null);
  const abortRef = useRef(null);
  async function runValidation() {
    if (!config) return;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setValidating(true);
    setValidateError(null);
    setProgress(null);
    try {
      setValidation(
        await validateStrategy(
          { config },
          { signal: ctrl.signal, onProgress: setProgress },
        ),
      );
    } catch (e) {
      // Cancelling is a deliberate user action, not a failure to report.
      if (e instanceof DOMException && e.name === "AbortError") return;
      setValidateError(e instanceof Error ? e.message : String(e));
    } finally {
      abortRef.current = null;
      setValidating(false);
      setProgress(null);
    }
  }
  function cancelValidation() {
    abortRef.current?.abort();
  }
  // Abandon an in-flight validation if the panel closes, so a cancelled run
  // doesn't keep a worker busy chewing through 100 backtests.
  useEffect(() => () => abortRef.current?.abort(), []);
  const m = data.metrics;
  const b = data.benchmark;
  const taxed = m.after_tax_cagr != null; // taxes were modeled
  const stratAfter = taxed ? m.after_tax_cagr : (m.pretax_cagr ?? m.cagr);
  const beats = taxed ? b?.beats_spy_after_tax : b?.beats_spy;
  const excess = taxed ? b?.excess_after_tax_cagr : b?.excess_cagr;
  const subject =
    data.mode === "manual"
      ? `Your basket (${data.tickers_used?.join(", ") ?? ""})`
      : `${prettyId(data.picker_id)} + ${prettyId(data.timer_id)}`;
  // Equity chart series: strategy pre-tax, strategy after-tax, S&P 500 (after-tax).
  const eq = data.equity_curve;
  const series = [
    {
      label: "Strategy (pre-tax)",
      color: "#98a2b3",
      values: eq.pretax,
      dashed: true,
    },
    {
      label: taxed ? "Strategy (after-tax)" : "Strategy",
      color: "#8b7bff",
      values: eq.aftertax,
    },
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
  const trust = assessTrust({
    mode,
    picker: pickerUsed,
    universeOption: universeUsed,
    period: data.period,
  });
  return (
    <div className="results-overlay" onClick={onClose}>
      <div className="results-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="results-head">
          <div>
            <div className="step-kicker">Backtest result</div>
            <h2 style={{ fontSize: 22 }}>{subject}</h2>
            <p className="sub" style={{ color: "var(--muted)", marginTop: 6 }}>
              {data.period.start} → {data.period.end} · universe:{" "}
              {data.universe}
            </p>
            {b && (
              <div className={"verdict " + (beats ? "win" : "lose")}>
                {beats ? "✓ Beat" : "✕ Lagged"} the S&P 500
                {excess != null &&
                  ` by ${Math.abs(excess * 100).toFixed(1)}%/yr`}
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
              <div className="k">
                {taxed ? "After-tax annual return" : "Annual return"}
              </div>
              <div className={"big " + (stratAfter >= 0 ? "pos" : "neg")}>
                {pct(stratAfter)}
              </div>
            </div>
            <div>
              <div className="k">
                Final value (from {money(m.starting_cash)})
              </div>
              <div className="big">
                {money(taxed ? m.after_tax_final_value : m.final_value)}
              </div>
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
              Drawdown{" "}
              <span className="chart-note">
                — how far below the prior peak, over time
              </span>
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
            A backtest can look great just because the strategy happened to fit
            this one stretch of history. This re-tests the same combo on data it
            wasn't chosen using — a much harder, more honest test. It reruns
            many windows, so it takes longer than a backtest.
          </p>

          {!validation && (
            <button
              className="btn primary"
              onClick={runValidation}
              disabled={validating || !config}
            >
              {validating
                ? "Validating… (this can take a bit)"
                : "Validate this strategy"}
            </button>
          )}
          {validating && (
            <div className="oos-progress" role="status" aria-live="polite">
              <div className="oos-loading">
                <span className="spinner" aria-hidden="true" />
                {progress && progress.phase === "curves" ? (
                  <>
                    Testing every strategy combination on this period —{" "}
                    <strong>
                      {progress.completed} of {progress.total}
                    </strong>
                    {etaText(progress)}
                  </>
                ) : (
                  "Rerunning the strategy across multiple out-of-sample windows…"
                )}
                <button className="btn-link" onClick={cancelValidation}>
                  Cancel
                </button>
              </div>
              {progress && progress.total > 0 && (
                <div
                  className="oos-bar"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={progress.total}
                  aria-valuenow={progress.completed}
                >
                  <div
                    className="oos-bar-fill"
                    style={{
                      width: `${(progress.completed / progress.total) * 100}%`,
                    }}
                  />
                </div>
              )}
              {progress?.label && progress.phase === "curves" && (
                <div className="oos-current">
                  {progress.label.replace(" × ", " + ")}
                </div>
              )}
            </div>
          )}
          {validateError && (
            <div className="oos-error">Validation failed — {validateError}</div>
          )}
          {validation && <ValidationPanel data={validation} />}

          {/* trade log */}
          <h3 className="block-title">Trade log</h3>
          <p className="sub" style={{ marginTop: -4, marginBottom: 12 }}>
            Completed round trips (a buy matched to the sell that closed it),
            most recent first. Hover a ticker for the company name, or click it
            to see that stock’s price history with these trades marked on it.
          </p>
          <TradeLog trips={data.round_trips} names={tickerNames} />
        </div>
      </div>
    </div>
  );
}

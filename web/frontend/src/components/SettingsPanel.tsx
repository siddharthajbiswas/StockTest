import { useState } from "react";
import type { Mode, UniverseOption } from "../types";
import { InfoTip } from "./InfoTip";
import { TaxRateHelper } from "./TaxRateHelper";
import { computeRates, type FilingStatus } from "../taxTables";

export interface Config {
  start: string;
  end: string;
  universe: "all" | "sp500-pit";
  taxDefaults: boolean;
  stRatePct: number;
  ltRatePct: number;
  topN: number;
  rebalance: "D" | "W" | "M" | "Q";
  commissionBps: number;
  slippageBps: number;
  /** Inputs to the rate helper. Kept here so they survive the panel unmounting. */
  taxStatus: FilingStatus;
  taxIncome: number;
  taxState: string;
}

interface Props {
  mode: Mode;
  config: Config;
  update: (patch: Partial<Config>) => void;
  universeOptions: UniverseOption[];
  /** Earliest/latest dates for which price data actually exists. */
  dataRange: { start: string; end: string } | null;
}

// Keep a picked date inside the available data window so the backtest can't be
// run over a range with no data.
const clamp = (v: string, lo: string, hi: string) =>
  v < lo ? lo : v > hi ? hi : v;

export function SettingsPanel({ mode, config, update, universeOptions, dataRange }: Props) {
  const activeUniverse = universeOptions.find((u) => u.id === config.universe);
  const dataMin = dataRange?.start;
  const dataMax = dataRange?.end;
  const [helperOpen, setHelperOpen] = useState(false);

  // Whether the rates in force are the ones the helper currently computes, so
  // the button can read "Applied" instead of inviting a pointless second click.
  const helperRates = computeRates(config.taxStatus, config.taxIncome, config.taxState);
  const near = (a: number, b: number) => Math.abs(a - b) < 0.005;
  const helperApplied =
    !config.taxDefaults &&
    near(config.stRatePct, helperRates.shortTotal * 100) &&
    near(config.ltRatePct, helperRates.longTotal * 100);
  return (
    <div className="panel">
      {/* Date range */}
      <div className="row">
        <div className="field">
          <label htmlFor="start">Start date</label>
          <input
            id="start"
            type="date"
            className="input"
            value={config.start}
            min={dataMin}
            max={config.end < (dataMax ?? config.end) ? config.end : dataMax}
            onChange={(e) =>
              update({ start: clamp(e.target.value, dataMin ?? e.target.value, config.end) })
            }
          />
        </div>
        <div className="field">
          <label htmlFor="end">End date</label>
          <input
            id="end"
            type="date"
            className="input"
            value={config.end}
            min={config.start > (dataMin ?? config.start) ? config.start : dataMin}
            max={dataMax}
            onChange={(e) =>
              update({ end: clamp(e.target.value, config.start, dataMax ?? e.target.value) })
            }
          />
        </div>
      </div>
      {dataRange && (
        <p className="hint" style={{ marginTop: -4, marginBottom: 8 }}>
          Data available {dataRange.start} to {dataRange.end}.
        </p>
      )}

      {/* Taxes */}
      <div className="field" style={{ marginTop: 8 }}>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          Taxes
          <InfoTip text="Selling winners triggers capital-gains tax. Frequent trading is taxed at higher short-term rates, while buy-and-hold defers tax — so two strategies with the same gross return can differ a lot after tax. We compare everything net of tax. The rates below are all-in: federal, the 3.8% net investment income surtax, and your state's income tax on gains." />
        </label>
        <p className="hint" style={{ marginBottom: 10 }}>
          Why it matters: a strategy only beats the market if it wins <em>after</em> taxes and fees.
        </p>
        <div className="seg" role="tablist" aria-label="Tax mode">
          <button
            className={config.taxDefaults ? "on" : ""}
            onClick={() => update({ taxDefaults: true })}
          >
            Use sensible defaults
          </button>
          <button
            className={!config.taxDefaults ? "on" : ""}
            onClick={() => update({ taxDefaults: false })}
          >
            Set my own rates
          </button>
        </div>

        {!config.taxDefaults && (
          <div className="row" style={{ marginTop: 14 }}>
            <div className="field">
              <label htmlFor="st">Short-term rate (%)</label>
              <input
                id="st"
                type="number"
                className="input"
                min={0}
                max={90}
                value={config.stRatePct}
                onChange={(e) => update({ stRatePct: Number(e.target.value) })}
              />
              <p className="hint">Held ≤ 1 year (taxed as income).</p>
            </div>
            <div className="field">
              <label htmlFor="lt">Long-term rate (%)</label>
              <input
                id="lt"
                type="number"
                className="input"
                min={0}
                max={90}
                value={config.ltRatePct}
                onChange={(e) => update({ ltRatePct: Number(e.target.value) })}
              />
              <p className="hint">Held &gt; 1 year (lower rate).</p>
            </div>
          </div>
        )}
        {config.taxDefaults && (
          <p className="hint" style={{ marginTop: 8 }}>
            Defaults: 35% short-term, 15% long-term — a rough stand-in for a high earner in a
            state with income tax. Your real rates depend on your income and state; the helper
            below works them out.
          </p>
        )}

        {/* Rate helper — answers "what are MY rates, including state tax?" */}
        <details className="collapsible" style={{ marginTop: 12 }} open={helperOpen}>
          <summary onClick={() => setHelperOpen((v) => !v)}>
            <span className="caret">▸</span> Work out my rates from my income and state
          </summary>
          <div className="body">
            <TaxRateHelper
              status={config.taxStatus}
              income={config.taxIncome}
              state={config.taxState}
              onChange={update}
              onApply={(shortPct, longPct) =>
                update({
                  taxDefaults: false,
                  stRatePct: Math.round(shortPct * 100) / 100,
                  ltRatePct: Math.round(longPct * 100) / 100,
                })
              }
              applied={helperApplied}
            />
          </div>
        </details>
      </div>

      {/* Advanced — collapsed by default (progressive disclosure) */}
      <details className="collapsible" style={{ marginTop: 8 }}>
        <summary>
          <span className="caret">▸</span> Advanced options
        </summary>
        <div className="body">
          {mode === "ai" && (
            <>
              <div className="field">
                <label>
                  Stock universe{" "}
                  <InfoTip text="Which stocks the strategy may buy on each day." />
                </label>
                <select
                  className="input"
                  value={config.universe}
                  onChange={(e) => update({ universe: e.target.value as Config["universe"] })}
                >
                  {universeOptions.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
                {activeUniverse && (
                  <div className="caveat" style={{ marginTop: 10 }}>
                    {activeUniverse.bias_caveat}
                  </div>
                )}
              </div>

              <div className="row">
                <div className="field">
                  <label htmlFor="topn">Stocks held</label>
                  <input
                    id="topn"
                    type="number"
                    className="input"
                    min={1}
                    max={100}
                    value={config.topN}
                    onChange={(e) => update({ topN: Number(e.target.value) })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="reb">Rebalance</label>
                  <select
                    id="reb"
                    className="input"
                    value={config.rebalance}
                    onChange={(e) => update({ rebalance: e.target.value as Config["rebalance"] })}
                  >
                    <option value="D">Daily</option>
                    <option value="W">Weekly</option>
                    <option value="M">Monthly</option>
                    <option value="Q">Quarterly</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <div className="row">
            <div className="field">
              <label htmlFor="comm">Commission (bps)</label>
              <input
                id="comm"
                type="number"
                className="input"
                min={0}
                value={config.commissionBps}
                onChange={(e) => update({ commissionBps: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label htmlFor="slip">Slippage (bps)</label>
              <input
                id="slip"
                type="number"
                className="input"
                min={0}
                value={config.slippageBps}
                onChange={(e) => update({ slippageBps: Number(e.target.value) })}
              />
            </div>
          </div>
          <p className="hint">1 bp = 0.01%. These model real trading costs on every trade.</p>
        </div>
      </details>
    </div>
  );
}

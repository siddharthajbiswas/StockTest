import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { fetchTickerHistory } from "../api";
import type { RoundTrip, TickerHistory } from "../types";
import { money, prettyDate, signedPct } from "../format";
import { tooltipStyle, useChartHover } from "./useChartHover";

interface Props {
  symbol: string;
  /** Company name, if the caller already knows it — avoids a flash of the bare symbol. */
  name?: string | null;
  /** Every round trip in this backtest for this symbol, newest first. */
  trips: RoundTrip[];
  onClose: () => void;
}

/**
 * A stock's own price history, opened by clicking a ticker in the trade log.
 *
 * Shows the full available history rather than just the backtest window, with
 * the strategy's entries and exits marked on it — the question someone clicks a
 * ticker to answer is usually "was that a good moment to buy?", which needs the
 * surrounding context to answer.
 */
export function StockHistory({ symbol, name, trips, onClose }: Props) {
  const [data, setData] = useState<TickerHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setData(null);
    setError(null);
    fetchTickerHistory(symbol)
      .then((d) => live && setData(d))
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, [symbol]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const title = data?.name ?? name ?? null;

  // Portalled for the same reason as StrategyDetail: this one is opened from
  // inside the results sheet, which sets `overflow: hidden`. It escapes that
  // today only because nothing between here and the root is transformed — a
  // fragile thing to rely on for a modal.
  return createPortal(
    <div className="results-overlay" onClick={onClose}>
      <div
        className="detail-sheet stock-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={`Price history for ${symbol}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="results-head">
          <div>
            <div className="step-kicker">Price history</div>
            <h2 style={{ fontSize: 22 }}>
              <span className="mono">{symbol}</span>
              {title && <span className="stock-name"> · {title}</span>}
            </h2>
            {data && data.first_date && (
              <p className="sub" style={{ color: "var(--muted)", marginTop: 6 }}>
                {data.first_date} → {data.last_date} · {data.n_bars.toLocaleString()} trading days
              </p>
            )}
          </div>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="detail-body">
          {error && <div className="error-banner">Couldn’t load {symbol} — {error}</div>}
          {!data && !error && <p className="hint">Loading price history…</p>}
          {data && data.dates.length < 2 && !error && (
            <p className="hint">No price history available for {symbol}.</p>
          )}
          {data && data.dates.length >= 2 && (
            <>
              <PriceChart data={data} trips={trips} />
              <p className="hint" style={{ marginTop: 10 }}>
                Closing prices, not adjusted for splits or dividends beyond what the source data
                already applies. Markers show where this backtest bought and sold.
              </p>

              {trips.length > 0 && (
                <>
                  <h4 className="detail-h">This strategy’s trades in {symbol}</h4>
                  <table className="mini-table">
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left" }}>Bought</th>
                        <th style={{ textAlign: "left" }}>Sold</th>
                        <th>Held</th>
                        <th>Return</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trips.map((t, i) => (
                        <tr key={i}>
                          <td style={{ textAlign: "left" }}>
                            {t.entry_date} <span className="mono">{money(t.entry_price, 2)}</span>
                          </td>
                          <td style={{ textAlign: "left" }}>
                            {t.exit_date} <span className="mono">{money(t.exit_price, 2)}</span>
                          </td>
                          <td>{t.holding_days}d</td>
                          <td className={t.pnl > 0 ? "pnl-pos" : "pnl-neg"}>
                            {signedPct(t.return_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** Close-price line with buy/sell markers from the backtest. */
function PriceChart({ data, trips }: { data: TickerHistory; trips: RoundTrip[] }) {
  const W = 620;
  const H = 240;
  const P = { t: 12, r: 14, b: 24, l: 56 };
  const n = data.dates.length;
  const hover = useChartHover({ width: W, padLeft: P.l, padRight: P.r, n });

  const vals = data.closes;
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = (hi - lo) * 0.08 || 1;
  const yLo = Math.max(0, lo - pad);
  const yHi = hi + pad;

  const innerW = W - P.l - P.r;
  const innerH = H - P.t - P.b;
  const sx = (i: number) => P.l + (i / (n - 1)) * innerW;
  const sy = (v: number) => P.t + (1 - (v - yLo) / (yHi - yLo)) * innerH;

  let d = "";
  for (let i = 0; i < n; i++) d += `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(vals[i]).toFixed(1)} `;

  // Map a trade date onto the nearest sample. The series is downsampled, so an
  // exact date match usually does not exist.
  const indexOfDate = (iso: string) => {
    let lo2 = 0;
    let hi2 = n - 1;
    while (lo2 < hi2) {
      const mid = (lo2 + hi2) >> 1;
      if (data.dates[mid] < iso) lo2 = mid + 1;
      else hi2 = mid;
    }
    return lo2;
  };

  const marks = trips.flatMap((t) => [
    { i: indexOfDate(t.entry_date), kind: "buy" as const, date: t.entry_date, price: t.entry_price },
    { i: indexOfDate(t.exit_date), kind: "sell" as const, date: t.exit_date, price: t.exit_price },
  ]);

  const ticks = [yLo + (yHi - yLo) * 0.12, (yLo + yHi) / 2, yLo + (yHi - yLo) * 0.88];
  const i = hover.index;

  return (
    <div className="chart-hoverable">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={`${data.symbol} closing price`}
        style={{ touchAction: "pan-y" }}
        {...hover.handlers}
      >
        {ticks.map((t, k) => (
          <g key={k}>
            <line x1={P.l} x2={W - P.r} y1={sy(t)} y2={sy(t)} stroke="rgba(255,255,255,0.08)" />
            <text x={P.l - 8} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="#98a2b3">
              ${t >= 1000 ? `${(t / 1000).toFixed(1)}k` : t.toFixed(0)}
            </text>
          </g>
        ))}
        <path d={d} fill="none" stroke="#8b7bff" strokeWidth="1.6" strokeLinejoin="round" />

        {marks.map((m, k) => (
          <circle
            key={k}
            cx={sx(m.i)}
            cy={sy(vals[m.i])}
            r="4"
            fill={m.kind === "buy" ? "#4ade9f" : "#f04438"}
            stroke="#0c0f1e"
            strokeWidth="1.2"
          >
            <title>
              {m.kind === "buy" ? "Bought" : "Sold"} {m.date} at{" "}
              {m.price.toFixed(2)}
            </title>
          </circle>
        ))}

        {i !== null && (
          <g pointerEvents="none">
            <line x1={sx(i)} x2={sx(i)} y1={P.t} y2={H - P.b} stroke="rgba(255,255,255,0.35)" />
            <circle cx={sx(i)} cy={sy(vals[i])} r="4" fill="#8b7bff" stroke="#0c0f1e" strokeWidth="1.5" />
          </g>
        )}

        <text x={P.l} y={H - 6} fontSize="11" fill="#98a2b3">{data.dates[0]}</text>
        <text x={W - P.r} y={H - 6} fontSize="11" fill="#98a2b3" textAnchor="end">
          {data.dates[n - 1]}
        </text>
      </svg>

      <div className="chart-legend" style={{ marginTop: 8 }}>
        <span><i className="legend-swatch" style={{ background: "#4ade9f", borderRadius: 6, height: 8, width: 8 }} /> Bought</span>
        <span><i className="legend-swatch" style={{ background: "#f04438", borderRadius: 6, height: 8, width: 8 }} /> Sold</span>
      </div>

      {i !== null && (
        <div className="chart-tip" style={tooltipStyle(sx(i) / W)}>
          <div className="chart-tip-date">{prettyDate(data.dates[i])}</div>
          <div className="chart-tip-row">
            <i className="chart-tip-dot" style={{ background: "#8b7bff" }} />
            <span className="chart-tip-label">Close</span>
            <span className="chart-tip-value">{money(vals[i], 2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

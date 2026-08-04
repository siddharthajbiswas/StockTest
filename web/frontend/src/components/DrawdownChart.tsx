import { prettyDate } from "../format";
import { tooltipStyle, useChartHover } from "./useChartHover";

/** Underwater (drawdown) chart: how far below the prior peak the portfolio was,
 *  as a %, at each point. Computed from the after-tax equity line. */
export function DrawdownChart({ dates, values }: { dates: string[]; values: number[] }) {
  const W = 780;
  const H = 150;
  const P = { t: 10, r: 14, b: 22, l: 58 };
  const n = values.length;

  // Unconditional so hook order is stable across the early return below.
  const hover = useChartHover({ width: W, padLeft: P.l, padRight: P.r, n });
  if (n < 2) return null;

  // Drawdown series (<= 0), and the running peak behind it — the tooltip
  // explains the number by naming the peak it is measured from.
  const dd: number[] = [];
  const peaks: number[] = [];
  let peak = -Infinity;
  for (const v of values) {
    peak = Math.max(peak, v);
    peaks.push(peak);
    dd.push(peak > 0 ? v / peak - 1 : 0);
  }
  const worst = Math.min(...dd, 0);
  const worstAt = dd.indexOf(worst);

  const innerW = W - P.l - P.r;
  const innerH = H - P.t - P.b;
  const sx = (i: number) => P.l + (i / (n - 1)) * innerW;
  const sy = (v: number) => P.t + (v / (worst || -1)) * innerH; // 0 at top, worst at bottom

  const step = Math.max(1, Math.floor(n / 260));
  let line = "";
  for (let i = 0; i < n; i += step) line += `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(dd[i]).toFixed(1)} `;
  line += `L${sx(n - 1).toFixed(1)},${sy(dd[n - 1]).toFixed(1)}`;
  const area = `${line} L${sx(n - 1).toFixed(1)},${sy(0).toFixed(1)} L${sx(0).toFixed(1)},${sy(0).toFixed(1)} Z`;

  const ticks = [0, worst * 0.5, worst];
  const i = hover.index;

  return (
    <div className="chart-hoverable">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Drawdown"
        style={{ touchAction: "pan-y" }}
        {...hover.handlers}
      >
        <defs>
          <linearGradient id="ddfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f04438" stopOpacity="0.05" />
            <stop offset="100%" stopColor="#f04438" stopOpacity="0.22" />
          </linearGradient>
        </defs>
        {ticks.map((t, k) => (
          <g key={k}>
            <line x1={P.l} x2={W - P.r} y1={sy(t)} y2={sy(t)} stroke="rgba(255,255,255,0.08)" />
            <text x={P.l - 8} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="#98a2b3">
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}
        <path d={area} fill="url(#ddfill)" />
        <path d={line} fill="none" stroke="#f04438" strokeWidth="1.6" />

        {/* Mark the worst point, so the headline max-drawdown number is findable. */}
        {worstAt >= 0 && worst < 0 && (
          <circle cx={sx(worstAt)} cy={sy(worst)} r="3" fill="#f04438" opacity="0.9" />
        )}

        {i !== null && (
          <g pointerEvents="none">
            <line
              x1={sx(i)}
              x2={sx(i)}
              y1={P.t}
              y2={H - P.b}
              stroke="rgba(255,255,255,0.35)"
              strokeWidth="1"
            />
            <circle cx={sx(i)} cy={sy(dd[i])} r="4" fill="#f04438" stroke="#0c0f1e" strokeWidth="1.5" />
          </g>
        )}

        <text x={P.l} y={H - 5} fontSize="11" fill="#98a2b3">
          {dates[0]}
        </text>
        <text x={W - P.r} y={H - 5} fontSize="11" fill="#98a2b3" textAnchor="end">
          {dates[n - 1]}
        </text>
      </svg>

      {i !== null && (
        <div className="chart-tip" style={tooltipStyle(sx(i) / W)}>
          <div className="chart-tip-date">{prettyDate(dates[i])}</div>
          <div className="chart-tip-row">
            <i className="chart-tip-dot" style={{ background: "#f04438" }} />
            <span className="chart-tip-label">Below peak</span>
            <span className="chart-tip-value">{(dd[i] * 100).toFixed(1)}%</span>
          </div>
          <div className="chart-tip-note">
            {dd[i] < -0.0001
              ? `Peak was ${peaks[i].toLocaleString(undefined, {
                  style: "currency",
                  currency: "USD",
                  maximumFractionDigits: 0,
                })}`
              : "At a new high"}
          </div>
        </div>
      )}
    </div>
  );
}

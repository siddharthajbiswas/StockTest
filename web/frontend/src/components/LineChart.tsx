import { money, prettyDate } from "../format";
import { tooltipStyle, useChartHover } from "./useChartHover";

export interface Series {
  label: string;
  color: string;
  values: number[];
  dashed?: boolean;
}

/** Multi-line chart on a shared date axis, dollar y-axis. Inline SVG, no library. */
export function LineChart({ dates, series }: { dates: string[]; series: Series[] }) {
  const W = 780;
  const H = 250;
  const P = { t: 12, r: 14, b: 24, l: 58 };
  const n = dates.length;

  // Hooks must run before the early return below, so this is unconditional.
  const hover = useChartHover({ width: W, padLeft: P.l, padRight: P.r, n });
  if (n < 2) return null;

  const all = series.flatMap((s) => s.values).filter((v) => Number.isFinite(v));
  const rawMin = Math.min(...all);
  const rawMax = Math.max(...all);
  const pad = (rawMax - rawMin) * 0.08 || 1;
  const lo = rawMin - pad;
  const hi = rawMax + pad;

  const innerW = W - P.l - P.r;
  const innerH = H - P.t - P.b;
  const sx = (i: number) => P.l + (i / (n - 1)) * innerW;
  const sy = (v: number) => P.t + (1 - (v - lo) / (hi - lo)) * innerH;

  // Downsample each series to ~260 points.
  const step = Math.max(1, Math.floor(n / 260));
  const path = (vals: number[]) => {
    let d = "";
    let started = false;
    for (let i = 0; i < n; i += step) {
      if (!Number.isFinite(vals[i])) continue;
      d += `${started ? "L" : "M"}${sx(i).toFixed(1)},${sy(vals[i]).toFixed(1)} `;
      started = true;
    }
    const last = n - 1;
    if (Number.isFinite(vals[last])) d += `L${sx(last).toFixed(1)},${sy(vals[last]).toFixed(1)}`;
    return d;
  };

  const fmt = (v: number) =>
    v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : `$${Math.round(v / 1000)}k`;
  const ticks = [lo + (hi - lo) * 0.12, (lo + hi) / 2, lo + (hi - lo) * 0.88];

  // The tooltip reads the FULL series, not the ~260-point downsample used for
  // the path — so the number shown is the real value on the hovered day.
  const i = hover.index;
  const readout =
    i === null
      ? null
      : {
          date: dates[i],
          rows: series
            .map((s) => ({ label: s.label, color: s.color, value: s.values[i] }))
            .filter((r) => Number.isFinite(r.value)),
        };

  return (
    <div className="chart-hoverable">
      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.label}>
            <i
              className="legend-swatch"
              style={{
                background: s.dashed
                  ? `repeating-linear-gradient(90deg, ${s.color} 0 4px, transparent 4px 7px)`
                  : s.color,
              }}
            />
            {s.label}
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Equity curves"
        style={{ touchAction: "pan-y" }}
        {...hover.handlers}
      >
        {ticks.map((t, k) => (
          <g key={k}>
            <line x1={P.l} x2={W - P.r} y1={sy(t)} y2={sy(t)} stroke="rgba(255,255,255,0.08)" />
            <text x={P.l - 8} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="#98a2b3">
              {fmt(t)}
            </text>
          </g>
        ))}
        {series.map((s) => (
          <path
            key={s.label}
            d={path(s.values)}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeDasharray={s.dashed ? "5 4" : undefined}
          />
        ))}

        {/* crosshair + one marker per series */}
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
            {series.map((s) =>
              Number.isFinite(s.values[i]) ? (
                <circle
                  key={s.label}
                  cx={sx(i)}
                  cy={sy(s.values[i])}
                  r="4"
                  fill={s.color}
                  stroke="#0c0f1e"
                  strokeWidth="1.5"
                />
              ) : null,
            )}
          </g>
        )}

        <text x={P.l} y={H - 6} fontSize="11" fill="#98a2b3">
          {dates[0]}
        </text>
        <text x={W - P.r} y={H - 6} fontSize="11" fill="#98a2b3" textAnchor="end">
          {dates[n - 1]}
        </text>
      </svg>

      {/* `below-legend`: the legend shares this positioning box, so the
          default top would put the bubble on top of it. */}
      {readout && (
        <div className="chart-tip below-legend" style={tooltipStyle(sx(i!) / W)}>
          <div className="chart-tip-date">{prettyDate(readout.date)}</div>
          {readout.rows.map((r) => (
            <div key={r.label} className="chart-tip-row">
              <i className="chart-tip-dot" style={{ background: r.color }} />
              <span className="chart-tip-label">{r.label}</span>
              <span className="chart-tip-value">{money(r.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

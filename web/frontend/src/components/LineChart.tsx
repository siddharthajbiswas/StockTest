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

  return (
    <div>
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
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Equity curves">
        {ticks.map((t, i) => (
          <g key={i}>
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
        <text x={P.l} y={H - 6} fontSize="11" fill="#98a2b3">
          {dates[0]}
        </text>
        <text x={W - P.r} y={H - 6} fontSize="11" fill="#98a2b3" textAnchor="end">
          {dates[n - 1]}
        </text>
      </svg>
    </div>
  );
}

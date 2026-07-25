import type { BenchmarkComparison, Metrics } from "../types";
import { METRIC_INFO } from "../content";
import { InfoTip } from "./InfoTip";
import { money, num, pct } from "../format";

function Tile({
  infoKey,
  value,
  tone,
  sub,
}: {
  infoKey: keyof typeof METRIC_INFO;
  value: string;
  tone?: "pos" | "neg";
  sub?: string;
}) {
  const info = METRIC_INFO[infoKey];
  return (
    <div className="stat">
      <div className="k" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {info.label} <InfoTip text={info.help} label={`About ${info.label}`} />
      </div>
      <div className={"v" + (tone ? " " + tone : "")}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export function MetricsPanel({
  m,
  benchmark,
  taxed,
}: {
  m: Metrics;
  benchmark: BenchmarkComparison | null;
  taxed: boolean;
}) {
  const afterCagr = taxed ? m.after_tax_cagr : m.pretax_cagr;
  const spyCagr = benchmark
    ? taxed
      ? benchmark.metrics.after_tax_cagr
      : benchmark.metrics.pretax_cagr
    : null;

  return (
    <div className="stat-grid metrics">
      <Tile
        infoKey="pretax_cagr"
        value={pct(m.pretax_cagr)}
        tone={(m.pretax_cagr ?? 0) >= 0 ? "pos" : "neg"}
      />
      <Tile
        infoKey="aftertax_cagr"
        value={pct(afterCagr)}
        tone={(afterCagr ?? 0) >= 0 ? "pos" : "neg"}
        sub={spyCagr != null ? `S&P 500: ${pct(spyCagr)}` : undefined}
      />
      <Tile
        infoKey="total_return"
        value={pct(taxed ? m.after_tax_total_return : m.total_return)}
      />
      <Tile infoKey="sharpe" value={num(m.sharpe)} />
      <Tile infoKey="max_drawdown" value={pct(m.max_drawdown)} tone="neg" />
      <Tile
        infoKey="tax_drag"
        value={taxed ? money(m.tax_drag_value) : "$0"}
        tone={taxed && (m.tax_drag_value ?? 0) > 0 ? "neg" : undefined}
        sub={taxed ? `${pct(m.tax_drag_cagr)} / yr of return` : "taxes not modeled"}
      />
      <Tile
        infoKey="win_rate"
        value={m.win_rate == null ? "—" : pct(m.win_rate, 0)}
        sub={`${m.n_round_trips} round trips`}
      />
      <Tile infoKey="n_trades" value={m.n_trades.toLocaleString()} sub={`${money(m.commission_paid)} commission`} />
    </div>
  );
}

// Response shapes produced by the in-browser engine worker. These originated
// as the FastAPI models (now reference/models.py, catalog.py) and are kept
// field-for-field identical to them, which is what the golden parity suite
// checks — so the Python reference implementation stays the source of truth.

export interface ParamSpec {
  name: string;
  type: string;
  default: unknown;
  description: string;
}

export interface Picker {
  id: string;
  name: string;
  data_source: "price" | "fundamentals";
  look_ahead_risk: boolean;
  description: string;
  params: ParamSpec[];
}

export interface Timer {
  id: string;
  name: string;
  description: string;
  params: ParamSpec[];
}

export interface UniverseOption {
  id: "all" | "sp500-pit";
  name: string;
  description: string;
  bias_caveat: string;
}

export interface UniverseNote {
  count: number;
  fixed: boolean;
  has_company_names: boolean;
  note: string;
}

export interface TickerRecord {
  symbol: string;
  name: string | null;
  has_fundamentals: boolean;
  market_cap: number | null;
  date_from: string | null;
  date_to: string | null;
}

export interface Metrics {
  starting_cash: number;
  final_value: number;
  total_return: number;
  cagr: number;
  sharpe: number;
  max_drawdown: number;
  n_trades: number;
  commission_paid: number;
  taxes_paid: number | null;
  terminal_tax: number | null;
  total_tax: number | null;
  after_tax_final_value: number | null;
  after_tax_total_return: number | null;
  after_tax_cagr: number | null;
  pretax_cagr: number | null;
  pretax_total_return: number | null;
  final_value_pretax: number | null;
  tax_drag_value: number | null;
  tax_drag_cagr: number | null;
  win_rate: number | null;
  n_round_trips: number;
}

export interface EquityCurve {
  dates: string[];
  pretax: number[];
  aftertax: number[];
}

export interface BenchmarkCurve {
  pretax: number[];
  aftertax: number[];
}

export interface TradeRecord {
  date: string;
  ticker: string;
  side: string;
  shares: number;
  price: number;
  value: number;
  commission: number;
}

export interface RoundTrip {
  ticker: string;
  entry_date: string;
  exit_date: string;
  shares: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
  holding_days: number;
}

export interface BenchmarkComparison {
  benchmark: string;
  metrics: Metrics;
  excess_cagr: number;
  beats_spy: boolean;
  excess_after_tax_cagr: number | null;
  beats_spy_after_tax: boolean | null;
  curve: BenchmarkCurve | null;
}

export interface BacktestResponse {
  mode: "picker" | "manual";
  picker_id: string | null;
  timer_id: string;
  universe: string;
  period: { start: string; end: string };
  tickers_used: string[] | null;
  metrics: Metrics;
  equity_curve: EquityCurve;
  trades: TradeRecord[];
  round_trips: RoundTrip[];
  benchmark: BenchmarkComparison | null;
}

export interface TaxSettings {
  enabled: boolean;
  short_term_rate: number;
  long_term_rate: number;
  long_term_days: number;
}

export interface BacktestRequest {
  picker_id?: string | null;
  picker_params?: Record<string, unknown>;
  tickers?: string[] | null;
  timer_id: string;
  timer_params?: Record<string, unknown>;
  top_n?: number;
  rebalance?: "D" | "W" | "M" | "Q";
  cash?: number;
  start?: string | null;
  end?: string | null;
  universe?: "all" | "sp500-pit";
  commission_pct?: number;
  slippage_pct?: number;
  tax?: TaxSettings;
}

export type Mode = "manual" | "ai";

export interface StrategyConfig {
  mode: "picker" | "manual";
  picker_id: string | null;
  picker_params: Record<string, unknown>;
  tickers: string[] | null;
  timer_id: string;
  timer_params: Record<string, unknown>;
  top_n: number;
  rebalance: "D" | "W" | "M" | "Q";
  universe: "all" | "sp500-pit";
  start: string | null;
  end: string | null;
  commission_pct: number;
  slippage_pct: number;
  tax: TaxSettings;
}

export interface SavedStrategy {
  id: string;
  name: string;
  created_at: string;
  config: StrategyConfig;
}

// ----- out-of-sample validation (ported: web/engine/src/validation.ts) -----

export type VerdictLevel = "held" | "mixed" | "failed";

export interface ValidationHoldout {
  split: string;
  spearman: number | null;
  n_ranked: number;
  spy_train_cagr: number | null;
  spy_test_cagr: number | null;
  your_train_cagr: number | null;
  your_test_cagr: number | null;
  your_train_rank: number;
  your_test_rank: number;
  beats_spy_test: boolean;
  rank_held: boolean;
}

export interface ValidationWindow {
  start: string;
  end: string;
  picked: string;
  combo_return: number | null;
  spy_return: number | null;
}

export interface ValidationWalkforward {
  has_windows: boolean;
  adaptive_oos_cagr: number | null;
  spy_oos_cagr: number | null;
  adaptive_beats_spy: boolean;
  your_oos_cagr: number | null;
  your_oos_beats_spy: boolean;
  windows: ValidationWindow[];
  most_picked: { combo: string; count: number }[];
}

export interface ValidationVerdict {
  level: VerdictLevel;
  score: number;
  beats_spy_out_of_sample: boolean;
  rank_held: boolean;
  walkforward_beats_spy: boolean;
}

export interface ValidationResult {
  meta: {
    n_baseline_combos: number;
    price_only: boolean;
    period: { start: string; end: string };
    span_years: number;
    train_years: number;
    step_years: number;
  };
  holdout: ValidationHoldout;
  walkforward: ValidationWalkforward;
  verdict: ValidationVerdict;
}

export interface ValidateRequest {
  config?: StrategyConfig;
  strategy_id?: string;
  split?: string | null;
  train_years?: number;
  step_years?: number;
  price_only?: boolean;
}

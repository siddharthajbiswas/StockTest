// Response shapes produced by the in-browser engine worker. These originated
// as the FastAPI models (now reference/models.py, catalog.py) and are kept
// field-for-field identical to them, which is what the golden parity suite
// checks — so the Python reference implementation stays the source of truth.
//
// Nothing here executes. The shapes are written down as typedefs because the
// parity suite pins them to Python, so a field renamed on this side without a
// matching change there is a bug no test on this side would catch.

/**
 * @typedef {object} ParamSpec
 * @property {string} name
 * @property {string} type
 * @property {unknown} default
 * @property {string} description
 *
 * @typedef {object} Picker
 * @property {string} id
 * @property {string} name
 * @property {"price" | "fundamentals"} data_source
 * @property {boolean} look_ahead_risk
 * @property {string} description
 * @property {ParamSpec[]} params
 *
 * @typedef {object} Timer
 * @property {string} id
 * @property {string} name
 * @property {string} description
 * @property {ParamSpec[]} params
 *
 * @typedef {object} UniverseOption
 * @property {"all" | "sp500-pit"} id
 * @property {string} name
 * @property {string} description
 * @property {string} bias_caveat
 *
 * @typedef {object} UniverseNote
 * @property {number} count
 * @property {boolean} fixed
 * @property {boolean} has_company_names
 * @property {string} note
 *
 * @typedef {object} TickerRecord
 * @property {string} symbol
 * @property {string | null} name
 * @property {boolean} has_fundamentals
 * @property {number | null} market_cap
 * @property {string | null} date_from
 * @property {string | null} date_to
 */

/**
 * One stock's price history — served by the worker's `tickerHistory` op.
 *
 * @typedef {object} TickerHistory
 * @property {string} symbol
 * @property {string | null} name
 * @property {string[]} dates
 * @property {number[]} closes
 * @property {string | null} first_date  Range of the underlying data, before
 *   downsampling.
 * @property {string | null} last_date
 * @property {number} n_bars  Real bar count, which exceeds dates.length when
 *   downsampled.
 */

/**
 * @typedef {object} Metrics
 * @property {number} starting_cash
 * @property {number} final_value
 * @property {number} total_return
 * @property {number} cagr
 * @property {number} sharpe
 * @property {number} max_drawdown
 * @property {number} n_trades
 * @property {number} commission_paid
 * @property {number | null} taxes_paid
 * @property {number | null} terminal_tax
 * @property {number | null} total_tax
 * @property {number | null} after_tax_final_value
 * @property {number | null} after_tax_total_return
 * @property {number | null} after_tax_cagr
 * @property {number | null} pretax_cagr
 * @property {number | null} pretax_total_return
 * @property {number | null} final_value_pretax
 * @property {number | null} tax_drag_value
 * @property {number | null} tax_drag_cagr
 * @property {number | null} win_rate
 * @property {number} n_round_trips
 *
 * @typedef {object} EquityCurve
 * @property {string[]} dates
 * @property {number[]} pretax
 * @property {number[]} aftertax
 *
 * @typedef {object} BenchmarkCurve
 * @property {number[]} pretax
 * @property {number[]} aftertax
 *
 * @typedef {object} TradeRecord
 * @property {string} date
 * @property {string} ticker
 * @property {string} side
 * @property {number} shares
 * @property {number} price
 * @property {number} value
 * @property {number} commission
 *
 * @typedef {object} RoundTrip
 * @property {string} ticker
 * @property {string} entry_date
 * @property {string} exit_date
 * @property {number} shares
 * @property {number} entry_price
 * @property {number} exit_price
 * @property {number} pnl
 * @property {number} return_pct
 * @property {number} holding_days
 *
 * @typedef {object} BenchmarkComparison
 * @property {string} benchmark
 * @property {Metrics} metrics
 * @property {number} excess_cagr
 * @property {boolean} beats_spy
 * @property {number | null} excess_after_tax_cagr
 * @property {boolean | null} beats_spy_after_tax
 * @property {BenchmarkCurve | null} curve
 *
 * @typedef {object} BacktestResponse
 * @property {"picker" | "manual"} mode
 * @property {string | null} picker_id
 * @property {string} timer_id
 * @property {string} universe
 * @property {{ start: string, end: string }} period
 * @property {string[] | null} tickers_used
 * @property {Metrics} metrics
 * @property {EquityCurve} equity_curve
 * @property {TradeRecord[]} trades
 * @property {RoundTrip[]} round_trips
 * @property {BenchmarkComparison | null} benchmark
 *
 * @typedef {object} TaxSettings
 * @property {boolean} enabled
 * @property {number} short_term_rate
 * @property {number} long_term_rate
 * @property {number} long_term_days
 *
 * @typedef {object} BacktestRequest
 * @property {string | null} [picker_id]
 * @property {Record<string, unknown>} [picker_params]
 * @property {string[] | null} [tickers]
 * @property {string} timer_id
 * @property {Record<string, unknown>} [timer_params]
 * @property {number} [top_n]
 * @property {"D" | "W" | "M" | "Q"} [rebalance]
 * @property {number} [cash]
 * @property {string | null} [start]
 * @property {string | null} [end]
 * @property {"all" | "sp500-pit"} [universe]
 * @property {number} [commission_pct]
 * @property {number} [slippage_pct]
 * @property {TaxSettings} [tax]
 *
 * @typedef {"manual" | "ai"} Mode
 *
 * @typedef {object} StrategyConfig
 * @property {"picker" | "manual"} mode
 * @property {string | null} picker_id
 * @property {Record<string, unknown>} picker_params
 * @property {string[] | null} tickers
 * @property {string} timer_id
 * @property {Record<string, unknown>} timer_params
 * @property {number} top_n
 * @property {"D" | "W" | "M" | "Q"} rebalance
 * @property {"all" | "sp500-pit"} universe
 * @property {string | null} start
 * @property {string | null} end
 * @property {number} commission_pct
 * @property {number} slippage_pct
 * @property {TaxSettings} tax
 *
 * @typedef {object} SavedStrategy
 * @property {string} id
 * @property {string} name
 * @property {string} created_at
 * @property {StrategyConfig} config
 */

// ----- out-of-sample validation (ported: web/engine/src/validation.js) -----

/**
 * @typedef {"held" | "mixed" | "failed"} VerdictLevel
 *
 * @typedef {object} ValidationHoldout
 * @property {string} split
 * @property {number | null} spearman
 * @property {number} n_ranked
 * @property {number | null} spy_train_cagr
 * @property {number | null} spy_test_cagr
 * @property {number | null} your_train_cagr
 * @property {number | null} your_test_cagr
 * @property {number} your_train_rank
 * @property {number} your_test_rank
 * @property {boolean} beats_spy_test
 * @property {boolean} rank_held
 *
 * @typedef {object} ValidationWindow
 * @property {string} start
 * @property {string} end
 * @property {string} picked
 * @property {number | null} combo_return
 * @property {number | null} spy_return
 *
 * @typedef {object} ValidationWalkforward
 * @property {boolean} has_windows
 * @property {number | null} adaptive_oos_cagr
 * @property {number | null} spy_oos_cagr
 * @property {boolean} adaptive_beats_spy
 * @property {number | null} your_oos_cagr
 * @property {boolean} your_oos_beats_spy
 * @property {ValidationWindow[]} windows
 * @property {{ combo: string, count: number }[]} most_picked
 *
 * @typedef {object} ValidationVerdict
 * @property {VerdictLevel} level
 * @property {number} score
 * @property {boolean} beats_spy_out_of_sample
 * @property {boolean} rank_held
 * @property {boolean} walkforward_beats_spy
 *
 * @typedef {object} ValidationMeta
 * @property {number} n_baseline_combos
 * @property {boolean} price_only
 * @property {{ start: string, end: string }} period
 * @property {number} span_years
 * @property {number} train_years
 * @property {number} step_years
 *
 * @typedef {object} ValidationResult
 * @property {ValidationMeta} meta
 * @property {ValidationHoldout} holdout
 * @property {ValidationWalkforward} walkforward
 * @property {ValidationVerdict} verdict
 *
 * @typedef {object} ValidateRequest
 * @property {StrategyConfig} [config]
 * @property {string} [strategy_id]
 * @property {string | null} [split]
 * @property {number} [train_years]
 * @property {number} [step_years]
 * @property {boolean} [price_only]
 */

export {};

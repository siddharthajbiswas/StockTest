"""Pydantic request/response schemas for the backtest API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TaxSettings(BaseModel):
    """Capital-gains tax knobs (maps to backtester.TaxPolicy). Set enabled=False
    to score gross-of-tax (taxes not modeled)."""

    enabled: bool = True
    short_term_rate: float = 0.35
    long_term_rate: float = 0.15
    long_term_days: int = 365


class StrategyConfig(BaseModel):
    """A reusable strategy definition — everything needed to repopulate the
    wizard and re-run a backtest, minus the cash amount."""

    mode: Literal["picker", "manual"]
    picker_id: str | None = None
    picker_params: dict[str, Any] = Field(default_factory=dict)
    tickers: list[str] | None = None
    timer_id: str
    timer_params: dict[str, Any] = Field(default_factory=dict)
    top_n: int = Field(15, ge=1, le=200)
    rebalance: Literal["D", "W", "M", "Q", "S", "A"] = "M"
    menu: list[str] | None = None
    trade_rule: Literal["standard", "tax_managed"] = "standard"
    gain_budget: float = Field(0.01, ge=0, le=1)
    wash_days: int = Field(31, ge=0, le=90)
    universe: Literal["all", "sp500-pit"] = "all"
    start: str | None = None
    end: str | None = None
    warmup_days: int = Field(0, ge=0, le=2000)
    commission_pct: float = Field(0.0005, ge=0)
    slippage_pct: float = Field(0.0005, ge=0)
    tax: TaxSettings = Field(default_factory=TaxSettings)


class SaveStrategyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    config: StrategyConfig


class SavedStrategy(BaseModel):
    id: str
    name: str
    created_at: str
    config: StrategyConfig


class ValidateRequest(BaseModel):
    """Validate a combo out-of-sample: pass an inline config OR a saved id."""

    config: StrategyConfig | None = None
    strategy_id: str | None = None
    split: str | None = None  # holdout boundary; None -> midpoint of the window
    train_years: int = Field(3, ge=1, le=15)
    step_years: int = Field(1, ge=1, le=5)
    price_only: bool = True  # baseline sweep uses only the trustworthy price pickers

    @model_validator(mode="after")
    def _one_source(self) -> "ValidateRequest":
        if (self.config is None) == (self.strategy_id is None):
            raise ValueError("Provide exactly one of `config` or `strategy_id`.")
        return self


class BacktestRequest(BaseModel):
    # --- selection: EXACTLY ONE of picker_id (AI mode) or tickers (manual) ---
    picker_id: str | None = Field(
        None, description="AI-picker mode: one of GET /pickers ids."
    )
    picker_params: dict[str, Any] = Field(default_factory=dict)
    tickers: list[str] | None = Field(
        None, description="Manual mode: an explicit basket; skips picker logic."
    )

    # --- timer (always required) ---
    timer_id: str
    timer_params: dict[str, Any] = Field(default_factory=dict)

    # --- portfolio / cadence ---
    top_n: int = Field(15, ge=1, le=200, description="Names held (AI mode).")
    rebalance: Literal["D", "W", "M", "Q", "S", "A"] = "M"
    cash: float = Field(100_000.0, gt=0)
    menu: list[str] | None = Field(
        None,
        description="AI-picker mode: restrict the picker to this shortlist "
                    "instead of the whole universe (e.g. an ETF menu).",
    )

    # --- how the portfolio is allowed to trade toward the target ---
    trade_rule: Literal["standard", "tax_managed"] = Field(
        "standard",
        description=(
            "'standard' rewrites weights whenever the basket changes. "
            "'tax_managed' rations sales by a realized-gain budget: losses are "
            "always harvestable, gains only up to `gain_budget` of portfolio "
            "value per year. For a taxable account this is usually worth more "
            "than the choice of signal."
        ),
    )
    gain_budget: float = Field(
        0.01, ge=0, le=1,
        description="tax_managed only: cap on the year's NET realized gain, as "
                    "a fraction of portfolio value. 0 = never take a net gain.",
    )
    wash_days: int = Field(
        31, ge=0, le=90,
        description="tax_managed only: days a name sold at a loss is barred "
                    "from repurchase, so the loss is not a wash sale.",
    )


    # --- date range (inclusive, YYYY-MM-DD); None = full available history ---
    start: str | None = None
    end: str | None = None
    warmup_days: int = Field(
        0, ge=0, le=2000,
        description=(
            "Calendar days of extra price history loaded BEFORE `start` purely "
            "to warm up indicators. Nothing trades during it and it is clipped "
            "out of the reported curve and metrics, so a long-lookback strategy "
            "is not handicapped by spending the first months of the window in "
            "cash with nothing to rank. 0 (the default) keeps the old behaviour."
        ),
    )

    # --- universe & costs ---
    universe: Literal["all", "sp500-pit"] = "all"
    commission_pct: float = Field(0.0005, ge=0)
    slippage_pct: float = Field(0.0005, ge=0)
    tax: TaxSettings = Field(default_factory=TaxSettings)

    @model_validator(mode="after")
    def _exactly_one_mode(self) -> "BacktestRequest":
        has_picker = self.picker_id is not None
        has_tickers = self.tickers is not None and len(self.tickers) > 0
        if has_picker == has_tickers:
            raise ValueError(
                "Provide exactly one of `picker_id` (AI mode) or a non-empty "
                "`tickers` list (manual mode)."
            )
        return self

    @property
    def is_manual(self) -> bool:
        return self.tickers is not None and len(self.tickers) > 0


# --------------------------- responses -------------------------------------


class Metrics(BaseModel):
    starting_cash: float
    final_value: float
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    n_trades: int
    commission_paid: float
    # Present only when taxes were modeled.
    taxes_paid: float | None = None
    terminal_tax: float | None = None
    total_tax: float | None = None
    after_tax_final_value: float | None = None
    after_tax_total_return: float | None = None
    after_tax_cagr: float | None = None
    # Pre-tax figures from the gross (tax-off) pass, and the resulting tax drag.
    pretax_cagr: float | None = None
    pretax_total_return: float | None = None
    final_value_pretax: float | None = None
    tax_drag_value: float | None = None  # $ the strategy lost to taxes
    tax_drag_cagr: float | None = None   # annualized % lost to taxes
    # Round-trip stats.
    win_rate: float | None = None
    n_round_trips: int = 0


class EquityCurve(BaseModel):
    """Chart-friendly equity curves sharing one date axis."""

    dates: list[str]
    pretax: list[float]
    aftertax: list[float]


class BenchmarkCurve(BaseModel):
    pretax: list[float]
    aftertax: list[float]


class TradeRecord(BaseModel):
    date: str
    ticker: str
    side: str
    shares: float
    price: float
    value: float
    commission: float


class RoundTrip(BaseModel):
    ticker: str
    entry_date: str
    exit_date: str
    shares: float
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    holding_days: int


class BenchmarkComparison(BaseModel):
    """SPY buy-and-hold over the same window, plus the strategy's edge over it."""

    benchmark: str
    metrics: Metrics
    excess_cagr: float
    beats_spy: bool
    # After-tax edge, present when taxes were modeled for both sides.
    excess_after_tax_cagr: float | None = None
    beats_spy_after_tax: bool | None = None
    curve: BenchmarkCurve | None = None


class BacktestResponse(BaseModel):
    mode: Literal["picker", "manual"]
    picker_id: str | None
    timer_id: str
    universe: str
    period: dict[str, str]
    tickers_used: list[str] | None = None  # manual/menu mode: the basket actually run
    trade_rule: Literal["standard", "tax_managed"] = "standard"
    metrics: Metrics
    equity_curve: EquityCurve
    trades: list[TradeRecord]
    round_trips: list[RoundTrip] = []
    benchmark: BenchmarkComparison | None = None

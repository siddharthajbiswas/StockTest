"""EngineService — wraps the StockTest engine as an in-process library.

Design notes (per STRATEGY_CATALOG.md and backtester/market.py):
  * The expensive part of a backtest is building `MarketData` (laying out every
    ticker's prices). We load all price CSVs from disk ONCE at startup, and cache
    the built `MarketData` per (universe, start, end) so repeated requests over
    the same window pay the layout cost only the first time. The full-range
    markets for both universes are pre-warmed at startup, so a default request
    (no date range) reuses a precomputed layout and never pays that cost.
  * We import the engine and grid_combos helpers — we do not copy their logic.
"""

from __future__ import annotations

import sys
import threading
from collections import OrderedDict
from pathlib import Path

import pandas as pd

# Make the StockTest project root importable (reference -> project root).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backtester import (  # noqa: E402
    Backtest,
    Combo,
    Picker,
    Strategy,
    TaxManagedCombo,
    TaxPolicy,
)
from backtester.data import UNIVERSE_EXCLUDE, load_prices  # noqa: E402
from grid_combos import benchmark_spy, build_market  # noqa: E402
from strategies.pickers import FUNDAMENTALS_PATH, PICKERS  # noqa: E402
from strategies.timers import TIMERS  # noqa: E402

from analytics import align_totals, round_trips, totals  # noqa: E402
from serialize import (  # noqa: E402
    benchmark_dict,
    metrics_dict,
    trades_list,
)
from tickers import TickerIndex  # noqa: E402

BENCHMARK_TICKER = "SPY"
_MARKET_CACHE_MAX = 16  # bound the cache so long-running servers don't grow unbounded


class UnknownTickersError(Exception):
    """Raised when a manual request names tickers we have no local data for."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Unknown tickers: {missing}")


class InvalidStrategyError(Exception):
    """Raised for an unknown picker/timer id or bad strategy parameters."""


class WarmUpGate(Strategy):
    """Wraps a strategy so it does nothing before `start`.

    Paired with a market that begins earlier, this is how a request gets a
    *warm* signal without the warm-up period polluting the scorecard: the inner
    strategy can see the extra bars through `ctx.history`, but it cannot trade
    on them, so the portfolio is still untouched cash on the first day of the
    window. `Result.since(start)` then reports the window alone.

    Without this, a 12-month-lookback strategy asked for "2010 to 2020" spends
    its first year in cash with nothing to rank, while the benchmark is
    compounding — a handicap that comes from the harness, not the strategy.
    """

    def __init__(self, inner: Strategy, start):
        self.inner = inner
        self.start = pd.Timestamp(start)

    def initialize(self, ctx) -> None:
        self.inner.initialize(ctx)

    def on_day(self, ctx) -> None:
        if ctx.date < self.start:
            return
        self.inner.on_day(ctx)


class FixedListPicker(Picker):
    """Manual mode: hold a fixed, user-supplied basket. The timer still runs
    daily on each name; the picker just never changes the candidate set. This is
    a thin Picker subclass over the existing base class — no engine logic copied.
    """

    name = "manual"

    def __init__(self, tickers: list[str]):
        self.tickers = list(tickers)

    def select(self, ctx, universe, n):
        tradable = set(universe)
        return [t for t in self.tickers if t in tradable]


class EngineService:
    def __init__(self, tickers: list[str] | None = None):
        # Load every price CSV once (full history). Reused for all requests.
        self.all_prices: dict[str, pd.DataFrame] = load_prices(tickers)
        self.available: set[str] = set(self.all_prices)
        # Global date span of the loaded price data (earliest first bar to
        # latest last bar across every ticker), so the UI can bound its date
        # pickers to what actually exists instead of accepting any date.
        self.data_range: tuple[str, str] | None = self._compute_data_range()
        # Ticker discovery index (symbol + any snapshot metadata), built once.
        self.tickers = TickerIndex(self.all_prices, FUNDAMENTALS_PATH)
        self._cache: "OrderedDict[tuple, object]" = OrderedDict()
        self._pinned: set[tuple] = set()
        self._lock = threading.Lock()

        # Pre-warm the full-range markets for both universes so a default
        # (no date range) request reuses a precomputed layout.
        for universe in ("all", "sp500-pit"):
            key = self._universe_market(universe, None, None, pin=True)  # noqa: F841

    def _compute_data_range(self) -> tuple[str, str] | None:
        """Earliest and latest calendar dates present across all loaded prices."""
        firsts = [df.index.min() for df in self.all_prices.values() if not df.empty]
        lasts = [df.index.max() for df in self.all_prices.values() if not df.empty]
        if not firsts or not lasts:
            return None
        return (min(firsts).strftime("%Y-%m-%d"), max(lasts).strftime("%Y-%m-%d"))

    # ---- price clipping (in-memory, no disk I/O) ------------------------
    def _clip(self, df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
        if start:
            df = df[df.index >= pd.Timestamp(start)]
        if end:
            df = df[df.index <= pd.Timestamp(end)]
        return df

    def _clip_universe(
        self, tickers: list[str], start: str | None, end: str | None
    ) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for t in tickers:
            df = self._clip(self.all_prices[t], start, end)
            if not df.empty:
                out[t] = df
        return out

    # ---- market cache ----------------------------------------------------
    def _cache_put(self, key: tuple, market, pin: bool) -> None:
        self._cache[key] = market
        self._cache.move_to_end(key)
        if pin:
            self._pinned.add(key)
        while len(self._cache) > _MARKET_CACHE_MAX:
            # Evict the oldest non-pinned entry.
            for k in list(self._cache):
                if k not in self._pinned:
                    del self._cache[k]
                    break
            else:
                break  # everything is pinned; stop evicting

    def _universe_market(self, universe: str, start, end, pin: bool = False):
        """MarketData over the full local universe, optionally PIT-filtered.
        UNIVERSE_EXCLUDE names (e.g. the leveraged SSO) are left out: they are
        for manual/menu mode only."""
        key = ("universe", universe, start, end)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            prices = self._clip_universe(
                sorted(t for t in self.available if t not in UNIVERSE_EXCLUDE), start, end
            )
            if not prices:
                raise InvalidStrategyError("No price data in the requested date range.")
            market = build_market(prices, universe)
            self._cache_put(key, market, pin)
            return market

    def _manual_market(self, tickers: list[str], start, end):
        """MarketData for a manual basket (+SPY so benchmark-referencing timers
        and the SPY-relative pickers/timers can see it). No PIT filter."""
        wanted = list(dict.fromkeys(tickers))  # de-dup, preserve order
        with_spy = wanted + ([BENCHMARK_TICKER] if BENCHMARK_TICKER not in wanted else [])
        key = ("manual", tuple(with_spy), start, end)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                cached = self._cache[key]
                return cached, [t for t in wanted if t in cached.tickers]
            prices = self._clip_universe(with_spy, start, end)
            basket_with_data = [t for t in wanted if t in prices]
            if not basket_with_data:
                raise InvalidStrategyError(
                    "None of the requested tickers have data in the date range."
                )
            market = build_market(prices, "all")
            self._cache_put(key, market, pin=False)
            return market, basket_with_data

    # ---- strategy construction ------------------------------------------
    def _make_picker(self, picker_id: str, params: dict):
        cls = PICKERS.get(picker_id)
        if cls is None:
            raise InvalidStrategyError(
                f"Unknown picker_id {picker_id!r}. Valid: {sorted(PICKERS)}"
            )
        try:
            return cls(**params)
        except TypeError as e:
            raise InvalidStrategyError(f"Bad params for picker {picker_id!r}: {e}")

    def _make_timer(self, timer_id: str, params: dict):
        cls = TIMERS.get(timer_id)
        if cls is None:
            raise InvalidStrategyError(
                f"Unknown timer_id {timer_id!r}. Valid: {sorted(TIMERS)}"
            )
        try:
            return cls(**params)
        except TypeError as e:
            raise InvalidStrategyError(f"Bad params for timer {timer_id!r}: {e}")

    # ---- validation (shared by save + backtest) -------------------------
    def validate_strategy(self, config) -> None:
        """Raise if a saved-strategy config wouldn't run. Uses the same picker/
        timer construction as an actual backtest, so a saved combo is guaranteed
        runnable."""
        self._make_timer(config.timer_id, config.timer_params)
        if config.mode == "manual":
            if not config.tickers:
                raise InvalidStrategyError("Manual mode needs at least one ticker.")
            missing = [t for t in config.tickers if t not in self.available]
            if missing:
                raise UnknownTickersError(missing)
        else:
            if not config.picker_id:
                raise InvalidStrategyError("Picker mode needs a picker_id.")
            self._make_picker(config.picker_id, config.picker_params)

    # ---- shared market/strategy resolution ------------------------------
    def _combo_class(self, req):
        """Combo, or TaxManagedCombo when the request asks for the gain-budget
        execution rule. Both take the same picker/timer, so every picker and
        timer in the catalog works under either rule."""
        if getattr(req, "trade_rule", "standard") != "tax_managed":
            return Combo, {}
        return TaxManagedCombo, {
            "gain_budget": getattr(req, "gain_budget", 0.01),
            "wash_days": getattr(req, "wash_days", 31),
        }

    def _resolve(self, req):
        """Return (market, make_strat, tickers_used). `make_strat` builds a
        *fresh* strategy each call (Combo/pickers carry per-run state)."""
        combo_cls, combo_kw = self._combo_class(req)
        menu = getattr(req, "menu", None)
        # Warm-up: load bars before the window so indicators are already warm on
        # its first day, and gate every strategy so nothing trades until then.
        warmup_days = int(getattr(req, "warmup_days", 0) or 0)
        data_start = req.start
        if warmup_days and req.start:
            data_start = (
                pd.Timestamp(req.start) - pd.Timedelta(days=warmup_days)
            ).date().isoformat()
        gate = (lambda s: WarmUpGate(s, req.start)) if data_start != req.start else (lambda s: s)
        if req.is_manual:
            missing = [t for t in req.tickers if t not in self.available]
            if missing:
                raise UnknownTickersError(missing)
            market, tickers_used = self._manual_market(req.tickers, data_start, req.end)
            top_n = max(1, len(req.tickers))

            def make_strat():
                return gate(combo_cls(
                    FixedListPicker(req.tickers),
                    self._make_timer(req.timer_id, req.timer_params),
                    top_n=top_n,
                    rebalance=req.rebalance,
                    **combo_kw,
                ))
        elif menu:
            # A shortlist behaves exactly like the full universe with the picker
            # filtered to `menu` — but building the market from just those names
            # is far cheaper, and in the browser it downloads a handful of
            # per-ticker files instead of the 13 MB universe bundle.
            missing = [t for t in menu if t not in self.available]
            if missing:
                raise UnknownTickersError(missing)
            market, tickers_used = self._manual_market(menu, data_start, req.end)

            def make_strat():
                return gate(combo_cls(
                    self._make_picker(req.picker_id, req.picker_params),
                    self._make_timer(req.timer_id, req.timer_params),
                    top_n=req.top_n,
                    rebalance=req.rebalance,
                    menu=tickers_used,
                    **combo_kw,
                ))
        else:
            market = self._universe_market(req.universe, data_start, req.end)
            tickers_used = None

            def make_strat():
                return gate(combo_cls(
                    self._make_picker(req.picker_id, req.picker_params),
                    self._make_timer(req.timer_id, req.timer_params),
                    top_n=req.top_n,
                    rebalance=req.rebalance,
                    **combo_kw,
                ))

        return market, make_strat, tickers_used

    def net_equity_series(self, req):
        """The strategy's after-tax (net) equity curve as a pandas Series — used
        by the out-of-sample validator to slice the exact configured combo."""
        net_policy = (
            TaxPolicy(req.tax.short_term_rate, req.tax.long_term_rate, req.tax.long_term_days)
            if req.tax.enabled
            else None
        )
        market, make_strat, _ = self._resolve(req)
        res = Backtest(
            make_strat(), market=market, cash=req.cash,
            commission_pct=req.commission_pct, slippage_pct=req.slippage_pct,
            tax_policy=net_policy,
        ).run()
        return self._clip_warmup(res, req).equity["total"]

    @staticmethod
    def _clip_warmup(res, req):
        """Drop the warm-up prefix so the scorecard covers only the window."""
        if not getattr(req, "warmup_days", 0) or not req.start:
            return res
        return res.since(req.start)

    # ---- the core run ----------------------------------------------------
    def run_backtest(self, req) -> dict:
        net_policy = (
            TaxPolicy(req.tax.short_term_rate, req.tax.long_term_rate, req.tax.long_term_days)
            if req.tax.enabled
            else None
        )
        market, make_strat, tickers_used = self._resolve(req)

        def run(policy):
            return Backtest(
                make_strat(),
                market=market,
                cash=req.cash,
                commission_pct=req.commission_pct,
                slippage_pct=req.slippage_pct,
                tax_policy=policy,
            ).run()

        # The "net" run is what the user actually experiences (taxes on if
        # requested). The "gross" run (taxes off) gives the honest pre-tax line —
        # the MarketData layout is cached, so this second pass is just the sim.
        net_res = self._clip_warmup(run(net_policy), req)
        gross_res = self._clip_warmup(run(None), req) if net_policy is not None else net_res

        dates = net_res.equity.index
        equity_curve = {
            "dates": [d.date().isoformat() for d in dates],
            "pretax": totals(gross_res),
            "aftertax": totals(net_res),
        }

        # Benchmark: SPY buy-and-hold, both pre- and after-tax, aligned to our dates.
        benchmark = None
        if BENCHMARK_TICKER in self.all_prices:
            spy_df = self._clip(self.all_prices[BENCHMARK_TICKER], req.start, req.end)
            if not spy_df.empty:
                spy_prices = {BENCHMARK_TICKER: spy_df}
                spy_net = benchmark_spy(
                    spy_prices, req.cash, req.commission_pct, req.slippage_pct, net_policy
                )
                spy_gross = (
                    benchmark_spy(spy_prices, req.cash, req.commission_pct, req.slippage_pct, None)
                    if net_policy is not None
                    else spy_net
                )
                if spy_net is not None:
                    benchmark = benchmark_dict(net_res, spy_net)
                    benchmark["curve"] = {
                        "pretax": align_totals(spy_gross, dates),
                        "aftertax": align_totals(spy_net, dates),
                    }

        rt, win_rate = round_trips(net_res.trades)
        metrics = metrics_dict(net_res)
        metrics.update(
            pretax_cagr=gross_res.cagr,
            pretax_total_return=gross_res.total_return,
            final_value_pretax=gross_res.final_value,
            tax_drag_value=gross_res.final_value - net_res.after_tax_final_value,
            tax_drag_cagr=gross_res.cagr - net_res.after_tax_cagr,
            win_rate=win_rate,
            n_round_trips=len(rt),
        )

        return {
            "mode": "manual" if req.is_manual else "picker",
            "picker_id": None if req.is_manual else req.picker_id,
            "timer_id": req.timer_id,
            "universe": "all" if (req.is_manual or getattr(req, "menu", None)) else req.universe,
            "trade_rule": getattr(req, "trade_rule", "standard"),
            "period": {
                "start": dates[0].date().isoformat(),
                "end": dates[-1].date().isoformat(),
            },
            "tickers_used": tickers_used,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "benchmark": benchmark,
            "trades": trades_list(net_res),
            "round_trips": rt,
        }

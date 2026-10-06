"""Run a strategy file against the CSV data and report per-day trades.

The strategy file is any Python module that exposes either:
  * a module-level `strategy` object, or
  * a single `Strategy` subclass (instantiated with no args).

Examples:
    python run_backtest.py --strategy strategies/sma_crossover.py \
        --tickers AAPL MSFT NVDA GOOGL --start 2015-01-01 --cash 100000

    python run_backtest.py --strategy strategies/buy_and_hold.py \
        --tickers SPY --start 2010-01-01 --show-trades
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path

from backtester import Backtest, Strategy, load_prices
from backtester.data import universe_tickers


def load_strategy(path: str) -> Strategy:
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import strategy from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    if hasattr(module, "strategy") and isinstance(module.strategy, Strategy):
        return module.strategy
    # Otherwise find a Strategy subclass defined in the module and instantiate it.
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Strategy) and obj is not Strategy and obj.__module__ == module.__name__:
            return obj()
    raise ValueError(
        f"{path} must define a `strategy` object or a Strategy subclass."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", required=True, help="Path to the algorithm .py file.")
    ap.add_argument("--tickers", nargs="+", help="Tickers to trade (default: all in data/ except UNIVERSE_EXCLUDE).")
    ap.add_argument("--start", help="Start date YYYY-MM-DD.")
    ap.add_argument("--end", help="End date YYYY-MM-DD.")
    ap.add_argument("--cash", type=float, default=100_000.0, help="Starting cash.")
    ap.add_argument("--commission-pct", type=float, default=0.0, help="Per-trade cost as a fraction (0.001 = 10bps).")
    ap.add_argument("--commission-per-share", type=float, default=0.0, help="Per-share cost.")
    ap.add_argument("--min-order-value", type=float, default=1.0, help="Skip orders smaller than this $ value.")
    ap.add_argument("--show-trades", action="store_true", help="Print the per-day trade log.")
    ap.add_argument("--save", help="Directory to write equity.csv and trades.csv.")
    ap.add_argument("--verbose", action="store_true", help="Let strategies log per-day messages.")
    args = ap.parse_args()

    strategy = load_strategy(args.strategy)
    prices = load_prices(args.tickers or universe_tickers(), start=args.start, end=args.end)
    print(f"Loaded {len(prices)} tickers. Running {type(strategy).__name__}...\n")

    bt = Backtest(
        strategy,
        prices,
        cash=args.cash,
        commission_pct=args.commission_pct,
        commission_per_share=args.commission_per_share,
        min_order_value=args.min_order_value,
        verbose=args.verbose,
    )
    result = bt.run()

    result.summary()
    if args.show_trades:
        result.trades_by_day()
    if args.save:
        result.save(args.save)
    return 0


if __name__ == "__main__":
    sys.exit(main())

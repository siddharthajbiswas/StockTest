"""A small, dependency-light daily backtester.

You write an algorithm (a `Strategy` subclass), the engine runs it over the
CSV price data in ./data one trading day at a time, and it records every trade
plus the portfolio equity curve.

Typical use:

    from backtester import Backtest, load_prices
    from strategies.sma_crossover import SmaCrossover

    prices = load_prices(["AAPL", "MSFT"])
    bt = Backtest(SmaCrossover(fast=20, slow=50), prices, cash=100_000)
    result = bt.run()
    result.summary()
"""

from .composite import Combo, Picker, Timer
from .data import load_prices
from .engine import Backtest
from .market import MarketData
from .result import Result
from .strategy import Context, Strategy
from .tax import TaxPolicy

__all__ = [
    "Backtest",
    "Combo",
    "Context",
    "MarketData",
    "Picker",
    "Result",
    "Strategy",
    "TaxPolicy",
    "Timer",
    "load_prices",
]

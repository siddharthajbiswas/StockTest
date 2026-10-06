"""Strategy-search lab: runs the real backtester engine over many windows.

Everything here drives `backtester.Backtest` directly -- the same engine the
website's JavaScript port is pinned to by the golden suite -- so tax lots, the
annual settlement, the terminal liquidation tax, commission and slippage are
exactly the site's. The lab only adds measurement (window checkpoints, a shared
SPY benchmark, statistics) and new strategy building blocks.

See research/lab/PROTOCOL.md for the evaluation protocol and how to use it.
"""

"""Turn an engine `Result` into JSON-serializable response pieces."""

from __future__ import annotations

import math

from backtester.result import Result


def _finite(x: float | None) -> float | None:
    """JSON has no NaN/Inf — coerce them to None so the payload stays valid."""
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def metrics_dict(res: Result) -> dict:
    n_trades = 0 if res.trades.empty else len(res.trades)
    commission = 0.0 if res.trades.empty else float(res.trades["commission"].sum())
    out = {
        "starting_cash": _finite(res.starting_cash),
        "final_value": _finite(res.final_value),
        "total_return": _finite(res.total_return),
        "cagr": _finite(res.cagr),
        "sharpe": _finite(res.sharpe),
        "max_drawdown": _finite(res.max_drawdown),
        "n_trades": n_trades,
        "commission_paid": _finite(commission),
        "taxes_paid": None,
        "terminal_tax": None,
        "total_tax": None,
        "after_tax_final_value": None,
        "after_tax_total_return": None,
        "after_tax_cagr": None,
    }
    if res.taxes_paid is not None:  # taxes were modeled
        out.update(
            taxes_paid=_finite(res.taxes_paid),
            terminal_tax=_finite(res.terminal_tax),
            total_tax=_finite(res.total_tax),
            after_tax_final_value=_finite(res.after_tax_final_value),
            after_tax_total_return=_finite(res.after_tax_total_return),
            after_tax_cagr=_finite(res.after_tax_cagr),
        )
    return out


def trades_list(res: Result) -> list[dict]:
    if res.trades.empty:
        return []
    out = []
    for date, t in res.trades.iterrows():
        out.append(
            {
                "date": date.date().isoformat(),
                "ticker": str(t["ticker"]),
                "side": str(t["side"]),
                "shares": float(t["shares"]),
                "price": float(t["price"]),
                "value": float(t["value"]),
                "commission": float(t["commission"]),
            }
        )
    return out


def benchmark_dict(strat: Result, spy: Result) -> dict:
    """SPY buy-and-hold metrics plus the strategy's edge over it."""
    spy_metrics = metrics_dict(spy)
    excess_cagr = _finite((strat.cagr or 0.0) - (spy.cagr or 0.0))
    out = {
        "benchmark": "SPY",
        "metrics": spy_metrics,
        "excess_cagr": excess_cagr,
        "beats_spy": (strat.cagr or 0.0) > (spy.cagr or 0.0),
        "excess_after_tax_cagr": None,
        "beats_spy_after_tax": None,
    }
    if strat.taxes_paid is not None and spy.taxes_paid is not None:
        out["excess_after_tax_cagr"] = _finite(
            (strat.after_tax_cagr or 0.0) - (spy.after_tax_cagr or 0.0)
        )
        out["beats_spy_after_tax"] = (strat.after_tax_cagr or 0.0) > (
            spy.after_tax_cagr or 0.0
        )
    return out

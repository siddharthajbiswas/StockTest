"""Behavioural tests for the reference implementation.

These replace the old `web/backend/tests/` suite, which drove everything through
a FastAPI `TestClient`. The HTTP API is gone — the app talks to the TypeScript
engine in a Web Worker — so what survives here is the behaviour that was being
tested *underneath* the endpoints, called directly on `EngineService`.

What deliberately did NOT survive, and where its coverage moved:

  * save / list / delete round-trip — the saved-strategy store was a JSON file
    on the server; it is now IndexedDB in the browser, verified end-to-end in
    Chrome (migration, persistence across reload, delete, LRU eviction).
  * HTTP status codes and response envelopes — there is no HTTP layer. The
    equivalent error surface is the worker protocol, covered by
    `web/engine/test/worker.test.ts`.

Run:  .venv/bin/python -m pytest reference -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

from models import BacktestRequest, StrategyConfig  # noqa: E402
from service import (  # noqa: E402
    EngineService,
    InvalidStrategyError,
    UnknownTickersError,
)


@pytest.fixture(scope="module")
def svc() -> EngineService:
    """One real service over the actual local CSVs. No mocking."""
    return EngineService()


def _ai_config(**over) -> dict:
    cfg = {
        "mode": "picker",
        "picker_id": "momentum",
        "picker_params": {"lookback": 63},
        "timer_id": "ma_cross",
        "timer_params": {"fast": 20, "slow": 100},
        "top_n": 10,
        "rebalance": "M",
        "universe": "sp500-pit",
        "start": "2016-01-01",
        "end": "2020-01-01",
    }
    cfg.update(over)
    return cfg


# ---------------------------------------------------------------------------
def test_valid_config_passes_validation(svc):
    svc.validate_strategy(StrategyConfig(**_ai_config()))


def test_invalid_picker_params_rejected(svc):
    """A config that would blow up at run time must be caught up front —
    this is what stopped an unrunnable strategy being saved."""
    bad = StrategyConfig(**_ai_config(picker_params={"not_a_real_param": 5}))
    with pytest.raises(InvalidStrategyError):
        svc.validate_strategy(bad)


def test_unknown_ticker_is_reported_with_the_offending_symbols(svc):
    cfg = StrategyConfig(
        mode="manual", tickers=["AAPL", "NOPE_TICKER"], timer_id="buy_hold",
        picker_id=None, picker_params={}, timer_params={},
    )
    with pytest.raises(UnknownTickersError) as e:
        svc.validate_strategy(cfg)
    assert e.value.missing == ["NOPE_TICKER"]


def test_manual_mode_needs_at_least_one_ticker(svc):
    cfg = StrategyConfig(
        mode="manual", tickers=[], timer_id="buy_hold",
        picker_id=None, picker_params={}, timer_params={},
    )
    with pytest.raises(InvalidStrategyError):
        svc.validate_strategy(cfg)


# ---------------------------------------------------------------------------
def _run(svc, **over):
    base = dict(
        picker_id="momentum", timer_id="buy_hold", top_n=10,
        universe="sp500-pit", start="2016-01-01", end="2020-01-01",
    )
    base.update(over)
    return svc.run_backtest(BacktestRequest(**base))


def test_custom_params_actually_change_the_result(svc):
    """Non-default params must change the backtest — otherwise the
    customization isn't real, only cosmetic."""
    default_run = _run(svc, picker_params={"lookback": 126})
    custom_run = _run(svc, picker_params={"lookback": 21})
    assert (
        default_run["metrics"]["final_value"] != custom_run["metrics"]["final_value"]
    ), "different momentum lookbacks should pick different baskets"


def test_response_reports_the_picker_actually_run(svc):
    """The UI keys its look-ahead warning off the returned picker_id, so it has
    to reflect what ran rather than whatever was requested elsewhere."""
    out = _run(svc, picker_id="value_pe", picker_params={},
               start="2023-01-01", end="2024-06-01")
    assert out["picker_id"] == "value_pe"
    assert out["mode"] == "picker"


def test_manual_mode_reports_the_tickers_used(svc):
    out = svc.run_backtest(BacktestRequest(
        tickers=["AAPL", "MSFT"], timer_id="buy_hold",
        start="2019-01-01", end="2021-12-31",
    ))
    assert out["mode"] == "manual"
    assert out["tickers_used"] == ["AAPL", "MSFT"]
    # SPY is added to the market for benchmark/relative strategies, but it is
    # not part of the user's basket.
    assert "SPY" not in out["tickers_used"]
    assert out["benchmark"] is not None


def test_exactly_one_mode_is_enforced(svc):
    with pytest.raises(ValueError):
        BacktestRequest(picker_id="momentum", tickers=["AAPL"], timer_id="buy_hold")
    with pytest.raises(ValueError):
        BacktestRequest(timer_id="buy_hold")

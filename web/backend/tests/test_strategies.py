"""Integration tests for saving/listing/deleting named strategies, and that a
saved combo's custom params actually flow through to /backtest."""

from __future__ import annotations


def _ai_config(**over):
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


def test_save_list_delete_roundtrip(client):
    # Initially empty.
    assert client.get("/strategies/mine").json()["strategies"] == []

    # Save one.
    r = client.post("/strategies/mine", json={"name": "My Momentum", "config": _ai_config()})
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["name"] == "My Momentum"
    assert saved["id"]
    assert saved["config"]["picker_params"] == {"lookback": 63}
    assert saved["config"]["timer_params"] == {"fast": 20, "slow": 100}

    # It appears in the list.
    lst = client.get("/strategies/mine").json()["strategies"]
    assert len(lst) == 1 and lst[0]["id"] == saved["id"]

    # Delete it.
    d = client.delete(f"/strategies/mine/{saved['id']}")
    assert d.status_code == 200 and d.json()["ok"] is True
    assert client.get("/strategies/mine").json()["strategies"] == []


def test_delete_missing_is_404(client):
    assert client.delete("/strategies/mine/doesnotexist").status_code == 404


def test_save_invalid_params_rejected(client):
    bad = _ai_config(picker_params={"not_a_real_param": 5})
    r = client.post("/strategies/mine", json={"name": "Bad", "config": bad})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error"] == "invalid_strategy"


def test_save_manual_unknown_ticker_404(client):
    cfg = {"mode": "manual", "tickers": ["AAPL", "NOPE_TICKER"], "timer_id": "buy_hold"}
    r = client.post("/strategies/mine", json={"name": "x", "config": cfg})
    assert r.status_code == 404
    assert r.json()["detail"]["unavailable"] == ["NOPE_TICKER"]


def test_custom_params_flow_to_backtest(client):
    """Non-default params must change the backtest — otherwise the customization
    isn't real. Compare default momentum vs a short-lookback momentum."""
    base = {
        "picker_id": "momentum",
        "timer_id": "buy_hold",
        "top_n": 10,
        "universe": "sp500-pit",
        "start": "2016-01-01",
        "end": "2020-01-01",
    }
    default_run = client.post("/backtest", json={**base, "picker_params": {"lookback": 126}})
    custom_run = client.post("/backtest", json={**base, "picker_params": {"lookback": 21}})
    assert default_run.status_code == custom_run.status_code == 200
    # Different momentum lookbacks pick different baskets -> different final value.
    assert default_run.json()["metrics"]["final_value"] != custom_run.json()["metrics"]["final_value"]

    # A fundamentals picker keeps its look-ahead-risk identity regardless of params;
    # the response still reports the picker actually used.
    fund = client.post(
        "/backtest",
        json={**base, "picker_id": "value_pe", "picker_params": {}, "start": "2023-01-01", "end": "2024-06-01"},
    )
    assert fund.status_code == 200
    assert fund.json()["picker_id"] == "value_pe"

"""Integration tests against real local data (no mocking).

Covered:
  * catalog endpoints (/pickers, /timers, /universe/options)
  * an AI-picker backtest
  * a manual-ticker-list backtest
  * a manual request naming an invalid ticker -> 404 listing what's unavailable
"""

from __future__ import annotations

# A short, recent window keeps each backtest fast while still producing trades.
START = "2015-01-01"
END = "2020-01-01"


# ---- catalog endpoints ---------------------------------------------------
def test_catalog_endpoints(client):
    pickers = client.get("/pickers").json()["pickers"]
    timers = client.get("/timers").json()["timers"]
    universes = client.get("/universe/options").json()["universes"]

    assert len(pickers) == 10
    assert len(timers) == 10
    assert {u["id"] for u in universes} == {"all", "sp500-pit"}

    momentum = next(p for p in pickers if p["id"] == "momentum")
    assert momentum["look_ahead_risk"] is False
    assert any(p["name"] == "lookback" for p in momentum["params"])

    value = next(p for p in pickers if p["id"] == "value_pe")
    assert value["look_ahead_risk"] is True  # fundamentals -> look-ahead flagged
    # Every universe option carries a bias caveat.
    assert all(u["bias_caveat"] for u in universes)


# ---- ticker discovery ----------------------------------------------------
def test_tickers_full_list(client):
    data = client.get("/tickers").json()
    assert data["universe"]["fixed"] is True
    assert data["universe"]["count"] == len(data["tickers"])
    assert data["universe"]["count"] > 500  # ~530 fixed universe
    assert "FIXED universe" in data["universe"]["note"]

    aapl = next(t for t in data["tickers"] if t["symbol"] == "AAPL")
    assert set(aapl) >= {"symbol", "name", "has_fundamentals", "market_cap",
                         "date_from", "date_to"}
    assert aapl["has_fundamentals"] is True  # AAPL is in the snapshot


def test_ticker_search_prefix(client):
    data = client.get("/tickers/search", params={"q": "AAP"}).json()
    symbols = [r["symbol"] for r in data["results"]]
    assert "AAPL" in symbols
    # Prefix matches should outrank incidental substring matches.
    assert all(s.upper().startswith("AAP") for s in symbols[:2]) or symbols[0] == "AAPL"
    assert "FIXED universe" in data["universe"]["note"]


def test_ticker_search_exact_ranks_first(client):
    data = client.get("/tickers/search", params={"q": "MSFT"}).json()
    assert data["results"][0]["symbol"] == "MSFT"


def test_ticker_search_fuzzy_typo(client):
    # A transposed/typo'd query still surfaces the intended symbol via fuzzy match.
    data = client.get("/tickers/search", params={"q": "MSTF", "limit": 10}).json()
    assert "MSFT" in [r["symbol"] for r in data["results"]]


def test_ticker_search_empty_query_rejected(client):
    assert client.get("/tickers/search", params={"q": ""}).status_code == 422


# ---- 1. AI-picker backtest ----------------------------------------------
def test_ai_picker_backtest(client):
    body = {
        "picker_id": "momentum",
        "picker_params": {"lookback": 126},
        "timer_id": "buy_hold",
        "top_n": 10,
        "rebalance": "M",
        "universe": "sp500-pit",
        "start": START,
        "end": END,
    }
    r = client.post("/backtest", json=body)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["mode"] == "picker"
    assert data["picker_id"] == "momentum"
    assert data["timer_id"] == "buy_hold"
    assert data["universe"] == "sp500-pit"

    m = data["metrics"]
    assert m["starting_cash"] == 100_000.0
    assert m["final_value"] > 0
    # Taxes are on by default -> after-tax metrics populated.
    assert m["after_tax_cagr"] is not None
    assert m["total_tax"] is not None

    # Equity curve carries aligned pre-tax and after-tax lines.
    eq = data["equity_curve"]
    assert len(eq["dates"]) == len(eq["pretax"]) == len(eq["aftertax"]) > 100
    # Taxes only cost money, so the after-tax line never ends above pre-tax.
    assert eq["aftertax"][-1] <= eq["pretax"][-1] + 1e-6
    assert data["metrics"]["n_trades"] > 0
    assert len(data["trades"]) == data["metrics"]["n_trades"]

    # New derived metrics.
    assert m["pretax_cagr"] is not None
    assert m["tax_drag_value"] is not None and m["tax_drag_value"] >= -1e-6
    assert m["n_round_trips"] == len(data["round_trips"])
    if data["round_trips"]:
        assert 0.0 <= m["win_rate"] <= 1.0
        rt = data["round_trips"][0]
        assert set(rt) >= {"ticker", "entry_date", "exit_date", "entry_price",
                           "exit_price", "pnl", "return_pct", "holding_days"}

    # Benchmark comparison vs SPY, with an aligned curve for overlaying.
    b = data["benchmark"]
    assert b["benchmark"] == "SPY"
    assert isinstance(b["beats_spy"], bool)
    assert b["beats_spy_after_tax"] is not None
    assert len(b["curve"]["aftertax"]) == len(eq["dates"])


# ---- 2. Manual-ticker-list backtest -------------------------------------
def test_manual_ticker_backtest(client):
    body = {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "timer_id": "ma_cross",
        "start": START,
        "end": END,
    }
    r = client.post("/backtest", json=body)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["mode"] == "manual"
    assert data["picker_id"] is None
    assert set(data["tickers_used"]) == {"AAPL", "MSFT", "GOOGL"}

    # Only the requested names (never SPY, which we inject only for the market)
    # should ever be traded by the strategy.
    traded = {t["ticker"] for t in data["trades"]}
    assert traded <= {"AAPL", "MSFT", "GOOGL"}
    assert traded  # ma_cross should trade at least one of them over 5 years

    assert data["metrics"]["final_value"] > 0
    assert data["benchmark"]["benchmark"] == "SPY"


# ---- 3. Invalid ticker -> clear 404 -------------------------------------
def test_manual_invalid_ticker(client):
    body = {
        "tickers": ["AAPL", "NOTAREALTICKER", "ALSOFAKE"],
        "timer_id": "buy_hold",
        "start": START,
        "end": END,
    }
    r = client.post("/backtest", json=body)
    assert r.status_code == 404, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "unknown_tickers"
    # The whole request fails clearly, listing exactly the bad symbols.
    assert set(detail["unavailable"]) == {"NOTAREALTICKER", "ALSOFAKE"}


# ---- extra: request that supplies neither / both modes -> 422 -----------
def test_mode_validation(client):
    neither = client.post("/backtest", json={"timer_id": "buy_hold"})
    assert neither.status_code == 422

    both = client.post(
        "/backtest",
        json={"picker_id": "momentum", "tickers": ["AAPL"], "timer_id": "buy_hold"},
    )
    assert both.status_code == 422

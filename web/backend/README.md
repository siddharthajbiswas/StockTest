# StockTest Backtest API

A FastAPI backend that wraps the existing Picker×Timer engine **as a library**
(it imports `backtester`, `strategies`, and `grid_combos` — it does not
reimplement any engine logic). See `../../STRATEGY_CATALOG.md` for the strategy
reference these endpoints expose.

## Running

```bash
# from this directory (web/backend), using the project venv:
../../.venv/bin/python -m uvicorn app:app --reload --port 8000
```

On startup the service loads every price CSV in `data/` **once** and pre-warms
the `MarketData` layout for both universes (`all`, `sp500-pit`). That layout is
the expensive part of a backtest (~seconds over 500 tickers × 26y), so a request
that uses the full date range reuses a precomputed market and pays only the cost
of the run itself. Markets for other date ranges are built on first use and
cached (bounded LRU).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + tickers loaded. |
| GET | `/pickers` | The 10 pickers: `id`, `name`, `description`, `data_source`, `look_ahead_risk`, `params`. |
| GET | `/timers` | The 10 timers, same shape (all price-only). |
| GET | `/universe/options` | `all` vs `sp500-pit`, each with a plain-language description and its bias caveat. |
| GET | `/tickers` | Full ticker list + metadata, for a browsable manual-picker UI. |
| GET | `/tickers/search?q=&limit=` | Prefix/fuzzy ticker search-as-you-type. |
| POST | `/backtest` | Run a single Picker×Timer (or manual-basket) backtest. |

Interactive docs at `/docs` once running.

## Ticker discovery (manual mode)

Manual mode picks from a **fixed universe of ~530 tickers** that have local price
CSVs — **not "any stock."** Both discovery endpoints return a `universe` block
that states this explicitly; the frontend (Phase W4) must surface it so users
understand a symbol they don't see here simply can't be backtested.

`GET /tickers` — full browsable list:

```jsonc
{
  "universe": {
    "count": 528, "fixed": true, "has_company_names": false,
    "note": "This is a FIXED universe of 528 tickers backed by local price data — not the whole market. ..."
  },
  "tickers": [
    {"symbol": "AAPL", "name": null, "has_fundamentals": true,
     "market_cap": 4.53e12, "date_from": "1980-12-12", "date_to": "2026-07-01"},
    ...
  ]
}
```

`GET /tickers/search?q=AAP&limit=20` — search-as-you-type. Ranking: exact symbol
> symbol prefix > symbol substring > name prefix/substring > fuzzy (typo-tolerant,
e.g. `MSTF` → `MSFT`). Same `universe` block, plus `query`, `count`, `results`.

> **No company names locally.** The fundamentals snapshot has no name column, so
> `name` is `null` and search is symbol-only (`has_company_names: false`). The
> join auto-detects a `name`/`longName`/`shortName` column if a future snapshot
> adds one — names then appear with no code change.

## POST /backtest

Provide **exactly one** of `picker_id` (AI mode) or a non-empty `tickers` list
(manual mode). Manual mode skips picker logic entirely and applies the timer
directly to the given basket.

```jsonc
{
  // --- selection: pick ONE mode ---
  "picker_id": "momentum",          // AI mode; or omit and pass "tickers"
  "picker_params": {"lookback": 126},
  "tickers": null,                   // manual mode: ["AAPL","MSFT",...]

  // --- timer (always) ---
  "timer_id": "ma_cross",
  "timer_params": {"fast": 50, "slow": 200},

  // --- portfolio / cadence ---
  "top_n": 15,                       // names held (AI mode)
  "rebalance": "M",                  // D | W | M | Q
  "cash": 100000,

  // --- window (inclusive, YYYY-MM-DD; null = full history) ---
  "start": "2015-01-01",
  "end": "2020-01-01",

  // --- universe & costs ---
  "universe": "sp500-pit",           // all | sp500-pit  (ignored in manual mode)
  "commission_pct": 0.0005,
  "slippage_pct": 0.0005,
  "tax": {"enabled": true, "short_term_rate": 0.35,
          "long_term_rate": 0.15, "long_term_days": 365}
}
```

### Response (abridged)

```jsonc
{
  "mode": "picker",                  // or "manual"
  "picker_id": "momentum",           // null in manual mode
  "timer_id": "ma_cross",
  "universe": "sp500-pit",
  "period": {"start": "2015-01-02", "end": "2019-12-31"},
  "tickers_used": null,              // manual mode: the basket actually run
  "metrics": {
    "starting_cash": 100000, "final_value": ..., "total_return": ...,
    "cagr": ..., "sharpe": ..., "max_drawdown": ...,
    "n_trades": ..., "commission_paid": ...,
    // present when tax.enabled:
    "taxes_paid": ..., "terminal_tax": ..., "total_tax": ...,
    "after_tax_final_value": ..., "after_tax_total_return": ..., "after_tax_cagr": ...
  },
  "equity_curve": {"dates": [...], "total": [...], "cash": [...], "holdings": [...]},
  "trades": [{"date": ..., "ticker": ..., "side": "BUY", "shares": ...,
              "price": ..., "value": ..., "commission": ...}],
  "benchmark": {
    "benchmark": "SPY",
    "metrics": { ... same shape ... },
    "excess_cagr": ..., "beats_spy": false,
    "excess_after_tax_cagr": ..., "beats_spy_after_tax": false
  }
}
```

### Errors

- **404** — a manual request named tickers not in the local dataset. The whole
  request fails (nothing runs silently); the body lists exactly what's missing:
  `{"detail": {"error": "unknown_tickers", "unavailable": ["FAKE1", ...]}}`.
- **422** — neither/both selection modes supplied, or invalid picker/timer id or
  params.

## Tests

Real integration tests against the local CSVs (no mocking): an AI-picker
backtest, a manual-ticker backtest, and an invalid-ticker 404.

```bash
../../.venv/bin/python -m pytest tests/ -q
```

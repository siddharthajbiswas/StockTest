"""FastAPI backend wrapping the StockTest engine.

Run from the project root:
    web/backend/... $ uvicorn app:app --reload        # (with web/backend on the path)
or:
    StockTest $ uvicorn web.backend.app:app --reload   # not supported; use the dir form

The service loads all price data and pre-warms MarketData at startup (see
service.EngineService), so per-request latency is the backtest itself, not the
data layout.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Ensure both the project root and this dir are importable regardless of CWD.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]  # web/backend -> project root (has backtester/, strategies/)
for _p in (str(_ROOT), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from catalog import (  # noqa: E402
    PICKER_CATALOG,
    TIMER_CATALOG,
    UNIVERSE_OPTIONS,
)
from models import (  # noqa: E402
    BacktestRequest,
    BacktestResponse,
    SavedStrategy,
    SaveStrategyRequest,
    StrategyConfig,
    ValidateRequest,
)
from oos_validation import ValidationRunner  # noqa: E402
from service import (  # noqa: E402
    EngineService,
    InvalidStrategyError,
    UnknownTickersError,
)
from store import StrategyStore  # noqa: E402

_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the engine service once, at startup: loads all CSVs and pre-warms
    # the MarketData layout so the first real request doesn't pay that cost.
    _state["engine"] = EngineService()
    _state["store"] = StrategyStore()
    # Serialized background runner for out-of-sample validations (slow: it
    # reruns many combos over many windows). Shares the pre-warmed engine.
    _state["validator"] = ValidationRunner(_state["engine"])
    yield
    _state.clear()


app = FastAPI(
    title="StockTest Backtest API",
    version="1.0.0",
    description="Wraps the composable Picker×Timer backtesting engine.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def engine() -> EngineService:
    return _state["engine"]


def store() -> StrategyStore:
    return _state["store"]


def validator() -> ValidationRunner:
    return _state["validator"]


def _universe_note() -> dict:
    """The fixed-universe limitation the frontend must communicate (Phase W4).
    Manual mode can only pick from these locally-stored tickers — not "any stock"."""
    eng = engine()
    return {
        "count": eng.tickers.count(),
        "fixed": True,
        "has_company_names": eng.tickers.has_name_data,
        "note": (
            f"This is a FIXED universe of {eng.tickers.count()} tickers backed by "
            "local price data — not the whole market. Symbols outside this set "
            "cannot be backtested. Company-name search is unavailable when the "
            "fundamentals snapshot has no name column (symbol-only matching)."
        ),
    }


@app.get("/health")
def health() -> dict:
    eng = engine()
    resp = {"status": "ok", "tickers_loaded": len(eng.available)}
    if eng.data_range is not None:
        resp["data_start"], resp["data_end"] = eng.data_range
    return resp


@app.get("/tickers")
def get_tickers() -> dict:
    """Full ticker list with metadata, for a browsable manual-picker UI."""
    eng = engine()
    return {"universe": _universe_note(), "tickers": eng.tickers.all()}


@app.get("/tickers/search")
def search_tickers(
    q: str = Query(..., min_length=1, description="Prefix/fuzzy query over symbol (and name if available)."),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Search-as-you-type over the fixed local universe."""
    eng = engine()
    results = eng.tickers.search(q, limit=limit)
    return {
        "universe": _universe_note(),
        "query": q,
        "count": len(results),
        "results": results,
    }


@app.get("/pickers")
def get_pickers() -> dict:
    return {"pickers": PICKER_CATALOG}


@app.get("/timers")
def get_timers() -> dict:
    return {"timers": TIMER_CATALOG}


@app.get("/universe/options")
def get_universe_options() -> dict:
    return {"universes": UNIVERSE_OPTIONS}


@app.post("/backtest", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest) -> dict:
    eng = engine()
    try:
        return eng.run_backtest(req)
    except UnknownTickersError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_tickers",
                "message": (
                    "One or more requested tickers are not in the local dataset."
                ),
                "unavailable": e.missing,
            },
        )
    except InvalidStrategyError as e:
        raise HTTPException(status_code=422, detail={"error": "invalid_strategy", "message": str(e)})


# --------------------------- saved strategies ------------------------------
@app.get("/strategies/mine")
def list_my_strategies() -> dict:
    return {"strategies": store().list()}


@app.post("/strategies/mine", response_model=SavedStrategy, status_code=201)
def save_my_strategy(req: SaveStrategyRequest) -> dict:
    # Validate the combo runs before we persist it, so a saved strategy is
    # guaranteed re-runnable.
    try:
        engine().validate_strategy(req.config)
    except UnknownTickersError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_tickers",
                "message": "One or more tickers are not in the local dataset.",
                "unavailable": e.missing,
            },
        )
    except InvalidStrategyError as e:
        raise HTTPException(status_code=422, detail={"error": "invalid_strategy", "message": str(e)})
    return store().add(req.name, req.config.model_dump())


@app.delete("/strategies/mine/{sid}")
def delete_my_strategy(sid: str) -> dict:
    if not store().delete(sid):
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": f"No saved strategy {sid!r}."})
    return {"ok": True, "id": sid}


# --------------------------- out-of-sample validation ----------------------
@app.post("/validate", status_code=202)
def start_validation(req: ValidateRequest) -> dict:
    """Kick off an out-of-sample check for an inline config or a saved id.

    This is slow (it reruns many combos over many windows), so it runs on a
    background thread; the client polls GET /validate/{job_id} for the result.
    """
    if req.strategy_id is not None:
        entry = next((s for s in store().list() if s["id"] == req.strategy_id), None)
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"No saved strategy {req.strategy_id!r}."},
            )
        cfg = StrategyConfig(**entry["config"])
    else:
        cfg = req.config  # validated by the model to be present when no id

    params = {
        "split": req.split,
        "train_years": req.train_years,
        "step_years": req.step_years,
        "price_only": req.price_only,
    }
    job_id = validator().submit(cfg, params)
    return {"job_id": job_id, "status": "running"}


@app.get("/validate/{job_id}")
def get_validation(job_id: str) -> dict:
    job = validator().get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"No validation job {job_id!r}."},
        )
    if job["status"] == "error":
        # Keep a 200 so the poller reads the message cleanly rather than
        # tripping the generic error path; the status field carries the failure.
        return {"status": "error", "error": job.get("error", "validation failed")}
    return job

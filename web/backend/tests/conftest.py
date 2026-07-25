"""Make the backend modules importable and provide a shared TestClient.

Everything is real: the client boots the FastAPI lifespan, which loads the
actual local CSVs in data/. No mocking — the tests exercise the whole stack.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# web/backend (so `from app import app`, `from service import ...` resolve).
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Point the saved-strategy store at a throwaway file so tests never touch the
# real store. Must be set before the app's lifespan builds the StrategyStore.
os.environ["STOCKTEST_STRATEGY_STORE"] = str(
    Path(tempfile.gettempdir()) / "stocktest_test_strategies.json"
)

from app import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_store():
    # Start each test from an empty store.
    p = Path(os.environ["STOCKTEST_STRATEGY_STORE"])
    if p.exists():
        p.unlink()
    yield


@pytest.fixture(scope="session")
def client():
    # `with` triggers startup (data load + market pre-warm) and shutdown.
    with TestClient(app) as c:
        yield c

"""A tiny JSON-file store for user-saved strategies.

Deliberately dependency-free (no DB): saved strategies are a small list, read
and written atomically under a lock. Point it elsewhere with the
STOCKTEST_STRATEGY_STORE env var (the tests use a temp file).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent / "store" / "saved_strategies.json"


class StrategyStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("STOCKTEST_STRATEGY_STORE", _DEFAULT_PATH))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[dict]:
        try:
            with open(self.path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, data: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.path)  # atomic on POSIX

    def list(self) -> list[dict]:
        with self._lock:
            return self._read()

    def add(self, name: str, config: dict) -> dict:
        entry = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "config": config,
        }
        with self._lock:
            data = self._read()
            data.insert(0, entry)  # newest first
            self._write(data)
        return entry

    def delete(self, sid: str) -> bool:
        with self._lock:
            data = self._read()
            kept = [e for e in data if e.get("id") != sid]
            if len(kept) == len(data):
                return False
            self._write(kept)
            return True

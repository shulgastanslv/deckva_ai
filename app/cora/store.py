"""In-memory CoraRun store."""

from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.RLock()
_runs: dict[str, dict[str, Any]] = {}


def save_run(run: dict[str, Any]) -> dict[str, Any]:
    run_id = run.get("coraRunId")
    if not run_id:
        raise RuntimeError("coraRunId required")
    with _lock:
        existing = _runs.get(run_id, {})
        merged = {**existing, **run, "updatedAt": time.time()}
        if "createdAt" not in merged:
            merged["createdAt"] = time.time()
        _runs[run_id] = merged
        return dict(merged)


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _runs.get(run_id)
        return dict(row) if row else None


def list_runs_for_user(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        rows = [dict(r) for r in _runs.values() if r.get("userId") == user_id]
    rows.sort(key=lambda r: r.get("createdAt", 0), reverse=True)
    return rows[:limit]

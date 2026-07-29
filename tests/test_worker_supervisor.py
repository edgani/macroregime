"""Worker supervisor tests (R9.4): postcondition checks are fail-closed and
honest about stale snapshots, error states, and missing files."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.worker_supervisor import REQUIRED_STATUS_STATE, check_cycle_postconditions

UTC = dt.timezone.utc


def _write(path: Path, payload: dict, *, age_seconds: float = 0) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    past = time.time() - age_seconds
    os.utime(path, (past, past))
    return path


def _status(state: str = REQUIRED_STATUS_STATE, error: str | None = None) -> dict:
    return {"state": state, "error": error, "last_success": "2026-07-29T01:55:17Z"}


def test_fresh_cycle_passes(tmp_path):
    snap = _write(tmp_path / "desk_snapshot.json", {"meta": {}}, age_seconds=60)
    status = _write(tmp_path / "worker_status.json", _status())
    result = check_cycle_postconditions(snap, status, max_age_seconds=1800)
    assert result["ok"], result
    assert result["status_state"] == REQUIRED_STATUS_STATE


def test_stale_snapshot_fails(tmp_path):
    snap = _write(tmp_path / "desk_snapshot.json", {"meta": {}}, age_seconds=7200)
    status = _write(tmp_path / "worker_status.json", _status())
    result = check_cycle_postconditions(snap, status, max_age_seconds=1800)
    assert not result["ok"]
    assert any(f.startswith("DESK_SNAPSHOT_STALE") for f in result["failures"])


def test_worker_error_state_fails(tmp_path):
    snap = _write(tmp_path / "desk_snapshot.json", {"meta": {}}, age_seconds=10)
    status = _write(tmp_path / "worker_status.json", _status(state="CURRENT_CONTEXT_ERROR", error="SegFault"))
    result = check_cycle_postconditions(snap, status, max_age_seconds=1800)
    assert not result["ok"]
    assert any(f.startswith("WORKER_STATE_NOT_READY") for f in result["failures"])
    assert any(f.startswith("WORKER_REPORTED_ERROR") for f in result["failures"])


def test_missing_files_fail(tmp_path):
    result = check_cycle_postconditions(
        tmp_path / "no_snapshot.json", tmp_path / "no_status.json", max_age_seconds=1800
    )
    assert not result["ok"]
    assert "DESK_SNAPSHOT_MISSING" in result["failures"]
    assert "WORKER_STATUS_MISSING" in result["failures"]


def test_unreadable_status_fails(tmp_path):
    snap = _write(tmp_path / "desk_snapshot.json", {"meta": {}}, age_seconds=10)
    status = tmp_path / "worker_status.json"
    status.write_text("{not json", encoding="utf-8")
    result = check_cycle_postconditions(snap, status, max_age_seconds=1800)
    assert not result["ok"]
    assert any(f.startswith("WORKER_STATUS_UNREADABLE") for f in result["failures"])

"""Atomic local runtime snapshot store.

The UI reads this store only; network collectors run in a separate worker. This removes provider
latency from Streamlit reruns and gives the dashboard website-like first paint from last-good data.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import json
import os
import time

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)
SNAPSHOT = RUNTIME / "desk_snapshot.json"
STATUS = RUNTIME / "worker_status.json"
PID = RUNTIME / "worker.pid"
FORCE = RUNTIME / "force_refresh.flag"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, default=str, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj.setdefault("_file_age_seconds", max(0.0, time.time() - path.stat().st_mtime))
        return obj
    except Exception:
        return None


def read_snapshot() -> Optional[dict]:
    return read_json(SNAPSHOT)


def write_snapshot(desk: dict) -> None:
    desk = dict(desk or {})
    runtime = dict(desk.get("runtime") or {})
    runtime.update({"snapshot_written_at": now_iso(), "architecture": "background-worker/local-snapshot"})
    desk["runtime"] = runtime
    atomic_write(SNAPSHOT, desk)


def read_status() -> Optional[dict]:
    return read_json(STATUS)


def write_status(**kwargs) -> None:
    current = read_status() or {}
    current.update(kwargs)
    current["updated_at"] = now_iso()
    atomic_write(STATUS, current)


def request_force_refresh() -> None:
    FORCE.write_text(now_iso(), encoding="utf-8")


def consume_force_refresh() -> bool:
    if not FORCE.exists():
        return False
    try:
        FORCE.unlink()
    except Exception:
        pass
    return True


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def worker_alive() -> bool:
    try:
        return PID.exists() and pid_alive(int(PID.read_text().strip()))
    except Exception:
        return False

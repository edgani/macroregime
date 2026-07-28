"""Non-blocking desk cache and background refresh runtime for War Room OS v7."""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DESK_SCHEMA_VERSION = "V7_NONBLOCKING_REFRESH_2026_07_18"
DESK_CACHE = CACHE_DIR / "desk_v7.pkl"
STATUS_PATH = CACHE_DIR / "refresh_status_v7.json"
LOCK_PATH = CACHE_DIR / "refresh_v7.lock"
LOG_PATH = CACHE_DIR / "refresh_v7.log"
DEFAULT_HARD_TIMEOUT = int(os.environ.get("WARROOM_REFRESH_HARD_TIMEOUT", "120"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temp, path)


def read_status() -> dict[str, Any]:
    try:
        if STATUS_PATH.exists():
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"state": "IDLE", "updated_at_utc": None}


def write_status(**values: Any) -> dict[str, Any]:
    status = read_status()
    status.update(values)
    status["updated_at_utc"] = utc_now_iso()
    atomic_json(STATUS_PATH, status)
    return status


def _timestamp_seconds(value: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def repair_stale_runtime() -> dict[str, Any]:
    status = read_status()
    if status.get("state") != "RUNNING":
        if LOCK_PATH.exists():
            try:
                LOCK_PATH.unlink()
            except Exception:
                pass
        return status
    started = _timestamp_seconds(status.get("started_at_utc"))
    hard = int(status.get("hard_timeout_seconds") or DEFAULT_HARD_TIMEOUT)
    if started is not None and time.time() - started > hard + 45:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        return write_status(
            state="TIMEOUT_RECOVERED",
            message="A previous refresh exceeded its hard timeout. The UI remains available on the last-known-good desk.",
            finished_at_utc=utc_now_iso(),
        )
    return status


def load_desk() -> dict[str, Any] | None:
    if not DESK_CACHE.exists():
        return None
    try:
        with DESK_CACHE.open("rb") as file:
            desk = pickle.load(file)
        if not isinstance(desk, dict):
            return None
        meta = dict(desk.get("meta") or {})
        if meta.get("desk_schema_version") != DESK_SCHEMA_VERSION:
            return None
        desk["meta"] = meta
        return desk
    except Exception:
        return None


def save_desk(desk: dict[str, Any]) -> None:
    if not isinstance(desk, dict):
        raise TypeError("desk must be a dictionary")
    desk = dict(desk)
    meta = dict(desk.get("meta") or {})
    meta["desk_schema_version"] = DESK_SCHEMA_VERSION
    meta["desk_saved_at_utc"] = utc_now_iso()
    desk["meta"] = meta
    temp = DESK_CACHE.with_suffix(".pkl.tmp")
    with temp.open("wb") as file:
        pickle.dump(desk, file, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temp, DESK_CACHE)


def cache_age_seconds() -> float | None:
    try:
        return max(0.0, time.time() - DESK_CACHE.stat().st_mtime)
    except Exception:
        return None


def is_running() -> bool:
    return repair_stale_runtime().get("state") == "RUNNING"


def launch_refresh(markets: list[str], force: bool = False, scope: str = "fast") -> tuple[bool, str]:
    """Launch a detached supervisor. Returns immediately and never waits for providers."""
    repair_stale_runtime()
    if is_running() or LOCK_PATH.exists():
        return False, "Refresh already running"
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"created={utc_now_iso()}\n".encode("utf-8"))
        os.close(fd)
    except FileExistsError:
        return False, "Refresh already running"

    hard_timeout = int(os.environ.get("WARROOM_REFRESH_HARD_TIMEOUT", "120" if scope == "fast" else "240"))
    command = [
        sys.executable,
        str(HERE / "refresh_desk_supervisor.py"),
        "--markets",
        ",".join(markets),
        "--scope",
        scope,
        "--hard-timeout",
        str(hard_timeout),
    ]
    if force:
        command.append("--force")

    env = os.environ.copy()
    env.setdefault("WARROOM_REQUEST_TIMEOUT", "5")
    env.setdefault("WARROOM_YFINANCE_TIMEOUT", "8")
    env.setdefault("WARROOM_RETRY_TOTAL", "1")
    env.setdefault("WARROOM_FEED_WORKERS", "12")
    env["WARROOM_REFRESH_SCOPE"] = scope

    log_handle = LOG_PATH.open("ab")
    kwargs: dict[str, Any] = {
        "cwd": str(HERE),
        "env": env,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(command, **kwargs)
    except Exception as exc:
        log_handle.close()
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        write_status(state="LAUNCH_FAILED", message=f"{type(exc).__name__}: {exc}")
        return False, f"Launch failed: {exc}"
    finally:
        try:
            log_handle.close()
        except Exception:
            pass

    write_status(
        state="RUNNING",
        message=f"Background {scope} refresh started",
        pid=process.pid,
        scope=scope,
        markets=markets,
        force=force,
        started_at_utc=utc_now_iso(),
        hard_timeout_seconds=hard_timeout,
    )
    return True, f"Background {scope} refresh started"

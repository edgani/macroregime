"""Atomic runtime store with stable revisions and a browser-readable static mirror.

The collector writes complete snapshots to ``runtime/`` and mirrors them to ``static/``.  The
browser polls the static JSON directly, so Streamlit never remounts the dashboard iframe.  A
content revision changes only when user-visible data changes; heartbeat/status updates are kept in
``worker_status.json`` and cannot make the dashboard flicker.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import hashlib
import json
import os
import time

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
STATIC = HERE / "static"
RUNTIME.mkdir(parents=True, exist_ok=True)
STATIC.mkdir(parents=True, exist_ok=True)

SNAPSHOT = RUNTIME / "desk_snapshot.json"
STATUS = RUNTIME / "worker_status.json"
PID = RUNTIME / "worker.pid"
FORCE = RUNTIME / "force_refresh.flag"
START_LOCK = RUNTIME / "worker_start.lock"
INSTANCE_LOCK = RUNTIME / "worker.instance.lock"

STATIC_SNAPSHOT = STATIC / "desk_snapshot.json"
STATIC_STATUS = STATIC / "worker_status.json"

_VOLATILE_RUNTIME_KEYS = {
    "snapshot_written_at", "snapshot_age_seconds", "worker_state", "worker_heartbeat_at",
    "last_attempt_at", "last_success", "last_error", "snapshot_sequence", "content_hash",
    "stability_events", "core_retained_items", "core_retained_last_good",
}
_VOLATILE_META_KEYS = {"generated"}
_VOLATILE_KEYS_GLOBAL = {
    "fetched_at", "checked_at", "generated", "generated_at", "updated_at", "_age_seconds",
    "_cache_age_seconds", "cache_age_seconds", "last_attempt_at",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    payload = json.dumps(obj, default=str, separators=(",", ":"), ensure_ascii=False)
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(payload)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def read_json(path: Path, *, include_age: bool = True) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        if not isinstance(obj, dict):
            return None
        if include_age:
            obj["_file_age_seconds"] = max(0.0, time.time() - path.stat().st_mtime)
        return obj
    except (OSError, ValueError, TypeError):
        return None


def read_snapshot() -> Optional[dict]:
    return read_json(SNAPSHOT)


def read_status() -> Optional[dict]:
    return read_json(STATUS)


def _stable_copy(value: Any, key_hint: str = "") -> Any:
    """Return a deterministic user-visible payload for revision hashing.

    Collector heartbeats, diagnostics and asynchronous status ordering must never create a new
    dashboard revision. Ranked lists keep their order; registries that are semantically sets are
    sorted by stable provider/dataset keys.
    """
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key.startswith("_file_") or key in _VOLATILE_KEYS_GLOBAL or key.endswith("_collected_at"):
                continue
            if key == "runtime":
                # Runtime metadata is published separately in worker_status.json. It must not redraw UI.
                continue
            if key == "meta" and isinstance(item, dict):
                out[key] = {k: _stable_copy(v, k) for k, v in item.items() if k not in _VOLATILE_META_KEYS}
            else:
                out[key] = _stable_copy(item, key)
        return out
    if isinstance(value, list):
        rows = [_stable_copy(v, key_hint) for v in value]
        if key_hint in {"statuses", "sources", "provider_statuses", "required_datasets", "core_datasets"}:
            def sort_key(item: Any) -> str:
                if isinstance(item, dict):
                    return "|".join(str(item.get(k) or "") for k in ("provider", "dataset", "ticker", "state", "endpoint"))
                return json.dumps(item, default=str, sort_keys=True, separators=(",", ":"))
            rows.sort(key=sort_key)
        return rows
    return value


def content_hash(desk: dict) -> str:
    canonical = json.dumps(_stable_copy(desk), default=str, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def write_snapshot(desk: dict, *, force: bool = False) -> dict:
    """Write a complete snapshot only when its meaningful content changes.

    Returns a small result dictionary used by the worker's diagnostics.  The previous snapshot is
    never removed before the replacement is complete.
    """
    desk = dict(desk or {})
    previous = read_json(SNAPSHOT, include_age=False) or {}
    previous_runtime = dict(previous.get("runtime") or {})
    runtime = dict(desk.get("runtime") or {})
    digest = content_hash(desk)
    previous_digest = str(previous_runtime.get("content_hash") or "")
    changed = digest != previous_digest
    previous_sequence = int(previous_runtime.get("snapshot_sequence") or 0)

    if not changed and not force and previous:
        return {"written": False, "changed": False, "revision": previous_sequence, "content_hash": previous_digest}

    runtime.update({
        "snapshot_written_at": now_iso(),
        "architecture": "background-worker/static-json-polling",
        "snapshot_sequence": previous_sequence + 1 if changed else previous_sequence,
        "content_hash": digest,
    })
    desk["runtime"] = runtime
    atomic_write(SNAPSHOT, desk)
    atomic_write(STATIC_SNAPSHOT, desk)
    return {"written": True, "changed": changed, "revision": runtime["snapshot_sequence"], "content_hash": digest}


def write_status(**kwargs) -> dict:
    current = read_json(STATUS, include_age=False) or {}
    current.update(kwargs)
    current["updated_at"] = now_iso()
    current.setdefault("architecture", "background-worker/static-json-polling")
    atomic_write(STATUS, current)
    atomic_write(STATIC_STATUS, current)
    return current


def request_force_refresh() -> None:
    FORCE.write_text(now_iso(), encoding="utf-8")


def force_refresh_requested() -> bool:
    return FORCE.exists()


def consume_force_refresh() -> bool:
    if not FORCE.exists():
        return False
    try:
        FORCE.unlink()
    except OSError:
        return False
    return True


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def worker_alive(max_heartbeat_age: float = 180.0) -> bool:
    """Return true only for a live PID with a recent collector heartbeat.

    An embedded collector shares the Streamlit PID. PID-only checks therefore reported a dead
    collector thread as alive forever. Status freshness closes that failure mode.
    """
    try:
        if not PID.exists() or not pid_alive(int(PID.read_text(encoding="utf-8").strip())):
            return False
        status = read_json(STATUS, include_age=True) or {}
        state = str(status.get("state") or "").upper()
        if state in {"WORKER_FATAL", "START_ERROR", "STOPPED"}:
            return False
        age = float(status.get("_file_age_seconds") or 0.0)
        return age <= max_heartbeat_age
    except (OSError, ValueError, TypeError):
        return False


def claim_worker_instance() -> bool:
    """Atomically claim the collector instance lease. Safe against simultaneous manual starts."""
    for _ in range(2):
        try:
            fd = os.open(str(INSTANCE_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(str(os.getpid()))
            PID.write_text(str(os.getpid()), encoding="utf-8")
            return True
        except FileExistsError:
            try:
                incumbent = int(INSTANCE_LOCK.read_text(encoding="utf-8").strip())
            except Exception:
                incumbent = -1
            if incumbent > 0 and pid_alive(incumbent):
                return False
            try:
                INSTANCE_LOCK.unlink()
            except OSError:
                return False
    return False


def release_worker_instance() -> None:
    try:
        owner = int(INSTANCE_LOCK.read_text(encoding="utf-8").strip()) if INSTANCE_LOCK.exists() else None
    except Exception:
        owner = None
    if owner in {None, os.getpid()}:
        for path in (INSTANCE_LOCK, PID):
            try:
                path.unlink()
            except OSError:
                pass


def acquire_start_lock(stale_after: float = 30.0) -> bool:
    """Prevent multiple Streamlit reruns from spawning duplicate collectors."""
    if START_LOCK.exists():
        try:
            if time.time() - START_LOCK.stat().st_mtime > stale_after:
                START_LOCK.unlink()
            else:
                return False
        except OSError:
            return False
    try:
        fd = os.open(str(START_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()} {now_iso()}")
        return True
    except FileExistsError:
        return False


def release_start_lock() -> None:
    try:
        START_LOCK.unlink()
    except OSError:
        pass

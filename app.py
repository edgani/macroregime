"""War Room OS hosted deployment shell.

The dashboard is embedded once. Hosted deployments perform one bounded inline market bootstrap
before first paint, then keep a singleton collector thread inside the Streamlit process. This avoids
detached-process and nested-multiprocessing failures on managed hosts. Local power users may set
``WARROOM_WORKER_MODE=process`` explicitly.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except Exception:
    pass

import streamlit as st
from runtime_store import (
    STATIC_SNAPSHOT,
    STATIC_STATUS,
    acquire_start_lock,
    read_snapshot,
    read_status,
    release_start_lock,
    worker_alive,
    write_snapshot,
    write_status,
)

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """<style>
    .stApp{background:#050811} header[data-testid="stHeader"]{display:none}
    .block-container{padding:0!important;max-width:100%!important}
    #MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
    iframe{display:block;border:0!important;background:#050811}
    </style>""",
    unsafe_allow_html=True,
)

DASH_SOURCE = HERE / "dashboard.html"
DASH_STATIC = HERE / "static" / "dashboard_live.html"
DASH_RUNTIME = HERE / "runtime" / "dashboard_runtime.html"
WORKER_PATH = HERE / "warroom_data_worker.py"
BOOT_LOG = HERE / "runtime" / "worker_boot.log"


def _boot_snapshot() -> dict:
    status = read_status() or {}
    worker_state = str(status.get("state") or "STARTING")
    return {
        "meta": {
            "source": "INITIALIZING",
            "generated": status.get("updated_at", "—"),
            "note": "Collector is building the first stable snapshot.",
        },
        "runtime": {
            "worker_state": worker_state,
            "architecture": "embedded-worker/static-json-polling",
            "snapshot_sequence": 0,
            "content_hash": "boot",
        },
        "data_health": {"overall": "INITIALIZING", "sources": [], "live_count": 0, "total_count": 0},
        "systemic": {"liquidity": "INITIALIZING", "quad_name": "INITIALIZING"},
        "markets": {},
        "alpha": [],
        "reference": {},
        "macro_observations": {},
        "market_breadth": {},
        "rotation_snapshot": {},
        "institutional": {"overall_state": "INITIALIZING", "statuses": [], "events": []},
        "live_intelligence": {
            "overall_state": "INITIALIZING",
            "statuses": [],
            "events": [],
            "crypto_derivatives": [],
            "crypto_options": [],
            "us_options": [],
            "us_squeeze": [],
        },
        "full_live_data": {"overall_state": "INITIALIZING", "statuses": [], "tab_coverage": {}},
    }


def _json_revision(path: Path) -> int:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return int(((obj.get("runtime") or {}).get("snapshot_sequence") or 0))
    except Exception:
        return -1


def _prepare_static() -> None:
    DASH_STATIC.parent.mkdir(parents=True, exist_ok=True)
    if not DASH_STATIC.exists() or DASH_STATIC.stat().st_mtime < DASH_SOURCE.stat().st_mtime:
        shutil.copy2(DASH_SOURCE, DASH_STATIC)

    runtime_snapshot = read_snapshot()
    if runtime_snapshot is not None and (
        not STATIC_SNAPSHOT.exists() or _json_revision(STATIC_SNAPSHOT) < int(((runtime_snapshot.get("runtime") or {}).get("snapshot_sequence") or 0))
    ):
        STATIC_SNAPSHOT.write_text(json.dumps(runtime_snapshot, default=str, separators=(",", ":")), encoding="utf-8")
    elif not STATIC_SNAPSHOT.exists():
        STATIC_SNAPSHOT.write_text(json.dumps(_boot_snapshot(), default=str, separators=(",", ":")), encoding="utf-8")

    if not STATIC_STATUS.exists():
        STATIC_STATUS.write_text(json.dumps(read_status() or {"state": "STARTING"}), encoding="utf-8")


def _prepare_runtime_dashboard() -> Path:
    """Embed the already-committed snapshot into first paint, then keep static JSON polling live."""
    if not DASH_SOURCE.exists():
        return DASH_SOURCE
    snapshot = read_snapshot() or _boot_snapshot()
    payload = json.dumps(snapshot, default=str, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    html = DASH_SOURCE.read_text(encoding="utf-8")
    seed = f"<script>window.DASHBOARD_DATA={payload};</script>"
    if "<body>" in html:
        html = html.replace("<body>", "<body>" + seed, 1)
    else:
        html = seed + html
    DASH_RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    tmp = DASH_RUNTIME.with_name(f"{DASH_RUNTIME.name}.{os.getpid()}.tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, DASH_RUNTIME)
    return DASH_RUNTIME


def _start_process_worker() -> dict:
    """Start the standalone worker and preserve its stderr for deployment diagnostics."""
    if worker_alive():
        return {"mode": "existing", "started": True}
    if not acquire_start_lock():
        for _ in range(30):
            if worker_alive():
                return {"mode": "existing", "started": True}
            time.sleep(0.1)
        return {"mode": "process", "started": False, "error": "worker start lock held without a live worker"}
    try:
        BOOT_LOG.parent.mkdir(parents=True, exist_ok=True)
        flags = 0
        kwargs: dict = {}
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            kwargs["start_new_session"] = True
        with open(BOOT_LOG, "a", encoding="utf-8", buffering=1) as log_handle:
            subprocess.Popen(
                [sys.executable, str(WORKER_PATH)],
                cwd=str(HERE),
                stdout=log_handle,
                stderr=log_handle,
                creationflags=flags,
                **kwargs,
            )
        for _ in range(50):
            status = read_status() or {}
            state = str(status.get("state") or "")
            if worker_alive() and state not in {"", "STARTING"}:
                return {"mode": "process", "started": True, "state": state}
            if state in {"WORKER_FATAL", "START_ERROR"}:
                return {"mode": "process", "started": False, "error": status.get("error")}
            time.sleep(0.1)
        return {"mode": "process", "started": worker_alive(), "state": (read_status() or {}).get("state")}
    except Exception as exc:
        write_status(state="START_ERROR", error=f"{type(exc).__name__}: {exc}", pending=[])
        return {"mode": "process", "started": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        release_start_lock()


def _embedded_runner() -> None:
    try:
        # Managed Streamlit hosts are often single-process sandboxes. Avoid nested process creation
        # and use bounded direct HTTP market fetches instead of yfinance cookie/crumb startup.
        os.environ.setdefault("WARROOM_HOSTED_MODE", "1")
        os.environ.setdefault("WARROOM_PRICE_BACKEND", "http")
        os.environ.setdefault("WARROOM_ENABLE_YFINANCE_FALLBACK", "0")
        os.environ.setdefault("WARROOM_INPROCESS_COLLECTORS", "1")
        # Embedded fallback avoids multiprocessing spawn quirks under Streamlit ScriptRunner;
        # collector child processes provide the only reliable hard timeout for DNS/library hangs.
        from warroom_data_worker import loop
        loop()
    except BaseException as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:]
        BOOT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(BOOT_LOG, "a", encoding="utf-8") as fh:
            fh.write("\nEMBEDDED WORKER FATAL\n" + detail + "\n")
        try:
            write_status(state="WORKER_FATAL", error=f"{type(exc).__name__}: {exc}", pending=[])
        except Exception:
            pass


@st.cache_resource(show_spinner=False)
def _start_embedded_worker() -> dict:
    if worker_alive():
        return {"mode": "existing", "started": True, "thread": None}
    thread = threading.Thread(target=_embedded_runner, name="warroom-collector", daemon=True)
    thread.start()
    for _ in range(40):
        status = read_status() or {}
        state = str(status.get("state") or "")
        if state not in {"", "STARTING"}:
            return {"mode": "embedded", "started": thread.is_alive(), "state": state, "thread": thread}
        if not thread.is_alive():
            break
        time.sleep(0.1)
    return {
        "mode": "embedded",
        "started": thread.is_alive(),
        "state": (read_status() or {}).get("state"),
        "thread": thread,
    }


def _ensure_worker() -> dict:
    if os.getenv("WARROOM_DISABLE_AUTOSTART", "0").strip().lower() in {"1", "true", "yes"}:
        return {"mode": "disabled", "started": False}
    # Deterministic hosted defaults are inherited by a standalone worker process.
    os.environ.setdefault("WARROOM_HOSTED_MODE", "1")
    os.environ.setdefault("WARROOM_PRICE_BACKEND", "http")
    os.environ.setdefault("WARROOM_ENABLE_YFINANCE_FALLBACK", "0")
    os.environ.setdefault("WARROOM_PRICE_HTTP_TIMEOUT", "3")
    os.environ.setdefault("WARROOM_BOOTSTRAP_HARD_TIMEOUT", "22")
    os.environ.setdefault("WARROOM_FAST_CORE_HARD_TIMEOUT", "55")
    os.environ.setdefault("WARROOM_FAST_CORE_PRICE_FIRST", "1")
    os.environ.setdefault("WARROOM_POST_BOOTSTRAP_CORE_DELAY", "90")
    os.environ.setdefault("WARROOM_CONTEXT_HARD_TIMEOUT", "90")
    os.environ.setdefault("WARROOM_FAST_US_NAMES", "12")
    os.environ.setdefault("WARROOM_FAST_IDX_NAMES", "8")
    os.environ.setdefault("WARROOM_FAST_CRYPTO_NAMES", "10")
    os.environ.setdefault("WARROOM_PRICE_HTTP_WORKERS", "10")
    os.environ.setdefault("WARROOM_MP_START_METHOD", "spawn")
    os.environ.setdefault("WARROOM_ALLOW_INPROCESS_FALLBACK", "0")
    requested = os.getenv("WARROOM_WORKER_MODE", "embedded").strip().lower()
    if requested == "process":
        result = _start_process_worker()
        if result.get("started"):
            return result
        # Automatic recovery for managed hosts where detached processes are unavailable.
        fallback = _start_embedded_worker()
        fallback["process_error"] = result.get("error")
        return fallback
    return _start_embedded_worker()


def _snapshot_has_terminal_boot_state(snapshot: dict | None = None) -> bool:
    snapshot = snapshot or read_snapshot() or {}
    runtime = snapshot.get("runtime") or {}
    revision = int(runtime.get("snapshot_sequence") or 0)
    health = str((snapshot.get("data_health") or {}).get("overall") or "").upper()
    source = str((snapshot.get("meta") or {}).get("source") or "").upper()
    return revision >= 2 and health not in {"", "INITIALIZING"} and source != "INITIALIZING"


def _inline_bootstrap_runner(box: dict) -> None:
    try:
        # The bootstrap universe is intentionally tiny and every public request has an explicit
        # connect/read timeout. No detached process or nested multiprocessing is required here.
        os.environ.setdefault("WARROOM_HOSTED_MODE", "1")
        os.environ.setdefault("WARROOM_PRICE_BACKEND", "http")
        os.environ.setdefault("WARROOM_ENABLE_YFINANCE_FALLBACK", "0")
        from warroom_data_worker import bootstrap_snapshot_once
        box["result"] = bootstrap_snapshot_once(direct=True, commit=False)
    except BaseException as exc:
        box["error"] = f"{type(exc).__name__}: {exc}"


def _ensure_initial_snapshot() -> dict:
    """Guarantee R2 before the iframe is mounted.

    Previous releases rendered R1 immediately and trusted a detached worker to replace it. On some
    managed hosts that worker never got CPU/process permission, leaving the browser permanently on
    INITIALIZING. v2.9 keeps first paint deterministic: either a small real-data bootstrap commits,
    or an explicit NO_DATA/error snapshot commits. Background planes are enrichment, not startup.
    """
    current = read_snapshot() or {}
    if _snapshot_has_terminal_boot_state(current):
        return {"state": "existing", "revision": int(((current.get("runtime") or {}).get("snapshot_sequence") or 0))}
    box: dict = {}
    thread = threading.Thread(target=_inline_bootstrap_runner, args=(box,), name="warroom-inline-bootstrap", daemon=True)
    thread.start()
    timeout = float(os.getenv("WARROOM_INLINE_BOOTSTRAP_SECONDS", "18"))
    thread.join(max(3.0, timeout))
    collected = dict(box.get("result") or {})
    if collected.get("snapshot") and not thread.is_alive():
        snapshot = collected.pop("snapshot")
        commit_result = write_snapshot(snapshot, force=True)
        state = "BOOTSTRAP_READY" if collected.get("observations") else "BOOTSTRAP_NO_DATA"
        write_status(
            state=state, pid=os.getpid(), pending=[], error=collected.get("error"),
            snapshot_revision=commit_result.get("revision"), last_success=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        collected.update({"state": "ready", "revision": commit_result.get("revision")})
        return collected

    current = read_snapshot() or {}
    if _snapshot_has_terminal_boot_state(current):
        collected.setdefault("state", "ready")
        return collected

    # The fetch thread is daemonized and may still finish later, but it has commit=False and cannot
    # overwrite the timeout snapshot or a newer background-worker revision after this point.
    status = read_status() or {}
    error = str(box.get("error") or status.get("error") or f"inline bootstrap exceeded {timeout:.0f}s")
    desk = _boot_snapshot()
    desk["meta"] = {"source": "NO_DATA", "generated": status.get("updated_at", "—"), "note": error}
    desk["runtime"].update({"worker_state": "BOOTSTRAP_TIMEOUT", "startup_error": error})
    desk["data_health"].update({"overall": "NO_DATA", "startup_error": error})
    desk["systemic"] = {"liquidity": "PENDING_BACKGROUND_CONTEXT", "quad_name": "NO_DATA"}
    desk["markets"] = {
        name: {"data_state": "NO_DATA", "funnel": {"universe": 0}, "setups": [], "note": error}
        for name in ("us", "idx", "crypto", "commodity", "fx")
    }
    result = write_snapshot(desk, force=True)
    write_status(state="BOOTSTRAP_TIMEOUT", error=error, pending=[], snapshot_revision=result.get("revision"))
    return {"state": "timeout", "revision": result.get("revision"), "error": error}


def _startup_watchdog_runner() -> None:
    """Never leave the browser on bootstrap R1 when the collector cannot commit a snapshot."""
    deadline = time.time() + float(os.getenv("WARROOM_STARTUP_WATCHDOG_SECONDS", "35"))
    while time.time() < deadline:
        snap = read_snapshot() or {}
        revision = int(((snap.get("runtime") or {}).get("snapshot_sequence") or 0))
        if revision > 1:
            return
        time.sleep(1.0)
    snap = read_snapshot() or {}
    revision = int(((snap.get("runtime") or {}).get("snapshot_sequence") or 0))
    if revision > 1:
        return
    status = read_status() or {}
    error = str(status.get("error") or f"collector did not commit within {int(float(os.getenv('WARROOM_STARTUP_WATCHDOG_SECONDS', '35')))}s")
    desk = _boot_snapshot()
    desk["meta"] = {"source": "NO_DATA", "generated": status.get("updated_at", "—"), "note": error}
    desk["runtime"].update({"worker_state": "STARTUP_TIMEOUT", "startup_error": error})
    desk["data_health"].update({"overall": "NO_DATA", "startup_error": error})
    desk["systemic"] = {"liquidity": "NO_DATA", "quad_name": "NO_DATA"}
    desk["markets"] = {
        name: {"data_state": "NO_DATA", "funnel": {"universe": 0}, "setups": [], "note": error}
        for name in ("us", "idx", "crypto", "commodity", "fx")
    }
    write_snapshot(desk, force=True)
    write_status(state="STARTUP_TIMEOUT", error=error, pending=[])


@st.cache_resource(show_spinner=False)
def _start_startup_watchdog() -> threading.Thread:
    thread = threading.Thread(target=_startup_watchdog_runner, name="warroom-startup-watchdog", daemon=True)
    thread.start()
    return thread


_prepare_static()
INITIAL_BOOTSTRAP = _ensure_initial_snapshot()
DASH_RENDER_SOURCE = _prepare_runtime_dashboard()
SUPERVISOR = _ensure_worker()
STARTUP_WATCHDOG = _start_startup_watchdog()


def _render_dashboard() -> None:
    source = DASH_RENDER_SOURCE if DASH_RENDER_SOURCE.exists() else DASH_SOURCE
    if not source.exists():
        st.error(f"Dashboard document is missing: {source}")
        return
    try:
        if hasattr(st, "iframe"):
            st.iframe(source, width="stretch", height=1160, tab_index=0)
            return
    except Exception as exc:
        fallback_error = exc
    else:
        fallback_error = None

    try:
        import streamlit.components.v1 as components
        components.html(source.read_text(encoding="utf-8"), height=1160, scrolling=False)
    except Exception as exc:
        detail = f"Primary iframe error: {fallback_error!r}; fallback error: {exc!r}"
        st.error("War Room dashboard could not be embedded.")
        st.code(detail)


status_now = read_status() or {}
if str(status_now.get("state") or "").upper() in {"WORKER_FATAL", "START_ERROR"}:
    st.error(f"War Room collector failed: {status_now.get('error') or 'unknown error'}. Check runtime/worker_boot.log.")

_render_dashboard()

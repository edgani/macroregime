"""Shared V10.1 operational-desk embedding for the streamlit entry points.

Both app.py (War Room 6 UI) and app_v101.py (desk-only shell) render the same
dashboard.html against the same runtime desk snapshot, so fixes to the desk
pipeline (quotes, macro, carry, thesis lifecycle) show up identically in both.
The embedded data worker is protected by runtime_store.claim_worker_instance,
so spawning it from two streamlit processes is safe (second one exits).
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run import build_desk  # noqa: E402
from runtime_store import read_snapshot, write_snapshot, write_status  # noqa: E402
from warroom.no_technical_policy import (  # noqa: E402
    assert_registry_has_no_active_technical_components,
    enforce_payload,
)

DASHBOARD = HERE / "dashboard.html"
CMV3_IMAGES = HERE / "assets" / "crashmeter_v3" / "backtests_b64.json"
MARKETS = ["us", "idx", "crypto", "commodity", "fx"]

_worker_lock = threading.Lock()
_worker_thread: threading.Thread | None = None


def empty_data() -> dict:
    return {
        "markets": MARKETS, "fred": {}, "fred_source": "NO_DATA", "feeds": {"_status": {}},
        "quotes": {"markets": {m: {} for m in MARKETS}},
        "public_sources": {"markets": {m: {"state": "ROUTE_ONLY", "items": [], "valid_items": 0} for m in MARKETS}, "markets_with_real_snapshot": 0},
        "universe_summary": {}, "sources": {}, "overall_source": "INITIALIZING",
    }


def seed_snapshot() -> dict:
    registry = json.loads((HERE / "component_registry_v99.json").read_text(encoding="utf-8"))
    assert_registry_has_no_active_technical_components(registry)
    import data_layer_v101 as DL
    snapshot = build_desk(DL.load_all(markets=MARKETS, allow_live=False, allow_synthetic=False))
    enforce_payload(snapshot)
    return snapshot


def _worker() -> None:
    try:
        from warroom_data_worker_v101 import loop
        loop()
    except BaseException as exc:
        write_status(state="WORKER_FATAL", error=f"{type(exc).__name__}: {exc}", capital_permission="PROOF_GATED")


def start_worker_once() -> threading.Thread | None:
    global _worker_thread
    if os.getenv("WARROOM_DISABLE_AUTOSTART", "0").lower() in {"1", "true", "yes"}:
        return None
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return _worker_thread
        thread = threading.Thread(target=_worker, name="warroom-v101-data-worker", daemon=True)
        thread.start()
        _worker_thread = thread
        return thread


def current_snapshot() -> dict:
    if read_snapshot() is None:
        write_snapshot(seed_snapshot(), force=True)
    snapshot = read_snapshot() or seed_snapshot()
    enforce_payload(snapshot)
    return snapshot


def desk_html(snapshot: dict) -> str:
    payload = json.dumps(snapshot, default=str, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    html = DASHBOARD.read_text(encoding="utf-8").replace("/*__INJECT_DATA__*/", f"window.DASHBOARD_DATA={payload};", 1)
    images = "[]"
    try:
        images = CMV3_IMAGES.read_text(encoding="utf-8")
    except OSError:
        pass
    return html.replace("/*__INJECT_CMV3_IMG__*/", f"window.CMV3_IMG={images};", 1)


def render_desk(height: int = 1320) -> None:
    """Streamlit entry: seed snapshot if needed, start worker, render desk."""
    import streamlit.components.v1 as components
    start_worker_once()
    components.html(desk_html(current_snapshot()), height=height, scrolling=True)

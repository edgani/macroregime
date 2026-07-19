"""War Room OS stable shell.

The dashboard iframe is mounted once.  It polls ``static/desk_snapshot.json`` directly and updates
only when the worker publishes a new content revision.  There is no ``st.fragment``/autorefresh
loop, so the whole iframe cannot blink every few seconds.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
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
    STATIC_SNAPSHOT, STATIC_STATUS, acquire_start_lock, read_snapshot, read_status,
    release_start_lock, worker_alive,
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
WORKER_PATH = HERE / "warroom_data_worker.py"


def _boot_snapshot() -> dict:
    status = read_status() or {}
    return {
        "meta": {"source": "INITIALIZING", "generated": status.get("updated_at", "—"),
                 "note": "Background collector is building the first stable snapshot."},
        "runtime": {"worker_state": status.get("state", "STARTING"),
                    "architecture": "background-worker/static-json-polling",
                    "snapshot_sequence": 0, "content_hash": "boot"},
        "data_health": {"overall": "INITIALIZING", "sources": [], "live_count": 0, "total_count": 0},
        "systemic": {"liquidity": "INITIALIZING", "quad_name": "INITIALIZING"},
        "markets": {}, "alpha": [], "reference": {}, "macro_observations": {},
        "market_breadth": {}, "rotation_snapshot": {},
        "institutional": {"overall_state": "INITIALIZING", "statuses": [], "events": []},
        "live_intelligence": {"overall_state": "INITIALIZING", "statuses": [], "events": [],
                              "crypto_derivatives": [], "crypto_options": [], "us_options": [],
                              "us_squeeze": []},
        "full_live_data": {"overall_state": "INITIALIZING", "statuses": [], "tab_coverage": {}},
    }


def _prepare_static() -> None:
    DASH_STATIC.parent.mkdir(parents=True, exist_ok=True)
    if not DASH_STATIC.exists() or DASH_STATIC.stat().st_mtime < DASH_SOURCE.stat().st_mtime:
        shutil.copy2(DASH_SOURCE, DASH_STATIC)
    if not STATIC_SNAPSHOT.exists():
        source = read_snapshot() or _boot_snapshot()
        STATIC_SNAPSHOT.write_text(json.dumps(source, default=str, separators=(",", ":")), encoding="utf-8")
    if not STATIC_STATUS.exists():
        STATIC_STATUS.write_text(json.dumps(read_status() or {"state": "STARTING"}), encoding="utf-8")


def _start_worker() -> bool:
    if worker_alive():
        return True
    if not acquire_start_lock():
        # Another Streamlit session/rerun is already spawning it.
        for _ in range(20):
            if worker_alive():
                return True
            time.sleep(0.1)
        return worker_alive()
    try:
        flags = 0
        kwargs = {}
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(
            [sys.executable, str(WORKER_PATH)], cwd=str(HERE),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags, **kwargs,
        )
        for _ in range(30):
            if worker_alive():
                return True
            time.sleep(0.1)
        return worker_alive()
    except Exception:
        return False
    finally:
        release_start_lock()


_prepare_static()
if os.getenv("WARROOM_DISABLE_AUTOSTART", "0").strip().lower() not in {"1", "true", "yes"}:
    _start_worker()

# IMPORTANT: embed the local HTML file, not the static URL.
#
# Streamlit >=1.56 treats a string that does not start with ``/`` as raw HTML. The old value
# ``app/static/dashboard_live.html`` was therefore rendered as visible text. Adding ``/`` alone
# is not sufficient because Streamlit serves .html files from ``static/`` as text/plain. Passing
# a local Path makes Streamlit read and embed the document as HTML, while the document polls JSON
# from Streamlit's supported static-file endpoint.
def _render_dashboard() -> None:
    if not DASH_SOURCE.exists():
        st.error(f"Dashboard document is missing: {DASH_SOURCE}")
        return
    try:
        if hasattr(st, "iframe"):
            st.iframe(DASH_SOURCE, width="stretch", height=1160, tab_index=0)
            return
    except Exception as exc:
        # A compatibility fallback is useful on hosting images with a partially upgraded
        # Streamlit package. The HTML still uses the same-origin static JSON endpoints.
        fallback_error = exc
    else:
        fallback_error = None

    try:
        import streamlit.components.v1 as components
        components.html(DASH_SOURCE.read_text(encoding="utf-8"), height=1160, scrolling=False)
    except Exception as exc:
        detail = f"Primary iframe error: {fallback_error!r}; fallback error: {exc!r}"
        st.error("War Room dashboard could not be embedded.")
        st.code(detail)


_render_dashboard()

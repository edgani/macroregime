"""War Room OS — fast snapshot UI.

Network I/O is owned by ``warroom_data_worker.py``. Streamlit only reads an atomic local snapshot,
so tab changes and reruns are no longer blocked by Yahoo/FRED/options/filing provider latency.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except Exception:
    pass

import streamlit as st
import streamlit.components.v1 as components
from runtime_store import read_snapshot, read_status, request_force_refresh, worker_alive

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp{background:#050811} header[data-testid="stHeader"]{background:transparent}
.block-container{padding:0 !important;max-width:100% !important} #MainMenu,footer{visibility:hidden}
section[data-testid="stSidebar"]{width:310px !important}
</style>""", unsafe_allow_html=True)

DASH_PATH = HERE / "dashboard.html"
WORKER_PATH = HERE / "warroom_data_worker.py"


def _inject(desk: dict) -> str:
    html = DASH_PATH.read_text(encoding="utf-8")
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk, default=str, separators=(",", ":")) + ";"
    return html.replace("/*__INJECT_DATA__*/", payload) if "/*__INJECT_DATA__*/" in html else html.replace("<body>", "<body><script>" + payload + "</script>", 1)


def _start_worker() -> bool:
    if worker_alive():
        return True
    try:
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen([sys.executable, str(WORKER_PATH)], cwd=str(HERE),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags, start_new_session=(os.name != "nt"))
        return True
    except Exception:
        return False


def _boot_desk(status: dict | None = None) -> dict:
    status = status or {}
    return {
        "meta": {"source": "INITIALIZING", "generated": status.get("updated_at", "—"),
                 "note": "Background collector is building the first local snapshot."},
        "runtime": {"worker_state": status.get("state", "STARTING"), "architecture": "background-worker/local-snapshot"},
        "data_health": {"overall": "INITIALIZING", "sources": [], "live_count": 0, "total_count": 0},
        "systemic": {"liquidity": "INITIALIZING", "quad_name": "INITIALIZING"},
        "markets": {}, "alpha": [], "reference": {}, "macro_observations": {}, "market_breadth": {}, "rotation_snapshot": {},
        "institutional": {"overall_state": "INITIALIZING", "statuses": [], "events": []},
        "live_intelligence": {"overall_state": "INITIALIZING", "statuses": [], "events": [], "crypto_derivatives": [], "crypto_options": [], "us_options": [], "us_squeeze": []},
        "full_live_data": {"overall_state": "INITIALIZING", "statuses": [], "tab_coverage": {}},
    }


def _provider_config():
    return [
        ("FRED official API", bool(os.getenv("FRED_API_KEY", "").strip()), "FRED_API_KEY", "optional but recommended"),
        ("SEC EDGAR", bool(os.getenv("WARROOM_SEC_USER_AGENT", "").strip()), "WARROOM_SEC_USER_AGENT", "public; contact identity required"),
        ("Unusual Whales", bool(os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()), "UNUSUAL_WHALES_API_KEY", "licensed enrichment"),
        ("Massive", bool(os.getenv("MASSIVE_API_KEY", "").strip()), "MASSIVE_API_KEY", "licensed options/TRF"),
        ("ORTEX / Intrinio", bool(os.getenv("ORTEX_API_KEY", "").strip() or os.getenv("INTRINIO_API_KEY", "").strip()), "ORTEX_API_KEY / INTRINIO_API_KEY", "licensed borrow/SI"),
        ("Nansen / Arkham", bool(os.getenv("NANSEN_API_KEY", "").strip() or os.getenv("ARKHAM_API_KEY", "").strip()), "NANSEN_API_KEY / ARKHAM_API_KEY", "licensed crypto entities"),
        ("Databento bridge", bool(os.getenv("DATABENTO_STREAM_BRIDGE_URL", "").strip()), "DATABENTO_STREAM_BRIDGE_URL", "licensed intraday futures OI"),
        ("IDX licensed bridge", bool(os.getenv("IDX_DATA_BRIDGE_URL", "").strip()), "IDX_DATA_BRIDGE_URL", "licensed broker/foreign/orderbook"),
        ("Binance / Bybit / OKX / Deribit", True, "PUBLIC ENDPOINTS", "public derivatives snapshots"),
        ("CFTC / Treasury / NY Fed / SEC", True, "PUBLIC ENDPOINTS", "official public, release cadence applies"),
    ]

_start_worker()

with st.sidebar:
    st.markdown("### War Room OS")
    st.caption("Fast local-snapshot architecture")
    refresh_seconds = st.select_slider("UI snapshot refresh", options=[3, 5, 10, 15, 30], value=5)
    if st.button("↻ Request data refresh", use_container_width=True):
        request_force_refresh(); st.toast("Background refresh requested")
    ws = read_status() or {}
    st.caption(f"Worker: **{ws.get('state','STARTING')}** · {ws.get('updated_at','—')}")
    snap = read_snapshot() or {}
    age = snap.get("_file_age_seconds")
    st.caption(f"Local snapshot age: **{int(age)}s**" if isinstance(age, (int,float)) else "Local snapshot: building")
    st.divider()
    st.markdown("**Provider activation**")
    for name, configured, env_name, note in _provider_config():
        st.caption(f"{'🟢' if configured else '⚪'} {name} · `{env_name}` · {note}")
    st.divider()
    st.caption("NO_SIGNAL means data loaded but no candidate passed. ACTION_REQUIRED means a public feed needs configuration. NOT_ENTITLED means a licensed feed is absent. NO_DATA means the core source itself produced no usable records.")


def _render():
    desk = read_snapshot()
    if not desk:
        _start_worker()
        desk = _boot_desk(read_status())
    runtime = dict(desk.get("runtime") or {})
    file_age = desk.pop("_file_age_seconds", None)
    runtime["snapshot_age_seconds"] = file_age
    desk["runtime"] = runtime
    meta = desk.get("meta") or {}
    health = desk.get("data_health") or {}
    st.caption(f"Snapshot source: {meta.get('source','INITIALIZING')} · health: {health.get('overall','INITIALIZING')} · worker: {runtime.get('worker_state','STARTING')} · snapshot age: {int(file_age)}s" if isinstance(file_age,(int,float)) else "Building first snapshot in background…")
    components.html(_inject(desk), height=1160, scrolling=False)

@st.fragment(run_every=f"{refresh_seconds}s")
def _fragment():
    _render()

_fragment()

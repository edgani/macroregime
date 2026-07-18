"""War Room OS v7 — non-blocking resilient dashboard.

The UI renders immediately from the latest verified desk (or an explicit no-data desk). Provider and
engine refreshes run in a supervised background process with a hard timeout. A slow or unavailable
provider can therefore never trap the Streamlit page behind an endless spinner.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = Path(__file__).resolve().parent

import streamlit as st
import streamlit.components.v1 as components

from alpha_foundry_adapter import load_alpha_foundry_state, minimal_desk
from data.resilient_market_data import read_health
from desk_runtime import (
    DESK_SCHEMA_VERSION,
    cache_age_seconds,
    is_running,
    launch_refresh,
    load_desk,
    read_status,
    repair_stale_runtime,
)

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
  .stApp{background:#0a0d12}
  header[data-testid="stHeader"]{background:transparent}
  .block-container{padding:0 !important;max-width:100% !important}
  #MainMenu,footer{visibility:hidden}
  section[data-testid="stSidebar"]{width:270px !important}
</style>""", unsafe_allow_html=True)

DASH_PATH = HERE / "dashboard.html"
DEFAULT_MARKETS = ["us", "idx", "crypto", "commodity", "fx"]


def inject(desk: dict) -> str:
    html = DASH_PATH.read_text(encoding="utf-8")
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk, default=str) + ";"
    if "/*__INJECT_DATA__*/" in html:
        return html.replace("/*__INJECT_DATA__*/", payload)
    return html.replace("<body>", "<body>\n<script>" + payload + "</script>", 1)


def status_age_minutes(status: dict) -> float | None:
    from datetime import datetime, timezone
    try:
        value = str(status.get("updated_at_utc") or "").replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0)
    except Exception:
        return None


repair_stale_runtime()

with st.sidebar:
    st.markdown("**War Room OS · NON-BLOCKING FEEDS**")
    markets = st.multiselect("Markets", DEFAULT_MARKETS, default=DEFAULT_MARKETS)
    auto_refresh = st.checkbox("Auto-refresh in background", value=True)
    refresh_minutes = st.select_slider("Full refresh interval", options=[5, 10, 15, 30, 60], value=15)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Fast refresh", use_container_width=True):
            ok, message = launch_refresh(markets or DEFAULT_MARKETS, force=True, scope="fast")
            (st.success if ok else st.info)(message)
            st.rerun()
    with c2:
        if st.button("Full refresh", use_container_width=True):
            ok, message = launch_refresh(markets or DEFAULT_MARKETS, force=True, scope="full")
            (st.success if ok else st.info)(message)
            st.rerun()

    st.caption(
        "Dashboard renders first. Providers and engines refresh in a supervised child process. "
        "Fast refresh seeds a representative desk; full refresh expands the configured universe."
    )

    status = read_status()
    st.markdown("**Refresh status**")
    st.caption(f"{status.get('state','IDLE')} · {status.get('message','No refresh recorded')}")
    if status.get("scope"):
        st.caption(f"scope={status.get('scope')} · timeout={status.get('hard_timeout_seconds','?')}s")
    if (HERE / ".cache" / "refresh_v7.log").exists():
        with st.expander("Background log tail", expanded=False):
            try:
                text = (HERE / ".cache" / "refresh_v7.log").read_text(encoding="utf-8", errors="replace")
                st.code(text[-5000:])
            except Exception as exc:
                st.caption(str(exc))

    health = read_health()
    if health.get("markets"):
        with st.expander("Feed health", expanded=False):
            for market, info in health["markets"].items():
                st.caption(
                    f"{market}: {info.get('status')} · live {info.get('live',0)} · "
                    f"fresh cache {info.get('cache_fresh',0)} · stale {info.get('cache_stale',0)} · "
                    f"missing {info.get('missing',0)}"
                )

    st.divider()
    st.markdown("**US Alpha Foundry**")
    foundry = load_alpha_foundry_state()
    counts = foundry.get("counts", {})
    st.caption(
        f"{foundry.get('status')} · shortlist {counts.get('shortlist',0)} · "
        f"trials {counts.get('registered_trials',0)}"
    )
    with st.expander("Run free-data research pipeline", expanded=False):
        sec_contact = st.text_input("SEC contact email", value=os.environ.get("SEC_CONTACT_EMAIL", ""))
        if st.button("Run Alpha Foundry Quick"):
            if "@" not in sec_contact:
                st.error("Masukkan email kontak valid untuk SEC fair-access policy.")
            else:
                env = os.environ.copy()
                env["SEC_USER_AGENT"] = f"Edward Gani {sec_contact}"
                log = (HERE / ".cache" / "alpha_foundry.log").open("ab")
                kwargs = dict(
                    cwd=str(HERE / "alpha_foundry"), env=env, stdout=log,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, close_fds=True,
                )
                if os.name == "nt":
                    kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                else:
                    kwargs["start_new_session"] = True
                subprocess.Popen([sys.executable, "run_pipeline.py", "--mode", "quick"], **kwargs)
                log.close()
                st.success("Alpha Foundry started in background. Dashboard tetap bisa dipakai.")

# Read the current desk immediately. No network call occurs in the Streamlit request path.
desk = load_desk()
status = read_status()
running = is_running()
cache_age = cache_age_seconds()

# First run: render now and start a fast seed in the background.
if desk is None and not running:
    launch_refresh(markets or DEFAULT_MARKETS, force=False, scope="fast")
    status = read_status()
    running = True

# Scheduled full refresh. It never blocks this page render.
if desk is not None and auto_refresh and not running:
    due_seconds = int(refresh_minutes) * 60
    if cache_age is None or cache_age >= due_seconds:
        launch_refresh(markets or DEFAULT_MARKETS, force=False, scope="full")
        status = read_status()
        running = True

if desk is None:
    desk = minimal_desk(
        "Initial provider seed is running in the background. The interface remains usable; "
        "real panels will replace this state after the first successful cache write."
    )
    desk.setdefault("meta", {})
    desk["meta"].update({
        "desk_schema_version": DESK_SCHEMA_VERSION,
        "source": "BACKGROUND_INITIALIZING",
        "data_mode": "NO_VERIFIED_CACHE_YET",
        "trading_permission": "RESEARCH_ONLY_PAPER_AND_LIVE_BLOCKED",
    })

# Visible refresh state without a blocking Streamlit spinner.
state = str(status.get("state") or "IDLE")
message = str(status.get("message") or "")
if state == "RUNNING":
    st.info(f"Background refresh berjalan: {message}. Dashboard di bawah tetap aktif.")
elif state == "SUCCESS":
    st.success(message or "Background refresh completed")
elif state in {"FAILED", "TIMEOUT", "TIMEOUT_RECOVERED", "LAUNCH_FAILED"}:
    st.warning(f"{state}: {message}. Last-known-good desk tetap dipakai.")

html = inject(desk)
components.html(html, height=1350, scrolling=True)

# Poll only while a worker is active. Otherwise use the selected normal refresh interval.
reload_seconds = 4 if running else max(60, int(refresh_minutes) * 60)
components.html(
    f"""<script>setTimeout(()=>window.parent.location.reload(), {reload_seconds * 1000});</script>""",
    height=0,
)

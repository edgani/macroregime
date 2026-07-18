"""War Room OS — Capital Intelligence Map.

Production rules
----------------
* No synthetic market data unless an explicit test command is used outside this app.
* Core market/macro data and institutional event feeds have separate refresh cadences.
* Missing credentials or failed providers render NOT_CONFIGURED / ERROR / STALE / NO_DATA.
* Trade events, TRF prints and filings are evidence; the UI never promotes them to intent by default.

Run:
    streamlit run app.py
"""
from __future__ import annotations

import json
import os
import sys
from copy import deepcopy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """<style>
      .stApp{background:#050811}
      header[data-testid="stHeader"]{background:transparent}
      .block-container{padding:0 !important;max-width:100% !important}
      #MainMenu,footer{visibility:hidden}
      section[data-testid="stSidebar"]{width:285px !important}
    </style>""",
    unsafe_allow_html=True,
)

DASH_PATH = os.path.join(HERE, "dashboard.html")
ALL_MARKETS = ["us", "idx", "crypto", "commodity", "fx"]


def _inject(desk: dict) -> str:
    with open(DASH_PATH, encoding="utf-8") as handle:
        html = handle.read()
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk, default=str, separators=(",", ":")) + ";"
    if "/*__INJECT_DATA__*/" in html:
        return html.replace("/*__INJECT_DATA__*/", payload)
    return html.replace("<body>", "<body>\n<script>" + payload + "</script>", 1)


@st.cache_data(ttl=60, show_spinner=False)
def _run_core(markets: tuple[str, ...]) -> dict:
    import data_layer as DL
    from run import build_desk

    data = DL.load_all(markets=list(markets), allow_live=True, allow_synthetic=False)
    return build_desk(data, top_per_market=40)


@st.cache_data(ttl=10, show_spinner=False)
def _run_institutional(desk: dict) -> dict:
    from institutional_data import collect_institutional_data

    return collect_institutional_data(desk)


def _provider_config() -> list[tuple[str, bool, str]]:
    return [
        ("SEC EDGAR", bool(os.getenv("WARROOM_SEC_USER_AGENT", "").strip()), "WARROOM_SEC_USER_AGENT"),
        ("Unusual Whales", bool(os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()), "UNUSUAL_WHALES_API_KEY"),
        ("Massive", bool(os.getenv("MASSIVE_API_KEY", "").strip()), "MASSIVE_API_KEY"),
        ("Nansen", bool(os.getenv("NANSEN_API_KEY", "").strip()), "NANSEN_API_KEY"),
        ("Arkham", bool(os.getenv("ARKHAM_API_KEY", "").strip()), "ARKHAM_API_KEY"),
    ]


with st.sidebar:
    st.markdown("### War Room OS")
    st.caption("Capital Intelligence Map · production mode")
    selected_markets = st.multiselect("Markets", ALL_MARKETS, default=ALL_MARKETS)
    auto_refresh = st.toggle("Auto-refresh live events", value=True)
    refresh_seconds = st.select_slider("Event refresh", options=[10, 15, 30, 60], value=15)
    st.caption("Core market/macro cache: 60 seconds. Provider-side cache and reporting lags still apply.")

    if st.button("↻ Force refresh all", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("**Provider configuration**")
    for provider, configured, env_name in _provider_config():
        mark = "🟢" if configured else "⚪"
        st.caption(f"{mark} {provider} · `{env_name}`")
    st.caption("Missing key = NOT_CONFIGURED. No placeholder records are created.")

    st.divider()
    st.markdown("**Data semantics**")
    st.caption(
        "Options-chain OI is a gamma proxy, not live flow. FINRA short volume is descriptive, "
        "not a dark-pool print. TRF prints and whale transfers do not prove intent."
    )


def _render() -> None:
    markets = tuple(selected_markets or ALL_MARKETS)
    try:
        core = _run_core(markets)
        desk = deepcopy(core)
        desk["institutional"] = _run_institutional(core)
        health = desk.get("data_health") or {}
        meta = desk.get("meta") or {}
        inst = desk.get("institutional") or {}
        live_count = int(health.get("live_count") or 0)
        inst_state = inst.get("overall_state") or "NOT_LOADED"
        st.caption(
            f"Market source: {meta.get('source','NO_DATA')} · data feeds live: {live_count}/{health.get('total_count',0)} "
            f"· institutional: {inst_state} · generated: {meta.get('generated','—')}"
        )
        components.html(_inject(desk), height=1160, scrolling=False)
    except Exception as exc:
        st.error(f"War Room run failed: {type(exc).__name__}: {exc}")
        fallback = {
            "meta": {"source": "ERROR", "generated": "—", "note": str(exc)},
            "data_health": {"overall": "ERROR", "sources": []},
            "systemic": {}, "markets": {}, "alpha": [], "reference": {},
            "institutional": {"overall_state": "ERROR", "statuses": [], "events": []},
        }
        components.html(_inject(fallback), height=1160, scrolling=False)


if auto_refresh:
    @st.fragment(run_every=f"{refresh_seconds}s")
    def _live_fragment() -> None:
        _render()

    _live_fragment()
else:
    _render()

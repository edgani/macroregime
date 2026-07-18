"""app.py — War Room OS · latest approved daily snapshots. Renders the approved dashboard.

    streamlit run app.py

Uses v40's proven loaders (data.loader.load_prices + data.fred_loader.load_fred_series) to fetch
live prices + FRED, runs the engines, and injects real data into dashboard.html. No historical/demo
modes. If a feed is down, the affected panel shows its honest state (not fabricated).
"""
from __future__ import annotations
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
import streamlit as st
import streamlit.components.v1 as components
import subprocess
from pathlib import Path
from alpha_foundry_adapter import attach_alpha_foundry, load_alpha_foundry_state, minimal_desk
from consistency_guard import enforce_desk

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
  .stApp{background:#0a0d12}
  header[data-testid="stHeader"]{background:transparent}
  .block-container{padding:0 !important;max-width:100% !important}
  #MainMenu,footer{visibility:hidden}
  section[data-testid="stSidebar"]{width:230px !important}
</style>""", unsafe_allow_html=True)

DASH_PATH = os.path.join(HERE, "dashboard.html")


def _inject(desk):
    html = open(DASH_PATH, encoding="utf-8").read()
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk, default=str) + ";"
    if "/*__INJECT_DATA__*/" in html:
        return html.replace("/*__INJECT_DATA__*/", payload)
    return html.replace("<body>", "<body>\n<script>" + payload + "</script>", 1)


@st.cache_data(ttl=1800, show_spinner="Fetching live data (yfinance + FRED) and running the engines…")
def _run(markets):
    import data_layer as DL
    from run import build_desk
    data = DL.load_all(markets=list(markets), allow_live=True)
    source = str(data.get("overall_source") or "")
    if not source.startswith("DAILY_SNAPSHOT"):
        return enforce_desk(minimal_desk("Approved daily market data unavailable; synthetic outputs are blocked from the review UI."))
    return enforce_desk(attach_alpha_foundry(build_desk(data, top_per_market=12)))


with st.sidebar:
    st.markdown("**War Room OS · DAILY SNAPSHOT / RESEARCH**")
    mkts = st.multiselect("Markets", ["us", "idx", "crypto", "commodity", "fx"],
                          default=["us", "idx", "crypto", "commodity", "fx"])
    if st.button("↻ Refresh live data"):
        st.cache_data.clear()
    st.caption("Latest available daily OHLCV + macro snapshots. This is not streaming execution data and not a LIVE trading permission.")
    st.divider()
    st.markdown("**US Alpha Foundry · integrated backend**")
    _fs = load_alpha_foundry_state()
    _fc = _fs.get("counts", {})
    st.caption(f"Status: {_fs.get('status')} · shortlist {_fc.get('shortlist',0)} · trials {_fc.get('registered_trials',0)}")
    st.caption("PAPER/LIVE tetap blocked sampai lockbox + prospective pass.")
    with st.expander("Run free-data research pipeline", expanded=False):
        _sec_contact = st.text_input("SEC contact email", value=os.environ.get("SEC_CONTACT_EMAIL", ""), key="sec_contact")
        _run_quick = st.button("Run US Alpha Foundry — Quick", key="run_af_quick")
        if _run_quick:
            if "@" not in _sec_contact:
                st.error("Masukkan email kontak yang valid untuk SEC fair-access policy.")
            else:
                _af_root = Path(HERE) / "alpha_foundry"
                _env = os.environ.copy()
                _env["SEC_USER_AGENT"] = f"Edward Gani {_sec_contact}"
                with st.spinner("Running free-data Alpha Foundry. Ini dapat memakan waktu..."):
                    _proc = subprocess.run([sys.executable, "run_pipeline.py", "--mode", "quick"], cwd=_af_root, env=_env, text=True, capture_output=True)
                if _proc.returncode == 0:
                    st.success("Pipeline selesai. Refresh dashboard untuk melihat shortlist/tournament.")
                    st.cache_data.clear()
                else:
                    st.error("Pipeline gagal. Log terakhir:")
                    st.code((_proc.stdout + "\n" + _proc.stderr)[-6000:])

try:
    desk = _run(tuple(mkts))
    html = _inject(desk)
    src = desk["meta"]["source"]; n = sum(len(m["setups"]) for m in desk["markets"].values())
    audit = desk.get("consistency_audit") or {}
    quarantined = int(audit.get("quarantined_count") or 0)
    if str(src).startswith("DAILY_SNAPSHOT"):
        st.toast(f"DAILY SNAPSHOT · configured watchlist {desk['meta']['universe_n']} · {n} displayed setups · RESEARCH ONLY")
        if quarantined:
            st.warning(f"{quarantined} malformed setup row(s) were quarantined. Unaffected research outputs remain visible; inspect Mission Control for details.")
    elif src == "DATA_UNAVAILABLE":
        st.warning("Live/approved market data was unavailable, so decision-bearing outputs were withheld. Check the sidebar market selection and Data Health/source details.")
    elif src == "CONSISTENCY_BLOCKED":
        st.error("A critical desk-structure error blocked decision outputs. This is different from a network/feed failure; inspect the consistency audit.")
    else:
        st.info(f"Research state loaded with source={src}. No LIVE claim is being made.")
except Exception as e:
    st.warning(f"Live market run failed: {e}. Original UI remains available in fail-closed mode; research status is still loaded.")
    desk = minimal_desk(str(e))
    html = _inject(desk)

components.html(html, height=1150, scrolling=True)

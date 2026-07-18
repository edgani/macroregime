"""app.py — War Room OS · LIVE only. Renders the approved v0.3 dashboard on your live feeds.

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
    return build_desk(data, top_per_market=40)  # raised 12→40 so the expanded crypto universe can surface


with st.sidebar:
    st.markdown("**War Room OS · LIVE**")
    mkts = st.multiselect("Markets", ["us", "idx", "crypto", "commodity", "fx"],
                          default=["us", "idx", "crypto", "commodity", "fx"])
    if st.button("↻ Refresh live data"):
        st.cache_data.clear()
    st.caption("Live feeds via v40 loaders (yfinance + FRED). Panels show honest state if a feed is down.")

try:
    desk = _run(tuple(mkts))
    html = _inject(desk)
    src = desk["meta"]["source"]; n = sum(len(m["setups"]) for m in desk["markets"].values())
    if src == "LIVE":
        st.toast(f"LIVE · universe {desk['meta']['universe_n']} · {n} setups")
    else:
        st.warning(f"Feeds returned no data here (source={src}). On your machine/Cloud the same loaders "
                   f"fetch live — this environment blocks outbound network. Showing the run as-is.")
except Exception as e:
    st.error(f"Run failed: {e}")
    html = open(DASH_PATH, encoding="utf-8").read()

components.html(html, height=1150, scrolling=True)

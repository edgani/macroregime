
from __future__ import annotations

import streamlit as st

from orchestration.build_snapshot import build_snapshot
from ui.dashboard_control_tower_page import render_dashboard_control_tower_page
from ui.us_stocks_page import render_us_stocks_page
from ui.ihsg_page import render_ihsg_page
from ui.forex_page import render_forex_page
from ui.commodities_page import render_commodities_page
from ui.crypto_page import render_crypto_page
from ui.risk_page import render_risk_page
from ui.diagnostics_page import render_diagnostics_page

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")


def _sidebar_controls() -> tuple[bool, bool, str]:
    with st.sidebar:
        st.markdown("## 🧭 MacroRegime Pro")
        st.caption("Refactor bridge: control tower + market action pages")
        force_refresh = st.button("🔄 Force Refresh", use_container_width=True)
        compact_mode = st.toggle("Compact runtime", value=True, help="Use runtime universe plan to keep the app lighter.")
        open_mode = st.selectbox(
            "Open mode",
            ["smart_fresh", "snapshot_only", "force_rebuild"],
            index=0,
            help="smart_fresh = normal, snapshot_only = prefer cached snapshot, force_rebuild = rebuild now",
        )
        st.markdown("---")
        page = st.radio(
            "Page",
            ["Dashboard", "US Stocks", "IHSG", "Forex", "Commodities", "Crypto", "Risk", "Diagnostics"],
            index=0,
        )
    return force_refresh, compact_mode, open_mode, page


def main() -> None:
    force_refresh, compact_mode, open_mode, page = _sidebar_controls()
    snapshot = build_snapshot(force_refresh=force_refresh, compact_mode=compact_mode, open_mode=open_mode)

    if page == "Dashboard":
        render_dashboard_control_tower_page(snapshot)
    elif page == "US Stocks":
        render_us_stocks_page(snapshot)
    elif page == "IHSG":
        render_ihsg_page(snapshot)
    elif page == "Forex":
        render_forex_page(snapshot)
    elif page == "Commodities":
        render_commodities_page(snapshot)
    elif page == "Crypto":
        render_crypto_page(snapshot)
    elif page == "Risk":
        render_risk_page(snapshot)
    elif page == "Diagnostics":
        render_diagnostics_page(snapshot)


if __name__ == "__main__":
    main()

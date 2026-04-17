from __future__ import annotations

import os
import streamlit as st

from orchestration.build_snapshot import build_snapshot
from ui.final_runtime import build_dashboard_payload, build_market_bundle
from ui.final_pages import render_dashboard, render_market_page, render_risk, render_diagnostics

st.set_page_config(page_title='MacroRegime Pro', page_icon='🧭', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
<style>
.block-container{max-width:1500px;padding-top:1rem;padding-bottom:2rem;}
[data-testid="stSidebar"]{border-right:1px solid rgba(255,255,255,.08);}
</style>
""", unsafe_allow_html=True)


def load_snapshot(force_refresh: bool = False) -> dict:
    os.environ.setdefault('MRP_LIVE_FETCH', '0')
    return build_snapshot(force_refresh=force_refresh, prefer_saved=not force_refresh, compact_mode=True)


def main():
    st.sidebar.title('MacroRegime Pro')
    refresh = st.sidebar.button('Refresh snapshot')
    page = st.sidebar.radio('Page', ['Dashboard','US Stocks','IHSG','Forex','Commodities','Crypto','Risk','Diagnostics'])
    snapshot = load_snapshot(force_refresh=refresh)

    if page == 'Dashboard':
        render_dashboard(build_dashboard_payload(snapshot))
    elif page == 'US Stocks':
        render_market_page(build_market_bundle(snapshot, 'US'), ihsg=False, title='US Stocks')
    elif page == 'IHSG':
        render_market_page(build_market_bundle(snapshot, 'IHSG'), ihsg=True, title='IHSG')
    elif page == 'Forex':
        render_market_page(build_market_bundle(snapshot, 'FX'), ihsg=False, title='Forex')
    elif page == 'Commodities':
        render_market_page(build_market_bundle(snapshot, 'Commodities'), ihsg=False, title='Commodities')
    elif page == 'Crypto':
        render_market_page(build_market_bundle(snapshot, 'Crypto'), ihsg=False, title='Crypto')
    elif page == 'Risk':
        render_risk(snapshot)
    elif page == 'Diagnostics':
        render_diagnostics(snapshot)


if __name__ == '__main__':
    main()
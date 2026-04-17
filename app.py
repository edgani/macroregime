
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from orchestration.build_snapshot import build_snapshot
from ui.refactor_runtime import build_scenario_stack, build_market_mix, build_market_bundle, build_dashboard_payload
from ui.refactor_pages import render_dashboard_page, render_market_page, render_risk_page, render_diagnostics_page

st.set_page_config(page_title='MacroRegime Pro Refactored', page_icon='🧭', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container{padding-top:0.6rem;padding-bottom:2rem;max-width:1500px;}
[data-testid="stSidebar"] {border-right:1px solid rgba(255,255,255,0.08);}
</style>
""", unsafe_allow_html=True)


def load_snapshot(force_refresh: bool = False) -> dict:
    os.environ.setdefault('MRP_LIVE_FETCH', '0')
    return build_snapshot(force_refresh=force_refresh, prefer_saved=not force_refresh, compact_mode=True)


def main():
    st.sidebar.title('MacroRegime Pro')
    refresh = st.sidebar.button('Refresh snapshot')
    page = st.sidebar.radio('Page', ['Dashboard', 'US Stocks', 'IHSG', 'Forex', 'Commodities', 'Crypto', 'Risk', 'Diagnostics'])
    snapshot = load_snapshot(force_refresh=refresh)

    stack = build_scenario_stack(snapshot)
    market_mix = build_market_mix(snapshot, stack)
    bundles = {
        'us': build_market_bundle(snapshot, 'us', market_mix),
        'ihsg': build_market_bundle(snapshot, 'ihsg', market_mix),
        'fx': build_market_bundle(snapshot, 'fx', market_mix),
        'commodities': build_market_bundle(snapshot, 'commodities', market_mix),
        'crypto': build_market_bundle(snapshot, 'crypto', market_mix),
    }
    dashboard_payload = build_dashboard_payload(snapshot, stack, market_mix, bundles)

    if page == 'Dashboard':
        render_dashboard_page(dashboard_payload)
    elif page == 'US Stocks':
        render_market_page(bundles['us'], ihsg=False, title='US Stocks')
    elif page == 'IHSG':
        render_market_page(bundles['ihsg'], ihsg=True)
    elif page == 'Forex':
        render_market_page(bundles['fx'], ihsg=False, title='Forex')
    elif page == 'Commodities':
        render_market_page(bundles['commodities'], ihsg=False, title='Commodities')
    elif page == 'Crypto':
        render_market_page(bundles['crypto'], ihsg=False, title='Crypto')
    elif page == 'Risk':
        render_risk_page(snapshot)
    elif page == 'Diagnostics':
        render_diagnostics_page(snapshot)


if __name__ == '__main__':
    main()

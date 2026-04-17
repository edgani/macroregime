
from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.dashboard_main_page import render_dashboard_main_page
from ui.scenarios_page import render_scenarios_page
from ui.cross_asset_page import render_cross_asset_page
from ui.opportunity_board_page import render_opportunity_board_page
from ui.components.compact_table_helpers import frame_height
from ui.components.market_action_tables import build_market_action_payload



def _attack_matrix(snapshot: dict) -> pd.DataFrame:
    sections = {
        'US': ('us', snapshot.get('us', {}) or {}),
        'IHSG': ('ihsg', snapshot.get('ihsg', {}) or {}),
        'FX': ('fx', snapshot.get('fx', {}) or {}),
        'Commodities': ('commodities', snapshot.get('commodities', {}) or {}),
        'Crypto': ('crypto', snapshot.get('crypto', {}) or {}),
    }
    table = []
    for label, (key, section) in sections.items():
        payload = build_market_action_payload(snapshot, section, key)
        if key == 'ihsg':
            table.append({
                'Market': label,
                'Best Longs / Buys Now': ', '.join([r.get('ticker','') for r in payload.get('buy_now', [])[:3]]) or '—',
                'Best Shorts Now': '—',
                'Front-Run Longs / Buys': ', '.join([r.get('ticker','') for r in payload.get('front_run_buy', [])[:3]]) or '—',
                'Front-Run Shorts': '—',
            })
        else:
            table.append({
                'Market': label,
                'Best Longs / Buys Now': ', '.join([r.get('ticker','') for r in payload.get('now_long', [])[:3]]) or '—',
                'Best Shorts Now': ', '.join([r.get('ticker','') for r in payload.get('now_short', [])[:3]]) or '—',
                'Front-Run Longs / Buys': ', '.join([r.get('ticker','') for r in payload.get('front_run_long', [])[:3]]) or '—',
                'Front-Run Shorts': ', '.join([r.get('ticker','') for r in payload.get('front_run_short', [])[:3]]) or '—',
            })
    return pd.DataFrame(table)


def _risk_summary_rows(snapshot: dict) -> list[str]:
    shared = snapshot.get('shared_core', {}) or {}
    risk = shared.get('risk_summary', {}) or {}
    exec_mode = shared.get('execution_mode', {}) or {}
    ribbon = shared.get('status_ribbon', {}) or {}
    return [
        f"Risk-off: {risk.get('risk_off_state', '-')}",
        f"Crash: {risk.get('crash_state', '-')}",
        f"Execution: {exec_mode.get('execute_mode', exec_mode.get('mode', '-'))}",
        f"Size multiplier: {exec_mode.get('size_multiplier', '-')}",
        f"Confidence: {ribbon.get('confidence_band', '-')}",
        f"Safe harbor: {ribbon.get('safe_harbor', '-')}",
    ]


def render_dashboard_control_tower_page(snapshot: dict) -> None:
    st.title('Dashboard')
    tabs = st.tabs(['Control Tower', 'Scenarios & What-If', 'Cross-Asset', 'Global Board'])

    with tabs[0]:
        render_dashboard_main_page(snapshot)
        st.divider()
        st.subheader('Ticker Attack Matrix')
        attack = _attack_matrix(snapshot)
        st.dataframe(attack, use_container_width=True, hide_index=True, height=frame_height(len(attack), base=72, row=30, max_height=220))
        st.caption('Dashboard tetap context-first, tapi sekarang langsung turun ke ticker/pair attack matrix.')
        st.divider()
        st.subheader('Risk State')
        for line in _risk_summary_rows(snapshot):
            st.write(f"- {line}")

    with tabs[1]:
        render_scenarios_page(snapshot)

    with tabs[2]:
        render_cross_asset_page(snapshot)

    with tabs[3]:
        render_opportunity_board_page(snapshot)


from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.dashboard_main_page import render_dashboard_main_page
from ui.scenarios_page import render_scenarios_page
from ui.cross_asset_page import render_cross_asset_page
from ui.opportunity_board_page import render_opportunity_board_page
from ui.components.compact_table_helpers import frame_height


def _pick(rows: list[dict], market: str, actionable: bool, side: str | None, n: int = 3) -> list[str]:
    out: list[str] = []
    for row in rows or []:
        if str(row.get('market', '')).upper() != market.upper():
            continue
        state = str(row.get('state', '')).lower()
        is_actionable = state == 'actionable'
        if actionable != is_actionable:
            continue
        if side is not None:
            rb = str(row.get('bias', '')).lower()
            if side == 'long' and 'long' not in rb and 'buy' not in rb:
                continue
            if side == 'short' and 'short' not in rb:
                continue
        ticker = str(row.get('ticker', '')).strip()
        if ticker and ticker not in out:
            out.append(ticker)
        if len(out) >= n:
            break
    return out


def _attack_matrix(snapshot: dict) -> pd.DataFrame:
    rows = snapshot.get('master_opportunities', {}).get('rows', []) or []
    table = []
    markets = [
        ('US', 'US'),
        ('IHSG', 'IHSG'),
        ('FX', 'FX'),
        ('Commodities', 'Commodities'),
        ('Crypto', 'Crypto'),
    ]
    for label, key in markets:
        if key == 'IHSG':
            table.append({
                'Market': label,
                'Best Longs / Buys Now': ', '.join(_pick(rows, key, True, 'long', 3)) or '—',
                'Best Shorts Now': '—',
                'Front-Run Longs / Buys': ', '.join(_pick(rows, key, False, 'long', 3)) or '—',
                'Front-Run Shorts': '—',
            })
        else:
            table.append({
                'Market': label,
                'Best Longs / Buys Now': ', '.join(_pick(rows, key, True, 'long', 3)) or '—',
                'Best Shorts Now': ', '.join(_pick(rows, key, True, 'short', 3)) or '—',
                'Front-Run Longs / Buys': ', '.join(_pick(rows, key, False, 'long', 3)) or '—',
                'Front-Run Shorts': ', '.join(_pick(rows, key, False, 'short', 3)) or '—',
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

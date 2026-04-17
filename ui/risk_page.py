
from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components.compact_table_helpers import frame_height
from utils.streamlit_utils import info_card, metric_card


def render_risk_page(snapshot: dict) -> None:
    st.title('Risk')
    shared = snapshot.get('shared_core', {}) or {}
    risk = shared.get('risk_summary', {}) or {}
    exec_mode = shared.get('execution_mode', {}) or {}
    rr = shared.get('risk_range', {}) or {}
    tact = shared.get('tactical_components', {}) or {}
    ribbon = shared.get('status_ribbon', {}) or {}

    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Risk-off', str(risk.get('risk_off_state', '-')), f"score {float(risk.get('risk_off_score', 0.0) or 0.0):.2f}")
    with c2:
        metric_card('Crash', str(risk.get('crash_state', '-')), f"score {float(risk.get('crash_score', 0.0) or 0.0):.2f}")
    with c3:
        metric_card('Execution', str(exec_mode.get('execute_mode', exec_mode.get('mode', '-'))), f"size {exec_mode.get('size_multiplier', '-')}")
    with c4:
        metric_card('Confidence', str(ribbon.get('confidence_band', '-')), str(ribbon.get('resolved_language', '-')))

    a, b = st.columns(2, gap='small')
    with a:
        info_card('Top reasons / risk state', [
            f"Top reasons: {', '.join(risk.get('top_reasons', [])[:3]) or '-'}",
            f"Divergence: {risk.get('risk_off_vs_crash_divergence_state', '-')}",
            f"Safe harbor: {ribbon.get('safe_harbor', '-')}",
            f"Best beneficiary: {ribbon.get('best_beneficiary', '-')}",
        ], accent='#633535')
    with b:
        info_card('Execution notes', list(exec_mode.get('notes', [])[:5]) or ['-'], accent='#365b46')

    st.subheader('Risk Range / Tactical Weather')
    rr_rows = [
        {'field': 'Range state', 'value': rr.get('range_state', '-')},
        {'field': 'Stretch', 'value': rr.get('stretch_state', '-')},
        {'field': 'Coverage', 'value': rr.get('asset_range_coverage', '-')},
        {'field': 'Trade score', 'value': tact.get('trade_score', '-')},
        {'field': 'Trend score', 'value': tact.get('trend_score', '-')},
        {'field': 'Tail score', 'value': tact.get('tail_score', '-')},
        {'field': 'Cross-asset confirm', 'value': tact.get('cross_asset_confirm', '-')},
        {'field': 'Weather score', 'value': tact.get('weather_score', '-')},
    ]
    st.dataframe(pd.DataFrame(rr_rows), use_container_width=True, hide_index=True, height=frame_height(len(rr_rows), base=72, row=28, max_height=220))

    if rr.get('notes'):
        st.caption(' | '.join(rr.get('notes', [])[:3]))

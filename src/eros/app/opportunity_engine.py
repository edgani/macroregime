"""Conservative opportunity interface."""

from __future__ import annotations

import streamlit as st

from eros.app.components import section_header
from eros.app.state import DashboardState

PACKET_FIELDS = (
    "Mechanism and competing thesis",
    "Four separate probabilities",
    "Expected win, loss, and tail",
    "Spread, slippage, funding, borrow, tax, FX, capacity",
    "Fundamental target and invalidation",
    "Crowding and capital formation",
    "Value of waiting and cash",
    "Decision snapshot and lineage",
)


def render(state: DashboardState) -> None:
    section_header(
        "Thesis to trade",
        "Opportunity Engine",
        "Which opportunity has positive conservative EV after every friction?",
    )
    filters = st.tabs(
        (
            "Leaderboard",
            "Horizon",
            "Instrument Type",
            "Capital Formation",
            "Crowding",
            "Thesis Detail",
            "Rejected",
        )
    )
    with filters[0]:
        if not state.qualified_opportunities:
            st.warning("NO QUALIFIED OPPORTUNITY")
            st.caption("An empty result is valid when acceptance gates fail.")
        else:
            st.dataframe(state.qualified_opportunities, width="stretch", hide_index=True)
    with filters[1]:
        st.info("Now / week / month / quarter / year+ remain separated. No eligible packets.")
    with filters[2]:
        st.info("Long / short / option / pair / hedge / wait mappings are evidence-gated.")
    with filters[3]:
        st.info("Capital-formation stage is UNKNOWN until independent flow families are admitted.")
    with filters[4]:
        st.info("Crowding and capacity cannot be inferred from attention or price action alone.")
    with filters[5]:
        rows = [{"Required field": field, "Status": "UNKNOWN"} for field in PACKET_FIELDS]
        st.dataframe(rows, width="stretch", hide_index=True)
    with filters[6]:
        st.dataframe(state.rejected_opportunities, width="stretch", hide_index=True)

    section_header("Acceptance", "Promotion Gate", "Why is capital still blocked?")
    st.error(state.execution.reason)

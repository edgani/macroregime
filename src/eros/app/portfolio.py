"""Portfolio, scenario, and decision-journal interface."""

from __future__ import annotations

import streamlit as st

from eros.app.components import section_header
from eros.app.state import DashboardState


def render(state: DashboardState) -> None:
    section_header(
        "Capital under uncertainty",
        "Portfolio",
        "What do I own, what hidden risks overlap, and what is the value of waiting?",
    )
    st.info("No personal portfolio is loaded. Research data and portfolio data stay separated.")
    sections = st.tabs(
        (
            "Current Portfolio",
            "Suggested Changes",
            "Exposure Decomposition",
            "Scenarios",
            "Liquidity",
            "Hedges",
            "Rebalance Queue",
            "Decision Journal",
        )
    )
    with sections[0]:
        st.caption("EMPTY — connect a private portfolio store separately from research data.")
    with sections[1]:
        st.warning("WAIT — no qualified opportunity and no holdings context.")
    with sections[2]:
        st.info(
            "UNKNOWN — growth, inflation, liquidity, credit, funding, country, currency, "
            "duration, commodity, policy, leverage, and counterparty overlap cannot be computed."
        )
    with sections[3]:
        st.dataframe(state.scenarios, width="stretch", hide_index=True)
    with sections[4]:
        st.info(
            "UNKNOWN — days-to-exit, spread, borrow, settlement, tax, and market access not loaded."
        )
    with sections[5]:
        st.info(
            "No hedge recommendation without position exposure and a validated scenario mechanism."
        )
    with sections[6]:
        st.error("LOCKED — every rebalance requires a qualified packet and human approval.")
    with sections[7]:
        st.caption("No action or inaction has been recorded in this synthetic snapshot.")

    section_header(
        "Decision completeness", "Four Required Answers", "Absence of action needs a reason too"
    )
    rows = [
        {"Question": "Why buy?", "Current answer": "No evidence-qualified reason."},
        {"Question": "Why sell?", "Current answer": "No position context."},
        {"Question": "Why not buy?", "Current answer": "Data, proof, and net-EV gates fail."},
        {"Question": "Why not sell?", "Current answer": "No portfolio is loaded."},
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

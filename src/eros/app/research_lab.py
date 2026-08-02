"""Research governance, proof, failures, and data-health interface."""

from __future__ import annotations

import streamlit as st

from eros.app.components import bullet_list, section_header
from eros.app.state import DashboardState


def render(state: DashboardState) -> None:
    section_header(
        "Proof center",
        "Research Lab",
        "What is known, what failed, and what must be learned next?",
    )
    sections = st.tabs(
        (
            "Thesis Discovery",
            "Evidence Firewall",
            "Mechanisms",
            "Experiments",
            "Prediction Journal",
            "Failures",
            "Data Health",
            "Coverage Gaps",
            "Models",
            "Agent IQ",
        )
    )
    with sections[0]:
        st.write("Every material observation requires 3-7 competing hypotheses including a null.")
        st.dataframe(
            [
                {
                    "Thesis": item.thesis_id,
                    "Status": item.status,
                    "Posterior": f"{item.posterior:.0%}",
                    "Interval": item.interval,
                    "Permission": item.decision_permission,
                }
                for item in state.theses
            ],
            width="stretch",
            hide_index=True,
        )
    with sections[1]:
        st.info("Narratives open research tickets; they cannot change score, sizing, or action.")
    with sections[2]:
        st.dataframe(state.mechanisms, width="stretch", hide_index=True)
    with sections[3]:
        st.warning("No experiment is eligible for PROVEN_SCOPE_LIMITED promotion in this snapshot.")
    with sections[4]:
        st.info("No matured sealed prospective forecast. Capital remains locked.")
    with sections[5]:
        st.write("Busted as tested: debt/GDP-to-gold shortcut and price-derived direction rules.")
    with sections[6]:
        feed_rows = [item.model_dump() for item in state.data_health.feeds]
        st.dataframe(feed_rows, width="stretch", hide_index=True)
    with sections[7]:
        bullet_list(state.unknowns)
    with sections[8]:
        st.info(
            "Every model requires owner, scope, assumptions, challenger, review date, "
            "and kill switch."
        )
    with sections[9]:
        st.dataframe(
            [
                {"Metric": "Calibration", "Status": "UNKNOWN"},
                {"Metric": "Replication rate", "Status": "UNKNOWN"},
                {"Metric": "Blind-spot score", "Status": "DATA_DEBT"},
                {"Metric": "Model decay", "Status": "UNKNOWN"},
            ],
            width="stretch",
            hide_index=True,
        )

    section_header("Governance", "Acceptance Battery", "Code running is not proof")
    st.dataframe(state.acceptance_gates, width="stretch", hide_index=True)

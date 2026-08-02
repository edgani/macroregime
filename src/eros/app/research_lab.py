"""Proof center and research-governance interface."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eros.app.shell import DemoState


def render(state: "DemoState") -> None:
    import streamlit as st
    st.title("Research Lab")
    sections = st.tabs(("Thesis Discovery", "Evidence Firewall", "Mechanisms", "Experiments", "Prediction Journal", "Failures", "Data Health", "Coverage Gaps", "Models", "Agent IQ"))
    messages = ["3–7 competing hypotheses including null are mandatory.", "Narratives cannot directly change sizing or action.", "No validated edge without experiment lineage.", "Holdouts are sealed; failed variants remain in the trial ledger.", "No matured prospective forecasts.", "Legacy claims remain unverified until reproduced.", "All live feeds: NO_DATA.", "Global PIT coverage and licensed flow data are material gaps.", "No model may approve itself.", "Calibration, replication, blind-spot, and decay metrics are UNKNOWN."]
    for section, message in zip(sections, messages, strict=True):
        with section:
            st.write(message)
    st.subheader("Acceptance battery")
    st.dataframe([{"gate": gate, "status": status} for gate, status in [("Architecture", "PASS"), ("Data", "FAIL"), ("Research", "PARTIAL"), ("Legacy replication", "FAIL"), ("Historical replay", "FAIL"), ("Opportunity", "PASS-EMPTY"), ("Portfolio", "PARTIAL"), ("Prospective", "FAIL")]], use_container_width=True, hide_index=True)

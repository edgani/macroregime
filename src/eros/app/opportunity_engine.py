"""Conservative opportunity interface."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eros.app.shell import DemoState


def render(state: "DemoState") -> None:
    import streamlit as st
    st.title("Opportunity Engine")
    st.warning("NO QUALIFIED OPPORTUNITY")
    st.write("Default ordering: conservative EV lower bound. No instrument is eligible because live evidence, costs, and calibration are incomplete.")
    st.subheader("Required packet")
    st.dataframe([{"field": field, "status": "UNKNOWN"} for field in ["Mechanism and thesis", "Four separated probabilities", "Expected win and loss", "All costs", "Target and invalidation", "Crowding and capacity", "Value of waiting", "Audit lineage"]], use_container_width=True, hide_index=True)
    with st.expander("Rejected opportunities"):
        st.write("All synthetic candidates are rejected from capital allocation by design.")

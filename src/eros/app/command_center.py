"""Decision-centric Command Center."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eros.app.shell import DemoState


def render(state: "DemoState") -> None:
    import streamlit as st
    st.title("EROS Command Center")
    st.caption(f"As of: {state.as_of}")
    cols = st.columns(4)
    for column, title, value in zip(cols, ["Data health", "Qualified opportunities", "Execution", "Unknowns"], ["NO_DATA", "0", "LOCKED", "Material"], strict=True):
        column.metric(title, value)
    st.subheader("Global regime")
    st.info("UNKNOWN — no point-in-time live feeds have been admitted.")
    st.subheader("Global Capital Map")
    st.dataframe([{"source": "Cash", "target": "Bonds", "status": "DATA_DEBT"}, {"source": "Bonds", "target": "Equities", "status": "DATA_DEBT"}], use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left:
        st.subheader("What Changed")
        st.write("No verified change packet is available.")
        st.subheader("Thesis Board")
        st.write("No active thesis has passed the evidence firewall.")
    with right:
        st.subheader("Opportunity Board")
        st.warning("NO QUALIFIED OPPORTUNITY")
        st.subheader("Action Queue")
        st.write("WAIT — human approval remains mandatory.")
    st.subheader("Top Risks and Unknowns")
    st.write("Live PIT coverage, licensed flow data, cross-country vintages, and prospective calibration are unresolved.")
    st.subheader("Upcoming Catalysts")
    st.write("UNKNOWN — no verified calendar adapter is active.")
    with st.expander("Lineage"):
        st.code("mode=synthetic
source=registries + frozen fixtures
execution_enabled=false")

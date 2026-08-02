"""Portfolio and decision-journal interface."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eros.app.shell import DemoState


def render(state: "DemoState") -> None:
    import streamlit as st
    st.title("Portfolio")
    st.info("No personal portfolio data is loaded. Research data and portfolio data are separated.")
    sections = st.tabs(("Current Portfolio", "Suggested Changes", "Exposure Decomposition", "Scenarios", "Liquidity", "Hedges", "Rebalance Queue", "Decision Journal"))
    for section, message in zip(sections, ["EMPTY", "WAIT", "UNKNOWN", "Synthetic scenarios only", "UNKNOWN", "No hedge recommendation", "Human approval required", "No decisions recorded"], strict=True):
        with section:
            st.write(message)
    st.subheader("Decision questions")
    st.write("Why buy: no qualified evidence. Why sell: no position context. Why not buy: acceptance gates fail. Why not sell: no portfolio loaded.")

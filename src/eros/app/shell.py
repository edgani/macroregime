"""Five-tab Streamlit shell for EROS v3."""

from __future__ import annotations

import streamlit as st

from eros.app.state import DashboardState, build_public_data_state, load_dashboard_state
from eros.app.theme import APP_CSS
from eros.data.public_markets import fetch_public_market_snapshot

PRODUCT_NAME = "EROS"
MAIN_TABS = (
    "Command Center",
    "Global Explorer",
    "Opportunity Engine",
    "Portfolio",
    "Research Lab",
)


def build_demo_state() -> DashboardState:
    """Backward-compatible state factory backed by the validated snapshot."""
    return load_dashboard_state()


@st.cache_data(ttl=300, show_spinner=False)
def _load_runtime_state() -> DashboardState:
    """Refresh public feeds every five minutes with last-good fallback."""
    return build_public_data_state(load_dashboard_state(), fetch_public_market_snapshot())


def _hero(state: DashboardState) -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">Economic Reasoning & Opportunity System</div>
          <h1>EROS v3.0</h1>
          <p>Global mechanism-first research, uncertainty reduction, and capital allocation.</p>
          <div class="mode-strip">
            <span class="mode-pill">MODE: {state.mode}</span>
            <span class="mode-pill">AS OF: {state.data_health.as_of}</span>
            <span class="mode-pill">EXECUTION: {state.execution.permission}</span>
            <span class="mode-pill">HUMAN APPROVAL: REQUIRED</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app() -> None:
    """Render the application; validation errors stop the app rather than inventing state."""
    st.set_page_config(page_title="EROS v3.0", page_icon=None, layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    state = _load_runtime_state()
    _hero(state)
    if state.mode == "SYNTHETIC_DEMO":
        st.warning(state.banner)
    elif state.mode == "PUBLIC_DATA":
        st.warning(
            "PUBLIC DATA + FROZEN SYNTHETIC RESEARCH FIXTURE — "
            "BENCHMARK OBSERVATIONS LOADED — CAUSAL REGIME UNKNOWN — EXECUTION LOCKED"
        )

    tabs = st.tabs(MAIN_TABS)
    from eros.app.command_center import render as render_command_center
    from eros.app.global_explorer import render as render_global_explorer
    from eros.app.opportunity_engine import render as render_opportunity_engine
    from eros.app.portfolio import render as render_portfolio
    from eros.app.research_lab import render as render_research_lab

    renderers = (
        render_command_center,
        render_global_explorer,
        render_opportunity_engine,
        render_portfolio,
        render_research_lab,
    )
    for tab, renderer in zip(tabs, renderers, strict=True):
        with tab:
            renderer(state)

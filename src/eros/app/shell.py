"""Five-tab Streamlit application shell and fail-closed demo state."""
from pydantic import BaseModel

MAIN_TABS = ("Command Center", "Global Explorer", "Opportunity Engine", "Portfolio", "Research Lab")


class DemoState(BaseModel):
    is_synthetic: bool
    banner: str
    execution_enabled: bool
    as_of: str


def build_demo_state() -> DemoState:
    return DemoState(is_synthetic=True, banner="SYNTHETIC DEMO — NO LIVE DATA — EXECUTION LOCKED", execution_enabled=False, as_of="Frozen fixture; not a live timestamp")


def render_app() -> None:
    import streamlit as st
    from eros.app.command_center import render as render_command_center
    from eros.app.global_explorer import render as render_global_explorer
    from eros.app.opportunity_engine import render as render_opportunity_engine
    from eros.app.portfolio import render as render_portfolio
    from eros.app.research_lab import render as render_research_lab

    st.set_page_config(page_title="EROS v3.0", page_icon=None, layout="wide", initial_sidebar_state="collapsed")
    state = build_demo_state()
    st.markdown("<style>html,body,[data-testid='stAppViewContainer']{background:#0d1117;color:#e6edf3}.stTabs [data-baseweb='tab-list']{gap:8px}.stTabs [data-baseweb='tab']{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 16px}</style>", unsafe_allow_html=True)
    st.error(state.banner)
    tabs = st.tabs(MAIN_TABS)
    renderers = (render_command_center, render_global_explorer, render_opportunity_engine, render_portfolio, render_research_lab)
    for tab, renderer in zip(tabs, renderers, strict=True):
        with tab:
            renderer(state)

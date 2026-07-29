"""
War Room — single-page operational desk.  Run:  streamlit run app.py

The desk (desk_embed + dashboard.html) is the entire UI: JARVIS plain-language
brief, thesis lifecycle, current quotes, macro/carry, and the War Room 6
intelligence bridge (quad, crash meter, funding, crowding, compass) — one page,
no stacked tab bars, no duplicate UI.

The legacy multi-tab render stack (warroom/render.py) remains importable and
its engines still feed the desk through warroom6_bridge in the data worker;
it is intentionally not rendered here anymore.
"""
import streamlit as st


def main():
    st.set_page_config(page_title="War Room", layout="wide", initial_sidebar_state="collapsed")
    from desk_embed import render_desk
    render_desk()


if __name__ == "__main__":
    main()

"""War Room OS V10.1 Streamlit shell for operational research and shadow trading.

Thin wrapper — the actual desk embedding (snapshot seed, data worker, payload
injection) lives in desk_embed.py and is shared with app.py so both entry
points render the identical desk.
"""
from __future__ import annotations

import streamlit as st

from desk_embed import render_desk

st.set_page_config(page_title="War Room OS V10.1 Operational Trading System", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>.stApp{background:#050811}header[data-testid="stHeader"]{display:none}.block-container{padding:0!important;max-width:100%!important}#MainMenu,footer,[data-testid="stToolbar"]{display:none!important}</style>""", unsafe_allow_html=True)

render_desk()

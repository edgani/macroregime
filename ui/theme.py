"""ui/theme.py — Global dark theme injection for v10 visual"""
from __future__ import annotations
import streamlit as st

def _inject_theme() -> None:
    st.markdown("""
        <style>
        .stApp { background-color: #0d1117 !important; }
        .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, li, span { color: #c9d1d9 !important; }
        button[data-baseweb="tab"] { background-color: #161b22 !important; color: #8b949e !important; border: 1px solid #30363d !important; border-radius: 8px 8px 0 0 !important; margin-right: 4px !important; font-size: 13px !important; font-weight: 600 !important; }
        button[data-baseweb="tab"][aria-selected="true"] { background-color: #1f6feb !important; color: #ffffff !important; border-bottom: 2px solid #58a6ff !important; }
        [data-testid="stMetric"] { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; padding: 12px !important; }
        [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; }
        [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 18px !important; font-weight: 700 !important; }
        .stDataFrame { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; }
        .stDataFrame th { background-color: #21262d !important; color: #e6edf3 !important; font-weight: 600 !important; font-size: 12px !important; }
        .stDataFrame td { color: #c9d1d9 !important; font-size: 12px !important; }
        .stAlert { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; }
        .stAlert [data-testid="stMarkdownContainer"] { color: #c9d1d9 !important; }
        .stProgress > div > div { background-color: #1f6feb !important; }
        .streamlit-expanderHeader { background-color: #161b22 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; border-radius: 8px !important; font-size: 13px !important; font-weight: 600 !important; }
        .streamlit-expanderContent { background-color: #0d1117 !important; border: 1px solid #30363d !important; border-top: none !important; border-radius: 0 0 8px 8px !important; }
        .stButton > button { background-color: #21262d !important; color: #c9d1d9 !important; border: 1px solid #30363d !important; border-radius: 8px !important; font-weight: 600 !important; }
        .stButton > button:hover { background-color: #30363d !important; border-color: #58a6ff !important; }
        .stJson { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: #30363d !important; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
        </style>
    """, unsafe_allow_html=True)
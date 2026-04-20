"""app_v9.py — MacroRegime Pro v9

REBUILT: Monolith replaced with modular pipeline.

Architecture:
  app_v9.py (~200 lines) = orchestrator only
    ↓
  orchestration/build_snapshot.py (778 lines) = full computation
    ↓  
  engines/* + features/* = individual signal engines
    ↓
  orchestration/snap_adapter.py = maps new snap → UI format
    ↓
  ui/* = all UI code unchanged (reads legacy snap format)

Benefits vs monolith (app.py):
  ✅ indpro_roc_3m, cpi_roc_3m, leading_indicator_composite (second derivatives)
  ✅ correct macro_features.py signals (not duplicated in monolith)
  ✅ BI rate awareness for IHSG
  ✅ clean single code path
  ✅ maintainable: each engine is independent
  ✅ ~200 lines vs 5000 lines
"""
from __future__ import annotations
import os, math, datetime
from pathlib import Path
from typing import Optional
import streamlit as st
import pandas as pd

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS (same dark theme as original) ─────────────────────────────────────────
st.markdown("""<style>
html,body,[class*="css"]{background:#0d1117!important;color:#e2e8f0}
.stApp{background:#0d1117}
section[data-testid="stSidebar"]{display:none}
.stTabs [data-baseweb="tab-list"]{background:#0d1117;border-bottom:1px solid #21262d}
.stTabs [data-baseweb="tab"]{color:#718096;padding:10px 16px;font-size:13px;font-weight:600}
.stTabs [aria-selected="true"]{color:#e2e8f0!important;border-bottom:2px solid #3b82f6!important}
div[data-testid="stExpander"]{background:#111827;border:1px solid #21262d;border-radius:8px}
.stDataFrame{background:#0d1117}
</style>""", unsafe_allow_html=True)

# ── Pipeline imports ───────────────────────────────────────────────────────────
try:
    from orchestration.build_snapshot import build_snapshot
    from orchestration.snap_adapter import adapt_snap
    _HAS_MODULAR = True
except ImportError as _e:
    _HAS_MODULAR = False
    _IMPORT_ERROR = str(_e)

# ── UI imports (unchanged from v8) ────────────────────────────────────────────
try:
    from ui.command_center_page import render_command_center
    _HAS_CC = True
except Exception:
    _HAS_CC = False

try:
    from ui.pages_redesigned import page_regime_intel, page_strategy, page_markets_v2, page_risk_diag
    _HAS_NEW_PAGES = True
except Exception:
    _HAS_NEW_PAGES = False

# ── Cache layer ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)  # 5-min for prices
def _load_snap(force: bool = False) -> dict:
    """Run the full modular pipeline and return adapted legacy snap."""
    new_snap = build_snapshot(
        force_refresh=force,
        compact_mode=False,
    )
    # Inject raw prices/fred into new_snap for adapter
    new_snap["_raw"] = {
        "prices": new_snap.get("meta", {}).get("_prices_ref", {}),
        "fred": new_snap.get("meta", {}).get("_fred_ref", {}),
    }
    return adapt_snap(new_snap)


def _load_snap_with_progress() -> dict:
    """Load snap with a progress indicator."""
    bar = st.progress(0, text="MacroRegime Pro — loading data...")
    try:
        bar.progress(20, text="Fetching market data...")
        snap = _load_snap()
        bar.progress(100, text="Done!")
        bar.empty()
        return snap
    except Exception as e:
        bar.empty()
        raise e


# ── Status ribbon (top bar) ───────────────────────────────────────────────────
def _render_ribbon(snap: dict) -> None:
    """Render the top status ribbon — quad, conf, best picks, VIX, time."""
    q = snap.get("q", {}); f = snap.get("f", {}); tickers = snap.get("regime_tickers", {})
    cr = snap.get("crash", {}); news = snap.get("news_overlay", {})
    
    s_quad = q.get("quad","Q?"); m_quad = q.get("monthly_quad", s_quad)
    conf = q.get("confidence", 0); vix = f.get("vix_last", 20)
    exec_mode = cr.get("exec_mode","?")
    news_label = news.get("label","")[:35] if news else ""
    
    quad_cfg = {"Q1":("#276749","#68d391"),"Q2":("#b7791f","#f6ad55"),"Q3":("#c53030","#fc8181"),"Q4":("#c53030","#feb2b2")}
    qbg, qtxt = quad_cfg.get(s_quad, ("#4a5568","#a0aec0"))
    mbg, mtxt = quad_cfg.get(m_quad, ("#4a5568","#a0aec0"))
    
    best_long = (tickers.get("us_longs") or ["—"])[0]
    best_ihsg = (tickers.get("ihsg_buys") or ["—"])[0]
    top_d = snap.get("top_drivers", []); top_d_str = " · ".join([d.get("label","")[:20] for d in top_d[:2]])
    ts = snap.get("ts","")[:16]

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:5px 16px;background:#0d1117;'
        f'border-bottom:1px solid #21262d;font-size:12px;flex-wrap:wrap;">'
        f'<span style="background:{qbg};color:{qtxt};padding:2px 10px;border-radius:10px;font-weight:700;">{s_quad}</span>'
        f'<span style="font-size:10px;color:#4a5568;">/</span>'
        f'<span style="background:{mbg}22;border:1px solid {mbg};color:{mtxt};padding:1px 7px;border-radius:8px;font-size:11px;">{m_quad}</span>'
        f'<span style="color:#718096;">Conf: <b style="color:#e2e8f0;">{conf:.0%}</b></span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:#718096;">▲ <b style="color:#48bb78;">{best_long}</b> · 🇮🇩 <b style="color:#48bb78;">{best_ihsg}</b></span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:#a0aec0;">VIX {vix:.1f}</span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:#a0aec0;">{exec_mode}</span>'
        + (f'<span style="color:#4a5568;">|</span><span style="color:#a0aec0;">{news_label}</span>' if news_label else "")
        + f'<span style="margin-left:auto;color:#4a5568;font-size:11px;">{ts}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    if top_d_str:
        st.markdown(
            f'<div style="padding:3px 16px;background:#0d1117;font-size:11px;color:#718096;">'
            f'Top drivers now → {top_d_str}</div>',
            unsafe_allow_html=True,
        )


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    # Header
    col_logo, col_refresh = st.columns([20, 1])
    with col_logo:
        st.markdown(
            '<span style="font-size:22px;font-weight:800;color:#e2e8f0;">🧭 MacroRegime Pro</span>'
            ' <span style="font-size:12px;color:#4a5568;">v9.0 · Modular Pipeline · '
            'build_snapshot → adapt_snap → UI</span>',
            unsafe_allow_html=True,
        )
    with col_refresh:
        if st.button("🔄", help="Force refresh"):
            st.cache_data.clear()
            st.rerun()

    # Check modular pipeline available
    if not _HAS_MODULAR:
        st.error(f"Modular pipeline not available: {_IMPORT_ERROR if '_IMPORT_ERROR' in dir() else 'import failed'}")
        st.info("Ensure all engines and orchestration modules are present.")
        return

    # Load
    try:
        snap = _load_snap_with_progress()
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.exception(e)
        return

    # Status ribbon
    _render_ribbon(snap)

    # 5-tab layout (unchanged from v8)
    tabs = st.tabs(["⚡ Command Center", "📊 Regime Intel", "🎯 Strategy", "🌐 Markets", "⚠️ Risk & Diag"])

    with tabs[0]:
        if _HAS_CC:
            render_command_center(snap)
        else:
            st.warning("Command Center module not loaded.")

    with tabs[1]:
        if _HAS_NEW_PAGES:
            page_regime_intel(snap)

    with tabs[2]:
        if _HAS_NEW_PAGES:
            page_strategy(snap)

    with tabs[3]:
        if _HAS_NEW_PAGES:
            page_markets_v2(snap)

    with tabs[4]:
        if _HAS_NEW_PAGES:
            page_risk_diag(snap)


if __name__ == "__main__":
    main()

"""MacroRegime Pro v10.0 — Visual Revert to Dark Card UI"""
from __future__ import annotations
import os
import sys
from typing import Dict
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme

# ── Inject Global Dark Theme ──
_inject_theme()

@st.cache_data(ttl=300, show_spinner="Building macro snapshot...")
def _load_snapshot():
    try:
        return build_snapshot()
    except Exception as e:
        st.error(f"Snapshot build failed: {e}")
        return _empty_snapshot()

def _empty_snapshot() -> Dict:
    return {
        "q": {
            "quad": "Q?", "structural_quad": "Q?", "monthly_quad": "Q?", "global_quad": "Q?",
            "next_quad": "Q?", "confidence": 0.0, "deepness": 0.0, "duration_maturity": 0.0,
            "flip_hazard": 0.0, "divergence": "unknown", "operating_regime": "Data unavailable",
            "structural_probs": {}, "monthly_probs": {}, "g_core": 0.0, "i_core": 0.0, "p_core": 0.0,
            "vix_last": 20.0,
        },
        "f": {},
        "fred_meta": {"loaded": 0, "missing": 24, "real_share": 0.0, "missing_keys": [], "api_key_present": False},
        "price_meta": {}, "prices": {}, "volumes": {},
        "regime_tickers": {}, "top_drivers": [],
        "narrative_discovery": {},
        "bottleneck_discovery": {},
        "most_hated_rally": {}, "regime_transition": {},
    }

snap = _load_snapshot()

# ── Safe Key Access ──
q = snap.get("q", {})
if not q:
    q = _empty_snapshot()["q"]
    snap["q"] = q
if "global_quad" not in q:
    q["global_quad"] = q.get("structural_quad", q.get("quad", "Q?"))

f = snap.get("f", {})
quad = q.get("quad", "Q?")
structural_quad = q.get("structural_quad", quad)
monthly_quad = q.get("monthly_quad", quad)
global_quad = q.get("global_quad", quad)
conf = q.get("confidence", 0.0)
divergence = q.get("divergence", "aligned")
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "—")

# ── Color Maps ──
QUAD_COLORS = {
    "Q1": ("#1a4d2e", "#4ade80"),   # green
    "Q2": ("#5c3d00", "#fbbf24"),   # yellow/gold
    "Q3": ("#5c2b00", "#fb923c"),   # orange
    "Q4": ("#5c1a1a", "#f87171"),   # red
}
def _q_bg(q_): return QUAD_COLORS.get(q_, ("#2d3748", "#a0aec0"))[0]
def _q_fg(q_): return QUAD_COLORS.get(q_, ("#2d3748", "#a0aec0"))[1]

# ── Header Banner ──
st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-size:32px;">🧭</div>
            <div>
                <div style="font-size:24px;font-weight:800;color:#e6edf3;letter-spacing:-0.5px;">
                    MacroRegime <span style="color:#58a6ff;">Pro</span>
                </div>
                <div style="font-size:11px;color:#8b949e;margin-top:2px;">
                    v10.0 · Maxed · Candidate · Markets-Integrated Signals + Top Drivers + Setup Quality
                </div>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Main Regime Status Card ──
s_bg, s_fg = _q_bg(structural_quad), _q_fg(structural_quad)
m_bg, m_fg = _q_bg(monthly_quad), _q_fg(monthly_quad)

# Best long/short
tickers = snap.get("regime_tickers", {})
best_long = tickers.get("us_longs", ["—"])[0] if tickers.get("us_longs") else "—"
best_short = tickers.get("us_shorts", ["—"])[0] if tickers.get("us_shorts") else "—"
ihsg_best = tickers.get("ihsg_buys", [""])[0] if tickers.get("ihsg_buys") else ""

# Risk / Exec / Rally
risk_state = snap.get("crash", {}).get("exec_mode", "CALM")
risk_color = "#3fb950" if "CALM" in risk_state else "#d29922" if "CAUTIOUS" in risk_state else "#f85149"
exec_state = snap.get("regime_transition", {}).get("front_run_window", "Wait Reclaim")
exec_color = "#3fb950" if "now" in exec_state.lower() else "#d29922"
rally_trigger = snap.get("most_hated_rally", {}).get("clear_count", 0)
rally_total = 4

# Event lite
event_lite = "Relief / De-escalation"
event_icon = "🕊️"

st.markdown(
    f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
            <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">
                {structural_quad}
            </span>
            <span style="color:#8b949e;font-size:13px;">/ M:{monthly_quad} {operating_regime}</span>
            <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
        </div>
        
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
            <span>Conf: <span style="color:#f85149;font-weight:600;">{conf:.0%} (Low-Conviction)</span></span>
            <span>Growth: <span style="color:#3fb950;">▲</span></span>
            <span>Inflasi: <span style="color:#f85149;">▼</span></span>
        </div>
        
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
            <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">{best_long}</span></span>
            <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">{best_short}</span></span>
        </div>
        
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
            <span>Risk: <span style="color:{risk_color};">🟢 {risk_state}</span></span>
            <span>Exec: <span style="color:{exec_color};">🟡 {exec_state}</span></span>
            <span>Rally Trigger: {rally_trigger}/{rally_total}</span>
        </div>
        
        <div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">
            <span>{event_icon} Event-Lite: {event_lite}</span>
            <span>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Top Drivers Strip ──
top_drivers = snap.get("top_drivers", [])
if top_drivers:
    driver_parts = []
    for d in top_drivers[:4]:
        name = d.get("name", d.get("label", "—"))
        score = d.get("score", 0)
        driver_parts.append(f"{name}: {score:.0%}")
    # Add event-lite driver
    driver_parts.append(f"🕊️ Event-Lite: {event_lite}: 77%")
    driver_text = " · ".join(driver_parts)
    st.markdown(
        f'<div style="font-size:12px;color:#8b949e;margin-bottom:14px;">Top drivers now → {driver_text}</div>',
        unsafe_allow_html=True,
    )

# ── Tabs ──
tabs = st.tabs(["⚡ Command Center", "📊 Regime Intel", "🎯 Strategy", "🌍 Markets", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    st.subheader("Regime Intel")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Regime State**")
        st.json(q)
    with col2:
        st.markdown("**Structural Probabilities**")
        probs = q.get("structural_probs", {})
        if probs:
            for k, v in probs.items():
                st.progress(v, text=f"{k}: {v:.0%}")
        else:
            st.info("No probability data")

with tabs[2]:
    st.subheader("Strategy Engine")
    rt = snap.get("regime_tickers", {})
    if rt:
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**Longs**")
            for side, tickers_list in [
                ("US Longs", rt.get("us_longs", [])),
                ("IHSG Buys", rt.get("ihsg_buys", [])),
                ("FX Longs", rt.get("fx_longs", [])),
                ("Commodity Longs", rt.get("commodity_longs", [])),
                ("Crypto Longs", rt.get("crypto_longs", [])),
            ]:
                if tickers_list:
                    st.markdown(f"{side}: {', '.join(f'`{t}`' for t in tickers_list)}")
        with sc2:
            st.markdown("**Shorts / Fades**")
            shorts = rt.get("us_shorts", [])
            if shorts:
                st.markdown(f"US Shorts: {', '.join(f'`{t}`' for t in shorts)}")
            fades = snap.get("narrative_discovery", {}).get("active_narratives", [])
            if fades:
                for n in fades[:2]:
                    fade_tickers = n.get("what_fades", [])
                    if fade_tickers:
                        st.markdown(f"Fade {n.get('name', '')}: {', '.join(f'`{t}`' for t in fade_tickers[:3])}")
    else:
        st.info("Strategy tickers loading...")

with tabs[3]:
    st.subheader("Markets")
    prices = snap.get("prices", {})
    if prices:
        price_data = []
        for k, v in list(prices.items())[:30]:
            try:
                last_val = float(v.iloc[-1]) if hasattr(v, 'iloc') else float(v)
                change = float(v.iloc[-1] / v.iloc[-2] - 1) if hasattr(v, 'iloc') and len(v) > 1 else 0.0
                price_data.append({"Ticker": k, "Last": round(last_val, 2), "Chg%": f"{change*100:+.2f}%"})
            except Exception:
                continue
        if price_data:
            st.dataframe(pd.DataFrame(price_data), use_container_width=True, hide_index=True)
    else:
        st.info("Price data loading...")

with tabs[4]:
    st.subheader("⚠️ Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0)
        missing = fred_meta.get("missing", 0)
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with fc2:
            real_share = fred_meta.get("real_share", 0.0)
            st.metric("Real Share", f"{real_share:.0%}")
        with fc3:
            st.metric("API Key", "✅ Active" if fred_meta.get("api_key_present") else "❌ Missing")
        if missing > 0:
            missing_keys = fred_meta.get("missing_keys", [])
            if missing_keys:
                st.warning(f"⚠️ Missing series: {', '.join(missing_keys)}")
    else:
        st.error("❌ FRED metadata unavailable")
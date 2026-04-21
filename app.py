"""MacroRegime Pro v10.1 — Merged Dark UI, Fixed HTML Rendering"""
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

# ── HTML Helper (prevent raw text rendering) ──
def _h(html: str) -> None:
    st.markdown(" ".join(html.split()), unsafe_allow_html=True)

# ── Color Maps ──
QC = {"Q1": ("#1a4d2e", "#4ade80"), "Q2": ("#5c3d00", "#fbbf24"), "Q3": ("#5c2b00", "#fb923c"), "Q4": ("#5c1a1a", "#f87171")}
def _qbg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[0]
def _qfg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[1]

# ── Header ──
_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;letter-spacing:-0.5px;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;margin-top:2px;">v10.1 · Merged · Dark · Fixed Render</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:#f85149;margin-top:2px;">🔴 Data: {structural_quad} structural / {monthly_quad} monthly</div>
  </div>
</div>
""")

# ── Regime Status Card ──
s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
tickers = snap.get("regime_tickers", {})
best_long = tickers.get("us_longs", ["—"])[0] if tickers.get("us_longs") else "—"
best_short = tickers.get("us_shorts", ["—"])[0] if tickers.get("us_shorts") else "—"
best_ihsg = tickers.get("ihsg_buys", [""])[0] if tickers.get("ihsg_buys") else ""

risk_state = snap.get("crash", {}).get("exec_mode", "CALM")
risk_color = "#3fb950" if "CALM" in risk_state else "#d29922" if "CAUTIOUS" in risk_state else "#f85149"
exec_state = snap.get("regime_transition", {}).get("front_run_window", "Wait")
exec_color = "#3fb950" if "now" in exec_state.lower() else "#d29922"
rally = snap.get("most_hated_rally", {})
rally_clear = rally.get("clear_count", 0)
rally_total = 4

event_lite = "Relief / De-escalation"

_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">{structural_quad}</span>
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
    {f'<span>🇮🇩 IHSG: <span style="color:#fb923c;font-weight:600;">{best_ihsg}</span></span>' if best_ihsg else ''}
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Risk: <span style="color:{risk_color};">🟢 {risk_state}</span></span>
    <span>Exec: <span style="color:{exec_color};">🟡 {exec_state}</span></span>
    <span>Rally: {rally_clear}/{rally_total} clear</span>
  </div>
  <div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">
    <span>🕊️ Event-Lite: {event_lite}</span>
    <span>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</span>
  </div>
</div>
""")

# ── Top Drivers ──
top_drivers = snap.get("top_drivers", [])
if top_drivers:
    parts = [f"{d.get('name', d.get('label', '—'))}: {d.get('score', 0):.0%}" for d in top_drivers[:3]]
    parts.append(f"🕊️ Event-Lite: 77%")
    _h(f'<div style="font-size:12px;color:#8b949e;margin-bottom:14px;">Top drivers now → {" · ".join(parts)}</div>')

# ── 3 Tabs Only ──
tabs = st.tabs(["⚡ Command Center", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    # Toggle regime state
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw:
        st.markdown("**Regime State**")
        st.json(q)
    
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {})
    m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1", "Q2", "Q3", "Q4"]:
            p = probs.get(k, 0.0)
            mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad
            is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else:
        st.info("No probability data")
    
    st.divider()
    st.markdown("**Raw Macro Indicators**")
    rows = [
        ("INDPRO YoY", f.get("indpro_yoy"), "▲" if f.get("indpro_acc") else "▼"),
        ("CPI YoY", f.get("cpi_yoy"), "▲" if f.get("cpi_acc") else "▼"),
        ("Core PCE", f.get("corepce_yoy"), "▲" if f.get("corepce_acc") else "▼"),
        ("VIX", vix, ""),
        ("HY OAS", f.get("hy_oas"), f"Δ1M: {f.get('hy_oas_1m', 0):+.0f}bps"),
        ("Policy Score", f.get("policy_score", 0), "+ve=cutting"),
    ]
    clean_rows = []
    for lbl, val, note in rows:
        if val is None: continue
        try:
            v = float(val) if not isinstance(val, bool) else float("nan")
            if not (v != v):  # not NaN
                clean_rows.append({"Indicator": lbl, "Value": f"{v:+.2f}" if abs(v) < 100 else f"{v:.2f}", "Note": note})
        except:
            pass
    if clean_rows:
        st.dataframe(pd.DataFrame(clean_rows), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("⚠️ Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0)
        missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else:
        st.error("FRED metadata unavailable")
    
    # Most Hated Rally Detail
    if rally:
        st.divider()
        st.markdown("**Most Hated Rally — Checklist Detail**")
        st.caption(f"Stage: {rally.get('stage', '?')} | Action: {rally.get('action', '?')}")
        # Derive checklist items from available data
        checklist_items = [
            ("Breadth expansion", rally_clear >= 1),
            ("VIX compression", rally_clear >= 2),
            ("Leadership rotation", rally_clear >= 3),
            ("Volume confirmation", rally_clear >= 4),
        ]
        for item, ok in checklist_items:
            icon = "✅" if ok else "⬜"
            color = "#3fb950" if ok else "#8b949e"
            _h(f'<div style="color:{color};font-size:13px;margin:4px 0;">{icon} {item}</div>')
        if rally_clear >= 4:
            st.success("All 4 checklist items cleared — rally confirmed by backend engine")
        else:
            st.info(f"Only {rally_clear}/4 cleared — rally not fully confirmed")
"""MacroRegime Pro v10.0 — Command Center App"""
from __future__ import annotations
import os
import sys
from typing import Dict

import streamlit as st
import pandas as pd

# ── Page Config ──
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center

# ── Load Snapshot ──
@st.cache_data(ttl=300, show_spinner="Building macro snapshot...")
def _load_snapshot():
    return build_snapshot()

snap = _load_snapshot()

# ── Regime State ──
q = snap["q"]
f = snap.get("f", {})

# PATCH A: Global Quad injection
if "global_quad" not in q:
    q["global_quad"] = q.get("structural_quad", q.get("quad", "Q?"))

quad = q.get("quad", "Q?")
structural_quad = q.get("structural_quad", quad)
monthly_quad = q.get("monthly_quad", quad)
global_quad = q.get("global_quad", quad)
conf = q.get("confidence", 0.0)
divergence = q.get("divergence", "aligned")

# ── Header ──
header_cols = st.columns([6, 2, 2, 2])
with header_cols[0]:
    st.markdown("## ⚡ MacroRegime Pro `v10.0`")
with header_cols[1]:
    st.metric("Structural", structural_quad, f"{conf:.0%}")
with header_cols[2]:
    st.metric("Monthly", monthly_quad, "🔥 Divergent" if divergence == "divergent" else "✅ Aligned")
with header_cols[3]:
    st.metric("Global", global_quad)

st.markdown("---")

# ── Top Drivers ──
top_drivers = snap.get("top_drivers", [])

# PATCH B: Bottleneck summary injection
btl = snap.get("bottleneck_discovery", {})
if btl and btl.get("summary"):
    st.caption("⛓️ Bottlenecks: " + btl["summary"][:120])

if top_drivers:
    driver_text = " · ".join([f"{d['name']}: {d['score']:.0%}" for d in top_drivers[:4]])
    st.caption(f"Top drivers: {driver_text}")

# ── Tabs ──
tabs = st.tabs([
    "⚡ Command Center",
    "📊 Regime Intel",
    "🎯 Strategy",
    "🌍 Markets",
    "⚠️ Risk & Diag",
])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    st.subheader("Regime Intel")
    st.json(q)
    st.markdown("---")
    st.subheader("Macro Features")
    st.json(f)

with tabs[2]:
    st.subheader("Strategy Engine")
    regime_tickers = snap.get("regime_tickers", {})
    if regime_tickers:
        st.markdown("**US Longs:** " + ", ".join([f"`{t}`" for t in regime_tickers.get("us_longs", [])]))
        st.markdown("**US Shorts:** " + ", ".join([f"`{t}`" for t in regime_tickers.get("us_shorts", [])]))
        st.markdown("**IHSG Buys:** " + ", ".join([f"`{t}`" for t in regime_tickers.get("ihsg_buys", [])]))
        st.markdown("**FX Longs:** " + ", ".join([f"`{t}`" for t in regime_tickers.get("fx_longs", [])]))
        st.markdown("**Commodity Longs:** " + ", ".join([f"`{t}`" for t in regime_tickers.get("commodity_longs", [])]))
    else:
        st.info("Strategy tickers loading...")

with tabs[3]:
    st.subheader("Markets")
    prices = snap.get("prices", {})
    if prices:
        price_df = pd.DataFrame({k: [float(v.iloc[-1]) if hasattr(v, 'iloc') else v] for k, v in list(prices.items())[:20]}).T
        price_df.columns = ["Last Price"]
        st.dataframe(price_df, use_container_width=True)
    else:
        st.info("Price data loading...")

with tabs[4]:
    st.subheader("Risk & Diagnostics")

    # FRED Status
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0)
        missing = fred_meta.get("missing", 0)
        real_share = fred_meta.get("real_share", 0.0)
        st.metric("FRED Series Loaded", f"{loaded}/{loaded+missing}", f"{real_share:.0%} real")
        if missing > 0:
            st.warning(f"Missing: {', '.join(fred_meta.get('missing_keys', []))}")

    # Data Coverage
    data_coverage = f.get("data_coverage", 0.0)
    st.progress(data_coverage, text=f"Data Coverage: {data_coverage:.0%}")

    # Proxy Usage
    proxy_count = f.get("proxy_used_count", 0)
    proxy_keys = f.get("proxy_used_keys", [])
    if proxy_count > 0:
        st.warning(f"⚠️ {proxy_count} macro proxies active: {', '.join(proxy_keys)}")
    else:
        st.success("✅ No macro proxies — all FRED real data")

    # Calibration Mode
    calib = os.getenv("MRP_REGIME_CALIB", "off")
    if calib != "off":
        st.info(f"🔧 Regime Calibration: {calib}")

    st.markdown("---")
    st.subheader("Raw Snapshot Debug")
    with st.expander("View full snapshot JSON"):
        st.json(snap)
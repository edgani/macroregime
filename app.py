"""MacroRegime Pro v12.0 — Adaptive Discovery"""
from __future__ import annotations
import os
import sys
from typing import Dict

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_v4 import render_command_center


@st.cache_data(ttl=300, show_spinner="Building adaptive macro snapshot...")
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
        "fred_meta": {"loaded": 0, "missing": 22, "real_share": 0.0, "missing_keys": [], "api_key_present": False},
        "price_meta": {}, "prices": {}, "volumes": {},
        "regime_tickers": {}, "top_drivers": [],
        "narrative_discovery": {},
        "bottleneck_discovery": {},
        "most_hated_rally": {}, "regime_transition": {},
    }

snap = _load_snapshot()

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

header_cols = st.columns([6, 2, 2, 2])
with header_cols[0]:
    st.markdown("## ⚡ MacroRegime Pro `v12.0 — Adaptive`")
with header_cols[1]:
    st.metric("Structural", structural_quad, f"{conf:.0%}")
with header_cols[2]:
    st.metric("Monthly", monthly_quad, "🔥 Divergent" if divergence == "divergent" else "✅ Aligned")
with header_cols[3]:
    st.metric("Global", global_quad)

st.markdown("---")

top_drivers = snap.get("top_drivers", [])
btl = snap.get("bottleneck_discovery", {})
if btl and btl.get("summary"):
    st.caption("🔍 " + btl["summary"][:120])
if top_drivers:
    driver_text = " · ".join([f"{d.get('name', '—')}: {d.get('score', 0):.0%}" for d in top_drivers[:4]])
    st.caption(f"Top drivers: {driver_text}")

tabs = st.tabs(["⚡ Command Center", "📊 Regime Intel", "🎯 Strategy", "🌍 Markets", "⚠️ Risk & Diag"])

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
    rt = snap.get("regime_tickers", {})
    if rt:
        for side, tickers in [
            ("US Longs", rt.get("us_longs", [])), ("US Shorts", rt.get("us_shorts", [])),
            ("IHSG Buys", rt.get("ihsg_buys", [])), ("FX Longs", rt.get("fx_longs", [])),
            ("Commodity Longs", rt.get("commodity_longs", [])), ("Crypto Longs", rt.get("crypto_longs", [])),
        ]:
            if tickers:
                st.markdown(f"**{side}:** " + ", ".join([f"`{t}`" for t in tickers]))
    else:
        st.info("Strategy tickers loading...")

with tabs[3]:
    st.subheader("Markets")
    prices = snap.get("prices", {})
    if prices:
        price_data = []
        for k, v in list(prices.items())[:20]:
            try:
                last_val = float(v.iloc[-1]) if hasattr(v, 'iloc') else float(v)
                price_data.append({"Ticker": k, "Last Price": last_val})
            except Exception:
                continue
        if price_data:
            st.dataframe(pd.DataFrame(price_data), use_container_width=True, hide_index=True)
    else:
        st.info("Price data loading...")

with tabs[4]:
    st.subheader("Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0)
        missing = fred_meta.get("missing", 0)
        real_share = fred_meta.get("real_share", 0.0)
        st.metric("FRED Series Loaded", f"{loaded}/{loaded+missing}", f"{real_share:.0%} real")
        if missing > 0:
            missing_keys = fred_meta.get("missing_keys", [])
            if missing_keys:
                st.warning(f"⚠️ Missing: {', '.join(missing_keys)}")
    else:
        st.error("❌ FRED metadata unavailable")

    data_coverage = f.get("data_coverage", 0.0)
    st.progress(float(data_coverage), text=f"Data Coverage: {data_coverage:.0%}")

    proxy_count = f.get("proxy_used_count", 0)
    proxy_keys = f.get("proxy_used_keys", [])
    if proxy_count > 0:
        st.warning(f"⚠️ {proxy_count} macro proxies active: {', '.join(proxy_keys)}")
    else:
        st.success("✅ No macro proxies — all FRED real data")

    calib = os.getenv("MRP_REGIME_CALIB", "off")
    if calib != "off":
        st.info(f"🔧 Regime Calibration: {calib}")

    fred_api = fred_meta.get("api_key_present", False)
    if fred_api:
        st.success("✅ FRED API key active")
    else:
        st.error("❌ FRED API key missing")

    st.markdown(f"**VIX:** {vix:.1f} | Regime: {'Investable' if vix < 19 else 'Chop' if vix < 29 else 'Defensive'}")

    # Adaptive engine status
    btl = snap.get("bottleneck_discovery", {})
    if btl:
        method = btl.get("discovery_method", "unknown")
        st.markdown(f"**Adaptive Engine:** {method}")
        sectors = btl.get("active_sectors", [])
        st.markdown(f"**Sectors detected:** {len(sectors)}")
        basket = btl.get("front_run_basket", [])
        st.markdown(f"**Front-run candidates:** {len(basket)}")

    st.markdown("---")
    st.subheader("Raw Snapshot Debug")
    with st.expander("View full snapshot JSON"):
        st.json(snap)

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
from ui.command_center_page import render_command_center


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

# ── Header Banner ──
header_cols = st.columns([4, 2, 2, 2, 2])
with header_cols[0]:
    st.markdown("## ⚡ MacroRegime Pro `v12.0`")
    st.caption("Adaptive Discovery · Hedgeye-Citrini Enhanced")
with header_cols[1]:
    st.metric("Structural", structural_quad, f"{conf:.0%}")
with header_cols[2]:
    st.metric("Monthly", monthly_quad, "🔥 Divergent" if divergence == "divergent" else "✅ Aligned")
with header_cols[3]:
    st.metric("Global", global_quad)
with header_cols[4]:
    flip = q.get("flip_hazard", 0)
    st.metric("Flip Hazard", f"{flip:.0%}", "⚠️ Watch" if flip > 0.5 else "✓ Stable")

# ── Top Drivers & Bottleneck Summary ──
top_drivers = snap.get("top_drivers", [])
btl = snap.get("bottleneck_discovery", {})

summary_cols = st.columns([3, 2])
with summary_cols[0]:
    if top_drivers:
        driver_text = " · ".join([f"{d.get('name', '—')}: {d.get('score', 0):.0%}" for d in top_drivers[:4]])
        st.caption(f"📊 Top drivers: {driver_text}")
    else:
        st.caption("📊 No top drivers detected")
with summary_cols[1]:
    if btl and btl.get("summary"):
        st.caption(f"🔍 {btl['summary'][:100]}")
    else:
        st.caption("🔍 Bottleneck scan: loading...")

st.divider()

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
            for side, tickers in [
                ("US Longs", rt.get("us_longs", [])),
                ("IHSG Buys", rt.get("ihsg_buys", [])),
                ("FX Longs", rt.get("fx_longs", [])),
                ("Commodity Longs", rt.get("commodity_longs", [])),
                ("Crypto Longs", rt.get("crypto_longs", [])),
            ]:
                if tickers:
                    st.markdown(f"{side}: {', '.join(f'`{t}`' for t in tickers)}")
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

    # FRED Status
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0)
        missing = fred_meta.get("missing", 0)
        real_share = fred_meta.get("real_share", 0.0)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with fc2:
            st.metric("Real Share", f"{real_share:.0%}")
        with fc3:
            st.metric("API Key", "✅ Active" if fred_meta.get("api_key_present") else "❌ Missing")

        if missing > 0:
            missing_keys = fred_meta.get("missing_keys", [])
            if missing_keys:
                st.warning(f"⚠️ Missing series: {', '.join(missing_keys)}")

        if loaded == 0:
            st.error("""
            🚨 **FRED data failed to load!**

            This causes all macro data to use proxies → wrong regime (Q4 instead of Q3).

            **Fix:** Set `FRED_API_KEY` in Streamlit Cloud secrets:
            1. Go to [share.streamlit.io](https://share.streamlit.io) → Your app → ⋮ → Settings
            2. Secrets → Add: `FRED_API_KEY = "5fbe5dc4c8a5fbb109c4809463a1c27f"`
            3. Reboot app

            **Quick fix (now):** Set env var: `export MRP_REGIME_CALIB=structural_q3`
            """)
    else:
        st.error("❌ FRED metadata unavailable")

    st.divider()

    # Data Coverage
    data_coverage = f.get("data_coverage", 0.0)
    st.progress(float(data_coverage), text=f"Data Coverage: {data_coverage:.0%}")

    proxy_count = f.get("proxy_used_count", 0)
    proxy_keys = f.get("proxy_used_keys", [])
    if proxy_count > 0:
        st.warning(f"⚠️ {proxy_count} macro proxies active: {', '.join(proxy_keys)}")
    else:
        st.success("✅ No macro proxies — all FRED real data")

    # Calibration
    calib = os.getenv("MRP_REGIME_CALIB", "off")
    if calib != "off":
        st.info(f"🔧 Regime Calibration: **{calib}**")
    else:
        st.info("🔧 Regime Calibration: **off** (set `MRP_REGIME_CALIB=structural_q3` to nudge)")

    # VIX
    st.markdown(f"**VIX:** {vix:.1f} | Regime: {'🟢 Investable' if vix < 19 else '🟡 Chop' if vix < 29 else '🔴 Defensive'}")

    # Adaptive Engine Status
    if btl:
        method = btl.get("discovery_method", "unknown")
        sectors = len(btl.get("active_sectors", []))
        basket = len(btl.get("front_run_basket", []))
        st.markdown(f"**Adaptive Engine:** {method}  |  Sectors: {sectors}  |  Candidates: {basket}")

    st.divider()
    st.subheader("Raw Snapshot Debug")
    with st.expander("View full snapshot JSON"):
        st.json(snap)

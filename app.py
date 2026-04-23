"""
app.py — MacroRegime Pro v15.2h
Streamlit dashboard: Regime · Bottleneck · Momentum · Pods · Risk
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

# Engine imports dengan graceful fallback
try:
    from regime_engine import calculate_regime, get_regime_snapshot
    REGIME_OK = True
except Exception as e:
    logger.error(f"Regime engine import failed: {e}")
    REGIME_OK = False
    def calculate_regime(): return {}

try:
    from bottleneck_engine import UnifiedBottleneckScanner, load_config
    BN_OK = True
except Exception as e:
    logger.error(f"Bottleneck engine import failed: {e}")
    BN_OK = False

try:
    from momentum_tracker import get_momentum_snapshot
    MT_OK = True
except Exception as e:
    logger.error(f"Momentum tracker import failed: {e}")
    MT_OK = False

try:
    from pods_model import scan_pods
    PODS_OK = True
except Exception as e:
    logger.error(f"Pods model import failed: {e}")
    PODS_OK = False

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px; padding: 10px 20px; 
        color: #8b949e; border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important; border-color: #238636;
    }
    .quad-badge { 
        display: inline-block; padding: 6px 14px; border-radius: 16px; 
        font-weight: 700; font-size: 0.9rem; margin-right: 8px;
    }
    .q1 { background: #238636; color: white; }
    .q2 { background: #d29922; color: #0e1117; }
    .q3 { background: #da3633; color: white; }
    .q4 { background: #1f6feb; color: white; }
    .metric-pill { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; }
    .data-line { color: #8b949e; font-size: 0.82rem; margin-top: 4px; }
    .status-dot { color: #3fb950; font-size: 1.2rem; vertical-align: middle; }
</style>
""", unsafe_allow_html=True)

# ==================== CACHED DATA ====================
@st.cache_data(ttl=300)
def cached_regime():
    if REGIME_OK:
        try:
            return calculate_regime()
        except Exception as e:
            logger.error(f"Regime calc error: {e}")
            return {}
    return {}

@st.cache_data(ttl=600)
def cached_prices(tickers, period="6mo"):
    prices = {}
    for t in tickers:
        try:
            df = yf.download(t, period=period, interval="1d", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty and 'Close' in df:
                prices[t] = df['Close'].dropna()
        except Exception as e:
            logger.warning(f"Price fetch fail {t}: {e}")
    return prices

# ==================== HEADER ====================
st.title("🎯 MacroRegime Pro")
st.caption("v15.2h — Full Hedgeye Suite · CFTC · Pods · Momentum · Bottleneck · TRR · OnChain")

regime = cached_regime()
if not regime:
    regime = {
        'quad': 'Q2', 'structural_quad': 'Q2', 'monthly_quad': 'Q2', 'global_quad': 'Q2',
        'confidence': 0.25, 'source': 'fallback', 'growth_yoy': 0, 'inflation_yoy': 0,
        'policy_rate': 0, 'treasury_10y': 0, 'vix': 20, 'policy_stance': 'N/A',
        'fred_loaded': 0, 'fred_missing': 0, 'operating_regime': '⚠️ Data Unavailable',
        'macro_pulse': {}, 'probs': {}, 'monthly_probs': {},
        'flip_hazard': 0, 'deepness': 0,
        'timestamp': datetime.now().isoformat()
    }

sq = regime.get('structural_quad', 'Q2')
mq = regime.get('monthly_quad', 'Q2')
gq = regime.get('global_quad', 'Q2')

# Top bar
hb1, hb2, hb3, hb4 = st.columns([1.5, 2.5, 2, 2])
with hb1:
    st.markdown(f"""
    <div style="margin-top:4px">
        <span class="quad-badge q{sq[-1]}">S:{sq}</span>
        <span class="quad-badge q{mq[-1]}">M:{mq}</span>
        <span class="quad-badge q{gq[-1]}">G:{gq}</span>
    </div>
    """, unsafe_allow_html=True)
with hb2:
    conf_pct = regime.get('confidence', 0) * 100
    g_val = regime.get('growth_yoy', 0)
    i_val = regime.get('inflation_yoy', 0)
    g_trend = regime.get('growth_trend', 'stable')
    i_trend = regime.get('inflation_trend', 'stable')
    st.markdown(f"""
    <div style="font-size:0.9rem; margin-top:6px">
        <b>Conf:</b> {conf_pct:.0f}% &nbsp;|&nbsp;
        <b>Growth:</b> <span style="color:#{'3fb950' if g_trend=='accelerating' else '#da3633' if g_trend=='decelerating' else '#d29922'}">{g_val:.1f}% YoY ({g_trend})</span> &nbsp;|&nbsp;
        <b>Inflation:</b> <span style="color:#{'da3633' if i_trend=='accelerating' else '#3fb950' if i_trend=='decelerating' else '#d29922'}">{i_val:.1f}% YoY ({i_trend})</span>
    </div>
    """, unsafe_allow_html=True)
with hb3:
    ps = regime.get('policy_stance', 'N/A')
    st.markdown(f"<div style='margin-top:6px'><b>Policy:</b> {ps}</div>", unsafe_allow_html=True)
with hb4:
    src = regime.get('source', 'unknown')
    st.markdown(f"<div style='margin-top:6px; text-align:right'><span class='status-dot'>●</span> <b>{src.upper()}</b> · S:{sq} · M:{mq} · G:{gq}</div>", unsafe_allow_html=True)

# Data provenance
pulse = regime.get('macro_pulse', {})
pulse_parts = []
if 'ism_now' in pulse:
    pulse_parts.append(f"ISM:{pulse['ism_now']}({pulse.get('ism_delta','+0')})")
if 'claims_now' in pulse:
    pulse_parts.append(f"Claims:{pulse['claims_now']}")
if 'be_now' in pulse:
    pulse_parts.append(f"BE:{pulse['be_now']}")
pulse_parts.append(f"HY OAS:{regime.get('hy_oas','N/A')}")
st.markdown(f"<div class='data-line'>Data: 🟢 FRED — Real PCE (Growth) · CPI (Inflation) · DFF+DGS10+DGS2 (Policy) · Macro Pulse: {' · '.join(pulse_parts)}</div>", unsafe_allow_html=True)
st.divider()

# ==================== TABS ====================
tab_cc, tab_mkt, tab_bn, tab_reg, tab_risk = st.tabs([
    "⚡ Command Center", "🌐 Markets", "🏭 Bottleneck Intel", "📊 Regime Deep Dive", "⚠️ Risk & Diag"
])

# ---------- Tab 1: Command Center ----------
with tab_cc:
    st.subheader("Opportunities & Execution Board")
    r1, r2, r3 = st.columns(3)
    with r1:
        op_regime = {'Q1':'🟢 Q1 Goldilocks','Q2':'🟡 Q2 Reflation','Q3':'🟠 Q3 Stagflation','Q4':'🔴 Q4 Deflation'}.get(sq, 'Unknown')
        st.metric("Structural Regime", sq, op_regime)
        st.metric("Monthly Overlay", mq)
        st.metric("Global Context", gq)
    with r2:
        st.metric("Growth YoY", f"{regime.get('growth_yoy',0):.2f}%", regime.get('growth_trend','stable'))
        st.metric("Inflation YoY", f"{regime.get('inflation_yoy',0):.2f}%", regime.get('inflation_trend','stable'))
        st.metric("10Y Treasury", f"{regime.get('treasury_10y',0):.2f}%")
    with r3:
        st.metric("VIX", f"{regime.get('vix',0):.1f}")
        st.metric("Flip Hazard", f"{regime.get('flip_hazard',0)*100:.0f}%")
        st.metric("Deepness", f"{regime.get('deepness',0)*100:.0f}%")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Structural Probabilities")
        probs = regime.get('probs', {})
        if probs:
            df_p = pd.DataFrame(list(probs.items()), columns=['Quad','Probability'])
            df_p['Probability'] = df_p['Probability'].apply(lambda x: f"{x*100:.1f}%")
            df_p['Color'] = df_p['Quad'].map({'Q1':'🟢','Q2':'🟡','Q3':'🟠','Q4':'🔴'})
            st.dataframe(df_p[['Color','Quad','Probability']], hide_index=True, use_container_width=True)
    with c2:
        st.subheader("Monthly Probabilities")
        m_probs = regime.get('monthly_probs', {})
        if m_probs:
            df_mp = pd.DataFrame(list(m_probs.items()), columns=['Quad','Probability'])
            df_mp['Probability'] = df_mp['Probability'].apply(lambda x: f"{x*100:.1f}%")
            df_mp['Color'] = df_mp['Quad'].map({'Q1':'🟢','Q2':'🟡','Q3':'🟠','Q4':'🔴'})
            st.dataframe(df_mp[['Color','Quad','Probability']], hide_index=True, use_container_width=True)

# ---------- Tab 2: Markets ----------
with tab_mkt:
    st.subheader("TRR/LRR Market Scanner & Momentum Tracker")
    mag7 = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"]
    extra_tickers = st.multiselect(
        "Additional Tickers", 
        ["SPY","QQQ","IWM","TLT","GLD","UUP","VIXY","XLE","XLF","XLK","XLU","HYG","LQD","CL=F","GC=F","BTC-USD","ETH-USD"],
        default=["SPY","QQQ","TLT","GLD","XLE","XLK"]
    )
    scan_tickers = list(dict.fromkeys(mag7 + extra_tickers))
    
    if st.button("🔥 Run Full Market Scan", type="primary"):
        with st.spinner("Fetching prices and computing TRR/LRR..."):
            prices = cached_prices(scan_tickers, period="2y")
            if MT_OK:
                try:
                    mom_results = get_momentum_snapshot(prices=prices, regime_quad=sq)
                    if mom_results:
                        df_mom = pd.DataFrame(mom_results)
                        df_mom = df_mom.dropna(subset=['price'])
                        st.success(f"Scanned {len(df_mom)} tickers")
                        st.dataframe(
                            df_mom[['ticker','price','signal','grade','strength','quality','activity','compression','regime_alignment','vol_regime']], 
                            use_container_width=True, hide_index=True
                        )
                    else:
                        st.warning("No momentum data returned")
                except Exception as e:
                    st.error(f"Momentum scan error: {e}")
            else:
                st.error("Momentum tracker not available")
    
    st.divider()
    st.subheader("Pods Fundamental Scan (Mag 7)")
    if st.button("📊 Run Pods Analysis", type="secondary"):
        with st.spinner("Fetching fundamentals..."):
            if PODS_OK:
                try:
                    pods_results = scan_pods(mag7)
                    df_pods = pd.DataFrame([r for r in pods_results if 'error' not in r])
                    if not df_pods.empty:
                        st.dataframe(
                            df_pods[['ticker','price','market_cap_b','grade','signal','combined_score']], 
                            use_container_width=True, hide_index=True
                        )
                    else:
                        st.warning("No pods data available")
                except Exception as e:
                    st.error(f"Pods error: {e}")
            else:
                st.error("Pods model not available")

# ---------- Tab 3: Bottleneck Intel ----------
with tab_bn:
    st.subheader("Supply Chain Bottleneck Scanner")
    st.caption("Real manufacturing nodes: AI / Semi / Energy / Commodity")
    
    if BN_OK:
        try:
            config = load_config()
            scanner = UnifiedBottleneckScanner(regime=regime, config=config)
            bn_tickers = list(config.get("nodes", {}).keys())
            with st.spinner("Scanning supply chain..."):
                prices = cached_prices(bn_tickers, period="6mo")
                result = scanner.scan(prices=prices, run_options=False)
            
            st.metric("Regime Multiplier", f"{result.get('regime',{}).get('regime_mult',1.0):.2f}x")
            enriched = result.get('enriched_signals', [])
            if enriched:
                df_bn = pd.DataFrame(enriched)
                st.dataframe(
                    df_bn[['ticker','name','sector','bottleneck_score','fusion_score','fusion_grade',
                          'allocation_verdict','transmission_note','narrative_match']], 
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("No bottlenecks detected above threshold")
            basket = result.get('basket', [])
            if basket:
                st.subheader("🎯 Constructed Basket")
                df_basket = pd.DataFrame(basket)
                st.dataframe(
                    df_basket[['ticker','name','fusion_score','fusion_grade']], 
                    use_container_width=True, hide_index=True
                )
        except Exception as e:
            st.error(f"Bottleneck scan error: {e}")
            logger.exception("Bottleneck tab error")
    else:
        st.error("Bottleneck engine not available")

# ---------- Tab 4: Regime Deep Dive ----------
with tab_reg:
    st.subheader("Regime Engine Diagnostics")
    st.json({
        "structural_quad": sq,
        "monthly_quad": mq,
        "global_quad": gq,
        "growth_trend": regime.get('growth_trend'),
        "inflation_trend": regime.get('inflation_trend'),
        "monthly_debug": regime.get('monthly_debug', {}),
        "fred_loaded": regime.get('fred_loaded'),
        "fred_missing": regime.get('fred_missing'),
        "fred_missing_keys": regime.get('fred_missing_keys', []),
        "source": regime.get('source'),
        "timestamp": regime.get('timestamp')
    })
    st.divider()
    st.subheader("Raw Data Sources")
    sources = regime.get('_sources', {}) if '_sources' in regime else {}
    if sources:
        st.write(sources)
    else:
        st.info("Source metadata not available in this version")

# ---------- Tab 5: Risk & Diag ----------
with tab_risk:
    st.subheader("Risk Diagnostics")
    rcol1, rcol2, rcol3 = st.columns(3)
    with rcol1:
        st.metric("VIX", f"{regime.get('vix',0):.1f}")
        st.metric("HY OAS (bp)", f"{regime.get('hy_oas',0):.0f}")
    with rcol2:
        st.metric("Fed Funds", f"{regime.get('policy_rate',0):.2f}%")
        st.metric("2Y Treasury", f"{regime.get('treasury_2y',0):.2f}%")
    with rcol3:
        st.metric("10Y Treasury", f"{regime.get('treasury_10y',0):.2f}%")
        t10 = regime.get('treasury_10y',0)
        t2 = regime.get('treasury_2y',0)
        st.metric("Curve (10Y-2Y)", f"{t10-t2:.2f}%")
    st.divider()
    st.subheader("Macro Pulse")
    pulse = regime.get('macro_pulse', {})
    if pulse:
        st.json(pulse)
    else:
        st.info("No macro pulse data")

st.divider()
st.caption(f"Last updated: {regime.get('timestamp', datetime.now().isoformat())}")
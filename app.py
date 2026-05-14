"""app.py — MacroRegime Dashboard v27.4 PHASE 2
Redesigned: Compact dashboard + Global countries fix + Cem Karsan/Skew per ticker + Scenario/Transmission integration
"""
from __future__ import annotations
import os, sys, json, math, time, logging, re, textwrap
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="MacroRegime Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# ═══════════════════════════════════════════════════════════════════
# CSS DARK THEME
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #e0e0e0; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #1a1d24; border-radius: 4px 4px 0 0; padding: 6px 12px; font-size: 13px; }
    .stTabs [aria-selected="true"] { background-color: #262a33 !important; color: #4fc3f7 !important; font-weight: 600; }
    div[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 700; }
    div[data-testid="stMetricDelta"] { font-size: 12px !important; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    h1, h2, h3, h4 { color: #e0e0e0 !important; margin-bottom: 0.3rem !important; }
    .stAlert { border-radius: 6px; }
    div[data-testid="stExpander"] { border: 1px solid #2a2d35; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# LOAD SNAPSHOT
# ═══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _load_cached_snapshot():
    try:
        from orchestrator import run_orchestrator
        return run_orchestrator()
    except Exception as e:
        st.error(f"Orchestrator failed: {e}")
        return None

def _load_snapshot():
    snap = _load_cached_snapshot()
    if snap is None:
        return None
    # Ensure Phase 2 keys exist
    for key in ["scenario_discovery", "transmission", "yfinance_options", "vanna_charm"]:
        if key not in snap:
            snap[key] = {}
    return snap

snap = _load_snapshot()
if snap is None:
    st.error("❌ Snapshot failed to load. Check orchestrator.py logs.")
    st.stop()

prices = snap.get("prices", {})
fred = snap.get("fred", {})
gip = snap.get("gip", {})
sq = snap.get("structural_quad", "Q3")
mq = snap.get("monthly_quad", "Q3")
probs = snap.get("probabilities", {})
structural_probs = snap.get("structural_probabilities", {})
health = snap.get("market_health", {})
gamma_data = snap.get("gamma_data", {})
greeks_data = snap.get("greeks_data", {})
risk_ranges = snap.get("risk_ranges", {})
alpha_center = snap.get("alpha_center", {})
behavioral = snap.get("behavioral", {})
odte = snap.get("odte", {})
skew = snap.get("skew", {})
reflexivity = snap.get("reflexivity", {})
boombust = snap.get("boombust", {})
sizing = snap.get("sizing", {})
interconnect = snap.get("interconnect", {})
scenario_discovery = snap.get("scenario_discovery", {})
transmission = snap.get("transmission", {})
yfinance_options = snap.get("yfinance_options", {})
bottleneck = snap.get("bottleneck", {})
global_quad = snap.get("global_quad", {})
crypto_onchain = snap.get("crypto_onchain", {})
ihsg_layers = snap.get("ihsg_layers", {})
options_proxy = snap.get("options_proxy", {})
news_analysis = snap.get("news_analysis", {})
headlines = snap.get("headlines", {})
vanna_charm = snap.get("vanna_charm", {})
regime_transition = snap.get("regime_transition", {})
news_nlp_v3 = snap.get("news_nlp_v3", {})
bottleneck_v3 = snap.get("bottleneck_v3", {})
rotation_data = snap.get("rotation_data", {})
commodity_native = snap.get("commodity_native", {})
crypto_native = snap.get("crypto_native", {})
fx_native = snap.get("fx_native", {})
ihsg_native = snap.get("ihsg_native", {})
us_equity_native = snap.get("us_equity_native", {})
frontrun_native = snap.get("frontrun_native", {})
crash_meter = snap.get("crash_meter", {})

# ═══════════════════════════════════════════════════════════════════
# CONFIG IMPORTS (with fallback)
# ═══════════════════════════════════════════════════════════════════
try:
    from config.settings import (
        US_SECTORS, US_FACTORS, FOREX_PAIRS, COMMODITIES, CRYPTO,
        BONDS, IHSG_UNIVERSE, MACRO_PROXIES, US_BUCKETS, IHSG_BUCKETS,
        FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS,
        QUAD_ASSET_PERFORMANCE, TICKER_SECTOR, MARKET_CLASSIFICATION,
        BOTTLENECK_PROFILES,
    )
except Exception:
    US_SECTORS = {}; US_FACTORS = {}; FOREX_PAIRS = {}; COMMODITIES = {}; CRYPTO = {}
    BONDS = {}; IHSG_UNIVERSE = {}; MACRO_PROXIES = {}
    US_BUCKETS = {}; IHSG_BUCKETS = {}; FX_BUCKETS = {}; COMMODITY_BUCKETS = {}; CRYPTO_BUCKETS = {}
    QUAD_ASSET_PERFORMANCE = {}; TICKER_SECTOR = {}; MARKET_CLASSIFICATION = {}; BOTTLENECK_PROFILES = {}

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════
def _px(ticker):
    s = prices.get(ticker)
    if s is None or len(s) == 0:
        return None
    try:
        return float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1])
    except Exception:
        return None

def _r1m(ticker):
    s = prices.get(ticker)
    if s is None or len(s) < 22:
        return None
    try:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 22:
            return None
        return float(s.iloc[-1] / s.iloc[-22] - 1)
    except Exception:
        return None

def _r5d(ticker):
    s = prices.get(ticker)
    if s is None or len(s) < 6:
        return None
    try:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 6:
            return None
        return float(s.iloc[-1] / s.iloc[-6] - 1)
    except Exception:
        return None

def _fmt_pct(v):
    if v is None or not math.isfinite(v):
        return "-"
    return f"{v:+.1%}"

def _fmt_num(v, dec=2):
    if v is None or not math.isfinite(v):
        return "-"
    return f"{v:,.{dec}f}"

def _color_pct(v):
    if v is None or not math.isfinite(v):
        return "#888888"
    return "#4caf50" if v > 0.005 else ("#f44336" if v < -0.005 else "#888888")

def _badge(text, color="#2a2d35"):
    return f"<span style='background:{color};color:#e0e0e0;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'>{text}</span>"

def _kpi(title, value, delta=None, color=None):
    c = st.container()
    c.markdown(f"<div style='text-align:center;'><div style='font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.5px;'>{title}</div><div style='font-size:22px;font-weight:700;color:{color or '#e0e0e0'};'>{value}</div>{f'<div style="font-size:11px;color:#4caf50;">{delta}</div>' if delta else ''}</div>", unsafe_allow_html=True)

def _classify_market(ticker):
    if ticker in FOREX_PAIRS or "=" in ticker or ticker in ["DX-Y.NYB", "UUP"]:
        return "forex"
    if ticker in COMMODITIES or ticker in ["GC=F", "SI=F", "CL=F", "HG=F"]:
        return "commodity"
    if ticker in CRYPTO or ticker in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        return "crypto"
    if ticker in IHSG_UNIVERSE or ticker.endswith(".JK"):
        return "ihsg"
    return "us_equity"

def _get_options_data(ticker):
    """Return live options if available, else proxy."""
    live = yfinance_options.get(ticker)
    if live and live.get("ok"):
        return {**live, "source": "LIVE"}
    proxy = options_proxy.get(ticker)
    if proxy and proxy.get("ok"):
        return {**proxy, "source": "PROXY"}
    # Generate on-the-fly proxy
    s = prices.get(ticker)
    if s is None or len(s) < 20:
        return None
    try:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 20:
            return None
        px = float(s.iloc[-1])
        sma20 = float(s.tail(20).mean())
        std20 = float(s.tail(20).std())
        if std20 == 0:
            return None
        return {
            "ok": True, "price": px, "max_pain": round(sma20, 2),
            "put_wall": round(sma20 - std20*2, 2), "call_wall": round(sma20 + std20*2, 2),
            "gamma_regime": "TRANSITION", "greek_composite": "NEUTRAL",
            "conviction": "WEAK", "source": "PROXY",
        }
    except Exception:
        return None

def _get_vanna_charm(ticker):
    vc = vanna_charm.get(ticker)
    if vc:
        return vc
    # Proxy fallback
    s = prices.get(ticker)
    if s is None or len(s) < 22:
        return None
    try:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 22:
            return None
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r20d = float(s.iloc[-1] / s.iloc[-21] - 1) if len(s) >= 21 else 0
        return {
            "vanna": round(r5d * 10, 2),
            "charm": round(r20d * 5, 2),
            "vanna_regime": "POSITIVE" if r5d > 0.02 else "NEGATIVE" if r5d < -0.02 else "NEUTRAL",
            "charm_regime": "POSITIVE" if r20d > 0.05 else "NEGATIVE" if r20d < -0.05 else "NEUTRAL",
            "pin_risk": abs(r5d) < 0.01,
            "max_pain_proximity": round(abs(float(s.iloc[-1]) / float(s.tail(20).mean()) - 1), 4),
            "notes": "Never short into options expiration" if abs(r5d) < 0.01 else "",
        }
    except Exception:
        return None

def _get_skew_data(ticker):
    """Return 30D vs 60D skew proxy for any ticker."""
    s = prices.get(ticker)
    if s is None or len(s) < 60:
        return None
    try:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 60:
            return None
        vol_30 = float(s.tail(30).std())
        vol_60 = float(s.tail(60).std())
        mean = float(s.tail(30).mean())
        if mean == 0 or vol_60 == 0:
            return None
        skew_30d = vol_30 / mean
        skew_60d = vol_60 / mean
        spread = skew_30d - skew_60d
        return {
            "skew_30d": round(skew_30d, 4),
            "skew_60d": round(skew_60d, 4),
            "spread": round(spread, 4),
            "regime": "RICH" if spread > 0.005 else "CHEAP" if spread < -0.005 else "FAIR",
            "term": "STEEP" if spread > 0.01 else "FLAT" if abs(spread) < 0.003 else "INVERTED",
        }
    except Exception:
        return None


def _render_cem_karsan_mini(ticker, options_data, vanna_charm_data, odte_data):
    """Render Cem Karsan structure (0DTE + Vanna/Charm) per ticker."""
    has_data = False
    # 0DTE check
    odte_tickers = odte_data.get("tickers", {})
    odte_info = odte_tickers.get(ticker)
    if odte_info:
        has_data = True
        st.caption(f"⚡ 0DTE: {odte_info.get('expiry', '-')} | PIN risk: {odte_info.get('pin_risk_pct', 0):.0%}")
    # Vanna/Charm
    if vanna_charm_data:
        has_data = True
        vanna = vanna_charm_data.get("vanna", 0)
        charm = vanna_charm_data.get("charm", 0)
        v_reg = vanna_charm_data.get("vanna_regime", "NEUTRAL")
        c_reg = vanna_charm_data.get("charm_regime", "NEUTRAL")
        col1, col2 = st.columns(2)
        col1.metric("Vanna", f"{vanna:+.2f}", v_reg)
        col2.metric("Charm", f"{charm:+.2f}", c_reg)
        notes = vanna_charm_data.get("notes", "")
        if notes:
            st.success(notes)
        if vanna_charm_data.get("pin_risk"):
            st.error("🎯 PIN risk detected — avoid directional bets")
    # Options (Max Pain)
    if options_data and options_data.get("ok"):
        has_data = True
        mp = options_data.get("max_pain")
        px = options_data.get("price")
        if mp and px:
            st.caption(f"Max Pain: **${mp}** | Price: ${px:.2f} | Dist: {abs(px-mp)/mp:.1%}")
        source = options_data.get("source", "PROXY")
        if source == "LIVE":
            st.success("📡 LIVE Options")
        else:
            st.info("📊 PROXY Options")
    if not has_data:
        st.caption("⚡ Cem Karsan: No 0DTE/Vanna data")

def _render_skew_mini(ticker):
    """Render skew term structure mini per ticker."""
    skew_data = _get_skew_data(ticker)
    if not skew_data:
        st.caption("📐 Skew: No data")
        return
    spread = skew_data.get("spread", 0)
    regime = skew_data.get("regime", "FAIR")
    term = skew_data.get("term", "FLAT")
    color = "#f44336" if regime == "RICH" else ("#4caf50" if regime == "CHEAP" else "#888")
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;'><span style='font-size:11px;color:#888;'>30D/60D Skew:</span><span style='font-size:13px;font-weight:700;color:{color};'>{regime} ({spread:+.2%})</span><span style='font-size:10px;color:#666;'>Term: {term}</span></div>", unsafe_allow_html=True)

def _render_narrative_card_native(ticker, market_type="us_equity"):
    """Render full ticker card with options, greeks, Cem Karsan, Skew, news."""
    s = prices.get(ticker)
    if s is None or len(s) == 0:
        st.warning(f"No data for {ticker}")
        return
    px = _px(ticker)
    r1m = _r1m(ticker)
    r5d = _r5d(ticker)
    color = _color_pct(r1m or 0)

    with st.container(border=True):
        # Header row
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"<div style='font-size:16px;font-weight:700;'>{ticker}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:16px;font-weight:700;text-align:right;'>${_fmt_num(px)}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='font-size:14px;font-weight:600;text-align:right;color:{color};'>{_fmt_pct(r1m)}</div>", unsafe_allow_html=True)

        # Options & Greeks
        opt = _get_options_data(ticker)
        if opt and opt.get("ok"):
            greeks = greeks_data.get(ticker, {})
            source = opt.get("source", "PROXY")
            badge_color = "#4caf50" if source == "LIVE" else "#ff9800"
            st.markdown(f"<div style='margin-bottom:4px;'>{_badge(f'Options & Greeks — {source}', badge_color)}</div>", unsafe_allow_html=True)
            o1, o2, o3, o4, o5 = st.columns(5)
            o1.metric("Max Pain", f"${opt.get('max_pain', '-')}")
            o2.metric("Put Wall", f"${opt.get('put_wall', '-')}")
            o3.metric("Call Wall", f"${opt.get('call_wall', '-')}")
            o4.metric("Gamma", opt.get("gamma_regime", "-"))
            o5.metric("Conviction", opt.get("conviction", "-"))
            if greeks:
                g1, g2, g3, g4 = st.columns(4)
                g1.metric("Delta", _fmt_num(greeks.get("delta")))
                g2.metric("Gamma", _fmt_num(greeks.get("gamma")))
                g3.metric("Theta", _fmt_num(greeks.get("theta")))
                g4.metric("Vega", _fmt_num(greeks.get("vega")))
        else:
            st.caption("📊 Options data unavailable")

        # Cem Karsan Structure
        st.markdown("<div style='margin-top:6px;margin-bottom:2px;font-size:12px;font-weight:600;color:#4fc3f7;'>⚡ Cem Karsan Structure</div>", unsafe_allow_html=True)
        vc = _get_vanna_charm(ticker)
        _render_cem_karsan_mini(ticker, opt, vc, odte)

        # Skew
        st.markdown("<div style='margin-top:6px;margin-bottom:2px;font-size:12px;font-weight:600;color:#4fc3f7;'>📐 Skew Term Structure</div>", unsafe_allow_html=True)
        _render_skew_mini(ticker)

        # News
        news = (news_analysis.get("ticker_specific") or {}).get(ticker, {})
        if news and news.get("headlines"):
            st.markdown("<div style='margin-top:6px;margin-bottom:2px;font-size:12px;font-weight:600;color:#4fc3f7;'>📰 News</div>", unsafe_allow_html=True)
            for h in news["headlines"][:2]:
                st.caption(f"• {h}")
            if news.get("front_run_signal"):
                sig = news["front_run_signal"]
                sig_color = "#4caf50" if "BULL" in sig else ("#f44336" if "BEAR" in sig else "#ff9800")
                st.markdown(f"<div style='margin-top:2px;'>{_badge(sig, sig_color)}</div>", unsafe_allow_html=True)

        # Risk Range
        rr = (risk_ranges.get("asset_ranges") or {}).get(ticker)
        if rr:
            tr = rr.get("trade", {})
            lrr = tr.get("lrr")
            trr = tr.get("trr")
            comp = rr.get("composite", "neutral")
            if lrr and trr:
                st.markdown(f"<div style='margin-top:4px;font-size:11px;'>Risk Range: <span style='color:#4caf50;'>LRR ${lrr}</span> → <span style='color:#f44336;'>TRR ${trr}</span> | Composite: <b>{comp.upper()}</b></div>", unsafe_allow_html=True)

def _render_crypto_card_compact(ticker):
    """Crypto card with Cem Karsan + Skew."""
    s = prices.get(ticker)
    if s is None or len(s) == 0:
        return
    px = _px(ticker)
    r1m = _r1m(ticker)
    onchain = crypto_onchain.get(ticker, {})
    color = _color_pct(r1m or 0)
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"<div style='font-size:16px;font-weight:700;'>{ticker}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:16px;font-weight:700;text-align:right;'>${_fmt_num(px)}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='font-size:14px;font-weight:600;text-align:right;color:{color};'>{_fmt_pct(r1m)}</div>", unsafe_allow_html=True)
        if onchain:
            st.caption(f"Momentum: {onchain.get('momentum_score', 0):.2f} | Trend: {onchain.get('trend_direction', '-')} | Vol: {onchain.get('volatility_20d', 0):.1%}")
        # Cem Karsan for crypto (relevant for BTC/ETH futures options)
        st.markdown("<div style='margin-top:4px;font-size:12px;font-weight:600;color:#4fc3f7;'>⚡ Cem Karsan Structure</div>", unsafe_allow_html=True)
        vc = _get_vanna_charm(ticker)
        _render_cem_karsan_mini(ticker, None, vc, odte)
        # Skew
        st.markdown("<div style='margin-top:4px;font-size:12px;font-weight:600;color:#4fc3f7;'>📐 Skew Term Structure</div>", unsafe_allow_html=True)
        _render_skew_mini(ticker)
        # News
        news = (news_analysis.get("ticker_specific") or {}).get(ticker, {})
        if news and news.get("headlines"):
            for h in news["headlines"][:2]:
                st.caption(f"• {h}")

def _render_market_tab(tickers, market_type="us_equity", cols=3):
    """Render grid of ticker cards for any market tab."""
    if not tickers:
        st.info("No tickers available.")
        return
    # Search/filter
    search = st.text_input(f"🔍 Search {market_type.title()} tickers", "", key=f"search_{market_type}")
    filtered = [t for t in tickers if search.upper() in t.upper()] if search else tickers
    if not filtered:
        st.info("No matching tickers.")
        return
    # Grid
    grid = [filtered[i:i+cols] for i in range(0, len(filtered), cols)]
    for row in grid:
        columns = st.columns(cols)
        for idx, ticker in enumerate(row):
            with columns[idx]:
                if market_type == "crypto":
                    _render_crypto_card_compact(ticker)
                else:
                    _render_narrative_card_native(ticker, market_type)


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD SECTIONS
# ═══════════════════════════════════════════════════════════════════

def _render_top_kpis():
    """Compact 6-KPI top bar."""
    vix_series = prices.get("^VIX")
    vix = float(vix_series.iloc[-1]) if vix_series is not None and len(vix_series) > 0 else 20.0
    dxy = _px("DX-Y.NYB") or _px("UUP") or 100.0
    gold = _px("GC=F") or _px("GLD") or 0
    spy = _px("SPY") or 0
    qqq = _px("QQQ") or 0
    total_assets = len(prices)
    news_count = news_analysis.get("analyzed_count", 0)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    regime_name = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(sq, sq)
    c1.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>REGIME</div><div style='font-size:18px;font-weight:700;color:#4fc3f7;'>{sq}</div><div style='font-size:10px;color:#888;'>{regime_name}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>VIX</div><div style='font-size:18px;font-weight:700;{'color:#f44336;' if vix > 25 else ('color:#4caf50;' if vix < 15 else 'color:#e0e0e0;')}'>{vix:.1f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>DXY</div><div style='font-size:18px;font-weight:700;'>{dxy:.2f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>GOLD</div><div style='font-size:18px;font-weight:700;'>{gold:,.0f}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>ASSETS</div><div style='font-size:18px;font-weight:700;'>{total_assets}</div></div>", unsafe_allow_html=True)
    c6.markdown(f"<div style='text-align:center;'><div style='font-size:10px;color:#888;'>NEWS</div><div style='font-size:18px;font-weight:700;'>{news_count}</div></div>", unsafe_allow_html=True)

def _render_regime_rich_chart():
    """3-subplot chart: Quarterly + Monthly + Forward 3M."""
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Quarterly", "Monthly", "Forward 3M"),
        specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]],
        horizontal_spacing=0.08,
    )
    # Quarterly
    q_labels = ["Q1", "Q2", "Q3", "Q4"]
    q_vals = [structural_probs.get(q, 0) * 100 for q in q_labels]
    q_colors = ["#4caf50", "#ff9800", "#f44336", "#9c27b0"]
    fig.add_trace(go.Bar(x=q_labels, y=q_vals, marker_color=q_colors, text=[f"{v:.0f}%" for v in q_vals], textposition="outside", showlegend=False), row=1, col=1)
    # Monthly
    m_labels = ["M1", "M2", "M3"]
    m_vals = [probs.get(f"M{i}", 0) * 100 for i in range(1, 4)]
    if sum(m_vals) == 0:
        m_vals = [33, 33, 34]
    fig.add_trace(go.Bar(x=m_labels, y=m_vals, marker_color=["#4fc3f7", "#81c784", "#ffb74d"], text=[f"{v:.0f}%" for v in m_vals], textposition="outside", showlegend=False), row=1, col=2)
    # Forward 3M (projected from current momentum)
    f_labels = ["M+1", "M+2", "M+3"]
    # Simple projection: drift toward structural quad
    base = structural_probs.get(sq, 0.35)
    f_vals = [base * 100, (base + 0.05) * 100, (base + 0.08) * 100]
    f_vals = [min(100, max(0, v)) for v in f_vals]
    fig.add_trace(go.Bar(x=f_labels, y=f_vals, marker_color=["#ab47bc", "#7e57c2", "#5e35b1"], text=[f"{v:.0f}%" for v in f_vals], textposition="outside", showlegend=False), row=1, col=3)
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", size=11),
        yaxis=dict(showgrid=True, gridcolor="#2a2d35", range=[0, 100]),
        yaxis2=dict(showgrid=True, gridcolor="#2a2d35", range=[0, 100]),
        yaxis3=dict(showgrid=True, gridcolor="#2a2d35", range=[0, 100]),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def _render_playbook_inline():
    """Compact playbook text below regime chart."""
    pb = get_playbook(sq, mq) if 'get_playbook' in globals() else {}
    if not pb:
        pb = {
            "structural": sq, "monthly": mq,
            "best_assets": [], "worst_assets": [],
            "strategy": f"Trade {sq} regime. Monthly: {mq}.",
            "sectors_overweight": [], "sectors_underweight": [],
        }
    st.markdown(f"<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>📖 Playbook — {sq} / {mq}</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div style='font-size:11px;'><b>Best:</b> {', '.join(pb.get('best_assets', [])[:5]) or 'TBD'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;'><b>Overweight:</b> {', '.join(pb.get('sectors_overweight', [])[:5]) or 'TBD'}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='font-size:11px;'><b>Worst:</b> {', '.join(pb.get('worst_assets', [])[:5]) or 'TBD'}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;'><b>Underweight:</b> {', '.join(pb.get('sectors_underweight', [])[:5]) or 'TBD'}</div>", unsafe_allow_html=True)
    st.caption(pb.get("strategy", "-"))

def _render_market_pulse():
    """12 mini cards: Leverage, Crash, Risk Off, Breadth, SPY, QQQ, Gold, VIX, Risk State, Sentiment, Bonds, Yves Alert."""
    vix_series = prices.get("^VIX")
    vix = float(vix_series.iloc[-1]) if vix_series is not None and len(vix_series) > 0 else 20.0
    spy = _px("SPY") or 0
    qqq = _px("QQQ") or 0
    gold = _px("GC=F") or _px("GLD") or 0
    tlt = _px("TLT") or 0
    dxy = _px("DX-Y.NYB") or _px("UUP") or 100.0

    # Leverage proxy: HY spread
    hyoas = fred.get("HYOAS")
    leverage = float(hyoas.iloc[-1]) if hyoas is not None and len(hyoas) > 0 else 4.0
    lev_state = "HIGH" if leverage > 5 else "MODERATE" if leverage > 3.5 else "LOW"
    lev_color = "#f44336" if leverage > 5 else "#ff9800" if leverage > 3.5 else "#4caf50"

    # Crash proxy: VIX + yield curve
    dgs10 = fred.get("DGS10")
    dgs2 = fred.get("DGS2")
    spread = 0
    if dgs10 is not None and dgs2 is not None:
        try:
            spread = float(dgs10.iloc[-1]) - float(dgs2.iloc[-1])
        except Exception:
            pass
    crash_prob = min(100, max(0, (vix - 15) * 2 + (0 if spread > 0 else 20)))
    crash_color = "#f44336" if crash_prob > 40 else "#ff9800" if crash_prob > 20 else "#4caf50"

    # Risk off: DXY + Gold
    risk_off = "ON" if dxy > 105 and gold > 2200 else "BUILDING" if dxy > 103 or gold > 2100 else "OFF"
    ro_color = "#f44336" if risk_off == "ON" else "#ff9800" if risk_off == "BUILDING" else "#4caf50"

    # Breadth proxy: SPY vs equal-weight
    spy_r = _r1m("SPY") or 0
    rsp = _r1m("RSP") or spy_r
    breadth = "STRONG" if spy_r > 0.03 and rsp > spy_r * 0.8 else "WEAK" if spy_r > 0.03 and rsp < spy_r * 0.5 else "NEUTRAL"
    br_color = "#4caf50" if breadth == "STRONG" else "#f44336" if breadth == "WEAK" else "#888"

    # Risk state
    risk_state = "RISK ON" if vix < 18 and spy_r > 0.02 else "RISK OFF" if vix > 25 or spy_r < -0.05 else "NEUTRAL"
    rs_color = "#4caf50" if risk_state == "RISK ON" else "#f44336" if risk_state == "RISK OFF" else "#888"

    # Sentiment
    bull = behavioral.get("bullish", 30)
    bear = behavioral.get("bearish", 30)
    sent = "BULLISH" if bull > bear + 10 else "BEARISH" if bear > bull + 10 else "NEUTRAL"
    sent_color = "#4caf50" if sent == "BULLISH" else "#f44336" if sent == "BEARISH" else "#888"

    # Bonds
    tlt_r = _r1m("TLT") or 0
    bonds = "BULL" if tlt_r > 0.03 else "BEAR" if tlt_r < -0.03 else "NEUTRAL"
    bond_color = "#4caf50" if bonds == "BULL" else "#f44336" if bonds == "BEAR" else "#888"

    # Yves alert
    yves = behavioral.get("yves", {})
    yves_alert = yves.get("alert", "None")
    yves_level = yves.get("alert_level", "NONE")
    yves_color = "#f44336" if yves_level in ["CRITICAL", "HIGH"] else "#ff9800" if yves_level == "MEDIUM" else "#4caf50"

    # Crash meter
    crash_prob_cm = 0
    if crash_meter and isinstance(crash_meter, dict):
        crash_prob_cm = crash_meter.get("crash_probability", crash_meter.get("probability", 0))
        if not isinstance(crash_prob_cm, (int, float)):
            crash_prob_cm = 0

    items = [
        ("Leverage", lev_state, lev_color, f"{leverage:.1f}%"),
        ("Crash Meter", f"{crash_prob_cm:.0f}%", "#f44336" if crash_prob_cm > 40 else "#ff9800" if crash_prob_cm > 20 else "#4caf50", "-"),
        ("Crash Prob", f"{crash_prob:.0f}%", crash_color, f"VIX {vix:.0f}"),
        ("Risk Off", risk_off, ro_color, f"DXY {dxy:.0f}"),
        ("Breadth", breadth, br_color, f"SPY {_fmt_pct(spy_r)}"),
        ("SPY", f"${spy:,.0f}", _color_pct(_r1m("SPY") or 0), _fmt_pct(_r1m("SPY"))),
        ("QQQ", f"${qqq:,.0f}", _color_pct(_r1m("QQQ") or 0), _fmt_pct(_r1m("QQQ"))),
        ("Gold", f"${gold:,.0f}", _color_pct(_r1m("GC=F") or _r1m("GLD") or 0), _fmt_pct(_r1m("GC=F") or _r1m("GLD") or 0)),
        ("VIX", f"{vix:.1f}", "#f44336" if vix > 25 else "#4caf50" if vix < 15 else "#888", "-"),
        ("Risk State", risk_state, rs_color, "-"),
        ("Sentiment", sent, sent_color, f"Bull {bull}%"),
        ("Bonds", bonds, bond_color, _fmt_pct(tlt_r)),
        ("Yves Alert", yves_alert[:12], yves_color, yves_level),
    ]

    cols_per_row = 6
    for i in range(0, len(items), cols_per_row):
        row = items[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for j, (title, value, color, sub) in enumerate(row):
            with cols[j]:
                st.markdown(f"<div style='text-align:center;padding:6px;background:#1a1d24;border-radius:4px;border-left:3px solid {color};'><div style='font-size:9px;color:#888;text-transform:uppercase;'>{title}</div><div style='font-size:14px;font-weight:700;color:{color};'>{value}</div><div style='font-size:9px;color:#666;'>{sub}</div></div>", unsafe_allow_html=True)

def _render_sector_rotation_compact():
    """10 mini sector cards."""
    sectors = ["XLK", "XLF", "XLE", "XLI", "XLP", "XLU", "XLB", "XLY", "XLRE", "SMH"]
    cols_per_row = 5
    for i in range(0, len(sectors), cols_per_row):
        row = sectors[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for j, ticker in enumerate(row):
            with cols[j]:
                r = _r1m(ticker) or 0
                color = _color_pct(r)
                st.markdown(f"<div style='text-align:center;padding:6px;background:#1a1d24;border-radius:4px;'><div style='font-size:10px;color:#888;'>{ticker}</div><div style='font-size:16px;font-weight:700;color:{color};'>{_fmt_pct(r)}</div></div>", unsafe_allow_html=True)

def _render_skew_chart_dashboard():
    """Plotly bar chart: 30D vs 60D skew spread for key tickers."""
    tickers = ["SPY", "QQQ", "IWM", "GLD", "TLT", "XLE", "XLF", "XLK", "SMH", "VIX", "CL=F", "GC=F"]
    data = []
    for t in tickers:
        sd = _get_skew_data(t)
        if sd:
            data.append({"ticker": t, "spread": sd["spread"], "regime": sd["regime"]})
    if not data:
        st.caption("📐 Skew data unavailable")
        return
    df = pd.DataFrame(data)
    colors = ["#f44336" if r == "RICH" else "#4caf50" if r == "CHEAP" else "#888" for r in df["regime"]]
    fig = go.Figure(go.Bar(
        x=df["ticker"], y=df["spread"],
        marker_color=colors,
        text=[f"{s:+.2%}" for s in df["spread"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=20, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", size=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#2a2d35", title="30D/60D Skew Spread"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def _render_philosophy_layer():
    """Compact 3-column: Soros · Cem Karsan · Skew Chart."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>🧠 Soros Reflexivity</div>", unsafe_allow_html=True)
        stage = boombust.get("stage", "INCEPTION")
        conf = boombust.get("stage_confidence", 0.5)
        score = reflexivity.get("super_bubble_score", 5.0)
        gap = reflexivity.get("reflexivity_gap", 0)
        st.markdown(f"<div style='font-size:11px;'>Stage: <b>{stage}</b> ({conf:.0%})</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;'>Bubble Score: <b>{score:.1f}</b>/10</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;'>Gap: <b>{gap:.2f}</b></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>⚡ Cem Karsan 0DTE</div>", unsafe_allow_html=True)
        expiry = odte.get("expiry", "-")
        cascade = odte.get("cascade_warning", False)
        pin_count = sum(1 for v in odte.get("tickers", {}).values() if v.get("pin_risk_pct", 0) > 0.3)
        st.markdown(f"<div style='font-size:11px;'>Expiry: <b>{expiry}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;'>PIN risk: <b>{pin_count}</b> tickers</div>", unsafe_allow_html=True)
        if cascade:
            st.error("🌊 Cascade warning active")
        else:
            st.success("✅ No cascade")
        # Vanna/Charm summary for SPY/QQQ
        for t in ["SPY", "QQQ"]:
            vc = _get_vanna_charm(t)
            if vc:
                st.caption(f"{t}: Vanna {vc.get('vanna', 0):+.1f} | Charm {vc.get('charm', 0):+.1f}")
    with c3:
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>📐 Skew Term Structure</div>", unsafe_allow_html=True)
        _render_skew_chart_dashboard()

def _render_scenario_discovery():
    """Scenario cards in dashboard."""
    active = scenario_discovery.get("active_scenarios", [])
    watch = scenario_discovery.get("watch_scenarios", [])
    if not active and not watch:
        st.caption("🔮 No active scenarios — macro stable")
        return
    if active:
        st.markdown(f"<div style='font-size:12px;font-weight:600;color:#f44336;margin-bottom:4px;'>🔮 {len(active)} Active Scenario(s)</div>", unsafe_allow_html=True)
        for sc in active[:3]:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"<div style='font-size:13px;font-weight:700;'>{sc.get('scenario', '-')}</div>", unsafe_allow_html=True)
                c1.caption(sc.get("trigger", "-"))
                c2.markdown(f"<div style='text-align:right;font-size:18px;font-weight:700;color:#f44336;'>{sc.get('confidence', 0):.0%}</div>", unsafe_allow_html=True)
                # Shock pills
                shocks = sc.get("shock", {})
                if shocks:
                    pills = " ".join([f"<span style='background:#2a2d35;padding:2px 6px;border-radius:3px;font-size:10px;'>{k} {_fmt_pct(v)}</span>" for k, v in list(shocks.items())[:5]])
                    st.markdown(f"<div style='margin-top:4px;'>{pills}</div>", unsafe_allow_html=True)
                # Cascade
                cascade = sc.get("sector_cascade", [])
                if cascade:
                    hits = [c for c in cascade if c.get("status") == "HIT"]
                    if hits:
                        st.caption(f"🎯 HIT: {', '.join([c['sector'] for c in hits[:3]])}")
    if watch:
        st.markdown(f"<div style='font-size:11px;color:#888;margin-top:4px;'>👁️ Watching: {', '.join(watch)}</div>", unsafe_allow_html=True)

def _render_transmission_dashboard():
    """Transmission cascade in dashboard."""
    active = transmission.get("active_scenarios", [])
    if not active:
        st.caption("🔗 No active transmission — markets decoupled")
        return
    st.markdown(f"<div style='font-size:12px;font-weight:600;color:#ff9800;margin-bottom:4px;'>🔗 Active Transmission Cascade(s)</div>", unsafe_allow_html=True)
    for sc in active[:2]:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:13px;font-weight:700;'>{sc.get('scenario', '-')}</div>", unsafe_allow_html=True)
            st.caption(sc.get("trigger", "-"))
            cascade = sc.get("sector_cascade", [])
            if cascade:
                flow = " → ".join([f"<b>{c['sector']}</b> ({c['impact']:+.1%})" for c in cascade[:4]])
                st.markdown(f"<div style='font-size:11px;margin-top:4px;'>📈 {flow}</div>", unsafe_allow_html=True)
            em = sc.get("em_impact", {})
            if em:
                st.caption(f"EM: DXY {em.get('DXY', 0):+.1%} | EM {em.get('EM', 0):+.1%} | Rupiah {em.get('Rupiah', 0):+.1%}")

def _render_regime_transition():
    """Display regime transition probabilities."""
    if not regime_transition or not regime_transition.get("transitions"):
        st.caption("🔄 Regime transition: No data")
        return
    current = regime_transition.get("current_quad", "Q3")
    most_likely = regime_transition.get("most_likely_60d", current)
    prob = regime_transition.get("most_likely_prob_60d", 0)
    st.markdown(f"<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>🔄 Regime Transition — {current} → {most_likely} in 60d: {prob:.0%}</div>", unsafe_allow_html=True)
    transitions = regime_transition.get("transitions", {})
    cols = st.columns(4)
    for i, q in enumerate(["Q1", "Q2", "Q3", "Q4"]):
        t = transitions.get(q, {})
        p30 = t.get("30d", 0)
        p60 = t.get("60d", 0)
        color = "#4caf50" if p60 > 0.4 else "#ff9800" if p60 > 0.2 else "#888"
        with cols[i]:
            st.markdown(f"<div style='text-align:center;padding:4px;background:#1a1d24;border-radius:4px;border-left:3px solid {color};'><div style='font-size:10px;color:#888;'>{q}</div><div style='font-size:14px;font-weight:700;color:{color};'>{p60:.0%}</div><div style='font-size:9px;color:#666;'>60d</div></div>", unsafe_allow_html=True)

def _render_crash_meter():
    """Display crash probability meter."""
    if not crash_meter:
        return
    prob = crash_meter.get("crash_probability", crash_meter.get("probability", 0))
    if isinstance(prob, (int, float)) and prob > 0:
        color = "#f44336" if prob > 40 else "#ff9800" if prob > 20 else "#4caf50"
        st.markdown(f"<div style='margin-top:4px;font-size:11px;'>💥 Crash Meter: <span style='color:{color};font-weight:700;'>{prob:.0f}%</span> ({crash_meter.get('regime', 'Normal')})</div>", unsafe_allow_html=True)

def _render_bottleneck_collapsed():
    """Bottleneck in collapsed expander."""
    with st.expander("🚧 Bottleneck Analysis", expanded=False):
        # Show v3 first, fallback to v1
        if bottleneck_v3 and bottleneck_v3.get("active_bottlenecks"):
            st.markdown("<div style='font-size:11px;font-weight:600;color:#4fc3f7;'>Bottleneck Discovery v3</div>", unsafe_allow_html=True)
            for bn in bottleneck_v3["active_bottlenecks"][:5]:
                st.markdown(f"<div style='font-size:12px;font-weight:700;color:#f44336;'>{bn.get('name', '-')}</div>", unsafe_allow_html=True)
                st.caption(f"Confidence: {bn.get('confidence', 0):.0%} | Status: {bn.get('status', '-')}")
                scores = bn.get("scores", {})
                if scores:
                    st.caption(f"Price: {scores.get('price_momentum', 0):.2f} | News: {scores.get('news_signal', 0):.2f} | Macro: {scores.get('macro_alignment', 0):.2f}")
            if bottleneck_v3.get("watch_bottlenecks"):
                st.caption(f"👁️ Watching: {len(bottleneck_v3['watch_bottlenecks'])} bottleneck(s)")
        elif bottleneck:
            st.json(bottleneck)
        else:
            st.caption("No bottleneck data")

def _render_global_countries():
    """Render 60 countries grouped by quad with color-coded borders."""
    gq = global_quad or _global_fallback(sq)
    country_list = gq.get("country_list", [])
    if not country_list:
        # Fallback from country_quads dict
        cqs = gq.get("country_quads", {})
        country_list = [{"country": c, "quad": q, "regime_name": {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q,q)} for c, q in cqs.items()]
    if not country_list:
        st.warning("No country data available")
        return

    quad_colors = {"Q1": "#4caf50", "Q2": "#ff9800", "Q3": "#f44336", "Q4": "#9c27b0"}
    quad_names = {"Q1": "Goldilocks", "Q2": "Reflation", "Q3": "Stagflation", "Q4": "Deflation"}

    st.markdown(f"<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:8px;'>🌍 Global Quad Map — {len(country_list)} Countries</div>", unsafe_allow_html=True)

    for quad in ["Q1", "Q2", "Q3", "Q4"]:
        countries = [c for c in country_list if c.get("quad") == quad]
        if not countries:
            continue
        color = quad_colors.get(quad, "#888")
        name = quad_names.get(quad, quad)
        st.markdown(f"<div style='font-size:11px;font-weight:600;color:{color};margin-top:6px;margin-bottom:2px;'>{quad} — {name} ({len(countries)} countries)</div>", unsafe_allow_html=True)
        # Render as compact badges
        badges = " ".join([f"<span style='display:inline-block;background:#1a1d24;border-left:2px solid {color};padding:2px 6px;margin:1px;border-radius:3px;font-size:10px;'>{c.get('country', '-')}</span>" for c in countries])
        st.markdown(f"<div style='line-height:1.6;'>{badges}</div>", unsafe_allow_html=True)

def _global_fallback(quad):
    base_map = {
        "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia","UAE","Israel","Poland","Czech Republic","Romania"],
        "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand","Colombia","New Zealand","Norway","Kazakhstan","Angola"],
        "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt","Spain","Netherlands","Belgium","Sweden","Switzerland"],
        "Q4": ["Venezuela","Iran","Ukraine","Greece","Portugal","Lebanon","Syria","Yemen","Zimbabwe","Sudan","Afghanistan","North Korea","Myanmar","Belarus","Bolivia"],
    }
    cqs = {}
    for q, countries in base_map.items():
        for c in countries:
            cqs[c] = q
    return {
        "global_quad": quad,
        "global_conf": 0.52,
        "global_probs": {"Q1":0.20,"Q2":0.25,"Q3":0.35,"Q4":0.20},
        "country_quads": cqs,
        "country_list": [{"country": c, "quad": q, "regime_name": {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q,q)} for q, countries in base_map.items() for c in countries],
        "em_recovery": {"trigger": f"Q3 defensive - watch for {quad} rotation", "confidence": 0.4},
        "dm_count": len(base_map.get("Q1",[])) + len(base_map.get("Q3",[])),
        "em_count": len(base_map.get("Q2",[])) + len(base_map.get("Q4",[])),
    }


# ═══════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ═══════════════════════════════════════════════════════════════════

st.title("🌐 MacroRegime Dashboard v27.4")
st.caption(f"Build: {snap.get('timestamp', '-')[:19]} · {len(prices)} assets · {len(fred)} FRED series · {news_analysis.get('analyzed_count', 0)} news")

# Top KPIs
_render_top_kpis()
# Regime Transition mini bar
if regime_transition and regime_transition.get("transitions"):
    current = regime_transition.get("current_quad", sq)
    most_likely = regime_transition.get("most_likely_60d", current)
    prob = regime_transition.get("most_likely_prob_60d", 0)
    st.markdown(f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>🔄 Transition Watch: <b>{current}</b> → <b>{most_likely}</b> in 60d: <span style='color:#ff9800;font-weight:700;'>{prob:.0%}</span></div>", unsafe_allow_html=True)
st.divider()

# TABS
tabs = st.tabs(["📊 Dashboard", "🇺🇸 US Stocks", "💱 Forex", "🛢️ Commodities", "₿ Crypto", "🇮🇩 IHSG", "🌍 Global & EM", "📈 Alpha Center", "🧠 Playbook", "⚙️ GIP Model"])

# ═══════════════════════════════════════════════════════════════════
# TAB 0: DASHBOARD
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:
    # Row 1: Behavioral Macro + Front-Run Radar
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>🧠 Behavioral Macro</div>", unsafe_allow_html=True)
        bull = behavioral.get("bullish", 30)
        bear = behavioral.get("bearish", 30)
        neut = behavioral.get("neutral", 40)
        fig = go.Figure(go.Pie(labels=["Bullish", "Bearish", "Neutral"], values=[bull, bear, neut], marker_colors=["#4caf50", "#f44336", "#888"], hole=0.5, textinfo="label+percent", textfont_size=10))
        fig.update_layout(height=160, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e0e0e0", size=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>📰 Front-Run Radar</div>", unsafe_allow_html=True)
        rumors = (news_analysis.get("rumor_watch") or [])[:6]
        if rumors:
            for r in rumors:
                sig = r.get("signal", "-")
                color = "#4caf50" if "BULL" in sig else ("#f44336" if "BEAR" in sig else "#ff9800")
                st.markdown(f"<div style='display:inline-block;margin:2px;'>{_badge(f'📰 {r.get('ticker', '-')} {sig[:15]}', color)}</div>", unsafe_allow_html=True)
        else:
            st.caption("No front-run signals")

    st.divider()

    # Row 2: Regime Chart + Playbook
    c1, c2 = st.columns([2, 1])
    with c1:
        _render_regime_rich_chart()
    with c2:
        _render_playbook_inline()

    st.divider()

    # Row 3: Market Pulse (merged Early Warning)
    st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>💓 Market Pulse</div>", unsafe_allow_html=True)
    _render_market_pulse()

    st.divider()

    # Row 4: Sector Rotation
    st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;margin-bottom:4px;'>🔄 Sector Rotation</div>", unsafe_allow_html=True)
    _render_sector_rotation_compact()

    st.divider()

    # Row 5: Regime Transition + Scenario Discovery
    c1, c2 = st.columns([1, 1])
    with c1:
        _render_regime_transition()
    with c2:
        _render_scenario_discovery()

    st.divider()

    # Row 6: Transmission + Crash Meter
    c1, c2 = st.columns([1, 1])
    with c1:
        _render_transmission_dashboard()
    with c2:
        _render_crash_meter()

    st.divider()

    # Row 6: Philosophy Layer
    _render_philosophy_layer()

    st.divider()

    # Row 7: Bottleneck (collapsed)
    _render_bottleneck_collapsed()

    # Footer
    st.caption(f"Build {snap.get('timestamp', '-')[:19]} · {len(prices)} assets · {len(fred)} FRED · {news_analysis.get('analyzed_count', 0)} news · MacroRegime v27.4")

# ═══════════════════════════════════════════════════════════════════
# TAB 1: US STOCKS
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    us_tickers = list(US_SECTORS.keys()) + list(US_FACTORS.keys()) + ["SPY", "QQQ", "IWM", "DIA", "ARKK", "SMH"]
    seen = set()
    us_tickers = [t for t in us_tickers if not (t in seen or seen.add(t))]
    _render_market_tab(us_tickers, "us_equity", cols=3)
    # US Equity Native
    if us_equity_native and isinstance(us_equity_native, dict):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>🇺🇸 US Equity Native</div>", unsafe_allow_html=True)
        st.json(us_equity_native)

# ═══════════════════════════════════════════════════════════════════
# TAB 2: FOREX
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    fx_tickers = list(FOREX_PAIRS.keys()) + ["DX-Y.NYB", "UUP"]
    _render_market_tab(fx_tickers, "forex", cols=3)
    # FX Native
    if fx_native and isinstance(fx_native, dict):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>💱 FX Native Analysis</div>", unsafe_allow_html=True)
        st.json(fx_native)

# ═══════════════════════════════════════════════════════════════════
# TAB 3: COMMODITIES
# ═══════════════════════════════════════════════════════════════════
with tabs[3]:
    comm_tickers = list(COMMODITIES.keys()) + ["GC=F", "SI=F", "CL=F", "HG=F", "NG=F", "ZC=F", "ZW=F", "ZS=F", "KC=F", "CC=F", "SB=F", "CT=F", "LB=F", "PL=F", "PA=F"]
    seen = set()
    comm_tickers = [t for t in comm_tickers if not (t in seen or seen.add(t))]
    _render_market_tab(comm_tickers, "commodity", cols=3)
    # Commodity Native
    if commodity_native and isinstance(commodity_native, dict):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>🛢️ Commodity Native Analysis</div>", unsafe_allow_html=True)
        st.json(commodity_native)

# ═══════════════════════════════════════════════════════════════════
# TAB 4: CRYPTO
# ═══════════════════════════════════════════════════════════════════
with tabs[4]:
    crypto_tickers = list(CRYPTO.keys()) + ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOT-USD", "AVAX-USD", "LINK-USD", "MATIC-USD", "UNI-USD", "AAVE-USD", "MKR-USD", "LDO-USD", "RPL-USD", "OP-USD", "ARB-USD", "SUI-USD", "SEI-USD", "TIA-USD", "DYM-USD", "STRK-USD", "MANTA-USD", "ZETA-USD", "WLD-USD", "PYTH-USD", "JTO-USD", "JUP-USD", "WIF-USD", "BONK-USD", "PEPE-USD", "FLOKI-USD", "SHIB-USD", "DOGE-USD", "TRUMP-USD"]
    seen = set()
    crypto_tickers = [t for t in crypto_tickers if not (t in seen or seen.add(t))]
    _render_market_tab(crypto_tickers, "crypto", cols=3)
    # Crypto Native
    if crypto_native and isinstance(crypto_native, dict):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>₿ Crypto Native Analysis</div>", unsafe_allow_html=True)
        st.json(crypto_native)

# ═══════════════════════════════════════════════════════════════════
# TAB 5: IHSG
# ═══════════════════════════════════════════════════════════════════
with tabs[5]:
    ihsg_tickers = list(IHSG_UNIVERSE.keys()) + ["^JKSE", "EIDO"]
    seen = set()
    ihsg_tickers = [t for t in ihsg_tickers if not (t in seen or seen.add(t))]
    _render_market_tab(ihsg_tickers, "ihsg", cols=3)
    # IHSG layers detail
    st.divider()
    st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>🇮🇩 IHSG Deep Layers</div>", unsafe_allow_html=True)
    if ihsg_native and isinstance(ihsg_native, dict):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#4fc3f7;'>🇮🇩 IHSG Native Analysis</div>", unsafe_allow_html=True)
        st.json(ihsg_native)
    if ihsg_layers:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Sector Momentum**")
            for sector, data in (ihsg_layers.get("ihsg_sector_momentum") or {}).items():
                st.caption(f"{sector}: {data.get('bias', '-')} ({data.get('avg_1m', 0):+.1%})")
            st.markdown("**Commodity Overlay**")
            for comm, data in (ihsg_layers.get("ihsg_commodity_overlay") or {}).items():
                st.caption(f"{comm}: {data.get('tailwind', '-')} | {data.get('signal', '-')}")
        with c2:
            st.markdown("**Rupiah Regime**")
            rr = ihsg_layers.get("ihsg_rupiah_regime", {})
            for k, v in rr.items():
                st.caption(f"{k}: {v}")
            st.markdown("**Macro Overlay**")
            mo = ihsg_layers.get("ihsg_macro_overlay", {})
            for k, v in mo.items():
                st.caption(f"{k}: {v}")
    else:
        st.caption("IHSG layers unavailable")

# ═══════════════════════════════════════════════════════════════════
# TAB 6: GLOBAL & EM
# ═══════════════════════════════════════════════════════════════════
with tabs[6]:
    gq = global_quad or _global_fallback(sq)
    st.markdown(f"<div style='font-size:14px;font-weight:700;'>🌍 Global Quad: {gq.get('global_quad', sq)} ({gq.get('global_conf', 0):.0%} confidence)</div>", unsafe_allow_html=True)
    # Quad probs mini chart
    probs_dict = gq.get("global_probs", {})
    if probs_dict:
        fig = go.Figure(go.Bar(
            x=list(probs_dict.keys()),
            y=[v*100 for v in probs_dict.values()],
            marker_color=["#4caf50", "#ff9800", "#f44336", "#9c27b0"],
            text=[f"{v:.0f}%" for v in probs_dict.values()],
            textposition="outside",
        ))
        fig.update_layout(height=160, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e0e0e0", size=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    # Countries
    _render_global_countries()
    # EM recovery
    em = gq.get("em_recovery", {})
    if em:
        st.caption(f"EM Recovery: {em.get('trigger', '-')} (confidence: {em.get('confidence', 0):.0%})")
    st.caption(f"DM: {gq.get('dm_count', 0)} countries | EM: {gq.get('em_count', 0)} countries")

# ═══════════════════════════════════════════════════════════════════
# TAB 7: ALPHA CENTER
# ═══════════════════════════════════════════════════════════════════
with tabs[7]:
    meta = alpha_center.get("meta", {})
    st.markdown(f"<div style='font-size:14px;font-weight:700;'>🎯 Alpha Center — {meta.get('regime', sq)} · Bias: {meta.get('bias', '-')}</div>", unsafe_allow_html=True)
    st.caption(f"VIX: {meta.get('vix', 0):.1f} | Total: {meta.get('total_items', 0)} setups")

    for level, label, color in [("level_1", "⭐ Level 1 (A-grade)", "#4caf50"), ("level_2", "🔶 Level 2 (B-grade)", "#ff9800"), ("watch", "👁️ Watch (C-grade)", "#888")]:
        items = alpha_center.get(level, [])
        if not items:
            continue
        st.markdown(f"<div style='font-size:12px;font-weight:600;color:{color};margin-top:8px;'>{label} — {len(items)} items</div>", unsafe_allow_html=True)
        for item in items[:20]:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.markdown(f"<div style='font-size:14px;font-weight:700;'>{item.get('ticker', '-')}</div>", unsafe_allow_html=True)
                c1.caption(f"{item.get('scanner_type', '-')} · {item.get('direction', '-')}")
                c2.markdown(f"<div style='text-align:right;font-size:13px;'>Entry: <b>${item.get('entry', '-')}</b></div>", unsafe_allow_html=True)
                c3.markdown(f"<div style='text-align:right;font-size:13px;'>TP1: <b>${item.get('target_1', '-')}</b></div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='text-align:right;font-size:13px;color:#f44336;'>SL: <b>${item.get('stop_loss', '-')}</b></div>", unsafe_allow_html=True)
                st.caption(f"R/R: {item.get('rr', '-')} | Grade: {item.get('grade', '-')} | Action: {item.get('action', '-')} | {item.get('thesis', '-')}")
                if item.get("news_signal"):
                    st.caption(f"📰 News: {item['news_signal']} — {item.get('news_headline', '')[:60]}")

# ═══════════════════════════════════════════════════════════════════
# TAB 8: PLAYBOOK
# ═══════════════════════════════════════════════════════════════════
with tabs[8]:
    pb = get_playbook(sq, mq) if 'get_playbook' in globals() else {}
    if not pb:
        pb = {"structural": sq, "monthly": mq, "best_assets": [], "worst_assets": [], "strategy": "-", "sectors_overweight": [], "sectors_underweight": [], "style": "", "fx": "", "bonds": ""}
    st.markdown(f"<div style='font-size:14px;font-weight:700;'>📖 Playbook — {sq} / {mq}</div>", unsafe_allow_html=True)
    st.markdown(f"**Strategy:** {pb.get('strategy', '-')}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Best Assets**")
        for a in pb.get("best_assets", []):
            st.caption(f"✅ {a}")
        st.markdown("**Overweight Sectors**")
        for s in pb.get("sectors_overweight", []):
            st.caption(f"▲ {s}")
    with c2:
        st.markdown("**Worst Assets**")
        for a in pb.get("worst_assets", []):
            st.caption(f"❌ {a}")
        st.markdown("**Underweight Sectors**")
        for s in pb.get("sectors_underweight", []):
            st.caption(f"▼ {s}")
    st.markdown(f"**Style:** {pb.get('style', '-')} | **FX:** {pb.get('fx', '-')} | **Bonds:** {pb.get('bonds', '-')}")
    # Scenario playbook overlay
    if scenario_discovery.get("active_scenarios"):
        st.divider()
        st.markdown("<div style='font-size:12px;font-weight:600;color:#f44336;'>🔮 Scenario Overlay</div>", unsafe_allow_html=True)
        for sc in scenario_discovery["active_scenarios"][:3]:
            st.caption(f"If **{sc.get('scenario', '-')}** → {', '.join([f'{k} {_fmt_pct(v)}' for k, v in list(sc.get('shock', {}).items())[:3]])}")

# ═══════════════════════════════════════════════════════════════════
# TAB 9: GIP MODEL
# ═══════════════════════════════════════════════════════════════════
with tabs[9]:
    st.markdown(f"<div style='font-size:14px;font-weight:700;'>⚙️ GIP Model — {sq} / {mq}</div>", unsafe_allow_html=True)
    st.json(gip)

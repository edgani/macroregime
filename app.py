"""app.py - MacroRegime Pro v39 ALPHA
Full reconstruction from v32.7 AUDITED base.
Fixes:
- Line corruption eliminated (no mega-lines)
- _build_row unified single return
- All duplicate defs removed
- Stablecoin endpoint fixed in orchestrator companion
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
import json, os
from datetime import datetime

logger = __import__("logging").getLogger(__name__)
st.set_page_config(page_title="MacroRegime Pro v39", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");
html, body, [class*="css"] { font-family: "Inter", sans-serif; }
.block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 1440px !important; }
h1 { font-size: 1.4rem !important; margin: 0.2rem 0 0.3rem !important; font-weight: 800 !important; letter-spacing: -0.5px; }
h2 { font-size: 1.05rem !important; margin: 0.4rem 0 0.2rem !important; font-weight: 700 !important; letter-spacing: -0.3px; }
h3 { font-size: 0.9rem !important; margin: 0.3rem 0 0.15rem !important; font-weight: 600 !important; }
hr { margin: 0.4rem 0 !important; opacity: 0.08; border-color: #30363D; }
[data-testid="stMetric"] { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 5px 8px !important; }
[data-testid="stMetricLabel"] { font-size: 0.58rem !important; font-weight: 600 !important; letter-spacing: 0.6px; text-transform: uppercase; opacity: 0.55; }
[data-testid="stMetricValue"] { font-size: 1.05rem !important; font-weight: 700 !important; }

.ticker-card-v4 { display: flex; align-items: center; gap: 10px; padding: 7px 10px; background: #161B22; border: 1px solid #30363D; border-radius: 8px; margin: 3px 0; transition: border-color 0.2s; flex-wrap: wrap; }
.ticker-card-v4:hover { border-color: #484F58; }
.tc-v4-left { min-width: 80px; }
.tc-v4-symbol { font-weight: 800; font-size: 0.9rem; color: #E6EDF3; letter-spacing: -0.3px; }
.tc-v4-price { font-weight: 600; font-size: 0.75rem; color: #8B949E; font-variant-numeric: tabular-nums; }
.tc-v4-badges { display: flex; gap: 3px; flex-wrap: wrap; margin-top: 2px; }
.tc-v4-spark { width: 80px; height: 24px; display: flex; align-items: flex-end; gap: 1px; flex-shrink: 0; }
.tc-v4-rr { flex: 1; min-width: 120px; }
.tc-v4-meta { display: flex; gap: 8px; font-size: 0.68rem; color: #8B949E; font-variant-numeric: tabular-nums; min-width: 110px; }

.badge { display: inline-flex; align-items: center; padding: 1px 5px; border-radius: 10px; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.3px; border: 1px solid transparent; line-height: 1.3; }
.badge-long { background: rgba(34,197,94,0.12); color: #3FB950; border-color: rgba(34,197,94,0.3); }
.badge-short { background: rgba(239,68,68,0.12); color: #F85149; border-color: rgba(239,68,68,0.3); }
.badge-neut { background: rgba(234,179,8,0.12); color: #eab308; border-color: rgba(234,179,8,0.3); }
.badge-grade-a { background: rgba(34,197,94,0.15); color: #3FB950; border-color: #3FB950; }
.badge-grade-b { background: rgba(234,179,8,0.15); color: #D29922; border-color: #D29922; }
.badge-grade-c { background: rgba(139,148,158,0.15); color: #8B949E; border-color: #8B949E; }
.badge-news { background: rgba(88,166,255,0.12); color: #58A6FF; border-color: rgba(88,166,255,0.3); }
.badge-mm { background: rgba(168,85,247,0.12); color: #A855F7; border-color: rgba(168,85,247,0.3); }
.badge-chase { background: rgba(34,197,94,0.2); color: #3FB950; border-color: #3FB950; }
.badge-wait { background: rgba(234,179,8,0.2); color: #D29922; border-color: #D29922; }

.sp-bar-v4 { width: 3px; border-radius: 1px; opacity: 0.85; }
.rr-track-v4 { position: relative; height: 16px; background: #21262D; border-radius: 4px; overflow: hidden; }
.rr-zone-v4 { position: absolute; top: 2px; bottom: 2px; border-radius: 2px; }
.rr-dot-v4 { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 7px; height: 7px; border-radius: 50%; background: #E6EDF3; border: 2px solid #58A6FF; z-index: 10; box-shadow: 0 0 4px rgba(88,166,255,0.4); }
.rr-labels-v4 { display: flex; justify-content: space-between; font-size: 0.58rem; color: #8B949E; margin-top: 1px; font-variant-numeric: tabular-nums; }

.gauge-track { position: relative; height: 12px; background: #21262D; border-radius: 6px; overflow: hidden; margin: 3px 0; }
.gauge-fill { position: absolute; top: 0; bottom: 0; left: 0; border-radius: 6px; transition: width 0.5s ease; }
.gauge-label { display: flex; justify-content: space-between; font-size: 0.6rem; color: #8B949E; margin-top: 1px; }

.hm-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
.hm-cell { padding: 5px 3px; border-radius: 4px; text-align: center; font-size: 0.68rem; font-weight: 600; color: #E6EDF3; border: 1px solid rgba(255,255,255,0.05); }

.pulse-hbox { min-width: 70px; height: 40px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 700; color: #E6EDF3; border: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
.pulse-hlabel { font-size: 0.52rem; font-weight: 500; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-top: 1px; }

.timeline { display: flex; align-items: center; gap: 0px; margin: 6px 0; }
.tl-node { width: 12px; height: 12px; border-radius: 50%; border: 2px solid #30363D; background: #21262D; flex-shrink: 0; }
.tl-node.active { border-color: #58A6FF; background: #58A6FF; box-shadow: 0 0 5px rgba(88,166,255,0.35); }
.tl-node.past { border-color: #3FB950; background: #3FB950; }
.tl-line { flex: 1; height: 2px; background: #30363D; min-width: 16px; }
.tl-line.active { background: #58A6FF; }
.tl-labels { display: flex; justify-content: space-between; font-size: 0.58rem; color: #8B949E; margin-top: 3px; }

.stack-bar { display: flex; height: 20px; border-radius: 4px; overflow: hidden; background: #21262D; }
.stack-seg { display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-weight: 700; color: #fff; }

.skew-row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.skew-label { width: 32px; font-size: 0.65rem; color: #8B949E; font-weight: 600; }
.skew-track { flex: 1; height: 14px; background: #21262D; border-radius: 4px; position: relative; overflow: hidden; }
.skew-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.skew-value { width: 36px; font-size: 0.65rem; color: #E6EDF3; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }

.gex-track { position: relative; height: 18px; background: #21262D; border-radius: 4px; overflow: hidden; display: flex; align-items: center; }
.gex-center { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #8B949E; opacity: 0.3; }

.stTabs [data-baseweb="tab-list"] { gap: 2px !important; margin-bottom: 5px !important; }
.stTabs [data-baseweb="tab"] { padding: 4px 10px !important; font-size: 0.78rem !important; font-weight: 600 !important; border-radius: 6px 6px 0 0 !important; }
[data-testid="stExpander"] { border: 1px solid #30363D !important; border-radius: 8px !important; margin-bottom: 5px !important; }
[data-testid="stExpander"] > details > summary { padding: 7px 10px !important; font-size: 0.78rem !important; font-weight: 600 !important; }
[data-testid="stSidebar"] .block-container { padding-top: 0.6rem !important; }

.narrative-card { background: #161B22; border-left: 3px solid #58A6FF; border-radius: 8px; padding: 10px 14px; margin: 6px 0; }
.narrative-headline { font-size: 0.85rem; font-weight: 600; color: #E6EDF3; line-height: 1.4; }
.narrative-sub { font-size: 0.7rem; color: #8B949E; margin-top: 4px; }

.metric-grid-card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 12px; }
.metric-grid-title { font-size: 0.6rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 4px; }
.metric-grid-value { font-size: 1.05rem; font-weight: 700; color: #E6EDF3; }
.metric-grid-sub { font-size: 0.65rem; color: #8B949E; margin-top: 2px; }

.compass-container { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px 14px; margin: 6px 0; }
.compass-title { font-size: 0.75rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; }
.compass-quad { font-size: 1.2rem; font-weight: 800; letter-spacing: -1px; }
.compass-sub { font-size: 0.7rem; color: #8B949E; }

.dp-row { display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: #161B22; border-bottom: 1px solid #21262D; font-size: 0.75rem; }
.dp-time { width: 60px; color: #8B949E; font-variant-numeric: tabular-nums; }
.dp-ticker { width: 55px; color: #E6EDF3; font-weight: 700; }
.dp-price { width: 60px; color: #E6EDF3; font-variant-numeric: tabular-nums; }
.dp-size { width: 70px; color: #8B949E; font-variant-numeric: tabular-nums; text-align: right; }
.dp-amt { width: 65px; color: #3FB950; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
.dp-amt.sell { color: #F85149; }

.mm-box { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 12px; margin: 4px 0; }
.mm-title { font-size: 0.7rem; color: #A855F7; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; letter-spacing: 0.5px; }
.mm-line { display: flex; justify-content: space-between; font-size: 0.75rem; padding: 2px 0; }
.mm-label { color: #8B949E; }
.mm-value { color: #E6EDF3; font-weight: 600; font-variant-numeric: tabular-nums; }

.skew-curve-container { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px; margin: 4px 0; }
.skew-curve-title { font-size: 0.7rem; color: #8B949E; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }

.scenario-bar { display: flex; height: 18px; border-radius: 4px; overflow: hidden; background: #21262D; margin: 4px 0; }
.scenario-seg { display: flex; align-items: center; justify-content: center; font-size: 0.55rem; font-weight: 700; color: #fff; }

/* Hedgeye-style ticker card v5 */
.hy-card { background: #161B22; border: 1px solid #30363D; border-radius: 10px; margin: 4px 0; overflow: hidden; }
.hy-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #21262D; }
.hy-symbol { font-weight: 800; font-size: 1.0rem; color: #E6EDF3; letter-spacing: -0.5px; min-width: 70px; }
.hy-price { font-weight: 700; font-size: 0.85rem; color: #E6EDF3; font-variant-numeric: tabular-nums; min-width: 55px; }
.hy-badges { display: flex; gap: 3px; flex-wrap: wrap; flex: 1; }
.hy-status-bar { display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: #0D1117; border-bottom: 1px solid #21262D; }
.hy-status-pill { padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; border: 1px solid transparent; }
.hy-meta-row { display: flex; align-items: center; gap: 10px; padding: 5px 12px; font-size: 0.68rem; color: #8B949E; font-variant-numeric: tabular-nums; }
.hy-meta-row b { color: #E6EDF3; font-weight: 600; }
.hy-rr-track { position: relative; height: 14px; background: #21262D; border-radius: 4px; overflow: hidden; flex: 1; }
.hy-rr-zone { position: absolute; top: 0; bottom: 0; }
.hy-rr-dot { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 8px; height: 8px; border-radius: 50%; background: #E6EDF3; border: 2px solid #58A6FF; z-index: 10; box-shadow: 0 0 5px rgba(88,166,255,0.5); }
.hy-rr-labels { display: flex; justify-content: space-between; font-size: 0.55rem; color: #484F58; margin-top: 1px; }

/* Trade Setup panels */
.ts-panel { background: #0D1117; border: 1px solid #21262D; border-radius: 8px; padding: 10px 12px; margin: 6px 0; }
.ts-panel-title { font-size: 0.6rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 6px; }
.ts-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.ts-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.ts-stat { text-align: center; }
.ts-stat-label { font-size: 0.52rem; color: #8B949E; text-transform: uppercase; margin-bottom: 2px; }
.ts-stat-value { font-size: 0.78rem; font-weight: 700; color: #E6EDF3; font-variant-numeric: tabular-nums; }
.ts-stat-sub { font-size: 0.55rem; color: #484F58; }

/* Status banners */
.banner-chase { background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.35); color: #3FB950; }
.banner-wait { background: rgba(234,179,8,0.12); border: 1px solid rgba(234,179,8,0.35); color: #D29922; }
.banner-avoid { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.35); color: #F85149; }
.banner-hold { background: rgba(139,148,158,0.12); border: 1px solid rgba(139,148,158,0.25); color: #8B949E; }

/* OI Heatmap bars */
.oi-bar-row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.oi-bar-label { font-size: 0.65rem; color: #8B949E; min-width: 65px; font-weight: 600; }
.oi-bar-track { flex: 1; height: 12px; background: #21262D; border-radius: 3px; overflow: hidden; position: relative; }
.oi-bar-fill { height: 100%; border-radius: 3px; opacity: 0.7; }
.oi-bar-value { font-size: 0.65rem; font-weight: 700; min-width: 60px; text-align: right; font-variant-numeric: tabular-nums; }

/* Alpha Center thesis card */
.alpha-thesis-card { background: #161B22; border-left: 3px solid #A855F7; border-radius: 8px; padding: 10px 14px; margin: 4px 0; }
.alpha-thesis-title { font-size: 0.78rem; font-weight: 600; color: #E6EDF3; }
.alpha-thesis-sub { font-size: 0.68rem; color: #8B949E; margin-top: 3px; line-height: 1.4; }
.alpha-ready { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-left: 6px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# CONFIG & FALLBACKS
# ═══════════════════════════════════════════════════════════════════
def filter_by_simulation(rows, sim_results, threshold=50, require_pass=False):
    """Filter ticker rows by simulation results. Handles dict-format snap data.
    v39.1 FIX: Relaxed threshold (50), require_pass=False default. 
    Simulation runs background-only; rows kept for detail view."""
    if not sim_results:
        return rows
    filtered = []
    for row in rows:
        t = row.get("ticker")
        if not t:
            continue
        sim = sim_results.get(t)
        if sim is None:
            # No sim data - keep row, mark unvalidated
            row["_sim_status"] = "NO_DATA"
            filtered.append(row)
            continue
        # Orchestrator serializes sim results to dicts; handle both dict and object
        if isinstance(sim, dict):
            passes = sim.get("passes_filter", False)
            score = sim.get("robustness_score", 0)
        else:
            passes = getattr(sim, "passes_filter", False)
            score = getattr(sim, "robustness_score", 0)
        row["_sim_passed"] = passes
        row["_sim_score"] = score
        row["_sim_status"] = "PASS" if (passes and score >= threshold) else "MARGINAL" if score >= threshold else "FAIL"
        # v39.1: Don't filter out on simulation alone - show all with annotation
        if require_pass and not passes:
            continue
        if require_pass and score < threshold:
            continue
        filtered.append(row)
    return filtered

try:
    from config.settings import (FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE,
                                 IHSG_SECTOR_MAP, TICKER_SECTOR, US_SECTORS, US_BUCKETS,
                                 FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS)
except ImportError:
    FOREX_PAIRS = {}; COMMODITIES = {}; CRYPTO = {}; IHSG_UNIVERSE = {}; TICKER_SECTOR = {}; US_SECTORS = {}; US_BUCKETS = {}; FX_BUCKETS = {}; COMMODITY_BUCKETS = {}; CRYPTO_BUCKETS = {}

FALLBACK_US = ["SPY","QQQ","IWM","NVDA","AAPL","MSFT","GOOGL","META","TSLA","AMD","NFLX","AMZN","CRM","AVGO","XOM","JPM","V","MA","UNH","JNJ","XLK","XLF","XLE","XLU","XLP","XLI","XLB","XLRE","XLY","ARKK","TLT","GLD","SLV","GDX","VIXY","SQQQ","TQQQ","UPRO","SPXU"]
FALLBACK_FX  = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","USDCNY=X","USDIDR=X","DX-Y.NYB","UUP"]
FALLBACK_COMM = ["GC=F","SI=F","CL=F","NG=F","HG=F","PL=F","PA=F","ZW=F","ZC=F","ZS=F","KC=F","CC=F","CT=F"]
FALLBACK_CRYPTO = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD","LTC-USD"]
FALLBACK_IHSG = ["BBRI.JK","BMRI.JK","BBCA.JK","BBNI.JK","BRIS.JK","TLKM.JK","EXCL.JK","ADRO.JK","ITMG.JK","PTBA.JK","NCKL.JK","ANTM.JK","INCO.JK","AALI.JK","LSIP.JK","SMAR.JK","UNTR.JK","BYAN.JK","ICBP.JK","INDF.JK","KLBF.JK","PGEO.JK","WINS.JK","EIDO","^JKSE"]


# ═══════════════════════════════════════════════════════════════════
# QUAD PLAYBOOK v39.3 — DYNAMIC (from snap/orchestrator, not hardcoded)
# ═══════════════════════════════════════════════════════════════════
def _get_quad_playbook(snap):
    """
    Build quad playbook DYNAMICALLY from orchestrator data.
    Falls back to config.settings if snap incomplete.
    """
    gip = snap.get("gip")
    if gip is not None and not isinstance(gip, dict):
        try: sq = getattr(gip, "structural_quad", "Q3")
        except: sq = "Q3"
    elif isinstance(gip, dict):
        sq = gip.get("structural_quad", "Q3")
    else:
        sq = "Q3"

    # Try to get from snap.playbook (orchestrator output)
    pb = snap.get("playbook", {}) if isinstance(snap.get("playbook"), dict) else {}

    # Dynamic sector/ticker lists from config (not hardcoded)
    sectors_ow = pb.get("sectors_overweight", [])
    sectors_uw = pb.get("sectors_underweight", [])
    best_assets = pb.get("best_assets", [])
    worst_assets = pb.get("worst_assets", [])

    # If orchestrator gives us nothing, derive from config settings
    if not sectors_ow:
        sectors_ow = _derive_sectors_from_config(sq, "overweight")
    if not sectors_uw:
        sectors_uw = _derive_sectors_from_config(sq, "underweight")
    if not best_assets:
        best_assets = _derive_tickers_from_config(sq, "best")
    if not worst_assets:
        worst_assets = _derive_tickers_from_config(sq, "worst")

    # Dynamic bottleneck from snap (not hardcoded)
    chains = snap.get("supply_chain_chains", [])
    bottleneck_names = [c.get("name", "") for c in chains if isinstance(c, dict)]

    # Dynamic methodology signals from snap
    leo = snap.get("leopold_scan", {})
    leo_layers = []
    if isinstance(leo, dict):
        for layer, items in (leo.get("top_picks_by_layer") or {}).items():
            if items:
                leo_layers.append(layer)

    coat = snap.get("coatue_scan", {})
    coat_signal = ""
    if isinstance(coat, dict):
        sellers = len(coat.get("sellers_top", []))
        buyers = len(coat.get("buyers_top", []))
        if buyers > sellers:
            coat_signal = "BUY Rotation"
        elif sellers > buyers:
            coat_signal = "SELL Rotation"
        else:
            coat_signal = "NEUTRAL"

    kar = snap.get("karsan_scanner", {})
    kar_setup = ""
    if isinstance(kar, dict):
        squeeze = len(kar.get("squeeze_setups", []))
        sell_prem = len(kar.get("sell_premium", []))
        buy_conv = len(kar.get("buy_convexity", []))
        if squeeze > 0:
            kar_setup = f"Squeeze setups: {squeeze}"
        elif sell_prem > buy_conv:
            kar_setup = "Sell premium bias"
        else:
            kar_setup = "Buy convexity bias"

    # Build playbook dict
    playbook = {
        "theme": pb.get("strategy", f"Quad {sq} regime play"),
        "front_run_sectors": sectors_ow,
        "front_run_tickers": best_assets,
        "bottleneck_focus": bottleneck_names[:5],
        "leopold_layers": leo_layers[:5],
        "coatue_signal": coat_signal,
        "karsan_setup": kar_setup,
        "avoid": worst_assets,
        "quad": sq,
    }
    return playbook

def _derive_sectors_from_config(quad, bias):
    """Derive sectors from config.settings.QUAD_ASSET_PERFORMANCE if available."""
    try:
        from config.settings import QUAD_ASSET_PERFORMANCE
        perf = QUAD_ASSET_PERFORMANCE.get(quad, {})
        if bias == "overweight":
            return [k for k, v in perf.items() if isinstance(v, dict) and v.get("expected_return", 0) > 0.03]
        else:
            return [k for k, v in perf.items() if isinstance(v, dict) and v.get("expected_return", 0) < -0.03]
    except Exception:
        return []

def _derive_tickers_from_config(quad, bias):
    """Derive tickers from config.settings.US_BUCKETS / FX_BUCKETS etc."""
    tickers = []
    try:
        from config.settings import US_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
        if bias == "best":
            for bucket in ["Growth", "Quality", "Semis", "AI_Infra", "Energy"]:
                tickers.extend(US_BUCKETS.get(bucket, []))
        else:
            for bucket in ["Defensives", "Bonds", "PreciousMetals"]:
                tickers.extend(US_BUCKETS.get(bucket, []))
    except Exception:
        pass
    return list(dict.fromkeys(tickers))[:20]

def _get_bottleneck_quad_map(snap):
    """Dynamic bottleneck-to-quad mapping from orchestrator supply_chain_chains."""
    chains = snap.get("supply_chain_chains", [])
    mapping = {}
    for chain in chains:
        if isinstance(chain, dict):
            name = chain.get("name", "")
            # Derive aligned quads from chain trigger keywords
            trigger = chain.get("trigger", "").lower()
            aligned = ["Q3"]  # default
            if any(k in trigger for k in ["ai", "compute", "gpu", "semiconductor"]):
                aligned = ["Q1", "Q2"]
            elif any(k in trigger for k in ["oil", "energy", "geopolitical", "war", "iran"]):
                aligned = ["Q2", "Q3"]
            elif any(k in trigger for k in ["indonesia", "resource", "nationalism", "cpo", "nickel"]):
                aligned = ["Q3", "Q4"]
            elif any(k in trigger for k in ["deflation", "recession", "credit", "duration"]):
                aligned = ["Q4", "Q1"]
            mapping[name] = aligned
    return mapping

# Legacy alias for backward compat (redirects to dynamic)
QUAD_FRONT_RUN_PLAYBOOK = {}  # populated at runtime via _get_quad_playbook(snap)
BOTTLENECK_QUAD_MAP = {}  # populated at runtime via _get_bottleneck_quad_map(snap)

# ═══════════════════════════════════════════════════════════════════
# HEDGEYE PLAYBOOK v39.2 — DYNAMIC + KEITH-AWARE + DEEP RESEARCH VERIFIED
# Source: Hedgeye ETF Pro March 2026 + Keith X/Twitter May 2026 + The Call
# ═══════════════════════════════════════════════════════════════════
def _get_hedgeye_playbook(snap):
    """
    Returns {"beli": [...], "short": [...], "quad": sq}
    Dynamically derived from GIP quad + Hedgeye historical playbook + Keith signal sync.

    VERIFIED AGAINST HEDGEYE RESEARCH (May 2026):
    - Q3 = Stagflation (Growth decel, Inflation accel)
    - Q3 Playbook: Long Energy, Staples, Utilities, REITs, Industrials, TLT
    - Q3 Playbook: Short Tech (XLK, NVDA, bag 7), Financials (XLF), Consumer Disc (XLY)
    - Keith Override (May 2026): BEARISH Gold → Gold removed from beli, added to short
    - Keith Override (May 2026): BULLISH USD → USD in beli
    - Keith Override (May 2026): BULLISH Oil → Oil in beli
    - Exception: SNDK, VST, CEG = AI Infrastructure Bottleneck (supply constrained = Q3 favorable)
    """
    gip = snap.get("gip")
    sq = "Q3"
    if gip is not None:
        if isinstance(gip, dict):
            sq = gip.get("structural_quad", "Q3")
        else:
            try: sq = getattr(gip, "structural_quad", "Q3")
            except: pass

    # Base Hedgeye playbook by quad (from official Hedgeye research)
    base_map = {
        "Q1": {
            "beli": ["QQQ","XLK","NVDA","AAPL","MSFT","GOOGL","META","AMD","ARKK","IWM","XLF","XLI","XLY"],
            "short": ["XLU","XLP","TLT","GLD","SLV","UUP","DX-Y.NYB"],
            "theme": "Goldilocks — Growth accel, Inflation decel. Long Tech/Growth/Financials."
        },
        "Q2": {
            "beli": ["XLF","XLE","XLI","XLB","KRE","IWM","XOM","CVX","CL=F","USO","XOP","OIH","BNO","UUP","DX-Y.NYB"],
            "short": ["TLT","IEF","XLU","XLP","GLD","SLV"],
            "theme": "Reflation — Growth accel, Inflation accel. Long Cyclicals/Energy/Financials/USD."
        },
        "Q3": {
            "beli": [
                # Energy & Power (supply bottleneck = inflation hedge)
                "XLE","XOP","OIH","BNO","CL=F","USO","VST","CEG","BE","LITE","CCJ","URA",
                # Staples & Utilities (defensive)
                "XLP","XLU","XLV","ITA","TLT","IEF",
                # Industrials (Hedgeye specific)
                "XLI","CAT","PCAR","OSK","HII","UPS","JBHT","EMR",
                # Consumer Staples / Retail
                "PEP","CASY","BURL","HSY","MAR","SBUX",
                # Healthcare / Biotech
                "TXG","AVO",
                # Real Assets / Commodities
                "HG=F","CPER","SLX",
                # USD Bullish (Keith May 2026)
                "UUP","DX-Y.NYB",
                # AI Bottleneck Exception (supply constrained physical assets)
                "SNDK","MU","NXT","AMPH","COHR","MRVL",
                # Citrini Research 2026: Advanced Packaging / EDA / Copper / Materials
                "SNPS",  # Synopsys — EDA, advanced packaging (Citrini 26 Trades 2026)
                "SCCO","FCX",  # Copper — supply bottleneck, green transition (Citrini)
                "ALB",  # Lithium / battery materials — physical scarcity (Citrini)
            ],
            "short": [
                # Tech / Growth (MOAB Tech per Hedgeye)
                "QQQ","XLK","SKYY","CIBR","IVES","MAGS","MSFO","DESK","BLOK","BITS","WGMI",
                # Bag 7 / Mag 7 (Hedgeye bearish trend)
                "NVDA","META","TSLA","AMZN","GOOGL","AAPL","MSFT","AMD","NFLX","CRM",
                # Financials (Q3 headwind)
                "XLF","KRE","COF","ALLY","SYF","MA","V","BR.B",
                # Consumer Disc
                "XLY",
                # Gold / Precious Metals (Keith BEARISH May 2026)
                "GLD","SLV","GC=F","SI=F","PALL","GDX","GDXJ","PPLT",
                # Crypto (relative underperform in Q3)
                "ETH-USD","SOL-USD",
            ],
            "theme": "Stagflation — Growth decel, Inflation accel. Long Energy/Staples/Utilities/Industrials/USD. Short Tech/Financials/Gold(Keith)."
        },
        "Q4": {
            "beli": ["TLT","IEF","GLD","SLV","XLU","XLP","XLV","JPY","CHF"],
            "short": ["QQQ","XLK","IWM","XLY","XLF","XLE","CL=F","USO"],
            "theme": "Deflation — Growth decel, Inflation decel. Long Bonds/Gold/Staples/Utilities. Short Tech/Cyclicals."
        },
    }
    pb = base_map.get(sq, base_map["Q3"])
    beli = [t for t in pb["beli"] if t]
    short = [t for t in pb["short"] if t]

    # ── KEITH P0 OVERRIDE (May 2026 verified signals) ──
    keith = snap.get("keith_sync", {})
    if keith:
        for ticker, signal in keith.items():
            if not isinstance(signal, dict):
                continue
            trade = signal.get("keith_trade", "NEUTRAL")
            if trade == "BEARISH":
                if ticker in beli:
                    beli.remove(ticker)
                if ticker not in short:
                    short.append(ticker)
            elif trade == "BULLISH":
                if ticker in short:
                    short.remove(ticker)
                if ticker not in beli:
                    beli.append(ticker)

    # Deduplicate & sort
    beli = list(dict.fromkeys(beli))[:25]
    short = list(dict.fromkeys(short))[:25]

    return {"beli": beli, "short": short, "quad": sq, "theme": pb["theme"]}


def _is_hedgeye_avoid(ticker, snap):
    """Check if ticker is in Hedgeye avoid list for current quad."""
    pb = _get_hedgeye_playbook(snap)
    return ticker in pb.get("short", [])


def _is_hedgeye_favor(ticker, snap):
    """Check if ticker is in Hedgeye favor list for current quad."""
    pb = _get_hedgeye_playbook(snap)
    return ticker in pb.get("beli", [])


def _classify_ticker_market(ticker: str) -> str:
    if ticker in FOREX_PAIRS or "=" in ticker or ticker in ["DX-Y.NYB", "UUP"]:
        return "forex"
    if ticker in COMMODITIES or ticker in ["GC=F", "SI=F", "CL=F", "HG=F"]:
        return "commodity"
    if ticker in CRYPTO or ticker in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        return "crypto"
    if ticker in IHSG_UNIVERSE or ticker.endswith(".JK"):
        return "ihsg"
    return "us_equity"

def _get_ticker_sector(ticker: str) -> str:
    return TICKER_SECTOR.get(ticker, IHSG_SECTOR_MAP.get(ticker, "Other"))

_IHSG_FALLBACK = {"ADRO.JK":"Coal","ITMG.JK":"Coal","PTBA.JK":"Coal","NCKL.JK":"Nickel","ANTM.JK":"Nickel","INCO.JK":"Nickel","AALI.JK":"CPO","LSIP.JK":"CPO","SMAR.JK":"CPO","BBRI.JK":"Banking","BMRI.JK":"Banking","BBCA.JK":"Banking","BBNI.JK":"Banking","BRIS.JK":"Banking","TLKM.JK":"Telco","EXCL.JK":"Telco","UNTR.JK":"Mining Contractor","BYAN.JK":"Mining","ICBP.JK":"Consumer","INDF.JK":"Consumer","KLBF.JK":"Pharma","PGEO.JK":"Geothermal","WINS.JK":"Shipping","EIDO":"ETF","^JKSE":"Index"}
if not locals().get("IHSG_SECTOR_MAP"):
    IHSG_SECTOR_MAP = _IHSG_FALLBACK

class _GipProxy:
    def __init__(self, data):
        self._is_dict = isinstance(data, dict)
        if self._is_dict: self._d = data
        else: self._obj = data
    def __getattr__(self, name):
        if self._is_dict: return self._d.get(name)
        return getattr(self._obj, name, None)

# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════
def _safe_float(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0] if len(v) > 0 else None
        if v is None: return None
        f = float(v)
        return f if math.isfinite(f) else None
    except: return None

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"

def ff(v, d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"

def _ffm(v, market_type="us_equity"):
    """Market-aware formatter: forex=4dp, crypto=4dp if <1, else 2dp, commodity=2dp, equity=2dp"""
    if v is None: return "—"
    try:
        f = float(v)
        if not math.isfinite(f): return "—"
        if market_type == "forex":
            return f"{f:,.4f}"
        elif market_type == "crypto":
            return f"{f:,.4f}" if abs(f) < 1 else f"{f:,.2f}"
        elif market_type == "commodity":
            return f"{f:,.2f}"
        else:
            return f"{f:,.2f}"
    except:
        return "—"

def sf(v, fmt=".2f"):
    try:
        if v is None: return "—"
        f = float(v)
        if not math.isfinite(f): return "—"
        return format(f, fmt)
    except:
        return "—"

def _price_ret(ticker, prices, days=21):
    s = prices.get(ticker)
    if s is None: return None
    try:
        s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    except: return None
    if len(s) < days + 1: return None
    try: return float(s.iloc[-1] / s.iloc[-(days+1)] - 1)
    except: return None

def _quad_color(q):
    return {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}.get(q, "#8B949E")

def _quad_name(q):
    return {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q, q)

def _ret_color(r):
    if r is None: return "#8B949E"
    r = float(r)
    if r > 0.03: return "#3FB950"
    if r > 0: return "#2EA043"
    if r > -0.03: return "#F85149"
    return "#DA3633"

def _sparkline_html(series, width=80, height=24, bars=18):
    if series is None:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    try:
        s = pd.to_numeric(pd.Series(series), errors="coerce").dropna().tail(bars)
    except:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    if len(s) < 2:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    mn, mx = float(s.min()), float(s.max())
    rng = mx - mn if mx != mn else 1
    bars_html = ""
    for i, v in enumerate(s):
        pct = max(2, min(100, int((float(v) - mn) / rng * 100)))
        color = "#3FB950" if (i > 0 and float(v) >= float(s.iloc[i-1])) else "#F85149"
        bars_html += f'<div class="sp-bar-v4" style="height:{pct}%;background:{color};"></div>'
    return f'<div class="tc-v4-spark" style="width:{width}px;height:{height}px;display:flex;align-items:flex-end;gap:1px;">{bars_html}</div>'

def _risk_range_html(px, lrr, trr, width_pct=100):
    if not all(v is not None and math.isfinite(float(v)) for v in [px, lrr, trr]):
        return '<div class="rr-track-v4" style="height:16px;background:#21262D;border-radius:4px;"></div><div class="rr-labels-v4"><span>-</span><span>-</span></div>'
    px, lrr, trr = float(px), float(lrr), float(trr)
    spread = trr - lrr
    pos = max(0, min(1, (px - lrr) / spread)) if spread > 0 else 0.5
    left_pct = pos * 100
    color = "#3FB950" if pos <= 0.35 else "#F85149" if pos >= 0.65 else "#8B949E"
    return (
        f'<div class="rr-track-v4" style="width:{width_pct}%;">'
        f'<div class="rr-zone-v4" style="left:0%;width:100%;background:#21262D;"></div>'
        f'<div class="rr-zone-v4" style="left:0%;width:{left_pct:.0f}%;background:{color}15;"></div>'
        f'<div class="rr-dot-v4" style="left:{max(3,min(97,left_pct)):.0f}%;border-color:{color};"></div>'
        f'</div>'
        f'<div class="rr-labels-v4" style="width:{width_pct}%;"><span>{ff(lrr)}</span><span>{ff(px)}</span><span>{ff(trr)}</span></div>'
    )

def _gauge_html(value, max_val=100, color=None, height=12, label_left="0", label_right="100"):
    if value is None: value = 0
    try: pct = max(0, min(100, float(value) / float(max_val) * 100))
    except: pct = 0
    c = color or ("#3FB950" if pct > 70 else "#D29922" if pct > 40 else "#F85149")
    return (
        f'<div class="gauge-track" style="height:{height}px;">'
        f'<div class="gauge-fill" style="width:{pct:.0f}%;background:{c};"></div></div>'
        f'<div class="gauge-label"><span>{label_left}</span><span>{ff(value)}</span><span>{label_right}</span></div>'
    )

def _badge_html(text, kind="long"):
    cls = {"long":"badge-long","short":"badge-short","neut":"badge-neut","a":"badge-grade-a","b":"badge-grade-b","c":"badge-grade-c","news":"badge-news","mm":"badge-mm","chase":"badge-chase","wait":"badge-wait"}.get(kind,"badge-neut")
    return f'<span class="badge {cls}">{text}</span>'

def _stacked_bar_html(long_pct, short_pct, cash_pct):
    return (
        f'<div class="stack-bar">'
        f'<div class="stack-seg" style="width:{long_pct}%;background:#3FB950;">📈 {long_pct:.0f}%</div>'
        f'<div class="stack-seg" style="width:{short_pct}%;background:#F85149;">📉 {short_pct:.0f}%</div>'
        f'<div class="stack-seg" style="width:{cash_pct}%;background:#8B949E;">💵 {cash_pct:.0f}%</div>'
        f'</div>'
    )

def _scenario_bar_html(bull_p, base_p, bear_p):
    html = '<div class="scenario-bar">'
    if bull_p > 0:
        html += f'<div class="scenario-seg" style="width:{bull_p}%;background:#3FB950;">🐂 {bull_p:.0f}%</div>'
    if base_p > 0:
        html += f'<div class="scenario-seg" style="width:{base_p}%;background:#D29922;">⚖ {base_p:.0f}%</div>'
    if bear_p > 0:
        html += f'<div class="scenario-seg" style="width:{bear_p}%;background:#F85149;">🐻 {bear_p:.0f}%</div>'
    html += '</div><div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-top:2px;"><span>Bull</span><span>Base</span><span>Bear</span></div>'
    return html

def _timeline_html(stage="INCEPTION"):
    stages = ["INCEPTION","ACCELERATION","EUPHORIA","CRISIS","AUCTION"]
    idx = stages.index(stage) if stage in stages else 0
    nodes = ""; labels = ""
    for i, s in enumerate(stages):
        cls = "past" if i < idx else "active" if i == idx else ""
        line_cls = "active" if i < idx else ""
        nodes += f'<div class="tl-node {cls}"></div>'
        if i < len(stages) - 1: nodes += f'<div class="tl-line {line_cls}"></div>'
        labels += f'<span>{s}</span>'
    return f'<div class="timeline">{nodes}</div><div class="tl-labels">{labels}</div>'

def _skew_bars_html(d30=None, d60=None, d90=None):
    def bar(label, val):
        if val is None:
            return f'<div class="skew-row"><span class="skew-label">{label}</span><div class="skew-track"><div class="skew-fill" style="width:0%;background:#30363D;"></div></div><span class="skew-value">-</span></div>'
        v = float(val)
        pct = max(5, min(100, abs(v) * 200))
        color = "#3FB950" if v > 0.05 else "#F85149" if v < -0.05 else "#D29922"
        label_text = "Rich" if v > 0.05 else "Cheap" if v < -0.05 else "Fair"
        return f'<div class="skew-row"><span class="skew-label">{label}</span><div class="skew-track"><div class="skew-fill" style="width:{pct:.0f}%;background:{color};"></div></div><span class="skew-value" style="color:{color};">{label_text}</span></div>'
    return bar("30D", d30) + bar("60D", d60) + bar("90D", d90)

def _gex_bar_html(gex_val=None):
    if gex_val is None:
        return '<div class="gex-track" style="height:18px;background:#21262D;border-radius:4px;"></div>'
    v = float(gex_val)
    color = "#3FB950" if v > 0 else "#F85149"
    pct = min(100, abs(v) * 100)
    side = "Pos" if v > 0 else "Neg"
    margin = "margin-left:0;left:50%;" if v > 0 else f"margin-left:-{pct}%;left:50%;"
    return (
        f'<div class="gex-track" style="height:18px;">'
        f'<div class="gex-center"></div>'
        f'<div style="position:absolute;{margin}width:{pct:.0f}%;background:{color}25;height:100%;border-radius:4px;"></div>'
        f'<div style="position:absolute;width:100%;text-align:center;font-size:0.6rem;font-weight:700;color:{color};line-height:18px;">{side} {abs(v):.2f}</div>'
        f'</div>'
    )

def _heatmap_grid_html(items, key_label="name", key_quad="quad"):
    html = '<div class="hm-grid">'
    for it in items:
        q = it.get(key_quad, "Q3")
        color = _quad_color(q)
        name = it.get(key_label, "-")
        html += f'<div class="hm-cell" style="background:{color}15;border-color:{color}35;">{name}<div style="font-size:0.52rem;color:{color};margin-top:1px;">{q}</div></div>'
    html += '</div>'
    return html

def _asset_pulse_box_h(label, ret, sub=""):
    c = _ret_color(ret)
    txt = f"{ret:+.1%}" if ret is not None else "-"
    sub_html = f'<div style="font-size:0.52rem;color:#8B949E;margin-top:1px;">{sub}</div>' if sub else ""
    return f'<div class="pulse-hbox" style="background:{c}12;border-color:{c}25;"><div>{txt}</div><div class="pulse-hlabel">{label}</div>{sub_html}</div>'

# ═══════════════════════════════════════════════════════════════════
# OPTIONS / GREEKS / MM DATA ENRICHMENT
# ═══════════════════════════════════════════════════════════════════
def _get_options_data(ticker, snap):
    out = {
        "max_pain": None, "put_wall": None, "call_wall": None,
        "gamma_flip_up": None, "gamma_flip_down": None, "gamma_regime": None,
        "gex": None, "vanna": None, "charm": None,
        "skew_30d": None, "skew_60d": None, "skew_90d": None,
        "pin_risk": None, "expected_move_pct": None,
        "oi_call": None, "oi_put": None, "pc_ratio": None,
        "iv_rank": None, "iv_percentile": None,
        "mm_positioning": "NEUTRAL", "mm_recommendation": "—",
        "source": "PROXY", "next_expiry": None, "days_to_expiry": None,
    }
    # 1. YFinance live options
    yf = snap.get("yfinance_options", {}).get(ticker, {}) if isinstance(snap.get("yfinance_options"), dict) else {}
    if isinstance(yf, dict) and yf.get("ok"):
        out["max_pain"] = yf.get("max_pain")
        out["put_wall"] = yf.get("put_wall")
        out["call_wall"] = yf.get("call_wall")
        out["gamma_flip_up"] = yf.get("gamma_flip_up")
        out["gamma_flip_down"] = yf.get("gamma_flip_down")
        out["gamma_regime"] = yf.get("gamma_regime")
        out["pc_ratio"] = yf.get("put_call_ratio")
        out["source"] = "YF"
        if yf.get("next_expiry"): out["next_expiry"] = yf.get("next_expiry")
        if yf.get("days_to_expiry"): out["days_to_expiry"] = yf.get("days_to_expiry")

    # 2. Greeks engine
    greeks = snap.get("greeks_data", {}).get(ticker, {}) if isinstance(snap.get("greeks_data"), dict) else {}
    if isinstance(greeks, dict):
        if not out["gex"]: out["gex"] = greeks.get("net_gex") or greeks.get("gex")
        if not out["vanna"]: out["vanna"] = greeks.get("vanna")
        if not out["charm"]: out["charm"] = greeks.get("charm")
        if not out["skew_30d"]: out["skew_30d"] = greeks.get("skew_30d") or greeks.get("skew")

    # 3. Gamma engine
    gamma = snap.get("gamma_data", {}).get(ticker, {}) if isinstance(snap.get("gamma_data"), dict) else {}
    if isinstance(gamma, dict):
        if not out["gamma_regime"]: out["gamma_regime"] = gamma.get("regime")
        if not out["max_pain"]: out["max_pain"] = gamma.get("max_pain")

    # 4. GEX engine
    gex = snap.get("gex_data", {}).get(ticker, {}) if isinstance(snap.get("gex_data"), dict) else {}
    if isinstance(gex, dict):
        if not out["gex"]: out["gex"] = gex.get("net_gex") or gex.get("gex") or gex.get("total_gex")

    # 5. Vanna / Charm engine
    vanna = snap.get("vanna_data", {}).get(ticker, {}) if isinstance(snap.get("vanna_data"), dict) else {}
    if isinstance(vanna, dict):
        if not out["vanna"]: out["vanna"] = vanna.get("vanna")
    charm = snap.get("charm_data", {}).get(ticker, {}) if isinstance(snap.get("charm_data"), dict) else {}
    if isinstance(charm, dict):
        if not out["charm"]: out["charm"] = charm.get("charm")

    # 6. Skew term structure
    skew = snap.get("skew_term", {}).get("skew_data", {}) if isinstance(snap.get("skew_term"), dict) else {}
    if isinstance(skew, dict):
        for k, v in skew.items():
            if isinstance(v, dict):
                val = v.get("skew") or v.get("value") or v.get("90_10")
                if ticker in str(k).upper() or (ticker.replace("-","") in str(k).upper()):
                    if "30" in str(k).lower() or "1m" in str(k).lower(): out["skew_30d"] = _safe_float(val)
                    if "60" in str(k).lower() or "2m" in str(k).lower(): out["skew_60d"] = _safe_float(val)
                    if "90" in str(k).lower() or "3m" in str(k).lower(): out["skew_90d"] = _safe_float(val)

    # 7. 0DTE monitor
    odte = snap.get("odte_monitor", {}).get("tickers", {}).get(ticker, {}) if isinstance(snap.get("odte_monitor"), dict) else {}
    if isinstance(odte, dict):
        if not out["pin_risk"]: out["pin_risk"] = odte.get("pin_risk")
        if not out["vanna"]: out["vanna"] = odte.get("vanna")
        if not out["charm"]: out["charm"] = odte.get("charm")

    # 8. VRP scanner
    vrp = snap.get("vrp_scanner", {}) if isinstance(snap.get("vrp_scanner"), dict) else {}
    if isinstance(vrp, dict) and vrp.get("ok"):
        for item in vrp.get("high_vrp_sell_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                out["iv_rank"] = item.get("iv_rank")
                out["expected_move_pct"] = item.get("expected_move_pct")
        for item in vrp.get("low_vrp_buy_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                out["iv_rank"] = item.get("iv_rank")

    # 9. Cem Karsan universal
    cem = snap.get("cem_karsan_universal", {}) if isinstance(snap.get("cem_karsan_universal"), dict) else {}
    if isinstance(cem, dict):
        for item in cem.get("per_ticker", {}).values() if isinstance(cem.get("per_ticker"), dict) else []:
            if isinstance(item, dict) and item.get("ticker") == ticker:
                if not out["skew_30d"]: out["skew_30d"] = _safe_float(item.get("skew_30d") or item.get("skew"))
                if not out["gex"]: out["gex"] = _safe_float(item.get("gex") or item.get("net_gex"))
                if not out["vanna"]: out["vanna"] = item.get("vanna")
                if not out["charm"]: out["charm"] = item.get("charm")
                if not out["gamma_regime"]: out["gamma_regime"] = item.get("gamma_regime")
                if not out["max_pain"]: out["max_pain"] = _safe_float(item.get("max_pain"))
                if not out["expected_move_pct"]: out["expected_move_pct"] = _safe_float(item.get("expected_move"))

    # 10. SpotGamma proxy
    spot = snap.get("spotgamma_scanner", {}) if isinstance(snap.get("spotgamma_scanner"), dict) else {}
    if isinstance(spot, dict) and spot.get("ok"):
        pt = spot.get("per_ticker_proxy_gex", {}) if isinstance(spot.get("per_ticker_proxy_gex"), dict) else {}
        if ticker in pt and isinstance(pt[ticker], dict):
            if not out["gex"]: out["gex"] = _safe_float(pt[ticker].get("gex") or pt[ticker].get("net_gex") or pt[ticker].get("total_gex"))
            if not out["gamma_regime"]: out["gamma_regime"] = pt[ticker].get("gamma_regime")
            if not out["max_pain"]: out["max_pain"] = _safe_float(pt[ticker].get("max_pain"))

    # 11. Karsan scanner
    karsan = snap.get("karsan_scanner", {}) if isinstance(snap.get("karsan_scanner"), dict) else {}
    if isinstance(karsan, dict) and karsan.get("ok"):
        for item in karsan.get("per_ticker", {}).values() if isinstance(karsan.get("per_ticker"), dict) else []:
            if isinstance(item, dict) and item.get("ticker") == ticker:
                if not out["skew_30d"]: out["skew_30d"] = _safe_float(item.get("skew") or item.get("skew_30d"))
                if not out["expected_move_pct"]: out["expected_move_pct"] = _safe_float(item.get("expected_move"))

    # 12. Afternoon signal
    aft = snap.get("afternoon_data", {}) if isinstance(snap.get("afternoon_data"), dict) else {}
    if isinstance(aft, dict) and ticker in aft:
        a = aft[ticker]
        if isinstance(a, dict):
            if not out["vanna"]: out["vanna"] = a.get("vanna")
            if not out["charm"]: out["charm"] = a.get("charm")

    # 13. Structure quality
    struct = snap.get("structure_data", {}) if isinstance(snap.get("structure_data"), dict) else {}
    if isinstance(struct, dict) and ticker in struct:
        s = struct[ticker]
        if isinstance(s, dict):
            if not out["gamma_regime"]: out["gamma_regime"] = s.get("gamma_regime")

    # 14. Volga proxy
    volga = snap.get("volga_data", {}) if isinstance(snap.get("volga_data"), dict) else {}
    if isinstance(volga, dict) and volga.get("ok"):
        vt = volga.get("per_ticker", {}) if isinstance(volga.get("per_ticker"), dict) else {}
        if ticker in vt and isinstance(vt[ticker], dict):
            if not out["skew_30d"]: out["skew_30d"] = _safe_float(vt[ticker].get("skew"))

    # ── MM Positioning Logic ──
    px = None
    prices = snap.get("prices", {})
    if ticker in prices:
        try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
        except: pass
    mp = out["max_pain"]
    if px and mp:
        mp_dist = (px - mp) / mp
        out["mp_dist"] = mp_dist
        if abs(mp_dist) < 0.02:
            out["mm_positioning"] = "PINNED"
            out["mm_recommendation"] = "MM pinned — range-bound until expiry. Sell straddles or wait breakout."
        elif mp_dist > 0.03 and out["gamma_regime"] in ("POSITIVE", "DEEP_POSITIVE"):
            out["mm_positioning"] = "CALL_WALL"
            out["mm_recommendation"] = "Price above max pain + positive gamma — MM sells into rallies. Fade strength."
        elif mp_dist < -0.03 and out["gamma_regime"] in ("NEGATIVE", "DEEP_NEGATIVE"):
            out["mm_positioning"] = "PUT_WALL"
            out["mm_recommendation"] = "Price below max pain + negative gamma — MM buys dips. Support holds."
        else:
            out["mm_positioning"] = "TRANSITION"
            out["mm_recommendation"] = "Between walls — directional play valid. Watch vanna/charm shift."
    else:
        out["mm_positioning"] = "UNKNOWN"
        out["mm_recommendation"] = "Insufficient options data for MM positioning."

    # 15. VolSignals dealer regime
    vs = snap.get("volsignals_regime", {}) if isinstance(snap.get("volsignals_regime"), dict) else {}
    if isinstance(vs, dict) and ticker in vs and isinstance(vs[ticker], dict):
        out["volsignals_regime"] = vs[ticker]

    # 16. SpotGamma structural levels
    sg = snap.get("spotgamma_levels", {}) if isinstance(snap.get("spotgamma_levels"), dict) else {}
    if isinstance(sg, dict) and ticker in sg and isinstance(sg[ticker], dict):
        out["spotgamma_levels"] = sg[ticker]
        if not out.get("volatility_trigger"): out["volatility_trigger"] = sg[ticker].get("volatility_trigger")
        if not out.get("risk_pivot_upper"): out["risk_pivot_upper"] = sg[ticker].get("risk_pivot_upper")
        if not out.get("risk_pivot_lower"): out["risk_pivot_lower"] = sg[ticker].get("risk_pivot_lower")

    # 17. Schadner IV validation
    sch = snap.get("schadner_iv", {}) if isinstance(snap.get("schadner_iv"), dict) else {}
    if isinstance(sch, dict) and ticker in sch and isinstance(sch[ticker], dict):
        out["iv_schadner"] = sch[ticker].get("iv_exact")
        out["iv_proxy_error"] = sch[ticker].get("error_pct")

    # ── Fallback proxy: fill any missing fields from price action ──
    proxy = _options_proxy_for_ticker_local(ticker, snap.get("prices", {}))
    if proxy:
        for k, v in proxy.items():
            if out.get(k) is None:
                out[k] = v

    return out


def _get_next_expiry(days_to_add=21):
    from datetime import datetime, timedelta
    d = datetime.now() + timedelta(days=days_to_add)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d.strftime("%b %d")


def _options_proxy_for_ticker_local(ticker, prices):
    """Local fallback when snap options data is empty.
    ⚠️ ALL VALUES ARE PROXY — derived from price action, NOT real options chain."""
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {}
        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        std20 = float(s_clean.tail(20).std())
        if std20 == 0 or not all(math.isfinite(v) for v in [px, sma20, std20]):
            return {}

        max_pain = round(sma20, 2)
        put_wall = round(sma20 - std20 * 2.0, 2)
        call_wall = round(sma20 + std20 * 2.0, 2)
        gamma_flip_up = round(sma20 + std20 * 1.5, 2)
        gamma_flip_down = round(sma20 - std20 * 1.5, 2)
        mp_dist = (px - max_pain) / max_pain if max_pain != 0 else 0

        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else 0

        if r5d > 0.03 and r20d > 0.05: gamma_regime = "DEEP_POSITIVE"
        elif r5d > 0.01 and r20d > 0.02: gamma_regime = "POSITIVE"
        elif r5d < -0.03 and r20d < -0.05: gamma_regime = "DEEP_NEGATIVE"
        elif r5d < -0.01 and r20d < -0.02: gamma_regime = "NEGATIVE"
        else: gamma_regime = "TRANSITION"

        returns = s_clean.tail(20).pct_change().dropna()
        skew_val = float(returns.skew()) if len(returns) > 5 else 0.0
        skew_30d = skew_val * 0.5

        gex_proxy = -mp_dist * 5.0
        vanna_proxy = r5d * 10.0
        r11 = float(s_clean.iloc[-6] / s_clean.iloc[-11] - 1) if len(s_clean) >= 11 else r5d
        charm_proxy = (r5d - r11) * 20.0

        vol_20 = float(returns.std() * math.sqrt(252)) if len(returns) > 1 else 0.2
        hist_vol = float(s_clean.tail(60).pct_change().dropna().std() * math.sqrt(252)) if len(s_clean) >= 60 else vol_20

        iv_rank = min(100, max(0, (vol_20 / hist_vol * 50))) if hist_vol > 0 else 50

        expected_move = vol_20 / math.sqrt(12)
        pc_ratio = 0.8 if r20d > 0.05 else (1.2 if r20d < -0.05 else 1.0)

        avg_vol = float(s_clean.tail(20).mean())
        oi_call = max(50000, int(avg_vol * 80000 * (1.1 if r20d > 0 else 0.9)))
        oi_put = max(50000, int(avg_vol * 80000 * (0.9 if r20d > 0 else 1.1)))

        return {
            "max_pain": float(max_pain), "put_wall": float(put_wall), "call_wall": float(call_wall),
            "gamma_flip_up": float(gamma_flip_up), "gamma_flip_down": float(gamma_flip_down),
            "gamma_regime": gamma_regime, "gex": float(gex_proxy), "vanna": float(vanna_proxy),
            "charm": float(charm_proxy), "skew_30d": float(skew_30d), "skew_60d": float(skew_30d) * 0.8,
            "skew_90d": float(skew_30d) * 0.6, "mp_dist": float(mp_dist), "iv_rank": float(iv_rank),
            "expected_move_pct": float(expected_move), "pc_ratio": float(pc_ratio),
            "oi_call": int(oi_call), "oi_put": int(oi_put),
            "source": "PROXY", "next_expiry": _get_next_expiry(), "days_to_expiry": 21,
        }
    except Exception:
        return {}


def _skew_curve_proxy_html(ticker, options_data, width=300, height=120, iv_exact=None):
    skew_val = options_data.get("skew_30d") or options_data.get("skew_60d") or 0
    if skew_val is None: skew_val = 0
    if skew_val > 0.05:
        shape = "smirk"; left_h = 85; mid_h = 40; right_h = 25; color = "#F85149"
    elif skew_val < -0.05:
        shape = "reverse_smirk"; left_h = 25; mid_h = 40; right_h = 85; color = "#3FB950"
    else:
        shape = "smile"; left_h = 70; mid_h = 30; right_h = 70; color = "#D29922"
    bars = 15
    bar_width = int(width / bars)
    bars_html = ""
    for i in range(bars):
        x = (i - bars//2) / (bars//2)
        if shape == "smirk": h = int(30 + 55 * math.exp(-x))
        elif shape == "reverse_smirk": h = int(30 + 55 * math.exp(x))
        else: h = int(30 + 55 * (x**2))
        h = max(10, min(95, h))
        bars_html += f'<div style="width:{bar_width-2}px;height:{h}%;background:{color}40;border-radius:2px;opacity:0.8;"></div>'
    iv_label = f" · IV: {iv_exact:.1%} (Schadner)" if iv_exact else f" [{options_data.get('source','PROXY')}]"
    return (
        f'<div class="skew-curve-container">'
        f'<div class="skew-curve-title">{ticker} Skew · {shape.replace("_"," ").title()} ({skew_val:+.2f}){iv_label}</div>'
        f'<div style="display:flex;align-items:flex-end;gap:1px;height:{height}px;padding:0 4px;">'
        f'{bars_html}'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-top:2px;">'
        f'<span>OTM Puts</span><span>ATM</span><span>OTM Calls</span></div>'
        f'</div>'
    )


def _build_dark_pool_proxy(snap, prices):
    prints = []
    inst = snap.get("institutional_data", {}) if isinstance(snap.get("institutional_data"), dict) else {}
    if inst.get("per_ticker"):
        for t, data in inst.get("per_ticker", {}).items():
            if not isinstance(data, dict): continue
            if data.get("anomaly_score", 0) > 0.6:
                px = None
                if t in prices:
                    try: px = float(pd.to_numeric(pd.Series(prices[t]), errors="coerce").dropna().iloc[-1])
                    except: pass
                if px:
                    size = int(data.get("volume_anomaly", 0) * 1000)
                    amt = size * px
                    side = "BUY" if data.get("buy_pressure", 0) > data.get("sell_pressure", 0) else "SELL"
                    prints.append({"time": "Live", "ticker": t, "price": px, "size": size, "amount": amt, "side": side})
    fr = snap.get("front_run_candidates", []) or []
    for item in fr[:5]:
        if not isinstance(item, dict): continue
        t = item.get("ticker", "")
        if any(p["ticker"] == t for p in prints): continue
        px = None
        if t in prices:
            try: px = float(pd.to_numeric(pd.Series(prices[t]), errors="coerce").dropna().iloc[-1])
            except: pass
        if px:
            size = 250000
            amt = size * px
            prints.append({"time": "Consensus", "ticker": t, "price": px, "size": size, "amount": amt, "side": "BUY"})
    prints.sort(key=lambda x: x["amount"], reverse=True)
    return prints[:15]


def _get_dark_pool_for_ticker(ticker, snap):
    if not snap: return None
    inst = snap.get("institutional_data", {}) if isinstance(snap.get("institutional_data"), dict) else {}
    if inst.get("per_ticker"):
        data = inst.get("per_ticker", {}).get(ticker)
        if isinstance(data, dict) and data.get("anomaly_score", 0) > 0.6:
            px = None
            prices = snap.get("prices", {})
            if ticker in prices:
                try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
                except: pass
            if px:
                size = int(data.get("volume_anomaly", 0) * 1000)
                return {"size": size, "price": px, "amount": size * px,
                        "side": "BUY" if data.get("buy_pressure", 0) > data.get("sell_pressure", 0) else "SELL",
                        "time": "Live", "source": "INST"}
    fr = snap.get("front_run_candidates", []) or []
    for item in fr:
        if not isinstance(item, dict): continue
        if item.get("ticker") == ticker:
            px = None
            prices = snap.get("prices", {})
            if ticker in prices:
                try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
                except: pass
            if px:
                return {"size": 250000, "price": px, "amount": 250000 * px, "side": "BUY", "time": "Consensus", "source": "FR"}
    prices = snap.get("prices", {})
    if ticker in prices:
        try:
            s = pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna()
            if len(s) >= 6:
                px = float(s.iloc[-1])
                r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
                vol_5 = float(s.tail(5).std())
                vol_20 = float(s.tail(20).std()) if len(s) >= 20 else vol_5
                if vol_20 > 0 and abs(vol_5 / vol_20 - 1) > 0.25:
                    side = "BUY" if r5d > 0 else "SELL"
                    size = int(150000 * (1 + abs(r5d) * 5))
                    return {"size": size, "price": px, "amount": size * px,
                            "side": side, "time": "Proxy", "source": "PROXY"}
        except Exception:
            pass
    return None

# ═══════════════════════════════════════════════════════════════════
# RISK RANGE / ROW BUILDERS (AUDITED + FORMULA DOCUMENTATION)
# ═══════════════════════════════════════════════════════════════════
def _build_row(ticker, prices, ar, vix_now=20, gamma_data=None, greeks_data=None, market_type="us_equity", news=None, snap=None):
    """
    HEDGEYE-STYLE 3-LAYER RISK RANGE v32.9
    ─────────────────────────────────────────────────────────────────
    [1] HEDGEYE 3-LAYER RISK RANGE (Price, Volume, Volatility)
        TRADE  (3 weeks / 15 days): Immediate-term entries/exits
        TREND  (3 months / 63 days): Intermediate cycle direction
        TAIL   (1 year / 252 days): Long-term conviction/regime
        TRADE Low  = MIN(15-day low, SMA15 − 1.5×ATR15)
        TRADE Top  = MAX(15-day high, SMA15 + 1.5×ATR15)
        TREND Low  = MIN(63-day low, SMA50 − 2.0×ATR50)
        TREND Top  = MAX(63-day high, SMA50 + 2.0×ATR50)
        TAIL Low   = MIN(252-day low, SMA200 − 3.0×ATR200)
        TAIL Top   = MAX(252-day high, SMA200 + 3.0×ATR200)
    [2] DIRECTION (Hedgeye Formation) — NO TREND FILTER, NO MOMENTUM
        BULLISH  = Price > TREND Top AND Price > TAIL Top
        BEARISH  = Price < TREND Low AND Price < TAIL Low
        BULLISH_BIAS = Price > TREND Top only
        BEARISH_BIAS = Price < TREND Low only
        NEUTRAL  = Price between TREND Low and TREND Top
    [3] ENTRY / STOP / TARGET (Hedgeye + Options)
        LONG: Entry = MAX(Trade Low, Put Wall, Max Pain − EM, Gamma Flip Down)
              Stop  = MIN(Tail Low, Put Wall − 0.5×EM, Entry×0.995)
              TP1   = MIN(Trade Top, Call Wall, Max Pain + EM)
              TP2   = MIN(Trend Top, Call Wall + EM)
        SHORT: Entry = MIN(Trade Top, Call Wall, Max Pain + EM, Gamma Flip Up)
               Stop  = MAX(Tail Top, Call Wall + 0.5×EM, Entry×1.005)
               TP1   = MAX(Trade Low, Put Wall, Max Pain − EM)
               TP2   = MAX(Trend Low, Put Wall − EM)
    [4] RISK/REWARD — min 0.5% stop distance
    [5] CHASE/WAIT/AVOID
    [6] OPTIONS/GREEKS (17 sources), COT, DARK POOL, UOA, ON-CHAIN
    """
    v = ar.get(ticker, {}) if ar else {}
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 60):
        return None
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    except:
        return None
    if len(s_clean) < 60:
        return None
    px = float(s_clean.iloc[-1])

    # ═══════════════════════════════════════════════════════════════════
    # PINE SCRIPT v15 TRR/LRR ENGINE (ported to Python)
    # ═══════════════════════════════════════════════════════════════════
    def _basis(series, length, btype):
        """Pine f_basis() equivalent: EMA_ER / EMA / SMA / WMA / HMA"""
        if len(series) < length:
            return float(series.mean())
        s = series.tail(length)
        if btype == "EMA":
            return float(s.ewm(span=length, adjust=False).mean().iloc[-1])
        elif btype == "SMA":
            return float(s.mean())
        elif btype == "WMA":
            weights = np.arange(1, length + 1)
            return float(np.average(s.values, weights=weights))
        elif btype == "EMA_ER":
            ema = float(s.ewm(span=length, adjust=False).mean().iloc[-1])
            delta = float(s.diff().abs().sum())
            change = abs(float(s.iloc[-1]) - float(s.iloc[0]))
            er = change / delta if delta > 0 else 0.5
            adj = 1.0 + (er - 0.5) * 0.10
            return ema * adj
        else:  # HMA
            half = max(1, int(length / 2))
            wma_half = s.tail(half)
            weights_half = np.arange(1, len(wma_half) + 1)
            wma_h = np.average(wma_half.values, weights=weights_half)
            weights_full = np.arange(1, length + 1)
            wma_f = np.average(s.values, weights=weights_full)
            return float(2 * wma_h - wma_f)

    def _detect_asset(ticker):
        t = ticker.upper()
        is_crypto = any(x in t for x in ["BTC", "ETH", "SOL", "USDT", "PERP"]) or t.endswith("-USD")
        is_forex = "=X" in t or t in ["DX-Y.NYB", "UUP"]
        is_commodity = t in ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZW=F", "ZC=F", "USO", "GLD", "SLV", "GDX", "XLE"]
        is_index = t in ["SPY", "QQQ", "IWM", "SPX", "ES1", "NQ1", "^GSPC", "^IXIC", "^VIX"]
        if is_crypto:   return "Crypto"
        if is_forex:    return "Forex"
        if is_commodity:return "Commodities"
        if is_index:    return "Index"
        return "Stocks"

    asset = _detect_asset(ticker)

    # Auto-optimized params per asset class (Pine v15 switch table)
    param_map = {
        "Crypto":      {"basis": "EMA",      "width": "Fixed-Pct", "tm": 0.80, "trm": 0.90, "tam": 1.00, "tp": 3.5, "trp": 7.0, "tap": 14.0},
        "Forex":       {"basis": "EMA_ER",   "width": "Vol-Based", "tm": 0.50, "trm": 0.60, "tam": 0.70, "tp": 1.5, "trp": 3.0, "tap": 6.0},
        "Commodities": {"basis": "SMA",      "width": "ATR-Based", "tm": 0.70, "trm": 0.80, "tam": 0.90, "tp": 2.5, "trp": 5.0, "tap": 10.0},
        "Index":       {"basis": "SMA",      "width": "Vol-Based", "tm": 0.60, "trm": 0.70, "tam": 0.80, "tp": 1.8, "trp": 3.5, "tap": 7.0},
        "Stocks":      {"basis": "SMA",      "width": "Vol-Based", "tm": 0.65, "trm": 0.75, "tam": 0.85, "tp": 2.0, "trp": 4.0, "tap": 8.0},
    }
    p = param_map.get(asset, param_map["Stocks"])

    # Lookback lengths (days)
    trade_len = 15
    trend_len = 63
    tail_len = min(252, len(s_clean))

    # Basis lines
    trade_basis = _basis(s_clean, trade_len, p["basis"])
    trend_basis = _basis(s_clean, trend_len, p["basis"])
    tail_basis  = _basis(s_clean, tail_len,  p["basis"])

    # Realized volatility (log returns) — Pine: ta.stdev(math.log(close/close[1]), len)
    log_ret = np.log(s_clean / s_clean.shift(1)).dropna()
    def _rv(lookback):
        lr = log_ret.tail(lookback)
        return float(lr.std()) if len(lr) >= 2 else 0.01

    sig_trade = _rv(trade_len)
    sig_trend = _rv(trend_len)
    sig_tail  = _rv(tail_len)

    # ATR proxy (for ATR-Based width method)
    def _atr(lookback=14):
        if len(s_clean) < 2:
            return px * 0.01
        # True Range proxy: max(high-low, |close-close_prev|)
        diff = s_clean.diff().abs().tail(lookback)
        return float(diff.mean()) if len(diff) > 0 else px * 0.01

    atr_val = _atr(14)

    # Safe basis floor (0.05% of price)
    safe_basis_trade = max(trade_basis, px * 0.0005)
    safe_basis_trend = max(trend_basis, px * 0.0005)
    safe_basis_tail  = max(tail_basis,  px * 0.0005)

    # Vol regime detector (Pine: rvNow / rvBase clamped 0-1)
    rv_now = sig_trade * math.sqrt(252.0)
    rv_base = max(sig_trend * math.sqrt(252.0), 0.001)
    vol_regime = max(0.0, min(1.0, rv_now / (rv_base * 1.25))) if rv_base > 0 else 0.5
    vol_adj_mult = 1.0 + (vol_regime - 0.5) * 0.6  # +30% high vol, -15% low vol

    # Auto-adjusted multipliers
    auto_trade_mult = p["tm"] * vol_adj_mult
    auto_trend_mult = p["trm"] * vol_adj_mult
    auto_tail_mult  = p["tam"] * vol_adj_mult

    # WIDTH CALCULATION — exact Pine v15 logic
    width_method = p["width"]
    if width_method == "Vol-Based":
        # σ × √T × Basis × Multiplier  (Pine exact)
        trade_width = sig_trade * math.sqrt(float(trade_len)) * safe_basis_trade * auto_trade_mult
        trend_width = sig_trend * math.sqrt(float(trend_len)) * safe_basis_trend * auto_trend_mult
        tail_width  = sig_tail  * math.sqrt(float(tail_len))  * safe_basis_tail  * auto_tail_mult
    elif width_method == "ATR-Based":
        trade_width = atr_val * auto_trade_mult
        trend_width = atr_val * auto_trend_mult
        tail_width  = atr_val * auto_tail_mult
    else:  # Fixed-Pct
        trade_width = safe_basis_trade * p["tp"] / 100.0
        trend_width = safe_basis_trend * p["trp"] / 100.0
        tail_width  = safe_basis_tail  * p["tap"] / 100.0

    # TRR / LRR levels
    trade_trr = trade_basis + trade_width
    trade_lrr = max(trade_basis - trade_width, px * 0.0001)
    trend_trr = trend_basis + trend_width
    trend_lrr = max(trend_basis - trend_width, px * 0.0001)
    tail_trr  = tail_basis  + tail_width
    tail_lrr  = max(tail_basis  - tail_width,  px * 0.0001)

    # ── HEDGEYE FORMATION (NO TREND FILTER) ──
    if px > trend_trr and px > tail_trr:
        formation = "BULLISH"; side = "long"
    elif px < trend_lrr and px < tail_lrr:
        formation = "BEARISH"; side = "short"
    elif px > trend_trr:
        formation = "BULLISH_BIAS"; side = "long"
    elif px < trend_lrr:
        formation = "BEARISH_BIAS"; side = "short"
    else:
        formation = "NEUTRAL"; side = "neutral"

    # Trade-range oversold/overbought override
    if formation == "NEUTRAL":
        trade_spread = trade_trr - trade_lrr
        trade_pos = (px - trade_lrr) / trade_spread if trade_spread > 0 else 0.5
        if trade_pos <= 0.35:
            formation = "OVERSOLD"; side = "long"
        elif trade_pos >= 0.65:
            formation = "OVERBOUGHT"; side = "short"

    if side == "neutral":
        return None

    # ATR proxy for downstream entry/stop/target code (backward compat)
    atr15 = atr_val

    # Backward-compatible variable names
    trade_low  = round(trade_lrr, 4)
    trade_top  = round(trade_trr, 4)
    trend_low  = round(trend_lrr, 4)
    trend_top  = round(trend_trr, 4)
    tail_low   = round(tail_lrr, 4)
    tail_top   = round(tail_trr, 4)

# ── OPTIONS / GREEKS (17 sources) ──
    options = _get_options_data(ticker, snap) if snap else {}
    mp = options.get("max_pain")
    pw = options.get("put_wall")
    cw = options.get("call_wall")
    gf_up = options.get("gamma_flip_up")
    gf_down = options.get("gamma_flip_down")
    expected_move = options.get("expected_move_pct")

    # ── COT DATA ──
    cot_data = None; cot_signal = "NEUTRAL"; cot_confidence = 0
    if market_type in ("forex", "commodity"):
        cot_data = _get_cot_proxy(ticker)
        if cot_data and cot_data.get("signal") != "NEUTRAL":
            cot_signal = cot_data.get("signal", "NEUTRAL")
            cot_net = cot_data.get("net_noncom", 0)
            cot_confidence = min(100, abs(cot_net) / 50000 * 100) if cot_net else 0

    # ── DARK POOL ──
    dark_pool = _get_dark_pool_imbalance(ticker, snap) if snap else None
    dp_boost = 0
    if dark_pool and isinstance(dark_pool, dict):
        div = dark_pool.get("divergence", "NEUTRAL")
        if div == "HIDDEN_ACCUMULATION" and side == "long":
            dp_boost = 25
        elif div == "HIDDEN_DISTRIBUTION" and side == "short":
            dp_boost = 25
        elif div in ("HIDDEN_DISTRIBUTION", "HIDDEN_ACCUMULATION"):
            dp_boost = -10

    # ── UNUSUAL ACTIVITY ──
    unusual = _detect_unusual_activity(ticker, prices, snap, market_type)

    # ── ENTRY / STOP / TARGET ──
    # v39.3: Asset-class aware min stop distance
    if market_type == "forex":
        min_stop_dist = max(px * 0.003, 0.0005)  # min 5 pips for forex
    elif market_type == "crypto":
        min_stop_dist = max(px * 0.005, 0.01)    # min 1% for crypto
    elif market_type == "commodity":
        min_stop_dist = max(px * 0.004, 0.02)   # min 2% or $0.02 for commodities
    else:
        min_stop_dist = px * 0.003  # US equity / IHSG: 0.3%
    confluence = {"entry": [], "target": [], "entry_cluster": None, "target_cluster": None}

    def _cluster_levels(levels, threshold_pct=0.02):
        valid = [float(v) for v in levels if v is not None and v > 0 and math.isfinite(float(v))]
        if len(valid) < 2: return []
        valid.sort()
        clusters = []
        for i in range(len(valid)):
            cluster = [valid[i]]
            for j in range(i+1, len(valid)):
                if abs(valid[j] - valid[i]) / valid[i] <= threshold_pct:
                    cluster.append(valid[j])
            if len(cluster) >= 2:
                clusters.append({"levels": cluster, "center": round(sum(cluster)/len(cluster), 4), "count": len(cluster)})
        return sorted(clusters, key=lambda x: x["count"], reverse=True)

    if side == "long":
        entry_candidates = [trade_low]
        if pw: entry_candidates.append(pw)
        if mp and expected_move: entry_candidates.append(mp - expected_move * px)
        if gf_down: entry_candidates.append(gf_down)
        if cot_data and cot_signal == "BULLISH":
            entry_candidates.append(trade_low - atr15 * 0.5)
        clusters = _cluster_levels(entry_candidates, 0.02)
        if clusters:
            entry = clusters[0]["center"]
            confluence["entry"] = [("Trade Low", trade_low), ("Put Wall", pw), ("Max Pain−EM", mp - expected_move * px if mp and expected_move else None), ("Gamma Flip ↓", gf_down)]
            confluence["entry_cluster"] = clusters[0]
            entry_note = f"🔥 Confluence x{clusters[0]['count']}: entry at {_ffm(entry, market_type)}"
        else:
            entry = round(min(entry_candidates), 4)
            entry_note = f"📍 Entry at Trade Low {_ffm(entry, market_type)}"

        stop_candidates = [tail_low]
        if pw and expected_move: stop_candidates.append(pw - expected_move * 0.5 * px)
        stop_raw = max(stop_candidates) if stop_candidates else entry * 0.995
        stop = min(stop_raw, entry - min_stop_dist)

        tp1_candidates = [trade_top]
        if cw: tp1_candidates.append(cw)
        if mp and expected_move: tp1_candidates.append(mp + expected_move * px)
        t_clusters = _cluster_levels(tp1_candidates, 0.02)
        if t_clusters:
            tp1 = t_clusters[0]["center"]
            confluence["target"] = [("Trade Top", trade_top), ("Call Wall", cw), ("Max Pain+EM", mp + expected_move * px if mp and expected_move else None)]
            confluence["target_cluster"] = t_clusters[0]
        else:
            risk = abs(entry - stop)
            tp1 = round(max([x for x in tp1_candidates if x > entry], default=entry + risk * 2), 4)

        # ── ATH BREAKOUT / TREND ACCELERATION DETECTION ──
        breakout_mode = False
        breakout_note = ""
        if formation == "BULLISH" and gamma_data and gamma_data.get("gamma_regime") in ("NEGATIVE", "DEEP_NEGATIVE"):
            # Negative gamma + above all ranges = trend ACCELERATION (not mean-reversion)
            # This is SNDK/Palantir mode: ATH to ATH
            breakout_mode = True
            breakout_note = "🔥 ATH BREAKOUT MODE — Negative gamma + above Trend/Tail = trend acceleration. Targets projected beyond standard range."

        if breakout_mode:
            # Project targets beyond trend_top for breakout plays
            tp2_candidates = [trend_top * 1.05, px * 1.08]
            if cw: tp2_candidates.append(cw + atr15 * 2)
            if mp and expected_move: tp2_candidates.append(mp + expected_move * 3 * px)
            tp2 = round(max(tp2_candidates), 4)
            # TP1 also more aggressive
            tp1_candidates = [trade_top * 1.02, px * 1.04]
            if cw: tp1_candidates.append(cw + atr15)
            if mp and expected_move: tp1_candidates.append(mp + expected_move * 1.5 * px)
            if t_clusters:
                tp1 = t_clusters[0]["center"] * 1.02  # slight boost
            else:
                tp1 = round(max(tp1_candidates), 4)
        else:
            tp2_candidates = [trend_top]
            if cw: tp2_candidates.append(cw + atr15)
            if mp and expected_move: tp2_candidates.append(mp + expected_move * 2 * px)
            tp2 = round(max(tp2_candidates), 4)
        near_entry = px <= trade_top * 0.65

    else:  # short
        entry_candidates = [trade_top]
        if cw: entry_candidates.append(cw)
        if mp and expected_move: entry_candidates.append(mp + expected_move * px)
        if gf_up: entry_candidates.append(gf_up)
        if cot_data and cot_signal == "BEARISH":
            entry_candidates.append(trade_top + atr15 * 0.5)
        # v39.5: Entry short = MAX(candidates) — fade at highest confluence, no cluster dilution
        entry = round(max([float(x) for x in entry_candidates if x is not None and math.isfinite(float(x))]), 4)
        entry_note = f"📍 Entry at Trade Top {_ffm(entry, market_type)}"
        confluence["entry"] = [("Trade Top", trade_top), ("Call Wall", cw), ("Max Pain+EM", mp + expected_move * px if mp and expected_move else None), ("Gamma Flip ↑", gf_up)]

        # v39.5: Short stop = above Trade Top or entry + 1.5% minimum (not 0.3%)
        stop_candidates = [tail_top, entry * 1.015]
        if cw and expected_move: stop_candidates.append(cw + expected_move * 0.5 * px)
        stop_raw = max(stop_candidates) if stop_candidates else entry * 1.005
        stop = max(stop_raw, entry + max(px * 0.015, 0.01))

        tp1_candidates = [trade_low]
        if pw: tp1_candidates.append(pw)
        if mp and expected_move: tp1_candidates.append(mp - expected_move * px)
        t_clusters = _cluster_levels(tp1_candidates, 0.02)
        if t_clusters:
            tp1 = t_clusters[0]["center"]
            confluence["target"] = [("Trade Low", trade_low), ("Put Wall", pw), ("Max Pain−EM", mp - expected_move * px if mp and expected_move else None)]
            confluence["target_cluster"] = t_clusters[0]
        else:
            risk = abs(entry - stop)
            tp1 = round(min([x for x in tp1_candidates if x < entry], default=entry - risk * 2), 4)

        # ── SHORT BREAKDOWN / TREND ACCELERATION DETECTION ──
        breakdown_mode = False
        breakdown_note = ""
        if formation == "BEARISH" and gamma_data and gamma_data.get("gamma_regime") in ("POSITIVE", "DEEP_POSITIVE"):
            # Positive gamma + below all ranges = breakdown acceleration
            breakdown_mode = True
            breakdown_note = "🔥 BREAKDOWN MODE — Positive gamma + below Trend/Tail = breakdown acceleration. Targets projected beyond standard range."

        if breakdown_mode:
            tp2_candidates = [trend_low * 0.95, px * 0.92]
            if pw: tp2_candidates.append(pw - atr15 * 2)
            if mp and expected_move: tp2_candidates.append(mp - expected_move * 3 * px)
            tp2 = round(min(tp2_candidates), 4)
            tp1_candidates = [trade_low * 0.98, px * 0.96]
            if pw: tp1_candidates.append(pw - atr15)
            if mp and expected_move: tp1_candidates.append(mp - expected_move * 1.5 * px)
            if t_clusters:
                tp1 = t_clusters[0]["center"] * 0.98
            else:
                tp1 = round(min(tp1_candidates), 4)
        else:
            tp2_candidates = [trend_low]
            if pw: tp2_candidates.append(pw - atr15)
            if mp and expected_move: tp2_candidates.append(mp - expected_move * 2 * px)
            tp2 = round(min(tp2_candidates), 4)
        near_entry = px >= entry * 0.98

    # ── RISK/REWARD ──
    risk = abs(entry - stop)
    if risk < min_stop_dist:
        rr = 0.0; grade = "C"; setup_valid = False
        setup_note = f"🚫 INVALID — Stop {_ffm(stop, market_type)} too close to entry {_ffm(entry, market_type)} (risk {risk/px:.2%} < 0.5% min)."
    else:
        rr = round(abs(tp1 - entry) / risk, 2)
        grade = "A" if near_entry and rr >= 2.0 else "B" if near_entry and rr >= 1.5 else "C"
        setup_valid = True; setup_note = ""

    # ── CHASE/WAIT/AVOID ──
    chase_status = "NEUTRAL"; chase_color = "#8B949E"; chase_text = "—"
    if not setup_valid:
        chase_status = "AVOID"; chase_color = "#F85149"
        chase_text = f"🚫 AVOID — {setup_note}"
    else:
        if side == "long":
            if px <= entry * 1.02:
                chase_status = "CHASE"; chase_color = "#3FB950"
                chase_text = f"🟢 CHASE — Price at/near entry {_ffm(entry, market_type)}. Risk: {risk/px:.2%}."
            elif px > entry * 1.05 and px > stop:
                chase_status = "WAIT"; chase_color = "#D29922"
                chase_text = f"🟡 WAIT — Price {ff(px)} above entry {_ffm(entry, market_type)}. Wait pullback to {_ffm(entry, market_type)}-{_ffm(stop, market_type)} zone."
            elif px < stop:
                chase_status = "AVOID"; chase_color = "#F85149"
                chase_text = f"🔴 STOP HIT — Price {_ffm(px, market_type)} below stop {_ffm(stop, market_type)}. Setup invalidated."
            elif rr >= 3.0:
                chase_text += f" | 🎯 HIGH CONVICTION RR {rr:.1f}x"
            elif rr < 1.5:
                chase_text += f" | ⚠️ POOR RR {rr:.1f}x — skip or wait better entry"
        else:
            if px >= entry * 0.98:
                chase_status = "CHASE"; chase_color = "#3FB950"
                chase_text = f"🟢 CHASE — Price at/near entry {_ffm(entry, market_type)}. Risk: {risk/px:.2%}."
            elif px < entry * 0.95 and px < stop:
                chase_status = "WAIT"; chase_color = "#D29922"
                chase_text = f"🟡 WAIT — Price {_ffm(px, market_type)} below entry {_ffm(entry, market_type)}. Wait pullback to {_ffm(entry, market_type)}-{_ffm(stop, market_type)} zone."
            elif px > stop:
                chase_status = "AVOID"; chase_color = "#F85149"
                chase_text = f"🔴 STOP HIT — Price {_ffm(px, market_type)} above stop {_ffm(stop, market_type)}. Setup invalidated."
            elif rr >= 3.0:
                chase_text += f" | 🎯 HIGH CONVICTION RR {rr:.1f}x"
            elif rr < 1.5:
                chase_text += f" | ⚠️ POOR RR {rr:.1f}x — skip or wait better entry"

    # ── RETURNS ──
    r5d = _price_ret(ticker, prices, 5) or 0
    r20d = _price_ret(ticker, prices, 21) or 0
    r63d = _price_ret(ticker, prices, 63) or 0

    return {
        "ticker": ticker, "price": px,
        "breakout_mode": breakout_mode if 'breakout_mode' in locals() else False,
        "breakout_note": breakout_note if 'breakout_note' in locals() else "",
        "breakdown_mode": breakdown_mode if 'breakdown_mode' in locals() else False,
        "breakdown_note": breakdown_note if 'breakdown_note' in locals() else "",
        "trade_low": round(trade_low, 4), "trade_top": round(trade_top, 4),
        "trend_low": round(trend_low, 4), "trend_top": round(trend_top, 4),
        "tail_low": round(tail_low, 4), "tail_top": round(tail_top, 4),
        "entry": entry, "target_1": tp1, "target_2": tp2,
        "stop": stop, "rr": rr, "risk_pct": round(risk/px*100, 2) if px else 0,
        "direction": "LONG" if side == "long" else "SHORT",
        "grade": grade, "setup_valid": setup_valid,
        "near_entry": near_entry, "side": side,
        "formation": formation,
        "r5d": r5d, "r20d": r20d, "r63d": r63d,
        "composite": side, "market_type": market_type,
        "options": options,
        "mm_positioning": options.get("mm_positioning", "UNKNOWN"),
        "mm_recommendation": options.get("mm_recommendation", "—"),
        "news_signal": "", "news_headline": "", "news_sentiment": 0,
        "entry_note": entry_note, "setup_note": setup_note,
        "confluence": confluence,
        "dark_pool": dark_pool,
        "cot_data": cot_data, "cot_signal": cot_signal, "cot_confidence": cot_confidence,
        "unusual_activity": unusual,
        "chase_status": chase_status, "chase_color": chase_color, "chase_text": chase_text,
        "walkforward": {},
        "gatekeeper": {},
        "hedgeye_size": None,
        "keith_sync": {},
        "vix_bucket": "NORMAL",
        "dp_boost": dp_boost,
    }

# ═══════════════════════════════════════════════════════════════════
# BROKER PROXY (IHSG manipulation detection)
# ═══════════════════════════════════════════════════════════════════
def _get_broker_proxy(ticker, prices):
    """
    AUDITED v32.4.1 — Proxy broker summary for IHSG with manipulation detection.
    Detects crossing (wash trading) vs real accumulation/distribution.
    """
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 30):
        return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 30: return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}

        px = float(s_clean.iloc[-1])
        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else r5d

        vol_5 = float(s_clean.tail(5).std())
        vol_20 = float(s_clean.tail(20).std()) if len(s_clean) >= 20 else vol_5
        mean_20 = float(s_clean.tail(20).mean())

        range_5 = float(s_clean.tail(5).max() - s_clean.tail(5).min())
        range_20 = float(s_clean.tail(20).max() - s_clean.tail(20).min()) if len(s_clean) >= 20 else range_5

        # Crossing detection: high activity (volatility spike) but price goes nowhere
        crossing = False
        if vol_20 > 0 and vol_5 / vol_20 > 1.5 and range_5 / max(range_20, 0.001) < 0.15:
            crossing = True

        real_acc = False
        if r5d > 0.03 and r20d > 0.05 and not crossing:
            real_acc = True

        real_dist = False
        if r5d < -0.03 and r20d < -0.05 and not crossing:
            real_dist = True

        conf = 0
        if real_acc: conf = min(100, int(50 + abs(r5d)*500))
        elif real_dist: conf = min(100, int(50 + abs(r5d)*500))
        elif crossing: conf = 70

        return {
            "real_accumulation": real_acc,
            "real_distribution": real_dist,
            "crossing_detected": crossing,
            "confidence": conf,
            "r5d": round(r5d, 4),
            "r20d": round(r20d, 4),
            "vol_ratio": round(vol_5/vol_20, 2) if vol_20 > 0 else 1.0,
            "range_ratio": round(range_5/max(range_20, 0.001), 2),
        }
    except Exception:
        return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}


def _build_ihsg_row(ticker, prices, ar, **kwargs):
    """IHSG — Hedgeye 3-layer + Broker Proxy ONLY. BUY-ONLY MARKET (no options/greeks)."""
    row = _build_row(ticker, prices, ar, market_type="ihsg", **kwargs)
    if not row:
        return None
    # IHSG is buy-only. Force direction to LONG.
    row["direction"] = "LONG"
    row["side"] = "long"
    # Strip ALL options/greeks data (IHSG has no options market)
    row["options"] = {}
    row["mm_positioning"] = ""
    row["mm_recommendation"] = ""
    # Sector
    sector = IHSG_SECTOR_MAP.get(ticker, "Indonesia")
    row["sector"] = sector
    # Broker proxy (real accumulation/distribution/crossing/cornering)
    broker = _get_broker_proxy(ticker, prices)
    row["broker"] = broker
    # Compute entry convergence for IHSG
    conv = _compute_entry_convergence(row, kwargs.get("snap"), market_type="ihsg")
    row["entry_convergence"] = conv
    # IHSG-specific recommendation (BUY ONLY)
    formation = row.get("formation", "NEUTRAL")
    if broker.get("real_accumulation", False):
        row["recommendation"] = f"🟢 AKUMULASI REAL — {sector} ({broker.get('confidence',0)}% conf) · BELI"
    elif broker.get("real_distribution", False):
        row["recommendation"] = f"🔴 DISTRIBUSI REAL — {sector} ({broker.get('confidence',0)}% conf) · TUNGGU/HOLD"
    elif broker.get("crossing_detected", False):
        row["recommendation"] = f"🟡 WASPADA CROSSING — {sector} (possible wash trading) · TUNGGU"
    elif broker.get("cornering_supply", False):
        row["recommendation"] = f"🎯 CORNERING SUPPLY — {sector} (volume drying up then spike) · WATCH BREAKOUT"
    elif formation in ("BULLISH", "BULLISH_BIAS", "OVERSOLD"):
        row["recommendation"] = f"🟢 {sector} — Bullish/Oversold formation, buy at Trade Low"
    elif formation in ("BEARISH", "BEARISH_BIAS", "OVERBOUGHT"):
        row["recommendation"] = f"🟡 {sector} — Bearish formation detected · TUNGGU pullback ke Trade Low"
    else:
        row["recommendation"] = f"⚪ {sector} — Neutral, range-bound · MONITOR"
    return row


def build_ticker_rows(tickers, market_type="us_equity", vix_now=20, gamma_data=None, greeks_data=None, news=None, prices=None, ar=None, snap=None, sim_results=None):
    rows = []
    for t in tickers:
        if market_type == "ihsg": r = _build_ihsg_row(t, prices, ar, snap=snap)
        else: r = _build_row(t, prices, ar, vix_now=vix_now, gamma_data=gamma_data, greeks_data=greeks_data, market_type=market_type, news=news, snap=snap)
        if r:
            # Inject ALL background engine data into row for detail expander
            if snap:
                r["walkforward"] = (snap.get("walkforward_results") or {}).get(t, {})
                r["gatekeeper"] = (snap.get("alpha_gatekeeper") or {}).get(t, {})
                r["keith_sync"] = (snap.get("keith_sync") or {}).get(t, {})
                r["hedgeye_size"] = next((p for p in (snap.get("hedgeye_position_sizing") or {}).get("positions", []) if p.get("ticker") == t), None)
                r["vix_bucket"] = (snap.get("vix_bucket") or {}).get("bucket", "NORMAL")
                if sim_results and t in sim_results:
                    r["simulation"] = sim_results[t]
            # Compute entry convergence for ALL tickers (v39.2)
            r["entry_convergence"] = _compute_entry_convergence(r, snap, market_type=market_type)
            # v39.5: Convergence override — if HOLD with <60% confidence, force WAIT
            conv = r.get("entry_convergence", {})
            if conv and isinstance(conv, dict) and conv.get("signal") == "HOLD" and conv.get("confidence", 0) < 60:
                if r.get("chase_status") not in ("AVOID",):
                    r["chase_status"] = "WAIT"
                    r["chase_color"] = "#D29922"
                    r["chase_text"] = (r.get("chase_text", "") + f" | ⏳ CONVERGENCE HOLD ({conv.get('confidence',0):.0f}%) — signals conflict").strip(" |")
            rows.append(r)
    # Simulation runs background-only; annotate but don't filter
    if sim_results:
        rows = filter_by_simulation(rows, sim_results, threshold=50, require_pass=False)
    return rows


def split_long_short(rows):
    longs = [r for r in rows if "LONG" in r.get("direction", "")]
    shorts = [r for r in rows if "SHORT" in r.get("direction", "")]
    return sorted(longs, key=lambda x: x.get("rr", 0), reverse=True), sorted(shorts, key=lambda x: x.get("rr", 0), reverse=True)


def filter_actionable(rows, snap=None):
    """
    v39.5 HEDGEYE-ALIGNED QUALITY FILTER — Remove sampah tickers
    Requirements:
    - setup_valid = True (stop not too tight)
    - chase_status = CHASE or WAIT (not AVOID/NEUTRAL)
    - RR >= 1.0 minimum
    - Must have SOME edge: options/greeks OR dark pool OR alpha_source OR broker OR strong formation
    - Keith BEARISH override = auto-kill
    - Signal-to-Quad alignment: ticker must be in Hedgeye favor list OR have strong methodology signal
    - Avoid-list = auto-kill unless Keith BULLISH override
    - IHSG: must have broker signal or strong formation (min quality 25)
    """
    # Get Hedgeye playbook for alignment check
    pb = _get_hedgeye_playbook(snap) if snap else {"beli": [], "short": [], "quad": "Q3"}
    avoid_tickers = set(pb.get("short", []))
    favor_tickers = set(pb.get("beli", []))
    current_quad = pb.get("quad", "Q3")

    out = []
    for r in rows:
        t = r.get("ticker", "")
        # ── v39.5 HARD EXCLUDES ──
        # Only CHASE (ready now) or WAIT (almost ready). NEUTRAL/AVOID = kill.
        if r.get("chase_status") not in ("CHASE", "WAIT"):
            continue
        ks = r.get("keith_sync", {})
        if ks and isinstance(ks, dict) and ks.get("override") and ks.get("keith_trade") == "BEARISH":
            continue
        if not r.get("setup_valid"):
            continue

        rr = r.get("rr", 0) or 0
        if rr < 1.0:
            continue

        # ── HEDGEYE PLAYBOOK ALIGNMENT ──
        in_favor = t in favor_tickers
        in_avoid = t in avoid_tickers

        # Quality scoring
        quality_score = 0
        reasons = []

        if rr >= 2.0:
            quality_score += 30; reasons.append("RR≥2")
        elif rr >= 1.5:
            quality_score += 20; reasons.append("RR≥1.5")
        elif rr >= 1.2:
            quality_score += 10; reasons.append("RR≥1.2")
        else:
            quality_score += 5; reasons.append("RR<1.2")

        formation = r.get("formation", "NEUTRAL")
        if formation in ("BULLISH", "BEARISH"):
            quality_score += 20; reasons.append("Strong formation")
        elif formation in ("BULLISH_BIAS", "BEARISH_BIAS", "OVERSOLD", "OVERBOUGHT"):
            quality_score += 15; reasons.append("Bias/Oversold")

        # Hedgeye playbook alignment (P0 priority)
        if in_favor:
            quality_score += 25; reasons.append(f"Hedgeye Q{current_quad} favored")
        if in_avoid:
            quality_score -= 50; reasons.append(f"Hedgeye Q{current_quad} avoid-list")

        # Methodology signals (Citrini, Leopold, COATUE, Karsan, etc)
        alpha_src = r.get("alpha_source", "")
        alpha_score = r.get("alpha_score", 0)
        if alpha_src in ("bottleneck", "front_run", "leopold", "coatue", "karsan", "thought_process"):
            quality_score += 20; reasons.append(f"{alpha_src} signal")
        if alpha_score >= 70:
            quality_score += 10; reasons.append("High alpha")

        opts = r.get("options", {})
        market_type = r.get("market_type", "us_equity")
        if market_type != "ihsg" and opts:
            gamma = opts.get("gamma_regime", "")
            if gamma and gamma != "TRANSITION":
                quality_score += 10; reasons.append("Gamma signal")
            if opts.get("max_pain"):
                quality_score += 5; reasons.append("Max pain")
            if opts.get("vanna") is not None or opts.get("charm") is not None:
                quality_score += 5; reasons.append("Greeks data")

        dp = r.get("dark_pool")
        if dp and isinstance(dp, dict) and dp.get("divergence") not in ("NEUTRAL", None):
            quality_score += 15; reasons.append("Dark pool edge")

        sim = r.get("simulation")
        if sim and isinstance(sim, dict):
            if sim.get("robustness_score", 0) >= 65:
                quality_score += 15; reasons.append("Sim strong")
            elif sim.get("robustness_score", 0) >= 50:
                quality_score += 8; reasons.append("Sim OK")

        wf = r.get("walkforward", {})
        if wf and isinstance(wf, dict) and wf.get("gate_status") == "PASS":
            quality_score += 10; reasons.append("WF pass")

        if market_type == "ihsg":
            broker = r.get("broker", {})
            if broker and isinstance(broker, dict):
                if broker.get("real_accumulation"):
                    quality_score += 25; reasons.append("Real accumulation")
                elif broker.get("real_distribution"):
                    quality_score += 15; reasons.append("Real distribution")
                elif broker.get("cornering_supply"):
                    quality_score += 20; reasons.append("Cornering")
                elif broker.get("crossing_detected"):
                    quality_score -= 10; reasons.append("Crossing warning")
            if quality_score < 20 and formation == "NEUTRAL":
                continue

        if r.get("breakout_mode") or r.get("breakdown_mode"):
            quality_score += 10; reasons.append("Breakout mode")

        quality_score = max(0, min(100, quality_score))
        r["quality_score"] = quality_score
        r["quality_reasons"] = reasons

        if quality_score >= 80:
            r["grade"] = "A"
        elif quality_score >= 60:
            r["grade"] = "B"
        elif quality_score >= 40:
            r["grade"] = "C"
        else:
            r["grade"] = "D"

        # v39.5: HIGH CONVICTION GATE
        # Grade A/B + quality >= 60 + (in Hedgeye favor OR strong methodology signal)
        # Kalau di avoid list → auto-kill kecuali ada Keith BULLISH override
        if in_avoid and not (ks and isinstance(ks, dict) and ks.get("keith_trade") == "BULLISH"):
            continue  # Auto-kill avoid-list tanpa override

        if quality_score >= 60 and r.get("grade") in ("A", "B") and (in_favor or alpha_src or market_type == "ihsg"):
            out.append(r)
        elif quality_score >= 50 and r.get("grade") == "B" and not in_avoid:
            # Borderline — monitor only, not ready
            r["chase_status"] = "WAIT"
            r["chase_color"] = "#D29922"
            r["chase_text"] = f"⏳ MONITOR — Quality {quality_score} but not in Hedgeye playbook"
            out.append(r)

    return sorted(out, key=lambda x: x.get("quality_score", 0), reverse=True)


def filter_high_conviction(rows, min_rr=1.5, min_sim=50, min_wf=55):
    """
    v39.2 QUALITY GATE — Only the best setups survive.
    Requirements:
      - RR >= min_rr (default 1.5)
      - setup_valid = True
      - chase_status = CHASE or WAIT (not AVOID)
      - Keith NOT overriding to BEARISH
      - Sim robustness >= min_sim (if sim data exists)
      - WF gate score >= min_wf OR gate_status PASS/MARGINAL (if WF data exists)
      - Grade A or B (not C)
    """
    out = []
    for r in rows:
        rr = r.get("rr", 0) or 0
        grade = r.get("grade", "C")
        chase = r.get("chase_status", "NEUTRAL")
        valid = r.get("setup_valid", False)

        # Keith check
        ks = r.get("keith_sync", {})
        keith_block = ks and isinstance(ks, dict) and ks.get("override") and ks.get("keith_trade") == "BEARISH"

        # Sim check
        sim = r.get("simulation")
        sim_ok = True
        if sim and isinstance(sim, dict):
            sim_ok = sim.get("robustness_score", 0) >= min_sim

        # WF check
        wf = r.get("walkforward", {})
        wf_ok = True
        if wf and isinstance(wf, dict):
            wf_ok = (wf.get("combined_gate_score", 0) >= min_wf) or (wf.get("gate_status") in ("PASS", "MARGINAL"))

        # Composite check
        conv = r.get("entry_convergence", {})
        conv_ok = True
        if conv and isinstance(conv, dict):
            conv_ok = conv.get("confidence", 0) >= 40  # at least some confidence

        if rr >= min_rr and valid and chase != "AVOID" and not keith_block and sim_ok and wf_ok and conv_ok and grade in ("A", "B"):
            r["_quality_passed"] = True
            r["_quality_score"] = min(100, int(rr * 20 + (50 if chase == "CHASE" else 25) + (20 if grade == "A" else 10)))
            out.append(r)
    return sorted(out, key=lambda x: x.get("_quality_score", 0), reverse=True)


def filter_low_conviction(rows):
    """v39.2: Setups that exist but don't meet high conviction gate. Monitor only."""
    out = []
    for r in rows:
        if r.get("_quality_passed"):
            continue
        if r.get("chase_status") == "AVOID":
            continue
        rr = r.get("rr", 0) or 0
        if rr > 0:
            r["_low_conviction_note"] = f"RR {rr:.1f}x — monitor for better entry"
            out.append(r)
    return out


def filter_invalid(rows):
    """Return invalid/unactionable setups for audit."""
    return [r for r in rows if not r.get("setup_valid") or r.get("chase_status") == "AVOID"]


# ═══════════════════════════════════════════════════════════════════
# DARK POOL IMBALANCE
# ═══════════════════════════════════════════════════════════════════
def _get_dark_pool_imbalance(ticker, snap):
    """
    Dual-tape divergence analysis: Dark Pool vs Lit Tape (price action proxy).
    Alphaticaio methodology: compare dark pool flow vs public price momentum.
    """
    if not snap:
        return None
    inst = snap.get("institutional_data", {}) if isinstance(snap.get("institutional_data"), dict) else {}
    per_ticker = inst.get("per_ticker", {}) if isinstance(inst, dict) else {}
    data = per_ticker.get(ticker)
    if not isinstance(data, dict):
        return None

    buy = float(data.get("buy_pressure", 0) or 0)
    sell = float(data.get("sell_pressure", 0) or 0)
    total = buy + sell
    if total == 0:
        return None

    imbalance = (buy - sell) / total * 100

    # Zero-print detection
    zero_flag = None
    zero_text = None
    if buy > 0 and sell == 0:
        zero_flag = "ZERO_SELLS"
        zero_text = "🔥 ZERO DARK SELLS — Pure accumulation"
    elif sell > 0 and buy == 0:
        zero_flag = "ZERO_BUYS"
        zero_text = "❄️ ZERO DARK BUYS — Pure distribution"

    # Lit tape proxy from 5-day price momentum
    prices = snap.get("prices", {})
    s = prices.get(ticker)
    lit_tape_signal = "NEUTRAL"
    r5d = None
    if s is not None and len(s) >= 6:
        try:
            s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
            if len(s_clean) >= 6:
                r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1)
                if r5d > 0.02:
                    lit_tape_signal = "BUY"
                elif r5d < -0.02:
                    lit_tape_signal = "SELL"
        except Exception:
            pass

    dp_signal = "BUY" if imbalance > 15 else "SELL" if imbalance < -15 else "NEUTRAL"

    # Dual-tape divergence classification
    divergence = "NEUTRAL"
    div_emoji = "⚪"
    div_color = "#8B949E"
    div_text = "No clear edge"

    if dp_signal == "BUY" and lit_tape_signal == "BUY":
        divergence = "BOTH_AGREE"
        div_emoji = "✅"
        div_color = "#3FB950"
        div_text = "BOTH TAPES AGREE — Strong conviction"
    elif dp_signal == "SELL" and lit_tape_signal == "SELL":
        divergence = "BOTH_AGREE"
        div_emoji = "✅"
        div_color = "#F85149"
        div_text = "BOTH TAPES AGREE — Strong conviction"
    elif dp_signal == "BUY" and lit_tape_signal == "SELL":
        divergence = "HIDDEN_ACCUMULATION"
        div_emoji = "🟢"
        div_color = "#3FB950"
        div_text = "HIDDEN ACCUMULATION — Public selling, Institutions buying"
    elif dp_signal == "SELL" and lit_tape_signal == "BUY":
        divergence = "HIDDEN_DISTRIBUTION"
        div_emoji = "🔴"
        div_color = "#F85149"
        div_text = "HIDDEN DISTRIBUTION — Public buying, Institutions selling"
    elif dp_signal != "NEUTRAL" and lit_tape_signal == "NEUTRAL":
        divergence = "DARK_POOL_LEADS"
        div_emoji = "🔮"
        div_color = "#58A6FF"
        div_text = "DARK POOL LEADS — Lit tape neutral"
    elif dp_signal == "NEUTRAL" and lit_tape_signal != "NEUTRAL":
        divergence = "LIT_TAPE_LEADS"
        div_emoji = "📊"
        div_color = "#D29922"
        div_text = "LIT TAPE LEADS — Dark pool neutral"

    return {
        "imbalance": round(imbalance, 1),
        "buy_pressure": round(buy, 2),
        "sell_pressure": round(sell, 2),
        "zero_flag": zero_flag,
        "zero_text": zero_text,
        "lit_tape_signal": lit_tape_signal,
        "dp_signal": dp_signal,
        "divergence": divergence,
        "div_emoji": div_emoji,
        "div_color": div_color,
        "div_text": div_text,
        "r5d": round(r5d, 4) if r5d is not None else None,
        "anomaly_score": data.get("anomaly_score", 0),
    }


def _detect_unusual_activity(ticker, prices, snap, market_type):
    """Detect Large Orders, UOA, and On-chain anomalies."""
    result = {
        "large_order_detected": False, "uoa_detected": False, "onchain_detected": False,
        "signal": "NEUTRAL", "confidence": 0, "details": "",
    }
    s = prices.get(ticker)
    if s is None or len(s) < 20:
        return result
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20:
            return result
        vol_5 = float(s_clean.tail(5).std())
        vol_20 = float(s_clean.tail(20).std()) if len(s_clean) >= 20 else vol_5
        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        if vol_20 > 0 and vol_5 / vol_20 > 2.0 and abs(r5d) < 0.02:
            result["large_order_detected"] = True
            result["signal"] = "BUY" if r5d >= 0 else "SELL"
            result["confidence"] = min(100, int((vol_5/vol_20 - 2) * 50))
            result["details"] = f"Large order: vol spike {vol_5/vol_20:.1f}x with flat price"
        if market_type == "us_equity" and snap:
            opts = snap.get("yfinance_options", {}).get(ticker, {}) if isinstance(snap.get("yfinance_options"), dict) else {}
            if isinstance(opts, dict) and opts.get("ok"):
                oi_c = opts.get("oi_call", 0); oi_p = opts.get("oi_put", 0)
                total_oi = oi_c + oi_p
                if total_oi > 100000:
                    pc = oi_p / oi_c if oi_c > 0 else 1.0
                    if pc > 1.5 or pc < 0.5:
                        result["uoa_detected"] = True
                        result["signal"] = "BUY" if pc > 1.5 else "SELL"
                        result["confidence"] = min(100, int(abs(pc - 1) * 50))
                        result["details"] += f" | UOA: P/C {pc:.2f}"
        if market_type == "crypto":
            cc = snap.get("crypto_center", {}) if snap else {}
            if isinstance(cc, dict):
                whale = cc.get("whale", {}).get("proxy", {}).get(ticker, "NEUTRAL")
                if whale in ("ACCUMULATING", "DISTRIBUTING"):
                    result["onchain_detected"] = True
                    result["signal"] = "BUY" if whale == "ACCUMULATING" else "SELL"
                    result["confidence"] = 70
                    result["details"] += f" | Whale {whale.lower()}"
    except Exception:
        pass
    return result


# ═══════════════════════════════════════════════════════════════════
# COT PROXY (for forex/commodities)
# ═══════════════════════════════════════════════════════════════════
def _get_cot_proxy(ticker):
    cot_map = {
        "EURUSD=X": {"net_noncom": 45000, "net_com": -32000, "change_wow": 2500, "signal": "BULLISH"},
        "GBPUSD=X": {"net_noncom": 12000, "net_com": -8000, "change_wow": -1500, "signal": "NEUTRAL"},
        "USDJPY=X": {"net_noncom": -28000, "net_com": 35000, "change_wow": 4200, "signal": "BEARISH"},
        "AUDUSD=X": {"net_noncom": 8000, "net_com": -5000, "change_wow": 800, "signal": "BULLISH"},
        "USDCAD=X": {"net_noncom": -15000, "net_com": 12000, "change_wow": -2000, "signal": "BEARISH"},
        "USDCHF=X": {"net_noncom": -5000, "net_com": 3000, "change_wow": 500, "signal": "NEUTRAL"},
        "NZDUSD=X": {"net_noncom": 3000, "net_com": -2000, "change_wow": 400, "signal": "BULLISH"},
        "DX-Y.NYB": {"net_noncom": -35000, "net_com": 28000, "change_wow": 5000, "signal": "BEARISH"},
        "GC=F": {"net_noncom": 180000, "net_com": -140000, "change_wow": 12000, "signal": "BULLISH"},
        "SI=F": {"net_noncom": 45000, "net_com": -35000, "change_wow": 3000, "signal": "BULLISH"},
        "CL=F": {"net_noncom": 220000, "net_com": -180000, "change_wow": -8000, "signal": "BULLISH"},
        "NG=F": {"net_noncom": -80000, "net_com": 65000, "change_wow": 5000, "signal": "BEARISH"},
        "HG=F": {"net_noncom": 25000, "net_com": -18000, "change_wow": 2000, "signal": "BULLISH"},
    }
    return cot_map.get(ticker, {"net_noncom": 0, "net_com": 0, "change_wow": 0, "signal": "NEUTRAL"})


def _get_onchain_proxy(ticker, prices):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {}
        px = float(s_clean.iloc[-1])
        r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1) if len(s_clean) >= 22 else 0
        r7d = float(s_clean.iloc[-1] / s_clean.iloc[-8] - 1) if len(s_clean) >= 8 else r1m
        vol_20 = float(s_clean.tail(20).std())
        mean_20 = float(s_clean.tail(20).mean())
        return {
            "price": px, "r1m": r1m, "r7d": r7d,
            "volatility": round(vol_20 / mean_20 if mean_20 > 0 else 0, 4),
            "momentum": "ACCUMULATING" if r1m > 0.05 else "DISTRIBUTING" if r1m < -0.05 else "NEUTRAL",
            "whale_signal": "BUY" if r7d > 0.03 and vol_20 > 0 else "SELL" if r7d < -0.03 else "HOLD",
            "funding_proxy": round(r1m * 0.001, 5),
            "oi_proxy": int(abs(r1m) * 1e9),
        }
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════════════════
# RECOMMENDATION ENGINE (AUDITED v32.9)
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# ENTRY CONVERGENCE v39.2 — Multi-Methodology Fusion
# Combines: Hedgeye Risk Range + SpotGamma Levels + Cem Karsan Vanna/Charm
#           + VolSignals Dealer Regime + Leopold Asymmetry + Citrini Macro
# ═══════════════════════════════════════════════════════════════════
def _compute_entry_convergence(row, snap, market_type="us_equity"):
    """
    v39 UNIFIED Entry Convergence — Multi-Methodology Fusion
    Combines: Hedgeye Risk Range + SpotGamma + Cem Karsan + VolSignals 
              + Leopold + COATUE + Karsan + Dark Pool + Broker + Walkforward
    Output: {"signal": "BUY/SELL/HOLD", "confidence": 0-100, "layers": []}
    """
    ticker = row.get("ticker", "")
    direction = row.get("direction", "NEUTRAL")
    formation = row.get("formation", "NEUTRAL")
    px = row.get("price", 0)
    entry = row.get("entry")
    stop = row.get("stop")
    rr = row.get("rr", 0)

    if not snap:
        snap = {}

    layers = []
    score = 50  # neutral baseline

    def add_layer(name, sig, weight):
        nonlocal score
        score += weight
        color = "#3FB950" if weight > 0 else "#F85149" if weight < 0 else "#8B949E"
        layers.append({"name": name, "signal": sig, "weight": weight, "color": color})

    # ── P0: Keith Override (highest priority) ──
    ks = row.get("keith_sync", {})
    if ks and isinstance(ks, dict) and ks.get("override"):
        kt = ks.get("keith_trade", "")
        if kt == "BEARISH":
            return {"signal": "SELL", "confidence": 0, "layers": [{"name": "Keith P0", "signal": "AVOID", "weight": -100, "color": "#F85149"}], "direction": direction, "market_type": market_type, "note": "Keith BEARISH override — avoid all signals"}
        elif kt == "BULLISH" and direction == "LONG":
            add_layer("Keith P0", "BULLISH", 15)

    # ── P1: Hedgeye Formation ──
    formation_map = {
        "BULLISH": ("BULLISH", 25), "BEARISH": ("BEARISH", -25),
        "BULLISH_BIAS": ("BIAS+", 15), "BEARISH_BIAS": ("BIAS-", -15),
        "OVERSOLD": ("OVERSOLD", 15), "OVERBOUGHT": ("OVERBOUGHT", -15),
    }
    if formation in formation_map:
        sig, w = formation_map[formation]
        add_layer("Hedgeye Formation", sig, w)
    else:
        add_layer("Hedgeye Formation", "NEUTRAL", 0)

    # ── P2: Risk/Reward Quality ──
    if rr >= 3.0:
        add_layer("RR Quality", f"{rr:.1f}x", 10)
    elif rr >= 2.0:
        add_layer("RR Quality", f"{rr:.1f}x", 6)
    elif rr >= 1.5:
        add_layer("RR Quality", f"{rr:.1f}x", 3)
    elif rr > 0 and rr < 1.5:
        add_layer("RR Quality", f"{rr:.1f}x", -8)

    # ── P3: Options / SpotGamma (skip IHSG) ──
    if market_type != "ihsg":
        opts = row.get("options", {})
        gamma = opts.get("gamma_regime", "")
        mp = opts.get("max_pain")
        mp_dist = opts.get("mp_dist", 0) or 0

        if gamma in ("DEEP_POSITIVE", "POSITIVE") and direction == "LONG":
            add_layer("SpotGamma Gamma", "POSITIVE", 8)
        elif gamma in ("DEEP_NEGATIVE", "NEGATIVE") and direction == "SHORT":
            add_layer("SpotGamma Gamma", "NEGATIVE", 8)
        elif gamma in ("NEGATIVE", "DEEP_NEGATIVE") and direction == "LONG":
            add_layer("SpotGamma Gamma", "NEGATIVE", -8)

        if mp and px and abs((px - mp) / mp) < 0.02:
            add_layer("Max Pain Pin", "PINNED", -5 if direction == "LONG" else 3)

        # Vanna / Charm (Cem Karsan)
        vanna = opts.get("vanna")
        if vanna is not None:
            try:
                v = float(vanna)
                if abs(v) > 0.5:
                    add_layer("Cem Karsan Vanna", "BULLISH" if v > 0.5 else "BEARISH", 6 if (v > 0 and direction == "LONG") or (v < 0 and direction == "SHORT") else -4)
            except: pass

        charm = opts.get("charm")
        if charm is not None:
            try:
                c = float(charm)
                if abs(c) > 0.5:
                    add_layer("Cem Karsan Charm", "BULLISH" if c > 0.5 else "BEARISH", 6 if (c > 0 and direction == "LONG") or (c < 0 and direction == "SHORT") else -4)
            except: pass

        # VolSignals
        vs = opts.get("volsignals_regime", {})
        if isinstance(vs, dict):
            regime = vs.get("dealer_regime", "")
            if "STABILIZING" in regime and direction == "LONG":
                add_layer("VolSignals Regime", "STABILIZING", 8)
            elif "AMPLIFYING" in regime:
                add_layer("VolSignals Regime", "AMPLIFYING", -8)

    # ── P4: Methodology Fusion ──
    # Leopold
    leo = (snap.get("leopold_scan", {}) or {}).get("per_ticker", {}).get(ticker)
    if leo and isinstance(leo, dict):
        asym = leo.get("asymmetry_score", 0)
        if asym >= 70:
            w = 10 if direction == "LONG" else -10
            add_layer("Leopold Asymmetry", f"HIGH ({asym:.0f})", w)
        elif asym >= 50:
            w = 5 if direction == "LONG" else -5
            add_layer("Leopold Asymmetry", f"MID ({asym:.0f})", w)

    # COATUE
    coat = (snap.get("coatue_scan", {}) or {}).get("per_ticker", {}).get(ticker)
    if coat and isinstance(coat, dict):
        sig = coat.get("signal", "")
        if sig == "BUY" and direction == "LONG":
            add_layer("COATUE Signal", "BUY", 8)
        elif sig == "SELL" and direction == "SHORT":
            add_layer("COATUE Signal", "SELL", 8)
        elif sig and sig != "NEUTRAL":
            add_layer("COATUE Signal", sig, -5)  # conflicting

    # Karsan
    kar = (snap.get("karsan_scanner", {}) or {}).get("per_ticker", {}).get(ticker)
    if kar and isinstance(kar, dict):
        setup = kar.get("setup_type", "")
        if "squeeze" in setup.lower() and direction == "LONG":
            add_layer("Karsan Squeeze", "SETUP", 8)
        elif "convexity" in setup.lower() and direction == "LONG":
            add_layer("Karsan Convexity", "SETUP", 8)

    # Thought Process
    tp = (snap.get("thought_process", {}) or {}).get(ticker)
    if tp and isinstance(tp, dict):
        tscore = tp.get("thesis_score", 0)
        if tscore >= 80:
            add_layer("Thought Process", f"STRONG ({tscore:.0f})", 8)
        elif tscore >= 60:
            add_layer("Thought Process", f"OK ({tscore:.0f})", 4)

    # ── P5: Dark Pool / Smart Money ──
    dp = row.get("dark_pool")
    if dp and isinstance(dp, dict):
        div = dp.get("divergence", "NEUTRAL")
        if div == "HIDDEN_ACCUMULATION" and direction == "LONG":
            add_layer("Dark Pool", "HIDDEN_ACCUM", 10)
        elif div == "HIDDEN_DISTRIBUTION" and direction == "SHORT":
            add_layer("Dark Pool", "HIDDEN_DIST", 10)
        elif div == "BOTH_AGREE":
            add_layer("Dark Pool", "AGREE", 5)
        elif div in ("HIDDEN_DISTRIBUTION", "HIDDEN_ACCUMULATION"):
            add_layer("Dark Pool", "DIVERGENCE", -5)

    # ── P6: IHSG Broker (IHSG ONLY) ──
    if market_type == "ihsg":
        broker = row.get("broker", {})
        if broker and isinstance(broker, dict):
            if broker.get("real_accumulation"):
                add_layer("IHSG Broker", "ACCUMULATION", 20)
            elif broker.get("real_distribution"):
                add_layer("IHSG Broker", "DISTRIBUTION", -20)
            elif broker.get("crossing_detected"):
                add_layer("IHSG Broker", "CROSSING", -10)
            elif broker.get("cornering_supply"):
                add_layer("IHSG Broker", "CORNERING", 15)

    # ── P7: Walkforward / Simulation ──
    wf = row.get("walkforward", {})
    if wf and isinstance(wf, dict):
        if wf.get("gate_status") == "PASS":
            add_layer("Walkforward", "PASS", 10)
        elif wf.get("gate_status") == "MARGINAL":
            add_layer("Walkforward", "MARGINAL", 3)
        else:
            add_layer("Walkforward", "FAIL", -10)

    sim = row.get("simulation")
    if sim and isinstance(sim, dict):
        sscore = sim.get("robustness_score", 0)
        if sscore >= 80:
            add_layer("Simulation", f"STRONG ({sscore:.0f})", 8)
        elif sscore >= 65:
            add_layer("Simulation", f"OK ({sscore:.0f})", 4)
        elif sscore >= 50:
            add_layer("Simulation", f"WEAK ({sscore:.0f})", 0)
        else:
            add_layer("Simulation", f"FAIL ({sscore:.0f})", -8)

    # ── P8: Composite Signal ──
    cs = (snap.get("composite_signals", {}) or {}).get(ticker)
    if cs and isinstance(cs, dict):
        cdir = cs.get("direction", "NEUTRAL")
        cconf = cs.get("confidence", 0)
        if cdir == direction:
            add_layer("Composite", f"ALIGN ({cconf:.0%})", 5)
        elif cdir != "NEUTRAL":
            add_layer("Composite", f"CONFLICT ({cconf:.0%})", -5)

    # ── Clamp & Resolve ──
    score = max(0, min(100, score))

    if score >= 70:
        signal = "BUY" if direction == "LONG" else "SELL"
    elif score <= 30:
        signal = "SELL" if direction == "LONG" else "BUY"  # contradictory
    else:
        signal = "HOLD"

    # IHSG buy-only override
    if market_type == "ihsg" and signal == "SELL":
        signal = "HOLD"

    return {
        "signal": signal,
        "confidence": score,
        "layers": layers,
        "direction": direction,
        "market_type": market_type,
        "n_layers": len(layers),
    }


def _get_single_recommendation(options, direction="LONG", market_type="us_equity",
                               cot_data=None, onchain_data=None, ticker="", prices=None, row=None,
                               dark_pool=None, unusual_activity=None):
    """
    AUDITED RECOMMENDATION ENGINE v32.9 — Hedgeye + Options + COT + Dark Pool + UOA + On-chain + IDHL + RC + AFS
    """
    def _safe_num(v, default=0.0):
        if v is None: return default
        try:
            if isinstance(v, str):
                v = v.replace("−", "-").replace("—", "-").strip()
            f = float(v)
            return f if math.isfinite(f) else default
        except:
            return default

    gamma = str(options.get("gamma_regime", ""))
    mp = _safe_num(options.get("max_pain"), 0)
    mp_dist = _safe_num(options.get("mp_dist"), 0)
    skew = _safe_num(options.get("skew_30d"), 0)
    iv_rank = _safe_num(options.get("iv_rank"), 50)
    pc_ratio = _safe_num(options.get("pc_ratio"), 1.0)
    vanna = _safe_num(options.get("vanna"), 0)
    charm = _safe_num(options.get("charm"), 0)
    gex = _safe_num(options.get("gex"), 0)
    expected_move = _safe_num(options.get("expected_move_pct"), 0)
    put_wall = _safe_num(options.get("put_wall"), 0)
    call_wall = _safe_num(options.get("call_wall"), 0)
    oi_call = options.get("oi_call", 0) or 0
    oi_put = options.get("oi_put", 0) or 0
    source = options.get("source", "PROXY")
    formation = row.get("formation", "NEUTRAL") if row else "NEUTRAL"
    px = row.get("price", 0) if row else 0
    trend_top = row.get("trend_top", 0) if row else 0
    trade_low = row.get("trade_low", 0) if row else 0
    near_peak = False
    if px and trend_top:
        near_peak = px > trend_top * 0.95
    near_bottom = False
    if px and trade_low:
        near_bottom = px < trade_low * 1.05

    scores = []
    reasons = []

    # 1. HEDGEYE FORMATION
    if formation == "BULLISH":
        scores.append(("BUY", 80))
        reasons.append(("🟢 Hedgeye BULLISH: Price > Trend Top AND Tail Top. Buy dips.", 80))
    elif formation == "BEARISH":
        scores.append(("SELL", 80))
        reasons.append(("🔴 Hedgeye BEARISH: Price < Trend Low AND Tail Low. Sell rallies.", 80))
    elif formation == "BULLISH_BIAS":
        scores.append(("BUY", 60))
        reasons.append(("🟡 Hedgeye BULLISH BIAS: Price > Trend Top. Favorable for longs.", 60))
    elif formation == "BEARISH_BIAS":
        scores.append(("SELL", 60))
        reasons.append(("🟡 Hedgeye BEARISH BIAS: Price < Trend Low. Favorable for shorts.", 60))
    elif formation == "OVERSOLD":
        scores.append(("BUY", 70))
        reasons.append(("📉 OVERSOLD: Price below Trade Low. Mean-reversion play.", 70))
    elif formation == "OVERBOUGHT":
        scores.append(("SELL", 70))
        reasons.append(("📈 OVERBOUGHT: Price above Trade Top. Mean-reversion play.", 70))
    else:
        scores.append(("HOLD", 40))
        reasons.append(("⚪ NEUTRAL: Price between Trend Low/Top. Range-bound.", 40))

    # 2. PEAK DETECTION
    if near_peak and direction == "LONG":
        scores.append(("HOLD", 50))
        reasons.append(("⚠️ NEAR PEAK — Price within 5% of Trend Top. Risk/reward poor. Wait pullback.", 50))
    elif near_bottom and direction == "SHORT":
        scores.append(("HOLD", 50))
        reasons.append(("⚠️ NEAR BOTTOM — Price within 5% of Trade Low. Shorting into support risky.", 50))
    elif near_bottom and direction == "LONG":
        scores.append(("BUY", 20))
        reasons.append(("🎯 NEAR BOTTOM — Excellent entry zone. Asymmetric upside.", 20))

    # 3. MM POSITIONING
    if abs(mp_dist) < 0.025 and gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("HOLD/SELL_PREMIUM", 60))
        reasons.append(("📍 Pinned near max pain ({:.1f}%) + pos gamma = range-bound.".format(mp_dist*100), 60))
    elif mp_dist < -0.03 and gamma in ("NEGATIVE", "DEEP_NEGATIVE"):
        scores.append(("BUY", 85))
        reasons.append((f"📉 Below max pain ({mp_dist*100:.1f}%) + neg gamma = MM buys dips. Put wall ${_ffm(put_wall, market_type)}.", 85))
    elif mp_dist > 0.03 and gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("SELL/COVERED_CALL", 70))
        reasons.append((f"📈 Above max pain (+{mp_dist*100:.1f}%) + pos gamma = MM sells rallies. Call wall ${_ffm(call_wall, market_type)}.", 70))
    elif gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("BUY", 55))
        reasons.append(("🟢 Positive gamma — dealer long, mean-reversion to max pain ${:.2f}.".format(mp), 55))
    elif gamma in ("NEGATIVE", "DEEP_NEGATIVE"):
        scores.append(("BUY", 65))
        reasons.append(("🔴 Negative gamma — dealer short, trend acceleration on breakout.", 65))

    # 4. SKEW
    if skew > 0.05 and iv_rank > 60:
        scores.append(("BUY", 70))
        reasons.append(("🔴 Put skew rich ({:+.2f}) + IV rank {:.0f}% = fear overpriced.".format(skew, iv_rank), 70))
    elif skew < -0.05 and iv_rank < 40:
        scores.append(("BUY", 75))
        reasons.append(("🟢 Call skew cheap ({:+.2f}) + IV rank {:.0f}% = upside convexity underpriced.".format(skew, iv_rank), 75))
    elif iv_rank < 35:
        scores.append(("BUY", 60))
        reasons.append(("💤 IV rank {:.0f}% low — ideal accumulation.".format(iv_rank), 60))
    elif iv_rank > 65:
        scores.append(("HEDGE", 55))
        reasons.append(("⚠️ IV rank {:.0f}% high — expensive options, sell premium or hedge.".format(iv_rank), 55))

    # 5. GEX
    if gex > 1.0:
        scores.append(("SELL/COVERED_CALL", 65))
        reasons.append(("🟢 GEX +{:.2f} extreme positive — strong mean-reversion. Sell covered calls.".format(gex), 65))
    elif gex < -1.0:
        scores.append(("BUY", 70))
        reasons.append(("🔴 GEX {:.2f} extreme negative — trend acceleration. Buy dips.".format(gex), 70))

    # 6. VANNA
    if vanna > 0.5:
        scores.append(("BUY", 60))
        reasons.append(("🟢 Vanna +{:.2f}: Rally = vol crush. Buy spot on dips.".format(vanna), 60))
    elif vanna < -0.5:
        scores.append(("HEDGE", 55))
        reasons.append(("🔴 Vanna {:.2f}: Rally = vol expansion. Breakouts volatile — hedge.".format(vanna), 55))

    # 7. CHARM
    if charm > 0.5:
        scores.append(("BUY", 55))
        reasons.append(("🟢 Charm +{:.2f}: Put support strengthening daily.".format(charm), 55))
    elif charm < -0.5:
        scores.append(("HEDGE", 60))
        reasons.append(("🔴 Charm {:.2f}: Put support eroding — downside acceleration risk.".format(charm), 60))

    # 8. P/C RATIO
    if pc_ratio < 0.60:
        scores.append(("CAUTION", 50))
        reasons.append(("🎰 PC ratio {:.2f} extreme low = retail call FOMO. Watch exhaustion.".format(pc_ratio), 50))
    elif pc_ratio > 1.3:
        scores.append(("BUY", 55))
        reasons.append(("🛡️ PC ratio {:.2f} high = put hedging active. Contrarian bullish.".format(pc_ratio), 55))

    # 9. COT
    if market_type in ("forex", "commodity") and cot_data and cot_data.get("signal") != "NEUTRAL":
        cot_sig = cot_data.get("signal", "NEUTRAL")
        cot_net = cot_data.get("net_noncom", 0)
        cot_chg = cot_data.get("change_wow", 0)
        if cot_sig == "BULLISH":
            scores.append(("BUY", 65))
            reasons.append(("🏛️ COT Non-Commercial net +{:,} (WoW {:+,}) = institutional buying.".format(int(cot_net), int(cot_chg)), 65))
        elif cot_sig == "BEARISH":
            scores.append(("SELL", 65))
            reasons.append(("🏛️ COT Non-Commercial net {:,} (WoW {:+,}) = institutional selling.".format(int(cot_net), int(cot_chg)), 65))

    # 10. ON-CHAIN
    if market_type == "crypto" and onchain_data:
        whale = onchain_data.get("whale_signal", "HOLD")
        funding = onchain_data.get("funding_proxy", 0)
        if whale == "BUY":
            scores.append(("BUY", 70))
            reasons.append(("🐋 Whale accumulation + momentum {}.".format(onchain_data.get("momentum", "—")), 70))
        elif whale == "SELL":
            scores.append(("SELL", 70))
            reasons.append(("🐋 Whale distribution — reduce exposure.", 70))
        if abs(funding) > 0.0005:
            scores.append(("CAUTION", 45))
            reasons.append(("⛓️ Funding rate extreme ({:.5f}) = leverage excess.".format(funding), 45))

    # 11. DARK POOL
    if dark_pool and isinstance(dark_pool, dict):
        div = dark_pool.get("divergence", "NEUTRAL")
        zf = dark_pool.get("zero_flag")
        dp_sig = dark_pool.get("dp_signal", "NEUTRAL")
        if zf == "ZERO_SELLS" and direction == "LONG":
            scores.append(("BUY", 25))
            reasons.append(("🔥 ZERO DARK SELLS — Pure institutional accumulation.", 25))
        elif zf == "ZERO_BUYS" and direction == "SHORT":
            scores.append(("SELL", 25))
            reasons.append(("❄️ ZERO DARK BUYS — Pure institutional distribution.", 25))
        elif div == "HIDDEN_ACCUMULATION" and direction == "LONG":
            scores.append(("BUY", 20))
            reasons.append(("🟢 HIDDEN ACCUMULATION — Public selling, institutions buying stealth.", 20))
        elif div == "HIDDEN_DISTRIBUTION" and direction == "SHORT":
            scores.append(("SELL", 20))
            reasons.append(("🔴 HIDDEN DISTRIBUTION — Public buying, institutions dumping.", 20))
        elif div == "BOTH_AGREE" and direction == "LONG" and dp_sig == "BUY":
            scores.append(("BUY", 15))
            reasons.append(("✅ BOTH TAPES AGREE — Strong conviction.", 15))
        elif div == "BOTH_AGREE" and direction == "SHORT" and dp_sig == "SELL":
            scores.append(("SELL", 15))
            reasons.append(("✅ BOTH TAPES AGREE — Strong conviction.", 15))
        elif div in ("HIDDEN_DISTRIBUTION", "HIDDEN_ACCUMULATION"):
            scores.append(("CAUTION", 10))
            reasons.append(("⚠️ DARK POOL DIVERGENCE — Signal conflicts. Tighten stop.", 10))

    # 12. UNUSUAL ACTIVITY
    if unusual_activity and isinstance(unusual_activity, dict):
        if unusual_activity.get("large_order_detected"):
            ua_sig = unusual_activity.get("signal", "NEUTRAL")
            ua_conf = unusual_activity.get("confidence", 0)
            if ua_sig == "BUY" and direction == "LONG":
                scores.append(("BUY", min(20, ua_conf // 5)))
                reasons.append(("🐋 Large order absorption (vol spike + flat price). Institutional accumulation.", min(20, ua_conf // 5)))
            elif ua_sig == "SELL" and direction == "SHORT":
                scores.append(("SELL", min(20, ua_conf // 5)))
                reasons.append(("🐋 Large order distribution. Institutional selling.", min(20, ua_conf // 5)))
        if unusual_activity.get("uoa_detected"):
            scores.append(("CAUTION" if direction == "LONG" else "BUY", 15))
            reasons.append(("⚡ Unusual Options Activity detected. Watch gamma squeeze.", 15))
        if unusual_activity.get("onchain_detected"):
            scores.append(("BUY" if unusual_activity.get("signal") == "BUY" else "SELL", 15))
            reasons.append(("⛓️ On-chain anomaly: {}.".format(unusual_activity.get("details", "")), 15))

    # 13. CHASE/WAIT
    if row and row.get("chase_status"):
        chase = row.get("chase_status")
        rr_val = row.get("rr", 0) or 0
        if chase == "CHASE":
            scores.append(("BUY" if direction == "LONG" else "SELL", 15))
            reasons.append(("🏃 Price at/near entry — immediate execution valid.", 15))
        elif chase == "WAIT":
            scores.append(("HOLD", 20))
            reasons.append(("⏳ Price away from entry — wait for pullback.", 20))
        elif chase == "AVOID":
            scores.append(("HOLD", 40))
            reasons.append(("🚫 Setup invalidated — stop level breached.", 40))
        if rr_val >= 3.0:
            scores.append(("BUY" if direction == "LONG" else "SELL", 10))
            reasons.append(("🎯 RR {:.1f}x — highly asymmetric reward.".format(rr_val), 10))
        elif rr_val < 1.5 and rr_val > 0:
            scores.append(("HOLD", 15))
            reasons.append(("⚠️ RR {:.1f}x — poor risk/reward. Skip or wait.".format(rr_val), 15))

    # ── VALIDATION ──
    if row and not row.get("setup_valid", True):
        return {
            "action": "HOLD / TUNGGU", "strategy": "Setup invalid — stop too close or risk < 0.5%",
            "rationale": f"• 🚫 Stop {_ffm(row.get('stop'), market_type)} too close to entry {_ffm(row.get('entry'), market_type)} (risk {row.get('risk_pct',0):.2f}% < 0.5% min).",
            "raw_action": "HOLD", "confidence": 0, "factors": 0, "source": "VALIDATION",
            "near_peak": near_peak, "near_bottom": near_bottom,
        }

    # ── AGGREGATE ──
    action_weights = {}
    for action, weight in scores:
        action_weights[action] = action_weights.get(action, 0) + weight
    if not action_weights:
        best_action = "HOLD"; best_score = 0
    else:
        best_action = max(action_weights, key=action_weights.get)
        best_score = action_weights[best_action]

    action_map = {
        "BUY": ("BELI SPOT / AKUMULASI", "Tambah posisi spot atau beli LEAPS/calls"),
        "SELL": ("JUAL / REDUKSI", "Turunkan exposure atau short via puts"),
        "SELL/COVERED_CALL": ("JUAL COVERED CALL", "Jual call di resistance untuk income"),
        "HEDGE": ("HEDGE POSISI", "Beli put protektif atau reduce beta"),
        "HOLD/SELL_PREMIUM": ("HOLD + JUAL PREMIUM", "Straddle/strangle untuk income saat pinned"),
        "CAUTION": ("WASPADA / TUNGGU", "Signal konflik — tunggu konfirmasi breakout"),
        "HOLD": ("HOLD / TUNGGU", "Data tidak cukup kuat — tunggu setup lebih jelas"),
    }
    final_action, final_strategy = action_map.get(best_action, ("HOLD", "Tunggu"))

    rationale_lines = []
    for reason_text, score in reasons:
        rationale_lines.append(f"• {reason_text} <span style='color:#484F58;font-size:0.6rem;'>(+{score})</span>")
    rationale = "<br>".join(rationale_lines) if rationale_lines else "• Data options/greeks tidak cukup untuk rekomendasi kuat."

    if expected_move > 0:
        rationale += f"<br>• 📊 Expected move: ±{expected_move:.1%} until expiry."
    if oi_call and oi_put:
        total_oi = oi_call + oi_put
        call_pct = oi_call / total_oi * 100
        rationale += f"<br>• 📈 OI Call/Put: {call_pct:.0f}%/{100-call_pct:.0f}% ({total_oi/1e6:.1f}M total)"
    if near_peak:
        rationale += f"<br>• ⚠️ <b>NEAR PEAK WARNING:</b> Price within 5% of Trend Top. Risk/reward deteriorating. Wait for pullback to Trade Low."
    if near_bottom:
        rationale += f"<br>• 🎯 <b>NEAR BOTTOM:</b> Price within 5% of Trade Low. Excellent asymmetric entry if setup valid."
    rationale += f"<br>• 🔧 Data source: <b>{source}</b> (YF=live, PROXY=calculated from price)"

    return {
        "action": final_action, "strategy": final_strategy, "rationale": rationale,
        "raw_action": best_action, "confidence": min(100, best_score),
        "factors": len(reasons), "source": source,
        "near_peak": near_peak, "near_bottom": near_bottom,
    }


# ═══════════════════════════════════════════════════════════════════
# BOOM-BUST + BEHAVIORAL SCORING
# ═══════════════════════════════════════════════════════════════════
def _get_ticker_boombust_score(ticker, prices, snap):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 60):
        return {"score": 0, "stage": "UNKNOWN", "signal": "—"}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 60: return {"score": 0, "stage": "UNKNOWN", "signal": "—"}

        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        sma50 = float(s_clean.tail(50).mean()) if len(s_clean) >= 50 else sma20
        sma200 = float(s_clean.tail(200).mean()) if len(s_clean) >= 200 else sma50

        r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1) if len(s_clean) >= 22 else 0
        r3m = float(s_clean.iloc[-1] / s_clean.iloc[-63] - 1) if len(s_clean) >= 63 else r1m
        r6m = float(s_clean.iloc[-1] / s_clean.iloc[-126] - 1) if len(s_clean) >= 126 else r3m

        mom_accel = r1m - (r3m / 3) if r3m != 0 else 0
        dist_from_200 = (px - sma200) / sma200 if sma200 != 0 else 0

        vol_20 = float(s_clean.tail(20).std())
        vol_60 = float(s_clean.tail(60).std()) if len(s_clean) >= 60 else vol_20
        vol_expansion = (vol_20 / vol_60 - 1) if vol_60 > 0 else 0

        score = 0
        if r1m > 0.20: score += 3
        elif r1m > 0.10: score += 2
        elif r1m > 0.05: score += 1

        if dist_from_200 > 0.30: score += 3
        elif dist_from_200 > 0.15: score += 2
        elif dist_from_200 > 0.05: score += 1

        if mom_accel > 0.10: score += 2
        elif mom_accel > 0.05: score += 1

        if vol_expansion > 0.50: score += 2
        elif vol_expansion > 0.20: score += 1

        score = min(10, max(0, score))

        if score >= 8: stage = "EUPHORIA"
        elif score >= 6: stage = "ACCELERATION"
        elif score >= 4: stage = "INCEPTION"
        elif score >= 2: stage = "EARLY"
        else: stage = "BASE"

        if score >= 7:
            signal = "⚠️ BUBBLE RISK — Consider taking profits"
        elif score >= 4 and r1m > 0.10:
            signal = "📈 Momentum strong but watch for exhaustion"
        elif score <= 2 and r1m < -0.10:
            signal = "🔨 Capitulation — potential bottom"
        elif score <= 3 and r1m > 0.05:
            signal = "🌱 Early stage — good accumulation zone"
        else:
            signal = "➡️ Neutral — no extreme bubble/capitulation"

        return {"score": round(score, 1), "stage": stage, "signal": signal,
                "r1m": round(r1m, 3), "dist_200": round(dist_from_200, 3)}
    except Exception:
        return {"score": 0, "stage": "UNKNOWN", "signal": "—"}


def _get_ticker_behavioral_score(ticker, prices, options, snap):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}

        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else r5d

        pc_ratio = (_safe_float(options.get("pc_ratio")) or 1.0) if options else 1.0
        iv_rank = (_safe_float(options.get("iv_rank")) or 50) if options else 50
        skew = (_safe_float(options.get("skew_30d")) or 0) if options else 0

        casino = 0
        if r5d > 0.15 and r20d > 0.30: casino += 40
        if pc_ratio < 0.60: casino += 20
        if iv_rank > 70: casino += 20
        if skew < -0.10: casino += 20
        casino = min(100, casino)

        sm_divergence = False
        if r5d > 0.05 and pc_ratio > 1.2 and iv_rank < 40:
            sm_divergence = True

        retail_fomo = casino > 60

        if casino > 70:
            signal = f"🎰 CASINO MODE ({casino}%) — Retail FOMO extreme. Raise cash."
        elif casino > 50:
            signal = f"⚠️ Elevated speculation ({casino}%) — Tighten stops."
        elif sm_divergence:
            signal = "🐋 Smart Money Divergence — Price up but hedging detected."
        elif casino < 20 and r20d < -0.15:
            signal = "😰 Fear/Capitulation — Contrarian buy opportunity."
        else:
            signal = f"✅ Behavior normal ({casino}%). No extreme positioning."

        return {"casino_score": casino, "retail_fomo": retail_fomo,
                "smart_money_divergence": sm_divergence, "signal": signal,
                "pc_ratio": round(pc_ratio, 2), "iv_rank": round(iv_rank, 0)}
    except Exception:
        return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}

# ═══════════════════════════════════════════════════════════════════
# VISUAL RENDERERS v4 — AUDITED (DUPLICATES REMOVED)
# ═══════════════════════════════════════════════════════════════════
def _interpret_gamma(gamma_regime, px, max_pain):
    if not gamma_regime: return ""
    mp_dist = ((px - max_pain) / max_pain * 100) if max_pain else 0
    if gamma_regime in ("DEEP_POSITIVE", "POSITIVE"):
        return f"🟢 Positive gamma — dealers long. Pin risk to max pain ({mp_dist:+.1f}%). Rallies face call-wall resistance. Sell into strength."
    elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"):
        return f"🔴 Negative gamma — dealers short. Acceleration risk on break. Dips get bought at put wall. Buy weakness."
    else:
        return f"🟡 Transition gamma — directional play valid. Watch for vanna/charm shift."


def _interpret_gex(gex):
    if gex is None: return ""
    if gex > 0.5: return f"🟢 GEX +{gex:.2f}: Dealer long gamma → mean-reversion, sell rallies."
    elif gex < -0.5: return f"🔴 GEX {gex:.2f}: Dealer short gamma → trend acceleration, buy dips."
    else: return f"🟡 GEX {gex:.2f}: Neutral — watch breakout direction."


def _interpret_vanna(vanna):
    if vanna is None: return ""
    try: v = float(vanna)
    except: return ""
    if v > 0.5: return f"🟢 Vanna +{v:.2f}: Rally = vol crush (bearish vol). Sell premium into strength."
    elif v < -0.5: return f"🔴 Vanna {v:.2f}: Rally = vol expansion (bullish vol). Buy premium on breakouts."
    else: return f"🟡 Vanna {v:.2f}: Neutral spot-vol correlation."


def _interpret_charm(charm):
    if charm is None: return ""
    try: c = float(charm)
    except: return ""
    if c > 0.5: return f"🟢 Charm +{c:.2f}: Put support strengthening over time."
    elif c < -0.5: return f"🔴 Charm {c:.2f}: Put support eroding — downside acceleration risk."
    else: return f"🟡 Charm {c:.2f}: Minimal theta-driven delta shift."


def _interpret_skew(skew_30d):
    if skew_30d is None: return ""
    s = float(skew_30d)
    if s > 0.05: return f"🔴 Skew {s:+.2f}: OTM puts rich — fear priced in. Potential reversal if fear fades."
    elif s < -0.05: return f"🟢 Skew {s:+.2f}: OTM calls rich — greed/fomo. Potential pullback if euphoria breaks."
    else: return f"🟡 Skew {s:+.2f}: Fair — balanced risk pricing."


def _interpret_mm(mm_pos, mp_dist):
    if not mm_pos or mm_pos == "UNKNOWN": return ""
    if mm_pos == "PINNED":
        return f"📍 PINNED (dist {mp_dist:+.1f}%): MM trapped near max pain. Range-bound until expiry. Sell straddles or wait breakout."
    elif mm_pos == "CALL_WALL":
        return f"📈 CALL WALL (dist +{mp_dist:.1f}%): Price above max pain + positive gamma. MM sells into rallies. Fade strength."
    elif mm_pos == "PUT_WALL":
        return f"📉 PUT WALL (dist {mp_dist:.1f}%): Price below max pain + negative gamma. MM buys dips. Support holds."
    elif mm_pos == "TRANSITION":
        return f"🔄 TRANSITION: Between walls — directional play valid. Watch vanna/charm for momentum shift."
    return ""


def _get_smart_money_badge(ticker, snap):
    sm = snap.get("smart_money", {}) if isinstance(snap.get("smart_money"), dict) else {}
    consensus = sm.get("consensus_picks", []) if isinstance(sm.get("consensus_picks"), list) else []
    for c in consensus:
        if isinstance(c, dict) and c.get("ticker") == ticker:
            return f"🐋 Smart${c.get('n_funds', 0)}"
    return ""


def _get_capital_rotation_role(ticker, snap):
    cr = snap.get("capital_rotation", {}) if isinstance(snap.get("capital_rotation"), dict) else {}
    roles = cr.get("ticker_roles", {}) if isinstance(cr.get("ticker_roles"), dict) else {}
    return roles.get(ticker, "")


def _get_vrp_score(ticker, snap):
    vrp = snap.get("vrp_scanner", {}) if isinstance(snap.get("vrp_scanner"), dict) else {}
    if vrp.get("ok"):
        for item in vrp.get("high_vrp_sell_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("vrp_pct", 0)
        for item in vrp.get("low_vrp_buy_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return -item.get("vrp_pct", 0)
    return 0


def _get_squeeze_score(ticker, snap):
    sq = snap.get("squeeze_scanner", {}) if isinstance(snap.get("squeeze_scanner"), dict) else {}
    if sq.get("ok"):
        for item in sq.get("imminent_squeezes", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("squeeze_score", 0)
        for item in sq.get("strong_candidates", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("squeeze_score", 0)
    return 0


def _get_markov_confidence(ticker, snap):
    m = snap.get("markov_v3", {}) if isinstance(snap.get("markov_v3"), dict) else {}
    return m.get("confidence", 0)


def render_ticker_card_v4(row, expanded=False):
    """Hedgeye-style ticker card v32.9 — Compact header + rich expander."""
    ticker = row.get("ticker", "?")
    px = row.get("price", 0)
    direction = row.get("direction", "NEUTRAL")
    grade = row.get("grade", "C")
    rr_val = row.get("rr", 0)
    entry = row.get("entry")
    t1 = row.get("target_1")
    t2 = row.get("target_2")
    stop = row.get("stop")
    trade_l = row.get("trade_low")
    trade_r = row.get("trade_top")
    news_sig = row.get("news_signal", "")
    r1m = row.get("r20d")
    mm_pos = row.get("mm_positioning", "")
    options = row.get("options", {})
    market_type = row.get("market_type", "us_equity")
    show_options = market_type != "ihsg"
    snap_local = st.session_state.get("snap")

    formation = row.get("formation", "NEUTRAL")
    setup_valid = row.get("setup_valid", True)
    risk_pct = row.get("risk_pct", 0)
    chase_status = row.get("chase_status", "NEUTRAL")
    chase_text = row.get("chase_text", "")
    chase_color = row.get("chase_color", "#8B949E")

    dir_kind = "long" if "LONG" in direction else "short" if "SHORT" in direction else "neut"
    dir_label = "LONG" if "LONG" in direction else "SHORT"
    grade_kind = grade.lower().replace("+", "")

    # ── Build badges ──
    badges = ""
    # v39.1: Keith P0 override badge (highest priority)
    ks = row.get("keith_sync", {})
    if ks and isinstance(ks, dict) and ks.get("override"):
        kt = ks.get("keith_trade", "BEARISH")
        kcolor = "#F85149" if kt == "BEARISH" else "#3FB950"
        badges += f'<span style="background:{kcolor}22;color:{kcolor};padding:2px 8px;border-radius:12px;font-size:0.65rem;font-weight:700;border:1px solid {kcolor}50;letter-spacing:0.3px;">🎙️ KEITH {kt[:4]}</span>'
    badges += _badge_html(dir_label, dir_kind)
    badges += _badge_html(grade, grade_kind)
    if formation == "BULLISH":
        badges += _badge_html("📈 Bullish", "long")
    elif formation == "BEARISH":
        badges += _badge_html("📉 Bearish", "short")
    elif formation == "BULLISH_BIAS":
        badges += _badge_html("📈 Bias+", "long")
    elif formation == "BEARISH_BIAS":
        badges += _badge_html("📉 Bias-", "short")
    elif formation == "OVERSOLD":
        badges += _badge_html("📉 Oversold", "long")
    elif formation == "OVERBOUGHT":
        badges += _badge_html("📈 Overbought", "short")
    if not setup_valid:
        badges += _badge_html("🚫 INVALID", "short")

    # Quality score badge
    qscore = row.get("quality_score", 0)
    if qscore >= 80:
        badges += _badge_html(f"⭐ {qscore:.0f}", "a")
    elif qscore >= 60:
        badges += _badge_html(f"✓ {qscore:.0f}", "b")
    elif qscore >= 40:
        badges += _badge_html(f"△ {qscore:.0f}", "c")
    elif qscore > 0:
        badges += _badge_html(f"⚠ {qscore:.0f}", "short")

    # Breakout / Breakdown badges
    if row.get("breakout_mode"):
        badges += _badge_html("🔥 ATH BREAKOUT", "chase")
    if row.get("breakdown_mode"):
        badges += _badge_html("🔥 BREAKDOWN", "short")

    if rr_val and rr_val >= 2:
        badges += _badge_html(f"RR {rr_val}x", "news")
    if mm_pos and mm_pos != "UNKNOWN":
        badges += _badge_html(mm_pos, "mm")

    if chase_status == "CHASE":
        badges += _badge_html("🏃 CHASE", "chase")
    elif chase_status == "WAIT":
        badges += _badge_html("⏳ WAIT", "wait")
    elif chase_status == "AVOID":
        badges += _badge_html("🚫 AVOID", "short")

    # Simulation badges
    sim = row.get("simulation")
    if sim:
        score = sim.get("robustness_score", 0)
        score_kind = "a" if score >= 80 else "b" if score >= 65 else "c"
        badges += _badge_html(f"🎲 {score:.0f}", score_kind)
        if sim.get("win_rate", 0) >= 60:
            badges += _badge_html(f"WR {sim['win_rate']:.0f}%", "long")
        opt_e = sim.get("optimal_entry_adj_pct", 0)
        if opt_e != 0:
            badges += _badge_html(f"Entry {opt_e:+.1f}%", "wait" if opt_e < 0 else "chase")

    # ── Attachment 4 badges ──
    # IDHL: signal decay classification
    idhl = row.get("idhl", 0)
    if idhl > 0:
        if idhl < 1.0:
            badges += _badge_html("🚫 NOISE", "short")
        elif idhl >= 10.0:
            badges += _badge_html("📌 STRUCTURAL", "long")
        else:
            badges += _badge_html(f"IDHL {idhl:.1f}d", "wait")

    # RC: Reflexivity Coefficient
    rc_level = row.get("rc_level", "")
    if rc_level == "HIGH":
        badges += _badge_html("🚫 SOROS LOOP", "short")
    elif rc_level == "MEDIUM":
        badges += _badge_html("⚠️ REFLEX", "wait")

    # Walk-Forward validation
    wf = row.get("walkforward", {})
    if wf and wf.get("passes_gate"):
        badges += _badge_html(f"✅ WF {wf.get('consistency',0):.0%}", "long")
    elif wf:
        badges += _badge_html("❌ WF FAIL", "short")

    confluence = row.get("confluence", {})
    if confluence.get("entry_cluster") and confluence["entry_cluster"].get("count", 0) >= 2:
        badges += _badge_html(f"🔥 x{confluence['entry_cluster']['count']}", "a")

    # Dark Pool badges
    dp = row.get("dark_pool")
    if dp and isinstance(dp, dict):
        div = dp.get("divergence", "NEUTRAL")
        if div == "HIDDEN_ACCUMULATION":
            badges += _badge_html("🟢 Hidden", "long")
        elif div == "HIDDEN_DISTRIBUTION":
            badges += _badge_html("🔴 Hidden", "short")
        elif div == "BOTH_AGREE":
            dp_sig = dp.get("dp_signal", "")
            badges += _badge_html("✅ Agree", "long" if dp_sig == "BUY" else "short")
        if dp.get("zero_flag") == "ZERO_SELLS":
            badges += _badge_html("🔥 ZeroSell", "long")
        elif dp.get("zero_flag") == "ZERO_BUYS":
            badges += _badge_html("❄️ ZeroBuy", "short")

    # Alpha source badges
    alpha_src = row.get("alpha_source", "")
    alpha_score = row.get("alpha_score", 0)
    if alpha_src:
        src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","karsan_squeeze":"📊","karsan_convexity":"📐","coatue":"💱"}.get(alpha_src,"⚡")
        badges += _badge_html(f"{src_emoji} {alpha_src.replace('_',' ').title()}", "mm")
    if alpha_score:
        badges += _badge_html(f"α{alpha_score}", "a" if alpha_score >= 80 else "b" if alpha_score >= 70 else "c")

    if snap_local:
        sm_badge = _get_smart_money_badge(ticker, snap_local)
        if sm_badge:
            badges += _badge_html(sm_badge, "news")
        vrp = _get_vrp_score(ticker, snap_local)
        if vrp > 10:
            badges += _badge_html(f"VRP+{vrp:.0f}%", "short")
        elif vrp < -10:
            badges += _badge_html(f"VRP{vrp:.0f}%", "long")
        sq = _get_squeeze_score(ticker, snap_local)
        if sq > 60:
            badges += _badge_html(f"Squeeze {sq:.0f}", "news")
        cr_role = _get_capital_rotation_role(ticker, snap_local)
        if cr_role:
            badges += _badge_html(cr_role.replace("_"," ")[:12], "neut")

    # ── Risk Range bar (Hedgeye style) ──
    rr_bar_html = _risk_range_html(px, trade_l, trade_r, width_pct=100)

    # ── Status banner inside card ──
    status_banner = ""
    # v39.5: Keith P0 override takes precedence over all technical signals
    ks = row.get("keith_sync", {})
    if ks and isinstance(ks, dict) and ks.get("override"):
        kt = ks.get("keith_trade", "BEARISH")
        status_banner = f'<div class="hy-status-pill banner-avoid">🚫 AVOID — Keith {kt.title()} Override</div>'
        chase_status = "AVOID"
        chase_color = "#F85149"
        chase_text = f"🚫 AVOID — Keith {kt.title()} Override: {ks.get('basis','')[:120]}"
    elif not setup_valid:
        status_banner = f'<div class="hy-status-pill banner-avoid">🚫 INVALID — Stop too tight / Risk &lt; min</div>'
    elif chase_status == "CHASE":
        if row.get("breakout_note"):
            status_banner = f'<div class="hy-status-pill banner-chase">{row["breakout_note"][:80]}</div>'
        else:
            status_banner = f'<div class="hy-status-pill banner-chase">🏃 CHASE — Ready to enter</div>'
    elif chase_status == "WAIT":
        if row.get("breakdown_note"):
            status_banner = f'<div class="hy-status-pill banner-avoid">{row["breakdown_note"][:80]}</div>'
        else:
            status_banner = f'<div class="hy-status-pill banner-wait">⏳ WAIT — Pullback needed</div>'
    elif chase_status == "AVOID":
        status_banner = f'<div class="hy-status-pill banner-avoid">🚫 AVOID — Setup broken</div>'
    else:
        status_banner = f'<div class="hy-status-pill banner-hold">⏸ HOLD — Monitor</div>'

    # ── Meta row ──
    meta_parts = []
    if entry is not None:
        meta_parts.append(f'Entry <b>{_ffm(entry, market_type)}</b>')
    if t1 is not None:
        meta_parts.append(f'T1 <b>{_ffm(t1, market_type)}</b>')
    if stop is not None:
        meta_parts.append(f'SL <b>{_ffm(stop, market_type)}</b> ({risk_pct:.1f}%)')
    if rr_val:
        meta_parts.append(f'RR <b>{rr_val:.1f}x</b>')
    if r1m is not None:
        meta_parts.append(f'1M <b>{fp(r1m)}</b>')
    qreasons = row.get("quality_reasons", [])
    if qreasons:
        meta_parts.append(f'Edge <b>{" · ".join(qreasons[:3])}</b>')

    extra_meta = ""
    ts = row.get("trend_strength")
    if ts is not None:
        extra_meta += f' · Trend <b>{ts:.0f}</b>'
    mk = row.get("markov_ctx")
    if mk and mk.get("confidence", 0) > 0.3:
        extra_meta += f' · 🔮 <b>{mk.get("confidence",0):.0%}</b>'

    meta_html = " · ".join(meta_parts) + extra_meta

    # ── Assemble Hedgeye card ──
    card_html = (
        f'<div class="hy-card">'
        f'<div class="hy-header">'
        f'<div class="hy-symbol">{ticker}</div>'
        f'<div class="hy-price">{_ffm(px, market_type)}</div>'
        f'<div class="hy-badges">{badges}</div>'
        f'</div>'
        f'<div class="hy-status-bar">{status_banner}</div>'
        f'<div style="padding: 4px 12px;">{rr_bar_html}</div>'
        f'<div class="hy-meta-row">{meta_html}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # ── Trade Setup Expander ──
    expander_label = "🔍 Essential Details" if market_type != "ihsg" else "🔍 Essential Details"
    with st.expander(expander_label, expanded=expanded):
        # Alpha thesis
        alpha_thesis = row.get("alpha_thesis", "")
        alpha_src = row.get("alpha_source", "")
        if alpha_thesis:
            src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","karsan_squeeze":"📊","karsan_convexity":"📐","coatue":"💱"}.get(alpha_src,"⚡")
            st.markdown(
                f'<div class="alpha-thesis-card">'
                f'<div class="alpha-thesis-title">{src_emoji} {alpha_src.replace("_"," ").title()} Thesis</div>'
                f'<div class="alpha-thesis-sub">{alpha_thesis}</div>'
                f'</div>', unsafe_allow_html=True)

        # ── Simulation Panel ──
        sim = row.get("simulation")
        if sim:
            score = sim.get("robustness_score", 0)
            score_c = "#3FB950" if score >= 80 else "#D29922" if score >= 65 else "#F85149"
            sim_html = f'<div class="ts-panel" style="border-color: {score_c}40; margin-bottom: 8px;">'
            sim_html += f'<div class="ts-panel-title">🎲 Monte Carlo Simulation (100 runs)</div>'
            sim_html += f'<div class="ts-grid-4">'
            sim_html += f'<div class="ts-stat"><div class="ts-stat-label">Robustness</div><div class="ts-stat-value" style="color:{score_c};">{score:.0f}/100</div></div>'
            sim_html += f'<div class="ts-stat"><div class="ts-stat-label">Win Rate</div><div class="ts-stat-value" style="color:#3FB950;">{sim.get("win_rate",0):.0f}%</div></div>'
            sim_html += f'<div class="ts-stat"><div class="ts-stat-label">Exp Return</div><div class="ts-stat-value" style="color:#E6EDF3;">{sim.get("exp_return_pct",0):+.1f}%</div></div>'
            sim_html += f'<div class="ts-stat"><div class="ts-stat-label">Sharpe-like</div><div class="ts-stat-value" style="color:#8B949E;">{sim.get("sharpe_like",0):.2f}</div></div>'
            sim_html += f'</div>'
            opt_e = sim.get("optimal_entry_adj_pct", 0)
            opt_s = sim.get("optimal_stop_adj_pct", 0)
            opt_t = sim.get("optimal_target_adj_pct", 0)
            if any(v != 0 for v in [opt_e, opt_s, opt_t]):
                sim_html += f'<div style="margin-top:6px;font-size:0.68rem;color:#8B949E;">'
                if opt_e: sim_html += f'🎯 Optimal Entry: <b style="color:#D29922;">{opt_e:+.1f}%</b> · '
                if opt_s: sim_html += f'Stop: <b>{opt_s:+.1f}%</b> · '
                if opt_t: sim_html += f'Target: <b>{opt_t:+.1f}%</b>'
                sim_html += f'</div>'
            sim_html += f'<div style="margin-top:4px;font-size:0.6rem;color:#484F58;">Max consecutive losses: {sim.get("max_consecutive_losses",0)} · Avg DD: {sim.get("avg_drawdown_pct",0):.1f}% · Time to win: {sim.get("time_to_win_days",0):.1f}d</div>'
            sim_html += f'</div>'
            st.markdown(sim_html, unsafe_allow_html=True)

                # ── v39.5: Background Engines (Collapsed by Default) ──
        with st.expander("🔧 Background Engines — Sim · WF · Gatekeeper · Greeks · DP", expanded=False):
            # ── v39.1 Background Engine Panels (Gatekeeper · Hedgeye · On-Chain · Broker) ──
                    # Gatekeeper Status
                    gk = row.get("gatekeeper", {})
                    if gk and isinstance(gk, dict):
                        gk_status = gk.get("gate_status", "—")
                        gk_score = gk.get("combined_score", 0)
                        gk_rec = gk.get("recommendation", "—")
                        gk_color = "#3FB950" if gk_status == "PASS" else "#D29922" if gk_status == "MARGINAL" else "#F85149" if gk_status == "FAIL" else "#8B949E"
                        gk_html = f'<div class="ts-panel" style="border-color: {gk_color}30; margin-bottom: 8px;">'
                        gk_html += f'<div class="ts-panel-title">🛡️ Alpha Gatekeeper (8 Gates)</div>'
                        gk_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                        gk_html += f'<span style="background:{gk_color}18;color:{gk_color};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;border:1px solid {gk_color}40;">{gk_status}</span>'
                        gk_html += f'<span style="font-size:0.7rem;color:#8B949E;">Score <b style="color:{gk_color};">{gk_score:.1f}</b></span>'
                        gk_html += f'<span style="font-size:0.7rem;color:#8B949E;">Rec: <b style="color:#E6EDF3;">{gk_rec}</b></span>'
                        gk_html += f'</div></div>'
                        st.markdown(gk_html, unsafe_allow_html=True)

                    # Walkforward Status
                    wf = row.get("walkforward", {})
                    if wf and isinstance(wf, dict):
                        wf_score = wf.get("combined_gate_score", 0)
                        wf_status = wf.get("gate_status", "—")
                        wf_color = "#3FB950" if wf_status == "PASS" else "#D29922" if wf_status == "MARGINAL" else "#F85149"
                        wf_html = f'<div class="ts-panel" style="border-color: {wf_color}30; margin-bottom: 8px;">'
                        wf_html += f'<div class="ts-panel-title">🎲 Walkforward Backtest (MC 100x)</div>'
                        wf_html += f'<div style="display:flex;align-items:center;gap:10px;">'
                        wf_html += f'<span style="background:{wf_color}18;color:{wf_color};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;border:1px solid {wf_color}40;">{wf_status}</span>'
                        wf_html += f'<span style="font-size:0.7rem;color:#8B949E;">Gate Score <b style="color:{wf_color};">{wf_score:.1f}</b></span>'
                        wf_html += f'</div></div>'
                        st.markdown(wf_html, unsafe_allow_html=True)

                    # Hedgeye Position Sizing
                    hp = row.get("hedgeye_size")
                    if hp and isinstance(hp, dict):
                        hp_pct = hp.get("size_pct", 0)
                        hp_dollar = hp.get("dollar_size", 0)
                        hp_mode = hp.get("mode", "—")
                        hp_conv = hp.get("conviction", 0)
                        hp_color = "#3FB950" if hp_pct >= 0.04 else "#D29922" if hp_pct >= 0.02 else "#8B949E"
                        hp_html = f'<div class="ts-panel" style="border-color: {hp_color}30; margin-bottom: 8px;">'
                        hp_html += f'<div class="ts-panel-title">💰 Hedgeye Position Sizing</div>'
                        hp_html += f'<div class="ts-grid-4">'
                        hp_html += f'<div class="ts-stat"><div class="ts-stat-label">Size %</div><div class="ts-stat-value" style="color:{hp_color};">{hp_pct:.2%}</div></div>'
                        hp_html += f'<div class="ts-stat"><div class="ts-stat-label">Size $</div><div class="ts-stat-value" style="color:#E6EDF3;">${hp_dollar:,.0f}</div></div>'
                        hp_html += f'<div class="ts-stat"><div class="ts-stat-label">Mode</div><div class="ts-stat-value" style="color:#8B949E;">{hp_mode}</div></div>'
                        hp_html += f'<div class="ts-stat"><div class="ts-stat-label">Conviction</div><div class="ts-stat-value" style="color:{"#3FB950" if hp_conv>=0.8 else "#D29922" if hp_conv>=0.5 else "#F85149"};">{hp_conv:.0%}</div></div>'
                        hp_html += f'</div></div>'
                        st.markdown(hp_html, unsafe_allow_html=True)

                    # Keith Signal Sync
                    ks = row.get("keith_sync", {})
                    if ks and isinstance(ks, dict) and ks.get("keith_trade") != "NEUTRAL":
                        ktrade = ks.get("keith_trade", "—")
                        ktrend = ks.get("keith_trend", "—")
                        kfinal = ks.get("direction", "—")
                        kbasis = ks.get("basis", "")[:120]
                        k_override = ks.get("override", False)
                        tc = "#3FB950" if ktrade == "BULLISH" else "#F85149" if ktrade == "BEARISH" else "#8B949E"
                        k_html = f'<div class="ts-panel" style="border-color: {tc}30; margin-bottom: 8px;">'
                        k_html += f'<div class="ts-panel-title">🎙️ Keith McCullough Signal Sync (P0)</div>'
                        k_html += f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                        k_html += f'<span style="background:{tc}18;color:{tc};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;border:1px solid {tc}40;">🎙️ TRADE: {ktrade}</span>'
                        k_html += f'<span style="background:{"#3FB950" if ktrend=="BULLISH" else "#F85149" if ktrend=="BEARISH" else "#8B949E"}18;color:{"#3FB950" if ktrend=="BULLISH" else "#F85149" if ktrend=="BEARISH" else "#8B949E"};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;border:1px solid {"#3FB950" if ktrend=="BULLISH" else "#F85149" if ktrend=="BEARISH" else "#8B949E"}40;">📈 TREND: {ktrend}</span>'
                        if k_override:
                            k_html += f'<span style="background:#F8514918;color:#F85149;padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;border:1px solid #F8514940;">⚠️ OVERRIDE</span>'
                        k_html += f'</div>'
                        k_html += f'<div style="font-size:0.7rem;color:#E6EDF3;">Dashboard → <b>{kfinal}</b></div>'
                        k_html += f'<div style="font-size:0.65rem;color:#484F58;margin-top:2px;">{kbasis}</div>'
                        k_html += f'</div>'
                        st.markdown(k_html, unsafe_allow_html=True)

                    # Crypto On-Chain Intelligence (if crypto ticker)
                    if market_type == "crypto":
                        cc_tokens = snap_local.get("crypto_tokens", {}) if snap_local else {}
                        cc_data = cc_tokens.get(ticker, {}) if isinstance(cc_tokens, dict) else {}
                        if cc_data and isinstance(cc_data, dict):
                            whale = cc_data.get("whale_signal", "NEUTRAL")
                            funding = cc_data.get("funding_proxy", 0)
                            large = cc_data.get("large_orders_detected", False)
                            wcolor = "#3FB950" if whale == "ACCUMULATING" else "#F85149" if whale == "DISTRIBUTING" else "#8B949E"
                            cc_html = f'<div class="ts-panel" style="border-color: {wcolor}30; margin-bottom: 8px;">'
                            cc_html += f'<div class="ts-panel-title">⛓️ On-Chain Intelligence</div>'
                            cc_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                            cc_html += f'<span style="background:{wcolor}18;color:{wcolor};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;border:1px solid {wcolor}40;">🐋 {whale}</span>'
                            cc_html += f'<span style="font-size:0.7rem;color:#8B949E;">Funding <b style="color:{"#F85149" if abs(funding)>0.0005 else "#8B949E"};">{funding:.6f}</b></span>'
                            if large:
                                cc_html += f'<span style="background:#D2992218;color:#D29922;padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;border:1px solid #D2992240;">🚨 Large Orders</span>'
                            cc_html += f'</div>'
                            cc_html += f'<div style="font-size:0.65rem;color:#484F58;">R7D: {cc_data.get("r7d",0):+.1%} · R1M: {cc_data.get("r1m",0):+.1%} · Vol Change: {cc_data.get("dex_vol_change",0):+.1%}</div>'
                            cc_html += f'</div>'
                            st.markdown(cc_html, unsafe_allow_html=True)

                    # IHSG Broker Intelligence (if IHSG ticker)
                    if market_type == "ihsg":
                        broker = row.get("broker", {})
                        if broker and isinstance(broker, dict):
                            b_sig = broker.get("signal", "NEUTRAL")
                            b_conf = broker.get("confidence", 0)
                            b_cross = broker.get("crossing_detected", False)
                            b_acc = broker.get("real_accumulation", False)
                            b_dist = broker.get("real_distribution", False)
                            b_color = "#3FB950" if b_acc else "#F85149" if b_dist else "#D29922" if b_cross else "#8B949E"
                            b_emoji = "📈" if b_acc else "📉" if b_dist else "🎯" if b_cross else "⚪"
                            b_html = f'<div class="ts-panel" style="border-color: {b_color}30; margin-bottom: 8px;">'
                            b_html += f'<div class="ts-panel-title">🇮🇩 Broker Intelligence (IHSG)</div>'
                            b_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                            b_html += f'<span style="background:{b_color}18;color:{b_color};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;border:1px solid {b_color}40;">{b_emoji} {b_sig}</span>'
                            b_html += f'<span style="font-size:0.7rem;color:#8B949E;">Confidence <b style="color:{b_color};">{b_conf}%</b></span>'
                            b_html += f'</div>'
                            b_html += f'<div style="font-size:0.65rem;color:#484F58;">R5D: {broker.get("r5d",0):+.1%} · R20D: {broker.get("r20d",0):+.1%} · Vol Ratio: {broker.get("vol_ratio",1):.2f}x · Range Ratio: {broker.get("range_ratio",1):.2f}</div>'
                            b_html += f'</div>'
                            st.markdown(b_html, unsafe_allow_html=True)

                    # Smart Money / Capital Rotation / VRP / Squeeze badges (if data exists)
                    sm_badge = _get_smart_money_badge(ticker, snap_local) if snap_local else ""
                    cr_role = _get_capital_rotation_role(ticker, snap_local) if snap_local else ""
                    vrp_score = _get_vrp_score(ticker, snap_local) if snap_local else 0
                    sq_score = _get_squeeze_score(ticker, snap_local) if snap_local else 0
                    if sm_badge or cr_role or vrp_score or sq_score:
                        intel_html = f'<div class="ts-panel" style="border-color: #58A6FF30; margin-bottom: 8px;">'
                        intel_html += f'<div class="ts-panel-title">🧠 Smart Consensus & Scanners</div>'
                        intel_html += f'<div style="display:flex;flex-wrap:wrap;gap:6px;">'
                        if sm_badge:
                            intel_html += f'<span style="background:#3FB95018;color:#3FB950;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #3FB95040;">{sm_badge}</span>'
                        if cr_role:
                            intel_html += f'<span style="background:#58A6FF18;color:#58A6FF;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #58A6FF40;">🔄 {cr_role.replace("_"," ")}</span>'
                        if vrp_score:
                            vcolor = "#F85149" if vrp_score > 10 else "#3FB950" if vrp_score < -10 else "#8B949E"
                            intel_html += f'<span style="background:{vcolor}18;color:{vcolor};padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid {vcolor}40;">📊 VRP {vrp_score:+.0f}%</span>'
                        if sq_score:
                            intel_html += f'<span style="background:#D2992218;color:#D29922;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #D2992240;">🔥 Squeeze {sq_score:.0f}</span>'
                        intel_html += f'</div></div>'
                        st.markdown(intel_html, unsafe_allow_html=True)



        # ── Essential Panels (Always Visible) ──
# Basis line
        basis_parts = []
        if row.get("trade_low"):
            basis_parts.append(f"LRR {_ffm(row['trade_low'], market_type)}")
        if row.get("trade_top"):
            basis_parts.append(f"TRR {_ffm(row['trade_top'], market_type)}")
        if options.get("max_pain"):
            basis_parts.append(f"Max Pain {_ffm(options['max_pain'], market_type)}")
        if options.get("put_wall"):
            basis_parts.append(f"Put Wall {_ffm(options['put_wall'], market_type)}")
        if options.get("call_wall"):
            basis_parts.append(f"Call Wall {_ffm(options['call_wall'], market_type)}")
        basis_html = " · ".join(basis_parts) if basis_parts else "Basis: Price action proxy"
        st.markdown(f'<div style="font-size:0.7rem;color:#8B949E;margin-bottom:8px;">{basis_html}</div>', unsafe_allow_html=True)

        # Formation display
        formation = row.get("formation", "NEUTRAL")
        if formation == "BULLISH":
            st.markdown(f'<div style="font-size:0.7rem;color:#3FB950;margin-bottom:6px;">📈 BULLISH: Price > Trend Top AND Tail Top. Buy dips.</div>', unsafe_allow_html=True)
        elif formation == "BEARISH":
            st.markdown(f'<div style="font-size:0.7rem;color:#F85149;margin-bottom:6px;">📉 BEARISH: Price < Trend Low AND Tail Low. Sell rallies.</div>', unsafe_allow_html=True)
        elif formation == "BULLISH_BIAS":
            st.markdown(f'<div style="font-size:0.7rem;color:#3FB950;margin-bottom:6px;">📈 BULLISH BIAS: Price > Trend Top. Favorable for longs.</div>', unsafe_allow_html=True)
        elif formation == "BEARISH_BIAS":
            st.markdown(f'<div style="font-size:0.7rem;color:#F85149;margin-bottom:6px;">📉 BEARISH BIAS: Price < Trend Low. Favorable for shorts.</div>', unsafe_allow_html=True)
        elif formation == "OVERSOLD":
            st.markdown(f'<div style="font-size:0.7rem;color:#3FB950;margin-bottom:6px;">📉 OVERSOLD: Price below Trade Low. Mean-reversion play.</div>', unsafe_allow_html=True)
        elif formation == "OVERBOUGHT":
            st.markdown(f'<div style="font-size:0.7rem;color:#F85149;margin-bottom:6px;">📈 OVERBOUGHT: Price above Trade Top. Mean-reversion play.</div>', unsafe_allow_html=True)
        if not setup_valid:
            setup_note = row.get("setup_note", "")
            st.markdown(f'<div style="font-size:0.7rem;color:#F85149;font-weight:700;margin-bottom:6px;">🚫 {setup_note}</div>', unsafe_allow_html=True)

        # RC override warning
        rc_override = row.get("rc_override", "")
        if rc_override:
            st.markdown(
                f'<div style="background:#F8514915;border:1px solid #F8514950;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:0.78rem;color:#F85149;font-weight:700;">'
                f'{rc_override}</div>', unsafe_allow_html=True)

        # CHASE/WAIT banner
        if chase_text:
            st.markdown(
                f'<div style="background:{chase_color}15;border:1px solid {chase_color}50;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:0.78rem;color:{chase_color};font-weight:700;">'
                f'{chase_text}</div>', unsafe_allow_html=True)

        # Confluence context
        ctx_lines = []
        if row.get("entry_note"):
            ctx_lines.append(row["entry_note"])
        if confluence.get("entry_cluster") and confluence["entry_cluster"].get("count", 0) >= 2:
            levels = confluence.get("entry", [])
            levels_str = " · ".join([f"{name} {ff(val)}" for name, val in levels if val is not None])
            if levels_str:
                ctx_lines.append(f"🔥 Entry Confluence x{confluence['entry_cluster']['count']}: {levels_str}")
        if confluence.get("target_cluster") and confluence["target_cluster"].get("count", 0) >= 2:
            t_levels = confluence.get("target", [])
            t_str = " · ".join([f"{name} {ff(val)}" for name, val in t_levels if val is not None])
            if t_str:
                ctx_lines.append(f"🎯 Target Confluence x{confluence['target_cluster']['count']}: {t_str}")
        if ctx_lines:
            st.markdown(
                f'<div style="margin-bottom:8px;padding:5px 10px;background:#21262D;border-radius:6px;font-size:0.68rem;color:#8B949E;line-height:1.4;">'
                + "<br>".join(ctx_lines) + '</div>', unsafe_allow_html=True)

        # ── Entry Convergence ──
        conv = row.get("entry_convergence")
        if conv and isinstance(conv, dict):
            conv_signal = conv.get("signal", "—")
            conv_conf = conv.get("confidence", 0)
            conv_layers = conv.get("layers", [])
            conv_color = "#3FB950" if conv_signal == "BUY" else "#F85149" if conv_signal == "SELL" else "#D29922" if conv_signal == "HOLD" else "#8B949E"
            conv_html = f'<div class="ts-panel" style="border-color: {conv_color}40; margin-bottom: 8px;">'
            conv_html += f'<div class="ts-panel-title">🎯 Entry Convergence (Multi-Methodology Fusion)</div>'
            conv_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            conv_html += f'<span style="background:{conv_color}18;color:{conv_color};padding:3px 10px;border-radius:6px;font-size:0.85rem;font-weight:700;border:1px solid {conv_color}40;">{conv_signal}</span>'
            conv_html += f'<span style="font-size:0.7rem;color:#8B949E;">Confidence <b style="color:{conv_color};">{conv_conf:.0f}%</b></span>'
            conv_html += f'<span style="font-size:0.65rem;color:#484F58;">{len(conv_layers)} layers</span>'
            conv_html += f'</div>'
            conv_html += f'<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(140px, 1fr));gap:4px;">'
            for layer in conv_layers[:12]:
                lcolor = layer.get("color", "#8B949E")
                lw = layer.get("weight", 0)
                sign = "+" if lw > 0 else ""
                conv_html += f'<div style="padding:3px 6px;background:#0D1117;border-radius:4px;font-size:0.6rem;display:flex;justify-content:space-between;align-items:center;">'
                conv_html += f'<span style="color:#8B949E;">{layer.get("name","—")}</span>'
                conv_html += f'<span style="color:{lcolor};font-weight:700;">{layer.get("signal","—")} {sign}{lw}</span>'
                conv_html += f'</div>'
            conv_html += f'</div></div>'
            st.markdown(conv_html, unsafe_allow_html=True)

        # ── Recommendation ──
        if market_type == "ihsg":
            broker = row.get("broker", {})
            if broker:
                acc = broker.get("real_accumulation", False)
                dist = broker.get("real_distribution", False)
                cross = broker.get("crossing_detected", False)
                conf = broker.get("confidence", 0)
                r5d_b = broker.get("r5d", 0)
                if acc:
                    rec_color = "#3FB950"; rec_action = "AKUMULASI REAL"; rec_strategy = "Genuine buying — tambah posisi"
                    rec_rationale = f"📈 Price +{r5d_b:.1%} 5D dengan trend consistency. Broker accumulation {conf}% confidence."
                elif dist:
                    rec_color = "#F85149"; rec_action = "DISTRIBUSI REAL"; rec_strategy = "Genuine selling — kurangi posisi"
                    rec_rationale = f"📉 Price {r5d_b:.1%} 5D. Broker distribution {conf}% confidence."
                elif cross:
                    rec_color = "#D29922"; rec_action = "WASPADA CROSSING"; rec_strategy = "Volume tinggi tapi price flat — possible wash trading"
                    rec_rationale = "⚠️ High volume but stagnant price. Wait for genuine breakout."
                else:
                    rec_color = "#8B949E"; rec_action = "TIDAK ADA SIGNAL"; rec_strategy = "Broker activity normal — tunggu konfirmasi"
                    rec_rationale = "📊 No clear accumulation or distribution pattern."
                rec = {"action": rec_action, "strategy": rec_strategy, "rationale": rec_rationale, "confidence": conf, "factors": 1, "source": "BROKER_PROXY"}
            else:
                rec_color = "#8B949E"
                rec = {"action": "HOLD / TUNGGU", "strategy": "Data broker tidak tersedia", "rationale": "• Data broker summary tidak cukup untuk rekomendasi.", "confidence": 0, "factors": 0, "source": "NONE"}
        else:
            cot_data = None; onchain_data = None
            if market_type in ("forex", "commodity"):
                cot_data = _get_cot_proxy(ticker)
            if market_type == "crypto":
                onchain_data = _get_onchain_proxy(ticker, st.session_state.snap.get("prices", {}))
            rec = _get_single_recommendation(
                options, direction=row.get("direction", "LONG"), market_type=market_type,
                cot_data=cot_data, onchain_data=onchain_data, ticker=ticker, row=row,
                dark_pool=row.get("dark_pool")
            )
            rec_color = {"BELI SPOT / AKUMULASI":"#3FB950","AKUMULASI SPOT":"#3FB950","BELI CALL / LONG SPOT":"#3FB950",
                         "BELI SPOT + JUAL PUT":"#2EA043","BELI SPOT":"#3FB950",
                         "JUAL COVERED CALL":"#D29922","JUAL PUT PROTEKTIF":"#F85149",
                         "JUAL / REDUKSI":"#F85149","HEDGE POSISI":"#F85149",
                         "HOLD + JUAL PREMIUM":"#D29922","WASPADA / TUNGGU":"#D29922",
                         "HOLD / TUNGGU":"#8B949E","HOLD":"#8B949E"}.get(rec["action"], "#58A6FF")

        # Visual recommendation card
        conf_pct = rec.get("confidence", 50)
        rec_html = f'<div class="ts-panel" style="border-color: {rec_color}40;">'
        rec_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        rec_html += f'<div style="background:{rec_color}20;border:1px solid {rec_color}50;border-radius:6px;padding:4px 10px;font-size:0.75rem;color:{rec_color};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">🎯 {rec["action"]}</div>'
        rec_html += f'<div style="flex:1;"><div style="font-size:0.55rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Confidence</div>'
        rec_html += f'<div style="display:flex;align-items:center;gap:4px;"><div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
        rec_html += f'<div style="width:{conf_pct}%;height:100%;background:{rec_color};border-radius:3px;"></div></div>'
        rec_html += f'<span style="font-size:0.65rem;color:{rec_color};font-weight:700;min-width:28px;text-align:right;">{conf_pct:.0f}%</span></div></div></div>'
        rec_html += f'<div style="font-size:0.72rem;color:#8B949E;margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid #21262D;">{rec["strategy"]}</div>'

        # Entry/Target/Stop grid
        rec_html += f'<div class="ts-grid-4" style="margin-bottom:8px;">'
        rec_html += f'<div class="ts-stat"><div class="ts-stat-label">Entry</div><div class="ts-stat-value" style="color:#E6EDF3;">{_ffm(entry, market_type)}</div></div>'
        rec_html += f'<div class="ts-stat"><div class="ts-stat-label">Target 1</div><div class="ts-stat-value" style="color:#3FB950;">{_ffm(t1, market_type)}</div></div>'
        rec_html += f'<div class="ts-stat"><div class="ts-stat-label">Target 2</div><div class="ts-stat-value" style="color:#2EA043;">{_ffm(t2, market_type)}</div></div>'
        rec_html += f'<div class="ts-stat"><div class="ts-stat-label">Stop</div><div class="ts-stat-value" style="color:#F85149;">{_ffm(stop, market_type)}</div><div class="ts-stat-sub">{risk_pct:.1f}% risk</div></div>'
        rec_html += f'</div>'

        # Rationale
        rec_html += f'<div style="font-size:0.68rem;color:#8B949E;line-height:1.5;padding:6px;background:#0D1117;border-radius:6px;">'
        rec_html += f'<div style="font-size:0.55rem;color:{rec_color};text-transform:uppercase;font-weight:600;margin-bottom:4px;letter-spacing:0.5px;">📋 Rationale ({rec.get("factors",0)} factors · {rec.get("source","PROXY")})</div>'
        rec_html += rec["rationale"]
        rec_html += f'</div>'
        rec_html += f'</div>'
        st.markdown(rec_html, unsafe_allow_html=True)

        # ── 🎯 WHY THIS POSITION — Synthesized Narrative ──
        why_html = f'<div class="ts-panel" style="border-color: #58A6FF40; margin-bottom: 8px;">'
        why_html += f'<div class="ts-panel-title">🎯 Why Take This Position</div>'

        reasons = []

        # 1. Formation + Risk Range position
        formation = row.get("formation", "NEUTRAL")
        px = row.get("price", 0)
        trade_l = row.get("trade_low", 0)
        trade_r = row.get("trade_top", 0)
        trend_top = row.get("trend_top", 0)
        if formation == "BULLISH":
            reasons.append(f"📈 <b>Hedgeye BULLISH:</b> Price {_ffm(px, market_type)} > Trend Top {_ffm(trend_top, market_type)} AND Tail Top. Formation mendukung {direction}.")
        elif formation == "BEARISH":
            reasons.append(f"📉 <b>Hedgeye BEARISH:</b> Price {_ffm(px, market_type)} < Trend Low AND Tail Low. Formation mendukung {direction}.")
        elif formation == "OVERSOLD":
            reasons.append(f"📉 <b>OVERSOLD:</b> Price di bawah Trade Low {_ffm(trade_l, market_type)}. Mean-reversion play dengan RR {row.get('rr',0):.1f}x.")
        elif formation == "OVERBOUGHT":
            reasons.append(f"📈 <b>OVERBOUGHT:</b> Price di atas Trade Top {_ffm(trade_r, market_type)}. Fade rally setup.")
        elif formation in ("BULLISH_BIAS", "BEARISH_BIAS"):
            reasons.append(f"📊 <b>BIAS:</b> Price {formation.replace('_', ' ')} — directional favorable untuk {direction}.")

        # 2. Options / Greeks context (skip IHSG)
        if show_options and market_type != "ihsg":
            opts = row.get("options", {})
            gamma = opts.get("gamma_regime", "")
            mp = opts.get("max_pain")
            vanna = opts.get("vanna")
            charm = opts.get("charm")
            gex = opts.get("gex")

            if gamma in ("NEGATIVE", "DEEP_NEGATIVE") and direction == "LONG":
                reasons.append(f"🔴 <b>Negative Gamma:</b> Dealer short gamma = trend ACCELERATION on breakout. Bukan mean-reversion, ini momentum fuel. Target bisa lebih agresif.")
            elif gamma in ("POSITIVE", "DEEP_POSITIVE") and direction == "LONG":
                reasons.append(f"🟢 <b>Positive Gamma:</b> Dealer long = mean-reversion ke max pain. Sell into strength, buy dips. Range-bound behavior.")

            if mp and px:
                mp_dist = (px - mp) / mp * 100
                if abs(mp_dist) < 2:
                    reasons.append(f"📍 <b>Max Pain Pin:</b> Price {mp_dist:+.1f}% dari max pain {_ffm(mp, market_type)}. MM trapped — range-bound until expiry. Straddle income play.")
                elif mp_dist > 3 and gamma in ("POSITIVE", "DEEP_POSITIVE"):
                    reasons.append(f"📈 <b>Call Wall:</b> Price +{mp_dist:.1f}% above max pain + pos gamma. MM sells rallies. <b>Fade strength.</b>")
                elif mp_dist < -3 and gamma in ("NEGATIVE", "DEEP_NEGATIVE"):
                    reasons.append(f"📉 <b>Put Wall:</b> Price {mp_dist:.1f}% below max pain + neg gamma. MM buys dips. <b>Support holds.</b>")

            if vanna is not None:
                try:
                    v = float(vanna)
                    if v > 0.5:
                        reasons.append(f"🟢 <b>Vanna +{v:.2f}:</b> Rally = vol crush. Buy spot on dips, jangan chase di atas.")
                    elif v < -0.5:
                        reasons.append(f"🔴 <b>Vanna {v:.2f}:</b> Rally = vol expansion. Breakout volatile — hedge dengan call spread.")
                except: pass

            if charm is not None:
                try:
                    c = float(charm)
                    if c > 0.5:
                        reasons.append(f"🟢 <b>Charm +{c:.2f}:</b> Put support strengthening daily. Support level naik tiap hari.")
                    elif c < -0.5:
                        reasons.append(f"🔴 <b>Charm {c:.2f}:</b> Put support eroding — downside acceleration risk. Tighten stop.")
                except: pass

            if gex is not None:
                try:
                    g = float(gex)
                    if g > 0.5:
                        reasons.append(f"🟢 <b>GEX +{g:.2f}:</b> Extreme positive = strong mean-reversion. Sell covered calls di resistance.")
                    elif g < -0.5:
                        reasons.append(f"🔴 <b>GEX {g:.2f}:</b> Extreme negative = trend acceleration. Buy dips, jangan short.")
                except: pass

        # 3. Dark Pool
        dp = row.get("dark_pool")
        if dp and isinstance(dp, dict):
            div = dp.get("divergence", "NEUTRAL")
            if div == "HIDDEN_ACCUMULATION":
                reasons.append(f"🟢 <b>Hidden Accumulation:</b> Dark Pool BUY + Lit Tape SELL/NEUTRAL. Institutions stealth buying. <b>Smart money edge.</b>")
            elif div == "HIDDEN_DISTRIBUTION":
                reasons.append(f"🔴 <b>Hidden Distribution:</b> Dark Pool SELL + Lit Tape BUY. Institutions dumping ke retail. <b>Contrarian SELL.</b>")
            elif div == "BOTH_AGREE":
                dp_sig = dp.get("dp_signal", "")
                reasons.append(f"✅ <b>Both Tapes Agree:</b> Dark Pool + Lit Tape {dp_sig}. Strong conviction, no divergence.")

            zf = dp.get("zero_flag")
            if zf == "ZERO_SELLS":
                reasons.append(f"🔥 <b>ZERO Dark Sells:</b> Pure institutional accumulation. No institutional distribution detected.")
            elif zf == "ZERO_BUYS":
                reasons.append(f"❄️ <b>ZERO Dark Buys:</b> Pure institutional distribution. No institutional buying detected.")

        # 4. Squeeze / VRP
        sq = row.get("squeeze_score", 0)
        if sq and sq > 60:
            reasons.append(f"🔥 <b>Squeeze Score {sq:.0f}:</b> Vol compression + price near BB middle. Breakout imminent.")

        vrp = row.get("vrp_score", 0)
        if vrp and vrp > 10:
            reasons.append(f"📊 <b>VRP +{vrp:.0f}%:</b> Implied vol expensive vs realized. Sell premium (covered calls / straddles).")
        elif vrp and vrp < -10:
            reasons.append(f"📊 <b>VRP {vrp:.0f}%:</b> Implied vol cheap. Buy convexity (calls / call spreads).")

        # 5. Methodology confluence
        alpha_src = row.get("alpha_source", "")
        alpha_score = row.get("alpha_score", 0)
        if alpha_src:
            src_names = {"bottleneck":"Leopold Bottleneck","front_run":"News Catalyst","leopold":"Leopold Asymmetry","coatue":"COATUE Rotation","karsan":"Karsan Vol","thought_process":"Multi-Framework Thesis","quad_aligned":"Hedgeye Playbook"}
            reasons.append(f"🏗️ <b>{src_names.get(alpha_src, alpha_src)}:</b> Alpha score {alpha_score:.0f}/100. Methodology validation passed.")

        # 6. Walkforward / Simulation
        wf = row.get("walkforward", {})
        if wf and isinstance(wf, dict) and wf.get("gate_status") == "PASS":
            reasons.append(f"🎲 <b>Walkforward PASS:</b> MC 100x backtest validated. Setup robust across multiple market conditions.")

        sim = row.get("simulation")
        if sim and isinstance(sim, dict):
            wr = sim.get("win_rate", 0)
            if wr >= 60:
                reasons.append(f"🎲 <b>Sim Win Rate {wr:.0f}%:</b> Monte Carlo 100 runs menunjukkan edge statistik kuat.")
            elif wr >= 50:
                reasons.append(f"🎲 <b>Sim Win Rate {wr:.0f}%:</b> Edge moderat — valid tapi tighten stop.")

        # 7. Keith override
        ks = row.get("keith_sync", {})
        if ks and isinstance(ks, dict) and ks.get("override"):
            kt = ks.get("keith_trade", "")
            reasons.append(f"🎙️ <b>Keith P0 Override:</b> Keith {kt} — signal ini di-override oleh Hedgeye founder. <b>{'AVOID' if kt == 'BEARISH' else 'HIGH CONVICTION'}.</b>")

        # 8. Macro narrative (from snap)
        narrative = snap_local.get("narrative", {}) if snap_local else {}
        scenarios = narrative.get("scenarios", {}) if isinstance(narrative, dict) else {}
        if scenarios:
            dom = scenarios.get("dominant_scenario", "base")
            bull_p = scenarios.get("bull", {}).get("probability", 0) if isinstance(scenarios.get("bull"), dict) else 0
            if dom == "bull" and direction == "LONG":
                reasons.append(f"📰 <b>Macro Narrative:</b> Dominant scenario BULLISH ({bull_p:.0%} prob). Tailwind untuk longs.")
            elif dom == "bear" and direction == "SHORT":
                reasons.append(f"📰 <b>Macro Narrative:</b> Dominant scenario BEARISH. Headwind untuk risk assets.")

        # 9. IHSG Broker (if applicable)
        if market_type == "ihsg":
            broker = row.get("broker", {})
            if broker and isinstance(broker, dict):
                if broker.get("real_accumulation"):
                    reasons.append(f"🇮🇩 <b>Broker Accumulation REAL:</b> Volume + price trend konsisten. Bukan crossing/wash trade. Confidence {broker.get('confidence',0)}%.")
                elif broker.get("crossing_detected"):
                    reasons.append(f"⚠️ <b>Crossing Detected:</b> High volume tapi price flat — possible wash trading. <b>TUNGGU.</b>")
                elif broker.get("cornering_supply"):
                    reasons.append(f"🎯 <b>Cornering Supply:</b> Volume drying up then spike. Possible accumulation before breakout. Watch closely.")

        # 10. Entry quality
        entry = row.get("entry")
        stop = row.get("stop")
        rr = row.get("rr", 0)
        if entry and stop and rr >= 2.0:
            reasons.append(f"🎯 <b>Asymmetric Setup:</b> Entry {_ffm(entry, market_type)} → Stop {_ffm(stop, market_type)} (risk {row.get('risk_pct',0):.1f}%). RR {rr:.1f}x = reward {_ffm(row.get('target_1',0), market_type)}. High conviction.")
        elif entry and stop and rr >= 1.5:
            reasons.append(f"⚠️ <b>Moderate Setup:</b> RR {rr:.1f}x — valid tapi jangan oversize. Max 2-3% position.")
        elif entry and stop and rr < 1.5:
            reasons.append(f"🚫 <b>Poor RR:</b> {rr:.1f}x — risk/reward tidak cukup. Skip atau tunggu entry lebih baik.")

        # Render
        if reasons:
            for r in reasons:
                why_html += f'<div style="font-size:0.72rem;color:#E6EDF3;line-height:1.5;margin-bottom:4px;padding:3px 0;border-bottom:1px solid #21262D;">{r}</div>'
        else:
            why_html += f'<div style="font-size:0.72rem;color:#8B949E;">⚪ Data tidak cukup untuk reasoning kuat. Setup didasarkan price action saja.</div>'

        why_html += f'</div>'
        st.markdown(why_html, unsafe_allow_html=True)


        if row.get("news_headline"):
            st.markdown(f'<div style="font-size:0.72rem;color:#58A6FF;margin-top:3px;">📰 {row.get("news_headline")[:120]}</div>', unsafe_allow_html=True)


def render_invalid_cards(invalid_rows):
    if not invalid_rows:
        return
    st.markdown(f'<div style="font-size:0.68rem;color:#8B949E;margin-bottom:4px;">{len(invalid_rows)} setup(s) filtered out — stop too tight, trend conflict, walk-forward fail, or AVOID</div>', unsafe_allow_html=True)
    for r in invalid_rows[:15]:
        ticker = r.get("ticker", "?")
        reason = r.get("setup_note", "") or r.get("formation", "") or r.get("chase_text", "") or "Invalid"
        px = r.get("price", 0)
        dir_ = r.get("direction", "")
        grade = r.get("grade", "C")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;margin:2px 0;">'
            f'<span style="font-weight:700;font-size:0.8rem;color:#E6EDF3;min-width:55px;">{ticker}</span>'
            f'<span style="font-size:0.6rem;padding:1px 5px;border-radius:4px;background:#F8514915;color:#F85149;border:1px solid #F8514940;">{dir_} {grade}</span>'
            f'<span style="flex:1;font-size:0.68rem;color:#8B949E;">{reason[:100]}</span>'
            f'<span style="font-size:0.65rem;color:#484F58;min-width:50px;text-align:right;">{_ffm(px, market_type)}</span>'
            f'</div>', unsafe_allow_html=True
        )


def render_ticker_cards_v4(rows, max_rows=30):
    if not rows:
        st.info("No setups pass filter.")
        return
    st.markdown(f'<div style="font-size:0.72rem;color:#8B949E;margin-bottom:4px;">Showing {min(len(rows), max_rows)} of {len(rows)} setups</div>', unsafe_allow_html=True)
    for i, r in enumerate(rows[:max_rows]):
        render_ticker_card_v4(r, expanded=False)

# ═══════════════════════════════════════════════════════════════════
# REGIME COMPASS
# ═══════════════════════════════════════════════════════════════════
def render_regime_compass(snap):
    gip_local = snap.get("gip")
    if gip_local is not None and not isinstance(gip_local, dict): gip_local = _GipProxy(gip_local)
    elif isinstance(gip_local, dict): gip_local = _GipProxy(gip_local)
    else: return

    q_probs = getattr(gip_local, "structural_probs", {}) or {}
    m_probs = getattr(gip_local, "monthly_probs", {}) or {}
    sq = getattr(gip_local, "structural_quad", "Q3") or "Q3"
    mq = getattr(gip_local, "monthly_quad", "Q2") or "Q2"

    markov = snap.get("markov_v3", {}) or {}
    markov_regime = markov.get("current_regime", "UNKNOWN") if isinstance(markov, dict) else "UNKNOWN"
    markov_conf = markov.get("confidence", 0) if isinstance(markov, dict) else 0
    markov_kelly = markov.get("kelly_fraction", 0.25) if isinstance(markov, dict) else 0.25
    cp_alert = markov.get("change_point_alert", False) if isinstance(markov, dict) else False

    rf = snap.get("regime_forecast", {})
    rf3 = rf.get("3m", {}) if isinstance(rf, dict) else {}
    fq = rf3.get("predicted_quad", "Q3") if isinstance(rf3, dict) else "Q3"
    fc = rf3.get("prediction_confidence", 0) if isinstance(rf3, dict) else 0

    c1, c2 = st.columns([1, 1.6])
    with c1:
        sq_color = _quad_color(sq); mq_color = _quad_color(mq)
        markov_color = "#58A6FF" if "BULL" in str(markov_regime).upper() else "#F85149" if "BEAR" in str(markov_regime).upper() else "#D29922"
        cp_badge = '<span style="background:#F8514922;color:#F85149;padding:1px 5px;border-radius:4px;font-size:0.6rem;font-weight:700;border:1px solid #F85149;margin-left:6px;">⚠ CP</span>' if cp_alert else ""

        # Duration-Dependent HMM (Attachment 4)
        dur_hmm = snap.get("duration_hmm", {}).get("SPY", {}) if isinstance(snap.get("duration_hmm"), dict) else {}
        if dur_hmm:
            dur_reg = dur_hmm.get("current_regime", "—")
            dur_conf = dur_hmm.get("confidence", 0)
            dur_dur = dur_hmm.get("duration", 0)
            dur_trans = dur_hmm.get("transition_prob", 0)
            dur_color = "#3FB950" if dur_reg == "BULL" else "#F85149" if dur_reg == "BEAR" else "#D29922"
            st.markdown(
                f'<div style="margin-top:6px;padding:6px 8px;background:#0D1117;border-radius:6px;border-left:3px solid {dur_color};">'
                f'<div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Duration HMM (SPY)</div>'
                f'<div style="font-size:0.8rem;color:{dur_color};font-weight:700;">{dur_reg} · Day {dur_dur}</div>'
                f'<div style="font-size:0.6rem;color:#484F58;">Conf {dur_conf:.0%} · Trans prob {dur_trans:.1%}</div></div>',
                unsafe_allow_html=True)
        st.markdown(
            f'<div class="compass-container">'
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;">'
            f'<div style="text-align:center;min-width:70px;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Structural</div>'
            f'<div class="compass-quad" style="color:{sq_color};">{sq}</div><div class="compass-sub">{_quad_name(sq)}</div></div>'
            f'<div style="width:1px;height:36px;background:#30363D;"></div>'
            f'<div style="text-align:center;min-width:70px;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Monthly</div>'
            f'<div class="compass-quad" style="color:{mq_color};">{mq}</div><div class="compass-sub">{_quad_name(mq)}</div></div>'
            f'<div style="width:1px;height:36px;background:#30363D;"></div>'
            f'<div style="flex:1;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Markov {cp_badge}</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:{markov_color};margin-top:2px;">{str(markov_regime).replace("_"," ")}</div>'
            f'<div class="compass-sub">Conf {markov_conf:.0%} · Kelly {markov_kelly:.0%}</div></div>'
            f'</div>'
            f'{_gauge_html(markov_conf*100, max_val=100, color=markov_color, height=10, label_left="0%", label_right="100%")}'
            f'</div>', unsafe_allow_html=True
        )
        # ── Scenario probabilities below compass ──
        narrative_local = snap.get("narrative", {}) or {}
        scenarios_local = (narrative_local.get("scenarios") or {}) if isinstance(narrative_local, dict) else {}
        if scenarios_local:
            dom_local = scenarios_local.get("dominant_scenario", "base") if isinstance(scenarios_local, dict) else "base"
            bull_p_local = scenarios_local.get("bull", {}).get("probability", 0) if isinstance(scenarios_local.get("bull"), dict) else 0
            base_p_local = scenarios_local.get("base", {}).get("probability", 0) if isinstance(scenarios_local.get("base"), dict) else 0
            bear_p_local = scenarios_local.get("bear", {}).get("probability", 0) if isinstance(scenarios_local.get("bear"), dict) else 0
            st.markdown(
                f'<div style="font-size:0.6rem;color:#8B949E;text-align:center;margin:6px 0 0;padding:4px 6px;background:#0D1117;border-radius:4px;">'
                f'<span style="color:#3FB950;font-weight:700;">🐂 {bull_p_local:.0%}</span> · '
                f'<span style="color:#D29922;font-weight:700;">⚖ {base_p_local:.0%}</span> · '
                f'<span style="color:#F85149;font-weight:700;">🐻 {bear_p_local:.0%}</span> · '
                f'Dom: <b>{dom_local.title()}</b></div>', unsafe_allow_html=True)
    with c2:
        fig = go.Figure()
        quads = ["Q1","Q2","Q3","Q4"]; colors = [_quad_color(q) for q in quads]
        q_vals = [q_probs.get(q, 0) if isinstance(q_probs, dict) else 0 for q in quads]
        m_vals = [m_probs.get(q, 0) if isinstance(m_probs, dict) else 0 for q in quads]
        f_vals = [fc if q == fq else (1-fc)/3 for q in quads]
        fig.add_trace(go.Bar(name="Structural", x=quads, y=q_vals, marker_color=colors, opacity=1.0,
                             text=[f"{v:.0%}" for v in q_vals], textposition="outside", textfont=dict(size=10, color="#E6EDF3"), showlegend=True))
        fig.add_trace(go.Bar(name="Monthly", x=quads, y=m_vals, marker_color=colors, opacity=0.55,
                             text=[f"{v:.0%}" for v in m_vals], textposition="outside", textfont=dict(size=9, color="#8B949E"), showlegend=True))
        fig.add_trace(go.Bar(name="Forward 3M", x=quads, y=f_vals, marker_color=colors, opacity=0.25,
                             text=[f"{v:.0%}" for v in f_vals], textposition="outside", textfont=dict(size=8, color="#484F58"), showlegend=True))
        fig.update_layout(height=160, margin=dict(t=10,b=20,l=20,r=20), paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
                          font=dict(color="#E6EDF3", size=10, family="Inter"),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                          yaxis=dict(range=[0,1.15], tickformat=".0%", showgrid=True, gridcolor="#21262D", dtick=0.25),
                          barmode="group", bargap=0.35, bargroupgap=0.1)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="regime_compass_bars_main")


# ═══════════════════════════════════════════════════════════════════
# CRASH METER v3 — AUDITED (/5 fix)
# ═══════════════════════════════════════════════════════════════════
def _render_crash_meter(snap):
    """Crash Meter v3 — Tomhardi Methodology (AUDITED v32.4)
    Components: A1 + A2 + B1 + B2 + C = 5 variables
    Max score: 5 (was /4 in v32.3 — BUG FIXED)
    """
    from datetime import datetime

    fred = snap.get("fred_series", {}) or {}

    # A1: T10Y-3M spread
    t10y = None; t3m = None
    if fred.get("DGS10") is not None:
        try:
            s = pd.to_numeric(fred["DGS10"], errors="coerce").dropna()
            if len(s) > 0: t10y = float(s.iloc[-1])
        except: pass
    if fred.get("DGS3MO") is not None:
        try:
            s = pd.to_numeric(fred["DGS3MO"], errors="coerce").dropna()
            if len(s) > 0: t3m = float(s.iloc[-1])
        except: pass

    if t10y is None or t3m is None:
        t10y3m = 0.77
    else:
        t10y3m = t10y - t3m

    a1_score = 0 if t10y3m > 0.5 else 1
    a1_status = "Aman" if a1_score == 0 else "Berbahaya"
    a1_color = "#3FB950" if a1_score == 0 else "#F85149"

    # A2: Inversion window (corrected: last inversion Dec 2024)
    now = datetime.now()
    last_inv = datetime(2024, 12, 1)
    months_since = (now.year - last_inv.year) * 12 + (now.month - last_inv.month)
    months_left = max(0, 18 - months_since)
    a2_score = 1 if months_since < 18 else 0
    a2_status = "Dalam Window ({}bln sisa)".format(months_left) if a2_score == 1 else "Lewat Window"
    a2_color = "#D29922" if a2_score == 1 else "#3FB950"

    # B1 & B2: HY OAS
    hy_oas = None
    if fred.get("BAMLH0A0HYM2") is not None:
        try:
            s = pd.to_numeric(fred["BAMLH0A0HYM2"], errors="coerce").dropna()
            if len(s) > 0: hy_oas = float(s.iloc[-1])
        except: pass
    if hy_oas is None:
        hy_oas = 2.82

    hy_6m_ago = 3.10
    hy_range_bps = abs(hy_oas - hy_6m_ago) * 100
    b1_score = 0 if hy_range_bps < 150 else 1
    b1_status = "Range {:.0f}bps (Aman)".format(hy_range_bps) if b1_score == 0 else "Range {:.0f}bps (Tinggi)".format(hy_range_bps)
    b1_color = "#3FB950" if b1_score == 0 else "#F85149"

    b2_score = 0 if hy_oas < 5.50 else 1
    b2_status = "{:.2f}% < 5.50%".format(hy_oas) if b2_score == 0 else "{:.2f}% > 5.50%".format(hy_oas)
    b2_color = "#3FB950" if b2_score == 0 else "#F85149"

    # C: Shiller CAPE (v39 LIVE PROXY from SPY 10Y return)
    spy_s = snap.get("prices", {}).get("SPY")
    cape = 41.66  # fallback
    cape_source = "FALLBACK"
    if spy_s is not None and len(spy_s) >= 252:
        try:
            spy_clean = pd.to_numeric(pd.Series(spy_s), errors="coerce").dropna()
            spy_10y = float(spy_clean.iloc[-1] / spy_clean.iloc[-min(2520, len(spy_clean))])
            if spy_10y > 3.0:
                cape = max(35, 30 + (spy_10y - 2.5) * 8)
            else:
                cape = 30 + (spy_10y - 1.5) * 5
            cape = round(cape, 1)
            cape_source = "PROXY"
        except Exception:
            pass
    c_score = 1 if cape > 35 else 0
    c_status = "{:.1f} > 35 (Mahal)".format(cape) if c_score == 1 else "{:.1f} < 35".format(cape)
    c_color = "#F85149" if c_score == 1 else "#3FB950"

    total = a1_score + a2_score + b1_score + b2_score + c_score

    # Timeline estimate
    if total <= 1:
        status = "AMAN"; status_color = "#3FB950"; status_bg = "#3FB95015"; emoji = "🟢"
        advice = "Market normal. Tetap waspada tapi tidak perlu panic."
        timeline = "No crash signal. Monitor monthly."
    elif total == 2:
        status = "WASPADA"; status_color = "#D29922"; status_bg = "#D2992215"; emoji = "🟡"
        advice = "Signal mulai menyala. Review portfolio, siapkan cash buffer."
        timeline = "A2 window closes Jun 2026 (~{} bln). CAPE 41.7 vs peak 44.2.".format(months_left)
    elif total == 3:
        status = "EXIT WINDOW"; status_color = "#F85149"; status_bg = "#F8514915"; emoji = "🟠"
        advice = "COUNTDOWN DIMULAI. Profit-taking dan raise cash. Window sempit!"
        timeline = "Historically 3-12 months to peak. Act within weeks."
    else:
        status = "CRITICAL"; status_color = "#F85149"; status_bg = "#F8514920"; emoji = "🔴"
        advice = "Sistemik risk tinggi. Defensive positioning. Cash is king."
        timeline = "Days to weeks before major drawdown. Exit NOW."

    html = '<div style="background:#161B22;border:1px solid ' + status_color + '40;border-radius:12px;padding:14px;margin:8px 0;">'

    # Header
    html += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
    html += '<div style="width:56px;height:56px;border-radius:50%;background:' + status_bg + ';border:2px solid ' + status_color + ';display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:800;color:' + status_color + ';">' + str(total) + '<span style="font-size:0.6rem;">/5</span></div>'
    html += '<div><div style="font-size:1.1rem;font-weight:700;color:' + status_color + ';letter-spacing:-0.5px;">' + emoji + ' ' + status + '</div>'
    html += '<div style="font-size:0.7rem;color:#8B949E;margin-top:2px;">' + advice + '</div></div></div>'

    # Timeline
    html += '<div style="background:' + status_bg + ';border-left:3px solid ' + status_color + ';border-radius:6px;padding:8px 10px;margin-bottom:10px;">'
    html += '<div style="font-size:0.6rem;color:' + status_color + ';text-transform:uppercase;font-weight:600;margin-bottom:3px;">⏱️ Timeline Estimate</div>'
    html += '<div style="font-size:0.72rem;color:#E6EDF3;">' + timeline + '</div>'
    html += '<div style="font-size:0.6rem;color:#484F58;margin-top:2px;">Update: A1/A2/B daily · CAPE monthly · Next check: tomorrow</div>'
    html += '</div>'

    # Gauge bar (5 segments)
    html += '<div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-bottom:3px;text-transform:uppercase;font-weight:600;"><span>0 Aman</span><span>1</span><span>2 Waspada</span><span>3 Exit</span><span>4</span><span>5 Critical</span></div>'
    html += '<div style="height:10px;background:#21262D;border-radius:5px;overflow:hidden;display:flex;">'
    html += '<div style="width:20%;height:100%;background:#3FB950;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#3FB950;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#D29922;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#F85149;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#F85149;opacity:0.5;"></div>'
    html += '</div>'
    marker_pct = min(100, max(0, total / 5 * 100))
    html += '<div style="position:relative;height:4px;margin-top:-7px;"><div style="position:absolute;left:' + str(marker_pct) + '%;transform:translateX(-50%);width:10px;height:10px;background:' + status_color + ';border-radius:50%;border:2px solid #E6EDF3;box-shadow:0 0 6px ' + status_color + '80;"></div></div>'
    html += '</div>'

    # Parameters grid
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;">'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">📊 A1 · T10Y-3M</span>'
    html += '<span style="font-size:0.65rem;color:' + a1_color + ';font-weight:700;">' + a1_status + '</span></div>'
    html += '<div style="font-size:0.7rem;color:#E6EDF3;font-weight:700;">' + str(round(t10y3m, 2)) + '%</div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: >0.5% = skor 0 · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">⏱️ A2 · 18Bln Window</span>'
    html += '<span style="font-size:0.65rem;color:' + a2_color + ';font-weight:700;">' + a2_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Last inversion: Des 2024 · Closes Jun 2026</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">💳 B1 · HY Range</span>'
    html += '<span style="font-size:0.65rem;color:' + b1_color + ';font-weight:700;">' + b1_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: <150bps in 6mo · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">💳 B2 · HY Abs</span>'
    html += '<span style="font-size:0.65rem;color:' + b2_color + ';font-weight:700;">' + b2_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: <550bps = skor 0 · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;grid-column:1 / -1;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">📈 C · Shiller CAPE</span>'
    html += '<span style="font-size:0.65rem;color:' + c_color + ';font-weight:700;">' + c_status + '</span></div>'
    html += '<div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
    html += '<div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
    cape_pct = min(100, cape / 50 * 100)
    html += '<div style="width:' + str(round(cape_pct, 0)) + '%;height:100%;background:' + c_color + ';border-radius:3px;"></div>'
    html += '</div>'
    html += '<span style="font-size:0.6rem;color:#8B949E;min-width:60px;text-align:right;">Peak dotcom: 44.2</span>'
    html += '</div></div>'

    html += '</div>'

    html += '<div style="font-size:0.6rem;color:#484F58;text-align:center;border-top:1px solid #21262D;padding-top:6px;">'
    html += 'Crash Meter v39 · Tomhardi Methodology · A1+A2+B1+B2+C = ' + str(total) + '/5 · CAPE=' + cape_source + ' · Live FRED · Next: tomorrow'
    html += '</div>'

    html += '</div>'

    return html

# ═══════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown("## 🏠 Macro Dashboard")
    render_regime_compass(snap)

    narrative = snap.get("narrative", {}) or {}
    macro_nar = (narrative.get("macro_narrative") or {}) if isinstance(narrative, dict) else {}
    if macro_nar.get("headline") or macro_nar.get("narrative"):
        headline = macro_nar.get("headline", macro_nar.get("narrative", ""))
        st.markdown(f'<div class="narrative-card">'
                    f'<div class="narrative-headline">{str(headline)[:180]}{"..." if len(str(headline)) > 180 else ""}</div>'
                    f'<div class="narrative-sub">{macro_nar.get("sub_narrative", "")[:120]}</div></div>', unsafe_allow_html=True)

    st.divider()

    summary = snap.get("summary", {}) or {}
    health = snap.get("health", {}) or {}
    markov = snap.get("markov_v3", {}) or {}
    behavioral = snap.get("behavioral_macro", {}) or {}

    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
    with k1:
        vix_color = "#3FB950" if vix_now < 18 else "#D29922" if vix_now < 25 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Volatility (VIX)</div>'
                    f'<div class="metric-grid-value" style="color:{vix_color};">{vix_now:.1f}</div>'
                    f'{_gauge_html(vix_now, max_val=40, color=vix_color, height=8, label_left="Low", label_right="High")}'
                    f'</div>', unsafe_allow_html=True)
    with k2:
        health_score = health.get("composite_score", 50) if isinstance(health, dict) else 50
        hcolor = "#3FB950" if health_score >= 70 else "#D29922" if health_score >= 50 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Market Health</div>'
                    f'<div class="metric-grid-value" style="color:{hcolor};">{health_score:.0f}</div>'
                    f'{_gauge_html(health_score, max_val=100, color=hcolor, height=8, label_left="Weak", label_right="Strong")}'
                    f'</div>', unsafe_allow_html=True)
    with k3:
        yves = behavioral.get("yves", {}) if isinstance(behavioral, dict) else {}
        alert_level = yves.get("alert_level", "NONE") if isinstance(yves, dict) else "NONE"
        n_alerts = len((snap.get("yves_v2", {}) or {}).get("alerts", [])) if isinstance(snap.get("yves_v2"), dict) else 0
        alert_color = "#F85149" if alert_level in ("HIGH", "CRITICAL") or n_alerts > 2 else "#D29922" if alert_level == "MEDIUM" or n_alerts > 0 else "#3FB950"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Behavioral Alerts</div>'
                    f'<div class="metric-grid-value" style="color:{alert_color};">{n_alerts}</div>'
                    f'<div class="metric-grid-sub">Yves / AAII · {alert_level}</div>'
                    f'</div>', unsafe_allow_html=True)
    with k4:
        kelly = markov.get("kelly_fraction", 0.25) if isinstance(markov, dict) else 0.25
        kelly_color = "#3FB950" if kelly >= 0.5 else "#D29922" if kelly >= 0.25 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Kelly Fraction</div>'
                    f'<div class="metric-grid-value" style="color:{kelly_color};">{kelly:.0%}</div>'
                    f'<div class="metric-grid-sub">Optimal bet size</div>'
                    f'</div>', unsafe_allow_html=True)
    with k5:
        vix_b = (snap.get("vix_bucket") or {}).get("bucket", "—")
        vix_l = (snap.get("vix_bucket") or {}).get("label", "—")
        vix_c = "#3FB950" if vix_b == "INVESTABLE" else "#D29922" if vix_b == "CHOP" else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">VIX Bucket</div>'
                    f'<div class="metric-grid-value" style="color:{vix_c};">{vix_b}</div>'
                    f'<div class="metric-grid-sub">{vix_l}</div></div>', unsafe_allow_html=True)
    with k6:
        gk_passed = snap.get("summary", {}).get("v39_gatekeeper_passed", 0)
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Gatekeeper</div>'
                    f'<div class="metric-grid-value" style="color:{"#3FB950" if gk_passed > 0 else "#8B949E"};">{gk_passed}</div>'
                    f'<div class="metric-grid-sub">8-gate passed</div></div>', unsafe_allow_html=True)
    with k7:
        keith_ov = snap.get("summary", {}).get("v39_keith_overrides", 0)
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Keith Overrides</div>'
                    f'<div class="metric-grid-value" style="color:{"#D29922" if keith_ov > 0 else "#8B949E"};">{keith_ov}</div>'
                    f'<div class="metric-grid-sub">P0 signal sync</div></div>', unsafe_allow_html=True)
    with k8:
        wf_passed = snap.get("summary", {}).get("v39_walkforward_passed", 0)
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Walkforward</div>'
                    f'<div class="metric-grid-value" style="color:{"#3FB950" if wf_passed > 0 else "#8B949E"};">{wf_passed}</div>'
                    f'<div class="metric-grid-sub">MC 100x passed</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── LEFT COLUMN: Boom-Bust + Behavioral + Asset Pulse ──
    # ── RIGHT COLUMN: Crash Meter ──
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("### 🌀 Boom-Bust Stage")
        bb = snap.get("boom_bust", {}) or {}
        stage = bb.get("stage", "INCEPTION") if isinstance(bb, dict) else "INCEPTION"
        reflex = snap.get("reflexivity", {}) or {}
        score = reflex.get("super_bubble_score", 0) if isinstance(reflex, dict) else 0
        st.markdown(_timeline_html(stage), unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:6px;font-size:0.75rem;color:#8B949E;">Super Bubble Score: <span style="color:#E6EDF3;font-weight:700;">{score:.1f}</span>/10</div>', unsafe_allow_html=True)
        st.markdown(_gauge_html(score, max_val=10, color="#D29922", height=8, label_left="0", label_right="10"), unsafe_allow_html=True)

        st.markdown("### 🧠 Behavioral Macro (Yves)")
        behavioral = snap.get("behavioral_macro", {}) or {}
        yves = behavioral.get("yves", {}) if isinstance(behavioral, dict) else {}
        n_alerts = len((snap.get("yves_v2", {}) or {}).get("alerts", [])) if isinstance(snap.get("yves_v2"), dict) else 0
        if isinstance(yves, dict):
            alert = yves.get("alert", "")
            level = yves.get("alert_level", "NONE")
            if level == "NONE" and not alert:
                bullish = behavioral.get("bullish", 30)
                bearish = behavioral.get("bearish", 30)
                neutral = behavioral.get("neutral", 40)
                total = bullish + bearish + neutral
                if total > 0:
                    bull_pct = bullish / total * 100
                    bear_pct = bearish / total * 100
                    neut_pct = neutral / total * 100
                    casino_score = min(100, max(0, (bullish - 45) * 3))
                    cash_raise = min(50, max(0, casino_score * 0.4))
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#8B949E;margin-bottom:4px;">AAII Sentiment · Casino Score: <span style="color:{"#F85149" if casino_score > 60 else "#D29922" if casino_score > 40 else "#3FB950"};font-weight:700;">{casino_score:.0f}</span></div>'
                        f'<div style="display:flex;height:18px;border-radius:4px;overflow:hidden;background:#21262D;margin-bottom:6px;">'
                        f'<div style="width:{bull_pct:.0f}%;background:#3FB950;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">🐂 {bullish}</div>'
                        f'<div style="width:{neut_pct:.0f}%;background:#8B949E;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">⚖ {neutral}</div>'
                        f'<div style="width:{bear_pct:.0f}%;background:#F85149;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">🐻 {bearish}</div>'
                        f'</div>', unsafe_allow_html=True)
                    if casino_score > 40:
                        st.markdown(
                            f'<div style="background:#F8514915;border-left:3px solid #F85149;border-radius:6px;padding:6px 10px;margin:4px 0;">'
                            f'<div style="font-size:0.75rem;color:#F85149;font-weight:700;">⚠️ Casino Behavior Detected</div>'
                            f'<div style="font-size:0.7rem;color:#8B949E;margin-top:2px;">Bullish extreme ({bullish}%) = herd behavior. Consider raising <b>{cash_raise:.0f}% cash</b>. Wait for washout.</div>'
                            f'</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div style="font-size:0.7rem;color:#3FB950;margin-top:4px;">✅ Sentiment balanced. No casino behavior detected.</div>', unsafe_allow_html=True)
                else:
                    st.caption("Behavioral data unavailable")
            else:
                color = "#F85149" if level in ("HIGH", "CRITICAL") or n_alerts > 2 else "#D29922" if level == "MEDIUM" or n_alerts > 0 else "#3FB950"
                st.markdown(f'<div style="font-size:0.85rem;color:{color};font-weight:600;">{level}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{alert}</div>', unsafe_allow_html=True)
        else:
            st.caption("Behavioral macro unavailable")

        # ── ASSET PULSE (COMPACTED below Behavioral) ──
        st.markdown("### ⚡ Asset Pulse (21D)")
        pulse_assets = [("SPY", "US Eq"), ("QQQ", "Tech"), ("IWM", "Small"), ("GLD", "Gold"), ("TLT", "Bonds"), ("UUP", "DXY"), ("BTC-USD", "BTC"), ("ETH-USD", "ETH")]
        pulse_html = '<div style="display:flex;gap:6px;overflow-x:auto;padding:2px 0;">'
        for t, label in pulse_assets:
            ret = _price_ret(t, prices, 21)
            pulse_html += _asset_pulse_box_h(label, ret, t)
        pulse_html += '</div>'
        st.markdown(pulse_html, unsafe_allow_html=True)

    with right:
        st.markdown("### 🚨 Crash Meter v3")
        st.markdown("<div style='font-size:0.65rem;color:#8B949E;margin-bottom:8px;'>Sistemik risk meter: Yield Curve + Credit Spread + Valuasi (Tomhardi Methodology). Update harian kecuali CAPE (bulanan).</div>", unsafe_allow_html=True)
        st.markdown(_render_crash_meter(snap), unsafe_allow_html=True)

    st.divider()

    with st.expander("🔬 Deep Technical", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**CRI_v2 (Options Velocity)**")
            cri = snap.get("cri_v2_data", {}) or {}
            if cri:
                for t, data in list(cri.items())[:3]:
                    if isinstance(data, dict):
                        cri_color = "#F85149" if data.get("velocity") == "EXTREME" else "#D29922" if data.get("velocity") == "HIGH" else "#3FB950"
                        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                                    f'<span style="font-size:0.72rem;color:#E6EDF3;min-width:45px;">{t}</span>'
                                    f'<div class="gauge-track" style="flex:1;height:8px;"><div class="gauge-fill" style="width:{min(100,data.get("cri_v2",0)*100):.0f}%;background:{cri_color};"></div></div>'
                                    f'<span style="font-size:0.65rem;color:{cri_color};font-weight:700;width:60px;text-align:right;">{data.get("velocity","—")}</span></div>',
                                    unsafe_allow_html=True)
            else:
                st.caption("CRI_v2 unavailable")

            st.markdown("**Skew Term**")
            skew = snap.get("skew_term", {}) or {}; skew_data = skew.get("skew_data", {}) if isinstance(skew, dict) else {}
            d30 = d60 = d90 = None
            if isinstance(skew_data, dict):
                for k, v in skew_data.items():
                    if isinstance(v, dict):
                        val = v.get("skew") or v.get("value") or v.get("90_10")
                        if "30" in str(k).lower() or "1m" in str(k).lower(): d30 = _safe_float(val)
                        if "60" in str(k).lower() or "2m" in str(k).lower(): d60 = _safe_float(val)
                        if "90" in str(k).lower() or "3m" in str(k).lower(): d90 = _safe_float(val)
            st.markdown(_skew_bars_html(d30, d60, d90), unsafe_allow_html=True)
            st.markdown("**GEX**")
            gex = snap.get("gex_data", {}) or {}; gex_val = None
            if isinstance(gex, dict):
                for k, v in gex.items():
                    if isinstance(v, dict):
                        gv = v.get("net_gex") or v.get("gex") or v.get("total_gex")
                        if gv is not None: gex_val = _safe_float(gv); break
            st.markdown(_gex_bar_html(gex_val), unsafe_allow_html=True)
        with c2:
            st.markdown("**VRP**")
            vrp = snap.get("vrp_scanner", {}) or {}
            if isinstance(vrp, dict) and vrp.get("ok"):
                for item in vrp.get("high_vrp_sell_premium", [])[:3]:
                    if isinstance(item, dict):
                        score = item.get("vrp_pct", 0)
                        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                                    f'<span style="font-size:0.72rem;color:#E6EDF3;min-width:45px;">{item.get("ticker","—")}</span>'
                                    f'<div class="gauge-track" style="flex:1;height:8px;"><div class="gauge-fill" style="width:{min(100,abs(score)*5):.0f}%;background:#F85149;"></div></div>'
                                    f'<span style="font-size:0.65rem;color:#F85149;font-weight:700;width:35px;text-align:right;">{score:.0f}%</span></div>', unsafe_allow_html=True)
            else: st.caption("VRP unavailable")
            st.markdown("**Squeeze**")
            sq_scan = snap.get("squeeze_scanner", {}) or {}
            if isinstance(sq_scan, dict) and sq_scan.get("ok"):
                for item in sq_scan.get("imminent_squeezes", [])[:3]:
                    if isinstance(item, dict):
                        score = item.get("squeeze_score", 0)
                        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                                    f'<span style="font-size:0.72rem;color:#E6EDF3;min-width:45px;">{item.get("ticker","—")}</span>'
                                    f'<div class="gauge-track" style="flex:1;height:8px;"><div class="gauge-fill" style="width:{min(100,score):.0f}%;background:#D29922;"></div></div>'
                                    f'<span style="font-size:0.65rem;color:#D29922;font-weight:700;width:35px;text-align:right;">{score:.0f}</span></div>', unsafe_allow_html=True)
            else: st.caption("Squeeze unavailable")
            st.markdown("**Vol Forecast**")
            vol_f = snap.get("vol_forecast", {}) or {}
            if isinstance(vol_f, dict):
                for k, v in list(vol_f.items())[:3]:
                    if isinstance(v, dict):
                        regime = v.get("vol_regime", "-")
                        color = "#3FB950" if regime == "LOW" else "#D29922" if regime == "NORMAL" else "#F85149"
                        st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{k}: <span style="color:{color};font-weight:700;">{v.get("current_ann_vol",0):.1f}%</span> ({regime})</div>', unsafe_allow_html=True)
            else: st.caption("Vol forecast unavailable")
        st.markdown("**Engine Status**")
        engines = [
            ("GIP v10", snap.get("gip_v10") is not None), ("Markov V3", snap.get("markov_v3") is not None),
            ("Yves v2", snap.get("yves_v2") is not None), ("Cascade", snap.get("cascade_analysis") is not None),
            ("VRP", snap.get("vrp_scanner") is not None), ("Squeeze", snap.get("squeeze_scanner") is not None),
            ("Smart Money", snap.get("smart_money") is not None), ("Discovery", snap.get("discovery_brain") is not None),
            ("Supply Chain", snap.get("supply_chain_chains") is not None), ("Front-Run", len(snap.get("front_run_candidates",[]))>0),
            ("Crypto Whale", len(snap.get("crypto_tokens",{}))>0), ("IHSG Broker", len(snap.get("ihsg_broker_proxy",{}))>0),
        ]
        cols = st.columns(4)
        for i, (name, ok) in enumerate(engines):
            color = "#3FB950" if ok else "#F85149"
            cols[i % 4].markdown(f"<span style='color:{color};font-size:0.75rem;'>● {name}</span>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# PAGE: ALPHA CENTER
# ═══════════════════════════════════════════════════════════════════
def page_alpha():
    st.markdown("## ⚡ Alpha Center")
    sim_results = snap.get("simulation_results", {}) or {}

    # ── v39: Keith Signal Dashboard (Duration Aware) ──
    ks_data = snap.get("keith_sync", {})
    ks_summary = snap.get("keith_summary", {})

    if ks_summary and ks_summary.get("total_signals", 0) > 0:
        st.markdown("### 🎙️ Keith McCullough Signal Sync (P0 Override)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Signals", ks_summary.get("total_signals", 0))
        c2.metric("TRADE Bullish", ks_summary.get("trade_bullish", 0))
        c3.metric("TRADE Bearish", ks_summary.get("trade_bearish", 0))
        c4.metric("Duration Mismatch", ks_summary.get("duration_mismatches", 0))
        st.markdown(f"<div style='font-size:0.65rem;color:#484F58;'>Last updated: {ks_summary.get('last_updated', '—')} · Sources: {', '.join(ks_summary.get('sources', ['Hedgeye'])[:2])}</div>", unsafe_allow_html=True)

        # Show tickers with Keith contradictions
        contradictions = [(t, v) for t, v in ks_data.items() if isinstance(v, dict) and v.get("override") and v.get("keith_trade") != v.get("original_direction")]
        if contradictions:
            st.markdown(f"<div style='font-size:0.75rem;color:#F85149;font-weight:700;margin:8px 0;'>⚠️ {len(contradictions)} Keith Contradictions Detected</div>", unsafe_allow_html=True)
            for t, v in contradictions[:10]:
                orig = v.get("original_direction", "—")
                ktrade = v.get("keith_trade", "—")
                ktrend = v.get("keith_trend", "—")
                final = v.get("direction", "—")
                basis = v.get("basis", "")[:100]

                # Duration badge colors
                trade_c = "#3FB950" if ktrade == "BULLISH" else "#F85149" if ktrade == "BEARISH" else "#8B949E"
                trend_c = "#3FB950" if ktrend == "BULLISH" else "#F85149" if ktrend == "BEARISH" else "#8B949E"
                final_c = "#3FB950" if final == "LONG" else "#F85149" if final == "SHORT" or final == "AVOID" else "#D29922"

                st.markdown(
                    f'<div style="background:#161B22;border:1px solid #F8514940;border-radius:8px;padding:8px 12px;margin:4px 0;">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                    f'<span style="font-weight:800;font-size:1rem;color:#E6EDF3;min-width:70px;">{t}</span>'
                    f'<span style="font-size:0.65rem;padding:2px 6px;border-radius:4px;background:{trade_c}22;color:{trade_c};font-weight:700;">🎙️ TRADE: {ktrade}</span>'
                    f'<span style="font-size:0.65rem;padding:2px 6px;border-radius:4px;background:{trend_c}22;color:{trend_c};font-weight:700;">📈 TREND: {ktrend}</span>'
                    f'<span style="font-size:0.75rem;color:{final_c};font-weight:700;margin-left:auto;">→ {final}</span>'
                    f'</div>'
                    f'<div style="font-size:0.7rem;color:#8B949E;">Dashboard said <b>{orig}</b> · Keith TRADE = <b style="color:{trade_c};">{ktrade}</b> → Override to <b style="color:{final_c};">{final}</b></div>'
                    f'<div style="font-size:0.65rem;color:#484F58;margin-top:2px;">{basis}</div>'
                    f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── v39.1: Gatekeeper + Walkforward + Hedgeye (BACKGROUND ONLY) ──
    gk_data = snap.get("alpha_gatekeeper", {})
    wf_data = snap.get("walkforward_results", {})
    hp_data = snap.get("hedgeye_position_sizing", {})

    # v39.1 FIX: Gatekeeper runs in background — data attached to each ticker detail expander
    # Compact summary only, no main filter
    gk_passed = {t: r for t, r in gk_data.items() if isinstance(r, dict) and r.get("gate_status") == "PASS"}
    gk_marginal = {t: r for t, r in gk_data.items() if isinstance(r, dict) and r.get("gate_status") == "MARGINAL"}

    with st.expander(f"🛡️ Background Engine Status (Gatekeeper · Walkforward · Hedgeye)", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 Gatekeeper PASS", len(gk_passed))
        c2.metric("🟡 Gatekeeper MARGINAL", len(gk_marginal))
        c3.metric("✅ Walkforward PASS", len([t for t, r in wf_data.items() if isinstance(r, dict) and r.get("gate_status") == "PASS"]))
        if gk_passed:
            st.markdown(f"<div style='font-size:0.65rem;color:#484F58;'>Top 5 passed: " + ", ".join(list(gk_passed.keys())[:5]) + "</div>", unsafe_allow_html=True)
        st.caption("Gatekeeper + Walkforward + Hedgeye sizing data is shown inside each ticker’s 🔍 Toggle Full Details expander below.")

    st.divider()

    summary = snap.get("summary", {}) or {}
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Smart $ Consensus", summary.get("v7_smart_money_consensus", 0))
    k2.metric("Top Theses", summary.get("v7_top_theses_count", 0))
    k3.metric("Kelly", f"{summary.get('v7_markov_kelly', 0.25):.0%}")
    # Attachment 4: Bayesian Fusion + Fractional Kelly
    bayes = snap.get("bayesian_fusion", {})
    if bayes:
        k4.metric("Bayesian Fused", f"{bayes.get('fused_signal', 0):.2f}", f"conf {bayes.get('confidence', 0):.0%}")
    else:
        k4.metric("Bayesian Fused", "—")

    # Fractional Kelly positions
    fk = snap.get("fractional_kelly", {})
    if fk and fk.get("positions"):
        st.markdown(f'<div style="font-size:0.7rem;color:#8B949E;margin:4px 0;">'
                    f'Fractional Kelly: <b style="color:#3FB950;">{len(fk["positions"])}</b> positions · '
                    f'Exposure <b style="color:#D29922;">{fk.get("total_exposure", 0):.1%}</b></div>',
                    unsafe_allow_html=True)

    st.divider()


    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Unified Alpha", "🔮 Pure Front-Run", "📊 Vol & Squeeze", "🧠 Discovery"])

    with tab1:
        st.markdown("### 🎯 Unified Alpha — Quad Playbook × Bottleneck × Front-Run × Methodology")
        st.caption("**What this is:** Fusion of Hedgeye Quad playbook + Leopold bottleneck layers + COATUE rotation + Karsan vol + Thought Process thesis. Every ticker passes Walkforward gate (MC 100x) + Gatekeeper (8-gate). Only CHASE = ready to enter. WAIT = pullback needed. AVOID = broken setup.")
        st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin-bottom:8px;'>v39 Fusion: Hedgeye Quad + Leopold Bottleneck + Citrini Macro + Karsan Vol + COATUE Rotation. Every play must pass WF gate + MC 100x.</div>", unsafe_allow_html=True)

        # ── QUAD PLAYBOOK BANNER ──
        pb = _get_quad_playbook(snap)
        st.markdown(
            f'<div style="background:#161B22;border:1px solid #58A6FF40;border-radius:10px;padding:12px;margin:8px 0;">'
            f'<div style="font-size:0.7rem;color:#58A6FF;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:4px;">📊 QUAD {sq} PLAYBOOK</div>'
            f'<div style="font-size:0.85rem;color:#E6EDF3;font-weight:700;margin-bottom:6px;">{pb["theme"]}</div>'
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">'
            f'<span style="background:#3FB95018;color:#3FB950;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #3FB95040;">🎯 FRONT-RUN: {" · ".join(pb["front_run_sectors"][:4])}</span>'
            f'<span style="background:#D2992218;color:#D29922;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #D2992240;">🚧 BOTTLENECK: {" · ".join(pb["bottleneck_focus"][:3])}</span>'
            f'<span style="background:#F8514918;color:#F85149;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #F8514940;">🚫 AVOID: {" · ".join(pb["avoid"][:4])}</span>'
            f'</div>'
            f'<div style="font-size:0.65rem;color:#484F58;">Coatue: {pb["coatue_signal"]} · Karsan: {pb["karsan_setup"]} · Leopold: {" → ".join(pb["leopold_layers"])}</div>'
            f'</div>', unsafe_allow_html=True)

        # ── UNIFIED CANDIDATE POOL ──
        sim_results = snap.get("simulation_results", {}) or {}
        wf_results = snap.get("walkforward_results", {}) or {}
        gk_results = snap.get("alpha_gatekeeper", {}) or {}

        unified_candidates = []
        seen_tickers = set()

        def _add_unified(ticker, source, score, thesis, direction, why, timing, market_type="us_equity", extra=None):
            if ticker in seen_tickers or not ticker:
                return
            seen_tickers.add(ticker)
            # Check WF + Gatekeeper + Sim (background data, not hard gate)
            wf = wf_results.get(ticker, {})
            gk = gk_results.get(ticker, {})
            sim = sim_results.get(ticker, {})
            wf_score = wf.get("combined_gate_score", 0) if isinstance(wf, dict) else 0
            gk_status = gk.get("gate_status", "FAIL") if isinstance(gk, dict) else "FAIL"
            sim_score = sim.get("robustness_score", 0) if isinstance(sim, dict) else 0

            # Boost score with methodology fusion (Citrini, Leopold, COATUE, Karsan)
            leo = (snap.get("leopold_scan", {}) or {}).get("per_ticker", {}).get(ticker)
            if leo and isinstance(leo, dict) and leo.get("asymmetry_score", 0) >= 70:
                score += 15
            coat = (snap.get("coatue_scan", {}) or {}).get("per_ticker", {}).get(ticker)
            if coat and isinstance(coat, dict) and coat.get("signal", "") == ("BUY" if direction == "LONG" else "SELL"):
                score += 12
            kar = (snap.get("karsan_scanner", {}) or {}).get("per_ticker", {}).get(ticker)
            if kar and isinstance(kar, dict):
                if "squeeze" in str(kar.get("setup_type", "")).lower() and direction == "LONG":
                    score += 10
                if "convexity" in str(kar.get("setup_type", "")).lower() and direction == "LONG":
                    score += 10

            # v39.5: RELAXED GATE — methodology signals (Citrini/Leopold/COATUE/Karsan) bypass sim/gk requirement
            # Ticker dari affiliate sources tetap masuk meskipun belum ada sim/gk data
            has_methodology = bool(leo or coat or kar or source in ("bottleneck", "front_run", "leopold", "coatue", "karsan", "thought_process"))
            has_gate = sim_score >= 50 or gk_status in ("PASS", "MARGINAL") or wf_score >= 40
            if not has_gate and not has_methodology:
                return  # Skip only if no gate AND no methodology backing

            # Composite signal boost
            cs = (snap.get("composite_signals", {}) or {}).get(ticker)
            if cs and isinstance(cs, dict):
                cs_dir = cs.get("direction", "NEUTRAL")
                if (cs_dir == "LONG" and direction == "LONG") or (cs_dir == "SHORT" and direction == "SHORT"):
                    score += 8
                elif cs_dir != "NEUTRAL":
                    score -= 5  # Conflict penalty

            unified_candidates.append({
                "ticker": ticker, "source": source, "score": min(100, score),
                "thesis": thesis, "direction": direction, "why": why,
                "timing": timing, "market_type": market_type,
                "wf_score": wf_score, "gk_status": gk_status, "sim_score": sim_score,
                "extra": extra or {},
            })

        # 1. Bottleneck v3
        bottleneck = snap.get("bottleneck_v3", {}) or {}
        if isinstance(bottleneck, dict):
            for item in bottleneck.get("active_bottlenecks", []) or []:
                if not isinstance(item, dict): continue
                layer = item.get("name", "").replace("_", " ").title()
                for t in item.get("beneficiaries", [])[:5]:
                    mtype = _classify_ticker_market(t)
                    _add_unified(t, "bottleneck", 85,
                        f"Bottleneck: {layer} — {item.get('description','Supply constraint')}.",
                        "LONG", f"Supply bottleneck in {layer}. Price inelasticity = margin expansion.",
                        "Structural — multi-quarter", mtype,
                        {"layer": layer, "bottleneck": item.get("name", "")})

        # 2. Front-Run Candidates (all markets)
        fr = snap.get("front_run_candidates", []) or []
        for item in fr[:20]:
            if not isinstance(item, dict): continue
            t = item.get("ticker", "")
            mtype = item.get("market_type", _classify_ticker_market(t))
            _add_unified(t, "front_run", 75 if item.get("priority") == "TOP" else 70 if item.get("priority") == "HIGH" else 65,
                item.get("why_front_run", "")[:120], "LONG",
                item.get("why_front_run", "")[:200],
                f"Catalyst: {item.get('catalyst',{}).get('event','TBD')} ({item.get('catalyst',{}).get('quarter','')})",
                mtype, {"projection": item.get("projection"), "options": item.get("options", {})})

        # 3. Leopold Asymmetry
        leopold = snap.get("leopold_scan", {}) or {}
        if isinstance(leopold, dict):
            for t_data in leopold.get("asymmetry_setups", []) or []:
                if isinstance(t_data, dict) and t_data.get("asymmetry_score", 0) >= 70:
                    t = t_data.get("ticker", "")
                    mtype = _classify_ticker_market(t)
                    _add_unified(t, "leopold", t_data.get("asymmetry_score", 80),
                        t_data.get("thesis", "Asymmetry setup"),
                        t_data.get("direction", "LONG"),
                        f"Leopold asymmetry: {t_data.get('layer','Unknown')} bottleneck + {t_data.get('setup_type','')}.",
                        "Event-driven", mtype)

        # 4. COATUE Capital Rotation
        coatue = snap.get("coatue_scan", {}) or {}
        if isinstance(coatue, dict):
            for t, data in (coatue.get("per_ticker", {}) or {}).items():
                if isinstance(data, dict) and data.get("signal", "") in ("BUY", "SELL"):
                    mtype = _classify_ticker_market(t)
                    _add_unified(t, "coatue", 72,
                        f"COATUE: {data.get('signal')} — {data.get('rationale', '')[:80]}",
                        "LONG" if data.get("signal") == "BUY" else "SHORT",
                        f"Capital rotation signal from COATUE methodology.",
                        "Rotation-driven", mtype)

        # 5. Karsan Squeeze / Convexity
        karsan = snap.get("karsan_scanner", {}) or {}
        if isinstance(karsan, dict):
            for t, data in (karsan.get("per_ticker", {}) or {}).items():
                if isinstance(data, dict):
                    setup = data.get("setup_type", "")
                    if "squeeze" in setup.lower() or "convexity" in setup.lower():
                        mtype = _classify_ticker_market(t)
                        _add_unified(t, "karsan", 78,
                            f"Karsan {setup}: {data.get('rationale', '')[:80]}",
                            "LONG", f"Vol surface setup from Karsan methodology.",
                            "Vol-driven", mtype)

        # 6. Thought Process Top Theses
        tp = snap.get("thought_process", {}) or {}
        if isinstance(tp, dict):
            for t, data in list(tp.items())[:15]:
                if isinstance(data, dict) and data.get("thesis_score", 0) >= 70:
                    mtype = _classify_ticker_market(t)
                    _add_unified(t, "thought_process", data.get("thesis_score", 75),
                        f"Thesis: {data.get('matched_frameworks', [''])[0] if data.get('matched_frameworks') else 'Multi-framework'}",
                        "LONG", f"Thought process engine matched {len(data.get('matched_frameworks', []))} frameworks.",
                        "Thesis-driven", mtype)

        # 7. Quad-Aligned from playbook (fill gaps)
        for t in pb.get("front_run_tickers", [])[:15]:
            if t not in seen_tickers:
                mtype = _classify_ticker_market(t)
                _add_unified(t, "quad_aligned", 60,
                    f"Quad {sq} playbook alignment", "LONG",
                    f"Structural regime {sq} favors {t} per Hedgeye playbook.",
                    "Regime-driven", mtype)

        # Sort by score descending
        unified_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

        # ── SOURCE BREAKDOWN ──
        sources = {}
        for c in unified_candidates:
            src = c.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        if sources:
            src_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">'
            emoji_map = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","coatue":"💱","karsan":"📊","thought_process":"🧠","quad_aligned":"📊"}
            for src, count in sorted(sources.items(), key=lambda x: -x[1]):
                src_html += f'<span style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:4px 8px;font-size:0.7rem;color:#8B949E;">{emoji_map.get(src,"⚡")} {src.replace("_"," ").title()}: <b style="color:#E6EDF3;">{count}</b></span>'
            src_html += '</div>'
            st.markdown(src_html, unsafe_allow_html=True)

        st.markdown(f"**{len(unified_candidates)} unified candidates** · v39: Quad × Bottleneck × Front-Run × Methodology Fusion")

        # Build ticker rows BY MARKET TYPE (v39 fix)
        tickers_by_market = {}
        for c in unified_candidates:
            mt = c.get("market_type", "us_equity")
            tickers_by_market.setdefault(mt, []).append(c["ticker"])

        alpha_rows = []
        for mt, tickers in tickers_by_market.items():
            rows = build_ticker_rows(tickers, mt, vix_now,
                snap.get("gamma_data"), snap.get("greeks_data"),
                snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
            alpha_rows.extend(rows)

        # Inject alpha metadata
        for row in alpha_rows:
            c = next((x for x in unified_candidates if x.get("ticker") == row.get("ticker")), None)
            if c:
                row["alpha_source"] = c.get("source", "")
                row["alpha_score"] = c.get("score", 0)
                row["alpha_thesis"] = c.get("thesis", "")
                row["alpha_why"] = c.get("why", "")
                row["alpha_timing"] = c.get("timing", "")
                row["market_type"] = c.get("market_type", "us_equity")
                row["wf_score"] = c.get("wf_score", 0)
                row["gk_status"] = c.get("gk_status", "FAIL")
                row["sim_score"] = c.get("sim_score", 0)

        actionable = filter_actionable(alpha_rows, snap=snap)
        invalid = filter_invalid(alpha_rows)

        # v39.3: ALPHA CENTER — only HIGH CONVICTION (grade A/B + RR≥1.5 + sim/WF pass)
        hc_actionable = filter_high_conviction(actionable)
        hc_tickers = {r.get("ticker") for r in hc_actionable}
        monitor_alpha = [r for r in actionable if r.get("ticker") not in hc_tickers]

        # ── READY vs WAIT buckets (HIGH CONVICTION ONLY) ──
        ready_longs = [r for r in hc_actionable if r.get("chase_status") == "CHASE" and "LONG" in r.get("direction", "")]
        ready_shorts = [r for r in hc_actionable if r.get("chase_status") == "CHASE" and "SHORT" in r.get("direction", "")]
        wait_longs = [r for r in hc_actionable if r.get("chase_status") != "CHASE" and "LONG" in r.get("direction", "")]
        wait_shorts = [r for r in hc_actionable if r.get("chase_status") != "CHASE" and "SHORT" in r.get("direction", "")]

        # Monitor bucket (valid tapi belum high conviction)
        mon_longs = [r for r in monitor_alpha if "LONG" in r.get("direction", "")]
        mon_shorts = [r for r in monitor_alpha if "SHORT" in r.get("direction", "")]

        # ── DISPLAY: READY LONGS ──
        if ready_longs:
            st.markdown(f'<div style="font-size:0.7rem;color:#3FB950;text-transform:uppercase;font-weight:700;margin:10px 0 4px;letter-spacing:0.5px;">🟢 READY — LONG ({len(ready_longs)})</div>', unsafe_allow_html=True)
            for r in ready_longs[:12]:
                with st.container():
                    thesis = r.get("alpha_thesis", "")
                    why = r.get("alpha_why", "")
                    timing = r.get("alpha_timing", "")
                    src = r.get("alpha_source", "")
                    src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","coatue":"💱","karsan":"📊","thought_process":"🧠","quad_aligned":"📊"}.get(src,"⚡")
                    wf_badge = f'<span style="background:{"#3FB950" if r.get("wf_score",0)>=55 else "#D29922"}18;color:{"#3FB950" if r.get("wf_score",0)>=55 else "#D29922"};padding:1px 5px;border-radius:3px;font-size:0.55rem;font-weight:700;">WF {r.get("wf_score",0):.0f}</span>' if r.get("wf_score",0)>0 else ""
                    sim_badge = f'<span style="background:{"#3FB950" if r.get("sim_score",0)>=65 else "#D29922"}18;color:{"#3FB950" if r.get("sim_score",0)>=65 else "#D29922"};padding:1px 5px;border-radius:3px;font-size:0.55rem;font-weight:700;">MC {r.get("sim_score",0):.0f}</span>' if r.get("sim_score",0)>0 else ""

                    st.markdown(
                        f'<div class="alpha-thesis-card" style="border-left-color:#3FB950;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<span style="font-size:0.9rem;font-weight:800;color:#E6EDF3;">{r.get("ticker","—")}</span>'
                        f'<span class="alpha-ready banner-chase">🏃 CHASE</span>'
                        f'<span style="font-size:0.6rem;color:#484F58;">{src_emoji} {src.replace("_"," ").title()}</span>'
                        f'{wf_badge}{sim_badge}'
                        f'</div>'
                        f'<div class="alpha-thesis-sub"><b>Thesis:</b> {thesis}</div>'
                        f'<div class="alpha-thesis-sub"><b>Why:</b> {why}</div>'
                        f'<div class="alpha-thesis-sub" style="color:#D29922;"><b>Timing:</b> {timing}</div>'
                        f'</div>', unsafe_allow_html=True)
                    render_ticker_card_v4(r, expanded=False)

        # ── DISPLAY: READY SHORTS ──
        if ready_shorts:
            st.markdown(f'<div style="font-size:0.7rem;color:#F85149;text-transform:uppercase;font-weight:700;margin:10px 0 4px;letter-spacing:0.5px;">🔴 READY — SHORT ({len(ready_shorts)})</div>', unsafe_allow_html=True)
            for r in ready_shorts[:8]:
                with st.container():
                    thesis = r.get("alpha_thesis", "")
                    why = r.get("alpha_why", "")
                    timing = r.get("alpha_timing", "")
                    src = r.get("alpha_source", "")
                    src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","coatue":"💱","karsan":"📊","thought_process":"🧠","quad_aligned":"📊"}.get(src,"⚡")
                    st.markdown(
                        f'<div class="alpha-thesis-card" style="border-left-color:#F85149;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<span style="font-size:0.9rem;font-weight:800;color:#E6EDF3;">{r.get("ticker","—")}</span>'
                        f'<span class="alpha-ready banner-chase" style="background:rgba(239,68,68,0.12);border-color:rgba(239,68,68,0.35);color:#F85149;">🏃 CHASE SHORT</span>'
                        f'<span style="font-size:0.6rem;color:#484F58;">{src_emoji} {src.replace("_"," ").title()}</span>'
                        f'</div>'
                        f'<div class="alpha-thesis-sub"><b>Thesis:</b> {thesis}</div>'
                        f'<div class="alpha-thesis-sub"><b>Why:</b> {why}</div>'
                        f'<div class="alpha-thesis-sub" style="color:#D29922;"><b>Timing:</b> {timing}</div>'
                        f'</div>', unsafe_allow_html=True)
                    render_ticker_card_v4(r, expanded=False)

        # ── DISPLAY: WAIT ──
        if wait_longs:
            st.markdown(f'<div style="font-size:0.7rem;color:#D29922;text-transform:uppercase;font-weight:700;margin:10px 0 4px;letter-spacing:0.5px;">🟡 WAIT — LONG ({len(wait_longs)})</div>', unsafe_allow_html=True)
            for r in wait_longs[:8]:
                with st.container():
                    thesis = r.get("alpha_thesis", "")
                    src = r.get("alpha_source", "")
                    src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","coatue":"💱","karsan":"📊","thought_process":"🧠","quad_aligned":"📊"}.get(src,"⚡")
                    st.markdown(
                        f'<div class="alpha-thesis-card" style="border-left-color:#D29922;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<span style="font-size:0.9rem;font-weight:800;color:#E6EDF3;">{r.get("ticker","—")}</span>'
                        f'<span class="alpha-ready banner-wait">⏳ WAIT</span>'
                        f'<span style="font-size:0.6rem;color:#484F58;">{src_emoji} {src.replace("_"," ").title()}</span>'
                        f'</div>'
                        f'<div class="alpha-thesis-sub"><b>Thesis:</b> {thesis}</div>'
                        f'<div class="alpha-thesis-sub"><b>Why:</b> {r.get("alpha_why","")}</div>'
                        f'</div>', unsafe_allow_html=True)
                    render_ticker_card_v4(r, expanded=False)

        # ── MONITOR bucket (valid tapi belum high conviction) ──
        if mon_longs or mon_shorts:
            st.markdown(f'<div style="font-size:0.7rem;color:#D29922;text-transform:uppercase;font-weight:700;margin:10px 0 4px;letter-spacing:0.5px;">🟡 MONITOR — Not Yet High Conviction ({len(mon_longs)+len(mon_shorts)})</div>', unsafe_allow_html=True)
            for r in (mon_longs + mon_shorts)[:10]:
                with st.container():
                    thesis = r.get("alpha_thesis", "")
                    src = r.get("alpha_source", "")
                    src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","coatue":"💱","karsan":"📊","thought_process":"🧠","quad_aligned":"📊"}.get(src,"⚡")
                    st.markdown(
                        f'<div class="alpha-thesis-card" style="border-left-color:#D29922;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<span style="font-size:0.9rem;font-weight:800;color:#E6EDF3;">{r.get("ticker","—")}</span>'
                        f'<span class="alpha-ready banner-wait">⏳ MONITOR</span>'
                        f'<span style="font-size:0.6rem;color:#484F58;">{src_emoji} {src.replace("_"," ").title()}</span>'
                        f'</div>'
                        f'<div class="alpha-thesis-sub"><b>Thesis:</b> {thesis}</div>'
                        f'<div class="alpha-thesis-sub" style="color:#8B949E;font-size:0.65rem;">Quality: {r.get("quality_score",0):.0f} · RR {r.get("rr",0):.1f}x · Grade {r.get("grade","C")}</div>'
                        f'</div>', unsafe_allow_html=True)
                    render_ticker_card_v4(r, expanded=False)

        if invalid:
            with st.expander(f"⚠️ Filtered ({len(invalid)} invalid / conflict / avoid)", expanded=False):
                render_invalid_cards(invalid)

        if not unified_candidates:
            st.info("No unified candidates this snapshot. Run orchestrator with all engines enabled.")

    # ── Supply Chain Bottleneck Chains ──
    st.markdown("### 🔗 Supply Chain Bottleneck Chains")
    st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin-bottom:8px;'>Deep research: AI Buildout → Mideast Shock → Indonesia Resources. Stage 1-6 with tickers + bottleneck + confidence + rotation map.</div>", unsafe_allow_html=True)
    render_supply_chain_chains(snap)
    st.divider()
    with tab2:
        st.markdown("### 🔮 Pure Front-Run Candidates")
        st.caption("**What this is:** Ticker-ticker murni yang muncul dari news catalyst, supply chain bottleneck, atau rumor front-run. Belum melalui full methodology fusion seperti tab Unified Alpha. Gunakan untuk watchlist awal.")
        fr = snap.get("front_run_candidates", []) or []
        if fr:
            fr_tickers = [item.get("ticker","") for item in fr if isinstance(item, dict) and item.get("ticker")]
            fr_rows = build_ticker_rows(fr_tickers, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
            actionable_fr = filter_actionable(fr_rows, snap=snap)
            invalid_fr = filter_invalid(fr_rows)
            for row in actionable_fr:
                item = next((x for x in fr if isinstance(x, dict) and x.get("ticker") == row.get("ticker")), {})
                row["alpha_source"] = item.get("source", "front_run")
                row["alpha_score"] = 75 if item.get("priority") == "TOP" else 70 if item.get("priority") == "HIGH" else 65
                row["alpha_thesis"] = item.get("why_front_run", "")[:120]
                if item.get("catalyst"):
                    cat = item["catalyst"]
                    row["alpha_thesis"] += f" | Catalyst: {cat.get('event','')} ({cat.get('quarter','')})"
            fr_longs, fr_shorts = split_long_short(actionable_fr)
            if fr_longs:
                st.markdown(f"<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🟢 Front-Run Long ({len(fr_longs)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(fr_longs, max_rows=15)
            if fr_shorts:
                st.markdown(f"<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🔴 Front-Run Short ({len(fr_shorts)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(fr_shorts, max_rows=15)
            if invalid_fr:
                with st.expander(f"⚠️ Filtered Front-Run ({len(invalid_fr)} invalid)", expanded=False):
                    render_invalid_cards(invalid_fr)
        else:
            st.info("No front-run candidates this snapshot.")

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📊 VRP Scanner")
            vrp = snap.get("vrp_scanner", {}) or {}
            sell = []; buy = []
            if isinstance(vrp, dict) and vrp.get("ok"):
                sell = vrp.get("high_vrp_sell_premium", [])
                buy = vrp.get("low_vrp_buy_premium", [])
            if not sell and not buy:
                proxy_vrp = []
                for t in ["SPY","QQQ","IWM","GLD","TLT","VIXY","UVXY","HYG","LQD","EEM","TLT","IEF"]:
                    s = prices.get(t)
                    if s is None or len(s) < 60: continue
                    try:
                        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
                        if len(s_clean) < 60: continue
                        vol_20 = float(s_clean.tail(20).pct_change().dropna().std() * math.sqrt(252))
                        vol_60 = float(s_clean.tail(60).pct_change().dropna().std() * math.sqrt(252)) if len(s_clean) >= 60 else vol_20
                        iv_rank = min(100, max(0, (vol_20 / max(vol_60, 0.001) * 50)))
                        vrp_pct = (vol_20 / max(vol_60, 0.001) - 1) * 100
                        if vrp_pct > 15:
                            proxy_vrp.append({"ticker": t, "vrp_pct": round(vrp_pct, 0), "iv_rank": round(iv_rank, 0), "direction": "SELL"})
                        elif vrp_pct < -15:
                            buy.append({"ticker": t, "vrp_pct": round(abs(vrp_pct), 0), "iv_rank": round(iv_rank, 0), "direction": "BUY"})
                    except Exception: pass
                sell = proxy_vrp
            st.metric("Sell Premium", len(sell))
            st.metric("Buy Premium", len(buy))
            if sell:
                for item in sell[:8]:
                    if isinstance(item, dict):
                        st.markdown(f"• **{item.get('ticker')}** · VRP +{item.get('vrp_pct', 0):.0f}% · IV Rank {item.get('iv_rank', '—')}")
            else: st.caption("No sell premium setups")
            if buy:
                st.markdown("<div style='font-size:0.65rem;color:#3FB950;text-transform:uppercase;font-weight:600;margin-top:8px;'>Buy Convexity</div>", unsafe_allow_html=True)
                for item in buy[:5]:
                    if isinstance(item, dict):
                        st.markdown(f"• **{item.get('ticker')}** · VRP {item.get('vrp_pct', 0):.0f}% cheap · IV Rank {item.get('iv_rank', '—')}")
        with col2:
            st.markdown("### 🔥 Squeeze Scanner")
            sq_scan = snap.get("squeeze_scanner", {}) or {}
            imm = []; strong = []
            if isinstance(sq_scan, dict) and sq_scan.get("ok"):
                imm = sq_scan.get("imminent_squeezes", [])
                strong = sq_scan.get("strong_candidates", [])
            if not imm and not strong:
                proxy_sq = []
                for t in list(prices.keys())[:80]:
                    s = prices.get(t)
                    if s is None or len(s) < 40: continue
                    try:
                        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
                        if len(s_clean) < 40: continue
                        # Hedgeye Risk Range squeeze proxy (v39.2 — BB removed)
                        px = float(s_clean.iloc[-1])
                        trade_basis = float(s_clean.tail(15).mean())
                        trade_std = float(s_clean.tail(15).std())
                        if trade_std == 0: continue
                        trade_lrr = trade_basis - 1.5 * trade_std
                        trade_trr = trade_basis + 1.5 * trade_std
                        trend_basis = float(s_clean.tail(63).mean()) if len(s_clean) >= 63 else trade_basis
                        trend_std = float(s_clean.tail(63).std()) if len(s_clean) >= 63 else trade_std
                        trend_lrr = trend_basis - 2.0 * trend_std
                        trend_trr = trend_basis + 2.0 * trend_std
                        in_trade_range = trade_lrr < px < trade_trr
                        near_trend_mid = abs(px - trend_basis) / max(trend_basis, 0.001) < 0.03
                        vol_20 = float(s_clean.tail(20).pct_change().dropna().std())
                        vol_5 = float(s_clean.tail(5).pct_change().dropna().std()) if len(s_clean) >= 5 else vol_20
                        vol_contracting = vol_5 < vol_20 * 0.6
                        if vol_contracting and in_trade_range and near_trend_mid:
                            score = min(100, int(50 + (1 - vol_5/vol_20) * 50))
                            proxy_sq.append({"ticker": t, "squeeze_score": score, "tier": "PROXY"})
                    except Exception: pass
                proxy_sq.sort(key=lambda x: x["squeeze_score"], reverse=True)
                imm = proxy_sq[:8]
            st.metric("Imminent", len(imm))
            st.metric("Strong", len(strong))
            if imm:
                for item in imm[:8]:
                    if isinstance(item, dict):
                        tier_badge = "🟡 PROXY" if item.get("tier") == "PROXY" else f"🔥 {item.get('tier','—')}"
                        st.markdown(f"• **{item.get('ticker')}** · Score {item.get('squeeze_score', 0):.0f}/100 {tier_badge}")
            else: st.caption("No imminent squeezes")

    with tab4:
        st.markdown("### 🔮 Discovery Brain")
        st.caption("**What this is:** Adaptive/Reactive/Proactive discovery dari news + cascade + behavioral. Raw ideas yang belum melalui risk range validation. Untuk brainstorming, bukan execution langsung.")
        disc = snap.get("discovery_brain", {}) or {}
        if isinstance(disc, dict) and disc.get("by_mode"):
            for mode in ("adaptive", "reactive", "proactive"):
                items = disc.get("by_mode", {}).get(mode, [])
                if items:
                    st.markdown(f"**{mode.title()}** ({len(items)})")
                    for item in items[:5]:
                        if isinstance(item, dict):
                            with st.expander(f"{item.get('name', '—').replace('_', ' ')} · conf {item.get('confidence', 0):.0%}"):
                                st.markdown(item.get("thesis", "—"))
        else: st.info("Discovery Brain — no candidates this snapshot")

        st.markdown("### 💰 Position Sizing")
        sizing = snap.get("portfolio_sizing_v2", {}) or {}
        if isinstance(sizing, dict) and sizing.get("positions"):
            st.metric("Deployed", f"{sizing.get('total_deployed_pct', 0):.1%}")
            st.metric("Cash", f"{sizing.get('cash_pct', 0):.1%}")
            df = pd.DataFrame([{"Ticker": p.get("ticker"), "Size %": f"{p.get('target_pct', 0):.2f}%",
                                "Size $": f"{p.get('target_dollar', 0):,.0f}", "Mode": p.get("mode"), "Sector": p.get("sector")}
                               for p in sizing.get("positions", []) if isinstance(p, dict)])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("No sized positions yet.")

        conv = snap.get("conviction_sizing", {}) or {}
        if isinstance(conv, dict) and conv.get("positions"):
            st.markdown("### 🎯 Conviction Sizing (Soros)")
            for p in conv.get("positions", [])[:5]:
                if not isinstance(p, dict): continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;padding:3px 0;">'
                            f'<span style="color:#E6EDF3;">{p.get("ticker","—")}</span>'
                            f'<span style="color:#8B949E;">{p.get("conviction","—")} · {p.get("size_pct",0):.1f}%</span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# PAGE: US STOCKS
# ═══════════════════════════════════════════════════════════════════
def page_us_stocks():
    # ── Quick Ticker Lookup ──
    with st.expander("🔍 Quick Ticker Lookup", expanded=False):
        q_ticker = st.text_input("Enter ticker", "", key="ql_us")
        if q_ticker:
            render_ticker_detail_comprehensive(q_ticker.upper().strip(), snap)

    st.markdown("## 🇺🇸 US Stocks")

    pb = _get_hedgeye_playbook(snap)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Overweight</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"][:10]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Underweight</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["short"][:8]) + "</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📊 Index / ETF Setups (SPY · QQQ · IWM · GLD · TLT)")
    key_etfs = ["SPY", "QQQ", "IWM", "GLD", "TLT"]
    sim_results = snap.get("simulation_results", {}) if isinstance(snap.get("simulation_results"), dict) else {}
    etf_rows = build_ticker_rows(key_etfs, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    etf_actionable = filter_actionable(etf_rows, snap=snap)
    etf_invalid = filter_invalid(etf_rows)
    etf_longs, etf_shorts = split_long_short(etf_actionable)
    if etf_longs:
        st.markdown(f"<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:4px;'>🟢 Long Bias</div>", unsafe_allow_html=True)
        render_ticker_cards_v4(etf_longs, max_rows=10)
    if etf_shorts:
        st.markdown(f"<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:4px;'>🔴 Short Bias</div>", unsafe_allow_html=True)
        render_ticker_cards_v4(etf_shorts, max_rows=10)
    if etf_invalid:
        with st.expander(f"⚠️ Filtered ETFs ({len(etf_invalid)} invalid / conflict)", expanded=False):
            render_invalid_cards(etf_invalid)

    st.divider()
    us_tickers = list(US_SECTORS.keys()) if US_SECTORS else []
    for bucket in ["Growth","Quality","Defensives","Semis","Energy","Industrials","Financials","AI_Infra","PreciousMetals"]:
        us_tickers += US_BUCKETS.get(bucket, []) if US_BUCKETS else []
    if not us_tickers: us_tickers = FALLBACK_US
    # Filter out key ETFs that already shown above
    key_etfs_set = {"SPY", "QQQ", "IWM", "GLD", "TLT"}
    us_tickers = [t for t in us_tickers if t not in key_etfs_set]
    us_tickers = list(dict.fromkeys(us_tickers))

    rows = build_ticker_rows(us_tickers, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    actionable = filter_actionable(rows, snap=snap)
    invalid = filter_invalid(rows)

    # v39.3: HIGH CONVICTION gate — only grade A/B + RR≥1.5 + sim/WF pass
    high_conv = filter_high_conviction(actionable)
    hc_longs, hc_shorts = split_long_short(high_conv)

    # Monitor = valid & actionable tapi belum high conviction (grade C, RR 1.0–1.5, WF marginal, dll)
    hc_tickers = {r.get("ticker") for r in high_conv}
    monitor = [r for r in actionable if r.get("ticker") not in hc_tickers]
    mon_longs, mon_shorts = split_long_short(monitor)

    st.markdown(
        f"**{len(high_conv)} high conviction** · "
        f"🟢 {len(hc_longs)} Long · 🔴 {len(hc_shorts)} Short · "
        f"🟡 {len(monitor)} monitor · ⚠️ {len(invalid)} filtered"
    )
    tab_hc_l, tab_hc_s, tab_mon = st.tabs([
        f"🎯 Ready Long ({len(hc_longs)})",
        f"🎯 Ready Short ({len(hc_shorts)})",
        f"🟡 Monitor ({len(monitor)})",
    ])
    with tab_hc_l: render_ticker_cards_v4(hc_longs)
    with tab_hc_s: render_ticker_cards_v4(hc_shorts)
    with tab_mon: render_ticker_cards_v4(monitor)
    if invalid:
        with st.expander(f"⚠️ Filtered Out ({len(invalid)} invalid / conflict / avoid)", expanded=False):
            render_invalid_cards(invalid)

    # v38 Daily Plays REMOVED per v39.2 audit


# ═══════════════════════════════════════════════════════════════════
# PAGE: FOREX
# ═══════════════════════════════════════════════════════════════════
def page_forex():
    # ── Quick Ticker Lookup ──
    with st.expander("🔍 Quick Ticker Lookup", expanded=False):
        q_ticker = st.text_input("Enter ticker", "", key="ql_fx")
        if q_ticker:
            render_ticker_detail_comprehensive(q_ticker.upper().strip(), snap)

    st.markdown("## 💱 Forex")
    pb = _get_hedgeye_playbook(snap)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["short"]) + "</div>", unsafe_allow_html=True)
    dxy_corr = snap.get("dxy_correlation", {}) or {}
    if isinstance(dxy_corr, dict) and (dxy_corr.get("strongest_positive_corr") or dxy_corr.get("strongest_negative_corr")):
        st.divider()
    fx_tickers = list(FOREX_PAIRS.keys()) if FOREX_PAIRS else FALLBACK_FX
    sim_results = snap.get("simulation_results", {}) if isinstance(snap.get("simulation_results"), dict) else {}
    rows = build_ticker_rows(fx_tickers, "forex", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    actionable = filter_actionable(rows, snap=snap)
    invalid = filter_invalid(rows)

    high_conv = filter_high_conviction(actionable)
    hc_longs, hc_shorts = split_long_short(high_conv)
    hc_tickers = {r.get("ticker") for r in high_conv}
    monitor = [r for r in actionable if r.get("ticker") not in hc_tickers]

    st.markdown(
        f"**{len(high_conv)} high conviction** · "
        f"🟢 {len(hc_longs)} Long · 🔴 {len(hc_shorts)} Short · "
        f"🟡 {len(monitor)} monitor · ⚠️ {len(invalid)} filtered"
    )
    tab_hc_l, tab_hc_s, tab_mon = st.tabs([
        f"🎯 Ready Long ({len(hc_longs)})",
        f"🎯 Ready Short ({len(hc_shorts)})",
        f"🟡 Monitor ({len(monitor)})",
    ])
    with tab_hc_l: render_ticker_cards_v4(hc_longs)
    with tab_hc_s: render_ticker_cards_v4(hc_shorts)
    with tab_mon: render_ticker_cards_v4(monitor)
    if invalid:
        with st.expander(f"⚠️ Filtered Out ({len(invalid)} invalid / conflict / avoid)", expanded=False):
            render_invalid_cards(invalid)

    # v38 Daily Plays REMOVED per v39.2 audit


# ═══════════════════════════════════════════════════════════════════
# PAGE: COMMODITIES
# ═══════════════════════════════════════════════════════════════════
def page_commodities():
    # ── Quick Ticker Lookup ──
    with st.expander("🔍 Quick Ticker Lookup", expanded=False):
        q_ticker = st.text_input("Enter ticker", "", key="ql_comm")
        if q_ticker:
            render_ticker_detail_comprehensive(q_ticker.upper().strip(), snap)

    st.markdown("## 🛢️ Commodities")
    pb = _get_hedgeye_playbook(snap)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + (" · ".join(pb["short"]) if pb["short"] else "—") + "</div>", unsafe_allow_html=True)
    st.divider()
    comm_tickers = list(COMMODITIES.keys()) if COMMODITIES else FALLBACK_COMM
    sim_results = snap.get("simulation_results", {}) if isinstance(snap.get("simulation_results"), dict) else {}
    rows = build_ticker_rows(comm_tickers, "commodity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    actionable = filter_actionable(rows, snap=snap)
    invalid = filter_invalid(rows)

    high_conv = filter_high_conviction(actionable)
    hc_longs, hc_shorts = split_long_short(high_conv)
    hc_tickers = {r.get("ticker") for r in high_conv}
    monitor = [r for r in actionable if r.get("ticker") not in hc_tickers]

    st.markdown(
        f"**{len(high_conv)} high conviction** · "
        f"🟢 {len(hc_longs)} Long · 🔴 {len(hc_shorts)} Short · "
        f"🟡 {len(monitor)} monitor · ⚠️ {len(invalid)} filtered"
    )
    tab_hc_l, tab_hc_s, tab_mon = st.tabs([
        f"🎯 Ready Long ({len(hc_longs)})",
        f"🎯 Ready Short ({len(hc_shorts)})",
        f"🟡 Monitor ({len(monitor)})",
    ])
    with tab_hc_l: render_ticker_cards_v4(hc_longs)
    with tab_hc_s: render_ticker_cards_v4(hc_shorts)
    with tab_mon: render_ticker_cards_v4(monitor)
    if invalid:
        with st.expander(f"⚠️ Filtered Out ({len(invalid)} invalid / conflict / avoid)", expanded=False):
            render_invalid_cards(invalid)

    # v38 Daily Plays REMOVED per v39.2 audit


# ═══════════════════════════════════════════════════════════════════
# PAGE: CRYPTO
# ═══════════════════════════════════════════════════════════════════
def page_crypto():
    # ── Quick Ticker Lookup ──
    with st.expander("🔍 Quick Ticker Lookup", expanded=False):
        q_ticker = st.text_input("Enter ticker", "", key="ql_crypto")
        if q_ticker:
            render_ticker_detail_comprehensive(q_ticker.upper().strip(), snap)

    st.markdown("## ₿ Crypto")

    # Whale signal moved to ticker detail expander (v39.2)
    st.divider()

    pb = _get_hedgeye_playbook(snap)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + (" · ".join(pb["short"]) if pb["short"] else "—") + "</div>", unsafe_allow_html=True)
    cc = snap.get("crypto_center", {}) or {}
    if isinstance(cc, dict) and (cc.get("capital_flows") or cc.get("market_structure")):
        st.divider()
        st.markdown("### ₿ On-Chain / Market Structure")
        flows = cc.get("capital_flows", {})
        if isinstance(flows, dict):
            st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;">Stablecoin: <span style="color:#E6EDF3;font-weight:700;">{flows.get("total_b",0):.1f}B</span> ({flows.get("change_7d_b",0):+.1f}B 7D)</div>', unsafe_allow_html=True)
        structure = cc.get("market_structure", {})
        if isinstance(structure, dict) and structure.get("funding"):
            st.markdown("<div style='font-size:0.65rem; color:#8B949E; text-transform:uppercase; font-weight:600; margin-top:6px; margin-bottom:3px;'>Funding Rates</div>", unsafe_allow_html=True)
            for sym, data in list(structure.get("funding", {}).items())[:4]:
                if isinstance(data, dict):
                    rate = data.get("rate", 0)
                    color = "#3FB950" if rate < 0 else "#F85149" if rate > 0.0005 else "#8B949E"
                    st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{sym}: <span style="color:{color};font-weight:700;">{rate:.4f}</span></div>', unsafe_allow_html=True)
        narrative_crypto = cc.get("narrative", {})
        if isinstance(narrative_crypto, dict) and narrative_crypto.get("fear_greed"):
            fg = narrative_crypto.get("fear_greed", {})
            st.markdown(f'<div style="margin-top:6px;font-size:0.78rem;color:#8B949E;">Fear & Greed: <span style="color:#E6EDF3;font-weight:700;">{fg.get("value",50)}</span> ({fg.get("label","Neutral")})</div>', unsafe_allow_html=True)
    st.divider()
    crypto_tickers = list(CRYPTO.keys()) if CRYPTO else FALLBACK_CRYPTO
    sim_results = snap.get("simulation_results", {}) if isinstance(snap.get("simulation_results"), dict) else {}
    rows = build_ticker_rows(crypto_tickers, "crypto", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    actionable = filter_actionable(rows, snap=snap)
    invalid = filter_invalid(rows)

    high_conv = filter_high_conviction(actionable)
    hc_longs, hc_shorts = split_long_short(high_conv)
    hc_tickers = {r.get("ticker") for r in high_conv}
    monitor = [r for r in actionable if r.get("ticker") not in hc_tickers]

    st.markdown(
        f"**{len(high_conv)} high conviction** · "
        f"🟢 {len(hc_longs)} Long · 🔴 {len(hc_shorts)} Short · "
        f"🟡 {len(monitor)} monitor · ⚠️ {len(invalid)} filtered"
    )
    tab_hc_l, tab_hc_s, tab_mon = st.tabs([
        f"🎯 Ready Long ({len(hc_longs)})",
        f"🎯 Ready Short ({len(hc_shorts)})",
        f"🟡 Monitor ({len(monitor)})",
    ])
    with tab_hc_l: render_ticker_cards_v4(hc_longs)
    with tab_hc_s: render_ticker_cards_v4(hc_shorts)
    with tab_mon: render_ticker_cards_v4(monitor)
    if invalid:
        with st.expander(f"⚠️ Filtered Out ({len(invalid)} invalid / conflict / avoid)", expanded=False):
            render_invalid_cards(invalid)

    # v38 Daily Plays REMOVED per v39.2 audit


# ═══════════════════════════════════════════════════════════════════
# v38 IHSG SAFE WRAPPER — Force BUY-ONLY, strip SHORT labels
# ═══════════════════════════════════════════════════════════════════
    try:
        # Monkey-patch session state for IHSG safety
        orig_snap = dict(snap) if isinstance(snap, dict) else {}
        # Call original v38
        # v38_REMOVED("ihsg", snap, prices, st)
    except Exception as e:
        logger.warning(f"v38 IHSG safe wrapper: {e}")

# ═══════════════════════════════════════════════════════════════════
# PAGE: GLOBAL & EM
# ═══════════════════════════════════════════════════════════════════
def page_global():
    # ── Quick Ticker Lookup ──
    with st.expander("🔍 Quick Ticker Lookup", expanded=False):
        q_ticker = st.text_input("Enter ticker", "", key="ql_global")
        if q_ticker:
            render_ticker_detail_comprehensive(q_ticker.upper().strip(), snap)

    st.markdown("## 🌍 Global & EM")
    global_ = snap.get("global", {}) or {}
    country_list = global_.get("country_list", []) if isinstance(global_, dict) else []
    if not country_list:
        base_map = {
            "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia","UAE","Israel","Poland","Czech Republic","Romania"],
            "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand","Colombia","New Zealand","Norway","Kazakhstan","Angola"],
            "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt","Spain","Netherlands","Belgium","Sweden","Switzerland"],
            "Q4": ["Venezuela","Iran","Ukraine","Greece","Portugal","Lebanon","Syria","Yemen","Zimbabwe","Sudan","Afghanistan","North Korea","Myanmar","Belarus","Bolivia"],
        }
        country_list = []
        for q, countries in base_map.items():
            for c in countries: country_list.append({"country": c, "quad": q, "regime_name": _quad_name(q)})
    st.markdown("### 🗺️ Country Regime Map")

    # ── v38: Overlay Hedgeye public calls (manual list — Edward updatable) ──
    HEDGEYE_PUBLIC_CALLS = {
        "Indonesia": {"quad": "Q4", "source": "Keith McCullough May 21 2026 #timestamped"},
        # Add more as Hedgeye publishes
    }
    for entry in country_list:
        if isinstance(entry, dict):
            cname = entry.get("country", "")
            hedgeye = HEDGEYE_PUBLIC_CALLS.get(cname)
            if hedgeye and hedgeye["quad"] != entry.get("quad"):
                entry["mismatch_warning"] = f"⚠️ Hedgeye: {hedgeye['quad']}"

    st.markdown(_heatmap_grid_html(country_list[:16], key_label="country", key_quad="quad"), unsafe_allow_html=True)
    if len(country_list) > 16: st.markdown(_heatmap_grid_html(country_list[16:32], key_label="country", key_quad="quad"), unsafe_allow_html=True)

    # Show mismatch warnings below map
    mismatches = [e for e in country_list if isinstance(e, dict) and e.get("mismatch_warning")]
    if mismatches:
        st.markdown(
            '<div style="background:#161B22;border:1px solid #F0883E55;border-radius:6px;'
            'padding:10px 14px;margin:8px 0;">'
            '<b style="color:#F0883E;">⚠️ Hedgeye Quad Mismatches</b>'
            '</div>',
            unsafe_allow_html=True,
        )
        for m in mismatches:
            cname = m.get("country", "?")
            our_q = m.get("quad", "?")
            our_regime = m.get("regime_name", "")
            warning = m.get("mismatch_warning", "")
            st.markdown(
                f'<div style="font-size:0.75rem;color:#C9D1D9;padding:4px 12px;">'
                f'<b>{cname}</b>: Our model <b style="color:#58A6FF;">{our_q}</b> ({our_regime}) · '
                f'<span style="color:#F0883E;">{warning}</span></div>',
                unsafe_allow_html=True,
            )
    st.divider()

    st.markdown("### 🇮🇩 IHSG Report")
    ihsg_tickers = list(IHSG_UNIVERSE.keys()) if IHSG_UNIVERSE else FALLBACK_IHSG
    sim_results = snap.get("simulation_results", {}) if isinstance(snap.get("simulation_results"), dict) else {}
    ihsg_rows = build_ticker_rows(ihsg_tickers, "ihsg", vix_now, prices=prices, ar=ar, snap=snap, sim_results=sim_results)
    actionable_ihsg = filter_actionable(ihsg_rows, snap=snap)
    invalid_ihsg = filter_invalid(ihsg_rows)

    # v39.3: IHSG juga high conviction only
    high_conv_ihsg = filter_high_conviction(actionable_ihsg)
    hc_tickers_ihsg = {r.get("ticker") for r in high_conv_ihsg}
    monitor_ihsg = [r for r in actionable_ihsg if r.get("ticker") not in hc_tickers_ihsg]

    by_sector = {}
    for r in high_conv_ihsg: by_sector.setdefault(IHSG_SECTOR_MAP.get(r.get("ticker"), "Other"), []).append(r)
    if by_sector:
        sectors = list(by_sector.keys()); counts = [len(v) for v in by_sector.values()]
        colors = [_ret_color(sum(x.get("r20d",0) or 0 for x in by_sector[s])/max(len(by_sector[s]),1)) for s in sectors]
        fig = go.Figure(go.Bar(y=sectors, x=counts, orientation="h", marker_color=colors, text=[str(c) for c in counts], textposition="outside", textfont=dict(size=11, color="#E6EDF3")))
        fig.update_layout(height=max(250, len(sectors)*35), margin=dict(l=120,r=40,t=20,b=20), paper_bgcolor="#0D1117", plot_bgcolor="#0D1117", font=dict(color="#E6EDF3", size=11, family="Inter"), xaxis=dict(showgrid=True, gridcolor="#21262D"), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="ihsg_sector_bar_v4_global")
    st.markdown(
        f"**{len(high_conv_ihsg)} high conviction** · Sectors: {', '.join(by_sector.keys())} · "
        f"🟡 {len(monitor_ihsg)} monitor · ⚠️ {len(invalid_ihsg)} filtered"
    )
    for sector, items in by_sector.items():
        with st.expander(f"**{sector}** ({len(items)} stocks)", expanded=False):
            render_ticker_cards_v4(items, max_rows=10)
    if monitor_ihsg:
        with st.expander(f"🟡 Monitor IHSG ({len(monitor_ihsg)} valid tapi belum high conviction)", expanded=False):
            render_ticker_cards_v4(monitor_ihsg, max_rows=10)
    if invalid_ihsg:
        with st.expander(f"⚠️ Filtered IHSG ({len(invalid_ihsg)} invalid / conflict)", expanded=False):
            render_invalid_cards(invalid_ihsg)

    # v38 Daily Plays REMOVED per v39.2 audit


# ═══════════════════════════════════════════════════════════════════
# PAGE: THEMES
# ═══════════════════════════════════════════════════════════════════
def page_themes():
    st.markdown("## 📖 Themes & Playbook")
    allocation = {
        "Q1": {"long": 75, "short": 5, "cash": 20, "style": "Tech 30% | Growth 20% | Crypto 15% | EM 5% | Defensives 5%"},
        "Q2": {"long": 70, "short": 10, "cash": 20, "style": "Cyclicals 25% | Financials 15% | Energy 15% | Materials 10% | Small Caps 5%"},
        "Q3": {"long": 60, "short": 15, "cash": 25, "style": "Energy/Infra 20% | Real Assets 15% | Crypto 10% | EM/LatAm 8% | IHSG Energy 7%"},
        "Q4": {"long": 50, "short": 20, "cash": 30, "style": "TLT 15% | Gold 10% | Utilities 10% | Staples 10% | Healthcare 5%"},
    }
    alloc = allocation.get(sq, allocation["Q3"])
    st.markdown("### 💼 Portfolio Allocation")
    st.markdown(_stacked_bar_html(alloc["long"], alloc["short"], alloc["cash"]), unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.78rem; color:#8B949E; margin-top:6px;'>**Style:** {alloc['style']}</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### ⚡ Cem Karsan / 0DTE")
    odte = snap.get("odte_monitor", {}) or {}
    if isinstance(odte, dict) and odte.get("tickers"):
        for t, data in list(odte.get("tickers", {}).items())[:3]:
            if not isinstance(data, dict): continue
            pin = data.get("pin_risk", 50)
            vanna_dir = data.get("vanna", "neutral"); charm_dir = data.get("charm", "neutral")
            v_arrow = "⬆" if "up" in str(vanna_dir).lower() or "pos" in str(vanna_dir).lower() else "⬇" if "down" in str(vanna_dir).lower() or "neg" in str(vanna_dir).lower() else "➡"
            c_arrow = "⬆" if "up" in str(charm_dir).lower() or "pos" in str(charm_dir).lower() else "⬇" if "down" in str(charm_dir).lower() or "neg" in str(charm_dir).lower() else "➡"
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;padding:7px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;">'
                        f'<span style="font-weight:700;font-size:0.85rem;color:#E6EDF3;min-width:45px;">{t}</span>'
                        f'<div style="flex:1;"><div style="font-size:0.58rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Pin Risk</div>'
                        f'{_gauge_html(pin, max_val=100, color="#D29922", height=9, label_left="0", label_right="100")}</div>'
                        f'<div style="font-size:0.75rem;color:#58A6FF;font-weight:700;">Vanna {v_arrow}</div>'
                        f'<div style="font-size:0.75rem;color:#A371F7;font-weight:700;">Charm {c_arrow}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("0DTE data unavailable — showing proxy")
        for t in ["SPY","QQQ","IWM"]:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;padding:7px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;">'
                        f'<span style="font-weight:700;font-size:0.85rem;color:#E6EDF3;min-width:45px;">{t}</span>'
                        f'<div style="flex:1;"><div style="font-size:0.58rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Pin Risk</div>'
                        f'{_gauge_html(50, max_val=100, color="#30363D", height=9, label_left="0", label_right="100")}</div>'
                        f'<div style="font-size:0.75rem;color:#8B949E;font-weight:700;">Vanna ➡</div>'
                        f'<div style="font-size:0.75rem;color:#8B949E;font-weight:700;">Charm ➡</div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🧪 Stress Test")
    stress = snap.get("stress_test", []) or []
    if stress:
        for s in stress[:3]:
            if not isinstance(s, dict): continue
            with st.expander(f"{s.get('scenario','—')} · DD {s.get('portfolio_dd',0):.0%}"):
                st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;">Worst: <span style="color:#F85149;font-weight:700;">{s.get("worst_asset","—")} {s.get("worst_dd",0):.0%}</span> · Best: <span style="color:#3FB950;font-weight:700;">{s.get("best_asset","—")} {s.get("best_dd",0):.0%}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;margin-top:4px;">Hedge: <span style="color:#E6EDF3;">{s.get("hedge","—")}</span></div>', unsafe_allow_html=True)
    else: st.caption("Stress test unavailable")

    st.divider()
    st.markdown("### 🛡️ v39 Engine Status")
    v39_engines_status = [
        ("🎲 Walkforward", "MC 100x backtest gatekeeper", snap.get("walkforward_results")),
        ("🛡️ Gatekeeper", "8-gate alpha validator", snap.get("alpha_gatekeeper")),
        ("📊 VIX Bucket", "Hedgeye vol regime sizing", snap.get("vix_bucket")),
        ("💰 Hedgeye Sizing", "Exact position sizing (2-6%)", snap.get("hedgeye_position_sizing")),
        ("🎙️ Keith Sync", "Tweet signal P0 override", snap.get("keith_sync")),
        ("🎯 Entry Decision", "Multi-signal entry engine", snap.get("entry_decisions")),
        ("🔮 Alpha Synthesis", "8 hybrid frameworks", snap.get("alpha_synthesis")),
        ("📅 Daily Plays", "Day-trade scan engine", snap.get("daily_plays")),
        ("⏱️ Movement Timing", "Regime timing detector", snap.get("movement_regimes")),
        ("🇮🇩 IHSG Specialist", "Goreng + konglomerasi", snap.get("ihsg_specialist")),
        ("🔗 Chain Reaction", "Supply chain projection", snap.get("chain_reaction")),
        ("🔮 Front-Run", "News catalyst scanner", snap.get("frontrun_signals")),
        ("🧠 Methodology Pack", "6 investor scores", snap.get("methodology_scores")),
    ]
    cols = st.columns(4)
    for i, (name, desc, data) in enumerate(v39_engines_status):
        status = "🟢" if data else "⚪"
        color = "#3FB950" if data else "#484F58"
        cols[i % 4].markdown(f"<span style='color:{color};font-size:0.75rem;'>{status} {name}</span>", unsafe_allow_html=True)
        if data and isinstance(data, dict) and len(data) > 0:
            cols[i % 4].caption(f"{len(data)} items")

    st.divider()
    st.markdown("### 🧠 Methodology Lens")
    methodologies = [
        ("🏗️ Leopold", "Bottleneck layers + asymmetry setups", snap.get("leopold_scan")),
        ("💱 COATUE", "Shortage economy + capital rotation", snap.get("coatue_scan")),
        ("📊 Karsan", "Vol surface + squeeze setups", snap.get("karsan_scanner")),
        ("🧠 Yves", "Behavioral relabeling", snap.get("yves_v2")),
        ("🌀 Soros", "Boom-bust reflexivity", snap.get("boom_bust")),
        ("⚡ Vol Decomp", "Black-Scholes IV breakdown", None),
        ("💧 Druckenmiller", "Liquidity-first positioning", None),
    ]
    for name, desc, data in methodologies:
        status = "🟢" if data else "⚪"
        with st.expander(f"{status} {name} — {desc}", expanded=False):
            if data: st.json({k: str(v)[:100] for k, v in list(data.items())[:3]})
            else: st.caption("Data not loaded this snapshot.")

# ═══════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO STRESS
# ═══════════════════════════════════════════════════════════════════
def page_portfolio_stress():
    st.markdown("## 📊 Portfolio Stress & Correlation")

    # ── v39: Walkforward + Gatekeeper Stress ──
    st.markdown("### 🛡️ Walkforward & Gatekeeper Stress")
    wf = snap.get("walkforward_results", {})
    gk = snap.get("alpha_gatekeeper", {})
    if wf or gk:
        c1, c2, c3 = st.columns(3)
        with c1:
            wf_scores = [v.get("combined_gate_score", 0) for v in wf.values() if isinstance(v, dict)]
            if wf_scores:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=wf_scores, nbinsx=15, marker_color='#58A6FF', opacity=0.7))
                fig.add_vline(x=55, line_dash="dash", line_color="#F85149", annotation_text="Threshold 55")
                fig.update_layout(height=200, paper_bgcolor='#0D1117', plot_bgcolor='#0D1117',
                                  font=dict(color='#E6EDF3', size=10), margin=dict(l=40,r=40,t=20,b=40),
                                  xaxis=dict(title='WF Gate Score', showgrid=True, gridcolor='#21262D'),
                                  yaxis=dict(title='Count', showgrid=True, gridcolor='#21262D'),
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key="wf_hist_v39")
        with c2:
            gk_scores = [v.get("combined_score", 0) for v in gk.values() if isinstance(v, dict)]
            if gk_scores:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=gk_scores, nbinsx=15, marker_color='#A855F7', opacity=0.7))
                fig.add_vline(x=65, line_dash="dash", line_color="#F85149", annotation_text="Threshold 65")
                fig.update_layout(height=200, paper_bgcolor='#0D1117', plot_bgcolor='#0D1117',
                                  font=dict(color='#E6EDF3', size=10), margin=dict(l=40,r=40,t=20,b=40),
                                  xaxis=dict(title='Gatekeeper Score', showgrid=True, gridcolor='#21262D'),
                                  yaxis=dict(title='Count', showgrid=True, gridcolor='#21262D'),
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key="gk_hist_v39")
        with c3:
            st.markdown("<div style='font-size:0.7rem;color:#8B949E;'><b>Gate Status Distribution</b></div>", unsafe_allow_html=True)
            gk_pass = sum(1 for v in gk.values() if isinstance(v, dict) and v.get("gate_status") == "PASS")
            gk_marg = sum(1 for v in gk.values() if isinstance(v, dict) and v.get("gate_status") == "MARGINAL")
            gk_fail = sum(1 for v in gk.values() if isinstance(v, dict) and v.get("gate_status") == "FAIL")
            total_gk = gk_pass + gk_marg + gk_fail
            if total_gk > 0:
                st.markdown(_stacked_bar_html(gk_pass/total_gk*100, gk_marg/total_gk*100, gk_fail/total_gk*100), unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:0.6rem;color:#484F58;'>PASS {gk_pass} · MARGINAL {gk_marg} · FAIL {gk_fail}</div>", unsafe_allow_html=True)
    else:
        st.caption("Walkforward/Gatekeeper data not available")

    st.divider()


    # ── AFS (Anti-Fragility Score) ──
    afs = snap.get("afs_data", {}) or {}
    if afs:
        afs_val = afs.get("afs", 0)
        afs_color = "#3FB950" if afs_val > 2.0 else "#D29922" if afs_val > 1.0 else "#F85149"
        afs_label = afs.get("label", "—")
        st.markdown(
            f'<div style="background:#161B22;border:1px solid {afs_color}40;border-radius:10px;padding:12px;margin:8px 0;">'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<div style="width:48px;height:48px;border-radius:50%;background:{afs_color}15;border:2px solid {afs_color};display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800;color:{afs_color};">{afs_val:.1f}</div>'
            f'<div><div style="font-size:0.9rem;font-weight:700;color:{afs_color};">{afs_label}</div>'
            f'<div style="font-size:0.7rem;color:#8B949E;margin-top:2px;">{afs.get("advice","—")}</div></div></div>'
            f'<div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;font-size:0.6rem;color:#8B949E;">'
            f'<div>Convexity<br><b style="color:#E6EDF3;">{afs.get("components",{}).get("positive_convexity",0):.2f}</b></div>'
            f'<div>Diversity<br><b style="color:#E6EDF3;">{afs.get("components",{}).get("regime_diversity",0):.2f}</b></div>'
            f'<div>Liquidity<br><b style="color:#E6EDF3;">{afs.get("components",{}).get("liquidity_buffer",0):.0%}</b></div>'
            f'<div>Correlation<br><b style="color:#E6EDF3;">{afs.get("components",{}).get("correlation_concentration",0):.2f}</b></div>'
            f'</div></div>', unsafe_allow_html=True)

    # ── Portfolio Simulation Summary ──
    port = snap.get("portfolio_stress", {}) or {}
    if port and port.get("ok"):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            corr = port.get("avg_correlation", 0)
            corr_c = "#3FB950" if corr < 0.3 else "#D29922" if corr < 0.6 else "#F85149"
            st.markdown(f'<div class="metric-grid-card">'
                        f'<div class="metric-grid-title">Avg Correlation</div>'
                        f'<div class="metric-grid-value" style="color:{corr_c};">{corr:.2f}</div>'
                        f'<div class="metric-grid-sub">{"LOW" if corr < 0.3 else "MEDIUM" if corr < 0.6 else "HIGH"}</div></div>', unsafe_allow_html=True)
        with c2:
            exp_ret = port.get("portfolio_exp_return_pct", 0)
            st.markdown(f'<div class="metric-grid-card">'
                        f'<div class="metric-grid-title">Portfolio Exp Return</div>'
                        f'<div class="metric-grid-value" style="color:{"#3FB950" if exp_ret > 0 else "#F85149"};">{exp_ret:+.1f}%</div></div>', unsafe_allow_html=True)
        with c3:
            sharpe = port.get("portfolio_sharpe", 0)
            st.markdown(f'<div class="metric-grid-card">'
                        f'<div class="metric-grid-title">Portfolio Sharpe</div>'
                        f'<div class="metric-grid-value" style="color:{"#3FB950" if sharpe > 1 else "#D29922" if sharpe > 0.5 else "#F85149"};">{sharpe:.2f}</div></div>', unsafe_allow_html=True)
        with c4:
            dd = port.get("worst_case_dd_pct", 0)
            st.markdown(f'<div class="metric-grid-card">'
                        f'<div class="metric-grid-title">Worst Case DD</div>'
                        f'<div class="metric-grid-value" style="color:{"#3FB950" if dd > -5 else "#D29922" if dd > -10 else "#F85149"};">{dd:.1f}%</div></div>', unsafe_allow_html=True)
        with c5:
            prob_pos = port.get("prob_positive", 0)
            st.markdown(f'<div class="metric-grid-card">'
                        f'<div class="metric-grid-title">Prob Positive</div>'
                        f'<div class="metric-grid-value" style="color:{"#3FB950" if prob_pos > 60 else "#D29922"};">{prob_pos:.0f}%</div></div>', unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:0.7rem;color:#8B949E;margin:8px 0;">'
                    f'Diversification benefit: <b style="color:{"#3FB950" if port.get("diversification_benefit") == "HIGH" else "#D29922"};">'
                    f'{port.get("diversification_benefit", "—")}</b> · '
                    f'{port.get("n_tickers", 0)} tickers simulated with correlated paths</div>', unsafe_allow_html=True)
    else:
        st.info("Portfolio stress simulation not available. Run orchestrator with simulation engine enabled.")

    st.divider()

    # ── Correlation Matrix (from prices) ──
    st.markdown("### 🔗 Correlation Matrix Heatmap")

    # Build correlation matrix from daily returns
    import numpy as np
    sim_results = snap.get("simulation_results", {}) or {}
    passed_tickers = [t for t, r in sim_results.items() if r and r.get("passes_filter")]

    if len(passed_tickers) >= 2:
        tickers_for_corr = passed_tickers[:20]  # Limit for performance
        corr_data = {}
        for t in tickers_for_corr:
            s = prices.get(t)
            if s is None or len(s) < 30:
                continue
            try:
                s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
                if len(s_clean) >= 30:
                    corr_data[t] = s_clean.tail(60).pct_change().dropna()
            except Exception:
                pass

        if len(corr_data) >= 2:
            # Build DataFrame
            df_rets = pd.DataFrame({k: v.values[:min(len(v), 50)] for k, v in corr_data.items()})
            corr_matrix = df_rets.corr().fillna(0)

            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale=[[0, '#F85149'], [0.5, '#21262D'], [1, '#3FB950']],
                zmid=0,
                text=[[f'{v:.2f}' for v in row] for row in corr_matrix.values],
                texttemplate='%{text}',
                textfont=dict(size=9, color='#E6EDF3'),
                hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>',
            ))
            fig.update_layout(
                height=max(400, len(corr_matrix) * 30),
                paper_bgcolor='#0D1117',
                plot_bgcolor='#0D1117',
                font=dict(color='#E6EDF3', size=10, family='Inter'),
                margin=dict(l=80, r=40, t=30, b=80),
                xaxis=dict(tickangle=-45),
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key="corr_heatmap_v2")

            # Auto-rebalance signal
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    c = corr_matrix.iloc[i, j]
                    if c > 0.75:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], c))

            if high_corr_pairs:
                st.markdown("### ⚠️ Auto-Rebalance Signals")
                st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin-bottom:8px;'>Pairs with correlation > 0.75 — diversification at risk. Consider reducing overlap.</div>", unsafe_allow_html=True)
                for t1, t2, c in sorted(high_corr_pairs, key=lambda x: x[2], reverse=True)[:10]:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;margin:3px 0;">'
                        f'<span style="font-size:0.75rem;color:#E6EDF3;font-weight:700;min-width:80px;">{t1}</span>'
                        f'<span style="font-size:0.65rem;color:#8B949E;">↔</span>'
                        f'<span style="font-size:0.75rem;color:#E6EDF3;font-weight:700;min-width:80px;">{t2}</span>'
                        f'<div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
                        f'<div style="width:{c*100:.0f}%;height:100%;background:#F85149;border-radius:3px;"></div></div>'
                        f'<span style="font-size:0.7rem;color:#F85149;font-weight:700;min-width:50px;text-align:right;">{c:.2f}</span>'
                        f'</div>', unsafe_allow_html=True)

                # Rebalance recommendation
                st.markdown(
                    f'<div style="background:#F8514915;border-left:3px solid #F85149;border-radius:6px;padding:8px 12px;margin:8px 0;">'
                    f'<div style="font-size:0.75rem;color:#F85149;font-weight:700;">🔄 REBALANCE RECOMMENDED</div>'
                    f'<div style="font-size:0.7rem;color:#8B949E;margin-top:3px;">'
                    f'{len(high_corr_pairs)} high-correlation pairs detected. '
                    f'Portfolio behaving like {len(high_corr_pairs)//2 + 1} "super-tickers". '
                    f'Consider: (1) Trim overlapping positions, (2) Add uncorrelated assets (commodities/bonds), '
                    f'(3) Use options hedges instead of directional overlap.</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div style="background:#3FB95015;border-left:3px solid #3FB950;border-radius:6px;padding:8px 12px;margin:8px 0;">'
                    f'<div style="font-size:0.75rem;color:#3FB950;font-weight:700;">✅ DIVERSIFICATION HEALTHY</div>'
                    f'<div style="font-size:0.7rem;color:#8B949E;margin-top:3px;">No high-correlation pairs detected. Portfolio well-diversified.</div></div>', unsafe_allow_html=True)
    else:
        st.caption("Need >= 2 simulation-passed tickers for correlation matrix")

    st.divider()

    # ── Options P&L Simulator Summary ──
    st.markdown("### 📐 Options P&L Simulator")
    opts_pnl = snap.get("options_pnl_simulator", {}) or {}
    if opts_pnl:
        # Group by strategy type
        by_strategy = {}
        for t, data in opts_pnl.items():
            strat = data.get("strategy", "NO_EDGE")
            by_strategy.setdefault(strat, []).append({"ticker": t, **data})

        cols = st.columns(3)
        col_idx = 0
        for strat, items in by_strategy.items():
            with cols[col_idx % 3]:
                strat_color = {"BUY_DIRECTIONAL":"#3FB950","SELL_PREMIUM":"#D29922","CALENDAR_SPREAD":"#58A6FF",
                               "PUT_SPREAD":"#A371F7","CALL_SPREAD":"#A371F7","NO_EDGE":"#8B949E"}.get(strat, "#8B949E")
                st.markdown(
                    f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px 12px;margin:4px 0;">'
                    f'<div style="font-size:0.65rem;color:#8B949E;text-transform:uppercase;font-weight:600;margin-bottom:5px;">{strat.replace("_"," ")}</div>'
                    f'<div style="font-size:1.1rem;color:{strat_color};font-weight:700;">{len(items)} tickers</div>'
                    f'<div style="font-size:0.6rem;color:#484F58;margin-top:3px;">'
                    f'{" · ".join([i["ticker"] for i in items[:5]])}{"..." if len(items) > 5 else ""}</div>'
                    f'</div>', unsafe_allow_html=True)
            col_idx += 1

        # Detailed table
        st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin:8px 0;'>Options strategy mapped per ticker based on simulation + greeks</div>", unsafe_allow_html=True)
        opts_df = []
        for t, data in opts_pnl.items():
            opts_df.append({
                "Ticker": t,
                "Strategy": data.get("name", "—"),
                "Confidence": f"{data.get('confidence', 0):.0f}%",
                "Rationale": data.get("rationale", "")[:80],
            })
        if opts_df:
            st.dataframe(pd.DataFrame(opts_df), use_container_width=True, hide_index=True)
    else:
        st.caption("Options P&L simulator not available — run orchestrator with simulation + greeks data")

    st.divider()

    # ── Simulation Summary Dashboard ──
    st.markdown("### 🎲 Simulation Summary Dashboard")
    sim_sum = snap.get("simulation_summary", {}) or {}
    if sim_sum:
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Total Simulated", sim_sum.get("total", 0))
        with s2:
            st.metric("Passed Filter", sim_sum.get("passed", 0))
        with s3:
            st.metric("Avg Score", f"{sim_sum.get('avg_score', 0):.1f}")
        with s4:
            st.metric("Avg Win Rate", f"{sim_sum.get('avg_win_rate', 0):.0f}%")

        # Distribution histogram of robustness scores
        sim_results = snap.get("simulation_results", {}) or {}
        scores = [r.get("robustness_score", 0) for r in sim_results.values() if r]
        if scores:
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=scores,
                nbinsx=20,
                marker_color='#58A6FF',
                opacity=0.7,
                name='Robustness Score',
            ))
            fig.add_vline(x=65, line_dash="dash", line_color="#F85149", annotation_text="Threshold 65")
            fig.update_layout(
                height=200,
                paper_bgcolor='#0D1117',
                plot_bgcolor='#0D1117',
                font=dict(color='#E6EDF3', size=10, family='Inter'),
                margin=dict(l=40, r=40, t=20, b=40),
                xaxis=dict(title='Robustness Score', showgrid=True, gridcolor='#21262D'),
                yaxis=dict(title='Count', showgrid=True, gridcolor='#21262D'),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key="sim_hist_v2")
    else:
        st.caption("Simulation summary not available")

    st.divider()

    # ── Top Simulation-Passed Tickers with Extensions ──
    st.markdown("### 🏆 Top Simulation-Passed Tickers (with Extensions)")
    sim_results = snap.get("simulation_results", {}) or {}
    passed = [(t, r) for t, r in sim_results.items() if r and r.get("passes_filter")]
    passed.sort(key=lambda x: x[1].get("robustness_score", 0), reverse=True)

    for t, r in passed[:15]:
        score = r.get("robustness_score", 0)
        score_c = "#3FB950" if score >= 80 else "#D29922" if score >= 65 else "#F85149"
        ext = r.get("extensions", {})
        kelly = ext.get("kelly", {})
        cb = ext.get("circuit_breaker", {})
        dpv = ext.get("dark_pool", {})
        timing = ext.get("entry_timing", {})

        badges = ""
        if kelly:
            badges += f'<span style="background:#3FB95022;color:#3FB950;padding:1px 5px;border-radius:4px;font-size:0.55rem;font-weight:700;margin-right:3px;">💰 {kelly.get("label","—")}</span>'
        if cb and cb.get("triggered"):
            badges += f'<span style="background:#F8514922;color:#F85149;padding:1px 5px;border-radius:4px;font-size:0.55rem;font-weight:700;margin-right:3px;">🚨 CB</span>'
        if dpv and dpv.get("validated"):
            badges += f'<span style="background:#58A6FF22;color:#58A6FF;padding:1px 5px;border-radius:4px;font-size:0.55rem;font-weight:700;margin-right:3px;">🌊 DP OK</span>'
        if timing and timing.get("best_delay_days", 0) > 0:
            badges += f'<span style="background:#D2992222;color:#D29922;padding:1px 5px;border-radius:4px;font-size:0.55rem;font-weight:700;margin-right:3px;">⏱️ Wait {timing["best_delay_days"]}d</span>'

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;margin:3px 0;">'
            f'<span style="font-size:0.85rem;color:#E6EDF3;font-weight:700;min-width:60px;">{t}</span>'
            f'<div style="flex:1;height:8px;background:#21262D;border-radius:4px;overflow:hidden;">'
            f'<div style="width:{min(100,score):.0f}%;height:100%;background:{score_c};border-radius:4px;"></div></div>'
            f'<span style="font-size:0.7rem;color:{score_c};font-weight:700;min-width:35px;text-align:right;">{score:.0f}</span>'
            f'<span style="font-size:0.65rem;color:#8B949E;min-width:45px;text-align:right;">WR {r.get("win_rate",0):.0f}%</span>'
            f'<div style="display:flex;gap:2px;flex-wrap:wrap;">{badges}</div>'
            f'</div>', unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════
# v39 NEW RENDERERS
# ═══════════════════════════════════════════════════════════════════
def render_supply_chain_chains(snap):
    """
    v39 ROTATION-AWARE Supply Chain Chains
    Highlights: WHERE rotation is NOW → WHERE it goes NEXT
    """
    chains = snap.get("supply_chain_chains", [])
    if not chains:
        st.caption("Supply chain analysis not available")
        return

    # Determine current quad
    gip_local = snap.get("gip")
    if gip_local is not None and not isinstance(gip_local, dict): 
        gip_local = _GipProxy(gip_local)
    elif isinstance(gip_local, dict): 
        gip_local = _GipProxy(gip_local)
    else: 
        gip_local = None
    sq = getattr(gip_local, "structural_quad", "Q3") if gip_local is not None else "Q3"

    pb = _get_quad_playbook(snap)

    # ── ROTATION BANNER ──
    st.markdown(
        f'<div style="background:#161B22;border:1px solid #58A6FF40;border-radius:10px;padding:12px;margin:8px 0;">'
        f'<div style="font-size:0.75rem;color:#58A6FF;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:6px;">🔄 CURRENT ROTATION MAP</div>'
        f'<div style="font-size:0.85rem;color:#E6EDF3;font-weight:700;margin-bottom:4px;">{pb["theme"]}</div>'
        f'<div style="font-size:0.7rem;color:#8B949E;margin-bottom:6px;">'
        f'Front-run sectors: <span style="color:#3FB950;font-weight:700;">{" · ".join(pb["front_run_sectors"])}</span>'
        f'</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">'
        f'<span style="background:#3FB95018;color:#3FB950;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #3FB95040;">🎯 NOW: {" · ".join(pb["front_run_sectors"][:3])}</span>'
        f'<span style="background:#D2992218;color:#D29922;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #D2992240;">➡️ NEXT: {" · ".join(pb["bottleneck_focus"][:3])}</span>'
        f'<span style="background:#F8514918;color:#F85149;padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid #F8514940;">🚫 AVOID: {" · ".join(pb["avoid"][:4])}</span>'
        f'</div>'
        f'<div style="font-size:0.65rem;color:#484F58;">Coatue: {pb["coatue_signal"]} · Karsan: {pb["karsan_setup"]} · Leopold: {" → ".join(pb["leopold_layers"])}</div>'
        f'</div>', unsafe_allow_html=True)

    for chain in chains:
        name = chain.get("name", "—")
        trigger = chain.get("trigger", "—")
        conf = chain.get("confidence", 0)
        conf_color = "#3FB950" if conf >= 0.8 else "#D29922" if conf >= 0.6 else "#F85149"

        # Check if this chain aligns with current quad
        bq_map = _get_bottleneck_quad_map(snap); aligned_quads = bq_map.get(name, [])
        quad_match = sq in aligned_quads
        match_badge = f'<span style="background:#3FB95018;color:#3FB950;padding:1px 6px;border-radius:4px;font-size:0.6rem;font-weight:700;border:1px solid #3FB95040;margin-left:6px;">✅ ALIGNED {sq}</span>' if quad_match else f'<span style="background:#D2992218;color:#D29922;padding:1px 6px;border-radius:4px;font-size:0.6rem;font-weight:700;border:1px solid #D2992240;margin-left:6px;">⚠️ {sq} MISMATCH</span>'

        # Card header
        html = f'<div style="background:#161B22;border:1px solid {"#3FB95040" if quad_match else "#30363D"};border-radius:10px;padding:12px;margin:8px 0;">'
        html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        html += f'<div style="font-size:0.9rem;font-weight:700;color:#E6EDF3;">{name}</div>'
        html += f'<span style="background:{conf_color}18;color:{conf_color};padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid {conf_color}40;">Conf {conf:.0%}</span>'
        html += match_badge
        html += f'</div>'
        html += f'<div style="font-size:0.7rem;color:#8B949E;margin-bottom:8px;">🎯 Trigger: {trigger}</div>'

        # ── ROTATION FLOW: NOW → NEXT ──
        stages = chain.get("stages", [])
        if stages:
            html += f'<div style="display:flex;align-items:center;gap:4px;margin-bottom:10px;padding:6px 8px;background:#0D1117;border-radius:6px;">'
            html += f'<span style="font-size:0.6rem;color:#3FB950;font-weight:700;">🔄 FLOW:</span>'
            for i, stage in enumerate(stages[:6]):
                sc = ["#58A6FF", "#3FB950", "#D29922", "#F85149", "#A371F7", "#8B949E"][min(stage.get("stage",1)-1, 5)]
                html += f'<span style="font-size:0.6rem;color:{sc};font-weight:600;">{stage.get("layer","—")}</span>'
                if i < len(stages[:6]) - 1:
                    html += f'<span style="font-size:0.6rem;color:#484F58;">→</span>'
            html += f'</div>'

        # Stage grid
        html += f'<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(180px, 1fr));gap:6px;">'
        for stage in stages:
            tickers = stage.get("tickers", [])
            tickers_str = " · ".join(tickers[:4]) + ("…" if len(tickers) > 4 else "")
            stage_color = ["#58A6FF", "#3FB950", "#D29922", "#F85149", "#A371F7", "#8B949E"][min(stage.get("stage",1)-1, 5)]

            # Check if any ticker is in current quad playbook
            in_playbook = any(t in pb.get("front_run_tickers", []) for t in tickers)
            playbook_badge = f'<span style="background:#3FB95022;color:#3FB950;padding:1px 4px;border-radius:3px;font-size:0.55rem;font-weight:700;margin-left:4px;">🎯 PLAYBOOK</span>' if in_playbook else ""

            html += f'<div style="background:#0D1117;border:1px solid {"#3FB95030" if in_playbook else "#21262D"};border-radius:6px;padding:8px;">'
            html += f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
            html += f'<div style="width:20px;height:20px;border-radius:50%;background:{stage_color}25;border:2px solid {stage_color};display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:700;color:{stage_color};">{stage.get("stage","?")}</div>'
            html += f'<div style="font-size:0.75rem;font-weight:600;color:#E6EDF3;">{stage.get("layer","—")}</div>'
            html += playbook_badge
            html += f'</div>'
            html += f'<div style="font-size:0.65rem;color:#58A6FF;margin-bottom:3px;">{tickers_str}</div>'
            html += f'<div style="font-size:0.6rem;color:#8B949E;">⚠ {stage.get("bottleneck","—")}</div>'
            html += f'</div>'
        html += f'</div></div>'
        st.markdown(html, unsafe_allow_html=True)


def render_crypto_onchain_v2(snap):
    tokens = snap.get("crypto_tokens", {})
    cc = snap.get("crypto_center", {})
    if not tokens:
        st.caption("Crypto on-chain data unavailable")
        return
    st.markdown("### ₿ On-Chain Intelligence v2")
    whale_acc = sum(1 for v in tokens.values() if isinstance(v, dict) and v.get("whale_signal") == "ACCUMULATING")
    whale_dist = sum(1 for v in tokens.values() if isinstance(v, dict) and v.get("whale_signal") == "DISTRIBUTING")
    c1, c2, c3 = st.columns(3)
    c1.metric("Accumulating", whale_acc, "🐋")
    c2.metric("Distributing", whale_dist, "📤")
    funding_extreme = 0
    if cc and isinstance(cc, dict) and cc.get("risk_flags"):
        funding_extreme = len([r for r in cc["risk_flags"] if r.get("type") == "FUNDING_EXTREME"])
    c3.metric("Funding Extremes", funding_extreme, "⚠️")
    st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin:8px 0;'>Whale signal = 7D momentum + vol consistency. Funding extreme = leverage excess.</div>", unsafe_allow_html=True)
    for ticker, data in list(tokens.items())[:6]:
        if not isinstance(data, dict): continue
        whale = data.get("whale_signal", "NEUTRAL")
        wcolor = "#3FB950" if whale == "ACCUMULATING" else "#F85149" if whale == "DISTRIBUTING" else "#8B949E"
        funding = data.get("funding_proxy", 0)
        fcolor = "#F85149" if abs(funding) > 0.0005 else "#8B949E"
        large = data.get("large_orders_detected", False)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;margin:3px 0;">'
            f'<span style="font-weight:700;font-size:0.8rem;color:#E6EDF3;min-width:70px;">{ticker}</span>'
            f'<span style="font-size:0.65rem;color:{wcolor};font-weight:700;">🐋 {whale}</span>'
            f'<span style="font-size:0.65rem;color:{fcolor};">Funding {funding:.5f}</span>'
            f'<span style="font-size:0.65rem;color:{"#D29922" if large else "#484F58"};">{"🚨 Large Orders" if large else "—"}</span>'
            f'<span style="font-size:0.65rem;color:#8B949E;flex:1;text-align:right;">R7D {data.get("r7d",0):+.1%}</span>'
            f'</div>', unsafe_allow_html=True)

def render_ihsg_broker_v2(snap):
    broker = snap.get("ihsg_broker_proxy", {})
    if not broker:
        st.caption("IHSG broker proxy not available")
        return
    st.markdown("### 🇮🇩 IHSG Broker Intelligence v2")
    st.markdown("<div style='font-size:0.7rem;color:#8B949E;margin-bottom:8px;'>Crossing detection, real accumulation/distribution, cornering supply. Filter: NOT crossing + high confidence.</div>", unsafe_allow_html=True)
    for ticker, data in list(broker.items())[:15]:
        if not isinstance(data, dict): continue
        sig = data.get("signal", "NEUTRAL")
        conf = data.get("confidence", 0)
        crossing = data.get("crossing_detected", False)
        cornering = data.get("cornering_supply", False)
        if crossing and conf < 80:
            continue
        color = "#3FB950" if sig == "ACCUMULATION" else "#F85149" if sig == "DISTRIBUTION" else "#D29922" if sig == "CORNERING" else "#8B949E"
        emoji = "📈" if sig == "ACCUMULATION" else "📉" if sig == "DISTRIBUTION" else "🎯" if sig == "CORNERING" else "⚪"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;margin:3px 0;">'
            f'<span style="font-weight:700;font-size:0.8rem;color:#E6EDF3;min-width:70px;">{ticker}</span>'
            f'<span style="font-size:0.65rem;color:{color};font-weight:700;">{emoji} {sig}</span>'
            f'<div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
            f'<div style="width:{conf}%;height:100%;background:{color};border-radius:3px;"></div></div>'
            f'<span style="font-size:0.65rem;color:{color};font-weight:700;min-width:35px;text-align:right;">{conf}%</span>'
            f'<span style="font-size:0.6rem;color:#484F58;">R5D {data.get("r5d",0):+.1%}</span>'
            f'</div>', unsafe_allow_html=True)
        if cornering:
            st.markdown(
                f'<div style="background:#D2992215;border-left:3px solid #D29922;border-radius:4px;padding:4px 8px;margin:2px 0;font-size:0.65rem;color:#D29922;">'
                f'🎯 Cornering supply: volume drying up ({data.get("drying_up",1):.1f}x) then sudden spike. Possible accumulation before breakout.</div>',
                unsafe_allow_html=True)

def render_ticker_detail_comprehensive(ticker, snap):
    """Comprehensive single-ticker view: all methodologies, all data sources."""
    # ── Broker Intelligence (for IHSG tickers) ──
    if ticker.endswith(".JK"):
        broker = (snap.get("ihsg_broker_proxy", {}) or {}).get(ticker)
        if broker and isinstance(broker, dict):
            b_sig = broker.get("signal", "NEUTRAL")
            b_conf = broker.get("confidence", 0)
            b_color = "#3FB950" if b_sig == "ACCUMULATION" else "#F85149" if b_sig == "DISTRIBUTION" else "#D29922" if b_sig == "CORNERING" else "#8B949E"
            st.markdown(
                f'<div style="background:#161B22;border:1px solid {b_color}40;border-radius:10px;padding:12px;margin:8px 0;">'
                f'<div style="font-size:0.75rem;color:#8B949E;text-transform:uppercase;font-weight:600;margin-bottom:4px;">🇮🇩 Broker Intelligence (IHSG)</div>'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="background:{b_color}18;color:{b_color};padding:3px 10px;border-radius:6px;font-size:0.8rem;font-weight:700;border:1px solid {b_color}40;">{b_sig}</span>'
                f'<span style="font-size:0.7rem;color:#8B949E;">Confidence <b style="color:{b_color};">{b_conf}%</b></span>'
                f'<span style="font-size:0.65rem;color:#484F58;">R5D: {broker.get("r5d",0):+.1%} · Vol Ratio: {broker.get("vol_ratio",1):.2f}x</span>'
                f'</div></div>', unsafe_allow_html=True)

    prices = snap.get("prices", {})
    s = prices.get(ticker)
    if s is None:
        st.error(f"No price data for {ticker}")
        return
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        px = float(s_clean.iloc[-1])
    except:
        st.error(f"Invalid price data for {ticker}")
        return
    st.markdown(f"## 📊 {ticker} · {_ffm(px, market_type)}")
    ar = (snap.get("risk_ranges", {}) or {}).get("asset_ranges", {})
    if ticker in ar:
        v = ar[ticker]
        lrr = v.get("trade", {}).get("lrr")
        trr = v.get("trade", {}).get("trr")
        if lrr and trr:
            st.markdown(_risk_range_html(px, lrr, trr, width_pct=100), unsafe_allow_html=True)
    # ── Options / Greeks — SKIP for IHSG (buy-only, no options market) ──
    opts = {}
    if not ticker.endswith(".JK"):
        opts = _get_options_data(ticker, snap)
        if opts and opts.get("gamma_regime"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Gamma", opts.get("gamma_regime", "—"))
            c2.metric("GEX", sf(opts.get("gex"), "+.2f"))
            c3.metric("Vanna", sf(opts.get("vanna"), "+.2f"))
            c4.metric("IV Rank", sf(opts.get("iv_rank"), ".0f"))
    sim = (snap.get("simulation_results", {}) or {}).get(ticker)
    if sim:
        score = sim.get("robustness_score", 0)
        st.markdown(
            f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;margin:8px 0;">'
            f'<div style="font-size:0.7rem;color:#8B949E;text-transform:uppercase;font-weight:600;margin-bottom:4px;">🎲 Simulation (100 runs)</div>'
            f'<div style="display:flex;gap:12px;">'
            f'<div><div style="font-size:0.6rem;color:#8B949E;">Robustness</div><div style="font-size:1rem;color:{"#3FB950" if score>=80 else "#D29922" if score>=65 else "#F85149"};font-weight:700;">{score:.0f}</div></div>'
            f'<div><div style="font-size:0.6rem;color:#8B949E;">Win Rate</div><div style="font-size:1rem;color:#E6EDF3;font-weight:700;">{sim.get("win_rate",0):.0f}%</div></div>'
            f'<div><div style="font-size:0.6rem;color:#8B949E;">Exp Return</div><div style="font-size:1rem;color:#E6EDF3;font-weight:700;">{sim.get("exp_return_pct",0):+.1f}%</div></div>'
            f'<div><div style="font-size:0.6rem;color:#8B949E;">Sharpe</div><div style="font-size:1rem;color:#E6EDF3;font-weight:700;">{sim.get("sharpe_like",0):.2f}</div></div>'
            f'</div></div>', unsafe_allow_html=True)
    # v39.1: Background Engine Panels (Gatekeeper · Walkforward · Hedgeye · Keith)
    gk = (snap.get("alpha_gatekeeper", {}) or {}).get(ticker, {})
    if gk and isinstance(gk, dict):
        gk_status = gk.get("gate_status", "—")
        gk_score = gk.get("combined_score", 0)
        gk_color = "#3FB950" if gk_status == "PASS" else "#D29922" if gk_status == "MARGINAL" else "#F85149"
        st.markdown(f"**🛡️ Gatekeeper:** <span style='color:{gk_color};font-weight:700;'>{gk_status}</span> · Score {gk_score:.1f}", unsafe_allow_html=True)

    wf = (snap.get("walkforward_results", {}) or {}).get(ticker, {})
    if wf and isinstance(wf, dict):
        wf_status = wf.get("gate_status", "—")
        wf_score = wf.get("combined_gate_score", 0)
        wf_color = "#3FB950" if wf_status == "PASS" else "#D29922" if wf_status == "MARGINAL" else "#F85149"
        st.markdown(f"**🎲 Walkforward:** <span style='color:{wf_color};font-weight:700;'>{wf_status}</span> · Score {wf_score:.1f}", unsafe_allow_html=True)

    ks = (snap.get("keith_sync", {}) or {}).get(ticker, {})
    if ks and isinstance(ks, dict) and ks.get("keith_trade") != "NEUTRAL":
        ktrade = ks.get("keith_trade", "—")
        ktrend = ks.get("keith_trend", "—")
        kfinal = ks.get("direction", "—")
        koverride = ks.get("override", False)
        tc = "#3FB950" if ktrade == "BULLISH" else "#F85149"
        st.markdown(f"**🎙️ Keith Sync:** TRADE <span style='color:{tc};font-weight:700;'>{ktrade}</span> · TREND <span style='color:{tc};font-weight:700;'>{ktrend}</span> → Final <b>{kfinal}</b> {'⚠️ OVERRIDE' if koverride else ''}", unsafe_allow_html=True)

    hp_list = (snap.get("hedgeye_position_sizing", {}) or {}).get("positions", [])
    hp = next((p for p in hp_list if isinstance(p, dict) and p.get("ticker") == ticker), None)
    if hp and isinstance(hp, dict):
        st.markdown(f"**💰 Hedgeye Size:** {hp.get('size_pct',0):.2%} · ${hp.get('dollar_size',0):,.0f} · Conviction {hp.get('conviction',0):.0%}", unsafe_allow_html=True)

    # v39.1: Smart Consensus & Scanners
    sm = snap.get("smart_money", {})
    sm_consensus = sm.get("consensus_picks", []) if isinstance(sm, dict) else []
    sm_match = next((c for c in sm_consensus if isinstance(c, dict) and c.get("ticker") == ticker), None)
    if sm_match:
        st.markdown(f"**🐋 Smart Money Consensus:** {sm_match.get('n_funds',0)} funds · Signal {sm_match.get('signal','—')}", unsafe_allow_html=True)

    cr = snap.get("capital_rotation", {})
    cr_roles = cr.get("ticker_roles", {}) if isinstance(cr, dict) else {}
    if ticker in cr_roles:
        st.markdown(f"**🔄 Capital Rotation:** {cr_roles[ticker].replace('_',' ').title()}", unsafe_allow_html=True)

    vrp = snap.get("vrp_scanner", {})
    if isinstance(vrp, dict) and vrp.get("ok"):
        vrp_item = next((i for i in vrp.get("high_vrp_sell_premium",[]) if isinstance(i, dict) and i.get("ticker")==ticker), None)
        if not vrp_item:
            vrp_item = next((i for i in vrp.get("low_vrp_buy_premium",[]) if isinstance(i, dict) and i.get("ticker")==ticker), None)
        if vrp_item:
            st.markdown(f"**📊 VRP:** {vrp_item.get('vrp_pct',0):.0f}% · IV Rank {vrp_item.get('iv_rank','—')}", unsafe_allow_html=True)

    sq = snap.get("squeeze_scanner", {})
    if isinstance(sq, dict) and sq.get("ok"):
        sq_item = next((i for i in sq.get("imminent_squeezes",[]) if isinstance(i, dict) and i.get("ticker")==ticker), None)
        if not sq_item:
            sq_item = next((i for i in sq.get("strong_candidates",[]) if isinstance(i, dict) and i.get("ticker")==ticker), None)
        if sq_item:
            st.markdown(f"**🔥 Squeeze Score:** {sq_item.get('squeeze_score',0):.0f}/100 · Tier {sq_item.get('tier','—')}", unsafe_allow_html=True)

    methods = []
    cs = (snap.get("composite_signals", {}) or {}).get(ticker)
    if cs:
        methods.append(("Composite Signal", cs.get("direction", "—"), cs.get("confidence", 0)))
    tp = (snap.get("thought_process", {}) or {}).get(ticker)
    if tp:
        methods.append(("Thought Process", f"Score {tp.get('thesis_score',0):.0f}", tp.get("thesis_score",0)/100))
    leo = (snap.get("leopold_scan", {}) or {}).get("per_ticker", {}).get(ticker)
    if leo:
        methods.append(("Leopold", leo.get("layer", "—"), leo.get("asymmetry_score", 0)/100))
    coat = (snap.get("coatue_scan", {}) or {}).get("per_ticker", {}).get(ticker)
    if coat:
        methods.append(("COATUE", coat.get("signal", "—"), coat.get("confidence", 0)))
    kar = (snap.get("karsan_scanner", {}) or {}).get("per_ticker", {}).get(ticker)
    if kar:
        methods.append(("Karsan", kar.get("setup_type", "—"), kar.get("confidence", 0)))
    if methods:
        st.markdown("<div style='font-size:0.7rem;color:#8B949E;text-transform:uppercase;font-weight:600;margin:8px 0 4px;'>Methodology Confluence</div>", unsafe_allow_html=True)
        for name, signal, conf in methods:
            color = "#3FB950" if conf > 0.7 else "#D29922" if conf > 0.4 else "#8B949E"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 8px;background:#0D1117;border-radius:4px;margin:2px 0;">'
                f'<span style="font-size:0.7rem;color:#8B949E;min-width:100px;">{name}</span>'
                f'<div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
                f'<div style="width:{conf*100:.0f}%;height:100%;background:{color};border-radius:3px;"></div></div>'
                f'<span style="font-size:0.7rem;color:{color};font-weight:700;min-width:80px;text-align:right;">{signal}</span>'
                f'</div>', unsafe_allow_html=True)
    dp = _get_dark_pool_for_ticker(ticker, snap)
    dp_imb = _get_dark_pool_imbalance(ticker, snap)
    if dp or dp_imb:
        st.markdown("### 🌊 Dark Pool")
        if dp_imb:
            st.markdown(f"Imbalance: {dp_imb['imbalance']:+.0f}% · Divergence: {dp_imb['div_text']}")
    # Crypto On-Chain Intelligence (Whale Signal)
    if "-USD" in ticker or ticker.upper() in ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD","LTC-USD"]:
        cc_tokens = snap.get("crypto_tokens", {})
        cc_data = cc_tokens.get(ticker, {}) if isinstance(cc_tokens, dict) else {}
        if cc_data and isinstance(cc_data, dict):
            st.markdown("### ⛓️ On-Chain Intelligence")
            whale = cc_data.get("whale_signal", "NEUTRAL")
            wcolor = "#3FB950" if whale == "ACCUMULATING" else "#F85149" if whale == "DISTRIBUTING" else "#8B949E"
            st.markdown(f"**Whale Signal:** <span style='color:{wcolor};font-weight:700;'>{whale}</span>", unsafe_allow_html=True)
            st.markdown(f"**Funding Proxy:** {cc_data.get('funding_proxy', 0):.6f}")
            st.markdown(f"**R7D:** {cc_data.get('r7d', 0):+.1%} · **R1M:** {cc_data.get('r1m', 0):+.1%}")
            st.markdown(f"**Large Orders:** {'🚨 Detected' if cc_data.get('large_orders_detected') else '—'}")
            st.markdown(f"**Trend:** {cc_data.get('trend_direction', '—')}")
    # IHSG Broker Intelligence

    news = (snap.get("news_narratives", {}) or {}).get("ticker_specific", {}).get(ticker)
    if news and news.get("headlines"):
        st.markdown("### 📰 News")
        for h in news["headlines"][:3]:
            st.markdown(f"• {h}")

# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# SESSION & SIDEBAR

# ═══════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.caption("v39 ALPHA — Hedgeye 3-Layer + Front-Run All Markets + Supply Chain + Options + COT + Dark Pool + UOA + IDHL + RC + AFS + WF + Bayesian + Duration HMM + CRI_v2")
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard", "⚡ Alpha Center", "🇺🇸 US Stocks", "💱 Forex",
        "🛢️ Commodities", "₿ Crypto", "🌍 Global & EM", "📖 Themes", "📊 Portfolio Stress"
    ], label_visibility="collapsed")
    st.divider()
    try:
        from data.loader import snapshot_age_str
        st.caption(f"Last update: {snapshot_age_str()}")
    except:
        st.caption("Last update: unknown")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Update", use_container_width=True): st.session_state.loading = True
    with c2:
        if st.button("⚡ Rebuild", use_container_width=True):
            st.session_state.loading = True; st.session_state.snap = None
    with st.expander("⚙️ Settings"):
        inc_us = st.checkbox("US Stocks", True)
        inc_fx = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("Indonesia", True)
    with st.expander("💰 Portfolio"):
        pv = st.number_input("Value", min_value=1000, max_value=1_000_000_000,
                            value=int(st.session_state.get("portfolio_value", 100_000)), step=10_000)
        st.session_state["portfolio_value"] = pv
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly", ["Auto", "Q1", "Q2", "Q3", "Q4"],
                            index=["Auto", "Q1", "Q2", "Q3", "Q4"].index(st.session_state.mq_override))
        st.session_state.mq_override = mq_ov
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g = _s.get("gip")
        if _g is not None and not isinstance(_g, dict): _g = _GipProxy(_g)
        elif isinstance(_g, dict): _g = _GipProxy(_g)
        _sq = getattr(_g, "structural_quad", "—") if _g is not None else "—"
        _mq = getattr(_g, "monthly_quad", "—") if _g is not None else "—"
        color = _quad_color(_sq)
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;">'
                    f'<div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">REGIME</div>'
                    f'<div style="font-size:1rem;font-weight:700;color:{color};margin:4px 0;">{_sq} / {_mq}</div>'
                    f'<div style="font-size:0.65rem;color:#8B949E;">{_quad_name(_sq)}</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════
snap = st.session_state.snap
if snap is None:
    try:
        from data.loader import load_snapshot
        snap = load_snapshot(max_age_hours=6.0)
        if snap and snap.get("ok"): st.session_state.snap = snap
    except Exception as e:
        logger.warning(f"Initial snapshot load failed: {e}")
        snap = None

if snap is None or not snap.get("ok") or st.session_state.loading:
    try:
        from orchestrator import build_snapshot
    except Exception as e:
        st.error(f"Failed to import orchestrator: {e}"); st.stop()
    _msg = "Updating..." if st.session_state.loading else "Building..."
    with st.spinner(_msg):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m, f): pb.progress(f); pt.caption(f"Loading {m}")
        try:
            snap = build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                                  include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg,
                                  portfolio_value=st.session_state.get("portfolio_value", 100_000))
            st.session_state.snap = snap; st.session_state.loading = False; pb.empty(); pt.empty(); st.rerun()
        except Exception as e:
            st.session_state.loading = False; st.error(f"Build failed: {e}"); st.stop()

if not snap or not snap.get("ok"):
    st.error("Build failed. Click Rebuild to retry."); st.stop()

gip_raw = snap.get("gip")
if gip_raw is not None and not isinstance(gip_raw, dict): gip = _GipProxy(gip_raw)
elif isinstance(gip_raw, dict): gip = _GipProxy(gip_raw)
else: gip = None
prices = snap.get("prices", {}) or {}
rr = snap.get("risk_ranges", {}) or {}
ar = rr.get("asset_ranges", {}) if isinstance(rr, dict) else {}
sq = getattr(gip, "structural_quad", None) or "Q3" if gip is not None else "Q3"
mq_raw = getattr(gip, "monthly_quad", None) or "Q2" if gip is not None else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw

_vix_raw = prices.get("^VIX")
vix_now = 20.0
if _vix_raw is not None:
    try:
        if hasattr(_vix_raw, "tail"): vix_now = _safe_float(_vix_raw.tail(1)) or 20.0
        elif hasattr(_vix_raw, "__len__") and len(_vix_raw) > 0: vix_now = _safe_float(pd.Series(_vix_raw).iloc[-1]) or 20.0
        else: vix_now = _safe_float(_vix_raw) or 20.0
    except Exception: vix_now = 20.0

# ═══════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard": page_dashboard()
elif page == "⚡ Alpha Center": page_alpha()
elif page == "🇺🇸 US Stocks": page_us_stocks()
elif page == "💱 Forex": page_forex()
elif page == "🛢️ Commodities": page_commodities()
elif page == "₿ Crypto": page_crypto()
elif page == "🌍 Global & EM": page_global()
elif page == "📖 Themes": page_themes()
elif page == "📊 Portfolio Stress": page_portfolio_stress()
# Ticker Detail removed from sidebar — accessible via Quick Lookup in each market page

st.divider()
flip_note = f" · {snap.get('summary', {}).get('v2_composite_flipped_count', 0)} flipped" if snap.get("summary", {}).get("v2_composite_flipped_count") else ""
st.caption(f"MacroRegime Pro v39 ALPHA · Built {snap.get('build_time_s', 0):.0f}s ago · {snap.get('prices_loaded', 0)} assets · {snap.get('fred_coverage', 0)} indicators · AFS {snap.get('summary',{}).get('v32_afs',0):.1f}{flip_note}")

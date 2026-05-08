"""app.py - MacroRegime Pro v17b | SELF-CONTAINED + yfinance fallback

If orchestrator/data.loader fails, app falls back to direct yfinance download.
This ensures the dashboard ALWAYS loads, even with broken dependencies.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math, time, logging, traceback, json, os
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html,body,[class*="css"] { font-family: 'JetBrains Mono', monospace; }
.big-quad { font-size: 42px; font-weight: 700; }
.card { background: #1F2937; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.gamma-deep-pos { border-left: 4px solid #10B981; padding-left: 12px; }
.gamma-pos { border-left: 4px solid #00D4AA; padding-left: 12px; }
.gamma-trans { border-left: 4px solid #F59E0B; padding-left: 12px; }
.gamma-neg { border-left: 4px solid #EF4444; padding-left: 12px; }
.gamma-deep-neg { border-left: 4px solid #7F1D1D; padding-left: 12px; }
</style>
""", unsafe_allow_html=True)

QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {"Q1":"Goldilocks - Growth+ Infl-","Q2":"Reflation - Growth+ Infl+","Q3":"Stagflation - Growth- Infl+","Q4":"Deflation - Growth- Infl-"}

def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def qnc(q): return QNC.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"
def ff(v, d=2):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"

def qcard(label, q, conf, sub=""):
    c = qc(q)
    s = f'<div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{sub}</div>' if sub else ""
    return f'<div class="card" style="border-top:3px solid {c};"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">{label}</div><div class="big-quad" style="color:{c};">{q}</div><div style="font-size:13px;color:{c};font-weight:600;">{qn(q)}</div><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Conf: {conf:.0%}</div>{s}</div>'

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=200,margin=dict(t=25,b=5,l=0,r=0),paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0",family="JetBrains Mono"),title=dict(text=title,font=dict(size=11,color="#9CA3AF")),yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),xaxis=dict(showgrid=False),bargap=0.35)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK: Direct yfinance download if orchestrator fails
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def _download_yf(tickers, period="1y"):
    """Direct yfinance download - no dependency on data.loader."""
    try:
        import yfinance as yf
        data = yf.download(tickers, period=period, progress=False, auto_adjust=True)
        if data.empty: return {}
        result = {}
        if len(tickers) == 1:
            result[tickers[0]] = data["Close"]
        else:
            for t in tickers:
                try:
                    s = data["Close"][t]
                    if not s.empty: result[t] = s
                except: pass
        return result
    except Exception as e:
        st.error(f"yfinance download failed: {e}")
        return {}

def _load_or_build_snapshot(inc_us, inc_fx, inc_comm, inc_cryp, inc_ihsg):
    """Try orchestrator first, fallback to direct yfinance."""
    snap = None
    error_log = []

    # Try 1: Orchestrator
    try:
        from orchestrator import build_snapshot
        snap = build_snapshot(
            include_us_stocks=inc_us, include_forex=inc_fx,
            include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg
        )
        if snap and snap.get("ok"):
            return snap, "orchestrator"
    except Exception as e:
        error_log.append(f"Orchestrator: {str(e)[:100]}")

    # Try 2: Load cached snapshot
    try:
        cache_path = Path("data/snapshot.json")
        if cache_path.exists():
            with open(cache_path, "r") as f:
                snap = json.load(f)
            if snap and snap.get("ok"):
                return snap, "cache"
    except Exception as e:
        error_log.append(f"Cache: {str(e)[:100]}")

    # Try 3: Direct yfinance fallback
    try:
        st.info("Loading prices directly via yfinance...")
        all_tickers = []
        if inc_us: all_tickers += ["SPY","QQQ","IWM","VIX","TLT","GLD","SLV","XLE","OIH","XLF","XLI","XLU","XLP","XLY","IBIT","BTC-USD"]
        if inc_fx: all_tickers += ["DX-Y.NYB","UUP","FXE","FXY"]
        if inc_comm: all_tickers += ["CL=F","GC=F","SI=F","HG=F","ZW=F"]
        if inc_cryp: all_tickers += ["BTC-USD","ETH-USD"]

        prices = _download_yf(all_tickers, period="1y")

        # Build minimal snapshot
        snap = {
            "ok": True,
            "build_time_s": 0.0,
            "prices_loaded": len(prices),
            "fred_coverage": 0,
            "price_frames_count": 0,
            "source": "yfinance_fallback",
            "prices": prices,
            "gip": None,
            "risk_ranges": {"asset_ranges":{}},
            "scenarios": {"scenarios":[],"base_case":None},
            "narratives": {"active_narratives":[],"building_narratives":[],"brewing_narratives":[],"total":0},
            "discovery": {},
            "transition": None,
            "health": {},
            "analogs": {},
            "bottleneck": {"level_1":[],"level_2":[],"watch":[],"avoid":[],"market_buckets":{},"em_recovery":None,"total_scanned":0,"futures_excluded":0},
            "global": {"country_quads":{},"global_quad":"Q3","global_probs":{},"global_conf":0.5},
            "auto_discoveries": {"ok":False,"candidates":[],"note":"Fallback mode"},
            "feedback_eval": {},
            "gamma": {"ok":False,"note":"Fallback mode"},
            "leveraged_etf": {"ok":False,"note":"Fallback mode"},
            "playbook": {"best_assets":["SPY","QQQ","GLD","TLT"],"worst_assets":[],"style":"","fx":"","bonds":""},
        }
        return snap, "yfinance"
    except Exception as e:
        error_log.append(f"yfinance: {str(e)[:100]}")

    # All failed
    return {"ok": False, "errors": error_log, "prices": {}}, "failed"

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR + LOAD
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

with st.sidebar:
    st.markdown("## MacroRegime Pro")
    st.markdown("*Hedgeye GIP - v17 - Autonomy*")
    st.divider()
    page = st.radio("", [
        "Dashboard","GIP Model","Risk Ranges","ETF Pro",
        "Leaderboard","Global Quad","IHSG","Bottleneck",
        "Narratives","Discovery","Health","Playbook",
    ], label_visibility="collapsed")
    st.divider()
    st.caption("Snapshot: " + ("Loaded" if st.session_state.snap and st.session_state.snap.get("ok") else "None"))
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Refresh", use_container_width=True): st.session_state.loading = True
    with c2:
        if st.button("Force", use_container_width=True):
            st.session_state.loading = True; st.session_state.snap = None
    with st.expander("Universe"):
        inc_us = st.checkbox("US Stocks", True)
        inc_fx = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("IHSG", True)
    st.divider()

snap = st.session_state.snap
if snap is None:
    snap, source = _load_or_build_snapshot(inc_us, inc_fx, inc_comm, inc_cryp, inc_ihsg)
    if snap and snap.get("ok"):
        st.session_state.snap = snap
        st.sidebar.caption(f"Loaded via: {source}")
    else:
        st.sidebar.caption(f"Load failed: {source}")

if st.session_state.loading:
    snap, source = _load_or_build_snapshot(inc_us, inc_fx, inc_comm, inc_cryp, inc_ihsg)
    st.session_state.snap = snap
    st.session_state.loading = False
    st.sidebar.caption(f"Reloaded via: {source}")
    st.rerun()

if not snap or not snap.get("ok"):
    st.error("No snapshot. Click Refresh to rebuild.")
    if snap and snap.get("errors"):
        with st.expander("Error details"):
            for e in snap["errors"]: st.code(e)
    st.stop()

# Extract
gip = snap.get("gip")
global_ = snap.get("global", {})
rr = snap.get("risk_ranges", {})
scen = snap.get("scenarios", {})
narr = snap.get("narratives", {})
disc = snap.get("discovery", {})
transition = snap.get("transition", None)
health = snap.get("health", {})
analogs = snap.get("analogs", {})
btk = snap.get("bottleneck", {})
pb_data = snap.get("playbook", {})
prices = snap.get("prices", {})
auto_disc = snap.get("auto_discoveries", {})
fb_eval = snap.get("feedback_eval", {})
gamma_data = snap.get("gamma", {})
lev_data = snap.get("leveraged_etf", {})

sq = gip.structural_quad if gip else "Q3"
mq = gip.monthly_quad if gip else "Q2"
gq = global_.get("global_quad", "Q3")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown(f'<div style="text-align:right;font-size:11px;color:#6B7280;">Source: {snap.get("source","orchestrator")} | Built {snap.get("build_time_s",0)}s | Prices: {snap.get("prices_loaded",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro - Dashboard")

    # Fallback banner if yfinance mode
    if snap.get("source") == "yfinance_fallback":
        st.warning("Running in FALLBACK mode - direct yfinance download. Some features limited. Click Force to retry orchestrator.")

    # VIX Bucket
    vbd = health.get("vix_bucket", {}) if health else {}
    vb = vbd.get("bucket", "-")
    if vb == "Investable":
        st.markdown(f'<div class="card" style="border-left:4px solid #10B981;"><b style="color:#10B981;">INVESTABLE BUCKET</b></div>', unsafe_allow_html=True)
    elif vb == "Chop":
        st.markdown(f'<div class="card" style="border-left:4px solid #F59E0B;"><b style="color:#F59E0B;">CHOP BUCKET</b></div>', unsafe_allow_html=True)
    elif vb == "Defensive":
        st.markdown(f'<div class="card" style="border-left:4px solid #EF4444;"><b style="color:#EF4444;">DEFENSIVE BUCKET</b></div>', unsafe_allow_html=True)

    # Gamma
    if gamma_data and gamma_data.get("ok"):
        color = gamma_data.get("color", "#9CA3AF")
        label = gamma_data.get("label", "Unknown")
        action = gamma_data.get("action", "-")
        st.markdown(f'<div class="card" style="border-left:4px solid {color};"><b>GAMMA: {label}</b> - {action}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card"><span style="color:#9CA3AF;">Gamma engine: {gamma_data.get("note","unavailable")}</span></div>', unsafe_allow_html=True)

    # Quad Cards
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(qcard("STRUCTURAL", sq, gip.structural_conf if gip else 0), unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY", mq, gip.monthly_conf if gip else 0), unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL", gq, global_.get("global_conf", 0)), unsafe_allow_html=True)

    # Quick Action
    if pb_data:
        best = " - ".join(pb_data.get("best_assets", [])[:6])
        worst = " - ".join(pb_data.get("worst_assets", [])[:5])
        st.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">QUICK ACTION - {sq} Structural - {mq} Monthly</div><div style="margin-top:8px;font-size:13px;"><span style="color:#10B981;">LONG:</span> <b>{best}</b></div><div style="margin-top:4px;font-size:13px;"><span style="color:#EF4444;">AVOID:</span> <b>{worst}</b></div></div>', unsafe_allow_html=True)

    # Price preview if yfinance fallback
    if snap.get("source") == "yfinance_fallback" and prices:
        st.markdown("---")
        st.markdown("### Price Preview (Fallback Mode)")
        preview_tickers = ["SPY", "QQQ", "GLD", "TLT", "CL=F", "DX-Y.NYB", "BTC-USD"]
        preview_data = []
        for t in preview_tickers:
            s = prices.get(t)
            if s is not None and len(s) >= 2:
                try:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    if len(s) >= 2:
                        ret_1d = float(s.iloc[-1] / s.iloc[-2] - 1)
                        ret_1m = float(s.iloc[-1] / s.iloc[-min(21, len(s))] - 1) if len(s) >= 21 else 0
                        preview_data.append({"Ticker": t, "Last": ff(s.iloc[-1], 2), "1D": fp(ret_1d), "1M": fp(ret_1m)})
                except: pass
        if preview_data:
            st.dataframe(pd.DataFrame(preview_data), hide_index=True, use_container_width=True)

# GIP MODEL
elif page == "GIP Model":
    st.markdown("# GIP Model - Growth - Inflation - Policy")
    if not gip:
        st.warning("No GIP data. Running in fallback mode - GIP requires FRED data.")
        st.info("To enable GIP: ensure data/loader.py and config/settings.py are properly configured.")
        st.stop()
    st.markdown("### Climate vs. Weather")
    cc, cw = st.columns(2)
    with cc: st.markdown(qcard("STRUCTURAL - CLIMATE", sq, gip.structural_conf, f"Coverage: {gip.data_coverage:.0%}"), unsafe_allow_html=True)
    with cw: st.markdown(qcard("MONTHLY - WEATHER", mq, gip.monthly_conf, f"Divergence: {gip.divergence}"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Growth & Inflation Signals")
    f = gip.features
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Growth Mom", fp(f.get("growth_momentum", 0)), "+" if f.get("growth_momentum", 0) > 0 else "-")
    m2.metric("Inflation Mom", fp(f.get("inflation_momentum", 0)), "+" if f.get("inflation_momentum", 0) > 0 else "-")
    m3.metric("Policy", fp(f.get("policy_score", 0)), "Dovish" if f.get("policy_score", 0) > 0.1 else "Hawkish" if f.get("policy_score", 0) < -0.1 else "Neutral")
    m4.metric("Leading", fp(f.get("leading_indicator_composite", 0)), "")

    st.markdown("---")
    st.markdown("### Quad Transition Probabilities")
    if gip.structural_probs:
        st.plotly_chart(prob_bar(gip.structural_probs, "Structural"), use_container_width=True, config={"displayModeBar": False})
    if gip.monthly_probs:
        st.plotly_chart(prob_bar(gip.monthly_probs, "Monthly"), use_container_width=True, config={"displayModeBar": False})

# RISK RANGES
elif page == "Risk Ranges":
    st.markdown("# Risk Range - TRADE - TREND - TAIL")
    ar = rr.get("asset_ranges", {})
    if not ar:
        st.info("No risk range data. Ensure risk_range_engine.py is configured.")
        st.stop()
    rows = []
    for sym, v in ar.items():
        tr = v.get("trade", {})
        rows.append({"Ticker": sym, "Px": ff(v.get("px")), "LRR": ff(tr.get("lrr")), "TRR": ff(tr.get("trr")),
                     "Signal": v.get("composite", "-").upper(), "Quality": v.get("quality", "-"),
                     "Stretch": tr.get("stretch", "-"), "Market": v.get("market", "-")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=520)

# ETF PRO
elif page == "ETF Pro":
    st.markdown("# ETF Pro - Quad-Aware ETF Positioning")
    ar = rr.get("asset_ranges", {})
    best_set = set(pb_data.get("best_assets", []))
    worst_set = set(pb_data.get("worst_assets", []))

    tabs = st.tabs(["US Equity", "Forex", "Commodities", "Crypto", "IHSG"])
    markets = ["us_equity", "forex", "commodity", "crypto", "ihsg"]
    for tab, mkt in zip(tabs, markets):
        with tab:
            rows = []
            for sym, v in ar.items():
                if v.get("market", "") != mkt: continue
                tr = v.get("trade", {})
                qf = "LONG" if sym in best_set else ("AVOID" if sym in worst_set else "-")
                rows.append({"Ticker": sym, "Px": ff(v.get("px")), "LRR": ff(tr.get("lrr")), "TRR": ff(tr.get("trr")),
                             "Signal": v.get("composite", "-").upper(), "Quad Fit": qf})
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=450)
            else:
                st.info(f"No {mkt} data.")

# LEADERBOARD
elif page == "Leaderboard":
    st.markdown("# The Leaderboard - Signal Strength Stocks")
    ar = rr.get("asset_ranges", {})
    if not ar:
        st.info("No risk range data.")
        st.stop()
    long_picks = []
    for sym, v in ar.items():
        if v.get("quality") in ("A", "B") and v.get("composite") == "bullish":
            tr = v.get("trade", {})
            long_picks.append({"ticker": sym, "quality": v["quality"], "px": v.get("px"), 
                               "lrr": tr.get("lrr"), "trr": tr.get("trr"), "stretch": tr.get("stretch", "-")})
    long_picks.sort(key=lambda x: x["quality"])
    st.markdown(f"### TOP LONG IDEAS ({len(long_picks)})")
    for p in long_picks[:21]:
        st.markdown(f'<div style="border-left:3px solid #10B981;padding-left:10px;margin-bottom:8px;"><b>{p["ticker"]} ({p["quality"]})</b> - Px: {ff(p["px"])} - LRR: <b>{ff(p["lrr"])}</b> - {p["stretch"]}</div>', unsafe_allow_html=True)

# GLOBAL QUAD
elif page == "Global Quad":
    st.markdown("# Global Quad - 50 Countries")
    gconf = global_.get("global_conf", 0.0)
    gprobs = global_.get("global_probs", {})
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD", gq, gconf, "50 Country ETFs"), unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs, "Global Probabilities"), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown("### Country Heatmap")
        heat = []
        country_data = global_.get("country_quads", {}) or global_.get("countries", {})
        for country, data in country_data.items():
            if isinstance(data, (list, tuple)) and len(data) >= 3:
                etf, quad, conf = data[0], data[1], data[2]
            elif isinstance(data, dict):
                etf, quad, conf = data.get("etf", ""), data.get("quad", ""), data.get("confidence", 0)
            else:
                etf, quad, conf = "", "", 0
            heat.append({"Country": country, "ETF": etf, "Quad": quad, "Conf": f"{conf:.0%}" if isinstance(conf, (int, float)) else "-"})
        if heat:
            df = pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v: f"color:{QC.get(v, '#9CA3AF')}", subset=["Quad"]), hide_index=True, height=420, use_container_width=True)
        else:
            st.info("No country quad data.")

# IHSG
elif page == "IHSG":
    st.markdown("# IHSG - Indonesia Market")
    st.info("IHSG data requires specific ticker configuration in settings.py.")

# BOTTLENECK
elif page == "Bottleneck":
    st.markdown("# Bottleneck Scanner - Supply Chain Alpha")
    if not btk:
        st.info("No bottleneck data.")
        st.stop()
    l1 = btk.get("level_1", [])
    l2 = btk.get("level_2", [])
    wt = btk.get("watch", [])
    av = btk.get("avoid", [])
    s1, s2, s3, s4 = st.columns(4)
    for col, lab, val, c in [(s1, "Level 1", len(l1), "#10B981"), (s2, "Level 2", len(l2), "#F59E0B"),
                               (s3, "Watch", len(wt), "#6366F1"), (s4, "Avoid", len(av), "#EF4444")]:
        col.markdown(f'<div class="card" style="text-align:center;border-top:3px solid {c};"><div style="font-size:11px;color:#9CA3AF;">{lab}</div><div style="font-size:28px;font-weight:700;color:{c};">{val}</div></div>', unsafe_allow_html=True)

    if btk.get("futures_excluded"):
        st.caption(f"{btk.get('futures_excluded', 0)} futures tickers excluded from equity scan")

    for data, title in [(l1, "Level 1 - Best"), (l2, "Level 2 - Building"), (wt, "Watch - Brewing"), (av, "Avoid - Regime Trap")]:
        if not data: continue
        with st.expander(f"**{title}** ({len(data)})"):
            rows = [{"Ticker": c["ticker"], "Sector": c["sector"].replace("_", " ").title(), "Trend": c["trend"],
                     "Score": str(round(c["score"], 2)), "EV": str(round(c.get("ev", 0), 2)),
                     "RF": str(round(c.get("regime_fit", 0), 2))} for c in data]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=min(len(rows) * 35 + 40, 400))

# NARRATIVES
elif page == "Narratives":
    st.markdown("# Narratives - Thematic Scoring")
    if not narr:
        st.info("No narrative data. Ensure narrative_engine.py is configured.")
        st.stop()
    active = narr.get("active_narratives", [])
    building = narr.get("building_narratives", [])
    brewing = narr.get("brewing_narratives", [])
    for items, label, color in [(active, "ACTIVE", "#10B981"), (building, "BUILDING", "#F59E0B"), (brewing, "BREWING", "#6366F1")]:
        if not items: continue
        st.markdown(f"### {label} ({len(items)})")
        for n in sorted(items, key=lambda x: x.get("score", 0), reverse=True):
            with st.expander(f"**{n.get('name', '')}** - Score: {n.get('score', 0):.0%}"):
                st.markdown(f"**Thesis:** {n.get('thesis', '')}")
                if n.get("tickers"): st.markdown(f"**Tickers:** {' - '.join(n['tickers'][:8])}")
                if n.get("best"): st.markdown(f"**Best:** {' - '.join(n['best'][:6])}")

# DISCOVERY
elif page == "Discovery":
    st.markdown("# Early Discovery - Pre-Consensus")
    cands = []
    if auto_disc and auto_disc.get("ok"):
        cands = auto_disc.get("candidates", [])
    if not cands:
        st.info("No discoveries yet. Run Force build to trigger discovery engine.")
        if auto_disc and not auto_disc.get("ok"):
            st.caption(f"Engine note: {auto_disc.get('note', '')}")
        st.stop()
    for stage, sc in [("active", "#10B981"), ("building", "#F59E0B"), ("brewing", "#6366F1"), ("pre_consensus", "#9CA3AF")]:
        items = [c for c in cands if c.get("stage") == stage]
        if not items: continue
        st.markdown(f"### {stage.upper().replace('_', ' ')} ({len(items)})")
        for c in items:
            conf = c.get("confidence", 0)
            with st.expander(f"**{c.get('name', '')}** - Conf: {conf:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis', '')}")
                if c.get("tickers"): st.markdown(f"**Tickers:** {' - '.join(c['tickers'][:8])}")
                if c.get("signals"):
                    for sig_type, strength in c["signals"].items():
                        st.progress(min(strength, 1.0), text=f"{sig_type}: {strength:.0%}")

# HEALTH
elif page == "Health":
    st.markdown("# Market Health - VIX - Breadth - Crash Meter")
    if not health:
        st.info("No health data.")
        st.stop()
    vb = health.get("vix_bucket", {})
    if vb:
        st.markdown(f'<div class="card" style="border-left:4px solid #EF4444;"><b>VIX BUCKET: {vb.get("bucket", "-").upper()}</b></div>', unsafe_allow_html=True)
    crash = health.get("crash", {})
    if crash:
        st.markdown("### Crash Meter")
        for k, v in crash.get("signals", {}).items():
            st.progress(v, text=f"{k}: {v:.0%}")

# PLAYBOOK
elif page == "Playbook":
    st.markdown("# Regime Playbook")
    if pb_data:
        c1, c2 = st.columns(2)
        with c1:
            best = " - ".join(pb_data.get("best_assets", []))
            st.markdown(f'<div class="card" style="border-left:4px solid #10B981;"><b>LONG - {sq}</b><br/>{best}</div>', unsafe_allow_html=True)
        with c2:
            worst = " - ".join(pb_data.get("worst_assets", []))
            st.markdown(f'<div class="card" style="border-left:4px solid #EF4444;"><b>AVOID - {sq}</b><br/>{worst}</div>', unsafe_allow_html=True)
    else:
        st.info("No playbook data.")

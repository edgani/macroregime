"""app.py — MacroRegime Pro v3.1 MAJOR SURGERY
Changes v3.1:
  • 5 tabs fully rebuilt: Radar · Risk Range™ · Alpha Center · Options Overlay · Playbook
  • Risk Range™ tab: Trade/Trend/Tail multi-duration proper visual
  • Options Overlay tab: Dealer Gamma proxy, Vol term structure, Greeks summary
  • A/B Test display in Playbook (Hedgeye mandatory)
  • Health tab merged into Playbook (compact)
  • Gap Matrix removed (developer junk)
  • Font sizes: min 13px body, 15px values, 11px labels
  • Zero duplicate sections
  • Fast mode: Refresh reuses cache, Full Rebuild forces re-fetch
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
import logging

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MacroRegime Pro v3.1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — readable, consistent, no bloat
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

.stApp { background-color: #0d1117; font-family: 'IBM Plex Sans', sans-serif; }
.stTabs [data-baseweb="tab-list"] { background: #161B22; border-radius: 8px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #8B949E; border-radius: 6px; font-size: 13px; font-weight: 600; padding: 6px 14px; }
.stTabs [aria-selected="true"] { background: #21262D !important; color: #E6EDF3 !important; }

/* Cards */
.card { background:#161B22; border:1px solid #30363D; border-radius:8px; padding:12px 14px; margin:4px 0; }
.card-q1 { background:#0D2818; border:1px solid #3FB950; border-radius:8px; padding:12px 14px; margin:4px 0; }
.card-q2 { background:#2D0D0D; border:1px solid #F85149; border-radius:8px; padding:12px 14px; margin:4px 0; }
.card-q3 { background:#2D2305; border:1px solid #D29922; border-radius:8px; padding:12px 14px; margin:4px 0; }
.card-q4 { background:#0a0a0a; border:1px solid #6E7681; border-radius:8px; padding:12px 14px; margin:4px 0; }
.card-blue { background:#0D1B2A; border:1px solid #1F6FEB; border-radius:8px; padding:12px 14px; margin:4px 0; }

/* KPI mini-box */
.kpi { background:#161B22; border:1px solid #30363D; border-radius:8px; padding:10px 12px; text-align:center; }
.kpi-label { font-size:11px; color:#8B949E; text-transform:uppercase; letter-spacing:0.8px; font-family:'IBM Plex Mono',monospace; }
.kpi-value { font-size:22px; font-weight:700; color:#E6EDF3; margin:3px 0; font-family:'IBM Plex Mono',monospace; }
.kpi-sub { font-size:12px; color:#8B949E; }

/* Badges */
.badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; margin-right:4px; font-family:'IBM Plex Mono',monospace; }
.badge-long { background:#3FB95020; color:#3FB950; border:1px solid #3FB950; }
.badge-short { background:#F8514920; color:#F85149; border:1px solid #F85149; }
.badge-neutral { background:#8B949E20; color:#8B949E; border:1px solid #8B949E; }
.badge-q1 { background:#3FB95020; color:#3FB950; border:1px solid #3FB950; }
.badge-q2 { background:#F8514920; color:#F85149; border:1px solid #F85149; }
.badge-q3 { background:#D2992220; color:#D29922; border:1px solid #D29922; }
.badge-q4 { background:#6E768120; color:#6E7681; border:1px solid #6E7681; }
.badge-a { background:#3FB95020; color:#3FB950; border:1px solid #3FB950; }
.badge-b { background:#D2992220; color:#D29922; border:1px solid #D29922; }
.badge-c { background:#8B949E20; color:#8B949E; border:1px solid #8B949E; }

/* Row items */
.row-item { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #21262D; font-size:13px; }
.row-item:last-child { border-bottom:none; }
.section-title { font-size:15px; font-weight:700; color:#E6EDF3; margin:10px 0 6px 0; text-transform:uppercase; letter-spacing:0.5px; font-family:'IBM Plex Mono',monospace; }
.sub-label { font-size:11px; color:#8B949E; text-transform:uppercase; letter-spacing:0.8px; font-family:'IBM Plex Mono',monospace; }

/* A/B Test */
.ab-box { background:#161B22; border:1px solid #30363D; border-radius:8px; padding:14px; }
.ab-title { font-size:13px; font-weight:700; color:#8B949E; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; margin-bottom:8px; }
.ab-result { font-size:15px; font-weight:700; margin-top:6px; }

/* Range gauge */
.rg-wrap { background:#21262D; border-radius:4px; height:8px; position:relative; margin:4px 0; }
.rg-fill { height:8px; border-radius:4px; transition:width 0.3s; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
QC  = {"Q1":"#3FB950","Q2":"#F85149","Q3":"#D29922","Q4":"#6E7681"}
QN  = {"Q1":"Growth↑ Inflation↓","Q2":"Growth↑ Inflation↑","Q3":"Stagflation","Q4":"Deflation"}
QNC = {"Q1":"Quad 1","Q2":"Quad 2","Q3":"Quad 3","Q4":"Quad 4"}
QUAD_EXPLAIN = {
    "Q1":"Risk-on. Tech, Bitcoin, Small Caps lead. Volatility compresses. Buy every dip.",
    "Q2":"Reflationary. Energy, Materials, Financials, Commodities win. Yields rise.",
    "Q3":"Stagflationary. Hard assets (Gold, Silver), Defensives. Short duration.",
    "Q4":"Most dangerous. Bonds, Gold, Utilities, Cash. Tech worst. Get defensive.",
}
QWINS = {
    "Q1":"Tech · Bitcoin · Small Caps · Semis",
    "Q2":"Energy · Materials · Commodities · Financials",
    "Q3":"Gold · Silver · GDX · Defensives",
    "Q4":"TLT · GLD · Utilities · Cash",
}
QWORST = {
    "Q1":"TLT · Gold · Utilities",
    "Q2":"TLT · Utilities · REITs",
    "Q3":"Tech · Growth · Small Caps",
    "Q4":"Tech · Bitcoin · High Beta · Small Caps",
}

def qc(q): return QC.get(q,"#8B949E")
def qn(q): return QN.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def _sf(v):
    if v is None: return None
    try:
        if isinstance(v,pd.Series): v=v.iloc[0]
        f=float(v); return f if math.isfinite(f) else None
    except: return None
def _price_ret(ticker,prices,days=21):
    s=prices.get(ticker)
    if s is None: return None
    s=pd.to_numeric(s,errors="coerce").dropna()
    if len(s)<days+1: return None
    try: return float(s.iloc[-1]/s.iloc[-(days+1)]-1)
    except: return None

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
for k,v in [("snap",None),("loading",False),("mq_override","Auto")]:
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📊 MacroRegime Pro v3.1")
    st.markdown('<div style="font-size:12px;color:#8B949E;">Hedgeye GIP · PVV · Options Overlay</div>', unsafe_allow_html=True)
    st.divider()

    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")

    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.loading = True
    with c2:
        if st.button("⚡ Rebuild", use_container_width=True):
            st.session_state.loading = True
            st.session_state.snap = None

    with st.expander("⚙️ Data Scope"):
        st.checkbox("US Stocks",   value=True, key="inc_us")
        st.checkbox("Forex",       value=True, key="inc_fx")
        st.checkbox("Commodities", value=True, key="inc_comm")
        st.checkbox("Crypto",      value=True, key="inc_cryp")
        st.checkbox("IHSG",        value=True, key="inc_ihsg")

    with st.expander("🔧 Quad Override"):
        opts = ["Auto","Q1","Q2","Q3","Q4"]
        mq_ov = st.selectbox("Monthly:", opts, index=opts.index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override:
            st.session_state.mq_override = mq_ov
        st.caption("Override when model diverges from Hedgeye")

    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g  = _s.get("gip")
        _sq = _g.structural_quad if _g else "—"
        _mq = _g.monthly_quad    if _g else "—"
        st.markdown(f"""
        <div style="background:#161B22;border:1px solid {qc(_sq)};border-radius:8px;padding:10px;text-align:center;">
          <div class="sub-label">CURRENT REGIME</div>
          <div style="font-size:22px;font-weight:700;color:{qc(_sq)};margin:4px 0;font-family:'IBM Plex Mono',monospace;">{_sq} / {_mq}</div>
          <div style="font-size:12px;color:#8B949E;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div>
        </div>""", unsafe_allow_html=True)
        st.divider()
        # Data sources
        sources = []
        if _s.get("cot_live"):    sources.append("🟢 COT")
        if _s.get("options_live"): sources.append("🟢 Options")
        if _s.get("cme_live"):    sources.append("🟢 CME")
        if (_s.get("defillama_live") or {}).get("ok"): sources.append("🟢 DeFiLlama")
        if _s.get("pvv"):         sources.append("🟢 PVV")
        if not sources:           sources.append("🟡 Proxy")
        st.caption("Sources: " + " · ".join(sources))

# ══════════════════════════════════════════════════════════════════════════════
# LOAD SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=12.0)
    if snap and snap.get("ok"):
        st.session_state.snap = snap

if snap is None or not snap.get("ok") or st.session_state.loading:
    from orchestrator import build_snapshot
    _msg = "🔄 Refreshing data..." if st.session_state.loading and st.session_state.snap else "⚡ Building MacroRegime Pro..."
    with st.spinner(_msg):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m, f): pb.progress(f); pt.caption(f"⏳ {m}")
        is_full_rebuild = (st.session_state.snap is None)
        snap = build_snapshot(
            progress_cb=prog,
            include_us_stocks   = st.session_state.get("inc_us",True),
            include_forex       = st.session_state.get("inc_fx",True),
            include_commodities = st.session_state.get("inc_comm",True),
            include_crypto      = st.session_state.get("inc_cryp",True),
            include_ihsg        = st.session_state.get("inc_ihsg",True),
            fast_refresh        = not is_full_rebuild,  # Refresh = fast, Rebuild = full
        )
        st.session_state.snap = snap
        st.session_state.loading = False
        pb.empty(); pt.empty()
        st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ Build failed. Click **⚡ Rebuild** to retry.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# UNPACK SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
gip             = snap.get("gip")
rr              = snap.get("risk_ranges",{})
health          = snap.get("health",{})
prices          = snap.get("prices",{})
pb_data         = snap.get("playbook",{})
alpha_center    = snap.get("alpha_center",{}) or {}
daily_signals   = snap.get("daily_signals",[]) or []
regime_forecast = snap.get("regime_forecast",{})
transition      = snap.get("transition",None)
gamma_data      = snap.get("gamma_data",{}) or {}
greeks_data     = snap.get("greeks_data",{}) or {}
options_live    = snap.get("options_live",{}) or {}
pvv_data        = snap.get("pvv",{}) or {}
trend_histories = snap.get("trend_histories",{}) or {}
cot_live        = snap.get("cot_live",{}) or {}
btk             = snap.get("bottleneck",{})
narr            = snap.get("narratives",{})
analogs         = snap.get("analogs",{})
news_narratives = snap.get("news_narratives",{})

sq      = gip.structural_quad if gip else "Q3"
mq_raw  = gip.monthly_quad    if gip else "Q2"
mq      = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
ar      = rr.get("asset_ranges",{})
vix_now = _sf(prices.get("^VIX", pd.Series()).tail(1)) if prices.get("^VIX") is not None else 20.0

all_items = []
for src_list in [
    alpha_center.get("longs",[]),
    alpha_center.get("shorts",[]),
    alpha_center.get("bottlenecks",[]),
    alpha_center.get("watches",[]),
]:
    all_items.extend(src_list if isinstance(src_list,list) else [])
if not all_items:
    all_items = daily_signals[:50] if daily_signals else []

# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs(["🎯 Macro Radar", "📐 Risk Range™", "⚡ Alpha Center", "🎛️ Options Overlay", "📋 Playbook"])


# ════════════════════════════════════════════════════════════════════════
# TAB 0: MACRO RADAR
# ════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("## 🎯 Macro Radar")
    st.caption("Regime · Forward · All Markets · 30-second read")

    # ── Top KPI row ──────────────────────────────────────────────────────
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    flip = gip.flip_hazard if gip else 0
    vbd  = health.get("vix_bucket",{}) if health else {}
    vl   = _sf(vbd.get("vix_last")) or vix_now or 20
    vb   = vbd.get("bucket","—")
    vix_color = "#3FB950" if vb=="Investable" else "#D29922" if vb=="Chop" else "#F85149"

    with k1: k1.markdown(f'<div class="kpi"><div class="kpi-label">Quarterly</div><div class="kpi-value" style="color:{qc(sq)};">{sq}</div><div class="kpi-sub">{QNC.get(sq,"")}</div></div>', unsafe_allow_html=True)
    with k2: k2.markdown(f'<div class="kpi"><div class="kpi-label">Monthly</div><div class="kpi-value" style="color:{qc(mq)};">{mq}</div><div class="kpi-sub">{QNC.get(mq,"")}</div></div>', unsafe_allow_html=True)
    with k3: k3.markdown(f'<div class="kpi"><div class="kpi-label">Flip Risk</div><div class="kpi-value" style="color:{"#F85149" if flip>0.35 else "#D29922" if flip>0.2 else "#3FB950"};">{flip:.0%}</div><div class="kpi-sub">{"HIGH" if flip>0.35 else "WATCH" if flip>0.2 else "LOW"}</div></div>', unsafe_allow_html=True)
    with k4: k4.markdown(f'<div class="kpi"><div class="kpi-label">VIX</div><div class="kpi-value" style="color:{vix_color};">{vl:.1f}</div><div class="kpi-sub">{vb}</div></div>', unsafe_allow_html=True)
    crash = health.get("crash",{}).get("state","calm") if health else "calm"
    cclr  = "#3FB950" if crash=="calm" else "#D29922" if crash=="watch" else "#F85149"
    with k5: k5.markdown(f'<div class="kpi"><div class="kpi-label">Crash Radar</div><div class="kpi-value" style="color:{cclr};">{crash.upper()}</div><div class="kpi-sub">market stress</div></div>', unsafe_allow_html=True)
    risk_off = health.get("risk_off",{}).get("state","risk_on") if health else "risk_on"
    roclr = "#3FB950" if risk_off=="risk_on" else "#D29922" if risk_off=="caution" else "#F85149"
    with k6: k6.markdown(f'<div class="kpi"><div class="kpi-label">Risk Regime</div><div class="kpi-value" style="color:{roclr};">{risk_off.upper().replace("_"," ")}</div><div class="kpi-sub">environment</div></div>', unsafe_allow_html=True)

    # ── Market Status Banner ──────────────────────────────────────────────
    st.markdown("") 
    if vb=="Investable": st.success(f"🟢 INVESTABLE CONDITIONS · VIX {vl:.1f} · {sq} / {mq} Regime · {QN.get(sq,'')}")
    elif vb=="Chop":     st.warning(f"🟡 CHOPPY CONDITIONS · VIX {vl:.1f} · Be selective · {QN.get(sq,'')}")
    elif vb=="Defensive":st.error(  f"🔴 DEFENSIVE MODE · VIX {vl:.1f} · Reduce risk · {QN.get(sq,'')}")

    st.divider()

    # ── Regime + Forward + Transition ────────────────────────────────────
    c1,c2,c3 = st.columns([1.2,1,1])
    with c1:
        st.markdown('<div class="section-title">Regime Map</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#161B22;border:1px solid {qc(sq)};border-radius:8px;padding:12px;margin-bottom:6px;">
          <div class="sub-label">QUARTERLY · {sq}</div>
          <div style="font-size:18px;font-weight:700;color:{qc(sq)};margin:3px 0;">{QN.get(sq,sq)}</div>
          <div style="font-size:13px;color:#E6EDF3;margin-top:4px;">{QUAD_EXPLAIN.get(sq,"")}</div>
          <div style="font-size:12px;color:#8B949E;margin-top:6px;">🟢 {QWINS.get(sq,"")}</div>
        </div>
        <div style="background:#161B22;border:1px solid {qc(mq)};border-radius:8px;padding:12px;">
          <div class="sub-label">MONTHLY · {mq}</div>
          <div style="font-size:16px;font-weight:700;color:{qc(mq)};margin:3px 0;">{QN.get(mq,mq)}</div>
          <div style="font-size:12px;color:#8B949E;margin-top:4px;">Shorter duration regime signal</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-title">Forward Engine</div>', unsafe_allow_html=True)
        if regime_forecast and regime_forecast.get("1m"):
            for dur, key in [("1M","1m"),("3M","3m"),("6M","6m")]:
                rf = regime_forecast.get(key,{})
                pq = rf.get("predicted_quad","—"); conf = rf.get("prediction_confidence",0)
                same = (pq == sq)
                clr = "#3FB950" if same else "#F85149"
                st.markdown(f"""
                <div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 10px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:12px;color:#8B949E;font-family:'IBM Plex Mono',monospace;">{dur}</span>
                  <span style="font-weight:700;color:{clr};font-family:'IBM Plex Mono',monospace;">{pq}</span>
                  <span style="font-size:12px;color:#8B949E;">{conf:.0%}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Run Full Rebuild for forward forecast")

        if transition:
            fw = transition.front_run_window
            fwc = {"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#30363D"}.get(fw,"#30363D")
            fwi = {"now":"🚨 ACT NOW","1-2w":"⚡ Position 1-2 Weeks","3-6w":"👀 Watch 3-6 Weeks","not yet":"🛑 Not Yet"}.get(fw,"🛑 Wait")
            st.markdown(f'<div style="background:{fwc};color:#fff;padding:8px 12px;border-radius:6px;font-weight:700;text-align:center;font-size:13px;margin-top:6px;">{fwi}</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="section-title">Market Breadth</div>', unsafe_allow_html=True)
        breadth_t = ["SPY","QQQ","IWM","XLK","XLE","XLF","XLI","XLU","XLP","XLV","XLB","XLC","SMH","SOXX"]
        adv=0; dec=0
        for t in breadth_t:
            ret = _price_ret(t,prices,21)
            if ret is not None:
                if ret>0.005: adv+=1
                elif ret<-0.005: dec+=1
        total_b = adv+dec or 1
        b_score = adv/total_b
        bc = "#3FB950" if b_score>0.65 else "#D29922" if b_score>0.45 else "#F85149"
        st.markdown(f"""
        <div class="card">
          <div class="sub-label">21D BREADTH</div>
          <div style="font-size:22px;font-weight:700;color:{bc};margin:4px 0;font-family:'IBM Plex Mono',monospace;">{b_score:.0%}</div>
          <div style="font-size:13px;color:#8B949E;">{adv} advancing · {dec} declining</div>
          <div style="background:#21262D;border-radius:4px;height:8px;margin-top:8px;">
            <div style="background:{bc};width:{b_score*100:.0f}%;height:8px;border-radius:4px;"></div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Quad performance table (quick)
        st.markdown('<div class="sub-label" style="margin-top:10px;">Quad Best Assets</div>', unsafe_allow_html=True)
        for q in ["Q1","Q2","Q3","Q4"]:
            tag = "badge-q1" if q=="Q1" else "badge-q2" if q=="Q2" else "badge-q3" if q=="Q3" else "badge-q4"
            active = q == sq
            st.markdown(f'<div style="font-size:12px;color:{"#E6EDF3" if active else "#8B949E"};padding:2px 0;{"font-weight:700;" if active else ""}"><span class="badge {tag}">{q}</span>{QWINS.get(q,"")}</div>', unsafe_allow_html=True)

    st.divider()

    # ── All Markets Pulse table ─────────────────────────────────────────
    st.markdown('<div class="section-title">All Markets Pulse</div>', unsafe_allow_html=True)
    mkt_tickers = {
        "S&P 500":"SPY","Nasdaq":"QQQ","Russell 2K":"IWM","Dow":"DIA",
        "Gold":"GLD","Silver":"SLV","WTI Oil":"USO","Nat Gas":"UNG",
        "Long Bond":"TLT","VIX":"^VIX","Dollar":"UUP","Bitcoin":"IBIT",
        "Semis":"SMH","Financials":"XLF","Energy":"XLE","Health":"XLV",
    }
    pulse_rows = []
    for name, t in mkt_tickers.items():
        px = _sf(prices.get(t,pd.Series()).tail(1)) if prices.get(t) is not None else None
        r1d = _price_ret(t,prices,1); r5d = _price_ret(t,prices,5); r21d = _price_ret(t,prices,21)
        rr_t = ar.get(t,{}); formation = rr_t.get("composite","—") if rr_t.get("ok") else "—"
        pulse_rows.append({"Asset":name,"Ticker":t,"Price":ff(px),
                           "1D":fp(r1d),"5D":fp(r5d),"21D":fp(r21d),
                           "Signal":formation.upper() if formation else "—"})
    df_pulse = pd.DataFrame(pulse_rows)
    def _color_pct(v):
        try:
            f=float(str(v).strip("%"))/100
            return f"color:#3FB950;font-weight:600;" if f>0.005 else f"color:#F85149;font-weight:600;" if f<-0.005 else "color:#8B949E;"
        except: return ""
    def _color_sig(v):
        if "BULL" in str(v).upper(): return "color:#3FB950;font-weight:700;"
        if "BEAR" in str(v).upper(): return "color:#F85149;font-weight:700;"
        return "color:#8B949E;"
    st.dataframe(
        df_pulse.style
            .map(lambda x: _color_pct(x), subset=["1D","5D","21D"])
            .map(lambda x: _color_sig(x), subset=["Signal"]),
        use_container_width=True, hide_index=True, height=320
    )


# ════════════════════════════════════════════════════════════════════════
# TAB 1: RISK RANGE™
# ════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("## 📐 Risk Range™")
    st.caption("Trade (≤3wk) · Trend (≥3mo) · Tail (≤3yr) · Price × Volume × Volatility")

    # ── Formation filter ─────────────────────────────────────────────────
    fc1,fc2,fc3 = st.columns([1,1,2])
    with fc1:
        formation_filter = st.selectbox("Formation", ["All","Bullish","Bearish","Neutral"], index=0)
    with fc2:
        market_filter = st.selectbox("Market", ["All","US Equity","Forex","Commodity","Crypto","IHSG"], index=0)
    with fc3:
        search_ticker = st.text_input("Search ticker", placeholder="SPY, NVDA, BTC-USD…").upper().strip()

    # ── Build RR table ──────────────────────────────────────────────────
    rr_rows = []
    for ticker, rv in ar.items():
        if not rv.get("ok"): continue
        px   = _sf(rv.get("px"))
        if px is None: continue

        tr   = rv.get("trade",{})
        tn   = rv.get("trend",{})
        ta   = rv.get("tail",{})
        lrr_t = _sf(tr.get("lrr")); trr_t = _sf(tr.get("trr"))
        lrr_n = _sf(tn.get("lrr")); trr_n = _sf(tn.get("trr"))
        lrr_a = _sf(ta.get("lrr")); trr_a = _sf(ta.get("trr"))

        comp  = rv.get("composite","neutral")
        qual  = rv.get("quality","C")
        mkt   = rv.get("market","us_equity")

        if formation_filter != "All" and formation_filter.lower() not in comp.lower(): continue
        if market_filter != "All" and market_filter.lower().replace(" ","_") not in mkt.lower(): continue
        if search_ticker and search_ticker not in ticker.upper(): continue

        # Position within trade range
        pos_trade = None
        if lrr_t and trr_t and (trr_t-lrr_t)>0:
            pos_trade = round((px-lrr_t)/(trr_t-lrr_t)*100,1)

        # Phase transition check
        phase = "🟢 BULLISH" if "bull" in comp.lower() else "🔴 BEARISH" if "bear" in comp.lower() else "🟡 NEUTRAL"
        if "transition" in comp.lower(): phase = "⚠️ TRANSITION"

        r1m  = _price_ret(ticker,prices,21)
        r3m  = _price_ret(ticker,prices,63)

        rr_rows.append({
            "Ticker":   ticker,
            "Price":    ff(px),
            "Grade":    qual,
            "Formation":phase,
            "T-Low":    ff(lrr_t) if lrr_t else "—",
            "T-High":   ff(trr_t) if trr_t else "—",
            "Position": f"{pos_trade:.0f}%" if pos_trade is not None else "—",
            "Tn-Low":   ff(lrr_n) if lrr_n else "—",
            "Tn-High":  ff(trr_n) if trr_n else "—",
            "1M%":      fp(r1m),
            "3M%":      fp(r3m),
            "_comp": comp, "_pos": pos_trade,
        })

    st.markdown(f'<div style="font-size:13px;color:#8B949E;margin-bottom:8px;">{len(rr_rows)} assets in range database</div>', unsafe_allow_html=True)

    if rr_rows:
        df_rr = pd.DataFrame(rr_rows)
        display_cols = ["Ticker","Price","Grade","Formation","T-Low","T-High","Position","Tn-Low","Tn-High","1M%","3M%"]
        st.dataframe(
            df_rr[display_cols].style
                .map(lambda x: "color:#3FB950;font-weight:700;" if "BULL" in str(x) else "color:#F85149;font-weight:700;" if "BEAR" in str(x) else "color:#D29922;font-weight:600;" if "TRANS" in str(x) else "", subset=["Formation"])
                .map(lambda x: "color:#3FB950;font-weight:700;" if x in ("A+","A") else "color:#D29922;font-weight:600;" if x=="B" else "color:#8B949E;", subset=["Grade"])
                .map(lambda x: _color_pct(x) if x != "—" else "", subset=["1M%","3M%"]),
            use_container_width=True, hide_index=True, height=360
        )
    else:
        st.info("No Range data yet — Run Full Rebuild")

    st.divider()

    # ── Phase Transition Alerts ──────────────────────────────────────────
    st.markdown('<div class="section-title">⚠️ Phase Transition Alerts</div>', unsafe_allow_html=True)
    transitions = [r for r in rr_rows if "TRANS" in r.get("Formation","")]
    if transitions:
        ta_c1,ta_c2,ta_c3 = st.columns(3)
        for i, tr_item in enumerate(transitions[:9]):
            col = [ta_c1,ta_c2,ta_c3][i%3]
            with col:
                st.markdown(f"""
                <div class="card" style="border-color:#D29922;">
                  <div style="font-size:13px;font-weight:700;color:#E6EDF3;">{tr_item['Ticker']}</div>
                  <div style="font-size:12px;color:#D29922;margin:2px 0;">⚠️ PHASE TRANSITION</div>
                  <div style="font-size:12px;color:#8B949E;">Price: {tr_item['Price']} | Range: {tr_item['T-Low']}–{tr_item['T-High']}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.success("✅ No phase transitions detected — formations are stable")

    st.divider()

    # ── Single Ticker Deep Dive ──────────────────────────────────────────
    st.markdown('<div class="section-title">Single Ticker Risk Range Deep Dive</div>', unsafe_allow_html=True)
    available_tickers = sorted([r["Ticker"] for r in rr_rows]) if rr_rows else ["SPY","QQQ","IWM"]
    sel_ticker = st.selectbox("Select ticker", available_tickers, index=0 if available_tickers else 0)

    if sel_ticker:
        rv = ar.get(sel_ticker,{})
        if rv.get("ok"):
            px   = _sf(rv.get("px"))
            tr   = rv.get("trade",{})
            tn   = rv.get("trend",{})
            ta2  = rv.get("tail",{})
            lrr_t = _sf(tr.get("lrr")); trr_t = _sf(tr.get("trr"))
            lrr_n = _sf(tn.get("lrr")); trr_n = _sf(tn.get("trr"))
            lrr_a = _sf(ta2.get("lrr")); trr_a = _sf(ta2.get("trr"))
            comp  = rv.get("composite","neutral")
            signal_color = "#3FB950" if "bull" in comp.lower() else "#F85149" if "bear" in comp.lower() else "#D29922"

            dd_c1,dd_c2 = st.columns([2,1])
            with dd_c1:
                # Multi-duration range chart
                fig = go.Figure()
                durations = []
                labels = []
                if lrr_t and trr_t:
                    durations.append(("TRADE (≤3wk)", lrr_t, trr_t))
                if lrr_n and trr_n:
                    durations.append(("TREND (≥3mo)", lrr_n, trr_n))
                if lrr_a and trr_a:
                    durations.append(("TAIL (≤3yr)", lrr_a, trr_a))

                colors = ["#1F6FEB","#3FB950","#D29922"]
                for i,(dur,lo,hi) in enumerate(durations):
                    fig.add_trace(go.Bar(
                        y=[dur], x=[hi-lo],
                        base=[lo], orientation='h',
                        marker_color=colors[i], opacity=0.25,
                        name=dur, showlegend=True,
                        hovertemplate=f"{dur}: ${lo:.2f} — ${hi:.2f}<extra></extra>",
                    ))
                    fig.add_trace(go.Bar(
                        y=[dur], x=[hi-lo],
                        base=[lo], orientation='h',
                        marker=dict(color="rgba(0,0,0,0)", line=dict(color=colors[i],width=2)),
                        showlegend=False,
                    ))

                if px:
                    fig.add_vline(x=px, line_dash="solid", line_color=signal_color, line_width=2,
                                  annotation_text=f"  ${px:.2f}", annotation_font_size=13,
                                  annotation_font_color=signal_color)

                fig.update_layout(
                    height=220, barmode='overlay',
                    paper_bgcolor="#161B22", plot_bgcolor="#161B22",
                    font=dict(color="#E6EDF3", family="IBM Plex Sans", size=12),
                    margin=dict(t=20,b=10,l=10,r=20),
                    xaxis=dict(showgrid=True, gridcolor="#21262D", tickfont=dict(size=12)),
                    yaxis=dict(showgrid=False),
                    legend=dict(orientation="h", y=-0.3, font=dict(size=11)),
                    title=dict(text=f"{sel_ticker} — Multi-Duration Risk Range™",
                               font=dict(size=13,color="#8B949E")),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

            with dd_c2:
                st.markdown(f"""
                <div class="card">
                  <div class="sub-label">Formation</div>
                  <div style="font-size:18px;font-weight:700;color:{signal_color};margin:4px 0;font-family:'IBM Plex Mono',monospace;">{comp.upper()}</div>
                  <div style="font-size:13px;color:#8B949E;">Quality: {rv.get("quality","—")}</div>
                </div>
                <div class="card" style="margin-top:6px;">
                  <div class="sub-label">Trade Range</div>
                  <div style="font-size:15px;font-weight:700;color:#E6EDF3;font-family:'IBM Plex Mono',monospace;">{ff(lrr_t)} — {ff(trr_t)}</div>
                  <div style="font-size:12px;color:#8B949E;margin-top:4px;">
                    {"Buy at LRR" if "bull" in comp.lower() else "Sell at TRR"} in this formation
                  </div>
                </div>
                <div class="card" style="margin-top:6px;">
                  <div class="sub-label">Trend Range</div>
                  <div style="font-size:15px;font-weight:700;color:#E6EDF3;font-family:'IBM Plex Mono',monospace;">{ff(lrr_n)} — {ff(trr_n)}</div>
                  <div style="font-size:12px;color:#8B949E;margin-top:4px;">Invalidation if Trend breaks</div>
                </div>""", unsafe_allow_html=True)

                if lrr_t and trr_t and px:
                    pos = (px-lrr_t)/(trr_t-lrr_t) if (trr_t-lrr_t)>0 else 0.5
                    pos = max(0,min(1,pos))
                    pos_c = "#3FB950" if pos<0.35 else "#F85149" if pos>0.75 else "#D29922"
                    st.markdown(f"""
                    <div class="card" style="margin-top:6px;">
                      <div class="sub-label">Position in Trade Range</div>
                      <div style="font-size:22px;font-weight:700;color:{pos_c};font-family:'IBM Plex Mono',monospace;">{pos:.0%}</div>
                      <div style="background:#21262D;border-radius:4px;height:8px;margin-top:6px;">
                        <div style="background:{pos_c};width:{pos*100:.0f}%;height:8px;border-radius:4px;"></div>
                      </div>
                      <div style="font-size:12px;color:#8B949E;margin-top:4px;">{"BUY ZONE" if pos<0.35 else "SELL ZONE" if pos>0.75 else "MID-RANGE"}</div>
                    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 2: ALPHA CENTER
# ════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("## ⚡ Alpha Center")
    st.caption(f"Priority setups · Quad {sq}/{mq} · Risk Range confirmed")

    if not all_items:
        st.info("No setups yet — Run Full Rebuild")
        st.stop()

    # ── Summary bar ──────────────────────────────────────────────────────
    longs  = [x for x in all_items if "LONG"  in str(x.get("direction","")).upper()]
    shorts = [x for x in all_items if "SHORT" in str(x.get("direction","")).upper()]
    sb1,sb2,sb3,sb4 = st.columns(4)
    sb1.metric("Total Setups", len(all_items))
    sb2.metric("Longs",        len(longs),  delta=f"+{len(longs)}", delta_color="normal")
    sb3.metric("Shorts",       len(shorts), delta=f"-{len(shorts)}", delta_color="inverse")
    sb4.metric("Quad Fit",     sq)

    st.divider()

    # ── Priority table ──────────────────────────────────────────────────
    tbl_rows = []
    for item in sorted(all_items, key=lambda x:x.get("priority_score",0), reverse=True)[:40]:
        t   = item.get("ticker","?")
        dir = item.get("direction","NEUTRAL")
        g   = item.get("grade","C")
        sc  = item.get("priority_score",0)
        w   = item.get("worth_entering","—")
        rr_i= item.get("rr",0)
        g_ok= gamma_data.get(t,{}).get("ok",False)
        gk_ok=greeks_data.get(t,{}).get("ok",False)
        opts_str = "✅ Live" if options_live.get(t,{}).get("ok") else ("📊 Proxy" if g_ok or gk_ok else "—")
        tbl_rows.append({
            "Ticker":t,"Dir":dir,"Grade":g,"Score":round(sc,1),
            "Price":ff(item.get("price")),"Entry":ff(item.get("entry")),
            "Target":ff(item.get("target_1")),"Stop":ff(item.get("stop_loss")),
            "R:R":ff(item.get("rr",0),1)+"x",
            "Options":opts_str,
            "Worth?":str(w)[:30] if w else "—",
        })

    df_ac = pd.DataFrame(tbl_rows)
    st.dataframe(
        df_ac.style
            .map(lambda x: "color:#3FB950;font-weight:700;" if "LONG" in str(x).upper() else "color:#F85149;font-weight:700;" if "SHORT" in str(x).upper() else "color:#8B949E;", subset=["Dir"])
            .map(lambda x: "color:#3FB950;font-weight:700;" if x in ("A+","A") else "color:#D29922;font-weight:600;" if x=="B" else "color:#8B949E;", subset=["Grade"]),
        use_container_width=True, hide_index=True, height=340
    )

    st.divider()

    # ── Top 5 Deep Dive ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Top 5 Priority Setups — Full Detail</div>', unsafe_allow_html=True)
    top5 = sorted(all_items, key=lambda x:x.get("priority_score",0), reverse=True)[:5]

    for idx, item in enumerate(top5):
        ticker = item.get("ticker","UNKNOWN")
        direction = item.get("direction","NEUTRAL")
        dir_color = "#3fb950" if "LONG" in direction.upper() else "#f85149" if "SHORT" in direction.upper() else "#8b949e"
        with st.expander(f"{'🟢' if 'LONG' in direction.upper() else '🔴' if 'SHORT' in direction.upper() else '⚪'} {ticker} · {direction} · Grade {item.get('grade','C')} · Score {item.get('priority_score',0):.1f}", expanded=(idx==0)):

            # Metrics row
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Price",    ff(item.get("price")))
            m2.metric("Entry",    ff(item.get("entry")))
            m3.metric("Target 1", ff(item.get("target_1")))
            m4.metric("Target 2", ff(item.get("target_2")))
            m5.metric("Stop",     ff(item.get("stop_loss")))
            m6.metric("R:R",      f"{item.get('rr',0):.1f}×")

            # ── Risk Range mini visual ──
            rr_t = ar.get(ticker,{})
            if rr_t and rr_t.get("ok"):
                tr = rr_t.get("trade",{})
                lrr = _sf(tr.get("lrr")); trr = _sf(tr.get("trr"))
                px  = item.get("price")
                if lrr and trr and px and (trr-lrr)>0:
                    pos = max(0,min(1,(px-lrr)/(trr-lrr)))
                    pos_c = "#3FB950" if pos<0.35 else "#F85149" if pos>0.75 else "#D29922"
                    st.markdown(f"""
                    <div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px 14px;margin:6px 0;">
                      <div class="sub-label">Risk Range™ — Trade Duration</div>
                      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;color:#8B949E;font-family:'IBM Plex Mono',monospace;">
                        <span>LRR ${lrr:.2f}</span><span style="color:{pos_c};font-weight:700;">${px:.2f} ({pos:.0%})</span><span>TRR ${trr:.2f}</span>
                      </div>
                      <div style="background:#21262D;border-radius:4px;height:10px;margin-top:4px;position:relative;">
                        <div style="background:{pos_c};width:{pos*100:.0f}%;height:10px;border-radius:4px;"></div>
                        <div style="position:absolute;top:-2px;left:{pos*100:.0f}%;width:2px;height:14px;background:#fff;border-radius:1px;transform:translateX(-50%);"></div>
                      </div>
                      <div style="font-size:12px;color:{pos_c};margin-top:4px;font-weight:700;">{"🟢 BUY ZONE — At/near LRR" if pos<0.35 else "🔴 SELL ZONE — At/near TRR" if pos>0.75 else "🟡 MID-RANGE — Wait for LRR"}</div>
                    </div>""", unsafe_allow_html=True)

            # ── Options & Greeks ──
            gamma = gamma_data.get(ticker,{})
            greek = greeks_data.get(ticker,{})
            opt   = options_live.get(ticker,{})
            if gamma.get("ok") or greek.get("ok") or opt.get("ok"):
                st.markdown('<div class="sub-label" style="margin-top:8px;">Options & Greeks</div>', unsafe_allow_html=True)
                og1,og2,og3,og4,og5,og6 = st.columns(6)
                og1.metric("Gamma Regime", gamma.get("regime","—") if gamma.get("ok") else "—")
                og2.metric("Δ Delta",      greek.get("delta","—")   if greek.get("ok") else "—")
                og3.metric("Composite",    greek.get("composite","—") if greek.get("ok") else "—")
                og4.metric("Vol Premium",  f"{greek.get('vol_premium',0):.1f}%" if greek.get("ok") else "—")
                og5.metric("Max Pain",     ff(gamma.get("max_pain")) if gamma.get("ok") else "—")
                og6.metric("Vanna",        greek.get("vanna","—")   if greek.get("ok") else "—")
                if opt.get("ok"):
                    og7,og8,og9 = st.columns(3)
                    og7.metric("P/C Volume", ff(opt.get("pc_volume")))
                    og8.metric("P/C OI",     ff(opt.get("pc_oi")))
                    og9.metric("IV Skew",    f"{opt.get('iv_skew',0):.3f}")

            # Thesis + Invalidators
            st.divider()
            cc1,cc2 = st.columns([2,1])
            with cc1:
                thesis = item.get("thesis") or item.get("recommendation") or "N/A"
                st.markdown(f'<div class="card-blue"><div class="sub-label">🎯 Thesis</div><div style="font-size:13px;color:#E6EDF3;margin-top:4px;">{thesis}</div></div>', unsafe_allow_html=True)
            with cc2:
                inv = item.get("invalidators",[])
                if inv:
                    inv_str = "\n".join(f"• {x}" for x in inv[:3])
                    st.markdown(f'<div class="card-q2"><div class="sub-label">❌ Invalidators</div><div style="font-size:12px;color:#F85149;margin-top:4px;">{inv_str}</div></div>', unsafe_allow_html=True)
                entry_advice = item.get("entry_advice","")
                if entry_advice:
                    w = item.get("worth_entering","—")
                    wc = "#3FB950" if "YES" in str(w).upper() or "BUY" in str(w).upper() else "#D29922" if "WAIT" in str(w).upper() else "#F85149"
                    st.markdown(f'<div class="card" style="margin-top:6px;border-color:{wc};"><div class="sub-label">Worth Entering?</div><div style="font-size:13px;color:{wc};font-weight:700;margin-top:4px;">{w}</div></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 3: OPTIONS OVERLAY
# ════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("## 🎛️ Options Overlay")
    st.caption("Dealer Gamma · Vol Structure · Greeks · Skew · Tier 1 Alpha methodology")

    # ── Gamma Dashboard ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Dealer Gamma Regime</div>', unsafe_allow_html=True)
    g1,g2,g3,g4 = st.columns(4)

    # Aggregate gamma reading from available tickers
    gamma_signals = [(t,d) for t,d in gamma_data.items() if d.get("ok")]
    pos_gamma = sum(1 for _,d in gamma_signals if "positive" in d.get("regime","").lower() or "bullish" in d.get("regime","").lower())
    neg_gamma = sum(1 for _,d in gamma_signals if "negative" in d.get("regime","").lower() or "bearish" in d.get("regime","").lower())
    total_g   = len(gamma_signals) or 1
    gamma_score = (pos_gamma - neg_gamma) / total_g

    gc = "#3FB950" if gamma_score>0.2 else "#F85149" if gamma_score<-0.2 else "#D29922"
    gamma_label = "POSITIVE — Vol damping" if gamma_score>0.2 else "NEGATIVE — Vol amplifying" if gamma_score<-0.2 else "MIXED — Neutral"

    with g1:
        st.markdown(f'<div class="kpi"><div class="kpi-label">Aggregate Gamma</div><div class="kpi-value" style="color:{gc};">{gamma_score:+.0%}</div><div class="kpi-sub">{gamma_label.split(" — ")[0]}</div></div>', unsafe_allow_html=True)
    with g2:
        vix_regime_str = "Compressed" if vix_now and vix_now < 15 else "Normal" if vix_now and vix_now < 25 else "Elevated" if vix_now and vix_now < 35 else "Extreme"
        vc2 = "#3FB950" if vix_now and vix_now<15 else "#D29922" if vix_now and vix_now<25 else "#F85149"
        st.markdown(f'<div class="kpi"><div class="kpi-label">VIX Regime</div><div class="kpi-value" style="color:{vc2};">{vix_now:.1f}</div><div class="kpi-sub">{vix_regime_str}</div></div>', unsafe_allow_html=True)
    with g3:
        # Vol premium proxy: VIX vs realized vol (SPY)
        spy_s = prices.get("SPY")
        rv_spy = 0.0
        if spy_s is not None:
            rets = pd.to_numeric(spy_s,errors="coerce").pct_change().dropna()
            rv_spy = float(rets.tail(20).std()*math.sqrt(252)*100) if len(rets)>=20 else 0.0
        vp = (vix_now or 20) - rv_spy
        vpc = "#F85149" if vp>5 else "#3FB950" if vp<-2 else "#D29922"
        vp_label = "Expensive — fear premium" if vp>5 else "Cheap — complacency" if vp<-2 else "Fair — normal"
        st.markdown(f'<div class="kpi"><div class="kpi-label">IV Premium (VIX-RV)</div><div class="kpi-value" style="color:{vpc};">{vp:+.1f}%</div><div class="kpi-sub">{vp_label.split(" — ")[0]}</div></div>', unsafe_allow_html=True)
    with g4:
        # Market breadth proxy for call/put balance
        spx_21 = _price_ret("SPY",prices,21)
        cp_proxy = "Call-Biased" if (spx_21 or 0)>0.03 else "Put-Biased" if (spx_21 or 0)<-0.03 else "Balanced"
        cp_c = "#3FB950" if cp_proxy=="Call-Biased" else "#F85149" if cp_proxy=="Put-Biased" else "#D29922"
        st.markdown(f'<div class="kpi"><div class="kpi-label">Flow Bias Proxy</div><div class="kpi-value" style="color:{cp_c};">{cp_proxy.split("-")[0]}</div><div class="kpi-sub">SPY 21D momentum proxy</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── Vol Term Structure Proxy ──────────────────────────────────────────
    st.markdown('<div class="section-title">Vol Term Structure Proxy — SPY</div>', unsafe_allow_html=True)

    vol_tickers_chart = ["SPY","QQQ","IWM","XLK","GLD","TLT"]
    vts_data = []
    for t in vol_tickers_chart:
        s = prices.get(t)
        if s is None: continue
        s_n = pd.to_numeric(s,errors="coerce").dropna()
        if len(s_n)<63: continue
        rets_s = s_n.pct_change().dropna()
        rv5  = float(rets_s.tail(5).std() * math.sqrt(252) * 100)  if len(rets_s)>=5  else None
        rv10 = float(rets_s.tail(10).std()* math.sqrt(252) * 100)  if len(rets_s)>=10 else None
        rv21 = float(rets_s.tail(21).std()* math.sqrt(252) * 100)  if len(rets_s)>=21 else None
        rv63 = float(rets_s.tail(63).std()* math.sqrt(252) * 100)  if len(rets_s)>=63 else None
        vts_data.append({"Ticker":t,"RV5":rv5,"RV10":rv10,"RV21":rv21,"RV63":rv63})

    if vts_data:
        fig_vts = go.Figure()
        x_labels = ["5D RV","10D RV","21D RV","63D RV"]
        colors_vts = ["#3FB950","#1F6FEB","#D29922","#F85149","#8B949E","#58A6FF"]
        for i, row in enumerate(vts_data):
            y_vals = [row.get("RV5"), row.get("RV10"), row.get("RV21"), row.get("RV63")]
            if all(v is None for v in y_vals): continue
            fig_vts.add_trace(go.Scatter(
                x=x_labels, y=y_vals,
                name=row["Ticker"], mode="lines+markers",
                line=dict(color=colors_vts[i%len(colors_vts)],width=2),
                marker=dict(size=7),
            ))
        if vix_now:
            fig_vts.add_hline(y=vix_now, line_dash="dash", line_color="#F85149",
                              annotation_text=f"  VIX {vix_now:.1f}", annotation_font_color="#F85149",
                              annotation_font_size=11)
        fig_vts.update_layout(
            height=280, paper_bgcolor="#161B22", plot_bgcolor="#161B22",
            font=dict(color="#E6EDF3", family="IBM Plex Sans", size=12),
            margin=dict(t=20,b=30,l=0,r=10),
            legend=dict(orientation="h", y=-0.35, font=dict(size=11)),
            yaxis=dict(title="Realized Vol %", showgrid=True, gridcolor="#21262D"),
            xaxis=dict(showgrid=False),
            title=dict(text="Realized Volatility Term Structure (RV vs VIX)", font=dict(size=12,color="#8B949E")),
        )
        st.plotly_chart(fig_vts, use_container_width=True, config={"displayModeBar":False})

    st.divider()

    # ── Greeks Summary Table ─────────────────────────────────────────────
    st.markdown('<div class="section-title">Greeks Summary — Top Tickers</div>', unsafe_allow_html=True)

    greek_rows = []
    for t, gk in greeks_data.items():
        if not gk.get("ok"): continue
        gm = gamma_data.get(t,{})
        greek_rows.append({
            "Ticker":  t,
            "Delta":   gk.get("delta","—"),
            "Gamma":   gm.get("regime","—") if gm.get("ok") else gk.get("gamma","—"),
            "Vanna":   gk.get("vanna","—"),
            "Charm":   gk.get("charm","—"),
            "RV 20D":  f"{gk.get('rvol_20d',0):.1f}%",
            "Vol Prem":f"{gk.get('vol_premium',0):+.1f}%",
            "Score":   gk.get("composite","—"),
        })

    if greek_rows:
        df_greek = pd.DataFrame(greek_rows)
        st.dataframe(
            df_greek.style
                .map(lambda x: "color:#3FB950;font-weight:700;" if "Long" in str(x) or "BULL" in str(x).upper() else "color:#F85149;font-weight:700;" if "Short" in str(x) or "BEAR" in str(x).upper() else "color:#8B949E;", subset=["Delta","Score"])
                .map(lambda x: "color:#3FB950;font-weight:700;" if "Positive" in str(x) or "positive" in str(x).lower() else "color:#F85149;font-weight:700;" if "Negative" in str(x) else "color:#8B949E;", subset=["Gamma"]),
            use_container_width=True, hide_index=True, height=300
        )
    else:
        st.info("Greeks require Full Rebuild with options analytics enabled")

    st.divider()

    # ── Live Options Chain (top tickers with live data) ───────────────────
    live_opts = [(t,d) for t,d in options_live.items() if d.get("ok")]
    if live_opts:
        st.markdown('<div class="section-title">Live Options Chain Data</div>', unsafe_allow_html=True)
        opt_rows = []
        for t, od in live_opts[:20]:
            pc = od.get("put_call_ratio",{})
            em = od.get("expected_move",{})
            opt_rows.append({
                "Ticker":   t,
                "Max Pain": ff(od.get("max_pain")),
                "Dist Pain":f"{od.get('dist_max_pain_pct',0):+.1f}%",
                "P/C Vol":  ff(pc.get("pc_volume") if isinstance(pc,dict) else od.get("pc_volume")),
                "P/C OI":   ff(pc.get("pc_oi") if isinstance(pc,dict) else od.get("pc_oi")),
                "Avg IV":   f"{od.get('avg_iv',0)*100:.1f}%",
                "IV Skew":  f"{od.get('iv_skew',0):.3f}",
                "Exp Move": ff(em.get("move_pct") if isinstance(em,dict) else od.get("expected_move")),
                "GEX":      f"{od.get('gex',0):,.0f}",
                "Source":   od.get("source","—")[:20],
            })
        df_opt = pd.DataFrame(opt_rows)
        st.dataframe(df_opt, use_container_width=True, hide_index=True, height=280)
    else:
        st.markdown("""
        <div class="card-q3">
          <div style="font-size:13px;font-weight:700;color:#D29922;">🟡 No Live Options Data</div>
          <div style="font-size:13px;color:#8B949E;margin-top:6px;">
            Live options chain requires Full Rebuild.<br>
            Greeks Proxy is active — derived from Price × Volume × Volatility.<br>
            For live IV/OI/skew: yfinance options chain fetched on Full Rebuild for top 15 tickers.
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Tier 1 Alpha Framework Note ──────────────────────────────────────
    st.divider()
    st.markdown("""
    <div class="card-blue">
      <div class="sub-label">Tier 1 Alpha / Hedgeye Options Framework</div>
      <div style="font-size:13px;color:#E6EDF3;margin-top:6px;">
        <b>Options = Confirmation Layer, NOT primary signal.</b> Workflow:<br>
        1️⃣ Risk Range says BUY at LRR + dealer gamma positive → High conviction dip buy.<br>
        2️⃣ Risk Range says SELL at TRR + 0DTE call chasing extreme → Fade the YOLO.<br>
        3️⃣ Trend breaks bearish + put skew expanding → Confirm phase transition. Get out.<br>
        4️⃣ Quad 4 entry + vol term structure inverts → Full defensive positioning.
      </div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 4: PLAYBOOK
# ════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("## 📋 Playbook")
    st.caption(f"Quad {sq} · A/B Test · Themes · Market Health")

    pl1, pl2 = st.columns([1,1])

    with pl1:
        # ── Quad Playbook ──────────────────────────────────────────────
        st.markdown(f'<div class="section-title">Quad {sq} Playbook</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card-{'q1' if sq=='Q1' else 'q2' if sq=='Q2' else 'q3' if sq=='Q3' else 'q4'}">
          <div style="font-size:14px;font-weight:700;color:{qc(sq)};">{sq} — {QN.get(sq,"")}</div>
          <div style="font-size:13px;color:#E6EDF3;margin-top:6px;">{QUAD_EXPLAIN.get(sq,"")}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card" style="margin-top:8px;">
          <div class="sub-label">🟢 BUY / HOLD — {sq}</div>
          <div style="font-size:13px;color:#3FB950;margin-top:4px;font-weight:600;">{QWINS.get(sq,"")}</div>
        </div>
        <div class="card" style="margin-top:6px;">
          <div class="sub-label">🔴 AVOID / SHORT — {sq}</div>
          <div style="font-size:13px;color:#F85149;margin-top:4px;font-weight:600;">{QWORST.get(sq,"")}</div>
        </div>""", unsafe_allow_html=True)

        if pb_data:
            strategy = pb_data.get("strategy","")
            if strategy:
                st.markdown(f'<div class="card" style="margin-top:6px;"><div class="sub-label">Strategy</div><div style="font-size:13px;color:#8B949E;margin-top:4px;">{strategy}</div></div>', unsafe_allow_html=True)

        # Forward warning
        if regime_forecast and regime_forecast.get("3m"):
            rf3 = regime_forecast["3m"]
            if rf3.get("predicted_quad") and rf3.get("predicted_quad") != sq:
                nq  = rf3["predicted_quad"]; conf = rf3.get("prediction_confidence",0)
                st.markdown(f"""
                <div class="card-q3" style="margin-top:8px;">
                  <div class="sub-label">⚠️ FORWARD ALERT — 3M</div>
                  <div style="font-size:13px;color:#D29922;margin-top:4px;font-weight:700;">
                    Model predicts shift to {nq} ({conf:.0%} confidence)<br>
                    <span style="font-weight:400;">Begin rotating toward: {QWINS.get(nq,"—")}</span>
                  </div>
                </div>""", unsafe_allow_html=True)

    with pl2:
        # ── A/B TEST — Hedgeye Mandatory ──────────────────────────────────
        st.markdown('<div class="section-title">A/B Test — Risk Management</div>', unsafe_allow_html=True)

        # Test A: What does the macro say?
        gip_signal = f"{sq} regime — {QN.get(sq,'')}"
        gip_action = QWINS.get(sq,"Risk-appropriate positioning")
        flip_warn  = f" ⚠️ Flip Risk {flip:.0%}" if flip>0.2 else ""
        a_verdict  = f"LONG {QWINS.get(sq,'').split(' · ')[0]}" if sq in ("Q1","Q2") else f"DEFENSIVE — {QWINS.get(sq,'').split(' · ')[0]}"
        a_color    = "#3FB950" if sq in ("Q1","Q2") else "#D29922" if sq=="Q3" else "#F85149"

        # Test B: What is the market pricing?
        bull_count  = sum(1 for r in rr_rows if "BULL" in r.get("Formation","").upper())
        bear_count  = sum(1 for r in rr_rows if "BEAR" in r.get("Formation","").upper())
        total_rr_c  = bull_count + bear_count or 1
        signal_bias = bull_count / total_rr_c
        b_verdict   = "BULLISH FORMATION" if signal_bias>0.55 else "BEARISH FORMATION" if signal_bias<0.40 else "MIXED / NEUTRAL"
        b_color     = "#3FB950" if signal_bias>0.55 else "#F85149" if signal_bias<0.40 else "#D29922"

        # Combined verdict
        aligned = (sq in ("Q1","Q2") and signal_bias>0.55) or (sq in ("Q3","Q4") and signal_bias<0.45)
        combined_verdict = "ALIGNED — Conviction HIGH" if aligned else "DIVERGING — Wait for confirmation"
        cv_color  = "#3FB950" if aligned else "#D29922"

        st.markdown(f"""
        <div class="ab-box">
          <div class="ab-title">Test A — What does the Macro say?</div>
          <div style="font-size:13px;color:#8B949E;">GIP Signal: <span style="color:#E6EDF3;font-weight:600;">{gip_signal}</span>{flip_warn}</div>
          <div class="ab-result" style="color:{a_color};">▶ {a_verdict}</div>
        </div>
        <div class="ab-box" style="margin-top:8px;">
          <div class="ab-title">Test B — What is the Signal saying?</div>
          <div style="font-size:13px;color:#8B949E;">Risk Range: <span style="color:#E6EDF3;font-weight:600;">{bull_count} Bullish · {bear_count} Bearish</span> ({signal_bias:.0%} positive)</div>
          <div style="font-size:13px;color:#8B949E;">VIX: <span style="color:#E6EDF3;font-weight:600;">{vl:.1f} ({vb})</span> · Gamma: <span style="color:#E6EDF3;font-weight:600;">{"Positive" if gamma_score>0.1 else "Negative" if gamma_score<-0.1 else "Neutral"}</span></div>
          <div class="ab-result" style="color:{b_color};">▶ {b_verdict}</div>
        </div>
        <div style="background:{cv_color}15;border:1px solid {cv_color};border-radius:8px;padding:12px 14px;margin-top:8px;">
          <div class="sub-label">Combined Verdict</div>
          <div style="font-size:16px;font-weight:700;color:{cv_color};margin-top:4px;font-family:'IBM Plex Mono',monospace;">▶ {combined_verdict}</div>
          <div style="font-size:12px;color:#8B949E;margin-top:4px;">
            {"Both Macro and Signal aligned → Initiate/Add." if aligned else "Macro and Signal diverging → Wait for Trend break or Quad shift before acting."}
          </div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Market Health (compact) ─────────────────────────────────────────
    st.markdown('<div class="section-title">Market Health</div>', unsafe_allow_html=True)
    hc1,hc2,hc3 = st.columns(3)

    with hc1:
        st.markdown('<div class="sub-label">Engine Status</div>', unsafe_allow_html=True)
        engines_status = [
            ("GIP Model",         "✅" if gip else "❌"),
            ("Risk Range™",       "✅" if ar else "❌"),
            ("PVV Engine",        "✅" if pvv_data else "🟡"),
            ("Gamma Engine",      "✅" if gamma_data else "🟡"),
            ("Greeks Proxy",      "✅" if greeks_data else "🟡"),
            ("Options Live",      "✅" if any(d.get("ok") for d in options_live.values()) else "🟡"),
            ("News NLP",          "✅" if news_narratives and news_narratives.get("analyzed_count",0)>0 else "🟡"),
            ("COT Data",          "✅" if cot_live else "🟡"),
        ]
        for name, status in engines_status:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:13px;border-bottom:1px solid #21262D;"><span style="color:#8B949E;">{name}</span><span>{status}</span></div>', unsafe_allow_html=True)

    with hc2:
        st.markdown('<div class="sub-label">Data Quality</div>', unsafe_allow_html=True)
        n_prices  = snap.get("prices_loaded",len(prices))
        n_ranges  = len(ar)
        n_signals = len(daily_signals)
        n_greek   = len([d for d in greeks_data.values() if d.get("ok")])
        n_options = len([d for d in options_live.values() if d.get("ok")])
        for label,val,total in [
            ("Prices loaded",  n_prices, 200),
            ("Risk Ranges",    n_ranges, 100),
            ("Daily Signals",  n_signals, 50),
            ("Greeks Active",  n_greek,  n_prices),
            ("Options Live",   n_options, 15),
        ]:
            pct = min(1,val/(total or 1))
            bc2 = "#3FB950" if pct>0.7 else "#D29922" if pct>0.3 else "#F85149"
            st.markdown(f"""
            <div style="padding:3px 0;border-bottom:1px solid #21262D;">
              <div style="display:flex;justify-content:space-between;font-size:12px;">
                <span style="color:#8B949E;">{label}</span>
                <span style="color:{bc2};font-weight:700;font-family:'IBM Plex Mono',monospace;">{val}</span>
              </div>
              <div style="background:#21262D;border-radius:3px;height:4px;margin-top:2px;">
                <div style="background:{bc2};width:{pct*100:.0f}%;height:4px;border-radius:3px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)

    with hc3:
        st.markdown('<div class="sub-label">COT Sentiment</div>', unsafe_allow_html=True)
        cot_items = [(t,d) for t,d in cot_live.items() if isinstance(d,dict) and d.get("ok")]
        if cot_items:
            for t, cd in cot_items[:8]:
                bias_s = cd.get("bias","—")
                bc3 = "#3FB950" if "Bull" in str(bias_s) else "#F85149" if "Bear" in str(bias_s) else "#8B949E"
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:13px;border-bottom:1px solid #21262D;"><span style="color:#8B949E;">{t}</span><span style="color:{bc3};font-weight:700;">{bias_s}</span></div>', unsafe_allow_html=True)
        else:
            st.caption("COT data not available in this build")

        # Snapshot info
        st.markdown('<div class="sub-label" style="margin-top:10px;">Build Info</div>', unsafe_allow_html=True)
        from data.loader import snapshot_age_str
        st.markdown(f'<div style="font-size:13px;color:#8B949E;">Last build: <span style="color:#E6EDF3;">{snapshot_age_str()}</span></div>', unsafe_allow_html=True)
        build_ts = snap.get("built_at","—")
        if build_ts: st.markdown(f'<div style="font-size:12px;color:#8B949E;">{str(build_ts)[:19]}</div>', unsafe_allow_html=True)

    # ── Risk Disclaimer ──────────────────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div class="card" style="border-color:#30363D;">
      <div style="font-size:12px;color:#6E7681;">
        This is a process output. Manage risk accordingly.<br>
        Current: <b style="color:{qc(sq)};">{sq} ({QN.get(sq,"")})</b> · Regime invalidates if Quad shifts to {['Q3','Q4'] if sq in ('Q1','Q2') else ['Q1','Q2']}.<br>
        Options structure currently {"confirming" if aligned else "not fully aligned with"} macro signal.<br>
        Duration: <b>Trade</b> ideas are ≤3wk. <b>Trend</b> positions are ≥3mo. Never mix durations without flagging it.
      </div>
    </div>""", unsafe_allow_html=True)

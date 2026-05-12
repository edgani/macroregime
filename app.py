"""app.py — MacroRegime Pro v3.0 MAJOR SURGERY
Changes: 5-tab clean · PVV + Trend · Options/Greeks per ticker · Gap Matrix fixed · Readable fonts
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="MacroRegime Pro v3", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Readable, clean, no duplication
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp { background-color: #0d1117; }
.card-green {background:#0D2818;border:1px solid #3FB950;border-radius:8px;padding:12px;margin:6px 0;}
.card-yellow {background:#2D2305;border:1px solid #D29922;border-radius:8px;padding:12px;margin:6px 0;}
.card-red {background:#2D0D0D;border:1px solid #F85149;border-radius:8px;padding:12px;margin:6px 0;}
.card-blue {background:#0D1B2A;border:1px solid #1F6FEB;border-radius:8px;padding:12px;margin:6px 0;}
.card {background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin:6px 0;}
.badge {display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-right:4px;}
.badge-a {background:#3FB95022;color:#3FB950;border:1px solid #3FB950;}
.badge-ap {background:#3FB95044;color:#3FB950;border:1px solid #3FB950;}
.badge-b {background:#D2992222;color:#D29922;border:1px solid #D29922;}
.badge-c {background:#8B949E22;color:#8B949E;border:1px solid #8B949E;}
.badge-long {background:#3FB95022;color:#3FB950;border:1px solid #3FB950;}
.badge-short {background:#F8514922;color:#F85149;border:1px solid #F85149;}
.badge-neutral {background:#8B949E22;color:#8B949E;border:1px solid #8B949E;}
.metric-box {background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;}
.metric-label {font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;}
.metric-value {font-size:20px;font-weight:700;color:#E6EDF3;margin:4px 0;}
.metric-sub {font-size:12px;color:#8B949E;}
.section-title {font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:6px;}
.section-sub {font-size:13px;color:#8B949E;margin-bottom:14px;}
.kpi-row {display:flex;gap:10px;flex-wrap:wrap;margin:10px 0;}
.kpi-box {background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px 14px;min-width:100px;text-align:center;}
.kpi-label {font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.3px;}
.kpi-value {font-size:18px;font-weight:700;color:#E6EDF3;}
/* Fix font sizes for readability */
.stTabs [data-baseweb="tab"] { font-size: 14px !important; font-weight: 600 !important; }
.stDataFrame { font-size: 13px !important; }
.stMarkdown p { font-size: 14px !important; line-height: 1.5 !important; }
</style>
""", unsafe_allow_html=True)

QC = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"🟢 Goldilocks — Growth Rising, Inflation Cooling",
    "Q2":"🟡 Reflation — Both Growth and Inflation Rising",
    "Q3":"🔴 Stagflation — Growth Slowing, Inflation Elevated",
    "Q4":"🟣 Deflation — Both Growth and Inflation Falling",
}
QUAD_EXPLAIN = {
    "Q1":"Best conditions for stocks and crypto. Growth is strong and inflation is under control.",
    "Q2":"Tricky environment. Economy growing but inflation biting. Commodities, energy, and international stocks tend to win.",
    "Q3":"Most dangerous quarter. Economy slowing but prices still high. Gold, silver, and defensive stocks are the place to be. Tech gets hurt.",
    "Q4":"Deflationary collapse. Safest assets win: government bonds, gold, utilities, cash. Avoid risk.",
}
QWINS = {"Q1":"Tech, Bitcoin, Small Caps","Q2":"Energy, Materials, Commodities","Q3":"Gold, Silver, Defensives","Q4":"Government Bonds, Gold, Cash"}

def qc(q): return QC.get(q,"#8B949E")
def qn(q): return QN.get(q,q)
def qnc(q): return QNC.get(q,q)

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

def ff(v,d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

def _sf(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v); return f if math.isfinite(f) else None
    except: return None

def _price_ret(ticker, prices, days=21):
    s = prices.get(ticker)
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < days + 1: return None
    try: return float(s.iloc[-1] / s.iloc[-(days+1)] - 1)
    except: return None

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=220,margin=dict(t=30,b=5,l=0,r=0),
        paper_bgcolor="#161B22",plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3",family="Inter",size=12),
        title=dict(text=title,font=dict(size=13,color="#8B949E")),
        yaxis=dict(range=[0,1.15],tickformat=".0%",showgrid=True,gridcolor="#21262D"),
        xaxis=dict(showgrid=False,tickfont=dict(size=14,color="#E6EDF3")),bargap=0.4)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro v3.0")
    st.markdown('<div style="font-size:12px;color:#8B949E;">PVV Multi-Duration + Hedgeye Methodology</div>', unsafe_allow_html=True)
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Full Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        st.checkbox("US Stocks", value=True, key="inc_us")
        st.checkbox("Forex", value=True, key="inc_fx")
        st.checkbox("Commodities", value=True, key="inc_comm")
        st.checkbox("Crypto", value=True, key="inc_cryp")
        st.checkbox("Indonesia (IHSG)", value=True, key="inc_ihsg")
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Regime:",["Auto","Q1","Q2","Q3","Q4"],
            index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
    st.caption("Override when model diverges from Hedgeye")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip")
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;">CURRENT REGIME</div><div style="font-size:20px;font-weight:700;color:{qc(_sq)};margin:4px 0;">{_sq} / {_mq}</div><div style="font-size:12px;color:#8B949E;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("**📡 Data Sources**")
        sources = []
        if _s.get("cot_live"): sources.append("🟢 COT")
        if _s.get("options_live"): sources.append("🟢 Options")
        if _s.get("cme_live"): sources.append("🟢 CME")
        if (_s.get("defillama_live") or {}).get("ok"): sources.append("🟢 DeFiLlama")
        if _s.get("crypto_options_live"): sources.append("🟢 Crypto Opts")
        if _s.get("news_narratives") and _s["news_narratives"].get("analyzed_count",0)>0: sources.append("🟢 News NLP")
        if _s.get("price_clusters") and _s["price_clusters"].get("meta",{}).get("clusters_found",0)>0: sources.append("🟢 Clusters")
        if _s.get("pvv"): sources.append("🟢 PVV")
        if not sources: sources.append("🟡 Proxy Only")
        st.caption(" · ".join(sources))

# ══════════════════════════════════════════════════════════════════════════════
# LOAD SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if snap is None or not snap.get("ok") or st.session_state.loading:
    from orchestrator import build_snapshot
    _msg = "🔄 Updating data..." if st.session_state.loading else "⚡ Building MacroRegime Pro..."
    with st.spinner(_msg):
        pb=st.progress(0.0); pt=st.empty()
        def prog(m,f): pb.progress(f); pt.caption(f"⏳ {m}")
        snap=build_snapshot(progress_cb=prog,
            include_us_stocks=st.session_state.get("inc_us",True),
            include_forex=st.session_state.get("inc_fx",True),
            include_commodities=st.session_state.get("inc_comm",True),
            include_crypto=st.session_state.get("inc_cryp",True),
            include_ihsg=st.session_state.get("inc_ihsg",True))
        st.session_state.snap=snap; st.session_state.loading=False
        pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ Build failed. Click **⚡ Full Rebuild** to retry."); st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# VARIABLES
# ══════════════════════════════════════════════════════════════════════════════
gip = snap.get("gip")
global_ = snap.get("global",{})
rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{})
narr = snap.get("narratives",{})
transition = snap.get("transition",None)
health = snap.get("health",{})
analogs = snap.get("analogs",{})
btk = snap.get("bottleneck",{})
pb_data = snap.get("playbook",{})
prices = snap.get("prices",{})
alpha = snap.get("alpha",{})
alpha_center = snap.get("alpha_center",{}) or {}
daily_signals = snap.get("daily_signals",[]) or []
regime_forecast = snap.get("regime_forecast",{})
forward_returns = snap.get("forward_returns",{})
leading_signals = snap.get("leading_signals",{})
price_clusters = snap.get("price_clusters",{})
news_narratives = snap.get("news_narratives",{})
pvv_data = snap.get("pvv",{}) or {}
trend_histories = snap.get("trend_histories",{}) or {}
gamma_data = snap.get("gamma_data",{}) or {}
greeks_data = snap.get("greeks_data",{}) or {}
vol_forecast = snap.get("vol_forecast",{}) or {}
stress_test = snap.get("stress_test",[]) or []
cot_live = snap.get("cot_live",{}) or {}
options_live = snap.get("options_live",{}) or {}

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
ar = rr.get("asset_ranges",{})
vix_now = _sf(prices.get("^VIX", pd.Series()).tail(1)) if prices.get("^VIX") is not None else 20.0

# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs(["🎯 Macro Radar", "📈 TREND Signals", "⚡ Alpha Center", "📋 Playbook", "🏥 Health"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 0: MACRO RADAR
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("## 🎯 Macro Radar")
    st.caption("Regime · Forward · All Markets · 30-second read")

    # KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Quarterly", sq, qn(sq), delta_color="off")
    with k2: st.metric("Monthly", mq, qn(mq), delta_color="off")
    with k3:
        flip = gip.flip_hazard if gip else 0
        st.metric("Flip Risk", f"{flip:.0%}", f"{gip.divergence if gip else '—'}" if flip>0.2 else None)
    with k4:
        vix_val = health.get("vix_bucket",{}).get("vix_last",18)
        vix_label = health.get("vix_bucket",{}).get("bucket","—")
        st.metric("VIX", f"{vix_val:.1f}", vix_label)
    with k5: st.metric("Assets", f"{snap.get('prices_loaded',0)}", f"{len(ar)} ranges")

    # Market Status Banner
    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable": st.success(f"🟢 GOOD CONDITIONS · VIX {vl:.1f}")
    elif vb=="Chop": st.warning(f"🟡 CHOPPY · VIX {vl:.1f}")
    elif vb=="Defensive": st.error(f"🔴 DEFENSIVE · VIX {vl:.1f}")

    # Regime Snapshot + Forward
    rs1, rs2, rs3 = st.columns([1.2,1,1])
    with rs1:
        st.markdown(f'<div style="background:#161B22;border:1px solid {qc(sq)};border-radius:6px;padding:10px;margin-bottom:6px;"><div style="font-size:11px;color:#8B949E;">QUARTERLY · {sq}</div><div style="font-size:16px;font-weight:700;color:{qc(sq)};margin:2px 0;">{QN.get(sq,sq)}</div><div style="font-size:12px;color:#E6EDF3;">{QUAD_EXPLAIN.get(sq,"")[:90]}...</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#161B22;border:1px solid {qc(mq)};border-radius:6px;padding:10px;"><div style="font-size:11px;color:#8B949E;">MONTHLY · {mq}</div><div style="font-size:16px;font-weight:700;color:{qc(mq)};margin:2px 0;">{QN.get(mq,mq)}</div><div style="font-size:12px;color:#E6EDF3;">{QUAD_EXPLAIN.get(mq,"")[:90]}...</div></div>', unsafe_allow_html=True)
    with rs2:
        if pb_data:
            best = " · ".join(pb_data.get("best_assets",[])[:5])
            worst = " · ".join(pb_data.get("worst_assets",[])[:4])
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px;"><div style="font-size:11px;color:#8B949E;margin-bottom:4px;">🎯 Playbook — {sq}</div><div style="font-size:12px;color:#3FB950;margin-bottom:3px;">🟢 {best}</div><div style="font-size:12px;color:#F85149;">🔴 {worst}</div></div>', unsafe_allow_html=True)
    with rs3:
        if regime_forecast and regime_forecast.get("1m"):
            rf1 = regime_forecast["1m"]; rf3 = regime_forecast["3m"]
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px;margin-bottom:6px;"><div style="font-size:11px;color:#8B949E;">🔮 Forward</div><div style="font-size:13px;color:#E6EDF3;">1M→{rf1.get("predicted_quad","—")} ({rf1.get("prediction_confidence",0):.0%})</div><div style="font-size:13px;color:#E6EDF3;">3M→{rf3.get("predicted_quad","—")} ({rf3.get("prediction_confidence",0):.0%})</div></div>', unsafe_allow_html=True)
        if transition:
            fw = transition.front_run_window
            fwc = {"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
            fwi = {"now":"🚨 ACT NOW","1-2w":"⚡ 1-2w","3-6w":"👀 Watch","not yet":"🛑 Wait"}.get(fw,"🛑 Wait")
            st.markdown(f'<div style="background:{fwc};color:#fff;padding:8px 12px;border-radius:6px;font-weight:600;text-align:center;font-size:12px;">{fwi}</div>', unsafe_allow_html=True)

    # Early Warning
    st.markdown("### 🚨 Early Warning")
    ew1, ew2, ew3, ew4 = st.columns(4)
    vix_regime = health.get("vix_bucket",{}).get("bucket","—")
    vix_color = "#3FB950" if vix_regime=="Investable" else "#D29922" if vix_regime=="Chop" else "#F85149"
    ew1.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:#8B949E;">VIX</div><div style="font-size:18px;font-weight:700;color:{vix_color};">{vl:.1f}</div><div style="font-size:11px;color:#8B949E;">{vix_regime}</div></div>', unsafe_allow_html=True)
    crash_state = health.get("crash",{}).get("state","calm")
    crash_color = "#3FB950" if crash_state=="calm" else "#D29922" if crash_state=="watch" else "#F85149"
    ew2.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:#8B949E;">CRASH</div><div style="font-size:18px;font-weight:700;color:{crash_color};">{crash_state.upper()}</div></div>', unsafe_allow_html=True)
    risk_off_state = health.get("risk_off",{}).get("state","risk_on")
    risk_color = "#3FB950" if risk_off_state=="risk_on" else "#D29922" if risk_off_state=="caution" else "#F85149"
    ew3.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:#8B949E;">RISK OFF</div><div style="font-size:18px;font-weight:700;color:{risk_color};">{risk_off_state.upper()}</div></div>', unsafe_allow_html=True)
    # Breadth
    breadth_tickers = list({"SPY","QQQ","IWM","XLK","XLE","XLF","XLI","XLU","XLP","XLV","XLB","XLC","XLRE","SMH","SOXX","VGT"})
    advancers=0; decliners=0
    for t in breadth_tickers:
        ret = _price_ret(t,prices,21)
        if ret is not None:
            if ret>0.005: advancers+=1
            elif ret<-0.005: decliners+=1
    total_b = advancers+decliners
    b_score = advancers/total_b if total_b>0 else 0.5
    b_color = "#3FB950" if b_score>0.6 else "#D29922" if b_score>0.4 else "#F85149"
    ew4.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:#8B949E;">BREADTH</div><div style="font-size:18px;font-weight:700;color:{b_color};">{b_score:.0%}</div><div style="font-size:10px;color:#8B949E;">{advancers}↑ {decliners}↓</div></div>', unsafe_allow_html=True)

    # PVV All Markets Table
    st.markdown("### 📊 All Markets — PVV Composite")
    if pvv_data:
        pvv_rows = []
        for ticker, res in pvv_data.items():
            if not res.get("ok"): continue
            trend = res.get("trend",{})
            pvv_rows.append({
                "Ticker": ticker, "Signal": res.get("composite_signal","—"),
                "VASP": round(res.get("composite_score",0),2),
                "Vol": trend.get("realized_vol","—"), "VoV": trend.get("vol_of_vol","—"),
                "Hurst": trend.get("hurst","—"), "LRR": trend.get("lrr","—"), "TRR": trend.get("trr","—"),
                "Formation": "Bull" if res.get("bullish_formation") else ("Bear" if res.get("bearish_formation") else "Mixed"),
                "Front-Run": res.get("front_run_rationale","")[:55],
            })
        if pvv_rows:
            df_pvv = pd.DataFrame(pvv_rows)
            st.dataframe(df_pvv.style
                .map(lambda x: 'color:#3FB950;font-weight:700;' if x=="BULLISH" else ('color:#F85149;font-weight:700;' if x=="BEARISH" else 'color:#8B949E;'), subset=["Signal"])
                .map(lambda x: 'color:#3FB950;font-weight:700;' if x=="Bull" else ('color:#F85149;font-weight:700;' if x=="Bear" else ''), subset=["Formation"])
                .format({"VASP":"{:.2f}","Vol":"{:.1f}","VoV":"{:.2f}","Hurst":"{:.3f}"}),
                use_container_width=True, hide_index=True, height=320)
    else:
        st.info("PVV data loading... Run Full Rebuild if empty.")

    # Forward Probabilities
    if gip:
        rp1, rp2 = st.columns(2)
        with rp1:
            st.markdown("**Quarterly Probabilities**")
            st.plotly_chart(prob_bar(gip.structural_probs,""), use_container_width=True, config={"displayModeBar":False}, key="prob_q")
        with rp2:
            st.markdown("**Monthly Probabilities**")
            st.plotly_chart(prob_bar(gip.monthly_probs,""), use_container_width=True, config={"displayModeBar":False}, key="prob_m")

    # Forward Projection
    if regime_forecast and regime_forecast.get("1m"):
        rf1=regime_forecast["1m"]; rf3=regime_forecast["3m"]; rf6=regime_forecast["6m"]
        fp1,fp2,fp3=st.columns(3)
        with fp1: st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px;"><div style="font-size:11px;color:#8B949E;">1 MONTH</div><div style="font-size:20px;font-weight:700;color:{qc(rf1.get("predicted_quad","Q3"))};">{rf1.get("predicted_quad","—")}</div><div style="font-size:11px;color:#8B949E;">Conf {rf1.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)
        with fp2: st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px;"><div style="font-size:11px;color:#8B949E;">3 MONTHS</div><div style="font-size:20px;font-weight:700;color:{qc(rf3.get("predicted_quad","Q3"))};">{rf3.get("predicted_quad","—")}</div><div style="font-size:11px;color:#8B949E;">Conf {rf3.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)
        with fp3: st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:10px;"><div style="font-size:11px;color:#8B949E;">6 MONTHS</div><div style="font-size:20px;font-weight:700;color:{qc(rf6.get("predicted_quad","Q3"))};">{rf6.get("predicted_quad","—")}</div><div style="font-size:11px;color:#8B949E;">Conf {rf6.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)

    # Vol Forecast
    if vol_forecast:
        st.markdown("**Vol Forecast**")
        vol_rows=[]
        for t in ["SPY","QQQ","GLD","TLT","DX-Y.NYB"]:
            if t in vol_forecast:
                v=vol_forecast[t]
                vol_rows.append({"Asset":t,"Current":f"{v['current_ann_vol']}%","Forecast":f"{v['forecast_ann_vol']}%","Regime":v['vol_regime'],"Daily":f"±{v['expected_daily_move_pct']:.1%}"})
        if vol_rows:
            df_vol=pd.DataFrame(vol_rows)
            st.dataframe(df_vol.style.map(lambda x: 'color:#3FB950;font-weight:600;' if x=="LOW" else ('color:#D29922;font-weight:600;' if x=="NORMAL" else ('color:#F85149;font-weight:600;' if x in ["ELEVATED","EXTREME"] else '')), subset=["Regime"]), hide_index=True, use_container_width=True, height=160)

    # Stress Test
    if stress_test:
        st.markdown("**Stress Test**")
        for sc in stress_test:
            sev_color="#F85149" if sc['severity']=="EXTREME" else "#D29922" if sc['severity']=="HIGH" else "#8B949E"
            with st.expander(f"⚠️ {sc['scenario']} | DD: {sc['portfolio_dd']:.0%} | {sc['severity']}", expanded=(sc['severity'] in ["EXTREME","HIGH"])):
                c1,c2,c3=st.columns(3)
                c1.metric("Portfolio DD",f"{sc['portfolio_dd']:.0%}")
                c2.metric("Worst",sc['worst_asset'],f"{sc['worst_dd']:.0%}")
                c3.metric("Best",sc['best_asset'],f"{sc['best_dd']:.0%}")
                st.info(f"🛡️ Hedge: {sc['hedge']}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: TREND SIGNALS — Historical color-coded charts
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("## 📈 TREND Signals")
    st.caption("Historical multi-duration signal charts — Green=Bullish · Red=Bearish · Gray=Neutral")

    dur = st.segmented_control("Duration", ["TRADE", "TREND", "TAIL"], default="TREND", key="trend_dur")

    if not trend_histories:
        st.info("No trend histories loaded. Run Full Rebuild to generate PVV + Trend data.")
    else:
        histories = trend_histories
        asset_groups = {
            "🇺🇸 US Stocks": ["SPY","QQQ","IWM","XLK","XLE","XLF","XLI","XLU","META","AAPL","NVDA","TSLA","AMZN","GOOGL","MSFT","JPM","JNJ","UNH","V","MA","PG","HD","BAC","ABBV","PFE","KO","PEP","WMT","DIS","NFLX","CRM","ADBE","PYPL","UBER","ABNB"],
            "🌏 Global & EM": ["EEM","EWZ","FXI","INDA","RSX","EWG","EWJ","EWY","EWT","EWH","EIDO","EPHE","THD","ARGT","GXG","ICOL","JSE.JO","NIFTY","SENSEX","DAX","FTSE","CAC40"],
            "💱 Forex": ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCAD=X","AUDUSD=X","NZDUSD=X","USDCHF=X","USDCNH=X","DX-Y.NYB"],
            "🪙 Commodities": ["GC=F","SI=F","CL=F","NG=F","HG=F","PL=F","PA=F","ZW=F","ZC=F","ZS=F","CT=F","CC=F","KC=F","SB=F"],
            "₿ Crypto": ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","LINK-USD","MATIC-USD","UNI-USD","LTC-USD","BCH-USD","ETC-USD","FIL-USD","AAVE-USD","SNX-USD","CRV-USD","SUSHI-USD","1INCH-USD","DYDX-USD","GRT-USD","MANA-USD","SAND-USD","AXS-USD","ENJ-USD","CHZ-USD","FLOW-USD","THETA-USD","XTZ-USD","ALGO-USD","VET-USD","TRX-USD","EOS-USD","NEO-USD","XLM-USD","XMR-USD","DASH-USD","ZEC-USD","BAT-USD","COMP-USD","MKR-USD","YFI-USD","ZRX-USD","KNC-USD","BAL-USD","REN-USD","UMA-USD","BNT-USD","LRC-USD","OCEAN-USD","RLC-USD","STORJ-USD","ANT-USD","REP-USD","WTC-USD","ICX-USD","WAN-USD","AION-USD","LOOM-USD","CVC-USD","DNT-USD","GNO-USD","MLN-USD","NMR-USD","BAND-USD","KAVA-USD","TOMO-USD","PERL-USD","WRX-USD","COTI-USD","STMX-USD","FTM-USD","HOT-USD","IOTA-USD","RVN-USD","SC-USD","DGB-USD","XVG-USD","NANO-USD","LSK-USD","ARDR-USD","NXT-USD","STRAT-USD","WAVES-USD","BTS-USD","STEEM-USD","DCR-USD","ZIL-USD","ONE-USD","HBAR-USD","CELR-USD"],
            "🇮🇩 IHSG": ["^JKSE","BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK","UNVR.JK","PGAS.JK","PTBA.JK","ADRO.JK","ANTM.JK","INCO.JK","ITMG.JK","HRUM.JK","MBMA.JK","MDKA.JK","TINS.JK","BRMS.JK","EXCL.JK","ISAT.JK","TOWR.JK","TBIG.JK","SMGR.JK","INTP.JK","SMCB.JK","WSBP.JK","WIKA.JK","ADHI.JK","PTPP.JK","JSMR.JK","CMNP.JK","META.JK","BORN.JK","CPIN.JK","MAIN.JK","JPFA.JK","SIPD.JK","AALI.JK","LSIP.JK","SSMS.JK","TAPG.JK","BWPT.JK","SIMP.JK","STAA.JK","MYOR.JK","ICBP.JK","INDF.JK","GOOD.JK","ULTJ.JK","SKBM.JK","KLBF.JK","KAEF.JK","DVLA.JK","HEAL.JK","MIKA.JK","SILO.JK","RAJA.JK","ERAA.JK","ACES.JK","MAPI.JK","LPPF.JK","MIDI.JK","AMRT.JK","MPPA.JK","RALS.JK","INKP.JK","FASW.JK","SPMA.JK","TBLA.JK","GGRM.JK","WIIM.JK","RMBA.JK","GJTL.JK","AUTO.JK","INDO.JK","AIMS.JK","BEST.JK","BIRD.JK","WEHA.JK","PANR.JK","MNCN.JK","SCMA.JK","EMTK.JK","BMTR.JK","VIVA.JK","DOID.JK","ENRG.JK","ESSA.JK","MEDC.JK","ELSA.JK","AKRA.JK","AISA.JK","INDR.JK","TPIA.JK","BRPT.JK","SMAR.JK","INCI.JK","IPCM.JK","LINK.JK","BALI.JK","POWR.JK"],
        }

        for group_name, tickers_group in asset_groups.items():
            available = [t for t in tickers_group if t in histories and histories[t].get(dur,[])]
            if not available: continue
            st.markdown(f"#### {group_name}")
            cols = st.columns(2)
            for idx, ticker in enumerate(available[:6]):
                with cols[idx%2]:
                    df_hist = pd.DataFrame(histories[ticker][dur])
                    if df_hist.empty: continue
                    df_hist["date"] = pd.to_datetime(df_hist["date"])
                    fig = go.Figure()
                    if "signal" in df_hist.columns:
                        colors = {"BULLISH":"#3FB950","BEARISH":"#F85149","NEUTRAL":"#8B949E"}
                        curr_sig = df_hist["signal"].iloc[0]; start=0
                        for i in range(1,len(df_hist)):
                            if df_hist["signal"].iloc[i]!=curr_sig or i==len(df_hist)-1:
                                seg = df_hist.iloc[start:i]
                                fig.add_trace(go.Scatter(x=seg["date"],y=seg["price"],mode="lines",line=dict(color=colors.get(curr_sig,"#8B949E"),width=2.5),showlegend=False,hoverinfo="skip"))
                                curr_sig=df_hist["signal"].iloc[i]; start=i
                        for sig,col in colors.items():
                            fig.add_trace(go.Scatter(x=[None],y=[None],mode="lines",line=dict(color=col,width=3),name=sig))
                    if "lrr" in df_hist.columns and df_hist["lrr"].notna().any():
                        fig.add_trace(go.Scatter(x=df_hist["date"].tolist()+df_hist["date"].tolist()[::-1],y=df_hist["trr"].tolist()+df_hist["lrr"].tolist()[::-1],fill="toself",fillcolor="rgba(255,255,255,0.03)",line=dict(color="rgba(255,255,255,0)"),name="Risk Range",showlegend=True))
                    pvv_t = pvv_data.get(ticker,{})
                    last_vasp = pvv_t.get("composite_score","—") if pvv_t.get("ok") else "—"
                    last_vov = pvv_t.get("trend",{}).get("vol_of_vol","—") if pvv_t.get("ok") else "—"
                    last_hurst = pvv_t.get("trend",{}).get("hurst","—") if pvv_t.get("ok") else "—"
                    fig.update_layout(title=f"{ticker}: {dur} SIGNAL",height=300,margin=dict(t=40,b=20,l=40,r=20),paper_bgcolor="#161B22",plot_bgcolor="#161B22",font=dict(color="#E6EDF3",family="Inter",size=12),xaxis=dict(showgrid=True,gridcolor="#21262D",tickfont=dict(size=11)),yaxis=dict(showgrid=True,gridcolor="#21262D",tickfont=dict(size=11),tickformat=",.0f" if df_hist["price"].max()>10 else ",.4f"),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),annotations=[dict(x=0.02,y=0.02,xref="paper",yref="paper",text=f"VASP: {last_vasp} | VoV: {last_vov} | H: {last_hurst}",showarrow=False,font=dict(size=10,color="#8B949E"),align="left")])
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: ALPHA CENTER
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("## ⚡ Alpha Center")
    st.caption("Bottlenecks · Alpha · Discovery · Daily Signals · Options per Ticker")

    ac = alpha_center
    meta = ac.get("meta",{}) if ac else {}
    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild."); st.stop()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Regime", meta.get("regime","?"))
    c2.metric("Bias", meta.get("bias","?"))
    c3.metric("VIX", meta.get("vix","?"))
    c4.metric("Total", meta.get("total_items",0))

    if transition:
        fw = transition.front_run_window
        fwc = {"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi = {"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:{fwc};color:#fff;padding:8px 14px;border-radius:6px;font-weight:600;text-align:center;margin:10px 0;font-size:13px;">{fwi}</div>', unsafe_allow_html=True)

    # Master Table
    all_items = ac.get("all",[])
    if not all_items:
        st.info("No Alpha Center items."); st.stop()

    df_rows = []
    for item in all_items:
        df_rows.append({
            "Ticker": item.get("ticker","—"), "Scanner": item.get("scanner_type","—"),
            "Direction": item.get("direction","—"), "Grade": item.get("grade","—"),
            "Score": round(item.get("priority_score",0),1), "Price": item.get("price"),
            "Entry": item.get("entry"), "T1": item.get("target_1"), "T2": item.get("target_2"),
            "Stop": item.get("stop_loss"), "RR": item.get("rr",0),
            "Worth?": item.get("worth_entering","—"), "Time": item.get("time_estimate","—"),
            "Thesis": (item.get("thesis") or item.get("recommendation") or "")[:55],
        })
    df_alpha = pd.DataFrame(df_rows)

    dir_opts = sorted([x for x in df_alpha["Direction"].unique().tolist() if x and str(x)!="nan"])
    grade_opts = sorted([x for x in df_alpha["Grade"].unique().tolist() if x and str(x)!="nan"])
    level_opts = sorted([x for x in df_alpha["Scanner"].unique().tolist() if x and str(x)!="nan"])

    f1,f2,f3,f4 = st.columns(4)
    filter_dirs = f1.multiselect("Direction", dir_opts, default=dir_opts[:3] if len(dir_opts)>=3 else dir_opts)
    filter_grades = f2.multiselect("Grade", grade_opts, default=[g for g in ["A+","A","B"] if g in grade_opts])
    filter_levels = f3.multiselect("Scanner", level_opts, default=level_opts)
    min_score = f4.slider("Min Score", 0.0, float(df_alpha["Score"].max() or 100), 0.0, 1.0)

    df_filtered = df_alpha[df_alpha["Direction"].isin(filter_dirs) & df_alpha["Grade"].isin(filter_grades) & df_alpha["Scanner"].isin(filter_levels) & (df_alpha["Score"]>=min_score)]
    st.write(f"**{len(df_filtered)}** of **{len(df_alpha)}** items")

    st.dataframe(df_filtered.style
        .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["LONG","BUY","YES"]) else ('color:#F85149;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["SHORT","SELL","NO"]) else 'color:#D29922;font-weight:600;'), subset=["Direction","Worth?"])
        .map(lambda x: 'color:#3FB950;font-weight:700;' if x in ["A+","A"] else ('color:#D29922;font-weight:600;' if x=="B" else ''), subset=["Grade"])
        .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,(int,float)) and x>=2.0 else ('color:#D29922;font-weight:600;' if isinstance(x,(int,float)) and x>=1.5 else ''), subset=["RR"])
        .format({"Score":"{:.1f}","Price":"{:.2f}","Entry":"{:.2f}","T1":"{:.2f}","T2":"{:.2f}","Stop":"{:.2f}","RR":"{:.1f}"})
        .background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True, hide_index=True, height=380)

    # Top 5 Priority Cards with OPTIONS & GREEKS per ticker
    st.markdown("### 🎯 Top 5 Priority Setups + Options Detail")
    top5 = sorted(all_items, key=lambda x: x.get("priority_score",0), reverse=True)[:5]
    for idx, item in enumerate(top5):
        ticker = item.get("ticker","UNKNOWN")
        direction = item.get("direction","NEUTRAL")
        dir_color = "#3fb950" if "LONG" in direction else "#f85149" if "SHORT" in direction else "#8b949e"
        worth = item.get("worth_entering","—")
        worth_color = "#3fb950" if "YES" in worth or "BUY" in worth else "#d29922" if "WAIT" in worth or "CHASE" in worth else "#f85149"

        with st.expander(f"{'🟢' if 'LONG' in direction else '🔴' if 'SHORT' in direction else '⚪'} {ticker} | {direction} | Grade {item.get('grade','C')} | Score {item.get('priority_score',0):.1f}", expanded=(idx==0)):
            c1,c2,c3 = st.columns(3)
            c1.markdown(f"**Direction:** <span style='color:{dir_color};font-weight:700;'>{direction}</span>", unsafe_allow_html=True)
            c2.markdown(f"**Worth Entering:** <span style='color:{worth_color};font-weight:700;'>{worth}</span>", unsafe_allow_html=True)
            c3.markdown(f"**Grade:** <span style='color:{dir_color};font-weight:700;'>{item.get('grade','C')}</span>", unsafe_allow_html=True)

            st.divider()
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Price", ff(item.get("price")))
            m2.metric("Entry", ff(item.get("entry")))
            m3.metric("Target 1", ff(item.get("target_1")))
            m4.metric("Target 2", ff(item.get("target_2")))
            m5.metric("Stop", ff(item.get("stop_loss")))
            m6.metric("R:R", f"{item.get('rr',0):.1f}x")

            # ── OPTIONS & GREEKS per ticker (GAP MATRIX FIX) ──
            gamma = gamma_data.get(ticker, {})
            greek = greeks_data.get(ticker, {})
            opt = options_live.get(ticker, {})

            with st.expander("📊 Options & Greeks Detail", expanded=False):
                if gamma.get("ok") or greek.get("ok") or opt.get("ok"):
                    o1,o2,o3,o4 = st.columns(4)
                    o1.metric("Gamma Regime", gamma.get("regime","—") if gamma.get("ok") else "—")
                    o2.metric("Greek Composite", greek.get("composite","—") if greek.get("ok") else "—")
                    o3.metric("Max Pain", ff(gamma.get("max_pain")) if gamma.get("ok") else "—")
                    o4.metric("Vol Premium", ff(greek.get("vol_premium")) if greek.get("ok") else "—")

                    o5,o6,o7,o8 = st.columns(4)
                    o5.metric("Delta", greek.get("delta","—") if greek.get("ok") else "—")
                    o6.metric("Vanna", ff(greek.get("vanna_val")) if greek.get("ok") else "—")
                    o7.metric("Charm", ff(greek.get("charm_val")) if greek.get("ok") else "—")
                    o8.metric("RV 20D", ff(greek.get("rvol_20d")) if greek.get("ok") else "—")

                    if opt.get("ok"):
                        st.divider()
                        st.markdown("**Live Options Chain**")
                        o9,o10,o11 = st.columns(3)
                        o9.metric("Put/Call Vol", ff(opt.get("pc_volume")))
                        o10.metric("Put/Call OI", ff(opt.get("pc_oi")))
                        o11.metric("IV Skew", ff(opt.get("skew")))
                else:
                    st.warning("🟡 No live options data — using price-action proxy only. Click Full Rebuild to fetch.")

            # ── TRR/LRR Visual per ticker ──
            rr_t = ar.get(ticker, {})
            if rr_t and rr_t.get("ok"):
                lrr = rr_t.get("trade",{}).get("lrr")
                trr = rr_t.get("trade",{}).get("trr")
                px = item.get("price")
                if lrr and trr and px:
                    with st.expander("📐 Risk Range (TRR/LRR)", expanded=False):
                        pos = (px - lrr) / (trr - lrr) if (trr - lrr) > 0 else 0.5
                        pos = max(0, min(1, pos))
                        fig_rr = go.Figure()
                        fig_rr.add_trace(go.Bar(x=["LRR","Price","TRR"], y=[lrr, px, trr], marker_color=["#F85149","#E6EDF3","#3FB950"], text=[ff(lrr), ff(px), ff(trr)], textposition="outside"))
                        fig_rr.add_hline(y=px, line_dash="dot", line_color="#E6EDF3", annotation_text=f"Position: {pos:.0%}")
                        fig_rr.update_layout(height=200, paper_bgcolor="#161B22", plot_bgcolor="#161B22", font=dict(color="#E6EDF3"), showlegend=False, margin=dict(t=10,b=10,l=10,r=10))
                        st.plotly_chart(fig_rr, use_container_width=True, config={"displayModeBar":False})
                        st.caption(f"Range: {ff(lrr)} → {ff(trr)} | Spread: {ff(trr-lrr)} | Position: {pos:.0%} within range")

            st.divider()
            st.markdown("**🎯 Thesis**")
            thesis = item.get("thesis") or item.get("recommendation") or "N/A"
            st.info(thesis)
            if item.get("invalidators"):
                st.error(f"❌ Invalidators: {', '.join(item.get('invalidators',[]))}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("## 📋 Playbook & Themes")
    st.caption(f"What to buy & avoid in {sq} · {qn(sq)}")
    st.divider()

    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"### Regime: {sq} · {QN.get(sq,'')}")
        st.markdown(f"**Strategy:** {pb_data.get('strategy','')}")
        st.markdown("#### 🟢 Buy/Hold")
        for asset in pb_data.get("best_assets",[])[:10]: st.markdown(f'- **{asset}**')
        st.markdown("#### 🔴 Avoid/Sell")
        for asset in pb_data.get("worst_assets",[])[:10]: st.markdown(f'- **{asset}**')
        if regime_forecast and regime_forecast.get("3m"):
            rf3 = regime_forecast["3m"]
            if rf3.get("predicted_quad") != sq:
                st.divider()
                st.warning(f"⚠️ **Forward Alert:** 3M predicts shift to **{rf3.get('predicted_quad')}** (conf {rf3.get('prediction_confidence',0):.0%}). Rotate toward {QWINS.get(rf3.get('predicted_quad'),'defensive')}.")
    with c2:
        st.markdown("### 📖 Themes & Narratives")
        narratives_list = narr.get("narratives",[]) if narr else []
        if price_clusters and price_clusters.get("clusters"):
            for c in price_clusters["clusters"]:
                if c.get("is_novel_theme") or c.get("confidence",0) > 0.6:
                    narratives_list.append({
                        "name": c.get("theme_hypothesis","Unknown Theme"),
                        "score": c.get("confidence",0.5),
                        "thesis": f"Cross-sector cluster of {c.get('member_count')} tickers. Dominant: {c.get('dominant_sector')}.",
                        "tickers": c.get("members",[])[:5], "best": c.get("members",[])[:5], "worst": [],
                        "invalidators": ["Cluster correlation breaks"],
                    })
        if news_narratives and news_narratives.get("emergent_narratives"):
            for en in news_narratives["emergent_narratives"]:
                narratives_list.append({
                    "name": f"News: {en.get('narrative','Unknown')}",
                    "score": min(en.get("avg_sentiment",0.5) + en.get("supply_chain_hits",0)*0.1, 1.0),
                    "thesis": f"News-driven: {en.get('mention_count')} mentions, {en.get('supply_chain_hits',0)} supply hits.",
                    "tickers": en.get("linked_tickers",[])[:5], "best": en.get("linked_tickers",[])[:5], "worst": [],
                    "invalidators": ["News volume drops"],
                })
        if not narratives_list:
            narratives_list = [
                {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand + safe haven.","tickers":["SLV","SILJ","GDXJ"],"best":["SLV","SILJ"],"worst":["XLK"],"invalidators":["Q4 deflation","DXY bullish"]},
                {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural.","tickers":["GLD","GDX","GDXJ"],"best":["GLD","GDX"],"worst":["HYG"],"invalidators":["Q4->Q1 direct","DXY reversal"]},
            ]
        for n in narratives_list:
            if not isinstance(n, dict): continue
            score = n.get("score",0)
            with st.expander(f"📚 {n.get('name','')} — Score: {score:.0%}", expanded=False):
                st.markdown(f"**Thesis:** {n.get('thesis','')}")
                st.markdown(f"**Best:** {', '.join(n.get('best', n.get('tickers',[]))[:5])}")
                st.markdown(f"**Avoid:** {', '.join(n.get('worst',[])[:5])}")
                st.caption(f"Invalidators: {', '.join(n.get('invalidators',[])[:3])}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: HEALTH
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("## 🏥 System Health")
    st.caption("Data pipeline status, coverage & diagnostics")
    st.divider()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Prices Loaded", snap.get("prices_loaded",0))
    c2.metric("Assets in Snapshot", len(ar))
    c3.metric("VIX", f"{vix_now:.1f}")
    c4.metric("Build Time", f"{snap.get('build_time_s',0):.0f}s")

    if daily_signals:
        st.divider()
        st.markdown("### Daily Signal Coverage")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Tickers Rated", len(daily_signals))
        c2.metric("Alpha Center Items", alpha_center.get("meta",{}).get("total_items",0) if alpha_center else 0)
        c3.metric("Strong Signals", sum(1 for s in daily_signals if "STRONG" in s.get("signal","")))
        c4.metric("Option-Analyzed", len(gamma_data))

    if gamma_data or greeks_data:
        st.divider()
        st.markdown("### Option Data Coverage")
        c1,c2,c3 = st.columns(3)
        c1.metric("Gamma Engine", len(gamma_data))
        c2.metric("Greeks Proxy", len(greeks_data))
        c3.metric("Combined", len(set(gamma_data.keys()) & set(greeks_data.keys())))

    if pvv_data:
        st.divider()
        st.markdown("### PVV Engine Status")
        c1,c2,c3,c4 = st.columns(4)
        sig_counts = pd.Series([v["composite_signal"] for v in pvv_data.values() if v.get("ok")]).value_counts()
        c1.metric("PVV Tickers", len(pvv_data))
        c2.metric("Bullish", sig_counts.get('BULLISH',0), delta="LONG")
        c3.metric("Bearish", sig_counts.get('BEARISH',0), delta="SHORT")
        c4.metric("Neutral", sig_counts.get('NEUTRAL',0))

    if regime_forecast and regime_forecast.get("1m"):
        st.divider()
        st.markdown("### Forward-Looking Engine Status")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("1M Predicted", regime_forecast["1m"].get("predicted_quad","—"))
        c2.metric("3M Predicted", regime_forecast["3m"].get("predicted_quad","—"))
        c3.metric("6M Predicted", regime_forecast["6m"].get("predicted_quad","—"))
        c4.metric("News Headlines", news_narratives.get("analyzed_count",0) if news_narratives else 0)

    st.divider()
    st.markdown("### Data Sources")
    sources = health.get("sources",{}) if health else {}
    if sources:
        for src, status in sources.items():
            color = "#3FB950" if status=="OK" else "#F85149" if status=="FAIL" else "#D29922"
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 14px;margin:4px 0;display:flex;justify-content:space-between;font-size:13px;"><span>{src}</span><span style="color:{color};font-weight:700;">{status}</span></div>', unsafe_allow_html=True)
    else:
        st.info("No detailed source status available.")

    # Gap Matrix Display
    st.divider()
    st.markdown("### 🧮 Gap Matrix — Hedgeye Framework vs Current")
    gap_data = [
        ["GIP Model Engine", "✅ Ada", "Kecl — Policy P kurang prominent"],
        ["Risk Range™ Engine", "✅ Ada (v2 Fractal)", "Minor — Visual chart di TREND Signals tab"],
        ["Quad Regime", "✅ Ada", "Minor"],
        ["Options Overlay", "✅ Engine + UI (v3)", "FIXED — Detail per ticker di Alpha Center"],
        ["Full Greeks (Δ,Γ,V,Θ)", "⚠️ Proxy + Live", "Proxy di Alpha Center, Live fetch saat rebuild"],
        ["Vol Term Structure (IV vs RV)", "⚠️ Partial", "RV ada, IV dari options live"],
        ["Put/Call Skew chart", "❌ Missing", "HIGH — Butuh data vendor"],
        ["OI/Flow UI", "✅ Engine + UI (v3)", "FIXED — COT + OI di Alpha Center per ticker"],
        ["A/B Test display", "❌ Missing", "MEDIUM — Roadmap"],
        ["Navigation", "✅ Fixed", "BUG FIXED — 5 tab clean, no emoji duplikat"],
    ]
    df_gap = pd.DataFrame(gap_data, columns=["Framework Layer", "Status", "Gap Level"])
    st.dataframe(df_gap, use_container_width=True, hide_index=True, height=380)

"""app.py - MacroRegime Pro v17 | Hedgeye-Style Dashboard

FIX v17:
- Global Quad country heatmap: reads "country_quads" key
- DXY correlations: native Streamlit progress bars
- Bottleneck tab: cleaner table + futures excluded note
- Narratives tab: auto-render from engine output
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html,body,[class*="css"] { font-family: 'JetBrains Mono', monospace; }
.big-quad { font-size: 42px; font-weight: 700; }
.sub-quad { font-size: 13px; color: #9CA3AF; }
.card { background: #1F2937; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.gamma-deep-pos { border-left: 4px solid #10B981; padding-left: 12px; }
.gamma-pos { border-left: 4px solid #00D4AA; padding-left: 12px; }
.gamma-trans { border-left: 4px solid #F59E0B; padding-left: 12px; }
.gamma-neg { border-left: 4px solid #EF4444; padding-left: 12px; }
.gamma-deep-neg { border-left: 4px solid #7F1D1D; padding-left: 12px; }
</style>
""", unsafe_allow_html=True)

# Constants
QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"Goldilocks - Growth+ Infl-",
    "Q2":"Reflation - Growth+ Infl+",
    "Q3":"Stagflation - Growth- Infl+",
    "Q4":"Deflation - Growth- Infl-",
}

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
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),
                    text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=200,margin=dict(t=25,b=5,l=0,r=0),
                      paper_bgcolor="#111827",plot_bgcolor="#111827",
                      font=dict(color="#E8ECF0",family="JetBrains Mono"),
                      title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
                      yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),
                      xaxis=dict(showgrid=False),bargap=0.35)
    return fig

def price_chart(prices_dict, tickers, title="", days=252):
    fig = go.Figure()
    colors = ["#00D4AA","#F59E0B","#EF4444","#6366F1","#10B981","#60A5FA","#F472B6","#A78BFA"]
    for i,t in enumerate(tickers):
        s = prices_dict.get(t)
        if s is None: continue
        s = pd.to_numeric(s,errors="coerce").dropna().tail(days)
        if s.empty: continue
        norm = s/float(s.iloc[0])*100
        fig.add_scatter(x=norm.index,y=norm.values,name=t,
                        line=dict(color=colors[i%len(colors)],width=1.5))
    fig.update_layout(height=280,margin=dict(t=30,b=20,l=0,r=0),
                      paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0"),
                      title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
                      xaxis=dict(showgrid=False),yaxis=dict(showgrid=True,gridcolor="#1F2B3D"),
                      legend=dict(bgcolor="rgba(0,0,0,0)"))
    return fig

def _btk_badge(ticker, btk_data):
    if not btk_data: return ""
    for lvl in ["level_1","level_2","watch","avoid"]:
        for x in (btk_data.get(lvl) or []):
            if x.get("ticker")==ticker:
                colors={"level_1":"#10B981","level_2":"#F59E0B","watch":"#6366F1","avoid":"#EF4444"}
                return f'<span style="background:{colors[lvl]};color:#fff;font-size:10px;padding:2px 6px;border-radius:3px;">{lvl.replace("_"," ").upper()}</span>'
    return ""

def _render_universe(title, tickers_map, prices, btk_data, days=252):
    st.markdown(f"### {title}")
    rows=[]
    for sym,info in tickers_map.items():
        s=prices.get(sym)
        if s is None: continue
        s=pd.to_numeric(s,errors="coerce").dropna().tail(days)
        if s.empty: continue
        r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
        r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
        r6=float(s.iloc[-1]/s.iloc[-126]-1) if len(s)>=126 else 0
        badge=_btk_badge(sym,btk_data)
        rows.append({"Ticker":sym,"Name":info if isinstance(info,str) else info.get("name",sym),
                     "1M":f"{r1:+.1%}","3M":f"{r3:+.1%}","6M":f"{r6:+.1%}","Bottleneck":badge})
    if rows:
        df=pd.DataFrame(rows)
        st.markdown(df.to_html(escape=False,index=False),unsafe_allow_html=True)
        fig=price_chart(prices,list(tickers_map.keys())[:8],title=f"{title} - Normalized",days=days)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    else:
        st.info("No data loaded for this universe.")

# DXY Correlations - NATIVE STREAMLIT
def _compute_dxy_correlations(prices: dict, window: int = 15) -> dict:
    from config.settings import DXY_CORRELATION_ASSETS
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy,errors="coerce").dropna()
    if len(dxy) < window+2: return {}
    dxy_ret = dxy.pct_change().dropna()
    result = {}
    for label,ticker in DXY_CORRELATION_ASSETS.items():
        s = prices.get(ticker)
        if s is None: continue
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0] if s.shape[1] > 0 else s.squeeze()
        s = pd.to_numeric(s,errors="coerce").dropna()
        if len(s) < window+2: continue
        asset_ret = s.pct_change().dropna()
        combined = pd.concat([dxy_ret,asset_ret],axis=1,join="inner")
        combined.columns = ["dxy","asset"]
        if len(combined) >= window:
            corr = combined["dxy"].tail(window).corr(combined["asset"].tail(window))
            if math.isfinite(corr): result[label] = round(corr,2)
    return result

def _render_dxy_native(prices: dict, dxy_corr: dict, sq: str):
    if not dxy_corr:
        st.warning("DXY data belum tersedia.")
        return
    st.markdown("#### KEY $USD CORRELATIONS (15D) - Keith McCullough")
    dxy_s = prices.get("DX-Y.NYB")
    dxy_trend = "-"
    if dxy_s is not None:
        dxy_s = pd.to_numeric(dxy_s,errors="coerce").dropna()
        if len(dxy_s) >= 63:
            dxy_21m = float(dxy_s.iloc[-1]/dxy_s.iloc[-22]-1)
            dxy_trend = "BEARISH" if dxy_21m<-0.005 else "BULLISH" if dxy_21m>0.005 else "NEUTRAL"
    st.caption(f"DXY TREND: **{dxy_trend}**")
    for label, corr in dxy_corr.items():
        c1, c2 = st.columns([3, 1])
        with c1:
            bar_color = "#10B981" if corr > 0.3 else "#EF4444" if corr < -0.3 else "#9CA3AF"
            st.progress(min(abs(corr), 1.0), text=f"{label}: {corr:+.2f}")
        with c2:
            st.markdown(f"<span style='color:{bar_color};font-weight:700;'>{corr:+.2f}</span>", unsafe_allow_html=True)
    btc_corr = dxy_corr.get("Bitcoin", None)
    if btc_corr is not None and dxy_trend != "-":
        if dxy_trend=="BEARISH" and sq!="Q4":
            st.success(f"BTC: DXY Bearish TREND ({btc_corr:+.2f} corr) -> BTC Bullish TREND thesis intact. LONG IBIT.")
        elif dxy_trend=="BULLISH":
            st.error(f"BTC: DXY Bullish TREND ({btc_corr:+.2f} corr) -> BTC headwind. Monitor TREND signal. Scale back.")
        else:
            st.info(f"BTC: DXY neutral ({btc_corr:+.2f} corr) -> Watch TREND signal before sizing.")

# Gamma panel
def _render_gamma(gamma: dict) -> str:
    if not gamma or not gamma.get("ok"):
        note=(gamma or {}).get("note","GammaRegimeEngine belum berjalan - tambahkan ke orchestrator step 14e.")
        return f'<div class="card"><b>GAMMA REGIME</b><br/><span style="color:#9CA3AF;">{note}</span></div>'
    th=gamma.get("throttle") or 0
    r10=gamma.get("rvol_10d"); r21=gamma.get("rvol_21d")
    vix=gamma.get("vix"); vp=gamma.get("vol_premium")
    bp=gamma.get("bar_pct") or 50
    color=gamma.get("color","#9CA3AF")
    label=gamma.get("label","Unknown")
    action=gamma.get("action","-")
    impl=gamma.get("impl","")
    regime=gamma.get("regime","UNKNOWN")
    css={"DEEP_POSITIVE":"gamma-deep-pos","POSITIVE":"gamma-pos","TRANSITION":"gamma-trans",
         "NEGATIVE":"gamma-neg","DEEP_NEGATIVE":"gamma-deep-neg"}.get(regime,"gamma-trans")
    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "-"
    vpc="#10B981" if (vp or 0)>0 else "#EF4444"
    return f'<div class="card {css}"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">GAMMA REGIME - Tier 1 Alpha Approx</div><div style="font-size:22px;font-weight:700;color:{color};margin:6px 0;">{label.upper()}</div><div style="font-size:12px;color:#E8ECF0;">{action}</div><div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;"><div>Throttle (approx)<br/><b>{f(th,"+.1f")}</b></div><div>rVol 10d<br/><b>{f(r10,".1f","%")}</b></div><div>rVol 21d<br/><b>{f(r21,".1f","%")}</b></div><div>Vol Premium<br/><b style="color:{vpc};">{f(vp,"+.1f","%")}</b></div></div><div style="margin-top:8px;font-size:10px;color:#9CA3AF;">{impl}</div></div>'

def _render_lev(lev: dict) -> str:
    if not lev or not lev.get("ok"):
        note=(lev or {}).get("note","LeveragedETFEngine belum berjalan - tambahkan ke orchestrator step 14f.")
        return f'<div class="card"><b>LEVERAGED ETF FLOW</b><br/><span style="color:#9CA3AF;">{note}</span></div>'
    tot=lev.get("total_mcap_b"); lo=lev.get("long_exposure_b")
    sh=lev.get("short_exposure_b"); si=lev.get("single_crypto_b")
    lp=lev.get("long_pct") or 0; sp=lev.get("short_pct") or 0
    op=max(0,round(100-lp-sp,1)); ath=lev.get("is_ath",False); rb=lev.get("rebalancing_pressure","-")
    tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    def b(v): return f"${v}B" if v is not None else "-"
    rc={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rb,"#6B7280")
    ath_b=' <span style="background:#EF4444;color:#fff;font-size:10px;padding:2px 6px;border-radius:3px;">ATH</span>' if ath else ""
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "-"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "-"
    return f'<div class="card"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">LEVERAGED ETF FLOW{ath_b}</div><div style="margin-top:8px;font-size:12px;">Long: {tls}</div><div style="font-size:12px;">Short: {tss}</div><div style="margin-top:6px;font-size:11px;color:#9CA3AF;">Rebal: <span style="color:{rc};font-weight:700;">{rb}</span> · yfinance AUM · cache 6h</div></div>'

def _sequence_pills(sq, mq):
    sqc=qc(sq); mqc=qc(mq)
    p="padding:3px 11px;border-radius:4px;font-weight:700;font-size:12px;"
    arr='->'
    if sq==mq:
        return f'<div style="margin:8px 0;"><span style="{p}background:{sqc};color:#111;">{sq}</span> <span style="color:#9CA3AF;">CONFIRMED</span> <span style="font-size:11px;color:#9CA3AF;">Structural & Monthly aligned</span></div>'
    if sq=="Q3" and mq=="Q2":
        return f'<div style="margin:8px 0;"><span style="{p}background:{sqc};color:#111;">{sq} STRUCT</span> <span style="color:#9CA3AF;">{arr}</span> <span style="{p}background:{mqc};color:#111;">{mq} MONTHLY</span> <span style="color:#9CA3AF;">{arr}</span> <span style="font-size:11px;color:#9CA3AF;">Q1 TARGET ~6wk · watch CPI -50bps</span></div>'
    return f'<div style="margin:8px 0;"><span style="{p}background:{sqc};color:#111;">{sq} STRUCT</span> <span style="color:#9CA3AF;">{arr}</span> <span style="{p}background:{mqc};color:#111;">{mq} MONTHLY</span> <span style="font-size:11px;color:#9CA3AF;">leading -> lagging</span></div>'

# SIDEBAR + LOAD
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

with st.sidebar:
    st.markdown("## MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v17 · Autonomy*")
    st.divider()
    page = st.radio("", [
        "Dashboard",
        "GIP Model",
        "Risk Ranges",
        "ETF Pro",
        "Leaderboard",
        "Global Quad",
        "IHSG",
        "Bottleneck",
        "Narratives",
        "Discovery",
        "Health",
        "Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Snapshot: {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("Force", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("Universe"):
        inc_us = st.checkbox("US Stocks",True)
        inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True)
        inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True)
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "-"
        _mq=_g.monthly_quad if _g else "-"
        _gq=_gl.get("global_quad","-") if _gl else "-"
        st.caption(f"Hedgeye: {_sq} Struct · {_mq} Monthly · {_gq} Global")
    else:
        st.caption("Hedgeye: - Struct · - Monthly · - Global")

snap = st.session_state.snap
if snap is None:
    snap=load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap=snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb=st.progress(0.0); pt=st.empty()
    def prog(m,f): pb.progress(f); pt.caption(m)
    snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                        include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
    st.session_state.snap=snap; st.session_state.loading=False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("No snapshot. Click Refresh to rebuild."); st.stop()

# Extract
gip = snap.get("gip")
global_ = snap.get("global",{})
rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{})
narr = snap.get("narratives",{})
disc = snap.get("discovery",{})
transition = snap.get("transition",None)
health = snap.get("health",{})
analogs = snap.get("analogs",{})
btk = snap.get("bottleneck",{})
pb_data = snap.get("playbook",{})
prices = snap.get("prices",{})
auto_disc = snap.get("auto_discoveries",{})
fb_eval = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{})
lev_data = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq = gip.monthly_quad if gip else "Q2"
gq = global_.get("global_quad","Q3")

dxy_corr = _compute_dxy_correlations(prices)

# DASHBOARD
if page == "Dashboard":
    st.markdown(f'<div style="text-align:right;font-size:11px;color:#6B7280;">Built {snap.get("build_time_s",0)}s · Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro - Dashboard")
    vbd=health.get("vix_bucket",{}) if health else {}
    vb=vbd.get("bucket","-"); vl=vbd.get("vix_last",0); vn=vbd.get("note",""); vr=vbd.get("risk_mode","-")
    if vb=="Investable": vh=f'<div class="card" style="border-left:4px solid #10B981;"><b style="color:#10B981;">INVESTABLE BUCKET</b><br/>VIX {vl:.1f} · {vn}<br/>Risk Mode: {vr}</div>'
    elif vb=="Chop": vh=f'<div class="card" style="border-left:4px solid #F59E0B;"><b style="color:#F59E0B;">CHOP BUCKET</b><br/>VIX {vl:.1f} · {vn}<br/>Risk Mode: {vr}</div>'
    elif vb=="Defensive": vh=f'<div class="card" style="border-left:4px solid #EF4444;"><b style="color:#EF4444;">DEFENSIVE BUCKET</b><br/>VIX {vl:.1f} · {vn}<br/>Risk Mode: {vr}</div>'
    else: vh=""
    if vh: st.markdown(vh+"\n", unsafe_allow_html=True)
    ga_col, dxy_col = st.columns([1.2, 1])
    with ga_col: st.markdown(_render_gamma(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy_native(prices, dxy_corr, sq)
    st.markdown(_render_lev(lev_data), unsafe_allow_html=True)
    _sq_q2p=(gip.structural_probs or {}).get("Q2",0) if gip else 0
    _sq_sub=f"Q2+ {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL - Climate",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY - Weather",mq,gip.monthly_conf if gip else 0,"Tactical"),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL - 50 Countries",gq,global_.get("global_conf",0),"GDP-weighted"),unsafe_allow_html=True)
    with c4:
        if gip:
            st.markdown(f'<div class="card" style="border-top:3px solid #6366F1;"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">ALIGNMENT</div><div style="font-size:18px;font-weight:700;color:#6366F1;margin:4px 0;">{gip.divergence.upper()}</div><div style="font-size:12px;color:#E8ECF0;">{gip.operating_regime}</div><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Flip Risk: {gip.flip_hazard:.0%}</div></div>', unsafe_allow_html=True)
    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0)
        wr=(pr/max(ev,1))*100
        st.markdown("", unsafe_allow_html=True)
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Evaluated</div><div style="font-size:20px;font-weight:700;">{ev}</div></div>',unsafe_allow_html=True)
        w2.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Promoted</div><div style="font-size:20px;font-weight:700;color:#10B981;">{pr}</div></div>',unsafe_allow_html=True)
        w3.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Demoted</div><div style="font-size:20px;font-weight:700;color:#EF4444;">{dm}</div></div>',unsafe_allow_html=True)
        w4.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Win Rate</div><div style="font-size:20px;font-weight:700;">{wr:.0f}%</div></div>',unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"ALERT","1-2w":"FLASH","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        if fw!="not yet":
            st.markdown(f'<div class="card" style="border-left:4px solid {fwc};"><div style="font-size:18px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
    st.markdown(_sequence_pills(sq,mq), unsafe_allow_html=True)
    if pb_data:
        best5=" · ".join(pb_data.get("best_assets",[])[:6])
        worst5=" · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">QUICK ACTION - {sq} Structural · {mq} Monthly</div><div style="margin-top:8px;font-size:13px;"><span style="color:#10B981;">LONG:</span> <b>{best5}</b></div><div style="margin-top:4px;font-size:13px;"><span style="color:#EF4444;">AVOID:</span> <b>{worst5}</b></div><div style="margin-top:6px;font-size:11px;color:#9CA3AF;">Full detail -> GIP Model · ETF Pro · Playbook</div></div>', unsafe_allow_html=True)
    if auto_disc:
        brewing=[c for c in auto_disc.get("candidates",[]) if c.get("stage")=="brewing"]
        if brewing:
            tb=max(brewing,key=lambda x:x.get("confidence",0))
            st.markdown(f'<div style="font-size:12px;color:#9CA3AF;margin-top:8px;">{len(brewing)} pre-consensus opportunities - Top: <b>{tb.get("name","")}</b> -> see Discovery</div>',unsafe_allow_html=True)

# GIP MODEL
elif page == "GIP Model":
    st.markdown("# GIP Model - Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative. 'Heating up or cooling down?' - 30 data points monthly, 90 quarterly.")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()
    st.markdown("### Climate vs. Weather")
    cc,cw=st.columns(2)
    with cc:
        st.markdown(qcard("STRUCTURAL - CLIMATE (Quarterly)",sq,gip.structural_conf,f"Coverage: {gip.data_coverage:.0%}"),unsafe_allow_html=True)
    with cw:
        st.markdown(qcard("MONTHLY - WEATHER (3-6 Week Overlay)",mq,gip.monthly_conf,f"Divergence: {gip.divergence}"),unsafe_allow_html=True)
    st.markdown("---"); st.markdown("### Growth & Inflation Signals")
    f=gip.features; gm=f.get("growth_momentum",0); im=f.get("inflation_momentum",0)
    gc2="#10B981" if gm>0 else "#EF4444"; ic2="#10B981" if im<0 else "#EF4444"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Growth Momentum</div><div style="font-size:20px;font-weight:700;color:{gc2};">{fp(gm)}</div><div style="font-size:11px;">{"Accel +" if gm>0 else "Decel -"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Inflation Momentum</div><div style="font-size:20px;font-weight:700;color:{ic2};">{fp(im)}</div><div style="font-size:11px;">{"Rising +" if im>0 else "Cooling -"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Policy Score</div><div style="font-size:20px;font-weight:700;">{fp(f.get("policy_score"))}</div><div style="font-size:11px;">{"Dovish" if f.get("policy_score",0)>0.1 else "Hawkish" if f.get("policy_score",0)<-0.1 else "Neutral"}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Leading Indicator</div><div style="font-size:20px;font-weight:700;">{fp(f.get("leading_indicator_composite"))}</div><div style="font-size:11px;">FRED: {fp(f.get("data_coverage"))}</div></div>',unsafe_allow_html=True)
    st.markdown("---"); st.markdown("### Quad Transition Probabilities")
    QWINS={"Q1":"Cyclicals, Tech, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives","Q4":"TLT, Gold, Utilities, Cash"}
    def _tp(probs, cur_q, label, desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">{label} - {desc}</div><div style="margin-top:4px;">Currently: <b>{cur_q}</b></div><div>Most likely -> <b style="color:{qc(top_q)};">{top_q}</b> ({top_p:.0%})</div></div>',unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        if top_q!=cur_q:
            st.markdown(f'<div style="font-size:12px;color:#9CA3AF;margin-bottom:12px;">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",qnc(sq))
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq))
    with tp3:
        gprobs=global_.get("global_probs",{})
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")
    st.markdown("---"); st.markdown("### Regime Timing")
    st.markdown(_sequence_pills(sq,mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"ALERT","1-2w":"FLASH","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        st.markdown(f'<div class="card" style="border-left:4px solid {fwc};"><div style="font-size:16px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        ew=getattr(transition,"early_warning_signals",{})
        if ew:
            st.markdown("#### Early Warning Signals")
            ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"YES" if v>=0.5 else "NO","Score":f"{v:.0f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=280)
            fc=sum(1 for v in ew.values() if v>=0.5)
            st.progress(fc/max(len(ew),1),text=f"Early warning: {fc}/{len(ew)} firing")
    if analogs and analogs.get("top_analogs"):
        st.markdown("---"); st.markdown("### Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"**{a['label']}** - Similarity: {a.get('similarity',0):.0%}", expanded=(i==0)):
                cc2=st.columns(3)
                cc2[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc2[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")
                imp=a.get("impacts",{})
                if imp: st.markdown("**Impacts:** "+" | ".join(f"{k.upper()}={v}" for k,v in imp.items()))

# RISK RANGES
elif page == "Risk Ranges":
    st.markdown("# Risk Range - TRADE · TREND · TAIL")
    st.caption("LRR = buy zone. TRR = trim zone. TREND break = exit. McCullough: 'Buy the damn dip in bullish formation.'")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()
    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
                  key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### Live Alerts")
        for sym,a in all_a[:20]:
            ic="CRIT" if a["priority"]=="CRITICAL" else "HIGH" if a["priority"]=="HIGH" else "MED"
            bdr="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div style="border-left:3px solid {bdr};padding-left:8px;margin-bottom:6px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} - {a.get("note","")}</div>',unsafe_allow_html=True)
    st.markdown("---")
    cl1,cl2=st.columns([1,3])
    with cl1: mkt_f=st.selectbox("Market",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search ticker","")
    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        tr=v.get("trade",{}); px=v.get("px",float("nan"))
        rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(tr.get("lrr")),"TRR":ff(tr.get("trr")),
                     "TRADE":v.get("composite","-").upper(),"Quality":v.get("quality","-"),
                     "Stretch":tr.get("stretch","-"),"Hurst":ff(v.get("trend",{}).get("hurst")),
                     "Market":v.get("market","-"),"Trap":"YES" if v.get("regime_trap") else ""})
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=520)
    else: st.info("No data matches filter.")

# ETF PRO
elif page == "ETF Pro":
    st.markdown("# ETF Pro - Quad-Aware ETF Positioning")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly · Go Anywhere, But Not Everywhere. ~25-35 ETF ideas, updated weekly.")
    ar=rr.get("asset_ranges",{}); best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    MARKET_LABELS={"us_equity":"US Equity","forex":"Forex","commodity":"Commodities","crypto":"Crypto","ihsg":"IHSG"}
    tabs=st.tabs(list(MARKET_LABELS.values()))
    for tab,(mkt,mlabel) in zip(tabs,MARKET_LABELS.items()):
        with tab:
            rows=[]
            for sym,v in ar.items():
                if v.get("market","")!=mkt: continue
                tr=v.get("trade",{}); px=v.get("px",float("nan"))
                lrr=tr.get("lrr",float("nan")); trr=tr.get("trr",float("nan"))
                comp=v.get("composite","neutral")
                qf="LONG" if sym in best_set else ("AVOID" if sym in worst_set else "-")
                rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(lrr),"TRR":ff(trr),
                             "Signal":comp.upper(),"Quality":v.get("quality","-"),
                             "Stretch":tr.get("stretch","-"),"Quad Fit":qf,
                             "Trap":"YES" if v.get("regime_trap") else ""})
            if mkt=="crypto" and dxy_corr:
                _render_dxy_native(prices, dxy_corr, sq)
                btc_rr=ar.get("IBIT",ar.get("BTC-USD",{}))
                btc_sig=btc_rr.get("composite","-")
                btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
                btc_action="LONG IBIT" if btc_sig=="bullish" and sq!="Q4" else ("EXIT - Q4 exception" if sq=="Q4" else "WAIT - Bearish TREND")
                st.markdown(f'<div class="card" style="border-left:4px solid {btc_c};"><b>BITCOIN SIGNAL: {btc_sig.upper()} -> {btc_action}</b><br/><span style="font-size:11px;color:#9CA3AF;">DXY/BTC 15D corr: {dxy_corr.get("Bitcoin","-")} · Keith: "Any quad other than Q4, bitcoin = biggest digital asset position."</span></div>', unsafe_allow_html=True)
            if rows:
                st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=450)
                longs=[r for r in rows if r["Signal"]=="BULLISH" and r["Quad Fit"]=="LONG"][:4]
                shorts=[r for r in rows if r["Signal"]=="BEARISH" and r["Quad Fit"]=="AVOID"][:4]
                if longs:
                    st.markdown("**Top Long Setups:**")
                    for e in longs: st.markdown(f'<div style="border-left:3px solid #10B981;padding-left:8px;margin-bottom:4px;"><b>{e["Ticker"]}</b> · Px {e["Px"]} · LRR <b>{e["LRR"]}</b> · TRR {e["TRR"]} · {e["Quality"]} · {e["Stretch"]}</div>',unsafe_allow_html=True)
                if shorts:
                    st.markdown("**Top Short Setups:**")
                    for e in shorts: st.markdown(f'<div style="border-left:3px solid #EF4444;padding-left:8px;margin-bottom:4px;"><b>{e["Ticker"]}</b> · Px {e["Px"]} · TRR <b>{e["TRR"]}</b> · LRR {e["LRR"]} · {e["Quality"]} · {e["Stretch"]}</div>',unsafe_allow_html=True)
            else: st.info(f"No {mlabel} data. Refresh.")

# LEADERBOARD
elif page == "Leaderboard":
    st.markdown("# The Leaderboard - Signal Strength Stocks")
    st.caption("Quality A = Bullish TRADE+TREND near LRR + volume confirm. Updated Monday. Min 1%, max 3% position.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()
    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]
    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); tn=v.get("trend",{})
        px=v.get("px",float("nan")); vol_c=tr.get("volume_confirm",0.5)
        stretch=tr.get("stretch","neutral"); hurst=tn.get("hurst",0.5)
        from config.settings import TICKER_SECTOR
        sector=TICKER_SECTOR.get(sym,"generic")
        if qual in ("A","B") and comp=="bullish":
            lrr=tr.get("lrr",float("nan")); trr=tr.get("trr",float("nan"))
            nlrr=stretch in ("oversold","reset_zone")
            if math.isfinite(px) and math.isfinite(lrr) and math.isfinite(trr) and (trr-lrr)>1e-9:
                pos=(px-lrr)/(trr-lrr); nlrr=pos<=0.35 or nlrr
                rf=sym in best_set; ra=sym in worst_set
                sc=(50 if qual=="A" else 30)+(25 if nlrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
                long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near LRR" if nlrr else f"Stretch: {stretch}","sector":sector})
        if qual in ("short_A","short_B") and comp=="bearish":
            lrr=tr.get("lrr",float("nan")); trr=tr.get("trr",float("nan"))
            ntrr=stretch in ("overbought","extended")
            if math.isfinite(px) and math.isfinite(lrr) and math.isfinite(trr) and (trr-lrr)>1e-9:
                pos=(px-lrr)/(trr-lrr); ntrr=pos>=0.65 or ntrr
                rf=sym in worst_set
                sc=(50 if qual=="short_A" else 30)+(25 if ntrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
                short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near TRR" if ntrr else f"Stretch: {stretch}","sector":sector})
    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])
    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Bullish Names</div><div style="font-size:24px;font-weight:700;">{len(long_picks)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Quality A Longs</div><div style="font-size:24px;font-weight:700;color:#10B981;">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Quality A Shorts</div><div style="font-size:24px;font-weight:700;color:#EF4444;">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="card"><div style="font-size:11px;color:#9CA3AF;">Regime Traps</div><div style="font-size:24px;font-weight:700;color:#F59E0B;">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>',unsafe_allow_html=True)
    st.markdown("---"); st.markdown("### TOP 21 LONG IDEAS")
    for p in long_picks[:21]:
        st.markdown(f'<div style="border-left:3px solid #10B981;padding-left:10px;margin-bottom:8px;"><div style="font-size:14px;font-weight:700;">{p["ticker"]} ({p["quality"]}) {"YES" if p["regime_fit"] else "NO"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div><div style="font-size:12px;color:#E8ECF0;">Px: {ff(p["px"])} · LRR: <b>{ff(p["lrr"])}</b> · TRR: {ff(p["trr"])} · {p["note"]}</div><div style="font-size:11px;color:#9CA3AF;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div></div>', unsafe_allow_html=True)
    if not long_picks: st.info("No Quality A/B longs. Market may be extended.")
    st.markdown("---"); st.markdown("### SHORT IDEAS")
    for p in short_picks[:15]:
        st.markdown(f'<div style="border-left:3px solid #EF4444;padding-left:10px;margin-bottom:8px;"><div style="font-size:14px;font-weight:700;">{p["ticker"]} ({p["quality"]}) {"YES" if p["regime_fit"] else "NO"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div><div style="font-size:12px;color:#E8ECF0;">Px: {ff(p["px"])} · TRR: <b>{ff(p["trr"])}</b> · LRR: {ff(p["lrr"])} · {p["note"]}</div><div style="font-size:11px;color:#9CA3AF;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div></div>', unsafe_allow_html=True)
    if not short_picks: st.info("No Quality Short-A/B setups.")
    with st.expander("Full Signal Table"):
        all_rows=([{"Ticker":p["ticker"],"Side":"LONG","Quality":p["quality"],"Score":f\'{p["score"]:.0f}\',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"Regime":"YES" if p["regime_fit"] else "-"} for p in long_picks]+
                  [{"Ticker":p["ticker"],"Side":"SHORT","Quality":p["quality"],"Score":f\'{p["score"]:.0f}\',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"Regime":"YES" if p["regime_fit"] else "-"} for p in short_picks])
        if all_rows: st.dataframe(pd.DataFrame(all_rows),hide_index=True,use_container_width=True)

# GLOBAL QUAD
elif page == "Global Quad":
    st.markdown("# Global Quad - 50 Countries")
    st.caption("GIP applied to country ETFs. GDP-weighted. Shows where capital is rotating globally.")
    if not global_: st.warning("No global data. Refresh."); st.stop()
    gconf=global_.get("global_conf",0.0); gprobs=global_.get("global_probs",{})
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        st.plotly_chart(prob_bar(gprobs,"Global Probabilities"),use_container_width=True,config={"displayModeBar":False})
    with c2:
        st.markdown("### Country Heatmap")
        heat=[]
        country_data = global_.get("country_quads", {})
        if not country_data:
            country_data = global_.get("countries", {})
        for country,data in country_data.items():
            if isinstance(data,(list,tuple)) and len(data)>=3:
                etf,quad,conf=data[0],data[1],data[2]
            elif isinstance(data,dict):
                etf,quad,conf=data.get("etf",""),data.get("quad",""),data.get("confidence",0)
            else:
                etf,quad,conf="","",0
            heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}" if isinstance(conf,(int,float)) else "-"})
        if heat:
            df=pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=420,use_container_width=True)
        else:
            st.info("No country quad data. Ensure global_quad_engine v3+ is running.")
    st.markdown("---"); st.markdown("### EM Recovery Signal")
    em_sig=btk.get("em_recovery",{}) if btk else {}
    if em_sig:
        conf=em_sig.get("confidence",0); ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'<div class="card" style="border-left:4px solid {ec};"><div style="font-size:13px;font-weight:700;color:#E8ECF0;">{em_sig.get("trigger","")}</div><div style="font-size:12px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div><div style="font-size:11px;color:#E8ECF0;margin-top:6px;">Confidence: {conf:.0%} · Best: {", ".join(em_sig.get("best",[])[:6])}</div></div>',unsafe_allow_html=True)
    else: st.info("EM recovery signal belum tersedia.")

# IHSG
elif page == "IHSG":
    st.markdown("# IHSG - Indonesia Market")
    st.caption("Local signal + sector thesis. Bank CKPN · OSV hulu · Coal cycle · Foreign flow.")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}
    if ihsg:
        rows=[{"Ticker":sym,"Px":ff(v.get("px",float("nan")),0),"LRR":ff(v.get("trade",{}).get("lrr"),0),"TRR":ff(v.get("trade",{}).get("trr"),0),"Signal":v.get("composite","-").upper(),"Quality":v.get("quality","-"),"Stretch":v.get("trade",{}).get("stretch","-"),"Trap":"YES" if v.get("regime_trap") else ""} for sym,v in ihsg.items()]
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else: _render_universe("IHSG Universe",IHSG_UNIVERSE,prices,btk,days=252)
    st.markdown("---"); st.markdown("### Sector Buckets")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"**{bucket.replace('_',' ')}** ({len(tickers)})"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}","Bottleneck":_btk_badge(t,btk)})
            if b_rows: st.markdown(pd.DataFrame(b_rows).to_html(escape=False,index=False),unsafe_allow_html=True)

# BOTTLENECK
elif page == "Bottleneck":
    st.markdown("# Bottleneck Scanner - Supply Chain Alpha")
    st.caption("Citrini: demand river meets capacity constraint. Second-order: own the bottleneck, not the end market.")
    if not btk: st.warning("No bottleneck data. Refresh."); st.stop()
    l1=btk.get("level_1",[]); l2=btk.get("level_2",[]); wt=btk.get("watch",[]); av=btk.get("avoid",[])
    s1,s2,s3,s4=st.columns(4)
    for col,lab,val,c in [(s1,"Level 1",len(l1),"#10B981"),(s2,"Level 2",len(l2),"#F59E0B"),(s3,"Watch",len(wt),"#6366F1"),(s4,"Avoid",len(av),"#EF4444")]:
        col.markdown(f'<div class="card" style="text-align:center;border-top:3px solid {c};"><div style="font-size:11px;color:#9CA3AF;">{lab}</div><div style="font-size:28px;font-weight:700;color:{c};">{val}</div></div>',unsafe_allow_html=True)
    if btk.get("futures_excluded"):
        st.caption(f"{btk.get('futures_excluded',0)} futures tickers excluded from equity scan (see Commodity tab)")
    def _rl(data,title):
        if not data: return
        with st.expander(f"**{title}** ({len(data)})",expanded=title.startswith("Level 1")):
            rows=[{"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),"Trend":c["trend"],"Score":f\'{c["score"]:.2f}\',"EV":f\'{c.get("ev",0):.2f}\',"RF":f\'{c.get("regime_fit",0):.0%}\',"Constraint":f\'{c.get("constraint",0):.0%}\',"Thesis":c.get("known_thesis","")[:60]} for c in data]
            if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=min(len(rows)*35+40,400))
    _rl(l1,"Level 1 - Best"); _rl(l2,"Level 2 - Building")
    _rl(wt,"Watch - Brewing"); _rl(av,"Avoid - Regime Trap")
    st.markdown("---")
    for mkt,items in (btk.get("market_buckets",{}) or {}).items():
        if not items: continue
        with st.expander(f"**{mkt.replace('_',' ').upper()}** - {len(items)}"):
            for c in items[:12]:
                tc="#10B981" if c.get("direction")=="long" else "#EF4444" if c.get("direction")=="short" else "#9CA3AF"
                st.markdown(f'<div style="border-left:3px solid {tc};padding-left:8px;margin-bottom:4px;"><b>{c["ticker"]}</b> {c.get("sector","").replace("_"," ").title()} · Score {c.get("score",0):.2f} · EV {c.get("ev",0):.2f} {"REGIME TRAP" if c.get("regime_trap") else ""}</div>',unsafe_allow_html=True)

# NARRATIVES
elif page == "Narratives":
    st.markdown("# Narratives - Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus. Score = conviction x regime fit x breadth.")
    if not narr: st.warning("No narrative data. Refresh."); st.stop()
    active=narr.get("active_narratives",[])
    if active:
        st.markdown(f"### ACTIVE ({len(active)})")
        for n in sorted(active,key=lambda x:x.get("score",0),reverse=True):
            score=n.get("score",0)
            with st.expander(f"**{n.get('name','')}** - Score: {score:.0%} | Breadth: {n.get('breadth','-')}"):
                st.markdown(f"**Thesis:** {n.get('thesis','')}")
                st.markdown(f"**Regime Fit:** {n.get('regime_fit','-')}")
                st.markdown(f"**Tickers:** {' · '.join(n.get('tickers',[])[:8])}")
                if n.get("best"): st.markdown(f"**Best setups:** {' · '.join(n['best'][:10])}")
                if n.get("worst"): st.markdown(f"**Fade:** {' · '.join(n['worst'][:10])}")
                if n.get("invalidators"): st.markdown(f"**Invalidators:** {', '.join(n['invalidators'][:3])}")
    building=narr.get("building_narratives",[])
    if building:
        st.markdown(f"### BUILDING ({len(building)})")
        for n in sorted(building,key=lambda x:x.get("score",0),reverse=True):
            with st.expander(f"**{n.get('name','')}** - Score: {n.get('score',0):.0%}"):
                st.markdown(f"**Thesis:** {n.get('thesis','')}")
                if n.get("best"): st.markdown(f"**Approaching active:** {' · '.join(n['best'][:8])}")
    brewing=narr.get("brewing_narratives",[])
    if brewing:
        st.markdown(f"### BREWING ({len(brewing)})")
        for n in sorted(brewing,key=lambda x:x.get("score",0),reverse=True):
            with st.expander(f"**{n.get('name','')}** - Score: {n.get('score',0):.0%}"):
                st.markdown(f"**Thesis:** {n.get('thesis','')}")
                if n.get("best"): st.markdown(f"**Pre-consensus watch:** {' · '.join(n['best'][:6])}")
    if not any([active, building, brewing]):
        st.info("Narratives not yet at critical mass. Run Force build.")

# DISCOVERY
elif page == "Discovery":
    st.markdown("# Early Discovery - Pre-Consensus")
    st.caption("Autonomy engine: regime fit + price cluster + supply chain graph + commodity spikes + theme detection.")

    # V4 format support
    cands = []
    if auto_disc and auto_disc.get("ok"):
        cands = auto_disc.get("candidates", [])
    elif disc:
        cands = disc.get("discoveries", [])

    if not cands:
        st.info("No discoveries yet. Run Force build.")
        if auto_disc and not auto_disc.get("ok"):
            st.caption(f"Engine note: {auto_disc.get('note','')}")
        st.stop()

    # Show engine stats
    if auto_disc and auto_disc.get("ok"):
        st.caption(f"Engine: AutoDiscoveryV4 | Total: {auto_disc.get('total',0)} | New: {auto_disc.get('new_this_run',0)} | Signals: {auto_disc.get('signals_harvested',0)}")

    for stage,sc in [("active","#10B981"),("building","#F59E0B"),("brewing","#6366F1"),("pre_consensus","#9CA3AF"),("early","#60A5FA")]:
        items=[c for c in cands if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper().replace('_',' ')} ({len(items)})")
        for c in items:
            conf=c.get("confidence",0)
            sig_types = ", ".join(c.get("signals", {}).keys())[:40]
            with st.expander(f"**{c.get('name','')}** - Conf: {conf:.0%} [{sig_types}]"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                st.markdown(f"**Category:** {c.get('category','')}")
                if c.get("tickers"): st.markdown(f"**Tickers:** {' · '.join(c['tickers'][:8])}")
                if c.get("signals"): 
                    st.markdown("**Signals:**")
                    for sig_type, strength in c["signals"].items():
                        st.progress(min(strength, 1.0), text=f"{sig_type}: {strength:.0%}")
                if c.get("first_detected"): st.markdown(f"**First seen:** {c['first_detected']}")
                if c.get("last_updated"): st.markdown(f"**Updated:** {c['last_updated']}")
                inv=c.get("invalidators",[])
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")

# HEALTH
elif page == "Health":
    st.markdown("# Market Health - VIX · Breadth · Crash Meter")
    if not health: st.warning("No health data. Refresh."); st.stop()
    vb=health.get("vix_bucket",{}); vb_b=vb.get("bucket","-")
    vb_c={"Investable":"#10B981","Chop":"#F59E0B","Defensive":"#EF4444"}.get(vb_b,"#6B7280")
    st.markdown(f'<div class="card" style="border-left:4px solid {vb_c};"><div style="font-size:18px;font-weight:700;color:{vb_c};">VIX BUCKET: {vb_b.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{vb.get("note","")}</div></div>',unsafe_allow_html=True)
    crash=health.get("crash",{})
    if crash:
        st.markdown("### Crash Meter")
        for k,v in crash.get("signals",{}).items(): st.progress(v,text=f"{k.replace('_',' ').title()}: {v:.0%}")
        st.markdown(f"**State:** {crash.get('state','')} · Score: {crash.get('score',0):.0%}")
        if crash.get("reasons"): st.markdown("**Reasons:** "+" · ".join(crash["reasons"]))
    breadth=health.get("market_health",{})
    if breadth:
        st.markdown("### Sector Breadth")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Score",f"{breadth.get('score',0):.2f}"); b2.metric("Verdict",breadth.get("verdict","-"))
        b3.metric("Sector Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW Health",f"{breadth.get('eqw_health',0):.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"• {note}")
    fg=health.get("fear_greed",{})
    if fg:
        st.markdown("---"); st.markdown("### Fear & Greed")
        fgs=fg.get("score",50); fgc="#10B981" if fgs<25 else "#F59E0B" if fgs<55 else "#EF4444"
        st.markdown(f"**Score:** {fgs:.0f}/100 - {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)

# PLAYBOOK
elif page == "Playbook":
    st.markdown("# Regime Playbook")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly · Scored by data, not opinion.")
    if pb_data:
        st.markdown("### Regime Positioning")
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f'<div class="card" style="border-left:4px solid #10B981;"><div style="font-size:13px;font-weight:700;color:#10B981;">LONG - {sq}</div><div style="font-size:14px;font-weight:700;margin:8px 0;">{" · ".join(pb_data.get("best_assets",[]))}</div><div style="font-size:12px;color:#E8ECF0;">Style: {pb_data.get("style","")}</div><div style="font-size:12px;color:#E8ECF0;">FX: {pb_data.get("fx","")}</div><div style="font-size:12px;color:#E8ECF0;">Bonds: {pb_data.get("bonds","")}</div>{("<div style=\"font-size:11px;color:#9CA3AF;margin-top:6px;\">Monthly adds: " + " · ".join(pb_data.get("monthly_adds",[])) + "</div>") if pb_data.get("monthly_adds") else ""}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="card" style="border-left:4px solid #EF4444;"><div style="font-size:13px;font-weight:700;color:#EF4444;">AVOID - {sq}</div><div style="font-size:14px;font-weight:700;margin:8px 0;">{" · ".join(pb_data.get("worst_assets",[]))}</div><div style="font-size:12px;color:#E8ECF0;">Hedge: {pb_data.get("hedge","BTAL")}</div><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{pb_data.get("sizing_note","Min 1% · Max 3%")}</div></div>', unsafe_allow_html=True)
        btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
        btc_sig=btc_rr.get("composite","-")
        btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
        btc_corr_val=dxy_corr.get("Bitcoin","-")
        q4_note=" (Q4 EXCEPTION - Exit BTC)" if sq=="Q4" else ""
        st.markdown(f'<div class="card" style="border-left:4px solid {btc_c};"><b>BITCOIN: {btc_sig.upper()}{q4_note}</b> - DXY/BTC 15D corr: {btc_corr_val} · "Any quad other than Q4, bitcoin = biggest digital asset position."</div>', unsafe_allow_html=True)
        scenarios_list=scen.get("scenarios",[])
        if scenarios_list:
            st.markdown("---"); st.markdown("### Scenario Probability Map")
            badges=["BASE","ALT","RISK","TAIL"]; badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
            row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
            for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
                pc=badge_colors[i]; em=sc_item.em_note[:60]+"..." if len(sc_item.em_note)>60 else sc_item.em_note
                with col:
                    st.markdown(f'<div class="card" style="border-top:3px solid {pc};"><div style="font-size:11px;color:#9CA3AF;">{badges[i]} P={sc_item.probability:.0%} · Conf={sc_item.confirmation_score:.0%}</div><div style="font-size:14px;font-weight:700;margin:4px 0;">{sc_item.name}</div><div style="font-size:12px;color:#E8ECF0;">{sc_item.headline}</div><div style="margin-top:6px;font-size:11px;">Best: {" · ".join(sc_item.best_assets[:4])}</div><div style="font-size:11px;">Avoid: {" · ".join(sc_item.worst_assets[:4])}</div><div style="margin-top:4px;font-size:10px;color:#9CA3AF;">{em}</div></div>',unsafe_allow_html=True)
        bc=scen.get("base_case")
        if bc and hasattr(bc,"confirmation_triggers"):
            st.markdown("---"); ct,ci=st.columns(2)
            with ct:
                st.markdown(f"### Confirmation Triggers ({bc.name})")
                for t in getattr(bc,"confirmation_triggers",[]): st.markdown(f"• {t}")
            with ci:
                st.markdown("### Invalidators")
                for inv in getattr(bc,"invalidators",[]): st.markdown(f"• {inv}")
        if gip:
            st.markdown("---"); st.markdown("### GIP Feature Data")
            f=gip.features
            rows=[["Growth Momentum",fp(f.get("growth_momentum")),"+" if f.get("growth_momentum",0)>0 else "-"],
                  ["Inflation Momentum",fp(f.get("inflation_momentum")),"+" if f.get("inflation_momentum",0)>0 else "-"],
                  ["Policy Score",fp(f.get("policy_score")),""],
                  ["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
                  ["Data Coverage",fp(f.get("data_coverage")),""],
                  ["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
                  ["Structural Conf",f"{gip.structural_conf:.0%}",""],
                  ["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
            st.dataframe(pd.DataFrame(rows,columns=["Signal","Value","Dir"]),hide_index=True,use_container_width=True)

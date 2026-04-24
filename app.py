"""app.py — MacroRegime Pro v13 | Hedgeye GIP Framework

Features:
- Per-market tab: Regime Playbook (top EV+) + Bottleneck Long/Short
- Bottleneck badge on known plays
- IHSG: EM Rotation Phase + Recovery Timeline
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(page_title="MacroRegime Pro",page_icon="📊",layout="wide",initial_sidebar_state="expanded")

st.markdown("""<style>
.stApp{background:#0B0F19;color:#E8ECF0}
.stSidebar{background:#111827}
.stDataFrame{border-radius:8px}
.css-1cpxqw2{background:#1F2B3D}
</style>""", unsafe_allow_html=True)

QC={"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN={"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
SC={"bullish":"#10B981","bearish":"#EF4444","neutral":"#6B7280","mixed":"#F59E0B"}
def qcls(q): return q.lower() if q in QN else ""
def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def fp(v): return f"{v:.1%}" if v is not None and math.isfinite(float(v)) else "—"
def ff(v,d=3): return f"{v:.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
def qcard(label,q,conf,note=""):
    return f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center">
<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px">{label}</div>
<div style="font-size:32px;font-weight:700;color:{qc(q)};margin:4px 0">{q[-1] if q in QN else "?"}</div>
<div style="font-size:14px;color:#E8ECF0;font-weight:500">{qn(q)}</div>
{"<div style=\"font-size:11px;color:#9CA3AF;margin-top:6px\">" + note + "</div>" if note else ""}
<div style="margin-top:10px;height:4px;background:#111827;border-radius:2px"><div style="width:{conf*100:.0f}%;height:100%;background:{qc(q)};border-radius:2px"></div></div>
<div style="font-size:10px;color:#9CA3AF;margin-top:4px">Conf: {conf:.0%}</div>
</div>"""

def prob_bar(probs, title=""):
    fig=go.Figure()
    for q,p in sorted(probs.items()):
        fig.add_bar(x=[q],y=[p],marker_color=QC.get(q,"#9CA3AF"),text=[f"{p:.0%}"],textposition="outside")
    fig.update_layout(showlegend=False,height=200,margin=dict(t=25,b=5,l=0,r=0),
        paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0",family="JetBrains Mono"),
        title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
        yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),
        xaxis=dict(showgrid=False),bargap=0.35)
    return fig

def price_chart(prices_dict, tickers, title="", days=252):
    fig=go.Figure()
    colors=["#00D4AA","#F59E0B","#EF4444","#6366F1","#10B981","#60A5FA","#F472B6","#A78BFA"]
    for i,t in enumerate(tickers):
        s = prices_dict.get(t)
        if s is None: continue
        s = pd.to_numeric(s,errors="coerce").dropna().tail(days)
        if s.empty: continue
        norm = s/float(s.iloc[0])*100
        fig.add_scatter(x=norm.index, y=norm.values, name=t,
            line=dict(color=colors[i%len(colors)],width=1.5))
    fig.update_layout(height=280,margin=dict(t=30,b=20,l=0,r=0),
        paper_bgcolor="#111827",plot_bgcolor="#111827",
        font=dict(color="#E8ECF0"),title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
        xaxis=dict(showgrid=False),yaxis=dict(showgrid=True,gridcolor="#1F2B3D"),
        legend=dict(bgcolor="rgba(0,0,0,0)"))
    return fig

# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt_tp(tp):
    if not tp: return "—"
    t1=tp.get("t1"); t2=tp.get("t2"); rr=tp.get("rr_ratio")
    return f"T1:{ff(t1,2)} T2:{ff(t2,2)} R:R={ff(rr,1)}"

def _ev_color(v):
    try:
        vv=float(v.replace("+","").replace("—","0"))
        return f"color:{'#10B981' if vv>0.3 else '#F59E0B' if vv>0 else '#EF4444'}"
    except: return "color:#6B7280"

def _ev_color_neg(v):
    try:
        vv=float(v.replace("+","").replace("—","0"))
        return f"color:{'#EF4444' if vv<0 else '#F59E0B' if vv<0.3 else '#10B981'}"
    except: return "color:#6B7280"

# ── Session state ─────────────────────────────────────────────────────────────
if "snap" not in st.session_state: st.session_state.snap=None
if "loading" not in st.session_state: st.session_state.loading=False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v13*")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard","📈 GIP Regime","🎯 Risk Ranges",
        "🌍 Global Quad","📊 US Stocks",
        "💱 Forex","🛢 Commodities","₿ Crypto",
        "🇮🇩 IHSG","🔍 Bottleneck","📖 Narratives","🔮 Scenarios",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh",use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Force",use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Universe"):
        inc_us = st.checkbox("US Stocks",True)
        inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True)
        inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True)
    st.divider()
    st.caption("Current Hedgeye: Q3 Structural · Q2 Monthly · Q3 Global")

# ── Load/build snapshot ───────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap=snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb=st.progress(0.0); pt=st.empty()
    def prog(m,f): pb.progress(f); pt.caption(m)
    snap=build_snapshot(progress_cb=prog,include_us_stocks=inc_us,include_forex=inc_fx,
        include_commodities=inc_comm,include_crypto=inc_cryp,include_ihsg=inc_ihsg)
    st.session_state.snap=snap; st.session_state.loading=False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ No snapshot. Click **🔄 Refresh**."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
gip = snap.get("gip")
global_ = snap.get("global",{})
rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{})
narr = snap.get("narratives",{})
btk = snap.get("bottleneck",{})
pb_data = snap.get("playbook",{})
prices = snap.get("prices",{})
stress = snap.get("stress",{})

sq=gip.structural_quad if gip else "Q3"
mq=gip.monthly_quad if gip else "Q2"
gq=global_.get("global_quad","Q3")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page=="🏠 Dashboard":
    st.markdown(f"<div style=\"text-align:right;font-size:11px;color:#9CA3AF\">Built {snap.get('build_time_s',0)}s · Prices: {snap.get('prices_loaded',0)} · FRED: {snap.get('fred_coverage',0)} · RR: {snap.get('price_frames_count',0)}</div>",unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro — Dashboard")

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL (Climate)",sq,gip.structural_conf if gip else 0,"Quarterly"),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY (Weather)",mq,gip.monthly_conf if gip else 0,"3-6 Week Overlay"),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL",gq,global_.get("global_conf",0),"50 Countries"),unsafe_allow_html=True)
    with c4:
        if gip:
            dc=qc(sq); flip=gip.flip_hazard
            st.markdown(f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center">
<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px">ALIGNMENT</div>
<div style="font-size:20px;font-weight:700;color:{dc};margin:4px 0">{gip.divergence.upper()}</div>
<div style="font-size:12px;color:#E8ECF0">{gip.operating_regime}</div>
<div style="font-size:11px;color:#9CA3AF;margin-top:8px">Flip Risk: {flip:.0%}</div>
</div>""",unsafe_allow_html=True)

    # ── Compact Quad Transition Probabilities (3-panel: Structural / Monthly / Global)
    if gip:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("### 📊 Quad Transition Probabilities")
        
        def _compact_transition_chart(probs: dict, current_q: str, label: str):
            """Compact bar + scenario labels."""
            fig = go.Figure()
            for q,p in sorted(probs.items()):
                is_current = (q == current_q)
                fig.add_bar(x=[q], y=[p], marker_color=QC.get(q,"#9CA3AF"),
                    marker_line=dict(width=2 if is_current else 0, color="white"),
                    text=[f"{p:.0%}"], textposition="outside",
                    name=q)
            # Scenario annotations at bottom
            scenarios_sorted = sorted(probs.items(), key=lambda x: x[1], reverse=True)
            base = scenarios_sorted[0] if scenarios_sorted else ("Q3",0)
            alt  = scenarios_sorted[1] if len(scenarios_sorted)>1 else ("Q4",0)
            
            fig.update_layout(
                showlegend=False, height=170,
                margin=dict(t=30,b=30,l=0,r=0),
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                font=dict(color="#E8ECF0", family="JetBrains Mono", size=10),
                title=dict(text=f"From {current_q} → Next Quad | {label}", font=dict(size=10,color="#9CA3AF")),
                yaxis=dict(range=[0,1.15], tickformat=".0%", showgrid=True, gridcolor="#1F2B3D", tickfont=dict(size=9)),
                xaxis=dict(showgrid=False, tickfont=dict(size=10)),
                bargap=0.3,
            )
            # Bottom annotation: BASE → ALT
            base_txt = f"🎯BASE {base[0]}={base[1]:.0%}"
            alt_txt  = f" | 🔄ALT {alt[0]}={alt[1]:.0%}"
            if len(scenarios_sorted)>2:
                risk = scenarios_sorted[2]
                alt_txt += f" | ⚠️{risk[0]}={risk[1]:.0%}"
            fig.add_annotation(x=0.5, y=-0.28, xref="paper", yref="paper",
                text=base_txt+alt_txt, showarrow=False,
                font=dict(size=9, color="#9CA3AF"), align="center")
            return fig

        tp1,tp2,tp3 = st.columns(3)
        with tp1:
            st.plotly_chart(_compact_transition_chart(gip.structural_probs, sq, "Structural"), use_container_width=True, config={"displayModeBar":False})
        with tp2:
            st.plotly_chart(_compact_transition_chart(gip.monthly_probs, mq, "Monthly"), use_container_width=True, config={"displayModeBar":False})
        with tp3:
            # Global quad transition from global_
            gprobs = global_.get("global_probs",{})
            if gprobs:
                st.plotly_chart(_compact_transition_chart(gprobs, gq, "Global"), use_container_width=True, config={"displayModeBar":False})
        
        # Scenario list compact
        scenarios_list = scen.get("scenarios",[])
        if scenarios_list:
            badges = ["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]
            scen_cols = st.columns(len(scenarios_list[:4]))
            for i, (sc_item, col) in enumerate(zip(scenarios_list[:4], scen_cols)):
                pc = "#10B981" if sc_item.probability>0.40 else "#F59E0B" if sc_item.probability>0.25 else "#6B7280"
                with col:
                    st.markdown(f"""<div style="background:#1A2235;border-radius:8px;padding:10px;border-left:3px solid {pc}">
<div style="font-size:10px;color:#9CA3AF">{badges[i]}</div>
<div style="font-family:monospace;font-weight:700;color:{pc};font-size:12px">{sc_item.name}</div>
<div style="font-size:10px;color:#9CA3AF;margin-top:4px">P={sc_item.probability:.0%} | Conf={sc_item.confirmation_score:.0%}</div>
<div style="font-size:10px;color:#E8ECF0;margin-top:4px">{sc_item.headline[:60]}...</div>
<div style="font-size:10px;color:#9CA3AF;margin-top:2px">EM: {sc_item.em_note[:55]}...</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    c_pb,c_sig=st.columns([1.3,1])
    with c_pb:
        st.markdown("### 🎯 Regime Playbook")
        if pb_data:
            st.markdown(f"**✅ LONG**: {' · '.join(pb_data.get('best_assets',[])[:5])}")
            st.markdown(f"**❌ AVOID**: {' · '.join(pb_data.get('worst_assets',[])[:5])}")
            st.markdown(f"📊 Style: {pb_data.get('style','')}")
            st.markdown(f"💱 FX: {pb_data.get('fx','')}")
            st.markdown(f"🏦 Bonds: {pb_data.get('bonds','')}")
            if pb_data.get("monthly_adds"):
                st.markdown(f"⚡ Monthly adds: {' · '.join(pb_data['monthly_adds'])}")
    with c_sig:
        st.markdown("### 📡 GIP Signals")
        if gip:
            f=gip.features
            rows=[["Growth Level", f.get("growth_level",0), True],
                  ["Growth Momentum",f.get("growth_momentum",0), True],
                  ["Inflation Level",f.get("inflation_level",0), False],
                  ["Inflation Mom",f.get("inflation_momentum",0), False],
                  ["Policy (+=ease)",f.get("policy_score",0), True]]
            for label,val,pg in rows:
                if math.isfinite(val):
                    ic=("🟢" if (val>0.05 and pg) or (val<-0.05 and not pg) else "🔴" if (val<-0.05 and pg) or (val>0.05 and not pg) else "🟡")
                    bar="█"*int(abs(val)*10)+"░"*(10-int(abs(val)*10))
                    col=("#10B981" if (val>0 and pg) or (val<0 and not pg) else "#EF4444")
                    st.markdown(f'{ic} **{label}**: `{val:+.3f}` {bar}',unsafe_allow_html=True)
            cov=f.get("data_coverage",0); prx=f.get("proxy_share",0)
            st.progress(cov,text=f"FRED coverage: {cov:.0%}")
            if prx>0.5: st.warning(f"⚠️ {prx:.0%} proxy signals — add FRED_API_KEY for accuracy")

    ar=rr.get("asset_ranges",{})
    crits=[(s,a) for s,v in ar.items() for a in v.get("alerts",[]) if a.get("priority")=="CRITICAL"][:5]
    if crits:
        st.markdown("---\n### 🚨 Critical Alerts")
        for sym,a in crits:
            st.markdown(f'<div style="background:#2D1B1B;border-left:3px solid #EF4444;padding:8px 12px;margin:4px 0;border-radius:4px">⚠️ **[{sym}]** {a["action"]} | {a.get("note","")}</div>',unsafe_allow_html=True)

    l1=btk.get("level_1",[]); l2=btk.get("level_2",[])
    top=l1[:2]+l2[:2]
    if top:
        st.markdown("---\n### 🔍 Top Bottleneck Setups")
        cols=st.columns(min(len(top),4))
        for i,c in enumerate(top[:4]):
            with cols[i]:
                tc="#10B981" if c["trend"]=="uptrend" else "#EF4444" if c["trend"]=="downtrend" else "#F59E0B"
                badge="⚡L1" if c["level"]=="level_1" else "📈L2"
                st.markdown(f"""<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center">
<div style="font-size:10px;color:#9CA3AF">{badge} {c['ticker']}</div>
<div style="font-size:13px;color:#E8ECF0;font-weight:500">{c['sector'].replace('_',' ').title()}</div>
<div style="font-size:16px;font-weight:700;color:{tc};margin:4px 0">{c['trend'].upper()}</div>
<div style="font-size:11px;color:#9CA3AF">Score: {c['score']:.2f} | EV: {c.get('ev',0):.2f}</div>
{"<div style=\"font-size:10px;color:#EF4444;margin-top:4px\">⚠️ REGIME TRAP</div>" if c.get("regime_trap") else ""}
</div>""",unsafe_allow_html=True)

    em_sig = btk.get("em_recovery", {})
    if em_sig:
        st.markdown("---\n### 🌍 EM Recovery Signal")
        conf = em_sig.get("confidence", 0)
        ec = "#10B981" if conf > 0.6 else "#F59E0B" if conf > 0.4 else "#6B7280"
        st.markdown(f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px">
<div style="font-size:14px;font-weight:700;color:{ec}">{em_sig.get('trigger','')}</div>
<div style="font-size:12px;color:#E8ECF0;margin:4px 0">{em_sig.get('rationale','')}</div>
<div style="font-size:11px;color:#9CA3AF">Confidence: {conf:.0%}</div>
<div style="margin-top:8px;font-size:12px">🎯 Best: {', '.join(em_sig.get('best',[])[:6])}</div>
</div>""",unsafe_allow_html=True)

    bc=scen.get("base_case")
    if bc:
        st.markdown("---\n### 🔮 Base Scenario")
        pc="#10B981" if bc.probability>0.40 else "#F59E0B"
        st.markdown(f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px">
<div style="font-size:14px;font-weight:700;color:{pc}">{bc.name}</div>
<div style="font-size:12px;color:#E8ECF0;margin:4px 0">{bc.headline}</div>
<div style="font-size:11px;color:#9CA3AF">Probability: {bc.probability:.0%}</div>
<div style="margin-top:8px;font-size:12px">✅ LONG: {", ".join(bc.best_assets[:4])}  | 
❌ AVOID: {", ".join(bc.worst_assets[:3])}</div>
<div style="font-size:11px;color:#9CA3AF;margin-top:6px">Catalyst: {bc.catalyst}</div>
</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GIP REGIME
# ══════════════════════════════════════════════════════════════════════════════
elif page=="📈 GIP Regime":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY RoC second derivative. 'Heating up or cooling down?'")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    g=gip.structural_g; i=gip.structural_i
    fig=go.Figure()
    for q,(x0,y0,x1,y1) in {"Q1":(-0.1,-1,1,0),"Q2":(-0.1,0,1,1),"Q3":(-1,0,-0.1,1),"Q4":(-1,-1,-0.1,0)}.items():
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,fillcolor=QC[q],opacity=0.08,line_width=0)
        fig.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2,text=f"<b>{q}</b><br>{qn(q)}",
            font=dict(size=11,color=QC[q]),showarrow=False)
    fig.add_hline(y=0,line_width=1,line_color="#333")
    fig.add_vline(x=0,line_width=1,line_color="#333")
    fig.add_scatter(x=[g],y=[i],mode="markers+text",
        marker=dict(size=18,color=qc(sq),symbol="circle",line=dict(width=2,color="white")),
        text=["CURRENT"],textposition="top center",textfont=dict(size=9,color="white"))
    fig.update_layout(xaxis_title="Growth Signal",yaxis_title="Inflation Signal",
        xaxis=dict(range=[-1,1],showgrid=True,gridcolor="#1F2B3D",zeroline=False),
        yaxis=dict(range=[-1,1],showgrid=True,gridcolor="#1F2B3D",zeroline=False),
        paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0"),
        height=360,margin=dict(t=20,b=40,l=40,r=20),showlegend=False)

    c1,c2=st.columns([1.3,1])
    with c1: st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with c2:
        st.markdown("#### Feature Breakdown")
        f=gip.features
        feat_rows=[]
        for k in ["growth_level","growth_momentum","inflation_level","inflation_momentum","policy_score","data_coverage","proxy_share"]:
            v=f.get(k,float("nan"))
            if math.isfinite(v):
                feat_rows.append({"Signal":k.replace("_"," ").title(),"Score":f"{v:+.4f}"})
        if feat_rows: st.dataframe(pd.DataFrame(feat_rows),hide_index=True,height=220)
        cov=f.get("data_coverage",0); prx=f.get("proxy_share",0)
        st.progress(cov,text=f"FRED Coverage: {cov:.0%}")
        if prx>0.5: st.warning(f"⚠️ {prx:.0%} proxy. Set FRED_API_KEY in secrets.toml for full accuracy.")
        else: st.success(f"✅ {1-prx:.0%} from FRED macro data")

    st.markdown("---")
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(prob_bar(gip.structural_probs,"Structural (Quarterly)"),use_container_width=True,config={"displayModeBar":False})
    with c2: st.plotly_chart(prob_bar(gip.monthly_probs,"Monthly (Weather Overlay)"),use_container_width=True,config={"displayModeBar":False})

    st.markdown("#### Raw FRED Data")
    raw_rows=[{"Series":k[4:].upper(),"Value":f"{v:.4f}"} for k,v in sorted(f.items()) if k.startswith("raw_") and math.isfinite(v)]
    if raw_rows: st.dataframe(pd.DataFrame(raw_rows),hide_index=True,height=250)
    else: st.info("No FRED data loaded — running on market price proxies. Add FRED_API_KEY to secrets.toml.")

# ══════════════════════════════════════════════════════════════════════════════
# RISK RANGES
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🎯 Risk Ranges":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("Hurst Rescaled Range Analysis. LRR=buy. TRR=trim. TREND break=exit.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()
    sm=rr.get("summary",{})
    s1,s2,s3,s4=st.columns(4)
    for col,lab,val,c in [(s1,"Total",sm.get("total",0),"#E8ECF0"),(s2,"Bullish",sm.get("bullish",0),"#10B981"),
                          (s3,"Bearish",sm.get("bearish",0),"#EF4444"),(s4,"A-Quality",sm.get("a_quality",0),"#00D4AA")]:
        col.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:700;color:{c}">{val}</div><div style="font-size:11px;color:#9CA3AF">{lab}</div></div>',unsafe_allow_html=True)

    c1,c2,c3=st.columns(3)
    with c1: sf=st.selectbox("Signal",["All","bullish","bearish","neutral","mixed"])
    with c2: qf=st.multiselect("Quality",["A","B","C","short_A","short_B","none"],default=["A","B","short_A","short_B"])
    with c3: ca=st.checkbox("Critical only",False)

    rows=[]
    for sym,v in sorted(ar.items()):
        comp=v.get("composite","neutral"); qual=v.get("quality","none")
        if sf!="All" and comp!=sf: continue
        if qf and qual not in qf: continue
        alerts=v.get("alerts",[])
        if ca and not any(a["priority"]=="CRITICAL" for a in alerts): continue
        rows.append({"Ticker":sym,"Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—"),
            "Tail":v.get("tail_signal","—"),"Composite":comp,"Quality":qual,
            "Trade LRR":ff(v.get("trade_lrr"),2),"Trade TRR":ff(v.get("trade_trr"),2),
            "Trend LRR":ff(v.get("trend_lrr"),2),"Trend TRR":ff(v.get("trend_trr"),2),
            "H(Trade)":f"{v.get('hurst_trade',0.5):.2f}","H(Trend)":f"{v.get('hurst_trend',0.5):.2f}",
            "VolCnf":f"{v.get('volume_confirm',0.5):.0%}","Stretch":v.get("trade_stretch","—"),
            "Alerts":len(alerts)})
    if rows:
        df=pd.DataFrame(rows)
        def sc(v): return "color:#10B981" if v=="bullish" else "color:#EF4444" if v=="bearish" else "color:#F59E0B" if v=="mixed" else "color:#6B7280"
        st.dataframe(df.style.map(sc,subset=["Trade","Trend","Tail","Composite"]),hide_index=True,height=420,use_container_width=True)
    else: st.info("No assets match filter.")

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("---\n### 🔔 Alerts")
        for sym,a in all_a[:20]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
            st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {"#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B" if a["priority"]=="HIGH" else "#60A5FA"};padding:8px 12px;margin:4px 0;border-radius:4px">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50+ Countries")
    st.caption("Hedgeye GIP for top 50 economies. Market-cap weighted.")
    if not global_: st.warning("No global data. Refresh."); st.stop()

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(qcard("GLOBAL QUAD",gq,global_.get("global_conf",0)),unsafe_allow_html=True)
    with c2:
        ub=global_.get("usd_bias","—"); uc="#EF4444" if ub=="bullish" else "#10B981"
        st.markdown(f'<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase">USD BIAS</div><div style="font-size:24px;font-weight:700;color:{uc};margin:4px 0">{ub.upper()}</div><div style="font-size:11px;color:#9CA3AF">{global_.get("usd_rationale","")[:55]}</div></div>',unsafe_allow_html=True)
    with c3:
        sy=global_.get("synchronized",False)
        st.markdown(f'<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase">SYNCHRONIZATION</div><div style="font-size:24px;font-weight:700;color:{"#10B981" if sy else "#F59E0B"};margin:4px 0">{"SYNC" if sy else "DIVERGENT"}</div></div>',unsafe_allow_html=True)
    with c4:
        emh=global_.get("em_headwind",False)
        st.markdown(f'<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center"><div style="font-size:11px;color:#9CA3AF;text-transform:uppercase">EM HEADWIND</div><div style="font-size:24px;font-weight:700;color:{"#EF4444" if emh else "#10B981"};margin:4px 0">{"YES" if emh else "NO"}</div><div style="font-size:11px;color:#9CA3AF">{global_.get("em_in_q3",0)} EM in Q3</div></div>',unsafe_allow_html=True)

    em_sig = btk.get("em_recovery", {})
    if em_sig:
        st.markdown("---")
        conf = em_sig.get("confidence", 0)
        ec = "#10B981" if conf > 0.6 else "#F59E0B" if conf > 0.4 else "#6B7280"
        st.markdown(f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px;margin-bottom:16px">
<div style="font-size:13px;font-weight:700;color:{ec}">🌍 EM RECOVERY SIGNAL — {em_sig.get('trigger','')}</div>
<div style="font-size:12px;color:#E8ECF0;margin:6px 0">{em_sig.get('rationale','')}</div>
<div style="font-size:11px;color:#9CA3AF">Confidence: {conf:.0%} | Best: {', '.join(em_sig.get('best',[])[:6])}</div>
</div>""",unsafe_allow_html=True)

    countries=global_.get("countries",{})
    if countries:
        rf=st.multiselect("Region",sorted({d["region"] for d in countries.values()}),default=sorted({d["region"] for d in countries.values()}))
        qfl=st.multiselect("Quad",["Q1","Q2","Q3","Q4"],default=["Q1","Q2","Q3","Q4"])
        rows=[]
        for country,d in sorted(countries.items()):
            if d["region"] not in rf or d["quad"] not in qfl: continue
            rows.append({"Country":country.replace("_"," "),"ETF":d["etf"],"Region":d["region"],
                "Quad":d["quad"],"Name":qn(d["quad"]),"Conf":f"{d['confidence']:.0%}",
                "1M":fp(d.get("etf_1m")),"3M":fp(d.get("etf_3m")),"6M":fp(d.get("etf_6m")),
                "CommodSens":f"{d['commodity_sensitivity']:.0%}","USDSens":f"{d['usd_sensitivity']:.0%}",
                "Note":d.get("rationale","")[:40]})
        if rows:
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),
                hide_index=True,height=480,use_container_width=True)

        qdist=global_.get("quad_distribution",{})
        if qdist:
            c1,c2=st.columns(2)
            with c1:
                fig=go.Figure(go.Pie(labels=list(qdist.keys()),values=list(qdist.values()),
                    marker_colors=[QC.get(q,"#9CA3AF") for q in qdist],hole=0.5,textinfo="label+percent"))
                fig.update_layout(title="Country Distribution",paper_bgcolor="#111827",font=dict(color="#E8ECF0"),height=260,margin=dict(t=30,b=0,l=0,r=0),showlegend=False)
                st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            with c2:
                st.markdown("#### Dominant Quad by Region")
                for r,q in sorted(global_.get("region_quads",{}).items()):
                    c=QC.get(q,"#9CA3AF")
                    st.markdown(f'<div style="background:#1F2B3D;border-radius:8px;padding:10px;margin:4px 0;display:flex;justify-content:space-between"><span style="color:#9CA3AF;font-size:12px">{r.upper()}</span><span style="color:{c};font-weight:700">{q} {qn(q)}</span></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# US STOCKS
# ══════════════════════════════════════════════════════════════════════════════
elif page=="📊 US Stocks":
    st.markdown("# 📊 US Equities — Sectors · Factors · Signal · Bottleneck")
    from config.settings import US_SECTORS, US_FACTORS, QUAD_ASSET_PERFORMANCE
    ar=rr.get("asset_ranges",{})

    # ── Regime Playbook for US Equities ────────────────────────────────────
    st.markdown("### 🎯 Regime Playbook — Q{} Best Plays".format(sq[-1]))
    pb=QUAD_ASSET_PERFORMANCE.get(sq,{})
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"**✅ Overweight Sectors**: {', '.join(pb.get('sectors_overweight',[]))}")
        st.markdown(f"**📈 Best Assets**: {', '.join(pb.get('best',[])[:6])}")
        st.markdown(f"**📊 Style**: {pb.get('style','')}")
    with c2:
        st.markdown(f"**❌ Underweight Sectors**: {', '.join(pb.get('sectors_underweight',[]))}")
        st.markdown(f"**📉 Worst Assets**: {', '.join(pb.get('worst',[])[:5])}")
        st.markdown(f"**🏦 Bonds**: {pb.get('bonds','')}")

    # Top EV+ from playbook assets
    usl=btk.get("us_long",[])
    playbook_tickers = pb.get("best",[]) + pb.get("sectors_overweight",[])
    playbook_tickers = [t.split(" (")[0].strip() for t in playbook_tickers]  # extract ticker from "XLK (Tech)"
    # Also extract from sector names
    sector_map = {"XLK":"XLK","XLY":"XLY","XLI":"XLI","XLF":"XLF","XLE":"XLE","XLB":"XLB","XLV":"XLV","XLP":"XLP","XLU":"XLU","XLRE":"XLRE","XLC":"XLC"}
    playbook_tickers = list(dict.fromkeys([sector_map.get(t,t) for t in playbook_tickers if t]))

    # Filter us_long yang masuk playbook
    playbook_long = [c for c in usl if c["ticker"] in playbook_tickers or any(c["ticker"]==t for t in playbook_tickers)]
    if not playbook_long and usl:
        playbook_long = usl[:5]  # fallback to top 5 EV+

    if playbook_long:
        st.markdown("#### 🔥 Top Regime-Aligned Long Plays (by EV)")
        rows=[]
        for c in playbook_long[:10]:
            badge = "⚡ BOTTLENECK" if c.get("known") else ""
            tp=c.get("tp",{})
            rows.append({"Ticker":c["ticker"] + (f" {badge}" if badge else ""),"Sector":c["sector"].replace("_"," ").title(),
                "EV":f"{c['ev']:+.3f}","Score":c["score"],"Trend":c["trend"].title(),
                "Accum":fp(c["acc"]),"RS 3M":fp(c.get("rs_3m")),"TP":_fmt_tp(tp)})
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=250)
    else:
        st.info(f"No strong regime-aligned long plays in {sq}. Defensive positioning recommended.")

    # ── Sector Chart + Risk Range ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Sector Performance vs SPY (Normalized 1yr)")
    st.plotly_chart(price_chart(prices,list(US_SECTORS.keys())[:6],"Sectors (rebased=100)",252),use_container_width=True,config={"displayModeBar":False})

    st.markdown("#### Sector Risk Range Signals")
    rows=[]
    for t,name in {**US_SECTORS,**US_FACTORS}.items():
        v=ar.get(t,{})
        s=prices.get(t)
        r1m=fp(float(pd.to_numeric(s,errors="coerce").dropna().pct_change(21).dropna().iloc[-1]) if s is not None and len(pd.to_numeric(s,errors="coerce").dropna())>22 else None)
        rows.append({"Ticker":t,"Name":name,"Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—"),
            "Composite":v.get("composite","—"),"Quality":v.get("quality","—"),
            "Trade LRR":ff(v.get("trade_lrr"),2),"Trade TRR":ff(v.get("trade_trr"),2),"1M Ret":r1m})
    if rows:
        df=pd.DataFrame(rows)
        def _us_color(v):
            return f"color:{QC.get(v) if v in QC else SC.get(v,'#6B7280')}"
        st.dataframe(df.style.map(_us_color,subset=["Trade","Trend","Composite"]),hide_index=True,use_container_width=True,height=300)

    # ── Bottleneck Long / Short / Avoid ────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Bottleneck Scanner — All US Stocks")
    st.caption(f"Structural {sq} = {'SHORT bias' if sq in ('Q3','Q4') else 'LONG bias'}. Sorted by Expected Value (EV). ⚡ = Known bottleneck play.")

    uss=btk.get("us_short",[]); usa=btk.get("us_avoid",[])
    t1,t2,t3=st.tabs([f"🟢 LONG ({len(usl)})",f"🔴 SHORT ({len(uss)})",f"⚪ AVOID ({len(usa)})"])

    with t1:
        if usl:
            rows=[]
            for c in usl[:30]:
                badge = "⚡ BOTTLENECK" if c.get("known") else ""
                tp=c.get("tp",{})
                rows.append({"Ticker":c["ticker"] + (f" {badge}" if badge else ""),"Sector":c["sector"].replace("_"," ").title(),
                    "EV":f"{c['ev']:+.3f}","Score":c["score"],"Constraint":fp(c["constraint"]),
                    "Regime":fp(c["regime_fit"]),"Trend":c["trend"].title(),"Accum":fp(c["acc"]),
                    "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],
                    "TP":_fmt_tp(tp),"Thesis":c.get("known_thesis","")[:55]})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=400)
        else: st.info(f"No US long candidates in {sq}. Q3/Q4 = defensive only (GLD, XLV, XLP, XLU).")

    with t2:
        if uss:
            rows=[]
            for c in uss[:30]:
                badge = "⚡ BOTTLENECK" if c.get("known") else ""
                tp=c.get("tp",{})
                rows.append({"Ticker":c["ticker"] + (f" {badge}" if badge else ""),"Sector":c["sector"].replace("_"," ").title(),
                    "EV":f"{c['ev']:+.3f}","Score":c["score"],"Constraint":fp(c["constraint"]),
                    "Regime":fp(c["regime_fit"]),"Trend":c["trend"].title(),"Accum":fp(c["acc"]),
                    "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],
                    "TP":_fmt_tp(tp),"Thesis":c.get("known_thesis","")[:55]})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color_neg,subset=["EV"]),hide_index=True,use_container_width=True,height=400)
        else: st.info(f"No US short candidates in {sq}. Q1/Q2 typically generate shorts.")

    with t3:
        if usa:
            rows=[{"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),
                "EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),"Reason":f"{c['direction'].replace('_',' ').title()} in {sq}"} for c in usa[:20]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=250)
        else: st.info("No avoid candidates.")

# ══════════════════════════════════════════════════════════════════════════════
# FOREX
# ══════════════════════════════════════════════════════════════════════════════
elif page=="💱 Forex":
    st.markdown("# 💱 Forex — Major · EM · Commodity FX · Bottleneck")
    from config.settings import FOREX_PAIRS, QUAD_ASSET_PERFORMANCE
    ar=rr.get("asset_ranges",{})

    # ── Regime Playbook for FX ─────────────────────────────────────────────
    st.markdown("### 🎯 Regime Playbook — Q{} FX Bias".format(sq[-1]))
    pb=QUAD_ASSET_PERFORMANCE.get(sq,{})
    st.markdown(f"**💱 FX Direction**: {pb.get('fx','')}")
    st.markdown(f"**USD Bias**: {'Bearish' if global_.get('usd_bias')=='bearish' else 'Bullish'}")

    # FX playbook assets
    fx_long=btk.get("forex_long",[]); fx_short=btk.get("forex_short",[])
    if sq in ("Q3","Q4"):
        st.info("⚠️ Q3/Q4 = USD bearish TREND (McCullough Apr 2026). Short USD vs commodity FX. EM FX mixed.")
    elif sq=="Q1":
        st.success("✅ Q1 = Goldilocks. USD moderate. EM FX with strong GDP benefit.")
    else:
        st.warning("⚡ Q2 = Reflation. Commodity FX outperform: AUD, CAD, NOK, MXN.")

    # Top EV+ FX plays
    if fx_long:
        st.markdown("#### 🔥 Top FX Long Plays (by EV)")
        rows=[{"Pair":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
            "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp"))} for c in fx_long[:10]]
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=200)

    # ── DXY + Pairs ────────────────────────────────────────────────────────
    st.markdown("---")
    ub=global_.get("usd_bias","—"); uc="#EF4444" if ub=="bullish" else "#10B981"
    st.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;margin-bottom:12px"><div style="font-size:11px;color:#9CA3AF">USD BIAS (Global Quad Context)</div><div style="font-size:20px;font-weight:700;color:{uc}">{ub.upper()}</div><div style="font-size:11px;color:#9CA3AF">{global_.get("usd_rationale","")}</div></div>',unsafe_allow_html=True)

    st.plotly_chart(price_chart(prices,["DX-Y.NYB"],"DXY (USD Index)",252),use_container_width=True,config={"displayModeBar":False})

    majors=[k for k in ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X"] if k in prices]
    if majors:
        st.plotly_chart(price_chart(prices,majors,"Major Pairs (rebased=100)",126),use_container_width=True,config={"displayModeBar":False})

    rows=[]
    for t,name in FOREX_PAIRS.items():
        s=prices.get(t)
        if s is None: continue
        s=pd.to_numeric(s,errors="coerce").dropna()
        if s.empty: continue
        px=float(s.iloc[-1])
        r1m=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>22 else None
        r3m=float(s.iloc[-1]/s.iloc[-63]-1) if len(s)>63 else None
        v=ar.get(t,{})
        rows.append({"Pair":name,"Ticker":t,"Price":ff(px,5),"1M Ret":fp(r1m),"3M Ret":fp(r3m),
            "Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—"),
            "Stretch":v.get("trade_stretch","—"),"TRR":ff(v.get("trade_trr"),5),"LRR":ff(v.get("trade_lrr"),5)})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(lambda v:f"color:{SC.get(v,'#6B7280')}",subset=["Trade","Trend"]),hide_index=True,use_container_width=True,height=350)

    # ── FX Bottleneck Long / Short ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 FX Bottleneck Scanner")
    st.caption(f"Structural {sq} = {'SHORT USD' if sq in ('Q3','Q4') else 'LONG USD' if sq=='Q4' else 'MIXED'}. Sorted by EV.")

    t1,t2=st.tabs([f"🟢 LONG ({len(fx_long)})",f"🔴 SHORT ({len(fx_short)})"])

    with t1:
        if fx_long:
            rows=[{"Pair":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in fx_long[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No FX long setups in {sq}.")

    with t2:
        if fx_short:
            rows=[{"Pair":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in fx_short[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color_neg,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No FX short setups in {sq}.")

# ══════════════════════════════════════════════════════════════════════════════
# COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🛢 Commodities":
    st.markdown("# 🛢 Commodities — Energy · Metals · Agri · Bottleneck")
    from config.settings import COMMODITIES, QUAD_ASSET_PERFORMANCE
    ar=rr.get("asset_ranges",{})

    # ── Regime Playbook for Commodities ────────────────────────────────────
    st.markdown("### 🎯 Regime Playbook — Q{} Commodity Bias".format(sq[-1]))
    pb=QUAD_ASSET_PERFORMANCE.get(sq,{})
    if sq=="Q2" or mq=="Q2":
        st.success("✅ Q2 = commodity-bullish. Energy, metals, agri bid. Broad commodity exposure viable.")
    elif sq=="Q3":
        st.info("⚠️ Q3 = selective commodity. Gold/precious metals BEST. Energy mixed. Base metals headwind. Agri ok.")
    elif sq=="Q4":
        st.error("❌ Q4 = commodity bearish. Avoid energy, base metals. Only gold defensive.")
    else:
        st.warning("⚡ Q1 = commodity neutral. Selective exposure.")

    st.markdown(f"**📈 Best**: {', '.join(pb.get('best',[])[:5])}")
    st.markdown(f"**📉 Worst**: {', '.join(pb.get('worst',[])[:5])}")

    # Top EV+ commodity plays
    cl=btk.get("commodity_long",[]); cs=btk.get("commodity_short",[])
    if cl:
        st.markdown("#### 🔥 Top Commodity Long Plays (by EV)")
        rows=[{"Ticker":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
            "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp"))} for c in cl[:10]]
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=200)

    # ── Charts ─────────────────────────────────────────────────────────────
    st.markdown("---")
    groups={"Precious":["GC=F","SI=F","GLD","SLV"],"Energy":["CL=F","BZ=F","NG=F","USO"],
        "Base Metals":["HG=F","ALI=F"],"Agriculture":["ZW=F","ZC=F","ZS=F","DBA"]}
    tabs=st.tabs(list(groups.keys())+["All Signals"])

    for i,(grp,tickers) in enumerate(groups.items()):
        with tabs[i]:
            avail=[t for t in tickers if t in prices]
            if avail:
                st.plotly_chart(price_chart(prices,avail,f"{grp} (rebased=100)",252),use_container_width=True,config={"displayModeBar":False})

    with tabs[-1]:
        rows=[]
        for t,name in COMMODITIES.items():
            s=prices.get(t)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1])
            r1m=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>22 else None
            r3m=float(s.iloc[-1]/s.iloc[-63]-1) if len(s)>63 else None
            v=ar.get(t,{})
            rows.append({"Ticker":t,"Name":name,"Price":ff(px,3),"1M":fp(r1m),"3M":fp(r3m),
                "Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—"),
                "Stretch":v.get("trade_stretch","—"),"LRR":ff(v.get("trade_lrr"),2),"TRR":ff(v.get("trade_trr"),2)})
        if rows:
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(lambda v:f"color:{SC.get(v,'#6B7280')}",subset=["Trade","Trend"]),hide_index=True,use_container_width=True,height=400)

    # ── Commodity Bottleneck Long / Short ──────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Commodity Bottleneck Scanner")
    st.caption(f"Structural {sq} = {'LONG selective' if sq in ('Q2','Q3') else 'SHORT' if sq=='Q4' else 'MIXED'}. Sorted by EV.")

    t1,t2=st.tabs([f"🟢 LONG ({len(cl)})",f"🔴 SHORT ({len(cs)})"])

    with t1:
        if cl:
            rows=[{"Ticker":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in cl[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No commodity long setups in {sq}.")

    with t2:
        if cs:
            rows=[{"Ticker":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in cs[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color_neg,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No commodity short setups in {sq}.")

# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page=="₿ Crypto":
    st.markdown("# ₿ Crypto — Bitcoin · Altcoins · ETFs · Bottleneck")
    from config.settings import CRYPTO, QUAD_ASSET_PERFORMANCE
    ar=rr.get("asset_ranges",{})

    # ── Regime Playbook for Crypto ─────────────────────────────────────────
    st.markdown("### 🎯 Regime Playbook — Q{} Crypto Bias".format(sq[-1]))
    pb=QUAD_ASSET_PERFORMANCE.get(sq,{})
    if sq in ("Q3","Q4"):
        st.error(f"⚠️ **{sq} = CRYPTO HEADWIND.** Risk-off regime. Reduce exposure. Only BTC quality (IBIT, FBTC) might hold.")
    elif sq=="Q1":
        st.success("✅ Q1 = Goldilocks. Crypto risk-on. Broad alt exposure viable. BTC, ETH, SOL, altcoins.")
    else:
        st.warning("⚡ Q2 = Reflation. BTC/ETH ok as inflation hedge. Alts selective. Avoid high-beta alts.")

    st.markdown(f"**📈 Best**: {', '.join(pb.get('best',[])[:5])}")
    st.markdown(f"**📉 Worst**: {', '.join(pb.get('worst',[])[:5])}")

    # Top EV+ crypto plays
    crl=btk.get("crypto_long",[]); crs=btk.get("crypto_short",[])
    if crl:
        st.markdown("#### 🔥 Top Crypto Long Plays (by EV)")
        rows=[{"Token":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
            "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp"))} for c in crl[:10]]
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=200)
    else:
        st.info(f"No crypto long setups in {sq}. Q3/Q4 = crypto headwind.")

    # ── Charts ─────────────────────────────────────────────────────────────
    st.markdown("---")
    btc_eth=[t for t in ["BTC-USD","ETH-USD","IBIT","FBTC"] if t in prices]
    if btc_eth:
        st.plotly_chart(price_chart(prices,btc_eth,"BTC · ETH · ETFs (rebased=100)",90),use_container_width=True,config={"displayModeBar":False})

    alts=[t for t in ["SOL-USD","ADA-USD","AVAX-USD","LINK-USD","MATIC-USD","DOT-USD"] if t in prices]
    if alts:
        st.plotly_chart(price_chart(prices,alts,"Altcoins (rebased=100)",90),use_container_width=True,config={"displayModeBar":False})

    rows=[]
    for t,name in CRYPTO.items():
        s=prices.get(t)
        if s is None: continue
        s=pd.to_numeric(s,errors="coerce").dropna()
        if s.empty: continue
        px=float(s.iloc[-1])
        r7d=float(s.iloc[-1]/s.iloc[-8]-1) if len(s)>8 else None
        r30d=float(s.iloc[-1]/s.iloc[-31]-1) if len(s)>31 else None
        v=ar.get(t,{})
        rows.append({"Token":name,"Ticker":t,"Price":ff(px,2),"7D":fp(r7d),"30D":fp(r30d),
            "Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—"),
            "Stretch":v.get("trade_stretch","—"),"LRR":ff(v.get("trade_lrr"),2),"TRR":ff(v.get("trade_trr"),2)})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(lambda v:f"color:{SC.get(v,'#6B7280')}",subset=["Trade","Trend"]),hide_index=True,use_container_width=True,height=350)

    # ── Crypto Bottleneck Long / Short ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Crypto Bottleneck Scanner")
    st.caption(f"Structural {sq} = {'SHORT' if sq in ('Q3','Q4') else 'LONG' if sq=='Q1' else 'SELECTIVE'}. Sorted by EV.")

    t1,t2=st.tabs([f"🟢 LONG ({len(crl)})",f"🔴 SHORT ({len(crs)})"])

    with t1:
        if crl:
            rows=[{"Token":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in crl[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No crypto long setups in {sq}.")

    with t2:
        if crs:
            rows=[{"Token":c["ticker"],"EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],"TP":_fmt_tp(c.get("tp")),
                "Thesis":c.get("known_thesis","")[:55]} for c in crs[:20]]
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color_neg,subset=["EV"]),hide_index=True,use_container_width=True,height=300)
        else: st.info(f"No crypto short setups in {sq}.")

# ══════════════════════════════════════════════════════════════════════════════
# IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Context · EM Rotation · Bottleneck")
    from config.settings import IHSG_UNIVERSE, QUAD_ASSET_PERFORMANCE
    ar=rr.get("asset_ranges",{})
    indo=global_.get("countries",{}).get("Indonesia",{})

    # ── EM Rotation Phase ─────────────────────────────────────────────────
    st.markdown("### 🌍 EM Rotation Phase — Where is IHSG in the Cycle?")

    # Determine phase
    if sq in ("Q3","Q4") and mq in ("Q3","Q4"):
        phase = "EM HEADWIND"
        phase_color = "#EF4444"
        phase_desc = "Structural Q3/Q4 = EM under pressure. Commodity cycle peaked. IDR fragile. Foreign outflows likely."
        recovery_trigger = "Q3→Q2 transition (monthly Q2 inside structural Q3)"
        recovery_conf = btk.get("em_recovery",{}).get("confidence",0)
    elif sq in ("Q3","Q4") and mq in ("Q1","Q2"):
        phase = "EM EARLY RECOVERY"
        phase_color = "#F59E0B"
        phase_desc = "Monthly Q2 overlay = early EM recovery signal. Commodity bid + USD bearish TREND = EM FX relief. But structural still headwind."
        recovery_trigger = "Structural confirmation to Q2/Q1"
        recovery_conf = 0.55
    elif sq in ("Q1","Q2"):
        phase = "EM TAILWIND"
        phase_color = "#10B981"
        phase_desc = "Q1/Q2 = MAX EM recovery. Historical +25-40% in first 6M of Q1. Broad EM exposure viable."
        recovery_trigger = "Already in recovery phase"
        recovery_conf = 0.85
    else:
        phase = "EM MIXED"
        phase_color = "#6B7280"
        phase_desc = "Mixed signals. Monitor monthly quad for direction."
        recovery_trigger = "Wait for clear monthly signal"
        recovery_conf = 0.35

    st.markdown(f"""<div style="background:#1F2B3D;border-radius:12px;padding:16px;margin-bottom:16px">
<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px">CURRENT EM PHASE</div>
<div style="font-size:28px;font-weight:700;color:{phase_color};margin:4px 0">{phase}</div>
<div style="font-size:12px;color:#E8ECF0;margin:6px 0">{phase_desc}</div>
<div style="font-size:11px;color:#9CA3AF;margin-top:8px">Recovery Trigger: {recovery_trigger} | Confidence: {recovery_conf:.0%}</div>
</div>""",unsafe_allow_html=True)

    # Rotation timeline
    st.markdown("#### 📅 EM Rotation Timeline")
    timeline_data = [
        ("Q3/Q4 Structural", "🔴 HEADWIND", "EM commodity exporters peak. IDR fragile. Foreign outflows."),
        ("Monthly Q2 Overlay", "🟡 EARLY SIGNAL", "Commodity bid + USD bearish = EM FX relief. Selective entry."),
        ("Q2 Structural Confirm", "🟢 RECOVERY", "Broad EM recovery. Commodity EM leads: Brazil, Mexico, Indonesia, Australia."),
        ("Q1 Structural", "🟢 MAX RECOVERY", "Historical +25-40% in 6M. All EM viable. Tech EM + quality EM best."),
    ]
    for step, status, desc in timeline_data:
        st.markdown(f"**{step}**: {status} — {desc}")

    # Indonesia specific
    st.markdown("---")
    c1,c2,c3=st.columns(3)
    q=indo.get("quad","Q3") if indo else "Q3"
    with c1: st.markdown(qcard("INDONESIA QUAD",q,indo.get("confidence",0) if indo else 0),unsafe_allow_html=True)
    with c2:
        uh=indo.get("usd_headwind",0) if indo else 0
        st.markdown(f'<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center"><div style="font-size:11px;color:#9CA3AF">USD HEADWIND</div><div style="font-size:24px;font-weight:700;color:{"#EF4444" if uh>0.3 else "#10B981"}">{uh:.0%}</div><div style="font-size:11px;color:#9CA3AF">USD Sensitivity: {indo.get("usd_sensitivity",0.55):.0%}</div></div>',unsafe_allow_html=True)
    with c3:
        cs=indo.get("commodity_sensitivity",0.70) if indo else 0.70
        st.markdown(f'<div style="background:#1F2B3D;border-radius:12px;padding:16px;text-align:center"><div style="font-size:11px;color:#9CA3AF">COMMODITY SENSITIVITY</div><div style="font-size:24px;font-weight:700;color:#F59E0B">{cs:.0%}</div><div style="font-size:11px;color:#9CA3AF">Coal · Palm Oil · Nickel</div></div>',unsafe_allow_html=True)

    # IHSG context
    st.markdown("#### Indonesia in Hedgeye Context")
    st.markdown(f"""**Structural {sq}** = Indonesia headwinds:
- 🔴 Commodity cycle peaked (coal/palm oil/nickel) — Q3 demand slowdown
- 🔴 IDR fragile without commodity tailwind — USD sensitivity {indo.get('usd_sensitivity',0.55):.0%}
- 🔴 Hedgeye: SHORT Indonesia (EIDO) — high commodity sensitivity + low USD beta = wrong regime
- ✅ Recovery catalyst: USD TREND breakdown + China stimulus + BI rate pivot
**EIDO signal**: {'⚠️ Bearish — avoid' if q in ('Q3','Q4') else '✅ Monitor — improving'}""")

    ihsg_tickers=[t for t in ["^JKSE","EIDO"] if t in prices]
    if ihsg_tickers:
        st.plotly_chart(price_chart(prices,ihsg_tickers,"IHSG / EIDO (rebased=100)",252),use_container_width=True,config={"displayModeBar":False})

    # EIDO Risk Range
    eido_v=ar.get("EIDO",{})
    if eido_v:
        st.markdown("#### EIDO Risk Range")
        cc=st.columns(3)
        for i,(dur,data) in enumerate([("TRADE",eido_v.get("trade",{})),("TREND",eido_v.get("trend",{})),("TAIL",eido_v.get("tail",{}))]):
            sig=data.get("signal","neutral"); sc2=SC.get(sig,"#6B7280")
            cc[i].markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9CA3AF">{dur}</div><div style="font-size:18px;font-weight:700;color:{sc2}">{sig.upper()}</div><div style="font-size:11px;color:#E8ECF0">LRR:{ff(data.get("lrr"),2)} TRR:{ff(data.get("trr"),2)}</div><div style="font-size:10px;color:#9CA3AF">H={data.get("hurst",0.5):.2f}</div></div>',unsafe_allow_html=True)

    # ── IHSG Regime Playbook ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎯 IHSG Regime Playbook — Q{}".format(sq[-1]))
    pb=QUAD_ASSET_PERFORMANCE.get(sq,{})
    if sq in ("Q3","Q4"):
        st.error("❌ Q3/Q4 = IHSG HEADWIND. Avoid commodity plays. Only defensive banks (BBCA.JK) and telco (TLKM.JK) viable.")
        st.markdown("**✅ Defensive**: BBCA.JK (highest ROE bank ASEAN), TLKM.JK (dividend yield 5%+)")
        st.markdown("**❌ Avoid**: ITMG.JK, ADRO.JK, PTBA.JK (coal peaked), INCO.JK (nickel cyclical), Property sector")
    elif sq=="Q2":
        st.success("✅ Q2 = IHSG COMMODITY BID. Coal, nickel, CPO exporters lead. Banks follow foreign flow.")
        st.markdown("**✅ Best**: INCO.JK (nickel structural), ITMG.JK (coal dividend), BBCA.JK (foreign flow anchor)")
        st.markdown("**⚡ Monthly adds**: Commodity exporters on USD bearish TREND")
    else:
        st.success("✅ Q1 = IHSG MAX RECOVERY. Broad exposure viable. Tech, banks, consumer.")
        st.markdown("**✅ Best**: BBCA.JK, TLKM.JK, KLBF.JK (consumer defensive), INCO.JK")

    # ── IHSG Stocks by Sector + Bottleneck ─────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 IHSG Stocks by Sector")
    ihsg_groups={"Banks":["BBCA.JK","BBRI.JK","BMRI.JK"],"Coal":["ITMG.JK","ADRO.JK","PTBA.JK","HRUM.JK"],
        "Nickel/Mining":["INCO.JK","MDKA.JK","ANTM.JK","NCKL.JK"],"CPO":["LSIP.JK","AALI.JK","SSMS.JK"],
        "Consumer":["UNVR.JK","ICBP.JK","KLBF.JK","MYOR.JK"],"Property":["BSDE.JK","CTRA.JK","PWON.JK"]}
    rows=[]
    for grp,tickers in ihsg_groups.items():
        for t in tickers:
            s=prices.get(t)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1])
            r1m=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>22 else None
            r3m=float(s.iloc[-1]/s.iloc[-63]-1) if len(s)>63 else None
            v=ar.get(t,{})
            rows.append({"Sector":grp,"Ticker":t,"Price":ff(px,0),"1M":fp(r1m),"3M":fp(r3m),
                "Trade":v.get("trade_signal","—"),"Trend":v.get("trend_signal","—")})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df.style.map(lambda v:f"color:{SC.get(v,'#6B7280')}",subset=["Trade","Trend"]),hide_index=True,use_container_width=True,height=350)
    else: st.info("IHSG stocks not loaded. Enable IHSG in Universe settings and Refresh.")

    # ── IHSG Bottleneck Long-Only ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 IHSG Bottleneck — LONG ONLY · EV Ranked")
    st.caption(f"IHSG cannot be shorted. Sorted by EV+ (highest expected value first). Structural {sq} = {'headwind' if sq in ('Q3','Q4') else 'tailwind'}.")

    ih=btk.get("ihsg_long",[]); iha=btk.get("ihsg_avoid",[])
    t1,t2=st.tabs([f"🟢 LONG ({len(ih)})",f"⚪ AVOID ({len(iha)})"])

    with t1:
        if ih:
            rows=[]
            for c in ih[:30]:
                badge = "⚡ BOTTLENECK" if c.get("known") else ""
                tp=c.get("tp",{})
                rows.append({"Ticker":c["ticker"] + (f" {badge}" if badge else ""),"Sector":c["sector"].replace("_"," ").title(),
                    "EV":f"{c['ev']:+.3f}","Score":c["score"],"Trend":c["trend"].title(),
                    "Accum":fp(c["acc"]),"RS 3M":fp(c.get("rs_3m")),"Range":c["range_label"],
                    "TP":_fmt_tp(tp),"Thesis":c.get("known_thesis","")[:60]})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=400)
        else:
            st.info(f"No IHSG long candidates in {sq}. Q3/Q4 = IHSG headwind. Wait for regime flip to Q2/Q1.")
            st.markdown("#### 🌍 When will IHSG recover?")
            st.markdown("""**Q3→Q2 transition** = earliest EM recovery signal.
- Trigger: Monthly Q2 inside Structural Q3 + commodity bid + USD bearish TREND
- Best IHSG plays: BBCA.JK (defensive bank), TLKM.JK (telco dividend), INCO.JK (nickel structural)
- Avoid: Coal plays (ITMG.JK, ADRO.JK) — commodity cycle peaked""")

    with t2:
        if iha:
            rows=[{"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),
                "EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),"Reason":"Trend down in Q3/Q4 — avoid"} for c in iha[:15]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=250)
        else: st.info("No IHSG avoid candidates.")

# ══════════════════════════════════════════════════════════════════════════════
# BOTTLENECK (Simplified)
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🔍 Bottleneck":
    st.markdown("# 🔍 Bottleneck Research — Known Plays · Brewing · Traps")
    st.caption("Deep-research bottleneck cases + pre-breakout brewing detection + regime traps.")
    if not btk: st.warning("No scanner data. Refresh."); st.stop()

    meta=btk.get("meta",{}); pb2=btk.get("playbook",{})

    s1,s2,s3=st.columns(3)
    s1.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:700;color:#F59E0B">{meta.get("brewing_count",0)}</div><div style="font-size:10px;color:#9CA3AF">⚗️ Brewing</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:700;color:#00D4AA">{len(btk.get("level_1",[]))}</div><div style="font-size:10px;color:#9CA3AF">⚡ Level 1</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:700;color:#EF4444">{len(btk.get("regime_traps",[]))}</div><div style="font-size:10px;color:#9CA3AF">⚠️ Traps</div></div>',unsafe_allow_html=True)

    with st.expander("📋 Regime Playbook + TP Framework",expanded=True):
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"**✅ Regime best**: {', '.join(pb2.get('sectors_overweight',[]))}")
            st.markdown(f"**📈 Best assets**: {', '.join(pb2.get('best',[])[:5])}")
            st.markdown(f"**💱 FX**: {pb2.get('fx','')}")
        with c2:
            st.markdown(f"**❌ Avoid**: {', '.join(pb2.get('sectors_underweight',[]))}")
            st.markdown(f"**📉 Worst**: {', '.join(pb2.get('worst',[])[:5])}")
            st.markdown(f"**🏦 Bonds**: {pb2.get('bonds','')}")
            st.markdown("---")
            st.markdown("""**TP Framework:**
- **Structural**: T1=TRADE TRR (25%) → T2=TREND TRR (50%) → T3=ATH (trail 25%). EXIT on TREND LRR break.
- **Float Squeeze**: T1=+30% (50%) → T2=+55% (40%). TIME STOP: 5 days. -12% hard.
- **Commodity**: T1=+1σ (33%) → T2=+2σ (33%) → T3=52w high (34%). -15% hard.
- **IHSG**: T1=TRADE TRR/+12% → T2=TREND TRR. Exit 100% on 2x foreign net sell.
- **Crypto**: T1=+40% (50%) → T2=+100% (40%). EXIT 14 days BEFORE unlock. -20% hard.
- **Forex**: T1=+2σ 21d (40%) → T2=+4σ 63d (40%). EXIT on regime flip.""")

    on_a=btk.get("on_analysis",{})
    with st.expander("🔍 ON Semiconductor Case Study"):
        st.markdown(f"**Status**: {on_a.get('current_status','')}")
        st.markdown(f"**Type**: {on_a.get('type','')}")
        st.markdown("**Why it surged:**")
        for r in on_a.get("why_surged",[]): st.markdown(f" • {r}")
        st.markdown("**Analogs now:**")
        for r in on_a.get("analogs_now",[]): st.markdown(f" • {r}")

    ph=btk.get("photonics",{})
    with st.expander("🔆 Photonics / CPO Chain (NVIDIA $4B confirmed)"):
        st.markdown(f"**{ph.get('thesis','')}**")
        st.markdown("**Supply chain layers:**")
        for l in ph.get("supply_chain",[]): st.markdown(f" • **{l['layer']}** — {l.get('note','')} → `{l.get('status','')}`")
        st.markdown(f"**Next pre-breakout**: {', '.join(ph.get('next_layer',[]))}")
        st.markdown(f"**Already run**: {', '.join(ph.get('already_run',[]))}")

    tabs=st.tabs(["⚗️ Brewing","📌 Known Plays","❌ Avoid","⚠️ Regime Traps"])

    with tabs[0]:
        st.markdown("### ⚗️ Brewing — Pre-Breakout Setups")
        st.caption("High constraint + regime fit + accumulation. Not yet level_1/2. Early entry.")
        br=btk.get("brewing",[])
        if br:
            rows=[]
            for c in br[:25]:
                rows.append({"Ticker":c["ticker"],"Market":c["market"].upper(),"Sector":c["sector"].replace("_"," ").title(),
                    "EV":f"{c['ev']:+.3f}","Constraint":fp(c["constraint"]),"Regime Fit":fp(c["regime_fit"]),
                    "Accum":fp(c["acc"]),"Trend":c["trend"].title(),"Range":c["range_label"],
                    "Thesis":c.get("known_thesis","")[:60]})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=420)
        else: st.info("No brewing setups. Check back after accumulation patterns form.")

    with tabs[1]:
        st.markdown("### 📌 Known Bottleneck Plays (Deep Research)")
        known=[c for c in btk.get("all_candidates",[]) if c.get("known")]
        if known:
            rows=[]
            for c in known[:20]:
                tp=c.get("tp",{})
                rows.append({"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),
                    "Type":c.get("btn_type","—"),"Phase":c["level"].replace("_"," ").title(),
                    "EV":f"{c['ev']:+.3f}","Score":c["score"],
                    "TP":_fmt_tp(tp),"Catalyst":c.get("known_catalyst","")[:50]})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(_ev_color,subset=["EV"]),hide_index=True,use_container_width=True,height=350)
        else: st.info("No known plays detected.")

    with tabs[2]:
        st.markdown("### ❌ Avoid — Wrong Regime / Wrong Trend")
        av=btk.get("avoid",[])
        if av:
            rows=[{"Ticker":c["ticker"],"Market":c["market"].upper(),"Sector":c["sector"].replace("_"," ").title(),
                "EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),"Reason":"Downtrend / Low regime fit"} for c in av[:15]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=300)
        else: st.info("No avoid candidates.")

    with tabs[3]:
        st.markdown("### ⚠️ Regime Traps — Looks Like Bottleneck, But Wrong Quad")
        traps=btk.get("regime_traps",[])
        if traps:
            rows=[{"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),
                "EV":f"{c['ev']:+.3f}","Trend":c["trend"].title(),
                "Why Trap":f"{c['btn_type']} in {sq} = wrong regime"} for c in traps[:15]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=300)
            st.error("⚠️ These have bottleneck characteristics but are REGIME TRAPS. Do NOT buy.")
        else: st.success("No regime traps detected.")

# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page=="📖 Narratives":
    st.markdown("# 📖 Active Narratives — Auto-Discovery")
    st.caption("Narratives scored from price action. No news API needed. Brewing = early alpha before consensus.")
    
    if not narr:
        st.warning("No narrative data. Refresh."); st.stop()
    
    sm=narr.get("summary",{})
    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div style="background:#1F2B3D;border-radius:8px;padding:12px"><div style="font-size:20px;font-weight:700;color:#10B981">{sm.get("active_count",0)}</div><div style="font-size:10px;color:#9CA3AF">ACTIVE</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div style="background:#1F2B3D;border-radius:8px;padding:12px"><div style="font-size:20px;font-weight:700;color:#F59E0B">{sm.get("building_count",0)}</div><div style="font-size:10px;color:#9CA3AF">BUILDING</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div style="background:#1F2B3D;border-radius:8px;padding:12px"><div style="font-size:20px;font-weight:700;color:#6B7280">{sm.get("brewing_count",0)}</div><div style="font-size:10px;color:#9CA3AF">BREWING</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div style="background:#1F2B3D;border-radius:8px;padding:12px"><div style="font-size:12px;font-weight:700;color:#00D4AA">{sm.get("top_conviction","—")[:25]}</div><div style="font-size:10px;color:#9CA3AF">TOP CONVICTION</div></div>',unsafe_allow_html=True)

    def _narr_card(n, expanded=False):
        stage=n.get("stage","—"); score=n.get("score",0); conv=n.get("conviction",0)
        sc={"active":"#10B981","building":"#F59E0B","brewing":"#6B7280","dormant":"#374151"}.get(stage,"#374151")
        badge={"active":"🟢 ACTIVE","building":"🟡 BUILDING","brewing":"⚪ BREWING","dormant":"⚫ DORMANT"}.get(stage,"")
        benef=[t for tlist in n.get("beneficiaries",{}).values() for t in tlist[:3]]
        fades=[t for tlist in n.get("fades",{}).values() for t in tlist[:2]]
        with st.expander(f"{badge} {n['name']} — Score:{score:.2f} | Conv:{conv:.0%} | Pump:{n.get('pump_risk',0):.0%}", expanded=expanded):
            st.markdown(f"*{n.get('description','')[:150]}*")
            cc=st.columns(3)
            cc[0].markdown(f"**✅ LONG**: {', '.join(benef[:5])}")
            cc[1].markdown(f"**❌ FADE**: {', '.join(fades[:3])}")
            cc[2].markdown(f"**Duration**: ~{n.get('typical_weeks',8)}w")
            if n.get("confirmation_signals"):
                st.caption(f"Confirm: {' | '.join(n['confirmation_signals'][:3])}")
            if n.get("catalyst_types"):
                st.caption(f"Catalyst: {' | '.join(n['catalyst_types'][:3])}")

    tab1,tab2,tab3,tab4,tab5 = st.tabs(["🟢 Active","🟡 Building","⚪ Brewing (Alpha)","📍 By Market","🔮 Pre-Consensus"])
    
    with tab1:
        active = narr.get("active",[])
        if active:
            for n in active[:8]: _narr_card(n, expanded=(active.index(n)==0))
        else: st.info(f"No active narratives in {sq}. Most narratives dormant in this regime.")
    
    with tab2:
        for n in narr.get("building",[])[:8]: _narr_card(n)
    
    with tab3:
        st.caption("⚡ **Brewing** = high constraint + regime fit + accumulation starting. These are the early-entry alpha plays before they become consensus.")
        for n in narr.get("brewing",[])[:8]: _narr_card(n)
    
    with tab4:
        market_tabs = st.tabs(["🇺🇸 US","🇮🇩 IHSG","₿ Crypto","💱 Forex","🛢 Commodity"])
        for mtt, mkey in zip(market_tabs, ["us_narratives","ihsg_narratives","crypto_narratives","fx_narratives","commodity_narratives"]):
            with mtt:
                for n in narr.get(mkey,[])[:6]: _narr_card(n)
    
    with tab5:
        st.caption("🎯 **Pre-Consensus** = regime-aligned narratives that are brewing but not yet widely known. Low pump risk, high regime fit = the transformer/switchgear type setup.")
        for n in narr.get("pre_consensus",[])[:8]: _narr_card(n)

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🔮 Scenarios":
    st.markdown("# 🔮 Adaptive Scenarios + Quad Transition Map")
    st.caption("Data-driven regime transition discovery. Probabilities update with live GIP features.")
    if not scen: st.warning("No scenario data."); st.stop()

    stab=scen.get("regime_stability","unknown")
    c1,c2,c3=st.columns(3)
    c1.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9CA3AF">Regime Stability</div><div style="font-size:20px;font-weight:700;color:{"#10B981" if stab=="stable" else "#F59E0B"}">{stab.upper()}</div></div>',unsafe_allow_html=True)
    c2.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9CA3AF">Flip Risk</div><div style="font-size:20px;font-weight:700;color:{"#EF4444" if scen.get("flip_hazard",0)>0.4 else "#F59E0B"}">{scen.get("flip_hazard",0):.0%}</div></div>',unsafe_allow_html=True)
    c3.markdown(f'<div style="background:#1F2B3D;border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9CA3AF">Current → Most Likely</div><div style="font-size:16px;font-weight:700;color:#E8ECF0">{scen.get("base_case").name if scen.get("base_case") else "—"}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Quad Transition Probabilities")
    scenarios=scen.get("scenarios",[])
    if scenarios:
        trans_probs={s.to_quad:s.probability for s in scenarios}
        fig=go.Figure()
        for q,p in sorted(trans_probs.items()):
            fig.add_bar(x=[q],y=[p],marker_color=QC.get(q,"#9CA3AF"),text=[f"{p:.0%}"],textposition="outside")
        fig.update_layout(showlegend=False,height=220,margin=dict(t=25,b=5,l=0,r=0),
            paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0"),
            title=dict(text=f"From {sq} → Next Quad Probabilities",font=dict(size=12,color="#9CA3AF")),
            yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),
            xaxis=dict(showgrid=False),bargap=0.35)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    st.markdown("---")
    st.markdown("### 🔮 Scenario Details")
    for i,s in enumerate(scenarios):
        badge=["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"][min(i,3)]
        pc="#10B981" if s.probability>0.40 else "#F59E0B" if s.probability>0.25 else "#6B7280"
        with st.expander(f"{badge} {s.name} — P={s.probability:.0%} | Conf={s.confirmation_score:.0%} | {s.headline}",expanded=(i==0)):
            cc=st.columns(3)
            cc[0].metric("Probability",f"{s.probability:.0%}")
            cc[1].metric("Confirmation",f"{s.confirmation_score:.0%}")
            cc[2].metric("Timeframe",f"~{s.timeframe_weeks}w")
            c1,c2=st.columns(2)
            with c1:
                st.markdown(f"**✅ Best**: {', '.join(s.best_assets[:5])}")
                st.markdown("**🔔 Triggers:**")
                for t in s.confirmation_triggers[:4]: st.markdown(f" • {t}")
            with c2:
                st.markdown(f"**❌ Avoid**: {', '.join(s.worst_assets[:5])}")
                st.markdown("**🚫 Invalidators:**")
                for t in s.invalidators[:3]: st.markdown(f" • {t}")
            st.caption(f"Catalyst: {s.catalyst} | Conviction: {s.conviction}")

            if s.name in ("Q3→Q2","Q4→Q1","Q3→Q1"):
                em_note={"Q3→Q2":"EM commodity exporters early recovery. Monthly Q2 = commodity bid.",
                    "Q4→Q1":"MAX EM recovery. Historical +25-40% in first 6M of Q1.",
                    "Q3→Q1":"Selective EM recovery. Only high-quality EM (India, Indonesia, Singapore)."}.get(s.name,"")
                st.success(f"🌍 EM IMPLICATION: {em_note}")

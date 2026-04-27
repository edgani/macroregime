"""app.py — MacroRegime Pro v14 | Hedgeye GIP Framework + 10/10 Autonomy

Features:
- Per-market tab: Regime Playbook (top EV+) + Bottleneck Long/Short
- Bottleneck badge on known plays
- IHSG: EM Rotation Phase + Recovery Timeline
- NEW: 🔮 Early Discovery — pre-consensus bottleneck/narrative/transition detection
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(page_title="MacroRegime Pro",page_icon="📊",layout="wide",initial_sidebar_state="expanded")

st.markdown("""<style>
.brewing-badge { display:inline-block; padding:2px 8px; border-radius:4px; background:#6B7280; color:white; font-size:11px; font-weight:bold; }
.building-badge { display:inline-block; padding:2px 8px; border-radius:4px; background:#F59E0B; color:white; font-size:11px; font-weight:bold; }
.active-badge { display:inline-block; padding:2px 8px; border-radius:4px; background:#10B981; color:white; font-size:11px; font-weight:bold; }
.chokepoint-badge { display:inline-block; padding:2px 8px; border-radius:4px; background:#EF4444; color:white; font-size:11px; font-weight:bold; }
.precon-card { background:#1F2937; border-left:4px solid #F59E0B; padding:12px; border-radius:6px; margin-bottom:8px; }
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
 return f"""<div style="background:#1F2937;border-radius:8px;padding:12px;text-align:center;border-top:4px solid {qc(q)}">
<div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px">{label}</div>
<div style="font-size:28px;font-weight:800;color:{qc(q)};margin:4px 0">{q[-1] if q in QN else "?"}</div>
<div style="font-size:13px;color:#E8ECF0;font-weight:600">{qn(q)}</div>
{("<div style=\"font-size:10px;color:#9CA3AF;margin-top:4px\">" + note + "</div>") if note else ""}
<div style="font-size:10px;color:#9CA3AF;margin-top:6px">Conf: {conf:.0%}</div>
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

# ── MODULE-LEVEL RENDERERS (must be before page dispatch) ────────────────────
def _btk_badge(ticker, btk_data):
 for lvl in ["level_1","level_2","watch","avoid"]:
  for x in btk_data.get(lvl,[]):
   if x.get("ticker")==ticker:
    colors={"level_1":"#10B981","level_2":"#F59E0B","watch":"#6366F1","avoid":"#EF4444"}
    return f"<span style='background:{colors[lvl]};color:white;padding:1px 5px;border-radius:3px;font-size:9px'>{lvl.replace('_','').upper()}</span>"
 return ""

def _render_universe(title, tickers_map, prices, btk_data, days=252):
 st.markdown(f"### {title}")
 rows=[]
 for sym, info in tickers_map.items():
  s=prices.get(sym)
  if s is None: continue
  s=pd.to_numeric(s,errors="coerce").dropna().tail(days)
  if s.empty: continue
  ret1m=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
  ret3m=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
  ret6m=float(s.iloc[-1]/s.iloc[-126]-1) if len(s)>=126 else 0
  badge=_btk_badge(sym, btk_data)
  rows.append({"Ticker":sym,"Name":info if isinstance(info,str) else info.get("name",sym),
   "1M":f"{ret1m:+.1%}","3M":f"{ret3m:+.1%}","6M":f"{ret6m:+.1%}",
   "Bottleneck":badge})
 if rows:
  df=pd.DataFrame(rows)
  st.markdown(df.to_html(escape=False,index=False),unsafe_allow_html=True)
  fig=price_chart(prices, list(tickers_map.keys())[:8], title=f"{title} — Normalized", days=days)
  st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
 else:
  st.info("No data loaded for this universe.")

def _render_scenario(sc, label, color, badge):
 if not sc: return
 # Handle both dict and object
 if isinstance(sc, dict):
  name=sc.get("name",""); prob=sc.get("probability",0); conf=sc.get("confirmation_score",0)
  headline=sc.get("headline",""); catalyst=sc.get("catalyst",""); em_note=sc.get("em_note","")
  best=sc.get("best_assets",[]); worst=sc.get("worst_assets",[])
  conv=sc.get("conviction",""); triggers=sc.get("confirmation_triggers",[])
  invalidators=sc.get("invalidators",[])
 else:
  name=sc.name; prob=sc.probability; conf=sc.confirmation_score
  headline=sc.headline; catalyst=sc.catalyst; em_note=sc.em_note
  best=sc.best_assets; worst=sc.worst_assets; conv=sc.conviction
  triggers=sc.confirmation_triggers; invalidators=sc.invalidators
 with st.expander(f"{badge} {label} — P={prob:.0%} · Conf={conf:.0%}", expanded=(label=="BASE")):
  st.markdown(f"**Headline:** {headline}")
  st.markdown(f"**Catalyst:** {catalyst}")
  st.markdown(f"**Confirmation triggers:** {' · '.join(triggers) if triggers else 'Data-dependent'}")
  st.markdown(f"**EM Note:** {em_note}")
  st.markdown(f"**Invalidators:** {' · '.join(invalidators) if invalidators else 'None defined'}")
  if best: st.markdown(f"**Best:** {' · '.join(best[:10])}")
  if worst: st.markdown(f"**Worst:** {' · '.join(worst[:10])}")

# ── Session state ─────────────────────────────────────────────────────────────
if "snap" not in st.session_state: st.session_state.snap=None
if "loading" not in st.session_state: st.session_state.loading=False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
 st.markdown("## 📊 MacroRegime Pro")
 st.markdown("*Hedgeye GIP · v14 · Autonomy*")
 st.divider()
 page = st.radio("", [
  "🏠 Dashboard","📈 GIP Regime","⏱️ Timing","🎯 Risk Ranges",
  "🌍 Global Quad","📊 US Stocks",
  "💱 Forex","🛢 Commodities","₿ Crypto",
  "🇮🇩 IHSG","🔍 Bottleneck","📖 Narratives","🔮 Early Discovery","🏥 Health","🔮 Scenarios",
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
 st.error("❌ No snapshot. Click **🔄 Refresh** or **⚡ Force** to rebuild."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
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
stress = snap.get("stress",{})
auto_disc = snap.get("auto_discoveries",{})
fb_eval = snap.get("feedback_eval",{})

sq=gip.structural_quad if gip else "Q3"
mq=gip.monthly_quad if gip else "Q2"
gq=global_.get("global_quad","Q3")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page=="🏠 Dashboard":
 st.markdown(f"<div style='text-align:right;font-size:10px;color:#6B7280'>Built {snap.get('build_time_s',0)}s · Prices: {snap.get('prices_loaded',0)} · FRED: {snap.get('fred_coverage',0)} · RR: {snap.get('price_frames_count',0)}</div>",unsafe_allow_html=True)
 st.markdown("# MacroRegime Pro — Dashboard")

 c1,c2,c3,c4=st.columns(4)
 with c1: st.markdown(qcard("STRUCTURAL (Climate)",sq,gip.structural_conf if gip else 0,"Quarterly"),unsafe_allow_html=True)
 with c2: st.markdown(qcard("MONTHLY (Weather)",mq,gip.monthly_conf if gip else 0,"3-6 Week Overlay"),unsafe_allow_html=True)
 with c3: st.markdown(qcard("GLOBAL",gq,global_.get("global_conf",0),"50 Countries"),unsafe_allow_html=True)
 with c4:
  if gip:
   dc=qc(sq); flip=gip.flip_hazard
   st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:12px;text-align:center;border-top:4px solid {dc}'>
<div style='font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px'>ALIGNMENT</div>
<div style='font-size:20px;font-weight:800;color:{dc};margin:4px 0'>{gip.divergence.upper()}</div>
<div style='font-size:12px;color:#E8ECF0'>{gip.operating_regime}</div>
<div style='font-size:10px;color:#9CA3AF;margin-top:6px'>Flip Risk: {flip:.0%}</div>
</div>""",unsafe_allow_html=True)

 # Front-Run Banner
 if transition:
  fw = transition.front_run_window
  fr = transition.front_run_rationale
  fw_color = {"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
  fw_icon = {"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
  if fw != "not yet":
   st.markdown(f"""<div style='background:{fw_color}22;border-left:4px solid {fw_color};padding:10px 14px;border-radius:6px;margin:12px 0'>
<span style='color:{fw_color};font-weight:800'>{fw_icon} FRONT-RUN WINDOW: {fw.upper()}</span><br/>
<span style='color:#E8ECF0;font-size:13px'>{fr}</span>
</div>""", unsafe_allow_html=True)

 # Early Discovery Alert on Dashboard
 if auto_disc:
  candidates = auto_disc.get("candidates",[])
  brewing = [c for c in candidates if c.get("stage")=="brewing"]
  if brewing:
   top_brew = max(brewing, key=lambda x:x.get("confidence",0))
   st.markdown(f"""<div style='background:#F59E0B11;border-left:4px solid #F59E0B;padding:10px 14px;border-radius:6px;margin:12px 0'>
<span style='color:#F59E0B;font-weight:800'>🔮 EARLY DISCOVERY ALERT</span> — {len(brewing)} pre-consensus opportunity detected<br/>
<span style='color:#E8ECF0;font-size:13px'>Top: <b>{top_brew.get('name','')}</b> — {top_brew.get('thesis','')[:80]}...</span>
<span style='color:#9CA3AF;font-size:11px'> → Go to <b>🔮 Early Discovery</b> tab</span>
</div>""", unsafe_allow_html=True)

 # Quad Transition Probability
 if gip:
  st.markdown("<br/>",unsafe_allow_html=True)
  st.markdown("### 📊 Quad Transition Probabilities")
  QUAD_NAMES = {"Q1":"Goldilocks (Growth↑ Inflation↓)","Q2":"Reflation (Growth↑ Inflation↑)","Q3":"Stagflation (Growth↓ Inflation↑)","Q4":"Deflation (Growth↓ Inflation↓)"}
  QUAD_WHAT_WINS = {"Q1":"Cyclicals, Tech, Small Caps, Equal-weight","Q2":"Energy, Materials, Commodity FX, TIPS","Q3":"Gold, USD, Defensives, Short Duration","Q4":"Long Duration (TLT), Gold, Defensives"}

  def _transition_panel(probs, current_q, horizon_label, horizon_desc):
   if not probs: return
   sorted_p = sorted(probs.items(), key=lambda x: x[1], reverse=True)
   top_q, top_p = sorted_p[0]
   cur_c = QC.get(current_q,"#9CA3AF")
   top_c = QC.get(top_q,"#9CA3AF")
   st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;margin-bottom:8px'>
<div style='font-size:10px;color:#9CA3AF;text-transform:uppercase'>{horizon_label} — {horizon_desc}</div>
<div style='font-size:12px;color:#E8ECF0;margin-top:4px'>Currently: <b style='color:{cur_c}'>{current_q}</b> — {QUAD_NAMES.get(current_q,'')}</div>
<div style='font-size:12px;color:#E8ECF0;margin-top:2px'>Most likely → <b style='color:{top_c}'>{top_q}</b> ({top_p:.0%})</div>
</div>""", unsafe_allow_html=True)
   fig = go.Figure()
   for q, p in sorted(probs.items()):
    is_top = (q == top_q)
    fig.add_bar(x=[q], y=[p], marker_color=QC.get(q,"#9CA3AF"),
     marker_line=dict(width=3 if is_top else 0, color="white"),
     text=[f"<b>{p:.0%}</b>"], textposition="outside",
     textfont=dict(size=13, color=QC.get(q,"#E8ECF0")), name=q)
   fig.update_layout(showlegend=False, height=180, margin=dict(t=10,b=8,l=4,r=4),
    paper_bgcolor="#111827", plot_bgcolor="#111827", font=dict(color="#E8ECF0", family="JetBrains Mono"),
    yaxis=dict(range=[0,1.15], tickformat=".0%", showgrid=True, gridcolor="#1F2B3D", tickfont=dict(size=10)),
    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#E8ECF0")), bargap=0.3)
   st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
   if top_q != current_q:
    action_map = {
     ("Q3","Q4"):("Deflation rotation","Inflation cooling → add TLT/duration, gold; reduce energy"),
     ("Q3","Q2"):("False dawn / head-fake","Growth stabilizes but inflation stays hot → stay short duration"),
     ("Q3","Q1"):("Clean recovery","Both inflation cools AND growth rebounds → max risk-on"),
     ("Q4","Q1"):("Goldilocks restart","Fed easing + growth recovery → maximum long positioning"),
     ("Q4","Q3"):("Supply shock re-ignition","Oil spike before growth recovers → gold/defense only"),
     ("Q1","Q2"):("Reflation beginning","Inflation re-accelerates → add energy/materials, trim bonds"),
     ("Q1","Q4"):("Growth fatigue","Late-cycle slowdown → rotate to defensives/quality"),
     ("Q2","Q3"):("Stagflation pressure intensifying","Growth decelerating, inflation sticky → reduce beta"),
     ("Q2","Q1"):("Soft landing","Growth holds, inflation cools → remain long cyclicals"),
    }
    key = (current_q, top_q)
    action_title, action_note = action_map.get(key, (f"{current_q}→{top_q} transition", QUAD_WHAT_WINS.get(top_q,"")))
    st.markdown(f"""<div style='background:#1F2937;border-radius:6px;padding:8px 12px;margin-top:4px'>
<span style='color:#F59E0B;font-weight:700'>IF {top_q} materializes: {action_title}</span><br/>
<span style='color:#9CA3AF;font-size:12px'>{action_note}</span>
</div>""", unsafe_allow_html=True)
   else:
    st.markdown(f"""<div style='background:#1F2937;border-radius:6px;padding:8px 12px;margin-top:4px'>
<span style='color:#10B981;font-weight:700'>📌 Most likely: {current_q} continuation</span> — {QUAD_WHAT_WINS.get(current_q,'')}
</div>""", unsafe_allow_html=True)

  tp1,tp2,tp3 = st.columns(3)
  with tp1: _transition_panel(gip.structural_probs, sq, "STRUCTURAL", "Quarterly Cycle")
  with tp2: _transition_panel(gip.monthly_probs, mq, "MONTHLY", "Weather/Tactical")
  with tp3:
   gprobs = global_.get("global_probs",{})
   gq_panel = global_.get("dominant_quad", gq)
   if gprobs: _transition_panel(gprobs, gq_panel, "GLOBAL", "50 Countries")

 # Scenario cards
 scenarios_list = scen.get("scenarios",[])
 if scenarios_list:
  badges = ["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]
  badge_colors = ["#10B981","#F59E0B","#EF4444","#6366F1"]
  row1, row2 = st.columns(2), st.columns(2)
  grids = [row1[0], row1[1], row2[0], row2[1]]
  for i, (sc_item, col) in enumerate(zip(scenarios_list[:4], grids)):
   pc = badge_colors[i]
   em_short = sc_item.em_note[:70] + "..." if len(sc_item.em_note) > 70 else sc_item.em_note
   with col:
    st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;border-left:4px solid {pc};margin-bottom:8px'>
<div style='font-size:10px;color:{pc};font-weight:800'>{badges[i]} P={sc_item.probability:.0%} · Conf={sc_item.confirmation_score:.0%}</div>
<div style='font-size:13px;color:#E8ECF0;font-weight:700;margin-top:4px'>{sc_item.name}</div>
<div style='font-size:11px;color:#9CA3AF;margin-top:2px'>{sc_item.headline}</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>🌍 {em_short}</div>
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
  st.markdown("### 🚨 Critical Alerts")
  for sym,a in crits:
   st.markdown(f'<div style="background:#EF444411;border-left:3px solid #EF4444;padding:6px 10px;border-radius:4px;margin-bottom:4px">⚠️ <b>[{sym}]</b> {a["action"]} | {a.get("note","")}</div>',unsafe_allow_html=True)

 l1=btk.get("level_1",[]); l2=btk.get("level_2",[])
 top=l1[:2]+l2[:2]
 if top:
  st.markdown("### 🔍 Top Bottleneck Setups")
  cols=st.columns(min(len(top),4))
  for i,c in enumerate(top[:4]):
   with cols[i]:
    tc="#10B981" if c["trend"]=="uptrend" else "#EF4444" if c["trend"]=="downtrend" else "#F59E0B"
    badge="⚡L1" if c["level"]=="level_1" else "📈L2"
    st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center;border-top:3px solid {tc}'>
<div style='font-size:10px;color:#9CA3AF'>{badge} {c['ticker']}</div>
<div style='font-size:11px;color:#E8ECF0;margin-top:4px'>{c['sector'].replace('_',' ').title()}</div>
<div style='font-size:10px;color:{tc};font-weight:700'>{c['trend'].upper()}</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>Score: {c['score']:.2f} | EV: {c.get('ev',0):.2f}</div>
{('<div style="font-size:9px;color:#EF4444;margin-top:4px">⚠️ REGIME TRAP</div>') if c.get("regime_trap") else ''}
</div>""",unsafe_allow_html=True)

 em_sig = btk.get("em_recovery", {}) if btk else {}
 if em_sig:
  st.markdown("### 🌍 EM Recovery Signal")
  conf = em_sig.get("confidence", 0)
  ec = "#10B981" if conf > 0.6 else "#F59E0B" if conf > 0.4 else "#6B7280"
  st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:12px;border-left:4px solid {ec}'>
<div style='font-size:13px;color:#E8ECF0;font-weight:700'>{em_sig.get('trigger','')}</div>
<div style='font-size:11px;color:#9CA3AF;margin-top:4px'>{em_sig.get('rationale','')}</div>
<div style='font-size:10px;color:{ec};margin-top:6px'>Confidence: {conf:.0%}</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>🎯 Best: {', '.join(em_sig.get('best',[])[:6])}</div>
</div>""",unsafe_allow_html=True)

 bc = scen.get("base_case")
 if bc:
  st.markdown(f"""<div style='background:#1F2937;border-radius:6px;padding:8px 12px;margin-top:8px'>
🔮 Base: <b>{bc.name}</b> — {bc.headline[:60]}...→ See <b>Scenarios</b> tab for full action plan
</div>""", unsafe_allow_html=True)

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
# TIMING
# ══════════════════════════════════════════════════════════════════════════════
elif page=="⏱️ Timing":
 st.markdown("# ⏱️ Timing — Next Quad + Front-Run Window")
 st.caption("When is the next regime shift? What early warning signals are firing? How to front-run before the market confirms.")
 if not transition:
  st.warning("Transition engine data not available. Refresh."); st.stop()

 fw = transition.front_run_window
 fr = transition.front_run_rationale
 fw_colors = {"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}
 fw_labels = {"now":"🚨 ACT NOW","1-2w":"⚡ POSITION 1-2 WEEKS","3-6w":"👀 WATCH 3-6 WEEKS","not yet":"🛑 NO SIGNAL YET"}
 fc = fw_colors.get(fw,"#374151")
 st.markdown(f"""<div style='background:{fc}22;border-left:4px solid {fc};padding:14px;border-radius:8px;margin-bottom:16px'>
<div style='font-size:18px;font-weight:800;color:{fc}'>{fw_labels.get(fw,"")}</div>
<div style='font-size:13px;color:#E8ECF0;margin-top:6px'>{fr}</div>
</div>""", unsafe_allow_html=True)

 st.markdown("### 📊 Transition Paths — Probability + Timing")
 paths = transition.transition_paths
 if paths:
  rows = []
  for p in paths:
   ew_pct = f"{p.early_warning_score:.0%}"
   rows.append({
    "Path": p.from_quad+"→"+p.to_quad,
    "P(transition)": f"{p.probability:.0%}",
    "Timeframe": f"~{p.timeframe_weeks}w",
    "EW Score": ew_pct,
    "Confidence": f"{p.confidence:.0%}",
    "Most likely asset": list(p.asset_implications.values())[0][:40] if p.asset_implications else "—",
   })
  st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

  for p in paths[:3]:
   path_c = QC.get(p.to_quad,"#9CA3AF")
   ew_frac = f"{int(p.early_warning_score*100)}%"
   with st.expander(f"{p.from_quad}→{p.to_quad} — P={p.probability:.0%} · EW={ew_frac} · ~{p.timeframe_weeks}w", expanded=(p.probability==paths[0].probability)):
    col_l,col_r = st.columns(2)
    with col_l:
     st.markdown(f"**Asset Implications:**")
     for mkt, impl in p.asset_implications.items():
      mkt_c = "#10B981" if "bullish" in impl.lower() else "#EF4444" if "bearish" in impl.lower() else "#9CA3AF"
      st.markdown(f'<span style="color:{mkt_c}">{mkt.upper()}</span>: {impl}', unsafe_allow_html=True)
    with col_r:
     st.markdown("**✅ Confirmation triggers:**")
     for t in p.confirmation_needed: st.markdown(f"• {t}")
     st.markdown("**🚫 Invalidators:**")
     for t in p.invalidators: st.markdown(f"• {t}")

 ew_sigs = transition.early_warning_signals
 if ew_sigs:
  st.markdown("---")
  st.markdown("### 🔔 Early Warning Signals")
  st.caption("1.0 = signal firing, 0.0 = not yet. Watch for clusters turning ON.")
  ew_rows = [{"Signal": k.replace("_"," ").title(), "Firing": "✅ YES" if v>=0.5 else "⬜ Not yet", "Score": f"{v:.0f}"} for k,v in sorted(ew_sigs.items(), key=lambda x: x[1], reverse=True)]
  df_ew = pd.DataFrame(ew_rows)
  st.dataframe(df_ew, hide_index=True, use_container_width=True, height=300)
  firing_count = sum(1 for v in ew_sigs.values() if v >= 0.5)
  total = len(ew_sigs)
  pct = firing_count/total if total else 0
  st.progress(pct, text=f"Early warning: {firing_count}/{total} signals firing ({pct:.0%})")

 if analogs and analogs.get("top_analogs"):
  st.markdown("---")
  st.markdown("### 📚 Historical Analogs")
  st.caption(analogs.get("composite_note",""))
  for a in analogs["top_analogs"]:
   sim = a.get("similarity",0)
   sim_c = "#10B981" if sim>0.6 else "#F59E0B" if sim>0.4 else "#6B7280"
   with st.expander(f"**{a['label']}** — Similarity: {sim:.0%}", expanded=(analogs["top_analogs"].index(a)==0)):
    cc = st.columns(3)
    cc[0].markdown(f"**1M:** {a.get('path_1m','')}")
    cc[1].markdown(f"**3M:** {a.get('path_3m','')}")
    cc[2].markdown(f"**6M:** {a.get('path_6m','')}")
    st.markdown(f"**Next bias:** {a.get('next_bias','')}")
    st.markdown(f"**Impacts:** " + " | ".join([f"{k.upper()}={v}" for k,v in a.get("impacts",{}).items()]))

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
  col.markdown(f'<div style="text-align:center"><div style="font-size:28px;font-weight:800;color:{c}">{val}</div><div style="font-size:10px;color:#9CA3AF">{lab}</div></div>',unsafe_allow_html=True)

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
  st.markdown("---")
  st.markdown("### 🔔 Alerts")
  for sym,a in all_a[:20]:
   ic="🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
   st.markdown(f'<div style="background:#1F2937;border-left:3px solid {"#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"};padding:6px 10px;border-radius:4px;margin-bottom:4px">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🌍 Global Quad":
 st.markdown("# 🌍 Global Quad — 50 Countries")
 st.caption("Same GIP model applied to country ETFs. Shows where capital is rotating.")
 if not global_: st.warning("No global data. Refresh."); st.stop()

 gq=global_.get("global_quad","Q3")
 gconf=global_.get("global_conf",0.0)
 gprobs=global_.get("global_probs",{})

 c1,c2=st.columns([1,1.5])
 with c1:
  st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
  st.markdown("### Global Probabilities")
  st.plotly_chart(prob_bar(gprobs,""),use_container_width=True,config={"displayModeBar":False})
 with c2:
  st.markdown("### Country Heatmap")
  heat=[]
  for country, data in global_.get("country_quads",{}).items():
   if isinstance(data, (list, tuple)) and len(data) >= 3:
    etf, quad, conf = data[0], data[1], data[2]
   elif isinstance(data, dict):
    etf, quad, conf = data.get("etf",""), data.get("quad",""), data.get("conf",0)
   else:
    etf, quad, conf = "", "", 0
   heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
  if heat:
   df=pd.DataFrame(heat)
   st.dataframe(df.style.map(lambda v: f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=420,use_container_width=True)
  else:
   st.info("No country quad data available.")

# ══════════════════════════════════════════════════════════════════════════════
# US STOCKS
# ══════════════════════════════════════════════════════════════════════════════
elif page=="📊 US Stocks":
 st.markdown("# 📊 US Stocks — Sectors · Factors · Notable Tickers")
 st.caption("Regime playbook + TRR/LRR + bottleneck badge. Best EV+ first.")
 from config.settings import US_SECTORS, US_FACTORS, TICKER_SECTOR, COMMODITIES, CRYPTO, FOREX_PAIRS, IHSG_UNIVERSE, BONDS, MACRO_PROXIES
 _render_universe("US Sectors", US_SECTORS, prices, btk)
 _render_universe("US Factors", US_FACTORS, prices, btk)

 st.markdown("### Notable Single Stocks (Bottleneck Plays)")
 # Filter: only true single stocks — exclude ETFs, commodities, crypto, forex, bonds, IHSG
 excluded = set(list(US_SECTORS.keys()) + list(US_FACTORS.keys()) + 
               list(COMMODITIES.keys()) + list(CRYPTO.keys()) + 
               list(FOREX_PAIRS.keys()) + list(IHSG_UNIVERSE.keys()) +
               list(BONDS.keys()) + list(MACRO_PROXIES.keys()) +
               ["DX-Y.NYB", "^VIX", "EIDO", "^JKSE"])
 notable={k:v for k,v in TICKER_SECTOR.items() if k not in excluded and k in prices and v != "generic"}
 rows=[]
 for sym, sector in notable.items():
  s=prices.get(sym)
  if s is None: continue
  s=pd.to_numeric(s,errors="coerce").dropna().tail(252)
  if s.empty: continue
  ret3m=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
  badge=_btk_badge(sym, btk)
  rows.append({"Ticker":sym,"Sector":sector.replace("_"," ").title(),"3M":f"{ret3m:+.1%}","Bottleneck":badge})
 if rows:
  df=pd.DataFrame(rows)
  st.markdown(df.to_html(escape=False,index=False),unsafe_allow_html=True)
 else:
  st.info("No notable single stocks loaded. Add tickers to TICKER_SECTOR in config/settings.py")

# ══════════════════════════════════════════════════════════════════════════════
# FOREX
# ══════════════════════════════════════════════════════════════════════════════
elif page=="💱 Forex":
 st.markdown("# 💱 Forex — Regime + Carry + Divergence")
 st.caption("DXY regime + EM carry. DXY bearish = EM relief. DXY bullish = EM pain.")
 from config.settings import FOREX_PAIRS
 _render_universe("Forex Pairs", FOREX_PAIRS, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🛢 Commodities":
 st.markdown("# 🛢 Commodities — Energy · Metals · Agriculture")
 st.caption("Q2/Q3 commodity cycle. Oil = growth proxy. Gold = Q3/Q4 safety.")
 from config.settings import COMMODITIES
 _render_universe("Commodities", COMMODITIES, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page=="₿ Crypto":
 st.markdown("# ₿ Crypto — Macro + On-Chain + Narrative")
 st.caption("Q1/Q2 risk-on. Q3/Q4 risk-off. Watch BTC dominance + DXY correlation.")
 from config.settings import CRYPTO
 _render_universe("Crypto", CRYPTO, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🇮🇩 IHSG":
 st.markdown("# 🇮🇩 IHSG — Indonesia Macro + Foreign Flow + JIIPE")
 st.caption("Indonesia-specific: CKPN cascade, offshore drilling, foreign flow, JIIPE.")
 from config.settings import IHSG_UNIVERSE
 _render_universe("IHSG Universe", IHSG_UNIVERSE, prices, btk, days=252)

 st.markdown("---")
 st.markdown("### 🌍 EM Recovery Signal")
 em_sig = btk.get("em_recovery", {}) if btk else {}
 if em_sig:
  conf = em_sig.get("confidence", 0)
  ec = "#10B981" if conf > 0.6 else "#F59E0B" if conf > 0.4 else "#6B7280"
  st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:12px;border-left:4px solid {ec}'>
<div style='font-size:13px;color:#E8ECF0;font-weight:700'>{em_sig.get('trigger','')}</div>
<div style='font-size:11px;color:#9CA3AF;margin-top:4px'>{em_sig.get('rationale','')}</div>
<div style='font-size:10px;color:{ec};margin-top:6px'>Confidence: {conf:.0%}</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>🎯 Best: {', '.join(em_sig.get('best',[])[:6])}</div>
</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# BOTTLENECK
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🔍 Bottleneck":
 st.markdown("# 🔍 Bottleneck Scanner — Supply Chain + Regime Fit")
 st.caption("Structural scarcity. Level 1 = best. Level 2 = building. Watch = brewing. Avoid = regime trap.")

 if not btk: st.warning("No bottleneck data. Refresh."); st.stop()

 l1=btk.get("level_1",[]); l2=btk.get("level_2",[]); wt=btk.get("watch",[]); av=btk.get("avoid",[])

 s1,s2,s3,s4=st.columns(4)
 for col,lab,val,c in [(s1,"Level 1",len(l1),"#10B981"),(s2,"Level 2",len(l2),"#F59E0B"),
  (s3,"Watch",len(wt),"#6366F1"),(s4,"Avoid",len(av),"#EF4444")]:
  col.markdown(f'<div style="text-align:center"><div style="font-size:28px;font-weight:800;color:{c}">{val}</div><div style="font-size:10px;color:#9CA3AF">{lab}</div></div>',unsafe_allow_html=True)

 def _render_level(level_data, title, color):
  if not level_data: return
  st.markdown(f"### {title}")
  rows=[]
  for c in level_data:
   rows.append({"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),"Trend":c["trend"],
    "Score":c["score"],"EV":c.get("ev","—"),"RS 3M":c.get("rs_3m","—"),
    "Regime Fit":c.get("regime_fit","—"),"Constraint":c.get("constraint","—"),
    "Thesis":c.get("thesis","")[:60],"Catalyst":c.get("catalyst","")[:40],
    "Risk":c.get("risk","")[:40]})
  if rows:
   df=pd.DataFrame(rows)
   st.dataframe(df.style.map(lambda v: f"color:{'#10B981' if v=='uptrend' else '#EF4444' if v=='downtrend' else '#F59E0B'}",subset=["Trend"]),hide_index=True,height=min(len(rows)*35+40,400),use_container_width=True)

 _render_level(l1,"⚡ Level 1 — Best Setups","#10B981")
 _render_level(l2,"📈 Level 2 — Building","#F59E0B")
 _render_level(wt,"👀 Watch — Brewing","#6366F1")
 _render_level(av,"🚫 Avoid — Regime Trap","#EF4444")

 st.markdown("---")
 st.markdown("### 🌍 EM Recovery Signal")
 em_sig = btk.get("em_recovery", {})
 if em_sig:
  conf = em_sig.get("confidence", 0)
  ec = "#10B981" if conf > 0.6 else "#F59E0B" if conf > 0.4 else "#6B7280"
  st.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:12px;border-left:4px solid {ec}'>
<div style='font-size:13px;color:#E8ECF0;font-weight:700'>{em_sig.get('trigger','')}</div>
<div style='font-size:11px;color:#9CA3AF;margin-top:4px'>{em_sig.get('rationale','')}</div>
<div style='font-size:10px;color:{ec};margin-top:6px'>Confidence: {conf:.0%}</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>🎯 Best: {', '.join(em_sig.get('best',[])[:6])}</div>
</div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page=="📖 Narratives":
 st.markdown("# 📖 Narratives — Adaptive · Reactive · Proactive")
 st.caption("Active = confirmed. Building = early traction. Brewing = pre-consensus. Fading = exit.")

 if not narr: st.warning("No narrative data. Refresh."); st.stop()

 active=narr.get("active",[]); building=narr.get("building",[]); brewing=narr.get("brewing",[]); fading=narr.get("fading",[])

 s1,s2,s3,s4=st.columns(4)
 for col,lab,val,c in [(s1,"Active",len(active),"#10B981"),(s2,"Building",len(building),"#F59E0B"),
  (s3,"Brewing",len(brewing),"#6366F1"),(s4,"Fading",len(fading),"#EF4444")]:
  col.markdown(f'<div style="text-align:center"><div style="font-size:28px;font-weight:800;color:{c}">{val}</div><div style="font-size:10px;color:#9CA3AF">{lab}</div></div>',unsafe_allow_html=True)

 def _render_narrative_list(narr_list, title, color):
  if not narr_list: return
  st.markdown(f"### {title}")
  for n in narr_list:
   with st.expander(f"**{n.get('name','')}** — Strength: {n.get('strength',0):.0%} | Regime Fit: {n.get('regime_fit',0):.0%}", expanded=False):
    st.markdown(f"**Thesis:** {n.get('thesis','')}")
    st.markdown(f"**Catalyst:** {n.get('catalyst','')}")
    st.markdown(f"**Risk:** {n.get('risk','')}")
    if n.get("beneficiary_tickers"):
     st.markdown(f"**Beneficiaries:** {', '.join(n['beneficiary_tickers'])}")
    if n.get("fade_tickers"):
     st.markdown(f"**Fade:** {', '.join(n['fade_tickers'])}")
    if n.get("spillover"):
     st.markdown(f"**Spillover:** {n['spillover']}")

 _render_narrative_list(active,"🟢 Active — Confirmed","#10B981")
 _render_narrative_list(building,"🟡 Building — Early Traction","#F59E0B")
 _render_narrative_list(brewing,"🔵 Brewing — Pre-Consensus","#6366F1")
 _render_narrative_list(fading,"🔴 Fading — Exit","#EF4444")

 st.markdown("---")
 st.markdown("### 🔥 Ignition Detection")
 ignition = narr.get("ignition",{})
 if ignition and ignition.get("detected"):
  st.success(f"🚨 IGNITION DETECTED: {ignition.get('dominant_narrative','')} — Strength: {ignition.get('strength',0):.0%}")
  st.markdown(f"**Tickers:** {', '.join(ignition.get('tickers',[])[:10])}")
  st.markdown(f"**Rationale:** {ignition.get('rationale','')}")
 else:
  st.info("No ignition detected. Narratives not yet reaching critical mass.")

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🏥 Health":
 st.markdown("# 🏥 Market Health — VIX · Breadth · Fear & Greed")
 st.caption("VIX bucket + crash meter + sector breadth + checklist.")

 if not health: st.warning("No health data. Refresh."); st.stop()

 vix_bucket = health.get("vix_bucket") or "unknown"
 vix_bucket = str(vix_bucket).lower()
 vix_color = {"investable":"#10B981","chop":"#F59E0B","defensive":"#EF4444"}.get(vix_bucket,"#6B7280")
 st.markdown(f"""<div style='background:{vix_color}22;border-left:4px solid {vix_color};padding:12px;border-radius:8px;margin-bottom:12px'>
<div style='font-size:16px;font-weight:800;color:{vix_color}'>VIX BUCKET: {vix_bucket.upper()}</div>
<div style='font-size:12px;color:#E8ECF0;margin-top:4px'>{health.get('vix_rationale','No rationale available')}</div>
</div>""",unsafe_allow_html=True)

 crash_meter = health.get("crash_meter",{})
 if crash_meter:
  st.markdown("### Crash Meter")
  for k,v in crash_meter.items():
   col = "#10B981" if v < 0.3 else "#F59E0B" if v < 0.6 else "#EF4444"
   st.progress(v, text=f"{k.replace('_',' ').title()}: {v:.0%}")

 breadth = health.get("breadth",{})
 if breadth:
  st.markdown("### Sector Breadth")
  for sector, score in breadth.items():
   col = "#10B981" if score > 0.6 else "#F59E0B" if score > 0.4 else "#EF4444"
   st.progress(score, text=f"{sector}: {score:.0%}")

 checklist = health.get("checklist",{})
 if checklist:
  st.markdown("### Health Checklist")
  for item, status in checklist.items():
   icon = "✅" if status else "❌"
   col = "#10B981" if status else "#EF4444"
   st.markdown(f'<span style="color:{col}">{icon}</span> {item}', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🔮 Scenarios":
 st.markdown("# 🔮 Adaptive Scenarios — Base · Alt · Risk · Tail")
 st.caption("4 scenarios with probability, confirmation score, and EM-specific implications.")

 if not scen: st.warning("No scenario data. Refresh."); st.stop()

 base=scen.get("base_case")
 alt=scen.get("alt_case")
 risk=scen.get("risk_case")
 tail=scen.get("tail_case")

 _render_scenario(base, "BASE", "#10B981", "🎯")
 _render_scenario(alt, "ALT", "#F59E0B", "🔄")
 _render_scenario(risk, "RISK", "#EF4444", "⚠️")
 _render_scenario(tail, "TAIL", "#6366F1", "📌")

 st.markdown("---")
 st.markdown("### 🧠 Scenario Logic")
 st.caption("How scenarios are generated:")
 st.markdown("""
1. **Structural Quad** (quarterly) sets the base case
2. **Monthly Quad** (weather) creates the alt case if divergent
3. **Flip Hazard** drives the risk case
4. **Data Coverage** quality determines the tail case
5. **Confirmation Score** = how many macro signals align with the scenario
""")

# ══════════════════════════════════════════════════════════════════════════════
# EARLY DISCOVERY — Pre-Consensus Alpha (NEW v14)
# ══════════════════════════════════════════════════════════════════════════════
elif page=="🔮 Early Discovery":
 st.markdown("# 🔮 Early Discovery — Pre-Consensus Alpha")
 st.caption("Auto-discovered opportunities BEFORE they become consensus. Source: price clustering + news NLP + SEC EDGAR + supply chain graph. Updated every snapshot.")

 if not auto_disc or not auto_disc.get("candidates"):
  st.info("🔍 No early discoveries yet. Run a fresh snapshot (⚡ Force) to trigger autonomous discovery.")
  st.stop()

 candidates = auto_disc.get("candidates",[])
 meta = auto_disc.get("meta",{})

 # Summary cards
 s1,s2,s3,s4,s5 = st.columns(5)
 total = len(candidates)
 bottlenecks = len([c for c in candidates if c.get("category")=="bottleneck"])
 narratives = len([c for c in candidates if c.get("category")=="narrative"])
 transitions = len([c for c in candidates if c.get("category")=="transition"])
 brewing = len([c for c in candidates if c.get("stage")=="brewing"])

 s1.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center'>
<div style='font-size:24px;font-weight:800;color:#E8ECF0'>{total}</div>
<div style='font-size:10px;color:#9CA3AF'>TOTAL DISCOVERED</div>
</div>""", unsafe_allow_html=True)
 s2.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center;border-top:3px solid #EF4444'>
<div style='font-size:24px;font-weight:800;color:#EF4444'>{bottlenecks}</div>
<div style='font-size:10px;color:#9CA3AF'>BOTTLENECKS</div>
</div>""", unsafe_allow_html=True)
 s3.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center;border-top:3px solid #6366F1'>
<div style='font-size:24px;font-weight:800;color:#6366F1'>{narratives}</div>
<div style='font-size:10px;color:#9CA3AF'>NARRATIVES</div>
</div>""", unsafe_allow_html=True)
 s4.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center;border-top:3px solid #F59E0B'>
<div style='font-size:24px;font-weight:800;color:#F59E0B'>{transitions}</div>
<div style='font-size:10px;color:#9CA3AF'>TRANSITIONS</div>
</div>""", unsafe_allow_html=True)
 s5.markdown(f"""<div style='background:#1F2937;border-radius:8px;padding:10px;text-align:center;border-top:3px solid #6B7280'>
<div style='font-size:24px;font-weight:800;color:#6B7280'>{brewing}</div>
<div style='font-size:10px;color:#9CA3AF'>BREWING (EARLY)</div>
</div>""", unsafe_allow_html=True)

 st.markdown(f"<div style='text-align:right;font-size:10px;color:#6B7280'>Build time: {meta.get('build_time_s',0)}s | Clusters: {meta.get('clusters_found',0)} | News: {meta.get('news_analyzed',0)} | Graph: {meta.get('graph_bottlenecks',0)}</div>", unsafe_allow_html=True)

 # Filters
 st.markdown("---")
 fc1, fc2, fc3 = st.columns(3)
 with fc1:
  stage_filter = st.multiselect("Stage", ["brewing","building","active"], default=["brewing","building"])
 with fc2:
  cat_filter = st.multiselect("Category", ["bottleneck","narrative","transition"], default=["bottleneck","narrative"])
 with fc3:
  conf_min = st.slider("Min Confidence", 0.0, 1.0, 0.45, 0.05)

 filtered = [c for c in candidates
  if c.get("stage") in stage_filter
  and c.get("category") in cat_filter
  and c.get("confidence",0) >= conf_min]

 # Sort: brewing first, then by confidence
 stage_order = {"brewing":0, "building":1, "active":2}
 filtered.sort(key=lambda x: (stage_order.get(x.get("stage"),3), -x.get("confidence",0)))

 # PRE-CONSENSIS HIGHLIGHT
 pre_con = [c for c in filtered if c.get("stage")=="brewing" and c.get("confidence",0) >= 0.5]
 if pre_con:
  st.markdown("### ⚡ PRE-CONSENSIS ALERTS — Not yet mainstream")
  for c in pre_con[:3]:
   cat_color = {"bottleneck":"#EF4444","narrative":"#6366F1","transition":"#F59E0B"}.get(c.get("category"),"#6B7280")
   st.markdown(f"""<div class='precon-card'>
<div style='display:flex;justify-content:space-between;align-items:center'>
<span style='font-size:14px;font-weight:700;color:#E8ECF0'>{c.get('name','')}</span>
<span style='background:{cat_color};color:white;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:bold'>{c.get('category','').upper()}</span>
</div>
<div style='font-size:12px;color:#9CA3AF;margin-top:6px'>{c.get('thesis','')}</div>
<div style='display:flex;gap:12px;margin-top:8px;font-size:11px;color:#6B7280'>
<span>🔥 Confidence: <b style='color:#F59E0B'>{c.get('confidence',0):.0%}</b></span>
<span>📈 Regime Fit: {c.get('regime_fit',0):.0%}</span>
<span>🎯 Beneficiaries: {', '.join(c.get('beneficiary_tickers',[])[:5])}</span>
</div>
<div style='font-size:10px;color:#6B7280;margin-top:4px'>Source: {' · '.join(c.get('source_signals',[]))}</div>
</div>""", unsafe_allow_html=True)

 # FULL TABLE
 st.markdown("### 📋 All Discoveries")
 if filtered:
  rows = []
  for c in filtered:
   stage = c.get("stage","—")
   badge_class = {"brewing":"brewing-badge","building":"building-badge","active":"active-badge"}.get(stage,"brewing-badge")
   cat_emoji = {"bottleneck":"🔴","narrative":"🔵","transition":"🟡"}.get(c.get("category"),"⚪")
   rows.append({
    "Name": c.get("name",""),
    "Stage": f"<span class='{badge_class}'>{stage.upper()}</span>",
    "Category": f"{cat_emoji} {c.get('category','').title()}",
    "Confidence": f"{c.get('confidence',0):.0%}",
    "Regime Fit": f"{c.get('regime_fit',0):.0%}",
    "Beneficiaries": ", ".join(c.get("beneficiary_tickers",[])[:4]),
    "Thesis (short)": c.get("thesis","")[:90] + "..." if len(c.get("thesis","")) > 90 else c.get("thesis",""),
    "Confirmation": c.get("confirmation_signal","")[:60],
    "Source": " · ".join(c.get("source_signals",[])),
   })
  df = pd.DataFrame(rows)
  st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
 else:
  st.info("No discoveries match your filters. Try lowering confidence or adding stages.")

 # BOTTLENECK DEEP DIVE
 st.markdown("---")
 st.markdown("### 🔴 Bottleneck Deep Dive")
 btk_cands = [c for c in candidates if c.get("category")=="bottleneck"]
 if btk_cands:
  for c in btk_cands[:5]:
   with st.expander(f"🔴 {c.get('name','')} — {c.get('stage','').upper()} | Conf: {c.get('confidence',0):.0%}", expanded=(c.get("stage")=="brewing")):
    c1, c2 = st.columns([2,1])
    with c1:
     st.markdown(f"**Thesis:** {c.get('thesis','')}")
     st.markdown(f"**Confirmation Signal:** {c.get('confirmation_signal','')}")
     st.markdown(f"**Invalidators:** {' · '.join(c.get('invalidators',[]))}")
    with c2:
     st.markdown(f"**Confidence:** {c.get('confidence',0):.0%}")
     st.markdown(f"**Regime Fit:** {c.get('regime_fit',0):.0%}")
     st.markdown(f"**Pump Risk:** {c.get('pump_risk',0):.0%}")
     if c.get("forward_return_expectation"):
      fre = c["forward_return_expectation"]
      st.markdown(f"**Expected 3M Return:** {fre.get('expected_3m','—')}")
     if c.get("transition_forecast"):
      tf = c["transition_forecast"]
      st.markdown(f"**Predicted Quad:** {tf.get('predicted_quad','—')} ({tf.get('prediction_confidence','—')})")
 else:
  st.info("No bottleneck discoveries yet. Run Force Refresh to scan.")

 # NARRATIVE DEEP DIVE
 st.markdown("---")
 st.markdown("### 🔵 Narrative Deep Dive")
 narr_cands = [c for c in candidates if c.get("category")=="narrative"]
 if narr_cands:
  for c in narr_cands[:5]:
   with st.expander(f"🔵 {c.get('name','')} — {c.get('stage','').upper()} | Conf: {c.get('confidence',0):.0%}", expanded=(c.get("stage")=="brewing")):
    st.markdown(f"**Thesis:** {c.get('thesis','')}")
    st.markdown(f"**Beneficiaries:** {', '.join(c.get('beneficiary_tickers',[]))}")
    st.markdown(f"**Confirmation:** {c.get('confirmation_signal','')}")
    st.markdown(f"**Invalidators:** {' · '.join(c.get('invalidators',[]))}")
 else:
  st.info("No narrative discoveries yet. Price clusters may not have crossed news validation threshold.")

 # TRANSITION FORECAST
 st.markdown("---")
 st.markdown("### 🟡 Transition Forecast")
 trans_cands = [c for c in candidates if c.get("category")=="transition"]
 if trans_cands:
  for c in trans_cands[:3]:
   with st.expander(f"🟡 {c.get('name','')} — Conf: {c.get('confidence',0):.0%}", expanded=True):
    st.markdown(f"**Thesis:** {c.get('thesis','')}")
    if c.get("transition_forecast"):
     tf = c["transition_forecast"]
     st.markdown("**Probability Distribution:**")
     for q, p in tf.get("probability_distribution",{}).items():
      st.markdown(f"- {q}: {p:.0%}")
    st.markdown(f"**Expected Return:** {c.get('forward_return_expectation',{})}")
 else:
  st.info("No transition forecasts. Structural and monthly quads may be aligned.")

 # FEEDBACK LOOP STATUS
 if fb_eval:
  st.markdown("---")
  st.markdown("### 🧠 Feedback Loop Status")
  st.caption("System tracks discoveries for 6 months. Winners auto-promoted to permanent lists. Losers auto-demoted.")
  c1, c2, c3 = st.columns(3)
  c1.metric("Evaluated", fb_eval.get("evaluated",0))
  c2.metric("Promoted ✅", fb_eval.get("promoted",0), "added to permanent")
  c3.metric("Demoted ❌", fb_eval.get("demoted",0), "removed")

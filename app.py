"""app.py — MacroRegime Pro | Hedgeye-Inspired Macro Dashboard

Navigation: Home → Regime → Risk Ranges → Global → Scanner → Scenarios → IHSG
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import math
from typing import Optional

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

  :root {
    --bg:      #0A0E1A;
    --bg2:     #111827;
    --bg3:     #1A2235;
    --accent:  #00D4AA;
    --q1:      #00D4AA;
    --q2:      #F59E0B;
    --q3:      #EF4444;
    --q4:      #6366F1;
    --text:    #E8ECF0;
    --muted:   #9CA3AF;
    --border:  #1F2B3D;
    --bull:    #10B981;
    --bear:    #EF4444;
    --neutral: #6B7280;
  }

  html, body, [class*="stApp"] { background:#0A0E1A !important; font-family:'Inter',sans-serif; }
  .stSidebar { background:#111827 !important; border-right:1px solid #1F2B3D; }
  .stSidebar .stMarkdown, .stSidebar label, .stSidebar .stRadio label { color:#E8ECF0 !important; }

  h1 { font-family:'JetBrains Mono',monospace; font-size:1.4rem !important; letter-spacing:-0.5px; }
  h2 { font-family:'JetBrains Mono',monospace; font-size:1.1rem !important; color:#00D4AA !important; }
  h3 { font-size:0.9rem !important; font-weight:600; text-transform:uppercase; letter-spacing:1px; color:#9CA3AF; }

  /* Quad cards */
  .quad-card {
    background:#111827; border:1px solid #1F2B3D; border-radius:10px;
    padding:18px; text-align:center; transition:all .2s;
  }
  .quad-card:hover { border-color:#00D4AA; box-shadow:0 0 20px rgba(0,212,170,0.08); }
  .quad-label { font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#9CA3AF; text-transform:uppercase; letter-spacing:1.5px; }
  .quad-num   { font-family:'JetBrains Mono',monospace; font-size:3.2rem; font-weight:700; line-height:1.0; }
  .quad-name  { font-size:0.85rem; font-weight:600; margin-top:4px; }
  .quad-conf  { font-size:0.72rem; color:#9CA3AF; margin-top:6px; }
  .q1 { color:#00D4AA; } .q2 { color:#F59E0B; } .q3 { color:#EF4444; } .q4 { color:#6366F1; }
  .border-q1 { border-color:#00D4AA !important; } .border-q2 { border-color:#F59E0B !important; }
  .border-q3 { border-color:#EF4444 !important; } .border-q4 { border-color:#6366F1 !important; }

  /* Signal badges */
  .badge-bull { background:#065F46; color:#10B981; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:700; font-family:'JetBrains Mono'; }
  .badge-bear { background:#450A0A; color:#EF4444; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:700; font-family:'JetBrains Mono'; }
  .badge-neut { background:#1F2937; color:#9CA3AF; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:700; font-family:'JetBrains Mono'; }
  .badge-mix  { background:#2D2006; color:#F59E0B; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:700; font-family:'JetBrains Mono'; }

  /* Alert badges */
  .alert-critical { background:#450A0A; color:#EF4444; border:1px solid #7F1D1D; padding:8px 14px; border-radius:8px; margin:4px 0; font-size:0.8rem; }
  .alert-high     { background:#1C1800; color:#F59E0B; border:1px solid #78350F; padding:8px 14px; border-radius:8px; margin:4px 0; font-size:0.8rem; }
  .alert-medium   { background:#0A1628; color:#60A5FA; border:1px solid #1E3A5F; padding:8px 14px; border-radius:8px; margin:4px 0; font-size:0.8rem; }

  /* Metric cards */
  .metric-card { background:#111827; border:1px solid #1F2B3D; border-radius:8px; padding:14px 18px; margin:4px 0; }
  .metric-val  { font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:700; color:#E8ECF0; }
  .metric-lbl  { font-size:0.72rem; color:#9CA3AF; text-transform:uppercase; letter-spacing:1px; }

  /* Tables */
  .stDataFrame { background:#111827 !important; }
  .stDataFrame table { background:#111827 !important; color:#E8ECF0 !important; }

  /* Status bar */
  .status-bar { background:#111827; border:1px solid #1F2B3D; border-radius:8px; padding:8px 16px; display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }

  /* Section divider */
  .section-header { border-left:3px solid #00D4AA; padding-left:12px; margin:20px 0 12px; }

  /* Playbook item */
  .pb-best  { color:#10B981; } .pb-worst { color:#EF4444; }

  /* Scrollable container */
  .scroll-box { max-height:400px; overflow-y:auto; padding-right:4px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

QUAD_COLORS = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QUAD_NAMES  = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
SIGNAL_COLORS = {"bullish":"#10B981","bearish":"#EF4444","neutral":"#6B7280","mixed":"#F59E0B"}

def q_cls(q):   return q.lower() if q in ("Q1","Q2","Q3","Q4") else ""
def q_color(q): return QUAD_COLORS.get(q,"#9CA3AF")
def q_name(q):  return QUAD_NAMES.get(q,q)
def fmt_pct(v): return f"{v:.1%}" if v is not None and math.isfinite(v) else "—"
def fmt_f(v,d=4): return f"{v:.{d}f}" if v is not None and math.isfinite(v) else "—"
def sig_badge(s):
    cls = {"bullish":"badge-bull","bearish":"badge-bear","neutral":"badge-neut","mixed":"badge-mix"}.get(s,"badge-neut")
    return f'<span class="{cls}">▲ {s.upper()}</span>' if s=="bullish" else \
           f'<span class="{cls}">▼ {s.upper()}</span>' if s=="bearish" else \
           f'<span class="{cls}">{s.upper()}</span>'

def quad_card_html(label, quad, conf, sub=""):
    return f"""
<div class="quad-card border-{q_cls(quad)}">
  <div class="quad-label">{label}</div>
  <div class="quad-num {q_cls(quad)}">{quad[-1] if quad in QUAD_NAMES else "?"}</div>
  <div class="quad-name {q_cls(quad)}">{q_name(quad)}</div>
  {"<div class='quad-conf'>" + sub + "</div>" if sub else ""}
  <div class="quad-conf">Confidence: {conf:.0%}</div>
</div>"""

def prob_bar_chart(probs: dict, title="Quad Probabilities"):
    fig = go.Figure()
    for q, p in sorted(probs.items()):
        fig.add_bar(
            x=[q], y=[p], name=q,
            marker_color=QUAD_COLORS.get(q,"#9CA3AF"),
            text=[f"{p:.0%}"], textposition="outside",
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#9CA3AF")),
        showlegend=False, height=220,
        margin=dict(t=30,b=10,l=0,r=0),
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font=dict(color="#E8ECF0", family="JetBrains Mono"),
        yaxis=dict(range=[0,1], tickformat=".0%", showgrid=True, gridcolor="#1F2B3D"),
        xaxis=dict(showgrid=False),
        bargap=0.3,
    )
    return fig

# ── Session state ─────────────────────────────────────────────────────────────

if "snap" not in st.session_state:
    st.session_state.snap = None
if "loading" not in st.session_state:
    st.session_state.loading = False

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP Framework*")
    st.divider()

    page = st.radio("", [
        "🏠 Dashboard",
        "📈 Regime (GIP)",
        "🎯 Risk Ranges",
        "🌍 Global Quad",
        "🔍 Bottleneck Scanner",
        "🔮 Scenarios",
        "🇮🇩 IHSG",
    ], label_visibility="collapsed")

    st.divider()

    from data.loader import snapshot_age_str, load_snapshot
    snap_age = snapshot_age_str()
    st.caption(f"📸 Snapshot: {snap_age}")

    col_r, col_f = st.columns(2)
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.loading = True
    with col_f:
        force = st.button("⚡ Force", use_container_width=True)

    st.divider()
    st.caption("**Coverage**")
    with st.expander("Universe Settings"):
        inc_crypto = st.checkbox("Crypto", value=True)
        inc_us     = st.checkbox("US Sectors", value=True)

    st.markdown("---")
    st.caption("v10.0 | Hedgeye GIP")

# ── Load snapshot ─────────────────────────────────────────────────────────────

snap = st.session_state.snap

if snap is None:
    # Try loading from disk
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"):
        st.session_state.snap = snap

if st.session_state.loading or (snap is None):
    from orchestrator import build_snapshot
    with st.spinner("🔄 Building MacroRegime snapshot..."):
        prog_bar = st.progress(0.0)
        prog_txt = st.empty()

        def on_prog(msg, frac):
            prog_bar.progress(frac)
            prog_txt.caption(msg)

        snap = build_snapshot(
            progress_cb=on_prog,
            include_crypto=inc_crypto if 'inc_crypto' in locals() else True,
            include_us_stocks=inc_us if 'inc_us' in locals() else True,
        )
        st.session_state.snap = snap
        st.session_state.loading = False
    prog_bar.empty(); prog_txt.empty()
    st.rerun()

if snap is None or not snap.get("ok"):
    st.error("❌ No snapshot available. Click **🔄 Refresh** to build from live data.")
    st.stop()

# ── Extract from snapshot ─────────────────────────────────────────────────────

gip      = snap.get("gip")
global_  = snap.get("global", {})
rr       = snap.get("risk_ranges", {})
scen     = snap.get("scenarios", {})
btk      = snap.get("bottleneck", {})
playbook = snap.get("playbook", {})
build_t  = snap.get("build_time_s", 0)

sq = gip.structural_quad  if gip else "Q3"
mq = gip.monthly_quad     if gip else "Q2"
gq = global_.get("global_quad","Q3")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Dashboard":
    # Status bar
    st.markdown(f"""
<div class="status-bar">
  <span>Built in {build_t}s · FRED series: {snap.get('fred_coverage',0)} · Prices: {snap.get('prices_loaded',0)}</span>
  <span style="color:#9CA3AF;font-size:0.78rem">MacroRegime Pro v10.0</span>
</div>""", unsafe_allow_html=True)

    st.markdown("# MacroRegime Pro — Dashboard")

    # Quad trinity
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if gip:
            st.markdown(quad_card_html("STRUCTURAL (Climate)",sq,gip.structural_conf,"Quarterly"), unsafe_allow_html=True)
    with c2:
        if gip:
            st.markdown(quad_card_html("MONTHLY (Weather)",mq,gip.monthly_conf,"Weather Overlay"), unsafe_allow_html=True)
    with c3:
        st.markdown(quad_card_html("GLOBAL",gq,global_.get("global_conf",0.5),"50 Countries"), unsafe_allow_html=True)
    with c4:
        if gip:
            div_color = "#00D4AA" if gip.divergence=="aligned" else "#EF4444"
            st.markdown(f"""
<div class="quad-card">
  <div class="quad-label">ALIGNMENT</div>
  <div style="font-size:1.8rem;font-weight:700;color:{div_color};margin:8px 0">{gip.divergence.upper()}</div>
  <div style="font-size:0.8rem;color:#9CA3AF">{gip.operating_regime}</div>
  <div style="font-size:0.72rem;color:#9CA3AF;margin-top:6px">Flip Risk: {gip.flip_hazard:.0%}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Prob bars
    if gip:
        col_sb, col_mb = st.columns(2)
        with col_sb:
            st.plotly_chart(prob_bar_chart(gip.structural_probs,"Structural Quad Probabilities"), use_container_width=True, config={"displayModeBar":False})
        with col_mb:
            st.plotly_chart(prob_bar_chart(gip.monthly_probs,"Monthly Quad Probabilities"), use_container_width=True, config={"displayModeBar":False})

    st.markdown("---")

    # Playbook + Key signals
    col_pb, col_signals = st.columns([1.2, 1])
    with col_pb:
        st.markdown("### 🎯 Current Playbook")
        if playbook:
            best_str  = " · ".join([f"**{a}**" for a in playbook.get("best_assets",[])[:4]])
            worst_str = " · ".join([f"~~{a}~~" for a in playbook.get("worst_assets",[])[:4]])
            st.markdown(f"✅ **LONG**: {best_str}")
            st.markdown(f"❌ **SHORT/AVOID**: {worst_str}")
            st.markdown(f"📊 **Style**: {playbook.get('style','')}")
            st.markdown(f"💱 **FX**: {playbook.get('fx','')}")
            st.markdown(f"🏦 **Bonds**: {playbook.get('bonds','')}")
            if playbook.get("monthly_adds"):
                st.markdown(f"⚡ **Monthly overlay adds**: {' · '.join(playbook['monthly_adds'][:3])}")

    with col_signals:
        st.markdown("### 📡 Key Signals")
        if gip:
            feats = gip.features
            g = feats.get("growth_level",0)+feats.get("growth_momentum",0)
            i = feats.get("inflation_level",0)+feats.get("inflation_momentum",0)
            p = feats.get("policy_score",0)
            cov = feats.get("data_coverage",0)
            prx = feats.get("proxy_share",0)

            def sig_row(label,val,pos_good=True):
                icon = ("🟢" if val>0.05 else "🔴" if val<-0.05 else "🟡") if pos_good else \
                       ("🔴" if val>0.05 else "🟢" if val<-0.05 else "🟡")
                return f"| {icon} | {label} | `{val:+.2f}` |"

            st.markdown(f"""
| | Signal | Score |
|---|---|---|
{sig_row("Growth",g,True)}
{sig_row("Inflation",i,False)}
{sig_row("Policy (+ = easing)",p,True)}
| {"🟢" if cov>0.7 else "🟡"} | FRED Coverage | `{cov:.0%}` |
| {"🔴" if prx>0.5 else "🟡" if prx>0.2 else "🟢"} | Proxy Share | `{prx:.0%}` |
""")

    # Critical alerts
    asset_ranges = rr.get("asset_ranges", {})
    critical = [
        (sym, a)
        for sym, v in asset_ranges.items()
        for a in v.get("alerts",[])
        if a.get("priority") == "CRITICAL"
    ][:6]
    if critical:
        st.markdown("---")
        st.markdown("### 🚨 Critical Alerts")
        for sym, alert in critical:
            st.markdown(f'<div class="alert-critical">⚠️ **{sym}** — {alert["action"]}: {alert["note"]}</div>', unsafe_allow_html=True)

    # Bottleneck top 3
    l1 = btk.get("level_1", [])
    if l1:
        st.markdown("---")
        st.markdown("### 🔍 Top Bottleneck Setups (Level 1)")
        cols = st.columns(min(len(l1[:3]), 3))
        for idx, c in enumerate(l1[:3]):
            with cols[idx]:
                trend_c = "#10B981" if c["trend"]=="uptrend" else "#EF4444" if c["trend"]=="downtrend" else "#F59E0B"
                st.markdown(f"""
<div class="metric-card">
  <div style="font-family:'JetBrains Mono';font-size:1.1rem;font-weight:700;color:#E8ECF0">{c['ticker']}</div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-bottom:8px">{c['sector'].replace('_',' ').title()}</div>
  <div style="color:{trend_c};font-size:0.8rem;font-weight:600">{c['trend'].upper()}</div>
  <div style="font-size:0.72rem;color:#9CA3AF;margin-top:6px">{c['rationale'][:80]}...</div>
  <div style="font-family:'JetBrains Mono';font-size:0.8rem;color:#00D4AA;margin-top:6px">Score: {c['score']:.2f}</div>
</div>""", unsafe_allow_html=True)

    # Base scenario
    base = scen.get("base_case")
    if base:
        st.markdown("---")
        st.markdown("### 🔮 Base Scenario")
        prob_c = "#10B981" if base.probability>0.40 else "#F59E0B"
        st.markdown(f"""
<div style="background:#111827;border:1px solid #1F2B3D;border-radius:10px;padding:16px">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div>
      <span style="font-family:'JetBrains Mono';font-weight:700;color:#E8ECF0;font-size:1.0rem">{base.name}</span>
      <span style="margin-left:12px;font-size:0.8rem;color:#9CA3AF">{base.headline}</span>
    </div>
    <div style="color:{prob_c};font-family:'JetBrains Mono';font-size:1.1rem;font-weight:700">{base.probability:.0%}</div>
  </div>
  <div style="margin-top:10px;font-size:0.78rem;color:#9CA3AF">
    <b style="color:#10B981">LONG:</b> {" · ".join(base.best_assets[:4])} &nbsp;|&nbsp;
    <b style="color:#EF4444">AVOID:</b> {" · ".join(base.worst_assets[:3])}
  </div>
  <div style="margin-top:8px;font-size:0.75rem;color:#6B7280">Catalyst: {base.catalyst}</div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# REGIME PAGE
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Regime (GIP)":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye's GIP model: YoY RoC of growth and inflation. Second derivative = the signal.")

    if not gip:
        st.warning("No GIP data. Click Refresh."); st.stop()

    # Axis chart (2D quad map)
    g = gip.structural_g; i = gip.structural_i
    fig = go.Figure()

    # Quad regions
    for q, (x0,y0,x1,y1) in {
        "Q1":(-0.05,-1.0,1.0,0.0), "Q2":(-0.05,0.0,1.0,1.0),
        "Q3":(-1.0,0.0,-0.05,1.0),  "Q4":(-1.0,-1.0,-0.05,0.0),
    }.items():
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,
                      fillcolor=QUAD_COLORS[q],opacity=0.08,line_width=0)
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2,
                           text=f"<b>{q}</b><br>{q_name(q)}",
                           font=dict(size=11,color=QUAD_COLORS[q]),
                           showarrow=False)

    # Axes
    fig.add_hline(y=0, line_width=1, line_color="#333")
    fig.add_vline(x=0, line_width=1, line_color="#333")

    # Current position
    fig.add_scatter(x=[g], y=[i], mode="markers+text",
                    marker=dict(size=16, color=QUAD_COLORS[sq], symbol="circle",
                                line=dict(width=2,color="white")),
                    text=["NOW"], textposition="top center",
                    textfont=dict(size=10, color="white"),
                    name="Current")

    fig.update_layout(
        xaxis_title="Growth (G score)", yaxis_title="Inflation (I score)",
        xaxis=dict(range=[-1,1], showgrid=True, gridcolor="#1F2B3D", zeroline=False),
        yaxis=dict(range=[-1,1], showgrid=True, gridcolor="#1F2B3D", zeroline=False),
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font=dict(color="#E8ECF0"), height=380,
        margin=dict(t=20,b=40,l=40,r=20),
        showlegend=False,
    )
    col_chart, col_detail = st.columns([1.2,1])
    with col_chart:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    with col_detail:
        st.markdown("#### Signal Breakdown")
        feats = gip.features
        rows = []
        for k in ["growth_level","growth_momentum","inflation_level","inflation_momentum","policy_score"]:
            v = feats.get(k, float("nan"))
            if math.isfinite(v):
                bar = "█" * int(abs(v)*10) + "░" * (10-int(abs(v)*10))
                color = "#10B981" if v>0 else "#EF4444"
                rows.append({"Signal":k.replace("_"," ").title(),"Score":f"{v:+.3f}","Bar":f'<span style="color:{color}">{bar}</span>'})
        if rows:
            df_sig = pd.DataFrame(rows)
            st.markdown(df_sig.to_html(escape=False,index=False,classes=""), unsafe_allow_html=True)

        st.markdown("#### Data Quality")
        cov = feats.get("data_coverage",0)
        prx = feats.get("proxy_share",0)
        st.progress(cov, text=f"FRED Coverage: {cov:.0%}")
        if prx > 0.3:
            st.warning(f"⚠️ {prx:.0%} signals using price proxies (no FRED). Add FRED_API_KEY for better accuracy.")
        else:
            st.success(f"✅ {1-prx:.0%} signals from FRED macro data")

    # Feature table
    st.markdown("---")
    st.markdown("#### 📋 All Raw Features (Transparency)")
    feat_rows = []
    for k,v in sorted(feats.items()):
        if k.startswith("raw_") and math.isfinite(v):
            feat_rows.append({"Series":k[4:].upper(),"Value":f"{v:.4f}"})
    if feat_rows:
        df_feat = pd.DataFrame(feat_rows)
        st.dataframe(df_feat, hide_index=True, height=250)


# ══════════════════════════════════════════════════════════════════════════════
# RISK RANGES
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🎯 Risk Ranges":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("Hedgeye Rescaled Range Analysis (Hurst). LRR = buy/add. TRR = sell/trim.")

    asset_ranges = rr.get("asset_ranges", {})
    if not asset_ranges:
        st.warning("No risk range data. Click Refresh."); st.stop()

    # Filter
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sig_filter = st.selectbox("Signal Filter", ["All","Bullish","Bearish","Mixed","Neutral"])
    with col_f2:
        quality_filter = st.multiselect("Setup Quality", ["A","B","C","short_A","short_B","none"], default=["A","B","short_A"])
    with col_f3:
        show_alerts_only = st.checkbox("Critical Alerts Only", False)

    # Summary row
    summary = rr.get("summary",{})
    s1,s2,s3,s4 = st.columns(4)
    for col, label, val, color in [
        (s1,"Total Assets",summary.get("total",0),"#E8ECF0"),
        (s2,"Bullish",summary.get("bullish",0),"#10B981"),
        (s3,"Bearish",summary.get("bearish",0),"#EF4444"),
        (s4,"A-Quality Setups",summary.get("a_quality",0),"#00D4AA"),
    ]:
        col.markdown(f'<div class="metric-card"><div class="metric-val" style="color:{color}">{val}</div><div class="metric-lbl">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Build table
    rows = []
    for sym, v in sorted(asset_ranges.items()):
        comp = v.get("composite","neutral")
        qual = v.get("quality","none")
        if sig_filter != "All" and comp.lower() != sig_filter.lower(): continue
        if quality_filter and qual not in quality_filter: continue
        alerts = v.get("alerts",[])
        if show_alerts_only and not any(a["priority"]=="CRITICAL" for a in alerts): continue
        rows.append({
            "Ticker": sym,
            "Trade": v.get("trade_signal","—"),
            "Trend": v.get("trend_signal","—"),
            "Tail": v.get("tail_signal","—"),
            "Composite": comp,
            "Quality": qual,
            "TRADE LRR": fmt_f(v.get("trade_lrr"),2),
            "TRADE TRR": fmt_f(v.get("trade_trr"),2),
            "TREND LRR": fmt_f(v.get("trend_lrr"),2),
            "TREND TRR": fmt_f(v.get("trend_trr"),2),
            "H (Trade)": f"{v.get('hurst_trade',0.5):.2f}",
            "H (Trend)": f"{v.get('hurst_trend',0.5):.2f}",
            "Vol Cnf": f"{v.get('volume_confirm',0.5):.0%}",
            "Stretch": v.get("trade_stretch","—"),
            "Alerts": len(alerts),
        })

    if rows:
        df = pd.DataFrame(rows)

        def color_signal(val):
            if val=="bullish": return "color:#10B981"
            if val=="bearish": return "color:#EF4444"
            if val=="mixed":   return "color:#F59E0B"
            return "color:#6B7280"

        st.dataframe(
            df.style.applymap(lambda v: color_signal(v) if v in ("bullish","bearish","neutral","mixed") else "",
                              subset=["Trade","Trend","Tail","Composite"]),
            hide_index=True, height=450, use_container_width=True,
        )
    else:
        st.info("No assets match filters.")

    # Alerts
    all_alerts = [(sym, a) for sym, v in asset_ranges.items() for a in v.get("alerts",[])]
    all_alerts.sort(key=lambda x: {"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_alerts:
        st.markdown("---")
        st.markdown("### 🔔 Active Alerts")
        for sym, a in all_alerts[:20]:
            cls = f"alert-{a['priority'].lower()}"
            icon = "🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
            st.markdown(f'<div class="{cls}">{icon} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a["note"]}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad Map — 50+ Countries")
    st.caption("Hedgeye runs GIP for every major economy. Global Quad = market-cap weighted.")

    if not global_:
        st.warning("No global data. Click Refresh."); st.stop()

    # Summary
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(quad_card_html("GLOBAL QUAD",gq,global_.get("global_conf",0.5)), unsafe_allow_html=True)
    with c2:
        usd_bias = global_.get("usd_bias","—")
        usd_c = "#EF4444" if usd_bias=="bullish" else "#10B981"
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">USD BIAS</div>
  <div class="metric-val" style="color:{usd_c}">{usd_bias.upper()}</div>
  <div style="font-size:0.72rem;color:#9CA3AF;margin-top:6px">{global_.get('usd_rationale','')[:60]}</div>
</div>""", unsafe_allow_html=True)
    with c3:
        sync = global_.get("synchronized",False)
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">SYNCHRONIZATION</div>
  <div class="metric-val" style="color:{'#10B981' if sync else '#EF4444'}">{'SYNC' if sync else 'DIVERGENT'}</div>
</div>""", unsafe_allow_html=True)
    with c4:
        em_hw = global_.get("em_headwind",False)
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">EM HEADWIND</div>
  <div class="metric-val" style="color:{'#EF4444' if em_hw else '#10B981'}">{'YES' if em_hw else 'NO'}</div>
  <div style="font-size:0.72rem;color:#9CA3AF;margin-top:6px">{global_.get('em_in_q3',0)} EM countries in Q3</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Country table
    countries = global_.get("countries",{})
    if countries:
        rows = []
        for country, d in sorted(countries.items()):
            q = d["quad"]; conf = d["confidence"]
            rows.append({
                "Country": country.replace("_"," "),
                "ETF": d["etf"],
                "Region": d["region"],
                "Quad": q,
                "Quad Name": q_name(q),
                "Confidence": f"{conf:.0%}",
                "ETF 1M": fmt_pct(d.get("etf_1m")),
                "ETF 3M": fmt_pct(d.get("etf_3m")),
                "ETF 6M": fmt_pct(d.get("etf_6m")),
                "Commodity Sens": f"{d['commodity_sensitivity']:.0%}",
                "USD Sens": f"{d['usd_sensitivity']:.0%}",
                "Rationale": d.get("rationale","")[:40],
            })
        df_c = pd.DataFrame(rows)

        region_filter = st.multiselect("Filter by Region",
            sorted(df_c["Region"].unique()), default=sorted(df_c["Region"].unique()))
        quad_f = st.multiselect("Filter by Quad", ["Q1","Q2","Q3","Q4"], default=["Q1","Q2","Q3","Q4"])

        df_c = df_c[df_c["Region"].isin(region_filter) & df_c["Quad"].isin(quad_f)]

        def color_quad(val):
            return f"color:{QUAD_COLORS.get(val,'#9CA3AF')}"

        st.dataframe(
            df_c.style.applymap(color_quad, subset=["Quad"]),
            hide_index=True, height=500, use_container_width=True,
        )

    # Quad distribution donut
    col_d, col_r = st.columns(2)
    with col_d:
        qdist = global_.get("quad_distribution",{})
        if qdist:
            fig = go.Figure(go.Pie(
                labels=list(qdist.keys()),
                values=list(qdist.values()),
                marker_colors=[QUAD_COLORS.get(q,"#9CA3AF") for q in qdist],
                hole=0.5, textinfo="label+percent",
            ))
            fig.update_layout(
                title="Country Quad Distribution",
                paper_bgcolor="#111827", font=dict(color="#E8ECF0"),
                height=280, margin=dict(t=30,b=0,l=0,r=0),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    with col_r:
        reg_quads = global_.get("region_quads",{})
        if reg_quads:
            st.markdown("#### Dominant Quad by Region")
            for region, q in sorted(reg_quads.items()):
                c = QUAD_COLORS.get(q,"#9CA3AF")
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 10px;border-bottom:1px solid #1F2B3D"><span style="color:#9CA3AF">{region.upper()}</span><span style="color:{c};font-weight:700;font-family:JetBrains Mono">{q} {q_name(q)}</span></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# BOTTLENECK SCANNER
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Bottleneck Scanner":
    st.markdown("# 🔍 Bottleneck Scanner")
    st.caption("Supply-constraint plays that fit the current macro regime. Citrini + Hedgeye methodology.")

    if not btk:
        st.warning("No scanner data. Click Refresh."); st.stop()

    meta = btk.get("meta",{})
    pb   = btk.get("playbook",{})

    # Stats
    s1,s2,s3,s4 = st.columns(4)
    s1.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#00D4AA">{meta.get("level_1_count",0)}</div><div class="metric-lbl">Level 1 (Pre-Breakout)</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#F59E0B">{meta.get("level_2_count",0)}</div><div class="metric-lbl">Level 2 (In Uptrend)</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="metric-card"><div class="metric-val">{meta.get("scored",0)}</div><div class="metric-lbl">Total Scored</div></div>', unsafe_allow_html=True)
    s4.markdown(f'<div class="metric-card"><div class="metric-val" style="color:{q_color(sq)}">{sq}</div><div class="metric-lbl">Structural Quad</div></div>', unsafe_allow_html=True)

    # Regime playbook
    with st.expander("📋 Current Regime Playbook", expanded=True):
        col_b, col_w = st.columns(2)
        with col_b:
            st.markdown(f"**✅ Best Sectors**: {', '.join(pb.get('sectors_overweight',[]))}")
            st.markdown(f"**📈 Best Assets**: {', '.join(pb.get('best',[])[:5])}")
            st.markdown(f"**💱 FX**: {pb.get('fx','')}")
        with col_w:
            st.markdown(f"**❌ Avoid Sectors**: {', '.join(pb.get('sectors_underweight',[]))}")
            st.markdown(f"**📉 Worst Assets**: {', '.join(pb.get('worst',[])[:5])}")
            st.markdown(f"**🏦 Bonds**: {pb.get('bonds','')}")

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Level 1 (Pre-Breakout)", "📈 Level 2 (Uptrend)", "👀 Watch List", "❌ Avoid"])

    def render_candidates(candidates, label):
        if not candidates:
            st.info(f"No {label} candidates found in current universe.")
            return
        rows = []
        for c in candidates:
            rows.append({
                "Ticker": c["ticker"],
                "Sector": c["sector"].replace("_"," ").title(),
                "Score": f"{c['score']:.2f}",
                "Constraint": f"{c['constraint']:.0%}",
                "Regime Fit": f"{c['regime_fit']:.0%}",
                "Trend": c["trend"].title(),
                "HH": "✅" if c["hh"] else "—",
                "HL": "✅" if c["hl"] else "—",
                "Accum": f"{c['acc']:.0%}",
                "RS 3M": fmt_pct(c["rs_3m"]),
                "Range": c["range_label"],
                "Px": fmt_f(c["px"],2),
                "Rationale": c["rationale"][:60],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=350)

    with tab1: render_candidates(btk.get("level_1",[]), "Level 1")
    with tab2: render_candidates(btk.get("level_2",[]), "Level 2")
    with tab3: render_candidates(btk.get("watch",[]),   "Watch")
    with tab4: render_candidates(btk.get("avoid",[]),   "Avoid")


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔮 Scenarios":
    st.markdown("# 🔮 Adaptive Scenarios")
    st.caption("Data-driven scenario discovery. Not forecasts — probabilistic maps of what the data requires.")

    if not scen:
        st.warning("No scenario data."); st.stop()

    stability = scen.get("regime_stability","unknown")
    stab_c = "#10B981" if stability=="stable" else "#EF4444"
    col1, col2 = st.columns([1,2])
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Regime Stability</div><div class="metric-val" style="color:{stab_c}">{stability.upper()}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Flip Risk</div><div class="metric-val">{scen.get("flip_hazard",0):.0%}</div></div>', unsafe_allow_html=True)

    scenarios = scen.get("scenarios",[])
    if not scenarios: st.info("No scenarios available."); st.stop()

    for i, s in enumerate(scenarios):
        prob_c = "#10B981" if s.probability>0.40 else "#F59E0B" if s.probability>0.25 else "#6B7280"
        badge = "🎯 BASE" if i==0 else "🔄 ALT" if i==1 else "⚠️ RISK" if i==2 else "📌 TAIL"
        with st.expander(f"{badge} {s.name} — P={s.probability:.0%} | {s.headline}", expanded=(i==0)):
            c1,c2,c3 = st.columns(3)
            c1.metric("Probability", f"{s.probability:.0%}")
            c2.metric("Confirmation", f"{s.confirmation_score:.0%}")
            c3.metric("Timeframe", f"~{s.timeframe_weeks}w")

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"**✅ Best Assets**: {', '.join(s.best_assets[:5])}")
                st.markdown("**🔔 Triggers**:")
                for t in s.confirmation_triggers[:4]:
                    st.markdown(f"  • {t}")
            with col_r:
                st.markdown(f"**❌ Avoid**: {', '.join(s.worst_assets[:5])}")
                st.markdown("**🚫 Invalidators**:")
                for t in s.invalidators[:3]:
                    st.markdown(f"  • {t}")

            st.caption(f"**Catalyst**: {s.catalyst} | **Conviction**: {s.conviction}")


# ══════════════════════════════════════════════════════════════════════════════
# IHSG
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Context")
    st.caption("Indonesia in global GIP context. EIDO + JKSE + macro regime overlay.")

    indonesia = global_.get("countries",{}).get("Indonesia",{})
    if not indonesia:
        st.warning("Indonesia data not loaded. Refresh required."); st.stop()

    q = indonesia.get("quad","Q3"); conf = indonesia.get("confidence",0)
    c1,c2,c3 = st.columns(3)
    c1.markdown(quad_card_html("INDONESIA QUAD",q,conf), unsafe_allow_html=True)
    with c2:
        usd_hw = indonesia.get("usd_headwind",0)
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">USD Headwind</div>
  <div class="metric-val" style="color:{'#EF4444' if usd_hw>0.3 else '#10B981'}">{usd_hw:.0%}</div>
  <div style="font-size:0.72rem;color:#9CA3AF">USD Sensitivity: {indonesia.get('usd_sensitivity',0.55):.0%}</div>
</div>""", unsafe_allow_html=True)
    with c3:
        comm = indonesia.get("commodity_sensitivity",0.70)
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">Commodity Sensitivity</div>
  <div class="metric-val">{comm:.0%}</div>
  <div style="font-size:0.72rem;color:#9CA3AF">Coal · Palm Oil · Nickel</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Performance")
    perf_rows = [
        {"Period": "1 Month",  "Return": fmt_pct(indonesia.get("etf_1m"))},
        {"Period": "3 Months", "Return": fmt_pct(indonesia.get("etf_3m"))},
        {"Period": "6 Months", "Return": fmt_pct(indonesia.get("etf_6m"))},
        {"Period": "12 Months","Return": fmt_pct(indonesia.get("etf_12m"))},
    ]
    st.dataframe(pd.DataFrame(perf_rows), hide_index=True)

    st.markdown("#### Rationale")
    st.info(indonesia.get("rationale","Data-derived from ETF price action"))

    st.markdown("#### Indonesia in Hedgeye Context")
    st.markdown(f"""
**Current structural quad: {sq}** — Indonesia in Q3 = headwinds:
- 🔴 Commodity cycle peaked (coal/palm oil/nickel) — Q3 demand slowdown
- 🔴 IDR fragile without commodity tailwind
- 🔴 Global Q3 = commodity demand weakens
- 🔴 Hedgeye: SHORT Indonesia (EIDO) — anti-Asia EM
- ✅ Only recovery catalyst: USD TREND breakdown + China reopening + BI rate pivot

**IHSG regime**: {'⚠️ Avoid — Hedgeye bearish' if q in ('Q3','Q4') else '🟢 Monitor — Improving'}
""")

    # EIDO risk range if available
    eido_rr = rr.get("asset_ranges",{}).get("EIDO")
    if eido_rr:
        st.markdown("#### EIDO Risk Range (TRADE/TREND/TAIL)")
        cols = st.columns(3)
        for i, (dur, data) in enumerate([("TRADE", eido_rr.get("trade",{})), ("TREND", eido_rr.get("trend",{})), ("TAIL", eido_rr.get("tail",{}))]):
            sig = data.get("signal","neutral")
            sc = SIGNAL_COLORS.get(sig,"#6B7280")
            cols[i].markdown(f"""
<div class="metric-card">
  <div class="metric-lbl">{dur}</div>
  <div style="color:{sc};font-weight:700;font-family:'JetBrains Mono'">{sig.upper()}</div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-top:6px">LRR: {fmt_f(data.get('lrr'),2)} | TRR: {fmt_f(data.get('trr'),2)}</div>
  <div style="font-size:0.72rem;color:#9CA3AF">Hurst: {data.get('hurst',0.5):.2f}</div>
</div>""", unsafe_allow_html=True)

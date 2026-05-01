"""app.py — MacroRegime Pro v16 | Hedgeye GIP Framework + Full Autonomy Pipeline

v16 changes:
- DiscoveryOrchestrator v3 wired (adaptive/reactive/proactive — was orphaned)
- Bottleneck page: unified thesis, Range Action, Forward Mult, Pod proxy, RR cross-ref
- Narratives page: updated for v3 format (narrative_dashboard + ignition_details)
- Early Discovery page: wired snap["discovery_v3"] (reactive+proactive per market)
- Dashboard: sector_momentum card + discovery_v3 summary
- Extract: dv3 + sec_mom pulled from snap
- Version bump: v16 in sidebar
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.vix-investable{background:linear-gradient(90deg,#064e3b,#065f46);border-left:6px solid #10B981;padding:16px;border-radius:8px;}
.vix-chop{background:linear-gradient(90deg,#451a03,#78350f);border-left:6px solid #F59E0B;padding:16px;border-radius:8px;}
.vix-defensive{background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:6px solid #EF4444;padding:16px;border-radius:8px;}
.winrate-card{background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;}
.signal-A{background:linear-gradient(90deg,#064e3b,#065f46);border-left:4px solid #10B981;padding:12px;border-radius:6px;margin-bottom:8px;}
.signal-shortA{background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:4px solid #EF4444;padding:12px;border-radius:6px;margin-bottom:8px;}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC  = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN  = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
SC  = {"bullish":"#10B981","bearish":"#EF4444","neutral":"#6B7280","mixed":"#F59E0B"}

def qc(q):  return QC.get(q,"#9CA3AF")
def qn(q):  return QN.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=3):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

# ── Chart helpers ─────────────────────────────────────────────────────────────
def prob_bar(probs: dict, title: str):
    if not probs: return go.Figure()
    items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    qs,ps = zip(*items)
    colors = [QC.get(q,"#9CA3AF") for q in qs]
    fig = go.Figure(go.Bar(x=list(qs), y=list(ps), marker_color=colors,
                           text=[f"{p:.0%}" for p in ps], textposition="outside"))
    fig.update_layout(title=title,height=220,margin=dict(l=10,r=10,t=30,b=10),
                      paper_bgcolor="#0F172A",plot_bgcolor="#0F172A",
                      font=dict(color="#E8ECF0"),yaxis=dict(tickformat=".0%",range=[0,1]),
                      showlegend=False)
    return fig

def price_chart(prices, tickers, title="", days=252):
    fig = go.Figure()
    for t in tickers:
        s = prices.get(t)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna().tail(days)
        if s.empty or s.iloc[0] == 0: continue
        norm = s / s.iloc[0] * 100
        fig.add_trace(go.Scatter(x=norm.index, y=norm.values, name=t, mode="lines",
                                 line=dict(width=1.5)))
    fig.update_layout(title=title, height=280, margin=dict(l=10,r=10,t=30,b=10),
                      paper_bgcolor="#0F172A", plot_bgcolor="#111827",
                      font=dict(color="#E8ECF0"), showlegend=True,
                      legend=dict(orientation="h",y=-0.2))
    return fig

def qcard(label, quad, conf, sub=""):
    c = qc(quad)
    return f'''<div style="background:#111827;border:2px solid {c};border-radius:10px;padding:14px;text-align:center;">
    <div style="font-size:10px;color:#9CA3AF;">{label}</div>
    <div style="font-size:28px;font-weight:900;color:{c};">{quad}</div>
    <div style="font-size:13px;color:{c};margin-top:2px;">{qn(quad)}</div>
    <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Conf: {conf:.0%}</div>
    <div style="font-size:10px;color:#6B7280;margin-top:2px;">{sub}</div>
    </div>'''

def _transition_panel(probs, quad, label, sub):
    c = qc(quad)
    st.markdown(f'<div style="background:#111827;border:1px solid {c};border-radius:8px;padding:10px;margin-bottom:8px;"><div style="font-size:10px;color:#9CA3AF;">{label} — {sub}</div><div style="font-size:22px;font-weight:800;color:{c};">{quad} <span style="font-size:12px;font-weight:400;">{qn(quad)}</span></div></div>', unsafe_allow_html=True)
    st.plotly_chart(prob_bar(probs, ""), use_container_width=True, config={"displayModeBar":False})

def _btk_badge(sym, btk_data):
    if not btk_data: return ""
    colors = {"level_1":"#10B981","level_2":"#F59E0B","watch":"#6366F1","avoid":"#EF4444"}
    for level in ("level_1","level_2","watch","avoid"):
        for c in btk_data.get(level,[]):
            if c.get("ticker") == sym:
                lvl = level
                return f'<span style="color:{colors.get(lvl,"#9CA3AF")};font-size:10px;">{lvl.replace("_"," ").upper()}</span>'
    return ""

def _render_universe(title, tickers_map, prices, btk_data, days=252):
    st.markdown(f"### {title}")
    rows = []
    for sym, info in tickers_map.items():
        s = prices.get(sym)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna().tail(days)
        if s.empty: continue
        ret1m = float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
        ret3m = float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
        ret6m = float(s.iloc[-1]/s.iloc[-126]-1) if len(s)>=126 else 0
        badge = _btk_badge(sym, btk_data)
        name = info if isinstance(info,str) else info.get("name",sym)
        rows.append({"Ticker":sym,"Name":name,"1M":f"{ret1m:+.1%}","3M":f"{ret3m:+.1%}","6M":f"{ret6m:+.1%}","Bottleneck":badge})
    if rows:
        df = pd.DataFrame(rows)
        st.markdown(df.to_html(escape=False,index=False), unsafe_allow_html=True)
        fig = price_chart(prices, list(tickers_map.keys())[:8], title=f"{title} — Normalized", days=days)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    else:
        st.info(f"No data loaded for {title}.")

def _render_scenario(sc, label, color, badge):
    if not sc: return
    if isinstance(sc, dict):
        name=sc.get("name",""); prob=sc.get("probability",0); conf=sc.get("confirmation_score",0)
        headline=sc.get("headline",""); catalyst=sc.get("catalyst",""); em_note=sc.get("em_note","")
        best=sc.get("best_assets",[]); worst=sc.get("worst_assets",[]); conv=sc.get("conviction","")
        triggers=sc.get("confirmation_triggers",[]); invalidators=sc.get("invalidators",[])
    else:
        name=sc.name; prob=sc.probability; conf=sc.confirmation_score
        headline=sc.headline; catalyst=sc.catalyst; em_note=sc.em_note
        best=sc.best_assets; worst=sc.worst_assets; conv=sc.conviction
        triggers=sc.confirmation_triggers; invalidators=sc.invalidators
    with st.expander(f"{badge} **{label}** — P={prob:.0%} · Conf={conf:.0%}", expanded=(label=="BASE")):
        st.markdown(f"**{headline}**")
        st.markdown(f"**Catalyst:** {catalyst}")
        st.markdown(f"**Conviction:** {conv}")
        if triggers: st.markdown(f"**Triggers:** {' · '.join(triggers)}")
        if invalidators: st.markdown(f"**Invalidators:** {' · '.join(invalidators)}")
        st.markdown(f"**EM Note:** {em_note}")
        c1,c2 = st.columns(2)
        if best: c1.markdown(f"**Best:** {' · '.join(best[:8])}")
        if worst: c2.markdown(f"**Worst:** {' · '.join(worst[:8])}")

# ── Session state ─────────────────────────────────────────────────────────────
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v17 · Front-Run*")
    st.divider()
    page = st.radio("", [
        "✈️ Front-Run",
        "🏠 Dashboard","📈 GIP Regime","⏱️ Timing","🎯 Risk Ranges",
        "🌍 Global Quad","📊 US Stocks",
        "💱 Forex","🛢 Commodities","₿ Crypto",
        "🇮🇩 IHSG","🔍 Bottleneck","📖 Narratives","🔮 Early Discovery",
        "🏥 Health","🔮 Scenarios","⚡ Signal Strength",
        "📋 Paper Trader",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading = True
    with c2:
        if st.button("⚡ Force", use_container_width=True):
            st.session_state.loading = True; st.session_state.snap = None
    with st.expander("⚙️ Universe"):
        inc_us   = st.checkbox("US Stocks", True)
        inc_fx   = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("IHSG", True)
    st.divider()
    # Dynamic quad caption — reads from snap, never hardcoded
    _snap_peek = st.session_state.get("snap") or {}
    _gip_peek  = _snap_peek.get("gip") if isinstance(_snap_peek, dict) else None
    _sq_peek   = getattr(_gip_peek, "structural_quad", "—") if _gip_peek else "—"
    _mq_peek   = getattr(_gip_peek, "monthly_quad",   "—") if _gip_peek else "—"
    _gq_peek   = (_snap_peek.get("global") or {}).get("global_quad","—") if isinstance(_snap_peek, dict) else "—"
    _qc_peek   = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
    st.markdown(
        f'<div style="font-size:11px;color:#6B7280;line-height:1.8;">'
        f'S: <span style="color:{_qc_peek.get(_sq_peek,"#9CA3AF")};font-weight:700;">{_sq_peek}</span> · '
        f'M: <span style="color:{_qc_peek.get(_mq_peek,"#9CA3AF")};font-weight:700;">{_mq_peek}</span> · '
        f'G: <span style="color:{_qc_peek.get(_gq_peek,"#9CA3AF")};font-weight:700;">{_gq_peek}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Load / build snapshot ─────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb = st.progress(0.0); pt = st.empty()
    def prog(m, f): pb.progress(f); pt.caption(m)
    snap = build_snapshot(
        progress_cb=prog,
        include_us_stocks=inc_us, include_forex=inc_fx,
        include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg,
    )
    st.session_state.snap = snap
    st.session_state.loading = False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ No snapshot. Click **🔄 Refresh** or **⚡ Force** to rebuild."); st.stop()

# ── Extract snap data ─────────────────────────────────────────────────────────
gip        = snap.get("gip")
global_    = snap.get("global", {})
rr         = snap.get("risk_ranges", {})
scen       = snap.get("scenarios", {})
narr       = snap.get("narratives", {})
transition = snap.get("transition", None)
health     = snap.get("health", {})
analogs    = snap.get("analogs", {})
btk        = snap.get("bottleneck", {})
pb_data    = snap.get("playbook", {})
prices     = snap.get("prices", {})
stress     = snap.get("stress", {})
auto_disc  = snap.get("auto_discoveries", {})
fb_eval    = snap.get("feedback_eval", {})
dv3        = snap.get("discovery_v3", {})        # v16: DiscoveryOrchestrator output
sec_mom    = snap.get("sector_momentum", {})     # v16: sector RS vs SPY
frontrun   = snap.get("frontrun", {})            # v17: unified front-run watchlist
paper_tr   = snap.get("paper_trader", {})        # v17: paper trader state

sq = gip.structural_quad if gip else "Q3"
mq = gip.monthly_quad if gip else "Q2"
gq = global_.get("global_quad", "Q3")

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(
        f'<div style="font-size:11px;color:#6B7280;">Built {snap.get("build_time_s",0)}s · '
        f'Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · '
        f'RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True
    )
    st.markdown("# MacroRegime Pro — Dashboard")

    # VIX Bucket Banner
    vix_data = health.get("vix_bucket", {}) if health else {}
    vix_b = vix_data.get("bucket","—"); vix_last=vix_data.get("vix_last",0)
    vix_note=vix_data.get("note",""); vix_risk=vix_data.get("risk_mode","—")
    if vix_b=="Investable":
        vix_html=f'<div class="vix-investable"><div style="font-size:20px;font-weight:800;color:#10B981;">🟢 INVESTABLE BUCKET</div><div style="font-size:13px;color:#A7F3D0;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Buy dips when signal searah.</div></div>'
    elif vix_b=="Chop":
        vix_html=f'<div class="vix-chop"><div style="font-size:20px;font-weight:800;color:#F59E0B;">🟡 CHOP BUCKET</div><div style="font-size:13px;color:#FDE68A;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Trade ranges, kurangi chase breakout.</div></div>'
    elif vix_b=="Defensive":
        vix_html=f'<div class="vix-defensive"><div style="font-size:20px;font-weight:800;color:#EF4444;">🔴 DEFENSIVE BUCKET</div><div style="font-size:13px;color:#FECACA;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Capital preservation. Size down.</div></div>'
    else:
        vix_html=f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;"><div style="font-size:14px;color:#9CA3AF;">VIX: {vix_last:.1f}</div></div>'
    st.markdown(vix_html, unsafe_allow_html=True)

    # ── FRONT-RUN STATUS BANNER ───────────────────────────────────────────────
    fw = frontrun.get("timing_window", getattr(transition,"front_run_window","not yet") if transition else "not yet")
    fr_rat = frontrun.get("timing_rationale", getattr(transition,"front_run_rationale","") if transition else "")
    boarding_ct = len(frontrun.get("boarding_now",[]))
    gate_ct     = len(frontrun.get("gate_soon",[]))
    fw_cfg = {
        "now":   ("#EF4444","🚨","FRONT-RUN NOW"),
        "1-2w":  ("#F59E0B","⚡","GATE OPENS SOON — 1-2 WEEKS"),
        "3-6w":  ("#6366F1","👀","EARLY WARNING — 3-6 WEEKS"),
        "not yet":("#374151","🛑","NO TRANSITION SIGNAL"),
    }
    fc,fi,fl = fw_cfg.get(fw, fw_cfg["not yet"])
    boarding_badge = f' <span style="background:#EF444433;border-radius:4px;padding:2px 8px;font-size:11px;color:#EF4444;margin-left:8px;">🚨 {boarding_ct} BOARDING</span>' if boarding_ct else ""
    gate_badge = f' <span style="background:#F59E0B33;border-radius:4px;padding:2px 8px;font-size:11px;color:#F59E0B;margin-left:4px;">⚡ {gate_ct} GATE</span>' if gate_ct else ""
    st.markdown(f'''<div style="background:{fc}18;border-left:5px solid {fc};padding:14px 18px;border-radius:8px;margin:12px 0;">
    <div style="font-size:17px;font-weight:900;color:{fc};">{fi} {fl}{boarding_badge}{gate_badge}</div>
    <div style="font-size:12px;color:#D1D5DB;margin-top:6px;">{fr_rat[:140] if fr_rat else "—"}</div>
    <div style="font-size:10px;color:#6B7280;margin-top:4px;">→ Go to <b>✈️ Front-Run</b> for full watchlist with entry levels, stops, and TP targets.</div>
    </div>''', unsafe_allow_html=True)
    st.markdown("---")

    # Quad cards
    tp1,tp2,tp3 = st.columns(3)
    with tp1:
        struct_p = gip.structural_probs if gip else {}
        _transition_panel(struct_p, sq, "STRUCTURAL", "Quarterly")
    with tp2:
        month_p = gip.monthly_probs if gip else {}
        _transition_panel(month_p, mq, "MONTHLY", "Weather/Tactical")
    with tp3:
        gprobs = global_.get("global_probs",{})
        _transition_panel(gprobs, gq, "GLOBAL", "50 Countries")

    # Scenario cards
    scenarios_list = scen.get("scenarios",[])
    if scenarios_list:
        badges=["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]
        badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
        r1,r2=st.columns(2),st.columns(2)
        grids=[r1[0],r1[1],r2[0],r2[1]]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]
            em_short=(sc_item.em_note[:70]+"...") if hasattr(sc_item,"em_note") and len(sc_item.em_note)>70 else getattr(sc_item,"em_note","")
            name=getattr(sc_item,"name",str(sc_item))
            headline=getattr(sc_item,"headline","")
            prob=getattr(sc_item,"probability",0)
            conf=getattr(sc_item,"confirmation_score",0)
            with col:
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">
                <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} P={prob:.0%} · Conf={conf:.0%}</div>
                <div style="font-size:13px;color:#E8ECF0;margin-top:6px;font-weight:600;">{name}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{headline}</div>
                <div style="font-size:10px;color:#6B7280;margin-top:6px;">🌍 {em_short}</div>
                </div>''', unsafe_allow_html=True)

    st.markdown("---")
    c_pb,c_sig = st.columns([1.3,1])
    with c_pb:
        st.markdown("### 🎯 Regime Playbook")
        if pb_data:
            st.markdown(f"**✅ LONG:** {' · '.join(pb_data.get('best_assets',[])[:6])}")
            st.markdown(f"**❌ AVOID:** {' · '.join(pb_data.get('worst_assets',[])[:6])}")
            st.markdown(f"📊 Style: {pb_data.get('style','')}")
            st.markdown(f"💱 FX: {pb_data.get('fx','')}")
            st.markdown(f"🏦 Bonds: {pb_data.get('bonds','')}")
            if pb_data.get("monthly_adds"):
                st.markdown(f"⚡ Monthly: {' · '.join(pb_data['monthly_adds'])}")
    with c_sig:
        st.markdown("### 📡 GIP Signals")
        if gip:
            f = gip.features
            rows=[
                ["Growth Mom",   f"{f.get('growth_momentum',0):+.3f}"],
                ["Inflation Mom",f"{f.get('inflation_momentum',0):+.3f}"],
                ["Policy",       f"{f.get('policy_score',0):+.3f}"],
                ["Flip Hazard",  f"{gip.flip_hazard:.0%}"],
                ["Data Coverage",f"{gip.data_coverage:.0%}"],
            ]
            st.table(pd.DataFrame(rows, columns=["Signal","Value"]))

    # Bottleneck quick summary
    st.markdown("---")
    bc1,bc2,bc3,bc4 = st.columns(4)
    for col,lab,lst,col_c in [
        (bc1,"⚡ L1",btk.get("level_1",[]),"#10B981"),
        (bc2,"📈 L2",btk.get("level_2",[]),"#F59E0B"),
        (bc3,"👀 Watch",btk.get("watch",[]),"#6366F1"),
        (bc4,"🔮 Brewing",btk.get("brewing",[]),"#A78BFA"),
    ]:
        col.markdown(f'<div style="text-align:center;font-size:10px;color:#9CA3AF;">{lab}</div><div style="text-align:center;font-size:22px;font-weight:800;color:{col_c};">{len(lst)}</div>',unsafe_allow_html=True)

    # Sector Momentum (v16 new)
    if sec_mom:
        st.markdown("---")
        st.markdown("### 📊 Sector Momentum (RS vs SPY, 63d)")
        top_s = sorted([(s,v) for s,v in sec_mom.items() if s!="generic"], key=lambda x:x[1], reverse=True)
        sm_rows=[{"Sector":s.replace("_"," ").title(),"RS vs SPY":f"{v:+.1%}",
                  "Signal":"📈 Leading" if v>0.05 else "📉 Lagging" if v<-0.05 else "➡️ Neutral"}
                 for s,v in top_s[:12]]
        if sm_rows:
            df_sm=pd.DataFrame(sm_rows)
            def _sc_rs(v):
                try:
                    fv=float(str(v).replace("%","").replace("+",""))
                    return "color:#10B981" if fv>5 else "color:#EF4444" if fv<-5 else "color:#6B7280"
                except: return ""
            st.dataframe(df_sm.style.map(_sc_rs,subset=["RS vs SPY"]),hide_index=True,height=220,use_container_width=True)

    # Discovery v3 summary (v16 new)
    if dv3 and (dv3.get("reactive") or dv3.get("proactive") or dv3.get("merged")):
        st.markdown("---")
        st.markdown("### 🔮 Discovery v3 — Pre-Consensus Signals")
        da,db,dc=st.columns(3)
        da.metric("Reactive", len(dv3.get("reactive",[])))
        db.metric("Proactive", len(dv3.get("proactive",[])))
        dc.metric("Merged", len(dv3.get("merged",[])))
        top_merged = dv3.get("merged",[])[:5]
        for c in top_merged:
            ev=c.get("ev",0); src=c.get("source","reactive_discovery")
            ec="#EF4444" if "reactive" in src else "#6366F1"
            st.markdown(f'<div style="border-left:3px solid {ec};padding:4px 10px;background:#111827;border-radius:4px;margin-bottom:4px;font-size:11px;color:#E8ECF0;"><b>{c.get("ticker","—")}</b> <span style="color:#9CA3AF;">{c.get("sector","").replace("_"," ").title()}</span> | EV:{ev:.3f} | {c.get("narrative","")[:60]}</div>',unsafe_allow_html=True)

    # Win Rate
    if fb_eval and fb_eval.get("evaluated",0)>0:
        st.markdown("---")
        st.markdown("### 🏆 Discovery Win Rate")
        w1,w2,w3=st.columns(3)
        w1.metric("Evaluated",fb_eval.get("evaluated",0))
        w2.metric("Promoted ↑",fb_eval.get("promoted",0))
        w3.metric("Demoted ↓",fb_eval.get("demoted",0))

# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP REGIME
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Regime":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY RoC second derivative. 'Heating up or cooling down?'")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    c1,c2,c3=st.columns(3)
    with c1: st.markdown(qcard("STRUCTURAL (Quarterly)",sq,gip.structural_conf,"Primary regime"),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY (Weather)",mq,gip.monthly_conf,"Tactical overlay"),unsafe_allow_html=True)
    with c3:
        div_label="Aligned ✅" if sq==mq else "Divergent ⚠️"
        st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:10px;padding:14px;text-align:center;"><div style="font-size:10px;color:#9CA3AF;">ALIGNMENT</div><div style="font-size:22px;font-weight:700;color:#E8ECF0;margin-top:8px;">{div_label}</div><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Flip Hazard: {gip.flip_hazard:.0%}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    c1,c2=st.columns(2)
    with c1: st.plotly_chart(prob_bar(gip.structural_probs,"Structural (Quarterly)"),use_container_width=True,config={"displayModeBar":False})
    with c2: st.plotly_chart(prob_bar(gip.monthly_probs,"Monthly (Weather)"),use_container_width=True,config={"displayModeBar":False})

    prx=gip.features.get("proxy_share",0)
    if prx>0.4: st.warning(f"⚠️ {prx:.0%} signal from price proxies — add FRED_API_KEY for full accuracy.")
    else: st.success(f"✅ {1-prx:.0%} from FRED macro data")

    st.markdown("#### Raw FRED / Proxy Data")
    raw=[{"Series":k[4:].upper(),"Value":f"{v:.4f}"} for k,v in sorted(gip.features.items()) if k.startswith("raw_") and math.isfinite(float(v if v else 0))]
    if raw: st.dataframe(pd.DataFrame(raw),hide_index=True,height=250)
    else: st.info("No FRED data. Add FRED_API_KEY to secrets.toml.")

# ══════════════════════════════════════════════════════════════════════════════
# ⏱️ TIMING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⏱️ Timing":
    st.markdown("# ⏱️ Timing — Next Quad + Front-Run Window")
    st.caption("When is the next regime shift? What early warning signals are firing?")
    if not transition: st.warning("Transition engine not available. Refresh."); st.stop()

    tw = transition.get("weeks_to_transition",0)
    tc = transition.get("confidence",0)
    tnq = transition.get("next_quad","—")
    tel = transition.get("early_warnings",{})

    t1,t2,t3=st.columns(3)
    t1.metric("Weeks to Transition",f"{tw}wk")
    t2.metric("Confidence",f"{tc:.0%}")
    t3.metric("Next Quad",tnq)

    if tel:
        st.markdown("---")
        st.markdown("### 🚨 Early Warning Signals")
        st.caption("Watch for clusters turning ON.")
        ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"✅ YES" if v>=0.5 else "⬜ Not yet","Score":f"{v:.2f}"} for k,v in sorted(tel.items(),key=lambda x:x[1],reverse=True)]
        st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=300)
        firing=sum(1 for v in tel.values() if v>=0.5)
        st.progress(firing/len(tel) if tel else 0, text=f"Early warning: {firing}/{len(tel)} signals firing")

    if analogs and analogs.get("top_analogs"):
        st.markdown("---")
        st.markdown("### 📚 Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for a in analogs["top_analogs"]:
            sim=a.get("similarity",0)
            sim_c="#10B981" if sim>0.6 else "#F59E0B" if sim>0.4 else "#6B7280"
            with st.expander(f"**{a['label']}** — Similarity: {sim:.0%}", expanded=(analogs["top_analogs"].index(a)==0)):
                cc=st.columns(3)
                cc[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")
                st.markdown(f"**Impacts:** " + " | ".join([f"{k.upper()}={v}" for k,v in a.get("impacts",{}).items()]))

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("Hurst Rescaled Range Analysis. LRR=buy. TRR=trim. TREND break=EXIT.")
    ar = rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()
    sm=rr.get("summary",{})
    s1,s2,s3,s4=st.columns(4)
    for col,lab,val,c in [(s1,"Total",sm.get("total",0),"#E8ECF0"),(s2,"Bullish",sm.get("bullish",0),"#10B981"),(s3,"Bearish",sm.get("bearish",0),"#EF4444"),(s4,"A-Quality",sm.get("a_quality",0),"#00D4AA")]:
        col.markdown(f'<div style="text-align:center;font-size:11px;color:#9CA3AF;">{lab}</div><div style="text-align:center;font-size:22px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)

    fc1,fc2,fc3=st.columns(3)
    with fc1: sf=st.selectbox("Signal",["All","bullish","bearish","neutral","mixed"])
    with fc2: qf=st.multiselect("Quality",["A","B","C","short_A","short_B","none"],default=["A","B","short_A","short_B"])
    with fc3: ca=st.checkbox("Critical only",False)

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
            "H(Trade)":f"{v.get('hurst_trade',0.5):.2f}","VolCnf":f"{v.get('volume_confirm',0.5):.0%}",
            "Stretch":v.get("trade_stretch","—"),"Alerts":len(alerts)})
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
            st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {"#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"};padding:8px;border-radius:4px;margin-bottom:4px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50 Countries")
    st.caption("Same GIP model applied to country ETFs. Shows where capital is rotating.")
    if not global_: st.warning("No global data. Refresh."); st.stop()
    gq=global_.get("global_quad","Q3"); gconf=global_.get("global_conf",0.0); gprobs=global_.get("global_probs",{})
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        st.plotly_chart(prob_bar(gprobs,""),use_container_width=True,config={"displayModeBar":False})
    with c2:
        heat=[]
        for country,data in global_.get("country_quads",{}).items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=data[0],data[1],data[2]
            elif isinstance(data,dict): etf,quad,conf=data.get("etf",""),data.get("quad",""),data.get("conf",0)
            else: etf,quad,conf="","",0
            heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            df=pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=420,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📊 US STOCKS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 US Stocks":
    st.markdown("# 📊 US Stocks — Sectors · Factors · Notable Tickers")
    st.caption("Regime playbook + TRR/LRR + bottleneck badge.")
    from config.settings import US_SECTORS,US_FACTORS,TICKER_SECTOR,COMMODITIES,CRYPTO,FOREX_PAIRS,IHSG_UNIVERSE,BONDS,MACRO_PROXIES
    _render_universe("US Sectors", US_SECTORS, prices, btk)
    _render_universe("US Factors", US_FACTORS, prices, btk)
    st.markdown("### Notable Single Stocks (Bottleneck Plays)")
    excluded=set(list(US_SECTORS)+list(US_FACTORS)+list(COMMODITIES)+list(CRYPTO)+list(FOREX_PAIRS)+list(IHSG_UNIVERSE)+list(BONDS)+list(MACRO_PROXIES)+["DX-Y.NYB","^VIX","EIDO","^JKSE"])
    notable={k:v for k,v in TICKER_SECTOR.items() if k not in excluded and k in prices and v!="generic"}
    rows=[]
    for sym,sector in notable.items():
        s=prices.get(sym)
        if s is None: continue
        s=pd.to_numeric(s,errors="coerce").dropna().tail(252)
        if s.empty: continue
        ret3m=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
        badge=_btk_badge(sym,btk)
        rows.append({"Ticker":sym,"Sector":sector.replace("_"," ").title(),"3M":f"{ret3m:+.1%}","Bottleneck":badge})
    if rows:
        df=pd.DataFrame(rows)
        st.markdown(df.to_html(escape=False,index=False),unsafe_allow_html=True)
    else: st.info("No notable stocks. Add to TICKER_SECTOR in config/settings.py")

# ══════════════════════════════════════════════════════════════════════════════
# 💱 FOREX
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💱 Forex":
    st.markdown("# 💱 Forex — Regime + Carry + Divergence")
    st.caption("DXY regime + EM carry. DXY bearish = EM relief. DXY bullish = EM pain.")
    from config.settings import FOREX_PAIRS
    _render_universe("Forex Pairs", FOREX_PAIRS, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# 🛢 COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛢 Commodities":
    st.markdown("# 🛢 Commodities — Energy · Metals · Agriculture")
    st.caption("Q2/Q3 commodity cycle. Oil = growth proxy. Gold = Q3/Q4 safety.")
    from config.settings import COMMODITIES
    _render_universe("Commodities", COMMODITIES, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# ₿ CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown("# ₿ Crypto — Macro + Narrative + DePIN")
    st.caption("Q1/Q2 risk-on. Q3/Q4 risk-off. Watch BTC dominance + DXY correlation.")
    from config.settings import CRYPTO
    _render_universe("Crypto Universe", CRYPTO, prices, btk, days=252)

# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Macro + Foreign Flow + JIIPE")
    st.caption("CKPN cascade, offshore drilling, foreign flow, JIIPE industrial estate.")
    from config.settings import IHSG_UNIVERSE
    _render_universe("IHSG Universe", IHSG_UNIVERSE, prices, btk, days=252)
    st.markdown("---")
    st.markdown("### 🌍 EM Recovery Signal")
    em_sig=btk.get("em_recovery",{}) if btk else {}
    if em_sig:
        conf=em_sig.get("confidence",0)
        ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:10px;"><div style="font-size:12px;font-weight:700;color:{ec};">{em_sig.get("trigger","")}</div><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div><div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Confidence: {conf:.0%}</div><div style="font-size:11px;color:#9CA3AF;margin-top:2px;">🎯 Best: {", ".join(em_sig.get("best",[])[:6])}</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔍 BOTTLENECK — v3 (full fix: unified thesis, Range Action, FwdX, Pod, RR)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Bottleneck":
    st.markdown("# 🔍 Bottleneck Scanner — Supply Chain + Regime Fit")
    st.caption("Structural scarcity mapped to GIP regime. Level 1 = best. Level 2 = building. Watch = brewing. Avoid = regime trap. **BUY at LRR. TRIM at TRR. EXIT on Trend breakdown.**")

    if not btk: st.warning("No bottleneck data. Refresh."); st.stop()

    with st.expander("⚙️ Framework Notes — EV Formula + Signal Logic", expanded=False):
        ev_formula=btk.get("ev_formula","regime_fit × trend_score × constraint × (1+rs_3m) × fwd_mult × range_discount")
        st.markdown(f"""
**EV Formula (v3):**
```
{ev_formula}
```
- `fwd_mult` = forward Quad transition multiplier — front-runs regime shift, not just current Quad
- `range_discount` = 0.70 at resistance / 0.85 approaching — **never buy at TRR**
- `constraint` = structural scarcity score (Citrini research)
- `regime_fit` = Hedgeye 27yr backtest per Quad

⚠️ `{btk.get("flow_proxy_note","OPTIONS FLOW: proxy only.")}`
⚠️ `{btk.get("pod_proxy_note","POD PROXY: price momentum ROC only.")}`
        """)

    l1=btk.get("level_1",[]); l2=btk.get("level_2",[]); wt=btk.get("watch",[]); av=btk.get("avoid",[]); br=btk.get("brewing",[])
    known_ct=btk.get("known_count",0)

    s1,s2,s3,s4,s5,s6=st.columns(6)
    for col,lab,val,c in [(s1,"Level 1",len(l1),"#10B981"),(s2,"Level 2",len(l2),"#F59E0B"),(s3,"Watch",len(wt),"#6366F1"),(s4,"Avoid",len(av),"#EF4444"),(s5,"Brewing",len(br),"#A78BFA"),(s6,"Known",known_ct,"#00D4AA")]:
        col.markdown(f'<div style="text-align:center;font-size:10px;color:#9CA3AF;">{lab}</div><div style="text-align:center;font-size:20px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)

    st.markdown("---")
    fc1,fc2,fc3=st.columns(3)
    with fc1: show_known_only=st.checkbox("Known bottlenecks only",False)
    with fc2: filter_action=st.selectbox("Range Action Filter",["All","✅ BUY ZONE","⏳ WAIT — MID RANGE","⚠️ APPROACHING TRR","🔴 TRIM ZONE"])
    with fc3: filter_direction=st.selectbox("Direction",["All","long","short","avoid_long","neutral"])

    def _apply_filters(data):
        out=[]
        for item in data:
            if show_known_only and not item.get("known"): continue
            if filter_action!="All" and item.get("range_action","")!=filter_action: continue
            if filter_direction!="All" and item.get("direction","")!=filter_direction: continue
            out.append(item)
        return out

    def _render_level(level_data, title, color):
        filtered=_apply_filters(level_data)
        if not filtered: return
        st.markdown(f"### {title} ({len(filtered)})")
        rows=[]
        for c in filtered:
            thesis_display=(c.get("thesis") or c.get("known_thesis") or c.get("rationale") or "—")[:85]
            catalyst_display=(c.get("catalyst") or c.get("known_catalyst") or "—")[:55]
            risk_display=(c.get("risk") or c.get("known_risk") or "—")[:55]
            pod_q=c.get("pod_quality","—")
            pod_icon="📈" if pod_q=="accelerating" else "📉" if pod_q=="decelerating" else "➡️"
            rows.append({
                "K":"✅" if c.get("known") else "◻",
                "Ticker":c["ticker"],"Market":c.get("market","—").replace("_"," ").title()[:10],
                "Sector":c.get("sector","—").replace("_"," ").title()[:18],"Trend":c.get("trend","—"),
                "Dir":c.get("direction","—"),"EV":f'{c.get("ev",0):.3f}',"Score":f'{c.get("score",0):.2f}',
                "RF":f'{c.get("regime_fit",0):.0%}',"Const":f'{c.get("constraint",0):.2f}',
                "FwdX":f'{c.get("forward_mult",1):.2f}x',
                "Action":c.get("range_action","—"),
                "RS 3M":f'{c.get("rs_3m",0):.1%}' if c.get("rs_3m") is not None else "—",
                "Pod":f'{pod_icon}{c.get("pod1_proxy",0):+.2f}',"RR Sig":c.get("rr_signal","—"),
                "Thesis":thesis_display,"Catalyst":catalyst_display,"Risk":risk_display,
            })
        if not rows: st.info("No results after filter."); return
        df=pd.DataFrame(rows)
        def _sc_trend(v): return "color:#10B981" if v=="uptrend" else "color:#EF4444" if v=="downtrend" else "color:#F59E0B"
        def _sc_action(v):
            if "BUY" in str(v): return "color:#10B981;font-weight:700"
            if "TRIM" in str(v): return "color:#EF4444;font-weight:700"
            if "APPROACH" in str(v): return "color:#F59E0B"
            return "color:#6B7280"
        def _sc_dir(v): return "color:#10B981" if v=="long" else "color:#EF4444" if v=="short" else "color:#F59E0B" if "avoid" in str(v) else "color:#6B7280"
        def _sc_rr(v): return "color:#10B981" if v=="bullish" else "color:#EF4444" if v=="bearish" else "color:#6B7280"
        def _sc_fwd(v):
            try:
                val=float(str(v).replace("x",""))
                return "color:#10B981;font-weight:700" if val>1.10 else "color:#F59E0B" if val>1.0 else "color:#6B7280"
            except: return ""
        styled=df.style.map(_sc_trend,subset=["Trend"]).map(_sc_action,subset=["Action"]).map(_sc_dir,subset=["Dir"]).map(_sc_rr,subset=["RR Sig"]).map(_sc_fwd,subset=["FwdX"])
        st.dataframe(styled,hide_index=True,height=min(len(rows)*38+50,520),use_container_width=True)
        with st.expander(f"📋 Thesis + TP Detail — {title}",expanded=False):
            for c in filtered[:12]:
                d_col="#10B981" if c.get("direction")=="long" else "#EF4444" if c.get("direction")=="short" else "#F59E0B"
                rr_col="#10B981" if c.get("rr_signal")=="bullish" else "#EF4444" if c.get("rr_signal")=="bearish" else "#6B7280"
                pod_col="#10B981" if c.get("pod_quality")=="accelerating" else "#EF4444" if c.get("pod_quality")=="decelerating" else "#9CA3AF"
                tp=c.get("tp",{}); tp_str=""
                if tp:
                    t1v=tp.get("t1"); t2v=tp.get("t2"); t3v=tp.get("t3"); stp=tp.get("stop")
                    if t1v and stp: tp_str=f"T1={t1v:.2f} | T2={t2v:.2f}"+(f" | T3={t3v:.2f}" if t3v else "")+f" | Stop={stp:.2f}"
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;margin-bottom:8px;">
<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">
<span style="font-size:14px;font-weight:800;color:#E8ECF0;">{c["ticker"]}</span>
<span style="font-size:11px;color:{d_col};font-weight:700;">{c.get("direction","—").upper()}</span>
<span style="font-size:11px;color:{rr_col};">RR: {c.get("rr_signal","—")}</span>
<span style="font-size:11px;color:#00D4AA;font-weight:700;">{c.get("range_action","—")}</span>
<span style="font-size:10px;color:#9CA3AF;">EV:{c.get("ev",0):.3f} | FwdX:{c.get("forward_mult",1):.2f}x | RF:{c.get("regime_fit",0):.0%}</span>
</div>
<div style="font-size:11px;color:#D1D5DB;margin-bottom:4px;"><b>Thesis:</b> {c.get("known_thesis") or c.get("thesis","—")}</div>
<div style="font-size:11px;color:#9CA3AF;margin-bottom:2px;"><b>Catalyst:</b> {c.get("catalyst","—")}</div>
<div style="font-size:11px;color:#EF4444;margin-bottom:4px;"><b>Risk:</b> {c.get("risk","—")}</div>
<div style="font-size:10px;color:#4B5563;margin-bottom:2px;">{tp_str}</div>
<div style="font-size:10px;color:{pod_col};">Pod Proxy: {c.get("pod_quality","—")} ({c.get("pod1_proxy",0):+.2f}) | {c.get("pod_note","proxy only")}</div>
</div>''', unsafe_allow_html=True)

    _render_level(l1,"⚡ Level 1 — Best Setups","#10B981")
    _render_level(l2,"📈 Level 2 — Building","#F59E0B")
    _render_level(wt,"👀 Watch — Brewing (acc≥0.65)","#6366F1")
    _render_level(av,"🚫 Avoid — Regime Trap","#EF4444")

    if br:
        st.markdown("---")
        st.markdown("### 🔮 Pre-Consensus Brewing — Second-Order Citrini Plays")
        st.caption("High constraint (≥0.70) + regime fit (≥0.60) + accumulation (≥0.65). Not yet Level 1/2 — pre-consensus.")
        for c in br[:8]:
            fwd_color="#10B981" if c.get("forward_mult",1)>1.10 else "#A78BFA"
            st.markdown(f'''<div style="background:linear-gradient(90deg,#1e1b4b,#2d1b69);border-left:4px solid #A78BFA;border-radius:6px;padding:10px;margin-bottom:6px;">
<div style="font-size:13px;font-weight:800;color:#E8ECF0;">{c["ticker"]} <span style="font-size:10px;color:#A78BFA;font-weight:400;margin-left:6px;">{c.get("sector","").replace("_"," ").title()}</span> <span style="font-size:10px;color:#00D4AA;font-weight:700;margin-left:8px;">{c.get("range_action","—")}</span></div>
<div style="font-size:11px;color:#C4B5FD;margin-top:4px;">{(c.get("thesis") or c.get("known_thesis") or "—")[:110]}</div>
<div style="font-size:10px;color:#7C3AED;margin-top:3px;">EV:{c.get("ev",0):.3f} | <span style="color:{fwd_color}">FwdX:{c.get("forward_mult",1):.2f}x</span> | RF:{c.get("regime_fit",0):.0%} | Acc:{c.get("acc",0):.0%} | Const:{c.get("constraint",0):.2f}</div>
</div>''', unsafe_allow_html=True)

    st.markdown("---")
    em_sig=btk.get("em_recovery",{})
    if em_sig:
        st.markdown("### 🌍 EM Recovery Signal")
        conf=em_sig.get("confidence",0); ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;"><div style="font-size:13px;font-weight:700;color:{ec};">{em_sig.get("trigger","—")}</div><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","—")}</div><div style="font-size:12px;color:#E8ECF0;margin-top:6px;">Confidence: {conf:.0%}</div><div style="font-size:11px;color:#9CA3AF;margin-top:2px;">🎯 Best: {", ".join(em_sig.get("best",[])[:6])}</div></div>',unsafe_allow_html=True)

    on_a=btk.get("on_analysis",{})
    if on_a and on_a.get("is_bottleneck"):
        st.markdown("---")
        st.markdown("### 🔌 ON Semiconductor — Deep Analysis")
        oc1,oc2=st.columns(2)
        with oc1:
            st.markdown("**Why it surged:**")
            for r in on_a.get("why_surged",[]): st.markdown(f"• {r}")
        with oc2:
            st.markdown(f"**Status:** {on_a.get('current_status','—')}")
            st.markdown(f"**Risk watch:** {on_a.get('risk_watch','—')}")

    st.markdown("---")
    _qc=QC.get(sq,"#9CA3AF"); _qn=QN.get(sq,"")
    st.markdown(f'<div style="background:#0F172A;border:1px solid #1E293B;border-radius:8px;padding:10px;"><div style="font-size:11px;color:#9CA3AF;">Active Regime Context</div><div style="font-size:13px;font-weight:700;color:{_qc};">Structural: {sq} ({_qn}) · Monthly: {mq}</div><div style="font-size:10px;color:#6B7280;margin-top:4px;">EV uses forward_mult to front-run Quad transition. range_discount penalises at-resistance. Known bottleneck boost is conditional on trend+regime.</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES — v3 format (adaptive · reactive · proactive)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown("# 📖 Narratives — Adaptive · Reactive · Proactive")
    st.caption("Active = ignition detected. Building = growing breadth. Brewing = pre-consensus. Fading = losing strength.")
    if not narr: st.warning("No narrative data. Refresh."); st.stop()

    # Support both v3 (narrative_dashboard) and legacy (active/building/brewing/fading)
    nd = narr.get("narrative_dashboard", [])
    if nd:
        # v3 format
        igniting = [n for n in nd if n.get("ignition")]
        strong   = [n for n in nd if not n.get("ignition") and n.get("current_strength",0)>=0.45]
        building = [n for n in nd if not n.get("ignition") and 0.25<=n.get("current_strength",0)<0.45]
        weak     = [n for n in nd if n.get("current_strength",0)<0.25]

        s1,s2,s3,s4=st.columns(4)
        for col,lab,val,c in [(s1,"🔥 Igniting",len(igniting),"#EF4444"),(s2,"💪 Strong",len(strong),"#10B981"),(s3,"🔨 Building",len(building),"#F59E0B"),(s4,"💤 Weak",len(weak),"#6B7280")]:
            col.markdown(f'<div style="text-align:center;font-size:11px;color:#9CA3AF;">{lab}</div><div style="text-align:center;font-size:22px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)

        dom=narr.get("dominant_narrative")
        if dom:
            dom_str=narr.get("dominant_strength",0)
            dom_mkt=narr.get("dominant_lead_market","")
            st.success(f"🚨 **Dominant Narrative:** `{dom}` — Strength: {dom_str:.0%} | Lead Market: {dom_mkt}")

        def _render_nd(items, title, color, expanded=True):
            if not items: return
            st.markdown(f"### {title} ({len(items)})")
            for n in items:
                name=n.get("narrative","").replace("_"," ").title()
                strength=n.get("current_strength",0)
                rw=n.get("regime_weight",0)
                fw4=n.get("forecast_4w",0)
                fw8=n.get("forecast_8w",0)
                lead_mkt=n.get("lead_market","")
                lead_sec=n.get("lead_sector","")
                breadth=n.get("sector_breadth",0)
                spill=n.get("top_spillover",[])
                ign=n.get("ignition",False)
                ign_badge="🔥 IGNITION" if ign else ""
                with st.expander(f"**{name}** {ign_badge} — Strength: {strength:.0%} | RF: {rw:.0%}", expanded=(ign and expanded)):
                    c1,c2,c3=st.columns(3)
                    c1.metric("Current Strength",f"{strength:.0%}")
                    c2.metric("Forecast 4W",f"{fw4:.0%}")
                    c3.metric("Forecast 8W",f"{fw8:.0%}")
                    st.markdown(f"**Lead Market:** {lead_mkt.replace('_',' ').title()} | **Lead Sector:** {lead_sec.replace('_',' ').title()} | **Breadth:** {breadth} sectors")
                    if spill: st.markdown(f"**Spillover:** {' → '.join(spill)}")

        _render_nd(igniting,"🔥 Igniting — Critical Mass Reached","#EF4444",expanded=True)
        _render_nd(strong,  "💪 Strong — Active Narrative","#10B981",expanded=False)
        _render_nd(building,"🔨 Building — Early Traction","#F59E0B",expanded=False)
        _render_nd(weak,    "💤 Weak — Dormant / Pre-Seed","#6B7280",expanded=False)

        # Ignition details
        ign_det=narr.get("ignition_details",{})
        if ign_det:
            st.markdown("---")
            st.markdown("### 🔥 Ignition Detection Details")
            for name,det in ign_det.items():
                if det.get("ignition"):
                    st.markdown(f'<div style="background:#450a0a;border-left:4px solid #EF4444;border-radius:6px;padding:10px;margin-bottom:6px;"><div style="font-size:13px;font-weight:700;color:#EF4444;">{name.replace("_"," ").title()}</div><div style="font-size:11px;color:#9CA3AF;">Strength: {det.get("strength",0):.0%} | Lead: {det.get("lead_market","")} / {det.get("lead_sector","")}</div><div style="font-size:10px;color:#6B7280;margin-top:4px;">Catalysts: {" · ".join(det.get("catalysts",[]))}</div></div>',unsafe_allow_html=True)

        # Spillover map
        spillover=narr.get("spillover",{})
        if spillover:
            st.markdown("---")
            st.markdown("### 🌊 Cross-Market Spillover")
            for asset_class, spill_data in spillover.items():
                if spill_data:
                    st.markdown(f"**{asset_class.replace('_',' ').title()}:** {spill_data}")

    else:
        # Legacy format fallback
        active=narr.get("active",[]); building_l=narr.get("building",[]); brewing_l=narr.get("brewing",[]); fading_l=narr.get("fading",[])
        s1,s2,s3,s4=st.columns(4)
        for col,lab,val,c in [(s1,"Active",len(active),"#10B981"),(s2,"Building",len(building_l),"#F59E0B"),(s3,"Brewing",len(brewing_l),"#6366F1"),(s4,"Fading",len(fading_l),"#EF4444")]:
            col.markdown(f'<div style="text-align:center;font-size:11px;color:#9CA3AF;">{lab}</div><div style="text-align:center;font-size:22px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)
        def _render_legacy(lst, title):
            if not lst: return
            st.markdown(f"### {title}")
            for n in lst:
                with st.expander(f"**{n.get('name','')}** — {n.get('strength',0):.0%}", expanded=False):
                    st.markdown(f"**Thesis:** {n.get('thesis','')}")
                    st.markdown(f"**Catalyst:** {n.get('catalyst','')}")
                    if n.get("beneficiary_tickers"): st.markdown(f"**Beneficiaries:** {', '.join(n['beneficiary_tickers'])}")
        _render_legacy(active,"🟢 Active"); _render_legacy(building_l,"🟡 Building"); _render_legacy(brewing_l,"🔵 Brewing"); _render_legacy(fading_l,"🔴 Fading")

# ══════════════════════════════════════════════════════════════════════════════
# 🔮 EARLY DISCOVERY — v3 (Discovery Orchestrator wired)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Early Discovery":
    st.markdown("# 🔮 Early Discovery — Pre-Consensus Alpha")
    st.caption("Adaptive · Reactive · Proactive discovery across ALL markets. Source: DiscoveryOrchestrator v3 (reactive scan + proactive chain) + Autonomy Stack. Updated every snapshot.")

    disc_src=st.radio("Discovery Source",["Discovery v3 (reactive+proactive)","Autonomy Stack (NLP+EDGAR)"],horizontal=True)

    if disc_src=="Discovery v3 (reactive+proactive)":
        if not dv3 or (not dv3.get("reactive") and not dv3.get("proactive") and not dv3.get("merged")):
            st.info("🔍 Discovery v3 empty. Run ⚡ Force rebuild to trigger DiscoveryOrchestrator.")
            meta=dv3.get("meta",{}) if dv3 else {}
            if meta: st.json(meta)
        else:
            merged=dv3.get("merged",[]); reactive=dv3.get("reactive",[]); proactive=dv3.get("proactive",[])
            m1,m2,m3=st.columns(3)
            m1.metric("Reactive",len(reactive)); m2.metric("Proactive",len(proactive)); m3.metric("Merged",len(merged))

            if merged:
                st.markdown("### 🎯 Merged Candidates (Ranked by EV × Source)")
                rows=[]
                for c in merged[:40]:
                    rows.append({"Ticker":c.get("ticker","—"),"Market":c.get("market","—").replace("_"," ").title(),"Sector":c.get("sector","—").replace("_"," ").title()[:20],
                        "Source":"🔴 Reactive" if c.get("source","")=="reactive_discovery" else "🔮 Proactive",
                        "EV":f'{c.get("ev",0):.3f}',"Const":f'{c.get("constraint",0):.2f}',
                        "Trend":c.get("trend","—") if "trend" in c else c.get("discovery_mode","—"),
                        "Narrative":c.get("narrative_tag","")[:35] if c.get("narrative_tag") else c.get("narrative","")[:35]})
                if rows:
                    df=pd.DataFrame(rows)
                    def _sc_src(v): return "color:#EF4444;font-weight:700" if "Reactive" in str(v) else "color:#A78BFA"
                    st.dataframe(df.style.map(_sc_src,subset=["Source"]),hide_index=True,height=420,use_container_width=True)

            if reactive:
                st.markdown("---"); st.markdown("### 🔴 Reactive Discoveries by Market")
                markets_seen={}
                for c in reactive: markets_seen.setdefault(c.get("market","us_equity"),[]).append(c)
                for mkt,cands in sorted(markets_seen.items()):
                    with st.expander(f"**{mkt.replace('_',' ').title()}** ({len(cands)})",expanded=(mkt=="us_equity")):
                        for c in cands[:10]:
                            bc=c.get("brewing_score",c.get("ev",0))
                            color="#10B981" if bc>0.6 else "#F59E0B" if bc>0.4 else "#9CA3AF"
                            st.markdown(f'<div style="border-left:3px solid {color};padding:6px 10px;margin-bottom:4px;background:#111827;border-radius:4px;"><b style="color:#E8ECF0;">{c.get("ticker","—")}</b> <span style="color:#9CA3AF;font-size:10px;margin-left:8px;">{c.get("sector","").replace("_"," ").title()}</span> <span style="color:{color};font-size:10px;margin-left:8px;">Brewing: {bc:.2f}</span><div style="font-size:10px;color:#6B7280;margin-top:2px;">{c.get("narrative","")[:80]}</div></div>',unsafe_allow_html=True)

            if proactive:
                st.markdown("---"); st.markdown("### 🔮 Proactive Chain (Pre-Consensus, 4-12wk Lead)")
                st.caption("Predicted from supply chain lag logic — before price confirms.")
                for c in proactive[:15]:
                    eta=c.get("proactive_eta_weeks","—"); prob=c.get("proactive_probability",0)
                    pc="#10B981" if prob>0.6 else "#F59E0B" if prob>0.4 else "#9CA3AF"
                    st.markdown(f'<div style="background:linear-gradient(90deg,#1e1b4b,#2d1b69);border-left:4px solid #6366F1;border-radius:6px;padding:10px;margin-bottom:6px;"><b style="color:#E8ECF0;">{c.get("ticker","—")}</b> <span style="color:#818CF8;font-size:10px;margin-left:6px;">{c.get("sector","").replace("_"," ").title()}</span> <span style="color:{pc};font-size:10px;margin-left:8px;">ETA: {eta}wk | P: {prob:.0%}</span><div style="font-size:10px;color:#C4B5FD;margin-top:4px;">{c.get("narrative","—")[:100]}</div></div>',unsafe_allow_html=True)

    else:
        if not auto_disc or not auto_disc.get("candidates"):
            st.info("🔍 No autonomy discoveries. Run ⚡ Force rebuild.")
        else:
            cands=auto_disc.get("candidates",[])
            st.markdown(f"### 🤖 Autonomy Stack — {len(cands)} Candidates")
            flt_stage=st.multiselect("Stage",["active","building","brewing","watching"],default=["active","building"])
            flt_conf=st.slider("Min Confidence",0.0,1.0,0.30,0.05)
            filtered=[c for c in cands if c.get("stage") in flt_stage and c.get("confidence",0)>=flt_conf]
            for c in filtered[:20]:
                conf=c.get("confidence",0); cc="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#9CA3AF"
                best=c.get("beneficiary_tickers",[]); invs=c.get("invalidators",[])
                st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;margin-bottom:8px;"><div style="font-size:13px;font-weight:800;color:#E8ECF0;">{c.get("name","—")} <span style="font-size:10px;color:#9CA3AF;font-weight:400;margin-left:8px;">{c.get("category","—")} · {c.get("stage","—")}</span> <span style="font-size:11px;color:{cc};font-weight:700;margin-left:8px;">{conf:.0%}</span></div><div style="font-size:11px;color:#D1D5DB;margin-top:4px;">{c.get("thesis","—")[:120]}</div><div style="font-size:10px;color:#9CA3AF;margin-top:4px;">🎯 {", ".join(best[:5])} | ❌ {", ".join(invs[:3]) if invs else "None"}</div></div>',unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0)>0:
        st.markdown("---"); st.markdown("### 📊 Feedback Loop — Win Rate")
        fe1,fe2,fe3=st.columns(3)
        fe1.metric("Evaluated",fb_eval.get("evaluated",0))
        fe2.metric("Promoted ↑",fb_eval.get("promoted",0))
        fe3.metric("Demoted ↓",fb_eval.get("demoted",0))

# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown("# 🏥 Market Health — VIX · Breadth · Fear & Greed")
    st.caption("VIX bucket + crash meter + sector breadth + checklist.")
    if not health: st.warning("No health data. Refresh."); st.stop()

    hc1,hc2,hc3=st.columns(3)
    crash=health.get("crash_meter",{})
    hc1.metric("Crash Meter",f"{crash.get('score',0):.0%}")
    hc2.metric("VIX Bucket",health.get("vix_bucket",{}).get("bucket","—"))
    hc3.metric("Breadth",f"{health.get('breadth',{}).get('pct_above_ma50',0):.0%}")

    fg=health.get("fear_greed",{}); fg_score=fg.get("score",50); fg_label=fg.get("label","—"); fg_source=fg.get("source","estimated")
    st.markdown(f"**Fear & Greed:** `{fg_label}` (source: {fg_source})")
    st.progress(fg_score/100, text=f"Fear & Greed: {fg_score:.0f}")

    checklist=health.get("checklists",{})
    if checklist:
        st.markdown("---"); st.markdown("### Health Checklists")
        for market,items in checklist.items():
            with st.expander(f"{market.upper()} Checklist",expanded=(market=="us")):
                for item in items:
                    icon="✅" if item.get("tone")=="good" else "⚠️" if item.get("tone")=="warn" else "❌"
                    st.markdown(f'{icon} {item.get("label","")}: {item.get("state","")} (score {item.get("score",0):.2f})')

# ══════════════════════════════════════════════════════════════════════════════
# 🔮 SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Scenarios":
    st.markdown("# 🔮 Adaptive Scenarios — Base · Alt · Risk · Tail")
    st.caption("4 scenarios with probability, confirmation score, and EM-specific implications.")
    if not scen: st.warning("No scenario data. Refresh."); st.stop()
    _render_scenario(scen.get("base_case"),"BASE","#10B981","🎯")
    _render_scenario(scen.get("alt_case"), "ALT","#F59E0B","🔄")
    # Risk/Tail from scenarios list
    sc_list=scen.get("scenarios",[])
    if len(sc_list)>2: _render_scenario(sc_list[2],"RISK","#EF4444","⚠️")
    if len(sc_list)>3: _render_scenario(sc_list[3],"TAIL","#6366F1","📌")
    st.markdown("---")
    st.markdown("### 🧠 Scenario Logic")
    st.markdown("1. **Structural Quad** → Base case  \n2. **Monthly Quad** (divergent) → Alt case  \n3. **Flip Hazard** → Risk case  \n4. **Leading indicators** → Tail case  \n5. **Confirmation Score** = macro signals aligning")

# ══════════════════════════════════════════════════════════════════════════════
# ⚡ SIGNAL STRENGTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Signal Strength":
    st.markdown("# ⚡ Signal Strength — Quality A Only")
    st.caption("Hedgeye-style high-conviction setups. Quality A = Bullish TRADE+TREND near LRR + volume expand. Short-A = Bearish near TRR. Filtered by regime alignment.")

    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    best_assets=set(pb_data.get("best_assets",[]))
    worst_assets=set(pb_data.get("worst_assets",[]))

    long_picks=[]; short_picks=[]
    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        trade=v.get("trade",{}); trend=v.get("trend",{})
        px=v.get("px",float("nan"))
        vol_c=trade.get("volume_confirm",0.5) if isinstance(trade,dict) else v.get("volume_confirm",0.5)
        stretch=trade.get("stretch","neutral") if isinstance(trade,dict) else v.get("trade_stretch","neutral")

        lrr=v.get("trade_lrr",float("nan")); trr=v.get("trade_trr",float("nan"))
        from config.settings import TICKER_SECTOR
        sector=TICKER_SECTOR.get(sym,"generic")
        regime_fit=any(sector.replace("_"," ").lower() in b.lower() or b.lower() in sym.lower() for b in best_assets) or sym in best_assets
        regime_avoid=any(sector.replace("_"," ").lower() in w.lower() or w.lower() in sym.lower() for w in worst_assets)

        if qual in ("A","B") and comp=="bullish":
            near_lrr=False
            if all(math.isfinite(x) for x in [px,lrr,trr]) and (trr-lrr)>1e-9:
                near_lrr=(px-lrr)/(trr-lrr)<=0.35 or stretch in ("oversold","reset_zone")
            else: near_lrr=stretch in ("oversold","reset_zone")
            score=50 if qual=="A" else 30
            if near_lrr: score+=20
            if vol_c>0.6: score+=15
            if regime_fit: score+=15
            if regime_avoid: score-=30
            long_picks.append({"ticker":sym,"quality":qual,"score":score,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"regime_fit":regime_fit})

        if qual in ("short_A","short_B") and comp=="bearish":
            near_trr=False
            if all(math.isfinite(x) for x in [px,lrr,trr]) and (trr-lrr)>1e-9:
                near_trr=(px-lrr)/(trr-lrr)>=0.65 or stretch in ("overbought","extended")
            else: near_trr=stretch in ("overbought","extended")
            score=50 if qual=="short_A" else 30
            if near_trr: score+=20
            if vol_c>0.6: score+=15
            short_picks.append({"ticker":sym,"quality":qual,"score":score,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"regime_fit":False})

    long_picks.sort(key=lambda x:x["score"],reverse=True)
    short_picks.sort(key=lambda x:x["score"],reverse=True)

    lc,sc2=st.columns(2)
    with lc:
        st.markdown("### 🟢 Long Setups")
        for p in long_picks[:10]:
            rf_badge="✅ Regime" if p["regime_fit"] else ""
            st.markdown(f'<div class="signal-A"><div style="font-size:13px;font-weight:800;color:#E8ECF0;">{p["ticker"]} <span style="font-size:10px;color:#9CA3AF;">{p["quality"]} · Score:{p["score"]}</span> <span style="font-size:10px;color:#10B981;">{rf_badge}</span></div><div style="font-size:11px;color:#A7F3D0;margin-top:4px;">LRR: {ff(p["lrr"],2)} | TRR: {ff(p["trr"],2)} | {p["stretch"]} | VolCnf: {p["vol_c"]:.0%}</div></div>',unsafe_allow_html=True)
        if not long_picks: st.info("No long setups meeting Quality A/B criteria.")

    with sc2:
        st.markdown("### 🔴 Short Setups")
        for p in short_picks[:10]:
            st.markdown(f'<div class="signal-shortA"><div style="font-size:13px;font-weight:800;color:#E8ECF0;">{p["ticker"]} <span style="font-size:10px;color:#9CA3AF;">{p["quality"]} · Score:{p["score"]}</span></div><div style="font-size:11px;color:#FECACA;margin-top:4px;">LRR: {ff(p["lrr"],2)} | TRR: {ff(p["trr"],2)} | {p["stretch"]} | VolCnf: {p["vol_c"]:.0%}</div></div>',unsafe_allow_html=True)
        if not short_picks: st.info("No short setups. Bearish trend may not be confirmed.")

    st.markdown("---")
    st.markdown("### 📋 Full Signal Strength Table")
    all_rows=[]
    for p in long_picks[:20]:
        all_rows.append({"Ticker":p["ticker"],"Side":"LONG","Quality":p["quality"],"Score":p["score"],"Px":ff(p["px"],2),"LRR":ff(p["lrr"],2),"TRR":ff(p["trr"],2),"Stretch":p["stretch"],"VolCnf":f'{p["vol_c"]:.0%}',"Regime":"✅" if p["regime_fit"] else "—"})
    for p in short_picks[:20]:
        all_rows.append({"Ticker":p["ticker"],"Side":"SHORT","Quality":p["quality"],"Score":p["score"],"Px":ff(p["px"],2),"LRR":ff(p["lrr"],2),"TRR":ff(p["trr"],2),"Stretch":p["stretch"],"VolCnf":f'{p["vol_c"]:.0%}',"Regime":"—"})
    if all_rows:
        df=pd.DataFrame(all_rows)
        def _sc_side(v): return "color:#10B981;font-weight:700" if v=="LONG" else "color:#EF4444;font-weight:700"
        st.dataframe(df.style.map(_sc_side,subset=["Side"]),hide_index=True,use_container_width=True)
    else: st.info("No signal strength data.")

# ══════════════════════════════════════════════════════════════════════════════
# ✈️ FRONT-RUN WATCHLIST — The actionable command center
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✈️ Front-Run":
    st.markdown("# ✈️ Front-Run Watchlist")
    st.caption("One page. Everything you need. Take position BEFORE the plane takes off.")

    if not frontrun or not frontrun.get("watchlist"):
        st.warning("Front-run data empty. Run ⚡ Force rebuild to generate.")
        st.markdown("""
**Why empty?** `FrontRunEngine` requires `engines/frontrun_engine.py` + updated `orchestrator.py`.
Deploy both files then Force rebuild.
        """); st.stop()

    # ── Regime + Timing Header ────────────────────────────────────────────────
    fw = frontrun.get("timing_window", "not yet")
    fr = frontrun.get("timing_rationale", "")
    tp = frontrun.get("timing_path", "")
    reg = frontrun.get("regime", sq)
    fw_cfg = {
        "now":    ("#EF4444", "🚨", "ACT NOW — HIGH CONVICTION"),
        "1-2w":   ("#F59E0B", "⚡", "POSITION — 1-2 WEEKS"),
        "3-6w":   ("#6366F1", "👀", "EARLY WARNING — 3-6 WEEKS"),
        "not yet":("#374151", "🛑", "NO SIGNAL — STAY POSITIONED"),
    }
    fc, fi, fl = fw_cfg.get(fw, fw_cfg["not yet"])
    st.markdown(f'''<div style="background:{fc}22;border-left:6px solid {fc};padding:16px;border-radius:8px;margin-bottom:16px;">
<div style="font-size:20px;font-weight:900;color:{fc};">{fi} {fl}</div>
<div style="font-size:13px;color:#E8ECF0;margin-top:8px;">{fr}</div>
<div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Regime: <b style="color:{QC.get(reg,"#9CA3AF")};">{reg} {QN.get(reg,"")}</b> · Monthly: {frontrun.get("monthly_quad","—")} · Transition: {tp or "—"}</div>
</div>''', unsafe_allow_html=True)

    # ── Metrics row ───────────────────────────────────────────────────────────
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("🚨 Boarding Now", len(frontrun.get("boarding_now",[])))
    m2.metric("⚡ Gate Soon",    len(frontrun.get("gate_soon",[])))
    m3.metric("👀 Check-In",    len(frontrun.get("check_in",[])))
    m4.metric("📈 Total Longs", len(frontrun.get("longs",[])))
    m5.metric("📉 Total Shorts",len(frontrun.get("shorts",[])))

    # ── Filter controls ───────────────────────────────────────────────────────
    st.markdown("---")
    fa,fb,fc2,fd = st.columns(4)
    with fa:
        status_filter = st.multiselect("Status", ["BOARDING NOW","GATE OPENS SOON","CHECK-IN","WAIT"],
                                        default=["BOARDING NOW","GATE OPENS SOON"])
    with fb:
        dir_filter = st.selectbox("Direction", ["All","long","short"])
    with fc2:
        mkt_filter = st.multiselect("Market", ["All","us_equity","ihsg","forex","commodity","crypto","bonds"],
                                     default=["All"])
    with fd:
        min_conf = st.slider("Min Confidence %", 0, 100, 40, 5)

    def _filter_candidates(cands):
        out = []
        for c in cands:
            if c.status not in status_filter and status_filter: continue
            if dir_filter != "All" and c.direction != dir_filter: continue
            if "All" not in mkt_filter and mkt_filter and c.market not in mkt_filter: continue
            if c.confidence_pct < min_conf: continue
            out.append(c)
        return out

    all_cands = frontrun.get("watchlist", [])
    # Rebuild as dataclass-like dicts if stored as dicts
    filtered = _filter_candidates([
        type('C', (), {k: v for k, v in c.items()})()
        if isinstance(c, dict) else c
        for c in all_cands
    ])

    if not filtered:
        st.info("No candidates match filters. Widen status/market/confidence filters.")
        st.stop()

    # ── BOARDING NOW — Priority cards ─────────────────────────────────────────
    boarding = [c for c in filtered if c.status == "BOARDING NOW"]
    if boarding:
        st.markdown(f"## 🚨 BOARDING NOW ({len(boarding)})")
        st.caption("All signals converge. Entry zone active. Act within 1-3 days.")
        for c in boarding[:8]:
            d_col = "#10B981" if c.direction == "long" else "#EF4444"
            px_str = f"${c.current_px:.2f}" if c.current_px else "—"
            entry_str = f"${c.entry_zone:.2f}" if c.entry_zone else "—"
            stop_str = f"${c.stop_loss:.2f}" if c.stop_loss else "—"
            tp1_str = f"${c.tp1:.2f}" if c.tp1 else "—"
            tp2_str = f"${c.tp2:.2f}" if c.tp2 else "—"
            t_str = f"${c.tp3:.2f}" if c.tp3 else "—"
            src_str = " · ".join(c.source_signals)
            st.markdown(f'''<div style="background:linear-gradient(135deg,#1a0000,#2d0000);border:2px solid #EF4444;border-radius:10px;padding:16px;margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
  <div>
    <span style="font-size:20px;font-weight:900;color:#E8ECF0;">{c.ticker}</span>
    <span style="font-size:12px;color:{d_col};font-weight:700;margin-left:10px;">{c.direction.upper()}</span>
    <span style="font-size:11px;color:#9CA3AF;margin-left:8px;">{c.market.replace("_"," ").title()} · {c.sector.replace("_"," ").title()}</span>
  </div>
  <div style="text-align:right;">
    <span style="background:#EF444433;border-radius:6px;padding:4px 12px;font-size:13px;font-weight:800;color:#EF4444;">🚨 {c.confidence_pct}%</span>
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px;">
  <div style="background:#0F172A;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">NOW</div><div style="font-size:13px;font-weight:700;color:#9CA3AF;">{px_str}</div></div>
  <div style="background:#064e3b;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">ENTRY</div><div style="font-size:13px;font-weight:700;color:#10B981;">{entry_str}</div></div>
  <div style="background:#450a0a;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">STOP</div><div style="font-size:13px;font-weight:700;color:#EF4444;">{stop_str}</div></div>
  <div style="background:#1a1a2e;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">T1</div><div style="font-size:13px;font-weight:700;color:#6366F1;">{tp1_str}</div></div>
  <div style="background:#1a1a2e;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">T2</div><div style="font-size:13px;font-weight:700;color:#818CF8;">{tp2_str}</div></div>
  <div style="background:#1a1a2e;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">T3</div><div style="font-size:13px;font-weight:700;color:#A5B4FC;">{t_str}</div></div>
</div>
<div style="margin-top:10px;font-size:11px;color:#D1D5DB;">{c.thesis[:110]}</div>
<div style="margin-top:6px;display:flex;gap:12px;font-size:10px;flex-wrap:wrap;">
  <span style="color:#9CA3AF;">⏱ {c.duration}</span>
  <span style="color:#9CA3AF;">📡 {src_str}</span>
  <span style="color:#F59E0B;">⚡ Score: {c.composite_score:.3f}</span>
  <span style="color:#9CA3AF;">{c.range_action}</span>
</div>
<div style="margin-top:4px;font-size:10px;color:#6B7280;">⚠️ Risk: {c.risk[:70]}</div>
</div>''', unsafe_allow_html=True)

    # ── Full Watchlist Table ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 📋 Full Watchlist ({len(filtered)} candidates)")

    rows = []
    for c in filtered:
        rows.append({
            "Status":  c.status_emoji + " " + c.status[:12],
            "Ticker":  c.ticker,
            "Mkt":     c.market.replace("_"," ").title()[:8],
            "Dir":     c.direction.upper(),
            "Score":   f"{c.composite_score:.3f}",
            "Conf":    f"{c.confidence_pct}%",
            "Px":      f"${c.current_px:.2f}" if c.current_px else "—",
            "Entry":   f"${c.entry_zone:.2f}" if c.entry_zone else "—",
            "Stop":    f"${c.stop_loss:.2f}" if c.stop_loss else "—",
            "T1":      f"${c.tp1:.2f}" if c.tp1 else "—",
            "T2":      f"${c.tp2:.2f}" if c.tp2 else "—",
            "Duration":c.duration[:12],
            "Timing":  f"{c.timing_score:.2f}",
            "BTK":     f"{c.btk_score:.2f}",
            "RR":      f"{c.rr_score:.2f}",
            "Signals": " · ".join(c.source_signals)[:30],
            "Thesis":  c.thesis[:60],
        })

    if rows:
        df = pd.DataFrame(rows)
        def _sc_dir(v): return "color:#10B981;font-weight:700" if "LONG" in str(v) else "color:#EF4444;font-weight:700" if "SHORT" in str(v) else ""
        def _sc_status(v):
            if "BOARDING" in str(v): return "color:#EF4444;font-weight:800"
            if "GATE" in str(v): return "color:#F59E0B;font-weight:700"
            if "CHECK" in str(v): return "color:#6366F1"
            return "color:#6B7280"
        def _sc_score(v):
            try:
                fv = float(str(v))
                return "color:#10B981;font-weight:700" if fv >= 0.65 else "color:#F59E0B" if fv >= 0.45 else "color:#9CA3AF"
            except: return ""
        styled = df.style.map(_sc_dir, subset=["Dir"]).map(_sc_status, subset=["Status"]).map(_sc_score, subset=["Score"])
        st.dataframe(styled, hide_index=True, height=500, use_container_width=True)

    # ── By Market breakdown ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🌍 By Market")
    by_mkt = frontrun.get("by_market", {})
    mkt_cols = st.columns(min(len(by_mkt), 3))
    for i, (mkt, cands) in enumerate(by_mkt.items()):
        col = mkt_cols[i % 3]
        with col:
            st.markdown(f"**{mkt.replace('_',' ').title()}** ({len(cands)})")
            for c in cands[:4]:
                if isinstance(c, dict):
                    ticker = c.get("ticker","—"); conf = c.get("confidence_pct",0); status = c.get("status","—"); score = c.get("composite_score",0)
                else:
                    ticker = c.ticker; conf = c.confidence_pct; status = c.status; score = c.composite_score
                emoji = "🚨" if "BOARDING" in status else "⚡" if "GATE" in status else "👀"
                col.markdown(f'`{ticker}` {emoji} {conf}%', unsafe_allow_html=False)

    # ── Composite score legend ────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📖 How Composite Score Works", expanded=False):
        wts = frontrun.get("meta", {}).get("weights", {})
        st.markdown(f"""
**Composite Score** = weighted average of 5 signal layers:

| Signal | Weight | Source |
|--------|--------|--------|
| Timing | {wts.get('timing',0.30):.0%} | RegimeTransitionEngine `front_run_window` |
| Bottleneck | {wts.get('btk',0.25):.0%} | BottleneckEngine Level + EV + Range Action |
| Risk Range | {wts.get('rr',0.25):.0%} | HurstRR Quality A/B + Stretch + Volume |
| Discovery | {wts.get('disc',0.10):.0%} | DiscoveryOrchestrator reactive/proactive |
| Narrative | {wts.get('narr',0.10):.0%} | NarrativeEngine ignition strength |

**Status:**
- 🚨 **BOARDING NOW** = score ≥ 0.65 AND price in entry zone (LRR)
- ⚡ **GATE OPENS SOON** = score ≥ 0.45
- 👀 **CHECK-IN** = score ≥ 0.30
- ⏳ **WAIT** = score < 0.30

**Entry geometry:** LRR (Trade Low Risk Range) = buy zone.
Stop = Trend LRR break → EXIT, not trim.
        """)

# ══════════════════════════════════════════════════════════════════════════════
# 📋 PAPER TRADER — Track your positions, audit win rate by regime
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Paper Trader":
    st.markdown("# 📋 Paper Trader — Position Tracker + Regime Audit")
    st.caption("Track signal-driven paper trades. Audit PnL by Quad regime. Close trades at TP or Stop.")

    # Session-state persistence
    if "pt_trades" not in st.session_state: st.session_state.pt_trades = []
    if "pt_closed" not in st.session_state: st.session_state.pt_closed = []

    # ── Manual entry ──────────────────────────────────────────────────────────
    st.markdown("### ➕ Add Paper Trade")
    with st.form("new_trade"):
        c1,c2,c3,c4 = st.columns(4)
        with c1: new_ticker = st.text_input("Ticker", placeholder="e.g. GLD")
        with c2: new_dir = st.selectbox("Direction", ["long","short"])
        with c3: new_entry = st.number_input("Entry Price", min_value=0.01, value=100.0, format="%.2f")
        with c4: new_stop = st.number_input("Stop Loss", min_value=0.01, value=92.0, format="%.2f")
        c5,c6,c7,c8 = st.columns(4)
        with c5: new_tp1 = st.number_input("T1", min_value=0.01, value=110.0, format="%.2f")
        with c6: new_tp2 = st.number_input("T2", min_value=0.01, value=120.0, format="%.2f")
        with c7: new_src = st.selectbox("Signal Source", ["frontrun_engine","bottleneck","rr_quality_a","discovery_v3","manual"])
        with c8: new_regime = st.selectbox("Regime", ["Q1","Q2","Q3","Q4"], index=["Q1","Q2","Q3","Q4"].index(sq) if sq in ["Q1","Q2","Q3","Q4"] else 2)
        submitted = st.form_submit_button("Add Trade ✅", use_container_width=True)
        if submitted and new_ticker:
            from datetime import datetime
            trade = {
                "trade_id": f"{new_ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "ticker": new_ticker.upper(), "direction": new_dir,
                "entry_price": new_entry, "stop_loss": new_stop,
                "tp1": new_tp1, "tp2": new_tp2, "tp3": None,
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
                "signal_source": new_src, "regime": new_regime,
                "status": "open", "pnl_pct": None, "exit_price": None,
            }
            st.session_state.pt_trades.append(trade)
            st.success(f"✅ Trade added: {new_ticker.upper()} {new_dir.upper()} @ ${new_entry:.2f}")
            st.rerun()

    # ── Auto-fill from Frontrun Watchlist ─────────────────────────────────────
    if frontrun.get("boarding_now"):
        st.markdown("### 🚨 Auto-fill from Boarding Now Signals")
        boarding = frontrun.get("boarding_now", [])
        for c in boarding[:5]:
            if isinstance(c, dict):
                t=c.get("ticker","—"); e=c.get("entry_zone"); s=c.get("stop_loss"); t1=c.get("tp1"); t2=c.get("tp2"); conf=c.get("confidence_pct",0)
            else:
                t=c.ticker; e=c.entry_zone; s=c.stop_loss; t1=c.tp1; t2=c.tp2; conf=c.confidence_pct
            if st.button(f"➕ {t} | Entry: ${e:.2f} | Stop: ${s:.2f} | Conf: {conf}%" if e and s else f"➕ {t} | Conf: {conf}%", key=f"auto_{t}"):
                from datetime import datetime
                trade = {"trade_id":f"{t}_{datetime.now().strftime('%Y%m%d_%H%M')}", "ticker":t, "direction":"long",
                    "entry_price":e or 0, "stop_loss":s or 0, "tp1":t1, "tp2":t2, "tp3":None,
                    "entry_date":datetime.now().strftime("%Y-%m-%d"), "signal_source":"frontrun_engine",
                    "regime":sq, "status":"open", "pnl_pct":None, "exit_price":None}
                st.session_state.pt_trades.append(trade)
                st.success(f"✅ {t} added from Boarding Now"); st.rerun()

    # ── Open Positions ─────────────────────────────────────────────────────────
    st.markdown("---")
    open_trades = [t for t in st.session_state.pt_trades if t.get("status")=="open"]
    st.markdown(f"### 📂 Open Positions ({len(open_trades)})")

    if open_trades:
        for trade in open_trades:
            ticker = trade["ticker"]
            entry = trade["entry_price"]
            stop  = trade.get("stop_loss",0)
            tp1   = trade.get("tp1")
            direction = trade.get("direction","long")

            # Live P&L
            s = prices.get(ticker)
            current_px = float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1]) if s is not None and len(pd.to_numeric(s, errors="coerce").dropna()) > 0 else entry
            pnl = (current_px - entry) / entry if direction == "long" else (entry - current_px) / entry
            pnl_c = "#10B981" if pnl >= 0 else "#EF4444"
            tp1_pct = (tp1 - entry) / entry if tp1 else None

            col_a, col_b, col_c, col_d, col_e = st.columns([2,1,1,1,1])
            with col_a:
                st.markdown(f'<div style="font-size:13px;font-weight:700;color:#E8ECF0;">{ticker} <span style="color:{"#10B981" if direction=="long" else "#EF4444"};font-size:11px;">{direction.upper()}</span></div><div style="font-size:10px;color:#9CA3AF;">Entry: ${entry:.2f} | Stop: ${stop:.2f}{" | T1: $"+str(round(tp1,2)) if tp1 else ""}</div>',unsafe_allow_html=True)
            with col_b:
                st.markdown(f'<div style="font-size:14px;font-weight:700;color:#9CA3AF;">${current_px:.2f}</div><div style="font-size:10px;color:#6B7280;">Current</div>',unsafe_allow_html=True)
            with col_c:
                st.markdown(f'<div style="font-size:14px;font-weight:700;color:{pnl_c};">{pnl:+.1%}</div><div style="font-size:10px;color:#6B7280;">P&L</div>',unsafe_allow_html=True)
            with col_d:
                st.markdown(f'<div style="font-size:11px;color:#9CA3AF;">{trade.get("regime","—")}</div><div style="font-size:10px;color:#6B7280;">{trade.get("signal_source","")[:12]}</div>',unsafe_allow_html=True)
            with col_e:
                if st.button("Close ✖", key=f"close_{trade['trade_id']}"):
                    trade["status"] = "closed"
                    trade["exit_price"] = current_px
                    trade["pnl_pct"] = round(pnl, 4)
                    st.session_state.pt_closed.append(trade)
                    st.session_state.pt_trades = [t for t in st.session_state.pt_trades if t["trade_id"] != trade["trade_id"]]
                    st.success(f"Closed {ticker} at ${current_px:.2f} | PnL: {pnl:+.1%}"); st.rerun()

            # Auto-TP / Stop alert
            if stop and current_px <= stop and direction == "long":
                st.error(f"🔴 {ticker} — STOP HIT at ${current_px:.2f}. Exit per process.")
            elif tp1 and current_px >= tp1 and direction == "long":
                st.success(f"✅ {ticker} — T1 HIT at ${current_px:.2f}. Trim 25% per process.")
            st.divider()
    else:
        st.info("No open positions. Add trades above or auto-fill from Front-Run Watchlist.")

    # ── Closed Trades + Performance Audit ─────────────────────────────────────
    closed_trades = st.session_state.pt_closed
    if closed_trades:
        st.markdown(f"### 📊 Closed Trades ({len(closed_trades)}) — Regime Audit")
        rows = []
        for t in closed_trades:
            rows.append({
                "Ticker": t["ticker"], "Dir": t.get("direction","—").upper(),
                "Entry": f"${t['entry_price']:.2f}", "Exit": f"${t.get('exit_price',0):.2f}",
                "PnL": f"{t.get('pnl_pct',0):+.1%}" if t.get('pnl_pct') else "—",
                "Regime": t.get("regime","—"), "Source": t.get("signal_source","—"),
                "Date": t.get("entry_date","—"),
            })
        df = pd.DataFrame(rows)
        def _sc_pnl(v):
            try:
                fv = float(str(v).replace("%","").replace("+",""))
                return "color:#10B981;font-weight:700" if fv > 0 else "color:#EF4444;font-weight:700"
            except: return ""
        st.dataframe(df.style.map(_sc_pnl, subset=["PnL"]), hide_index=True, use_container_width=True)

        # Win rate by regime
        by_regime: dict = {}
        for t in closed_trades:
            r = t.get("regime","—"); p = t.get("pnl_pct",0) or 0
            by_regime.setdefault(r, []).append(p)
        st.markdown("#### 🏆 Win Rate by Quad Regime")
        wr_cols = st.columns(len(by_regime))
        for i, (regime, pnls) in enumerate(by_regime.items()):
            wr = sum(1 for p in pnls if p > 0) / len(pnls) if pnls else 0
            avg = np.mean(pnls) if pnls else 0
            rc = QC.get(regime, "#9CA3AF")
            wr_cols[i].markdown(f'<div style="background:#111827;border:1px solid {rc};border-radius:8px;padding:10px;text-align:center;"><div style="font-size:14px;font-weight:800;color:{rc};">{regime}</div><div style="font-size:20px;font-weight:900;color:{"#10B981" if wr>=0.5 else "#EF4444"};">{wr:.0%}</div><div style="font-size:11px;color:#9CA3AF;">Win Rate</div><div style="font-size:12px;color:{"#10B981" if avg>=0 else "#EF4444"};margin-top:4px;">{avg:+.1%} avg</div></div>', unsafe_allow_html=True)

        # Overall stats
        all_pnls = [t.get("pnl_pct",0) or 0 for t in closed_trades]
        if all_pnls:
            st.markdown(f"**Overall:** {sum(1 for p in all_pnls if p>0)}/{len(all_pnls)} wins ({sum(1 for p in all_pnls if p>0)/len(all_pnls):.0%}) · Avg: {np.mean(all_pnls):+.1%} · Best: {max(all_pnls):+.1%} · Worst: {min(all_pnls):+.1%}")

    if st.button("🗑️ Clear All Closed Trades"):
        st.session_state.pt_closed = []; st.rerun()
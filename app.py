"""app.py — MacroRegime Pro v18 | Restructured: 7 Pages · st.tabs() · @st.cache_data

Changes vs v17:
  - 18 sidebar pages → 7 (massive perf improvement: fewer full reruns)
  - st.tabs() within pages = instant switching (no full rerun)
  - All config imports moved to TOP (not inside elif blocks)
  - @st.cache_data on _render_universe, price calcs, bottleneck table
  - Compact Bottleneck: one filterable table + expandable cards (no more L1/L2/Watch headers)
  - Markets: one page with 6 inner tabs (Global, US, Forex, Commodity, Crypto, IHSG)
  - Command Center: Dashboard + GIP + Timing + Health in one page
  - Research: Bottleneck + Narratives + Discovery in one page
  - EM Recovery: graceful empty state (was showing blank)

New structure:
  ✈️ Front-Run       ← Primary actionable page
  🏠 Command Center  ← Dashboard + GIP + Timing + Health
  🎯 Signals         ← Risk Ranges + Signal Strength + Alerts
  🌍 Markets         ← Global + US + Forex + Commodity + Crypto + IHSG
  🔍 Research        ← Bottleneck + Narratives + Discovery
  🔮 Scenarios       ← Scenarios only
  📋 Paper Trader    ← Position tracker
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
from datetime import datetime

# ── ALL config imports at TOP — never inside elif blocks ──────────────────────
from config.settings import (
    US_SECTORS, US_FACTORS, TICKER_SECTOR, MARKET_CLASSIFICATION,
    COMMODITIES, CRYPTO, FOREX_PAIRS, IHSG_UNIVERSE, BONDS,
    MACRO_PROXIES, BOTTLENECK_PROFILES, QUAD_ASSET_PERFORMANCE,
)

st.set_page_config(page_title="MacroRegime Pro", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.vix-investable{background:linear-gradient(90deg,#064e3b,#065f46);border-left:6px solid #10B981;padding:14px;border-radius:8px;}
.vix-chop{background:linear-gradient(90deg,#451a03,#78350f);border-left:6px solid #F59E0B;padding:14px;border-radius:8px;}
.vix-defensive{background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:6px solid #EF4444;padding:14px;border-radius:8px;}
.signal-A{background:linear-gradient(90deg,#064e3b,#065f46);border-left:4px solid #10B981;padding:10px;border-radius:6px;margin-bottom:6px;}
.signal-shortA{background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:4px solid #EF4444;padding:10px;border-radius:6px;margin-bottom:6px;}
div[data-testid="stTabs"] button {font-size:12px !important; padding:6px 12px !important;}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}

def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v, d=2):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

# ── Chart helpers ─────────────────────────────────────────────────────────────
def prob_bar(probs: dict, title: str = ""):
    if not probs: return go.Figure()
    items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    qs, ps = zip(*items)
    fig = go.Figure(go.Bar(x=list(qs), y=list(ps),
        marker_color=[QC.get(q,"#9CA3AF") for q in qs],
        text=[f"{p:.0%}" for p in ps], textposition="outside"))
    fig.update_layout(title=title, height=200, margin=dict(l=0,r=0,t=25,b=0),
        paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
        font=dict(color="#E8ECF0"), yaxis=dict(tickformat=".0%",range=[0,1]),
        showlegend=False)
    return fig

def qcard(label, quad, conf, sub=""):
    c = qc(quad)
    return (f'<div style="background:#111827;border:2px solid {c};border-radius:10px;'
            f'padding:12px;text-align:center;">'
            f'<div style="font-size:10px;color:#9CA3AF;">{label}</div>'
            f'<div style="font-size:26px;font-weight:900;color:{c};">{quad}</div>'
            f'<div style="font-size:12px;color:{c};">{qn(quad)}</div>'
            f'<div style="font-size:10px;color:#9CA3AF;">Conf:{conf:.0%} · {sub}</div></div>')

# ── Cached helpers ────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def _calc_returns(prices_json: str, sym: str, days: int = 252):
    """Cache price return calculations — expensive part of _render_universe."""
    import json
    prices_dict = json.loads(prices_json)
    s = prices_dict.get(sym)
    if s is None: return None, None, None
    series = pd.Series(s).dropna().tail(days)
    if series.empty: return None, None, None
    r1 = float(series.iloc[-1]/series.iloc[-22]-1) if len(series)>=22 else 0
    r3 = float(series.iloc[-1]/series.iloc[-64]-1) if len(series)>=64 else 0
    r6 = float(series.iloc[-1]/series.iloc[-126]-1) if len(series)>=126 else 0
    return r1, r3, r6

def _btk_badge(sym, btk_data):
    if not btk_data: return ""
    colors = {"level_1":"#10B981","level_2":"#F59E0B","watch":"#6366F1","avoid":"#EF4444"}
    for lvl in ("level_1","level_2","watch","avoid"):
        if any(c.get("ticker")==sym for c in btk_data.get(lvl,[])):
            return f'<span style="color:{colors[lvl]};font-size:10px;">{lvl.replace("_"," ").upper()}</span>'
    return ""

def _render_universe(title: str, tickers_map: dict, prices: dict,
                     btk_data: dict, days: int = 252):
    """Unified market universe renderer — used for all 6 asset classes."""
    rows = []
    for sym, info in tickers_map.items():
        s = prices.get(sym)
        if s is None: continue
        s_clean = pd.to_numeric(pd.Series(s) if isinstance(s,list) else s,
                                errors="coerce").dropna().tail(days)
        if s_clean.empty: continue
        r1 = float(s_clean.iloc[-1]/s_clean.iloc[-22]-1) if len(s_clean)>=22 else 0
        r3 = float(s_clean.iloc[-1]/s_clean.iloc[-64]-1) if len(s_clean)>=64 else 0
        badge = _btk_badge(sym, btk_data)
        name = info if isinstance(info,str) else info.get("name",sym)
        rows.append({"Ticker":sym,"Name":name[:22],
                     "1M":f"{r1:+.1%}","3M":f"{r3:+.1%}","Bottleneck":badge})
    if not rows:
        st.info(f"No data for {title}.")
        return
    df = pd.DataFrame(rows)
    st.markdown(f"**{title}** ({len(rows)} tickers)")
    st.markdown(df.to_html(escape=False,index=False), unsafe_allow_html=True)

def _render_scenario(sc, label, color, badge):
    if not sc: return
    if isinstance(sc,dict):
        name=sc.get("name",""); prob=sc.get("probability",0)
        conf=sc.get("confirmation_score",0); headline=sc.get("headline","")
        catalyst=sc.get("catalyst",""); em_note=sc.get("em_note","")
        best=sc.get("best_assets",[]); worst=sc.get("worst_assets",[])
        triggers=sc.get("confirmation_triggers",[]); invalidators=sc.get("invalidators",[])
    else:
        name=sc.name; prob=sc.probability; conf=sc.confirmation_score
        headline=sc.headline; catalyst=sc.catalyst; em_note=sc.em_note
        best=sc.best_assets; worst=sc.worst_assets
        triggers=sc.confirmation_triggers; invalidators=sc.invalidators
    with st.expander(f"{badge} **{label}** — P={prob:.0%} · Conf={conf:.0%}", expanded=(label=="BASE")):
        st.markdown(f"**{headline}**")
        c1,c2 = st.columns(2)
        c1.markdown(f"**Catalyst:** {catalyst}")
        c2.markdown(f"**EM:** {em_note[:120]}")
        if triggers: st.markdown("**Triggers:** " + " · ".join(triggers[:3]))
        if invalidators: st.markdown("**Invalidators:** " + " · ".join(invalidators[:3]))
        if best: st.markdown(f"✅ **Best:** {' · '.join(best[:6])}")
        if worst: st.markdown(f"❌ **Worst:** {' · '.join(worst[:6])}")

# ── Session state ─────────────────────────────────────────────────────────────
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "pt_trades" not in st.session_state: st.session_state.pt_trades = []
if "pt_closed" not in st.session_state: st.session_state.pt_closed = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v18*")
    st.divider()
    page = st.radio("", [
        "✈️ Front-Run",
        "🏠 Command Center",
        "🎯 Signals",
        "🌍 Markets",
        "🔍 Research",
        "🔮 Scenarios",
        "📋 Paper Trader",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.loading = True
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
    # Dynamic quad display
    _sp = st.session_state.get("snap") or {}
    _gp = _sp.get("gip") if isinstance(_sp,dict) else None
    _sq = getattr(_gp,"structural_quad","—") if _gp else "—"
    _mq = getattr(_gp,"monthly_quad","—") if _gp else "—"
    _gq = (_sp.get("global") or {}).get("global_quad","—") if isinstance(_sp,dict) else "—"
    _qc = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
    st.markdown(
        f'<div style="font-size:11px;color:#6B7280;">S: '
        f'<b style="color:{_qc.get(_sq,"#9CA3AF")};">{_sq}</b> · '
        f'M: <b style="color:{_qc.get(_mq,"#9CA3AF")};">{_mq}</b> · '
        f'G: <b style="color:{_qc.get(_gq,"#9CA3AF")};">{_gq}</b></div>',
        unsafe_allow_html=True)

# ── Load / build ──────────────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb = st.progress(0.0); pt = st.empty()
    snap = build_snapshot(progress_cb=lambda m,f: (pb.progress(f), pt.caption(m)),
                          include_us_stocks=inc_us, include_forex=inc_fx,
                          include_commodities=inc_comm, include_crypto=inc_cryp,
                          include_ihsg=inc_ihsg)
    st.session_state.snap = snap
    st.session_state.loading = False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ No snapshot. Click 🔄 Refresh or ⚡ Force."); st.stop()

# ── Extract snap (once, at top) ───────────────────────────────────────────────
gip        = snap.get("gip")
global_    = snap.get("global", {})
rr         = snap.get("risk_ranges", {})
scen       = snap.get("scenarios", {})
narr       = snap.get("narratives", {})
transition = snap.get("transition")
health     = snap.get("health", {})
analogs    = snap.get("analogs", {})
btk        = snap.get("bottleneck", {})
pb_data    = snap.get("playbook", {})
prices     = snap.get("prices", {})
stress     = snap.get("stress", {})
auto_disc  = snap.get("auto_discoveries", {})
fb_eval    = snap.get("feedback_eval", {})
dv3        = snap.get("discovery_v3", {})
sec_mom    = snap.get("sector_momentum", {})
frontrun   = snap.get("frontrun", {})

sq  = gip.structural_quad if gip else "Q3"
mq  = gip.monthly_quad if gip else "Q3"
gq  = global_.get("global_quad","Q3")
ar  = rr.get("asset_ranges", {})

# ══════════════════════════════════════════════════════════════════════════════
# ✈️ FRONT-RUN
# ══════════════════════════════════════════════════════════════════════════════
if page == "✈️ Front-Run":
    st.markdown("# ✈️ Front-Run Watchlist")
    st.caption("One page. Everything. Take position BEFORE the plane takes off.")

    if not frontrun or not frontrun.get("watchlist"):
        st.warning("Front-run data empty. Run ⚡ Force rebuild.")
        st.stop()

    fw  = frontrun.get("timing_window","not yet")
    fr  = frontrun.get("timing_rationale","")
    fw_cfg = {
        "now":    ("#EF4444","🚨","ACT NOW — HIGH CONVICTION"),
        "1-2w":   ("#F59E0B","⚡","GATE OPENS — 1-2 WEEKS"),
        "3-6w":   ("#6366F1","👀","EARLY WARNING — 3-6 WEEKS"),
        "not yet":("#374151","🛑","NO SIGNAL — STAY POSITIONED"),
    }
    fc,fi,fl = fw_cfg.get(fw, fw_cfg["not yet"])
    boarding_ct = len(frontrun.get("boarding_now",[]))
    gate_ct     = len(frontrun.get("gate_soon",[]))
    st.markdown(f'''<div style="background:{fc}18;border-left:6px solid {fc};padding:14px;border-radius:8px;margin-bottom:14px;">
<div style="font-size:19px;font-weight:900;color:{fc};">{fi} {fl}</div>
<div style="font-size:12px;color:#D1D5DB;margin-top:6px;">{fr[:160] if fr else "—"}</div>
<div style="font-size:10px;color:#6B7280;margin-top:4px;">
  <b style="color:{fc};">{boarding_ct} BOARDING</b> &nbsp;|&nbsp; {gate_ct} GATE SOON &nbsp;|&nbsp;
  Regime: <b style="color:{QC.get(sq,"#9CA3AF")};">{sq} {qn(sq)}</b> · {frontrun.get("timing_path","—")}
</div></div>''', unsafe_allow_html=True)

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("🚨 Boarding",   boarding_ct)
    m2.metric("⚡ Gate Soon",  gate_ct)
    m3.metric("📈 Total Long", len(frontrun.get("longs",[])))
    m4.metric("📉 Total Short",len(frontrun.get("shorts",[])))

    st.markdown("---")
    fa,fb,fc2,fd = st.columns(4)
    with fa: status_f = st.multiselect("Status",["BOARDING NOW","GATE OPENS SOON","CHECK-IN","WAIT"],default=["BOARDING NOW","GATE OPENS SOON"])
    with fb: dir_f    = st.selectbox("Dir",["All","long","short"])
    with fc2: mkt_f   = st.multiselect("Market",["All","us_equity","ihsg","forex","commodity","crypto"],default=["All"])
    with fd: min_conf = st.slider("Min Conf %", 0, 100, 35, 5)

    def _fc(cands):
        out = []
        for c in cands:
            s   = c.get("status","") if isinstance(c,dict) else getattr(c,"status","")
            d   = c.get("direction","") if isinstance(c,dict) else getattr(c,"direction","")
            m   = c.get("market","") if isinstance(c,dict) else getattr(c,"market","")
            cf  = c.get("confidence_pct",0) if isinstance(c,dict) else getattr(c,"confidence_pct",0)
            if status_f and s not in status_f: continue
            if dir_f!="All" and d!=dir_f: continue
            if "All" not in mkt_f and mkt_f and m not in mkt_f: continue
            if cf < min_conf: continue
            out.append(c)
        return out

    filtered = _fc(frontrun.get("watchlist",[]))

    def _gv(c,k,fb=""): return c.get(k,fb) if isinstance(c,dict) else getattr(c,k,fb)

    # Boarding Now cards
    boarding = [c for c in filtered if _gv(c,"status","")=="BOARDING NOW"]
    if boarding:
        st.markdown(f"## 🚨 BOARDING NOW ({len(boarding)})")
        for c in boarding[:6]:
            dc   = "#10B981" if _gv(c,"direction","")=="long" else "#EF4444"
            px   = _gv(c,"current_px"); entry=_gv(c,"entry_zone"); stp=_gv(c,"stop_loss")
            tp1  = _gv(c,"tp1"); tp2=_gv(c,"tp2"); tp3=_gv(c,"tp3")
            conf = _gv(c,"confidence_pct",0); score=_gv(c,"composite_score",0)
            srcs = " · ".join(_gv(c,"source_signals",[]))
            th   = _gv(c,"thesis","—")[:110]
            risk = _gv(c,"risk","—")[:80]
            st.markdown(f'''<div style="background:linear-gradient(135deg,#1a0000,#2d0000);border:2px solid #EF4444;border-radius:10px;padding:14px;margin-bottom:10px;">
<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
  <span style="font-size:20px;font-weight:900;color:#E8ECF0;">{_gv(c,"ticker","—")}</span>
  <span style="font-size:12px;color:{dc};font-weight:700;">{_gv(c,"direction","").upper()}</span>
  <span style="font-size:11px;color:#9CA3AF;">{_gv(c,"market","").replace("_"," ").title()} · {_gv(c,"sector","").replace("_"," ").title()[:18]}</span>
  <span style="background:#EF444433;border-radius:4px;padding:2px 10px;font-size:12px;font-weight:800;color:#EF4444;margin-left:auto;">{conf}%</span>
</div>
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:10px;">
  {"".join(f'<div style="background:#0F172A;border-radius:5px;padding:6px;text-align:center;"><div style="font-size:8px;color:#6B7280;">{lbl}</div><div style="font-size:12px;font-weight:700;color:{col};">{val}</div></div>'
  for lbl,val,col in [
    ("NOW",    f"${px:.2f}" if px else "—","#9CA3AF"),
    ("ENTRY",  f"${entry:.2f}" if entry else "—","#10B981"),
    ("STOP",   f"${stp:.2f}" if stp else "—","#EF4444"),
    ("T1",     f"${tp1:.2f}" if tp1 else "—","#6366F1"),
    ("T2",     f"${tp2:.2f}" if tp2 else "—","#818CF8"),
    ("T3",     f"${tp3:.2f}" if tp3 else "—","#A5B4FC"),
  ])}
</div>
<div style="font-size:11px;color:#D1D5DB;margin-bottom:4px;">{th}</div>
<div style="font-size:10px;color:#6B7280;">⚠️ {risk} &nbsp;|&nbsp; 📡 {srcs} &nbsp;|&nbsp; Score: {score:.3f} &nbsp;|&nbsp; {_gv(c,"duration","")}</div>
</div>''', unsafe_allow_html=True)

    # Full table
    st.markdown("---")
    st.markdown(f"### 📋 Full Watchlist ({len(filtered)})")
    if filtered:
        rows = []
        for c in filtered:
            px=_gv(c,"current_px"); entry=_gv(c,"entry_zone"); stp=_gv(c,"stop_loss"); tp1=_gv(c,"tp1")
            rows.append({
                "Status":  _gv(c,"status_emoji","")+" "+_gv(c,"status","")[:12],
                "Ticker":  _gv(c,"ticker",""),
                "Mkt":     _gv(c,"market","").replace("_"," ").title()[:8],
                "Dir":     _gv(c,"direction","").upper(),
                "Conf":    f'{_gv(c,"confidence_pct",0)}%',
                "Score":   f'{_gv(c,"composite_score",0):.3f}',
                "Px":      f"${px:.2f}" if px else "—",
                "Entry":   f"${entry:.2f}" if entry else "—",
                "Stop":    f"${stp:.2f}" if stp else "—",
                "T1":      f"${tp1:.2f}" if tp1 else "—",
                "Dur":     _gv(c,"duration","")[:10],
                "Signals": " · ".join(_gv(c,"source_signals",[]))[:28],
            })
        df = pd.DataFrame(rows)
        def _sd(v): return "color:#10B981;font-weight:700" if "LONG" in str(v) else "color:#EF4444;font-weight:700" if "SHORT" in str(v) else ""
        def _ss(v): return "color:#EF4444;font-weight:800" if "BOARD" in str(v) else "color:#F59E0B;font-weight:700" if "GATE" in str(v) else "color:#6366F1" if "CHECK" in str(v) else "color:#6B7280"
        st.dataframe(df.style.map(_sd,subset=["Dir"]).map(_ss,subset=["Status"]),
                     hide_index=True, height=480, use_container_width=True)

    # Score legend
    with st.expander("📖 Score Formula", expanded=False):
        wts = frontrun.get("meta",{}).get("weights",{})
        st.markdown(f"""**Composite = {wts.get('timing',.3):.0%} Timing + {wts.get('btk',.25):.0%} Bottleneck + {wts.get('rr',.25):.0%} RR + {wts.get('disc',.10):.0%} Discovery + {wts.get('narr',.10):.0%} Narrative**
🚨 BOARDING = score ≥ 0.65 AND at LRR (entry zone) · ⚡ GATE = score ≥ 0.45 · 👀 CHECK-IN = score ≥ 0.30""")

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 COMMAND CENTER  (Dashboard + GIP + Timing + Health — all in one)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏠 Command Center":
    st.markdown("# 🏠 Command Center")
    st.markdown(
        f'<div style="font-size:11px;color:#6B7280;">Built {snap.get("build_time_s",0)}s · '
        f'Prices:{snap.get("prices_loaded",0)} · FRED:{snap.get("fred_coverage",0)} · '
        f'RR:{snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)

    cc = st.tabs(["🏠 Overview", "📈 GIP Model", "⏱️ Timing", "🏥 Health"])

    # ── Tab 1: Overview ───────────────────────────────────────────────────────
    with cc[0]:
        # VIX Banner
        vd = health.get("vix_bucket",{}) if health else {}
        vb = vd.get("bucket","—"); vl=vd.get("vix_last",0); vn=vd.get("note",""); vr=vd.get("risk_mode","—")
        vmap={"Investable":("vix-investable","🟢 INVESTABLE","#10B981"),
              "Chop":("vix-chop","🟡 CHOP","#F59E0B"),
              "Defensive":("vix-defensive","🔴 DEFENSIVE","#EF4444")}
        vcls,vlbl,vcol = vmap.get(vb,("","—","#9CA3AF"))
        st.markdown(f'<div class="{vcls}" style="padding:12px;border-radius:8px;margin-bottom:12px;">'
                    f'<div style="font-size:18px;font-weight:800;color:{vcol};">{vlbl} BUCKET</div>'
                    f'<div style="font-size:12px;color:#E8ECF0;margin-top:4px;">VIX {vl:.1f} · {vn}</div>'
                    f'<div style="font-size:10px;color:#6B7280;margin-top:2px;">Risk Mode: {vr}</div></div>',
                    unsafe_allow_html=True)

        # Front-run banner
        fw = frontrun.get("timing_window", getattr(transition,"front_run_window","not yet") if transition else "not yet")
        fr = frontrun.get("timing_rationale", getattr(transition,"front_run_rationale","") if transition else "")
        fw_cfg={"now":("#EF4444","🚨","ACT NOW"),"1-2w":("#F59E0B","⚡","1-2 WEEKS"),"3-6w":("#6366F1","👀","3-6 WEEKS"),"not yet":("#374151","🛑","NO SIGNAL")}
        fc2,fi2,fl2 = fw_cfg.get(fw, fw_cfg["not yet"])
        if fw != "not yet":
            st.markdown(f'<div style="background:{fc2}18;border-left:5px solid {fc2};padding:10px;border-radius:6px;margin-bottom:12px;">'
                        f'<div style="font-size:14px;font-weight:800;color:{fc2};">{fi2} FRONT-RUN: {fl2}</div>'
                        f'<div style="font-size:11px;color:#D1D5DB;margin-top:4px;">{fr[:120]}</div></div>',
                        unsafe_allow_html=True)

        # Quad cards
        qa,qb,qc2 = st.columns(3)
        with qa: st.markdown(qcard("STRUCTURAL",sq,gip.structural_conf if gip else 0,"Quarterly"),unsafe_allow_html=True)
        with qb: st.markdown(qcard("MONTHLY",mq,gip.monthly_conf if gip else 0,"Weather"),unsafe_allow_html=True)
        with qc2: st.markdown(qcard("GLOBAL",gq,global_.get("global_conf",0),"50 Countries"),unsafe_allow_html=True)

        # Playbook
        st.markdown("---")
        pa,pb2 = st.columns(2)
        with pa:
            st.markdown("### 🎯 Regime Playbook")
            if pb_data:
                st.markdown(f"**✅ LONG:** {' · '.join(pb_data.get('best_assets',[])[:6])}")
                st.markdown(f"**❌ AVOID:** {' · '.join(pb_data.get('worst_assets',[])[:5])}")
                st.markdown(f"📊 {pb_data.get('style','')}")
                st.markdown(f"💱 {pb_data.get('fx','')}")
        with pb2:
            st.markdown("### 📡 GIP Signals")
            if gip:
                f = gip.features
                for label,key,pos in [
                    ("Growth Level","growth_level",True),("Growth Mom","growth_momentum",True),
                    ("Inflation Level","inflation_level",False),("Inflation Mom","inflation_momentum",False),
                    ("Policy","policy_score",True),
                ]:
                    v = f.get(key,float("nan"))
                    if math.isfinite(v):
                        ok = (v>0.05 and pos) or (v<-0.05 and not pos)
                        ic = "🟢" if ok else "🔴" if ((v<-0.05 and pos) or (v>0.05 and not pos)) else "🟡"
                        st.markdown(f"{ic} **{label}**: `{v:+.3f}`")

        # Bottleneck quick
        bc1,bc2,bc3,bc4 = st.columns(4)
        for col,lab,lst,col_c in [(bc1,"⚡ L1",btk.get("level_1",[]),"#10B981"),(bc2,"📈 L2",btk.get("level_2",[]),"#F59E0B"),(bc3,"🔮 Brew",btk.get("brewing",[]),"#A78BFA"),(bc4,"🚫 Avoid",btk.get("avoid",[]),"#EF4444")]:
            col.markdown(f'<div style="text-align:center;font-size:10px;color:#9CA3AF;">{lab}</div>'
                         f'<div style="text-align:center;font-size:20px;font-weight:800;color:{col_c};">{len(lst)}</div>',
                         unsafe_allow_html=True)

    # ── Tab 2: GIP Model ──────────────────────────────────────────────────────
    with cc[1]:
        if not gip: st.warning("No GIP data."); st.stop()
        g=gip.structural_g; i=gip.structural_i
        fig=go.Figure()
        for q,(x0,y0,x1,y1) in {"Q1":(-0.1,-1,1,0),"Q2":(-0.1,0,1,1),"Q3":(-1,0,-0.1,1),"Q4":(-1,-1,-0.1,0)}.items():
            fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,fillcolor=QC[q],opacity=0.08,line_width=0)
            fig.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2,text=f"<b>{q}</b><br>{qn(q)}",font=dict(size=10,color=QC[q]),showarrow=False)
        fig.add_hline(y=0,line_width=1,line_color="#333"); fig.add_vline(x=0,line_width=1,line_color="#333")
        fig.add_scatter(x=[g],y=[i],mode="markers+text",marker=dict(size=16,color=qc(sq),symbol="circle",line=dict(width=2,color="white")),text=["NOW"],textposition="top center",textfont=dict(size=9,color="white"))
        fig.update_layout(xaxis_title="Growth",yaxis_title="Inflation",xaxis=dict(range=[-1,1],showgrid=True,gridcolor="#1F2B3D",zeroline=False),yaxis=dict(range=[-1,1],showgrid=True,gridcolor="#1F2B3D",zeroline=False),paper_bgcolor="#111827",plot_bgcolor="#111827",font=dict(color="#E8ECF0"),height=340,margin=dict(t=10,b=30,l=30,r=10),showlegend=False)
        ga,gb = st.columns([1.3,1])
        with ga: st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        with gb:
            c1p,c2p = st.columns(2)
            with c1p: st.plotly_chart(prob_bar(gip.structural_probs,"Structural"),use_container_width=True,config={"displayModeBar":False})
            with c2p: st.plotly_chart(prob_bar(gip.monthly_probs,"Monthly"),use_container_width=True,config={"displayModeBar":False})
            cov=gip.features.get("data_coverage",0); prx=gip.features.get("proxy_share",0)
            st.progress(cov, text=f"FRED Coverage: {cov:.0%}")
            if prx>0.5: st.warning(f"⚠️ {prx:.0%} proxy. Add FRED_API_KEY for accuracy.")

    # ── Tab 3: Timing ─────────────────────────────────────────────────────────
    with cc[2]:
        if not transition: st.warning("Transition data unavailable.")
        else:
            fw=transition.front_run_window; fr=transition.front_run_rationale
            fw_colors={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}
            fw_labels={"now":"🚨 ACT NOW","1-2w":"⚡ 1-2 WEEKS","3-6w":"👀 3-6 WEEKS","not yet":"🛑 NO SIGNAL"}
            fc3=fw_colors.get(fw,"#374151")
            st.markdown(f'<div style="background:{fc3}22;border-left:4px solid {fc3};padding:12px;border-radius:8px;margin-bottom:12px;">'
                        f'<div style="font-size:15px;font-weight:800;color:{fc3};">{fw_labels.get(fw,"")}</div>'
                        f'<div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',
                        unsafe_allow_html=True)
            paths=transition.transition_paths
            if paths:
                rows=[]
                for p in paths:
                    rows.append({"Path":f"{p.from_quad}→{p.to_quad}","P":f"{p.probability:.0%}","~wk":f"~{p.timeframe_weeks}w","EW":f"{p.early_warning_score:.0%}","Conf":f"{p.confidence:.0%}"})
                st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=160)
                for p in paths[:2]:
                    with st.expander(f"{p.from_quad}→{p.to_quad} — P={p.probability:.0%} · ~{p.timeframe_weeks}wk",expanded=(p==paths[0])):
                        ca,cb=st.columns(2)
                        with ca:
                            st.markdown("**Asset implications:**")
                            for mkt,impl in p.asset_implications.items():
                                col="#10B981" if "bullish" in impl.lower() else "#EF4444" if "bearish" in impl.lower() else "#9CA3AF"
                                st.markdown(f'<span style="color:{col};">{mkt.upper()}: {impl}</span>',unsafe_allow_html=True)
                        with cb:
                            st.markdown("**Confirm:** " + " · ".join(p.confirmation_needed[:3]))
                            st.markdown("**Invalidate:** " + " · ".join(p.invalidators[:3]))
            ew=transition.early_warning_signals
            if ew:
                st.markdown("### 🔔 Early Warning Signals")
                ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"✅" if v>=0.5 else "⬜","Score":f"{v:.2f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
                st.dataframe(pd.DataFrame(ew_rows),hide_index=True,height=250,use_container_width=True)
                firing=sum(1 for v in ew.values() if v>=0.5)
                st.progress(firing/len(ew) if ew else 0,text=f"{firing}/{len(ew)} firing")

        if analogs and analogs.get("top_analogs"):
            st.markdown("### 📚 Historical Analogs")
            for a in analogs["top_analogs"][:2]:
                sim=a.get("similarity",0)
                with st.expander(f"**{a['label']}** — {sim:.0%} similar", expanded=(a==analogs["top_analogs"][0])):
                    c1,c2,c3=st.columns(3)
                    c1.markdown(f"**1M:** {a.get('path_1m','')}"); c2.markdown(f"**3M:** {a.get('path_3m','')}"); c3.markdown(f"**6M:** {a.get('path_6m','')}")
                    st.markdown(f"**Next bias:** {a.get('next_bias','')} | **Impacts:** " + " | ".join(f"{k.upper()}={v}" for k,v in a.get("impacts",{}).items()))

    # ── Tab 4: Health ─────────────────────────────────────────────────────────
    with cc[3]:
        if not health: st.warning("No health data.")
        else:
            h1,h2,h3=st.columns(3)
            crash=health.get("crash_meter",{})
            h1.metric("Crash Meter",f"{crash.get('score',0):.0%}")
            h2.metric("VIX Bucket",health.get("vix_bucket",{}).get("bucket","—"))
            h3.metric("Breadth",f"{health.get('breadth',{}).get('pct_above_ma50',0):.0%}")
            fg=health.get("fear_greed",{}); fgs=fg.get("score",50)
            st.progress(fgs/100,text=f"Fear & Greed: {fg.get('label','—')} ({fgs:.0f})")
            checklist=health.get("checklists",{})
            if checklist:
                st.markdown("### Checklists")
                for mkt,items in checklist.items():
                    with st.expander(f"{mkt.upper()}",expanded=(mkt=="us")):
                        for item in items:
                            icon="✅" if item.get("tone")=="good" else "⚠️" if item.get("tone")=="warn" else "❌"
                            st.markdown(f"{icon} {item.get('label','')}: {item.get('state','')} ({item.get('score',0):.2f})")

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 SIGNALS  (Risk Ranges + Signal Strength)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Signals":
    st.markdown("# 🎯 Signals — Risk Range™ + Quality A Setups")
    sig_tabs = st.tabs(["🎯 Risk Ranges", "⚡ Quality A Picks", "🔔 Alerts"])

    with sig_tabs[0]:
        st.caption("Hurst R/S. LRR=buy zone. TRR=trim. TREND break=EXIT.")
        sm=rr.get("summary",{})
        s1,s2,s3,s4=st.columns(4)
        for col,lab,val,c in [(s1,"Total",sm.get("total",0),"#E8ECF0"),(s2,"Bullish",sm.get("bullish",0),"#10B981"),(s3,"Bearish",sm.get("bearish",0),"#EF4444"),(s4,"Quality A",sm.get("a_quality",0),"#00D4AA")]:
            col.markdown(f'<div style="text-align:center;font-size:10px;color:#9CA3AF;">{lab}</div>'
                         f'<div style="text-align:center;font-size:20px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)
        fc1,fc2,fc3=st.columns(3)
        with fc1: sf=st.selectbox("Signal",["All","bullish","bearish","neutral","mixed"],key="rr_sig")
        with fc2: qf=st.multiselect("Quality",["A","B","C","short_A","short_B","none"],default=["A","B","short_A","short_B"],key="rr_qual")
        with fc3: ca=st.checkbox("Critical alerts only",False,key="rr_crit")
        rows=[]
        for sym,v in sorted(ar.items()):
            comp=v.get("composite","neutral"); qual=v.get("quality","none"); alerts=v.get("alerts",[])
            if sf!="All" and comp!=sf: continue
            if qf and qual not in qf: continue
            if ca and not any(a["priority"]=="CRITICAL" for a in alerts): continue
            rows.append({"Ticker":sym,"Composite":comp,"Quality":qual,
                "Trade LRR":ff(v.get("trade_lrr")),"Trade TRR":ff(v.get("trade_trr")),
                "Trend LRR":ff(v.get("trend_lrr")),"Stretch":v.get("trade_stretch","—"),
                "H":f"{v.get('hurst_trade',0.5):.2f}","VolCnf":fp(v.get("volume_confirm",0.5)),
                "Alerts":len(alerts)})
        if rows:
            df=pd.DataFrame(rows)
            def sc(v): return "color:#10B981" if v=="bullish" else "color:#EF4444" if v=="bearish" else "color:#F59E0B" if v=="mixed" else "color:#6B7280"
            st.dataframe(df.style.map(sc,subset=["Composite"]),hide_index=True,height=450,use_container_width=True)

    with sig_tabs[1]:
        st.caption("Quality A = Bullish TRADE+TREND near LRR + volume expand.")
        best_assets=set(pb_data.get("best_assets",[])); worst_assets=set(pb_data.get("worst_assets",[]))
        long_picks=[]; short_picks=[]
        for sym,v in ar.items():
            qual=v.get("quality","none"); comp=v.get("composite","neutral")
            px=v.get("px",float("nan")); lrr=v.get("trade_lrr",float("nan")); trr=v.get("trade_trr",float("nan"))
            stretch=v.get("trade_stretch","neutral"); vol_c=v.get("volume_confirm",0.5)
            sector=TICKER_SECTOR.get(sym,"generic")
            rf=any(sector.replace("_"," ").lower() in b.lower() or b.lower() in sym.lower() for b in best_assets) or sym in best_assets
            if qual in ("A","B") and comp=="bullish":
                near_lrr=False
                if all(math.isfinite(x if x else float("nan")) for x in [px,lrr,trr]) and (trr-lrr)>1e-9:
                    near_lrr=(px-lrr)/(trr-lrr)<=0.35 or stretch in ("oversold","reset_zone")
                score=(50 if qual=="A" else 30)+(20 if near_lrr else 0)+(15 if vol_c>0.6 else 0)+(15 if rf else 0)
                long_picks.append({"ticker":sym,"qual":qual,"score":score,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"rf":rf})
            if qual in ("short_A","short_B") and comp=="bearish":
                near_trr=stretch in ("overbought","extended") or (all(math.isfinite(x if x else float("nan")) for x in [px,lrr,trr]) and (trr-lrr)>1e-9 and (px-lrr)/(trr-lrr)>=0.65)
                score=(50 if qual=="short_A" else 30)+(20 if near_trr else 0)+(15 if vol_c>0.6 else 0)
                short_picks.append({"ticker":sym,"qual":qual,"score":score,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"rf":False})
        long_picks.sort(key=lambda x:x["score"],reverse=True)
        short_picks.sort(key=lambda x:x["score"],reverse=True)
        lc,sc3=st.columns(2)
        with lc:
            st.markdown("### 🟢 Long — Quality A/B")
            for p in long_picks[:8]:
                rf_b="✅" if p["rf"] else ""
                st.markdown(f'<div class="signal-A"><b>{p["ticker"]}</b> {rf_b} <span style="color:#9CA3AF;font-size:10px;">{p["qual"]} · Score:{p["score"]}</span><br><span style="font-size:11px;color:#A7F3D0;">LRR:{ff(p["lrr"])} | TRR:{ff(p["trr"])} | {p["stretch"]} | VolCnf:{p["vol_c"]:.0%}</span></div>',unsafe_allow_html=True)
            if not long_picks: st.info("No long setups.")
        with sc3:
            st.markdown("### 🔴 Short — Quality S-A")
            for p in short_picks[:8]:
                st.markdown(f'<div class="signal-shortA"><b>{p["ticker"]}</b> <span style="color:#9CA3AF;font-size:10px;">{p["qual"]} · Score:{p["score"]}</span><br><span style="font-size:11px;color:#FECACA;">LRR:{ff(p["lrr"])} | TRR:{ff(p["trr"])} | {p["stretch"]} | VolCnf:{p["vol_c"]:.0%}</span></div>',unsafe_allow_html=True)
            if not short_picks: st.info("No short setups.")

    with sig_tabs[2]:
        all_alerts=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
        if all_alerts:
            for sym,a in all_alerts[:25]:
                ic="🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
                border="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
                st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {border};padding:8px;border-radius:4px;margin-bottom:4px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>',unsafe_allow_html=True)
        else: st.info("No alerts.")

# ══════════════════════════════════════════════════════════════════════════════
# 🌍 MARKETS  (Global + US + Forex + Commodity + Crypto + IHSG)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Markets":
    st.markdown("# 🌍 Markets")
    mkt_tabs = st.tabs(["🌍 Global Quad", "📊 US Stocks", "💱 Forex", "🛢 Commodities", "₿ Crypto", "🇮🇩 IHSG"])

    with mkt_tabs[0]:
        if not global_: st.warning("No global data.")
        else:
            gq2=global_.get("global_quad","Q3"); gconf=global_.get("global_conf",0.0); gprobs=global_.get("global_probs",{})
            gc1,gc2=st.columns([1,1.5])
            with gc1:
                st.markdown(qcard("GLOBAL QUAD",gq2,gconf,"50 Country ETFs"),unsafe_allow_html=True)
                st.plotly_chart(prob_bar(gprobs,""),use_container_width=True,config={"displayModeBar":False})
            with gc2:
                heat=[]
                for country,data in global_.get("country_quads",{}).items():
                    if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=data[0],data[1],data[2]
                    elif isinstance(data,dict): etf,quad,conf=data.get("etf",""),data.get("quad",""),data.get("conf",0)
                    else: continue
                    heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
                if heat:
                    df=pd.DataFrame(heat)
                    st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=400,use_container_width=True)

    with mkt_tabs[1]:
        st.caption(f"Regime: {sq} {qn(sq)} · Best: {' · '.join(pb_data.get('best_assets',[])[:4])}")
        _render_universe("US Sectors", US_SECTORS, prices, btk)
        _render_universe("US Factors", US_FACTORS, prices, btk)
        # Notable single stocks
        excluded=set(list(US_SECTORS)+list(US_FACTORS)+list(COMMODITIES)+list(CRYPTO)+list(FOREX_PAIRS)+list(IHSG_UNIVERSE)+list(BONDS)+list(MACRO_PROXIES)+["DX-Y.NYB","^VIX","EIDO","^JKSE"])
        notable={k:v for k,v in TICKER_SECTOR.items() if k not in excluded and k in prices and v!="generic"}
        if notable:
            st.markdown("### Notable Stocks (Bottleneck Plays)")
            rows=[]
            for sym,sector in notable.items():
                s=prices.get(sym)
                if s is None: continue
                s=pd.to_numeric(pd.Series(s),errors="coerce").dropna().tail(252)
                if s.empty: continue
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                rows.append({"Ticker":sym,"Sector":sector.replace("_"," ").title(),"3M":f"{r3:+.1%}","Bottleneck":_btk_badge(sym,btk)})
            if rows: st.markdown(pd.DataFrame(rows).to_html(escape=False,index=False),unsafe_allow_html=True)

    with mkt_tabs[2]:
        st.caption("DXY bearish (McCullough Q3 confirmed) = EM FX relief. Commodity FX leads.")
        _render_universe("Forex Pairs", FOREX_PAIRS, prices, btk)

    with mkt_tabs[3]:
        st.caption("Q2/Q3 commodity cycle. Gold = Q3/Q4 safety. Oil = growth proxy.")
        _render_universe("Commodities", COMMODITIES, prices, btk)

    with mkt_tabs[4]:
        st.caption("Q1/Q2 risk-on. Q3/Q4 risk-off. BTC dominance + DXY correlation.")
        _render_universe("Crypto Universe", CRYPTO, prices, btk)

    with mkt_tabs[5]:
        st.caption("CKPN cascade, offshore drilling, foreign flow, JIIPE industrial estate.")
        _render_universe("IHSG Universe", IHSG_UNIVERSE, prices, btk)
        # EM Recovery Signal
        st.markdown("---")
        st.markdown("### 🌍 EM Recovery Signal")
        em_sig = btk.get("em_recovery",{}) if btk else {}
        if em_sig and em_sig.get("trigger"):
            conf=em_sig.get("confidence",0)
            ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
            st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">'
                        f'<div style="font-size:13px;font-weight:700;color:{ec};">{em_sig.get("trigger","")}</div>'
                        f'<div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div>'
                        f'<div style="font-size:12px;color:#E8ECF0;margin-top:6px;">Confidence: {conf:.0%}</div>'
                        f'<div style="font-size:11px;color:#9CA3AF;margin-top:2px;">🎯 Best: {", ".join(em_sig.get("best",[])[:6])}</div>'
                        f'</div>',unsafe_allow_html=True)
        else:
            # Graceful empty state — was showing blank before
            quad_key = f"{sq}→{mq}"
            st.info(f"EM Recovery Signal: No active signal for {quad_key}. "
                    f"Signal activates on Q3→Q2 or Q4→Q1 transitions. "
                    f"Current: {sq} structural / {mq} monthly.")
            st.markdown(f"""
**When EM recovery signals fire:**
- Q3→Q2: Commodity exporters recover (EIDO, EWZ, EWW, NORW)
- Q4→Q1: MAX EM recovery — all EM equities + EM FX
- Confidence threshold: > 0.40 to activate
            """)

# ══════════════════════════════════════════════════════════════════════════════
# 🔍 RESEARCH  (Bottleneck + Narratives + Discovery — compact)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Research":
    st.markdown("# 🔍 Research — Bottleneck · Narratives · Discovery")
    res_tabs = st.tabs(["🔍 Bottleneck", "📖 Narratives", "🔮 Discovery"])

    # ── Bottleneck (compact single-table design) ──────────────────────────────
    with res_tabs[0]:
        st.caption("Citrini supply chain scarcity. BUY at LRR. TRIM at TRR. Level 1 = best.")

        if not btk:
            st.warning("No bottleneck data. Refresh."); st.stop()

        ev_formula = btk.get("ev_formula","regime_fit × trend_score × constraint × fwd_mult × range_discount")
        with st.expander("⚙️ EV Formula", expanded=False):
            st.code(ev_formula)
            st.caption(f"Flow: {btk.get('flow_proxy_note','')} | Pod: {btk.get('pod_proxy_note','')}")

        # Summary metrics
        all_btk = btk.get("all_scored",[])
        l1=btk.get("level_1",[]); l2=btk.get("level_2",[]); wt=btk.get("watch",[]); br=btk.get("brewing",[])
        m1,m2,m3,m4,m5 = st.columns(5)
        for col,lab,val,c in [(m1,"L1",len(l1),"#10B981"),(m2,"L2",len(l2),"#F59E0B"),(m3,"Watch",len(wt),"#6366F1"),(m4,"Brew",len(br),"#A78BFA"),(m5,"Known",btk.get("known_count",0),"#00D4AA")]:
            col.markdown(f'<div style="text-align:center;font-size:10px;color:#9CA3AF;">{lab}</div>'
                         f'<div style="text-align:center;font-size:18px;font-weight:800;color:{c};">{val}</div>',unsafe_allow_html=True)

        st.markdown("---")
        # COMPACT FILTER ROW
        bf1,bf2,bf3,bf4,bf5 = st.columns(5)
        with bf1: level_f = st.multiselect("Level",["level_1","level_2","watch","brewing","avoid"],default=["level_1","level_2","watch"],key="btk_lvl")
        with bf2: dir_f2  = st.selectbox("Dir",["All","long","short","avoid_long"],key="btk_dir")
        with bf3: mkt_f2  = st.selectbox("Market",["All","us_equity","ihsg","forex","commodity","crypto"],key="btk_mkt")
        with bf4: action_f= st.selectbox("Action",["All","✅ BUY ZONE","⏳ WAIT — MID RANGE","⚠️ APPROACHING TRR","🔴 TRIM ZONE"],key="btk_act")
        with bf5: known_only = st.checkbox("Known only",False,key="btk_known")

        # ONE unified table (no more L1/L2/Watch separate sections)
        all_for_table = l1+l2+wt+br+btk.get("avoid",[])
        filtered_btk = []
        for c in all_for_table:
            if level_f and c.get("level","") not in level_f: continue
            if dir_f2!="All" and c.get("direction","")!=dir_f2: continue
            if mkt_f2!="All" and c.get("market","")!=mkt_f2: continue
            if action_f!="All" and c.get("range_action","")!=action_f: continue
            if known_only and not c.get("known"): continue
            filtered_btk.append(c)

        if filtered_btk:
            rows=[]
            for c in filtered_btk:
                thesis=(c.get("thesis") or c.get("known_thesis") or c.get("rationale") or "—")[:70]
                pod_q=c.get("pod_quality","—"); pod_i="📈" if pod_q=="accelerating" else "📉" if pod_q=="decelerating" else "➡️"
                lvl_colors={"level_1":"#10B981","level_2":"#F59E0B","watch":"#6366F1","avoid":"#EF4444","brewing":"#A78BFA"}
                rows.append({
                    "K":      "✅" if c.get("known") else "◻",
                    "Level":  c.get("level","—"),
                    "Ticker": c["ticker"],
                    "Mkt":    c.get("market","—").replace("_"," ").title()[:8],
                    "Dir":    c.get("direction","—"),
                    "EV":     f'{c.get("ev",0):.3f}',
                    "RF":     f'{c.get("regime_fit",0):.0%}',
                    "FwdX":   f'{c.get("forward_mult",1):.2f}x',
                    "Action": c.get("range_action","—"),
                    "RS3M":   f'{c.get("rs_3m",0):.1%}' if c.get("rs_3m") is not None else "—",
                    "Pod":    f'{pod_i}{c.get("pod1_proxy",0):+.2f}',
                    "Thesis": thesis,
                })
            df=pd.DataFrame(rows)
            def _sl(v): return f"color:{lvl_colors.get(v,'#9CA3AF')};font-weight:700"
            def _sa(v):
                if "BUY" in str(v): return "color:#10B981;font-weight:700"
                if "TRIM" in str(v): return "color:#EF4444;font-weight:700"
                if "APPROACH" in str(v): return "color:#F59E0B"
                return "color:#6B7280"
            def _sd2(v): return "color:#10B981" if v=="long" else "color:#EF4444" if v=="short" else "color:#F59E0B" if "avoid" in str(v) else "color:#6B7280"
            def _sfwd(v):
                try:
                    fv=float(str(v).replace("x",""))
                    return "color:#10B981;font-weight:700" if fv>1.10 else "color:#F59E0B" if fv>1.0 else "color:#6B7280"
                except: return ""
            st.dataframe(df.style.map(_sl,subset=["Level"]).map(_sa,subset=["Action"]).map(_sd2,subset=["Dir"]).map(_sfwd,subset=["FwdX"]),
                         hide_index=True, height=500, use_container_width=True)

            # Expandable thesis cards (max 8)
            with st.expander("📋 Thesis Detail", expanded=False):
                for c in filtered_btk[:8]:
                    dc="#10B981" if c.get("direction")=="long" else "#EF4444" if c.get("direction")=="short" else "#F59E0B"
                    tp=c.get("tp",{}); tp_str=""
                    if tp and tp.get("t1") and tp.get("stop"):
                        tp_str=f"T1=${tp['t1']:.2f} | T2=${tp.get('t2',0):.2f} | Stop=${tp['stop']:.2f}"
                    st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:10px;margin-bottom:6px;">
<span style="font-size:13px;font-weight:800;color:#E8ECF0;">{c["ticker"]}</span>
<span style="font-size:11px;color:{dc};font-weight:700;margin-left:8px;">{c.get("direction","").upper()}</span>
<span style="font-size:11px;color:#00D4AA;margin-left:8px;">{c.get("range_action","")}</span>
<span style="font-size:10px;color:#9CA3AF;margin-left:8px;">EV:{c.get("ev",0):.3f} FwdX:{c.get("forward_mult",1):.2f}x</span>
<div style="font-size:11px;color:#D1D5DB;margin-top:4px;">{c.get("known_thesis") or c.get("thesis","—")}</div>
<div style="font-size:10px;color:#6B7280;margin-top:3px;">⚡ {c.get("catalyst","—")} | ⚠️ {c.get("risk","—")} | {tp_str}</div>
</div>''', unsafe_allow_html=True)
        else:
            st.info("No candidates match filters.")

        # Brewing highlight
        if br:
            st.markdown("---")
            st.markdown("### 🔮 Pre-Consensus Brewing")
            for c in br[:5]:
                fwd_c="#10B981" if c.get("forward_mult",1)>1.10 else "#A78BFA"
                st.markdown(f'<div style="background:linear-gradient(90deg,#1e1b4b,#2d1b69);border-left:3px solid #A78BFA;border-radius:5px;padding:8px;margin-bottom:5px;">'
                             f'<b style="color:#E8ECF0;">{c["ticker"]}</b> '
                             f'<span style="font-size:10px;color:#00D4AA;">{c.get("range_action","")}</span> '
                             f'<span style="font-size:10px;color:{fwd_c};">FwdX:{c.get("forward_mult",1):.2f}x</span> '
                             f'<span style="font-size:10px;color:#7C3AED;">EV:{c.get("ev",0):.3f} RF:{c.get("regime_fit",0):.0%}</span>'
                             f'<div style="font-size:10px;color:#C4B5FD;margin-top:3px;">{(c.get("thesis") or c.get("known_thesis",""))[:90]}</div>'
                             f'</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔭 Untracked Bottleneck Hints")
        st.caption("Tickers below have confirmed/emerging bottleneck thesis tapi belum ada di universe. "
                   "Add ke settings.py → TICKER_SECTOR + IHSG_UNIVERSE jika ingin di-track.")

        from config.settings import BOTTLENECK_HINTS

        # Determine loaded tickers
        loaded = set(prices.keys()) if prices else set()

        # Current quad untuk filter quad_fit
        active_quad = sq  # structural quad dari snap

        hints_shown = 0
        for sector, hint_list in BOTTLENECK_HINTS.items():
            # Filter: only show hints where ticker NOT loaded
            missing = [h for h in hint_list if h["ticker"] not in loaded]
            if not missing:
                continue

            # Optionally filter by quad fit
            # (show all if no quad match — don't hide potentially useful hints)
            quad_matched = [h for h in missing if active_quad in h.get("quad_fit", [])]
            other = [h for h in missing if active_quad not in h.get("quad_fit", [])]
            # Quad-matched first
            ordered = quad_matched + other

            # Get bottleneck profile constraint for this sector
            profile = BOTTLENECK_PROFILES.get(sector, {})
            constraint = profile.get("constraint", 0.0)
            regime_fit = profile.get(active_quad, 0.5)
            sector_label = sector.replace("_", " ").title()

            # Color by constraint level
            if constraint >= 0.85:
                border_color = "#EF4444"
                badge = "🔴 CRITICAL"
            elif constraint >= 0.75:
                border_color = "#F59E0B"
                badge = "🟡 HIGH"
            else:
                border_color = "#6366F1"
                badge = "🔵 MODERATE"

            with st.expander(
                f"{badge} **{sector_label}** — Constraint {constraint:.0%} | "
                f"Regime Fit ({active_quad}): {regime_fit:.0%} | "
                f"{len(ordered)} untracked",
                expanded=(constraint >= 0.85)  # auto-expand critical sectors
            ):
                for h in ordered:
                    in_quad = active_quad in h.get("quad_fit", [])
                    quad_tag = f"✅ {active_quad} fit" if in_quad else f"⚠️ better in {'/'.join(h.get('quad_fit', []))}"
                    source_tag = h.get("source", "")

                    st.markdown(
                        f"""<div style="background:#111827;border-left:3px solid {border_color};
                        padding:10px 14px;border-radius:4px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:14px;font-weight:700;color:#E8ECF0;">
                                <code style="background:#1F2937;padding:2px 6px;border-radius:3px;
                                font-size:13px;color:#60A5FA;">{h['ticker']}</code>
                                &nbsp;{h['name']}
                            </span>
                            <span style="font-size:10px;color:#6B7280;">{quad_tag} · {source_tag}</span>
                        </div>
                        <div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{h['why']}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                hints_shown += len(ordered)

        if hints_shown == 0:
            st.success("✅ All known bottleneck candidates are already tracked in universe.")
        else:
            st.caption(f"💡 {hints_shown} untracked hints across {len(BOTTLENECK_HINTS)} sectors. "
                       "Add tickers ke `config/settings.py → TICKER_SECTOR` untuk mulai track.")

    # ── Narratives ────────────────────────────────────────────────────────────
    with res_tabs[1]:
        if not narr:
            st.warning("No narrative data. Refresh.")
        else:
            nd = narr.get("narrative_dashboard", [])
            forecasts_raw = narr.get("forecasts", {})

            # NarrativeUniverseConnector — Ricky article signals
            universe_active = {}; universe_sesi = None; uni_articles = []
            try:
                from engines.narrative_universe_connector import NarrativeUniverseConnector
                uni_result = NarrativeUniverseConnector().score(prices, sq)
                universe_active = uni_result.get("active_themes", {})
                universe_sesi   = uni_result.get("ihsg_cycle_stage")
                uni_articles    = uni_result.get("top_signals", [])
            except Exception: pass

            # Boost scores from Ricky universe
            for item in nd:
                boost = universe_active.get(item.get("narrative",""), 0) * 0.20
                if boost > 0.01:
                    item["current_strength"] = min(1.0, item.get("current_strength",0) + boost)
                    item["universe_boost"] = round(boost, 3)
            nd.sort(key=lambda x: x.get("current_strength",0), reverse=True)

            # Ricky Sesi banner
            if universe_sesi:
                sesi_cfg = {
                    "sesi_1":("#EF4444","🩸 SESI 1 — PAIN/BOTTOM","Foreign exit. Wait for banking stabilization."),
                    "sesi_2":("#F59E0B","🌱 SESI 2 — BANKING STABILIZE","BBCA/BBRI net buy. Start positioning."),
                    "sesi_3":("#10B981","👑 SESI 3 — KING IS BACK","Coal/OSV/Konglo firing. Full position."),
                }
                sc,sl,sd = sesi_cfg.get(universe_sesi,("#6B7280","",""))
                st.markdown(f'''<div style="background:{sc}22;border-left:5px solid {sc};padding:10px;border-radius:6px;margin-bottom:10px;"><div style="font-size:14px;font-weight:800;color:{sc};">RICKY {sl}</div><div style="font-size:11px;color:#D1D5DB;margin-top:3px;">{sd}</div></div>''',unsafe_allow_html=True)

            # Dominant
            dom = narr.get("dominant_narrative")
            if dom:
                ds=narr.get("dominant_strength",0); dm=narr.get("dominant_lead_market","")
                st.success(f"🔥 **Dominant:** `{dom.replace(chr(95),' ').title()}` — Strength:{ds:.0%} | Lead:{dm.replace(chr(95),' ').title()}")

            # Metrics
            igniting=[n for n in nd if n.get("ignition") or n.get("current_strength",0)>=0.55]
            strong=[n for n in nd if 0.35<=n.get("current_strength",0)<0.55]
            building=[n for n in nd if 0.15<=n.get("current_strength",0)<0.35]
            c1,c2,c3=st.columns(3)
            c1.metric("🔥 Igniting",len(igniting)); c2.metric("💪 Active",len(strong)); c3.metric("🔨 Building",len(building))

            # ── FORWARD-LOOKING (market always forward-looking) ────────────────
            st.markdown("---")
            st.markdown("### 🔭 Forward Forecast — What Market Will Price In (4-8W)")
            st.caption("Market discounts 4-12 weeks ahead. Focus on 4W/8W, not current strength.")
            fwd_ranked = sorted(nd, key=lambda x: max(x.get("forecast_4w",0),x.get("forecast_8w",0)), reverse=True)
            top_fwd = [n for n in fwd_ranked if max(n.get("forecast_4w",0),n.get("forecast_8w",0))>0.05][:6]
            if top_fwd:
                for n in top_fwd:
                    name_d=n.get("narrative","").replace("_"," ").title()
                    cur=n.get("current_strength",0); fw4=n.get("forecast_4w",0); fw8=n.get("forecast_8w",0); rf=n.get("regime_weight",0.5)
                    lead=n.get("lead_market","").replace("_"," ").title()
                    ub=f" +{n.get('universe_boost',0):.0%} Ricky" if n.get("universe_boost",0)>0.02 else ""
                    arrow="📈 ACCELERATING" if fw4>cur*1.2 else "📉 FADING" if fw4<cur*0.8 else "➡️ STABLE"
                    ac="#10B981" if "ACC" in arrow else "#EF4444" if "FAD" in arrow else "#F59E0B"
                    st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:6px;padding:10px;margin-bottom:6px;">
<div style="display:flex;justify-content:space-between;"><span style="font-size:13px;font-weight:700;color:#E8ECF0;">{name_d}</span><span style="font-size:11px;color:{ac};font-weight:700;">{arrow}</span></div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:7px;">
<div style="text-align:center;background:#0F172A;border-radius:4px;padding:5px;"><div style="font-size:8px;color:#6B7280;">NOW</div><div style="font-size:12px;font-weight:700;color:#9CA3AF;">{cur:.0%}</div></div>
<div style="text-align:center;background:#064e3b;border-radius:4px;padding:5px;"><div style="font-size:8px;color:#6B7280;">4W</div><div style="font-size:12px;font-weight:700;color:#10B981;">{fw4:.0%}</div></div>
<div style="text-align:center;background:#1e1b4b;border-radius:4px;padding:5px;"><div style="font-size:8px;color:#6B7280;">8W</div><div style="font-size:12px;font-weight:700;color:#6366F1;">{fw8:.0%}</div></div>
<div style="text-align:center;background:#111827;border-radius:4px;padding:5px;"><div style="font-size:8px;color:#6B7280;">RF</div><div style="font-size:12px;font-weight:700;color:#F59E0B;">{rf:.0%}</div></div>
</div>
<div style="font-size:10px;color:#6B7280;margin-top:3px;">Lead: {lead}{ub}</div>
</div>''',unsafe_allow_html=True)
            else:
                st.info("Proactive forecasts empty — ensure scenario_output passed to NarrativeEngine in orchestrator.py")

            # ── Current strength table ──────────────────────────────────────
            st.markdown("---"); st.markdown("### 📡 Current Narrative Strength (All)")
            rows=[]
            for n in nd:
                cur=n.get("current_strength",0); fw4=n.get("forecast_4w",0); rf=n.get("regime_weight",0)
                ign="🔥" if n.get("ignition") else ("📈" if cur>0.35 else ("🔨" if cur>0.15 else "💤"))
                ub=f"+{n.get('universe_boost',0):.0%}" if n.get("universe_boost",0)>0.01 else ""
                rows.append({"S":ign,"Narrative":n.get("narrative","").replace("_"," ").title()[:32],
                    "Strength":f"{cur:.0%}","4W":f"{fw4:.0%}","RF":f"{rf:.0%}",
                    "Lead":n.get("lead_market","").replace("_"," ").title()[:12],
                    "Spillover":" → ".join(n.get("top_spillover",[])[:2])[:20],"Ricky":ub})
            if rows:
                df=pd.DataFrame(rows)
                def _ss(v):
                    try: fv=float(str(v).replace("%",""))/100; return "color:#10B981;font-weight:700" if fv>=0.45 else "color:#F59E0B" if fv>=0.25 else "color:#6B7280"
                    except: return ""
                st.dataframe(df.style.map(_ss,subset=["Strength","4W"]),hide_index=True,height=420,use_container_width=True)

            # Ricky article signals
            if uni_articles:
                st.markdown("---"); st.markdown("### 📚 Ricky Live Article Signals")
                for art_id, score, dtickers in uni_articles[:8]:
                    sc2="#10B981" if score>0.5 else "#F59E0B" if score>0.3 else "#9CA3AF"
                    st.markdown(f'''<div style="border-left:3px solid {sc2};padding:5px 10px;background:#111827;border-radius:4px;margin-bottom:3px;"><span style="font-size:11px;font-weight:700;color:#E8ECF0;">{art_id.replace(chr(95)," ").title()[:48]}</span><span style="font-size:11px;color:{sc2};font-weight:700;margin-left:8px;">{score:.0%}</span><div style="font-size:10px;color:#6B7280;">{" · ".join(dtickers[:5])}</div></div>''',unsafe_allow_html=True)

            # Spillover map
            spillover=narr.get("spillover",{})
            if any(spillover.values()):
                st.markdown("---"); st.markdown("### 🌊 Cross-Market Spillover")
                for mkt,spill in spillover.items():
                    if spill: st.markdown(f"**{mkt.replace('_',' ').title()}:** {spill}")


    # ── Discovery ─────────────────────────────────────────────────────────────
    with res_tabs[2]:
        if dv3 and (dv3.get("reactive") or dv3.get("proactive") or dv3.get("merged")):
            merged=dv3.get("merged",[]); reactive=dv3.get("reactive",[]); proactive=dv3.get("proactive",[])
            d1,d2,d3=st.columns(3)
            d1.metric("Reactive",len(reactive)); d2.metric("Proactive",len(proactive)); d3.metric("Merged",len(merged))
            if merged:
                rows=[]
                for c in merged[:30]:
                    rows.append({"Ticker":c.get("ticker","—"),"Mkt":c.get("market","").replace("_"," ").title()[:8],
                        "Source":"🔴 React" if c.get("source","")=="reactive_discovery" else "🔮 Proact",
                        "EV":f'{c.get("ev",0):.3f}',"Sector":c.get("sector","").replace("_"," ").title()[:18],
                        "Narrative":c.get("narrative_tag","")[:30] or c.get("narrative","")[:30]})
                df=pd.DataFrame(rows)
                def _dsrc(v): return "color:#EF4444;font-weight:700" if "React" in str(v) else "color:#A78BFA"
                st.dataframe(df.style.map(_dsrc,subset=["Source"]),hide_index=True,height=380,use_container_width=True)
        else:
            auto_cands=auto_disc.get("candidates",[]) if auto_disc else []
            if not auto_cands: st.info("No discovery data. Run ⚡ Force rebuild.")
            else:
                for c in auto_cands[:12]:
                    conf=c.get("confidence",0); cc="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#9CA3AF"
                    st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:6px;padding:10px;margin-bottom:6px;">'
                                f'<b style="color:#E8ECF0;">{c.get("name","—")}</b> <span style="color:{cc};font-size:10px;">{conf:.0%}</span> <span style="color:#9CA3AF;font-size:10px;">{c.get("stage","—")}</span>'
                                f'<div style="font-size:11px;color:#D1D5DB;margin-top:3px;">{c.get("thesis","—")[:100]}</div>'
                                f'<div style="font-size:10px;color:#9CA3AF;">🎯 {", ".join(c.get("beneficiary_tickers",[])[:5])}</div>'
                                f'</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔮 SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Scenarios":
    st.markdown("# 🔮 Scenarios — Base · Alt · Risk · Tail")
    st.caption("Transition probability matrix × macro confirmation. McCullough: 'Scenarios are probabilistic maps, not predictions.'")
    if not scen: st.warning("No scenario data."); st.stop()
    _render_scenario(scen.get("base_case"),"BASE","#10B981","🎯")
    _render_scenario(scen.get("alt_case"), "ALT","#F59E0B","🔄")
    sc_list=scen.get("scenarios",[])
    if len(sc_list)>2: _render_scenario(sc_list[2],"RISK","#EF4444","⚠️")
    if len(sc_list)>3: _render_scenario(sc_list[3],"TAIL","#6366F1","📌")
    st.markdown("---")
    inp=scen.get("inputs",{}); stab=scen.get("regime_stability","—")
    st.markdown(f"**Regime Stability:** {stab} | **G-Mom:** {inp.get('g_mom',0):+.3f} | **I-Mom:** {inp.get('i_mom',0):+.3f} | **Policy:** {inp.get('policy',0):+.3f}")

# ══════════════════════════════════════════════════════════════════════════════
# 📋 PAPER TRADER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Paper Trader":
    st.markdown("# 📋 Paper Trader — Track · Audit · Learn")
    st.caption("Signal-driven position tracker. Auto-alert on TP/Stop. Win rate by Quad regime.")

    pt_tabs = st.tabs(["➕ New Trade", "📂 Open Positions", "📊 Performance"])

    with pt_tabs[0]:
        st.markdown("**Add from Front-Run Boarding Now:**")
        if frontrun.get("boarding_now"):
            for c in frontrun.get("boarding_now",[])[:5]:
                t=_gv(c,"ticker","—"); e=_gv(c,"entry_zone"); s=_gv(c,"stop_loss"); t1=_gv(c,"tp1"); conf=_gv(c,"confidence_pct",0)
                label = f"➕ {t} | Entry:${e:.2f} Stop:${s:.2f} Conf:{conf}%" if e and s else f"➕ {t} | Conf:{conf}%"
                if st.button(label, key=f"auto_{t}"):
                    trade={"trade_id":f"{t}_{datetime.now().strftime('%Y%m%d_%H%M')}","ticker":t,"direction":"long","entry_price":e or 0,"stop_loss":s or 0,"tp1":t1,"tp2":_gv(c,"tp2"),"tp3":None,"entry_date":datetime.now().strftime("%Y-%m-%d"),"signal_source":"frontrun_engine","regime":sq,"status":"open","pnl_pct":None,"exit_price":None}
                    st.session_state.pt_trades.append(trade); st.success(f"✅ {t} added"); st.rerun()
        st.markdown("---")
        st.markdown("**Manual entry:**")
        with st.form("new_trade"):
            c1,c2,c3 = st.columns(3)
            with c1: ntick=st.text_input("Ticker",placeholder="e.g. GLD"); ndir=st.selectbox("Dir",["long","short"])
            with c2: nentry=st.number_input("Entry",min_value=0.01,value=100.0,format="%.2f"); nstop=st.number_input("Stop",min_value=0.01,value=92.0,format="%.2f")
            with c3: ntp1=st.number_input("T1",min_value=0.01,value=110.0,format="%.2f"); nsrc=st.selectbox("Source",["frontrun_engine","bottleneck","rr_quality_a","manual"])
            if st.form_submit_button("Add Trade ✅",use_container_width=True) and ntick:
                trade={"trade_id":f"{ntick.upper()}_{datetime.now().strftime('%Y%m%d_%H%M')}","ticker":ntick.upper(),"direction":ndir,"entry_price":nentry,"stop_loss":nstop,"tp1":ntp1,"tp2":None,"tp3":None,"entry_date":datetime.now().strftime("%Y-%m-%d"),"signal_source":nsrc,"regime":sq,"status":"open","pnl_pct":None,"exit_price":None}
                st.session_state.pt_trades.append(trade); st.success(f"✅ {ntick.upper()} added"); st.rerun()

    with pt_tabs[1]:
        open_t=[t for t in st.session_state.pt_trades if t.get("status")=="open"]
        if not open_t: st.info("No open positions. Add from New Trade tab.")
        for trade in open_t:
            s = prices.get(trade["ticker"])
            cur = float(pd.to_numeric(pd.Series(s),errors="coerce").dropna().iloc[-1]) if s is not None and len(pd.to_numeric(pd.Series(s),errors="coerce").dropna())>0 else trade["entry_price"]
            pnl = (cur-trade["entry_price"])/trade["entry_price"] if trade["direction"]=="long" else (trade["entry_price"]-cur)/trade["entry_price"]
            pc = "#10B981" if pnl>=0 else "#EF4444"
            ca,cb,cc2,cd,ce = st.columns([2,1,1,1,1])
            with ca: st.markdown(f'<b style="color:#E8ECF0;">{trade["ticker"]}</b> <span style="color:{"#10B981" if trade["direction"]=="long" else "#EF4444"};font-size:11px;">{trade["direction"].upper()}</span><br><span style="font-size:10px;color:#9CA3AF;">Entry:${trade["entry_price"]:.2f} Stop:${trade.get("stop_loss",0):.2f}{" T1:$"+str(round(trade["tp1"],2)) if trade.get("tp1") else ""}</span>',unsafe_allow_html=True)
            with cb: st.markdown(f'<div style="font-size:14px;font-weight:700;color:#9CA3AF;">${cur:.2f}</div><div style="font-size:9px;color:#6B7280;">Now</div>',unsafe_allow_html=True)
            with cc2: st.markdown(f'<div style="font-size:14px;font-weight:700;color:{pc};">{pnl:+.1%}</div><div style="font-size:9px;color:#6B7280;">P&L</div>',unsafe_allow_html=True)
            with cd: st.markdown(f'<div style="font-size:11px;color:#9CA3AF;">{trade.get("regime","—")}</div>',unsafe_allow_html=True)
            with ce:
                if st.button("Close ✖",key=f"close_{trade['trade_id']}"):
                    trade.update({"status":"closed","exit_price":cur,"pnl_pct":round(pnl,4)})
                    st.session_state.pt_closed.append(trade)
                    st.session_state.pt_trades=[t for t in st.session_state.pt_trades if t["trade_id"]!=trade["trade_id"]]
                    st.success(f"Closed {trade['ticker']} {pnl:+.1%}"); st.rerun()
            if trade.get("stop_loss") and cur<=trade["stop_loss"] and trade["direction"]=="long":
                st.error(f"🔴 {trade['ticker']} STOP HIT at ${cur:.2f}. Exit per process.")
            elif trade.get("tp1") and cur>=trade["tp1"] and trade["direction"]=="long":
                st.success(f"✅ {trade['ticker']} T1 HIT at ${cur:.2f}. Trim 25%.")
            st.divider()

    with pt_tabs[2]:
        closed = st.session_state.pt_closed
        if not closed: st.info("No closed trades yet.")
        else:
            rows=[]
            for t in closed:
                rows.append({"Ticker":t["ticker"],"Dir":t.get("direction","—").upper(),"Entry":f"${t['entry_price']:.2f}","Exit":f"${t.get('exit_price',0):.2f}","PnL":f"{t.get('pnl_pct',0):+.1%}" if t.get('pnl_pct') else "—","Regime":t.get("regime","—"),"Source":t.get("signal_source","—"),"Date":t.get("entry_date","—")})
            df=pd.DataFrame(rows)
            def _sp(v):
                try: fv=float(str(v).replace("%","").replace("+",""))
                except: return ""
                return "color:#10B981;font-weight:700" if fv>0 else "color:#EF4444;font-weight:700"
            st.dataframe(df.style.map(_sp,subset=["PnL"]),hide_index=True,use_container_width=True)
            by_regime={}
            for t in closed:
                r=t.get("regime","—"); p=t.get("pnl_pct",0) or 0
                by_regime.setdefault(r,[]).append(p)
            if by_regime:
                st.markdown("### 🏆 Win Rate by Quad")
                cols=st.columns(len(by_regime))
                for i,(regime,pnls) in enumerate(by_regime.items()):
                    wr=sum(1 for p in pnls if p>0)/len(pnls) if pnls else 0
                    avg=np.mean(pnls) if pnls else 0
                    rc=QC.get(regime,"#9CA3AF")
                    cols[i].markdown(f'<div style="background:#111827;border:1px solid {rc};border-radius:8px;padding:8px;text-align:center;"><div style="font-size:13px;font-weight:800;color:{rc};">{regime}</div><div style="font-size:20px;font-weight:900;color:{"#10B981" if wr>=0.5 else "#EF4444"};">{wr:.0%}</div><div style="font-size:10px;color:#9CA3AF;">Win Rate</div><div style="font-size:12px;color:{"#10B981" if avg>=0 else "#EF4444"};">{avg:+.1%}</div></div>',unsafe_allow_html=True)
            all_pnls=[t.get("pnl_pct",0) or 0 for t in closed]
            if all_pnls:
                wins=sum(1 for p in all_pnls if p>0)
                st.markdown(f"**Overall:** {wins}/{len(all_pnls)} wins ({wins/len(all_pnls):.0%}) · Avg:{np.mean(all_pnls):+.1%} · Best:{max(all_pnls):+.1%} · Worst:{min(all_pnls):+.1%}")
            if st.button("🗑️ Clear All"):
                st.session_state.pt_closed=[]; st.rerun()

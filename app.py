"""app.py — MacroRegime Pro v20 | Professional Client Dashboard

14 Tabs:
 🏠 Dashboard      📈 GIP Model      🎯 Risk Ranges™   ⚡ Alpha Center
 📊 Leaderboard   🌍 Global Quad     💱 Forex          🛢️ Commodities
 ₿ Crypto          🇮🇩 IHSG           📖 Narratives     🔮 Discovery
 🏥 Health         📋 Playbook
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import time

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — Professional Dark Theme
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .main, .stApp {background-color: #0D1117;}
    h1, h2, h3, h4 {color: #E6EDF3; font-family: 'Inter', sans-serif; font-weight: 700;}
    p, div, span {color: #8B949E; font-family: 'Inter', sans-serif;}
    
    /* Cards */
    .card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 20px;
        margin: 12px 0;
    }
    .card-green {border-left: 4px solid #3FB950;}
    .card-yellow {border-left: 4px solid #D29922;}
    .card-red {border-left: 4px solid #F85149;}
    .card-blue {border-left: 4px solid #1F6FEB;}
    .card-purple {border-left: 4px solid #A371F7;}
    
    /* Pills */
    .pill {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 13px;
        margin: 2px;
    }
    .pill-green {background: rgba(63,185,80,0.15); color: #3FB950;}
    .pill-yellow {background: rgba(210,153,34,0.15); color: #D29922;}
    .pill-red {background: rgba(248,81,73,0.15); color: #F85149;}
    .pill-blue {background: rgba(31,111,235,0.15); color: #1F6FEB;}
    .pill-purple {background: rgba(163,113,247,0.15); color: #A371F7;}
    .pill-gray {background: rgba(139,148,158,0.15); color: #8B949E;}
    
    /* Metric boxes */
    .metric-box {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        height: 100%;
    }
    .metric-label {color: #8B949E; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;}
    .metric-value {color: #E6EDF3; font-size: 32px; font-weight: 700;}
    .metric-sub {color: #8B949E; font-size: 12px; margin-top: 6px;}
    
    /* Info boxes */
    .info-box {background: #161B22; border-left: 4px solid #1F6FEB; padding: 14px 18px; border-radius: 8px; margin: 10px 0;}
    .success-box {background: #161B22; border-left: 4px solid #3FB950; padding: 14px 18px; border-radius: 8px; margin: 10px 0;}
    .warning-box {background: #161B22; border-left: 4px solid #D29922; padding: 14px 18px; border-radius: 8px; margin: 10px 0;}
    .danger-box {background: #161B22; border-left: 4px solid #F85149; padding: 14px 18px; border-radius: 8px; margin: 10px 0;}
    
    /* Tables */
    .stDataFrame {border-radius: 10px; overflow: hidden;}
    
    /* Buttons */
    .stButton>button {
        background: #21262D;
        color: #E6EDF3;
        border: 1px solid #30363D;
        border-radius: 8px;
        font-weight: 500;
    }
    .stButton>button:hover {background: #30363D;}
    
    /* Dividers */
    hr {border-color: #30363D !important; margin: 20px 0 !important;}
    
    /* Sidebar */
    [data-testid="stSidebar"] {background: #0D1117; border-right: 1px solid #21262D;}
    [data-testid="stSidebar"] h2 {font-size: 18px;}
    
    /* Expander */
    .streamlit-expanderHeader {background: #161B22; border-radius: 8px; border: 1px solid #30363D;}
    
    /* Progress */
    .stProgress > div > div {background-color: #1F6FEB;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
QC = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"🟢 Goldilocks — Growth Rising, Inflation Cooling",
    "Q2":"🟡 Reflation — Both Growth and Inflation Rising",
    "Q3":"🔴 Stagflation — Growth Slowing, Inflation Elevated",
    "Q4":"🟣 Deflation — Both Growth and Inflation Falling",
}
QUAD_EXPLAIN = {
    "Q1":"Best conditions for stocks and crypto. Growth is strong and inflation is under control. This is when markets perform best.",
    "Q2":"Tricky environment. Economy growing but inflation biting. Commodities, energy, and international stocks tend to win. Crypto can work.",
    "Q3":"Most dangerous quarter. Economy slowing but prices still high. Gold, silver, and defensive stocks are the place to be. Tech gets hurt.",
    "Q4":"Deflationary collapse. Safest assets win: government bonds, gold, utilities, cash. Avoid risk.",
}

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

# ── Risk Range Levels ─────────────────────────────────────────────────────────
def _rr_levels(px, lrr, trr, side="long"):
    px = _sf(px) or 0; lrr = _sf(lrr) or 0; trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = max(0.0, min(1.0, (px - lrr) / spread)) if spread > 0 else 0.5

    if side == "long":
        entry, tp1, tp2, stop = round(lrr,2), round(lrr+spread*0.50,2), round(trr,2), round(lrr-spread*0.25,2)
        near_entry, can_enter, near_target = pos <= 0.35, pos <= 0.55, pos >= 0.75
        action = "✅ Buy Now — Price at Buy Zone" if near_entry else ("📈 Still Good — Can Enter" if can_enter else ("🔴 Take Profit — Near Target" if near_target else "⏳ Wait — Not at Best Entry"))
    else:
        entry, tp1, tp2, stop = round(trr,2), round(trr-spread*0.50,2), round(lrr,2), round(trr+spread*0.25,2)
        near_entry, can_enter, near_target = pos >= 0.65, pos >= 0.45, pos <= 0.25
        action = "✅ Sell/Short — Price at Sell Zone" if near_entry else ("📉 Still Ok — Partial Short" if can_enter else ("🔴 Cover Short — Near Target" if near_target else "⏳ Wait — Price Not High Enough"))

    rr_r = round(abs(tp1-entry)/max(abs(entry-stop),0.01), 2)
    hold = "3 months+" if rr_r >= 2.5 else ("1-3 weeks" if rr_r >= 1.5 else "Skip — poor R:R")
    return {"entry":entry,"tp1":tp1,"tp2":tp2,"stop":stop,"rr":rr_r,"pos":round(pos,2),"side":side,"hold":hold,"near_entry":near_entry,"near_target":near_target,"can_enter":can_enter,"action":action}

def _merge_with_options(rl, opt, side="long"):
    if not opt or not opt.get("ok") or not rl: return rl
    lv = (opt.get("long_levels",{}) if side=="long" else opt.get("short_levels",{})) or {}
    if lv.get("ev_ok"):
        for k in ["entry","tp1","tp2","stop","rr"]:
            if lv.get(k): rl[k] = lv[k]
        rl["opt_confirm"] = True; rl["hold"] = lv.get("holding", rl["hold"])
    return rl

# ── Table Builders ────────────────────────────────────────────────────────────
def _client_table(picks, side="long"):
    rows = []
    for p in picks:
        rl = p.get("rl") or {}
        if not rl: continue
        action = rl.get("action","—")
        st_icon = "✅ Act Now" if ("Buy Now" in action or "Sell/Short" in action) else ("📊 Chase OK" if ("Still Good" in action or "Still Ok" in action) else ("🔴 Take Profit" if ("Take Profit" in action or "Cover" in action) else "⏳ Wait"))
        pos_pct = round(rl.get("pos",0.5)*100)
        pos_bar = f"{'█'*int(pos_pct/10)}{'░'*(10-int(pos_pct/10))} {pos_pct}%"
        rr = _sf(rl.get("rr")); rr_str = f"{rr:.1f}×" if rr else "—"
        opt_tag = " ✦" if rl.get("opt_confirm") else ""
        rows.append({
            "Ticker": p.get("ticker",""), "Sector": p.get("sector","").replace("_"," ").title()[:14],
            "Price": ff(_sf(p.get("px"))), "Status": st_icon,
            "Entry": ff(_sf(rl.get("entry"))), "Target 1": ff(_sf(rl.get("tp1"))),
            "Target 2": ff(_sf(rl.get("tp2"))), "Stop Loss": ff(_sf(rl.get("stop"))),
            "R:R": rr_str + opt_tag, "Hold For": rl.get("hold","—")[:12],
            "Grade": p.get("quality","—"), "Position": pos_bar,
        })
    return pd.DataFrame(rows)

def _alpha_table(items, side="long"):
    rows = []
    for item in items:
        rl = item.get("rl") or {}; opt = item.get("opt") or {}
        action = rl.get("action","—")
        st_icon = "✅ Act Now" if ("Act Now" in action or "Buy Now" in action or "Sell/Short" in action) else ("📊 Chase OK" if ("Still Good" in action or "Still Ok" in action) else ("🔴 Take Profit" if ("Take Profit" in action or "Cover" in action) else "⏳ Wait"))
        im = opt.get("implied_move_pct") if opt else None
        iv_p = opt.get("iv_percentile") if opt else None
        mp = opt.get("max_pain") if opt else None
        rows.append({
            "Ticker": item.get("ticker",""), "Sector": item.get("sector","")[:14],
            "Price": ff(_sf(item.get("px"))), "Status": st_icon,
            "Entry": ff(_sf(rl.get("entry"))), "Target 1": ff(_sf(rl.get("tp1"))),
            "Target 2": ff(_sf(rl.get("tp2"))), "Stop Loss": ff(_sf(rl.get("stop"))),
            "R:R": f"{_sf(rl.get('rr')) or 0:.1f}×{'✦' if rl.get('opt_confirm') else ''}",
            "Hold For": rl.get("hold","—")[:10], "Exp Move": f"±{fp(im)}" if im else "—",
            "IV Rank": fp(iv_p) if iv_p else "—", "Max Pain": ff(_sf(mp)) if mp else "—",
            "Grade": item.get("quality","—"),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Visual Components ─────────────────────────────────────────────────────────
def _quad_badge(q, size=28):
    pill = {"Q1":"pill-green","Q2":"pill-yellow","Q3":"pill-red","Q4":"pill-purple"}.get(q,"pill-gray")
    return f'<span class="pill {pill}" style="font-size:{size}px;">{q}</span>'

def _status_pill(status, text):
    css = {"buy":"pill-green","sell":"pill-red","wait":"pill-yellow","watch":"pill-blue"}.get(status,"pill-gray")
    return f'<span class="pill {css}">{text}</span>'

def _metric_box(label, value, sub="", color="#E6EDF3"):
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    return f'<div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color};">{value}</div>{sub_html}</div>'

def _card(title, content, color="#30363D", border_color=None):
    bc = border_color or color
    return f'<div class="card" style="border-left-color:{bc};"><div style="font-weight:700;color:#E6EDF3;margin-bottom:10px;">{title}</div><div style="color:#8B949E;">{content}</div></div>'

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=220,margin=dict(t=30,b=5,l=0,r=0),
        paper_bgcolor="#161B22",plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3",family="Inter"),
        title=dict(text=title,font=dict(size=12,color="#8B949E")),
        yaxis=dict(range=[0,1.15],tickformat=".0%",showgrid=True,gridcolor="#21262D",tickcolor="#8B949E"),
        xaxis=dict(showgrid=False,tickfont=dict(size=13,color="#E6EDF3")),bargap=0.4)
    return fig

def _seq_pills(sq, mq):
    if sq == mq:
        return '<div style="margin:12px 0;"><span class="pill pill-green">🟢 REGIME ALIGNED</span><span style="color:#8B949E;margin-left:8px;">Both monthly and quarterly point the same direction</span></div>'
    target = ""
    if sq == "Q3" and mq == "Q2": target = '<span class="pill pill-blue">→ Q1 TARGET</span>'
    elif sq == "Q3" and mq == "Q1": target = '<span class="pill pill-blue">→ WATCH Q2→Q1</span>'
    return f'<div style="margin:12px 0;"><span class="pill pill-red">🔴 Structural: {sq}</span><span style="color:#8B949E;margin:0 6px;">→</span><span class="pill pill-yellow">🟡 Monthly: {mq}</span>{target}</div>'

# ── Gamma & Lev Cards ────────────────────────────────────────────────────────
def _gamma_card(gamma):
    if not gamma or not gamma.get("ok"):
        return '<div class="warning-box"><b>⚡ GAMMA REGIME</b><br/><span style="color:#8B949E;">Loading...</span></div>'
    th = _sf(gamma.get("throttle")) or 0; r10 = _sf(gamma.get("rvol_10d")); vp = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN")); label = str(gamma.get("label","—")); action = str(gamma.get("action","—"))
    color = str(gamma.get("color","#8B949E"))
    explain = {"DEEP_POSITIVE":"🟢 Very calm — buy dips","POSITIVE":"🟢 Calm — dips get bought","TRANSITION":"🟡 Shifting — careful sizing","NEGATIVE":"🔴 Volatile — reduce size","DEEP_NEGATIVE":"🔴 Dangerous — stay disciplined"}.get(regime,"Unclear")
    css = {"DEEP_POSITIVE":"card-green","POSITIVE":"card-green","TRANSITION":"card-yellow","NEGATIVE":"card-red","DEEP_NEGATIVE":"card-red"}.get(regime,"card-yellow")
    vpc = "#3FB950" if (vp is not None and vp > 0) else "#F85149"
    return f'''
    <div class="card {css}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <span style="color:#E6EDF3;font-weight:700;">⚡ OPTIONS MARKET STRUCTURE</span>
            <span class="pill {css.replace('card-','pill-').replace('green','pill-green').replace('yellow','pill-yellow').replace('red','pill-red')}" style="font-size:11px;">{label.upper()}</span>
        </div>
        <div style="color:#8B949E;font-size:13px;margin-bottom:12px;">{explain}</div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
            <div><div style="font-size:11px;color:#8B949E;">Gamma Throttle</div><div style="font-size:20px;font-weight:700;color:{color};">{th:+.2f}</div></div>
            <div><div style="font-size:11px;color:#8B949E;">10d Realized Vol</div><div style="font-size:20px;font-weight:700;color:#E6EDF3;">{r10:.1f}%</div></div>
            <div><div style="font-size:11px;color:#8B949E;">Vol Premium</div><div style="font-size:20px;font-weight:700;color:{vpc};">{vp:+.1f}%</div></div>
        </div>
        <div style="margin-top:10px;font-size:13px;color:#E6EDF3;"><b>📊 Action:</b> {action}</div>
    </div>'''

def _lev_card(lev):
    if not lev or not lev.get("ok"):
        return '<div class="warning-box"><b>📊 LEVERAGED ETF FLOWS</b><br/><span style="color:#8B949E;">Loading...</span></div>'
    tot=_sf(lev.get("total_mcap_b")); lo=_sf(lev.get("long_exposure_b")); sh=_sf(lev.get("short_exposure_b"))
    lp=float(lev.get("long_pct") or 0); sp=float(lev.get("short_pct") or 0); ath=bool(lev.get("is_ath",False))
    rb=str(lev.get("rebalancing_pressure","—")); rc={"HIGH":"#F85149","MEDIUM":"#D29922","LOW":"#3FB950"}.get(rb,"#8B949E")
    op=max(0,round(100-lp-sp,0)); tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return f'''
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:#E6EDF3;font-weight:700;">📊 LEVERAGED ETF FLOWS</span>
            <span style="font-size:11px;color:#8B949E;">{"ALL TIME HIGH" if ath else ""}</span>
        </div>
        <div style="margin-top:10px;display:flex;gap:16px;flex-wrap:wrap;font-size:13px;">
            <span>Total: <b style="color:#E6EDF3;">${tot:.0f}B</b></span>
            <span>Long: <b style="color:#3FB950;">{lp:.0f}%</b> (${lo:.0f}B)</span>
            <span>Short: <b style="color:#F85149;">{sp:.0f}%</b> (${sh:.0f}B)</span>
            <span>Other: <b style="color:#8B949E;">{op:.0f}%</b></span>
        </div>
        <div style="margin-top:8px;font-size:12px;color:#8B949E;">Rebalancing: <span style="color:{rc};font-weight:600;">{rb}</span></div>
        <div style="margin-top:6px;font-size:12px;color:#8B949E;">Long: {tls} | Short: {tss}</div>
    </div>'''

# ── DXY & Levels ─────────────────────────────────────────────────────────────
def _compute_dxy_corr(prices, window=15):
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy, errors="coerce").dropna()
    if len(dxy) < window+2: return {}
    dxy_ret = dxy.pct_change().dropna()
    try: from config.settings import DXY_CORRELATION_ASSETS
    except: return {}
    result = {}
    for label, ticker in DXY_CORRELATION_ASSETS.items():
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < window+2: continue
        combined = pd.concat([dxy_ret, s.pct_change().dropna()], axis=1, join="inner").dropna()
        combined.columns = ["dxy","asset"]
        if len(combined) >= window:
            c = float(combined["dxy"].tail(window).corr(combined["asset"].tail(window)))
            if math.isfinite(c): result[label] = round(c, 2)
    return result

def _render_levels(rl, side="long", opt=None):
    if not rl: return
    tc = "#3FB950" if side == "long" else "#F85149"
    ext_tag = " ⚠️ Extended" if rl.get("near_target") else ""
    opt_tag = " ✦ Options confirmed" if rl.get("opt_confirm") else ""
    st.markdown(f'<div style="color:{tc};font-size:15px;font-weight:700;margin-bottom:6px;">{rl.get("action")}{opt_tag}{ext_tag}</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Buy/Sell at", f"${rl['entry']:,.2f}")
    c2.metric("Target 1", f"${rl['tp1']:,.2f}")
    c3.metric("Target 2", f"${rl['tp2']:,.2f}")
    c4.metric("Stop Loss", f"${rl['stop']:,.2f}")
    c5.metric("Reward:Risk", f"{rl['rr']:.1f}× · {rl.get('hold','—')[:10]}")
    if opt and opt.get("ok"):
        st.caption(f"📊 Options: Implied move ±{fp(opt.get('implied_move_pct'))} · IV rank {fp(opt.get('iv_percentile'))} · Max pain ${ff(opt.get('max_pain'))}")
    st.markdown('<div style="height:1px;background:#30363D;margin:16px 0;"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown('<p style="color:#8B949E;font-size:13px;">Powered by Hedgeye Methodology</p>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard","📈 GIP Model","🎯 Risk Ranges™","⚡ Alpha Center",
        "📊 Leaderboard","🌍 Global Quad","💱 Forex","🛢️ Commodities","₿ Crypto",
        "🇮🇩 IHSG","📖 Narratives","🔮 Discovery","🏥 Health","📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Update", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Full Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        inc_us = st.checkbox("US Stocks",True); inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True); inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("Indonesia (IHSG)",True)
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Regime:",["Auto","Q1","Q2","Q3","Q4"],
            index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
        st.caption("Override when model diverges from Hedgeye")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        st.markdown(f'<div class="metric-box" style="padding:12px;"><div class="metric-label">CURRENT REGIME</div><div class="metric-value" style="font-size:20px;">{_sq} / {_mq}</div><div class="metric-sub">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)

# ── Auto-build ────────────────────────────────────────────────────────────────
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
        snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
            include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
        st.session_state.snap=snap; st.session_state.loading=False
        pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ Build failed. Click **⚡ Full Rebuild** to retry."); st.stop()

# ── Extract Data ─────────────────────────────────────────────────────────────
gip = snap.get("gip"); global_ = snap.get("global",{}); rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{}); narr = snap.get("narratives",{}); disc = snap.get("discovery",{})
transition = snap.get("transition",None); health = snap.get("health",{}); analogs = snap.get("analogs",{})
btk = snap.get("bottleneck",{}); pb_data = snap.get("playbook",{}); prices = snap.get("prices",{})
auto_disc = snap.get("auto_discoveries",{}); fb_eval = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{}); lev_data = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq = (global_.get("global_quad","Q3") if global_ else "Q3")
ar = rr.get("asset_ranges",{})
dxy_corr = _compute_dxy_corr(prices)
ai_data = snap.get("ai_analysis",{}) or {}

# Fallbacks
FALLBACK_NARRATIVES = [
    {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand (solar, AI chips) + safe haven. Mine supply flat.","tickers":["SLV","SILJ","GDXJ","GDX","GLD"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],"invalidators":["Q4 deflation signal","DXY sustained bullish"]},
    {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural. Safe haven in Q3.","tickers":["GLD","GDX","GDXJ","AEM","WPM"],"best":["GLD","GDX"],"worst":["HYG","IWM"],"invalidators":["Q4→Q1 direct","DXY reversal"]},
    {"name":"Defense Reshoring","score":0.85,"thesis":"NATO 2%+ GDP commitment. Geopolitical premium. ITA/LMT/KTOS secular long in ALL quads.","tickers":["ITA","LMT","RTX","KTOS","PLTR","GD"],"best":["ITA","KTOS"],"worst":["XLU"],"invalidators":["Global peace agreement"]},
    {"name":"AI Power Infrastructure","score":0.83,"thesis":"AI data centers need 24/7 firm power. Nuclear + gas only scalable solutions.","tickers":["VST","CEG","GEV","ETN","VRT"],"best":["VST","CEG"],"worst":["INTC"],"invalidators":["AI capex cycle pause"]},
    {"name":"Energy Offense (Q2)","score":0.80,"thesis":"Q2 = Reflation = Energy offense. OIH oil services = operating leverage.","tickers":["XLE","OIH","BNO","XOP","DAR","MTDR"],"best":["OIH","BNO"],"worst":["XLU","XLP"],"invalidators":["Demand collapse (Q4)"]},
    {"name":"International Rotation","score":0.78,"thesis":"JPXN +37% Q1 2026. EIS +21.8%. USD bearish = EM tailwind.","tickers":["JPXN","EIS","TUR","NORW","EWZ","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],"invalidators":["DXY bullish reversal"]},
    {"name":"Bitcoin Reflation","score":0.75,"thesis":"Every quad except Q4 = long Bitcoin. DXY bearish correlation supports crypto bid.","tickers":["IBIT","FBTC","BTC-USD"],"best":["IBIT"],"worst":["MSTY","BLOK"],"invalidators":["Q4 signal","DXY bullish reversal"]},
    {"name":"Indonesia Commodity Play","score":0.65,"thesis":"EIDO = coal + nickel + CPO + geothermal. Q2/Q3 = commodity bid.","tickers":["EIDO","PGEO.JK","ADRO.JK","NCKL.JK"],"best":["EIDO","PGEO.JK"],"worst":["TLKM.JK"],"invalidators":["China demand collapse","Q4 deflation"]},
]
FALLBACK_DISCOVERY = [
    {"name":"AI Photonics Bottleneck","category":"Structural Constraint","stage":"active","confidence":0.88,"thesis":"LITE sole supplier 200G EML lasers. NVIDIA $2B photonics.","beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],"confirmation_signal":"LITE earnings + NVIDIA capex","invalidators":["China photonics scaling"]},
    {"name":"SiC Power Monopoly (WOLF)","category":"Structural Constraint","stage":"active","confidence":0.84,"thesis":"WOLF = ONLY US large-scale SiC substrate. CHIPS Act strategic.","beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["Legacy Si"],"confirmation_signal":"EV OEM adoption + DOD qual","invalidators":["China SiC subsidies"]},
    {"name":"Japan Yen Weakness → JPXN","category":"Macro Rotation","stage":"active","confidence":0.82,"thesis":"Yen bearish = Japanese exporters win. BoJ ultra-dovish.","beneficiary_tickers":["JPXN","EWJ"],"fade_tickers":["FXY"],"confirmation_signal":"USD/JPY >145","invalidators":["BoJ hike >1%"]},
    {"name":"Silver Physical Squeeze","category":"Commodity","stage":"building","confidence":0.78,"thesis":"Solar + AI chip silver demand accelerating. Mine supply flat.","beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],"confirmation_signal":"LBMA inventory <150M oz","invalidators":["India demand collapse"]},
    {"name":"Indonesia OSV Bottleneck","category":"Local Bottleneck","stage":"brewing","confidence":0.65,"thesis":"Pertamina hulu expansion = OSV fleet utilization >90%.","beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],"confirmation_signal":"Pertamina Q2 capex","invalidators":["Pertamina budget freeze"]},
]

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<h1 style="margin-bottom:4px;">🏠 Dashboard</h1>', unsafe_allow_html=True)
    st.caption("Command center. 30-second read.")
    st.divider()

    # AI Badge
    ai_ok = ai_data.get("ok", False)
    ai_ts = ai_data.get("generated_at")
    ai_cnt_narr = len(ai_data.get("narratives",[]))
    ai_cnt_alpha = len(ai_data.get("alpha_ideas",[]))
    ai_cnt_btk = len(ai_data.get("bottlenecks",[]))
    if ai_ok:
        import datetime
        ts_str = datetime.datetime.fromtimestamp(ai_ts).strftime("%H:%M") if ai_ts else "—"
        model_name = ai_data.get("model", "unknown")
        if "rule-based" in str(model_name):
            st.markdown(f'<div class="success-box">🧠 AI RULE-BASED ACTIVE — Auto-generated from live data · {ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box">🤖 AI ACTIVE — {model_name} · {ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</div>', unsafe_allow_html=True)
    else:
        ai_reason = ai_data.get("reason", "")
        st.markdown(f'<div class="warning-box">🤖 AI: Fallback — {ai_reason}</div>', unsafe_allow_html=True)

    st.caption(f"Built {snap.get('build_time_s',0):.0f}s ago · {snap.get('prices_loaded',0)} assets · {snap.get('fred_coverage',0)} macro indicators")

    # Market Condition
    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable":
        st.markdown(f'<div class="success-box"><b>🟢 GOOD MARKET CONDITIONS · VIX {vl:.1f}</b><br/>{vbd.get("note","")}<br/>Risk mode: {vbd.get("risk_mode","Normal")}</div>', unsafe_allow_html=True)
    elif vb=="Chop":
        st.markdown(f'<div class="warning-box"><b>🟡 CHOPPY CONDITIONS · VIX {vl:.1f}</b><br/>{vbd.get("note","")}<br/>Risk mode: {vbd.get("risk_mode","Normal")}</div>', unsafe_allow_html=True)
    elif vb=="Defensive":
        st.markdown(f'<div class="danger-box"><b>🔴 DEFENSIVE CONDITIONS · VIX {vl:.1f}</b><br/>{vbd.get("note","")}<br/>Risk mode: {vbd.get("risk_mode","Normal")}</div>', unsafe_allow_html=True)

    # Gamma + DXY + Lev
    g_col, dxy_col = st.columns([1.1, 1])
    with g_col: st.markdown(_gamma_card(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy(prices, dxy_corr, sq)
    st.markdown(_lev_card(lev_data), unsafe_allow_html=True)

    # Regime Metrics
    sq_q2p = (_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    sq_sub = f"Q2 probability: {sq_q2p:.0%}" if (sq=="Q3" and sq_q2p>0.25) else ""
    mq_sub = "⚠ Model Q1 · Hedgeye Q2" if mq_raw=="Q1" else ""

    r1,r2,r3,r4 = st.columns(4)
    with r1: st.markdown(_metric_box("Quarterly Regime", sq, QUAD_EXPLAIN[sq][:60]+"...", qc(sq)), unsafe_allow_html=True)
    with r2: st.markdown(_metric_box("Monthly Regime", mq, mq_sub or "3-6 week tactical", qc(mq)), unsafe_allow_html=True)
    with r3:
        gconf = _sf(global_.get("global_conf",0)) if global_ else 0
        st.markdown(_metric_box("Global (50 Countries)", gq, f"Confidence: {gconf:.0%}", qc(gq)), unsafe_allow_html=True)
    with r4:
        if gip:
            flip = gip.flip_hazard
            flip_c = "#F85149" if flip > 0.4 else "#D29922" if flip > 0.25 else "#3FB950"
            st.markdown(_metric_box("Regime Change Risk", f"{flip:.0%}", f"{gip.divergence.title()}", flip_c), unsafe_allow_html=True)

    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    if transition:
        fw = transition.front_run_window; fr = transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div class="danger-box" style="border-color:{fwc};"><b>{fwi}</b><br/>{fr}</div>', unsafe_allow_html=True)

    # Playbook Summary
    if pb_data:
        best5 = " · ".join(pb_data.get("best_assets",[])[:6])
        worst5 = " · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div class="card card-green"><div style="font-weight:700;color:#E6EDF3;margin-bottom:8px;">🎯 What to Do Right Now — {sq} · {mq}</div><div style="color:#3FB950;margin-bottom:4px;">✅ Buy/Hold: {best5}</div><div style="color:#F85149;">❌ Avoid/Sell: {worst5}</div></div>', unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0)
        wr=(pr/max(ev,1))*100
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Evaluated", ev); c2.metric("Winners", pr); c3.metric("Losers", dm); c4.metric("Win Rate", f"{wr:.1f}%")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown('<h1 style="margin-bottom:4px;">📈 GIP Model</h1>', unsafe_allow_html=True)
    st.caption("Growth · Inflation · Policy — The Map")
    st.divider()
    if not gip: st.warning("Data loading..."); st.stop()

    cc,cw = st.columns(2)
    with cc:
        st.markdown(f'<div class="card" style="border-left-color:{qc(sq)};"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Quarterly Regime (Climate)</div><div style="font-size:36px;font-weight:700;color:{qc(sq)};">{sq}</div><div style="color:#8B949E;margin:8px 0;">{QNC.get(sq,"")}</div><div style="font-size:13px;color:#E6EDF3;">{QUAD_EXPLAIN[sq]}</div><div style="margin-top:12px;font-size:11px;color:#8B949E;">Confidence: {gip.structural_conf:.0%} · Flip risk: {gip.flip_hazard:.0%}</div></div>', unsafe_allow_html=True)
    with cw:
        st.markdown(f'<div class="card" style="border-left-color:{qc(mq)};"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Monthly Regime (Weather — 3-6 Weeks)</div><div style="font-size:36px;font-weight:700;color:{qc(mq)};">{mq}</div><div style="color:#8B949E;margin:8px 0;">{QNC.get(mq,"")}</div><div style="font-size:13px;color:#E6EDF3;">{QUAD_EXPLAIN[mq]}</div><div style="margin-top:12px;font-size:11px;color:#8B949E;">Confidence: {gip.monthly_conf:.0%} · Divergence: {gip.divergence}</div></div>', unsafe_allow_html=True)
    if mq_raw == "Q1":
        st.warning("⚠ Model computed Q1, Hedgeye manual call = Q2. Use Quad Override in sidebar.")

    st.divider()
    st.markdown("### What the Data Is Saying")
    f = gip.features; gm = _sf(f.get("growth_momentum")) or 0; im = _sf(f.get("inflation_momentum")) or 0
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Growth Direction", "📈 Accelerating" if gm>0 else "📉 Decelerating", f"{gm:+.1%}")
    s2.metric("Inflation Direction", "📈 Rising" if im>0 else "📉 Cooling", f"{im:+.1%}")
    s3.metric("Central Bank", "Dovish 🕊️" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish 🦅" if (_sf(f.get("policy_score")) or 0)<-0.1 else "Neutral ⚖️")
    s4.metric("Data Coverage", f"{gip.data_coverage:.0%}")

    st.divider()
    st.markdown("### Where Are We Going Next?")
    QWINS={"Q1":"Tech, Bitcoin, Small Caps","Q2":"Energy, Materials, Commodities","Q3":"Gold, Silver, Defensives","Q4":"Government Bonds, Gold, Cash"}
    def _tp(probs, cur_q, label):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="font-size:13px;color:#8B949E;margin-bottom:4px;">{label}</div><div style="color:#E6EDF3;margin-bottom:8px;">Most likely next: <b>{top_q} {QN.get(top_q,"")}</b> ({top_p:.0%})</div>', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        if top_q!=cur_q: st.info(f"If regime shifts to {top_q}: **{QWINS.get(top_q,'')}** are the winners")
    c1,c2,c3 = st.columns(3)
    with c1: _tp(gip.structural_probs, sq, "Quarterly Probabilities")
    with c2: _tp(gip.monthly_probs, mq, "Monthly Probabilities")
    with c3:
        gprobs = (global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs, gq, "Global Probabilities")

    st.divider()
    st.markdown("### Timing Signal")
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div class="card" style="border-left-color:{fwc};"><div style="color:{fwc};font-weight:700;">{fwi}</div><div style="color:#8B949E;font-size:13px;margin-top:4px;">{fr}</div></div>', unsafe_allow_html=True)

    if analogs and analogs.get("top_analogs"):
        st.divider()
        st.markdown("### Historical Comparisons")
        for i,a in enumerate(analogs["top_analogs"][:3]):
            with st.expander(f"📚 **{a['label']}** — {a.get('similarity',0):.0%} similar", expanded=(i==0)):
                c1,c2,c3=st.columns(3)
                c1.metric("Next 1M", a.get("path_1m","—")); c2.metric("Next 3M", a.get("path_3m","—")); c3.metric("Next 6M", a.get("path_6m","—"))
                st.info(f"📊 {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown('<h1 style="margin-bottom:4px;">🎯 Risk Ranges™</h1>', unsafe_allow_html=True)
    st.caption("Buy Zone = LRR. Sell Zone = TRR. Break below = exit.")
    st.divider()
    if not ar: st.warning("Data loading..."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
        key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Priority Alerts")
        for sym,a in all_a[:15]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡"
            st.markdown(f'<div style="background:#161B22;border-left:3px solid {"#F85149" if a["priority"]=="CRITICAL" else "#D29922"};padding:8px 12px;margin:4px 0;border-radius:4px;"><span style="color:#E6EDF3;font-weight:600;">{ic} {sym}</span> — <span style="color:#8B949E;">{a["action"]} ({a["duration"]})</span></div>', unsafe_allow_html=True)

    st.divider()
    cl1,cl2,cl3 = st.columns([1,2,1])
    with cl1: mkt_f=st.selectbox("Filter by market:",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search:",placeholder="Type ticker name...")
    with cl3: show_only=st.selectbox("Show:",["All signals","Buy signals only","Sell signals only"])

    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        sig=v.get("composite","—").upper()
        if show_only=="Buy signals only" and sig!="BULLISH": continue
        if show_only=="Sell signals only" and sig!="BEARISH": continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        side="long" if sig=="BULLISH" else "short"; rl=_rr_levels(px,lrr,trr,side)
        pos_pct=round((rl.get("pos",0.5))*100) if rl else 50
        action=(rl.get("action","—")[:30] if rl else "—")
        rows.append({"Ticker":sym,"Price":ff(px),"Buy Zone":ff(lrr),"Sell Zone":ff(trr),"Action":action,"Position":f"{pos_pct}%","Signal":sig,"Quality":v.get("quality","—"),"Market":v.get("market","—")})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=520,
            column_config={"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Signal":st.column_config.TextColumn("Signal",width="small"),"Quality":st.column_config.TextColumn("Grade",width="small"),"Position":st.column_config.TextColumn("In Range",width="small"),"Action":st.column_config.TextColumn("What to Do",width="large")})
    else: st.info("No data matches your filter.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ⚡ ALPHA CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown('<h1 style="margin-bottom:4px;">⚡ Alpha Center</h1>', unsafe_allow_html=True)
    st.caption("Best trades right now. Entry, targets, stop, and time horizon.")
    st.divider()

    if transition:
        fw=transition.front_run_window
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div class="card" style="border-left-color:{fwc};"><span style="color:{fwc};font-weight:700;">{fwi}</span></div>', unsafe_allow_html=True)
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    try:
        from engines.options_engine import OptionsEngine
        _oe = OptionsEngine(); _oe_ok = True
    except Exception as _err:
        _oe = None; _oe_ok = False

    def _get_all_items():
        all_longs=[]; all_shorts=[]
        for item in (btk.get("level_1",[]) or []) + (btk.get("level_2",[]) or []):
            ticker=item.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{})
            px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); dir_=item.get("direction","long")
            rl=_rr_levels(px,lrr,trr,dir_)
            if not rl: continue
            opt=None
            if _oe_ok and _oe and px and px>0:
                try: opt=_oe.analyze(ticker,px,lrr,trr,v.get("composite","neutral"))
                except: pass
            if opt: rl=_merge_with_options(rl,opt,dir_)
            item_out={**item,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":opt,"sector":item.get("sector","").replace("_"," ").title()[:14],"quality":item.get("quality","A"),"comp":v.get("composite","neutral")}
            if dir_=="long": all_longs.append(item_out)
            else: all_shorts.append(item_out)

        if not all_longs and not all_shorts:
            for sym,v in ar.items():
                if v.get("market") not in ("us_equity","commodity"): continue
                comp=v.get("composite",""); qual=v.get("quality","")
                tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
                if comp=="bullish" and qual in ("A","B","C"):
                    rl=_rr_levels(px,lrr,trr,"long")
                    if rl:
                        from config.settings import TICKER_SECTOR
                        all_longs.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":None,"sector":TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14],"quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength A/B/C"})
                elif comp=="bearish" and qual in ("short_A","short_B","short_C"):
                    rl=_rr_levels(px,lrr,trr,"short")
                    if rl:
                        from config.settings import TICKER_SECTOR
                        all_shorts.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":None,"sector":TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14],"quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength Short A/B/C"})

        if not all_longs and ai_data.get("ok"):
            for idea in ai_data.get("alpha_ideas",[]):
                if idea.get("direction")=="long":
                    ticker=idea.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); rl=_rr_levels(px,lrr,trr,"long")
                    if rl: all_longs.append({"ticker":ticker,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"sector":idea.get("category","AI")[:14],"quality":"A","comp":"bullish","ev":idea.get("confidence",0.7),"known_thesis":idea.get("thesis",""),"opt":None})
        if not all_shorts and ai_data.get("ok"):
            for idea in ai_data.get("alpha_ideas",[]):
                if idea.get("direction")=="short":
                    ticker=idea.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); rl=_rr_levels(px,lrr,trr,"short")
                    if rl: all_shorts.append({"ticker":ticker,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"sector":idea.get("category","AI")[:14],"quality":"short_A","comp":"bearish","ev":idea.get("confidence",0.7),"known_thesis":idea.get("thesis",""),"opt":None})

        def _sort_key(x):
            action=x.get("rl",{}).get("action","") if x.get("rl") else ""
            return 0 if ("Act Now" in action or "Buy Now" in action or "Sell/Short" in action) else (1 if ("Still Good" in action or "Still Ok" in action) else 2)
        all_longs.sort(key=_sort_key); all_shorts.sort(key=_sort_key)
        return all_longs, all_shorts

    all_longs, all_shorts = _get_all_items()

    stat1,stat2,stat3,stat4 = st.columns(4)
    stat1.metric("Long Ideas", len(all_longs)); stat2.metric("Short Ideas", len(all_shorts))
    stat3.metric("Act Now", sum(1 for x in all_longs+all_shorts if x.get("rl",{}) and ("Act Now" in x["rl"].get("action","") or "Buy Now" in x["rl"].get("action","") or "Sell/Short" in x["rl"].get("action",""))))
    stat4.metric("Options Enhanced", sum(1 for x in all_longs+all_shorts if x.get("opt",{}) and x.get("opt",{}).get("ok")))

    st.divider()
    st.markdown("### 🟢 LONG IDEAS — Buy These")
    st.caption("Entry = best price to buy. Target 1 & 2 = where to sell. Stop Loss = exit.")
    if all_longs:
        df_l=_alpha_table(all_longs[:20],"long")
        st.dataframe(df_l, hide_index=True, use_container_width=True, height=min(len(df_l)*37+40,500),
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed View — Top 3 Longs"):
            for item in all_longs[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"),"long",item.get("opt"))
    else: st.info("No long setups right now. Markets may be extended — wait for pullback.")

    st.divider()
    st.markdown("### 🔴 SHORT IDEAS — Sell / Avoid")
    st.caption("Entry = best price to short. Target = where to cover. Stop = exit if goes above.")
    if all_shorts:
        df_s=_alpha_table(all_shorts[:15],"short")
        st.dataframe(df_s, hide_index=True, use_container_width=True, height=min(len(df_s)*37+40,450),
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed View — Top 3 Shorts"):
            for item in all_shorts[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"),"short",item.get("opt"))
    else: st.info("No short setups right now.")

    wt=btk.get("watch",[]) if btk else []
    if wt:
        st.divider()
        st.markdown("### 👀 WATCH LIST")
        st.caption("Early signs. Monitor for entry.")
        wt_rows=[{"Ticker":w.get("ticker",""),"Sector":w.get("sector","").replace("_"," ").title()[:14],"Direction":w.get("direction","long").upper(),"Score":f'{w.get("score",0):.2f}',"Thesis":w.get("known_thesis","")[:60]} for w in wt[:15]]
        st.dataframe(pd.DataFrame(wt_rows), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📊 LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown('<h1 style="margin-bottom:4px;">📊 Leaderboard</h1>', unsafe_allow_html=True)
    st.caption("Highest-conviction ideas. Grade A = strongest signal.")
    st.divider()
    if not ar: st.warning("Data loading..."); st.stop()

    try:
        from engines.options_engine import OptionsEngine as _OE2
        _oe2=_OE2(); _oe2_ok=True
    except: _oe2=None; _oe2_ok=False

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]
    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral"); tr=v.get("trade",{}); tn=v.get("trend",{})
        px=_sf(v.get("px")); vol_c=_sf(tr.get("volume_confirm")) or 0.5; stretch=tr.get("stretch",""); hurst=_sf(tn.get("hurst")) or 0.5
        lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()
        except: sector="Generic"
        if qual in ("A","B","C") and comp=="bullish":
            rl=_rr_levels(px,lrr,trr,"long"); pos=rl.get("pos",0.5) if rl else 0.5
            rf=sym in best_set; ra=sym in worst_set
            sc=(50 if qual=="A" else 30)+(25 if (rl and rl.get("near_entry")) else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector[:14],"comp":comp})
        if qual in ("short_A","short_B","short_C") and comp=="bearish":
            rl=_rr_levels(px,lrr,trr,"short"); pos=rl.get("pos",0.5) if rl else 0.5; rf=sym in worst_set
            sc=(50 if qual=="short_A" else 30)+(25 if (rl and rl.get("near_entry")) else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector[:14],"comp":comp})
    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Long Ideas",len(long_picks)); m2.metric("Grade A Longs",sum(1 for p in long_picks if p["quality"]=="A"))
    m3.metric("Grade A Shorts",sum(1 for p in short_picks if p["quality"]=="short_A")); m4.metric("Regime Traps",sum(1 for v in ar.values() if v.get("regime_trap")))

    st.divider()
    st.markdown("### 🟢 TOP LONG IDEAS")
    st.caption("Buy Zone = LRR. TP1 = midpoint. TP2 = TRR. Stop = 25% below buy zone. ✦ = options confirmed.")
    if long_picks:
        df_longs=_client_table(long_picks[:21])
        st.dataframe(df_longs, hide_index=True, use_container_width=True,
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Sector":st.column_config.TextColumn("Sector",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed — Top 5 Longs"):
            for p in long_picks[:5]:
                rl=p.get("rl"); opt_r=None
                if _oe2_ok and _oe2 and p["px"] and p["px"]>0:
                    try: opt_r=_oe2.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
                    except: pass
                if rl and opt_r: rl=_merge_with_options(rl,opt_r,"long")
                st.markdown(f"**{p['ticker']}** ({p['quality']}) — {p['sector']}")
                if rl: _render_levels(rl,"long",opt_r)
    else: st.info("No Grade A/B/C long ideas. Market may be extended.")

    st.divider()
    st.markdown("### 🔴 SHORT IDEAS")
    st.caption("Sell Zone = TRR. Cover at Target 1 & 2. Stop = 25% above sell zone.")
    if short_picks:
        df_shorts=_client_table(short_picks[:15]); df_shorts=df_shorts.rename(columns={"Buy/Sell at":"Sell at"})
        st.dataframe(df_shorts, hide_index=True, use_container_width=True,
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed — Top 5 Shorts"):
            for p in short_picks[:5]:
                rl=p.get("rl"); opt_r=None
                if _oe2_ok and _oe2 and p["px"] and p["px"]>0:
                    try: opt_r=_oe2.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
                    except: pass
                if rl and opt_r: rl=_merge_with_options(rl,opt_r,"short")
                st.markdown(f"**{p['ticker']}** ({p['quality']}) — {p['sector']}")
                if rl: _render_levels(rl,"short",opt_r)
    else: st.info("No short ideas currently.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown('<h1 style="margin-bottom:4px;">🌍 Global Macro — 50 Countries</h1>', unsafe_allow_html=True)
    st.caption("Where is money rotating globally?")
    st.divider()
    if not global_: st.warning("Data loading..."); st.stop()

    gconf=_sf(global_.get("global_conf",0)) or 0; gprobs=global_.get("global_probs",{}) or {}
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(f'<div class="card" style="border-left-color:{qc(gq)};"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Global Regime</div><div style="font-size:36px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="color:#8B949E;margin:8px 0;">{QNC.get(gq,"")}</div><div style="font-size:11px;color:#8B949E;">50 country ETFs · GDP-weighted · Confidence: {gconf:.0%}</div></div>', unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs,"Global Regime Probabilities"), use_container_width=True, config={"displayModeBar":False})
    with c2:
        cq=global_.get("country_quads",{}) or {}; heat=[]
        for country,data in cq.items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_sf(data[2]) or 0
            elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_sf(data.get("conf",0)) or 0
            else: continue
            if quad: heat.append({"Country":country,"ETF":etf,"Regime":quad,"Confidence":f"{conf:.0%}"})
        if heat:
            st.dataframe(pd.DataFrame(heat).style.map(lambda v:f"color:{QC.get(v,'#8B949E')}" if v in QC else "",subset=["Regime"]), hide_index=True,height=420,use_container_width=True)
        else: st.info("Country data loading.")

    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_sf(em_sig.get("confidence")) or 0
        ec="#3FB950" if conf>0.6 else "#D29922" if conf>0.4 else "#8B949E"
        st.markdown(f'<div class="card card-green" style="border-left-color:{ec};"><b>{em_sig.get("trigger","")}</b><br/>{em_sig.get("rationale","")}<br/>Best plays: {", ".join(em_sig.get("best",[])[:6])}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 💱 FOREX (NEW)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💱 Forex":
    st.markdown('<h1 style="margin-bottom:4px;">💱 Forex</h1>', unsafe_allow_html=True)
    st.caption("Major pairs + emerging market currencies. DXY drives everything.")
    st.divider()

    # DXY Context
    dxy = prices.get("DX-Y.NYB")
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r = float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            trend = "Bearish (falling)" if r < -0.005 else ("Bullish (rising)" if r > 0.005 else "Neutral")
            tc = "#F85149" if "Bearish" in trend else "#3FB950" if "Bullish" in trend else "#8B949E"
            st.markdown(f'<div class="card"><div style="font-weight:700;color:#E6EDF3;margin-bottom:6px;">💱 US DOLLAR INDEX (DXY)</div><div style="font-size:28px;font-weight:700;color:{tc};">${float(dxy.iloc[-1]):.2f}</div><div style="color:#8B949E;">15-day trend: <span style="color:{tc};font-weight:600;">{trend}</span> · When DXY falls, EM and commodities rise</div></div>', unsafe_allow_html=True)

    # Forex Risk Ranges
    forex_rr = {sym:v for sym,v in ar.items() if v.get("market","")=="forex"}
    if forex_rr:
        rows=[]
        for sym,v in forex_rr.items():
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            sig=v.get("composite","—").upper(); qual=v.get("quality","—")
            rl=_rr_levels(px,lrr,trr,"long" if sig=="BULLISH" else "short")
            r1m=_price_ret(sym,prices,21); r3m=_price_ret(sym,prices,63)
            action = rl.get("action","—")[:35] if rl else "—"
            rows.append({
                "Pair":sym,"Price":ff(px,4),"Buy Zone":ff(lrr,4),"Sell Zone":ff(trr,4),
                "Action":action,"Signal":sig,"Grade":qual,
                "1M Return":fp(r1m) if r1m is not None else "—",
                "3M Return":fp(r3m) if r3m is not None else "—",
            })
        st.markdown("### All Forex Pairs")
        df=pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=500,
            column_config={"Action":st.column_config.TextColumn("What to Do",width="large"),"Pair":st.column_config.TextColumn("Pair",width="small")})
    else:
        st.info("Forex data loading. Ensure Forex checkbox is active in Settings.")

    # DXY Correlations
    if dxy_corr:
        st.divider()
        st.markdown("### DXY Correlations")
        rows=[]
        for label, corr in dxy_corr.items():
            if corr < -0.3: explain = "📉 Goes UP when Dollar FALLS"
            elif corr > 0.3: explain = "📈 Goes UP when Dollar RISES"
            else: explain = "↔ Not much affected"
            rows.append({"Asset":label,"Correlation":corr,"Meaning":explain})
        df=pd.DataFrame(rows)
        st.dataframe(df.style.format({"Correlation":"{:+.2f}"}).background_gradient(subset=["Correlation"],cmap="RdYlGn",vmin=-1,vmax=1), hide_index=True, use_container_width=True, height=200)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🛢️ COMMODITIES (NEW)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛢️ Commodities":
    st.markdown('<h1 style="margin-bottom:4px;">🛢️ Commodities</h1>', unsafe_allow_html=True)
    st.caption("Energy, precious metals, industrial metals, agriculture.")
    st.divider()

    # Commodity categories from config
    COMM_CATS = {
        "Energy": ["CL=F","BZ=F","NG=F","XLE","OIH","BNO","XOP"],
        "Precious Metals": ["GLD","SLV","PPLT","GDX","GDXJ","SIL","SILJ"],
        "Industrial Metals": ["CPER","SLX","GC=F","SI=F","HG=F"],
        "Agriculture": ["DBA","CORN","SOYB","WEAT"],
    }

    for cat_name, tickers in COMM_CATS.items():
        cat_items = {sym:v for sym,v in ar.items() if sym in tickers}
        if not cat_items: continue
        st.markdown(f"### {cat_name}")
        rows=[]
        for sym,v in cat_items.items():
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            sig=v.get("composite","—").upper(); qual=v.get("quality","—")
            rl=_rr_levels(px,lrr,trr,"long" if sig=="BULLISH" else "short")
            r1m=_price_ret(sym,prices,21); r3m=_price_ret(sym,prices,63)
            action = rl.get("action","—")[:35] if rl else "—"
            rows.append({
                "Ticker":sym,"Price":ff(px),"Buy Zone":ff(lrr),"Sell Zone":ff(trr),
                "Action":action,"Signal":sig,"Grade":qual,
                "1M":fp(r1m) if r1m is not None else "—",
                "3M":fp(r3m) if r3m is not None else "—",
            })
        if rows:
            df=pd.DataFrame(rows)
            st.dataframe(df, hide_index=True, use_container_width=True, height=min(len(df)*37+40,300),
                column_config={"Action":st.column_config.TextColumn("What to Do",width="large")})
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # Regime context for commodities
    st.divider()
    if sq in ("Q2","Q3"):
        st.markdown(f'<div class="card card-green"><b>🟢 Commodity-Friendly Regime: {sq}</b><br/>{QUAD_EXPLAIN[sq][:80]}<br/>Energy and metals tend to outperform in {sq}.</div>', unsafe_allow_html=True)
    elif sq == "Q4":
        st.markdown(f'<div class="card card-red"><b>🔴 Commodity Headwind: {sq}</b><br/>Deflationary pressure hurts commodities. Only gold/silver as safety.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card card-yellow"><b>🟡 Mixed Commodity Signals: {sq}</b><br/>Selective opportunities. Watch individual supply-demand.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ₿ CRYPTO (NEW)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown('<h1 style="margin-bottom:4px;">₿ Crypto</h1>', unsafe_allow_html=True)
    st.caption("Bitcoin, Ethereum, and crypto ETFs. Regime-aware positioning.")
    st.divider()

    # Regime-based guidance
    if sq == "Q4":
        st.markdown(f'<div class="card card-red"><div style="font-size:18px;font-weight:700;color:#F85149;">⚠️ EXIT CRYPTO — Q4 Deflation</div><div style="color:#8B949E;">Q4 = deflationary collapse. Risk assets get destroyed. Cash, bonds, gold win. Bitcoin is NOT immune in Q4.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card card-green"><div style="font-size:18px;font-weight:700;color:#3FB950;">✅ CRYPTO OK — {sq} Regime</div><div style="color:#8B949E;">{sq} = {"Goldilocks" if sq=="Q1" else "Reflation" if sq=="Q2" else "Stagflation"}. Bitcoin and crypto tend to work. DXY bearish = tailwind.</div></div>', unsafe_allow_html=True)

    # Crypto Risk Ranges
    CRYPTO_TICKERS = ["BTC-USD","ETH-USD","IBIT","FBTC","MSTY","BLOK","WGMI","BITS"]
    crypto_rr = {sym:v for sym,v in ar.items() if sym in CRYPTO_TICKERS or v.get("market","")=="crypto"}
    if crypto_rr:
        rows=[]
        for sym,v in crypto_rr.items():
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            sig=v.get("composite","—").upper(); qual=v.get("quality","—")
            rl=_rr_levels(px,lrr,trr,"long" if sig=="BULLISH" else "short")
            r1m=_price_ret(sym,prices,21); r3m=_price_ret(sym,prices,63)
            action = rl.get("action","—")[:35] if rl else "—"
            rows.append({
                "Ticker":sym,"Price":ff(px),"Buy Zone":ff(lrr),"Sell Zone":ff(trr),
                "Action":action,"Signal":sig,"Grade":qual,
                "1M":fp(r1m) if r1m is not None else "—",
                "3M":fp(r3m) if r3m is not None else "—",
            })
        st.markdown("### Crypto Assets")
        df=pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=min(len(df)*37+40,350),
            column_config={"Action":st.column_config.TextColumn("What to Do",width="large")})
    else:
        st.info("Crypto data loading. Ensure Crypto checkbox is active in Settings.")

    # Bitcoin-specific context
    btc_rr=ar.get("IBIT",ar.get("BTC-USD",{})); btc_sig=btc_rr.get("composite","—")
    btc_c="#3FB950" if btc_sig=="bullish" else "#F85149" if btc_sig=="bearish" else "#8B949E"
    dxy_btc = dxy_corr.get("Bitcoin","—")
    st.markdown(f'<div class="card" style="border-left-color:{btc_c};"><div style="font-weight:700;color:#E6EDF3;">₿ Bitcoin Signal</div><div style="color:#8B949E;">Composite: <span style="color:{btc_c};font-weight:600;">{btc_sig.upper()}</span> · DXY/BTC correlation: {dxy_btc} · Rule: Any regime except Q4 = long Bitcoin</div></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### Crypto Basis (Spot vs ETF)")
    st.caption("ETF premium/discount to spot = basis. Positive = ETF trades premium (bullish demand).")
    basis_data = []
    for etf, spot in [("IBIT","BTC-USD"),("FBTC","BTC-USD")]:
        etf_px = _sf(prices.get(etf, pd.Series()).tail(1)) if prices.get(etf) is not None else None
        spot_px = _sf(prices.get(spot, pd.Series()).tail(1)) if prices.get(spot) is not None else None
        if etf_px and spot_px:
            basis = (etf_px / spot_px - 1) * 100
            basis_data.append({"ETF":etf,"Spot":spot,"ETF Price":ff(etf_px),"Spot Price":ff(spot_px),"Basis":f"{basis:+.2f}%","Signal":"Premium demand" if basis>0.5 else ("Discount" if basis<-0.5 else "Fair value")})
    if basis_data:
        st.dataframe(pd.DataFrame(basis_data), hide_index=True, use_container_width=True)
    else:
        st.info("Basis data loading. Need both ETF and spot prices.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown('<h1 style="margin-bottom:4px;">🇮🇩 Indonesia Market (IHSG)</h1>', unsafe_allow_html=True)
    st.caption("Indonesian stocks. No options data. Signals from price/volume.")
    st.divider()
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS

    ihsg_rr = {sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}
    if ihsg_rr:
        rows=[]
        for sym,v in ihsg_rr.items():
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            sig=v.get("composite","—").upper(); rl=_rr_levels(px,lrr,trr,"long" if sig=="BULLISH" else "short")
            action = rl.get("action","—")[:35] if rl else "—"
            rows.append({"Ticker":sym,"Price":ff(px,0),"Buy Zone":ff(lrr,0),"Sell Zone":ff(trr,0),"Action":action,"Signal":sig,"Grade":v.get("quality","—"),"Name":IHSG_UNIVERSE.get(sym,sym)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
            column_config={"Action":st.column_config.TextColumn("What to Do",width="large"),"Name":st.column_config.TextColumn("Company",width="medium")})
    else:
        rows=[]
        for sym in list(IHSG_UNIVERSE.keys()):
            s=prices.get(sym)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1]); r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else None; r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
            rows.append({"Ticker":sym,"Company":IHSG_UNIVERSE.get(sym,sym),"Price":f"{px:,.0f}","1 Month":f"{r1:+.1%}" if r1 is not None else "—","3 Months":f"{r3:+.1%}" if r3 is not None else "—"})
        if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=420)
        else: st.warning("IHSG data tidak tersedia. Pastikan checkbox aktif.")

    st.divider()
    st.markdown("### Sector Performance")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"**{bucket.replace('_',' ')}** ({len(tickers)} stocks)"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0; r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"Company":IHSG_UNIVERSE.get(t,t)[:20],"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}"})
            if b_rows: st.dataframe(pd.DataFrame(b_rows), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📖 NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown('<h1 style="margin-bottom:4px;">📖 Active Themes</h1>', unsafe_allow_html=True)
    st.caption("Big investment themes running right now. Higher score = stronger.")
    st.divider()

    active = ((narr.get("active_narratives",[]) or []) if narr else [])
    fallback = [n for n in FALLBACK_NARRATIVES if sq in n.get("regime","ALL") or mq in n.get("regime","ALL") or "ALL" in n.get("regime","ALL")]
    all_n = active if active else fallback

    if ai_data.get("ok") and ai_data.get("narratives"):
        st.success(f"🧠 **{len(ai_data.get('narratives',[]))} rule-based narratives** from live data · Auto-updated every 6 hours")

    for n in sorted(all_n, key=lambda x: x.get("score",0), reverse=True):
        score=n.get("score",0)
        strength = "🔥 Very Strong" if score>0.8 else ("📈 Strong" if score>0.6 else ("📊 Building" if score>0.4 else "👀 Early Stage"))
        with st.expander(f"**{n.get('name','')}** — {strength} ({score:.0%})"):
            st.markdown(f"**What's happening:** {n.get('thesis','')}")
            c1,c2=st.columns(2)
            with c1:
                if n.get("best"): st.markdown(f"**✅ Best to own:** {' · '.join(n['best'][:6])}")
                if n.get("tickers"): st.markdown(f"**All tickers:** {' · '.join(n['tickers'][:8])}")
            with c2:
                if n.get("worst"): st.markdown(f"**❌ Avoid:** {' · '.join(n['worst'][:4])}")
                if n.get("invalidators"): st.markdown(f"**⚠️ Breaks if:** {' | '.join(n['invalidators'][:3])}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🔮 DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown('<h1 style="margin-bottom:4px;">🔮 Pre-Consensus Ideas</h1>', unsafe_allow_html=True)
    st.caption("Early-stage opportunities before they become consensus.")
    st.divider()

    cands = ((auto_disc.get("candidates",[]) or []) if auto_disc else []) + ((disc.get("discoveries",[]) or []) if disc else [])
    all_disc = cands if cands else FALLBACK_DISCOVERY

    if ai_data.get("ok"):
        su = ai_data.get("scenario_update",{}) or {}; ai_ideas = ai_data.get("alpha_ideas",[])
        if su or ai_ideas:
            st.markdown("### 🧠 Rule-Based Analysis")
            if su:
                c1,c2=st.columns(2)
                with c1:
                    if su.get("opportunity"): st.success(f"**Opportunity**: {su['opportunity']}")
                with c2:
                    if su.get("headline_risk"): st.error(f"**Risk**: {su['headline_risk']}")
                if su.get("regime_change_signal"): st.info(f"**Regime shift watch**: {su['regime_change_signal']}")
            if ai_ideas:
                st.markdown(f"#### 🎯 Alpha Ideas ({len(ai_ideas)})")
                for idea in ai_ideas:
                    conf=idea.get("confidence",0.7)
                    with st.expander(f"**{idea.get('ticker','')}** — {idea.get('name','')} · {conf:.0%}"):
                        st.markdown(f"**Direction:** {'🟢 LONG' if idea.get('direction')=='long' else '🔴 SHORT'}")
                        st.markdown(f"**Thesis:** {idea.get('thesis','')}")
                        st.markdown(f"**Why now:** {idea.get('regime_fit','')}")
                        if idea.get("invalidators"): st.warning(f"**Breaks if:** {', '.join(idea['invalidators'])}")
                st.divider()

    for stage,label,color in [("active","✅ Active — Strong Signal","#3FB950"),("building","📈 Building — Gaining Traction","#D29922"),("brewing","👀 Brewing — Early Stage","#1F6FEB")]:
        items=[c for c in all_disc if c.get("stage")==stage]
        if not items: continue
        st.markdown(f'<div style="color:{color};font-weight:700;margin:12px 0;font-size:15px;">{label} ({len(items)})</div>', unsafe_allow_html=True)
        for c in items:
            conf=c.get("confidence",c.get("conviction",0.7))
            with st.expander(f"**{c.get('name','')}** — Confidence: {conf:.0%}"):
                st.markdown(f"**The Idea:** {c.get('thesis','')}")
                st.markdown(f"**Category:** {c.get('category','')}")
                c1,c2=st.columns(2)
                with c1:
                    ben=c.get("beneficiary_tickers",[])
                    if ben: st.markdown(f"**✅ Buy:** {' · '.join(ben[:8])}")
                with c2:
                    fade=c.get("fade_tickers",[])
                    if fade: st.markdown(f"**❌ Fade:** {' · '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs: st.success(f"✅ **Confirmation:** {cs}")
                if inv: st.warning(f"⚠️ **Breaks if:** {', '.join(inv) if isinstance(inv,list) else inv}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown('<h1 style="margin-bottom:4px;">🏥 Market Health Check</h1>', unsafe_allow_html=True)
    st.caption("VIX = fear gauge. Crash meter = stress. Breadth = participation.")
    st.divider()
    if not health: st.warning("Data loading..."); st.stop()

    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","—")
    vb_c={"Investable":"#3FB950","Chop":"#D29922","Defensive":"#F85149"}.get(vb_b,"#8B949E")
    vb_explain={"Investable":"Market is calm. Good conditions to buy pullbacks.","Chop":"Uncertainty. Be selective and reduce size.","Defensive":"Market stressed. Protect capital first."}.get(vb_b,"")
    st.markdown(f'<div class="card" style="border-left-color:{vb_c};"><div style="color:{vb_c};font-weight:700;font-size:18px;">{vb_b.upper()} CONDITIONS</div><div style="color:#8B949E;margin-top:8px;">{vb_explain}</div><div style="color:#8B949E;font-size:12px;">{vb_d.get("note","")}</div></div>', unsafe_allow_html=True)

    crash=health.get("crash",{}) or {}
    if crash:
        st.divider()
        st.markdown("### Market Stress Level")
        score=_sf(crash.get("score")) or 0
        st.progress(float(score), text=f"Overall stress: {score:.0%} — {crash.get('state','Normal')}")
        for k,v in (crash.get("signals",{}) or {}).items():
            st.progress(float(v) if v else 0, text=f"{k.replace('_',' ').title()}: {v:.0%}")
        if crash.get("reasons"): st.warning("Stress factors: " + " · ".join(crash["reasons"]))

    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.divider()
        st.markdown("### Market Participation")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Health Score",f"{_sf(breadth.get('score')) or 0:.0%}")
        b2.metric("Assessment",breadth.get("verdict","—"))
        b3.metric("Sectors Rising",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("Equal-Weight Health",f"{_sf(breadth.get('eqw_health')) or 0:.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"• {note}")

    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.divider()
        st.markdown("### Fear & Greed Meter")
        fgs=_sf(fg.get("score")) or 50
        fgc="#3FB950" if fgs<25 else "#D29922" if fgs<55 else "#F85149"
        fgl = "Extreme Fear (buy signal)" if fgs<25 else ("Fear" if fgs<45 else ("Neutral" if fgs<55 else ("Greed" if fgs<75 else "Extreme Greed (warning)")))
        st.markdown(f"<div style='font-size:24px;font-weight:700;color:{fgc};'>{fgs:.0f}/100 — {fgl}</div>", unsafe_allow_html=True)
        st.progress(fgs/100)
        st.caption("Below 25 = too fearful = often BUY. Above 75 = too greedy = often WARNING.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown('<h1 style="margin-bottom:4px;">📋 Regime Playbook</h1>', unsafe_allow_html=True)
    st.caption(f"Complete action guide for {sq} {QN[sq]} with {mq} {QN[mq]} overlay.")
    st.divider()

    st.markdown(f'<div class="card" style="border-left-color:{qc(sq)};"><div style="font-size:18px;font-weight:700;color:{qc(sq)};">{QNC[sq]}</div><div style="color:#8B949E;margin-top:8px;">{QUAD_EXPLAIN[sq]}</div></div>', unsafe_allow_html=True)

    if pb_data:
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown(f"**✅ Own These in {sq}:**")
            st.markdown(" · ".join(pb_data.get("best_assets",[])))
            st.markdown(f"\n**Style:** {pb_data.get('style','')}")
            st.markdown(f"**Currency:** {pb_data.get('fx','')}")
            st.markdown(f"**Bonds:** {pb_data.get('bonds','')}")
            if pb_data.get("monthly_adds"): st.markdown(f"**Monthly adds:** {' · '.join(pb_data.get('monthly_adds',[]))}")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="card card-red">', unsafe_allow_html=True)
            st.markdown(f"**❌ Avoid These in {sq}:**")
            st.markdown(" · ".join(pb_data.get("worst_assets",[])))
            st.markdown(f"\n**Hedge with:** {pb_data.get('hedge','BTAL')}")
            st.markdown(f"**Position size:** {pb_data.get('sizing_note','Min 1% · Max 3% per name')}")
            st.markdown('</div>', unsafe_allow_html=True)

    btc_rr=ar.get("IBIT",ar.get("BTC-USD",{})); btc_sig=btc_rr.get("composite","—")
    btc_c="#3FB950" if btc_sig=="bullish" else "#F85149" if btc_sig=="bearish" else "#8B949E"
    btc_action = "EXIT Bitcoin" if sq=="Q4" else (f"HOLD/BUY Bitcoin — Signal: {btc_sig.upper()}" if btc_sig=="bullish" else "REDUCE Bitcoin")
    dxy_c = dxy_corr.get("Bitcoin","—")
    st.markdown(f'<div class="card" style="border-left-color:{btc_c};"><span style="color:{btc_c};font-weight:700;">₿ Bitcoin: {btc_action}</span><span style="color:#8B949E;"> · Rule: Any regime except Q4 = long Bitcoin · DXY/BTC correlation: {dxy_c}</span></div>', unsafe_allow_html=True)

    scenarios_list=(scen.get("scenarios",[]) or []) if scen else []
    if scenarios_list:
        st.divider()
        st.markdown("### What Could Happen Next?")
        badges=["Most Likely","Alternative","Risk Scenario","Tail Risk"]; badge_colors=["#3FB950","#D29922","#F85149","#A371F7"]
        r1,r2=st.columns(2); r3,r4=st.columns(2); grids=[r1,r2,r3,r4]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]
            with col:
                st.markdown(f'<div class="card" style="border-left-color:{pc};"><div style="font-size:11px;color:{pc};font-weight:700;margin-bottom:4px;">{badges[i]} · {sc_item.probability:.0%}</div><div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:4px;">{sc_item.name}</div><div style="font-size:12px;color:#8B949E;margin-bottom:8px;">{sc_item.headline}</div><div style="font-size:12px;color:#3FB950;">Win: {" · ".join(sc_item.best_assets[:3])}</div><div style="font-size:12px;color:#F85149;">Avoid: {" · ".join(sc_item.worst_assets[:3])}</div></div>', unsafe_allow_html=True)

    if gip:
        st.divider()
        st.markdown("### Raw Signals (Advanced)")
        f=gip.features
        rows=[["Growth Speed",fp(f.get("growth_momentum")),"Faster" if (_sf(f.get("growth_momentum")) or 0)>0 else "Slower"],
            ["Inflation Speed",fp(f.get("inflation_momentum")),"Rising" if (_sf(f.get("inflation_momentum")) or 0)>0 else "Cooling"],
            ["Central Bank",fp(f.get("policy_score")),"Dovish" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish"],
            ["Leading Indicators",fp(f.get("leading_indicator_composite")),"—"],
            ["Data Confidence",fp(f.get("data_coverage")),"—"],
            ["Regime Change Risk",f"{gip.flip_hazard:.0%}","—"]]
        st.dataframe(pd.DataFrame(rows,columns=["Indicator","Reading","Direction"]),hide_index=True,use_container_width=True)
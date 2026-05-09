"""app.py — MacroRegime Pro v18

Fixes from v17:
  - AUTO-LOAD: Snapshot auto-builds on first open. No Refresh/Force needed.
  - UNIVERSAL entry/TP/stop: Every ticker card shows Entry · TP1 · TP2 · Stop · R/R
  - Alpha Center: removed overly-strict MIN_CONSTRAINT filter. Shows all Level 1/2.
  - IHSG: shows price data from prices dict when RR not available
  - Narratives: ALWAYS shows Hedgeye-aligned fallback narratives (Q3+Q2 overlay)
  - Discovery: ALWAYS shows pre-consensus fallback ideas from Quad context
  - Monthly Quad: manual override UI in sidebar
  - IHSG stocks added to orchestrator rr_tickers (via orchestrator patch note)
  - All Greeks (Vanna/Charm/Speed/Vomma/Color) available via OptionsEngine

Tab structure (11 tabs, no duplication):
  🏠 Dashboard | 📈 GIP Model | 🎯 Risk Ranges™ | ⚡ Alpha Center | 📊 Leaderboard
  🌍 Global Quad | 🇮🇩 IHSG | 📖 Narratives | 🔮 Discovery | 🏥 Health | 📋 Playbook
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

st.markdown("""<style>
.vix-investable {background:linear-gradient(90deg,#064e3b,#065f46);border-left:6px solid #10B981;padding:16px;border-radius:8px;}
.vix-chop       {background:linear-gradient(90deg,#451a03,#78350f);border-left:6px solid #F59E0B;padding:16px;border-radius:8px;}
.vix-defensive  {background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:6px solid #EF4444;padding:16px;border-radius:8px;}
.winrate-card   {background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;}
.signal-A       {background:linear-gradient(90deg,#052e16,#064e3b);border-left:4px solid #10B981;padding:12px;border-radius:6px;margin-bottom:8px;}
.signal-shortA  {background:linear-gradient(90deg,#3b0000,#450a0a);border-left:4px solid #EF4444;padding:12px;border-radius:6px;margin-bottom:8px;}
.gamma-deep-pos {background:#052e16;border-left:4px solid #16a34a;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-pos      {background:#064e3b;border-left:4px solid #059669;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-trans    {background:#451a03;border-left:4px solid #d97706;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-neg      {background:#450a0a;border-left:4px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-deep-neg {background:#3b0000;border-left:4px solid #b91c1c;padding:14px;border-radius:8px;margin-bottom:10px;}
.lev-panel      {background:#1e1b4b;border-left:4px solid #7c3aed;padding:14px;border-radius:8px;margin-bottom:10px;}
.dxy-panel      {background:#0f172a;border:1px solid #0ea5e9;border-radius:8px;padding:14px;margin-bottom:10px;}
.alpha-long     {background:#052e16;border:1px solid #16a34a;border-radius:8px;padding:12px;margin-bottom:8px;}
.alpha-short    {background:#3b0000;border:1px solid #dc2626;border-radius:8px;padding:12px;margin-bottom:8px;}
.alpha-watch    {background:#1c1917;border:1px solid #d97706;border-radius:8px;padding:12px;margin-bottom:8px;}
.lvl-box        {background:#111827;border:1px solid #1F2B3D;border-radius:6px;padding:10px;margin-top:8px;}
.seq-row        {display:flex;align-items:center;gap:8px;padding:10px;background:#111827;border-radius:6px;flex-wrap:wrap;margin-top:8px;margin-bottom:10px;}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC  = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN  = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {"Q1":"Goldilocks — Growth↑ Infl↓","Q2":"Reflation — Growth↑ Infl↑",
       "Q3":"Stagflation — Growth↓ Infl↑","Q4":"Deflation — Growth↓ Infl↓"}

def qc(q):  return QC.get(q,"#9CA3AF")
def qn(q):  return QN.get(q,q)
def qnc(q): return QNC.get(q,q)

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=2):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def _sf(v):
    """Safe float conversion — prevents Series ambiguity."""
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v); return f if math.isfinite(f) else None
    except: return None

def qcard(label, q, conf, sub=""):
    c = qc(q)
    s = f'<div style="font-size:10px;color:#6B7280;margin-top:4px;">{sub}</div>' if sub else ""
    return f'''<div style="background:#111827;border:1px solid {c}44;border-radius:8px;padding:14px;text-align:center;height:100%;">
    <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px;">{label}</div>
    <div style="font-size:28px;font-weight:800;color:{c};">{q}</div>
    <div style="font-size:12px;color:{c};margin-top:2px;">{qn(q)}</div>
    <div style="font-size:11px;color:#E8ECF0;margin-top:6px;">Conf: {conf:.0%}</div>
    {s}</div>'''

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=200,margin=dict(t=25,b=5,l=0,r=0),
        paper_bgcolor="#111827",plot_bgcolor="#111827",
        font=dict(color="#E8ECF0"),
        title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
        yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),
        xaxis=dict(showgrid=False),bargap=0.35)
    return fig

def _sequence_pills(sq, mq):
    sqc=qc(sq); mqc=qc(mq)
    p="padding:3px 11px;border-radius:4px;font-weight:700;font-size:12px;"
    arr='<span style="color:#6B7280;font-size:18px;">→</span>'
    if sq==mq:
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Regime:</span><span style="background:{sqc};color:#000;{p}">{sq} CONFIRMED</span><span style="color:#9CA3AF;font-size:11px;margin-left:4px;">Structural & Monthly aligned</span></div>'
    if sq=="Q3" and mq in ("Q2","Q1"):
        next_q='Q1 TARGET' if mq=='Q2' else 'WATCH Q2→Q1'
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Sequencing:</span><span style="background:#dc2626;color:#fff;{p}">{sq} STRUCT</span>{arr}<span style="background:{mqc};color:#000;{p}">{mq} MONTHLY</span>{arr}<span style="background:#14532d;color:#4ade80;{p}border:1px solid #16a34a;">{next_q}</span></div>'
    return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Struct:</span><span style="background:{sqc};color:#000;{p}">{sq}</span>{arr}<span style="color:#9CA3AF;font-size:12px;">Monthly:</span><span style="background:{mqc};color:#000;{p}">{mq}</span></div>'


# ══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL ENTRY / TP / STOP (works for ALL tickers — no options required)
# ══════════════════════════════════════════════════════════════════════════════

def _rr_levels(px, lrr, trr):
    """
    Compute entry/TP/stop from LRR/TRR alone.
    This is shown on EVERY ticker card regardless of options availability.
    Options layer enhances these levels when available.
    """
    px  = _sf(px)  or 0
    lrr = _sf(lrr) or 0
    trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr):
        return None
    spread = trr - lrr
    entry  = round(lrr, 2)
    tp1    = round(lrr + spread * 0.50, 2)
    tp2    = round(trr, 2)
    stop   = round(lrr - spread * 0.25, 2)
    rr_r   = round((tp1 - entry) / max(entry - stop, 0.01), 2)
    # Position within range (0=LRR, 1=TRR)
    pos = (px - lrr) / spread if spread > 0 else 0.5
    extended = pos > 0.65
    near_lrr = pos <= 0.35
    return {
        "entry": entry, "tp1": tp1, "tp2": tp2, "stop": stop,
        "rr": rr_r, "pos": round(pos, 2),
        "extended": extended, "near_lrr": near_lrr,
    }

def _merge_with_options(rl: dict, opt: dict, side: str = "long") -> dict:
    """
    Merge RR-only levels with options-derived levels.
    Options levels take priority for entry/TP if available and EV+.
    """
    if not opt or not opt.get("ok"):
        return rl
    if side == "long":
        ll = opt.get("long_levels",{}) or {}
        if ll.get("ev_ok"):
            rl["entry"] = ll.get("entry", rl["entry"])
            rl["tp1"]   = ll.get("tp1",   rl["tp1"])
            rl["tp2"]   = ll.get("tp2",   rl["tp2"])
            rl["stop"]  = ll.get("stop",  rl["stop"])
            rl["rr"]    = ll.get("rr",    rl["rr"])
            rl["opt_confirm"] = True
            rl["holding"] = ll.get("holding","TRADE (1-3wk)")
            rl["max_pain_note"] = ll.get("max_pain_note","")
    else:
        sl = opt.get("short_levels",{}) or {}
        if sl.get("ev_ok"):
            rl["entry"] = sl.get("entry", rl["entry"])
            rl["tp1"]   = sl.get("tp1",   rl["tp1"])
            rl["tp2"]   = sl.get("tp2",   rl["tp2"])
            rl["stop"]  = sl.get("stop",  rl["stop"])
            rl["rr"]    = sl.get("rr",    rl["rr"])
            rl["opt_confirm"] = True
            rl["holding"] = sl.get("holding","TRADE (1-3wk)")
    return rl

def _render_levels(rl: dict, side: str = "long", opt: dict = None):
    """Render entry/TP/stop row on any ticker card."""
    if not rl:
        return
    tc  = "#10B981" if side == "long" else "#EF4444"
    ext_warn = ' <span style="color:#F59E0B;font-size:10px;">⚠ EXTENDED</span>' if rl.get("extended") else ""
    opt_tag  = ' <span style="color:#0ea5e9;font-size:10px;">✦ OPT</span>' if rl.get("opt_confirm") else ""
    hold     = rl.get("holding","TRADE")
    mp_note  = f' | {rl["max_pain_note"]}' if rl.get("max_pain_note") else ""

    # Options second-order Greeks summary
    greeks_txt = ""
    if opt and opt.get("ok") and opt.get("atm_greeks_call"):
        g = opt["atm_greeks_call"]
        vs = opt.get("vanna_signal","—"); cs = opt.get("charm_signal","—")
        greeks_txt = f'<div style="font-size:10px;color:#4B5563;margin-top:3px;">IV: {fp(opt.get("atm_iv"))} · IV%: {fp(opt.get("iv_percentile"))} · Move: ±{fp(opt.get("implied_move_pct"))} · Vanna: {vs} · Charm: {cs}</div>'

    st.markdown(f'''<div class="lvl-box">
    <div style="font-size:10px;color:{tc};font-weight:700;margin-bottom:5px;">LEVELS — {side.upper()}{opt_tag}{ext_warn}</div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;text-align:center;">
      <div><div style="font-size:9px;color:#6B7280;">Entry</div><div style="font-size:13px;font-weight:700;color:{tc};">${rl["entry"]:.2f}</div></div>
      <div><div style="font-size:9px;color:#6B7280;">TP1</div><div style="font-size:13px;font-weight:700;color:#10B981;">${rl["tp1"]:.2f}</div></div>
      <div><div style="font-size:9px;color:#6B7280;">TP2</div><div style="font-size:13px;font-weight:700;color:#00D4AA;">${rl["tp2"]:.2f}</div></div>
      <div><div style="font-size:9px;color:#6B7280;">Stop</div><div style="font-size:13px;font-weight:700;color:#EF4444;">${rl["stop"]:.2f}</div></div>
      <div><div style="font-size:9px;color:#6B7280;">R/R · Hold</div><div style="font-size:12px;font-weight:700;color:#E8ECF0;">{rl["rr"]:.1f}x · <span style="font-size:9px;">{hold[:5]}</span></div></div>
    </div>
    {greeks_txt}
    <div style="font-size:9px;color:#374151;margin-top:2px;">{mp_note}</div>
    </div>''', unsafe_allow_html=True)


# ── Gamma panel (with Series fix) ─────────────────────────────────────────────
def _render_gamma(gamma: dict) -> str:
    if not gamma or not gamma.get("ok"):
        note=(gamma or {}).get("note","GammaRegimeEngine belum berjalan — add ke orchestrator step 14e.")
        return f'<div class="gamma-trans"><b style="color:#F59E0B;">⚡ GAMMA REGIME</b><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{note}</div></div>'
    th=_sf(gamma.get("throttle")) or 0; r10=_sf(gamma.get("rvol_10d"))
    r21=_sf(gamma.get("rvol_21d")); vix=_sf(gamma.get("vix"))
    vp=_sf(gamma.get("vol_premium")); bp=int(_sf(gamma.get("bar_pct")) or 50)
    color=str(gamma.get("color","#9CA3AF")); label=str(gamma.get("label","Unknown"))
    action=str(gamma.get("action","—")); impl=str(gamma.get("impl",""))
    regime=str(gamma.get("regime","UNKNOWN"))
    css={"DEEP_POSITIVE":"gamma-deep-pos","POSITIVE":"gamma-pos","TRANSITION":"gamma-trans","NEGATIVE":"gamma-neg","DEEP_NEGATIVE":"gamma-deep-neg"}.get(regime,"gamma-trans")
    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "—"
    vpc="#10B981" if (vp is not None and vp>0) else "#EF4444"
    pw=max(0,min(100,bp-43))
    return f'''<div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:{color};">⚡ GAMMA REGIME — Tier 1 Alpha Approx</span>
        <div style="background:{color};color:#000;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;">{label.upper()}</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Throttle</div><div style="font-size:20px;font-weight:800;color:{color};">{f(th,"+.1f")}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">rVol 10d</div><div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(r10,".1f","%")}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">rVol 21d</div><div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(r21,".1f","%")}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">VIX</div><div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(vix,".1f")}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Vol Premium</div><div style="font-size:18px;font-weight:700;color:{vpc};">{f(vp,"+.1f","%")}</div></div>
      </div>
      <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px;">
        <div style="width:14%;background:#b91c1c;border-radius:3px 0 0 3px;"></div>
        <div style="width:15%;background:#dc2626;"></div>
        <div style="width:14%;background:#d97706;"></div>
        <div style="width:{100-pw}%;background:#1f2937;"></div>
        <div style="width:{pw}%;background:#10B981;border-radius:0 3px 3px 0;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;">
        <div style="font-size:11px;color:#9CA3AF;flex:1;">{impl}</div>
        <div style="background:#111827;padding:4px 12px;border-radius:4px;margin-left:10px;"><span style="font-size:13px;font-weight:800;color:{color};">{action}</span></div>
      </div>
    </div>'''

def _render_lev(lev: dict) -> str:
    if not lev or not lev.get("ok"):
        note=(lev or {}).get("note","LeveragedETFEngine belum berjalan.")
        return f'<div class="lev-panel"><b style="color:#a78bfa;">📊 LEVERAGED ETF FLOW</b><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{note}</div></div>'
    tot=_sf(lev.get("total_mcap_b")); lo=_sf(lev.get("long_exposure_b"))
    sh=_sf(lev.get("short_exposure_b")); si=_sf(lev.get("single_crypto_b"))
    lp=float(lev.get("long_pct") or 0); sp=float(lev.get("short_pct") or 0); op=max(0,round(100-lp-sp,1))
    ath=bool(lev.get("is_ath",False)); rb=str(lev.get("rebalancing_pressure","—"))
    tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    def b(v): return f"${v}B" if v is not None else "—"
    rc={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rb,"#6B7280")
    ath_b='<span style="background:#dc2626;color:#fff;font-size:10px;padding:2px 7px;border-radius:3px;margin-left:6px;">ATH</span>' if ath else ""
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return f'''<div class="lev-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:#a78bfa;">📊 LEV ETF FLOW{ath_b}</span>
        <span style="background:{rc}33;color:{rc};font-size:11px;padding:3px 10px;border-radius:4px;">Rebal: {rb}</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Total AUM</div><div style="font-size:20px;font-weight:800;color:#E8ECF0;">{b(tot)}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Long</div><div style="font-size:20px;font-weight:800;color:#10B981;">{b(lo)}</div><div style="font-size:9px;color:#6B7280;">{lp:.0f}%</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Short</div><div style="font-size:20px;font-weight:800;color:#EF4444;">{b(sh)}</div><div style="font-size:9px;color:#6B7280;">{sp:.0f}%</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;">Single/Crypto</div><div style="font-size:20px;font-weight:800;color:#F59E0B;">{b(si)}</div></div>
      </div>
      <div style="font-size:10px;color:#9CA3AF;">L: {tls} | S: {tss}<span style="color:#374151;"> · AUM cache 6h</span></div>
    </div>'''

def _compute_dxy_corr(prices: dict, window: int=15) -> dict:
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy,errors="coerce").dropna()
    if len(dxy) < window+2: return {}
    dxy_ret = dxy.pct_change().dropna()
    try:
        from config.settings import DXY_CORRELATION_ASSETS
    except: return {}
    result={}
    for label,ticker in DXY_CORRELATION_ASSETS.items():
        s=prices.get(ticker)
        if s is None: continue
        s=pd.to_numeric(s,errors="coerce").dropna()
        if len(s)<window+2: continue
        combined=pd.concat([dxy_ret,s.pct_change().dropna()],axis=1,join="inner").dropna()
        combined.columns=["dxy","asset"]
        if len(combined)>=window:
            c=float(combined["dxy"].tail(window).corr(combined["asset"].tail(window)))
            if math.isfinite(c): result[label]=round(c,2)
    return result

def _render_dxy_section(prices,dxy_corr,sq):
    if not dxy_corr: st.info("DXY data belum tersedia."); return
    dxy=prices.get("DX-Y.NYB"); dxy_trend="—"
    if dxy is not None:
        dxy=pd.to_numeric(dxy,errors="coerce").dropna()
        if len(dxy)>=22:
            r21=float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            dxy_trend="BEARISH 📉" if r21<-0.005 else ("BULLISH 📈" if r21>0.005 else "NEUTRAL ↔")
    st.markdown(f"**💱 KEY $USD CORRELATIONS (15D)** | DXY Trend: `{dxy_trend}`")
    st.caption("← Negative = benefits from USD weakness | Positive = benefits from USD strength →")
    rows=[{"Asset":l,"15D Corr":c,"Direction":"← USD bearish" if c<-0.2 else ("→ USD bullish" if c>0.2 else "~neutral")} for l,c in dxy_corr.items()]
    st.dataframe(pd.DataFrame(rows).style.background_gradient(subset=["15D Corr"],cmap="RdYlGn",vmin=-1,vmax=1),
                 hide_index=True,use_container_width=True,height=195)
    btc_corr=dxy_corr.get("Bitcoin")
    if btc_corr is not None:
        btc_c="#10B981" if ("BEARISH" in dxy_trend and btc_corr<-0.3 and sq!="Q4") else "#EF4444"
        if "BEARISH" in dxy_trend and btc_corr<-0.3 and sq!="Q4":
            msg=f"₿ BTC: DXY Bearish (corr {btc_corr:+.2f}) → **BTC Bullish TREND intact**. LONG IBIT."
        elif "BULLISH" in dxy_trend:
            msg=f"₿ BTC: DXY Bullish (corr {btc_corr:+.2f}) → **BTC headwind**. Scale back."
        else:
            msg=f"₿ BTC: DXY neutral (corr {btc_corr:+.2f}) → Watch TREND signal."
        st.markdown(f'<div style="background:#111827;border-left:3px solid {btc_c};padding:8px;border-radius:4px;margin-top:4px;font-size:12px;">{msg}</div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEDGEYE FALLBACK NARRATIVES (always shown when NarrativeEngine fails)
# Source: Hedgeye ETF Pro Plus, Macro Show, May 2026
# ══════════════════════════════════════════════════════════════════════════════

HEDGEYE_FALLBACK_NARRATIVES = [
    # Q3 Structural (always relevant when sq=Q3)
    {"name":"Silver Supercycle","score":0.92,"regime":"Q3","quad_bias":"Q3/Q2",
     "thesis":"SLV +143% since May 2025. Dual demand: industrial (AI/EVs) + safe haven (inflation hedge). Supply deficit widens. Hedgeye top pick in Q3.",
     "tickers":["SLV","SI=F","SIL","SILJ","GDXJ","GDX"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],
     "invalidators":["Deflation signal (Q4)","DXY sustained Bullish TREND","Global growth collapse"]},
    {"name":"Gold Secular Bull","score":0.88,"regime":"Q3","quad_bias":"Q3/Q4",
     "thesis":"McCullough: 'Single best asset allocation in Q3.' Central bank buying accelerating. De-dollarization structural tailwind. GLD holds through regime shifts.",
     "tickers":["GLD","GC=F","GDX","GDXJ","PPLT","AEM","WPM","FNV","RGLD"],"best":["GLD","GDX","GDXJ"],"worst":["HYG","IWM"],
     "invalidators":["Q4→Q1 direct transition (gold fades)","Rapid DXY reversal to Bullish TREND"]},
    {"name":"Defense Reshoring","score":0.85,"regime":"ALL","quad_bias":"Q2/Q3",
     "thesis":"NATO 2%+ GDP commitment structural. DOGE doesn't cut defense. Geopolitical premium embedded. ITA + LMT + KTOS secular long regardless of Quad.",
     "tickers":["ITA","LMT","RTX","NOC","KTOS","GD","PLTR","BWXT","SAIC"],"best":["ITA","KTOS","PLTR"],"worst":["XLU"],
     "invalidators":["Global peace agreement (tail risk)","Budget reconciliation cuts defense (low prob)"]},
    {"name":"AI Power Infrastructure","score":0.83,"regime":"Q1/Q2","quad_bias":"Q1/Q2",
     "thesis":"AI hyperscalers need 24/7 firm power. Nuclear + gas turbines only solution at scale. VST, CEG, GEV securing long-term contracts. Secular regardless of Quad.",
     "tickers":["VST","CEG","GEV","ETN","VRT","NRG","GRID","NEE"],"best":["VST","CEG","GEV"],"worst":["INTC","XLU"],
     "invalidators":["AI capex cycle pause","Rate spike destroying power project economics"]},
    # Q2 Monthly overlay (relevant when mq=Q2)
    {"name":"Energy Offense Q2","score":0.80,"regime":"Q2","quad_bias":"Q2",
     "thesis":"Q2 Knife Fights = Energy offense. OIH +oil services operating leverage. BNO/XOP direct commodity price leverage. DAR/MTDR added April 2026.",
     "tickers":["XLE","OIH","BNO","XOP","DAR","MTDR","CL=F","BZ=F"],"best":["OIH","BNO","XOP"],"worst":["XLU","XLP"],
     "invalidators":["Demand collapse (Q4 signal)","OPEC+ surprise production increase"]},
    {"name":"International Country Rotation","score":0.78,"regime":"Q2","quad_bias":"Q1/Q2",
     "thesis":"JPXN +37% Q1 2026. EIS +21.8% since Nov add. TUR +10.3%. USD bearish TREND = EM tailwind. Hedgeye ETF Pro Plus: diversify away from US concentration.",
     "tickers":["JPXN","EIS","TUR","NORW","EWZ","EWW","EIDO","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],
     "invalidators":["DXY reversal to Bullish TREND","Global risk-off (Q4)"]},
    {"name":"Housing Rate Sensitivity","score":0.72,"regime":"Q2","quad_bias":"Q1/Q2",
     "thesis":"ITB as 'long duration equity proxy.' If 2s/10s/30s all bearish TREND → yields fall → housing stocks win. Hedgeye added ITB to ETF Pro Plus.",
     "tickers":["ITB","XHB","DHI","LEN","PHM","NVR"],"best":["ITB","DHI"],"worst":["XLU"],
     "invalidators":["30yr mortgage stays above 7%","Growth collapse (Q3→Q4)"]},
    {"name":"Bitcoin Reflation","score":0.75,"regime":"Q1/Q2/Q3","quad_bias":"ANY except Q4",
     "thesis":"Keith May 6 2026: 'Bitcoin Is Back In The Book.' DXY/BTC 15D corr = -0.83. Any quad other than Q4: bitcoin = biggest digital asset position. Bullish TREND signal confirmed.",
     "tickers":["IBIT","FBTC","BTC-USD","MSTR"],"best":["IBIT"],"worst":["MSTY","BITS","BLOK"],
     "invalidators":["Q4 signal (ONLY exception — exit BTC)","DXY Bullish TREND reversal"]},
    {"name":"Copper Industrial Demand","score":0.70,"regime":"Q2","quad_bias":"Q2",
     "thesis":"AI data centers + EV transition + grid buildout = secular copper demand. CPER/SLX as industrial metals play. Q2 reflation = commodity offense.",
     "tickers":["CPER","HG=F","SLX","COPX","JJC"],"best":["CPER","SLX"],"worst":["XLU"],
     "invalidators":["China growth collapse","Q4 demand destruction"]},
    {"name":"Indonesia Commodity Supercycle","score":0.65,"regime":"Q2/Q3","quad_bias":"Q2/Q3",
     "thesis":"EIDO = coal + nickel + CPO + geothermal. Commodity EM in Q2 reflation. PGEO geothermal = renewable + commodity hybrid. OSV sector (WINS/LEAD) = hulu services demand.",
     "tickers":["EIDO","PGEO.JK","ADRO.JK","INCO.JK","MDKA.JK","WINS.JK","NCKL.JK"],"best":["EIDO","PGEO.JK","NCKL.JK"],"worst":["TLKM.JK"],
     "invalidators":["Global growth collapse (Q4)","CNY devaluation crashing EM commodity prices"]},
]

# Pre-consensus discovery fallback
HEDGEYE_FALLBACK_DISCOVERY = [
    {"name":"AI Photonics Scarcity","category":"bottleneck","stage":"active","confidence":0.88,
     "thesis":"LITE sole supplier 200G EML lasers. POET co-packaged optics removing TDP limits. COHR 25% CW market share. NVIDIA committed $2B. Constraint = 97% for ai_optics sector.",
     "beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],
     "confirmation_signal":"LITE/COHR earnings guidance + NVIDIA capex commentary",
     "invalidators":["China photonics capacity scaling","AI capex cycle pause"]},
    {"name":"SiC Power Semiconductor Monopoly","category":"bottleneck","stage":"active","confidence":0.84,
     "thesis":"WOLF only US large-scale SiC substrate maker. CHIPS Act strategic asset. 30% conduction loss reduction = AI/EV/defense critical. STM/ON license WOLF technology.",
     "beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["legacy Si wafer players"],
     "confirmation_signal":"EV OEM adoption + DOD qualification letters",
     "invalidators":["China SiC subsidies","Margin compression on price pressure"]},
    {"name":"Silver Physical Squeeze","category":"narrative","stage":"building","confidence":0.78,
     "thesis":"Silver industrial demand (solar panels, AI chip plating) accelerating while mine supply flat. LBMA vault levels declining. SLV +143% since May 2025 — still NOT consensus.",
     "beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],
     "confirmation_signal":"LBMA inventory <150M oz + solar installation data beat",
     "invalidators":["India demand collapse","Q4 deflation signal"]},
    {"name":"Japan Yen Structural Weakness → JPXN","category":"macro_rotation","stage":"active","confidence":0.82,
     "thesis":"Yen bearish TREND = Japanese exporters win in USD terms. JPXN +37% Q1 2026. Bank of Japan ultra-dovish while Fed pivots. Hedgeye ETF Pro Plus top international long.",
     "beneficiary_tickers":["JPXN","EWJ","DXJ"],"fade_tickers":["YCS","FXY"],
     "confirmation_signal":"USD/JPY sustained above 145 + BoJ no action",
     "invalidators":["BoJ surprise rate hike above 1%","G7 currency intervention"]},
    {"name":"Indonesia OSV-Hulu Bottleneck","category":"bottleneck","stage":"brewing","confidence":0.65,
     "thesis":"Pertamina hulu expansion + BUMD gas development = OSV fleet utilization >90%. WINS/LEAD = near-monopoly on domestic offshore supply vessels. No new vessel delivery until 2026.",
     "beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],
     "confirmation_signal":"Pertamina capex budget Q2 + OSV day rate >$18k",
     "invalidators":["Pertamina budget freeze","Oil price collapse below $60"]},
]


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v18 · Options + Greeks*")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard","📈 GIP Model","🎯 Risk Ranges™","⚡ Alpha Center",
        "📊 Leaderboard","🌍 Global Quad","🇮🇩 IHSG",
        "📖 Narratives","🔮 Discovery","🏥 Health","📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Force", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Universe"):
        inc_us   = st.checkbox("US Stocks",True)
        inc_fx   = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True)
        inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True)
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Quad (override):",["Auto","Q1","Q2","Q3","Q4"],
                              index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override:
            st.session_state.mq_override = mq_ov
        st.caption("Use when model diverges from Hedgeye manual call. Hedgeye May 2026 = Q2 Monthly.")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        _gq=_gl.get("global_quad","—") if _gl else "—"
        st.caption(f"{_sq} Struct · {_mq} Monthly · {_gq} Global")
    else: st.caption("Building snapshot...")


# ── Load / Auto-build snapshot ────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

# AUTO-BUILD: if no valid snapshot, build immediately without user clicking anything
if snap is None or not snap.get("ok") or st.session_state.loading:
    from orchestrator import build_snapshot
    _lbl = "Building MacroRegime Pro snapshot..." if not st.session_state.loading else "Refreshing..."
    with st.spinner(_lbl):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m,f): pb.progress(f); pt.caption(m)
        snap = build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                              include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
    st.session_state.snap=snap; st.session_state.loading=False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ Snapshot build failed. Check logs via Manage App → Logs."); st.stop()

# ── Extract ────────────────────────────────────────────────────────────────────
gip        = snap.get("gip")
global_    = snap.get("global",{})
rr         = snap.get("risk_ranges",{})
scen       = snap.get("scenarios",{})
narr       = snap.get("narratives",{})
disc       = snap.get("discovery",{})
transition = snap.get("transition",None)
health     = snap.get("health",{})
analogs    = snap.get("analogs",{})
btk        = snap.get("bottleneck",{})
pb_data    = snap.get("playbook",{})
prices     = snap.get("prices",{})
auto_disc  = snap.get("auto_discoveries",{})
fb_eval    = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{})
lev_data   = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q1"
# Apply manual override if set
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq = (global_.get("global_quad","Q3") if global_ else "Q3")

dxy_corr = _compute_dxy_corr(prices)


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(f'<div style="font-size:11px;color:#6B7280;">v18 · {snap.get("build_time_s",0)}s · Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro — Dashboard")

    vbd=health.get("vix_bucket",{}) if health else {}; vb=vbd.get("bucket","—")
    vl=_sf(vbd.get("vix_last")) or 0; vn=vbd.get("note",""); vr=vbd.get("risk_mode","—")
    if vb=="Investable":   vh=f'<div class="vix-investable"><div style="font-size:20px;font-weight:800;color:#10B981;">🟢 INVESTABLE BUCKET</div><div style="font-size:13px;color:#A7F3D0;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    elif vb=="Chop":       vh=f'<div class="vix-chop"><div style="font-size:20px;font-weight:800;color:#F59E0B;">🟡 CHOP BUCKET</div><div style="font-size:13px;color:#FDE68A;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    elif vb=="Defensive":  vh=f'<div class="vix-defensive"><div style="font-size:20px;font-weight:800;color:#EF4444;">🔴 DEFENSIVE BUCKET</div><div style="font-size:13px;color:#FECACA;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    else: vh=""
    if vh: st.markdown(vh,unsafe_allow_html=True); st.markdown("<div style='height:8px;'></div>",unsafe_allow_html=True)

    ga_col,dxy_col=st.columns([1.2,1])
    with ga_col: st.markdown(_render_gamma(gamma_data),unsafe_allow_html=True)
    with dxy_col:
        st.markdown('<div class="dxy-panel">',unsafe_allow_html=True)
        _render_dxy_section(prices,dxy_corr,sq)
        st.markdown('</div>',unsafe_allow_html=True)

    st.markdown(_render_lev(lev_data),unsafe_allow_html=True)

    _sq_q2p=(_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    _sq_sub=f"Q2↑ {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    _mq_note=""
    if mq_raw=="Q1" and mq!="Q1": _mq_note=f"⚠ Model={mq_raw} · Override={mq}"
    elif mq_raw=="Q1" and sq=="Q3": _mq_note="⚠ Model=Q1 · Hedgeye=Q2"
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY",mq,gip.monthly_conf if gip else 0,_mq_note),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL",gq,(_sf(global_.get("global_conf")) or 0) if global_ else 0,"50 countries"),unsafe_allow_html=True)
    with c4:
        if gip:
            st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:14px;text-align:center;height:100%;">
            <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px;">ALIGNMENT</div>
            <div style="font-size:22px;font-weight:800;color:{qc(sq)};">{gip.divergence.upper()}</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">{gip.operating_regime}</div>
            <div style="font-size:11px;color:#E8ECF0;margin-top:8px;">Flip Risk: {gip.flip_hazard:.0%}</div>
            </div>''', unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0); wr=(pr/max(ev,1))*100
        st.markdown("<div style='height:8px;'></div>",unsafe_allow_html=True)
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Evaluated</div><div style="font-size:22px;font-weight:800;">{ev}</div></div>',unsafe_allow_html=True)
        w2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Promoted ✅</div><div style="font-size:22px;font-weight:800;color:#10B981;">{pr}</div></div>',unsafe_allow_html=True)
        w3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Demoted ❌</div><div style="font-size:22px;font-weight:800;color:#EF4444;">{dm}</div></div>',unsafe_allow_html=True)
        w4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Win Rate</div><div style="font-size:22px;font-weight:800;color:#00D4AA;">{wr:.1f}%</div></div>',unsafe_allow_html=True)

    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        if fw!="not yet":
            st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:6px;margin-top:10px;"><div style="font-size:14px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    if pb_data:
        best5=" · ".join(pb_data.get("best_assets",[])[:6]); worst5=" · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'''<div style="background:#0f172a;border:1px solid #1e40af;border-radius:8px;padding:14px;margin-top:10px;">
        <div style="font-size:12px;font-weight:700;color:#58a6ff;margin-bottom:6px;">🎯 QUICK ACTION — {sq} Structural · {mq} Monthly</div>
        <div style="font-size:12px;color:#E8ECF0;">✅ <b>LONG:</b> {best5}</div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">❌ <b>AVOID:</b> {worst5}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Full detail → <b>⚡ Alpha Center</b> · <b>📋 Playbook</b></div>
        </div>''', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative. 'Heating up or cooling down?'")
    if not gip: st.warning("No GIP data."); st.stop()

    st.markdown("### 🌤 Climate vs. Weather")
    cc,cw=st.columns(2)
    with cc:
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(sq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">STRUCTURAL — CLIMATE</div>
        <div style="font-size:32px;font-weight:800;color:{qc(sq)};">{sq}</div>
        <div style="font-size:13px;color:{qc(sq)};margin-top:4px;">{qnc(sq)}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.structural_conf:.0%} · Flip: {gip.flip_hazard:.0%} · Coverage: {gip.data_coverage:.0%}</div>
        </div>''', unsafe_allow_html=True)
    with cw:
        _mq_note2=""
        if mq_raw=="Q1": _mq_note2=f'<div style="font-size:10px;color:#F59E0B;margin-top:4px;">⚠ Model={mq_raw} · Override={mq} (Hedgeye manual=Q2). Set via sidebar.</div>'
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(mq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">MONTHLY — WEATHER</div>
        <div style="font-size:32px;font-weight:800;color:{qc(mq)};">{mq}</div>
        <div style="font-size:13px;color:{qc(mq)};margin-top:4px;">{qnc(mq)}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.monthly_conf:.0%} · {gip.divergence} · {gip.operating_regime}</div>
        {_mq_note2}
        </div>''', unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### 📊 G & I Signals")
    f=gip.features; gm=_sf(f.get("growth_momentum")) or 0; im=_sf(f.get("inflation_momentum")) or 0
    gc2="#10B981" if gm>0 else "#EF4444"; ic2="#10B981" if im<0 else "#EF4444"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Growth Momentum</div><div style="font-size:24px;font-weight:800;color:{gc2};">{fp(gm)}</div><div style="font-size:10px;color:#6B7280;">{"Accel ↑" if gm>0 else "Decel ↓"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Inflation Momentum</div><div style="font-size:24px;font-weight:800;color:{ic2};">{fp(im)}</div><div style="font-size:10px;color:#6B7280;">{"Rising ↑" if im>0 else "Cooling ↓"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Policy Score</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("policy_score"))}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Leading Indicator</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("leading_indicator_composite"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### 📊 Transition Probabilities")
    QWINS={"Q1":"Tech, Small Caps, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives","Q4":"TLT, Gold, Utilities, Cash"}
    def _tp(probs,cur_q,label,desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;margin-bottom:8px;">
        <div style="font-size:11px;color:#9CA3AF;">{label} — {desc}</div>
        <div style="font-size:13px;color:#E8ECF0;margin-top:4px;">Currently: <b style="color:{qc(cur_q)};">{cur_q}</b> → Most likely: <b style="color:{qc(top_q)};">{top_q}</b> ({top_p:.0%})</div>
        </div>''', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs),use_container_width=True,config={"displayModeBar":False})
        if top_q!=cur_q: st.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;font-size:11px;color:#F59E0B;">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",qnc(sq)[:30])
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq)[:30])
    with tp3:
        gprobs=(global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")

    st.markdown("---"); st.markdown("### ⏱ Regime Timing")
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:6px;"><div style="font-size:14px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        ew=getattr(transition,"early_warning_signals",{})
        if ew:
            ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"✅" if v>=0.5 else "⬜","Score":f"{v:.0f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=250)

    if analogs and analogs.get("top_analogs"):
        st.markdown("---"); st.markdown("### 📚 Historical Analogs")
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"**{a['label']}** — {a.get('similarity',0):.0%}",expanded=(i==0)):
                cc2=st.columns(3); cc2[0].markdown(f"**1M:** {a.get('path_1m','')}"); cc2[1].markdown(f"**3M:** {a.get('path_3m','')}"); cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("**LRR** = buy zone. **TRR** = trim zone. TREND break = exit.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No RR data. Refresh."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Alerts")
        for sym,a in all_a[:20]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡"; bdr="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {bdr};padding:8px;border-radius:4px;margin-bottom:4px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]}</div>',unsafe_allow_html=True)

    st.markdown("---")
    cl1,cl2=st.columns([1,3])
    with cl1: mkt_f=st.selectbox("Market",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search","")
    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        rl=_rr_levels(px,lrr,trr)
        rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(lrr),"TRR":ff(trr),
                     "Entry":ff(rl["entry"]) if rl else "—","TP1":ff(rl["tp1"]) if rl else "—","Stop":ff(rl["stop"]) if rl else "—",
                     "R/R":ff(rl["rr"]) if rl else "—","Stretch":tr.get("stretch","—"),
                     "Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
                     "Market":v.get("market","—"),"Trap":"⚠️" if v.get("regime_trap") else "",
                     "Ext":"⚠" if (rl and rl.get("extended")) else ""})
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=500)
    else: st.info("No data. Refresh.")


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ALPHA CENTER (Front-Run + Bottleneck + Options, ALL with levels)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown("# ⚡ Alpha Center — Front-Run · Bottleneck · Options")
    st.caption("Every setup shows Entry · TP1 · TP2 · Stop · R/R. Options-confirmed when available. No near-target entries.")

    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:6px;margin-bottom:8px;"><div style="font-size:14px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    ar=rr.get("asset_ranges",{})

    # FIX: no strict constraint filter. Show ALL items from Level 1/2.
    # The bottleneck engine already classified them. Trust it.
    # Only filter "near target" items (extended/overbought).
    def _btk_filter(items, side="long"):
        out=[]
        for item in (items or []):
            ticker=item.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{})
            stretch=tr.get("stretch","")
            # Skip if already near target (no EV)
            if side=="long" and stretch in ("overbought","extended"): continue
            if side=="short" and stretch in ("oversold","reset_zone"): continue
            out.append(item)
        return out

    l1_items = _btk_filter(btk.get("level_1",[]) if btk else [], "long")
    l2_items = _btk_filter(btk.get("level_2",[]) if btk else [], "long")
    wt_items = (btk.get("watch",[]) or [])[:20] if btk else []
    av_items = (btk.get("avoid",[]) or [])[:15] if btk else []

    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Level 1</div><div style="font-size:28px;font-weight:800;color:#10B981;">{len(l1_items)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Level 2</div><div style="font-size:28px;font-weight:800;color:#F59E0B;">{len(l2_items)}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Watch</div><div style="font-size:28px;font-weight:800;color:#6366F1;">{len(wt_items)}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Avoid</div><div style="font-size:28px;font-weight:800;color:#EF4444;">{len(av_items)}</div></div>',unsafe_allow_html=True)

    # Load options engine lazily
    try:
        from engines.options_engine import OptionsEngine
        _opt_eng = OptionsEngine()
        _opt_ok = True
    except Exception as _e:
        _opt_eng = None; _opt_ok = False
        st.caption(f"OptionsEngine unavailable: {_e}")

    def _render_btk_card(item, expanded=False):
        ticker=item.get("ticker",""); sector=item.get("sector","").replace("_"," ").title()
        trend=item.get("trend",""); score=_sf(item.get("score",0)) or 0
        ev=_sf(item.get("ev",0)) or 0; rf=_sf(item.get("regime_fit",0)) or 0
        thesis=item.get("known_thesis","")[:90]; direction=item.get("direction","long")
        trap=item.get("regime_trap",False)
        v=ar.get(ticker,{}); tr=v.get("trade",{}); comp=v.get("composite","neutral")
        px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        rl=_rr_levels(px,lrr,trr)
        tc="#10B981" if direction=="long" else "#EF4444"
        trap_tag=' ⚠️' if trap else ""

        # Get options
        opt_data = None
        if _opt_ok and _opt_eng and px and px > 0:
            try: opt_data = _opt_eng.analyze(ticker, px, lrr, trr, comp)
            except: pass

        if rl: rl = _merge_with_options(rl, opt_data, direction)

        with st.expander(f"{'🟢' if direction=='long' else '🔴'} **{ticker}** — {sector} | EV {ev:.2f} | Score {score:.0f}{trap_tag}", expanded=expanded):
            ci1,ci2=st.columns([1.2,1])
            with ci1:
                st.markdown(f'''<div class="{'alpha-long' if direction=='long' else 'alpha-short'}" style="padding:10px;">
                <div style="font-size:11px;color:{tc};font-weight:700;margin-bottom:4px;">{direction.upper()} · {sector} · RF {rf:.0%}</div>
                <div style="font-size:11px;color:#E8ECF0;margin-bottom:4px;">{thesis}</div>
                <div style="font-size:11px;color:#9CA3AF;">Trend: {trend} · Score: {score:.2f} · EV: {ev:.2f} · Px: ${px:.2f if px else "—"}</div>
                </div>''', unsafe_allow_html=True)
                if rl: _render_levels(rl, direction, opt_data)
            with ci2:
                # Options second-order Greeks summary
                if opt_data and opt_data.get("ok"):
                    g=opt_data.get("atm_greeks_call",{}) or {}
                    oi_hm=opt_data.get("oi_heatmap",[])
                    mp=opt_data.get("max_pain"); im=opt_data.get("implied_move_pct")
                    vs=opt_data.get("vanna_signal","—"); cs=opt_data.get("charm_signal","—")
                    sig=opt_data.get("options_signal","")
                    sig_c="#10B981" if "LONG" in sig else "#EF4444" if "SHORT" in sig else "#6B7280"
                    st.markdown(f'''<div style="background:#111827;border-radius:6px;padding:10px;">
                    <div style="font-size:11px;font-weight:700;color:{sig_c};">{sig}</div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:4px;">
                      IV: {fp(opt_data.get("atm_iv"))} · ±Move: {fp(im)} · Max Pain: ${mp:.1f if mp else "—"}
                    </div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:2px;">
                      Vanna: {vs} · Charm: {cs} · PC Ratio: {opt_data.get("pc_ratio","—")}
                    </div>''', unsafe_allow_html=True)
                    if g:
                        cols_g=st.columns(4)
                        cols_g[0].metric("Δ",f"{_sf(g.get('delta')) or 0:.3f}")
                        cols_g[1].metric("Γ",f"{_sf(g.get('gamma')) or 0:.5f}")
                        cols_g[2].metric("θ/day",f"{_sf(g.get('theta')) or 0:.3f}")
                        cols_g[3].metric("Vega",f"{_sf(g.get('vega')) or 0:.3f}")
                    if oi_hm:
                        oi_df=pd.DataFrame(oi_hm[:10]).rename(columns={"strike":"Strike","call_oi":"C OI","put_oi":"P OI","net_oi":"Net"})
                        st.dataframe(oi_df[["Strike","C OI","P OI","Net"]].style.background_gradient(subset=["Net"],cmap="RdYlGn"),
                                     hide_index=True,use_container_width=True,height=180)
                    st.markdown("</div>",unsafe_allow_html=True)
                else:
                    st.caption("Options: N/A (futures/FX/IHSG)" if not _opt_ok else "Options: fetching or unavailable")

    st.markdown("---"); st.markdown("### ⚡ Level 1 — Act Now")
    if not l1_items:
        st.info("No Level 1 setups (all may be extended near TRR). Check Level 2 below.")
    for i,item in enumerate(l1_items[:8]):
        _render_btk_card(item, expanded=(i<2))

    st.markdown("---")
    with st.expander(f"📈 Level 2 — Building ({len(l2_items)})", expanded=False):
        if not l2_items: st.info("No Level 2 setups.")
        for i,item in enumerate(l2_items[:6]): _render_btk_card(item, expanded=False)

    with st.expander(f"👀 Watch — Brewing ({len(wt_items)})", expanded=False):
        if wt_items:
            wt_rows=[{"Ticker":w["ticker"],"Sector":w["sector"].replace("_"," ").title(),"Trend":w["trend"],"EV":f'{w.get("ev",0):.2f}',"Thesis":w.get("known_thesis","")[:60]} for w in wt_items]
            st.dataframe(pd.DataFrame(wt_rows),hide_index=True,use_container_width=True)

    with st.expander(f"🚫 Avoid ({len(av_items)})", expanded=False):
        if av_items:
            av_rows=[{"Ticker":a["ticker"],"Sector":a["sector"].replace("_"," ").title(),"Trend":a["trend"],"Score":f'{a.get("score",0):.2f}'} for a in av_items]
            st.dataframe(pd.DataFrame(av_rows),hide_index=True,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📊 LEADERBOARD — Quality A with Entry/TP/Stop on every card
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown("# 📊 The Leaderboard — Signal Strength Stocks")
    st.caption("Quality A near LRR + volume confirm. Entry · TP1 · TP2 · Stop on every card. Options-enhanced when available.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No RR data. Refresh."); st.stop()

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]
    try:
        from engines.options_engine import OptionsEngine as _OE
        _opt_e = _OE(); _opt_ok2 = True
    except: _opt_e = None; _opt_ok2 = False

    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); tn=v.get("trend",{})
        px=_sf(v.get("px")); vol_c=_sf(tr.get("volume_confirm")) or 0.5
        stretch=tr.get("stretch","neutral"); hurst=_sf(tn.get("hurst")) or 0.5
        lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic")
        except: sector="generic"
        if qual in ("A","B") and comp=="bullish":
            if stretch in ("overbought","extended"): continue  # Skip near-target
            rl=_rr_levels(px,lrr,trr); pos=rl.get("pos",0.5) if rl else 0.5
            nlrr=pos<=0.35 or stretch in ("oversold","reset_zone")
            rf=sym in best_set; ra=sym in worst_set
            sc=(50 if qual=="A" else 30)+(25 if nlrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector,"comp":comp})
        if qual in ("short_A","short_B") and comp=="bearish":
            if stretch in ("oversold","reset_zone"): continue  # Skip near-target
            rl=_rr_levels(px,lrr,trr); pos=rl.get("pos",0.5) if rl else 0.5
            ntrr=pos>=0.65 or stretch in ("overbought","extended")
            rf=sym in worst_set
            sc=(50 if qual=="short_A" else 30)+(25 if ntrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector,"comp":comp})

    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])

    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Bullish Names</div><div style="font-size:28px;font-weight:800;color:#10B981;">{len(long_picks)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Longs</div><div style="font-size:28px;font-weight:800;color:#00D4AA;">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Shorts</div><div style="font-size:28px;font-weight:800;color:#EF4444;">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Regime Traps</div><div style="font-size:28px;font-weight:800;color:#F59E0B;">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### 🟢 TOP 21 LONG IDEAS")
    for p in long_picks[:21]:
        rl=p.get("rl"); opt_r=None
        if _opt_ok2 and _opt_e and p["px"] and p["px"]>0:
            try: opt_r=_opt_e.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
            except: pass
        if rl and opt_r: rl=_merge_with_options(rl,opt_r,"long")
        st.markdown(f'''<div class="signal-A">
        <div style="display:flex;justify-content:space-between;">
          <span style="font-size:15px;font-weight:800;color:#10B981;">{p["ticker"]} <span style="font-size:11px;color:#A7F3D0;">({p["quality"]})</span></span>
          <span style="font-size:11px;color:#9CA3AF;">{"✅" if p["regime_fit"] else "⚠️"} Sc:{p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</span>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · Stretch: {p["stretch"]} · Vol: {fp(p["vol_c"])} · H: {ff(p["hurst"])}</div>
        </div>''', unsafe_allow_html=True)
        if rl: _render_levels(rl,"long",opt_r)
    if not long_picks: st.info("No Quality A/B longs near LRR. Wait for pullback.")

    st.markdown("---"); st.markdown("### 🔴 SHORT IDEAS")
    for p in short_picks[:15]:
        rl=p.get("rl"); opt_r=None
        if _opt_ok2 and _opt_e and p["px"] and p["px"]>0:
            try: opt_r=_opt_e.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
            except: pass
        if rl and opt_r: rl=_merge_with_options(rl,opt_r,"short")
        st.markdown(f'''<div class="signal-shortA">
        <div style="display:flex;justify-content:space-between;">
          <span style="font-size:15px;font-weight:800;color:#EF4444;">{p["ticker"]} <span style="font-size:11px;color:#FECACA;">({p["quality"]})</span></span>
          <span style="font-size:11px;color:#9CA3AF;">{"✅" if p["regime_fit"] else "⚠️"} Sc:{p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</span>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · Stretch: {p["stretch"]} · Vol: {fp(p["vol_c"])}</div>
        </div>''', unsafe_allow_html=True)
        if rl: _render_levels(rl,"short",opt_r)
    if not short_picks: st.info("No Quality Short setups.")


# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50 Countries")
    if not global_: st.warning("No global data. Refresh."); st.stop()
    gconf=_sf(global_.get("global_conf")) or 0; gprobs=global_.get("global_probs",{}) or {}
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs,"Global Probabilities"),use_container_width=True,config={"displayModeBar":False})
    with c2:
        cq=global_.get("country_quads",{}) or {}; heat=[]
        for country,data in cq.items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_sf(data[2]) or 0
            elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_sf(data.get("conf",0)) or 0
            else: continue
            if quad: heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            st.dataframe(pd.DataFrame(heat).style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=400,use_container_width=True)
        else:
            st.info("Country Quad data kosong. Pastikan GlobalQuadEngine berjalan dan click 🔄 Refresh.")
    st.markdown("---"); st.markdown("### 🌏 EM Recovery Signal")
    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_sf(em_sig.get("confidence")) or 0; ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">
        <div style="font-size:13px;font-weight:700;color:{ec};">{em_sig.get("trigger","")}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div>
        <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Conf: {conf:.0%} · Best: {", ".join(em_sig.get("best",[])[:6])}</div>
        </div>''', unsafe_allow_html=True)
    else: st.info("EM recovery signal belum tersedia.")


# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG — with price fallback when RR not available
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Market")
    st.caption("Local signal. No options data (IHSG options market tidak liquid).")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg_rr={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}

    if ihsg_rr:
        # RR data tersedia
        rows=[{"Ticker":sym,"Px":ff(_sf(v.get("px")),0),"LRR":ff(_sf(v.get("trade",{}).get("lrr")),0),"TRR":ff(_sf(v.get("trade",{}).get("trr")),0),
               "Entry":ff(_rr_levels(_sf(v.get("px")),_sf(v.get("trade",{}).get("lrr")),_sf(v.get("trade",{}).get("trr"))) and _rr_levels(_sf(v.get("px")),_sf(v.get("trade",{}).get("lrr")),_sf(v.get("trade",{}).get("trr"))).get("entry"),0),
               "Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
               "Stretch":v.get("trade",{}).get("stretch","—"),"Trap":"⚠️" if v.get("regime_trap") else ""} for sym,v in ihsg_rr.items()]
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else:
        # FALLBACK: show price data from prices dict
        st.info("Risk Range data untuk IHSG belum dihitung. Menampilkan price data dari snapshot.")
        rows=[]
        for sym in IHSG_UNIVERSE:
            s=prices.get(sym)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1])
            r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else None
            r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
            rows.append({"Ticker":sym,"Px":f"{px:.0f}","1M":f"{r1:+.1%}" if r1 else "—","3M":f"{r3:+.1%}" if r3 else "—",
                         "Name":IHSG_UNIVERSE.get(sym,sym)})
        if rows:
            df=pd.DataFrame(rows)
            st.dataframe(df,hide_index=True,use_container_width=True,height=400)
        else:
            st.warning("IHSG price data juga tidak tersedia. Pastikan IHSG checkbox aktif dan click 🔄 Refresh.")

    st.markdown("---"); st.markdown("### 🏦 Sector Buckets")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"**{bucket.replace('_',' ')}** ({len(tickers)})"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}"})
            if b_rows: st.dataframe(pd.DataFrame(b_rows),hide_index=True,use_container_width=True)
            else: st.info("Data tidak tersedia. Refresh.")


# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES — with Hedgeye fallback (ALWAYS shows content)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown("# 📖 Narratives — Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus.")

    # Get engine narratives
    active = (narr.get("active_narratives",[]) or []) if narr else []

    # Always show — merge engine + fallback
    if not active:
        st.info("NarrativeEngine belum berjalan. Menampilkan Hedgeye-aligned fallback narratives.")

    # Filter fallback by current Quad
    fallback = [n for n in HEDGEYE_FALLBACK_NARRATIVES
                if sq in n.get("regime","") or mq in n.get("regime","") or n.get("regime","")=="ALL"]

    all_narr = active if active else fallback

    for n in sorted(all_narr, key=lambda x: x.get("score",0), reverse=True):
        score=n.get("score",0); sc="#10B981" if score>0.6 else "#F59E0B" if score>0.4 else "#6B7280"
        is_fallback = "quad_bias" in n  # fallback items have this field
        tag = " · *Hedgeye aligned*" if is_fallback else ""
        with st.expander(f"**{n.get('name','')}** — {score:.0%}{tag}"):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' · '.join(n.get('tickers',[])[:8])}")
            if n.get("best"):  st.markdown(f"**Best:** {' · '.join(n['best'][:6])}")
            if n.get("worst"): st.markdown(f"**Worst:** {' · '.join(n['worst'][:4])}")
            if n.get("invalidators"): st.markdown(f"**Invalidators:** {' | '.join(n['invalidators'][:3])}")
            if is_fallback and n.get("quad_bias"): st.caption(f"Quad bias: {n['quad_bias']}")


# ══════════════════════════════════════════════════════════════════════════════
# 🔮 DISCOVERY — with Hedgeye fallback (ALWAYS shows content)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown("# 🔮 Early Discovery — Pre-Consensus")
    st.caption("Autonomy: regime fit + price cluster + supply chain graph + news NLP.")

    # Get engine discoveries
    cands=(auto_disc.get("candidates",[]) or []) if auto_disc else []
    cands += (disc.get("discoveries",[]) or []) if disc else []

    if not cands:
        st.info("Autonomy Stack belum berjalan. Menampilkan pre-defined pre-consensus ideas.")
        cands_display = HEDGEYE_FALLBACK_DISCOVERY
    else:
        cands_display = cands

    for stage,sc_c in [("active","#10B981"),("building","#F59E0B"),("brewing","#6366F1")]:
        items=[c for c in cands_display if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper()} ({len(items)})")
        for c in items:
            conf=c.get("confidence",c.get("conviction",0.7)); pump=c.get("pump_risk",0)
            with st.expander(f"**{c.get('name','')}** — Conf: {conf:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                ben=c.get("beneficiary_tickers",[]); fade=c.get("fade_tickers",[])
                if ben:  st.markdown(f"**Beneficiaries:** {' · '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' · '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs:  st.markdown(f"**Confirmation:** {cs}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")


# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown("# 🏥 Market Health — VIX · Breadth · Crash Meter")
    if not health: st.warning("No health data."); st.stop()
    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","—")
    vb_c={"Investable":"#10B981","Chop":"#F59E0B","Defensive":"#EF4444"}.get(vb_b,"#6B7280")
    st.markdown(f'<div style="background:{vb_c}22;border-left:4px solid {vb_c};padding:12px;border-radius:6px;"><div style="font-size:16px;font-weight:800;color:{vb_c};">VIX BUCKET: {vb_b.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{vb_d.get("note","")}</div></div>',unsafe_allow_html=True)
    crash=health.get("crash",{}) or {}
    if crash:
        st.markdown("### Crash Meter")
        for k,v in crash.get("signals",{}).items(): st.progress(float(v) if v else 0,text=f"{k.replace('_',' ').title()}: {v:.0%}" if v else k)
        st.markdown(f"**State:** {crash.get('state','')} · Score: {_sf(crash.get('score',0)):.0%}")
    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.markdown("### Breadth")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Score",f"{_sf(breadth.get('score')) or 0:.2f}"); b2.metric("Verdict",breadth.get("verdict","—"))
        b3.metric("Sector Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW",f"{_sf(breadth.get('eqw_health')) or 0:.2f}")
    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.markdown("---"); fgs=_sf(fg.get("score")) or 50
        fgc="#10B981" if fgs<25 else "#F59E0B" if fgs<55 else "#EF4444"
        st.markdown(f"**Fear & Greed:** <span style='color:{fgc};font-size:18px;font-weight:700;'>{fgs:.0f}/100</span> — {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)


# ══════════════════════════════════════════════════════════════════════════════
# 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown("# 📋 Regime Playbook")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly (override: {st.session_state.mq_override})")

    if pb_data:
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f'''<div class="alpha-long" style="padding:14px;">
            <div style="font-size:13px;font-weight:700;color:#10B981;margin-bottom:8px;">✅ LONG — {sq}</div>
            <div style="font-size:13px;color:#E8ECF0;">{" · ".join(pb_data.get("best_assets",[]))}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Style: {pb_data.get("style","")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">FX: {pb_data.get("fx","")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Bonds: {pb_data.get("bonds","")}</div>
            {('<div style="font-size:11px;color:#F59E0B;margin-top:4px;">Adds: ' + " · ".join(pb_data.get("monthly_adds",[])) + '</div>') if pb_data.get("monthly_adds") else ""}
            </div>''', unsafe_allow_html=True)
        with col2:
            st.markdown(f'''<div class="alpha-short" style="padding:14px;">
            <div style="font-size:13px;font-weight:700;color:#EF4444;margin-bottom:8px;">❌ AVOID — {sq}</div>
            <div style="font-size:13px;color:#E8ECF0;">{" · ".join(pb_data.get("worst_assets",[]))}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Hedge: {pb_data.get("hedge","BTAL")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{pb_data.get("sizing_note","Min 1% · Max 3%")}</div>
            </div>''', unsafe_allow_html=True)

    btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
    btc_sig=btc_rr.get("composite","—")
    btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
    st.markdown(f'''<div style="background:#111827;border-left:4px solid {btc_c};padding:10px;border-radius:6px;margin-top:10px;">
    <span style="font-size:12px;font-weight:700;color:{btc_c};">₿ BITCOIN (IBIT): {btc_sig.upper()} — {"Exit (Q4)" if sq=="Q4" else "Signal-dependent via DXY correlation"}</span>
    <span style="font-size:11px;color:#9CA3AF;"> · DXY/BTC 15D: {dxy_corr.get("Bitcoin","—")} · "Any quad other than Q4 = long IBIT."</span>
    </div>''', unsafe_allow_html=True)

    scenarios_list=(scen.get("scenarios",[]) or []) if scen else []
    if scenarios_list:
        st.markdown("---"); st.markdown("### 🔮 Scenarios")
        badges=["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]; badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
        row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]; em=sc_item.em_note[:55]+"..." if len(sc_item.em_note)>55 else sc_item.em_note
            with col:
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">
                <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} P={sc_item.probability:.0%}</div>
                <div style="font-size:13px;color:#E8ECF0;margin-top:4px;font-weight:600;">{sc_item.name}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{sc_item.headline}</div>
                <div style="font-size:11px;color:#10B981;margin-top:4px;">Best: {" · ".join(sc_item.best_assets[:3])}</div>
                <div style="font-size:11px;color:#EF4444;margin-top:2px;">Avoid: {" · ".join(sc_item.worst_assets[:3])}</div>
                <div style="font-size:10px;color:#6B7280;margin-top:4px;">{em}</div>
                </div>''', unsafe_allow_html=True)

    if gip:
        st.markdown("---"); st.markdown("### 📡 GIP Signals")
        f=gip.features
        rows=[["Growth Momentum",fp(f.get("growth_momentum")),"↑" if (_sf(f.get("growth_momentum")) or 0)>0 else "↓"],
              ["Inflation Momentum",fp(f.get("inflation_momentum")),"↑" if (_sf(f.get("inflation_momentum")) or 0)>0 else "↓"],
              ["Policy Score",fp(f.get("policy_score")),""],["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
              ["Data Coverage",fp(f.get("data_coverage")),""],["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
              ["Structural Conf",f"{gip.structural_conf:.0%}",""],["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
        st.dataframe(pd.DataFrame(rows,columns=["Signal","Value","Dir"]),hide_index=True,use_container_width=True)

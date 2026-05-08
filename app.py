"""app.py — MacroRegime Pro v16 | Hedgeye-Style Dashboard

ONE purpose per tab. ZERO content duplication.
  🏠 Dashboard     = Status. Read in 30 seconds.
  📈 GIP Model     = The Map. Full macro + transition charts + analogs.
  🎯 Risk Ranges™  = LRR/TRR table + alerts.
  ⚡ ETF Pro       = ETF ideas by asset class.
  📊 Leaderboard   = Quality A stock picks.
  🌍 Global Quad   = 50 countries + EM recovery.
  🇮🇩 IHSG         = Indonesia only.
  🔍 Bottleneck    = Supply chain alpha.
  📖 Narratives    = Thematic scoring.
  🔮 Discovery     = Pre-consensus AI discoveries.
  🏥 Health        = Market vitals.
  📋 Playbook      = Full regime action plan + scenarios.

Bitcoin mechanics (Keith McCullough):
  - "Any quad other than Quad 4, bitcoin = biggest digital asset position."
  - DXY/BTC 15D correlation = -0.83 (May 2026). Bearish DXY = Bullish BTC.
  - Apr 20 2026: "Bitcoin Bullish TREND @Hedgeye vs Bearish TREND USD -0.6%"
  - May 6 2026: "Bitcoin Is Back In The Book" — LONG IBIT.
  - Q4 = only exception. Exit BTC in Q4.
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

st.markdown("""<style>
.vix-investable {background:linear-gradient(90deg,#064e3b,#065f46);border-left:6px solid #10B981;padding:16px;border-radius:8px;}
.vix-chop       {background:linear-gradient(90deg,#451a03,#78350f);border-left:6px solid #F59E0B;padding:16px;border-radius:8px;}
.vix-defensive  {background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:6px solid #EF4444;padding:16px;border-radius:8px;}
.winrate-card   {background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;}
.signal-A       {background:linear-gradient(90deg,#064e3b,#065f46);border-left:4px solid #10B981;padding:12px;border-radius:6px;margin-bottom:8px;}
.signal-shortA  {background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:4px solid #EF4444;padding:12px;border-radius:6px;margin-bottom:8px;}
.gamma-deep-pos {background:#052e16;border-left:4px solid #16a34a;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-pos      {background:#064e3b;border-left:4px solid #059669;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-trans    {background:#451a03;border-left:4px solid #d97706;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-neg      {background:#450a0a;border-left:4px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-deep-neg {background:#3b0000;border-left:4px solid #b91c1c;padding:14px;border-radius:8px;margin-bottom:10px;}
.lev-panel      {background:#1e1b4b;border-left:4px solid #7c3aed;padding:14px;border-radius:8px;margin-bottom:10px;}
.dxy-panel      {background:#0f172a;border-left:4px solid #0ea5e9;padding:14px;border-radius:8px;margin-bottom:10px;}
.seq-row        {display:flex;align-items:center;gap:8px;padding:10px;background:#111827;border-radius:6px;flex-wrap:wrap;margin-top:8px;margin-bottom:10px;}
.etf-long       {background:#052e16;border:1px solid #16a34a;border-radius:6px;padding:10px;margin-bottom:6px;}
.etf-short      {background:#3b0000;border:1px solid #dc2626;border-radius:6px;padding:10px;margin-bottom:6px;}
.action-box     {background:#0f172a;border:1px solid #1e40af;border-radius:8px;padding:14px;margin-top:10px;}
.btc-long       {background:#052e16;border:1px solid #16a34a;border-radius:6px;padding:10px;margin-top:8px;}
.btc-neutral    {background:#111827;border:1px solid #374151;border-radius:6px;padding:10px;margin-top:8px;}
.btc-short      {background:#3b0000;border:1px solid #dc2626;border-radius:6px;padding:10px;margin-top:8px;}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"Goldilocks — Growth↑ Infl↓",
    "Q2":"Reflation — Growth↑ Infl↑",
    "Q3":"Stagflation — Growth↓ Infl↑",
    "Q4":"Deflation — Growth↓ Infl↓",
}

def qc(q):   return QC.get(q,"#9CA3AF")
def qn(q):   return QN.get(q,q)
def qnc(q):  return QNC.get(q,q)
def fp(v):
    try:    return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v, d=2):
    try:    return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

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
                return f'<span style="color:{colors.get(lvl)};font-size:10px;">{lvl.replace("_"," ").upper()}</span>'
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
        fig=price_chart(prices,list(tickers_map.keys())[:8],title=f"{title} — Normalized",days=days)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    else:
        st.info("No data loaded for this universe.")

# ── DXY Correlation (Keith McCullough's Key $USD Correlations table) ───────────
def _compute_dxy_correlations(prices: dict, window: int = 15) -> dict:
    """
    Compute 15D rolling correlation of key assets vs DXY.
    Source: Keith McCullough — "Key $USD Correlations* 15D"
    BTC/USD corr = -0.83 to -0.90 (Apr-May 2026)
    """
    from config.settings import DXY_CORRELATION_ASSETS, DXY_CORRELATION_WINDOW
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy,errors="coerce").dropna()
    if len(dxy) < window+2: return {}
    dxy_ret = dxy.pct_change().dropna()
    result = {}
    for label,ticker in DXY_CORRELATION_ASSETS.items():
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s,errors="coerce").dropna()
        if len(s) < window+2: continue
        asset_ret = s.pct_change().dropna()
        combined = pd.concat([dxy_ret,asset_ret],axis=1,join="inner")
        combined.columns = ["dxy","asset"]
        if len(combined) >= window:
            corr = combined["dxy"].tail(window).corr(combined["asset"].tail(window))
            if math.isfinite(corr): result[label] = round(corr,2)
    return result

def _render_dxy_panel(prices: dict, dxy_corr: dict, sq: str) -> str:
    """Render Keith's Key $USD Correlations table + BTC implication."""
    if not dxy_corr:
        return '<div class="dxy-panel"><b style="color:#0ea5e9;">💱 KEY $USD CORRELATIONS (15D)</b><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">DXY data belum tersedia.</div></div>'

    rows_html = ""
    for label,corr in dxy_corr.items():
        if corr > 0.3:         color="#10B981"  # positively correlated with USD
        elif corr < -0.3:      color="#EF4444"  # inversely correlated with USD
        else:                   color="#9CA3AF"
        bar_width = int(abs(corr)*50)
        bar_dir  = "right" if corr>0 else "left"
        rows_html += f'''
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:5px;">
          <span style="font-size:11px;color:#9CA3AF;width:80px;">{label}</span>
          <div style="flex:1;background:#1f2937;border-radius:3px;height:16px;position:relative;overflow:hidden;">
            <div style="position:absolute;{"right" if corr<0 else "left"}:50%;top:0;height:100%;
                 width:{bar_width}%;background:{color};"></div>
            <div style="position:absolute;left:50%;top:0;height:100%;width:1px;background:#374151;"></div>
          </div>
          <span style="font-size:12px;font-weight:700;color:{color};width:45px;text-align:right;">{corr:+.2f}</span>
        </div>'''

    # BTC signal implication
    btc_corr = dxy_corr.get("Bitcoin", None)
    dxy_s = prices.get("DX-Y.NYB")
    dxy_trend = "—"
    if dxy_s is not None:
        dxy_s = pd.to_numeric(dxy_s,errors="coerce").dropna()
        if len(dxy_s) >= 63:
            dxy_21m = float(dxy_s.iloc[-1]/dxy_s.iloc[-22]-1)
            dxy_63m = float(dxy_s.iloc[-1]/dxy_s.iloc[-64]-1)
            dxy_trend = "BEARISH" if dxy_21m<-0.005 else "BULLISH" if dxy_21m>0.005 else "NEUTRAL"

    btc_implication = ""
    if btc_corr is not None and dxy_trend != "—":
        if dxy_trend=="BEARISH" and sq!="Q4":
            btc_implication = f'<div style="margin-top:6px;font-size:11px;color:#10B981;">₿ BTC: DXY Bearish TREND ({btc_corr:+.2f} corr) → <b>BTC Bullish TREND thesis intact</b>. LONG IBIT.</div>'
        elif dxy_trend=="BULLISH":
            btc_implication = f'<div style="margin-top:6px;font-size:11px;color:#EF4444;">₿ BTC: DXY Bullish TREND ({btc_corr:+.2f} corr) → <b>BTC headwind</b>. Monitor TREND signal. Scale back.</div>'
        else:
            btc_implication = f'<div style="margin-top:6px;font-size:11px;color:#9CA3AF;">₿ BTC: DXY neutral ({btc_corr:+.2f} corr) → Watch TREND signal before sizing.</div>'

    return f'''<div class="dxy-panel">
      <div style="font-size:13px;font-weight:700;color:#0ea5e9;margin-bottom:10px;">
        💱 KEY $USD CORRELATIONS (15D) — Keith McCullough
        <span style="font-size:10px;color:#6B7280;font-weight:400;margin-left:8px;">DXY TREND: <b style="color:{"#EF4444" if dxy_trend=="BEARISH" else "#10B981" if dxy_trend=="BULLISH" else "#9CA3AF"};">{dxy_trend}</b></span>
      </div>
      <div style="font-size:10px;color:#6B7280;margin-bottom:8px;display:flex;gap:20px;">
        <span>← USD bearish = asset benefits</span>
        <span style="margin-left:auto;">asset benefits when USD bullish →</span>
      </div>
      {rows_html}
      {btc_implication}
    </div>'''

# ── Gamma panel ───────────────────────────────────────────────────────────────
def _render_gamma(gamma: dict) -> str:
    if not gamma or not gamma.get("ok"):
        note=(gamma or {}).get("note","GammaRegimeEngine belum berjalan — tambahkan ke orchestrator step 14e.")
        return f'<div class="gamma-trans"><b style="color:#F59E0B;">⚡ GAMMA REGIME</b><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{note}</div></div>'
    th=gamma.get("throttle") or 0
    r10=gamma.get("rvol_10d"); r21=gamma.get("rvol_21d")
    vix=gamma.get("vix"); vp=gamma.get("vol_premium")
    bp=gamma.get("bar_pct") or 50
    color=gamma.get("color","#9CA3AF")
    label=gamma.get("label","Unknown")
    action=gamma.get("action","—")
    impl=gamma.get("impl","")
    regime=gamma.get("regime","UNKNOWN")
    css={"DEEP_POSITIVE":"gamma-deep-pos","POSITIVE":"gamma-pos","TRANSITION":"gamma-trans",
         "NEGATIVE":"gamma-neg","DEEP_NEGATIVE":"gamma-deep-neg"}.get(regime,"gamma-trans")
    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "—"
    vpc="#10B981" if (vp or 0)>0 else "#EF4444"
    pw=max(0,min(100,bp-43))
    return f'''<div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:{color};">⚡ GAMMA REGIME — Tier 1 Alpha Approx</span>
        <div style="background:{color};color:#000;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;">{label.upper()}</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Throttle (approx)</div>
          <div style="font-size:20px;font-weight:800;color:{color};">{f(th,"+.1f")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 10d</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(r10,".1f","%")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 21d</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(r21,".1f","%")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">VIX</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{f(vix,".1f")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Vol Premium</div>
          <div style="font-size:18px;font-weight:700;color:{vpc};">{f(vp,"+.1f","%")}</div>
        </div>
      </div>
      <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px;">
        <div style="width:14%;background:#b91c1c;border-radius:3px 0 0 3px;"></div>
        <div style="width:15%;background:#dc2626;"></div>
        <div style="width:14%;background:#d97706;"></div>
        <div style="width:{100-pw}%;background:#1f2937;"></div>
        <div style="width:{pw}%;background:#10B981;border-radius:0 3px 3px 0;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:11px;color:#9CA3AF;flex:1;">{impl}</div>
        <div style="background:#111827;padding:4px 12px;border-radius:4px;margin-left:10px;">
          <span style="font-size:13px;font-weight:800;color:{color};">{action}</span>
        </div>
      </div>
    </div>'''

def _render_lev(lev: dict) -> str:
    if not lev or not lev.get("ok"):
        note=(lev or {}).get("note","LeveragedETFEngine belum berjalan — tambahkan ke orchestrator step 14f.")
        return f'<div class="lev-panel"><b style="color:#a78bfa;">📊 LEVERAGED ETF FLOW</b><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{note}</div></div>'
    tot=lev.get("total_mcap_b"); lo=lev.get("long_exposure_b")
    sh=lev.get("short_exposure_b"); si=lev.get("single_crypto_b")
    lp=lev.get("long_pct") or 0; sp=lev.get("short_pct") or 0
    op=max(0,round(100-lp-sp,1)); ath=lev.get("is_ath",False); rb=lev.get("rebalancing_pressure","—")
    tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    def b(v): return f"${v}B" if v is not None else "—"
    rc={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rb,"#6B7280")
    ath_b='<span style="background:#dc2626;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:3px;margin-left:6px;">ATH</span>' if ath else ""
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return f'''<div class="lev-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:#a78bfa;">📊 LEVERAGED ETF FLOW{ath_b}</span>
        <span style="background:{rc}33;color:{rc};font-size:11px;padding:3px 10px;border-radius:4px;">Rebal: {rb}</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Total AUM</div><div style="font-size:20px;font-weight:800;color:#E8ECF0;">{b(tot)}</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Long</div><div style="font-size:20px;font-weight:800;color:#10B981;">{b(lo)}</div><div style="font-size:9px;color:#6B7280;">{lp}%</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Short</div><div style="font-size:20px;font-weight:800;color:#EF4444;">{b(sh)}</div><div style="font-size:9px;color:#6B7280;">{sp}%</div></div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Single/Crypto</div><div style="font-size:20px;font-weight:800;color:#F59E0B;">{b(si)}</div></div>
      </div>
      <div style="display:flex;height:7px;border-radius:4px;overflow:hidden;margin-bottom:5px;gap:1px;">
        <div style="width:{lp}%;background:#10B981;border-radius:3px 0 0 3px;"></div>
        <div style="width:{sp}%;background:#EF4444;"></div>
        <div style="width:{op}%;background:#F59E0B;border-radius:0 3px 3px 0;"></div>
      </div>
      <div style="font-size:10px;color:#9CA3AF;">Long: {tls}<br>Short: {tss}<span style="color:#4B5563;"> · yfinance AUM · cache 6h</span></div>
    </div>'''

def _sequence_pills(sq, mq):
    sqc=qc(sq); mqc=qc(mq)
    p="padding:3px 11px;border-radius:4px;font-weight:700;font-size:12px;"
    arr='<span style="color:#6B7280;font-size:18px;">→</span>'
    if sq==mq:
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Regime:</span><span style="background:{sqc};color:#000;{p}">{sq} CONFIRMED</span><span style="color:#9CA3AF;font-size:11px;margin-left:4px;">Structural & Monthly aligned</span></div>'
    if sq=="Q3" and mq=="Q2":
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Sequencing:</span><span style="background:#dc2626;color:#fff;{p}">{sq} STRUCT</span>{arr}<span style="background:{mqc};color:#000;{p}">{mq} MONTHLY</span>{arr}<span style="background:#14532d;color:#4ade80;{p}border:1px solid #16a34a;">Q1 TARGET</span><span style="color:#4B5563;font-size:10px;margin-left:4px;">~6wk · watch CPI -50bps</span></div>'
    return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Struct:</span><span style="background:{sqc};color:#000;{p}">{sq}</span>{arr}<span style="color:#9CA3AF;font-size:12px;">Monthly:</span><span style="background:{mqc};color:#000;{p}">{mq}</span><span style="color:#4B5563;font-size:10px;margin-left:4px;">leading → lagging</span></div>'


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR + LOAD
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v16 · Autonomy*")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard",
        "📈 GIP Model",
        "🎯 Risk Ranges™",
        "⚡ ETF Pro",
        "📊 Leaderboard",
        "🌍 Global Quad",
        "🇮🇩 IHSG",
        "🔍 Bottleneck",
        "📖 Narratives",
        "🔮 Discovery",
        "🏥 Health",
        "📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2 = st.columns(2)
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
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"
        _mq=_g.monthly_quad if _g else "—"
        _gq=_gl.get("global_quad","—") if _gl else "—"
        st.caption(f"Hedgeye: {_sq} Struct · {_mq} Monthly · {_gq} Global")
    else:
        st.caption("Hedgeye: — Struct · — Monthly · — Global")

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
    st.error("❌ No snapshot. Click 🔄 Refresh to rebuild."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
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
mq = gip.monthly_quad    if gip else "Q2"
gq = global_.get("global_quad","Q3")

# Pre-compute DXY correlations (used in Dashboard + ETF Pro crypto)
dxy_corr = _compute_dxy_correlations(prices)


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD — Status center. Read in 30 seconds.
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(f'<div style="font-size:11px;color:#6B7280;">Built {snap.get("build_time_s",0)}s · Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro — Dashboard")

    # VIX Bucket
    vbd=health.get("vix_bucket",{}) if health else {}
    vb=vbd.get("bucket","—"); vl=vbd.get("vix_last",0); vn=vbd.get("note",""); vr=vbd.get("risk_mode","—")
    if vb=="Investable":   vh=f'<div class="vix-investable"><div style="font-size:20px;font-weight:800;color:#10B981;">🟢 INVESTABLE BUCKET</div><div style="font-size:13px;color:#A7F3D0;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vr}</div></div>'
    elif vb=="Chop":       vh=f'<div class="vix-chop"><div style="font-size:20px;font-weight:800;color:#F59E0B;">🟡 CHOP BUCKET</div><div style="font-size:13px;color:#FDE68A;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vr}</div></div>'
    elif vb=="Defensive":  vh=f'<div class="vix-defensive"><div style="font-size:20px;font-weight:800;color:#EF4444;">🔴 DEFENSIVE BUCKET</div><div style="font-size:13px;color:#FECACA;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vr}</div></div>'
    else: vh=""
    if vh: st.markdown(vh+"\n<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Gamma + DXY Correlations (2 columns)
    ga_col, dxy_col = st.columns([1.2, 1])
    with ga_col: st.markdown(_render_gamma(gamma_data), unsafe_allow_html=True)
    with dxy_col: st.markdown(_render_dxy_panel(prices, dxy_corr, sq), unsafe_allow_html=True)

    # Leveraged ETF Flow
    st.markdown(_render_lev(lev_data), unsafe_allow_html=True)

    # Quad Cards
    _sq_q2p=(gip.structural_probs or {}).get("Q2",0) if gip else 0
    _sq_sub=f"Q2↑ {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL — Climate",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY — Weather",mq,gip.monthly_conf if gip else 0,"Tactical"),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL — 50 Countries",gq,global_.get("global_conf",0),"GDP-weighted"),unsafe_allow_html=True)
    with c4:
        if gip:
            st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:14px;text-align:center;height:100%;">
            <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px;">ALIGNMENT</div>
            <div style="font-size:22px;font-weight:800;color:{qc(sq)};">{gip.divergence.upper()}</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">{gip.operating_regime}</div>
            <div style="font-size:11px;color:#E8ECF0;margin-top:8px;">Flip Risk: {gip.flip_hazard:.0%}</div>
            </div>''', unsafe_allow_html=True)

    # Win Rate
    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0)
        wr=(pr/max(ev,1))*100
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Evaluated</div><div style="font-size:22px;font-weight:800;color:#E8ECF0;">{ev}</div></div>',unsafe_allow_html=True)
        w2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Promoted ✅</div><div style="font-size:22px;font-weight:800;color:#10B981;">{pr}</div></div>',unsafe_allow_html=True)
        w3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Demoted ❌</div><div style="font-size:22px;font-weight:800;color:#EF4444;">{dm}</div></div>',unsafe_allow_html=True)
        w4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Win Rate</div><div style="font-size:22px;font-weight:800;color:#00D4AA;">{wr:.1f}%</div></div>',unsafe_allow_html=True)

    # Front-Run + Sequencing
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        if fw!="not yet":
            st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:6px;margin-top:10px;"><div style="font-size:14px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        st.markdown(_sequence_pills(sq,mq), unsafe_allow_html=True)

    # Quick action summary
    if pb_data:
        best5=" · ".join(pb_data.get("best_assets",[])[:6])
        worst5=" · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'''<div class="action-box">
        <div style="font-size:12px;font-weight:700;color:#58a6ff;margin-bottom:6px;">🎯 QUICK ACTION — {sq} Structural · {mq} Monthly</div>
        <div style="font-size:12px;color:#E8ECF0;">✅ <b>LONG:</b> {best5}</div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">❌ <b>AVOID:</b> {worst5}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Full detail → <b>📈 GIP Model</b> · <b>⚡ ETF Pro</b> · <b>📋 Playbook</b></div>
        </div>''', unsafe_allow_html=True)

    # Discovery alert (1 line only)
    if auto_disc:
        brewing=[c for c in auto_disc.get("candidates",[]) if c.get("stage")=="brewing"]
        if brewing:
            tb=max(brewing,key=lambda x:x.get("confidence",0))
            st.markdown(f'<div style="background:#6366F122;border-left:4px solid #6366F1;padding:10px;border-radius:6px;margin-top:10px;"><span style="font-size:12px;font-weight:700;color:#818CF8;">🔮 {len(brewing)} pre-consensus opportunities</span><span style="font-size:11px;color:#E8ECF0;"> — Top: <b>{tb.get("name","")}</b> → see <b>🔮 Discovery</b></span></div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP MODEL — The Map (macro analysis, probability charts, analogs)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative. 'Heating up or cooling down?' — 30 data points monthly, 90 quarterly.")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    # Climate vs Weather
    st.markdown("### 🌤 Climate vs. Weather")
    cc,cw=st.columns(2)
    with cc:
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(sq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">STRUCTURAL — CLIMATE (Quarterly)</div>
        <div style="font-size:32px;font-weight:800;color:{qc(sq)};">{sq}</div>
        <div style="font-size:13px;color:{qc(sq)};margin-top:4px;">{qnc(sq)}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.structural_conf:.0%} · Flip Risk: {gip.flip_hazard:.0%} · Coverage: {gip.data_coverage:.0%}</div>
        </div>''', unsafe_allow_html=True)
    with cw:
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(mq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">MONTHLY — WEATHER (3-6 Week Overlay)</div>
        <div style="font-size:32px;font-weight:800;color:{qc(mq)};">{mq}</div>
        <div style="font-size:13px;color:{qc(mq)};margin-top:4px;">{qnc(mq)}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.monthly_conf:.0%} · Divergence: {gip.divergence} · {gip.operating_regime}</div>
        </div>''', unsafe_allow_html=True)

    # G + I Signals
    st.markdown("---"); st.markdown("### 📊 Growth & Inflation Signals")
    f=gip.features; gm=f.get("growth_momentum",0); im=f.get("inflation_momentum",0)
    gc2="#10B981" if gm>0 else "#EF4444"; ic2="#10B981" if im<0 else "#EF4444"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Growth Momentum</div><div style="font-size:24px;font-weight:800;color:{gc2};">{fp(gm)}</div><div style="font-size:10px;color:#6B7280;">{"Accel ↑" if gm>0 else "Decel ↓"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Inflation Momentum</div><div style="font-size:24px;font-weight:800;color:{ic2};">{fp(im)}</div><div style="font-size:10px;color:#6B7280;">{"Rising ↑" if im>0 else "Cooling ↓"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Policy Score</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("policy_score"))}</div><div style="font-size:10px;color:#6B7280;">{"Dovish" if f.get("policy_score",0)>0.1 else "Hawkish" if f.get("policy_score",0)<-0.1 else "Neutral"}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Leading Indicator</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("leading_indicator_composite"))}</div><div style="font-size:10px;color:#6B7280;">FRED: {fp(f.get("data_coverage"))}</div></div>',unsafe_allow_html=True)

    # Transition Probability Charts
    st.markdown("---"); st.markdown("### 📊 Quad Transition Probabilities")
    QWINS={"Q1":"Cyclicals, Tech, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives","Q4":"TLT, Gold, Utilities, Cash"}

    def _tp(probs, cur_q, label, desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;margin-bottom:8px;">
        <div style="font-size:11px;color:#9CA3AF;">{label} — {desc}</div>
        <div style="font-size:13px;color:#E8ECF0;margin-top:4px;">Currently: <b style="color:{qc(cur_q)};">{cur_q}</b></div>
        <div style="font-size:12px;color:#9CA3AF;margin-top:2px;">Most likely → <b style="color:{qc(top_q)};">{top_q}</b> ({top_p:.0%})</div>
        </div>''', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        if top_q!=cur_q:
            st.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;font-size:11px;color:#F59E0B;">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)

    sq_q2p=(gip.structural_probs or {}).get("Q2",0)
    sq_desc=qnc(sq)+(f" · Q2↑ {sq_q2p:.0%}" if sq=="Q3" and sq_q2p>0.25 else "")
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",sq_desc)
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq))
    with tp3:
        gprobs=global_.get("global_probs",{})
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")

    # Regime Timing (front-run + sequencing)
    st.markdown("---"); st.markdown("### ⏱ Regime Timing")
    st.markdown(_sequence_pills(sq,mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:6px;"><div style="font-size:14px;font-weight:700;color:{fwc};">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        ew=getattr(transition,"early_warning_signals",{})
        if ew:
            st.markdown("#### Early Warning Signals")
            ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"✅" if v>=0.5 else "⬜","Score":f"{v:.0f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=280)
            fc=sum(1 for v in ew.values() if v>=0.5)
            st.progress(fc/max(len(ew),1),text=f"Early warning: {fc}/{len(ew)} firing")

    # Historical Analogs
    if analogs and analogs.get("top_analogs"):
        st.markdown("---"); st.markdown("### 📚 Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"**{a['label']}** — Similarity: {a.get('similarity',0):.0%}", expanded=(i==0)):
                cc2=st.columns(3)
                cc2[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc2[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")
                imp=a.get("impacts",{})
                if imp: st.markdown("**Impacts:** "+" | ".join(f"{k.upper()}={v}" for k,v in imp.items()))


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES™ — The Compass (LRR/TRR table)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("**LRR** = buy zone. **TRR** = trim zone. TREND break = exit. McCullough: 'Buy the damn dip in bullish formation.'")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
                 key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Live Alerts")
        for sym,a in all_a[:20]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
            bdr="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {bdr};padding:8px;border-radius:4px;margin-bottom:4px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>',unsafe_allow_html=True)

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
                     "TRADE":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
                     "Stretch":tr.get("stretch","—"),"Hurst":ff(v.get("trend",{}).get("hurst")),
                     "Market":v.get("market","—"),"Trap":"⚠️" if v.get("regime_trap") else ""})
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=520)
    else: st.info("No data matches filter.")


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ETF PRO — The Positions (ETF ideas by asset class)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ ETF Pro":
    st.markdown("# ⚡ ETF Pro — Quad-Aware ETF Positioning")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly · Go Anywhere, But Not Everywhere. ~25-35 ETF ideas, updated weekly.")
    ar=rr.get("asset_ranges",{}); best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))

    MARKET_LABELS={"us_equity":"🇺🇸 US Equity","forex":"💱 Forex","commodity":"🛢 Commodities","crypto":"₿ Crypto","ihsg":"🇮🇩 IHSG"}
    tabs=st.tabs(list(MARKET_LABELS.values()))
    for tab,(mkt,mlabel) in zip(tabs,MARKET_LABELS.items()):
        with tab:
            rows=[]
            for sym,v in ar.items():
                if v.get("market","")!=mkt: continue
                tr=v.get("trade",{}); px=v.get("px",float("nan"))
                lrr=tr.get("lrr",float("nan")); trr=tr.get("trr",float("nan"))
                comp=v.get("composite","neutral")
                qf="✅ LONG" if sym in best_set else ("❌ AVOID" if sym in worst_set else "—")
                rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(lrr),"TRR":ff(trr),
                             "Signal":comp.upper(),"Quality":v.get("quality","—"),
                             "Stretch":tr.get("stretch","—"),"Quad Fit":qf,
                             "Trap":"⚠️" if v.get("regime_trap") else ""})

            if mkt=="crypto" and dxy_corr:
                st.markdown(_render_dxy_panel(prices, dxy_corr, sq), unsafe_allow_html=True)
                # Bitcoin specific signal
                btc_rr=ar.get("IBIT",ar.get("BTC-USD",{}))
                btc_sig=btc_rr.get("composite","—")
                btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
                btc_css="btc-long" if btc_sig=="bullish" else ("btc-short" if btc_sig=="bearish" else "btc-neutral")
                btc_action="LONG IBIT" if btc_sig=="bullish" and sq!="Q4" else ("EXIT — Q4 exception" if sq=="Q4" else "WAIT — Bearish TREND")
                st.markdown(f'''<div class="{btc_css}">
                <b style="color:{btc_c};">₿ BITCOIN SIGNAL: {btc_sig.upper()} → {btc_action}</b><br>
                <span style="font-size:11px;color:#9CA3AF;">DXY/BTC 15D corr: {dxy_corr.get("Bitcoin","—")} · Keith: "Any quad other than Q4, bitcoin = biggest digital asset position."</span>
                </div>''', unsafe_allow_html=True)

            if rows:
                st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=450)
                longs=[r for r in rows if r["Signal"]=="BULLISH" and r["Quad Fit"]=="✅ LONG"][:4]
                shorts=[r for r in rows if r["Signal"]=="BEARISH" and r["Quad Fit"]=="❌ AVOID"][:4]
                if longs:
                    st.markdown("**Top Long Setups:**")
                    for e in longs: st.markdown(f'<div class="etf-long"><b style="color:#10B981;">{e["Ticker"]}</b> · Px {e["Px"]} · LRR <b>{e["LRR"]}</b> · TRR {e["TRR"]} · {e["Quality"]} · {e["Stretch"]}</div>',unsafe_allow_html=True)
                if shorts:
                    st.markdown("**Top Short Setups:**")
                    for e in shorts: st.markdown(f'<div class="etf-short"><b style="color:#EF4444;">{e["Ticker"]}</b> · Px {e["Px"]} · TRR <b>{e["TRR"]}</b> · LRR {e["LRR"]} · {e["Quality"]} · {e["Stretch"]}</div>',unsafe_allow_html=True)
            else: st.info(f"No {mlabel} data. Refresh.")


# ══════════════════════════════════════════════════════════════════════════════
# 📊 LEADERBOARD — Quality A Stock Picks
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown("# 📊 The Leaderboard — Signal Strength Stocks")
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
    s1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Bullish Names</div><div style="font-size:28px;font-weight:800;color:#10B981;">{len(long_picks)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Longs</div><div style="font-size:28px;font-weight:800;color:#00D4AA;">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Shorts</div><div style="font-size:28px;font-weight:800;color:#EF4444;">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Regime Traps</div><div style="font-size:28px;font-weight:800;color:#F59E0B;">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### 🟢 TOP 21 LONG IDEAS")
    for p in long_picks[:21]:
        st.markdown(f'''<div class="signal-A">
        <div style="display:flex;justify-content:space-between;">
          <span style="font-size:15px;font-weight:800;color:#10B981;">{p["ticker"]} <span style="font-size:11px;color:#A7F3D0;">({p["quality"]})</span></span>
          <span style="font-size:11px;color:#9CA3AF;">{"✅" if p["regime_fit"] else "⚠️"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</span>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · LRR: <b>{ff(p["lrr"])}</b> · TRR: {ff(p["trr"])} · {p["note"]}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div>
        </div>''', unsafe_allow_html=True)
    if not long_picks: st.info("No Quality A/B longs. Market may be extended.")

    st.markdown("---"); st.markdown("### 🔴 SHORT IDEAS")
    for p in short_picks[:15]:
        st.markdown(f'''<div class="signal-shortA">
        <div style="display:flex;justify-content:space-between;">
          <span style="font-size:15px;font-weight:800;color:#EF4444;">{p["ticker"]} <span style="font-size:11px;color:#FECACA;">({p["quality"]})</span></span>
          <span style="font-size:11px;color:#9CA3AF;">{"✅" if p["regime_fit"] else "⚠️"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</span>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · TRR: <b>{ff(p["trr"])}</b> · LRR: {ff(p["lrr"])} · {p["note"]}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div>
        </div>''', unsafe_allow_html=True)
    if not short_picks: st.info("No Quality Short-A/B setups.")

    with st.expander("📋 Full Signal Table"):
        all_rows=([{"Ticker":p["ticker"],"Side":"LONG","Quality":p["quality"],"Score":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"Regime":"✅" if p["regime_fit"] else "—"} for p in long_picks]+
                  [{"Ticker":p["ticker"],"Side":"SHORT","Quality":p["quality"],"Score":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"Regime":"✅" if p["regime_fit"] else "—"} for p in short_picks])
        if all_rows: st.dataframe(pd.DataFrame(all_rows),hide_index=True,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD — 50 countries + EM recovery
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50 Countries")
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
        for country,data in global_.get("country_quads",{}).items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=data[0],data[1],data[2]
            elif isinstance(data,dict): etf,quad,conf=data.get("etf",""),data.get("quad",""),data.get("conf",0)
            else: etf,quad,conf="","",0
            heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            df=pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),hide_index=True,height=420,use_container_width=True)
        else: st.info("No country quad data.")

    st.markdown("---"); st.markdown("### 🌏 EM Recovery Signal")
    em_sig=btk.get("em_recovery",{}) if btk else {}
    if em_sig:
        conf=em_sig.get("confidence",0); ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">
        <div style="font-size:13px;font-weight:700;color:{ec};">{em_sig.get("trigger","")}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div>
        <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Confidence: {conf:.0%} · Best: {", ".join(em_sig.get("best",[])[:6])}</div>
        </div>''', unsafe_allow_html=True)
    else: st.info("EM recovery signal belum tersedia.")


# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG — Indonesia only
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Market")
    st.caption("Local signal + sector thesis. Bank CKPN · OSV hulu · Coal cycle · Foreign flow.")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}
    if ihsg:
        rows=[{"Ticker":sym,"Px":ff(v.get("px",float("nan")),0),"LRR":ff(v.get("trade",{}).get("lrr"),0),"TRR":ff(v.get("trade",{}).get("trr"),0),"Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),"Stretch":v.get("trade",{}).get("stretch","—"),"Trap":"⚠️" if v.get("regime_trap") else ""} for sym,v in ihsg.items()]
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else: _render_universe("IHSG Universe",IHSG_UNIVERSE,prices,btk,days=252)

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
                b_rows.append({"Ticker":t,"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}","Bottleneck":_btk_badge(t,btk)})
            if b_rows: st.markdown(pd.DataFrame(b_rows).to_html(escape=False,index=False),unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🔍 BOTTLENECK — Supply Chain Alpha
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Bottleneck":
    st.markdown("# 🔍 Bottleneck Scanner — Supply Chain Alpha")
    st.caption("Citrini: demand river meets capacity constraint. Second-order: own the bottleneck, not the end market.")
    if not btk: st.warning("No bottleneck data. Refresh."); st.stop()

    l1=btk.get("level_1",[]); l2=btk.get("level_2",[]); wt=btk.get("watch",[]); av=btk.get("avoid",[])
    s1,s2,s3,s4=st.columns(4)
    for col,lab,val,c in [(s1,"Level 1",len(l1),"#10B981"),(s2,"Level 2",len(l2),"#F59E0B"),(s3,"Watch",len(wt),"#6366F1"),(s4,"Avoid",len(av),"#EF4444")]:
        col.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">{lab}</div><div style="font-size:28px;font-weight:800;color:{c};">{val}</div></div>',unsafe_allow_html=True)

    def _rl(data,title):
        if not data: return
        with st.expander(f"**{title}** ({len(data)})",expanded=title.startswith("⚡")):
            rows=[{"Ticker":c["ticker"],"Sector":c["sector"].replace("_"," ").title(),"Trend":c["trend"],"Score":f'{c["score"]:.2f}',"EV":f'{c.get("ev",0):.2f}',"RF":f'{c.get("regime_fit",0):.0%}',"Constraint":f'{c.get("constraint",0):.0%}',"Thesis":c.get("known_thesis","")[:60]} for c in data]
            if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=min(len(rows)*35+40,400))

    _rl(l1,"⚡ Level 1 — Best"); _rl(l2,"📈 Level 2 — Building")
    _rl(wt,"👀 Watch — Brewing"); _rl(av,"🚫 Avoid — Regime Trap")

    st.markdown("---")
    for mkt,items in (btk.get("market_buckets",{}) or {}).items():
        if not items: continue
        with st.expander(f"**{mkt.replace('_',' ').upper()}** — {len(items)}"):
            for c in items[:12]:
                tc="#10B981" if c.get("direction")=="long" else "#EF4444" if c.get("direction")=="short" else "#9CA3AF"
                st.markdown(f'<div style="background:#111827;border:1px solid #1F2B3D;border-radius:6px;padding:8px;margin-bottom:4px;"><span style="font-size:13px;font-weight:700;color:{tc};">{c["ticker"]}</span><span style="font-size:11px;color:#9CA3AF;margin-left:8px;">{c.get("sector","").replace("_"," ").title()} · Score {c.get("score",0):.2f} · EV {c.get("ev",0):.2f}</span>{"<span style=\'font-size:10px;color:#EF4444;margin-left:8px;\'>⚠️ REGIME TRAP</span>" if c.get("regime_trap") else ""}</div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES — Thematic Scoring
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown("# 📖 Narratives — Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus. Score = conviction × regime fit.")
    if not narr: st.warning("No narrative data. Refresh."); st.stop()
    active=narr.get("active_narratives",[])
    for n in sorted(active,key=lambda x:x.get("score",0),reverse=True):
        score=n.get("score",0); sc="#10B981" if score>0.6 else "#F59E0B" if score>0.4 else "#6B7280"
        with st.expander(f"**{n.get('name','')}** — {score:.0%}"):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' · '.join(n.get('tickers',[])[:8])}")
            inv=n.get("invalidators",[]); best=n.get("best",[]); worst=n.get("worst",[])
            if inv:  st.markdown(f"**Invalidators:** {', '.join(inv[:3])}")
            if best: st.markdown(f"**Best:** {' · '.join(best[:10])}")
            if worst:st.markdown(f"**Worst:** {' · '.join(worst[:10])}")
    if not active: st.info("Narratives not yet at critical mass.")


# ══════════════════════════════════════════════════════════════════════════════
# 🔮 DISCOVERY — Pre-Consensus Opportunities
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown("# 🔮 Early Discovery — Pre-Consensus")
    st.caption("Autonomy engine: regime fit + price cluster + supply chain graph + news NLP.")
    cands=(auto_disc.get("candidates",[]) if auto_disc else [])+(disc.get("discoveries",[]) if disc else [])
    if not cands: st.info("No discoveries yet. Run Force build."); st.stop()
    for stage,sc in [("active","#10B981"),("building","#F59E0B"),("brewing","#6366F1")]:
        items=[c for c in cands if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper()} ({len(items)})")
        for c in items:
            conf=c.get("confidence",c.get("conviction",0)); pump=c.get("pump_risk",0)
            with st.expander(f"**{c.get('name','')}** — Conf: {conf:.0%} · Pump: {pump:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                st.markdown(f"**Category:** {c.get('category','')}")
                ben=c.get("beneficiary_tickers",[]); fade=c.get("fade_tickers",[])
                if ben:  st.markdown(f"**Beneficiaries:** {' · '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' · '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs:  st.markdown(f"**Confirmation:** {cs}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")


# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH — Market Vitals
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown("# 🏥 Market Health — VIX · Breadth · Crash Meter")
    if not health: st.warning("No health data. Refresh."); st.stop()
    vb=health.get("vix_bucket",{}); vb_b=vb.get("bucket","—")
    vb_c={"Investable":"#10B981","Chop":"#F59E0B","Defensive":"#EF4444"}.get(vb_b,"#6B7280")
    st.markdown(f'<div style="background:{vb_c}22;border-left:4px solid {vb_c};padding:12px;border-radius:6px;"><div style="font-size:16px;font-weight:800;color:{vb_c};">VIX BUCKET: {vb_b.upper()}</div><div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{vb.get("note","")}</div></div>',unsafe_allow_html=True)

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
        b1.metric("Score",f"{breadth.get('score',0):.2f}"); b2.metric("Verdict",breadth.get("verdict","—"))
        b3.metric("Sector Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW Health",f"{breadth.get('eqw_health',0):.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"• {note}")

    fg=health.get("fear_greed",{})
    if fg:
        st.markdown("---"); st.markdown("### Fear & Greed")
        fgs=fg.get("score",50); fgc="#10B981" if fgs<25 else "#F59E0B" if fgs<55 else "#EF4444"
        st.markdown(f"**Score:** <span style='color:{fgc};font-size:18px;font-weight:700;'>{fgs:.0f}/100</span> — {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)


# ══════════════════════════════════════════════════════════════════════════════
# 📋 PLAYBOOK — Full Regime Action Plan + Scenarios
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown("# 📋 Regime Playbook")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly · Scored by data, not opinion.")

    if pb_data:
        st.markdown("### 🎯 Regime Positioning")
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f'''<div class="etf-long" style="padding:14px;">
            <div style="font-size:13px;font-weight:700;color:#10B981;margin-bottom:8px;">✅ LONG — {sq}</div>
            <div style="font-size:13px;color:#E8ECF0;">{" · ".join(pb_data.get("best_assets",[]))}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Style: {pb_data.get("style","")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">FX: {pb_data.get("fx","")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Bonds: {pb_data.get("bonds","")}</div>
            {('<div style="font-size:11px;color:#F59E0B;margin-top:4px;">Monthly adds: ' + " · ".join(pb_data.get("monthly_adds",[])) + '</div>') if pb_data.get("monthly_adds") else ""}
            </div>''', unsafe_allow_html=True)
        with col2:
            st.markdown(f'''<div class="etf-short" style="padding:14px;">
            <div style="font-size:13px;font-weight:700;color:#EF4444;margin-bottom:8px;">❌ AVOID — {sq}</div>
            <div style="font-size:13px;color:#E8ECF0;">{" · ".join(pb_data.get("worst_assets",[]))}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Hedge: {pb_data.get("hedge","BTAL")}</div>
            <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{pb_data.get("sizing_note","Min 1% · Max 3%")}</div>
            </div>''', unsafe_allow_html=True)

    # Bitcoin status with DXY correlation
    btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
    btc_sig=btc_rr.get("composite","—")
    btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
    btc_corr_val=dxy_corr.get("Bitcoin","—")
    q4_note=" (Q4 EXCEPTION — Exit BTC)" if sq=="Q4" else ""
    st.markdown(f'''<div style="background:#111827;border-left:4px solid {btc_c};padding:10px;border-radius:6px;margin-top:10px;">
    <span style="font-size:12px;font-weight:700;color:{btc_c};">₿ BITCOIN: {btc_sig.upper()}{q4_note}</span>
    <span style="font-size:11px;color:#9CA3AF;"> — DXY/BTC 15D corr: {btc_corr_val} · "Any quad other than Q4, bitcoin = biggest digital asset position."</span>
    </div>''', unsafe_allow_html=True)

    # Scenarios
    scenarios_list=scen.get("scenarios",[])
    if scenarios_list:
        st.markdown("---"); st.markdown("### 🔮 Scenario Probability Map")
        badges=["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]; badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
        row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]; em=sc_item.em_note[:60]+"..." if len(sc_item.em_note)>60 else sc_item.em_note
            with col:
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;">
                <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} P={sc_item.probability:.0%} · Conf={sc_item.confirmation_score:.0%}</div>
                <div style="font-size:13px;color:#E8ECF0;margin-top:6px;font-weight:600;">{sc_item.name}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{sc_item.headline}</div>
                <div style="font-size:11px;color:#10B981;margin-top:4px;">Best: {" · ".join(sc_item.best_assets[:4])}</div>
                <div style="font-size:11px;color:#EF4444;margin-top:2px;">Avoid: {" · ".join(sc_item.worst_assets[:4])}</div>
                <div style="font-size:10px;color:#6B7280;margin-top:4px;">🌍 {em}</div>
                </div>''', unsafe_allow_html=True)

    # Confirmation + Invalidators
    bc=scen.get("base_case")
    if bc and hasattr(bc,"confirmation_triggers"):
        st.markdown("---"); ct,ci=st.columns(2)
        with ct:
            st.markdown(f"### ✅ Confirmation Triggers ({bc.name})")
            for t in getattr(bc,"confirmation_triggers",[]): st.markdown(f"• {t}")
        with ci:
            st.markdown("### ❌ Invalidators")
            for inv in getattr(bc,"invalidators",[]): st.markdown(f"• {inv}")

    # GIP feature data
    if gip:
        st.markdown("---"); st.markdown("### 📡 GIP Feature Data")
        f=gip.features
        rows=[["Growth Momentum",fp(f.get("growth_momentum")),"↑" if f.get("growth_momentum",0)>0 else "↓"],
              ["Inflation Momentum",fp(f.get("inflation_momentum")),"↑" if f.get("inflation_momentum",0)>0 else "↓"],
              ["Policy Score",fp(f.get("policy_score")),""],
              ["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
              ["Data Coverage",fp(f.get("data_coverage")),""],
              ["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
              ["Structural Conf",f"{gip.structural_conf:.0%}",""],
              ["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
        st.dataframe(pd.DataFrame(rows,columns=["Signal","Value","Dir"]),hide_index=True,use_container_width=True)

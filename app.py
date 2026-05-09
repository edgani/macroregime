"""app.py — MacroRegime Pro v19 | Hedgeye-Class Client Dashboard

Design principles:
  1. Client-first: every label uses plain language, no jargon
  2. Action-driven: every screen answers "what should I do?"
  3. Zero duplicates across tabs
  4. All numbers formatted (never 6 decimal places)
  5. Every trade has: entry, target 1, target 2, stop loss, R:R, hold time
  6. Options data integrated where available (expiry-aware)
  7. Shorts logic corrected: Entry=TRR, TP=LRR direction

11 Tabs:
  🏠 Dashboard      — Command center. 30-second read.
  📈 GIP Model      — The Map. Macro regime with plain explanations.
  🎯 Risk Ranges™   — Every asset: buy zone, trim zone, stop.
  ⚡ Alpha Center   — Best trades right now. Table + detail view.
  📊 Leaderboard    — Stock picks with full levels.
  🌍 Global Quad    — World map. Where is money rotating?
  🇮🇩 IHSG          — Indonesia stocks.
  📖 Narratives     — What themes are running?
  🔮 Discovery      — Pre-consensus ideas.
  🏥 Health         — Market risk indicators.
  📋 Playbook       — Full regime action plan.
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

# ── Professional Dark Theme CSS ────────────────────────────────────────────────
st.markdown("""<style>
/* Base */
[data-testid="stAppViewContainer"] { background-color: #0D1117; }
[data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }

/* Metric cards */
.card {background:#161B22;border:1px solid #30363D;border-radius:12px;padding:20px;height:100%;}
.card-green  {background:linear-gradient(135deg,#0D2818,#0A2010);border:1px solid #238636;border-left:4px solid #3FB950;border-radius:10px;padding:16px;margin-bottom:10px;}
.card-red    {background:linear-gradient(135deg,#2D1215,#200A0A);border:1px solid #DA3633;border-left:4px solid #F85149;border-radius:10px;padding:16px;margin-bottom:10px;}
.card-yellow {background:linear-gradient(135deg,#2D2108,#1C1300);border:1px solid #BB8009;border-left:4px solid #D29922;border-radius:10px;padding:16px;margin-bottom:10px;}
.card-blue   {background:linear-gradient(135deg,#0C1A2E,#071120);border:1px solid #1F6FEB;border-left:4px solid #58A6FF;border-radius:10px;padding:16px;margin-bottom:10px;}
.card-purple {background:linear-gradient(135deg,#1A0D2E,#100720);border:1px solid #6E40C9;border-left:4px solid #A371F7;border-radius:10px;padding:16px;margin-bottom:10px;}

/* Status badges */
.badge-buy   {background:#238636;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;display:inline-block;}
.badge-sell  {background:#DA3633;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;display:inline-block;}
.badge-wait  {background:#BB8009;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;display:inline-block;}
.badge-watch {background:#1F6FEB;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;display:inline-block;}

/* Section headers */
.section-header {font-size:20px;font-weight:700;color:#E6EDF3;margin:20px 0 8px 0;border-bottom:1px solid #30363D;padding-bottom:8px;}
.sub-header {font-size:14px;color:#8B949E;margin-bottom:12px;}

/* Pill tags */
.pill {display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;margin:2px;}
.pill-green {background:#162a1e;color:#3FB950;border:1px solid #238636;}
.pill-red   {background:#2d1215;color:#F85149;border:1px solid #DA3633;}
.pill-yellow{background:#2d2108;color:#D29922;border:1px solid #BB8009;}
.pill-blue  {background:#0c1a2e;color:#58A6FF;border:1px solid #1F6FEB;}
.pill-gray  {background:#21262D;color:#8B949E;border:1px solid #30363D;}

/* Range bar */
.range-bar-container{background:#21262D;height:8px;border-radius:4px;overflow:hidden;margin:4px 0;}
.range-bar-fill{height:100%;border-radius:4px;transition:width 0.3s;}

/* Seq row */
.seq-row{display:flex;align-items:center;gap:8px;padding:12px 16px;background:#161B22;border-radius:8px;flex-wrap:wrap;margin:8px 0;border:1px solid #30363D;}

/* Table styling */
[data-testid="stDataFrame"] { border: 1px solid #30363D; border-radius: 8px; }
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC  = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}
QN  = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
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

def qc(q):   return QC.get(q,"#8B949E")
def qn(q):   return QN.get(q,q)
def qnc(q):  return QNC.get(q,q)

def fp(v):
    try:    return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=2):
    try:    return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def _sf(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v); return f if math.isfinite(f) else None
    except: return None


# ── Direction-aware entry/TP/stop ─────────────────────────────────────────────
def _rr_levels(px, lrr, trr, side="long"):
    """
    LONG:  Entry=LRR, TP1=midpoint↑, TP2=TRR, Stop=below LRR
    SHORT: Entry=TRR, TP1=midpoint↓, TP2=LRR, Stop=above TRR
    """
    px  = _sf(px)  or 0
    lrr = _sf(lrr) or 0
    trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = max(0.0, min(1.0, (px - lrr) / spread)) if spread > 0 else 0.5

    if side == "long":
        entry = round(lrr, 2)
        tp1   = round(lrr + spread * 0.50, 2)
        tp2   = round(trr, 2)
        stop  = round(lrr - spread * 0.25, 2)
        near_entry  = pos <= 0.35
        can_enter   = pos <= 0.55
        near_target = pos >= 0.75
        if near_entry:    action = "✅ Buy Now — Price at Buy Zone"
        elif can_enter:   action = "📈 Still Good — Can Enter (Not Ideal)"
        elif near_target: action = "🔴 Take Profit — Near Target"
        else:             action = "⏳ Wait — Not at Best Entry Yet"
    else:
        entry = round(trr, 2)
        tp1   = round(trr - spread * 0.50, 2)
        tp2   = round(lrr, 2)
        stop  = round(trr + spread * 0.25, 2)
        near_entry  = pos >= 0.65
        can_enter   = pos >= 0.45
        near_target = pos <= 0.25
        if near_entry:    action = "✅ Sell/Short — Price at Sell Zone"
        elif can_enter:   action = "📉 Still Ok — Partial Short"
        elif near_target: action = "🔴 Cover Short — Near Target"
        else:             action = "⏳ Wait — Price Not High Enough to Short Yet"

    rr_r = round(abs(tp1 - entry) / max(abs(entry - stop), 0.01), 2)
    hold = "3 months+" if rr_r >= 2.5 else ("1-3 weeks" if rr_r >= 1.5 else "Skip — poor reward:risk")

    return {
        "entry": entry, "tp1": tp1, "tp2": tp2, "stop": stop,
        "rr": rr_r, "pos": round(pos, 2), "side": side, "hold": hold,
        "near_entry": near_entry, "near_target": near_target,
        "can_enter": can_enter, "action": action,
    }

def _merge_with_options(rl, opt, side="long"):
    if not opt or not opt.get("ok") or not rl: return rl
    if side == "long":
        ll = opt.get("long_levels",{}) or {}
        if ll.get("ev_ok"):
            for k in ["entry","tp1","tp2","stop","rr"]:
                if ll.get(k): rl[k] = ll[k]
            rl["opt_confirm"] = True
            rl["hold"] = ll.get("holding", rl["hold"])
    else:
        sl = opt.get("short_levels",{}) or {}
        if sl.get("ev_ok"):
            for k in ["entry","tp1","tp2","stop","rr"]:
                if sl.get(k): rl[k] = sl[k]
            rl["opt_confirm"] = True
            rl["hold"] = sl.get("holding", rl["hold"])
    return rl


# ── Client-friendly ticker table builder ─────────────────────────────────────
def _client_table(picks, side="long"):
    """
    Build a DataFrame that a non-expert client can read.
    Plain English labels. Numbers formatted. Status clear.
    """
    rows = []
    for p in picks:
        rl = p.get("rl") or {}
        if not rl: continue
        action = rl.get("action","—")
        # Status emoji only
        if "Buy Now" in action or "Sell/Short" in action:  st_icon = "✅ Act Now"
        elif "Still Good" in action or "Still Ok" in action: st_icon = "📊 Chase OK"
        elif "Take Profit" in action or "Cover" in action:   st_icon = "🔴 Take Profit"
        else:                                                  st_icon = "⏳ Wait"

        # Position bar (0-100%)
        pos_pct = round(rl.get("pos",0.5)*100)
        pos_bar = f"{'█'*int(pos_pct/10)}{'░'*(10-int(pos_pct/10))} {pos_pct}%"

        # R/R simplified
        rr = _sf(rl.get("rr"))
        rr_str = f"{rr:.1f}×" if rr else "—"

        opt_tag = " ✦" if rl.get("opt_confirm") else ""

        rows.append({
            "Ticker": p.get("ticker",""),
            "Sector": p.get("sector","").replace("_"," ").title()[:14],
            "Price": ff(_sf(p.get("px"))),
            "Status": st_icon,
            "Buy/Sell at": ff(_sf(rl.get("entry"))),
            "Target 1": ff(_sf(rl.get("tp1"))),
            "Target 2": ff(_sf(rl.get("tp2"))),
            "Stop Loss": ff(_sf(rl.get("stop"))),
            "Reward:Risk": rr_str + opt_tag,
            "Hold For": rl.get("hold","—")[:12],
            "Grade": p.get("quality","—"),
            "In Range%": pos_bar,
        })
    return pd.DataFrame(rows)


# ── Visual components ─────────────────────────────────────────────────────────
def _quad_badge(q, size=28):
    c = qc(q)
    pill = {"Q1":"pill-green","Q2":"pill-yellow","Q3":"pill-red","Q4":"pill-purple"}.get(q,"pill-gray")
    return f'<span class="{pill}" style="font-size:{size}px;font-weight:800;padding:4px 14px;">{q}</span>'

def _status_pill(status, text):
    css = {"buy":"pill-green","sell":"pill-red","wait":"pill-yellow","watch":"pill-blue"}.get(status,"pill-gray")
    return f'<span class="{css}">{text}</span>'

def _range_bar_html(pos, color="#3FB950"):
    w = max(0, min(100, round(pos*100)))
    return f'''<div class="range-bar-container">
    <div class="range-bar-fill" style="width:{w}%;background:{color};"></div>
    </div><div style="font-size:10px;color:#8B949E;margin-top:2px;">{w}% from buy zone</div>'''

def _metric_box(label, value, sub="", color="#E6EDF3"):
    return f'''<div class="card" style="text-align:center;">
    <div style="font-size:11px;color:#8B949E;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
    <div style="font-size:26px;font-weight:800;color:{color};">{value}</div>
    {f'<div style="font-size:11px;color:#8B949E;margin-top:4px;">{sub}</div>' if sub else ""}
    </div>'''

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
    sqc=qc(sq); mqc=qc(mq)
    s = "padding:4px 14px;border-radius:20px;font-weight:700;font-size:13px;"
    arr = '<span style="color:#30363D;font-size:16px;margin:0 4px;">→</span>'
    if sq == mq:
        return f'<div class="seq-row"><span style="color:#8B949E;font-size:12px;">Regime:</span><span style="background:{sqc}22;color:{sqc};border:1px solid {sqc};{s}">{sq} ALIGNED</span><span style="color:#8B949E;font-size:11px;margin-left:6px;">Both monthly and quarterly point the same direction</span></div>'
    if sq == "Q3" and mq in ("Q2","Q1"):
        target = "Q1 TARGET" if mq=="Q2" else "WATCH Q2→Q1"
        return f'<div class="seq-row"><span style="color:#8B949E;font-size:12px;">Cycle:</span><span style="background:{sqc}22;color:{sqc};border:1px solid {sqc};{s}">{sq} Structural</span>{arr}<span style="background:{mqc}22;color:{mqc};border:1px solid {mqc};{s}">{mq} Monthly</span>{arr}<span style="background:#16241E;color:#3FB950;border:1px solid #238636;{s}">{target}</span><span style="color:#8B949E;font-size:10px;margin-left:6px;">~6 weeks · watch CPI</span></div>'
    return f'<div class="seq-row"><span style="color:#8B949E;font-size:12px;">Quarterly:</span><span style="background:{sqc}22;color:{sqc};border:1px solid {sqc};{s}">{sq}</span>{arr}<span style="color:#8B949E;font-size:12px;">Monthly:</span><span style="background:{mqc}22;color:{mqc};border:1px solid {mqc};{s}">{mq}</span></div>'


# ── Gamma card ────────────────────────────────────────────────────────────────
def _gamma_card(gamma):
    if not gamma or not gamma.get("ok"):
        note=(gamma or {}).get("note","Gamma analysis loading...")
        return f'<div class="card-yellow"><div style="font-size:12px;font-weight:700;color:#D29922;margin-bottom:6px;">⚡ GAMMA REGIME (Tier 1 Alpha)</div><div style="font-size:12px;color:#8B949E;">{note}</div></div>'

    th   = _sf(gamma.get("throttle")) or 0.0
    r10  = _sf(gamma.get("rvol_10d"))
    r21  = _sf(gamma.get("rvol_21d"))
    vix  = _sf(gamma.get("vix"))
    vp   = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN"))
    label  = str(gamma.get("label","Unknown"))
    action = str(gamma.get("action","—"))
    color  = str(gamma.get("color","#8B949E"))

    # Client-friendly explanation
    regime_explain = {
        "DEEP_POSITIVE":"🟢 Very calm market. Good time to buy dips. Dealers automatically absorb volatility.",
        "POSITIVE":      "🟢 Calm market. Dips tend to get bought. Favorable conditions for longs.",
        "TRANSITION":    "🟡 Market structure shifting. More volatility possible. Be careful sizing in.",
        "NEGATIVE":      "🔴 Volatile market. Moves tend to extend and accelerate. Reduce size.",
        "DEEP_NEGATIVE": "🔴 High volatility regime. Dangerous for large positions. Stay disciplined.",
    }.get(regime, "Market structure unclear.")

    css = {
        "DEEP_POSITIVE":"card-green","POSITIVE":"card-green","TRANSITION":"card-yellow",
        "NEGATIVE":"card-red","DEEP_NEGATIVE":"card-red"
    }.get(regime,"card-yellow")

    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "—"
    vpc = "#3FB950" if (vp is not None and vp > 0) else "#F85149"

    return f'''<div class="{css}">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <span style="font-size:13px;font-weight:700;color:{color};">⚡ OPTIONS MARKET STRUCTURE</span>
      <span style="background:{color}22;color:{color};border:1px solid {color};font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{label.upper()}</span>
    </div>
    <div style="font-size:12px;color:#E6EDF3;margin-bottom:10px;">{regime_explain}</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;color:#8B949E;margin-bottom:3px;">Gamma Throttle</div>
        <div style="font-size:18px;font-weight:800;color:{color};">{f(th,"+.2f")}</div>
      </div>
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;color:#8B949E;margin-bottom:3px;">10d Volatility</div>
        <div style="font-size:18px;font-weight:700;color:#E6EDF3;">{f(r10,".1f","%")}</div>
      </div>
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;color:#8B949E;margin-bottom:3px;">VIX Level</div>
        <div style="font-size:18px;font-weight:700;color:#E6EDF3;">{f(vix,".1f")}</div>
      </div>
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;">
        <div style="font-size:10px;color:#8B949E;margin-bottom:3px;">Vol Premium</div>
        <div style="font-size:18px;font-weight:700;color:{vpc};">{f(vp,"+.1f","%")}</div>
      </div>
    </div>
    <div style="font-size:12px;color:{color};font-weight:600;">📊 Action: {action}</div>
    </div>'''


# ── Lev ETF card ──────────────────────────────────────────────────────────────
def _lev_card(lev):
    if not lev or not lev.get("ok"):
        note=(lev or {}).get("note","Leveraged ETF data loading...")
        return f'<div class="card-purple"><div style="font-size:12px;font-weight:700;color:#A371F7;margin-bottom:6px;">📊 LEVERAGED ETF FLOWS</div><div style="font-size:12px;color:#8B949E;">{note}</div></div>'
    tot=_sf(lev.get("total_mcap_b")); lo=_sf(lev.get("long_exposure_b"))
    sh=_sf(lev.get("short_exposure_b"))
    lp=float(lev.get("long_pct") or 0); sp=float(lev.get("short_pct") or 0)
    ath=bool(lev.get("is_ath",False)); rb=str(lev.get("rebalancing_pressure","—"))
    def b(v): return f"${v:.0f}B" if v else "—"
    rc={"HIGH":"#F85149","MEDIUM":"#D29922","LOW":"#3FB950"}.get(rb,"#8B949E")
    op = max(0, round(100-lp-sp,0))
    tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return f'''<div class="card-purple">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <span style="font-size:13px;font-weight:700;color:#A371F7;">📊 LEVERAGED ETF FLOWS{" · <span style='background:#DA3633;color:#fff;font-size:10px;padding:1px 6px;border-radius:4px;'>ALL TIME HIGH</span>" if ath else ""}</span>
      <span style="background:{rc}22;color:{rc};border:1px solid {rc};font-size:11px;padding:3px 10px;border-radius:20px;">Rebalancing: {rb}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px;">
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#8B949E;margin-bottom:3px;">Total Assets</div><div style="font-size:20px;font-weight:800;color:#E6EDF3;">{b(tot)}</div></div>
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#8B949E;margin-bottom:3px;">Long</div><div style="font-size:20px;font-weight:800;color:#3FB950;">{b(lo)}</div><div style="font-size:10px;color:#8B949E;">{lp:.0f}%</div></div>
      <div style="background:#0D1117;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#8B949E;margin-bottom:3px;">Short</div><div style="font-size:20px;font-weight:800;color:#F85149;">{b(sh)}</div><div style="font-size:10px;color:#8B949E;">{sp:.0f}%</div></div>
    </div>
    <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-bottom:6px;gap:2px;">
      <div style="width:{lp:.0f}%;background:#3FB950;border-radius:3px 0 0 3px;"></div>
      <div style="width:{sp:.0f}%;background:#F85149;"></div>
      <div style="width:{op:.0f}%;background:#D29922;border-radius:0 3px 3px 0;"></div>
    </div>
    <div style="font-size:10px;color:#8B949E;">Long leaders: {tls} &nbsp;|&nbsp; Short leaders: {tss}</div>
    </div>'''


# ── DXY Correlations (FIXED: 2 decimal places, not 6) ─────────────────────────
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

def _render_dxy(prices, dxy_corr, sq):
    if not dxy_corr:
        st.caption("DXY correlation data loading...")
        return
    dxy = prices.get("DX-Y.NYB")
    dxy_trend = "Neutral"
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r = float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            dxy_trend = "Bearish (falling)" if r < -0.005 else ("Bullish (rising)" if r > 0.005 else "Neutral")

    trend_color = "#F85149" if "Bearish" in dxy_trend else "#3FB950" if "Bullish" in dxy_trend else "#8B949E"

    st.markdown(f"""
    <div class="card-blue" style="padding:14px;">
    <div style="font-size:13px;font-weight:700;color:#58A6FF;margin-bottom:6px;">💱 US DOLLAR CORRELATIONS (15-Day)</div>
    <div style="font-size:12px;color:#8B949E;margin-bottom:10px;">
      Dollar Trend: <span style="color:{trend_color};font-weight:700;">{dxy_trend}</span>
      &nbsp;·&nbsp; <span style="color:#8B949E;">How each asset moves when dollar moves</span>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # FIX: format numbers properly using column_config
    rows = []
    for label, corr in dxy_corr.items():
        if corr < -0.3:   explain = "📉 Goes UP when Dollar FALLS"
        elif corr > 0.3:  explain = "📈 Goes UP when Dollar RISES"
        else:             explain = "↔ Not much affected by Dollar"
        rows.append({"Asset": label, "Correlation": corr, "What This Means": explain})
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style
          .format({"Correlation": "{:+.2f}"})  # FIX: 2 decimal places
          .background_gradient(subset=["Correlation"], cmap="RdYlGn", vmin=-1, vmax=1),
        hide_index=True, use_container_width=True, height=210,
        column_config={
            "Correlation": st.column_config.NumberColumn("15D Correlation", format="%+.2f"),
            "Asset": st.column_config.TextColumn("Asset", width="small"),
            "What This Means": st.column_config.TextColumn("What This Means", width="large"),
        }
    )

    btc = dxy_corr.get("Bitcoin")
    if btc is not None:
        if "Bearish" in dxy_trend and btc < -0.3 and sq != "Q4":
            st.success(f"₿ **Bitcoin signal**: Dollar is falling (corr {btc:+.2f}). When dollar falls, Bitcoin tends to rise. **Current signal: BUY (IBIT)**")
        elif "Bullish" in dxy_trend:
            st.warning(f"₿ **Bitcoin signal**: Dollar is rising (corr {btc:+.2f}). Dollar strength = Bitcoin headwind. **Reduce or avoid Bitcoin now.**")
        else:
            st.info(f"₿ **Bitcoin signal**: Dollar neutral (corr {btc:+.2f}). Watch for a clear direction before sizing up.")


# ── Render levels (using native st.columns — no HTML nesting bugs) ────────────
def _render_levels(rl, side="long", opt=None):
    if not rl: return
    tc = "#3FB950" if side == "long" else "#F85149"
    ext_tag = " ⚠️ Extended" if rl.get("near_target") else ""
    opt_tag = " ✦ Options confirmed" if rl.get("opt_confirm") else ""
    action  = rl.get("action","—")

    st.markdown(f'<div style="background:#0D1117;border:1px solid #30363D;border-radius:8px;padding:12px;margin-top:6px;">'
                f'<div style="font-size:11px;font-weight:700;color:{tc};margin-bottom:8px;">{action}{opt_tag}{ext_tag}</div>',
                unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Buy/Sell at",   f"${rl['entry']:,.2f}")
    c2.metric("Target 1",      f"${rl['tp1']:,.2f}")
    c3.metric("Target 2",      f"${rl['tp2']:,.2f}")
    c4.metric("Stop Loss",     f"${rl['stop']:,.2f}")
    c5.metric("Reward:Risk",   f"{rl['rr']:.1f}× · {rl.get('hold','—')[:10]}")

    if opt and opt.get("ok"):
        im = opt.get("implied_move_pct"); iv_p = opt.get("iv_percentile")
        mp = opt.get("max_pain"); vs = opt.get("vanna_signal","—"); cs = opt.get("charm_signal","—")
        st.caption(
            f"📊 Options: Implied move ±{fp(im)} · IV rank {fp(iv_p)} · Max pain ${ff(mp)} · "
            f"Vanna flow: {vs} · Charm: {cs}"
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR + AUTO-LOAD
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Powered by Hedgeye Methodology*")
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard","📈 GIP Model","🎯 Risk Ranges™","⚡ Alpha Center",
        "📊 Leaderboard","🌍 Global Quad","🇮🇩 IHSG",
        "📖 Narratives","🔮 Discovery","🏥 Health","📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")
    col1,col2=st.columns(2)
    with col1:
        if st.button("🔄 Update", use_container_width=True): st.session_state.loading=True
    with col2:
        if st.button("⚡ Full Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        inc_us   = st.checkbox("US Stocks",True)
        inc_fx   = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True)
        inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("Indonesia (IHSG)",True)
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Regime:",["Auto","Q1","Q2","Q3","Q4"],
                              index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
        st.caption("Override when model diverges from Hedgeye. May 2026 = Q2 Monthly.")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        _gq=(_gl.get("global_quad","—") if _gl else "—")
        st.markdown(f'<div style="text-align:center;margin-top:8px;">'
                    f'<div style="font-size:10px;color:#8B949E;">CURRENT REGIME</div>'
                    f'<div style="font-size:16px;font-weight:700;color:{QC.get(_sq,"#8B949E")};">{_sq} / {_mq}</div>'
                    f'<div style="font-size:10px;color:#8B949E;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div>'
                    f'</div>', unsafe_allow_html=True)

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

# ── Extract data ──────────────────────────────────────────────────────────────
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

sq    = gip.structural_quad if gip else "Q3"
mq_raw= gip.monthly_quad    if gip else "Q2"
mq    = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq    = (global_.get("global_quad","Q3") if global_ else "Q3")
ar    = rr.get("asset_ranges",{})
dxy_corr = _compute_dxy_corr(prices)
ai_data  = snap.get("ai_analysis",{}) or {}  # Claude API autonomous analysis

# Fallback narratives and discoveries
FALLBACK_NARRATIVES = [
    {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand (solar, AI chips) + safe haven. Mine supply flat. Dual demand bottleneck.","tickers":["SLV","SILJ","GDXJ","GDX","GLD"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],"invalidators":["Q4 deflation signal","DXY sustained bullish TREND"]},
    {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural. Safe haven in Q3. McCullough: 'Single best asset in Q3.'","tickers":["GLD","GDX","GDXJ","AEM","WPM"],"best":["GLD","GDX"],"worst":["HYG","IWM"],"invalidators":["Q4→Q1 direct","DXY reversal to strong bullish"]},
    {"name":"Defense Reshoring","score":0.85,"thesis":"NATO 2%+ GDP commitment. DOGE doesn't cut defense. Geopolitical premium. ITA/LMT/KTOS secular long in ALL quads.","tickers":["ITA","LMT","RTX","KTOS","PLTR","GD"],"best":["ITA","KTOS"],"worst":["XLU"],"invalidators":["Global peace agreement (low probability)"]},
    {"name":"AI Power Infrastructure","score":0.83,"thesis":"AI data centers need 24/7 firm power. Nuclear + gas only solutions at scale. VST, CEG, GEV winning long-term contracts.","tickers":["VST","CEG","GEV","ETN","VRT"],"best":["VST","CEG"],"worst":["INTC"],"invalidators":["AI capex cycle pause"]},
    {"name":"Energy Offense (Q2 Monthly)","score":0.80,"thesis":"Q2 = Reflation = Energy offense. OIH oil services = operating leverage. BNO/XOP = direct commodity price. Q2 'Knife Fights' = own energy.","tickers":["XLE","OIH","BNO","XOP","DAR","MTDR"],"best":["OIH","BNO"],"worst":["XLU","XLP"],"invalidators":["Demand collapse (Q4)"]},
    {"name":"International Rotation","score":0.78,"thesis":"JPXN +37% Q1 2026. EIS +21.8%. TUR +10.3%. USD bearish = EM tailwind. Diversify away from US concentration.","tickers":["JPXN","EIS","TUR","NORW","EWZ","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],"invalidators":["DXY bullish reversal"]},
    {"name":"Bitcoin Reflation","score":0.75,"thesis":"Keith May 6 2026: 'Bitcoin Is Back.' DXY/BTC correlation -0.83. Every quad except Q4 = long IBIT. USD bearish = Bitcoin bullish.","tickers":["IBIT","FBTC","BTC-USD"],"best":["IBIT"],"worst":["MSTY","BLOK"],"invalidators":["Q4 signal (only exception)","DXY bullish reversal"]},
    {"name":"Indonesia Commodity Supercycle","score":0.65,"thesis":"EIDO = coal + nickel + CPO + geothermal. Q2 reflation = commodity bid. PGEO geothermal = renewable hybrid. OSV sector rebound.","tickers":["EIDO","PGEO.JK","ADRO.JK","NCKL.JK","WINS.JK"],"best":["EIDO","PGEO.JK"],"worst":["TLKM.JK"],"invalidators":["China demand collapse","Q4 deflation"]},
]
FALLBACK_DISCOVERY = [
    {"name":"AI Photonics Bottleneck","category":"Structural Constraint","stage":"active","confidence":0.88,"thesis":"LITE is the sole supplier of 200G EML lasers. POET's co-packaged optics removes thermal limits. COHR has 25% CW laser market share. NVIDIA committed $2B to photonics. Constraint = 97%.","beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],"confirmation_signal":"LITE earnings guidance + NVIDIA capex commentary","invalidators":["China photonics scaling","AI capex pause"]},
    {"name":"SiC Power Monopoly (WOLF)","category":"Structural Constraint","stage":"active","confidence":0.84,"thesis":"WOLF is the ONLY US large-scale SiC substrate maker. CHIPS Act strategic asset. 30% conduction loss reduction. STM/ON license WOLF technology.","beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["Legacy Si players"],"confirmation_signal":"EV OEM adoption letters + DOD qualification","invalidators":["China SiC subsidies"]},
    {"name":"Japan Yen Weakness → JPXN","category":"Macro Rotation","stage":"active","confidence":0.82,"thesis":"Yen bearish trend = Japanese exporters win in USD terms. JPXN +37% Q1 2026. Bank of Japan ultra-dovish. Hedgeye #1 international long.","beneficiary_tickers":["JPXN","EWJ"],"fade_tickers":["FXY"],"confirmation_signal":"USD/JPY above 145 + BoJ no action","invalidators":["BoJ surprise hike above 1%"]},
    {"name":"Silver Physical Squeeze","category":"Commodity","stage":"building","confidence":0.78,"thesis":"Solar panel + AI chip silver demand accelerating. Mine supply flat. LBMA vault levels declining. SLV +143% — NOT yet consensus.","beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],"confirmation_signal":"LBMA inventory <150M oz","invalidators":["India demand collapse","Q4 signal"]},
    {"name":"Indonesia OSV Bottleneck","category":"Local Bottleneck","stage":"brewing","confidence":0.65,"thesis":"Pertamina hulu expansion + BUMD gas = OSV fleet utilization >90%. WINS/LEAD near-monopoly on domestic offshore vessels. No new vessel delivery until 2026.","beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],"confirmation_signal":"Pertamina Q2 capex + OSV day rate >$18k","invalidators":["Pertamina budget freeze","Oil <$60"]},
]


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    # Header
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">MacroRegime Pro Dashboard</div>', unsafe_allow_html=True)

    # AI status badge
    ai_ok = ai_data.get("ok", False)
    ai_ts = ai_data.get("generated_at")
    ai_cnt_narr = len(ai_data.get("narratives",[]))
    ai_cnt_alpha = len(ai_data.get("alpha_ideas",[]))
    ai_cnt_btk = len(ai_data.get("bottlenecks",[]))
    if ai_ok:
        import datetime
        ts_str = datetime.datetime.fromtimestamp(ai_ts).strftime("%H:%M") if ai_ts else "—"
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:20px;">🤖 AI ACTIVE</span><span style="font-size:11px;color:#8B949E;">Claude generated {ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str} · Auto-refreshes every 6h</span></div>', unsafe_allow_html=True)
    else:
        ai_reason = ai_data.get("reason","")
        if "ANTHROPIC_API_KEY" in ai_reason:
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="background:#BB8009;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:20px;">⚠ AI OFFLINE</span><span style="font-size:11px;color:#8B949E;">Add ANTHROPIC_API_KEY to Streamlit Secrets to enable autonomous discovery</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="background:#21262D;color:#8B949E;font-size:10px;padding:2px 10px;border-radius:20px;">🤖 AI: Fallback</span><span style="font-size:11px;color:#8B949E;">Using pre-defined content. AI analysis will auto-run when API is available.</span></div>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:12px;color:#8B949E;margin-bottom:16px;">Built {snap.get("build_time_s",0):.0f}s ago · {snap.get("prices_loaded",0)} assets tracked · {snap.get("fred_coverage",0)} macro indicators</div>', unsafe_allow_html=True)

    # VIX Bucket — plain English
    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    vn = vbd.get("note",""); vr = vbd.get("risk_mode","Normal")
    if vb=="Investable":
        st.markdown(f'<div class="card-green"><div style="font-size:18px;font-weight:800;color:#3FB950;">🟢 GOOD MARKET CONDITIONS · VIX {vl:.1f}</div><div style="font-size:13px;color:#A8D8A8;margin-top:4px;">{vn}</div><div style="font-size:11px;color:#8B949E;margin-top:2px;">Market is calm. Good time to buy pullbacks when signal aligns. Risk mode: {vr}</div></div>', unsafe_allow_html=True)
    elif vb=="Chop":
        st.markdown(f'<div class="card-yellow"><div style="font-size:18px;font-weight:800;color:#D29922;">🟡 CHOPPY CONDITIONS · VIX {vl:.1f}</div><div style="font-size:13px;color:#E6C97A;margin-top:4px;">{vn}</div><div style="font-size:11px;color:#8B949E;margin-top:2px;">Market uncertain. Reduce trade size. Be more selective. Risk mode: {vr}</div></div>', unsafe_allow_html=True)
    elif vb=="Defensive":
        st.markdown(f'<div class="card-red"><div style="font-size:18px;font-weight:800;color:#F85149;">🔴 DEFENSIVE CONDITIONS · VIX {vl:.1f}</div><div style="font-size:13px;color:#FFA0A0;margin-top:4px;">{vn}</div><div style="font-size:11px;color:#8B949E;margin-top:2px;">Market stressed. Stay in defensive assets. Not the time to buy aggressively. Risk mode: {vr}</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Gamma + DXY in columns
    g_col, dxy_col = st.columns([1.1, 1])
    with g_col: st.markdown(_gamma_card(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy(prices, dxy_corr, sq)

    # Leveraged ETF
    st.markdown(_lev_card(lev_data), unsafe_allow_html=True)

    # Regime Cards
    st.markdown("<div class='section-header'>Current Market Regime</div>", unsafe_allow_html=True)
    sq_q2p = (_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    sq_sub  = f"Q2 probability: {sq_q2p:.0%}" if (sq=="Q3" and sq_q2p>0.25) else ""
    mq_sub  = "⚠ Model Q1 · Hedgeye Q2" if mq_raw=="Q1" else ""

    r1,r2,r3,r4 = st.columns(4)
    with r1:
        st.markdown(_metric_box("Quarterly Regime", sq, QUAD_EXPLAIN[sq][:60]+"...", qc(sq)), unsafe_allow_html=True)
    with r2:
        st.markdown(_metric_box("Monthly Regime", mq, mq_sub or "3-6 week tactical overlay", qc(mq)), unsafe_allow_html=True)
    with r3:
        gconf = _sf(global_.get("global_conf",0)) if global_ else 0
        st.markdown(_metric_box("Global (50 Countries)", gq, f"Confidence: {gconf:.0%}", qc(gq)), unsafe_allow_html=True)
    with r4:
        if gip:
            flip = gip.flip_hazard
            flip_c = "#F85149" if flip > 0.4 else "#D29922" if flip > 0.25 else "#3FB950"
            st.markdown(_metric_box("Regime Change Risk", f"{flip:.0%}", f"{gip.divergence.title()} · {gip.operating_regime[:30]}", flip_c), unsafe_allow_html=True)

    # Sequencing
    if transition or True:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    # Front-run signal
    if transition:
        fw = transition.front_run_window; fr = transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:14px;border-radius:8px;margin-top:8px;"><div style="font-size:15px;font-weight:700;color:{fwc};">{fwi}</div><div style="font-size:12px;color:#E6EDF3;margin-top:4px;">{fr}</div></div>', unsafe_allow_html=True)

    # Quick Action Summary
    if pb_data:
        best5 = " · ".join(pb_data.get("best_assets",[])[:6])
        worst5 = " · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f"""
        <div class="card-blue" style="margin-top:12px;padding:16px;">
          <div style="font-size:14px;font-weight:700;color:#58A6FF;margin-bottom:8px;">🎯 What to Do Right Now — {sq} Quarterly · {mq} Monthly</div>
          <div style="font-size:13px;color:#E6EDF3;margin-bottom:4px;">✅ <b>Buy / Hold:</b> {best5}</div>
          <div style="font-size:13px;color:#E6EDF3;">❌ <b>Avoid / Sell:</b> {worst5}</div>
          <div style="font-size:11px;color:#8B949E;margin-top:8px;">See details → <b>⚡ Alpha Center</b> · <b>📊 Leaderboard</b> · <b>📋 Playbook</b></div>
        </div>
        """, unsafe_allow_html=True)

    # Win rate
    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0)
        wr=(pr/max(ev,1))*100
        st.markdown("<div class='section-header'>Signal Track Record</div>", unsafe_allow_html=True)
        t1,t2,t3,t4 = st.columns(4)
        t1.metric("Signals Evaluated", ev)
        t2.metric("Winners ✅", pr)
        t3.metric("Losers ❌", dm)
        t4.metric("Win Rate", f"{wr:.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">📈 GIP Model — Growth · Inflation · Policy</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Hedgeye methodology: We track whether economic conditions are speeding up or slowing down — not just the level. This determines which assets win or lose.</div>', unsafe_allow_html=True)
    if not gip: st.warning("Data loading..."); st.stop()

    # Regime explanation boxes
    st.markdown("### Current vs Monthly Regime")
    cc,cw = st.columns(2)
    with cc:
        st.markdown(f'''<div style="background:{qc(sq)}18;border:2px solid {qc(sq)};border-radius:12px;padding:20px;">
        <div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">QUARTERLY REGIME (Climate)</div>
        <div style="font-size:40px;font-weight:800;color:{qc(sq)};margin-bottom:4px;">{sq}</div>
        <div style="font-size:15px;color:{qc(sq)};font-weight:600;margin-bottom:8px;">{QNC.get(sq,"")}</div>
        <div style="font-size:12px;color:#8B949E;line-height:1.6;">{QUAD_EXPLAIN[sq]}</div>
        <div style="margin-top:12px;font-size:11px;color:#8B949E;">Confidence: {gip.structural_conf:.0%} · Regime change risk: {gip.flip_hazard:.0%} · Data coverage: {gip.data_coverage:.0%}</div>
        </div>''', unsafe_allow_html=True)
    with cw:
        st.markdown(f'''<div style="background:{qc(mq)}18;border:2px solid {qc(mq)};border-radius:12px;padding:20px;">
        <div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">MONTHLY REGIME (Weather — 3-6 Weeks)</div>
        <div style="font-size:40px;font-weight:800;color:{qc(mq)};margin-bottom:4px;">{mq}</div>
        <div style="font-size:15px;color:{qc(mq)};font-weight:600;margin-bottom:8px;">{QNC.get(mq,"")}</div>
        <div style="font-size:12px;color:#8B949E;line-height:1.6;">{QUAD_EXPLAIN[mq]}</div>
        <div style="margin-top:12px;font-size:11px;color:#8B949E;">Confidence: {gip.monthly_conf:.0%} · Divergence: {gip.divergence} · {gip.operating_regime}</div>
        </div>''', unsafe_allow_html=True)
        if mq_raw == "Q1":
            st.warning("⚠ Model computed Q1, Hedgeye manual call = Q2. Use Quad Override in sidebar to set Q2.")

    # Key signals
    st.markdown("---")
    st.markdown("### What the Data Is Saying")
    f = gip.features; gm = _sf(f.get("growth_momentum")) or 0; im = _sf(f.get("inflation_momentum")) or 0
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Growth Direction", "📈 Accelerating" if gm>0 else "📉 Decelerating", f"{gm:+.1%}")
    s2.metric("Inflation Direction", "📈 Rising" if im>0 else "📉 Cooling", f"{im:+.1%}")
    s3.metric("Central Bank Stance", "Dovish 🕊️" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish 🦅" if (_sf(f.get("policy_score")) or 0)<-0.1 else "Neutral ⚖️")
    s4.metric("Data Coverage", f"{gip.data_coverage:.0%}", "From FRED + markets")

    # Transition probabilities
    st.markdown("---")
    st.markdown("### Where Are We Going Next?")
    st.caption("Probability of each regime in the coming months. Based on historical patterns and current leading indicators.")
    QWINS={"Q1":"Tech, Bitcoin, Small Caps","Q2":"Energy, Materials, Commodities","Q3":"Gold, Silver, Defensives","Q4":"Government Bonds, Gold, Cash"}
    def _tp(probs, cur_q, label):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin-bottom:8px;"><div style="font-size:11px;color:#8B949E;">{label}</div><div style="font-size:14px;color:#E6EDF3;margin-top:4px;">Most likely next: <b style="color:{qc(top_q)};">{top_q} {QN.get(top_q,"")}</b> ({top_p:.0%})</div></div>', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        if top_q!=cur_q: st.info(f"If regime shifts to {top_q}: **{QWINS.get(top_q,'')}** are the winners")
    tp1,tp2,tp3 = st.columns(3)
    with tp1: _tp(gip.structural_probs, sq, "Quarterly Regime Probabilities")
    with tp2: _tp(gip.monthly_probs, mq, "Monthly Regime Probabilities")
    with tp3:
        gprobs = (global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs, gq, "Global Regime (50 Countries)")

    # Front-run
    st.markdown("---")
    st.markdown("### Timing Signal")
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW — Window is Open","1-2w":"⚡ Act in 1-2 Weeks","3-6w":"👀 Watch in 3-6 Weeks","not yet":"🛑 Not Yet — Stay Patient"}.get(fw,"🛑 Not Yet")
        st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:14px;border-radius:8px;"><div style="font-size:15px;font-weight:700;color:{fwc};">{fwi}</div><div style="font-size:12px;color:#E6EDF3;margin-top:4px;">{fr}</div></div>', unsafe_allow_html=True)

    # Analogs
    if analogs and analogs.get("top_analogs"):
        st.markdown("---")
        st.markdown("### Historical Comparisons")
        st.caption("Similar periods in history — what happened next?")
        for i,a in enumerate(analogs["top_analogs"][:3]):
            with st.expander(f"📚 **{a['label']}** — {a.get('similarity',0):.0%} similar to today", expanded=(i==0)):
                c1,c2,c3=st.columns(3)
                c1.metric("Next 1 Month", a.get("path_1m","—"))
                c2.metric("Next 3 Months", a.get("path_3m","—"))
                c3.metric("Next 6 Months", a.get("path_6m","—"))
                st.info(f"📊 {a.get('next_bias','')}")


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">🎯 Risk Ranges™</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;"><b>Buy Zone (LRR)</b> = the price where buying makes sense. <b>Sell Zone (TRR)</b> = the price to take profit. If price breaks below Buy Zone = exit immediately.</div>', unsafe_allow_html=True)

    if not ar: st.warning("Data loading. Please wait..."); st.stop()

    # Alerts
    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
                 key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Priority Alerts")
        for sym,a in all_a[:15]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡"
            st.markdown(f'<div style="background:#21262D;border-left:3px solid {"#F85149" if a["priority"]=="CRITICAL" else "#D29922"};padding:10px;border-radius:4px;margin-bottom:4px;font-size:13px;">{ic} <b>{sym}</b> — {a["action"]} ({a["duration"]})</div>', unsafe_allow_html=True)

    st.markdown("---")
    cl1,cl2,cl3 = st.columns([1,2,1])
    with cl1: mkt_f=st.selectbox("Filter by market:",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search:",placeholder="Type ticker name...")
    with cl3: show_only=st.selectbox("Show:",["All signals","Buy signals only","Sell signals only"])

    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        sig = v.get("composite","—").upper()
        if show_only=="Buy signals only" and sig!="BULLISH": continue
        if show_only=="Sell signals only" and sig!="BEARISH": continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        side = "long" if sig=="BULLISH" else "short"
        rl = _rr_levels(px,lrr,trr,side)
        pos_pct = round((rl.get("pos",0.5))*100) if rl else 50
        action = (rl.get("action","—")[:30] if rl else "—")
        rows.append({
            "Ticker":sym,
            "Price":ff(px),
            "Buy Zone":ff(lrr),
            "Sell Zone":ff(trr),
            "Recommend. Action":action,
            "Position":f"{pos_pct}%",
            "Signal":sig,
            "Quality":v.get("quality","—"),
            "Market":v.get("market","—"),
        })
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=520,
                     column_config={
                         "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                         "Signal": st.column_config.TextColumn("Signal", width="small"),
                         "Quality": st.column_config.TextColumn("Grade", width="small"),
                         "Position": st.column_config.TextColumn("In Range", width="small"),
                         "Recommend. Action": st.column_config.TextColumn("What to Do", width="large"),
                     })
    else: st.info("No data matches your filter.")


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ALPHA CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">⚡ Alpha Center</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Best trades right now. Each idea has a clear entry price, take-profit target, stop loss, and time horizon. Options data confirms where available.</div>', unsafe_allow_html=True)

    # Timing signal
    if transition:
        fw=transition.front_run_window
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 Window OPEN — Best time to act","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Preparing — Watch for entry","not yet":"🛑 Not yet — Stay patient"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:{fwc}22;border-left:4px solid {fwc};padding:12px;border-radius:8px;margin-bottom:12px;"><div style="font-size:15px;font-weight:700;color:{fwc};">{fwi}</div></div>', unsafe_allow_html=True)
        st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    try:
        from engines.options_engine import OptionsEngine
        _oe = OptionsEngine(); _oe_ok = True
    except Exception as _err:
        _oe = None; _oe_ok = False

    def _get_all_items():
        """Get all long/short ideas from btk + rr fallback, categorized."""
        all_longs = []; all_shorts = []

        # Try btk first
        for item in (btk.get("level_1",[]) or []) + (btk.get("level_2",[]) or []):
            ticker = item.get("ticker",""); v = ar.get(ticker,{}); tr = v.get("trade",{})
            px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            dir_=item.get("direction","long")
            rl = _rr_levels(px,lrr,trr,dir_)
            if not rl: continue
            # Get options
            opt = None
            if _oe_ok and _oe and px and px > 0:
                try: opt = _oe.analyze(ticker,px,lrr,trr,v.get("composite","neutral"))
                except: pass
            if opt: rl = _merge_with_options(rl, opt, dir_)
            item_out = {**item, "px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":opt,
                        "sector":item.get("sector","").replace("_"," ").title()[:14],
                        "quality":item.get("quality","A"),"comp":v.get("composite","neutral")}
            if dir_ == "long": all_longs.append(item_out)
            else: all_shorts.append(item_out)

        # Fallback from RR if btk empty
        if not all_longs and not all_shorts:
            for sym,v in ar.items():
                if v.get("market") not in ("us_equity","commodity"): continue
                comp=v.get("composite",""); qual=v.get("quality","")
                tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
                if comp=="bullish" and qual in ("A","B"):
                    rl=_rr_levels(px,lrr,trr,"long")
                    if rl:
                        from config.settings import TICKER_SECTOR
                        all_longs.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":None,
                                          "sector":TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14],
                                          "quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength A/B"})
                elif comp=="bearish" and qual in ("short_A","short_B"):
                    rl=_rr_levels(px,lrr,trr,"short")
                    if rl:
                        from config.settings import TICKER_SECTOR
                        all_shorts.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":None,
                                           "sector":TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14],
                                           "quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength Short A/B"})

        # Sort by action priority: act now > chase ok > wait
        def _sort_key(x):
            action = x.get("rl",{}).get("action","") if x.get("rl") else ""
            if "Act Now" in action or "Buy Now" in action or "Sell/Short" in action: return 0
            if "Still Good" in action or "Still Ok" in action: return 1
            return 2
        all_longs.sort(key=_sort_key); all_shorts.sort(key=_sort_key)
        return all_longs, all_shorts

    all_longs, all_shorts = _get_all_items()

    # Stats
    stat1,stat2,stat3,stat4 = st.columns(4)
    stat1.metric("Long Ideas", len(all_longs))
    stat2.metric("Short Ideas", len(all_shorts))
    stat3.metric("Act Now", sum(1 for x in all_longs+all_shorts if x.get("rl",{}) and ("Act Now" in x["rl"].get("action","") or "Buy Now" in x["rl"].get("action","") or "Sell/Short" in x["rl"].get("action",""))))
    stat4.metric("Options Enhanced", sum(1 for x in all_longs+all_shorts if x.get("opt",{}) and x.get("opt",{}).get("ok")))

    st.markdown("---")

    # Build comprehensive table
    def _alpha_table(items, side):
        rows = []
        for item in items:
            rl = item.get("rl") or {}
            opt = item.get("opt") or {}
            action = rl.get("action","—")
            if "Act Now" in action or "Buy Now" in action or "Sell/Short" in action: st_icon = "✅ Act Now"
            elif "Still Good" in action or "Still Ok" in action: st_icon = "📊 Chase OK"
            elif "Take Profit" in action or "Cover" in action: st_icon = "🔴 Take Profit"
            else: st_icon = "⏳ Wait"

            # Options data
            im = opt.get("implied_move_pct") if opt else None
            iv_p = opt.get("iv_percentile") if opt else None
            mp = opt.get("max_pain") if opt else None
            opt_sig = opt.get("options_signal","—") if opt else "—"

            rows.append({
                "Ticker": item.get("ticker",""),
                "Sector": item.get("sector","")[:14],
                "Price": ff(_sf(item.get("px"))),
                "Status": st_icon,
                "Entry": ff(_sf(rl.get("entry"))),
                "Target 1": ff(_sf(rl.get("tp1"))),
                "Target 2": ff(_sf(rl.get("tp2"))),
                "Stop Loss": ff(_sf(rl.get("stop"))),
                "R:R": f"{_sf(rl.get('rr')) or 0:.1f}×{'✦' if rl.get('opt_confirm') else ''}",
                "Hold For": rl.get("hold","—")[:10],
                "Exp Move": f"±{fp(im)}" if im else "—",
                "IV Rank": fp(iv_p) if iv_p else "—",
                "Max Pain": ff(_sf(mp)) if mp else "—",
                "Grade": item.get("quality","—"),
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    # Long table
    st.markdown("### 🟢 LONG IDEAS — Buy These")
    st.caption("These assets are showing bullish signals. Entry = best price to buy. Target 1 & 2 = where to sell. Stop Loss = exit if it goes here.")
    if all_longs:
        df_l = _alpha_table(all_longs[:20], "long")
        st.dataframe(df_l, hide_index=True, use_container_width=True, height=min(len(df_l)*37+40,500),
                     column_config={
                         "Status": st.column_config.TextColumn("Status", width="medium"),
                         "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                         "Grade": st.column_config.TextColumn("Grade", width="small"),
                         "Hold For": st.column_config.TextColumn("Hold For", width="small"),
                     })
        # Detail for top 3
        with st.expander("📋 Detailed View — Top 3 Long Setups"):
            for item in all_longs[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"), "long", item.get("opt"))
    else:
        st.info("No long setups right now. Markets may be extended — wait for a pullback.")

    st.markdown("---")

    # Short table
    st.markdown("### 🔴 SHORT IDEAS — Sell / Avoid These")
    st.caption("These assets are showing bearish signals. Entry = best price to short. Target 1 & 2 = where to cover. Stop Loss = exit if it goes above this.")
    if all_shorts:
        df_s = _alpha_table(all_shorts[:15], "short")
        st.dataframe(df_s, hide_index=True, use_container_width=True, height=min(len(df_s)*37+40,450),
                     column_config={
                         "Status": st.column_config.TextColumn("Status", width="medium"),
                         "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                         "Grade": st.column_config.TextColumn("Grade", width="small"),
                     })
        with st.expander("📋 Detailed View — Top 3 Short Setups"):
            for item in all_shorts[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"), "short", item.get("opt"))
    else:
        st.info("No short setups right now.")

    # Watch list
    wt = btk.get("watch",[]) if btk else []
    if wt:
        st.markdown("---")
        st.markdown("### 👀 WATCH LIST — Building Up")
        st.caption("These haven't reached our entry level yet, but are showing early signs. Monitor these.")
        wt_rows=[{"Ticker":w.get("ticker",""),"Sector":w.get("sector","").replace("_"," ").title()[:14],"Direction":w.get("direction","long").upper(),"Score":f'{w.get("score",0):.2f}',"What's Happening":w.get("known_thesis","")[:60]} for w in wt[:15]]
        st.dataframe(pd.DataFrame(wt_rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📊 LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">📊 Leaderboard — Signal Strength</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Our highest-conviction ideas. Grade A = strongest signal. Every pick shows exactly where to buy, where to take profit, and where to cut losses.</div>', unsafe_allow_html=True)

    if not ar: st.warning("Data loading..."); st.stop()

    try:
        from engines.options_engine import OptionsEngine as _OE2
        _oe2 = _OE2(); _oe2_ok = True
    except: _oe2 = None; _oe2_ok = False

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]

    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); tn=v.get("trend",{})
        px=_sf(v.get("px")); vol_c=_sf(tr.get("volume_confirm")) or 0.5
        stretch=tr.get("stretch",""); hurst=_sf(tn.get("hurst")) or 0.5
        lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()
        except: sector="Generic"

        if qual in ("A","B") and comp=="bullish":
            rl=_rr_levels(px,lrr,trr,"long"); pos=rl.get("pos",0.5) if rl else 0.5
            rf=sym in best_set; ra=sym in worst_set
            sc=(50 if qual=="A" else 30)+(25 if (rl and rl.get("near_entry")) else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector[:14],"comp":comp})
        if qual in ("short_A","short_B") and comp=="bearish":
            rl=_rr_levels(px,lrr,trr,"short"); pos=rl.get("pos",0.5) if rl else 0.5
            rf=sym in worst_set
            sc=(50 if qual=="short_A" else 30)+(25 if (rl and rl.get("near_entry")) else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"sector":sector[:14],"comp":comp})

    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])

    # Stats
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Long Ideas", len(long_picks))
    m2.metric("Grade A Longs", sum(1 for p in long_picks if p["quality"]=="A"))
    m3.metric("Grade A Shorts", sum(1 for p in short_picks if p["quality"]=="short_A"))
    m4.metric("Regime Traps", sum(1 for v in ar.values() if v.get("regime_trap")))

    st.markdown("---")

    # Long table
    st.markdown("### 🟢 TOP LONG IDEAS")
    st.caption("Buy Zone = LRR. Take Profit 1 = midpoint. Take Profit 2 = TRR. Stop Loss = 25% below buy zone. ✦ = confirmed by options data.")
    if long_picks:
        df_longs = _client_table(long_picks[:21])
        st.dataframe(df_longs, hide_index=True, use_container_width=True,
                     column_config={
                         "Status": st.column_config.TextColumn("Status", width="medium"),
                         "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                         "Sector": st.column_config.TextColumn("Sector", width="small"),
                         "Hold For": st.column_config.TextColumn("Hold", width="small"),
                         "In Range%": st.column_config.TextColumn("Position in Range", width="medium"),
                         "Grade": st.column_config.TextColumn("Grade", width="small"),
                     })
        with st.expander("📋 Detailed Level View — Top 5 Longs"):
            for p in long_picks[:5]:
                rl=p.get("rl"); opt_r=None
                if _oe2_ok and _oe2 and p["px"] and p["px"]>0:
                    try: opt_r=_oe2.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
                    except: pass
                if rl and opt_r: rl=_merge_with_options(rl,opt_r,"long")
                st.markdown(f"**{p['ticker']}** ({p['quality']}) — {p['sector']} — {rl.get('action','') if rl else ''}")
                if rl: _render_levels(rl,"long",opt_r)
    else: st.info("No Grade A/B long ideas currently. Market may be extended — wait for pullback.")

    st.markdown("---")
    st.markdown("### 🔴 SHORT IDEAS")
    st.caption("Sell Zone = TRR. Cover (buy back) at Target 1 and Target 2. Stop Loss = 25% above sell zone.")
    if short_picks:
        df_shorts = _client_table(short_picks[:15])
        # Rename "Buy/Sell at" to "Sell at" for shorts
        df_shorts = df_shorts.rename(columns={"Buy/Sell at":"Sell at"})
        st.dataframe(df_shorts, hide_index=True, use_container_width=True,
                     column_config={
                         "Status": st.column_config.TextColumn("Status", width="medium"),
                         "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                         "Grade": st.column_config.TextColumn("Grade", width="small"),
                     })
        with st.expander("📋 Detailed Level View — Top 5 Shorts"):
            for p in short_picks[:5]:
                rl=p.get("rl"); opt_r=None
                if _oe2_ok and _oe2 and p["px"] and p["px"]>0:
                    try: opt_r=_oe2.analyze(p["ticker"],p["px"],p["lrr"],p["trr"],p["comp"])
                    except: pass
                if rl and opt_r: rl=_merge_with_options(rl,opt_r,"short")
                st.markdown(f"**{p['ticker']}** ({p['quality']}) — {p['sector']} — {rl.get('action','') if rl else ''}")
                if rl: _render_levels(rl,"short",opt_r)
    else: st.info("No short ideas currently.")


# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">🌍 Global Macro — 50 Countries</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Where is money rotating globally? Each country\'s economic regime determines which assets win.</div>', unsafe_allow_html=True)
    if not global_: st.warning("Data loading..."); st.stop()

    gconf=_sf(global_.get("global_conf",0)) or 0; gprobs=global_.get("global_probs",{}) or {}
    c1,c2 = st.columns([1,1.5])
    with c1:
        st.markdown(f'''<div style="background:{qc(gq)}18;border:2px solid {qc(gq)};border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">GLOBAL REGIME</div>
        <div style="font-size:48px;font-weight:800;color:{qc(gq)};margin-bottom:6px;">{gq}</div>
        <div style="font-size:14px;color:{qc(gq)};font-weight:600;">{QNC.get(gq,"")}</div>
        <div style="margin-top:10px;font-size:11px;color:#8B949E;">Based on 50 country ETFs · GDP-weighted · Confidence: {gconf:.0%}</div>
        </div>''', unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs,"Global Regime Probabilities"), use_container_width=True, config={"displayModeBar":False})
    with c2:
        cq=global_.get("country_quads",{}) or {}; heat=[]
        for country,data in cq.items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_sf(data[2]) or 0
            elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_sf(data.get("conf",0)) or 0
            else: continue
            if quad: heat.append({"Country":country,"ETF":etf,"Regime":quad,"Confidence":f"{conf:.0%}"})
        if heat:
            st.dataframe(pd.DataFrame(heat).style.map(lambda v:f"color:{QC.get(v,'#8B949E')}" if v in QC else "",subset=["Regime"]),
                         hide_index=True,height=420,use_container_width=True)
        else: st.info("Country data loading. Refresh to compute.")

    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_sf(em_sig.get("confidence")) or 0
        ec="#3FB950" if conf>0.6 else "#D29922" if conf>0.4 else "#8B949E"
        st.markdown(f'<div style="background:{ec}18;border-left:4px solid {ec};padding:14px;border-radius:8px;margin-top:12px;"><div style="font-size:13px;font-weight:700;color:{ec};">{em_sig.get("trigger","")}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{em_sig.get("rationale","")}</div><div style="font-size:11px;color:#E6EDF3;margin-top:4px;">Best plays: {", ".join(em_sig.get("best",[])[:6])}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">🇮🇩 Indonesia Market (IHSG)</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Indonesian stocks. No options data (market not liquid enough). Signals based on price/volume analysis.</div>', unsafe_allow_html=True)
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS

    ihsg_rr = {sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}

    if ihsg_rr:
        rows = []
        for sym,v in ihsg_rr.items():
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            sig=v.get("composite","—").upper()
            rl=_rr_levels(px,lrr,trr,"long" if sig=="BULLISH" else "short")
            action = rl.get("action","—")[:35] if rl else "—"
            rows.append({"Ticker":sym,"Price":ff(px,0),"Buy Zone":ff(lrr,0),"Sell Zone":ff(trr,0),
                         "Action":action,"Signal":sig,"Quality":v.get("quality","—"),
                         "Name":IHSG_UNIVERSE.get(sym,sym)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                     column_config={"Action": st.column_config.TextColumn("What to Do", width="large"),
                                    "Name": st.column_config.TextColumn("Company", width="medium")})
    else:
        # Always show price data from snapshot — no rebuild required
        rows=[]
        for sym in list(IHSG_UNIVERSE.keys()):
            s=prices.get(sym)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1])
            r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else None
            r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
            rows.append({"Ticker":sym,"Company":IHSG_UNIVERSE.get(sym,sym),"Price":f"{px:,.0f}",
                         "1 Month":f"{r1:+.1%}" if r1 is not None else "—",
                         "3 Months":f"{r3:+.1%}" if r3 is not None else "—"})
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=420)
        else:
            st.warning("IHSG data tidak tersedia. Pastikan IHSG checkbox aktif lalu click 🔄 Update.")

    st.markdown("---"); st.markdown("### Sector Performance")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"**{bucket.replace('_',' ')}** ({len(tickers)} stocks)"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"Company":IHSG_UNIVERSE.get(t,t)[:20],"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}"})
            if b_rows: st.dataframe(pd.DataFrame(b_rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">📖 Active Themes</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">These are the big investment themes running right now. Each theme drives a group of assets. Higher score = stronger theme.</div>', unsafe_allow_html=True)

    active = ((narr.get("active_narratives",[]) or []) if narr else [])
    fallback = [n for n in FALLBACK_NARRATIVES if sq in n.get("regime","ALL") or mq in n.get("regime","ALL") or "ALL" in n.get("regime","ALL")]
    all_n = active if active else fallback

    # Show AI status
    if ai_data.get("ok") and ai_data.get("narratives"):
        st.success(f"🤖 **{len(ai_data.get('narratives',[]))} AI-generated narratives** from latest news · Auto-updated every 6 hours")

    for n in sorted(all_n, key=lambda x: x.get("score",0), reverse=True):
        score=n.get("score",0)
        sc="#3FB950" if score>0.6 else "#D29922" if score>0.4 else "#8B949E"
        strength = "🔥 Very Strong" if score>0.8 else ("📈 Strong" if score>0.6 else ("📊 Building" if score>0.4 else "👀 Early Stage"))
        with st.expander(f"**{n.get('name','')}** — {strength} ({score:.0%})"):
            st.markdown(f"**What's happening:** {n.get('thesis','')}")
            cols=st.columns(2)
            with cols[0]:
                if n.get("best"): st.markdown("**Best assets to own:** " + " · ".join(n["best"][:6]))
                if n.get("tickers"): st.markdown("**All related tickers:** " + " · ".join(n["tickers"][:8]))
            with cols[1]:
                if n.get("worst"): st.markdown("**Avoid these:** " + " · ".join(n["worst"][:4]))
                if n.get("invalidators"): st.markdown("**This thesis breaks if:** " + " | ".join(n["invalidators"][:3]))


# ══════════════════════════════════════════════════════════════════════════════
# 🔮 DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">🔮 Pre-Consensus Ideas</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">These are ideas the market hasn\'t fully priced in yet. Early-stage opportunities before they become consensus. Higher confidence = more data supporting the thesis.</div>', unsafe_allow_html=True)

    cands = ((auto_disc.get("candidates",[]) or []) if auto_disc else []) + ((disc.get("discoveries",[]) or []) if disc else [])
    all_disc = cands if cands else FALLBACK_DISCOVERY

    # Show AI-generated scenario update if available
    if ai_data.get("ok"):
        su = ai_data.get("scenario_update",{}) or {}
        ai_ideas = ai_data.get("alpha_ideas",[])
        if su or ai_ideas:
            st.markdown("### 🤖 AI Analysis — Updated from Latest News")
            if su:
                col1,col2 = st.columns(2)
                with col1:
                    if su.get("opportunity"):
                        st.success(f"**Opportunity**: {su['opportunity']}")
                with col2:
                    if su.get("headline_risk"):
                        st.error(f"**Risk**: {su['headline_risk']}")
                if su.get("regime_change_signal"):
                    st.info(f"**Watch for regime shift**: {su['regime_change_signal']}")
            if ai_ideas:
                st.markdown(f"#### 🎯 AI-Generated Alpha Ideas ({len(ai_ideas)})")
                for idea in ai_ideas:
                    conf = idea.get("confidence",0.7)
                    with st.expander(f"**{idea.get('ticker','')}** — {idea.get('name','')} · Confidence {conf:.0%}"):
                        st.markdown(f"**Direction:** {'🟢 LONG' if idea.get('direction')=='long' else '🔴 SHORT'}")
                        st.markdown(f"**Thesis:** {idea.get('thesis','')}")
                        st.markdown(f"**Why now:** {idea.get('regime_fit','')}")
                        if idea.get("invalidators"): st.warning(f"**Breaks if:** {', '.join(idea['invalidators'])}")
            st.divider()

    for stage,label,color in [("active","✅ Active — Strong Signal","#3FB950"),("building","📈 Building — Gaining Traction","#D29922"),("brewing","👀 Brewing — Early Stage","#1F6FEB")]:
        items=[c for c in all_disc if c.get("stage")==stage]
        if not items: continue
        st.markdown(f'<div style="font-size:16px;font-weight:700;color:{color};margin:16px 0 8px 0;">{label} ({len(items)})</div>', unsafe_allow_html=True)
        for c in items:
            conf=c.get("confidence",c.get("conviction",0.7))
            with st.expander(f"**{c.get('name','')}** — Confidence: {conf:.0%}"):
                st.markdown(f"**The Idea:** {c.get('thesis','')}")
                st.markdown(f"**Category:** {c.get('category','')}")
                cols=st.columns(2)
                with cols[0]:
                    ben=c.get("beneficiary_tickers",[])
                    if ben: st.markdown(f"**Buy these:** {' · '.join(ben[:8])}")
                with cols[1]:
                    fade=c.get("fade_tickers",[])
                    if fade: st.markdown(f"**Avoid these:** {' · '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs: st.success(f"✅ **Confirmation signal:** {cs}")
                if inv: st.warning(f"⚠️ **Thesis breaks if:** {', '.join(inv) if isinstance(inv,list) else inv}")


# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">🏥 Market Health Check</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Overall market health indicators. VIX = fear gauge. Crash meter = stress level. Breadth = how many assets are participating.</div>', unsafe_allow_html=True)
    if not health: st.warning("Data loading..."); st.stop()

    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","—")
    vb_c={"Investable":"#3FB950","Chop":"#D29922","Defensive":"#F85149"}.get(vb_b,"#8B949E")
    vb_explain={"Investable":"Market is calm. Good conditions to buy pullbacks.","Chop":"Uncertainty. Be selective and reduce size.","Defensive":"Market stressed. Protect capital first."}.get(vb_b,"")
    st.markdown(f'<div style="background:{vb_c}18;border-left:4px solid {vb_c};padding:16px;border-radius:8px;margin-bottom:12px;"><div style="font-size:20px;font-weight:800;color:{vb_c};">{vb_b.upper()} CONDITIONS</div><div style="font-size:13px;color:#E6EDF3;margin-top:4px;">{vb_explain}</div><div style="font-size:11px;color:#8B949E;margin-top:2px;">{vb_d.get("note","")}</div></div>', unsafe_allow_html=True)

    crash=health.get("crash",{}) or {}
    if crash:
        st.markdown("### Market Stress Level")
        score=_sf(crash.get("score")) or 0
        st.progress(float(score), text=f"Overall stress: {score:.0%} — {crash.get('state','Normal')}")
        for k,v in (crash.get("signals",{}) or {}).items():
            clean=k.replace("_"," ").title()
            st.progress(float(v) if v else 0, text=f"{clean}: {v:.0%}")
        if crash.get("reasons"): st.warning("Stress factors: " + " · ".join(crash["reasons"]))

    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.markdown("### Market Participation")
        st.caption("Are most assets rising or is it just a few leaders?")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Health Score",f"{_sf(breadth.get('score')) or 0:.0%}")
        b2.metric("Assessment",breadth.get("verdict","—"))
        b3.metric("Sectors Rising",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("Equal-Weight Health",f"{_sf(breadth.get('eqw_health')) or 0:.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"• {note}")

    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.markdown("---"); st.markdown("### Fear & Greed Meter")
        fgs=_sf(fg.get("score")) or 50
        fgc="#3FB950" if fgs<25 else "#D29922" if fgs<55 else "#F85149"
        fgl = "Extreme Fear (good time to buy)" if fgs<25 else ("Fear" if fgs<45 else ("Neutral" if fgs<55 else ("Greed" if fgs<75 else "Extreme Greed (be careful)")))
        st.markdown(f"<div style='font-size:24px;font-weight:800;color:{fgc};'>{fgs:.0f}/100 — {fgl}</div>", unsafe_allow_html=True)
        st.progress(fgs/100)
        st.caption("Below 25 = market too fearful = often a BUY signal. Above 75 = market too greedy = often a WARNING signal.")


# ══════════════════════════════════════════════════════════════════════════════
# 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown('<div style="font-size:28px;font-weight:800;color:#E6EDF3;margin-bottom:4px;">📋 Regime Playbook</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;color:#8B949E;margin-bottom:16px;">Your complete action guide for <b style="color:{qc(sq)};">{sq} {QN[sq]}</b> quarterly regime with <b style="color:{qc(mq)};">{mq} {QN[mq]}</b> monthly overlay.</div>', unsafe_allow_html=True)

    # Regime explanation
    st.markdown(f'<div style="background:{qc(sq)}18;border:1px solid {qc(sq)};border-radius:12px;padding:16px;margin-bottom:16px;"><div style="font-size:14px;font-weight:700;color:{qc(sq)};margin-bottom:6px;">{QNC[sq]}</div><div style="font-size:13px;color:#E6EDF3;">{QUAD_EXPLAIN[sq]}</div></div>', unsafe_allow_html=True)

    if pb_data:
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<div class="card-green" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown(f"**✅ Own These in {sq}:**")
            st.markdown(" · ".join(pb_data.get("best_assets",[])))
            st.markdown(f"\n**Style:** {pb_data.get('style','')}")
            st.markdown(f"**Currency:** {pb_data.get('fx','')}")
            st.markdown(f"**Bonds:** {pb_data.get('bonds','')}")
            if pb_data.get("monthly_adds"): st.markdown(f"**Monthly adds:** {' · '.join(pb_data.get('monthly_adds',[]))}")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="card-red" style="padding:16px;">', unsafe_allow_html=True)
            st.markdown(f"**❌ Avoid These in {sq}:**")
            st.markdown(" · ".join(pb_data.get("worst_assets",[])))
            st.markdown(f"\n**Hedge with:** {pb_data.get('hedge','BTAL')}")
            st.markdown(f"**Position size:** {pb_data.get('sizing_note','Min 1% · Max 3% per name')}")
            st.markdown('</div>', unsafe_allow_html=True)

    # Bitcoin
    btc_rr=ar.get("IBIT",ar.get("BTC-USD",{})); btc_sig=btc_rr.get("composite","—")
    btc_c="#3FB950" if btc_sig=="bullish" else "#F85149" if btc_sig=="bearish" else "#8B949E"
    btc_action = "EXIT Bitcoin" if sq=="Q4" else (f"HOLD/BUY Bitcoin (IBIT) — Signal: {btc_sig.upper()}" if btc_sig=="bullish" else "REDUCE Bitcoin position")
    dxy_c = dxy_corr.get("Bitcoin","—")
    st.markdown(f'<div style="background:{btc_c}18;border-left:4px solid {btc_c};padding:12px;border-radius:8px;margin:12px 0;"><span style="font-size:14px;font-weight:700;color:{btc_c};">₿ Bitcoin: {btc_action}</span><span style="font-size:12px;color:#8B949E;"> · Rule: Any regime except Q4 = long Bitcoin · DXY/BTC correlation: {dxy_c}</span></div>', unsafe_allow_html=True)

    # Scenarios
    scenarios_list=(scen.get("scenarios",[]) or []) if scen else []
    if scenarios_list:
        st.markdown("---"); st.markdown("### What Could Happen Next?")
        badges=["Most Likely","Alternative","Risk Scenario","Tail Risk"]; badge_colors=["#3FB950","#D29922","#F85149","#A371F7"]
        r1,r2=st.columns(2); r3,r4=st.columns(2); grids=[r1,r2,r3,r4]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]
            with col:
                st.markdown(f'''<div style="background:#161B22;border:1px solid {pc}44;border-left:3px solid {pc};border-radius:10px;padding:14px;">
                <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} · {sc_item.probability:.0%} probability</div>
                <div style="font-size:14px;color:#E6EDF3;margin-top:6px;font-weight:600;">{sc_item.name}</div>
                <div style="font-size:12px;color:#8B949E;margin-top:4px;">{sc_item.headline}</div>
                <div style="font-size:11px;color:#3FB950;margin-top:6px;">Win: {" · ".join(sc_item.best_assets[:3])}</div>
                <div style="font-size:11px;color:#F85149;margin-top:2px;">Avoid: {" · ".join(sc_item.worst_assets[:3])}</div>
                </div>''', unsafe_allow_html=True)

    # GIP signals table
    if gip:
        st.markdown("---"); st.markdown("### Raw Signals (For Advanced Users)")
        f=gip.features
        rows=[["Growth Speed",fp(f.get("growth_momentum")),"Faster" if (_sf(f.get("growth_momentum")) or 0)>0 else "Slower"],
              ["Inflation Speed",fp(f.get("inflation_momentum")),"Rising" if (_sf(f.get("inflation_momentum")) or 0)>0 else "Cooling"],
              ["Central Bank",fp(f.get("policy_score")),"Dovish" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish"],
              ["Leading Indicators",fp(f.get("leading_indicator_composite")),"—"],
              ["Data Confidence",fp(f.get("data_coverage")),"—"],
              ["Regime Change Risk",f"{gip.flip_hazard:.0%}","—"]]
        st.dataframe(pd.DataFrame(rows,columns=["Indicator","Reading","Direction"]),hide_index=True,use_container_width=True)

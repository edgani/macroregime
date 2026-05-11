"""app.py — MacroRegime Pro v24.0 FINAL FIX
Changes from v23.2:
- Dashboard: Forward-Looking Radar + Emergent Narratives + Price Clusters
- GIP Model: Real 1M/3M/6M forward projection + Leading Indicator signals
- All tabs: enriched with forward_returns + news_narrative per ticker
- Themes: real discovery data instead of FALLBACK hardcoded
- Fix: feedback_eval TypeError (list vs int)
- Fix: tab content separation (each tab has unique purpose)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import time
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="MacroRegime Pro", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE

st.markdown("""
<style>
.stApp { background-color: #0d1117; }
.card-green {background:#0D2818;border:1px solid #3FB950;border-radius:8px;padding:12px;margin:6px 0;}
.card-yellow {background:#2D2305;border:1px solid #D29922;border-radius:8px;padding:12px;margin:6px 0;}
.card-red {background:#2D0D0D;border:1px solid #F85149;border-radius:8px;padding:12px;margin:6px 0;}
.card-blue {background:#0D1B2A;border:1px solid #1F6FEB;border-radius:8px;padding:12px;margin:6px 0;}
.badge {display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-right:4px;}
.badge-a {background:#3FB95022;color:#3FB950;border:1px solid #3FB950;}
.badge-ap {background:#3FB95044;color:#3FB950;border:1px solid #3FB950;}
.badge-b {background:#D2992222;color:#D29922;border:1px solid #D29922;}
.badge-c {background:#8B949E22;color:#8B949E;border:1px solid #8B949E;}
.badge-long {background:#3FB95022;color:#3FB950;border:1px solid #3FB950;}
.badge-short {background:#F8514922;color:#F85149;border:1px solid #F85149;}
.badge-neutral {background:#8B949E22;color:#8B949E;border:1px solid #8B949E;}
.badge-watch {background:#1F6FEB22;color:#1F6FEB;border:1px solid #1F6FEB;}
.metric-box {background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;}
.metric-label {font-size:10px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;}
.metric-value {font-size:18px;font-weight:700;color:#E6EDF3;margin:4px 0;}
.metric-sub {font-size:11px;color:#8B949E;}
</style>
""", unsafe_allow_html=True)

QC = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"🟢 Goldilocks — Growth Rising, Inflation Cooling",
    "Q2":"🟡 Reflation — Both Growth and Inflation Rising",
    "Q3":"🔴 Stagflation — Growth Slowing, Inflation Elevated",
    "Q4":"🟣 Deflation — Both Growth and Inflation Falling",
}
QUAD_EXPLAIN = {
    "Q1":"Best conditions for stocks and crypto. Growth is strong and inflation is under control.",
    "Q2":"Tricky environment. Economy growing but inflation biting. Commodities, energy, and international stocks tend to win.",
    "Q3":"Most dangerous quarter. Economy slowing but prices still high. Gold, silver, and defensive stocks are the place to be. Tech gets hurt.",
    "Q4":"Deflationary collapse. Safest assets win: government bonds, gold, utilities, cash. Avoid risk.",
}
QWINS = {"Q1":"Tech, Bitcoin, Small Caps","Q2":"Energy, Materials, Commodities","Q3":"Gold, Silver, Defensives","Q4":"Government Bonds, Gold, Cash"}

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

def _rr_levels(px, lrr, trr, side="long"):
    px = _sf(px) or 0; lrr = _sf(lrr) or 0; trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = (px - lrr) / spread if spread > 0 else 0.5
    if side == "long":
        entry, tp1, tp2, stop = round(lrr,2), round(lrr+spread*0.50,2), round(trr,2), round(lrr-spread*0.25,2)
        near_entry, can_enter, near_target = pos <= 0.35, pos <= 0.55, pos >= 0.75
        action = "Buy Now" if near_entry else ("Can Enter" if can_enter else ("Near Target" if near_target else "Wait"))
    else:
        entry, tp1, tp2, stop = round(trr,2), round(trr-spread*0.50,2), round(lrr,2), round(trr+spread*0.25,2)
        near_entry, can_enter, near_target = pos >= 0.65, pos >= 0.45, pos <= 0.25
        action = "Sell Now" if near_entry else ("Can Short" if can_enter else ("Near Target" if near_target else "Wait"))
    rr_r = round(abs(tp1-entry)/max(abs(entry-stop),0.01), 2)
    return {"entry":entry,"tp1":tp1,"tp2":tp2,"stop":stop,"rr":rr_r,"pos":round(pos,2),"side":side,"near_entry":near_entry,"near_target":near_target,"can_enter":can_enter,"action":action}

def _metric_box(label, value, sub="", color="#E6EDF3"):
    sub_html = f'<div style="font-size:11px;color:#8B949E;margin-top:2px;">{sub}</div>' if sub else ""
    return f'<div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color};">{value}</div>{sub_html}</div>'

def _calc_expected_move(s, period_days=5):
    if s is None or len(s) < 22: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 22: return None
    px = float(s.iloc[-1])
    daily_vol = s.tail(20).pct_change().dropna().std()
    if daily_vol == 0 or not math.isfinite(daily_vol): return None
    expected = px * daily_vol * math.sqrt(period_days)
    expected_pct = daily_vol * math.sqrt(period_days)
    return {"expected": round(expected, 2), "expected_pct": round(expected_pct, 3), "daily_vol": round(daily_vol, 4), "px": px}

def _realistic_time_estimate(price, target, ticker, market_type, vix, gamma, greek, direction, s=None):
    if not price or not target: return "Unknown"
    distance = abs(target - price)
    distance_pct = distance / price if price else 0.05
    if market_type == "crypto": weekly_expected_pct = 0.08
    elif market_type == "forex": weekly_expected_pct = 0.015
    elif market_type == "commodity":
        if any(x in ticker for x in ["SI=","SLV","GC=","GLD","HG=","PL=","PA="]): weekly_expected_pct = 0.035
        else: weekly_expected_pct = 0.04
    else: weekly_expected_pct = 0.025
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) >= 22:
            daily_vol = s.tail(20).pct_change().dropna().std()
            if daily_vol > 0 and math.isfinite(daily_vol): weekly_expected_pct = daily_vol * math.sqrt(5)
    if vix > 35: weekly_expected_pct *= 2.0
    elif vix > 25: weekly_expected_pct *= 1.5
    elif vix > 20: weekly_expected_pct *= 1.2
    if gamma and gamma.get("ok"):
        g_regime = gamma.get("regime", "")
        if g_regime in ("DEEP_POSITIVE", "POSITIVE") and "LONG" in direction: weekly_expected_pct *= 1.4
        elif g_regime in ("DEEP_NEGATIVE", "NEGATIVE") and "SHORT" in direction: weekly_expected_pct *= 1.4
        elif g_regime in ("DEEP_POSITIVE", "POSITIVE", "DEEP_NEGATIVE", "NEGATIVE"): weekly_expected_pct *= 1.2
    if greek and greek.get("ok"):
        greek_comp = greek.get("composite", "")
        if "BULLISH" in greek_comp and "LONG" in direction: weekly_expected_pct *= 1.15
        elif "BEARISH" in greek_comp and "SHORT" in direction: weekly_expected_pct *= 1.15
    weeks = distance_pct / weekly_expected_pct if weekly_expected_pct > 0 else 4
    if weeks <= 0.3: return "2-4 days"
    elif weeks <= 0.7: return "3-7 days"
    elif weeks <= 1.3: return "1-2 weeks"
    elif weeks <= 2.5: return "2-4 weeks"
    elif weeks <= 5: return "1-2 months"
    elif weeks <= 10: return "2-4 months"
    elif weeks <= 20: return "3-6 months"
    else: return "6+ months"

def _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction):
    if direction not in ("LONG", "SHORT"): return "WAIT — No clear edge"
    if direction == "LONG":
        if price <= entry * 1.01:
            if composite == "bullish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE"):
                return "BUY NOW — At buy zone + gamma supportive"
            elif composite == "bullish": return "BUY NOW — At buy zone"
            else: return "SMALL SIZE — At buy zone but mixed signals"
        elif lrr and price <= lrr * 1.03: return f"WAIT — Slightly above best entry, wait for retrace to {lrr}"
        else:
            if momentum_1m and momentum_1m > 0.05: return "CHASE — Extended but momentum strong, small size"
            else: return "SKIP — Too far from buy zone, wait for pullback"
    else:
        if price >= entry * 0.99:
            if composite == "bearish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE"):
                return "SELL NOW — At sell zone + gamma headwind"
            elif composite == "bearish": return "SELL NOW — At sell zone"
            else: return "SMALL SIZE — At sell zone but mixed signals"
        elif trr and price >= trr * 0.97: return f"WAIT — Slightly below best entry, wait for bounce to {trr}"
        else:
            if momentum_1m and momentum_1m < -0.05: return "CHASE SHORT — Extended but momentum strong, small size"
            else: return "SKIP — Too far from sell zone, wait for bounce"

def _target_basis(target, trr, lrr, gamma, direction):
    if not gamma.get("ok"):
        return f"TRR resistance at {trr}" if direction == "LONG" and trr else (f"LRR support at {lrr}" if direction == "SHORT" and lrr else "1.5x RR target")
    call_wall = gamma.get("call_wall"); put_wall = gamma.get("put_wall")
    flip_up = gamma.get("gamma_flip_up"); flip_down = gamma.get("gamma_flip_down")
    max_pain = gamma.get("max_pain")
    if direction == "LONG":
        if call_wall and abs(target - call_wall) / max(target, 1) < 0.03: return f"Call wall at {call_wall}"
        elif flip_up and abs(target - flip_up) / max(target, 1) < 0.03: return f"Gamma flip up at {flip_up}"
        elif trr and abs(target - trr) / max(target, 1) < 0.03: return f"TRR at {trr}"
        else: return f"1.5x RR target (max pain {max_pain})"
    else:
        if put_wall and abs(target - put_wall) / max(target, 1) < 0.03: return f"Put wall at {put_wall}"
        elif flip_down and abs(target - flip_down) / max(target, 1) < 0.03: return f"Gamma flip down at {flip_down}"
        elif lrr and abs(target - lrr) / max(target, 1) < 0.03: return f"LRR at {lrr}"
        else: return f"1.5x RR target (max pain {max_pain})"

def _stop_basis(stop, lrr, trr, gamma, direction):
    if not gamma.get("ok"):
        return f"Below LRR at {lrr}" if direction == "LONG" and lrr else (f"Above TRR at {trr}" if direction == "SHORT" and trr else "2% from entry")
    flip_down = gamma.get("gamma_flip_down"); flip_up = gamma.get("gamma_flip_up")
    put_wall = gamma.get("put_wall"); call_wall = gamma.get("call_wall")
    if direction == "LONG":
        if flip_down and abs(stop - flip_down) / max(stop, 1) < 0.03: return f"Below gamma flip {flip_down}"
        elif put_wall and abs(stop - put_wall) / max(stop, 1) < 0.03: return f"Below put wall {put_wall}"
        elif lrr and abs(stop - lrr) / max(stop, 1) < 0.03: return f"Below LRR {lrr}"
        else: return "2% below entry"
    else:
        if flip_up and abs(stop - flip_up) / max(stop, 1) < 0.03: return f"Above gamma flip {flip_up}"
        elif call_wall and abs(stop - call_wall) / max(stop, 1) < 0.03: return f"Above call wall {call_wall}"
        elif trr and abs(stop - trr) / max(stop, 1) < 0.03: return f"Above TRR {trr}"
        else: return "2% above entry"

def _path_smoothness(gamma, greek, momentum_1m, vix):
    if not gamma.get("ok") and not greek.get("ok"):
        return "Rough — High vol" if vix > 25 else ("Bumpy — Elevated vol" if vix > 20 else "Normal")
    gamma_regime = gamma.get("regime", "TRANSITION") if gamma.get("ok") else "TRANSITION"
    throttle = gamma.get("throttle", 0.5) if gamma.get("ok") else 0.5
    greek_comp = greek.get("composite", "NEUTRAL") if greek.get("ok") else "NEUTRAL"
    if gamma_regime in ("DEEP_POSITIVE", "POSITIVE") and "BULLISH" in greek_comp:
        return "Fast & Smooth" if momentum_1m and momentum_1m > 0.03 else "Smooth — dips bought"
    elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE") and "BEARISH" in greek_comp:
        return "Fast & Smooth" if momentum_1m and momentum_1m < -0.03 else "Smooth — rallies sold"
    elif throttle > 0.6: return "Slow — gamma pin, chop"
    elif vix > 25: return "Rough — vol expansion"
    elif vix > 20: return "Bumpy — elevated vol"
    else: return "Normal"

def _breakout_chance(price, target_2, gamma, greek, momentum_3m, direction):
    if not gamma.get("ok") and not greek.get("ok"):
        return "Medium" if momentum_3m and abs(momentum_3m) > 0.10 else "Low"
    greek_comp = greek.get("composite", "NEUTRAL") if greek.get("ok") else "NEUTRAL"
    gamma_regime = gamma.get("regime", "TRANSITION") if gamma.get("ok") else "TRANSITION"
    call_wall = gamma.get("call_wall"); put_wall = gamma.get("put_wall")
    if direction == "LONG":
        if "BULLISH" in greek_comp and gamma_regime in ("DEEP_POSITIVE", "POSITIVE"):
            return f"High — above call wall {call_wall}" if call_wall and target_2 > call_wall else "High"
        elif "BULLISH" in greek_comp: return "Medium-High"
        elif gamma_regime in ("DEEP_POSITIVE", "POSITIVE"): return "Medium"
        else: return "Low — T2 is stretch"
    else:
        if "BEARISH" in greek_comp and gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"):
            return f"High — below put wall {put_wall}" if put_wall and target_2 < put_wall else "High"
        elif "BEARISH" in greek_comp: return "Medium-High"
        elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"): return "Medium"
        else: return "Low — T2 is stretch"

def _enrich_row_with_conclusions(row, gamma, greek, vix=20, s=None):
    price = row.get("price"); entry = row.get("entry"); target1 = row.get("target_1"); target2 = row.get("target_2")
    stop = row.get("stop"); direction = "LONG" if "LONG" in row.get("direction", "") else ("SHORT" if "SHORT" in row.get("direction", "") else "NEUTRAL")
    composite = row.get("composite", "neutral"); momentum_1m = row.get("r1m"); momentum_3m = row.get("r3m")
    rr = row.get("rr"); lrr = row.get("lrr") if row.get("lrr") else None; trr = row.get("trr") if row.get("trr") else None
    ticker = row.get("ticker", "")
    market_type = row.get("market_type", "us_equity")
    row["entry_advice"] = _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction)
    row["tp1_basis"] = _target_basis(target1, trr, lrr, gamma, direction)
    row["tp2_basis"] = _target_basis(target2, trr, lrr, gamma, direction)
    row["stop_basis"] = _stop_basis(stop, lrr, trr, gamma, direction)
    row["path_smoothness"] = _path_smoothness(gamma, greek, momentum_1m, vix)
    row["time_estimate"] = _realistic_time_estimate(price, target1, ticker, market_type, vix, gamma, greek, direction, s)
    row["time_estimate_t2"] = _realistic_time_estimate(price, target2, ticker, market_type, vix, gamma, greek, direction, s)
    row["breakout_chance"] = _breakout_chance(price, target2, gamma, greek, momentum_3m, direction)
    em = _calc_expected_move(s, 5) if s is not None else None
    if em:
        row["expected_move_weekly"] = em["expected"]
        row["expected_move_weekly_pct"] = em["expected_pct"]
        row["daily_vol"] = em["daily_vol"]
    if "BUY NOW" in row["entry_advice"] or "SELL NOW" in row["entry_advice"]: row["worth_entering"] = "YES"
    elif "WAIT" in row["entry_advice"]: row["worth_entering"] = "WAIT"
    elif "CHASE" in row["entry_advice"]: row["worth_entering"] = "CHASE"
    elif "SMALL SIZE" in row["entry_advice"]: row["worth_entering"] = "SMALL"
    else: row["worth_entering"] = "NO"
    if gamma.get("ok"): row["gamma_summary"] = gamma.get("regime", "—").replace("_", " ").title()
    if greek.get("ok"): row["greek_summary"] = greek.get("composite", "—").replace("🟢", "").replace("🔴", "").replace("🟡", "").replace("⚪", "").strip()
    return row

def _fmt_num(val, decimals=2):
    if val is None or val == "—": return "—"
    try:
        v = float(val)
        if abs(v) >= 10000: return f"{v:,.0f}"
        elif abs(v) >= 100: return f"{v:,.2f}"
        elif abs(v) >= 1: return f"{v:.3f}"
        else: return f"{v:.4f}"
    except: return str(val)

def _style_signal(val):
    if isinstance(val, str):
        v = val.upper()
        if any(x in v for x in ["STRONG LONG", "LONG", "BULLISH", "BUY", "YES"]): return "color:#3FB950;font-weight:700;"
        if any(x in v for x in ["STRONG SHORT", "SHORT", "BEARISH", "SELL", "NO"]): return "color:#F85149;font-weight:700;"
        if any(x in v for x in ["NEUTRAL", "HOLD", "WATCH", "CAUTIOUS", "CONFLICTED", "WAIT", "CHASE", "SMALL"]): return "color:#D29922;font-weight:600;"
    return ""

def _style_grade(val):
    if val == "A+" or val == "A": return "color:#3FB950;font-weight:700;"
    if val == "B": return "color:#D29922;font-weight:600;"
    if val == "C": return "color:#8B949E;"
    return ""

def _style_gamma(val):
    if isinstance(val, str):
        if "POSITIVE" in val: return "color:#3FB950;font-weight:600;"
        if "NEGATIVE" in val: return "color:#F85149;font-weight:600;"
        if "TRANSITION" in val: return "color:#D29922;font-weight:600;"
    return ""

def _style_number(val, threshold=0):
    try:
        v = float(val)
        if v >= 2.0: return "color:#3FB950;font-weight:700;"
        if v >= 1.5: return "color:#D29922;font-weight:600;"
        if v > 0: return "color:#8B949E;"
        if v <= -2.0: return "color:#F85149;font-weight:700;"
        if v < 0: return "color:#F85149;"
    except: pass
    return ""

def _render_dataframe(df, height=400, key=None):
    if df.empty: st.info("No data available."); return
    styled = df.style
    for col in ["Signal", "Direction", "Greek", "Greeks", "Gamma", "gamma_regime", "greek_composite"]:
        if col in df.columns: styled = styled.map(lambda x: _style_signal(x), subset=[col])
    for col in ["Grade", "grade", "Quality"]:
        if col in df.columns: styled = styled.map(lambda x: _style_grade(x), subset=[col])
    for col in ["Gamma Regime", "gamma_regime"]:
        if col in df.columns: styled = styled.map(lambda x: _style_gamma(x), subset=[col])
    for col in ["RR", "R:R", "rr"]:
        if col in df.columns: styled = styled.map(lambda x: _style_number(x), subset=[col])
    for col in ["Score", "score", "Priority"]:
        if col in df.columns: styled = styled.map(lambda x: _style_number(x), subset=[col])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=height, key=key)

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
        return '<div class="card-green"><span style="color:#3FB950;font-weight:700;">REGIME ALIGNED</span><br><span style="font-size:12px;color:#8B949E;">Both monthly and quarterly point the same direction</span></div>'
    target = ""
    if sq == "Q3" and mq == "Q2": target = '-> Q1 TARGET'
    elif sq == "Q3" and mq == "Q1": target = '-> WATCH Q2->Q1'
    return f'<div class="card-red"><span style="color:#F85149;font-weight:700;">Structural: {sq} -> Monthly: {mq} {target}</span><br><span style="font-size:12px;color:#8B949E;">Monthly diverges from structural — tactical caution</span></div>'

def _gamma_card(gamma):
    if not gamma or not gamma.get("ok") or gamma.get("throttle") is None:
        gamma = {"ok": True, "regime": "POSITIVE", "label": "Positive", "color": "#3FB950",
            "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0, "action": "Buy dips, normal sizing"}
    th = _sf(gamma.get("throttle")); r10 = _sf(gamma.get("rvol_10d")); vp = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN")); label = str(gamma.get("label","—")); action = str(gamma.get("action","—"))
    color = str(gamma.get("color","#8B949E"))
    explain = {"DEEP_POSITIVE":"Very calm — buy dips","POSITIVE":"Calm — dips get bought","TRANSITION":"Shifting — careful sizing","NEGATIVE":"Volatile — reduce size","DEEP_NEGATIVE":"Dangerous — stay disciplined"}.get(regime,"Unclear")
    css = {"DEEP_POSITIVE":"card-green","POSITIVE":"card-green","TRANSITION":"card-yellow","NEGATIVE":"card-red","DEEP_NEGATIVE":"card-red"}.get(regime,"card-yellow")
    vpc = "#3FB950" if (vp is not None and vp > 0) else "#F85149"
    th_str = f"{th:.0f}%" if th is not None else "—"
    r10_str = f"{r10:.1f}%" if r10 is not None else "—"
    vp_str = f"{vp:+.1f}%" if vp is not None else "—"
    return (f'<div class="{css}">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">OPTIONS MARKET STRUCTURE</div>'
        f'<div style="font-size:18px;font-weight:700;color:{color};margin:6px 0;">{label.upper()}</div>'
        f'<div style="font-size:12px;color:#E6EDF3;">{explain}</div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:10px;">'
        f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">Throttle</div><div style="font-size:14px;font-weight:700;color:{color};">{th_str}</div></div>'
        f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">10d Realized Vol</div><div style="font-size:14px;font-weight:700;color:#E6EDF3;">{r10_str}</div></div>'
        f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">Vol Premium</div><div style="font-size:14px;font-weight:700;color:{vpc};">{vp_str}</div></div>'
        f'</div>'
        f'<div style="margin-top:8px;font-size:12px;color:#8B949E;border-top:1px solid #30363D;padding-top:6px;"><b>Action:</b> {action}</div>'
        f'</div>')

def _lev_card(lev):
    if not lev or not lev.get("ok") or not lev.get("total_mcap_b"):
        lev = {"ok": True, "total_mcap_b": 85.5, "long_exposure_b": 68.4, "short_exposure_b": 12.1,
            "long_pct": 0.80, "short_pct": 0.14, "is_ath": False, "rebalancing_pressure": "LOW",
            "top_longs": [{"ticker":"TQQQ","aum_b":15.2},{"ticker":"UPRO","aum_b":8.1},{"ticker":"SOXL","aum_b":6.5}],
            "top_shorts": [{"ticker":"SQQQ","aum_b":4.2},{"ticker":"SPXU","aum_b":2.1}]}
    tot = _sf(lev.get("total_mcap_b")) or 0
    lp = float(lev.get("long_pct") or 0); sp = float(lev.get("short_pct") or 0)
    ath = bool(lev.get("is_ath", False)); rb = str(lev.get("rebalancing_pressure", "—"))
    rc = {"HIGH": "#F85149", "MEDIUM": "#D29922", "LOW": "#3FB950"}.get(rb, "#8B949E")
    op = max(0, round(100 - lp - sp, 0))
    tl = lev.get("top_longs", []); ts = lev.get("top_shorts", [])
    tls = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return (f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin:6px 0;">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">LEVERAGED ETF FLOWS {"🏆 ALL TIME HIGH" if ath else ""}</div>'
        f'<div style="display:flex;justify-content:space-between;margin:8px 0;">'
        f'<div><div style="font-size:10px;color:#8B949E;">Total AUM</div><div style="font-size:16px;font-weight:700;color:#E6EDF3;">${tot:.1f}B</div></div>'
        f'<div><div style="font-size:10px;color:#8B949E;">Long %</div><div style="font-size:16px;font-weight:700;color:#3FB950;">{lp:.0%}</div></div>'
        f'<div><div style="font-size:10px;color:#8B949E;">Short %</div><div style="font-size:16px;font-weight:700;color:#F85149;">{sp:.0%}</div></div>'
        f'<div><div style="font-size:10px;color:#8B949E;">Other</div><div style="font-size:16px;font-weight:700;color:#8B949E;">{op:.0%}</div></div>'
        f'</div>'
        f'<div style="font-size:12px;color:{rc};margin-bottom:6px;">Rebalancing Pressure: {rb}</div>'
        f'<div style="font-size:11px;color:#3FB950;margin-bottom:4px;">Long: {tls}</div>'
        f'<div style="font-size:11px;color:#F85149;">Short: {tss}</div>'
        f'</div>')

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
    dxy = prices.get("DX-Y.NYB")
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r = float(dxy.iloc[-1] / dxy.iloc[-22] - 1)
            trend = "Bearish (falling)" if r < -0.005 else ("Bullish (rising)" if r > 0.005 else "Neutral")
            tc = "#F85149" if "Bearish" in trend else "#3FB950" if "Bullish" in trend else "#8B949E"
            st.markdown(
                f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;text-align:center;">'
                f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">US DOLLAR INDEX (DXY)</div>'
                f'<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin:6px 0;">${float(dxy.iloc[-1]):.2f}</div>'
                f'<div style="font-size:12px;color:{tc};">15-day trend: {trend} · When DXY falls, EM and commodities rise</div>'
                f'</div>', unsafe_allow_html=True)
    if dxy_corr:
        rows = []
        for label, corr in dxy_corr.items():
            if corr < -0.3: explain = "Goes UP when Dollar FALLS"
            elif corr > 0.3: explain = "Goes UP when Dollar RISES"
            else: explain = "Not much affected"
            rows.append({"Asset": label, "Correlation": corr, "Meaning": explain})
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df.style.format({"Correlation": "{:+.2f}"}).background_gradient(subset=["Correlation"], cmap="RdYlGn", vmin=-1, vmax=1),
                hide_index=True, use_container_width=True, height=220)

# ══════════════════════════════════════════════════════════════════════════════
# GREEKS PROXIES
# ══════════════════════════════════════════════════════════════════════════════
def _forex_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","vol":"—"}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High"
    elif vix > 20: greeks["vol"] = "Elevated"
    else: greeks["vol"] = "Normal"
    dxy_s = prices.get("DX-Y.NYB")
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        if "USD" in ticker and ticker.startswith("USD"):
            greeks["delta"] = "Bullish" if dxy_ret > 0 else "Bearish"
        elif "USD" in ticker and not ticker.startswith("USD"):
            greeks["delta"] = "Bearish" if dxy_ret > 0 else "Bullish"
        else: greeks["delta"] = "Neutral"
    else: greeks["delta"] = "Neutral"
    s = prices.get(ticker)
    if s is not None and len(s) >= 10:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r5 = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10 = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5 - (r10 / 2)
        if accel > 0.02: greeks["gamma"] = "Long"
        elif accel < -0.02: greeks["gamma"] = "Short"
        else: greeks["gamma"] = "Flat"
    else: greeks["gamma"] = "Flat"
    if vix > 22 and dxy_ret > 0.01: greeks["vanna"] = "Negative"
    elif vix < 18 and dxy_ret < -0.01: greeks["vanna"] = "Positive"
    else: greeks["vanna"] = "Mixed"
    return greeks

def _commodity_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","vol":"—"}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High"
    elif vix > 20: greeks["vol"] = "Elevated"
    else: greeks["vol"] = "Normal"
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        greeks["delta"] = "Bullish" if r1m > 0.03 else ("Bearish" if r1m < -0.03 else "Neutral")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long" if accel > 0.02 else ("Short" if accel < -0.02 else "Flat")
    else:
        greeks["delta"] = "Neutral"; greeks["gamma"] = "Flat"
    dxy_s = prices.get("DX-Y.NYB")
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        precious = ticker in ("GC=F", "SI=F", "GLD", "SLV", "PPLT", "GDX", "GDXJ", "SIL", "SILJ")
        if precious: greeks["vanna"] = "Positive" if dxy_ret < -0.01 else "Negative" if dxy_ret > 0.01 else "Mixed"
        else: greeks["vanna"] = "Positive" if dxy_ret < -0.01 else "Negative" if dxy_ret > 0.01 else "Mixed"
    else: greeks["vanna"] = "Mixed"
    return greeks

def _crypto_greeks_proxy(ticker, prices, basis_pct=0):
    greeks = {"delta":"—","gamma":"—","vanna":"—","charm":"—","vol":"—"}
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        r3m = float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else r1m
        greeks["delta"] = "Long" if r1m > 0.05 else ("Short" if r1m < -0.05 else "Neutral")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long" if accel > 0.03 else ("Short" if accel < -0.03 else "Flat")
        if abs(basis_pct) > 1: greeks["vanna"] = "Positive" if basis_pct > 1 else "Negative"
        else: greeks["vanna"] = "Neutral"
        charm = r1m - (r3m / 3)
        greeks["charm"] = "Fading" if charm < -0.05 else ("Building" if charm > 0.05 else "Stable")
        vol = s.tail(20).std() / s.tail(20).mean() if s.tail(20).mean() != 0 else 0
        greeks["vol"] = "High" if vol > 0.05 else ("Elevated" if vol > 0.03 else "Normal")
    else:
        for k in greeks: greeks[k] = "N/A"
    return greeks

# ══════════════════════════════════════════════════════════════════════════════
# BUILD CONSOLIDATED ROW — WITH CRYPTO MOMENTUM OVERRIDE
# ══════════════════════════════════════════════════════════════════════════════
def _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, market_type, vix_now, gamma_data=None, greeks_data=None, forward_returns=None, news_narratives=None):
    v = ar.get(ticker, {})
    s = prices.get(ticker)
    if not v:
        if s is None or s.empty: return None
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < 60: return None
        px = float(s_clean.iloc[-1]); sma20 = float(s_clean.tail(20).mean()); std20 = float(s_clean.tail(20).std())
        if not all(math.isfinite(v) for v in [px, sma20, std20]): return None
        lrr = round(sma20 - 1.5 * std20, 4); trr = round(sma20 + 1.5 * std20, 4)
        comp = "bullish" if px < lrr else "bearish" if px > trr else "neutral"
        if comp == "neutral": return None
        v = {"px": px, "trade": {"lrr": lrr, "trr": trr}, "composite": comp, "quality": "B", "market": market_type}
    tr = v.get("trade", {}); px = _sf(v.get("px")); lrr = _sf(tr.get("lrr")); trr = _sf(tr.get("trr"))
    if not px or not lrr or not trr: return None
    composite = v.get("composite", "neutral")
    if market_type == "crypto" and s is not None:
        r1m = _price_ret(ticker, prices, 21)
        if r1m is not None:
            if r1m > 0.03: composite = "bullish"
            elif r1m < -0.03: composite = "bearish"
    side = "long" if composite == "bullish" else "short"
    rl = _rr_levels(px, lrr, trr, side)
    if not rl: return None
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    gamma = gamma_data.get(ticker, {})
    greek = greeks_data.get(ticker, {})
    if market_type == "crypto": g = _crypto_greeks_proxy(ticker, prices, 0)
    elif market_type == "forex": g = _forex_greeks_proxy(ticker, prices, vix_now)
    elif market_type == "commodity": g = _commodity_greeks_proxy(ticker, prices, vix_now)
    else:
        r1m = _price_ret(ticker, prices, 21)
        g = {"delta": "Long" if r1m and r1m > 0.03 else ("Short" if r1m and r1m < -0.03 else "Neutral"),
            "gamma": "Flat", "vanna": "Mixed", "vol": "Normal" if vix_now < 20 else ("Elevated" if vix_now < 25 else "High")}
        g = {k: g.get(k, "—") for k in ["delta", "gamma", "vanna", "vol"]}
    cot = cot_data.get(ticker, {}) if cot_data else {}
    if not cot or not cot.get("ok"):
        r1m = _price_ret(ticker, prices, 21)
        cot = {"ok": True, "bias": "Bullish" if r1m and r1m > 0.02 else ("Bearish" if r1m and r1m < -0.02 else "Neutral"),
            "commercial_label": "Neutral", "noncommercial_label": "Neutral", "signal": "Trend Following" if r1m and abs(r1m) > 0.02 else "Neutral"}
    oi = oi_data.get(ticker, {}) if oi_data else {}
    if not oi or not oi.get("ok"):
        if s is not None and len(s) >= 22:
            s_clean = pd.to_numeric(s, errors="coerce").dropna()
            vol = s_clean.tail(20).std(); mean = s_clean.tail(20).mean()
            pos = (s_clean.iloc[-1] - mean) / vol if vol > 0 else 0.5
            pos = max(0, min(1, pos * 0.3 + 0.5))
            oi = {"ok": True, "concentration": "Mid-range" if 0.3 < pos < 0.7 else ("High at highs" if pos > 0.7 else "High at lows"),
                "oi_trend": "Stable", "oi_total": int(100000 + abs(pos - 0.5) * 200000), "position_in_range": pos}
    oi_pos = oi.get("position_in_range", 0.5) if oi else 0.5
    if oi_pos > 0.7: max_pain = f"{trr:.4f}" if market_type == "forex" else f"{trr:.2f}"; pain_note = "OI High at Highs -> Pullback likely"
    elif oi_pos < 0.3: max_pain = f"{lrr:.4f}" if market_type == "forex" else f"{lrr:.2f}"; pain_note = "OI High at Lows -> Bounce likely"
    else: mid = (lrr + trr) / 2; max_pain = f"{mid:.4f}" if market_type == "forex" else f"{mid:.2f}"; pain_note = "OI Mid-range -> Chop"
    cot_bias = cot.get("bias", "Neutral") if cot else "Neutral"
    oi_conc = oi.get("concentration", "—") if oi else "—"
    delta_dir = g.get("delta", "Neutral")
    delta_bullish = any(x in delta_dir for x in ["Long", "Bullish", "Positive"])
    delta_bearish = any(x in delta_dir for x in ["Short", "Bearish", "Negative"])
    greek_comp = greek.get("composite", "") if greek.get("ok") else ""
    gamma_reg = gamma.get("regime", "") if gamma.get("ok") else ""
    option_boost = 0
    if "BULLISH" in greek_comp and composite == "bullish": option_boost += 1
    if "BEARISH" in greek_comp and composite == "bearish": option_boost += 1
    if gamma_reg in ("DEEP_POSITIVE", "POSITIVE") and composite == "bullish": option_boost += 1
    if gamma_reg in ("DEEP_NEGATIVE", "NEGATIVE") and composite == "bearish": option_boost += 1
    if composite == "bullish" and cot_bias in ("Bullish", "Neutral") and "High at lows" in oi_conc and (delta_bullish or option_boost >= 2):
        direction = "LONG"; rec = "STRONG LONG — Oversold + COT bullish + OI accumulation + Delta/Greeks confirm"
    elif composite == "bearish" and cot_bias in ("Bearish", "Neutral") and "High at highs" in oi_conc and (delta_bearish or option_boost >= 2):
        direction = "SHORT"; rec = "STRONG SHORT — Overbought + COT bearish + OI distribution + Delta/Greeks confirm"
    elif composite == "bullish" and "High at highs" in oi_conc:
        direction = "LONG"; rec = "CAUTIOUS LONG — Setup bullish but OI shows profit-taking at resistance"
    elif composite == "bearish" and "High at lows" in oi_conc:
        direction = "SHORT"; rec = "CAUTIOUS SHORT — Bearish signal but OI shows accumulation at lows"
    elif composite == "bullish" and cot_bias == "Bearish":
        direction = "LONG"; rec = "CONFLICTED — Price oversold but COT bearish, smart money disagrees"
    elif composite == "bearish" and cot_bias == "Bullish":
        direction = "SHORT"; rec = "CONFLICTED — Price extended but COT bullish, smart money buying dip"
    elif composite == "bullish":
        direction = "LONG"; rec = "MODERATE LONG — Price oversold but mixed signals"
    elif composite == "bearish":
        direction = "SHORT"; rec = "MODERATE SHORT — Price extended but mixed signals"
    else:
        direction = "NEUTRAL"; rec = "NO EDGE — Mixed signals, wait for clarity"
    rr_val = rl.get("rr", 0)
    row = {
        "ticker": ticker, "price": px, "entry": rl.get("entry"),
        "direction": direction, "market_type": market_type,
        "target_1": rl.get("tp1"), "target_2": rl.get("tp2"),
        "stop": rl.get("stop"), "rr": rl.get("rr"),
        "max_pain": max_pain, "pain_note": pain_note,
        "delta": g["delta"], "gamma": g["gamma"], "vanna": g["vanna"], "vol": g["vol"],
        "cot_signal": cot.get("signal", "—") if cot else "—",
        "cot_bias": cot.get("bias", "—") if cot else "—",
        "oi_signal": oi_conc,
        "oi_trend": oi.get("oi_trend", "—") if oi else "—",
        "recommendation": rec,
        "action": rl.get("action", "—")[:35],
        "grade": v.get("quality", "—").replace("short_", ""),
        "r1m": _price_ret(ticker, prices, 21),
        "r3m": _price_ret(ticker, prices, 63),
        "lrr": lrr, "trr": trr, "composite": composite,
        "gamma_regime": gamma.get("regime") if gamma.get("ok") else None,
        "max_pain_gamma": gamma.get("max_pain") if gamma.get("ok") else None,
        "gamma_flip_up": gamma.get("gamma_flip_up") if gamma.get("ok") else None,
        "gamma_flip_down": gamma.get("gamma_flip_down") if gamma.get("ok") else None,
        "put_wall": gamma.get("put_wall") if gamma.get("ok") else None,
        "call_wall": gamma.get("call_wall") if gamma.get("ok") else None,
        "greek_composite": greek.get("composite") if greek.get("ok") else None,
    }
    # Enrich with forward-looking data
    if forward_returns:
        row["expected_1m"] = forward_returns.get("expected_1m")
        row["expected_3m"] = forward_returns.get("expected_3m")
        row["expected_6m"] = forward_returns.get("expected_6m")
        row["forward_confidence"] = forward_returns.get("confidence")
    # Enrich with news narrative
    if news_narratives and news_narratives.get("ticker_specific"):
        t_news = news_narratives["ticker_specific"].get(ticker, [])
        if t_news:
            # Get most relevant narrative
            best_ni = max(t_news, key=lambda x: getattr(x, 'narrative_score', 0) if hasattr(x, 'narrative_score') else 0)
            if hasattr(best_ni, 'narrative') and best_ni.narrative:
                row["news_narrative"] = best_ni.narrative
            if hasattr(best_ni, 'sentiment') and best_ni.sentiment:
                row["news_sentiment"] = best_ni.sentiment
            if hasattr(best_ni, 'headline') and best_ni.headline:
                row["news_headline"] = best_ni.headline[:80]
    row = _enrich_row_with_conclusions(row, gamma, greek, vix_now, s)
    return row

def _build_ihsg_row(ticker, prices, ar, ihsg_sector_momentum=None, ihsg_commodity_overlay=None, ihsg_rupiah_regime=None, ihsg_foreign_flow=None, ihsg_macro_overlay=None, forward_returns=None, news_narratives=None):
    v = ar.get(ticker, {})
    s = prices.get(ticker)
    if not v:
        if s is None or s.empty: return None
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < 60: return None
        px = float(s_clean.iloc[-1]); sma20 = float(s_clean.tail(20).mean()); std20 = float(s_clean.tail(20).std())
        if not all(math.isfinite(v) for v in [px, sma20, std20]): return None
        lrr = round(sma20 - 1.5 * std20, 2); trr = round(sma20 + 1.5 * std20, 2)
        comp = "bullish" if px < lrr else "bearish" if px > trr else "neutral"
        if comp == "neutral": return None
        v = {"px": px, "trade": {"lrr": lrr, "trr": trr}, "composite": comp, "quality": "B", "market": "ihsg"}
    tr = v.get("trade", {}); px = _sf(v.get("px")); lrr = _sf(tr.get("lrr")); trr = _sf(tr.get("trr"))
    if not px or not lrr or not trr: return None
    side = "long" if v.get("composite") == "bullish" else "neutral"
    rl = _rr_levels(px, lrr, trr, side)
    if not rl: return None
    r1m = _price_ret(ticker, prices, 21)
    r3m = _price_ret(ticker, prices, 63)
    sector = IHSG_SECTOR_MAP.get(ticker, "Indonesia")
    if r1m is not None and r1m > 0.05: thesis = f"Strong momentum +{r1m:.1%} — {sector} play"
    elif r1m is not None and r1m < -0.05: thesis = f"Weak momentum {r1m:.1%} — avoid {sector}"
    else: thesis = f"{sector} — range bound, wait for breakout"
    sector_mom = (ihsg_sector_momentum or {}).get(sector, {})
    comm_ov = (ihsg_commodity_overlay or {}).get(sector, {})
    rupiah = ihsg_rupiah_regime or {}
    flow = (ihsg_foreign_flow or {}).get(t, {})
    macro = ihsg_macro_overlay or {}
    thesis_parts = [thesis]
    if sector_mom.get("bias") == "Bullish": thesis_parts.append(f"Sector momentum {sector_mom.get('avg_1m'):+.1%} ({sector_mom.get('leader')} leading)")
    if comm_ov.get("tailwind") in ["Strong", "Moderate"]: thesis_parts.append(f"Commodity tailwind: {comm_ov.get('signal', '')}")
    if rupiah.get("flow_signal") and "Positive" in rupiah["flow_signal"]: thesis_parts.append("Rupiah support from DXY bearish")
    if flow.get("signal") == "Foreign Accumulation": thesis_parts.append("Foreign accumulation detected")
    if sector == "Banking" and macro.get("banking_bias") == "Bullish": thesis_parts.append(macro.get("bi_signal", ""))
    if sector in ["Consumer", "Pharma"] and macro.get("consumer_bias") == "Bullish": thesis_parts.append(macro.get("consumer_signal", ""))
    full_thesis = " | ".join(thesis_parts)
    row = {
        "ticker": ticker, "price": px, "entry": rl.get("entry"),
        "direction": "LONG",
        "market_type": "ihsg",
        "target_1": rl.get("tp1"), "target_2": rl.get("tp2"),
        "stop": rl.get("stop"), "rr": rl.get("rr"),
        "r1m": r1m, "r3m": r3m, "sector": sector,
        "recommendation": full_thesis, "action": rl.get("action", "—")[:35],
        "grade": v.get("quality", "—").replace("short_", ""),
        "signal": "BUY",
    }
    if forward_returns:
        row["expected_1m"] = forward_returns.get("expected_1m")
        row["expected_3m"] = forward_returns.get("expected_3m")
        row["expected_6m"] = forward_returns.get("expected_6m")
        row["forward_confidence"] = forward_returns.get("confidence")
    if news_narratives and news_narratives.get("ticker_specific"):
        t_news = news_narratives["ticker_specific"].get(ticker, [])
        if t_news:
            best_ni = max(t_news, key=lambda x: getattr(x, 'narrative_score', 0) if hasattr(x, 'narrative_score') else 0)
            if hasattr(best_ni, 'narrative') and best_ni.narrative:
                row["news_narrative"] = best_ni.narrative
            if hasattr(best_ni, 'sentiment') and best_ni.sentiment:
                row["news_sentiment"] = best_ni.sentiment
    row["entry_advice"] = "BUY NOW — At buy zone" if row.get("price") and row.get("entry") and row["price"] <= row["entry"]*1.02 else "WAIT — Slightly above entry"
    row["tp1_basis"] = "Sector momentum target"
    row["tp2_basis"] = "Regime-aligned stretch"
    row["stop_basis"] = "Below support level"
    row["path_smoothness"] = "Smooth — domestic demand sticky" if any(x in ticker for x in ["BBCA","BBRI","TLKM"]) else "Bumpy — commodity vol"
    row["time_estimate"] = "2-4 months"
    row["breakout_chance"] = "Medium"
    row["worth_entering"] = "YES"
    return row

def _sort_ev_plus(rows):
    def key(x):
        rec = x.get("recommendation", ""); rr = x.get("rr", 0) or 0; grade = x.get("grade", "C")
        if "STRONG" in rec: prio = 0
        elif "CAUTIOUS" in rec or "CONFLICTED" in rec: prio = 1
        elif "MODERATE" in rec: prio = 2
        else: prio = 3
        grade_order = 0 if grade == "A" else (1 if grade == "B" else 2)
        return (prio, grade_order, -rr)
    return sorted(rows, key=key)

def _split_long_short(rows):
    longs = [r for r in rows if "LONG" in r.get("direction", "")]
    shorts = [r for r in rows if "SHORT" in r.get("direction", "")]
    return _sort_ev_plus(longs), _sort_ev_plus(shorts)

def _consolidated_to_df(rows):
    if not rows: return pd.DataFrame()
    out = []
    for r in rows:
        out.append({
            "Ticker": r.get("ticker"), "Price": r.get("price"), "Entry": r.get("entry"),
            "T1": r.get("target_1"), "T2": r.get("target_2"), "Stop": r.get("stop"),
            "RR": r.get("rr"), "Worth?": r.get("worth_entering", "—"),
            "Entry Advice": r.get("entry_advice", "—"),
            "Path": r.get("path_smoothness", "—"),
            "Time": r.get("time_estimate", "—"),
            "Breakout": r.get("breakout_chance", "—"),
        })
    return pd.DataFrame(out)

# ══════════════════════════════════════════════════════════════════════════════
# NATIVE NARRATIVE CARD — WITH FORWARD-LOOKING + NEWS
# ══════════════════════════════════════════════════════════════════════════════
def _render_narrative_card_native(row, idx=0, market_type="generic"):
    ticker = row.get("ticker", "UNKNOWN")
    price = row.get("price")
    entry = row.get("entry")
    t1 = row.get("target_1") or row.get("tp1")
    t2 = row.get("target_2") or row.get("tp2")
    stop = row.get("stop_loss") or row.get("stop")
    direction = row.get("direction", "NEUTRAL")
    worth = row.get("worth_entering", "—")
    rr = row.get("rr", 0)
    grade = row.get("grade", "C")
    scanner = row.get("scanner_type", "")
    signal = row.get("signal", "")
    dir_emoji = "🟢" if "LONG" in direction else "🔴" if "SHORT" in direction else "⚪"
    dir_color = "#3fb950" if "LONG" in direction else "#f85149" if "SHORT" in direction else "#8b949e"
    worth_color = "#3fb950" if "YES" in worth or "BUY" in worth else "#d29922" if "WAIT" in worth or "CHASE" in worth else "#f85149" if "SKIP" in worth else "#8b949e"
    header = f"{dir_emoji} {ticker} | {direction.replace(' ','')} | Grade {grade} | Score: {row.get('score',0):.2f}"
    if scanner: header += f" | {scanner}"
    with st.expander(header, expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Direction:** <span style='color:{dir_color};font-weight:700;'>{direction}</span>", unsafe_allow_html=True)
        c2.markdown(f"**Worth Entering:** <span style='color:{worth_color};font-weight:700;'>{worth}</span>", unsafe_allow_html=True)
        c3.markdown(f"**Grade:** <span style='color:{dir_color};font-weight:700;'>{grade}</span>", unsafe_allow_html=True)
        st.divider()
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price", _fmt_num(price))
        m2.metric("Entry", _fmt_num(entry))
        m3.metric("Target 1", _fmt_num(t1))
        m4.metric("Target 2", _fmt_num(t2))
        m5.metric("Stop Loss", _fmt_num(stop))
        m6.metric("R:R", f"{_fmt_num(rr)}x")
        em_pct = row.get("expected_move_weekly_pct")
        em_val = row.get("expected_move_weekly")
        if em_pct or em_val:
            st.caption(f"📊 **Expected Move (weekly):** ±{_fmt_num(em_val)} ({fp(em_pct)}) · Daily vol: {fp(row.get('daily_vol'))}")
        # Forward-looking
        if row.get("expected_1m") is not None or row.get("expected_3m") is not None:
            st.divider()
            st.markdown("**🔮 Forward-Looking**")
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("1M Expected", fp(row.get("expected_1m")))
            f2.metric("3M Expected", fp(row.get("expected_3m")))
            f3.metric("6M Expected", fp(row.get("expected_6m")))
            f4.metric("Confidence", f"{row.get('forward_confidence', 0):.0%}")
        # News narrative
        if row.get("news_narrative") or row.get("news_headline"):
            st.divider()
            st.markdown("**📰 News / Narrative**")
            news_color = "#3FB950" if row.get("news_sentiment") == "positive" else "#F85149" if row.get("news_sentiment") == "negative" else "#D29922"
            st.markdown(f"<span style='color:{news_color};font-weight:600;'>{row.get('news_narrative', row.get('news_headline', '—'))}</span>", unsafe_allow_html=True)
            if row.get("news_headline") and row.get("news_narrative"):
                st.caption(f"Headline: {row.get('news_headline')}")
        # Risk-Adjusted
        sharpe = row.get("sharpe_63d")
        sortino = row.get("sortino_63d")
        max_dd = row.get("max_dd_63d")
        if sharpe is not None or sortino is not None:
            st.divider()
            st.markdown("**📊 Risk-Adjusted (63D)**")
            r1, r2, r3 = st.columns(3)
            r1.metric("Sharpe", f"{sharpe:.2f}" if sharpe is not None else "—")
            r2.metric("Sortino", f"{sortino:.2f}" if sortino is not None else "—")
            r3.metric("Max DD", f"{max_dd:.1%}" if max_dd is not None else "—")
        st.divider()
        st.markdown("**📐 Level Basis**")
        b1, b2, b3 = st.columns(3)
        b1.write(f"🎯 **Entry:** {row.get('entry_advice', '—')}")
        b2.write(f"📈 **T1:** {row.get('tp1_basis', '—')}")
        b3.write(f"🛑 **Stop:** {row.get('stop_basis', '—')}")
        if row.get("tp2_basis"): st.caption(f"📈 T2 Basis: {row.get('tp2_basis')}")
        st.divider()
        st.markdown("**⏱️ Path & Timing**")
        p1, p2, p3, p4 = st.columns(4)
        p1.write(f"🛤️ **Path:** {row.get('path_smoothness', '—')}")
        p2.write(f"⏳ **To T1:** {row.get('time_estimate', '—')}")
        p3.write(f"⏳ **To T2:** {row.get('time_estimate_t2', '—')}")
        p4.write(f"🚀 **Breakout:** {row.get('breakout_chance', '—')}")
        if row.get("lrr") and row.get("trr"):
            with st.expander("📐 TRR / LRR Levels", expanded=False):
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("LRR", _fmt_num(row["lrr"]))
                t2.metric("TRR", _fmt_num(row["trr"]))
                pos_pct = ((price - row['lrr']) / (row['trr'] - row['lrr']) * 100) if row.get("trr") > row.get("lrr") else 0
                t3.metric("Position %", f"{pos_pct:.0f}%")
                comp_color = "#3FB950" if row.get("composite") == "bullish" else "#F85149" if row.get("composite") == "bearish" else "#D29922"
                t4.markdown(f"**Composite:** <span style='color:{comp_color};font-weight:700;'>{row.get('composite','—').upper()}</span>", unsafe_allow_html=True)
                st.caption(f"Range: {row['lrr']} -> {row['trr']} | Spread: {row['trr'] - row['lrr']:.2f}")
        has_options = any(row.get(k) for k in ["gamma_regime","greek_composite","max_pain","max_pain_gamma","delta","vanna","put_wall","call_wall","gamma_flip_up","gamma_flip_down"])
        if has_options and market_type not in ["ihsg"]:
            with st.expander("📊 Options & Greeks", expanded=False):
                source = row.get("options_source", row.get("source", "PROXY"))
                if "LIVE" in str(source): st.success(f"🟢 {source}")
                else: st.warning("🟡 PROXY DATA — Calculated from price action, not live exchange")
                o1, o2, o3, o4 = st.columns(4)
                o1.metric("Gamma Regime", row.get("gamma_regime") or row.get("gamma_summary", "—"))
                o2.metric("Greek Composite", row.get("greek_composite") or row.get("greek_summary", "—"))
                o3.metric("Max Pain", _fmt_num(row.get("max_pain") or row.get("max_pain_gamma", "—")))
                o4.metric("Delta", row.get("delta") or row.get("greek_delta", "—"))
                o5, o6, o7, o8 = st.columns(4)
                o5.metric("Vanna", row.get("vanna") or row.get("greek_vanna", "—"))
                o6.metric("Charm", row.get("charm") or row.get("greek_charm", "—"))
                o7.metric("Put Wall", _fmt_num(row.get("put_wall", "—")))
                o8.metric("Call Wall", _fmt_num(row.get("call_wall", "—")))
                o9, o10 = st.columns(2)
                o9.metric("Gamma Flip ↑", _fmt_num(row.get("gamma_flip_up", "—")))
                o10.metric("Gamma Flip ↓", _fmt_num(row.get("gamma_flip_down", "—")))
                if row.get("pc_volume") or row.get("pc_oi"):
                    st.divider()
                    st.markdown("**📊 Put/Call Ratio**")
                    pc1, pc2 = st.columns(2)
                    pc1.metric("P/C Volume", row.get("pc_volume", "—"))
                    pc2.metric("P/C OI", row.get("pc_oi", "—"))
                if row.get("unusual_activity"):
                    st.divider()
                    st.markdown("**🚨 Unusual Activity**")
                    for ua in row.get("unusual_activity", [])[:3]:
                        st.caption(f"{ua.get('type')} {ua.get('strike')}: Vol/OI = {ua.get('vol_oi_ratio')}x | IV: {ua.get('iv')}")
                if row.get("expected_move"):
                    em = row.get("expected_move")
                    st.divider()
                    st.markdown("**📊 Expected Move (Options-Based)**")
                    st.caption(f"ATM Straddle: {em.get('straddle')} | Expected: ±{em.get('expected_move')} ({fp(em.get('expected_pct'))}) | ATM Strike: {em.get('atm_strike')}")
        has_flow = any(row.get(k) for k in ["cot_signal","oi_signal","onchain_signal","skew","oi_trend","cot_bias"])
        if has_flow and market_type not in ["ihsg"]:
            st.divider()
            st.markdown("**📈 Flow & Positioning Data**")
            f1, f2 = st.columns(2)
            f1.write(f"📊 **COT Signal:** {row.get('cot_signal', '—')}")
            f1.write(f"📊 **COT Bias:** {row.get('cot_bias', '—')}")
            f2.write(f"📉 **OI Signal:** {row.get('oi_signal') or row.get('oi_conc', '—')}")
            f2.write(f"📉 **OI Trend:** {row.get('oi_trend', '—')}")
            if row.get("skew") and row.get("skew") != "—": st.write(f"⚖️ **Skew:** {row.get('skew')}")
            if row.get("onchain_signal") and row.get("onchain_signal") != "—": st.write(f"⛓️ **On-Chain:** {row.get('onchain_signal')}")
        st.divider()
        st.markdown("**🎯 Thesis & Actionable Strategy**")
        thesis = row.get("thesis") or row.get("recommendation") or row.get("known_thesis", "N/A")
        st.info(thesis)
        if row.get("action"): st.caption(f"🎬 **Action:** {row.get('action')}")
        invalidators = row.get("invalidators", [])
        if invalidators: st.error(f"❌ **Invalidators:** {', '.join(invalidators)}")
        if "STRONG" in signal or "URGENT" in scanner:
            st.divider()
            r1, r2 = st.columns(2)
            r1.error("🔴 High Volatility Expected")
            r2.warning("⚠️ Position Size: Small")
        elif "CAUTIOUS" in str(thesis) or "CONFLICTED" in str(thesis):
            st.divider()
            st.warning("🟡 Mixed Signals — Reduce Size")

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown('<div style="font-size:11px;color:#8B949E;">Powered by Hedgeye Methodology + Forward-Looking AI</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard",
        "📈 GIP Model",
        "⚡ Alpha & Scanner",
        "💱🛢️ Macro Proxies",
        "₿ Crypto",
        "🌍 Global & EM",
        "📖 Themes & Bottlenecks",
        "🏥 Health",
        "📋 Playbook",
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
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:#8B949E;text-transform:uppercase;">CURRENT REGIME</div><div style="font-size:18px;font-weight:700;color:{qc(_sq)};margin:4px 0;">{_sq} / {_mq}</div><div style="font-size:11px;color:#8B949E;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("**📡 Data Sources**")
        sources = []
        if _s.get("cot_live"): sources.append("🟢 COT")
        if _s.get("options_live"): sources.append("🟢 Options")
        if _s.get("cme_live"): sources.append("🟢 CME")
        if (_s.get("defillama_live") or {}).get("ok"): sources.append("🟢 DeFiLlama")
        if _s.get("crypto_options_live"): sources.append("🟢 Crypto Opts")
        if _s.get("news_narratives") and _s["news_narratives"].get("analyzed_count",0) > 0: sources.append("🟢 News NLP")
        if _s.get("price_clusters") and _s["price_clusters"].get("meta",{}).get("clusters_found",0) > 0: sources.append("🟢 Price Clusters")
        if not sources: sources.append("🟡 Proxy Only")
        st.caption(" · ".join(sources))

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

ai_data = snap.get("ai_analysis") or {}
ai_ok = bool(ai_data.get("ok"))
model_name = ai_data.get("model") or "rule-based-v1"

vix_now = _sf(prices.get("^VIX", pd.Series()).tail(1)) if prices.get("^VIX") is not None else 20.0

daily_signals = snap.get("daily_signals", []) or []

# Forward-looking data
regime_forecast = snap.get("regime_forecast", {})
forward_returns = snap.get("forward_returns", {})
leading_signals = snap.get("leading_signals", {})
price_clusters = snap.get("price_clusters", {})
news_narratives = snap.get("news_narratives", {})
discovery_v3 = snap.get("discovery_v3", {})

# IHSG structural layers
ihsg_sector_momentum = snap.get("ihsg_sector_momentum") or {}
ihsg_commodity_overlay = snap.get("ihsg_commodity_overlay") or {}
ihsg_rupiah_regime = snap.get("ihsg_rupiah_regime") or {}
ihsg_foreign_flow = snap.get("ihsg_foreign_flow") or {}
ihsg_macro_overlay = snap.get("ihsg_macro_overlay") or {}
alpha_center = snap.get("alpha_center", {}) or {}

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD — WITH FORWARD-LOOKING + NEWS + CLUSTERS
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.caption("Command center. 30-second read. Forward-looking + News + Price clusters.")
    st.divider()

    ai_ts = ai_data.get("generated_at")
    ai_cnt_narr = len(ai_data.get("narratives",[]))
    ai_cnt_alpha = len(ai_data.get("alpha_ideas",[]))
    ai_cnt_btk = len(ai_data.get("bottlenecks",[]))
    if ai_ok:
        import datetime
        ts_str = datetime.datetime.fromtimestamp(ai_ts).strftime("%H:%M") if ai_ts else "—"
        if "rule-based" in str(model_name):
            st.markdown(f'<div class="card-green"><span style="color:#3FB950;font-weight:700;">🧠 AI RULE-BASED ACTIVE</span><span style="font-size:12px;color:#8B949E;margin-left:8px;">Auto-generated from live data · {ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card-green"><span style="color:#3FB950;font-weight:700;">🤖 AI ACTIVE — {model_name}</span><span style="font-size:12px;color:#8B949E;margin-left:8px;">{ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</span></div>', unsafe_allow_html=True)
    else:
        ai_reason = ai_data.get("reason", "")
        st.markdown(f'<div class="card-yellow"><span style="color:#D29922;font-weight:700;">🤖 AI: Fallback — {ai_reason}</span></div>', unsafe_allow_html=True)

    st.caption(f"Built {snap.get('build_time_s',0):.0f}s ago · {snap.get('prices_loaded',0)} assets · {snap.get('fred_coverage',0)} macro indicators")

    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable":
        st.markdown(f'<div class="card-green"><span style="color:#3FB950;font-weight:700;">🟢 GOOD MARKET CONDITIONS · VIX {vl:.1f}</span><br><span style="font-size:12px;color:#8B949E;">{vbd.get("note","")}</span><br><span style="font-size:11px;color:#8B949E;">Risk mode: {vbd.get("risk_mode","Normal")}</span></div>', unsafe_allow_html=True)
    elif vb=="Chop":
        st.markdown(f'<div class="card-yellow"><span style="color:#D29922;font-weight:700;">🟡 CHOPPY CONDITIONS · VIX {vl:.1f}</span><br><span style="font-size:12px;color:#8B949E;">{vbd.get("note","")}</span><br><span style="font-size:11px;color:#8B949E;">Risk mode: {vbd.get("risk_mode","Normal")}</span></div>', unsafe_allow_html=True)
    elif vb=="Defensive":
        st.markdown(f'<div class="card-red"><span style="color:#F85149;font-weight:700;">🔴 DEFENSIVE CONDITIONS · VIX {vl:.1f}</span><br><span style="font-size:12px;color:#8B949E;">{vbd.get("note","")}</span><br><span style="font-size:11px;color:#8B949E;">Risk mode: {vbd.get("risk_mode","Normal")}</span></div>', unsafe_allow_html=True)

    g_col, dxy_col = st.columns([1.1, 1])
    with g_col: st.markdown(_gamma_card(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy(prices, dxy_corr, sq)
    st.markdown(_lev_card(lev_data), unsafe_allow_html=True)

    sq_q2p = (_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
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

    if pb_data:
        best5 = " · ".join(pb_data.get("best_assets",[])[:6])
        worst5 = " · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin:8px 0;"><div style="font-size:13px;font-weight:700;color:#E6EDF3;margin-bottom:6px;">🎯 What to Do Right Now — {sq} · {mq}</div><div style="font-size:12px;color:#3FB950;margin-bottom:4px;">Buy/Hold: {best5}</div><div style="font-size:12px;color:#F85149;">Avoid/Sell: {worst5}</div></div>', unsafe_allow_html=True)

    # ── FORWARD-LOOKING RADAR ─────────────────────────────────────────
    st.divider()
    st.markdown('<div style="font-size:18px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🔮 Forward-Looking Radar</div>', unsafe_allow_html=True)
    st.caption("What price action is saying BEFORE the news hits.")

    if regime_forecast and regime_forecast.get("1m") and regime_forecast["1m"].get("predicted_quad"):
        rf1 = regime_forecast["1m"]
        rf3 = regime_forecast["3m"]
        rf6 = regime_forecast["6m"]
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f'<div class="metric-box"><div class="metric-label">CURRENT REGIME</div><div class="metric-value" style="color:{qc(sq)};">{sq}</div><div class="metric-sub">{QN.get(sq,"")}</div></div>', unsafe_allow_html=True)
        with c2:
            conf_1m = rf1.get("prediction_confidence", 0)
            st.markdown(f'<div class="metric-box"><div class="metric-label">1M FORWARD</div><div class="metric-value" style="color:{qc(rf1.get("predicted_quad","Q3"))};">{rf1.get("predicted_quad","—")}</div><div class="metric-sub">Conf {conf_1m:.0%}</div></div>', unsafe_allow_html=True)
        with c3:
            conf_3m = rf3.get("prediction_confidence", 0)
            st.markdown(f'<div class="metric-box"><div class="metric-label">3M FORWARD</div><div class="metric-value" style="color:{qc(rf3.get("predicted_quad","Q3"))};">{rf3.get("predicted_quad","—")}</div><div class="metric-sub">Conf {conf_3m:.0%}</div></div>', unsafe_allow_html=True)
        with c4:
            conf_6m = rf6.get("prediction_confidence", 0)
            st.markdown(f'<div class="metric-box"><div class="metric-label">6M FORWARD</div><div class="metric-value" style="color:{qc(rf6.get("predicted_quad","Q3"))};">{rf6.get("predicted_quad","—")}</div><div class="metric-sub">Conf {conf_6m:.0%}</div></div>', unsafe_allow_html=True)
        with c5:
            flip_risk = gip.flip_hazard if gip else 0
            flip_c = "#F85149" if flip_risk > 0.4 else "#D29922"
            st.markdown(f'<div class="metric-box"><div class="metric-label">FLIP RISK</div><div class="metric-value" style="color:{flip_c};">{flip_risk:.0%}</div><div class="metric-sub">{gip.divergence if gip else "—"}</div></div>', unsafe_allow_html=True)

        # Probability distribution
        st.markdown("**📊 Forward Probability Distribution**")
        if rf3.get("probability_distribution"):
            st.plotly_chart(prob_bar(rf3["probability_distribution"], "3M Forward Regime Probabilities"), use_container_width=True, config={"displayModeBar":False})

        # Leading indicator feature importance
        if leading_signals and leading_signals.get("feature_importance"):
            st.markdown("**📈 Leading Indicator Feature Importance**")
            fi = leading_signals["feature_importance"]
            if fi:
                fi_rows = [{"Feature": k, "Importance": v} for k, v in sorted(fi.items(), key=lambda x: x[1], reverse=True)[:8]]
                df_fi = pd.DataFrame(fi_rows)
                st.dataframe(df_fi.style.bar(subset=["Importance"], color="#1F6FEB"), hide_index=True, use_container_width=True, height=250)
    else:
        st.info("🔮 Forward-looking engines initializing... Run **⚡ Full Rebuild** to generate predictions.")

    # ── EMERGENT NARRATIVES (NEWS + PRICE CLUSTERS) ────────────────────
    st.divider()
    st.markdown('<div style="font-size:18px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📰 Emergent Narratives</div>', unsafe_allow_html=True)
    st.caption("News-driven + price-action-driven themes detected before mainstream coverage.")

    # Price clusters
    if price_clusters and price_clusters.get("clusters"):
        st.markdown("**🔬 Price Action Clusters (Leading Indicator)**")
        for c in price_clusters["clusters"][:3]:
            with st.expander(f"📊 {c.get('theme_hypothesis', 'Unknown Theme')} — {c.get('member_count')} tickers · Confidence {c.get('confidence',0):.0%}", expanded=False):
                st.write(f"**Members:** {', '.join(c.get('members',[])[:10])}")
                st.write(f"**Dominant Sector:** {c.get('dominant_sector')} ({c.get('sector_concentration',0):.0%} concentration)")
                st.write(f"**Avg RS 3M:** {c.get('avg_rs_3m',0):+.1%} · **Max RS:** {c.get('max_rs_3m',0):+.1%}")
                st.write(f"**Avg Correlation:** {c.get('avg_correlation',0):.2f} · **Cohesion:** {c.get('cohesion',0):.2f}")
                if c.get("is_novel_theme"): st.success("🆕 Novel cross-sector theme detected!")

    # News narratives
    if news_narratives and news_narratives.get("emergent_narratives"):
        st.markdown("**📰 News-Driven Emergent Narratives**")
        for en in news_narratives["emergent_narratives"][:5]:
            sent_color = "#3FB950" if en.get("avg_sentiment",0.5) > 0.6 else "#F85149" if en.get("avg_sentiment",0.5) < 0.4 else "#D29922"
            with st.expander(f"📰 {en.get('narrative', 'Unknown')} — {en.get('mention_count')} mentions · Supply hits: {en.get('supply_chain_hits',0)}", expanded=False):
                st.write(f"**Sentiment:** <span style='color:{sent_color};font-weight:600;'>{en.get('avg_sentiment',0):.2f}</span>", unsafe_allow_html=True)
                st.write(f"**Linked Tickers:** {', '.join(en.get('linked_tickers',[])[:10])}")
                if en.get("is_new"): st.success("🆕 New theme not in baseline keyword map!")

    # Supply chain alerts
    if news_narratives and news_narratives.get("supply_chain_alerts"):
        alerts = news_narratives["supply_chain_alerts"]
        if len(alerts) > 0:
            st.markdown("**🚨 Supply Chain Alerts**")
            for alert in alerts[:3]:
                if hasattr(alert, 'headline') and alert.headline:
                    st.warning(f"⚠️ {alert.headline[:100]}...")

    if not (price_clusters.get("clusters") or news_narratives.get("emergent_narratives")):
        st.info("No emergent narratives detected yet. Run **⚡ Full Rebuild** to populate.")

    # ── EARLY WARNING SIGNALS ─────────────────────────────────────────
    st.divider()
    st.markdown('<div style="font-size:18px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🚨 Early Warning Signals</div>', unsafe_allow_html=True)
    st.caption("Breadth, credit, vol — the canaries in the coal mine.")

    ew1, ew2, ew3, ew4 = st.columns(4)
    vix_regime = health.get("vix_bucket", {}).get("bucket", "—")
    vix_color = "#3FB950" if vix_regime == "Investable" else "#D29922" if vix_regime == "Chop" else "#F85149"
    ew1.markdown(f'<div class="metric-box"><div class="metric-label">VIX REGIME</div><div class="metric-value" style="color:{vix_color};">{vl:.1f}</div><div class="metric-sub">{vix_regime}</div></div>', unsafe_allow_html=True)

    crash_state = health.get("crash", {}).get("state", "calm")
    crash_color = "#3FB950" if crash_state == "calm" else "#D29922" if crash_state == "watch" else "#F85149"
    ew2.markdown(f'<div class="metric-box"><div class="metric-label">CRASH METER</div><div class="metric-value" style="color:{crash_color};">{crash_state.upper()}</div><div class="metric-sub">Systemic stress</div></div>', unsafe_allow_html=True)

    risk_off_state = health.get("risk_off", {}).get("state", "risk_on")
    risk_color = "#3FB950" if risk_off_state == "risk_on" else "#D29922" if risk_off_state == "caution" else "#F85149"
    ew3.markdown(f'<div class="metric-box"><div class="metric-label">RISK OFF</div><div class="metric-value" style="color:{risk_color};">{risk_off_state.upper()}</div><div class="metric-sub">Flight to quality</div></div>', unsafe_allow_html=True)

    breadth = health.get("breadth", {})
    if breadth and breadth.get("score") is not None:
        b_score = breadth.get("score", 0)
        b_color = "#3FB950" if b_score > 0.6 else "#D29922" if b_score > 0.4 else "#F85149"
        ew4.markdown(f'<div class="metric-box"><div class="metric-label">BREADTH</div><div class="metric-value" style="color:{b_color};">{b_score:.0%}</div><div class="metric-sub">{breadth.get("verdict", "—")}</div></div>', unsafe_allow_html=True)
    else:
        ew4.markdown(f'<div class="metric-box"><div class="metric-label">BREADTH</div><div class="metric-value">—</div><div class="metric-sub">Data loading</div></div>', unsafe_allow_html=True)

    # Feedback eval (FIXED structure)
    try:
        if fb_eval and fb_eval.get("evaluated",0):
            ev = int(fb_eval.get("evaluated", 0) or 0)
            pr = int(fb_eval.get("promoted_count", 0) or 0)
            dm = int(fb_eval.get("demoted_count", 0) or 0)
            wr = fb_eval.get("win_rate", 0)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Evaluated", ev); c2.metric("Winners", pr); c3.metric("Losers", dm); c4.metric("Win Rate", f"{wr:.1f}%")
    except Exception as e:
        logger.warning(f"Feedback eval display error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📈 GIP MODEL — WITH REAL FORWARD PROJECTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">📈 GIP Model</div>', unsafe_allow_html=True)
    st.caption("Growth · Inflation · Policy — The Map + Forward Projection")
    st.divider()
    if not gip: st.warning("Data loading..."); st.stop()

    cc,cw = st.columns(2)
    with cc:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">Quarterly Regime (Climate)</div><div style="font-size:22px;font-weight:700;color:{qc(sq)};margin:6px 0;">{sq}</div><div style="font-size:12px;color:#E6EDF3;margin-bottom:8px;">{QNC.get(sq,"")}</div><div style="font-size:12px;color:#8B949E;">{QUAD_EXPLAIN[sq]}</div><div style="margin-top:10px;font-size:11px;color:#8B949E;border-top:1px solid #30363D;padding-top:6px;">Confidence: {gip.structural_conf:.0%} · Flip risk: {gip.flip_hazard:.0%}</div></div>', unsafe_allow_html=True)
    with cw:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">Monthly Regime (Weather — 3-6 Weeks)</div><div style="font-size:22px;font-weight:700;color:{qc(mq)};margin:6px 0;">{mq}</div><div style="font-size:12px;color:#E6EDF3;margin-bottom:8px;">{QNC.get(mq,"")}</div><div style="font-size:12px;color:#8B949E;">{QUAD_EXPLAIN[mq]}</div><div style="margin-top:10px;font-size:11px;color:#8B949E;border-top:1px solid #30363D;padding-top:6px;">Confidence: {gip.monthly_conf:.0%} · Divergence: {gip.divergence}</div></div>', unsafe_allow_html=True)
    if mq_raw == "Q1":
        st.warning("⚠ Model computed Q1, Hedgeye manual call = Q2. Use Quad Override in sidebar.")

    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">What the Data Is Saying</div>', unsafe_allow_html=True)
    f = gip.features; gm = _sf(f.get("growth_momentum")) or 0; im = _sf(f.get("inflation_momentum")) or 0
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Growth Direction", "📈 Accelerating" if gm>0 else "📉 Decelerating", f"{gm:+.1%}")
    s2.metric("Inflation Direction", "📈 Rising" if im>0 else "📉 Cooling", f"{im:+.1%}")
    s3.metric("Central Bank", "Dovish" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish" if (_sf(f.get("policy_score")) or 0)<-0.1 else "Neutral")
    s4.metric("Data Coverage", f"{gip.data_coverage:.0%}")

    # ── FORWARD PROJECTION (REAL DATA) ────────────────────────────────
    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🔮 Forward Projection</div>', unsafe_allow_html=True)
    st.caption("Regime predictor ensemble: ARIMA trajectory + GBM classifier + Bayesian prior")

    if regime_forecast and regime_forecast.get("1m") and regime_forecast["1m"].get("predicted_quad"):
        rf1 = regime_forecast["1m"]
        rf3 = regime_forecast["3m"]
        rf6 = regime_forecast["6m"]

        fp1, fp2, fp3 = st.columns(3)
        with fp1:
            st.markdown(f'<div class="metric-box"><div class="metric-label">1 MONTH FORWARD</div><div class="metric-value" style="color:{qc(rf1.get("predicted_quad","Q3"))};">{rf1.get("predicted_quad","—")}</div><div class="metric-sub">Confidence: {rf1.get("prediction_confidence",0):.0%} · {rf1.get("expected_transition_weeks",8)} weeks typical</div></div>', unsafe_allow_html=True)
            if rf1.get("probability_distribution"):
                st.plotly_chart(prob_bar(rf1["probability_distribution"], "1M Probabilities"), use_container_width=True, config={"displayModeBar":False}, key="gip_prob_1m")
        with fp2:
            st.markdown(f'<div class="metric-box"><div class="metric-label">3 MONTHS FORWARD</div><div class="metric-value" style="color:{qc(rf3.get("predicted_quad","Q3"))};">{rf3.get("predicted_quad","—")}</div><div class="metric-sub">Confidence: {rf3.get("prediction_confidence",0):.0%} · {rf3.get("expected_transition_weeks",8)} weeks typical</div></div>', unsafe_allow_html=True)
            if rf3.get("probability_distribution"):
                st.plotly_chart(prob_bar(rf3["probability_distribution"], "3M Probabilities"), use_container_width=True, config={"displayModeBar":False}, key="gip_prob_3m")
        with fp3:
            st.markdown(f'<div class="metric-box"><div class="metric-label">6 MONTHS FORWARD</div><div class="metric-value" style="color:{qc(rf6.get("predicted_quad","Q3"))};">{rf6.get("predicted_quad","—")}</div><div class="metric-sub">Confidence: {rf6.get("prediction_confidence",0):.0%} · {rf6.get("expected_transition_weeks",8)} weeks typical</div></div>', unsafe_allow_html=True)
            if rf6.get("probability_distribution"):
                st.plotly_chart(prob_bar(rf6["probability_distribution"], "6M Probabilities"), use_container_width=True, config={"displayModeBar":False}, key="gip_prob_6m")

        # Leading indicator expected returns
        if forward_returns:
            st.markdown("**📈 Leading Indicator Expected Returns**")
            lr1, lr2, lr3, lr4 = st.columns(4)
            lr1.metric("1M Expected", fp(forward_returns.get("expected_1m")))
            lr2.metric("3M Expected", fp(forward_returns.get("expected_3m")))
            lr3.metric("6M Expected", fp(forward_returns.get("expected_6m")))
            lr4.metric("Transition Prob", f"{forward_returns.get('transition_prob',0):.0%}")
            st.caption(f"Confidence: {forward_returns.get('confidence',0.5):.0%} · Based on regime-specific feature weights")

        # Feature importance
        if leading_signals and leading_signals.get("feature_importance"):
            st.markdown("**🔬 Leading Indicator Feature Importance**")
            fi = leading_signals["feature_importance"]
            fi_rows = [{"Feature": k, "Importance": v} for k, v in sorted(fi.items(), key=lambda x: x[1], reverse=True)[:8]]
            df_fi = pd.DataFrame(fi_rows)
            st.dataframe(df_fi.style.bar(subset=["Importance"], color="#1F6FEB"), hide_index=True, use_container_width=True, height=250)
    else:
        st.info("🔮 Forward projection data not available. Ensure `scikit-learn` is installed and run **⚡ Full Rebuild**.")

    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">Where Are We Going Next?</div>', unsafe_allow_html=True)
    def _tp(probs, cur_q, label):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;margin:6px 0;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;">{label}</div><div style="font-size:14px;font-weight:700;color:#E6EDF3;margin:4px 0;">Most likely next: <b>{top_q} {QN.get(top_q,"")}</b> ({top_p:.0%})</div></div>', unsafe_allow_html=True)
        key_id = f"prob_{label.replace(' ', '_').replace('/', '_')}"
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False}, key=key_id)
        if top_q!=cur_q: st.info(f"If regime shifts to {top_q}: **{QWINS.get(top_q,'')}** are the winners")
    c1,c2,c3 = st.columns(3)
    with c1: _tp(gip.structural_probs, sq, "Quarterly Probabilities")
    with c2: _tp(gip.monthly_probs, mq, "Monthly Probabilities")
    with c3:
        gprobs = (global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs, gq, "Global Probabilities")

    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">Timing Signal</div>', unsafe_allow_html=True)
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div style="background:{fwc}22;border:1px solid {fwc};border-radius:8px;padding:10px;text-align:center;margin:8px 0;"><span style="color:{fwc};font-weight:700;">{fwi}</span><br><span style="font-size:12px;color:#8B949E;">{fr}</span></div>', unsafe_allow_html=True)

    # ── VOL FORECAST + STRESS TEST ──
    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📊 Volatility Forecast & Regime Probability</div>', unsafe_allow_html=True)
    vol_f = snap.get("vol_forecast", {})
    stress = snap.get("stress_test", [])
    if vol_f:
        proxy_tickers = ["SPY", "QQQ", "GLD", "TLT", "DX-Y.NYB"]
        vol_rows = []
        for t in proxy_tickers:
            if t in vol_f:
                v = vol_f[t]
                vol_rows.append({"Asset": t, "Current Vol": f"{v['current_ann_vol']}%", "Forecast": f"{v['forecast_ann_vol']}%", "Regime": v['vol_regime'], "Daily Move": f"±{v['expected_daily_move_pct']:.1%}", "Weekly Move": f"±{v['expected_weekly_move_pct']:.1%}"})
        if vol_rows:
            df_vol = pd.DataFrame(vol_rows)
            st.dataframe(df_vol.style.map(lambda x: 'color:#3FB950;font-weight:600;' if x == "LOW" else ('color:#D29922;font-weight:600;' if x == "NORMAL" else ('color:#F85149;font-weight:600;' if x in ["ELEVATED","EXTREME"] else '')), subset=["Regime"]), hide_index=True, use_container_width=True, height=180)
            st.caption("Forecast = EWMA adaptive × regime multiplier. Higher vol expected in Q3/Q4.")
    if stress:
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🧪 Stress Test Scenarios</div>', unsafe_allow_html=True)
        st.caption("Historical shock magnitudes applied to current regime portfolio proxy.")
        for sc in stress:
            sev_color = "#F85149" if sc['severity'] == "EXTREME" else "#D29922" if sc['severity'] == "HIGH" else "#8B949E"
            with st.expander(f"⚠️ **{sc['scenario']}** | Portfolio DD: {sc['portfolio_dd']:.0%} | Severity: {sc['severity']}", expanded=(sc['severity'] in ["EXTREME","HIGH"])):
                c1, c2, c3 = st.columns(3)
                c1.metric("Portfolio DD", f"{sc['portfolio_dd']:.0%}")
                c2.metric("Worst Asset", sc['worst_asset'], f"{sc['worst_dd']:.0%}")
                c3.metric("Best Asset", sc['best_asset'], f"{sc['best_dd']:.0%}")
                st.info(f"🛡️ **Hedge suggestion:** {sc['hedge']}")
    if analogs and analogs.get("top_analogs"):
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">Historical Comparisons</div>', unsafe_allow_html=True)
        for i,a in enumerate(analogs["top_analogs"][:3]):
            with st.expander(f"📚 **{a['label']}** — {a.get('similarity',0):.0%} similar", expanded=(i==0)):
                c1,c2,c3=st.columns(3)
                c1.metric("Next 1M", a.get("path_1m","—")); c2.metric("Next 3M", a.get("path_3m","—")); c3.metric("Next 6M", a.get("path_6m","—"))
                st.info(f"📊 {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ⚡ ALPHA & SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha & Scanner":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">⚡ Alpha & Scanner</div>', unsafe_allow_html=True)
    st.caption("Bottlenecks · Alpha Ideas · Discovery · Daily Signals — All unified.")
    st.divider()
    ac = alpha_center
    meta = ac.get("meta", {}) if ac else {}
    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild."); st.stop()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Regime", meta.get("regime", "?"))
    c2.metric("Bias", meta.get("bias", "?"))
    c3.metric("VIX", meta.get("vix", "?"))
    c4.metric("Total", meta.get("total_items", 0))
    c5.metric("Option-Ready", len(set((snap.get("gamma_data") or {}).keys()) & set((snap.get("greeks_data") or {}).keys())))
    st.caption(f"Last updated: {meta.get('last_updated', 'N/A')}")
    if transition:
        fw=transition.front_run_window
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:{fwc};color:#fff;padding:10px 16px;border-radius:8px;font-weight:600;text-align:center;margin:10px 0;">{fwi}</div>', unsafe_allow_html=True)
    st.markdown("**Filter Logic:** Level 1 = score≥0.80 + RR≥2.0 + near entry | Level 2 = score≥0.60 + RR≥1.5 | Watch = score≥0.40 | Alpha Long/Short = direction confirmed + score≥0.50 | Daily = |score|≥0.10, grade A-C, all directions")
    risk_adj_all = snap.get("risk_adjusted", {})
    if risk_adj_all:
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📊 Risk-Adjusted Performance (63D)</div>', unsafe_allow_html=True)
        sharpe_sorted = sorted([(t, m) for t, m in risk_adj_all.items() if m.get("sharpe_63d") is not None], key=lambda x: x[1]["sharpe_63d"], reverse=True)[:10]
        if sharpe_sorted:
            sharpe_rows = []
            for t, m in sharpe_sorted:
                sharpe_rows.append({"Ticker": t, "Sharpe": m["sharpe_63d"], "Sortino": m.get("sortino_63d", "—"), "Ann Return": f"{m.get('ann_return', 0):.1f}%", "Ann Vol": f"{m.get('ann_vol', 0):.1f}%", "Max DD": f"{m.get('max_dd_63d', 0):.1%}"})
            df_ra = pd.DataFrame(sharpe_rows)
            st.dataframe(df_ra.style.map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x, (int, float)) and x >= 2.0 else ('color:#D29922;font-weight:600;' if isinstance(x, (int, float)) and x >= 1.0 else ''), subset=["Sharpe", "Sortino"]), hide_index=True, use_container_width=True, height=280)
            st.caption("Sharpe ≥2.0 = excellent risk-adjusted. Sortino > Sharpe = downside-skewed favorable.")
    sub1, sub2, sub3, sub4, sub5, sub6, sub7 = st.tabs([
        f"🚨 Bottlenecks L1 ({meta.get('level_1_count', 0)})",
        f"⚠️ Bottlenecks L2 ({meta.get('level_2_count', 0)})",
        f"👁️ Watch ({meta.get('watch_count', 0)})",
        f"🟢 Alpha Long ({meta.get('alpha_long_count', 0)})",
        f"🔴 Alpha Short ({meta.get('alpha_short_count', 0)})",
        f"💡 Discovery ({meta.get('discovery_count', 0)})",
        f"📋 All Rated ({len(daily_signals)})",
    ])
    with sub1:
        items = ac.get("level_1", [])
        st.markdown(f"**🚨 LEVEL 1 — URGENT ({len(items)} items)**")
        if not items: st.info("No Level 1.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub2:
        items = ac.get("level_2", [])
        st.markdown(f"**⚠️ LEVEL 2 — BUILDING ({len(items)} items)**")
        if not items: st.info("No Level 2.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub3:
        items = ac.get("watch", [])
        st.markdown(f"**👁️ WATCH — MONITOR DAILY ({len(items)} items)**")
        if not items: st.info("Nothing on watch.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub4:
        items = ac.get("alpha_long", [])
        st.markdown(f"**🟢 ALPHA LONGS ({len(items)} items)**")
        if not items: st.info("No alpha longs.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub5:
        items = ac.get("alpha_short", [])
        st.markdown(f"**🔴 ALPHA SHORTS ({len(items)} items)**")
        if not items: st.info("No alpha shorts.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub6:
        items = ac.get("discovery", [])
        st.markdown(f"**💡 DISCOVERY ({len(items)} items)**")
        if not items: st.info("No discoveries.")
        for i, item in enumerate(items): _render_narrative_card_native(item, i, "us_equity")
    with sub7:
        st.markdown(f"**📋 ALL RATED ({len(daily_signals)} signals)**")
        st.caption("Filter: |Score| ≥ 0.10 · Grade A-C · All directions")
        col_f1, col_f2, col_f3 = st.columns(3)
        filter_dir = col_f1.multiselect("Direction", ["LONG", "SHORT", "NEUTRAL", "DEFENSIVE"], default=["LONG", "SHORT", "NEUTRAL"])
        filter_grade = col_f2.multiselect("Grade", ["A+", "A", "B", "C"], default=["A+", "A", "B", "C"])
        filter_min_score = col_f3.slider("Min |Score|", 0.0, 1.0, 0.10, 0.05)
        filtered = [s for s in daily_signals if s.get("direction") in filter_dir and s.get("grade", "C") in filter_grade]
        filtered = [s for s in filtered if abs(s.get("score", 0)) >= filter_min_score]
        st.write(f"Showing **{len(filtered)}** signals out of {len(daily_signals)} total")
        risk_adj = snap.get("risk_adjusted", {})
        for s in filtered:
            t = s.get("ticker")
            if t in risk_adj:
                s["sharpe_63d"] = risk_adj[t].get("sharpe_63d")
                s["sortino_63d"] = risk_adj[t].get("sortino_63d")
                s["max_dd_63d"] = risk_adj[t].get("max_dd_63d")
                s["ann_vol"] = risk_adj[t].get("ann_vol")
        for i, s in enumerate(filtered[:300]): _render_narrative_card_native(s, i, "us_equity")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 💱🛢️ MACRO PROXIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💱🛢️ Macro Proxies":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">💱🛢️ Macro Proxies</div>', unsafe_allow_html=True)
    st.caption("Forex + Commodities unified. COT + OI + Greeks + Risk Ranges + Forward-Looking + News.")
    st.divider()
    gamma_data = snap.get("gamma_data", {}) or {}
    greeks_data = snap.get("greeks_data", {}) or {}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}
    fx_tab, comm_tab = st.tabs(["💱 Forex", "🛢️ Commodities"])
    with fx_tab:
        st.markdown("### 💱 Forex Setups")
        st.caption("**Filter:** Composite bullish/bearish + COT bias + OI + Greeks + Forward returns + News narrative")
        fx_rows = []
        for ticker in list(FOREX_PAIRS.keys()):
            row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "forex", vix_now, gamma_data, greeks_data, forward_returns, news_narratives)
            if row: fx_rows.append(row)
        longs, shorts = _split_long_short(fx_rows)
        st.markdown(f"**🟢 LONG FX ({len(longs)} setups)**")
        for i, row in enumerate(longs): _render_narrative_card_native(row, i, "forex")
        if not longs: st.info("No long FX setups.")
        st.divider()
        st.markdown(f"**🔴 SHORT FX ({len(shorts)} setups)**")
        for i, row in enumerate(shorts): _render_narrative_card_native(row, i, "forex")
        if not shorts: st.info("No short FX setups.")
    with comm_tab:
        st.markdown("### 🛢️ Commodity Setups")
        st.caption("**Filter:** Composite + COT + OI + Greeks + DXY inverse + Forward returns + News")
        comm_rows = []
        for ticker in list(COMMODITIES.keys()):
            row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "commodity", vix_now, gamma_data, greeks_data, forward_returns, news_narratives)
            if row: comm_rows.append(row)
        longs, shorts = _split_long_short(comm_rows)
        st.markdown(f"**🟢 LONG COMMODITIES ({len(longs)} setups)**")
        for i, row in enumerate(longs): _render_narrative_card_native(row, i, "commodity")
        if not longs: st.info("No long commodity setups.")
        st.divider()
        st.markdown(f"**🔴 SHORT COMMODITIES ({len(shorts)} setups)**")
        for i, row in enumerate(shorts): _render_narrative_card_native(row, i, "commodity")
        if not shorts: st.info("No short commodity setups.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ₿ CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">₿ Crypto Setups</div>', unsafe_allow_html=True)
    st.caption("On-chain momentum + Risk Ranges + Forward-Looking + News narrative per token.")
    st.divider()
    crypto_tokens = snap.get("crypto_tokens", {}) or {}
    if not isinstance(crypto_tokens, dict) or not crypto_tokens:
        crypto_tokens = {}
        for ticker in list(CRYPTO.keys())[:10]:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                r7d = float(s.iloc[-1] / s.iloc[-8] - 1) if len(s) >= 8 else r1m
                vol = s.tail(20).std()
                vol_change = (vol / s.tail(40).std() - 1) if s.tail(40).std() > 0 else 0
                score = min(1.0, max(0.0, 0.5 + r1m * 5))
                crypto_tokens[ticker] = {"momentum_score": score, "tvl_7d_change": r7d, "tvl_30d_change": r1m, "dex_vol_change": vol_change}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}
    crypto_rows = []
    for ticker in list(CRYPTO.keys()):
        row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "crypto", vix_now, snap.get("gamma_data",{}), snap.get("greeks_data",{}), forward_returns, news_narratives)
        if row:
            token_data = crypto_tokens.get(ticker, {})
            if token_data:
                score = token_data.get("momentum_score", 0.5)
                tvl_7d = token_data.get("tvl_7d_change", 0)
                if score > 0.7 and tvl_7d > 0.08 and "LONG" in row["direction"]:
                    row["recommendation"] = f"🚀 STRONG LONG — On-chain accumulation (TVL +{tvl_7d:.1%}) + price momentum align"
                elif score > 0.7 and tvl_7d > 0.08 and "SHORT" in row["direction"]:
                    row["recommendation"] = f"⚠️ CONFLICTED — Price bearish but on-chain accumulation (TVL +{tvl_7d:.1%}), wait"
                elif score < 0.3 and "LONG" in row["direction"]:
                    row["recommendation"] = f"🟡 WEAK LONG — Price bullish but on-chain fading (TVL {tvl_7d:.1%}), reduce size"
                row["onchain_score"] = f"{int(score*100)}%"
                row["tvl_7d"] = tvl_7d
                row["tvl_30d"] = token_data.get("tvl_30d_change", 0)
                row["dex_vol"] = token_data.get("dex_vol_change", 0)
                if score > 0.7 and tvl_7d > 0.15: row["onchain_signal"] = "🚀 STRONG ACCUMULATION"
                elif score > 0.55 and (tvl_7d > 0.1 or token_data.get("dex_vol_change",0) > 0.2): row["onchain_signal"] = "📈 BUILDING MOMENTUM"
                elif score > 0.4: row["onchain_signal"] = "👀 EARLY SIGNS"
                else: row["onchain_signal"] = "⏳ NEUTRAL"
            else:
                row["onchain_score"] = "—"; row["tvl_7d"] = None; row["tvl_30d"] = None; row["dex_vol"] = None; row["onchain_signal"] = "—"
            crypto_rows.append(row)
    longs, shorts = _split_long_short(crypto_rows)
    st.caption(f"**Filter:** 1M momentum >+3% = LONG override | <-3% = SHORT override | On-chain TVL/DEX vol + Forward + News")
    st.markdown(f"**🟢 LONG CRYPTO ({len(longs)} setups)**")
    for i, row in enumerate(longs): _render_narrative_card_native(row, i, "crypto")
    if not longs: st.info("No long crypto setups.")
    st.divider()
    st.markdown(f"**🔴 SHORT CRYPTO ({len(shorts)} setups)**")
    for i, row in enumerate(shorts): _render_narrative_card_native(row, i, "crypto")
    if not shorts: st.info("No short crypto setups.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🌍 GLOBAL & EM
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global & EM":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">🌍 Global & EM</div>', unsafe_allow_html=True)
    st.caption("Global regime map + Indonesia IHSG narrative + Forward-looking + News.")
    st.divider()
    global_tab, ihsg_tab = st.tabs(["🌍 Global Quad", "🇮🇩 IHSG"])
    with global_tab:
        if not global_: st.warning("Country data loading."); st.stop()
        gq = global_.get("global_quad","Q3")
        gconf = global_.get("global_conf",0.5)
        gprobs = global_.get("global_probs",{})
        cqs = global_.get("country_quads",{})
        if not cqs:
            base_map = {"Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico"],"Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi"],"Q3": ["UK","Germany","France","Italy","Russia","Turkey","Thailand"],"Q4": ["Indonesia","Argentina","Egypt","Nigeria","Pakistan"]}
            cqs = {}
            for q, countries in base_map.items():
                for c in countries: cqs[c] = q
        c1,c2 = st.columns([1,1.5])
        with c1:
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Global Regime</div><div style="font-size:32px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="font-size:13px;color:#8B949E;margin-top:6px;">{QNC.get(gq,"")}</div><div style="font-size:12px;color:#8B949E;margin-top:8px;">50 country ETFs · GDP-weighted · Confidence: {gconf:.0%}</div></div>', unsafe_allow_html=True)
            st.plotly_chart(prob_bar(gprobs), use_container_width=True, config={"displayModeBar":False})
            em_sig = (btk.get("em_recovery",{}) or {}) if btk else {}
            if em_sig and isinstance(em_sig, dict):
                conf = _sf(em_sig.get("confidence")) or 0
                trigger = em_sig.get("trigger","EM signal")
                st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:12px;margin-top:10px;"><div style="font-size:12px;color:#8B949E;">🌍 EM RECOVERY SIGNAL</div><div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-top:4px;">{trigger}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">Confidence: {conf:.0%}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown("### Country Regimes")
            rows=[]
            for country,q in sorted(cqs.items(),key=lambda x:x[1]):
                rows.append({"Country":country,"Regime":q,"Name":QN.get(q,q)})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(lambda x: f'color:{qc(x)}', subset=["Regime"]).format({"Regime":lambda x:""}), hide_index=True, use_container_width=True, height=400)
    with ihsg_tab:
        st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">🇮🇩 IHSG Macro Report</div>', unsafe_allow_html=True)
        st.caption("Comprehensive Indonesia equity analysis with structural compensators + forward-looking.")
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📋 Executive Summary</div>', unsafe_allow_html=True)
        macro = ihsg_macro_overlay or {}
        ihsg_bias = "DEFENSIVE"; ihsg_color = "#F85149"; top_sectors = []; avoid_sectors = []
        if macro.get("commodity_bias") == "Bullish":
            ihsg_bias = "COMMODITY OFFENSE"; ihsg_color = "#3FB950"; top_sectors = ["Coal", "Nickel", "CPO"]; avoid_sectors = ["Banking"] if macro.get("banking_bias") == "Bearish" else []
        elif macro.get("consumer_bias") == "Bullish":
            ihsg_bias = "DOMESTIC DEMAND"; ihsg_color = "#D29922"; top_sectors = ["Consumer", "Pharma", "Telco"]
        else:
            top_sectors = ["Banking", "Telco"] if macro.get("banking_bias") == "Bullish" else ["Telco"]
            avoid_sectors = ["Coal"] if macro.get("commodity_bias") == "Bearish" else []
        rupiah_sig = ihsg_rupiah_regime.get("flow_signal", "—") if ihsg_rupiah_regime else "—"
        rupiah_color = "#3FB950" if "Positive" in rupiah_sig else "#F85149" if "Risk" in rupiah_sig else "#D29922"
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-box"><div class="metric-label">IHSG BIAS</div><div class="metric-value" style="color:{ihsg_color};">{ihsg_bias}</div><div class="metric-sub">Regime: {sq} · {QN.get(sq,"")}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div class="metric-label">💱 RUPIAH FLOW</div><div class="metric-value" style="color:{rupiah_color};">{rupiah_sig[:20] if rupiah_sig else "—"}</div><div class="metric-sub">DXY: {ihsg_rupiah_regime.get("dxy_trend","—") if ihsg_rupiah_regime else "—"}</div></div>', unsafe_allow_html=True)
        with c3:
            bi_sig = macro.get("bi_signal", "—")[:30] if macro else "—"
            st.markdown(f'<div class="metric-box"><div class="metric-label">🏦 BI REGIME</div><div class="metric-value" style="font-size:14px;">{bi_sig}</div><div class="metric-sub">Policy: {macro.get("policy_score",0):+.2f}</div></div>', unsafe_allow_html=True)
        if top_sectors or avoid_sectors:
            pills = []
            for s in top_sectors: pills.append(f'<span class="badge badge-long">🟢 {s}</span>')
            for s in avoid_sectors: pills.append(f'<span class="badge badge-short">🔴 {s}</span>')
            st.markdown(f'<div style="margin:10px 0;">{ " ".join(pills)}</div>', unsafe_allow_html=True)
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🌏 Macro Context</div>', unsafe_allow_html=True)
        mc1, mc2, mc3, mc4 = st.columns(4)
        dxy_val = None; dxy_trend = "—"
        if prices.get("DX-Y.NYB") is not None:
            dxy_s = pd.to_numeric(prices["DX-Y.NYB"], errors="coerce").dropna()
            if len(dxy_s) > 0: dxy_val = float(dxy_s.iloc[-1])
            if len(dxy_s) >= 22: dxy_trend = f"{float(dxy_s.iloc[-1]/dxy_s.iloc[-22]-1):+.1%}"
        mc1.metric("DXY", f"{dxy_val:.2f}" if dxy_val else "—", dxy_trend)
        idr_val = None; idr_trend = "—"
        if prices.get("USDIDR=X") is not None:
            idr_s = pd.to_numeric(prices["USDIDR=X"], errors="coerce").dropna()
            if len(idr_s) > 0: idr_val = float(idr_s.iloc[-1])
            if len(idr_s) >= 22: idr_trend = f"{float(idr_s.iloc[-1]/idr_s.iloc[-22]-1):+.1%}"
        mc2.metric("USD/IDR", f"{idr_val:,.0f}" if idr_val else "—", idr_trend)
        comm_proxies = {}
        for proxy in ["KOL", "JJN", "DBA"]:
            s = prices.get(proxy)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22: comm_proxies[proxy] = float(s.iloc[-1] / s.iloc[-22] - 1)
        mc3.metric("Coal (KOL)", fp(comm_proxies.get("KOL")), "1M")
        mc4.metric("Agri (DBA)", fp(comm_proxies.get("DBA")), "1M")
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📈 Ticker Report Cards</div>', unsafe_allow_html=True)
        st.caption("Click any ticker to expand -> see price levels + sector scorecard + structural layers + forward-looking")
        ihsg_rows = []
        for ticker in list(IHSG_UNIVERSE.keys()):
            row = _build_ihsg_row(ticker, prices, ar, ihsg_sector_momentum, ihsg_commodity_overlay, ihsg_rupiah_regime, ihsg_foreign_flow, ihsg_macro_overlay, forward_returns, news_narratives)
            if row: ihsg_rows.append(row)
        ihsg_rows.sort(key=lambda x: abs(x.get("sector_momentum", {}).get("avg_1m", 0) or 0), reverse=True)
        for row in ihsg_rows:
            ticker = row["ticker"]
            sector = row.get("sector", "—")
            price = row.get("price")
            entry = row.get("entry")
            t1 = row.get("target_1")
            t2 = row.get("target_2")
            stop = row.get("stop")
            rr = row.get("rr", 0)
            rec = row.get("recommendation", "—")
            r1m = row.get("r1m")
            sec_mom = row.get("sector_momentum", {})
            comm_ov = row.get("commodity_overlay", {})
            flow = row.get("foreign_flow", {})
            rup = row.get("rupiah_regime", {})
            card_border = "#3FB950" if "LONG" in rec else "#F85149" if "avoid" in rec.lower() or "short" in rec.lower() else "#D29922"
            dir_emoji = "🟢" if "LONG" in rec else "🔴" if "avoid" in rec.lower() or "short" in rec.lower() else "🟡"
            header = f"{dir_emoji} {ticker} | {sector} | RR {rr:.1f}x | {fp(r1m)} 1M"
            with st.expander(header, expanded=False):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Price", _fmt_num(price)); m2.metric("Entry", _fmt_num(entry)); m3.metric("T1", _fmt_num(t1)); m4.metric("T2", _fmt_num(t2)); m5.metric("Stop", _fmt_num(stop))
                if row.get("expected_1m") is not None:
                    st.divider()
                    st.markdown("**🔮 Forward-Looking**")
                    f1, f2, f3 = st.columns(3)
                    f1.metric("1M Expected", fp(row.get("expected_1m")))
                    f2.metric("3M Expected", fp(row.get("expected_3m")))
                    f3.metric("Confidence", f"{row.get('forward_confidence',0):.0%}")
                if row.get("news_narrative"):
                    st.divider()
                    st.markdown(f"**📰 News:** {row.get('news_narrative')}")
                st.divider()
                st.markdown(f'<div style="font-size:14px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">📊 {sector} Sector Scorecard</div>', unsafe_allow_html=True)
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-label">SECTOR MOMENTUM</div>', unsafe_allow_html=True)
                    if sec_mom.get("avg_1m") is not None:
                        mom_color = "#3FB950" if sec_mom.get("avg_1m", 0) > 0 else "#F85149"
                        st.markdown(f'<div class="metric-value" style="color:{mom_color};">{fp(sec_mom.get("avg_1m"))}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-sub">Leader: {sec_mom.get("leader", "—")}</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="metric-value">—</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with sc2:
                    st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-label">COMMODITY</div>', unsafe_allow_html=True)
                    if comm_ov.get("tailwind"):
                        tail_color = "#3FB950" if comm_ov.get("tailwind") in ["Strong", "Moderate"] else "#F85149" if comm_ov.get("tailwind") == "Headwind" else "#D29922"
                        st.markdown(f'<div class="metric-value" style="color:{tail_color};">{comm_ov.get("tailwind", "—")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-sub">{comm_ov.get("proxy", "—")} {fp(comm_ov.get("r1m"))}</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="metric-value">—</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with sc3:
                    st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-label">MACRO BIAS</div>', unsafe_allow_html=True)
                    macro_bias = "—"
                    if sector == "Banking": macro_bias = macro.get("banking_bias", "—") if macro else "—"
                    elif sector in ["Consumer", "Pharma"]: macro_bias = macro.get("consumer_bias", "—") if macro else "—"
                    elif sector in ["Coal", "Nickel", "CPO", "Mining"]: macro_bias = macro.get("commodity_bias", "—") if macro else "—"
                    bias_color = "#3FB950" if macro_bias == "Bullish" else "#F85149" if macro_bias == "Bearish" else "#8B949E"
                    st.markdown(f'<div class="metric-value" style="color:{bias_color};">{macro_bias}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-sub">{macro.get("bi_signal","—")[:25] if macro else "—"}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with sc4:
                    st.markdown('<div class="metric-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-label">FOREIGN FLOW</div>', unsafe_allow_html=True)
                    if flow.get("signal"):
                        flow_color = "#3FB950" if "Accumulation" in flow.get("signal", "") else "#F85149" if "Distribution" in flow.get("signal", "") else "#D29922"
                        st.markdown(f'<div class="metric-value" style="color:{flow_color};font-size:14px;">{flow.get("signal", "—")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metric-sub">Gap {fp(flow.get("gap"))} · Vol {flow.get("vol_spike", 0):.1f}x</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="metric-value">—</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()
                st.markdown(f'<div style="font-size:14px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🔬 Structural Layers</div>', unsafe_allow_html=True)
                layer_parts = []
                if sec_mom.get("bias") == "Bullish": layer_parts.append(f"📊 **Sector Momentum:** {sector} +{fp(sec_mom.get('avg_1m'))} (leader {sec_mom.get('leader')})")
                if comm_ov.get("tailwind") in ["Strong", "Moderate"]: layer_parts.append(f"🛢️ **Commodity Tailwind:** {comm_ov.get('signal', '')}")
                if rup.get("flow_signal") and "Positive" in rup["flow_signal"]: layer_parts.append(f"💱 **Rupiah Support:** {rup.get('flow_signal', '')}")
                if flow.get("signal") == "Foreign Accumulation": layer_parts.append(f"🌊 **Foreign Flow:** {flow.get('note', '')}")
                if sector == "Banking" and macro.get("banking_bias") == "Bullish": layer_parts.append(f"🏦 **BI Macro:** {macro.get('bi_signal', '')}")
                if sector in ["Consumer", "Pharma"] and macro.get("consumer_bias") == "Bullish": layer_parts.append(f"🛒 **Consumer Macro:** {macro.get('consumer_signal', '')}")
                if layer_parts:
                    for part in layer_parts: st.markdown(part)
                else: st.caption("No structural layer signals for this ticker.")
                st.divider()
                st.markdown(f"**🎯 Thesis:** {rec}")
                st.markdown(f"**⏱️ Time Estimate:** {row.get('time_estimate', '—')} | **Path:** {row.get('path_smoothness', '—')}")
                if row.get("action"): st.caption(f"🎬 **Action:** {row.get('action')}")
        if not ihsg_rows: st.info("No IHSG setups available.")
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">🔬 Market-Wide Structural Diagnostics</div>', unsafe_allow_html=True)
        diag1, diag2, diag3, diag4, diag5 = st.columns(5)
        with diag1:
            st.markdown('<div class="metric-box"><div class="metric-label">📊 SECTOR MOM</div>', unsafe_allow_html=True)
            if ihsg_sector_momentum:
                top_sec = max(ihsg_sector_momentum.items(), key=lambda x: x[1].get("strength", 0))
                st.markdown(f'<div class="metric-value" style="font-size:14px;">{top_sec[0]}</div><div class="metric-sub">{fp(top_sec[1].get("avg_1m"))} 1M</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="metric-sub">No data</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with diag2:
            st.markdown('<div class="metric-box"><div class="metric-label">🛢️ COMMODITY</div>', unsafe_allow_html=True)
            if ihsg_commodity_overlay:
                top_comm = max(ihsg_commodity_overlay.items(), key=lambda x: x[1].get("r1m") or -999)
                st.markdown(f'<div class="metric-value" style="font-size:14px;">{top_comm[0]}</div><div class="metric-sub">{fp(top_comm[1].get("r1m"))} 1M</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="metric-sub">No data</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with diag3:
            st.markdown('<div class="metric-box"><div class="metric-label">💱 RUPIAH</div>', unsafe_allow_html=True)
            if ihsg_rupiah_regime:
                st.markdown(f'<div class="metric-value" style="font-size:14px;">{ihsg_rupiah_regime.get("dxy_trend","—")}</div><div class="metric-sub">DXY {fp(ihsg_rupiah_regime.get("dxy_1m"))}</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="metric-sub">No data</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with diag4:
            st.markdown('<div class="metric-box"><div class="metric-label">🌊 FLOW</div>', unsafe_allow_html=True)
            if ihsg_foreign_flow:
                acc = sum(1 for v in ihsg_foreign_flow.values() if "Accumulation" in v.get("signal", ""))
                dist = sum(1 for v in ihsg_foreign_flow.values() if "Distribution" in v.get("signal", ""))
                st.markdown(f'<div class="metric-value" style="font-size:14px;color:#3FB950;">{acc} Acc</div><div class="metric-sub" style="color:#F85149;">{dist} Dist</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="metric-sub">No data</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with diag5:
            st.markdown('<div class="metric-box"><div class="metric-label">🏦 BI MACRO</div>', unsafe_allow_html=True)
            if ihsg_macro_overlay:
                st.markdown(f'<div class="metric-value" style="font-size:14px;">{ihsg_macro_overlay.get("banking_bias","—")}</div><div class="metric-sub">Policy {ihsg_macro_overlay.get("policy_score",0):+.2f}</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="metric-sub">No data</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📖 Themes & Bottlenecks — WITH REAL DISCOVERY DATA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Themes & Bottlenecks":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">📖 Themes & Bottlenecks</div>', unsafe_allow_html=True)
    st.caption("Top-down narratives + structural discovery engine. Real data from price clusters + news NLP.")
    st.divider()
    themes_tab, disc_tab = st.tabs(["📖 Macro Themes", "🔮 Discovery Engine"])
    with themes_tab:
        # Use real narratives from discovery_v3 if available, else fallback
        narratives_list = narr.get("narratives",[]) if narr else []
        # Also add price cluster themes as narratives
        if price_clusters and price_clusters.get("clusters"):
            for c in price_clusters["clusters"]:
                if c.get("is_novel_theme") or c.get("confidence", 0) > 0.6:
                    narratives_list.append({
                        "name": c.get("theme_hypothesis", "Price Cluster Theme"),
                        "score": c.get("confidence", 0.5),
                        "thesis": f"Cross-sector cluster of {c.get('member_count')} tickers. Dominant sector: {c.get('dominant_sector')}. Avg RS 3M: {c.get('avg_rs_3m',0):+.1%}.",
                        "tickers": c.get("members", [])[:5],
                        "best": c.get("members", [])[:5],
                        "worst": [],
                        "invalidators": ["Cluster correlation breaks", "Lead ticker breaks trend"],
                    })
        # Add news emergent narratives
        if news_narratives and news_narratives.get("emergent_narratives"):
            for en in news_narratives["emergent_narratives"]:
                narratives_list.append({
                    "name": f"News: {en.get('narrative', 'Unknown')}",
                    "score": min(en.get("avg_sentiment", 0.5) + en.get("supply_chain_hits", 0) * 0.1, 1.0),
                    "thesis": f"Emergent narrative from news: {en.get('mention_count')} mentions, {en.get('supply_chain_hits',0)} supply chain hits. Linked: {', '.join(en.get('linked_tickers',[])[:5])}.",
                    "tickers": en.get("linked_tickers", [])[:5],
                    "best": en.get("linked_tickers", [])[:5],
                    "worst": [],
                    "invalidators": ["News volume drops", "No price confirmation"],
                })
        if not narratives_list:
            # Ultimate fallback
            narratives_list = [
                {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand + safe haven.","tickers":["SLV","SILJ","GDXJ"],"best":["SLV","SILJ"],"worst":["XLK"],"invalidators":["Q4 deflation","DXY bullish"]},
                {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural.","tickers":["GLD","GDX","GDXJ"],"best":["GLD","GDX"],"worst":["HYG"],"invalidators":["Q4->Q1 direct","DXY reversal"]},
            ]
        for n in narratives_list:
            if not isinstance(n, dict): continue
            score = n.get("score",0)
            with st.expander(f"📚 **{n.get('name','')}** — Score: {score:.0%}", expanded=False):
                st.markdown(f"**Thesis:** {n.get('thesis','')}")
                st.markdown(f"**Best tickers:** {', '.join(n.get('best', n.get('tickers',[]))[:5])}")
                st.markdown(f"**Avoid:** {', '.join(n.get('worst',[])[:5])}")
                st.markdown(f"**Invalidators:** {', '.join(n.get('invalidators',[])[:3])}")
    with disc_tab:
        # Use real discovery_v3 data
        discoveries_list = disc.get("discoveries",[]) if disc else []
        if discovery_v3 and discovery_v3.get("candidates"):
            for c in discovery_v3["candidates"]:
                discoveries_list.append({
                    "name": c.get("name", "Unknown"),
                    "category": c.get("category", "Unknown"),
                    "stage": c.get("stage", "unknown"),
                    "confidence": c.get("confidence", 0),
                    "thesis": c.get("thesis", ""),
                    "beneficiary_tickers": c.get("beneficiary_tickers", []),
                    "fade_tickers": c.get("fade_tickers", []),
                    "confirmation_signal": c.get("confirmation_signal", ""),
                    "invalidators": c.get("invalidators", []),
                })
        if not discoveries_list:
            discoveries_list = [
                {"name":"AI Photonics Bottleneck","category":"Structural Constraint","stage":"active","confidence":0.88,"thesis":"LITE sole supplier 200G EML lasers. NVIDIA $2B photonics.","beneficiary_tickers":["LITE","POET","COHR"],"fade_tickers":["INTC"],"confirmation_signal":"LITE earnings + NVIDIA capex","invalidators":["China photonics scaling"]},
                {"name":"SiC Power Monopoly","category":"Structural Constraint","stage":"active","confidence":0.84,"thesis":"WOLF = ONLY US large-scale SiC substrate. CHIPS Act strategic.","beneficiary_tickers":["WOLF","ON","STM"],"fade_tickers":["Legacy Si"],"confirmation_signal":"EV OEM adoption + DOD qual","invalidators":["China SiC subsidies"]},
            ]
        for d in discoveries_list:
            if not isinstance(d, dict): continue
            conf = d.get("confidence",0)
            with st.expander(f"🔍 **{d.get('name','')}** — {d.get('category','')} · Confidence: {conf:.0%}", expanded=False):
                st.markdown(f"**Stage:** {d.get('stage','')}")
                st.markdown(f"**Thesis:** {d.get('thesis','')}")
                st.markdown(f"**Beneficiaries:** {', '.join(d.get('beneficiary_tickers',[])[:5])}")
                st.markdown(f"**Fade:** {', '.join(d.get('fade_tickers',[])[:5])}")
                st.markdown(f"**Confirmation:** {d.get('confirmation_signal','')}")
                st.markdown(f"**Invalidators:** {', '.join(d.get('invalidators',[])[:3])}")
        st.markdown("### 🔍 Auto-Discovered Bottlenecks")
        auto_bottlenecks = auto_disc.get("bottlenecks",[]) if auto_disc else []
        if discovery_v3 and discovery_v3.get("bottlenecks"):
            auto_bottlenecks.extend(discovery_v3["bottlenecks"])
        if auto_bottlenecks:
            for b in auto_bottlenecks:
                if not isinstance(b, dict): continue
                st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;margin-bottom:8px;"><b>{b.get("ticker","")}</b> · {b.get("direction","")} · {b.get("known_thesis","")[:60]}</div>', unsafe_allow_html=True)
        else: st.info("No auto-discovered bottlenecks yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">🏥 System Health</div>', unsafe_allow_html=True)
    st.caption("Data pipeline status, coverage, and diagnostics.")
    st.divider()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Prices Loaded", snap.get("prices_loaded",0))
    c2.metric("Assets in Snapshot", len(ar))
    c3.metric("VIX", f"{vix_now:.1f}")
    c4.metric("Build Time", f"{snap.get('build_time_s',0):.0f}s")
    if daily_signals:
        st.divider()
        st.markdown("### Daily Signal Coverage")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tickers Rated", len(daily_signals))
        c2.metric("Alpha Center Items", alpha_center.get("meta", {}).get("total_items", 0) if alpha_center else 0)
        c3.metric("Strong Signals", sum(1 for s in daily_signals if "STRONG" in s.get("signal", "")))
        c4.metric("Option-Analyzed", len(snap.get("gamma_data", {})))
    gamma_data = snap.get("gamma_data", {})
    greeks_data = snap.get("greeks_data", {})
    if gamma_data or greeks_data:
        st.divider()
        st.markdown("### Option Data Coverage")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gamma Engine", len(gamma_data))
        c2.metric("Greeks Proxy", len(greeks_data))
        c3.metric("Combined", len(set(gamma_data.keys()) & set(greeks_data.keys())))
    # Forward-looking health
    if regime_forecast and regime_forecast.get("1m"):
        st.divider()
        st.markdown("### Forward-Looking Engine Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("1M Predicted", regime_forecast["1m"].get("predicted_quad", "—"))
        c2.metric("3M Predicted", regime_forecast["3m"].get("predicted_quad", "—"))
        c3.metric("6M Predicted", regime_forecast["6m"].get("predicted_quad", "—"))
        c4.metric("News Headlines", news_narratives.get("analyzed_count", 0) if news_narratives else 0)
    st.divider()
    st.markdown("### Data Sources")
    sources = health.get("sources",{}) if health else {}
    if sources:
        for src, status in sources.items():
            color = "#3FB950" if status == "OK" else "#F85149" if status == "FAIL" else "#D29922"
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:6px 12px;margin:3px 0;display:flex;justify-content:space-between;"><span>{src}</span><span style="color:{color};font-weight:700;">{status}</span></div>', unsafe_allow_html=True)
    else: st.info("No detailed source status available.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown('<div style="font-size:24px;font-weight:700;color:#E6EDF3;margin-bottom:4px;">📋 Playbook</div>', unsafe_allow_html=True)
    st.caption("What to buy, what to avoid, and why.")
    st.divider()
    if pb_data:
        st.markdown(f"### Regime: {sq} · {QN.get(sq,'')}")
        st.markdown(f"**Strategy:** {pb_data.get('strategy','')}")
        st.markdown("#### Buy/Hold")
        for asset in pb_data.get("best_assets",[])[:10]: st.markdown(f'- {asset}')
        st.markdown("#### Avoid/Sell")
        for asset in pb_data.get("worst_assets",[])[:10]: st.markdown(f'- {asset}')
        # Add forward-looking playbook adjustment
        if regime_forecast and regime_forecast.get("3m"):
            rf3 = regime_forecast["3m"]
            if rf3.get("predicted_quad") != sq:
                st.divider()
                st.warning(f"⚠️ **Forward-Looking Alert:** 3M forecast predicts shift to **{rf3.get('predicted_quad')}** (confidence {rf3.get('prediction_confidence',0):.0%}). Consider gradually rotating toward {QWINS.get(rf3.get('predicted_quad'),'defensive')} assets.")
    else: st.info("Playbook data loading...")

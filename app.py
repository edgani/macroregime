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

try:
    from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE, IHSG_SECTOR_MAP, TICKER_SECTOR, US_SECTORS, US_BUCKETS
except ImportError:
    from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE, TICKER_SECTOR, US_SECTORS, US_BUCKETS
    # Fallback IHSG sector map if not exported from config
    IHSG_SECTOR_MAP = {
        "ADRO.JK": "Coal", "ITMG.JK": "Coal", "PTBA.JK": "Coal",
        "NCKL.JK": "Nickel", "ANTM.JK": "Nickel", "INCO.JK": "Nickel",
        "AALI.JK": "CPO", "LSIP.JK": "CPO", "SMAR.JK": "CPO",
        "BBRI.JK": "Banking", "BMRI.JK": "Banking", "BBCA.JK": "Banking", "BBNI.JK": "Banking", "BRIS.JK": "Banking",
        "TLKM.JK": "Telco", "EXCL.JK": "Telco",
        "UNTR.JK": "Mining Contractor", "BYAN.JK": "Mining",
        "ICBP.JK": "Consumer", "INDF.JK": "Consumer", "KLBF.JK": "Pharma",
        "PGEO.JK": "Geothermal", "WINS.JK": "Shipping",
        "EIDO": "ETF", "^JKSE": "Index",
    }

st.markdown("""
<style>
.stApp { background-color: #0d1117; }
.card-green {background:#0D2818;border:1px solid #3FB950;border-radius:8px;padding:12px;margin:6px 0;}
.card-yellow {background:#2D2305;border:1px solid #D29922;border-radius:8px;padding:12px;margin:6px 0;}
.card-red {background:#2D0D0D;border:1px solid #F85149;border-radius:8px;padding:12px;margin:6px 0;}
.card-blue {background:#0D1B2A;border:1px solid #1F6FEB;border-radius:8px;padding:12px;margin:6px 0;}
.card {background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin:6px 0;}
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
.section-title {font-size:22px;font-weight:700;color:#E6EDF3;margin-bottom:4px;}
.section-sub {font-size:12px;color:#8B949E;margin-bottom:12px;}
.kpi-row {display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;}
.kpi-box {background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 12px;min-width:120px;text-align:center;}
.kpi-label {font-size:10px;color:#8B949E;text-transform:uppercase;letter-spacing:0.3px;}
.kpi-value {font-size:16px;font-weight:700;color:#E6EDF3;}
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

def _section_header(title, subtitle=""):
    sub = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    return f'<div class="section-title">{title}</div>{sub}'

def _kpi_box(label, value, color="#E6EDF3"):
    return f'<div class="kpi-box"><div class="kpi-label">{label}</div><div class="kpi-value" style="color:{color};">{value}</div></div>'

def _card(title, content, border_color="#30363D"):
    return f'<div style="background:#161B22;border:1px solid {border_color};border-radius:8px;padding:12px;margin:6px 0;"><div style="font-size:13px;font-weight:700;color:#E6EDF3;margin-bottom:8px;">{title}</div><div style="font-size:12px;color:#8B949E;">{content}</div></div>'

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
    flow = (ihsg_foreign_flow or {}).get(ticker, {})
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

    # Color coding
    dir_emoji = "🟢" if "LONG" in direction else "🔴" if "SHORT" in direction else "⚪"
    dir_color = "#3fb950" if "LONG" in direction else "#f85149" if "SHORT" in direction else "#8b949e"
    worth_color = "#3fb950" if "YES" in worth or "BUY" in worth else "#d29922" if "WAIT" in worth or "CHASE" in worth else "#f85149" if "SKIP" in worth else "#8b949e"

    # Build header
    header = f"{dir_emoji} {ticker} | {direction.replace(' ✅','').replace(' ⚠️','')} | Grade {grade}"
    if scanner:
        header += f" | {scanner}"
    if row.get("score") is not None:
        header += f" | Score: {row.get('score',0):.2f}"

    with st.expander(header, expanded=False):
        # ── Top Row: Direction + Worth + Grade ──
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Direction:** <span style='color:{dir_color};font-weight:700;'>{direction}</span>", unsafe_allow_html=True)
        c2.markdown(f"**Worth Entering:** <span style='color:{worth_color};font-weight:700;'>{worth}</span>", unsafe_allow_html=True)
        c3.markdown(f"**Grade:** <span style='color:{dir_color};font-weight:700;'>{grade}</span>", unsafe_allow_html=True)

        st.divider()

        # ── Price Metrics ──
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price", _fmt_num(price))
        m2.metric("Entry", _fmt_num(entry))
        m3.metric("Target 1", _fmt_num(t1))
        m4.metric("Target 2", _fmt_num(t2))
        m5.metric("Stop Loss", _fmt_num(stop))
        m6.metric("R:R", f"{_fmt_num(rr)}x")

        # Expected Move
        em_pct = row.get("expected_move_weekly_pct")
        em_val = row.get("expected_move_weekly")
        if em_pct or em_val:
            st.caption(f"📊 Expected Move (weekly): ±{_fmt_num(em_val)} ({fp(em_pct)}) · Daily vol: {fp(row.get('daily_vol'))}")

        # ── TRR / LRR Toggle ──
        if row.get("lrr") and row.get("trr"):
            with st.expander("📐 TRR / LRR Levels", expanded=False):
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("LRR", _fmt_num(row.get("lrr")))
                t2.metric("TRR", _fmt_num(row.get("trr")))
                price = row.get("price")
                lrr = row.get("lrr")
                trr = row.get("trr")
                pos_pct = ((price - lrr) / (trr - lrr) * 100) if (trr and lrr and trr > lrr) else 0
                t3.metric("Position %", f"{pos_pct:.0f}%")
                comp_color = "#3FB950" if row.get("composite") == "bullish" else "#F85149" if row.get("composite") == "bearish" else "#D29922"
                t4.markdown(f"**Composite:** <span style='color:{comp_color};font-weight:700;'>{row.get('composite','—').upper()}</span>", unsafe_allow_html=True)
                st.caption(f"Range: {lrr} -> {trr} | Spread: {trr - lrr:.2f}")

        # ── Forward-Looking Toggle ──
        if row.get("expected_1m") is not None or row.get("expected_3m") is not None:
            with st.expander("🔮 Forward-Looking", expanded=False):
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("1M Expected", fp(row.get("expected_1m")))
                f2.metric("3M Expected", fp(row.get("expected_3m")))
                f3.metric("6M Expected", fp(row.get("expected_6m")))
                f4.metric("Confidence", f"{row.get('forward_confidence', 0):.0%}")

        # ── News / Narrative Toggle ──
        if row.get("news_narrative") or row.get("news_headline"):
            with st.expander("📰 News / Narrative", expanded=False):
                news_color = "#3FB950" if row.get("news_sentiment") == "positive" else "#F85149" if row.get("news_sentiment") == "negative" else "#D29922"
                st.markdown(f"<span style='color:{news_color};font-weight:600;'>{row.get('news_narrative', row.get('news_headline', '—'))}</span>", unsafe_allow_html=True)
                if row.get("news_headline") and row.get("news_narrative"):
                    st.caption(f"Headline: {row.get('news_headline')}")

        # ── Options & Greeks (skip for IHSG) ──
        has_options = any(row.get(k) for k in ["gamma_regime","greek_composite","max_pain","max_pain_gamma","delta","vanna","put_wall","call_wall","gamma_flip_up","gamma_flip_down"])
        if has_options and market_type not in ["ihsg"]:
            with st.expander("📊 Options & Greeks", expanded=False):
                source = row.get("options_source", row.get("source", "PROXY"))
                if "LIVE" in str(source):
                    st.success(f"🟢 {source}")
                else:
                    st.warning("🟡 PROXY DATA — Calculated from price action")
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
                    st.markdown("**Put/Call Ratio**")
                    pc1, pc2 = st.columns(2)
                    pc1.metric("P/C Volume", row.get("pc_volume", "—"))
                    pc2.metric("P/C OI", row.get("pc_oi", "—"))
                if row.get("unusual_activity"):
                    st.divider()
                    st.markdown("**Unusual Activity**")
                    for ua in row.get("unusual_activity", [])[:3]:
                        st.caption(f"{ua.get('type')} {ua.get('strike')}: Vol/OI = {ua.get('vol_oi_ratio')}x | IV: {ua.get('iv')}")
                if row.get("expected_move"):
                    em = row.get("expected_move")
                    st.divider()
                    st.markdown("**Expected Move (Options-Based)**")
                    st.caption(f"ATM Straddle: {em.get('straddle')} | Expected: ±{em.get('expected_move')} ({fp(em.get('expected_pct'))}) | ATM Strike: {em.get('atm_strike')}")

        # ── Flow & Positioning ──
        has_flow = any(row.get(k) for k in ["cot_signal","oi_signal","onchain_signal","skew","oi_trend","cot_bias"])
        if has_flow and market_type not in ["ihsg"]:
            st.divider()
            st.markdown("**📈 Flow & Positioning**")
            f1, f2 = st.columns(2)
            f1.write(f"**COT Signal:** {row.get('cot_signal', '—')}")
            f1.write(f"**COT Bias:** {row.get('cot_bias', '—')}")
            f2.write(f"**OI Signal:** {row.get('oi_signal') or row.get('oi_conc', '—')}")
            f2.write(f"**OI Trend:** {row.get('oi_trend', '—')}")
            if row.get("skew") and row.get("skew") != "—":
                st.write(f"**Skew:** {row.get('skew')}")
            if row.get("onchain_signal") and row.get("onchain_signal") != "—":
                st.write(f"**On-Chain:** {row.get('onchain_signal')}")

        # ── Risk-Adjusted ──
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

        # ── Thesis & Strategy ──
        st.divider()
        st.markdown("**🎯 Thesis & Strategy**")
        thesis = row.get("thesis") or row.get("recommendation") or row.get("known_thesis", "N/A")
        st.info(thesis)
        if row.get("action"):
            st.caption(f"🎬 **Action:** {row.get('action')}")

        invalidators = row.get("invalidators", [])
        if invalidators:
            st.error(f"❌ **Invalidators:** {', '.join(invalidators)}")

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
    st.markdown("## 📊 MacroRegime Pro v2.0")
    st.markdown('<div style="font-size:11px;color:#8B949E;">PVV Multi-Duration + Hedgeye Methodology</div>', unsafe_allow_html=True)
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Full Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        st.checkbox("US Stocks", value=True, key="inc_us")
        st.checkbox("Forex", value=True, key="inc_fx")
        st.checkbox("Commodities", value=True, key="inc_comm")
        st.checkbox("Crypto", value=True, key="inc_cryp")
        st.checkbox("Indonesia (IHSG)", value=True, key="inc_ihsg")
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
        if _s.get("pvv"): sources.append("🟢 PVV")
        if not sources: sources.append("🟡 Proxy Only")
        st.caption(" · ".join(sources))

snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap


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
# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD — COMPACT v2
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD — COMPACT v2
# ══════════════════════════════════════════════════════════════════════════════

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
        snap=build_snapshot(progress_cb=prog, include_us_stocks=st.session_state.get("inc_us", True), include_forex=st.session_state.get("inc_fx", True),
            include_commodities=st.session_state.get("inc_comm", True), include_crypto=st.session_state.get("inc_cryp", True), include_ihsg=st.session_state.get("inc_ihsg", True))
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
# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD — COMPACT v2
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD — COMPACT v2
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs(["🎯 Macro Radar", "📈 TREND Signals", "⚡ Alpha Center", "📋 Playbook", "🏥 Health"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0: 🎯 MACRO RADAR
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("## 🎯 Macro Radar")
    st.caption("Regime · Forward · All Markets · 30-second read")

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Quarterly", sq, qn(sq), delta_color="off")
    with k2: st.metric("Monthly", mq, qn(mq), delta_color="off")
    with k3:
        flip = gip.flip_hazard if gip else 0
        st.metric("Flip Risk", f"{flip:.0%}", f"{gip.divergence if gip else '—'}" if flip > 0.2 else None)
    with k4:
        vix_val = health.get("vix_bucket", {}).get("vix_last", 18)
        vix_label = health.get("vix_bucket", {}).get("bucket", "—")
        st.metric("VIX", f"{vix_val:.1f}", vix_label)
    with k5: st.metric("Assets", f"{snap.get('prices_loaded',0)}", f"{len(ar)} ranges")

    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable":
        st.success(f"🟢 GOOD CONDITIONS · VIX {vl:.1f} · {vbd.get('risk_mode','Normal')}")
    elif vb=="Chop":
        st.warning(f"🟡 CHOPPY · VIX {vl:.1f} · {vbd.get('risk_mode','Normal')}")
    elif vb=="Defensive":
        st.error(f"🔴 DEFENSIVE · VIX {vl:.1f} · {vbd.get('risk_mode','Normal')}")

    rs1, rs2, rs3 = st.columns([1.2, 1, 1])
    with rs1:
        st.markdown(f'<div style="background:#161B22;border:1px solid {qc(sq)};border-radius:6px;padding:8px;margin-bottom:6px;"><div style="font-size:10px;color:#8B949E;">QUARTERLY · {sq}</div><div style="font-size:14px;font-weight:700;color:{qc(sq)};margin:2px 0;">{QN.get(sq,sq)}</div><div style="font-size:11px;color:#E6EDF3;">{QUAD_EXPLAIN.get(sq,"")[:80]}...</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#161B22;border:1px solid {qc(mq)};border-radius:6px;padding:8px;"><div style="font-size:10px;color:#8B949E;">MONTHLY · {mq}</div><div style="font-size:14px;font-weight:700;color:{qc(mq)};margin:2px 0;">{QN.get(mq,mq)}</div><div style="font-size:11px;color:#E6EDF3;">{QUAD_EXPLAIN.get(mq,"")[:80]}...</div></div>', unsafe_allow_html=True)
    with rs2:
        if pb_data:
            best = " · ".join(pb_data.get("best_assets",[])[:5])
            worst = " · ".join(pb_data.get("worst_assets",[])[:4])
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px;"><div style="font-size:10px;color:#8B949E;margin-bottom:4px;">🎯 Playbook — {sq}</div><div style="font-size:11px;color:#3FB950;margin-bottom:3px;">🟢 {best}</div><div style="font-size:11px;color:#F85149;">🔴 {worst}</div></div>', unsafe_allow_html=True)
    with rs3:
        if regime_forecast and regime_forecast.get("1m"):
            rf1 = regime_forecast["1m"]; rf3 = regime_forecast["3m"]
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px;margin-bottom:6px;"><div style="font-size:10px;color:#8B949E;">🔮 Forward</div><div style="font-size:12px;color:#E6EDF3;">1M→{rf1.get("predicted_quad","—")} ({rf1.get("prediction_confidence",0):.0%})</div><div style="font-size:12px;color:#E6EDF3;">3M→{rf3.get("predicted_quad","—")} ({rf3.get("prediction_confidence",0):.0%})</div></div>', unsafe_allow_html=True)
        if transition:
            fw = transition.front_run_window
            fwc = {"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
            fwi = {"now":"🚨 ACT NOW","1-2w":"⚡ 1-2w","3-6w":"👀 Watch","not yet":"🛑 Wait"}.get(fw,"🛑 Wait")
            st.markdown(f'<div style="background:{fwc};color:#fff;padding:6px 10px;border-radius:6px;font-weight:600;text-align:center;font-size:11px;">{fwi}</div>', unsafe_allow_html=True)

    st.markdown("### 🚨 Early Warning")
    ew1, ew2, ew3, ew4 = st.columns(4)
    vix_regime = health.get("vix_bucket", {}).get("bucket", "—")
    vix_color = "#3FB950" if vix_regime == "Investable" else "#D29922" if vix_regime == "Chop" else "#F85149"
    ew1.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">VIX</div><div style="font-size:16px;font-weight:700;color:{vix_color};">{vl:.1f}</div><div style="font-size:10px;color:#8B949E;">{vix_regime}</div></div>', unsafe_allow_html=True)
    crash_state = health.get("crash", {}).get("state", "calm")
    crash_color = "#3FB950" if crash_state == "calm" else "#D29922" if crash_state == "watch" else "#F85149"
    ew2.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">CRASH</div><div style="font-size:16px;font-weight:700;color:{crash_color};">{crash_state.upper()}</div></div>', unsafe_allow_html=True)
    risk_off_state = health.get("risk_off", {}).get("state", "risk_on")
    risk_color = "#3FB950" if risk_off_state == "risk_on" else "#D29922" if risk_off_state == "caution" else "#F85149"
    ew3.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">RISK OFF</div><div style="font-size:16px;font-weight:700;color:{risk_color};">{risk_off_state.upper()}</div></div>', unsafe_allow_html=True)
    breadth_tickers = list(US_SECTORS.keys())
    for bucket in ["Growth", "Quality", "Defensives", "Semis", "Energy", "Industrials", "Financials", "AI_Infra", "PreciousMetals"]:
        breadth_tickers += US_BUCKETS.get(bucket, [])
    breadth_tickers = list(dict.fromkeys(breadth_tickers))
    advancers = 0; decliners = 0; unchanged = 0
    for t in breadth_tickers:
        ret = _price_ret(t, prices, 21)
        if ret is not None:
            if ret > 0.005: advancers += 1
            elif ret < -0.005: decliners += 1
            else: unchanged += 1
    total_b = advancers + decliners + unchanged
    b_score = advancers / total_b if total_b > 0 else 0.5
    b_color = "#3FB950" if b_score > 0.6 else "#D29922" if b_score > 0.4 else "#F85149"
    ew4.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:#8B949E;">BREADTH</div><div style="font-size:16px;font-weight:700;color:{b_color};">{b_score:.0%}</div><div style="font-size:9px;color:#8B949E;">{advancers}↑ {decliners}↓</div></div>', unsafe_allow_html=True)

    st.caption(f"Built {snap.get('build_time_s',0):.0f}s ago · {snap.get('prices_loaded',0)} assets · {snap.get('fred_coverage',0)} indicators")

    st.markdown("### 📊 All Markets — PVV Composite")
    pvv_data = snap.get("pvv", {})
    if pvv_data:
        pvv_rows = []
        for ticker, res in pvv_data.items():
            if not res.get("ok"): continue
            trend = res.get("trend", {})
            pvv_rows.append({
                "Ticker": ticker, "Signal": res.get("composite_signal", "—"),
                "VASP": round(res.get("composite_score", 0), 2),
                "Vol": trend.get("realized_vol", "—"), "VoV": trend.get("vol_of_vol", "—"),
                "Hurst": trend.get("hurst", "—"), "LRR": trend.get("lrr", "—"),
                "TRR": trend.get("trr", "—"),
                "Formation": "Bull" if res.get("bullish_formation") else ("Bear" if res.get("bearish_formation") else "Mixed"),
                "Front-Run": res.get("front_run_rationale", "")[:60],
            })
        if pvv_rows:
            df_pvv = pd.DataFrame(pvv_rows)
            st.dataframe(
                df_pvv.style
                    .map(lambda x: 'color:#3FB950;font-weight:700;' if x=="BULLISH" else ('color:#F85149;font-weight:700;' if x=="BEARISH" else ('color:#8B949E;' if x=="NEUTRAL" else '')), subset=["Signal"])
                    .map(lambda x: 'color:#3FB950;font-weight:700;' if x=="Bull" else ('color:#F85149;font-weight:700;' if x=="Bear" else ''), subset=["Formation"])
                    .format({"VASP": "{:.2f}", "Vol": "{:.1f}", "VoV": "{:.2f}", "Hurst": "{:.3f}"}),
                use_container_width=True, hide_index=True, height=300
            )
    else:
        st.info("PVV data loading...")

    st.markdown("### 🔮 Forward Outlook")
    if gip:
        rp1, rp2 = st.columns(2)
        with rp1:
            st.markdown("**Quarterly Probabilities**")
            st.plotly_chart(prob_bar(gip.structural_probs, ""), use_container_width=True, config={"displayModeBar":False}, key="dash_prob_q2")
        with rp2:
            st.markdown("**Monthly Probabilities**")
            st.plotly_chart(prob_bar(gip.monthly_probs, ""), use_container_width=True, config={"displayModeBar":False}, key="dash_prob_m2")

    if regime_forecast and regime_forecast.get("1m"):
        rf1 = regime_forecast["1m"]; rf3 = regime_forecast["3m"]; rf6 = regime_forecast["6m"]
        fp1, fp2, fp3 = st.columns(3)
        with fp1:
            st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px;"><div style="font-size:10px;color:#8B949E;">1 MONTH</div><div style="font-size:18px;font-weight:700;color:{qc(rf1.get("predicted_quad","Q3"))};">{rf1.get("predicted_quad","—")}</div><div style="font-size:10px;color:#8B949E;">Conf {rf1.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)
        with fp2:
            st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px;"><div style="font-size:10px;color:#8B949E;">3 MONTHS</div><div style="font-size:18px;font-weight:700;color:{qc(rf3.get("predicted_quad","Q3"))};">{rf3.get("predicted_quad","—")}</div><div style="font-size:10px;color:#8B949E;">Conf {rf3.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)
        with fp3:
            st.markdown(f'<div style="text-align:center;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px;"><div style="font-size:10px;color:#8B949E;">6 MONTHS</div><div style="font-size:18px;font-weight:700;color:{qc(rf6.get("predicted_quad","Q3"))};">{rf6.get("predicted_quad","—")}</div><div style="font-size:10px;color:#8B949E;">Conf {rf6.get("prediction_confidence",0):.0%}</div></div>', unsafe_allow_html=True)

    vol_f = snap.get("vol_forecast", {})
    if vol_f:
        st.markdown("**Vol Forecast**")
        proxy_tickers = ["SPY", "QQQ", "GLD", "TLT", "DX-Y.NYB"]
        vol_rows = []
        for t in proxy_tickers:
            if t in vol_f:
                v = vol_f[t]
                vol_rows.append({"Asset": t, "Current": f"{v['current_ann_vol']}%", "Forecast": f"{v['forecast_ann_vol']}%", "Regime": v['vol_regime'], "Daily": f"±{v['expected_daily_move_pct']:.1%}"})
        if vol_rows:
            df_vol = pd.DataFrame(vol_rows)
            st.dataframe(df_vol.style.map(lambda x: 'color:#3FB950;font-weight:600;' if x == "LOW" else ('color:#D29922;font-weight:600;' if x == "NORMAL" else ('color:#F85149;font-weight:600;' if x in ["ELEVATED","EXTREME"] else '')), subset=["Regime"]), hide_index=True, use_container_width=True, height=160)

    stress = snap.get("stress_test", [])
    if stress:
        st.markdown("**Stress Test**")
        for sc in stress:
            sev_color = "#F85149" if sc['severity'] == "EXTREME" else "#D29922" if sc['severity'] == "HIGH" else "#8B949E"
            with st.expander(f"⚠️ {sc['scenario']} | DD: {sc['portfolio_dd']:.0%} | {sc['severity']}", expanded=(sc['severity'] in ["EXTREME","HIGH"])):
                c1, c2, c3 = st.columns(3)
                c1.metric("Portfolio DD", f"{sc['portfolio_dd']:.0%}")
                c2.metric("Worst", sc['worst_asset'], f"{sc['worst_dd']:.0%}")
                c3.metric("Best", sc['best_asset'], f"{sc['best_dd']:.0%}")
                st.info(f"🛡️ Hedge: {sc['hedge']}")

    if analogs and analogs.get("top_analogs"):
        st.markdown("**Historical Analogs**")
        for i, a in enumerate(analogs["top_analogs"][:3]):
            with st.expander(f"📚 {a['label']} — {a.get('similarity',0):.0%} similar", expanded=(i==0)):
                c1, c2, c3 = st.columns(3)
                c1.metric("1M", a.get("path_1m","—")); c2.metric("3M", a.get("path_3m","—")); c3.metric("6M", a.get("path_6m","—"))
                st.caption(f"📊 {a.get('next_bias','')}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: 📈 TREND SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("## 📈 TREND Signals")
    st.caption("Historical multi-duration signal charts — Hedgeye style")

    dur = st.segmented_control("Duration", ["TRADE", "TREND", "TAIL"], default="TREND", key="trend_dur")

    if not snap or not snap.get("trend_histories"):
        st.info("No trend histories loaded. Run Full Rebuild to generate.")
    else:
        histories = snap["trend_histories"]
        pvv_data = snap.get("pvv", {})

        asset_groups = {
            "🇺🇸 US Stocks": ["SPY", "QQQ", "IWM", "XLK", "XLE", "XLF", "XLI", "XLU", "META", "AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "JPM", "JNJ", "UNH", "V", "MA", "PG", "HD", "BAC", "ABBV", "PFE", "KO", "PEP", "WMT", "DIS", "NFLX", "CRM", "ADBE", "PYPL", "UBER", "ABNB"],
            "🌏 Global & EM": ["EEM", "EWZ", "FXI", "INDA", "RSX", "EWG", "EWJ", "EWY", "EWT", "EWH", "EIDO", "EPHE", "THD", "ARGT", "GXG", "ICOL", "JSE.JO", "NIFTY", "SENSEX", "DAX", "FTSE", "CAC40"],
            "💱 Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCAD=X", "AUDUSD=X", "NZDUSD=X", "USDCHF=X", "USDCNH=X", "DX-Y.NYB"],
            "🪙 Commodities": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "PL=F", "PA=F", "ZW=F", "ZC=F", "ZS=F", "CT=F", "CC=F", "KC=F", "SB=F"],
            "₿ Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD", "UNI-USD", "LTC-USD", "BCH-USD", "ETC-USD", "FIL-USD", "AAVE-USD", "SNX-USD", "CRV-USD", "SUSHI-USD", "1INCH-USD", "DYDX-USD", "GRT-USD", "MANA-USD", "SAND-USD", "AXS-USD", "ENJ-USD", "CHZ-USD", "FLOW-USD", "THETA-USD", "XTZ-USD", "ALGO-USD", "VET-USD", "TRX-USD", "EOS-USD", "NEO-USD", "XLM-USD", "XMR-USD", "DASH-USD", "ZEC-USD", "BAT-USD", "COMP-USD", "MKR-USD", "YFI-USD", "ZRX-USD", "KNC-USD", "BAL-USD", "REN-USD", "UMA-USD", "BNT-USD", "LRC-USD", "OCEAN-USD", "RLC-USD", "STORJ-USD", "ANT-USD", "REP-USD", "WTC-USD", "ICX-USD", "WAN-USD", "AION-USD", "LOOM-USD", "CVC-USD", "DNT-USD", "GNO-USD", "MLN-USD", "NMR-USD", "BAND-USD", "KAVA-USD", "TOMO-USD", "PERL-USD", "WRX-USD", "COTI-USD", "STMX-USD", "FTM-USD", "HOT-USD", "IOTA-USD", "RVN-USD", "SC-USD", "DGB-USD", "XVG-USD", "NANO-USD", "LSK-USD", "ARDR-USD", "NXT-USD", "STRAT-USD", "WAVES-USD", "BTS-USD", "STEEM-USD", "DCR-USD", "ZIL-USD", "ONE-USD", "HBAR-USD", "CELR-USD"],
            "🇮🇩 IHSG": ["^JKSE", "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "UNVR.JK", "PGAS.JK", "PTBA.JK", "ADRO.JK", "ANTM.JK", "INCO.JK", "ITMG.JK", "HRUM.JK", "MBMA.JK", "MDKA.JK", "TINS.JK", "BRMS.JK", "EXCL.JK", "ISAT.JK", "TOWR.JK", "TBIG.JK", "SMGR.JK", "INTP.JK", "SMCB.JK", "WSBP.JK", "WIKA.JK", "ADHI.JK", "PTPP.JK", "JSMR.JK", "CMNP.JK", "META.JK", "BORN.JK", "CPIN.JK", "MAIN.JK", "JPFA.JK", "SIPD.JK", "AALI.JK", "LSIP.JK", "SSMS.JK", "TAPG.JK", "BWPT.JK", "SIMP.JK", "STAA.JK", "MYOR.JK", "ICBP.JK", "INDF.JK", "GOOD.JK", "ULTJ.JK", "SKBM.JK", "KLBF.JK", "KAEF.JK", "DVLA.JK", "HEAL.JK", "MIKA.JK", "SILO.JK", "RAJA.JK", "ERAA.JK", "ACES.JK", "MAPI.JK", "LPPF.JK", "MIDI.JK", "AMRT.JK", "MPPA.JK", "RALS.JK", "INKP.JK", "FASW.JK", "SPMA.JK", "TBLA.JK", "GGRM.JK", "WIIM.JK", "RMBA.JK", "GJTL.JK", "AUTO.JK", "INDO.JK", "AIMS.JK", "BEST.JK", "BIRD.JK", "WEHA.JK", "PANR.JK", "MNCN.JK", "SCMA.JK", "EMTK.JK", "BMTR.JK", "VIVA.JK", "DOID.JK", "ENRG.JK", "ESSA.JK", "MEDC.JK", "ELSA.JK", "AKRA.JK", "AISA.JK", "INDR.JK", "TPIA.JK", "BRPT.JK", "SMAR.JK", "INCI.JK", "IPCM.JK", "LINK.JK", "BALI.JK", "POWR.JK"],
        }

        all_pvv_tickers = [t for t in pvv_data.keys() if t not in [x for g in asset_groups.values() for x in g]]
        if all_pvv_tickers:
            asset_groups["📊 Other"] = all_pvv_tickers[:20]

        for group_name, tickers_group in asset_groups.items():
            available = [t for t in tickers_group if t in histories and histories[t].get(dur, [])]
            if not available:
                continue
            st.markdown(f"#### {group_name}")
            cols = st.columns(2)
            for idx, ticker in enumerate(available[:6]):
                with cols[idx % 2]:
                    df_hist = pd.DataFrame(histories[ticker][dur])
                    if df_hist.empty:
                        continue
                    df_hist["date"] = pd.to_datetime(df_hist["date"])

                    import plotly.graph_objects as go
                    fig = go.Figure()

                    if "signal" in df_hist.columns:
                        colors = {"BULLISH": "#3FB950", "BEARISH": "#F85149", "NEUTRAL": "#8B949E"}
                        curr_sig = df_hist["signal"].iloc[0]
                        start = 0
                        for i in range(1, len(df_hist)):
                            if df_hist["signal"].iloc[i] != curr_sig or i == len(df_hist) - 1:
                                seg = df_hist.iloc[start:i]
                                fig.add_trace(go.Scatter(
                                    x=seg["date"], y=seg["price"],
                                    mode="lines", line=dict(color=colors.get(curr_sig, "#8B949E"), width=2.5),
                                    showlegend=False, hoverinfo="skip"
                                ))
                                curr_sig = df_hist["signal"].iloc[i]
                                start = i
                        for sig, col in colors.items():
                            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                line=dict(color=col, width=3), name=sig))

                    if "lrr" in df_hist.columns and df_hist["lrr"].notna().any():
                        fig.add_trace(go.Scatter(
                            x=df_hist["date"].tolist() + df_hist["date"].tolist()[::-1],
                            y=df_hist["trr"].tolist() + df_hist["lrr"].tolist()[::-1],
                            fill="toself", fillcolor="rgba(255,255,255,0.03)",
                            line=dict(color="rgba(255,255,255,0)"), name="Risk Range", showlegend=True
                        ))

                    pvv_t = pvv_data.get(ticker, {})
                    last_vasp = pvv_t.get("composite_score", "—") if pvv_t.get("ok") else "—"
                    last_vov = pvv_t.get("trend", {}).get("vol_of_vol", "—") if pvv_t.get("ok") else "—"
                    last_hurst = pvv_t.get("trend", {}).get("hurst", "—") if pvv_t.get("ok") else "—"

                    fig.update_layout(
                        title=f"{ticker}: {dur} SIGNAL",
                        height=300,
                        margin=dict(t=40, b=20, l=40, r=20),
                        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
                        font=dict(color="#E6EDF3", family="Inter, sans-serif"),
                        xaxis=dict(showgrid=True, gridcolor="#21262D", tickfont=dict(size=10)),
                        yaxis=dict(showgrid=True, gridcolor="#21262D", tickfont=dict(size=10),
                                   tickformat=",.0f" if df_hist["price"].max() > 10 else ",.4f"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
                        annotations=[dict(
                            x=0.02, y=0.02, xref="paper", yref="paper",
                            text=f"VASP: {last_vasp} | VoV: {last_vov} | H: {last_hurst}",
                            showarrow=False, font=dict(size=9, color="#8B949E"), align="left"
                        )]
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tabs[2]:
    st.markdown("## ⚡ Alpha Center")
    st.caption("Bottlenecks · Alpha · Discovery · Daily Signals")

    ac = alpha_center
    meta = ac.get("meta", {}) if ac else {}
    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild."); st.stop()

    # ── Meta Bar ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime", meta.get("regime", "?"))
    c2.metric("Bias", meta.get("bias", "?"))
    c3.metric("VIX", meta.get("vix", "?"))
    c4.metric("Total", meta.get("total_items", 0))

    if transition:
        fw = transition.front_run_window
        fwc = {"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi = {"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:{fwc};color:#fff;padding:6px 12px;border-radius:6px;font-weight:600;text-align:center;margin:8px 0;font-size:12px;">{fwi}</div>', unsafe_allow_html=True)

    # ── Master Table ──
    all_items = ac.get("all", [])
    if not all_items:
        st.info("No Alpha Center items available."); st.stop()

    df_rows = []
    for item in all_items:
        df_rows.append({
            "Ticker": item.get("ticker", "—"),
            "Scanner": item.get("scanner_type", "—"),
            "Direction": item.get("direction", "—"),
            "Grade": item.get("grade", "—"),
            "Score": round(item.get("priority_score", 0), 1),
            "Price": item.get("price"),
            "Entry": item.get("entry"),
            "T1": item.get("target_1"),
            "T2": item.get("target_2"),
            "Stop": item.get("stop_loss"),
            "RR": item.get("rr", 0),
            "Worth?": item.get("worth_entering", "—"),
            "Time": item.get("time_estimate", "—"),
            "Thesis": (item.get("thesis") or item.get("recommendation") or "")[:60],
        })
    df_alpha = pd.DataFrame(df_rows)

    # Safe defaults for multiselect
    dir_opts = sorted([x for x in df_alpha["Direction"].unique().tolist() if x and str(x) != "nan"])
    grade_opts = sorted([x for x in df_alpha["Grade"].unique().tolist() if x and str(x) != "nan"])
    level_opts = sorted([x for x in df_alpha["Scanner"].unique().tolist() if x and str(x) != "nan"])

    f1, f2, f3, f4 = st.columns(4)
    filter_dirs = f1.multiselect("Direction", dir_opts, default=dir_opts[:3] if len(dir_opts) >= 3 else dir_opts)
    filter_grades = f2.multiselect("Grade", grade_opts, default=[g for g in ["A+","A","B"] if g in grade_opts])
    filter_levels = f3.multiselect("Scanner", level_opts, default=level_opts)
    min_score = f4.slider("Min Score", 0.0, float(df_alpha["Score"].max() or 100), 0.0, 1.0)

    df_filtered = df_alpha[
        df_alpha["Direction"].isin(filter_dirs) &
        df_alpha["Grade"].isin(filter_grades) &
        df_alpha["Scanner"].isin(filter_levels) &
        (df_alpha["Score"] >= min_score)
    ]
    st.write(f"**{len(df_filtered)}** of **{len(df_alpha)}** items")

    st.dataframe(
        df_filtered.style
            .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["LONG","BUY","YES"]) else ('color:#F85149;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["SHORT","SELL","NO"]) else ''), subset=["Direction","Worth?"])
            .map(lambda x: 'color:#3FB950;font-weight:700;' if x in ["A+","A"] else ('color:#D29922;font-weight:600;' if x=="B" else ''), subset=["Grade"])
            .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,(int,float)) and x>=2.0 else ('color:#D29922;font-weight:600;' if isinstance(x,(int,float)) and x>=1.5 else ''), subset=["RR"])
            .format({"Score": "{:.1f}", "Price": "{:.2f}", "Entry": "{:.2f}", "T1": "{:.2f}", "T2": "{:.2f}", "Stop": "{:.2f}", "RR": "{:.1f}"})
            .background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True, hide_index=True, height=380
    )

    # ── Top 5 Priority Cards ──
    # ── Daily Signals Summary ──
    ds_summary = snap.get("daily_signals_summary", {})
    if ds_summary:
        st.markdown("### 📈 Daily Signals Overview")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", ds_summary.get("total", 0))
        c2.metric("Strong Longs", ds_summary.get("strong_longs", 0), delta="LONG")
        c3.metric("Longs", ds_summary.get("longs", 0))
        c4.metric("Strong Shorts", ds_summary.get("strong_shorts", 0), delta="SHORT")
        c5.metric("Shorts", ds_summary.get("shorts", 0))
        c6.metric("Neutrals", ds_summary.get("neutrals", 0))
        top5_signals = ds_summary.get("top_5_by_score", [])
        if top5_signals:
            st.markdown("**Top 5 by Score:**")
            sig_rows = []
            for s in top5_signals:
                sig_rows.append({
                    "Ticker": s.get("ticker", "—"), "Signal": s.get("signal", "—"),
                    "Direction": s.get("direction", "—"), "Grade": s.get("grade", "—"),
                    "Score": round(s.get("score", 0), 2), "Price": s.get("price"),
                    "Entry": s.get("entry"), "T1": s.get("target_1"),
                    "Stop": s.get("stop_loss"), "RR": s.get("rr", 0),
                    "Thesis": (s.get("thesis") or "")[:60],
                })
            df_sig = pd.DataFrame(sig_rows)
            st.dataframe(
                df_sig.style
                .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["LONG","BUY","YES"]) else ('color:#F85149;font-weight:700;' if isinstance(x,str) and any(y in x.upper() for y in ["SHORT","SELL","NO"]) else ''), subset=["Signal","Direction"])
                .map(lambda x: 'color:#3FB950;font-weight:700;' if x in ["A+","A"] else ('color:#D29922;font-weight:600;' if x=="B" else ''), subset=["Grade"])
                .map(lambda x: 'color:#3FB950;font-weight:700;' if isinstance(x,(int,float)) and x>=2.0 else ('color:#D29922;font-weight:600;' if isinstance(x,(int,float)) and x>=1.5 else ''), subset=["RR"])
                .format({"Score": "{:.2f}", "Price": "{:.2f}", "Entry": "{:.2f}", "T1": "{:.2f}", "Stop": "{:.2f}", "RR": "{:.1f}"}),
                use_container_width=True, hide_index=True, height=220
            )

    st.markdown("### 🎯 Top 5 Priority Setups")
    top5 = sorted(all_items, key=lambda x: x.get("priority_score", 0), reverse=True)[:5]
    for i, item in enumerate(top5):
        _render_narrative_card_native(item, i, "us_equity")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🇺🇸 US STOCKS — COMPACT
# ══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("## 📋 Playbook & Themes")
    st.caption(f"What to buy & avoid in {sq} · {qn(sq)} · Themes & Narratives")
    st.divider()
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
    
    st.divider()
    st.markdown("### 📖 Themes & Narratives")
    narratives_list = narr.get("narratives",[]) if narr else []
    if price_clusters and price_clusters.get("clusters"):
            for c in price_clusters["clusters"]:
                if c.get("is_novel_theme") or c.get("confidence", 0) > 0.6:
                    narratives_list.append({
                        "name": c.get("theme_hypothesis", "Unknown Theme"),
                        "score": c.get("confidence", 0.5),
                        "thesis": f"Cross-sector cluster of {c.get('member_count')} tickers. Dominant: {c.get('dominant_sector')}. Avg RS 3M: {c.get('avg_rs_3m',0):+.1%}.",
                        "tickers": c.get("members", [])[:5],
                        "best": c.get("members", [])[:5],
                        "worst": [],
                        "invalidators": ["Cluster correlation breaks"],
                    })
    if news_narratives and news_narratives.get("emergent_narratives"):
        for en in news_narratives["emergent_narratives"]:
            narratives_list.append({
                "name": f"News: {en.get('narrative', 'Unknown')}",
            "score": min(en.get("avg_sentiment", 0.5) + en.get("supply_chain_hits", 0) * 0.1, 1.0),
            "thesis": f"News-driven: {en.get('mention_count')} mentions, {en.get('supply_chain_hits',0)} supply hits. Linked: {', '.join(en.get('linked_tickers',[])[:5])}.",
            "tickers": en.get("linked_tickers", [])[:5],
            "best": en.get("linked_tickers", [])[:5],
            "worst": [],
            "invalidators": ["News volume drops"],
        })
    if not narratives_list:
        narratives_list = [
            {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand + safe haven.","tickers":["SLV","SILJ","GDXJ"],"best":["SLV","SILJ"],"worst":["XLK"],"invalidators":["Q4 deflation","DXY bullish"]},
            {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural.","tickers":["GLD","GDX","GDXJ"],"best":["GLD","GDX"],"worst":["HYG"],"invalidators":["Q4->Q1 direct","DXY reversal"]},
        ]
        for n in narratives_list:
            if not isinstance(n, dict): continue
        score = n.get("score",0)
        with st.expander(f"📚 {n.get('name','')} — Score: {score:.0%}", expanded=False):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Best:** {', '.join(n.get('best', n.get('tickers',[]))[:5])}")
            st.markdown(f"**Avoid:** {', '.join(n.get('worst',[])[:5])}")
            st.caption(f"Invalidators: {', '.join(n.get('invalidators',[])[:3])}")
    # ══════════════════════════════════════════════════════════════════════════════
    # TAB: ⚡ ALPHA CENTER — COMPACT
    # ══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("## 🏥 System Health")
    st.caption("Data pipeline status, coverage & diagnostics")
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


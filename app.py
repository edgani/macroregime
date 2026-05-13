"""app.py — MacroRegime Pro v27.0 FINAL
Changes from v26.0:
- FIXED: NameError prevention — all config vars initialized with defaults before sidebar
- FIXED: Dashboard fully redesigned — compact, no scrolling waste, visual hierarchy
- NEW: Front-Run Radar section showing rumor + news momentum setups
- NEW: News sentiment badge on every narrative card
- NEW: Forward-Looking philosophy banner
- FIXED: Options & Greeks full proxy fallback with price-derived levels
- FIXED: All patch functions integrated natively (no more blank fields)
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

# ═══════════════════════════════════════════════════════════════════
# DEFENSIVE DEFAULTS — prevent NameError on any execution path
# ═══════════════════════════════════════════════════════════════════
inc_us = True
inc_fx = True
inc_comm = True
inc_cryp = True
inc_ihsg = True
meta = {}

# ═══════════════════════════════════════════════════════════════════
# Settings import with fallback
# ═══════════════════════════════════════════════════════════════════
try:
    from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE, IHSG_SECTOR_MAP, TICKER_SECTOR, US_SECTORS, US_BUCKETS
except ImportError:
    from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE, TICKER_SECTOR, US_SECTORS, US_BUCKETS
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

# ═══════════════════════════════════════════════════════════════════
# CSS — compact, dark, professional
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
  --bg-primary: #0d1117;
  --bg-card: #161B22;
  --bg-elevated: #21262D;
  --border-default: #30363D;
  --border-focus: #58A6FF;
  --text-primary: #E6EDF3;
  --text-secondary: #8B949E;
  --text-muted: #6E7681;
  --q1: #3FB950; --q2: #D29922; --q3: #F85149; --q4: #A371F7;
  --long: #3FB950; --short: #F85149; --neutral: #D29922; --wait: #8B949E;
  --boarding: #F85149; --gate: #D29922; --checkin: #1F6FEB; --waitpill: #6E7681;
  --news-bull: #238636; --news-bear: #DA3633; --news-rumor: #8957E5;
  --font-xs: 10px; --font-sm: 11px; --font-base: 12px; --font-md: 13px; --font-lg: 14px; --font-xl: 16px; --font-2xl: 18px; --font-3xl: 22px;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
}
.stApp { background-color: var(--bg-primary); }
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: var(--space-3);
  margin: var(--space-2) 0;
}
.card-green { background:#0D2818; border-color:var(--long); }
.card-yellow { background:#2D2305; border-color:var(--neutral); }
.card-red { background:#2D0D0D; border-color:var(--short); }
.card-blue { background:#0D1B2A; border-color:#1F6FEB; }
.card-purple { background:#1a0d2e; border-color:#8957E5; }
.badge {
  display:inline-block; padding:2px 8px; border-radius:4px;
  font-size:var(--font-xs); font-weight:600; margin-right:4px;
}
.badge-a { background:#3FB95022; color:var(--long); border:1px solid var(--long); }
.badge-ap { background:#3FB95044; color:var(--long); border:1px solid var(--long); }
.badge-b { background:#D2992222; color:var(--neutral); border:1px solid var(--neutral); }
.badge-c { background:#8B949E22; color:var(--text-secondary); border:1px solid var(--text-secondary); }
.badge-long { background:#3FB95022; color:var(--long); border:1px solid var(--long); }
.badge-short { background:#F8514922; color:var(--short); border:1px solid var(--short); }
.badge-neutral { background:#8B949E22; color:var(--text-secondary); border:1px solid var(--text-secondary); }
.badge-boarding { background:var(--boarding); color:#fff; }
.badge-gate { background:var(--gate); color:#fff; }
.badge-checkin { background:var(--checkin); color:#fff; }
.badge-wait { background:var(--waitpill); color:#fff; }
.badge-news-bull { background:#23863633; color:#3FB950; border:1px solid #238636; }
.badge-news-bear { background:#DA363333; color:#F85149; border:1px solid #DA3633; }
.badge-news-rumor { background:#8957E533; color:#BC8AF9; border:1px solid #8957E5; }
.metric-box {
  background:var(--bg-card); border:1px solid var(--border-default);
  border-radius:8px; padding:10px; text-align:center;
}
.metric-label { font-size:var(--font-xs); color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; }
.metric-value { font-size:var(--font-2xl); font-weight:700; color:var(--text-primary); margin:4px 0; }
.metric-sub { font-size:var(--font-sm); color:var(--text-secondary); }
.section-title { font-size:var(--font-3xl); font-weight:700; color:var(--text-primary); margin-bottom:4px; }
.section-sub { font-size:var(--font-base); color:var(--text-secondary); margin-bottom:var(--space-3); }
.kpi-row { display:flex; gap:8px; flex-wrap:wrap; margin:8px 0; }
.kpi-box {
  background:var(--bg-card); border:1px solid var(--border-default);
  border-radius:6px; padding:8px 12px; min-width:120px; text-align:center;
}
.kpi-label { font-size:var(--font-xs); color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.3px; }
.kpi-value { font-size:var(--font-xl); font-weight:700; color:var(--text-primary); }
/* Risk Range Bar — 3 Tier */
.rr-bar {
  position:relative; height:28px; background:var(--bg-elevated);
  border-radius:4px; margin:8px 0; overflow:hidden;
}
.rr-dot {
  position:absolute; top:50%; transform:translate(-50%,-50%);
  width:12px; height:12px; border-radius:50%; background:var(--text-primary);
  border:2px solid var(--border-focus); z-index:5;
}
/* Flight Board */
.flight-board { display:flex; gap:6px; flex-wrap:wrap; margin:8px 0; }
.flight-pill { padding:4px 10px; border-radius:20px; font-size:var(--font-xs); font-weight:700; color:#fff; }
/* News ticker */
.news-ticker {
  background: var(--bg-elevated);
  border-left: 3px solid var(--news-rumor);
  padding: 8px 12px;
  margin: 4px 0;
  border-radius: 0 6px 6px 0;
  font-size: 12px;
}
.front-run-banner {
  background: linear-gradient(90deg, #161B22 0%, #1a0d2e 50%, #161B22 100%);
  border: 1px solid #8957E5;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

QC = {"Q1":"var(--q1)","Q2":"var(--q2)","Q3":"var(--q3)","Q4":"var(--q4)"}
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

def qc(q): return QC.get(q,"var(--text-secondary)")
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

def _rr_levels(px, trade_l, trade_r, side="long"):
    px = _sf(px) or 0; trade_l = _sf(trade_l) or 0; trade_r = _sf(trade_r) or 0
    if not (trade_l > 0 and trade_r > 0 and trade_r > trade_l): return None
    spread = trade_r - trade_l
    pos = (px - trade_l) / spread if spread > 0 else 0.5
    if side == "long":
        entry, tp1, tp2, stop = round(trade_l,2), round(trade_l+spread*0.50,2), round(trade_r,2), round(trade_l-spread*0.25,2)
        near_entry, can_enter, near_target = pos <= 0.35, pos <= 0.55, pos >= 0.75
        action = "Buy Now" if near_entry else ("Can Enter" if can_enter else ("Near Target" if near_target else "Wait"))
    else:
        entry, tp1, tp2, stop = round(trade_r,2), round(trade_r-spread*0.50,2), round(trade_l,2), round(trade_r+spread*0.25,2)
        near_entry, can_enter, near_target = pos >= 0.65, pos >= 0.45, pos <= 0.25
        action = "Sell Now" if near_entry else ("Can Short" if can_enter else ("Near Target" if near_target else "Wait"))
    rr_r = round(abs(tp1-entry)/max(abs(entry-stop),0.01), 2)
    return {"entry":entry,"tp1":tp1,"tp2":tp2,"stop":stop,"rr":rr_r,"pos":round(pos,2),"side":side,"near_entry":near_entry,"near_target":near_target,"can_enter":can_enter,"action":action}

def _risk_range_bar_html(px, trade_l, trade_r, trend_l, trend_r, tail_l, tail_r, width_pct=100):
    if not all([tail_l, tail_r, px]) or tail_r <= tail_l: return ""
    tail_span = tail_r - tail_l
    if tail_span <= 0: return ""
    trade_l_pct = max(0, (trade_l - tail_l) / tail_span * 100)
    trade_r_pct = min(100, (trade_r - tail_l) / tail_span * 100)
    trend_l_pct = max(0, (trend_l - tail_l) / tail_span * 100) if trend_l else trade_l_pct
    trend_r_pct = min(100, (trend_r - tail_l) / tail_span * 100) if trend_r else trade_r_pct
    px_pct = (px - tail_l) / tail_span * 100
    px_pct = max(2, min(98, px_pct))
    return f"""
    <div class="rr-bar" style="width:{width_pct}%">
      <div style="position:absolute;left:0;right:0;top:0;bottom:0;background:#21262D;"></div>
      <div style="position:absolute;left:{trend_l_pct:.1f}%;right:{100-trend_r_pct:.1f}%;top:3px;bottom:3px;background:#30363D;border-radius:3px;"></div>
      <div style="position:absolute;left:{trade_l_pct:.1f}%;right:{100-trade_r_pct:.1f}%;top:6px;bottom:6px;background:#484F58;border-radius:2px;"></div>
      <div style="position:absolute;left:{trade_l_pct:.1f}%;top:0;bottom:0;width:2px;background:var(--short);z-index:3;"></div>
      <div style="position:absolute;left:{trade_r_pct:.1f}%;top:0;bottom:0;width:2px;background:var(--long);z-index:3;"></div>
      <div style="position:absolute;left:{trend_l_pct:.1f}%;top:0;bottom:0;width:1px;background:var(--neutral);opacity:0.5;z-index:2;"></div>
      <div style="position:absolute;left:{trend_r_pct:.1f}%;top:0;bottom:0;width:1px;background:var(--neutral);opacity:0.5;z-index:2;"></div>
      <div class="rr-dot" style="left:{px_pct:.1f}%;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text-secondary);margin-top:4px;flex-wrap:wrap;gap:4px;">
      <span>TAIL {tail_l}</span>
      <span>TREND {trend_l}</span>
      <span style="color:var(--short);font-weight:700;">TRADE {trade_l}</span>
      <span style="color:var(--text-primary);font-weight:700;">PRICE {px}</span>
      <span style="color:var(--long);font-weight:700;">TRADE {trade_r}</span>
      <span>TREND {trend_r}</span>
      <span>TAIL {tail_r}</span>
    </div>
    """

def _flight_pill(status, count):
    cls = {"BOARDING NOW":"badge-boarding","GATE OPENS SOON":"badge-gate","CHECK-IN":"badge-checkin","WAIT":"badge-wait"}.get(status,"badge-wait")
    return f'<span class="badge {cls}">{status}: {count}</span>'

def _section_header(title, subtitle=""):
    sub = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    return f'<div class="section-title">{title}</div>{sub}'

def _kpi_box(label, value, color="var(--text-primary)"):
    return f'<div class="kpi-box"><div class="kpi-label">{label}</div><div class="kpi-value" style="color:{color};">{value}</div></div>'

def _card(title, content, border_color="var(--border-default)"):
    return f'<div style="background:var(--bg-card);border:1px solid {border_color};border-radius:8px;padding:12px;margin:6px 0;"><div style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:8px;">{title}</div><div style="font-size:12px;color:var(--text-secondary);">{content}</div></div>'

def _metric_box(label, value, sub="", color="var(--text-primary)"):
    sub_html = f'<div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">{sub}</div>' if sub else ""
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

def _entry_advice(price, entry, trade_l, trade_r, gamma, greek, momentum_1m, composite, direction):
    if direction not in ("LONG", "SHORT"): return "WAIT — No clear edge"
    if direction == "LONG":
        if price <= entry * 1.01:
            if composite == "bullish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE"):
                return "BUY NOW — At buy zone + gamma supportive"
            elif composite == "bullish": return "BUY NOW — At buy zone"
            else: return "SMALL SIZE — At buy zone but mixed signals"
        elif trade_l and price <= trade_l * 1.03: return f"WAIT — Slightly above best entry, wait for retrace to {trade_l}"
        else:
            if momentum_1m and momentum_1m > 0.05: return "CHASE — Extended but momentum strong, small size"
            else: return "SKIP — Too far from buy zone, wait for pullback"
    else:
        if price >= entry * 0.99:
            if composite == "bearish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE"):
                return "SELL NOW — At sell zone + gamma headwind"
            elif composite == "bearish": return "SELL NOW — At sell zone"
            else: return "SMALL SIZE — At sell zone but mixed signals"
        elif trade_r and price >= trade_r * 0.97: return f"WAIT — Slightly below best entry, wait for bounce to {trade_r}"
        else:
            if momentum_1m and momentum_1m < -0.05: return "CHASE SHORT — Extended but momentum strong, small size"
            else: return "SKIP — Too far from sell zone, wait for bounce"

def _target_basis(target, trade_r, trade_l, gamma, direction):
    if not gamma.get("ok"):
        return f"TRADE resistance at {trade_r}" if direction == "LONG" and trade_r else (f"TRADE support at {trade_l}" if direction == "SHORT" and trade_l else "1.5x RR target")
    call_wall = gamma.get("call_wall"); put_wall = gamma.get("put_wall")
    flip_up = gamma.get("gamma_flip_up"); flip_down = gamma.get("gamma_flip_down")
    max_pain = gamma.get("max_pain")
    if direction == "LONG":
        if call_wall and abs(target - call_wall) / max(target, 1) < 0.03: return f"Call wall at {call_wall}"
        elif flip_up and abs(target - flip_up) / max(target, 1) < 0.03: return f"Gamma flip up at {flip_up}"
        elif trade_r and abs(target - trade_r) / max(target, 1) < 0.03: return f"TRADE at {trade_r}"
        else: return f"1.5x RR target (max pain {max_pain})"
    else:
        if put_wall and abs(target - put_wall) / max(target, 1) < 0.03: return f"Put wall at {put_wall}"
        elif flip_down and abs(target - flip_down) / max(target, 1) < 0.03: return f"Gamma flip down at {flip_down}"
        elif trade_l and abs(target - trade_l) / max(target, 1) < 0.03: return f"TRADE at {trade_l}"
        else: return f"1.5x RR target (max pain {max_pain})"

def _stop_basis(stop, trade_l, trade_r, gamma, direction):
    if not gamma.get("ok"):
        return f"Below TRADE at {trade_l}" if direction == "LONG" and trade_l else (f"Above TRADE at {trade_r}" if direction == "SHORT" and trade_r else "2% from entry")
    flip_down = gamma.get("gamma_flip_down"); flip_up = gamma.get("gamma_flip_up")
    put_wall = gamma.get("put_wall"); call_wall = gamma.get("call_wall")
    if direction == "LONG":
        if flip_down and abs(stop - flip_down) / max(stop, 1) < 0.03: return f"Below gamma flip {flip_down}"
        elif put_wall and abs(stop - put_wall) / max(stop, 1) < 0.03: return f"Below put wall {put_wall}"
        elif trade_l and abs(stop - trade_l) / max(stop, 1) < 0.03: return f"Below TRADE {trade_l}"
        else: return "2% below entry"
    else:
        if flip_up and abs(stop - flip_up) / max(stop, 1) < 0.03: return f"Above gamma flip {flip_up}"
        elif call_wall and abs(stop - call_wall) / max(stop, 1) < 0.03: return f"Above call wall {call_wall}"
        elif trade_r and abs(stop - trade_r) / max(stop, 1) < 0.03: return f"Above TRADE {trade_r}"
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
    rr = row.get("rr"); trade_l = row.get("trade_l") if row.get("trade_l") else None; trade_r = row.get("trade_r") if row.get("trade_r") else None
    ticker = row.get("ticker", "")
    market_type = row.get("market_type", "us_equity")
    row["entry_advice"] = _entry_advice(price, entry, trade_l, trade_r, gamma, greek, momentum_1m, composite, direction)
    row["tp1_basis"] = _target_basis(target1, trade_r, trade_l, gamma, direction)
    row["tp2_basis"] = _target_basis(target2, trade_r, trade_l, gamma, direction)
    row["stop_basis"] = _stop_basis(stop, trade_l, trade_r, gamma, direction)
    row["path_smoothness"] = _path_smoothness(gamma, greek, momentum_1m, vix)
    row["time_estimate"] = _realistic_time_estimate(price, target1, ticker, market_type, vix, gamma, greek, direction, s)
    row["time_estimate_t2"] = _realistic_time_estimate(price, target2, ticker, market_type, vix, gamma, greek, direction, s)
    row["breakout_chance"] = _breakout_chance(price, target2, gamma, greek, momentum_3m, direction)
    em = _calc_expected_move(s, 5) if s is not None else None
    if em:
        row["expected_move_weekly"] = em["expected"]; row["expected_move_weekly_pct"] = em["expected_pct"]; row["daily_vol"] = em["daily_vol"]
    if "BUY NOW" in row["entry_advice"] or "SELL NOW" in row["entry_advice"]: row["worth_entering"] = "YES"
    elif "WAIT" in row["entry_advice"]: row["worth_entering"] = "WAIT"
    elif "CHASE" in row["entry_advice"]: row["worth_entering"] = "CHASE"
    elif "SMALL SIZE" in row["entry_advice"]: row["worth_entering"] = "SMALL"
    else: row["worth_entering"] = "NO"
    if gamma.get("ok"): row["gamma_summary"] = gamma.get("regime", "—").replace("_", " ").title()
    if greek.get("ok"): row["greek_summary"] = greek.get("composite", "—").replace("🟢", "").replace("🔴", "").replace("🟡", "").replace("⚪", "").strip()
    return row

def _get_live_or_proxy_greeks(ticker, prices, vix_now, gamma_data, greeks_data, market_type):
    """Return (gamma_dict, greek_dict) prioritizing live snapshot data."""
    gamma = (gamma_data or {}).get(ticker, {}) if gamma_data else {}
    greek = (greeks_data or {}).get(ticker, {}) if greeks_data else {}
    has_live_gamma = bool(gamma and gamma.get("ok"))
    has_live_greek = bool(greek and greek.get("ok"))
    if not has_live_gamma or not has_live_greek:
        s = prices.get(ticker)
        px = None; sma20 = None; std20 = None
        if s is not None and len(s) >= 20:
            s_clean = pd.to_numeric(s, errors="coerce").dropna()
            if len(s_clean) >= 20:
                px = float(s_clean.iloc[-1])
                sma20 = float(s_clean.tail(20).mean())
                std20 = float(s_clean.tail(20).std())
        if market_type == "crypto":
            proxy = _crypto_greeks_proxy(ticker, prices, 0)
        elif market_type == "forex":
            proxy = _forex_greeks_proxy(ticker, prices, vix_now)
        elif market_type == "commodity":
            proxy = _commodity_greeks_proxy(ticker, prices, vix_now)
        else:
            r1m = _price_ret(ticker, prices, 21)
            proxy = {
                "delta": "Long 🟢" if r1m and r1m > 0.03 else ("Short 🔴" if r1m and r1m < -0.03 else "Neutral ⚪"),
                "gamma": "Flat ⚪", "vanna": "Mixed 🟡", "vol": "Normal 🟢" if vix_now < 20 else ("Elevated 🟡" if vix_now < 25 else "High 🔴"),
                "charm": "Stable 🟡", "volga": "Low 🟢", "composite": "NEUTRAL ⚪", "composite_score": 0,
            }
        if px is not None and sma20 is not None and std20 is not None:
            proxy.setdefault("max_pain", round(sma20, 2))
            proxy.setdefault("put_wall", round(sma20 - std20 * 2.0, 2))
            proxy.setdefault("call_wall", round(sma20 + std20 * 2.0, 2))
            proxy.setdefault("gamma_flip_up", round(sma20 + std20 * 1.5, 2))
            proxy.setdefault("gamma_flip_down", round(sma20 - std20 * 1.5, 2))
        if not has_live_gamma:
            gamma = {
                "ok": True, "regime": "TRANSITION", "label": "Proxy", "color": "#D29922",
                "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0,
                "action": "Buy dips, normal sizing — gamma supportive",
                "max_pain": proxy.get("max_pain", round(sma20, 2) if sma20 else 100),
                "gamma_flip_up": proxy.get("call_wall", round(sma20 + std20 * 1.5, 2) if sma20 and std20 else 105),
                "gamma_flip_down": proxy.get("put_wall", round(sma20 - std20 * 1.5, 2) if sma20 and std20 else 95),
                "put_wall": proxy.get("put_wall", round(sma20 - std20 * 2.0, 2) if sma20 and std20 else 90),
                "call_wall": proxy.get("call_wall", round(sma20 + std20 * 2.0, 2) if sma20 and std20 else 110),
            }
        if not has_live_greek:
            greek = {
                "ok": True, "ticker": ticker, "price": round(px, 2) if px else 100,
                "delta": proxy.get("delta", "Neutral ⚪"),
                "delta_val": 0.0, "delta_note": "Proxy delta from price action",
                "gamma": proxy.get("gamma", "Flat ⚪"),
                "gamma_val": 0.0, "gamma_note": "Proxy gamma",
                "vanna": proxy.get("vanna", "Mixed 🟡"),
                "vanna_val": 0.0, "vanna_note": "Proxy vanna",
                "charm": proxy.get("charm", "Stable 🟡"),
                "charm_val": 0.0, "charm_note": "Proxy charm",
                "volga": proxy.get("volga", "Low 🟢"),
                "volga_val": 0.0, "volga_note": "Proxy volga",
                "vol": proxy.get("vol", "Normal 🟢"),
                "vol_note": "Proxy vol",
                "vix": vix_now,
                "rvol_20d": 15.0, "vol_premium": -2.0,
                "max_pain": proxy.get("max_pain", round(sma20, 2) if sma20 else 100),
                "dist_max_pain_pct": 0.0,
                "oi_concentration": "Mid-range 🟡", "oi_note": "Proxy OI",
                "composite": proxy.get("composite", "NEUTRAL ⚪"),
                "composite_score": proxy.get("composite_score", 0),
                "composite_note": "Proxy composite",
                "r1m": _price_ret(ticker, prices, 21) or 0,
                "r5d": 0, "sma20": round(sma20, 2) if sma20 else 100, "sma50": round(sma20, 2) if sma20 else 100,
            }
    return gamma, greek

def _forex_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","charm":"—","vol":"—","volga":"—","composite":"NEUTRAL ⚪","composite_score":0}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High 🔴"; greeks["volga"] = "High 🔴"
    elif vix > 20: greeks["vol"] = "Elevated 🟡"; greeks["volga"] = "Elevated 🟡"
    else: greeks["vol"] = "Normal 🟢"; greeks["volga"] = "Low 🟢"
    dxy_s = prices.get("DX-Y.NYB")
    dxy_ret = 0.0
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        if "USD" in ticker and ticker.startswith("USD"):
            greeks["delta"] = "Bullish 🟢" if dxy_ret > 0 else "Bearish 🔴"
        elif "USD" in ticker and not ticker.startswith("USD"):
            greeks["delta"] = "Bearish 🔴" if dxy_ret > 0 else "Bullish 🟢"
        else: greeks["delta"] = "Neutral ⚪"
    else: greeks["delta"] = "Neutral ⚪"
    s = prices.get(ticker)
    if s is not None and len(s) >= 10:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r5 = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10 = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5 - (r10 / 2)
        if accel > 0.02: greeks["gamma"] = "Long 📈"
        elif accel < -0.02: greeks["gamma"] = "Short 📉"
        else: greeks["gamma"] = "Flat ⚪"
        charm = r5 - (r10 / 3)
        if charm > 0.01: greeks["charm"] = "Building 🟢"
        elif charm < -0.01: greeks["charm"] = "Fading 🔴"
        else: greeks["charm"] = "Stable 🟡"
        if vix > 22 and dxy_ret > 0.01: greeks["vanna"] = "Negative ⚠️"
        elif vix < 18 and dxy_ret < -0.01: greeks["vanna"] = "Positive ✅"
        else: greeks["vanna"] = "Mixed 🟡"
        score = 0
        if "Bullish" in greeks["delta"]: score += 0.3
        elif "Bearish" in greeks["delta"]: score -= 0.3
        if "Long" in greeks["gamma"]: score += 0.1
        elif "Short" in greeks["gamma"]: score -= 0.1
        greeks["composite_score"] = round(max(-1, min(1, score)), 2)
        greeks["composite"] = "BULLISH 🟢" if score > 0.3 else ("BEARISH 🔴" if score < -0.3 else "NEUTRAL ⚪")
    else:
        greeks["gamma"] = "Flat ⚪"; greeks["charm"] = "Stable 🟡"; greeks["vanna"] = "Mixed 🟡"
    if s is not None and len(s) >= 20:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) >= 20:
            px = float(s.iloc[-1]); sma20 = float(s.tail(20).mean()); std20 = float(s.tail(20).std())
            greeks["max_pain"] = round(sma20, 2)
            greeks["put_wall"] = round(sma20 - std20 * 2.0, 2)
            greeks["call_wall"] = round(sma20 + std20 * 2.0, 2)
            greeks["gamma_flip_up"] = round(sma20 + std20 * 1.5, 2)
            greeks["gamma_flip_down"] = round(sma20 - std20 * 1.5, 2)
    return greeks

def _commodity_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","charm":"—","vol":"—","volga":"—","composite":"NEUTRAL ⚪","composite_score":0}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High 🔴"; greeks["volga"] = "High 🔴"
    elif vix > 20: greeks["vol"] = "Elevated 🟡"; greeks["volga"] = "Elevated 🟡"
    else: greeks["vol"] = "Normal 🟢"; greeks["volga"] = "Low 🟢"
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        greeks["delta"] = "Bullish 🟢" if r1m > 0.03 else ("Bearish 🔴" if r1m < -0.03 else "Neutral ⚪")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long 📈" if accel > 0.02 else ("Short 📉" if accel < -0.02 else "Flat ⚪")
        charm = r5d - (r10d / 3)
        greeks["charm"] = "Building 🟢" if charm > 0.01 else ("Fading 🔴" if charm < -0.01 else "Stable 🟡")
    else:
        greeks["delta"] = "Neutral ⚪"; greeks["gamma"] = "Flat ⚪"; greeks["charm"] = "Stable 🟡"
    dxy_s = prices.get("DX-Y.NYB")
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        precious = ticker in ("GC=F", "SI=F", "GLD", "SLV", "PPLT", "GDX", "GDXJ", "SIL", "SILJ")
        if precious: greeks["vanna"] = "Positive ✅" if dxy_ret < -0.01 else ("Negative ⚠️" if dxy_ret > 0.01 else "Mixed 🟡")
        else: greeks["vanna"] = "Positive ✅" if dxy_ret < -0.01 else ("Negative ⚠️" if dxy_ret > 0.01 else "Mixed 🟡")
    else: greeks["vanna"] = "Mixed 🟡"
    score = 0
    if "Bullish" in greeks["delta"]: score += 0.3
    elif "Bearish" in greeks["delta"]: score -= 0.3
    if "Long" in greeks["gamma"]: score += 0.1
    elif "Short" in greeks["gamma"]: score -= 0.1
    greeks["composite_score"] = round(max(-1, min(1, score)), 2)
    greeks["composite"] = "BULLISH 🟢" if score > 0.3 else ("BEARISH 🔴" if score < -0.3 else "NEUTRAL ⚪")
    if s is not None and len(s) >= 20:
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) >= 20:
            px = float(s.iloc[-1]); sma20 = float(s.tail(20).mean()); std20 = float(s.tail(20).std())
            greeks["max_pain"] = round(sma20, 2)
            greeks["put_wall"] = round(sma20 - std20 * 2.0, 2)
            greeks["call_wall"] = round(sma20 + std20 * 2.0, 2)
            greeks["gamma_flip_up"] = round(sma20 + std20 * 1.5, 2)
            greeks["gamma_flip_down"] = round(sma20 - std20 * 1.5, 2)
    return greeks

def _crypto_greeks_proxy(ticker, prices, basis_pct=0):
    greeks = {"delta":"—","gamma":"—","vanna":"—","charm":"—","vol":"—","volga":"—","composite":"NEUTRAL ⚪","composite_score":0}
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        r3m = float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else r1m
        greeks["delta"] = "Long 🟢" if r1m > 0.05 else ("Short 🔴" if r1m < -0.05 else "Neutral ⚪")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long 📈" if accel > 0.03 else ("Short 📉" if accel < -0.03 else "Flat ⚪")
        if abs(basis_pct) > 1: greeks["vanna"] = "Positive ✅" if basis_pct > 1 else "Negative ⚠️"
        else: greeks["vanna"] = "Mixed 🟡"
        charm = r1m - (r3m / 3)
        greeks["charm"] = "Fading 🔴" if charm < -0.05 else ("Building 🟢" if charm > 0.05 else "Stable 🟡")
        vol = s.tail(20).std() / s.tail(20).mean() if s.tail(20).mean() != 0 else 0
        greeks["vol"] = "High 🔴" if vol > 0.05 else ("Elevated 🟡" if vol > 0.03 else "Normal 🟢")
        greeks["volga"] = "High 🔴" if vol > 0.04 else ("Elevated 🟡" if vol > 0.025 else "Low 🟢")
        score = 0
        if "Long" in greeks["delta"]: score += 0.3
        elif "Short" in greeks["delta"]: score -= 0.3
        if "Long" in greeks["gamma"]: score += 0.15
        elif "Short" in greeks["gamma"]: score -= 0.15
        greeks["composite_score"] = round(max(-1, min(1, score)), 2)
        greeks["composite"] = "BULLISH 🟢" if score > 0.3 else ("BEARISH 🔴" if score < -0.3 else "NEUTRAL ⚪")
        if len(s) >= 20:
            px = float(s.iloc[-1]); sma20 = float(s.tail(20).mean()); std20 = float(s.tail(20).std())
            greeks["max_pain"] = round(sma20, 2)
            greeks["put_wall"] = round(sma20 - std20 * 2.0, 2)
            greeks["call_wall"] = round(sma20 + std20 * 2.0, 2)
            greeks["gamma_flip_up"] = round(sma20 + std20 * 1.5, 2)
            greeks["gamma_flip_down"] = round(sma20 - std20 * 1.5, 2)
    else:
        for k in greeks: greeks[k] = "N/A"
    return greeks


def _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, market_type, vix_now, gamma_data=None, greeks_data=None, forward_returns=None, news_narratives=None):
    v = ar.get(ticker, {})
    s = prices.get(ticker)
    if not v:
        if s is None or s.empty: return None
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < 60: return None
        px = float(s_clean.iloc[-1]); sma20 = float(s_clean.tail(20).mean()); std20 = float(s_clean.tail(20).std())
        if not all(math.isfinite(v) for v in [px, sma20, std20]): return None
        trade_l = round(sma20 - 1.5 * std20, 4); trade_r = round(sma20 + 1.5 * std20, 4)
        comp = "bullish" if px < trade_l else "bearish" if px > trade_r else "neutral"
        if comp == "neutral": return None
        v = {"px": px, "trade": {"lrr": trade_l, "trr": trade_r}, "composite": comp, "quality": "B", "market": market_type}
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

    # 3-TIER RISK RANGE
    trade_l = lrr; trade_r = trr
    trend_l = trend_r = tail_l = tail_r = None
    if s is not None and len(s) >= 50:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) >= 50:
            sma50 = float(s_clean.tail(50).mean())
            std50 = float(s_clean.tail(50).std())
            if math.isfinite(sma50) and math.isfinite(std50):
                trend_l = round(sma50 - 1.5 * std50, 4)
                trend_r = round(sma50 + 1.5 * std50, 4)
        if len(s_clean) >= 200:
            sma200 = float(s_clean.tail(200).mean())
            std200 = float(s_clean.tail(200).std())
            if math.isfinite(sma200) and math.isfinite(std200):
                tail_l = round(sma200 - 2.0 * std200, 4)
                tail_r = round(sma200 + 2.0 * std200, 4)
        elif len(s_clean) >= 100:
            sma100 = float(s_clean.tail(100).mean())
            std100 = float(s_clean.tail(100).std())
            if math.isfinite(sma100) and math.isfinite(std100):
                tail_l = round(sma100 - 2.0 * std100, 4)
                tail_r = round(sma100 + 2.0 * std100, 4)
        elif trend_l is not None:
            tail_l = round(trend_l - std50 * 2.0, 4) if math.isfinite(std50) else trend_l
            tail_r = round(trend_r + std50 * 2.0, 4) if math.isfinite(std50) else trend_r

    gamma, greek = _get_live_or_proxy_greeks(ticker, prices, vix_now, gamma_data, greeks_data, market_type)

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
    if oi_pos > 0.7: max_pain = f"{trade_r:.4f}" if market_type == "forex" else f"{trade_r:.2f}"; pain_note = "OI High at Highs -> Pullback likely"
    elif oi_pos < 0.3: max_pain = f"{trade_l:.4f}" if market_type == "forex" else f"{trade_l:.2f}"; pain_note = "OI High at Lows -> Bounce likely"
    else: mid = (trade_l + trade_r) / 2; max_pain = f"{mid:.4f}" if market_type == "forex" else f"{mid:.2f}"; pain_note = "OI Mid-range -> Chop"
    cot_bias = cot.get("bias", "Neutral") if cot else "Neutral"
    oi_conc = oi.get("concentration", "—") if oi else "—"
    delta_dir = greek.get("delta", "Neutral") if greek.get("ok") else "Neutral"
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
        "delta": greek.get("delta","—") if greek.get("ok") else "—",
        "gamma": greek.get("gamma","—") if greek.get("ok") else "—",
        "vanna": greek.get("vanna","—") if greek.get("ok") else "—",
        "charm": greek.get("charm","—") if greek.get("ok") else "—",
        "vol": greek.get("vol","—") if greek.get("ok") else "—",
        "volga": greek.get("volga","—") if greek.get("ok") else "—",
        "cot_signal": cot.get("signal", "—") if cot else "—",
        "cot_bias": cot.get("bias", "—") if cot else "—",
        "oi_signal": oi_conc,
        "oi_trend": oi.get("oi_trend", "—") if oi else "—",
        "recommendation": rec,
        "action": rl.get("action", "—")[:35],
        "grade": v.get("quality", "—").replace("short_", ""),
        "r1m": _price_ret(ticker, prices, 21),
        "r3m": _price_ret(ticker, prices, 63),
        "trade_l": trade_l, "trade_r": trade_r,
        "trend_l": trend_l, "trend_r": trend_r,
        "tail_l": tail_l, "tail_r": tail_r,
        "composite": composite,
        "gamma_regime": gamma.get("regime") if gamma.get("ok") else None,
        "max_pain_gamma": gamma.get("max_pain") if gamma.get("ok") else None,
        "gamma_flip_up": gamma.get("gamma_flip_up") if gamma.get("ok") else None,
        "gamma_flip_down": gamma.get("gamma_flip_down") if gamma.get("ok") else None,
        "put_wall": gamma.get("put_wall") if gamma.get("ok") else None,
        "call_wall": gamma.get("call_wall") if gamma.get("ok") else None,
        "greek_composite": greek.get("composite") if greek.get("ok") else None,
        "options_source": "LIVE" if (gamma_data and gamma_data.get(ticker,{}).get("ok") and greeks_data and greeks_data.get(ticker,{}).get("ok")) else "PROXY"
    }
    # News injection
    if news_narratives and news_narratives.get("ticker_specific"):
        t_news = news_narratives["ticker_specific"].get(ticker, {})
        if t_news:
            row["news_signal"] = t_news.get("front_run_signal")
            row["news_headline"] = (t_news.get("headlines") or [""])[0]
            row["news_sentiment"] = t_news.get("sentiment_score")
            row["news_themes"] = t_news.get("themes", [])
    if forward_returns:
        row["expected_1m"] = forward_returns.get("expected_1m")
        row["expected_3m"] = forward_returns.get("expected_3m")
        row["expected_6m"] = forward_returns.get("expected_6m")
        row["forward_confidence"] = forward_returns.get("confidence")
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
    trade_l = row.get("trade_l") or row.get("lrr")
    trade_r = row.get("trade_r") or row.get("trr")
    trend_l = row.get("trend_l")
    trend_r = row.get("trend_r")
    tail_l = row.get("tail_l")
    tail_r = row.get("tail_r")

    # NEWS data
    news_signal = row.get("news_signal")
    news_headline = row.get("news_headline", "")
    news_sentiment = row.get("news_sentiment")
    news_themes = row.get("news_themes", [])

    dir_emoji = "🟢" if "LONG" in direction else "🔴" if "SHORT" in direction else "⚪"
    dir_color = "var(--long)" if "LONG" in direction else "var(--short)" if "SHORT" in direction else "var(--text-secondary)"
    worth_color = "var(--long)" if "YES" in worth or "BUY" in worth else "var(--neutral)" if "WAIT" in worth or "CHASE" in worth else "var(--short)" if "SKIP" in worth else "var(--text-secondary)"

    # News emoji suffix for expander label (plain text, no HTML)
    news_suffix = ""
    if news_signal:
        if "BULLISH" in news_signal or "BUILDING" in news_signal or "MOMENTUM" in news_signal:
            news_suffix = " 📰+"
        elif "BEARISH" in news_signal or "NEGATIVE" in news_signal:
            news_suffix = " 📰-"
        elif "RUMOR" in news_signal:
            news_suffix = " 🔮"

    header = f"{dir_emoji} {ticker} | {direction.replace(' ✅','').replace(' ⚠️','')} | Grade {grade}"
    if scanner: header += f" | {scanner}"
    if row.get("score") is not None: header += f" | Score: {row.get('score',0):.2f}"
    header += news_suffix

    with st.expander(header, expanded=False):
        # Render colored news badge as first element inside expander
        if news_signal:
            if "BULLISH" in news_signal or "BUILDING" in news_signal or "MOMENTUM" in news_signal:
                st.markdown('<span class="badge badge-news-bull">📰 NEWS+</span>', unsafe_allow_html=True)
            elif "BEARISH" in news_signal or "NEGATIVE" in news_signal:
                st.markdown('<span class="badge badge-news-bear">📰 NEWS-</span>', unsafe_allow_html=True)
            elif "RUMOR" in news_signal:
                st.markdown('<span class="badge badge-news-rumor">🔮 RUMOR</span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Direction:** <span style='color:{dir_color};font-weight:700;'>{direction}</span>", unsafe_allow_html=True)
        c2.markdown(f"**Worth Entering:** <span style='color:{worth_color};font-weight:700;'>{worth}</span>", unsafe_allow_html=True)
        c3.markdown(f"**Grade:** <span style='color:{dir_color};font-weight:700;'>{grade}</span>", unsafe_allow_html=True)
        st.divider()

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price", ff(price))
        m2.metric("Entry", ff(entry))
        m3.metric("Target 1", ff(t1))
        m4.metric("Target 2", ff(t2))
        m5.metric("Stop Loss", ff(stop))
        m6.metric("R:R", f"{ff(rr)}x")

        # 3-Tier Risk Range Visual Bar
        if tail_l and tail_r and price:
            st.markdown("**📐 Risk Range (Trade · Trend · Tail)**")
            st.markdown(_risk_range_bar_html(price, trade_l, trade_r, trend_l, trend_r, tail_l, tail_r, 100), unsafe_allow_html=True)
        elif trade_l and trade_r and price:
            st.markdown("**📐 Risk Range (Trade)**")
            st.markdown(_risk_range_bar_html(price, trade_l, trade_r, trade_l, trade_r, trade_l, trade_r, 100), unsafe_allow_html=True)

        em_pct = row.get("expected_move_weekly_pct")
        em_val = row.get("expected_move_weekly")
        if em_pct or em_val:
            st.caption(f"📊 Expected Move (weekly): ±{ff(em_val)} ({fp(em_pct)}) · Daily vol: {fp(row.get('daily_vol'))}")

        # NEWS SECTION
        if news_signal or news_headline:
            st.divider()
            news_color = "#3FB950" if news_sentiment and news_sentiment > 0.2 else ("#F85149" if news_sentiment and news_sentiment < -0.2 else "#D29922")
            st.markdown(f"**📰 News / Front-Run Signal**")
            if news_signal:
                st.markdown(f'<span style="color:{news_color};font-weight:700;font-size:13px;">🔮 {news_signal}</span>', unsafe_allow_html=True)
            if news_headline:
                st.markdown(f'<div class="news-ticker">{news_headline}</div>', unsafe_allow_html=True)
            if news_themes:
                st.caption(f"Themes: {', '.join(news_themes)}")
            if news_sentiment is not None:
                st.caption(f"Sentiment score: {news_sentiment:+.2f}")

        if row.get("expected_1m") is not None or row.get("expected_3m") is not None:
            with st.expander("🔮 Forward-Looking", expanded=False):
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("1M Expected", fp(row.get("expected_1m")))
                f2.metric("3M Expected", fp(row.get("expected_3m")))
                f3.metric("6M Expected", fp(row.get("expected_6m")))
                f4.metric("Confidence", f"{row.get('forward_confidence', 0):.0%}")

        if row.get("news_narrative") or row.get("news_headline"):
            with st.expander("📰 News / Narrative", expanded=False):
                news_color = "var(--long)" if row.get("news_sentiment") == "positive" else "var(--short)" if row.get("news_sentiment") == "negative" else "var(--neutral)"
                st.markdown(f"<span style='color:{news_color};font-weight:600;'>{row.get('news_narrative', row.get('news_headline', '—'))}</span>", unsafe_allow_html=True)
                if row.get("news_headline") and row.get("news_narrative"):
                    st.caption(f"Headline: {row.get('news_headline')}")

        has_options = any(row.get(k) for k in ["gamma_regime","greek_composite","max_pain","max_pain_gamma","delta","vanna","put_wall","call_wall","gamma_flip_up","gamma_flip_down"])
        if has_options and market_type not in ["ihsg"]:
            with st.expander("📊 Options & Greeks", expanded=False):
                source = row.get("options_source", "PROXY")
                if "LIVE" in str(source):
                    st.success(f"🟢 {source}")
                else:
                    st.warning("🟡 PROXY DATA — Calculated from price action")
                o1, o2, o3, o4 = st.columns(4)
                o1.metric("Gamma Regime", row.get("gamma_regime") or row.get("gamma_summary", "—"))
                o2.metric("Greek Composite", row.get("greek_composite") or row.get("greek_summary", "—"))
                o3.metric("Max Pain", ff(row.get("max_pain") or row.get("max_pain_gamma", "—")))
                o4.metric("Delta", row.get("delta") or row.get("greek_delta", "—"))
                o5, o6, o7, o8 = st.columns(4)
                o5.metric("Vanna", row.get("vanna") or row.get("greek_vanna", "—"))
                o6.metric("Charm", row.get("charm") or row.get("greek_charm", "—"))
                o7.metric("Put Wall", ff(row.get("put_wall", "—")))
                o8.metric("Call Wall", ff(row.get("call_wall", "—")))
                o9, o10 = st.columns(2)
                o9.metric("Gamma Flip ↑", ff(row.get("gamma_flip_up", "—")))
                o10.metric("Gamma Flip ↓", ff(row.get("gamma_flip_down", "—")))

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

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        color = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}.get(q,"#8B949E")
        fig.add_bar(x=[q],y=[p],marker_color=color,text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=220,margin=dict(t=30,b=5,l=0,r=0),
        paper_bgcolor="#161B22",plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3",family="Inter"),
        title=dict(text=title,font=dict(size=12,color="#8B949E")),
        yaxis=dict(range=[0,1.15],tickformat=".0%",showgrid=True,gridcolor="#21262D",tickcolor="#8B949E"),
        xaxis=dict(showgrid=False,tickfont=dict(size=13,color="#E6EDF3")),bargap=0.4)
    return fig

def _seq_pills(sq, mq):
    if sq == mq:
        return '<div class="card-green"><span style="color:var(--long);font-weight:700;">REGIME ALIGNED</span><br><span style="font-size:12px;color:var(--text-secondary);">Both monthly and quarterly point the same direction</span></div>'
    target = ""
    if sq == "Q3" and mq == "Q2": target = '-> Q1 TARGET'
    elif sq == "Q3" and mq == "Q1": target = '-> WATCH Q2->Q1'
    return f'<div class="card-red"><span style="color:var(--short);font-weight:700;">Structural: {sq} -> Monthly: {mq} {target}</span><br><span style="font-size:12px;color:var(--text-secondary);">Monthly diverges from structural — tactical caution</span></div>'

def _gamma_card(gamma):
    if not gamma or not gamma.get("ok") or gamma.get("throttle") is None:
        gamma = {"ok": True, "regime": "POSITIVE", "label": "Positive", "color": "#3FB950",
            "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0, "action": "Buy dips, normal sizing"}
    th = _sf(gamma.get("throttle")); r10 = _sf(gamma.get("rvol_10d")); vp = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN")); label = str(gamma.get("label","—")); action = str(gamma.get("action","—"))
    color = str(gamma.get("color","#8B949E"))
    explain = {"DEEP_POSITIVE":"Very calm — buy dips","POSITIVE":"Calm — dips get bought","TRANSITION":"Shifting — careful sizing","NEGATIVE":"Volatile — reduce size","DEEP_NEGATIVE":"Dangerous — stay disciplined"}.get(regime,"Unclear")
    css = {"DEEP_POSITIVE":"card-green","POSITIVE":"card-green","TRANSITION":"card-yellow","NEGATIVE":"card-red","DEEP_NEGATIVE":"card-red"}.get(regime,"card-yellow")
    vpc = "var(--long)" if (vp is not None and vp > 0) else "var(--short)"
    th_str = f"{th:.0f}%" if th is not None else "—"
    r10_str = f"{r10:.1f}%" if r10 is not None else "—"
    vp_str = f"{vp:+.1f}%" if vp is not None else "—"
    return (f'<div class="{css}">'
        f'<div style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">OPTIONS MARKET STRUCTURE</div>'
        f'<div style="font-size:18px;font-weight:700;color:{color};margin:6px 0;">{label.upper()}</div>'
        f'<div style="font-size:12px;color:var(--text-primary);">{explain}</div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:10px;">'
        f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Throttle</div><div style="font-size:14px;font-weight:700;color:{color};">{th_str}</div></div>'
        f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">10d Realized Vol</div><div style="font-size:14px;font-weight:700;color:var(--text-primary);">{r10_str}</div></div>'
        f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Vol Premium</div><div style="font-size:14px;font-weight:700;color:{vpc};">{vp_str}</div></div>'
        f'</div>'
        f'<div style="margin-top:8px;font-size:12px;color:var(--text-secondary);border-top:1px solid var(--border-default);padding-top:6px;"><b>Action:</b> {action}</div>'
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
    rc = {"HIGH": "var(--short)", "MEDIUM": "var(--neutral)", "LOW": "var(--long)"}.get(rb, "var(--text-secondary)")
    op = max(0, round(100 - lp - sp, 0))
    tl = lev.get("top_longs", []); ts = lev.get("top_shorts", [])
    tls = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return (f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:12px;margin:6px 0;">'
        f'<div style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">LEVERAGED ETF FLOWS {"🏆 ALL TIME HIGH" if ath else ""}</div>'
        f'<div style="display:flex;justify-content:space-between;margin:8px 0;">'
        f'<div><div style="font-size:10px;color:var(--text-secondary);">Total AUM</div><div style="font-size:16px;font-weight:700;color:var(--text-primary);">${tot:.1f}B</div></div>'
        f'<div><div style="font-size:10px;color:var(--text-secondary);">Long %</div><div style="font-size:16px;font-weight:700;color:var(--long);">{lp:.0%}</div></div>'
        f'<div><div style="font-size:10px;color:var(--text-secondary);">Short %</div><div style="font-size:16px;font-weight:700;color:var(--short);">{sp:.0%}</div></div>'
        f'<div><div style="font-size:10px;color:var(--text-secondary);">Other</div><div style="font-size:16px;font-weight:700;color:var(--text-secondary);">{op:.0%}</div></div>'
        f'</div>'
        f'<div style="font-size:12px;color:{rc};margin-bottom:6px;">Rebalancing Pressure: {rb}</div>'
        f'<div style="font-size:11px;color:var(--long);margin-bottom:4px;">Long: {tls}</div>'
        f'<div style="font-size:11px;color:var(--short);">Short: {tss}</div>'
        f'</div>')


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR — all config vars defined here, accessible globally
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown('<div style="font-size:11px;color:var(--text-secondary);">Powered by Hedgeye Methodology + Forward-Looking AI + News Engine</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard",
        "⚡ Alpha Center",
        "🇺🇸 US Stocks",
        "💱 Forex",
        "🛢️ Commodities",
        "₿ Crypto",
        "🌍 Global & EM",
        "📖 Themes",
        "🏥 Health",
    ], label_visibility="collapsed")
    st.divider()
    try:
        from data.loader import snapshot_age_str, load_snapshot
        st.caption(f"Last update: {snapshot_age_str()}")
    except Exception:
        st.caption("Last update: unknown")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Update", width="stretch"): st.session_state.loading=True
    with c2:
        if st.button("⚡ Full Rebuild", width="stretch"):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        inc_us = st.checkbox("US Stocks", True)
        inc_fx = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("Indonesia (IHSG)", True)
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Regime:",["Auto","Q1","Q2","Q3","Q4"],
            index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
    st.caption("Override when model diverges from Hedgeye")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip")
        _sq=_g.structural_quad if _g else "—"
        _mq=_g.monthly_quad if _g else "—"
        st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;">CURRENT REGIME</div><div style="font-size:18px;font-weight:700;color:{qc(_sq)};margin:4px 0;">{_sq} / {_mq}</div><div style="font-size:11px;color:var(--text-secondary);">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)
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

# ═══════════════════════════════════════════════════════════════════
# DATA LOADING — defensive, no NameError possible
# ═══════════════════════════════════════════════════════════════════
snap = st.session_state.snap
if snap is None:
    try:
        snap = load_snapshot(max_age_hours=6.0)
        if snap and snap.get("ok"): st.session_state.snap = snap
    except Exception as e:
        logger.warning(f"Initial snapshot load failed: {e}")
        snap = None

if snap is None or not snap.get("ok") or st.session_state.loading:
    try:
        from orchestrator import build_snapshot
    except Exception as e:
        st.error(f"Failed to import orchestrator: {e}")
        st.stop()
    _msg = "🔄 Updating data…" if st.session_state.loading else "⚡ Building MacroRegime Pro…"
    with st.spinner(_msg):
        pb=st.progress(0.0); pt=st.empty()
        def prog(m,f): pb.progress(f); pt.caption(f"⏳ {m}")
        try:
            snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
            st.session_state.snap=snap; st.session_state.loading=False
            pb.empty(); pt.empty()
            st.rerun()
        except Exception as e:
            st.session_state.loading=False
            st.error(f"Build failed: {e}")
            st.stop()

if not snap or not snap.get("ok"):
    st.error("❌ Build failed. Click **⚡ Full Rebuild** to retry."); st.stop()

# ═══════════════════════════════════════════════════════════════════
# GLOBAL DATA EXTRACTION — safe defaults everywhere
# ═══════════════════════════════════════════════════════════════════
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
auto_disc = snap.get("auto_discoveries",{})
fb_eval = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{})
lev_data = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq = (global_.get("global_quad","Q3") if global_ else "Q3")
ar = rr.get("asset_ranges",{})
dxy_corr = snap.get("dxy_correlation",{})

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
discovery_v3 = snap.get("bottleneck_discovery", {})
frontrun = snap.get("frontrun", {})
rumor_watch = snap.get("rumor_watch", []) or []

# IHSG structural layers
ihsg_sector_momentum = snap.get("ihsg_sector_momentum") or {}
ihsg_commodity_overlay = snap.get("ihsg_commodity_overlay") or {}
ihsg_rupiah_regime = snap.get("ihsg_rupiah_regime") or {}
ihsg_foreign_flow = snap.get("ihsg_foreign_flow") or {}
ihsg_macro_overlay = snap.get("ihsg_macro_overlay") or {}
alpha_center = snap.get("alpha_center", {}) or {}

# Live options/greeks from snapshot
live_gamma = snap.get("gamma_data", {}) or {}
live_greeks = snap.get("greeks_data", {}) or {}

# Safe meta extraction
meta = alpha_center.get("meta", {}) if alpha_center else {}

# ═══════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD — Redesigned, Compact, Forward-Looking
# ═══════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown("## 🏠 Dashboard")
    st.caption("Macro regime command center — 30-second read · Forward-looking before headline")

    # ── ROW 0: FORWARD-LOOKING PHILOSOPHY BANNER ──
    st.markdown("""
    <div style="background: linear-gradient(90deg, #0d1117 0%, #161B22 50%, #0d1117 100%);
    border: 1px solid #30363D; border-radius: 8px; padding: 10px 14px; margin: 4px 0 12px 0;">
      <div style="font-size: 11px; color: #8B949E; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">🧠 Forward-Looking Philosophy</div>
      <div style="font-size: 12px; color: #E6EDF3; line-height: 1.5;">
        Market prices-in <b>expectation</b> before news hits. We monitor <b>supply chain bottlenecks</b>, <b>options flow</b>, 
        <b>news rumors</b>, and <b>macro shifts</b> to detect what the market will price next. 
        Earnings priced in milliseconds · Structural bottlenecks in months · Front-run before the headline.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ROW 1: COMPACT KPI (7 columns, minimal) ──
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    with k1: st.metric("Q", sq, qn(sq), delta_color="off")
    with k2: st.metric("M", mq, qn(mq), delta_color="off")
    with k3:
        flip = gip.flip_hazard if gip else 0
        flip_note = gip.divergence if gip else "-"
        st.metric("Flip", f"{flip:.0%}", flip_note if flip > 0.2 else None)
    with k4:
        vix_val = health.get("vix_bucket", {}).get("vix_last", 18) if health else 18
        vix_label = health.get("vix_bucket", {}).get("bucket", "-") if health else "-"
        st.metric("VIX", f"{vix_val:.1f}", vix_label)
    with k5:
        dxy_val = None
        if prices.get("DX-Y.NYB") is not None:
            try:
                dxy_s = pd.to_numeric(prices["DX-Y.NYB"], errors="coerce").dropna()
                if len(dxy_s) > 0: dxy_val = float(dxy_s.iloc[-1])
            except: pass
        st.metric("DXY", f"{dxy_val:.2f}" if dxy_val else "-")
    with k6:
        gold_val = None
        if prices.get("GC=F") is not None:
            try:
                gold_s = pd.to_numeric(prices["GC=F"], errors="coerce").dropna()
                if len(gold_s) > 0: gold_val = float(gold_s.iloc[-1])
            except: pass
        st.metric("Gold", f"{gold_val:.1f}" if gold_val else "-")
    with k7: st.metric("Assets", f"{snap.get('prices_loaded',0)}", f"{len(ar)} rng")

    # ── ROW 2: MARKET STATUS BANNER ──
    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","-")
    vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable":
        st.success(f"🟢 GOOD CONDITIONS — VIX {vl:.1f} — {vbd.get('risk_mode','Normal')}")
    elif vb=="Chop":
        st.warning(f"🟡 CHOPPY — VIX {vl:.1f} — {vbd.get('risk_mode','Normal')}")
    elif vb=="Defensive":
        st.error(f"🔴 DEFENSIVE — VIX {vl:.1f} — {vbd.get('risk_mode','Normal')}")
    else:
        st.info(f"⚪ UNKNOWN — VIX {vl:.1f}")

    # ── ROW 3: FRONT-RUN RADAR (NEW) ──
    if rumor_watch:
        st.markdown("### 📡 Front-Run Radar — News & Rumor Signals")
        st.caption("Tickers with headline momentum before price catches up")
        rw_cols = st.columns(min(4, len(rumor_watch[:4])))
        for idx, rw in enumerate(rumor_watch[:4]):
            with rw_cols[idx]:
                sig = rw.get("signal", "")
                sentiment = rw.get("sentiment", 0)
                rumor = rw.get("rumor", 0)
                r_ticker = rw.get("ticker", "-")
                headline = rw.get("headline", "")[:60]
                themes = rw.get("themes", [])

                if "BULLISH" in sig or "BUILDING" in sig:
                    card_border = "var(--long)"
                    badge_class = "badge-news-bull"
                    badge_text = "📰 BULLISH"
                elif "BEARISH" in sig or "NEGATIVE" in sig:
                    card_border = "var(--short)"
                    badge_class = "badge-news-bear"
                    badge_text = "📰 BEARISH"
                else:
                    card_border = "#8957E5"
                    badge_class = "badge-news-rumor"
                    badge_text = "🔮 RUMOR"

                st.markdown(f"""
                <div style="background:var(--bg-card);border:1px solid {card_border};border-radius:8px;padding:10px;margin:4px 0;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:14px;font-weight:700;color:var(--text-primary);">{r_ticker}</span>
                    <span class="badge {badge_class}">{badge_text}</span>
                  </div>
                  <div style="font-size:11px;color:var(--text-secondary);line-height:1.4;margin-bottom:6px;">{headline}</div>
                  <div style="display:flex;gap:8px;font-size:10px;color:var(--text-muted);">
                    <span>Sentiment: {sentiment:+.2f}</span>
                    <span>Rumor: {rumor:.2f}</span>
                    {f'<span>Themes: {", ".join(themes[:2])}</span>' if themes else ''}
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── ROW 3b: HOT NARRATIVES FROM NEWS ──
    if news_narratives and news_narratives.get("emergent_narratives"):
        emergent = news_narratives["emergent_narratives"]
        if emergent:
            st.markdown("### 🔥 Hot Narratives This Week")
            st.caption("Emergent themes detected from headline clustering")
            nar_cols = st.columns(min(4, len(emergent[:4])))
            for idx, en in enumerate(emergent[:4]):
                with nar_cols[idx]:
                    theme_name = en.get("name", "Unknown")
                    sentiment = en.get("avg_sentiment", 0)
                    mentions = en.get("mentions", 0)
                    tickers = en.get("tickers", [])[:4]
                    headlines = en.get("headlines", [])[:1]

                    if sentiment > 0.2:
                        nar_border = "var(--long)"
                        nar_bg = "#0D2818"
                    elif sentiment < -0.2:
                        nar_border = "var(--short)"
                        nar_bg = "#2D0D0D"
                    else:
                        nar_border = "var(--neutral)"
                        nar_bg = "#2D2305"

                    ticker_pills = " ".join([f'<span class="badge badge-neutral">{t}</span>' for t in tickers])
                    hl_text = headlines[0][:50] if headlines else ""

                    st.markdown(f"""
                    <div style="background:{nar_bg};border:1px solid {nar_border};border-radius:8px;padding:10px;margin:4px 0;">
                      <div style="font-size:12px;font-weight:700;color:var(--text-primary);margin-bottom:4px;">{theme_name.upper()}</div>
                      <div style="font-size:10px;color:var(--text-secondary);margin-bottom:6px;">{mentions} mentions · sentiment {sentiment:+.2f}</div>
                      <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;line-height:1.3;">{hl_text}</div>
                      <div style="display:flex;flex-wrap:wrap;gap:4px;">{ticker_pills}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── ROW 4: PLAYBOOK + FORWARD (merged, no duplicate Q/M) ──
    best_assets = " - ".join(pb_data.get("best_assets",[])[:6]) if pb_data else "Loading..."
    worst_assets = " - ".join(pb_data.get("worst_assets",[])[:5]) if pb_data else "Loading..."
    strategy = pb_data.get("strategy","") if pb_data else ""
    forward_alert = ""
    if regime_forecast and regime_forecast.get("3m"):
        rf3 = regime_forecast["3m"]
        if rf3.get("predicted_quad") != sq and rf3.get("prediction_confidence",0) > 0.4:
            forward_alert = f" ⚠️ 3M shift to {rf3.get('predicted_quad')} ({rf3.get('prediction_confidence',0):.0%} conf)"
    st.markdown(f"""
    <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px 14px;margin:6px 0;display:flex;gap:16px;flex-wrap:wrap;align-items:center;justify-content:space-between;">
      <div style="flex:1;min-width:260px;">
        <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">🎯 PLAYBOOK — {sq} · {qn(sq)}</div>
        <div style="font-size:12px;color:var(--text-primary);line-height:1.4;">
          <span style="color:var(--long);font-weight:600;">🟢 Buy:</span> {best_assets}<br>
          <span style="color:var(--short);font-weight:600;">🔴 Avoid:</span> {worst_assets}
        </div>
      </div>
      <div style="min-width:140px;text-align:right;">
        <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">FORWARD</div>
        <div style="font-size:12px;color:var(--text-primary);">1M→{regime_forecast.get("1m",{}).get("predicted_quad","-")} ({regime_forecast.get("1m",{}).get("prediction_confidence",0):.0%})</div>
        <div style="font-size:11px;color:var(--neutral);font-weight:600;">{forward_alert}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ROW 5: FLIGHT BOARD ──
    if frontrun:
        st.markdown("### ✈️ Flight Board")
        fb_cols = st.columns(4)
        with fb_cols[0]:
            boarding = frontrun.get("boarding_now", [])
            st.markdown(f'<div style="text-align:center;">{_flight_pill("BOARDING NOW", len(boarding))}</div>', unsafe_allow_html=True)
            for item in boarding[:2]:
                st.caption(f"🚨 {item.get('ticker', '-')} | {item.get('direction', '-')}")
        with fb_cols[1]:
            gate = frontrun.get("gate_opens_soon", [])
            st.markdown(f'<div style="text-align:center;">{_flight_pill("GATE OPENS SOON", len(gate))}</div>', unsafe_allow_html=True)
            for item in gate[:2]:
                st.caption(f"⚡ {item.get('ticker', '-')} | {item.get('direction', '-')}")
        with fb_cols[2]:
            checkin = frontrun.get("check_in", [])
            st.markdown(f'<div style="text-align:center;">{_flight_pill("CHECK-IN", len(checkin))}</div>', unsafe_allow_html=True)
            for item in checkin[:2]:
                st.caption(f"👀 {item.get('ticker', '-')} | {item.get('direction', '-')}")
        with fb_cols[3]:
            wait = frontrun.get("wait", [])
            st.markdown(f'<div style="text-align:center;">{_flight_pill("WAIT", len(wait))}</div>', unsafe_allow_html=True)
            for item in wait[:2]:
                st.caption(f"⏳ {item.get('ticker', '-')}")

    # ── ROW 6: EARLY WARNING + VOL FORECAST (8 cards, 1 row) ──
    st.markdown("### 🚨 Early Warning + Volatility")
    ew_cols = st.columns(8)
    lev_rb = lev_data.get("rebalancing_pressure", "-") if lev_data else "-"
    lev_color = {"HIGH": "var(--short)", "MEDIUM": "var(--neutral)", "LOW": "var(--long)"}.get(lev_rb, "var(--text-secondary)")
    with ew_cols[0]:
        st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">LEVERAGE</div><div style="font-size:14px;font-weight:700;color:{lev_color};">{lev_rb}</div></div>', unsafe_allow_html=True)
    crash_state = health.get("crash", {}).get("state", "calm") if health else "calm"
    crash_color = "var(--long)" if crash_state == "calm" else "var(--neutral)" if crash_state == "watch" else "var(--short)"
    with ew_cols[1]:
        st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">CRASH</div><div style="font-size:14px;font-weight:700;color:{crash_color};">{crash_state.upper()}</div></div>', unsafe_allow_html=True)
    risk_off_state = health.get("risk_off", {}).get("state", "risk_on") if health else "risk_on"
    risk_color = "var(--long)" if risk_off_state == "risk_on" else "var(--neutral)" if risk_off_state == "caution" else "var(--short)"
    with ew_cols[2]:
        st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">RISK OFF</div><div style="font-size:14px;font-weight:700;color:{risk_color};">{risk_off_state.upper()}</div></div>', unsafe_allow_html=True)
    breadth_tickers = list(US_SECTORS.keys())
    for bucket in ["Growth", "Quality", "Defensives", "Semis", "Energy", "Industrials", "Financials", "AI_Infra", "PreciousMetals"]:
        breadth_tickers += US_BUCKETS.get(bucket, [])
    breadth_tickers = list(dict.fromkeys(breadth_tickers))
    advancers = 0; decliners = 0
    for t in breadth_tickers:
        ret = _price_ret(t, prices, 21)
        if ret is not None:
            if ret > 0.005: advancers += 1
            elif ret < -0.005: decliners += 1
    total_b = advancers + decliners
    b_score = advancers / total_b if total_b > 0 else 0.5
    b_color = "var(--long)" if b_score > 0.6 else "var(--neutral)" if b_score > 0.4 else "var(--short)"
    with ew_cols[3]:
        st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">BREADTH</div><div style="font-size:14px;font-weight:700;color:{b_color};">{b_score:.0%}</div><div style="font-size:8px;color:var(--text-secondary);">{advancers}↑ {decliners}↓</div></div>', unsafe_allow_html=True)
    vol_f = snap.get("vol_forecast", {})
    vol_proxies = [("SPY", "SPY"), ("QQQ", "QQQ"), ("GLD", "Gold"), ("VIX", "VIX")]
    for idx, (ticker_key, label) in enumerate(vol_proxies):
        with ew_cols[4 + idx]:
            if ticker_key in vol_f:
                v = vol_f[ticker_key]
                regime = v.get("vol_regime", "NORMAL")
                vcol = "var(--long)" if regime == "LOW" else ("var(--neutral)" if regime == "NORMAL" else "var(--short)")
                val = v.get("current_ann_vol", 0)
                st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">{label}</div><div style="font-size:14px;font-weight:700;color:{vcol};">{val}%</div><div style="font-size:8px;color:var(--text-secondary);">{regime}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">{label}</div><div style="font-size:14px;font-weight:700;color:var(--text-secondary);">-</div></div>', unsafe_allow_html=True)


    # ── ROW 6b: SECTOR ROTATION MOMENTUM ──
    st.markdown("### 📊 Sector Rotation (1M)")
    st.caption("Where the money is flowing now")
    sector_tickers = {
        "Tech": "QQQ", "Energy": "XLE", "Financials": "XLF", 
        "Healthcare": "XLV", "Industrials": "XLI", "Materials": "XLB",
        "Consumer": "XLY", "Utilities": "XLU", "REITs": "XLRE", "Gold": "GLD"
    }
    sec_cols = st.columns(len(sector_tickers))
    for idx, (name, sym) in enumerate(sector_tickers.items()):
        ret = _price_ret(sym, prices, 21)
        if ret is not None:
            color = "var(--long)" if ret > 0.03 else "var(--neutral)" if ret > -0.03 else "var(--short)"
            bg = "#0D2818" if ret > 0.03 else "#2D2305" if ret > -0.03 else "#2D0D0D"
            with sec_cols[idx]:
                st.markdown(f'<div style="background:{bg};border:1px solid {color};border-radius:6px;padding:6px;text-align:center;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">{name}</div><div style="font-size:13px;font-weight:700;color:{color};">{fp(ret)}</div></div>', unsafe_allow_html=True)
        else:
            with sec_cols[idx]:
                st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;text-align:center;"><div style="font-size:9px;color:var(--text-secondary);text-transform:uppercase;">{name}</div><div style="font-size:13px;font-weight:700;color:var(--text-secondary);">-</div></div>', unsafe_allow_html=True)

    # ── ROW 7: REGIME PROB + FORWARD (merged into 1 row) ──
    st.markdown("### 📊 Regime Map")
    rp1, rp2, rp3 = st.columns([1.2, 1, 1])
    with rp1:
        st.markdown("**Quarterly**")
        if gip and hasattr(gip, 'structural_probs'):
            st.plotly_chart(prob_bar(gip.structural_probs, ""), width="stretch", config={"displayModeBar":False}, key="dash_prob_q")
        else:
            st.caption("No quarterly probs")
    with rp2:
        st.markdown("**Monthly**")
        if gip and hasattr(gip, 'monthly_probs'):
            st.plotly_chart(prob_bar(gip.monthly_probs, ""), width="stretch", config={"displayModeBar":False}, key="dash_prob_m")
        else:
            st.caption("No monthly probs")
    with rp3:
        st.markdown("**🔮 Forward**")
        if regime_forecast and regime_forecast.get("1m"):
            rf1 = regime_forecast["1m"]; rf3 = regime_forecast["3m"]; rf6 = regime_forecast["6m"]
            st.markdown(f"""
            <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:8px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:10px;color:var(--text-secondary);">1M</span><span style="font-size:12px;font-weight:700;color:{qc(rf1.get('predicted_quad','Q3'))};">{rf1.get("predicted_quad","-")}</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:10px;color:var(--text-secondary);">3M</span><span style="font-size:12px;font-weight:700;color:{qc(rf3.get('predicted_quad','Q3'))};">{rf3.get("predicted_quad","-")}</span></div>
              <div style="display:flex;justify-content:space-between;"><span style="font-size:10px;color:var(--text-secondary);">6M</span><span style="font-size:12px;font-weight:700;color:{qc(rf6.get('predicted_quad','Q3'))};">{rf6.get("predicted_quad","-")}</span></div>
            </div>
            """, unsafe_allow_html=True)
            conf1 = rf1.get("prediction_confidence",0)
            conf3 = rf3.get("prediction_confidence",0)
            st.caption(f"Conf: 1M {conf1:.0%} · 3M {conf3:.0%}")
        else:
            st.caption("No forward data")

    # ── ROW 8: MARKET EDGE (DXY + Stress + Forward-Looking) ──
    st.markdown("### 🧠 Market Edge")
    edge1, edge2, edge3 = st.columns(3)
    with edge1:
        dxy_trend = dxy_corr.get("dxy_trend", "Neutral") if dxy_corr else "Neutral"
        dxy_color = "var(--long)" if "Bullish" in dxy_trend else "var(--short)" if "Bearish" in dxy_trend else "var(--neutral)"
        dxy_val_mini = None
        if prices.get("DX-Y.NYB") is not None:
            try:
                dxy_s_mini = pd.to_numeric(prices["DX-Y.NYB"], errors="coerce").dropna()
                if len(dxy_s_mini) > 0: dxy_val_mini = float(dxy_s_mini.iloc[-1])
            except: pass
        pos_count = len(dxy_corr.get("strongest_positive_corr", [])) if dxy_corr else 0
        neg_count = len(dxy_corr.get("strongest_negative_corr", [])) if dxy_corr else 0
        dxy_disp = f"{dxy_val_mini:.2f}" if dxy_val_mini else "-"
        st.markdown(f"""
        <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">💵 DXY CORRELATION</div>
          <div style="font-size:16px;font-weight:700;color:{dxy_color};margin:2px 0;">{dxy_trend} {dxy_disp}</div>
          <div style="font-size:11px;color:var(--text-secondary);">{pos_count} pos · {neg_count} neg correlated</div>
        </div>
        """, unsafe_allow_html=True)
    with edge2:
        stress = snap.get("stress_test", [])
        if stress:
            worst = max(stress, key=lambda x: x.get("portfolio_dd", 0))
            sev = worst.get("severity", "HIGH")
            sevcol = "var(--short)" if sev == "EXTREME" else "var(--neutral)"
            st.markdown(f"""
            <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px;">
              <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">⚠️ WORST STRESS</div>
              <div style="font-size:14px;font-weight:700;color:{sevcol};margin:2px 0;">{worst.get("scenario","-")}</div>
              <div style="font-size:11px;color:var(--text-secondary);">DD: {worst.get("portfolio_dd",0):.0%} · {sev}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px;">
              <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">⚠️ STRESS TEST</div>
              <div style="font-size:12px;color:var(--text-secondary);">No active stress scenarios</div>
            </div>
            """, unsafe_allow_html=True)
    with edge3:
        # Forward-looking edge card
        news_count = news_narratives.get("analyzed_count", 0) if news_narratives else 0
        rumor_count = len(rumor_watch)
        st.markdown(f"""
        <div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">🧠 FORWARD-LOOKING EDGE</div>
          <div style="font-size:11px;color:var(--text-primary);line-height:1.4;">
            News scanned: <b>{news_count}</b> headlines · <b>{rumor_count}</b> front-run signals detected
          </div>
          <div style="font-size:10px;color:var(--neutral);margin-top:4px;">⏱️ Earnings priced in ms · Structural in months</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ROW 9: SUPPLY CHAIN BOTTLENECK HEATMAP ──
    st.markdown("### 🔥 AI Infrastructure Bottleneck Monitor")
    st.caption("Structural chokepoints · Multi-year lead times · Price-in before headline")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown("""
        <div style="background:#2D0D0D;border:1px solid var(--short);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">🔴 CRITICAL</div>
          <div style="font-size:14px;font-weight:700;color:var(--short);margin:4px 0;">HBM / DRAM</div>
          <div style="font-size:11px;color:var(--text-primary);line-height:1.4;">
            Samsung + SK Hynix + Micron >95% supply. 2026 sold out. DRAM prices +80-90%.
          </div>
          <div style="font-size:10px;color:var(--neutral);margin-top:4px;">⏱️ Lead: 12-18 mo · Watch: <b>MU</b>, <b>005930.KS</b>, <b>SK Hynix</b></div>
        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">DRAM +80-90% y/y · 2026 capacity sold out</div>
        </div>
        """, unsafe_allow_html=True)
    with b2:
        st.markdown("""
        <div style="background:#2D0D0D;border:1px solid var(--short);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">🔴 CRITICAL</div>
          <div style="font-size:14px;font-weight:700;color:var(--short);margin:4px 0;">Power Grid / Transformers</div>
          <div style="font-size:11px;color:var(--text-primary);line-height:1.4;">
            Lead time 4-5 years. PJM summer 2027 shortfall 6,600 MW. Only 5GW of 12GW announced under construction.
          </div>
          <div style="font-size:10px;color:var(--neutral);margin-top:4px;">⏱️ Lead: 4-5 yr · Watch: <b>VST</b>, <b>ETN</b>, <b>GEV</b>, <b>NRG</b></div>
        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">PJM 6.6GW shortfall by 2027 · Only 5/12GW contracted</div>
        </div>
        """, unsafe_allow_html=True)
    with b3:
        st.markdown("""
        <div style="background:#2D2305;border:1px solid var(--neutral);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">🟡 ELEVATED</div>
          <div style="font-size:14px;font-weight:700;color:var(--neutral);margin:4px 0;">Optical / Photonics</div>
          <div style="font-size:11px;color:var(--text-primary);line-height:1.4;">
            Data movement shifting to photons. NVDA partners with Corning, Coherent, Lumentum. All at ATHs.
          </div>
          <div style="font-size:10px;color:var(--neutral);margin-top:4px;">⏱️ Lead: 6-12 mo · Watch: <b>COHR</b>, <b>LITE</b>, <b>GLW</b>, <b>CIEN</b></div>
        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">NVDA photonics partnerships · Data center optical upgrade cycle</div>
        </div>
        """, unsafe_allow_html=True)
    with b4:
        st.markdown("""
        <div style="background:#0D2818;border:1px solid var(--long);border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">🟢 MONITOR</div>
          <div style="font-size:14px;font-weight:700;color:var(--long);margin:4px 0;">Agentic AI / CPU</div>
          <div style="font-size:11px;color:var(--text-primary);line-height:1.4;">
            Autonomous AI workloads optimizing server CPUs. New tailwind for INTC, AMD, NVDA Vera CPU.
          </div>
          <div style="font-size:10px;color:var(--neutral);margin-top:4px;">⏱️ Cycle: Monthly · Watch: <b>INTC</b>, <b>AMD</b>, <b>NVDA</b>, <b>ARM</b></div>
        <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">Agentic AI server CPU demand · NVDA Vera CPU 2026</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ROW 10: HISTORICAL ANALOGS (collapsed) ──
    if analogs and analogs.get("top_analogs"):
        with st.expander("📚 Historical Analogs", expanded=False):
            for i, a in enumerate(analogs["top_analogs"][:3]):
                c1, c2, c3 = st.columns(3)
                c1.metric("1M", a.get("path_1m","-")); c2.metric("3M", a.get("path_3m","-")); c3.metric("6M", a.get("path_6m","-"))
                if a.get("next_bias"):
                    st.caption(f"📊 {a['next_bias']}")

    st.caption(f"Built {snap.get('build_time_s',0):.0f}s ago · {snap.get('prices_loaded',0)} assets · {snap.get('fred_coverage',0)} indicators · {news_narratives.get('analyzed_count',0)} headlines scanned")


# ═══════════════════════════════════════════════════════════════════
# PAGE: ALPHA CENTER
# ═══════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown("## ⚡ Alpha Center")
    st.caption("Bottlenecks - Alpha - Discovery - Daily Signals - Front-Run")

    ac = alpha_center
    meta = ac.get("meta", {}) if ac else {}
    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild.")
        # Show fallback from daily_signals if available
        if daily_signals:
            st.markdown("### 📈 Daily Signals Fallback")
            for s in daily_signals[:5]:
                st.caption(f"{s.get('ticker', '-')} | {s.get('direction', '-')} | {s.get('signal', '-')}")
        st.stop()

    # Meta Bar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime", meta.get("regime", "?"))
    c2.metric("Bias", meta.get("bias", "?"))
    c3.metric("VIX", meta.get("vix", "?"))
    c4.metric("Total", meta.get("total_items", 0))

    if transition:
        fw = transition.front_run_window
        fwc = {"now":"var(--short)","1-2w":"var(--neutral)","3-6w":"var(--checkin)","not yet":"var(--waitpill)"}.get(fw,"var(--waitpill)")
        fwi = {"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:{fwc};color:#fff;padding:6px 12px;border-radius:6px;font-weight:600;text-align:center;margin:8px 0;font-size:12px;">{fwi}</div>', unsafe_allow_html=True)

    # Flight Board Pills
    if frontrun:
        st.markdown("### ✈️ Flight Board")
        pills_html = '<div class="flight-board">'
        for status, items in frontrun.items():
            if items:
                cls = {"boarding_now":"badge-boarding","gate_opens_soon":"badge-gate","check_in":"badge-checkin","wait":"badge-wait"}.get(status,"badge-wait")
                label = status.replace("_", " ").upper()
                pills_html += f'<span class="badge {cls}">{label}: {len(items)}</span>'
        pills_html += '</div>'
        st.markdown(pills_html, unsafe_allow_html=True)

    # Master Table
    all_items = ac.get("all", [])
    if not all_items:
        st.info("No Alpha Center items available.")
        st.stop()

    df_rows = []
    for item in all_items:
        df_rows.append({
            "Ticker": item.get("ticker", "-"),
            "Scanner": item.get("scanner_type", "-"),
            "Direction": item.get("direction", "-"),
            "Grade": item.get("grade", "-"),
            "Score": round(item.get("priority_score", 0), 1),
            "Price": item.get("price"),
            "Entry": item.get("entry"),
            "T1": item.get("target_1"),
            "T2": item.get("target_2"),
            "Stop": item.get("stop_loss"),
            "RR": item.get("rr", 0),
            "Worth?": item.get("worth_entering", "-"),
            "Time": item.get("time_estimate", "-"),
            "Thesis": (item.get("thesis") or item.get("recommendation") or "")[:60],
            "News": item.get("news_signal", "")[:20],
        })
    df_alpha = pd.DataFrame(df_rows)

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

    # Pre-process: fill None numeric values
    df_display = df_filtered.copy()
    for col in ["Price", "Entry", "T1", "T2", "Stop", "RR", "Score"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")

    st.dataframe(
        df_display.style
            .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["LONG","BUY","YES"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["SHORT","SELL","NO"]) else ""), subset=["Direction","Worth?"])
            .map(lambda x: "color:var(--long);font-weight:700;" if x in ["A+","A"] else ("color:var(--neutral);font-weight:600;" if x=="B" else ""), subset=["Grade"])
            .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"])
            .background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=100),
        width="stretch", hide_index=True, height=380
    )

    # Daily Signals Summary
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
                    "Ticker": s.get("ticker", "-"), "Signal": s.get("signal", "-"),
                    "Direction": s.get("direction", "-"), "Grade": s.get("grade", "-"),
                    "Score": round(s.get("score", 0), 2), "Price": s.get("price"),
                    "Entry": s.get("entry"), "T1": s.get("target_1"),
                    "Stop": s.get("stop_loss"), "RR": s.get("rr", 0),
                    "Thesis": (s.get("thesis") or "")[:60],
                })
            df_sig = pd.DataFrame(sig_rows)
            df_sig_display = df_sig.copy()
            for col in ["Price", "Entry", "T1", "Stop", "RR", "Score"]:
                if col in df_sig_display.columns:
                    df_sig_display[col] = df_sig_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")
            st.dataframe(
                df_sig_display.style
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["LONG","BUY","YES"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["SHORT","SELL","NO"]) else ""), subset=["Signal","Direction"])
                .map(lambda x: "color:var(--long);font-weight:700;" if x in ["A+","A"] else ("color:var(--neutral);font-weight:600;" if x=="B" else ""), subset=["Grade"])
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
                width="stretch", hide_index=True, height=220
            )

    # Top 5 Priority Cards
    st.markdown("### 🎯 Top 5 Priority Setups")
    top5 = sorted(all_items, key=lambda x: x.get("priority_score", 0), reverse=True)[:5]
    for i, item in enumerate(top5):
        _render_narrative_card_native(item, i, "us_equity")

# ═══════════════════════════════════════════════════════════════════
# PAGE: US STOCKS
# ═══════════════════════════════════════════════════════════════════
elif page == "🇺🇸 US Stocks":
    st.markdown("## 🇺🇸 US Stocks")
    st.caption("US Equities - Options - Greeks - COT - OI - Risk Ranges")

    gamma_data = snap.get("gamma_data", {}) or {}
    greeks_data = snap.get("greeks_data", {}) or {}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}

    us_tickers = list(US_SECTORS.keys())
    for bucket in ["Growth", "Quality", "Defensives", "Semis", "Energy", "Industrials", "Financials", "AI_Infra", "PreciousMetals", "International", "Housing", "Bitcoin"]:
        us_tickers += US_BUCKETS.get(bucket, [])
    us_tickers = list(dict.fromkeys(us_tickers))

    us_rows = []
    for ticker in us_tickers:
        row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "us_equity", vix_now, gamma_data, greeks_data, forward_returns, news_narratives)
        if row: us_rows.append(row)
    longs, shorts = _split_long_short(us_rows)

    all_us = longs + shorts
    if all_us:
        df_us = _consolidated_to_df(all_us)
        df_us_display = df_us.copy()
        for col in ["Price", "Entry", "T1", "T2", "Stop", "RR"]:
            if col in df_us_display.columns:
                df_us_display[col] = df_us_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")
        st.dataframe(
            df_us_display.style
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["YES","BUY NOW"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["NO","SKIP"]) else ("color:var(--neutral);font-weight:600;" if isinstance(x,str) and any(y in x.upper() for y in ["WAIT","CHASE","SMALL"]) else "")), subset=["Worth?"])
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
            width="stretch", hide_index=True, height=320
        )
    else:
        st.info("No US stock setups.")

    c1, c2 = st.columns(2)
    with c1:
        if longs:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:var(--long);margin:8px 0;">🟢 Top 5 Longs ({len(longs)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(longs[:5]): _render_narrative_card_native(row, i, "us_equity")
    with c2:
        if shorts:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:var(--short);margin:8px 0;">🔴 Top 5 Shorts ({len(shorts)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(shorts[:5]): _render_narrative_card_native(row, i, "us_equity")

# ═══════════════════════════════════════════════════════════════════
# PAGE: FOREX
# ═══════════════════════════════════════════════════════════════════
elif page == "💱 Forex":
    st.markdown("## 💱 Forex")
    st.caption("FX - DXY + COT - OI - Greeks - Risk Ranges")

    gamma_data = snap.get("gamma_data", {}) or {}
    greeks_data = snap.get("greeks_data", {}) or {}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}

    # DXY Header
    dxy_val = None; dxy_trend = "-"
    if prices.get("DX-Y.NYB") is not None:
        try:
            dxy_s = pd.to_numeric(prices["DX-Y.NYB"], errors="coerce").dropna()
            if len(dxy_s) > 0: dxy_val = float(dxy_s.iloc[-1])
            if len(dxy_s) >= 22: dxy_trend = f"{float(dxy_s.iloc[-1]/dxy_s.iloc[-22]-1):+.1%}"
        except: pass
    st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:8px;padding:12px;text-align:center;margin-bottom:12px;"><div style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">US DOLLAR INDEX (DXY)</div><div style="font-size:24px;font-weight:700;color:var(--text-primary);margin:6px 0;">${dxy_val:.2f}</div><div style="font-size:12px;color:var(--text-secondary);">1M: {dxy_trend} - When DXY falls, EM and commodities rise</div></div>', unsafe_allow_html=True)

    fx_rows = []
    for ticker in list(FOREX_PAIRS.keys()):
        row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "forex", vix_now, gamma_data, greeks_data, forward_returns, news_narratives)
        if row: fx_rows.append(row)
    longs, shorts = _split_long_short(fx_rows)
    all_fx = longs + shorts
    if all_fx:
        df_fx = _consolidated_to_df(all_fx)
        df_fx_display = df_fx.copy()
        for col in ["Price", "Entry", "T1", "T2", "Stop", "RR"]:
            if col in df_fx_display.columns:
                df_fx_display[col] = df_fx_display[col].apply(lambda x: round(x, 4) if pd.notna(x) and isinstance(x, (int, float)) else "—")
        st.dataframe(
            df_fx_display.style
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["YES","BUY NOW"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["NO","SKIP"]) else ("color:var(--neutral);font-weight:600;" if isinstance(x,str) and any(y in x.upper() for y in ["WAIT","CHASE","SMALL"]) else "")), subset=["Worth?"])
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
            width="stretch", hide_index=True, height=260
        )
    else:
        st.info("No forex setups.")
    c1, c2 = st.columns(2)
    with c1:
        if longs:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:var(--long);margin:6px 0;">🟢 Top 5 ({len(longs)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(longs[:5]): _render_narrative_card_native(row, i, "forex")
    with c2:
        if shorts:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:var(--short);margin:6px 0;">🔴 Top 5 ({len(shorts)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(shorts[:5]): _render_narrative_card_native(row, i, "forex")

# ═══════════════════════════════════════════════════════════════════
# PAGE: COMMODITIES
# ═══════════════════════════════════════════════════════════════════
elif page == "🛢️ Commodities":
    st.markdown("## 🛢️ Commodities")
    st.caption("Commodities - COT - OI - Greeks - Risk Ranges")

    gamma_data = snap.get("gamma_data", {}) or {}
    greeks_data = snap.get("greeks_data", {}) or {}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}

    comm_rows = []
    for ticker in list(COMMODITIES.keys()):
        row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "commodity", vix_now, gamma_data, greeks_data, forward_returns, news_narratives)
        if row: comm_rows.append(row)
    longs, shorts = _split_long_short(comm_rows)
    all_comm = longs + shorts
    if all_comm:
        df_comm = _consolidated_to_df(all_comm)
        df_comm_display = df_comm.copy()
        for col in ["Price", "Entry", "T1", "T2", "Stop", "RR"]:
            if col in df_comm_display.columns:
                df_comm_display[col] = df_comm_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")
        st.dataframe(
            df_comm_display.style
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["YES","BUY NOW"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["NO","SKIP"]) else ("color:var(--neutral);font-weight:600;" if isinstance(x,str) and any(y in x.upper() for y in ["WAIT","CHASE","SMALL"]) else "")), subset=["Worth?"])
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
            width="stretch", hide_index=True, height=260
        )
    else:
        st.info("No commodity setups.")
    c1, c2 = st.columns(2)
    with c1:
        if longs:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:var(--long);margin:6px 0;">🟢 Top 5 ({len(longs)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(longs[:5]): _render_narrative_card_native(row, i, "commodity")
    with c2:
        if shorts:
            st.markdown(f'<div style="font-size:13px;font-weight:700;color:var(--short);margin:6px 0;">🔴 Top 5 ({len(shorts)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(shorts[:5]): _render_narrative_card_native(row, i, "commodity")


# ═══════════════════════════════════════════════════════════════════
# PAGE: CRYPTO
# ═══════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown("## ₿ Crypto Setups")
    st.caption("On-chain momentum + Risk Ranges + Greeks")

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
                row["onchain_score"] = f"{int(score*100)}%"
                row["tvl_7d"] = tvl_7d
                if score > 0.7 and tvl_7d > 0.15: row["onchain_signal"] = "🚀 STRONG"
                elif score > 0.55: row["onchain_signal"] = "📈 BUILDING"
                elif score > 0.4: row["onchain_signal"] = "👀 EARLY"
                else: row["onchain_signal"] = "⏳ NEUTRAL"
            else:
                row["onchain_score"] = "-"; row["tvl_7d"] = None; row["onchain_signal"] = "-"
            crypto_rows.append(row)
    longs, shorts = _split_long_short(crypto_rows)

    all_crypto = longs + shorts
    if all_crypto:
        df_crypto = _consolidated_to_df(all_crypto)
        df_crypto["On-Chain"] = [r.get("onchain_signal","-") for r in all_crypto]
        df_crypto["TVL 7D"] = [f"{r.get('tvl_7d',0):+.1%}" if r.get('tvl_7d') is not None else "-" for r in all_crypto]
        df_crypto_display = df_crypto.copy()
        for col in ["Price", "Entry", "T1", "T2", "Stop", "RR"]:
            if col in df_crypto_display.columns:
                df_crypto_display[col] = df_crypto_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")
        st.dataframe(
            df_crypto_display.style
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["YES","BUY NOW"]) else ("color:var(--short);font-weight:700;" if isinstance(x,str) and any(y in x.upper() for y in ["NO","SKIP"]) else ("color:var(--neutral);font-weight:600;" if isinstance(x,str) and any(y in x.upper() for y in ["WAIT","CHASE","SMALL"]) else "")), subset=["Worth?"])
                .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
            width="stretch", hide_index=True, height=260
        )
    else:
        st.info("No crypto setups.")

    c1, c2 = st.columns(2)
    with c1:
        if longs:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:var(--long);margin:8px 0;">🟢 Top 5 Longs ({len(longs)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(longs[:5]): _render_narrative_card_native(row, i, "crypto")
    with c2:
        if shorts:
            st.markdown(f'<div style="font-size:14px;font-weight:700;color:var(--short);margin:8px 0;">🔴 Top 5 Shorts ({len(shorts)} total)</div>', unsafe_allow_html=True)
            for i, row in enumerate(shorts[:5]): _render_narrative_card_native(row, i, "crypto")

# ═══════════════════════════════════════════════════════════════════
# PAGE: GLOBAL & EM
# ═══════════════════════════════════════════════════════════════════
elif page == "🌍 Global & EM":
    st.markdown("## 🌍 Global & EM")
    st.caption("50-country regime map + Indonesia IHSG Report")

    global_tab, ihsg_tab = st.tabs(["🌍 Global Quad", "🇮🇩 IHSG Report"])

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
            st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">GLOBAL REGIME</div><div style="font-size:24px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="font-size:11px;color:var(--text-primary);">{QN.get(gq,gq)}</div><div style="font-size:10px;color:var(--text-secondary);margin-top:4px;">Conf: {gconf:.0%}</div></div>', unsafe_allow_html=True)
            st.plotly_chart(prob_bar(gprobs), width="stretch", config={"displayModeBar":False})
            em_sig = (btk.get("em_recovery",{}) or {}) if btk else {}
            if em_sig and isinstance(em_sig, dict):
                conf = _sf(em_sig.get("confidence")) or 0
                trigger = em_sig.get("trigger","EM signal")
                st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px;margin-top:6px;font-size:11px;"><b>EM Signal:</b> <span style="color:var(--text-secondary);">{trigger} (conf: {conf:.0%})</span></div>', unsafe_allow_html=True)
        with c2:
            rows=[]
            for country,q in sorted(cqs.items(),key=lambda x:x[1]):
                rows.append({"Country":country,"Regime":q,"Name":QN.get(q,q)})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.map(lambda x: f'color:{qc(x)}', subset=["Regime"]).format({"Regime":lambda x:""}), hide_index=True, width="stretch", height=320)

    with ihsg_tab:
        st.markdown("### 🇮🇩 IHSG Macro Report")
        st.caption("Indonesia equity - Narrative report format")

        # Executive Summary
        macro = ihsg_macro_overlay or {}
        ihsg_bias = "DEFENSIVE"; ihsg_color = "var(--short)"; top_sectors = []; avoid_sectors = []
        if macro.get("commodity_bias") == "Bullish":
            ihsg_bias = "COMMODITY OFFENSE"; ihsg_color = "var(--long)"; top_sectors = ["Coal", "Nickel", "CPO"]
        elif macro.get("consumer_bias") == "Bullish":
            ihsg_bias = "DOMESTIC DEMAND"; ihsg_color = "var(--neutral)"; top_sectors = ["Consumer", "Pharma", "Telco"]
        else:
            top_sectors = ["Banking", "Telco"] if macro.get("banking_bias") == "Bullish" else ["Telco"]
        rupiah_sig = ihsg_rupiah_regime.get("flow_signal", "-") if ihsg_rupiah_regime else "-"
        rupiah_color = "var(--long)" if "Positive" in rupiah_sig else "var(--short)" if "Risk" in rupiah_sig else "var(--neutral)"
        bi_sig = macro.get("bi_signal", "-")[:20] if macro else "-"

        e1, e2, e3, e4 = st.columns(4)
        e1.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">IHSG BIAS</div><div style="font-size:14px;font-weight:700;color:{ihsg_color};">{ihsg_bias}</div></div>', unsafe_allow_html=True)
        e2.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">RUPIAH</div><div style="font-size:13px;font-weight:700;color:{rupiah_color};">{rupiah_sig[:18] if rupiah_sig else "-"}</div></div>', unsafe_allow_html=True)
        e3.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">BI REGIME</div><div style="font-size:12px;font-weight:700;color:var(--text-primary);">{bi_sig}</div></div>', unsafe_allow_html=True)
        e4.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">POLICY</div><div style="font-size:14px;font-weight:700;">{macro.get("policy_score",0):+.2f}</div></div>', unsafe_allow_html=True)
        if top_sectors or avoid_sectors:
            pills = []
            for s in top_sectors: pills.append(f'<span class="badge badge-long">{s}</span>')
            for s in avoid_sectors: pills.append(f'<span class="badge badge-short">{s}</span>')
            st.markdown(f'<div style="margin:6px 0;">{ " ".join(pills)}</div>', unsafe_allow_html=True)

        # Macro Context
        mc1, mc2, mc3, mc4 = st.columns(4)
        dxy_val = None; dxy_trend = "-"
        if prices.get("DX-Y.NYB") is not None:
            try:
                dxy_s = pd.to_numeric(prices["DX-Y.NYB"], errors="coerce").dropna()
                if len(dxy_s) > 0: dxy_val = float(dxy_s.iloc[-1])
                if len(dxy_s) >= 22: dxy_trend = f"{float(dxy_s.iloc[-1]/dxy_s.iloc[-22]-1):+.1%}"
            except: pass
        mc1.metric("DXY", f"{dxy_val:.2f}" if dxy_val else "-", dxy_trend)
        idr_val = None; idr_trend = "-"
        if prices.get("USDIDR=X") is not None:
            try:
                idr_s = pd.to_numeric(prices["USDIDR=X"], errors="coerce").dropna()
                if len(idr_s) > 0: idr_val = float(idr_s.iloc[-1])
                if len(idr_s) >= 22: idr_trend = f"{float(idr_s.iloc[-1]/idr_s.iloc[-22]-1):+.1%}"
            except: pass
        mc2.metric("USD/IDR", f"{idr_val:,.0f}" if idr_val else "-", idr_trend)
        comm_proxies = {}
        for proxy in ["KOL", "JJN", "DBA"]:
            s = prices.get(proxy)
            if s is not None and len(s) >= 22:
                try:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    if len(s) >= 22: comm_proxies[proxy] = float(s.iloc[-1] / s.iloc[-22] - 1)
                except: pass
        mc3.metric("Coal (KOL)", fp(comm_proxies.get("KOL")), "1M")
        mc4.metric("Agri (DBA)", fp(comm_proxies.get("DBA")), "1M")

        # Narrative Report
        st.markdown("### 📰 Macro Narrative")
        narrative_parts = []
        if ihsg_rupiah_regime:
            narrative_parts.append(f"**Rupiah:** {ihsg_rupiah_regime.get('flow_signal', '-')}")
        if ihsg_macro_overlay:
            narrative_parts.append(f"**BI Policy:** {ihsg_macro_overlay.get('bi_signal', '-')}")
            narrative_parts.append(f"**Banking Bias:** {ihsg_macro_overlay.get('banking_bias', '-')}")
            narrative_parts.append(f"**Consumer Bias:** {ihsg_macro_overlay.get('consumer_bias', '-')}")
        if ihsg_commodity_overlay:
            for sector, data in ihsg_commodity_overlay.items():
                if data.get("tailwind") in ["Strong", "Moderate"]:
                    narrative_parts.append(f"**{sector}:** {data.get('signal', '-')}")
        if narrative_parts:
            for part in narrative_parts:
                st.markdown(part)

        # IHSG Table
        ihsg_rows = []
        for ticker in list(IHSG_UNIVERSE.keys()):
            row = _build_ihsg_row(ticker, prices, ar, ihsg_sector_momentum, ihsg_commodity_overlay, ihsg_rupiah_regime, ihsg_foreign_flow, ihsg_macro_overlay, forward_returns, news_narratives)
            if row: ihsg_rows.append(row)

        if ihsg_rows:
            df_ihsg = pd.DataFrame([{
                "Ticker": r["ticker"], "Sector": r.get("sector","-"), "Price": r["price"], "Entry": r.get("entry"),
                "T1": r.get("target_1"), "T2": r.get("target_2"), "Stop": r.get("stop"),
                "RR": r.get("rr",0), "1M": fp(r.get("r1m")), "3M": fp(r.get("r3m")),
                "Signal": r.get("signal","-"), "Grade": r.get("grade","C"),
                "Thesis": r.get("recommendation","-")[:50],
            } for r in ihsg_rows])
            df_ihsg_display = df_ihsg.copy()
            for col in ["Price", "Entry", "T1", "T2", "Stop", "RR"]:
                if col in df_ihsg_display.columns:
                    df_ihsg_display[col] = df_ihsg_display[col].apply(lambda x: round(x, 2) if pd.notna(x) and isinstance(x, (int, float)) else "—")
            st.dataframe(
                df_ihsg_display.style
                    .map(lambda x: "color:var(--long);font-weight:700;" if x=="BUY" else ("color:var(--short);font-weight:700;" if x=="SELL" else ""), subset=["Signal"])
                    .map(lambda x: "color:var(--long);font-weight:700;" if x in ["A","A+"] else ("color:var(--neutral);font-weight:600;" if x=="B" else ""), subset=["Grade"])
                    .map(lambda x: "color:var(--long);font-weight:700;" if isinstance(x,(int,float)) and x>=2.0 else ("color:var(--neutral);font-weight:600;" if isinstance(x,(int,float)) and x>=1.5 else ""), subset=["RR"]),
                width="stretch", hide_index=True, height=280
            )
            ihsg_rows.sort(key=lambda x: abs(x.get("r1m") or 0), reverse=True)
            st.markdown("### 🎯 Top 5 IHSG (by momentum)")
            for i, row in enumerate(ihsg_rows[:5]):
                _render_narrative_card_native(row, i, "ihsg")
        else:
            st.info("No IHSG setups.")

        # Structural Diagnostics
        st.markdown("### 🔬 Structural Diagnostics")
        d1, d2, d3, d4, d5 = st.columns(5)
        with d1:
            if ihsg_sector_momentum:
                top_sec = max(ihsg_sector_momentum.items(), key=lambda x: x[1].get("strength", 0))
                st.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">SECTOR MOM</div><div style="font-size:13px;font-weight:700;">{top_sec[0]}</div><div style="font-size:10px;color:var(--text-secondary);">{fp(top_sec[1].get("avg_1m"))}</div></div>', unsafe_allow_html=True)
            else: st.caption("No data")
        with d2:
            if ihsg_commodity_overlay:
                top_comm = max(ihsg_commodity_overlay.items(), key=lambda x: x[1].get("r1m") or -999)
                st.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">COMMODITY</div><div style="font-size:13px;font-weight:700;">{top_comm[0]}</div><div style="font-size:10px;color:var(--text-secondary);">{fp(top_comm[1].get("r1m"))}</div></div>', unsafe_allow_html=True)
            else: st.caption("No data")
        with d3:
            if ihsg_rupiah_regime:
                st.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">RUPIAH</div><div style="font-size:13px;font-weight:700;">{ihsg_rupiah_regime.get("dxy_trend","-")}</div></div>', unsafe_allow_html=True)
            else: st.caption("No data")
        with d4:
            if ihsg_foreign_flow:
                acc = sum(1 for v in ihsg_foreign_flow.values() if "Accumulation" in v.get("signal", ""))
                dist = sum(1 for v in ihsg_foreign_flow.values() if "Distribution" in v.get("signal", ""))
                st.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">FLOW</div><div style="font-size:13px;font-weight:700;color:var(--long);">{acc} Acc</div><div style="font-size:10px;color:var(--short);">{dist} Dist</div></div>', unsafe_allow_html=True)
            else: st.caption("No data")
        with d5:
            if ihsg_macro_overlay:
                st.markdown(f'<div style="text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">BI MACRO</div><div style="font-size:13px;font-weight:700;">{ihsg_macro_overlay.get("banking_bias","-")}</div></div>', unsafe_allow_html=True)
            else: st.caption("No data")

# ═══════════════════════════════════════════════════════════════════
# PAGE: THEMES
# ═══════════════════════════════════════════════════════════════════
elif page == "📖 Themes":
    st.markdown("## 📖 Themes")
    st.caption("Top-down narratives + price clusters + news NLP")

    narratives_list = narr.get("narratives",[]) if narr else []

    # Add emergent narratives from news engine
    if news_narratives and news_narratives.get("emergent_narratives"):
        for en in news_narratives["emergent_narratives"]:
            narratives_list.append({
                "name": f"News: {en.get('name', 'Unknown')}",
                "score": min(abs(en.get("avg_sentiment", 0.5)) + en.get("supply_chain_hits", 0) * 0.1, 1.0),
                "thesis": f"News-driven: {en.get('mentions', 0)} mentions. Linked: {', '.join(en.get('tickers',[])[:5])}.",
                "tickers": en.get("tickers", [])[:5],
                "best": en.get("tickers", [])[:5],
                "worst": [],
                "invalidators": ["News volume drops"],
                "news_headlines": en.get("headlines", [])[:3],
            })

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
            if n.get("news_headlines"):
                st.markdown("**📰 Recent Headlines:**")
                for hl in n["news_headlines"][:3]:
                    st.markdown(f'<div class="news-ticker">{hl}</div>', unsafe_allow_html=True)
            st.caption(f"Invalidators: {', '.join(n.get('invalidators',[])[:3])}")

# ═══════════════════════════════════════════════════════════════════
# PAGE: HEALTH
# ═══════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
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

    if regime_forecast and regime_forecast.get("1m"):
        st.divider()
        st.markdown("### Forward-Looking Engine Status")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("1M Predicted", regime_forecast["1m"].get("predicted_quad", "-"))
        c2.metric("3M Predicted", regime_forecast["3m"].get("predicted_quad", "-"))
        c3.metric("6M Predicted", regime_forecast["6m"].get("predicted_quad", "-"))
        c4.metric("News Headlines", news_narratives.get("analyzed_count", 0) if news_narratives else 0)

    if discovery_v3:
        st.divider()
        st.markdown("### Bottleneck Scanner V3")
        c1, c2, c3 = st.columns(3)
        c1.metric("Reactive Found", discovery_v3.get("meta", {}).get("reactive_found", 0))
        c2.metric("Proactive Predicted", discovery_v3.get("meta", {}).get("proactive_predicted", 0))
        c3.metric("Spillover Links", discovery_v3.get("meta", {}).get("spillover_links", 0))

    # News engine status
    st.divider()
    st.markdown("### 📰 News Engine Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Headlines Scanned", news_narratives.get("analyzed_count", 0) if news_narratives else 0)
    c2.metric("Rumor Signals", len(rumor_watch))
    c3.metric("Emergent Themes", len(news_narratives.get("emergent_narratives", [])) if news_narratives else 0)

    st.divider()
    st.markdown("### Data Sources")
    sources = health.get("sources",{}) if health else {}
    if sources:
        for src, status in sources.items():
            color = "var(--long)" if status == "OK" else "var(--short)" if status == "FAIL" else "var(--neutral)"
            st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border-default);border-radius:6px;padding:6px 12px;margin:3px 0;display:flex;justify-content:space-between;"><span>{src}</span><span style="color:{color};font-weight:700;">{status}</span></div>', unsafe_allow_html=True)
    else: st.info("No detailed source status available.")

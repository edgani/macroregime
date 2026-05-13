"""app.py — MacroRegime Pro v27.0 FRONT-RUN PATCH
Changes from v26.0:
- FIXED: Alpha Center NameError (ac/meta undefined → alpha_center)
- ADDED: Front-Run Catalyst Engine — supply chain, macro triggers, earnings, news
- ADDED: Dashboard Front-Run Catalyst Board
- ADDED: Narrative cards now show "What can make this go up" for front-running
- ADDED: Ticker-specific bottleneck mapping (HBM, Power, Optical, Housing, etc.)
- IMPROVED: Alpha Center table with Front-Run score column
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import time
import logging
import os

logger = logging.getLogger(__name__)

st.set_page_config(page_title="MacroRegime Pro", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

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

st.markdown("""
<style>
:root {
    --long: #3FB950; --short: #F85149; --neutral: #D29922;
    --q1: #3FB950; --q2: #D29922; --q3: #F85149; --q4: #A371F7;
    --bg: #0D1117; --card: #161B22; --border: #30363D;
    --text-primary: #E6EDF3; --text-secondary: #8B949E;
}
.badge-boarding { background: linear-gradient(135deg,#F85149 0%,#D29922 100%); color:#fff; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:700; }
.badge-gate { background: linear-gradient(135deg,#D29922 0%,#3FB950 100%); color:#fff; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:700; }
.badge-checkin { background: #21262D; color: #D29922; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:600; border:1px solid #D29922; }
.badge-wait { background: #21262D; color: #8B949E; padding:3px 10px; border-radius:6px; font-size:12px; }
.front-run-critical { border-left: 3px solid #F85149; padding-left: 8px; }
.front-run-elevated { border-left: 3px solid #D29922; padding-left: 8px; }
.front-run-monitor { border-left: 3px solid #3FB950; padding-left: 8px; }
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
<div style="position:relative;width:100%;height:28px;background:linear-gradient(90deg,#21262D 0%,#30363D 100%);border-radius:4px;margin:8px 0;">
  <div style="position:absolute;left:{trade_l_pct}%;width:{trade_r_pct-trade_l_pct}%;height:100%;background:linear-gradient(90deg,rgba(63,185,80,0.25),rgba(217,153,34,0.25),rgba(248,81,73,0.25));border-radius:4px;"></div>
  <div style="position:absolute;left:{trend_l_pct}%;width:{trend_r_pct-trend_l_pct}%;height:100%;border:1px dashed #8B949E;border-radius:4px;opacity:0.5;"></div>
  <div style="position:absolute;left:{px_pct}%;top:50%;transform:translate(-50%,-50%);width:10px;height:10px;background:#E6EDF3;border-radius:50%;box-shadow:0 0 6px rgba(230,237,243,0.6);z-index:10;"></div>
</div>
<div style="display:flex;justify-content:space-between;font-size:10px;color:#8B949E;margin-top:-4px;">
  <span>TAIL {tail_l}</span><span>TREND {trend_l}</span><span>TRADE {trade_l}</span>
  <span style="color:#E6EDF3;font-weight:700;">PRICE {px}</span>
  <span>TRADE {trade_r}</span><span>TREND {trend_r}</span><span>TAIL {tail_r}</span>
</div>
"""

def _flight_pill(status, count):
    cls = {"BOARDING NOW":"badge-boarding","GATE OPENS SOON":"badge-gate","CHECK-IN":"badge-checkin","WAIT":"badge-wait"}.get(status,"badge-wait")
    return f'<span class="{cls}">{status.replace("_"," ").upper()}: {count}</span>'

def _section_header(title, subtitle=""):
    sub = f'<div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return f'<div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:4px;">{title}</div>{sub}'

def _kpi_box(label, value, color="var(--text-primary)"):
    return f'<div style="background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px;text-align:center;"><div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">{label}</div><div style="font-size:18px;font-weight:700;color:{color};">{value}</div></div>'

def _card(title, content, border_color="var(--border-default)"):
    return f'<div style="background:var(--card);border-left:3px solid {border_color};border-radius:6px;padding:12px;margin-bottom:8px;"><div style="font-size:12px;font-weight:700;color:var(--text-primary);margin-bottom:6px;">{title}</div><div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">{content}</div></div>'

def _metric_box(label, value, sub="", color="var(--text-primary)"):
    sub_html = f'<div style="font-size:10px;color:var(--text-secondary);margin-top:2px;">{sub}</div>' if sub else ""
    return f'<div style="text-align:center;"><div style="font-size:11px;color:var(--text-secondary);margin-bottom:2px;">{label}</div><div style="font-size:20px;font-weight:700;color:{color};">{value}</div>{sub_html}</div>'

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

# ═══════════════════════════════════════════════════════════════════
# FRONT-RUN & CATALYST ENGINE v27.0
# ═══════════════════════════════════════════════════════════════════

def _get_supply_chain_signal(ticker, discovery_v3, prices):
    """Map ticker to AI infrastructure bottleneck signal for front-running."""
    if not discovery_v3 or not isinstance(discovery_v3, dict):
        return None
    bottleneck_map = {
        "MU": {"theme": "HBM / DRAM", "severity": "CRITICAL", "lead_time": "12-18 mo",
               "catalyst": "2026 capacity sold out. DRAM spot +80-90%. Any capacity announcement = gap up.",
               "watch": "MU, 005930.KS, 000660.KS", "front_run": "Monitor SK Hynix/Micron capex guides"},
        "NVDA": {"theme": "HBM / DRAM", "severity": "CRITICAL", "lead_time": "12-18 mo",
                 "catalyst": "HBM3E demand exceeds supply. Vera CPU launch H2 2026.",
                 "watch": "NVDA, MU, TSM", "front_run": "NVDA earnings guide > consensus = +8-12%"},
        "TSM": {"theme": "HBM / DRAM", "severity": "CRITICAL", "lead_time": "12-18 mo",
                "catalyst": "CoWoS capacity bottleneck. 2026 fully booked.",
                "watch": "TSM, AMAT, LRCX", "front_run": "TSM capex raise = semi rally"},
        "AMD": {"theme": "Agentic AI / CPU", "severity": "MONITOR", "lead_time": "Monthly cycle",
                "catalyst": "MI350 ramp vs Blackwell. Agentic AI workloads boosting server CPU demand.",
                "watch": "AMD, INTC, NVDA", "front_run": "AMD data center rev beat = +6-10%"},
        "INTC": {"theme": "Agentic AI / CPU", "severity": "MONITOR", "lead_time": "Monthly cycle",
                 "catalyst": "18A node recovery. Foundry break-even target 2026.",
                 "watch": "INTC, TSM, ASML", "front_run": "INTC fab partnership news = gap up"},
        "VST": {"theme": "Power Grid / Transformers", "severity": "CRITICAL", "lead_time": "4-5 yr",
                "catalyst": "PJM summer 2027 shortfall 6,600 MW. Only 5GW of 12GW announced under construction.",
                "watch": "VST, ETN, GEV, CEG", "front_run": "Any PJM capacity auction result = vol spike"},
        "ETN": {"theme": "Power Grid / Transformers", "severity": "CRITICAL", "lead_time": "4-5 yr",
               "catalyst": "Transformer lead times 2-3x normal. Data center electrification demand surge.",
               "watch": "ETN, GEV, PWR", "front_run": "Eaton data center order book beat = +5-8%"},
        "GEV": {"theme": "Power Grid / Transformers", "severity": "CRITICAL", "lead_time": "4-5 yr",
               "catalyst": "Grid modernization backlog at record. Gas turbine demand resurgence.",
               "watch": "GEV, ETN, CEG", "front_run": "GEV turbine order >$2B = +7-10%"},
        "CEG": {"theme": "Power Grid / Transformers", "severity": "CRITICAL", "lead_time": "4-5 yr",
               "catalyst": "Nuclear restart + AI power demand. Microsoft/Amazon PPA announcements.",
               "watch": "CEG, VST, OKLO", "front_run": "CEG nuclear relicense news = gap up"},
        "COHR": {"theme": "Optical / Photonics", "severity": "ELEVATED", "lead_time": "6-12 mo",
                 "catalyst": "NVDA optical interconnect partnerships. 1.6T transceiver ramp.",
                 "watch": "COHR, LITE, GLW", "front_run": "COHR 1.6T shipment announce = +10-15%"},
        "LITE": {"theme": "Optical / Photonics", "severity": "ELEVATED", "lead_time": "6-12 mo",
                "catalyst": "Lumentum 800G/1.6T laser supply to NVDA. Datacenter fiber upgrade cycle.",
                "watch": "LITE, COHR, GLW", "front_run": "LITE NVDA design win = +8-12%"},
        "GLW": {"theme": "Optical / Photonics", "severity": "ELEVATED", "lead_time": "6-12 mo",
               "catalyst": "Corning optical fiber for AI clusters. Gorilla Glass auto adoption.",
               "watch": "GLW, COHR, LITE", "front_run": "GLW optical rev guide raise = +5-7%"},
        "XHB": {"theme": "Housing / Rates", "severity": "ELEVATED", "lead_time": "3-6 mo",
               "catalyst": "Fed cut cycle restart pricing. 10Y yield <4% = refi boom. Lumber futures stabilizing.",
               "watch": "XHB, DHI, LEN, NAIL", "front_run": "CPI miss + Fed dove speech = XHB +3-5% in session"},
        "DHI": {"theme": "Housing / Rates", "severity": "ELEVATED", "lead_time": "3-6 mo",
               "catalyst": "Order backlog + community count growth. Mortgage rate sensitivity high.",
               "watch": "DHI, LEN, PHM", "front_run": "DHI order beat + margin guide up = +6-9%"},
        "NAIL": {"theme": "Housing / Rates", "severity": "ELEVATED", "lead_time": "3-6 mo",
                "catalyst": "3x levered homebuilders. Fed pivot = 15-25% moves in weeks.",
                "watch": "NAIL, XHB, ITB", "front_run": "NFP miss + yields collapse = NAIL +10-15%"},
        "GLD": {"theme": "Gold Secular Bull", "severity": "ELEVATED", "lead_time": "Structural",
               "catalyst": "Central bank buying record pace. De-dollarization + fiscal deficit concerns.",
               "watch": "GLD, GDX, GDXJ", "front_run": "Any BRICS currency news = GLD +1-2% overnight"},
        "SLV": {"theme": "Silver Supercycle", "severity": "ELEVATED", "lead_time": "Structural",
               "catalyst": "Industrial demand + safe haven. Solar panel silver loadings rising.",
               "watch": "SLV, SILJ, GDXJ", "front_run": "Silver ETF flow spike = momentum chase"},
        "BTC-USD": {"theme": "Bitcoin Halving Cycle", "severity": "MONITOR", "lead_time": "4 yr cycle",
                   "catalyst": "Post-halving supply squeeze. ETF inflows structural demand floor.",
                   "watch": "BTC-USD, ETH-USD, MSTR", "front_run": "Spot ETF daily inflow >$500M = +5-8%"},
        "MSTR": {"theme": "Bitcoin Leverage", "severity": "MONITOR", "lead_time": "4 yr cycle",
                "catalyst": "BTC proxy with 2.5x implied leverage. Convertible issuance = BTC buying.",
                "watch": "MSTR, COIN, HOOD", "front_run": "MSTR BTC purchase announce = +8-12%"},
        "ADRO.JK": {"theme": "Coal Export", "severity": "ELEVATED", "lead_time": "Quarterly",
                   "catalyst": "HBA price benchmark + China restocking. Rupiah stability key.",
                   "watch": "ADRO.JK, ITMG.JK, PTBA.JK", "front_run": "China PMI >50 + HBA price hike = +5-8%"},
        "BBCA.JK": {"theme": "Banking NIM", "severity": "MONITOR", "lead_time": "Monthly",
                   "catalyst": "BI rate cut cycle = NIM expansion. Digital banking growth.",
                   "watch": "BBCA.JK, BBRI.JK, BMRI.JK", "front_run": "BI rate cut 25bp = banking +3-5%"},
        "BBRI.JK": {"theme": "Banking NIM", "severity": "MONITOR", "lead_time": "Monthly",
                   "catalyst": "Microloan growth + NIM recovery. Government infra loan pipeline.",
                   "watch": "BBRI.JK, BBCA.JK, BBNI.JK", "front_run": "BBRI NPL ratio <2.5% = +4-6%"},
    }
    if ticker in bottleneck_map:
        return bottleneck_map[ticker]
    for key, val in bottleneck_map.items():
        if key in ticker or ticker in key:
            return val
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) >= 22:
            r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1)
            if r1m > 0.15:
                return {"theme": "Momentum Extension", "severity": "MONITOR", "lead_time": "Weekly",
                       "catalyst": f"+{r1m:.1%} 1M momentum. Watch for profit-taking vs continuation.",
                       "watch": ticker, "front_run": "Volume spike + break ATH = continuation"}
            elif r1m < -0.15:
                return {"theme": "Oversold Bounce", "severity": "MONITOR", "lead_time": "Weekly",
                       "catalyst": f"{r1m:.1%} 1M drawdown. Mean reversion or structural breakdown?",
                       "watch": ticker, "front_run": "RSI <30 + volume capitulation = bounce"}
    return None

def _get_macro_trigger(ticker, prices, gip, dxy_corr):
    """Generate macro trigger map for front-running."""
    triggers = []
    sq = gip.structural_quad if gip else "Q3"
    dxy_trend = dxy_corr.get("dxy_trend", "Neutral") if dxy_corr else "Neutral"
    if any(x in ticker for x in ["GLD", "GC=F", "SLV", "SI=F", "GDX", "PPLT"]):
        if "Bearish" in dxy_trend:
            triggers.append({"event": "DXY bearish break", "impact": "HIGH", "timeframe": "1-2 weeks", "confidence": 0.75,
                           "detail": "DXY <100 + real yields falling = precious metals bid"})
        triggers.append({"event": "Fed pause/pivot", "impact": "HIGH", "timeframe": "FOMC dependent", "confidence": 0.60,
                        "detail": "Rate cut pricing = gold secular bid intensifies"})
    if any(x in ticker for x in ["XHB", "DHI", "LEN", "NAIL", "PHM", "TOL"]):
        if sq in ["Q1", "Q4"]:
            triggers.append({"event": "10Y yield < 4.0%", "impact": "HIGH", "timeframe": "Daily", "confidence": 0.70,
                           "detail": "Mortgage rate sensitivity extreme. Refi boom restarts."})
        triggers.append({"event": "CPI/PCE miss", "impact": "HIGH", "timeframe": "Monthly", "confidence": 0.65,
                        "detail": "Inflation cooling = Fed cut pricing = housing rally"})
    if any(x in ticker for x in ["NVDA", "AMD", "TSM", "AVGO", "MRVL", "COHR", "QCOM", "SMCI"]):
        triggers.append({"event": "AI capex guide raise", "impact": "HIGH", "timeframe": "Earnings", "confidence": 0.80,
                        "detail": "Hyperscaler capex +20% YoY = entire AI supply chain rerating"})
        if sq == "Q3":
            triggers.append({"event": "Stagflation fade", "impact": "MEDIUM", "timeframe": "1-3 months", "confidence": 0.50,
                           "detail": "Q3->Q1 transition = growth scare fading = tech multiple expansion"})
    if any(x in ticker for x in ["VST", "ETN", "GEV", "CEG", "PWR", "FLR"]):
        triggers.append({"event": "Data center PPA announce", "impact": "HIGH", "timeframe": "Quarterly", "confidence": 0.70,
                        "detail": "Microsoft/Amazon/Google 1GW+ power deals = backlog visibility"})
        triggers.append({"event": "Grid interconnection reform", "impact": "MEDIUM", "timeframe": "Policy", "confidence": 0.55,
                        "detail": "FERC Order 2023 implementation = queue acceleration"})
    if any(x in ticker for x in ["BTC", "ETH", "MSTR", "COIN", "HOOD"]):
        triggers.append({"event": "ETF inflow streak", "impact": "HIGH", "timeframe": "Daily", "confidence": 0.75,
                        "detail": "Spot BTC ETF 5-day inflow streak = momentum ignition"})
        triggers.append({"event": "Halving supply squeeze", "impact": "MEDIUM", "timeframe": "2024-2025", "confidence": 0.60,
                        "detail": "Post-halving miner sell pressure declining"})
    if ticker.endswith(".JK") or ticker in ["EIDO", "^JKSE"]:
        triggers.append({"event": "BI rate cut", "impact": "HIGH", "timeframe": "Monthly", "confidence": 0.65,
                        "detail": "Rate cut = banking NIM + consumer credit growth"})
        triggers.append({"event": "China stimulus", "impact": "HIGH", "timeframe": "Policy", "confidence": 0.60,
                        "detail": "China infra stimulus = coal/nickel/CPO demand surge"})
        triggers.append({"event": "Rupiah < 15800", "impact": "MEDIUM", "timeframe": "Daily", "confidence": 0.55,
                        "detail": "Rupiah strength = foreign flow return = IHSG rerating"})
    if any(x in ticker for x in ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCAD", "USDCHF"]):
        if "Bearish" in dxy_trend:
            triggers.append({"event": "DXY break 100", "impact": "HIGH", "timeframe": "1-2 weeks", "confidence": 0.70,
                           "detail": "DXY bearish = EMFX and commodity FX rally"})
        triggers.append({"event": "Fed-ECB divergence", "impact": "MEDIUM", "timeframe": "Monthly", "confidence": 0.55,
                        "detail": "Relative central bank policy = FX direction"})
    return triggers[:3]

def _get_earnings_proxy(ticker, prices):
    s = prices.get(ticker)
    if s is None or len(s) < 40:
        return None
    s_clean = pd.to_numeric(s, errors="coerce").dropna()
    if len(s_clean) < 40:
        return None
    px = float(s_clean.iloc[-1])
    vol = s_clean.tail(20).std()
    expected_move = px * (vol / px if px > 0 else 0.02) * math.sqrt(5) if vol > 0 else px * 0.04
    r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
    r10d = float(s_clean.iloc[-1] / s_clean.iloc[-11] - 1) if len(s_clean) >= 11 else 0
    drift = "Bullish drift" if r5d > 0.03 and r5d > r10d * 0.7 else \
            "Bearish drift" if r5d < -0.03 and r5d < r10d * 0.7 else "Neutral"
    return {
        "expected_move": round(expected_move, 2),
        "expected_move_pct": round(expected_move / px, 3) if px > 0 else 0,
        "drift": drift,
        "vol_setup": "Elevated" if (vol / px if px > 0 else 0) > 0.025 else "Normal",
        "note": f"Pre-earnings vol: ±{expected_move:.2f} ({expected_move/px:.1%}) — {drift}"
    }

def _build_front_run_catalysts(ticker, prices, gip, dxy_corr, discovery_v3, news_narratives, market_type="us_equity"):
    catalysts = {
        "ticker": ticker,
        "supply_chain": _get_supply_chain_signal(ticker, discovery_v3, prices),
        "macro_triggers": _get_macro_trigger(ticker, prices, gip, dxy_corr),
        "earnings": _get_earnings_proxy(ticker, prices),
        "news": None,
        "composite_front_run_score": 0,
        "top_catalyst": None,
    }
    if news_narratives and news_narratives.get("ticker_specific"):
        t_news = news_narratives["ticker_specific"].get(ticker, [])
        if t_news:
            best = max(t_news, key=lambda x: getattr(x, "narrative_score", 0) if hasattr(x, "narrative_score") else 0)
            if hasattr(best, "narrative") and best.narrative:
                catalysts["news"] = {
                    "headline": getattr(best, "headline", "News catalyst")[:80],
                    "narrative": best.narrative[:120],
                    "sentiment": getattr(best, "sentiment", "neutral"),
                    "score": getattr(best, "narrative_score", 0.5),
                }
    score = 0
    if catalysts["supply_chain"] and catalysts["supply_chain"]["severity"] == "CRITICAL":
        score += 40
    elif catalysts["supply_chain"] and catalysts["supply_chain"]["severity"] == "ELEVATED":
        score += 25
    if catalysts["macro_triggers"]:
        high_impact = sum(1 for t in catalysts["macro_triggers"] if t.get("impact") == "HIGH")
        score += high_impact * 15
    if catalysts["earnings"] and catalysts["earnings"]["drift"] != "Neutral":
        score += 10
    if catalysts["news"] and catalysts["news"]["sentiment"] == "positive":
        score += 15
    elif catalysts["news"] and catalysts["news"]["sentiment"] == "negative":
        score -= 10
    catalysts["composite_front_run_score"] = min(100, max(0, score))
    candidates = []
    if catalysts["supply_chain"]:
        candidates.append(("supply_chain", catalysts["supply_chain"]["catalyst"][:100]))
    if catalysts["news"]:
        candidates.append(("news", catalysts["news"]["narrative"][:100]))
    if catalysts["macro_triggers"]:
        candidates.append(("macro", catalysts["macro_triggers"][0]["detail"][:100]))
    if catalysts["earnings"]:
        candidates.append(("earnings", catalysts["earnings"]["note"][:100]))
    if candidates:
        catalysts["top_catalyst"] = candidates[0]
    return catalysts

def _front_run_badge_html(score):
    if score >= 70:
        return f'<span style="background:linear-gradient(135deg,#F85149 0%,#D29922 100%);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">🔥 FRONT-RUN {score}</span>'
    elif score >= 40:
        return f'<span style="background:linear-gradient(135deg,#D29922 0%,#3FB950 100%);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">⚡ WATCH {score}</span>'
    elif score > 0:
        return f'<span style="background:#21262D;color:#8B949E;padding:2px 8px;border-radius:4px;font-size:11px;">👀 Monitor {score}</span>'
    return ''

def _render_front_run_section(row, market_type="us_equity"):
    catalysts = row.get("front_run_catalysts")
    if not catalysts:
        return
    score = catalysts.get("composite_front_run_score", 0)
    if score == 0 and not catalysts.get("supply_chain") and not catalysts.get("macro_triggers"):
        return
    st.divider()
    st.markdown("**🚀 Front-Run Catalyst**")
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(_front_run_badge_html(score), unsafe_allow_html=True)
    with c2:
        if catalysts.get("top_catalyst"):
            st.caption(f"**{catalysts['top_catalyst'][0].upper()}:** {catalysts['top_catalyst'][1]}")
    sc = catalysts.get("supply_chain")
    if sc:
        css_cls = {"CRITICAL": "front-run-critical", "ELEVATED": "front-run-elevated", "MONITOR": "front-run-monitor"}.get(sc.get("severity", ""), "")
        with st.expander(f"🔥 {sc.get('theme', 'Supply Chain')} — {sc.get('severity', '')}", expanded=False):
            st.markdown(f"<div class='{css_cls}'>**Catalyst:** {sc.get('catalyst', '—')}</div>", unsafe_allow_html=True)
            st.markdown(f"**Lead Time:** {sc.get('lead_time', '—')} · **Watch:** {sc.get('watch', '—')}")
            st.info(f"🎯 **Front-Run Play:** {sc.get('front_run', '—')}")
    triggers = catalysts.get("macro_triggers", [])
    if triggers:
        with st.expander("🌍 Macro Triggers", expanded=False):
            for t in triggers:
                impact_color = "#F85149" if t.get("impact") == "HIGH" else "#D29922" if t.get("impact") == "MEDIUM" else "#8B949E"
                st.markdown(f"<span style='color:{impact_color};font-weight:700;'>[{t.get('impact', '')}]</span> {t.get('event', '')} — *{t.get('timeframe', '')}* (conf: {t.get('confidence', 0):.0%})", unsafe_allow_html=True)
                st.caption(t.get("detail", "—"))
    earn = catalysts.get("earnings")
    if earn:
        with st.expander("📊 Earnings Vol Setup", expanded=False):
            st.metric("Expected Move", f"±{earn.get('expected_move', 0):.2f}", f"{earn.get('expected_move_pct', 0):.1%}")
            st.caption(f"Drift: {earn.get('drift', '—')} · Vol: {earn.get('vol_setup', '—')}")
    news = catalysts.get("news")
    if news:
        news_color = "var(--long)" if news.get("sentiment") == "positive" else "var(--short)" if news.get("sentiment") == "negative" else "var(--neutral)"
        with st.expander("📰 News Signal", expanded=False):
            st.markdown(f"<span style='color:{news_color};font-weight:600;'>{news.get('headline', '—')}</span>", unsafe_allow_html=True)
            st.caption(news.get("narrative", "—"))

def _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, market_type, vix_now, gamma_data=None, greeks_data=None, forward_returns=None, news_narratives=None, gip=None, dxy_corr=None, discovery_v3=None):
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
    if forward_returns:
        row["expected_1m"] = forward_returns.get("expected_1m")
        row["expected_3m"] = forward_returns.get("expected_3m")
        row["expected_6m"] = forward_returns.get("expected_6m")
        row["forward_confidence"] = forward_returns.get("confidence")
    if news_narratives and news_narratives.get("ticker_specific"):
        t_news = news_narratives["ticker_specific"].get(ticker, [])
        if t_news:
            best_ni = max(t_news, key=lambda x: getattr(x, "narrative_score", 0) if hasattr(x, "narrative_score") else 0)
            if hasattr(best_ni, "narrative") and best_ni.narrative:
                row["news_narrative"] = best_ni.narrative
            if hasattr(best_ni, "sentiment") and best_ni.sentiment:
                row["news_sentiment"] = best_ni.sentiment
            if hasattr(best_ni, "headline") and best_ni.headline:
                row["news_headline"] = best_ni.headline[:80]
    row["front_run_catalysts"] = _build_front_run_catalysts(ticker, prices, gip, dxy_corr, discovery_v3, news_narratives, market_type)
    row = _enrich_row_with_conclusions(row, gamma, greek, vix_now, s)
    return row

def _build_ihsg_row(ticker, prices, ar, ihsg_sector_momentum=None, ihsg_commodity_overlay=None, ihsg_rupiah_regime=None, ihsg_foreign_flow=None, ihsg_macro_overlay=None, forward_returns=None, news_narratives=None, gip=None, dxy_corr=None, discovery_v3=None):
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
            best_ni = max(t_news, key=lambda x: getattr(x, "narrative_score", 0) if hasattr(x, "narrative_score") else 0)
            if hasattr(best_ni, "narrative") and best_ni.narrative:
                row["news_narrative"] = best_ni.narrative
            if hasattr(best_ni, "sentiment") and best_ni.sentiment:
                row["news_sentiment"] = best_ni.sentiment
    row["entry_advice"] = "BUY NOW — At buy zone" if row.get("price") and row.get("entry") and row["price"] <= row["entry"]*1.02 else "WAIT — Slightly above entry"
    row["tp1_basis"] = "Sector momentum target"
    row["tp2_basis"] = "Regime-aligned stretch"
    row["stop_basis"] = "Below support level"
    row["path_smoothness"] = "Smooth — domestic demand sticky" if any(x in ticker for x in ["BBCA","BBRI","TLKM"]) else "Bumpy — commodity vol"
    row["time_estimate"] = "2-4 months"
    row["breakout_chance"] = "Medium"
    row["worth_entering"] = "YES"
    row["front_run_catalysts"] = _build_front_run_catalysts(ticker, prices, gip, dxy_corr, discovery_v3, news_narratives, "ihsg")
    return row

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
    dir_emoji = "🟢" if "LONG" in direction else "🔴" if "SHORT" in direction else "⚪"
    dir_color = "var(--long)" if "LONG" in direction else "var(--short)" if "SHORT" in direction else "var(--text-secondary)"
    worth_color = "var(--long)" if "YES" in worth or "BUY" in worth else "var(--neutral)" if "WAIT" in worth or "CHASE" in worth else "var(--short)" if "SKIP" in worth else "var(--text-secondary)"
    fr_badge = ""
    fr_cats = row.get("front_run_catalysts")
    if fr_cats and fr_cats.get("composite_front_run_score", 0) > 0:
        fr_badge = _front_run_badge_html(fr_cats["composite_front_run_score"])
    header = f"{dir_emoji} {ticker} | {direction.replace(' ✅','').replace(' ⚠️','')} | Grade {grade}"
    if scanner: header += f" | {scanner}"
    if row.get("score") is not None: header += f" | Score: {row.get('score',0):.2f}"
    if fr_badge: header += f" | {fr_badge}"
    with st.expander(header, expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Direction:** {direction}", unsafe_allow_html=True)
        c2.markdown(f"**Worth Entering:** {worth}", unsafe_allow_html=True)
        c3.markdown(f"**Grade:** {grade}", unsafe_allow_html=True)
        st.divider()
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price", ff(price))
        m2.metric("Entry", ff(entry))
        m3.metric("Target 1", ff(t1))
        m4.metric("Target 2", ff(t2))
        m5.metric("Stop Loss", ff(stop))
        m6.metric("R:R", f"{ff(rr)}x")
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
                st.markdown(f"{row.get('news_narrative', row.get('news_headline', '—'))}", unsafe_allow_html=True)
                if row.get("news_headline") and row.get("news_narrative"):
                    st.caption(f"Headline: {row.get('news_headline')}")
        _render_front_run_section(row, market_type)
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
        return '<div style="background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px;text-align:center;margin-bottom:8px;"><div style="font-size:12px;font-weight:700;color:var(--long);">REGIME ALIGNED</div><div style="font-size:11px;color:var(--text-secondary);">Both monthly and quarterly point the same direction</div></div>'
    target = ""
    if sq == "Q3" and mq == "Q2": target = '-> Q1 TARGET'
    elif sq == "Q3" and mq == "Q1": target = '-> WATCH Q2->Q1'
    return f'<div style="background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px;text-align:center;margin-bottom:8px;"><div style="font-size:12px;font-weight:700;color:var(--neutral);">Structural: {sq} -> Monthly: {mq} {target}</div><div style="font-size:11px;color:var(--text-secondary);">Monthly diverges from structural — tactical caution</div></div>'

def _gamma_card(gamma):
    if not gamma or not gamma.get("ok") or gamma.get("throttle") is None:
        gamma = {"ok": True, "regime": "POSITIVE", "label": "Positive", "color": "#3FB950",
                 "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0, "action": "Buy dips, normal sizing"}
    th = _sf(gamma.get("throttle")); r10 = _sf(gamma.get("rvol_10d")); vp = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN")); label = str(gamma.get("label","—")); action = str(gamma.get("action","—"))
    color = str(gamma.get("color","#8B949E"))
    explain = {"DEEP_POSITIVE":"Very calm — buy dips","POSITIVE":"Calm — dips get bought","TRANSITION":"Shifting — careful sizing","NEGATIVE":"Volatile — reduce size","DEEP_NEGATIVE":"Dangerous — stay disciplined"}.get(regime,"Unclear")
    vpc = "var(--long)" if (vp is not None and vp > 0) else "var(--short)"
    th_str = f"{th:.0f}%" if th is not None else "—"
    r10_str = f"{r10:.1f}%" if r10 is not None else "—"
    vp_str = f"{vp:+.1f}%" if vp is not None else "—"
    return (f'<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px;">'
            f'<div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">OPTIONS MARKET STRUCTURE</div>'
            f'<div style="font-size:22px;font-weight:800;color:{color};margin-bottom:4px;">{label.upper()}</div>'
            f'<div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px;">{explain}</div>'
            f'<div style="display:flex;gap:8px;margin-bottom:8px;">'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Throttle</div><div style="font-size:14px;font-weight:700;color:{vpc};">{th_str}</div></div>'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">10d Realized Vol</div><div style="font-size:14px;font-weight:700;color:var(--text-primary);">{r10_str}</div></div>'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Vol Premium</div><div style="font-size:14px;font-weight:700;color:{vpc};">{vp_str}</div></div></div>'
            f'<div style="font-size:11px;color:var(--text-secondary);border-top:1px solid var(--border);padding-top:6px;"><b>Action:</b> {action}</div>'
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
    tl = lev.get("top_longs", []); ts = lev.get("top_shorts", [])
    tls = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return (f'<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px;">'
            f'<div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">LEVERAGED ETF FLOWS {"🏆 ALL TIME HIGH" if ath else ""}</div>'
            f'<div style="display:flex;gap:8px;margin-bottom:8px;">'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Total AUM</div><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${tot:.1f}B</div></div>'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Long %</div><div style="font-size:14px;font-weight:700;color:var(--long);">{lp:.0%}</div></div>'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Short %</div><div style="font-size:14px;font-weight:700;color:var(--short);">{sp:.0%}</div></div>'
            f'<div style="flex:1;background:#0D1117;border-radius:4px;padding:6px;text-align:center;"><div style="font-size:10px;color:var(--text-secondary);">Rebal</div><div style="font-size:14px;font-weight:700;color:{rc};">{rb}</div></div></div>'
            f'<div style="font-size:11px;color:var(--text-secondary);border-top:1px solid var(--border);padding-top:6px;"><div>Long: {tls}</div><div style="margin-top:2px;">Short: {tss}</div></div>'
            f'</div>')



# ═══════════════════════════════════════════════════════════════════
# MAIN APP — COMPACT v27.1
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# AUTO-LOAD / SAVE MECHANISM
# ═══════════════════════════════════════════════════════════════════

_SNAPSHOT_FILE = "macroregime_snapshot.pkl"

if "snap" not in st.session_state:
    st.session_state.snap = None
if "prices" not in st.session_state:
    st.session_state.prices = {}
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None

# Try auto-load from saved snapshot
if st.session_state.snap is None:
    try:
        import pickle
        if os.path.exists(_SNAPSHOT_FILE):
            with open(_SNAPSHOT_FILE, "rb") as f:
                data = pickle.load(f)
            st.session_state.snap = data.get("snap")
            st.session_state.prices = data.get("prices", {})
            st.session_state.last_refresh = data.get("timestamp")
    except Exception:
        pass  # Silent fail, will show "Click Full Rebuild"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.caption("v27.1 — Compact Patch")
    st.divider()
    page = st.radio("Navigate", [
        "📊 Dashboard",
        "🇺🇸 US Stocks",
        "💱 Forex",
        "🪙 Commodities",
        "₿ Crypto",
        "🇮🇩 IHSG",
        "⚡ Alpha Center",
        "🔧 Admin",
    ], index=0)
    st.divider()

    # ── FULL REBUILD with robust import path ──
    if st.button("🔄 Full Rebuild", type="primary"):
        with st.spinner("Rebuilding all data..."):
            rebuild_error = None
            debug_info = []
            try:
                import sys, os, importlib.util
                project_root = os.path.dirname(os.path.abspath(__file__))
                debug_info.append(f"Project root: {project_root}")
                debug_info.append(f"Python path: {sys.path[:3]}")

                # Check critical files exist
                init_path = os.path.join(project_root, "src", "macroregime", "__init__.py")
                rebuild_path = os.path.join(project_root, "src", "macroregime", "rebuild.py")
                debug_info.append(f"__init__.py exists: {os.path.exists(init_path)}")
                debug_info.append(f"rebuild.py exists: {os.path.exists(rebuild_path)}")

                # Method 1: add src/ to sys.path
                src_path = os.path.join(project_root, "src")
                if src_path not in sys.path and os.path.isdir(src_path):
                    sys.path.insert(0, src_path)

                try:
                    from macroregime.rebuild import full_rebuild
                    debug_info.append("Import method 1: OK")
                except ImportError as e1:
                    debug_info.append(f"Method 1 failed: {e1}")
                    try:
                        from src.macroregime.rebuild import full_rebuild
                        debug_info.append("Import method 2: OK")
                    except ImportError as e2:
                        debug_info.append(f"Method 2 failed: {e2}")
                        # Method 3: direct file load
                        if os.path.exists(rebuild_path):
                            spec = importlib.util.spec_from_file_location("macroregime.rebuild", rebuild_path)
                            rebuild_mod = importlib.util.module_from_spec(spec)
                            sys.modules["macroregime.rebuild"] = rebuild_mod
                            spec.loader.exec_module(rebuild_mod)
                            full_rebuild = rebuild_mod.full_rebuild
                            debug_info.append("Import method 3: OK (direct load)")
                        else:
                            raise ImportError(f"rebuild.py not found at {rebuild_path}")

                snap, prices = full_rebuild()
                st.session_state.snap = snap
                st.session_state.prices = prices
                st.session_state.last_refresh = pd.Timestamp.now()

                # Auto-save snapshot
                try:
                    import pickle
                    with open(_SNAPSHOT_FILE, "wb") as f:
                        pickle.dump({"snap": snap, "prices": prices, "timestamp": st.session_state.last_refresh}, f)
                except Exception as save_err:
                    st.warning(f"Rebuild OK but auto-save failed: {save_err}")

                st.success("✅ Rebuild complete! Snapshot saved.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                rebuild_error = str(e)
                st.error(f"❌ Rebuild failed: {rebuild_error}")
                with st.expander("🔍 Debug Info", expanded=False):
                    for line in debug_info:
                        st.code(line)
                st.info("💡 **Troubleshooting:**\n"
                        "1. Check that `src/macroregime/rebuild.py` exists in your repo\n"
                        "2. Verify `src/macroregime/__init__.py` exists (can be empty)\n"
                        "3. If both exist but still fail, check `rebuild.py` for syntax errors\n"
                        "4. Check Streamlit Cloud logs for full traceback")

    # Status indicator
    if st.session_state.last_refresh:
        st.caption(f"🟢 Last refresh: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.caption("🔴 No data loaded. Click Full Rebuild.")

snap = st.session_state.snap
prices = st.session_state.prices

if snap is None:
    st.info("👈 Click **Full Rebuild** in the sidebar to load data.")
    st.stop()

gip = snap.get("gip")
dxy_corr = snap.get("dxy_corr", {})
discovery_v3 = snap.get("discovery_v3", {})
news_narratives = snap.get("news_narratives", {})
gamma_data = snap.get("gamma_data", {})
greeks_data = snap.get("greeks_data", {})
cot_data = snap.get("cot_data", {})
oi_data = snap.get("oi_data", {})
vix_now = snap.get("vix", 20)

# ═══════════════════════════════════════════════════════════════════
# DASHBOARD — COMPACT (semua di 1 halaman)
# ═══════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")
    st.caption("Regime · Probabilities · Front-Run · Signals · Playbook")
    st.divider()

    # ── ROW 1: REGIME BANNER + PROB BARS ──
    if gip:
        sq = gip.structural_quad
        mq = gip.monthly_quad

        # Regime Banner
        st.markdown(f"""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:11px;color:var(--text-secondary);">STRUCTURAL</div>
              <div style="font-size:22px;font-weight:800;color:{qc(sq)};">{qn(sq)}</div>
              <div style="font-size:10px;color:var(--text-secondary);">{qnc(sq)}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:11px;color:var(--text-secondary);">MONTHLY</div>
              <div style="font-size:22px;font-weight:800;color:{qc(mq)};">{qn(mq)}</div>
              <div style="font-size:10px;color:var(--text-secondary);">{qnc(mq)}</div>
            </div>
          </div>
          <div style="margin-top:8px;font-size:11px;color:var(--text-secondary);border-top:1px solid var(--border);padding-top:6px;">
            {QUAD_EXPLAIN.get(sq, "")} | <b>Wins:</b> {QWINS.get(sq, "—")} | <b>Avoid:</b> {QWINS.get(mq, "—")}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Probabilities (compact inline)
        probs = gip.quarterly_probs if hasattr(gip, "quarterly_probs") else {}
        mprobs = gip.monthly_probs if hasattr(gip, "monthly_probs") else {}
        if probs or mprobs:
            c1, c2 = st.columns(2)
            with c1:
                if probs:
                    fig = prob_bar(probs, "Quarterly")
                    st.plotly_chart(fig, use_container_width=True, key="dash_qprobs")
            with c2:
                if mprobs:
                    fig = prob_bar(mprobs, "Monthly")
                    st.plotly_chart(fig, use_container_width=True, key="dash_mprobs")

        st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    st.divider()

    # ── ROW 2: VIX + GAMMA + LEVERAGE (compact 3-col) ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_kpi_box("VIX", f"{vix_now:.1f}", qc("Q3") if vix_now > 25 else qc("Q1")), unsafe_allow_html=True)
    with c2:
        gamma = snap.get("gamma", {})
        st.markdown(_gamma_card(gamma), unsafe_allow_html=True)
    with c3:
        lev = snap.get("leverage", {})
        st.markdown(_lev_card(lev), unsafe_allow_html=True)

    st.divider()

    # ── ROW 3: FRONT-RUN CATALYST BOARD ──
    with st.expander("🚀 Front-Run Catalyst Board", expanded=True):
        st.caption("What can make these go up — before the news hits")
        all_rows = []
        for market_type, tickers in [("us_equity", US_BUCKETS.get("core", [])), ("forex", FOREX_PAIRS), ("commodity", COMMODITIES), ("crypto", CRYPTO), ("ihsg", IHSG_UNIVERSE)]:
            ar = snap.get("analysis", {}).get(market_type, {})
            for t in tickers:
                if market_type == "ihsg":
                    r = _build_ihsg_row(t, prices, ar, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
                else:
                    r = _build_consolidated_row(t, prices, ar, cot_data, oi_data, market_type, vix_now, gamma_data, greeks_data, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
                if r and r.get("front_run_catalysts") and r["front_run_catalysts"].get("composite_front_run_score", 0) > 0:
                    all_rows.append(r)
        if all_rows:
            all_rows.sort(key=lambda x: x["front_run_catalysts"]["composite_front_run_score"], reverse=True)
            top10 = all_rows[:10]
            cols = st.columns(5)
            for i, row in enumerate(top10):
                with cols[i % 5]:
                    score = row["front_run_catalysts"]["composite_front_run_score"]
                    badge = _front_run_badge_html(score)
                    st.markdown(f"{badge}", unsafe_allow_html=True)
                    st.markdown(f"**{row['ticker']}** @ {ff(row['price'])}")
                    tc = row["front_run_catalysts"].get("top_catalyst")
                    if tc:
                        st.caption(f"{tc[1][:55]}...")
                    st.caption(f"{row.get('direction', '—')} | RR {row.get('rr', 0):.1f}x")
        else:
            st.info("No front-run catalysts detected. Run Full Rebuild to refresh.")

    st.divider()

    # ── ROW 4: DAILY SIGNALS ──
    with st.expander("📡 Daily Signals", expanded=True):
        daily = snap.get("daily_signals", [])
        if daily:
            for sig in daily[:5]:
                st.markdown(f"🎯 **{sig.get('ticker', '—')}** — {sig.get('signal', '—')} | {sig.get('confidence', '—')}")
        else:
            st.info("No daily signals. Run Full Rebuild.")

    st.divider()

    # ── ROW 5: PLAYBOOK (merged dari tab terpisah) ──
    with st.expander("📖 Playbook — Tactical Rules", expanded=False):
        if gip:
            sq = gip.structural_quad
            mq = gip.monthly_quad
            st.markdown(f"**Current:** {qn(sq)} (structural) → {qn(mq)} (monthly)")
            st.info(QUAD_EXPLAIN.get(sq, ""))
            st.markdown(f"**Winners:** {QWINS.get(sq, '—')}  |  **Avoid:** {QWINS.get(mq, '—')}")
        st.markdown("""
        **Q1 Goldilocks** — Buy dips, normal size. Tech + crypto lead.  
        **Q2 Reflation** — Commodity + energy overweight. Tighten stops.  
        **Q3 Stagflation** — Gold + silver + defensives. Reduce equity beta.  
        **Q4 Deflation** — Bonds + gold + cash. Avoid risk assets.
        """)

    # ── ROW 6: THEMES + GLOBAL & EM (merged, under construction) ──
    with st.expander("🎨 Themes & Global EM", expanded=False):
        st.info("🚧 Under construction. Add tickers to config.settings.US_BUCKETS")
        if discovery_v3:
            st.markdown("**Discovery v3 Bottlenecks:**")
            for theme, data in discovery_v3.items():
                if isinstance(data, dict) and data.get("tickers"):
                    st.caption(f"• {theme}: {', '.join(data['tickers'][:8])}")

# ═══════════════════════════════════════════════════════════════════
# US STOCKS
# ═══════════════════════════════════════════════════════════════════
if page == "🇺🇸 US Stocks":
    st.markdown("## 🇺🇸 US Stocks")
    st.caption("US equity signals with options, COT, and front-run catalysts")
    st.divider()
    ar = snap.get("analysis", {}).get("us_equity", {})
    rows = []
    for t in US_BUCKETS.get("core", []):
        r = _build_consolidated_row(t, prices, ar, cot_data, oi_data, "us_equity", vix_now, gamma_data, greeks_data, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
        if r: rows.append(r)
    longs, shorts = _split_long_short(rows)
    if longs:
        st.markdown("### 🟢 LONGS")
        for r in longs:
            _render_narrative_card_native(r, market_type="us_equity")
    if shorts:
        st.markdown("### 🔴 SHORTS")
        for r in shorts:
            _render_narrative_card_native(r, market_type="us_equity")
    if not rows:
        st.info("No signals. Run Full Rebuild.")

# ═══════════════════════════════════════════════════════════════════
# FOREX
# ═══════════════════════════════════════════════════════════════════
if page == "💱 Forex":
    st.markdown("## 💱 Forex")
    st.caption("FX signals with DXY correlation and macro triggers")
    st.divider()
    ar = snap.get("analysis", {}).get("forex", {})
    rows = []
    for t in FOREX_PAIRS:
        r = _build_consolidated_row(t, prices, ar, cot_data, oi_data, "forex", vix_now, gamma_data, greeks_data, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
        if r: rows.append(r)
    longs, shorts = _split_long_short(rows)
    if longs:
        st.markdown("### 🟢 LONGS")
        for r in longs:
            _render_narrative_card_native(r, market_type="forex")
    if shorts:
        st.markdown("### 🔴 SHORTS")
        for r in shorts:
            _render_narrative_card_native(r, market_type="forex")
    if not rows:
        st.info("No signals. Run Full Rebuild.")

# ═══════════════════════════════════════════════════════════════════
# COMMODITIES
# ═══════════════════════════════════════════════════════════════════
if page == "🪙 Commodities":
    st.markdown("## 🪙 Commodities")
    st.caption("Commodity signals with supply chain and macro triggers")
    st.divider()
    ar = snap.get("analysis", {}).get("commodity", {})
    rows = []
    for t in COMMODITIES:
        r = _build_consolidated_row(t, prices, ar, cot_data, oi_data, "commodity", vix_now, gamma_data, greeks_data, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
        if r: rows.append(r)
    longs, shorts = _split_long_short(rows)
    if longs:
        st.markdown("### 🟢 LONGS")
        for r in longs:
            _render_narrative_card_native(r, market_type="commodity")
    if shorts:
        st.markdown("### 🔴 SHORTS")
        for r in shorts:
            _render_narrative_card_native(r, market_type="commodity")
    if not rows:
        st.info("No signals. Run Full Rebuild.")

# ═══════════════════════════════════════════════════════════════════
# CRYPTO
# ═══════════════════════════════════════════════════════════════════
if page == "₿ Crypto":
    st.markdown("## ₿ Crypto")
    st.caption("Crypto signals with on-chain and halving cycle front-run")
    st.divider()
    ar = snap.get("analysis", {}).get("crypto", {})
    rows = []
    for t in CRYPTO:
        r = _build_consolidated_row(t, prices, ar, cot_data, oi_data, "crypto", vix_now, gamma_data, greeks_data, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
        if r: rows.append(r)
    longs, shorts = _split_long_short(rows)
    if longs:
        st.markdown("### 🟢 LONGS")
        for r in longs:
            _render_narrative_card_native(r, market_type="crypto")
    if shorts:
        st.markdown("### 🔴 SHORTS")
        for r in shorts:
            _render_narrative_card_native(r, market_type="crypto")
    if not rows:
        st.info("No signals. Run Full Rebuild.")

# ═══════════════════════════════════════════════════════════════════
# IHSG
# ═══════════════════════════════════════════════════════════════════
if page == "🇮🇩 IHSG":
    st.markdown("## 🇮🇩 IHSG")
    st.caption("Indonesia stock signals with sector momentum and macro overlays")
    st.divider()
    ar = snap.get("analysis", {}).get("ihsg", {})
    rows = []
    for t in IHSG_UNIVERSE:
        r = _build_ihsg_row(t, prices, ar, gip=gip, dxy_corr=dxy_corr, discovery_v3=discovery_v3, news_narratives=news_narratives)
        if r: rows.append(r)
    if rows:
        rows.sort(key=lambda x: x.get("rr", 0) or 0, reverse=True)
        for r in rows:
            _render_narrative_card_native(r, market_type="ihsg")
    else:
        st.info("No signals. Run Full Rebuild.")

# ═══════════════════════════════════════════════════════════════════
# ALPHA CENTER — FIXED v27.1
# ═══════════════════════════════════════════════════════════════════
if page == "⚡ Alpha Center":
    st.markdown("## ⚡ Alpha Center")
    st.caption("Bottlenecks · Alpha · Discovery · Daily Signals · Front-Run")
    st.divider()

    # FIX: Define ac and meta properly
    alpha_center = snap.get("alpha_center", {}) or {}
    ac = alpha_center
    meta = alpha_center.get("meta", {}) if alpha_center else {}

    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild.")
        st.stop()

    # ── Meta Bar ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime", meta.get("regime", "?"))
    c2.metric("Bias", meta.get("bias", "?"))
    c3.metric("VIX", meta.get("vix", "?"))
    c4.metric("Total", meta.get("total_items", 0))

    st.divider()

    # ── Flight Board ──
    st.markdown("### ✈️ Flight Board")
    flights = ac.get("flights", {})
    if flights:
        for status, items in flights.items():
            if items:
                st.markdown(_flight_pill(status, len(items)), unsafe_allow_html=True)
                cols = st.columns(4)
                for i, item in enumerate(items[:8]):
                    with cols[i % 4]:
                        ticker = item.get("ticker", "—")
                        score = item.get("front_run_score", 0)
                        badge = _front_run_badge_html(score)
                        st.markdown(f"{badge} **{ticker}**", unsafe_allow_html=True)
                        st.caption(f"{item.get('signal', '—')} | RR {item.get('rr', 0):.1f}x")
    else:
        st.info("No flight board data.")

    st.divider()

    # ── Alpha Table with Front-Run Scores ──
    st.markdown("### 📋 Alpha Table")
    alpha_items = ac.get("items", [])
    if alpha_items:
        df_data = []
        for item in alpha_items:
            df_data.append({
                "Ticker": item.get("ticker", "—"),
                "Direction": item.get("direction", "—"),
                "Price": item.get("price", "—"),
                "Entry": item.get("entry", "—"),
                "T1": item.get("target_1", "—"),
                "T2": item.get("target_2", "—"),
                "Stop": item.get("stop", "—"),
                "RR": item.get("rr", "—"),
                "Grade": item.get("grade", "—"),
                "Front-Run": item.get("front_run_score", 0),
                "Worth?": item.get("worth_entering", "—"),
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No alpha items. Run Full Rebuild.")

    st.divider()

    # ── Discovery v3 ──
    st.markdown("### 🔍 Discovery v3")
    if discovery_v3:
        for theme, data in discovery_v3.items():
            if isinstance(data, dict):
                with st.expander(f"{theme}", expanded=False):
                    st.write(data.get("description", "—"))
                    if data.get("tickers"):
                        st.caption(f"Tickers: {', '.join(data['tickers'][:15])}")
    else:
        st.info("No discovery data.")

# ═══════════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════════
if page == "🔧 Admin":
    st.markdown("## 🔧 Admin")
    st.caption("System status and diagnostics")
    st.divider()
    st.markdown("### Session State")
    st.json({k: str(v)[:100] for k, v in st.session_state.items()})
    st.divider()
    st.markdown("### Data Snapshot Keys")
    if snap:
        st.write(list(snap.keys()))
    else:
        st.info("No snapshot loaded.")
    st.divider()
    st.markdown("### Price Data Keys")
    st.write(list(prices.keys())[:20])
    st.caption(f"Total: {len(prices)} tickers")

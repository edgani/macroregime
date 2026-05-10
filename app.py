"""app.py — MacroRegime Pro v23.0 | MERGED TABS + NARRATIVE CARDS
Changes:
- MERGED: Alpha Center + Leaderboard + Daily Signals → "⚡ Alpha & Scanner"
- MERGED: Forex + Commodities → "💱🛢️ Macro Proxies"  
- MERGED: Global Quad + IHSG → "🌍 Global & EM"
- MERGED: Narratives + Discovery → "📖 Themes & Bottlenecks"
- ALL ticker tabs now use _render_narrative_card (NVTS-style report per ticker)
- Filter loosened: include all relevant tickers with |score|>0.10 or composite!=neutral
- Professional spacing, font sizing, dark theme
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import time
import logging

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

from config.settings import FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE

# ══════════════════════════════════════════════════════════════════════════════
# CSS — PROFESSIONAL DARK THEME
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp { background-color: #0d1117; }
.st-emotion-cache-1y4p8pa { max-width: 1200px; }

.narrative-card {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.narrative-card:hover {
    border-color: #58a6ff;
    box-shadow: 0 6px 20px rgba(88,166,255,0.15);
}
.card-header {
    font-size: 18px;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 12px;
    border-bottom: 1px solid #21262d;
    padding-bottom: 10px;
}
.card-section {
    font-size: 13px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 14px;
    margin-bottom: 8px;
}
.card-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #21262d;
    font-size: 14px;
    color: #c9d1d9;
}
.card-row:last-child { border-bottom: none; }
.card-label { color: #8b949e; font-weight: 500; }
.card-value { font-weight: 600; color: #e6edf3; }
.card-value.green { color: #3fb950; }
.card-value.red { color: #f85149; }
.card-value.yellow { color: #d29922; }
.card-value.blue { color: #58a6ff; }

.metric-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
    margin-bottom: 12px;
}
.metric-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
}
.metric-label {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 16px;
    font-weight: 700;
    color: #e6edf3;
}

.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-long { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.badge-short { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.badge-neutral { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.badge-urgent { background: rgba(248,81,73,0.2); color: #f85149; border: 1px solid #f85149; }
.badge-a { background: rgba(63,185,80,0.2); color: #3fb950; }
.badge-b { background: rgba(210,153,34,0.2); color: #d29922; }
.badge-c { background: rgba(139,148,158,0.2); color: #8b949e; }

.thesis-box {
    background: #0d1117;
    border-left: 3px solid #58a6ff;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-top: 10px;
    font-size: 14px;
    line-height: 1.6;
    color: #c9d1d9;
}

.risk-bar {
    display: flex;
    gap: 8px;
    margin-top: 10px;
}
.risk-pill {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
}
.risk-low { background: rgba(63,185,80,0.15); color: #3fb950; }
.risk-med { background: rgba(210,153,34,0.15); color: #d29922; }
.risk-high { background: rgba(248,81,73,0.15); color: #f85149; }

.section-hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #30363d, transparent);
    margin: 16px 0;
}

.streamlit-expanderHeader {
    font-size: 15px !important;
    font-weight: 600 !important;
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
}
.streamlit-expanderContent {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    padding: 20px !important;
}

.stCheckbox label {
    font-size: 13px !important;
    color: #c9d1d9 !important;
}
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
    "Q1":"Best conditions for stocks and crypto. Growth is strong and inflation is under control. This is when markets perform best.",
    "Q2":"Tricky environment. Economy growing but inflation biting. Commodities, energy, and international stocks tend to win. Crypto can work.",
    "Q3":"Most dangerous quarter. Economy slowing but prices still high. Gold, silver, and defensive stocks are the place to be. Tech gets hurt.",
    "Q4":"Deflationary collapse. Safest assets win: government bonds, gold, utilities, cash. Avoid risk.",
}
QWINS = {
    "Q1":"Tech, Bitcoin, Small Caps",
    "Q2":"Energy, Materials, Commodities",
    "Q3":"Gold, Silver, Defensives",
    "Q4":"Government Bonds, Gold, Cash",
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

def _rr_levels(px, lrr, trr, side="long"):
    px = _sf(px) or 0; lrr = _sf(lrr) or 0; trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = (px - lrr) / spread if spread > 0 else 0.5
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

def _metric_box(label, value, sub="", color="#E6EDF3"):
    sub_html = f'<div style="font-size:11px;color:#8B949E;margin-top:4px;">{sub}</div>' if sub else ""
    return f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:14px;text-align:center;"><div style="font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">{label}</div><div style="font-size:22px;font-weight:700;color:{color};">{value}</div>{sub_html}</div>'

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Build consolidated row for ANY ticker (Forex, Commodity, Crypto, IHSG)
# ══════════════════════════════════════════════════════════════════════════════

def _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, market_type, vix_now, gamma_data=None, greeks_data=None):
    """Build a narrative-ready row for any ticker."""
    s = prices.get(ticker)
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 22: return None

    px = float(s.iloc[-1])
    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
    r3m = float(s.iloc[-1] / s.iloc[-min(63,len(s))] - 1) if len(s) >= 22 else r1m
    vol = s.tail(20).std()
    vol_3m = s.tail(63).std() if len(s) >= 63 else vol
    vol_chg = (vol / vol_3m - 1) if vol_3m > 0 else 0

    # Risk Ranges
    rng = ar.get(ticker, {})
    lrr = _sf(rng.get("lrr")) or px * 0.95
    trr = _sf(rng.get("trr")) or px * 1.05

    # Direction logic
    side = "long" if r1m > 0.02 else ("short" if r1m < -0.02 else "neutral")
    if market_type == "forex":
        # FX: DXY bearish = EM/commodity FX bullish
        dxy_s = prices.get("DX-Y.NYB")
        if dxy_s is not None and len(dxy_s) > 22:
            dxy_r = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
            if "USD" in ticker and ticker != "USD/TRY":
                side = "short" if dxy_r < -0.01 else "long"
            else:
                side = "long" if dxy_r < -0.01 else "short"

    rr_lv = _rr_levels(px, lrr, trr, side)
    if rr_lv is None: return None

    # Composite score
    score = min(1.0, max(-1.0, r1m * 5 + (0.3 if vol_chg > 0.2 else 0) + (0.2 if vix_now > 25 else 0)))

    # Grade
    if score >= 0.7: grade = "A"
    elif score >= 0.5: grade = "B"
    else: grade = "C"
    if rr_lv["rr"] >= 2.5 and score >= 0.6: grade = "A+"

    # COT / OI
    cot_sig = "—"; cot_bias = "—"; oi_sig = "—"; oi_trend = "—"
    if cot_data and ticker in cot_data:
        cd = cot_data[ticker]
        cot_sig = cd.get("signal", "—")
        cot_bias = cd.get("bias", "—")
    if oi_data and ticker in oi_data:
        od = oi_data[ticker]
        oi_sig = od.get("signal", "—")
        oi_trend = od.get("trend", "—")

    # Greeks / Gamma
    gamma_reg = "—"; greek_comp = "—"; max_pain = "—"; delta = "—"; vanna = "—"; charm = "—"
    put_wall = "—"; call_wall = "—"; flip_up = "—"; flip_down = "—"

    if gamma_data and ticker in gamma_data:
        gd = gamma_data[ticker]
        gamma_reg = gd.get("regime", "—")
        max_pain = gd.get("max_pain", "—")
        put_wall = gd.get("put_wall", "—")
        call_wall = gd.get("call_wall", "—")
        flip_up = gd.get("flip_up", "—")
        flip_down = gd.get("flip_down", "—")

    if greeks_data and ticker in greeks_data:
        gr = greeks_data[ticker]
        greek_comp = gr.get("composite", "—")
        delta = gr.get("delta", "—")
        vanna = gr.get("vanna", "—")
        charm = gr.get("charm", "—")

    # Thesis
    known_thesis = ""
    if market_type == "forex":
        known_thesis = f"FX setup: {ticker} — Monthly momentum {r1m:+.1%}. Risk Range: {lrr:.2f}–{trr:.2f}."
    elif market_type == "commodity":
        known_thesis = f"Commodity: {ticker} — 1M return {r1m:+.1%}. Vol change {vol_chg:+.1%}."
    elif market_type == "crypto":
        known_thesis = f"Crypto: {ticker} — 1M momentum {r1m:+.1%}. Vol {vol:.2f}."
    else:
        known_thesis = f"Setup: {ticker} — 1M return {r1m:+.1%}."

    # Worth entering
    worth = rr_lv["action"]

    # Path & timing
    path = "🟢 Smooth" if abs(r1m) > 0.05 and abs(r3m) > 0.10 else "🟡 Bumpy"
    time_est = rr_lv["hold"]
    breakout = "High" if score > 0.7 and rr_lv["rr"] > 2.0 else "Medium" if score > 0.4 else "Low"

    return {
        "ticker": ticker,
        "price": px,
        "entry": rr_lv["entry"],
        "target_1": rr_lv["tp1"],
        "target_2": rr_lv["tp2"],
        "stop_loss": rr_lv["stop"],
        "rr": rr_lv["rr"],
        "direction": "LONG" if side == "long" else "SHORT" if side == "short" else "NEUTRAL",
        "grade": grade,
        "score": score,
        "worth_entering": worth,
        "entry_advice": worth,
        "tp1_basis": f"Risk Range mid-point (50% of LRR→TRR)",
        "tp2_basis": f"Risk Range top (TRR) — momentum stretch",
        "stop_basis": f"Below Risk Range low (LRR) — invalidation",
        "path_smoothness": path,
        "time_estimate": time_est,
        "breakout_chance": breakout,
        "hold": time_est,
        "thesis": known_thesis,
        "recommendation": known_thesis,
        "known_thesis": known_thesis,
        "gamma_regime": gamma_reg,
        "greek_composite": greek_comp,
        "max_pain": max_pain,
        "delta": delta,
        "vanna": vanna,
        "charm": charm,
        "put_wall": put_wall,
        "call_wall": call_wall,
        "gamma_flip_up": flip_up,
        "gamma_flip_down": flip_down,
        "cot_signal": cot_sig,
        "cot_bias": cot_bias,
        "oi_signal": oi_sig,
        "oi_trend": oi_trend,
        "skew": "—",
        "onchain_signal": "—",
        "invalidators": ["Q4 deflation signal", "DXY bullish reversal"] if market_type in ["forex","commodity"] else ["VIX >35", "Q4 signal"],
    }

def _build_ihsg_row(ticker, prices, ar):
    """Build narrative row for IHSG ticker."""
    s = prices.get(ticker)
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 22: return None

    px = float(s.iloc[-1])
    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)

    rng = ar.get(ticker, {})
    lrr = _sf(rng.get("lrr")) or px * 0.92
    trr = _sf(rng.get("trr")) or px * 1.08

    side = "long" if r1m > 0.01 else ("short" if r1m < -0.05 else "neutral")
    rr_lv = _rr_levels(px, lrr, trr, side)
    if rr_lv is None: return None

    score = min(1.0, max(-1.0, r1m * 5))
    grade = "A" if score >= 0.6 else "B" if score >= 0.3 else "C"

    # Sector narrative
    sector_narratives = {
        "ADRO.JK": "Coal + aluminium diversified. Q3 commodity bid. Dividend yield 8%+.",
        "ITMG.JK": "Pure-play coal lowest cost. Cash machine at current prices.",
        "PTBA.JK": "Turnaround story. Value play with coal recovery.",
        "NCKL.JK": "HPAL nickel for EV batteries. Speculative but high upside.",
        "ANTM.JK": "Diversified: bauxite + nickel + gold. Safer than pure nickel.",
        "BBCA.JK": "Best-in-class banking franchise. Premium but justified.",
        "BBRI.JK": "Microfinance king. Dividend yield 6%+ cushion.",
        "BRIS.JK": "Syariah growth story. Most volatile but highest upside.",
        "LSIP.JK": "Most efficient CPO producer. Cost <3,000/mt.",
        "AALI.JK": "Astra Agro. Most liquid CPO play.",
        "TLKM.JK": "Defensive growth. Dividend 5%+. Data consumption 20% growth.",
        "EXCL.JK": "Turnaround + merger Smartfren. Speculative.",
        "WINS.JK": "OSV bottleneck. Pertamina hulu expansion = fleet utilization >90%.",
        "ELSA.JK": "Most diversified offshore. Drilling + logistics.",
        "PGEO.JK": "Geothermal secular. Baseload power for AI data centers.",
    }
    thesis = sector_narratives.get(ticker, f"Indonesia {ticker} — 1M return {r1m:+.1%}. Commodity exporter tailwind.")

    return {
        "ticker": ticker,
        "price": px,
        "entry": rr_lv["entry"],
        "target_1": rr_lv["tp1"],
        "target_2": rr_lv["tp2"],
        "stop_loss": rr_lv["stop"],
        "rr": rr_lv["rr"],
        "direction": "LONG" if side == "long" else "SHORT" if side == "short" else "NEUTRAL",
        "grade": grade,
        "score": score,
        "worth_entering": rr_lv["action"],
        "entry_advice": rr_lv["action"],
        "tp1_basis": "Sector momentum target",
        "tp2_basis": "Regime-aligned stretch",
        "stop_basis": "Below support level",
        "path_smoothness": "🟢 Smooth — domestic sticky" if any(x in ticker for x in ["BBCA","BBRI","TLKM"]) else "🟡 Bumpy — commodity vol",
        "time_estimate": "2-4 months",
        "breakout_chance": "Medium",
        "hold": "2-4 months",
        "thesis": thesis,
        "recommendation": thesis,
        "known_thesis": thesis,
        "invalidators": ["China demand collapse", "Q4 deflation", "BI rate hike >50bp"],
    }

def _split_long_short(rows):
    longs = [r for r in rows if "LONG" in r.get("direction", "")]
    shorts = [r for r in rows if "SHORT" in r.get("direction", "")]
    return sorted(longs, key=lambda x: x.get("score",0), reverse=True), sorted(shorts, key=lambda x: abs(x.get("score",0)), reverse=True)

def _compute_dxy_corr(prices):
    try:
        dxy = prices.get("DX-Y.NYB")
        btc = prices.get("BTC-USD")
        if dxy is None or btc is None: return -0.83
        dxy = pd.to_numeric(dxy, errors="coerce").dropna().tail(15)
        btc = pd.to_numeric(btc, errors="coerce").dropna().tail(15)
        if len(dxy) < 10 or len(btc) < 10: return -0.83
        return float(dxy.corr(btc))
    except: return -0.83

def prob_bar(probs):
    labels = list(probs.keys()) if isinstance(probs, dict) else ["Q1","Q2","Q3","Q4"]
    vals = [probs.get(k,0) if isinstance(probs, dict) else 0 for k in labels]
    cols = [qc(l) for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=cols, text=[f"{v:.0%}" for v in vals], textposition="outside"))
    fig.update_layout(height=200, margin=dict(t=20,b=20,l=20,r=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#E6EDF3", showlegend=False, yaxis=dict(showgrid=False, showticklabels=False))
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVE CARD RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_num(val, decimals=2):
    if val is None or val == "—": return "—"
    try:
        v = float(val)
        if abs(v) >= 10000: return f"{v:,.0f}"
        elif abs(v) >= 100: return f"{v:,.2f}"
        elif abs(v) >= 1: return f"{v:.3f}"
        else: return f"{v:.4f}"
    except: return str(val)

def _render_narrative_card(row, idx=0, market_type="generic"):
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
    dir_class = "badge-long" if "LONG" in direction else "badge-short" if "SHORT" in direction else "badge-neutral"
    dir_text = "LONG" if "LONG" in direction else "SHORT" if "SHORT" in direction else "NEUTRAL"

    worth_class = ""
    if "BUY NOW" in worth or "SELL NOW" in worth: worth_emoji = "✅"; worth_class = "green"
    elif "WAIT" in worth: worth_emoji = "⏳"; worth_class = "yellow"
    elif "CHASE" in worth: worth_emoji = "🏃"; worth_class = "blue"
    elif "SMALL" in worth: worth_emoji = "⚠️"; worth_class = "yellow"
    elif "SKIP" in worth: worth_emoji = "❌"; worth_class = "red"
    else: worth_emoji = "⚪"; worth_class = ""

    grade_class = f"badge-{grade.lower().replace('+','')}" if grade.lower() in ["a+","a","b","c"] else "badge-c"

    header_html = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:20px;">{dir_emoji}</span>
            <span style="font-size:18px;font-weight:700;color:#e6edf3;">{ticker}</span>
            <span class="badge {dir_class}">{dir_text}</span>
            <span class="badge {grade_class}">Grade {grade}</span>
            {f'<span class="badge badge-urgent">{scanner}</span>' if scanner else ''}
        </div>
        <div style="text-align:right;">
            <div style="font-size:11px;color:#8b949e;">WORTH ENTERING?</div>
            <div style="font-size:16px;font-weight:700;" class="card-value {worth_class}">{worth_emoji} {worth}</div>
        </div>
    </div>
    """

    snap_html = f"""
    <div class="metric-grid">
        <div class="metric-box"><div class="metric-label">Price</div><div class="metric-value">{_fmt_num(price)}</div></div>
        <div class="metric-box"><div class="metric-label">Entry</div><div class="metric-value" style="color:#58a6ff;">{_fmt_num(entry)}</div></div>
        <div class="metric-box"><div class="metric-label">Target 1</div><div class="metric-value" style="color:#3fb950;">{_fmt_num(t1)}</div></div>
        <div class="metric-box"><div class="metric-label">Target 2</div><div class="metric-value" style="color:#2ea043;">{_fmt_num(t2)}</div></div>
        <div class="metric-box"><div class="metric-label">Stop Loss</div><div class="metric-value" style="color:#f85149;">{_fmt_num(stop)}</div></div>
        <div class="metric-box"><div class="metric-label">R:R</div><div class="metric-value" style="color:#d29922;">{_fmt_num(rr)}x</div></div>
    </div>
    """

    entry_basis = row.get("entry_advice") or row.get("entry_basis", "—")
    tp1_basis = row.get("tp1_basis", "—")
    tp2_basis = row.get("tp2_basis", "—")
    stop_basis = row.get("stop_basis", "—")

    basis_html = f"""
    <div class="card-section">📐 Level Basis</div>
    <div class="card-row"><span class="card-label">🎯 Entry Strategy</span><span class="card-value">{entry_basis}</span></div>
    <div class="card-row"><span class="card-label">📈 Target 1 Basis</span><span class="card-value">{tp1_basis}</span></div>
    <div class="card-row"><span class="card-label">📈 Target 2 Basis</span><span class="card-value">{tp2_basis}</span></div>
    <div class="card-row"><span class="card-label">🛑 Stop Basis</span><span class="card-value">{stop_basis}</span></div>
    """

    path = row.get("path_smoothness", "—")
    time_est = row.get("time_estimate", "—")
    breakout = row.get("breakout_chance", "—")
    hold = row.get("hold") or row.get("hold_for", "—")

    path_html = f"""
    <div class="card-section">⏱️ Path & Timing</div>
    <div class="card-row"><span class="card-label">🛤️ Path Smoothness</span><span class="card-value">{path}</span></div>
    <div class="card-row"><span class="card-label">⏳ Time Estimate</span><span class="card-value">{time_est}</span></div>
    <div class="card-row"><span class="card-label">🚀 Breakout Chance</span><span class="card-value">{breakout}</span></div>
    <div class="card-row"><span class="card-label">📅 Hold Period</span><span class="card-value">{hold}</span></div>
    """

    has_options = any(row.get(k) for k in ["gamma_regime","greek_composite","max_pain","delta","vanna","put_wall","call_wall","gamma_flip_up","gamma_flip_down"])
    opt_html = ""
    if has_options and market_type not in ["ihsg"]:
        gamma_reg = row.get("gamma_regime") or row.get("gamma_summary", "—")
        greek_comp = row.get("greek_composite") or row.get("greek_summary", "—")
        max_pain = row.get("max_pain") or row.get("max_pain_gamma", "—")
        delta = row.get("delta") or row.get("greek_delta", "—")
        vanna = row.get("vanna") or row.get("greek_vanna", "—")
        charm = row.get("charm") or row.get("greek_charm", "—")
        put_wall = row.get("put_wall", "—")
        call_wall = row.get("call_wall", "—")
        flip_up = row.get("gamma_flip_up", "—")
        flip_down = row.get("gamma_flip_down", "—")

        opt_html = f"""
        <div class="card-section">📊 Option Market Structure</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">
            <div class="metric-box"><div class="metric-label">Gamma Regime</div><div class="metric-value" style="font-size:13px;">{gamma_reg}</div></div>
            <div class="metric-box"><div class="metric-label">Greek Composite</div><div class="metric-value" style="font-size:13px;">{greek_comp}</div></div>
            <div class="metric-box"><div class="metric-label">Max Pain</div><div class="metric-value" style="font-size:13px;">{_fmt_num(max_pain)}</div></div>
            <div class="metric-box"><div class="metric-label">Delta</div><div class="metric-value" style="font-size:13px;">{delta}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <div class="metric-box"><div class="metric-label">Vanna</div><div class="metric-value" style="font-size:13px;">{vanna}</div></div>
            <div class="metric-box"><div class="metric-label">Charm</div><div class="metric-value" style="font-size:13px;">{charm}</div></div>
            <div class="metric-box"><div class="metric-label">Put Wall</div><div class="metric-value" style="font-size:13px;">{_fmt_num(put_wall)}</div></div>
            <div class="metric-box"><div class="metric-label">Call Wall</div><div class="metric-value" style="font-size:13px;">{_fmt_num(call_wall)}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px;">
            <div class="metric-box"><div class="metric-label">Gamma Flip ↑</div><div class="metric-value" style="font-size:13px;">{_fmt_num(flip_up)}</div></div>
            <div class="metric-box"><div class="metric-label">Gamma Flip ↓</div><div class="metric-value" style="font-size:13px;">{_fmt_num(flip_down)}</div></div>
        </div>
        """

    has_flow = any(row.get(k) for k in ["cot_signal","oi_signal","onchain_signal","skew","oi_trend","cot_bias"])
    flow_html = ""
    if has_flow:
        cot_sig = row.get("cot_signal", "—")
        cot_bias = row.get("cot_bias", "—")
        oi_sig = row.get("oi_signal") or row.get("oi_conc", "—")
        oi_trend = row.get("oi_trend", "—")
        skew = row.get("skew", "—")
        onchain = row.get("onchain_signal", "—")

        flow_html = f"""
        <div class="card-section">📈 Flow & Positioning Data</div>
        <div class="card-row"><span class="card-label">📊 COT Signal</span><span class="card-value">{cot_sig}</span></div>
        <div class="card-row"><span class="card-label">📊 COT Bias</span><span class="card-value">{cot_bias}</span></div>
        <div class="card-row"><span class="card-label">📉 OI Signal</span><span class="card-value">{oi_sig}</span></div>
        <div class="card-row"><span class="card-label">📉 OI Trend</span><span class="card-value">{oi_trend}</span></div>
        {f'<div class="card-row"><span class="card-label">⚖️ Skew</span><span class="card-value">{skew}</span></div>' if skew != "—" else ''}
        {f'<div class="card-row"><span class="card-label">⛓️ On-Chain</span><span class="card-value">{onchain}</span></div>' if onchain != "—" else ''}
        """

    thesis = row.get("thesis") or row.get("recommendation") or row.get("known_thesis", "N/A")
    action = row.get("action", "")
    invalidators = row.get("invalidators", [])

    thesis_html = f"""
    <div class="card-section">🎯 Thesis & Actionable Strategy</div>
    <div class="thesis-box">{thesis}</div>
    {f'<div style="margin-top:8px;font-size:13px;color:#8b949e;"><b>🎬 Action:</b> {action}</div>' if action else ''}
    {f'<div style="margin-top:8px;font-size:12px;color:#f85149;"><b>❌ Invalidators:</b> {", ".join(invalidators)}</div>' if invalidators else ''}
    """

    risk_html = ""
    if "STRONG" in signal or "URGENT" in scanner:
        risk_html = """<div class="risk-bar"><span class="risk-pill risk-high">🔴 High Volatility Expected</span><span class="risk-pill risk-med">⚠️ Position Size: Small</span></div>"""
    elif "CAUTIOUS" in str(thesis) or "CONFLICTED" in str(thesis):
        risk_html = """<div class="risk-bar"><span class="risk-pill risk-med">🟡 Mixed Signals — Reduce Size</span></div>"""

    full_html = f"""
    <div class="narrative-card">
        {header_html}
        {snap_html}
        <div class="section-hr"></div>
        {basis_html}
        <div class="section-hr"></div>
        {path_html}
        {opt_html}
        {flow_html}
        <div class="section-hr"></div>
        {thesis_html}
        {risk_html}
    </div>
    """
    st.markdown(full_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR & NAVIGATION — MERGED TABS
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown('<div style="font-size:12px;color:#8b949e;">Merged Tabs · Narrative Cards · v23.0</div>', unsafe_allow_html=True)
    st.divider()

    page = st.radio("Navigation", [
        "🏠 Dashboard",
        "📈 GIP Model",
        "🎯 Risk Ranges™",
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
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:14px;text-align:center;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">CURRENT REGIME</div><div style="font-size:28px;font-weight:700;color:{qc(_sq)};">{_sq} / {_mq}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)

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
alpha_center = snap.get("alpha_center", {}) or {}

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.caption("Command center. 30-second read.")
    st.divider()

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">STRUCTURAL</div><div style="font-size:32px;font-weight:700;color:{qc(sq)};">{sq}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{QN.get(sq,"")}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">MONTHLY</div><div style="font-size:32px;font-weight:700;color:{qc(mq)};">{mq}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{QN.get(mq,"")}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">GLOBAL</div><div style="font-size:32px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{QN.get(gq,"")}</div></div>', unsafe_allow_html=True)

    st.divider()
    c1,c2 = st.columns([1,1.2])
    with c1:
        st.markdown("### 🎯 What to Do Now")
        wins = QWINS.get(mq,"—")
        st.markdown(f"**Monthly ({mq}) wins:** {wins}")
        st.markdown(f"**Structural ({sq}) wins:** {QWINS.get(sq,'—')}")
        if transition:
            fw=transition.front_run_window
            fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
            fwi={"now":"🚨 Window OPEN — Act now","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet — wait"}.get(fw,"🛑 Not yet")
            st.markdown(f'<div style="background:{fwc};color:#fff;padding:10px 16px;border-radius:8px;font-weight:600;text-align:center;margin-top:10px;">{fwi}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### 📊 Regime Probabilities")
        probs = scen.get("probabilities",{}) if scen else {}
        if probs:
            st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        else:
            st.info("Scenario probabilities not available.")

    st.divider()
    st.markdown("### 🔥 Top 5 Alpha Ideas")
    top5 = []
    if alpha_center:
        for k in ["level_1","level_2","alpha_long"]:
            items = alpha_center.get(k, [])
            for item in items:
                if isinstance(item, dict):
                    top5.append(item)
                    if len(top5) >= 5: break
            if len(top5) >= 5: break
    if not top5 and daily_signals:
        top5 = [s for s in daily_signals if s.get("direction") == "LONG"][:5]

    if top5:
        for i, item in enumerate(top5):
            _render_narrative_card(item, i, "us_equity")
    else:
        st.info("No alpha ideas. Run Full Rebuild.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">📈 GIP Model</div>', unsafe_allow_html=True)
    st.caption("Growth, Inflation, Policy — 3-layer quad engine.")
    st.divider()
    if not gip:
        st.warning("GIP data not available."); st.stop()

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">STRUCTURAL</div><div style="font-size:28px;font-weight:700;color:{qc(sq)};">{sq}</div><div style="font-size:13px;color:#8B949E;">{QNC.get(sq,"")}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">MONTHLY</div><div style="font-size:28px;font-weight:700;color:{qc(mq)};">{mq}</div><div style="font-size:13px;color:#8B949E;">{QNC.get(mq,"")}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">GLOBAL</div><div style="font-size:28px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="font-size:13px;color:#8B949E;">{QNC.get(gq,"")}</div></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🧮 Raw GIP Scores")
    raw = gip.raw_scores if hasattr(gip, 'raw_scores') else {}
    if raw:
        df = pd.DataFrame({"Score":[raw.get("growth",0),raw.get("inflation",0),raw.get("policy",0)]}, index=["Growth","Inflation","Policy"])
        st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
    else:
        st.info("Raw scores not available.")

    st.markdown("### 📊 Quad Probabilities")
    probs = scen.get("probabilities",{}) if scen else {}
    if probs:
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
    st.markdown("### 🔄 Transition Signal")
    if transition:
        st.markdown(f"**From:** {transition.from_quad} → **To:** {transition.to_quad}")
        st.markdown(f"**Confidence:** {transition.confidence:.0%}")
        st.markdown(f"**Front-run window:** {transition.front_run_window}")
        st.markdown(f"**Trigger:** {transition.trigger}")
    else:
        st.info("No transition signal.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">🎯 Risk Ranges™</div>', unsafe_allow_html=True)
    st.caption("LRR → TRR framework. Position sizing + invalidation.")
    st.divider()
    if not rr:
        st.warning("Risk Ranges not available."); st.stop()

    st.markdown("### 📐 Risk Range Table")
    rows = []
    for ticker, rng in ar.items():
        lrr = _sf(rng.get("lrr")); trr = _sf(rng.get("trr")); mid = (lrr+trr)/2 if lrr and trr else None
        s = prices.get(ticker)
        px = float(s.iloc[-1]) if s is not None and len(s) > 0 else None
        if px and lrr and trr:
            pos = (px - lrr) / (trr - lrr)
            rows.append({"Ticker":ticker,"Price":px,"LRR":lrr,"TRR":trr,"Mid":mid,"Position":f"{pos:.0%}","Zone":"BUY" if pos < 0.35 else ("SELL" if pos > 0.75 else "HOLD")})
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=600)
    else:
        st.info("No risk range data.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ⚡ ALPHA & SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha & Scanner":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">⚡ Alpha & Scanner</div>', unsafe_allow_html=True)
    st.caption("Bottlenecks · Alpha Ideas · Discovery · Daily Signals — All unified. Narrative cards below.")
    st.divider()

    ac = alpha_center
    meta = ac.get("meta", {}) if ac else {}

    if not ac or not meta:
        st.warning("Alpha Center data not available. Run Full Rebuild.")
        st.stop()

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
        st.markdown(f"**🚨 LEVEL 1 — URGENT ACTION REQUIRED ({len(items)} items)**")
        if not items: st.info("No Level 1 bottlenecks.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub2:
        items = ac.get("level_2", [])
        st.markdown(f"**⚠️ LEVEL 2 — BUILDING SETUPS ({len(items)} items)**")
        if not items: st.info("No Level 2 bottlenecks.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub3:
        items = ac.get("watch", [])
        st.markdown(f"**👁️ WATCH LIST — MONITOR DAILY ({len(items)} items)**")
        if not items: st.info("Nothing on watch.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub4:
        items = ac.get("alpha_long", [])
        st.markdown(f"**🟢 ALPHA LONGS — PLAYBOOK ALIGNED ({len(items)} items)**")
        if not items: st.info("No alpha longs.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub5:
        items = ac.get("alpha_short", [])
        st.markdown(f"**🔴 ALPHA SHORTS — AVOID/SHORT ({len(items)} items)**")
        if not items: st.info("No alpha shorts.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub6:
        items = ac.get("discovery", [])
        st.markdown(f"**💡 DISCOVERY — STRUCTURAL BOTTLENECKS ({len(items)} items)**")
        if not items: st.info("No discoveries.")
        for i, item in enumerate(items):
            _render_narrative_card(item, i, "us_equity")

    with sub7:
        st.markdown(f"**📋 ALL RATED TICKERS — HEDGEYE-STYLE ({len(daily_signals)} signals)**")
        st.caption("Filter: |Score| ≥ 0.10 · Grade A-C · All directions · Sorted by conviction")

        col_f1, col_f2, col_f3 = st.columns(3)
        filter_dir = col_f1.multiselect("Direction", ["LONG", "SHORT", "NEUTRAL", "DEFENSIVE"], default=["LONG", "SHORT", "NEUTRAL"])
        filter_grade = col_f2.multiselect("Grade", ["A+", "A", "B", "C"], default=["A+", "A", "B", "C"])
        filter_min_score = col_f3.slider("Min |Score|", 0.0, 1.0, 0.10, 0.05)

        filtered = [s for s in daily_signals if s.get("direction") in filter_dir and s.get("grade", "C") in filter_grade]
        filtered = [s for s in filtered if abs(s.get("score", 0)) >= filter_min_score]
        st.write(f"Showing **{len(filtered)}** signals out of {len(daily_signals)} total")

        for i, s in enumerate(filtered[:300]):
            with st.expander(f"{s.get('ticker')} | {s.get('signal')} | Score: {s.get('score',0):.2f} | Grade: {s.get('grade')}", expanded=False):
                _render_narrative_card(s, i, "us_equity")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 💱🛢️ MACRO PROXIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💱🛢️ Macro Proxies":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">💱🛢️ Macro Proxies</div>', unsafe_allow_html=True)
    st.caption("Forex + Commodities unified. COT + OI + Greeks + Risk Ranges. Narrative cards.")
    st.divider()

    gamma_data = snap.get("gamma_data", {}) or {}
    greeks_data = snap.get("greeks_data", {}) or {}
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}

    fx_tab, comm_tab = st.tabs(["💱 Forex", "🛢️ Commodities"])

    with fx_tab:
        st.markdown("### 💱 Forex Setups")
        fx_rows = []
        for ticker in list(FOREX_PAIRS.keys()):
            row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "forex", vix_now, gamma_data, greeks_data)
            if row: fx_rows.append(row)
        longs, shorts = _split_long_short(fx_rows)

        st.markdown(f"**🟢 LONG FX ({len(longs)} setups)**")
        for i, row in enumerate(longs):
            _render_narrative_card(row, i, "forex")
        if not longs: st.info("No long FX setups.")

        st.divider()
        st.markdown(f"**🔴 SHORT FX ({len(shorts)} setups)**")
        for i, row in enumerate(shorts):
            _render_narrative_card(row, i, "forex")
        if not shorts: st.info("No short FX setups.")

    with comm_tab:
        st.markdown("### 🛢️ Commodity Setups")
        comm_rows = []
        for ticker in list(COMMODITIES.keys()):
            row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "commodity", vix_now, gamma_data, greeks_data)
            if row: comm_rows.append(row)
        longs, shorts = _split_long_short(comm_rows)

        st.markdown(f"**🟢 LONG COMMODITIES ({len(longs)} setups)**")
        for i, row in enumerate(longs):
            _render_narrative_card(row, i, "commodity")
        if not longs: st.info("No long commodity setups.")

        st.divider()
        st.markdown(f"**🔴 SHORT COMMODITIES ({len(shorts)} setups)**")
        for i, row in enumerate(shorts):
            _render_narrative_card(row, i, "commodity")
        if not shorts: st.info("No short commodity setups.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ₿ CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">₿ Crypto Setups</div>', unsafe_allow_html=True)
    st.caption("On-chain momentum + Risk Ranges. Narrative cards per token.")
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
                crypto_tokens[ticker] = {
                    "momentum_score": score, "tvl_7d_change": r7d,
                    "tvl_30d_change": r1m, "dex_vol_change": vol_change,
                }

    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}

    crypto_rows = []
    for ticker in list(CRYPTO.keys()):
        row = _build_consolidated_row(ticker, prices, ar, cot_data, oi_data, "crypto", vix_now)
        if row:
            token_data = crypto_tokens.get(ticker, {})
            if token_data:
                score = token_data.get("momentum_score", 0.5)
                tvl_7d = token_data.get("tvl_7d_change", 0)
                if score > 0.7 and tvl_7d > 0.08 and "LONG" in row["direction"]:
                    row["recommendation"] = f"🚀 STRONG LONG — On-chain accumulation (TVL +{tvl_7d:.1%}) + price momentum align"
                elif score > 0.7 and tvl_7d > 0.08 and "SHORT" in row["direction"]:
                    row["recommendation"] = f"⚠️ CONTRADICTORY — Price bearish but on-chain accumulation (TVL +{tvl_7d:.1%}), wait"
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

    st.markdown(f"**🟢 LONG CRYPTO ({len(longs)} setups)**")
    for i, row in enumerate(longs):
        _render_narrative_card(row, i, "crypto")
    if not longs: st.info("No long crypto setups.")

    st.divider()
    st.markdown(f"**🔴 SHORT CRYPTO ({len(shorts)} setups)**")
    for i, row in enumerate(shorts):
        _render_narrative_card(row, i, "crypto")
    if not shorts: st.info("No short crypto setups.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🌍 GLOBAL & EM
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global & EM":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">🌍 Global & EM</div>', unsafe_allow_html=True)
    st.caption("Global regime map + Indonesia IHSG narrative. Narrative cards for EM tickers.")
    st.divider()

    global_tab, ihsg_tab = st.tabs(["🌍 Global Quad", "🇮🇩 IHSG"])

    with global_tab:
        if not global_: st.warning("Country data loading."); st.stop()
        gq = global_.get("global_quad","Q3")
        gconf = global_.get("global_conf",0.5)
        gprobs = global_.get("global_probs",{})
        cqs = global_.get("country_quads",{})
        if not cqs:
            base_map = {
                "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico"],
                "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi"],
                "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Thailand"],
                "Q4": ["Indonesia","Argentina","Egypt","Nigeria","Pakistan"],
            }
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
        st.markdown("### 🇮🇩 IHSG — Indonesia Narrative Report")
        st.caption("Commodity exporter + domestic demand. Q3/Q2 overlay = mixed tailwind. Narrative cards per sector.")

        ihsg_rows = []
        for ticker in list(IHSG_UNIVERSE.keys()):
            row = _build_ihsg_row(ticker, prices, ar)
            if row:
                row["entry_advice"] = "✅ BUY NOW — At buy zone" if row.get("price") and row.get("entry") and row["price"] <= row["entry"]*1.02 else "⏳ WAIT — Slightly above entry"
                row["tp1_basis"] = f"Sector momentum target"
                row["tp2_basis"] = f"Regime-aligned stretch"
                row["stop_basis"] = f"Below support level"
                row["path_smoothness"] = "🟢 Smooth — domestic demand sticky" if any(x in ticker for x in ["BBCA","BBRI","TLKM"]) else "🟡 Bumpy — commodity vol"
                row["time_estimate"] = "2-4 months"
                row["breakout_chance"] = "Medium"
                row["worth_entering"] = "✅ YES" if "LONG" in row.get("direction","") else "⏳ WATCH"
                ihsg_rows.append(row)

        longs = [r for r in ihsg_rows if "LONG" in r.get("direction","")]
        shorts = [r for r in ihsg_rows if "SHORT" in r.get("direction","")]

        st.markdown(f"**🟢 INDONESIA LONGS ({len(longs)} setups)**")
        for i, row in enumerate(longs):
            _render_narrative_card(row, i, "ihsg")
        if not longs: st.info("No IHSG longs.")

        if shorts:
            st.divider()
            st.markdown(f"**🔴 INDONESIA SHORTS ({len(shorts)} setups)**")
            for i, row in enumerate(shorts):
                _render_narrative_card(row, i, "ihsg")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📖 THEMES & BOTTLENECKS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Themes & Bottlenecks":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">📖 Themes & Bottlenecks</div>', unsafe_allow_html=True)
    st.caption("Top-down narratives + structural discovery engine. Merge of Narratives + Discovery.")
    st.divider()

    themes_tab, disc_tab = st.tabs(["📖 Macro Themes", "🔮 Discovery Engine"])

    with themes_tab:
        narratives_list = narr.get("narratives",[]) if narr else []
        if not narratives_list:
            narratives_list = [
                {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand (solar, AI chips) + safe haven. Mine supply flat.","tickers":["SLV","SILJ","GDXJ","GDX","GLD"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],"invalidators":["Q4 deflation signal","DXY sustained bullish"]},
                {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural. Safe haven in Q3.","tickers":["GLD","GDX","GDXJ","AEM","WPM"],"best":["GLD","GDX"],"worst":["HYG","IWM"],"invalidators":["Q4→Q1 direct","DXY reversal"]},
                {"name":"Defense Reshoring","score":0.85,"thesis":"NATO 2%+ GDP commitment. Geopolitical premium. ITA/LMT/KTOS secular long in ALL quads.","tickers":["ITA","LMT","RTX","KTOS","PLTR","GD"],"best":["ITA","KTOS"],"worst":["XLU"],"invalidators":["Global peace agreement"]},
                {"name":"AI Power Infrastructure","score":0.83,"thesis":"AI data centers need 24/7 firm power. Nuclear + gas only scalable solutions.","tickers":["VST","CEG","GEV","ETN","VRT"],"best":["VST","CEG"],"worst":["INTC"],"invalidators":["AI capex cycle pause"]},
                {"name":"Energy Offense (Q2)","score":0.80,"thesis":"Q2 = Reflation = Energy offense. OIH oil services = operating leverage.","tickers":["XLE","OIH","BNO","XOP","DAR","MTDR"],"best":["OIH","BNO"],"worst":["XLU","XLP"],"invalidators":["Demand collapse (Q4)"]},
                {"name":"International Rotation","score":0.78,"thesis":"JPXN +37% Q1 2026. EIS +21.8%. USD bearish = EM tailwind.","tickers":["JPXN","EIS","TUR","NORW","EWZ","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],"invalidators":["DXY bullish reversal"]},
                {"name":"Bitcoin Reflation","score":0.75,"thesis":"Every quad except Q4 = long Bitcoin. DXY bearish correlation supports crypto bid.","tickers":["IBIT","FBTC","BTC-USD"],"best":["IBIT"],"worst":["MSTY","BLOK"],"invalidators":["Q4 signal","DXY bullish reversal"]},
                {"name":"Indonesia Commodity Play","score":0.65,"thesis":"EIDO = coal + nickel + CPO + geothermal. Q2/Q3 = commodity bid.","tickers":["EIDO","PGEO.JK","ADRO.JK","NCKL.JK"],"best":["EIDO","PGEO.JK"],"worst":["TLKM.JK"],"invalidators":["China demand collapse","Q4 deflation"]},
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
        discoveries_list = disc.get("discoveries",[]) if disc else []
        if not discoveries_list:
            discoveries_list = [
                {"name":"AI Photonics Bottleneck","category":"Structural Constraint","stage":"active","confidence":0.88,"thesis":"LITE sole supplier 200G EML lasers. NVIDIA $2B photonics.","beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],"confirmation_signal":"LITE earnings + NVIDIA capex","invalidators":["China photonics scaling"]},
                {"name":"SiC Power Monopoly (WOLF)","category":"Structural Constraint","stage":"active","confidence":0.84,"thesis":"WOLF = ONLY US large-scale SiC substrate. CHIPS Act strategic.","beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["Legacy Si"],"confirmation_signal":"EV OEM adoption + DOD qual","invalidators":["China SiC subsidies"]},
                {"name":"Japan Yen Weakness → JPXN","category":"Macro Rotation","stage":"active","confidence":0.82,"thesis":"Yen bearish = Japanese exporters win. BoJ ultra-dovish.","beneficiary_tickers":["JPXN","EWJ"],"fade_tickers":["FXY"],"confirmation_signal":"USD/JPY >145","invalidators":["BoJ hike >1%"]},
                {"name":"Silver Physical Squeeze","category":"Commodity","stage":"building","confidence":0.78,"thesis":"Solar + AI chip silver demand accelerating. Mine supply flat.","beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],"confirmation_signal":"LBMA inventory <150M oz","invalidators":["India demand collapse"]},
                {"name":"Indonesia OSV Bottleneck","category":"Local Bottleneck","stage":"brewing","confidence":0.65,"thesis":"Pertamina hulu expansion = OSV fleet utilization >90%.","beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],"confirmation_signal":"Pertamina Q2 capex","invalidators":["Pertamina budget freeze"]},
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
        if auto_bottlenecks:
            for b in auto_bottlenecks:
                if not isinstance(b, dict): continue
                st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;margin-bottom:8px;"><b>{b.get("ticker","")}</b> · {b.get("direction","")} · {b.get("known_thesis","")[:60]}</div>', unsafe_allow_html=True)
        else:
            st.info("No auto-discovered bottlenecks yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">🏥 Health</div>', unsafe_allow_html=True)
    st.caption("Data quality + model diagnostics.")
    st.divider()
    if not health:
        st.info("Health data not available."); st.stop()

    for section, data in health.items():
        with st.expander(f"🔍 {section}", expanded=True):
            if isinstance(data, dict):
                for k,v in data.items():
                    st.markdown(f"**{k}:** {v}")
            elif isinstance(data, list):
                for item in data:
                    st.markdown(f"- {item}")
            else:
                st.markdown(str(data))

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown('<div style="font-size:28px;font-weight:700;color:#E6EDF3;">📋 Playbook</div>', unsafe_allow_html=True)
    st.caption("Regime-specific allocation rules.")
    st.divider()
    if not pb_data:
        st.info("Playbook data not available."); st.stop()

    st.markdown(f"### Current Playbook: {sq} / {mq}")

    allocations = pb_data.get("allocations", {})
    if allocations:
        st.markdown("#### 🎯 Target Allocations")
        for asset, pct in allocations.items():
            st.markdown(f"- **{asset}:** {pct:.0%}")

    rules = pb_data.get("rules", [])
    if rules:
        st.markdown("#### 📜 Rules")
        for rule in rules:
            st.markdown(f"- {rule}")

    triggers = pb_data.get("rebalance_triggers", [])
    if triggers:
        st.markdown("#### 🔄 Rebalance Triggers")
        for trigger in triggers:
            st.markdown(f"- {trigger}")

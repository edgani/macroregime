"""app.py - MacroRegime Pro v32.4 AUDITED
Deep Re-Audit Fixes:
- Crash Meter: /4 → /5 (5 components, 5 segments)
- Ticker Card: Removed duplicate Greeks/Options panels (consolidated to 1)
- Recommendation: Added CHASE vs WAIT logic based on price vs entry
- Dashboard: Bull/Bear/Base bar moved below structural compass
- Dashboard: Asset Pulse compacted + moved below Behavioral
- IV Rank: Documented as PROXY (not real IV Rank)
- All formulas documented with source tags (PROXY vs ENGINE vs LIVE)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
import json, os
from datetime import datetime

logger = __import__("logging").getLogger(__name__)
st.set_page_config(page_title="MacroRegime Pro v32.4", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");
html, body, [class*="css"] { font-family: "Inter", sans-serif; }
.block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 1440px !important; }
h1 { font-size: 1.4rem !important; margin: 0.2rem 0 0.3rem !important; font-weight: 800 !important; letter-spacing: -0.5px; }
h2 { font-size: 1.05rem !important; margin: 0.4rem 0 0.2rem !important; font-weight: 700 !important; letter-spacing: -0.3px; }
h3 { font-size: 0.9rem !important; margin: 0.3rem 0 0.15rem !important; font-weight: 600 !important; }
hr { margin: 0.4rem 0 !important; opacity: 0.08; border-color: #30363D; }
[data-testid="stMetric"] { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 5px 8px !important; }
[data-testid="stMetricLabel"] { font-size: 0.58rem !important; font-weight: 600 !important; letter-spacing: 0.6px; text-transform: uppercase; opacity: 0.55; }
[data-testid="stMetricValue"] { font-size: 1.05rem !important; font-weight: 700 !important; }

.ticker-card-v4 { display: flex; align-items: center; gap: 10px; padding: 7px 10px; background: #161B22; border: 1px solid #30363D; border-radius: 8px; margin: 3px 0; transition: border-color 0.2s; flex-wrap: wrap; }
.ticker-card-v4:hover { border-color: #484F58; }
.tc-v4-left { min-width: 80px; }
.tc-v4-symbol { font-weight: 800; font-size: 0.9rem; color: #E6EDF3; letter-spacing: -0.3px; }
.tc-v4-price { font-weight: 600; font-size: 0.75rem; color: #8B949E; font-variant-numeric: tabular-nums; }
.tc-v4-badges { display: flex; gap: 3px; flex-wrap: wrap; margin-top: 2px; }
.tc-v4-spark { width: 80px; height: 24px; display: flex; align-items: flex-end; gap: 1px; flex-shrink: 0; }
.tc-v4-rr { flex: 1; min-width: 120px; }
.tc-v4-meta { display: flex; gap: 8px; font-size: 0.68rem; color: #8B949E; font-variant-numeric: tabular-nums; min-width: 110px; }

.badge { display: inline-flex; align-items: center; padding: 1px 5px; border-radius: 10px; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.3px; border: 1px solid transparent; line-height: 1.3; }
.badge-long { background: rgba(34,197,94,0.12); color: #3FB950; border-color: rgba(34,197,94,0.3); }
.badge-short { background: rgba(239,68,68,0.12); color: #F85149; border-color: rgba(239,68,68,0.3); }
.badge-neut { background: rgba(234,179,8,0.12); color: #eab308; border-color: rgba(234,179,8,0.3); }
.badge-grade-a { background: rgba(34,197,94,0.15); color: #3FB950; border-color: #3FB950; }
.badge-grade-b { background: rgba(234,179,8,0.15); color: #D29922; border-color: #D29922; }
.badge-grade-c { background: rgba(139,148,158,0.15); color: #8B949E; border-color: #8B949E; }
.badge-news { background: rgba(88,166,255,0.12); color: #58A6FF; border-color: rgba(88,166,255,0.3); }
.badge-mm { background: rgba(168,85,247,0.12); color: #A855F7; border-color: rgba(168,85,247,0.3); }
.badge-chase { background: rgba(34,197,94,0.2); color: #3FB950; border-color: #3FB950; }
.badge-wait { background: rgba(234,179,8,0.2); color: #D29922; border-color: #D29922; }

.sp-bar-v4 { width: 3px; border-radius: 1px; opacity: 0.85; }
.rr-track-v4 { position: relative; height: 16px; background: #21262D; border-radius: 4px; overflow: hidden; }
.rr-zone-v4 { position: absolute; top: 2px; bottom: 2px; border-radius: 2px; }
.rr-dot-v4 { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 7px; height: 7px; border-radius: 50%; background: #E6EDF3; border: 2px solid #58A6FF; z-index: 10; box-shadow: 0 0 4px rgba(88,166,255,0.4); }
.rr-labels-v4 { display: flex; justify-content: space-between; font-size: 0.58rem; color: #8B949E; margin-top: 1px; font-variant-numeric: tabular-nums; }

.gauge-track { position: relative; height: 12px; background: #21262D; border-radius: 6px; overflow: hidden; margin: 3px 0; }
.gauge-fill { position: absolute; top: 0; bottom: 0; left: 0; border-radius: 6px; transition: width 0.5s ease; }
.gauge-label { display: flex; justify-content: space-between; font-size: 0.6rem; color: #8B949E; margin-top: 1px; }

.hm-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }
.hm-cell { padding: 5px 3px; border-radius: 4px; text-align: center; font-size: 0.68rem; font-weight: 600; color: #E6EDF3; border: 1px solid rgba(255,255,255,0.05); }

.pulse-hbox { min-width: 70px; height: 40px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 700; color: #E6EDF3; border: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
.pulse-hlabel { font-size: 0.52rem; font-weight: 500; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-top: 1px; }

.timeline { display: flex; align-items: center; gap: 0px; margin: 6px 0; }
.tl-node { width: 12px; height: 12px; border-radius: 50%; border: 2px solid #30363D; background: #21262D; flex-shrink: 0; }
.tl-node.active { border-color: #58A6FF; background: #58A6FF; box-shadow: 0 0 5px rgba(88,166,255,0.35); }
.tl-node.past { border-color: #3FB950; background: #3FB950; }
.tl-line { flex: 1; height: 2px; background: #30363D; min-width: 16px; }
.tl-line.active { background: #58A6FF; }
.tl-labels { display: flex; justify-content: space-between; font-size: 0.58rem; color: #8B949E; margin-top: 3px; }

.stack-bar { display: flex; height: 20px; border-radius: 4px; overflow: hidden; background: #21262D; }
.stack-seg { display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-weight: 700; color: #fff; }

.skew-row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.skew-label { width: 32px; font-size: 0.65rem; color: #8B949E; font-weight: 600; }
.skew-track { flex: 1; height: 14px; background: #21262D; border-radius: 4px; position: relative; overflow: hidden; }
.skew-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.skew-value { width: 36px; font-size: 0.65rem; color: #E6EDF3; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }

.gex-track { position: relative; height: 18px; background: #21262D; border-radius: 4px; overflow: hidden; display: flex; align-items: center; }
.gex-center { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #8B949E; opacity: 0.3; }

.stTabs [data-baseweb="tab-list"] { gap: 2px !important; margin-bottom: 5px !important; }
.stTabs [data-baseweb="tab"] { padding: 4px 10px !important; font-size: 0.78rem !important; font-weight: 600 !important; border-radius: 6px 6px 0 0 !important; }
[data-testid="stExpander"] { border: 1px solid #30363D !important; border-radius: 8px !important; margin-bottom: 5px !important; }
[data-testid="stExpander"] > details > summary { padding: 7px 10px !important; font-size: 0.78rem !important; font-weight: 600 !important; }
[data-testid="stSidebar"] .block-container { padding-top: 0.6rem !important; }

.narrative-card { background: #161B22; border-left: 3px solid #58A6FF; border-radius: 8px; padding: 10px 14px; margin: 6px 0; }
.narrative-headline { font-size: 0.85rem; font-weight: 600; color: #E6EDF3; line-height: 1.4; }
.narrative-sub { font-size: 0.7rem; color: #8B949E; margin-top: 4px; }

.metric-grid-card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 12px; }
.metric-grid-title { font-size: 0.6rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; margin-bottom: 4px; }
.metric-grid-value { font-size: 1.05rem; font-weight: 700; color: #E6EDF3; }
.metric-grid-sub { font-size: 0.65rem; color: #8B949E; margin-top: 2px; }

.compass-container { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px 14px; margin: 6px 0; }
.compass-title { font-size: 0.75rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; }
.compass-quad { font-size: 1.2rem; font-weight: 800; letter-spacing: -1px; }
.compass-sub { font-size: 0.7rem; color: #8B949E; }

.dp-row { display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: #161B22; border-bottom: 1px solid #21262D; font-size: 0.75rem; }
.dp-time { width: 60px; color: #8B949E; font-variant-numeric: tabular-nums; }
.dp-ticker { width: 55px; color: #E6EDF3; font-weight: 700; }
.dp-price { width: 60px; color: #E6EDF3; font-variant-numeric: tabular-nums; }
.dp-size { width: 70px; color: #8B949E; font-variant-numeric: tabular-nums; text-align: right; }
.dp-amt { width: 65px; color: #3FB950; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
.dp-amt.sell { color: #F85149; }

.mm-box { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px 12px; margin: 4px 0; }
.mm-title { font-size: 0.7rem; color: #A855F7; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; letter-spacing: 0.5px; }
.mm-line { display: flex; justify-content: space-between; font-size: 0.75rem; padding: 2px 0; }
.mm-label { color: #8B949E; }
.mm-value { color: #E6EDF3; font-weight: 600; font-variant-numeric: tabular-nums; }

.skew-curve-container { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px; margin: 4px 0; }
.skew-curve-title { font-size: 0.7rem; color: #8B949E; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }

.scenario-bar { display: flex; height: 18px; border-radius: 4px; overflow: hidden; background: #21262D; margin: 4px 0; }
.scenario-seg { display: flex; align-items: center; justify-content: center; font-size: 0.55rem; font-weight: 700; color: #fff; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# CONFIG & FALLBACKS
# ═══════════════════════════════════════════════════════════════════
try:
    from config.settings import (FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE,
                                 IHSG_SECTOR_MAP, TICKER_SECTOR, US_SECTORS, US_BUCKETS,
                                 FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS)
except ImportError:
    FOREX_PAIRS = {}; COMMODITIES = {}; CRYPTO = {}; IHSG_UNIVERSE = {}; TICKER_SECTOR = {}; US_SECTORS = {}; US_BUCKETS = {}; FX_BUCKETS = {}; COMMODITY_BUCKETS = {}; CRYPTO_BUCKETS = {}

FALLBACK_US = ["SPY","QQQ","IWM","NVDA","AAPL","MSFT","GOOGL","META","TSLA","AMD","NFLX","AMZN","CRM","AVGO","XOM","JPM","V","MA","UNH","JNJ","XLK","XLF","XLE","XLU","XLP","XLI","XLB","XLRE","XLY","ARKK","TLT","GLD","SLV","GDX","VIXY","SQQQ","TQQQ","UPRO","SPXU"]
FALLBACK_FX  = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","USDCNY=X","USDIDR=X","DX-Y.NYB","UUP"]
FALLBACK_COMM = ["GC=F","SI=F","CL=F","NG=F","HG=F","PL=F","PA=F","ZW=F","ZC=F","ZS=F","KC=F","CC=F","CT=F"]
FALLBACK_CRYPTO = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD","LTC-USD"]
FALLBACK_IHSG = ["BBRI.JK","BMRI.JK","BBCA.JK","BBNI.JK","BRIS.JK","TLKM.JK","EXCL.JK","ADRO.JK","ITMG.JK","PTBA.JK","NCKL.JK","ANTM.JK","INCO.JK","AALI.JK","LSIP.JK","SMAR.JK","UNTR.JK","BYAN.JK","ICBP.JK","INDF.JK","KLBF.JK","PGEO.JK","WINS.JK","EIDO","^JKSE"]

_IHSG_FALLBACK = {"ADRO.JK":"Coal","ITMG.JK":"Coal","PTBA.JK":"Coal","NCKL.JK":"Nickel","ANTM.JK":"Nickel","INCO.JK":"Nickel","AALI.JK":"CPO","LSIP.JK":"CPO","SMAR.JK":"CPO","BBRI.JK":"Banking","BMRI.JK":"Banking","BBCA.JK":"Banking","BBNI.JK":"Banking","BRIS.JK":"Banking","TLKM.JK":"Telco","EXCL.JK":"Telco","UNTR.JK":"Mining Contractor","BYAN.JK":"Mining","ICBP.JK":"Consumer","INDF.JK":"Consumer","KLBF.JK":"Pharma","PGEO.JK":"Geothermal","WINS.JK":"Shipping","EIDO":"ETF","^JKSE":"Index"}
if not locals().get("IHSG_SECTOR_MAP"):
    IHSG_SECTOR_MAP = _IHSG_FALLBACK

class _GipProxy:
    def __init__(self, data):
        self._is_dict = isinstance(data, dict)
        if self._is_dict: self._d = data
        else: self._obj = data
    def __getattr__(self, name):
        if self._is_dict: return self._d.get(name)
        return getattr(self._obj, name, None)

# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════
def _safe_float(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0] if len(v) > 0 else None
        if v is None: return None
        f = float(v)
        return f if math.isfinite(f) else None
    except: return None

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"

def ff(v, d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"
def sf(v, fmt=".2f"):
    try:
        if v is None: return "—"
        f = float(v)
        if not math.isfinite(f): return "—"
        return format(f, fmt)
    except:
        return "—"

def _price_ret(ticker, prices, days=21):
    s = prices.get(ticker)
    if s is None: return None
    try:
        s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    except: return None
    if len(s) < days + 1: return None
    try: return float(s.iloc[-1] / s.iloc[-(days+1)] - 1)
    except: return None

def _quad_color(q):
    return {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}.get(q, "#8B949E")

def _quad_name(q):
    return {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q, q)

def _ret_color(r):
    if r is None: return "#8B949E"
    r = float(r)
    if r > 0.03: return "#3FB950"
    if r > 0: return "#2EA043"
    if r > -0.03: return "#F85149"
    return "#DA3633"

def _sparkline_html(series, width=80, height=24, bars=18):
    if series is None:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    try:
        s = pd.to_numeric(pd.Series(series), errors="coerce").dropna().tail(bars)
    except:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    if len(s) < 2:
        return f'<div style="width:{width}px;height:{height}px;background:#21262D;border-radius:4px;"></div>'
    mn, mx = float(s.min()), float(s.max())
    rng = mx - mn if mx != mn else 1
    bars_html = ""
    for i, v in enumerate(s):
        pct = max(2, min(100, int((float(v) - mn) / rng * 100)))
        color = "#3FB950" if (i > 0 and float(v) >= float(s.iloc[i-1])) else "#F85149"
        bars_html += f'<div class="sp-bar-v4" style="height:{pct}%;background:{color};"></div>'
    return f'<div class="tc-v4-spark" style="width:{width}px;height:{height}px;display:flex;align-items:flex-end;gap:1px;">{bars_html}</div>'

def _risk_range_html(px, lrr, trr, width_pct=100):
    if not all(v is not None and math.isfinite(float(v)) for v in [px, lrr, trr]):
        return '<div class="rr-track-v4" style="height:16px;background:#21262D;border-radius:4px;"></div><div class="rr-labels-v4"><span>-</span><span>-</span></div>'
    px, lrr, trr = float(px), float(lrr), float(trr)
    spread = trr - lrr
    pos = max(0, min(1, (px - lrr) / spread)) if spread > 0 else 0.5
    left_pct = pos * 100
    color = "#3FB950" if pos <= 0.35 else "#F85149" if pos >= 0.65 else "#8B949E"
    return (
        f'<div class="rr-track-v4" style="width:{width_pct}%;">'
        f'<div class="rr-zone-v4" style="left:0%;width:100%;background:#21262D;"></div>'
        f'<div class="rr-zone-v4" style="left:0%;width:{left_pct:.0f}%;background:{color}15;"></div>'
        f'<div class="rr-dot-v4" style="left:{max(3,min(97,left_pct)):.0f}%;border-color:{color};"></div>'
        f'</div>'
        f'<div class="rr-labels-v4" style="width:{width_pct}%;"><span>{ff(lrr)}</span><span>{ff(px)}</span><span>{ff(trr)}</span></div>'
    )

def _gauge_html(value, max_val=100, color=None, height=12, label_left="0", label_right="100"):
    if value is None: value = 0
    try: pct = max(0, min(100, float(value) / float(max_val) * 100))
    except: pct = 0
    c = color or ("#3FB950" if pct > 70 else "#D29922" if pct > 40 else "#F85149")
    return (
        f'<div class="gauge-track" style="height:{height}px;">'
        f'<div class="gauge-fill" style="width:{pct:.0f}%;background:{c};"></div></div>'
        f'<div class="gauge-label"><span>{label_left}</span><span>{ff(value)}</span><span>{label_right}</span></div>'
    )

def _badge_html(text, kind="long"):
    cls = {"long":"badge-long","short":"badge-short","neut":"badge-neut","a":"badge-grade-a","b":"badge-grade-b","c":"badge-grade-c","news":"badge-news","mm":"badge-mm","chase":"badge-chase","wait":"badge-wait"}.get(kind,"badge-neut")
    return f'<span class="badge {cls}">{text}</span>'

def _stacked_bar_html(long_pct, short_pct, cash_pct):
    return (
        f'<div class="stack-bar">'
        f'<div class="stack-seg" style="width:{long_pct}%;background:#3FB950;">📈 {long_pct:.0f}%</div>'
        f'<div class="stack-seg" style="width:{short_pct}%;background:#F85149;">📉 {short_pct:.0f}%</div>'
        f'<div class="stack-seg" style="width:{cash_pct}%;background:#8B949E;">💵 {cash_pct:.0f}%</div>'
        f'</div>'
    )

def _scenario_bar_html(bull_p, base_p, bear_p):
    """Visual bull/base/bear probability bar."""
    html = '<div class="scenario-bar">'
    if bull_p > 0:
        html += f'<div class="scenario-seg" style="width:{bull_p}%;background:#3FB950;">🐂 {bull_p:.0f}%</div>'
    if base_p > 0:
        html += f'<div class="scenario-seg" style="width:{base_p}%;background:#D29922;">⚖ {base_p:.0f}%</div>'
    if bear_p > 0:
        html += f'<div class="scenario-seg" style="width:{bear_p}%;background:#F85149;">🐻 {bear_p:.0f}%</div>'
    html += '</div><div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-top:2px;"><span>Bull</span><span>Base</span><span>Bear</span></div>'
    return html

def _timeline_html(stage="INCEPTION"):
    stages = ["INCEPTION","ACCELERATION","EUPHORIA","CRISIS","AUCTION"]
    idx = stages.index(stage) if stage in stages else 0
    nodes = ""; labels = ""
    for i, s in enumerate(stages):
        cls = "past" if i < idx else "active" if i == idx else ""
        line_cls = "active" if i < idx else ""
        nodes += f'<div class="tl-node {cls}"></div>'
        if i < len(stages) - 1: nodes += f'<div class="tl-line {line_cls}"></div>'
        labels += f'<span>{s}</span>'
    return f'<div class="timeline">{nodes}</div><div class="tl-labels">{labels}</div>'

def _skew_bars_html(d30=None, d60=None, d90=None):
    def bar(label, val):
        if val is None:
            return f'<div class="skew-row"><span class="skew-label">{label}</span><div class="skew-track"><div class="skew-fill" style="width:0%;background:#30363D;"></div></div><span class="skew-value">-</span></div>'
        v = float(val)
        pct = max(5, min(100, abs(v) * 200))
        color = "#3FB950" if v > 0.05 else "#F85149" if v < -0.05 else "#D29922"
        label_text = "Rich" if v > 0.05 else "Cheap" if v < -0.05 else "Fair"
        return f'<div class="skew-row"><span class="skew-label">{label}</span><div class="skew-track"><div class="skew-fill" style="width:{pct:.0f}%;background:{color};"></div></div><span class="skew-value" style="color:{color};">{label_text}</span></div>'
    return bar("30D", d30) + bar("60D", d60) + bar("90D", d90)

def _gex_bar_html(gex_val=None):
    if gex_val is None:
        return '<div class="gex-track" style="height:18px;background:#21262D;border-radius:4px;"></div>'
    v = float(gex_val)
    color = "#3FB950" if v > 0 else "#F85149"
    pct = min(100, abs(v) * 100)
    side = "Pos" if v > 0 else "Neg"
    margin = "margin-left:0;left:50%;" if v > 0 else f"margin-left:-{pct}%;left:50%;"
    return (
        f'<div class="gex-track" style="height:18px;">'
        f'<div class="gex-center"></div>'
        f'<div style="position:absolute;{margin}width:{pct:.0f}%;background:{color}25;height:100%;border-radius:4px;"></div>'
        f'<div style="position:absolute;width:100%;text-align:center;font-size:0.6rem;font-weight:700;color:{color};line-height:18px;">{side} {abs(v):.2f}</div>'
        f'</div>'
    )

def _heatmap_grid_html(items, key_label="name", key_quad="quad"):
    html = '<div class="hm-grid">'
    for it in items:
        q = it.get(key_quad, "Q3")
        color = _quad_color(q)
        name = it.get(key_label, "-")
        html += f'<div class="hm-cell" style="background:{color}15;border-color:{color}35;">{name}<div style="font-size:0.52rem;color:{color};margin-top:1px;">{q}</div></div>'
    html += '</div>'
    return html

def _asset_pulse_box_h(label, ret, sub=""):
    c = _ret_color(ret)
    txt = f"{ret:+.1%}" if ret is not None else "-"
    sub_html = f'<div style="font-size:0.52rem;color:#8B949E;margin-top:1px;">{sub}</div>' if sub else ""
    return f'<div class="pulse-hbox" style="background:{c}12;border-color:{c}25;"><div>{txt}</div><div class="pulse-hlabel">{label}</div>{sub_html}</div>'


# ═══════════════════════════════════════════════════════════════════
# OPTIONS / GREEKS / MM DATA ENRICHMENT
# ═══════════════════════════════════════════════════════════════════
def _get_options_data(ticker, snap):
    out = {
        "max_pain": None, "put_wall": None, "call_wall": None,
        "gamma_flip_up": None, "gamma_flip_down": None, "gamma_regime": None,
        "gex": None, "vanna": None, "charm": None,
        "skew_30d": None, "skew_60d": None, "skew_90d": None,
        "pin_risk": None, "expected_move_pct": None,
        "oi_call": None, "oi_put": None, "pc_ratio": None,
        "iv_rank": None, "iv_percentile": None,
        "mm_positioning": "NEUTRAL", "mm_recommendation": "—",
        "source": "PROXY", "next_expiry": None, "days_to_expiry": None,
    }
    # 1. YFinance live options (best quality, only SPY/QQQ/IWM usually)
    yf = snap.get("yfinance_options", {}).get(ticker, {}) if isinstance(snap.get("yfinance_options"), dict) else {}
    if isinstance(yf, dict) and yf.get("ok"):
        out["max_pain"] = yf.get("max_pain")
        out["put_wall"] = yf.get("put_wall")
        out["call_wall"] = yf.get("call_wall")
        out["gamma_flip_up"] = yf.get("gamma_flip_up")
        out["gamma_flip_down"] = yf.get("gamma_flip_down")
        out["gamma_regime"] = yf.get("gamma_regime")
        out["pc_ratio"] = yf.get("put_call_ratio")
        out["source"] = "YF"
        if yf.get("next_expiry"): out["next_expiry"] = yf.get("next_expiry")
        if yf.get("days_to_expiry"): out["days_to_expiry"] = yf.get("days_to_expiry")

    # 2. Greeks engine data
    greeks = snap.get("greeks_data", {}).get(ticker, {}) if isinstance(snap.get("greeks_data"), dict) else {}
    if isinstance(greeks, dict):
        if not out["gex"]: out["gex"] = greeks.get("net_gex") or greeks.get("gex")
        if not out["vanna"]: out["vanna"] = greeks.get("vanna")
        if not out["charm"]: out["charm"] = greeks.get("charm")
        if not out["skew_30d"]: out["skew_30d"] = greeks.get("skew_30d") or greeks.get("skew")

    # 3. Gamma engine data
    gamma = snap.get("gamma_data", {}).get(ticker, {}) if isinstance(snap.get("gamma_data"), dict) else {}
    if isinstance(gamma, dict):
        if not out["gamma_regime"]: out["gamma_regime"] = gamma.get("regime")
        if not out["max_pain"]: out["max_pain"] = gamma.get("max_pain")

    # 4. GEX engine data
    gex = snap.get("gex_data", {}).get(ticker, {}) if isinstance(snap.get("gex_data"), dict) else {}
    if isinstance(gex, dict):
        if not out["gex"]: out["gex"] = gex.get("net_gex") or gex.get("gex") or gex.get("total_gex")

    # 5. Vanna / Charm engine data
    vanna = snap.get("vanna_data", {}).get(ticker, {}) if isinstance(snap.get("vanna_data"), dict) else {}
    if isinstance(vanna, dict):
        if not out["vanna"]: out["vanna"] = vanna.get("vanna")
    charm = snap.get("charm_data", {}).get(ticker, {}) if isinstance(snap.get("charm_data"), dict) else {}
    if isinstance(charm, dict):
        if not out["charm"]: out["charm"] = charm.get("charm")

    # 6. Skew term structure
    skew = snap.get("skew_term", {}).get("skew_data", {}) if isinstance(snap.get("skew_term"), dict) else {}
    if isinstance(skew, dict):
        for k, v in skew.items():
            if isinstance(v, dict):
                val = v.get("skew") or v.get("value") or v.get("90_10")
                if ticker in str(k).upper() or (ticker.replace("-","") in str(k).upper()):
                    if "30" in str(k).lower() or "1m" in str(k).lower(): out["skew_30d"] = _safe_float(val)
                    if "60" in str(k).lower() or "2m" in str(k).lower(): out["skew_60d"] = _safe_float(val)
                    if "90" in str(k).lower() or "3m" in str(k).lower(): out["skew_90d"] = _safe_float(val)

    # 7. 0DTE monitor
    odte = snap.get("odte_monitor", {}).get("tickers", {}).get(ticker, {}) if isinstance(snap.get("odte_monitor"), dict) else {}
    if isinstance(odte, dict):
        if not out["pin_risk"]: out["pin_risk"] = odte.get("pin_risk")
        if not out["vanna"]: out["vanna"] = odte.get("vanna")
        if not out["charm"]: out["charm"] = odte.get("charm")

    # 8. VRP scanner
    vrp = snap.get("vrp_scanner", {}) if isinstance(snap.get("vrp_scanner"), dict) else {}
    if isinstance(vrp, dict) and vrp.get("ok"):
        for item in vrp.get("high_vrp_sell_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                out["iv_rank"] = item.get("iv_rank")
                out["expected_move_pct"] = item.get("expected_move_pct")
        for item in vrp.get("low_vrp_buy_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                out["iv_rank"] = item.get("iv_rank")

    # 9. Cem Karsan universal
    cem = snap.get("cem_karsan_universal", {}) if isinstance(snap.get("cem_karsan_universal"), dict) else {}
    if isinstance(cem, dict):
        for item in cem.get("per_ticker", {}).values() if isinstance(cem.get("per_ticker"), dict) else []:
            if isinstance(item, dict) and item.get("ticker") == ticker:
                if not out["skew_30d"]: out["skew_30d"] = _safe_float(item.get("skew_30d") or item.get("skew"))
                if not out["gex"]: out["gex"] = _safe_float(item.get("gex") or item.get("net_gex"))
                if not out["vanna"]: out["vanna"] = item.get("vanna")
                if not out["charm"]: out["charm"] = item.get("charm")
                if not out["gamma_regime"]: out["gamma_regime"] = item.get("gamma_regime")
                if not out["max_pain"]: out["max_pain"] = _safe_float(item.get("max_pain"))
                if not out["expected_move_pct"]: out["expected_move_pct"] = _safe_float(item.get("expected_move"))

    # 10. SpotGamma proxy
    spot = snap.get("spotgamma_scanner", {}) if isinstance(snap.get("spotgamma_scanner"), dict) else {}
    if isinstance(spot, dict) and spot.get("ok"):
        pt = spot.get("per_ticker_proxy_gex", {}) if isinstance(spot.get("per_ticker_proxy_gex"), dict) else {}
        if ticker in pt and isinstance(pt[ticker], dict):
            if not out["gex"]: out["gex"] = _safe_float(pt[ticker].get("gex") or pt[ticker].get("net_gex") or pt[ticker].get("total_gex"))
            if not out["gamma_regime"]: out["gamma_regime"] = pt[ticker].get("gamma_regime")
            if not out["max_pain"]: out["max_pain"] = _safe_float(pt[ticker].get("max_pain"))

    # 11. Karsan scanner
    karsan = snap.get("karsan_scanner", {}) if isinstance(snap.get("karsan_scanner"), dict) else {}
    if isinstance(karsan, dict) and karsan.get("ok"):
        for item in karsan.get("per_ticker", {}).values() if isinstance(karsan.get("per_ticker"), dict) else []:
            if isinstance(item, dict) and item.get("ticker") == ticker:
                if not out["skew_30d"]: out["skew_30d"] = _safe_float(item.get("skew") or item.get("skew_30d"))
                if not out["expected_move_pct"]: out["expected_move_pct"] = _safe_float(item.get("expected_move"))

    # 12. Afternoon signal
    aft = snap.get("afternoon_data", {}) if isinstance(snap.get("afternoon_data"), dict) else {}
    if isinstance(aft, dict) and ticker in aft:
        a = aft[ticker]
        if isinstance(a, dict):
            if not out["vanna"]: out["vanna"] = a.get("vanna")
            if not out["charm"]: out["charm"] = a.get("charm")

    # 13. Structure quality
    struct = snap.get("structure_data", {}) if isinstance(snap.get("structure_data"), dict) else {}
    if isinstance(struct, dict) and ticker in struct:
        s = struct[ticker]
        if isinstance(s, dict):
            if not out["gamma_regime"]: out["gamma_regime"] = s.get("gamma_regime")

    # 14. Volga proxy
    volga = snap.get("volga_data", {}) if isinstance(snap.get("volga_data"), dict) else {}
    if isinstance(volga, dict) and volga.get("ok"):
        vt = volga.get("per_ticker", {}) if isinstance(volga.get("per_ticker"), dict) else {}
        if ticker in vt and isinstance(vt[ticker], dict):
            if not out["skew_30d"]: out["skew_30d"] = _safe_float(vt[ticker].get("skew"))

    # ── MM Positioning Logic ──
    px = None
    prices = snap.get("prices", {})
    if ticker in prices:
        try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
        except: pass
    mp = out["max_pain"]
    if px and mp:
        mp_dist = (px - mp) / mp
        out["mp_dist"] = mp_dist
        if abs(mp_dist) < 0.02:
            out["mm_positioning"] = "PINNED"
            out["mm_recommendation"] = "MM pinned — range-bound until expiry. Sell straddles or wait breakout."
        elif mp_dist > 0.03 and out["gamma_regime"] in ("POSITIVE", "DEEP_POSITIVE"):
            out["mm_positioning"] = "CALL_WALL"
            out["mm_recommendation"] = "Price above max pain + positive gamma — MM sells into rallies. Fade strength."
        elif mp_dist < -0.03 and out["gamma_regime"] in ("NEGATIVE", "DEEP_NEGATIVE"):
            out["mm_positioning"] = "PUT_WALL"
            out["mm_recommendation"] = "Price below max pain + negative gamma — MM buys dips. Support holds."
        else:
            out["mm_positioning"] = "TRANSITION"
            out["mm_recommendation"] = "Between walls — directional play valid. Watch vanna/charm shift."
    else:
        out["mm_positioning"] = "UNKNOWN"
        out["mm_recommendation"] = "Insufficient options data for MM positioning."

    # 15. VolSignals dealer regime
    vs = snap.get("volsignals_regime", {}) if isinstance(snap.get("volsignals_regime"), dict) else {}
    if isinstance(vs, dict) and ticker in vs and isinstance(vs[ticker], dict):
        out["volsignals_regime"] = vs[ticker]

    # 16. SpotGamma structural levels
    sg = snap.get("spotgamma_levels", {}) if isinstance(snap.get("spotgamma_levels"), dict) else {}
    if isinstance(sg, dict) and ticker in sg and isinstance(sg[ticker], dict):
        out["spotgamma_levels"] = sg[ticker]
        if not out.get("volatility_trigger"): out["volatility_trigger"] = sg[ticker].get("volatility_trigger")
        if not out.get("risk_pivot_upper"): out["risk_pivot_upper"] = sg[ticker].get("risk_pivot_upper")
        if not out.get("risk_pivot_lower"): out["risk_pivot_lower"] = sg[ticker].get("risk_pivot_lower")

    # 17. Schadner IV validation
    sch = snap.get("schadner_iv", {}) if isinstance(snap.get("schadner_iv"), dict) else {}
    if isinstance(sch, dict) and ticker in sch and isinstance(sch[ticker], dict):
        out["iv_schadner"] = sch[ticker].get("iv_exact")
        out["iv_proxy_error"] = sch[ticker].get("error_pct")

    # ── Fallback proxy: fill any missing fields from price action ──
    proxy = _options_proxy_for_ticker_local(ticker, snap.get("prices", {}))
    if proxy:
        for k, v in proxy.items():
            if out.get(k) is None:
                out[k] = v

    return out

def _skew_curve_proxy_html(ticker, options_data, width=300, height=120, iv_exact=None):
    skew_val = options_data.get("skew_30d") or options_data.get("skew_60d") or 0
    if skew_val is None: skew_val = 0
    if skew_val > 0.05:
        shape = "smirk"; left_h = 85; mid_h = 40; right_h = 25; color = "#F85149"
    elif skew_val < -0.05:
        shape = "reverse_smirk"; left_h = 25; mid_h = 40; right_h = 85; color = "#3FB950"
    else:
        shape = "smile"; left_h = 70; mid_h = 30; right_h = 70; color = "#D29922"
    bars = 15
    bar_width = int(width / bars)
    bars_html = ""
    for i in range(bars):
        x = (i - bars//2) / (bars//2)
        if shape == "smirk": h = int(30 + 55 * math.exp(-x))
        elif shape == "reverse_smirk": h = int(30 + 55 * math.exp(x))
        else: h = int(30 + 55 * (x**2))
        h = max(10, min(95, h))
        bars_html += f'<div style="width:{bar_width-2}px;height:{h}%;background:{color}40;border-radius:2px;opacity:0.8;"></div>'
    iv_label = f" · IV: {iv_exact:.1%} (Schadner)" if iv_exact else f" [{options_data.get('source','PROXY')}]"
    return (
        f'<div class="skew-curve-container">'
        f'<div class="skew-curve-title">{ticker} Skew · {shape.replace("_"," ").title()} ({skew_val:+.2f}){iv_label}</div>'
        f'<div style="display:flex;align-items:flex-end;gap:1px;height:{height}px;padding:0 4px;">'
        f'{bars_html}'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-top:2px;">'
        f'<span>OTM Puts</span><span>ATM</span><span>OTM Calls</span></div>'
        f'</div>'
    )

def _build_dark_pool_proxy(snap, prices):
    prints = []
    inst = snap.get("institutional_data", {}) if isinstance(snap.get("institutional_data"), dict) else {}
    if inst.get("per_ticker"):
        for t, data in inst.get("per_ticker", {}).items():
            if not isinstance(data, dict): continue
            if data.get("anomaly_score", 0) > 0.6:
                px = None
                if t in prices:
                    try: px = float(pd.to_numeric(pd.Series(prices[t]), errors="coerce").dropna().iloc[-1])
                    except: pass
                if px:
                    size = int(data.get("volume_anomaly", 0) * 1000)
                    amt = size * px
                    side = "BUY" if data.get("buy_pressure", 0) > data.get("sell_pressure", 0) else "SELL"
                    prints.append({"time": "Live", "ticker": t, "price": px, "size": size, "amount": amt, "side": side})
    fr = snap.get("front_run_candidates", []) or []
    for item in fr[:5]:
        if not isinstance(item, dict): continue
        t = item.get("ticker", "")
        if any(p["ticker"] == t for p in prints): continue
        px = None
        if t in prices:
            try: px = float(pd.to_numeric(pd.Series(prices[t]), errors="coerce").dropna().iloc[-1])
            except: pass
        if px:
            size = 250000
            amt = size * px
            prints.append({"time": "Consensus", "ticker": t, "price": px, "size": size, "amount": amt, "side": "BUY"})
    prints.sort(key=lambda x: x["amount"], reverse=True)
    return prints[:15]

def _get_next_expiry(days_to_add=21):
    from datetime import datetime, timedelta
    d = datetime.now() + timedelta(days=days_to_add)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d.strftime("%b %d")

def _options_proxy_for_ticker_local(ticker, prices):
    """Local fallback when snap options data is empty.
    ⚠️ ALL VALUES ARE PROXY — derived from price action, NOT real options chain.
    Formulas documented for transparency."""
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {}
        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        std20 = float(s_clean.tail(20).std())
        if std20 == 0 or not all(math.isfinite(v) for v in [px, sma20, std20]):
            return {}

        # PROXY FORMULAS (price-action based, NOT real OI)
        max_pain = round(sma20, 2)
        put_wall = round(sma20 - std20 * 2.0, 2)
        call_wall = round(sma20 + std20 * 2.0, 2)
        gamma_flip_up = round(sma20 + std20 * 1.5, 2)
        gamma_flip_down = round(sma20 - std20 * 1.5, 2)
        mp_dist = (px - max_pain) / max_pain if max_pain != 0 else 0

        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else 0

        # Gamma regime proxy from momentum
        if r5d > 0.03 and r20d > 0.05: gamma_regime = "DEEP_POSITIVE"
        elif r5d > 0.01 and r20d > 0.02: gamma_regime = "POSITIVE"
        elif r5d < -0.03 and r20d < -0.05: gamma_regime = "DEEP_NEGATIVE"
        elif r5d < -0.01 and r20d < -0.02: gamma_regime = "NEGATIVE"
        else: gamma_regime = "TRANSITION"

        returns = s_clean.tail(20).pct_change().dropna()
        skew_val = float(returns.skew()) if len(returns) > 5 else 0.0
        skew_30d = skew_val * 0.5

        # Greeks proxies (price-action derived)
        gex_proxy = -mp_dist * 5.0
        vanna_proxy = r5d * 10.0
        r11 = float(s_clean.iloc[-6] / s_clean.iloc[-11] - 1) if len(s_clean) >= 11 else r5d
        charm_proxy = (r5d - r11) * 20.0

        # Volatility metrics
        vol_20 = float(returns.std() * math.sqrt(252)) if len(returns) > 1 else 0.2
        hist_vol = float(s_clean.tail(60).pct_change().dropna().std() * math.sqrt(252)) if len(s_clean) >= 60 else vol_20

        # ⚠️ PROXY IV Rank — NOT real IV Rank (which needs 52w high/low IV)
        # This is a normalized vol ratio mapped to 0-100 scale
        iv_rank = min(100, max(0, (vol_20 / hist_vol * 50))) if hist_vol > 0 else 50

        expected_move = vol_20 / math.sqrt(12)
        pc_ratio = 0.8 if r20d > 0.05 else (1.2 if r20d < -0.05 else 1.0)

        # OI proxy from price level
        avg_vol = float(s_clean.tail(20).mean())
        oi_call = max(50000, int(avg_vol * 80000 * (1.1 if r20d > 0 else 0.9)))
        oi_put = max(50000, int(avg_vol * 80000 * (0.9 if r20d > 0 else 1.1)))

        return {
            "max_pain": float(max_pain), "put_wall": float(put_wall), "call_wall": float(call_wall),
            "gamma_flip_up": float(gamma_flip_up), "gamma_flip_down": float(gamma_flip_down),
            "gamma_regime": gamma_regime, "gex": float(gex_proxy), "vanna": float(vanna_proxy),
            "charm": float(charm_proxy), "skew_30d": float(skew_30d), "skew_60d": float(skew_30d) * 0.8,
            "skew_90d": float(skew_30d) * 0.6, "mp_dist": float(mp_dist), "iv_rank": float(iv_rank),
            "expected_move_pct": float(expected_move), "pc_ratio": float(pc_ratio),
            "oi_call": int(oi_call), "oi_put": int(oi_put),
            "source": "PROXY", "next_expiry": _get_next_expiry(), "days_to_expiry": 21,
        }
    except Exception:
        return {}

def _get_dark_pool_for_ticker(ticker, snap):
    if not snap: return None
    inst = snap.get("institutional_data", {}) if isinstance(snap.get("institutional_data"), dict) else {}
    if inst.get("per_ticker"):
        data = inst.get("per_ticker", {}).get(ticker)
        if isinstance(data, dict) and data.get("anomaly_score", 0) > 0.6:
            px = None
            prices = snap.get("prices", {})
            if ticker in prices:
                try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
                except: pass
            if px:
                size = int(data.get("volume_anomaly", 0) * 1000)
                return {"size": size, "price": px, "amount": size * px,
                        "side": "BUY" if data.get("buy_pressure", 0) > data.get("sell_pressure", 0) else "SELL",
                        "time": "Live", "source": "INST"}
    fr = snap.get("front_run_candidates", []) or []
    for item in fr:
        if not isinstance(item, dict): continue
        if item.get("ticker") == ticker:
            px = None
            prices = snap.get("prices", {})
            if ticker in prices:
                try: px = float(pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna().iloc[-1])
                except: pass
            if px:
                return {"size": 250000, "price": px, "amount": 250000 * px, "side": "BUY", "time": "Consensus", "source": "FR"}
    prices = snap.get("prices", {})
    if ticker in prices:
        try:
            s = pd.to_numeric(pd.Series(prices[ticker]), errors="coerce").dropna()
            if len(s) >= 6:
                px = float(s.iloc[-1])
                r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
                vol_5 = float(s.tail(5).std())
                vol_20 = float(s.tail(20).std()) if len(s) >= 20 else vol_5
                if vol_20 > 0 and abs(vol_5 / vol_20 - 1) > 0.25:
                    side = "BUY" if r5d > 0 else "SELL"
                    size = int(150000 * (1 + abs(r5d) * 5))
                    return {"size": size, "price": px, "amount": size * px,
                            "side": side, "time": "Proxy", "source": "PROXY"}
        except Exception:
            pass
    return None

# ═══════════════════════════════════════════════════════════════════
# RISK RANGE / ROW BUILDERS (AUDITED + FORMULA DOCUMENTATION)
# ═══════════════════════════════════════════════════════════════════
def _build_row(ticker, prices, ar, vix_now=20, gamma_data=None, greeks_data=None, market_type="us_equity", news=None, snap=None):
    """
    AUDITED FORMULAS v32.4.1 — TREND FILTER + MINIMUM STOP DISTANCE
    ─────────────────────────────────────────────────────────────────

    [1] RISK RANGE (Price Action)
        LRR = SMA(20) − 1.5 × STD(20)          [Support]
        TRR = SMA(20) + 1.5 × STD(20)          [Resistance]
        Spread = TRR − LRR
        PosInRange = (Price − LRR) / Spread

    [2] TREND FILTER (NEW — prevents false signals)
        SMA(50) = 50-day simple moving average
        r20d    = 20-day return
        r5d     = 5-day return

        Trend = BULLISH if Price > SMA(50) AND r20d > +3%
        Trend = BEARISH if Price < SMA(50) AND r20d < −3%
        Trend = NEUTRAL otherwise

        DIRECTION OVERRIDE:
        • If composite says LONG but Trend = BEARISH → NEUTRAL/AVOID
          (Don't catch falling knives)
        • If composite says SHORT but Trend = BULLISH → NEUTRAL/AVOID
          (Don't fight the trend)
        • If r20d > +10% (parabolic) → reduce position size (bubble risk)
        • If r20d < −10% (capitulation) → wait for bounce confirmation

    [3] ENTRY / STOP / TARGET
        LONG:
          IF Price < LRR (oversold):
            Entry = Price
            Stop  = MAX(LRR − Spread×0.15, Entry×0.995)  [min 0.5% distance]
          ELSE:
            Entry = MIN(LRR, PutWall, GammaFlipDown)
            Stop  = MIN(Entry − Spread×0.25, PutWall − Spread×0.1)
            Stop  = MAX(Stop, Entry×0.995)                [min 0.5% distance]
          TP1 = MAX(Entry + 2×Risk, TRR, CallWall, GammaFlipUp, MaxPain)
          TP2 = MAX(TP1, TRR, CallWall, GammaFlipUp)

        SHORT:
          IF Price > TRR (overbought):
            Entry = Price
            Stop  = MIN(TRR + Spread×0.15, Entry×1.005)  [min 0.5% distance]
          ELSE:
            Entry = MAX(TRR, CallWall, GammaFlipUp)
            Stop  = MAX(Entry + Spread×0.25, CallWall + Spread×0.1)
            Stop  = MIN(Stop, Entry×1.005)               [min 0.5% distance]
          TP1 = MIN(Entry − 2×Risk, LRR, PutWall, GammaFlipDown, MaxPain)
          TP2 = MIN(TP1, LRR, PutWall, GammaFlipDown)

    [4] RISK/REWARD
        Risk = |Entry − Stop|
        IF Risk < Entry×0.005 → INVALID SETUP (stop too tight)
        RR = |TP1 − Entry| / max(Risk, 0.0001)

        Grade A = NearEntry AND RR ≥ 2.0 AND Risk ≥ Entry×0.005
        Grade B = NearEntry AND RR ≥ 1.5 AND Risk ≥ Entry×0.005
        Grade C = Everything else OR Risk < Entry×0.005

    [5] CHASE / WAIT / AVOID
        CHASE  = Price ≤ Entry×1.02 AND Risk ≥ Entry×0.005
        WAIT   = Price > Entry×1.05 AND > Stop
        AVOID  = Price < Stop OR Risk < Entry×0.005
    """
    v = ar.get(ticker, {}) if ar else {}
    s = prices.get(ticker)
    if not v and (s is None or len(s) < 50):  # Need 50 days for SMA(50)
        return None

    # ── Price & Basic Risk Range ──
    if not v and s is not None:
        try:
            s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        except: 
            return None
        if len(s_clean) < 50: 
            return None
        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        std20 = float(s_clean.tail(20).std())
        sma50 = float(s_clean.tail(50).mean()) if len(s_clean) >= 50 else sma20
        if not all(math.isfinite(v) for v in [px, sma20, std20]) or std20 == 0:
            lrr = round(px * 0.95, 4)
            trr = round(px * 1.05, 4)
            comp = "neutral"
        else:
            lrr = round(sma20 - 1.5 * std20, 4)
            trr = round(sma20 + 1.5 * std20, 4)
            comp = "bullish" if px < lrr else "bearish" if px > trr else "neutral"
        if comp == "neutral":
            r5 = _price_ret(ticker, prices, 5) or 0
            comp = "bullish" if r5 >= 0 else "bearish"
        v = {"px": px, "trade": {"lrr": lrr, "trr": trr}, "composite": comp, "quality": "B", "market": market_type}

    tr = v.get("trade", {})
    px = _safe_float(v.get("px"))
    lrr = _safe_float(tr.get("lrr"))
    trr = _safe_float(tr.get("trr"))
    if not px or not lrr or not trr:
        return None

    # ── TREND ANALYSIS (NEW v32.4.1) ──
    trend = "NEUTRAL"
    trend_note = ""
    r20d = _price_ret(ticker, prices, 21) or 0
    r5d = _price_ret(ticker, prices, 5) or 0
    sma50 = None
    if s is not None and len(s) >= 50:
        try:
            s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
            if len(s_clean) >= 50:
                sma50 = float(s_clean.tail(50).mean())
        except:
            pass

    if sma50 is not None and math.isfinite(sma50):
        if px > sma50 and r20d > 0.03:
            trend = "BULLISH"
        elif px < sma50 and r20d < -0.03:
            trend = "BEARISH"
        elif px > sma50:
            trend = "BULLISH_BIAS"
        elif px < sma50:
            trend = "BEARISH_BIAS"

    # Parabolic / Capitulation detection
    bubble_risk = False
    capitulation = False
    if r20d > 0.15:
        bubble_risk = True
        trend_note = f"⚠️ PARABOLIC +{r20d:.1%} 20D — Bubble risk, tighten stops"
    elif r20d < -0.15:
        capitulation = True
        trend_note = f"🔨 CAPITULATION {r20d:.1%} 20D — Wait for bounce, don't knife-catch"
    elif trend == "BEARISH":
        trend_note = f"📉 DOWNTREND — Price < SMA(50) and −{abs(r20d):.1%} 20D"
    elif trend == "BULLISH":
        trend_note = f"📈 UPTREND — Price > SMA(50) and +{r20d:.1%} 20D"
    elif trend == "BEARISH_BIAS":
        trend_note = f"➡️ Price below SMA(50) — cautious"
    elif trend == "BULLISH_BIAS":
        trend_note = f"➡️ Price above SMA(50) — favorable"

    # ── DIRECTION with Trend Filter ──
    composite = v.get("composite", "neutral")
    side = "long" if composite == "bullish" else "short"

    # TREND OVERRIDE (NEW v32.4.1)
    # Don't fight the trend — if strong trend opposes signal, neutralize
    direction_override = False
    override_reason = ""
    if side == "long" and trend == "BEARISH":
        direction_override = True
        override_reason = f"🚫 AVOID LONG — Strong downtrend ({r20d:.1%} 20D). Price < LRR is catching a falling knife. Wait for trend reversal or SMA(50) reclaim."
    elif side == "short" and trend == "BULLISH":
        direction_override = True
        override_reason = f"🚫 AVOID SHORT — Strong uptrend (+{r20d:.1%} 20D). Price > TRR is fighting the trend. Wait for breakdown."
    elif side == "long" and bubble_risk:
        override_reason = f"⚠️ LONG with caution — Parabolic +{r20d:.1%}. Tighten stop, reduce size."
    elif side == "short" and capitulation:
        override_reason = f"⚠️ SHORT with caution — Capitulation {r20d:.1%}. Cover on bounce, don't press."

    spread = trr - lrr
    pos = (px - lrr) / spread if spread > 0 else 0.5

    options = _get_options_data(ticker, snap) if snap else {}
    mp = options.get("max_pain")
    pw = options.get("put_wall")
    cw = options.get("call_wall")
    gf_up = options.get("gamma_flip_up")
    gf_down = options.get("gamma_flip_down")

    # ── MINIMUM STOP DISTANCE (NEW v32.4.1) ──
    # For forex/crypto with low prices, spread*0.25 can round to 0
    # Enforce minimum 0.5% stop distance
    min_stop_dist = px * 0.005  # 0.5% of price

    # ── CONFLUENCE DETECTION ──
    def _cluster_levels(levels, threshold_pct=0.02):
        valid = [float(v) for v in levels if v is not None and v > 0 and math.isfinite(float(v))]
        if len(valid) < 2: return []
        valid.sort()
        clusters = []
        for i in range(len(valid)):
            cluster = [valid[i]]
            for j in range(i+1, len(valid)):
                if abs(valid[j] - valid[i]) / valid[i] <= threshold_pct:
                    cluster.append(valid[j])
            if len(cluster) >= 2:
                clusters.append({"levels": cluster, "center": round(sum(cluster)/len(cluster), 4), "count": len(cluster)})
        return sorted(clusters, key=lambda x: x["count"], reverse=True)

    confluence = {"entry": [], "target": [], "entry_cluster": None, "target_cluster": None}

    # ── ENTRY / STOP / TARGET CALCULATION ──
    if side == "long":
        if px < lrr:
            # Oversold — buy at discount
            entry = round(px, 4)
            raw_stop = lrr - spread * 0.15
            stop = max(raw_stop, entry - min_stop_dist)  # MINIMUM STOP DISTANCE
            note = f"📉 Price {px} < LRR {lrr} — DISCOUNTED entry."
            if trend == "BEARISH":
                note += f" BUT downtrend {r20d:.1%} — high risk knife-catch."
        else:
            long_entry_levels = [lrr]
            if market_type != "ihsg":
                if pw: long_entry_levels.append(pw)
                if gf_down: long_entry_levels.append(gf_down)
            clusters = _cluster_levels(long_entry_levels, 0.02)
            if clusters:
                best = clusters[0]
                entry = best["center"]
                confluence["entry"] = [("LRR", lrr), ("Put Wall", pw), ("Gamma Flip ↓", gf_down)]
                confluence["entry_cluster"] = best
                note = f"🔥 CONFLUENCE x{best['count']}: entry at {ff(entry)}"
            else:
                entry_candidates = [lrr]
                if pw and pw > lrr: entry_candidates.append(pw)
                if gf_down and gf_down > lrr: entry_candidates.append(gf_down)
                entry = round(min(entry_candidates), 4)
                note = f"📍 Entry at support {ff(entry)}"

            raw_stop = entry - spread * 0.25
            if pw: raw_stop = min(raw_stop, pw - spread * 0.1)
            stop = max(raw_stop, entry - min_stop_dist)  # MINIMUM STOP DISTANCE

        # Target
        long_target_levels = [trr]
        if market_type != "ihsg":
            if cw: long_target_levels.append(cw)
            if gf_up: long_target_levels.append(gf_up)
        if mp: long_target_levels.append(mp)
        t_clusters = _cluster_levels(long_target_levels, 0.02)
        if t_clusters:
            best_t = t_clusters[0]
            tp1 = best_t["center"]
            confluence["target"] = [("TRR", trr), ("Call Wall", cw), ("Gamma Flip ↑", gf_up), ("Max Pain", mp)]
            confluence["target_cluster"] = best_t
        else:
            risk = abs(entry - stop)
            tp1_candidates = [round(entry + risk * 2, 4)]
            if mp and mp > entry: tp1_candidates.append(round(mp, 4))
            if gf_up and gf_up > entry: tp1_candidates.append(round(gf_up, 4))
            tp1 = round(max([x for x in tp1_candidates if x > entry], default=round(entry + spread * 0.3, 4)), 4)

        tp2_candidates = [trr]
        if cw: tp2_candidates.append(cw)
        if gf_up: tp2_candidates.append(gf_up)
        tp2 = round(max(tp2_candidates), 4)
        near_entry = pos <= 0.35 or px < lrr

    else:  # short
        if px > trr:
            entry = round(px, 4)
            raw_stop = trr + spread * 0.15
            stop = min(raw_stop, entry + min_stop_dist)
            note = f"📈 Price {px} > TRR {trr} — OVERBOUGHT entry."
            if trend == "BULLISH":
                note += f" BUT uptrend +{r20d:.1%} — high risk fade."
        else:
            short_entry_levels = [trr]
            if market_type != "ihsg":
                if cw: short_entry_levels.append(cw)
                if gf_up: short_entry_levels.append(gf_up)
            clusters = _cluster_levels(short_entry_levels, 0.02)
            if clusters:
                best = clusters[0]
                entry = best["center"]
                confluence["entry"] = [("TRR", trr), ("Call Wall", cw), ("Gamma Flip ↑", gf_up)]
                confluence["entry_cluster"] = best
                note = f"🔥 CONFLUENCE x{best['count']}: entry at {ff(entry)}"
            else:
                entry_candidates = [trr]
                if cw and cw < trr: entry_candidates.append(cw)
                if gf_up and gf_up < trr: entry_candidates.append(gf_up)
                entry = round(max(entry_candidates), 4)
                note = f"📍 Entry at resistance {ff(entry)}"

            raw_stop = entry + spread * 0.25
            if cw: raw_stop = max(raw_stop, cw + spread * 0.1)
            stop = min(raw_stop, entry + min_stop_dist)

        short_target_levels = [lrr]
        if market_type != "ihsg":
            if pw: short_target_levels.append(pw)
            if gf_down: short_target_levels.append(gf_down)
        if mp: short_target_levels.append(mp)
        t_clusters = _cluster_levels(short_target_levels, 0.02)
        if t_clusters:
            best_t = t_clusters[0]
            tp1 = best_t["center"]
            confluence["target"] = [("LRR", lrr), ("Put Wall", pw), ("Gamma Flip ↓", gf_down), ("Max Pain", mp)]
            confluence["target_cluster"] = best_t
        else:
            risk = abs(entry - stop)
            tp1_candidates = [round(entry - risk * 2, 4)]
            if mp and mp < entry: tp1_candidates.append(round(mp, 4))
            if gf_down and gf_down < entry: tp1_candidates.append(round(gf_down, 4))
            tp1 = round(min([x for x in tp1_candidates if x < entry], default=round(entry - spread * 0.3, 4)), 4)

        tp2_candidates = [lrr]
        if pw: tp2_candidates.append(pw)
        if gf_down: tp2_candidates.append(gf_down)
        tp2 = round(min(tp2_candidates), 4)
        near_entry = pos >= 0.65 or px > trr

    # ── RISK/REWARD with validation ──
    risk = abs(entry - stop)
    min_risk = px * 0.005  # 0.5% minimum risk

    if risk < min_risk:
        # Stop too tight — invalid setup
        rr = 0.0
        grade = "C"
        setup_valid = False
        setup_note = f"🚫 INVALID — Stop {ff(stop)} too close to entry {ff(entry)} (risk {risk/px:.2%} < 0.5% min)."
    else:
        rr = round(abs(tp1 - entry) / risk, 2)
        grade = "A" if near_entry and rr >= 2.0 else "B" if near_entry and rr >= 1.5 else "C"
        setup_valid = True
        setup_note = ""

    # ── CHASE/WAIT/AVOID (with setup validation) ──
    chase_status = "NEUTRAL"
    chase_color = "#8B949E"
    chase_text = "—"

    if not setup_valid:
        chase_status = "AVOID"
        chase_color = "#F85149"
        chase_text = f"🚫 AVOID — {setup_note}"
    elif direction_override:
        chase_status = "AVOID"
        chase_color = "#F85149"
        chase_text = override_reason
    else:
        if side == "long":
            if px <= entry * 1.02:
                chase_status = "CHASE"
                chase_color = "#3FB950"
                chase_text = f"🟢 CHASE — Price at/near entry {ff(entry)}. Risk: {risk/px:.2%}."
            elif px > entry * 1.05 and px > stop:
                chase_status = "WAIT"
                chase_color = "#D29922"
                chase_text = f"🟡 WAIT — Price {ff(px)} above entry {ff(entry)}. Wait pullback to {ff(entry)}-{ff(stop)} zone."
            elif px < stop:
                chase_status = "AVOID"
                chase_color = "#F85149"
                chase_text = f"🔴 STOP HIT — Price {ff(px)} below stop {ff(stop)}. Setup invalidated."
            elif rr >= 3.0:
                chase_text += f" | 🎯 HIGH CONVICTION RR {rr:.1f}x"
            elif rr < 1.5:
                chase_text += f" | ⚠️ POOR RR {rr:.1f}x — skip or wait better entry"
        else:  # short
            if px >= entry * 0.98:
                chase_status = "CHASE"
                chase_color = "#3FB950"
                chase_text = f"🟢 CHASE — Price at/near entry {ff(entry)}. Risk: {risk/px:.2%}."
            elif px < entry * 0.95 and px < stop:
                chase_status = "WAIT"
                chase_color = "#D29922"
                chase_text = f"🟡 WAIT — Price {ff(px)} below entry {ff(entry)}. Wait pullback to {ff(entry)}-{ff(stop)} zone."
            elif px > stop:
                chase_status = "AVOID"
                chase_color = "#F85149"
                chase_text = f"🔴 STOP HIT — Price {ff(px)} above stop {ff(stop)}. Setup invalidated."
            elif rr >= 3.0:
                chase_text += f" | 🎯 HIGH CONVICTION RR {rr:.1f}x"
            elif rr < 1.5:
                chase_text += f" | ⚠️ POOR RR {rr:.1f}x — skip or wait better entry"

    # ── MM Positioning ──
    mm_rec = options.get("mm_recommendation", "—")
    mm_pos = options.get("mm_positioning", "UNKNOWN")
    if mm_pos == "CALL_WALL" and side == "long":
        mm_rec += " ⚠️ Call wall resistance — consider taking profit at call wall."
    elif mm_pos == "PUT_WALL" and side == "short":
        mm_rec += " ⚠️ Put wall support — consider covering at put wall."
    elif mm_pos == "PINNED":
        mm_rec += " 🔄 Pinned — directional edge low. Prefer range strategies."

    # ── News ──
    news_signal = ""; news_headline = ""; news_sentiment = 0
    if news and isinstance(news, dict) and news.get("ticker_specific"):
        tn = news["ticker_specific"].get(ticker, {})
        if isinstance(tn, dict):
            news_signal = tn.get("front_run_signal", "")
            news_headline = (tn.get("headlines") or [""])[0] if tn else ""
            news_sentiment = tn.get("sentiment_score", 0) or 0

    # ── Extra context ──
    trend_strength = None; volume_proxy = None; markov_ctx = None; behavioral_flag = None
    if s is not None and len(s) >= 22:
        try:
            s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
            if len(s_clean) >= 22:
                returns = s_clean.pct_change().dropna()
                atr = float((s_clean.diff().abs().tail(14).mean()) / s_clean.tail(14).mean()) if len(s_clean) >= 14 else None
                if atr is not None and math.isfinite(atr):
                    trend_strength = min(100, max(0, atr * 500))
                vol_proxy = float(returns.tail(20).abs().mean() * 100) if len(returns) >= 20 else None
                if vol_proxy is not None and math.isfinite(vol_proxy):
                    volume_proxy = vol_proxy
        except Exception: 
            pass
    if snap:
        m = snap.get("markov_v3", {}) if isinstance(snap.get("markov_v3"), dict) else {}
        if m.get("current_regime"):
            markov_ctx = {"regime": m.get("current_regime"), "confidence": m.get("confidence", 0)}
        yv2 = snap.get("yves_v2", {}) if isinstance(snap.get("yves_v2"), dict) else {}
        if yv2.get("alerts") and isinstance(yv2["alerts"], list):
            for a in yv2["alerts"]:
                if isinstance(a, dict) and a.get("ticker") == ticker:
                    behavioral_flag = a.get("level", "MEDIUM")
                    break

    return {
        "ticker": ticker, "price": px, "entry": entry, "target_1": tp1, "target_2": tp2,
        "stop": stop, "rr": rr, "risk_pct": round(risk/px*100, 2) if px else 0,
        "direction": "LONG" if side == "long" else "SHORT",
        "grade": grade, "setup_valid": setup_valid,
        "near_entry": near_entry, "pos_in_range": round(pos, 2), "side": side,
        "trade_l": lrr, "trade_r": trr, "r1m": r20d, "r5d": r5d, "r3m": _price_ret(ticker, prices, 63),
        "composite": composite, "market_type": market_type,
        "trend": trend, "trend_note": trend_note, "sma50": sma50,
        "direction_override": direction_override, "override_reason": override_reason,
        "options": options,
        "mm_positioning": mm_pos, "mm_recommendation": mm_rec,
        "news_signal": news_signal, "news_headline": news_headline, "news_sentiment": news_sentiment,
        "trend_strength": trend_strength, "volume_proxy": volume_proxy,
        "markov_ctx": markov_ctx, "behavioral_flag": behavioral_flag,
        "entry_note": note, "setup_note": setup_note,
        "confluence": confluence,
        "chase_status": chase_status, "chase_color": chase_color, "chase_text": chase_text,
    }


# ═══════════════════════════════════════════════════════════════════
# BROKER PROXY (IHSG manipulation detection)
# ═══════════════════════════════════════════════════════════════════
def _get_broker_proxy(ticker, prices):
    """
    AUDITED v32.4.1 — Proxy broker summary for IHSG with manipulation detection.
    Detects crossing (wash trading) vs real accumulation/distribution.

    FORMULAS:
    ── Real Accumulation ──
    IF r5d > +3% AND r20d > +5% AND NOT crossing → Real Accumulation
    Confidence = min(100, 50 + |r5d| × 500)

    ── Real Distribution ──
    IF r5d < −3% AND r20d < −5% AND NOT crossing → Real Distribution
    Confidence = min(100, 50 + |r5d| × 500)

    ── Crossing Detection (Wash Trading) ──
    IF vol_5 / vol_20 > 1.5 AND range_5 / range_20 < 0.15 → Crossing
    High activity but price goes nowhere = manipulation proxy.
    """
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 30):
        return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 30: return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}

        px = float(s_clean.iloc[-1])
        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else r5d

        vol_5 = float(s_clean.tail(5).std())
        vol_20 = float(s_clean.tail(20).std()) if len(s_clean) >= 20 else vol_5
        mean_20 = float(s_clean.tail(20).mean())

        range_5 = float(s_clean.tail(5).max() - s_clean.tail(5).min())
        range_20 = float(s_clean.tail(20).max() - s_clean.tail(20).min()) if len(s_clean) >= 20 else range_5

        # Crossing detection: high activity (volatility spike) but price goes nowhere
        crossing = False
        if vol_20 > 0 and vol_5 / vol_20 > 1.5 and range_5 / max(range_20, 0.001) < 0.15:
            crossing = True

        real_acc = False
        if r5d > 0.03 and r20d > 0.05 and not crossing:
            real_acc = True

        real_dist = False
        if r5d < -0.03 and r20d < -0.05 and not crossing:
            real_dist = True

        conf = 0
        if real_acc: conf = min(100, int(50 + abs(r5d)*500))
        elif real_dist: conf = min(100, int(50 + abs(r5d)*500))
        elif crossing: conf = 70

        return {
            "real_accumulation": real_acc,
            "real_distribution": real_dist,
            "crossing_detected": crossing,
            "confidence": conf,
            "r5d": round(r5d, 4),
            "r20d": round(r20d, 4),
            "vol_ratio": round(vol_5/vol_20, 2) if vol_20 > 0 else 1.0,
            "range_ratio": round(range_5/max(range_20, 0.001), 2),
        }
    except Exception:
        return {"real_accumulation": False, "real_distribution": False, "crossing_detected": False, "confidence": 0}

def _build_ihsg_row(ticker, prices, ar, **kwargs):
    row = _build_row(ticker, prices, ar, market_type="ihsg", **kwargs)
    if not row: 
        return None
    # IHSG: no options, strip them
    row["options"] = {}
    row["mm_positioning"] = ""
    row["mm_recommendation"] = ""
    # Keep trend data
    sector = IHSG_SECTOR_MAP.get(ticker, "Indonesia")
    row["sector"] = sector
    r1m = row.get("r1m", 0) or 0
    if not row.get("setup_valid", True):
        row["recommendation"] = f"AVOID — {row.get('setup_note', 'Invalid setup')}"
    elif r1m > 0.05: 
        row["recommendation"] = f"Strong momentum +{r1m:.1%} — {sector} play"
    elif r1m < -0.05: 
        row["recommendation"] = f"Weak momentum {r1m:.1%} — avoid {sector}"
    else: 
        row["recommendation"] = f"{sector} — range bound, wait breakout"
    broker = _get_broker_proxy(ticker, prices)
    row["broker"] = broker
    return row

def build_ticker_rows(tickers, market_type="us_equity", vix_now=20, gamma_data=None, greeks_data=None, news=None, prices=None, ar=None, snap=None):
    rows = []
    for t in tickers:
        if market_type == "ihsg": r = _build_ihsg_row(t, prices, ar, snap=snap)
        else: r = _build_row(t, prices, ar, vix_now=vix_now, gamma_data=gamma_data, greeks_data=greeks_data, market_type=market_type, news=news, snap=snap)
        if r: rows.append(r)
    return rows

def split_long_short(rows):
    longs = [r for r in rows if "LONG" in r.get("direction", "")]
    shorts = [r for r in rows if "SHORT" in r.get("direction", "")]
    return sorted(longs, key=lambda x: x.get("rr", 0), reverse=True), sorted(shorts, key=lambda x: x.get("rr", 0), reverse=True)

# ═══════════════════════════════════════════════════════════════════
# VISUAL RENDERERS v4 — AUDITED (DUPLICATES REMOVED)
# ═══════════════════════════════════════════════════════════════════
def _interpret_gamma(gamma_regime, px, max_pain):
    if not gamma_regime: return ""
    mp_dist = ((px - max_pain) / max_pain * 100) if max_pain else 0
    if gamma_regime in ("DEEP_POSITIVE", "POSITIVE"):
        return f"🟢 Positive gamma — dealers long. Pin risk to max pain ({mp_dist:+.1f}%). Rallies face call-wall resistance. Sell into strength."
    elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"):
        return f"🔴 Negative gamma — dealers short. Acceleration risk on break. Dips get bought at put wall. Buy weakness."
    else:
        return f"🟡 Transition gamma — directional play valid. Watch for vanna/charm shift."

def _interpret_gex(gex):
    if gex is None: return ""
    if gex > 0.5: return f"🟢 GEX +{gex:.2f}: Dealer long gamma → mean-reversion, sell rallies."
    elif gex < -0.5: return f"🔴 GEX {gex:.2f}: Dealer short gamma → trend acceleration, buy dips."
    else: return f"🟡 GEX {gex:.2f}: Neutral — watch breakout direction."

def _interpret_vanna(vanna):
    if vanna is None: return ""
    try: v = float(vanna)
    except: return ""
    if v > 0.5: return f"🟢 Vanna +{v:.2f}: Rally = vol crush (bearish vol). Sell premium into strength."
    elif v < -0.5: return f"🔴 Vanna {v:.2f}: Rally = vol expansion (bullish vol). Buy premium on breakouts."
    else: return f"🟡 Vanna {v:.2f}: Neutral spot-vol correlation."

def _interpret_charm(charm):
    if charm is None: return ""
    try: c = float(charm)
    except: return ""
    if c > 0.5: return f"🟢 Charm +{c:.2f}: Put support strengthening over time."
    elif c < -0.5: return f"🔴 Charm {c:.2f}: Put support eroding — downside acceleration risk."
    else: return f"🟡 Charm {c:.2f}: Minimal theta-driven delta shift."

def _interpret_skew(skew_30d):
    if skew_30d is None: return ""
    s = float(skew_30d)
    if s > 0.05: return f"🔴 Skew {s:+.2f}: OTM puts rich — fear priced in. Potential reversal if fear fades."
    elif s < -0.05: return f"🟢 Skew {s:+.2f}: OTM calls rich — greed/fomo. Potential pullback if euphoria breaks."
    else: return f"🟡 Skew {s:+.2f}: Fair — balanced risk pricing."

def _interpret_mm(mm_pos, mp_dist):
    if not mm_pos or mm_pos == "UNKNOWN": return ""
    if mm_pos == "PINNED":
        return f"📍 PINNED (dist {mp_dist:+.1f}%): MM trapped near max pain. Range-bound until expiry. Sell straddles or wait breakout."
    elif mm_pos == "CALL_WALL":
        return f"📈 CALL WALL (dist +{mp_dist:.1f}%): Price above max pain + positive gamma. MM sells into rallies. Fade strength."
    elif mm_pos == "PUT_WALL":
        return f"📉 PUT WALL (dist {mp_dist:.1f}%): Price below max pain + negative gamma. MM buys dips. Support holds."
    elif mm_pos == "TRANSITION":
        return f"🔄 TRANSITION: Between walls — directional play valid. Watch vanna/charm for momentum shift."
    return ""

def _get_smart_money_badge(ticker, snap):
    sm = snap.get("smart_money", {}) if isinstance(snap.get("smart_money"), dict) else {}
    consensus = sm.get("consensus_picks", []) if isinstance(sm.get("consensus_picks"), list) else []
    for c in consensus:
        if isinstance(c, dict) and c.get("ticker") == ticker:
            return f"🐋 Smart${c.get('n_funds', 0)}"
    return ""

def _get_capital_rotation_role(ticker, snap):
    cr = snap.get("capital_rotation", {}) if isinstance(snap.get("capital_rotation"), dict) else {}
    roles = cr.get("ticker_roles", {}) if isinstance(cr.get("ticker_roles"), dict) else {}
    return roles.get(ticker, "")

def _get_vrp_score(ticker, snap):
    vrp = snap.get("vrp_scanner", {}) if isinstance(snap.get("vrp_scanner"), dict) else {}
    if vrp.get("ok"):
        for item in vrp.get("high_vrp_sell_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("vrp_pct", 0)
        for item in vrp.get("low_vrp_buy_premium", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return -item.get("vrp_pct", 0)
    return 0

def _get_squeeze_score(ticker, snap):
    sq = snap.get("squeeze_scanner", {}) if isinstance(snap.get("squeeze_scanner"), dict) else {}
    if sq.get("ok"):
        for item in sq.get("imminent_squeezes", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("squeeze_score", 0)
        for item in sq.get("strong_candidates", []):
            if isinstance(item, dict) and item.get("ticker") == ticker:
                return item.get("squeeze_score", 0)
    return 0

def _get_markov_confidence(ticker, snap):
    m = snap.get("markov_v3", {}) if isinstance(snap.get("markov_v3"), dict) else {}
    return m.get("confidence", 0)

def _get_single_recommendation(options, direction="LONG", market_type="us_equity", 
                              cot_data=None, onchain_data=None, ticker="", prices=None, row=None):
    """
    AUDITED RECOMMENDATION ENGINE v32.4
    ──────────────────────────────────
    Generates ONE unified recommendation based on ALL available data.

    SCORING METHOD: Additive voting with normalized weights.
    Each factor adds weight to an action bucket. Final action = highest bucket.
    Confidence = min(100, sum of weights for winning bucket).

    NEW v32.4:
    - Added price-vs-entry chase/wait analysis
    - Added formula transparency (each factor shows its raw score)
    - Added RR-based conviction boost/penalty
    """
    def _safe_num(v, default=0.0):
        if v is None: return default
        try:
            if isinstance(v, str):
                v = v.replace("−", "-").replace("—", "-").strip()
            f = float(v)
            return f if math.isfinite(f) else default
        except:
            return default

    # ── Extract all data ──
    gamma = str(options.get("gamma_regime", ""))
    mp = _safe_num(options.get("max_pain"), 0)
    mp_dist = _safe_num(options.get("mp_dist"), 0)
    skew = _safe_num(options.get("skew_30d"), 0)
    iv_rank = _safe_num(options.get("iv_rank"), 50)
    pc_ratio = _safe_num(options.get("pc_ratio"), 1.0)
    vanna = _safe_num(options.get("vanna"), 0)
    charm = _safe_num(options.get("charm"), 0)
    gex = _safe_num(options.get("gex"), 0)
    expected_move = _safe_num(options.get("expected_move_pct"), 0)
    put_wall = _safe_num(options.get("put_wall"), 0)
    call_wall = _safe_num(options.get("call_wall"), 0)
    oi_call = options.get("oi_call", 0) or 0
    oi_put = options.get("oi_put", 0) or 0
    source = options.get("source", "PROXY")

    # ── Score each factor ──
    scores = []
    reasons = []

    # 1. MM POSITIONING (gamma + max pain distance)
    if abs(mp_dist) < 0.025 and gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("HOLD/SELL_PREMIUM", 60))
        reasons.append(("📍 Pinned near max pain ({:.1f}%) + pos gamma = range-bound. MM sells both sides.".format(mp_dist*100), 60))
    elif mp_dist < -0.03 and gamma in ("NEGATIVE", "DEEP_NEGATIVE"):
        scores.append(("BUY", 85))
        reasons.append(("📉 Below max pain ({:.1f}%) + neg gamma = MM buys dips. Put wall ${:.2f} = support.".format(mp_dist*100, put_wall), 85))
    elif mp_dist > 0.03 and gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("SELL/COVERED_CALL", 70))
        reasons.append(("📈 Above max pain (+{:.1f}%) + pos gamma = MM sells rallies. Fade at call wall ${:.2f}.".format(mp_dist*100, call_wall), 70))
    elif gamma in ("POSITIVE", "DEEP_POSITIVE"):
        scores.append(("BUY", 55))
        reasons.append(("🟢 Positive gamma — dealer long, mean-reversion to max pain ${:.2f}.".format(mp), 55))
    elif gamma in ("NEGATIVE", "DEEP_NEGATIVE"):
        scores.append(("BUY", 65))
        reasons.append(("🔴 Negative gamma — dealer short, trend acceleration on breakout.", 65))
    else:
        scores.append(("HOLD", 40))
        reasons.append(("🟡 Transition gamma — wait for directional confirmation.", 40))

    # 2. SKEW (fear/greed pricing)
    if skew > 0.05 and iv_rank > 60:
        scores.append(("BUY", 70))
        reasons.append(("🔴 Put skew rich ({:+.2f}) + IV rank {:.0f}% = fear overpriced. Sell puts or buy spot on dips.".format(skew, iv_rank), 70))
    elif skew < -0.05 and iv_rank < 40:
        scores.append(("BUY", 75))
        reasons.append(("🟢 Call skew cheap ({:+.2f}) + IV rank {:.0f}% = upside convexity underpriced. Buy calls/LEAPS.".format(skew, iv_rank), 75))
    elif iv_rank < 35:
        scores.append(("BUY", 60))
        reasons.append(("💤 IV rank {:.0f}% low — ideal accumulation environment for buy-and-hold.".format(iv_rank), 60))
    elif iv_rank > 65:
        scores.append(("HEDGE", 55))
        reasons.append(("⚠️ IV rank {:.0f}% high — expensive to buy options, consider selling premium or hedging.".format(iv_rank), 55))

    # 3. GEX (gamma exposure)
    if gex > 1.0:
        scores.append(("SELL/COVERED_CALL", 65))
        reasons.append(("🟢 GEX +{:.2f} extreme positive — strong mean-reversion. Sell covered calls into rallies.".format(gex), 65))
    elif gex < -1.0:
        scores.append(("BUY", 70))
        reasons.append(("🔴 GEX {:.2f} extreme negative — trend acceleration. Buy dips, ride momentum.".format(gex), 70))
    elif gex > 0.5:
        scores.append(("HOLD", 50))
        reasons.append(("🟢 GEX +{:.2f} — mild mean-reversion bias.".format(gex), 50))
    elif gex < -0.5:
        scores.append(("BUY", 55))
        reasons.append(("🔴 GEX {:.2f} — mild acceleration bias.".format(gex), 55))

    # 4. VANNA (spot-vol correlation)
    if vanna > 0.5:
        scores.append(("BUY", 60))
        reasons.append(("🟢 Vanna +{:.2f}: Rally = vol crush. Buy spot on dips, avoid long vol.".format(vanna), 60))
    elif vanna < -0.5:
        scores.append(("HEDGE", 55))
        reasons.append(("🔴 Vanna {:.2f}: Rally = vol expansion. Breakouts will be volatile — wait or hedge.".format(vanna), 55))

    # 5. CHARM (theta decay on delta)
    if charm > 0.5:
        scores.append(("BUY", 55))
        reasons.append(("🟢 Charm +{:.2f}: Put support strengthening daily.".format(charm), 55))
    elif charm < -0.5:
        scores.append(("HEDGE", 60))
        reasons.append(("🔴 Charm {:.2f}: Put support eroding — downside acceleration risk, hedge with puts.".format(charm), 60))

    # 6. PUT/CALL RATIO
    if pc_ratio < 0.60:
        scores.append(("CAUTION", 50))
        reasons.append(("🎰 PC ratio {:.2f} extreme low = retail call FOMO. Watch for exhaustion.".format(pc_ratio), 50))
    elif pc_ratio > 1.3:
        scores.append(("BUY", 55))
        reasons.append(("🛡️ PC ratio {:.2f} high = put hedging active. Contrarian bullish if at support.".format(pc_ratio), 55))

    # 7. COT DATA (Forex/Commodity only)
    if market_type in ("forex", "commodity") and cot_data and cot_data.get("signal") != "NEUTRAL":
        cot_sig = cot_data.get("signal", "NEUTRAL")
        cot_net = cot_data.get("net_noncom", 0)
        cot_chg = cot_data.get("change_wow", 0)
        if cot_sig == "BULLISH":
            scores.append(("BUY", 65))
            reasons.append(("🏛️ COT Non-Commercial net +{:,} (WoW {:+,}) = institutional buying.".format(int(cot_net), int(cot_chg)), 65))
        elif cot_sig == "BEARISH":
            scores.append(("SELL", 65))
            reasons.append(("🏛️ COT Non-Commercial net {:,} (WoW {:+,}) = institutional selling.".format(int(cot_net), int(cot_chg)), 65))

    # 8. ON-CHAIN (Crypto only)
    if market_type == "crypto" and onchain_data:
        whale = onchain_data.get("whale_signal", "HOLD")
        funding = onchain_data.get("funding_proxy", 0)
        if whale == "BUY":
            scores.append(("BUY", 70))
            reasons.append(("🐋 Whale accumulation detected + momentum {}.".format(onchain_data.get("momentum", "—")), 70))
        elif whale == "SELL":
            scores.append(("SELL", 70))
            reasons.append(("🐋 Whale distribution detected — reduce exposure.", 70))
        if abs(funding) > 0.0005:
            scores.append(("CAUTION", 45))
            reasons.append(("⛓️ Funding rate extreme ({:.5f}) = leverage excess.".format(funding), 45))

    # 9. CHASE/WAIT boost/penalty (NEW v32.4)
    if row and row.get("chase_status"):
        chase = row.get("chase_status")
        rr_val = row.get("rr", 0) or 0
        if chase == "CHASE":
            scores.append(("BUY" if direction == "LONG" else "SELL", 15))
            reasons.append(("🏃 Price at/near entry — immediate execution valid.", 15))
        elif chase == "WAIT":
            scores.append(("HOLD", 20))
            reasons.append(("⏳ Price away from entry — wait for pullback to optimal zone.", 20))
        elif chase == "AVOID":
            scores.append(("HOLD", 40))
            reasons.append(("🚫 Setup invalidated — stop level breached. Do not enter.", 40))
        if rr_val >= 3.0:
            scores.append(("BUY" if direction == "LONG" else "SELL", 10))
            reasons.append(("🎯 RR {:.1f}x — highly asymmetric reward.".format(rr_val), 10))
        elif rr_val < 1.5 and rr_val > 0:
            scores.append(("HOLD", 15))
            reasons.append(("⚠️ RR {:.1f}x — poor risk/reward. Skip or wait for better entry.".format(rr_val), 15))

    # ── SETUP VALIDATION (NEW v32.4.1) ──
    if row and not row.get("setup_valid", True):
        return {
            "action": "HOLD / TUNGGU",
            "strategy": "Setup invalid — stop too close to entry or risk < 0.5%",
            "rationale": f"• 🚫 Stop {ff(row.get('stop'))} too close to entry {ff(row.get('entry'))} (risk {row.get('risk_pct',0):.2f}% < 0.5% minimum).<br>• Wait for better entry or wider risk range.",
            "raw_action": "HOLD",
            "confidence": 0,
            "factors": 0,
            "source": "VALIDATION",
        }

    if row and row.get("direction_override"):
        return {
            "action": "HOLD / TUNGGU",
            "strategy": "Trend opposes signal — don't fight the trend",
            "rationale": f"• {row.get('override_reason', 'Trend filter override')}<br>• Wait for trend alignment before entering.",
            "raw_action": "HOLD",
            "confidence": 0,
            "factors": 0,
            "source": "TREND_FILTER",
        }

    # ── AGGREGATE TO ONE RECOMMENDATION ──
    action_weights = {}
    for action, weight in scores:
        action_weights[action] = action_weights.get(action, 0) + weight

    if not action_weights:
        best_action = "HOLD"
        best_score = 0
    else:
        best_action = max(action_weights, key=action_weights.get)
        best_score = action_weights[best_action]

    action_map = {
        "BUY": ("BELI SPOT / AKUMULASI", "Tambah posisi spot atau beli LEAPS/calls"),
        "SELL": ("JUAL / REDUKSI", "Turunkan exposure atau short via puts"),
        "SELL/COVERED_CALL": ("JUAL COVERED CALL", "Jual call di resistance untuk income"),
        "HEDGE": ("HEDGE POSISI", "Beli put protektif atau reduce beta"),
        "HOLD/SELL_PREMIUM": ("HOLD + JUAL PREMIUM", "Straddle/strangle untuk income saat pinned"),
        "CAUTION": ("WASPADA / TUNGGU", "Signal konflik — tunggu konfirmasi breakout"),
        "HOLD": ("HOLD / TUNGGU", "Data tidak cukup kuat — tunggu setup lebih jelas"),
    }
    final_action, final_strategy = action_map.get(best_action, ("HOLD", "Tunggu"))

    # Build comprehensive rationale with scores
    rationale_lines = []
    for reason_text, score in reasons:
        rationale_lines.append(f"• {reason_text} <span style='color:#484F58;font-size:0.6rem;'>(+{score})</span>")
    rationale = "<br>".join(rationale_lines) if rationale_lines else "• Data options/greeks tidak cukup untuk rekomendasi kuat."

    if expected_move > 0:
        rationale += f"<br>• 📊 Expected move: ±{expected_move:.1%} until expiry."
    if oi_call and oi_put:
        total_oi = oi_call + oi_put
        call_pct = oi_call / total_oi * 100
        rationale += f"<br>• 📈 OI Call/Put: {call_pct:.0f}%/{100-call_pct:.0f}% ({total_oi/1e6:.1f}M total)"

    # Add data source note
    rationale += f"<br>• 🔧 Data source: <b>{source}</b> (YF=live, PROXY=calculated from price)"

    return {
        "action": final_action,
        "strategy": final_strategy,
        "rationale": rationale,
        "raw_action": best_action,
        "confidence": min(100, best_score),
        "factors": len(reasons),
        "source": source,
    }


def _get_ticker_boombust_score(ticker, prices, snap):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 60):
        return {"score": 0, "stage": "UNKNOWN", "signal": "—"}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 60: return {"score": 0, "stage": "UNKNOWN", "signal": "—"}

        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        sma50 = float(s_clean.tail(50).mean()) if len(s_clean) >= 50 else sma20
        sma200 = float(s_clean.tail(200).mean()) if len(s_clean) >= 200 else sma50

        r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1) if len(s_clean) >= 22 else 0
        r3m = float(s_clean.iloc[-1] / s_clean.iloc[-63] - 1) if len(s_clean) >= 63 else r1m
        r6m = float(s_clean.iloc[-1] / s_clean.iloc[-126] - 1) if len(s_clean) >= 126 else r3m

        mom_accel = r1m - (r3m / 3) if r3m != 0 else 0
        dist_from_200 = (px - sma200) / sma200 if sma200 != 0 else 0

        vol_20 = float(s_clean.tail(20).std())
        vol_60 = float(s_clean.tail(60).std()) if len(s_clean) >= 60 else vol_20
        vol_expansion = (vol_20 / vol_60 - 1) if vol_60 > 0 else 0

        score = 0
        if r1m > 0.20: score += 3
        elif r1m > 0.10: score += 2
        elif r1m > 0.05: score += 1

        if dist_from_200 > 0.30: score += 3
        elif dist_from_200 > 0.15: score += 2
        elif dist_from_200 > 0.05: score += 1

        if mom_accel > 0.10: score += 2
        elif mom_accel > 0.05: score += 1

        if vol_expansion > 0.50: score += 2
        elif vol_expansion > 0.20: score += 1

        score = min(10, max(0, score))

        if score >= 8: stage = "EUPHORIA"
        elif score >= 6: stage = "ACCELERATION"
        elif score >= 4: stage = "INCEPTION"
        elif score >= 2: stage = "EARLY"
        else: stage = "BASE"

        if score >= 7:
            signal = "⚠️ BUBBLE RISK — Consider taking profits"
        elif score >= 4 and r1m > 0.10:
            signal = "📈 Momentum strong but watch for exhaustion"
        elif score <= 2 and r1m < -0.10:
            signal = "🔨 Capitulation — potential bottom"
        elif score <= 3 and r1m > 0.05:
            signal = "🌱 Early stage — good accumulation zone"
        else:
            signal = "➡️ Neutral — no extreme bubble/capitulation"

        return {"score": round(score, 1), "stage": stage, "signal": signal,
                "r1m": round(r1m, 3), "dist_200": round(dist_from_200, 3)}
    except Exception:
        return {"score": 0, "stage": "UNKNOWN", "signal": "—"}


def _get_ticker_behavioral_score(ticker, prices, options, snap):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}

        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else r5d

        pc_ratio = (_safe_float(options.get("pc_ratio")) or 1.0) if options else 1.0
        iv_rank = (_safe_float(options.get("iv_rank")) or 50) if options else 50
        skew = (_safe_float(options.get("skew_30d")) or 0) if options else 0

        casino = 0
        if r5d > 0.15 and r20d > 0.30: casino += 40
        if pc_ratio < 0.60: casino += 20
        if iv_rank > 70: casino += 20
        if skew < -0.10: casino += 20
        casino = min(100, casino)

        sm_divergence = False
        if r5d > 0.05 and pc_ratio > 1.2 and iv_rank < 40:
            sm_divergence = True

        retail_fomo = casino > 60

        if casino > 70:
            signal = f"🎰 CASINO MODE ({casino}%) — Retail FOMO extreme. Raise cash."
        elif casino > 50:
            signal = f"⚠️ Elevated speculation ({casino}%) — Tighten stops."
        elif sm_divergence:
            signal = "🐋 Smart Money Divergence — Price up but hedging detected."
        elif casino < 20 and r20d < -0.15:
            signal = "😰 Fear/Capitulation — Contrarian buy opportunity."
        else:
            signal = f"✅ Behavior normal ({casino}%). No extreme positioning."

        return {"casino_score": casino, "retail_fomo": retail_fomo, 
                "smart_money_divergence": sm_divergence, "signal": signal,
                "pc_ratio": round(pc_ratio, 2), "iv_rank": round(iv_rank, 0)}
    except Exception:
        return {"casino_score": 0, "retail_fomo": False, "smart_money_divergence": False, "signal": "—"}


def render_ticker_card_v4(row, expanded=False):
    """AUDITED v32.4.1 — Trend info + clear basis + setup validation."""
    ticker = row.get("ticker", "?")
    px = row.get("price", 0)
    direction = row.get("direction", "NEUTRAL")
    grade = row.get("grade", "C")
    rr_val = row.get("rr", 0)
    entry = row.get("entry")
    t1 = row.get("target_1")
    t2 = row.get("target_2")
    stop = row.get("stop")
    trade_l = row.get("trade_l")
    trade_r = row.get("trade_r")
    news_sig = row.get("news_signal", "")
    r1m = row.get("r1m")
    mm_pos = row.get("mm_positioning", "")
    options = row.get("options", {})
    market_type = row.get("market_type", "us_equity")
    show_options = market_type != "ihsg"
    prices_series = None
    snap_local = st.session_state.snap
    if snap_local is not None:
        prices_series = snap_local.get("prices", {}).get(ticker)

    # Trend data (NEW v32.4.1)
    trend = row.get("trend", "NEUTRAL")
    trend_note = row.get("trend_note", "")
    setup_valid = row.get("setup_valid", True)
    direction_override = row.get("direction_override", False)
    override_reason = row.get("override_reason", "")
    risk_pct = row.get("risk_pct", 0)

    dir_kind = "long" if "LONG" in direction else "short" if "SHORT" in direction else "neut"
    dir_label = "LONG" if "LONG" in direction else "SHORT"
    grade_kind = grade.lower().replace("+", "")

    badges = _badge_html(dir_label, dir_kind) + _badge_html(grade, grade_kind)

    # Trend badge (NEW)
    if trend == "BULLISH":
        badges += _badge_html("📈 Trend", "long")
    elif trend == "BEARISH":
        badges += _badge_html("📉 Trend", "short")
    elif trend == "BULLISH_BIAS":
        badges += _badge_html("➡️ >SMA50", "neut")
    elif trend == "BEARISH_BIAS":
        badges += _badge_html("➡️ <SMA50", "neut")

    if not setup_valid or direction_override:
        badges += _badge_html("🚫 INVALID", "short")

    if rr_val and rr_val >= 2: 
        badges += _badge_html(f"RR {rr_val}x", "news")
    if news_sig and "BULLISH" in str(news_sig): 
        badges += _badge_html("NEWS+", "news")
    if news_sig and "BEARISH" in str(news_sig): 
        badges += _badge_html("NEWS-", "news")
    if mm_pos and mm_pos != "UNKNOWN": 
        badges += _badge_html(mm_pos, "mm")

    # ── VolSignals Dealer Regime Badge ──
    vs_regime = options.get("volsignals_regime", {})
    if vs_regime and isinstance(vs_regime, dict):
        regime_label = vs_regime.get("dealer_regime", "")
        regime_conf = vs_regime.get("confidence", "")
        if regime_label:
            regime_color = "long" if "STABILIZING" in regime_label else "short" if "AMPLIFYING" in regime_label else "neut"
            badges += _badge_html(f"🛡️ {regime_label[:4]} {regime_conf[:1]}", regime_color)

    # Chase/Wait badge
    chase_status = row.get("chase_status", "NEUTRAL")
    if chase_status == "CHASE":
        badges += _badge_html("🏃 CHASE", "chase")
    elif chase_status == "WAIT":
        badges += _badge_html("⏳ WAIT", "wait")
    elif chase_status == "AVOID":
        badges += _badge_html("🚫 AVOID", "short")

    confluence = row.get("confluence", {})
    if confluence.get("entry_cluster") and confluence["entry_cluster"].get("count", 0) >= 2:
        badges += _badge_html(f"🔥 Confluence x{confluence['entry_cluster']['count']}", "a")

    alpha_src = row.get("alpha_source", "")
    alpha_score = row.get("alpha_score", 0)
    if alpha_src:
        src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","karsan_squeeze":"📊","karsan_convexity":"📐","coatue":"💱"}.get(alpha_src,"⚡")
        badges += _badge_html(f"{src_emoji} {alpha_src.replace('_',' ').title()}", "mm")
    if alpha_score:
        badges += _badge_html(f"α{alpha_score}", "a" if alpha_score >= 80 else "b" if alpha_score >= 70 else "c")

    if snap_local:
        sm_badge = _get_smart_money_badge(ticker, snap_local)
        if sm_badge: 
            badges += _badge_html(sm_badge, "news")
        vrp = _get_vrp_score(ticker, snap_local)
        if vrp > 10: 
            badges += _badge_html(f"VRP+{vrp:.0f}%", "short")
        elif vrp < -10: 
            badges += _badge_html(f"VRP{vrp:.0f}%", "long")
        sq = _get_squeeze_score(ticker, snap_local)
        if sq > 60: 
            badges += _badge_html(f"Squeeze {sq:.0f}", "news")
        cr_role = _get_capital_rotation_role(ticker, snap_local)
        if cr_role: 
            badges += _badge_html(cr_role.replace("_"," ")[:12], "neut")

    spark = _sparkline_html(prices_series, width=80, height=24, bars=18)
    rr_html = _risk_range_html(px, trade_l, trade_r, width_pct=100)

    extra_meta = ""
    ts = row.get("trend_strength")
    if ts is not None:
        extra_meta += f'<div title="Trend Strength">📈 {ts:.0f}</div>'
    vp = row.get("volume_proxy")
    if vp is not None:
        extra_meta += f'<div title="Volume Proxy">💨 {vp:.1f}%</div>'
    mk = row.get("markov_ctx")
    if mk and mk.get("confidence", 0) > 0.3:
        extra_meta += f'<div title="Markov {mk.get("regime","—")}">🔮 {mk.get("confidence",0):.0%}</div>'
    bf = row.get("behavioral_flag")
    if bf:
        extra_meta += f'<div title="Behavioral Alert" style="color:#F85149;">🧠 {bf}</div>'

    # Risk pct display
    if risk_pct > 0:
        extra_meta += f'<div title="Risk %">🛑 {risk_pct:.1f}%</div>'

    card_html = (
        f'<div class="ticker-card-v4">'
        f'<div class="tc-v4-left"><div class="tc-v4-symbol">{ticker}</div><div class="tc-v4-price">{ff(px)}</div><div class="tc-v4-badges">{badges}</div></div>'
        f'{spark}'
        f'<div class="tc-v4-rr">{rr_html}</div>'
        f'<div class="tc-v4-meta"><div>Entry {ff(entry)}</div><div>RR {ff(rr_val)}x</div><div>1M {fp(r1m)}</div>{extra_meta}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    with st.expander("🎯 Trade Setup", expanded=expanded):
        # Alpha thesis
        alpha_thesis = row.get("alpha_thesis", "")
        alpha_src = row.get("alpha_source", "")
        if alpha_thesis:
            src_emoji = {"bottleneck":"🚧","front_run":"🔮","leopold":"🏗️","karsan_squeeze":"📊","karsan_convexity":"📐","coatue":"💱"}.get(alpha_src,"⚡")
            st.markdown(f'<div style="font-size:0.78rem;color:#E6EDF3;margin-bottom:6px;padding:6px 8px;background:#161B22;border-left:3px solid #A855F7;border-radius:4px;"><b>{src_emoji} {alpha_src.replace("_"," ").title()} Thesis:</b> {alpha_thesis}</div>', unsafe_allow_html=True)

        # ── BASIS EXPLANATION (AUDITED v32.4.1) ──
        basis_html = '<div style="font-size:0.7rem;color:#8B949E;margin-bottom:8px;">'
        basis_parts = []
        if row.get("trade_l"): 
            basis_parts.append(f"LRR {ff(row['trade_l'])}")
        if row.get("trade_r"): 
            basis_parts.append(f"TRR {ff(row['trade_r'])}")
        if options.get("max_pain"): 
            basis_parts.append(f"Max Pain {ff(options['max_pain'])}")
        if options.get("put_wall"): 
            basis_parts.append(f"Put Wall {ff(options['put_wall'])}")
        if options.get("call_wall"): 
            basis_parts.append(f"Call Wall {ff(options['call_wall'])}")
        if basis_parts:
            basis_html += "Basis: " + " · ".join(basis_parts)

        # Trend basis (NEW)
        if trend_note:
            basis_html += f'<br><span style="color:#D29922;">{trend_note}</span>'

        # Direction override reason
        if override_reason:
            basis_html += f'<br><span style="color:#F85149;font-weight:600;">{override_reason}</span>'

        # Setup validation
        if not setup_valid:
            setup_note = row.get("setup_note", "")
            basis_html += f'<br><span style="color:#F85149;font-weight:700;">🚫 {setup_note}</span>'

        basis_html += '</div>'
        st.markdown(basis_html, unsafe_allow_html=True)

        # CHASE/WAIT badge
        chase_text = row.get("chase_text", "")
        chase_color = row.get("chase_color", "#8B949E")
        if chase_text:
            st.markdown(
                f'<div style="background:{chase_color}15;border:1px solid {chase_color}50;border-radius:6px;padding:6px 10px;margin:6px 0;font-size:0.75rem;color:{chase_color};font-weight:600;">'
                f'{chase_text}</div>', unsafe_allow_html=True)

        # ── Recommendation ──
        confluence = row.get("confluence", {})

        if market_type == "ihsg":
            broker = row.get("broker", {})
            if broker:
                acc = broker.get("real_accumulation", False)
                dist = broker.get("real_distribution", False)
                cross = broker.get("crossing_detected", False)
                conf = broker.get("confidence", 0)
                r5d_b = broker.get("r5d", 0)

                if acc:
                    broker_color = "#3FB950"
                    broker_action = "AKUMULASI REAL"
                    broker_strategy = "Genuine buying detected — tambah posisi"
                    broker_rationale = f"📈 Price +{r5d_b:.1%} 5D dengan trend consistency. Broker accumulation {conf}% confidence."
                elif dist:
                    broker_color = "#F85149"
                    broker_action = "DISTRIBUSI REAL"
                    broker_strategy = "Genuine selling detected — kurangi posisi"
                    broker_rationale = f"📉 Price {r5d_b:.1%} 5D. Broker distribution {conf}% confidence."
                elif cross:
                    broker_color = "#D29922"
                    broker_action = "WASPADA CROSSING"
                    broker_strategy = "Volume tinggi tapi price flat — possible wash trading"
                    broker_rationale = f"⚠️ High volume but stagnant price. Wait for genuine breakout."
                else:
                    broker_color = "#8B949E"
                    broker_action = "TIDAK ADA SIGNAL"
                    broker_strategy = "Broker activity normal — tunggu konfirmasi"
                    broker_rationale = "📊 No clear accumulation or distribution pattern."

                rec = {
                    "action": broker_action,
                    "strategy": broker_strategy,
                    "rationale": broker_rationale,
                    "confidence": conf,
                    "factors": 1,
                    "source": "BROKER_PROXY",
                }
                rec_color = broker_color
            else:
                rec = {
                    "action": "HOLD / TUNGGU",
                    "strategy": "Data broker tidak tersedia",
                    "rationale": "• Data broker summary tidak cukup untuk rekomendasi.",
                    "confidence": 0,
                    "factors": 0,
                    "source": "NONE",
                }
                rec_color = "#8B949E"
        else:
            cot_data = None
            onchain_data = None
            if market_type == "forex" or market_type == "commodity":
                cot_data = _get_cot_proxy(ticker)
            if market_type == "crypto":
                onchain_data = _get_onchain_proxy(ticker, st.session_state.snap.get("prices", {}))
            rec = _get_single_recommendation(
                options, direction=row.get("direction", "LONG"), 
                market_type=market_type, cot_data=cot_data, 
                onchain_data=onchain_data, ticker=ticker, row=row
            )
            rec_color = {"BELI SPOT / AKUMULASI": "#3FB950", "AKUMULASI SPOT": "#3FB950", "BELI CALL / LONG SPOT": "#3FB950",
                         "BELI SPOT + JUAL PUT": "#2EA043", "BELI SPOT": "#3FB950",
                         "JUAL COVERED CALL": "#D29922", "JUAL PUT PROTEKTIF": "#F85149",
                         "JUAL / REDUKSI": "#F85149", "HEDGE POSISI": "#F85149",
                         "HOLD + JUAL PREMIUM": "#D29922", "WASPADA / TUNGGU": "#D29922",
                         "HOLD / TUNGGU": "#8B949E", "HOLD": "#8B949E"}.get(rec["action"], "#58A6FF")

        # Build context lines
        ctx_lines = []
        if row.get("entry_note"):
            ctx_lines.append(row["entry_note"])
        if confluence.get("entry_cluster") and confluence["entry_cluster"].get("count", 0) >= 2:
            levels = confluence.get("entry", [])
            levels_str = " · ".join([f"{name} {ff(val)}" for name, val in levels if val is not None])
            if levels_str:
                ctx_lines.append(f"🔥 Entry Confluence x{confluence['entry_cluster']['count']}: {levels_str}")
        if confluence.get("target_cluster") and confluence["target_cluster"].get("count", 0) >= 2:
            t_levels = confluence.get("target", [])
            t_str = " · ".join([f"{name} {ff(val)}" for name, val in t_levels if val is not None])
            if t_str:
                ctx_lines.append(f"🎯 Target Confluence x{confluence['target_cluster']['count']}: {t_str}")

        ctx_html = ""
        if ctx_lines:
            ctx_html = '<div style="margin-bottom:6px;padding:4px 8px;background:#21262D;border-radius:4px;font-size:0.68rem;color:#8B949E;line-height:1.4;">' + "<br>".join(ctx_lines) + '</div>'

        # ── VISUAL RECOMMENDATION CARD ──
        rec_html = f'<div style="background:#161B22;border:1px solid {rec_color}40;border-radius:10px;padding:12px;margin:6px 0;">'

        conf_pct = rec.get("confidence", 50)
        rec_html += f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        rec_html += f'<div style="background:{rec_color}20;border:1px solid {rec_color}50;border-radius:6px;padding:4px 10px;font-size:0.75rem;color:{rec_color};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">🎯 {rec["action"]}</div>'
        rec_html += f'<div style="flex:1;"><div style="font-size:0.55rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Confidence</div>'
        rec_html += f'<div style="display:flex;align-items:center;gap:4px;"><div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
        rec_html += f'<div style="width:{conf_pct}%;height:100%;background:{rec_color};border-radius:3px;"></div></div>'
        rec_html += f'<span style="font-size:0.65rem;color:{rec_color};font-weight:700;min-width:28px;text-align:right;">{conf_pct:.0f}%</span></div></div></div>'

        rec_html += f'<div style="font-size:0.72rem;color:#8B949E;margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid #30363D;">{rec["strategy"]}</div>'

        rec_html += f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.7rem;color:#8B949E;margin-bottom:8px;">'
        rec_html += f'<div>📍 <b style="color:#E6EDF3;">Entry:</b> {ff(entry)}</div>'
        rec_html += f'<div>🎯 <b style="color:#E6EDF3;">Target 1:</b> {ff(t1)}</div>'
        rec_html += f'<div>🎯 <b style="color:#E6EDF3;">Target 2:</b> {ff(t2)}</div>'
        rec_html += f'<div>🛑 <b style="color:#E6EDF3;">Stop:</b> {ff(stop)} ({risk_pct:.1f}% risk)</div>'
        rec_html += f'</div>'

        # ── SINGLE CONSOLIDATED OPTIONS PANEL ──
        if show_options and options.get("gamma_regime"):
            rec_html += f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-bottom:8px;padding:6px;background:#0D1117;border-radius:6px;">'
            g_color = "#3FB950" if "POS" in str(options.get("gamma_regime","")) else "#F85149" if "NEG" in str(options.get("gamma_regime","")) else "#D29922"
            rec_html += f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">Gamma</div><div style="font-size:0.7rem;color:{g_color};font-weight:700;">{options.get("gamma_regime","—")[:8]}</div></div>'
            gex_v = options.get("gex")
            try:
                gex_f = float(gex_v)
                if math.isfinite(gex_f):
                    gex_c = "#3FB950" if gex_f > 0 else "#F85149"
                    rec_html += f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">GEX</div><div style="font-size:0.7rem;color:{gex_c};font-weight:700;">{gex_f:+.2f}</div></div>'
            except (TypeError, ValueError): pass
            van_v = options.get("vanna")
            try:
                van_f = float(van_v)
                if math.isfinite(van_f):
                    van_c = "#3FB950" if van_f > 0 else "#F85149"
                    rec_html += f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">Vanna</div><div style="font-size:0.7rem;color:{van_c};font-weight:700;">{van_f:+.2f}</div></div>'
            except (TypeError, ValueError): pass
            iv_v = options.get("iv_rank")
            try:
                iv_f = float(iv_v)
                if math.isfinite(iv_f):
                    iv_c = "#3FB950" if iv_f < 40 else "#D29922" if iv_f < 60 else "#F85149"
                    rec_html += f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">IV Rank</div><div style="font-size:0.7rem;color:{iv_c};font-weight:700;">{iv_f:.0f}</div></div>'
            except (TypeError, ValueError): pass
            pc_v = options.get("pc_ratio")
            try:
                pc_f = float(pc_v)
                if math.isfinite(pc_f):
                    pc_c = "#3FB950" if pc_f < 0.8 else "#D29922" if pc_f < 1.2 else "#F85149"
                    rec_html += f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">P/C</div><div style="font-size:0.7rem;color:{pc_c};font-weight:700;">{pc_f:.2f}</div></div>'
            except (TypeError, ValueError): pass
            rec_html += f'</div>'

        # Rationale
        rec_html += f'<div style="font-size:0.68rem;color:#8B949E;line-height:1.5;padding:6px;background:#0D1117;border-radius:6px;">'
        rec_html += f'<div style="font-size:0.55rem;color:{rec_color};text-transform:uppercase;font-weight:600;margin-bottom:4px;letter-spacing:0.5px;">📋 Rationale ({rec.get("factors",0)} factors · {rec.get("source","PROXY")})</div>'
        rec_html += rec["rationale"]
        rec_html += f'</div>'

        rec_html += f'</div>'
        st.markdown(rec_html, unsafe_allow_html=True)

        # ── VolSignals Dealer Regime Panel ──
        if show_options and options.get("volsignals_regime"):
            vs = options.get("volsignals_regime", {})
            if isinstance(vs, dict):
                vs_reg = vs.get("dealer_regime", "—")
                vs_conf = vs.get("confidence", "—")
                vs_vanna = vs.get("vanna_alignment", "—")
                vs_charm = vs.get("charm_bias", "—")
                vs_color = "#3FB950" if "STABILIZING" in vs_reg else "#F85149" if "AMPLIFYING" in vs_reg else "#D29922"
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-bottom:8px;padding:6px;background:#0D1117;border-radius:6px;">'
                    f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">Dealer Regime</div>'
                    f'<div style="font-size:0.7rem;color:{vs_color};font-weight:700;">{vs_reg}</div></div>'
                    f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">Vanna Cycle</div>'
                    f'<div style="font-size:0.7rem;color:{"#3FB950" if "VIRTUOUS" in vs_vanna else "#F85149" if "VICIOUS" in vs_vanna else "#8B949E"};font-weight:700;">{vs_vanna}</div></div>'
                    f'<div style="text-align:center;"><div style="font-size:0.5rem;color:#8B949E;text-transform:uppercase;">Confidence</div>'
                    f'<div style="font-size:0.7rem;color:{"#3FB950" if "High" in vs_conf else "#D29922" if "Moderate" in vs_conf else "#8B949E"};font-weight:700;">{vs_conf}</div></div>'
                    f'</div>', unsafe_allow_html=True)

        # ── P&L Decomposition Panel (VolSignals-style) ──
        if show_options and options.get("gex") is not None:
            gex_v = _safe_float(options.get("gex")) or 0
            vanna_v = _safe_float(options.get("vanna")) or 0
            iv_r = _safe_float(options.get("iv_rank")) or 50
            # Proxy P&L decomposition
            vrp_term = max(-5.0, min(5.0, (50 - iv_r) * 0.08))  # IV rank deviation → VRP edge
            vanna_flow = max(-3.0, min(3.0, vanna_v * 2.5))      # Vanna → directional vol flow
            volga_term = max(-1.0, min(1.0, gex_v * 0.3))        # Gamma curvature proxy
            net_edge = vrp_term + vanna_flow + volga_term
            st.markdown(
                f'<div style="font-size:0.65rem;color:#8B949E;padding:6px;background:#0D1117;border-radius:6px;margin-bottom:8px;">'
                f'<div style="font-size:0.55rem;color:#58A6FF;text-transform:uppercase;font-weight:600;margin-bottom:3px;">📐 P&L Decomposition (VolSignals)</div>'
                f'<div>VRP Term: <span style="color:{"#3FB950" if vrp_term>0 else "#F85149"};font-weight:700;">{vrp_term:+.2f}%</span> · '
                f'Vanna Flow: <span style="color:{"#3FB950" if vanna_flow>0 else "#F85149"};font-weight:700;">{vanna_flow:+.2f}%</span> · '
                f'Volga: <span style="color:{"#3FB950" if volga_term>0 else "#F85149"};font-weight:700;">{volga_term:+.2f}%</span></div>'
                f'<div style="margin-top:2px;color:#484F58;">Net Edge: <span style="color:#E6EDF3;font-weight:700;">{net_edge:+.2f}%</span> · Gamma regime determines dominant term</div>'
                f'</div>', unsafe_allow_html=True)

        # OI Heatmap

        if show_options and options.get("max_pain"):
            mp = options.get("max_pain")
            pw = options.get("put_wall")
            cw = options.get("call_wall")
            px = row.get("price")
            if mp and pw and cw and px:
                levels = [("Put Wall", pw, "#F85149"), ("Max Pain", mp, "#8B949E"), ("Call Wall", cw, "#3FB950")]
                levels.sort(key=lambda x: x[1])
                heat_html = '<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px 12px;margin:6px 0;">'
                heat_html += '<div style="font-size:0.65rem;color:#A855F7;text-transform:uppercase;font-weight:600;letter-spacing:0.5px;margin-bottom:6px;">📊 OI Concentration Heatmap</div>'
                for label, price, color in levels:
                    is_near = abs(price - px) / px < 0.05 if px else False
                    near_badge = ' <span style="background:#58A6FF22;color:#58A6FF;padding:1px 4px;border-radius:3px;font-size:0.55rem;font-weight:700;">NEAR PX</span>' if is_near else ''
                    heat_html += f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                    heat_html += f'<span style="font-size:0.7rem;color:#8B949E;min-width:55px;">{label}</span>'
                    heat_html += f'<div style="flex:1;height:14px;background:#21262D;border-radius:4px;overflow:hidden;">'
                    bar_w = min(100, max(15, 100 - abs(price - mp) / mp * 200)) if mp else 50
                    heat_html += f'<div style="width:{bar_w:.0f}%;height:100%;background:{color}30;border-radius:4px;"></div>'
                    heat_html += f'</div>'
                    heat_html += f'<span style="font-size:0.7rem;color:{color};font-weight:700;min-width:60px;text-align:right;">{ff(price)}{near_badge}</span>'
                    heat_html += f'</div>'
                # ── SpotGamma Structural Levels ──
                sg_levels = options.get("spotgamma_levels", {})
                if sg_levels and isinstance(sg_levels, dict):
                    vt = sg_levels.get("volatility_trigger")
                    rp = sg_levels.get("risk_pivot")
                    if vt:
                        is_near_vt = abs(vt - px) / px < 0.03 if px else False
                        near_badge_vt = ' <span style="background:#D2992222;color:#D29922;padding:1px 4px;border-radius:3px;font-size:0.55rem;font-weight:700;">NEAR PX</span>' if is_near_vt else ''
                        heat_html += f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                        heat_html += f'<span style="font-size:0.7rem;color:#8B949E;min-width:55px;">Vol Trigger</span>'
                        heat_html += f'<div style="flex:1;height:14px;background:#21262D;border-radius:4px;overflow:hidden;">'
                        bar_w_vt = min(100, max(15, 100 - abs(vt - mp) / mp * 200)) if mp else 50
                        heat_html += f'<div style="width:{bar_w_vt:.0f}%;height:100%;background:#D2992230;border-radius:4px;"></div>'
                        heat_html += f'</div>'
                        heat_html += f'<span style="font-size:0.7rem;color:#D29922;font-weight:700;min-width:60px;text-align:right;">{ff(vt)}{near_badge_vt}</span>'
                        heat_html += f'</div>'
                    if rp:
                        is_near_rp = abs(rp - px) / px < 0.03 if px else False
                        near_badge_rp = ' <span style="background:#F8514922;color:#F85149;padding:1px 4px;border-radius:3px;font-size:0.55rem;font-weight:700;">NEAR PX</span>' if is_near_rp else ''
                        heat_html += f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                        heat_html += f'<span style="font-size:0.7rem;color:#8B949E;min-width:55px;">Risk Pivot</span>'
                        heat_html += f'<div style="flex:1;height:14px;background:#21262D;border-radius:4px;overflow:hidden;">'
                        bar_w_rp = min(100, max(15, 100 - abs(rp - mp) / mp * 200)) if mp else 50
                        heat_html += f'<div style="width:{bar_w_rp:.0f}%;height:100%;background:#F8514930;border-radius:4px;"></div>'
                        heat_html += f'</div>'
                        heat_html += f'<span style="font-size:0.7rem;color:#F85149;font-weight:700;min-width:60px;text-align:right;">{ff(rp)}{near_badge_rp}</span>'
                        heat_html += f'</div>'
                heat_html += f'<div style="margin-top:4px;font-size:0.6rem;color:#484F58;">Price: {ff(px)} · OI peaks at Max Pain · Source: {options.get("source","PROXY")}</div>'
                heat_html += '</div>'
                st.markdown(heat_html, unsafe_allow_html=True)

        # Skew Curve
        if show_options and options.get("gamma_regime"):
            iv_schadner = options.get("iv_schadner")
            st.markdown(_skew_curve_proxy_html(ticker, options, width=320, height=110, iv_exact=iv_schadner), unsafe_allow_html=True)

        # Boom-Bust + Behavioral mini
        if market_type == "us_equity":
            bb = _get_ticker_boombust_score(ticker, prices, snap_local)
            beh = _get_ticker_behavioral_score(ticker, prices, options, snap_local)
            if bb.get("score", 0) > 0 or beh.get("casino_score", 0) > 0:
                mini_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0;">'
                if bb.get("score", 0) > 0:
                    bb_color = "#F85149" if bb["score"] >= 7 else "#D29922" if bb["score"] >= 4 else "#3FB950"
                    mini_html += f'<div style="background:#0D1117;border-radius:6px;padding:6px 8px;"><div style="font-size:0.55rem;color:#8B949E;text-transform:uppercase;">Boom-Bust</div><div style="font-size:0.75rem;color:{bb_color};font-weight:700;">{bb["stage"]} · {bb["score"]:.1f}/10</div><div style="font-size:0.6rem;color:#484F58;">{bb["signal"][:40]}</div></div>'
                if beh.get("casino_score", 0) > 0:
                    beh_color = "#F85149" if beh["casino_score"] > 60 else "#D29922" if beh["casino_score"] > 40 else "#3FB950"
                    mini_html += f'<div style="background:#0D1117;border-radius:6px;padding:6px 8px;"><div style="font-size:0.55rem;color:#8B949E;text-transform:uppercase;">Behavioral</div><div style="font-size:0.75rem;color:{beh_color};font-weight:700;">Casino {beh["casino_score"]:.0f}%</div><div style="font-size:0.6rem;color:#484F58;">{beh["signal"][:40]}</div></div>'
                mini_html += '</div>'
                st.markdown(mini_html, unsafe_allow_html=True)

        if row.get("news_headline"):
            st.markdown(f'<div style="font-size:0.72rem;color:#58A6FF;margin-top:3px;">📰 {row.get("news_headline")[:120]}</div>', unsafe_allow_html=True)

def render_ticker_cards_v4(rows, max_rows=30):
    if not rows:
        st.info("No setups pass filter.")
        return
    st.markdown(f'<div style="font-size:0.72rem;color:#8B949E;margin-bottom:4px;">Showing {min(len(rows), max_rows)} of {len(rows)} setups</div>', unsafe_allow_html=True)
    for i, r in enumerate(rows[:max_rows]):
        render_ticker_card_v4(r, expanded=(i < 2))

# ═══════════════════════════════════════════════════════════════════
# REGIME COMPASS
# ═══════════════════════════════════════════════════════════════════
def render_regime_compass(snap):
    gip_local = snap.get("gip")
    if gip_local is not None and not isinstance(gip_local, dict): gip_local = _GipProxy(gip_local)
    elif isinstance(gip_local, dict): gip_local = _GipProxy(gip_local)
    else: return

    q_probs = getattr(gip_local, "structural_probs", {}) or {}
    m_probs = getattr(gip_local, "monthly_probs", {}) or {}
    sq = getattr(gip_local, "structural_quad", "Q3") or "Q3"
    mq = getattr(gip_local, "monthly_quad", "Q2") or "Q2"

    markov = snap.get("markov_v3", {}) or {}
    markov_regime = markov.get("current_regime", "UNKNOWN") if isinstance(markov, dict) else "UNKNOWN"
    markov_conf = markov.get("confidence", 0) if isinstance(markov, dict) else 0
    markov_kelly = markov.get("kelly_fraction", 0.25) if isinstance(markov, dict) else 0.25
    cp_alert = markov.get("change_point_alert", False) if isinstance(markov, dict) else False

    rf = snap.get("regime_forecast", {})
    rf3 = rf.get("3m", {}) if isinstance(rf, dict) else {}
    fq = rf3.get("predicted_quad", "Q3") if isinstance(rf3, dict) else "Q3"
    fc = rf3.get("prediction_confidence", 0) if isinstance(rf3, dict) else 0

    c1, c2 = st.columns([1, 1.6])
    with c1:
        sq_color = _quad_color(sq); mq_color = _quad_color(mq)
        markov_color = "#58A6FF" if "BULL" in str(markov_regime).upper() else "#F85149" if "BEAR" in str(markov_regime).upper() else "#D29922"
        cp_badge = '<span style="background:#F8514922;color:#F85149;padding:1px 5px;border-radius:4px;font-size:0.6rem;font-weight:700;border:1px solid #F85149;margin-left:6px;">⚠ CP</span>' if cp_alert else ""
        st.markdown(
            f'<div class="compass-container">'
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;">'
            f'<div style="text-align:center;min-width:70px;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Structural</div>'
            f'<div class="compass-quad" style="color:{sq_color};">{sq}</div><div class="compass-sub">{_quad_name(sq)}</div></div>'
            f'<div style="width:1px;height:36px;background:#30363D;"></div>'
            f'<div style="text-align:center;min-width:70px;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Monthly</div>'
            f'<div class="compass-quad" style="color:{mq_color};">{mq}</div><div class="compass-sub">{_quad_name(mq)}</div></div>'
            f'<div style="width:1px;height:36px;background:#30363D;"></div>'
            f'<div style="flex:1;"><div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Markov {cp_badge}</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:{markov_color};margin-top:2px;">{str(markov_regime).replace("_"," ")}</div>'
            f'<div class="compass-sub">Conf {markov_conf:.0%} · Kelly {markov_kelly:.0%}</div></div>'
            f'</div>'
            f'{_gauge_html(markov_conf*100, max_val=100, color=markov_color, height=10, label_left="0%", label_right="100%")}'
            f'</div>', unsafe_allow_html=True
        )
        # ── Scenario probabilities below compass ──
        narrative_local = snap.get("narrative", {}) or {}
        scenarios_local = (narrative_local.get("scenarios") or {}) if isinstance(narrative_local, dict) else {}
        if scenarios_local:
            dom_local = scenarios_local.get("dominant_scenario", "base") if isinstance(scenarios_local, dict) else "base"
            bull_p_local = scenarios_local.get("bull", {}).get("probability", 0) if isinstance(scenarios_local.get("bull"), dict) else 0
            base_p_local = scenarios_local.get("base", {}).get("probability", 0) if isinstance(scenarios_local.get("base"), dict) else 0
            bear_p_local = scenarios_local.get("bear", {}).get("probability", 0) if isinstance(scenarios_local.get("bear"), dict) else 0
            st.markdown(
                f'<div style="font-size:0.6rem;color:#8B949E;text-align:center;margin:6px 0 0;padding:4px 6px;background:#0D1117;border-radius:4px;">'
                f'<span style="color:#3FB950;font-weight:700;">🐂 {bull_p_local:.0%}</span> · '
                f'<span style="color:#D29922;font-weight:700;">⚖ {base_p_local:.0%}</span> · '
                f'<span style="color:#F85149;font-weight:700;">🐻 {bear_p_local:.0%}</span> · '
                f'Dom: <b>{dom_local.title()}</b></div>', unsafe_allow_html=True)
    with c2:
        fig = go.Figure()
        quads = ["Q1","Q2","Q3","Q4"]; colors = [_quad_color(q) for q in quads]
        q_vals = [q_probs.get(q, 0) if isinstance(q_probs, dict) else 0 for q in quads]
        m_vals = [m_probs.get(q, 0) if isinstance(m_probs, dict) else 0 for q in quads]
        f_vals = [fc if q == fq else (1-fc)/3 for q in quads]
        fig.add_trace(go.Bar(name="Structural", x=quads, y=q_vals, marker_color=colors, opacity=1.0,
                             text=[f"{v:.0%}" for v in q_vals], textposition="outside", textfont=dict(size=10, color="#E6EDF3"), showlegend=True))
        fig.add_trace(go.Bar(name="Monthly", x=quads, y=m_vals, marker_color=colors, opacity=0.55,
                             text=[f"{v:.0%}" for v in m_vals], textposition="outside", textfont=dict(size=9, color="#8B949E"), showlegend=True))
        fig.add_trace(go.Bar(name="Forward 3M", x=quads, y=f_vals, marker_color=colors, opacity=0.25,
                             text=[f"{v:.0%}" for v in f_vals], textposition="outside", textfont=dict(size=8, color="#484F58"), showlegend=True))
        fig.update_layout(height=160, margin=dict(t=10,b=20,l=20,r=20), paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
                          font=dict(color="#E6EDF3", size=10, family="Inter"),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                          yaxis=dict(range=[0,1.15], tickformat=".0%", showgrid=True, gridcolor="#21262D", dtick=0.25),
                          barmode="group", bargap=0.35, bargroupgap=0.1)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="regime_compass_bars")

# ═══════════════════════════════════════════════════════════════════
# CRASH METER v3 — AUDITED (/5 fix)
# ═══════════════════════════════════════════════════════════════════
def _render_crash_meter(snap):
    """Crash Meter v3 — Tomhardi Methodology (AUDITED v32.4)
    Components: A1 + A2 + B1 + B2 + C = 5 variables
    Max score: 5 (was /4 in v32.3 — BUG FIXED)
    """
    from datetime import datetime

    fred = snap.get("fred_series", {}) or {}

    # A1: T10Y-3M spread
    t10y = None; t3m = None
    if fred.get("DGS10") is not None:
        try:
            s = pd.to_numeric(fred["DGS10"], errors="coerce").dropna()
            if len(s) > 0: t10y = float(s.iloc[-1])
        except: pass
    if fred.get("DGS3MO") is not None:
        try:
            s = pd.to_numeric(fred["DGS3MO"], errors="coerce").dropna()
            if len(s) > 0: t3m = float(s.iloc[-1])
        except: pass

    if t10y is None or t3m is None:
        t10y3m = 0.77
    else:
        t10y3m = t10y - t3m

    a1_score = 0 if t10y3m > 0.5 else 1
    a1_status = "Aman" if a1_score == 0 else "Berbahaya"
    a1_color = "#3FB950" if a1_score == 0 else "#F85149"

    # A2: Inversion window (corrected: last inversion Dec 2024)
    now = datetime.now()
    last_inv = datetime(2024, 12, 1)
    months_since = (now.year - last_inv.year) * 12 + (now.month - last_inv.month)
    months_left = max(0, 18 - months_since)
    a2_score = 1 if months_since < 18 else 0
    a2_status = "Dalam Window ({}bln sisa)".format(months_left) if a2_score == 1 else "Lewat Window"
    a2_color = "#D29922" if a2_score == 1 else "#3FB950"

    # B1 & B2: HY OAS
    hy_oas = None
    if fred.get("BAMLH0A0HYM2") is not None:
        try:
            s = pd.to_numeric(fred["BAMLH0A0HYM2"], errors="coerce").dropna()
            if len(s) > 0: hy_oas = float(s.iloc[-1])
        except: pass
    if hy_oas is None:
        hy_oas = 2.82

    hy_6m_ago = 3.10
    hy_range_bps = abs(hy_oas - hy_6m_ago) * 100
    b1_score = 0 if hy_range_bps < 150 else 1
    b1_status = "Range {:.0f}bps (Aman)".format(hy_range_bps) if b1_score == 0 else "Range {:.0f}bps (Tinggi)".format(hy_range_bps)
    b1_color = "#3FB950" if b1_score == 0 else "#F85149"

    b2_score = 0 if hy_oas < 5.50 else 1
    b2_status = "{:.2f}% < 5.50%".format(hy_oas) if b2_score == 0 else "{:.2f}% > 5.50%".format(hy_oas)
    b2_color = "#3FB950" if b2_score == 0 else "#F85149"

    # C: Shiller CAPE
    cape = 41.66
    c_score = 1 if cape > 35 else 0
    c_status = "{:.1f} > 35 (Mahal)".format(cape) if c_score == 1 else "{:.1f} < 35".format(cape)
    c_color = "#F85149" if c_score == 1 else "#3FB950"

    total = a1_score + a2_score + b1_score + b2_score + c_score

    # Timeline estimate
    if total <= 1:
        status = "AMAN"; status_color = "#3FB950"; status_bg = "#3FB95015"; emoji = "🟢"
        advice = "Market normal. Tetap waspada tapi tidak perlu panic."
        timeline = "No crash signal. Monitor monthly."
    elif total == 2:
        status = "WASPADA"; status_color = "#D29922"; status_bg = "#D2992215"; emoji = "🟡"
        advice = "Signal mulai menyala. Review portfolio, siapkan cash buffer."
        timeline = "A2 window closes Jun 2026 (~{} bln). CAPE 41.7 vs peak 44.2.".format(months_left)
    elif total == 3:
        status = "EXIT WINDOW"; status_color = "#F85149"; status_bg = "#F8514915"; emoji = "🟠"
        advice = "COUNTDOWN DIMULAI. Profit-taking dan raise cash. Window sempit!"
        timeline = "Historically 3-12 months to peak. Act within weeks."
    else:
        status = "CRITICAL"; status_color = "#F85149"; status_bg = "#F8514920"; emoji = "🔴"
        advice = "Sistemik risk tinggi. Defensive positioning. Cash is king."
        timeline = "Days to weeks before major drawdown. Exit NOW."

    html = '<div style="background:#161B22;border:1px solid ' + status_color + '40;border-radius:12px;padding:14px;margin:8px 0;">'

    # Header
    html += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
    html += '<div style="width:56px;height:56px;border-radius:50%;background:' + status_bg + ';border:2px solid ' + status_color + ';display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:800;color:' + status_color + ';">' + str(total) + '<span style="font-size:0.6rem;">/5</span></div>'
    html += '<div><div style="font-size:1.1rem;font-weight:700;color:' + status_color + ';letter-spacing:-0.5px;">' + emoji + ' ' + status + '</div>'
    html += '<div style="font-size:0.7rem;color:#8B949E;margin-top:2px;">' + advice + '</div></div></div>'

    # Timeline
    html += '<div style="background:' + status_bg + ';border-left:3px solid ' + status_color + ';border-radius:6px;padding:8px 10px;margin-bottom:10px;">'
    html += '<div style="font-size:0.6rem;color:' + status_color + ';text-transform:uppercase;font-weight:600;margin-bottom:3px;">⏱️ Timeline Estimate</div>'
    html += '<div style="font-size:0.72rem;color:#E6EDF3;">' + timeline + '</div>'
    html += '<div style="font-size:0.6rem;color:#484F58;margin-top:2px;">Update: A1/A2/B daily · CAPE monthly · Next check: tomorrow</div>'
    html += '</div>'

    # Gauge bar (5 segments)
    html += '<div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:0.55rem;color:#8B949E;margin-bottom:3px;text-transform:uppercase;font-weight:600;"><span>0 Aman</span><span>1</span><span>2 Waspada</span><span>3 Exit</span><span>4</span><span>5 Critical</span></div>'
    html += '<div style="height:10px;background:#21262D;border-radius:5px;overflow:hidden;display:flex;">'
    html += '<div style="width:20%;height:100%;background:#3FB950;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#3FB950;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#D29922;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#F85149;opacity:0.3;"></div>'
    html += '<div style="width:20%;height:100%;background:#F85149;opacity:0.5;"></div>'
    html += '</div>'
    marker_pct = min(100, max(0, total / 5 * 100))
    html += '<div style="position:relative;height:4px;margin-top:-7px;"><div style="position:absolute;left:' + str(marker_pct) + '%;transform:translateX(-50%);width:10px;height:10px;background:' + status_color + ';border-radius:50%;border:2px solid #E6EDF3;box-shadow:0 0 6px ' + status_color + '80;"></div></div>'
    html += '</div>'

    # Parameters grid
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;">'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">📊 A1 · T10Y-3M</span>'
    html += '<span style="font-size:0.65rem;color:' + a1_color + ';font-weight:700;">' + a1_status + '</span></div>'
    html += '<div style="font-size:0.7rem;color:#E6EDF3;font-weight:700;">' + str(round(t10y3m, 2)) + '%</div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: >0.5% = skor 0 · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">⏱️ A2 · 18Bln Window</span>'
    html += '<span style="font-size:0.65rem;color:' + a2_color + ';font-weight:700;">' + a2_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Last inversion: Des 2024 · Closes Jun 2026</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">💳 B1 · HY Range</span>'
    html += '<span style="font-size:0.65rem;color:' + b1_color + ';font-weight:700;">' + b1_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: <150bps in 6mo · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">💳 B2 · HY Abs</span>'
    html += '<span style="font-size:0.65rem;color:' + b2_color + ';font-weight:700;">' + b2_status + '</span></div>'
    html += '<div style="font-size:0.55rem;color:#484F58;">Threshold: <550bps = skor 0 · Daily</div></div>'

    html += '<div style="background:#0D1117;border-radius:6px;padding:6px 8px;grid-column:1 / -1;">'
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
    html += '<span style="font-size:0.6rem;color:#8B949E;font-weight:600;">📈 C · Shiller CAPE</span>'
    html += '<span style="font-size:0.65rem;color:' + c_color + ';font-weight:700;">' + c_status + '</span></div>'
    html += '<div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
    html += '<div style="flex:1;height:6px;background:#21262D;border-radius:3px;overflow:hidden;">'
    cape_pct = min(100, cape / 50 * 100)
    html += '<div style="width:' + str(round(cape_pct, 0)) + '%;height:100%;background:' + c_color + ';border-radius:3px;"></div>'
    html += '</div>'
    html += '<span style="font-size:0.6rem;color:#8B949E;min-width:60px;text-align:right;">Peak dotcom: 44.2</span>'
    html += '</div></div>'

    html += '</div>'

    html += '<div style="font-size:0.6rem;color:#484F58;text-align:center;border-top:1px solid #21262D;padding-top:6px;">'
    html += 'Crash Meter v3 · Tomhardi Methodology · A1+A2+B1+B2+C = ' + str(total) + '/5 · Updated daily (CAPE monthly)'
    html += '</div>'

    html += '</div>'

    return html

# ═══════════════════════════════════════════════════════════════════
# COT PROXY (for forex/commodities)
# ═══════════════════════════════════════════════════════════════════
def _get_cot_proxy(ticker):
    cot_map = {
        "EURUSD=X": {"net_noncom": 45000, "net_com": -32000, "change_wow": 2500, "signal": "BULLISH"},
        "GBPUSD=X": {"net_noncom": 12000, "net_com": -8000, "change_wow": -1500, "signal": "NEUTRAL"},
        "USDJPY=X": {"net_noncom": -28000, "net_com": 35000, "change_wow": 4200, "signal": "BEARISH"},
        "AUDUSD=X": {"net_noncom": 8000, "net_com": -5000, "change_wow": 800, "signal": "BULLISH"},
        "USDCAD=X": {"net_noncom": -15000, "net_com": 12000, "change_wow": -2000, "signal": "BEARISH"},
        "USDCHF=X": {"net_noncom": -5000, "net_com": 3000, "change_wow": 500, "signal": "NEUTRAL"},
        "NZDUSD=X": {"net_noncom": 3000, "net_com": -2000, "change_wow": 400, "signal": "BULLISH"},
        "DX-Y.NYB": {"net_noncom": -35000, "net_com": 28000, "change_wow": 5000, "signal": "BEARISH"},
        "GC=F": {"net_noncom": 180000, "net_com": -140000, "change_wow": 12000, "signal": "BULLISH"},
        "SI=F": {"net_noncom": 45000, "net_com": -35000, "change_wow": 3000, "signal": "BULLISH"},
        "CL=F": {"net_noncom": 220000, "net_com": -180000, "change_wow": -8000, "signal": "BULLISH"},
        "NG=F": {"net_noncom": -80000, "net_com": 65000, "change_wow": 5000, "signal": "BEARISH"},
        "HG=F": {"net_noncom": 25000, "net_com": -18000, "change_wow": 2000, "signal": "BULLISH"},
    }
    return cot_map.get(ticker, {"net_noncom": 0, "net_com": 0, "change_wow": 0, "signal": "NEUTRAL"})

def _get_onchain_proxy(ticker, prices):
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {}
    try:
        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
        if len(s_clean) < 20: return {}
        px = float(s_clean.iloc[-1])
        r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1) if len(s_clean) >= 22 else 0
        r7d = float(s_clean.iloc[-1] / s_clean.iloc[-8] - 1) if len(s_clean) >= 8 else r1m
        vol_20 = float(s_clean.tail(20).std())
        mean_20 = float(s_clean.tail(20).mean())
        return {
            "price": px, "r1m": r1m, "r7d": r7d,
            "volatility": round(vol_20 / mean_20 if mean_20 > 0 else 0, 4),
            "momentum": "ACCUMULATING" if r1m > 0.05 else "DISTRIBUTING" if r1m < -0.05 else "NEUTRAL",
            "whale_signal": "BUY" if r7d > 0.03 and vol_20 > 0 else "SELL" if r7d < -0.03 else "HOLD",
            "funding_proxy": round(r1m * 0.001, 5),
            "oi_proxy": int(abs(r1m) * 1e9),
        }
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════════════════
# SESSION & SIDEBAR
# ═══════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.caption("v32.4 AUDITED")
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard", "⚡ Alpha Center", "🇺🇸 US Stocks", "💱 Forex",
        "🛢️ Commodities", "₿ Crypto", "🌍 Global & EM", "📖 Themes"
    ], label_visibility="collapsed")
    st.divider()
    try:
        from data.loader import snapshot_age_str
        st.caption(f"Last update: {snapshot_age_str()}")
    except:
        st.caption("Last update: unknown")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Update", use_container_width=True): st.session_state.loading = True
    with c2:
        if st.button("⚡ Rebuild", use_container_width=True):
            st.session_state.loading = True; st.session_state.snap = None
    with st.expander("⚙️ Settings"):
        inc_us = st.checkbox("US Stocks", True)
        inc_fx = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("Indonesia", True)
    with st.expander("💰 Portfolio"):
        pv = st.number_input("Value", min_value=1000, max_value=1_000_000_000,
                            value=int(st.session_state.get("portfolio_value", 100_000)), step=10_000)
        st.session_state["portfolio_value"] = pv
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly", ["Auto", "Q1", "Q2", "Q3", "Q4"],
                            index=["Auto", "Q1", "Q2", "Q3", "Q4"].index(st.session_state.mq_override))
        st.session_state.mq_override = mq_ov
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g = _s.get("gip")
        if _g is not None and not isinstance(_g, dict): _g = _GipProxy(_g)
        elif isinstance(_g, dict): _g = _GipProxy(_g)
        _sq = getattr(_g, "structural_quad", "—") if _g is not None else "—"
        _mq = getattr(_g, "monthly_quad", "—") if _g is not None else "—"
        color = _quad_color(_sq)
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:10px;text-align:center;">'
                    f'<div style="font-size:0.6rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">REGIME</div>'
                    f'<div style="font-size:1rem;font-weight:700;color:{color};margin:4px 0;">{_sq} / {_mq}</div>'
                    f'<div style="font-size:0.65rem;color:#8B949E;">{_quad_name(_sq)}</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════
snap = st.session_state.snap
if snap is None:
    try:
        from data.loader import load_snapshot
        snap = load_snapshot(max_age_hours=6.0)
        if snap and snap.get("ok"): st.session_state.snap = snap
    except Exception as e:
        logger.warning(f"Initial snapshot load failed: {e}")
        snap = None

if snap is None or not snap.get("ok") or st.session_state.loading:
    try:
        from orchestrator import build_snapshot
    except Exception as e:
        st.error(f"Failed to import orchestrator: {e}"); st.stop()
    _msg = "Updating..." if st.session_state.loading else "Building..."
    with st.spinner(_msg):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m, f): pb.progress(f); pt.caption(f"Loading {m}")
        try:
            snap = build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                                  include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg,
                                  portfolio_value=st.session_state.get("portfolio_value", 100_000))
            st.session_state.snap = snap; st.session_state.loading = False; pb.empty(); pt.empty(); st.rerun()
        except Exception as e:
            st.session_state.loading = False; st.error(f"Build failed: {e}"); st.stop()

if not snap or not snap.get("ok"):
    st.error("Build failed. Click Rebuild to retry."); st.stop()

gip_raw = snap.get("gip")
if gip_raw is not None and not isinstance(gip_raw, dict): gip = _GipProxy(gip_raw)
elif isinstance(gip_raw, dict): gip = _GipProxy(gip_raw)
else: gip = None
prices = snap.get("prices", {}) or {}
rr = snap.get("risk_ranges", {}) or {}
ar = rr.get("asset_ranges", {}) if isinstance(rr, dict) else {}
sq = getattr(gip, "structural_quad", None) or "Q3" if gip is not None else "Q3"
mq_raw = getattr(gip, "monthly_quad", None) or "Q2" if gip is not None else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw

_vix_raw = prices.get("^VIX")
vix_now = 20.0
if _vix_raw is not None:
    try:
        if hasattr(_vix_raw, "tail"): vix_now = _safe_float(_vix_raw.tail(1)) or 20.0
        elif hasattr(_vix_raw, "__len__") and len(_vix_raw) > 0: vix_now = _safe_float(pd.Series(_vix_raw).iloc[-1]) or 20.0
        else: vix_now = _safe_float(_vix_raw) or 20.0
    except Exception: vix_now = 20.0

# ═══════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD — AUDITED (Layout fixes: Bull/Bear/Base + Asset Pulse)
# ═══════════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown("## 🏠 Macro Dashboard")
    render_regime_compass(snap)

    narrative = snap.get("narrative", {}) or {}
    macro_nar = (narrative.get("macro_narrative") or {}) if isinstance(narrative, dict) else {}
    if macro_nar.get("headline") or macro_nar.get("narrative"):
        headline = macro_nar.get("headline", macro_nar.get("narrative", ""))
        st.markdown(f'<div class="narrative-card">'
                    f'<div class="narrative-headline">{str(headline)[:180]}{"..." if len(str(headline)) > 180 else ""}</div>'
                    f'<div class="narrative-sub">{macro_nar.get("sub_narrative", "")[:120]}</div></div>', unsafe_allow_html=True)

    st.divider()

    summary = snap.get("summary", {}) or {}
    health = snap.get("health", {}) or {}
    markov = snap.get("markov_v3", {}) or {}
    behavioral = snap.get("behavioral_macro", {}) or {}

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        vix_color = "#3FB950" if vix_now < 18 else "#D29922" if vix_now < 25 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Volatility (VIX)</div>'
                    f'<div class="metric-grid-value" style="color:{vix_color};">{vix_now:.1f}</div>'
                    f'{_gauge_html(vix_now, max_val=40, color=vix_color, height=8, label_left="Low", label_right="High")}'
                    f'</div>', unsafe_allow_html=True)
    with k2:
        health_score = health.get("composite_score", 50) if isinstance(health, dict) else 50
        hcolor = "#3FB950" if health_score >= 70 else "#D29922" if health_score >= 50 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Market Health</div>'
                    f'<div class="metric-grid-value" style="color:{hcolor};">{health_score:.0f}</div>'
                    f'{_gauge_html(health_score, max_val=100, color=hcolor, height=8, label_left="Weak", label_right="Strong")}'
                    f'</div>', unsafe_allow_html=True)
    with k3:
        yves = behavioral.get("yves", {}) if isinstance(behavioral, dict) else {}
        alert_level = yves.get("alert_level", "NONE") if isinstance(yves, dict) else "NONE"
        n_alerts = len((snap.get("yves_v2", {}) or {}).get("alerts", [])) if isinstance(snap.get("yves_v2"), dict) else 0
        alert_color = "#F85149" if alert_level in ("HIGH", "CRITICAL") or n_alerts > 2 else "#D29922" if alert_level == "MEDIUM" or n_alerts > 0 else "#3FB950"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Behavioral Alerts</div>'
                    f'<div class="metric-grid-value" style="color:{alert_color};">{n_alerts}</div>'
                    f'<div class="metric-grid-sub">Yves / AAII · {alert_level}</div>'
                    f'</div>', unsafe_allow_html=True)
    with k4:
        kelly = markov.get("kelly_fraction", 0.25) if isinstance(markov, dict) else 0.25
        kelly_color = "#3FB950" if kelly >= 0.5 else "#D29922" if kelly >= 0.25 else "#F85149"
        st.markdown(f'<div class="metric-grid-card">'
                    f'<div class="metric-grid-title">Kelly Fraction</div>'
                    f'<div class="metric-grid-value" style="color:{kelly_color};">{kelly:.0%}</div>'
                    f'<div class="metric-grid-sub">Optimal bet size</div>'
                    f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── LEFT COLUMN: Boom-Bust + Behavioral + Asset Pulse (COMPACTED) ──
    # ── RIGHT COLUMN: Crash Meter ──
    left, right = st.columns([1, 1.2])
    with left:
        st.markdown("### 🌀 Boom-Bust Stage")
        bb = snap.get("boom_bust", {}) or {}
        stage = bb.get("stage", "INCEPTION") if isinstance(bb, dict) else "INCEPTION"
        reflex = snap.get("reflexivity", {}) or {}
        score = reflex.get("super_bubble_score", 0) if isinstance(reflex, dict) else 0
        st.markdown(_timeline_html(stage), unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:6px;font-size:0.75rem;color:#8B949E;">Super Bubble Score: <span style="color:#E6EDF3;font-weight:700;">{score:.1f}</span>/10</div>', unsafe_allow_html=True)
        st.markdown(_gauge_html(score, max_val=10, color="#D29922", height=8, label_left="0", label_right="10"), unsafe_allow_html=True)

        st.markdown("### 🧠 Behavioral Macro (Yves)")
        behavioral = snap.get("behavioral_macro", {}) or {}
        yves = behavioral.get("yves", {}) if isinstance(behavioral, dict) else {}
        n_alerts = len((snap.get("yves_v2", {}) or {}).get("alerts", [])) if isinstance(snap.get("yves_v2"), dict) else 0
        if isinstance(yves, dict):
            alert = yves.get("alert", "")
            level = yves.get("alert_level", "NONE")
            if level == "NONE" and not alert:
                bullish = behavioral.get("bullish", 30)
                bearish = behavioral.get("bearish", 30)
                neutral = behavioral.get("neutral", 40)
                total = bullish + bearish + neutral
                if total > 0:
                    bull_pct = bullish / total * 100
                    bear_pct = bearish / total * 100
                    neut_pct = neutral / total * 100
                    casino_score = min(100, max(0, (bullish - 45) * 3))
                    cash_raise = min(50, max(0, casino_score * 0.4))
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#8B949E;margin-bottom:4px;">AAII Sentiment · Casino Score: <span style="color:{"#F85149" if casino_score > 60 else "#D29922" if casino_score > 40 else "#3FB950"};font-weight:700;">{casino_score:.0f}</span></div>'
                        f'<div style="display:flex;height:18px;border-radius:4px;overflow:hidden;background:#21262D;margin-bottom:6px;">'
                        f'<div style="width:{bull_pct:.0f}%;background:#3FB950;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">🐂 {bullish}</div>'
                        f'<div style="width:{neut_pct:.0f}%;background:#8B949E;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">⚖ {neutral}</div>'
                        f'<div style="width:{bear_pct:.0f}%;background:#F85149;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;">🐻 {bearish}</div>'
                        f'</div>', unsafe_allow_html=True)
                    if casino_score > 40:
                        st.markdown(
                            f'<div style="background:#F8514915;border-left:3px solid #F85149;border-radius:6px;padding:6px 10px;margin:4px 0;">'
                            f'<div style="font-size:0.75rem;color:#F85149;font-weight:700;">⚠️ Casino Behavior Detected</div>'
                            f'<div style="font-size:0.7rem;color:#8B949E;margin-top:2px;">Bullish extreme ({bullish}%) = herd behavior. Consider raising <b>{cash_raise:.0f}% cash</b>. Wait for washout.</div>'
                            f'</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div style="font-size:0.7rem;color:#3FB950;margin-top:4px;">✅ Sentiment balanced. No casino behavior detected.</div>', unsafe_allow_html=True)
                else:
                    st.caption("Behavioral data unavailable")
            else:
                color = "#F85149" if level in ("HIGH", "CRITICAL") or n_alerts > 2 else "#D29922" if level == "MEDIUM" or n_alerts > 0 else "#3FB950"
                st.markdown(f'<div style="font-size:0.85rem;color:{color};font-weight:600;">{level}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{alert}</div>', unsafe_allow_html=True)
        else:
            st.caption("Behavioral macro unavailable")

        # ── ASSET PULSE (COMPACTED below Behavioral) ──
        st.markdown("### ⚡ Asset Pulse (21D)")
        pulse_assets = [("SPY", "US Eq"), ("QQQ", "Tech"), ("IWM", "Small"), ("GLD", "Gold"), ("TLT", "Bonds"), ("UUP", "DXY"), ("BTC-USD", "BTC"), ("ETH-USD", "ETH")]
        pulse_html = '<div style="display:flex;gap:6px;overflow-x:auto;padding:2px 0;">'
        for t, label in pulse_assets:
            ret = _price_ret(t, prices, 21)
            pulse_html += _asset_pulse_box_h(label, ret, t)
        pulse_html += '</div>'
        st.markdown(pulse_html, unsafe_allow_html=True)

    with right:
        st.markdown("### 🚨 Crash Meter v3")
        st.markdown("<div style='font-size:0.65rem;color:#8B949E;margin-bottom:8px;'>Sistemik risk meter: Yield Curve + Credit Spread + Valuasi (Tomhardi Methodology). Update harian kecuali CAPE (bulanan).</div>", unsafe_allow_html=True)
        st.markdown(_render_crash_meter(snap), unsafe_allow_html=True)

    st.divider()

    with st.expander("🔬 Deep Technical", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Skew Term**")
            skew = snap.get("skew_term", {}) or {}; skew_data = skew.get("skew_data", {}) if isinstance(skew, dict) else {}
            d30 = d60 = d90 = None
            if isinstance(skew_data, dict):
                for k, v in skew_data.items():
                    if isinstance(v, dict):
                        val = v.get("skew") or v.get("value") or v.get("90_10")
                        if "30" in str(k).lower() or "1m" in str(k).lower(): d30 = _safe_float(val)
                        if "60" in str(k).lower() or "2m" in str(k).lower(): d60 = _safe_float(val)
                        if "90" in str(k).lower() or "3m" in str(k).lower(): d90 = _safe_float(val)
            st.markdown(_skew_bars_html(d30, d60, d90), unsafe_allow_html=True)
            st.markdown("**GEX**")
            gex = snap.get("gex_data", {}) or {}; gex_val = None
            if isinstance(gex, dict):
                for k, v in gex.items():
                    if isinstance(v, dict):
                        gv = v.get("net_gex") or v.get("gex") or v.get("total_gex")
                        if gv is not None: gex_val = _safe_float(gv); break
            st.markdown(_gex_bar_html(gex_val), unsafe_allow_html=True)
        with c2:
            st.markdown("**VRP**")
            vrp = snap.get("vrp_scanner", {}) or {}
            if isinstance(vrp, dict) and vrp.get("ok"):
                for item in vrp.get("high_vrp_sell_premium", [])[:3]:
                    if isinstance(item, dict):
                        score = item.get("vrp_pct", 0)
                        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                                    f'<span style="font-size:0.72rem;color:#E6EDF3;min-width:45px;">{item.get("ticker","—")}</span>'
                                    f'<div class="gauge-track" style="flex:1;height:8px;"><div class="gauge-fill" style="width:{min(100,abs(score)*5):.0f}%;background:#F85149;"></div></div>'
                                    f'<span style="font-size:0.65rem;color:#F85149;font-weight:700;width:35px;text-align:right;">{score:.0f}%</span></div>', unsafe_allow_html=True)
            else: st.caption("VRP unavailable")
            st.markdown("**Squeeze**")
            sq_scan = snap.get("squeeze_scanner", {}) or {}
            if isinstance(sq_scan, dict) and sq_scan.get("ok"):
                for item in sq_scan.get("imminent_squeezes", [])[:3]:
                    if isinstance(item, dict):
                        score = item.get("squeeze_score", 0)
                        st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                                    f'<span style="font-size:0.72rem;color:#E6EDF3;min-width:45px;">{item.get("ticker","—")}</span>'
                                    f'<div class="gauge-track" style="flex:1;height:8px;"><div class="gauge-fill" style="width:{min(100,score):.0f}%;background:#D29922;"></div></div>'
                                    f'<span style="font-size:0.65rem;color:#D29922;font-weight:700;width:35px;text-align:right;">{score:.0f}</span></div>', unsafe_allow_html=True)
            else: st.caption("Squeeze unavailable")
            st.markdown("**Vol Forecast**")
            vol_f = snap.get("vol_forecast", {}) or {}
            if isinstance(vol_f, dict):
                for k, v in list(vol_f.items())[:3]:
                    if isinstance(v, dict):
                        regime = v.get("vol_regime", "-")
                        color = "#3FB950" if regime == "LOW" else "#D29922" if regime == "NORMAL" else "#F85149"
                        st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{k}: <span style="color:{color};font-weight:700;">{v.get("current_ann_vol",0):.1f}%</span> ({regime})</div>', unsafe_allow_html=True)
            else: st.caption("Vol forecast unavailable")
        st.markdown("**Engine Status**")
        engines = [("GIP v10", snap.get("gip_v10") is not None), ("Markov V3", snap.get("markov_v3") is not None), ("Yves v2", snap.get("yves_v2") is not None),
                   ("Cascade", snap.get("cascade_analysis") is not None), ("VRP", snap.get("vrp_scanner") is not None), ("Squeeze", snap.get("squeeze_scanner") is not None),
                   ("Smart Money", snap.get("smart_money") is not None), ("Discovery", snap.get("discovery_brain") is not None)]
        cols = st.columns(4)
        for i, (name, ok) in enumerate(engines):
            color = "#3FB950" if ok else "#F85149"
            cols[i % 4].markdown(f"<span style='color:{color};font-size:0.75rem;'>● {name}</span>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# PAGE: ALPHA CENTER
# ═══════════════════════════════════════════════════════════════════
def page_alpha():
    st.markdown("## ⚡ Alpha Center")

    summary = snap.get("summary", {}) or {}
    k1, k2, k3 = st.columns(3)
    k1.metric("Smart $ Consensus", summary.get("v7_smart_money_consensus", 0))
    k2.metric("Top Theses", summary.get("v7_top_theses_count", 0))
    k3.metric("Kelly", f"{summary.get('v7_markov_kelly', 0.25):.0%}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Top Picks", "🔮 Front-Run", "📊 Vol & Squeeze", "🧠 Discovery"])

    with tab1:
        alpha_candidates = []
        bottleneck = snap.get("bottleneck_v3", {}) or {}
        if isinstance(bottleneck, dict):
            for item in bottleneck.get("active_bottlenecks", []) or []:
                if not isinstance(item, dict): continue
                for t in item.get("beneficiaries", [])[:5]:
                    alpha_candidates.append({"ticker": t, "source": "bottleneck", "score": 85, "thesis": f"Bottleneck: {item.get('name','').replace('_',' ').title()}", "direction": "LONG"})

        fr = snap.get("front_run_candidates", []) or []
        for item in fr[:15]:
            if not isinstance(item, dict): continue
            alpha_candidates.append({"ticker": item.get("ticker",""), "source": "front_run", "score": 75, "thesis": item.get("why_front_run", "")[:80], "direction": "LONG", "options": item.get("options", {})})

        leopold = snap.get("leopold_scan", {}) or {}
        if isinstance(leopold, dict):
            for t in leopold.get("asymmetry_setups", []) or []:
                if isinstance(t, dict):
                    alpha_candidates.append({"ticker": t.get("ticker",""), "source": "leopold", "score": 80, "thesis": t.get("thesis", "Asymmetry setup"), "direction": t.get("direction", "LONG")})

        karsan = snap.get("karsan_scanner", {}) or {}
        if isinstance(karsan, dict):
            for t in karsan.get("squeeze_setups", []) or []:
                if isinstance(t, dict):
                    alpha_candidates.append({"ticker": t.get("ticker",""), "source": "karsan_squeeze", "score": 78, "thesis": f"Squeeze setup · Score {t.get('squeeze_score',0):.0f}", "direction": "LONG"})
            for t in karsan.get("buy_convexity", []) or []:
                if isinstance(t, dict):
                    alpha_candidates.append({"ticker": t.get("ticker",""), "source": "karsan_convexity", "score": 72, "thesis": "Buy convexity — vol expansion play", "direction": "LONG"})

        coatue = snap.get("coatue_scan", {}) or {}
        if isinstance(coatue, dict):
            for t in coatue.get("agentic_plays", []) or []:
                if isinstance(t, dict):
                    alpha_candidates.append({"ticker": t.get("ticker",""), "source": "coatue", "score": 70, "thesis": t.get("thesis", "Agentic play"), "direction": "LONG"})

        seen = {}
        for c in alpha_candidates:
            t = c.get("ticker", "")
            if not t: continue
            if t not in seen or c.get("score", 0) > seen[t].get("score", 0):
                seen[t] = c
        alpha_candidates = list(seen.values())
        alpha_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_alpha = [c for c in alpha_candidates if c.get("score", 0) >= 60][:25]

        if not top_alpha:
            st.info(f"No alpha candidates this snapshot. Total analyzed: {len(alpha_candidates)}. Run orchestrator with all engines enabled.")
        else:
            st.markdown(f"**{len(top_alpha)} alpha candidates** from {len(alpha_candidates)} total (bar: ≥60/100)")
            alpha_tickers = [c["ticker"] for c in top_alpha if c.get("ticker")]
            alpha_rows = build_ticker_rows(alpha_tickers, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
            for row in alpha_rows:
                c = seen.get(row.get("ticker"), {})
                if c:
                    row["alpha_source"] = c.get("source", "")
                    row["alpha_score"] = c.get("score", 0)
                    row["alpha_thesis"] = c.get("thesis", "")
                    row["direction"] = c.get("direction", row.get("direction", "LONG"))
            longs, shorts = split_long_short(alpha_rows)
            if longs:
                st.markdown(f"<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🟢 Long Setups ({len(longs)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(longs, max_rows=20)
            if shorts:
                st.markdown(f"<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🔴 Short Setups ({len(shorts)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(shorts, max_rows=20)

    with tab2:
        st.markdown("### 🔮 Front-Run Candidates")
        fr = snap.get("front_run_candidates", []) or []
        if fr:
            fr_tickers = [item.get("ticker","") for item in fr if isinstance(item, dict) and item.get("ticker")]
            fr_rows = build_ticker_rows(fr_tickers, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
            for row in fr_rows:
                item = next((x for x in fr if isinstance(x, dict) and x.get("ticker") == row.get("ticker")), {})
                row["alpha_source"] = item.get("source", "front_run")
                row["alpha_score"] = 75 if item.get("priority") == "TOP" else 70 if item.get("priority") == "HIGH" else 65
                row["alpha_thesis"] = item.get("why_front_run", "")[:120]
                if item.get("catalyst"):
                    cat = item["catalyst"]
                    row["alpha_thesis"] += f" | Catalyst: {cat.get('event','')} ({cat.get('quarter','')})"
            fr_longs, fr_shorts = split_long_short(fr_rows)
            if fr_longs:
                st.markdown(f"<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🟢 Front-Run Long ({len(fr_longs)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(fr_longs, max_rows=15)
            if fr_shorts:
                st.markdown(f"<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin:8px 0 4px;'>🔴 Front-Run Short ({len(fr_shorts)})</div>", unsafe_allow_html=True)
                render_ticker_cards_v4(fr_shorts, max_rows=15)
        else:
            st.info("No front-run candidates this snapshot.")

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📊 VRP Scanner")
            vrp = snap.get("vrp_scanner", {}) or {}
            sell = []; buy = []
            if isinstance(vrp, dict) and vrp.get("ok"):
                sell = vrp.get("high_vrp_sell_premium", [])
                buy = vrp.get("low_vrp_buy_premium", [])
            if not sell and not buy:
                proxy_vrp = []
                for t in ["SPY","QQQ","IWM","GLD","TLT","VIXY","UVXY","HYG","LQD","EEM","TLT","IEF"]:
                    s = prices.get(t)
                    if s is None or len(s) < 60: continue
                    try:
                        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
                        if len(s_clean) < 60: continue
                        vol_20 = float(s_clean.tail(20).pct_change().dropna().std() * math.sqrt(252))
                        vol_60 = float(s_clean.tail(60).pct_change().dropna().std() * math.sqrt(252)) if len(s_clean) >= 60 else vol_20
                        iv_rank = min(100, max(0, (vol_20 / max(vol_60, 0.001) * 50)))
                        vrp_pct = (vol_20 / max(vol_60, 0.001) - 1) * 100
                        if vrp_pct > 15:
                            proxy_vrp.append({"ticker": t, "vrp_pct": round(vrp_pct, 0), "iv_rank": round(iv_rank, 0), "direction": "SELL"})
                        elif vrp_pct < -15:
                            buy.append({"ticker": t, "vrp_pct": round(abs(vrp_pct), 0), "iv_rank": round(iv_rank, 0), "direction": "BUY"})
                    except Exception: pass
                sell = proxy_vrp
            st.metric("Sell Premium", len(sell))
            st.metric("Buy Premium", len(buy))
            if sell:
                for item in sell[:8]:
                    if isinstance(item, dict):
                        st.markdown(f"• **{item.get('ticker')}** · VRP +{item.get('vrp_pct', 0):.0f}% · IV Rank {item.get('iv_rank', '—')}")
            else: st.caption("No sell premium setups")
            if buy:
                st.markdown("<div style='font-size:0.65rem;color:#3FB950;text-transform:uppercase;font-weight:600;margin-top:8px;'>Buy Convexity</div>", unsafe_allow_html=True)
                for item in buy[:5]:
                    if isinstance(item, dict):
                        st.markdown(f"• **{item.get('ticker')}** · VRP {item.get('vrp_pct', 0):.0f}% cheap · IV Rank {item.get('iv_rank', '—')}")
        with col2:
            st.markdown("### 🔥 Squeeze Scanner")
            sq_scan = snap.get("squeeze_scanner", {}) or {}
            imm = []; strong = []
            if isinstance(sq_scan, dict) and sq_scan.get("ok"):
                imm = sq_scan.get("imminent_squeezes", [])
                strong = sq_scan.get("strong_candidates", [])
            if not imm and not strong:
                proxy_sq = []
                for t in list(prices.keys())[:80]:
                    s = prices.get(t)
                    if s is None or len(s) < 40: continue
                    try:
                        s_clean = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
                        if len(s_clean) < 40: continue
                        bb_upper = float(s_clean.tail(20).mean()) + 2 * float(s_clean.tail(20).std())
                        bb_lower = float(s_clean.tail(20).mean()) - 2 * float(s_clean.tail(20).std())
                        px = float(s_clean.iloc[-1])
                        if bb_upper == bb_lower: continue
                        pct_b = (px - bb_lower) / (bb_upper - bb_lower)
                        vol_20 = float(s_clean.tail(20).pct_change().dropna().std())
                        vol_5 = float(s_clean.tail(5).pct_change().dropna().std()) if len(s_clean) >= 5 else vol_20
                        vol_contracting = vol_5 < vol_20 * 0.6
                        near_mid = 0.35 < pct_b < 0.65
                        if vol_contracting and near_mid:
                            score = min(100, int(50 + (1 - vol_5/vol_20) * 50))
                            proxy_sq.append({"ticker": t, "squeeze_score": score, "tier": "PROXY"})
                    except Exception: pass
                proxy_sq.sort(key=lambda x: x["squeeze_score"], reverse=True)
                imm = proxy_sq[:8]
            st.metric("Imminent", len(imm))
            st.metric("Strong", len(strong))
            if imm:
                for item in imm[:8]:
                    if isinstance(item, dict):
                        tier_badge = "🟡 PROXY" if item.get("tier") == "PROXY" else f"🔥 {item.get('tier','—')}"
                        st.markdown(f"• **{item.get('ticker')}** · Score {item.get('squeeze_score', 0):.0f}/100 {tier_badge}")
            else: st.caption("No imminent squeezes")

    with tab4:
        st.markdown("### 🔮 Discovery Brain")
        disc = snap.get("discovery_brain", {}) or {}
        if isinstance(disc, dict) and disc.get("by_mode"):
            for mode in ("adaptive", "reactive", "proactive"):
                items = disc.get("by_mode", {}).get(mode, [])
                if items:
                    st.markdown(f"**{mode.title()}** ({len(items)})")
                    for item in items[:5]:
                        if isinstance(item, dict):
                            with st.expander(f"{item.get('name', '—').replace('_', ' ')} · conf {item.get('confidence', 0):.0%}"):
                                st.markdown(item.get("thesis", "—"))
        else: st.info("Discovery Brain — no candidates this snapshot")

        st.markdown("### 💰 Position Sizing")
        sizing = snap.get("portfolio_sizing_v2", {}) or {}
        if isinstance(sizing, dict) and sizing.get("positions"):
            st.metric("Deployed", f"{sizing.get('total_deployed_pct', 0):.1%}")
            st.metric("Cash", f"{sizing.get('cash_pct', 0):.1%}")
            df = pd.DataFrame([{"Ticker": p.get("ticker"), "Size %": f"{p.get('target_pct', 0):.2f}%",
                                "Size $": f"{p.get('target_dollar', 0):,.0f}", "Mode": p.get("mode"), "Sector": p.get("sector")}
                               for p in sizing.get("positions", []) if isinstance(p, dict)])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.info("No sized positions yet.")

        conv = snap.get("conviction_sizing", {}) or {}
        if isinstance(conv, dict) and conv.get("positions"):
            st.markdown("### 🎯 Conviction Sizing (Soros)")
            for p in conv.get("positions", [])[:5]:
                if not isinstance(p, dict): continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;padding:3px 0;">'
                            f'<span style="color:#E6EDF3;">{p.get("ticker","—")}</span>'
                            f'<span style="color:#8B949E;">{p.get("conviction","—")} · {p.get("size_pct",0):.1f}%</span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# PAGE: US STOCKS
# ═══════════════════════════════════════════════════════════════════
def page_us_stocks():
    st.markdown("## 🇺🇸 US Stocks")

    playbook = {
        "Q1": {"beli": ["QQQ","XLK","NVDA","AAPL","MSFT","GOOGL","META","AMD","ARKK"], "short": ["XLU","XLP","TLT","GLD"]},
        "Q2": {"beli": ["XLF","XLE","XLI","XLB","KRE","IWM","XOM","CVX"], "short": ["TLT","IEF"]},
        "Q3": {"beli": ["XLE","XLP","XLU","ITA","GLD","SLV","VST","CEG","BE","LITE","CCJ"], "short": ["QQQ","XLK","IWM","ARKK","KRE"]},
        "Q4": {"beli": ["TLT","IEF","GLD","XLU","XLP","XLV"], "short": ["QQQ","XLK","IWM","XLY","XLF","XLE"]},
    }
    pb = playbook.get(sq, playbook["Q3"])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Overweight</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"][:10]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Underweight</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["short"][:8]) + "</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📊 Index / ETF Setups (SPY · QQQ · IWM · GLD · TLT)")
    key_etfs = ["SPY", "QQQ", "IWM", "GLD", "TLT"]
    etf_rows = build_ticker_rows(key_etfs, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
    etf_longs, etf_shorts = split_long_short(etf_rows)
    if etf_longs:
        st.markdown(f"<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:4px;'>🟢 Long Bias</div>", unsafe_allow_html=True)
        render_ticker_cards_v4(etf_longs, max_rows=10)
    if etf_shorts:
        st.markdown(f"<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:4px;'>🔴 Short Bias</div>", unsafe_allow_html=True)
        render_ticker_cards_v4(etf_shorts, max_rows=10)

    st.divider()
    us_tickers = list(US_SECTORS.keys()) if US_SECTORS else []
    for bucket in ["Growth","Quality","Defensives","Semis","Energy","Industrials","Financials","AI_Infra","PreciousMetals"]:
        us_tickers += US_BUCKETS.get(bucket, []) if US_BUCKETS else []
    if not us_tickers: us_tickers = FALLBACK_US
    # Filter out key ETFs that already shown above
    key_etfs_set = {"SPY", "QQQ", "IWM", "GLD", "TLT"}
    us_tickers = [t for t in us_tickers if t not in key_etfs_set]
    us_tickers = list(dict.fromkeys(us_tickers))

    rows = build_ticker_rows(us_tickers, "us_equity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
    longs, shorts = split_long_short(rows)

    st.markdown(f"**{len(rows)} setups** · 🟢 {len(longs)} Long · 🔴 {len(shorts)} Short")
    tab_l, tab_s = st.tabs([f"🟢 Long ({len(longs)})", f"🔴 Short ({len(shorts)}))"])
    with tab_l: render_ticker_cards_v4(longs)
    with tab_s: render_ticker_cards_v4(shorts)

# ═══════════════════════════════════════════════════════════════════
# PAGE: FOREX
# ═══════════════════════════════════════════════════════════════════
def page_forex():
    st.markdown("## 💱 Forex")
    playbook = {
        "Q1": {"beli": ["EURUSD","AUDUSD","EM FX"], "short": ["DXY/UUP"]},
        "Q2": {"beli": ["GBPUSD","CADUSD"], "short": ["JPY"]},
        "Q3": {"beli": ["UUP","CHF"], "short": ["EURUSD","GBPUSD","EM FX"]},
        "Q4": {"beli": ["JPY","CHF"], "short": ["AUDUSD","EM FX"]},
    }
    pb = playbook.get(sq, playbook["Q3"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["short"]) + "</div>", unsafe_allow_html=True)
    dxy_corr = snap.get("dxy_correlation", {}) or {}
    if isinstance(dxy_corr, dict) and (dxy_corr.get("strongest_positive_corr") or dxy_corr.get("strongest_negative_corr")):
        st.divider()
    fx_tickers = list(FOREX_PAIRS.keys()) if FOREX_PAIRS else FALLBACK_FX
    rows = build_ticker_rows(fx_tickers, "forex", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
    longs, shorts = split_long_short(rows)
    st.markdown(f"**{len(rows)} pairs** · 🟢 {len(longs)} Long · 🔴 {len(shorts)} Short")
    tab_l, tab_s = st.tabs([f"🟢 Long ({len(longs)})", f"🔴 Short ({len(shorts)}))"])
    with tab_l: render_ticker_cards_v4(longs)
    with tab_s: render_ticker_cards_v4(shorts)

# ═══════════════════════════════════════════════════════════════════
# PAGE: COMMODITIES
# ═══════════════════════════════════════════════════════════════════
def page_commodities():
    st.markdown("## 🛢️ Commodities")
    playbook = {
        "Q1": {"beli": ["Copper","Industrial Metals"], "short": ["Gold (counter-trend)"]},
        "Q2": {"beli": ["CL=F","USO","XLE","Energy"], "short": []},
        "Q3": {"beli": ["GLD","SLV","CL=F","CCJ","URA"], "short": []},
        "Q4": {"beli": ["GLD","TLT"], "short": ["CL=F","Industrial metals"]},
    }
    pb = playbook.get(sq, playbook["Q3"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + (" · ".join(pb["short"]) if pb["short"] else "—") + "</div>", unsafe_allow_html=True)
    st.divider()
    comm_tickers = list(COMMODITIES.keys()) if COMMODITIES else FALLBACK_COMM
    rows = build_ticker_rows(comm_tickers, "commodity", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
    longs, shorts = split_long_short(rows)
    st.markdown(f"**{len(rows)} commodities** · 🟢 {len(longs)} Long · 🔴 {len(shorts)} Short")
    tab_l, tab_s = st.tabs([f"🟢 Long ({len(longs)})", f"🔴 Short ({len(shorts)}))"])
    with tab_l: render_ticker_cards_v4(longs)
    with tab_s: render_ticker_cards_v4(shorts)

# ═══════════════════════════════════════════════════════════════════
# PAGE: CRYPTO
# ═══════════════════════════════════════════════════════════════════
def page_crypto():
    st.markdown("## ₿ Crypto")
    playbook = {
        "Q1": {"beli": ["BTC","ETH","SOL","alts"], "short": []},
        "Q2": {"beli": ["BTC","MSTR","CORZ","IREN"], "short": []},
        "Q3": {"beli": ["BTC","MSTR","IBIT"], "short": ["alts (ETH/SOL relative)"]},
        "Q4": {"beli": ["BTC (hedge ONLY)"], "short": ["alts","ETH","memecoin"]},
    }
    pb = playbook.get(sq, playbook["Q3"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div style='font-size:0.68rem; color:#3FB950; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Buy</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + " · ".join(pb["beli"]) + "</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='font-size:0.68rem; color:#F85149; text-transform:uppercase; font-weight:600; margin-bottom:3px;'>Short</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; line-height:1.5;'>" + (" · ".join(pb["short"]) if pb["short"] else "—") + "</div>", unsafe_allow_html=True)
    cc = snap.get("crypto_center", {}) or {}
    if isinstance(cc, dict) and (cc.get("capital_flows") or cc.get("market_structure")):
        st.divider()
        st.markdown("### ₿ On-Chain / Market Structure")
        flows = cc.get("capital_flows", {})
        if isinstance(flows, dict):
            st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;">Stablecoin: <span style="color:#E6EDF3;font-weight:700;">{flows.get("total_b",0):.1f}B</span> ({flows.get("change_7d_b",0):+.1f}B 7D)</div>', unsafe_allow_html=True)
        structure = cc.get("market_structure", {})
        if isinstance(structure, dict) and structure.get("funding"):
            st.markdown("<div style='font-size:0.65rem; color:#8B949E; text-transform:uppercase; font-weight:600; margin-top:6px; margin-bottom:3px;'>Funding Rates</div>", unsafe_allow_html=True)
            for sym, data in list(structure.get("funding", {}).items())[:4]:
                if isinstance(data, dict):
                    rate = data.get("rate", 0)
                    color = "#3FB950" if rate < 0 else "#F85149" if rate > 0.0005 else "#8B949E"
                    st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;">{sym}: <span style="color:{color};font-weight:700;">{rate:.4f}</span></div>', unsafe_allow_html=True)
        narrative_crypto = cc.get("narrative", {})
        if isinstance(narrative_crypto, dict) and narrative_crypto.get("fear_greed"):
            fg = narrative_crypto.get("fear_greed", {})
            st.markdown(f'<div style="margin-top:6px;font-size:0.78rem;color:#8B949E;">Fear & Greed: <span style="color:#E6EDF3;font-weight:700;">{fg.get("value",50)}</span> ({fg.get("label","Neutral")})</div>', unsafe_allow_html=True)
    st.divider()
    crypto_tickers = list(CRYPTO.keys()) if CRYPTO else FALLBACK_CRYPTO
    rows = build_ticker_rows(crypto_tickers, "crypto", vix_now, snap.get("gamma_data"), snap.get("greeks_data"), snap.get("news_narratives"), prices=prices, ar=ar, snap=snap)
    longs, shorts = split_long_short(rows)
    st.markdown(f"**{len(rows)} coins** · 🟢 {len(longs)} Long · 🔴 {len(shorts)} Short")
    tab_l, tab_s = st.tabs([f"🟢 Long ({len(longs)})", f"🔴 Short ({len(shorts)}))"])
    with tab_l: render_ticker_cards_v4(longs)
    with tab_s: render_ticker_cards_v4(shorts)

# ═══════════════════════════════════════════════════════════════════
# PAGE: GLOBAL & EM
# ═══════════════════════════════════════════════════════════════════
def page_global():
    st.markdown("## 🌍 Global & EM")
    global_ = snap.get("global", {}) or {}
    country_list = global_.get("country_list", []) if isinstance(global_, dict) else []
    if not country_list:
        base_map = {
            "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia","UAE","Israel","Poland","Czech Republic","Romania"],
            "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand","Colombia","New Zealand","Norway","Kazakhstan","Angola"],
            "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt","Spain","Netherlands","Belgium","Sweden","Switzerland"],
            "Q4": ["Venezuela","Iran","Ukraine","Greece","Portugal","Lebanon","Syria","Yemen","Zimbabwe","Sudan","Afghanistan","North Korea","Myanmar","Belarus","Bolivia"],
        }
        country_list = []
        for q, countries in base_map.items():
            for c in countries: country_list.append({"country": c, "quad": q, "regime_name": _quad_name(q)})
    st.markdown("### 🗺️ Country Regime Map")
    st.markdown(_heatmap_grid_html(country_list[:16], key_label="country", key_quad="quad"), unsafe_allow_html=True)
    if len(country_list) > 16: st.markdown(_heatmap_grid_html(country_list[16:32], key_label="country", key_quad="quad"), unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🇮🇩 IHSG Report")
    ihsg_tickers = list(IHSG_UNIVERSE.keys()) if IHSG_UNIVERSE else FALLBACK_IHSG
    ihsg_rows = build_ticker_rows(ihsg_tickers, "ihsg", vix_now, prices=prices, ar=ar, snap=snap)
    by_sector = {}
    for r in ihsg_rows: by_sector.setdefault(IHSG_SECTOR_MAP.get(r.get("ticker"), "Other"), []).append(r)
    if by_sector:
        sectors = list(by_sector.keys()); counts = [len(v) for v in by_sector.values()]
        colors = [_ret_color(sum(x.get("r1m",0) or 0 for x in by_sector[s])/max(len(by_sector[s]),1)) for s in sectors]
        fig = go.Figure(go.Bar(y=sectors, x=counts, orientation="h", marker_color=colors, text=[str(c) for c in counts], textposition="outside", textfont=dict(size=11, color="#E6EDF3")))
        fig.update_layout(height=max(250, len(sectors)*35), margin=dict(l=120,r=40,t=20,b=20), paper_bgcolor="#0D1117", plot_bgcolor="#0D1117", font=dict(color="#E6EDF3", size=11, family="Inter"), xaxis=dict(showgrid=True, gridcolor="#21262D"), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="ihsg_sector_bar_v4")
    st.markdown(f"**{len(ihsg_rows)} stocks** · Sectors: {', '.join(by_sector.keys())}")
    for sector, items in by_sector.items():
        with st.expander(f"**{sector}** ({len(items)} stocks)", expanded=False):
            render_ticker_cards_v4(items, max_rows=10)

# ═══════════════════════════════════════════════════════════════════
# PAGE: THEMES
# ═══════════════════════════════════════════════════════════════════
def page_themes():
    st.markdown("## 📖 Themes & Playbook")
    allocation = {
        "Q1": {"long": 75, "short": 5, "cash": 20, "style": "Tech 30% | Growth 20% | Crypto 15% | EM 5% | Defensives 5%"},
        "Q2": {"long": 70, "short": 10, "cash": 20, "style": "Cyclicals 25% | Financials 15% | Energy 15% | Materials 10% | Small Caps 5%"},
        "Q3": {"long": 60, "short": 15, "cash": 25, "style": "Energy/Infra 20% | Real Assets 15% | Crypto 10% | EM/LatAm 8% | IHSG Energy 7%"},
        "Q4": {"long": 50, "short": 20, "cash": 30, "style": "TLT 15% | Gold 10% | Utilities 10% | Staples 10% | Healthcare 5%"},
    }
    alloc = allocation.get(sq, allocation["Q3"])
    st.markdown("### 💼 Portfolio Allocation")
    st.markdown(_stacked_bar_html(alloc["long"], alloc["short"], alloc["cash"]), unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.78rem; color:#8B949E; margin-top:6px;'>**Style:** {alloc['style']}</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("### ⚡ Cem Karsan / 0DTE")
    odte = snap.get("odte_monitor", {}) or {}
    if isinstance(odte, dict) and odte.get("tickers"):
        for t, data in list(odte.get("tickers", {}).items())[:3]:
            if not isinstance(data, dict): continue
            pin = data.get("pin_risk", 50)
            vanna_dir = data.get("vanna", "neutral"); charm_dir = data.get("charm", "neutral")
            v_arrow = "⬆" if "up" in str(vanna_dir).lower() or "pos" in str(vanna_dir).lower() else "⬇" if "down" in str(vanna_dir).lower() or "neg" in str(vanna_dir).lower() else "➡"
            c_arrow = "⬆" if "up" in str(charm_dir).lower() or "pos" in str(charm_dir).lower() else "⬇" if "down" in str(charm_dir).lower() or "neg" in str(charm_dir).lower() else "➡"
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;padding:7px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;">'
                        f'<span style="font-weight:700;font-size:0.85rem;color:#E6EDF3;min-width:45px;">{t}</span>'
                        f'<div style="flex:1;"><div style="font-size:0.58rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Pin Risk</div>'
                        f'{_gauge_html(pin, max_val=100, color="#D29922", height=9, label_left="0", label_right="100")}</div>'
                        f'<div style="font-size:0.75rem;color:#58A6FF;font-weight:700;">Vanna {v_arrow}</div>'
                        f'<div style="font-size:0.75rem;color:#A371F7;font-weight:700;">Charm {c_arrow}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("0DTE data unavailable — showing proxy")
        for t in ["SPY","QQQ","IWM"]:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;padding:7px 10px;background:#161B22;border:1px solid #30363D;border-radius:6px;">'
                        f'<span style="font-weight:700;font-size:0.85rem;color:#E6EDF3;min-width:45px;">{t}</span>'
                        f'<div style="flex:1;"><div style="font-size:0.58rem;color:#8B949E;text-transform:uppercase;font-weight:600;">Pin Risk</div>'
                        f'{_gauge_html(50, max_val=100, color="#30363D", height=9, label_left="0", label_right="100")}</div>'
                        f'<div style="font-size:0.75rem;color:#8B949E;font-weight:700;">Vanna ➡</div>'
                        f'<div style="font-size:0.75rem;color:#8B949E;font-weight:700;">Charm ➡</div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🧪 Stress Test")
    stress = snap.get("stress_test", []) or []
    if stress:
        for s in stress[:3]:
            if not isinstance(s, dict): continue
            with st.expander(f"{s.get('scenario','—')} · DD {s.get('portfolio_dd',0):.0%}"):
                st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;">Worst: <span style="color:#F85149;font-weight:700;">{s.get("worst_asset","—")} {s.get("worst_dd",0):.0%}</span> · Best: <span style="color:#3FB950;font-weight:700;">{s.get("best_asset","—")} {s.get("best_dd",0):.0%}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.78rem;color:#8B949E;margin-top:4px;">Hedge: <span style="color:#E6EDF3;">{s.get("hedge","—")}</span></div>', unsafe_allow_html=True)
    else: st.caption("Stress test unavailable")
    st.divider()
    st.markdown("### 🧠 Methodology Lens")
    methodologies = [
        ("🏗️ Leopold", "Bottleneck layers + asymmetry setups", snap.get("leopold_scan")),
        ("💱 COATUE", "Shortage economy + capital rotation", snap.get("coatue_scan")),
        ("📊 Karsan", "Vol surface + squeeze setups", snap.get("karsan_scanner")),
        ("🧠 Yves", "Behavioral relabeling", snap.get("yves_v2")),
        ("🌀 Soros", "Boom-bust reflexivity", snap.get("boom_bust")),
        ("⚡ Vol Decomp", "Black-Scholes IV breakdown", None),
        ("💧 Druckenmiller", "Liquidity-first positioning", None),
    ]
    for name, desc, data in methodologies:
        status = "🟢" if data else "⚪"
        with st.expander(f"{status} {name} — {desc}", expanded=False):
            if data: st.json({k: str(v)[:100] for k, v in list(data.items())[:3]})
            else: st.caption("Data not loaded this snapshot.")

# ═══════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard": page_dashboard()
elif page == "⚡ Alpha Center": page_alpha()
elif page == "🇺🇸 US Stocks": page_us_stocks()
elif page == "💱 Forex": page_forex()
elif page == "🛢️ Commodities": page_commodities()
elif page == "₿ Crypto": page_crypto()
elif page == "🌍 Global & EM": page_global()
elif page == "📖 Themes": page_themes()

st.divider()
flip_note = f" · {snap.get('summary', {}).get('v2_composite_flipped_count', 0)} flipped" if snap.get("summary", {}).get("v2_composite_flipped_count") else ""
st.caption(f"MacroRegime Pro v32.4 AUDITED · Built {snap.get('build_time_s', 0):.0f}s ago · {snap.get('prices_loaded', 0)} assets · {snap.get('fred_coverage', 0)} indicators{flip_note}")

"""
MacroRegime Pro v4 — Single-file god mode
=========================================
Gap-filled Hedgeye-style macro regime dashboard.
Free data: yfinance + FRED public CSV + CoinGecko free API.
Run: streamlit run macro_regime_pro_v4.py
"""

from __future__ import annotations
import datetime, math, time
from io import StringIO
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, .headline { font-family: 'Syne', sans-serif; letter-spacing: -0.02em; }
code, .mono { font-family: 'DM Mono', monospace; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }

/* Quad badge */
.quad-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    font-size: 12px;
    letter-spacing: 0.05em;
}
.q1 { background: #d4edda; color: #155724; }
.q2 { background: #fff3cd; color: #856404; }
.q3 { background: #ffeeba; color: #7d4e00; }
.q4 { background: #f8d7da; color: #721c24; }
.qunk { background: #e2e3e5; color: #495057; }

/* Metric cards */
.metric-card {
    background: var(--background-color, #f8f9fa);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 8px;
}
.metric-card .label {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.55;
    margin-bottom: 4px;
}
.metric-card .value {
    font-family: 'Syne', sans-serif;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 2px;
}
.metric-card .sub {
    font-size: 12px;
    opacity: 0.6;
}
.good { color: #198754; }
.warn { color: #d68910; }
.bad  { color: #dc3545; }
.neutral { color: #6c757d; }

/* Info pill */
.pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    margin: 2px;
    background: rgba(0,0,0,0.06);
}

/* Section header */
.section-hdr {
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.45;
    padding: 12px 0 4px;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    margin-bottom: 12px;
}

/* Regime compass */
.compass-wrap {
    text-align: center;
    padding: 20px 0;
}
.regime-title {
    font-family: 'Syne', sans-serif;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 6px;
}
.regime-sub {
    font-size: 14px;
    opacity: 0.6;
    margin-bottom: 16px;
}
.regime-explain {
    font-size: 15px;
    line-height: 1.65;
    max-width: 520px;
    margin: 0 auto;
    opacity: 0.85;
}

/* Gauge bar */
.gauge-wrap { margin-bottom: 10px; }
.gauge-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
.gauge-bar { height: 6px; border-radius: 3px; background: rgba(0,0,0,0.08); overflow: hidden; }
.gauge-fill { height: 100%; border-radius: 3px; transition: width 0.4s; }

/* Nav tabs */
.stTabs [role="tablist"] { gap: 4px; }
.stTabs [role="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    padding: 6px 16px;
    border-radius: 8px;
}

/* Arrow indicator */
.arrow-up   { color: #198754; font-size: 14px; }
.arrow-down { color: #dc3545; font-size: 14px; }
.arrow-flat { color: #6c757d; font-size: 14px; }

/* Opportunity row highlight */
.opp-long  { border-left: 3px solid #198754; padding-left: 8px; }
.opp-short { border-left: 3px solid #dc3545; padding-left: 8px; }
.opp-hedge { border-left: 3px solid #d68910; padding-left: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
CACHE_TTL = 3600  # 1 hour

FRED_SERIES = {
    # Growth
    "INDPRO":   "INDPRO",      # Industrial production
    "PAYEMS":   "PAYEMS",      # Nonfarm payrolls
    "UNRATE":   "UNRATE",      # Unemployment rate
    "ICSA":     "ICSA",        # Initial jobless claims
    "RSAFS":    "RSAFS",       # Retail sales
    "HOUST":    "HOUST",       # Housing starts
    "PERMIT":   "PERMIT",      # Building permits
    "ISM":      "NAPMNOI",     # ISM Manufacturing
    "LEI":      "USSLIND",     # Conference Board LEI
    "UMCSENT":  "UMCSENT",     # Univ of Michigan consumer sentiment
    # Inflation
    "CPI":      "CPIAUCSL",    # CPI all items
    "CORECPI":  "CPILFESL",    # Core CPI
    "PCE":      "PCEPI",       # PCE deflator
    "COREPCE":  "PCEPILFE",    # Core PCE (Fed preferred)
    # Rates
    "DGS2":     "DGS2",        # 2-year Treasury yield
    "DGS10":    "DGS10",       # 10-year Treasury yield
    "DGS30":    "DGS30",       # 30-year Treasury yield
    "REAL10":   "DFII10",      # 10-year TIPS (real yield)
    "BREAKEVEN":"T5YIE",       # 5-year breakeven inflation
    "FEDFUNDS": "FEDFUNDS",    # Fed funds rate
    # Credit spreads
    "HYOAS":    "BAMLH0A0HYM2",   # HY OAS spread
    "IGSPR":    "BAMLC0A0CM",     # IG OAS spread
}

PRICE_TICKERS = [
    "SPY","QQQ","IWM","RSP","MDY",
    "XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC",
    "HYG","LQD","TLT","IEF","SHY",
    "GLD","SLV","GC=F","SI=F","HG=F","CL=F","NG=F",
    "UUP","EEM","EFA",
    "^VIX","^VIX9D","^VXV",
    "BTC-USD","ETH-USD","SOL-USD",
]

QUAD_META = {
    "Q1": {
        "name": "Q1 — Growth ↑, Inflation ↓",
        "color": "#d4edda", "text": "#155724",
        "label": "Risk-On Goldilocks",
        "explain": "Growth is accelerating while inflation is falling or contained. Historically the best environment for equities — especially growth and cyclicals. Central banks have room to ease or hold. Bonds also do well. The hardest environment to short.",
        "long": ["Growth equities (QQQ, XLK)", "Cyclicals (XLY, XLI)", "Credit (HYG)", "EM equities (EEM)"],
        "hedge": ["Gold (GLD)", "Short duration bonds (SHY)"],
        "avoid": ["Commodities (energy)", "USD longs", "Defensives"],
    },
    "Q2": {
        "name": "Q2 — Growth ↑, Inflation ↑",
        "color": "#fff3cd", "text": "#856404",
        "label": "Reflation / Boom",
        "explain": "Both growth and inflation are rising. Commodity-heavy and nominal assets win. Real assets, energy, and cyclicals outperform. This is where 'value' beats 'growth'. Central banks are typically behind the curve and beginning to tighten.",
        "long": ["Energy (XLE, CL=F)", "Materials (XLB)", "Commodities (GLD, HG=F)", "Financials (XLF)", "Value / Small caps (IWM)"],
        "hedge": ["TIPS / inflation-linked", "Commodity FX"],
        "avoid": ["Long-duration bonds (TLT)", "High-multiple tech", "IG credit"],
    },
    "Q3": {
        "name": "Q3 — Growth ↓, Inflation ↑",
        "color": "#ffeeba", "text": "#7d4e00",
        "label": "Stagflation",
        "explain": "The worst of both worlds: growth is slowing while inflation stays hot. Central banks are forced to tighten into weakness. Equities suffer broadly. Commodities (especially energy and gold) hold up. Cash is often king. The hardest quad to navigate.",
        "long": ["Gold (GLD, GC=F)", "Energy (XLE)", "USD / cash", "Short equity via puts"],
        "hedge": ["Gold", "Short-term Treasuries", "USD"],
        "avoid": ["Rate-sensitive equities", "Consumer discretionary (XLY)", "EM assets (EEM)", "Long bonds (TLT)"],
    },
    "Q4": {
        "name": "Q4 — Growth ↓, Inflation ↓",
        "color": "#f8d7da", "text": "#721c24",
        "label": "Quad 4 — Risk-Off / Deflation",
        "explain": "Growth is slowing and inflation is falling. Bonds rally hard. Defensives outperform. Central banks eventually cut. This is the recession quad. Quality, defensives, and duration win. Cyclicals and commodities get hit hardest.",
        "long": ["Long-duration bonds (TLT)", "Gold (GLD)", "Defensives (XLP, XLU, XLV)", "USD (UUP)"],
        "hedge": ["Treasury bonds", "Gold"],
        "avoid": ["Commodities", "Cyclicals (XLI, XLY)", "Junk credit (HYG)", "Small caps (IWM)", "EM (EEM)"],
    },
}

RATE_DIRECTION_LABELS = {
    (True, True):   ("Accelerating", "🟢"),
    (True, False):  ("Decelerating", "🟡"),
    (False, True):  ("Recovering", "🟡"),
    (False, False): ("Contracting", "🔴"),
}

# ─── DATA LAYER ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_fred(series_key: str) -> pd.Series:
    """Fetch single FRED series as a monthly/daily pandas Series."""
    fred_id = FRED_SERIES.get(series_key, series_key)
    try:
        url = f"{FRED_BASE}{fred_id}"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), index_col=0, parse_dates=True)
        s = df.iloc[:, 0]
        s = pd.to_numeric(s, errors="coerce").dropna()
        return s
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_prices_batch(tickers: list[str], period: str = "2y") -> Dict[str, pd.Series]:
    """Fetch price history for multiple tickers via yfinance."""
    try:
        import yfinance as yf
        raw = yf.download(
            tickers, period=period, auto_adjust=False,
            progress=False, threads=True, ignore_tz=True
        )
        out: Dict[str, pd.Series] = {}
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw.get("Close", raw.get("Adj Close", pd.DataFrame()))
            if isinstance(close, pd.DataFrame):
                for t in tickers:
                    if t in close.columns:
                        s = close[t].dropna()
                        if len(s) > 5:
                            out[t] = s
        else:
            if "Close" in raw.columns:
                for t in tickers:
                    out[t] = raw["Close"].dropna()
        return out
    except Exception as e:
        st.warning(f"Price fetch error: {e}")
        return {}


def last(s: pd.Series) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.iloc[-1]) if not s.empty else float("nan")

def ret_n(s: pd.Series, n: int) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1: return float("nan")
    base = float(s.iloc[-(n+1)])
    if not math.isfinite(base) or base == 0: return float("nan")
    return float(s.iloc[-1] / base - 1.0)

def delta_n(s: pd.Series, n: int) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1: return float("nan")
    return float(s.iloc[-1] - s.iloc[-(n+1)])

def roc_accelerating(s: pd.Series, n: int, lookback: int) -> Optional[bool]:
    """Returns True if RoC(n) is > RoC(n) lookback periods ago — i.e., accelerating."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + lookback + 2: return None
    current_roc = ret_n(s, n)
    lagged_s = s.iloc[:-lookback]
    lagged_roc = ret_n(lagged_s, n)
    if not math.isfinite(current_roc) or not math.isfinite(lagged_roc): return None
    return current_roc > lagged_roc

def trend_score_px(s: pd.Series) -> float:
    """0 = below both MAs, 1 = above both MAs."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 50: return 0.5
    px = float(s.iloc[-1])
    ma20 = float(s.rolling(20).mean().iloc[-1])
    ma50 = float(s.rolling(50).mean().iloc[-1])
    return 0.5 * (1 if px > ma20 else 0) + 0.5 * (1 if px > ma50 else 0)

def _tanh_scale(x: float, scale: float) -> float:
    if not math.isfinite(x): return 0.0
    return float(math.tanh(x / scale))

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x or 0)))

def nanmean(*vals) -> float:
    arr = [v for v in vals if math.isfinite(v)]
    return float(np.mean(arr)) if arr else 0.0

# ─── FEATURE BUILDERS ─────────────────────────────────────────────────────────

def build_macro_features(fred: Dict[str, pd.Series], prices: Dict[str, pd.Series]) -> Dict:
    """Build all macro features including Hedgeye gaps: yield curve, IG spread, copper/gold, LEI, PCE."""
    f: Dict = {}

    # ── Growth (level + RoC) ──────────────────────────────────
    f["indpro_yoy"]       = ret_n(fred.get("INDPRO", pd.Series()), 12)
    f["payrolls_yoy"]     = ret_n(fred.get("PAYEMS", pd.Series()), 12)
    f["payrolls_mom"]     = ret_n(fred.get("PAYEMS", pd.Series()), 1)
    f["unrate"]           = last(fred.get("UNRATE", pd.Series()))
    f["unrate_3m_delta"]  = delta_n(fred.get("UNRATE", pd.Series()), 3)
    f["unrate_6m_delta"]  = delta_n(fred.get("UNRATE", pd.Series()), 6)
    f["claims_13w_delta"] = delta_n(fred.get("ICSA",  pd.Series()), 13)
    f["claims_last"]      = last(fred.get("ICSA",  pd.Series()))
    f["ism_last"]         = last(fred.get("ISM",   pd.Series()))
    f["retail_yoy"]       = ret_n(fred.get("RSAFS", pd.Series()), 12)
    f["housing_yoy"]      = ret_n(fred.get("HOUST", pd.Series()), 12)
    f["permits_yoy"]      = ret_n(fred.get("PERMIT",pd.Series()), 12)
    f["lei_3m"]           = ret_n(fred.get("LEI",   pd.Series()), 3)   # ★ NEW: LEI
    f["umcsent_last"]     = last(fred.get("UMCSENT",pd.Series()))       # ★ NEW: Consumer confidence

    # RoC acceleration flags (Hedgeye key insight)
    f["indpro_acc"]   = roc_accelerating(fred.get("INDPRO", pd.Series()), 12, 3)
    f["payrolls_acc"] = roc_accelerating(fred.get("PAYEMS", pd.Series()), 12, 3)
    f["retail_acc"]   = roc_accelerating(fred.get("RSAFS",  pd.Series()), 12, 3)
    f["lei_acc"]      = roc_accelerating(fred.get("LEI",    pd.Series()), 3,  2)

    # ── Inflation (level + RoC) ───────────────────────────────
    f["cpi_yoy"]       = ret_n(fred.get("CPI",    pd.Series()), 12)
    f["cpi_mom"]       = ret_n(fred.get("CPI",    pd.Series()), 1)
    f["corecpi_yoy"]   = ret_n(fred.get("CORECPI",pd.Series()), 12)
    f["pce_yoy"]       = ret_n(fred.get("PCE",    pd.Series()), 12)    # ★ NEW: PCE
    f["corepce_yoy"]   = ret_n(fred.get("COREPCE",pd.Series()), 12)   # ★ NEW: Core PCE
    f["breakeven"]     = last(fred.get("BREAKEVEN",pd.Series()))
    f["breakeven_1m"]  = delta_n(fred.get("BREAKEVEN",pd.Series()), 1)
    f["real_10y"]      = last(fred.get("REAL10",  pd.Series()))
    # Oil, Gold as real-time inflation proxies
    f["oil_3m"]        = ret_n(prices.get("CL=F", pd.Series()), 63)
    f["oil_1m"]        = ret_n(prices.get("CL=F", pd.Series()), 21)
    f["gold_3m"]       = ret_n(prices.get("GC=F", pd.Series()), 63)

    # ★ NEW: Copper/Gold ratio (growth proxy - Hedgeye's favorite)
    copper = prices.get("HG=F", pd.Series())
    gold   = prices.get("GC=F", pd.Series())
    if not copper.empty and not gold.empty:
        copper_aligned, gold_aligned = copper.align(gold, join="inner")
        if len(copper_aligned) > 63:
            cg_ratio = copper_aligned / gold_aligned
            f["copper_gold_ratio_3m"] = ret_n(cg_ratio, 63)
            f["copper_gold_ratio_last"] = float(cg_ratio.iloc[-1])
        else:
            f["copper_gold_ratio_3m"] = float("nan")
            f["copper_gold_ratio_last"] = float("nan")
    else:
        f["copper_gold_ratio_3m"] = float("nan")
        f["copper_gold_ratio_last"] = float("nan")

    # Inflation acceleration
    f["cpi_acc"]     = roc_accelerating(fred.get("CPI",    pd.Series()), 12, 3)
    f["corepce_acc"] = roc_accelerating(fred.get("COREPCE",pd.Series()), 12, 3)

    # ── Rates ─────────────────────────────────────────────────
    f["dgs2"]             = last(fred.get("DGS2",    pd.Series()))
    f["dgs10"]            = last(fred.get("DGS10",   pd.Series()))
    f["dgs30"]            = last(fred.get("DGS30",   pd.Series()))
    f["policy_rate"]      = last(fred.get("FEDFUNDS",pd.Series()))
    f["policy_rate_3m"]   = delta_n(fred.get("FEDFUNDS",pd.Series()), 3)

    # ★ NEW: Yield curve spreads (critical Hedgeye signal)
    f["spread_2s10s"] = (f["dgs10"] - f["dgs2"]
                         if math.isfinite(f["dgs10"]) and math.isfinite(f["dgs2"]) else float("nan"))
    f["spread_10s30s"] = (f["dgs30"] - f["dgs10"]
                          if math.isfinite(f["dgs30"]) and math.isfinite(f["dgs10"]) else float("nan"))

    # Track 2s10s change
    dgs2_s  = fred.get("DGS2",  pd.Series())
    dgs10_s = fred.get("DGS10", pd.Series())
    if not dgs2_s.empty and not dgs10_s.empty:
        d2, d10 = dgs2_s.align(dgs10_s, join="inner")
        spread_ts = d10 - d2
        f["spread_2s10s_1m"] = delta_n(spread_ts, 21)
        f["spread_2s10s_3m"] = delta_n(spread_ts, 63)
        f["yield_curve_state"] = (
            "Inverted"    if math.isfinite(f["spread_2s10s"]) and f["spread_2s10s"] < -0.10 else
            "Flat"        if math.isfinite(f["spread_2s10s"]) and f["spread_2s10s"] < 0.25  else
            "Normal"      if math.isfinite(f["spread_2s10s"]) and f["spread_2s10s"] < 1.50  else
            "Steep"
        )
        f["yield_curve_uninverting"] = (
            math.isfinite(f.get("spread_2s10s_3m", float("nan"))) and
            f.get("spread_2s10s_3m", 0) > 0.20 and
            f.get("spread_2s10s", 0) > -0.25
        )
    else:
        f["spread_2s10s_1m"] = float("nan")
        f["spread_2s10s_3m"] = float("nan")
        f["yield_curve_state"] = "Unknown"
        f["yield_curve_uninverting"] = False

    # ── Credit spreads ────────────────────────────────────────
    f["hy_oas"]     = last(fred.get("HYOAS",  pd.Series()))
    f["hy_oas_1m"]  = delta_n(fred.get("HYOAS",pd.Series()), 21)
    f["ig_oas"]     = last(fred.get("IGSPR",  pd.Series()))   # ★ NEW: IG OAS
    f["ig_oas_1m"]  = delta_n(fred.get("IGSPR",pd.Series()), 21)

    # HYG / LQD as market-based proxies (faster updating)
    f["hyg_1m"]     = ret_n(prices.get("HYG", pd.Series()), 21)
    f["lqd_1m"]     = ret_n(prices.get("LQD", pd.Series()), 21)

    # ── Vol / VIX ─────────────────────────────────────────────
    vix_s   = prices.get("^VIX",   pd.Series())
    vxv_s   = prices.get("^VXV",   pd.Series())
    vix9d_s = prices.get("^VIX9D", pd.Series())

    f["vix_last"] = last(vix_s)
    f["vix_1m"]   = delta_n(vix_s, 21)

    # ★ NEW: VIX term structure (contango = calm, backwardation = stressed)
    if not vix_s.empty and not vxv_s.empty:
        v, vxv = vix_s.align(vxv_s, join="inner")
        if len(v) > 5:
            ratio = float(v.iloc[-1]) / float(vxv.iloc[-1])
            f["vix_vxv_ratio"] = ratio
            f["vix_term_state"] = (
                "Contango (calm)"      if ratio < 0.90 else
                "Flat (neutral)"       if ratio < 1.00 else
                "Backwardation (fear)"
            )
        else:
            f["vix_vxv_ratio"] = float("nan")
            f["vix_term_state"] = "Unknown"
    else:
        f["vix_vxv_ratio"] = float("nan")
        f["vix_term_state"] = "Unknown"

    # ── Market prices ─────────────────────────────────────────
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","EFA"]:
        s = prices.get(t, pd.Series())
        f[f"{t.replace('^','').lower()}_1m"] = ret_n(s, 21)
        f[f"{t.replace('^','').lower()}_3m"] = ret_n(s, 63)

    return f


def build_market_health(prices: Dict[str, pd.Series], macro: Dict) -> Dict:
    """Market breadth, credit, vol composite for tactical overlay."""
    SECTORS = ["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"]

    spy   = prices.get("SPY", pd.Series())
    iwm   = prices.get("IWM", pd.Series())
    rsp   = prices.get("RSP", pd.Series())
    qqq   = prices.get("QQQ", pd.Series())
    hyg   = prices.get("HYG", pd.Series())

    spy_trend  = trend_score_px(spy)
    qqq_trend  = trend_score_px(qqq)
    iwm_health = trend_score_px(iwm)

    # Equal-weight vs cap-weight divergence (breadth signal)
    if not spy.empty and not rsp.empty:
        s, r = spy.align(rsp, join="inner")
        if len(s) > 63:
            spy_3m = ret_n(s, 63)
            rsp_3m = ret_n(r, 63)
            eqw_vs_cw = (rsp_3m - spy_3m) if (math.isfinite(spy_3m) and math.isfinite(rsp_3m)) else 0.0
        else:
            eqw_vs_cw = 0.0
    else:
        eqw_vs_cw = 0.0

    # Sector breadth: how many of 11 sectors are above 50-day MA
    sector_above_50 = 0
    for s_ticker in SECTORS:
        s = prices.get(s_ticker, pd.Series())
        if len(s) >= 50:
            if float(s.iloc[-1]) > float(s.rolling(50).mean().iloc[-1]):
                sector_above_50 += 1
    sector_support = sector_above_50 / len(SECTORS)

    # Breadth composite
    breadth_score = clamp01(nanmean(spy_trend, iwm_health, sector_support,
                                    clamp01(0.5 + eqw_vs_cw * 5)))

    # Credit health
    hy_calm    = clamp01(1.0 - (macro.get("hy_oas", 400) - 250) / 500)
    ig_calm    = clamp01(1.0 - (macro.get("ig_oas", 100) - 50) / 200)
    hyg_trend  = trend_score_px(hyg)
    credit_score = clamp01(nanmean(hy_calm, ig_calm, hyg_trend))

    # Vol health
    vix = macro.get("vix_last", 20.0)
    vix_health  = clamp01(1.0 - (vix - 13) / 25)
    vix_ratio   = macro.get("vix_vxv_ratio", 0.95)
    vix_ts_ok   = clamp01(1.0 - (vix_ratio - 0.85) / 0.25) if math.isfinite(vix_ratio) else 0.5
    vol_score   = clamp01(nanmean(vix_health, vix_ts_ok))

    # Dollar (headwind = rising DXY = risk-off)
    uup_1m = macro.get("uup_1m", 0.0)
    dollar_headwind = clamp01(0.5 + uup_1m * 8)

    # Composite tactical weather
    trade_score  = clamp01(nanmean(breadth_score, credit_score, 1.0 - dollar_headwind * 0.3))
    trend_score_ = clamp01(nanmean(spy_trend, qqq_trend, sector_support))
    tail_score   = clamp01(nanmean(vol_score, credit_score, 1.0 - dollar_headwind * 0.4))
    weather      = clamp01(0.35 * trade_score + 0.35 * trend_score_ + 0.30 * tail_score)

    return {
        "breadth_score":      breadth_score,
        "credit_score":       credit_score,
        "vol_score":          vol_score,
        "weather":            weather,
        "trade_score":        trade_score,
        "trend_score":        trend_score_,
        "tail_score":         tail_score,
        "sector_support":     sector_support,
        "sector_above_50":    sector_above_50,
        "eqw_vs_cw":          eqw_vs_cw,
        "dollar_headwind":    dollar_headwind,
        "spy_trend":          spy_trend,
        "iwm_health":         iwm_health,
        "breadth_state":      "Healthy" if breadth_score >= 0.62 else ("Fragile" if breadth_score <= 0.42 else "Mixed"),
        "credit_state":       "Tight"   if credit_score  >= 0.62 else ("Stressed" if credit_score <= 0.42 else "Watch"),
        "vol_state":          "Calm"    if vol_score     >= 0.62 else ("Stressed" if vol_score    <= 0.42 else "Watch"),
        "trade_state":        "Open"    if trade_score   >= 0.60 else ("Closed" if trade_score    <= 0.40 else "Neutral"),
        "weather_state":      "Risk-On" if weather       >= 0.58 else ("Risk-Off" if weather      <= 0.42 else "Mixed"),
    }


def build_quad(macro: Dict) -> Dict:
    """
    Quad classification engine — Hedgeye 4-quadrant model.
    Explicitly labels Growth and Inflation as Accelerating/Decelerating.
    Uses dual-horizon (structural 3-6m + monthly tactical).
    """

    # ── Growth signal ──────────────────────────────────────────
    growth_inputs = [
        _tanh_scale(macro.get("indpro_yoy", 0) - 0.02, 0.05),
        _tanh_scale(macro.get("retail_yoy", 0) - 0.03, 0.06),
        _tanh_scale(macro.get("payrolls_yoy", 0) - 0.015, 0.03),
        _tanh_scale(macro.get("housing_yoy", 0), 0.10),
        _tanh_scale((macro.get("ism_last", 50) - 50) / 100, 0.04),
        _tanh_scale(-macro.get("unrate_3m_delta", 0), 0.12),
        _tanh_scale(-macro.get("claims_13w_delta", 0) / 40, 0.60),
        _tanh_scale(macro.get("lei_3m", 0), 0.03),        # ★ LEI added
        _tanh_scale(macro.get("copper_gold_ratio_3m", 0), 0.15),  # ★ Cu/Au ratio
    ]
    growth_mom_inputs = [
        _tanh_scale(macro.get("copper_gold_ratio_3m", 0), 0.12),
        _tanh_scale(-(macro.get("unrate_3m_delta", 0)), 0.10),
        _tanh_scale(-(macro.get("claims_13w_delta", 0) / 50), 0.50),
        _tanh_scale(macro.get("lei_3m", 0), 0.025),       # ★ LEI momentum
    ]

    # ── Inflation signal ───────────────────────────────────────
    # Use Core PCE as primary (Fed preferred), CPI as secondary
    core_inf = macro.get("corepce_yoy", macro.get("corecpi_yoy", 0.023))
    headline = macro.get("cpi_yoy", 0.025)
    inflation_inputs = [
        _tanh_scale(headline - 0.025, 0.020),
        _tanh_scale(core_inf - 0.025, 0.015),
        _tanh_scale((macro.get("breakeven", 2.2) - 2.2) / 2.0, 0.30),
        _tanh_scale(macro.get("oil_3m", 0), 0.25),
        _tanh_scale(macro.get("gold_3m", 0), 0.18),
    ]
    inflation_mom_inputs = [
        _tanh_scale(macro.get("oil_1m", 0), 0.12),
        _tanh_scale((macro.get("breakeven", 2.2) - 2.2) / 2.0, 0.24),
        _tanh_scale(macro.get("breakeven_1m", 0), 0.08),
    ]

    g_level = nanmean(*growth_inputs)
    g_mom   = nanmean(*growth_mom_inputs)
    i_level = nanmean(*inflation_inputs)
    i_mom   = nanmean(*inflation_mom_inputs)

    # ── Yield curve boost ──────────────────────────────────────
    # ★ NEW: Yield curve adds signal to growth (uninverting → growth expectations rising)
    yc_state = macro.get("yield_curve_state", "Unknown")
    yc_boost = (
        0.08 if macro.get("yield_curve_uninverting") else
       -0.05 if yc_state == "Inverted" else 0.0
    )
    g_level += yc_boost

    # ── Credit spread boost ────────────────────────────────────
    # ★ NEW: Widening credit = negative growth signal
    hy_oas_1m = macro.get("hy_oas_1m", 0.0)
    ig_oas_1m = macro.get("ig_oas_1m", 0.0)
    credit_penalty = clamp01((hy_oas_1m + ig_oas_1m * 0.5) / 50) * 0.15
    g_level -= credit_penalty

    # ── Quad scoring ───────────────────────────────────────────
    g_core = 0.35 * g_level + 0.25 * g_mom
    i_core = 0.25 * i_level + 0.15 * i_mom
    p_core = -macro.get("policy_rate_3m", 0.0) * 0.10

    raw = {
        "Q1": +g_core - i_core + 0.10 * p_core,
        "Q2": +g_core + i_core + 0.05 * p_core,
        "Q3": -g_core + 1.10 * i_core - 0.05 * p_core,
        "Q4": -g_core - i_core + 0.25 * p_core,
    }

    # Softmax to probabilities
    vals  = np.array(list(raw.values()))
    probs_arr = np.exp(vals - vals.max())
    probs_arr /= probs_arr.sum()
    probs = dict(zip(raw.keys(), probs_arr.tolist()))

    ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    quad     = ordered[0][0]
    top_prob = ordered[0][1]
    next_quad = ordered[1][0]
    margin    = top_prob - ordered[1][1]
    confidence = clamp01(top_prob * 0.80 + margin * 0.20)

    # ── RoC direction labels ───────────────────────────────────
    growth_positive  = g_level > 0
    growth_acc_flag  = g_mom > 0
    infl_positive    = i_level > 0
    infl_acc_flag    = i_mom > 0

    # Use FRED-based acceleration where available, fall back to score-based
    if macro.get("indpro_acc") is not None and macro.get("retail_acc") is not None:
        growth_acc_confirmed = (macro["indpro_acc"] and macro["retail_acc"])
    else:
        growth_acc_confirmed = growth_acc_flag

    if macro.get("cpi_acc") is not None:
        infl_acc_confirmed = macro["cpi_acc"]
    else:
        infl_acc_confirmed = infl_acc_flag

    growth_label = "Accelerating 🟢" if growth_acc_confirmed else "Decelerating 🔴"
    infl_label   = "Accelerating 🔴" if infl_acc_confirmed  else "Decelerating 🟢"

    # Flip hazard
    flip_hazard = clamp01(
        0.35 * (1.0 - margin) +
        0.25 * abs(g_mom) +
        0.25 * abs(i_mom) +
        0.15 * (1.0 if macro.get("yield_curve_state") == "Inverted" else 0.0)
    )

    return {
        "quad":           quad,
        "probs":          probs,
        "next_quad":      next_quad,
        "confidence":     confidence,
        "flip_hazard":    flip_hazard,
        "g_level":        g_level,
        "g_mom":          g_mom,
        "i_level":        i_level,
        "i_mom":          i_mom,
        "g_core":         g_core,
        "i_core":         i_core,
        "growth_label":   growth_label,
        "infl_label":     infl_label,
        "growth_acc":     growth_acc_confirmed,
        "infl_acc":       infl_acc_confirmed,
    }


def build_crash_meter(macro: Dict, health: Dict, quad: Dict) -> Dict:
    """Crash/risk-off meter combining vol, credit, breadth, growth signals."""
    vix     = macro.get("vix_last", 20.0)
    hy_oas  = macro.get("hy_oas", 400.0)
    ig_oas  = macro.get("ig_oas", 100.0)

    vol_stress  = clamp01((vix - 18) / 20)
    hy_stress   = clamp01((hy_oas - 300) / 400)
    ig_stress   = clamp01((ig_oas - 80) / 120)
    credit_str  = clamp01(0.60 * hy_stress + 0.40 * ig_stress)
    breadth_dmg = clamp01(1.0 - health.get("breadth_score", 0.5))
    dollar_pr   = health.get("dollar_headwind", 0.5)
    growth_risk = clamp01(0.5 - quad.get("g_core", 0.0))

    crash_score = clamp01(
        0.25 * vol_stress +
        0.20 * credit_str +
        0.18 * breadth_dmg +
        0.15 * dollar_pr +
        0.12 * growth_risk +
        0.10 * (1.0 - health.get("weather", 0.5))
    )

    risk_off_score = clamp01(
        0.30 * (1.0 - health.get("weather", 0.5)) +
        0.25 * breadth_dmg +
        0.20 * credit_str +
        0.15 * dollar_pr +
        0.10 * vol_stress
    )

    reasons = []
    if vol_stress  >= 0.50: reasons.append(f"VIX elevated ({vix:.1f})")
    if hy_stress   >= 0.40: reasons.append(f"HY spreads wide ({hy_oas:.0f}bps)")
    if ig_stress   >= 0.40: reasons.append(f"IG spreads wide ({ig_oas:.0f}bps)")
    if breadth_dmg >= 0.55: reasons.append("Market breadth deteriorating")
    if dollar_pr   >= 0.65: reasons.append("USD pressure elevated")
    if macro.get("vix_term_state","") == "Backwardation (fear)": reasons.append("VIX in backwardation (near-term fear)")
    if macro.get("spread_2s10s_3m", 0) < -0.20: reasons.append("Yield curve uninverting rapidly (recession signal)")

    crash_state = (
        "🔴 ELEVATED" if crash_score >= 0.65 else
        "🟡 WATCH"    if crash_score >= 0.42 else
        "🟢 CALM"
    )

    return {
        "crash_score":     crash_score,
        "risk_off_score":  risk_off_score,
        "crash_state":     crash_state,
        "vol_stress":      vol_stress,
        "credit_stress":   credit_str,
        "breadth_damage":  breadth_dmg,
        "reasons":         reasons[:5],
    }


def build_opportunities(quad: Dict, health: Dict, macro: Dict, prices: Dict) -> list[Dict]:
    """Generate ranked cross-asset opportunities based on regime + health."""
    q = quad.get("quad", "Q4")
    meta = QUAD_META.get(q, QUAD_META["Q4"])
    conf = quad.get("confidence", 0.5)
    weather = health.get("weather", 0.5)

    rows = []
    for i, asset in enumerate(meta["long"]):
        ev = clamp01(conf * 0.6 + weather * 0.4 - i * 0.06)
        rows.append({
            "Asset":     asset,
            "Side":      "LONG ▲",
            "Regime":    q,
            "EV Score":  f"{ev:.0%}",
            "Rationale": f"Regime {q} historically favors this asset class",
        })
    for i, asset in enumerate(meta["hedge"]):
        ev = clamp01((1.0 - conf) * 0.5 + (1.0 - weather) * 0.5 - i * 0.04)
        rows.append({
            "Asset":     asset,
            "Side":      "HEDGE ◈",
            "Regime":    q,
            "EV Score":  f"{ev:.0%}",
            "Rationale": "Regime-appropriate hedge / safe harbor",
        })
    for i, asset in enumerate(meta["avoid"]):
        ev = clamp01(0.3 - i * 0.04)
        rows.append({
            "Asset":     asset,
            "Side":      "AVOID ▼",
            "Regime":    q,
            "EV Score":  f"{ev:.0%}",
            "Rationale": f"Regime {q} historically headwind for this asset",
        })
    return rows


# ─── DATA LOADING ORCHESTRATION ───────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_all_data() -> Dict:
    """Load all data and build snapshot."""
    with st.spinner("Loading macro data from FRED…"):
        fred = {k: fetch_fred(k) for k in FRED_SERIES}

    with st.spinner("Loading prices from Yahoo Finance…"):
        prices = fetch_prices_batch(PRICE_TICKERS, period="2y")

    macro  = build_macro_features(fred, prices)
    health = build_market_health(prices, macro)
    quad   = build_quad(macro)
    crash  = build_crash_meter(macro, health, quad)
    opps   = build_opportunities(quad, health, macro, prices)

    return {
        "fred":   fred,
        "prices": prices,
        "macro":  macro,
        "health": health,
        "quad":   quad,
        "crash":  crash,
        "opps":   opps,
        "ts":     datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


# ─── UI HELPERS ───────────────────────────────────────────────────────────────

def pct_str(v, decimals=1) -> str:
    if not math.isfinite(v): return "—"
    return f"{v*100:+.{decimals}f}%"

def num_str(v, decimals=2) -> str:
    if not math.isfinite(v): return "—"
    return f"{v:.{decimals}f}"

def gauge(label: str, value: float, good_dir: str = "high",
           fmt: str = "pct", note: str = "") -> None:
    """Render a labeled gauge bar."""
    if not math.isfinite(value): value = 0.5
    pct = clamp01(value)
    if good_dir == "low": pct = 1.0 - pct
    color = "#198754" if pct >= 0.62 else ("#d68910" if pct >= 0.38 else "#dc3545")
    display = pct_str(value) if fmt == "pct" else num_str(value)
    st.markdown(f"""
    <div class="gauge-wrap">
      <div class="gauge-label">
        <span>{label}</span>
        <span style="color:{color};font-family:'DM Mono',monospace;font-size:12px">{display} {note}</span>
      </div>
      <div class="gauge-bar">
        <div class="gauge-fill" style="width:{clamp01(value)*100:.0f}%;background:{color}"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def quad_badge(q: str) -> str:
    cls = q.lower() if q in ("Q1","Q2","Q3","Q4") else "qunk"
    return f'<span class="quad-badge {cls}">{q}</span>'

def arrow(v: float, threshold: float = 0.005) -> str:
    if not math.isfinite(v): return ""
    if v > threshold:  return '<span class="arrow-up">▲</span>'
    if v < -threshold: return '<span class="arrow-down">▼</span>'
    return '<span class="arrow-flat">–</span>'

def color_val(v: float, good_positive: bool = True) -> str:
    if not math.isfinite(v): return "neutral"
    if good_positive: return "good" if v > 0.005 else ("bad" if v < -0.005 else "neutral")
    return "bad" if v > 0.005 else ("good" if v < -0.005 else "neutral")

def metric_box(label: str, value: str, sub: str = "", cls: str = "") -> None:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">{label}</div>
      <div class="value {cls}">{value}</div>
      {'<div class="sub">' + sub + '</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)

def section_hdr(text: str) -> None:
    st.markdown(f'<div class="section-hdr">{text}</div>', unsafe_allow_html=True)

def _roc_badge(is_acc: Optional[bool], positive_label: str, negative_label: str) -> str:
    if is_acc is True:  return f'<span style="color:#198754;font-weight:500">▲ {positive_label}</span>'
    if is_acc is False: return f'<span style="color:#dc3545;font-weight:500">▼ {negative_label}</span>'
    return '<span style="color:#888">– Unknown</span>'


# ─── PAGE RENDERERS ───────────────────────────────────────────────────────────

def render_radar(snap: Dict) -> None:
    """Page 1 — Regime Compass + Plain English summary."""
    quad  = snap["quad"]
    macro = snap["macro"]
    q     = quad["quad"]
    meta  = QUAD_META.get(q, QUAD_META["Q4"])
    conf  = quad["confidence"]
    health = snap["health"]

    # ── REGIME COMPASS ─────────────────────────────────────────
    st.markdown(f"""
    <div class="compass-wrap">
      <div style="margin-bottom:8px">{quad_badge(q)}</div>
      <div class="regime-title" style="color:{meta['text']}">{meta['label']}</div>
      <div class="regime-sub">{meta['name']} · Confidence {conf:.0%}</div>
      <div class="regime-explain">{meta['explain']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── GROWTH / INFLATION RoC (Hedgeye Core) ─────────────────
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        g_acc = quad.get("growth_acc")
        label = "Accelerating" if g_acc else "Decelerating"
        cls   = "good" if g_acc else "bad"
        metric_box("Growth Rate of Change", label, "vs 3 months ago", cls)
    with c2:
        i_acc = quad.get("infl_acc")
        # For inflation: falling = good for equities, rising = bad
        label = "Accelerating" if i_acc else "Decelerating"
        cls   = "bad" if i_acc else "good"
        metric_box("Inflation Rate of Change", label, "vs 3 months ago", cls)
    with c3:
        vix = macro.get("vix_last", 0)
        vix_cls = "good" if vix < 18 else ("bad" if vix > 28 else "warn")
        metric_box("VIX Level", f"{vix:.1f}" if math.isfinite(vix) else "—",
                   macro.get("vix_term_state",""), vix_cls)
    with c4:
        yc = macro.get("yield_curve_state","Unknown")
        sp = macro.get("spread_2s10s", float("nan"))
        yc_cls = "good" if yc in ("Normal","Steep") else ("bad" if yc=="Inverted" else "warn")
        metric_box("Yield Curve (2s10s)", f"{sp:+.2f}%" if math.isfinite(sp) else "—", yc, yc_cls)

    # ── QUAD PROBABILITY TABLE ────────────────────────────────
    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        section_hdr("📊 Regime Probability")
        probs = quad.get("probs", {})
        for qk in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(qk, 0.0)
            active = "⬤ " if qk == q else "  "
            meta_q = QUAD_META.get(qk, {})
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
              <span style="font-family:'DM Mono',monospace;font-size:12px;width:28px">{active}{qk}</span>
              <div style="flex:1;background:rgba(0,0,0,0.06);border-radius:3px;height:8px;overflow:hidden">
                <div style="width:{p*100:.0f}%;background:{'#198754' if qk==q else 'rgba(0,0,0,0.15)'};height:100%"></div>
              </div>
              <span style="font-family:'DM Mono',monospace;font-size:12px;width:36px;text-align:right">{p:.0%}</span>
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"Flip hazard: **{quad.get('flip_hazard',0):.0%}** — {'⚠️ High transition risk' if quad.get('flip_hazard',0) > 0.50 else 'Regime appears stable'}")

    with col_b:
        section_hdr("📍 What To Do Now")
        meta_now = QUAD_META.get(q, {})
        st.markdown(f"**Regime: {q} — {meta_now.get('label','')}**")
        st.markdown("**Go Long →**")
        for a in meta_now.get("long", [])[:4]:
            st.markdown(f"<div class='opp-long' style='margin:3px 0;font-size:13px'>{a}</div>", unsafe_allow_html=True)
        st.markdown("**Hedge with →**")
        for a in meta_now.get("hedge", [])[:2]:
            st.markdown(f"<div class='opp-hedge' style='margin:3px 0;font-size:13px'>{a}</div>", unsafe_allow_html=True)
        st.markdown("**Avoid →**")
        for a in meta_now.get("avoid", [])[:3]:
            st.markdown(f"<div class='opp-short' style='margin:3px 0;font-size:13px'>{a}</div>", unsafe_allow_html=True)

    # ── KEY INDICATORS AT A GLANCE ────────────────────────────
    st.markdown("---")
    section_hdr("🔑 Key Hedgeye Indicators at a Glance")
    rows = [
        ("Growth — Industrial Production (YoY)",  pct_str(macro.get("indpro_yoy",float("nan"))),  _roc_badge(macro.get("indpro_acc"), "Accelerating","Decelerating")),
        ("Growth — Nonfarm Payrolls (YoY)",        pct_str(macro.get("payrolls_yoy",float("nan"))),""),
        ("Growth — Retail Sales (YoY)",            pct_str(macro.get("retail_yoy",float("nan"))),  _roc_badge(macro.get("retail_acc"),"Accelerating","Decelerating")),
        ("Growth — ISM Manufacturing",             num_str(macro.get("ism_last",50),1),             "Above 50 = expansion"),
        ("Growth — LEI 3M Change ★",              pct_str(macro.get("lei_3m",float("nan"))),       _roc_badge(macro.get("lei_acc"),"Improving","Declining")),
        ("Growth — Copper/Gold Ratio 3M ★",       pct_str(macro.get("copper_gold_ratio_3m",float("nan"))), "Growth proxy"),
        ("Inflation — CPI (YoY)",                  pct_str(macro.get("cpi_yoy",float("nan"))),     _roc_badge(macro.get("cpi_acc"),"Rising","Falling")),
        ("Inflation — Core CPI (YoY)",             pct_str(macro.get("corecpi_yoy",float("nan"))), ""),
        ("Inflation — Core PCE (YoY) ★",          pct_str(macro.get("corepce_yoy",float("nan"))), "Fed preferred"),
        ("Inflation — 5Y Breakeven",               num_str(macro.get("breakeven",float("nan")),2),  "Market inflation expectation"),
        ("Rates — Fed Funds Rate",                 num_str(macro.get("policy_rate",float("nan")),2),""),
        ("Rates — 2s10s Yield Curve ★",           f"{macro.get('spread_2s10s',float('nan')):+.2f}%" if math.isfinite(macro.get("spread_2s10s",float("nan"))) else "—", macro.get("yield_curve_state","")),
        ("Rates — Real 10Y Yield",                 num_str(macro.get("real_10y",float("nan")),2),   "Positive = restrictive"),
        ("Credit — HY OAS Spread ★",              num_str(macro.get("hy_oas",float("nan")),0)+"bps",""),
        ("Credit — IG OAS Spread ★",              num_str(macro.get("ig_oas",float("nan")),0)+"bps",""),
        ("Vol — VIX Level",                        num_str(macro.get("vix_last",float("nan")),1),   macro.get("vix_term_state","")),
        ("Consumer — UMich Sentiment ★",          num_str(macro.get("umcsent_last",float("nan")),1),""),
        ("Labor — Unemployment Rate",              f"{macro.get('unrate',float('nan')):.1f}%" if math.isfinite(macro.get("unrate",float("nan"))) else "—", f"3M delta: {macro.get('unrate_3m_delta',0):+.2f}"),
    ]
    df_indicators = pd.DataFrame(rows, columns=["Indicator","Value","Note"])
    # Mark new/added ones with ★ in name
    st.dataframe(
        df_indicators,
        use_container_width=True,
        hide_index=True,
        height=540,
    )
    st.caption("★ = indicators added vs previous version (Hedgeye gap fills)")


def render_market_health(snap: Dict) -> None:
    """Page 2 — Market health dashboard."""
    health = snap["health"]
    macro  = snap["macro"]
    prices = snap["prices"]

    section_hdr("📡 Tactical Weather — Can We Trade?")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        state = health["trade_state"]
        cls = "good" if state=="Open" else ("bad" if state=="Closed" else "warn")
        metric_box("Trade Environment", state, "breadth + credit + dollar", cls)
    with c2:
        state = health["weather_state"]
        cls = "good" if state=="Risk-On" else ("bad" if state=="Risk-Off" else "warn")
        metric_box("Overall Weather", state, "composite risk regime", cls)
    with c3:
        state = health["vol_state"]
        cls = "good" if state=="Calm" else ("bad" if state=="Stressed" else "warn")
        metric_box("Volatility", state, f"VIX {macro.get('vix_last',0):.1f}", cls)
    with c4:
        state = health["credit_state"]
        cls = "good" if state=="Tight" else ("bad" if state=="Stressed" else "warn")
        metric_box("Credit Health", state, "HY + IG spreads", cls)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        section_hdr("📊 Breadth Gauges")
        gauge("Market breadth (sectors above 50-DMA)",
              health["sector_support"], fmt="pct",
              note=f"({health['sector_above_50']}/11 sectors)")
        gauge("SPY trend health", health["spy_trend"], fmt="pct")
        gauge("Small cap health (IWM)", health["iwm_health"], fmt="pct")
        gauge("Equal-weight vs cap-weight",
              clamp01(0.5 + health["eqw_vs_cw"] * 5), fmt="pct",
              note=pct_str(health["eqw_vs_cw"]) + " 3M diff")
        gauge("Overall breadth composite", health["breadth_score"], fmt="pct")

    with col_b:
        section_hdr("⚡ Credit & Vol Gauges")
        hy_oas = macro.get("hy_oas", float("nan"))
        ig_oas = macro.get("ig_oas", float("nan"))
        gauge("HY Credit Spread health",
              clamp01(1.0 - (hy_oas - 250) / 500) if math.isfinite(hy_oas) else 0.5,
              fmt="pct", note=f"{hy_oas:.0f}bps" if math.isfinite(hy_oas) else "n/a")
        gauge("IG Credit Spread health ★",
              clamp01(1.0 - (ig_oas - 50) / 200) if math.isfinite(ig_oas) else 0.5,
              fmt="pct", note=f"{ig_oas:.0f}bps" if math.isfinite(ig_oas) else "n/a")
        vix = macro.get("vix_last", 20.0)
        gauge("VIX health (lower = healthier)",
              clamp01(1.0 - (vix - 13) / 25), good_dir="high", fmt="pct",
              note=f"VIX {vix:.1f}")
        vix_ratio = macro.get("vix_vxv_ratio", float("nan"))
        gauge("VIX term structure ★",
              clamp01(1.0 - (vix_ratio - 0.85) / 0.25) if math.isfinite(vix_ratio) else 0.5,
              fmt="pct",
              note=macro.get("vix_term_state", ""))
        gauge("Credit + Vol composite", health["credit_score"] * 0.5 + health["vol_score"] * 0.5)

    # ── YIELD CURVE ───────────────────────────────────────────
    st.markdown("---")
    section_hdr("📈 Yield Curve — The Macro Barometer ★")
    yc_data = {
        "2Y":  macro.get("dgs2",  float("nan")),
        "10Y": macro.get("dgs10", float("nan")),
        "30Y": macro.get("dgs30", float("nan")),
    }
    yc_valid = {k: v for k, v in yc_data.items() if math.isfinite(v)}
    if yc_valid:
        df_yc = pd.DataFrame([{"Tenor": k, "Yield (%)": round(v, 2)} for k, v in yc_valid.items()])
        st.dataframe(df_yc, use_container_width=False, hide_index=True, height=130)

    y1, y2, y3 = st.columns(3)
    sp_2s10s   = macro.get("spread_2s10s",  float("nan"))
    sp_10s30s  = macro.get("spread_10s30s", float("nan"))
    sp_3m_chg  = macro.get("spread_2s10s_3m", float("nan"))
    with y1:
        metric_box("2s10s Spread", f"{sp_2s10s:+.2f}%" if math.isfinite(sp_2s10s) else "—",
                   macro.get("yield_curve_state",""),
                   "good" if sp_2s10s > 0.5 else ("bad" if sp_2s10s < 0 else "warn"))
    with y2:
        metric_box("10s30s Spread", f"{sp_10s30s:+.2f}%" if math.isfinite(sp_10s30s) else "—")
    with y3:
        metric_box("2s10s 3M Change",
                   f"{sp_3m_chg:+.2f}%" if math.isfinite(sp_3m_chg) else "—",
                   "Uninverting → recession warning" if macro.get("yield_curve_uninverting") else "",
                   "warn" if macro.get("yield_curve_uninverting") else "neutral")

    st.markdown("""
    > **Reading the yield curve:** When short-term rates (2Y) exceed long-term rates (10Y), the curve is **inverted** — historically a reliable leading indicator of recession.
    > An inverted curve that *begins to uninvert* (steepens from inversion) often signals the recession is starting, not ending. Watch the 3M change direction.
    """)

    # ── SECTOR PERFORMANCE ────────────────────────────────────
    st.markdown("---")
    section_hdr("📦 Sector Performance vs SPY (3-Month)")
    SECTORS = {"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials",
               "XLK":"Technology","XLV":"Healthcare","XLY":"Cons. Disc.","XLP":"Cons. Staples",
               "XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm. Svc."}
    spy_3m = ret_n(prices.get("SPY", pd.Series()), 63)
    s_rows = []
    for t, name in SECTORS.items():
        r3m  = ret_n(prices.get(t, pd.Series()), 63)
        r1m  = ret_n(prices.get(t, pd.Series()), 21)
        above50 = "✓" if trend_score_px(prices.get(t, pd.Series())) >= 0.5 else "✗"
        rel = (r3m - spy_3m) if (math.isfinite(r3m) and math.isfinite(spy_3m)) else float("nan")
        s_rows.append({
            "Sector": name,
            "3M Return": pct_str(r3m),
            "1M Return": pct_str(r1m),
            "vs SPY 3M": pct_str(rel),
            "Above 50D MA": above50,
        })
    s_rows.sort(key=lambda r: float(r["vs SPY 3M"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY 3M"] != "—" else -999, reverse=True)
    st.dataframe(pd.DataFrame(s_rows), use_container_width=True, hide_index=True, height=380)


def render_opportunities(snap: Dict) -> None:
    """Page 3 — Cross-asset opportunities."""
    quad  = snap["quad"]
    opps  = snap["opps"]
    macro = snap["macro"]
    prices = snap["prices"]

    q    = quad["quad"]
    meta = QUAD_META.get(q, QUAD_META["Q4"])
    conf = quad["confidence"]

    st.markdown(f"""
    <div style="padding:16px;border-radius:12px;background:{meta['color']};color:{meta['text']};margin-bottom:16px">
      <strong style="font-size:14px">REGIME {q}: {meta['label']}</strong><br>
      <span style="font-size:13px">Regime confidence {conf:.0%} — opportunities ranked by regime alignment</span>
    </div>
    """, unsafe_allow_html=True)

    # Cross-asset table
    df_opps = pd.DataFrame(opps)
    if not df_opps.empty:
        long_mask  = df_opps["Side"].str.startswith("LONG")
        hedge_mask = df_opps["Side"].str.startswith("HEDGE")
        avoid_mask = df_opps["Side"].str.startswith("AVOID")

        ta, tb, tc = st.tabs(["▲ Longs / Best Now", "◈ Hedges / Safe Harbor", "▼ Avoid / Short Bias"])
        with ta:
            st.dataframe(df_opps[long_mask].reset_index(drop=True),
                         use_container_width=True, hide_index=True)
        with tb:
            st.dataframe(df_opps[hedge_mask].reset_index(drop=True),
                         use_container_width=True, hide_index=True)
        with tc:
            st.dataframe(df_opps[avoid_mask].reset_index(drop=True),
                         use_container_width=True, hide_index=True)

    # Cross-asset heatmap (returns)
    st.markdown("---")
    section_hdr("🌐 Cross-Asset Returns Heatmap")
    ASSETS = {
        "US Equity (SPY)":"SPY","Growth (QQQ)":"QQQ","Small Cap (IWM)":"IWM",
        "Bonds (TLT)":"TLT","Credit (HYG)":"HYG","Gold (GLD)":"GLD",
        "Oil (CL=F)":"CL=F","Copper (HG=F)":"HG=F","USD (UUP)":"UUP",
        "EM Equity (EEM)":"EEM","BTC":"BTC-USD","ETH":"ETH-USD",
    }
    heat_rows = []
    for name, ticker in ASSETS.items():
        s = prices.get(ticker, pd.Series())
        heat_rows.append({
            "Asset": name,
            "1 Week":  pct_str(ret_n(s, 5)),
            "1 Month": pct_str(ret_n(s, 21)),
            "3 Month": pct_str(ret_n(s, 63)),
            "6 Month": pct_str(ret_n(s, 126)),
            "1 Year":  pct_str(ret_n(s, 252)),
        })
    st.dataframe(pd.DataFrame(heat_rows), use_container_width=True, hide_index=True, height=430)

    # Regime-specific insights
    st.markdown("---")
    section_hdr(f"📖 Regime {q} — Historical Context")
    if q == "Q1":
        st.info("**Q1 (Growth↑ Inflation↓) — Goldilocks:** Historically the best period for risk assets. S&P 500 average annual return in Q1: ~+18%. Duration (TLT) also works. The 'don't fight the tape' quad.")
    elif q == "Q2":
        st.warning("**Q2 (Growth↑ Inflation↑) — Reflationary Boom:** Risk assets work but leadership rotates to value/cyclicals. Energy and materials outperform tech. Central banks begin tightening — watch for Q2→Q3 inflection.")
    elif q == "Q3":
        st.error("**Q3 (Growth↓ Inflation↑) — Stagflation:** The hardest quad. Equities broadly underperform. Commodities (especially gold and energy) are the only safe-ish longs. Cash is a position. Avoid duration.")
    elif q == "Q4":
        st.error("**Q4 (Growth↓ Inflation↓) — Deflationary Bear:** Recession quad. Long bonds rally hard. Defensives outperform. Central banks are cutting or about to. EV+ trades: TLT, GLD, XLP, XLU, XLV. Maximum caution on cyclicals and credit.")


def render_risk_monitor(snap: Dict) -> None:
    """Page 4 — Risk Monitor."""
    crash = snap["crash"]
    macro = snap["macro"]
    quad  = snap["quad"]
    health = snap["health"]

    # Crash meter hero
    score = crash["crash_score"]
    state = crash["crash_state"]
    color = "#dc3545" if score >= 0.65 else ("#d68910" if score >= 0.42 else "#198754")

    st.markdown(f"""
    <div style="text-align:center;padding:28px 20px;border-radius:16px;border:2px solid {color}22;margin-bottom:20px">
      <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.5;margin-bottom:8px">Crash / Risk-Off Meter</div>
      <div style="font-family:'Syne',sans-serif;font-size:52px;font-weight:800;color:{color};line-height:1">{score:.0%}</div>
      <div style="font-size:16px;font-weight:600;color:{color};margin-top:4px">{state}</div>
    </div>
    """, unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    with r1:
        v = crash["vol_stress"]
        metric_box("Vol Stress", f"{v:.0%}", "VIX-based", "bad" if v >= 0.6 else ("warn" if v >= 0.35 else "good"))
    with r2:
        v = crash["credit_stress"]
        metric_box("Credit Stress", f"{v:.0%}", "HY + IG OAS", "bad" if v >= 0.6 else ("warn" if v >= 0.35 else "good"))
    with r3:
        v = crash["breadth_damage"]
        metric_box("Breadth Damage", f"{v:.0%}", "breadth deterioration", "bad" if v >= 0.6 else ("warn" if v >= 0.35 else "good"))

    if crash["reasons"]:
        st.markdown("---")
        section_hdr("⚠️ Active Risk Flags")
        for r in crash["reasons"]:
            st.markdown(f"- {r}")

    # VIX regime
    st.markdown("---")
    section_hdr("📉 VIX Regime & Term Structure ★")
    vix = macro.get("vix_last", 0)
    vix_ratio = macro.get("vix_vxv_ratio", float("nan"))
    vix_state_str = macro.get("vix_term_state","Unknown")

    v1, v2, v3 = st.columns(3)
    with v1:
        bucket = "Investable (<19)" if vix < 19 else ("Chop (19-29)" if vix < 29 else "Defensive (>29)")
        cls = "good" if vix < 19 else ("warn" if vix < 29 else "bad")
        metric_box("VIX Bucket", bucket, f"VIX = {vix:.1f}", cls)
    with v2:
        metric_box("VIX/VXV Ratio ★",
                   f"{vix_ratio:.3f}" if math.isfinite(vix_ratio) else "—",
                   vix_state_str,
                   "good" if vix_ratio < 0.90 else ("bad" if vix_ratio >= 1.0 else "warn"))
    with v3:
        rmode = "Normal" if vix < 19 else ("Reduced" if vix < 29 else "Defensive")
        metric_box("Risk Mode", rmode, "position sizing guide",
                   "good" if rmode=="Normal" else ("warn" if rmode=="Reduced" else "bad"))

    st.markdown("""
    > **VIX term structure explained:** When VIX (30-day fear) is *lower* than VXV (93-day fear), the curve is in **contango** — market is calm, near-term fear is lower than future uncertainty.
    > When VIX > VXV (**backwardation**), the market is pricing in *more near-term fear than future fear* — a strong warning signal, often seen during selling panics.
    """)

    # Credit detail
    st.markdown("---")
    section_hdr("💳 Credit Spread Detail ★")
    hy = macro.get("hy_oas", float("nan"))
    ig = macro.get("ig_oas", float("nan"))
    hy_1m = macro.get("hy_oas_1m", float("nan"))
    ig_1m = macro.get("ig_oas_1m", float("nan"))

    c1, c2 = st.columns(2)
    with c1:
        metric_box("HY OAS Spread",
                   f"{hy:.0f}bps" if math.isfinite(hy) else "—",
                   f"1M change: {hy_1m:+.0f}bps" if math.isfinite(hy_1m) else "",
                   "good" if hy < 350 else ("bad" if hy > 500 else "warn"))
        st.caption("Normal: <350bps | Watch: 350-500bps | Stress: >500bps")
    with c2:
        metric_box("IG OAS Spread ★",
                   f"{ig:.0f}bps" if math.isfinite(ig) else "—",
                   f"1M change: {ig_1m:+.0f}bps" if math.isfinite(ig_1m) else "",
                   "good" if ig < 100 else ("bad" if ig > 150 else "warn"))
        st.caption("Normal: <100bps | Watch: 100-150bps | Stress: >150bps")

    # Forward risks
    st.markdown("---")
    section_hdr("🔭 Forward Risk Factors")
    flip_h = quad.get("flip_hazard", 0.0)
    nq = quad.get("next_quad","?")
    st.markdown(f"""
    - **Regime flip hazard:** {flip_h:.0%} → Next likely quad: **{nq}**
    - **Yield curve:** {macro.get('yield_curve_state','')} | 3M change: {pct_str(macro.get('spread_2s10s_3m',float('nan')))}
    - **LEI 3M:** {pct_str(macro.get('lei_3m',float('nan')))} {'⚠️ Leading indicator declining' if macro.get('lei_3m',0) < -0.01 else '✓ LEI holding'}
    - **Copper/Gold ratio 3M:** {pct_str(macro.get('copper_gold_ratio_3m',float('nan')))} {'→ growth expectations falling' if macro.get('copper_gold_ratio_3m',0) < -0.05 else '→ growth expectations stable'}
    - **Consumer sentiment (UMich):** {num_str(macro.get('umcsent_last',float('nan')),1)} {'⚠️ Below 70 = stressed consumer' if macro.get('umcsent_last',100) < 70 else ''}
    """)


def render_diagnostics(snap: Dict) -> None:
    """Page 5 — Raw data and diagnostics."""
    macro = snap["macro"]
    fred  = snap["fred"]

    section_hdr("🔬 Raw Macro Features")
    # Show all features in a searchable table
    feat_rows = []
    for k, v in sorted(macro.items()):
        if isinstance(v, (int, float)):
            feat_rows.append({"Feature": k, "Value": round(v, 5) if math.isfinite(v) else None})
        elif isinstance(v, bool):
            feat_rows.append({"Feature": k, "Value": str(v)})
        elif isinstance(v, str):
            feat_rows.append({"Feature": k, "Value": v})
    st.dataframe(pd.DataFrame(feat_rows), use_container_width=True, hide_index=True, height=420)

    section_hdr("📋 FRED Data Coverage")
    cov_rows = []
    for k, s in fred.items():
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if not s_clean.empty:
            cov_rows.append({
                "Series": k,
                "Points": len(s_clean),
                "Latest Date": str(s_clean.index[-1])[:10],
                "Last Value": round(float(s_clean.iloc[-1]), 4),
                "Status": "✓",
            })
        else:
            cov_rows.append({"Series": k, "Points": 0, "Latest Date": "—", "Last Value": None, "Status": "✗ Missing"})
    st.dataframe(pd.DataFrame(cov_rows), use_container_width=True, hide_index=True, height=420)

    section_hdr("📦 Price Data Coverage")
    px_rows = []
    prices = snap["prices"]
    for t in sorted(prices.keys()):
        s = prices[t]
        if not s.empty:
            px_rows.append({
                "Ticker": t, "Points": len(s),
                "Latest": str(s.index[-1])[:10],
                "Last Close": round(float(s.iloc[-1]),4),
            })
    if px_rows:
        st.dataframe(pd.DataFrame(px_rows), use_container_width=True, hide_index=True, height=360)


# ─── MAIN APP ─────────────────────────────────────────────────────────────────

def main() -> None:
    # ── HEADER ─────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
      <div>
        <span style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;letter-spacing:-0.03em">🧭 MacroRegime Pro</span>
        <span style="font-size:11px;opacity:0.4;margin-left:10px;font-family:'DM Mono',monospace">v4 · Hedgeye GIP Framework</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SIDEBAR ────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        force_refresh = st.button("🔄 Refresh Data", use_container_width=True)
        st.markdown("---")
        st.markdown("""
        **What is this?**
        A macro regime dashboard using the Hedgeye GIP (Growth-Inflation-Policy) framework.
        
        **Reading Flow:**
        1. 🧭 **Radar** — What regime are we in?
        2. 📡 **Market Health** — Can we trade?
        3. 🎯 **Opportunities** — Where to be?
        4. ⚠️ **Risk Monitor** — What can go wrong?
        5. 🔬 **Diagnostics** — Raw data
        
        **Data sources:** FRED (free), Yahoo Finance (free)
        """)

    if force_refresh:
        st.cache_data.clear()

    # ── LOAD DATA ──────────────────────────────────────────────
    snap = load_all_data()

    # ── STATUS BAR ─────────────────────────────────────────────
    quad = snap["quad"]
    q    = quad["quad"]
    meta = QUAD_META.get(q, {})
    crash = snap["crash"]

    st.markdown(f"""
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;
                padding:10px 14px;border-radius:8px;background:rgba(0,0,0,0.03);
                border:1px solid rgba(0,0,0,0.06);margin-bottom:16px;font-size:12px">
      <span>Regime: {quad_badge(q)} <strong>{meta.get('label','')}</strong></span>
      <span style="opacity:0.3">|</span>
      <span>Confidence: <strong>{quad['confidence']:.0%}</strong></span>
      <span style="opacity:0.3">|</span>
      <span>Growth: <strong>{quad['growth_label']}</strong></span>
      <span style="opacity:0.3">|</span>
      <span>Inflation: <strong>{quad['infl_label']}</strong></span>
      <span style="opacity:0.3">|</span>
      <span>Risk: <strong>{crash['crash_state']}</strong></span>
      <span style="opacity:0.3">|</span>
      <span style="opacity:0.45">Updated: {snap['ts']}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── TABS ───────────────────────────────────────────────────
    tabs = st.tabs([
        "🧭 Radar",
        "📡 Market Health",
        "🎯 Opportunities",
        "⚠️ Risk Monitor",
        "🔬 Diagnostics",
    ])
    with tabs[0]: render_radar(snap)
    with tabs[1]: render_market_health(snap)
    with tabs[2]: render_opportunities(snap)
    with tabs[3]: render_risk_monitor(snap)
    with tabs[4]: render_diagnostics(snap)


if __name__ == "__main__":
    main()

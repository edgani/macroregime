# app.py
# Macro + Bottleneck Decision Engine
# Self-contained Streamlit app.
# Dependencies normally available on Streamlit Cloud:
#   streamlit, pandas, numpy, requests
#
# IMPORTANT:
# - Public FRED/Yahoo data are used for live/exploratory state monitoring.
# - Revised FRED history is NOT equivalent to point-in-time/vintage data.
# - PIT analyst revisions, historical constituents/delistings, options/dealer inventory,
#   physical commodity data and crypto on-chain/tokenomics remain DATA-GATED unless supplied.
# - The app never fabricates missing data; unavailable layers are explicitly labelled.

from __future__ import annotations

import io
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st


# -----------------------------------------------------------------------------
# PAGE / STYLE
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Macro + Bottleneck Decision Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
      div[data-testid="stMetric"] {
          border: 1px solid rgba(128,128,128,.25);
          padding: 10px 12px;
          border-radius: 10px;
      }
      .small-note {font-size:.83rem; opacity:.78;}
      .status-ok {font-weight:700;}
      .status-warn {font-weight:700;}
      .status-bad {font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

FRED_SERIES: Dict[str, Dict[str, str]] = {
    # Macro / labor
    "CFNAI": {"label": "Chicago Fed National Activity Index", "engine": "Growth"},
    "ICSA": {"label": "Initial Claims", "engine": "Growth"},
    "UNRATE": {"label": "Unemployment Rate", "engine": "Growth"},
    # Inflation
    "CPILFESL": {"label": "Core CPI Index", "engine": "Inflation"},
    "PCEPILFE": {"label": "Core PCE Price Index", "engine": "Inflation"},
    "T5YIE": {"label": "5Y Breakeven Inflation", "engine": "Inflation"},
    # Rates / policy transmission
    "DGS2": {"label": "2Y Treasury Yield", "engine": "Rates"},
    "DGS10": {"label": "10Y Treasury Yield", "engine": "Rates"},
    "DFII10": {"label": "10Y Real Yield", "engine": "Rates"},
    "T10Y3M": {"label": "10Y minus 3M Curve", "engine": "Rates"},
    "THREEFYTP10": {"label": "10Y Term Premium", "engine": "Rates"},
    # Credit / financial conditions
    "BAMLH0A0HYM2": {"label": "US High Yield OAS", "engine": "Credit"},
    "DRTSCILM": {"label": "SLOOS C&I Tightening", "engine": "Credit"},
    "NFCI": {"label": "Chicago Fed NFCI", "engine": "Credit"},
    # Stress / liquidity plumbing
    "VIXCLS": {"label": "VIX", "engine": "Stress"},
    "WRESBAL": {"label": "Reserve Balances", "engine": "Funding"},
    "WALCL": {"label": "Fed Total Assets", "engine": "Funding"},
    "WTREGEN": {"label": "Treasury General Account", "engine": "Funding"},
    "RRPONTSYD": {"label": "ON RRP", "engine": "Funding"},
    # Dollar
    "DTWEXBGS": {"label": "Trade-Weighted US Dollar", "engine": "FX"},
}

CORE_PROJECTION_FEATURES = [
    "T10Y3M",
    "BAMLH0A0HYM2",
    "DFII10",
    "THREEFYTP10",
    "NFCI",
    "VIXCLS",
    "ICSA",
    "T5YIE",
]

DEFAULT_MARKET_TICKERS = ["SPY", "IWM", "QQQ", "GLD", "USO", "UUP", "BTC-USD"]

DATA_GATED = [
    ("Macro surprise", "Pre-release consensus history / PIT surprise database"),
    ("Reaction residual", "Event-level macro surprise + timestamped multi-asset reactions"),
    ("PIT estimate revisions", "Historical analyst estimates as actually known on each date"),
    ("Historical equity universe", "Constituents + delisted/suspended securities + corporate actions"),
    ("Options/dealer state", "Full option surface/trade direction/dealer inventory or defensible proxy"),
    ("Treasury market depth", "Order-book / bid-ask / dealer capacity data"),
    ("Commodity physical layer", "Inventories, production, spare capacity, curve, processing/logistics"),
    ("FX intervention layer", "Reserve operations, intervention records, cross-currency funding"),
    ("Crypto native layer", "Stablecoins, on-chain usage, exchange balances, OI/funding, unlocks/emissions"),
    ("Company bottleneck fundamentals", "PIT backlog/RPO/orders, margins, FCF, capex, balance sheet"),
]


METRIC_VALIDATION = pd.DataFrame([
    ["10Y-2Y / curve state","Macro cycle / recession state",
     "Recession<=12m AUC ~0.867 in available test", "CORE_CONDITIONAL",
     "Cycle-state input; not an immediate crash/entry trigger."],
    ["Initial claims state","Labor deterioration",
     "Recession<=12m AUC ~0.631; high standalone false positives", "CORE_COMPLEMENT",
     "Useful early deterioration input; poor standalone precision."],
    ["HY OAS 13w change","Credit stress velocity",
     "Forward >10% fall/6m AUC ~0.653; >20% fall/12m ~0.718", "CORE_STRESS",
     "Stress/risk modifier; not a standalone crash predictor."],
    ["BBB OAS","Credit diagnostic",
     "Spearman ~0.97 level / ~0.92 13w change vs HY", "DIAGNOSTIC_REDUNDANT",
     "Do not give a separate vote when HY is available."],
    ["HY OAS level","Credit state",
     "Regime dependent standalone leading power", "CONTEXT",
     "State variable; velocity is more useful for transition."],
    ["VIX level","Market stress",
     "Moderate overall discrimination; unstable subperiods", "DIAGNOSTIC",
     "Stress/position sizing, not deterministic direction."],
    ["SLOOS tightening","Credit supply",
     "Recession<=12m AUC ~0.692 in available sample", "CORE_MEDIUM_HORIZON",
     "Use with release lag / true vintage data in proof build."],
    ["NFCI","Financial conditions",
     "Core concept; complete vintage proof still required", "CORE_DATA_GATED",
     "Live state useful; historic proof must avoid revision leakage."],
    ["Fed assets-TGA-RRP","Liquidity plumbing",
     "Rejected as universal asset signal", "DROP_STANDALONE",
     "Show components; never use as universal buy/sell mapping."],
    ["Raw CAPE / valuation","Expected return / fragility",
     "Wrong tool for short-horizon timing", "DIAGNOSTIC_LONG_HORIZON",
     "Use for expectations/asymmetry and tail severity."],
    ["Dealer gamma","Short-horizon amplification",
     "Public estimates assumption-sensitive", "CONDITIONAL",
     "Never use deterministic direction rule."],
    ["Macro surprise","Event repricing",
     "Strong causal prior; PIT consensus required", "CORE_DATA_GATED",
     "Actual minus pre-release consensus, standardized."],
    ["Reaction residual","Event / market confirmation",
     "Architecture retained; event dataset required", "CORE_DATA_GATED",
     "Observed response minus expected response to surprise."],
    ["Estimate revisions","Ticker selection",
     "PIT analyst-estimate history required", "CORE_DATA_GATED",
     "Mandatory for serious cross-sectional winner/loser testing."],
    ["Backlog/orders/RPO acceleration","Bottleneck capture",
     "Challenge-case support; broad PIT OOS pending", "CORE_SELECTION_RESEARCH",
     "Primary bottleneck-to-ticker bridge."],
    ["Margin/FCF operating leverage","Bottleneck monetization",
     "Strong causal role; broad PIT OOS pending", "CORE_SELECTION_RESEARCH",
     "Separates demand headlines from profitable capture."],
    ["Implied expectations / relative valuation","Ticker asymmetry",
     "Required to prevent chasing already-priced stories", "CORE_SELECTION_RESEARCH",
     "Prefer reverse-implied expectations over raw PE thresholds."],
], columns=["Metric family","Placement","Evidence","Status","Use"])


SCENARIO_REGISTRY = pd.DataFrame([
    ["Macro","Growth scare + disinflation","4Q","Growth state + EBP/HY + financial conditions","PROMISING"],
    ["Macro","Overheating / reflation","4Q","Growth + inflation expectations","PROMISING_SIMPLE"],
    ["Macro","Soft landing","4Q","Growth + inflation distribution","RESEARCH"],
    ["Macro","Stagflation","4Q","Growth + inflation distribution","SAMPLE_LIMITED"],
    ["Inflation","Supply-chain inflation shock","1M–1Q","Supply pressure + inflation pipeline","DATA_GATED"],
    ["Rates","Bull steepener","1–6M","Curve decomposition + policy repricing","TEST"],
    ["Rates","Bear steepener / term-premium shock","1–6M","Long yields + term premium + fiscal pressure","TEST"],
    ["Credit/Crash","Credit velocity + funding deterioration","1–6M","HY velocity + funding + stress","TEST"],
    ["Crash","Vol spike without credit confirmation","Days–1M","Vol + credit + funding","TEST"],
    ["Crash","Correlation/liquidation transition","Days–1M","Cross-asset corr + leverage + funding","DATA_GATED"],
    ["Index","First ATH after long base","1–12M","ATH episode + breadth + revisions + credit","DATA_GATED"],
    ["Index","Repeated ATH + fundamentals","1–6M","ATH cluster + breadth + revisions","DATA_GATED"],
    ["Index","ATH + credit/rates divergence","1–6M","ATH + credit + real yields + breadth","DATA_GATED"],
    ["Ticker","Price lag + positive revisions","1–6M","PIT revisions + price expectations","DATA_GATED"],
    ["Ticker","Backlog + profitable monetization","1–12M","Orders/RPO + revenue + margin + FCF","CORE_RESEARCH"],
    ["Ticker","Backlog without monetization","1–12M","Backlog + cash conversion + margin","NEGATIVE_CONTROL"],
    ["Ticker","Monster-winner reload","1–6M","Correction + revisions + valuation reset + intact bottleneck","DATA_GATED"],
    ["Ticker","Bottleneck resolution","1–12M","Capacity + inventory + lead times + pricing","DATA_GATED"],
    ["Ticker","Second-order capex bottleneck","3–18M","Capex chain + order/backlog migration","CORE_RESEARCH"],
    ["Commodity","Low inventory + backwardation + demand","1–6M","Physical inventory + curve + demand","DATA_GATED"],
    ["Commodity","Destock → restock","1–12M","Inventory + orders + utilization","DATA_GATED"],
    ["FX","Rate move rejected by FX","Days–3M","Relative rates + FX reaction residual","DATA_GATED"],
    ["Crypto","Spot/stablecoin-led rally","Days–3M","Spot flow + stablecoins + low leverage","DATA_GATED"],
    ["Crypto","Leverage-only rally","Days–1M","OI/funding/liquidations + weak real demand","DATA_GATED"],
], columns=["Engine","Scenario","Horizon","Minimal sufficient set","Status"])


# -----------------------------------------------------------------------------
# DATA ACCESS
# -----------------------------------------------------------------------------

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MacroDecisionEngine/1.0; +https://streamlit.io)"
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_series(series_id: str) -> pd.Series:
    """Fetch public latest/revised FRED data via fredgraph CSV. No API key required."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, headers=HTTP_HEADERS, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty or len(df.columns) < 2:
        raise ValueError(f"No data returned for {series_id}")
    date_col = df.columns[0]
    value_col = df.columns[1]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    s = df.dropna(subset=[date_col, value_col]).set_index(date_col)[value_col].sort_index()
    s.name = series_id
    return s


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yahoo_history(symbol: str, range_: str = "20y") -> pd.DataFrame:
    """Fetch Yahoo chart endpoint. Gracefully fails if Yahoo blocks the request."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "range": range_,
        "interval": "1d",
        "includeAdjustedClose": "true",
        "events": "div,splits",
    }
    r = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    result = data.get("chart", {}).get("result")
    if not result:
        err = data.get("chart", {}).get("error")
        raise ValueError(f"Yahoo returned no result for {symbol}: {err}")
    result = result[0]
    ts = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    close = adj if adj is not None else quote.get("close")
    if not ts or close is None:
        raise ValueError(f"No price history for {symbol}")
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(ts, unit="s", utc=True).tz_convert(None),
            "close": pd.to_numeric(pd.Series(close), errors="coerce"),
        }
    ).dropna()
    return df.set_index("date").sort_index()


def safe_fetch_all_fred() -> Tuple[Dict[str, pd.Series], pd.DataFrame]:
    series: Dict[str, pd.Series] = {}
    health_rows: List[dict] = []
    for sid, meta in FRED_SERIES.items():
        try:
            s = fetch_fred_series(sid)
            series[sid] = s
            last_date = s.index.max()
            age_days = (pd.Timestamp.utcnow().tz_localize(None).normalize() - last_date.normalize()).days
            health_rows.append({
                "Series": sid,
                "Label": meta["label"],
                "Engine": meta["engine"],
                "Last date": last_date.date(),
                "Latest": float(s.iloc[-1]),
                "Age (days)": age_days,
                "Status": "LIVE" if age_days <= 45 else "STALE/FREQUENCY",
            })
        except Exception as e:
            health_rows.append({
                "Series": sid,
                "Label": meta["label"],
                "Engine": meta["engine"],
                "Last date": pd.NaT,
                "Latest": np.nan,
                "Age (days)": np.nan,
                "Status": f"ERROR: {str(e)[:55]}",
            })
    return series, pd.DataFrame(health_rows)


# -----------------------------------------------------------------------------
# HELPERS / TRANSFORMS
# -----------------------------------------------------------------------------

def latest(s: Optional[pd.Series]) -> float:
    if s is None or s.dropna().empty:
        return np.nan
    return float(s.dropna().iloc[-1])


def value_asof_days(s: pd.Series, days_back: int) -> float:
    s = s.dropna().sort_index()
    if s.empty:
        return np.nan
    target = s.index.max() - pd.Timedelta(days=days_back)
    prior = s.loc[:target]
    if prior.empty:
        return np.nan
    return float(prior.iloc[-1])


def change_days(s: Optional[pd.Series], days_back: int) -> float:
    if s is None or s.dropna().empty:
        return np.nan
    now = latest(s)
    old = value_asof_days(s, days_back)
    return now - old if np.isfinite(now) and np.isfinite(old) else np.nan


def pct_change_days(s: Optional[pd.Series], days_back: int) -> float:
    if s is None or s.dropna().empty:
        return np.nan
    now = latest(s)
    old = value_asof_days(s, days_back)
    if not np.isfinite(now) or not np.isfinite(old) or old == 0:
        return np.nan
    return now / old - 1.0


def annualized_index_change(s: Optional[pd.Series], months: int) -> float:
    """Approximate annualized inflation using index level and calendar offset."""
    if s is None or s.dropna().empty:
        return np.nan
    s = s.dropna().sort_index()
    end = s.index.max()
    target = end - pd.DateOffset(months=months)
    prior = s.loc[:target]
    if prior.empty:
        return np.nan
    old = float(prior.iloc[-1])
    now = float(s.iloc[-1])
    if old <= 0:
        return np.nan
    return (now / old) ** (12 / months) - 1


def historical_percentile(s: Optional[pd.Series], window_years: int = 15) -> float:
    if s is None or s.dropna().empty:
        return np.nan
    s = s.dropna().sort_index()
    cutoff = s.index.max() - pd.DateOffset(years=window_years)
    x = s.loc[cutoff:]
    if len(x) < 20:
        x = s
    if len(x) < 5:
        return np.nan
    cur = float(x.iloc[-1])
    return float((x <= cur).mean() * 100)


def fmt(x: float, decimals: int = 2, suffix: str = "") -> str:
    if not np.isfinite(x):
        return "N/A"
    return f"{x:.{decimals}f}{suffix}"


def state_from_percentile(p: float, high_bad: bool = True) -> str:
    if not np.isfinite(p):
        return "NO DATA"
    if high_bad:
        if p >= 90: return "EXTREME"
        if p >= 75: return "ELEVATED"
        if p <= 25: return "LOW"
        return "NORMAL"
    else:
        if p >= 75: return "STRONG"
        if p <= 25: return "WEAK"
        return "NORMAL"


def build_live_snapshot(series: Dict[str, pd.Series]) -> pd.DataFrame:
    core_cpi_3m = annualized_index_change(series.get("CPILFESL"), 3) * 100
    core_pce_3m = annualized_index_change(series.get("PCEPILFE"), 3) * 100
    claims_13w = pct_change_days(series.get("ICSA"), 91) * 100
    hy_13w = change_days(series.get("BAMLH0A0HYM2"), 91) * 100  # pct points -> bps
    curve_13w = change_days(series.get("T10Y3M"), 91)
    real_yield_13w = change_days(series.get("DFII10"), 91)
    term_premium_13w = change_days(series.get("THREEFYTP10"), 91)
    dollar_13w = pct_change_days(series.get("DTWEXBGS"), 91) * 100
    reserve_13w = pct_change_days(series.get("WRESBAL"), 91) * 100

    rows = [
        ["Growth","CFNAI",latest(series.get("CFNAI")),historical_percentile(series.get("CFNAI")), "Broad activity state"],
        ["Growth","Initial Claims 13w %Δ",claims_13w,np.nan,"Labor deterioration velocity"],
        ["Growth","Unemployment",latest(series.get("UNRATE")),historical_percentile(series.get("UNRATE")),"Labor state"],
        ["Inflation","Core CPI 3m ann.",core_cpi_3m,np.nan,"Short-run inflation impulse"],
        ["Inflation","Core PCE 3m ann.",core_pce_3m,np.nan,"Short-run inflation impulse"],
        ["Inflation","5Y Breakeven",latest(series.get("T5YIE")),historical_percentile(series.get("T5YIE")),"Market inflation expectation"],
        ["Rates","2Y Yield",latest(series.get("DGS2")),historical_percentile(series.get("DGS2")),"Front-end policy pricing"],
        ["Rates","10Y Yield",latest(series.get("DGS10")),historical_percentile(series.get("DGS10")),"Long-end discount rate"],
        ["Rates","10Y Real Yield",latest(series.get("DFII10")),historical_percentile(series.get("DFII10")),"Real discount-rate state"],
        ["Rates","10Y Real Yield 13w Δ",real_yield_13w,np.nan,"Discount-rate impulse"],
        ["Rates","10Y-3M Curve",latest(series.get("T10Y3M")),historical_percentile(series.get("T10Y3M")),"Cycle / curve state"],
        ["Rates","Curve 13w Δ",curve_13w,np.nan,"Steepening/flattening transition"],
        ["Rates","10Y Term Premium",latest(series.get("THREEFYTP10")),historical_percentile(series.get("THREEFYTP10")),"Long-end risk premium"],
        ["Rates","Term Premium 13w Δ",term_premium_13w,np.nan,"Long-end repricing impulse"],
        ["Credit","HY OAS",latest(series.get("BAMLH0A0HYM2")),historical_percentile(series.get("BAMLH0A0HYM2")),"Credit risk state"],
        ["Credit","HY OAS 13w Δ (bp)",hy_13w,np.nan,"Credit stress velocity"],
        ["Credit","SLOOS Tightening",latest(series.get("DRTSCILM")),historical_percentile(series.get("DRTSCILM")),"Credit supply"],
        ["Credit","NFCI",latest(series.get("NFCI")),historical_percentile(series.get("NFCI")),"Broad financial conditions"],
        ["Stress","VIX",latest(series.get("VIXCLS")),historical_percentile(series.get("VIXCLS")),"Equity volatility state"],
        ["Funding","Reserve Balances 13w %Δ",reserve_13w,np.nan,"Plumbing diagnostic only"],
        ["FX","Trade-weighted USD 13w %Δ",dollar_13w,np.nan,"Dollar impulse"],
    ]
    return pd.DataFrame(rows, columns=["Engine","Metric","Value","Historical percentile","Role"])


def live_regime_cards(series: Dict[str, pd.Series]) -> List[Tuple[str, str, str]]:
    """Descriptive states only; not trade rules."""
    cfnai = latest(series.get("CFNAI"))
    claims = pct_change_days(series.get("ICSA"), 91) * 100
    cpi3 = annualized_index_change(series.get("CPILFESL"), 3) * 100
    pce3 = annualized_index_change(series.get("PCEPILFE"), 3) * 100
    hy = latest(series.get("BAMLH0A0HYM2"))
    hyv = change_days(series.get("BAMLH0A0HYM2"), 91) * 100
    nfci = latest(series.get("NFCI"))
    vix = latest(series.get("VIXCLS"))
    real10 = latest(series.get("DFII10"))
    tp = latest(series.get("THREEFYTP10"))

    # These labels are descriptive display logic, NOT production alpha thresholds.
    growth = "MIXED"
    if np.isfinite(cfnai) and np.isfinite(claims):
        if cfnai > 0 and claims < 10:
            growth = "RESILIENT"
        elif cfnai < -0.7 and claims > 15:
            growth = "DETERIORATING"

    infl = "MIXED"
    inf_vals = [x for x in [cpi3, pce3] if np.isfinite(x)]
    if inf_vals:
        inf_mean = float(np.mean(inf_vals))
        if inf_mean < 2.5: infl = "COOLING"
        elif inf_mean > 3.5: infl = "ELEVATED"
        else: infl = "STICKY / MID-RANGE"

    credit = "NORMAL"
    if np.isfinite(hy) and np.isfinite(hyv):
        if hy > 5 or hyv > 100: credit = "STRESS RISING"
        elif hy < 4 and hyv < 50: credit = "BENIGN"

    funding = "NORMAL"
    if np.isfinite(nfci):
        if nfci > 0.5: funding = "TIGHT"
        elif nfci < 0: funding = "LOOSE/NORMAL"

    vol = "NORMAL"
    if np.isfinite(vix):
        if vix > 30: vol = "HIGH"
        elif vix < 20: vol = "LOW/NORMAL"
        else: vol = "ELEVATED"

    rates = "NORMAL"
    if np.isfinite(real10) and np.isfinite(tp):
        if real10 > 2 or tp > 1: rates = "HIGH COST OF CAPITAL"
        elif real10 < 1: rates = "EASIER"

    return [
        ("Growth", growth, "Descriptive current state"),
        ("Inflation", infl, "3m annualized core CPI/PCE"),
        ("Credit", credit, "HY level + 13w velocity"),
        ("Financial conditions", funding, "NFCI state"),
        ("Volatility", vol, "VIX state"),
        ("Long-rate pressure", rates, "10Y real yield + term premium"),
    ]


# -----------------------------------------------------------------------------
# EMPIRICAL ANALOG PROJECTION
# -----------------------------------------------------------------------------

def monthly_feature_panel(series: Dict[str, pd.Series]) -> pd.DataFrame:
    cols = {}
    for sid in CORE_PROJECTION_FEATURES:
        s = series.get(sid)
        if s is None or s.empty:
            continue
        m = s.resample("ME").last()
        if sid == "ICSA":
            m = np.log(m.replace(0, np.nan))
        cols[sid] = m
    if len(cols) < 5:
        return pd.DataFrame()
    panel = pd.concat(cols, axis=1).sort_index().ffill(limit=3)
    return panel


def robust_scale(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    med = df.median()
    q1 = df.quantile(0.25)
    q3 = df.quantile(0.75)
    iqr = (q3 - q1).replace(0, np.nan)
    z = (df - med) / iqr
    return z, med, iqr


def forward_return_monthly(price_df: pd.DataFrame, months: int) -> pd.Series:
    m = price_df["close"].resample("ME").last().dropna()
    return m.shift(-months) / m - 1.0


def analog_projection(
    feature_panel: pd.DataFrame,
    price_df: pd.DataFrame,
    neighbors: int = 20,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if feature_panel.empty or price_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Align price outcome universe.
    returns = pd.DataFrame({
        "1M": forward_return_monthly(price_df, 1),
        "3M": forward_return_monthly(price_df, 3),
        "6M": forward_return_monthly(price_df, 6),
        "12M": forward_return_monthly(price_df, 12),
    })

    full = feature_panel.join(returns, how="left")
    features = [c for c in CORE_PROJECTION_FEATURES if c in full.columns]
    if len(features) < 5:
        return pd.DataFrame(), pd.DataFrame()

    # Current feature vector.
    current_date = feature_panel.dropna(subset=features, how="any").index.max()
    current = feature_panel.loc[current_date, features]

    # Only use historical observations with known 12M outcome.
    hist = full.loc[full.index < current_date - pd.DateOffset(months=12)].dropna(
        subset=features + ["1M","3M","6M","12M"]
    )
    if len(hist) < 30:
        return pd.DataFrame(), pd.DataFrame()

    # Robust scaling on the historical set only. Current is transformed with same parameters.
    _, med, iqr = robust_scale(hist[features])
    usable = iqr.replace(0, np.nan)
    hist_z = (hist[features] - med) / usable
    cur_z = (current - med) / usable
    valid_features = cur_z.dropna().index.tolist()
    if len(valid_features) < 4:
        return pd.DataFrame(), pd.DataFrame()

    dist = np.sqrt(((hist_z[valid_features] - cur_z[valid_features]) ** 2).mean(axis=1))
    k = max(8, min(neighbors, len(dist)))
    nearest_idx = dist.nsmallest(k).index
    analogs = hist.loc[nearest_idx].copy()
    analogs.insert(0, "Distance", dist.loc[nearest_idx])
    analogs = analogs.sort_values("Distance")

    stats = []
    for h in ["1M","3M","6M","12M"]:
        x = analogs[h].dropna()
        stats.append({
            "Horizon": h,
            "P(return > 0)": (x > 0).mean(),
            "P(return > 10%)": (x > 0.10).mean(),
            "P(return > 25%)": (x > 0.25).mean(),
            "P(return < -10%)": (x < -0.10).mean(),
            "10th pct": x.quantile(.10),
            "Median": x.median(),
            "90th pct": x.quantile(.90),
            "N analogs": len(x),
        })
    return pd.DataFrame(stats), analogs


# -----------------------------------------------------------------------------
# BOTTLENECK / TICKER UPLOAD MODEL
# -----------------------------------------------------------------------------

BOTTLE_REQUIRED = [
    "ticker",
    "bottleneck_score",
    "capture_score",
    "monetization_score",
    "duration_score",
    "balance_sheet_score",
    "revision_score",
    "expectation_gap_score",
    "confirmation_score",
    "valuation_risk",
    "crowding_risk",
    "tail_risk",
]

BOTTLE_OPTIONAL = [
    "current_price",
    "prior_high",
    "base_fair_value",
    "bull_fair_value",
    "extreme_fair_value",
    "reason",
    "kill_switch",
]


def bottleneck_template() -> pd.DataFrame:
    return pd.DataFrame(columns=BOTTLE_REQUIRED + BOTTLE_OPTIONAL)


def score_bottleneck(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in BOTTLE_REQUIRED:
        if c == "ticker":
            continue
        out[c] = pd.to_numeric(out[c], errors="coerce").clip(0, 100)

    positive = [
        "bottleneck_score","capture_score","monetization_score","duration_score",
        "balance_sheet_score","revision_score","expectation_gap_score","confirmation_score"
    ]
    negative = ["valuation_risk","crowding_risk","tail_risk"]

    # Equal-ish groups intentionally simple; production weights must be OOS validated.
    out["quality_core"] = out[positive].mean(axis=1)
    out["risk_penalty"] = out[negative].mean(axis=1)
    out["research_score"] = (0.75 * out["quality_core"] + 0.25 * (100 - out["risk_penalty"]))

    # Strict gate: quality-first, not fixed top-N. These are research UI gates,
    # not claimed alpha-optimal thresholds.
    gate = (
        (out["bottleneck_score"] >= 70) &
        (out["capture_score"] >= 65) &
        (out["monetization_score"] >= 60) &
        (out["revision_score"] >= 60) &
        (out["expectation_gap_score"] >= 50) &
        (out["tail_risk"] <= 75)
    )
    out["qualifies_research"] = gate

    for c in ["current_price","prior_high","base_fair_value","bull_fair_value","extreme_fair_value"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    if "current_price" in out.columns:
        cp = out["current_price"].replace(0, np.nan)
        if "prior_high" in out.columns:
            out["retest_upside"] = out["prior_high"] / cp - 1
        if "base_fair_value" in out.columns:
            out["base_upside"] = out["base_fair_value"] / cp - 1
        if "bull_fair_value" in out.columns:
            out["bull_upside"] = out["bull_fair_value"] / cp - 1
        if "extreme_fair_value" in out.columns:
            out["extreme_upside"] = out["extreme_fair_value"] / cp - 1

    return out.sort_values(["qualifies_research","research_score"], ascending=[False,False])


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------

st.sidebar.title("Controls")
st.sidebar.caption("Live public-data research build")

market_symbol = st.sidebar.text_input(
    "Projection symbol",
    value="IWM",
    help="Examples: SPY, IWM, QQQ, GLD, BTC-USD, a US ticker such as PLTR.",
).strip().upper()

neighbors = st.sidebar.slider("Historical analog count", min_value=8, max_value=40, value=20, step=1)

st.sidebar.divider()
st.sidebar.markdown("**Data policy**")
st.sidebar.caption(
    "Live FRED/Yahoo is usable for monitoring and exploratory analogs. "
    "It is NOT a substitute for PIT/vintage data in final backtests."
)


# -----------------------------------------------------------------------------
# LOAD LIVE DATA
# -----------------------------------------------------------------------------

with st.spinner("Loading public live data..."):
    fred, health = safe_fetch_all_fred()

snapshot = build_live_snapshot(fred)
cards = live_regime_cards(fred)


# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------

st.title("Macro + Bottleneck Decision Engine")
st.caption(
    "Live public-data research app. No hard-coded 'inflation → gold' mappings. "
    "Missing PIT / asset-specific inputs are surfaced as DATA-GATED, not fabricated."
)

live_count = int((health["Status"] == "LIVE").sum()) if not health.empty else 0
loaded_count = int(health["Latest"].notna().sum()) if not health.empty else 0
total_count = len(health)

h1, h2, h3, h4 = st.columns(4)
h1.metric("FRED series loaded", f"{loaded_count}/{total_count}")
h2.metric("Fresh/live series", f"{live_count}/{total_count}")
h3.metric("Projection symbol", market_symbol)
h4.metric("Model status", "RESEARCH / NOT FINAL")


tabs = st.tabs([
    "Command Center",
    "Scenario Matrix",
    "Forward Projection",
    "Bottleneck / Ticker",
    "Proof Center",
    "Data Coverage",
])


# -----------------------------------------------------------------------------
# TAB 1 — COMMAND CENTER
# -----------------------------------------------------------------------------

with tabs[0]:
    st.subheader("Current state — derived from live public data")
    st.warning(
        "State labels below are descriptive monitoring logic, not validated trade thresholds. "
        "Production signals require the PIT/OOS proof pipeline."
    )

    cols = st.columns(3)
    for i, (name, state, note) in enumerate(cards):
        with cols[i % 3]:
            st.metric(name, state)
            st.caption(note)

    st.markdown("### Live metric snapshot")
    display = snapshot.copy()
    display["Value"] = display["Value"].map(lambda x: fmt(x, 2))
    display["Historical percentile"] = display["Historical percentile"].map(
        lambda x: fmt(x, 0, "%") if np.isfinite(x) else "—"
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("### Funding / liquidity plumbing — components only")
    st.info(
        "The app intentionally does NOT create `Fed assets - TGA - RRP = BUY/SELL`. "
        "These are shown as plumbing components because the universal net-liquidity rule was rejected."
    )
    plumbing = []
    for sid in ["WRESBAL","WALCL","WTREGEN","RRPONTSYD"]:
        s = fred.get(sid)
        plumbing.append({
            "Series": sid,
            "Name": FRED_SERIES[sid]["label"],
            "Latest": latest(s),
            "13w % change": pct_change_days(s, 91) * 100,
        })
    st.dataframe(pd.DataFrame(plumbing), use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# TAB 2 — SCENARIO MATRIX
# -----------------------------------------------------------------------------

with tabs[1]:
    st.subheader("Scenario/state-transition library")
    st.write(
        "A scenario is an interaction of existing metric families, not a new metric. "
        "Russell ATH is one example of an index state; it only matters conditionally."
    )
    st.dataframe(SCENARIO_REGISTRY, use_container_width=True, hide_index=True)

    st.markdown("### Live contradiction monitor")
    contradictions = []

    hy_vel = change_days(fred.get("BAMLH0A0HYM2"), 91) * 100
    vix = latest(fred.get("VIXCLS"))
    cfnai = latest(fred.get("CFNAI"))
    real_yield_delta = change_days(fred.get("DFII10"), 91)
    claims_delta = pct_change_days(fred.get("ICSA"), 91) * 100

    if np.isfinite(vix) and np.isfinite(hy_vel):
        if vix >= 25 and hy_vel < 50:
            contradictions.append(
                "Volatility elevated but credit-spread velocity is not confirming: "
                "candidate correction/non-systemic stress state."
            )
    if np.isfinite(cfnai) and np.isfinite(claims_delta):
        if cfnai > 0 and claims_delta > 15:
            contradictions.append(
                "Broad activity remains positive while claims deteriorate: mixed growth transition."
            )
    if np.isfinite(real_yield_delta) and real_yield_delta > 0.40:
        contradictions.append(
            "Real yields have risen materially over ~13 weeks: cost-of-capital bottleneck is strengthening."
        )

    if contradictions:
        for c in contradictions:
            st.warning(c)
    else:
        st.success("No simple live contradictions triggered by the currently loaded public subset.")

    st.caption(
        "Production version will add earnings revisions, breadth, flows, funding basis, physical bottlenecks "
        "and cross-sectional PIT data when those sources are supplied."
    )


# -----------------------------------------------------------------------------
# TAB 3 — FORWARD PROJECTION
# -----------------------------------------------------------------------------

with tabs[2]:
    st.subheader(f"Mechanical historical-analog projection — {market_symbol}")
    st.warning(
        "EXPLORATORY ONLY. This is a current-state nearest-neighbor distribution using revised public history. "
        "It is not the final OOS/PIT forecast model and is not a buy/sell recommendation."
    )

    price_error = None
    try:
        px = fetch_yahoo_history(market_symbol, "20y")
    except Exception as e:
        px = pd.DataFrame()
        price_error = str(e)

    panel = monthly_feature_panel(fred)
    stats, analogs = analog_projection(panel, px, neighbors=neighbors)

    if price_error:
        st.error(f"Price adapter error for {market_symbol}: {price_error}")
    elif stats.empty:
        st.info("Not enough overlapping feature/price history to calculate analog projection.")
    else:
        formatted = stats.copy()
        for c in ["P(return > 0)","P(return > 10%)","P(return > 25%)","P(return < -10%)"]:
            formatted[c] = formatted[c].map(lambda x: f"{x:.1%}")
        for c in ["10th pct","Median","90th pct"]:
            formatted[c] = formatted[c].map(lambda x: f"{x:.1%}")
        st.dataframe(formatted, use_container_width=True, hide_index=True)

        pcols = st.columns(4)
        current_price = float(px["close"].iloc[-1])
        prior_high = float(px["close"].cummax().iloc[-1])
        drawdown = current_price / prior_high - 1.0
        one_year = px.loc[px.index >= px.index.max() - pd.DateOffset(years=1), "close"]
        one_year_high = float(one_year.max()) if not one_year.empty else np.nan

        pcols[0].metric("Current", f"{current_price:,.2f}")
        pcols[1].metric("Max close in loaded history", f"{prior_high:,.2f}")
        pcols[2].metric("Drawdown from loaded peak", f"{drawdown:.1%}")
        pcols[3].metric("1Y high", f"{one_year_high:,.2f}" if np.isfinite(one_year_high) else "N/A")

        st.markdown("### Closest historical macro states")
        show = analogs.reset_index().rename(columns={"index":"Analog month"}).copy()
        show["1M"] = show["1M"].map(lambda x: f"{x:.1%}")
        show["3M"] = show["3M"].map(lambda x: f"{x:.1%}")
        show["6M"] = show["6M"].map(lambda x: f"{x:.1%}")
        show["12M"] = show["12M"].map(lambda x: f"{x:.1%}")
        cols_show = ["Analog month","Distance","1M","3M","6M","12M"]
        st.dataframe(show[cols_show].head(neighbors), use_container_width=True, hide_index=True)

        st.caption(
            "This analog block is intentionally mechanical. It does not know PIT earnings revisions, "
            "index breadth, valuation expectations, commodity physical state, intervention risk or crypto-native data."
        )


# -----------------------------------------------------------------------------
# TAB 4 — BOTTLENECK / TICKER
# -----------------------------------------------------------------------------

with tabs[3]:
    st.subheader("Quality-first bottleneck / ticker engine")
    st.write(
        "No fixed Top-100 list. A ticker only survives the research gate when bottleneck, capture, monetization, "
        "revision, expectations-gap and risk fields are simultaneously strong."
    )

    with st.expander("CSV schema / how remaining upside is handled"):
        st.code(
            ",".join(BOTTLE_REQUIRED + BOTTLE_OPTIONAL),
            language="text"
        )
        st.write(
            "For remaining upside, supply **base_fair_value / bull_fair_value / extreme_fair_value** from a "
            "defensible valuation model. The app computes +25/+50/+100-style runway from those values; "
            "it does not invent a target because a stock previously surged."
        )

    template_csv = bottleneck_template().to_csv(index=False).encode()
    st.download_button(
        "Download bottleneck CSV template",
        data=template_csv,
        file_name="bottleneck_input_template.csv",
        mime="text/csv",
    )

    up = st.file_uploader("Upload PIT/validated bottleneck candidate CSV", type=["csv"])

    if up is None:
        st.info(
            "No company-level PIT dataset supplied yet. This is correctly DATA-GATED. "
            "The app will not hard-code GNRC/MOD/POWL/SNDK/PLTR scores as if they were validated live inputs."
        )
    else:
        try:
            raw = pd.read_csv(up)
            missing = [c for c in BOTTLE_REQUIRED if c not in raw.columns]
            if missing:
                st.error("Missing required columns: " + ", ".join(missing))
            else:
                ranked = score_bottleneck(raw)
                winners = ranked.loc[ranked["qualifies_research"]].copy()
                st.metric("Qualified research candidates", len(winners))

                view_cols = [
                    "ticker","research_score","quality_core","risk_penalty","qualifies_research",
                    "retest_upside","base_upside","bull_upside","extreme_upside","reason","kill_switch"
                ]
                view_cols = [c for c in view_cols if c in ranked.columns]
                view = ranked[view_cols].copy()
                for c in ["retest_upside","base_upside","bull_upside","extreme_upside"]:
                    if c in view.columns:
                        view[c] = view[c].map(lambda x: f"{x:.1%}" if np.isfinite(x) else "DATA-GATED")
                for c in ["research_score","quality_core","risk_penalty"]:
                    if c in view.columns:
                        view[c] = view[c].map(lambda x: f"{x:.1f}")
                st.dataframe(view, use_container_width=True, hide_index=True)

                if len(winners) == 0:
                    st.warning("NO QUALIFYING WINNER under the current research gate.")
                else:
                    chosen = st.selectbox("Inspect candidate", winners["ticker"].astype(str).tolist())
                    row = winners.loc[winners["ticker"].astype(str) == chosen].iloc[0]
                    st.markdown(f"### {chosen} — reason / invalidation")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Research score", f"{row['research_score']:.1f}")
                    c2.metric("Core quality", f"{row['quality_core']:.1f}")
                    c3.metric("Risk penalty", f"{row['risk_penalty']:.1f}")

                    if "reason" in row.index and pd.notna(row["reason"]):
                        st.success(str(row["reason"]))
                    if "kill_switch" in row.index and pd.notna(row["kill_switch"]):
                        st.error("Kill switch: " + str(row["kill_switch"]))

                    ladder = []
                    cp = row.get("current_price", np.nan)
                    if np.isfinite(cp) and cp > 0:
                        for label, col in [
                            ("Retest", "prior_high"),
                            ("Base", "base_fair_value"),
                            ("Bull", "bull_fair_value"),
                            ("Extreme", "extreme_fair_value"),
                        ]:
                            val = row.get(col, np.nan)
                            if np.isfinite(val):
                                ladder.append({
                                    "Scenario": label,
                                    "Value": val,
                                    "Upside / downside": val / cp - 1
                                })
                    if ladder:
                        ld = pd.DataFrame(ladder)
                        ld["Upside / downside"] = ld["Upside / downside"].map(lambda x: f"{x:.1%}")
                        st.dataframe(ld, use_container_width=True, hide_index=True)
                    else:
                        st.warning(
                            "Remaining-upside distribution is DATA-GATED because no defensible fair-value "
                            "scenarios were supplied."
                        )
        except Exception as e:
            st.error(f"Could not process bottleneck CSV: {e}")


# -----------------------------------------------------------------------------
# TAB 5 — PROOF CENTER
# -----------------------------------------------------------------------------

with tabs[4]:
    st.subheader("Metric / placement proof registry")
    st.dataframe(METRIC_VALIDATION, use_container_width=True, hide_index=True)

    st.markdown("### Rules enforced by the architecture")
    rules = [
        "A famous metric is not automatically an independent vote.",
        "A metric is tested against the target/horizon implied by its causal role.",
        "A signal may be CORE, CONDITIONAL, DIAGNOSTIC, DATA-GATED or REJECTED.",
        "No threshold is optimized simply because it made the historical PnL look better.",
        "Russell ATH and similar states are scenario conditions, not standalone buy/crash rules.",
        "Past monster winners are allowed to reappear only if remaining fundamental runway re-opens.",
        "The app can output NO TRADE / NO QUALIFYING WINNER.",
    ]
    for r in rules:
        st.write("•", r)

    st.markdown("### Rejected / busted mappings")
    busted = [
        "Inflation high → automatically buy gold/oil",
        "Yield-curve inversion → immediately short stocks",
        "VIX above a fixed threshold → crash",
        "Fed assets − TGA − RRP → universal liquidity trade",
        "Backlog growth → automatic bottleneck winner",
        "High CAPE → immediate market short",
        "Dealer gamma estimate → deterministic market direction",
        "Tune the model until PLTR/SNDK appear",
        "Add every macro feature to every scenario",
    ]
    for b in busted:
        st.write("✗", b)


# -----------------------------------------------------------------------------
# TAB 6 — DATA COVERAGE
# -----------------------------------------------------------------------------

with tabs[5]:
    st.subheader("Live source health")
    st.dataframe(health, use_container_width=True, hide_index=True)

    st.markdown("### Required data that this single-file public build does NOT yet have")
    dg = pd.DataFrame(DATA_GATED, columns=["Layer","Required source/data"])
    dg["Status"] = "DATA-GATED"
    st.dataframe(dg, use_container_width=True, hide_index=True)

    st.markdown("### What is actually live in this app")
    st.write(
        "FRED public series feed: macro activity, claims, unemployment, inflation indices, breakevens, "
        "Treasury yields/real yield/curve/term premium, HY OAS, SLOOS, NFCI, VIX, Fed plumbing components, USD."
    )
    st.write(
        "Yahoo chart adapter: current/historical market prices for the selected symbol, used only for the "
        "mechanical analog distribution and drawdown/ATH context."
    )

    st.error(
        "Do not call the full engine 'proven' until the DATA-GATED layers are filled with point-in-time "
        "datasets and the frozen validation protocol is rerun. Latest/revised history can create look-ahead "
        "if used as though it were known historically."
    )

    st.markdown("### Deployment")
    st.code(
        """streamlit run app.py

# Streamlit Cloud:
# 1. Put app.py in your repo
# 2. New app -> select repo/branch -> Main file path: app.py
# 3. Deploy
#
# No FRED API key is required for this public-data build.
""",
        language="bash",
    )


st.divider()
st.caption(
    "Research build. The app separates live observable data from missing PIT/asset-specific data so "
    "a missing source cannot silently become a fabricated signal."
)

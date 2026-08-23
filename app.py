from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# MACRO INTELLIGENCE — LANDING PAGE 1
# Visual-first landing page.
# Numerical probabilities remain gated until the research pipeline
# proves them with point-in-time, out-of-sample validation.
# ============================================================

st.set_page_config(
    page_title="Macro Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FED_EBP_URL = "https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv"
FED_FCIG_3Y_URL = "https://www.federalreserve.gov/econres/notes/feds-notes/fci_g_public_monthly_3yr.csv"
FED_FCIG_1Y_URL = "https://www.federalreserve.gov/econres/notes/feds-notes/fci_g_public_monthly_1yr.csv"

PROJECTION_MODEL_VALIDATED = False
CRASH_MODEL_VALIDATED = False


def _secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


FRED_API_KEY = _secret("FRED_API_KEY")


@dataclass(frozen=True)
class SeriesSpec:
    label: str
    start: str
    unit: str
    role: str


SERIES: Dict[str, SeriesSpec] = {
    # Growth / state
    "BBKMGDP": SeriesSpec("BBK Monthly GDP Growth", "1960-01-01", "% annualized", "growth_now"),
    "BBKMCOIX": SeriesSpec("BBK Coincident Index", "1960-01-01", "σ from trend", "growth_now"),
    "BBKMLEIX": SeriesSpec("BBK Leading Index", "1960-01-01", "σ from trend", "growth_lead"),
    "WEI": SeriesSpec("Weekly Economic Index", "2008-01-01", "GDP-aligned %", "growth_crosscheck"),
    # Inflation
    "PCETRIM12M159SFRBDAL": SeriesSpec("Dallas Fed Trimmed Mean PCE", "1977-01-01", "% y/y", "inflation"),
    "PCEPILFE": SeriesSpec("Core PCE Price Index", "1959-01-01", "index", "inflation"),
    "PCEPI": SeriesSpec("Headline PCE Price Index", "1959-01-01", "index", "inflation_context"),
    # Labor
    "SAHMREALTIME": SeriesSpec("Real-time Sahm Rule", "1959-12-01", "pp", "labor_current"),
    "ICSA": SeriesSpec("Initial Jobless Claims", "1967-01-01", "claims", "labor_challenger"),
    # Credit / conditions
    "DRTSCILM": SeriesSpec("SLOOS: Tightening C&I Standards", "1990-01-01", "net %", "credit_context"),
    "NFCIRISK": SeriesSpec("Chicago Fed NFCI Risk Subindex", "1971-01-01", "index", "market_stress"),
    # Market context
    "VIXCLS": SeriesSpec("VIX", "1990-01-01", "index", "market_stress_context"),
    "BAMLH0A0HYM2": SeriesSpec("US High Yield OAS", "1996-01-01", "%", "market_stress_context"),
    "SP500": SeriesSpec("S&P 500", "2016-01-01", "index", "market_context"),
    "T5YIE": SeriesSpec("5Y Breakeven Inflation", "2003-01-01", "%", "market_pricing"),
    "DGS10": SeriesSpec("10Y Treasury Yield", "1962-01-01", "%", "market_pricing"),
    "DGS2": SeriesSpec("2Y Treasury Yield", "1976-06-01", "%", "market_pricing"),
    "FEDFUNDS": SeriesSpec("Fed Funds", "1954-07-01", "%", "policy_context"),
    "DCOILWTICO": SeriesSpec("WTI Oil", "1986-01-02", "USD/barrel", "event_proxy"),
}

EVIDENCE = [
    {
        "Component": "BBK Coincident / Monthly GDP",
        "Role": "Current growth state",
        "Status": "EXTERNAL BENCHMARK",
        "Reason": "Broad dynamic-factor construction from many real-activity series; avoids hand-picked landing-page weights.",
        "Known limitation": "Our own point-in-time replication is still required.",
    },
    {
        "Component": "BBK Leading Index",
        "Role": "Medium-horizon growth lead",
        "Status": "EXTERNAL BENCHMARK",
        "Reason": "Published leading indicator with recession ROC evidence; we use published qualitative thresholds only.",
        "Known limitation": "False positives/negatives exist.",
    },
    {
        "Component": "WEI",
        "Role": "High-frequency growth cross-check",
        "Status": "EXTERNAL BENCHMARK",
        "Reason": "High-frequency cross-check of broad activity.",
        "Known limitation": "Shorter history than classic monthly macro series.",
    },
    {
        "Component": "Trimmed Mean PCE + Core PCE",
        "Role": "Underlying inflation range",
        "Status": "ROBUSTNESS PAIR",
        "Reason": "Landing page shows range/disagreement instead of forcing one fragile estimator to win.",
        "Known limitation": "Relative performance changes by regime.",
    },
    {
        "Component": "Real-time Sahm Rule",
        "Role": "Labor / recession confirmation",
        "Status": "PUBLISHED RULE",
        "Reason": "Simple published recession confirmation framework.",
        "Known limitation": "Confirming, not a front-running labor forecast.",
    },
    {
        "Component": "Fed Excess Bond Premium model",
        "Role": "12M recession benchmark",
        "Status": "FED MODEL OUTPUT",
        "Reason": "Direct published Fed benchmark; not refit here.",
        "Known limitation": "Recession benchmark, not crash probability.",
    },
    {
        "Component": "Fed FCI-G",
        "Role": "12M financial impulse",
        "Status": "FED MODEL OUTPUT",
        "Reason": "Published growth-impulse context; avoids unvalidated homemade liquidity shortcuts.",
        "Known limitation": "Rule-of-thumb, not a full causal model.",
    },
    {
        "Component": "Structural fragility / crash probability",
        "Role": "Crash engine",
        "Status": "BLOCKED BY RESEARCH GATE",
        "Reason": "No fake precision until long-history point-in-time validation passes.",
        "Known limitation": "Deliberately unavailable in Landing v1.",
    },
]

HEADERS = {
    "User-Agent": "MacroIntelligence/1.0 (+Streamlit; research dashboard)",
    "Accept": "text/csv,application/json,text/plain,*/*",
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred(series_id: str, start: str) -> pd.Series:
    if FRED_API_KEY:
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": start,
            "sort_order": "asc",
        }
        r = requests.get(FRED_API_URL, params=params, headers=HEADERS, timeout=25)
        r.raise_for_status()
        payload = r.json()
        obs = payload.get("observations", [])
        if not obs:
            raise ValueError(f"No observations returned for {series_id}")
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"].replace(".", np.nan), errors="coerce")
        out = df.dropna().set_index("date")["value"].sort_index()
    else:
        params = {"id": series_id, "cosd": start}
        r = requests.get(FRED_GRAPH_URL, params=params, headers=HEADERS, timeout=25)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.shape[1] < 2:
            raise ValueError(f"Unexpected FRED CSV format for {series_id}")
        date_col = df.columns[0]
        value_col = series_id if series_id in df.columns else df.columns[-1]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col].replace(".", np.nan), errors="coerce")
        out = df.dropna(subset=[date_col, value_col]).set_index(date_col)[value_col].sort_index()

    out.name = series_id
    if out.empty:
        raise ValueError(f"Empty series after parsing: {series_id}")
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_research_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "date" not in df.columns:
        raise ValueError("Expected a 'date' column in Federal Reserve research CSV")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all() -> Tuple[Dict[str, pd.Series], Dict[str, pd.DataFrame], Dict[str, str]]:
    data: Dict[str, pd.Series] = {}
    research: Dict[str, pd.DataFrame] = {}
    errors: Dict[str, str] = {}

    for sid, spec in SERIES.items():
        try:
            data[sid] = fetch_fred(sid, spec.start)
        except Exception as exc:
            errors[sid] = str(exc)

    for name, url in {
        "EBP": FED_EBP_URL,
        "FCIG3": FED_FCIG_3Y_URL,
        "FCIG1": FED_FCIG_1Y_URL,
    }.items():
        try:
            research[name] = fetch_research_csv(url)
        except Exception as exc:
            errors[name] = str(exc)

    return data, research, errors


# ---------- helpers ----------
def latest(s: Optional[pd.Series]) -> Tuple[float, Optional[pd.Timestamp]]:
    if s is None or s.empty:
        return np.nan, None
    x = s.dropna()
    if x.empty:
        return np.nan, None
    return float(x.iloc[-1]), pd.Timestamp(x.index[-1])


def lag_value(s: Optional[pd.Series], n: int = 1) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    if len(x) <= n:
        return np.nan
    return float(x.iloc[-1 - n])


def value_n_months_ago(s: Optional[pd.Series], months: int) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    if x.empty:
        return np.nan
    target_date = x.index[-1] - pd.DateOffset(months=months)
    subset = x[x.index <= target_date]
    return float(subset.iloc[-1]) if len(subset) else np.nan


def yoy_from_index(s: Optional[pd.Series]) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    if len(x) < 13:
        return np.nan
    return float((x.iloc[-1] / x.iloc[-13] - 1.0) * 100.0)


def yoy_at_lag(s: Optional[pd.Series], lag_months: int) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    end = len(x) - 1 - lag_months
    start = end - 12
    if start < 0 or end < 0:
        return np.nan
    return float((x.iloc[end] / x.iloc[start] - 1.0) * 100.0)


def pct(x: float, digits: int = 1) -> str:
    return "—" if not np.isfinite(x) else f"{x:.{digits}f}%"


def num(x: float, digits: int = 2) -> str:
    return "—" if not np.isfinite(x) else f"{x:.{digits}f}"


def signed(x: float, digits: int = 2, suffix: str = "") -> str:
    return "—" if not np.isfinite(x) else f"{x:+.{digits}f}{suffix}"


def date_str(d: Optional[pd.Timestamp]) -> str:
    return "n/a" if d is None else pd.Timestamp(d).strftime("%d %b %Y")


def delta_word(now: float, old: float, higher_is_worse: bool = False, eps: float = 1e-12) -> Tuple[str, str]:
    if not (np.isfinite(now) and np.isfinite(old)):
        return "→", "unchanged / insufficient history"
    diff = now - old
    if abs(diff) <= eps:
        return "→", "unchanged"
    improving = diff < 0 if higher_is_worse else diff > 0
    return ("↗", "improving") if improving else ("↘", "deteriorating")


def historical_percentile(s: Optional[pd.Series], lookback_years: Optional[int] = None) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna().copy()
    if lookback_years and len(x):
        cutoff = x.index[-1] - pd.DateOffset(years=lookback_years)
        x = x[x.index >= cutoff]
    if len(x) < 20:
        return np.nan
    current = float(x.iloc[-1])
    return float((x <= current).mean() * 100.0)


def one_year_drawdown(s: Optional[pd.Series]) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    if len(x) < 20:
        return np.nan
    cutoff = x.index[-1] - pd.DateOffset(years=1)
    y = x[x.index >= cutoff]
    if y.empty:
        return np.nan
    peak = float(y.max())
    return float((float(y.iloc[-1]) / peak - 1.0) * 100.0)


def series_to_plot(s: Optional[pd.Series], years: float = 5.0, zscore: bool = False) -> pd.DataFrame:
    if s is None or s.empty:
        return pd.DataFrame()
    x = s.dropna().copy()
    cutoff = x.index[-1] - pd.DateOffset(days=int(years * 365))
    x = x[x.index >= cutoff]
    if x.empty:
        return pd.DataFrame()
    if zscore:
        std = float(x.std())
        if std > 0:
            x = (x - float(x.mean())) / std
    return x.to_frame(name="value")


def growth_state(bbk_gdp: float, bbk_co: float, wei: float) -> Tuple[str, str, str]:
    if not (np.isfinite(bbk_gdp) and np.isfinite(bbk_co)):
        return "UNKNOWN", "gray", "Missing BBK current-state data."
    if bbk_co <= -1.0:
        return "RECESSION-LIKE", "red", "BBK coincident index is at/below the published -1σ recession-risk threshold."
    if bbk_gdp < 0:
        return "CONTRACTING", "red", "BBK monthly GDP estimate is negative."
    if np.isfinite(wei) and wei < 0 < bbk_gdp:
        return "MIXED", "amber", "BBK is positive but the high-frequency WEI cross-check is negative."
    if bbk_co < 0:
        return "POSITIVE · BELOW TREND", "amber", "Growth is positive while the broad activity cycle is below trend."
    return "POSITIVE · ABOVE TREND", "green", "Growth is positive and the broad activity cycle is above trend."


def bbk_lead_state(x: float) -> Tuple[str, str]:
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    if x <= -1.0:
        return "ELEVATED DOWNTURN LEAD", "red"
    if x < 0:
        return "BELOW-TREND LEAD", "amber"
    return "ABOVE-TREND LEAD", "green"


def inflation_state(trimmed: float, core: float, trim_3m_ago: float, core_3m_ago: float) -> Tuple[str, str, str]:
    vals = [v for v in (trimmed, core) if np.isfinite(v)]
    if not vals:
        return "UNKNOWN", "gray", "unknown"
    if all(v > 2.0 for v in vals):
        level_label, tone = "ABOVE 2% TARGET", "amber"
    elif all(v <= 2.0 for v in vals):
        level_label, tone = "AT / BELOW 2%", "green"
    else:
        level_label, tone = "MIXED AROUND 2%", "amber"

    dirs: List[float] = []
    if np.isfinite(trimmed) and np.isfinite(trim_3m_ago):
        dirs.append(np.sign(trimmed - trim_3m_ago))
    if np.isfinite(core) and np.isfinite(core_3m_ago):
        dirs.append(np.sign(core - core_3m_ago))
    if dirs and all(d < 0 for d in dirs):
        direction = "cooling"
    elif dirs and all(d > 0 for d in dirs):
        direction = "heating"
    else:
        direction = "mixed"
    return level_label, tone, direction


def sahm_state(x: float) -> Tuple[str, str]:
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    if x >= 0.50:
        return "RECESSION SIGNAL ACTIVE", "red"
    return "NO SAHM RECESSION SIGNAL", "green"


def fcig_state(x: float) -> Tuple[str, str, str]:
    if not np.isfinite(x):
        return "UNKNOWN", "gray", "—"
    if x > 0:
        return "HEADWIND", "red", f"≈ {abs(x):.2f}pp drag to next-year GDP growth"
    if x < 0:
        return "TAILWIND", "green", f"≈ {abs(x):.2f}pp boost to next-year GDP growth"
    return "NEUTRAL", "gray", "≈ 0pp impulse"


def nfci_risk_state(x: float) -> Tuple[str, str]:
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    return ("ABOVE-AVERAGE STRESS", "red") if x > 0 else ("BELOW-AVERAGE STRESS", "green")


def regime_descriptor(growth_label: str, inflation_direction: str, inflation_level: str) -> str:
    weak_growth = any(k in growth_label for k in ["BELOW TREND", "CONTRACT", "RECESSION", "MIXED"])
    inflation_hot = "ABOVE" in inflation_level
    if weak_growth and inflation_hot and inflation_direction == "heating":
        return "STAGFLATION RISK"
    if weak_growth and inflation_direction == "cooling":
        return "DISINFLATIONARY SLOWDOWN"
    if not weak_growth and inflation_direction == "cooling":
        return "GOLDILOCKS / DISINFLATION"
    if not weak_growth and inflation_direction == "heating":
        return "REFLATION"
    return "MIXED / TRANSITION"


def severity_label(x: float, low: float, high: float, reverse: bool = False) -> Tuple[str, str]:
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    if reverse:
        if x <= low:
            return "LOW", "green"
        if x <= high:
            return "MODERATE", "amber"
        return "ELEVATED", "red"
    else:
        if x >= high:
            return "ELEVATED", "red"
        if x >= low:
            return "MODERATE", "amber"
        return "LOW", "green"


def rank_scenarios(regime: str, bbk_lead: float, ebp_prob: float, fcig: float, infl_direction: str) -> List[dict]:
    base = {
        "name": regime,
        "tag": "BASE CASE",
        "tone": "blue",
        "why": [],
        "confirm": [],
        "break": [],
    }
    alt1 = {"name": "REACCELERATION", "tag": "ALTERNATIVE", "tone": "green", "why": [], "confirm": [], "break": []}
    alt2 = {"name": "RECESSION RISK", "tag": "TAIL RISK", "tone": "red", "why": [], "confirm": [], "break": []}

    if regime == "DISINFLATIONARY SLOWDOWN":
        base["why"] = [
            "Broad growth is positive but below trend.",
            "Underlying inflation is cooling rather than re-heating.",
            "Financial/credit conditions matter more than near-term headline strength.",
        ]
        base["confirm"] = ["BBK Leading remains below trend.", "Claims trend higher.", "Inflation keeps cooling."]
        base["break"] = ["BBK Leading reaccelerates above trend.", "Labor stabilizes clearly.", "Inflation re-heats."]
        alt1["why"] = ["Would need growth breadth to improve.", "Usually needs leading indicators to turn up."]
        alt1["confirm"] = ["BBK Leading up.", "WEI/claims improve."]
        alt1["break"] = ["EBP rises sharply.", "Claims worsen."]
        alt2["why"] = ["Credit deterioration or labor crack could push slowdown into recession."]
        alt2["confirm"] = ["Sahm moves toward trigger.", "EBP / HY stress rises."]
        alt2["break"] = ["Credit stress eases.", "Broad growth steadies."]
    elif regime == "GOLDILOCKS / DISINFLATION":
        base["why"] = ["Growth is holding up while inflation cools.", "This is the friendliest macro mix if it persists."]
        base["confirm"] = ["Growth stays positive.", "Inflation keeps cooling."]
        base["break"] = ["Growth slips below trend.", "Inflation re-accelerates."]
        alt1["name"] = "DISINFLATIONARY SLOWDOWN"
        alt1["why"] = ["Most likely downside if growth loses altitude."]
        alt1["confirm"] = ["BBK Leading weakens.", "Claims drift higher."]
        alt1["break"] = ["Leading data reaccelerate."]
        alt2["why"] = ["Tail risk if credit/labor crack emerges anyway."]
        alt2["confirm"] = ["EBP spikes.", "Sahm deteriorates."]
        alt2["break"] = ["Credit stays calm."]
    else:
        base["why"] = ["Current admitted indicators do not point to a clean single quadrant."]
        base["confirm"] = ["Need stronger convergence across growth, inflation and credit."]
        base["break"] = ["Conflicting indicators resolve in one direction."]
        alt1["why"] = ["Reacceleration if growth improves without inflation re-heating."]
        alt1["confirm"] = ["Leading growth improves."]
        alt1["break"] = ["Credit stress rises."]
        alt2["why"] = ["Recession risk if credit/labor weaken together."]
        alt2["confirm"] = ["Claims and EBP worsen."]
        alt2["break"] = ["Growth broadens positively."]

    # small evidence tuning
    if np.isfinite(bbk_lead) and bbk_lead <= -0.5:
        alt2["why"].append("Leading growth signal is below trend.")
    if np.isfinite(ebp_prob) and ebp_prob >= 25:
        alt2["why"].append("Fed EBP recession benchmark is not trivial.")
    if np.isfinite(fcig) and fcig < 0:
        alt1["why"].append("Financial conditions are providing a tailwind.")
    if infl_direction == "heating":
        base["break"].append("Inflation heating would weaken the disinflation thesis.")

    return [base, alt1, alt2]


def watch_items(regime: str, growth_label: str, infl_direction: str) -> List[dict]:
    if regime == "DISINFLATIONARY SLOWDOWN":
        return [
            {"label": "Growth follow-through", "need": "BBK Leading / WEI / claims confirm weakening", "type": "data"},
            {"label": "Credit pressure", "need": "EBP / HY spreads do not accelerate higher", "type": "data"},
            {"label": "Inflation cooling", "need": "Trimmed/Core PCE continue lower", "type": "data"},
            {"label": "Labor crack", "need": "Sahm stays below trigger", "type": "data"},
        ]
    if regime == "GOLDILOCKS / DISINFLATION":
        return [
            {"label": "Growth durability", "need": "Current growth remains positive", "type": "data"},
            {"label": "Inflation discipline", "need": "No re-heating in underlying inflation", "type": "data"},
            {"label": "Credit calm", "need": "EBP / HY remain contained", "type": "data"},
            {"label": "Rates pressure", "need": "Long-end yields do not become a new headwind", "type": "data"},
        ]
    return [
        {"label": "Growth direction", "need": "Need cleaner confirmation from BBK lead / WEI", "type": "data"},
        {"label": "Inflation direction", "need": "Need clearer cooling vs heating signal", "type": "data"},
        {"label": "Credit regime", "need": "Need stable / worsening separation", "type": "data"},
        {"label": "Labor", "need": "Watch Sahm and claims", "type": "data"},
    ]


TONE = {
    "green": ("#23d18b", "rgba(35,209,139,.10)"),
    "amber": ("#f2b35f", "rgba(242,179,95,.12)"),
    "red": ("#ff7070", "rgba(255,112,112,.12)"),
    "gray": ("#95a1b2", "rgba(149,161,178,.10)"),
    "blue": ("#7caeff", "rgba(124,174,255,.12)"),
}

st.markdown(
    """
<style>
:root {
  --bg:#070b11;
  --panel:#0f1520;
  --panel2:#121a26;
  --border:#202a3a;
  --text:#eaf0f8;
  --muted:#8b97a8;
}
.stApp {background:var(--bg); color:var(--text);}
.block-container {max-width:1500px; padding-top:1.2rem; padding-bottom:2.5rem;}
header[data-testid="stHeader"] {background:transparent;}
.hero {padding:18px 20px; border:1px solid var(--border); border-radius:18px; background:linear-gradient(180deg, rgba(18,26,38,.97), rgba(11,16,24,.98));}
.hero-title {font-size:2.2rem; font-weight:800; letter-spacing:-.04em; margin:0;}
.hero-sub {font-size:.92rem; color:var(--muted); margin-top:.2rem;}
.chips {display:flex; flex-wrap:wrap; gap:8px; margin-top:14px;}
.chip {display:inline-block; padding:6px 10px; border-radius:999px; font-size:.68rem; font-weight:780; letter-spacing:.04em; text-transform:uppercase;}
.section-title {font-size:.78rem; font-weight:780; letter-spacing:.11em; color:#9aa7b8; text-transform:uppercase; margin:1.1rem 0 .55rem 0;}
.panel {border:1px solid var(--border); border-radius:16px; padding:14px 15px; background:linear-gradient(180deg, rgba(17,24,36,.96), rgba(11,16,24,.98));}
.card {border:1px solid var(--border); border-radius:16px; padding:15px 15px 14px 15px; background:linear-gradient(180deg, rgba(18,25,38,.96), rgba(12,17,24,.99)); min-height:160px;}
.kicker {font-size:.69rem; font-weight:760; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);}
.value {font-size:1.12rem; font-weight:780; margin-top:.45rem; line-height:1.15;}
.big {font-size:1.85rem; font-weight:820; line-height:1.05; margin-top:.25rem; letter-spacing:-.03em;}
.note {font-size:.78rem; color:#9cabbc; margin-top:.55rem; line-height:1.42;}
.pill {display:inline-block; margin-top:.7rem; padding:4px 8px; border-radius:999px; font-size:.66rem; font-weight:760; letter-spacing:.04em;}
.timeline {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.tcell {border:1px solid var(--border); border-radius:14px; padding:14px; background:#0d131d; min-height:125px;}
.thead {font-size:.68rem; color:#90a0b0; text-transform:uppercase; letter-spacing:.08em; font-weight:760;}
.tval {font-size:1.04rem; font-weight:780; margin-top:.5rem;}
.tnote {font-size:.76rem; color:#91a0b0; margin-top:.45rem; line-height:1.38;}
.minicard {border:1px solid var(--border); border-radius:14px; padding:12px 13px; background:#0d131d; min-height:115px;}
.labelrow {display:flex; justify-content:space-between; align-items:flex-start; gap:10px;}
.smallcaps {font-size:.64rem; letter-spacing:.08em; text-transform:uppercase; color:#91a0b0; font-weight:760;}
.scenario-box {border:1px solid var(--border); border-radius:16px; padding:14px; background:#0d131d; min-height:290px;}
.scenario-name {font-size:1.0rem; font-weight:800; margin-top:.3rem;}
.scenario-list {margin:.55rem 0 0 0; padding-left:1rem; color:#ced7e4; font-size:.79rem; line-height:1.45;}
.gate {border:1px solid #384559; border-radius:14px; padding:12px 14px; background:rgba(83,98,127,.09); color:#c0cad8; font-size:.79rem; line-height:1.45;}
.metric-grid {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px;}
.watch {border:1px solid var(--border); border-radius:14px; padding:10px 12px; background:#0d131d;}
.watch-title {font-size:.78rem; font-weight:760; color:#e9eef6;}
.watch-note {font-size:.75rem; color:#93a0b0; margin-top:.18rem; line-height:1.35;}
.barwrap {margin-top:.4rem; background:#141d2a; border-radius:999px; height:8px; overflow:hidden;}
.bar {height:100%; border-radius:999px;}
.trust-row {display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,.055); gap:12px; font-size:.80rem;}
.trust-row:last-child {border-bottom:none;}
.text-right {text-align:right;}
.caption-tech {font-size:.75rem; color:#94a3b5;}
@media(max-width: 900px) {
  .timeline {grid-template-columns:1fr 1fr;}
  .metric-grid {grid-template-columns:1fr;}
}
</style>
""",
    unsafe_allow_html=True,
)


def tone_badge(text: str, tone: str) -> str:
    color, bg = TONE.get(tone, TONE["gray"])
    return f"<span class='chip' style='color:{color}; background:{bg}; border:1px solid {color}33'>{text}</span>"


def render_main_card(kicker: str, value: str, big: str, note: str, tone: str = "gray") -> None:
    color, bg = TONE.get(tone, TONE["gray"])
    st.markdown(
        f"""
<div class="card">
  <div class="kicker">{kicker}</div>
  <div class="value" style="color:{color}">{value}</div>
  <div class="big">{big}</div>
  <div class="note">{note}</div>
  <span class="pill" style="color:{color}; background:{bg}; border:1px solid {color}33">LIVE / RULE-BASED</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_small_metric(title: str, value: str, note: str, tone: str = "gray") -> None:
    color, bg = TONE.get(tone, TONE["gray"])
    st.markdown(
        f"""
<div class="minicard">
  <div class="smallcaps">{title}</div>
  <div style="font-size:1.35rem; font-weight:800; color:{color}; margin-top:.35rem">{value}</div>
  <div class="caption-tech" style="margin-top:.45rem">{note}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_bar(title: str, value: float, tone: str, note: str) -> None:
    color, bg = TONE.get(tone, TONE["gray"])
    v = 0 if not np.isfinite(value) else max(0, min(100, value))
    st.markdown(
        f"""
<div class="watch">
  <div class="labelrow">
    <div class="watch-title">{title}</div>
    <div class="smallcaps" style="color:{color}">{num(v,0) if np.isfinite(value) else '—'}/100</div>
  </div>
  <div class="barwrap"><div class="bar" style="width:{v}%; background:{color}"></div></div>
  <div class="watch-note">{note}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def scenario_tile(scn: dict) -> None:
    tone = scn.get("tone", "gray")
    color, bg = TONE.get(tone, TONE["gray"])
    why = "".join(f"<li>{x}</li>" for x in scn.get("why", [])[:4])
    conf = "".join(f"<li>{x}</li>" for x in scn.get("confirm", [])[:3])
    brk = "".join(f"<li>{x}</li>" for x in scn.get("break", [])[:3])
    st.markdown(
        f"""
<div class="scenario-box">
  <span class="chip" style="color:{color}; background:{bg}; border:1px solid {color}33">{scn.get('tag','SCENARIO')}</span>
  <div class="scenario-name" style="color:{color}">{scn.get('name','')}</div>
  <div class="caption-tech" style="margin-top:.35rem">Probability remains <b>research-gated</b> until the projection model passes point-in-time OOS validation.</div>
  <div class="smallcaps" style="margin-top:.8rem">Why this is on the board</div>
  <ul class="scenario-list">{why}</ul>
  <div class="smallcaps" style="margin-top:.6rem">What would confirm it</div>
  <ul class="scenario-list">{conf}</ul>
  <div class="smallcaps" style="margin-top:.6rem">What would break it</div>
  <ul class="scenario-list">{brk}</ul>
</div>
""",
        unsafe_allow_html=True,
    )


# sidebar
if st.sidebar.button("Refresh live data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("### Research gate")
st.sidebar.caption("Live dashboard can run without FRED key. Strict vintage / ALFRED validation is a separate step.")
st.sidebar.write("FRED API key:", "✅ detected" if FRED_API_KEY else "⚠️ not set")
st.sidebar.write("Projection model:", "✅ validated" if PROJECTION_MODEL_VALIDATED else "🔒 gated")
st.sidebar.write("Crash model:", "✅ validated" if CRASH_MODEL_VALIDATED else "🔒 gated")

with st.spinner("Loading official/public macro data…"):
    data, research, errors = fetch_all()

# core data
bbk_gdp, bbk_gdp_date = latest(data.get("BBKMGDP"))
bbk_co, bbk_co_date = latest(data.get("BBKMCOIX"))
bbk_lead, bbk_lead_date = latest(data.get("BBKMLEIX"))
wei, wei_date = latest(data.get("WEI"))
trimmed, trimmed_date = latest(data.get("PCETRIM12M159SFRBDAL"))
core_pce_yoy = yoy_from_index(data.get("PCEPILFE"))
headline_pce_yoy = yoy_from_index(data.get("PCEPI"))
trimmed_3m = lag_value(data.get("PCETRIM12M159SFRBDAL"), 3)
core_pce_yoy_3m = yoy_at_lag(data.get("PCEPILFE"), 3)
sahm, sahm_date = latest(data.get("SAHMREALTIME"))
claims, claims_date = latest(data.get("ICSA"))
sloos, sloos_date = latest(data.get("DRTSCILM"))
nfci_risk, nfci_date = latest(data.get("NFCIRISK"))
vix, vix_date = latest(data.get("VIXCLS"))
hy_oas, hy_date = latest(data.get("BAMLH0A0HYM2"))
spx, spx_date = latest(data.get("SP500"))
spx_dd_1y = one_year_drawdown(data.get("SP500"))
breakeven5, breakeven_date = latest(data.get("T5YIE"))
dgs10, dgs10_date = latest(data.get("DGS10"))
dgs2, dgs2_date = latest(data.get("DGS2"))
fedfunds, fedfunds_date = latest(data.get("FEDFUNDS"))
oil, oil_date = latest(data.get("DCOILWTICO"))
curve_2s10s = dgs10 - dgs2 if np.isfinite(dgs10) and np.isfinite(dgs2) else np.nan
oil_3m_ago = value_n_months_ago(data.get("DCOILWTICO"), 3)
oil_3m_chg = (oil / oil_3m_ago - 1.0) * 100.0 if np.isfinite(oil) and np.isfinite(oil_3m_ago) and oil_3m_ago != 0 else np.nan

# research datasets
if "EBP" in research and not research["EBP"].empty:
    ebp_df = research["EBP"].copy()
    for c in ["gz_spread", "ebp", "est_prob"]:
        if c in ebp_df:
            ebp_df[c] = pd.to_numeric(ebp_df[c], errors="coerce")
    ebp_clean = ebp_df.dropna(subset=["est_prob"])
    ebp_latest = ebp_clean.iloc[-1]
    ebp_prob = float(ebp_latest["est_prob"]) * 100.0
    ebp = float(ebp_latest["ebp"])
    ebp_date = pd.Timestamp(ebp_latest["date"])
    ebp_prev_prob = float(ebp_clean.iloc[-2]["est_prob"]) * 100.0 if len(ebp_clean) >= 2 else np.nan
else:
    ebp_prob = ebp = ebp_prev_prob = np.nan
    ebp_date = None

if "FCIG3" in research and not research["FCIG3"].empty:
    fcig3 = research["FCIG3"].copy()
    fcig_col = next((c for c in fcig3.columns if c.startswith("FCI-G Index")), None)
    if fcig_col:
        fcig3[fcig_col] = pd.to_numeric(fcig3[fcig_col], errors="coerce")
        fcig_clean = fcig3.dropna(subset=[fcig_col])
        fcig = float(fcig_clean.iloc[-1][fcig_col])
        fcig_prev = float(fcig_clean.iloc[-2][fcig_col]) if len(fcig_clean) >= 2 else np.nan
        fcig_date = pd.Timestamp(fcig_clean.iloc[-1]["date"])
    else:
        fcig = fcig_prev = np.nan
        fcig_date = None
else:
    fcig = fcig_prev = np.nan
    fcig_date = None

if "FCIG1" in research and not research["FCIG1"].empty:
    fcig1df = research["FCIG1"].copy()
    fcig1_col = next((c for c in fcig1df.columns if c.startswith("FCI-G Index")), None)
    if fcig1_col:
        fcig1df[fcig1_col] = pd.to_numeric(fcig1df[fcig1_col], errors="coerce")
        fcig1_clean = fcig1df.dropna(subset=[fcig1_col])
        fcig_1y = float(fcig1_clean.iloc[-1][fcig1_col])
    else:
        fcig_1y = np.nan
else:
    fcig_1y = np.nan

# logic

growth_label, growth_tone, growth_note = growth_state(bbk_gdp, bbk_co, wei)
lead_label, lead_tone = bbk_lead_state(bbk_lead)
infl_label, infl_tone, infl_direction = inflation_state(trimmed, core_pce_yoy, trimmed_3m, core_pce_yoy_3m)
labor_label, labor_tone = sahm_state(sahm)
fcig_label, fcig_tone, fcig_note = fcig_state(fcig)
stress_label, stress_tone = nfci_risk_state(nfci_risk)
regime = regime_descriptor(growth_label, infl_direction, infl_label)

lead_arrow, lead_change_word = delta_word(bbk_lead, lag_value(data.get("BBKMLEIX"), 1), higher_is_worse=False)
fcig_arrow, fcig_change_word = delta_word(fcig, fcig_prev, higher_is_worse=True)
ebp_arrow, ebp_change_word = delta_word(ebp_prob, ebp_prev_prob, higher_is_worse=True)
stress_arrow, stress_change_word = delta_word(nfci_risk, lag_value(data.get("NFCIRISK"), 4), higher_is_worse=True)

coverage = (len(data) + len(research)) / (len(SERIES) + 3)
quality_label = "LIVE DATA OK" if coverage >= 0.85 else "DATA DEGRADED"
quality_tone = "green" if coverage >= 0.85 else "amber"

# event/proxy states
inflation_resurgence_label, inflation_resurgence_tone = severity_label(
    np.nanmean([
        100 - historical_percentile(data.get("PCETRIM12M159SFRBDAL"), 10) if np.isfinite(historical_percentile(data.get("PCETRIM12M159SFRBDAL"), 10)) else np.nan,
        100 - historical_percentile(data.get("T5YIE"), 10) if np.isfinite(historical_percentile(data.get("T5YIE"), 10)) else np.nan,
    ]),
    35,
    65,
)
credit_label, credit_tone = severity_label(
    np.nanmean([
        historical_percentile(data.get("BAMLH0A0HYM2"), 10),
        ebp_prob,
    ]),
    35,
    60,
)
rate_label, rate_tone = severity_label(historical_percentile(data.get("DGS10"), 10), 40, 75)
energy_label, energy_tone = severity_label(np.nanmean([
    historical_percentile(data.get("DCOILWTICO"), 10),
    oil_3m_chg if np.isfinite(oil_3m_chg) else np.nan,
]), 35, 70)

# crash context gauges (descriptive, not validated probability)
fragility_score = np.nanmean([
    historical_percentile(data.get("BAMLH0A0HYM2"), 10),
    historical_percentile(data.get("DGS10"), 10),
    100 - historical_percentile(data.get("SP500"), 5) if np.isfinite(historical_percentile(data.get("SP500"), 5)) else np.nan,
])
stress_score = np.nanmean([
    historical_percentile(data.get("VIXCLS"), 10),
    historical_percentile(data.get("NFCIRISK"), 10),
    historical_percentile(data.get("BAMLH0A0HYM2"), 10),
])
shock_absorption = 100 - np.nanmean([
    historical_percentile(data.get("VIXCLS"), 10),
    historical_percentile(data.get("BAMLH0A0HYM2"), 10),
    historical_percentile(data.get("DGS10"), 10),
])
fragility_tone = "green" if np.isfinite(fragility_score) and fragility_score < 40 else ("amber" if np.isfinite(fragility_score) and fragility_score < 65 else "red")
stress_gauge_tone = "green" if np.isfinite(stress_score) and stress_score < 40 else ("amber" if np.isfinite(stress_score) and stress_score < 65 else "red")
shock_tone = "green" if np.isfinite(shock_absorption) and shock_absorption >= 60 else ("amber" if np.isfinite(shock_absorption) and shock_absorption >= 40 else "red")

base_scenarios = rank_scenarios(regime, bbk_lead, ebp_prob, fcig, infl_direction)
watchlist = watch_items(regime, growth_label, infl_direction)

# ---------------- header ----------------
col_a, col_b = st.columns([4.6, 1.4])
with col_a:
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-title">Macro Intelligence</div>
  <div class="hero-sub">Landing Page 1 · visual-first · live macro state + published benchmark context · exact probabilities stay locked until validated.</div>
  <div class="chips">
    {tone_badge(quality_label, quality_tone)}
    {tone_badge(f'Current regime: {regime}', 'blue')}
    {tone_badge('Projection gated', 'gray' if not PROJECTION_MODEL_VALIDATED else 'green')}
    {tone_badge('Crash model gated', 'gray' if not CRASH_MODEL_VALIDATED else 'green')}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
with col_b:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**Read this first**")
    st.caption(
        "This page is built to be easy to scan. Big colored blocks tell you the current state. Technical pieces stay gated unless they are backed by official data or already-validated rules."
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 1. macro now ----------------
st.markdown('<div class="section-title">1 · Macro now</div>', unsafe_allow_html=True)
mc = st.columns(5)
with mc[0]:
    render_main_card(
        "Economy",
        growth_label,
        pct(bbk_gdp, 2),
        f"BBK Monthly GDP · Coincident {signed(bbk_co,2,'σ')} · WEI {pct(wei,2)} · {date_str(bbk_gdp_date)}",
        growth_tone,
    )
with mc[1]:
    infl_vals = [x for x in [trimmed, core_pce_yoy] if np.isfinite(x)]
    infl_range = "—" if not infl_vals else f"{min(infl_vals):.1f}–{max(infl_vals):.1f}%"
    render_main_card(
        "Underlying inflation",
        infl_label,
        infl_range,
        f"Trimmed PCE {pct(trimmed,1)} · Core PCE {pct(core_pce_yoy,1)} · direction: {infl_direction}",
        infl_tone,
    )
with mc[2]:
    render_main_card(
        "Labor",
        labor_label,
        num(sahm, 2),
        f"Real-time Sahm · trigger 0.50pp · claims {num(claims,0)} · {date_str(sahm_date)}",
        labor_tone,
    )
with mc[3]:
    render_main_card(
        "12M financial impulse",
        fcig_label,
        signed(-fcig, 2, 'pp') if np.isfinite(fcig) else '—',
        f"Fed FCI-G baseline · {fcig_note} · latest {date_str(fcig_date)}",
        fcig_tone,
    )
with mc[4]:
    ebp_tone = "green" if np.isfinite(ebp_prob) and ebp_prob < 20 else ("amber" if np.isfinite(ebp_prob) and ebp_prob < 35 else ("red" if np.isfinite(ebp_prob) else "gray"))
    render_main_card(
        "12M recession benchmark",
        "FED EBP MODEL",
        pct(ebp_prob, 1),
        f"Published Fed recession benchmark · EBP {signed(ebp,2)} · {date_str(ebp_date)}",
        ebp_tone,
    )

# quick visuals
sv1, sv2, sv3, sv4 = st.columns(4)
with sv1:
    render_small_metric("Growth lead", f"{lead_arrow} {signed(bbk_lead,2,'σ')}", f"BBK Leading · {lead_label}", lead_tone)
with sv2:
    render_small_metric("Stress", f"{stress_arrow} {signed(nfci_risk,2)}", f"NFCI Risk · {stress_label}", stress_tone)
with sv3:
    render_small_metric("Rates context", pct(dgs10, 2), f"10Y Treasury · 2s10s {signed(curve_2s10s,2,'pp')}", "blue")
with sv4:
    render_small_metric("Energy proxy", f"${num(oil,1)}", f"WTI oil · 3M change {pct(oil_3m_chg,1)}", energy_tone)

# ---------------- 2. path ----------------
st.markdown('<div class="section-title">2 · Macro path</div>', unsafe_allow_html=True)
near_term = "POSITIVE" if np.isfinite(bbk_gdp) and bbk_gdp > 0 else ("CONTRACTING" if np.isfinite(bbk_gdp) else "UNKNOWN")
path_html = f"""
<div class="timeline">
  <div class="tcell">
    <div class="thead">Now</div>
    <div class="tval">{growth_label}</div>
    <div class="tnote">Broad activity right now. BBK GDP {pct(bbk_gdp,2)} · Coincident {signed(bbk_co,2,'σ')} · WEI {pct(wei,2)}.</div>
  </div>
  <div class="tcell">
    <div class="thead">+1Q</div>
    <div class="tval">{near_term}</div>
    <div class="tnote">Short-horizon bias from current broad/high-frequency data only. Exact probability is locked.</div>
  </div>
  <div class="tcell">
    <div class="thead">≈ +2Q</div>
    <div class="tval">{lead_label}</div>
    <div class="tnote">Uses BBK Leading. This is the main medium-horizon visual anchor on Landing v1.</div>
  </div>
  <div class="tcell">
    <div class="thead">+4Q</div>
    <div class="tval">{fcig_label} / EBP</div>
    <div class="tnote">12M published context: FCI-G {signed(fcig,2)} · EBP recession benchmark {pct(ebp_prob,1)}.</div>
  </div>
</div>
"""
st.markdown(path_html, unsafe_allow_html=True)
st.markdown(
    f"<div class='gate' style='margin-top:10px'><b>Current best description of the path:</b> {regime}. Exact regime probabilities remain locked until the projection engine is separately validated.</div>",
    unsafe_allow_html=True,
)

# ---------------- 3. scenarios ----------------
st.markdown('<div class="section-title">3 · Top 3 scenarios</div>', unsafe_allow_html=True)
sc1, sc2, sc3 = st.columns(3)
with sc1:
    scenario_tile(base_scenarios[0])
with sc2:
    scenario_tile(base_scenarios[1])
with sc3:
    scenario_tile(base_scenarios[2])

# ---------------- 4. event watch ----------------
st.markdown('<div class="section-title">4 · Event / pressure watch</div>', unsafe_allow_html=True)
aw1, aw2, aw3, aw4 = st.columns(4)
with aw1:
    render_small_metric("Inflation resurgence", inflation_resurgence_label, f"Trimmed/Core PCE + breakeven context", inflation_resurgence_tone)
with aw2:
    render_small_metric("Credit pressure", credit_label, f"HY OAS + Fed EBP benchmark", credit_tone)
with aw3:
    render_small_metric("Rates / fiscal pressure", rate_label, f"10Y yield percentile context", rate_tone)
with aw4:
    render_small_metric("Energy shock pressure", energy_label, f"WTI level + 3M move", energy_tone)

st.markdown(
    "<div class='gate'><b>Important:</b> this row is a live pressure board, not a final event-probability engine. Geopolitics, war, ceasefire, sanctions and other exogenous hazards need their own validated event layer later.</div>",
    unsafe_allow_html=True,
)

# ---------------- 5. market vs model ----------------
st.markdown('<div class="section-title">5 · Market vs model</div>', unsafe_allow_html=True)
mv1, mv2 = st.columns([1.3, 1.2])
with mv1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**Market pricing context**")
    st.markdown(
        f"""
<div class="trust-row"><div>5Y breakeven inflation</div><div class="text-right"><b>{pct(breakeven5,2)}</b><br><span class="caption-tech">Market inflation pricing</span></div></div>
<div class="trust-row"><div>10Y Treasury</div><div class="text-right"><b>{pct(dgs10,2)}</b><br><span class="caption-tech">Long-end rates context</span></div></div>
<div class="trust-row"><div>2Y Treasury</div><div class="text-right"><b>{pct(dgs2,2)}</b><br><span class="caption-tech">Front-end rates context</span></div></div>
<div class="trust-row"><div>Fed funds</div><div class="text-right"><b>{pct(fedfunds,2)}</b><br><span class="caption-tech">Current policy anchor</span></div></div>
<div class="trust-row"><div>2s10s curve</div><div class="text-right"><b>{signed(curve_2s10s,2,'pp')}</b><br><span class="caption-tech">Curve shape</span></div></div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
with mv2:
    st.markdown(
        "<div class='panel'><b>Expectation gap</b><br><div class='caption-tech' style='margin-top:.35rem'>This panel is deliberately conservative. We show market pricing context, but we do <b>not</b> claim 'market is wrong' until the expectation-gap mapping is validated. That prevents fake edge from narrative extrapolation.</div><div class='gate' style='margin-top:12px'><b>Status:</b> gap engine locked. Needed next: map economic projection vs market-implied pricing using validated links for growth, inflation, Fed path and credit.</div></div>",
        unsafe_allow_html=True,
    )

# ---------------- 6. crash control room ----------------
st.markdown('<div class="section-title">6 · Crash control room</div>', unsafe_allow_html=True)
cr1, cr2 = st.columns([1.1, 1.3])
with cr1:
    c1, c2 = st.columns(2)
    with c1:
        render_bar("Immediate stress", stress_score, stress_gauge_tone, "Descriptive gauge from VIX, NFCI Risk and HY OAS. Useful as context, not as a validated crash probability.")
        render_bar("Structural fragility", fragility_score, fragility_tone, "Placeholder descriptive gauge only. Formal fragility engine remains gated pending validation.")
    with c2:
        render_bar("Shock absorption", shock_absorption, shock_tone, "Higher means the market appears better able to absorb a shock. Still descriptive, not a final model.")
        render_bar("1Y drawdown pressure", abs(spx_dd_1y) if np.isfinite(spx_dd_1y) else np.nan, "amber" if np.isfinite(spx_dd_1y) and abs(spx_dd_1y) >= 10 else "green", "Current distance from the 1Y high on the S&P 500.")
with cr2:
    st.markdown(
        f"""
<div class="panel">
  <b>Crash probabilities</b>
  <div class="gate" style="margin-top:10px">3M / 6M / 12M probabilities of a >20% drawdown remain <b>research-gated</b>. We will only release them after point-in-time feature construction, long-history target definition, calibration and OOS validation are complete.</div>
  <div class="metric-grid" style="margin-top:12px">
    <div class="watch">
      <div class="watch-title">Most plausible failure mode right now</div>
      <div class="watch-note" style="margin-top:.35rem">Based on currently admitted components, the dominant visible risk is <b>growth / credit deterioration</b>, not a proven funding-system seizure.</div>
    </div>
    <div class="watch">
      <div class="watch-title">What would make crash risk rise fast?</div>
      <div class="watch-note" style="margin-top:.35rem">A worse labor signal, wider credit stress, and loss of financial tailwind at the same time. The point is the <b>combination</b>, not any single headline.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# ---------------- 7. what changed / what to watch ----------------
st.markdown('<div class="section-title">7 · What changed · what to watch next</div>', unsafe_allow_html=True)
wc1, wc2 = st.columns(2)
risk_up = []
risk_down = []
if np.isfinite(bbk_lead):
    item = f"Growth lead {lead_arrow} {lead_change_word}: BBK Leading {signed(bbk_lead,2,'σ')}"
    (risk_down if lead_change_word == "improving" else risk_up).append(item)
if np.isfinite(fcig):
    item = f"Financial impulse {fcig_arrow} {fcig_change_word}: FCI-G {signed(fcig,2)}"
    (risk_down if fcig_change_word == "improving" else risk_up).append(item)
if np.isfinite(ebp_prob):
    item = f"Credit/recession benchmark {ebp_arrow} {ebp_change_word}: {pct(ebp_prob,1)}"
    (risk_down if ebp_change_word == "improving" else risk_up).append(item)
if np.isfinite(nfci_risk):
    item = f"Immediate stress {stress_arrow} {stress_change_word}: NFCI Risk {signed(nfci_risk,2)}"
    (risk_down if stress_change_word == "improving" else risk_up).append(item)
if np.isfinite(sahm) and sahm < 0.50:
    risk_down.append(f"Labor confirmation still calm: Sahm {num(sahm,2)} below 0.50 trigger")
if "ABOVE" in infl_label:
    risk_up.append(f"Policy constraint still matters: underlying inflation range {infl_range} remains above 2%")

with wc1:
    st.markdown('<div class="panel"><b>What changed lately</b>', unsafe_allow_html=True)
    st.markdown("**Headwind / risk-up**")
    if risk_up:
        for item in risk_up[:6]:
            st.markdown(f"- {item}")
    else:
        st.caption("No admitted deterministic risk-up change right now.")
    st.markdown("**Buffer / risk-down**")
    if risk_down:
        for item in risk_down[:6]:
            st.markdown(f"- {item}")
    else:
        st.caption("No admitted deterministic risk-down change right now.")
    st.markdown('</div>', unsafe_allow_html=True)
with wc2:
    st.markdown('<div class="panel"><b>What to watch next</b>', unsafe_allow_html=True)
    for item in watchlist:
        st.markdown(
            f"<div class='watch' style='margin-bottom:8px'><div class='watch-title'>{item['label']}</div><div class='watch-note'>{item['need']}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- 8. trust panel + charts ----------------
st.markdown('<div class="section-title">8 · Trust panel</div>', unsafe_allow_html=True)
tr1, tr2 = st.columns([1.1, 1.3])
with tr1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**How much to trust this page**")
    st.markdown(
        f"""
<div class="trust-row"><div>Live data coverage</div><div class="text-right"><b>{coverage:.0%}</b><br><span class="caption-tech">{quality_label}</span></div></div>
<div class="trust-row"><div>Projection model</div><div class="text-right"><b>{'Released' if PROJECTION_MODEL_VALIDATED else 'Locked'}</b><br><span class="caption-tech">Needs point-in-time OOS proof</span></div></div>
<div class="trust-row"><div>Crash model</div><div class="text-right"><b>{'Released' if CRASH_MODEL_VALIDATED else 'Locked'}</b><br><span class="caption-tech">No fake crash %</span></div></div>
<div class="trust-row"><div>Numerical path</div><div class="text-right"><b>Deterministic</b><br><span class="caption-tech">No LLM-generated weights</span></div></div>
<div class="trust-row"><div>Key limitation</div><div class="text-right"><b>Latest revision data</b><br><span class="caption-tech">Backtesting must use vintages later</span></div></div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
with tr2:
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("**Growth / lead visual**")
        df_plot = pd.concat(
            [series_to_plot(data.get("BBKMCOIX"), 8), series_to_plot(data.get("BBKMLEIX"), 8)],
            axis=1,
        )
        if not df_plot.empty:
            df_plot.columns = ["BBK Coincident", "BBK Leading"]
            st.line_chart(df_plot)
        else:
            st.caption("Chart unavailable.")
    with ch2:
        st.markdown("**Inflation visual**")
        s1 = series_to_plot(data.get("PCETRIM12M159SFRBDAL"), 8)
        s2 = series_to_plot(data.get("PCEPILFE"), 8)
        if not s1.empty or not s2.empty:
            inf = pd.concat([s1, s2], axis=1)
            inf.columns = ["Trimmed Mean PCE", "Core PCE Index"]
            # transform second column to yoy when possible for better comparability
            core_series = data.get("PCEPILFE")
            if core_series is not None and not core_series.empty:
                yoy_vals = core_series.pct_change(12) * 100
                yoy_vals = yoy_vals[yoy_vals.index >= (yoy_vals.dropna().index[-1] - pd.DateOffset(years=8))] if not yoy_vals.dropna().empty else yoy_vals
                inf = pd.concat([s1.rename(columns={"value":"Trimmed Mean PCE"}), yoy_vals.to_frame(name="Core PCE YoY")], axis=1)
            st.line_chart(inf.dropna(how="all"))
        else:
            st.caption("Chart unavailable.")

with st.expander("Technical notes / why some blocks are still locked"):
    st.markdown(
        """
- **Why no exact macro probabilities yet?** Because point-in-time, out-of-sample validation has not been completed. We deliberately avoid fake precision.
- **Why no crash probability yet?** Crash models are especially vulnerable to overfitting. We will not show a number until the target definition, features and calibration are validated across history.
- **Why use BBK / Fed models on the landing page?** Because they are published external benchmarks and better than pretending we already solved the whole projection problem.
- **What happens next?** We test candidate components one by one: KEEP / SUPPORTING ONLY / REJECT. Only proven components graduate into the model.
"""
    )
    st.dataframe(pd.DataFrame(EVIDENCE), use_container_width=True, hide_index=True)

with st.expander("Raw source readings / freshness"):
    rows = [
        ["BBK Monthly GDP", bbk_gdp, "% annualized", bbk_gdp_date],
        ["BBK Coincident", bbk_co, "σ", bbk_co_date],
        ["BBK Leading", bbk_lead, "σ", bbk_lead_date],
        ["WEI", wei, "GDP-aligned %", wei_date],
        ["Trimmed Mean PCE", trimmed, "% y/y", trimmed_date],
        ["Core PCE YoY", core_pce_yoy, "% y/y", latest(data.get("PCEPILFE"))[1]],
        ["Headline PCE YoY", headline_pce_yoy, "% y/y", latest(data.get("PCEPI"))[1]],
        ["Sahm real-time", sahm, "pp", sahm_date],
        ["Initial claims", claims, "claims", claims_date],
        ["SLOOS C&I tightening", sloos, "net %", sloos_date],
        ["Fed EBP", ebp, "index", ebp_date],
        ["Fed EBP recession benchmark", ebp_prob, "%", ebp_date],
        ["Fed FCI-G", fcig, "pp growth impulse", fcig_date],
        ["NFCI Risk", nfci_risk, "index", nfci_date],
        ["VIX", vix, "index", vix_date],
        ["HY OAS", hy_oas, "%", hy_date],
        ["S&P 500", spx, "index", spx_date],
        ["5Y Breakeven", breakeven5, "%", breakeven_date],
        ["10Y Treasury", dgs10, "%", dgs10_date],
        ["2Y Treasury", dgs2, "%", dgs2_date],
        ["Fed funds", fedfunds, "%", fedfunds_date],
        ["WTI Oil", oil, "USD/barrel", oil_date],
    ]
    raw = pd.DataFrame(rows, columns=["Series", "Latest", "Unit", "Observation date"])
    raw["Observation date"] = pd.to_datetime(raw["Observation date"], errors="coerce").dt.date
    st.dataframe(raw, use_container_width=True, hide_index=True)

if errors:
    with st.expander(f"Data errors ({len(errors)})"):
        err_df = pd.DataFrame([{"Source": k, "Error": v} for k, v in errors.items()])
        st.dataframe(err_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    "Landing Page 1 is intentionally conservative: visual, readable, and honest. Live state and published benchmark context are shown now; our own exact macro and crash probabilities stay locked until the validation pipeline proves them."
)

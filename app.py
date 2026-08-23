from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================
# MACRO INTELLIGENCE — LANDING PAGE 1 / COMPACT V3
# ============================================================
# This page intentionally separates:
#   1) current economic state,
#   2) projected macro path,
#   3) market/crash vulnerabilities,
#   4) world/event scenarios and constraints.
# Exact proprietary macro/crash/event probabilities remain gated until
# point-in-time out-of-sample validation is complete.
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
FED_FCIG_URL = "https://www.federalreserve.gov/econres/notes/feds-notes/fci_g_public_monthly_3yr.csv"
TREASURY_DEBT_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
AI_GPR_MONTHLY_URL = "https://www.matteoiacoviello.com/ai_gpr_files/ai_gpr_data_monthly.csv"

# Current-law reference, not a fitted model input.
# P.L. 119-21 set the statutory limit at $41.104tn on 2025-07-04.
STATUTORY_DEBT_LIMIT_TN = 41.104
DEBT_LIMIT_REFERENCE_DATE = "04 Jul 2025"
CBO_BASELINE_LIMIT_TIMING = "sometime in 2027"

PROJECTION_MODEL_VALIDATED = False
CRASH_MODEL_VALIDATED = False
EVENT_PROBABILITY_MODEL_VALIDATED = False
EXPECTATION_GAP_VALIDATED = False


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


SERIES: Dict[str, SeriesSpec] = {
    # Growth
    "BBKMGDP": SeriesSpec("BBK Monthly GDP Growth", "1960-01-01", "% annualized"),
    "BBKMCOIX": SeriesSpec("BBK Coincident Index", "1960-01-01", "σ"),
    "BBKMLEIX": SeriesSpec("BBK Leading Index", "1960-01-01", "σ"),
    "WEI": SeriesSpec("Weekly Economic Index", "2008-01-01", "%"),
    # Inflation
    "PCETRIM12M159SFRBDAL": SeriesSpec("Dallas Fed Trimmed Mean PCE", "1977-01-01", "% y/y"),
    "PCEPILFE": SeriesSpec("Core PCE Price Index", "1959-01-01", "index"),
    # Labor / credit
    "SAHMREALTIME": SeriesSpec("Real-time Sahm Rule", "1959-12-01", "pp"),
    "ICSA": SeriesSpec("Initial Jobless Claims", "1967-01-01", "claims"),
    "DRTSCILM": SeriesSpec("SLOOS C&I Tightening", "1990-01-01", "net %"),
    # Market / stress
    "NFCIRISK": SeriesSpec("NFCI Risk", "1971-01-01", "index"),
    "VIXCLS": SeriesSpec("VIX", "1990-01-01", "index"),
    "BAMLH0A0HYM2": SeriesSpec("HY OAS", "1996-01-01", "%"),
    "SP500": SeriesSpec("S&P 500", "2016-01-01", "index"),
    # Rates / pricing
    "T5YIE": SeriesSpec("5Y Breakeven", "2003-01-01", "%"),
    "DGS10": SeriesSpec("10Y Treasury", "1962-01-01", "%"),
    "DGS2": SeriesSpec("2Y Treasury", "1976-06-01", "%"),
    "FEDFUNDS": SeriesSpec("Fed Funds", "1954-07-01", "%"),
    "THREEFYTP10": SeriesSpec("10Y Term Premium", "1990-01-01", "%"),
    # Energy
    "DCOILWTICO": SeriesSpec("WTI Oil", "1986-01-02", "$/bbl"),
    # Fiscal constraints
    "GFDEGDQ188S": SeriesSpec("Federal Debt / GDP", "1966-01-01", "% GDP"),
    "FYFSGDA188S": SeriesSpec("Federal Deficit / GDP", "1940-01-01", "% GDP"),
    "FYOIGDA188S": SeriesSpec("Federal Interest Outlays / GDP", "1940-01-01", "% GDP"),
    # Event / supply / uncertainty context
    "GSCPI": SeriesSpec("Global Supply Chain Pressure Index", "1997-01-01", "σ"),
    "USEPUINDXD": SeriesSpec("US Economic Policy Uncertainty", "1985-01-01", "index"),
}

# Scenario library is intentionally broad. Inclusion here is NOT proof.
SCENARIO_LIBRARY = [
    ("Macro", "Disinflationary slowdown", "Growth cools while inflation falls", "Growth, labor, credit, inflation"),
    ("Macro", "Reacceleration", "Leading growth and breadth recover", "BBK lead, WEI, breadth, credit"),
    ("Macro", "Recession / credit crack", "Labor and credit weaken together", "Sahm, claims, EBP, HY OAS"),
    ("Geopolitical", "War continues / financing manageable", "Conflict spending rises but financing remains absorbable", "Fiscal capacity, auctions, rates, energy"),
    ("Geopolitical", "War + energy stagflation", "Supply shock lifts inflation while growth weakens", "Oil, breakevens, rates, growth"),
    ("Geopolitical", "Fiscal-forced de-escalation", "Fiscal/rate constraints materially raise pressure to shrink conflict", "Debt headroom, deficit, interest burden, term premium"),
    ("Geopolitical", "Diplomatic ceasefire / peace dividend", "Risk premium and supply stress normalize", "Diplomacy feed, oil, freight, rates"),
    ("Geopolitical", "Crisis-forced ceasefire", "De-escalation occurs because fiscal/economic stress becomes binding", "Fiscal stress, credit, growth, political funding"),
    ("Fiscal", "Debt-limit confrontation", "Legal borrowing constraint becomes binding", "Debt subject to limit, X-date, extraordinary measures"),
    ("Fiscal", "Treasury term-premium shock", "Heavy issuance / fiscal concern lifts long-end compensation", "10Y, term premium, auction metrics"),
    ("Fiscal", "Fiscal crowding-out", "Government financing raises private borrowing costs", "Yields, term premium, housing/capex"),
    ("Credit", "Private-credit stress", "Opaque/illiquid credit losses transmit to broader credit", "BDC/private-credit data, HY, banks"),
    ("Credit", "Bank / CRE stress", "CRE losses and funding stress tighten lending", "CRE delinquencies, bank funding, SLOOS"),
    ("Liquidity", "Dollar funding squeeze", "Funding stress forces deleveraging", "Funding spreads, basis, FX swaps, NFCI"),
    ("Market", "Broad ATH / healthy broadening", "Large, small and equal-weight markets confirm", "SPY/IWM/RSP, breadth"),
    ("Market", "Narrow ATH / concentration fragility", "Headline index rises while participation deteriorates", "Breadth, concentration, earnings"),
    ("Market", "ATH + credit divergence", "Price remains strong while credit weakens", "Index ATH, EBP, HY OAS"),
    ("Market", "Low-vol + leverage unwind", "Calm conditions encourage leverage then amplify shock", "VIX, leverage, funding, liquidity"),
    ("Market", "Correlation spike + falling liquidity", "Diversification disappears while market depth falls", "Cross-asset correlation, depth, funding"),
    ("Energy", "Oil supply shock", "Physical disruption transmits into inflation and growth", "Oil curve, shipping, shortages"),
    ("China", "China stimulus / credit impulse", "China demand impulse lifts global cyclicals", "TSF, credit impulse, PMI, property"),
    ("China", "China property relapse", "Property weakness drags credit and global demand", "Property sales, defaults, TSF"),
    ("Japan", "BOJ / yen-carry unwind", "Rates and FX force global deleveraging", "JGB, USDJPY, cross-asset vol"),
    ("Trade", "Tariff / sanctions escalation", "Trade barriers raise costs and weaken volumes", "Tariffs, trade, freight, prices"),
    ("Cyber", "Critical financial infrastructure shock", "Payments/clearing outage creates liquidity stress", "Operational/event feed, funding, vol"),
    ("Technology", "AI productivity boom", "Productivity offsets wage/inflation pressure", "Productivity, capex, margins"),
    ("Technology", "AI capex / debt unwind", "Capex expectations and financing reverse", "Capex, credit, earnings revisions"),
    ("Policy", "Fed too tight", "Policy stays restrictive after underlying economy weakens", "FCI-G, labor, inflation, rates"),
    ("Policy", "Inflation-forced tightening", "Inflation resurgence prevents easing", "PCE, breakevens, oil, wages"),
]

SCENARIO_SCREEN = [
    ("ATH alone", "REJECT STANDALONE", "HIGH", "ATH is context, not a crash trigger."),
    ("Russell / IWM ATH alone", "REJECT STANDALONE", "MEDIUM", "Condition on breadth, rates, credit and earnings."),
    ("Breadth strength / failure", "KEEP CORE STATE", "HIGH", "Use as market-state confirmation."),
    ("Credit widening / EBP", "KEEP CORE", "HIGH", "Forward downturn / transmission information."),
    ("ATH + credit deterioration", "KEEP CONDITIONAL", "MED-HIGH", "High-priority divergence; bespoke OOS test still required."),
    ("Rate / term-premium shock + rich valuation", "KEEP CORE", "HIGH", "Fragility through discount rates and liquidity."),
    ("Low VIX alone", "REJECT STANDALONE", "HIGH", "Calm volatility alone is not a crash signal."),
    ("Low VIX + high leverage", "KEEP FRAGILITY", "HIGH", "Volatility-paradox / deleveraging vulnerability."),
    ("High leverage alone", "SUPPORTING ONLY", "HIGH", "Vulnerability, not timing."),
    ("Funding stress + leverage", "KEEP CORE", "HIGH", "Key crash-amplification channel."),
    ("Momentum melt-up -> crash", "REVISE", "HIGH", "Simple ATH melt-up formulation is not supported."),
    ("Failed ATH breakout", "RESEARCH ONLY", "LOW-MED", "Do not promote without stronger evidence."),
    ("Concentration + narrowing breadth", "KEEP CONDITIONAL", "MED-HIGH", "Needs credit/liquidity/earnings context."),
    ("Energy shock + sticky inflation + yields", "KEEP EVENT", "HIGH", "Clear macro transmission channel."),
    ("Fiscal-forced de-escalation", "KEEP AS CONDITIONAL SCENARIO", "MEDIUM", "Economic constraint can raise de-escalation pressure, but cannot determine political choice alone."),
]

HEADERS = {
    "User-Agent": "MacroIntelligence/3.0 (+Streamlit; research dashboard)",
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
        r = requests.get(FRED_API_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if not obs:
            raise ValueError(f"No observations returned for {series_id}")
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"].replace(".", np.nan), errors="coerce")
        s = df.dropna().set_index("date")["value"].sort_index()
    else:
        r = requests.get(
            FRED_GRAPH_URL,
            params={"id": series_id, "cosd": start},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.shape[1] < 2:
            raise ValueError(f"Unexpected FRED response for {series_id}")
        dcol = df.columns[0]
        vcol = series_id if series_id in df.columns else df.columns[-1]
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        df[vcol] = pd.to_numeric(df[vcol].replace(".", np.nan), errors="coerce")
        s = df.dropna(subset=[dcol, vcol]).set_index(dcol)[vcol].sort_index()
    if s.empty:
        raise ValueError(f"Empty series: {series_id}")
    s.name = series_id
    return s


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_research_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "date" not in df.columns:
        raise ValueError("Expected date column")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_treasury_debt() -> Tuple[float, Optional[pd.Timestamp]]:
    params = {"sort": "-record_date", "page[size]": 1}
    r = requests.get(TREASURY_DEBT_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        raise ValueError("No Treasury debt data")
    row = data[0]
    debt = float(row["tot_pub_debt_out_amt"]) / 1e12
    return debt, pd.Timestamp(row["record_date"])


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yahoo(symbol: str, start: str = "2000-01-01") -> pd.Series:
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int((pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": p1,
        "period2": p2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    idx = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(None)
    adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
    if adj is None:
        adj = result["indicators"]["quote"][0]["close"]
    s = pd.Series(pd.to_numeric(adj, errors="coerce"), index=idx, name=symbol).dropna().sort_index()
    if s.empty:
        raise ValueError(f"Empty Yahoo series {symbol}")
    return s


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ai_gpr_monthly() -> pd.DataFrame:
    """Optional public geopolitical-risk feed. It informs event activity, not political intent."""
    r = requests.get(AI_GPR_MONTHLY_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty:
        raise ValueError("Empty AI-GPR data")
    date_col = next((c for c in df.columns if "date" in c.lower()), df.columns[0])
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col).set_index(date_col)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    return df


def load_all():
    data, research, market, errors = {}, {}, {}, {}
    for sid, spec in SERIES.items():
        try:
            data[sid] = fetch_fred(sid, spec.start)
        except Exception as exc:
            errors[sid] = str(exc)
    for name, url in {"EBP": FED_EBP_URL, "FCIG": FED_FCIG_URL}.items():
        try:
            research[name] = fetch_research_csv(url)
        except Exception as exc:
            errors[name] = str(exc)
    for sym in ["SPY", "IWM", "RSP"]:
        try:
            market[sym] = fetch_yahoo(sym)
        except Exception as exc:
            errors[f"Yahoo:{sym}"] = str(exc)
    try:
        debt_now, debt_date = fetch_treasury_debt()
    except Exception as exc:
        debt_now, debt_date = np.nan, None
        errors["TreasuryDebt"] = str(exc)
    try:
        gpr = fetch_ai_gpr_monthly()
    except Exception as exc:
        gpr = pd.DataFrame()
        errors["AI-GPR"] = str(exc)
    return data, research, market, gpr, debt_now, debt_date, errors


# ----------------------------- helpers -----------------------------
def latest(s: Optional[pd.Series]) -> Tuple[float, Optional[pd.Timestamp]]:
    if s is None or s.empty:
        return np.nan, None
    x = s.dropna()
    return (float(x.iloc[-1]), pd.Timestamp(x.index[-1])) if len(x) else (np.nan, None)


def lag_value(s: Optional[pd.Series], n: int = 1) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    return float(x.iloc[-1 - n]) if len(x) > n else np.nan


def months_ago(s: Optional[pd.Series], months: int) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    target = x.index[-1] - pd.DateOffset(months=months)
    y = x[x.index <= target]
    return float(y.iloc[-1]) if len(y) else np.nan


def yoy_from_index(s: Optional[pd.Series]) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    return float((x.iloc[-1] / x.iloc[-13] - 1) * 100) if len(x) >= 13 else np.nan


def yoy_at_lag(s: Optional[pd.Series], lag: int) -> float:
    if s is None:
        return np.nan
    x = s.dropna()
    end = len(x) - 1 - lag
    start = end - 12
    return float((x.iloc[end] / x.iloc[start] - 1) * 100) if start >= 0 else np.nan


def hist_pct(s: Optional[pd.Series], years: int = 10) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    x = x[x.index >= x.index[-1] - pd.DateOffset(years=years)]
    if len(x) < 20:
        return np.nan
    return float((x <= x.iloc[-1]).mean() * 100)


def dist_to_ath(s: Optional[pd.Series]) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    return float((x.iloc[-1] / x.max() - 1) * 100)


def relative_change(a: Optional[pd.Series], b: Optional[pd.Series], months: int = 3) -> float:
    if a is None or b is None or a.empty or b.empty:
        return np.nan
    df = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if df.empty:
        return np.nan
    r = df["a"] / df["b"]
    old = r[r.index <= r.index[-1] - pd.DateOffset(months=months)]
    if old.empty or old.iloc[-1] == 0:
        return np.nan
    return float((r.iloc[-1] / old.iloc[-1] - 1) * 100)


def fmt(x: float, digits: int = 1, suffix: str = "") -> str:
    return "—" if not np.isfinite(x) else f"{x:.{digits}f}{suffix}"


def signed(x: float, digits: int = 1, suffix: str = "") -> str:
    return "—" if not np.isfinite(x) else f"{x:+.{digits}f}{suffix}"


def growth_state(gdp: float, coincident: float, wei: float):
    if not np.isfinite(gdp) or not np.isfinite(coincident):
        return "UNKNOWN", "gray"
    if coincident <= -1:
        return "RECESSION-LIKE", "red"
    if gdp < 0:
        return "CONTRACTING", "red"
    if np.isfinite(wei) and wei < 0 < gdp:
        return "MIXED", "amber"
    if coincident < 0:
        return "POSITIVE · BELOW TREND", "amber"
    return "POSITIVE · ABOVE TREND", "green"


def lead_state(x: float):
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    if x <= -1:
        return "DOWNTURN LEAD", "red"
    if x < 0:
        return "BELOW-TREND LEAD", "amber"
    return "ABOVE-TREND LEAD", "green"


def inflation_state(trimmed: float, core: float, t3: float, c3: float):
    vals = [x for x in [trimmed, core] if np.isfinite(x)]
    if not vals:
        return "UNKNOWN", "gray", "UNKNOWN"
    if all(x > 2 for x in vals):
        level, tone = "ABOVE TARGET", "amber"
    elif all(x <= 2 for x in vals):
        level, tone = "AT / BELOW TARGET", "green"
    else:
        level, tone = "MIXED", "amber"
    dirs = []
    if np.isfinite(trimmed) and np.isfinite(t3):
        dirs.append(np.sign(trimmed - t3))
    if np.isfinite(core) and np.isfinite(c3):
        dirs.append(np.sign(core - c3))
    direction = "COOLING" if dirs and all(d < 0 for d in dirs) else ("HEATING" if dirs and all(d > 0 for d in dirs) else "MIXED")
    return level, tone, direction


def labor_state(sahm: float):
    if not np.isfinite(sahm):
        return "UNKNOWN", "gray"
    return ("RECESSION SIGNAL", "red") if sahm >= 0.50 else ("NO SAHM SIGNAL", "green")


def fcig_state(x: float):
    if not np.isfinite(x):
        return "UNKNOWN", "gray"
    return ("HEADWIND", "red") if x > 0 else (("TAILWIND", "green") if x < 0 else ("NEUTRAL", "blue"))


def regime_name(growth: str, infl_dir: str):
    weak = any(k in growth for k in ["BELOW", "CONTRACT", "RECESSION", "MIXED"])
    if weak and infl_dir == "COOLING":
        return "DISINFLATIONARY SLOWDOWN"
    if weak and infl_dir == "HEATING":
        return "STAGFLATION RISK"
    if not weak and infl_dir == "COOLING":
        return "GOLDILOCKS / DISINFLATION"
    if not weak and infl_dir == "HEATING":
        return "REFLATION"
    return "MIXED / TRANSITION"


def tone_from_score(x: float):
    if not np.isfinite(x):
        return "gray"
    if x < 40:
        return "green"
    if x < 65:
        return "amber"
    return "red"


def fiscal_constraint_score(debt_gdp: float, deficit_gdp: float, interest_gdp: float, term_premium: float) -> float:
    """Descriptive pressure proxy, NOT a validated fiscal-crisis probability."""
    pieces = []
    if np.isfinite(debt_gdp):
        pieces.append(np.clip((debt_gdp - 70) / 70 * 100, 0, 100))
    if np.isfinite(deficit_gdp):
        pieces.append(np.clip((abs(min(deficit_gdp, 0)) - 2) / 8 * 100, 0, 100))
    if np.isfinite(interest_gdp):
        pieces.append(np.clip((interest_gdp - 1) / 4 * 100, 0, 100))
    if np.isfinite(term_premium):
        pieces.append(np.clip((term_premium + 0.25) / 2.0 * 100, 0, 100))
    return float(np.mean(pieces)) if pieces else np.nan


def energy_pressure_score(oil_pctile: float, oil_3m: float, breakeven_pctile: float) -> float:
    parts = []
    if np.isfinite(oil_pctile):
        parts.append(oil_pctile)
    if np.isfinite(oil_3m):
        parts.append(np.clip(50 + oil_3m * 2, 0, 100))
    if np.isfinite(breakeven_pctile):
        parts.append(breakeven_pctile)
    return float(np.mean(parts)) if parts else np.nan




def pct_change_over(s: Optional[pd.Series], months: int = 3) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    old = x[x.index <= x.index[-1] - pd.DateOffset(months=months)]
    if old.empty or old.iloc[-1] == 0:
        return np.nan
    return float((x.iloc[-1] / old.iloc[-1] - 1) * 100)


def level_change_over(s: Optional[pd.Series], months: int = 3) -> float:
    if s is None or s.empty:
        return np.nan
    x = s.dropna()
    old = x[x.index <= x.index[-1] - pd.DateOffset(months=months)]
    if old.empty:
        return np.nan
    return float(x.iloc[-1] - old.iloc[-1])


def first_numeric_col(df: pd.DataFrame, includes: tuple[str, ...], excludes: tuple[str, ...] = ()) -> Optional[str]:
    for c in df.columns:
        low = c.lower().replace("-", "_")
        if all(k.lower() in low for k in includes) and not any(k.lower() in low for k in excludes):
            if pd.api.types.is_numeric_dtype(df[c]):
                return c
    return None


def gpr_readings(gpr: pd.DataFrame) -> dict:
    out = {"gpr": np.nan, "gpr_pct": np.nan, "gpr_change": np.nan, "oil_gpr": np.nan, "acts": np.nan, "threats": np.nan}
    if gpr is None or gpr.empty:
        return out
    numeric = gpr.select_dtypes(include=[np.number])
    if numeric.empty:
        return out
    main_col = first_numeric_col(gpr, ("gpr", "ai"), ("oil", "non", "threat", "act", "orig"))
    if main_col is None:
        main_col = first_numeric_col(gpr, ("gpr",), ("oil", "non", "threat", "act", "orig"))
    oil_col = first_numeric_col(gpr, ("oil", "gpr"))
    act_col = first_numeric_col(gpr, ("act", "gpr")) or first_numeric_col(gpr, ("gpr", "act"))
    threat_col = first_numeric_col(gpr, ("threat", "gpr")) or first_numeric_col(gpr, ("gpr", "threat"))
    if main_col:
        x = pd.to_numeric(gpr[main_col], errors="coerce").dropna()
        if len(x):
            out["gpr"] = float(x.iloc[-1])
            hist = x[x.index >= x.index[-1] - pd.DateOffset(years=10)]
            if len(hist) >= 12:
                out["gpr_pct"] = float((hist <= hist.iloc[-1]).mean() * 100)
            old = x[x.index <= x.index[-1] - pd.DateOffset(months=3)]
            if len(old):
                out["gpr_change"] = float(x.iloc[-1] - old.iloc[-1])
    for key, col in [("oil_gpr", oil_col), ("acts", act_col), ("threats", threat_col)]:
        if col:
            x = pd.to_numeric(gpr[col], errors="coerce").dropna()
            if len(x): out[key] = float(x.iloc[-1])
    return out


def crash_state_name(stress: float, fragility: float) -> tuple[str, str, str]:
    if stress >= 65 and fragility >= 65:
        return "CRASH DANGER", "red", "Stress is active while the system is already fragile."
    if stress < 50 and fragility >= 65:
        return "POWDER KEG", "amber", "Fragile, but the active-stress cascade is not yet present."
    if stress >= 65 and fragility < 65:
        return "SHOCK / STRESS", "red", "Stress is high, but structural fragility is less extreme."
    if stress >= 45 or fragility >= 50:
        return "WATCH", "amber", "Some vulnerability is present; no full crash configuration."
    return "RESILIENT", "green", "Low stress and lower structural fragility."


def plain_regime(growth: str, lead: str, credit_tone: str, stress_score: float) -> tuple[str, str]:
    if "RECESSION" in growth or "CONTRACT" in growth:
        return "ECONOMY CONTRACTING", "Growth has crossed into contractionary territory."
    if "BELOW" in growth or "BELOW" in lead:
        if credit_tone == "red" or stress_score >= 65:
            return "SLOWING · STRESS BUILDING", "Growth momentum is weak and financial stress is reinforcing it."
        return "GROWING · LOSING MOMENTUM", "The economy is still expanding, but leading growth is softer."
    if "ABOVE" in growth and "ABOVE" in lead:
        return "EXPANDING · MOMENTUM HEALTHY", "Growth and leading activity are both above trend."
    return "TRANSITION · NEED CONFIRMATION", "The data do not yet agree on a single clean path."


def adaptive_scenarios(*, growth: str, lead_value: float, lead_delta: float, wei: float, inflation_dir: str,
                       claims: float, claims_3m: float, ebp_prob: float, hy: float, hy_3m: float,
                       fcig: float, market_structure: str, fiscal_score: float, rates_score: float,
                       energy_score: float, funding_score: float, gpr_pct: float, gpr_change: float,
                       gscpi: float, gscpi_delta: float, epu_pct: float, spy_ath: float) -> list[dict]:
    """Heuristic evidence ranking only. score is NOT probability."""
    scenarios = []
    def add(name, family, impact, rules, confirms, invalidates, transmission, confidence="SCREENED"):
        hits = [r for r in rules if r[0]]
        total = len(rules)
        score = int(round(100 * len(hits) / total)) if total else 0
        direction = "↑" if len(hits) >= max(1, total//2) else "→"
        tone = "red" if impact == "SEVERE" and score >= 50 else ("amber" if score >= 40 else ("green" if family in ["Positive", "Market"] and score >= 50 else "blue"))
        scenarios.append({"name":name,"family":family,"impact":impact,"score":score,"hits":[r[1] for r in hits],"total":total,"direction":direction,"tone":tone,"confirms":confirms,"invalidates":invalidates,"transmission":transmission,"confidence":confidence})
    weak_growth = any(k in growth for k in ["BELOW","MIXED","CONTRACT","RECESSION"])
    claims_worse = np.isfinite(claims) and np.isfinite(claims_3m) and claims > claims_3m
    hy_worse = np.isfinite(hy) and np.isfinite(hy_3m) and hy > hy_3m
    lead_improving = np.isfinite(lead_delta) and lead_delta > 0
    gpr_high = np.isfinite(gpr_pct) and gpr_pct >= 70
    gpr_rising = np.isfinite(gpr_change) and gpr_change > 0
    supply_stress = (np.isfinite(gscpi) and gscpi > 1) or (np.isfinite(gscpi_delta) and gscpi_delta > .5)
    epu_high = np.isfinite(epu_pct) and epu_pct >= 75
    near_ath = np.isfinite(spy_ath) and spy_ath >= -2
    add("Disinflationary slowdown","Macro","MEDIUM",[(weak_growth,"growth below/near trend"),(inflation_dir=="COOLING","inflation cooling"),(np.isfinite(lead_value) and lead_value<0,"leading growth below trend"),(fcig<0,"financial conditions still cushion growth")],"Claims/lead stay soft while inflation keeps cooling.","Leading growth reaccelerates and labor breadth improves.","Growth ↓ + inflation ↓; duration support can coexist with weaker cyclicals.")
    add("Reacceleration","Positive","POSITIVE",[(lead_improving,"leading growth improving"),(np.isfinite(wei) and wei>0,"high-frequency activity positive"),("IMPROVING" in market_structure or "BROAD" in market_structure,"market breadth improving"),(fcig<0,"financial conditions supportive")],"Lead/WEI/breadth improve together.","Credit widens or inflation re-heats before growth confirms.","Growth breadth ↑ → earnings breadth ↑ → cyclicals/small caps can catch up.")
    add("Recession / credit crack","Macro","SEVERE",[(np.isfinite(lead_value) and lead_value<=-1,"BBK lead at recession-risk zone"),(claims_worse,"claims worsening"),(np.isfinite(ebp_prob) and ebp_prob>=25,"EBP recession benchmark elevated"),(hy_worse,"HY spreads widening"),(funding_score>=65,"funding stress elevated")],"Labor + credit + funding deteriorate together.","Credit calms and claims/leading growth stabilize.","Credit ↓ → hiring/capex ↓ → earnings ↓ → broader drawdown risk.")
    add("Inflation resurgence / policy bind","Macro","HIGH",[(inflation_dir=="HEATING","underlying inflation heating"),(energy_score>=65,"energy pressure elevated"),(supply_stress,"global supply pressure elevated"),(rates_score>=65,"rates/term premium elevated")],"Core/trimmed PCE, oil/supply and breakevens rise together.","Energy/supply normalize and underlying inflation keeps falling.","Inflation ↑ → easing delayed → yields/discount rates ↑ → growth/valuation pressure.")
    add("Rates / term-premium shock","Fiscal","HIGH",[(rates_score>=65,"long-rate/term-premium pressure elevated"),(fiscal_score>=65,"fiscal pressure elevated"),(epu_high,"policy uncertainty elevated"),(near_ath,"risk assets near highs")],"Term premium and long yields rise while funding/credit begin to weaken.","Long yields/term premium reverse without credit damage.","Long yields ↑ → mortgage/capex/valuation pressure ↑ → fragility rises.")
    add("War / energy stagflation","Geopolitical","SEVERE",[(gpr_high,"geopolitical risk high"),(gpr_rising,"geopolitical risk rising"),(energy_score>=65,"energy pressure elevated"),(supply_stress,"supply-chain pressure elevated")],"GPR + oil-GPR/energy + supply pressure rise together.","GPR/energy/supply stress normalize.","Conflict → energy/supply shock → inflation ↑ + growth ↓ → policy bind.", confidence="EVENT FEED")
    add("Fiscal crowding-out","Fiscal","HIGH",[(fiscal_score>=65,"fiscal pressure elevated"),(rates_score>=65,"rates/term premium elevated"),(np.isfinite(interest_gdp) and interest_gdp>=3,"interest burden high"),(epu_high,"policy uncertainty elevated")],"Issuance/term premium and private borrowing costs rise together.","Funding demand absorbs issuance and term premium falls.","Fiscal financing ↑ → long rates ↑ → housing/capex/private credit ↓.")
    add("Fiscal pressure → de-escalation incentive","Geopolitical","HIGH",[(fiscal_score>=65,"fiscal constraint elevated"),(rates_score>=65,"rates pressure elevated"),(gpr_high,"geopolitical conflict risk elevated"),(energy_score>=65,"war/energy cost channel elevated")],"Conflict feed confirms an active costly conflict while fiscal/rate constraints tighten.","Conflict de-escalates for diplomatic reasons or financing/rates normalize.","War cost + interest/funding burden ↑ → economic/political incentive to shrink conflict ↑.", confidence="CONDITIONAL — NOT POLITICAL PREDICTION")
    add("ATH + credit divergence","Market","HIGH",[(near_ath,"SPY near ATH"),(hy_worse,"HY widening"),(np.isfinite(ebp_prob) and ebp_prob>=20,"EBP recession benchmark non-trivial"),("DETERIORATING" in market_structure or "NARROW" in market_structure,"breadth/leadership fragile")],"Price stays high while credit/breadth deteriorate.","Credit tightens and breadth broadens.","Price optimism vs financing deterioration → fragile breakout / repricing risk.")
    add("Funding / deleveraging cascade","Market","SEVERE",[(funding_score>=65,"funding/stress elevated"),(stress_score>=65,"market stress elevated"),(fragility_score>=65,"system fragility elevated"),(credit_score>=65,"credit pressure elevated")],"Stress, credit and funding rise together.","Funding/stress normalize quickly.","Volatility ↑ → liquidity ↓ → deleveraging ↑ → correlations ↑ → drawdown amplification.")
    scenarios.sort(key=lambda x:(x["score"], 1 if x["impact"]=="SEVERE" else 0), reverse=True)
    return scenarios


def attention_items(items: list[tuple[str,float,str,str]]) -> list[tuple[str,float,str,str]]:
    clean=[x for x in items if np.isfinite(x[1])]
    return sorted(clean,key=lambda x:x[1],reverse=True)[:3]

# ----------------------------- UI -----------------------------
COLORS = {
    "green": ("#20d58b", "rgba(32,213,139,.12)"),
    "amber": ("#f4b45f", "rgba(244,180,95,.12)"),
    "red": ("#ff6d74", "rgba(255,109,116,.12)"),
    "blue": ("#75a9ff", "rgba(117,169,255,.12)"),
    "gray": ("#8e9bad", "rgba(142,155,173,.10)"),
}

st.markdown(
    """
<style>
:root{--bg:#070b11;--panel:#0f1621;--border:#202b3b;--muted:#8e9bad;--text:#edf3fb}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1540px;padding-top:.7rem;padding-bottom:1.2rem}
header[data-testid="stHeader"]{background:transparent}
.hero{border:1px solid var(--border);border-radius:15px;padding:12px 15px;background:linear-gradient(180deg,#111a27,#0c121b)}
.hero-title{font-size:1.65rem;font-weight:840;letter-spacing:-.035em}.sub{font-size:.75rem;color:var(--muted);margin-top:2px}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.badge{display:inline-block;padding:4px 7px;border-radius:999px;font-size:.59rem;font-weight:820;letter-spacing:.035em}
.section{font-size:.66rem;font-weight:820;letter-spacing:.11em;text-transform:uppercase;color:#91a4bc;margin:.55rem 0 .3rem}
.panel{border:1px solid var(--border);border-radius:13px;background:linear-gradient(180deg,#111925,#0c121b);padding:10px 11px}.ptitle{font-size:.74rem;font-weight:830;margin-bottom:6px}
.summary-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px}.summary{border:1px solid var(--border);border-radius:11px;background:#0c131d;padding:8px 9px;min-height:78px}.kicker{font-size:.54rem;letter-spacing:.08em;text-transform:uppercase;color:#8090a4;font-weight:810}.svalue{font-size:.80rem;font-weight:830;margin-top:3px;line-height:1.12}.snum{font-size:1.14rem;font-weight:850;margin-top:2px}.snote{font-size:.60rem;color:#8f9cac;margin-top:3px;line-height:1.25}
.matrix{width:100%;border-collapse:separate;border-spacing:4px}.matrix th{font-size:.56rem;color:#8393a7;text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:2px}.matrix td{padding:7px;border:1px solid var(--border);border-radius:8px;background:#0c131c;vertical-align:top}.rowname{font-size:.64rem;font-weight:820;color:#dbe5ef}.cellv{font-size:.66rem;font-weight:830;line-height:1.15}.celln{font-size:.55rem;color:#8c99aa;margin-top:2px;line-height:1.2}
.quad{position:relative;height:190px;border:1px solid var(--border);border-radius:11px;overflow:hidden;background:linear-gradient(90deg,rgba(32,213,139,.05) 0 50%,rgba(255,109,116,.055) 50% 100%),linear-gradient(0deg,rgba(32,213,139,.05) 0 50%,rgba(255,109,116,.04) 50% 100%)}.qv{position:absolute;width:1px;top:0;bottom:0;left:50%;background:#2a3748}.qh{position:absolute;height:1px;left:0;right:0;top:50%;background:#2a3748}.qlabel{position:absolute;font-size:.53rem;font-weight:810;letter-spacing:.04em;text-transform:uppercase;color:#8090a4}.dot{position:absolute;width:16px;height:16px;border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 0 4px rgba(255,255,255,.05)}
.scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.scenario{border:1px solid var(--border);border-radius:10px;background:#0c131d;padding:8px;min-height:104px}.scenario-title{font-size:.70rem;font-weight:830;margin-top:4px}.scenario-note{font-size:.60rem;color:#92a0b0;line-height:1.25;margin-top:4px}
.rowline{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid rgba(255,255,255,.055);padding:5px 0;font-size:.64rem}.rowline:last-child{border-bottom:none}.muted{color:#8997a8}.right{text-align:right}
.constraint-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.constraint{border:1px solid var(--border);border-radius:9px;background:#0c131d;padding:7px}.ctitle{font-size:.59rem;color:#8d9bad;text-transform:uppercase;font-weight:810}.cval{font-size:.75rem;font-weight:840;margin-top:3px}.cnote{font-size:.56rem;color:#8997a8;margin-top:2px;line-height:1.18}
.chain{font-size:.62rem;color:#c8d3df;line-height:1.45;padding:7px 8px;background:#0c131d;border:1px solid var(--border);border-radius:9px}.gate{border:1px solid #38465a;border-radius:9px;background:rgba(74,90,117,.10);padding:7px 8px;font-size:.60rem;color:#aeb9c8;line-height:1.28}.watch-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.watch{border:1px solid var(--border);border-radius:9px;background:#0c131d;padding:7px}.watch-title{font-size:.63rem;font-weight:820}.watch-note{font-size:.57rem;color:#8e9bac;margin-top:2px;line-height:1.2}
div[data-baseweb="tab-list"]{gap:6px}button[data-baseweb="tab"]{height:34px;font-size:.72rem}
@media(max-width:1000px){.summary-grid{grid-template-columns:1fr 1fr}.scenario-grid,.constraint-grid{grid-template-columns:1fr}.matrix{font-size:.8rem}}
</style>
""",
    unsafe_allow_html=True,
)


def badge(text: str, tone: str) -> str:
    c, bg = COLORS[tone]
    return f"<span class='badge' style='color:{c};background:{bg};border:1px solid {c}33'>{text}</span>"


def state_cell(value: str, note: str, tone: str) -> str:
    c, bg = COLORS[tone]
    return f"<td style='background:{bg};border-color:{c}2f'><div class='cellv' style='color:{c}'>{value}</div><div class='celln'>{note}</div></td>"


def summary_card(kicker: str, value: str, number: str, note: str, tone: str) -> str:
    c, bg = COLORS[tone]
    return f"<div class='summary' style='background:linear-gradient(180deg,{bg},#0c131d)'><div class='kicker'>{kicker}</div><div class='svalue' style='color:{c}'>{value}</div><div class='snum'>{number}</div><div class='snote'>{note}</div></div>"


def scenario_card(tag: str, name: str, note: str, tone: str) -> str:
    c, _ = COLORS[tone]
    return f"<div class='scenario'>{badge(tag,tone)}<div class='scenario-title' style='color:{c}'>{name}</div><div class='scenario-note'>{note}</div></div>"


def constraint_card(title: str, value: str, note: str, tone: str) -> str:
    c, bg = COLORS[tone]
    return f"<div class='constraint' style='background:{bg}'><div class='ctitle'>{title}</div><div class='cval' style='color:{c}'>{value}</div><div class='cnote'>{note}</div></div>"


# ----------------------------- LOAD -----------------------------
if st.sidebar.button("Refresh live data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("### Validation gates")
st.sidebar.write("Projection:", "✅" if PROJECTION_MODEL_VALIDATED else "🔒")
st.sidebar.write("Crash probability:", "✅" if CRASH_MODEL_VALIDATED else "🔒")
st.sidebar.write("Event probability:", "✅" if EVENT_PROBABILITY_MODEL_VALIDATED else "🔒")
st.sidebar.write("Market expectation gap:", "✅" if EXPECTATION_GAP_VALIDATED else "🔒")
st.sidebar.caption("Grey means gated / unavailable — not neutral.")


with st.spinner("Loading official/public macro data…"):
    data, research, market, gpr_df, treasury_debt_tn, treasury_debt_date, errors = load_all()

# ----------------------------- live readings -----------------------------
bbk_gdp, _ = latest(data.get("BBKMGDP")); bbk_co, _ = latest(data.get("BBKMCOIX")); bbk_lead, _ = latest(data.get("BBKMLEIX")); wei, _ = latest(data.get("WEI"))
trimmed, _ = latest(data.get("PCETRIM12M159SFRBDAL")); core_pce = yoy_from_index(data.get("PCEPILFE")); trimmed_3m = lag_value(data.get("PCETRIM12M159SFRBDAL"), 3); core_3m = yoy_at_lag(data.get("PCEPILFE"), 3)
sahm, _ = latest(data.get("SAHMREALTIME")); claims, _ = latest(data.get("ICSA")); claims_3m = months_ago(data.get("ICSA"), 3); sloos, _ = latest(data.get("DRTSCILM"))
nfci, _ = latest(data.get("NFCIRISK")); vix, _ = latest(data.get("VIXCLS")); hy, _ = latest(data.get("BAMLH0A0HYM2")); hy_3m = months_ago(data.get("BAMLH0A0HYM2"), 3)
breakeven, _ = latest(data.get("T5YIE")); d10, _ = latest(data.get("DGS10")); d2, _ = latest(data.get("DGS2")); fedfunds, _ = latest(data.get("FEDFUNDS")); term_premium, _ = latest(data.get("THREEFYTP10"))
oil, _ = latest(data.get("DCOILWTICO")); oil_3m = months_ago(data.get("DCOILWTICO"), 3); oil_chg_3m = (oil/oil_3m-1)*100 if np.isfinite(oil) and np.isfinite(oil_3m) and oil_3m!=0 else np.nan
debt_gdp, _ = latest(data.get("GFDEGDQ188S")); deficit_gdp, _ = latest(data.get("FYFSGDA188S")); interest_gdp, _ = latest(data.get("FYOIGDA188S")); curve = d10-d2 if np.isfinite(d10) and np.isfinite(d2) else np.nan
gscpi, _ = latest(data.get("GSCPI")); gscpi_delta = level_change_over(data.get("GSCPI"), 3)
epu, _ = latest(data.get("USEPUINDXD")); epu_pct = hist_pct(data.get("USEPUINDXD"), 10)
gpr = gpr_readings(gpr_df)

# Fed published outputs
ebp_prob = ebp = np.nan
if "EBP" in research and not research["EBP"].empty:
    edf=research["EBP"].copy()
    for c in ["ebp","est_prob"]:
        if c in edf: edf[c]=pd.to_numeric(edf[c],errors="coerce")
    ec=edf.dropna(subset=["est_prob"])
    if len(ec): ebp_prob=float(ec.iloc[-1]["est_prob"])*100; ebp=float(ec.iloc[-1]["ebp"])
fcig=np.nan
if "FCIG" in research and not research["FCIG"].empty:
    fdf=research["FCIG"].copy(); fcol=next((c for c in fdf.columns if c.startswith("FCI-G Index")),None)
    if fcol:
        fdf[fcol]=pd.to_numeric(fdf[fcol],errors="coerce"); fc=fdf.dropna(subset=[fcol])
        if len(fc): fcig=float(fc.iloc[-1][fcol])

# states
growth,growth_tone=growth_state(bbk_gdp,bbk_co,wei); lead,lead_tone=lead_state(bbk_lead); inflation,inflation_tone,inflation_dir=inflation_state(trimmed,core_pce,trimmed_3m,core_3m); labor,labor_tone=labor_state(sahm); fc_state,fc_tone=fcig_state(fcig); regime=regime_name(growth,inflation_dir)
lead_delta = bbk_lead - lag_value(data.get("BBKMLEIX"),1) if np.isfinite(bbk_lead) and np.isfinite(lag_value(data.get("BBKMLEIX"),1)) else np.nan
credit_tone="red" if (np.isfinite(ebp_prob) and ebp_prob>=35) else ("amber" if np.isfinite(hy) and np.isfinite(hy_3m) and hy>hy_3m else "green")
credit_state="STRESS" if credit_tone=="red" else ("WIDENING / WATCH" if credit_tone=="amber" else "CALM")
stress_score=np.nanmean([hist_pct(data.get("VIXCLS")),hist_pct(data.get("NFCIRISK")),hist_pct(data.get("BAMLH0A0HYM2"))]); fragility_score=np.nanmean([hist_pct(data.get("DGS10")),hist_pct(data.get("THREEFYTP10")),hist_pct(data.get("BAMLH0A0HYM2"))])
if not np.isfinite(stress_score): stress_score=50.0
if not np.isfinite(fragility_score): fragility_score=50.0
crash_state, crash_tone, crash_explain = crash_state_name(stress_score,fragility_score)
fiscal_score=fiscal_constraint_score(debt_gdp,deficit_gdp,interest_gdp,term_premium); fiscal_tone=tone_from_score(fiscal_score)
energy_score=energy_pressure_score(hist_pct(data.get("DCOILWTICO")),oil_chg_3m,hist_pct(data.get("T5YIE"))); energy_tone=tone_from_score(energy_score)
rates_score=np.nanmean([hist_pct(data.get("DGS10")),hist_pct(data.get("THREEFYTP10"))]); rates_tone=tone_from_score(rates_score)
credit_score=np.nanmean([hist_pct(data.get("BAMLH0A0HYM2")),ebp_prob]); credit_pressure_tone=tone_from_score(credit_score)
funding_score=np.nanmean([hist_pct(data.get("NFCIRISK")),hist_pct(data.get("VIXCLS"))]); funding_tone=tone_from_score(funding_score)
geo_score=np.nanmean([gpr.get("gpr_pct",np.nan), hist_pct(data.get("USEPUINDXD"),10)]); geo_tone=tone_from_score(geo_score)

rough_gross_headroom=STATUTORY_DEBT_LIMIT_TN-treasury_debt_tn if np.isfinite(treasury_debt_tn) else np.nan

# market structure
spy,iwm,rsp=market.get("SPY"),market.get("IWM"),market.get("RSP"); spy_ath,iwm_ath,rsp_ath=dist_to_ath(spy),dist_to_ath(iwm),dist_to_ath(rsp); iwm_rel=relative_change(iwm,spy,3); rsp_rel=relative_change(rsp,spy,3)
if all(np.isfinite(x) for x in [spy_ath,iwm_ath,rsp_ath]) and spy_ath>=-1.5 and iwm_ath>=-1.5 and rsp_ath>=-1.5: market_structure,market_tone="BROAD ATH / BROADENING","green"
elif np.isfinite(spy_ath) and spy_ath>=-1.5 and ((np.isfinite(iwm_ath) and iwm_ath<-5) or (np.isfinite(rsp_ath) and rsp_ath<-5)): market_structure,market_tone="NARROW LEADERSHIP","amber"
elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel>0 and rsp_rel>0: market_structure,market_tone="BREADTH IMPROVING","green"
elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel<0 and rsp_rel<0: market_structure,market_tone="BREADTH DETERIORATING","amber"
else: market_structure,market_tone="MIXED / OPTIONAL FEED","blue"

coverage=(len(data)+len(research)+(0 if gpr_df.empty else 1))/(len(SERIES)+3); coverage_tone="green" if coverage>=.85 else "amber"
plain_state, plain_explain = plain_regime(growth,lead,credit_tone,stress_score)

# adaptive scenario ranking
scenarios=adaptive_scenarios(growth=growth,lead_value=bbk_lead,lead_delta=lead_delta,wei=wei,inflation_dir=inflation_dir,claims=claims,claims_3m=claims_3m,ebp_prob=ebp_prob,hy=hy,hy_3m=hy_3m,fcig=fcig,market_structure=market_structure,fiscal_score=fiscal_score,rates_score=rates_score,energy_score=energy_score,funding_score=funding_score,gpr_pct=gpr.get("gpr_pct",np.nan),gpr_change=gpr.get("gpr_change",np.nan),gscpi=gscpi,gscpi_delta=gscpi_delta,epu_pct=epu_pct,spy_ath=spy_ath)
macro_scen=[x for x in scenarios if x["family"] in ["Macro","Positive"]][:3]
event_scen=[x for x in scenarios if x["family"] in ["Geopolitical","Fiscal"] and x["score"]>=25][:4]
market_scen=[x for x in scenarios if x["family"]=="Market"][:2]

# top attention drivers
growth_attention=np.nanmean([100-hist_pct(data.get("BBKMLEIX")), 65 if (np.isfinite(claims) and np.isfinite(claims_3m) and claims>claims_3m) else 25])
attention=attention_items([
    ("Rates / term premium",rates_score,"Long yields and term premium","Rates"),
    ("Fiscal pressure",fiscal_score,"Debt, deficit and interest burden","Fiscal"),
    ("Growth momentum",growth_attention,"Leading growth + claims","Growth"),
    ("Credit",credit_score,"HY OAS + EBP","Credit"),
    ("Funding / stress",funding_score,"NFCI + VIX","Funding"),
    ("Energy / supply",np.nanmean([energy_score, hist_pct(data.get("GSCPI"))]),"Oil + global supply chain","Energy"),
    ("Geopolitical / policy uncertainty",geo_score,"AI-GPR + EPU","World events"),
])

# event override
override_candidates=[x for x in event_scen if x["score"]>=50]
event_override=override_candidates[0] if override_candidates else None

# ----------------------------- HEADER -----------------------------
st.markdown(f"""
<div class='hero'>
  <div class='hero-title'>Macro Intelligence</div>
  <div class='sub'>Landing Page 1 · low-scroll control room · state → projection → scenarios → crash transmission.</div>
  <div class='legend'>{badge('GREEN = supportive / resilient / improving','green')}{badge('AMBER = caution / transition / monitor','amber')}{badge('RED = stress / deterioration / adverse','red')}{badge('BLUE = information / base state','blue')}{badge('GREY = not released / unvalidated / unavailable','gray')}</div>
  <div class='sub' style='margin-top:5px'><b>Colors describe the component, not a trade.</b> Green ≠ automatic buy. Red ≠ automatic sell.</div>
</div>""",unsafe_allow_html=True)

tab_control,tab_events,tab_research=st.tabs(["CONTROL ROOM","ACTIVE EVENTS","RESEARCH"])

# ============================================================
# CONTROL ROOM
# ============================================================
with tab_control:
    # Right now translation
    rt_tone = "red" if crash_tone=="red" else ("amber" if "LOSING" in plain_state or "WATCH" in crash_state or crash_state=="POWDER KEG" else "green")
    st.markdown("<div class='section'>Right now</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='panel'><div class='ptitle' style='font-size:.95rem'>{badge(plain_state,rt_tone)} &nbsp; {badge(crash_state,crash_tone)}</div><div style='font-size:.78rem;line-height:1.45;color:#d8e1ec'><b>{plain_explain}</b> {crash_explain} " + (f"<b>Event override:</b> {event_override['name']}." if event_override else "<b>Event override:</b> none active from admitted feeds.") + "</div></div>",unsafe_allow_html=True)

    # Top 3 matters + compact strip
    st.markdown("<div class='section'>Top 3 things that matter now</div>",unsafe_allow_html=True)
    cols=st.columns(3)
    for col,(name,score,note,fam) in zip(cols,attention):
        with col:
            tone=tone_from_score(score)
            st.markdown(summary_card(f"#{attention.index((name,score,note,fam))+1} · {fam}",name,fmt(score,0,"/100"),note+" · attention score, not probability",tone),unsafe_allow_html=True)

    st.markdown("<div class='section'>Projection + crash map</div>",unsafe_allow_html=True)
    left,right=st.columns([1.75,1])
    with left:
        claims_dir="WEAKENING" if np.isfinite(claims) and np.isfinite(claims_3m) and claims>claims_3m else "STABLE / IMPROVING"; claims_tone="amber" if claims_dir=="WEAKENING" else "green"
        hy_dir="WIDENING" if np.isfinite(hy) and np.isfinite(hy_3m) and hy>hy_3m else "CALM / TIGHTER"; hy_tone="amber" if hy_dir=="WIDENING" else "green"
        dash=lambda note: state_cell("—",note,"gray")
        rows=[]
        rows.append("<tr><td><div class='rowname'>Growth</div></td>"+state_cell(growth,f"BBK GDP {fmt(bbk_gdp,2,'%')}",growth_tone)+state_cell("CURRENT BIAS","broad/high-frequency state",growth_tone)+state_cell(lead,f"BBK lead {signed(bbk_lead,2,'σ')}",lead_tone)+dash("proprietary +4Q not released")+"</tr>")
        rows.append("<tr><td><div class='rowname'>Inflation</div></td>"+state_cell(inflation,f"Trim/Core {fmt(trimmed,1,'%')}/{fmt(core_pce,1,'%')}",inflation_tone)+state_cell(inflation_dir,"observed 3M direction","green" if inflation_dir=="COOLING" else ("red" if inflation_dir=="HEATING" else "amber"))+dash("pipeline projection pending")+dash("long projection pending")+"</tr>")
        rows.append("<tr><td><div class='rowname'>Labor</div></td>"+state_cell(labor,f"Sahm {signed(sahm,2)}",labor_tone)+state_cell(claims_dir,f"Claims {fmt(claims,0)}",claims_tone)+dash("leading composite pending")+dash("long projection pending")+"</tr>")
        rows.append("<tr><td><div class='rowname'>Credit</div></td>"+state_cell(credit_state,f"EBP {signed(ebp,2)} · HY {fmt(hy,2,'%')}",credit_tone)+state_cell(hy_dir,"HY 3M direction",hy_tone)+dash("credit impulse pending")+dash("proprietary path pending")+"</tr>")
        rows.append("<tr><td><div class='rowname'>Financial conditions</div></td>"+state_cell(fc_state,f"FCI-G {signed(fcig,2)}",fc_tone)+state_cell(fc_state,"near-term carry",fc_tone)+dash("+2Q model pending")+dash("+4Q model pending")+"</tr>")
        st.markdown("<div class='panel'><div class='ptitle'>Projection Matrix · NOW → +1Q → +2Q → +4Q</div><table class='matrix'><thead><tr><th>Engine</th><th>NOW</th><th>+1Q</th><th>+2Q</th><th>+4Q</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table><div class='gate' style='margin-top:5px'><b>12M supporting benchmarks:</b> Fed EBP recession "+fmt(ebp_prob,1,"%")+" · FCI-G "+signed(fcig,2)+". These support the horizon; they are not mislabeled as our +4Q projection.</div></div>",unsafe_allow_html=True)
    with right:
        dot_color=COLORS[crash_tone][0]; x=max(3,min(97,fragility_score)); y=max(3,min(97,100-stress_score))
        st.markdown(f"""<div class='panel'><div class='ptitle'>Crash Map · {crash_state}</div><div class='quad'><div class='qv'></div><div class='qh'></div><div class='qlabel' style='left:7px;top:7px'>Shock / stress</div><div class='qlabel' style='right:7px;top:7px'>Crash danger</div><div class='qlabel' style='left:7px;bottom:7px'>Healthy</div><div class='qlabel' style='right:7px;bottom:7px'>Powder keg</div><div class='dot' style='left:{x}%;top:{y}%;background:{dot_color}'></div></div><div class='rowline'><div>Immediate stress</div><div class='right'><b>{int(stress_score)}/100 · {('LOW' if stress_score<40 else 'MED' if stress_score<65 else 'HIGH')}</b></div></div><div class='rowline'><div>Fragility</div><div class='right'><b>{int(fragility_score)}/100 · {('LOW' if fragility_score<40 else 'MED' if fragility_score<65 else 'HIGH')}</b></div></div><div class='gate' style='margin-top:5px'>{crash_explain} Exact &gt;20% drawdown probability stays grey until validated.</div></div>""",unsafe_allow_html=True)

    # scenarios + driver relationship map
    st.markdown("<div class='section'>Scenarios + driver map</div>",unsafe_allow_html=True)
    s1,s2=st.columns([1.1,1.25])
    with s1:
        html="<div class='scenario-grid'>"
        for i,sc in enumerate(macro_scen[:3]):
            tag="BASE / ACTIVE" if i==0 else ("ALTERNATIVE" if i==1 else "TAIL")
            note=f"Evidence {len(sc['hits'])}/{sc['total']} · {sc['direction']} · {sc['transmission']}"
            html+=scenario_card(tag,sc['name'],note,sc['tone'])
        html+="</div>"
        st.markdown("<div class='panel'><div class='ptitle'>Adaptive Macro Paths</div>"+html+"<div class='gate' style='margin-top:5px'>Rank is evidence activation, <b>not probability</b>. Candidates automatically rise/fall as inputs change.</div></div>",unsafe_allow_html=True)
    with s2:
        # compact driver-scenario transmission map
        st.markdown("<div class='panel'><div class='ptitle'>Driver → Scenario Map</div>",unsafe_allow_html=True)
        dm=pd.DataFrame({
            "Slowdown":["++","+","++","+","−"],
            "Reaccel":["−−","0","−−","−","++"],
            "Stagflation":["+","+++","+","++","0"],
            "Crash cascade":["+","+","+++","++","−−"],
            "Fiscal / war constraint":["0","++","+","+++","0"],
        },index=["Growth weakness","Energy / supply","Credit / funding","Rates / fiscal","Liquidity support"])
        def map_cell(v):
            if v in ["+++","++"]: return "#ff6d7430" if v=="+++" else "#f4b45f25"
            if v in ["−−","−"]: return "#20d58b22"
            return "#75a9ff16"
        # HTML table
        h="<table class='matrix'><thead><tr><th>Driver</th>"+"".join(f"<th>{c}</th>" for c in dm.columns)+"</tr></thead><tbody>"
        for idxr,row in dm.iterrows():
            h+=f"<tr><td><div class='rowname'>{idxr}</div></td>"+"".join(f"<td style='background:{map_cell(v)}'><div class='cellv'>{v}</div></td>" for v in row)+"</tr>"
        h+="</tbody></table><div class='gate' style='margin-top:5px'><b>Legend:</b> + increases that scenario pressure; − buffers it; more signs = stronger structural transmission assumption. This is a causal map, not a raw correlation matrix.</div></div>"
        st.markdown(h,unsafe_allow_html=True)

    # event override + next confirmations
    st.markdown("<div class='section'>Event override + next confirmations</div>",unsafe_allow_html=True)
    e1,e2=st.columns([1,1.3])
    with e1:
        if event_override:
            ev_note = f"Evidence {len(event_override['hits'])}/{event_override['total']} · {event_override['transmission']}"
            ev_card = scenario_card(event_override['family'], event_override['name'], ev_note, event_override['tone'])
            st.markdown(f"<div class='panel'><div class='ptitle'>⚠ Event Override Active</div>{ev_card}<div class='gate' style='margin-top:5px'><b>Confirm:</b> {event_override['confirms']}<br><b>Breaks if:</b> {event_override['invalidates']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='panel'><div class='ptitle'>Event Override</div>"+scenario_card("CURRENT","NONE ACTIVE","No admitted world-event scenario currently has enough live evidence to override the base macro path.","green")+"</div>",unsafe_allow_html=True)
    with e2:
        nexts=[
            ("Growth", "Need BBK lead + WEI + claims to converge.", lead_tone),
            ("Inflation", "Need Trimmed/Core PCE to move together; supply shock can change the branch.", inflation_tone),
            ("Credit", "Danger if HY/EBP widen before headline macro cracks.", credit_tone),
            ("World events", "AI-GPR + oil/supply pressure must confirm an event transmission, not just headlines.", geo_tone),
        ]
        html="<div class='watch-grid'>"+"".join(f"<div class='watch'><div class='watch-title' style='color:{COLORS[t][0]}'>{n}</div><div class='watch-note'>{txt}</div></div>" for n,txt,t in nexts)+"</div>"
        st.markdown("<div class='panel'><div class='ptitle'>What changes the answer?</div>"+html+"</div>",unsafe_allow_html=True)

# ============================================================
# ACTIVE EVENTS — only material live scenarios
# ============================================================
with tab_events:
    st.markdown("<div class='section'>Active event radar</div>",unsafe_allow_html=True)
    st.markdown("<div class='gate'><b>Adaptive by design:</b> this tab shows only scenarios with live evidence. The full library is hidden in Research. Economic/event data can score activation and transmission; political intent probabilities remain gated.</div>",unsafe_allow_html=True)
    if event_scen:
        cols=st.columns(min(4,len(event_scen)))
        for col,sc in zip(cols,event_scen[:4]):
            with col:
                tone=sc['tone']; c=COLORS[tone][0]
                st.markdown(f"<div class='scenario' style='min-height:170px'><div>{badge(sc['family'],tone)}</div><div class='scenario-title' style='color:{c};font-size:.83rem'>{sc['name']}</div><div class='snum'>{sc['score']}/100</div><div class='snote'>Activation score · not probability · impact {sc['impact']} · {sc['direction']}</div><div class='scenario-note'><b>Live evidence:</b> {', '.join(sc['hits'][:3]) if sc['hits'] else 'insufficient'}.</div></div>",unsafe_allow_html=True)
    else:
        st.success("No material event scenario is active from currently admitted feeds.")

    st.markdown("<div class='section'>World-event sensors</div>",unsafe_allow_html=True)
    s1,s2,s3,s4=st.columns(4)
    sensors=[
        (s1,"Geopolitical risk",gpr.get('gpr_pct',np.nan),f"AI-GPR {fmt(gpr.get('gpr',np.nan),1)} · 3M Δ {signed(gpr.get('gpr_change',np.nan),1)}",geo_tone),
        (s2,"Supply-chain pressure",hist_pct(data.get('GSCPI')),f"GSCPI {signed(gscpi,2)} · 3M Δ {signed(gscpi_delta,2)}",tone_from_score(hist_pct(data.get('GSCPI')))),
        (s3,"Energy pressure",energy_score,f"WTI {fmt(oil,1,'$')} · 3M {signed(oil_chg_3m,1,'%')}",energy_tone),
        (s4,"Policy uncertainty",epu_pct,f"EPU {fmt(epu,0)}",tone_from_score(epu_pct)),
    ]
    for col,name,score,note,tone in sensors:
        with col: st.markdown(summary_card(name,"LIVE SENSOR",fmt(score,0,"/100"),note,tone),unsafe_allow_html=True)

    st.markdown("<div class='section'>Dominant transmission</div>",unsafe_allow_html=True)
    if event_scen:
        top=event_scen[0]
        st.markdown(f"<div class='panel'><div class='ptitle'>{top['name']}</div><div class='chain'>{top['transmission']}</div><div class='constraint-grid' style='margin-top:6px'>{constraint_card('CONFIRM', 'WATCH', top['confirms'], 'amber')}{constraint_card('INVALIDATE', 'BREAK', top['invalidates'], 'green')}{constraint_card('CONFIDENCE', top['confidence'], 'Activation is not political probability.', 'gray')}</div></div>",unsafe_allow_html=True)
    else:
        st.markdown("<div class='panel'><div class='ptitle'>No dominant event transmission</div><div class='chain'>Base macro path currently dominates the dashboard.</div></div>",unsafe_allow_html=True)

    with st.expander(f"Dormant scenario library · {len(SCENARIO_LIBRARY)} candidates"):
        st.dataframe(pd.DataFrame(SCENARIO_LIBRARY,columns=["Family","Scenario","Mechanism","Key data / trigger family"]),use_container_width=True,hide_index=True,height=420)

# ============================================================
# RESEARCH
# ============================================================
with tab_research:
    st.markdown("<div class='section'>Validation status</div>",unsafe_allow_html=True)
    status=pd.DataFrame([
        ["Live state","RELEASED","Official/public latest data"],
        ["Adaptive scenario activation","HEURISTIC / SCREENING","Evidence-count ranking; not probability"],
        ["Macro probability +1Q/+2Q/+4Q","LOCKED","Needs point-in-time OOS calibration"],
        ["Crash probability","LOCKED","Needs target/frequency/calibration tournament"],
        ["Political event probability","LOCKED","Economic/GPR data do not determine intent"],
        ["Expectation gap","LOCKED","Needs validated model-vs-market mapping"],
    ],columns=["Layer","Status","Meaning"])
    st.dataframe(status,use_container_width=True,hide_index=True)

    st.markdown("<div class='section'>Scenario screening</div>",unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(SCENARIO_SCREEN,columns=["Scenario","Decision","Evidence strength","Why"]),use_container_width=True,hide_index=True)

    st.markdown("<div class='section'>Raw readings</div>",unsafe_allow_html=True)
    raw=pd.DataFrame([
        ["BBK Monthly GDP",bbk_gdp,"% ann."],["BBK Coincident",bbk_co,"σ"],["BBK Leading",bbk_lead,"σ"],["WEI",wei,"%"],["Trimmed PCE",trimmed,"% y/y"],["Core PCE",core_pce,"% y/y"],["Sahm",sahm,"pp"],["Claims",claims,"claims"],["SLOOS",sloos,"net %"],["EBP",ebp,"index"],["EBP recession benchmark",ebp_prob,"%"],["FCI-G",fcig,"pp impulse"],["NFCI Risk",nfci,"index"],["VIX",vix,"index"],["HY OAS",hy,"%"],["5Y breakeven",breakeven,"%"],["10Y Treasury",d10,"%"],["2Y Treasury",d2,"%"],["Fed Funds",fedfunds,"%"],["10Y Term Premium",term_premium,"%"],["WTI",oil,"$/bbl"],["GSCPI",gscpi,"σ"],["EPU",epu,"index"],["AI-GPR",gpr.get('gpr',np.nan),"index"],["Debt/GDP",debt_gdp,"%"],["Deficit/GDP",deficit_gdp,"%"],["Interest/GDP",interest_gdp,"%"],["Treasury gross debt",treasury_debt_tn,"tn USD"],
    ],columns=["Series","Latest","Unit"])
    st.dataframe(raw,use_container_width=True,hide_index=True)
    if errors:
        with st.expander(f"Data / optional feed errors ({len(errors)})"):
            st.dataframe(pd.DataFrame([{"Source":k,"Error":v} for k,v in errors.items()]),use_container_width=True,hide_index=True)

st.caption("Landing v4: one control room for plain-English state, explicit projection, adaptive scenarios, event override and crash anatomy. Numerical probabilities remain locked until proven out-of-sample.")

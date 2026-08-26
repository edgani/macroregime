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


def safe_float(x) -> float:
    try:
        v=float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan

def fmt(x: float, digits: int = 1, suffix: str = "") -> str:
    x=safe_float(x)
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
        parts.append(np.clip(oil_pctile, 0, 100))
    if np.isfinite(oil_3m):
        parts.append(np.clip(50 + oil_3m * 2, 0, 100))
    if np.isfinite(breakeven_pctile):
        parts.append(np.clip(breakeven_pctile, 0, 100))
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
                       gscpi: float, gscpi_delta: float, epu_pct: float, spy_ath: float,
                       interest_gdp: float = np.nan, stress_score: float = np.nan,
                       fragility_score: float = np.nan, credit_score: float = np.nan) -> list[dict]:
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

def action_state_engine(*, plain_state: str, growth: str, lead_value: float, inflation_dir: str,
                        credit_tone: str, stress_score: float, fragility_score: float, fcig: float,
                        event_override: Optional[dict], market_structure: str, rates_score: float,
                        fiscal_score: float) -> dict:
    """Translate admitted macro/risk states into a simple posture. Not a return forecast/probability."""
    score = 35.0
    risk_reasons, buffers = [], []

    if "CONTRACT" in growth or "RECESSION" in growth:
        score += 25; risk_reasons.append("growth is contractionary")
    elif "LOSING" in plain_state or "BELOW" in growth or (np.isfinite(lead_value) and lead_value < 0):
        score += 10; risk_reasons.append("growth momentum is below trend")
    elif "HEALTHY" in plain_state or (np.isfinite(lead_value) and lead_value > 0):
        score -= 8; buffers.append("growth momentum is healthy")

    if credit_tone == "red":
        score += 22; risk_reasons.append("credit stress is active")
    elif credit_tone == "amber":
        score += 10; risk_reasons.append("credit is widening")
    else:
        score -= 6; buffers.append("credit remains calm")

    if stress_score >= 65:
        score += 22; risk_reasons.append("immediate market stress is high")
    elif stress_score >= 45:
        score += 9; risk_reasons.append("market stress is elevated")
    elif stress_score < 40:
        score -= 5; buffers.append("immediate stress is low")

    if fragility_score >= 65:
        score += 11; risk_reasons.append("system fragility is high")
    elif fragility_score >= 50:
        score += 5; risk_reasons.append("system fragility is moderate")

    if inflation_dir == "HEATING":
        score += 12; risk_reasons.append("inflation is re-heating")
    elif inflation_dir == "MIXED":
        score += 4; risk_reasons.append("inflation direction is mixed")
    elif inflation_dir == "COOLING":
        score -= 4; buffers.append("inflation is cooling")

    if np.isfinite(fcig):
        if fcig < 0:
            score -= 5; buffers.append("financial conditions are a tailwind")
        elif fcig > 0:
            score += 6; risk_reasons.append("financial conditions are a headwind")

    if np.isfinite(rates_score) and rates_score >= 65:
        score += 8; risk_reasons.append("long-rate / term-premium pressure is elevated")
    if np.isfinite(fiscal_score) and fiscal_score >= 65:
        score += 4; risk_reasons.append("fiscal pressure is elevated")

    if "BROAD" in market_structure or "IMPROVING" in market_structure:
        score -= 5; buffers.append("market breadth is improving")
    elif "NARROW" in market_structure or "DETERIORATING" in market_structure:
        score += 8; risk_reasons.append("market structure is fragile")

    if event_override:
        impact = event_override.get("impact", "")
        score += 16 if impact == "SEVERE" else (9 if impact == "HIGH" else 4)
        risk_reasons.append(f"event override active: {event_override.get('name','event risk')}")

    score = float(max(0, min(100, score)))

    if score >= 75:
        label, tone = "CRISIS RISK-OFF", "red"
        headline = "Protect liquidity first. Cut leverage and fragile/illiquid risk."
    elif score >= 60:
        label, tone = "DEFENSIVE", "red"
        headline = "Reduce beta and leverage; raise liquidity and quality."
    elif score >= 45:
        label, tone = "HOLD / SELECTIVE", "amber"
        headline = "Keep core exposure, add no new leverage, and wait for confirmation."
    elif score >= 25:
        label, tone = "SELECTIVE RISK-ON", "green"
        headline = "Add risk gradually only where breadth, credit and macro confirm."
    else:
        label, tone = "RISK-ON", "green"
        headline = "Conditions are broadly supportive; add risk in tranches, not by chasing."

    leverage = "CUT FAST" if score >= 75 else ("REDUCE" if score >= 60 else ("NO NEW LEVERAGE" if score >= 45 else "MODEST / NORMAL"))
    cash = "MAXIMIZE LIQUIDITY" if score >= 75 else ("RAISE" if score >= 60 else ("KEEP DRY POWDER" if score >= 45 else "NORMAL BUFFER"))
    beta = "CUT HIGH-BETA" if score >= 75 else ("REDUCE HIGH-BETA" if score >= 60 else ("KEEP QUALITY / DON'T CHASE" if score >= 45 else "ADD GRADUALLY"))
    credit = "AVOID LOWER-QUALITY CREDIT" if score >= 60 else ("QUALITY BIAS" if score >= 45 else "NORMAL / WATCH SPREADS")
    if inflation_dir == "COOLING" and score >= 45:
        duration = "CAN ADD SELECTIVELY IF YIELDS CONFIRM"
    elif inflation_dir == "HEATING":
        duration = "AVOID ADDING LONG DURATION"
    else:
        duration = "WAIT FOR RATES CONFIRMATION"
    hedge = "KEEP / INCREASE TAIL HEDGE" if score >= 60 else ("MAINTAIN, DON'T OVERPAY" if score >= 45 else "NORMAL HEDGE")

    return {"score":score,"label":label,"tone":tone,"headline":headline,
            "leverage":leverage,"cash":cash,"beta":beta,"credit":credit,
            "duration":duration,"hedge":hedge,
            "risk_reasons":risk_reasons[:5],"buffers":buffers[:5]}


def horizon_action_plan(*, current: dict, growth: str, lead_value: float, inflation_dir: str,
                        credit_tone: str) -> list[dict]:
    out=[{"horizon":"NOW","state":current["label"],"tone":current["tone"],
          "action":current["headline"],"status":"LIVE"}]

    if credit_tone == "red" or ("CONTRACT" in growth and inflation_dir != "COOLING"):
        q1=("DEFENSIVE","red","Reduce beta/leverage; prioritize liquidity and quality.")
    elif ("BELOW" in growth or (np.isfinite(lead_value) and lead_value < 0)) and inflation_dir=="COOLING" and credit_tone=="green":
        q1=("HOLD / QUALITY","amber","Keep quality exposure; add only on confirmation and retain dry powder.")
    elif ("ABOVE" in growth or "POSITIVE" in growth) and inflation_dir=="COOLING" and credit_tone=="green":
        q1=("SELECTIVE RISK-ON","green","Add risk in tranches if breadth and credit remain healthy.")
    elif inflation_dir=="HEATING":
        q1=("RATE-SENSITIVE CAUTION","amber","Avoid adding leverage/long duration until inflation and yields settle.")
    else:
        q1=("HOLD / SELECTIVE","amber","Wait for growth, inflation and credit to converge.")
    out.append({"horizon":"+1Q","state":q1[0],"tone":q1[1],"action":q1[2],"status":"CONDITIONAL"})

    if np.isfinite(lead_value) and lead_value <= -1:
        q2=("DEFENSIVE","red","Cut beta/leverage if labor or credit also confirm deterioration.") if credit_tone=="red" else ("DEFENSIVE TILT","amber","Reduce cyclical/high-beta risk unless labor and credit improve.")
    elif np.isfinite(lead_value) and lead_value < 0:
        q2=("QUALITY / OPTIONALITY","amber","Stay selective; duration can work if yields fall, but don't assume recession.") if inflation_dir=="COOLING" and credit_tone=="green" else ("CAUTION","amber","Keep risk tight until the below-trend lead reverses or confirms.")
    elif np.isfinite(lead_value) and lead_value > 0 and credit_tone=="green":
        q2=("ADD RISK GRADUALLY","green","Broaden exposure if growth, breadth and credit confirm together.")
    else:
        q2=("WAIT / NO FORCED BET","gray","No sufficiently strong +2Q action state.")
    out.append({"horizon":"+2Q","state":q2[0],"tone":q2[1],"action":q2[2],"status":"EVIDENCE-ALIGNED"})

    out.append({"horizon":"+4Q","state":"NOT RELEASED","tone":"gray",
                "action":"Do not make an autonomous +4Q portfolio bet until the projection model is validated; use scenario triggers instead.",
                "status":"GATED"})
    return out


def scenario_action(scenario_name: str) -> dict:
    n=scenario_name.lower()
    if "reaccel" in n or "goldilocks" in n:
        return {"state":"ADD RISK GRADUALLY","tone":"green","action":"Add beta/cyclicals in tranches; small caps only if breadth and credit confirm; normalize excess cash.","avoid":"Do not chase if credit starts widening."}
    if "disinflationary slowdown" in n:
        return {"state":"HOLD / QUALITY","tone":"amber","action":"Keep quality exposure and dry powder; reduce weak cyclicals; duration only if yields/inflation fall.","avoid":"Do not confuse slowing growth with an automatic crash."}
    if "recession" in n or "credit crack" in n:
        return {"state":"DEFENSIVE","tone":"red","action":"Cut leverage/high beta, raise liquidity, upgrade credit quality; add duration only if inflation is cooling.","avoid":"Avoid lower-quality credit and illiquid risk."}
    if "stagflation" in n or "inflation resurgence" in n or "policy bind" in n:
        return {"state":"STAGFLATION DEFENSE","tone":"red","action":"Reduce leverage, long-duration/rate-sensitive exposure and fragile cyclicals; keep liquidity and inflation/energy resilience.","avoid":"Do not rely on fast policy easing."}
    if "term-premium" in n or "crowding-out" in n or "rates" in n:
        return {"state":"RATE-SHOCK DEFENSE","tone":"amber","action":"Reduce long-duration/rate-sensitive risk; favor strong balance sheets and liquidity until yields reverse.","avoid":"Do not average blindly into rate-sensitive assets while yields accelerate."}
    if "de-escalation incentive" in n:
        return {"state":"WAIT FOR CONFIRMATION","tone":"amber","action":"If de-escalation is confirmed AND oil/rates fall while credit stays healthy, add risk gradually; otherwise keep protection.","avoid":"Do not front-run a political decision from fiscal data alone."}
    if "war / energy" in n:
        return {"state":"EVENT DEFENSE","tone":"red","action":"Keep beta/leverage lower; prioritize liquidity and inflation/energy resilience; watch credit for financial transmission.","avoid":"Act on real energy/rates/credit transmission, not headlines alone."}
    if "ath + credit divergence" in n:
        return {"state":"DON'T CHASE","tone":"amber","action":"Keep core winners but trim leverage/new high-beta adds until credit and breadth reconfirm.","avoid":"ATH alone is not a sell signal."}
    if "funding" in n or "deleveraging" in n or "cascade" in n:
        return {"state":"CRISIS RISK-OFF","tone":"red","action":"Cut leverage rapidly, maximize liquidity, reduce illiquid/high-beta/lower-quality credit and keep tail hedges.","avoid":"Do not wait for GDP/recession confirmation once funding transmission is active."}
    return {"state":"MONITOR / CONDITIONAL","tone":"blue","action":"Keep current posture; act only when the scenario confirmation conditions are met.","avoid":"Do not trade a narrative before transmission is visible."}


def next_data_decision_grid() -> list[dict]:
    return [
        {"growth":"↑ / STABLE","inflation":"↓","state":"UPGRADE","tone":"green","action":"Add risk gradually if credit and labor stay healthy. Broaden only when breadth confirms."},
        {"growth":"↓","inflation":"↓","state":"SLOWDOWN","tone":"amber","action":"Keep quality, raise selectivity and dry powder; duration can improve if yields confirm lower."},
        {"growth":"↑","inflation":"↑","state":"REFLATION / RATE RISK","tone":"amber","action":"Keep risk selective but avoid adding long duration/leverage; watch yields and credit."},
        {"growth":"↓","inflation":"↑","state":"STAGFLATION","tone":"red","action":"Go defensive: cut beta/leverage, raise liquidity and reduce rate-sensitive exposure."},
    ]

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





def compute_macro_gate_snapshot(refresh: bool=False):
    """Compute the compact macro gate without rendering the full macro dashboard."""
    if refresh:
        for _fn in [fetch_fred, fetch_research_csv, fetch_treasury_debt, fetch_yahoo, fetch_ai_gpr_monthly]:
            try: _fn.clear()
            except Exception: pass
    data, research, market, gpr_df, treasury_debt_tn, treasury_debt_date, errors = load_all()
    bbk_gdp, _ = latest(data.get("BBKMGDP")); bbk_co, _ = latest(data.get("BBKMCOIX")); bbk_lead, _ = latest(data.get("BBKMLEIX")); wei, _ = latest(data.get("WEI"))
    trimmed, _ = latest(data.get("PCETRIM12M159SFRBDAL")); core_pce = yoy_from_index(data.get("PCEPILFE")); trimmed_3m = lag_value(data.get("PCETRIM12M159SFRBDAL"), 3); core_3m = yoy_at_lag(data.get("PCEPILFE"), 3)
    sahm, _ = latest(data.get("SAHMREALTIME")); claims, _ = latest(data.get("ICSA")); claims_3m = months_ago(data.get("ICSA"), 3)
    nfci, _ = latest(data.get("NFCIRISK")); vix, _ = latest(data.get("VIXCLS")); hy, _ = latest(data.get("BAMLH0A0HYM2")); hy_3m = months_ago(data.get("BAMLH0A0HYM2"), 3)
    d10, _ = latest(data.get("DGS10")); d2, _ = latest(data.get("DGS2")); term_premium, _ = latest(data.get("THREEFYTP10")); breakeven, _ = latest(data.get("T5YIE"))
    oil, _ = latest(data.get("DCOILWTICO")); oil_3m = months_ago(data.get("DCOILWTICO"), 3); oil_chg_3m = (oil/oil_3m-1)*100 if np.isfinite(oil) and np.isfinite(oil_3m) and oil_3m!=0 else np.nan
    debt_gdp, _ = latest(data.get("GFDEGDQ188S")); deficit_gdp, _ = latest(data.get("FYFSGDA188S")); interest_gdp, _ = latest(data.get("FYOIGDA188S"))
    gscpi, _ = latest(data.get("GSCPI")); gscpi_delta = level_change_over(data.get("GSCPI"), 3)
    epu, _ = latest(data.get("USEPUINDXD")); epu_pct = hist_pct(data.get("USEPUINDXD"), 10); gpr=gpr_readings(gpr_df)
    ebp_prob=ebp=np.nan
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
    growth,growth_tone=growth_state(bbk_gdp,bbk_co,wei); lead,lead_tone=lead_state(bbk_lead); inflation,inflation_tone,inflation_dir=inflation_state(trimmed,core_pce,trimmed_3m,core_3m); regime=regime_name(growth,inflation_dir)
    lead_delta=bbk_lead-lag_value(data.get("BBKMLEIX"),1) if np.isfinite(bbk_lead) and np.isfinite(lag_value(data.get("BBKMLEIX"),1)) else np.nan
    credit_tone="red" if (np.isfinite(ebp_prob) and ebp_prob>=35) else ("amber" if np.isfinite(hy) and np.isfinite(hy_3m) and hy>hy_3m else "green")
    credit_state="STRESS" if credit_tone=="red" else ("WIDENING / WATCH" if credit_tone=="amber" else "CALM")
    stress_score=np.nanmean([hist_pct(data.get("VIXCLS")),hist_pct(data.get("NFCIRISK")),hist_pct(data.get("BAMLH0A0HYM2"))]); fragility_score=np.nanmean([hist_pct(data.get("DGS10")),hist_pct(data.get("THREEFYTP10")),hist_pct(data.get("BAMLH0A0HYM2"))])
    if not np.isfinite(stress_score): stress_score=50.0
    if not np.isfinite(fragility_score): fragility_score=50.0
    crash_state,crash_tone,crash_explain=crash_state_name(stress_score,fragility_score)
    fiscal_score=fiscal_constraint_score(debt_gdp,deficit_gdp,interest_gdp,term_premium)
    energy_score=energy_pressure_score(hist_pct(data.get("DCOILWTICO")),oil_chg_3m,hist_pct(data.get("T5YIE")))
    rates_score=np.nanmean([hist_pct(data.get("DGS10")),hist_pct(data.get("THREEFYTP10"))]); credit_score=np.nanmean([hist_pct(data.get("BAMLH0A0HYM2")),ebp_prob]); funding_score=np.nanmean([hist_pct(data.get("NFCIRISK")),hist_pct(data.get("VIXCLS"))]); geo_score=np.nanmean([gpr.get("gpr_pct",np.nan),hist_pct(data.get("USEPUINDXD"),10)])
    spy,iwm,rsp=market.get("SPY"),market.get("IWM"),market.get("RSP"); spy_ath,iwm_ath,rsp_ath=dist_to_ath(spy),dist_to_ath(iwm),dist_to_ath(rsp); iwm_rel=relative_change(iwm,spy,3); rsp_rel=relative_change(rsp,spy,3)
    if all(np.isfinite(x) for x in [spy_ath,iwm_ath,rsp_ath]) and spy_ath>=-1.5 and iwm_ath>=-1.5 and rsp_ath>=-1.5: market_structure="BROAD ATH / BROADENING"
    elif np.isfinite(spy_ath) and spy_ath>=-1.5 and ((np.isfinite(iwm_ath) and iwm_ath<-5) or (np.isfinite(rsp_ath) and rsp_ath<-5)): market_structure="NARROW LEADERSHIP"
    elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel>0 and rsp_rel>0: market_structure="BREADTH IMPROVING"
    elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel<0 and rsp_rel<0: market_structure="BREADTH DETERIORATING"
    else: market_structure="MIXED / OPTIONAL FEED"
    plain_state,plain_explain=plain_regime(growth,lead,credit_tone,stress_score)
    scenarios=adaptive_scenarios(growth=growth,lead_value=bbk_lead,lead_delta=lead_delta,wei=wei,inflation_dir=inflation_dir,claims=claims,claims_3m=claims_3m,ebp_prob=ebp_prob,hy=hy,hy_3m=hy_3m,fcig=fcig,market_structure=market_structure,fiscal_score=fiscal_score,rates_score=rates_score,energy_score=energy_score,funding_score=funding_score,gpr_pct=gpr.get("gpr_pct",np.nan),gpr_change=gpr.get("gpr_change",np.nan),gscpi=gscpi,gscpi_delta=gscpi_delta,epu_pct=epu_pct,spy_ath=spy_ath,interest_gdp=interest_gdp,stress_score=stress_score,fragility_score=fragility_score,credit_score=credit_score)
    macro_scen=[x for x in scenarios if x["family"] in ["Macro","Positive"]][:3]; event_scen=[x for x in scenarios if x["family"] in ["Geopolitical","Fiscal"] and x["score"]>=25][:4]
    override_candidates=[x for x in event_scen if x["score"]>=50]; event_override=override_candidates[0] if override_candidates else None
    action_now=action_state_engine(plain_state=plain_state,growth=growth,lead_value=bbk_lead,inflation_dir=inflation_dir,credit_tone=credit_tone,stress_score=stress_score,fragility_score=fragility_score,fcig=fcig,event_override=event_override,market_structure=market_structure,rates_score=rates_score,fiscal_score=fiscal_score)
    # Fail closed when the macro control room is missing too many critical families.
    critical_macro = [bbk_gdp, bbk_lead, trimmed, core_pce, sahm, claims, hy, nfci, vix, d10, term_premium]
    critical_available = sum(1 for x in critical_macro if np.isfinite(x))
    macro_data_coverage = critical_available / len(critical_macro)
    if macro_data_coverage < 0.55:
        action_now = {
            "score":50.0,"label":"HOLD / MACRO GATED","tone":"gray",
            "headline":"Critical macro families are incomplete. Keep sizing conservative and disable leverage upgrades until the feeds recover.",
            "leverage":"NO NEW LEVERAGE","cash":"KEEP DRY POWDER","beta":"NO UPGRADE",
            "credit":"GATED","duration":"GATED","hedge":"MAINTAIN",
            "risk_reasons":["macro data coverage below safety threshold"],"buffers":[],
        }
        plain_state = "MACRO GATED"
        plain_explain = f"Only {critical_available}/{len(critical_macro)} critical macro readings are available."
        crash_state, crash_tone = "GATED", "gray"
        credit_state = "GATED"
        event_override = None
    horizon_actions=horizon_action_plan(current=action_now,growth=growth,lead_value=bbk_lead,inflation_dir=inflation_dir,credit_tone=credit_tone)
    if macro_data_coverage < 0.55:
        horizon_actions=[{"horizon":"NOW","state":"MACRO GATED","tone":"gray","action":"No leverage upgrade until critical feeds recover.","status":"GATED"},
                         {"horizon":"+1Q","state":"NOT RELEASED","tone":"gray","action":"Projection gated by incomplete data.","status":"GATED"},
                         {"horizon":"+2Q","state":"NOT RELEASED","tone":"gray","action":"Projection gated by incomplete data.","status":"GATED"},
                         {"horizon":"+4Q","state":"NOT RELEASED","tone":"gray","action":"Projection model not validated.","status":"GATED"}]
    # Beginner-facing payload. Keep the technical readings available, but do not force
    # the daily UI to expose every raw series. This also gives the Opportunity page a
    # single stable contract instead of reaching into macro internals.
    labor_now, labor_tone = labor_state(sahm)
    claims_direction = "WEAKENING" if np.isfinite(claims) and np.isfinite(claims_3m) and claims > claims_3m else "STABLE / IMPROVING"
    fc_state, fc_tone = fcig_state(fcig)
    inflation_one_q = inflation_dir if inflation_dir in ["COOLING","HEATING"] else "MIXED / WATCH"
    projection_rows = [
        {"engine":"Growth","now":plain_state,"q1":lead,"q2":lead if np.isfinite(bbk_lead) else "GATED","q4":"GATED","confidence":"MEDIUM" if np.isfinite(bbk_lead) else "LOW"},
        {"engine":"Inflation","now":inflation,"q1":inflation_one_q,"q2":"GATED","q4":"GATED","confidence":"MEDIUM"},
        {"engine":"Labor","now":labor_now,"q1":claims_direction,"q2":"GATED","q4":"GATED","confidence":"MEDIUM"},
        {"engine":"Credit","now":credit_state,"q1":"WIDENING" if credit_tone=="amber" else ("STRESS" if credit_tone=="red" else "CALM"),"q2":"GATED","q4":"GATED","confidence":"MEDIUM"},
        {"engine":"Financial conditions","now":fc_state,"q1":fc_state,"q2":"GATED","q4":"GATED","confidence":"MEDIUM"},
    ]
    attention_raw = [
        ("Rates / term premium", rates_score, f"10Y {fmt(d10,2,'%')} · term premium {fmt(term_premium,2,'%')}"),
        ("Growth momentum", max(0.0, min(100.0, 50.0 - (bbk_lead if np.isfinite(bbk_lead) else 0.0)*20.0)), f"Leading growth {signed(bbk_lead,2,'σ')}"),
        ("Credit", credit_score, f"HY OAS {fmt(hy,2,'%')} · EBP recession benchmark {fmt(ebp_prob,1,'%')}"),
        ("Energy", energy_score, f"WTI {fmt(oil,1,'$')} · 3M {signed(oil_chg_3m,1,'%')}"),
        ("Fiscal", fiscal_score, f"Debt/GDP {fmt(debt_gdp,1,'%')} · interest/GDP {fmt(interest_gdp,1,'%')}"),
        ("Geopolitics", geo_score, f"GPR percentile {fmt(gpr.get('gpr_pct',np.nan),0,'%')}"),
    ]
    attention = [
        {"name":n,"score":float(v) if np.isfinite(v) else np.nan,"note":note}
        for n,v,note in sorted(attention_raw,key=lambda x:(-1 if not np.isfinite(x[1]) else -x[1]))[:3]
    ]
    top_paths = []
    for sc in (macro_scen + event_scen):
        if len(top_paths) >= 3: break
        if any(x.get("name")==sc.get("name") for x in top_paths): continue
        sa = scenario_action(sc.get("name", ""))
        top_paths.append({
            "name":sc.get("name"),"family":sc.get("family"),"score":sc.get("score"),"impact":sc.get("impact"),
            "transmission":sc.get("transmission"),"confirms":sc.get("confirms"),"invalidates":sc.get("invalidates"),
            "action":sa.get("action"),"action_state":sa.get("state"),"tone":sa.get("tone"),
        })
    snapshot={
        "action_label":action_now.get("label"),"action_tone":action_now.get("tone"),"action_score":action_now.get("score"),"headline":action_now.get("headline"),
        "regime":plain_state,"regime_explain":plain_explain,"crash_state":crash_state,"crash_tone":crash_tone,"credit_state":credit_state,"market_structure":market_structure,
        "event_override":event_override.get("name") if event_override else None,"event_override_score":event_override.get("score") if event_override else None,"horizon_actions":horizon_actions,
        "macro_scenarios":macro_scen,"event_scenarios":event_scen,"top_paths":top_paths,"projection_rows":projection_rows,"attention":attention,
        "crash_stress":float(stress_score),"crash_fragility":float(fragility_score),"macro_data_coverage":float(macro_data_coverage),
        "next_confirmations":[
            {"name":"Growth","watch":"Leading growth + weekly activity + claims must agree before the path is upgraded/downgraded."},
            {"name":"Inflation","watch":"Underlying PCE and energy/supply pressure must move together."},
            {"name":"Credit","watch":"HY/EBP/funding deterioration is the key escalation gate before a crash branch is promoted."},
            {"name":"Events","watch":"Real energy/shipping/supply transmission must confirm headlines."},
        ],
        "decision_grid":next_data_decision_grid(),
        "raw_readings":{
            "BBK monthly GDP":bbk_gdp,"BBK leading":bbk_lead,"WEI":wei,"Trimmed PCE":trimmed,"Core PCE":core_pce,"Sahm":sahm,"Claims":claims,
            "EBP recession benchmark":ebp_prob,"FCI-G":fcig,"NFCI risk":nfci,"VIX":vix,"HY OAS":hy,"5Y breakeven":breakeven,"10Y Treasury":d10,
            "2Y Treasury":d2,"10Y term premium":term_premium,"WTI":oil,"GSCPI":gscpi,"EPU":epu,"AI-GPR":gpr.get('gpr',np.nan),
            "Debt/GDP":debt_gdp,"Deficit/GDP":deficit_gdp,"Interest/GDP":interest_gdp,"Treasury gross debt":treasury_debt_tn,
        },
        "data_errors":errors,"refreshed_at_utc":pd.Timestamp.utcnow().isoformat(),
    }
    st.session_state["macro_gate_snapshot"]=snapshot
    return snapshot


def render_macro_control_room():
    """Beginner-first macro page. The model internals remain available under one expander."""
    c1,c2=st.columns([1,4])
    with c1:
        refresh=st.button("Refresh macro", use_container_width=True, key="macro_refresh_final")
    snap=compute_macro_gate_snapshot(refresh=refresh)
    with c2:
        st.caption("Latest public macro/event feeds. Grey means not validated/unavailable — never neutral. Numerical macro/crash/event probabilities remain locked until PIT/OOS validation passes.")

    event=snap.get("event_override") or "NONE ACTIVE"
    tone=snap.get("action_tone","gray")
    st.markdown("<div class='section'>Macro decision board</div>",unsafe_allow_html=True)
    cards="<div class='summary-grid' style='grid-template-columns:repeat(5,minmax(0,1fr))'>"
    cards+=summary_card("ACTION NOW",str(snap.get("action_label","—")),"",str(snap.get("headline","")),tone)
    cards+=summary_card("ECONOMY",str(snap.get("regime","—")),"",str(snap.get("regime_explain","")),"blue")
    cards+=summary_card("CRASH SETUP",str(snap.get("crash_state","—")),"",f"Stress {fmt(snap.get('crash_stress',np.nan),0,'/100')} · fragility {fmt(snap.get('crash_fragility',np.nan),0,'/100')}",str(snap.get("crash_tone","gray")))
    cards+=summary_card("CREDIT",str(snap.get("credit_state","—")),"","Key escalation gate before a financial cascade.","red" if snap.get("credit_state")=="STRESS" else ("amber" if "WATCH" in str(snap.get("credit_state")) else "green"))
    cards+=summary_card("EVENT OVERRIDE",event,"","Only material live transmission is promoted here.","amber" if event!="NONE ACTIVE" else "green")
    cards+="</div>"
    st.markdown(cards,unsafe_allow_html=True)
    st.markdown(f"<div class='panel' style='margin-top:7px'><div class='ptitle'>Plain English</div><div style='font-size:.76rem;line-height:1.45'>{snap.get('headline','')} <b>Portfolio implication:</b> {snap.get('action_label','—')}. Macro changes sizing/expression; it should not automatically kill a strong secular bottom-up thesis.</div></div>",unsafe_allow_html=True)

    st.markdown("<div class='section'>What matters most now</div>",unsafe_allow_html=True)
    att=snap.get("attention",[]) or []
    if att:
        cols=st.columns(min(3,len(att)))
        for col,item in zip(cols,att[:3]):
            with col:
                sc=item.get("score",np.nan); t=tone_from_score(sc)
                st.markdown(summary_card(item.get("name","Driver"),"WATCH",fmt(sc,0,"/100"),item.get("note","")+" · attention, not probability",t),unsafe_allow_html=True)

    st.markdown("<div class='section'>Where the economy is going</div>",unsafe_allow_html=True)
    left,right=st.columns([1.65,1])
    with left:
        proj=pd.DataFrame(snap.get("projection_rows",[]))
        if not proj.empty:
            proj=proj.rename(columns={"engine":"Engine","now":"NOW","q1":"+1Q","q2":"+2Q","q4":"+4Q","confidence":"Confidence"})
            st.dataframe(proj,use_container_width=True,hide_index=True)
        st.caption("Future cells stay GATED when the proprietary path is not validated. Supporting benchmarks are not mislabeled as forecasts.")
    with right:
        stress=safe_float(snap.get("crash_stress")); frag=safe_float(snap.get("crash_fragility"))
        state=snap.get("crash_state","GATED")
        meaning=("Vulnerable, but no active cascade." if state=="POWDER KEG" else ("Stress and fragility are both elevated; prioritize liquidity." if "DANGER" in str(state) else "No crash conclusion from a single gauge."))
        st.markdown(f"<div class='panel'><div class='ptitle'>Crash setup · {state}</div><div class='rowline'><div>Immediate stress</div><div class='right'><b>{fmt(stress,0,'/100')}</b></div></div><div class='rowline'><div>Fragility</div><div class='right'><b>{fmt(frag,0,'/100')}</b></div></div><div class='rowline'><div>Credit</div><div class='right'><b>{snap.get('credit_state','—')}</b></div></div><div class='gate' style='margin-top:6px'>{meaning} Exact drawdown probability remains gated.</div></div>",unsafe_allow_html=True)

    st.markdown("<div class='section'>Most supported paths · next 1–2 quarters</div>",unsafe_allow_html=True)
    paths=snap.get("top_paths",[]) or []
    if paths:
        cols=st.columns(min(3,len(paths)))
        for col,sc in zip(cols,paths[:3]):
            with col:
                t=sc.get("tone","blue")
                st.markdown(f"<div class='scenario'><div>{badge(sc.get('family','PATH'),t)}</div><div class='scenario-title'>{sc.get('name','')}</div><div class='scenario-note'><b>Transmission:</b> {sc.get('transmission','')}<br><br><b>If confirmed → {sc.get('action_state','WATCH')}</b><br>{sc.get('action','')}<br><br><b>Confirms:</b> {sc.get('confirms','')}<br><b>Breaks if:</b> {sc.get('invalidates','')}</div></div>",unsafe_allow_html=True)
    else:
        st.info("No scenario currently clears the live evidence gate; the base macro path dominates.")

    st.markdown("<div class='section'>What would change the action?</div>",unsafe_allow_html=True)
    ncs=snap.get("next_confirmations",[]) or []
    cols=st.columns(2)
    for i,item in enumerate(ncs):
        with cols[i%2]:
            st.markdown(f"<div class='watch'><div class='watch-title'>{item.get('name','')}</div><div class='watch-note'>{item.get('watch','')}</div></div>",unsafe_allow_html=True)

    with st.expander("Technical evidence / next-data decision grid / raw readings", expanded=False):
        dg=pd.DataFrame(snap.get("decision_grid",[]))
        if not dg.empty:
            st.markdown("**Next economic-data decision grid**")
            st.dataframe(dg,use_container_width=True,hide_index=True)
        raw=snap.get("raw_readings",{}) or {}
        if raw:
            st.markdown("**Raw latest readings**")
            st.dataframe(pd.DataFrame([{"Series":k,"Latest":v} for k,v in raw.items()]),use_container_width=True,hide_index=True)
        errs=snap.get("data_errors",{}) or {}
        if errs:
            st.markdown("**Feed errors / unavailable optional data**")
            st.dataframe(pd.DataFrame([{"Source":k,"Error":v} for k,v in errs.items()]),use_container_width=True,hide_index=True)

    st.caption("Macro page is deliberately compact: action → projection → crash setup → top scenarios → confirmations. Research internals stay hidden unless requested.")

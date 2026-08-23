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
    return data, research, market, debt_now, debt_date, errors


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
    data, research, market, treasury_debt_tn, treasury_debt_date, errors = load_all()

# Current readings
bbk_gdp, _ = latest(data.get("BBKMGDP"))
bbk_co, _ = latest(data.get("BBKMCOIX"))
bbk_lead, _ = latest(data.get("BBKMLEIX"))
wei, _ = latest(data.get("WEI"))
trimmed, _ = latest(data.get("PCETRIM12M159SFRBDAL"))
core_pce = yoy_from_index(data.get("PCEPILFE"))
trimmed_3m = lag_value(data.get("PCETRIM12M159SFRBDAL"), 3)
core_3m = yoy_at_lag(data.get("PCEPILFE"), 3)
sahm, _ = latest(data.get("SAHMREALTIME"))
claims, _ = latest(data.get("ICSA"))
claims_3m = months_ago(data.get("ICSA"), 3)
sloos, _ = latest(data.get("DRTSCILM"))
nfci, _ = latest(data.get("NFCIRISK"))
vix, _ = latest(data.get("VIXCLS"))
hy, _ = latest(data.get("BAMLH0A0HYM2"))
hy_3m = months_ago(data.get("BAMLH0A0HYM2"), 3)
breakeven, _ = latest(data.get("T5YIE"))
d10, _ = latest(data.get("DGS10"))
d2, _ = latest(data.get("DGS2"))
fedfunds, _ = latest(data.get("FEDFUNDS"))
term_premium, _ = latest(data.get("THREEFYTP10"))
oil, _ = latest(data.get("DCOILWTICO"))
oil_3m = months_ago(data.get("DCOILWTICO"), 3)
oil_chg_3m = (oil / oil_3m - 1) * 100 if np.isfinite(oil) and np.isfinite(oil_3m) and oil_3m != 0 else np.nan
debt_gdp, _ = latest(data.get("GFDEGDQ188S"))
deficit_gdp, _ = latest(data.get("FYFSGDA188S"))
interest_gdp, _ = latest(data.get("FYOIGDA188S"))
curve = d10 - d2 if np.isfinite(d10) and np.isfinite(d2) else np.nan

# Fed published model outputs
ebp_prob = ebp = np.nan
if "EBP" in research and not research["EBP"].empty:
    edf = research["EBP"].copy()
    for c in ["ebp", "est_prob"]:
        if c in edf:
            edf[c] = pd.to_numeric(edf[c], errors="coerce")
    ec = edf.dropna(subset=["est_prob"])
    if len(ec):
        ebp_prob = float(ec.iloc[-1]["est_prob"]) * 100
        ebp = float(ec.iloc[-1]["ebp"])

fcig = np.nan
if "FCIG" in research and not research["FCIG"].empty:
    fdf = research["FCIG"].copy()
    fcol = next((c for c in fdf.columns if c.startswith("FCI-G Index")), None)
    if fcol:
        fdf[fcol] = pd.to_numeric(fdf[fcol], errors="coerce")
        fc = fdf.dropna(subset=[fcol])
        if len(fc):
            fcig = float(fc.iloc[-1][fcol])

# States
growth, growth_tone = growth_state(bbk_gdp, bbk_co, wei)
lead, lead_tone = lead_state(bbk_lead)
inflation, inflation_tone, inflation_dir = inflation_state(trimmed, core_pce, trimmed_3m, core_3m)
labor, labor_tone = labor_state(sahm)
fc_state, fc_tone = fcig_state(fcig)
regime = regime_name(growth, inflation_dir)
credit_tone = "red" if (np.isfinite(ebp_prob) and ebp_prob >= 35) else ("amber" if np.isfinite(hy) and np.isfinite(hy_3m) and hy > hy_3m else "green")
credit_state = "STRESS" if credit_tone == "red" else ("WIDENING / WATCH" if credit_tone == "amber" else "CALM")
stress_score = np.nanmean([hist_pct(data.get("VIXCLS")), hist_pct(data.get("NFCIRISK")), hist_pct(data.get("BAMLH0A0HYM2"))])
fragility_score = np.nanmean([hist_pct(data.get("DGS10")), hist_pct(data.get("THREEFYTP10")), hist_pct(data.get("BAMLH0A0HYM2"))])
if not np.isfinite(stress_score): stress_score = 50.0
if not np.isfinite(fragility_score): fragility_score = 50.0

# Fiscal / event constraint scores
fiscal_score = fiscal_constraint_score(debt_gdp, deficit_gdp, interest_gdp, term_premium)
fiscal_tone = tone_from_score(fiscal_score)
energy_score = energy_pressure_score(hist_pct(data.get("DCOILWTICO")), oil_chg_3m, hist_pct(data.get("T5YIE")))
energy_tone = tone_from_score(energy_score)
rates_score = np.nanmean([hist_pct(data.get("DGS10")), hist_pct(data.get("THREEFYTP10"))])
rates_tone = tone_from_score(rates_score)
credit_score = np.nanmean([hist_pct(data.get("BAMLH0A0HYM2")), ebp_prob])
credit_score = float(credit_score) if np.isfinite(credit_score) else np.nan
credit_pressure_tone = tone_from_score(credit_score)
funding_score = np.nanmean([hist_pct(data.get("NFCIRISK")), hist_pct(data.get("VIXCLS"))])
funding_tone = tone_from_score(funding_score)

# Debt limit context: gross debt is not debt-subject-to-limit; show as context only.
rough_gross_headroom = STATUTORY_DEBT_LIMIT_TN - treasury_debt_tn if np.isfinite(treasury_debt_tn) else np.nan
rough_headroom_pct = rough_gross_headroom / STATUTORY_DEBT_LIMIT_TN * 100 if np.isfinite(rough_gross_headroom) else np.nan

# Optional market structure
spy, iwm, rsp = market.get("SPY"), market.get("IWM"), market.get("RSP")
spy_ath, iwm_ath, rsp_ath = dist_to_ath(spy), dist_to_ath(iwm), dist_to_ath(rsp)
iwm_rel = relative_change(iwm, spy, 3)
rsp_rel = relative_change(rsp, spy, 3)
if all(np.isfinite(x) for x in [spy_ath, iwm_ath, rsp_ath]) and spy_ath >= -1.5 and iwm_ath >= -1.5 and rsp_ath >= -1.5:
    market_structure, market_tone = "BROAD ATH / BROADENING", "green"
elif np.isfinite(spy_ath) and spy_ath >= -1.5 and ((np.isfinite(iwm_ath) and iwm_ath < -5) or (np.isfinite(rsp_ath) and rsp_ath < -5)):
    market_structure, market_tone = "NARROW LEADERSHIP", "amber"
elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel > 0 and rsp_rel > 0:
    market_structure, market_tone = "BREADTH IMPROVING", "green"
elif np.isfinite(iwm_rel) and np.isfinite(rsp_rel) and iwm_rel < 0 and rsp_rel < 0:
    market_structure, market_tone = "BREADTH DETERIORATING", "amber"
else:
    market_structure, market_tone = "MIXED / OPTIONAL FEED", "blue"

coverage = (len(data) + len(research)) / (len(SERIES) + 2)
coverage_tone = "green" if coverage >= .85 else "amber"

# ----------------------------- HEADER -----------------------------
st.markdown(
    f"""
<div class='hero'>
  <div class='hero-title'>Macro Intelligence</div>
  <div class='sub'>Landing Page 1 · compact control room · macro projection + crash anatomy + world/event scenario constraints.</div>
  <div class='legend'>
    {badge('GREEN = supportive / resilient / improving','green')}
    {badge('AMBER = caution / transition / monitor','amber')}
    {badge('RED = stress / deterioration / adverse','red')}
    {badge('BLUE = information / base state','blue')}
    {badge('GREY = gated / not validated / unavailable','gray')}
  </div>
  <div class='sub' style='margin-top:6px'><b>Colors describe each component.</b> Green is not automatically BUY; red is not automatically SELL.</div>
</div>
""",
    unsafe_allow_html=True,
)

# Tabs keep page low-scroll.
tab_control, tab_world, tab_research = st.tabs(["CONTROL ROOM", "WORLD / EVENT SCENARIOS", "RESEARCH / RAW"])

# ============================================================
# TAB 1 — CONTROL ROOM
# ============================================================
with tab_control:
    st.markdown("<div class='section'>Control strip</div>", unsafe_allow_html=True)
    html = "<div class='summary-grid'>"
    html += summary_card("Current regime", regime, "", f"Growth {growth.lower()} · inflation {inflation_dir.lower()}", "blue")
    html += summary_card("Growth lead", lead, signed(bbk_lead,2,"σ"), "Main medium-horizon anchor", lead_tone)
    html += summary_card("Market structure", market_structure, "", "ATH is context; breadth/credit decide whether it is healthy or fragile", market_tone)
    html += summary_card("Crash state", "STRESS × FRAGILITY", f"{int(stress_score)}/{int(fragility_score)}", "State map only; exact crash probability remains gated", tone_from_score(max(stress_score, fragility_score)))
    html += summary_card("Fiscal constraint", "PRESSURE", fmt(fiscal_score,0,"/100"), f"Debt/deficit/interest/term-premium context", fiscal_tone)
    html += summary_card("Data health", "LIVE", f"{coverage:.0%}", "Latest state; point-in-time backtest is separate", coverage_tone)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("<div class='section'>Projection + crash map</div>", unsafe_allow_html=True)
    left, right = st.columns([1.75, 1])
    with left:
        claims_dir = "WEAKENING" if np.isfinite(claims) and np.isfinite(claims_3m) and claims > claims_3m else "STABLE / IMPROVING"
        claims_tone = "amber" if claims_dir == "WEAKENING" else "green"
        hy_dir = "WIDENING" if np.isfinite(hy) and np.isfinite(hy_3m) and hy > hy_3m else "CALM / TIGHTER"
        hy_tone = "amber" if hy_dir == "WIDENING" else "green"
        rows = []
        rows.append("<tr><td><div class='rowname'>Growth</div></td>" + state_cell(growth, f"BBK GDP {fmt(bbk_gdp,2,'%')}", growth_tone) + state_cell("CURRENT BIAS", "near-term broad state", growth_tone) + state_cell(lead, f"BBK lead {signed(bbk_lead,2,'σ')}", lead_tone) + state_cell("12M BENCHMARK", f"EBP recession {fmt(ebp_prob,1,'%')}", "amber" if ebp_prob >= 20 else "green") + "</tr>")
        rows.append("<tr><td><div class='rowname'>Inflation</div></td>" + state_cell(inflation, f"Trim/Core {fmt(trimmed,1,'%')}/{fmt(core_pce,1,'%')}", inflation_tone) + state_cell(inflation_dir, "observed direction", "green" if inflation_dir == "COOLING" else ("red" if inflation_dir == "HEATING" else "amber")) + state_cell("GATED", "pipeline model pending", "gray") + state_cell("GATED", "longer projection pending", "gray") + "</tr>")
        rows.append("<tr><td><div class='rowname'>Labor</div></td>" + state_cell(labor, f"Sahm {signed(sahm,2)}", labor_tone) + state_cell(claims_dir, f"Claims {fmt(claims,0)}", claims_tone) + state_cell("GATED", "leading labor composite pending", "gray") + state_cell("GATED", "long horizon pending", "gray") + "</tr>")
        rows.append("<tr><td><div class='rowname'>Credit</div></td>" + state_cell(credit_state, f"EBP {signed(ebp,2)} · HY {fmt(hy,2,'%')}", credit_tone) + state_cell(hy_dir, "HY OAS 3M direction", hy_tone) + state_cell("GATED", "credit impulse model pending", "gray") + state_cell("EBP CONTEXT", f"12M recession {fmt(ebp_prob,1,'%')}", "amber" if ebp_prob >= 20 else "green") + "</tr>")
        rows.append("<tr><td><div class='rowname'>Financial conditions</div></td>" + state_cell(fc_state, f"FCI-G {signed(fcig,2)}", fc_tone) + state_cell(fc_state, "current conditions carry near-term", fc_tone) + state_cell("GATED", "no invented +2Q path", "gray") + state_cell(fc_state, "published 12M impulse", fc_tone) + "</tr>")
        rows.append("<tr><td><div class='rowname'>Fiscal pressure</div></td>" + state_cell("ELEVATED" if fiscal_score >= 65 else ("WATCH" if fiscal_score >= 40 else "LOW"), f"Debt/GDP {fmt(debt_gdp,1,'%')}", fiscal_tone) + state_cell("WATCH", f"10Y {fmt(d10,2,'%')} · TP {fmt(term_premium,2,'%')}", rates_tone) + state_cell("GATED", "fiscal-path model pending", "gray") + state_cell("STRUCTURAL", f"Interest/GDP {fmt(interest_gdp,2,'%')}", fiscal_tone) + "</tr>")
        st.markdown("<div class='panel'><div class='ptitle'>Projection Matrix · NOW → +1Q → +2Q → +4Q</div><table class='matrix'><thead><tr><th>Engine</th><th>NOW</th><th>+1Q</th><th>+2Q</th><th>+4Q</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>", unsafe_allow_html=True)

    with right:
        dot_tone = tone_from_score(max(stress_score, fragility_score))
        dot_color = COLORS[dot_tone][0]
        x = max(3, min(97, fragility_score)); y = max(3, min(97, 100 - stress_score))
        st.markdown(f"""
<div class='panel'><div class='ptitle'>Crash Map · Fragility × Immediate Stress</div>
<div class='quad'><div class='qv'></div><div class='qh'></div>
<div class='qlabel' style='left:7px;top:7px'>Shock / stress</div><div class='qlabel' style='right:7px;top:7px'>Crash danger</div>
<div class='qlabel' style='left:7px;bottom:7px'>Healthy</div><div class='qlabel' style='right:7px;bottom:7px'>Powder keg</div>
<div class='dot' style='left:{x}%;top:{y}%;background:{dot_color}'></div></div>
<div class='rowline'><div class='muted'>Immediate stress</div><div class='right'><b>{int(stress_score)}/100</b></div></div>
<div class='rowline'><div class='muted'>Fragility proxy</div><div class='right'><b>{int(fragility_score)}/100</b></div></div>
<div class='rowline'><div class='muted'>Exact &gt;20% crash probability</div><div class='right'>{badge('GATED','gray')}</div></div>
<div class='gate' style='margin-top:6px'>Low stress + high fragility = vulnerable but not imminent. High stress + high fragility = dangerous. This is a state map, not a crash-probability model.</div></div>
""", unsafe_allow_html=True)

    st.markdown("<div class='section'>Macro scenarios + constraint map</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.25, 1])
    with c1:
        alt = "REACCELERATION" if regime != "GOLDILOCKS / DISINFLATION" else "SLOWDOWN"
        sc = "<div class='scenario-grid'>"
        sc += scenario_card("BASE", regime, "Best current description. Numerical probability stays gated until projection OOS validation.", "blue")
        sc += scenario_card("ALTERNATIVE", alt, "Requires a clear turn in leading growth, breadth, credit and inflation consistency.", "green")
        sc += scenario_card("TAIL", "GROWTH / CREDIT CRACK", "Labor + credit deterioration must reinforce each other; one headline alone is insufficient.", "red")
        sc += "</div>"
        st.markdown("<div class='panel'><div class='ptitle'>Top Macro Paths</div>" + sc + "</div>", unsafe_allow_html=True)
    with c2:
        constraints = "<div class='constraint-grid'>"
        constraints += constraint_card("Fiscal", "ELEVATED" if fiscal_score >= 65 else ("WATCH" if fiscal_score >= 40 else "LOW"), f"Debt/GDP {fmt(debt_gdp,1,'%')} · deficit {fmt(deficit_gdp,1,'%')}", fiscal_tone)
        constraints += constraint_card("Rates / term premium", "ELEVATED" if rates_score >= 65 else ("WATCH" if rates_score >= 40 else "LOW"), f"10Y {fmt(d10,2,'%')} · TP {fmt(term_premium,2,'%')}", rates_tone)
        constraints += constraint_card("Energy", "ELEVATED" if energy_score >= 65 else ("WATCH" if energy_score >= 40 else "LOW"), f"WTI {fmt(oil,1,'$')} · 3M {signed(oil_chg_3m,1,'%')}", energy_tone)
        constraints += constraint_card("Credit", "ELEVATED" if credit_score >= 65 else ("WATCH" if credit_score >= 40 else "LOW"), f"HY {fmt(hy,2,'%')} · EBP rec. {fmt(ebp_prob,1,'%')}", credit_pressure_tone)
        constraints += constraint_card("Funding / stress", "ELEVATED" if funding_score >= 65 else ("WATCH" if funding_score >= 40 else "LOW"), f"NFCI {signed(nfci,2)} · VIX {fmt(vix,1)}", funding_tone)
        constraints += constraint_card("Geopolitical choice", "GATED", "Economic data can constrain choices; it cannot determine political intent alone.", "gray")
        constraints += "</div>"
        st.markdown("<div class='panel'><div class='ptitle'>Constraint Map</div>" + constraints + "</div>", unsafe_allow_html=True)

    st.markdown("<div class='section'>What changes the answer?</div>", unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1:
        st.markdown("<div class='panel'><div class='ptitle'>Confirmation / invalidation</div><div class='watch-grid'>" +
                    "<div class='watch'><div class='watch-title'>Growth</div><div class='watch-note'>BBK Leading + WEI + claims must converge before the path gets upgraded/downgraded.</div></div>" +
                    "<div class='watch'><div class='watch-title'>Inflation</div><div class='watch-note'>Cooling must persist; re-heating changes the policy/fiscal branch.</div></div>" +
                    "<div class='watch'><div class='watch-title'>Credit</div><div class='watch-note'>Watch EBP/HY widening before headline macro cracks.</div></div>" +
                    "<div class='watch'><div class='watch-title'>Market structure</div><div class='watch-note'>ATH is not bearish by itself; breadth + credit decide whether it is healthy or fragile.</div></div></div></div>", unsafe_allow_html=True)
    with w2:
        st.markdown(f"""
<div class='panel'><div class='ptitle'>Market Pricing · compact</div>
<div class='rowline'><div>5Y breakeven<div class='muted'>market inflation pricing</div></div><div class='right'><b>{fmt(breakeven,2,'%')}</b></div></div>
<div class='rowline'><div>10Y Treasury<div class='muted'>long-end pressure</div></div><div class='right'><b>{fmt(d10,2,'%')}</b></div></div>
<div class='rowline'><div>2Y Treasury<div class='muted'>front-end context</div></div><div class='right'><b>{fmt(d2,2,'%')}</b></div></div>
<div class='rowline'><div>Fed funds<div class='muted'>policy anchor</div></div><div class='right'><b>{fmt(fedfunds,2,'%')}</b></div></div>
<div class='gate' style='margin-top:6px'>{badge('EXPECTATION GAP GATED','gray')} No “market is wrong” call until mapping is validated.</div></div>
""", unsafe_allow_html=True)

# ============================================================
# TAB 2 — WORLD / EVENT SCENARIOS
# ============================================================
with tab_world:
    st.markdown("<div class='section'>World / event scenario engine</div>", unsafe_allow_html=True)
    st.markdown("<div class='gate'><b>Key rule:</b> economic data can tell us whether a scenario is becoming easier/harder to sustain and how it would transmit. It cannot, by itself, tell us that a political actor 'must' choose war or peace. Therefore event probabilities remain grey until the geopolitical/event hazard model is validated.</div>", unsafe_allow_html=True)

    top, side = st.columns([1.35, 1])
    with top:
        st.markdown("<div class='panel'><div class='ptitle'>Scenario Constellation · examples are conditional, not deterministic</div>", unsafe_allow_html=True)
        event_cards = "<div class='scenario-grid'>"
        event_cards += scenario_card("CONFLICT", "War continues · financing manageable", "Possible if financing demand remains absorbable, rates/funding stay contained, and energy disruption is limited.", "blue")
        event_cards += scenario_card("CONFLICT", "War + energy stagflation", "Becomes more dangerous if oil/supply stress lifts inflation while growth and credit weaken.", energy_tone if energy_tone != "green" else "amber")
        event_cards += scenario_card("FISCAL", "Fiscal-forced de-escalation", "Probability can rise if fiscal headroom, term premium, interest burden and political funding become binding together. Not implied by debt level alone.", fiscal_tone)
        event_cards += scenario_card("PEACE", "Diplomatic ceasefire / peace dividend", "If diplomacy resolves the conflict before macro damage: risk premium, oil/freight pressure and inflation expectations can normalize.", "green")
        event_cards += scenario_card("PEACE", "Crisis-forced ceasefire", "Same ceasefire headline, different economics: if de-escalation is forced by fiscal/credit stress, markets need not react bullishly.", "amber")
        event_cards += scenario_card("FISCAL", "Debt-limit confrontation", f"Current-law ceiling is ${STATUTORY_DEBT_LIMIT_TN:.3f}tn; CBO baseline says Treasury reaches the limit {CBO_BASELINE_LIMIT_TIMING}. Exact legal headroom requires debt-subject-to-limit data.", "amber")
        event_cards += "</div>"
        st.markdown(event_cards + "</div>", unsafe_allow_html=True)

    with side:
        st.markdown(f"""
<div class='panel'><div class='ptitle'>Fiscal–War Constraint Monitor</div>
<div class='rowline'><div>Gross federal debt / GDP</div><div class='right'><b>{fmt(debt_gdp,1,'%')}</b></div></div>
<div class='rowline'><div>Federal deficit / GDP</div><div class='right'><b>{fmt(deficit_gdp,1,'%')}</b></div></div>
<div class='rowline'><div>Interest outlays / GDP</div><div class='right'><b>{fmt(interest_gdp,2,'%')}</b></div></div>
<div class='rowline'><div>10Y term premium</div><div class='right'><b>{fmt(term_premium,2,'%')}</b></div></div>
<div class='rowline'><div>Daily gross debt (Treasury)</div><div class='right'><b>{fmt(treasury_debt_tn,2,' tn')}</b></div></div>
<div class='rowline'><div>Statutory debt limit reference</div><div class='right'><b>${STATUTORY_DEBT_LIMIT_TN:.3f}tn</b><div class='muted'>{DEBT_LIMIT_REFERENCE_DATE}</div></div></div>
<div class='rowline'><div>Gross-debt vs ceiling difference</div><div class='right'><b>{signed(rough_gross_headroom,2,' tn')}</b><div class='muted'>rough context only — not legal headroom</div></div></div>
<div class='gate' style='margin-top:6px'><b>Do not read gross-debt difference as exact debt-ceiling headroom.</b> Debt subject to limit differs from total public debt. This box is a fiscal-pressure context until the legal debt-limit feed is wired.</div></div>
""", unsafe_allow_html=True)

    st.markdown("<div class='section'>How a conflict scenario transmits</div>", unsafe_allow_html=True)
    ch1, ch2, ch3 = st.columns(3)
    with ch1:
        st.markdown("<div class='panel'><div class='ptitle'>A · Financing remains manageable</div><div class='chain'>War spending ↑ → deficit ↑ → issuance ↑ → demand absorbs issuance → yields/funding contained → <b>no binding fiscal constraint yet</b>.</div><div class='gate' style='margin-top:6px'>Confirmation: auction/funding demand remains healthy, term premium stable, energy disruption limited.</div></div>", unsafe_allow_html=True)
    with ch2:
        st.markdown("<div class='panel'><div class='ptitle'>B · Crowding-out / stagflation</div><div class='chain'>War + supply disruption → oil/freight ↑ → inflation ↑ + growth ↓ → easing becomes harder → yields/credit cost ↑ → valuations/housing/capex weaken.</div><div class='gate' style='margin-top:6px'>Confirmation: energy + breakevens + term premium + credit stress rise together.</div></div>", unsafe_allow_html=True)
    with ch3:
        st.markdown("<div class='panel'><div class='ptitle'>C · Fiscal pressure raises de-escalation incentive</div><div class='chain'>War burn-rate ↑ + deficit/interest burden ↑ + legal/political funding constraint ↑ → economic cost becomes harder to absorb → <b>de-escalation pressure rises</b>.</div><div class='gate' style='margin-top:6px'>Not deterministic: government can also raise/suspend ceiling, borrow more, cut other spending, raise revenue, or shift burden to allies.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section'>Other scenario families the engine should discover/test</div>", unsafe_allow_html=True)
    library_df = pd.DataFrame(SCENARIO_LIBRARY, columns=["Family", "Scenario", "Mechanism", "Key data / trigger family"])
    st.dataframe(library_df, use_container_width=True, hide_index=True, height=420)

# ============================================================
# TAB 3 — RESEARCH
# ============================================================
with tab_research:
    st.markdown("<div class='section'>Scenario screening</div>", unsafe_allow_html=True)
    screen_df = pd.DataFrame(SCENARIO_SCREEN, columns=["Scenario", "Decision", "Evidence strength", "Why"])
    st.dataframe(screen_df, use_container_width=True, hide_index=True)

    st.markdown("<div class='section'>Raw readings</div>", unsafe_allow_html=True)
    raw = pd.DataFrame([
        ["BBK Monthly GDP", bbk_gdp, "% annualized"], ["BBK Coincident", bbk_co, "σ"], ["BBK Leading", bbk_lead, "σ"], ["WEI", wei, "%"],
        ["Trimmed Mean PCE", trimmed, "% y/y"], ["Core PCE", core_pce, "% y/y"], ["Sahm", sahm, "pp"], ["Initial Claims", claims, "claims"],
        ["SLOOS", sloos, "net %"], ["EBP", ebp, "index"], ["EBP recession benchmark", ebp_prob, "%"], ["FCI-G", fcig, "pp impulse"],
        ["NFCI Risk", nfci, "index"], ["VIX", vix, "index"], ["HY OAS", hy, "%"], ["5Y Breakeven", breakeven, "%"],
        ["10Y Treasury", d10, "%"], ["2Y Treasury", d2, "%"], ["Fed Funds", fedfunds, "%"], ["10Y Term Premium", term_premium, "%"],
        ["WTI Oil", oil, "$/bbl"], ["Debt / GDP", debt_gdp, "% GDP"], ["Deficit / GDP", deficit_gdp, "% GDP"], ["Interest Outlays / GDP", interest_gdp, "% GDP"],
        ["Treasury daily gross debt", treasury_debt_tn, "trillion USD"],
    ], columns=["Series", "Latest", "Unit"])
    st.dataframe(raw, use_container_width=True, hide_index=True)

    st.markdown("<div class='section'>Research gates</div>", unsafe_allow_html=True)
    st.markdown("""
- **Projection probability:** locked until point-in-time / vintage walk-forward validation.
- **Crash probability:** locked until drawdown target definition, calibration and OOS tests are frozen.
- **Event probability:** locked until geopolitical/event-frequency data and historical base rates are validated.
- **War sustainability vs war choice:** separate models. Economic constraints can change feasibility/incentives; they do not determine political intent.
- **Scenario discovery:** broad candidate universe is allowed, but production only admits scenarios with incremental OOS information and stable transmission logic.
""")

    if errors:
        with st.expander(f"Data / optional feed errors ({len(errors)})"):
            st.dataframe(pd.DataFrame([{"Source": k, "Error": v} for k, v in errors.items()]), use_container_width=True, hide_index=True)

st.caption("Landing v3 is a visual prototype: live states are official/public benchmarks; proprietary future probabilities stay grey until validated. World/event scenarios are conditional transmission maps, not political predictions.")

from __future__ import annotations

import io
import json
import math
import os
import re
import statistics
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    import networkx as nx
except Exception:
    nx = None

try:
    import yfinance as yf
except Exception:
    yf = None

# ============================================================
# OPPORTUNITY INTELLIGENCE ENGINE v1.5 AUTO DECISION VIEW
# ------------------------------------------------------------
# Goal: high-recall discovery of exceptional opportunities, then
# high-precision confirmation. No classic technical indicators.
# Price history is used only for valuation context, policy-relevant
# speed/volatility and realized outcome/replay — never RSI/MACD/etc.
# ------------------------------------------------------------
# IMPORTANT RESEARCH GATES
# - Scenario discovery can generate hypotheses automatically.
# - LLM-style narrative is not allowed to assign numeric probability.
# - Historical acceptance cases are NEVER used to tune thresholds.
# - Action labels are research states until PIT/OOS validation passes.
# - Fair-value bands are transparent scenario estimates, not guarantees.
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Opportunity Intelligence",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Macro module is optional-safe at import time so a stale/mismatched deploy cannot blank the whole app.
try:
    import macro_embedded as _macro_module
    _macro_import_error = ""
except Exception as _macro_exc:
    _macro_module = None
    _macro_import_error = f"{type(_macro_exc).__name__}: {_macro_exc}"

def _macro_gate_fallback(error: str = "") -> Dict[str, Any]:
    """Fail closed: keep the scanner alive but never upgrade risk if macro is unavailable."""
    snap = {
        "action_label": "HOLD / MACRO GATED",
        "action_tone": "gray",
        "action_score": 50,
        "headline": "Macro feed unavailable; leverage upgrades disabled until the live macro gate returns.",
        "regime": "MACRO GATED",
        "regime_explain": "Opportunity discovery can continue, but sizing/expression must remain conservative.",
        "crash_state": "GATED",
        "crash_tone": "gray",
        "credit_state": "GATED",
        "market_structure": "GATED",
        "event_override": None,
        "event_override_score": None,
        "horizon_actions": [],
        "macro_scenarios": [],
        "event_scenarios": [],
        "data_errors": {"macro_module": error or "macro module unavailable"},
        "refreshed_at_utc": pd.Timestamp.utcnow().isoformat(),
    }
    st.session_state["macro_gate_snapshot"] = snap
    if error:
        st.session_state["macro_refresh_error"] = error
    return snap

def safe_compute_macro_gate_snapshot(refresh: bool = False) -> Dict[str, Any]:
    fn = getattr(_macro_module, "compute_macro_gate_snapshot", None) if _macro_module is not None else None
    if not callable(fn):
        detail = _macro_import_error or "macro_embedded.py is stale/missing compute_macro_gate_snapshot()"
        return _macro_gate_fallback(detail)
    try:
        return fn(refresh=refresh)
    except Exception as exc:
        return _macro_gate_fallback(f"{type(exc).__name__}: {exc}")

def safe_render_macro_control_room() -> None:
    fn = getattr(_macro_module, "render_macro_control_room", None) if _macro_module is not None else None
    if not callable(fn):
        snap = _macro_gate_fallback(_macro_import_error or "macro_embedded.py is stale/missing render_macro_control_room()")
        st.error("Macro module mismatch detected. The app stays online in MACRO GATED mode; deploy app.py and macro_embedded.py from the same bundle.")
        st.json({k: snap.get(k) for k in ["action_label","regime","crash_state","credit_state"]})
        return
    try:
        fn()
    except Exception as exc:
        snap = _macro_gate_fallback(f"{type(exc).__name__}: {exc}")
        st.error("Live macro rendering failed, so the app switched to MACRO GATED mode instead of crashing.")
        st.caption(str(exc))
        st.json({k: snap.get(k) for k in ["action_label","regime","crash_state","credit_state"]})

HEADERS = {
    "User-Agent": "OpportunityIntelligence/1.0 research-dashboard contact=local-user",
    "Accept": "application/json,text/csv,text/xml,application/xml,text/plain,*/*",
}

NO_TECHNICALS = True
PRODUCTION_ACTION_MODEL_VALIDATED = False
PRODUCTION_FAIR_VALUE_MODEL_VALIDATED = False
PRODUCTION_EVENT_PROBABILITY_VALIDATED = False

# -----------------------------
# Utility
# -----------------------------
def safe_float(x: Any) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def fmt_num(x: float, digits: int = 1, suffix: str = "") -> str:
    return "—" if not np.isfinite(x) else f"{x:,.{digits}f}{suffix}"


def fmt_money(x: float, currency: str = "$", digits: int = 2) -> str:
    if not np.isfinite(x):
        return "—"
    if abs(x) >= 1e12:
        return f"{currency}{x/1e12:,.2f}T"
    if abs(x) >= 1e9:
        return f"{currency}{x/1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"{currency}{x/1e6:,.2f}M"
    return f"{currency}{x:,.{digits}f}"


def pct(x: float, digits: int = 1) -> str:
    return "—" if not np.isfinite(x) else f"{x*100:,.{digits}f}%"


def clamp(x: float, lo: float, hi: float) -> float:
    if not np.isfinite(x):
        return np.nan
    return max(lo, min(hi, x))


def percentile_rank(s: pd.Series, value: float) -> float:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if not np.isfinite(value) or x.empty:
        return np.nan
    return float((x <= value).mean())


def robust_quantiles(values: Sequence[float]) -> Tuple[float, float, float]:
    x = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 2:
        return (np.nan, np.nan, np.nan)
    return tuple(float(v) for v in x.quantile([0.25, 0.50, 0.75]).tolist())


def read_csv(name: str) -> pd.DataFrame:
    p = DATA / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


UNIVERSE = read_csv("universe.csv")
EDGES = read_csv("causal_edges.csv")
FAMILIES = read_csv("opportunity_families.csv")
TEMPLATES = read_csv("scenario_templates.csv")
ACCEPTANCE = read_csv("acceptance_tests.csv")
REPLAY = read_csv("replay_phases.csv")
DISCOVERY_QUERIES = read_csv("scenario_discovery_queries.csv")
SOURCE_REGISTRY = read_csv("source_registry.csv")

# -----------------------------
# Styling
# -----------------------------
COLORS = {
    "green": ("#27d896", "rgba(39,216,150,.12)"),
    "amber": ("#f2b557", "rgba(242,181,87,.13)"),
    "red": ("#ff6d77", "rgba(255,109,119,.12)"),
    "blue": ("#78aaff", "rgba(120,170,255,.12)"),
    "gray": ("#93a0b2", "rgba(147,160,178,.10)"),
    "purple": ("#b99cff", "rgba(185,156,255,.12)"),
}

st.markdown(
    """
<style>
:root{--bg:#070b11;--panel:#0f1621;--panel2:#0b121b;--border:#202d3e;--text:#eef4fb;--muted:#8d9aac}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1580px;padding-top:.65rem;padding-bottom:1.3rem}
header[data-testid="stHeader"]{background:transparent}
.hero{border:1px solid var(--border);border-radius:16px;padding:14px 16px;background:linear-gradient(180deg,#111b29,#0c121b)}
.hero-title{font-size:1.75rem;font-weight:850;letter-spacing:-.035em}.sub{font-size:.76rem;color:var(--muted);margin-top:3px;line-height:1.35}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:.59rem;font-weight:830;letter-spacing:.035em}
.section{font-size:.66rem;font-weight:830;letter-spacing:.11em;text-transform:uppercase;color:#91a4bc;margin:.65rem 0 .33rem}
.panel{border:1px solid var(--border);border-radius:13px;background:linear-gradient(180deg,#111925,#0c121b);padding:11px 12px}.ptitle{font-size:.74rem;font-weight:840;margin-bottom:7px}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px}.kpi{border:1px solid var(--border);border-radius:11px;background:#0c131d;padding:8px 9px;min-height:82px}.kicker{font-size:.53rem;color:#8392a5;font-weight:820;letter-spacing:.08em;text-transform:uppercase}.kval{font-size:.82rem;font-weight:840;margin-top:4px}.knum{font-size:1.12rem;font-weight:860;margin-top:2px}.knote{font-size:.59rem;color:#8e9bad;line-height:1.23;margin-top:3px}
.action{border:1px solid var(--border);border-radius:13px;padding:11px;background:#0c131d}.action h3{margin:0;font-size:1.05rem}.action p{font-size:.67rem;color:#9aa8b8;line-height:1.35;margin:.35rem 0 0}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.card{border:1px solid var(--border);border-radius:11px;background:#0c131d;padding:9px;min-height:104px}.ct{font-size:.69rem;font-weight:840}.cn{font-size:.60rem;color:#8f9cad;line-height:1.28;margin-top:4px}
.small{font-size:.60rem;color:#8f9cad;line-height:1.32}.big{font-size:1.28rem;font-weight:860}.muted{color:#8f9cad}.row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.055);font-size:.65rem}.row:last-child{border-bottom:none}.right{text-align:right}
.chainbox{padding:8px 9px;border:1px solid var(--border);border-radius:10px;background:#0c131d;font-size:.64rem;line-height:1.45;color:#d3dde8}.gate{border:1px solid #39485c;border-radius:9px;background:rgba(80,97,126,.10);padding:7px 8px;color:#aeb9c8;font-size:.60rem;line-height:1.3}
.stagebar{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.stage{padding:4px 7px;border-radius:8px;font-size:.58rem;font-weight:820;border:1px solid var(--border);background:#0c131d}.stage.on{box-shadow:0 0 0 1px rgba(255,255,255,.06) inset}
.matrix{width:100%;border-collapse:separate;border-spacing:4px}.matrix th{font-size:.55rem;color:#8291a4;text-transform:uppercase;letter-spacing:.05em;text-align:left}.matrix td{border:1px solid var(--border);border-radius:8px;padding:7px;background:#0c131d;vertical-align:top}.mv{font-size:.67rem;font-weight:830}.mn{font-size:.55rem;color:#8d9aac;margin-top:2px}
div[data-baseweb="tab-list"]{gap:6px}button[data-baseweb="tab"]{height:34px;font-size:.71rem}
@media(max-width:1000px){.kpis,.grid3{grid-template-columns:1fr 1fr}}
</style>
""",
    unsafe_allow_html=True,
)


def badge(text: str, tone: str = "blue") -> str:
    c, bg = COLORS.get(tone, COLORS["gray"])
    return f"<span class='badge' style='color:{c};background:{bg};border:1px solid {c}33'>{text}</span>"


def kpi(kicker: str, value: str, num: str, note: str, tone: str = "blue") -> str:
    c, bg = COLORS.get(tone, COLORS["gray"])
    return f"<div class='kpi' style='background:linear-gradient(180deg,{bg},#0c131d)'><div class='kicker'>{kicker}</div><div class='kval' style='color:{c}'>{value}</div><div class='knum'>{num}</div><div class='knote'>{note}</div></div>"


# -----------------------------
# Market-data adapters
# -----------------------------
@dataclass
class AssetSnapshot:
    market: str
    symbol: str
    name: str
    sector: str = "Unknown"
    price: float = np.nan
    market_cap: float = np.nan
    trailing_pe: float = np.nan
    forward_pe: float = np.nan
    revenue_ttm: float = np.nan
    eps_ttm: float = np.nan
    fcf_ttm: float = np.nan
    gross_margin: float = np.nan
    net_margin: float = np.nan
    revenue_growth_yoy: float = np.nan
    eps_growth_yoy: float = np.nan
    gross_margin_change: float = np.nan
    fcf_growth_yoy: float = np.nan
    price_change_20d: float = np.nan
    realized_vol_20d: float = np.nan
    history_rows: int = 0
    data_quality: str = "LOW"
    error: str = ""


def _pick_row(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    idx_map = {str(i).lower(): i for i in df.index}
    for c in candidates:
        if c.lower() in idx_map:
            return pd.to_numeric(df.loc[idx_map[c.lower()]], errors="coerce")
    for i in df.index:
        il = str(i).lower()
        if any(c.lower() in il for c in candidates):
            return pd.to_numeric(df.loc[i], errors="coerce")
    return None


def _series_latest4(s: Optional[pd.Series]) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    x = pd.to_numeric(s, errors="coerce").dropna()
    # yfinance financial columns are usually newest first
    return x.iloc[:8]


def _yoy_from_quarters(s: Optional[pd.Series]) -> float:
    x = _series_latest4(s)
    if len(x) < 5 or x.iloc[4] == 0:
        return np.nan
    return float(x.iloc[0] / x.iloc[4] - 1)


def _margin_latest(num: Optional[pd.Series], den: Optional[pd.Series]) -> float:
    a, b = _series_latest4(num), _series_latest4(den)
    if a.empty or b.empty or b.iloc[0] == 0:
        return np.nan
    return float(a.iloc[0] / b.iloc[0])


def _margin_change_yoy(num: Optional[pd.Series], den: Optional[pd.Series]) -> float:
    a, b = _series_latest4(num), _series_latest4(den)
    if len(a) < 5 or len(b) < 5 or b.iloc[0] == 0 or b.iloc[4] == 0:
        return np.nan
    return float(a.iloc[0] / b.iloc[0] - a.iloc[4] / b.iloc[4])


def _ttm(s: Optional[pd.Series]) -> float:
    x = _series_latest4(s)
    return float(x.iloc[:4].sum()) if len(x) >= 4 else np.nan


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yfinance_snapshot(market: str, symbol: str, name: str) -> Dict[str, Any]:
    snap = AssetSnapshot(market=market, symbol=symbol, name=name)
    if yf is None:
        snap.error = "yfinance is not installed"
        return dict(snap.__dict__)
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="2y", auto_adjust=True, actions=False)
        info = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}
        snap.sector = str(info.get("sector") or info.get("industry") or "Unknown")
        snap.market_cap = safe_float(info.get("marketCap"))
        snap.trailing_pe = safe_float(info.get("trailingPE"))
        snap.forward_pe = safe_float(info.get("forwardPE"))
        if hist is not None and not hist.empty and "Close" in hist:
            close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
            snap.history_rows = len(close)
            if not close.empty:
                snap.price = float(close.iloc[-1])
                if len(close) >= 21 and close.iloc[-21] != 0:
                    snap.price_change_20d = float(close.iloc[-1] / close.iloc[-21] - 1)
                    ret = np.log(close / close.shift(1)).dropna().iloc[-20:]
                    snap.realized_vol_20d = float(ret.std(ddof=1) * np.sqrt(252)) if len(ret) >= 10 else np.nan

        inc = getattr(t, "quarterly_income_stmt", pd.DataFrame())
        cf = getattr(t, "quarterly_cashflow", pd.DataFrame())
        rev = _pick_row(inc, ["Total Revenue", "Operating Revenue", "Revenue"])
        gross = _pick_row(inc, ["Gross Profit"])
        net = _pick_row(inc, ["Net Income", "Net Income Common Stockholders"])
        eps = _pick_row(inc, ["Diluted EPS", "Basic EPS"])
        fcf = _pick_row(cf, ["Free Cash Flow"])
        if fcf is None:
            ocf = _pick_row(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
            capex = _pick_row(cf, ["Capital Expenditure", "Capital Expenditures"])
            if ocf is not None and capex is not None:
                fcf = pd.to_numeric(ocf, errors="coerce") + pd.to_numeric(capex, errors="coerce")

        snap.revenue_ttm = _ttm(rev)
        snap.eps_ttm = _ttm(eps)
        if not np.isfinite(snap.eps_ttm) and np.isfinite(snap.market_cap) and np.isfinite(snap.trailing_pe) and snap.trailing_pe != 0 and np.isfinite(snap.price):
            snap.eps_ttm = snap.price / snap.trailing_pe
        snap.fcf_ttm = _ttm(fcf)
        snap.revenue_growth_yoy = _yoy_from_quarters(rev)
        snap.eps_growth_yoy = _yoy_from_quarters(eps)
        snap.fcf_growth_yoy = _yoy_from_quarters(fcf)
        snap.gross_margin = _margin_latest(gross, rev)
        snap.net_margin = _margin_latest(net, rev)
        snap.gross_margin_change = _margin_change_yoy(gross, rev)
        if not np.isfinite(snap.trailing_pe) and np.isfinite(snap.price) and np.isfinite(snap.eps_ttm) and snap.eps_ttm > 0:
            snap.trailing_pe = snap.price / snap.eps_ttm
        valid = sum(np.isfinite(v) for v in [snap.price, snap.revenue_growth_yoy, snap.gross_margin, snap.eps_ttm, snap.market_cap])
        snap.data_quality = "HIGH" if valid >= 5 else ("MEDIUM" if valid >= 3 else "LOW")
        return dict(snap.__dict__)
    except Exception as e:
        snap.error = str(e)
        return dict(snap.__dict__)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_price_only_snapshot(market: str, symbol: str, name: str) -> Dict[str, Any]:
    """Lightweight market adapter for FX/commodities; avoids pointless company-financial calls."""
    snap=AssetSnapshot(market=market,symbol=symbol,name=name)
    if yf is None:
        snap.error="yfinance is not installed"
        return dict(snap.__dict__)
    try:
        t=yf.Ticker(symbol)
        hist=t.history(period="1y",auto_adjust=True,actions=False)
        if hist is not None and not hist.empty and "Close" in hist:
            close=pd.to_numeric(hist["Close"],errors="coerce").dropna()
            snap.history_rows=len(close)
            if not close.empty:
                snap.price=float(close.iloc[-1])
                if len(close)>=21 and close.iloc[-21]!=0:
                    snap.price_change_20d=float(close.iloc[-1]/close.iloc[-21]-1)
                    ret=np.log(close/close.shift(1)).dropna().iloc[-20:]
                    snap.realized_vol_20d=float(ret.std(ddof=1)*np.sqrt(252)) if len(ret)>=10 else np.nan
        snap.data_quality="MEDIUM" if np.isfinite(snap.price) else "LOW"
        return dict(snap.__dict__)
    except Exception as exc:
        snap.error=str(exc)
        return dict(snap.__dict__)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_coingecko(coin_id: str) -> Dict[str, Any]:
    if not coin_id:
        return {}
    url = f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(coin_id)}"
    try:
        r = requests.get(url, params={"localization":"false","tickers":"false","market_data":"true","community_data":"false","developer_data":"false","sparkline":"false"}, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_defillama_revenue(slug: str) -> pd.Series:
    if not slug:
        return pd.Series(dtype=float)
    candidates = [
        f"https://api.llama.fi/summary/fees/{urllib.parse.quote(slug)}?dataType=dailyRevenue",
        f"https://api.llama.fi/summary/fees/{urllib.parse.quote(slug)}?dataType=dailyFees",
    ]
    for url in candidates:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            j = r.json()
            chart = j.get("totalDataChart") or j.get("totalDataChartBreakdown") or []
            rows = []
            if isinstance(chart, list):
                for item in chart:
                    if isinstance(item, list) and len(item) >= 2 and isinstance(item[1], (int,float)):
                        rows.append((pd.to_datetime(item[0], unit="s", errors="coerce"), float(item[1])))
            if rows:
                return pd.Series(dict(rows)).sort_index()
        except Exception:
            continue
    return pd.Series(dtype=float)


# -----------------------------
# News / automatic scenario discovery
# -----------------------------
STOPWORDS = set("the a an and or for to of in on with as at by from is are was were be been being this that it its their our your new says said after before over amid into up down more less rise rises rising fall falls falling market markets stock stocks company companies business industry us u s year years month months week weeks today latest".split())

THEME_RULES = {
    "Supply bottleneck": ["shortage","bottleneck","capacity","allocation","lead time","backlog","sold out","scarcity","constraint"],
    "Data-center power": ["data center","datacenter","transformer","grid","power demand","turbine","switchgear","electricity"],
    "Photonics / networking": ["photonics","optical","transceiver","laser","co-packaged","cpo","bandwidth","interconnect"],
    "War / shipping": ["war","attack","chokepoint","shipping","tanker","sanction","blockade","missile","ceasefire"],
    "Commodity scarcity": ["inventory","export ban","crop","drought","harvest","mine disruption","production cut"],
    "Crypto value capture": ["buyback","burn","fees","revenue","emissions","unlock","tokenholder","staking"],
    "Crypto usage / scarcity": ["shielded","privacy","adoption","integration","wallet","usage","issuance"],
    "FX intervention": ["intervention","disorderly","finance ministry","currency support","yen buying","verbal intervention"],
    "Credit / funding": ["credit stress","funding squeeze","default","private credit","spread widening","bank stress"],
    "Policy / fiscal": ["tariff","subsidy","appropriation","fiscal","debt ceiling","government contract","export control"],
    "Cyber / infrastructure": ["cyberattack","outage","clearing","payment system","ransomware","infrastructure attack"],
    "Consumer inflection": ["pricing power","distribution expansion","consumer demand","market share","product launch","margin expansion"],
}

THEME_ROOT = {
    "Supply bottleneck": "Supply bottleneck",
    "Data-center power": "Electrical load",
    "Photonics / networking": "Networking bandwidth",
    "War / shipping": "War escalation",
    "Commodity scarcity": "Physical commodity bottleneck",
    "Crypto value capture": "Protocol usage",
    "Crypto usage / scarcity": "Private asset usage",
    "FX intervention": "Policy intervention hazard",
    "Credit / funding": "Credit/funding shock",
    "Policy / fiscal": "Policy intervention",
    "Cyber / infrastructure": "Cyber shock",
    "Consumer inflection": "Consumer demand",
}


@st.cache_data(ttl=900, show_spinner=False)
def google_news_rss(query: str, limit: int = 12) -> List[Dict[str, str]]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q":query, "hl":"en-US", "gl":"US", "ceid":"US:en"})
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source = ""
            src = item.find("source")
            if src is not None and src.text:
                source = src.text.strip()
            out.append({"title":title,"link":link,"pubDate":pub,"source":source,"query":query})
        return out
    except Exception:
        return []


def classify_headline(text: str) -> List[str]:
    t = text.lower()
    hits = []
    for theme, terms in THEME_RULES.items():
        if any(term in t for term in terms):
            hits.append(theme)
    return hits


def extract_novel_terms(headlines: Sequence[str], known_terms: Iterable[str], min_count: int = 3) -> List[Tuple[str,int]]:
    known = set(k.lower() for k in known_terms)
    c = Counter()
    for h in headlines:
        words = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", h.lower())
        for w in set(words):
            if w in STOPWORDS or w in known:
                continue
            c[w] += 1
    return [(w,n) for w,n in c.most_common(12) if n >= min_count]


@st.cache_data(ttl=900, show_spinner=False)
def discover_live_scenarios(max_queries: int = 10) -> pd.DataFrame:
    rows = []
    queries = DISCOVERY_QUERIES.head(max_queries) if not DISCOVERY_QUERIES.empty else pd.DataFrame()
    all_items: List[Dict[str,str]] = []
    qlist = [str(qrow["query"]) for _, qrow in queries.iterrows()]
    if qlist:
        with ThreadPoolExecutor(max_workers=min(6, len(qlist))) as ex:
            futs = [ex.submit(google_news_rss, q, 10) for q in qlist]
            for fut in as_completed(futs):
                try:
                    all_items.extend(fut.result())
                except Exception:
                    pass
    if not all_items:
        return pd.DataFrame(columns=["theme","root","evidence_count","source_count","latest_headline","sources","novelty"])

    buckets: Dict[str,List[Dict[str,str]]] = defaultdict(list)
    for item in all_items:
        themes = classify_headline(item["title"])
        for th in themes:
            buckets[th].append(item)

    for th, items in buckets.items():
        sources = sorted(set(i.get("source") or "Unknown" for i in items))
        rows.append({
            "theme": th,
            "root": THEME_ROOT.get(th, th),
            "evidence_count": len(items),
            "source_count": len(sources),
            "latest_headline": items[0]["title"] if items else "",
            "sources": ", ".join(sources[:5]),
            "novelty": "MAPPED",
        })

    known_terms = [term for terms in THEME_RULES.values() for term in terms]
    novel = extract_novel_terms([i["title"] for i in all_items], known_terms, min_count=3)
    for word, n in novel[:6]:
        matched = [i for i in all_items if word in i["title"].lower()]
        sources = sorted(set(i.get("source") or "Unknown" for i in matched))
        rows.append({
            "theme": f"NOVEL CLUSTER: {word}",
            "root": "Unmapped hypothesis",
            "evidence_count": n,
            "source_count": len(sources),
            "latest_headline": matched[0]["title"] if matched else "",
            "sources": ", ".join(sources[:5]),
            "novelty": "NOVEL — NEEDS CAUSAL MAPPING",
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["discovery_rank"] = df["evidence_count"].rank(pct=True) * 0.6 + df["source_count"].rank(pct=True) * 0.4
        df = df.sort_values(["discovery_rank","source_count"], ascending=False).reset_index(drop=True)
    return df


def persist_scenario_memory(df: pd.DataFrame) -> None:
    if df.empty:
        return
    p = STATE / "scenario_memory.json"
    try:
        old: Dict[str, Any] = {}
        if p.exists():
            old = json.loads(p.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat()
        for _, r in df.iterrows():
            key = str(r["theme"])
            entry = old.get(key, {"first_seen":now,"observations":0})
            entry.update({
                "last_seen": now,
                "observations": int(entry.get("observations",0)) + 1,
                "root": str(r.get("root","")),
                "evidence_count": int(r.get("evidence_count",0)),
                "source_count": int(r.get("source_count",0)),
                "latest_headline": str(r.get("latest_headline","")),
            })
            old[key] = entry
        p.write_text(json.dumps(old, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_scenario_memory() -> pd.DataFrame:
    p = STATE / "scenario_memory.json"
    try:
        if not p.exists():
            return pd.DataFrame()
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = [{"theme":k, **v} for k,v in d.items()]
        return pd.DataFrame(rows).sort_values("last_seen", ascending=False)
    except Exception:
        return pd.DataFrame()


# -----------------------------
# Causal graph
# -----------------------------
def normalize_edges() -> pd.DataFrame:
    if EDGES.empty:
        return EDGES
    e = EDGES.copy()
    for c in ["source","target","mechanism","sign","lag","role","validation","condition"]:
        if c not in e:
            e[c] = ""
    return e


EDGE_DF = normalize_edges()


def find_root_candidates(term: str) -> List[str]:
    if EDGE_DF.empty:
        return []
    terml = term.lower().strip()
    nodes = sorted(set(EDGE_DF["source"].astype(str)) | set(EDGE_DF["target"].astype(str)))
    direct = [n for n in nodes if terml in n.lower()]
    if direct:
        return direct[:20]
    tokens = [t for t in re.findall(r"[a-z0-9]+", terml) if len(t) > 2]
    scored = []
    for n in nodes:
        score = sum(1 for t in tokens if t in n.lower())
        if score:
            scored.append((score,n))
    return [n for _,n in sorted(scored, reverse=True)[:20]]


def expand_chain(root: str, depth: int = 4, max_edges: int = 80) -> pd.DataFrame:
    if EDGE_DF.empty or not root:
        return pd.DataFrame()
    by_source = defaultdict(list)
    for i, r in EDGE_DF.iterrows():
        by_source[str(r["source"])].append(i)
    q = deque([(root,0)])
    seen_nodes = {root}
    selected = []
    while q and len(selected) < max_edges:
        node, d = q.popleft()
        if d >= depth:
            continue
        for idx in by_source.get(node, []):
            r = EDGE_DF.loc[idx]
            selected.append(idx)
            tgt = str(r["target"])
            if tgt not in seen_nodes:
                seen_nodes.add(tgt)
                q.append((tgt,d+1))
    if not selected:
        return pd.DataFrame()
    out = EDGE_DF.loc[selected].copy().drop_duplicates()
    # derive BFS layer for display
    layer = {root:0}
    changed = True
    while changed:
        changed = False
        for _, r in out.iterrows():
            s,t = str(r["source"]),str(r["target"])
            if s in layer and (t not in layer or layer[t] > layer[s]+1):
                layer[t] = layer[s]+1; changed=True
    out["layer"] = out["target"].map(layer).fillna(depth).astype(int)
    return out


def chain_plot(chain: pd.DataFrame, root: str):
    if go is None or nx is None or chain.empty:
        return None
    G = nx.DiGraph()
    G.add_node(root, layer=0)
    for _, r in chain.iterrows():
        G.add_edge(str(r["source"]), str(r["target"]), role=str(r.get("role","")), sign=str(r.get("sign","")))
        G.nodes[str(r["target"])]["layer"] = int(r.get("layer",1))
    layers = defaultdict(list)
    for n, attrs in G.nodes(data=True):
        layers[int(attrs.get("layer",0))].append(n)
    pos = {}
    for lx in sorted(layers):
        nodes = layers[lx]
        for j,n in enumerate(nodes):
            pos[n] = (lx, -(j - (len(nodes)-1)/2))
    ex, ey = [], []
    for a,b in G.edges():
        x0,y0=pos[a]; x1,y1=pos[b]
        ex += [x0,x1,None]; ey += [y0,y1,None]
    edge_trace = go.Scatter(x=ex,y=ey,mode="lines",line=dict(width=1,color="#435269"),hoverinfo="none")
    nxv, nyv, text, colors = [], [], [], []
    for n in G.nodes():
        x,y=pos[n]; nxv.append(x); nyv.append(y); text.append(n)
        if n == root: colors.append("#78aaff")
        else:
            incoming = [d.get("role","") for _,_,d in G.in_edges(n,data=True)]
            role = incoming[0] if incoming else ""
            colors.append("#ff6d77" if role=="LOSER" else ("#f2b557" if role in {"BOTTLENECK","CONDITIONAL"} else "#27d896"))
    node_trace = go.Scatter(x=nxv,y=nyv,mode="markers+text",text=text,textposition="top center",textfont=dict(size=9,color="#d9e4ef"),marker=dict(size=14,color=colors,line=dict(width=1,color="#0b1119")),hoverinfo="text")
    fig = go.Figure([edge_trace,node_trace])
    fig.update_layout(height=500,showlegend=False,margin=dict(l=5,r=5,t=5,b=5),paper_bgcolor="#0b1119",plot_bgcolor="#0b1119",xaxis=dict(visible=False),yaxis=dict(visible=False))
    return fig


# -----------------------------
# Opportunity discovery / projection
# -----------------------------
def base_family_from_market(market: str) -> str:
    return {
        "US":"Fundamental / causal inflection",
        "IHSG":"Fundamental / structural inflection",
        "FX":"Relative macro / policy hazard",
        "Commodity":"Physical bottleneck / event propagation",
        "Crypto":"Economic value / usage / scarcity",
    }.get(market,"Cross-asset opportunity")


def _snapshot_one(r: pd.Series) -> Dict[str, Any]:
    market, symbol, name = str(r["market"]), str(r["symbol"]), str(r["name"])
    external_id = str(r.get("external_id") or "")
    # Asset-class adapters are intentionally different. Do not waste company-financial
    # calls on FX/commodities, and do not trust Yahoo aliases for crypto economics.
    if market == "Crypto":
        snap=dict(AssetSnapshot(market=market,symbol=symbol,name=name).__dict__)
        if external_id:
            j=fetch_coingecko(external_id)
            md=(j or {}).get("market_data",{}) or {}
            snap["price"]=safe_float((md.get("current_price",{}) or {}).get("usd"))
            snap["market_cap"]=safe_float((md.get("market_cap",{}) or {}).get("usd"))
            snap["crypto_fdv"]=safe_float((md.get("fully_diluted_valuation",{}) or {}).get("usd"))
            snap["data_quality"]="MEDIUM" if np.isfinite(snap["price"]) and np.isfinite(snap["market_cap"]) else "LOW"
        snap["source_coverage"]="CoinGecko market/supply + optional DeFiLlama economics"
    elif market in ["FX","Commodity"]:
        snap=dict(fetch_price_only_snapshot(market,symbol,name))
        snap["source_coverage"]="Yahoo market price/history; physical/relative-macro adapters still gated"
    else:
        snap=dict(fetch_yfinance_snapshot(market,symbol,name))
        snap["source_coverage"]="Yahoo market + public company financial metadata"
    snap["external_id"] = external_id
    snap["notes"] = str(r.get("notes") or "")
    snap["refreshed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return snap


def build_snapshot_frame(rows: pd.DataFrame, max_assets: int = 20) -> pd.DataFrame:
    subset = [r for _, r in rows.head(max_assets).iterrows()]
    if not subset:
        return pd.DataFrame()
    snaps: List[Dict[str, Any]] = []
    # Bounded parallelism keeps the refresh fast without flooding free endpoints.
    with ThreadPoolExecutor(max_workers=min(6, len(subset))) as ex:
        futs = [ex.submit(_snapshot_one, r) for r in subset]
        for fut in as_completed(futs):
            try:
                snaps.append(fut.result())
            except Exception as exc:
                snaps.append({"error": str(exc), "data_quality": "LOW"})
    return pd.DataFrame(snaps)


def add_cross_sectional_evidence(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    metrics = ["revenue_growth_yoy","eps_growth_yoy","gross_margin_change","fcf_growth_yoy","net_margin"]
    for m in metrics:
        out[f"{m}_rank"] = np.nan
    # rank within sector where enough peers, else within market
    for idx, r in out.iterrows():
        peers = out[(out["market"]==r["market"]) & (out["sector"]==r["sector"])]
        if len(peers) < 4:
            peers = out[out["market"]==r["market"]]
        for m in metrics:
            out.at[idx,f"{m}_rank"] = percentile_rank(peers[m], safe_float(r[m]))

    evidence_cols = [f"{m}_rank" for m in metrics[:4]]
    out["evidence_families"] = out[evidence_cols].apply(lambda row: int(sum(np.isfinite(v) and v >= 0.75 for v in row)), axis=1)
    out["deterioration_families"] = out[evidence_cols].apply(lambda row: int(sum(np.isfinite(v) and v <= 0.25 for v in row)), axis=1)

    def stage(n: int, d: int) -> str:
        if n >= 4: return "HIGH-CONVICTION CANDIDATE"
        if n >= 3: return "CONFIRMED INFLECTION"
        if n >= 2: return "WATCH"
        if d >= 3: return "DETERIORATION WATCH"
        return "DISCOVERED / NEEDS MORE EVIDENCE"
    out["stage"] = [stage(int(n),int(d)) for n,d in zip(out["evidence_families"],out["deterioration_families"])]
    return out


def sector_multiple_bands(scan: pd.DataFrame, row: pd.Series) -> Tuple[float,float,float]:
    peers = scan[(scan["market"]==row["market"]) & (scan["sector"]==row["sector"]) & (scan["trailing_pe"]>0) & (scan["trailing_pe"]<200)]
    if len(peers) < 4:
        peers = scan[(scan["market"]==row["market"]) & (scan["trailing_pe"]>0) & (scan["trailing_pe"]<200)]
    return robust_quantiles(peers["trailing_pe"].tolist())


def scenario_growth_bands(row: pd.Series) -> Tuple[float,float,float]:
    # transparent, non-fitted projection anchor: combine revenue & EPS current YoY,
    # then use wide scenario dispersion. This is a research projection, not production.
    vals = [safe_float(row.get("revenue_growth_yoy")), safe_float(row.get("eps_growth_yoy")), safe_float(row.get("fcf_growth_yoy"))]
    vals = [v for v in vals if np.isfinite(v) and -0.95 < v < 5.0]
    if not vals:
        return (-0.15, 0.05, 0.25)
    med = float(np.median(vals))
    spread = max(0.15, float(np.std(vals)) if len(vals)>1 else 0.25)
    # cap only to prevent nonsensical arithmetic, not to optimize backtest
    bear = clamp(med-spread, -0.75, 2.0)
    base = clamp(med, -0.50, 2.5)
    bull = clamp(med+spread, -0.25, 4.0)
    return bear,base,bull


def valuation_projection(scan: pd.DataFrame, row: pd.Series) -> Dict[str, Any]:
    pe25,pemed,pe75 = sector_multiple_bands(scan,row)
    eps = safe_float(row.get("eps_ttm")); price=safe_float(row.get("price"))
    g_bear,g_base,g_bull = scenario_growth_bands(row)
    out = {"pe25":pe25,"pemed":pemed,"pe75":pe75,"g_bear":g_bear,"g_base":g_base,"g_bull":g_bull}
    if not np.isfinite(eps) or eps <= 0 or not np.isfinite(price) or not np.isfinite(pemed):
        out.update({"bear_eps":np.nan,"base_eps":np.nan,"bull_eps":np.nan,"fv_bear":np.nan,"fv_base":np.nan,"fv_bull":np.nan,"implied_eps":np.nan,"expectation_gap":np.nan})
        return out
    bear_eps = eps*(1+g_bear); base_eps=eps*(1+g_base); bull_eps=eps*(1+g_bull)
    # Cross-sectional multiple bands make the assumptions visible and comparable.
    fv_bear = max(0,bear_eps)*pe25 if np.isfinite(pe25) else np.nan
    fv_base = max(0,base_eps)*pemed if np.isfinite(pemed) else np.nan
    fv_bull = max(0,bull_eps)*pe75 if np.isfinite(pe75) else np.nan
    implied_eps = price/pemed if pemed>0 else np.nan
    gap = (base_eps-implied_eps)/abs(implied_eps) if np.isfinite(implied_eps) and implied_eps!=0 else np.nan
    out.update({"bear_eps":bear_eps,"base_eps":base_eps,"bull_eps":bull_eps,"fv_bear":fv_bear,"fv_base":fv_base,"fv_bull":fv_bull,"implied_eps":implied_eps,"expectation_gap":gap})
    return out


def action_from_relative_rank(scan: pd.DataFrame) -> pd.DataFrame:
    out = scan.copy()
    gaps=[]
    for _,r in out.iterrows():
        gaps.append(valuation_projection(out,r).get("expectation_gap",np.nan))
    out["expectation_gap"] = gaps
    out["gap_rank"] = out.groupby("market")["expectation_gap"].rank(pct=True)
    actions=[]
    for _,r in out.iterrows():
        n=int(r.get("evidence_families",0)); d=int(r.get("deterioration_families",0)); gr=safe_float(r.get("gap_rank")); market=str(r.get("market"))
        if d>=3 and np.isfinite(gr) and gr<=0.25:
            action = "SELL / AVOID" if market=="IHSG" else ("SHORT / PUT CANDIDATE" if market=="US" else "BEARISH CANDIDATE")
        elif n>=3 and np.isfinite(gr) and gr>=0.80:
            action = "BUILD CANDIDATE"
        elif n>=2 and np.isfinite(gr) and gr>=0.60:
            action = "SELECTIVE ADD / WATCH"
        elif n>=2:
            action = "HOLD / NEEDS BETTER PRICE"
        else:
            action = "WATCH / NO FORCED TRADE"
        actions.append(action)
    out["research_action"] = actions
    return out


def deep_crypto_metrics(symbol_row: pd.Series) -> Dict[str, Any]:
    cid = str(symbol_row.get("external_id") or "")
    j = fetch_coingecko(cid)
    if not j:
        return {}
    md = j.get("market_data",{}) or {}
    mcap = safe_float((md.get("market_cap",{}) or {}).get("usd"))
    fdv = safe_float((md.get("fully_diluted_valuation",{}) or {}).get("usd"))
    circ = safe_float(md.get("circulating_supply")); total=safe_float(md.get("total_supply")); maxs=safe_float(md.get("max_supply"))
    slug = cid
    revenue = fetch_defillama_revenue(slug)
    rev30 = float(revenue.iloc[-30:].sum()) if len(revenue)>=30 else np.nan
    prev30 = float(revenue.iloc[-60:-30].sum()) if len(revenue)>=60 else np.nan
    rev_growth = rev30/prev30-1 if np.isfinite(rev30) and np.isfinite(prev30) and prev30>0 else np.nan
    annualized = rev30*12 if np.isfinite(rev30) else np.nan
    return {
        "market_cap":mcap,"fdv":fdv,"fdv_premium":fdv/mcap-1 if mcap>0 and np.isfinite(fdv) else np.nan,
        "circulating_supply":circ,"total_supply":total,"max_supply":maxs,
        "circulating_ratio":circ/maxs if np.isfinite(circ) and np.isfinite(maxs) and maxs>0 else np.nan,
        "revenue_30d":rev30,"revenue_growth_30d":rev_growth,"annualized_revenue":annualized,
        "mcap_to_revenue":mcap/annualized if mcap>0 and annualized>0 else np.nan,
    }


def news_evidence(query: str, limit: int = 15) -> Dict[str, Any]:
    items = google_news_rss(query,limit=limit)
    themes=Counter(); titles=[]; sources=set()
    for it in items:
        titles.append(it["title"]); sources.add(it.get("source") or "Unknown")
        for th in classify_headline(it["title"]): themes[th]+=1
    return {"items":items,"themes":themes,"titles":titles,"sources":sources}


def adaptive_scenario_branches(root: str) -> pd.DataFrame:
    """Return scenario branches relevant to the inferred causal root.
    Branches are hypotheses with trigger/action/falsifier, never numeric probabilities.
    """
    if TEMPLATES.empty:
        return pd.DataFrame()
    r=(root or "").lower()
    names=[]
    if any(k in r for k in ["supply","nand","memory","cpo","electrical","transformer","network","photon","cooling","bottleneck"]):
        names=["Bottleneck persists","Bottleneck worsens","Supply catches up","Substitution","Policy intervention","Demand destruction","Capex response creates new bottleneck"]
    elif any(k in r for k in ["war","oil","shipping"]):
        names=["Event escalation","Event normalization","Policy intervention","Demand destruction","Capex response creates new bottleneck"]
    elif any(k in r for k in ["protocol","token","private asset","scarcity"]):
        # Reuse generic templates where mechanisms map cleanly; extra crypto-specific
        # branches are generated below without a hard-coded winner/ticker.
        extra=pd.DataFrame([
            {"scenario":"Value capture strengthens","trigger":"External usage/revenue rises while buyback/burn/distribution grows and dilution falls","economic_projection":"Net holder accrual accelerates","action_logic":"BUILD/ADD only if market-implied growth still trails the economic projection","falsifier":"Revenue decouples from holder capture or dilution offsets accrual"},
            {"scenario":"Usage grows but token capture fails","trigger":"Users/fees rise without holder economics","economic_projection":"Protocol may win while token does not","action_logic":"NO ADD / rotate to better value-capture expression","falsifier":"Direct capture mechanism becomes durable"},
            {"scenario":"Dilution / unlock shock","trigger":"Emission or unlock schedule overwhelms organic demand","economic_projection":"Net token accrual turns negative","action_logic":"TRIM / SELL; leverage short only after liquidity/risk gate","falsifier":"Unlock absorbed while usage/capture accelerates"},
            {"scenario":"Usage-scarcity breakout","trigger":"Real usage rises while effective liquid float / issuance tightens","economic_projection":"Scarcity premium can expand","action_logic":"BUILD if adoption is real and valuation is not already pricing the bull case","falsifier":"Usage is mostly speculative or effective float rises"},
        ])
        base=TEMPLATES[TEMPLATES["scenario"].isin(["Substitution","Policy intervention","Demand destruction"])].copy()
        return pd.concat([extra,base],ignore_index=True)
    elif any(k in r for k in ["intervention","currency"]):
        return pd.DataFrame([
            {"scenario":"Intervention executes","trigger":"Official escalation + disorderly move + policy capacity converge","economic_projection":"Sharp FX reversal risk; carry may delever","action_logic":"Prefer defined-risk short/hedge expression; do not wait for macro confirmation after execution","falsifier":"Authorities step back or move stabilizes"},
            {"scenario":"No intervention / tolerance continues","trigger":"Currency remains weak but speed/volatility eases or rhetoric softens","economic_projection":"Carry/relative-macro trend can persist","action_logic":"Do not front-run intervention solely from a price level","falsifier":"Official escalation or coordinated action rises"},
            {"scenario":"Intervention spills into carry unwind","trigger":"FX reversal collides with crowded leverage","economic_projection":"Cross-asset volatility and deleveraging rise","action_logic":"Cut leverage / fragile risk; favor liquidity","falsifier":"Positioning is light and funding stays stable"},
        ])
    else:
        names=["Bottleneck persists","Supply catches up","Policy intervention","Demand destruction","Event escalation","Event normalization"]
    return TEMPLATES[TEMPLATES["scenario"].isin(names)].copy()


def infer_root_from_evidence(name: str, evidence: Dict[str,Any]) -> str:
    themes=evidence.get("themes",Counter())
    if themes:
        th=themes.most_common(1)[0][0]
        return THEME_ROOT.get(th,th)
    candidates=find_root_candidates(name)
    return candidates[0] if candidates else ""



# -----------------------------
# Decision-view helpers
# -----------------------------
ACTION_TIER = {
    "BUILD CANDIDATE": 5,
    "SELECTIVE ADD / WATCH": 4,
    "HOLD / NEEDS BETTER PRICE": 3,
    "WATCH / NO FORCED TRADE": 2,
    "SHORT / PUT CANDIDATE": 4,
    "SELL / AVOID": 4,
    "BEARISH CANDIDATE": 4,
}


def rank_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Research ordering only; not a return probability or production score."""
    if df.empty:
        return df
    out=df.copy()
    out["_action_tier"]=out.get("research_action",pd.Series(index=out.index,dtype=object)).map(ACTION_TIER).fillna(1)
    out["_evidence"]=pd.to_numeric(out.get("evidence_families",0),errors="coerce").fillna(0)
    out["_gap"]=pd.to_numeric(out.get("gap_rank",np.nan),errors="coerce").fillna(-1)
    out["_quality"]=out.get("data_quality",pd.Series(index=out.index,dtype=object)).map({"HIGH":2,"MEDIUM":1,"LOW":0}).fillna(0)
    return out.sort_values(["_action_tier","_evidence","_gap","_quality"],ascending=False)


def infer_specific_root(name: str, symbol: str, evidence: Dict[str,Any]) -> str:
    text=" ".join(evidence.get("titles",[])).lower()+" "+str(name).lower()+" "+str(symbol).lower()
    generic = infer_root_from_evidence(name,evidence)
    # Generic causal-domain routing; never keyed to acceptance-test tickers.
    routes=[
        (["nand","flash memory","enterprise ssd","ssd demand","memory shortage","flash storage"],"NAND / enterprise SSD demand"),
        (["transformer","switchgear","grid interconnection","power demand","data center power","datacenter power"],"Electrical load"),
        (["photonics","optical transceiver","co-packaged optics","cpo optics","laser interconnect","network bandwidth"],"Networking bandwidth"),
        (["palm oil","cpo price","biodiesel","edible oil"],"CPO price"),
        (["tanker","shipping lane","strait","oil supply disruption","war risk"],"War escalation"),
        (["shielded","privacy coin","private transactions","zcash"],"Private asset usage"),
        (["token buyback","buy and burn","protocol revenue","tokenholder revenue","fees revenue"],"Protocol usage"),
        (["yen intervention","currency intervention","verbal intervention","disorderly fx"],"Currency depreciation speed"),
    ]
    for terms,root in routes:
        if any(t in text for t in terms):
            return root
    return generic


def scenario_horizon(theme: str, novelty: str) -> str:
    t=(theme or "").lower()
    if "novel" in (novelty or "").lower(): return "BREWING / RESEARCH"
    if any(k in t for k in ["war","shipping","fx intervention","credit","funding"]): return "NOW–1Q"
    if any(k in t for k in ["supply bottleneck","data-center power","commodity scarcity","policy / fiscal"]): return "1–2Q"
    if any(k in t for k in ["photonics","consumer inflection","crypto value","crypto usage"]): return "1–2Q"
    return "1–2Q"


def filtered_scenarios(discovered: pd.DataFrame, max_rows: int=3) -> pd.DataFrame:
    """Only show live, sufficiently-supported scenarios. No fake numeric probabilities."""
    if discovered.empty: return discovered
    d=discovered.copy()
    d["evidence_count"]=pd.to_numeric(d["evidence_count"],errors="coerce").fillna(0)
    d["source_count"]=pd.to_numeric(d["source_count"],errors="coerce").fillna(0)
    mapped=d[(d["novelty"]=="MAPPED") & (d["evidence_count"]>=3) & (d["source_count"]>=3)].copy()
    novel=d[(d["novelty"]!="MAPPED") & (d["evidence_count"]>=7) & (d["source_count"]>=4)].copy()
    d=pd.concat([mapped,novel],ignore_index=True)
    if d.empty: return d
    if "discovery_rank" in d.columns: d=d.sort_values(["discovery_rank","source_count"],ascending=False)
    else: d=d.sort_values(["evidence_count","source_count"],ascending=False)
    d["horizon"]=[scenario_horizon(str(a),str(b)) for a,b in zip(d["theme"],d["novelty"])]
    return d.head(max_rows)


def chain_brief(root: str) -> Dict[str,Any]:
    ch=expand_chain(root,depth=4,max_edges=70) if root else pd.DataFrame()
    if ch.empty:
        return {"chain":ch,"direct":[],"bottlenecks":[],"losers":[],"normalization":[]}
    direct=ch[ch["role"].isin(["DIRECT","SECOND"])]["target"].astype(str).drop_duplicates().tolist()
    bott=ch[ch["role"].astype(str).str.contains("BOTTLENECK|CONDITIONAL",case=False,regex=True,na=False)]["target"].astype(str).drop_duplicates().tolist()
    losers=ch[ch["role"].astype(str).str.upper().eq("LOSER")]["target"].astype(str).drop_duplicates().tolist()
    normal=ch[ch["role"].astype(str).str.upper().eq("NORMALIZATION")]["target"].astype(str).drop_duplicates().tolist()
    return {"chain":ch,"direct":direct,"bottlenecks":bott,"losers":losers,"normalization":normal}


def _tokens(text: str) -> set:
    stop={"data","center","chain","acceptance","test","only","live","scanner","market","demand","supply","producer","direct","second","third","power"}
    return {x for x in re.findall(r"[a-z0-9]+",str(text).lower()) if len(x)>=4 and x not in stop}


def exposed_assets_from_chain(root: str, selected_symbol: str="", limit: int=8) -> pd.DataFrame:
    """Map causal nodes to the seeded universe by transparent text overlap; this is candidate exposure, not a buy call."""
    info=chain_brief(root)
    ch=info["chain"]
    if ch.empty or UNIVERSE.empty: return pd.DataFrame()
    corpus=" ".join(ch["target"].astype(str).tolist()+ch["source"].astype(str).tolist()+ch["mechanism"].astype(str).tolist())
    ctok=_tokens(corpus)
    rows=[]
    for _,r in UNIVERSE.iterrows():
        text=" ".join([str(r.get("name","")),str(r.get("notes",""))])
        overlap=len(ctok & _tokens(text))
        if overlap>0 or str(r.get("symbol",""))==selected_symbol:
            rows.append({"market":r.get("market"),"symbol":r.get("symbol"),"name":r.get("name"),"exposure_matches":overlap,"notes":r.get("notes","")})
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["exposure_matches"],ascending=False).head(limit)


def merge_scanned_actions(exposed: pd.DataFrame, scan: pd.DataFrame) -> pd.DataFrame:
    if exposed.empty: return exposed
    out=exposed.copy()
    if scan.empty:
        out["research_action"]="NOT SCANNED"
        out["price"]=np.nan
        out["data_quality"]="—"
        return out
    cols=[c for c in ["symbol","research_action","price","data_quality","stage"] if c in scan.columns]
    return out.merge(scan[cols].drop_duplicates("symbol"),on="symbol",how="left").fillna({"research_action":"NOT SCANNED","data_quality":"—","stage":"—"})


def opportunity_thesis_summary(row: pd.Series, evidence: Dict[str,Any], root: str) -> str:
    themes=[k for k,_ in evidence.get("themes",Counter()).most_common(2)]
    if root:
        base=f"Causal root: {root}."
    else:
        base="No mapped causal root yet."
    if themes:
        base += " Live evidence: " + ", ".join(themes) + "."
    if int(safe_float(row.get("evidence_families")) if np.isfinite(safe_float(row.get("evidence_families"))) else 0)>=2:
        base += " Multiple fundamental evidence families are improving."
    else:
        base += " Fundamental confirmation is still incomplete."
    return base


def price_in_label(val: Dict[str,Any]) -> Tuple[str,str]:
    gap=safe_float(val.get("expectation_gap"))
    if not np.isfinite(gap): return "UNKNOWN / GATED","gray"
    if gap>=0.35: return "MARKET MAY UNDERPRICE BASE CASE","green"
    if gap>=0.10: return "SOME POSITIVE GAP","green"
    if gap>-0.15: return "ROUGHLY PRICED","amber"
    return "EXPECTATIONS LOOK RICH","red"

def parallel_driver_root(root: str) -> str:
    r=(root or "").lower()
    if any(k in r for k in ["nand","enterprise ssd","electrical load","networking bandwidth","photon"]):
        return "AI adoption"
    if any(k in r for k in ["oil supply","shipping","war escalation"]):
        return "War escalation"
    return ""

# -----------------------------
# Auto-decision / expression helpers
# -----------------------------
AUTO_REFRESH_SECONDS = 1800  # 30 minutes


@st.cache_data(ttl=900, show_spinner=False)
def fetch_option_snapshot(symbol: str, direction: str = "CALL") -> Dict[str, Any]:
    """Fetch one liquid-ish near-ATM option snapshot for expression research.
    This is NOT a technical signal and NOT an option-pricing alpha model.
    """
    if yf is None:
        return {"error": "yfinance unavailable"}
    try:
        t = yf.Ticker(symbol)
        expiries = list(getattr(t, "options", []) or [])
        if not expiries:
            return {"error": "no listed options"}
        now = pd.Timestamp.now(tz="UTC").tz_localize(None)
        choices = []
        for e in expiries:
            d = pd.to_datetime(e, errors="coerce")
            if pd.isna(d):
                continue
            days = (d - now.normalize()).days
            if 21 <= days <= 150:
                choices.append((abs(days-60), days, e))
        if not choices:
            for e in expiries[:4]:
                d = pd.to_datetime(e, errors="coerce")
                if pd.isna(d):
                    continue
                days = max(1, (d - now.normalize()).days)
                choices.append((abs(days-60), days, e))
        if not choices:
            return {"error": "no usable expiry"}
        _, days, expiry = sorted(choices)[0]
        chain = t.option_chain(expiry)
        tab = chain.calls if direction.upper()=="CALL" else chain.puts
        if tab is None or tab.empty:
            return {"error": "empty option chain"}
        hist = t.history(period="5d", auto_adjust=True, actions=False)
        spot = safe_float(hist["Close"].dropna().iloc[-1]) if hist is not None and not hist.empty else np.nan
        x = tab.copy()
        x["strike"] = pd.to_numeric(x["strike"], errors="coerce")
        if np.isfinite(spot):
            x["dist"] = (x["strike"]-spot).abs()
            x = x.sort_values("dist")
        row = x.iloc[0]
        bid=safe_float(row.get("bid")); ask=safe_float(row.get("ask")); last=safe_float(row.get("lastPrice"))
        mid=(bid+ask)/2 if np.isfinite(bid) and np.isfinite(ask) and ask>=bid and ask>0 else last
        spread=(ask-bid)/mid if np.isfinite(mid) and mid>0 and np.isfinite(bid) and np.isfinite(ask) else np.nan
        iv=safe_float(row.get("impliedVolatility"))
        oi=safe_float(row.get("openInterest")); vol=safe_float(row.get("volume"))
        implied_move=iv*np.sqrt(max(days,1)/365.0) if np.isfinite(iv) else np.nan
        liquid = bool((np.isfinite(spread) and spread <= .12) and (np.isfinite(oi) and oi >= 50))
        return {
            "symbol":symbol,"direction":direction.upper(),"expiry":expiry,"days":days,"spot":spot,
            "strike":safe_float(row.get("strike")),"bid":bid,"ask":ask,"mid":mid,"spread":spread,
            "iv":iv,"open_interest":oi,"volume":vol,"implied_move":implied_move,
            "liquidity":"PASS" if liquid else "WEAK / CHECK MANUALLY","error":""
        }
    except Exception as exc:
        return {"error": str(exc)}


def _scan_age_seconds() -> float:
    raw=st.session_state.get("intel_refreshed_at_utc")
    if not raw:
        return np.inf
    try:
        dt=pd.Timestamp(raw)
        if dt.tzinfo is None:
            dt=dt.tz_localize("UTC")
        return float((pd.Timestamp.now(tz="UTC")-dt).total_seconds())
    except Exception:
        return np.inf


def _run_intelligence(scan_input: pd.DataFrame, scan_signature: Tuple[Any,...], max_assets: int, force: bool=False) -> None:
    """Automatic, bounded refresh. Cache TTLs prevent endpoint hammering."""
    if force:
        for _fn in [fetch_yfinance_snapshot,fetch_price_only_snapshot,fetch_coingecko,fetch_defillama_revenue,google_news_rss,discover_live_scenarios,fetch_option_snapshot]:
            try: _fn.clear()
            except Exception: pass
    try:
        safe_compute_macro_gate_snapshot(refresh=force)
    except Exception as exc:
        st.session_state["macro_refresh_error"] = str(exc)
    fresh=build_snapshot_frame(scan_input,max_assets=max_assets) if not scan_input.empty else pd.DataFrame()
    if not fresh.empty:
        try:
            fresh=action_from_relative_rank(add_cross_sectional_evidence(fresh))
        except Exception as exc:
            fresh["error"]=fresh.get("error","")
            fresh["stage"]="DISCOVERED / NEEDS MORE EVIDENCE"
            fresh["research_action"]="WATCH / NO FORCED TRADE"
            fresh["evidence_families"]=0
            fresh["deterioration_families"]=0
            fresh["gap_rank"]=np.nan
            fresh["expectation_gap"]=np.nan
            st.session_state["scan_repair_error"]=str(exc)
    try:
        scen=discover_live_scenarios(max_queries=8)
    except Exception as exc:
        scen=pd.DataFrame()
        st.session_state["scenario_refresh_error"]=str(exc)
    st.session_state["live_scan_records"]=fresh.to_dict("records") if not fresh.empty else []
    st.session_state["live_scan_signature"]=scan_signature
    st.session_state["scenario_discovery_records"]=scen.to_dict("records") if not scen.empty else []
    st.session_state["intel_refreshed_at_utc"]=datetime.now(timezone.utc).isoformat(timespec="seconds")


def _macro_allows_long_leverage(mg: Dict[str,Any]) -> bool:
    label=str(mg.get("action_label","")).upper()
    crash=str(mg.get("crash_state","")).upper()
    return not any(k in label for k in ["DEFENSIVE","CRISIS"]) and "CRASH DANGER" not in crash


def _expression_tables(ranked: pd.DataFrame, mg: Dict[str,Any]) -> Dict[str,pd.DataFrame]:
    if ranked.empty:
        empty=pd.DataFrame()
        return {"buyhold":empty,"spot":empty,"leverage":empty,"options":empty,"radar":empty}
    out=ranked.copy()
    action=out.get("research_action",pd.Series(index=out.index,dtype=str)).fillna("").astype(str)
    qual=out.get("data_quality",pd.Series(index=out.index,dtype=str)).fillna("LOW").astype(str)
    ev=pd.to_numeric(out.get("evidence_families",0),errors="coerce").fillna(0)
    det=pd.to_numeric(out.get("deterioration_families",0),errors="coerce").fillna(0)
    gap=pd.to_numeric(out.get("expectation_gap",np.nan),errors="coerce")

    # Long-duration stock ownership: only US/IHSG, no short/leverage assumption.
    buyhold=out[out["market"].isin(["US","IHSG"]) & action.str.contains("BUILD|SELECTIVE ADD|HOLD",regex=True,na=False)].copy()
    if not buyhold.empty:
        buyhold["expression"]=["BUY / BUILD" if "BUILD" in a else ("ACCUMULATE" if "SELECTIVE" in a else "HOLD / WAIT BETTER PRICE") for a in buyhold["research_action"].astype(str)]

    # Cash/spot expressions for non-stock markets. No forced trade if causal confirmation is weak.
    spot=out[out["market"].isin(["Crypto","FX","Commodity"]) & action.str.contains("BUILD|SELECTIVE ADD|HOLD|BEARISH",regex=True,na=False)].copy()
    if not spot.empty:
        spot["expression"]=["SPOT LONG" if any(k in a for k in ["BUILD","SELECTIVE ADD"]) else ("SPOT / CASH HOLD" if "HOLD" in a else "BEARISH / AVOID") for a in spot["research_action"].astype(str)]

    # Leverage is earned, never the default. IHSG excluded by user constraint.
    long_ok=action.str.contains("BUILD",na=False) & (ev>=3) & qual.eq("HIGH") & _macro_allows_long_leverage(mg)
    short_ok=action.str.contains("SHORT|SELL|BEARISH",regex=True,na=False) & (det>=3) & qual.eq("HIGH")
    lev=out[(out["market"]!="IHSG") & (long_ok|short_ok)].copy()
    if not lev.empty:
        lev["expression"]=["LEVERAGED LONG" if "BUILD" in a else "LEVERAGED SHORT" for a in lev["research_action"].astype(str)]
        lev["risk_gate"]="EARNED / RESEARCH"

    # Options are a directional thesis shortlist; live IV/liquidity is fetched only for the selected detail.
    opt=out[(out["market"]=="US") & ((action.str.contains("BUILD",na=False) & (ev>=3) & qual.eq("HIGH")) | (action.str.contains("SHORT|SELL",regex=True,na=False) & (det>=3) & qual.eq("HIGH")))].copy()
    if not opt.empty:
        opt["expression"]=["CALL CANDIDATE" if "BUILD" in a else "PUT CANDIDATE" for a in opt["research_action"].astype(str)]
        opt["option_edge"]="CHECK LIVE IV / LIQUIDITY"

    radar=out[~out.index.isin(pd.concat([buyhold,spot,lev,opt],axis=0).index if any(not x.empty for x in [buyhold,spot,lev,opt]) else [])].copy()
    radar=radar.head(12)
    return {"buyhold":buyhold,"spot":spot,"leverage":lev,"options":opt,"radar":radar}


def _display_scoreboard(df: pd.DataFrame, kind: str) -> None:
    if df.empty:
        st.markdown(f"<div class='gate'><b>NO QUALIFIED {kind.upper()} OPPORTUNITY RIGHT NOW.</b> The engine does not manufacture a trade when evidence, valuation or data coverage is insufficient.</div>",unsafe_allow_html=True)
        return
    rows=[]
    for _,r in df.head(10).iterrows():
        val=valuation_projection(df,r) if str(r.get("market")) in ["US","IHSG"] else {}
        pin,_=price_in_label(val)
        rows.append({
            "market":r.get("market"),"symbol":r.get("symbol"),"name":r.get("name"),
            "ACTION":r.get("expression",r.get("research_action")),"stage":r.get("stage"),
            "price":r.get("price"),"price-in":pin if val else "asset-class model",
            "evidence":r.get("evidence_families"),"data":r.get("data_quality")
        })
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)


def _render_opportunity_detail(row: pd.Series, ranked: pd.DataFrame, mg: Dict[str,Any], view_kind: str) -> None:
    query=f"{row.get('name','')} {row.get('symbol','')} shortage capacity pricing adoption revenue contract backlog demand supply buyback burn intervention"
    ev=news_evidence(query,limit=8)
    root=infer_specific_root(str(row.get("name","")),str(row.get("symbol","")),ev)
    val=valuation_projection(ranked,row) if str(row.get("market")) in ["US","IHSG"] else {}
    pin,pintone=price_in_label(val)
    action=str(row.get("expression",row.get("research_action","WATCH")))
    atone="green" if any(x in action for x in ["BUILD","LONG","CALL","ACCUMULATE"]) else ("red" if any(x in action for x in ["SELL","SHORT","PUT","BEARISH"]) else "amber")
    st.markdown(f"<div class='action'><div class='kicker'>ACTION NOW</div><h3 style='color:{COLORS[atone][0]}'>{action}</h3><p>{opportunity_thesis_summary(row,ev,root)}<br><b>Stage:</b> {row.get('stage','—')} · <b>Data:</b> {row.get('data_quality','—')} · <b>Price-in:</b> {pin}</p></div>",unsafe_allow_html=True)

    if str(row.get("market")) in ["US","IHSG"]:
        proj=pd.DataFrame([
            ["Bear",pct(val.get("g_bear",np.nan)),fmt_num(val.get("bear_eps",np.nan),2),fmt_money(val.get("fv_bear",np.nan))],
            ["Base",pct(val.get("g_base",np.nan)),fmt_num(val.get("base_eps",np.nan),2),fmt_money(val.get("fv_base",np.nan))],
            ["Bull",pct(val.get("g_bull",np.nan)),fmt_num(val.get("bull_eps",np.nan),2),fmt_money(val.get("fv_bull",np.nan))],
        ],columns=["Scenario","Earnings-power change","Projected NTM EPS","Research FV"])
        st.markdown("**Projection / what today's price already assumes**")
        st.dataframe(proj,use_container_width=True,hide_index=True)
        st.caption(f"Current price implies ~{fmt_num(val.get('implied_eps',np.nan),2)} EPS at the scanned peer median multiple; base projection ~{fmt_num(val.get('base_eps',np.nan),2)}. Research expectation gap {pct(val.get('expectation_gap',np.nan))}. Fair value remains a transparent research range until PIT/OOS validation passes.")
    elif str(row.get("market"))=="Crypto":
        urow=UNIVERSE[UNIVERSE["symbol"]==row.get("symbol")]
        cm=deep_crypto_metrics(urow.iloc[0]) if not urow.empty else {}
        if cm:
            st.markdown("**Crypto economic projection inputs**")
            st.dataframe(pd.DataFrame([{
                "Market cap":fmt_money(cm.get("market_cap",np.nan)),"FDV premium":pct(cm.get("fdv_premium",np.nan)),
                "30D revenue":fmt_money(cm.get("revenue_30d",np.nan)),"Revenue acceleration":pct(cm.get("revenue_growth_30d",np.nan)),
                "Mcap / annualized revenue":fmt_num(cm.get("mcap_to_revenue",np.nan),1)+"x"
            }]),use_container_width=True,hide_index=True)
            st.caption("Revenue is not a hard buy rule. Holder capture, dilution/unlocks and real usage must agree before promotion.")
        else:
            st.caption("Crypto economics incomplete → no forced high-conviction trade.")
    else:
        st.caption("Dedicated physical/relative-macro fair-value projection for this asset class is still gated; directional expression is not upgraded without it.")

    branches=adaptive_scenario_branches(root)
    if not branches.empty:
        st.markdown("**Most relevant scenarios — next 1–2Q**")
        st.dataframe(branches[["scenario","trigger","economic_projection","action_logic","falsifier"]].head(3),use_container_width=True,hide_index=True)

    cb=chain_brief(root)
    is_bottleneck=bool(cb.get("bottlenecks")) or any(k in (root or "").lower() for k in ["nand","supply","electrical load","networking bandwidth","cpo price","war escalation","transformer","photon"])
    if is_bottleneck and not cb.get("chain",pd.DataFrame()).empty:
        st.markdown("**Bottleneck → spillover → who gets paid**")
        bc1,bc2,bc3=st.columns(3)
        with bc1: st.markdown(f"<div class='chainbox'><b>Root bottleneck</b><br>{root}<br><br><b>Direct transmission</b><br>{'<br>'.join(cb['direct'][:5]) or '—'}</div>",unsafe_allow_html=True)
        with bc2: st.markdown(f"<div class='chainbox'><b>Next bottleneck</b><br>{'<br>'.join(cb['bottlenecks'][:5]) or 'Not separately mapped yet'}<br><br><b>Normalization</b><br>{'<br>'.join(cb['normalization'][:4]) or 'Capacity/substitution must be monitored'}</div>",unsafe_allow_html=True)
        with bc3: st.markdown(f"<div class='chainbox'><b>Potential losers</b><br>{'<br>'.join(cb['losers'][:6]) or '—'}</div>",unsafe_allow_html=True)
        driver=parallel_driver_root(root) or root
        exposed=merge_scanned_actions(exposed_assets_from_chain(driver,str(row.get("symbol")),limit=10),ranked)
        if not exposed.empty:
            st.caption("Potential beneficiaries from the same root driver. 'Exposed' is not 'buy': each name still passes through its own valuation/action gate.")
            showcols=[c for c in ["market","symbol","name","research_action","price","data_quality","notes"] if c in exposed.columns]
            st.dataframe(exposed[showcols],use_container_width=True,hide_index=True)

    if view_kind=="OPTIONS" and str(row.get("market"))=="US":
        direction="CALL" if "CALL" in action or "BUILD" in str(row.get("research_action")) else "PUT"
        od=fetch_option_snapshot(str(row.get("symbol")),direction)
        st.markdown("**Live option expression check**")
        if od.get("error"):
            st.warning("Option chain unavailable: "+str(od.get("error")))
        else:
            st.dataframe(pd.DataFrame([{
                "Direction":od.get("direction"),"Expiry":od.get("expiry"),"Days":od.get("days"),"Spot":od.get("spot"),
                "Strike":od.get("strike"),"Mid":od.get("mid"),"Bid/ask spread":pct(od.get("spread",np.nan)),
                "IV":pct(od.get("iv",np.nan)),"Implied move":pct(od.get("implied_move",np.nan)),"OI":od.get("open_interest"),"Liquidity":od.get("liquidity")
            }]),use_container_width=True,hide_index=True)
            st.caption("A directional thesis does not automatically mean buy the option. This check only verifies current chain/liquidity/IV context; the option-pricing edge model remains research-gated.")

    if ev.get("items"):
        e=pd.DataFrame(ev["items"])
        st.caption("Latest evidence used for the explanation")
        st.dataframe(e[[c for c in ["source","title","pubDate"] if c in e.columns]].head(4),use_container_width=True,hide_index=True)


# -----------------------------
# UI — AUTO DECISION VIEW
# -----------------------------
st.markdown(
    f"""
<div class='hero'>
 <div class='hero-title'>Opportunity Intelligence Engine</div>
 <div class='sub'>Always-on decision view: macro gate → automatic opportunity discovery → projection / price-in → only relevant scenarios → bottleneck spillover → best expression.</div>
 <div class='legend'>
   {badge('GREEN = qualified / attractive asymmetry','green')}
   {badge('AMBER = watch / priced-in / needs confirmation','amber')}
   {badge('RED = deterioration / short-side','red')}
   {badge('GREY = data/model gated','gray')}
 </div>
 <div class='sub' style='margin-top:5px'>No classic technical indicators. The scanner runs automatically; refresh is optional, not required.</div>
</div>
""",
    unsafe_allow_html=True,
)

markets_available=[m for m in ["US","IHSG","FX","Commodity","Crypto"] if m in set(UNIVERSE.get("market",pd.Series(dtype=str)).astype(str))]
st.sidebar.markdown("## Auto scanner")
selected_markets=st.sidebar.multiselect("Markets",markets_available,default=markets_available)
st.sidebar.markdown(f"{badge('AUTO · ~30 MIN CACHE','green')}",unsafe_allow_html=True)
force_refresh=st.sidebar.button("Refresh now (optional)",use_container_width=True)
st.sidebar.caption("No button is required. First load and market-selection changes scan automatically. Cached public data prevents repeated endpoint hammering.")
with st.sidebar.expander("Data / research gates",expanded=False):
    st.write("Action model", "✅" if PRODUCTION_ACTION_MODEL_VALIDATED else "🔒 research state")
    st.write("Fair value", "✅" if PRODUCTION_FAIR_VALUE_MODEL_VALIDATED else "🔒 research range")
    st.write("Event probability", "✅" if PRODUCTION_EVENT_PROBABILITY_VALIDATED else "🔒 evidence ranking only")
    st.caption("Current public adapters are current-at-fetch, but full PIT production coverage is still being built.")

if selected_markets:
    scan_input=UNIVERSE[UNIVERSE["market"].isin(selected_markets)].copy().reset_index(drop=True)
else:
    scan_input=UNIVERSE.iloc[0:0].copy()
max_assets=len(scan_input)
scan_signature=(tuple(selected_markets),int(max_assets),"v1.5")

# Automatic initial/stale refresh. The user never has to press a scan button.
existing_records=st.session_state.get("live_scan_records",[])
need_auto=(not existing_records) or (st.session_state.get("live_scan_signature")!=scan_signature) or (_scan_age_seconds()>AUTO_REFRESH_SECONDS)
if force_refresh or need_auto:
    reason="manual refresh" if force_refresh else ("first automatic scan" if not existing_records else "automatic refresh")
    with st.spinner(f"{reason}: scanning {max_assets} assets + macro + near-term scenario evidence…"):
        _run_intelligence(scan_input,scan_signature,max_assets=max_assets,force=force_refresh)

# Periodic trigger while an app session stays open. On older Streamlit versions this block is simply skipped.
if hasattr(st,"fragment"):
    @st.fragment(run_every=AUTO_REFRESH_SECONDS)
    def _periodic_refresh_tick():
        if _scan_age_seconds()>AUTO_REFRESH_SECONDS:
            st.session_state["_auto_tick_due"]=True
            try:
                st.rerun(scope="app")
            except TypeError:
                st.rerun()
    _periodic_refresh_tick()

scan=pd.DataFrame(st.session_state.get("live_scan_records",[]))
discovered=pd.DataFrame(st.session_state.get("scenario_discovery_records",[]))
mg=st.session_state.get("macro_gate_snapshot",{}) or {}
ranked=rank_opportunities(scan[scan.get("error",pd.Series(index=scan.index,dtype=str)).fillna("")==""] if not scan.empty and "error" in scan else scan)
expr=_expression_tables(ranked,mg)

nav=st.radio("Workspace",["OPPORTUNITIES","MACRO DETAILS","RESEARCH / REPLAY"],horizontal=True,label_visibility="collapsed",key="decision_nav_v15")

if nav=="MACRO DETAILS":
    safe_render_macro_control_room()

elif nav=="RESEARCH / REPLAY":
    st.markdown("<div class='section'>Research gates / historical replay</div>",unsafe_allow_html=True)
    st.markdown("<div class='gate'>This area is secondary. Daily decisions belong in OPPORTUNITIES. Acceptance cases are frozen tests and may not tune the live rules.</div>",unsafe_allow_html=True)
    with st.expander("Historical acceptance tests",expanded=False):
        st.dataframe(ACCEPTANCE,use_container_width=True,hide_index=True)
        cases=REPLAY["case"].dropna().unique().tolist() if not REPLAY.empty else []
        if cases:
            case=st.selectbox("Replay case",cases,key="replay_case_compact_v15")
            rr=REPLAY[REPLAY["case"]==case]
            st.dataframe(rr[["date","phase","scanner_state","evidence_known_then","causal_chain","source_url"]],use_container_width=True,hide_index=True)
    with st.expander("Data-source registry / known gaps",expanded=True):
        st.dataframe(SOURCE_REGISTRY,use_container_width=True,hide_index=True)
        st.markdown("<div class='gate'><b>Still not production-complete:</b> full PIT SEC/IDX fundamentals + estimate revisions; verified holder-capture/unlock/usage for every crypto; physical inventory/forward-curve data for commodities; CFTC/REER/BoP/policy intervention feeds for FX; and a validated option expected-distribution model. Missing critical fields lower the action state instead of being fabricated.</div>",unsafe_allow_html=True)

else:
    st.markdown("<div class='section'>Macro gate · one-line context</div>",unsafe_allow_html=True)
    if mg:
        event=mg.get("event_override") or "NONE"
        html="<div class='kpis'>"
        html+=kpi("Macro action",str(mg.get("action_label","—")),fmt_num(safe_float(mg.get("action_score")),0)+"/100",str(mg.get("headline","")),str(mg.get("action_tone","gray")))
        html+=kpi("Regime",str(mg.get("regime","—")),"",str(mg.get("regime_human",mg.get("headline",""))),"blue")
        html+=kpi("Crash state",str(mg.get("crash_state","—")),"","Credit: "+str(mg.get("credit_state","—")),str(mg.get("crash_tone","gray")))
        html+=kpi("Event override",str(event),"","Only a material active override is shown.","amber" if event!="NONE" else "green")
        html+="</div>"
        st.markdown(html,unsafe_allow_html=True)

    refreshed=st.session_state.get("intel_refreshed_at_utc","—")
    high=(ranked.get("data_quality",pd.Series(dtype=str))=="HIGH").mean() if not ranked.empty else 0
    st.caption(f"Automatic intelligence refresh UTC: {refreshed} · scanned {len(ranked)}/{max_assets} selected assets · high-quality rows {high:.0%}. Current-at-fetch does not mean complete PIT coverage.")

    st.markdown("<div class='section'>Opportunities · choose the expression, not another scanner</div>",unsafe_allow_html=True)
    view=st.radio("Opportunity type",["BUY & HOLD · STOCKS","SPOT / CASH","LEVERAGED LONG / SHORT","OPTIONS · CALL / PUT","EARLY RADAR"],horizontal=True,key="opp_subview")
    mapkey={"BUY & HOLD · STOCKS":"buyhold","SPOT / CASH":"spot","LEVERAGED LONG / SHORT":"leverage","OPTIONS · CALL / PUT":"options","EARLY RADAR":"radar"}
    key=mapkey[view]
    df=expr[key]
    _display_scoreboard(df,view)

    if not df.empty:
        options=[str(x) for x in df["symbol"].head(10).tolist()]
        selected=st.selectbox("Explain this opportunity",options,key=f"detail_{key}")
        row=df[df["symbol"].astype(str)==selected].iloc[0]
        st.markdown("<div class='section'>Why this exists · projection · scenario · bottleneck spillover</div>",unsafe_allow_html=True)
        _render_opportunity_detail(row,ranked,mg,"OPTIONS" if key=="options" else key.upper())

    # Global near-term scenarios stay compact and automatic; no separate scan tab.
    st.markdown("<div class='section'>Most supported scenarios that can change the above · max 3</div>",unsafe_allow_html=True)
    near=filtered_scenarios(discovered,max_rows=3)
    if near.empty:
        st.markdown("<div class='gate'>No live scenario clears the multi-source evidence gate right now. Nothing is forced into the dashboard.</div>",unsafe_allow_html=True)
    else:
        cards="<div class='grid3'>"
        for i,(_,r) in enumerate(near.iterrows()):
            tone="purple" if "NOVEL" in str(r.get("novelty","")) else ("amber" if any(k in str(r.get("theme","")).lower() for k in ["war","credit","funding","bottleneck","power"]) else "blue")
            cards+=f"<div class='card'><div class='kicker'>{r.get('horizon','1–2Q')}</div><div class='ct' style='margin-top:5px'>{r.get('theme','')}</div><div class='cn'><b>{int(safe_float(r.get('evidence_count')))} mentions / {int(safe_float(r.get('source_count')))} sources</b><br>{r.get('latest_headline','')}<br><span class='muted'>Evidence-ranked scenario, not a fake probability.</span></div></div>"
        cards+="</div>"
        st.markdown(cards,unsafe_allow_html=True)

st.caption("v1.5 Auto Decision View · opportunities appear automatically; causal chains and scenarios are embedded only where they change an action. No classic technical indicators.")

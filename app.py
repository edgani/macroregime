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
# OPPORTUNITY INTELLIGENCE ENGINE v1.2 UNIFIED
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

from macro_embedded import render_macro_control_room

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
    for _, qrow in queries.iterrows():
        all_items.extend(google_news_rss(str(qrow["query"]), limit=10))
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


def build_snapshot_frame(rows: pd.DataFrame, max_assets: int = 20) -> pd.DataFrame:
    snaps = []
    for _, r in rows.head(max_assets).iterrows():
        market, symbol, name = str(r["market"]), str(r["symbol"]), str(r["name"])
        if market == "Crypto":
            # price via yfinance if available, economics via CoinGecko/DefiLlama later
            s = fetch_yfinance_snapshot(market, symbol, name)
        else:
            s = fetch_yfinance_snapshot(market, symbol, name)
        snaps.append(dict(s))
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
# UI header and sidebar
# -----------------------------
st.markdown(
    f"""
<div class='hero'>
 <div class='hero-title'>Opportunity Intelligence Engine</div>
 <div class='sub'>Macro action gate → discover the economic change → trace beneficiary/loser chains → project fundamentals → reverse-engineer what price assumes → choose the expression.</div>
 <div class='legend'>
   {badge('DISCOVERY = high recall','blue')}
   {badge('CONFIRMATION = evidence agreement','green')}
   {badge('CAUTION / priced-in','amber')}
   {badge('Deterioration / adverse','red')}
   {badge('GATED = not proven','gray')}
 </div>
 <div class='sub'><b>No classic technical indicators.</b> Price is used only for valuation context, policy-relevant speed/volatility and replay outcomes.</div>
</div>
""", unsafe_allow_html=True)

markets_available = [m for m in ["US","IHSG","FX","Commodity","Crypto"] if m in set(UNIVERSE.get("market",[]))]
st.sidebar.markdown("### Live scanner")
selected_markets = st.sidebar.multiselect("Markets", markets_available, default=markets_available[:2] + (["Crypto"] if "Crypto" in markets_available else []))
max_assets = st.sidebar.slider("Max assets per scan", 5, 40, 18, 1)
scan_btn = st.sidebar.button("Run / refresh live scan", use_container_width=True, type="primary")
st.sidebar.caption("The app loads first. Network-heavy market scanning runs only when you press the button, so deploy/local startup cannot hang on Yahoo/API calls.")

st.sidebar.markdown("### Research gates")
st.sidebar.write("Action model", "✅" if PRODUCTION_ACTION_MODEL_VALIDATED else "🔒 research state")
st.sidebar.write("Fair value", "✅" if PRODUCTION_FAIR_VALUE_MODEL_VALIDATED else "🔒 transparent research range")
st.sidebar.write("Event probability", "✅" if PRODUCTION_EVENT_PROBABILITY_VALIDATED else "🔒 no fake probabilities")
st.sidebar.caption("Acceptance cases are frozen tests; live rules may not special-case SNDK/PLTR/VVV/ZEC/ADES/JPY.")

# Run a bounded live scan. It can fail gracefully when deployment blocks a source.
if selected_markets:
    scan_universe = UNIVERSE[UNIVERSE["market"].isin(selected_markets)].copy()
else:
    scan_universe = UNIVERSE.iloc[0:0].copy()
# round-robin markets to prevent first market monopolizing limit
parts=[]
per_market=max(1,max_assets//max(1,len(selected_markets))) if selected_markets else max_assets
for m in selected_markets:
    parts.append(scan_universe[scan_universe["market"]==m].head(per_market))
scan_input=pd.concat(parts,ignore_index=True) if parts else scan_universe

scan_signature = (tuple(selected_markets), int(max_assets))
if scan_btn:
    # Clear only the network adapter we are explicitly refreshing.  Do not nuke every app cache.
    try:
        fetch_yfinance_snapshot.clear()
    except Exception:
        pass
    with st.spinner("Scanning public market/fundamental data…"):
        fresh_scan = build_snapshot_frame(scan_input, max_assets=max_assets) if not scan_input.empty else pd.DataFrame()
    st.session_state["live_scan_records"] = fresh_scan.to_dict("records")
    st.session_state["live_scan_signature"] = scan_signature

scan_raw = pd.DataFrame(st.session_state.get("live_scan_records", []))
scan_stale = bool(not scan_raw.empty and st.session_state.get("live_scan_signature") != scan_signature)
if not scan_raw.empty:
    try:
        scan = action_from_relative_rank(add_cross_sectional_evidence(scan_raw))
    except Exception as _scan_err:
        # Old/incomplete session rows should never crash the whole dashboard.
        scan = scan_raw.copy()
        scan["error"] = scan.get("error", "")
        scan["stage"] = scan.get("stage", "DISCOVERED / NEEDS MORE EVIDENCE")
        scan["research_action"] = scan.get("research_action", "WATCH / NO FORCED TRADE")
        scan["evidence_families"] = pd.to_numeric(scan.get("evidence_families", 0), errors="coerce").fillna(0) if isinstance(scan.get("evidence_families", 0), pd.Series) else 0
        scan["gap_rank"] = np.nan
        scan["expectation_gap"] = np.nan
        st.warning(f"Live scan schema was repaired from an older/incomplete session snapshot: {_scan_err}")
else:
    scan = pd.DataFrame()

# -----------------------------
# Tabs
# -----------------------------
NAV_OPTIONS = [
    "MACRO + ACTION",
    "OPPORTUNITY CONTROL ROOM",
    "CAUSAL CHAINS",
    "AUTO SCENARIO DISCOVERY",
    "HISTORICAL REPLAY",
    "RESEARCH / GATES",
]
nav = st.radio(
    "Workspace",
    NAV_OPTIONS,
    horizontal=True,
    label_visibility="collapsed",
    key="unified_workspace",
)

if nav == "MACRO + ACTION":
    render_macro_control_room()

elif nav == "OPPORTUNITY CONTROL ROOM":
    _mg = st.session_state.get("macro_gate_snapshot")
    if _mg:
        _tone = _mg.get("action_tone", "gray")
        _event = _mg.get("event_override") or "None"
        st.markdown(
            "<div class='panel'><div class='ptitle'>MACRO GATE → OPPORTUNITY EXPRESSION</div>"
            f"<div class='kpis'>"
            f"{kpi('Macro action', _mg.get('action_label','—'), fmt_num(safe_float(_mg.get('action_score')),0)+'/100', _mg.get('headline',''), _tone)}"
            f"{kpi('Macro regime', _mg.get('regime','—'), '', _mg.get('regime_explain',''), 'blue')}"
            f"{kpi('Crash state', _mg.get('crash_state','—'), '', 'Credit: '+str(_mg.get('credit_state','—')), _mg.get('crash_tone','gray'))}"
            f"{kpi('Event override', str(_event), '', 'This can downgrade/alter the preferred expression.', 'amber' if _event != 'None' else 'green')}"
            "</div><div class='gate' style='margin-top:6px'>Macro is a <b>gate and sizing/expression modifier</b>, not a reason to kill a strong secular bottom-up thesis. Refresh it in <b>MACRO + ACTION</b>.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Macro gate has not been loaded in this session yet. Open **MACRO + ACTION** once; its action state will then flow into this opportunity view.")

    st.markdown("<div class='section'>What should I look at now?</div>", unsafe_allow_html=True)
    if scan.empty:
        st.info("Scanner ready. Choose markets in the sidebar and press **Run / refresh live scan**. The app intentionally does not hit Yahoo/API endpoints during startup.")
    elif scan_stale:
        st.warning("The displayed scan is from a different market/max-assets selection. Press **Run / refresh live scan** to update it.")
    else:
        usable=scan[scan["error"].fillna("")==""] if "error" in scan else scan
        build_count=int(usable["research_action"].str.contains("BUILD",na=False).sum()) if not usable.empty else 0
        confirmed=int(usable["stage"].str.contains("CONFIRMED|HIGH-CONVICTION",regex=True,na=False).sum()) if not usable.empty else 0
        watch=int(usable["stage"].str.contains("WATCH",na=False).sum()) if not usable.empty else 0
        bad=int(usable["research_action"].str.contains("SELL|SHORT|BEARISH",regex=True,na=False).sum()) if not usable.empty else 0
        quality=(usable["data_quality"]=="HIGH").mean() if not usable.empty else 0
        kpis="<div class='kpis'>"
        kpis+=kpi("Build candidates","HIGH-RECALL / NOT AUTO-BUY",str(build_count),"Need deep causal confirmation before capital.","green" if build_count else "gray")
        kpis+=kpi("Confirmed inflections","EVIDENCE AGREEMENT",str(confirmed),"Independent fundamental families agree.","green" if confirmed else "gray")
        kpis+=kpi("Early radar","WATCH",str(watch),"Designed not to miss early inflections.","blue")
        kpis+=kpi("Deterioration","SHORT / EXIT RADAR",str(bad),"Only actionable after causal + valuation confirmation.","red" if bad else "gray")
        kpis+=kpi("Live data quality","HIGH COVERAGE",f"{quality:.0%}","Per scanned row; grey means source incomplete.","green" if quality>.6 else "amber")
        kpis+=kpi("Technical indicators","OFF","0","No RSI/MACD/MA/oscillator signal path.","green")
        kpis+="</div>"
        st.markdown(kpis,unsafe_allow_html=True)

        display=usable.copy()
        if not display.empty:
            display["rev YoY"] = display["revenue_growth_yoy"].map(lambda x: pct(x))
            display["EPS YoY"] = display["eps_growth_yoy"].map(lambda x: pct(x))
            display["GM Δ"] = display["gross_margin_change"].map(lambda x: pct(x))
            display["gap"] = display["expectation_gap"].map(lambda x: pct(x))
            cols=["market","symbol","name","stage","research_action","price","rev YoY","EPS YoY","GM Δ","gap","data_quality"]
            _sort_cols=[c for c in ["evidence_families","gap_rank"] if c in display.columns]
            _table=display.sort_values(_sort_cols,ascending=[False]*len(_sort_cols)) if _sort_cols else display
            st.dataframe(_table[cols],use_container_width=True,hide_index=True)

            st.markdown("<div class='section'>Deep-dive one candidate</div>", unsafe_allow_html=True)
            symbols=display["symbol"].tolist()
            selected_symbol=st.selectbox("Ticker / asset",symbols,index=0,key="deep_symbol")
            row=display[display["symbol"]==selected_symbol].iloc[0]
            urow=UNIVERSE[UNIVERSE["symbol"]==selected_symbol]
            urow=urow.iloc[0] if not urow.empty else pd.Series(dtype=object)
            val=valuation_projection(display,row)

            left,right=st.columns([1.25,1])
            with left:
                tone="green" if "BUILD" in str(row["research_action"]) else ("red" if any(x in str(row["research_action"]) for x in ["SELL","SHORT","BEARISH"]) else "amber")
                c,_=COLORS[tone]
                st.markdown(f"""
<div class='action'>
 <div class='kicker'>RESEARCH ACTION STATE</div>
 <h3 style='color:{c}'>{row['research_action']}</h3>
 <p><b>{row['name']} ({row['symbol']})</b> · {base_family_from_market(str(row['market']))}<br>
 Stage: <b>{row['stage']}</b> · Data quality: <b>{row['data_quality']}</b><br>
 This is a research state, not a production trade signal until PIT/OOS validation passes.</p>
</div>
""",unsafe_allow_html=True)
                st.markdown("<div class='section'>Fundamental projection / price-in</div>",unsafe_allow_html=True)
                proj=pd.DataFrame([
                    ["Bear",pct(val.get("g_bear",np.nan)),fmt_num(val.get("bear_eps",np.nan),2),fmt_num(val.get("pe25",np.nan),1)+"x",fmt_money(val.get("fv_bear",np.nan))],
                    ["Base",pct(val.get("g_base",np.nan)),fmt_num(val.get("base_eps",np.nan),2),fmt_num(val.get("pemed",np.nan),1)+"x",fmt_money(val.get("fv_base",np.nan))],
                    ["Bull",pct(val.get("g_bull",np.nan)),fmt_num(val.get("bull_eps",np.nan),2),fmt_num(val.get("pe75",np.nan),1)+"x",fmt_money(val.get("fv_bull",np.nan))],
                ],columns=["Scenario","Earnings-power change","Projected NTM EPS","Peer multiple anchor","Research FV"])
                st.dataframe(proj,use_container_width=True,hide_index=True)
                st.markdown(f"""
<div class='gate'><b>Reverse valuation:</b> current price {fmt_money(safe_float(row['price']))} implies roughly <b>{fmt_num(val.get('implied_eps',np.nan),2)} EPS</b> at the scanned peer median multiple. Our data-anchored base projection is <b>{fmt_num(val.get('base_eps',np.nan),2)}</b>. Expectation gap: <b>{pct(val.get('expectation_gap',np.nan))}</b>.<br>
Fair-value bands are deliberately wide and assumption-visible; they are not production validated yet.</div>
""",unsafe_allow_html=True)

            with right:
                st.markdown("<div class='panel'><div class='ptitle'>Why now / what changes the answer</div>",unsafe_allow_html=True)
                reasons=[]
                if safe_float(row.get("revenue_growth_yoy_rank"))>=.75: reasons.append("Revenue growth is top-quartile vs scanned peers")
                if safe_float(row.get("eps_growth_yoy_rank"))>=.75: reasons.append("EPS growth is top-quartile vs scanned peers")
                if safe_float(row.get("gross_margin_change_rank"))>=.75: reasons.append("Gross-margin change is top-quartile vs scanned peers")
                if safe_float(row.get("fcf_growth_yoy_rank"))>=.75: reasons.append("FCF growth is top-quartile vs scanned peers")
                if not reasons: reasons=["Current live fundamentals do not yet show enough independent evidence; stay in discovery mode."]
                for rtext in reasons[:5]: st.markdown(f"<div class='row'><div>{rtext}</div><div class='right'>{badge('EVIDENCE','green')}</div></div>",unsafe_allow_html=True)
                st.markdown(f"<div class='row'><div>What price already assumes</div><div class='right'><b>{fmt_num(val.get('implied_eps',np.nan),2)} EPS @ peer median</b></div></div>",unsafe_allow_html=True)
                st.markdown(f"<div class='row'><div>What would upgrade</div><div class='right'>More independent causal evidence + positive expectation gap</div></div>",unsafe_allow_html=True)
                st.markdown(f"<div class='row'><div>What would downgrade</div><div class='right'>Growth/margin/FCF deterioration or supply/adoption thesis breaks</div></div></div>",unsafe_allow_html=True)

                if str(row["market"])=="Crypto":
                    cm=deep_crypto_metrics(urow)
                    if cm:
                        st.markdown("<div class='section'>Crypto economics</div>",unsafe_allow_html=True)
                        st.markdown(f"""
<div class='panel'>
 <div class='row'><div>Market cap</div><div class='right'><b>{fmt_money(cm.get('market_cap',np.nan))}</b></div></div>
 <div class='row'><div>FDV premium</div><div class='right'><b>{pct(cm.get('fdv_premium',np.nan))}</b></div></div>
 <div class='row'><div>30D protocol revenue</div><div class='right'><b>{fmt_money(cm.get('revenue_30d',np.nan))}</b></div></div>
 <div class='row'><div>Revenue acceleration</div><div class='right'><b>{pct(cm.get('revenue_growth_30d',np.nan))}</b></div></div>
 <div class='row'><div>Mcap / annualized revenue</div><div class='right'><b>{fmt_num(cm.get('mcap_to_revenue',np.nan),1)}x</b></div></div>
 <div class='gate' style='margin-top:6px'>Revenue alone is never enough. Deep confirmation still needs holder capture, dilution/unlocks and usage quality.</div>
</div>
""",unsafe_allow_html=True)

            st.markdown("<div class='section'>Automatic thesis explanation</div>",unsafe_allow_html=True)
            q=f"{row['name']} {row['symbol']} shortage capacity pricing adoption revenue buyback burn contract backlog margin demand supply"
            ev=news_evidence(q,limit=12)
            root=infer_root_from_evidence(str(row['name']),ev)
            ths=", ".join(f"{k} ({v})" for k,v in ev["themes"].most_common(4)) or "No strong mapped live theme yet"
            chain=expand_chain(root,depth=3,max_edges=40) if root else pd.DataFrame()
            st.markdown(f"""
<div class='panel'>
 <div class='row'><div>Detected live themes</div><div class='right'><b>{ths}</b></div></div>
 <div class='row'><div>Inferred causal root</div><div class='right'><b>{root or 'UNMAPPED / needs research'}</b></div></div>
 <div class='row'><div>Why this matters</div><div class='right'>The engine explains the economic chain, not just the ticker.</div></div>
</div>
""",unsafe_allow_html=True)
            if not chain.empty:
                st.dataframe(chain[["source","target","mechanism","sign","lag","role","validation","condition"]].head(30),use_container_width=True,hide_index=True)
            st.markdown("<div class='section'>Adaptive scenario branches + action if confirmed</div>",unsafe_allow_html=True)
            branches=adaptive_scenario_branches(root)
            if not branches.empty:
                st.dataframe(branches[["scenario","trigger","economic_projection","action_logic","falsifier"]],use_container_width=True,hide_index=True)
            else:
                st.caption("No mapped scenario branch yet — keep the thesis in discovery until a causal scenario is defined.")
            if ev["items"]:
                with st.expander("Live evidence headlines"):
                    st.dataframe(pd.DataFrame(ev["items"])[["source","title","pubDate"]],use_container_width=True,hide_index=True)

elif nav == "CAUSAL CHAINS":
    st.markdown("<div class='section'>Chain engine — direct, second-order, third-order and losers</div>",unsafe_allow_html=True)
    presets=[
        "AI adoption","Electrical load","Networking bandwidth","CPO price","War escalation","Protocol usage","Private asset usage","Currency depreciation speed","Consumer mobility recovery"
    ]
    nodes=sorted(set(EDGE_DF["source"].astype(str)) | set(EDGE_DF["target"].astype(str))) if not EDGE_DF.empty else []
    default_idx=nodes.index("AI adoption") if "AI adoption" in nodes else 0
    root=st.selectbox("Root change / bottleneck / shock",nodes,index=default_idx,key="chain_root") if nodes else ""
    depth=st.slider("Propagation depth",1,6,4,key="chain_depth")
    chain=expand_chain(root,depth=depth,max_edges=120)
    if chain.empty:
        st.info("No mapped downstream edges yet. Auto Scenario Discovery can still surface a novel root; add it to the graph only after causal validation.")
    else:
        # compact chain summary by role
        role_counts=chain["role"].value_counts().to_dict()
        khtml="<div class='kpis'>"
        for label,role,tone in [("Direct","DIRECT","green"),("Second order","SECOND","green"),("Third+","THIRD","blue"),("Bottlenecks","BOTTLENECK","amber"),("Losers","LOSER","red"),("Normalization","NORMALIZATION","purple")]:
            khtml+=kpi(label,role,str(role_counts.get(role,0)),"Mapped economic links",tone)
        khtml+="</div>"; st.markdown(khtml,unsafe_allow_html=True)
        fig=chain_plot(chain,root)
        if fig is not None:
            st.plotly_chart(fig,use_container_width=True)
        st.dataframe(chain[["source","target","mechanism","sign","lag","role","validation","condition"]],use_container_width=True,hide_index=True)
        st.markdown("<div class='section'>How to trade the chain</div>",unsafe_allow_html=True)
        direct=chain[chain["role"].isin(["DIRECT","SECOND","THIRD","FOURTH"])]["target"].drop_duplicates().tolist()
        bott=chain[chain["role"].astype(str).str.contains("BOTTLENECK",case=False,na=False)]["target"].drop_duplicates().tolist()
        losers=chain[chain["role"]=="LOSER"]["target"].drop_duplicates().tolist()
        normal=chain[chain["role"]=="NORMALIZATION"]["target"].drop_duplicates().tolist()
        a,b,c=st.columns(3)
        with a:
            st.markdown(f"<div class='panel'><div class='ptitle'>Potential beneficiaries</div><div class='small'>{'<br>'.join(direct[:18]) or '—'}</div></div>",unsafe_allow_html=True)
        with b:
            st.markdown(f"<div class='panel'><div class='ptitle'>Scarcity / next bottleneck nodes</div><div class='small'>{'<br>'.join(bott[:18]) or '—'}</div></div>",unsafe_allow_html=True)
        with c:
            st.markdown(f"<div class='panel'><div class='ptitle'>Losers / later normalization</div><div class='small'><b>Losers</b><br>{'<br>'.join(losers[:10]) or '—'}<br><br><b>Normalization</b><br>{'<br>'.join(normal[:10]) or '—'}</div></div>",unsafe_allow_html=True)

    st.markdown("<div class='section'>Data-center example: not just chips</div>",unsafe_allow_html=True)
    dc=expand_chain("AI adoption",depth=5,max_edges=120)
    if not dc.empty:
        st.dataframe(dc[["source","target","mechanism","role","lag","condition"]],use_container_width=True,hide_index=True)

elif nav == "AUTO SCENARIO DISCOVERY":
    st.markdown("<div class='section'>Automatic scenario discovery — scenario list changes with live evidence</div>",unsafe_allow_html=True)
    st.markdown("<div class='gate'>The engine scans broad causal queries, clusters headlines into known themes, and also surfaces recurring unmapped terms as <b>NOVEL CLUSTERS</b>. A novel cluster is a research hypothesis, not a probability. It must be mapped to a causal chain and falsifier before it can affect action.</div>",unsafe_allow_html=True)
    maxq=st.slider("Broad discovery query families",4,15,10,key="disc_q")
    discover_btn = st.button("Run live scenario discovery", key="run_scenario_discovery", type="primary")
    st.caption("Like the ticker scan, this network-heavy step is manual so the app always renders immediately on local and cloud deploys.")
    if discover_btn:
        try:
            discover_live_scenarios.clear()
        except Exception:
            pass
        with st.spinner("Scanning broad public-news themes…"):
            fresh_discovered = discover_live_scenarios(max_queries=maxq)
        st.session_state["scenario_discovery_records"] = fresh_discovered.to_dict("records")
        st.session_state["scenario_discovery_maxq"] = int(maxq)
    discovered = pd.DataFrame(st.session_state.get("scenario_discovery_records", []))
    if discovered.empty:
        st.info("Scenario discovery is ready. Press **Run live scenario discovery** when you want a fresh public-news scan; nothing is fabricated while it is idle.")
    else:
        persist_scenario_memory(discovered)
        st.dataframe(discovered[["theme","root","evidence_count","source_count","novelty","latest_headline","sources"]],use_container_width=True,hide_index=True)
        active=discovered.iloc[0]
        root=str(active["root"])
        st.markdown(f"<div class='section'>Top discovered chain: {active['theme']}</div>",unsafe_allow_html=True)
        if root!="Unmapped hypothesis":
            ch=expand_chain(root,depth=4,max_edges=70)
            if not ch.empty:
                fig=chain_plot(ch,root)
                if fig is not None: st.plotly_chart(fig,use_container_width=True)
                st.dataframe(ch[["source","target","mechanism","role","lag","condition"]].head(45),use_container_width=True,hide_index=True)
        else:
            st.info("This is intentionally unmapped. The engine found a recurring new theme that is not yet in the causal library; research must identify mechanism, beneficiaries, losers, confirmation and falsifier before promotion.")
        st.markdown("<div class='section'>If this scenario confirms, what changes?</div>",unsafe_allow_html=True)
        br=adaptive_scenario_branches(root)
        if not br.empty:
            st.dataframe(br[["scenario","trigger","economic_projection","action_logic","falsifier"]],use_container_width=True,hide_index=True)

    st.markdown("<div class='section'>Scenario memory</div>",unsafe_allow_html=True)
    mem=load_scenario_memory()
    if mem.empty: st.caption("No persistent scenario memory yet.")
    else: st.dataframe(mem.head(40),use_container_width=True,hide_index=True)

elif nav == "HISTORICAL REPLAY":
    st.markdown("<div class='section'>Acceptance tests — examples are tests, never training labels</div>",unsafe_allow_html=True)
    st.dataframe(ACCEPTANCE,use_container_width=True,hide_index=True)
    st.markdown("<div class='gate'>PASS requires point-in-time evidence known on that date, a pre-frozen rule, negative controls, false-positive burden and lead time. The table below is the replay manifest / causal timeline; it is not yet a statistical proof by itself.</div>",unsafe_allow_html=True)
    cases=REPLAY["case"].dropna().unique().tolist() if not REPLAY.empty else []
    if cases:
        selected_case=st.selectbox("Replay case",cases,key="replay_case")
        r=REPLAY[REPLAY["case"]==selected_case].copy()
        st.dataframe(r[["date","phase","scanner_state","evidence_known_then","causal_chain","source_url"]],use_container_width=True,hide_index=True)
        st.markdown("<div class='section'>What the final replay must report</div>",unsafe_allow_html=True)
        st.markdown("""
<div class='grid3'>
 <div class='card'><div class='ct'>First detection</div><div class='cn'>Earliest date the frozen scanner raised DISCOVERED/WATCH using only information available then.</div></div>
 <div class='card'><div class='ct'>First actionable state</div><div class='cn'>When independent evidence + projection + expectation gap justified BUILD/SHORT — not when price already moved.</div></div>
 <div class='card'><div class='ct'>False positives</div><div class='cn'>How many same-family candidates fired but never produced the expected economics. Mandatory precision control.</div></div>
 <div class='card'><div class='ct'>Lead time</div><div class='cn'>Days/weeks before major repricing or intervention event.</div></div>
 <div class='card'><div class='ct'>Adverse excursion</div><div class='cn'>How wrong / early the signal looked before confirmation. Prevents hindsight-only storytelling.</div></div>
 <div class='card'><div class='ct'>Exit replay</div><div class='cn'>BUILD → HOLD → NO ADD → TRIM → SELL based on economics and price-in, not technical exits.</div></div>
</div>
""",unsafe_allow_html=True)

elif nav == "RESEARCH / GATES":
    st.markdown("<div class='section'>Frozen principles</div>",unsafe_allow_html=True)
    st.markdown("""
<div class='grid3'>
 <div class='card'><div class='ct'>1 · High recall first</div><div class='cn'>Discovery is intentionally sensitive so early bottlenecks/adoption/value-capture inflections are not discarded before evidence matures.</div></div>
 <div class='card'><div class='ct'>2 · High precision before capital</div><div class='cn'>Action requires independent evidence families, causal explanation, projection, expectation gap, falsifier and expression suitability.</div></div>
 <div class='card'><div class='ct'>3 · No hard-coded winner logic</div><div class='cn'>SNDK, PLTR, VVV, ZEC, ADES and JPY are frozen acceptance cases. They may not set thresholds or special rules.</div></div>
 <div class='card'><div class='ct'>4 · Auto-discover scenarios</div><div class='cn'>Broad feeds can surface mapped and novel clusters. Novel hypotheses remain quarantined until causally validated.</div></div>
 <div class='card'><div class='ct'>5 · Whole-chain search</div><div class='cn'>Direct winners, suppliers, equipment, logistics, substitutes, macro transmission, losers and normalization nodes are all searched.</div></div>
 <div class='card'><div class='ct'>6 · Price-in before action</div><div class='cn'>A great business can be a bad trade. Reverse valuation asks what earnings/usage/duration today's price already requires.</div></div>
</div>
""",unsafe_allow_html=True)
    st.markdown("<div class='section'>Source / coverage registry</div>",unsafe_allow_html=True)
    st.dataframe(SOURCE_REGISTRY,use_container_width=True,hide_index=True)
    st.markdown("<div class='section'>Opportunity families</div>",unsafe_allow_html=True)
    st.dataframe(FAMILIES,use_container_width=True,hide_index=True)
    st.markdown("<div class='section'>Scenario templates</div>",unsafe_allow_html=True)
    st.dataframe(TEMPLATES,use_container_width=True,hide_index=True)
    st.markdown("<div class='section'>Known limitations before production</div>",unsafe_allow_html=True)
    st.markdown("""
<div class='gate'>
<b>Still gated:</b> full point-in-time fundamentals for every global asset; exhaustive all-listed IHSG/US universe; verified tokenholder-capture adapters for every protocol; physical inventory/curve adapters for every commodity; cross-country FX equilibrium models; historical valuation distributions; option implied-distribution comparison; and purged/embargoed OOS acceptance statistics.<br><br>
The architecture is intentionally built so missing data becomes grey / research-only rather than being replaced with a fabricated score.
</div>
""",unsafe_allow_html=True)

st.caption("Opportunity Intelligence v1.1 · causal-first, projection-aware, scenario-adaptive, no classic technical indicators.")

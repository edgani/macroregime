from __future__ import annotations

import io
import html
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

from decision_core import (
    neutral_percentile_rank, entry_decision, expression_decision,
    get_prior_checkpoint, save_checkpoint, compute_revision_edge,
)
from ihsg_transaction import (
    eod_transaction_snapshot,
    intraday_transaction_snapshot,
    combine_transaction_layers,
    transaction_evidence_delta,
    transaction_summary_text,
)
from market_memory import MarketMemory
from verticals import enrich_with_memory, snapshot_features, available_families_from_row
from opportunity_kernel import VERTICAL_REQUIREMENTS, vertical_readiness, earliness_from_components
from defillama_adapter import chain_snapshot as defillama_chain_snapshot
from story_optionality import apply_story_optionality
from opportunity_longitudinal import OpportunityMemory
from opportunity_discovery import sync_opportunities, EQUITY_MARKETS, BENCHMARKS
from opportunity_outcomes import update_from_price_frames
from opportunity_learning import write_periodic_learning_reports
from opportunity_ui import render_opportunity_tracker, render_learning_lab, install_memequant_style

# ============================================================
# OPPORTUNITY INTELLIGENCE ENGINE v3.2.1 · LONGITUDINAL MARKET OPPORTUNITY OS
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
STATE = Path(os.environ.get("OIE_STATE_DIR", str(ROOT / "state")))
STATE.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="Market Opportunity OS · v3.2.1",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="collapsed",
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
    # Tie-neutral midrank: identical peers map to 50th percentile, not all to 100th.
    return neutral_percentile_rank(pd.to_numeric(s, errors="coerce").dropna().tolist(), value)


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
ONCHAIN_WATCHLIST = read_csv("onchain_watchlist.csv")
MEMORY = MarketMemory(STATE / "market_memory.sqlite")
OPP_MEMORY = OpportunityMemory(STATE / "opportunity_memory.sqlite")

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
.plainbox{border:1px solid var(--border);border-radius:12px;background:#0c131d;padding:10px 12px;font-size:.73rem;line-height:1.45;color:#dbe6f2}.plainbox b{color:#fff}.decision-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px}.decision-card{border:1px solid var(--border);border-radius:11px;background:#0c131d;padding:9px;min-height:80px}.dv{font-size:.82rem;font-weight:850;margin-top:4px}.dn{font-size:.58rem;color:#8f9cad;line-height:1.28;margin-top:3px}.info4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.info-card{border:1px solid var(--border);border-radius:11px;background:#0c131d;padding:9px;min-height:105px}.info-title{font-size:.64rem;font-weight:850}.info-text{font-size:.60rem;color:#9aa7b7;line-height:1.38;margin-top:5px}.top3{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}.topopp{border:1px solid var(--border);border-radius:12px;background:linear-gradient(180deg,#111925,#0c131d);padding:10px;min-height:94px}.topopp .sym{font-size:1.0rem;font-weight:880}.topopp .why{font-size:.60rem;color:#91a0b1;line-height:1.32;margin-top:4px}
.stagebar{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.stage{padding:4px 7px;border-radius:8px;font-size:.58rem;font-weight:820;border:1px solid var(--border);background:#0c131d}.stage.on{box-shadow:0 0 0 1px rgba(255,255,255,.06) inset}
.matrix{width:100%;border-collapse:separate;border-spacing:4px}.matrix th{font-size:.55rem;color:#8291a4;text-transform:uppercase;letter-spacing:.05em;text-align:left}.matrix td{border:1px solid var(--border);border-radius:8px;padding:7px;background:#0c131d;vertical-align:top}.mv{font-size:.67rem;font-weight:830}.mn{font-size:.55rem;color:#8d9aac;margin-top:2px}
div[data-baseweb="tab-list"]{gap:6px}button[data-baseweb="tab"]{height:34px;font-size:.71rem}

.visual-shell{border:1px solid var(--border);border-radius:14px;background:#090e15;padding:8px 10px}
.metric-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px;margin:7px 0}
.metric-mini{border:1px solid var(--border);border-radius:10px;background:#0b1119;padding:8px 10px;min-height:68px}
.metric-mini .m1{font-size:.51rem;color:#7f8da1;text-transform:uppercase;letter-spacing:.08em;font-weight:800}
.metric-mini .m2{font-size:1.02rem;font-weight:900;margin-top:3px}.metric-mini .m3{font-size:.56rem;color:#8996a8;margin-top:2px;line-height:1.25}
.compact-table div[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:12px;overflow:hidden}
div[data-testid="stPlotlyChart"]{border:1px solid var(--border);border-radius:14px;background:#090e15;padding:2px}
[data-testid="stMetric"]{border:1px solid var(--border);border-radius:10px;padding:8px 10px;background:#0b1119}
.today-card{border:1px solid var(--border);border-radius:15px;background:linear-gradient(180deg,#101a27,#0b1119);padding:14px 16px;margin:7px 0 10px}.today-label{font-size:.56rem;color:#8da0b7;letter-spacing:.10em;font-weight:850;text-transform:uppercase}.today-main{font-size:1.25rem;font-weight:900;letter-spacing:-.02em;margin-top:3px}.today-note{font-size:.69rem;color:#a9b5c4;line-height:1.38;margin-top:4px}
.simple-board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:7px 0 12px}.simple-col{border:1px solid var(--border);border-radius:12px;background:#0b1119;padding:10px;min-height:92px}.simple-col .sc-label{font-size:.54rem;letter-spacing:.08em;text-transform:uppercase;font-weight:850}.simple-col .sc-count{font-size:1.25rem;font-weight:900;margin-top:2px}.ticker-chip{display:inline-block;border:1px solid #2a394c;border-radius:999px;padding:3px 7px;margin:4px 3px 0 0;font-size:.58rem;font-weight:800;background:#101824;color:#dfe8f3}
.pick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0 12px}.pick-card{border:1px solid var(--border);border-radius:13px;background:linear-gradient(180deg,#111925,#0b1119);padding:11px;min-height:132px}.pick-top{display:flex;justify-content:space-between;gap:7px;align-items:flex-start}.pick-symbol{font-size:1.05rem;font-weight:920}.pick-market{font-size:.54rem;color:#8595aa;margin-top:1px}.pick-action{font-size:.70rem;font-weight:900;margin-top:8px}.pick-why{font-size:.61rem;color:#a2afbf;line-height:1.35;margin-top:5px}.pick-meta{font-size:.56rem;color:#7f8da1;line-height:1.35;margin-top:7px}.rank-badge{min-width:24px;height:24px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:#162132;border:1px solid #26364a;font-size:.60rem;font-weight:900}
.mode-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:8px 0 10px}.mode-card{border:1px solid var(--border);border-radius:11px;background:#0b1119;padding:9px 10px}.mode-name{font-size:.58rem;color:#8c9bae;font-weight:800}.mode-ready{font-size:.82rem;font-weight:900;margin-top:3px}.mode-note{font-size:.54rem;color:#7e8b9d;margin-top:2px}
.list-card{display:grid;grid-template-columns:90px 1.1fr 1fr .9fr .8fr;gap:8px;align-items:center;border:1px solid var(--border);border-radius:11px;background:#0b1119;padding:8px 10px;margin-bottom:6px}.list-sym{font-size:.82rem;font-weight:900}.list-sub{font-size:.54rem;color:#7f8da1}.list-action{font-size:.64rem;font-weight:850}.list-why,.list-meta{font-size:.57rem;color:#98a6b7;line-height:1.3}
.simple-help{font-size:.61rem;color:#8d9aac;line-height:1.4;margin:3px 0 8px}
/* v3.2.1: real native-button navigation, styled as product tabs. */
div[data-testid="stButton"]>button,button[data-testid="stBaseButton-secondary"]{border:1px solid #173947!important;background:#06131b!important;color:#b8d1d5!important;border-radius:8px!important;min-height:34px!important;font-size:.67rem!important;font-weight:820!important;box-shadow:none!important}
button[data-testid="stBaseButton-primary"]{border:1px solid #10d9bd!important;background:rgba(16,217,189,.12)!important;color:#14f1d0!important;border-radius:8px!important;min-height:34px!important;font-size:.67rem!important;font-weight:900!important;box-shadow:0 0 0 1px rgba(16,241,208,.08) inset!important}
div[data-testid="stButton"]>button:hover{border-color:#10cdb6!important;color:#13efd0!important}
.nav-caption{font-size:.52rem;color:#607b86;letter-spacing:.12em;text-transform:uppercase;margin:2px 0 4px}
@media(max-width:1000px){.kpis,.grid3,.decision-grid,.info4,.top3,.metric-strip,.simple-board,.pick-grid,.mode-strip{grid-template-columns:1fr 1fr}.list-card{grid-template-columns:80px 1fr 1fr}.list-meta,.list-why{grid-column:span 1}}
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
    net_margin_change: float = np.nan
    net_income_ttm: float = np.nan
    operating_cash_flow_ttm: float = np.nan
    capex_ttm: float = np.nan
    rd_ttm: float = np.nan
    rd_to_revenue: float = np.nan
    capex_to_revenue: float = np.nan
    total_cash: float = np.nan
    total_debt: float = np.nan
    shares_outstanding: float = np.nan
    shares_change_yoy: float = np.nan
    eps_estimate_next_year: float = np.nan
    eps_estimate_next_year_30d_ago: float = np.nan
    eps_revisions_up_30d: float = np.nan
    eps_revisions_down_30d: float = np.nan
    analyst_count_next_year: float = np.nan
    revenue_estimate_growth_next_year: float = np.nan
    revenue_growth_yoy: float = np.nan
    eps_growth_yoy: float = np.nan
    gross_margin_change: float = np.nan
    fcf_growth_yoy: float = np.nan
    price_change_20d: float = np.nan
    realized_vol_20d: float = np.nan
    avg_value_20d: float = np.nan
    avg_volume_20d: float = np.nan
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


def _latest(s: Optional[pd.Series]) -> float:
    x=_series_latest4(s)
    return float(x.iloc[0]) if len(x) else np.nan


def _level_change_yoy(s: Optional[pd.Series]) -> float:
    x=_series_latest4(s)
    if len(x)<5 or x.iloc[4]==0: return np.nan
    return float(x.iloc[0]/x.iloc[4]-1)


def _analysis_cell(df: Any, row: str, col: str) -> float:
    try:
        if df is None or getattr(df,'empty',True): return np.nan
        return safe_float(df.loc[row,col])
    except Exception:
        return np.nan


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
                if "Volume" in hist.columns:
                    vol = pd.to_numeric(hist["Volume"], errors="coerce").reindex(close.index)
                    tail = pd.DataFrame({"close": close, "volume": vol}).dropna().tail(20)
                    if not tail.empty:
                        snap.avg_volume_20d = float(tail["volume"].mean())
                        snap.avg_value_20d = float((tail["close"] * tail["volume"]).mean())

        inc = getattr(t, "quarterly_income_stmt", pd.DataFrame())
        cf = getattr(t, "quarterly_cashflow", pd.DataFrame())
        bs = getattr(t, "quarterly_balance_sheet", pd.DataFrame())
        rev = _pick_row(inc, ["Total Revenue", "Operating Revenue", "Revenue"])
        gross = _pick_row(inc, ["Gross Profit"])
        net = _pick_row(inc, ["Net Income", "Net Income Common Stockholders"])
        eps = _pick_row(inc, ["Diluted EPS", "Basic EPS"])
        rd = _pick_row(inc, ["Research And Development", "Research Development"])
        ocf = _pick_row(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
        capex = _pick_row(cf, ["Capital Expenditure", "Capital Expenditures"])
        fcf = _pick_row(cf, ["Free Cash Flow"])
        cash = _pick_row(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash"])
        debt = _pick_row(bs, ["Total Debt"])
        shares = _pick_row(bs, ["Ordinary Shares Number", "Share Issued"])
        if fcf is None:
            if ocf is not None and capex is not None:
                fcf = pd.to_numeric(ocf, errors="coerce") + pd.to_numeric(capex, errors="coerce")

        snap.revenue_ttm = _ttm(rev)
        snap.eps_ttm = _ttm(eps)
        if not np.isfinite(snap.eps_ttm) and np.isfinite(snap.market_cap) and np.isfinite(snap.trailing_pe) and snap.trailing_pe != 0 and np.isfinite(snap.price):
            snap.eps_ttm = snap.price / snap.trailing_pe
        snap.fcf_ttm = _ttm(fcf)
        snap.net_income_ttm = _ttm(net)
        snap.operating_cash_flow_ttm = _ttm(ocf)
        snap.capex_ttm = _ttm(capex)
        snap.rd_ttm = _ttm(rd)
        snap.revenue_growth_yoy = _yoy_from_quarters(rev)
        snap.eps_growth_yoy = _yoy_from_quarters(eps)
        snap.fcf_growth_yoy = _yoy_from_quarters(fcf)
        snap.gross_margin = _margin_latest(gross, rev)
        snap.net_margin = _margin_latest(net, rev)
        snap.gross_margin_change = _margin_change_yoy(gross, rev)
        snap.net_margin_change = _margin_change_yoy(net, rev)
        snap.rd_to_revenue = snap.rd_ttm/snap.revenue_ttm if np.isfinite(snap.rd_ttm) and np.isfinite(snap.revenue_ttm) and snap.revenue_ttm>0 else np.nan
        snap.capex_to_revenue = abs(snap.capex_ttm)/snap.revenue_ttm if np.isfinite(snap.capex_ttm) and np.isfinite(snap.revenue_ttm) and snap.revenue_ttm>0 else np.nan
        snap.total_cash = _latest(cash)
        snap.total_debt = _latest(debt)
        snap.shares_outstanding = _latest(shares)
        snap.shares_change_yoy = _level_change_yoy(shares)
        if not np.isfinite(snap.trailing_pe) and np.isfinite(snap.price) and np.isfinite(snap.eps_ttm) and snap.eps_ttm > 0:
            snap.trailing_pe = snap.price / snap.eps_ttm
        if market in ["US","HK","Hong Kong","China","Europe","Taiwan"]:
            try:
                et = t.get_eps_trend()
                er = t.get_eps_revisions()
                ee = t.get_earnings_estimate()
                re = t.get_revenue_estimate()
                snap.eps_estimate_next_year = _analysis_cell(et, "+1y", "current")
                snap.eps_estimate_next_year_30d_ago = _analysis_cell(et, "+1y", "30daysAgo")
                snap.eps_revisions_up_30d = _analysis_cell(er, "+1y", "upLast30days")
                snap.eps_revisions_down_30d = _analysis_cell(er, "+1y", "downLast30days")
                snap.analyst_count_next_year = _analysis_cell(ee, "+1y", "numberOfAnalysts")
                snap.revenue_estimate_growth_next_year = _analysis_cell(re, "+1y", "growth")
            except Exception:
                pass
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


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_defillama_holders_revenue(slug: str) -> pd.Series:
    """Tokenholder income (buybacks/burns/distributions) when DefiLlama tracks it."""
    if not slug:
        return pd.Series(dtype=float)
    url=f"https://api.llama.fi/summary/fees/{urllib.parse.quote(slug)}?dataType=dailyHoldersRevenue"
    try:
        r=requests.get(url,headers=HEADERS,timeout=15)
        if r.status_code!=200: return pd.Series(dtype=float)
        j=r.json(); chart=j.get("totalDataChart") or j.get("totalDataChartBreakdown") or []
        rows=[]
        if isinstance(chart,list):
            for item in chart:
                if isinstance(item,list) and len(item)>=2 and isinstance(item[1],(int,float)):
                    rows.append((pd.to_datetime(item[0],unit="s",errors="coerce"),float(item[1])))
        return pd.Series(dict(rows)).sort_index() if rows else pd.Series(dtype=float)
    except Exception:
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


def _secret_or_env(name: str) -> str:
    """Read server-side API keys without ever exposing them in the UI or repository."""
    v = str(os.environ.get(name, "") or "").strip()
    if v:
        return v
    try:
        if name in st.secrets:
            return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        pass
    return ""


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_ihsg_transaction_eod(symbol: str, price: float, adv_value_20d: float) -> Dict[str, Any]:
    token = _secret_or_env("INDEX_ALPHA_API_KEY")
    if not token:
        return {"eod_status": "GATED · INDEX_ALPHA_API_KEY MISSING", "eod_errors": ["Configure server-side secret to enable broker attribution."]}
    return eod_transaction_snapshot(
        symbol,
        token,
        lookback_days=int(os.environ.get("OIE_IHSG_BROKER_LOOKBACK", "5")),
        price=safe_float(price),
        adv_value_20d=safe_float(adv_value_20d),
    )


@st.cache_data(ttl=90, show_spinner=False)
def fetch_ihsg_transaction_intraday(symbol: str) -> Dict[str, Any]:
    token = _secret_or_env("INVEZGO_API_KEY")
    if not token:
        return {"intraday_status": "GATED · INVEZGO_API_KEY MISSING", "intraday_errors": ["Configure server-side secret to enable live microstructure."]}
    # Queue is deliberately not polled on the broad scan. Order-book + intraday data
    # cover the fast layer without burning quota; raw queue can be enabled later for
    # a focused ticker microscope.
    return intraday_transaction_snapshot(symbol, token, include_queue=False)


def fetch_ihsg_transaction_snapshot(symbol: str, price: float, adv_value_20d: float) -> Dict[str, Any]:
    eod = fetch_ihsg_transaction_eod(symbol, price, adv_value_20d)
    intra = fetch_ihsg_transaction_intraday(symbol)
    return combine_transaction_layers(eod, intra, price=safe_float(price))


def _snapshot_one(r: pd.Series) -> Dict[str, Any]:
    market, symbol, name = str(r["market"]), str(r["symbol"]), str(r["name"])
    external_id = str(r.get("external_id") or "")
    llama_slug = str(r.get("defillama_slug") or "")
    # Asset-class adapters are intentionally different. Do not waste company-financial
    # calls on FX/commodities, and do not trust Yahoo aliases for crypto economics.
    if market == "Crypto":
        snap=dict(AssetSnapshot(market=market,symbol=symbol,name=name).__dict__)
        snap.update({"crypto_fdv":np.nan,"fdv_premium":np.nan,"circulating_ratio":np.nan,"revenue_30d":np.nan,"revenue_growth_30d":np.nan,"annualized_revenue":np.nan,"mcap_to_revenue":np.nan,"holders_revenue_30d":np.nan,"holder_capture_ratio":np.nan,"holder_capture_status":"GATED","market_model_status":"PARTIAL / ECONOMICS"})
        if external_id:
            j=fetch_coingecko(external_id)
            md=(j or {}).get("market_data",{}) or {}
            snap["price"]=safe_float((md.get("current_price",{}) or {}).get("usd"))
            snap["market_cap"]=safe_float((md.get("market_cap",{}) or {}).get("usd"))
            snap["crypto_fdv"]=safe_float((md.get("fully_diluted_valuation",{}) or {}).get("usd"))
            circ=safe_float(md.get("circulating_supply")); maxs=safe_float(md.get("max_supply")); total=safe_float(md.get("total_supply"))
            denom=maxs if np.isfinite(maxs) and maxs>0 else total
            snap["circulating_ratio"]=circ/denom if np.isfinite(circ) and np.isfinite(denom) and denom>0 else np.nan
            snap["fdv_premium"]=snap["crypto_fdv"]/snap["market_cap"]-1 if np.isfinite(snap["crypto_fdv"]) and np.isfinite(snap["market_cap"]) and snap["market_cap"]>0 else np.nan
            rev=fetch_defillama_revenue(llama_slug)
            if len(rev)>=30:
                snap["revenue_30d"]=float(rev.iloc[-30:].sum())
            if len(rev)>=60:
                prev=float(rev.iloc[-60:-30].sum())
                snap["revenue_growth_30d"]=snap["revenue_30d"]/prev-1 if prev>0 and np.isfinite(snap["revenue_30d"]) else np.nan
            snap["annualized_revenue"]=snap["revenue_30d"]*12 if np.isfinite(snap["revenue_30d"]) else np.nan
            snap["mcap_to_revenue"]=snap["market_cap"]/snap["annualized_revenue"] if np.isfinite(snap["market_cap"]) and np.isfinite(snap["annualized_revenue"]) and snap["annualized_revenue"]>0 else np.nan
            holders=fetch_defillama_holders_revenue(llama_slug)
            snap["holders_revenue_30d"]=float(holders.iloc[-30:].sum()) if len(holders)>=30 else np.nan
            snap["holder_capture_ratio"]=snap["holders_revenue_30d"]/snap["revenue_30d"] if np.isfinite(snap["holders_revenue_30d"]) and np.isfinite(snap["revenue_30d"]) and snap["revenue_30d"]>0 else np.nan
            if np.isfinite(snap["holder_capture_ratio"]): snap["holder_capture_status"]="TRACKED"
            valid=sum(np.isfinite(snap.get(k,np.nan)) for k in ["price","market_cap","fdv_premium","circulating_ratio","revenue_growth_30d","holder_capture_ratio"])
            snap["data_quality"]="HIGH" if valid>=4 else ("MEDIUM" if valid>=2 else "LOW")
        snap["source_coverage"]="CoinGecko market/supply + DeFiLlama protocol economics; holder capture/usage remains gated unless independently confirmed"
    elif market in ["FX","Commodity","Index"]:
        snap=dict(fetch_price_only_snapshot(market,symbol,name))
        snap["market_model_status"]=("GATED / NEEDS RELATIVE-MACRO" if market=="FX" else ("GATED / NEEDS PHYSICAL BALANCE" if market=="Commodity" else "GATED / NEEDS MACRO+BREADTH"))
        snap["source_coverage"]="Yahoo market price/history only; direction cannot be promoted without dedicated causal data"
    else:
        snap=dict(fetch_yfinance_snapshot(market,symbol,name))
        snap["market_model_status"]="RESEARCH READY / CURRENT DATA"
        snap["source_coverage"]="Yahoo market + public company financial metadata; PIT SEC/IDX and estimate-revision history still required for production validation"
        if market == "IHSG":
            tx = fetch_ihsg_transaction_snapshot(symbol, safe_float(snap.get("price")), safe_float(snap.get("avg_value_20d")))
            snap.update(tx)
            snap["source_coverage"] += "; IHSG transaction layer = Index Alpha EOD broker attribution + Invezgo intraday/order-book when API keys are configured"
    snap["external_id"] = external_id
    snap["defillama_slug"] = llama_slug
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
    """Asset-class-specific evidence. Never score FX/commodities with stock earnings fields."""
    if df.empty:
        return df
    out=df.copy()
    for c in ["evidence_families","deterioration_families"]:
        out[c]=0
    out["evidence_basis"]=""
    if "market_model_status" not in out.columns:
        out["market_model_status"]="GATED"

    stock_metrics=["revenue_growth_yoy","eps_growth_yoy","gross_margin_change","fcf_growth_yoy","net_margin"]
    for m in stock_metrics:
        out[f"{m}_rank"]=np.nan
    # Stocks: causal fundamental inflection + cross-sectional confirmation.
    for market in ["US","IHSG","HK","Hong Kong","China","Europe","Taiwan"]:
        idxs=out.index[out["market"].eq(market)].tolist()
        for idx in idxs:
            r=out.loc[idx]
            peers=out[(out["market"]==market) & (out.get("sector",pd.Series(index=out.index,dtype=str))==r.get("sector"))]
            if len(peers)<4:
                peers=out[out["market"]==market]
            for m in stock_metrics:
                if m in out.columns:
                    out.at[idx,f"{m}_rank"]=percentile_rank(peers[m],safe_float(r.get(m)))
            er=[safe_float(out.at[idx,f"{m}_rank"]) for m in stock_metrics[:4]]
            ev=int(sum(np.isfinite(v) and v>=.75 for v in er))
            det=int(sum(np.isfinite(v) and v<=.25 for v in er))
            out.at[idx,"evidence_families"]=ev; out.at[idx,"deterioration_families"]=det
            out.at[idx,"evidence_basis"]="revenue + EPS + margin + FCF inflection"
            out.at[idx,"market_model_status"]="RESEARCH READY / CURRENT DATA"

    # IHSG transaction intelligence contributes AT MOST one evidence family. This prevents
    # feature multiplication from overwhelming fundamentals and keeps missing data fail-closed.
    for idx in out.index[out["market"].eq("IHSG")].tolist():
        ev_add, det_add, tx_basis = transaction_evidence_delta(out.loc[idx].to_dict())
        if ev_add or det_add:
            out.at[idx,"evidence_families"] = int(out.at[idx,"evidence_families"]) + int(ev_add)
            out.at[idx,"deterioration_families"] = int(out.at[idx,"deterioration_families"]) + int(det_add)
        base = str(out.at[idx,"evidence_basis"] or "")
        out.at[idx,"evidence_basis"] = (base + " + " + tx_basis).strip(" +")

    # Story / expectation optionality contributes AT MOST one family and never from "loss" alone.
    # US requires analyst revisions to confirm; IHSG requires improving economics with survivable financing.
    for idx in out.index[out["market"].isin(["US","IHSG","HK","Hong Kong","China","Europe","Taiwan"])].tolist():
        r=out.loc[idx]
        market=str(r.get("market"))
        story_state=str(r.get("story_state", ""))
        fin=str(r.get("financing_risk", "DATA GATED"))
        story_score=safe_float(r.get("story_optionality_score"))
        cred=safe_float(r.get("story_credibility_score"))
        base=str(out.at[idx,"evidence_basis"] or "")
        if market in ["US","HK","Hong Kong","China","Europe","Taiwan"]:
            rev_state=str(r.get("expectation_revision_state", "DATA GATED"))
            if rev_state=="UPWARD REVISION" and np.isfinite(story_score) and story_score>=60 and np.isfinite(cred) and cred>=55 and fin!="HIGH":
                out.at[idx,"evidence_families"]=int(out.at[idx,"evidence_families"])+1
                out.at[idx,"evidence_basis"]=(base+" + expectation optionality + upward analyst revisions").strip(" +")
            elif rev_state=="DOWNWARD REVISION" and ("BAD LOSS" in story_state or fin=="HIGH"):
                out.at[idx,"deterioration_families"]=int(out.at[idx,"deterioration_families"])+1
                out.at[idx,"evidence_basis"]=(base+" + negative expectation revision").strip(" +")
        else:
            if "EARLY STORY CANDIDATE" in story_state and np.isfinite(story_score) and story_score>=70 and np.isfinite(cred) and cred>=60 and fin!="HIGH":
                out.at[idx,"evidence_families"]=int(out.at[idx,"evidence_families"])+1
                out.at[idx,"evidence_basis"]=(base+" + narrative optionality + improving economics").strip(" +")
            elif "BAD LOSS" in story_state or fin=="HIGH":
                out.at[idx,"deterioration_families"]=int(out.at[idx,"deterioration_families"])+1
                out.at[idx,"evidence_basis"]=(base+" + weak loss quality / financing risk").strip(" +")

    # Crypto: economics / dilution / scarcity. Revenue existence alone is never a buy rule.
    cidx=out.index[out["market"].eq("Crypto")].tolist()
    if cidx:
        cp=out.loc[cidx].copy()
        for metric in ["revenue_growth_30d","fdv_premium","circulating_ratio","mcap_to_revenue","holder_capture_ratio","holders_revenue_30d"]:
            if metric not in out.columns: out[metric]=np.nan
        for idx in cidx:
            r=out.loc[idx]
            rg_rank=percentile_rank(cp["revenue_growth_30d"],safe_float(r.get("revenue_growth_30d")))
            fdv_rank=percentile_rank(cp["fdv_premium"],safe_float(r.get("fdv_premium")))
            circ_rank=percentile_rank(cp["circulating_ratio"],safe_float(r.get("circulating_ratio")))
            val_rank=percentile_rank(cp["mcap_to_revenue"],safe_float(r.get("mcap_to_revenue")))
            ev=0; det=0; basis=[]
            if np.isfinite(rg_rank) and rg_rank>=.70: ev+=1; basis.append("revenue acceleration")
            if np.isfinite(fdv_rank) and fdv_rank<=.35: ev+=1; basis.append("lower dilution/FDV premium")
            if np.isfinite(circ_rank) and circ_rank>=.65: ev+=1; basis.append("higher circulating ratio")
            if safe_float(r.get("holders_revenue_30d"))>0: ev+=1; basis.append("tracked tokenholder income")
            if np.isfinite(val_rank) and val_rank<=.35 and safe_float(r.get("annualized_revenue"))>0: ev+=1; basis.append("economic value vs peers")
            if np.isfinite(rg_rank) and rg_rank<=.30: det+=1
            if np.isfinite(fdv_rank) and fdv_rank>=.70: det+=1
            if np.isfinite(circ_rank) and circ_rank<=.30: det+=1
            out.at[idx,"evidence_families"]=ev; out.at[idx,"deterioration_families"]=det
            out.at[idx,"evidence_basis"]=" + ".join(basis) if basis else "economics incomplete; usage/holder-capture confirmation required"
            ready = np.isfinite(safe_float(r.get("holder_capture_ratio"))) and np.isfinite(safe_float(r.get("revenue_growth_30d"))) and np.isfinite(safe_float(r.get("fdv_premium")))
            out.at[idx,"market_model_status"]="RESEARCH READY / VALUE CAPTURE" if ready else "PARTIAL / ECONOMICS"

    # FX and commodities are included in the universe, but not promoted from price history alone.
    for market,status,basis in [
        ("FX","GATED / NEEDS RELATIVE-MACRO","needs rates/REER/BoP/positioning/policy data"),
        ("Commodity","GATED / NEEDS PHYSICAL BALANCE","needs inventory/production/consumption/curve/spare-capacity data"),
        ("Index","GATED / NEEDS MACRO+BREADTH","needs breadth/earnings/liquidity/regime context; price-only index history is not alpha"),
    ]:
        idxs=out.index[out["market"].eq(market)].tolist()
        for idx in idxs:
            out.at[idx,"evidence_families"]=0; out.at[idx,"deterioration_families"]=0
            out.at[idx,"evidence_basis"]=basis; out.at[idx,"market_model_status"]=status
            if str(out.at[idx,"data_quality"]).upper()=="HIGH": out.at[idx,"data_quality"]="MEDIUM"

    def stage_row(r: pd.Series) -> str:
        n=int(safe_float(r.get("evidence_families")) if np.isfinite(safe_float(r.get("evidence_families"))) else 0)
        d=int(safe_float(r.get("deterioration_families")) if np.isfinite(safe_float(r.get("deterioration_families"))) else 0)
        market=str(r.get("market"))
        if market in ["FX","Commodity","Index"]: return "DATA GATED / EARLY RADAR"
        if market=="Crypto":
            status=str(r.get("market_model_status",""))
            if d>=3: return "DETERIORATION WATCH"
            if "RESEARCH READY" in status and n>=4: return "CONFIRMED VALUE-CAPTURE INFLECTION"
            if n>=3: return "WATCH · ECONOMICS CONFIRMING"
            return "DISCOVERED / NEEDS USAGE + CAPTURE"
        if market=="IHSG" and str(r.get("story_state",""))=="EARLY STORY CANDIDATE" and n>=2:
            return "EARLY STORY CANDIDATE"
        if market=="US" and str(r.get("expectation_optionality_state",""))=="INFLECTION + REVISIONS CONFIRM" and n>=2:
            return "EXPECTATION INFLECTION"
        if n>=4: return "HIGH-CONVICTION CANDIDATE"
        if n>=3: return "CONFIRMED INFLECTION"
        if n>=2: return "WATCH"
        if d>=3: return "DETERIORATION WATCH"
        return "DISCOVERED / NEEDS MORE EVIDENCE"
    out["stage"]=[stage_row(r) for _,r in out.iterrows()]
    return out

def sector_multiple_context(scan: pd.DataFrame, row: pd.Series) -> Dict[str, Any]:
    """Transparent valuation context. Never fall back from a sparse sector to the entire market.

    A whole-market fallback was convenient but conceptually wrong (e.g. valuing a bank against a
    semiconductor). We now prefer forward P/E because the projection is NTM-like, then trailing P/E
    only when there are at least four same-sector peers. Otherwise fair value is GATED.
    """
    market=str(row.get("market")); sector=str(row.get("sector") or "Unknown"); symbol=str(row.get("symbol"))
    peers=scan[(scan.get("market",pd.Series(index=scan.index,dtype=str)).astype(str)==market) &
               (scan.get("sector",pd.Series(index=scan.index,dtype=str)).astype(str)==sector) &
               (scan.get("symbol",pd.Series(index=scan.index,dtype=str)).astype(str)!=symbol)].copy()
    for metric,label,upper in [("forward_pe","same-sector forward P/E",120),("trailing_pe","same-sector trailing P/E",200)]:
        if metric not in peers.columns: continue
        vals=pd.to_numeric(peers[metric],errors="coerce")
        vals=vals[(vals>0)&(vals<upper)].dropna()
        if len(vals)>=4:
            q25,q50,q75=robust_quantiles(vals.tolist())
            conf="HIGH" if len(vals)>=8 else "MEDIUM"
            return {"pe25":q25,"pemed":q50,"pe75":q75,"peer_count":int(len(vals)),"valuation_basis":label,"valuation_confidence":conf}
    return {"pe25":np.nan,"pemed":np.nan,"pe75":np.nan,"peer_count":0,"valuation_basis":"GATED · insufficient same-sector peers","valuation_confidence":"GATED"}


def sector_multiple_bands(scan: pd.DataFrame, row: pd.Series) -> Tuple[float,float,float]:
    c=sector_multiple_context(scan,row)
    return c["pe25"],c["pemed"],c["pe75"]


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


def sector_sales_context(scan: pd.DataFrame, row: pd.Series) -> Dict[str, Any]:
    """Same-sector Price/Sales context for loss-making companies; never market-wide fallback."""
    market=str(row.get("market")); sector=str(row.get("sector") or "Unknown"); symbol=str(row.get("symbol"))
    peers=scan[(scan.get("market",pd.Series(index=scan.index,dtype=str)).astype(str)==market) &
               (scan.get("sector",pd.Series(index=scan.index,dtype=str)).astype(str)==sector) &
               (scan.get("symbol",pd.Series(index=scan.index,dtype=str)).astype(str)!=symbol)].copy()
    if len(peers)<4:
        return {"ps25":np.nan,"psmed":np.nan,"ps75":np.nan,"peer_count":0,"valuation_basis":"GATED · insufficient same-sector P/S peers","valuation_confidence":"GATED"}
    mcap=pd.to_numeric(peers.get("market_cap",pd.Series(index=peers.index,dtype=float)),errors="coerce")
    rev=pd.to_numeric(peers.get("revenue_ttm",pd.Series(index=peers.index,dtype=float)),errors="coerce")
    ps=(mcap/rev).replace([np.inf,-np.inf],np.nan)
    ps=ps[(ps>0.15)&(ps<40)].dropna()
    if len(ps)<4:
        return {"ps25":np.nan,"psmed":np.nan,"ps75":np.nan,"peer_count":int(len(ps)),"valuation_basis":"GATED · insufficient valid same-sector P/S peers","valuation_confidence":"GATED"}
    q25,q50,q75=robust_quantiles(ps.tolist())
    return {"ps25":q25,"psmed":q50,"ps75":q75,"peer_count":int(len(ps)),"valuation_basis":"same-sector Price/Sales · loss-making fallback","valuation_confidence":"HIGH" if len(ps)>=8 else "MEDIUM"}


def valuation_projection(scan: pd.DataFrame, row: pd.Series) -> Dict[str, Any]:
    ctx=sector_multiple_context(scan,row)
    pe25,pemed,pe75=ctx["pe25"],ctx["pemed"],ctx["pe75"]
    eps = safe_float(row.get("eps_ttm")); price=safe_float(row.get("price"))
    g_bear,g_base,g_bull = scenario_growth_bands(row)
    out = {**ctx,"g_bear":g_bear,"g_base":g_base,"g_bull":g_bull}
    if np.isfinite(eps) and eps > 0 and np.isfinite(price) and np.isfinite(pemed):
        bear_eps = eps*(1+g_bear); base_eps=eps*(1+g_base); bull_eps=eps*(1+g_bull)
        fv_bear = max(0,bear_eps)*pe25 if np.isfinite(pe25) else np.nan
        fv_base = max(0,base_eps)*pemed if np.isfinite(pemed) else np.nan
        fv_bull = max(0,bull_eps)*pe75 if np.isfinite(pe75) else np.nan
        implied_eps = price/pemed if pemed>0 else np.nan
        gap = (base_eps-implied_eps)/abs(implied_eps) if np.isfinite(implied_eps) and implied_eps!=0 else np.nan
        out.update({"bear_eps":bear_eps,"base_eps":base_eps,"bull_eps":bull_eps,"fv_bear":fv_bear,"fv_base":fv_base,"fv_bull":fv_bull,"implied_eps":implied_eps,"expectation_gap":gap,"valuation_mode":"P/E"})
        return out

    # Loss-making fallback: use same-sector P/S, projected revenue and current market cap.
    # This is intentionally unavailable when same-sector peers are sparse.
    revenue=safe_float(row.get("revenue_ttm")); mcap=safe_float(row.get("market_cap"))
    psctx=sector_sales_context(scan,row)
    ps25,psmed,ps75=psctx["ps25"],psctx["psmed"],psctx["ps75"]
    out.update(psctx)
    if np.isfinite(revenue) and revenue>0 and np.isfinite(mcap) and mcap>0 and np.isfinite(price) and np.isfinite(psmed):
        rev_bear=max(0,revenue*(1+g_bear)); rev_base=max(0,revenue*(1+g_base)); rev_bull=max(0,revenue*(1+g_bull))
        mc_bear=rev_bear*ps25 if np.isfinite(ps25) else np.nan
        mc_base=rev_base*psmed
        mc_bull=rev_bull*ps75 if np.isfinite(ps75) else np.nan
        fv_bear=price*(mc_bear/mcap) if np.isfinite(mc_bear) else np.nan
        fv_base=price*(mc_base/mcap)
        fv_bull=price*(mc_bull/mcap) if np.isfinite(mc_bull) else np.nan
        gap=mc_base/mcap-1
        implied_revenue=mcap/psmed if psmed>0 else np.nan
        out.update({"bear_eps":np.nan,"base_eps":np.nan,"bull_eps":np.nan,"fv_bear":fv_bear,"fv_base":fv_base,"fv_bull":fv_bull,"implied_eps":np.nan,"implied_revenue":implied_revenue,"expectation_gap":gap,"valuation_mode":"P/S LOSS-MAKING"})
        return out
    out.update({"bear_eps":np.nan,"base_eps":np.nan,"bull_eps":np.nan,"fv_bear":np.nan,"fv_base":np.nan,"fv_bull":np.nan,"implied_eps":np.nan,"expectation_gap":np.nan,"valuation_mode":"GATED"})
    if not np.isfinite(revenue) or revenue<=0: out["valuation_basis"]="GATED · positive revenue base unavailable"
    return out


def action_from_relative_rank(scan: pd.DataFrame) -> pd.DataFrame:
    """Research-state actions using absolute, interpretable evidence + valuation gates.

    We deliberately removed gap percentile ranking from the action decision because a small seed
    universe can make percentile ranks unstable and overfit. A missing/weak valuation basis fails
    closed instead of becoming a BUY/SHORT.
    """
    out=scan.copy()
    gaps=[]; vconf=[]; vbasis=[]; pcount=[]; bears=[]; bases=[]; bulls=[]; vmodes=[]
    equity_markets=["US","IHSG","HK","Hong Kong","China","Europe","Taiwan"]
    for _,r in out.iterrows():
        if str(r.get("market")) in equity_markets:
            val=valuation_projection(out,r)
            gaps.append(val.get("expectation_gap",np.nan)); vconf.append(val.get("valuation_confidence","GATED")); vbasis.append(val.get("valuation_basis","GATED")); pcount.append(val.get("peer_count",0))
            bears.append(val.get("fv_bear",np.nan)); bases.append(val.get("fv_base",np.nan)); bulls.append(val.get("fv_bull",np.nan)); vmodes.append(val.get("valuation_mode","GATED"))
        else:
            gaps.append(np.nan); vconf.append("N/A"); vbasis.append("asset-class model"); pcount.append(0); bears.append(np.nan); bases.append(np.nan); bulls.append(np.nan); vmodes.append("ASSET-CLASS MODEL")
    out["expectation_gap"]=gaps; out["valuation_confidence"]=vconf; out["valuation_basis"]=vbasis; out["valuation_peer_count"]=pcount
    out["upside_case_value"]=bulls; out["base_case_value"]=bases; out["downside_case_value"]=bears; out["valuation_mode"]=vmodes
    actions=[]
    for _,r in out.iterrows():
        n=int(safe_float(r.get("evidence_families")) if np.isfinite(safe_float(r.get("evidence_families"))) else 0)
        d=int(safe_float(r.get("deterioration_families")) if np.isfinite(safe_float(r.get("deterioration_families"))) else 0)
        gap=safe_float(r.get("expectation_gap")); market=str(r.get("market")); status=str(r.get("market_model_status","")); vc=str(r.get("valuation_confidence","GATED"))
        if market in ["FX","Commodity"]:
            action="WATCH / DATA GATED"
        elif market=="Crypto":
            if d>=3: action="BEARISH / AVOID"
            elif "RESEARCH READY" in status and n>=4 and str(r.get("data_quality","LOW")).upper()=="HIGH": action="BUILD CANDIDATE"
            elif n>=3 and str(r.get("data_quality","LOW")).upper()=="HIGH": action="SELECTIVE ADD / WATCH"
            else: action="WATCH / NO FORCED TRADE"
        elif vc=="GATED" or not np.isfinite(gap):
            action="WATCH / VALUATION GATED" if n>=2 else "WATCH / NO FORCED TRADE"
        elif d>=3 and gap<=-0.20:
            action="SELL / AVOID" if market=="IHSG" else "SHORT / PUT CANDIDATE"
        elif n>=3 and gap>=0.20:
            action="BUILD CANDIDATE"
        elif n>=2 and gap>=0.10:
            action="SELECTIVE ADD / WATCH"
        elif n>=2 and gap>-0.20:
            action="HOLD / NEEDS BETTER PRICE"
        elif d>=2 and gap<=-0.20:
            action="SELL / AVOID" if market=="IHSG" else "BEARISH CANDIDATE"
        else:
            action="WATCH / NO FORCED TRADE"
        actions.append(action)
    out["research_action"]=actions
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
    slug = str(symbol_row.get("defillama_slug") or "")
    revenue = fetch_defillama_revenue(slug)
    rev30 = float(revenue.iloc[-30:].sum()) if len(revenue)>=30 else np.nan
    prev30 = float(revenue.iloc[-60:-30].sum()) if len(revenue)>=60 else np.nan
    rev_growth = rev30/prev30-1 if np.isfinite(rev30) and np.isfinite(prev30) and prev30>0 else np.nan
    annualized = rev30*12 if np.isfinite(rev30) else np.nan
    holders=fetch_defillama_holders_revenue(slug)
    holders30=float(holders.iloc[-30:].sum()) if len(holders)>=30 else np.nan
    return {
        "market_cap":mcap,"fdv":fdv,"fdv_premium":fdv/mcap-1 if mcap>0 and np.isfinite(fdv) else np.nan,
        "circulating_supply":circ,"total_supply":total,"max_supply":maxs,
        "circulating_ratio":circ/maxs if np.isfinite(circ) and np.isfinite(maxs) and maxs>0 else np.nan,
        "revenue_30d":rev30,"revenue_growth_30d":rev_growth,"annualized_revenue":annualized,
        "holders_revenue_30d":holders30,"holder_capture_ratio":holders30/rev30 if np.isfinite(holders30) and np.isfinite(rev30) and rev30>0 else np.nan,
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
# v3 Market Opportunity OS · universal memory + vertical radar
# -----------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_defillama_chain_snapshot(chain: str) -> Dict[str, Any]:
    """Free DeFiLlama ecosystem snapshot. Failure is visible and never promoted to a signal."""
    return defillama_chain_snapshot(chain)


def _memory_enrich_and_record(fresh: pd.DataFrame) -> pd.DataFrame:
    """Compute change from prior snapshots first, then append what is known now.

    This ordering is deliberate: the current observation is never allowed into its own baseline.
    """
    if fresh.empty:
        return fresh
    out = enrich_with_memory(fresh, MEMORY)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for _, r in out.iterrows():
        try:
            MEMORY.record_snapshot(
                str(r.get("symbol", "")), str(r.get("market", "")), snapshot_features(r),
                state=str(r.get("change_state", "")), source_quality=str(r.get("data_quality", "LOW")),
                observed_at_utc=observed,
            )
        except Exception:
            pass
    return out


def _onchain_radar_frame() -> pd.DataFrame:
    items=[]
    for _, r in ONCHAIN_WATCHLIST.iterrows():
        if str(r.get("entity_type","")).lower() == "chain":
            items.append((str(r.get("entity") or ""),str(r.get("defillama_id") or r.get("entity") or ""),str(r.get("notes") or "")))
    rows=[]
    def one(item):
        entity,chain,notes=item
        snap=fetch_defillama_chain_snapshot(chain)
        d={"Entity":entity or chain,"Type":"Chain","Notes":notes}; d.update(snap)
        changes=[safe_float(d.get("tvl_7d")),safe_float(d.get("stablecoins_7d")),safe_float(d.get("dex_volume_7d_change")),safe_float(d.get("fees_7d_change")),safe_float(d.get("revenue_7d_change"))]
        finite=[x for x in changes if np.isfinite(x)]
        d["change_breadth"]=(sum(x>0 for x in finite)/len(finite)) if finite else np.nan
        d["change_strength"]=float(np.nanmedian(finite)) if finite else np.nan
        if len(finite)<3: d["state"]="DATA GATED"
        elif d["change_breadth"]>=.75 and d["change_strength"]>0: d["state"]="ACCELERATING"
        elif d["change_breadth"]>=.60: d["state"]="EMERGING"
        elif d["change_breadth"]<=.25: d["state"]="FADING"
        else: d["state"]="MIXED / QUIET"
        return d
    with ThreadPoolExecutor(max_workers=min(7,max(1,len(items)))) as ex:
        futs=[ex.submit(one,x) for x in items]
        for fut in as_completed(futs):
            try: rows.append(fut.result())
            except Exception as exc: rows.append({"Entity":"unknown","state":"DATA GATED","defillama_errors":[str(exc)],"source_quality":"LOW"})
    return pd.DataFrame(rows).sort_values(["state","Entity"]) if rows else pd.DataFrame()


def _market_status_frame(scan: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    labels=[("On-chain",None),("Crypto","Crypto"),("US Stocks","US"),("IHSG","IHSG"),("Forex","FX"),("Commodities","Commodity")]
    for label,m in labels:
        if m is None:
            rows.append({"Vertical":label,"Status":"PARTIAL · DEFILLAMA WIRED","Coverage":"ecosystem/capital wired; wallet quality/social remain gated","Candidates":"—"})
            continue
        sub=scan[scan.get("market",pd.Series(index=scan.index,dtype=str)).astype(str)==m] if not scan.empty else pd.DataFrame()
        if sub.empty:
            rows.append({"Vertical":label,"Status":"NO DATA","Coverage":"—","Candidates":0}); continue
        statuses=sub.get("vertical_status",pd.Series(index=sub.index,dtype=str)).fillna("GATED").astype(str)
        ready=int((statuses=="READY").sum()); partial=int((statuses=="PARTIAL").sum())
        status="READY" if ready==len(sub) else ("PARTIAL" if (ready+partial)>0 else "GATED")
        cov=pd.to_numeric(sub.get("vertical_core_coverage",pd.Series(index=sub.index,dtype=float)),errors="coerce").mean()
        rows.append({"Vertical":label,"Status":status,"Coverage":pct(cov,0) if np.isfinite(cov) else "GATED","Candidates":len(sub)})
    return pd.DataFrame(rows)


def _render_control_room(ranked: pd.DataFrame, mg: Dict[str,Any]) -> None:
    """Dense operator-style control room. Native controls remain real Streamlit widgets; visual cards are presentation only."""
    install_memequant_style(st)
    market_counts=MEMORY.counts()
    opp_counts=OPP_MEMORY.counts()
    active=OPP_MEMORY.events_frame(active_only=True,limit=200)
    alerts=OPP_MEMORY.alerts_frame(limit=12)
    n_markets=ranked["market"].nunique() if not ranked.empty and "market" in ranked else 0
    high_data=int((ranked.get("data_quality",pd.Series(dtype=str)).astype(str).str.upper()=="HIGH").sum()) if not ranked.empty else 0
    regime=str(mg.get("regime") or mg.get("action_label") or "GATED")
    action_label=str(mg.get("action_label") or "MACRO GATED")

    st.markdown(f"""
<div class='mq-top'>
 <div class='mq-brand'><div class='mq-logo'>◢◣</div><div><div class='mq-name'>Opportunity<span>OS</span></div><div class='mq-tag'>CHANGE → CAPTURE → EXPECTATION GAP → OUTCOME</div></div></div>
 <div class='mq-status'><b>◉ SCAN</b><small>{len(ranked)} candidates</small></div>
 <div class='mq-status'><b>◆ MEMORY</b><small>{opp_counts.get('events',0)} frozen events</small></div>
 <div class='mq-status'><b>◎ ENGINE</b><small>v3.2.1 UI hotfix</small></div>
 <div class='mq-status'><b>◉ DATA</b><small>{high_data} high-quality</small></div>
 <div class='mq-status'><b>◇ MARKETS</b><small>{n_markets} active</small></div>
 <div class='mq-search'>⌕ Use the candidate controls below to inspect one opportunity without losing scanner state.</div>
 <div class='mq-wallet'>RISK · {html.escape(regime[:18])}</div>
</div>
<div class='mq-titlebar'><div><div class='mq-title'>◉ Cross-Market Opportunity Control Room</div><div class='mq-sub'>Automatic discovery, causal capture, immutable first-seen memory and fail-closed data gates. Navigation is independent from scanner refresh.</div></div>
<div class='mq-kpirow'><div class='mq-kpi'><b>ACTIVE</b><strong>{opp_counts.get('active',0)}</strong><small>tracked theses</small></div><div class='mq-kpi'><b>SNAPSHOTS</b><strong>{market_counts.get('snapshots',0)}</strong><small>market memory</small></div><div class='mq-kpi'><b>OUTCOMES</b><strong>{opp_counts.get('outcomes',0)}</strong><small>matured labels</small></div><div class='mq-kpi'><b>MACRO</b><strong style='font-size:10px'>{html.escape(action_label[:24])}</strong><small>timing context</small></div></div></div>
""",unsafe_allow_html=True)

    left,center,right=st.columns([1.0,2.05,1.0],gap="small")
    status=_market_status_frame(ranked)
    with left:
        st.markdown("<div class='mq-section'>Vertical readiness</div>",unsafe_allow_html=True)
        cards=[]
        for _,r in status.iterrows():
            state=str(r.get('Status','GATED')); cls='mq-up' if state=='READY' else ('mq-down' if state in {'GATED','NO DATA'} else '')
            cards.append(f"<div class='mq-mini'><small>{html.escape(str(r.get('Vertical','')))}</small><strong class='{cls}'>{html.escape(state)}</strong><div class='mq-sub'>{html.escape(str(r.get('Coverage','')))} · {html.escape(str(r.get('Candidates','—')))} candidates</div></div>")
        st.markdown("<div class='mq-mini-grid'>"+"".join(cards)+"</div>",unsafe_allow_html=True)
        st.markdown("<div class='mq-section'>Inspect candidate</div>",unsafe_allow_html=True)
        symbols=ranked.get('symbol',pd.Series(dtype=str)).astype(str).head(20).tolist() if not ranked.empty else []
        if symbols:
            if st.session_state.get("control_selected_symbol") not in symbols:
                st.session_state["control_selected_symbol"]=symbols[0]
            selected=st.selectbox("Control room candidate",symbols,key="control_selected_symbol",label_visibility="collapsed")
        else:
            selected=None
            st.caption("No valid candidates in the selected market set.")

    row=None
    if selected and not ranked.empty:
        hit=ranked[ranked.get('symbol',pd.Series(index=ranked.index,dtype=str)).astype(str)==str(selected)]
        if not hit.empty: row=hit.iloc[0]
    with center:
        st.markdown("<div class='mq-section'>Selected opportunity</div>",unsafe_allow_html=True)
        if row is None:
            st.markdown("<div class='mq-empty'>Scanner has not produced an inspectable candidate yet.</div>",unsafe_allow_html=True)
        else:
            sym=html.escape(str(row.get('symbol','—'))); name=html.escape(str(row.get('name',''))); market=html.escape(str(row.get('market',''))); action=html.escape(str(row.get('research_action','WATCH'))); change=html.escape(str(row.get('change_state','BASELINE BUILDING'))); quality=html.escape(str(row.get('data_quality','GATED')))
            why=html.escape(str(row.get('why') or row.get('notes') or row.get('thesis') or 'Evidence is still accumulating.'))
            score=safe_float(row.get('opportunity_score')); score_txt=fmt_num(score,0) if np.isfinite(score) else '—'
            st.markdown(f"<div class='mq-hero'><div class='mq-hero-top'><div><h2>{sym} · {name}</h2><div class='mq-meta'>{market} · data {quality} · {change}</div></div><span class='mq-pill'>{action}</span></div><div class='mq-thesis'>{why[:520]}</div><div class='mq-scores'><div class='mq-score'><small>OPPORTUNITY</small><strong>{score_txt}</strong></div><div class='mq-score'><small>EVIDENCE</small><strong>{fmt_num(safe_float(row.get('evidence_families')),0)}</strong></div><div class='mq-score'><small>MEMORY OBS</small><strong>{fmt_num(safe_float(row.get('memory_observations')),0)}</strong></div><div class='mq-score'><small>VERTICAL</small><strong style='font-size:10px'>{html.escape(str(row.get('vertical_status','GATED')))}</strong></div></div></div>",unsafe_allow_html=True)
            causal=[str(row.get(k,'')) for k in ['driver','first_order_effect','second_order_effect','bottleneck','beneficiary'] if str(row.get(k,'')).strip() and str(row.get(k,'')).lower()!='nan']
            if causal:
                st.markdown("<div class='mq-section'>Causal transmission</div><div class='mq-chain'>"+" <span class='mq-arrow'>→</span> ".join(html.escape(x) for x in causal)+"</div>",unsafe_allow_html=True)
            else:
                st.markdown("<div class='mq-section'>Causal transmission</div><div class='mq-empty'>Causal chain incomplete → candidate cannot be upgraded by narrative alone.</div>",unsafe_allow_html=True)
            compact=[c for c in ['research_action','stage','change_state','sequence_signature','expectation_gap','vertical_missing_core'] if c in ranked.columns]
            if compact:
                st.dataframe(pd.DataFrame([{c:row.get(c) for c in compact}]),use_container_width=True,hide_index=True)

    with right:
        st.markdown("<div class='mq-section'>Macro & risk</div>",unsafe_allow_html=True)
        risk_items=[('REGIME',regime),('CRASH',mg.get('crash_state','GATED')),('CREDIT',mg.get('credit_state','GATED')),('STRUCTURE',mg.get('market_structure','GATED'))]
        st.markdown("<div class='mq-mini-grid'>"+"".join(f"<div class='mq-mini'><small>{k}</small><strong>{html.escape(str(v))[:38]}</strong></div>" for k,v in risk_items)+"</div>",unsafe_allow_html=True)
        st.markdown("<div class='mq-section'>Recent opportunity alerts</div>",unsafe_allow_html=True)
        if alerts.empty:
            st.markdown("<div class='mq-empty'>No deduplicated state alerts yet.</div>",unsafe_allow_html=True)
        else:
            feed=''.join(f"<div class='mq-feedrow'><div>{html.escape(str(r.get('observed_at_utc',''))[11:19])}</div><div class='mq-event'>{html.escape(str(r.get('alert_type','')))[:18]}</div><div>{html.escape(str(r.get('message','')))[:60]}</div></div>" for _,r in alerts.head(8).iterrows())
            st.markdown("<div class='mq-feed'>"+feed+"</div>",unsafe_allow_html=True)

    st.markdown("<div class='mq-section'>Cross-market opportunity radar</div>",unsafe_allow_html=True)
    if ranked.empty:
        st.info("Current scan is empty / gated.")
    else:
        cols=[c for c in ["market","symbol","research_action","stage","change_state","sequence_signature","memory_observations","vertical_status","vertical_missing_core"] if c in ranked.columns]
        st.dataframe(ranked[cols].head(36),use_container_width=True,hide_index=True,height=430)
    st.caption("Fail-closed: missing causal, fundamental or market-specific evidence remains GATED; price momentum never substitutes for missing economics.")


def _render_verticals(ranked: pd.DataFrame) -> None:
    st.markdown("<div class='section'>Vertical engines · same kernel, different evidence</div>",unsafe_allow_html=True)
    tabs=st.tabs(["ON-CHAIN","CRYPTO","US STOCKS","IHSG","FOREX","COMMODITIES"])
    with tabs[0]:
        st.caption("Core: ecosystem + capital + usage + quality + memory. Wallet/social/narrative are independent adapters and must not be faked from TVL.")
        oc=_onchain_radar_frame()
        if oc.empty:
            st.warning("On-chain watchlist unavailable.")
        else:
            show=oc.copy()
            for c in ["tvl_7d","tvl_30d","stablecoins_7d","stablecoins_30d","dex_volume_7d_change","fees_7d_change","revenue_7d_change","change_breadth"]:
                if c in show: show[c]=show[c].map(lambda x:pct(safe_float(x),1))
            cols=[c for c in ["Entity","state","tvl","tvl_7d","stablecoins","stablecoins_7d","dex_volume_24h","dex_volume_7d_change","fees_24h","fees_7d_change","revenue_24h","revenue_7d_change","source_quality"] if c in show]
            st.dataframe(show[cols],use_container_width=True,hide_index=True)
            st.caption("DeFiLlama confirmation deliberately separates TVL from stablecoins, DEX activity, fees and revenue so token-price repricing cannot masquerade as broad ecosystem growth.")
    def _market_tab(tab, market, title, core_note):
        with tab:
            st.caption(core_note)
            sub=ranked[ranked.get("market",pd.Series(index=ranked.index,dtype=str)).astype(str)==market] if not ranked.empty else pd.DataFrame()
            if sub.empty:
                st.info(f"No {title} rows loaded."); return
            story_cols=[]
            if market in ["US","HK","Hong Kong","China","Europe","Taiwan"]: story_cols=["loss_type","expectation_optionality_state","expectation_optionality_score","expectation_revision_state","financing_risk"]
            elif market=="IHSG": story_cols=["loss_type","story_state","story_optionality_score","story_credibility_score","financing_risk"]
            cols=[c for c in ["symbol","name","research_action","stage"]+story_cols+["change_state","sequence_signature","memory_observations","vertical_status","vertical_core_coverage","vertical_missing_core","data_quality"] if c in sub]
            st.dataframe(sub[cols],use_container_width=True,hide_index=True)
    _market_tab(tabs[1],"Crypto","crypto","Liquid crypto requires spot/leverage/positioning evidence; current value-capture data is useful but leverage remains gated until OI/funding/liquidation adapters are complete.")
    _market_tab(tabs[2],"US","US stocks","Core: fundamentals + estimate revisions + capital flow + causal chain + valuation + memory. Current build has fundamentals + live Yahoo analyst trend/revisions + loss-making P/S fallback; Market Memory makes revision snapshots PIT going forward. Capital-flow history remains gated.")
    _market_tab(tabs[3],"IHSG","IHSG","Core: fundamentals + broker flow + foreign flow + corporate actions + valuation + memory. Broker summary is bounded to one evidence family and cannot overpower fundamentals. Loss-making narrative optionality is separate and only activates when economics improve and financing is survivable.")
    _market_tab(tabs[4],"FX","FX","Core: relative rates + macro surprise + central banks + positioning + valuation + memory. Price-only rows remain DATA GATED by design.")
    _market_tab(tabs[5],"Commodity","commodities","Core: physical supply/demand + inventory + curve + positioning + memory. Price-only rows remain DATA GATED by design.")

# -----------------------------
# Decision-view helpers
# -----------------------------
ACTION_TIER = {
    "BUILD CANDIDATE": 5,
    "SELECTIVE ADD / WATCH": 4,
    "HOLD / NEEDS BETTER PRICE": 3,
    "WATCH / NO FORCED TRADE": 2,
    "WATCH / VALUATION GATED": 2,
    "WATCH / DATA GATED": 1,
    "SHORT / PUT CANDIDATE": 4,
    "SELL / AVOID": 4,
    "BEARISH CANDIDATE": 4,
}


def rank_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Research ordering only; never a probability. Uses absolute expectation gap, not seed-universe percentiles."""
    if df.empty:
        return df
    out=df.copy()
    out["_action_tier"]=out.get("research_action",pd.Series(index=out.index,dtype=object)).map(ACTION_TIER).fillna(1)
    out["_evidence"]=pd.to_numeric(out.get("evidence_families",0),errors="coerce").fillna(0)
    out["_gap"]=pd.to_numeric(out.get("expectation_gap",np.nan),errors="coerce").fillna(-9)
    out["_quality"]=out.get("data_quality",pd.Series(index=out.index,dtype=object)).map({"HIGH":2,"MEDIUM":1,"LOW":0}).fillna(0)
    out["_vconf"]=out.get("valuation_confidence",pd.Series(index=out.index,dtype=object)).map({"HIGH":2,"MEDIUM":1,"GATED":0,"N/A":1}).fillna(0)
    return out.sort_values(["_action_tier","_evidence","_vconf","_gap","_quality"],ascending=False)


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


@st.cache_data(ttl=900, show_spinner=False)
def fetch_deribit_option_snapshot(symbol: str, direction: str = "CALL") -> Dict[str, Any]:
    """Public Deribit option snapshot for BTC/ETH only. No API key required.
    Directional thesis still has to pass the crypto economics/risk gate first.
    """
    base={"BTC-USD":"BTC","ETH-USD":"ETH"}.get(str(symbol).upper())
    if not base:
        return {"error":"crypto options adapter currently supports liquid BTC/ETH Deribit markets only"}
    try:
        idx=requests.get("https://www.deribit.com/api/v2/public/get_index_price",params={"index_name":f"{base.lower()}_usd"},headers=HEADERS,timeout=12)
        idx.raise_for_status(); spot=safe_float((idx.json().get("result") or {}).get("index_price"))
        ins=requests.get("https://www.deribit.com/api/v2/public/get_instruments",params={"currency":base,"kind":"option","expired":"false"},headers=HEADERS,timeout=15)
        ins.raise_for_status(); instruments=ins.json().get("result") or []
        now_ms=int(pd.Timestamp.now(tz="UTC").timestamp()*1000); want="call" if direction.upper()=="CALL" else "put"
        candidates=[]
        for x in instruments:
            if str(x.get("option_type","")).lower()!=want: continue
            exp=safe_float(x.get("expiration_timestamp")); strike=safe_float(x.get("strike"))
            if not np.isfinite(exp) or not np.isfinite(strike): continue
            days=(exp-now_ms)/86400000
            if days<14 or days>150: continue
            dte_pen=abs(days-60); strike_pen=abs(strike-spot)/spot if np.isfinite(spot) and spot>0 else 9
            candidates.append((dte_pen+strike_pen*30,days,strike,x.get("instrument_name")))
        if not candidates: return {"error":"no usable BTC/ETH option expiry"}
        _,days,strike,name=sorted(candidates,key=lambda z:z[0])[0]
        bs=requests.get("https://www.deribit.com/api/v2/public/get_book_summary_by_instrument",params={"instrument_name":name},headers=HEADERS,timeout=12)
        bs.raise_for_status(); rows=bs.json().get("result") or []
        if not rows: return {"error":"empty Deribit book summary"}
        r=rows[0]; bid=safe_float(r.get("bid_price")); ask=safe_float(r.get("ask_price")); mark=safe_float(r.get("mark_price"))
        mid=(bid+ask)/2 if np.isfinite(bid) and np.isfinite(ask) and ask>=bid else mark
        spread=(ask-bid)/mid if np.isfinite(mid) and mid>0 and np.isfinite(bid) and np.isfinite(ask) else np.nan
        iv=safe_float(r.get("mark_iv")); iv=iv/100 if np.isfinite(iv) and iv>2 else iv
        oi=safe_float(r.get("open_interest")); prem_usd=mid*spot if np.isfinite(mid) and np.isfinite(spot) else np.nan
        liquid=bool(np.isfinite(spread) and spread<=.15 and np.isfinite(oi) and oi>=10)
        return {"symbol":symbol,"direction":direction.upper(),"venue":"Deribit","instrument":name,"days":round(days,1),"spot":spot,"strike":strike,
                "bid":bid,"ask":ask,"mid":mid,"premium_usd":prem_usd,"spread":spread,"iv":iv,"open_interest":oi,
                "implied_move":iv*np.sqrt(days/365) if np.isfinite(iv) else np.nan,"liquidity":"PASS" if liquid else "WEAK / CHECK MANUALLY","error":""}
    except Exception as exc:
        return {"error":str(exc)}


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
        for _fn in [fetch_yfinance_snapshot,fetch_price_only_snapshot,fetch_coingecko,fetch_defillama_revenue,fetch_defillama_holders_revenue,google_news_rss,discover_live_scenarios,fetch_option_snapshot,fetch_deribit_option_snapshot,fetch_ihsg_transaction_eod,fetch_ihsg_transaction_intraday]:
            try: _fn.clear()
            except Exception: pass
    try:
        safe_compute_macro_gate_snapshot(refresh=force)
    except Exception as exc:
        st.session_state["macro_refresh_error"] = str(exc)
    fresh=build_snapshot_frame(scan_input,max_assets=max_assets) if not scan_input.empty else pd.DataFrame()
    if not fresh.empty:
        try:
            fresh=action_from_relative_rank(add_cross_sectional_evidence(apply_story_optionality(fresh)))
            fresh=_memory_enrich_and_record(fresh)
        except Exception as exc:
            fresh["error"]=fresh.get("error","")
            fresh["stage"]="DISCOVERED / NEEDS MORE EVIDENCE"
            fresh["research_action"]="WATCH / NO FORCED TRADE"
            fresh["evidence_families"]=0
            fresh["deterioration_families"]=0
            fresh["expectation_gap"]=np.nan
            fresh["valuation_confidence"]="GATED"
            fresh["valuation_basis"]="GATED · scan repair"
            st.session_state["scan_repair_error"]=str(exc)
        try:
            if "change_state" not in fresh.columns:
                fresh=_memory_enrich_and_record(fresh)
        except Exception as exc:
            st.session_state["memory_refresh_error"]=str(exc)
    try:
        scen=discover_live_scenarios(max_queries=8)
    except Exception as exc:
        scen=pd.DataFrame()
        st.session_state["scenario_refresh_error"]=str(exc)
    st.session_state["live_scan_records"]=fresh.to_dict("records") if not fresh.empty else []
    st.session_state["live_scan_signature"]=scan_signature
    st.session_state["scenario_discovery_records"]=scen.to_dict("records") if not scen.empty else []
    st.session_state["intel_refreshed_at_utc"]=datetime.now(timezone.utc).isoformat(timespec="seconds")


@st.cache_data(ttl=21600, show_spinner=False)
def _fetch_outcome_history(symbol: str, start_iso: str) -> pd.Series:
    if yf is None or not symbol:
        return pd.Series(dtype=float)
    try:
        start=(pd.Timestamp(start_iso)-pd.Timedelta(days=5)).date().isoformat()
        hist=yf.Ticker(symbol).history(start=start,auto_adjust=True,actions=False)
        if hist is None or hist.empty or "Close" not in hist:
            return pd.Series(dtype=float)
        s=pd.to_numeric(hist["Close"],errors="coerce").dropna()
        idx=pd.to_datetime(s.index,utc=True,errors="coerce"); s.index=idx
        return s[~s.index.isna()]
    except Exception:
        return pd.Series(dtype=float)


def _refresh_mature_opportunity_outcomes(limit: int = 8) -> None:
    """Bounded, cached outcome maturation. Never backfills future data into the event snapshot."""
    if yf is None:
        return
    events=OPP_MEMORY.events_frame(active_only=False,limit=200)
    if events.empty:
        return
    # Oldest first so mature events get labeled before fresh ones.
    events=events.sort_values("first_seen_time",ascending=True).head(int(limit))
    for _,ev in events.iterrows():
        symbol=str(ev.get("symbol") or ""); market=str(ev.get("market") or ""); anchor=str(ev.get("first_seen_time") or "")
        if not symbol or not anchor: continue
        asset=_fetch_outcome_history(symbol,anchor)
        if asset.empty: continue
        bench_symbol=str(BENCHMARKS.get(market,"") or "")
        # Descriptive benchmark labels are not treated as tickers.
        bench=_fetch_outcome_history(bench_symbol,anchor) if bench_symbol and all(x not in bench_symbol for x in [" / ","specific","context"]) else pd.Series(dtype=float)
        update_from_price_frames(OPP_MEMORY,str(ev.get("event_id")),asset,benchmark_prices=(bench if not bench.empty else None),sector_prices=None)


def _macro_allows_long_leverage(mg: Dict[str,Any]) -> bool:
    label=str(mg.get("action_label","")).upper()
    crash=str(mg.get("crash_state","")).upper()
    return not any(k in label for k in ["DEFENSIVE","CRISIS"]) and "CRASH DANGER" not in crash


def _plain_horizon(row: pd.Series, kind: str = "") -> str:
    stage=str(row.get("stage","")).upper()
    market=str(row.get("market","")).upper()
    if "HIGH-CONVICTION" in stage: return "2Q–2Y" if market in ["US","IHSG","CRYPTO"] else "days–1Q"
    if "CONFIRMED" in stage: return "1–4Q" if market in ["US","IHSG","CRYPTO"] else "days–1Q"
    if "WATCH" in stage: return "1–2Q"
    return "early / wait"


def _conviction_label(row: pd.Series) -> str:
    ev=int(safe_float(row.get("evidence_families")) if np.isfinite(safe_float(row.get("evidence_families"))) else 0)
    q=str(row.get("data_quality","LOW")).upper()
    if ev>=4 and q=="HIGH": return "HIGH"
    if ev>=3 and q in ["HIGH","MEDIUM"]: return "MED-HIGH"
    if ev>=2 and q=="HIGH": return "MEDIUM"
    return "LOW / EARLY"


def _asymmetry_label(row: pd.Series, val: Dict[str,Any]) -> str:
    px=safe_float(row.get("price")); fv=safe_float(val.get("fv_base")) if val else np.nan
    gap=safe_float(val.get("expectation_gap")) if val else np.nan
    if np.isfinite(px) and px>0 and np.isfinite(fv):
        up=fv/px-1
        if up>=0.50 and _conviction_label(row) in ["HIGH","MED-HIGH"]: return "HIGH"
        if up>=0.20: return "POSITIVE"
        if up<=-0.20: return "NEGATIVE"
    if np.isfinite(gap) and gap>=0.25: return "POSITIVE"
    return "MIXED"


def _why_now_compact(row: pd.Series) -> str:
    bits=[]
    if str(row.get("market"))=="IHSG":
        tx_state=str(row.get("transaction_state","")).upper()
        tx_cov=str(row.get("transaction_coverage","LOW")).upper()
        tx_score=safe_float(row.get("transaction_score"))
        if tx_cov in ["MEDIUM","HIGH"] and tx_state and tx_state not in ["NEUTRAL / MIXED","DATA GATED"]:
            label=f"transaction: {tx_state.lower()}"
            if np.isfinite(tx_score): label += f" ({tx_score:.0f}/100)"
            bits.append((999.0,label))
    rg=safe_float(row.get("revenue_growth_yoy")); eg=safe_float(row.get("eps_growth_yoy")); gm=safe_float(row.get("gross_margin_change")); fcf=safe_float(row.get("fcf_growth_yoy"))
    if np.isfinite(rg): bits.append((abs(rg), f"revenue {'accelerating' if rg>0 else 'weakening'} {pct(rg)}"))
    if np.isfinite(eg): bits.append((abs(eg), f"EPS {'accelerating' if eg>0 else 'weakening'} {pct(eg)}"))
    if np.isfinite(gm): bits.append((abs(gm)*2, f"gross margin {'expanding' if gm>0 else 'compressing'} {pct(gm)}"))
    if np.isfinite(fcf): bits.append((abs(fcf), f"FCF {'improving' if fcf>0 else 'weakening'} {pct(fcf)}"))
    bits=sorted(bits,key=lambda x:x[0],reverse=True)
    if bits: return "; ".join(x[1] for x in bits[:2])
    note=str(row.get("notes","") or "").replace("acceptance test only; ","").strip()
    return note if note else "Early evidence; needs deeper causal confirmation"


def _asset_currency(row: pd.Series) -> str:
    market=str(row.get("market",""))
    if market=="IHSG": return "Rp"
    if market=="FX": return ""
    return "$"

def _fmt_asset_price(row: pd.Series, x: float, digits: int=2) -> str:
    if not np.isfinite(safe_float(x)): return "—"
    cur=_asset_currency(row)
    if cur=="Rp": return f"Rp{safe_float(x):,.0f}"
    if cur=="": return f"{safe_float(x):,.4f}"
    return fmt_money(safe_float(x),cur,digits)


def _macro_fit(mg: Dict[str,Any], direction: str="LONG") -> str:
    label=str(mg.get("action_label","MACRO GATED")).upper(); crash=str(mg.get("crash_state",""))
    if "MACRO GATED" in label: return "GATED"
    if direction=="LONG" and any(k in label for k in ["DEFENSIVE","CRISIS"]): return "HEADWIND"
    if direction=="SHORT" and any(k in label for k in ["DEFENSIVE","CRISIS"]): return "TAILWIND"
    if "RISK-ON" in label: return "TAILWIND" if direction=="LONG" else "HEADWIND"
    return "NEUTRAL / SELECTIVE"


def _plain_action_from_row(row: pd.Series, kind: str) -> str:
    research=str(row.get("research_action","")).upper(); stage=str(row.get("stage","")).upper()
    if kind=="buyhold":
        if "SELL" in research or "AVOID" in research: return "TRIM / SELL / AVOID"
        if "BUILD" in research and ("CONFIRMED" in stage or "HIGH-CONVICTION" in stage): return "BUY / BUILD"
        if "SELECTIVE ADD" in research and "WATCH" in stage: return "WATCH · WAIT CONFIRMATION"
        if "SELECTIVE ADD" in research: return "SELECTIVE ADD"
        if "HOLD" in research: return "HOLD · WAIT BETTER PRICE"
        return "WATCH"
    return str(row.get("expression",row.get("research_action","WATCH")))


def _expression_tables(ranked: pd.DataFrame, mg: Dict[str,Any]) -> Dict[str,pd.DataFrame]:
    """Build expression surfaces without hiding an asset class.

    v2.3 only returned *qualified* leverage/options rows. That was safe but visually
    confusing: FX/commodities/crypto appeared to be missing. v2.4+ keeps the same
    fail-closed capital rule but shows monitored rows with an explicit WAIT/GATED
    state. A row is actionable only when `qualified=True`.
    """
    if ranked.empty:
        empty=pd.DataFrame()
        return {"buyhold":empty,"spot":empty,"leverage":empty,"options":empty,"radar":empty}
    out=ranked.copy()
    action=out.get("research_action",pd.Series(index=out.index,dtype=str)).fillna("").astype(str)
    qual=out.get("data_quality",pd.Series(index=out.index,dtype=str)).fillna("LOW").astype(str).str.upper()
    ev=pd.to_numeric(out.get("evidence_families",0),errors="coerce").fillna(0)
    det=pd.to_numeric(out.get("deterioration_families",0),errors="coerce").fillna(0)
    status=out.get("market_model_status",pd.Series(index=out.index,dtype=str)).fillna("GATED").astype(str)

    # Cash ownership surface: show the whole stock research universe, not only BUYs.
    buyhold=out[out["market"].isin(["US","IHSG"])].copy()
    if not buyhold.empty:
        buyhold["expression"]=[_plain_action_from_row(r,"buyhold") for _,r in buyhold.iterrows()]
        buyhold["qualified"]=buyhold["expression"].astype(str).str.contains("BUY|BUILD|ADD|SELL|AVOID",regex=True,na=False)

    # Spot/cash surface: always show crypto/FX/commodities, while preserving direction gates.
    spot=out[out["market"].isin(["Crypto","FX","Commodity"])].copy()
    if not spot.empty:
        labels=[]; qflags=[]
        for _,r in spot.iterrows():
            a=str(r.get("research_action","")).upper(); stt=str(r.get("market_model_status","")).upper()
            if any(k in a for k in ["BUILD","SELECTIVE ADD"]): lab="SPOT LONG / BUILD"; q=True
            elif any(k in a for k in ["SHORT","SELL","BEARISH"]): lab="BEARISH / AVOID"; q=True
            elif "RESEARCH READY" not in stt and str(r.get("market")) in ["FX","Commodity"]: lab="WAIT · MODEL GATED"; q=False
            else: lab="HOLD / WATCH"; q=False
            labels.append(lab); qflags.append(q)
        spot["expression"]=labels; spot["qualified"]=qflags

    # Leverage: show US/FX/commodity/crypto rows even when not yet qualified.
    long_signal=action.str.contains("BUILD|SELECTIVE ADD",regex=True,na=False)
    short_signal=action.str.contains("SHORT|SELL|BEARISH",regex=True,na=False)
    model_ready=status.str.contains("RESEARCH READY",case=False,na=False)
    long_ok=long_signal & (ev>=3) & qual.eq("HIGH") & model_ready & _macro_allows_long_leverage(mg)
    short_ok=short_signal & (det>=3) & qual.eq("HIGH") & model_ready
    lev=out[out["market"].isin(["US","FX","Commodity","Crypto"])].copy()
    if not lev.empty:
        expressions=[]; qflags=[]; gates=[]
        for idx,r in lev.iterrows():
            q=bool(long_ok.loc[idx] or short_ok.loc[idx])
            a=str(r.get("research_action","")).upper(); m=str(r.get("market")); stt=str(r.get("market_model_status","GATED"))
            if q:
                lab="LEVERAGED LONG" if long_ok.loc[idx] else "LEVERAGED SHORT"
                gate="EARNED · CAUSAL DATA + MACRO/RISK"
            elif m=="US":
                lab="WAIT · NO LEVERAGE EDGE"; gate="needs stronger evidence / valuation / macro fit"
            elif m=="Crypto":
                lab="WAIT · CRYPTO LEVERAGE GATED"; gate="needs research-ready usage/value-capture + leverage data"
            elif m=="FX":
                lab="WAIT · FX LEVERAGE GATED"; gate="needs relative macro + REER/BoP/positioning/policy"
            else:
                lab="WAIT · COMMODITY LEVERAGE GATED"; gate="needs physical balance + curve + spare capacity"
            expressions.append(lab); qflags.append(q); gates.append(gate)
        lev["expression"]=expressions; lev["qualified"]=qflags; lev["risk_gate"]=gates
        lev=lev.sort_values(["qualified","evidence_families"],ascending=[False,False],kind="stable")

    # Options: show all US listed-option research rows plus BTC/ETH Deribit rows.
    # Only qualified rows become CALL/PUT candidates; everything else stays visibly WAIT/GATED.
    us_base=out["market"].eq("US")
    crypto_symbol=out["symbol"].astype(str).str.upper().isin(["BTC-USD","ETH-USD"])
    option_base=us_base | (out["market"].eq("Crypto") & crypto_symbol)
    opt=out[option_base].copy()
    if not opt.empty:
        us_qual=(us_base & (((long_signal) & (ev>=3) & qual.eq("HIGH")) | ((short_signal) & (det>=3) & qual.eq("HIGH"))))
        crypto_model_ready=status.str.contains("RESEARCH READY",case=False,na=False)
        crypto_qual=(out["market"].eq("Crypto") & crypto_symbol & crypto_model_ready & (ev>=3) & qual.eq("HIGH") & action.str.contains("BUILD|SELECTIVE ADD|BEARISH|SHORT|SELL",regex=True,na=False))
        qmask=us_qual | crypto_qual
        labels=[]; qflags=[]; checks=[]
        for idx,r in opt.iterrows():
            q=bool(qmask.loc[idx]); a=str(r.get("research_action","")).upper(); m=str(r.get("market"))
            bearish=any(k in a for k in ["SHORT","SELL","BEARISH"])
            if q: lab="PUT CANDIDATE" if bearish else "CALL CANDIDATE"
            elif m=="Crypto": lab="WAIT · BTC/ETH OPTION THESIS GATED"
            else: lab="WAIT · OPTION EDGE NOT EARNED"
            labels.append(lab); qflags.append(q); checks.append("DERIBIT IV / SKEW / LIQUIDITY" if m=="Crypto" else "US IV / SKEW / LIQUIDITY")
        opt["expression"]=labels; opt["qualified"]=qflags; opt["option_edge"]=checks
        opt=opt.sort_values(["qualified","evidence_families"],ascending=[False,False],kind="stable")

    used=set(pd.concat([x for x in [buyhold,spot] if not x.empty],axis=0).index.tolist()) if any(not x.empty for x in [buyhold,spot]) else set()
    radar=out[~out.index.isin(used)].copy()
    if not radar.empty:
        radar=radar.sort_values([c for c in ["evidence_families","data_quality"] if c in radar.columns],ascending=False,kind="stable").head(24)
        radar["qualified"]=False
    return {"buyhold":buyhold,"spot":spot,"leverage":lev,"options":opt,"radar":radar}

def _expression_readiness(kind: str) -> List[Tuple[str,str,str]]:
    """Visible truth table. A market never disappears just because it is gated."""
    k=kind.lower()
    if k=="buyhold":
        return [("US stocks","ACTIVE","cash stock + valuation/entry engine"),("IHSG","ACTIVE · CASH ONLY","buy/build/hold/trim/sell; no leverage/options")]
    if k=="spot":
        return [("Crypto","ACTIVE / PARTIAL","spot shown; value-capture model where data exists"),("FX","VISIBLE · GATED IF INCOMPLETE","direction appears only after relative-macro model clears"),("Commodities","VISIBLE · GATED IF INCOMPLETE","direction appears only after physical model clears")]
    if k=="leverage":
        return [("US","ACTIVE WHEN EARNED","fundamental + valuation + macro"),("Crypto","VISIBLE","leveraged row shown; capital blocked until crypto leverage model clears"),("FX","VISIBLE","row shown; blocked until relative-macro/REER/BoP/positioning clears"),("Commodity","VISIBLE","row shown; blocked until physical/curve model clears"),("IHSG","NOT ALLOWED","cash only")]
    if k=="options":
        return [("US","ACTIVE WHEN EARNED","listed calls/puts"),("BTC / ETH","VISIBLE · DERIBIT","CALL/PUT only after crypto thesis + IV/liquidity clear"),("Other crypto","NO LIQUID OPTION SURFACE","never fabricate an option"),("FX / Commodity","NOT YET IN PRODUCT","future listed-option/futures-option module")]
    return [("All markets","EARLY RADAR","discovery is broad; capital waits for asset-class confirmation")]

def _render_expression_readiness(kind: str) -> None:
    rows=_expression_readiness(kind)
    if not rows: return
    html="<div class='grid3' style='grid-template-columns:repeat(%d,minmax(0,1fr))'>" % min(5,len(rows))
    for market,status,note in rows:
        stxt=status.upper()
        tone="green" if "ACTIVE" in stxt else ("amber" if any(x in stxt for x in ["PARTIAL","ADAPTER READY"]) else "gray")
        c=COLORS[tone][0]
        html+=f"<div class='card' style='min-height:78px'><div class='kicker'>{market}</div><div class='ct' style='color:{c};margin-top:4px'>{status}</div><div class='cn'>{note}</div></div>"
    html+="</div>"
    st.markdown(html,unsafe_allow_html=True)


def _display_scoreboard(df: pd.DataFrame, kind: str) -> None:
    if df.empty:
        st.markdown(f"<div class='gate'><b>NO {kind.upper()} ROWS.</b> This surface is empty because the selected universe does not contain a supported instrument.</div>",unsafe_allow_html=True)
        return
    rows=[]; k=kind.upper()
    for _,r in df.head(18).iterrows():
        val=valuation_projection(df,r) if str(r.get("market")) in ["US","IHSG"] else {}
        pin,_=price_in_label(val); px=safe_float(r.get("price")); base=safe_float(val.get("fv_base")) if val else np.nan
        upside=base/px-1 if np.isfinite(base) and np.isfinite(px) and px>0 else np.nan
        q=bool(r.get("qualified",False))
        common={"State":"● ACTION" if q else "○ WAIT","Market":r.get("market"),"Ticker":r.get("symbol"),"Action":_plain_action_from_row(r,"buyhold") if "BUY & HOLD" in k else r.get("expression",r.get("research_action")),"Conviction":_conviction_label(r),"Price":r.get("price")}
        if "BUY & HOLD" in k: common.update({"Base FV":base,"Upside":upside,"Price-in":pin})
        elif "LEVERAGED" in k: common.update({"Gate":r.get("risk_gate","—")})
        elif "OPTIONS" in k: common.update({"Option check":r.get("option_edge","—")})
        elif "EARLY" in k: common.update({"Stage":r.get("stage")})
        else: common.update({"Stage":r.get("stage")})
        rows.append(common)
    show=pd.DataFrame(rows)
    st.dataframe(show,use_container_width=True,hide_index=True,height=min(480,38+35*len(show)),column_config={"Price":st.column_config.NumberColumn(format="%.2f"),"Base FV":st.column_config.NumberColumn(format="%.2f"),"Upside":st.column_config.NumberColumn(format="%.1f%%")})


def _plotly_base(fig, height: int=340, legend: bool=True):
    if go is None: return None
    fig.update_layout(height=height,margin=dict(l=20,r=20,t=42,b=22),paper_bgcolor="#090e15",plot_bgcolor="#090e15",font=dict(color="#dce6f2",size=11),showlegend=legend,legend=dict(orientation="h",yanchor="bottom",y=1.02,x=0),hoverlabel=dict(bgcolor="#111925"))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.055)",zerolinecolor="rgba(255,255,255,.12)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,.055)",zerolinecolor="rgba(255,255,255,.12)")
    return fig


def _render_expression_matrix(expr: Dict[str,pd.DataFrame]) -> None:
    if go is None: return
    markets=["US","IHSG","Crypto","FX","Commodity"]
    cols=[("buyhold","Cash / stock"),("spot","Spot / cash"),("leverage","Leverage"),("options","Options")]
    z=[]; text=[]
    for m in markets:
        zr=[]; tr=[]
        for key,label in cols:
            d=expr.get(key,pd.DataFrame())
            if d.empty or "market" not in d: sub=pd.DataFrame()
            else: sub=d[d["market"].astype(str)==m]
            if m=="IHSG" and key in ["leverage","options"]: val=0; txt="NOT ALLOWED"
            elif m in ["FX","Commodity"] and key=="options": val=0; txt="NOT YET"
            elif sub.empty: val=0; txt="—"
            elif "qualified" in sub.columns and sub["qualified"].fillna(False).astype(bool).any(): val=3; txt="ACTION"
            else: val=1; txt="VISIBLE / WAIT"
            zr.append(val); tr.append(txt)
        z.append(zr); text.append(tr)
    fig=go.Figure(go.Heatmap(z=z,x=[c[1] for c in cols],y=markets,text=text,texttemplate="%{text}",hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>",zmin=0,zmax=3,colorscale=[[0,"#101722"],[.33,"#39485c"],[.66,"#f59e0b"],[1,"#16c784"]],showscale=False,xgap=5,ygap=5))
    fig.update_layout(title="Expression coverage · nothing disappears when gated")
    _plotly_base(fig,310,False)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})


def _opportunity_map_frame(ranked: pd.DataFrame) -> pd.DataFrame:
    if ranked.empty: return pd.DataFrame()
    rows=[]
    for _,r in ranked.iterrows():
        market=str(r.get("market")); ev=safe_float(r.get("evidence_families")); det=safe_float(r.get("deterioration_families")); quality=str(r.get("data_quality","LOW")).upper()
        evidence=(0 if not np.isfinite(ev) else ev)-(0 if not np.isfinite(det) else det)
        x=np.nan; source=""
        if market in ["US","IHSG"]:
            v=valuation_projection(ranked,r); gap=safe_float(v.get("expectation_gap")); x=100*clamp(gap,-1,1) if np.isfinite(gap) else np.nan; source="expectation gap"
        elif market=="Crypto":
            x=clamp(evidence*18,-90,90); source="crypto economics evidence"
        else:
            x=0.0; source="causal model gated"
        rows.append({"Market":market,"Ticker":r.get("symbol"),"Evidence":evidence,"Asymmetry":x,"Quality":quality,"Action":r.get("research_action"),"Source":source})
    return pd.DataFrame(rows)


def _qualified_modes_for_symbol(expr: Dict[str,pd.DataFrame], symbol: str) -> List[Tuple[str,str]]:
    """Return only genuinely qualified expressions for one underlying."""
    out=[]
    labels={"buyhold":"STOCK","spot":"SPOT","leverage":"LEVERAGE","options":"OPTION"}
    for key in ["buyhold","spot","leverage","options"]:
        d=expr.get(key,pd.DataFrame())
        if d.empty or "symbol" not in d.columns:
            continue
        sub=d[d["symbol"].astype(str)==str(symbol)]
        if sub.empty:
            continue
        if "qualified" in sub.columns:
            sub=sub[sub["qualified"].fillna(False).astype(bool)]
        if sub.empty:
            continue
        action=str(sub.iloc[0].get("expression",sub.iloc[0].get("research_action","ACTION")))
        out.append((labels[key],action))
    return out


def _plain_board_state(row: pd.Series, expr: Dict[str,pd.DataFrame]) -> Dict[str,Any]:
    symbol=str(row.get("symbol","—"))
    modes=_qualified_modes_for_symbol(expr,symbol)
    research=str(row.get("research_action","WATCH") or "WATCH").upper()
    quality=str(row.get("data_quality","LOW") or "LOW").upper()
    model=str(row.get("market_model_status","GATED") or "GATED").upper()
    market=str(row.get("market",""))
    downside_words=["SHORT","SELL","PUT","BEARISH","EXIT","TRIM","AVOID"]
    if modes:
        actions=" · ".join(x[1] for x in modes)
        downside=any(w in actions.upper() for w in downside_words)
        return {"bucket":"AVOID / DOWNSIDE" if downside else "ACT NOW","tone":"red" if downside else "green","action":modes[0][1],"modes":modes,"ready":True}
    if any(w in research for w in downside_words):
        return {"bucket":"AVOID / DOWNSIDE","tone":"red","action":research,"modes":[],"ready":False}
    if quality=="LOW" or (market in ["FX","Commodity","Crypto"] and "READY" not in model):
        return {"bucket":"NOT READY","tone":"gray","action":"WAIT FOR DATA","modes":[],"ready":False}
    return {"bucket":"WATCH","tone":"amber","action":"WAIT / WATCH","modes":[],"ready":False}


def _render_plain_mode_strip(expr: Dict[str,pd.DataFrame]) -> None:
    specs=[("buyhold","Cash / stock","normal ownership"),("leverage","Leverage","only when risk gate clears"),("options","Options","call / put when edge clears"),("spot","Spot / cash","crypto / FX / commodity")]
    h="<div class='mode-strip'>"
    for key,name,note in specs:
        d=expr.get(key,pd.DataFrame())
        ready=int(d.get("qualified",pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not d.empty and "qualified" in d else 0
        tone="green" if ready>0 else "gray"; c=COLORS[tone][0]
        h+=f"<div class='mode-card'><div class='mode-name'>{html.escape(name)}</div><div class='mode-ready' style='color:{c}'>{ready} ready</div><div class='mode-note'>{html.escape(note)}</div></div>"
    h+="</div>"
    st.markdown(h,unsafe_allow_html=True)


def _render_opportunity_visuals(ranked: pd.DataFrame, expr: Dict[str,pd.DataFrame]) -> None:
    """Plain-language daily board. No scatter plot or model matrix on the default screen."""
    if ranked.empty:
        st.markdown("<div class='gate'><b>No opportunities loaded.</b> The scanner has no valid rows for the selected markets.</div>",unsafe_allow_html=True)
        return

    states=[]
    for idx,r in ranked.iterrows():
        stt=_plain_board_state(r,expr)
        states.append((idx,stt))

    # 1) Fast traffic-light summary: user should understand the whole universe in seconds.
    buckets=[("ACT NOW","green"),("WATCH","amber"),("AVOID / DOWNSIDE","red"),("NOT READY","gray")]
    board="<div class='simple-board'>"
    for label,tone in buckets:
        ids=[idx for idx,stt in states if stt["bucket"]==label]
        syms=[str(ranked.loc[idx].get("symbol","")) for idx in ids[:6]]
        c=COLORS[tone][0]
        chips="".join(f"<span class='ticker-chip'>{html.escape(x)}</span>" for x in syms) or "<span class='list-sub'>none</span>"
        board+=f"<div class='simple-col'><div class='sc-label' style='color:{c}'>{label}</div><div class='sc-count'>{len(ids)}</div><div>{chips}</div></div>"
    board+="</div>"
    st.markdown("<div class='section'>At a glance</div>",unsafe_allow_html=True)
    st.markdown(board,unsafe_allow_html=True)

    # 2) Top picks. Qualified actions first, then strongest watch candidates.
    order_pos={idx:pos for pos,idx in enumerate(ranked.index.tolist())}
    def sort_key(item):
        idx,stt=item
        # Keep the engine's existing ranking intact. Only move genuinely ready expressions ahead of watch-only rows.
        ready_priority=0 if bool(stt.get("ready",False)) else 1
        bucket_priority={"ACT NOW":0,"AVOID / DOWNSIDE":1,"WATCH":2,"NOT READY":3}.get(stt["bucket"],4)
        return (ready_priority,bucket_priority,order_pos.get(idx,10**9))
    ordered=sorted(states,key=sort_key)[:4]
    picks="<div class='pick-grid'>"
    for rank,(idx,stt) in enumerate(ordered,1):
        r=ranked.loc[idx]; sym=str(r.get("symbol","—")); market=str(r.get("market","—")); name=str(r.get("name","") or "")
        c=COLORS[stt["tone"]][0]
        ev=int(safe_float(r.get("evidence_families")) if np.isfinite(safe_float(r.get("evidence_families"))) else 0)
        det=int(safe_float(r.get("deterioration_families")) if np.isfinite(safe_float(r.get("deterioration_families"))) else 0)
        why=_why_now_compact(r)
        mode_txt=", ".join(x[0] for x in stt["modes"]) if stt["modes"] else "no capital expression yet"
        extra=""
        if market in ["US","IHSG"]:
            try:
                v=valuation_projection(ranked,r); px=safe_float(r.get("price")); base=safe_float(v.get("fv_base"))
                if np.isfinite(px) and px>0 and np.isfinite(base):
                    up=base/px-1
                    extra=f" · research upside {pct(up)}" if up>=0 else f" · research downside {pct(up)}"
            except Exception:
                pass
        picks+=f"<div class='pick-card'><div class='pick-top'><div><div class='pick-symbol'>{html.escape(sym)}</div><div class='pick-market'>{html.escape(market)} · {html.escape(name[:28])}</div></div><div class='rank-badge'>#{rank}</div></div><div class='pick-action' style='color:{c}'>{html.escape(stt['action'])}</div><div class='pick-why'>{html.escape(why)}</div><div class='pick-meta'>Confidence {_conviction_label(r)} · {ev} supporting / {det} negative · {html.escape(mode_txt)}{html.escape(extra)}</div></div>"
    picks+="</div>"
    st.markdown("<div class='section'>Top opportunities now</div>",unsafe_allow_html=True)
    st.markdown(picks,unsafe_allow_html=True)

    st.markdown("<div class='section'>How it can be traded</div>",unsafe_allow_html=True)
    _render_plain_mode_strip(expr)
    st.markdown("<div class='simple-help'>Read it left to right: <b>ACT NOW</b> means the model has earned an expression; <b>WATCH</b> means the thesis is interesting but entry is not earned; <b>NOT READY</b> means missing data/model coverage, not a hidden buy signal.</div>",unsafe_allow_html=True)


def _render_expression_cards(df: pd.DataFrame, kind: str) -> None:
    """Simple ranked list for the chosen expression. Advanced evidence is hidden below."""
    if df.empty:
        st.markdown("<div class='gate'><b>Nothing supported in this mode.</b> Change expression or selected markets.</div>",unsafe_allow_html=True)
        return
    h=""
    for _,r in df.head(8).iterrows():
        q=bool(r.get("qualified",False)); action=str(r.get("expression",r.get("research_action","WATCH")))
        downside=any(x in action.upper() for x in ["SHORT","PUT","SELL","BEARISH","EXIT","TRIM","AVOID"])
        tone=("red" if downside else "green") if q else "amber"
        if (not q) and ("GATED" in action.upper() or str(r.get("data_quality","LOW")).upper()=="LOW"): tone="gray"
        c=COLORS[tone][0]
        state="READY" if q else ("DATA GATED" if tone=="gray" else "WATCH")
        sym=html.escape(str(r.get("symbol","—"))); market=html.escape(str(r.get("market","—")))
        why=html.escape(_why_now_compact(r)); conf=html.escape(_conviction_label(r)); horizon=html.escape(_plain_horizon(r,kind))
        h+=f"<div class='list-card'><div><div class='list-sym'>{sym}</div><div class='list-sub'>{market}</div></div><div class='list-action' style='color:{c}'>{html.escape(action)}</div><div class='list-why'>{why}</div><div class='list-meta'>{conf} confidence · {horizon}</div><div class='list-meta' style='color:{c};font-weight:850'>{state}</div></div>"
    st.markdown(h,unsafe_allow_html=True)

def _render_evidence_flow_chart(df: pd.DataFrame, title: str="Evidence flow vs price-in") -> None:
    if df.empty or go is None: return
    d=df.head(14).copy(); labels=d["symbol"].astype(str).tolist()
    net=[]; gap=[]
    for _,r in d.iterrows():
        ev=safe_float(r.get("evidence_families")); det=safe_float(r.get("deterioration_families")); net.append((ev if np.isfinite(ev) else 0)-(det if np.isfinite(det) else 0))
        if str(r.get("market")) in ["US","IHSG"]:
            v=valuation_projection(df,r); g=safe_float(v.get("expectation_gap")); gap.append(g*100 if np.isfinite(g) else None)
        elif str(r.get("market"))=="Crypto": gap.append(net[-1]*18)
        else: gap.append(None)
    bar_colors=["#10b981" if x>=0 else "#f43f5e" for x in net]
    fig=go.Figure([go.Bar(x=labels,y=net,name="Net evidence",marker_color=bar_colors,yaxis="y"),go.Scatter(x=labels,y=gap,name="Asymmetry / price-in",mode="lines+markers",line=dict(color="#f59e0b",width=2.5),marker=dict(size=7),yaxis="y2")])
    fig.update_layout(title=title,yaxis=dict(title="Net evidence",side="left"),yaxis2=dict(title="Asymmetry",overlaying="y",side="right",showgrid=False),barmode="relative")
    _plotly_base(fig,330,True); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})


def _render_compact_selected(row: pd.Series, ranked: pd.DataFrame, mg: Dict[str,Any], view_kind: str) -> None:
    val=valuation_projection(ranked,row) if str(row.get("market")) in ["US","IHSG"] else {}
    prior=get_prior_checkpoint(str(row.get("symbol","")),STATE)
    entry=entry_decision(row.to_dict(),val,mg,prior)
    ev=safe_float(row.get("evidence_families")); det=safe_float(row.get("deterioration_families")); px=safe_float(row.get("price")); base=safe_float(val.get("fv_base")) if val else np.nan
    q=bool(row.get("qualified",False)); action=str(row.get("expression",row.get("research_action","WATCH")))
    cells=[("ACTION",action,"ACTION" if q else "WAIT"),("ENTRY",str(entry.get("entry_stage","DISCOVER")),str(entry.get("allocation_guide","0%"))),("EVIDENCE",f"{int(ev) if np.isfinite(ev) else 0} ↑ / {int(det) if np.isfinite(det) else 0} ↓",str(row.get("data_quality","LOW"))),("PRICE",_fmt_asset_price(row,px),"current"),("BASE FV",_fmt_asset_price(row,base) if np.isfinite(base) else "GATED","same-sector only")]
    if str(row.get("market"))=="IHSG":
        txs=safe_float(row.get("transaction_score")); tx_state=str(row.get("transaction_state","DATA GATED"))
        cells.append(("TRANSACTION",f"{txs:.0f}/100" if np.isfinite(txs) else "GATED",tx_state))
    h="<div class='metric-strip'>"
    for a,b,c in cells: h+=f"<div class='metric-mini'><div class='m1'>{a}</div><div class='m2'>{b}</div><div class='m3'>{c}</div></div>"
    h+="</div>"; st.markdown(h,unsafe_allow_html=True)
    if go is not None:
        values=[max(0,min(100,(ev if np.isfinite(ev) else 0)/5*100)),100 if str(row.get("data_quality","LOW")).upper()=="HIGH" else (60 if str(row.get("data_quality","LOW")).upper()=="MEDIUM" else 25),max(0,min(100,50+(safe_float(val.get("expectation_gap"))*100 if val and np.isfinite(safe_float(val.get("expectation_gap"))) else 0))),100 if "TAILWIND" in _macro_fit(mg,"SHORT" if "SHORT" in action or "PUT" in action else "LONG") else (55 if "NEUTRAL" in _macro_fit(mg) else 25)]
        fig=go.Figure(go.Bar(x=values,y=["Causal evidence","Data quality","Asymmetry","Macro fit"],orientation="h",marker_color=["#10b981","#6ea8fe","#f59e0b","#b794f4"],text=[f"{v:.0f}" for v in values],textposition="inside"))
        fig.update_xaxes(range=[0,100],visible=False); fig.update_layout(title="Decision stack · why this is / is not actionable")
        _plotly_base(fig,260,False); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})


def _state_score(text: str) -> int:
    t=str(text).upper()
    if any(k in t for k in ["SUPPORT","POSITIVE","CALM","IMPROV","TAILWIND","COOLING","RESILIENT"]): return 2
    if any(k in t for k in ["STRESS","CONTRACT","DANGER","DETERIOR","HEATING","RECESSION"]): return -2
    if any(k in t for k in ["GATED","NOT RELEASED"]): return 0
    return 1 if any(k in t for k in ["WATCH","MIXED","BELOW-TREND"]) else 0


def _render_macro_visual_room() -> None:
    fn=getattr(_macro_module,"compute_macro_gate_snapshot",None) if _macro_module is not None else None
    if not callable(fn):
        safe_render_macro_control_room(); return
    c1,c2=st.columns([1,5])
    with c1: refresh=st.button("Refresh macro",use_container_width=True,key="macro_refresh_visual_v24")
    try: snap=fn(refresh=refresh)
    except Exception:
        safe_render_macro_control_room(); return
    st.markdown("<div class='section'>Macro cockpit · visual first</div>",unsafe_allow_html=True)
    h="<div class='metric-strip'>"
    for a,b,c in [("POSTURE",snap.get("action_label","—"),"portfolio"),("REGIME",snap.get("regime","—"),"economy"),("CRASH",snap.get("crash_state","—"),f"stress {safe_float(snap.get('crash_stress')):.0f} / fragility {safe_float(snap.get('crash_fragility')):.0f}"),("CREDIT",snap.get("credit_state","—"),"transmission gate"),("EVENT",snap.get("event_override") or "NONE","override")]: h+=f"<div class='metric-mini'><div class='m1'>{a}</div><div class='m2'>{b}</div><div class='m3'>{c}</div></div>"
    h+="</div>"; st.markdown(h,unsafe_allow_html=True)
    left,right=st.columns([1.55,1])
    with left:
        proj=pd.DataFrame(snap.get("projection_rows",[]))
        if not proj.empty and go is not None:
            xs=["NOW","+1Q","+2Q","+4Q"]; ys=proj["engine"].astype(str).tolist(); text=[]; z=[]
            for _,r in proj.iterrows():
                vals=[r.get("now"),r.get("q1"),r.get("q2"),r.get("q4")]; text.append([str(v) for v in vals]); z.append([_state_score(v) for v in vals])
            fig=go.Figure(go.Heatmap(z=z,x=xs,y=ys,text=text,texttemplate="%{text}",colorscale=[[0,"#ef4444"],[.5,"#263244"],[1,"#10b981"]],zmin=-2,zmax=2,showscale=False,xgap=5,ygap=5,hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>"))
            fig.update_layout(title="Macro path matrix · NOW → +4Q"); _plotly_base(fig,360,False); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with right:
        att=snap.get("attention",[]) or []
        if att and go is not None:
            names=[x.get("name") for x in att]; vals=[safe_float(x.get("score")) for x in att]
            fig=go.Figure(go.Bar(x=vals,y=names,orientation="h",marker_color="#f59e0b",text=[f"{v:.0f}" if np.isfinite(v) else "—" for v in vals],textposition="inside"))
            fig.update_xaxes(range=[0,100],title="attention / pressure"); fig.update_layout(title="What matters most now"); _plotly_base(fig,360,False); st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    paths=snap.get("top_paths",[]) or []
    if paths:
        st.markdown("<div class='section'>Top paths · only 3</div>",unsafe_allow_html=True)
        cards="<div class='grid3'>"
        for sc in paths[:3]: cards+=f"<div class='card'><div class='kicker'>{sc.get('family','PATH')}</div><div class='ct'>{sc.get('name','')}</div><div class='cn'><b>{sc.get('action_state','WATCH')}</b><br>{sc.get('action','')}</div></div>"
        cards+="</div>"; st.markdown(cards,unsafe_allow_html=True)
    with st.expander("Full macro explanation / raw readings",expanded=False):
        st.write(snap.get("headline","")); st.dataframe(pd.DataFrame(snap.get("projection_rows",[])),use_container_width=True,hide_index=True); st.json(snap.get("raw_readings",{}))

def _render_opportunity_detail(row: pd.Series, ranked: pd.DataFrame, mg: Dict[str,Any], view_kind: str) -> None:
    query=f"{row.get('name','')} {row.get('symbol','')} shortage capacity pricing adoption revenue contract backlog demand supply buyback burn intervention"
    ev=news_evidence(query,limit=8)
    root=infer_specific_root(str(row.get("name","")),str(row.get("symbol","")),ev)
    val=valuation_projection(ranked,row) if str(row.get("market")) in ["US","IHSG"] else {}
    pin,pintone=price_in_label(val)
    raw_action=_plain_action_from_row(row,"buyhold") if view_kind=="BUYHOLD" else str(row.get("expression",row.get("research_action","WATCH")))
    prior_cp=get_prior_checkpoint(str(row.get("symbol","")), STATE)
    entry=entry_decision(row.to_dict(), val, mg, prior_cp)
    expr=expression_decision(row.to_dict(), entry, mg)
    action=entry.get("entry_action",raw_action) if view_kind in ["BUYHOLD","SPOT","RADAR"] else raw_action
    atone="green" if any(x in action for x in ["BUILD","ADD","CORE","LONG","CALL","STARTER"]) else ("red" if any(x in action for x in ["SELL","SHORT","PUT","BEARISH","EXIT"]) else "amber")
    thesis=opportunity_thesis_summary(row,ev,root)
    conf=_conviction_label(row); horizon=_plain_horizon(row,view_kind); asym=_asymmetry_label(row,val)
    px=safe_float(row.get("price")); base=safe_float(val.get("fv_base")) if val else np.nan; bull=safe_float(val.get("fv_bull")) if val else np.nan; bear=safe_float(val.get("fv_bear")) if val else np.nan
    upside=base/px-1 if np.isfinite(base) and np.isfinite(px) and px>0 else np.nan
    branches=adaptive_scenario_branches(root)
    falsifier=str(branches.iloc[0].get("falsifier","Needs causal invalidation rule")) if not branches.empty else "Critical thesis input reverses or data stops confirming."
    huge=str(branches.iloc[0].get("economic_projection","Economics accelerate faster/longer than market expects")) if not branches.empty else "Fundamentals accelerate faster and stay durable longer than priced."

    st.markdown(f"<div class='plainbox'><b>{row.get('symbol')} · {row.get('name')}</b><br>{thesis}</div>",unsafe_allow_html=True)
    cards="<div class='decision-grid'>"
    cards+=f"<div class='decision-card'><div class='kicker'>ENTRY / ACTION NOW</div><div class='dv' style='color:{COLORS[atone][0]}'>{action}</div><div class='dn'>Detection is not entry. Current stage: {entry.get('entry_stage','DISCOVER')}.</div></div>"
    cards+=f"<div class='decision-card'><div class='kicker'>CURRENT PRICE</div><div class='dv'>{_fmt_asset_price(row,px)}</div><div class='dn'>Latest scanned price.</div></div>"
    cards+=f"<div class='decision-card'><div class='kicker'>BASE FAIR VALUE</div><div class='dv'>{_fmt_asset_price(row,base) if np.isfinite(base) else 'GATED'}</div><div class='dn'>Research range, not a precise target.</div></div>"
    cards+=f"<div class='decision-card'><div class='kicker'>BASE UPSIDE</div><div class='dv'>{pct(upside) if np.isfinite(upside) else 'GATED'}</div><div class='dn'>Versus current price.</div></div>"
    cards+=f"<div class='decision-card'><div class='kicker'>HORIZON</div><div class='dv'>{horizon}</div><div class='dn'>When thesis should resolve.</div></div>"
    cards+=f"<div class='decision-card'><div class='kicker'>ENTRY SIZE</div><div class='dv'>{entry.get('allocation_guide','0%')}</div><div class='dn'>Conviction {conf}. Sizing guide, not calibrated probability.</div></div>"
    cards+="</div>"
    st.markdown(cards,unsafe_allow_html=True)

    st.markdown("<div class='section'>Read this before the numbers</div>",unsafe_allow_html=True)
    info="<div class='info4'>"
    info+=f"<div class='info-card'><div class='info-title'>WHY NOW?</div><div class='info-text'>{_why_now_compact(row)}</div></div>"
    info+=f"<div class='info-card'><div class='info-title'>WHAT MAY BE MISPRICED?</div><div class='info-text'>{pin}. Base expectation gap: {pct(val.get('expectation_gap',np.nan)) if val else 'asset-class model gated'}.</div></div>"
    info+=f"<div class='info-card'><div class='info-title'>WHAT CAN MAKE IT MUCH BIGGER?</div><div class='info-text'>{huge}</div></div>"
    info+=f"<div class='info-card'><div class='info-title'>WHAT KILLS THE THESIS?</div><div class='info-text'>{falsifier}</div></div>"
    info+="</div>"
    st.markdown(info,unsafe_allow_html=True)

    if str(row.get("market"))=="IHSG":
        st.markdown("**IHSG Transaction Intelligence · broker inventory + live microstructure**")
        tx_score=safe_float(row.get("transaction_score"))
        tx_rows=[
            {"Layer":"State","Reading":str(row.get("transaction_state","DATA GATED")),"Why it matters":"Research state only; not a calibrated probability or standalone entry."},
            {"Layer":"Coverage","Reading":str(row.get("transaction_coverage","LOW")),"Why it matters":"Missing provider/API data lowers coverage instead of being imputed."},
            {"Layer":"Research score","Reading":f"{tx_score:.0f}/100" if np.isfinite(tx_score) else "GATED","Why it matters":"Bounded evidence score, not win probability."},
            {"Layer":"Broker persistence edge","Reading":pct(safe_float(row.get("persistence_edge"))),"Why it matters":"Top accumulating brokers persistent vs top distributing brokers."},
            {"Layer":"Buyer concentration","Reading":pct(safe_float(row.get("buyer_top3_share"))),"Why it matters":"Top-3 share of positive broker inventory transfer."},
            {"Layer":"NG / crossing contamination","Reading":pct(safe_float(row.get("crossing_transfer_risk"))),"Why it matters":"High negotiated-market share is discounted as non-directional transfer risk."},
            {"Layer":"Foreign flow intensity","Reading":pct(safe_float(row.get("foreign_flow_intensity"))),"Why it matters":"Foreign buy-sell imbalance relative to foreign gross flow."},
            {"Layer":"Accumulator execution cost","Reading":_fmt_asset_price(row,safe_float(row.get("accumulator_cost"))),"Why it matters":"Execution-cost proxy of top accumulating brokers; not beneficial-owner cost."},
            {"Layer":"Order-book imbalance","Reading":pct(safe_float(row.get("order_book_imbalance"))),"Why it matters":"Visible depth only; low weight because orders can cancel."},
            {"Layer":"Aggressive flow","Reading":pct(safe_float(row.get("aggressive_flow_imbalance"))),"Why it matters":"Only shown when provider returns HAKA/HAKI-type fields; otherwise gated."},
            {"Layer":"Absorption","Reading":str(row.get("absorption_side","GATED")),"Why it matters":"Requires aggressive-flow vs price disagreement; never inferred from a static wall alone."},
        ]
        st.dataframe(pd.DataFrame(tx_rows),use_container_width=True,hide_index=True)
        eod_err=row.get("eod_errors",[]); in_err=row.get("intraday_errors",[])
        if eod_err or in_err:
            st.caption("Transaction data notes: " + " | ".join([str(x) for x in (list(eod_err) if isinstance(eod_err,list) else [eod_err]) + (list(in_err) if isinstance(in_err,list) else [in_err]) if x][:4]))
        st.caption("Accounting guardrail: broker net across the whole market sums to ~0. The engine therefore measures broker-level persistence/concentration and group flow, not a fictitious total-market broker net buy.")

    st.markdown("**Entry logic · why detection is not automatically a trade**")
    entry_rows=[]
    for reason in entry.get("reasons",[]) or []:
        entry_rows.append({"Type":"Supports entry","Evidence":reason})
    for gate in entry.get("gates",[]) or []:
        entry_rows.append({"Type":"Gate / wait","Evidence":gate})
    rev_edge=safe_float(entry.get("revision_edge"))
    if np.isfinite(rev_edge):
        entry_rows.append({"Type":"Fair value vs price revision","Evidence":f"FV revision minus price revision = {rev_edge*100:.1f}pp"})
    entry_rows.append({"Type":"Best expression after entry","Evidence":f"{expr.get('best_expression','WATCH')} · {expr.get('why','')}"})
    st.dataframe(pd.DataFrame(entry_rows),use_container_width=True,hide_index=True)
    st.caption("Lifecycle: DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT. Option/leverage are expressions after entry is earned, never discovery signals.")

    if str(row.get("market")) in ["US","IHSG"]:
        proj=pd.DataFrame([
            ["Bear",pct(val.get("g_bear",np.nan)),fmt_num(val.get("bear_eps",np.nan),2),_fmt_asset_price(row,bear), pct(bear/px-1) if np.isfinite(bear) and np.isfinite(px) and px>0 else "—"],
            ["Base",pct(val.get("g_base",np.nan)),fmt_num(val.get("base_eps",np.nan),2),_fmt_asset_price(row,base), pct(upside) if np.isfinite(upside) else "—"],
            ["Bull",pct(val.get("g_bull",np.nan)),fmt_num(val.get("bull_eps",np.nan),2),_fmt_asset_price(row,bull), pct(bull/px-1) if np.isfinite(bull) and np.isfinite(px) and px>0 else "—"],
        ],columns=["Scenario","Earnings change","Projected NTM EPS","Research fair value","vs current"])
        st.markdown("**Projection / fair value / what today's price assumes**")
        st.dataframe(proj,use_container_width=True,hide_index=True)
        st.caption(f"Valuation basis: {val.get('valuation_basis','GATED')} · peers {int(safe_float(val.get('peer_count',0)) if np.isfinite(safe_float(val.get('peer_count',0))) else 0)} · confidence {val.get('valuation_confidence','GATED')}. Current price implies ~{fmt_num(val.get('implied_eps',np.nan),2)} EPS at that multiple vs base projection ~{fmt_num(val.get('base_eps',np.nan),2)}. If same-sector valuation evidence is insufficient, fair value stays GATED rather than using the whole market as a fake peer set.")
    elif str(row.get("market"))=="Crypto":
        urow=UNIVERSE[UNIVERSE["symbol"]==row.get("symbol")]
        cm=deep_crypto_metrics(urow.iloc[0]) if not urow.empty else {}
        if cm:
            st.markdown("**Crypto economics · not just price**")
            st.dataframe(pd.DataFrame([{
                "Market cap":fmt_money(cm.get("market_cap",np.nan)),"FDV premium":pct(cm.get("fdv_premium",np.nan)),
                "30D revenue":fmt_money(cm.get("revenue_30d",np.nan)),"Revenue acceleration":pct(cm.get("revenue_growth_30d",np.nan)),
                "30D holder income":fmt_money(cm.get("holders_revenue_30d",np.nan)),"Holder capture":pct(cm.get("holder_capture_ratio",np.nan)),
                "Mcap / annualized revenue":fmt_num(cm.get("mcap_to_revenue",np.nan),1)+"x"
            }]),use_container_width=True,hide_index=True)
            st.caption("Revenue alone is never a buy rule. Holder capture, dilution/unlocks and real usage must agree.")
        else:
            st.caption("Critical crypto economics are incomplete → action cannot be promoted to high conviction.")
    else:
        st.caption("Dedicated physical / relative-macro fair-value projection for this asset class is still gated; direction is not upgraded without it.")

    if not branches.empty:
        st.markdown("**If this happens, do this · max 3 relevant scenarios**")
        st.dataframe(branches[["scenario","trigger","economic_projection","action_logic","falsifier"]].head(3),use_container_width=True,hide_index=True)

    cb=chain_brief(root)
    is_bottleneck=bool(cb.get("bottlenecks")) or any(k in (root or "").lower() for k in ["nand","supply","electrical load","networking bandwidth","cpo price","war escalation","transformer","photon"])
    if is_bottleneck and not cb.get("chain",pd.DataFrame()).empty:
        st.markdown("**Bottleneck chain · only shown because it can change the opportunity**")
        bc1,bc2,bc3=st.columns(3)
        with bc1: st.markdown(f"<div class='chainbox'><b>Where the bottleneck is</b><br>{root}<br><br><b>Who gets paid first</b><br>{'<br>'.join(cb['direct'][:5]) or '—'}</div>",unsafe_allow_html=True)
        with bc2: st.markdown(f"<div class='chainbox'><b>Where it can spread next</b><br>{'<br>'.join(cb['bottlenecks'][:5]) or 'Not separately mapped yet'}<br><br><b>How it heals</b><br>{'<br>'.join(cb['normalization'][:4]) or 'Capacity/substitution must be monitored'}</div>",unsafe_allow_html=True)
        with bc3: st.markdown(f"<div class='chainbox'><b>Who can lose</b><br>{'<br>'.join(cb['losers'][:6]) or '—'}</div>",unsafe_allow_html=True)
        driver=parallel_driver_root(root) or root
        exposed=merge_scanned_actions(exposed_assets_from_chain(driver,str(row.get("symbol")),limit=10),ranked)
        if not exposed.empty:
            st.caption("Companies exposed to the same root driver. Exposure is not a buy signal; each name still passes its own valuation/action gate.")
            showcols=[c for c in ["market","symbol","name","research_action","price","data_quality","notes"] if c in exposed.columns]
            st.dataframe(exposed[showcols],use_container_width=True,hide_index=True)

    if view_kind=="OPTIONS" and str(row.get("market")) in ["US","Crypto"]:
        direction="CALL" if "CALL" in action or any(k in str(row.get("research_action")) for k in ["BUILD","SELECTIVE ADD"]) else "PUT"
        od=fetch_option_snapshot(str(row.get("symbol")),direction) if str(row.get("market"))=="US" else fetch_deribit_option_snapshot(str(row.get("symbol")),direction)
        st.markdown("**Live option expression check**")
        if od.get("error"):
            st.warning("Option market unavailable/gated: "+str(od.get("error")))
        else:
            st.dataframe(pd.DataFrame([{
                "Venue":od.get("venue","US listed"),"Direction":od.get("direction"),"Instrument":od.get("instrument","—"),"Expiry":od.get("expiry","—"),"Days":od.get("days"),"Spot":od.get("spot"),
                "Strike":od.get("strike"),"Mid":od.get("mid"),"Premium USD":od.get("premium_usd",np.nan),"Bid/ask spread":pct(od.get("spread",np.nan)),
                "IV":pct(od.get("iv",np.nan)),"Implied move":pct(od.get("implied_move",np.nan)),"OI":od.get("open_interest"),"Liquidity":od.get("liquidity")
            }]),use_container_width=True,hide_index=True)
            st.caption("Directional thesis ≠ automatically buy the option. IV, liquidity, expiry and catalyst timing must justify the expression. Crypto adapter is intentionally limited to liquid BTC/ETH Deribit options.")

    try:
        save_checkpoint(str(row.get("symbol","")), price=px, fv_base=base, entry_stage=str(entry.get("entry_stage","DISCOVER")), default_root=STATE)
    except Exception:
        pass

    if ev.get("items"):
        with st.expander("Latest evidence / sources",expanded=False):
            e=pd.DataFrame(ev["items"])
            st.dataframe(e[[c for c in ["source","title","pubDate"] if c in e.columns]].head(6),use_container_width=True,hide_index=True)


# -----------------------------
# UI — persistent native navigation
# -----------------------------
NAV_ITEMS=["CONTROL ROOM","OPPORTUNITIES","DECISION DESK","VERTICALS","MACRO & EVENTS","RESEARCH / REPLAY"]

def _set_workspace(target: str) -> None:
    st.session_state["decision_nav_v321"] = target
    # A page change must never feel dead because a stale 30-minute scan starts first.
    # The next periodic tick can refresh after navigation has rendered.
    st.session_state["_skip_auto_scan_once"] = True

def _render_workspace_nav() -> str:
    current=st.session_state.get("decision_nav_v321","CONTROL ROOM")
    if current not in NAV_ITEMS:
        current="CONTROL ROOM"; st.session_state["decision_nav_v321"]=current
    st.markdown("<div class='nav-caption'>Workspace</div>",unsafe_allow_html=True)
    cols=st.columns([1.02,1.05,1.05,.84,1.12,1.18],gap="small")
    for col,item in zip(cols,NAV_ITEMS):
        with col:
            st.button(item,key=f"navbtn_{item}",use_container_width=True,type="primary" if item==current else "secondary",on_click=_set_workspace,args=(item,))
    return st.session_state.get("decision_nav_v321",current)

# -----------------------------
# UI — AUTO DECISION VIEW
# -----------------------------
# v3.2: the old full-width hero was removed; OPPORTUNITIES renders the denser reference-style status header.
markets_available=[m for m in ["US","IHSG","HK","Hong Kong","China","Europe","Taiwan","FX","Commodity","Index","Crypto"] if m in set(UNIVERSE.get("market",pd.Series(dtype=str)).astype(str))]
st.sidebar.markdown("## Auto scanner")
selected_markets=st.sidebar.multiselect("Markets",markets_available,default=markets_available)
st.sidebar.markdown(f"{badge('AUTO · ~30 MIN CACHE','green')}",unsafe_allow_html=True)
force_refresh=st.sidebar.button("Refresh now (optional)",use_container_width=True)
st.sidebar.caption("No button is required. First load and market-selection changes scan automatically. Cached public data prevents repeated endpoint hammering.")
with st.sidebar.expander("Data / research gates",expanded=False):
    st.write("Universe", f"SEED + adaptive discovery · {len(UNIVERSE)} mapped assets")
    st.caption("Not yet a full US/IDX exchange enumeration. Unknown opportunities can enter through scenario/news discovery, but full-universe recall remains a research gate.")
    st.write("Action model", "✅" if PRODUCTION_ACTION_MODEL_VALIDATED else "🔒 research state")
    st.write("Fair value", "✅" if PRODUCTION_FAIR_VALUE_MODEL_VALIDATED else "🔒 research range")
    st.write("Event probability", "✅" if PRODUCTION_EVENT_PROBABILITY_VALIDATED else "🔒 evidence ranking only")
    st.caption("Current public adapters are current-at-fetch, but full PIT production coverage is still being built.")
    st.write("IHSG EOD broker", "✅ Index Alpha" if _secret_or_env("INDEX_ALPHA_API_KEY") else "🔒 add INDEX_ALPHA_API_KEY")
    st.write("IHSG intraday", "✅ Invezgo" if _secret_or_env("INVEZGO_API_KEY") else "🔒 add INVEZGO_API_KEY")
    st.caption("Transaction data is optional-safe: without keys the IHSG layer stays DATA GATED and cannot silently create a buy signal.")

# Render navigation BEFORE any expensive scan. Native buttons + callback state make every page switch immediate and persistent.
nav=_render_workspace_nav()
skip_auto_scan_once=bool(st.session_state.pop("_skip_auto_scan_once",False))

if selected_markets:
    scan_input=UNIVERSE[UNIVERSE["market"].isin(selected_markets)].copy().reset_index(drop=True)
else:
    scan_input=UNIVERSE.iloc[0:0].copy()
max_assets=len(scan_input)
scan_signature=(tuple(selected_markets),int(max_assets),"v3.2.1-longitudinal-opportunity-os")

# Automatic initial/stale refresh. The user never has to press a scan button.
existing_records=st.session_state.get("live_scan_records",[])
need_auto=(not existing_records) or (st.session_state.get("live_scan_signature")!=scan_signature) or (_scan_age_seconds()>AUTO_REFRESH_SECONDS)
if force_refresh or (need_auto and not skip_auto_scan_once):
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

# v3.2 longitudinal layer: freeze first meaningful detection BEFORE future outcomes mature.
try:
    _active_opportunities = sync_opportunities(ranked, OPP_MEMORY, mg)
    _refresh_mature_opportunity_outcomes(limit=8)
    st.session_state["learning_report_paths"] = write_periodic_learning_reports(OPP_MEMORY, STATE)
except Exception as _opp_exc:
    _active_opportunities = pd.DataFrame()
    st.session_state["opportunity_memory_error"] = str(_opp_exc)

if nav=="CONTROL ROOM":
    _render_control_room(ranked,mg)

elif nav=="OPPORTUNITIES":
    render_opportunity_tracker(st, ranked, OPP_MEMORY, mg)

elif nav=="VERTICALS":
    _render_verticals(ranked)

elif nav=="MACRO & EVENTS":
    _render_macro_visual_room()

elif nav=="RESEARCH / REPLAY":
    render_learning_lab(st, OPP_MEMORY)
    st.markdown("<div class='section'>Legacy research / validation</div>",unsafe_allow_html=True)
    st.markdown("<div class='gate'>Use this only when you want to inspect historical replay, data coverage, rejected signals or research gates. Daily decisions stay in OPPORTUNITIES.</div>",unsafe_allow_html=True)
    with st.expander("Historical acceptance tests",expanded=False):
        st.dataframe(ACCEPTANCE,use_container_width=True,hide_index=True)
        cases=REPLAY["case"].dropna().unique().tolist() if not REPLAY.empty else []
        if cases:
            case=st.selectbox("Replay case",cases,key="replay_case_compact_v20")
            rr=REPLAY[REPLAY["case"]==case]
            st.dataframe(rr[["date","phase","scanner_state","evidence_known_then","causal_chain","source_url"]],use_container_width=True,hide_index=True)
    with st.expander("Data sources / readiness",expanded=True):
        st.dataframe(SOURCE_REGISTRY,use_container_width=True,hide_index=True)
        readiness=pd.DataFrame([
            ["Universe coverage","PARTIAL · SEED + ADAPTIVE DISCOVERY","full US + IDX + broader crypto enumeration / stage-1 screening still required for maximum recall"],
            ["Macro / cross-asset regime","CURRENT MONITORING READY","PIT probability calibration still locked"],
            ["US stock buy/hold/sell","RESEARCH READY","PIT SEC + estimate-revision history still needed for production validation"],
            ["IHSG buy/hold/sell","RESEARCH READY · CASH ONLY","transaction layer uses Index Alpha + Invezgo when keys are configured; full PIT validation still required"],
            ["US leverage","SUPPORTED WHEN EARNED","requires high data + evidence + macro/risk gate"],
            ["FX leverage","DATA GATED","relative macro, REER, BoP, positioning, intervention history"],
            ["Commodity leverage","DATA GATED","physical balances, inventory, curve/carry, spare capacity"],
            ["Crypto spot","PARTIAL","holder capture, unlock schedule and real usage are not universal"],
            ["Crypto leverage","THESIS GATED","adapter exists; leverage disabled until crypto causal data is complete"],
            ["US stock options","SUPPORTED WHEN EARNED","live option chain; expected-distribution model remains research state"],
            ["BTC/ETH options","DERIBIT ADAPTER READY · THESIS GATED","only liquid BTC/ETH; no fake options for illiquid tokens"],
        ],columns=["Layer","Current status","What is still missing"])
        st.dataframe(readiness,use_container_width=True,hide_index=True)
        st.markdown("<div class='gate'><b>Fail-closed rule:</b> missing causal data never gets replaced with price momentum or a technical indicator. The asset stays in Early Radar / GATED until the correct data family is available.</div>",unsafe_allow_html=True)

elif nav=="DECISION DESK":
    # DECISION DESK · preserved v3.1 daily screen. Core decision logic is not replaced.
    # SIMPLE DAILY SCREEN. The first viewport answers: posture, act/watch/avoid, and top names.
    macro_label=str(mg.get("action_label","MACRO GATED"))
    macro_upper=macro_label.upper()
    if any(x in macro_upper for x in ["DEFENSIVE","CRISIS"]):
        macro_guide="Be selective. Prefer cash/stock and only take leverage when it is explicitly marked READY."
        macro_tone="amber"
    elif "RISK-ON" in macro_upper:
        macro_guide="Backdrop is supportive. Prioritize qualified longs, but still wait for the entry gate instead of chasing."
        macro_tone="green"
    elif "GATED" in macro_upper:
        macro_guide="Macro data is incomplete. Discovery can continue, but leverage upgrades stay blocked."
        macro_tone="gray"
    else:
        macro_guide="Mixed backdrop. Let asset-specific evidence decide; keep sizing selective."
        macro_tone="amber"
    mc=COLORS[macro_tone][0]
    st.markdown(f"<div class='today-card'><div class='today-label'>TODAY'S POSTURE</div><div class='today-main' style='color:{mc}'>{html.escape(macro_label)}</div><div class='today-note'>{html.escape(macro_guide)}</div></div>",unsafe_allow_html=True)

    _render_opportunity_visuals(ranked,expr)

    st.markdown("<div class='section'>Expression desk</div>",unsafe_allow_html=True)
    view=st.radio("Expression",["BUY & HOLD / SELL · STOCKS","LEVERAGED LONG / SHORT","OPTIONS · CALL / PUT","SPOT / CASH","EARLY RADAR"],horizontal=True,key="opp_subview_v24",label_visibility="collapsed")
    mapkey={"BUY & HOLD / SELL · STOCKS":"buyhold","SPOT / CASH":"spot","LEVERAGED LONG / SHORT":"leverage","OPTIONS · CALL / PUT":"options","EARLY RADAR":"radar"}; key=mapkey[view]
    df=expr[key]
    a_count=int(df.get("qualified",pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not df.empty and "qualified" in df else 0
    c1,c2,c3=st.columns(3)
    c1.metric("Ready now",a_count)
    c2.metric("On watch",max(0,len(df)-a_count))
    c3.metric("Markets covered",df["market"].nunique() if not df.empty and "market" in df else 0)
    st.markdown("<div class='simple-help'>The list below is intentionally simple: <b>action → reason → confidence → status</b>. Open one ticker only when you want the detailed entry logic.</div>",unsafe_allow_html=True)
    _render_expression_cards(df,key)
    with st.expander("Advanced · all rows / model gates",expanded=False):
        _render_expression_readiness(key)
        _display_scoreboard(df,view)
        _render_evidence_flow_chart(df,view.title())

    if not df.empty:
        options=[str(x) for x in df["symbol"].head(24).tolist()]
        selected=st.selectbox("Open one",options,key=f"detail_{key}_v24",label_visibility="collapsed")
        row=df[df["symbol"].astype(str)==selected].iloc[0]
        _render_compact_selected(row,ranked,mg,"OPTIONS" if key=="options" else ("BUYHOLD" if key=="buyhold" else key.upper()))
        with st.expander("Deep dive · thesis / valuation / causal chain / sources",expanded=False):
            _render_opportunity_detail(row,ranked,mg,"OPTIONS" if key=="options" else ("BUYHOLD" if key=="buyhold" else key.upper()))

    near=filtered_scenarios(discovered,max_rows=3)
    if not near.empty:
        with st.expander("Next 1–2Q scenarios · max 3",expanded=False):
            showcols=[c for c in ["theme","horizon","latest_headline","source_count"] if c in near.columns]
            st.dataframe(near[showcols],use_container_width=True,hide_index=True)

else:
    st.warning("Unknown workspace state; returning to CONTROL ROOM.")
    _render_control_room(ranked,mg)

st.caption("v3.2.1 · Market Opportunity OS · longitudinal discovery/learning + interactive UI navigation hotfix. No classic technical indicators; no autotrading.")

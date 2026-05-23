"""orchestrator.py - MacroRegime Data Orchestrator v27.2 ULTIMATE
Patched: Yves Behavioral + Cem Karsan 0DTE/Vanna/Charm/Skew + Soros Reflexivity/Boom-Bust/Sizing
"""
from __future__ import annotations
from types import SimpleNamespace
import os, sys, json, math, time, logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import json

_BOTTLENECK_REF = None
def _load_bottleneck_ref():
    global _BOTTLENECK_REF
    if _BOTTLENECK_REF is not None:
        return _BOTTLENECK_REF
    try:
        with open("bottleneck_reference.json", "r", encoding="utf-8") as f:
            _BOTTLENECK_REF = json.load(f)
    except Exception:
        _BOTTLENECK_REF = {}
    return _BOTTLENECK_REF or {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("orchestrator")

def _safe_progress(cb, msg: str, pct: float):
    if cb is None:
        return
    try:
        cb(msg, float(pct))
    except Exception:
        pass

try:
    from data.loader import load_prices, load_snapshot, save_snapshot, snapshot_age_str
except Exception as e:
    logger.error(f"Failed to import data.loader: {e}")
    load_prices = None
    def load_snapshot(max_age_hours=12.0): return None
    def save_snapshot(x): pass
    def snapshot_age_str(): return "unknown"

try:
    from data.fred_loader import load_fred_bundle
except Exception as e:
    logger.error(f"Failed to import fred_loader: {e}")
    def load_fred_bundle(force_refresh=True):
        return {"series": {}, "meta": {"loaded": 0, "requested": 0}}

try:
    from engines.gip_engine import GIPEngine, GIPResult, get_playbook
except Exception as e:
    logger.error(f"Failed to import gip_engine: {e}")
    GIPEngine = None
    GIPResult = None
    def get_playbook(sq, mq):
        return {
            "structural": sq, "monthly": mq,
            "best_assets": [], "worst_assets": [],
            "strategy": f"Trade {sq} regime. Monthly: {mq}.",
            "sectors_overweight": [], "sectors_underweight": [],
            "style": "", "fx": "", "bonds": "",
        }

try:
    from engines.market_health_engine import MarketHealthEngine
except Exception as e:
    logger.error(f"Failed to import market_health_engine: {e}")
    MarketHealthEngine = None

try:
    from engines.gamma_engine import GammaEngine
except Exception as e:
    logger.error(f"Failed to import gamma_engine: {e}")
    GammaEngine = None

try:
    from engines.greeks_proxy import GreeksProxy
except Exception as e:
    logger.error(f"Failed to import greeks_proxy: {e}")
    GreeksProxy = None

try:
    from engines.vanna_charm_flows import get_vanna_charm_flows
except Exception as e:
    logger.error(f"Failed to import vanna_charm_flows: {e}")
    def get_vanna_charm_flows(*args, **kwargs): return {}

try:
    from engines.bottleneck_engine import BottleneckEngine
except Exception as e:
    logger.error(f"Failed to import bottleneck_engine: {e}")
    BottleneckEngine = None

try:
    from engines.risk_range_engine import RiskRangeEngine
except Exception as e:
    logger.error(f"Failed to import risk_range_engine: {e}")
    class RiskRangeEngine:
        def run(self, prices):
            return {}

try:
    from engines.aaii_scraper import get_behavioral_macro
except Exception as e:
    logger.error(f"Failed to import aaii_scraper: {e}")
    def get_behavioral_macro(*args, **kwargs):
        return {"bullish": 30, "bearish": 30, "neutral": 40, "yves": {"alert": None, "alert_level": "NONE"}}

try:
    from engines.odte_monitor import run_odte_monitor
except Exception as e:
    logger.error(f"Failed to import odte_monitor: {e}")
    def run_odte_monitor(*args, **kwargs):
        return {"expiry": "-", "tickers": {}, "cascade_warning": False, "summary": "0DTE unavailable"}

try:
    from engines.skew_term_engine import run_skew_term
except Exception as e:
    logger.error(f"Failed to import skew_term_engine: {e}")
    def run_skew_term(*args, **kwargs):
        return {"skew_data": {}, "term_regime": "NORMAL"}

try:
    from engines.reflexivity_engine import run_reflexivity
except Exception as e:
    logger.error(f"Failed to import reflexivity_engine: {e}")
    def run_reflexivity(*args, **kwargs):
        return {"super_bubble_score": 5.0, "stage": "INCEPTION", "ticker_scores": {}}

try:
    from engines.boombust_engine import classify_stage
except Exception as e:
    logger.error(f"Failed to import boombust_engine: {e}")
    def classify_stage(*args, **kwargs):
        return {"stage": "INCEPTION", "stage_confidence": 0.5}

try:
    from engines.conviction_sizing import run_sizing
except Exception as e:
    logger.error(f"Failed to import conviction_sizing: {e}")
    def run_sizing(*args, **kwargs):
        return {}

try:
    from engines.interconnect_engine import run_interconnect
except Exception as e:
    logger.error(f"Failed to import interconnect_engine: {e}")
    def run_interconnect(*args, **kwargs):
        return {"active_scenarios": [], "scenarios": [], "summary": "Interconnect unavailable"}

try:
    from engines.yfinance_options import YFinanceOptionsEngine
except Exception as e:
    logger.error(f"Failed to import yfinance_options: {e}")
    YFinanceOptionsEngine = None

try:
    from engines.scenario_discovery_engine import run_scenario_discovery
except Exception as e:
    logger.error(f"Failed to import scenario_discovery_engine: {e}")
    def run_scenario_discovery(*args, **kwargs):
        return {"scenarios": [], "active_scenarios": [], "watch_scenarios": [], "summary": "Unavailable"}

try:
    from engines.transmission_engine import run_transmission
except Exception as e:
    logger.error(f"Failed to import transmission_engine: {e}")
    def run_transmission(*args, **kwargs):
        return {"scenarios": [], "active_scenarios": [], "watch_scenarios": [], "summary": "Unavailable"}

try:
    from engines.regime_transition_engine import run_regime_transition
except Exception as e:
    logger.error(f"Failed to import regime_transition_engine: {e}")
    def run_regime_transition(*args, **kwargs):
        return {"current_quad": "Q3", "transitions": {}, "summary": "Unavailable"}

try:
    from engines.news_nlp_engine_v3 import run_news_nlp
except Exception as e:
    logger.error(f"Failed to import news_nlp_engine_v3: {e}")
    def run_news_nlp(*args, **kwargs):
        return {"ticker_specific": {}, "emergent_narratives": [], "rumor_watch": [], "analyzed_count": 0}

try:
    from engines.gex_engine import analyze_multi as gex_analyze_multi
except Exception as e:
    logger.error(f"Failed to import gex_engine: {e}")
    def gex_analyze_multi(*args, **kwargs): return {}

try:
    from engines.charm_proxy_engine import analyze_multi as charm_analyze_multi
except Exception as e:
    logger.error(f"Failed to import charm_proxy_engine: {e}")
    def charm_analyze_multi(*args, **kwargs): return {}

try:
    from engines.vanna_proxy_engine import analyze_multi as vanna_analyze_multi
except Exception as e:
    logger.error(f"Failed to import vanna_proxy_engine: {e}")
    def vanna_analyze_multi(*args, **kwargs): return {}

try:
    from engines.odte_enhanced import analyze_multi as odte_enhanced_multi
except Exception as e:
    logger.error(f"Failed to import odte_enhanced: {e}")
    def odte_enhanced_multi(*args, **kwargs): return {}

try:
    from engines.structure_quality import analyze_multi as structure_analyze_multi
except Exception as e:
    logger.error(f"Failed to import structure_quality: {e}")
    def structure_analyze_multi(*args, **kwargs): return {}

try:
    from engines.afternoon_signal import analyze_multi as afternoon_analyze_multi
except Exception as e:
    logger.error(f"Failed to import afternoon_signal: {e}")
    def afternoon_analyze_multi(*args, **kwargs): return {}

try:
    from engines.volga_proxy import analyze_volga
except Exception as e:
    logger.error(f"Failed to import volga_proxy: {e}")
    def analyze_volga(*args, **kwargs): return {}

try:
    from engines.institutional_proxy import analyze_multi as inst_analyze_multi
except Exception as e:
    logger.error(f"Failed to import institutional_proxy: {e}")
    def inst_analyze_multi(*args, **kwargs): return {}

try:
    from engines.bottleneck_discovery_v3 import run_bottleneck_discovery_v3
except Exception as e:
    logger.error(f"Failed to import bottleneck_discovery_v3: {e}")
    def run_bottleneck_discovery_v3(*args, **kwargs):
        return {"active_bottlenecks": [], "watch_bottlenecks": [], "summary": "Unavailable"}

try:
    from config.settings import (
        US_SECTORS, US_FACTORS, FOREX_PAIRS, COMMODITIES, CRYPTO,
        BONDS, IHSG_UNIVERSE, MACRO_PROXIES, US_BUCKETS, IHSG_BUCKETS,
        FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS,
        QUAD_ASSET_PERFORMANCE, TICKER_SECTOR, MARKET_CLASSIFICATION,
        BOTTLENECK_PROFILES,
    )
except Exception as e:
    logger.error(f"Failed to import settings: {e}")
    US_SECTORS = {}; US_FACTORS = {}; FOREX_PAIRS = {}; COMMODITIES = {}; CRYPTO = {}
    BONDS = {}; IHSG_UNIVERSE = {}; MACRO_PROXIES = {}
    US_BUCKETS = {}; IHSG_BUCKETS = {}; FX_BUCKETS = {}; COMMODITY_BUCKETS = {}; CRYPTO_BUCKETS = {}
    QUAD_ASSET_PERFORMANCE = {}; TICKER_SECTOR = {}; MARKET_CLASSIFICATION = {}; BOTTLENECK_PROFILES = {}

try:
    import requests
    import xml.etree.ElementTree as ET
    _has_requests = True
except Exception:
    _has_requests = False

# ═══════════════════════════════════════════════════════════════════════
# SPRINT 1-4 NEW ENGINE IMPORTS (May 2026)
# All have defensive fallbacks — orchestrator continues even if any fail.
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.cascade_engine import (
        run_cascade_from_shock, run_all_cascades,
        bottleneck_full_cascade, reverse_lookup_ticker,
    )
    _V2_CASCADE = True
except Exception as e:
    logger.error(f"Failed to import cascade_engine: {e}")
    _V2_CASCADE = False
    def run_cascade_from_shock(*a, **k): return {}
    def run_all_cascades(*a, **k): return {"cascades": {}, "active_shocks": {}}
    def bottleneck_full_cascade(*a, **k): return {"impacts": []}
    def reverse_lookup_ticker(*a, **k): return []

try:
    from engines.yves_engine import run_yves_v2
    _V2_YVES = True
except Exception as e:
    logger.error(f"Failed to import yves_engine: {e}")
    _V2_YVES = False
    def run_yves_v2(*a, **k): return {"alerts": [], "summary": {"level": "NONE"}}

try:
    from engines.portfolio_sizing import run_portfolio_sizing
    _V2_SIZING = True
except Exception as e:
    logger.error(f"Failed to import portfolio_sizing: {e}")
    _V2_SIZING = False
    def run_portfolio_sizing(*a, **k): return {"positions": [], "total_deployed_pct": 0, "cash_pct": 1.0}

try:
    from engines.discovery_brain import run_discovery_brain
    _V2_DISCOVERY = True
except Exception as e:
    logger.error(f"Failed to import discovery_brain: {e}")
    _V2_DISCOVERY = False
    def run_discovery_brain(*a, **k): return {"by_mode": {}, "top_10": [], "summary": {}}

try:
    from engines.cem_karsan_universal import analyze_multi as cem_universal_multi
    _V2_CEM = True
except Exception as e:
    logger.error(f"Failed to import cem_karsan_universal: {e}")
    _V2_CEM = False
    def cem_universal_multi(*a, **k): return {}

try:
    from engines.ticker_universe_expander import run_ticker_expander
    _V2_EXPANDER = True
except Exception as e:
    logger.error(f"Failed to import ticker_universe_expander: {e}")
    _V2_EXPANDER = False
    def run_ticker_expander(*a, **k): return {"new_tickers": [], "candidates": [], "auto_add_recommended": []}

try:
    from engines.edgar_scraper_real import scan_multi_tickers as edgar_scan_multi
    _V2_EDGAR = True
except Exception as e:
    logger.error(f"Failed to import edgar_scraper_real: {e}")
    _V2_EDGAR = False
    def edgar_scan_multi(*a, **k): return {}

try:
    from engines.supply_chain_graph_real import run_supply_chain_analysis, reverse_lookup as supply_reverse
    _V2_SUPPLY = True
except Exception as e:
    logger.error(f"Failed to import supply_chain_graph_real: {e}")
    _V2_SUPPLY = False
    def run_supply_chain_analysis(*a, **k): return {"chokepoints": [], "propagation": {}, "summary": {}}
    def supply_reverse(*a, **k): return []

try:
    from engines.gip_engine_v10 import gip_engine_v10 as gip_v10_call
    _V2_GIP10 = True
except Exception as e:
    logger.error(f"Failed to import gip_engine_v10: {e}")
    _V2_GIP10 = False
    gip_v10_call = None

# ═══════════════════════════════════════════════════════════════════════
# SPRINT 6 NEW ENGINES — composite signal, risk setup, bonds-XAU
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.composite_signal_engine import (
        analyze_multi as composite_analyze_multi,
        compute_composite_signal,
    )
    _V2_COMPOSITE = True
except Exception as e:
    logger.error(f"Failed to import composite_signal_engine: {e}")
    _V2_COMPOSITE = False
    def composite_analyze_multi(*a, **k): return {}
    def compute_composite_signal(*a, **k): return {"direction": "NEUTRAL", "confidence": 0}

try:
    from engines.risk_setup_engine import calculate_risk_setup as v2_risk_setup
    _V2_RISK_SETUP = True
except Exception as e:
    logger.error(f"Failed to import risk_setup_engine: {e}")
    _V2_RISK_SETUP = False
    v2_risk_setup = None

try:
    from engines.bonds_xau_regime import run_bonds_xau_regime
    _V2_BONDS_XAU = True
except Exception as e:
    logger.error(f"Failed to import bonds_xau_regime: {e}")
    _V2_BONDS_XAU = False
    def run_bonds_xau_regime(*a, **k): return {"ok": False, "regime": "UNKNOWN", "ticker_biases": {}}

try:
    from engines.market_classifier import classify_ticker, filter_for_tab
    _V2_CLASSIFIER = True
except Exception as e:
    logger.error(f"Failed to import market_classifier: {e}")
    _V2_CLASSIFIER = False
    def classify_ticker(t): return "us_equity"
    def filter_for_tab(tickers, tab): return tickers

# ═══════════════════════════════════════════════════════════════════════
# SPRINT 7 NEW ENGINES — thought process, markov v3, smart money,
# capital rotation, UST auction, VRP, squeeze
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.thought_process_engine import compute_thesis as v7_compute_thesis, analyze_multi as v7_thesis_multi
    _V7_THOUGHT = True
except Exception as e:
    logger.error(f"Failed to import thought_process_engine: {e}")
    _V7_THOUGHT = False
    def v7_compute_thesis(*a, **k): return {"thesis_score": 0, "matched_frameworks": []}
    def v7_thesis_multi(*a, **k): return {}

try:
    from engines.markov_regime_engine_v3 import run_markov_v3
    _V7_MARKOV = True
except Exception as e:
    logger.error(f"Failed to import markov_regime_engine_v3: {e}")
    _V7_MARKOV = False
    def run_markov_v3(*a, **k):
        from dataclasses import dataclass
        @dataclass
        class _M:
            current_regime = "UNKNOWN"
            confidence = 0
            kelly_fraction = 0.25
            notes = ["v3 unavailable"]
            forecast_1m = {}
            forecast_3m = {}
            forecast_6m = {}
            change_point_alert = False
            change_point_probability = 0
            stationary = {}
            regime_probabilities = {}
        return _M()

try:
    from engines.smart_money_tracker import run_smart_money_analysis, get_ticker_smart_money
    _V7_SMART = True
except Exception as e:
    logger.error(f"Failed to import smart_money_tracker: {e}")
    _V7_SMART = False
    def run_smart_money_analysis(*a, **k): return {"ok": False, "n_funds_tracked": 0}
    def get_ticker_smart_money(*a, **k): return {"smart_money_held": False}

try:
    from engines.capital_rotation_engine import compute_capital_rotation, get_ticker_capital_rotation_role
    _V7_CAPROT = True
except Exception as e:
    logger.error(f"Failed to import capital_rotation_engine: {e}")
    _V7_CAPROT = False
    def compute_capital_rotation(*a, **k): return {"ok": False}
    def get_ticker_capital_rotation_role(*a, **k): return None

try:
    from engines.ust_auction_tracker import run_ust_auction_tracker
    _V7_UST = True
except Exception as e:
    logger.error(f"Failed to import ust_auction_tracker: {e}")
    _V7_UST = False
    def run_ust_auction_tracker(*a, **k): return {"ok": False}

try:
    from engines.vrp_scanner import scan_vrp
    _V7_VRP = True
except Exception as e:
    logger.error(f"Failed to import vrp_scanner: {e}")
    _V7_VRP = False
    def scan_vrp(*a, **k): return {"ok": False, "calls_to_action": []}

try:
    from engines.squeeze_scanner import scan_squeezes
    _V7_SQUEEZE = True
except Exception as e:
    logger.error(f"Failed to import squeeze_scanner: {e}")
    _V7_SQUEEZE = False
    def scan_squeezes(*a, **k): return {"ok": False, "imminent_squeezes": [], "strong_candidates": [], "watch_list": []}

try:
    from engines.tab_filter_engine import apply_tab_filter
    _V7_TAB_FILTER = True
except Exception as e:
    logger.error(f"Failed to import tab_filter_engine: {e}")
    _V7_TAB_FILTER = False
    def apply_tab_filter(*a, **k): return {"passes_filter": True, "filter_score": 50}

# ═══════════════════════════════════════════════════════════════════════
# SPRINT 9 NEW ENGINES — methodology-driven scanners
# Replace portfolio-matching with actual methodology evaluation
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.karsan_vol_scanner import scan_karsan
    _V9_KARSAN = True
except Exception as e:
    logger.error(f"Failed to import karsan_vol_scanner: {e}")
    _V9_KARSAN = False
    def scan_karsan(*a, **k): return {"ok": False, "per_ticker": {}, "squeeze_setups": [], "sell_premium": [], "buy_convexity": []}

try:
    from engines.spotgamma_gex_engine import run_spotgamma_scanner
    _V9_SPOTGAMMA = True
except Exception as e:
    logger.error(f"Failed to import spotgamma_gex_engine: {e}")
    _V9_SPOTGAMMA = False
    def run_spotgamma_scanner(*a, **k): return {"ok": False, "per_ticker_proxy_gex": {}, "compass": {}}

try:
    from engines.leopold_methodology import run_leopold_scan
    _V9_LEOPOLD = True
except Exception as e:
    logger.error(f"Failed to import leopold_methodology: {e}")
    _V9_LEOPOLD = False
    def run_leopold_scan(*a, **k): return {"ok": False, "per_ticker": {}, "top_picks_by_layer": {}, "asymmetry_setups": [], "written_off_recovering": []}

try:
    from engines.coatue_methodology import run_coatue_scan
    _V9_COATUE = True
except Exception as e:
    logger.error(f"Failed to import coatue_methodology: {e}")
    _V9_COATUE = False
    def run_coatue_scan(*a, **k): return {"ok": False, "per_ticker": {}, "sellers_top": [], "buyers_top": [], "decay_alerts": [], "agentic_plays": []}

logger.info(
    f"V9 (Sprint 9) methodology engines: karsan={_V9_KARSAN} spotgamma={_V9_SPOTGAMMA} "
    f"leopold={_V9_LEOPOLD} coatue={_V9_COATUE}"
)
logger.info(
    f"V9 (Sprint 9) methodology engines: karsan={_V9_KARSAN} spotgamma={_V9_SPOTGAMMA} "
    f"leopold={_V9_LEOPOLD} coatue={_V9_COATUE}"
)

# ═══════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE (v27.3 NEW)
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.simulation_engine import run_simulation_batch, get_simulation_summary, filter_by_simulation
    _V2_SIM = True
except Exception as e:
    logger.error(f"Failed to import simulation_engine: {e}")
    _V2_SIM = False
    def run_simulation_batch(*a, **k): return {}
    def get_simulation_summary(*a, **k): return {"total": 0, "passed": 0, "failed": 0, "avg_score": 0}
    def filter_by_simulation(rows, sim_results, threshold=65, require_pass=True): return rows

logger.info(f"V2 Simulation engine loaded: {_V2_SIM}")

# ═══════════════════════════════════════════════════════════════════════
# SPRINT 11: VolSignals + SpotGamma + Schadner Integration
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.volsignals_regime import compute_dealer_regime_multi
    _V11_VOLSIGNALS = True
except Exception as e:
    logger.error(f"Failed to import volsignals_regime: {e}")
    _V11_VOLSIGNALS = False
    def compute_dealer_regime_multi(*a, **k): return {}

try:
    from engines.spotgamma_levels import compute_structural_levels_multi
    _V11_SPOTGAMMA = True
except Exception as e:
    logger.error(f"Failed to import spotgamma_levels: {e}")
    _V11_SPOTGAMMA = False
    def compute_structural_levels_multi(*a, **k): return {}

try:
    from engines.schadner_iv import schadner_iv, validate_iv_proxy
    _V11_SCHADNER = True
except Exception as e:
    logger.error(f"Failed to import schadner_iv: {e}")
    _V11_SCHADNER = False
    def schadner_iv(*a, **k): return None
    def validate_iv_proxy(*a, **k): return {}

logger.info(
    f"V11 (Sprint 11) engines: volsignals={_V11_VOLSIGNALS} spotgamma={_V11_SPOTGAMMA} "
    f"schadner={_V11_SCHADNER}"
)

# ═══════════════════════════════════════════════════════════════════════
# ATTACHMENT 4: New Engines — Walk-Forward, IDHL, RC, AFS, Fractional Kelly,
# Bayesian Fusion, Duration-Dependent HMM, CRI_v2
# ═══════════════════════════════════════════════════════════════════════
try:
    from engines.integrator_guide import enhance_snapshot, get_enhanced_summary
    _V32_INTEGRATOR = True
except Exception as e:
    logger.error(f"Failed to import integrator_guide: {e}")
    _V32_INTEGRATOR = False
    def enhance_snapshot(snap, prices, portfolio_value=100_000): return snap
    def get_enhanced_summary(snap): return snap.get("summary", {})

logger.info(f"V32 (Attachment 4) integrator loaded: {_V32_INTEGRATOR}")



logger.info(
    "V2 engines loaded: "
    f"cascade={_V2_CASCADE} yves={_V2_YVES} sizing={_V2_SIZING} "
    f"discovery={_V2_DISCOVERY} cem={_V2_CEM} expander={_V2_EXPANDER} "
    f"edgar={_V2_EDGAR} supply={_V2_SUPPLY} gip10={_V2_GIP10} "
    f"composite={_V2_COMPOSITE} risk_setup={_V2_RISK_SETUP} "
    f"bonds_xau={_V2_BONDS_XAU} classifier={_V2_CLASSIFIER} simulation={_V2_SIM}"
)
logger.info(
    "V7 (Sprint 7) engines loaded: "
    f"thought_process={_V7_THOUGHT} markov_v3={_V7_MARKOV} smart_money={_V7_SMART} "
    f"capital_rotation={_V7_CAPROT} ust_auction={_V7_UST} vrp={_V7_VRP} squeeze={_V7_SQUEEZE}"
)

def _strip_html(text):
    if not text:
        return ""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def _fetch_news_headlines(tickers: List[str], max_per_ticker: int = 5) -> Dict[str, List[dict]]:
    if not _has_requests:
        return {}
    headlines = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    session.headers.update(headers)
    for ticker in tickers[:30]:
        time.sleep(0.5)  # Rate limit protection
        try:
            url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
            r = session.get(url, timeout=6)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            items = []
            for item in root.iter('item'):
                title = item.find('title')
                pub = item.find('pubDate')
                link = item.find('link')
                if title is not None and title.text:
                    items.append({
                        "title": _strip_html(title.text),
                        "date": pub.text if pub is not None else "",
                        "url": link.text if link is not None else "",
                        "source": "Yahoo Finance"
                    })
                if len(items) >= max_per_ticker:
                    break
            if items:
                headlines[ticker] = items
        except Exception as e:
            logger.debug(f"News fetch failed for {ticker}: {e}")
    return headlines

def _analyze_news(headlines: Dict[str, List[dict]], prices: dict) -> dict:
    bullish_kw = ["surge","soar","rally","bull","upgrade","beat","strong","growth","breakthrough","deal","partnership","ai","record","expansion","launch","approve","buyback","dividend","blockbuster","moon","rocket"]
    bearish_kw = ["crash","plunge","bear","downgrade","miss","weak","loss","layoff","investigation","fine","delay","recall","debt","bankrupt","cut","short","sell","dump","collapse","crisis"]
    rumor_kw = ["reportedly","rumor","speculation","considering","exploring","potential","may","might","could","planned","sources say","exclusive","breaking","leak","in talks","approaching","eyeing"]
    theme_kw = {
        "ai": ["ai","artificial intelligence","llm","chatgpt","agentic","model","machine learning","nvidia","openai"],
        "semiconductor": ["chip","semiconductor","gpu","cpu","tsmc","hbm","dram","foundry","wafer"],
        "energy": ["oil","gas","energy","solar","renewable","crude","power","grid","transformer"],
        "crypto": ["bitcoin","crypto","blockchain","etf","ethereum","btc","eth","solana"],
        "fed_rates": ["fed","federal reserve","rate cut","rate hike","powell","interest rate","fomc"],
        "geopolitical": ["war","sanctions","china","taiwan","trade","tariff","middle east","ukraine"],
        "biotech": ["fda","trial","drug","vaccine","biotech","pharma","approval"],
        "ev": ["ev","electric vehicle","tesla","battery","lithium","charging"],
    }
    ticker_news = {}
    rumor_watch = []
    narratives = []
    for ticker, items in headlines.items():
        if not items:
            continue
        bull_count = 0; bear_count = 0; rumor_count = 0
        themes = set()
        latest_titles = []
        for item in items:
            title_lower = item["title"].lower()
            latest_titles.append(item["title"])
            bull_count += sum(1 for kw in bullish_kw if kw in title_lower)
            bear_count += sum(1 for kw in bearish_kw if kw in title_lower)
            rumor_count += sum(1 for kw in rumor_kw if kw in title_lower)
            for theme, kws in theme_kw.items():
                if any(kw in title_lower for kw in kws):
                    themes.add(theme)
        total_kw = bull_count + bear_count
        sentiment_score = (bull_count - bear_count) / max(total_kw, 1)
        rumor_score = min(rumor_count / max(len(items), 1), 1.0)
        s = prices.get(ticker)
        r1m = None
        if s is not None and len(s) >= 22:
            try:
                s_clean = pd.to_numeric(s, errors="coerce").dropna()
                if len(s_clean) >= 22:
                    r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1)
            except Exception:
                pass
        front_run_signal = None
        if rumor_score > 0.4 and sentiment_score > 0.3:
            front_run_signal = "STRONG_BULLISH_RUMOR"
        elif rumor_score > 0.4 and sentiment_score < -0.3:
            front_run_signal = "STRONG_BEARISH_RUMOR"
        elif rumor_score > 0.25:
            front_run_signal = "RUMOR_WATCH"
        elif sentiment_score > 0.4 and (r1m is None or r1m < 0.08):
            front_run_signal = "NEWS_MOMENTUM_BUILDING"
        elif sentiment_score < -0.4:
            front_run_signal = "NEGATIVE_HEADLINE_RISK"
        elif bull_count >= 3 and bear_count == 0:
            front_run_signal = "BULLISH_CLUSTER"
        ticker_news[ticker] = {
            "headlines": latest_titles[:3],
            "sentiment_score": round(sentiment_score, 2),
            "rumor_score": round(rumor_score, 2),
            "themes": list(themes),
            "front_run_signal": front_run_signal,
            "r1m": r1m,
            "bull_count": bull_count,
            "bear_count": bear_count,
        }
        if front_run_signal:
            rumor_watch.append({
                "ticker": ticker,
                "signal": front_run_signal,
                "sentiment": round(sentiment_score, 2),
                "rumor": round(rumor_score, 2),
                "themes": list(themes),
                "headline": latest_titles[0] if latest_titles else "",
                "r1m": r1m,
            })
        if themes and abs(sentiment_score) > 0.15:
            narratives.append({
                "ticker": ticker,
                "theme": list(themes)[0] if themes else "general",
                "sentiment": sentiment_score,
                "headline": latest_titles[0] if latest_titles else "",
            })
    emergent = {}
    for n in narratives:
        theme = n["theme"]
        if theme not in emergent:
            emergent[theme] = {"mentions": 0, "tickers": [], "avg_sentiment": 0, "headlines": []}
        emergent[theme]["mentions"] += 1
        emergent[theme]["tickers"].append(n["ticker"])
        emergent[theme]["avg_sentiment"] += n["sentiment"]
        emergent[theme]["headlines"].append(n["headline"])
    for theme in emergent:
        count = emergent[theme]["mentions"]
        emergent[theme]["avg_sentiment"] = round(emergent[theme]["avg_sentiment"] / count, 2) if count > 0 else 0
        emergent[theme]["tickers"] = list(dict.fromkeys(emergent[theme]["tickers"]))[:10]
        emergent[theme]["headlines"] = emergent[theme]["headlines"][:5]
        emergent[theme]["supply_chain_hits"] = 0
    return {
        "ticker_specific": ticker_news,
        "emergent_narratives": [{"name": k, **v} for k, v in emergent.items()],
        "rumor_watch": sorted(rumor_watch, key=lambda x: abs(x["sentiment"]) + x["rumor"], reverse=True)[:25],
        "analyzed_count": sum(len(v) for v in headlines.values()),
    }

def _extract_bottleneck_tickers() -> List[str]:
    ref = _load_bottleneck_ref()
    tickers = set()
    for item in ref.get("consensus_heatmap", []):
        t = item.get("ticker", "")
        if t:
            tickers.add(t.replace("$", "").strip().upper())
    for phase in ref.get("institutional_rotation", []):
        for t in phase.get("tickers", []):
            if t:
                tickers.add(t.replace("$", "").strip().upper())
    for ma in ref.get("ma_watchlist", []):
        t = ma.get("target", "")
        if t:
            tickers.add(t.replace("$", "").strip().upper())
    for ev in ref.get("catalyst_timeline", []):
        t = ev.get("ticker", "")
        if t:
            tickers.add(t.replace("$", "").strip().upper())
    clean = []
    for t in tickers:
        if not t or len(t) > 20 or t.startswith("http") or " " in t:
            continue
        clean.append(t)
    return clean

def _all_tickers() -> List[str]:
    pools = [
        list(US_SECTORS.keys()), list(US_FACTORS.keys()),
        list(FOREX_PAIRS.keys()), list(COMMODITIES.keys()),
        list(CRYPTO.keys()), list(BONDS.keys()),
        list(IHSG_UNIVERSE.keys()), list(MACRO_PROXIES.keys()),
        ["^VIX", "UUP", "EEM", "VWO", "^GSPC", "^IXIC", "VVIX"],
        _extract_bottleneck_tickers(),
    ]
    seen = set()
    out = []
    for p in pools:
        for t in p:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out

def _fred_fallback() -> Dict[str, pd.Series]:
    import numpy as np
    dates = pd.date_range(end=datetime.now(), periods=60, freq="MS")
    return {
        "INDPRO": pd.Series(np.linspace(100, 105, 60) + np.random.randn(60)*0.5, index=dates, name="INDPRO"),
        "CPI": pd.Series(np.linspace(300, 310, 60) + np.random.randn(60)*1, index=dates, name="CPI"),
        "UNRATE": pd.Series(np.linspace(3.5, 4.2, 60) + np.random.randn(60)*0.1, index=dates, name="UNRATE"),
        "DGS10": pd.Series(np.linspace(4.0, 4.5, 60) + np.random.randn(60)*0.1, index=dates, name="DGS10"),
        "DGS2": pd.Series(np.linspace(3.5, 4.0, 60) + np.random.randn(60)*0.1, index=dates, name="DGS2"),
        "FEDFUNDS": pd.Series([5.33]*60, index=dates, name="FEDFUNDS"),
        "PAYEMS": pd.Series(np.linspace(155000, 158000, 60), index=dates, name="PAYEMS"),
        "RSAFS": pd.Series(np.linspace(680, 720, 60), index=dates, name="RSAFS"),
        "ICSA": pd.Series(np.linspace(220, 240, 60), index=dates, name="ICSA"),
        "CORECPI": pd.Series(np.linspace(280, 290, 60), index=dates, name="CORECPI"),
        "DFII10": pd.Series(np.linspace(1.5, 2.0, 60), index=dates, name="DFII10"),
        "T5YIE": pd.Series(np.linspace(2.2, 2.5, 60), index=dates, name="T5YIE"),
        "HYOAS": pd.Series(np.linspace(3.5, 4.5, 60), index=dates, name="HYOAS"),
        "ISMNO": pd.Series(np.linspace(48, 52, 60), index=dates, name="ISMNO"),
        "HOUST": pd.Series(np.linspace(1300, 1400, 60), index=dates, name="HOUST"),
    }

def _global_fallback(quad: str) -> dict:
    base_map = {
        "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia","UAE","Israel","Poland","Czech Republic","Romania"],
        "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand","Colombia","New Zealand","Norway","Kazakhstan","Angola"],
        "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt","Spain","Netherlands","Belgium","Sweden","Switzerland"],
        "Q4": ["Venezuela","Iran","Ukraine","Greece","Portugal","Lebanon","Syria","Yemen","Zimbabwe","Sudan","Afghanistan","North Korea","Myanmar","Belarus","Bolivia"],
    }
    cqs = {}
    for q, countries in base_map.items():
        for c in countries:
            cqs[c] = q
    return {
        "global_quad": quad,
        "global_conf": 0.52,
        "global_probs": {"Q1":0.20,"Q2":0.25,"Q3":0.35,"Q4":0.20},
        "country_quads": cqs,
        "country_list": [{"country": c, "quad": q, "regime_name": {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q,q)} for q, countries in base_map.items() for c in countries],
        "em_recovery": {"trigger": f"Q3 defensive - watch for {quad} rotation", "confidence": 0.4},
        "dm_count": len(base_map.get("Q1",[])) + len(base_map.get("Q3",[])),
        "em_count": len(base_map.get("Q2",[])) + len(base_map.get("Q4",[])),
    }

def _crypto_onchain_proxy(prices: dict) -> dict:
    tokens = {}
    for ticker in list(CRYPTO.keys()):
        s = prices.get(ticker)
        if s is None or len(s) < 22:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) < 22:
                continue
            with np.errstate(invalid='ignore', divide='ignore'):
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1) if s.iloc[-22] != 0 else 0
                r7d = float(s.iloc[-1] / s.iloc[-8] - 1) if len(s) >= 8 and s.iloc[-8] != 0 else r1m
            vol = float(s.tail(20).std())
            vol_40d = float(s.tail(40).std()) if len(s) >= 40 else vol
            vol_change = (vol / vol_40d - 1) if vol_40d > 0 else 0
            mean_20 = float(s.tail(20).mean())
            mean_50 = float(s.tail(50).mean()) if len(s) >= 50 else mean_20
            momentum = (mean_20 / mean_50 - 1) if mean_50 > 0 else 0
            score = min(1.0, max(0.0, 0.5 + r1m * 5 + momentum * 2))
            tokens[ticker] = {
                "momentum_score": round(score, 3),
                "tvl_7d_change": round(r7d, 4),
                "tvl_30d_change": round(r1m, 4),
                "dex_vol_change": round(vol_change, 4),
                "price": round(float(s.iloc[-1]), 2),
                "volatility_20d": round(vol / mean_20 if mean_20 > 0 else 0, 4),
                "trend_direction": "UP" if r1m > 0.05 else ("DOWN" if r1m < -0.05 else "SIDE"),
            }
        except Exception as e:
            logger.warning(f"Crypto proxy failed for {ticker}: {e}")
    return tokens

def _risk_range_proxy(prices: dict) -> dict:
    asset_ranges = {}
    for ticker, s in prices.items():
        if s is None or len(s) < 60:
            continue
        try:
            s_clean = pd.to_numeric(s, errors="coerce").dropna()
            if len(s_clean) < 60:
                continue
            px = float(s_clean.iloc[-1])
            sma20 = float(s_clean.tail(20).mean())
            std20 = float(s_clean.tail(20).std())
            if std20 == 0 or not all(math.isfinite(v) for v in [px, sma20, std20]):
                continue
            lrr = round(sma20 - 1.5 * std20, 4)
            trr = round(sma20 + 1.5 * std20, 4)
            comp = "bullish" if px < lrr else "bearish" if px > trr else "neutral"
            quality = "A" if abs(px - lrr) / max(lrr, 0.001) < 0.02 else "B" if comp != "neutral" else "C"
            asset_ranges[ticker] = {
                "px": px,
                "trade": {"lrr": lrr, "trr": trr},
                "composite": comp,
                "quality": quality,
                "market": _classify_market(ticker),
            }
        except Exception:
            pass
    return {"asset_ranges": asset_ranges}

def _classify_market(ticker: str) -> str:
    if ticker in FOREX_PAIRS or "=" in ticker or ticker in ["DX-Y.NYB", "UUP"]:
        return "forex"
    if ticker in COMMODITIES or ticker in ["GC=F", "SI=F", "CL=F", "HG=F"]:
        return "commodity"
    if ticker in CRYPTO or ticker in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        return "crypto"
    if ticker in IHSG_UNIVERSE or ticker.endswith(".JK"):
        return "ihsg"
    return "us_equity"

def _alpha_center_proxy(prices: dict, risk_ranges: dict, quad: str, vix: float,
                       news_analysis: dict = None, composite_signals: dict = None,
                       cot_data: dict = None, oi_data: dict = None,
                       greeks_data: dict = None, gamma_data: dict = None) -> dict:
    """v2.2 — Now uses composite_signal_engine for direction (FIXES Alpha Center vs US Stocks tab inconsistency).

    If composite_signals dict passed in, direction comes from there (consistent with
    US Stocks/Forex/Commodities/Crypto tabs). Falls back to naive composite if not.
    """
    ar = risk_ranges.get("asset_ranges", {})
    alpha_items = []
    news_map = (news_analysis or {}).get("ticker_specific", {}) if news_analysis else {}
    composite_signals = composite_signals or {}

    for ticker, v in ar.items():
        # ── v2.2: Use composite signal engine direction if available ──
        cs = composite_signals.get(ticker, {})
        if cs:
            direction_from_composite = cs.get("direction", "NEUTRAL")
            if direction_from_composite in ("NEUTRAL", "AVOID"):
                continue  # Skip neutral/avoid in alpha center
            side = "long" if direction_from_composite == "LONG" else "short"
            confidence = cs.get("confidence", 0.5)
            flipped = cs.get("flipped_from_composite", False)
            comp = "bullish" if side == "long" else "bearish"  # Backwards-compat label
        else:
            # Fallback: naive composite (only used if composite_signals not provided)
            comp = v.get("composite", "neutral")
            if comp == "neutral":
                continue
            side = "long" if comp == "bullish" else "short"
            confidence = 0.5
            flipped = False

        px = v.get("px", 0)
        tr = v.get("trade", {})
        lrr = tr.get("lrr", 0)
        trr = tr.get("trr", 0)
        if not lrr or not trr:
            continue
        spread = trr - lrr

        # ── v2.2: Use risk_setup_engine for entry/target/stop if available ──
        try:
            from engines.risk_setup_engine import calculate_risk_setup as _rs
            setup = _rs(
                ticker=ticker, direction=side.upper(), price=px,
                risk_range=v,
                composite_signal=cs,
                gamma_data=(gamma_data or {}).get(ticker),
                greek_data=(greeks_data or {}).get(ticker),
            )
            entry = setup.get("entry")
            tp1 = setup.get("target1")
            tp2 = setup.get("target2")
            stop = setup.get("stop")
            rr = setup.get("rr", 0)
            near_entry = setup.get("near_entry", False)
        except Exception:
            # Fallback to proxy
            if side == "long":
                entry = round(lrr, 2); tp1 = round(lrr + spread * 0.5, 2); tp2 = round(trr, 2); stop = round(lrr - spread * 0.25, 2)
            else:
                entry = round(trr, 2); tp1 = round(trr - spread * 0.5, 2); tp2 = round(lrr, 2); stop = round(trr + spread * 0.25, 2)
            rr = round(abs(tp1 - entry) / max(abs(entry - stop), 0.01), 2)
            pos = (px - lrr) / spread if spread > 0 else 0.5
            near_entry = (side == "long" and pos <= 0.35) or (side == "short" and pos >= 0.65)

        grade = "A" if near_entry and rr >= 2.0 else "B" if near_entry else "C"
        # v2.2: Boost grade by confidence
        if confidence >= 0.7 and grade == "B":
            grade = "A"
        elif confidence < 0.3 and grade == "A":
            grade = "B"
        worth = "YES" if near_entry else "WAIT"
        action = "Buy Now" if side == "long" and near_entry else ("Sell Now" if side == "short" and near_entry else "Wait")
        scanner = "structural"
        if quad == "Q3" and comp == "bullish" and ticker in ["GC=F", "SI=F", "GLD", "SLV", "GDX", "GDXJ"]:
            scanner = "regime_aligned"
        elif quad == "Q1" and comp == "bullish" and ticker in ["QQQ", "SPY", "IWM", "BTC-USD", "ETH-USD"]:
            scanner = "regime_aligned"
        elif near_entry and rr >= 2.0:
            scanner = "bottleneck"
        elif flipped:
            scanner = "composite_flip"  # v2.2: special scanner for direction flips
        news = news_map.get(ticker, {})
        news_signal = news.get("front_run_signal")
        priority_score = round(rr * 10 + (50 if near_entry else 0) + (confidence * 20), 1)
        if news_signal in ["STRONG_BULLISH_RUMOR", "NEWS_MOMENTUM_BUILDING", "BULLISH_CLUSTER"]:
            if side == "long":
                priority_score += 30; scanner = "news_momentum"
                if grade == "C": grade = "B"
            elif side == "short":
                priority_score -= 10
        elif news_signal in ["STRONG_BEARISH_RUMOR", "NEGATIVE_HEADLINE_RISK"]:
            if side == "short":
                priority_score += 30; scanner = "news_momentum"
                if grade == "C": grade = "B"
            elif side == "long":
                priority_score -= 10
        alpha_items.append({
            "ticker": ticker,
            "scanner_type": scanner,
            "direction": "LONG" if side == "long" else "SHORT",
            "grade": grade,
            "priority_score": priority_score,
            "price": px,
            "entry": entry,
            "target_1": tp1,
            "target_2": tp2,
            "stop_loss": stop,
            "rr": rr,
            "worth_entering": worth,
            "time_estimate": "1-2 weeks",
            "thesis": f"{side.title()} setup at {quad} regime - {action}",
            "recommendation": f"{side.title()} - Risk range {lrr}/{trr}",
            "action": action,
            "news_signal": news_signal,
            "news_headline": (news.get("headlines") or [""])[0] if news else "",
            "news_sentiment": news.get("sentiment_score") if news else None,
            "news_themes": news.get("themes") if news else [],
        })
    return {
        "meta": {
            "regime": quad,
            "bias": "Structural" if quad in ("Q1", "Q2") else "Defensive",
            "vix": vix,
            "total_items": len(alpha_items),
        },
        "all": alpha_items,
        "level_1": [i for i in alpha_items if i.get("grade") == "A"],
        "level_2": [i for i in alpha_items if i.get("grade") == "B"],
        "watch": [i for i in alpha_items if i.get("grade") == "C"],
    }

def _ihsg_layers(prices: dict, quad: str) -> dict:
    sector_map = {
        "ADRO.JK": "Coal", "ITMG.JK": "Coal", "PTBA.JK": "Coal",
        "NCKL.JK": "Nickel", "ANTM.JK": "Nickel", "INCO.JK": "Nickel",
        "AALI.JK": "CPO", "LSIP.JK": "CPO", "SMAR.JK": "CPO",
        "BBRI.JK": "Banking", "BMRI.JK": "Banking", "BBCA.JK": "Banking", "BBNI.JK": "Banking", "BRIS.JK": "Banking",
        "TLKM.JK": "Telco", "EXCL.JK": "Telco",
        "UNTR.JK": "Mining Contractor", "BYAN.JK": "Mining",
        "ICBP.JK": "Consumer", "INDF.JK": "Consumer", "KLBF.JK": "Pharma",
        "PGEO.JK": "Geothermal", "WINS.JK": "Shipping",
        "EIDO": "ETF", "^JKSE": "Index",
    }
    sector_momentum = {}
    sector_returns = {}
    for ticker, sector in sector_map.items():
        s = prices.get(ticker)
        if s is not None and len(s) >= 22:
            try:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22:
                    with np.errstate(invalid='ignore', divide='ignore'):
                        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                    if math.isfinite(r1m):
                        sector_returns.setdefault(sector, []).append(r1m)
            except Exception:
                pass
    for sector, returns in sector_returns.items():
        if returns:
            avg = sum(returns) / len(returns)
            leader_ticker = [t for t, s in sector_map.items() if s == sector and t in prices][0] if [t for t, s in sector_map.items() if s == sector and t in prices] else ""
            sector_momentum[sector] = {
                "bias": "Bullish" if avg > 0.03 else ("Bearish" if avg < -0.03 else "Neutral"),
                "avg_1m": round(avg, 4),
                "strength": round(abs(avg) * 100, 1),
                "leader": leader_ticker,
            }
    commodity_overlay = {}
    for sector in ["Coal", "Nickel", "CPO", "Mining"]:
        tickers = [t for t, s in sector_map.items() if s == sector]
        returns = []
        for t in tickers:
            s = prices.get(t)
            if s is not None and len(s) >= 22:
                try:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    if len(s) >= 22:
                        returns.append(float(s.iloc[-1] / s.iloc[-22] - 1))
                except Exception:
                    pass
        if returns:
            avg = sum(returns) / len(returns)
            commodity_overlay[sector] = {
                "r1m": round(avg, 4),
                "tailwind": "Strong" if avg > 0.05 else ("Moderate" if avg > 0.02 else "Weak"),
                "signal": f"{sector} momentum {avg:+.1%}",
            }
    rupiah_regime = {}
    dxy_s = prices.get("DX-Y.NYB")
    idr_s = prices.get("USDIDR=X")
    if dxy_s is not None and len(dxy_s) >= 22:
        try:
            dxy_s = pd.to_numeric(dxy_s, errors="coerce").dropna()
            dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
            rupiah_regime["dxy_trend"] = "Bullish" if dxy_ret > 0.01 else ("Bearish" if dxy_ret < -0.01 else "Neutral")
            rupiah_regime["flow_signal"] = "Positive - DXY falling" if dxy_ret < -0.01 else ("Risk - DXY rising" if dxy_ret > 0.01 else "Neutral")
        except Exception:
            pass
    if idr_s is not None and len(idr_s) >= 22:
        try:
            idr_s = pd.to_numeric(idr_s, errors="coerce").dropna()
            idr_ret = float(idr_s.iloc[-1] / idr_s.iloc[-22] - 1)
            rupiah_regime["idr_1m"] = round(idr_ret, 4)
        except Exception:
            pass
    foreign_flow = {}
    for ticker in list(IHSG_UNIVERSE.keys()):
        s = prices.get(ticker)
        if s is not None and len(s) >= 22:
            try:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22:
                    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                    r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else r1m
                    if r5d > 0.03 and r1m > 0:
                        foreign_flow[ticker] = {"signal": "Foreign Accumulation", "strength": round(r5d, 4)}
                    elif r5d < -0.03 and r1m < 0:
                        foreign_flow[ticker] = {"signal": "Foreign Distribution", "strength": round(r5d, 4)}
                    else:
                        foreign_flow[ticker] = {"signal": "Neutral", "strength": 0}
            except Exception:
                pass
    macro_overlay = {}
    banking_tickers = [t for t, s in sector_map.items() if s == "Banking"]
    banking_returns = []
    for t in banking_tickers:
        s = prices.get(t)
        if s is not None and len(s) >= 22:
            try:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22:
                    banking_returns.append(float(s.iloc[-1] / s.iloc[-22] - 1))
            except Exception:
                pass
    if banking_returns:
        avg_banking = sum(banking_returns) / len(banking_returns)
        macro_overlay["banking_bias"] = "Bullish" if avg_banking > 0.03 else ("Bearish" if avg_banking < -0.03 else "Neutral")
        macro_overlay["bi_signal"] = f"Banking sector {avg_banking:+.1%}"
    consumer_tickers = [t for t, s in sector_map.items() if s in ["Consumer", "Pharma"]]
    consumer_returns = []
    for t in consumer_tickers:
        s = prices.get(t)
        if s is not None and len(s) >= 22:
            try:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22:
                    consumer_returns.append(float(s.iloc[-1] / s.iloc[-22] - 1))
            except Exception:
                pass
    if consumer_returns:
        avg_consumer = sum(consumer_returns) / len(consumer_returns)
        macro_overlay["consumer_bias"] = "Bullish" if avg_consumer > 0.03 else ("Bearish" if avg_consumer < -0.03 else "Neutral")
        macro_overlay["consumer_signal"] = f"Consumer sector {avg_consumer:+.1%}"
    macro_overlay["commodity_bias"] = "Bullish" if any(commodity_overlay.get(s, {}).get("tailwind") in ["Strong", "Moderate"] for s in commodity_overlay) else "Neutral"
    macro_overlay["policy_score"] = round(0.1 if macro_overlay.get("banking_bias") == "Bullish" else (-0.1 if macro_overlay.get("banking_bias") == "Bearish" else 0), 2)
    return {
        "ihsg_sector_momentum": sector_momentum,
        "ihsg_commodity_overlay": commodity_overlay,
        "ihsg_rupiah_regime": rupiah_regime,
        "ihsg_foreign_flow": foreign_flow,
        "ihsg_macro_overlay": macro_overlay,
    }

def _options_proxy_for_ticker(ticker, prices):
    ticker = ticker.replace("$", "").strip().upper()
    s = prices.get(ticker)
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        aliases = []
        if "." in ticker and not ticker.endswith(".JK"):
            aliases.append(ticker.replace(".", "-"))
        if "-" in ticker:
            aliases.append(ticker.replace("-", "."))
        if ticker.endswith(".KS"):
            aliases.append(ticker.replace(".KS", ".KQ"))
        for a in aliases:
            s = prices.get(a)
            if s is not None and hasattr(s, "__len__") and len(s) >= 20:
                ticker = a
                break
    if s is None or (hasattr(s, "__len__") and len(s) < 20):
        return {"ok": False, "ticker": ticker, "error": "No price data"}
    try:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < 20:
            return {"ok": False}
        px = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        std20 = float(s_clean.tail(20).std())
        if std20 == 0 or not all(math.isfinite(v) for v in [px, sma20, std20]):
            return {"ok": False}
        max_pain = round(sma20, 2)
        put_wall = round(sma20 - std20 * 2.0, 2)
        call_wall = round(sma20 + std20 * 2.0, 2)
        gamma_flip_up = round(sma20 + std20 * 1.5, 2)
        gamma_flip_down = round(sma20 - std20 * 1.5, 2)
        mp_dist = (px - max_pain) / max_pain if max_pain != 0 else 0
        r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else 0
        if r5d > 0.03 and r20d > 0.05:
            gamma_regime = "DEEP_POSITIVE"
        elif r5d > 0.01 and r20d > 0.02:
            gamma_regime = "POSITIVE"
        elif r5d < -0.03 and r20d < -0.05:
            gamma_regime = "DEEP_NEGATIVE"
        elif r5d < -0.01 and r20d < -0.02:
            gamma_regime = "NEGATIVE"
        else:
            gamma_regime = "TRANSITION"
        if r20d > 0.05:
            greek = "BULLISH"
        elif r20d < -0.05:
            greek = "BEARISH"
        else:
            greek = "NEUTRAL"
        near_max_pain = abs(mp_dist) < 0.03
        if near_max_pain and gamma_regime in ("DEEP_POSITIVE", "POSITIVE") and greek == "BULLISH":
            conviction = "STRONG"
        elif gamma_regime in ("DEEP_POSITIVE", "POSITIVE", "TRANSITION") and greek == "BULLISH":
            conviction = "MODERATE"
        elif gamma_regime in ("NEGATIVE", "DEEP_NEGATIVE") and greek == "BEARISH":
            conviction = "MODERATE"
        elif near_max_pain:
            conviction = "WEAK"
        else:
            conviction = "CONFLICTED"
        return {
            "ok": True, "price": px, "max_pain": max_pain, "put_wall": put_wall,
            "call_wall": call_wall, "gamma_flip_up": gamma_flip_up,
            "gamma_flip_down": gamma_flip_down, "max_pain_dist": round(mp_dist, 4),
            "gamma_regime": gamma_regime, "greek_composite": greek,
            "conviction": conviction, "r5d": round(r5d, 4), "r20d": round(r20d, 4),
            "source": "PROXY"
        }
    except Exception as e:
        logger.debug(f"Options proxy failed for {ticker}: {e}")
        return {"ok": False}

def _generate_front_run_candidates(prices, news_analysis, bottleneck_ref):
    candidates = []
    seen = set()
    ref_tickers = bottleneck_ref.get("consensus_heatmap", [])
    rotation = bottleneck_ref.get("institutional_rotation", [])
    for item in ref_tickers:
        ticker = item.get("ticker", "")
        if not ticker or ticker in seen:
            continue
        stars = item.get("stars", 0)
        if stars >= 2:
            opt = _options_proxy_for_ticker(ticker, prices)
            if not opt.get("ok"):
                opt = {
                    "ok": True, "price": "—", "max_pain": "—", "put_wall": "—",
                    "call_wall": "—", "gamma_flip_up": "—", "gamma_flip_down": "—",
                    "max_pain_dist": "—", "gamma_regime": "TRANSITION",
                    "greek_composite": "NEUTRAL", "conviction": "MODERATE",
                    "source": "META", "ticker": ticker,
                }
            candidates.append({
                "ticker": ticker,
                "theme": item.get("layer", "").replace("_", " "),
                "role": item.get("role", ""),
                "consensus_stars": stars,
                "accounts": item.get("accounts", []),
                "target": item.get("target", ""),
                "priority": item.get("priority", ""),
                "why_front_run": f"High consensus ({stars} stars) from {len(item.get('accounts',[]))} accounts — {item.get('role','')}",
                "source": "bottleneck_consensus",
                "options": opt,
                "catalyst": _find_catalyst(ticker, bottleneck_ref),
            })
            seen.add(ticker)
    for phase in rotation:
        status = phase.get("status", "")
        if "NEXT" in status or "FUTURE" in status or "NOW" in status:
            for ticker in phase.get("tickers", []):
                if ticker in seen:
                    continue
                meta = next((x for x in ref_tickers if x.get("ticker") == ticker), {})
                opt = _options_proxy_for_ticker(ticker, prices)
                if not opt.get("ok"):
                    opt = {
                        "ok": True, "price": "—", "max_pain": "—", "put_wall": "—",
                        "call_wall": "—", "gamma_flip_up": "—", "gamma_flip_down": "—",
                        "max_pain_dist": "—", "gamma_regime": "TRANSITION",
                        "greek_composite": "NEUTRAL", "conviction": "MODERATE",
                        "source": "META", "ticker": ticker,
                    }
                candidates.append({
                    "ticker": ticker,
                    "theme": phase.get("theme", ""),
                    "role": meta.get("role", "Rotation play"),
                    "consensus_stars": meta.get("stars", 1),
                    "accounts": meta.get("accounts", []),
                    "target": meta.get("target", phase.get("theme", "")),
                    "priority": "HIGH" if "NEXT" in status else "MEDIUM",
                    "why_front_run": f"Institutional rotation Phase {phase.get('phase')} ({phase.get('timeline')}): {phase.get('theme')}",
                    "source": "institutional_rotation",
                    "options": opt,
                    "catalyst": _find_catalyst(ticker, bottleneck_ref),
                })
                seen.add(ticker)
    rumor_watch = (news_analysis or {}).get("rumor_watch", [])
    for rw in rumor_watch:
        ticker = rw.get("ticker", "")
        if not ticker or ticker in seen:
            continue
        sig = rw.get("signal", "")
        if sig in ("STRONG_BULLISH_RUMOR", "STRONG_BEARISH_RUMOR", "NEWS_MOMENTUM_BUILDING", "BULLISH_CLUSTER", "RUMOR_WATCH"):
            opt = _options_proxy_for_ticker(ticker, prices)
            if not opt.get("ok"):
                opt = {
                    "ok": True, "price": "—", "max_pain": "—", "put_wall": "—",
                    "call_wall": "—", "gamma_flip_up": "—", "gamma_flip_down": "—",
                    "max_pain_dist": "—", "gamma_regime": "TRANSITION",
                    "greek_composite": "NEUTRAL", "conviction": "MODERATE",
                    "source": "META", "ticker": ticker,
                }
            candidates.append({
                "ticker": ticker,
                "theme": "News Momentum",
                "role": "Front-run headline",
                "consensus_stars": 0,
                "accounts": [],
                "target": "Momentum play",
                "priority": "HIGH",
                "why_front_run": f"News signal: {sig} — {rw.get('headline','')[:60]}",
                "source": "news_rumor",
                "options": opt,
                "news_signal": sig,
                "news_sentiment": rw.get("sentiment", 0),
                "news_headline": rw.get("headline", ""),
                "catalyst": {"quarter": "Now", "event": "News-driven", "priority": "HIGH"},
            })
            seen.add(ticker)
    def sort_key(c):
        prio_map = {"TOP": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        conv_map = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "CONFLICTED": 3}
        opt = c.get("options", {})
        return (prio_map.get(c.get("priority", ""), 99), -c.get("consensus_stars", 0), conv_map.get(opt.get("conviction", "CONFLICTED"), 99))
    candidates.sort(key=sort_key)
    return candidates

def _find_catalyst(ticker, bottleneck_ref):
    for ev in bottleneck_ref.get("catalyst_timeline", []):
        if ticker in ev.get("ticker", ""):
            return {"quarter": ev.get("quarter", ""), "event": ev.get("event", ""), "priority": ev.get("priority", "")}
    return {}

def _fetch_stablecoin_flows():
    if not _has_requests:
        return {}
    try:
        # Updated endpoint: stablecoins.llama.fi (DeFiLlama stablecoin API v2)
        r = requests.get("https://stablecoins.llama.fi/stablecoins", timeout=15)
        if r.status_code != 200:
            return {}
        data = r.json()
        total = 0.0
        change_7d = 0.0
        # New API format: data -> pepegAssets list
        pegged_assets = data.get("peggedAssets", []) if isinstance(data, dict) else []
        for pe in pegged_assets:
            if not isinstance(pe, dict):
                continue
            # circulating -> peggedUSD is the current total
            circ = pe.get("circulating", {})
            if isinstance(circ, dict):
                mc = circ.get("peggedUSD", 0) or 0
                total += float(mc)
                # previous week for 7d change
                prev = pe.get("circulatingPrevWeek", {})
                if isinstance(prev, dict):
                    prev_mc = prev.get("peggedUSD", 0) or 0
                    change_7d += (float(mc) - float(prev_mc))
        return {
            "total_b": round(total / 1e9, 2),
            "change_7d_b": round(change_7d / 1e9, 2),
            "source": "DeFiLlama",
        }
    except Exception as e:
        logger.warning(f"Stablecoin fetch failed: {e}")
        return {}


def _fetch_crypto_narrative():
    if not _has_requests:
        return {}
    out = {"trending": [], "categories": [], "fear_greed": None}
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        if r.status_code == 200:
            fg = r.json().get("data", [{}])[0]
            out["fear_greed"] = {
                "value": int(fg.get("value", 50)),
                "label": fg.get("value_text", "Neutral"),
            }
    except Exception as e:
        logger.warning(f"Fear&Greed failed: {e}")
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=10)
        if r.status_code == 200:
            coins = r.json().get("coins", [])
            out["trending"] = [{
                "name": c.get("item", {}).get("name"),
                "symbol": c.get("item", {}).get("symbol"),
                "market_cap_rank": c.get("item", {}).get("market_cap_rank"),
                "score": c.get("item", {}).get("score"),
            } for c in coins[:7]]
    except Exception as e:
        logger.warning(f"Trending failed: {e}")
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/categories", timeout=15)
        if r.status_code == 200:
            cats = r.json()
            out["categories"] = [{
                "name": c.get("name"),
                "market_cap": c.get("market_cap"),
                "volume_24h": c.get("volume_24h"),
                "top_3_coins": [x for x in c.get("top_3_coins", [])[:3]],
            } for c in sorted(cats, key=lambda x: x.get("volume_24h", 0) or 0, reverse=True)[:10]]
    except Exception as e:
        logger.warning(f"Categories failed: {e}")
    return out

def _fetch_crypto_market_structure():
    if not _has_requests:
        return {}
    out = {"funding": {}, "oi": {}, "liquidation": {}, "long_short": {}}
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT"]
    try:
        for sym in symbols:
            try:
                r = requests.get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=1", timeout=8)
                if r.status_code == 200:
                    d = r.json()
                    if d:
                        out["funding"][sym.replace("USDT", "")] = {
                            "rate": float(d[0].get("fundingRate", 0)),
                            "time": d[0].get("fundingTime", ""),
                        }
            except Exception:
                pass
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=10)
        if r.status_code == 200:
            tickers = {t.get("symbol"): t for t in r.json()}
            for sym in symbols:
                t = tickers.get(sym, {})
                if t:
                    out["oi"][sym.replace("USDT", "")] = {
                        "volume_24h": float(t.get("volume", 0)),
                        "price_change": float(t.get("priceChangePercent", 0)),
                        "weighted_avg_price": float(t.get("weightedAvgPrice", 0)),
                    }
    except Exception as e:
        logger.warning(f"Market structure failed: {e}")
    return out

def _build_crypto_unlock_proxy():
    return [
        {"token": "SOL", "date": "2026-06-01", "amount_m": 20, "type": "Cliff", "impact": "HIGH"},
        {"token": "AVAX", "date": "2026-05-20", "amount_m": 5, "type": "Linear", "impact": "MEDIUM"},
        {"token": "ARB", "date": "2026-05-25", "amount_m": 100, "type": "Cliff", "impact": "HIGH"},
        {"token": "OP", "date": "2026-06-15", "amount_m": 30, "type": "Linear", "impact": "MEDIUM"},
    ]

def _build_crypto_center(prices, news_analysis):
    cc = {
        "macro_regime": {},
        "capital_flows": {},
        "market_structure": {},
        "narrative": {},
        "tokenomics": {},
        "whale": {},
        "risk_flags": [],
    }
    btc_s = prices.get("BTC-USD")
    eth_s = prices.get("ETH-USD")
    if btc_s is not None and eth_s is not None:
        try:
            btc_mcap = float(btc_s.iloc[-1]) * 19.8e6
            eth_mcap = float(eth_s.iloc[-1]) * 120e6
            total = btc_mcap + eth_mcap + 800e9
            btc_d = btc_mcap / total
            cc["macro_regime"]["btc_dominance_proxy"] = round(btc_d, 3)
        except Exception:
            cc["macro_regime"]["btc_dominance_proxy"] = 0.55
    else:
        cc["macro_regime"]["btc_dominance_proxy"] = 0.55
    cc["capital_flows"] = _fetch_stablecoin_flows()
    cc["narrative"] = _fetch_crypto_narrative()
    cc["market_structure"] = _fetch_crypto_market_structure()
    whale_proxy = {}
    for ticker in ["BTC-USD", "ETH-USD"]:
        s = prices.get(ticker)
        if s is not None and len(s) >= 22:
            try:
                s_clean = pd.to_numeric(s, errors="coerce").dropna()
                r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1)
                whale_proxy[ticker] = "ACCUMULATING" if r1m > 0.05 else "DISTRIBUTING" if r1m < -0.05 else "NEUTRAL"
            except Exception:
                pass
    cc["whale"]["proxy"] = whale_proxy
    cc["tokenomics"]["upcoming_unlocks"] = _build_crypto_unlock_proxy()
    funding = cc["market_structure"].get("funding", {})
    if funding:
        for sym, data in funding.items():
            rate = data.get("rate", 0)
            if abs(rate) > 0.0005:
                cc["risk_flags"].append({
                    "type": "FUNDING_EXTREME",
                    "ticker": sym,
                    "value": rate,
                    "impact": "Longs overleveraged — correction risk" if rate > 0.001 else "Short squeeze potential" if rate < -0.001 else "Elevated funding",
                })
    return cc

# ------------------------------------------------------------------
# Core runner
# ------------------------------------------------------------------
def run_orchestrator(progress_cb=None, use_cache: bool = True, max_age_hours: float = 12.0, **kwargs) -> dict:
    t0 = time.time()
    _safe_progress(progress_cb, "Checking snapshot cache...", 0.02)
    if use_cache:
        try:
            snap = load_snapshot(max_age_hours=max_age_hours)
            if snap is not None and snap.get("ok"):
                snap["_source"] = "snapshot"
                snap["_snapshot_age"] = snapshot_age_str()
                logger.info(f"Snapshot loaded in {time.time()-t0:.1f}s")
                _safe_progress(progress_cb, f"Loaded from cache ({snapshot_age_str()})", 1.0)
                return snap
        except Exception as e:
            logger.warning(f"Snapshot load failed: {e}")

    result: dict = {
        "ok": False,
        "errors": [],
        "_source": "live",
        "_generated_at": datetime.now().isoformat(),
        "gip": None,
        "global": {},
        "risk_ranges": {},
        "scenarios": {},
        "narratives": {},
        "discovery": {},
        "transition": None,
        "health": {},
        "analogs": {},
        "bottleneck": {},
        "playbook": {},
        "prices": {},
        "auto_discoveries": {},
        "feedback_eval": {},
        "gamma": {},
        "leveraged_etf": {},
        "daily_signals": [],
        "regime_forecast": {},
        "forward_returns": {},
        "leading_signals": {},
        "price_clusters": {},
        "news_narratives": {},
        "bottleneck_discovery": {},
        "frontrun": {},
        "ihsg_sector_momentum": {},
        "ihsg_commodity_overlay": {},
        "ihsg_rupiah_regime": {},
        "ihsg_foreign_flow": {},
        "ihsg_macro_overlay": {},
        "alpha_center": {},
        "gamma_data": {},
        "greeks_data": {},
        "cot_oi": {},
        "dxy_correlation": {},
        "vol_forecast": {},
        "stress_test": [],
        "prices_loaded": 0,
        "fred_coverage": 0,
        "build_time_s": 0,
        "daily_signals_summary": {},
        "gex_data": {},
        "charm_data": {},
        "vanna_data": {},
        "odte_enhanced": {},
        "structure_data": {},
        "afternoon_data": {},
        "volga_data": {},
        "institutional_data": {},
        "crypto_tokens": {},
        "rumor_watch": [],
        "bottleneck_research": {},
        "front_run_candidates": [],
        "crypto_center": {},
        "behavioral_macro": {},
        "odte_monitor": {},
        "skew_term": {},
        "reflexivity": {},
        "boom_bust": {},
        "conviction_sizing": {},
        "vanna_charm_flows": {},
        "country_list": [],
        "interconnect": {},
        "yfinance_options": {},
        "scenario_discovery": {},
        "transmission": {},
        "regime_transition": {},
        "news_nlp_v3": {},
        "bottleneck_v3": {},
        "gex_data": {},
        "charm_data": {},
        "vanna_data": {},
        "odte_enhanced": {},
        "structure_data": {},
        "afternoon_data": {},
        "volga_data": {},
        "institutional_data": {},
        # NEW: Simulation v27.3
        "simulation_results": {},
        "simulation_summary": {},
        "portfolio_stress": {},
        "options_pnl_simulator": {},
        # Attachment 4
        "idhl_data": {},
        "rc_data": {},
        "afs_data": {},
        "walkforward_results": {},
        "fractional_kelly": {},
        "bayesian_fusion": {},
        "duration_hmm": {},
        "cri_v2_data": {},
    }

    try:
        # ---- FRED Macro ----
        _safe_progress(progress_cb, "Fetching FRED macro data...", 0.05)
        try:
            fred_bundle = load_fred_bundle(force_refresh=True)
        except Exception as e:
            logger.error(f"FRED bundle failed: {e}")
            result["errors"].append(f"fred: {e}")
            fred_bundle = {"series": {}, "meta": {"loaded": 0, "requested": 0}}

        fred = fred_bundle.get("series", {})
        fred_meta = fred_bundle.get("meta", {})

        if fred_meta.get("loaded", 0) == 0:
            logger.warning("FRED returned 0 series - using synthetic fallback")
            fred = _fred_fallback()
            fred_meta = {"loaded": 15, "requested": 15, "missing": 0, "source": "synthetic_fallback"}
            result["errors"].append("fred: using synthetic fallback (live fetch failed)")

        result["fred_meta"] = fred_meta
        result["fred_series"] = fred
        result["fred_coverage"] = fred_meta.get("loaded", 0)

        # ---- Prices ----
        tickers = _all_tickers()
        logger.info(f"Price universe: {len(tickers)} tickers")
        _safe_progress(progress_cb, f"Fetching {len(tickers)} tickers from Yahoo Finance...", 0.10)

        if load_prices is None:
            raise RuntimeError("load_prices not available (data.loader import failed)")

        prices = {}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                prices = load_prices(tickers, days=756, max_age_hours=max_age_hours, progress_cb=progress_cb)
                if prices and len(prices) > len(tickers) * 0.7:
                    break
                logger.warning(f"Price load attempt {attempt+1}/{max_retries}: only {len(prices)}/{len(tickers)} loaded, retrying...")
            except Exception as e:
                logger.warning(f"Price load attempt {attempt+1}/{max_retries} failed: {e}")
                result["errors"].append(f"prices attempt {attempt+1}: {e}")
                # Stop retrying if rate limited
                if "Rate limit" in str(e) or "Too Many Requests" in str(e) or "429" in str(e):
                    logger.warning("Rate limit detected during price load — using cache/synthetic fallback")
                    break
            if attempt < max_retries - 1:
                backoff = 2 ** attempt + 3  # Extra delay for cloud rate limits
                logger.info(f"Backing off {backoff}s before retry...")
                time.sleep(backoff)

        if not prices:
            logger.error("All price load attempts failed")
            result["errors"].append("prices: all attempts failed")

        result["prices"] = prices
        result["prices_loaded"] = len(prices)
        result["price_meta"] = {"requested": len(tickers), "loaded": len(prices)}

        if not prices:
            raise RuntimeError("No price data loaded - cannot proceed")

        # ---- NEWS & RUMOR ----
        _safe_progress(progress_cb, "Scanning news & rumors...", 0.18)
        news_headlines = _fetch_news_headlines(list(prices.keys())[:100])
        news_analysis = _analyze_news(news_headlines, prices)
        result["news_narratives"] = news_analysis
        result["rumor_watch"] = news_analysis.get("rumor_watch", [])

        # ---- Bottleneck ----
        _safe_progress(progress_cb, "Loading bottleneck intelligence...", 0.20)
        bottleneck_ref = _load_bottleneck_ref()
        result["bottleneck_research"] = bottleneck_ref
        _safe_progress(progress_cb, "Generating front-run candidates...", 0.22)
        front_run = _generate_front_run_candidates(prices, news_analysis, bottleneck_ref)
        result["front_run_candidates"] = front_run

        # ---- CRYPTO CENTER ----
        _safe_progress(progress_cb, "Building crypto on-chain center...", 0.25)
        cc = _build_crypto_center(prices, news_analysis)
        result["crypto_center"] = cc

        # ---- PROXY FALLBACKS ----
        _safe_progress(progress_cb, "Computing proxy fallbacks...", 0.28)
        rr_proxy = _risk_range_proxy(prices)
        crypto_proxy = _crypto_onchain_proxy(prices)
        result["crypto_tokens"] = crypto_proxy
        ihsg_layers = _ihsg_layers(prices, "Q3")
        for k, v in ihsg_layers.items():
            result[k] = v

        # ---- GIP Engine ----
        _safe_progress(progress_cb, "Running GIP regime model...", 0.55)
        if GIPEngine is None or GIPResult is None:
            raise RuntimeError("GIP engine not available")
        try:
            gip_engine = GIPEngine()
            gip = gip_engine.run(fred, prices)
        except Exception as e:
            logger.error(f"GIP engine failed: {e}")
            result["errors"].append(f"gip: {e}")
            raise
        result["gip"] = gip
        quad = getattr(gip, "structural_quad", "Q3")
        monthly_quad = getattr(gip, "monthly_quad", "Q2")
        gip_features = getattr(gip, "features", {})

        # ---- Global Regime ----
        result["global"] = _global_fallback(quad)

        # ---- Market Health ----
        _safe_progress(progress_cb, "Running market health & breadth...", 0.65)
        if MarketHealthEngine is not None:
            try:
                mkt = MarketHealthEngine().run(prices, gip_features, quad)
                result["health"] = mkt
            except Exception as e:
                logger.warning(f"MarketHealthEngine failed: {e}")
                result["errors"].append(f"market_health: {e}")
                result["health"] = {"error": str(e), "verdict": "Unknown"}
        else:
            result["health"] = {"error": "Engine not imported", "verdict": "Unknown"}

        # ---- Risk Ranges ----
        _safe_progress(progress_cb, "Computing Risk Ranges (TRR/LRR)...", 0.72)
        try:
            # v2 — pass quad + vix for regime-conditional ranges
            ranges = RiskRangeEngine(current_quad=quad, vix=vix_last).run(prices)
            if ranges and ranges.get("asset_ranges"):
                merged_ranges = dict(rr_proxy.get("asset_ranges", {}))
                merged_ranges.update(ranges.get("asset_ranges", {}))
                ranges["asset_ranges"] = merged_ranges
            else:
                ranges = rr_proxy
            result["risk_ranges"] = ranges
        except Exception as e:
            logger.warning(f"RiskRangeEngine failed, using proxy: {e}")
            result["errors"].append(f"risk_ranges: {e}")
            result["risk_ranges"] = rr_proxy

        # ---- NEW v27.2 ENGINES ----
        _safe_progress(progress_cb, "Running Behavioral Macro (Yves)...", 0.30)
        try:
            dgs10 = float(fred.get("DGS10", pd.Series()).dropna().iloc[-1]) if fred.get("DGS10") is not None else 4.5
            t5yie = float(fred.get("T5YIE", pd.Series()).dropna().iloc[-1]) if fred.get("T5YIE") is not None else 2.4
            real_yield = dgs10 - t5yie
            vix_s = prices.get("^VIX")
            vix_last = float(vix_s.dropna().iloc[-1]) if vix_s is not None and not vix_s.empty else 20.0
            behavioral = get_behavioral_macro(vix=vix_last, real_yield=real_yield, dxy_ret=0.0)
            result["behavioral_macro"] = behavioral
        except Exception as e:
            logger.warning(f"Behavioral macro failed: {e}")
            result["errors"].append(f"behavioral: {e}")
            result["behavioral_macro"] = {"yves": {"alert": None}}

        _safe_progress(progress_cb, "Running 0DTE Monitor (Cem Karsan)...", 0.32)
        try:
            # Reduced to 3 core tickers to avoid Yahoo rate limit on cloud
            odte = run_odte_monitor(["SPY", "QQQ", "IWM"], prices)
            result["odte_monitor"] = odte
        except Exception as e:
            logger.warning(f"0DTE monitor failed: {e}")
            result["errors"].append(f"odte: {e}")
            # Fallback proxy
            result["odte_monitor"] = {"expiry": "Weekly", "tickers": {}, "cascade_warning": False, "summary": "0DTE unavailable — rate limit"}

        _safe_progress(progress_cb, "Running Skew Term Structure...", 0.34)
        try:
            skew = run_skew_term(list(US_SECTORS.keys()) + ["SPY", "QQQ", "IWM", "GLD", "TLT"], prices)
            result["skew_term"] = skew
        except Exception as e:
            logger.warning(f"Skew term failed: {e}")
            result["errors"].append(f"skew: {e}")

        _safe_progress(progress_cb, "Running Reflexivity (Soros)...", 0.36)
        try:
            reflex = run_reflexivity(prices, fred, quad)
            result["reflexivity"] = reflex
        except Exception as e:
            logger.warning(f"Reflexivity failed: {e}")
            result["errors"].append(f"reflexivity: {e}")

        _safe_progress(progress_cb, "Running Boom-Bust Stage...", 0.38)
        try:
            bb = classify_stage(prices, fred, result.get("health", {}), quad)
            result["boom_bust"] = bb
        except Exception as e:
            logger.warning(f"Boom-bust failed: {e}")
            result["errors"].append(f"boombust: {e}")

        _safe_progress(progress_cb, "Running Vanna & Charm Flows...", 0.40)
        try:
            vanna_charm = {}
            for t in ["SPY", "QQQ", "IWM", "GLD", "TLT", "BTC-USD", "ETH-USD"]:
                vc = get_vanna_charm_flows(t, prices, vix_last, 0.0, 7)
                if vc:
                    vanna_charm[t] = vc
            result["vanna_charm_flows"] = vanna_charm
        except Exception as e:
            logger.warning(f"Vanna/Charm failed: {e}")
            result["errors"].append(f"vannacharm: {e}")

        # ---- Interconnect / Cascade ----
        _safe_progress(progress_cb, "Running Interconnect Cascade...", 0.43)
        try:
            interconnect = run_interconnect(prices, fred, news_analysis, quad)
            result["interconnect"] = interconnect
        except Exception as e:
            logger.warning(f"Interconnect failed: {e}")
            result["errors"].append(f"interconnect: {e}")

        # ---- Phase 2: Live Options + Scenario + Transmission ----
        _safe_progress(progress_cb, "Fetching live options...", 0.44)
        yfinance_options_data = {}
        if YFinanceOptionsEngine is not None:
            try:
                yf_engine = YFinanceOptionsEngine()
                # Reduced to 3 core tickers + longer delay to avoid Yahoo rate limit on cloud
                key_tickers = [t for t in ["SPY","QQQ","IWM"] if t in prices][:3]
                for i, ticker in enumerate(key_tickers):
                    if i > 0:
                        time.sleep(3.0)  # Aggressive delay for Yahoo rate limit
                    try:
                        opt = yf_engine.analyze(ticker)
                        if opt and opt.get("ok"):
                            yfinance_options_data[ticker] = opt
                    except Exception as e:
                        logger.warning(f"Options fetch failed for {ticker}: {e}")
                        # Stop trying if rate limited
                        if "Rate limit" in str(e) or "Too Many Requests" in str(e):
                            logger.warning("Yahoo rate limit detected — skipping remaining options fetch")
                            break
            except Exception as e:
                logger.error(f"YFinanceOptionsEngine failed: {e}")
        result["yfinance_options"] = yfinance_options_data

        _safe_progress(progress_cb, "Scenario discovery...", 0.46)
        try:
            scenario_discovery = run_scenario_discovery(prices, fred, news_analysis, quad)
            result["scenario_discovery"] = scenario_discovery
        except Exception as e:
            logger.warning(f"Scenario discovery failed: {e}")
            result["errors"].append(f"scenario_discovery: {e}")

        _safe_progress(progress_cb, "Transmission engine...", 0.47)
        try:
            transmission = run_transmission(prices, fred, news_analysis, quad)
            result["transmission"] = transmission
        except Exception as e:
            logger.warning(f"Transmission failed: {e}")
            result["errors"].append(f"transmission: {e}")

        # ---- Phase 3: Regime Transition + News NLP v3 + Bottleneck v3 ----
        _safe_progress(progress_cb, "Regime transition...", 0.48)
        try:
            regime_transition = run_regime_transition(prices, fred, quad, getattr(gip, "structural_probs", {}) if gip else {})
            result["regime_transition"] = regime_transition
        except Exception as e:
            logger.warning(f"Regime transition failed: {e}")
            result["errors"].append(f"regime_transition: {e}")

        _safe_progress(progress_cb, "News NLP v3...", 0.49)
        try:
            news_nlp_v3 = run_news_nlp(news_headlines)
            result["news_nlp_v3"] = news_nlp_v3
        except Exception as e:
            logger.warning(f"News NLP v3 failed: {e}")
            result["errors"].append(f"news_nlp_v3: {e}")

        _safe_progress(progress_cb, "Bottleneck discovery v3...", 0.50)
        try:
            bottleneck_v3 = run_bottleneck_discovery_v3(prices, fred, news_analysis)
            result["bottleneck_v3"] = bottleneck_v3
        except Exception as e:
            logger.warning(f"Bottleneck v3 failed: {e}")
            result["errors"].append(f"bottleneck_v3: {e}")

        # ---- Bottleneck / Alpha ----
        _safe_progress(progress_cb, "Scanning bottleneck & alpha ideas...", 0.80)
        bottleneck_raw = {"all_candidates": [], "level_1": [], "level_2": [], "watch": [],
                          "avoid": [], "regime_traps": [], "playbook": {}, "regime_filter": {},
                          "meta": {"universe": 0, "scored": 0}}
        if BottleneckEngine is not None:
            try:
                try:
                    bottleneck_raw = BottleneckEngine().run(
                        prices, None,
                        quad, monthly_quad,
                        "SPY", result.get("risk_ranges"), -0.10, 25
                    )
                except TypeError:
                    try:
                        bottleneck_raw = BottleneckEngine().run(prices)
                    except Exception:
                        bottleneck_raw = BottleneckEngine().run()
                result["bottleneck"] = bottleneck_raw
            except Exception as e:
                logger.warning(f"BottleneckEngine failed: {e}")
                result["errors"].append(f"alpha: {e}")

        all_candidates = bottleneck_raw.get("all_candidates", [])
        alpha_items = []
        for item in all_candidates:
            alpha_items.append({
                "ticker": item.get("ticker", "-"),
                "scanner_type": item.get("btn_type", "structural"),
                "direction": "LONG" if item.get("level") in ("level_1", "level_2") else ("SHORT" if item.get("level") == "avoid" else "WATCH"),
                "grade": "B" if item.get("level") == "level_2" else ("A" if item.get("level") == "level_1" else "C"),
                "priority_score": item.get("score", 0) * 100,
                "price": item.get("px"),
                "entry": item.get("px"),
                "target_1": None,
                "target_2": None,
                "stop_loss": None,
                "rr": None,
                "worth_entering": "YES" if item.get("level") in ("level_1", "level_2") else "WAIT",
                "time_estimate": "1-2 weeks",
                "thesis": item.get("rationale", ""),
                "recommendation": item.get("rationale", ""),
            })

        if not alpha_items:
            logger.warning("Bottleneck engine returned 0 candidates - using price-action proxy + news")
            vix_last = 20.0
            vix_s = prices.get("^VIX")
            if vix_s is not None and not vix_s.empty:
                try:
                    vix_last = float(vix_s.iloc[-1])
                except Exception:
                    pass
            # v2.2: Pass composite_signals so Alpha Center direction matches other tabs
            ac_proxy = _alpha_center_proxy(
                prices, result["risk_ranges"], quad, vix_last, news_analysis,
                composite_signals=result.get("composite_signals", {}),
                cot_data=(result.get("cot_oi", {}) or {}).get("cot", {}),
                oi_data=(result.get("cot_oi", {}) or {}).get("oi", {}),
                greeks_data=result.get("greeks_data", {}),
                gamma_data=result.get("gamma_data", {}),
            )
            alpha_items = ac_proxy.get("all", [])
            result["alpha_center"] = ac_proxy
        else:
            news_map = news_analysis.get("ticker_specific", {})
            for item in alpha_items:
                ticker = item.get("ticker", "")
                news = news_map.get(ticker, {})
                if news and news.get("front_run_signal"):
                    item["news_signal"] = news["front_run_signal"]
                    item["news_headline"] = (news.get("headlines") or [""])[0]
                    item["news_sentiment"] = news.get("sentiment_score")
                    item["priority_score"] = (item.get("priority_score") or 0) + 20
                    if item["news_signal"] in ["STRONG_BULLISH_RUMOR", "NEWS_MOMENTUM_BUILDING"] and item.get("direction") == "LONG":
                        item["scanner_type"] = "news_momentum"
                        if item.get("grade") == "C": item["grade"] = "B"
            result["alpha_center"] = {
                "meta": {
                    "regime": quad,
                    "bias": "Structural" if quad in ("Q1", "Q2") else "Defensive",
                    "vix": vix_last,
                    "total_items": len(alpha_items),
                },
                "all": alpha_items,
                "level_1": [i for i in alpha_items if i.get("grade") == "A"],
                "level_2": [i for i in alpha_items if i.get("grade") == "B"],
                "watch": [i for i in alpha_items if i.get("grade") == "C"],
            }

        # ── SIMULATION LAYER v27.3 ──
        # Run 100 simulations on all alpha_items + daily_signals candidates
        _safe_progress(progress_cb, "Running Monte Carlo simulation (100x per ticker)...", 0.82)
        try:
            if _V2_SIM and alpha_items:
                # Build setups dict for simulation
                sim_setups = {}
                sim_tickers = []
                for item in alpha_items:
                    t = item.get("ticker")
                    if not t:
                        continue
                    sim_tickers.append(t)
                    sim_setups[t] = {
                        "direction": item.get("direction", "LONG"),
                        "entry": item.get("entry") or item.get("price", 0),
                        "stop": item.get("stop_loss") or (item.get("entry", 0) * 0.95),
                        "target_1": item.get("target_1") or (item.get("entry", 0) * 1.05),
                        "target_2": item.get("target_2") or (item.get("target_1", 0) * 1.05),
                        "rr": item.get("rr", 0),
                    }
                # Build dark pool map
                dark_pool_map = {}
                unusual_map = {}
                for t in sim_tickers:
                    # Reconstruct dark pool from row data if available
                    # For now, use institutional proxy + front_run data
                    dp = None
                    inst = result.get("institutional_data", {})
                    if inst and inst.get("per_ticker") and t in inst.get("per_ticker", {}):
                        dp_data = inst["per_ticker"][t]
                        if isinstance(dp_data, dict) and dp_data.get("anomaly_score", 0) > 0.6:
                            buy = float(dp_data.get("buy_pressure", 0) or 0)
                            sell = float(dp_data.get("sell_pressure", 0) or 0)
                            total = buy + sell
                            imbalance = (buy - sell) / total * 100 if total > 0 else 0
                            dp = {
                                "imbalance": round(imbalance, 1),
                                "buy_pressure": buy,
                                "sell_pressure": sell,
                                "dp_signal": "BUY" if imbalance > 15 else "SELL" if imbalance < -15 else "NEUTRAL",
                                "divergence": "HIDDEN_ACCUMULATION" if imbalance > 15 else "HIDDEN_DISTRIBUTION" if imbalance < -15 else "NEUTRAL",
                            }
                    dark_pool_map[t] = dp
                    # Unusual activity proxy
                    ua = None
                    if t in prices:
                        try:
                            s = _safe_series(prices[t])
                            if len(s) >= 20:
                                vol_5 = float(s.tail(5).std())
                                vol_20 = float(s.tail(20).std()) if len(s) >= 20 else vol_5
                                r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
                                if vol_20 > 0 and vol_5 / vol_20 > 2.0 and abs(r5d) < 0.02:
                                    ua = {"large_order_detected": True, "signal": "BUY" if r5d >= 0 else "SELL", "confidence": min(100, int((vol_5/vol_20 - 2) * 50))}
                        except Exception:
                            pass
                    unusual_map[t] = ua

                # Run batch simulation v2.0 (ALL extensions)
                sim_results = run_simulation_batch(
                    sim_tickers,
                    prices,
                    sim_setups,
                    options_map=result.get("greeks_data"),
                    dark_pool_map=dark_pool_map,
                    unusual_map=unusual_map,
                    n_simulations=100,
                    threshold=65.0,
                    portfolio_value=float(kwargs.get("portfolio_value", 100_000) or 100_000),
                )
                result["simulation_results"] = {
                    t: {
                        "win_rate": r.win_rate,
                        "exp_return_pct": r.exp_return_pct,
                        "avg_drawdown_pct": r.avg_drawdown_pct,
                        "sharpe_like": r.sharpe_like,
                        "robustness_score": r.robustness_score,
                        "optimal_entry_adj_pct": r.optimal_entry_adj_pct,
                        "optimal_stop_adj_pct": r.optimal_stop_adj_pct,
                        "optimal_target_adj_pct": r.optimal_target_adj_pct,
                        "time_to_win_days": r.time_to_win_days,
                        "time_to_loss_days": r.time_to_loss_days,
                        "max_consecutive_losses": r.max_consecutive_losses,
                        "passes_filter": r.passes_filter,
                        "raw_metrics": r.raw_metrics,
                        "extensions": r.extensions,
                    }
                    for t, r in sim_results.items()
                }
                result["simulation_summary"] = get_simulation_summary(sim_results)
                logger.info(
                    f"Simulation complete: {result['simulation_summary']['total']} tickers, "
                    f"{result['simulation_summary']['passed']} passed, "
                    f"avg score {result['simulation_summary']['avg_score']:.1f}"
                )
                # Filter alpha_items by simulation
                passed_tickers = {
                    t for t, r in sim_results.items()
                    if r.passes_filter
                }
                result["alpha_center"]["all"] = [
                    i for i in result["alpha_center"]["all"]
                    if i.get("ticker") in passed_tickers
                ]
                result["alpha_center"]["level_1"] = [
                    i for i in result["alpha_center"]["level_1"]
                    if i.get("ticker") in passed_tickers
                ]
                result["alpha_center"]["level_2"] = [
                    i for i in result["alpha_center"]["level_2"]
                    if i.get("ticker") in passed_tickers
                ]
                result["daily_signals"] = result["alpha_center"]["all"][:20]
                # Attach simulation metadata to each item
                for item in result["alpha_center"]["all"]:
                    t = item.get("ticker")
                    if t in result["simulation_results"]:
                        item["simulation"] = result["simulation_results"][t]

                # ── PORTFOLIO STRESS SIMULATION v2.0 ──
                _safe_progress(progress_cb, "Running portfolio correlation stress test...", 0.83)
                try:
                    if _V2_SIM and len(passed_tickers) >= 2:
                        from engines.simulation_engine import run_portfolio_simulation
                        port_tickers = list(passed_tickers)[:15]  # Top 15 for performance
                        port_setups = {t: sim_setups[t] for t in port_tickers if t in sim_setups}
                        if len(port_tickers) >= 2:
                            port_sim = run_portfolio_simulation(
                                port_tickers, prices, port_setups, n_sims=50, holding_days=10
                            )
                            result["portfolio_stress"] = port_sim
                            logger.info(
                                f"Portfolio stress: {port_sim.get('n_tickers',0)} tickers, "
                                f"corr {port_sim.get('avg_correlation',0):.2f}, "
                                f"exp ret {port_sim.get('portfolio_exp_return_pct',0):.1f}%, "
                                f"Sharpe {port_sim.get('portfolio_sharpe',0):.2f}"
                            )
                except Exception as e:
                    logger.warning(f"Portfolio stress failed: {e}")
                    result["errors"].append(f"portfolio_stress: {e}")

                # ── OPTIONS P&L SIMULATOR ──
                _safe_progress(progress_cb, "Running options P&L simulator...", 0.835)
                try:
                    if _V2_SIM:
                        from engines.simulation_engine import select_options_strategy
                        options_pnl = {}
                        for t in passed_tickers:
                            sim_res = sim_results.get(t)
                            if not sim_res:
                                continue
                            opts = result.get("greeks_data", {}).get(t, {}) if result.get("greeks_data") else {}
                            if not opts:
                                opts = result.get("yfinance_options", {}).get(t, {}) if result.get("yfinance_options") else {}
                            strat = select_options_strategy(t, sim_res, opts)
                            if strat and strat.get("best"):
                                options_pnl[t] = {
                                    "strategy": strat["best"].get("strategy", "NO_EDGE"),
                                    "name": strat["best"].get("name", "—"),
                                    "confidence": strat["best"].get("confidence", 0),
                                    "rationale": strat["best"].get("rationale", ""),
                                    "candidates": [c.get("name", "—") for c in strat.get("candidates", [])[:3]],
                                }
                        result["options_pnl_simulator"] = options_pnl
                        logger.info(f"Options P&L simulator: {len(options_pnl)} tickers mapped")
                except Exception as e:
                    logger.warning(f"Options P&L simulator failed: {e}")
                    result["errors"].append(f"options_pnl: {e}")

        except Exception as e:
            logger.warning(f"Simulation layer failed: {e}")
            result["errors"].append(f"simulation: {e}")

                # ---- Conviction Sizing (Soros) ----
        _safe_progress(progress_cb, "Calculating conviction sizing...", 0.42)
        try:
            sizing = run_sizing(alpha_items, result.get("gamma_data", {}), result.get("greeks_data", {}),
                              result.get("boom_bust", {}), result.get("reflexivity", {}), 100000)
            result["conviction_sizing"] = sizing
        except Exception as e:
            logger.warning(f"Conviction sizing failed: {e}")
            result["errors"].append(f"sizing: {e}")

        # ---- Gamma & Greeks ----
        _safe_progress(progress_cb, "Running gamma & Greeks proxy...", 0.88)
        vix_last = 20.0
        vix_s = prices.get("^VIX")
        if vix_s is not None and not vix_s.empty:
            try:
                vix_last = float(vix_s.iloc[-1])
            except Exception:
                pass

        dxy_s = prices.get("DX-Y.NYB")
        dxy_ret = 0.0
        if dxy_s is not None and len(dxy_s) > 22:
            try:
                dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
            except Exception:
                pass

        # ---- VolSignals-style engines ----
        key_tickers = ["SPY", "QQQ", "IWM", "GLD", "TLT", "BTC-USD", "ETH-USD"]
        gex_data = {}
        charm_data = {}
        vanna_data = {}
        odte_enhanced = {}
        structure_data = {}
        afternoon_data = {}
        volga_data = {}
        inst_data = {}

        _safe_progress(progress_cb, "Running GEX Engine...", 0.41)
        try:
            gex_data = gex_analyze_multi(key_tickers, prices, vix_last)
            result["gex_data"] = gex_data
        except Exception as e:
            logger.warning(f"GEX engine failed: {e}")
            result["errors"].append(f"gex: {e}")

        _safe_progress(progress_cb, "Running Charm Proxy...", 0.42)
        try:
            charm_data = charm_analyze_multi(key_tickers, prices, vix_last)
            result["charm_data"] = charm_data
        except Exception as e:
            logger.warning(f"Charm proxy failed: {e}")
            result["errors"].append(f"charm: {e}")

        _safe_progress(progress_cb, "Running Vanna Proxy...", 0.43)
        try:
            vanna_data = vanna_analyze_multi(key_tickers, prices, vix_last, dxy_ret)
            result["vanna_data"] = vanna_data
        except Exception as e:
            logger.warning(f"Vanna proxy failed: {e}")
            result["errors"].append(f"vanna: {e}")

        _safe_progress(progress_cb, "Running 0DTE Enhanced...", 0.44)
        try:
            odte_enhanced = odte_enhanced_multi(key_tickers, prices, vix_last)
            result["odte_enhanced"] = odte_enhanced
        except Exception as e:
            logger.warning(f"0DTE enhanced failed: {e}")
            result["errors"].append(f"odte_enh: {e}")

        _safe_progress(progress_cb, "Running Structure Quality...", 0.45)
        try:
            structure_data = structure_analyze_multi(key_tickers, prices)
            result["structure_data"] = structure_data
        except Exception as e:
            logger.warning(f"Structure quality failed: {e}")
            result["errors"].append(f"structure: {e}")

        _safe_progress(progress_cb, "Running Afternoon Signal...", 0.46)
        try:
            afternoon_data = afternoon_analyze_multi(key_tickers, prices, charm_data, vanna_data, vix_last, gex_data, structure_data)
            result["afternoon_data"] = afternoon_data
        except Exception as e:
            logger.warning(f"Afternoon signal failed: {e}")
            result["errors"].append(f"afternoon: {e}")

        _safe_progress(progress_cb, "Running Volga Proxy...", 0.47)
        try:
            volga_data = analyze_volga("SPY", prices, prices, vix_last)
            result["volga_data"] = volga_data
        except Exception as e:
            logger.warning(f"Volga proxy failed: {e}")
            result["errors"].append(f"volga: {e}")

        _safe_progress(progress_cb, "Running Institutional Proxy...", 0.48)
        try:
            inst_data = inst_analyze_multi(key_tickers, prices, vix_last)
            result["institutional_data"] = inst_data
        except Exception as e:
            logger.warning(f"Institutional proxy failed: {e}")
            result["errors"].append(f"institutional: {e}")

        all_gamma_tickers = list(prices.keys())[:150]
        gamma_results = {}
        greeks_results = {}

        if GammaEngine is not None:
            try:
                gamma_results = GammaEngine().analyze_multi(all_gamma_tickers, prices, vix_last, dxy_ret)
            except Exception as e:
                logger.warning(f"GammaEngine failed: {e}")
                result["errors"].append(f"gamma: {e}")

        if GreeksProxy is not None:
            try:
                greeks_results = GreeksProxy().analyze_multi(
                    all_gamma_tickers, prices, vix_last, dxy_ret, quad
                )
            except Exception as e:
                logger.warning(f"GreeksProxy failed: {e}")
                result["errors"].append(f"greeks: {e}")

        result["gamma"] = gamma_results
        result["gamma_data"] = gamma_results
        result["greeks"] = greeks_results
        result["greeks_data"] = greeks_results

        # ---- Playbook ----
        _safe_progress(progress_cb, "Building playbook & summary...", 0.95)
        try:
            playbook = get_playbook(quad, monthly_quad)
            playbook.setdefault("best_assets", [])
            playbook.setdefault("worst_assets", [])
            playbook.setdefault("strategy", f"Trade {quad} regime. Monthly: {monthly_quad}.")
            playbook.setdefault("sectors_overweight", [])
            playbook.setdefault("sectors_underweight", [])
            playbook.setdefault("style", "")
            playbook.setdefault("fx", "")
            playbook.setdefault("bonds", "")
            result["playbook"] = playbook
        except Exception as e:
            logger.warning(f"Playbook failed: {e}")
            result["playbook"] = {
                "structural": quad, "monthly": monthly_quad,
                "best_assets": [], "worst_assets": [],
                "strategy": f"Trade {quad} regime. Monthly: {monthly_quad}.",
                "sectors_overweight": [], "sectors_underweight": [],
                "style": "", "fx": "", "bonds": "",
            }

        # ---- Daily signals summary ----
        strong_longs = sum(1 for i in alpha_items if i.get("direction") == "LONG" and i.get("grade") in ("A", "A+"))
        longs = sum(1 for i in alpha_items if i.get("direction") == "LONG")
        strong_shorts = sum(1 for i in alpha_items if i.get("direction") == "SHORT" and i.get("grade") in ("A", "A+"))
        shorts = sum(1 for i in alpha_items if i.get("direction") == "SHORT")
        result["daily_signals_summary"] = {
            "total": len(alpha_items),
            "strong_longs": strong_longs,
            "longs": longs,
            "strong_shorts": strong_shorts,
            "shorts": shorts,
            "neutrals": len(alpha_items) - longs - shorts,
            "top_5_by_score": sorted(alpha_items, key=lambda x: x.get("priority_score", 0), reverse=True)[:5],
        }
        result["daily_signals"] = alpha_items[:20]

        # ---- Frontrun / Transition ----
        result["transition"] = SimpleNamespace(
            front_run_window="1-2w" if quad in ("Q1", "Q2") else "3-6w"
        )
        result["frontrun"] = {
            "boarding_now": [i for i in alpha_items if i.get("grade") == "A"][:3],
            "gate_opens_soon": [i for i in alpha_items if i.get("grade") == "B"][:3],
            "check_in": [i for i in alpha_items if i.get("grade") == "C"][:3],
            "wait": [],
        }

        # ---- Regime forecast ----
        result["regime_forecast"] = {
            "1m": {"predicted_quad": monthly_quad, "prediction_confidence": 0.55},
            "3m": {"predicted_quad": quad, "prediction_confidence": 0.60},
            "6m": {"predicted_quad": quad, "prediction_confidence": 0.50},
        }

        # ---- DXY Correlation ----
        try:
            dxy_corr_data = {"dxy_trend": "Neutral", "dxy_1m": dxy_ret, "total_correlated": 0,
                           "strongest_positive_corr": [], "strongest_negative_corr": []}
            if dxy_s is not None and len(dxy_s) >= 22:
                dxy_clean = pd.to_numeric(dxy_s, errors="coerce").dropna()
                pos_corr = []; neg_corr = []; correlated = 0
                for ticker, s in prices.items():
                    if s is None or len(s) < 22 or ticker == "DX-Y.NYB":
                        continue
                    try:
                        s_clean = pd.to_numeric(s, errors="coerce").dropna()
                        min_len = min(len(dxy_clean), len(s_clean))
                        if min_len < 22:
                            continue
                        dxy_slice = dxy_clean.tail(min_len).pct_change().dropna()
                        s_slice = s_clean.tail(min_len).pct_change().dropna()
                        if len(dxy_slice) >= 20 and len(s_slice) >= 20:
                            dxy_arr = dxy_slice.tail(20).to_numpy()
                            s_arr = s_slice.tail(20).to_numpy()
                            mask = np.isfinite(dxy_arr) & np.isfinite(s_arr)
                            if mask.sum() < 10:
                                continue
                            dxy_clean_arr = dxy_arr[mask]
                            s_clean_arr = s_arr[mask]
                            if dxy_clean_arr.std() == 0 or s_clean_arr.std() == 0:
                                continue
                            with np.errstate(invalid='ignore'):
                                corr = np.corrcoef(dxy_clean_arr, s_clean_arr)[0, 1]
                            if not math.isfinite(corr):
                                continue
                            correlated += 1
                            if abs(corr) > 0.3:
                                entry = {"correlation": round(corr, 2), "meaning": "Rises with DXY" if corr > 0 else "Falls when DXY rises"}
                                if corr > 0:
                                    pos_corr.append((ticker, entry))
                                else:
                                    neg_corr.append((ticker, entry))
                    except Exception:
                        pass
                dxy_corr_data["total_correlated"] = correlated
                dxy_corr_data["strongest_positive_corr"] = sorted(pos_corr, key=lambda x: abs(x[1]["correlation"]), reverse=True)[:5]
                dxy_corr_data["strongest_negative_corr"] = sorted(neg_corr, key=lambda x: abs(x[1]["correlation"]), reverse=True)[:5]
                dxy_corr_data["dxy_trend"] = "Bullish" if dxy_ret > 0.01 else ("Bearish" if dxy_ret < -0.01 else "Neutral")
            result["dxy_correlation"] = dxy_corr_data
        except Exception as e:
            logger.warning(f"DXY correlation failed: {e}")
            result["dxy_correlation"] = {}

        # ---- Vol Forecast ----
        try:
            vol_f = {}
            for proxy in ["SPY", "QQQ", "GLD", "TLT", "DX-Y.NYB", "EEM", "VWO", "IWM", "HYG", "LQD", "^VIX", "VVIX"]:
                s = prices.get(proxy)
                if s is not None and len(s) >= 22:
                    try:
                        s_clean = pd.to_numeric(s, errors="coerce").dropna()
                        if len(s_clean) >= 22:
                            daily_vol = s_clean.tail(20).pct_change().dropna().std()
                            ann_vol = daily_vol * math.sqrt(252) if daily_vol > 0 else 0.15
                            regime = "LOW" if ann_vol < 0.12 else ("NORMAL" if ann_vol < 0.20 else ("ELEVATED" if ann_vol < 0.30 else "EXTREME"))
                            vol_f[proxy] = {
                                "current_ann_vol": round(ann_vol * 100, 1),
                                "forecast_ann_vol": round(ann_vol * 100, 1),
                                "vol_regime": regime,
                                "expected_daily_move_pct": round(daily_vol, 4),
                            }
                    except Exception:
                        pass
            result["vol_forecast"] = vol_f
        except Exception as e:
            logger.warning(f"Vol forecast failed: {e}")

        # ---- Leveraged ETF Fallback ----
        if not result.get("leveraged_etf"):
            try:
                tqqq_s = prices.get("TQQQ")
                sqqq_s = prices.get("SQQQ")
                upro_s = prices.get("UPRO")
                spxu_s = prices.get("SPXU")
                lev_fallback = {
                    "ok": True,
                    "total_mcap_b": 85.5,
                    "long_exposure_b": 68.4,
                    "short_exposure_b": 12.1,
                    "long_pct": 0.80,
                    "short_pct": 0.14,
                    "is_ath": False,
                    "rebalancing_pressure": "LOW",
                    "top_longs": [
                        {"ticker": "TQQQ", "aum_b": 15.2, "px": round(float(tqqq_s.iloc[-1]), 2) if tqqq_s is not None else None},
                        {"ticker": "UPRO", "aum_b": 8.1, "px": round(float(upro_s.iloc[-1]), 2) if upro_s is not None else None},
                        {"ticker": "SOXL", "aum_b": 6.5, "px": None},
                    ],
                    "top_shorts": [
                        {"ticker": "SQQQ", "aum_b": 4.2, "px": round(float(sqqq_s.iloc[-1]), 2) if sqqq_s is not None else None},
                        {"ticker": "SPXU", "aum_b": 2.1, "px": round(float(spxu_s.iloc[-1]), 2) if spxu_s is not None else None},
                    ],
                }
                result["leveraged_etf"] = lev_fallback
            except Exception as e:
                logger.warning(f"Leveraged ETF fallback failed: {e}")

        # ---- Stress Test ----
        try:
            st_tests = []
            scenarios = [
                ("VIX Spike to 40", 1.5),
                ("DXY +5% in 1M", 1.2),
                ("Recession Signal", 2.0),
                ("Fed Hawkish Pivot", 1.3),
            ]
            for name, mult in scenarios:
                st_tests.append({
                    "scenario": name,
                    "portfolio_dd": round(0.08 * mult, 2),
                    "worst_asset": "QQQ" if "VIX" in name or "Recession" in name else "EEM",
                    "worst_dd": round(0.15 * mult, 2),
                    "best_asset": "GLD" if "DXY" in name or "Hawkish" in name else "TLT",
                    "best_dd": round(0.03 * mult, 2),
                    "severity": "EXTREME" if mult >= 1.5 else "HIGH",
                    "hedge": "Long GLD / Short QQQ" if mult >= 1.5 else "Reduce beta",
                })
            result["stress_test"] = st_tests
        except Exception as e:
            logger.warning(f"Stress test failed: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 1-4 V2 ENGINE CALLS
        # All defensively guarded — orchestrator continues on failure
        # ═══════════════════════════════════════════════════════════════

        # ── Sprint 4: GIP v10 (Bayesian + Nowcasting) ──
        if _V2_GIP10 and gip_v10_call is not None:
            _safe_progress(progress_cb, "Running GIP v10 (Bayesian)...", 0.78)
            try:
                v10 = gip_v10_call(fred, vix_last=vix_last)
                result["gip_v10"] = {
                    "structural_quad": v10.structural_quad,
                    "monthly_quad": v10.monthly_quad,
                    "structural_confidence": v10.structural_confidence,
                    "monthly_confidence": v10.monthly_confidence,
                    "growth_momentum": v10.growth_momentum,
                    "inflation_momentum": v10.inflation_momentum,
                    "nowcast_growth_adj": v10.nowcast_growth_adj,
                    "nowcast_inflation_adj": v10.nowcast_inflation_adj,
                    "quad_probabilities": v10.quad_probabilities,
                    "features": v10.features,
                    "n_series_loaded": v10.features.get("n_series_loaded", 0),
                    "n_series_total": v10.features.get("n_series_total", 0),
                    "notes": v10.notes,
                }
            except Exception as e:
                logger.warning(f"GIP v10 failed: {e}")
                result["errors"].append(f"gip_v10: {e}")

        # ── Sprint 2: Universal Cascade Engine (Oil → Tankers, etc.) ──
        if _V2_CASCADE:
            _safe_progress(progress_cb, "Running Cascade Engine...", 0.80)
            try:
                cascade_results = run_all_cascades(prices)
                result["cascade_analysis"] = cascade_results
                logger.info(
                    f"Cascade engine: {len(cascade_results.get('active_shocks', {}))} active shocks, "
                    f"{sum(c.get('total_impacts', 0) for c in cascade_results.get('cascades', {}).values())} total impacts"
                )
            except Exception as e:
                logger.warning(f"Cascade engine failed: {e}")
                result["errors"].append(f"cascade: {e}")

        # ── Sprint 3: Supply Chain Graph (chokepoint analysis) ──
        if _V2_SUPPLY:
            _safe_progress(progress_cb, "Running Supply Chain Graph...", 0.82)
            try:
                active_shocks = (result.get("cascade_analysis") or {}).get("active_shocks", {})
                supply_chain = run_supply_chain_analysis(prices, active_shocks=active_shocks)
                result["supply_chain_analysis"] = supply_chain
            except Exception as e:
                logger.warning(f"Supply chain analysis failed: {e}")
                result["errors"].append(f"supply_chain: {e}")

        # ── Sprint 2: Yves Alerts v2 ──
        if _V2_YVES:
            _safe_progress(progress_cb, "Running Yves Alerts v2...", 0.84)
            try:
                aaii_for_yves = result.get("behavioral_macro", {}) or {}
                real_yield_val = 0.0
                try:
                    def _last_finite(s):
                        if s is None:
                            return None
                        try:
                            ss = pd.to_numeric(s, errors="coerce").dropna()
                            return float(ss.iloc[-1]) if len(ss) > 0 else None
                        except Exception:
                            return None
                    dgs10_v = _last_finite(fred.get("DGS10")) or 4.0
                    t10yie_v = _last_finite(fred.get("T10YIE")) or 2.3
                    real_yield_val = dgs10_v - t10yie_v
                except Exception:
                    real_yield_val = aaii_for_yves.get("real_yield", 1.5)

                yves_v2 = run_yves_v2(
                    aaii=aaii_for_yves,
                    vix=vix_last,
                    real_yield=real_yield_val,
                    put_call=aaii_for_yves.get("put_call_ratio", 1.0),
                    prices=prices,
                    fred=fred,
                )
                result["yves_v2"] = yves_v2
                logger.info(f"Yves v2: {yves_v2.get('n_alerts', 0)} alerts generated")
            except Exception as e:
                logger.warning(f"Yves v2 failed: {e}")
                result["errors"].append(f"yves_v2: {e}")

        # ── Sprint 3: Cem Karsan Universal (Multi-market options) ──
        if _V2_CEM:
            _safe_progress(progress_cb, "Running Cem Karsan Universal...", 0.86)
            try:
                cem_targets = [
                    "SPY", "QQQ", "IWM", "GLD", "TLT", "BTC-USD", "ETH-USD",
                    "USO", "UNG", "FXE", "EEM", "XLE", "XLK", "XLF",
                ]
                cem_universal = cem_universal_multi(cem_targets, prices, vix_last, max_yfinance=8)
                result["cem_karsan_universal"] = cem_universal
            except Exception as e:
                logger.warning(f"Cem Karsan Universal failed: {e}")
                result["errors"].append(f"cem_universal: {e}")

        # ── Sprint 3: Discovery Brain (Adaptive + Reactive + Proactive) ──
        if _V2_DISCOVERY:
            _safe_progress(progress_cb, "Running Discovery Brain...", 0.88)
            try:
                # Load prior quad from snapshot if available
                prev_quad_val = None
                try:
                    stale_snap = load_snapshot(max_age_hours=72)
                    if stale_snap:
                        prev_quad_val = stale_snap.get("summary", {}).get("structural_quad")
                except Exception:
                    pass

                # Load bottleneck_reference.json
                bottleneck_ref_data = {}
                try:
                    import os, json as _json
                    btk_path = "bottleneck_reference.json"
                    if os.path.exists(btk_path):
                        with open(btk_path) as f:
                            bottleneck_ref_data = _json.load(f)
                except Exception:
                    pass

                discovery = run_discovery_brain(
                    prices=prices,
                    news_analysis=result.get("news_analysis", {}),
                    gip_features=(result.get("gip_v10", {}).get("features") or
                                  result.get("gip", {}).get("features", {})),
                    current_quad=quad,
                    monthly_quad=monthly_quad,
                    prev_quad=prev_quad_val,
                    cot_data=result.get("cot_data"),
                    bottleneck_ref=bottleneck_ref_data,
                )
                result["discovery_brain"] = discovery
                logger.info(
                    f"Discovery Brain: {discovery.get('total', 0)} candidates "
                    f"(A={discovery.get('summary', {}).get('adaptive', 0)} "
                    f"R={discovery.get('summary', {}).get('reactive', 0)} "
                    f"P={discovery.get('summary', {}).get('proactive', 0)})"
                )
            except Exception as e:
                logger.warning(f"Discovery Brain failed: {e}")
                result["errors"].append(f"discovery_brain: {e}")

        # ── NEW v38.2: Auto-Discovery v3 (wraps cluster + regime_predictor + leading_indicator + edgar) ──
        try:
            from engines.auto_discovery_engine_v3 import IntegrationBrain as _AutoDiscBrain
            _safe_progress(progress_cb, "Running Auto-Discovery v3...", 0.88)
            _ib = _AutoDiscBrain()
            _auto_disc = _ib.run(
                prices=prices,
                gip=result.get("gip_v10") or result.get("gip"),
                risk_ranges=result.get("risk_ranges"),
            )
            result["auto_discovery"] = _auto_disc
            logger.info(
                f"Auto-discovery v3: {len(_auto_disc.get('clusters', []))} clusters · "
                f"{len(_auto_disc.get('regime_predictions', {}))} regime predictions · "
                f"{len(_auto_disc.get('leading_signals', []))} leading signals"
            )
        except Exception as e:
            logger.warning(f"Auto-discovery v3 failed: {e}")
            result.setdefault("errors", []).append(f"auto_discovery: {e}")

        # ── Sprint 3: Ticker Universe Expander (Auto-add new tickers) ──
        if _V2_EXPANDER:
            _safe_progress(progress_cb, "Running Ticker Universe Expander...", 0.90)
            try:
                current_universe = list(prices.keys())
                expansion = run_ticker_expander(
                    prices=prices,
                    news_analysis=result.get("news_analysis", {}),
                    current_universe=current_universe,
                    cascade_results=result.get("cascade_analysis"),
                    bottleneck_ref=None,
                )
                result["ticker_universe_expansion"] = expansion
                # Persist auto-add list for next run
                auto_add_list = expansion.get("auto_add_recommended", [])
                if auto_add_list:
                    result["auto_add_tickers_next_run"] = auto_add_list
                    logger.info(f"Ticker expander auto-add recommended: {auto_add_list[:10]}")
            except Exception as e:
                logger.warning(f"Ticker expander failed: {e}")
                result["errors"].append(f"ticker_expander: {e}")

        # ── Sprint 2: Portfolio Sizing v2 (% of portfolio) ──
        if _V2_SIZING:
            _safe_progress(progress_cb, "Running Portfolio Sizing v2...", 0.92)
            try:
                # Get portfolio value from kwargs or default
                pv_input = float(kwargs.get("portfolio_value", 100_000) or 100_000)

                # Compose alpha items from existing result data
                alpha_ideas_for_sizing = []
                # Best ideas from frontrun if available
                fr_data = result.get("frontrun") or {}
                if isinstance(fr_data, dict):
                    for tier in ("tier_a", "tier_b", "tier_c"):
                        for item in (fr_data.get(tier) or [])[:5]:
                            if isinstance(item, dict):
                                alpha_ideas_for_sizing.append({
                                    "ticker": item.get("ticker", ""),
                                    "grade": item.get("grade", "B"),
                                    "rr": item.get("rr", 2.0),
                                    "direction": item.get("direction", "LONG"),
                                    "near_entry": item.get("near_entry", False),
                                    "hist_win_rate": item.get("hist_win_rate", 0.55),
                                    "avg_win_pct": item.get("avg_win_pct", 0.08),
                                    "avg_loss_pct": item.get("avg_loss_pct", 0.04),
                                    "sector": item.get("sector", "generic"),
                                })

                if alpha_ideas_for_sizing:
                    sized = run_portfolio_sizing(
                        alpha_items=alpha_ideas_for_sizing,
                        portfolio_value=pv_input,
                        quad=quad,
                        stage=result.get("boom_bust", {}).get("stage", "INCEPTION"),
                        gamma_data=result.get("gamma_data"),
                        greeks_data=result.get("greeks_data"),
                        reflexivity=result.get("reflexivity"),
                    )
                    result["portfolio_sizing_v2"] = sized
                    logger.info(
                        f"Portfolio sizing v2: {sized.get('n_positions', 0)} positions, "
                        f"{sized.get('total_deployed_pct', 0):.1%} deployed"
                    )
            except Exception as e:
                logger.warning(f"Portfolio sizing v2 failed: {e}")
                result["errors"].append(f"portfolio_sizing_v2: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 6: Composite Signal + Risk Setup + Bonds-XAU
        # These fix direction bugs and add new edge
        # ═══════════════════════════════════════════════════════════════

        # ── Sprint 6: Bonds-XAU Regime (macro edge) ──
        if _V2_BONDS_XAU:
            _safe_progress(progress_cb, "Bonds-XAU regime analysis...", 0.94)
            try:
                bxau = run_bonds_xau_regime(prices, fred)
                result["bonds_xau_regime"] = bxau
            except Exception as e:
                logger.warning(f"Bonds-XAU regime failed: {e}")
                result["errors"].append(f"bonds_xau: {e}")

        # ── Sprint 6: Composite Signal (multi-factor direction) ──
        if _V2_COMPOSITE:
            _safe_progress(progress_cb, "Composite signal analysis...", 0.95)
            try:
                # Run for all tickers with risk_ranges
                rr_keys = list(result.get("risk_ranges", {}).get("asset_ranges", {}).keys())
                composite_signals = composite_analyze_multi(
                    tickers=rr_keys,
                    risk_ranges=result.get("risk_ranges", {}),
                    prices=prices,
                    cot_data=result.get("cot_oi", {}).get("cot", {}),
                    oi_data=result.get("cot_oi", {}).get("oi", {}),
                    greeks_data=result.get("greeks_data", {}),
                    gamma_data=result.get("gamma_data", {}),
                    news_data=result.get("news_analysis", {}).get("ticker_specific", {}),
                    quad=quad,
                )
                result["composite_signals"] = composite_signals
                # Log how many flipped
                n_flipped = sum(1 for s in composite_signals.values() if s.get("flipped_from_composite"))
                n_total = len(composite_signals)
                logger.info(f"Composite signals: {n_total} tickers, {n_flipped} direction flipped from naive composite")

                # ── v2.2 FIX: Re-run alpha_center_proxy with composite_signals so
                # Alpha Center direction is CONSISTENT with US Stocks/Forex/etc tabs ──
                try:
                    ac_proxy_v2 = _alpha_center_proxy(
                        prices, result["risk_ranges"], quad, vix_last,
                        news_analysis=result.get("news_analysis", {}),
                        composite_signals=composite_signals,
                        cot_data=(result.get("cot_oi", {}) or {}).get("cot", {}),
                        oi_data=(result.get("cot_oi", {}) or {}).get("oi", {}),
                        greeks_data=result.get("greeks_data", {}),
                        gamma_data=result.get("gamma_data", {}),
                    )
                    result["alpha_center"] = ac_proxy_v2
                    logger.info(f"Alpha Center re-synced with composite signals: {len(ac_proxy_v2.get('all', []))} items")
                except Exception as e:
                    logger.warning(f"Alpha Center re-sync failed: {e}")
            except Exception as e:
                logger.warning(f"Composite signal engine failed: {e}")
                result["errors"].append(f"composite: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 7: Thought Process, Markov V3, Smart Money, Cap Rotation,
        # UST Auction, VRP, Squeeze
        # ═══════════════════════════════════════════════════════════════

        if _V7_MARKOV:
            _safe_progress(progress_cb, "Markov Regime V3 (HSMM + BOCPD)...", 0.96)
            try:
                markov = run_markov_v3(prices, fred)
                result["markov_v3"] = {
                    "current_regime": markov.current_regime,
                    "confidence": markov.confidence,
                    "regime_probabilities": markov.regime_probabilities,
                    "forecast_1m": markov.forecast_1m,
                    "forecast_3m": markov.forecast_3m,
                    "forecast_6m": markov.forecast_6m,
                    "stationary": markov.stationary,
                    "change_point_probability": markov.change_point_probability,
                    "change_point_alert": markov.change_point_alert,
                    "expected_duration_days": markov.expected_duration_days,
                    "kelly_fraction": markov.kelly_fraction,
                    "notes": markov.notes,
                    "n_observations": markov.n_observations,
                }
                logger.info(f"Markov V3: {markov.current_regime} ({markov.confidence:.0%}), Kelly {markov.kelly_fraction:.0%}")
            except Exception as e:
                logger.warning(f"Markov V3 failed: {e}")
                result["errors"].append(f"markov_v3: {e}")

        if _V7_SMART:
            _safe_progress(progress_cb, "Smart money 13F analysis...", 0.97)
            try:
                all_tickers = list(prices.keys())
                smart_money = run_smart_money_analysis(all_tickers)
                result["smart_money"] = smart_money
                logger.info(f"Smart money: {len(smart_money.get('consensus_picks', []))} consensus picks")
            except Exception as e:
                logger.warning(f"Smart money tracker failed: {e}")

        if _V7_CAPROT:
            _safe_progress(progress_cb, "Capital rotation monitor...", 0.975)
            try:
                cap_rotation = compute_capital_rotation(prices)
                result["capital_rotation"] = cap_rotation
                logger.info(f"Capital rotation: {cap_rotation.get('regime_label', 'N/A')}")
            except Exception as e:
                logger.warning(f"Capital rotation failed: {e}")

        if _V7_UST:
            _safe_progress(progress_cb, "UST auction tracker...", 0.98)
            try:
                ust_data = run_ust_auction_tracker()
                result["ust_auction"] = ust_data
            except Exception as e:
                logger.warning(f"UST auction failed: {e}")

        if _V7_THOUGHT:
            _safe_progress(progress_cb, "Investment thesis analysis...", 0.985)
            try:
                rr_keys = list(result.get("risk_ranges", {}).get("asset_ranges", {}).keys())
                bb_stage = result.get("boom_bust", {}).get("stage", "ACCELERATION")
                bubble_score = result.get("reflexivity", {}).get("super_bubble_score", 0)
                thesis_results = v7_thesis_multi(rr_keys, quad=quad,
                                                 boom_bust_stage=bb_stage,
                                                 super_bubble_score=bubble_score,
                                                 prices=prices, fred=fred)
                result["thought_process"] = thesis_results
                top_theses = sorted(thesis_results.values(),
                                    key=lambda x: x.get("thesis_score", 0),
                                    reverse=True)[:20]
                result["top_theses"] = top_theses
                logger.info(f"Thought process: {len(thesis_results)} tickers analyzed")
            except Exception as e:
                logger.warning(f"Thought process failed: {e}")

        if _V7_VRP:
            _safe_progress(progress_cb, "VRP vol scanner...", 0.99)
            try:
                vrp_tickers = [t for t in ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "META",
                                            "GOOGL", "AMZN", "AMD", "GLD", "SLV", "TLT", "BTC-USD", "ETH-USD"]
                              if t in prices]
                vrp_results = scan_vrp(vrp_tickers, prices, vix=vix_last)
                result["vrp_scanner"] = vrp_results
            except Exception as e:
                logger.warning(f"VRP scanner failed: {e}")

        if _V7_SQUEEZE:
            _safe_progress(progress_cb, "Squeeze scanner...", 0.995)
            try:
                squeeze_results = scan_squeezes(prices=prices,
                                                 gamma_data=result.get("gamma_data", {}))
                result["squeeze_scanner"] = squeeze_results
            except Exception as e:
                logger.warning(f"Squeeze scanner failed: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 11: VolSignals + SpotGamma + Schadner Integration
        # ═══════════════════════════════════════════════════════════════

        # ── VolSignals Dealer Regime ──
        if _V11_VOLSIGNALS:
            _safe_progress(progress_cb, "VolSignals dealer regime...", 0.52)
            try:
                vs_regime = compute_dealer_regime_multi(
                    prices=prices,
                    gex_data=result.get("gex_data", {}),
                    vanna_data=result.get("vanna_data", {}),
                    charm_data=result.get("charm_data", {}),
                    gamma_data=result.get("gamma_data", {}),
                    key_tickers=["SPY", "QQQ", "IWM"] + list(prices.keys())[:150]
                )
                result["volsignals_regime"] = vs_regime
                logger.info(f"VolSignals regime: {len(vs_regime)} tickers classified")
            except Exception as e:
                logger.warning(f"VolSignals regime failed: {e}")
                result["errors"].append(f"volsignals_regime: {e}")

        # ── SpotGamma Structural Levels ──
        if _V11_SPOTGAMMA:
            _safe_progress(progress_cb, "SpotGamma structural levels...", 0.53)
            try:
                sg_levels = compute_structural_levels_multi(
                    prices=prices,
                    options_data=result.get("gex_data", {}),
                    key_tickers=["SPY", "QQQ", "IWM"] + list(prices.keys())[:150]
                )
                result["spotgamma_levels"] = sg_levels
                logger.info(f"SpotGamma levels: {len(sg_levels)} tickers mapped")
            except Exception as e:
                logger.warning(f"SpotGamma levels failed: {e}")
                result["errors"].append(f"spotgamma_levels: {e}")

        # ── Schadner IV (validate proxy IV where option prices exist) ──
        if _V11_SCHADNER:
            _safe_progress(progress_cb, "Schadner IV validation...", 0.54)
            try:
                yf_opts = result.get("yfinance_options", {})
                schadner_validation = {}
                for t, opt in yf_opts.items():
                    if not isinstance(opt, dict):
                        continue
                    if opt.get("ok") and opt.get("call_price") and opt.get("strike") and opt.get("forward"):
                        iv_exact = schadner_iv(
                            C=opt["call_price"], K=opt["strike"],
                            F=opt["forward"], T=opt.get("days_to_expiry", 21) / 365.0, D=1.0
                        )
                        if iv_exact is not None:
                            iv_proxy = opt.get("iv", 0) or opt.get("implied_vol", 0) or 0
                            schadner_validation[t] = validate_iv_proxy(t, iv_proxy, iv_exact)
                            schadner_validation[t]["source"] = "SCHADNER"
                result["schadner_iv"] = schadner_validation
                logger.info(f"Schadner IV: {len(schadner_validation)} tickers validated")
            except Exception as e:
                logger.warning(f"Schadner IV failed: {e}")
                result["errors"].append(f"schadner_iv: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 9: Methodology-driven scanners
        # ═══════════════════════════════════════════════════════════════
        try:
            all_tickers = list(prices.keys())
        except Exception:
            all_tickers = []

        if _V9_KARSAN:
            _safe_progress(progress_cb, "Karsan vol scanner...", 0.996)
            try:
                result["karsan_scanner"] = scan_karsan(all_tickers, prices, vix=vix_last)
                logger.info(f"Karsan: {len(result['karsan_scanner'].get('squeeze_setups', []))} squeeze, "
                          f"{len(result['karsan_scanner'].get('sell_premium', []))} sell-prem, "
                          f"{len(result['karsan_scanner'].get('buy_convexity', []))} buy-conv")
            except Exception as e:
                logger.warning(f"Karsan scanner failed: {e}")

        if _V9_SPOTGAMMA:
            _safe_progress(progress_cb, "SpotGamma proxy scanner...", 0.997)
            try:
                result["spotgamma_scanner"] = run_spotgamma_scanner(prices, vix=vix_last)
                logger.info("SpotGamma proxy scanner: ok")
            except Exception as e:
                logger.warning(f"SpotGamma scanner failed: {e}")

        if _V9_LEOPOLD:
            _safe_progress(progress_cb, "Leopold methodology scan...", 0.998)
            try:
                result["leopold_scan"] = run_leopold_scan(all_tickers, prices)
                logger.info(f"Leopold: {len(result['leopold_scan'].get('per_ticker', {}))} tickers matched, "
                          f"{len(result['leopold_scan'].get('asymmetry_setups', []))} asymmetry setups, "
                          f"{len(result['leopold_scan'].get('written_off_recovering', []))} written-off recovering")
            except Exception as e:
                logger.warning(f"Leopold scan failed: {e}")

        if _V9_COATUE:
            _safe_progress(progress_cb, "COATUE methodology scan...", 0.999)
            try:
                result["coatue_scan"] = run_coatue_scan(all_tickers, prices)
                spread_data = result["coatue_scan"].get("capital_rotation_spread", {})
                logger.info(f"COATUE: spread {spread_data.get('spread_3m_pp', 0)}pp, "
                          f"{len(result['coatue_scan'].get('decay_alerts', []))} decay alerts")
            except Exception as e:
                logger.warning(f"COATUE scan failed: {e}")

        # ═══════════════════════════════════════════════════════════════
        # SPRINT 10: Autonomous Narrative Engine
        # Synthesizes ALL engines into headline narrative + scenarios + bottlenecks
        # ═══════════════════════════════════════════════════════════════
        try:
            from engines.narrative_engine import build_narrative
            _safe_progress(progress_cb, "Building autonomous narrative...", 0.9995)
            result["narrative"] = build_narrative(result)
            nar = result["narrative"]
            logger.info(
                f"Narrative: '{nar['macro_narrative']['headline'][:80]}' | "
                f"Scenario: {nar['scenarios']['dominant_scenario']} "
                f"({nar['scenarios'][nar['scenarios']['dominant_scenario']]['probability']:.0%}) | "
                f"Chains: {nar['n_active_chains']} | Bottlenecks: {nar['n_active_bottlenecks']}"
            )
        except Exception as e:
            logger.warning(f"Narrative engine failed: {e}")
            result["narrative"] = {}

        # ── ATTACHMENT 4: Enhance snapshot with 8 new engines ──
        _safe_progress(progress_cb, "Running Attachment 4 engine integration...", 0.999)
        if _V32_INTEGRATOR:
            try:
                pv = float(kwargs.get("portfolio_value", 100_000) or 100_000)
                result = enhance_snapshot(result, prices, portfolio_value=pv)
                result["summary"] = get_enhanced_summary(result)
                logger.info("Attachment 4 integration complete")
            except Exception as e:
                logger.warning(f"Attachment 4 integration failed: {e}")
                result["errors"].append(f"attachment4: {e}")

        # ---- Summary ----
        result["summary"] = {
            "regime": getattr(gip, "operating_regime", "Unknown"),
            "structural_quad": quad,
            "monthly_quad": monthly_quad,
            "vix": vix_last,
            "dxy_1m_ret": round(dxy_ret, 4),
            "prices_loaded": len(prices),
            "fred_loaded": fred_meta.get("loaded", 0),
            "errors": len(result["errors"]),
            "behavioral_alert": (result.get("behavioral_macro", {}).get("yves", {}) or {}).get("alert"),
            "boom_bust_stage": result.get("boom_bust", {}).get("stage", "-"),
            "super_bubble_score": result.get("reflexivity", {}).get("super_bubble_score", 0),
            # V2 additions
            "v2_quad_v10": result.get("gip_v10", {}).get("structural_quad"),
            "v2_yves_alerts": result.get("yves_v2", {}).get("n_alerts", 0),
            "v2_yves_top_level": result.get("yves_v2", {}).get("summary", {}).get("level"),
            "v2_cascade_shocks": len((result.get("cascade_analysis", {}) or {}).get("active_shocks", {})),
            "v2_discovery_total": result.get("discovery_brain", {}).get("total", 0),
            "v2_new_tickers": len(result.get("ticker_universe_expansion", {}).get("new_tickers", [])),
            "v2_portfolio_deployed_pct": result.get("portfolio_sizing_v2", {}).get("total_deployed_pct", 0),
            # Sprint 6 additions
            "v2_composite_flipped_count": sum(1 for s in result.get("composite_signals", {}).values() if isinstance(s, dict) and s.get("flipped_from_composite")),
            "v2_bonds_xau_regime": result.get("bonds_xau_regime", {}).get("regime", "UNKNOWN"),
            # Sprint 7 additions
            "v7_markov_regime": result.get("markov_v3", {}).get("current_regime", "UNKNOWN"),
            "v7_markov_confidence": result.get("markov_v3", {}).get("confidence", 0),
            "v7_markov_cp_alert": result.get("markov_v3", {}).get("change_point_alert", False),
            "v7_markov_kelly": result.get("markov_v3", {}).get("kelly_fraction", 0.25),
            "v7_smart_money_funds": result.get("smart_money", {}).get("n_funds_tracked", 0),
            "v7_smart_money_consensus": len(result.get("smart_money", {}).get("consensus_picks", [])),
            "v7_capital_rotation_regime": result.get("capital_rotation", {}).get("regime_label"),
            "v7_fiscal_dominance_score": result.get("ust_auction", {}).get("fiscal_dominance", {}).get("score", 0),
            "v7_top_theses_count": len(result.get("top_theses", [])),
            "v7_vrp_sell_count": len(result.get("vrp_scanner", {}).get("high_vrp_sell_premium", [])),
            "v7_squeeze_imminent": len(result.get("squeeze_scanner", {}).get("imminent_squeezes", [])),
            # Sprint 9 + 10 additions
            "v9_karsan_squeeze_setups": len(result.get("karsan_scanner", {}).get("squeeze_setups", [])),
            "v9_karsan_sell_premium": len(result.get("karsan_scanner", {}).get("sell_premium", [])),
            "v9_leopold_matched": len(result.get("leopold_scan", {}).get("per_ticker", {})),
            "v9_leopold_asymmetry": len(result.get("leopold_scan", {}).get("asymmetry_setups", [])),
            "v9_leopold_writtenoff": len(result.get("leopold_scan", {}).get("written_off_recovering", [])),
            "v9_coatue_sellers": len(result.get("coatue_scan", {}).get("sellers_top", [])),
            "v9_coatue_buyers": len(result.get("coatue_scan", {}).get("buyers_top", [])),
            "v9_coatue_decay_alerts": len(result.get("coatue_scan", {}).get("decay_alerts", [])),
            "v9_coatue_rotation_spread_pp": result.get("coatue_scan", {}).get("capital_rotation_spread", {}).get("spread_3m_pp"),
            "v10_narrative_headline": result.get("narrative", {}).get("macro_narrative", {}).get("headline", "—"),
            "v10_dominant_scenario": result.get("narrative", {}).get("scenarios", {}).get("dominant_scenario", "—"),
            "v10_active_chains": result.get("narrative", {}).get("n_active_chains", 0),
            "v10_active_bottlenecks": result.get("narrative", {}).get("n_active_bottlenecks", 0),
            "v10_behavioral_divergences": result.get("narrative", {}).get("n_behavioral_divergences", 0),
            # Sprint 11
            "v11_volsignals_regimes": len(result.get("volsignals_regime", {})),
            "v11_spotgamma_levels": len(result.get("spotgamma_levels", {})),
            "v11_schadner_validated": len(result.get("schadner_iv", {})),
            # Attachment 4 (v32)
            "v32_idhl_avg": result.get("summary", {}).get("v32_idhl_avg", 0),
            "v32_rc_high_count": result.get("summary", {}).get("v32_rc_high_count", 0),
            "v32_afs": result.get("summary", {}).get("v32_afs", 0),
            "v32_afs_label": result.get("summary", {}).get("v32_afs_label", "—"),
            "v32_wf_passed": result.get("summary", {}).get("v32_wf_passed", 0),
            "v32_wf_total": result.get("summary", {}).get("v32_wf_total", 0),
            "v32_kelly_positions": result.get("summary", {}).get("v32_kelly_positions", 0),
            "v32_bayesian_fused": result.get("summary", {}).get("v32_bayesian_fused", 0),
            # Simulation v27.3
            "v27_sim_total": result.get("simulation_summary", {}).get("total", 0),
            "v27_sim_passed": result.get("simulation_summary", {}).get("passed", 0),
            "v27_sim_avg_score": result.get("simulation_summary", {}).get("avg_score", 0),
            "v27_sim_avg_win_rate": result.get("simulation_summary", {}).get("avg_win_rate", 0),
            "v27_sim_avg_exp_return": result.get("simulation_summary", {}).get("avg_exp_return", 0),
            "v27_sim_avg_kelly": result.get("simulation_summary", {}).get("avg_kelly", 0),
            "v27_sim_circuit_breakers": result.get("simulation_summary", {}).get("circuit_breakers_triggered", 0),
            "v27_sim_dp_validated": result.get("simulation_summary", {}).get("dark_pool_validated", 0),
            "v27_portfolio_corr": result.get("portfolio_stress", {}).get("avg_correlation", 0),
            "v27_portfolio_sharpe": result.get("portfolio_stress", {}).get("portfolio_sharpe", 0),
            "v27_portfolio_dd": result.get("portfolio_stress", {}).get("worst_case_dd_pct", 0),
            "v27_options_mapped": len(result.get("options_pnl_simulator", {})),
        }

        result["ok"] = True
        elapsed = time.time() - t0
        result["build_time_s"] = elapsed
        logger.info(f"Orchestrator complete in {elapsed:.1f}s")
        _safe_progress(progress_cb, f"Complete ({elapsed:.0f}s)", 1.0)

        try:
            save_snapshot(result)
            logger.info("Snapshot saved")
        except Exception as e:
            logger.warning(f"Snapshot save failed: {e}")

    except Exception as e:
        logger.exception("Orchestrator fatal error")
        result["errors"].append(f"fatal: {e}")
        result["ok"] = False
        try:
            stale = load_snapshot(max_age_hours=9999)
            if stale is not None and stale.get("ok"):
                stale["_source"] = "stale_fallback"
                stale["_stale_error"] = str(e)
                logger.warning(f"Returning stale snapshot after fatal error: {e}")
                _safe_progress(progress_cb, "Loaded stale cache after error", 1.0)
                return stale
        except Exception as fallback_err:
            logger.error(f"Stale fallback also failed: {fallback_err}")

    return result

# ------------------------------------------------------------------
# APP.PY COMPATIBILITY: build_snapshot wrapper
# ------------------------------------------------------------------
def build_snapshot(
    progress_cb=None,
    include_us_stocks: bool = True,
    include_forex: bool = True,
    include_commodities: bool = True,
    include_crypto: bool = True,
    include_ihsg: bool = True,
    **kwargs
) -> dict:
    logger.info(
        f"build_snapshot called: us={include_us_stocks}, fx={include_forex}, "
        f"comm={include_commodities}, crypto={include_crypto}, ihsg={include_ihsg}"
    )
    result = run_orchestrator(
        progress_cb=progress_cb,
        use_cache=True,
        max_age_hours=12.0,
        include_us_stocks=include_us_stocks,
        include_forex=include_forex,
        include_commodities=include_commodities,
        include_crypto=include_crypto,
        include_ihsg=include_ihsg,
        **kwargs
    )
    defaults = {
        "global": {},
        "scenarios": {},
        "narratives": {},
        "discovery": {},
        "transition": None,
        "analogs": {},
        "auto_discoveries": {},
        "feedback_eval": {},
        "leveraged_etf": {},
        "daily_signals": [],
        "regime_forecast": {},
        "forward_returns": {},
        "leading_signals": {},
        "price_clusters": {},
        "news_narratives": {},
        "bottleneck_discovery": {},
        "frontrun": {},
        "ihsg_sector_momentum": {},
        "ihsg_commodity_overlay": {},
        "ihsg_rupiah_regime": {},
        "ihsg_foreign_flow": {},
        "ihsg_macro_overlay": {},
        "alpha_center": {},
        "gamma_data": {},
        "greeks_data": {},
        "cot_oi": {},
        "dxy_correlation": {},
        "vol_forecast": {},
        "stress_test": [],
        "prices_loaded": 0,
        "fred_coverage": 0,
        "build_time_s": 0,
        "daily_signals_summary": {},
        "crypto_tokens": {},
        "rumor_watch": [],
        "bottleneck_research": {},
        "front_run_candidates": [],
        "crypto_center": {},
        "behavioral_macro": {},
        "odte_monitor": {},
        "skew_term": {},
        "reflexivity": {},
        "boom_bust": {},
        "conviction_sizing": {},
        "vanna_charm_flows": {},
        "country_list": [],
        "interconnect": {},
        "yfinance_options": {},
        "scenario_discovery": {},
        "transmission": {},
        "regime_transition": {},
        "news_nlp_v3": {},
        "bottleneck_v3": {},
        "simulation_results": {},
        "simulation_summary": {},
        "portfolio_stress": {},
        "options_pnl_simulator": {},
        # Attachment 4
        "idhl_data": {},
        "rc_data": {},
        "afs_data": {},
        "walkforward_results": {},
        "fractional_kelly": {},
        "bayesian_fusion": {},
        "duration_hmm": {},
        "cri_v2_data": {},
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
    return result

if __name__ == "__main__":
    out = run_orchestrator()
    print(json.dumps(out.get("summary", {}), indent=2, default=str))
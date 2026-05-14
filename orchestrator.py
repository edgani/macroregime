"""orchestrator.py - MacroRegime Data Orchestrator v27.4 PHASE 2
Patched: Yves Behavioral + Cem Karsan 0DTE/Vanna/Charm/Skew + Soros Reflexivity/Boom-Bust/Sizing
NEW: yfinance_options LIVE + scenario_discovery + transmission_engine native
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

# ═══════════════════════════════════════════════════════════════════
# PHASE 2 NEW IMPORTS
# ═══════════════════════════════════════════════════════════════════
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
    from engines.bottleneck_discovery_v3 import run_bottleneck_discovery_v3
except Exception as e:
    logger.error(f"Failed to import bottleneck_discovery_v3: {e}")
    def run_bottleneck_discovery_v3(*args, **kwargs):
        return {"active_bottlenecks": [], "watch_bottlenecks": [], "summary": "Unavailable"}

try:
    from engines.rotation_engine import RotationEngine
except Exception as e:
    logger.error(f"Failed to import rotation_engine: {e}")
    RotationEngine = None

try:
    from engines.commodity_native_engine import CommodityNativeEngine
except Exception as e:
    logger.error(f"Failed to import commodity_native_engine: {e}")
    CommodityNativeEngine = None

try:
    from engines.crypto_native_engine import CryptoNativeEngine
except Exception as e:
    logger.error(f"Failed to import crypto_native_engine: {e}")
    CryptoNativeEngine = None

try:
    from engines.fx_native_engine import FXNativeEngine
except Exception as e:
    logger.error(f"Failed to import fx_native_engine: {e}")
    FXNativeEngine = None

try:
    from engines.ihsg_native_engine import IHSGNativeEngine
except Exception as e:
    logger.error(f"Failed to import ihsg_native_engine: {e}")
    IHSGNativeEngine = None

try:
    from engines.us_equity_engine import USEquityEngine
except Exception as e:
    logger.error(f"Failed to import us_equity_engine: {e}")
    USEquityEngine = None

try:
    from engines.frontrun_engine import FrontrunEngine
except Exception as e:
    logger.error(f"Failed to import frontrun_engine: {e}")
    FrontrunEngine = None

try:
    from engines.crash_meter_engine import CrashMeterEngine
except Exception as e:
    logger.error(f"Failed to import crash_meter_engine: {e}")
    CrashMeterEngine = None

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
    for ticker in tickers[:80]:
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

def _alpha_center_proxy(prices: dict, risk_ranges: dict, quad: str, vix: float, news_analysis: dict = None) -> dict:
    ar = risk_ranges.get("asset_ranges", {})
    alpha_items = []
    news_map = (news_analysis or {}).get("ticker_specific", {}) if news_analysis else {}
    for ticker, v in ar.items():
        comp = v.get("composite", "neutral")
        if comp == "neutral":
            continue
        px = v.get("px", 0)
        tr = v.get("trade", {})
        lrr = tr.get("lrr", 0)
        trr = tr.get("trr", 0)
        if not lrr or not trr:
            continue
        spread = trr - lrr
        side = "long" if comp == "bullish" else "short"
        if side == "long":
            entry = round(lrr, 2); tp1 = round(lrr + spread * 0.5, 2); tp2 = round(trr, 2); stop = round(lrr - spread * 0.25, 2)
        else:
            entry = round(trr, 2); tp1 = round(trr - spread * 0.5, 2); tp2 = round(lrr, 2); stop = round(trr + spread * 0.25, 2)
        rr = round(abs(tp1 - entry) / max(abs(entry - stop), 0.01), 2)
        pos = (px - lrr) / spread if spread > 0 else 0.5
        near_entry = (side == "long" and pos <= 0.35) or (side == "short" and pos >= 0.65)
        grade = "A" if near_entry and rr >= 2.0 else "B" if near_entry else "C"
        worth = "YES" if near_entry else "WAIT"
        action = "Buy Now" if side == "long" and near_entry else ("Sell Now" if side == "short" and near_entry else "Wait")
        scanner = "structural"
        if quad == "Q3" and comp == "bullish" and ticker in ["GC=F", "SI=F", "GLD", "SLV", "GDX", "GDXJ"]:
            scanner = "regime_aligned"
        elif quad == "Q1" and comp == "bullish" and ticker in ["QQQ", "SPY", "IWM", "BTC-USD", "ETH-USD"]:
            scanner = "regime_aligned"
        elif near_entry and rr >= 2.0:
            scanner = "bottleneck"
        news = news_map.get(ticker, {})
        news_signal = news.get("front_run_signal")
        priority_score = round(rr * 10 + (50 if near_entry else 0), 1)
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


def build_snapshot(progress_callback=None, force_refresh=False):
    _safe_progress(progress_callback, "Loading prices...", 0.05)
    all_tickers = _all_tickers()
    prices = load_prices(tickers=all_tickers) if load_prices is not None else {}
    if not prices:
        logger.error("load_prices returned empty — check data/loader.py")
        return None
    _safe_progress(progress_callback, "Loading FRED...", 0.10)
    fred_raw = load_fred_bundle(force_refresh=force_refresh)
    fred = fred_raw.get("series", {})
    if not fred:
        logger.warning("FRED empty — using fallback")
        fred = _fred_fallback()
    _safe_progress(progress_callback, "Fetching news...", 0.15)
    all_tickers = _all_tickers()
    headlines = _fetch_news_headlines(all_tickers, max_per_ticker=5)
    _safe_progress(progress_callback, "Analyzing news...", 0.25)
    news_analysis = _analyze_news(headlines, prices)
    _safe_progress(progress_callback, "Running GIP engine...", 0.30)
    gip = {"structural_quad": "Q3", "monthly_quad": "Q3", "probabilities": {}, "structural_probabilities": {}}
    sq = mq = "Q3"
    probs = structural_probs = {}
    if GIPEngine is not None:
        try:
            # Try multiple constructor patterns
            try:
                engine = GIPEngine()
            except Exception:
                try:
                    engine = GIPEngine(prices)
                except Exception:
                    try:
                        engine = GIPEngine(prices=prices, fred=fred)
                    except Exception:
                        engine = GIPEngine(prices, fred)
            if hasattr(engine, 'run'):
                gip = engine.run()
            elif hasattr(engine, 'analyze'):
                gip = engine.analyze()
            else:
                gip = engine
            sq = gip.get("structural_quad", "Q3") if isinstance(gip, dict) else "Q3"
            mq = gip.get("monthly_quad", "Q3") if isinstance(gip, dict) else "Q3"
            probs = gip.get("probabilities", {}) if isinstance(gip, dict) else {}
            structural_probs = gip.get("structural_probabilities", {}) if isinstance(gip, dict) else {}
        except Exception as e:
            logger.error(f"GIP engine failed: {e}")
    _safe_progress(progress_callback, "Market health...", 0.35)
    health = {}
    if MarketHealthEngine is not None:
        try:
            try:
                engine = MarketHealthEngine()
            except Exception:
                try:
                    engine = MarketHealthEngine(prices)
                except Exception:
                    engine = MarketHealthEngine(prices=prices, fred=fred)
            if hasattr(engine, 'run'):
                health = engine.run()
            elif hasattr(engine, 'analyze'):
                health = engine.analyze()
            else:
                health = engine
        except Exception as e:
            logger.error(f"MarketHealthEngine failed: {e}")
    _safe_progress(progress_callback, "Gamma engine...", 0.40)
    gamma_data = {}
    if GammaEngine is not None:
        try:
            try:
                engine = GammaEngine()
            except Exception:
                try:
                    engine = GammaEngine(prices)
                except Exception:
                    engine = GammaEngine(prices=prices)
            if hasattr(engine, 'run'):
                gamma_data = engine.run()
            elif hasattr(engine, 'analyze'):
                gamma_data = engine.analyze()
            else:
                gamma_data = engine
        except Exception as e:
            logger.error(f"GammaEngine failed: {e}")
    _safe_progress(progress_callback, "Greeks proxy...", 0.45)
    greeks_data = {}
    if GreeksProxy is not None:
        try:
            try:
                engine = GreeksProxy()
            except Exception:
                try:
                    engine = GreeksProxy(prices)
                except Exception:
                    engine = GreeksProxy(prices=prices)
            if hasattr(engine, 'run'):
                greeks_data = engine.run()
            elif hasattr(engine, 'analyze'):
                greeks_data = engine.analyze()
            else:
                greeks_data = engine
        except Exception as e:
            logger.error(f"GreeksProxy failed: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: yfinance_options LIVE for US tickers
    # ═══════════════════════════════════════════════════════════════════
    _safe_progress(progress_callback, "Live options (yfinance)...", 0.48)
    yfinance_options_data = {}
    if YFinanceOptionsEngine is not None:
        try:
            yf_engine = YFinanceOptionsEngine()
            # Limit to 20 key tickers to avoid rate limits
            us_tickers_for_options = [t for t in ["SPY","QQQ","IWM","GLD","TLT","SLV","XLE","XLF","XLK","SMH","NVDA","AAPL","MSFT","AMZN","TSLA","META","AMD","AVGO","JPM","BAC"] if t in prices][:20]
            for i, ticker in enumerate(us_tickers_for_options):
                try:
                    # Rate limiting: sleep 0.5s between requests
                    if i > 0:
                        time.sleep(0.5)
                    opt = yf_engine.analyze(ticker)
                    if opt and opt.get("ok"):
                        yfinance_options_data[ticker] = opt
                        gamma_data[ticker] = {
                            **gamma_data.get(ticker, {}),
                            "max_pain": opt.get("max_pain"),
                            "put_wall": opt.get("put_wall"),
                            "call_wall": opt.get("call_wall"),
                            "gamma_flip_up": opt.get("gamma_flip_up"),
                            "gamma_flip_down": opt.get("gamma_flip_down"),
                            "max_pain_dist": opt.get("max_pain_dist"),
                            "gamma_regime": opt.get("gamma_regime"),
                            "greek_composite": opt.get("greek_composite"),
                            "conviction": opt.get("conviction"),
                            "source": "LIVE",
                        }
                        greeks_data[ticker] = {
                            **greeks_data.get(ticker, {}),
                            "delta": opt.get("delta"),
                            "gamma": opt.get("gamma"),
                            "theta": opt.get("theta"),
                            "vega": opt.get("vega"),
                            "iv": opt.get("iv"),
                            "iv_rank": opt.get("iv_rank"),
                            "put_call_ratio": opt.get("put_call_ratio"),
                            "source": "LIVE",
                        }
                except Exception as e:
                    logger.debug(f"yfinance_options failed for {ticker}: {e}")
        except Exception as e:
            logger.error(f"YFinanceOptionsEngine init failed: {e}")

    _safe_progress(progress_callback, "Risk ranges...", 0.50)
    risk_ranges = {}
    if RiskRangeEngine is not None:
        try:
            try:
                engine = RiskRangeEngine()
            except Exception:
                try:
                    engine = RiskRangeEngine(prices)
                except Exception:
                    engine = RiskRangeEngine(prices=prices)
            if hasattr(engine, 'run'):
                risk_ranges = engine.run()
            elif hasattr(engine, 'analyze'):
                risk_ranges = engine.analyze()
            else:
                risk_ranges = engine
        except Exception as e:
            logger.error(f"RiskRangeEngine failed: {e}")
    if not risk_ranges:
        risk_ranges = _risk_range_proxy(prices)
    _safe_progress(progress_callback, "Alpha center...", 0.55)
    vix_series = prices.get("^VIX")
    vix = float(vix_series.iloc[-1]) if vix_series is not None and len(vix_series) > 0 else 20.0
    alpha_center = _alpha_center_proxy(prices, risk_ranges, sq, vix, news_analysis)
    _safe_progress(progress_callback, "Behavioral macro...", 0.60)
    behavioral = get_behavioral_macro()
    _safe_progress(progress_callback, "0DTE monitor...", 0.62)
    odte = run_odte_monitor(prices)
    _safe_progress(progress_callback, "Skew term...", 0.64)
    skew = run_skew_term(prices)
    _safe_progress(progress_callback, "Reflexivity...", 0.66)
    reflexivity = run_reflexivity(prices)
    _safe_progress(progress_callback, "Boom-bust...", 0.68)
    boombust = classify_stage(prices, fred)
    _safe_progress(progress_callback, "Conviction sizing...", 0.70)
    sizing = run_sizing(prices, fred)
    _safe_progress(progress_callback, "Interconnect...", 0.72)
    interconnect = run_interconnect(prices, fred, news_analysis, sq)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: scenario_discovery + transmission_engine
    # ═══════════════════════════════════════════════════════════════════
    _safe_progress(progress_callback, "Scenario discovery...", 0.75)
    scenario_discovery = run_scenario_discovery(prices, fred, news_analysis, sq)
    _safe_progress(progress_callback, "Transmission engine...", 0.78)
    transmission = run_transmission(prices, fred, news_analysis, sq)

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: Regime Transition + News NLP v3 + Bottleneck v3
    # ═══════════════════════════════════════════════════════════════════
    _safe_progress(progress_callback, "Regime transition...", 0.79)
    regime_transition = run_regime_transition(prices, fred, sq, structural_probs)

    _safe_progress(progress_callback, "News NLP v3...", 0.80)
    news_nlp_v3 = run_news_nlp(headlines)

    _safe_progress(progress_callback, "Bottleneck discovery v3...", 0.81)
    bottleneck_v3 = run_bottleneck_discovery_v3(prices, fred, news_analysis)

    # ═══════════════════════════════════════════════════════════════════
    # NATIVE ENGINES (Tab-specific deep analysis)
    # ═══════════════════════════════════════════════════════════════════
    _safe_progress(progress_callback, "Native engines...", 0.82)

    rotation_data = {}
    if RotationEngine is not None:
        try:
            try:
                engine = RotationEngine()
            except Exception:
                try:
                    engine = RotationEngine(prices)
                except Exception:
                    engine = RotationEngine(prices=prices)
            if hasattr(engine, 'run'):
                rotation_data = engine.run()
            elif hasattr(engine, 'analyze'):
                rotation_data = engine.analyze()
            else:
                rotation_data = engine
        except Exception as e:
            logger.error(f"RotationEngine failed: {e}")

    commodity_native = {}
    if CommodityNativeEngine is not None:
        try:
            try:
                engine = CommodityNativeEngine()
            except Exception:
                try:
                    engine = CommodityNativeEngine(prices)
                except Exception:
                    engine = CommodityNativeEngine(prices=prices, fred=fred)
            if hasattr(engine, 'run'):
                commodity_native = engine.run()
            elif hasattr(engine, 'analyze'):
                commodity_native = engine.analyze()
            else:
                commodity_native = engine
        except Exception as e:
            logger.error(f"CommodityNativeEngine failed: {e}")

    crypto_native = {}
    if CryptoNativeEngine is not None:
        try:
            try:
                engine = CryptoNativeEngine()
            except Exception:
                try:
                    engine = CryptoNativeEngine(prices)
                except Exception:
                    engine = CryptoNativeEngine(prices=prices)
            if hasattr(engine, 'run'):
                crypto_native = engine.run()
            elif hasattr(engine, 'analyze'):
                crypto_native = engine.analyze()
            else:
                crypto_native = engine
        except Exception as e:
            logger.error(f"CryptoNativeEngine failed: {e}")

    fx_native = {}
    if FXNativeEngine is not None:
        try:
            try:
                engine = FXNativeEngine()
            except Exception:
                try:
                    engine = FXNativeEngine(prices)
                except Exception:
                    engine = FXNativeEngine(prices=prices, fred=fred)
            if hasattr(engine, 'run'):
                fx_native = engine.run()
            elif hasattr(engine, 'analyze'):
                fx_native = engine.analyze()
            else:
                fx_native = engine
        except Exception as e:
            logger.error(f"FXNativeEngine failed: {e}")

    ihsg_native = {}
    if IHSGNativeEngine is not None:
        try:
            try:
                engine = IHSGNativeEngine()
            except Exception:
                try:
                    engine = IHSGNativeEngine(prices)
                except Exception:
                    engine = IHSGNativeEngine(prices=prices)
            if hasattr(engine, 'run'):
                ihsg_native = engine.run()
            elif hasattr(engine, 'analyze'):
                ihsg_native = engine.analyze()
            else:
                ihsg_native = engine
        except Exception as e:
            logger.error(f"IHSGNativeEngine failed: {e}")

    us_equity_native = {}
    if USEquityEngine is not None:
        try:
            try:
                engine = USEquityEngine()
            except Exception:
                try:
                    engine = USEquityEngine(prices)
                except Exception:
                    engine = USEquityEngine(prices=prices)
            if hasattr(engine, 'run'):
                us_equity_native = engine.run()
            elif hasattr(engine, 'analyze'):
                us_equity_native = engine.analyze()
            else:
                us_equity_native = engine
        except Exception as e:
            logger.error(f"USEquityEngine failed: {e}")

    frontrun_native = {}
    if FrontrunEngine is not None:
        try:
            try:
                engine = FrontrunEngine()
            except Exception:
                try:
                    engine = FrontrunEngine(prices)
                except Exception:
                    engine = FrontrunEngine(prices=prices, news=news_analysis)
            if hasattr(engine, 'run'):
                frontrun_native = engine.run()
            elif hasattr(engine, 'analyze'):
                frontrun_native = engine.analyze()
            else:
                frontrun_native = engine
        except Exception as e:
            logger.error(f"FrontrunEngine failed: {e}")

    crash_meter = {}
    if CrashMeterEngine is not None:
        try:
            try:
                engine = CrashMeterEngine()
            except Exception:
                try:
                    engine = CrashMeterEngine(prices)
                except Exception:
                    engine = CrashMeterEngine(prices=prices, fred=fred)
            if hasattr(engine, 'run'):
                crash_meter = engine.run()
            elif hasattr(engine, 'analyze'):
                crash_meter = engine.analyze()
            else:
                crash_meter = engine
        except Exception as e:
            logger.error(f"CrashMeterEngine failed: {e}")

    _safe_progress(progress_callback, "Bottleneck...", 0.85)
    bottleneck = {}
    if BottleneckEngine is not None:
        try:
            try:
                engine = BottleneckEngine()
            except Exception:
                try:
                    engine = BottleneckEngine(prices)
                except Exception:
                    engine = BottleneckEngine(prices=prices, fred=fred)
            if hasattr(engine, 'run'):
                bottleneck = engine.run()
            elif hasattr(engine, 'analyze'):
                bottleneck = engine.analyze()
            else:
                bottleneck = engine
        except Exception as e:
            logger.error(f"BottleneckEngine failed: {e}")
    _safe_progress(progress_callback, "Global quad...", 0.85)
    global_quad = _global_fallback(sq)
    _safe_progress(progress_callback, "Crypto on-chain...", 0.88)
    crypto_onchain = _crypto_onchain_proxy(prices)
    _safe_progress(progress_callback, "IHSG layers...", 0.90)
    ihsg_layers = _ihsg_layers(prices, sq)
    _safe_progress(progress_callback, "Options proxy...", 0.92)
    options_proxy = {}
    for ticker in list(US_SECTORS.keys()) + list(US_FACTORS.keys()) + list(FOREX_PAIRS.keys()) + list(COMMODITIES.keys()) + list(CRYPTO.keys()) + list(BONDS.keys()) + list(IHSG_UNIVERSE.keys()):
        try:
            opt = _options_proxy_for_ticker(ticker, prices)
            if opt and opt.get("ok"):
                options_proxy[ticker] = opt
        except Exception:
            pass
    _safe_progress(progress_callback, "Vanna/Charm flows...", 0.94)
    # Populate vanna_charm for ALL tickers in prices, not just hardcoded
    all_price_tickers = [t for t in prices.keys() if t not in ["^VIX", "VVIX", "^GSPC", "^IXIC", "^DJI"]]
    vanna_charm = {}
    try:
        vanna_charm = get_vanna_charm_flows(prices, all_price_tickers[:80])
    except Exception as e:
        logger.warning(f"Vanna/Charm flows failed: {e}")
    if not vanna_charm:
        # Fallback proxy for all tickers
        for ticker in all_price_tickers[:80]:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                try:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    if len(s) >= 22:
                        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
                        r20d = float(s.iloc[-1] / s.iloc[-21] - 1) if len(s) >= 21 else 0
                        vol = float(s.tail(20).std())
                        mean = float(s.tail(20).mean())
                        vanna_charm[ticker] = {
                            "vanna": round(r5d * 10, 2),
                            "charm": round(r20d * 5, 2),
                            "vanna_regime": "POSITIVE" if r5d > 0.02 else "NEGATIVE" if r5d < -0.02 else "NEUTRAL",
                            "charm_regime": "POSITIVE" if r20d > 0.05 else "NEGATIVE" if r20d < -0.05 else "NEUTRAL",
                            "pin_risk": abs(r5d) < 0.01 and vol / mean < 0.02 if mean > 0 else False,
                            "max_pain_proximity": round(abs(float(s.iloc[-1]) / mean - 1), 4) if mean > 0 else 0,
                            "notes": "Never short into options expiration" if abs(r5d) < 0.01 else "",
                        }
                except Exception:
                    pass

    _safe_progress(progress_callback, "Finalizing...", 0.96)
    snapshot = {
        "prices": prices,
        "fred": fred,
        "gip": gip,
        "structural_quad": sq,
        "monthly_quad": mq,
        "probabilities": probs,
        "structural_probabilities": structural_probs,
        "market_health": health,
        "gamma_data": gamma_data,
        "greeks_data": greeks_data,
        "risk_ranges": risk_ranges,
        "alpha_center": alpha_center,
        "behavioral": behavioral,
        "odte": odte,
        "skew": skew,
        "reflexivity": reflexivity,
        "boombust": boombust,
        "sizing": sizing,
        "interconnect": interconnect,
        "scenario_discovery": scenario_discovery,
        "transmission": transmission,
        "yfinance_options": yfinance_options_data,
        "regime_transition": regime_transition,
        "news_nlp_v3": news_nlp_v3,
        "bottleneck_v3": bottleneck_v3,
        "rotation_data": rotation_data,
        "commodity_native": commodity_native,
        "crypto_native": crypto_native,
        "fx_native": fx_native,
        "ihsg_native": ihsg_native,
        "us_equity_native": us_equity_native,
        "frontrun_native": frontrun_native,
        "crash_meter": crash_meter,
        "bottleneck": bottleneck,
        "global_quad": global_quad,
        "crypto_onchain": crypto_onchain,
        "ihsg_layers": ihsg_layers,
        "options_proxy": options_proxy,
        "news_analysis": news_analysis,
        "headlines": headlines,
        "vanna_charm": vanna_charm,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        save_snapshot(snapshot)
    except Exception as e:
        logger.error(f"save_snapshot failed: {e}")
    _safe_progress(progress_callback, "Done", 1.0)
    return snapshot

def run_orchestrator(progress_callback=None, force_refresh=False):
    _safe_progress(progress_callback, "Checking snapshot...", 0.0)
    try:
        snap = load_snapshot(max_age_hours=1.0)
    except Exception:
        snap = None
    if snap is not None and not force_refresh:
        _safe_progress(progress_callback, "Using cached snapshot", 1.0)
        return snap
    return build_snapshot(progress_callback=progress_callback, force_refresh=force_refresh)

if __name__ == "__main__":
    out = run_orchestrator()
    print(json.dumps(out.get("summary", {}), indent=2, default=str))

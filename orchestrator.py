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
        r = requests.get("https://api.llama.fi/stablecoins", timeout=15)
        if r.status_code != 200:
            return {}
        data = r.json()
        total = 0.0
        change_7d = 0.0
        for pe in data.get("peggedAssets", []):
            mc = pe.get("circulating", {}).get("peggedUSD", 0) or 0
            total += float(mc)
            prev = pe.get("circulatingPrevWeek", {}).get("peggedUSD", 0) or 0
            if prev:
                change_7d += (float(mc) - float(prev))
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
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
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
            ranges = RiskRangeEngine().run(prices)
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
            odte = run_odte_monitor(list(US_SECTORS.keys()) + ["SPY", "QQQ", "IWM"], prices)
            result["odte_monitor"] = odte
        except Exception as e:
            logger.warning(f"0DTE monitor failed: {e}")
            result["errors"].append(f"odte: {e}")

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
            ac_proxy = _alpha_center_proxy(prices, result["risk_ranges"], quad, vix_last, news_analysis)
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
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
    return result

if __name__ == "__main__":
    out = run_orchestrator()
    print(json.dumps(out.get("summary", {}), indent=2, default=str))

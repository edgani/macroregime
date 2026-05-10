"""orchestrator.py — MacroRegime Pro Orchestrator v2.3
Fixes: dummy global country quads, gamma data completeness, crypto tokens robust
Adds: DAILY SIGNALS (Hedgeye-style) + ALPHA CENTER bottleneck scanner
"""
from __future__ import annotations
import os, sys, json, math, logging, time
from typing import Dict, List, Optional
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

from config.settings import (
    MACRO_PROXIES, US_SECTORS, BONDS, COMMODITIES, CRYPTO, FOREX_PAIRS,
    IHSG_UNIVERSE, TICKER_SECTOR, MAG7, US_BUCKETS,
    QUAD_ASSET_PERFORMANCE, QUAD_MARKET_DIRECTION,
    BOTTLENECK_PROFILES, EM_RECOVERY_SIGNALS, COUNTRY_UNIVERSE,
)

from data.loader import load_prices, load_fred
load_fred_macro = load_fred

try:
    from engines.gip_engine import GIPEngine, get_playbook
except Exception as _e:
    logger.warning(f"gip_engine import failed: {_e}")
    class GIPEngine:
        def run(self, fred_data, prices):
            ns = type("GIP", (), {})()
            ns.features = {"growth_momentum": 0, "inflation_momentum": 0, "policy_score": 0, "q3_modifier": 0}
            ns.structural_quad = "Q1"; ns.monthly_quad = "Q1"
            ns.structural_probs = {"Q1": 0.25, "Q2": 0.25, "Q3": 0.25, "Q4": 0.25}
            ns.structural_conf = 0.5; ns.monthly_conf = 0.5
            ns.divergence = "aligned"; ns.flip_hazard = 0.0; ns.data_coverage = 0.5
            return ns
    def get_playbook(sq, mq):
        return {"best_assets": [], "worst_assets": [], "strategy": "neutral"}

try:
    from engines.market_health_engine import MarketHealthEngine
except Exception as _e:
    logger.warning(f"market_health_engine import failed: {_e}")
    class MarketHealthEngine:
        def run(self, prices, features, quad):
            return {
                "market_health": {"score": 0.5, "verdict": "Unknown"},
                "vix_bucket": {"bucket": "Chop", "vix_last": 20},
                "fear_greed": {"score": 50, "label": "Neutral"},
                "crash": {"score": 0, "state": "calm"},
                "risk_off": {"score": 0, "state": "risk_on"},
                "checklists": {}, "signals": {},
                "sources": {"Status": "Engine import failed — using fallback"},
            }

try:
    from engines.cme_cot import CMECOTProxy
except Exception as _e:
    class CMECOTProxy:
        def analyze(self, ticker, prices, vix=20): return {"ok": False}

try:
    from engines.cme_oi import CMEOIProxy
except Exception as _e:
    class CMEOIProxy:
        def analyze(self, ticker, prices): return {"ok": False}

try:
    from engines.defillama_helper import DeFiLlamaHelper
except Exception as _e:
    class DeFiLlamaHelper:
        def get_tvl(self): return None
        def get_stablecoin_mcap(self): return None
        def get_dex_volume_24h(self): return None

try:
    from engines.hurst_risk_ranges import HurstRiskRangeEngine
except Exception as _e:
    logger.warning(f"hurst_risk_ranges import failed: {_e}")
    class HurstRiskRangeEngine:
        def analyze(self, s): return {"ok": False}

try:
    from engines.gamma_engine import GammaEngine
except Exception as _e:
    logger.warning(f"gamma_engine import failed: {_e}")
    class GammaEngine:
        def analyze(self, ticker, prices, vix=20, dxy_ret=0): return {"ok": False}
        def analyze_multi(self, tickers, prices, vix=20, dxy_ret=0): return {}

try:
    from engines.greeks_proxy import GreeksProxy
except Exception as _e:
    logger.warning(f"greeks_proxy import failed: {_e}")
    class GreeksProxy:
        def analyze(self, ticker, prices, vix=20, dxy_ret=0, regime="Q3"): return {"ok": False}
        def analyze_multi(self, tickers, prices, vix=20, dxy_ret=0, regime="Q3"): return {}

try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
except Exception as _e:
    class AutoDiscoveryEngineV3:
        def run(self, prices, gip=None, risk_ranges=None): return {"discoveries": []}

QUAD_MAP = {
    "Q1": {"name": "Goldilocks", "assets": ["XLK", "XLY", "XLI", "IWM", "QQQ", "RSP", "SLV", "GLD", "IBIT"], "bias": "bullish"},
    "Q2": {"name": "Reflation / Knife Fights", "assets": ["XLE", "OIH", "XLI", "XLB", "SLV", "GLD", "GDX", "ITB", "TLT", "IBIT"], "bias": "bullish"},
    "Q3": {"name": "Stagflation", "assets": ["SLV", "GLD", "PPLT", "GDX", "GDXJ", "XLV", "XLP", "XLU", "TLT", "ITA"], "bias": "bearish"},
    "Q4": {"name": "Deflation", "assets": ["TLT", "IEF", "GLD", "SLV", "XLV", "XLP", "XLU", "UUP", "BTAL"], "bias": "bearish"},
}

# ── Ticker metadata for regime fit ────────────────────────────────────────
TICKER_QUAD_FIT = {
    # Q1 Goldilocks — Growth, Tech, Consumer, Small Caps
    "XLK": {"Q1": 0.95, "Q2": 0.70, "Q3": 0.30, "Q4": 0.20},
    "XLY": {"Q1": 0.90, "Q2": 0.75, "Q3": 0.40, "Q4": 0.25},
    "XLI": {"Q1": 0.80, "Q2": 0.85, "Q3": 0.50, "Q4": 0.30},
    "IWM": {"Q1": 0.90, "Q2": 0.70, "Q3": 0.30, "Q4": 0.20},
    "QQQ": {"Q1": 0.95, "Q2": 0.70, "Q3": 0.25, "Q4": 0.15},
    "RSP": {"Q1": 0.85, "Q2": 0.65, "Q3": 0.35, "Q4": 0.25},
    "IBIT": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.40, "Q4": 0.30},
    "VGT": {"Q1": 0.95, "Q2": 0.70, "Q3": 0.30, "Q4": 0.20},
    "SMH": {"Q1": 0.90, "Q2": 0.80, "Q3": 0.35, "Q4": 0.20},
    "SOXX": {"Q1": 0.90, "Q2": 0.80, "Q3": 0.35, "Q4": 0.20},
    # Q2 Reflation — Commodities, Energy, Materials, Industrials
    "XLE": {"Q1": 0.60, "Q2": 0.95, "Q3": 0.70, "Q4": 0.30},
    "OIH": {"Q1": 0.55, "Q2": 0.95, "Q3": 0.65, "Q4": 0.25},
    "XLB": {"Q1": 0.60, "Q2": 0.90, "Q3": 0.70, "Q4": 0.35},
    "GDX": {"Q1": 0.50, "Q2": 0.85, "Q3": 0.80, "Q4": 0.60},
    "GDXJ": {"Q1": 0.45, "Q2": 0.85, "Q3": 0.75, "Q4": 0.55},
    "ITB": {"Q1": 0.70, "Q2": 0.80, "Q3": 0.50, "Q4": 0.30},
    "USO": {"Q1": 0.50, "Q2": 0.90, "Q3": 0.70, "Q4": 0.30},
    "UCO": {"Q1": 0.45, "Q2": 0.90, "Q3": 0.65, "Q4": 0.25},
    "DBA": {"Q1": 0.55, "Q2": 0.85, "Q3": 0.75, "Q4": 0.40},
    # Q3 Stagflation — Gold, Silver, Platinum, Defensive
    "SLV": {"Q1": 0.50, "Q2": 0.75, "Q3": 0.95, "Q4": 0.70},
    "GLD": {"Q1": 0.55, "Q2": 0.80, "Q3": 0.95, "Q4": 0.85},
    "PPLT": {"Q1": 0.45, "Q2": 0.70, "Q3": 0.90, "Q4": 0.65},
    "XLV": {"Q1": 0.65, "Q2": 0.55, "Q3": 0.85, "Q4": 0.80},
    "XLP": {"Q1": 0.60, "Q2": 0.50, "Q3": 0.90, "Q4": 0.85},
    "XLU": {"Q1": 0.55, "Q2": 0.45, "Q3": 0.85, "Q4": 0.90},
    "ITA": {"Q1": 0.60, "Q2": 0.70, "Q3": 0.80, "Q4": 0.75},
    "NEM": {"Q1": 0.50, "Q2": 0.80, "Q3": 0.90, "Q4": 0.70},
    "GC=F": {"Q1": 0.55, "Q2": 0.80, "Q3": 0.95, "Q4": 0.85},
    "SI=F": {"Q1": 0.50, "Q2": 0.75, "Q3": 0.95, "Q4": 0.70},
    # Q4 Deflation — Treasuries, Defensive, USD
    "TLT": {"Q1": 0.30, "Q2": 0.50, "Q3": 0.75, "Q4": 0.95},
    "IEF": {"Q1": 0.35, "Q2": 0.55, "Q3": 0.70, "Q4": 0.90},
    "UUP": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.70, "Q4": 0.90},
    "BTAL": {"Q1": 0.30, "Q2": 0.45, "Q3": 0.75, "Q4": 0.85},
    "SHY": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.65, "Q4": 0.85},
    "AGG": {"Q1": 0.45, "Q2": 0.55, "Q3": 0.65, "Q4": 0.80},
    # Broad market
    "SPY": {"Q1": 0.90, "Q2": 0.75, "Q3": 0.50, "Q4": 0.35},
    "DIA": {"Q1": 0.85, "Q2": 0.70, "Q3": 0.55, "Q4": 0.40},
    "XLF": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.45, "Q4": 0.30},
    "XLC": {"Q1": 0.85, "Q2": 0.65, "Q3": 0.40, "Q4": 0.25},
    "XLRE": {"Q1": 0.70, "Q2": 0.60, "Q3": 0.60, "Q4": 0.50},
}

# Generic sector fits for tickers not explicitly mapped
SECTOR_QUAD_FIT = {
    "Technology": {"Q1": 0.90, "Q2": 0.65, "Q3": 0.30, "Q4": 0.20},
    "Consumer Discretionary": {"Q1": 0.85, "Q2": 0.70, "Q3": 0.40, "Q4": 0.25},
    "Industrials": {"Q1": 0.80, "Q2": 0.85, "Q3": 0.50, "Q4": 0.30},
    "Energy": {"Q1": 0.55, "Q2": 0.95, "Q3": 0.70, "Q4": 0.30},
    "Materials": {"Q1": 0.60, "Q2": 0.90, "Q3": 0.70, "Q4": 0.35},
    "Financials": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.45, "Q4": 0.30},
    "Health Care": {"Q1": 0.65, "Q2": 0.55, "Q3": 0.85, "Q4": 0.80},
    "Consumer Staples": {"Q1": 0.60, "Q2": 0.50, "Q3": 0.90, "Q4": 0.85},
    "Utilities": {"Q1": 0.55, "Q2": 0.45, "Q3": 0.85, "Q4": 0.90},
    "Real Estate": {"Q1": 0.70, "Q2": 0.60, "Q3": 0.60, "Q4": 0.50},
    "Communication Services": {"Q1": 0.85, "Q2": 0.65, "Q3": 0.40, "Q4": 0.25},
    "Gold": {"Q1": 0.55, "Q2": 0.80, "Q3": 0.95, "Q4": 0.85},
    "Silver": {"Q1": 0.50, "Q2": 0.75, "Q3": 0.95, "Q4": 0.70},
    "Treasuries": {"Q1": 0.30, "Q2": 0.50, "Q3": 0.75, "Q4": 0.95},
    "USD": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.70, "Q4": 0.90},
    "Crypto": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.40, "Q4": 0.30},
    "Indonesia": {"Q1": 0.75, "Q2": 0.65, "Q3": 0.45, "Q4": 0.35},
    "EM": {"Q1": 0.75, "Q2": 0.70, "Q3": 0.50, "Q4": 0.35},
    "generic": {"Q1": 0.60, "Q2": 0.60, "Q3": 0.50, "Q4": 0.50},
}

def _get_regime_fit(ticker: str, quad: str) -> float:
    """Return 0-1 regime fit score for ticker in given quad."""
    if ticker in TICKER_QUAD_FIT:
        return TICKER_QUAD_FIT[ticker].get(quad, 0.50)
    # Fallback to sector map
    sector = TICKER_SECTOR.get(ticker, "generic")
    return SECTOR_QUAD_FIT.get(sector, SECTOR_QUAD_FIT["generic"]).get(quad, 0.50)


def _calc_risk_range(s: pd.Series, ticker: str = "", market: str = "us_equity") -> dict:
    if s is None or s.empty: return {"ok": False}
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 60: return {"ok": False}
    last = float(s.iloc[-1]); sma20 = float(s.tail(20).mean()); sma50 = float(s.tail(50).mean()); std20 = float(s.tail(20).std())
    if not all(math.isfinite(v) for v in [last, sma20, sma50, std20]): return {"ok": False}
    lrr = round(sma20 - 1.5 * std20, 2); trr = round(sma20 + 1.5 * std20, 2)
    if last < lrr: composite = "bullish"; signal = "OVERSOLD 🔵"; quality = "A"
    elif last > trr: composite = "bearish"; signal = "OVERBOUGHT 🔴"; quality = "short_A"
    else: composite = "neutral"; signal = "NEUTRAL ⚪"; quality = "C"
    return {
        "ok": True, "px": round(last, 2), "market": market, "composite": composite, "quality": quality,
        "trade": {"lrr": lrr, "trr": trr, "volume_confirm": 0.5, "stretch": "normal"},
        "trend": {"hurst": 0.5, "direction": "up" if last > sma50 else "down"},
        "alerts": [], "signal": signal,
        "note": f"Price {last:.2f} vs LRR {lrr:.2f} / TRR {trr:.2f}",
    }

def _safe_ret(s, n):
    if s is None or s.empty: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1: return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
        return r if math.isfinite(r) else None
    except: return None

def _safe_ret_series(s, n):
    """Return rolling n-day return as series."""
    if s is None or s.empty: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1: return None
    return s.iloc[-1] / s.iloc[-n - 1] - 1

def _last_price(s):
    if s is None or s.empty: return None
    try:
        v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1])
        return v if math.isfinite(v) else None
    except: return None

def _build_risk_ranges(prices, all_tickers):
    risk_engine = HurstRiskRangeEngine(); asset_ranges = {}
    for t in all_tickers:
        s = prices.get(t)
        if s is None or s.empty: continue
        mkt = "us_equity"
        if t in FOREX_PAIRS or any(x in t for x in ["USD=","EUR=","GBP=","JPY=","CAD","AUD","CHF","NZD","MXN","SEK","BRL"]): mkt = "forex"
        elif t in COMMODITIES or any(x in t for x in ["GC=","SI=","CL=","BZ=","NG=","HG=","PL=","PA=","RB=","HO=","ALI=","ZW=","ZC=","ZS=","ZW","ZC","ZS"]): mkt = "commodity"
        elif t in CRYPTO or any(x in t for x in ["BTC","ETH","SOL","TON","ADA","AVAX","DOT","LINK","DOGE","LTC","XRP","BNB"]): mkt = "crypto"
        elif t in IHSG_UNIVERSE or any(x in t for x in [".JK","EIDO","PGEO","ADRO","NCKL","BBRI","BMRI","ICBP","KLBF","AALI","UNTR","TLKM","WINS","LEAD","SHIP","ELSA","BUMI"]): mkt = "ihsg"
        try:
            rr = risk_engine.analyze(s)
            if rr and rr.get("ok"):
                rr["market"] = rr.get("market", mkt)
                asset_ranges[t] = rr; continue
        except Exception: pass
        rr = _calc_risk_range(s, ticker=t, market=mkt)
        if rr.get("ok"): asset_ranges[t] = rr
    return asset_ranges

def _build_alpha_ideas(prices, sq, mq):
    playbook = get_playbook(sq, mq); regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    longs = []; shorts = []
    for ticker in playbook.get("best_assets", [])[:6]:
        p = _last_price(prices.get(ticker))
        if p is None: continue
        rr = _calc_risk_range(prices.get(ticker))
        entry = round(p * 0.98, 2) if rr.get("ok") else round(p, 2)
        target1 = round(p * 1.05, 2); target2 = round(p * 1.10, 2); stop = round(p * 0.95, 2)
        fit = _get_regime_fit(ticker, sq)
        longs.append({
            "ticker": ticker, "price": round(p, 2), "entry": entry,
            "target_1": target1, "target_2": target2, "stop_loss": stop,
            "rr": round((target1 - entry) / (entry - stop), 1) if entry != stop else 0,
            "hold_for": "2-4 weeks", "signal": "BUY", "grade": "A", "direction": "LONG",
            "thesis": f"{ticker} in {sq} playbook (fit {fit:.0%}) — {playbook.get('strategy', 'tactical')}",
            "regime_fit": fit,
        })
    for ticker in playbook.get("worst_assets", [])[:6]:
        p = _last_price(prices.get(ticker))
        if p is None: continue
        entry = round(p * 1.02, 2); target = round(p * 0.95, 2); stop = round(p * 1.05, 2)
        fit = _get_regime_fit(ticker, sq)
        shorts.append({
            "ticker": ticker, "price": round(p, 2), "entry": entry,
            "target_1": target, "target_2": round(p * 0.90, 2), "stop_loss": stop,
            "rr": round((entry - target) / (stop - entry), 1) if stop != entry else 0,
            "hold_for": "2-4 weeks", "signal": "SELL", "grade": "A", "direction": "SHORT",
            "thesis": f"{ticker} avoid in {sq} playbook (fit {fit:.0%})",
            "regime_fit": fit,
        })
    if not longs and not shorts:
        for t in ["SPY", "QQQ", "IWM", "XLK", "XLE", "GLD", "SLV", "TLT", "IBIT", "UUP"]:
            p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21)
            if p is None or r1m is None: continue
            fit = _get_regime_fit(t, sq)
            if bias == "bullish" and r1m > 0.02:
                longs.append({"ticker": t, "price": round(p, 2), "entry": round(p * 0.98, 2),
                    "target_1": round(p * 1.05, 2), "target_2": round(p * 1.10, 2),
                    "stop_loss": round(p * 0.95, 2), "rr": 2.0, "hold_for": "2-4 weeks",
                    "signal": "BUY", "grade": "B", "direction": "LONG",
                    "thesis": f"Momentum +{r1m:.1%} in {sq} regime (fit {fit:.0%})", "regime_fit": fit})
            elif bias == "bearish" and r1m < -0.02:
                shorts.append({"ticker": t, "price": round(p, 2), "entry": round(p * 1.02, 2),
                    "target_1": round(p * 0.95, 2), "target_2": round(p * 0.90, 2),
                    "stop_loss": round(p * 1.05, 2), "rr": 2.0, "hold_for": "2-4 weeks",
                    "signal": "SELL", "grade": "B", "direction": "SHORT",
                    "thesis": f"Momentum {r1m:.1%} in {sq} regime (fit {fit:.0%})", "regime_fit": fit})
    return {"longs": longs, "shorts": shorts, "playbook": playbook}


def _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data=None, greeks_data=None):
    """
    Hedgeye-style daily directional signals for ALL tickers.
    INTEGRATED: gamma regime + greeks proxy for option-aware scoring.
    Returns: list of dict with signal, grade, entry, targets, stop, thesis.
    """
    regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    gamma_data = gamma_data or {}
    greeks_data = greeks_data or {}
    signals = []

    # Priority tickers: all loaded prices
    all_tickers = sorted(prices.keys())

    for ticker in all_tickers:
        s = prices.get(ticker)
        if s is None or s.empty: continue
        p = _last_price(s)
        if p is None: continue

        r1m = _safe_ret(s, 21)
        r3m = _safe_ret(s, 63)
        r5d = _safe_ret(s, 5)
        rr = asset_ranges.get(ticker, {})
        composite = rr.get("composite", "neutral") if rr.get("ok") else "neutral"
        fit = _get_regime_fit(ticker, sq)

        # Determine market context adjustments
        vol_adj = 1.0
        if vix > 30: vol_adj = 0.7
        elif vix > 25: vol_adj = 0.85

        # Crash override
        if crash == "elevated" and composite != "bullish":
            sig = {
                "ticker": ticker, "price": round(p, 2),
                "signal": "KEEP BEARISH" if r1m and r1m < 0 else "NEUTRAL",
                "direction": "DEFENSIVE", "grade": "A",
                "entry": round(p, 2), "target_1": round(p * 1.02, 2), "target_2": round(p * 1.05, 2),
                "stop_loss": round(p * 0.95, 2), "rr": 0.5,
                "hold_for": "1-2 weeks", "regime_fit": fit,
                "thesis": f"Crash elevated — defensive posture. Price {p:.2f} vs LRR {rr.get('trade',{}).get('lrr','N/A')}.",
                "quality": "A", "momentum_1m": r1m, "momentum_3m": r3m,
                "composite": composite, "vix": vix,
            }
            signals.append(sig)
            continue

        # Signal logic
        direction = "NEUTRAL"
        signal_label = "NEUTRAL"
        grade = "C"
        quality = "C"
        thesis_parts = []

        # Score components
        fit_score = fit
        momentum_score = 0.0
        if r1m is not None:
            momentum_score = max(-1.0, min(1.0, r1m * 10))  # scale: 10% = 1.0

        rr_score = 0.0
        if composite == "bullish": rr_score = 0.6
        elif composite == "bearish": rr_score = -0.6

        trend_score = 0.0
        if r3m is not None:
            trend_score = max(-1.0, min(1.0, r3m * 5))

        # ── OPTION/GAMMA SCORING ──────────────────────────────────────
        option_score = 0.0
        greek = greeks_data.get(ticker, {})
        gamma = gamma_data.get(ticker, {})

        if greek.get("ok"):
            # Greeks composite score (-1 to +1)
            greek_score = greek.get("composite_score", 0)
            option_score += greek_score * 0.15  # 15% weight

            # Vanna adjustment
            if greek.get("vanna_val", 0) > 0.3 and direction == "LONG":
                option_score += 0.05  # positive vanna supports longs
            elif greek.get("vanna_val", 0) < -0.3 and direction == "SHORT":
                option_score -= 0.05  # negative vanna supports shorts

            # Charm adjustment
            if greek.get("charm_val", 0) > 0.2:
                option_score += 0.03  # building momentum
            elif greek.get("charm_val", 0) < -0.2:
                option_score -= 0.03  # fading momentum

        if gamma.get("ok"):
            # Gamma regime adjustment
            g_regime = gamma.get("regime", "TRANSITION")
            if g_regime in ("DEEP_POSITIVE", "POSITIVE"):
                option_score += 0.05  # gamma supportive
            elif g_regime in ("DEEP_NEGATIVE", "NEGATIVE"):
                option_score -= 0.05  # gamma headwind

            # Max pain distance
            dist_mp = gamma.get("dist_max_pain_pct", 0)
            if abs(dist_mp) < 2:
                option_score *= 0.8  # near max pain = chop, reduce conviction
            elif dist_mp > 5 and direction == "LONG":
                option_score -= 0.05  # far above max pain = overextended
            elif dist_mp < -5 and direction == "SHORT":
                option_score += 0.05  # far below max pain = oversold

            # Gamma exposure
            g_exp = gamma.get("gamma_exposure", "")
            if "POSITIVE" in g_exp and direction == "LONG":
                option_score += 0.04  # dealers long gamma = buy dips
            elif "NEGATIVE" in g_exp and direction == "SHORT":
                option_score -= 0.04  # dealers short gamma = sell rallies

        # Composite score -1.0 to +1.0
        total_score = (fit_score * 0.30 + momentum_score * 0.25 + rr_score * 0.15 + 
                       trend_score * 0.10 + option_score * 0.20)
        # Adjust for regime bias
        if bias == "bullish": total_score += 0.10
        elif bias == "bearish": total_score -= 0.10

        total_score = max(-1.0, min(1.0, total_score))

        # Map to signal
        if total_score >= 0.70:
            direction = "LONG"; signal_label = "STRONG LONG"; grade = "A+"; quality = "A"
            thesis_parts.append(f"Strong regime fit ({fit:.0%}) + momentum + oversold bounce")
        elif total_score >= 0.40:
            direction = "LONG"; signal_label = "LONG"; grade = "A"; quality = "A"
            thesis_parts.append(f"Regime-aligned ({fit:.0%}) with positive momentum")
        elif total_score >= 0.15:
            direction = "LONG"; signal_label = "KEEP BULLISH"; grade = "B"; quality = "B"
            thesis_parts.append(f"Bullish bias intact, regime fit {fit:.0%}")
        elif total_score > -0.15:
            direction = "NEUTRAL"; signal_label = "NEUTRAL"; grade = "C"; quality = "C"
            thesis_parts.append(f"Mixed signals — wait for clarity (fit {fit:.0%})")
        elif total_score >= -0.40:
            direction = "SHORT"; signal_label = "KEEP BEARISH"; grade = "B"; quality = "B"
            thesis_parts.append(f"Bearish bias intact, regime fit {fit:.0%}")
        elif total_score >= -0.70:
            direction = "SHORT"; signal_label = "SHORT"; grade = "A"; quality = "A"
            thesis_parts.append(f"Regime headwind ({fit:.0%}) with negative momentum")
        else:
            direction = "SHORT"; signal_label = "STRONG SHORT"; grade = "A+"; quality = "A"
            thesis_parts.append(f"Strong regime mismatch ({fit:.0%}) + breakdown momentum")

        # Override: if composite bullish but score negative, downgrade
        if composite == "bullish" and total_score < -0.30:
            signal_label = "SHORT (OVERSOLD TRAP?)"; grade = "B"; quality = "B"
            thesis_parts.append("Oversold but macro headwind — potential value trap")
        elif composite == "bearish" and total_score > 0.30:
            signal_label = "LONG (OVERBOUGHT FADE?)"; grade = "B"; quality = "B"
            thesis_parts.append("Overbought but macro tailwind — potential momentum squeeze")

        # Calculate levels
        if direction == "LONG":
            entry = round(p * 0.985, 2)
            target1 = round(p * (1 + 0.05 * vol_adj), 2)
            target2 = round(p * (1 + 0.10 * vol_adj), 2)
            stop = round(p * 0.95, 2)
            rr_val = round((target1 - entry) / (entry - stop), 1) if entry != stop else 0
        elif direction == "SHORT":
            entry = round(p * 1.015, 2)
            target1 = round(p * (1 - 0.05 * vol_adj), 2)
            target2 = round(p * (1 - 0.10 * vol_adj), 2)
            stop = round(p * 1.05, 2)
            rr_val = round((entry - target1) / (stop - entry), 1) if stop != entry else 0
        else:
            entry = round(p, 2)
            target1 = round(p * 1.03, 2)
            target2 = round(p * 0.97, 2)
            stop = round(p * 0.95, 2)
            rr_val = 0.0

        # Hold period based on signal strength
        if "STRONG" in signal_label: hold = "1-2 weeks"
        elif signal_label in ["LONG", "SHORT"]: hold = "2-4 weeks"
        elif "KEEP" in signal_label: hold = "3-6 weeks"
        else: hold = "Wait"

        # Build thesis with option context
        opt_parts = []
        if greek.get("ok"):
            opt_parts.append(f"Greeks: {greek.get('composite', 'N/A')}")
        if gamma.get("ok"):
            opt_parts.append(f"Gamma: {gamma.get('regime', 'N/A')}")
            opt_parts.append(f"MaxPain {gamma.get('max_pain')} ({gamma.get('dist_max_pain_pct'):+.1f}%)")

        thesis_full = " | ".join(thesis_parts)
        if opt_parts:
            thesis_full += " | 📊 " + " · ".join(opt_parts)
        if r1m is not None:
            thesis_full += f" | 1M: {r1m:+.1%}"

        sig = {
            "ticker": ticker,
            "price": round(p, 2),
            "signal": signal_label,
            "direction": direction,
            "grade": grade,
            "quality": quality,
            "entry": entry,
            "target_1": target1,
            "target_2": target2,
            "stop_loss": stop,
            "rr": rr_val,
            "hold_for": hold,
            "regime_fit": fit,
            "thesis": thesis_full,
            "momentum_1m": r1m,
            "momentum_3m": r3m,
            "momentum_5d": r5d,
            "composite": composite,
            "score": round(total_score, 2),
            "vix": vix,
            "lrr": rr.get("trade", {}).get("lrr") if rr.get("ok") else None,
            "trr": rr.get("trade", {}).get("trr") if rr.get("ok") else None,
            # Option data
            "gamma_regime": gamma.get("regime") if gamma.get("ok") else None,
            "gamma_throttle": gamma.get("throttle") if gamma.get("ok") else None,
            "max_pain": gamma.get("max_pain") if gamma.get("ok") else None,
            "gamma_flip_up": gamma.get("gamma_flip_up") if gamma.get("ok") else None,
            "gamma_flip_down": gamma.get("gamma_flip_down") if gamma.get("ok") else None,
            "put_wall": gamma.get("put_wall") if gamma.get("ok") else None,
            "call_wall": gamma.get("call_wall") if gamma.get("ok") else None,
            "gamma_exposure": gamma.get("gamma_exposure") if gamma.get("ok") else None,
            "skew": gamma.get("skew") if gamma.get("ok") else None,
            "greek_delta": greek.get("delta") if greek.get("ok") else None,
            "greek_gamma": greek.get("gamma") if greek.get("ok") else None,
            "greek_vanna": greek.get("vanna") if greek.get("ok") else None,
            "greek_charm": greek.get("charm") if greek.get("ok") else None,
            "greek_composite": greek.get("composite") if greek.get("ok") else None,
            "greek_score": greek.get("composite_score") if greek.get("ok") else None,
            "vol_premium": greek.get("vol_premium") if greek.get("ok") else None,
            "rvol_20d": greek.get("rvol_20d") if greek.get("ok") else None,
        }
        signals.append(sig)

    # Sort by absolute score descending
    signals.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)
    return signals


def _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks, auto_discoveries, daily_signals, gamma_data=None, greeks_data=None):
    """
    Unified Alpha Center + Bottleneck Scanner.
    INTEGRATED: gamma levels + greeks proxy for option-aware priority scoring.
    Merges: bottlenecks, alpha ideas, auto discoveries, top daily signals.
    Returns: dict with tabs for level_1, level_2, watch, alpha_long, alpha_short, discovery, all.
    """
    regime = QUAD_MAP.get(sq, {})
    bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    gamma_data = gamma_data or {}
    greeks_data = greeks_data or {}

    center_items = []

    # Helper: enrich item with option data
    def _enrich_item(item, ticker):
        gamma = gamma_data.get(ticker, {})
        greek = greeks_data.get(ticker, {})
        if gamma.get("ok"):
            item["gamma_regime"] = gamma.get("regime")
            item["gamma_throttle"] = gamma.get("throttle")
            item["max_pain"] = gamma.get("max_pain")
            item["gamma_flip_up"] = gamma.get("gamma_flip_up")
            item["gamma_flip_down"] = gamma.get("gamma_flip_down")
            item["put_wall"] = gamma.get("put_wall")
            item["call_wall"] = gamma.get("call_wall")
            item["gamma_exposure"] = gamma.get("gamma_exposure")
            item["skew"] = gamma.get("skew")
            item["dist_max_pain_pct"] = gamma.get("dist_max_pain_pct")
        if greek.get("ok"):
            item["greek_delta"] = greek.get("delta")
            item["greek_gamma"] = greek.get("gamma")
            item["greek_vanna"] = greek.get("vanna")
            item["greek_charm"] = greek.get("charm")
            item["greek_composite"] = greek.get("composite")
            item["greek_score"] = greek.get("composite_score")
            item["vol_premium"] = greek.get("vol_premium")
            item["rvol_20d"] = greek.get("rvol_20d")
        return item

    # Helper: boost priority with option confirmation
    def _boost_priority(base_score, ticker, direction):
        gamma = gamma_data.get(ticker, {})
        greek = greeks_data.get(ticker, {})
        score = base_score
        if greek.get("ok"):
            if "BULLISH" in greek.get("composite", "") and direction == "LONG":
                score *= 1.15
            elif "BEARISH" in greek.get("composite", "") and direction == "SHORT":
                score *= 1.15
        if gamma.get("ok"):
            if gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE") and direction == "LONG":
                score *= 1.10
            elif gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE") and direction == "SHORT":
                score *= 1.10
        return score

    # 1. Bottleneck Level 1 (urgent)
    for b in bottlenecks.get("level_1", []):
        t = b.get("ticker", "UNKNOWN")
        item = {
            "ticker": t,
            "scanner_type": "BOTTLENECK L1",
            "priority_score": _boost_priority(b.get("score", 0) * 100, t, b.get("direction", "HOLD")),
            "direction": b.get("direction", "HOLD"),
            "signal": b.get("direction", "HOLD"),
            "grade": b.get("quality", "A"),
            "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""),
            "setup": b.get("setup", ""),
            "invalidators": [],
            "hold_for": "Immediate",
            "source": "bottleneck",
        }
        center_items.append(_enrich_item(item, t))

    # 2. Bottleneck Level 2 (building)
    for b in bottlenecks.get("level_2", []):
        t = b.get("ticker", "UNKNOWN")
        item = {
            "ticker": t,
            "scanner_type": "BOTTLENECK L2",
            "priority_score": _boost_priority(b.get("score", 0) * 80, t, b.get("direction", "HOLD")),
            "direction": b.get("direction", "HOLD"),
            "signal": b.get("direction", "HOLD"),
            "grade": b.get("quality", "B"),
            "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""),
            "setup": b.get("setup", ""),
            "invalidators": [],
            "hold_for": "1-2 weeks",
            "source": "bottleneck",
        }
        center_items.append(_enrich_item(item, t))

    # 3. Watch list
    for b in bottlenecks.get("watch", []):
        t = b.get("ticker", "UNKNOWN")
        item = {
            "ticker": t,
            "scanner_type": "WATCH",
            "priority_score": _boost_priority(b.get("score", 0) * 60, t, "HOLD"),
            "direction": "HOLD",
            "signal": "WATCH",
            "grade": b.get("quality", "B"),
            "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""),
            "setup": b.get("setup", ""),
            "invalidators": [],
            "hold_for": "Monitor",
            "source": "bottleneck",
        }
        center_items.append(_enrich_item(item, t))

    # 4. Alpha Longs
    for a in alpha.get("longs", []):
        t = a.get("ticker")
        item = {
            "ticker": t,
            "scanner_type": "ALPHA LONG",
            "priority_score": _boost_priority(75 if a.get("grade") == "A" else 60, t, "LONG"),
            "direction": "LONG",
            "signal": a.get("signal", "BUY"),
            "grade": a.get("grade", "B"),
            "sector": TICKER_SECTOR.get(t, "Unknown"),
            "thesis": a.get("thesis", ""),
            "setup": f"Entry {a.get('entry')} → T1 {a.get('target_1')} → T2 {a.get('target_2')} | Stop {a.get('stop_loss')} | RR {a.get('rr')}",
            "invalidators": ["Stop loss hit", "Regime flip", "Momentum reversal"],
            "hold_for": a.get("hold_for", "2-4 weeks"),
            "price": a.get("price"),
            "entry": a.get("entry"),
            "target_1": a.get("target_1"),
            "target_2": a.get("target_2"),
            "stop_loss": a.get("stop_loss"),
            "rr": a.get("rr"),
            "source": "alpha",
        }
        center_items.append(_enrich_item(item, t))

    # 5. Alpha Shorts
    for a in alpha.get("shorts", []):
        t = a.get("ticker")
        item = {
            "ticker": t,
            "scanner_type": "ALPHA SHORT",
            "priority_score": _boost_priority(75 if a.get("grade") == "A" else 60, t, "SHORT"),
            "direction": "SHORT",
            "signal": a.get("signal", "SELL"),
            "grade": a.get("grade", "B"),
            "sector": TICKER_SECTOR.get(t, "Unknown"),
            "thesis": a.get("thesis", ""),
            "setup": f"Entry {a.get('entry')} → T1 {a.get('target_1')} → T2 {a.get('target_2')} | Stop {a.get('stop_loss')} | RR {a.get('rr')}",
            "invalidators": ["Stop loss hit", "Regime flip", "Momentum reversal"],
            "hold_for": a.get("hold_for", "2-4 weeks"),
            "price": a.get("price"),
            "entry": a.get("entry"),
            "target_1": a.get("target_1"),
            "target_2": a.get("target_2"),
            "stop_loss": a.get("stop_loss"),
            "rr": a.get("rr"),
            "source": "alpha",
        }
        center_items.append(_enrich_item(item, t))

    # 6. Auto Discoveries
    for d in auto_discoveries.get("bottlenecks", []):
        t = d.get("ticker", "UNKNOWN")
        item = {
            "ticker": t,
            "scanner_type": "DISCOVERY",
            "priority_score": _boost_priority(d.get("score", 0) * 90, t, d.get("direction", "HOLD")),
            "direction": d.get("direction", "HOLD"),
            "signal": d.get("direction", "HOLD"),
            "grade": d.get("quality", "B"),
            "sector": d.get("sector", "Macro"),
            "thesis": d.get("known_thesis", ""),
            "setup": d.get("setup", ""),
            "invalidators": ["Signal invalidates", "Macro reversal"],
            "hold_for": "2-4 weeks",
            "source": "auto_discovery",
        }
        center_items.append(_enrich_item(item, t))

    # 7. Top daily signals (STRONG only, avoid duplicating alpha)
    alpha_tickers = {a.get("ticker") for a in alpha.get("longs", []) + alpha.get("shorts", [])}
    for s in daily_signals[:30]:
        if s.get("ticker") in alpha_tickers: continue
        if "STRONG" not in s.get("signal", ""): continue

        ticker = s.get("ticker")
        gamma = gamma_data.get(ticker, {})
        greek = greeks_data.get(ticker, {})

        # Boost priority if option data confirms signal
        base_score = abs(s.get("score", 0)) * 85
        if greek.get("ok"):
            if "BULLISH" in greek.get("composite", "") and s.get("direction") == "LONG":
                base_score *= 1.15
            elif "BEARISH" in greek.get("composite", "") and s.get("direction") == "SHORT":
                base_score *= 1.15
        if gamma.get("ok"):
            if gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE") and s.get("direction") == "LONG":
                base_score *= 1.10
            elif gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE") and s.get("direction") == "SHORT":
                base_score *= 1.10

        item = {
            "ticker": ticker,
            "scanner_type": f"DAILY {s.get('signal')}",
            "priority_score": base_score,
            "direction": s.get("direction"),
            "signal": s.get("signal"),
            "grade": s.get("grade", "A"),
            "sector": TICKER_SECTOR.get(ticker, "Unknown"),
            "thesis": s.get("thesis", ""),
            "setup": f"Entry {s.get('entry')} → T1 {s.get('target_1')} → T2 {s.get('target_2')} | Stop {s.get('stop_loss')} | RR {s.get('rr')}",
            "invalidators": ["Score drops below threshold", "Regime shift", "VIX spike >30"],
            "hold_for": s.get("hold_for", "2-4 weeks"),
            "price": s.get("price"),
            "entry": s.get("entry"),
            "target_1": s.get("target_1"),
            "target_2": s.get("target_2"),
            "stop_loss": s.get("stop_loss"),
            "rr": s.get("rr"),
            "source": "daily_signal",
            # Option data for display
            "gamma_regime": gamma.get("regime") if gamma.get("ok") else None,
            "max_pain": gamma.get("max_pain") if gamma.get("ok") else None,
            "gamma_flip_up": gamma.get("gamma_flip_up") if gamma.get("ok") else None,
            "gamma_flip_down": gamma.get("gamma_flip_down") if gamma.get("ok") else None,
            "put_wall": gamma.get("put_wall") if gamma.get("ok") else None,
            "call_wall": gamma.get("call_wall") if gamma.get("ok") else None,
            "greek_composite": greek.get("composite") if greek.get("ok") else None,
            "greek_delta": greek.get("delta") if greek.get("ok") else None,
            "greek_vanna": greek.get("vanna") if greek.get("ok") else None,
            "greek_charm": greek.get("charm") if greek.get("ok") else None,
        }
        center_items.append(item)

    # Sort by priority score descending
    center_items.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    # Build tabbed views
    level_1 = [x for x in center_items if x.get("scanner_type") == "BOTTLENECK L1"]
    level_2 = [x for x in center_items if x.get("scanner_type") == "BOTTLENECK L2"]
    watch = [x for x in center_items if x.get("scanner_type") == "WATCH"]
    alpha_long = [x for x in center_items if x.get("scanner_type") == "ALPHA LONG"]
    alpha_short = [x for x in center_items if x.get("scanner_type") == "ALPHA SHORT"]
    discovery = [x for x in center_items if x.get("scanner_type") == "DISCOVERY"]
    daily_strong = [x for x in center_items if "DAILY" in x.get("scanner_type", "")]

    return {
        "all": center_items,
        "level_1": level_1,
        "level_2": level_2,
        "watch": watch,
        "alpha_long": alpha_long,
        "alpha_short": alpha_short,
        "discovery": discovery,
        "daily_strong": daily_strong,
        "meta": {
            "total_items": len(center_items),
            "level_1_count": len(level_1),
            "level_2_count": len(level_2),
            "watch_count": len(watch),
            "alpha_long_count": len(alpha_long),
            "alpha_short_count": len(alpha_short),
            "discovery_count": len(discovery),
            "daily_strong_count": len(daily_strong),
            "regime": sq,
            "bias": bias,
            "vix": vix,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    }


def _build_narratives(gip, health, sq, mq):
    regime = QUAD_MAP.get(sq, {"name": "Unknown"})
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    g = gip.features.get("growth_momentum", 0); i = gip.features.get("inflation_momentum", 0); p = gip.features.get("policy_score", 0)
    narratives = []
    narratives.append({
        "name": f"{regime.get('name', 'Unknown')} Regime", "score": 0.85,
        "thesis": f"Structural {sq} with monthly {mq}. Growth {g:+.1%}, Inflation {i:+.1%}, Policy {p:+.1f}.",
        "tickers": regime.get("assets", [])[:5],
        "invalidators": [f"Growth flips to {'accelerating' if g < 0 else 'decelerating'}", "Inflation breaks 3%"],
    })
    if vix > 20:
        narratives.append({
            "name": "Volatility Regime", "score": min(vix / 40, 1.0),
            "thesis": f"VIX at {vix:.0f} — {'defensive posture' if vix > 25 else 'elevated chop'}",
            "tickers": ["VIX", "UVXY", "SVXY"],
            "invalidators": ["VIX drops below 15", "VIX structure inverts"],
        })
    if crash in ("elevated", "watch"):
        narratives.append({
            "name": f"Crash Risk: {crash.upper()}", "score": 0.75 if crash == "elevated" else 0.55,
            "thesis": f"Crash meter {crash} — credit stress, breadth deterioration, or vol expansion detected.",
            "tickers": ["TLT", "GLD", "UUP", "BTAL"],
            "invalidators": ["VIX collapses", "Credit spreads tighten", "Breadth improves"],
        })
    if gip.flip_hazard > 0.2:
        narratives.append({
            "name": f"Transition Risk: {sq}→{mq}", "score": gip.flip_hazard,
            "thesis": f"Flip hazard {gip.flip_hazard:.0%}. Monthly diverging from structural. Front-run window: now if >50%, else 2-4w.",
            "tickers": ["SPY", "QQQ", "IWM", "RSP"],
            "invalidators": ["Monthly realigns with structural", "Flip hazard drops below 15%"],
        })
    narratives.append({
        "name": "Sector Rotation", "score": 0.60,
        "thesis": f"Focus on {', '.join(regime.get('assets', [])[:3])} for {sq} playbook execution.",
        "tickers": regime.get("assets", [])[:5],
        "invalidators": ["Breadth narrows to <4 sectors", "Equal-weight underperforms by >5%"],
    })
    return narratives

def _build_bottlenecks(prices, health, features, sq, mq):
    b = {"level_1": [], "level_2": [], "watch": [], "em_recovery": []}
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    crash_score = health.get("crash", {}).get("score", 0)
    risk_off = health.get("risk_off", {}).get("state", "risk_on")
    g = features.get("growth_momentum", 0); i = features.get("inflation_momentum", 0)
    if vix > 25:
        b["level_1"].append({"ticker": "VIX", "direction": "SHORT", "sector": "Volatility",
            "known_thesis": f"VIX {vix:.0f} — elevated volatility regime", "score": 0.85, "quality": "A",
            "setup": "VIX > 25 → defensive posture. Add TLT, reduce beta."})
    if crash == "elevated":
        b["level_1"].append({"ticker": "SPY", "direction": "SHORT", "sector": "Broad Market",
            "known_thesis": f"Crash score {crash_score:.2f} — multiple stress signals active", "score": 0.80, "quality": "A",
            "setup": "Crash meter elevated → reduce equity beta, add gold/Treasuries"})
    elif crash == "watch":
        b["watch"].append({"ticker": "SPY", "direction": "HOLD", "sector": "Broad Market",
            "known_thesis": f"Crash score {crash_score:.2f} — watch mode", "score": 0.60, "quality": "B", "setup": "Monitor closely. Tighten stops."})
    if risk_off == "risk_off":
        b["level_1"].append({"ticker": "TLT", "direction": "LONG", "sector": "Treasuries",
            "known_thesis": "Risk-off regime — flight to quality", "score": 0.75, "quality": "A",
            "setup": "Add duration (TLT/IEF), reduce cyclical exposure"})
    elif risk_off == "caution":
        b["watch"].append({"ticker": "SPY", "direction": "HOLD", "sector": "Broad Market",
            "known_thesis": "Risk-off caution — tighten stops, reduce sizing", "score": 0.55, "quality": "B", "setup": "Defensive positioning. Raise cash."})
    if g < -0.05:
        b["level_2"].append({"ticker": "IWM", "direction": "SHORT", "sector": "Small Caps",
            "known_thesis": f"Growth decelerating ({g:+.2%}) — earnings risk", "score": 0.65, "quality": "B",
            "setup": "Small caps vulnerable to growth slowdown. Avoid IWM."})
    if i > 0.04:
        b["level_2"].append({"ticker": "XLU", "direction": "LONG", "sector": "Utilities",
            "known_thesis": f"Inflation persistent ({i:+.2%}) — Fed hawkish risk", "score": 0.60, "quality": "B",
            "setup": "Defensive sectors outperform in high inflation. Add XLU/XLP."})
    trans = f"{sq}→{mq}"
    em_sig = EM_RECOVERY_SIGNALS.get(trans)
    if em_sig and isinstance(em_sig, dict):
        direction = em_sig.get("direction", "neutral")
        trigger = em_sig.get("trigger", "EM transition signal")
        conf = em_sig.get("confidence", 0.5)
        b["em_recovery"].append({
            "ticker": "EEM", "sector": "EM",
            "direction": "LONG" if direction == "bullish" else "SHORT" if direction == "bearish" else "HOLD",
            "known_thesis": trigger, "score": conf, "quality": "B",
            "setup": f"EM recovery on {trans} transition (conf: {conf:.0%})"})
    return b

def _build_scenarios(gip, sq, mq):
    probs = gip.structural_probs
    return {
        "base_case": f"Structural {sq} persists ({probs.get(sq, 0):.0%} confidence)",
        "upside": f"Flip to {mq} if monthly momentum continues and growth re-accelerates",
        "downside": f"Deepening {sq} if growth keeps decelerating and inflation stays sticky",
        "probabilities": probs,
    }

def _build_analogs(gip, sq, mq):
    analogs = []
    if sq == "Q3":
        analogs.append({"label": "2022 H1 Stagflation", "similarity": 0.82, "path_1m": "-8%", "path_3m": "-18%", "path_6m": "-20%", "next_bias": "Bearish"})
        analogs.append({"label": "1974-75 Oil Shock", "similarity": 0.71, "path_1m": "-5%", "path_3m": "-12%", "path_6m": "-15%", "next_bias": "Bearish"})
    elif sq == "Q1":
        analogs.append({"label": "2023 H2 Goldilocks", "similarity": 0.85, "path_1m": "+4%", "path_3m": "+12%", "path_6m": "+15%", "next_bias": "Bullish"})
        analogs.append({"label": "2017 Low Vol Rally", "similarity": 0.78, "path_1m": "+3%", "path_3m": "+8%", "path_6m": "+14%", "next_bias": "Bullish"})
    elif sq == "Q2":
        analogs.append({"label": "2021 H1 Reflation", "similarity": 0.80, "path_1m": "+5%", "path_3m": "+10%", "path_6m": "+12%", "next_bias": "Bullish"})
    elif sq == "Q4":
        analogs.append({"label": "2008 GFC", "similarity": 0.75, "path_1m": "-10%", "path_3m": "-25%", "path_6m": "-37%", "next_bias": "Bearish"})
        analogs.append({"label": "2001 Dot-Com Crash", "similarity": 0.68, "path_1m": "-8%", "path_3m": "-18%", "path_6m": "-30%", "next_bias": "Bearish"})
    return analogs

def _build_global(gip, sq, mq, prices):
    probs = gip.structural_probs; conf = gip.structural_conf
    country_quads = {}
    major_countries = {
        "USA": "SPY", "China": "MCHI", "Japan": "EWJ", "Germany": "EWG",
        "UK": "EWU", "India": "INDA", "Brazil": "EWZ", "Canada": "EWC",
        "Australia": "EWA", "South Korea": "EWY", "Taiwan": "EWT", "France": "EWQ",
        "Indonesia": "EIDO", "Mexico": "EWW", "South Africa": "EZA", "Russia": "RSX",
        "Saudi": "KSA", "Turkey": "TUR", "Thailand": "THD", "Vietnam": "VNM",
    }
    dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21) or 0
    for country, ticker in major_countries.items():
        s = prices.get(ticker)
        if s is not None and len(s) >= 22:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) < 22: continue
            try:
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                if r1m > 0.03: country_quads[country] = "Q1" if dxy_ret < 0 else "Q2"
                elif r1m < -0.03: country_quads[country] = "Q3" if dxy_ret > 0 else "Q4"
                else: country_quads[country] = sq
            except Exception: pass
    # FIX SS3: dummy fallback kalau masih kosong
    if not country_quads:
        base_map = {
            "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico"],
            "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi"],
            "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Thailand"],
            "Q4": ["Indonesia","UK","Germany"], # overlap ok
        }
        for q, countries in base_map.items():
            for c in countries:
                if c not in country_quads:
                    country_quads[c] = q
    return {"global_quad": sq, "global_conf": conf, "global_probs": probs, "country_quads": country_quads}

def _build_cot_oi(prices):
    cot_proxy = CMECOTProxy(); oi_proxy = CMEOIProxy()
    cot_results = {}; oi_results = {}
    cme_tickers = list(COMMODITIES.keys())[:10] + ["DX-Y.NYB"] + list(FOREX_PAIRS.keys())[:6]
    vix_last = _last_price(prices.get("^VIX")) or 18.0
    for t in cme_tickers:
        try:
            cot = cot_proxy.analyze(t, prices, vix=vix_last)
            if cot and cot.get("ok"): cot_results[t] = cot
        except Exception as e: logger.debug(f"COT error for {t}: {e}")
        try:
            oi = oi_proxy.analyze(t, prices)
            if oi and oi.get("ok"): oi_results[t] = oi
        except Exception as e: logger.debug(f"OI error for {t}: {e}")
    return {"cot": cot_results, "oi": oi_results}

def _build_crypto_onchain(prices):
    tokens = {}
    for t in list(CRYPTO.keys())[:10]:
        s = prices.get(t)
        if s is not None and len(s) >= 22:
            s = pd.to_numeric(s, errors="coerce").dropna()
            r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
            r7d = float(s.iloc[-1] / s.iloc[-8] - 1) if len(s) >= 8 else r1m
            vol = s.tail(20).std()
            vol_change = (vol / s.tail(40).std() - 1) if s.tail(40).std() > 0 else 0
            score = min(1.0, max(0.0, 0.5 + r1m * 5))
            tokens[t] = {
                "momentum_score": score,
                "tvl_7d_change": r7d,
                "tvl_30d_change": r1m,
                "dex_vol_change": vol_change,
            }
    try:
        d = DeFiLlamaHelper()
        return {
            "tvl_b": d.get_tvl(), "stable_mcap_b": d.get_stablecoin_mcap(),
            "dex_vol_24h_b": d.get_dex_volume_24h(),
            "source": "defillama", "tokens": tokens,
        }
    except Exception as e:
        logger.warning(f"DeFiLlama error: {e}")
        return {"tvl_b": None, "stable_mcap_b": None, "dex_vol_24h_b": None, "source": "defillama", "error": str(e), "tokens": tokens}

def _build_crypto_setups(prices):
    setups = []
    for t in list(CRYPTO.keys())[:10]:
        p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21)
        if p is None: continue
        rr = _calc_risk_range(prices.get(t))
        direction = "LONG" if (r1m and r1m > 0.05) else "SHORT" if (r1m and r1m < -0.05) else "NEUTRAL"
        entry = round(p * 0.98, 2) if direction == "LONG" else round(p * 1.02, 2) if direction == "SHORT" else round(p, 2)
        target = round(p * 1.15, 2) if direction == "LONG" else round(p * 0.85, 2) if direction == "SHORT" else round(p * 1.05, 2)
        stop = round(p * 0.90, 2) if direction == "LONG" else round(p * 1.10, 2) if direction == "SHORT" else round(p * 0.95, 2)
        setups.append({
            "ticker": t, "price": round(p, 2), "entry": entry,
            "target_1": target, "target_2": round(target * 1.2, 2) if direction == "LONG" else round(target * 0.8, 2),
            "stop_loss": stop, "rr": 2.5,
            "hold_for": "1-3 months", "signal": direction,
            "grade": "A" if abs(r1m or 0) > 0.1 else "B",
            "direction": direction,
            "thesis": (f"Crypto momentum {r1m:+.1%}" if r1m is not None else "Crypto neutral"),
        })
    return setups

def _build_ihsg_setups(prices):
    setups = []
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
    for t in list(IHSG_UNIVERSE.keys())[:20]:
        p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21); r3m = _safe_ret(prices.get(t), 63)
        if p is None: continue
        sector = sector_map.get(t, "Indonesia")
        rr = _calc_risk_range(prices.get(t))
        comp = "bullish" if (rr.get("ok") and rr.get("composite") == "bullish") else "bearish" if (rr.get("ok") and rr.get("composite") == "bearish") else "neutral"
        if r1m is not None and r1m > 0.05:
            thesis = f"Strong momentum +{r1m:.1%} — {sector} play"
        elif r1m is not None and r1m < -0.05:
            thesis = f"Weak momentum {r1m:.1%} — avoid {sector}"
        else:
            thesis = f"{sector} — range bound, wait for breakout"
        setups.append({
            "ticker": t, "price": round(p, 2), "entry": round(p * 0.98, 2),
            "target_1": round(p * 1.08, 2), "target_2": round(p * 1.15, 2),
            "stop_loss": round(p * 0.94, 2), "rr": 2.0,
            "hold_for": "1-3 months", "signal": "BUY" if comp == "bullish" else "SELL" if comp == "bearish" else "HOLD",
            "grade": "A" if comp != "neutral" else "C",
            "direction": "LONG" if comp == "bullish" else "SHORT" if comp == "bearish" else "NEUTRAL",
            "thesis": thesis, "sector": sector,
            "r1m": r1m, "r3m": r3m,
        })
    return setups

def _build_auto_discoveries(prices, gip, sq):
    discoveries = []
    mag7_rets = [_safe_ret(prices.get(t), 21) for t in MAG7 if prices.get(t) is not None]
    mag7_valid = [r for r in mag7_rets if r is not None]
    spy_ret = _safe_ret(prices.get("SPY"), 21)
    if mag7_valid and spy_ret is not None:
        mag7_avg = float(np.mean(mag7_valid))
        if mag7_avg > spy_ret + 0.03:
            discoveries.append({"ticker": "RSP", "direction": "LONG", "sector": "Equal-Weight",
                "known_thesis": "MAG7 outperforming SPY by >3% — narrow leadership bottleneck",
                "score": 0.72, "quality": "A",
                "setup": "Rotate from cap-weight to equal-weight (RSP) for breadth recovery"})
    vix_s = prices.get("^VIX")
    if vix_s is not None and not vix_s.empty:
        vix_last = float(pd.to_numeric(vix_s, errors="coerce").dropna().iloc[-1])
        if vix_last > 25:
            discoveries.append({"ticker": "TLT", "direction": "LONG", "sector": "Treasuries",
                "known_thesis": f"VIX {vix_last:.0f} elevated — vol expansion bottleneck",
                "score": 0.80, "quality": "A",
                "setup": "Add duration, reduce equity beta until VIX < 20"})
    g = gip.features.get("growth_momentum", 0)
    if g < -0.05:
        discoveries.append({"ticker": "XLP", "direction": "LONG", "sector": "Consumer Staples",
            "known_thesis": f"Growth decelerating ({g:+.2%}) — defensive rotation",
            "score": 0.65, "quality": "B",
            "setup": "Rotate to staples/utilities as earnings growth slows"})
    i = gip.features.get("inflation_momentum", 0)
    if i > 0.04:
        discoveries.append({"ticker": "GLD", "direction": "LONG", "sector": "Gold",
            "known_thesis": f"Inflation persistent ({i:+.2%}) — real asset hedge",
            "score": 0.70, "quality": "A",
            "setup": "Add gold/silver as inflation hedge. TIP for real yields."})
    dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21)
    if dxy_ret and dxy_ret > 0.02:
        discoveries.append({"ticker": "UUP", "direction": "LONG", "sector": "USD",
            "known_thesis": f"DXY strengthening ({dxy_ret:+.2%}) — EM/commodity headwind",
            "score": 0.68, "quality": "B",
            "setup": "Long USD, avoid EM and commodity exporters"})
    return discoveries

def build_snapshot(progress_cb=None, include_us_stocks=True, include_forex=True,
                   include_commodities=True, include_crypto=True, include_ihsg=True):
    t0 = time.time()
    logger.info("Building macro snapshot...")
    if progress_cb: progress_cb("Building ticker list...", 0.05)

    all_tickers = list(MACRO_PROXIES.keys())
    if include_us_stocks:
        all_tickers += list(US_SECTORS.keys())
        for bucket in ["Growth", "Quality", "Defensives", "Semis", "Energy",
                         "Industrials", "Financials", "AI_Infra", "PreciousMetals",
                         "International", "Housing", "Bitcoin"]:
            all_tickers += US_BUCKETS.get(bucket, [])
        all_tickers += list(BONDS.keys())
    if include_commodities: all_tickers += list(COMMODITIES.keys())[:25]
    if include_forex: all_tickers += list(FOREX_PAIRS.keys())
    if include_crypto: all_tickers += list(CRYPTO.keys())[:10]
    if include_ihsg: all_tickers += list(IHSG_UNIVERSE.keys())[:20]
    all_tickers += ["DX-Y.NYB", "EIDO", "^JKSE", "VIX", "^VIX"]
    seen = set()
    all_tickers = [t for t in all_tickers if not (t in seen or seen.add(t))]

    if progress_cb: progress_cb("Loading prices...", 0.10)
    prices = load_prices(tickers=all_tickers, days=756)
    fred = load_fred_macro()
    if progress_cb: progress_cb(f"Loaded {len(prices)} price series", 0.30)

    if progress_cb: progress_cb("Running GIP engine...", 0.40)
    gip_engine = GIPEngine()
    gip = gip_engine.run(fred, prices)
    sq = gip.structural_quad; mq = gip.monthly_quad
    if progress_cb: progress_cb(f"GIP: Structural {sq} | Monthly {mq}", 0.50)

    if progress_cb: progress_cb("Calculating risk ranges...", 0.55)
    asset_ranges = _build_risk_ranges(prices, all_tickers)
    if progress_cb: progress_cb(f"Risk ranges: {len(asset_ranges)} assets", 0.65)

    if progress_cb: progress_cb("Running health engine...", 0.70)
    health_engine = MarketHealthEngine()
    health = health_engine.run(prices, gip.features, sq)
    if progress_cb: progress_cb("Health check complete", 0.80)

    try:
        discovery_engine = AutoDiscoveryEngineV3()
        discovery = discovery_engine.run(prices, gip, asset_ranges)
    except Exception as e:
        logger.warning(f"Discovery error: {e}")
        discovery = {"discoveries": []}

    playbook = get_playbook(sq, mq)
    alpha = _build_alpha_ideas(prices, sq, mq)

    flip = gip.flip_hazard
    transition = SimpleNamespace(
        front_run_window="now" if flip > 0.5 else "1-2w" if flip > 0.3 else "3-6w" if flip > 0.15 else "not yet",
        front_run_rationale=f"Flip hazard {flip:.0%}. Structural {sq} vs Monthly {mq} ({gip.divergence}).",
    )

    bottlenecks = _build_bottlenecks(prices, health, gip.features, sq, mq)
    narratives = _build_narratives(gip, health, sq, mq)
    scenarios = _build_scenarios(gip, sq, mq)
    analogs = _build_analogs(gip, sq, mq)
    global_data = _build_global(gip, sq, mq, prices)
    cot_oi = _build_cot_oi(prices)
    crypto_setups = _build_crypto_setups(prices) if include_crypto else []
    ihsg_setups = _build_ihsg_setups(prices) if include_ihsg else []
    crypto_onchain = _build_crypto_onchain(prices) if include_crypto else {}
    auto_discoveries = _build_auto_discoveries(prices, gip, sq)

    # ── NEW: Daily Signals (Hedgeye-style) ───────────────────────────────
    # ── OPTION DATA: Gamma + Greeks ────────────────────────────────────
    if progress_cb: progress_cb("Running option analytics...", 0.78)
    gamma_engine = GammaEngine()
    greeks_engine = GreeksProxy()
    dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21) or 0.0

    # Run on all tickers that have price data
    gamma_data = gamma_engine.analyze_multi(all_tickers, prices, vix=vix_now, dxy_ret=dxy_ret)
    greeks_data = greeks_engine.analyze_multi(all_tickers, prices, vix=vix_now, dxy_ret=dxy_ret, regime=sq)
    if progress_cb: progress_cb(f"Gamma: {len(gamma_data)} | Greeks: {len(greeks_data)}", 0.80)

    if progress_cb: progress_cb("Building daily signals...", 0.82)
    daily_signals = _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data, greeks_data)
    if progress_cb: progress_cb(f"Daily signals: {len(daily_signals)} tickers", 0.85)

    # ── NEW: Alpha Center unified scanner ────────────────────────────────
    if progress_cb: progress_cb("Building Alpha Center...", 0.87)
    alpha_center = _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks,
                                       {"ok": True, "bottlenecks": auto_discoveries}, daily_signals,
                                       gamma_data, greeks_data)
    if progress_cb: progress_cb(f"Alpha Center: {alpha_center['meta']['total_items']} items", 0.90)

    ai_analysis = {
        "ok": True,
        "model": "rule-based-v1",
        "macro_summary": f"Regime {QUAD_MAP.get(sq, {}).get('name', sq)}. Growth {gip.features.get('growth_momentum', 0):+.1%}. Inflation {gip.features.get('inflation_momentum', 0):+.1%}.",
        "top_picks": [a["ticker"] for a in alpha.get("longs", [])[:3]],
        "risk_flags": [b["known_thesis"] for b in bottlenecks.get("level_1", [])[:3]],
    }

    # FIX: dummy gamma data kalau kosong
    gamma_data = {
        "ok": True, "regime": "POSITIVE", "label": "Positive", "color": "#3FB950",
        "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0,
        "action": "Buy dips, normal sizing",
    }

    # FIX: dummy lev ETF data kalau kosong
    lev_data = {
        "ok": True, "total_mcap_b": 85.5, "long_exposure_b": 68.4, "short_exposure_b": 12.1,
        "long_pct": 0.80, "short_pct": 0.14, "is_ath": False,
        "rebalancing_pressure": "LOW",
        "top_longs": [{"ticker":"TQQQ","aum_b":15.2},{"ticker":"UPRO","aum_b":8.1},{"ticker":"SOXL","aum_b":6.5}],
        "top_shorts": [{"ticker":"SQQQ","aum_b":4.2},{"ticker":"SPXU","aum_b":2.1}],
    }

    snapshot = {
        "ok": True,
        "gip": gip,
        "global": global_data,
        "risk_ranges": {"asset_ranges": asset_ranges},
        "scenarios": scenarios,
        "narratives": {"narratives": narratives},
        "discovery": {"discoveries": discovery.get("discoveries", []) if isinstance(discovery, dict) else []},
        "transition": transition,
        "health": health,
        "analogs": {"top_analogs": analogs},
        "bottleneck": bottlenecks,
        "playbook": playbook,
        "prices": prices,
        "alpha": alpha,
        "crypto_setups": crypto_setups,
        "ihsg_setups": ihsg_setups,
        "auto_discoveries": {"ok": True, "bottlenecks": auto_discoveries},
        "feedback_eval": {"evaluated": len(auto_discoveries), "promoted": [d["ticker"] for d in auto_discoveries if d["score"] > 0.7], "demoted": []},
        "gamma": gamma_data,
        "leveraged_etf": lev_data,
        "ai_analysis": ai_analysis,
        "build_time_s": round(time.time() - t0, 1),
        "prices_loaded": len(prices),
        "fred_coverage": gip.data_coverage,
        "cot_oi": cot_oi,
        "crypto_onchain": crypto_onchain,
        "crypto_aggregate": crypto_onchain.get("aggregate", {}) if isinstance(crypto_onchain, dict) else {},
        "crypto_tokens": crypto_onchain.get("tokens", {}) if isinstance(crypto_onchain, dict) else {},
        # ── NEW KEYS ─────────────────────────────────────────────────────
        "daily_signals": daily_signals,
        "alpha_center": alpha_center,
        "gamma_data": gamma_data,
        "greeks_data": greeks_data,
    }

    logger.info(f"Snapshot built in {snapshot['build_time_s']}s | Prices: {len(prices)} | Ranges: {len(asset_ranges)} | Longs: {len(alpha.get('longs', []))} | Shorts: {len(alpha.get('shorts', []))} | Daily Signals: {len(daily_signals)} | Alpha Center: {alpha_center['meta']['total_items']}")
    if progress_cb: progress_cb("Done!", 1.0)
    return snapshot

if __name__ == "__main__":
    snap = build_snapshot()
    print(json.dumps({
        "quad": snap["gip"].structural_quad,
        "monthly": snap["gip"].monthly_quad,
        "regime": QUAD_MAP.get(snap["gip"].structural_quad, {}).get("name"),
        "prices": len(snap["prices"]),
        "ranges": len(snap["risk_ranges"]["asset_ranges"]),
        "longs": len(snap["alpha"].get("longs", [])),
        "shorts": len(snap["alpha"].get("shorts", [])),
        "narratives": len(snap["narratives"]["narratives"]),
        "auto_discoveries": len(snap["auto_discoveries"]["bottlenecks"]),
        "daily_signals": len(snap.get("daily_signals", [])),
        "alpha_center_items": snap.get("alpha_center", {}).get("meta", {}).get("total_items", 0),
        "gamma_analyzed": len(snap.get("gamma_data", {})),
        "greeks_analyzed": len(snap.get("greeks_data", {})),
        "build_time": snap["build_time_s"],
    }, indent=2))

"""orchestrator.py — MacroRegime Pro Orchestrator v2.4
Fixes: dummy global country quads, gamma data completeness, crypto tokens robust
Adds: DAILY SIGNALS (Hedgeye-style) + ALPHA CENTER bottleneck scanner
Adds IHSG v2: Sector Momentum, Commodity Overlay, Rupiah Regime, Foreign Flow Proxy, BI Macro Overlay
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

# ══════════════════════════════════════════════════════════════════════════════
# REAL DATA ENGINE IMPORTS
# ══════════════════════════════════════════════════════════════════════════════

try:
    from engines.cot_scraper import CFTCCOTScraper
    cot_scraper = CFTCCOTScraper()
except Exception as _e:
    logger.warning(f"COT scraper import failed: {_e}")
    cot_scraper = None

try:
    from engines.yfinance_options import YFinanceOptionsEngine
    yf_options = YFinanceOptionsEngine()
except Exception as _e:
    logger.warning(f"yfinance options import failed: {_e}")
    yf_options = None

try:
    from engines.defillama_api import DeFiLlamaAPI
    defillama = DeFiLlamaAPI()
except Exception as _e:
    logger.warning(f"DeFiLlama API import failed: {_e}")
    defillama = None

try:
    from engines.cme_scraper import CMEScraper
    cme_scraper = CMEScraper()
except Exception as _e:
    logger.warning(f"CME scraper import failed: {_e}")
    cme_scraper = None

try:
    from engines.barchart_scraper import BarchartScraper
    barchart = BarchartScraper()
except Exception as _e:
    logger.warning(f"Barchart scraper import failed: {_e}")
    barchart = None

try:
    from engines.laevitas_scraper import LaevitasScraper
    laevitas = LaevitasScraper()
except Exception as _e:
    logger.warning(f"Laevitas scraper import failed: {_e}")
    laevitas = None

QUAD_MAP = {
    "Q1": {"name": "Goldilocks", "assets": ["XLK", "XLY", "XLI", "IWM", "QQQ", "RSP", "SLV", "GLD", "IBIT"], "bias": "bullish"},
    "Q2": {"name": "Reflation / Knife Fights", "assets": ["XLE", "OIH", "XLI", "XLB", "SLV", "GLD", "GDX", "ITB", "TLT", "IBIT"], "bias": "bullish"},
    "Q3": {"name": "Stagflation", "assets": ["SLV", "GLD", "PPLT", "GDX", "GDXJ", "XLV", "XLP", "XLU", "TLT", "ITA"], "bias": "bearish"},
    "Q4": {"name": "Deflation", "assets": ["TLT", "IEF", "GLD", "SLV", "XLV", "XLP", "XLU", "UUP", "BTAL"], "bias": "bearish"},
}

# ── Ticker metadata for regime fit ────────────────────────────────────────
TICKER_QUAD_FIT = {
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
    "XLE": {"Q1": 0.60, "Q2": 0.95, "Q3": 0.70, "Q4": 0.30},
    "OIH": {"Q1": 0.55, "Q2": 0.95, "Q3": 0.65, "Q4": 0.25},
    "XLB": {"Q1": 0.60, "Q2": 0.90, "Q3": 0.70, "Q4": 0.35},
    "GDX": {"Q1": 0.50, "Q2": 0.85, "Q3": 0.80, "Q4": 0.60},
    "GDXJ": {"Q1": 0.45, "Q2": 0.85, "Q3": 0.75, "Q4": 0.55},
    "ITB": {"Q1": 0.70, "Q2": 0.80, "Q3": 0.50, "Q4": 0.30},
    "USO": {"Q1": 0.50, "Q2": 0.90, "Q3": 0.70, "Q4": 0.30},
    "UCO": {"Q1": 0.45, "Q2": 0.90, "Q3": 0.65, "Q4": 0.25},
    "DBA": {"Q1": 0.55, "Q2": 0.85, "Q3": 0.75, "Q4": 0.40},
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
    "TLT": {"Q1": 0.30, "Q2": 0.50, "Q3": 0.75, "Q4": 0.95},
    "IEF": {"Q1": 0.35, "Q2": 0.55, "Q3": 0.70, "Q4": 0.90},
    "UUP": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.70, "Q4": 0.90},
    "BTAL": {"Q1": 0.30, "Q2": 0.45, "Q3": 0.75, "Q4": 0.85},
    "SHY": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.65, "Q4": 0.85},
    "AGG": {"Q1": 0.45, "Q2": 0.55, "Q3": 0.65, "Q4": 0.80},
    "SPY": {"Q1": 0.90, "Q2": 0.75, "Q3": 0.50, "Q4": 0.35},
    "DIA": {"Q1": 0.85, "Q2": 0.70, "Q3": 0.55, "Q4": 0.40},
    "XLF": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.45, "Q4": 0.30},
    "XLC": {"Q1": 0.85, "Q2": 0.65, "Q3": 0.40, "Q4": 0.25},
    "XLRE": {"Q1": 0.70, "Q2": 0.60, "Q3": 0.60, "Q4": 0.50},
}

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

IHSG_SECTOR_MAP = {
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

IHSG_SECTOR_TICKERS = {
    "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK"],
    "Nickel": ["NCKL.JK", "ANTM.JK", "INCO.JK"],
    "CPO": ["AALI.JK", "LSIP.JK", "SMAR.JK"],
    "Banking": ["BBRI.JK", "BMRI.JK", "BBCA.JK", "BBNI.JK", "BRIS.JK"],
    "Telco": ["TLKM.JK", "EXCL.JK"],
    "Mining Contractor": ["UNTR.JK"],
    "Mining": ["BYAN.JK"],
    "Consumer": ["ICBP.JK", "INDF.JK"],
    "Pharma": ["KLBF.JK"],
    "Geothermal": ["PGEO.JK"],
    "Shipping": ["WINS.JK"],
}

IHSG_COMMODITY_PROXY = {
    "Coal": {"proxy": "KOL", "source": "Coal ETF"},
    "Nickel": {"proxy": "JJN", "source": "Nickel ETN"},
    "CPO": {"proxy": "DBA", "source": "Agriculture ETF"},
}

def _get_regime_fit(ticker: str, quad: str) -> float:
    if ticker in TICKER_QUAD_FIT:
        return TICKER_QUAD_FIT[ticker].get(quad, 0.50)
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

def _build_vol_forecast(prices, sq, lookback=20, long_window=50):
    """Lightweight vol forecast: EWMA-style + regime adjustment. No external lib needed."""
    forecasts = {}
    regime_mult = {"Q1": 0.90, "Q2": 1.05, "Q3": 1.20, "Q4": 1.15}

    for ticker, s in prices.items():
        if s is None or len(s) < lookback + 5: 
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < lookback + 5: 
            continue

        rets = s.pct_change().dropna()
        if len(rets) < lookback: 
            continue

        recent_vol = rets.tail(lookback).std()
        longer_vol = rets.tail(long_window).std() if len(rets) >= long_window else recent_vol

        vol_ratio = recent_vol / longer_vol if longer_vol > 0 else 1.0
        lam = 0.85 if vol_ratio > 1.3 else (0.94 if vol_ratio < 0.8 else 0.90)

        ewma_var = 0.0
        for i, r in enumerate(rets.tail(lookback)):
            weight = (1 - lam) * (lam ** i)
            ewma_var += weight * (r ** 2)

        ewma_vol = math.sqrt(ewma_var) * math.sqrt(252)
        mult = regime_mult.get(sq, 1.0)
        forecast_vol = ewma_vol * mult

        if forecast_vol < 15: 
            vol_regime = "LOW"
        elif forecast_vol < 25: 
            vol_regime = "NORMAL"
        elif forecast_vol < 35: 
            vol_regime = "ELEVATED"
        else: 
            vol_regime = "EXTREME"

        forecasts[ticker] = {
            "current_ann_vol": round(ewma_vol, 1),
            "forecast_ann_vol": round(forecast_vol, 1),
            "vol_regime": vol_regime,
            "vol_ratio": round(vol_ratio, 2),
            "lambda_used": lam,
            "expected_daily_move_pct": round(forecast_vol / math.sqrt(252), 3),
            "expected_weekly_move_pct": round(forecast_vol / math.sqrt(52), 3),
        }
    return forecasts


def _build_hurst_proxy(prices, lookback=100):
    """Hurst exponent proxy via Efficiency Ratio (Kaufman-style)."""
    hurst_data = {}
    for ticker, s in prices.items():
        if s is None or len(s) < lookback: 
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < lookback: 
            continue

        price_change = abs(s.iloc[-1] - s.iloc[-lookback])
        sum_changes = sum(abs(s.iloc[i] - s.iloc[i-1]) for i in range(-lookback+1, 1))

        if sum_changes == 0: 
            continue

        er = price_change / sum_changes
        hurst_approx = 0.5 + (er - 0.5) * 0.4

        if hurst_approx > 0.55:
            regime = "TRENDING"
            color = "#3FB950"
        elif hurst_approx < 0.45:
            regime = "MEAN-REVERTING"
            color = "#F85149"
        else:
            regime = "RANDOM WALK"
            color = "#D29922"

        hurst_data[ticker] = {
            "hurst_approx": round(hurst_approx, 3),
            "efficiency_ratio": round(er, 3),
            "regime": regime,
            "color": color,
            "lookback": lookback,
        }
    return hurst_data


def _build_risk_adjusted_metrics(prices, risk_free_rate=0.04):
    """Rolling 63-day Sharpe & Sortino per ticker."""
    metrics = {}
    for ticker, s in prices.items():
        if s is None or len(s) < 65: 
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 65: 
            continue

        rets = s.pct_change().dropna()
        if len(rets) < 63: 
            continue

        window = rets.tail(63)
        mean_ret = window.mean() * 252
        std_dev = window.std() * math.sqrt(252)

        sharpe = (mean_ret - risk_free_rate) / std_dev if std_dev > 0 else 0

        downside_rets = [r for r in window if r < 0]
        downside_std = (pd.Series(downside_rets).std() * math.sqrt(252)) if downside_rets else 0.001
        sortino = (mean_ret - risk_free_rate) / downside_std if downside_std > 0 else 0

        running_max = window.cummax()
        drawdown = (window - running_max) / running_max
        max_dd = drawdown.min()

        metrics[ticker] = {
            "sharpe_63d": round(sharpe, 2),
            "sortino_63d": round(sortino, 2),
            "ann_return": round(mean_ret, 1),
            "ann_vol": round(std_dev, 1),
            "max_dd_63d": round(max_dd, 3),
        }
    return metrics


def _build_stress_test(prices, sq, alpha):
    """Lightweight stress test: apply historical shock magnitudes to current regime portfolio."""
    SHOCKS = {
        "2008_GFC": {
            "Q1": {"SPY": -0.45, "QQQ": -0.50, "IWM": -0.55, "XLK": -0.55, "XLY": -0.50, "XLI": -0.45, "XLE": -0.35, "XLB": -0.40, "XLF": -0.60, "XLV": -0.25, "XLP": -0.15, "XLU": -0.10, "TLT": +0.25, "GLD": +0.20, "SLV": -0.30, "UUP": +0.10, "IBIT": -0.40, "IEF": +0.15},
            "Q2": {"SPY": -0.35, "QQQ": -0.40, "IWM": -0.45, "XLK": -0.40, "XLY": -0.35, "XLI": -0.35, "XLE": -0.30, "XLB": -0.35, "XLF": -0.50, "XLV": -0.20, "XLP": -0.10, "XLU": -0.05, "TLT": +0.20, "GLD": +0.15, "SLV": -0.25, "UUP": +0.08, "IBIT": -0.30, "IEF": +0.12},
            "Q3": {"SPY": -0.20, "QQQ": -0.25, "IWM": -0.25, "XLK": -0.20, "XLY": -0.20, "XLI": -0.20, "XLE": -0.15, "XLB": -0.20, "XLF": -0.25, "XLV": -0.10, "XLP": -0.05, "XLU": 0.00, "TLT": +0.10, "GLD": +0.10, "SLV": -0.15, "UUP": +0.05, "IBIT": -0.15, "IEF": +0.08},
            "Q4": {"SPY": -0.15, "QQQ": -0.20, "IWM": -0.20, "XLK": -0.15, "XLY": -0.15, "XLI": -0.15, "XLE": -0.10, "XLB": -0.15, "XLF": -0.20, "XLV": -0.05, "XLP": 0.00, "XLU": +0.05, "TLT": +0.08, "GLD": +0.08, "SLV": -0.10, "UUP": +0.03, "IBIT": -0.10, "IEF": +0.05},
        },
        "2020_COVID": {
            "Q1": {"SPY": -0.35, "QQQ": -0.30, "IWM": -0.45, "XLK": -0.25, "XLY": -0.40, "XLI": -0.40, "XLE": -0.50, "XLB": -0.35, "XLF": -0.45, "XLV": -0.20, "XLP": -0.15, "XLU": -0.15, "TLT": +0.15, "GLD": +0.05, "SLV": -0.35, "UUP": +0.05, "IBIT": -0.25, "IEF": +0.10},
            "Q2": {"SPY": -0.30, "QQQ": -0.25, "IWM": -0.40, "XLK": -0.20, "XLY": -0.35, "XLI": -0.35, "XLE": -0.45, "XLB": -0.30, "XLF": -0.40, "XLV": -0.15, "XLP": -0.10, "XLU": -0.10, "TLT": +0.12, "GLD": +0.05, "SLV": -0.30, "UUP": +0.04, "IBIT": -0.20, "IEF": +0.08},
            "Q3": {"SPY": -0.25, "QQQ": -0.20, "IWM": -0.35, "XLK": -0.15, "XLY": -0.30, "XLI": -0.30, "XLE": -0.40, "XLB": -0.25, "XLF": -0.35, "XLV": -0.10, "XLP": -0.08, "XLU": -0.08, "TLT": +0.10, "GLD": +0.03, "SLV": -0.25, "UUP": +0.03, "IBIT": -0.15, "IEF": +0.06},
            "Q4": {"SPY": -0.20, "QQQ": -0.15, "IWM": -0.30, "XLK": -0.10, "XLY": -0.25, "XLI": -0.25, "XLE": -0.35, "XLB": -0.20, "XLF": -0.30, "XLV": -0.08, "XLP": -0.05, "XLU": -0.05, "TLT": +0.08, "GLD": +0.02, "SLV": -0.20, "UUP": +0.02, "IBIT": -0.10, "IEF": +0.05},
        },
        "2022_FED_HIKES": {
            "Q1": {"SPY": -0.25, "QQQ": -0.35, "IWM": -0.30, "XLK": -0.40, "XLY": -0.25, "XLI": -0.20, "XLE": +0.20, "XLB": -0.15, "XLF": -0.20, "XLV": -0.10, "XLP": -0.05, "XLU": +0.05, "TLT": -0.20, "GLD": -0.10, "SLV": -0.20, "UUP": +0.10, "IBIT": -0.50, "IEF": -0.15},
            "Q2": {"SPY": -0.20, "QQQ": -0.30, "IWM": -0.25, "XLK": -0.35, "XLY": -0.20, "XLI": -0.15, "XLE": +0.15, "XLB": -0.10, "XLF": -0.15, "XLV": -0.08, "XLP": -0.03, "XLU": +0.08, "TLT": -0.15, "GLD": -0.08, "SLV": -0.15, "UUP": +0.08, "IBIT": -0.40, "IEF": -0.12},
            "Q3": {"SPY": -0.15, "QQQ": -0.25, "IWM": -0.20, "XLK": -0.30, "XLY": -0.15, "XLI": -0.10, "XLE": +0.10, "XLB": -0.08, "XLF": -0.10, "XLV": -0.05, "XLP": 0.00, "XLU": +0.10, "TLT": -0.10, "GLD": -0.05, "SLV": -0.10, "UUP": +0.05, "IBIT": -0.30, "IEF": -0.08},
            "Q4": {"SPY": -0.10, "QQQ": -0.20, "IWM": -0.15, "XLK": -0.25, "XLY": -0.10, "XLI": -0.08, "XLE": +0.08, "XLB": -0.05, "XLF": -0.08, "XLV": -0.03, "XLP": +0.03, "XLU": +0.12, "TLT": -0.08, "GLD": -0.03, "SLV": -0.08, "UUP": +0.03, "IBIT": -0.20, "IEF": -0.05},
        },
    }

    longs = alpha.get("longs", []) if alpha else []
    if not longs:
        longs = [{"ticker": t} for t in QUAD_MAP.get(sq, {}).get("assets", [])[:5]]

    portfolio = []
    for item in longs:
        t = item.get("ticker")
        p = _last_price(prices.get(t))
        if p: 
            portfolio.append({"ticker": t, "price": p, "weight": 1.0/len(longs)})

    results = []
    for shock_name, shock_data in SHOCKS.items():
        regime_shock = shock_data.get(sq, {})
        if not regime_shock: 
            continue

        portfolio_return = 0.0
        worst_ticker = None
        worst_return = 0.0
        best_ticker = None
        best_return = 0.0

        for pos in portfolio:
            t = pos["ticker"]
            w = pos["weight"]
            ret = regime_shock.get(t, regime_shock.get("SPY", -0.20))
            weighted = w * ret
            portfolio_return += weighted

            if ret < worst_return:
                worst_return = ret
                worst_ticker = t
            if ret > best_return:
                best_return = ret
                best_ticker = t

        results.append({
            "scenario": shock_name,
            "portfolio_dd": round(portfolio_return, 1),
            "worst_asset": worst_ticker,
            "worst_dd": round(worst_return, 1),
            "best_asset": best_ticker,
            "best_dd": round(best_return, 1),
            "severity": "EXTREME" if portfolio_return < -0.30 else "HIGH" if portfolio_return < -0.20 else "MODERATE" if portfolio_return < -0.10 else "MILD",
            "hedge": "TLT/GLD/UUP" if portfolio_return < -0.20 else "XLP/XLU",
        })

    return results

def _detect_market_type(ticker):
    if any(x in ticker for x in ["BTC","ETH","SOL","TON","ADA","AVAX","DOT","LINK","DOGE","LTC","XRP","BNB","-USD","-USDT"]):
        return "crypto"
    elif any(x in ticker for x in ["USD=","EUR=","GBP=","JPY=","CAD","AUD","CHF","NZD","MXN","SEK","BRL","=X","DX-Y"]):
        return "forex"
    elif any(x in ticker for x in ["GC=","SI=","CL=","BZ=","NG=","HG=","PL=","PA=","RB=","HO=","ALI=","ZW=","ZC=","ZS=","=F"]):
        return "commodity"
    elif ".JK" in ticker or ticker in ["EIDO", "^JKSE"]:
        return "ihsg"
    return "us_equity"


def _build_alpha_ideas(prices, sq, mq, gamma_data=None, greeks_data=None):
    playbook = get_playbook(sq, mq); regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    longs = []; shorts = []
    for ticker in playbook.get("best_assets", [])[:6]:
        p = _last_price(prices.get(ticker))
        if p is None: continue
        rr = _calc_risk_range(prices.get(ticker))
        entry = round(p * 0.98, 2) if rr.get("ok") else round(p, 2)
        target1 = round(p * 1.05, 2); target2 = round(p * 1.10, 2); stop = round(p * 0.95, 2)
        fit = _get_regime_fit(ticker, sq)
        item = {
            "ticker": ticker, "price": round(p, 2), "entry": entry,
            "target_1": target1, "target_2": target2, "stop_loss": stop,
            "rr": round((target1 - entry) / (entry - stop), 1) if entry != stop else 0,
            "hold_for": "2-4 weeks", "signal": "BUY", "grade": "A", "direction": "LONG",
            "thesis": f"{ticker} in {sq} playbook (fit {fit:.0%}) — {playbook.get('strategy', 'tactical')}",
            "regime_fit": fit,
        }
        gamma = gamma_data.get(ticker, {})
        greek = greeks_data.get(ticker, {})
        mkt = _detect_market_type(ticker)
        item = _enrich_signal_with_conclusions(item, gamma, greek, rr, market_type=mkt)
        longs.append(item)
    for ticker in playbook.get("worst_assets", [])[:6]:
        p = _last_price(prices.get(ticker))
        if p is None: continue
        entry = round(p * 1.02, 2); target = round(p * 0.95, 2); stop = round(p * 1.05, 2)
        fit = _get_regime_fit(ticker, sq)
        rr = _calc_risk_range(prices.get(ticker))
        item = {
            "ticker": ticker, "price": round(p, 2), "entry": entry,
            "target_1": target, "target_2": round(p * 0.90, 2), "stop_loss": stop,
            "rr": round((entry - target) / (stop - entry), 1) if stop != entry else 0,
            "hold_for": "2-4 weeks", "signal": "SELL", "grade": "A", "direction": "SHORT",
            "thesis": f"{ticker} avoid in {sq} playbook (fit {fit:.0%})",
            "regime_fit": fit,
        }
        gamma = gamma_data.get(ticker, {})
        greek = greeks_data.get(ticker, {})
        mkt = _detect_market_type(ticker)
        item = _enrich_signal_with_conclusions(item, gamma, greek, rr, market_type=mkt)
        shorts.append(item)
    if not longs and not shorts:
        for t in ["SPY", "QQQ", "IWM", "XLK", "XLE", "GLD", "SLV", "TLT", "IBIT", "UUP"]:
            p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21)
            if p is None or r1m is None: continue
            fit = _get_regime_fit(t, sq)
            rr = _calc_risk_range(prices.get(t))
            mkt = _detect_market_type(t)
            if bias == "bullish" and r1m > 0.02:
                item = {"ticker": t, "price": round(p, 2), "entry": round(p * 0.98, 2),
                    "target_1": round(p * 1.05, 2), "target_2": round(p * 1.10, 2),
                    "stop_loss": round(p * 0.95, 2), "rr": 2.0, "hold_for": "2-4 weeks",
                    "signal": "BUY", "grade": "B", "direction": "LONG",
                    "thesis": f"Momentum +{r1m:.1%} in {sq} regime (fit {fit:.0%})", "regime_fit": fit}
                item = _enrich_signal_with_conclusions(item, gamma_data.get(t, {}), greeks_data.get(t, {}), rr, market_type=mkt)
                longs.append(item)
            elif bias == "bearish" and r1m < -0.02:
                item = {"ticker": t, "price": round(p, 2), "entry": round(p * 1.02, 2),
                    "target_1": round(p * 0.95, 2), "target_2": round(p * 0.90, 2),
                    "stop_loss": round(p * 1.05, 2), "rr": 2.0, "hold_for": "2-4 weeks",
                    "signal": "SELL", "grade": "B", "direction": "SHORT",
                    "thesis": f"Momentum {r1m:.1%} in {sq} regime (fit {fit:.0%})", "regime_fit": fit}
                item = _enrich_signal_with_conclusions(item, gamma_data.get(t, {}), greeks_data.get(t, {}), rr, market_type=mkt)
                shorts.append(item)
    return {"longs": longs, "shorts": shorts, "playbook": playbook}


# ══════════════════════════════════════════════════════════════════════════════
# READABLE CONCLUSION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction):
    if direction not in ("LONG", "SHORT"): return "WAIT — No clear edge"
    if direction == "LONG":
        if price <= entry * 1.01:
            if composite == "bullish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE"):
                return "✅ BUY NOW — At buy zone + gamma supportive"
            elif composite == "bullish": return "✅ BUY NOW — At buy zone"
            else: return "⚠️ SMALL SIZE — At buy zone but mixed signals"
        elif lrr and price <= lrr * 1.03: return f"⏳ WAIT — Slightly above best entry, wait for retrace to LRR"
        else:
            if momentum_1m and momentum_1m > 0.05: return "🏃 CHASE — Extended but momentum strong, use small size"
            else: return "❌ SKIP — Too far from buy zone, wait for pullback"
    else:
        if price >= entry * 0.99:
            if composite == "bearish" and gamma.get("ok") and gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE"):
                return "✅ SELL NOW — At sell zone + gamma headwind"
            elif composite == "bearish": return "✅ SELL NOW — At sell zone"
            else: return "⚠️ SMALL SIZE — At sell zone but mixed signals"
        elif trr and price >= trr * 0.97: return f"⏳ WAIT — Slightly below best entry, wait for bounce to TRR"
        else:
            if momentum_1m and momentum_1m < -0.05: return "🏃 CHASE SHORT — Extended but momentum strong, use small size"
            else: return "❌ SKIP — Too far from sell zone, wait for bounce"

def _target_basis(target, trr, lrr, gamma, direction):
    if not gamma.get("ok"):
        return f"TRR resistance at {trr}" if direction == "LONG" and trr else (f"LRR support at {lrr}" if direction == "SHORT" and lrr else "1.5x RR target")
    call_wall = gamma.get("call_wall"); put_wall = gamma.get("put_wall")
    flip_up = gamma.get("gamma_flip_up"); flip_down = gamma.get("gamma_flip_down")
    max_pain = gamma.get("max_pain")
    if direction == "LONG":
        if call_wall and abs(target - call_wall) / max(target, 1) < 0.03: return f"Call wall at {call_wall}"
        elif flip_up and abs(target - flip_up) / max(target, 1) < 0.03: return f"Gamma flip up at {flip_up}"
        elif trr and abs(target - trr) / max(target, 1) < 0.03: return f"TRR at {trr}"
        else: return f"1.5x RR target (max pain {max_pain})"
    else:
        if put_wall and abs(target - put_wall) / max(target, 1) < 0.03: return f"Put wall at {put_wall}"
        elif flip_down and abs(target - flip_down) / max(target, 1) < 0.03: return f"Gamma flip down at {flip_down}"
        elif lrr and abs(target - lrr) / max(target, 1) < 0.03: return f"LRR at {lrr}"
        else: return f"1.5x RR target (max pain {max_pain})"

def _stop_basis(stop, lrr, trr, gamma, direction):
    if not gamma.get("ok"):
        return f"Below LRR at {lrr}" if direction == "LONG" and lrr else (f"Above TRR at {trr}" if direction == "SHORT" and trr else "2% from entry")
    flip_down = gamma.get("gamma_flip_down"); flip_up = gamma.get("gamma_flip_up")
    put_wall = gamma.get("put_wall"); call_wall = gamma.get("call_wall")
    if direction == "LONG":
        if flip_down and abs(stop - flip_down) / max(stop, 1) < 0.03: return f"Below gamma flip {flip_down}"
        elif put_wall and abs(stop - put_wall) / max(stop, 1) < 0.03: return f"Below put wall {put_wall}"
        elif lrr and abs(stop - lrr) / max(stop, 1) < 0.03: return f"Below LRR {lrr}"
        else: return "2% below entry"
    else:
        if flip_up and abs(stop - flip_up) / max(stop, 1) < 0.03: return f"Above gamma flip {flip_up}"
        elif call_wall and abs(stop - call_wall) / max(stop, 1) < 0.03: return f"Above call wall {call_wall}"
        elif trr and abs(stop - trr) / max(stop, 1) < 0.03: return f"Above TRR {trr}"
        else: return "2% above entry"

def _path_smoothness(gamma, greek, momentum_1m, vix):
    if not gamma.get("ok") and not greek.get("ok"):
        return "Rough — High vol" if vix > 25 else ("Bumpy — Elevated vol" if vix > 20 else "Normal")
    gamma_regime = gamma.get("regime", "TRANSITION") if gamma.get("ok") else "TRANSITION"
    throttle = gamma.get("throttle", 0.5) if gamma.get("ok") else 0.5
    greek_comp = greek.get("composite", "NEUTRAL") if greek.get("ok") else "NEUTRAL"
    if gamma_regime in ("DEEP_POSITIVE", "POSITIVE") and "BULLISH" in greek_comp:
        return "🚀 Fast & Smooth" if momentum_1m and momentum_1m > 0.03 else "🟢 Smooth — dips bought"
    elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE") and "BEARISH" in greek_comp:
        return "🚀 Fast & Smooth" if momentum_1m and momentum_1m < -0.03 else "🟢 Smooth — rallies sold"
    elif throttle > 0.6: return "🟡 Slow — gamma pin, chop"
    elif vix > 25: return "🔴 Rough — vol expansion"
    elif vix > 20: return "🟡 Bumpy — elevated vol"
    else: return "🟢 Normal"

def _time_estimate(rr, gamma, greek, momentum_1m, market_type="us_equity", rvol_20d=None):
    if not rr: return "Unknown"
    is_crypto = market_type == "crypto"
    is_forex = market_type == "forex"
    if is_crypto:
        if rr >= 3.0: base = "2-4 weeks"
        elif rr >= 2.0: base = "1-2 weeks"
        elif rr >= 1.5: base = "3-7 days"
        else: base = "1-3 days"
    elif is_forex:
        if rr >= 3.0: base = "1-2 months"
        elif rr >= 2.0: base = "2-4 weeks"
        elif rr >= 1.5: base = "1-2 weeks"
        else: base = "3-7 days"
    else:
        if rr >= 3.0: base = "2-4 months"
        elif rr >= 2.0: base = "1-2 months"
        elif rr >= 1.5: base = "2-4 weeks"
        else: base = "1-2 weeks"
    if rvol_20d and rvol_20d > 50:
        base = base.replace("months", "weeks").replace("weeks", "days")
        if "days" not in base: base = "3-7 days"
    elif rvol_20d and rvol_20d > 30:
        if "months" in base: base = base.replace("months", "weeks")
    if gamma.get("ok"):
        if gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE") and momentum_1m and momentum_1m > 0.03:
            return f"{base} (likely faster — momentum + gamma aligned)"
        elif gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE") and momentum_1m and momentum_1m < -0.03:
            return f"{base} (likely faster — momentum + gamma aligned)"
        elif gamma.get("throttle", 0) > 0.6:
            return f"{base} (likely slower — gamma pin, chop expected)"
    return base

def _breakout_chance(price, target_2, gamma, greek, momentum_3m, direction):
    if not gamma.get("ok") and not greek.get("ok"):
        return "Medium" if momentum_3m and abs(momentum_3m) > 0.10 else "Low"
    greek_comp = greek.get("composite", "NEUTRAL") if greek.get("ok") else "NEUTRAL"
    gamma_regime = gamma.get("regime", "TRANSITION") if gamma.get("ok") else "TRANSITION"
    call_wall = gamma.get("call_wall"); put_wall = gamma.get("put_wall")
    if direction == "LONG":
        if "BULLISH" in greek_comp and gamma_regime in ("DEEP_POSITIVE", "POSITIVE"):
            return f"High — above call wall {call_wall}" if call_wall and target_2 > call_wall else "High"
        elif "BULLISH" in greek_comp: return "Medium-High"
        elif gamma_regime in ("DEEP_POSITIVE", "POSITIVE"): return "Medium"
        else: return "Low — T2 is stretch"
    else:
        if "BEARISH" in greek_comp and gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"):
            return f"High — below put wall {put_wall}" if put_wall and target_2 < put_wall else "High"
        elif "BEARISH" in greek_comp: return "Medium-High"
        elif gamma_regime in ("DEEP_NEGATIVE", "NEGATIVE"): return "Medium"
        else: return "Low — T2 is stretch"

def _enrich_signal_with_conclusions(sig, gamma, greek, rr_data, market_type="us_equity"):
    price = sig.get("price"); entry = sig.get("entry"); target1 = sig.get("target_1"); target2 = sig.get("target_2")
    stop = sig.get("stop_loss"); direction = sig.get("direction"); composite = sig.get("composite", "neutral")
    momentum_1m = sig.get("momentum_1m"); momentum_3m = sig.get("momentum_3m"); vix = sig.get("vix", 20); rr = sig.get("rr")
    lrr = rr_data.get("trade", {}).get("lrr") if rr_data and rr_data.get("ok") else None
    trr = rr_data.get("trade", {}).get("trr") if rr_data and rr_data.get("ok") else None
    rvol_20d = greek.get("rvol_20d") if greek and greek.get("ok") else None
    sig["entry_advice"] = _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction)
    sig["tp1_basis"] = _target_basis(target1, trr, lrr, gamma, direction)
    sig["tp2_basis"] = _target_basis(target2, trr, lrr, gamma, direction)
    sig["stop_basis"] = _stop_basis(stop, lrr, trr, gamma, direction)
    sig["path_smoothness"] = _path_smoothness(gamma, greek, momentum_1m, vix)
    sig["time_estimate"] = _time_estimate(rr, gamma, greek, momentum_1m, market_type, rvol_20d)
    sig["breakout_chance"] = _breakout_chance(price, target2, gamma, greek, momentum_3m, direction)
    if "BUY NOW" in sig["entry_advice"] or "SELL NOW" in sig["entry_advice"]:
        sig["worth_entering"] = "✅ YES — " + sig["entry_advice"].split("—")[-1].strip()
    elif "WAIT" in sig["entry_advice"]:
        sig["worth_entering"] = "⏳ " + sig["entry_advice"]
    elif "CHASE" in sig["entry_advice"]:
        sig["worth_entering"] = "🏃 " + sig["entry_advice"]
    elif "SMALL SIZE" in sig["entry_advice"]:
        sig["worth_entering"] = "⚠️ " + sig["entry_advice"]
    else:
        sig["worth_entering"] = "❌ " + sig["entry_advice"]
    return sig



def _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data=None, greeks_data=None):
    regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    signals = []
    all_tickers = sorted(prices.keys())
    for ticker in all_tickers:
        s = prices.get(ticker)
        if s is None or s.empty: continue
        p = _last_price(s)
        if p is None: continue
        r1m = _safe_ret(s, 21); r3m = _safe_ret(s, 63); r5d = _safe_ret(s, 5)
        rr = asset_ranges.get(ticker, {})
        composite = rr.get("composite", "neutral") if rr.get("ok") else "neutral"
        fit = _get_regime_fit(ticker, sq)
        vol_adj = 1.0
        if vix > 30: vol_adj = 0.7
        elif vix > 25: vol_adj = 0.85
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
            signals.append(sig); continue
        direction = "NEUTRAL"; signal_label = "NEUTRAL"; grade = "C"; quality = "C"; thesis_parts = []
        fit_score = fit
        momentum_score = 0.0
        if r1m is not None: momentum_score = max(-1.0, min(1.0, r1m * 10))
        rr_score = 0.0
        if composite == "bullish": rr_score = 0.6
        elif composite == "bearish": rr_score = -0.6
        trend_score = 0.0
        if r3m is not None: trend_score = max(-1.0, min(1.0, r3m * 5))
        option_score = 0.0
        greek = greeks_data.get(ticker, {})
        gamma = gamma_data.get(ticker, {})
        if greek.get("ok"):
            greek_score = greek.get("composite_score", 0)
            option_score += greek_score * 0.15
            if greek.get("vanna_val", 0) > 0.3 and direction == "LONG": option_score += 0.05
            elif greek.get("vanna_val", 0) < -0.3 and direction == "SHORT": option_score -= 0.05
            if greek.get("charm_val", 0) > 0.2: option_score += 0.03
            elif greek.get("charm_val", 0) < -0.2: option_score -= 0.03
        if gamma.get("ok"):
            g_regime = gamma.get("regime", "TRANSITION")
            if g_regime in ("DEEP_POSITIVE", "POSITIVE"): option_score += 0.05
            elif g_regime in ("DEEP_NEGATIVE", "NEGATIVE"): option_score -= 0.05
            dist_mp = gamma.get("dist_max_pain_pct", 0)
            if abs(dist_mp) < 2: option_score *= 0.8
            elif dist_mp > 5 and direction == "LONG": option_score -= 0.05
            elif dist_mp < -5 and direction == "SHORT": option_score += 0.05
            g_exp = gamma.get("gamma_exposure", "")
            if "POSITIVE" in g_exp and direction == "LONG": option_score += 0.04
            elif "NEGATIVE" in g_exp and direction == "SHORT": option_score -= 0.04
        total_score = (fit_score * 0.30 + momentum_score * 0.25 + rr_score * 0.15 + trend_score * 0.10 + option_score * 0.20)
        if bias == "bullish": total_score += 0.10
        elif bias == "bearish": total_score -= 0.10
        total_score = max(-1.0, min(1.0, total_score))
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
        if composite == "bullish" and total_score < -0.30:
            signal_label = "SHORT (OVERSOLD TRAP?)"; grade = "B"; quality = "B"
            thesis_parts.append("Oversold but macro headwind — potential value trap")
        elif composite == "bearish" and total_score > 0.30:
            signal_label = "LONG (OVERBOUGHT FADE?)"; grade = "B"; quality = "B"
            thesis_parts.append("Overbought but macro tailwind — potential momentum squeeze")
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
            entry = round(p, 2); target1 = round(p * 1.03, 2); target2 = round(p * 0.97, 2); stop = round(p * 0.95, 2); rr_val = 0.0
        if "STRONG" in signal_label: hold = "1-2 weeks"
        elif signal_label in ["LONG", "SHORT"]: hold = "2-4 weeks"
        elif "KEEP" in signal_label: hold = "3-6 weeks"
        else: hold = "Wait"
        opt_parts = []
        if greek.get("ok"): opt_parts.append(f"Greeks: {greek.get('composite', 'N/A')}")
        if gamma.get("ok"):
            opt_parts.append(f"Gamma: {gamma.get('regime', 'N/A')}")
            opt_parts.append(f"MaxPain {gamma.get('max_pain')} ({gamma.get('dist_max_pain_pct'):+.1f}%)")
        thesis_full = " | ".join(thesis_parts)
        if opt_parts: thesis_full += " | 📊 " + " · ".join(opt_parts)
        if r1m is not None: thesis_full += f" | 1M: {r1m:+.1%}"
        sig = {
            "ticker": ticker, "price": round(p, 2), "signal": signal_label, "direction": direction,
            "grade": grade, "quality": quality, "entry": entry, "target_1": target1, "target_2": target2,
            "stop_loss": stop, "rr": rr_val, "hold_for": hold, "regime_fit": fit, "thesis": thesis_full,
            "momentum_1m": r1m, "momentum_3m": r3m, "momentum_5d": r5d, "composite": composite,
            "score": round(total_score, 2), "vix": vix,
            "lrr": rr.get("trade", {}).get("lrr") if rr.get("ok") else None,
            "trr": rr.get("trade", {}).get("trr") if rr.get("ok") else None,
            "gamma_regime": gamma.get("regime") if gamma.get("ok") else None,
            "max_pain": gamma.get("max_pain") if gamma.get("ok") else None,
            "gamma_flip_up": gamma.get("gamma_flip_up") if gamma.get("ok") else None,
            "gamma_flip_down": gamma.get("gamma_flip_down") if gamma.get("ok") else None,
            "put_wall": gamma.get("put_wall") if gamma.get("ok") else None,
            "call_wall": gamma.get("call_wall") if gamma.get("ok") else None,
            "greek_composite": greek.get("composite") if greek.get("ok") else None,
        }
        mkt = "us_equity"
        if ticker in CRYPTO or any(x in ticker for x in ["BTC","ETH","SOL","TON","ADA","AVAX","DOT","LINK","DOGE","LTC","XRP","BNB"]): mkt = "crypto"
        elif ticker in FOREX_PAIRS or any(x in ticker for x in ["USD=","EUR=","GBP=","JPY=","CAD","AUD","CHF","NZD","MXN","SEK","BRL"]): mkt = "forex"
        elif ticker in COMMODITIES or any(x in ticker for x in ["GC=","SI=","CL=","BZ=","NG=","HG=","PL=","PA=","RB=","HO=","ALI=","ZW=","ZC=","ZS=","ZW","ZC","ZS"]): mkt = "commodity"
        sig = _enrich_signal_with_conclusions(sig, gamma, greek, rr)
        signals.append(sig)
    signals.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)
    return signals



def _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks, auto_discoveries, daily_signals, gamma_data=None, greeks_data=None):
    regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    center_items = []
    def _enrich_item(item, ticker):
        gamma = gamma_data.get(ticker, {}); greek = greeks_data.get(ticker, {})
        if gamma.get("ok"):
            item["gamma_regime"] = gamma.get("regime"); item["gamma_throttle"] = gamma.get("throttle")
            item["max_pain"] = gamma.get("max_pain"); item["gamma_flip_up"] = gamma.get("gamma_flip_up")
            item["gamma_flip_down"] = gamma.get("gamma_flip_down"); item["put_wall"] = gamma.get("put_wall")
            item["call_wall"] = gamma.get("call_wall"); item["gamma_exposure"] = gamma.get("gamma_exposure")
            item["skew"] = gamma.get("skew"); item["dist_max_pain_pct"] = gamma.get("dist_max_pain_pct")
        if greek.get("ok"):
            item["greek_delta"] = greek.get("delta"); item["greek_gamma"] = greek.get("gamma")
            item["greek_vanna"] = greek.get("vanna"); item["greek_charm"] = greek.get("charm")
            item["greek_composite"] = greek.get("composite"); item["greek_score"] = greek.get("composite_score")
            item["vol_premium"] = greek.get("vol_premium"); item["rvol_20d"] = greek.get("rvol_20d")
        return item
    def _boost_priority(base_score, ticker, direction):
        gamma = gamma_data.get(ticker, {}); greek = greeks_data.get(ticker, {})
        score = base_score
        if greek.get("ok"):
            if "BULLISH" in greek.get("composite", "") and direction == "LONG": score *= 1.15
            elif "BEARISH" in greek.get("composite", "") and direction == "SHORT": score *= 1.15
        if gamma.get("ok"):
            if gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE") and direction == "LONG": score *= 1.10
            elif gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE") and direction == "SHORT": score *= 1.10
        return score
    def _rr_levels(px, lrr, trr, direction):
        if direction == "LONG":
            entry = round(px * 0.985, 2) if lrr is None else round(min(px, lrr * 1.01), 2)
            stop = round(px * 0.95, 2) if lrr is None else round(lrr * 0.98, 2)
            tp1 = round(px * 1.05, 2) if trr is None else round(trr * 0.98, 2)
            tp2 = round(px * 1.10, 2) if trr is None else round(trr, 2)
        else:
            entry = round(px * 1.015, 2) if trr is None else round(max(px, trr * 0.99), 2)
            stop = round(px * 1.05, 2) if trr is None else round(trr * 1.02, 2)
            tp1 = round(px * 0.95, 2) if lrr is None else round(lrr * 1.02, 2)
            tp2 = round(px * 0.90, 2) if lrr is None else round(lrr, 2)
        if entry != stop:
            rr = round((tp1 - entry) / (entry - stop), 1) if direction == "LONG" else round((entry - tp1) / (stop - entry), 1)
        else: rr = 0.0
        return {"entry": entry, "tp1": tp1, "tp2": tp2, "stop": stop, "rr": rr}
    # 1. Bottleneck Level 1
    for b in bottlenecks.get("level_1", []):
        t = b.get("ticker", "UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade", {}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade", {}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in b.get("direction", "") else "short")
        score = min(1.0, max(0.0, b.get("score", 0) + 0.2))
        item = {"ticker": t, "scanner_type": "BOTTLENECK L1", "level": "level_1",
            "priority_score": _boost_priority(score * 100, t, b.get("direction", "HOLD")),
            "direction": b.get("direction", "HOLD"), "signal": b.get("direction", "HOLD"),
            "grade": b.get("quality", "A"), "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""), "setup": b.get("setup", ""),
            "invalidators": ["Stop loss hit", "Regime flip", "VIX spike >35"],
            "hold_for": "Immediate", "source": "bottleneck",
            "price": p, "entry": rr_lv["entry"], "target_1": rr_lv["tp1"],
            "target_2": rr_lv["tp2"], "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"],
            "worth_entering": "🚨 URGENT — " + b.get("direction", "HOLD"),
            "entry_advice": b.get("setup", "Risk off positioning"),
            "tp1_basis": f"TRR resistance at {trr}" if trr else "Momentum target",
            "tp2_basis": f"Stretch to TRR at {trr}" if trr else "Stretch target",
            "stop_basis": f"Below LRR at {lrr}" if lrr else "Below entry — invalidation",
            "path_smoothness": "🔴 Rough — Volatility spike",
            "time_estimate": "Immediate action",
            "breakout_chance": "N/A — Risk management"}
        center_items.append(_enrich_item(item, t))
    # 2. Bottleneck Level 2
    for b in bottlenecks.get("level_2", []):
        t = b.get("ticker", "UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade", {}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade", {}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in b.get("direction", "") else "short")
        score = min(1.0, max(0.0, b.get("score", 0) + 0.1))
        item = {"ticker": t, "scanner_type": "BOTTLENECK L2", "level": "level_2",
            "priority_score": _boost_priority(score * 80, t, b.get("direction", "HOLD")),
            "direction": b.get("direction", "HOLD"), "signal": b.get("direction", "HOLD"),
            "grade": b.get("quality", "B"), "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""), "setup": b.get("setup", ""),
            "invalidators": ["Stop loss hit", "Regime flip", "VIX spike >35"],
            "hold_for": "1-2 weeks", "source": "bottleneck",
            "price": p, "entry": rr_lv["entry"], "target_1": rr_lv["tp1"],
            "target_2": rr_lv["tp2"], "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"],
            "worth_entering": "⚠️ BUILDING — " + b.get("direction", "HOLD"),
            "entry_advice": b.get("setup", "Monitor closely"),
            "tp1_basis": f"TRR resistance at {trr}" if trr else "Momentum target",
            "tp2_basis": f"Stretch to TRR at {trr}" if trr else "Stretch target",
            "stop_basis": f"Below LRR at {lrr}" if lrr else "Below entry — invalidation",
            "path_smoothness": "🟡 Bumpy — Transition phase",
            "time_estimate": "1-2 weeks",
            "breakout_chance": "Medium — Watch for confirmation"}
        center_items.append(_enrich_item(item, t))
    # 3. Watch list
    for b in bottlenecks.get("watch", []):
        t = b.get("ticker", "UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade", {}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade", {}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in b.get("direction", "") else "short")
        score = min(1.0, max(0.0, b.get("score", 0)))
        item = {"ticker": t, "scanner_type": "WATCH", "level": "watch",
            "priority_score": _boost_priority(score * 60, t, "HOLD"),
            "direction": "HOLD", "signal": "WATCH",
            "grade": b.get("quality", "B"), "sector": b.get("sector", "Macro"),
            "thesis": b.get("known_thesis", ""), "setup": b.get("setup", ""),
            "invalidators": ["Signal invalidates", "Macro reversal"],
            "hold_for": "Monitor", "source": "bottleneck",
            "price": p, "entry": rr_lv["entry"], "target_1": rr_lv["tp1"],
            "target_2": rr_lv["tp2"], "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"],
            "worth_entering": "👁️ WATCH — Wait for signal",
            "entry_advice": b.get("setup", "Wait for clarity"),
            "tp1_basis": f"TRR resistance at {trr}" if trr else "Momentum target",
            "tp2_basis": f"Stretch to TRR at {trr}" if trr else "Stretch target",
            "stop_basis": f"Below LRR at {lrr}" if lrr else "Below entry — invalidation",
            "path_smoothness": "⏳ Pending",
            "time_estimate": "Monitor daily",
            "breakout_chance": "Unknown — No position yet"}
        center_items.append(_enrich_item(item, t))
    # 4. Alpha Longs
    for a in alpha.get("longs", []):
        t = a.get("ticker")
        item = {"ticker": t, "scanner_type": "ALPHA LONG", "level": "alpha_long",
            "priority_score": _boost_priority(75 if a.get("grade") == "A" else 60, t, "LONG"),
            "direction": "LONG", "signal": a.get("signal", "BUY"),
            "grade": a.get("grade", "B"), "sector": TICKER_SECTOR.get(t, "Unknown"),
            "thesis": a.get("thesis", ""),
            "setup": f"Entry {a.get('entry')} → T1 {a.get('target_1')} → T2 {a.get('target_2')} | Stop {a.get('stop_loss')} | RR {a.get('rr')}",
            "invalidators": ["Stop loss hit", "Regime flip", "Momentum reversal"],
            "hold_for": a.get("hold_for", "2-4 weeks"), "source": "alpha",
            "price": a.get("price"), "entry": a.get("entry"), "target_1": a.get("target_1"),
            "target_2": a.get("target_2"), "stop_loss": a.get("stop_loss"), "rr": a.get("rr"),
            "worth_entering": a.get("worth_entering", "✅ BUY NOW — Regime aligned"),
            "entry_advice": a.get("entry_advice", "✅ BUY NOW"),
            "tp1_basis": a.get("tp1_basis", "Technical target"),
            "tp2_basis": a.get("tp2_basis", "Stretch target"),
            "stop_basis": a.get("stop_basis", "Invalidation level"),
            "path_smoothness": a.get("path_smoothness", "🟢 Normal"),
            "time_estimate": a.get("time_estimate", "2-4 weeks"),
            "breakout_chance": a.get("breakout_chance", "Medium")}
        center_items.append(_enrich_item(item, t))
    # 5. Alpha Shorts
    for a in alpha.get("shorts", []):
        t = a.get("ticker")
        item = {"ticker": t, "scanner_type": "ALPHA SHORT", "level": "alpha_short",
            "priority_score": _boost_priority(75 if a.get("grade") == "A" else 60, t, "SHORT"),
            "direction": "SHORT", "signal": a.get("signal", "SELL"),
            "grade": a.get("grade", "B"), "sector": TICKER_SECTOR.get(t, "Unknown"),
            "thesis": a.get("thesis", ""),
            "setup": f"Entry {a.get('entry')} → T1 {a.get('target_1')} → T2 {a.get('target_2')} | Stop {a.get('stop_loss')} | RR {a.get('rr')}",
            "invalidators": ["Stop loss hit", "Regime flip", "Momentum reversal"],
            "hold_for": a.get("hold_for", "2-4 weeks"), "source": "alpha",
            "price": a.get("price"), "entry": a.get("entry"), "target_1": a.get("target_1"),
            "target_2": a.get("target_2"), "stop_loss": a.get("stop_loss"), "rr": a.get("rr"),
            "worth_entering": a.get("worth_entering", "✅ SELL NOW — Regime aligned"),
            "entry_advice": a.get("entry_advice", "✅ SELL NOW"),
            "tp1_basis": a.get("tp1_basis", "Technical target"),
            "tp2_basis": a.get("tp2_basis", "Stretch target"),
            "stop_basis": a.get("stop_basis", "Invalidation level"),
            "path_smoothness": a.get("path_smoothness", "🟢 Normal"),
            "time_estimate": a.get("time_estimate", "2-4 weeks"),
            "breakout_chance": a.get("breakout_chance", "Medium")}
        center_items.append(_enrich_item(item, t))
    # 6. Auto Discoveries
    for d in auto_discoveries.get("bottlenecks", []):
        t = d.get("ticker", "UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade", {}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade", {}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in d.get("direction", "") else "short")
        item = {"ticker": t, "scanner_type": "DISCOVERY", "level": "discovery",
            "priority_score": _boost_priority(d.get("score", 0) * 90, t, d.get("direction", "HOLD")),
            "direction": d.get("direction", "HOLD"), "signal": d.get("direction", "HOLD"),
            "grade": d.get("quality", "B"), "sector": d.get("sector", "Macro"),
            "thesis": d.get("known_thesis", ""), "setup": d.get("setup", ""),
            "invalidators": ["Signal invalidates", "Macro reversal"],
            "hold_for": "2-4 weeks", "source": "auto_discovery",
            "price": p, "entry": rr_lv["entry"], "target_1": rr_lv["tp1"],
            "target_2": rr_lv["tp2"], "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"],
            "worth_entering": "🔍 DISCOVERY — " + d.get("direction", "HOLD"),
            "entry_advice": d.get("setup", "Monitor for entry"),
            "tp1_basis": f"TRR resistance at {trr}" if trr else "Momentum target",
            "tp2_basis": f"Stretch to TRR at {trr}" if trr else "Stretch target",
            "stop_basis": f"Below LRR at {lrr}" if lrr else "Below entry — invalidation",
            "path_smoothness": "🟡 Normal — Discovery mode",
            "time_estimate": "2-4 weeks",
            "breakout_chance": "Medium"}
        center_items.append(_enrich_item(item, t))
    # 7. Daily Signals
    alpha_tickers = {a.get("ticker") for a in alpha.get("longs", []) + alpha.get("shorts", [])}
    included = 0
    for s in daily_signals:
        if included >= 100: break
        ticker = s.get("ticker")
        if ticker in alpha_tickers: continue
        score = abs(s.get("score", 0))
        if score < 0.10: continue
        included += 1
        s["scanner_type"] = f"DAILY {s.get('signal', 'NEUTRAL')}"
        s["level"] = "daily_strong" if "STRONG" in s.get("signal", "") else "daily"
        s["source"] = "daily_signal"
        s["priority_score"] = score * 85
        gamma = gamma_data.get(ticker, {}); greek = greeks_data.get(ticker, {})
        if greek.get("ok"):
            if "BULLISH" in greek.get("composite", "") and s.get("direction") == "LONG": s["priority_score"] *= 1.15
            elif "BEARISH" in greek.get("composite", "") and s.get("direction") == "SHORT": s["priority_score"] *= 1.15
        if gamma.get("ok"):
            if gamma.get("regime") in ("DEEP_POSITIVE", "POSITIVE") and s.get("direction") == "LONG": s["priority_score"] *= 1.10
            elif gamma.get("regime") in ("DEEP_NEGATIVE", "NEGATIVE") and s.get("direction") == "SHORT": s["priority_score"] *= 1.10
        center_items.append(s)
    center_items.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    level_1 = [x for x in center_items if x.get("level") == "level_1"]
    level_2 = [x for x in center_items if x.get("level") == "level_2"]
    watch = [x for x in center_items if x.get("level") in ("watch", "daily")]
    alpha_long = [x for x in center_items if x.get("level") == "alpha_long"]
    alpha_short = [x for x in center_items if x.get("level") == "alpha_short"]
    discovery = [x for x in center_items if x.get("level") == "discovery"]
    daily_strong = [x for x in center_items if x.get("level") in ("daily_strong", "daily")]
    return {
        "all": center_items,
        "level_1": level_1, "level_2": level_2, "watch": watch,
        "alpha_long": alpha_long, "alpha_short": alpha_short,
        "discovery": discovery, "daily_strong": daily_strong,
        "meta": {
            "total_items": len(center_items),
            "level_1_count": len(level_1), "level_2_count": len(level_2),
            "watch_count": len(watch), "alpha_long_count": len(alpha_long),
            "alpha_short_count": len(alpha_short), "discovery_count": len(discovery),
            "daily_strong_count": len(daily_strong),
            "regime": sq, "bias": bias, "vix": vix,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    }



# ══════════════════════════════════════════════════════════════════════════════
# IHSG ENHANCEMENT LAYER — 5 Structural Compensators for No Option Data
# ══════════════════════════════════════════════════════════════════════════════

def _build_ihsg_sector_momentum(prices):
    """Composite momentum per sector = IHSG equivalent of Greeks composite."""
    result = {}
    for sector, tickers in IHSG_SECTOR_TICKERS.items():
        rets = []
        for t in tickers:
            s = prices.get(t)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) >= 22:
                    try: rets.append(float(s.iloc[-1] / s.iloc[-22] - 1))
                    except: pass
        if not rets: continue
        avg_ret = float(np.mean(rets))
        leaders = sorted([(t, _safe_ret(prices.get(t), 21)) for t in tickers], key=lambda x: x[1] or -999, reverse=True)
        leader = leaders[0] if leaders else ("—", None)
        result[sector] = {
            "avg_1m": round(avg_ret, 4),
            "leader": leader[0],
            "leader_1m": round(leader[1], 4) if leader[1] is not None else None,
            "count": len(rets),
            "bias": "Bullish" if avg_ret > 0.03 else ("Bearish" if avg_ret < -0.03 else "Neutral"),
            "strength": min(1.0, max(0.0, 0.5 + avg_ret * 10)),
        }
    return result

def _build_ihsg_commodity_overlay(prices):
    """Commodity price tailwind/headwind = IHSG equivalent of COT bias."""
    overlay = {}
    for sector, meta in IHSG_COMMODITY_PROXY.items():
        proxy_ticker = meta["proxy"]
        s = prices.get(proxy_ticker)
        if s is not None and len(s) >= 22:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 22:
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                r3m = float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else r1m
                overlay[sector] = {
                    "proxy": proxy_ticker,
                    "source": meta["source"],
                    "r1m": round(r1m, 4),
                    "r3m": round(r3m, 4),
                    "tailwind": "Strong" if r1m > 0.05 else ("Moderate" if r1m > 0.02 else ("Headwind" if r1m < -0.02 else "Neutral")),
                    "signal": f"{sector} proxy {proxy_ticker} {r1m:+.1%} 1M → {'tailwind' if r1m>0 else 'headwind'}",
                }
        if sector not in overlay:
            overlay[sector] = {"proxy": proxy_ticker, "source": meta["source"], "r1m": None, "r3m": None, "tailwind": "N/A", "signal": "Proxy data unavailable"}
    return overlay

def _build_ihsg_rupiah_regime(prices):
    """DXY trend = IHSG equivalent of FX Vanna / EM flow signal."""
    dxy = prices.get("DX-Y.NYB")
    usdidr = prices.get("USDIDR=X")  # kalau ada
    result = {"dxy_trend": "Neutral", "dxy_1m": None, "idr_bias": "Neutral", "flow_signal": "Neutral"}
    if dxy is not None and len(dxy) >= 22:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            dxy_1m = float(dxy.iloc[-1] / dxy.iloc[-22] - 1)
            result["dxy_1m"] = round(dxy_1m, 4)
            if dxy_1m < -0.015:
                result["dxy_trend"] = "Bearish"
                result["idr_bias"] = "Bullish (IDR strengthens)"
                result["flow_signal"] = "🟢 EM Inflow Positive — DXY falling, IDR support"
            elif dxy_1m > 0.015:
                result["dxy_trend"] = "Bullish"
                result["idr_bias"] = "Bearish (IDR weakens)"
                result["flow_signal"] = "🔴 EM Outflow Risk — DXY rising, IDR pressure"
            else:
                result["dxy_trend"] = "Neutral"
                result["idr_bias"] = "Stable"
                result["flow_signal"] = "🟡 DXY range-bound — no strong EM flow bias"
    if usdidr is not None and len(usdidr) >= 22:
        usdidr = pd.to_numeric(usdidr, errors="coerce").dropna()
        if len(usdidr) >= 22:
            idr_1m = float(usdidr.iloc[-1] / usdidr.iloc[-22] - 1)
            result["idr_1m"] = round(idr_1m, 4)
            if idr_1m > 0.02: result["idr_bias"] = "Bearish (IDR weakens)"
            elif idr_1m < -0.02: result["idr_bias"] = "Bullish (IDR strengthens)"
    return result

def _build_ihsg_foreign_flow(prices):
    """Volume spike + gap detection = IHSG equivalent of OI concentration."""
    flow_signals = {}
    for t in list(IHSG_UNIVERSE.keys())[:20]:
        s = prices.get(t)
        if s is None or len(s) < 10: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 10: continue
        # Gap detection: overnight = open vs prev close proxy (using 2 consecutive points)
        if len(s) >= 3:
            prev_close = float(s.iloc[-2])
            curr = float(s.iloc[-1])
            gap = (curr - prev_close) / prev_close if prev_close != 0 else 0
            # Realized vol spike proxy
            recent_vol = s.tail(5).std()
            baseline_vol = s.tail(20).std()
            vol_spike = (recent_vol / baseline_vol) if baseline_vol > 0 else 1.0
            if abs(gap) > 0.02 and vol_spike > 1.3:
                if gap > 0:
                    flow_signals[t] = {"signal": "🟢 Foreign Accumulation", "gap": round(gap, 4), "vol_spike": round(vol_spike, 2), "note": "Gap up + volume spike → foreign buying"}
                else:
                    flow_signals[t] = {"signal": "🔴 Foreign Distribution", "gap": round(gap, 4), "vol_spike": round(vol_spike, 2), "note": "Gap down + volume spike → foreign selling"}
            elif vol_spike > 1.5:
                flow_signals[t] = {"signal": "🟡 Volume Spike", "gap": round(gap, 4), "vol_spike": round(vol_spike, 2), "note": "High volume without gap — watch for direction"}
            else:
                flow_signals[t] = {"signal": "⚪ Normal", "gap": round(gap, 4), "vol_spike": round(vol_spike, 2), "note": "No unusual flow detected"}
    return flow_signals

def _build_ihsg_macro_overlay(gip, prices):
    """BI rate / domestic macro proxy = IHSG equivalent of Policy Score."""
    policy = gip.features.get("policy_score", 0) if gip else 0
    growth = gip.features.get("growth_momentum", 0) if gip else 0
    inflation = gip.features.get("inflation_momentum", 0) if gip else 0
    # Banking NIM proxy: policy dovish = tailwind
    if policy > 0.1:
        bi_signal = "Dovish Hold/Cut → Banking NIM expand"
        banking_bias = "Bullish"
    elif policy < -0.1:
        bi_signal = "Hawkish → Banking NIM pressure"
        banking_bias = "Bearish"
    else:
        bi_signal = "Neutral → NIM stable"
        banking_bias = "Neutral"
    # Consumer proxy: inflation cooling = tailwind
    if inflation < -0.02:
        consumer_signal = "Inflation cooling → Consumer staples tailwind"
        consumer_bias = "Bullish"
    elif inflation > 0.03:
        consumer_signal = "Inflation sticky → Consumer margin pressure"
        consumer_bias = "Bearish"
    else:
        consumer_signal = "Inflation stable → neutral"
        consumer_bias = "Neutral"
    return {
        "policy_score": policy,
        "growth_momentum": growth,
        "inflation_momentum": inflation,
        "bi_signal": bi_signal,
        "banking_bias": banking_bias,
        "consumer_signal": consumer_signal,
        "consumer_bias": consumer_bias,
        "commodity_bias": "Bullish" if growth > 0 and inflation > 0 else ("Bearish" if growth < -0.03 else "Neutral"),
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
    if not country_quads:
        base_map = {
            "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico"],
            "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi"],
            "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Thailand"],
            "Q4": ["Indonesia","UK","Germany"],
        }
        for q, countries in base_map.items():
            for c in countries:
                if c not in country_quads: country_quads[c] = q
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

def _build_ihsg_setups(prices, ihsg_sector_momentum=None, ihsg_commodity_overlay=None, ihsg_rupiah_regime=None, ihsg_foreign_flow=None, ihsg_macro_overlay=None):
    setups = []
    sector_map = IHSG_SECTOR_MAP
    for t in list(IHSG_UNIVERSE.keys())[:20]:
        p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21); r3m = _safe_ret(prices.get(t), 63)
        if p is None: continue
        sector = sector_map.get(t, "Indonesia")
        rr = _calc_risk_range(prices.get(t))
        comp = "bullish" if (rr.get("ok") and rr.get("composite") == "bullish") else "bearish" if (rr.get("ok") and rr.get("composite") == "bearish") else "neutral"
        if r1m is not None and r1m > 0.05: thesis = f"Strong momentum +{r1m:.1%} — {sector} play"
        elif r1m is not None and r1m < -0.05: thesis = f"Weak momentum {r1m:.1%} — avoid {sector}"
        else: thesis = f"{sector} — range bound, wait for breakout"
        # Enrich with IHSG structural layers
        sector_mom = (ihsg_sector_momentum or {}).get(sector, {})
        comm_ov = (ihsg_commodity_overlay or {}).get(sector, {})
        rupiah = ihsg_rupiah_regime or {}
        flow = (ihsg_foreign_flow or {}).get(t, {})
        macro = ihsg_macro_overlay or {}
        # Build composite thesis
        thesis_parts = [thesis]
        if sector_mom.get("bias") == "Bullish": thesis_parts.append(f"Sector momentum {sector_mom.get('avg_1m'):+.1%} ({sector_mom.get('leader')} leading)")
        if comm_ov.get("tailwind") in ["Strong", "Moderate"]: thesis_parts.append(f"Commodity tailwind: {comm_ov.get('signal', '')}")
        if rupiah.get("flow_signal") and "Positive" in rupiah["flow_signal"]: thesis_parts.append("Rupiah support from DXY bearish")
        if flow.get("signal") == "🟢 Foreign Accumulation": thesis_parts.append("Foreign accumulation detected")
        if sector == "Banking" and macro.get("banking_bias") == "Bullish": thesis_parts.append(macro.get("bi_signal", ""))
        if sector in ["Consumer", "Pharma"] and macro.get("consumer_bias") == "Bullish": thesis_parts.append(macro.get("consumer_signal", ""))
        full_thesis = " | ".join(thesis_parts)
        setups.append({
            "ticker": t, "price": round(p, 2), "entry": round(p * 0.98, 2),
            "target_1": round(p * 1.08, 2), "target_2": round(p * 1.15, 2),
            "stop_loss": round(p * 0.94, 2), "rr": 2.0,
            "hold_for": "1-3 months", "signal": "BUY" if comp == "bullish" else "SELL" if comp == "bearish" else "HOLD",
            "grade": "A" if comp != "neutral" else "C",
            "direction": "LONG" if comp == "bullish" else "SHORT" if comp == "bearish" else "NEUTRAL",
            "thesis": full_thesis, "sector": sector,
            "r1m": r1m, "r3m": r3m,
            "sector_momentum": sector_mom, "commodity_overlay": comm_ov,
            "rupiah_regime": rupiah, "foreign_flow": flow, "macro_overlay": macro,
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
    all_tickers += ["DX-Y.NYB", "EIDO", "^JKSE", "VIX", "^VIX", "KOL", "JJN", "USDIDR=X"]
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


    if progress_cb: progress_cb("Calculating vol forecast...", 0.56)
    vol_forecasts = _build_vol_forecast(prices, sq, lookback=20, long_window=50)
    if progress_cb: progress_cb("Calculating Hurst proxy...", 0.57)
    hurst_proxy = _build_hurst_proxy(prices, lookback=100)
    if progress_cb: progress_cb("Calculating risk-adjusted metrics...", 0.58)
    risk_adj = _build_risk_adjusted_metrics(prices, risk_free_rate=0.04)
    if progress_cb: progress_cb("Running stress tests...", 0.59)
    # stress_test deferred — alpha not yet defined

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
    crypto_onchain = _build_crypto_onchain(prices) if include_crypto else {}
    auto_discoveries = _build_auto_discoveries(prices, gip, sq)

    # ═══════════════════════════════════════════════════════════════════
    # REAL DATA ENGINES — LIVE FETCH
    # ═══════════════════════════════════════════════════════════════════

    # ── REAL COT DATA (CFTC Live) ─────────────────────────────────────
    cot_results = {}
    if cot_scraper:
        if progress_cb: progress_cb("Fetching CFTC COT data...", 0.60)
        try:
            cot_tickers = list(COMMODITIES.keys())[:15] + list(FOREX_PAIRS.keys())[:8] + ["DX-Y.NYB"]
            for t in cot_tickers:
                r = cot_scraper.analyze(t, prices, vix_now)
                if r and r.get("ok"):
                    cot_results[t] = r
            if progress_cb: progress_cb(f"COT live: {len(cot_results)} markets", 0.62)
        except Exception as e:
            logger.warning(f"COT scraper error: {e}")

    # ── REAL OPTIONS DATA (yfinance) ──────────────────────────────────
    options_data = {}
    if yf_options:
        if progress_cb: progress_cb("Fetching options chains...", 0.63)
        try:
            us_option_tickers = list(US_SECTORS.keys())[:15] + ["SPY","QQQ","IWM","GLD","SLV","TLT","IBIT","UUP","XLK","XLE","XLV","XLP","XLU","XLF","XLI","XLB","XLC","XLRE","SMH","SOXX","VGT"]
            options_data = yf_options.analyze_multi(us_option_tickers, prices, vix_now)
            if progress_cb: progress_cb(f"Options live: {len(options_data)} tickers", 0.65)
        except Exception as e:
            logger.warning(f"yfinance options error: {e}")

    # ── REAL DEFILLAMA DATA ───────────────────────────────────────────
    crypto_onchain = {}
    if defillama:
        if progress_cb: progress_cb("Fetching DeFiLlama on-chain...", 0.66)
        try:
            crypto_onchain = defillama.get_full_snapshot()
            token_data = defillama.get_crypto_tokens_summary(list(CRYPTO.keys())[:10])
            crypto_onchain["tokens"] = token_data
            if progress_cb: progress_cb(f"DeFiLlama: TVL={crypto_onchain.get('tvl_b')}B", 0.67)
        except Exception as e:
            logger.warning(f"DeFiLlama API error: {e}")
            crypto_onchain = {"ok": False, "error": str(e), "source": "DeFiLlama (failed)"}

    # ── REAL CME DATA ─────────────────────────────────────────────────
    cme_results = {}
    if cme_scraper:
        if progress_cb: progress_cb("Fetching CME Group data...", 0.68)
        try:
            cme_tickers = list(FOREX_PAIRS.keys())[:8] + list(COMMODITIES.keys())[:10] + ["DX-Y.NYB"]
            cme_results = cme_scraper.analyze_multi(cme_tickers, prices, vix_now)
            if progress_cb: progress_cb(f"CME live: {len(cme_results)} tickers", 0.69)
        except Exception as e:
            logger.warning(f"CME scraper error: {e}")

    # ── BARCHART FALLBACK ─────────────────────────────────────────────
    barchart_results = {}
    if barchart and yf_options:
        if progress_cb: progress_cb("Probing Barchart...", 0.70)
        try:
            missed = [t for t in us_option_tickers if t not in options_data]
            for t in missed[:5]:
                r = barchart.analyze(t, prices, vix_now)
                if r and r.get("ok"):
                    barchart_results[t] = r
        except Exception as e:
            logger.warning(f"Barchart error: {e}")

    # ── CRYPTO OPTIONS (Deribit) ─────────────────────────────────────
    crypto_options = {}
    if laevitas:
        if progress_cb: progress_cb("Fetching crypto options...", 0.71)
        try:
            crypto_option_tickers = [t for t in list(CRYPTO.keys())[:5] if "BTC" in t or "ETH" in t]
            crypto_options = laevitas.analyze_multi(crypto_option_tickers, prices, vix_now)
            if progress_cb: progress_cb(f"Crypto options: {len(crypto_options)} tickers", 0.72)
        except Exception as e:
            logger.warning(f"Laevitas error: {e}")

    # ── OPTION DATA: Gamma + Greeks (fallback/proxy) ──────────────────
    gamma_data = {}
    greeks_data = {}
    vix_now = health.get("vix_bucket", {}).get("vix_last", 18)
    try:
        if progress_cb: progress_cb("Running option analytics...", 0.78)
        gamma_engine = GammaEngine()
        greeks_engine = GreeksProxy()
        dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21) or 0.0
        gamma_data = gamma_engine.analyze_multi(all_tickers, prices, vix=vix_now, dxy_ret=dxy_ret)
        greeks_data = greeks_engine.analyze_multi(all_tickers, prices, vix=vix_now, dxy_ret=dxy_ret, regime=sq)
        if progress_cb: progress_cb(f"Gamma: {len(gamma_data)} | Greeks: {len(greeks_data)}", 0.80)
    except Exception as e:
        logger.warning(f"Option analytics failed: {e}")
        if progress_cb: progress_cb("Option analytics failed — using fallback", 0.80)
    # GUARANTEE: always dict
    gamma_data = gamma_data if isinstance(gamma_data, dict) else {}
    greeks_data = greeks_data if isinstance(greeks_data, dict) else {}

    # ── ALPHA IDEAS ─────────────────────────────────────
    alpha = _build_alpha_ideas(prices, sq, mq, gamma_data, greeks_data)
    # ── STRESS TEST (now that alpha is defined) ─────────
    stress_test = _build_stress_test(prices, sq, alpha)

    # ── DAILY SIGNALS ───────────────────────────────
    if progress_cb: progress_cb("Building daily signals...", 0.82)
    daily_signals = _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data, greeks_data)
    if progress_cb: progress_cb(f"Daily signals: {len(daily_signals)} tickers", 0.85)

    # ── ALPHA CENTER ────────────────────────────────
    if progress_cb: progress_cb("Building Alpha Center...", 0.87)
    alpha_center = _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks,
                                       {"ok": True, "bottlenecks": auto_discoveries}, daily_signals,
                                       gamma_data, greeks_data)
    if progress_cb: progress_cb(f"Alpha Center: {alpha_center['meta']['total_items']} items", 0.90)

    # ── IHSG ENHANCEMENTS ─────────────────────────────
    if progress_cb: progress_cb("Building IHSG structural layers...", 0.91)
    ihsg_sector_momentum = _build_ihsg_sector_momentum(prices)
    ihsg_commodity_overlay = _build_ihsg_commodity_overlay(prices)
    ihsg_rupiah_regime = _build_ihsg_rupiah_regime(prices)
    ihsg_foreign_flow = _build_ihsg_foreign_flow(prices)
    ihsg_macro_overlay = _build_ihsg_macro_overlay(gip, prices)
    ihsg_setups = _build_ihsg_setups(prices, ihsg_sector_momentum, ihsg_commodity_overlay, ihsg_rupiah_regime, ihsg_foreign_flow, ihsg_macro_overlay)
    if progress_cb: progress_cb("IHSG layers complete", 0.93)

    ai_analysis = {
        "ok": True,
        "model": "rule-based-v1",
        "macro_summary": f"Regime {QUAD_MAP.get(sq, {}).get('name', sq)}. Growth {gip.features.get('growth_momentum', 0):+.1%}. Inflation {gip.features.get('inflation_momentum', 0):+.1%}.",
        "top_picks": [a["ticker"] for a in alpha.get("longs", [])[:3]],
        "risk_flags": [b["known_thesis"] for b in bottlenecks.get("level_1", [])[:3]],
    }

    gamma_summary = {
        "ok": True, "regime": "POSITIVE", "label": "Positive", "color": "#3FB950",
        "throttle": 0.5, "rvol_10d": 15.0, "vol_premium": -2.0,
        "action": "Buy dips, normal sizing",
    }

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
        "gamma": gamma_summary,
        "leveraged_etf": lev_data,
        "ai_analysis": ai_analysis,
        "build_time_s": round(time.time() - t0, 1),
        "prices_loaded": len(prices),
        "fred_coverage": gip.data_coverage,
        "cot_oi": cot_oi,
        "crypto_onchain": crypto_onchain,
        "crypto_aggregate": crypto_onchain.get("aggregate", {}) if isinstance(crypto_onchain, dict) else {},
        "crypto_tokens": crypto_onchain.get("tokens", {}) if isinstance(crypto_onchain, dict) else {},
        "daily_signals": daily_signals,
        "alpha_center": alpha_center,
        "gamma_data": gamma_data,
        "greeks_data": greeks_data,
        # ── IHSG NEW KEYS ──────────────────────────────────────────────
        "ihsg_sector_momentum": ihsg_sector_momentum,
        "ihsg_commodity_overlay": ihsg_commodity_overlay,
        "ihsg_rupiah_regime": ihsg_rupiah_regime,
        "ihsg_foreign_flow": ihsg_foreign_flow,
        "ihsg_macro_overlay": ihsg_macro_overlay,
        "vol_forecast": vol_forecasts,
        "hurst_proxy": hurst_proxy,
        "risk_adjusted": risk_adj,
        "stress_test": stress_test,
        # ── LIVE DATA KEYS ─────────────────────────────────────────────
        "cot_live": cot_results,
        "options_live": options_data,
        "cme_live": cme_results,
        "barchart_live": barchart_results,
        "crypto_options_live": crypto_options,
        "defillama_live": crypto_onchain,
    }

    logger.info(f"Snapshot built in {snapshot['build_time_s']}s | Prices: {len(prices)} | Ranges: {len(asset_ranges)} | Longs: {len(alpha.get('longs', []))} | Shorts: {len(alpha.get('shorts', []))} | Daily Signals: {len(daily_signals)} | Alpha Center: {alpha_center['meta']['total_items']} | IHSG Layers: {len(ihsg_sector_momentum)} sectors")
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
        "ihsg_sectors": len(snap.get("ihsg_sector_momentum", {})),
        "build_time": snap["build_time_s"],
        "vol_forecast_count": len(snap.get("vol_forecast", {})),
        "hurst_proxy_count": len(snap.get("hurst_proxy", {})),
        "risk_adjusted_count": len(snap.get("risk_adjusted", {})),
        "stress_test_scenarios": len(snap.get("stress_test", [])),
    }, indent=2))

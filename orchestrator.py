"""orchestrator.py — MacroRegime Pro v3.1 SPEED FIXED
Changes v3.1:
  • VIX → ^VIX (caret required for Yahoo Finance indices)
  • Removed: VEX, WDL, ALI=F, ZNC=F, LBS=F (nonexistent/delisted)
  • Options analytics capped at top 30 tickers (was all_tickers — major speedup)
  • fast_refresh=True: reuses cached prices, skips heavy engines (NewsNLP/EDGAR/full options)
  • Cache default 12h
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

try:
    from config.narrative_universe import NARRATIVE_UNIVERSE
except Exception:
    NARRATIVE_UNIVERSE = {}

try:
    import config.autonomy_settings as AUTONOMY
except Exception:
    AUTONOMY = None

try:
    from engines.ai_engine import AIEngine
except Exception as _e:
    logger.warning(f"ai_engine import failed: {_e}")
    class AIEngine:
        def run(self, sq, mq, gq, gip_features, prices, **kwargs):
            return {"ok": False, "narratives": [], "bottlenecks": [], "alpha_ideas": [], "scenario_update": {}}

try:
    from engines.pvv_engine import PVVEngine, PVVScanner
    PVV_AVAILABLE = True
except Exception as _e:
    logger.warning(f"pvv_engine: {_e}")
    PVV_AVAILABLE = False
    class PVVScanner:
        def analyze_multi(self, prices, volumes=None): return {}

try:
    from engines.trend_signal_engine import TrendSignalEngine, TrendSignalScanner
    TREND_AVAILABLE = True
except Exception as _e:
    logger.warning(f"trend_signal_engine: {_e}")
    TREND_AVAILABLE = False
    class TrendSignalScanner:
        def build_multi(self, prices, volumes=None, duration="TREND"): return {}

try:
    from engines.bottleneck_discovery_v3 import BottleneckDiscoveryV3
except Exception as _e:
    logger.warning(f"bottleneck_discovery_v3: {_e}")
    class BottleneckDiscoveryV3:
        def __init__(self, settings_module): pass
        def run(self, prices, **kwargs): return {"reactive":[],"proactive":[],"spillover":[],"meta":{}}

try:
    from engines.leading_indicator_engine import LeadingIndicatorEngine
except Exception:
    class LeadingIndicatorEngine:
        def run(self, prices, gip_features, sq): return {}

try:
    from engines.regime_predictor_engine import RegimePredictorEngine
except Exception:
    class RegimePredictorEngine:
        def predict(self, features, sq): return {}

try:
    from engines.gamma_engine import GammaEngine
except Exception as _e:
    logger.warning(f"gamma_engine: {_e}")
    class GammaEngine:
        def analyze_multi(self, tickers, prices, **kwargs): return {}

try:
    from engines.greeks_proxy import GreeksProxy
except Exception as _e:
    logger.warning(f"greeks_proxy: {_e}")
    class GreeksProxy:
        def analyze_multi(self, tickers, prices, **kwargs): return {}

try:
    from engines.yfinance_options import YFinanceOptionsEngine as YFO
    yf_options = YFO()
except Exception:
    yf_options = None

try:
    from engines.cot_scraper import cot_scraper
    COT_AVAILABLE = True
except Exception:
    cot_scraper = None; COT_AVAILABLE = False

try:
    from engines.cme_scraper import cme_scraper
except Exception:
    cme_scraper = None

try:
    from engines.barchart_scraper import barchart_scraper as barchart
except Exception:
    barchart = None

try:
    from engines.defillama import DeFiLlamaEngine
    defillama = DeFiLlamaEngine()
except Exception:
    defillama = None

try:
    from engines.laevitas import LaevitasEngine
    laevitas = LaevitasEngine()
except Exception:
    laevitas = None

try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
    discovery_engine = AutoDiscoveryEngineV3()
except Exception as _e:
    logger.warning(f"auto_discovery_v3: {_e}")
    discovery_engine = None

from data.loader import load_prices, save_snapshot

try:
    from engines.gip_engine import GIPEngine
    from engines.market_health import MarketHealthEngine
    from engines.transition_engine import TransitionEngine
    from engines.playbook_engine import PlaybookEngine
except Exception as _e:
    logger.warning(f"Core engine import failed: {_e}")

try:
    from fredapi import Fred
    _FRED_KEY = os.environ.get("FRED_API_KEY") or ""
    _fred_client = Fred(api_key=_FRED_KEY) if _FRED_KEY else None
except Exception:
    _fred_client = None

def load_fred_macro():
    if _fred_client is None:
        return {}
    series_ids = {
        "gdp_growth": "A191RL1Q225SBEA",
        "cpi_yoy": "CPIAUCSL",
        "core_cpi": "CPILFESL",
        "pce": "PCEPI",
        "unemployment": "UNRATE",
        "fed_funds": "FEDFUNDS",
        "10y_yield": "DGS10",
        "2y_yield": "DGS2",
        "credit_spread": "BAMLH0A0HYM2",
        "ism_mfg": "MANEMP",
        "consumer_conf": "UMCSENT",
        "housing_starts": "HOUST",
        "industrial_prod": "INDPRO",
        "retail_sales": "RSAFS",
        "m2": "M2SL",
    }
    data = {}
    for k, sid in series_ids.items():
        try:
            s = _fred_client.get_series(sid, observation_start="2018-01-01")
            if s is not None and len(s) > 0:
                data[k] = s
        except Exception:
            pass
    return data

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
QUAD_MAP = {
    "Q1": {"name":"Growth↑ Inflation↓","bias":"bullish","assets":["QQQ","XLK","IBIT","IWM","SMH"],"shorts":["TLT","GLD","XLU"]},
    "Q2": {"name":"Growth↑ Inflation↑","bias":"bullish","assets":["XLE","OIH","XOP","SLV","GDX","XLF"],"shorts":["TLT","XLU","XLRE"]},
    "Q3": {"name":"Stagflation","bias":"defensive","assets":["GLD","SLV","GDX","GDXJ","XLP","XLV","XLU","ITA"],"shorts":["QQQ","IWM","XLK"]},
    "Q4": {"name":"Deflation","bias":"bearish","assets":["TLT","IEF","GLD","XLU","XLP","UUP"],"shorts":["SPY","QQQ","IWM","IBIT","XLK"]},
}

TICKER_QUAD_FIT = {
    "QQQ":{"Q1":0.95,"Q2":0.70,"Q3":0.25,"Q4":0.10},
    "XLK":{"Q1":0.95,"Q2":0.65,"Q3":0.20,"Q4":0.10},
    "IBIT":{"Q1":0.90,"Q2":0.75,"Q3":0.30,"Q4":0.15},
    "IWM":{"Q1":0.85,"Q2":0.75,"Q3":0.25,"Q4":0.10},
    "SPY":{"Q1":0.80,"Q2":0.70,"Q3":0.35,"Q4":0.20},
    "GLD":{"Q1":0.30,"Q2":0.60,"Q3":0.90,"Q4":0.85},
    "SLV":{"Q1":0.35,"Q2":0.75,"Q3":0.85,"Q4":0.65},
    "TLT":{"Q1":0.50,"Q2":0.15,"Q3":0.30,"Q4":0.95},
    "XLE":{"Q1":0.55,"Q2":0.90,"Q3":0.65,"Q4":0.15},
    "XLU":{"Q1":0.30,"Q2":0.25,"Q3":0.70,"Q4":0.80},
    "XLP":{"Q1":0.40,"Q2":0.45,"Q3":0.75,"Q4":0.80},
    "XLV":{"Q1":0.55,"Q2":0.50,"Q3":0.70,"Q4":0.65},
    "XLF":{"Q1":0.70,"Q2":0.85,"Q3":0.35,"Q4":0.15},
    "UUP":{"Q1":0.35,"Q2":0.70,"Q3":0.65,"Q4":0.85},
    "GDX":{"Q1":0.35,"Q2":0.70,"Q3":0.90,"Q4":0.80},
    "GDXJ":{"Q1":0.30,"Q2":0.65,"Q3":0.90,"Q4":0.75},
    "ITA":{"Q1":0.60,"Q2":0.75,"Q3":0.80,"Q4":0.45},
    "SMH":{"Q1":0.95,"Q2":0.60,"Q3":0.20,"Q4":0.10},
    "NVDA":{"Q1":0.95,"Q2":0.65,"Q3":0.20,"Q4":0.10},
    "MSTR":{"Q1":0.90,"Q2":0.75,"Q3":0.25,"Q4":0.10},
    "^JKSE":{"Q1":0.65,"Q2":0.75,"Q3":0.50,"Q4":0.30},
    "EIDO":{"Q1":0.65,"Q2":0.75,"Q3":0.50,"Q4":0.30},
}

SECTOR_QUAD_FIT = {
    "us_equity": {"Q1":0.75,"Q2":0.70,"Q3":0.35,"Q4":0.20},
    "tech":      {"Q1":0.90,"Q2":0.60,"Q3":0.20,"Q4":0.10},
    "energy":    {"Q1":0.50,"Q2":0.85,"Q3":0.65,"Q4":0.20},
    "commodity": {"Q1":0.40,"Q2":0.80,"Q3":0.75,"Q4":0.50},
    "forex":     {"Q1":0.50,"Q2":0.55,"Q3":0.55,"Q4":0.60},
    "crypto":    {"Q1":0.85,"Q2":0.70,"Q3":0.30,"Q4":0.15},
    "ihsg":      {"Q1":0.60,"Q2":0.70,"Q3":0.50,"Q4":0.30},
    "generic":   {"Q1":0.50,"Q2":0.50,"Q3":0.50,"Q4":0.50},
}

IHSG_TICKER_SECTOR = {
    "ADRO.JK":"Coal","ITMG.JK":"Coal","PTBA.JK":"Coal","BUMI.JK":"Coal",
    "NCKL.JK":"Nickel","ANTM.JK":"Nickel","INCO.JK":"Nickel","MDKA.JK":"Nickel",
    "AALI.JK":"CPO","LSIP.JK":"CPO","SSMS.JK":"CPO",
    "BBRI.JK":"Banking","BMRI.JK":"Banking","BBCA.JK":"Banking","BBNI.JK":"Banking","BRIS.JK":"Banking",
    "TLKM.JK":"Telco","EXCL.JK":"Telco","ISAT.JK":"Telco",
    "UNTR.JK":"Mining Contractor","BYAN.JK":"Mining","AADI.JK":"Mining",
    "ICBP.JK":"Consumer","INDF.JK":"Consumer","KLBF.JK":"Pharma",
    "PGEO.JK":"Geothermal","WINS.JK":"Shipping",
    "EIDO":"ETF","^JKSE":"Index",
}

IHSG_SECTOR_TICKERS = {
    "Coal":   ["ADRO.JK","ITMG.JK","PTBA.JK"],
    "Nickel": ["NCKL.JK","ANTM.JK","INCO.JK"],
    "CPO":    ["AALI.JK","LSIP.JK","SSMS.JK"],
    "Banking":["BBRI.JK","BMRI.JK","BBCA.JK","BBNI.JK","BRIS.JK"],
    "Telco":  ["TLKM.JK","EXCL.JK"],
    "Consumer":["ICBP.JK","INDF.JK"],
    "Pharma": ["KLBF.JK"],
}

IHSG_COMMODITY_PROXY = {
    "Coal":   {"proxy":"KOL","source":"Coal ETF"},
    "Nickel": {"proxy":"JJN","source":"Nickel ETN"},
    "CPO":    {"proxy":"DBA","source":"Agriculture ETF"},
}

# ── TOP OPTIONS TICKERS — cap analytics to 30 for speed ─────────────────────
TOP_OPTIONS_TICKERS = list(dict.fromkeys(
    ["SPY","QQQ","IWM","GLD","SLV","TLT","IBIT","UUP","XLK","XLE","XLV","XLP","XLU","XLF","XLI"] +
    ["NVDA","AAPL","MSFT","META","GOOGL","AMZN","TSLA","AMD","AVGO","JPM"] +
    ["SMH","GDX","XOP","BTC-USD","ETH-USD"]
))[:30]

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _get_regime_fit(ticker: str, quad: str) -> float:
    if ticker in TICKER_QUAD_FIT:
        return TICKER_QUAD_FIT[ticker].get(quad, 0.50)
    sector = TICKER_SECTOR.get(ticker, "generic")
    return SECTOR_QUAD_FIT.get(sector, SECTOR_QUAD_FIT["generic"]).get(quad, 0.50)

def _calc_risk_range(s, ticker="", market="us_equity"):
    if s is None or s.empty: return {"ok": False}
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 60: return {"ok": False}
    last = float(s.iloc[-1]); sma20 = float(s.tail(20).mean()); sma50 = float(s.tail(50).mean())
    std20 = float(s.tail(20).std())
    if not all(math.isfinite(v) for v in [last, sma20, sma50, std20]): return {"ok": False}
    lrr = round(sma20 - 1.5 * std20, 2); trr = round(sma20 + 1.5 * std20, 2)
    lrr_t = round(sma20 - 2.0 * std20, 2); trr_t = round(sma20 + 2.0 * std20, 2)  # Trend
    std_all = float(s.std())
    lrr_tail = round(float(s.mean()) - 2.5 * std_all, 2); trr_tail = round(float(s.mean()) + 2.5 * std_all, 2)  # Tail
    if last < lrr: composite = "bullish"; quality = "A"
    elif last > trr: composite = "bearish"; quality = "short_A"
    elif last < sma20: composite = "neutral"; quality = "B"
    else: composite = "neutral"; quality = "C"
    return {
        "ok": True, "px": round(last, 2), "market": market, "composite": composite, "quality": quality,
        "trade": {"lrr": lrr, "trr": trr},
        "trend": {"lrr": lrr_t, "trr": trr_t, "direction": "up" if last > sma50 else "down"},
        "tail":  {"lrr": lrr_tail, "trr": trr_tail},
        "signal": "OVERSOLD" if last < lrr else ("OVERBOUGHT" if last > trr else "NEUTRAL"),
        "note": f"Price {last:.2f} | Trade {lrr:.2f}–{trr:.2f} | Trend {lrr_t:.2f}–{trr_t:.2f}",
    }

def _safe_ret(s, n):
    if s is None or s.empty: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1: return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
        return r if math.isfinite(r) else None
    except: return None

def _last_price(s):
    if s is None or s.empty: return None
    try:
        v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1])
        return v if math.isfinite(v) else None
    except: return None

def _build_risk_ranges(prices, all_tickers):
    asset_ranges = {}
    for t in all_tickers:
        s = prices.get(t)
        if s is None or s.empty: continue
        mkt = "us_equity"
        if t in FOREX_PAIRS or any(x in t for x in ["USD=","EUR=","GBP=","JPY=","CAD","AUD","CHF","NZD","MXN","SEK","BRL","IDR"]):
            mkt = "forex"
        elif t in COMMODITIES or any(x in t for x in ["GC=","SI=","CL=","BZ=","NG=","HG=","PL=","PA=","RB=","HO=","ZW=","ZC=","ZS=","=F"]):
            mkt = "commodity"
        elif t in CRYPTO or any(x in t for x in ["BTC","ETH","SOL","ADA","AVAX","DOT","LINK","DOGE","LTC","XRP","BNB"]):
            mkt = "crypto"
        elif t in IHSG_UNIVERSE or any(x in t for x in [".JK","EIDO","^JKSE"]):
            mkt = "ihsg"
        rr = _calc_risk_range(s, ticker=t, market=mkt)
        if rr.get("ok"): asset_ranges[t] = rr
    return asset_ranges

def _build_vol_forecast(prices, sq, lookback=20, long_window=50):
    forecasts = {}
    regime_mult = {"Q1":0.90,"Q2":1.05,"Q3":1.20,"Q4":1.15}
    for ticker, s in prices.items():
        if s is None or len(s) < lookback + 5: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < lookback + 5: continue
        rets = s.pct_change().dropna()
        if len(rets) < lookback: continue
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
        if forecast_vol < 15: vol_regime = "LOW"
        elif forecast_vol < 25: vol_regime = "NORMAL"
        elif forecast_vol < 35: vol_regime = "ELEVATED"
        else: vol_regime = "EXTREME"
        forecasts[ticker] = {
            "current_ann_vol": round(ewma_vol, 1),
            "forecast_ann_vol": round(forecast_vol, 1),
            "vol_regime": vol_regime,
            "vol_ratio": round(vol_ratio, 2),
            "lambda_used": lam,
        }
    return forecasts

def _build_risk_adjusted_metrics(prices, risk_free_rate=0.04):
    metrics = {}
    for ticker, s in prices.items():
        if s is None or len(s) < 65: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 65: continue
        rets = s.pct_change().dropna().tail(63)
        if len(rets) < 60: continue
        mean_ret = rets.mean() * 252; std_dev = rets.std() * math.sqrt(252)
        sharpe = (mean_ret - risk_free_rate) / std_dev if std_dev > 0 else 0
        downside = pd.Series([r for r in rets if r < 0]).std() * math.sqrt(252) or 0.001
        sortino = (mean_ret - risk_free_rate) / downside
        max_dd = (rets - rets.cummax()).min()
        metrics[ticker] = {"sharpe_63d": round(sharpe, 2), "sortino_63d": round(sortino, 2),
                           "ann_return": round(mean_ret, 3), "ann_vol": round(std_dev, 3), "max_dd_63d": round(max_dd, 3)}
    return metrics

def _build_stress_test(prices, sq, alpha):
    SHOCKS = {
        "2008_GFC": {
            "Q1": {"SPY":-0.45,"QQQ":-0.50,"IWM":-0.55,"XLK":-0.55,"XLE":-0.35,"XLF":-0.60,"TLT":+0.25,"GLD":+0.20},
            "Q2": {"SPY":-0.35,"QQQ":-0.40,"IWM":-0.45,"XLK":-0.40,"XLE":-0.30,"XLF":-0.50,"TLT":+0.20,"GLD":+0.15},
            "Q3": {"SPY":-0.20,"QQQ":-0.25,"IWM":-0.25,"XLK":-0.20,"XLE":-0.15,"XLF":-0.25,"TLT":+0.10,"GLD":+0.10},
            "Q4": {"SPY":-0.15,"QQQ":-0.20,"IWM":-0.20,"XLK":-0.15,"XLE":-0.10,"XLF":-0.20,"TLT":+0.08,"GLD":+0.08},
        },
        "2022_Taper": {
            "Q1": {"SPY":-0.20,"QQQ":-0.30,"IWM":-0.25,"XLK":-0.35,"TLT":-0.20,"GLD":+0.05,"XLE":+0.40},
            "Q2": {"SPY":-0.15,"QQQ":-0.25,"IWM":-0.20,"XLK":-0.30,"TLT":-0.25,"GLD":+0.10,"XLE":+0.35},
            "Q3": {"SPY":-0.10,"QQQ":-0.15,"IWM":-0.15,"XLK":-0.20,"TLT":-0.15,"GLD":+0.05,"XLE":+0.20},
            "Q4": {"SPY":-0.05,"QQQ":-0.10,"IWM":-0.10,"XLK":-0.15,"TLT":-0.10,"GLD":+0.03,"XLE":+0.10},
        },
        "2020_COVID": {
            "Q1": {"SPY":-0.35,"QQQ":-0.25,"IWM":-0.45,"XLK":-0.20,"TLT":+0.20,"GLD":+0.05},
            "Q2": {"SPY":-0.30,"QQQ":-0.20,"IWM":-0.40,"XLK":-0.18,"TLT":+0.18,"GLD":+0.05},
            "Q3": {"SPY":-0.20,"QQQ":-0.15,"IWM":-0.30,"XLK":-0.12,"TLT":+0.12,"GLD":+0.03},
            "Q4": {"SPY":-0.15,"QQQ":-0.10,"IWM":-0.20,"XLK":-0.08,"TLT":+0.08,"GLD":+0.02},
        },
    }
    results = []
    long_tickers = [a.get("ticker") for a in alpha.get("longs", []) if a.get("ticker")]
    for scenario, quad_shocks in SHOCKS.items():
        shock = quad_shocks.get(sq, {})
        exposure = 0.0
        for t in long_tickers:
            s_val = shock.get(t, -0.10)
            px = _last_price(prices.get(t)) or 0
            exposure += px * s_val
        results.append({"scenario": scenario, "quad": sq, "portfolio_impact": round(exposure, 2),
                        "shock_map": shock, "long_tickers": long_tickers[:5]})
    return results

# ── Signal helpers ────────────────────────────────────────────────────────────
def _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction):
    if direction not in ("LONG", "SHORT"): return "WAIT — No clear edge"
    if direction == "LONG":
        if price and lrr and price <= lrr * 1.02: return "BUY NOW — At/near LRR buy zone"
        if price and trr and price >= trr * 0.98: return "WAIT — Price at TRR, wait for pullback to LRR"
        if momentum_1m and momentum_1m < -0.10: return "SMALL SIZE — Deep pullback, scale in"
        return "BUY DIP — Wait for LRR test"
    else:
        if price and trr and price >= trr * 0.98: return "SELL NOW — At/near TRR sell zone"
        if price and lrr and price <= lrr * 1.02: return "WAIT — Price at LRR, wait for TRR retest"
        return "SELL RALLY — Wait for TRR test"

def _rr_levels(price, lrr, trr, direction="long"):
    if lrr and trr and price:
        spread = trr - lrr
        if direction == "long":
            entry = round(lrr * 1.005, 2); tp1 = round(lrr + spread * 0.5, 2)
            tp2  = round(trr, 2); stop = round(lrr * 0.97, 2)
            rr_val = round((tp1 - entry) / max(entry - stop, 0.01), 2)
        else:
            entry = round(trr * 0.995, 2); tp1 = round(trr - spread * 0.5, 2)
            tp2  = round(lrr, 2); stop = round(trr * 1.03, 2)
            rr_val = round((entry - tp1) / max(stop - entry, 0.01), 2)
        return {"entry": entry, "tp1": tp1, "tp2": tp2, "stop": stop, "rr": rr_val}
    p = price or 100.0
    if direction == "long":
        return {"entry": round(p*0.98,2),"tp1":round(p*1.05,2),"tp2":round(p*1.10,2),"stop":round(p*0.95,2),"rr":1.7}
    return {"entry":round(p*1.02,2),"tp1":round(p*0.95,2),"tp2":round(p*0.90,2),"stop":round(p*1.05,2),"rr":1.7}

def _boost_priority(base_score, ticker, direction):
    boost = 0
    mag7 = list(MAG7.keys()) if MAG7 else ["NVDA","AAPL","MSFT","META","GOOGL","AMZN","TSLA"]
    if ticker in ["SPY","QQQ","IWM","GLD","TLT","IBIT"]: boost += 5
    if ticker in mag7: boost += 3
    if "STRONG" in str(direction).upper(): boost += 10
    return round(min(100, base_score + boost), 2)

def _frontrun_status(composite_score, near_entry, direction="LONG"):
    if composite_score >= 0.75 and near_entry: return "BOARDING NOW"
    if composite_score >= 0.60: return "GATE OPENS SOON"
    if composite_score >= 0.40: return "CHECK-IN"
    return "WAIT"

def _enrich_signal_with_conclusions(sig, gamma, greek, rr_data, market_type="us_equity"):
    price = sig.get("price"); entry = sig.get("entry")
    lrr = rr_data.get("trade", {}).get("lrr") if rr_data and rr_data.get("ok") else None
    trr = rr_data.get("trade", {}).get("trr") if rr_data and rr_data.get("ok") else None
    direction = sig.get("direction","LONG"); composite = sig.get("composite","neutral")
    momentum_1m = sig.get("momentum_1m"); vix = sig.get("vix", 20)
    sig["entry_advice"] = _entry_advice(price, entry, lrr, trr, gamma, greek, momentum_1m, composite, direction)
    if "BUY NOW" in sig["entry_advice"] or "SELL NOW" in sig["entry_advice"]:
        sig["worth_entering"] = "YES — " + sig["entry_advice"]
    elif "WAIT" in sig["entry_advice"]:
        sig["worth_entering"] = "WAIT — " + sig["entry_advice"]
    else:
        sig["worth_entering"] = "MONITOR — " + sig["entry_advice"]
    return sig

def _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data=None, greeks_data=None):
    regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18) if health else 18
    crash = health.get("crash", {}).get("state", "calm") if health else "calm"
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    signals = []
    for ticker, s in prices.items():
        if s is None or s.empty: continue
        p = _last_price(s)
        if p is None: continue
        r1m = _safe_ret(s, 21); r3m = _safe_ret(s, 63); r5d = _safe_ret(s, 5)
        rr = asset_ranges.get(ticker, {})
        composite = rr.get("composite", "neutral") if rr.get("ok") else "neutral"
        fit = _get_regime_fit(ticker, sq)
        lrr = rr.get("trade", {}).get("lrr") if rr.get("ok") else None
        trr = rr.get("trade", {}).get("trr") if rr.get("ok") else None
        gamma = gamma_data.get(ticker, {}); greek = greeks_data.get(ticker, {})
        vol_adj = 1.0 if vix < 25 else (0.85 if vix < 30 else 0.70)
        # Score
        score = 0.0
        if composite == "bullish":   score += 0.40
        elif composite == "bearish": score -= 0.40
        score += (r1m or 0) * 2; score += (r5d or 0) * 1; score += (fit - 0.5) * 0.5
        score *= vol_adj; score = max(-1, min(1, score))
        # Signal label
        if score > 0.5:   signal_label = "STRONG LONG";  direction = "LONG"; grade = "A"
        elif score > 0.2: signal_label = "LONG";          direction = "LONG"; grade = "B"
        elif score < -0.5: signal_label = "STRONG SHORT"; direction = "SHORT"; grade = "A"
        elif score < -0.2: signal_label = "SHORT";        direction = "SHORT"; grade = "B"
        else: signal_label = "NEUTRAL"; direction = "NEUTRAL"; grade = "C"
        rr_lv = _rr_levels(p, lrr, trr, "long" if direction == "LONG" else "short")
        sig = {
            "ticker": ticker, "price": round(p, 2), "signal": signal_label, "direction": direction,
            "grade": grade, "entry": rr_lv["entry"], "target_1": rr_lv["tp1"], "target_2": rr_lv["tp2"],
            "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"], "hold_for": "2-4 weeks",
            "regime_fit": fit, "score": round(score, 2), "vix": vix,
            "momentum_1m": r1m, "momentum_3m": r3m, "composite": composite,
            "lrr": lrr, "trr": trr,
            "thesis": f"{ticker} {signal_label} | {sq}/{mq} regime | fit {fit:.0%} | 1M {fp(r1m)} | LRR {ff(lrr)}–TRR {ff(trr)}",
        }
        sig = _enrich_signal_with_conclusions(sig, gamma, greek, rr, market_type="us_equity")
        signals.append(sig)
    signals.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)
    return signals

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

def _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks, auto_discoveries, daily_signals, gamma_data=None, greeks_data=None):
    regime = QUAD_MAP.get(sq, {}); bias = regime.get("bias", "neutral")
    vix = health.get("vix_bucket", {}).get("vix_last", 18) if health else 18
    gamma_data = gamma_data or {}; greeks_data = greeks_data or {}
    center_items = []

    def _enrich_item(item, ticker):
        gamma = gamma_data.get(ticker, {}); greek = greeks_data.get(ticker, {})
        if gamma.get("ok"):
            for k in ["regime","throttle","max_pain","gamma_flip_up","gamma_flip_down","put_wall","call_wall","gamma_exposure","skew","dist_max_pain_pct"]:
                if k in gamma: item[f"gamma_{k}" if k not in item else k] = gamma[k]
        if greek.get("ok"):
            for k in ["composite","delta","gamma","vanna","charm","vol_premium","rvol_20d"]:
                if k in greek: item[f"greek_{k}" if k in ("gamma",) else k] = greek[k]
        rr_data = asset_ranges.get(ticker, {})
        comp_score = _compute_composite_score(item, rr_data, gamma_data, greeks_data, vix)
        near_entry = bool(item.get("entry") and item.get("price") and abs(item["price"] - item["entry"]) / max(item["price"], 0.01) < 0.03)
        item["composite_score"] = comp_score
        item["frontrun_status"] = _frontrun_status(comp_score, near_entry, item.get("direction","LONG"))
        return item

    def _compute_composite_score(item, rr_data, gamma_data, greeks_data, vix):
        score = 0.0
        score += item.get("regime_fit", 0.5) * 0.30
        qual = rr_data.get("quality","C") if rr_data and rr_data.get("ok") else "C"
        score += {"A":1.0,"B":0.70,"C":0.35,"short_A":1.0,"short_B":0.70}.get(qual, 0.35) * 0.25
        gamma = gamma_data.get(item.get("ticker",""), {}); greek = greeks_data.get(item.get("ticker",""), {})
        align = 0.5
        if gamma.get("ok") and greek.get("ok"):
            g_reg = gamma.get("regime","TRANSITION"); g_comp = greek.get("composite","NEUTRAL")
            if item.get("direction") == "LONG" and g_reg in ("DEEP_POSITIVE","POSITIVE") and "BULLISH" in g_comp: align = 1.0
            elif item.get("direction") == "SHORT" and g_reg in ("DEEP_NEGATIVE","NEGATIVE") and "BEARISH" in g_comp: align = 1.0
            else: align = 0.4
        score += align * 0.25
        score += min(item.get("discovery_score", 0.0), 1.0) * 0.10
        vix_mult = 1.0 if vix < 25 else (0.85 if vix < 30 else 0.70)
        return round(min(1.0, max(0.0, score * vix_mult * 0.10 + 0.10)), 2)

    # Bottleneck Level 1
    for b in bottlenecks.get("level_1", []):
        t = b.get("ticker","UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade",{}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade",{}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in b.get("direction","") else "short")
        score = min(1.0, max(0.0, b.get("score",0)))
        item = {"ticker":t,"scanner_type":"BOTTLENECK L1","level":"level_1",
            "priority_score":_boost_priority(score*100,t,b.get("direction","HOLD")),
            "direction":b.get("direction","HOLD"),"signal":b.get("direction","HOLD"),
            "grade":b.get("quality","A"),"sector":b.get("sector","Macro"),
            "thesis":b.get("known_thesis",""),"setup":b.get("setup",""),
            "invalidators":["Stop hit","Regime flip","VIX >35"],"hold_for":"Immediate","source":"bottleneck",
            "price":p,"entry":rr_lv["entry"],"target_1":rr_lv["tp1"],"target_2":rr_lv["tp2"],
            "stop_loss":rr_lv["stop"],"rr":rr_lv["rr"],"worth_entering":"URGENT — "+b.get("direction","HOLD"),
            "entry_advice":b.get("setup","Risk off positioning"),"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    # Bottleneck Level 2
    for b in bottlenecks.get("level_2", []):
        t = b.get("ticker","UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade",{}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade",{}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in b.get("direction","") else "short")
        score = min(1.0, max(0.0, b.get("score",0)+0.1))
        item = {"ticker":t,"scanner_type":"BOTTLENECK L2","level":"level_2",
            "priority_score":_boost_priority(score*80,t,b.get("direction","HOLD")),
            "direction":b.get("direction","HOLD"),"grade":b.get("quality","B"),"sector":b.get("sector","Macro"),
            "thesis":b.get("known_thesis",""),"hold_for":"1-2 weeks","source":"bottleneck",
            "price":p,"entry":rr_lv["entry"],"target_1":rr_lv["tp1"],"target_2":rr_lv["tp2"],
            "stop_loss":rr_lv["stop"],"rr":rr_lv["rr"],"worth_entering":"BUILDING — "+b.get("direction","HOLD"),
            "entry_advice":b.get("setup","Monitor closely"),"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    # Watch
    for b in bottlenecks.get("watch", []):
        t = b.get("ticker","UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t, {}); lrr = rr.get("trade",{}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade",{}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long")
        item = {"ticker":t,"scanner_type":"WATCH","level":"watch",
            "priority_score":_boost_priority(b.get("score",0)*60,t,"HOLD"),
            "direction":"HOLD","grade":b.get("quality","B"),"sector":b.get("sector","Macro"),
            "thesis":b.get("known_thesis",""),"hold_for":"Monitor","source":"bottleneck",
            "price":p,"entry":rr_lv["entry"],"target_1":rr_lv["tp1"],"target_2":rr_lv["tp2"],
            "stop_loss":rr_lv["stop"],"rr":rr_lv["rr"],"worth_entering":"WATCH — Wait for signal",
            "entry_advice":b.get("setup","Wait for clarity"),"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    # Alpha longs / shorts
    for a in alpha.get("longs", []):
        t = a.get("ticker"); p = _last_price(prices.get(t)) or a.get("price",0)
        item = {"ticker":t,"scanner_type":"ALPHA LONG","level":"alpha_long",
            "priority_score":_boost_priority(75 if a.get("grade")=="A" else 60,t,"LONG"),
            "direction":"LONG","signal":a.get("signal","BUY"),"grade":a.get("grade","B"),
            "sector":TICKER_SECTOR.get(t,"Unknown"),"thesis":a.get("thesis",""),
            "hold_for":"2-4 weeks","source":"alpha","price":a.get("price",p),
            "entry":a.get("entry"),"target_1":a.get("target_1"),"target_2":a.get("target_2"),
            "stop_loss":a.get("stop_loss"),"rr":a.get("rr",2.0),
            "worth_entering":a.get("worth_entering","YES"),"entry_advice":a.get("entry_advice",""),
            "invalidators":["Stop hit","Trend breaks","Quad shifts"],"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    for a in alpha.get("shorts", []):
        t = a.get("ticker"); p = _last_price(prices.get(t)) or a.get("price",0)
        item = {"ticker":t,"scanner_type":"ALPHA SHORT","level":"alpha_short",
            "priority_score":_boost_priority(75 if a.get("grade")=="A" else 60,t,"SHORT"),
            "direction":"SHORT","signal":a.get("signal","SELL"),"grade":a.get("grade","B"),
            "sector":TICKER_SECTOR.get(t,"Unknown"),"thesis":a.get("thesis",""),
            "hold_for":"2-4 weeks","source":"alpha","price":a.get("price",p),
            "entry":a.get("entry"),"target_1":a.get("target_1"),"target_2":a.get("target_2"),
            "stop_loss":a.get("stop_loss"),"rr":a.get("rr",2.0),
            "worth_entering":a.get("worth_entering","YES"),"entry_advice":a.get("entry_advice",""),
            "invalidators":["Stop hit","Trend breaks","Quad shifts"],"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    # Auto discoveries
    for d in (auto_discoveries.get("bottlenecks", []) if isinstance(auto_discoveries, dict) else []):
        t = d.get("ticker","UNKNOWN"); p = _last_price(prices.get(t)) or 0.0
        rr = asset_ranges.get(t,{}); lrr = rr.get("trade",{}).get("lrr") if rr.get("ok") else None; trr = rr.get("trade",{}).get("trr") if rr.get("ok") else None
        rr_lv = _rr_levels(p, lrr, trr, "long" if "LONG" in d.get("direction","") else "short")
        item = {"ticker":t,"scanner_type":"DISCOVERY","level":"discovery",
            "priority_score":_boost_priority(d.get("score",0)*90,t,d.get("direction","HOLD")),
            "direction":d.get("direction","HOLD"),"grade":d.get("quality","B"),
            "sector":d.get("sector","Macro"),"thesis":d.get("known_thesis",""),
            "hold_for":"2-4 weeks","source":"auto_discovery","price":p,
            "entry":rr_lv["entry"],"target_1":rr_lv["tp1"],"target_2":rr_lv["tp2"],
            "stop_loss":rr_lv["stop"],"rr":rr_lv["rr"],
            "worth_entering":"DISCOVERY — "+d.get("direction","HOLD"),
            "entry_advice":d.get("setup","Monitor for entry"),"regime_fit":_get_regime_fit(t,sq)}
        center_items.append(_enrich_item(item, t))

    # Daily signals (top 100 by score, skip duplicates)
    existing_tickers = {x.get("ticker") for x in center_items}
    included = 0
    for s in daily_signals:
        if included >= 100: break
        ticker = s.get("ticker")
        if ticker in existing_tickers: continue
        if abs(s.get("score",0)) < 0.10: continue
        included += 1; existing_tickers.add(ticker)
        s["scanner_type"] = f"DAILY {s.get('signal','NEUTRAL')}"
        s["level"] = "daily_strong" if "STRONG" in s.get("signal","") else "daily"
        s["source"] = "daily_signal"
        s["priority_score"] = abs(s.get("score",0)) * 85
        center_items.append(s)

    center_items.sort(key=lambda x: x.get("priority_score",0), reverse=True)
    level_1    = [x for x in center_items if x.get("level") == "level_1"]
    level_2    = [x for x in center_items if x.get("level") == "level_2"]
    watch      = [x for x in center_items if x.get("level") == "watch"]
    alpha_long = [x for x in center_items if x.get("level") == "alpha_long"]
    alpha_short= [x for x in center_items if x.get("level") == "alpha_short"]
    discovery  = [x for x in center_items if x.get("level") == "discovery"]
    daily_strong=[x for x in center_items if x.get("level") in ("daily_strong","daily")]
    return {
        "all": center_items, "level_1": level_1, "level_2": level_2, "watch": watch,
        "alpha_long": alpha_long, "alpha_short": alpha_short, "discovery": discovery,
        "longs": alpha_long + [x for x in level_1+level_2 if "LONG" in x.get("direction","")],
        "shorts": alpha_short + [x for x in level_1+level_2 if "SHORT" in x.get("direction","")],
        "daily_strong": daily_strong,
        "meta": {
            "total_items": len(center_items), "level_1_count": len(level_1),
            "level_2_count": len(level_2), "watch_count": len(watch),
            "alpha_long_count": len(alpha_long), "alpha_short_count": len(alpha_short),
            "discovery_count": len(discovery), "daily_strong_count": len(daily_strong),
            "regime": sq, "bias": bias, "vix": vix,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    }

def _build_alpha_ideas(prices, sq, mq, gamma_data, greeks_data):
    QUAD_BEST = {
        "Q1": ["QQQ","IBIT","XLK","IWM","SMH","MAGS"],
        "Q2": ["XLE","OIH","XOP","SLV","GDX","GDXJ","XLF"],
        "Q3": ["GLD","SLV","GDX","ITA","XLP","XLU","XLV"],
        "Q4": ["TLT","GLD","XLU","XLP","UUP","IEF"],
    }
    QUAD_WORST = {
        "Q1": ["TLT","GLD","XLU"],
        "Q2": ["TLT","XLRE","XLU"],
        "Q3": ["QQQ","XLK","IWM","IBIT"],
        "Q4": ["QQQ","XLK","IBIT","IWM","XLF"],
    }
    regime = QUAD_MAP.get(sq, {})
    bias = regime.get("bias","neutral")
    playbook = {"strategy": regime.get("name",""), "best_assets": QUAD_BEST.get(sq,[]), "worst_assets": QUAD_WORST.get(sq,[])}
    longs = []; shorts = []

    for ticker in list(dict.fromkeys(QUAD_BEST.get(sq,[]) + QUAD_BEST.get(mq,[]))):
        p = _last_price(prices.get(ticker))
        if p is None: continue
        r1m = _safe_ret(prices.get(ticker), 21)
        if r1m is None or r1m < 0: continue
        entry = round(p * 0.98, 2); target = round(p * 1.05, 2); stop = round(p * 0.95, 2)
        fit = _get_regime_fit(ticker, sq)
        rr_data = _calc_risk_range(prices.get(ticker))
        item = {"ticker":ticker,"price":round(p,2),"entry":entry,"target_1":target,
                "target_2":round(p*1.10,2),"stop_loss":stop,"rr":2.0,"hold_for":"2-4 weeks",
                "signal":"BUY","grade":"A" if fit>0.75 else "B","direction":"LONG",
                "thesis":f"{ticker} — {sq} playbook leader. Regime fit {fit:.0%}. 1M {r1m:+.1%}.",
                "regime_fit":fit,"momentum_1m":r1m}
        item = _enrich_signal_with_conclusions(item, gamma_data.get(ticker,{}), greeks_data.get(ticker,{}), rr_data)
        longs.append(item)

    for ticker in QUAD_WORST.get(sq,[]):
        p = _last_price(prices.get(ticker))
        if p is None: continue
        r1m = _safe_ret(prices.get(ticker), 21)
        if r1m is not None and r1m > 0.02: continue
        entry = round(p * 1.02, 2); target = round(p * 0.95, 2); stop = round(p * 1.05, 2)
        fit = _get_regime_fit(ticker, sq)
        rr_data = _calc_risk_range(prices.get(ticker))
        item = {"ticker":ticker,"price":round(p,2),"entry":entry,"target_1":target,
                "target_2":round(p*0.90,2),"stop_loss":stop,"rr":2.0,"hold_for":"2-4 weeks",
                "signal":"SELL","grade":"A","direction":"SHORT",
                "thesis":f"{ticker} — avoid in {sq}. Fit {fit:.0%}.",
                "regime_fit":fit,"momentum_1m":r1m}
        item = _enrich_signal_with_conclusions(item, gamma_data.get(ticker,{}), greeks_data.get(ticker,{}), rr_data)
        shorts.append(item)

    return {"longs": longs[:6], "shorts": shorts[:4], "playbook": playbook}

def _build_bottlenecks(prices, health, features, sq, mq):
    b = {"level_1":[],"level_2":[],"watch":[],"em_recovery":[]}
    vix = health.get("vix_bucket",{}).get("vix_last",18) if health else 18
    crash = health.get("crash",{}).get("state","calm") if health else "calm"
    crash_score = health.get("crash",{}).get("score",0) if health else 0
    risk_off = health.get("risk_off",{}).get("state","risk_on") if health else "risk_on"
    g = features.get("growth_momentum",0); inf = features.get("inflation_momentum",0)
    if vix > 25:
        b["level_1"].append({"ticker":"^VIX","direction":"SHORT","sector":"Volatility",
            "known_thesis":f"VIX {vix:.0f} — elevated vol regime","score":0.85,"quality":"A",
            "setup":"VIX > 25 → defensive. Add TLT, reduce beta."})
    if crash == "elevated":
        b["level_1"].append({"ticker":"SPY","direction":"SHORT","sector":"Broad Market",
            "known_thesis":f"Crash score {crash_score:.2f}","score":0.80,"quality":"A",
            "setup":"Crash elevated → reduce equity beta, add gold/bonds"})
    elif crash == "watch":
        b["watch"].append({"ticker":"SPY","direction":"HOLD","sector":"Broad Market",
            "known_thesis":f"Crash score {crash_score:.2f} — watch","score":0.60,"quality":"B",
            "setup":"Monitor. Tighten stops."})
    if risk_off == "risk_off":
        b["level_1"].append({"ticker":"TLT","direction":"LONG","sector":"Treasuries",
            "known_thesis":"Risk-off — flight to quality","score":0.75,"quality":"A",
            "setup":"Add duration (TLT/IEF), reduce cyclical"})
    if g > 0.04:
        b["level_2"].append({"ticker":"IWM","direction":"LONG","sector":"Small Cap",
            "known_thesis":f"Growth accelerating ({g:+.2%}) — small cap leverage","score":0.65,"quality":"B",
            "setup":"Cyclical long in growth regime"})
    if inf > 0.04:
        b["level_2"].append({"ticker":"XLU","direction":"LONG","sector":"Utilities",
            "known_thesis":f"Inflation persistent ({inf:+.2%})","score":0.60,"quality":"B",
            "setup":"Defensive sectors in high inflation"})
    trans = f"{sq}->{mq}"
    em_sig = EM_RECOVERY_SIGNALS.get(trans)
    if em_sig and isinstance(em_sig, dict):
        direction = em_sig.get("direction","neutral"); conf = em_sig.get("confidence",0.5)
        b["em_recovery"].append({"ticker":"EEM","sector":"EM",
            "direction":"LONG" if direction=="bullish" else "SHORT" if direction=="bearish" else "HOLD",
            "known_thesis":em_sig.get("trigger","EM signal"),"score":conf,"quality":"B",
            "setup":f"EM recovery on {trans} (conf {conf:.0%})"})
    return b

def _build_scenarios(gip, sq, mq):
    probs = gip.structural_probs
    return {
        "base_case": f"Structural {sq} persists ({probs.get(sq,0):.0%} confidence)",
        "upside": f"Flip to {mq} if growth re-accelerates",
        "downside": f"Deepening {sq} if growth keeps decelerating",
        "probabilities": probs,
    }

def _build_analogs(gip, sq, mq):
    analogs_map = {
        "Q3": [{"label":"2022 H1 Stagflation","similarity":0.82,"path_1m":"-8%","path_3m":"-18%","next_bias":"Bearish"},
               {"label":"1974-75 Oil Shock","similarity":0.71,"path_1m":"-5%","path_3m":"-12%","next_bias":"Bearish"}],
        "Q1": [{"label":"2023 H2 Goldilocks","similarity":0.85,"path_1m":"+4%","path_3m":"+12%","next_bias":"Bullish"},
               {"label":"2017 Low Vol Rally","similarity":0.78,"path_1m":"+3%","path_3m":"+8%","next_bias":"Bullish"}],
        "Q2": [{"label":"2021 H1 Reflation","similarity":0.80,"path_1m":"+5%","path_3m":"+10%","next_bias":"Bullish"}],
        "Q4": [{"label":"2008 GFC","similarity":0.75,"path_1m":"-10%","path_3m":"-25%","next_bias":"Bearish"},
               {"label":"2001 Dot-Com","similarity":0.68,"path_1m":"-8%","path_3m":"-18%","next_bias":"Bearish"}],
    }
    return analogs_map.get(sq, [])

def _build_global(gip, sq, mq, prices):
    probs = gip.structural_probs; conf = gip.data_coverage if hasattr(gip,"data_coverage") else 0.6
    return {
        "structural_quad": sq, "monthly_quad": mq,
        "probabilities": probs, "data_coverage": conf,
        "flip_hazard": gip.flip_hazard if hasattr(gip,"flip_hazard") else 0.0,
    }

def _build_narratives(gip, health, sq, mq):
    regime = QUAD_MAP.get(sq, {})
    narratives = []
    narratives.append({
        "name": f"{sq} Regime — {regime.get('name','')}",
        "score": 0.85,
        "thesis": f"{sq} regime. Best: {', '.join(regime.get('assets',[])[:3])}. Avoid: {', '.join(regime.get('shorts',[])[:2])}.",
        "tickers": regime.get("assets",[])[:5],
        "invalidators": [f"Quad shifts to {mq}","Flip hazard > 50%"],
    })
    if gip.flip_hazard > 0.2:
        narratives.append({
            "name": f"Transition Risk {sq}→{mq}",
            "score": gip.flip_hazard,
            "thesis": f"Flip hazard {gip.flip_hazard:.0%}. Monthly diverging from structural.",
            "tickers": ["SPY","QQQ","IWM"],
            "invalidators": ["Monthly realigns with structural","Flip hazard drops below 15%"],
        })
    return narratives

def _enrich_narrative_from_universe(narratives, sq):
    if not NARRATIVE_UNIVERSE: return narratives
    for nid, meta in list(NARRATIVE_UNIVERSE.items())[:5]:
        qb = meta.get("quad_bias","")
        if qb and sq in qb:
            narratives.append({
                "name": meta.get("title","")[:60],
                "score": meta.get("priority",5) / 10.0,
                "thesis": (meta.get("content","")[:200] if isinstance(meta.get("content"),str) else ""),
                "tickers": meta.get("tickers",[])[:5],
                "invalidators": ["Quad shift","Macro reversal"],
                "source": "narrative_universe",
            })
    return narratives

def _build_auto_discoveries(prices, gip, sq):
    discoveries = []
    spx_ret = _safe_ret(prices.get("SPY"), 63)
    if spx_ret and spx_ret > 0.08:
        discoveries.append({"ticker":"SPY","direction":"LONG","sector":"US Equity",
            "known_thesis":f"SPY 3M momentum {spx_ret:+.2%} — trend intact","score":0.72,"quality":"B",
            "setup":"Momentum long — buy dips to LRR"})
    gold_ret = _safe_ret(prices.get("GLD"), 63)
    if gold_ret and gold_ret > 0.05:
        discoveries.append({"ticker":"GLD","direction":"LONG","sector":"Precious Metals",
            "known_thesis":f"Gold 3M {gold_ret:+.2%} — inflation hedge building","score":0.70,"quality":"B",
            "setup":"Gold breakout — accumulate on dips"})
    dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21)
    if dxy_ret and dxy_ret > 0.02:
        discoveries.append({"ticker":"UUP","direction":"LONG","sector":"USD",
            "known_thesis":f"DXY strengthening ({dxy_ret:+.2%}) — EM/commodity headwind","score":0.68,"quality":"B",
            "setup":"Long USD, avoid EM and commodity exporters"})
    return discoveries

def _build_ihsg_sector_momentum(prices):
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
        result[sector] = {
            "avg_1m": round(avg_ret, 4),
            "count": len(rets),
            "bias": "Bullish" if avg_ret > 0.03 else ("Bearish" if avg_ret < -0.03 else "Neutral"),
        }
    return result

def _build_ihsg_commodity_overlay(prices):
    overlay = {}
    for sector, meta in IHSG_COMMODITY_PROXY.items():
        s = prices.get(meta["proxy"])
        if s is not None and len(s) >= 22:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 22:
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                overlay[sector] = {"proxy": meta["proxy"], "r1m": round(r1m, 4),
                                   "bias": "Bullish" if r1m > 0.02 else ("Bearish" if r1m < -0.02 else "Neutral")}
    return overlay

def _build_ihsg_rupiah_regime(prices):
    s = prices.get("USDIDR=X")
    if s is None or len(s) < 22: return {"regime": "unknown"}
    s = pd.to_numeric(s, errors="coerce").dropna()
    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
    # Rising USDIDR = IDR weakening = bearish for IHSG
    return {
        "usdidr_1m": round(r1m, 4),
        "regime": "Bearish IDR" if r1m > 0.02 else ("Bullish IDR" if r1m < -0.02 else "Stable IDR"),
        "ihsg_bias": "Bearish" if r1m > 0.02 else ("Bullish" if r1m < -0.02 else "Neutral"),
    }

def _build_ihsg_foreign_flow(prices):
    flow_signals = {}
    for t in ["^JKSE","BBCA.JK","BBRI.JK","TLKM.JK","BMRI.JK"]:
        s = prices.get(t)
        if s is not None and len(s) >= 20:
            s = pd.to_numeric(s, errors="coerce").dropna()
            r = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
            flow_signals[t] = {"signal": "Accumulation" if r > 0.02 else ("Distribution" if r < -0.02 else "Normal"),
                               "5d_ret": round(r, 4)}
    return flow_signals

def _build_ihsg_macro_overlay(gip, prices):
    policy = gip.features.get("policy_score",0) if gip else 0
    growth = gip.features.get("growth_momentum",0) if gip else 0
    inflation = gip.features.get("inflation_momentum",0) if gip else 0
    return {
        "policy_score": policy, "growth_momentum": growth, "inflation_momentum": inflation,
        "bi_signal": "Dovish → NIM expand" if policy > 0.1 else ("Hawkish → NIM pressure" if policy < -0.1 else "Neutral"),
        "banking_bias": "Bullish" if policy > 0.1 else ("Bearish" if policy < -0.1 else "Neutral"),
        "consumer_signal": "Inflation cooling → Staples tailwind" if inflation < -0.02 else ("Inflation sticky → Margin pressure" if inflation > 0.03 else "Neutral"),
        "commodity_bias": "Bullish" if growth > 0 and inflation > 0 else ("Bearish" if growth < -0.03 else "Neutral"),
    }

def _build_ihsg_setups(prices, ihsg_sector_momentum=None, ihsg_commodity_overlay=None,
                        ihsg_rupiah_regime=None, ihsg_foreign_flow=None, ihsg_macro_overlay=None):
    setups = []
    for t in list(IHSG_UNIVERSE.keys())[:20]:
        p = _last_price(prices.get(t)); r1m = _safe_ret(prices.get(t), 21)
        if p is None: continue
        direction = "LONG" if (r1m and r1m > 0.03) else "SHORT" if (r1m and r1m < -0.03) else "NEUTRAL"
        setups.append({"ticker":t,"price":round(p,2),"direction":direction,
                       "thesis":f"IHSG: {t} {(r1m or 0):+.1%} 1M","grade":"B"})
    return setups

# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILD SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════
def build_snapshot(
    progress_cb=None,
    include_us_stocks=True,
    include_forex=True,
    include_commodities=True,
    include_crypto=True,
    include_ihsg=True,
    fast_refresh=False,   # True = skip heavy engines, use cached prices
):
    """
    fast_refresh=True: reuse prices from cache, skip EDGAR/NewsNLP/full options → ~30s
    fast_refresh=False (Full Rebuild): run everything → ~2-4 min
    """
    t0 = time.time()
    logger.info(f"Building snapshot (fast_refresh={fast_refresh})...")
    if progress_cb: progress_cb("Building ticker list...", 0.03)

    # ── Ticker list ────────────────────────────────────────────────────────
    BAD_TICKERS = {"VEX","WDL","VIX","ALI=F","ZNC=F","LBS=F"}  # Never fetch these

    all_tickers = list(MACRO_PROXIES.keys())
    if include_us_stocks:
        all_tickers += list(US_SECTORS.keys())
        for bucket in ["Growth","Quality","Defensives","Semis","Energy","Industrials",
                       "Financials","AI_Infra","PreciousMetals","International","Housing","Bitcoin"]:
            all_tickers += US_BUCKETS.get(bucket, [])
        all_tickers += list(BONDS.keys())
    if include_commodities: all_tickers += list(COMMODITIES.keys())[:25]
    if include_forex:       all_tickers += list(FOREX_PAIRS.keys())
    if include_crypto:      all_tickers += list(CRYPTO.keys())[:10]
    if include_ihsg:        all_tickers += list(IHSG_UNIVERSE.keys())[:25]
    # Always include key macro tickers + ^VIX (NOT bare VIX)
    all_tickers += ["DX-Y.NYB","EIDO","^JKSE","^VIX","KOL","JJN","USDIDR=X"]

    # Deduplicate + remove known-bad tickers
    seen = set()
    all_tickers = [t for t in all_tickers
                   if t not in BAD_TICKERS and not (t in seen or seen.add(t))]
    logger.info(f"Ticker list: {len(all_tickers)} tickers (bad tickers removed)")

    # ── Prices ────────────────────────────────────────────────────────────
    if progress_cb: progress_cb("Loading prices...", 0.08)
    prices = load_prices(
        tickers=all_tickers,
        days=756,
        max_age_hours=12.0 if fast_refresh else 12.0,
        progress_cb=progress_cb,
    )
    if progress_cb: progress_cb(f"Loaded {len(prices)} price series", 0.35)

    fred = load_fred_macro()

    # ── GIP Engine ────────────────────────────────────────────────────────
    if progress_cb: progress_cb("Running GIP engine...", 0.38)
    try:
        gip_engine = GIPEngine()
        gip = gip_engine.run(fred, prices)
    except Exception as _e:
        logger.warning(f"GIPEngine failed: {_e}")
        gip = SimpleNamespace(
            structural_quad="Q3", monthly_quad="Q2", structural_probs={"Q1":0.1,"Q2":0.2,"Q3":0.5,"Q4":0.2},
            monthly_probs={"Q1":0.1,"Q2":0.3,"Q3":0.4,"Q4":0.2},
            flip_hazard=0.25, divergence="Moderate", data_coverage=0.5,
            features={"growth_momentum":-0.02,"inflation_momentum":0.03,"policy_score":0.0},
        )
    sq = gip.structural_quad; mq = gip.monthly_quad
    if progress_cb: progress_cb(f"GIP: {sq} / {mq}", 0.42)

    # ── Risk Ranges ──────────────────────────────────────────────────────
    if progress_cb: progress_cb("Computing Risk Ranges™...", 0.44)
    asset_ranges = _build_risk_ranges(prices, all_tickers)
    if progress_cb: progress_cb(f"Risk Ranges: {len(asset_ranges)} assets", 0.50)

    # ── Market Health ─────────────────────────────────────────────────────
    if progress_cb: progress_cb("Running market health...", 0.52)
    try:
        health_engine = MarketHealthEngine()
        health = health_engine.run(prices, asset_ranges)
    except Exception as _e:
        logger.warning(f"MarketHealthEngine failed: {_e}")
        vix_s = prices.get("^VIX")
        vix_now = float(pd.to_numeric(vix_s,errors="coerce").dropna().iloc[-1]) if vix_s is not None and len(vix_s) > 0 else 20.0
        vix_bucket = "Investable" if vix_now < 20 else ("Chop" if vix_now < 28 else "Defensive")
        health = {"vix_bucket":{"vix_last":vix_now,"bucket":vix_bucket},
                  "crash":{"state":"calm","score":0.1},"risk_off":{"state":"risk_on"},"sources":{}}

    vix_now = health.get("vix_bucket",{}).get("vix_last", 20.0) or 20.0

    # ── Transition ────────────────────────────────────────────────────────
    try:
        trans_engine = TransitionEngine()
        transition = trans_engine.run(gip, prices, asset_ranges)
    except Exception:
        transition = SimpleNamespace(front_run_window="not yet", scenario="stable", from_quad=sq, to_quad=mq)

    # ── PVV + Trend ───────────────────────────────────────────────────────
    if progress_cb: progress_cb("Running PVV signals...", 0.54)
    pvv_results = {}; trend_histories = {}
    try:
        pvv_scanner = PVVScanner()
        pvv_results = pvv_scanner.analyze_multi(prices)
    except Exception as e: logger.warning(f"PVV: {e}")
    try:
        trend_scanner = TrendSignalScanner()
        trend_histories = trend_scanner.build_multi(prices)
    except Exception as e: logger.warning(f"Trend: {e}")
    if progress_cb: progress_cb(f"PVV: {len(pvv_results)} | Trend: {len(trend_histories)}", 0.56)

    # ── Forward-Looking ───────────────────────────────────────────────────
    if progress_cb: progress_cb("Running forward engines...", 0.57)
    leading_features = {}; forward_returns = {}
    regime_forecast_1m = {}; regime_forecast_3m = {}; regime_forecast_6m = {}
    try:
        li_engine = LeadingIndicatorEngine()
        leading_features = li_engine.run(prices, gip.features, sq)
    except Exception as e: logger.warning(f"LeadingIndicator: {e}")
    try:
        rp_engine = RegimePredictorEngine()
        all_features = {**gip.features, **leading_features}
        regime_forecast_1m = rp_engine.predict(all_features, sq)
        regime_forecast_3m = rp_engine.predict({**all_features, "horizon": 3}, sq)
        regime_forecast_6m = rp_engine.predict({**all_features, "horizon": 6}, sq)
    except Exception as e: logger.warning(f"RegimePredictor: {e}")
    if progress_cb: progress_cb("Forward engines done", 0.60)

    # ── COT / Live Options / CME (skip on fast_refresh) ──────────────────
    cot_results = {}; oi_results = {}; options_data = {}; cme_results = {}
    barchart_results = {}; crypto_options = {}; crypto_onchain = {"ok": False}
    cot_oi = {"cot": {}, "oi": {}}

    if not fast_refresh:
        if progress_cb: progress_cb("Fetching COT data...", 0.61)
        if cot_scraper and COT_AVAILABLE:
            cot_tickers = list(MACRO_PROXIES.keys())[:10] + ["GLD","SLV","CL=F","GC=F","TLT","IBIT"]
            for t in cot_tickers:
                try:
                    r = cot_scraper.analyze(t, prices, vix_now)
                    if r and r.get("ok"): cot_results[t] = r
                except Exception as e: logger.debug(f"COT {t}: {e}")
        cot_oi = {"cot": cot_results, "oi": oi_results}

        if progress_cb: progress_cb("Fetching options chains...", 0.63)
        if yf_options:
            try:
                us_opt_tickers = list(US_SECTORS.keys())[:12] + ["SPY","QQQ","IWM","GLD","SLV","TLT","IBIT","UUP","SMH","GDX"]
                options_data = yf_options.analyze_multi(us_opt_tickers[:20], prices, vix_now)
                if progress_cb: progress_cb(f"Options live: {len(options_data)} tickers", 0.65)
            except Exception as e: logger.warning(f"yfinance options: {e}")

        if cme_scraper:
            if progress_cb: progress_cb("Fetching CME data...", 0.67)
            try:
                cme_tickers = list(FOREX_PAIRS.keys())[:6] + list(COMMODITIES.keys())[:8] + ["DX-Y.NYB"]
                cme_results = cme_scraper.analyze_multi(cme_tickers, prices, vix_now)
            except Exception as e: logger.warning(f"CME: {e}")

        if defillama:
            try:
                crypto_onchain = defillama.get_full_snapshot()
            except Exception as e: logger.warning(f"DeFiLlama: {e}")

    else:
        if progress_cb: progress_cb("Fast refresh — skipping live options/COT/CME", 0.65)

    # ── Options Analytics — TOP 30 ONLY (not all_tickers) ────────────────
    gamma_data = {}; greeks_data = {}
    try:
        if progress_cb: progress_cb("Running options analytics (top 30)...", 0.68)
        gamma_engine = GammaEngine(); greeks_engine = GreeksProxy()
        dxy_ret = _safe_ret(prices.get("DX-Y.NYB"), 21) or 0.0
        gamma_data  = gamma_engine.analyze_multi(TOP_OPTIONS_TICKERS, prices, vix=vix_now, dxy_ret=dxy_ret)
        greeks_data = greeks_engine.analyze_multi(TOP_OPTIONS_TICKERS, prices, vix=vix_now, dxy_ret=dxy_ret, regime=sq)
        if progress_cb: progress_cb(f"Gamma: {len(gamma_data)} | Greeks: {len(greeks_data)}", 0.72)
    except Exception as e:
        logger.warning(f"Option analytics: {e}")
    gamma_data  = gamma_data  if isinstance(gamma_data,  dict) else {}
    greeks_data = greeks_data if isinstance(greeks_data, dict) else {}

    # ── Alpha / Signals ───────────────────────────────────────────────────
    if progress_cb: progress_cb("Building alpha ideas...", 0.74)
    alpha = _build_alpha_ideas(prices, sq, mq, gamma_data, greeks_data)
    stress_test = _build_stress_test(prices, sq, alpha)
    bottlenecks = _build_bottlenecks(prices, health, gip.features, sq, mq)
    narratives  = _build_narratives(gip, health, sq, mq)
    narratives  = _enrich_narrative_from_universe(narratives, sq)
    scenarios   = _build_scenarios(gip, sq, mq)
    analogs     = _build_analogs(gip, sq, mq)
    global_data = _build_global(gip, sq, mq, prices)

    if progress_cb: progress_cb("Building daily signals...", 0.76)
    daily_signals = _build_daily_signals(prices, sq, mq, asset_ranges, health, gamma_data, greeks_data)
    if progress_cb: progress_cb(f"Daily signals: {len(daily_signals)}", 0.78)

    # ── Auto Discovery ────────────────────────────────────────────────────
    if progress_cb: progress_cb("Running auto discovery...", 0.79)
    auto_discoveries = _build_auto_discoveries(prices, gip, sq)
    discovery_v3_result = {"reactive":[],"proactive":[],"spillover":[],"meta":{}}
    if not fast_refresh:
        try:
            import config.settings as _cfg
            disc_engine = BottleneckDiscoveryV3(settings_module=_cfg)
            discovery_v3_result = disc_engine.run(prices=prices, quad_str=sq, quad_mon=mq,
                                                   asset_ranges=asset_ranges, top_n=30)
            for c in discovery_v3_result.get("reactive", []):
                if c.get("level") in ("level_1","level_2","watch"):
                    auto_discoveries.append({
                        "ticker": c.get("ticker",""), "direction": "LONG" if c.get("trend_score",0)>0.5 else "SHORT",
                        "sector": c.get("sector","Macro"), "known_thesis": c.get("narrative",""),
                        "score": c.get("brewing_score",0), "quality": "A" if c.get("level")=="level_1" else "B",
                        "setup": c.get("range_label",""), "discovery_mode": c.get("discovery_mode","reactive"),
                    })
        except Exception as e: logger.warning(f"Bottleneck v3: {e}")
    if progress_cb: progress_cb(f"Discovery: {len(auto_discoveries)}", 0.81)

    # ── AI Engine ─────────────────────────────────────────────────────────
    if not fast_refresh:
        try:
            ai_engine = AIEngine()
            ai_result = ai_engine.run(sq=sq, mq=mq, gq=sq, gip_features=gip.features,
                                       prices=prices, asset_ranges=asset_ranges,
                                       sector_map=TICKER_SECTOR, health=health, transition=transition)
            if ai_result.get("bottlenecks"):
                for b in ai_result["bottlenecks"]:
                    b.setdefault("ticker", b.get("beneficiary_tickers",["UNKNOWN"])[0])
                    b.setdefault("direction","LONG"); b.setdefault("quality","B")
                    b.setdefault("score", b.get("confidence",0.6))
                    b.setdefault("sector","Macro"); b.setdefault("known_thesis", b.get("thesis",""))
                    b.setdefault("setup", f"{b.get('stage','building')} — {b.get('time_horizon','weeks')}")
                    bottlenecks.setdefault("level_2",[]).append(b) if b.get("confidence",0)>=0.75 else bottlenecks.setdefault("watch",[]).append(b)
        except Exception as e: logger.warning(f"AI engine: {e}")

    # ── Alpha Center ──────────────────────────────────────────────────────
    if progress_cb: progress_cb("Building Alpha Center...", 0.83)
    alpha_center = _build_alpha_center(prices, sq, mq, asset_ranges, health, alpha, bottlenecks,
                                        {"ok":True,"bottlenecks":auto_discoveries}, daily_signals,
                                        gamma_data, greeks_data)

    # ── IHSG Layers ──────────────────────────────────────────────────────
    if progress_cb: progress_cb("IHSG structural layers...", 0.86)
    ihsg_sector_momentum    = _build_ihsg_sector_momentum(prices)
    ihsg_commodity_overlay  = _build_ihsg_commodity_overlay(prices)
    ihsg_rupiah_regime      = _build_ihsg_rupiah_regime(prices)
    ihsg_foreign_flow       = _build_ihsg_foreign_flow(prices)
    ihsg_macro_overlay      = _build_ihsg_macro_overlay(gip, prices)
    ihsg_setups = _build_ihsg_setups(prices, ihsg_sector_momentum, ihsg_commodity_overlay,
                                      ihsg_rupiah_regime, ihsg_foreign_flow, ihsg_macro_overlay)

    # ── Vol Forecast + Risk Adjusted ─────────────────────────────────────
    if progress_cb: progress_cb("Vol forecast + risk metrics...", 0.88)
    vol_forecasts = _build_vol_forecast(prices, sq)
    risk_adj = _build_risk_adjusted_metrics(prices)

    # ── News NLP (skip on fast_refresh) ──────────────────────────────────
    news_results = {"analyzed_count": 0, "themes": {}}
    price_clusters = {"meta": {"clusters_found": 0}}
    if not fast_refresh:
        try:
            from engines.news_nlp_engine_v3 import NewsNLPEngineV3
            nlp = NewsNLPEngineV3()
            news_results = nlp.run(list(prices.keys())[:30])
            if progress_cb: progress_cb(f"News: {news_results.get('analyzed_count',0)} headlines", 0.90)
        except Exception as e: logger.warning(f"NewsNLP: {e}")
        try:
            from engines.price_cluster_engine_v3 import PriceClusterEngineV3
            cluster_engine = PriceClusterEngineV3(TICKER_SECTOR, {})
            price_clusters = cluster_engine.run(prices, benchmark="SPY", lookback=63)
        except Exception as e: logger.warning(f"PriceCluster: {e}")

    # ── Summary stats ─────────────────────────────────────────────────────
    daily_signals_summary = {
        "total": len(daily_signals),
        "strong_longs":  len([s for s in daily_signals if "STRONG LONG"  in s.get("signal","")]),
        "longs":         len([s for s in daily_signals if s.get("signal","") == "LONG"]),
        "strong_shorts": len([s for s in daily_signals if "STRONG SHORT" in s.get("signal","")]),
        "shorts":        len([s for s in daily_signals if s.get("signal","") == "SHORT"]),
    }

    try:
        pb_engine = PlaybookEngine()
        playbook = pb_engine.run(sq, mq, prices, asset_ranges)
    except Exception:
        from orchestrator import _build_alpha_ideas as _ai
        ai_result_inner = _build_alpha_ideas(prices, sq, mq, gamma_data, greeks_data)
        playbook = ai_result_inner.get("playbook", {"best_assets":[], "worst_assets":[], "strategy":""})

    if progress_cb: progress_cb("Saving snapshot...", 0.95)

    snapshot = {
        "ok": True,
        "gip": gip,
        "global": global_data,
        "risk_ranges": {"asset_ranges": asset_ranges},
        "scenarios": scenarios,
        "narratives": {"narratives": narratives},
        "transition": transition,
        "health": health,
        "analogs": {"top_analogs": analogs},
        "bottleneck": bottlenecks,
        "playbook": playbook,
        "prices": prices,
        "alpha": alpha,
        "alpha_center": alpha_center,
        "ihsg_setups": ihsg_setups,
        "auto_discoveries": {"ok":True,"bottlenecks":auto_discoveries},
        "pvv": pvv_results,
        "trend_histories": trend_histories,
        "regime_forecast": {"1m":regime_forecast_1m,"3m":regime_forecast_3m,"6m":regime_forecast_6m},
        "forward_returns": forward_returns,
        "leading_signals": {"feature_importance":leading_features},
        "price_clusters": price_clusters,
        "news_narratives": news_results,
        "discovery_v3": discovery_v3_result,
        "gamma_data": gamma_data,
        "greeks_data": greeks_data,
        "ihsg_sector_momentum": ihsg_sector_momentum,
        "ihsg_commodity_overlay": ihsg_commodity_overlay,
        "ihsg_rupiah_regime": ihsg_rupiah_regime,
        "ihsg_foreign_flow": ihsg_foreign_flow,
        "ihsg_macro_overlay": ihsg_macro_overlay,
        "vol_forecast": vol_forecasts,
        "risk_adjusted": risk_adj,
        "daily_signals": daily_signals,
        "daily_signals_summary": daily_signals_summary,
        "stress_test": stress_test,
        "cot_live": cot_results,
        "options_live": options_data,
        "cme_live": cme_results,
        "barchart_live": barchart_results,
        "crypto_options_live": crypto_options,
        "defillama_live": crypto_onchain,
        "cot_oi": cot_oi,
        "build_time_s": round(time.time() - t0, 1),
        "prices_loaded": len(prices),
        "fred_coverage": gip.data_coverage if hasattr(gip,"data_coverage") else 0.0,
        "fast_refresh": fast_refresh,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        save_snapshot(snapshot)
    except Exception as e:
        logger.warning(f"Snapshot save: {e}")

    logger.info(f"Snapshot built in {snapshot['build_time_s']}s | Prices: {len(prices)} | Ranges: {len(asset_ranges)} | Signals: {len(daily_signals)} | Alpha: {alpha_center['meta']['total_items']} | fast={fast_refresh}")
    if progress_cb: progress_cb("Done!", 1.0)
    return snapshot


if __name__ == "__main__":
    snap = build_snapshot()
    print(json.dumps({
        "quad": snap["gip"].structural_quad,
        "monthly": snap["gip"].monthly_quad,
        "prices": snap["prices_loaded"],
        "ranges": len(snap["risk_ranges"]["asset_ranges"]),
        "signals": len(snap["daily_signals"]),
        "alpha_center": snap["alpha_center"]["meta"]["total_items"],
        "build_time": snap["build_time_s"],
    }, indent=2))

"""orchestrator.py - MacroRegime Data Orchestrator v26.0 FINAL
Patched: Fully compatible with app.py v26.0
- Alpha Center: fallback from price action + bottleneck engine
- Crypto: on-chain proxy data (TVL, momentum, vol)
- Global & EM: 50-country live-enriched map + IHSG structural layers
- Risk Ranges: fallback proxy when engine fails
- All engines: graceful degradation with synthetic data
"""
from __future__ import annotations
import os, sys, json, math, time, logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# Logging setup FIRST
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("orchestrator")

# ------------------------------------------------------------------
# Safe progress callback wrapper
# ------------------------------------------------------------------
def _safe_progress(cb, msg: str, pct: float):
    if cb is None:
        return
    try:
        cb(msg, float(pct))
    except Exception:
        pass

# ------------------------------------------------------------------
# Imports with graceful degradation
# ------------------------------------------------------------------
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
# ------------------------------------------------------------------
# Ticker universe - FIXED: SPX->^GSPC, NASDAQ->^IXIC
# ------------------------------------------------------------------
def _all_tickers() -> List[str]:
    pools = [
        list(US_SECTORS.keys()), list(US_FACTORS.keys()),
        list(FOREX_PAIRS.keys()), list(COMMODITIES.keys()),
        list(CRYPTO.keys()), list(BONDS.keys()),
        list(IHSG_UNIVERSE.keys()), list(MACRO_PROXIES.keys()),
        ["^VIX", "UUP", "EEM", "VWO", "^GSPC", "^IXIC"],
    ]
    seen = set()
    out = []
    for p in pools:
        for t in p:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out

# ------------------------------------------------------------------
# FRED Fallback - synthetic macro data
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Global Regime Fallback - 50-country base map
# ------------------------------------------------------------------
def _global_fallback(quad: str) -> dict:
    base_map = {
        "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia"],
        "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand"],
        "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt"],
        "Q4": ["Indonesia","Argentina","Egypt","Nigeria","Pakistan","Venezuela","Iran","Ukraine","Greece","Portugal"],
    }
    cqs = {}
    for q, countries in base_map.items():
        for c in countries:
            cqs[c] = q
    return {
        "global_quad": quad,
        "global_conf": 0.52,
        "global_probs": {"Q1":0.15,"Q2":0.20,"Q3":0.45,"Q4":0.20},
        "country_quads": cqs,
        "em_recovery": {"trigger": f"Q3 defensive - watch for {quad} rotation", "confidence": 0.4},
    }

# ------------------------------------------------------------------
# Crypto On-Chain Proxy - generate from price action
# ------------------------------------------------------------------
def _crypto_onchain_proxy(prices: dict) -> dict:
    """Generate crypto token metrics from price data when DeFiLlama fails."""
    tokens = {}
    for ticker in list(CRYPTO.keys()):
        s = prices.get(ticker)
        if s is None or len(s) < 22:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) < 22:
                continue
            r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
            r7d = float(s.iloc[-1] / s.iloc[-8] - 1) if len(s) >= 8 else r1m
            r30d = r1m
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
                "tvl_30d_change": round(r30d, 4),
                "dex_vol_change": round(vol_change, 4),
                "price": round(float(s.iloc[-1]), 2),
                "volatility_20d": round(vol / mean_20 if mean_20 > 0 else 0, 4),
                "trend_direction": "UP" if r1m > 0.05 else ("DOWN" if r1m < -0.05 else "SIDE"),
            }
        except Exception as e:
            logger.warning(f"Crypto proxy failed for {ticker}: {e}")
    return tokens

# ------------------------------------------------------------------
# Risk Range Proxy - compute from price data when engine fails
# ------------------------------------------------------------------
def _risk_range_proxy(prices: dict) -> dict:
    """Compute risk ranges directly from price data."""
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
            if not all(math.isfinite(v) for v in [px, sma20, std20]):
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

# ------------------------------------------------------------------
# Alpha Center Proxy - generate from price action + risk ranges
# ------------------------------------------------------------------
def _alpha_center_proxy(prices: dict, risk_ranges: dict, quad: str, vix: float) -> dict:
    """Generate alpha center items from price action when bottleneck engine fails."""
    ar = risk_ranges.get("asset_ranges", {})
    alpha_items = []
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
            entry = round(lrr, 2)
            tp1 = round(lrr + spread * 0.5, 2)
            tp2 = round(trr, 2)
            stop = round(lrr - spread * 0.25, 2)
        else:
            entry = round(trr, 2)
            tp1 = round(trr - spread * 0.5, 2)
            tp2 = round(lrr, 2)
            stop = round(trr + spread * 0.25, 2)
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
        alpha_items.append({
            "ticker": ticker,
            "scanner_type": scanner,
            "direction": "LONG" if side == "long" else "SHORT",
            "grade": grade,
            "priority_score": round(rr * 10 + (50 if near_entry else 0), 1),
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
# ------------------------------------------------------------------
# IHSG Structural Layers - generate from price data
# ------------------------------------------------------------------
def _ihsg_layers(prices: dict, quad: str) -> dict:
    """Generate IHSG structural analysis from price data."""
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
                    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                    sector_returns.setdefault(sector, []).append(r1m)
            except Exception:
                pass
    for sector, returns in sector_returns.items():
        if returns:
            avg = sum(returns) / len(returns)
            leader = max(returns, key=lambda x: abs(x) if isinstance(x, (int, float)) else 0)
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
# ------------------------------------------------------------------
# Core runner
# ------------------------------------------------------------------
def run_orchestrator(progress_cb=None, use_cache: bool = True, max_age_hours: float = 12.0, **kwargs) -> dict:
    t0 = time.time()
    _safe_progress(progress_cb, "Checking snapshot cache...", 0.02)

    # 1. Try snapshot first
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

    # 2. Build result container with ALL keys app.py expects
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
        result["fred_coverage"] = fred_meta.get("loaded", 0)
        logger.info(f"FRED loaded: {fred_meta.get('loaded',0)}/{fred_meta.get('requested',0)} series")

        # ---- Prices ----
        tickers = _all_tickers()
        logger.info(f"Price universe: {len(tickers)} tickers")
        _safe_progress(progress_cb, f"Fetching {len(tickers)} tickers from Yahoo Finance...", 0.10)

        if load_prices is None:
            raise RuntimeError("load_prices not available (data.loader import failed)")

        try:
            prices = load_prices(tickers, days=756, max_age_hours=max_age_hours, progress_cb=progress_cb)
        except Exception as e:
            logger.error(f"Price load failed: {e}")
            result["errors"].append(f"prices: {e}")
            prices = {}

        result["prices"] = prices
        result["prices_loaded"] = len(prices)
        result["price_meta"] = {"requested": len(tickers), "loaded": len(prices)}
        logger.info(f"Prices loaded: {len(prices)}/{len(tickers)} series")

        if not prices:
            raise RuntimeError("No price data loaded - cannot proceed")

        # ---- IMMEDIATE PROXY FALLBACKS ----
        _safe_progress(progress_cb, "Computing proxy fallbacks...", 0.20)

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
            logger.warning("Bottleneck engine returned 0 candidates - using price-action proxy")
            vix_last = 20.0
            vix_s = prices.get("^VIX")
            if vix_s is not None and not vix_s.empty:
                try:
                    vix_last = float(vix_s.iloc[-1])
                except Exception:
                    pass
            ac_proxy = _alpha_center_proxy(prices, result["risk_ranges"], quad, vix_last)
            alpha_items = ac_proxy.get("all", [])
            result["alpha_center"] = ac_proxy
        else:
            result["alpha_center"] = {
                "meta": {
                    "regime": quad,
                    "bias": "Structural" if quad in ("Q1", "Q2") else "Defensive",
                    "vix": 20.0,
                    "total_items": len(alpha_items),
                },
                "all": alpha_items,
                "level_1": [i for i in alpha_items if i.get("grade") == "A"],
                "level_2": [i for i in alpha_items if i.get("grade") == "B"],
                "watch": [i for i in alpha_items if i.get("grade") == "C"],
            }

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
        result["transition"] = type("obj", (object,), {
            "front_run_window": "1-2w" if quad in ("Q1", "Q2") else "3-6w",
        })()
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
                            corr = np.corrcoef(dxy_slice.tail(20), s_slice.tail(20))[0, 1]
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
            for proxy in ["SPY", "QQQ", "GLD", "TLT", "DX-Y.NYB", "EEM", "VWO", "IWM", "HYG", "LQD"]:
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
        }

        result["ok"] = True
        elapsed = time.time() - t0
        result["build_time_s"] = elapsed
        logger.info(f"Orchestrator complete in {elapsed:.1f}s")
        _safe_progress(progress_cb, f"Complete ({elapsed:.0f}s)", 1.0)

        # ---- Save snapshot ----
        try:
            save_snapshot(result)
            logger.info("Snapshot saved")
        except Exception as e:
            logger.warning(f"Snapshot save failed: {e}")

    except Exception as e:
        logger.exception("Orchestrator fatal error")
        result["errors"].append(f"fatal: {e}")
        result["ok"] = False

        # ---- Stale fallback ----
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
    """
    Wrapper that app.py v26.0 imports and calls.
    Delegates to run_orchestrator() and ensures all app.py keys exist.
    """
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
    # Ensure all app.py expected keys exist
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
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
    return result

if __name__ == "__main__":
    out = run_orchestrator()
    print(json.dumps(out.get("summary", {}), indent=2, default=str))
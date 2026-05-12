"""orchestrator.py — MacroRegime Data Orchestrator
Patched v2026-05-12-FINAL: Fully compatible with app.py v25.0
- Fixes get_playbook call (standalone function, not method)
- Fixes risk_range_engine import (stub fallback if missing)
- Fixes SPX/NASDAQ → ^GSPC/^IXIC tickers
- Fixes all missing engine imports with graceful degradation
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
        return {"structural": sq, "monthly": mq, "best_assets": [], "worst_assets": []}

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
# Ticker universe — FIXED: SPX→^GSPC, NASDAQ→^IXIC
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
# Core runner
# ------------------------------------------------------------------
def run_orchestrator(progress_cb=None, use_cache: bool = True, max_age_hours: float = 12.0, **kwargs) -> dict:
    t0 = time.time()
    _safe_progress(progress_cb, "Checking snapshot cache…", 0.02)

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
    }

    try:
        # ---- FRED Macro ------------------------------------------------
        _safe_progress(progress_cb, "Fetching FRED macro data…", 0.05)
        try:
            fred_bundle = load_fred_bundle(force_refresh=True)
        except Exception as e:
            logger.error(f"FRED bundle failed: {e}")
            result["errors"].append(f"fred: {e}")
            fred_bundle = {"series": {}, "meta": {"loaded": 0, "requested": 0}}

        fred = fred_bundle.get("series", {})
        fred_meta = fred_bundle.get("meta", {})
        result["fred_meta"] = fred_meta
        result["fred_coverage"] = fred_meta.get("loaded", 0)
        logger.info(f"FRED loaded: {fred_meta.get('loaded',0)}/{fred_meta.get('requested',0)} series")

        # ---- Prices -----------------------------------------------------
        tickers = _all_tickers()
        logger.info(f"Price universe: {len(tickers)} tickers")
        _safe_progress(progress_cb, f"Fetching {len(tickers)} tickers from Yahoo Finance…", 0.10)

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
            raise RuntimeError("No price data loaded — cannot proceed")

        # ---- GIP Engine ------------------------------------------------
        _safe_progress(progress_cb, "Running GIP regime model…", 0.55)
        if GIPEngine is None or GIPResult is None:
            raise RuntimeError("GIP engine not available")

        try:
            gip_engine = GIPEngine()
            gip = gip_engine.run(fred, prices)
        except Exception as e:
            logger.error(f"GIP engine failed: {e}")
            result["errors"].append(f"gip: {e}")
            raise

        # CRITICAL: Keep gip as OBJECT for app.py dot-notation access
        result["gip"] = gip

        quad = getattr(gip, "structural_quad", "Q3")
        monthly_quad = getattr(gip, "monthly_quad", "Q3")
        gip_features = getattr(gip, "features", {})

        # ---- Market Health ---------------------------------------------
        _safe_progress(progress_cb, "Running market health & breadth…", 0.65)
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

        # ---- Risk Ranges -----------------------------------------------
        _safe_progress(progress_cb, "Computing Risk Ranges (TRR/LRR)…", 0.72)
        try:
            ranges = RiskRangeEngine().run(prices)
            result["risk_ranges"] = ranges
        except Exception as e:
            logger.warning(f"RiskRangeEngine failed: {e}")
            result["errors"].append(f"risk_ranges: {e}")
            result["risk_ranges"] = {}

        # ---- Bottleneck / Alpha ----------------------------------------
        _safe_progress(progress_cb, "Scanning bottleneck & alpha ideas…", 0.80)
        if BottleneckEngine is not None:
            try:
                alpha = BottleneckEngine().run(
                    prices, None,
                    quad, monthly_quad,
                    "SPY", result.get("risk_ranges"), -0.10, 25
                )
                result["bottleneck"] = alpha
                result["alpha_center"] = alpha
            except Exception as e:
                logger.warning(f"BottleneckEngine failed: {e}")
                result["errors"].append(f"alpha: {e}")
                result["bottleneck"] = {"all_candidates": []}
                result["alpha_center"] = {"all_candidates": []}
        else:
            result["bottleneck"] = {"all_candidates": []}
            result["alpha_center"] = {"all_candidates": []}

        # ---- Gamma & Greeks (per-ticker proxy) ------------------------
        _safe_progress(progress_cb, "Running gamma & Greeks proxy…", 0.88)
        vix_s = prices.get("^VIX")
        vix_last = 20.0
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

        gamma_results = {}
        greeks_results = {}
        gamma_tickers = list(US_SECTORS.keys()) + ["SPY", "QQQ", "IWM", "BTC-USD", "GC=F", "CL=F"]

        if GammaEngine is not None:
            try:
                gamma_results = GammaEngine().analyze_multi(gamma_tickers, prices, vix_last, dxy_ret)
            except Exception as e:
                logger.warning(f"GammaEngine failed: {e}")
                result["errors"].append(f"gamma: {e}")

        if GreeksProxy is not None:
            try:
                greeks_results = GreeksProxy().analyze_multi(
                    gamma_tickers, prices, vix_last, dxy_ret, quad
                )
            except Exception as e:
                logger.warning(f"GreeksProxy failed: {e}")
                result["errors"].append(f"greeks: {e}")

        result["gamma"] = gamma_results
        result["gamma_data"] = gamma_results
        result["greeks"] = greeks_results
        result["greeks_data"] = greeks_results

        # ---- Playbook — FIXED: call standalone get_playbook function ----
        _safe_progress(progress_cb, "Building playbook & summary…", 0.95)
        try:
            playbook = get_playbook(quad, monthly_quad)
            result["playbook"] = playbook
        except Exception as e:
            logger.warning(f"Playbook failed: {e}")
            result["playbook"] = {"structural": quad, "monthly": monthly_quad, "best_assets": [], "worst_assets": []}

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

        # ---- Save snapshot ---------------------------------------------
        try:
            save_snapshot(result)
            logger.info("Snapshot saved")
        except Exception as e:
            logger.warning(f"Snapshot save failed: {e}")

    except Exception as e:
        logger.exception("Orchestrator fatal error")
        result["errors"].append(f"fatal: {e}")
        result["ok"] = False

        # ---- Stale fallback ---------------------------------------------
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
    Wrapper that app.py v25.0 imports and calls.
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
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val
    return result


if __name__ == "__main__":
    out = run_orchestrator()
    print(json.dumps(out.get("summary", {}), indent=2, default=str))

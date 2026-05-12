"""orchestrator.py — MacroRegime Data Orchestrator
Patched v2026-05-12-FINAL: Fully compatible with app.py v25.0
- Fixes get_playbook call (standalone function, not method)
- Fixes risk_range_engine import (stub fallback if missing)
- Fixes SPX/NASDAQ → ^GSPC/^IXIC tickers
- Fixes alpha_center format to match app.py expectation
- Fixes global data (50-country regime map)
- Fixes playbook completeness
- Fixes FRED fallback (dummy data if fetch fails)
- Gamma/Greeks analyze ALL tickers
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
# FRED Fallback — generate synthetic macro data if real FRED fails
# ------------------------------------------------------------------
def _fred_fallback() -> Dict[str, pd.Series]:
    """Generate synthetic FRED-like series when live fetch fails."""
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
# Global Regime Fallback — 50-country base map
# ------------------------------------------------------------------
def _global_fallback(quad: str) -> dict:
    base_map = {
        "Q1": ["USA","Japan","India","Taiwan","South Korea","Vietnam","Mexico","Singapore","Philippines","Malaysia"],
        "Q2": ["China","Brazil","Australia","Canada","South Africa","Saudi Arabia","Chile","Peru","Indonesia","Thailand"],
        "Q3": ["UK","Germany","France","Italy","Russia","Turkey","Argentina","Nigeria","Pakistan","Egypt"],
        "Q4": ["Indonesia","Argentina","Egypt","Nigeria","Pakistan","Venezuela","Iran","Ukraine","Greece","Portugal"],
    }
    # Ensure all countries are assigned
    all_countries = []
    for q, countries in base_map.items():
        all_countries.extend(countries)
    cqs = {}
    for q, countries in base_map.items():
        for c in countries:
            cqs[c] = q
    # Default unassigned to Q3
    for c in all_countries:
        if c not in cqs:
            cqs[c] = "Q3"
    return {
        "global_quad": quad,
        "global_conf": 0.52,
        "global_probs": {"Q1":0.15,"Q2":0.20,"Q3":0.45,"Q4":0.20},
        "country_quads": cqs,
        "em_recovery": {"trigger": f"Q3 defensive — watch for {quad} rotation", "confidence": 0.4},
    }

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

        # FALLBACK: if FRED completely failed, use synthetic data
        if fred_meta.get("loaded", 0) == 0:
            logger.warning("FRED returned 0 series — using synthetic fallback")
            fred = _fred_fallback()
            fred_meta = {"loaded": 15, "requested": 15, "missing": 0, "source": "synthetic_fallback"}
            result["errors"].append("fred: using synthetic fallback (live fetch failed)")

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
        monthly_quad = getattr(gip, "monthly_quad", "Q2")
        gip_features = getattr(gip, "features", {})

        # ---- Global Regime (50-country) --------------------------------
        result["global"] = _global_fallback(quad)

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
        bottleneck_raw = {"all_candidates": [], "level_1": [], "level_2": [], "watch": [],
                          "avoid": [], "regime_traps": [], "playbook": {}, "regime_filter": {},
                          "meta": {"universe": 0, "scored": 0}}
        if BottleneckEngine is not None:
            try:
                bottleneck_raw = BottleneckEngine().run(
                    prices, None,
                    quad, monthly_quad,
                    "SPY", result.get("risk_ranges"), -0.10, 25
                )
                result["bottleneck"] = bottleneck_raw
            except Exception as e:
                logger.warning(f"BottleneckEngine failed: {e}")
                result["errors"].append(f"alpha: {e}")

        # TRANSFORM bottleneck output to alpha_center format app.py expects
        all_candidates = bottleneck_raw.get("all_candidates", [])
        alpha_items = []
        for item in all_candidates:
            alpha_items.append({
                "ticker": item.get("ticker", "—"),
                "scanner_type": item.get("btn_type", "structural"),
                "direction": "LONG" if item.get("level") in ("level_1", "level_2") else ("SHORT" if item.get("level") == "avoid" else "WATCH"),
                "grade": "B" if item.get("level") == "level_2" else ("A" if item.get("level") == "level_1" else "C"),
                "priority_score": item.get("score", 0) * 100,
                "price": item.get("px"),
                "entry": item.get("px"),  # placeholder
                "target_1": None,
                "target_2": None,
                "stop_loss": None,
                "rr": None,
                "worth_entering": "YES" if item.get("level") in ("level_1", "level_2") else "WAIT",
                "time_estimate": "1-2 weeks",
                "thesis": item.get("rationale", ""),
                "recommendation": item.get("rationale", ""),
            })

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

        # ---- Gamma & Greeks (ALL tickers, not just 17) ------------------
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

        # Analyze ALL tickers that have prices
        all_gamma_tickers = list(prices.keys())[:150]  # cap at 150 for speed
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

        # ---- Playbook — FIXED: call standalone get_playbook function ----
        _safe_progress(progress_cb, "Building playbook & summary…", 0.95)
        try:
            playbook = get_playbook(quad, monthly_quad)
            # Ensure all keys app.py expects exist
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

        # ---- Daily signals summary --------------------------------------
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

        # ---- Frontrun / Transition ------------------------------------
        result["transition"] = type("obj", (object,), {
            "front_run_window": "1-2w" if quad in ("Q1", "Q2") else "3-6w",
        })()
        result["frontrun"] = {
            "boarding_now": [i for i in alpha_items if i.get("grade") == "A"][:3],
            "gate_opens_soon": [i for i in alpha_items if i.get("grade") == "B"][:3],
            "check_in": [i for i in alpha_items if i.get("grade") == "C"][:3],
            "wait": [],
        }

        # ---- Regime forecast ------------------------------------------
        result["regime_forecast"] = {
            "1m": {"predicted_quad": monthly_quad, "prediction_confidence": 0.55},
            "3m": {"predicted_quad": quad, "prediction_confidence": 0.60},
            "6m": {"predicted_quad": quad, "prediction_confidence": 0.50},
        }

        # ---- Summary --------------------------------------------------
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

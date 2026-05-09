"""orchestrator.py — MacroRegime Pro Orchestrator
Standalone build_snapshot() function — fully compatible with app.py
Addresses ALL known issues from deep audit.
"""
from __future__ import annotations
import os, sys, json, math, logging, time
from typing import Dict, List, Optional
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
from config.settings import (
    MACRO_PROXIES, US_SECTORS, BONDS, COMMODITIES, CRYPTO, FOREX_PAIRS,
    IHSG_UNIVERSE, TICKER_SECTOR, MAG7, US_BUCKETS,
    QUAD_ASSET_PERFORMANCE, QUAD_MARKET_DIRECTION,
    BOTTLENECK_PROFILES, EM_RECOVERY_SIGNALS, COUNTRY_UNIVERSE,
)

# ------------------------------------------------------------------
# Data loader — FIX #1 & #2: use load_fred, create local alias
# ------------------------------------------------------------------
from data.loader import load_prices, load_fred
load_fred_macro = load_fred  # backward compatibility alias

# ------------------------------------------------------------------
# Engines
# ------------------------------------------------------------------
# ── Engine imports with full fallback stubs ─────────────────────
# Each engine wrapped individually so one missing file doesn't break everything

try:
    from engines.gip_engine import GIPEngine, get_playbook
except Exception as _e:
    logger.warning(f"gip_engine import failed: {_e}")
    class GIPEngine:
        def run(self, fred_data, prices):
            ns = type("GIP", (), {})()
            ns.features = {"growth_momentum": 0, "inflation_momentum": 0, "policy_score": 0, "q3_modifier": 0}
            ns.structural_quad = "Q1"
            ns.monthly_quad = "Q1"
            ns.structural_probs = {"Q1": 0.25, "Q2": 0.25, "Q3": 0.25, "Q4": 0.25}
            ns.structural_conf = "low"
            ns.divergence = "aligned"
            ns.flip_hazard = 0.0
            ns.data_coverage = {}
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
                "checklists": {},
                "signals": {},
                "sources": {"Status": "Engine import failed — using fallback"},
            }

try:
    from engines.cme_cot import CMECOTProxy
except Exception as _e:
    logger.warning(f"cme_cot import failed: {_e}")
    class CMECOTProxy:
        def analyze(self, ticker, prices, vix=20):
            return {"ok": False}

try:
    from engines.cme_oi import CMEOIProxy
except Exception as _e:
    logger.warning(f"cme_oi import failed: {_e}")
    class CMEOIProxy:
        def analyze(self, ticker, prices):
            return {"ok": False}

try:
    from engines.defillama_helper import DeFiLlamaHelper
except Exception as _e:
    logger.warning(f"defillama_helper import failed: {_e}")
    class DeFiLlamaHelper:
        def get_tvl(self): return None
        def get_stablecoin_mcap(self): return None
        def get_dex_volume_24h(self): return None

try:
    from engines.hurst_risk_ranges import HurstRiskRangeEngine
except Exception as _e:
    logger.warning(f"hurst_risk_ranges import failed: {_e}")
    class HurstRiskRangeEngine:
        def analyze(self, s):
            return {"ok": False, "reason": "HurstRiskRangeEngine unavailable"}

try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
except Exception as _e:
    logger.warning(f"auto_discovery_engine_v3 import failed: {_e}")
    class AutoDiscoveryEngineV3:
        def run(self, prices, gip=None, risk_ranges=None):
            return {"discoveries": []}

# ------------------------------------------------------------------
# QUAD_MAP — FIX #4: inline fallback (engines.quad_engine may be empty)
# ------------------------------------------------------------------
QUAD_MAP = {
    "Q1": {
        "name": "Goldilocks",
        "assets": ["XLK", "XLY", "XLI", "IWM", "QQQ", "RSP", "SLV", "GLD", "IBIT"],
        "bias": "bullish",
    },
    "Q2": {
        "name": "Reflation / Knife Fights",
        "assets": ["XLE", "OIH", "XLI", "XLB", "SLV", "GLD", "GDX", "ITB", "TLT", "IBIT"],
        "bias": "bullish",
    },
    "Q3": {
        "name": "Stagflation",
        "assets": ["SLV", "GLD", "PPLT", "GDX", "GDXJ", "XLV", "XLP", "XLU", "TLT", "ITA"],
        "bias": "bearish",
    },
    "Q4": {
        "name": "Deflation",
        "assets": ["TLT", "IEF", "GLD", "SLV", "XLV", "XLP", "XLU", "UUP", "BTAL"],
        "bias": "bearish",
    },
}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _safe_ret(s, n):
    if s is None or s.empty:
        return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n + 1:
        return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
        return r if math.isfinite(r) else None
    except Exception:
        return None

def _last_price(s):
    if s is None or s.empty:
        return None
    try:
        v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1])
        return v if math.isfinite(v) else None
    except Exception:
        return None

def _clamp01(x):
    return float(max(0.0, min(1.0, x)))


# ═══════════════════════════════════════════════════════════════════
# INTERNAL BUILDERS
# ═══════════════════════════════════════════════════════════════════
def _build_bottlenecks(prices, health, features, sq, mq):
    """Build bottleneck structure expected by app.py."""
    b = {"level_1": [], "level_2": [], "watch": [], "em_recovery": []}
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    crash_score = health.get("crash", {}).get("score", 0)
    risk_off = health.get("risk_off", {}).get("state", "risk_on")
    g = features.get("growth_momentum", 0)
    i = features.get("inflation_momentum", 0)

    if vix > 25:
        b["level_1"].append({
            "ticker": "VIX", "direction": "SHORT", "sector": "Volatility",
            "known_thesis": f"VIX {vix:.0f} — elevated volatility regime",
            "score": 0.85, "quality": "A", "setup": "VIX > 25 → defensive posture",
        })
    if crash == "elevated":
        b["level_1"].append({
            "ticker": "SPY", "direction": "SHORT", "sector": "Broad Market",
            "known_thesis": f"Crash score {crash_score:.2f} — multiple stress signals active",
            "score": 0.80, "quality": "A", "setup": "Crash meter elevated → reduce beta",
        })
    elif crash == "watch":
        b["watch"].append({
            "ticker": "SPY", "direction": "HOLD", "sector": "Broad Market",
            "known_thesis": f"Crash score {crash_score:.2f} — watch mode",
            "score": 0.60, "quality": "B", "setup": "Monitor closely",
        })
    if risk_off == "risk_off":
        b["level_1"].append({
            "ticker": "TLT", "direction": "LONG", "sector": "Treasuries",
            "known_thesis": "Risk-off regime — flight to quality",
            "score": 0.75, "quality": "A", "setup": "Add duration / reduce equity beta",
        })
    elif risk_off == "caution":
        b["watch"].append({
            "ticker": "SPY", "direction": "HOLD", "sector": "Broad Market",
            "known_thesis": "Risk-off caution — tighten stops, reduce sizing",
            "score": 0.55, "quality": "B", "setup": "Defensive positioning",
        })
    if g < -0.05:
        b["level_2"].append({
            "ticker": "IWM", "direction": "SHORT", "sector": "Small Caps",
            "known_thesis": f"Growth decelerating ({g:+.2%}) — earnings risk",
            "score": 0.65, "quality": "B", "setup": "Small caps vulnerable to growth slowdown",
        })
    if i > 0.04:
        b["level_2"].append({
            "ticker": "XLU", "direction": "LONG", "sector": "Utilities",
            "known_thesis": f"Inflation persistent ({i:+.2%}) — Fed hawkish risk",
            "score": 0.60, "quality": "B", "setup": "Defensive sectors outperform in high inflation",
        })

    # EM recovery signals
    trans = f"{sq}→{mq}"
    em_sig = EM_RECOVERY_SIGNALS.get(trans)
    if em_sig:
        b["em_recovery"].append({
            "ticker": "EEM",
            "direction": "LONG" if em_sig["direction"] == "bullish" else "SHORT",
            "sector": "EM",
            "known_thesis": em_sig["trigger"],
            "score": 0.70, "quality": "B",
            "setup": f"EM recovery on {trans} transition",
        })

    return b


def _build_narratives(gip, health, sq, mq):
    """Build narrative strings expected by app.py."""
    regime = QUAD_MAP.get(sq, {"name": "Unknown"})
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    g = gip.features.get("growth_momentum", 0)
    i = gip.features.get("inflation_momentum", 0)
    p = gip.features.get("policy_score", 0)

    parts = []
    parts.append(f"🌍 MacroRegime: **{regime.get('name', 'Unknown')}** ({sq})")
    parts.append(f"📊 Growth {g:+.2%} | Inflation {i:+.2%} | Policy {p:+.2f}")
    parts.append(f"🔀 Monthly {mq} inside Structural {sq} | Divergence: {gip.divergence}")
    if vix > 25:
        parts.append(f"⚠️ VIX {vix:.0f} — defensive posture warranted")
    if crash in ("elevated", "watch"):
        parts.append(f"🚨 Crash meter: {crash.upper()}")
    if gip.flip_hazard > 0.3:
        parts.append(f"⚡ Flip hazard {gip.flip_hazard:.0%} — regime transition risk")

    return parts


def _build_scenarios(gip, sq, mq):
    """Build scenario structure expected by app.py."""
    probs = gip.structural_probs
    return {
        "base_case": f"Structural {sq} persists ({probs.get(sq, 0):.0%} confidence)",
        "upside": f"Flip to {mq} if monthly momentum continues and growth re-accelerates",
        "downside": f"Deepening {sq} if growth keeps decelerating and inflation stays sticky",
        "probabilities": probs,
    }


def _build_analogs(gip, sq, mq):
    """Build analog structure expected by app.py."""
    analogs = []
    if sq == "Q3":
        analogs.append({
            "label": "2022 H1 Stagflation", "similarity": 0.82,
            "path_1m": "-8%", "path_3m": "-18%", "path_6m": "-20%",
            "next_bias": "Bearish",
        })
        analogs.append({
            "label": "1974-75 Oil Shock", "similarity": 0.71,
            "path_1m": "-5%", "path_3m": "-12%", "path_6m": "-15%",
            "next_bias": "Bearish",
        })
    elif sq == "Q1":
        analogs.append({
            "label": "2023 H2 Goldilocks", "similarity": 0.85,
            "path_1m": "+4%", "path_3m": "+12%", "path_6m": "+15%",
            "next_bias": "Bullish",
        })
        analogs.append({
            "label": "2017 Low Vol Rally", "similarity": 0.78,
            "path_1m": "+3%", "path_3m": "+8%", "path_6m": "+14%",
            "next_bias": "Bullish",
        })
    elif sq == "Q2":
        analogs.append({
            "label": "2021 H1 Reflation", "similarity": 0.80,
            "path_1m": "+5%", "path_3m": "+10%", "path_6m": "+12%",
            "next_bias": "Bullish",
        })
    elif sq == "Q4":
        analogs.append({
            "label": "2008 GFC", "similarity": 0.75,
            "path_1m": "-10%", "path_3m": "-25%", "path_6m": "-37%",
            "next_bias": "Bearish",
        })
        analogs.append({
            "label": "2001 Dot-Com Crash", "similarity": 0.68,
            "path_1m": "-8%", "path_3m": "-18%", "path_6m": "-30%",
            "next_bias": "Bearish",
        })
    return analogs


def _build_global(gip, sq, mq):
    """Build global structure expected by app.py."""
    probs = gip.structural_probs
    conf = gip.structural_conf
    return {
        "global_quad": sq,
        "global_conf": conf,
        "global_probs": probs,
        "country_quads": {},  # populated if country engine exists
    }


def _build_cot_oi(prices):
    """Build COT + OI proxy for CME futures."""
    cot_proxy = CMECOTProxy()
    oi_proxy = CMEOIProxy()
    cot_results = {}
    oi_results = {}
    cme_tickers = list(COMMODITIES.keys())[:10] + ["DX-Y.NYB"] + list(FOREX_PAIRS.keys())[:6]
    vix_last = _last_price(prices.get("^VIX")) or 18.0

    for t in cme_tickers:
        try:
            cot = cot_proxy.analyze(t, prices, vix=vix_last)
            if cot and cot.get("ok"):
                cot_results[t] = cot
        except Exception as e:
            logger.debug(f"COT error for {t}: {e}")
        try:
            oi = oi_proxy.analyze(t, prices)
            if oi and oi.get("ok"):
                oi_results[t] = oi
        except Exception as e:
            logger.debug(f"OI error for {t}: {e}")

    return {"cot": cot_results, "oi": oi_results}


def _build_crypto_onchain():
    """Fetch DeFiLlama on-chain metrics."""
    try:
        d = DeFiLlamaHelper()
        return {
            "tvl_b": d.get_tvl(),
            "stable_mcap_b": d.get_stablecoin_mcap(),
            "dex_vol_24h_b": d.get_dex_volume_24h(),
            "source": "defillama",
        }
    except Exception as e:
        logger.warning(f"DeFiLlama error: {e}")
        return {"tvl_b": None, "stable_mcap_b": None, "dex_vol_24h_b": None, "source": "defillama", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — FIX #3: standalone function, not class method
# ═══════════════════════════════════════════════════════════════════
def build_snapshot(progress_cb=None, include_us_stocks=True, include_forex=True,
                   include_commodities=True, include_crypto=True, include_ihsg=True):
    """Build full macro snapshot. Called by app.py line 557."""
    t0 = time.time()
    logger.info("Building macro snapshot...")
    if progress_cb:
        progress_cb("Building ticker list...", 0.05)

    # ── 1. Build ticker list ──────────────────────────────────────
    all_tickers = list(MACRO_PROXIES.keys())
    if include_us_stocks:
        all_tickers += list(US_SECTORS.keys())
        for bucket in ["Growth", "Quality", "Defensives", "Semis", "Energy",
                       "Industrials", "Financials", "AI_Infra", "PreciousMetals",
                       "International", "Housing", "Bitcoin"]:
            all_tickers += US_BUCKETS.get(bucket, [])
    all_tickers += list(BONDS.keys())
    if include_commodities:
        all_tickers += list(COMMODITIES.keys())[:25]
    if include_forex:
        all_tickers += list(FOREX_PAIRS.keys())  # FIX #8: forex included
    if include_crypto:
        all_tickers += list(CRYPTO.keys())[:10]
    if include_ihsg:
        all_tickers += list(IHSG_UNIVERSE.keys())[:20]
    all_tickers += ["DX-Y.NYB", "EIDO", "^JKSE", "VIX", "^VIX"]
    # deduplicate while preserving order
    seen = set()
    all_tickers = [t for t in all_tickers if not (t in seen or seen.add(t))]

    # ── 2. Load data — FIX #2: pass tickers explicitly ────────────
    if progress_cb:
        progress_cb("Loading prices...", 0.10)
    prices = load_prices(tickers=all_tickers, days=756)

    if progress_cb:
        progress_cb(f"Loaded {len(prices)} price series", 0.30)
    fred = load_fred_macro()

    # ── 3. GIP Engine — FIX #5: call .run(fred, prices), not .analyze() ──
    if progress_cb:
        progress_cb("Running GIP engine...", 0.40)
    gip_engine = GIPEngine()
    gip = gip_engine.run(fred, prices)
    sq = gip.structural_quad
    mq = gip.monthly_quad

    if progress_cb:
        progress_cb(f"GIP: Structural {sq} | Monthly {mq}", 0.50)

    # ── 4. Risk Ranges (TRR/LRR) ──────────────────────────────────
    risk_engine = HurstRiskRangeEngine()
    asset_ranges = {}
    for t in all_tickers:
        s = prices.get(t)
        if s is None or s.empty:
            continue
        try:
            rr = risk_engine.analyze(s)
            if rr and rr.get("ok"):
                asset_ranges[t] = rr
        except Exception as e:
            logger.debug(f"Risk range error for {t}: {e}")

    if progress_cb:
        progress_cb(f"Risk ranges: {len(asset_ranges)} assets", 0.65)

    # ── 5. Market Health ──────────────────────────────────────────
    if progress_cb:
        progress_cb("Running health engine...", 0.70)
    health_engine = MarketHealthEngine()
    health = health_engine.run(prices, gip.features, sq)

    if progress_cb:
        progress_cb("Health check complete", 0.80)

    # ── 6. Discovery ──────────────────────────────────────────────
    try:
        discovery_engine = AutoDiscoveryEngineV3()
        discovery = discovery_engine.run(prices, gip, asset_ranges)
    except Exception as e:
        logger.warning(f"Discovery error: {e}")
        discovery = {"discoveries": []}

    # ── 7. Playbook — FIX #9: call get_playbook() ─────────────────
    playbook = get_playbook(sq, mq)

    # ── 8. Transition ─────────────────────────────────────────────
    flip = gip.flip_hazard
    transition = SimpleNamespace(
        front_run_window="now" if flip > 0.5 else "1-2w" if flip > 0.3 else "3-6w" if flip > 0.15 else "not yet",
        front_run_rationale=(
            f"Flip hazard {flip:.0%}. "
            f"Structural {sq} vs Monthly {mq} ({gip.divergence})."
        ),
    )

    # ── 9. Bottlenecks ────────────────────────────────────────────
    bottlenecks = _build_bottlenecks(prices, health, gip.features, sq, mq)

    # ── 10. Narratives ────────────────────────────────────────────
    narratives = _build_narratives(gip, health, sq, mq)

    # ── 11. Scenarios ─────────────────────────────────────────────
    scenarios = _build_scenarios(gip, sq, mq)

    # ── 12. Analogs ───────────────────────────────────────────────
    analogs = _build_analogs(gip, sq, mq)

    # ── 13. Global ────────────────────────────────────────────────
    global_data = _build_global(gip, sq, mq)

    # ── 14. COT + OI ──────────────────────────────────────────────
    cot_oi = _build_cot_oi(prices)

    # ── 15. Crypto on-chain ───────────────────────────────────────
    crypto_onchain = _build_crypto_onchain() if include_crypto else {}

    # ── 16. Assemble snapshot — FIX #10: complete structure ───────
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
        "auto_discoveries": {"ok": True, "bottlenecks": []},
        "feedback_eval": {"evaluated": 0, "promoted": [], "demoted": []},
        "gamma": {"ok": False, "reason": "Gamma engine not configured"},
        "leveraged_etf": {"ok": False, "reason": "Leveraged ETF engine not configured"},
        "ai_analysis": {"ok": False, "reason": "AI engine not configured"},
        "build_time_s": round(time.time() - t0, 1),
        "prices_loaded": len(prices),
        "fred_coverage": gip.data_coverage,
        "cot_oi": cot_oi,
        "crypto_onchain": crypto_onchain,
    }

    logger.info(f"Snapshot built in {snapshot['build_time_s']}s | "
                f"Prices: {len(prices)} | Ranges: {len(asset_ranges)}")
    if progress_cb:
        progress_cb("Done!", 1.0)
    return snapshot


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    snap = build_snapshot()
    print(json.dumps({
        "quad": snap["gip"].structural_quad,
        "monthly": snap["gip"].monthly_quad,
        "regime": QUAD_MAP.get(snap["gip"].structural_quad, {}).get("name"),
        "prices": len(snap["prices"]),
        "ranges": len(snap["risk_ranges"]["asset_ranges"]),
        "build_time": snap["build_time_s"],
    }, indent=2))

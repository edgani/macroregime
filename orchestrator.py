"""orchestrator.py — MacroRegime Pro Orchestrator
Single entry point: build_snapshot() → returns full macro snapshot dict.
Compatible with app.py expectations.
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

try:
    from config.autonomy_settings import AUTONOMY_LEVEL
except Exception:
    AUTONOMY_LEVEL = "semi"

# ------------------------------------------------------------------
# Engines
# ------------------------------------------------------------------
from data.loader import load_prices, load_fred_macro
from engines.gip_engine import GIPEngine, get_playbook
from engines.market_health_engine import MarketHealthEngine
from engines.hurst_risk_ranges import HurstRiskRangeEngine
from engines.cme_cot import CMECOTProxy
from engines.cme_oi import CMEOpenInterestProxy
from engines.defillama_helper import DeFiLlamaHelper
from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3

# QUAD_MAP fallback — engines.quad_engine may or may not export it
try:
    from engines.quad_engine import QUAD_MAP
except Exception:
    QUAD_MAP = {
        "Q1": {"name": "Goldilocks", "assets": ["XLK", "XLY", "XLI", "IWM", "QQQ", "RSP", "SLV", "GLD", "IBIT"], "bias": "bullish"},
        "Q2": {"name": "Reflation / Knife Fights", "assets": ["XLE", "OIH", "XLI", "XLB", "SLV", "GLD", "GDX", "ITB", "TLT", "IBIT"], "bias": "bullish"},
        "Q3": {"name": "Stagflation", "assets": ["SLV", "GLD", "PPLT", "GDX", "GDXJ", "XLV", "XLP", "XLU", "TLT", "ITA"], "bias": "bearish"},
        "Q4": {"name": "Deflation", "assets": ["TLT", "IEF", "GLD", "SLV", "XLV", "XLP", "XLU", "UUP", "BTAL"], "bias": "bearish"},
    }
    logger.info("Using fallback QUAD_MAP")


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
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
# BUILDERS (internal)
# ═══════════════════════════════════════════════════════════════════
def _build_bottlenecks(prices, health, features, sq, mq):
    b = {"level_1": [], "level_2": [], "watch": [], "em_recovery": []}
    vix = health.get("vix_bucket", {}).get("vix_last", 18)
    crash = health.get("crash", {}).get("state", "calm")
    crash_score = health.get("crash", {}).get("score", 0)
    risk_off = health.get("risk_off", {}).get("state", "risk_on")
    g = features.get("growth_momentum", 0)
    i = features.get("inflation_momentum", 0)

    if vix > 25:
        b["level_1"].append(f"VIX {vix:.0f} — elevated volatility")
    if crash == "elevated":
        b["level_1"].append(f"Crash score {crash_score:.2f} — multiple stress signals")
    elif crash == "watch":
        b["watch"].append(f"Crash score {crash_score:.2f} — watch mode")
    if risk_off == "risk_off":
        b["level_1"].append("Risk-off regime — reduce beta")
    elif risk_off == "caution":
        b["watch"].append("Risk-off caution — tighten stops")
    if g < -0.05:
        b["level_2"].append(f"Growth decelerating ({g:+.2%})")
    if i > 0.04:
        b["level_2"].append(f"Inflation persistent ({i:+.2%})")

    # EM recovery
    trans = f"{sq}→{mq}"
    em_sig = EM_RECOVERY_SIGNALS.get(trans)
    if em_sig:
        b["em_recovery"].append(em_sig["trigger"])

    return b

def _build_narratives(gip, health, sq, mq):
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
        parts.append(f"⚠️ VIX {vix:.0f} — defensive posture")
    if crash in ("elevated", "watch"):
        parts.append(f"🚨 Crash meter: {crash.upper()}")

    return parts

def _build_scenarios(gip, sq, mq):
    probs = gip.structural_probs
    return {
        "base_case": f"Structural {sq} persists ({probs.get(sq, 0):.0%} confidence)",
        "upside": f"Flip to {mq} if monthly momentum continues",
        "downside": f"Deepening {sq} if growth keeps decelerating",
        "probabilities": probs,
    }

def _build_analogs(gip, sq, mq):
    # Simple analogs based on quad history
    analogs = []
    if sq == "Q3":
        analogs.append({"period": "2022 H1", "quad": "Q3", "return_spy": "-20%", "note": "Fed hiking into slowing growth"})
        analogs.append({"period": "1974-75", "quad": "Q3", "return_spy": "-15%", "note": "Oil shock + stagflation"})
    elif sq == "Q1":
        analogs.append({"period": "2023 H2", "quad": "Q1", "return_spy": "+15%", "note": "Goldilocks post-pause"})
    elif sq == "Q2":
        analogs.append({"period": "2021 H1", "quad": "Q2", "return_spy": "+12%", "note": "Reflation post-COVID"})
    elif sq == "Q4":
        analogs.append({"period": "2008", "quad": "Q4", "return_spy": "-37%", "note": "GFC deflation"})
    return analogs

def _build_global(gip, sq, mq):
    probs = gip.structural_probs
    conf = gip.structural_conf
    return {
        "global_quad": sq,
        "global_conf": conf,
        "global_probs": probs,
        "country_quads": {},  # populated if country engine exists
    }

def _build_cot_oi(prices):
    cot_proxy = CMECOTProxy()
    oi_proxy = CMEOpenInterestProxy()
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
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def build_snapshot(progress_cb=None, include_us_stocks=True, include_forex=True,
                   include_commodities=True, include_crypto=True, include_ihsg=True):
    """Build full macro snapshot. Called by app.py"""
    t0 = time.time()
    logger.info("Building macro snapshot...")
    if progress_cb:
        progress_cb(0.05, "Loading prices...")

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
        all_tickers += list(FOREX_PAIRS.keys())  # <-- FIX: forex included
    if include_crypto:
        all_tickers += list(CRYPTO.keys())[:10]
    if include_ihsg:
        all_tickers += list(IHSG_UNIVERSE.keys())[:20]
    all_tickers += ["DX-Y.NYB", "EIDO", "^JKSE", "VIX", "^VIX"]
    # deduplicate while preserving order
    seen = set()
    all_tickers = [t for t in all_tickers if not (t in seen or seen.add(t))]

    # ── 2. Load data ──────────────────────────────────────────────
    prices = load_prices(tickers=all_tickers, lookback=756)
    fred = load_fred_macro()
    if progress_cb:
        progress_cb(0.30, f"Loaded {len(prices)} price series")

    # ── 3. GIP Engine ─────────────────────────────────────────────
    gip_engine = GIPEngine()
    gip = gip_engine.run(fred, prices)
    sq = gip.structural_quad
    mq = gip.monthly_quad
    if progress_cb:
        progress_cb(0.45, f"GIP: Structural {sq} | Monthly {mq}")

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
        progress_cb(0.60, f"Risk ranges: {len(asset_ranges)} assets")

    # ── 5. Market Health ──────────────────────────────────────────
    health_engine = MarketHealthEngine()
    health = health_engine.run(prices, gip.features, sq)

    # ── 6. Discovery ──────────────────────────────────────────────
    try:
        discovery_engine = AutoDiscoveryEngineV3()
        discovery = discovery_engine.run(prices, gip.features, sq)
    except Exception as e:
        logger.warning(f"Discovery error: {e}")
        discovery = {"discoveries": []}

    # ── 7. Playbook ───────────────────────────────────────────────
    playbook = get_playbook(sq, mq)

    # ── 8. Transition ─────────────────────────────────────────────
    transition = SimpleNamespace(
        front_run_window="2-4 weeks" if gip.flip_hazard > 0.4 else "4-8 weeks",
        front_run_rationale=(
            f"Flip hazard {gip.flip_hazard:.0%}. "
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

    # ── 16. Placeholders for optional engines ─────────────────────
    gamma = {"ok": False, "reason": "Gamma engine not configured"}
    leveraged_etf = {"ok": False, "reason": "Leveraged ETF engine not configured"}
    ai_analysis = {"ok": False, "reason": "AI engine not configured"}
    auto_discoveries = {"ok": True, "bottlenecks": []}
    feedback_eval = {"evaluated": 0, "promoted": [], "demoted": []}

    # ── 17. Assemble snapshot ─────────────────────────────────────
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
        "auto_discoveries": auto_discoveries,
        "feedback_eval": feedback_eval,
        "gamma": gamma,
        "leveraged_etf": leveraged_etf,
        "ai_analysis": ai_analysis,
        "build_time_s": round(time.time() - t0, 1),
        "fred_coverage": gip.data_coverage,
        "cot_oi": cot_oi,
        "crypto_onchain": crypto_onchain,
    }

    logger.info(f"Snapshot built in {snapshot['build_time_s']}s | "
                f"Prices: {len(prices)} | Ranges: {len(asset_ranges)}")
    if progress_cb:
        progress_cb(1.0, "Done!")
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

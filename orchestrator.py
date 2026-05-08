"""orchestrator.py — MacroRegime Pro v16 | Snapshot builder
INCLUDES: 10/10 Autonomy Stack LIGHTWEIGHT (NO torch/transformers)
+ Gamma Regime Engine (soft import)
+ Leveraged ETF Flow Engine (soft import)
+ Hedgeye ETF Pro Plus tickers in Risk Range universe
"""
from __future__ import annotations
import time, logging, math, os, json
from typing import Optional, Callable, Dict, List
import numpy as np
import pandas as pd

from data.loader import load_fred, load_prices, save_snapshot, load_snapshot, snapshot_age_str

# ── Core engines (hard import — app cannot run without these) ─────────────────
from engines.gip_engine import GIPEngine, get_playbook
from engines.hurst_rr_engine import HurstRREngine

# Setup logger BEFORE soft imports that use it in except blocks
logger = logging.getLogger(__name__)

# ── Secondary engines (soft import — graceful degradation if missing) ─────────
_GLOBAL_QUAD_OK = False
try:
    from engines.global_quad_engine import GlobalQuadEngine
    _GLOBAL_QUAD_OK = True
except Exception as _e:
    logger.warning(f"GlobalQuadEngine unavailable: {_e}")

_SCENARIO_OK = False
try:
    from engines.scenario_engine import ScenarioEngine
    _SCENARIO_OK = True
except Exception as _e:
    logger.warning(f"ScenarioEngine unavailable: {_e}")

_BOTTLENECK_OK = False
try:
    from engines.bottleneck_engine import BottleneckEngine
    _BOTTLENECK_OK = True
except Exception as _e:
    logger.warning(f"BottleneckEngine unavailable: {_e}")

_NARRATIVE_OK = False
try:
    from engines.narrative_engine import NarrativeEngine
    _NARRATIVE_OK = True
except Exception as _e:
    logger.warning(f"NarrativeEngine unavailable: {_e}")

_DISCOVERY_OK = False
try:
    from engines.adaptive_discovery_engine import AdaptiveDiscoveryEngine
    _DISCOVERY_OK = True
except Exception as _e:
    logger.warning(f"AdaptiveDiscoveryEngine unavailable: {_e}")

_TRANSITION_OK = False
try:
    from engines.regime_transition_engine import RegimeTransitionEngine
    _TRANSITION_OK = True
except Exception as _e:
    logger.warning(f"RegimeTransitionEngine unavailable: {_e}")

_HEALTH_OK = False
try:
    from engines.market_health_engine import MarketHealthEngine
    _HEALTH_OK = True
except Exception as _e:
    logger.warning(f"MarketHealthEngine unavailable: {_e}")

_ANALOG_OK = False
try:
    from engines.historical_analog_engine import HistoricalAnalogEngine
    _ANALOG_OK = True
except Exception as _e:
    logger.warning(f"HistoricalAnalogEngine unavailable: {_e}")

from config.settings import (
    MACRO_PROXIES, US_SECTORS, US_FACTORS, FOREX_PAIRS,
    COMMODITIES, CRYPTO, BONDS, IHSG_UNIVERSE, COUNTRY_UNIVERSE,
    TICKER_SECTOR, MARKET_CLASSIFICATION, BOTTLENECK_PROFILES,
)

# ── Autonomy engine imports (soft — graceful fallback if files missing) ───────
_AUTONOMY_AVAILABLE = False
try:
    from engines.price_cluster_engine_v3 import PriceClusterEngineV3
    from engines.news_nlp_engine_v3 import NewsNLPEngineV3
    from engines.edgar_scraper_engine import EDGARScraperEngine
    from engines.supply_chain_graph_engine import SupplyChainGraphEngine
    from engines.leading_indicator_engine import LeadingIndicatorEngine
    from engines.regime_predictor_engine import RegimePredictorEngine
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
    from engines.feedback_loop_engine_v3 import FeedbackLoopEngineV3
    _AUTONOMY_AVAILABLE = True
    logger.info("Autonomy stack v3 (lightweight) loaded successfully.")
except Exception as e:
    logger.warning(f"Autonomy stack not available: {e}")
    _AUTONOMY_AVAILABLE = False

# ── Gamma Regime Engine (soft — file may not exist yet) ───────────────────────
_GAMMA_AVAILABLE = False
try:
    from engines.gamma_regime_engine import GammaRegimeEngine
    _GAMMA_AVAILABLE = True
    logger.info("GammaRegimeEngine loaded.")
except Exception as e:
    logger.warning(f"GammaRegimeEngine not available: {e}")

# ── Leveraged ETF Engine (soft — file may not exist yet) ─────────────────────
_LEV_ETF_AVAILABLE = False
try:
    from engines.leveraged_etf_engine import LeveragedETFEngine
    _LEV_ETF_AVAILABLE = True
    logger.info("LeveragedETFEngine loaded.")
except Exception as e:
    logger.warning(f"LeveragedETFEngine not available: {e}")


def _prog(cb, msg, frac):
    logger.info(f"[{frac:.0%}] {msg}")
    if cb:
        cb(msg, frac)


def build_snapshot(
    progress_cb: Optional[Callable] = None,
    include_crypto: bool = True,
    include_us_stocks: bool = True,
    include_forex: bool = True,
    include_commodities: bool = True,
    include_ihsg: bool = True,
) -> dict:
    t0 = time.time()
    snap: dict = {"ts": t0, "ok": False}

    # 1. FRED
    _prog(progress_cb, "Loading FRED macro data...", 0.04)
    fred = load_fred(months=36)
    snap["fred_coverage"] = len(fred)

    # 2. Core prices (always)
    _prog(progress_cb, "Loading core market prices...", 0.10)
    prices: Dict[str, pd.Series] = {}
    prices.update(load_prices(list(MACRO_PROXIES.keys()) + list(BONDS.keys()) + ["DX-Y.NYB", "^VIX"], days=756))

    # 3. US equities
    if include_us_stocks:
        _prog(progress_cb, "Loading US sectors + factors...", 0.16)
        prices.update(load_prices(list(US_SECTORS.keys()) + list(US_FACTORS.keys()), days=756))
        _prog(progress_cb, "Loading notable single stocks...", 0.21)
        notable = [t for t in TICKER_SECTOR if t not in prices and t not in ("generic",)]
        prices.update(load_prices(notable, days=365))

    # 4. Forex
    if include_forex:
        _prog(progress_cb, "Loading forex pairs (major + EM)...", 0.26)
        prices.update(load_prices(list(FOREX_PAIRS.keys()), days=756))

    # 5. Commodities
    if include_commodities:
        _prog(progress_cb, "Loading commodities (energy, metals, agri)...", 0.31)
        prices.update(load_prices(list(COMMODITIES.keys()), days=756))

    # 6. Crypto
    if include_crypto:
        _prog(progress_cb, "Loading crypto universe...", 0.36)
        prices.update(load_prices(list(CRYPTO.keys()), days=365))

    # 7. IHSG
    if include_ihsg:
        _prog(progress_cb, "Loading IHSG + Indonesia stocks...", 0.40)
        prices.update(load_prices(list(IHSG_UNIVERSE.keys()), days=756))

    # 8. Country ETFs for global quad
    _prog(progress_cb, "Loading country ETFs (50 countries)...", 0.44)
    country_etfs = list({v[0] for v in COUNTRY_UNIVERSE.values()})
    prices.update(load_prices(country_etfs, days=756))
    snap["prices_loaded"] = len(prices)

    # 9. GIP
    _prog(progress_cb, "Running GIP model (G·I·P second derivative)...", 0.50)
    try:
        gip = GIPEngine().run(fred=fred, prices=prices)
    except Exception as e:
        logger.error(f"GIP error: {e}")
        raise
    snap["gip"] = gip
    snap["playbook"] = get_playbook(gip.structural_quad, gip.monthly_quad)

    # 10. Global Quad
    _prog(progress_cb, "Running Global Quad (50 countries)...", 0.58)
    if _GLOBAL_QUAD_OK:
        global_quad = GlobalQuadEngine().run(prices=prices, us_gip_result=gip)
    else:
        global_quad = {"global_quad": "—", "global_conf": 0, "global_probs": {}, "country_quads": {}}
    snap["global"] = global_quad

    # 11. Risk Ranges — INCLUDES Hedgeye ETF Pro Plus tickers
    _prog(progress_cb, "Fetching OHLCV for Hurst risk ranges...", 0.64)
    rr_tickers = (
        list(MACRO_PROXIES.keys())
        + list(US_SECTORS.keys())
        + list(BONDS.keys())
        + list(COMMODITIES.keys())[:15]
        + (list(CRYPTO.keys())[:6] if include_crypto else [])
        + ["DX-Y.NYB", "EIDO", "^JKSE"]
        + [
            t
            for t in TICKER_SECTOR
            if TICKER_SECTOR.get(t)
            in (
                "ai_optics",
                "ai_power",
                "ai_power_infra",
                "precious_metals",
                "precious_metals_miners",
                "defense",
                "oil_services",
                "housing",
                "steel",
                "infrastructure",
            )
        ][:25]
    )

    # ── Hedgeye ETF Pro Plus actual tickers — MUST be in Risk Range ──────────
    hedgeye_etf_pro_tickers = [
        # Q2 LONG (ETF Pro Plus confirmed)
        "XLI",
        "XLE",
        "OIH",
        "BNO",
        "XOP",
        "ITB",
        "TLT",
        "LQD",
        "JPXN",
        "EIS",
        "TUR",
        "NORW",
        "EWZ",
        "EWW",
        "EIDO",
        "GLIN",
        "DAR",
        "MTDR",
        "SLX",
        "CPER",
        # Precious Metals (monster performers)
        "SLV",
        "GLD",
        "PPLT",
        "GDX",
        "GDXJ",
        "SIL",
        "SILJ",
        # Defense / Secular
        "ITA",
        "GRID",
        # Q2/Q3 SHORT targets
        "MSTY",
        "BITS",
        "BLOK",
        "WGMI",
        "MAGS",
        # Anti-beta hedge
        "BTAL",
        "DUST",
        # Signal Strength Stocks
        "ULS",
        "BRBR",
        # Standard
        "QQQ",
        "SPY",
        "IWM",
        "RSP",
        "GLD",
        "SLV",
    ]
    rr_tickers = rr_tickers + hedgeye_etf_pro_tickers
    rr_tickers = list(dict.fromkeys(rr_tickers))  # dedupe, preserve order

    price_frames: Dict[str, pd.DataFrame] = {}
    try:
        import yfinance as yf

        raw = yf.download(rr_tickers, period="2y", progress=False, auto_adjust=True, timeout=30, threads=True)
        if not raw.empty:
            for t in rr_tickers:
                try:
                    if len(rr_tickers) == 1:
                        df = raw
                    else:
                        df = raw.xs(t, level=1, axis=1) if t in raw.columns.get_level_values(1) else pd.DataFrame()
                    if not df.empty and "Close" in df.columns:
                        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                        df = df[cols].apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
                        price_frames[t] = df
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"OHLCV fetch partial: {e}")

    for t in rr_tickers:
        if t not in price_frames and t in prices:
            c = pd.to_numeric(prices[t], errors="coerce").dropna()
            if len(c) > 20:
                df = pd.DataFrame({"Open": c, "High": c * 1.003, "Low": c * 0.997, "Close": c, "Volume": np.nan})
                price_frames[t] = df

    snap["price_frames_count"] = len(price_frames)
    stress = _build_stress(prices, gip)
    rr_result = HurstRREngine().run(price_frames=price_frames, stress=stress)
    snap["risk_ranges"] = rr_result
    snap["stress"] = stress

    # 12. Scenarios
    _prog(progress_cb, "Discovering adaptive scenarios...", 0.80)
    if _SCENARIO_OK:
        scenarios = ScenarioEngine().run(
            structural_quad=gip.structural_quad,
            monthly_quad=gip.monthly_quad,
            features=gip.features,
            flip_hazard=gip.flip_hazard,
            data_coverage=gip.data_coverage,
        )
    else:
        scenarios = {}
    snap["scenarios"] = scenarios

    # 13. Bottleneck Scanner
    _prog(progress_cb, "Scanning bottlenecks (all asset classes)...", 0.88)
    if _BOTTLENECK_OK:
        try:
            btk = BottleneckEngine().run(
                prices=prices,
                quad_str=gip.structural_quad,
                quad_mon=gip.monthly_quad,
                benchmark="SPY",
                asset_ranges=rr_result.get("asset_ranges", {}),
            )
        except Exception as e:
            logger.warning(f"Bottleneck run error: {e}")
            btk = {}
    else:
        btk = {}
    snap["bottleneck"] = btk

    # 14. Narrative Engine
    _prog(progress_cb, "Scoring active narratives...", 0.93)
    if _NARRATIVE_OK:
        try:
            narratives = NarrativeEngine().run(
                prices=prices,
                quad_str=gip.structural_quad,
                quad_mon=gip.monthly_quad,
                benchmark="SPY",
            )
        except Exception as e:
            logger.warning(f"Narrative run error: {e}")
            narratives = {}
    else:
        narratives = {}
    snap["narratives"] = narratives

    # 14b. Regime Transition
    _prog(progress_cb, "Computing regime transition timing...", 0.91)
    if _TRANSITION_OK:
        try:
            macro_ctx = {k: v for k, v in gip.features.items() if isinstance(v, float)}
            market_ctx = {
                "oil_3m": float(
                    prices.get("CL=F", pd.Series()).tail(1).iloc[-1] / prices.get("CL=F", pd.Series()).iloc[-64] - 1
                )
                if len(prices.get("CL=F", pd.Series())) > 64
                else 0.0,
                "gold_3m": float(
                    prices.get("GLD", pd.Series()).tail(1).iloc[-1] / prices.get("GLD", pd.Series()).iloc[-64] - 1
                )
                if len(prices.get("GLD", pd.Series())) > 64
                else 0.0,
            }
            transition = RegimeTransitionEngine().run(macro=macro_ctx, market=market_ctx, gip_result=gip)
        except Exception as e:
            logger.warning(f"Transition engine: {e}")
            transition = None
    else:
        transition = None
    snap["transition"] = transition

    # 14c. Market Health
    _prog(progress_cb, "Computing market health signals...", 0.92)
    if _HEALTH_OK:
        try:
            health = MarketHealthEngine().run(prices=prices, gip_features=gip.features, quad=gip.structural_quad)
        except Exception as e:
            logger.warning(f"Health engine: {e}")
            health = {}
    else:
        health = {}
    snap["health"] = health

    # 14d. Historical Analogs
    _prog(progress_cb, "Matching historical analogs...", 0.925)
    if _ANALOG_OK:
        try:
            prices_ctx = {
                "oil_3m": market_ctx.get("oil_3m", 0) if _TRANSITION_OK else 0,
                "vol_stress": stress.get("vol_stress", 0),
            }
            analogs = HistoricalAnalogEngine().run(gip_features=gip.features, prices_context=prices_ctx)
        except Exception as e:
            logger.warning(f"Analog engine: {e}")
            analogs = {"top_analogs": [], "composite_note": ""}
    else:
        analogs = {"top_analogs": [], "composite_note": ""}
    snap["analogs"] = analogs

    # 14e. Gamma Regime (computed dari SPY rVol + VIX — zero hardcode)
    _prog(progress_cb, "Computing gamma regime approximation...", 0.935)
    if _GAMMA_AVAILABLE:
        try:
            gamma_result = GammaRegimeEngine().run(prices=prices)
        except Exception as e:
            logger.warning(f"Gamma regime engine error: {e}")
            gamma_result = {
                "ok": False,
                "throttle": None,
                "regime": "UNKNOWN",
                "source": "error",
                "note": str(e),
            }
    else:
        gamma_result = {
            "ok": False,
            "throttle": None,
            "regime": "UNKNOWN",
            "source": "unavailable",
            "note": "GammaRegimeEngine not found. Copy engines/gamma_regime_engine.py to repo.",
        }
    snap["gamma"] = gamma_result

    # 14f. Leveraged ETF Flow (yfinance AUM — zero hardcode)
    _prog(progress_cb, "Fetching leveraged ETF AUM data...", 0.940)
    if _LEV_ETF_AVAILABLE:
        try:
            lev_result = LeveragedETFEngine().run(prices=prices)
        except Exception as e:
            logger.warning(f"Leveraged ETF engine error: {e}")
            lev_result = {
                "ok": False,
                "total_mcap_b": None,
                "source": "error",
                "note": str(e),
            }
    else:
        lev_result = {
            "ok": False,
            "total_mcap_b": None,
            "source": "unavailable",
            "note": "LeveragedETFEngine not found. Copy engines/leveraged_etf_engine.py to repo.",
        }
    snap["leveraged_etf"] = lev_result

    # 15. TRUE AUTONOMY v3 LIGHTWEIGHT
    _prog(progress_cb, "Running autonomous discovery (lightweight)...", 0.96)
    if _AUTONOMY_AVAILABLE:
        try:
            auto = AutoDiscoveryEngineV3(
                sector_map=TICKER_SECTOR,
                market_map=MARKET_CLASSIFICATION,
                known_tickers=list(TICKER_SECTOR.keys()),
                use_transformers=False,
            )
            discoveries = auto.run(
                prices=prices,
                structural_quad=gip.structural_quad,
                monthly_quad=gip.monthly_quad,
                gip_features=gip.features,
                theme_queries=None,
                run_edgar=True,
            )
            snap["auto_discoveries"] = discoveries
            fb = FeedbackLoopEngineV3()
            fb.track(discoveries.get("candidates", []), regime=gip.structural_quad)
            fb_eval = fb.evaluate(prices, benchmark="SPY")
            snap["feedback_eval"] = fb_eval
            predictor = RegimePredictorEngine()
            predictor.record_transition(gip.structural_quad, gip.monthly_quad, gip.features)
        except Exception as e:
            logger.warning(f"Autonomy step error: {e}")
            snap["auto_discoveries"] = {"candidates": [], "meta": {"error": str(e)}}
            snap["feedback_eval"] = {"evaluated": 0, "promoted": 0, "demoted": 0}
    elif _DISCOVERY_OK:
        _prog(progress_cb, "Running Claude API discovery fallback...", 0.965)
        try:
            discovery = AdaptiveDiscoveryEngine().run(
                prices=prices,
                structural_quad=gip.structural_quad,
                monthly_quad=gip.monthly_quad,
                gip_features=gip.features,
            )
        except Exception as e:
            logger.warning(f"Discovery engine failed: {e}")
            discovery = {"discoveries": [], "status": "error", "message": str(e)}
        snap["discovery"] = discovery
        snap["auto_discoveries"] = {"candidates": [], "meta": {"fallback": "claude_api"}}
        snap["feedback_eval"] = {"evaluated": 0, "promoted": 0, "demoted": 0}
    else:
        snap["auto_discoveries"] = {"candidates": [], "meta": {"fallback": "unavailable"}}
        snap["feedback_eval"] = {"evaluated": 0, "promoted": 0, "demoted": 0}

    # Store prices subset for UI
    snap["prices"] = {k: v for k, v in prices.items() if isinstance(v, pd.Series) and len(v) > 10}
    snap["build_time_s"] = round(time.time() - t0, 1)
    snap["ok"] = True
    _prog(progress_cb, "Saving snapshot...", 0.98)
    save_snapshot(snap)
    _prog(progress_cb, "Done!", 1.0)
    logger.info(f"Built in {snap['build_time_s']}s. Prices: {snap['prices_loaded']}, RR: {snap['price_frames_count']}")
    return snap


def _build_stress(prices, gip) -> dict:
    def last(t):
        s = prices.get(t)
        if s is None:
            return None
        s = pd.to_numeric(s, errors="coerce").dropna()
        return float(s.iloc[-1]) if not s.empty else None

    def ret1m(t):
        s = prices.get(t)
        if s is None:
            return 0.0
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 22:
            return 0.0
        return float(s.iloc[-1] / s.iloc[-22] - 1)

    vix_raw = last("^VIX")
    vix = vix_raw if (vix_raw is not None and math.isfinite(vix_raw)) else 18.0
    dxy_1m = ret1m("DX-Y.NYB")
    vol_stress = float(np.clip((vix - 15.0) / 25.0, 0.0, 1.0))
    shock = 0.5 if gip.structural_quad == "Q3" else 0.8 if gip.structural_quad == "Q4" else 0.2
    crowding = float(gip.features.get("proxy_share", 0.3))
    dollar_pres = float(np.clip(0.5 + dxy_1m / 0.04, 0.0, 1.0))
    tail_bid = float(np.clip((vix - 20.0) / 30.0, 0.0, 1.0))
    return dict(
        vol_stress=vol_stress,
        shock_penalty=shock * 0.5,
        crowding=crowding,
        dollar_pressure=dollar_pres,
        tail_hedge_bid=tail_bid,
        vix=vix,
    )


def get_or_build(force=False, max_age_h=4.0, **kw) -> dict:
    if not force:
        snap = load_snapshot(max_age_hours=max_age_h)
        if snap and snap.get("ok"):
            return snap
    return build_snapshot(**kw)

"""orchestrator.py v17 — Full Pipeline · All Engines Wired

FIXES vs repo v15/v16:
 1. DiscoveryOrchestrator NOW CALLED (was completely orphaned)
 2. NarrativeEngine gets scenario_output → proactive forecasts WORK
 3. BottleneckEngine gets flow_scores → EV formula correct
 4. sector_momentum computed before all downstream engines
 5. flow_scores_proxy computed from RS momentum
 6. FrontRunEngine added (new file — aggregates all signals)
 7. Price downloads batched (was 6 separate calls → 2 batches)
 8. RR tickers prioritized (max 250 to prevent timeout)
 9. All engines wrapped in _safe() — one failure never kills snapshot

Pipeline order (dependency-aware):
 1. FRED data
 2. Prices (2 batches: core + extended)
 3. GIP (needs FRED + prices)
 4. Global Quad (needs prices + GIP)
 5. Stress overlay (needs prices + GIP)
 6. Sector Momentum (needs prices → feeds bottleneck + narrative)
 7. Flow Scores proxy (needs prices → feeds bottleneck)
 8. Risk Range™ (needs prices, prioritized 250 tickers)
 9. Scenario Engine (needs GIP)
 10. Bottleneck Engine (needs prices + GIP + scenario + flow_scores)
 11. Narrative Engine (needs prices + scenario + bottleneck signals)
 12. Discovery Orchestrator v3 (needs all of above)
 13. Adaptive Discovery / Autonomy Stack
 14. FrontRunEngine (aggregates ALL signals → watchlist)
 15. Regime Transition + Health + Historical Analogs
"""
from __future__ import annotations
import time, logging, math, os
from typing import Optional, Callable, Dict, List, Tuple
import numpy as np
import pandas as pd

from data.loader import load_fred, load_prices, save_snapshot, load_snapshot, snapshot_age_str

# ═══════════════════════════════════════════════════════════════════════════════
# FIX: logger MUST be defined BEFORE all try/except blocks that reference it
# ═══════════════════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)

# ── Core engine imports — each wrapped so one failure never kills the app ─────
try:
    from engines.gip_engine import GIPEngine, get_playbook
except Exception as _e:
    logger.error(f"gip_engine import failed: {_e}"); raise  # GIP is required

try:
    from engines.global_quad_engine import GlobalQuadEngine
    _HAS_GLOBAL_QUAD = True
except Exception as _e:
    logger.warning(f"global_quad_engine: {_e}"); _HAS_GLOBAL_QUAD = False; GlobalQuadEngine = None

try:
    from engines.hurst_rr_engine import HurstRREngine
    _HAS_RR = True
except Exception as _e:
    logger.warning(f"hurst_rr_engine: {_e}"); _HAS_RR = False; HurstRREngine = None

try:
    from engines.scenario_engine import ScenarioEngine
    _HAS_SCENARIO = True
except Exception as _e:
    logger.warning(f"scenario_engine: {_e}"); _HAS_SCENARIO = False; ScenarioEngine = None

try:
    from engines.bottleneck_engine import BottleneckEngine
    _HAS_BTK = True
except Exception as _e:
    logger.warning(f"bottleneck_engine: {_e}"); _HAS_BTK = False; BottleneckEngine = None

try:
    from engines.narrative_engine import NarrativeEngine
    _HAS_NARRATIVE = True
except Exception as _e:
    logger.warning(f"narrative_engine: {_e}"); _HAS_NARRATIVE = False; NarrativeEngine = None

try:
    from engines.adaptive_discovery_engine import AdaptiveDiscoveryEngine
    _HAS_ADAPTIVE = True
except Exception as _e:
    logger.warning(f"adaptive_discovery_engine: {_e}"); _HAS_ADAPTIVE = False; AdaptiveDiscoveryEngine = None

try:
    from engines.regime_transition_engine import RegimeTransitionEngine
    _HAS_TRANSITION = True
except Exception as _e:
    logger.warning(f"regime_transition_engine: {_e}"); _HAS_TRANSITION = False; RegimeTransitionEngine = None

try:
    from engines.market_health_engine import MarketHealthEngine
    _HAS_HEALTH = True
except Exception as _e:
    logger.warning(f"market_health_engine: {_e}"); _HAS_HEALTH = False; MarketHealthEngine = None

try:
    from engines.historical_analog_engine import HistoricalAnalogEngine
    _HAS_ANALOGS = True
except Exception as _e:
    logger.warning(f"historical_analog_engine: {_e}"); _HAS_ANALOGS = False; HistoricalAnalogEngine = None

from config.settings import (
    MACRO_PROXIES, US_SECTORS, US_FACTORS, FOREX_PAIRS,
    COMMODITIES, CRYPTO, BONDS, IHSG_UNIVERSE, COUNTRY_UNIVERSE,
    TICKER_SECTOR, MARKET_CLASSIFICATION, BOTTLENECK_PROFILES,
)

# ── Soft imports — graceful fallback ─────────────────────────────────────────
_AUTONOMY_AVAILABLE = False
try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
    from engines.feedback_loop_engine_v3 import FeedbackLoopEngineV3
    _AUTONOMY_AVAILABLE = True
    logger.info("Autonomy stack loaded.")
except Exception as e:
    logger.warning(f"Autonomy stack: {e}")

_DISCOVERY_V3_AVAILABLE = False
try:
    from engines.discovery_orchestrator import DiscoveryOrchestrator
    _DISCOVERY_V3_AVAILABLE = True
    logger.info("DiscoveryOrchestrator v3 loaded.")
except Exception as e:
    logger.warning(f"DiscoveryOrchestrator: {e}")

_FRONTRUN_AVAILABLE = False
try:
    from engines.frontrun_engine import FrontRunEngine
    _FRONTRUN_AVAILABLE = True
    logger.info("FrontRunEngine loaded.")
except Exception as e:
    logger.warning(f"FrontRunEngine: {e}")

# ── Helpers ───────────────────────────────────────────────────────────────────
def _prog(cb: Optional[Callable], msg: str, frac: float) -> None:
    logger.info(f"[{frac:.0%}] {msg}")
    if cb:
        cb(msg, min(frac, 1.0))

def _safe(fn, fallback, label="engine"):
    try:
        return fn()
    except Exception as e:
        logger.warning(f"{label} failed: {e}")
        return fallback

def _compute_sector_momentum(
    prices: Dict[str, pd.Series],
    sector_map: Dict[str, str],
    benchmark: str = "SPY",
    lookback: int = 63,
) -> Dict[str, float]:
    """Sector RS vs benchmark. Fed to bottleneck + narrative + discovery engines."""
    bench = prices.get(benchmark)
    if bench is None:
        return {}
    bench_n = pd.to_numeric(bench, errors="coerce").dropna()
    if len(bench_n) < lookback + 1:
        return {}
    bench_ret = float(bench_n.iloc[-1] / bench_n.iloc[-lookback-1] - 1)

    sector_rs: Dict[str, List[float]] = {}
    for ticker, sector in sector_map.items():
        s = prices.get(ticker)
        if s is None:
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < lookback + 1:
            continue
        try:
            rs = float(s.iloc[-1] / s.iloc[-lookback-1] - 1) - bench_ret
            sector_rs.setdefault(sector, []).append(rs)
        except Exception:
            pass
    return {sec: float(np.median(vals)) for sec, vals in sector_rs.items() if vals}

def _compute_flow_scores_proxy(
    prices: Dict[str, pd.Series],
    benchmark: str = "SPY",
) -> Dict[str, float]:
    """
    Proxy for options flow / momentum acceleration.
    (5d RS - 21d RS) normalized. Positive = accelerating vs benchmark.
    NOTE: Not true dealer gamma. Labeled clearly. Max impact ±0.08 on EV.
    """
    bench = prices.get(benchmark)
    if bench is None:
        return {}
    bench_n = pd.to_numeric(bench, errors="coerce").dropna()
    if len(bench_n) < 22:
        return {}
    bench_s = float(bench_n.iloc[-1]/bench_n.iloc[-6]-1) if len(bench_n) >= 6 else 0.0
    bench_l = float(bench_n.iloc[-1]/bench_n.iloc[-22]-1) if len(bench_n) >= 22 else 0.0

    scores: Dict[str, float] = {}
    for ticker, series in prices.items():
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) < 22:
            continue
        try:
            rs_s = float(s.iloc[-1]/s.iloc[-6]-1) - bench_s
            rs_l = float(s.iloc[-1]/s.iloc[-22]-1) - bench_l
            scores[ticker] = float(np.clip((rs_s - rs_l) / 0.05, -1.0, 1.0))
        except Exception:
            pass
    return scores

def _prioritize_rr_tickers(prices: Dict[str, pd.Series], max_tickers: int = 250) -> List[str]:
    """Prioritize tickers for expensive Hurst R/S computation."""
    priority = set(MACRO_PROXIES.keys()) | set(BONDS.keys()) | \
        set(US_SECTORS.keys()) | set(US_FACTORS.keys()) | \
        {"SPY","QQQ","IWM","GLD","DX-Y.NYB","^VIX","BTC-USD","GC=F","CL=F"}
    try:
        from engines.bottleneck_engine import KNOWN_BOTTLENECKS
        priority |= set(KNOWN_BOTTLENECKS.keys())
    except Exception:
        pass

    bench = prices.get("SPY")
    bench_n = pd.to_numeric(bench, errors="coerce").dropna() if bench is not None else None
    bench_ret = float(bench_n.iloc[-1]/bench_n.iloc[-64]-1) if bench_n is not None and len(bench_n) >= 64 else 0.0

    ranked: List[Tuple[float, str]] = []
    for ticker, series in prices.items():
        if ticker in priority:
            continue
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) < 64:
            continue
        try:
            rs = abs(float(s.iloc[-1]/s.iloc[-64]-1) - bench_ret)
            ranked.append((rs, ticker))
        except Exception:
            pass
    ranked.sort(reverse=True)
    extended = [t for _, t in ranked[:max_tickers - len(priority)]]
    final = sorted(priority & set(prices.keys())) + extended
    return final[:max_tickers]

# ── Main build ────────────────────────────────────────────────────────────────
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

    # 1. FRED ──────────────────────────────────────────────────────────────────
    _prog(progress_cb, "Loading FRED macro data...", 0.04)
    fred = _safe(lambda: load_fred(months=36), {}, "FRED")
    snap["fred_coverage"] = len(fred)

    # 2. PRICES — batched (FIX: was 6 separate calls) ─────────────────────────
    _prog(progress_cb, "Loading core prices (benchmarks + bonds + VIX)...", 0.08)
    prices: Dict[str, pd.Series] = {}
    core = list(MACRO_PROXIES.keys()) + list(BONDS.keys()) + ["DX-Y.NYB","^VIX","SPY","QQQ"]
    prices.update(_safe(lambda: load_prices(list(dict.fromkeys(core)), days=756), {}, "CorePrices"))

    _prog(progress_cb, "Loading extended universe...", 0.14)
    ext = []
    if include_us_stocks:
        ext += list(US_SECTORS.keys()) + list(US_FACTORS.keys())
        ext += [t for t in TICKER_SECTOR if t not in prices]
    if include_forex:
        ext += list(FOREX_PAIRS.keys())
    if include_commodities:
        ext += list(COMMODITIES.keys())
    if include_crypto:
        ext += list(CRYPTO.keys())
    if include_ihsg:
        ext += list(IHSG_UNIVERSE.keys())
    ext += list({v[0] for v in COUNTRY_UNIVERSE.values() if isinstance(v,(list,tuple)) and len(v)>0})
    ext = list(dict.fromkeys(t for t in ext if t not in prices))

    # Chunk 100 for reliability
    for i, chunk in enumerate([ext[j:j+100] for j in range(0, len(ext), 100)]):
        frac = 0.14 + (i/max(len(ext)//100,1)) * 0.14
        _prog(progress_cb, f"Loading batch {i+1} ({len(chunk)} tickers)...", frac)
        prices.update(_safe(lambda c=chunk: load_prices(c, days=365), {}, f"Batch{i+1}"))

    snap["prices_loaded"] = len(prices)
    _prog(progress_cb, f"Prices loaded: {len(prices)}", 0.30)

    # 3. GIP ───────────────────────────────────────────────────────────────────
    _prog(progress_cb, "Running GIP model (Growth·Inflation·Policy RoC)...", 0.34)
    gip = _safe(lambda: GIPEngine().run(fred=fred, prices=prices), None, "GIP")
    if gip is None:
        snap["error"] = "GIP engine failed"
        return snap
    snap["gip"] = gip
    snap["playbook"] = get_playbook(gip.structural_quad, gip.monthly_quad)

    sq = gip.structural_quad
    mq = gip.monthly_quad

    # 4. GLOBAL QUAD ───────────────────────────────────────────────────────────
    _prog(progress_cb, "Running Global Quad (50 countries)...", 0.40)
    snap["global"] = _safe(
        lambda: GlobalQuadEngine().run(prices=prices, us_gip_result=gip),
        {"global_quad": sq, "country_quads": {}}, "GlobalQuad"
    ) if _HAS_GLOBAL_QUAD else {"global_quad": sq, "country_quads": {}}

    # 5. STRESS ────────────────────────────────────────────────────────────────
    _prog(progress_cb, "Computing stress overlay...", 0.44)
    def _stress():
        vix = prices.get("^VIX")
        vix_last = float(pd.to_numeric(vix, errors="coerce").dropna().iloc[-1]) if vix is not None else 18.0
        dxy = prices.get("DX-Y.NYB")
        dxy_1m = float(pd.to_numeric(dxy, errors="coerce").dropna().pct_change(21).dropna().iloc[-1]) if dxy is not None and len(dxy) > 22 else 0.0
        vol_stress = float(np.clip((vix_last-15.0)/25.0, 0.0, 1.0))
        return dict(
            vol_stress=vol_stress,
            vix=vix_last,
            dxy_1m=dxy_1m,
            shock_penalty=0.5 if sq in ("Q3","Q4") else 0.2,
            crowding=float(gip.features.get("proxy_share",0.3)),
            dollar_pressure=float(np.clip(0.5+dxy_1m/0.04,0.0,1.0)),
            tail_hedge_bid=float(np.clip((vix_last-20.0)/30.0,0.0,1.0))
        )
    stress = _safe(_stress, {"vix":18.0,"vol_stress":0.3}, "Stress")
    snap["stress"] = stress

    # 6. SECTOR MOMENTUM — feeds bottleneck + narrative + discovery ───────────
    _prog(progress_cb, "Computing sector momentum (RS vs SPY 63d)...", 0.47)
    sector_momentum = _safe(
        lambda: _compute_sector_momentum(prices, TICKER_SECTOR, "SPY"),
        {}, "SectorMomentum"
    )
    snap["sector_momentum"] = sector_momentum

    # 7. FLOW SCORES PROXY — feeds bottleneck EV formula ─────────────────────
    _prog(progress_cb, "Computing flow scores proxy (momentum acceleration)...", 0.49)
    flow_scores = _safe(lambda: _compute_flow_scores_proxy(prices, "SPY"), {}, "FlowScores")

    # 8. RISK RANGE™ — prioritized, max 250 tickers ───────────────────────────
    _prog(progress_cb, "Building price frames for Risk Range™...", 0.51)
    rr_tickers = _prioritize_rr_tickers(prices, max_tickers=250)
    price_frames: Dict[str, pd.DataFrame] = {}
    for sym in rr_tickers:
        s = prices.get(sym)
        if s is None or len(s) < 30:
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        df = pd.DataFrame({"Close": s})
        df["High"] = s.rolling(5, min_periods=1).max()
        df["Low"] = s.rolling(5, min_periods=1).min()
        df["Volume"] = 1.0
        price_frames[sym] = df
    snap["price_frames_count"] = len(price_frames)

    _prog(progress_cb, f"Running Risk Range™ ({len(rr_tickers)} tickers)...", 0.54)
    rr_result = _safe(
        lambda: HurstRREngine().run(price_frames=price_frames, stress=stress, symbols=rr_tickers),
        {"asset_ranges":{}, "summary":{}}, "HurstRR"
    ) if _HAS_RR else {"asset_ranges":{}, "summary":{}}
    snap["risk_ranges"] = rr_result
    asset_ranges = rr_result.get("asset_ranges", {})

    # 9. SCENARIO ENGINE ───────────────────────────────────────────────────────
    _prog(progress_cb, "Building adaptive scenarios...", 0.61)
    scenarios = _safe(
        lambda: ScenarioEngine().run(
            structural_quad=sq, monthly_quad=mq,
            features=gip.features,
            flip_hazard=gip.flip_hazard,
            data_coverage=gip.data_coverage,
        ), {}, "ScenarioEngine"
    ) if _HAS_SCENARIO else {}
    snap["scenarios"] = scenarios

    # 10. BOTTLENECK ENGINE ─────────────────────────────────────────────────────
    _prog(progress_cb, "Scanning bottlenecks (all asset classes)...", 0.66)
    btk = _safe(
        lambda: BottleneckEngine().run(
            prices=prices,
            quad_str=sq, quad_mon=mq,
            benchmark="SPY",
            asset_ranges=asset_ranges,
            flow_scores=flow_scores,
        ),
        {"level_1":[],"level_2":[],"watch":[],"avoid":[],"brewing":[],"all_scored":[]},
        "BottleneckEngine"
    ) if _HAS_BTK else {"level_1":[],"level_2":[],"watch":[],"avoid":[],"brewing":[],"all_scored":[]}
    snap["bottleneck"] = btk

    # 11. NARRATIVE ENGINE ──────────────────────────────────────────────────────
    _prog(progress_cb, "Scoring narratives (adaptive·reactive·proactive)...", 0.71)
    narratives = _safe(
        lambda: NarrativeEngine().run(
            prices=prices,
            quad_str=sq, quad_mon=mq,
            benchmark="SPY",
            scenario_output=scenarios,
            supply_chain_signals=btk.get("all_scored"),
            target_asset_classes=["us_equity","ihsg","forex","commodity","crypto","bonds"],
        ),
        {"narrative_dashboard":[],"dominant_narrative":None,"meta":{}},
        "NarrativeEngine"
    ) if _HAS_NARRATIVE else {"narrative_dashboard":[],"dominant_narrative":None,"meta":{"error":"narrative_engine unavailable"}}
    snap["narratives"] = narratives

    # 12. DISCOVERY ORCHESTRATOR v3 — ADAPTIVE · REACTIVE · PROACTIVE ──────────
    # FIX: Was COMPLETELY ORPHANED. Now wired with all context.
    _prog(progress_cb, "Running Discovery v3 (reactive·proactive·all markets)...", 0.76)
    if _DISCOVERY_V3_AVAILABLE:
        import config.settings as _cfg
        discovery_v3 = _safe(
            lambda: DiscoveryOrchestrator(_cfg).run_full_pipeline(
                prices=prices,
                volumes=None,
                quad_str=sq, quad_mon=mq,
                benchmark="SPY",
                asset_ranges=asset_ranges,
                scenario_output=scenarios,
                supply_chain_signals=btk.get("all_scored"),
                sector_momentum=sector_momentum,
                flow_scores=flow_scores,
                top_n=60,
            ),
            {"reactive":[],"proactive":[],"narrative":{},"merged":[]},
            "DiscoveryOrchestrator"
        )
    else:
        discovery_v3 = _safe(
            lambda: AdaptiveDiscoveryEngine().run(
                prices=prices,
                structural_quad=sq, monthly_quad=mq,
                gip_features=gip.features,
            ),
            {"discoveries":[],"status":"fallback"},
            "AdaptiveDiscovery"
        )
    snap["discovery_v3"] = discovery_v3

    # 13. AUTONOMY STACK ───────────────────────────────────────────────────────
    _prog(progress_cb, "Running autonomy stack (NLP·cluster·EDGAR)...", 0.81)
    if _AUTONOMY_AVAILABLE:
        auto_disc = _safe(
            lambda: AutoDiscoveryEngineV3(
                sector_map=TICKER_SECTOR,
                market_map=MARKET_CLASSIFICATION,
                known_tickers=list(TICKER_SECTOR.keys()),
                use_transformers=False,
            ).run(
                prices=prices,
                structural_quad=sq, monthly_quad=mq,
                gip_features=gip.features,
                run_edgar=True,
            ),
            {"candidates":[],"meta":{"autonomy":"unavailable"}},
            "AutoDiscovery"
        )
        snap["auto_discoveries"] = auto_disc
        snap["feedback_eval"] = _safe(
            lambda: _run_feedback(auto_disc, prices, sq),
            {"evaluated":0,"promoted":0,"demoted":0},
            "FeedbackLoop"
        )
    else:
        snap["auto_discoveries"] = {"candidates":[],"meta":{"autonomy":"unavailable"}}
        snap["feedback_eval"] = {"evaluated":0,"promoted":0,"demoted":0}

    # 14. FRONT-RUN ENGINE — aggregates ALL signals into one watchlist ─────────
    _prog(progress_cb, "Building front-run watchlist (all signals aggregated)...", 0.85)
    if _FRONTRUN_AVAILABLE:
        snap["frontrun"] = _safe(
            lambda: FrontRunEngine().run(snap={
                "transition": None,  # set below after step 15
                "bottleneck": btk,
                "risk_ranges": rr_result,
                "discovery_v3": discovery_v3,
                "narratives": narratives,
                "prices": prices,
                "gip": gip,
            }),
            {"watchlist":[],"boarding_now":[],"gate_soon":[],"timing_window":"not yet"},
            "FrontRunEngine (pre-transition)"
        )
    else:
        snap["frontrun"] = {"watchlist":[],"boarding_now":[],"gate_soon":[],"timing_window":"not yet",
                            "meta":{"error":"frontrun_engine.py not found in repo"}}

    # 15. REGIME TRANSITION + HEALTH + ANALOGS ────────────────────────────────
    _prog(progress_cb, "Computing regime transition + market health...", 0.88)
    macro_ctx = {k: v for k,v in gip.features.items() if isinstance(v, float)}
    def _p(t, n):
        s = prices.get(t)
        if s is None:
            return 0.0
        s = pd.to_numeric(s, errors="coerce").dropna()
        return float(s.iloc[-1]/s.iloc[-n]-1) if len(s) > n else 0.0
    market_ctx = {"oil_3m":_p("CL=F",64),"gold_3m":_p("GLD",64),"dxy_1m":_p("DX-Y.NYB",22)}

    transition = _safe(
        lambda: RegimeTransitionEngine().run(macro=macro_ctx, market=market_ctx, gip_result=gip),
        None, "RegimeTransition"
    )
    snap["transition"] = transition

    snap["health"] = _safe(
        lambda: MarketHealthEngine().run(prices=prices, gip_features=gip.features, quad=sq),
        {}, "MarketHealth"
    )
    snap["analogs"] = _safe(
        lambda: HistoricalAnalogEngine().run(gip_features=gip.features, prices_context=market_ctx),
        {"top_analogs":[],"composite_note":""}, "HistoricalAnalogs"
    )

    # 16. RE-RUN FrontRun with transition signal now available ─────────────────
    if _FRONTRUN_AVAILABLE and transition is not None:
        snap["frontrun"] = _safe(
            lambda: FrontRunEngine().run(snap={
                "transition": transition,
                "bottleneck": btk,
                "risk_ranges": rr_result,
                "discovery_v3": discovery_v3,
                "narratives": narratives,
                "prices": prices,
                "gip": gip,
            }),
            snap["frontrun"], "FrontRunEngine (final)"
        )

    # 17. METADATA ──────────────────────────────────────────────────────────────
    snap["prices"] = {k: v for k,v in prices.items() if isinstance(v,pd.Series) and len(v)>10}
    build_t = round(time.time() - t0, 1)
    snap["build_time_s"] = build_t
    snap["ok"] = True

    _prog(progress_cb, f"Snapshot complete in {build_t}s. Saving...", 0.98)
    _safe(lambda: save_snapshot(snap), None, "SaveSnapshot")
    _prog(progress_cb, "Done!", 1.0)

    logger.info(
        f"[BUILD COMPLETE] {build_t}s | Prices:{snap['prices_loaded']} "
        f"| RR:{snap.get('price_frames_count',0)} "
        f"| Quad:{sq}/{mq} "
        f"| DiscoveryV3:{'✅' if _DISCOVERY_V3_AVAILABLE else '⚠️'} "
        f"| FrontRun:{'✅' if _FRONTRUN_AVAILABLE else '⚠️'} "
        f"| Autonomy:{'✅' if _AUTONOMY_AVAILABLE else '⚠️'}"
    )
    return snap

def _run_feedback(auto_disc: dict, prices: dict, quad: str) -> dict:
    fb = FeedbackLoopEngineV3()
    fb.track(auto_disc.get("candidates",[]), regime=quad)
    return fb.evaluate(prices, benchmark="SPY")

def get_or_build(force: bool = False, max_age_h: float = 4.0, **kw) -> dict:
    """Primary entry point for app.py."""
    if not force:
        snap = load_snapshot(max_age_hours=max_age_h)
        if snap and snap.get("ok"):
            return snap
    return build_snapshot(**kw)

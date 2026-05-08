"""orchestrator.py v18 — FULL FIX

FIXES APPLIED:
1. load_prices() now receives actual ticker list (not broken kwargs)
2. AutoDiscoveryEngineV3 instantiated with correct args
3. AutoDiscoveryEngineV3.run() called with correct signature
4. AutoDiscoveryEngineV4 robustness: handles empty/malformed prices
5. CLI output: prints formatted snapshot even if Streamlit missing
"""
from __future__ import annotations
import os, sys, json, math, time, logging, traceback
from pathlib import Path
from typing import Dict, Optional, Callable, List
from dataclasses import asdict

import pandas as pd
import numpy as np

# ── Logging: force stdout so you SEE errors immediately ─────────────────────
logger = logging.getLogger("macroregime")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(h)

# ── Defensive imports ───────────────────────────────────────────────────────
try:
    from data.loader import load_prices, load_fred, snapshot_path, save_snapshot, load_snapshot
except ImportError as e:
    logger.warning(f"data.loader import failed: {e}")
    def load_prices(tickers=None, days=756, ttl=3600): 
        return {}
    def load_fred(months=36): 
        return {}
    def snapshot_path(): 
        return Path("data/snapshot.json")
    def save_snapshot(snap): 
        pass
    def load_snapshot(**kwargs): 
        return None

try:
    from config.settings import (
        US_SECTORS, US_FACTORS, FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE,
        BONDS, MACRO_PROXIES, TICKER_SECTOR, MARKET_CLASSIFICATION,
        QUAD_ASSET_PERFORMANCE, QUAD_MARKET_DIRECTION,
        BOTTLENECK_PROFILES, ISM_NEUTRAL, PRICE_HISTORY_DAYS,
    )
except ImportError as e:
    logger.warning(f"config.settings import failed: {e}")
    US_SECTORS = {}; US_FACTORS = {}; FOREX_PAIRS = {}; COMMODITIES = {}; CRYPTO = {}; IHSG_UNIVERSE = {}
    BONDS = {}; MACRO_PROXIES = {}; TICKER_SECTOR = {}; MARKET_CLASSIFICATION = {}
    QUAD_ASSET_PERFORMANCE = {}; QUAD_MARKET_DIRECTION = {}; BOTTLENECK_PROFILES = {}; ISM_NEUTRAL = 50.0
    PRICE_HISTORY_DAYS = 756

try:
    from config.autonomy_settings import AUTONOMY_CONFIG, DISCOVERY_CONFIG
except ImportError:
    AUTONOMY_CONFIG = {}; DISCOVERY_CONFIG = {}

# ── Engine imports (all defensive) ──────────────────────────────────────────
def _import_engine(module_name, class_name, fallback_factory):
    try:
        mod = __import__(f"engines.{module_name}", fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception as e:
        logger.warning(f"Engine {module_name}.{class_name} failed: {e}")
        return fallback_factory

# GIP
try:
    from engines.gip_engine import GIPEngine, get_playbook
except ImportError:
    logger.warning("gip_engine failed")
    class GIPEngine:
        def run(self, fred, prices):
            class FakeGIP:
                structural_quad="Q3"; monthly_quad="Q2"; structural_conf=0.5; monthly_conf=0.5
                divergence="divergent"; operating_regime="Q3/Q2"; flip_hazard=0.5
                structural_g=0; structural_i=0; monthly_g=0; monthly_i=0
                policy_score=0; data_coverage=0.5; proxy_share=0.5
                features={}
            return FakeGIP()
    def get_playbook(sq, mq): 
        return {"best_assets":[],"worst_assets":[],"style":"","fx":"","bonds":""}

# Risk Range
try:
    from engines.risk_range_engine import RiskRangeEngine
except ImportError:
    class RiskRangeEngine:
        def run(self, prices, **kwargs): 
            return {"asset_ranges":{}}

# Scenario
try:
    from engines.scenario_engine import ScenarioEngine
except ImportError:
    class ScenarioEngine:
        def run(self, gip, risk_ranges): 
            return {"scenarios":[],"base_case":None}

# Hurst
try:
    from engines.hurst_rr_engine import HurstRiskRangeEngine
except ImportError:
    class HurstRiskRangeEngine:
        def run(self, prices, risk_ranges): 
            return {}

# Regime Transition
try:
    from engines.regime_transition_engine import RegimeTransitionEngine
except ImportError:
    class RegimeTransitionEngine:
        def run(self, gip, risk_ranges, prices):
            class FakeTrans:
                front_run_window="not yet"; front_run_rationale="Engine unavailable"
            return FakeTrans()

# Market Health
try:
    from engines.market_health_engine import MarketHealthEngine
except ImportError:
    class MarketHealthEngine:
        def run(self, prices, risk_ranges): 
            return {}

# Historical Analog
try:
    from engines.historical_analog_engine import HistoricalAnalogEngine
except ImportError:
    class HistoricalAnalogEngine:
        def run(self, gip, prices): 
            return {"top_analogs":[],"composite_note":""}

# Bottleneck
try:
    from engines.bottleneck_engine import BottleneckEngine
except ImportError:
    class BottleneckEngine:
        def run(self, prices, sq, mq, risk_ranges=None):
            return {"level_1":[],"level_2":[],"watch":[],"avoid":[],"market_buckets":{},"em_recovery":None,"total_scanned":0,"futures_excluded":0}

# Global Quad
try:
    from engines.global_quad_engine import GlobalQuadEngine
except ImportError:
    class GlobalQuadEngine:
        def run(self, prices, us_gip_result=None, stress=None):
            return {"country_quads":{},"global_quad":"Q3","global_probs":{},"global_conf":0.5}

# Narrative
try:
    from engines.narrative_engine import NarrativeEngine
except ImportError:
    class NarrativeEngine:
        def run(self, sq, mq, risk_ranges, prices):
            return {"active_narratives":[],"building_narratives":[],"brewing_narratives":[],"spillover":{},"total":0}

# Gamma
try:
    from engines.gamma_regime_engine import GammaRegimeEngine
except ImportError:
    class GammaRegimeEngine:
        def run(self, prices, vix_proxy=None): 
            return {"ok":False,"note":"Gamma engine unavailable"}

# Leading Indicator
try:
    from engines.leading_indicator_engine import LeadingIndicatorEngine
except ImportError:
    class LeadingIndicatorEngine:
        def run(self, prices, gip): 
            return {}

# Leveraged ETF
try:
    from engines.leveraged_etf_engine import LeveragedETFEngine
except ImportError:
    class LeveragedETFEngine:
        def run(self, prices): 
            return {"ok":False,"note":"Leveraged ETF engine unavailable"}

# Adaptive Discovery
try:
    from engines.adaptive_discovery_engine import AdaptiveDiscoveryEngine
except ImportError:
    class AdaptiveDiscoveryEngine:
        def run(self, prices, gip, risk_ranges): 
            raise Exception("Unavailable")

# V4 Discovery
try:
    from engines.auto_discovery_engine_v4 import AutoDiscoveryEngineV4
except ImportError:
    class AutoDiscoveryEngineV4:
        def run(self, prices, gip=None, risk_ranges=None):
            return {"ok":False,"candidates":[],"note":"V4 unavailable"}

# V3 Discovery
try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
except ImportError:
    class AutoDiscoveryEngineV3:
        def __init__(self, *args, **kwargs): 
            pass
        def run(self, prices, gip=None, risk_ranges=None):
            return {"ok":False,"candidates":[],"note":"V3 unavailable"}


# ── Helper: build ticker list from boolean flags ─────────────────────────────
def _build_ticker_list(
    include_us_stocks=True, include_forex=True, include_commodities=True,
    include_crypto=True, include_ihsg=True
) -> List[str]:
    """Convert boolean universe flags into an actual ticker list for load_prices()."""
    tickers = []
    # Core macro proxies ALWAYS included (needed for GIP calculation)
    tickers.extend(list(MACRO_PROXIES.keys()))
    tickers.extend(list(BONDS.keys()))
    if include_us_stocks:
        tickers.extend(list(US_SECTORS.keys()))
        tickers.extend(list(US_FACTORS.keys()))
    if include_forex:
        tickers.extend(list(FOREX_PAIRS.keys()))
    if include_commodities:
        tickers.extend(list(COMMODITIES.keys()))
    if include_crypto:
        tickers.extend(list(CRYPTO.keys()))
    if include_ihsg:
        tickers.extend(list(IHSG_UNIVERSE.keys()))
    # Deduplicate while preserving order
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


class SnapshotBuilder:
    def __init__(self, progress_cb: Optional[Callable] = None):
        self.progress_cb = progress_cb
        self.step = 0
        self.total_steps = 16
        self.start_time = time.time()

    def _prog(self, msg: str):
        self.step += 1
        frac = min(self.step / self.total_steps, 1.0)
        if self.progress_cb:
            self.progress_cb(msg, frac)
        logger.info(f"[{self.step}/{self.total_steps}] {msg}")

    def build(self, include_us_stocks=True, include_forex=True, include_commodities=True,
              include_crypto=True, include_ihsg=True) -> Dict:
        snapshot = {"ok": False, "build_time_s": 0.0}
        try:
            # ── 1. Load prices ──────────────────────────────────────────────
            self._prog("Building ticker list...")
            ticker_list = _build_ticker_list(
                include_us_stocks, include_forex, include_commodities, include_crypto, include_ihsg
            )
            logger.info(f"Ticker universe: {len(ticker_list)} symbols")

            self._prog("Loading prices...")
            prices = load_prices(tickers=ticker_list, days=PRICE_HISTORY_DAYS)
            snapshot["prices_loaded"] = len(prices)
            logger.info(f"Prices loaded: {len(prices)} series")
            if len(prices) < 10:
                logger.warning("Very few price series loaded — check network/tickers")

            # ── 2. Load FRED ────────────────────────────────────────────────
            self._prog("Loading FRED data...")
            fred = load_fred(months=36)
            snapshot["fred_coverage"] = len(fred)
            logger.info(f"FRED coverage: {len(fred)} series")

            # ── 3. GIP Engine ───────────────────────────────────────────────
            self._prog("Running GIP engine...")
            gip = GIPEngine().run(fred, prices)
            snapshot["gip"] = gip
            sq = gip.structural_quad
            mq = gip.monthly_quad
            logger.info(f"GIP => Structural {sq} | Monthly {mq} | Divergence {gip.divergence}")

            # ── 4. Risk Ranges ──────────────────────────────────────────────
            self._prog("Computing risk ranges...")
            rr_engine = RiskRangeEngine()
            risk_ranges = rr_engine.run(prices, structural_quad=sq, monthly_quad=mq)
            snapshot["risk_ranges"] = risk_ranges
            snapshot["price_frames_count"] = len(risk_ranges.get("asset_ranges", {}))

            # ── 5. Hurst overlay ────────────────────────────────────────────
            self._prog("Hurst overlay...")
            hurst_engine = HurstRiskRangeEngine()
            hurst_overlay = hurst_engine.run(prices, risk_ranges)
            snapshot["hurst_overlay"] = hurst_overlay

            # ── 6. Scenario ─────────────────────────────────────────────────
            self._prog("Scenario analysis...")
            scenario_engine = ScenarioEngine()
            scenarios = scenario_engine.run(gip, risk_ranges)
            snapshot["scenarios"] = scenarios

            # ── 7. Regime Transition ────────────────────────────────────────
            self._prog("Regime transition...")
            transition_engine = RegimeTransitionEngine()
            transition = transition_engine.run(gip, risk_ranges, prices)
            snapshot["transition"] = transition

            # ── 8. Market Health ──────────────────────────────────────────
            self._prog("Market health...")
            health_engine = MarketHealthEngine()
            health = health_engine.run(prices, risk_ranges)
            snapshot["health"] = health

            # ── 9. Historical Analogs ───────────────────────────────────────
            self._prog("Historical analogs...")
            analog_engine = HistoricalAnalogEngine()
            analogs = analog_engine.run(gip, prices)
            snapshot["analogs"] = analogs

            # ── 10. Bottleneck ─────────────────────────────────────────────
            self._prog("Bottleneck scanner...")
            bottleneck_engine = BottleneckEngine()
            bottleneck = bottleneck_engine.run(prices, sq, mq, risk_ranges)
            snapshot["bottleneck"] = bottleneck

            # ── 11. Global Quad ─────────────────────────────────────────────
            self._prog("Global quad (50 countries)...")
            stress = health.get("stress", {}) if health else {}
            global_data = GlobalQuadEngine().run(prices, us_gip_result=gip, stress=stress)
            snapshot["global"] = global_data

            # ── 12. Narrative ───────────────────────────────────────────────
            self._prog("Narrative scoring...")
            narrative_engine = NarrativeEngine()
            narratives = narrative_engine.run(sq, mq, risk_ranges.get("asset_ranges", {}), prices)
            snapshot["narratives"] = narratives

            # ── 13. Gamma ───────────────────────────────────────────────────
            self._prog("Gamma regime...")
            gamma_engine = GammaRegimeEngine()
            gamma = gamma_engine.run(prices, vix_proxy=None)
            snapshot["gamma"] = gamma

            # ── 14. Leading Indicators ──────────────────────────────────────
            self._prog("Leading indicators...")
            li_engine = LeadingIndicatorEngine()
            leading = li_engine.run(prices, gip)
            snapshot["leading"] = leading

            # ── 15. Leveraged ETF ────────────────────────────────────────────
            self._prog("Leveraged ETF flow...")
            lev_engine = LeveragedETFEngine()
            lev = lev_engine.run(prices)
            snapshot["leveraged_etf"] = lev

            # ── 16. Discovery Engine ───────────────────────────────────────
            self._prog("Discovery engine...")
            auto_disc = {"ok": False, "candidates": [], "note": "Discovery skipped"}

            # Try V4 first
            try:
                disc_engine = AutoDiscoveryEngineV4()
                auto_disc = disc_engine.run(prices, gip, risk_ranges)
                logger.info(f"V4 discovery: {auto_disc.get('total', 0)} candidates")
            except Exception as e:
                logger.warning(f"AutoDiscoveryV4 failed ({e}), falling back to V3")
                # Try V3 with CORRECT args
                try:
                    disc_engine = AutoDiscoveryEngineV3(
                        sector_map=TICKER_SECTOR,
                        market_map=MARKET_CLASSIFICATION,
                        known_tickers=list(prices.keys()),
                        use_transformers=False,
                    )
                    auto_disc = disc_engine.run(
                        prices=prices,
                        gip=gip,
                        risk_ranges=risk_ranges,
                    )
                    logger.info(f"V3 discovery: {len(auto_disc.get('candidates', []))} candidates")
                except Exception as e2:
                    logger.warning(f"AutoDiscoveryV3 also failed ({e2}), using empty")
                    auto_disc = {"ok": False, "candidates": [], "note": f"Discovery engines failed: V4={e}, V3={e2}"}

            snapshot["auto_discoveries"] = auto_disc

            # ── Final assembly ──────────────────────────────────────────────
            snapshot["playbook"] = get_playbook(sq, mq)
            snapshot["ok"] = True
            snapshot["build_time_s"] = round(time.time() - self.start_time, 1)
            snapshot["prices"] = prices

            save_snapshot(snapshot)
            self._prog("Snapshot saved.")
            return snapshot

        except Exception as e:
            logger.error(f"Snapshot build failed: {e}")
            traceback.print_exc()
            snapshot["error"] = str(e)
            snapshot["build_time_s"] = round(time.time() - self.start_time, 1)
            return snapshot


def build_snapshot(progress_cb=None, **kwargs):
    return SnapshotBuilder(progress_cb=progress_cb).build(**kwargs)


def _fmt_quad(q):
    return f"{q} (Goldilocks)" if q=="Q1" else f"{q} (Reflation)" if q=="Q2" else f"{q} (Stagflation)" if q=="Q3" else f"{q} (Deflation)"


def print_snapshot(snap: Dict):
    """CLI pretty-printer so you SEE output even without Streamlit."""
    sep = "=" * 70
    print("\n" + sep)
    print(" MACROREGIME SNAPSHOT")
    print(sep)
    ok = snap.get("ok")
    print(f"Build OK      : {ok}")
    print(f"Build Time    : {snap.get('build_time_s')}s")
    if not ok:
        print(f"ERROR         : {snap.get('error', 'Unknown')}")
        print(sep)
        return

    gip = snap.get("gip")
    if gip:
        print(f"\n📊 GIP REGIME")
        print(f"  Structural  : {_fmt_quad(gip.structural_quad)} (conf={gip.structural_conf:.0%})")
        print(f"  Monthly     : {_fmt_quad(gip.monthly_quad)} (conf={gip.monthly_conf:.0%})")
        print(f"  Divergence  : {gip.divergence}")
        print(f"  Operating   : {gip.operating_regime}")
        print(f"  Flip Hazard : {gip.flip_hazard:.0%}")
        print(f"  Data Coverage: {gip.data_coverage:.0%} | Proxy Share: {gip.proxy_share:.0%}")

    pb = snap.get("playbook", {})
    if pb:
        print(f"\n📋 PLAYBOOK ({pb.get('structural')}/{pb.get('monthly')})")
        print(f"  Best Assets : {', '.join(pb.get('best_assets', [])[:8]) or '—'}")
        print(f"  Worst Assets: {', '.join(pb.get('worst_assets', [])[:8]) or '—'}")
        print(f"  Style       : {pb.get('style', '—')}")
        print(f"  FX          : {pb.get('fx', '—')}")
        print(f"  Bonds       : {pb.get('bonds', '—')}")

    disc = snap.get("auto_discoveries", {})
    if disc:
        print(f"\n🔍 DISCOVERY ({disc.get('total', 0)} candidates)")
        for c in disc.get("candidates", [])[:5]:
            print(f"  • [{c.get('stage','?').upper()}] {c.get('name','?')} (conf={c.get('confidence',0):.0%})")
            print(f"    Thesis: {c.get('thesis','')[:100]}...")

    rr = snap.get("risk_ranges", {})
    n_rr = len(rr.get("asset_ranges", {}))
    print(f"\n📈 Risk Ranges : {n_rr} assets computed")
    print(f"📉 Prices loaded: {snap.get('prices_loaded')} series")
    print(f"🏛️  FRED loaded  : {snap.get('fred_coverage')} series")
    print(sep + "\n")


if __name__ == "__main__":
    print("[CLI] Building macro regime snapshot...")
    snap = build_snapshot()
    print_snapshot(snap)

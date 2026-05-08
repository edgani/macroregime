"""orchestrator.py v17 - Full macro regime snapshot builder

FIX v17:
- Defensive imports (fallback if engine files missing)
- Import NarrativeEngine from narrative_engine.py
- Import GammaRegimeEngine with defensive DataFrame handling
- Fix logger initialization (avoid duplicate handlers)
"""
from __future__ import annotations
import os, sys, json, math, time, logging, traceback
from pathlib import Path
from typing import Dict, Optional, Callable
from dataclasses import asdict

import pandas as pd
import numpy as np

# Logging setup (defensive against duplicate handlers)
logger = logging.getLogger("macroregime")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Defensive imports ───────────────────────────────────────────────────────
# data.loader
try:
    from data.loader import load_prices, load_fred, snapshot_path, save_snapshot, load_snapshot
except ImportError as e:
    logger.warning(f"data.loader import failed: {e}")
    def load_prices(**kwargs): return {}
    def load_fred(): return {}
    def snapshot_path(): return Path("data/snapshot.json")
    def save_snapshot(snap): pass
    def load_snapshot(**kwargs): return None

# config.settings
try:
    from config.settings import (
        US_EQUITY_UNIVERSE, FOREX_UNIVERSE, COMMODITY_UNIVERSE, CRYPTO_UNIVERSE, IHSG_UNIVERSE,
        TICKER_SECTOR, MARKET_CLASSIFICATION, QUAD_ASSET_PERFORMANCE, QUAD_MARKET_DIRECTION,
        BOTTLENECK_PROFILES, ISM_NEUTRAL,
    )
except ImportError as e:
    logger.warning(f"config.settings import failed: {e}")
    US_EQUITY_UNIVERSE = {}; FOREX_UNIVERSE = {}; COMMODITY_UNIVERSE = {}; CRYPTO_UNIVERSE = {}; IHSG_UNIVERSE = {}
    TICKER_SECTOR = {}; MARKET_CLASSIFICATION = {}; QUAD_ASSET_PERFORMANCE = {}; QUAD_MARKET_DIRECTION = {}
    BOTTLENECK_PROFILES = {}; ISM_NEUTRAL = 50.0

# config.autonomy_settings
try:
    from config.autonomy_settings import AUTONOMY_CONFIG, DISCOVERY_CONFIG
except ImportError:
    AUTONOMY_CONFIG = {}; DISCOVERY_CONFIG = {}

# engines — all with defensive fallback
ENGINE_FALLBACKS = {}

def _import_engine(module_name, class_name):
    try:
        mod = __import__(f"engines.{module_name}", fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception as e:
        logger.warning(f"Engine {module_name}.{class_name} failed: {e}")
        return ENGINE_FALLBACKS.get(class_name, lambda: None)

# Import all engines
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
    def get_playbook(sq, mq): return {"best_assets":[],"worst_assets":[],"style":"","fx":"","bonds":""}

try:
    from engines.risk_range_engine import RiskRangeEngine
except ImportError:
    class RiskRangeEngine:
        def run(self, prices, **kwargs): return {"asset_ranges":{}}

try:
    from engines.scenario_engine import ScenarioEngine
except ImportError:
    class ScenarioEngine:
        def run(self, gip, risk_ranges): return {"scenarios":[],"base_case":None}

try:
    from engines.hurst_rr_engine import HurstRiskRangeEngine
except ImportError:
    class HurstRiskRangeEngine:
        def run(self, prices, risk_ranges): return {}

try:
    from engines.regime_transition_engine import RegimeTransitionEngine
except ImportError:
    class RegimeTransitionEngine:
        def run(self, gip, risk_ranges, prices): 
            class FakeTrans:
                front_run_window="not yet"; front_run_rationale="Engine unavailable"
            return FakeTrans()

try:
    from engines.market_health_engine import MarketHealthEngine
except ImportError:
    class MarketHealthEngine:
        def run(self, prices, risk_ranges): return {}

try:
    from engines.historical_analog_engine import HistoricalAnalogEngine
except ImportError:
    class HistoricalAnalogEngine:
        def run(self, gip, prices): return {"top_analogs":[],"composite_note":""}

try:
    from engines.bottleneck_engine import BottleneckEngine
except ImportError:
    class BottleneckEngine:
        def run(self, prices, sq, mq, risk_ranges=None): 
            return {"level_1":[],"level_2":[],"watch":[],"avoid":[],"market_buckets":{},"em_recovery":None,"total_scanned":0,"futures_excluded":0}

try:
    from engines.global_quad_engine import GlobalQuadEngine
except ImportError:
    class GlobalQuadEngine:
        def run(self, prices, us_gip_result=None, stress=None): 
            return {"country_quads":{},"global_quad":"Q3","global_probs":{},"global_conf":0.5}

try:
    from engines.narrative_engine import NarrativeEngine
except ImportError:
    class NarrativeEngine:
        def run(self, sq, mq, risk_ranges, prices): 
            return {"active_narratives":[],"building_narratives":[],"brewing_narratives":[],"spillover":{},"total":0}

try:
    from engines.gamma_regime_engine import GammaRegimeEngine
except ImportError:
    class GammaRegimeEngine:
        def run(self, prices, vix_proxy=None): return {"ok":False,"note":"Gamma engine unavailable"}

try:
    from engines.leading_indicator_engine import LeadingIndicatorEngine
except ImportError:
    class LeadingIndicatorEngine:
        def run(self, prices, gip): return {}

try:
    from engines.leveraged_etf_engine import LeveragedETFEngine
except ImportError:
    class LeveragedETFEngine:
        def run(self, prices): return {"ok":False,"note":"Leveraged ETF engine unavailable"}

try:
    from engines.adaptive_discovery_engine import AdaptiveDiscoveryEngine
except ImportError:
    class AdaptiveDiscoveryEngine:
        def run(self, prices, gip, risk_ranges): raise Exception("Unavailable")

try:
    from engines.auto_discovery_engine_v4 import AutoDiscoveryEngineV4
except ImportError:
    class AutoDiscoveryEngineV4:
        def run(self, prices, gip, risk_ranges): 
            return {"ok":False,"candidates":[],"note":"V4 unavailable"}

try:
    from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3
except ImportError:
    class AutoDiscoveryEngineV3:
        def run(self, prices, gip, risk_ranges): 
            return {"ok":False,"candidates":[],"note":"V3 unavailable"}

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
            self._prog("Loading prices...")
            prices = load_prices(
                include_us_stocks=include_us_stocks, include_forex=include_forex,
                include_commodities=include_commodities, include_crypto=include_crypto,
                include_ihsg=include_ihsg,
            )
            snapshot["prices_loaded"] = len(prices)

            self._prog("Loading FRED data...")
            fred = load_fred()
            snapshot["fred_coverage"] = len(fred)

            self._prog("Running GIP engine...")
            gip = GIPEngine().run(fred, prices)
            snapshot["gip"] = gip
            sq = gip.structural_quad; mq = gip.monthly_quad

            self._prog("Computing risk ranges...")
            rr_engine = RiskRangeEngine()
            risk_ranges = rr_engine.run(prices, structural_quad=sq, monthly_quad=mq)
            snapshot["risk_ranges"] = risk_ranges
            snapshot["price_frames_count"] = len(risk_ranges.get("asset_ranges", {}))

            self._prog("Hurst overlay...")
            hurst_engine = HurstRiskRangeEngine()
            hurst_overlay = hurst_engine.run(prices, risk_ranges)
            snapshot["hurst_overlay"] = hurst_overlay

            self._prog("Scenario analysis...")
            scenario_engine = ScenarioEngine()
            scenarios = scenario_engine.run(gip, risk_ranges)
            snapshot["scenarios"] = scenarios

            self._prog("Regime transition...")
            transition_engine = RegimeTransitionEngine()
            transition = transition_engine.run(gip, risk_ranges, prices)
            snapshot["transition"] = transition

            self._prog("Market health...")
            health_engine = MarketHealthEngine()
            health = health_engine.run(prices, risk_ranges)
            snapshot["health"] = health

            self._prog("Historical analogs...")
            analog_engine = HistoricalAnalogEngine()
            analogs = analog_engine.run(gip, prices)
            snapshot["analogs"] = analogs

            self._prog("Bottleneck scanner...")
            bottleneck_engine = BottleneckEngine()
            bottleneck = bottleneck_engine.run(prices, sq, mq, risk_ranges)
            snapshot["bottleneck"] = bottleneck

            self._prog("Global quad (50 countries)...")
            stress = health.get("stress", {}) if health else {}
            global_data = GlobalQuadEngine().run(prices, us_gip_result=gip, stress=stress)
            snapshot["global"] = global_data

            self._prog("Narrative scoring...")
            narrative_engine = NarrativeEngine()
            narratives = narrative_engine.run(sq, mq, risk_ranges.get("asset_ranges", {}), prices)
            snapshot["narratives"] = narratives

            self._prog("Gamma regime...")
            gamma_engine = GammaRegimeEngine()
            gamma = gamma_engine.run(prices, vix_proxy=None)
            snapshot["gamma"] = gamma

            self._prog("Leading indicators...")
            li_engine = LeadingIndicatorEngine()
            leading = li_engine.run(prices, gip)
            snapshot["leading"] = leading

            self._prog("Leveraged ETF flow...")
            lev_engine = LeveragedETFEngine()
            lev = lev_engine.run(prices)
            snapshot["leveraged_etf"] = lev

            self._prog("Discovery engine...")
            try:
                disc_engine = AutoDiscoveryEngineV4()
                auto_disc = disc_engine.run(prices, gip, risk_ranges)
            except Exception as e:
                logger.warning(f"AutoDiscoveryV4 failed ({e}), falling back to V3")
                try:
                    disc_engine = AutoDiscoveryEngineV3()
                    auto_disc = disc_engine.run(prices, gip, risk_ranges)
                except Exception as e2:
                    logger.warning(f"AutoDiscoveryV3 also failed ({e2}), using empty")
                    auto_disc = {"ok": False, "candidates": [], "note": "Discovery engines failed"}
            snapshot["auto_discoveries"] = auto_disc

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

if __name__ == "__main__":
    snap = build_snapshot()
    print(f"Snapshot built: {snap.get('ok')} in {snap.get('build_time_s')}s")

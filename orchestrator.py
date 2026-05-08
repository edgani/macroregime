"""orchestrator.py v17 - Full macro regime snapshot builder

FIX v17:
- Import NarrativeEngine from narrative_engine.py (was patch instructions)
- Import GammaRegimeEngine with defensive DataFrame handling
- Fix logger initialization (avoid duplicate handlers)
- Cleaner step progression
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

# Engines
from data.loader import load_prices, load_fred, snapshot_path, save_snapshot, load_snapshot
from config.settings import (
    US_EQUITY_UNIVERSE, FOREX_UNIVERSE, COMMODITY_UNIVERSE, CRYPTO_UNIVERSE, IHSG_UNIVERSE,
    TICKER_SECTOR, MARKET_CLASSIFICATION, QUAD_ASSET_PERFORMANCE, QUAD_MARKET_DIRECTION,
    BOTTLENECK_PROFILES, ISM_NEUTRAL,
)
from config.autonomy_settings import AUTONOMY_CONFIG, DISCOVERY_CONFIG

from engines.gip_engine import GIPEngine, get_playbook
from engines.risk_range_engine import RiskRangeEngine
from engines.scenario_engine import ScenarioEngine
from engines.hurst_rr_engine import HurstRiskRangeEngine
from engines.regime_transition_engine import RegimeTransitionEngine
from engines.market_health_engine import MarketHealthEngine
from engines.historical_analog_engine import HistoricalAnalogEngine
from engines.bottleneck_engine import BottleneckEngine
from engines.global_quad_engine import GlobalQuadEngine
from engines.narrative_engine import NarrativeEngine
from engines.gamma_regime_engine import GammaRegimeEngine
from engines.leading_indicator_engine import LeadingIndicatorEngine
from engines.leveraged_etf_engine import LeveragedETFEngine
from engines.adaptive_discovery_engine import AdaptiveDiscoveryEngine
from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3

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
                disc_engine = AdaptiveDiscoveryEngine()
                auto_disc = disc_engine.run(prices, gip, risk_ranges)
            except Exception as e:
                logger.warning(f"AdaptiveDiscoveryEngine failed ({e}), falling back to V3")
                disc_engine = AutoDiscoveryEngineV3()
                auto_disc = disc_engine.run(prices, gip, risk_ranges)
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

"""engines/narrative_engine_v3.py — Multi-Market Adaptive · Reactive · Proactive Narrative Engine

Narrative = the "story" market believes about why an asset/sector should move.
Covers: US Equities, Forex, Commodities, Crypto, IHSG, Bonds, Global/Country.

Three modes:
  • ADAPTIVE : Narrative weights auto-adjust per macro regime (Q1-Q4)
  • REACTIVE : Detects narrative ignition from simultaneous sector spikes + volume clustering
  • PROACTIVE: Predicts dominant narrative 4-8 weeks forward from supply chain + macro signals

Integrates with scenario_engine.py and bottleneck_discovery_v3.py.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# NARRATIVE TAXONOMY — Cross-market, cross-asset
# ═══════════════════════════════════════════════════════════════════════════════
NARRATIVES: Dict[str, Dict] = {
    # US / Global Tech
    "ai_infrastructure": {
        "sectors": ["ai_compute", "ai_memory", "ai_optics", "ai_power", "ai_power_infra",
                    "ai_packaging", "transformer_infra", "ai_networking", "semis_taiwan", "semis_korea"],
        "keywords": ["AI data center", "GPU shortage", "HBM", "CoWoS", "photonics", "CPO", "SiC", "power density"],
        "quad_boost": {"Q1": 0.85, "Q2": 0.75, "Q3": 0.55, "Q4": 0.35},
        "markets": ["us_equity", "crypto", "global"],
    },
    "decentralized_ai": {
        "sectors": ["depin_ai"],
        "keywords": ["decentralized compute", "DePIN", "Bittensor", "Render", "AI agent", "on-chain AI"],
        "quad_boost": {"Q1": 0.90, "Q2": 0.70, "Q3": 0.30, "Q4": 0.40},
        "markets": ["crypto"],
    },
    # Energy & Hard Assets
    "energy_transition": {
        "sectors": ["uranium", "ai_power_infra", "utilities", "energy_infra", "transformer_infra"],
        "keywords": ["nuclear renaissance", "AI power", "grid upgrade", "baseload", "gas turbine"],
        "quad_boost": {"Q1": 0.60, "Q2": 0.80, "Q3": 0.75, "Q4": 0.50},
        "markets": ["us_equity", "commodity", "ihsg", "global"],
    },
    "hard_assets_scarcity": {
        "sectors": ["precious_metals", "commodity_copper", "commodity_aluminum", "nickel", "coal", "uranium"],
        "keywords": ["copper shortage", "de-dollarization", "central bank buying", "supply deficit", "resource nationalism"],
        "quad_boost": {"Q1": 0.65, "Q2": 0.85, "Q3": 0.90, "Q4": 0.85},
        "markets": ["commodity", "us_equity", "ihsg", "forex"],
    },
    # Defense & Geopolitics
    "defense_reshoring": {
        "sectors": ["defense"],
        "keywords": ["NATO spending", "munitions shortage", "hypersonic", "missile defense", "industrial base"],
        "quad_boost": {"Q1": 0.55, "Q2": 0.70, "Q3": 0.80, "Q4": 0.65},
        "markets": ["us_equity", "commodity"],
    },
    # Healthcare
    "healthcare_scarcity": {
        "sectors": ["healthcare_eq", "pharma"],
        "keywords": ["GLP-1 shortage", "robotic surgery", "aging population", "drug pricing", "obesity epidemic"],
        "quad_boost": {"Q1": 0.60, "Q2": 0.55, "Q3": 0.85, "Q4": 0.80},
        "markets": ["us_equity"],
    },
    # Shipping & Logistics
    "shipping_supply_crisis": {
        "sectors": ["dry_bulk_shipping", "osv_hulu", "tanker_ship", "indonesia_shipping", "indonesia_osv"],
        "keywords": ["Red Sea disruption", "fleet renewal", "IMO 2023", "day rates", "vessel shortage", "offshore drilling ramp"],
        "quad_boost": {"Q1": 0.60, "Q2": 0.80, "Q3": 0.65, "Q4": 0.45},
        "markets": ["ihsg", "us_equity", "commodity"],
    },
    # Indonesia-specific
    "indonesia_commodity_supercycle": {
        "sectors": ["coal", "nickel", "cpo_palm", "osv_hulu", "oil_distribution", "indonesia_mining", "indonesia_energy"],
        "keywords": ["IHSG", "foreign flow", "CKPN cascade", "offshore drilling", "1 juta BPD", "JIIPE", "tanker cycle", "OSV day rates"],
        "quad_boost": {"Q1": 0.70, "Q2": 0.85, "Q3": 0.60, "Q4": 0.40},
        "markets": ["ihsg"],
    },
    "indonesia_banking_recovery": {
        "sectors": ["banking"],
        "keywords": ["BBCA", "BBRI", "foreign net buy", "CKPN", "NPL", "BI rate", "rupiah stability"],
        "quad_boost": {"Q1": 0.80, "Q2": 0.75, "Q3": 0.50, "Q4": 0.35},
        "markets": ["ihsg"],
    },
    # Macro / FX
    "dxy_bearish_em_recovery": {
        "sectors": ["em_fx", "ihsg_banks", "ihsg_consumer", "commodity_gold"],
        "keywords": ["USD bearish TREND", "EM FX relief", "DXY breakdown", "Fed pivot", "capital flows"],
        "quad_boost": {"Q1": 0.85, "Q2": 0.70, "Q3": 0.75, "Q4": 0.40},
        "markets": ["forex", "ihsg", "commodity", "global"],
    },
    "fed_pivot_liquidity": {
        "sectors": ["bonds", "us_equity", "em_fx", "crypto"],
        "keywords": ["Fed cut", "liquidity injection", "QT end", "yield curve steepening", "credit easing"],
        "quad_boost": {"Q1": 0.90, "Q2": 0.60, "Q3": 0.50, "Q4": 0.85},
        "markets": ["bonds", "us_equity", "crypto", "global"],
    },
    # China / Asia
    "china_reopening_commodity": {
        "sectors": ["commodity_copper", "commodity_aluminum", "energy_infra", "coal", "cpo_palm"],
        "keywords": ["China stimulus", "property rescue", "infrastructure", "commodity demand", "Australian export"],
        "quad_boost": {"Q1": 0.75, "Q2": 0.85, "Q3": 0.60, "Q4": 0.30},
        "markets": ["commodity", "global", "ihsg"],
    },
    # Bonds / Rates
    "bond_duration_bull": {
        "sectors": ["bonds"],
        "keywords": ["TLT", "yield collapse", "deflation", "recession pricing", "flight to quality"],
        "quad_boost": {"Q1": 0.40, "Q2": 0.30, "Q3": 0.80, "Q4": 0.95},
        "markets": ["bonds"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-MARKET NARRATIVE SPILLOVER
# ═══════════════════════════════════════════════════════════════════════════════
NARRATIVE_SPILLOVER: Dict[str, List[Tuple[str, float]]] = {
    "ai_infrastructure": [
        ("decentralized_ai", 0.80), ("hard_assets_scarcity", 0.40),
        ("energy_transition", 0.60), ("china_reopening_commodity", 0.30),
    ],
    "decentralized_ai": [
        ("ai_infrastructure", 0.50),
    ],
    "energy_transition": [
        ("hard_assets_scarcity", 0.70), ("ai_infrastructure", 0.50),
        ("indonesia_commodity_supercycle", 0.40),
    ],
    "hard_assets_scarcity": [
        ("energy_transition", 0.50), ("shipping_supply_crisis", 0.40),
        ("indonesia_commodity_supercycle", 0.60),
    ],
    "defense_reshoring": [
        ("hard_assets_scarcity", 0.60), ("indonesia_commodity_supercycle", 0.20),
    ],
    "shipping_supply_crisis": [
        ("indonesia_commodity_supercycle", 0.60), ("hard_assets_scarcity", 0.40),
        ("energy_transition", 0.30),
    ],
    "indonesia_commodity_supercycle": [
        ("shipping_supply_crisis", 0.60), ("hard_assets_scarcity", 0.50),
        ("china_reopening_commodity", 0.45),
    ],
    "dxy_bearish_em_recovery": [
        ("indonesia_banking_recovery", 0.70), ("indonesia_commodity_supercycle", 0.55),
        ("fed_pivot_liquidity", 0.60), ("hard_assets_scarcity", 0.50),
    ],
    "fed_pivot_liquidity": [
        ("dxy_bearish_em_recovery", 0.70), ("ai_infrastructure", 0.50),
        ("indonesia_banking_recovery", 0.40), ("bond_duration_bull", 0.80),
    ],
    "china_reopening_commodity": [
        ("hard_assets_scarcity", 0.60), ("indonesia_commodity_supercycle", 0.50),
        ("shipping_supply_crisis", 0.30),
    ],
    "bond_duration_bull": [
        ("fed_pivot_liquidity", 0.80), ("dxy_bearish_em_recovery", 0.50),
    ],
}


@dataclass
class NarrativeScore:
    name: str
    strength: float
    ignition_detected: bool
    regime_weight: float
    sector_breadth: int
    volume_intensity: float
    lead_sector: str
    lead_market: str
    forecast_weeks_4: float
    forecast_weeks_8: float
    spillover_to: List[Tuple[str, float]] = field(default_factory=list)
    catalyst_triggers: List[str] = field(default_factory=list)
    invalidators: List[str] = field(default_factory=list)


class NarrativeEngineV3:
    def __init__(self, settings_module):
        self.cfg = settings_module
        self.sector_map = getattr(settings_module, "TICKER_SECTOR", {})
        self.market_map = getattr(settings_module, "MARKET_CLASSIFICATION", {})
        self.us_buckets = getattr(settings_module, "US_BUCKETS", {})
        self.ihsg_buckets = getattr(settings_module, "IHSG_BUCKETS", {})
        self.fx_buckets = getattr(settings_module, "FX_BUCKETS", {})
        self.comm_buckets = getattr(settings_module, "COMMODITY_BUCKETS", {})
        self.crypto_buckets = getattr(settings_module, "CRYPTO_BUCKETS", {})
        self.country_univ = getattr(settings_module, "COUNTRY_UNIVERSE", {})

    # ── ADAPTIVE ──────────────────────────────────────────────────────────────
    def adaptive_weights(self, quad_str: str) -> Dict[str, float]:
        qk = quad_str.upper()
        return {name: meta["quad_boost"].get(qk, 0.5) for name, meta in NARRATIVES.items()}

    # ── REACTIVE: Multi-market ignition ───────────────────────────────────────
    def reactive_ignition(
        self,
        prices: Dict[str, pd.Series],
        volumes: Optional[Dict[str, pd.Series]] = None,
        lookback: int = 21,
        breadth_threshold: float = 0.35,
        volume_z_threshold: float = 1.5,
        return_threshold: float = 0.06,
    ) -> Dict[str, NarrativeScore]:
        scores: Dict[str, NarrativeScore] = {}

        for name, meta in NARRATIVES.items():
            sectors = meta["sectors"]
            participating = []

            for sector in sectors:
                tickers = [t for t, s in self.sector_map.items() if s == sector]
                if not tickers:
                    tickers = (self.us_buckets.get(sector, []) +
                               self.ihsg_buckets.get(sector, []) +
                               self.fx_buckets.get(sector, []) +
                               self.comm_buckets.get(sector, []) +
                               self.crypto_buckets.get(sector, []))

                spiked = 0
                sector_returns = []
                vol_intensities = []
                for t in tickers:
                    close = prices.get(t)
                    if close is None or len(close) < lookback + 5:
                        continue
                    close = pd.to_numeric(close, errors="coerce").dropna()
                    ret = float(close.iloc[-1] / close.iloc[-lookback] - 1)
                    sector_returns.append(ret)
                    if ret > return_threshold:
                        spiked += 1
                        if volumes and t in volumes:
                            vol = pd.to_numeric(volumes[t], errors="coerce").dropna()
                            if len(vol) >= lookback + 20:
                                rv = float(vol.tail(lookback).mean())
                                hv = float(vol.tail(lookback + 60).head(60).mean())
                                hs = float(vol.tail(lookback + 60).head(60).std())
                                if hs > 0:
                                    vol_intensities.append(max((rv - hv) / hs, 0.0))

                breadth = spiked / max(len(tickers), 1)
                if sector_returns:
                    avg_ret = np.mean(sector_returns)
                    max_ret = max(sector_returns) if sector_returns else 0
                else:
                    avg_ret = 0
                    max_ret = 0

                if breadth >= breadth_threshold or max_ret > 0.12:
                    participating.append({
                        "sector": sector, "breadth": breadth, "avg_ret": avg_ret,
                        "max_ret": max_ret, "tickers_spiked": spiked, "total_tickers": len(tickers),
                        "market": self._sector_market(sector),
                    })

            if participating:
                avg_breadth = np.mean([p["breadth"] for p in participating])
                avg_ret = np.mean([p["avg_ret"] for p in participating])
                max_ret = max([p["max_ret"] for p in participating])
                vol_int = np.mean(vol_intensities) if vol_intensities else 0.0

                strength = float(np.clip(
                    (avg_breadth * 0.35) +
                    (min(avg_ret / 0.20, 1.0) * 0.30) +
                    (min(max_ret / 0.30, 1.0) * 0.20) +
                    (min(vol_int / 2.0, 1.0) * 0.15),
                    0.0, 1.0
                ))
                ignition = strength >= 0.55 and avg_breadth >= breadth_threshold
                lead = max(participating, key=lambda x: x["max_ret"])

                scores[name] = NarrativeScore(
                    name=name, strength=round(strength, 3), ignition_detected=ignition,
                    regime_weight=0.0, sector_breadth=len(participating),
                    volume_intensity=round(vol_int, 3), lead_sector=lead["sector"],
                    lead_market=lead.get("market", "us_equity"),
                    forecast_weeks_4=0.0, forecast_weeks_8=0.0,
                    spillover_to=NARRATIVE_SPILLOVER.get(name, []),
                    catalyst_triggers=[f"{p['sector']} ({p['market']}) breadth {p['breadth']:.0%}" for p in participating],
                    invalidators=["Breadth drops below 20%", "Volume intensity normalizes", "Lead sector breaks TREND LRR"],
                )
        return scores

    def _sector_market(self, sector: str) -> str:
        for t, s in self.sector_map.items():
            if s == sector:
                return self.market_map.get(t, "us_equity")
        return "us_equity"

    # ── PROACTIVE ─────────────────────────────────────────────────────────────
    def proactive_forecast(
        self,
        current_scores: Dict[str, NarrativeScore],
        scenario_output: Dict,
        supply_chain_signals: Optional[Dict] = None,
        weeks: int = 8,
    ) -> Dict[str, NarrativeScore]:
        supply_chain_signals = supply_chain_signals or {}
        base_case = scenario_output.get("base_case")
        to_quad = base_case.to_quad if base_case else "Q3"
        to_prob = base_case.probability if base_case else 0.25
        target_weights = self.adaptive_weights(to_quad)
        forecasts = {}

        for name, current in current_scores.items():
            decay = 0.85 ** (weeks / 4)
            base_forecast = current.strength * decay
            scenario_boost = target_weights.get(name, 0.5) * to_prob * 0.30
            supply_boost = 0.0
            sig = supply_chain_signals.get(name, {})
            if sig.get("order_backlog_growth", 0) > 0.30:
                supply_boost += 0.15
            if sig.get("lead_time_extension", 0) > 12:
                supply_boost += 0.12
            if sig.get("capex_surge", False):
                supply_boost += 0.10
            if sig.get("inventory_days_compression", 0) > 20:
                supply_boost += 0.08
            if sig.get("foreign_flow_acceleration", False):
                supply_boost += 0.10

            spillover_boost = 0.0
            for source_name, spill_list in NARRATIVE_SPILLOVER.items():
                source_score = current_scores.get(source_name)
                if source_score and source_score.strength > 0.60:
                    for target_narr, spill_w in spill_list:
                        if target_narr == name:
                            spillover_boost += source_score.strength * spill_w * 0.25

            forecast = float(np.clip(base_forecast + scenario_boost + supply_boost + spillover_boost, 0.0, 1.0))
            forecast_4 = float(np.clip(current.strength * (0.90 if weeks >= 4 else 1.0) + scenario_boost * 0.5 + supply_boost * 0.3, 0.0, 1.0))

            forecasts[name] = NarrativeScore(
                name=name, strength=current.strength, ignition_detected=current.ignition_detected,
                regime_weight=round(target_weights.get(name, 0.5), 3), sector_breadth=current.sector_breadth,
                volume_intensity=current.volume_intensity, lead_sector=current.lead_sector,
                lead_market=current.lead_market, forecast_weeks_4=round(forecast_4, 3),
                forecast_weeks_8=round(forecast, 3), spillover_to=current.spillover_to,
                catalyst_triggers=current.catalyst_triggers + [f"Scenario {to_quad} prob {to_prob:.0%}"],
                invalidators=current.invalidators,
            )
        return forecasts

    # ── SPILLOVER: Cross-market narrative translation ─────────────────────────
    def spillover_translation(
        self,
        dominant_narrative: str,
        target_asset_class: str,
        prices: Dict[str, pd.Series],
    ) -> List[Dict]:
        spill = NARRATIVE_SPILLOVER.get(dominant_narrative, [])
        results = []
        for spill_name, spill_w in spill:
            meta = NARRATIVES.get(spill_name)
            if not meta:
                continue
            sectors = meta["sectors"]
            for sector in sectors:
                tickers = [t for t, s in self.sector_map.items() if s == sector]
                if target_asset_class == "crypto":
                    tickers = [t for t in tickers if self.market_map.get(t) == "crypto"]
                elif target_asset_class == "ihsg":
                    tickers = [t for t in tickers if t.endswith(".JK")]
                elif target_asset_class == "commodity":
                    tickers = [t for t in tickers if self.market_map.get(t) == "commodity"]
                elif target_asset_class == "forex":
                    tickers = [t for t in tickers if self.market_map.get(t) == "forex"]
                elif target_asset_class == "bonds":
                    tickers = [t for t in tickers if self.market_map.get(t) == "bonds"]
                elif target_asset_class == "global":
                    tickers = [t for t in tickers if t in self.country_univ]

                for t in tickers:
                    close = prices.get(t)
                    if close is None or len(close) < 30:
                        continue
                    close = pd.to_numeric(close, errors="coerce").dropna()
                    ret_21d = float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) > 22 else 0
                    ret_63d = float(close.iloc[-1] / close.iloc[-64] - 1) if len(close) > 64 else 0
                    hi52 = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
                    px = float(close.iloc[-1])
                    pct_from_hi = (px - hi52) / max(hi52, 1e-9)
                    results.append({
                        "narrative_source": dominant_narrative,
                        "narrative_target": spill_name,
                        "ticker": t, "asset_class": target_asset_class,
                        "spillover_weight": round(spill_w, 2),
                        "ret_21d": round(ret_21d, 3), "ret_63d": round(ret_63d, 3),
                        "pct_from_hi": round(pct_from_hi, 3),
                        "priced_in_score": round(
                            (1.0 if pct_from_hi > -0.05 else 0.5 if pct_from_hi > -0.15 else 0.0) * spill_w, 3
                        ),
                        "verdict": "fully_priced" if pct_from_hi > -0.05 else
                                   "partially_priced" if pct_from_hi > -0.20 else "not_priced_in",
                    })
        results.sort(key=lambda x: x["priced_in_score"], reverse=True)
        return results

    # ── MAIN RUN ──────────────────────────────────────────────────────────────
    def run(
        self,
        prices: Dict[str, pd.Series],
        volumes: Optional[Dict[str, pd.Series]] = None,
        quad_str: str = "Q3",
        scenario_output: Optional[Dict] = None,
        supply_chain_signals: Optional[Dict] = None,
        target_asset_classes: Optional[List[str]] = None,
    ) -> Dict:
        target_asset_classes = target_asset_classes or ["crypto", "forex", "commodity", "ihsg", "bonds", "global"]
        adaptive = self.adaptive_weights(quad_str)
        ignition = self.reactive_ignition(prices, volumes)
        forecasts = {}
        if scenario_output:
            forecasts = self.proactive_forecast(ignition, scenario_output, supply_chain_signals, 8)

        spillover = {}
        if ignition:
            dominant = max(ignition.items(), key=lambda x: x[1].strength)
            d_name, d_score = dominant
            if d_score.strength >= 0.50:
                for ac in target_asset_classes:
                    spillover[ac] = self.spillover_translation(d_name, ac, prices)

        narrative_dashboard = []
        for name in NARRATIVES:
            cur = ignition.get(name)
            fore = forecasts.get(name)
            narrative_dashboard.append({
                "narrative": name,
                "current_strength": round(cur.strength, 3) if cur else 0.0,
                "ignition": cur.ignition_detected if cur else False,
                "regime_weight": round(adaptive.get(name, 0.5), 3),
                "forecast_4w": round(fore.forecast_weeks_4, 3) if fore else 0.0,
                "forecast_8w": round(fore.forecast_weeks_8, 3) if fore else 0.0,
                "lead_sector": cur.lead_sector if cur else "",
                "lead_market": cur.lead_market if cur else "",
                "sector_breadth": cur.sector_breadth if cur else 0,
                "top_spillover": [s[0] for s in (cur.spillover_to if cur else [])][:3],
            })
        narrative_dashboard.sort(key=lambda x: x["current_strength"], reverse=True)

        return {
            "narrative_dashboard": narrative_dashboard,
            "dominant_narrative": d_name if ignition else None,
            "dominant_strength": round(d_score.strength, 3) if ignition else 0.0,
            "dominant_lead_market": d_score.lead_market if ignition else "",
            "adaptive_weights": {k: round(v, 3) for k, v in adaptive.items()},
            "ignition_details": {k: {
                "strength": v.strength, "ignition": v.ignition_detected,
                "lead_sector": v.lead_sector, "lead_market": v.lead_market,
                "volume_intensity": v.volume_intensity, "catalysts": v.catalyst_triggers,
            } for k, v in ignition.items()},
            "forecasts": {k: {
                "fw_4w": v.forecast_weeks_4, "fw_8w": v.forecast_weeks_8,
                "regime_weight": v.regime_weight,
            } for k, v in forecasts.items()},
            "spillover": spillover,
            "meta": {
                "quad": quad_str,
                "narratives_tracked": len(NARRATIVES),
                "igniting_now": sum(1 for v in ignition.values() if v.ignition_detected),
                "markets_covered": len(target_asset_classes),
            },
        }
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from collections import defaultdict

import numpy as np
from utils.math_utils import clamp01


BOTTLENECK_CATEGORIES = {
    "ai_compute": {
        "name": "AI Compute Bottleneck",
        "layers": [
            {"layer": "demand", "tickers": ["NVDA", "AMD", "AVGO", "TSM", "ASML"], "signals": ["capex", "backlog", "utilization"]},
            {"layer": "interconnect", "tickers": ["CRDO", "ALAB", "MRVL", "LITE", "COHR"], "signals": ["optics_shortage", "co_packaged_optics"]},
            {"layer": "memory", "tickers": ["MU", "WDC", "STX"], "signals": ["hbm_supply", "ddr5_transition"]},
            {"layer": "power", "tickers": ["VST", "CEG", "NNE", "SMR"], "signals": ["datacenter_power", "nuclear_renaissance"]},
            {"layer": "downstream", "tickers": ["AMZN", "MSFT", "GOOGL", "META"], "signals": ["inference_cost", "roi_timeline"]},
        ],
        "bottleneck_indicators": {
            "primary": ["LITE", "CRDO", "MRVL"],
            "confirmation": ["NVDA", "TSM"],
            "invalidation": ["AMD", "INTC"],
        },
    },
    "optics_photonics": {
        "name": "Optics/Photonics Shortage",
        "layers": [
            {"layer": "components", "tickers": ["LITE", "COHR", "NPTN", "AAOI"], "signals": ["order_book", "lead_time"]},
            {"layer": "substrates", "tickers": ["AMAT", "LRCX", "KLAC"], "signals": ["co_wafer_demand", "advanced_packaging"]},
            {"layer": "equipment", "tickers": ["TER", "FORM"], "signals": ["test_capacity", "photonic_test"]},
            {"layer": "end_market", "tickers": ["CIEN", "INFN", "ANET"], "signals": ["telco_capex", "ai_cluster_connect"]},
        ],
        "bottleneck_indicators": {
            "primary": ["LITE", "COHR"],
            "confirmation": ["CIEN", "ANET"],
            "invalidation": ["INFN"],
        },
    },
    "energy_transition": {
        "name": "Energy Transition Constraint",
        "layers": [
            {"layer": "uranium", "tickers": ["URA", "CCJ", "UUUU", "LEU"], "signals": ["contracting", "production_restart"]},
            {"layer": "grid", "tickers": ["VST", "NRG", "CEG"], "signals": ["interconnection_queue", "baseload_shortage"]},
            {"layer": "storage", "tickers": ["TSLA", "ENPH", "SEDG", "FLNC"], "signals": ["battery_supply", "lithium_price"]},
        ],
        "bottleneck_indicators": {
            "primary": ["URA", "CCJ"],
            "confirmation": ["VST", "CEG"],
            "invalidation": ["TSLA"],
        },
    },
    "indonesia_coal": {
        "name": "Indonesia Coal/Nickel Supply",
        "layers": [
            {"layer": "coal", "tickers": ["ADRO.JK", "PTBA.JK", "ITMG.JK"], "signals": ["export_quota", "domestic_demand"]},
            {"layer": "nickel", "tickers": ["ANTM.JK", "INCO.JK"], "signals": ["ev_battery_demand", "processing_capacity"]},
            {"layer": "shipping", "tickers": ["IPCM.JK", "TMAS.JK"], "signals": ["freight_rate", "port_congestion"]},
        ],
        "bottleneck_indicators": {
            "primary": ["ADRO.JK", "ANTM.JK"],
            "confirmation": ["PTBA.JK"],
            "invalidation": ["USDIDR=X"],
        },
    },
    "quantum_compute": {
        "name": "Quantum Computing Inflection",
        "layers": [
            {"layer": "hardware", "tickers": ["IONQ", "QUBT", "RGTI", "QBTS"], "signals": ["qubit_count", "error_rate"]},
            {"layer": "photonics", "tickers": ["LITE", "COHR"], "signals": ["photonic_qc", "interconnect"]},
            {"layer": "software", "tickers": ["MSFT", "GOOGL", "IBM"], "signals": ["quantum_advantage", "algorithm"]},
        ],
        "bottleneck_indicators": {
            "primary": ["IONQ", "RGTI"],
            "confirmation": ["GOOGL", "IBM"],
            "invalidation": ["MSFT"],
        },
    },
    "defense_rearm": {
        "name": "Global Defense Rearmament",
        "layers": [
            {"layer": "aerospace", "tickers": ["LMT", "NOC", "RTX", "GD"], "signals": ["backlog", "intl_orders"]},
            {"layer": "shipbuilding", "tickers": ["HII", "NSSC"], "signals": ["naval_budget", "yard_capacity"]},
            {"layer": "drone", "tickers": ["AVAV", "EH", "UAVS"], "signals": ["autonomy", "swarm_tech"]},
        ],
        "bottleneck_indicators": {
            "primary": ["LMT", "NOC"],
            "confirmation": ["RTX", "HII"],
            "invalidation": ["GD"],
        },
    },
}


@dataclass
class BottleneckSignal:
    category: str
    layer: str
    ticker: str
    demand_score: float
    supply_score: float
    pricing_score: float
    momentum_score: float
    composite: float
    stage: str
    front_run_ready: bool


@dataclass
class BottleneckDiscoveryOutput:
    active_bottlenecks: List[Dict]
    ticker_implications: Dict[str, List[str]]
    cross_market_chains: List[Dict]
    front_run_basket: List[Dict]
    summary: str


class BottleneckDiscoveryEngine:
    def __init__(self, prices: Dict[str, any], news_signals: Dict = None):
        self.prices = prices
        self.news = news_signals or {}

    def _ret_n(self, s, n: int) -> float:
        if s is None or len(s) < n + 1:
            return float("nan")
        return float(s.iloc[-1] / s.iloc[-(n + 1)] - 1.0)

    def _volatility(self, s, n: int) -> float:
        if s is None or len(s) < n + 1:
            return float("nan")
        returns = s.iloc[-n:].pct_change().dropna()
        return float(returns.std()) if len(returns) > 5 else float("nan")

    def _score_layer(self, layer_def: Dict) -> List[BottleneckSignal]:
        signals = []
        for ticker in layer_def["tickers"]:
            s = self.prices.get(ticker)
            if s is None or getattr(s, "empty", True):
                continue
            r1m = self._ret_n(s, 21)
            r3m = self._ret_n(s, 63)
            demand = clamp01(
                0.4 * (r3m / 0.15 if r3m > 0 else 0)
                + 0.3 * (r1m / 0.08 if r1m > 0 else 0)
                + 0.3
            )
            vol = self._volatility(s, 21)
            supply = clamp01(0.5 * demand + 0.5 * (1.0 - min(vol / 0.05, 1.0)))
            pricing = clamp01(
                0.6 * demand + 0.4 * (1.0 if r1m > 0 and r3m > 0 else 0.3)
            )
            composite = 0.35 * demand + 0.25 * supply + 0.25 * pricing + 0.15 * clamp01(
                r1m / 0.10 if r1m > 0 else 0
            )
            if composite > 0.70 and r3m > 0.20:
                stage = "mature"
            elif composite > 0.50 and r1m > 0.05:
                stage = "building"
            elif composite > 0.30:
                stage = "early"
            else:
                stage = "exhausted"
            signals.append(
                BottleneckSignal(
                    category=layer_def.get("category", ""),
                    layer=layer_def["layer"],
                    ticker=ticker,
                    demand_score=round(demand, 3),
                    supply_score=round(supply, 3),
                    pricing_score=round(pricing, 3),
                    momentum_score=round(clamp01(r1m / 0.10) if r1m > 0 else 0, 3),
                    composite=round(composite, 3),
                    stage=stage,
                    front_run_ready=(
                        stage in ["early", "building"] and composite > 0.45 and r1m > 0
                    ),
                )
            )
        return signals

    def _detect_market(self, ticker: str) -> str:
        if ticker.endswith(".JK"):
            return "IHSG"
        if ticker.endswith(("-USD", "=X", "=F")):
            return "FX/Commodity"
        return "US"

    def _trace_cross_market(self, category: str, all_signals: List[BottleneckSignal]) -> Dict:
        cat_def = BOTTLENECK_CATEGORIES.get(category, {})
        layers = cat_def.get("layers", [])
        indicators = cat_def.get("bottleneck_indicators", {})
        chain = []
        for layer in layers:
            layer_sigs = [s for s in all_signals if s.layer == layer["layer"]]
            if not layer_sigs:
                continue
            best = max(layer_sigs, key=lambda x: x.composite)
            chain.append(
                {
                    "layer": layer["layer"],
                    "leader": best.ticker,
                    "score": best.composite,
                    "stage": best.stage,
                    "market": self._detect_market(best.ticker),
                }
            )
        primary = indicators.get("primary", [])
        confirm = indicators.get("confirmation", [])
        invalid = indicators.get("invalidation", [])
        primary_scores = [s.composite for s in all_signals if s.ticker in primary]
        confirm_scores = [s.composite for s in all_signals if s.ticker in confirm]
        invalid_scores = [s.composite for s in all_signals if s.ticker in invalid]
        bottleneck_valid = (
            len(primary_scores) > 0
            and max(primary_scores) > 0.55
            and (len(confirm_scores) == 0 or max(confirm_scores) > 0.40)
            and (len(invalid_scores) == 0 or max(invalid_scores) < 0.60)
        )
        return {
            "category": category,
            "chain": chain,
            "bottleneck_valid": bottleneck_valid,
            "bottleneck_strength": round(max(primary_scores) if primary_scores else 0, 3),
            "primary_tickers": primary,
            "confirmation_tickers": confirm,
            "invalidation_tickers": invalid,
        }

    def _regime_fit(self, category: str, quad: str) -> float:
        fits = {
            "ai_compute": {"Q1": 1.3, "Q2": 1.2, "Q3": 0.7, "Q4": 0.5},
            "optics_photonics": {"Q1": 1.2, "Q2": 1.1, "Q3": 0.8, "Q4": 0.6},
            "energy_transition": {"Q1": 1.0, "Q2": 1.3, "Q3": 1.1, "Q4": 0.7},
            "indonesia_coal": {"Q1": 0.9, "Q2": 1.3, "Q3": 1.2, "Q4": 0.6},
            "quantum_compute": {"Q1": 1.2, "Q2": 1.0, "Q3": 0.6, "Q4": 0.5},
            "defense_rearm": {"Q1": 0.8, "Q2": 1.1, "Q3": 1.3, "Q4": 0.9},
        }
        return fits.get(category, {}).get(quad, 1.0)

    def _get_invalidators(self, category: str) -> str:
        inv = (
            BOTTLENECK_CATEGORIES.get(category, {})
            .get("bottleneck_indicators", {})
            .get("invalidation", [])
        )
        return ", ".join(inv) if inv else "market breadth"

    def run(self, current_quad: str = "Q?") -> BottleneckDiscoveryOutput:
        all_signals = []
        cross_chains = []
        for cat_key, cat_def in BOTTLENECK_CATEGORIES.items():
            for layer in cat_def["layers"]:
                layer["category"] = cat_key
                sigs = self._score_layer(layer)
                all_signals.extend(sigs)
            chain = self._trace_cross_market(cat_key, all_signals)
            if chain["bottleneck_valid"]:
                cross_chains.append(chain)

        bottleneck_scores = defaultdict(float)
        for s in all_signals:
            if s.front_run_ready:
                bottleneck_scores[s.category] += s.composite

        active = [
            {
                "category": cat,
                "composite_score": round(score, 3),
                "stage": self._aggregate_stage(
                    [s for s in all_signals if s.category == cat and s.front_run_ready]
                ),
                "lead_tickers": [
                    s.ticker
                    for s in all_signals
                    if s.category == cat and s.front_run_ready
                ][:5],
                "regime_alignment": self._regime_fit(cat, current_quad),
            }
            for cat, score in sorted(
                bottleneck_scores.items(), key=lambda x: x[1], reverse=True
            )
            if score > 1.0
        ]

        ticker_map = defaultdict(list)
        for s in all_signals:
            if s.front_run_ready:
                ticker_map[s.ticker].append(s.category)

        front_run = []
        for s in sorted(all_signals, key=lambda x: x.composite, reverse=True):
            if s.front_run_ready and s.composite > 0.55:
                front_run.append(
                    {
                        "ticker": s.ticker,
                        "market": self._detect_market(s.ticker),
                        "bottleneck": s.category,
                        "layer": s.layer,
                        "conviction": round(s.composite, 3),
                        "stage": s.stage,
                        "rationale": f"{s.layer} layer in {s.category}: demand={s.demand_score}, supply={s.supply_score}, pricing={s.pricing_score}",
                        "entry_trigger": "Momentum confirms + no invalidation leader",
                        "invalidation": f"Watch {self._get_invalidators(s.category)} for reversal",
                    }
                )

        summary = self._generate_summary(active, cross_chains, current_quad)
        return BottleneckDiscoveryOutput(
            active_bottlenecks=active,
            ticker_implications=dict(ticker_map),
            cross_market_chains=cross_chains,
            front_run_basket=front_run[:12],
            summary=summary,
        )

    def _aggregate_stage(self, signals: List[BottleneckSignal]) -> str:
        if not signals:
            return "none"
        stages = [s.stage for s in signals]
        if "early" in stages and "building" in stages:
            return "early/building"
        return max(set(stages), key=stages.count)

    def _generate_summary(self, active: List[Dict], chains: List[Dict], quad: str) -> str:
        if not active:
            return "No active bottlenecks detected. Stay in regime-driven positions."
        top = active[0]
        return (
            f"Top bottleneck: {top['category']} ({top['stage']} stage, "
            f"regime-fit {top['regime_alignment']:.2f}x). "
            f"{len(chains)} cross-market chains validated. "
            f"{len([c for c in chains if c['bottleneck_valid']])} front-run opportunities."
        )

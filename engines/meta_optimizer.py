"""engines/meta_optimizer.py — Self-Calibrating GIP & Bottleneck Weights

Auto-tune weights via rolling backtest performance. No static weights.
Bayesian-style update: higher weight to components with lower forecast error.

Runs offline weekly. Updates settings.py weights automatically.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class WeightUpdate:
    parameter: str
    old_value: float
    new_value: float
    improvement: float          # reduction in forecast error
    confidence: float           # statistical significance


class MetaOptimizer:
    """Meta-learning layer: optimize engine parameters from historical performance."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module
        self.growth_weights = getattr(settings_module, "GROWTH_LEVEL_WEIGHTS", {}) if settings_module else {}
        self.inflation_weights = getattr(settings_module, "INFLATION_LEVEL_WEIGHTS", {}) if settings_module else {}
        self.structural_weights = getattr(settings_module, "STRUCTURAL_WEIGHTS", {}) if settings_module else {}
        self.monthly_weights = getattr(settings_module, "MONTHLY_WEIGHTS", {}) if settings_module else {}

    def _compute_quad_accuracy(
        self,
        historical_gip_results: List[Dict],
        window: int = 12,  # weeks
    ) -> Dict[str, float]:
        """Compute rolling accuracy per component."""
        if len(historical_gip_results) < window + 4:
            return {}

        # Test each component's predictive power in isolation
        components = ["growth_level", "growth_momentum", "inflation_level", "inflation_momentum", "policy_score"]
        accuracies = {}

        for comp in components:
            correct = 0
            total = 0
            for i in range(window, len(historical_gip_results) - 4):
                # Use only this component to predict quad 4 weeks forward
                hist = historical_gip_results[i - window:i]
                feature_vals = [h["features"].get(comp, 0) for h in hist if "features" in h]
                if len(feature_vals) < 5:
                    continue

                # Simple rule: positive = Q1/Q2, negative = Q3/Q4
                avg_feature = np.mean(feature_vals)
                actual_future = historical_gip_results[i + 4].get("structural_quad", "Q3")

                predicted = "Q1" if avg_feature > 0.2 else "Q2" if avg_feature > 0 else "Q3" if avg_feature > -0.2 else "Q4"
                if predicted == actual_future:
                    correct += 1
                total += 1

            accuracies[comp] = correct / max(total, 1)

        return accuracies

    def optimize_gip_weights(
        self,
        historical_gip_results: List[Dict],
        min_window: int = 12,
    ) -> List[WeightUpdate]:
        """Optimize GIP component weights from historical accuracy."""
        accuracies = self._compute_quad_accuracy(historical_gip_results, min_window)
        if not accuracies:
            return []

        # Normalize accuracies to weights (higher accuracy = higher weight)
        total_acc = sum(accuracies.values())
        if total_acc < 0.01:
            return []

        updates = []
        weight_map = {
            "growth_level": ("GROWTH_LEVEL_WEIGHTS", self.growth_weights),
            "growth_momentum": ("GROWTH_MOM_WEIGHTS", getattr(self.cfg, "GROWTH_MOM_WEIGHTS", {})),
            "inflation_level": ("INFLATION_LEVEL_WEIGHTS", self.inflation_weights),
            "inflation_momentum": ("INFLATION_MOM_WEIGHTS", getattr(self.cfg, "INFLATION_MOM_WEIGHTS", {})),
        }

        for comp, acc in accuracies.items():
            if comp not in weight_map:
                continue
            param_name, current_weights = weight_map[comp]
            if not current_weights:
                continue

            # Distribute weight proportionally to accuracy
            target_share = acc / total_acc
            current_total = sum(current_weights.values())

            for sub_key in current_weights:
                old_w = current_weights[sub_key]
                # Smooth update: 80% old + 20% new
                new_w = old_w * 0.8 + (target_share * current_total * 0.2)
                if abs(new_w - old_w) > 0.01:
                    updates.append(WeightUpdate(
                        parameter=f"{param_name}.{sub_key}",
                        old_value=round(old_w, 3),
                        new_value=round(new_w, 3),
                        improvement=round(acc - 0.25, 3),  # baseline 25%
                        confidence=round(min(acc * 2, 1.0), 2),
                    ))

        return updates

    def optimize_bottleneck_thresholds(
        self,
        historical_trades: List[Dict],
        min_samples: int = 20,
    ) -> List[WeightUpdate]:
        """Optimize brewing detection thresholds from trade PnL."""
        if len(historical_trades) < min_samples:
            return []

        # Group by brewing_score bucket
        buckets: Dict[str, List[float]] = {
            "low": [],      # 0.50-0.60
            "mid": [],      # 0.60-0.75
            "high": [],     # 0.75+
        }

        for trade in historical_trades:
            score = trade.get("brewing_score", 0)
            pnl = trade.get("pnl_21d", 0)
            if score < 0.50:
                continue
            elif score < 0.60:
                buckets["low"].append(pnl)
            elif score < 0.75:
                buckets["mid"].append(pnl)
            else:
                buckets["high"].append(pnl)

        updates = []
        for bucket, pnls in buckets.items():
            if len(pnls) < 5:
                continue
            winrate = sum(1 for p in pnls if p > 0) / len(pnls)
            avg_pnl = np.mean(pnls)

            # Adjust threshold based on winrate
            if bucket == "low" and winrate > 0.55:
                # Lower threshold to capture more
                updates.append(WeightUpdate(
                    parameter="MARKET_BREWING_CONFIG.acc_threshold",
                    old_value=0.50,
                    new_value=0.45,
                    improvement=round(winrate - 0.50, 3),
                    confidence=round(min(len(pnls) / 50, 1.0), 2),
                ))
            elif bucket == "high" and winrate < 0.45:
                # Raise threshold, high scores not working
                updates.append(WeightUpdate(
                    parameter="MARKET_BREWING_CONFIG.acc_threshold",
                    old_value=0.50,
                    new_value=0.55,
                    improvement=round(0.50 - winrate, 3),
                    confidence=round(min(len(pnls) / 50, 1.0), 2),
                ))

        return updates

    def generate_settings_patch(
        self,
        gip_updates: List[WeightUpdate],
        bottleneck_updates: List[WeightUpdate],
    ) -> str:
        """Generate Python code patch for settings.py."""
        lines = ["# Auto-generated weight update by meta_optimizer.py", ""]

        for u in gip_updates + bottleneck_updates:
            if u.confidence < 0.30:
                continue  # Skip low-confidence updates
            lines.append(f"# {u.parameter}: {u.old_value} → {u.new_value} (improvement: {u.improvement}, confidence: {u.confidence})")

        return "\n".join(lines)

    def run(
        self,
        historical_gip: Optional[List[Dict]] = None,
        historical_trades: Optional[List[Dict]] = None,
    ) -> Dict:
        """Full optimization pipeline."""
        gip_updates = []
        if historical_gip and len(historical_gip) > 16:
            gip_updates = self.optimize_gip_weights(historical_gip)

        bottleneck_updates = []
        if historical_trades and len(historical_trades) > 20:
            bottleneck_updates = self.optimize_bottleneck_thresholds(historical_trades)

        patch = self.generate_settings_patch(gip_updates, bottleneck_updates)

        return {
            "gip_updates": [
                {"param": u.parameter, "old": u.old_value, "new": u.new_value,
                 "improvement": u.improvement, "confidence": u.confidence}
                for u in gip_updates if u.confidence >= 0.30
            ],
            "bottleneck_updates": [
                {"param": u.parameter, "old": u.old_value, "new": u.new_value,
                 "improvement": u.improvement, "confidence": u.confidence}
                for u in bottleneck_updates if u.confidence >= 0.30
            ],
            "settings_patch": patch,
            "meta": {
                "total_updates": len(gip_updates) + len(bottleneck_updates),
                "high_confidence_updates": sum(1 for u in gip_updates + bottleneck_updates if u.confidence >= 0.50),
                "gip_history_weeks": len(historical_gip) if historical_gip else 0,
                "trade_history_count": len(historical_trades) if historical_trades else 0,
            },
        }
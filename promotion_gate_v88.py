"""Exact-scope V8.8 promotion gate for one market sleeve.

A market can only become limited-production eligible after narrative timing, bottleneck-to-price
calibration, extreme-winner discovery where applicable, real realized performance and independent
approval all pass.  No result transfers across markets.
"""
from __future__ import annotations

from typing import Any
import hashlib
import json
import math

MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
REQUIRED_TRUE = [
    "zero_technical_inputs", "complete_global_trial_ledger", "blind_signal_ids",
    "point_in_time_lineage", "frozen_model_before_holdout", "walk_forward_validation",
    "untouched_lockbox", "global_multiple_testing_correction", "post_cutoff_or_prospective_evidence",
    "calibration_pass", "false_alarm_pass", "remaining_return_lower_bound_positive",
    "actual_costs_borrow_impact_capacity", "realized_performance_gate_pass",
    "narrative_incremental_timing_pass", "market_specific_projection_pass",
    "bottleneck_value_bridge_pass", "projection_calibration_pass", "independent_reviewer_approval",
]
ARTIFACT_ROLES = (
    "trial_ledger", "pit_dataset", "model", "holdout_result", "trade_ledger", "equity_ledger",
    "narrative_timing_benchmark", "projection_spec", "projection_benchmark", "review",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _metric(metrics: dict[str, Any], name: str, reasons: list[str]) -> float | None:
    try:
        value = float(metrics.get(name))
    except (TypeError, ValueError):
        reasons.append(f"metric missing or invalid: {name}")
        return None
    if not math.isfinite(value):
        reasons.append(f"metric non-finite: {name}")
        return None
    return value


def evaluate(receipt: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    scope = receipt.get("scope") or {}
    for key in ("market", "universe", "direction", "horizon", "execution_method"):
        if not str(scope.get(key) or "").strip():
            reasons.append(f"scope missing: {key}")
    market = str(scope.get("market") or "").strip().lower()
    if market not in MARKETS:
        reasons.append("unsupported or missing market")

    gates = receipt.get("gates") or {}
    for gate in REQUIRED_TRUE:
        if gates.get(gate) is not True:
            reasons.append(f"gate failed or missing: {gate}")

    metrics = receipt.get("metrics") or {}
    thresholds = {
        "closed_trades": (200.0, "min"),
        "prospective_months": (24.0, "min"),
        "regime_count": (4.0, "min"),
        "real_net_profit_factor": (1.50, "min"),
        "profit_factor_bootstrap_95pct_lower": (1.20, "min"),
        "normal_max_drawdown": (0.15, "max"),
        "stress_max_drawdown": (0.20, "max"),
        "narrative_timing_ready_50pct_hit_rate_12m": (0.35, "min"),
        "narrative_incremental_hit_rate_vs_dormant": (0.15, "min"),
        "narrative_incremental_bootstrap_lower": (0.0, "strict_min"),
        "narrative_median_days_to_50pct": (180.0, "max"),
        "narrative_median_mae": (0.25, "max"),
        "projection_count": (200.0, "min"),
        "projection_months": (24.0, "min"),
        "projection_regime_count": (4.0, "min"),
        "projection_error_improvement_vs_no_change": (0.10, "min"),
        "projection_interval_coverage": (0.70, "min"),
        "projection_interval_coverage_upper": (0.90, "max"),
        "projection_scenario_brier": (0.20, "max"),
        "projection_direction_accuracy": (0.55, "min"),
        "projection_return_rank_correlation": (0.0, "strict_min"),
        "projection_severe_loss_rate": (0.15, "max"),
    }
    for name, (threshold, mode) in thresholds.items():
        value = _metric(metrics, name, reasons)
        if value is None:
            continue
        if mode == "min" and value < threshold:
            reasons.append(f"metric below threshold: {name}")
        elif mode == "strict_min" and value <= threshold:
            reasons.append(f"metric must be strictly above threshold: {name}")
        elif mode == "max" and value > threshold:
            reasons.append(f"metric above threshold: {name}")

    if market in {"us", "idx", "crypto"}:
        for name, threshold in (
            ("extreme_winner_recall_at_20", 0.25),
            ("extreme_winner_recall_at_50", 0.45),
            ("extreme_winner_precision_at_20", 0.08),
            ("extreme_winner_median_remaining_return", 3.0),
        ):
            value = _metric(metrics, name, reasons)
            if value is not None and value < threshold:
                reasons.append(f"metric below threshold: {name}")
        if metrics.get("mandatory_known_cases_captured") is not True:
            reasons.append("mandatory post-freeze named diagnostics not captured")
    else:
        # Commodity and FX require a market-specific large-move benchmark rather than stock multibaggers.
        for name, threshold in (
            ("large_move_recall_at_20", 0.25),
            ("large_move_precision_at_20", 0.10),
        ):
            value = _metric(metrics, name, reasons)
            if value is not None and value < threshold:
                reasons.append(f"metric below threshold: {name}")

    error_limits = {"us": 0.35, "idx": 0.40, "commodity": 0.22, "fx": 0.12, "crypto": 0.45}
    target_error = _metric(metrics, "projection_median_abs_log_error", reasons)
    if target_error is not None and market in error_limits and target_error > error_limits[market]:
        reasons.append("projection target error above market-specific ceiling")

    artifacts = receipt.get("artifacts") or {}
    for role in ARTIFACT_ROLES:
        digest = str(artifacts.get(role) or "").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            reasons.append(f"artifact hash missing or invalid: {role}")
    if market in {"us", "idx", "crypto"}:
        digest = str(artifacts.get("extreme_winner_benchmark") or "").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            reasons.append("artifact hash missing or invalid: extreme_winner_benchmark")
    else:
        digest = str(artifacts.get("large_move_benchmark") or "").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            reasons.append("artifact hash missing or invalid: large_move_benchmark")

    payload = {
        "schema": "warroom.v88.market_promotion_adjudication.v1",
        "eligible": not reasons,
        "permission": "LIMITED_PRODUCTION_ELIGIBLE" if not reasons else "BLOCKED",
        "scope": scope,
        "reasons": sorted(set(reasons)),
    }
    payload["adjudication_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload

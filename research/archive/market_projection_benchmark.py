"""Blind, point-in-time benchmark for V8.8 market-specific price projections.

The benchmark never constructs signals.  It scores already-frozen projections against outcomes and
compares them with a no-change baseline.  This is intentionally separate from the projection engine
so holdout outcomes can remain hidden until adjudication.
"""
from __future__ import annotations

from typing import Any
import math

import numpy as np
import pandas as pd

REQUIRED = [
    "prediction_id", "market", "instrument_id", "as_of", "horizon_end", "regime",
    "current_price", "target_low", "target_base", "target_high", "expected_target_price",
    "probability_low", "probability_base", "probability_high", "realized_price",
    "point_in_time_valid", "model_frozen_before_outcome", "projection_hash", "outcome_source_hash",
]
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
ERROR_LIMITS = {"us": 0.35, "idx": 0.40, "commodity": 0.22, "fx": 0.12, "crypto": 0.45}


def _to_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _safe_log_error(predicted: pd.Series, realized: pd.Series) -> pd.Series:
    return (np.log(predicted) - np.log(realized)).abs()


def _scenario_brier(row: pd.Series) -> float:
    targets = np.asarray([row.target_low, row.target_base, row.target_high], dtype=float)
    probs = np.asarray([row.probability_low, row.probability_base, row.probability_high], dtype=float)
    actual = int(np.argmin(np.abs(np.log(targets) - math.log(float(row.realized_price)))))
    one_hot = np.zeros(3); one_hot[actual] = 1.0
    return float(np.mean((probs - one_hot) ** 2))


def validate_frame(frame: pd.DataFrame) -> dict[str, Any]:
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        return {"valid": False, "errors": ["missing columns: " + ", ".join(missing)], "rows": len(frame)}
    work = frame.copy()
    errors: list[str] = []
    if work["prediction_id"].astype(str).duplicated().any():
        errors.append("duplicate prediction_id")
    if not work["market"].astype(str).str.lower().isin(MARKETS).all():
        errors.append("unsupported market")
    for column in ("as_of", "horizon_end"):
        work[column] = _to_time(work[column])
        if work[column].isna().any():
            errors.append(f"invalid {column}")
    if not errors and (work["horizon_end"] <= work["as_of"]).any():
        errors.append("horizon_end must be after as_of")
    numeric = [
        "current_price", "target_low", "target_base", "target_high", "expected_target_price",
        "probability_low", "probability_base", "probability_high", "realized_price",
    ]
    for column in numeric:
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            errors.append(f"non-numeric {column}")
    if not errors:
        prices = ["current_price", "target_low", "target_base", "target_high", "expected_target_price", "realized_price"]
        if (work[prices] <= 0).any().any():
            errors.append("prices and targets must be positive")
        if ((work.target_low > work.target_base) | (work.target_base > work.target_high)).any():
            errors.append("targets must be ordered low <= base <= high")
        probability_sum = work[["probability_low", "probability_base", "probability_high"]].sum(axis=1)
        if ((probability_sum - 1.0).abs() > 1e-8).any() or (work[["probability_low", "probability_base", "probability_high"]] < 0).any().any():
            errors.append("invalid scenario probabilities")
    for column in ("point_in_time_valid", "model_frozen_before_outcome"):
        if not work[column].astype(bool).all():
            errors.append(f"{column} must be true for every row")
    for column in ("projection_hash", "outcome_source_hash"):
        if work[column].astype(str).str.fullmatch(r"[0-9a-f]{64}").fillna(False).eq(False).any():
            errors.append(f"invalid {column}")
    return {"valid": not errors, "errors": sorted(set(errors)), "rows": len(work), "work": work if not errors else None}


def _market_metrics(work: pd.DataFrame, market: str) -> dict[str, Any]:
    group = work.loc[work.market.astype(str).str.lower().eq(market)].copy()
    if group.empty:
        return {"market": market, "count": 0, "all_projection_gates_pass": False, "reason": "no outcomes"}
    group["realized_return"] = group.realized_price / group.current_price - 1.0
    group["projected_return"] = group.expected_target_price / group.current_price - 1.0
    group["base_abs_log_error"] = _safe_log_error(group.target_base, group.realized_price)
    group["expected_abs_log_error"] = _safe_log_error(group.expected_target_price, group.realized_price)
    group["no_change_abs_log_error"] = _safe_log_error(group.current_price, group.realized_price)
    group["interval_hit"] = (group.realized_price >= group.target_low) & (group.realized_price <= group.target_high)
    group["direction_hit"] = np.sign(group.projected_return).eq(np.sign(group.realized_return))
    group["brier"] = group.apply(_scenario_brier, axis=1)
    group["month"] = group.horizon_end.dt.strftime("%Y-%m")
    expected_error = float(group.expected_abs_log_error.median())
    baseline_error = float(group.no_change_abs_log_error.median())
    improvement = 1.0 - expected_error / baseline_error if baseline_error > 0 else float("-inf")
    interval_coverage = float(group.interval_hit.mean())
    brier = float(group.brier.mean())
    direction = float(group.direction_hit.mean())
    correlation = float(group[["projected_return", "realized_return"]].corr(method="spearman").iloc[0, 1]) if len(group) >= 3 else float("nan")
    metrics = {
        "market": market,
        "count": int(len(group)),
        "months": int(group.month.nunique()),
        "regimes": int(group.regime.astype(str).nunique()),
        "median_expected_abs_log_error": expected_error,
        "median_base_abs_log_error": float(group.base_abs_log_error.median()),
        "median_no_change_abs_log_error": baseline_error,
        "error_improvement_vs_no_change": improvement,
        "interval_coverage": interval_coverage,
        "scenario_brier": brier,
        "direction_accuracy": direction,
        "spearman_projected_vs_realized_return": correlation,
        "median_realized_return": float(group.realized_return.median()),
        "median_projected_return": float(group.projected_return.median()),
        "severe_loss_rate": float((group.realized_return <= -0.35).mean()),
    }
    gates = {
        "minimum_200_predictions": metrics["count"] >= 200,
        "minimum_24_months": metrics["months"] >= 24,
        "minimum_4_regimes": metrics["regimes"] >= 4,
        "target_error_within_market_limit": expected_error <= ERROR_LIMITS[market],
        "beats_no_change_error_by_10pct": improvement >= 0.10,
        "interval_coverage_between_70_and_90pct": 0.70 <= interval_coverage <= 0.90,
        "scenario_brier_at_most_0_20": brier <= 0.20,
        "direction_accuracy_at_least_55pct": direction >= 0.55,
        "projected_realized_rank_correlation_positive": math.isfinite(correlation) and correlation > 0,
        "severe_loss_rate_at_most_15pct": metrics["severe_loss_rate"] <= 0.15,
    }
    metrics["gates"] = gates
    metrics["all_projection_gates_pass"] = all(gates.values())
    return metrics


def evaluate(frame: pd.DataFrame) -> dict[str, Any]:
    validation = validate_frame(frame)
    if not validation["valid"]:
        return {"schema": "warroom.v88.projection_benchmark.v1", "valid": False, "errors": validation["errors"], "all_markets_pass": False}
    work = validation.pop("work")
    by_market = {market: _market_metrics(work, market) for market in sorted(MARKETS)}
    return {
        "schema": "warroom.v88.projection_benchmark.v1",
        "valid": True,
        "errors": [],
        "rows": len(work),
        "by_market": by_market,
        "all_markets_pass": all(row.get("all_projection_gates_pass") for row in by_market.values()),
        "claim_limit": "This scorecard proves target calibration only for each exact market/universe/horizon represented. It cannot transfer proof across markets.",
    }

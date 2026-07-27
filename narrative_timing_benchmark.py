"""Incremental benchmark for bottleneck discovery versus repricing timing.

This benchmark tests the user's core requirement: finding a real bottleneck is not enough. The
activation state must add measurable timing value over a bottleneck-only baseline on a blind,
point-in-time universe.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

REQUIRED = [
    "as_of", "security_id", "stage", "bottleneck_confirmed", "timing_ready", "rank",
    "future_return_252d", "days_to_50pct_return", "max_adverse_excursion_252d",
    "is_extreme_winner", "outcome_available_at",
]
ALLOWED_STAGES = {
    "STRUCTURAL_DORMANT", "EVIDENCE_BUILDING", "REPRICING_READY_RESEARCH_CANDIDATE",
    "ACTIVATION_WITHOUT_CONSERVATIVE_VALUATION_MARGIN", "RECOGNIZED_OR_LATE",
    "SUPPLY_RESPONSE_CAN_CLOSE_GAP", "NARRATIVE_NOT_FALSIFIED", "INVALIDATED",
}


def _bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def validate(frame: pd.DataFrame) -> dict[str, Any]:
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        return {"valid": False, "errors": ["missing columns: " + ",".join(missing)]}
    w = frame.copy()
    errors: list[str] = []
    w["as_of"] = pd.to_datetime(w["as_of"], utc=True, errors="coerce")
    w["outcome_available_at"] = pd.to_datetime(w["outcome_available_at"], utc=True, errors="coerce")
    if w[["as_of", "outcome_available_at"]].isna().any().any():
        errors.append("invalid timestamps")
    if (w["outcome_available_at"] <= w["as_of"]).any():
        errors.append("outcome must become available after forecast")
    if not w["stage"].astype(str).isin(ALLOWED_STAGES).all():
        errors.append("unknown stage")
    for c in ["rank", "future_return_252d", "days_to_50pct_return", "max_adverse_excursion_252d"]:
        w[c] = pd.to_numeric(w[c], errors="coerce")
        if w[c].isna().any():
            errors.append(f"non-numeric {c}")
    if (w["rank"] <= 0).any():
        errors.append("rank must be positive")
    if w.duplicated(["as_of", "security_id"]).any():
        errors.append("duplicate as_of/security_id")
    return {"valid": not errors, "errors": sorted(set(errors)), "rows": len(w)}


def _bootstrap_delta(ready: np.ndarray, baseline: np.ndarray, *, repetitions: int = 10000, seed: int = 8701) -> dict[str, float]:
    if ready.size == 0 or baseline.size == 0:
        return {"lower_95": float("nan"), "median": float("nan")}
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(repetitions):
        r = rng.choice(ready, size=ready.size, replace=True)
        b = rng.choice(baseline, size=baseline.size, replace=True)
        vals.append(float(np.mean(r) - np.mean(b)))
    a = np.asarray(vals)
    return {"lower_95": float(np.quantile(a, 0.05)), "median": float(np.median(a))}


def score(frame: pd.DataFrame, *, top_k: int = 50) -> dict[str, Any]:
    v = validate(frame)
    if not v["valid"]:
        return {"valid": False, "errors": v["errors"], "all_gates_pass": False}
    w = frame.copy()
    w["bottleneck_confirmed"] = _bool(w["bottleneck_confirmed"])
    w["timing_ready"] = _bool(w["timing_ready"])
    w["is_extreme_winner"] = _bool(w["is_extreme_winner"])
    for c in ["rank", "future_return_252d", "days_to_50pct_return", "max_adverse_excursion_252d"]:
        w[c] = pd.to_numeric(w[c], errors="coerce")

    universe = w[w["rank"] <= top_k]
    baseline = universe[universe["bottleneck_confirmed"]]
    ready = universe[universe["timing_ready"]]
    dormant = baseline[~baseline["timing_ready"]]

    hit_ready = (ready["future_return_252d"] >= 0.50).astype(float).to_numpy()
    hit_dormant = (dormant["future_return_252d"] >= 0.50).astype(float).to_numpy()
    extreme_total = int(universe["is_extreme_winner"].sum())
    extreme_captured = int((ready["is_extreme_winner"]).sum())
    recall = extreme_captured / extreme_total if extreme_total else float("nan")
    precision = float(ready["is_extreme_winner"].mean()) if len(ready) else float("nan")
    delta = _bootstrap_delta(hit_ready, hit_dormant)
    ready_hit_rate = float(np.mean(hit_ready)) if hit_ready.size else float("nan")
    dormant_hit_rate = float(np.mean(hit_dormant)) if hit_dormant.size else float("nan")
    lead = ready.loc[ready["days_to_50pct_return"] >= 0, "days_to_50pct_return"]
    adverse = ready["max_adverse_excursion_252d"].abs()

    metrics = {
        "rows": int(len(w)), "top_k_rows": int(len(universe)),
        "bottleneck_only_rows": int(len(baseline)), "timing_ready_rows": int(len(ready)),
        "dormant_bottleneck_rows": int(len(dormant)),
        "timing_ready_50pct_hit_rate_12m": ready_hit_rate,
        "dormant_bottleneck_50pct_hit_rate_12m": dormant_hit_rate,
        "incremental_hit_rate": ready_hit_rate - dormant_hit_rate if math.isfinite(ready_hit_rate) and math.isfinite(dormant_hit_rate) else float("nan"),
        "incremental_hit_rate_bootstrap": delta,
        "extreme_winner_recall_with_timing_ready": float(recall),
        "extreme_winner_precision_with_timing_ready": float(precision),
        "median_days_to_50pct_return": float(lead.median()) if len(lead) else float("nan"),
        "median_max_adverse_excursion_252d": float(adverse.median()) if len(adverse) else float("nan"),
    }
    gates = {
        "minimum_5000_blind_rows": len(w) >= 5000,
        "minimum_1000_bottleneck_rows": len(baseline) >= 1000,
        "minimum_200_timing_ready_rows": len(ready) >= 200,
        "timing_ready_hit_rate_at_least_35pct": math.isfinite(ready_hit_rate) and ready_hit_rate >= 0.35,
        "incremental_hit_rate_at_least_15pct": math.isfinite(metrics["incremental_hit_rate"]) and metrics["incremental_hit_rate"] >= 0.15,
        "bootstrap_incremental_lower_bound_positive": math.isfinite(delta["lower_95"]) and delta["lower_95"] > 0,
        "extreme_winner_recall_at_least_35pct": math.isfinite(recall) and recall >= 0.35,
        "median_time_to_50pct_at_most_180_days": len(lead) > 0 and float(lead.median()) <= 180,
        "median_adverse_excursion_at_most_25pct": len(adverse) > 0 and float(adverse.median()) <= 0.25,
    }
    return {
        "schema": "warroom.v87.narrative_timing_benchmark.v1",
        "valid": True, "metrics": metrics, "gates": gates,
        "all_gates_pass": all(gates.values()),
        "claim_limit": "Tests whether activation evidence adds timing value over bottleneck discovery alone. It is necessary but not sufficient for capital promotion.",
    }

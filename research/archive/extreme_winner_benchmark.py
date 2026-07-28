"""Extreme-winner acceptance benchmark for War Room OS V8.6.

Market prices are consumed only to construct future outcome labels and measure realized risk.
They are never accepted as predictor features. The benchmark is deliberately split into:

1. known-case diagnostics (for named examples such as SNDK and PLTR), and
2. a complete blind-universe test that prevents success on hand-picked winners from being proof.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from warroom.no_technical_policy import validate_feature_names

PREDICTION_REQUIRED = [
    "forecast_id", "strategy_id", "as_of", "security_id", "ticker", "rank", "score",
    "execution_reference_price", "feature_domains", "feature_snapshot_hash", "model_hash",
    "trial_ledger_hash", "universe_snapshot_hash",
]
OUTCOME_REQUIRED = [
    "as_of", "security_id", "ticker", "horizon_days", "eligible", "future_peak_at",
    "future_peak_price", "execution_reference_price", "max_forward_return",
    "max_adverse_excursion", "is_5x_36m", "is_10x_60m", "is_100x_120m",
    "eligibility_date", "winner_window_fraction_elapsed", "outcome_snapshot_hash",
]
ALLOWED_FEATURE_DOMAINS = {
    "economics", "fundamentals", "expectations", "liquidity", "credit", "valuation",
    "positioning", "signed_flow", "physical_market", "bottleneck", "causal_transmission",
    "corporate_actions", "market_structure", "supply_chain", "customer_qualification",
    "protocol_value_capture", "controller_free_float", "broker_inventory",
}
HEX64 = r"[0-9a-f]{64}"


def _timestamps(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _parse_domains(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return [part.strip().lower() for part in str(value or "").replace("|", ",").split(",") if part.strip()]


def validate_predictions(frame: pd.DataFrame) -> dict[str, Any]:
    missing = [column for column in PREDICTION_REQUIRED if column not in frame.columns]
    if missing:
        return {"valid": False, "errors": [f"missing columns: {', '.join(missing)}"], "rows": len(frame)}
    work = frame.copy()
    errors: list[str] = []
    if work["forecast_id"].astype(str).duplicated().any():
        errors.append("duplicate forecast_id")
    work["as_of"] = _timestamps(work["as_of"])
    if work["as_of"].isna().any():
        errors.append("invalid as_of")
    for column in ("rank", "score", "execution_reference_price"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            errors.append(f"non-numeric {column}")
    if (work["rank"] <= 0).any():
        errors.append("rank must be positive")
    if (work["execution_reference_price"] <= 0).any():
        errors.append("execution_reference_price must be positive")
    for column in ("feature_snapshot_hash", "model_hash", "trial_ledger_hash", "universe_snapshot_hash"):
        if work[column].astype(str).str.fullmatch(HEX64).fillna(False).eq(False).any():
            errors.append(f"invalid {column}")
    domain_violations: list[str] = []
    for idx, value in work["feature_domains"].items():
        domains = _parse_domains(value)
        forbidden = validate_feature_names(domains)
        unknown = sorted(set(domains) - ALLOWED_FEATURE_DOMAINS)
        if not domains:
            domain_violations.append(f"row {idx}: feature domains missing")
        if forbidden:
            domain_violations.append(f"row {idx}: prohibited predictor domain")
        if unknown:
            domain_violations.append(f"row {idx}: unknown domains {','.join(unknown)}")
    errors.extend(domain_violations)
    duplicate_rank = work.duplicated(["strategy_id", "as_of", "rank"])
    if duplicate_rank.any():
        errors.append("duplicate rank within strategy/as_of")
    return {"valid": not errors, "errors": sorted(set(errors)), "rows": len(work)}


def validate_outcomes(frame: pd.DataFrame) -> dict[str, Any]:
    missing = [column for column in OUTCOME_REQUIRED if column not in frame.columns]
    if missing:
        return {"valid": False, "errors": [f"missing columns: {', '.join(missing)}"], "rows": len(frame)}
    work = frame.copy()
    errors: list[str] = []
    for column in ("as_of", "future_peak_at", "eligibility_date"):
        work[column] = _timestamps(work[column])
        if work[column].isna().any():
            errors.append(f"invalid {column}")
    if not errors and (work["future_peak_at"] < work["as_of"]).any():
        errors.append("future_peak_at cannot precede as_of")
    for column in (
        "horizon_days", "future_peak_price", "execution_reference_price", "max_forward_return",
        "max_adverse_excursion", "winner_window_fraction_elapsed",
    ):
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            errors.append(f"non-numeric {column}")
    if (work["horizon_days"] <= 0).any():
        errors.append("horizon_days must be positive")
    if (work[["future_peak_price", "execution_reference_price"]] <= 0).any().any():
        errors.append("prices must be positive")
    if ((work["winner_window_fraction_elapsed"] < 0) | (work["winner_window_fraction_elapsed"] > 1)).any():
        errors.append("winner_window_fraction_elapsed must be within [0,1]")
    for column in ("eligible", "is_5x_36m", "is_10x_60m", "is_100x_120m"):
        normalized = work[column].astype(str).str.lower()
        if not normalized.isin(["true", "false", "1", "0"]).all() and work[column].dtype != bool:
            errors.append(f"invalid boolean {column}")
    if work["outcome_snapshot_hash"].astype(str).str.fullmatch(HEX64).fillna(False).eq(False).any():
        errors.append("invalid outcome_snapshot_hash")
    if work.duplicated(["as_of", "security_id", "horizon_days"]).any():
        errors.append("duplicate as_of/security_id/horizon_days")
    return {"valid": not errors, "errors": sorted(set(errors)), "rows": len(work)}


def _bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1"])


def _bootstrap_metric(values: np.ndarray, *, statistic: str, repetitions: int = 10000, seed: int = 8601) -> dict[str, float]:
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        return {"lower_95": float("nan"), "median": float("nan"), "valid_repetitions": 0}
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(repetitions):
        sample = rng.choice(clean, size=clean.size, replace=True)
        if statistic == "mean":
            stats.append(float(np.mean(sample)))
        elif statistic == "median":
            stats.append(float(np.median(sample)))
        else:
            raise ValueError(f"unsupported statistic: {statistic}")
    arr = np.asarray(stats)
    return {"lower_95": float(np.quantile(arr, 0.05)), "median": float(np.median(arr)), "valid_repetitions": len(arr)}


def score(
    predictions: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    top_k_primary: int = 20,
    top_k_secondary: int = 50,
    known_case_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    pred_validation = validate_predictions(predictions)
    outcome_validation = validate_outcomes(outcomes)
    if not pred_validation["valid"] or not outcome_validation["valid"]:
        return {
            "valid": False,
            "prediction_validation": pred_validation,
            "outcome_validation": outcome_validation,
            "all_extreme_winner_gates_pass": False,
            "errors": pred_validation["errors"] + outcome_validation["errors"],
        }

    pred = predictions.copy()
    out = outcomes.copy()
    pred["as_of"] = _timestamps(pred["as_of"])
    out["as_of"] = _timestamps(out["as_of"])
    out["future_peak_at"] = _timestamps(out["future_peak_at"])
    out["eligible"] = _bool(out["eligible"])
    for column in ("is_5x_36m", "is_10x_60m", "is_100x_120m"):
        out[column] = _bool(out[column])
    for column in ("rank", "execution_reference_price"):
        pred[column] = pd.to_numeric(pred[column], errors="coerce")
    for column in ("max_forward_return", "max_adverse_excursion", "winner_window_fraction_elapsed", "future_peak_price"):
        out[column] = pd.to_numeric(out[column], errors="coerce")

    merged = pred.merge(out, on=["as_of", "security_id", "ticker"], how="left", suffixes=("_pred", "_out"))
    matched = merged["outcome_snapshot_hash"].notna()
    coverage = float(matched.mean()) if len(merged) else 0.0
    eligible = out[out["eligible"]].copy()
    winners_5x = eligible[eligible["is_5x_36m"]]

    top20 = merged[(merged["rank"] <= top_k_primary) & matched]
    top50 = merged[(merged["rank"] <= top_k_secondary) & matched]
    top20_winner = top20["is_5x_36m"].fillna(False).astype(bool)
    top50_winner = top50["is_5x_36m"].fillna(False).astype(bool)

    winner_keys = set(zip(winners_5x["as_of"].astype(str), winners_5x["security_id"].astype(str)))
    captured20_keys = set(zip(top20.loc[top20_winner, "as_of"].astype(str), top20.loc[top20_winner, "security_id"].astype(str)))
    captured50_keys = set(zip(top50.loc[top50_winner, "as_of"].astype(str), top50.loc[top50_winner, "security_id"].astype(str)))
    recall20 = len(winner_keys & captured20_keys) / len(winner_keys) if winner_keys else float("nan")
    recall50 = len(winner_keys & captured50_keys) / len(winner_keys) if winner_keys else float("nan")
    precision20 = float(top20_winner.mean()) if len(top20) else float("nan")

    early_hits = top50[
        top50_winner
        & (top50["winner_window_fraction_elapsed"] <= 0.30)
        & (top50["max_forward_return"] >= 2.0)
    ].copy()
    remaining = early_hits["max_forward_return"].to_numpy(dtype=float)
    adverse = early_hits["max_adverse_excursion"].abs().to_numpy(dtype=float)
    lead_days = (early_hits["future_peak_at"] - early_hits["as_of"]).dt.total_seconds().to_numpy(dtype=float) / 86400.0

    severe_loss_rate = float((top20["max_forward_return"] <= -0.50).mean()) if len(top20) else float("nan")
    known_case_results: dict[str, Any] = {}
    known_case_pass = True
    for label, security_id in (known_case_ids or {}).items():
        rows = early_hits[early_hits["security_id"].astype(str) == str(security_id)]
        passed = not rows.empty
        known_case_results[label] = {
            "security_id": str(security_id),
            "captured_early_top50": passed,
            "best_rank": int(rows["rank"].min()) if passed else None,
            "first_capture_at": rows["as_of"].min().isoformat() if passed else None,
            "remaining_return_at_first_capture": float(rows.sort_values("as_of").iloc[0]["max_forward_return"]) if passed else None,
        }
        known_case_pass = known_case_pass and passed

    metrics = {
        "prediction_outcome_coverage": coverage,
        "eligible_rows": int(len(eligible)),
        "five_x_winner_rows": int(len(winners_5x)),
        "recall_at_20_5x_36m": float(recall20),
        "recall_at_50_5x_36m": float(recall50),
        "precision_at_20_5x_36m": float(precision20),
        "early_hit_count": int(len(early_hits)),
        "median_remaining_return": float(np.median(remaining)) if remaining.size else float("nan"),
        "remaining_return_bootstrap": _bootstrap_metric(remaining, statistic="median"),
        "median_lead_days": float(np.median(lead_days)) if lead_days.size else float("nan"),
        "median_pre_peak_adverse_excursion": float(np.median(adverse)) if adverse.size else float("nan"),
        "severe_false_positive_rate_top20": severe_loss_rate,
        "known_case_results": known_case_results,
    }
    gates = {
        "complete_prediction_outcome_coverage": coverage >= 0.995,
        "minimum_100_blind_5x_winner_rows": len(winners_5x) >= 100,
        "blind_recall_at_20_at_least_25pct": math.isfinite(recall20) and recall20 >= 0.25,
        "blind_recall_at_50_at_least_45pct": math.isfinite(recall50) and recall50 >= 0.45,
        "blind_precision_at_20_at_least_8pct": math.isfinite(precision20) and precision20 >= 0.08,
        "median_remaining_return_at_least_300pct": remaining.size > 0 and float(np.median(remaining)) >= 3.0,
        "bootstrap_median_remaining_return_lower_at_least_150pct": remaining.size > 0 and metrics["remaining_return_bootstrap"]["lower_95"] >= 1.5,
        "median_lead_at_least_180_days": lead_days.size > 0 and float(np.median(lead_days)) >= 180.0,
        "median_pre_peak_adverse_excursion_at_most_25pct": adverse.size > 0 and float(np.median(adverse)) <= 0.25,
        "severe_false_positive_rate_at_most_15pct": math.isfinite(severe_loss_rate) and severe_loss_rate <= 0.15,
        "mandatory_known_cases_captured": known_case_pass and bool(known_case_ids),
    }
    return {
        "schema": "warroom.v86.extreme_winner_score.v1",
        "valid": True,
        "prediction_validation": pred_validation,
        "outcome_validation": outcome_validation,
        "metrics": metrics,
        "gates": gates,
        "all_extreme_winner_gates_pass": all(gates.values()),
        "claim_limit": "Historical winner recall is a mandatory falsification test; it is not sufficient by itself for live capital permission.",
    }

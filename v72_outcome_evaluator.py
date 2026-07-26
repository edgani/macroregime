"""Frozen historical evaluator for V72 signed-dealer options claims.

The evaluator consumes derived, license-permitted research tables. It cannot fetch data, change
feature sets, or authorize a trade. Production evaluation uses the exact dates and 5,000 day-
cluster bootstrap replications frozen in V72_OUTCOME_EVALUATOR_SPEC_FROZEN.json.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "research_v56" / "V72_OUTCOME_EVALUATOR_SPEC_FROZEN.json"
PROTOCOL_PATH = ROOT / "research_v56" / "V72_SPX_SIGNED_DEALER_PROTOCOL_FROZEN.json"

C1_BASE = ["lagged_rv", "intraday_seasonal_rv", "abs_spot_shock", "unsigned_gamma_magnitude", "gross_oi_topology"]
C1_ADD = ["signed_omm_gamma", "signed_omm_gamma_x_abs_spot_shock", "gamma_to_depth"]
C1_OUTCOMES = ["future_rv_5m", "future_rv_15m", "future_rv_30m"]
C2_BASE = ["distance_to_strike", "time_to_expiry_minutes", "expected_move_fraction", "lagged_rv", "unsigned_gamma_concentration"]
C2_ADD = ["signed_gamma_concentration", "signed_gamma_concentration_x_approach_direction", "gamma_to_depth"]
C2_OUTCOME = "pin_event"
C3_REQUIRED = ["trading_dt", "ex_ante_variance_gap", "net_pnl", "simple_baseline_pnl", "double_cost_net_pnl"]
SPLITS = {
    "discovery": (pd.Timestamp("2020-07-01"), pd.Timestamp("2022-06-30")),
    "validation": (pd.Timestamp("2022-07-01"), pd.Timestamp("2023-06-30")),
    "lockbox": (pd.Timestamp("2023-07-01"), pd.Timestamp("2025-06-30")),
}


class V72EvaluationError(ValueError):
    pass


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(df: pd.DataFrame, cols: Sequence[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise V72EvaluationError(f"{label} missing columns: {missing}")


def _prepare(df: pd.DataFrame, cols: Sequence[str], label: str) -> pd.DataFrame:
    _require(df, ["trading_dt", *cols], label)
    out = df[["trading_dt", *cols]].copy()
    out["trading_dt"] = pd.to_datetime(out["trading_dt"], errors="coerce").dt.normalize()
    if out["trading_dt"].isna().any():
        raise V72EvaluationError(f"{label} invalid trading_dt")
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if out[list(cols)].isna().any().any() or not np.isfinite(out[list(cols)].to_numpy(dtype=float)).all():
        raise V72EvaluationError(f"{label} non-finite values")
    return out.sort_values("trading_dt", kind="mergesort").reset_index(drop=True)


def _split(df: pd.DataFrame, name: str) -> pd.DataFrame:
    lo, hi = SPLITS[name]
    return df[(df["trading_dt"] >= lo) & (df["trading_dt"] <= hi)].copy()


@dataclass(frozen=True)
class Standardizer:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "Standardizer":
        mean = np.mean(x, axis=0)
        scale = np.std(x, axis=0, ddof=0)
        if not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale <= 1e-12):
            raise V72EvaluationError("zero-variance or non-finite discovery feature")
        return cls(mean=mean, scale=scale)

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.scale


def _ols_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    return np.linalg.pinv(design, rcond=1e-12) @ y


def _ols_predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ beta


def _daily_score(df: pd.DataFrame, row_score: np.ndarray) -> pd.Series:
    tmp = pd.DataFrame({"trading_dt": df["trading_dt"].to_numpy(), "score": row_score})
    return tmp.groupby("trading_dt", sort=True)["score"].mean()


def _max_stat_lcb(scores: Mapping[str, pd.Series], *, reps: int, seed: int, confidence: float = 0.95) -> dict[str, Any]:
    if not scores:
        raise V72EvaluationError("no score series")
    panel = pd.concat({k: v for k, v in scores.items()}, axis=1).sort_index().fillna(0.0)
    if len(panel) < 2:
        raise V72EvaluationError("too few independent dates")
    arr = panel.to_numpy(dtype=float)
    obs = arr.mean(axis=0)
    rng = np.random.default_rng(seed)
    n = len(arr)
    boot = np.empty((reps, arr.shape[1]), dtype=float)
    for i in range(reps):
        idx = rng.integers(0, n, size=n)
        boot[i] = arr[idx].mean(axis=0)
    # Studentize before taking the max statistic so metrics measured in dollars, Brier points,
    # and variance-loss units share one family-wise confidence gate without scale domination.
    se = np.std(arr, axis=0, ddof=1) / math.sqrt(n)
    if not np.isfinite(se).all() or np.any(se <= 1e-15):
        raise V72EvaluationError("zero or non-finite day-cluster standard error")
    deviations = np.max((obs[None, :] - boot) / se[None, :], axis=1)
    q = float(np.quantile(deviations, confidence))
    lower = obs - q * se
    return {
        "dates": int(n),
        "replications": int(reps),
        "confidence": confidence,
        "studentized_max_stat_quantile": q,
        "standard_error": {k: float(v) for k, v in zip(panel.columns, se)},
        "observed": {k: float(v) for k, v in zip(panel.columns, obs)},
        "simultaneous_lower_bound": {k: float(v) for k, v in zip(panel.columns, lower)},
    }


def evaluate_claim_1(df: pd.DataFrame) -> dict[str, Any]:
    cols = [*C1_BASE, *C1_ADD, *C1_OUTCOMES]
    data = _prepare(df, cols, "V72_C1")
    discovery = _split(data, "discovery")
    if discovery.empty:
        raise V72EvaluationError("V72_C1 discovery split empty")
    base_scaler = Standardizer.fit(discovery[C1_BASE].to_numpy(dtype=float))
    full_scaler = Standardizer.fit(discovery[[*C1_BASE, *C1_ADD]].to_numpy(dtype=float))
    x_base_train = base_scaler.transform(discovery[C1_BASE].to_numpy(dtype=float))
    x_full_train = full_scaler.transform(discovery[[*C1_BASE, *C1_ADD]].to_numpy(dtype=float))
    models: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for outcome in C1_OUTCOMES:
        y = discovery[outcome].to_numpy(dtype=float)
        models[outcome] = (_ols_fit(x_base_train, y), _ols_fit(x_full_train, y))

    split_scores: dict[str, dict[str, pd.Series]] = {}
    summary: dict[str, dict[str, float]] = {}
    for split_name in ("validation", "lockbox"):
        part = _split(data, split_name)
        if part.empty:
            raise V72EvaluationError(f"V72_C1 {split_name} split empty")
        xb = base_scaler.transform(part[C1_BASE].to_numpy(dtype=float))
        xf = full_scaler.transform(part[[*C1_BASE, *C1_ADD]].to_numpy(dtype=float))
        split_scores[split_name] = {}
        summary[split_name] = {}
        for outcome in C1_OUTCOMES:
            y = part[outcome].to_numpy(dtype=float)
            b0, b1 = models[outcome]
            improvement = (y - _ols_predict(b0, xb)) ** 2 - (y - _ols_predict(b1, xf)) ** 2
            key = f"C1_{outcome}"
            split_scores[split_name][key] = _daily_score(part, improvement)
            summary[split_name][key] = float(np.mean(improvement))
    return {
        "claim_id": "V72_C1_VERIFIED_GAMMA_RESPONSE",
        "rows": int(len(data)),
        "independent_dates": int(data["trading_dt"].nunique()),
        "summary": summary,
        "daily_scores": split_scores,
    }


def evaluate_claim_2(df: pd.DataFrame) -> dict[str, Any]:
    cols = [*C2_BASE, *C2_ADD, C2_OUTCOME]
    data = _prepare(df, cols, "V72_C2")
    if not set(data[C2_OUTCOME].unique()).issubset({0.0, 1.0}):
        raise V72EvaluationError("V72_C2 pin_event must be binary")
    discovery = _split(data, "discovery")
    if discovery.empty or discovery[C2_OUTCOME].nunique() != 2:
        raise V72EvaluationError("V72_C2 discovery split lacks both classes")
    base_scaler = Standardizer.fit(discovery[C2_BASE].to_numpy(dtype=float))
    full_scaler = Standardizer.fit(discovery[[*C2_BASE, *C2_ADD]].to_numpy(dtype=float))
    base = LogisticRegression(C=1.0, solver="liblinear", max_iter=2000, random_state=7202)
    full = LogisticRegression(C=1.0, solver="liblinear", max_iter=2000, random_state=7202)
    y_train = discovery[C2_OUTCOME].to_numpy(dtype=int)
    base.fit(base_scaler.transform(discovery[C2_BASE].to_numpy(dtype=float)), y_train)
    full.fit(full_scaler.transform(discovery[[*C2_BASE, *C2_ADD]].to_numpy(dtype=float)), y_train)

    split_scores: dict[str, dict[str, pd.Series]] = {}
    summary: dict[str, dict[str, float]] = {}
    for split_name in ("validation", "lockbox"):
        part = _split(data, split_name)
        if part.empty:
            raise V72EvaluationError(f"V72_C2 {split_name} split empty")
        y = part[C2_OUTCOME].to_numpy(dtype=float)
        pb = base.predict_proba(base_scaler.transform(part[C2_BASE].to_numpy(dtype=float)))[:, 1]
        pf = full.predict_proba(full_scaler.transform(part[[*C2_BASE, *C2_ADD]].to_numpy(dtype=float)))[:, 1]
        improvement = (y - pb) ** 2 - (y - pf) ** 2
        key = "C2_PIN_BREAK_BRIER"
        split_scores[split_name] = {key: _daily_score(part, improvement)}
        summary[split_name] = {key: float(np.mean(improvement))}
    return {
        "claim_id": "V72_C2_INCREMENTAL_PIN_BREAK",
        "rows": int(len(data)),
        "independent_dates": int(data["trading_dt"].nunique()),
        "summary": summary,
        "daily_scores": split_scores,
    }


def evaluate_claim_3(df: pd.DataFrame) -> dict[str, Any]:
    data = _prepare(df, C3_REQUIRED[1:], "V72_C3")
    data["selected"] = data["ex_ante_variance_gap"] > 0.0
    data["selected_net_pnl"] = np.where(data["selected"], data["net_pnl"], 0.0)
    data["selected_double_cost_pnl"] = np.where(data["selected"], data["double_cost_net_pnl"], 0.0)
    data["incremental_pnl"] = data["selected_net_pnl"] - data["simple_baseline_pnl"]
    split_scores: dict[str, dict[str, pd.Series]] = {}
    summary: dict[str, dict[str, float]] = {}
    selected_events: dict[str, int] = {}
    for split_name in ("validation", "lockbox"):
        part = _split(data, split_name)
        if part.empty:
            raise V72EvaluationError(f"V72_C3 {split_name} split empty")
        daily = part.groupby("trading_dt", sort=True).agg(
            primary=("selected_net_pnl", "sum"),
            incremental=("incremental_pnl", "sum"),
            double_cost=("selected_double_cost_pnl", "sum"),
        )
        split_scores[split_name] = {
            "C3_PRIMARY_NET_PNL": daily["primary"],
            "C3_INCREMENTAL_NET_PNL": daily["incremental"],
            "C3_DOUBLE_COST_NET_PNL": daily["double_cost"],
        }
        summary[split_name] = {k: float(v.mean()) for k, v in split_scores[split_name].items()}
        selected_events[split_name] = int(part["selected"].sum())
    return {
        "claim_id": "V72_C3_NET_GAMMA_SCALP",
        "rows": int(len(data)),
        "independent_dates": int(data["trading_dt"].nunique()),
        "selected_events": selected_events,
        "summary": summary,
        "daily_scores": split_scores,
    }



def _mean_lockbox_scores(result: Mapping[str, Any]) -> dict[str, float]:
    return {k: float(v.mean()) for k, v in result["daily_scores"]["lockbox"].items()}


def _joint_permute(df: pd.DataFrame, columns: Sequence[str], rng: np.random.Generator) -> pd.DataFrame:
    out = df.copy()
    idx = rng.permutation(len(out))
    values = out.loc[:, list(columns)].to_numpy(copy=True)[idx]
    out.loc[:, list(columns)] = values
    return out


def _placebo_gate(c1: pd.DataFrame, c2: pd.DataFrame, c3: pd.DataFrame,
                  main_observed: Mapping[str, float], *, fixture_mode: bool) -> dict[str, Any]:
    repetitions = 20 if fixture_mode else 200
    rng = np.random.default_rng(7299)
    draws = {k: [] for k in main_observed}
    for _ in range(repetitions):
        c1p = _joint_permute(c1, C1_ADD, rng)
        c2p = _joint_permute(c2, C2_ADD, rng)
        c3p = c3.copy()
        c3p["ex_ante_variance_gap"] = rng.permutation(c3p["ex_ante_variance_gap"].to_numpy())
        results = (evaluate_claim_1(c1p), evaluate_claim_2(c2p), evaluate_claim_3(c3p))
        scores: dict[str, float] = {}
        for result in results:
            scores.update(_mean_lockbox_scores(result))
        for key in draws:
            draws[key].append(float(scores[key]))
    p_values = {
        key: float((1 + sum(x >= float(main_observed[key]) for x in values)) / (repetitions + 1))
        for key, values in draws.items()
    }
    passed = all(p <= 0.05 for p in p_values.values())
    return {
        "repetitions": repetitions,
        "seed": 7299,
        "null": "joint permutation of verified signed features; ex-ante selector permutation for gamma scalp",
        "p_values": p_values,
        "status": "PASS" if passed else "FAIL",
    }

def evaluate_all(c1: pd.DataFrame, c2: pd.DataFrame, c3: pd.DataFrame, *, fixture_mode: bool = False) -> dict[str, Any]:
    c1r = evaluate_claim_1(c1)
    c2r = evaluate_claim_2(c2)
    c3r = evaluate_claim_3(c3)
    reps = 500 if fixture_mode else 5000
    all_scores: dict[str, dict[str, pd.Series]] = {"validation": {}, "lockbox": {}}
    for result in (c1r, c2r, c3r):
        for split_name in ("validation", "lockbox"):
            all_scores[split_name].update(result["daily_scores"][split_name])
    inference = {
        split_name: _max_stat_lcb(all_scores[split_name], reps=reps, seed=7200 + (0 if split_name == "validation" else 1))
        for split_name in ("validation", "lockbox")
    }
    observed_validation = inference["validation"]["observed"]
    observed_lockbox = inference["lockbox"]["observed"]
    lower_lockbox = inference["lockbox"]["simultaneous_lower_bound"]
    all_positive = all(v > 0 for v in observed_validation.values()) and all(v > 0 for v in observed_lockbox.values())
    simultaneous_positive = all(v > 0 for v in lower_lockbox.values())
    placebo = _placebo_gate(c1, c2, c3, observed_lockbox, fixture_mode=fixture_mode)

    minimums = {
        "V72_C1_VERIFIED_GAMMA_RESPONSE": (250, 1500),
        "V72_C2_INCREMENTAL_PIN_BREAK": (250, 1000),
        "V72_C3_NET_GAMMA_SCALP": (200, 300),
    }
    counts_ok = True
    if not fixture_mode:
        counts_ok = (
            c1r["independent_dates"] >= minimums[c1r["claim_id"]][0] and c1r["rows"] >= minimums[c1r["claim_id"]][1]
            and c2r["independent_dates"] >= minimums[c2r["claim_id"]][0] and c2r["rows"] >= minimums[c2r["claim_id"]][1]
            and c3r["independent_dates"] >= minimums[c3r["claim_id"]][0]
            and c3r["selected_events"].get("validation", 0) + c3r["selected_events"].get("lockbox", 0) >= minimums[c3r["claim_id"]][1]
        )
    historical_gate = all_positive and simultaneous_positive and counts_ok and placebo["status"] == "PASS"
    return {
        "schema": "warroom.v72_historical_evaluation",
        "status": "HISTORICAL_GATE_PASS_REQUIRES_PLACEBO_AND_PROSPECTIVE" if historical_gate else "NOT_PROMOTED",
        "fixture_mode": fixture_mode,
        "protocol_sha256": _hash(PROTOCOL_PATH),
        "evaluator_spec_sha256": _hash(SPEC_PATH),
        "claims": [{k: v for k, v in r.items() if k != "daily_scores"} for r in (c1r, c2r, c3r)],
        "simultaneous_inference": inference,
        "gate_components": {
            "validation_and_lockbox_all_positive": all_positive,
            "simultaneous_lockbox_lower_bounds_all_positive": simultaneous_positive,
            "minimum_counts": counts_ok,
            "placebo_gate": placebo,
            "prospective_gate": "NOT_MATURED",
        },
        "historical_gate_pass": historical_gate,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }

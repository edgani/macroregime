"""War Room OS V9.6 anti-overfitting adjudication.

This module does not discover a profitable rule. It adjudicates a frozen candidate family using an
untouched lockbox and refuses promotion when the full search history, causal lifecycle, chronology,
benchmark, costs, regimes or contamination controls are incomplete.

Implemented controls:
- frozen mapping/candidate/test lifecycle and complete trial accounting;
- purged expanding walk-forward with embargo;
- CSCV-style probability of backtest overfitting (PBO);
- deflated Sharpe probability using the full registered trial count;
- block-bootstrap familywise max-statistic and Holm correction versus a benchmark;
- untouched post-freeze lockbox bootstrap;
- parameter-neighbourhood, regime, stress-cost and P&L-concentration stability;
- no promotion to live capital. This report is only an input to the separate actual-fill gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats

from causal_research_lifecycle_v96 import replay as replay_lifecycle, read_events as read_lifecycle_events

SCHEMA = "warroom.v96.anti_overfit_report.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_COLUMNS = {
    "timestamp", "candidate_id", "net_return", "stress_return", "benchmark_return",
    "regime", "family_id", "parameter_index",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")




def _clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json(v) for v in value]
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value

def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} root must be an object")
    return raw


def _time(value: Any) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize("UTC")
    return parsed.tz_convert("UTC")


def _strict_bool(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if value is False or value == 0:
        return False
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no", ""}:
            return False
    raise ValueError(f"not a strict boolean: {value!r}")


def _load_returns(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError("return matrix missing columns: " + ", ".join(missing))
    work = frame.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    if work["timestamp"].isna().any():
        raise ValueError("invalid timestamps")
    if work.duplicated(["timestamp", "candidate_id"]).any():
        raise ValueError("duplicate timestamp/candidate rows")
    for col in ("net_return", "stress_return", "benchmark_return", "parameter_index"):
        work[col] = pd.to_numeric(work[col], errors="coerce")
        if work[col].isna().any() or not np.isfinite(work[col]).all():
            raise ValueError(f"invalid numeric column: {col}")
    if (work[["net_return", "stress_return", "benchmark_return"]].abs() > 1.0).any().any():
        raise ValueError("period returns outside [-100%, +100%] rejected")
    for col in ("candidate_id", "regime", "family_id"):
        work[col] = work[col].astype(str).str.strip()
        if work[col].eq("").any():
            raise ValueError(f"blank {col}")
    return work.sort_values(["timestamp", "candidate_id"]).reset_index(drop=True)


def _period_sharpe(values: Iterable[float], periods_per_year: int) -> float:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return float("nan")
    sd = float(np.std(x, ddof=1))
    if sd <= 0:
        return math.inf if float(np.mean(x)) > 0 else -math.inf
    return float(np.mean(x) / sd * math.sqrt(periods_per_year))


def _metric(values: pd.Series, periods_per_year: int) -> float:
    return _period_sharpe(values.to_numpy(float), periods_per_year)


def _contiguous_blocks(times: list[pd.Timestamp], n_blocks: int) -> list[set[pd.Timestamp]]:
    parts = np.array_split(np.asarray(times, dtype=object), n_blocks)
    return [set(pd.Timestamp(x) for x in part.tolist()) for part in parts if len(part)]


def _pbo(frame: pd.DataFrame, *, candidates: list[str], periods_per_year: int, blocks: int) -> dict[str, Any]:
    times = sorted(frame["timestamp"].unique())
    blocks = min(blocks, len(times))
    if blocks < 4:
        return {"valid": False, "pbo": None, "combinations": 0, "reason": "fewer than four time blocks"}
    if blocks % 2:
        blocks -= 1
    partitions = _contiguous_blocks([pd.Timestamp(x) for x in times], blocks)
    pivot = frame.pivot(index="timestamp", columns="candidate_id", values="net_return").sort_index()
    pivot = pivot[candidates].dropna(how="any")
    lambdas: list[float] = []
    selected: dict[str, int] = {}
    half = blocks // 2
    for train_indices in itertools.combinations(range(blocks), half):
        train_times = set().union(*(partitions[i] for i in train_indices))
        test_times = set(pivot.index).difference(train_times)
        train = pivot.loc[pivot.index.isin(train_times)]
        test = pivot.loc[pivot.index.isin(test_times)]
        if len(train) < 3 or len(test) < 3:
            continue
        train_scores = {c: _period_sharpe(train[c], periods_per_year) for c in candidates}
        winner = max(candidates, key=lambda c: (-math.inf if not math.isfinite(train_scores[c]) else train_scores[c], c))
        test_scores = pd.Series({c: _period_sharpe(test[c], periods_per_year) for c in candidates})
        ranks = test_scores.rank(method="average", ascending=True)
        omega = float(ranks[winner] / (len(candidates) + 1.0))
        omega = min(max(omega, 1e-9), 1 - 1e-9)
        lambdas.append(math.log(omega / (1.0 - omega)))
        selected[winner] = selected.get(winner, 0) + 1
    if not lambdas:
        return {"valid": False, "pbo": None, "combinations": 0, "reason": "no valid CSCV combinations"}
    return {
        "valid": True,
        "pbo": float(np.mean(np.asarray(lambdas) < 0.0)),
        "median_logit_oos_rank": float(np.median(lambdas)),
        "combinations": len(lambdas),
        "winner_counts": selected,
    }


def _expected_max_normal(n_trials: int) -> float:
    if n_trials <= 1:
        return 0.0
    gamma = 0.5772156649015329
    a = stats.norm.ppf(1.0 - 1.0 / n_trials)
    b = stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float((1.0 - gamma) * a + gamma * b)


def _deflated_sharpe(values: pd.Series, *, periods_per_year: int, n_trials: int) -> dict[str, Any]:
    x = values.to_numpy(float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"valid": False, "probability": None, "reason": "insufficient observations"}
    mean = float(np.mean(x)); sd = float(np.std(x, ddof=1))
    if sd <= 0:
        return {"valid": False, "probability": None, "reason": "zero variance"}
    sr_period = mean / sd
    skew = float(stats.skew(x, bias=False)) if n > 3 else 0.0
    kurt = float(stats.kurtosis(x, fisher=False, bias=False)) if n > 4 else 3.0
    sr_star = _expected_max_normal(max(1, n_trials)) / math.sqrt(max(n - 1, 1))
    denominator_term = 1.0 - skew * sr_period + ((kurt - 1.0) / 4.0) * (sr_period ** 2)
    if denominator_term <= 0:
        return {"valid": False, "probability": None, "reason": "invalid non-normal variance adjustment"}
    z = (sr_period - sr_star) * math.sqrt(n - 1) / math.sqrt(denominator_term)
    return {
        "valid": True,
        "observations": n,
        "annualized_sharpe": float(sr_period * math.sqrt(periods_per_year)),
        "expected_max_trial_sharpe_threshold_annualized": float(sr_star * math.sqrt(periods_per_year)),
        "skew": skew,
        "kurtosis": kurt,
        "z": float(z),
        "probability": float(stats.norm.cdf(z)),
        "trial_count": int(n_trials),
    }


def _moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.asarray([], dtype=int)
    block = max(1, min(block, n))
    starts = rng.integers(0, n, size=math.ceil(n / block))
    pieces = [np.arange(start, start + block) % n for start in starts]
    return np.concatenate(pieces)[:n]


def _bootstrap_mean_pvalue(values: np.ndarray, *, block: int, repetitions: int, seed: int) -> dict[str, Any]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return {"valid": False, "pvalue": None, "lower_95": None, "reason": "insufficient observations"}
    observed = float(np.mean(x))
    centered = x - observed
    rng = np.random.default_rng(seed)
    null_means = np.empty(repetitions)
    sampled_means = np.empty(repetitions)
    for i in range(repetitions):
        idx = _moving_block_indices(len(x), block, rng)
        null_means[i] = float(np.mean(centered[idx]))
        sampled_means[i] = float(np.mean(x[idx]))
    return {
        "valid": True,
        "observed_mean": observed,
        "pvalue": float((1 + np.sum(null_means >= observed)) / (repetitions + 1)),
        "lower_95": float(np.quantile(sampled_means, 0.025)),
        "repetitions": repetitions,
        "block": block,
    }


def _familywise_max_stat(frame: pd.DataFrame, candidates: list[str], *, block: int, repetitions: int, seed: int) -> dict[str, Any]:
    pivot = frame.pivot(index="timestamp", columns="candidate_id", values="net_return").sort_index()[candidates]
    bench = frame.drop_duplicates("timestamp").set_index("timestamp")["benchmark_return"].reindex(pivot.index)
    diff = pivot.sub(bench, axis=0).dropna(how="any")
    if len(diff) < 5:
        return {"valid": False, "familywise_pvalue": None, "reason": "insufficient aligned observations"}
    x = diff.to_numpy(float)
    means = np.mean(x, axis=0)
    std = np.std(x, axis=0, ddof=1)
    std = np.where(std > 0, std, np.nan)
    observed_t = means / (std / math.sqrt(len(x)))
    observed_max = float(np.nanmax(observed_t))
    centered = x - means
    rng = np.random.default_rng(seed)
    boot_max = np.empty(repetitions)
    for i in range(repetitions):
        idx = _moving_block_indices(len(x), block, rng)
        sample = centered[idx]
        sample_mean = np.mean(sample, axis=0)
        sample_std = np.std(sample, axis=0, ddof=1)
        t = sample_mean / np.where(sample_std > 0, sample_std / math.sqrt(len(sample)), np.nan)
        boot_max[i] = float(np.nanmax(t))
    pvalue = float((1 + np.sum(boot_max >= observed_max)) / (repetitions + 1))
    raw_p: dict[str, float] = {}
    for i, candidate in enumerate(candidates):
        t = observed_t[i]
        raw_p[candidate] = float(1.0 - stats.t.cdf(t, df=max(len(x) - 1, 1))) if np.isfinite(t) else 1.0
    holm = _holm_adjust(raw_p)
    return {
        "valid": True,
        "observations": len(x),
        "observed_max_t": observed_max,
        "familywise_pvalue": pvalue,
        "raw_one_sided_pvalues": raw_p,
        "holm_adjusted_pvalues": holm,
        "repetitions": repetitions,
        "block": block,
    }


def _holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (key, p) in enumerate(items):
        value = min(1.0, (m - rank) * float(p))
        running = max(running, value)
        adjusted[key] = running
    return adjusted


def _purged_walk_forward(frame: pd.DataFrame, *, candidate: str, periods_per_year: int, folds: int, purge: int, embargo: int) -> dict[str, Any]:
    candidate_frame = frame[frame["candidate_id"] == candidate].sort_values("timestamp").copy()
    times = candidate_frame["timestamp"].drop_duplicates().tolist()
    if len(times) < folds * 3:
        return {"valid": False, "folds": 0, "reason": "insufficient observations for walk-forward"}
    test_parts = [list(x) for x in np.array_split(np.asarray(times, dtype=object), folds + 1)[1:] if len(x)]
    results: list[dict[str, Any]] = []
    all_times = list(times)
    for test in test_parts:
        test_start = all_times.index(test[0]); test_end = all_times.index(test[-1])
        train_end = max(0, test_start - purge)
        train_times = all_times[:train_end]
        if embargo:
            # Embargo is applied after each test window; in expanding walk-forward it protects later folds.
            embargo_end = min(len(all_times), test_end + 1 + embargo)
        else:
            embargo_end = test_end + 1
        test_frame = candidate_frame[candidate_frame["timestamp"].isin(test)]
        diff = test_frame["net_return"] - test_frame["benchmark_return"]
        stress_diff = test_frame["stress_return"] - test_frame["benchmark_return"]
        results.append({
            "test_start": pd.Timestamp(test[0]).isoformat(),
            "test_end": pd.Timestamp(test[-1]).isoformat(),
            "train_observations": len(train_times),
            "test_observations": len(test_frame),
            "mean_excess": float(diff.mean()),
            "stress_mean_excess": float(stress_diff.mean()),
            "sharpe": _period_sharpe(diff, periods_per_year),
            "embargo_until_index": embargo_end,
        })
    valid = [x for x in results if x["test_observations"] >= 2]
    return {
        "valid": bool(valid),
        "folds": len(valid),
        "positive_fraction": float(np.mean([x["mean_excess"] > 0 for x in valid])) if valid else 0.0,
        "stress_positive_fraction": float(np.mean([x["stress_mean_excess"] > 0 for x in valid])) if valid else 0.0,
        "median_excess": float(np.median([x["mean_excess"] for x in valid])) if valid else None,
        "worst_excess": float(np.min([x["mean_excess"] for x in valid])) if valid else None,
        "results": valid,
        "purge_periods": purge,
        "embargo_periods": embargo,
    }


def _regime_stability(frame: pd.DataFrame, candidate: str, *, minimum_observations: int) -> dict[str, Any]:
    work = frame[frame["candidate_id"] == candidate].copy()
    rows: list[dict[str, Any]] = []
    for regime, group in work.groupby("regime"):
        diff = group["net_return"] - group["benchmark_return"]
        stress = group["stress_return"] - group["benchmark_return"]
        rows.append({
            "regime": str(regime), "observations": len(group),
            "mean_excess": float(diff.mean()), "stress_mean_excess": float(stress.mean()),
        })
    eligible = [x for x in rows if x["observations"] >= minimum_observations]
    return {
        "regimes": len(eligible),
        "positive_regimes": sum(x["mean_excess"] > 0 for x in eligible),
        "stress_positive_regimes": sum(x["stress_mean_excess"] > 0 for x in eligible),
        "worst_mean_excess": min((x["mean_excess"] for x in eligible), default=None),
        "rows": rows,
    }


def _concentration(frame: pd.DataFrame, candidate: str) -> dict[str, Any]:
    work = frame[frame["candidate_id"] == candidate]
    diff = (work["net_return"] - work["benchmark_return"]).to_numpy(float)
    positive = np.sort(diff[diff > 0])[::-1]
    gross = float(positive.sum())
    if gross <= 0:
        return {"single": math.inf, "top5": math.inf, "gross_positive": gross}
    return {
        "single": float(positive[:1].sum() / gross),
        "top5": float(positive[:5].sum() / gross),
        "gross_positive": gross,
    }


def _neighbourhood(frame: pd.DataFrame, candidate: str) -> dict[str, Any]:
    selected = frame[frame["candidate_id"] == candidate]
    if selected.empty:
        return {"valid": False, "reason": "selected candidate absent"}
    family = str(selected["family_id"].iloc[0])
    selected_param = float(selected["parameter_index"].iloc[0])
    family_frame = frame[frame["family_id"] == family]
    summary = family_frame.groupby("candidate_id").agg(
        parameter_index=("parameter_index", "first"),
        mean_net=("net_return", "mean"),
        mean_stress=("stress_return", "mean"),
        benchmark=("benchmark_return", "mean"),
    ).reset_index()
    summary["mean_excess"] = summary["mean_net"] - summary["benchmark"]
    summary["stress_excess"] = summary["mean_stress"] - summary["benchmark"]
    summary["distance"] = (summary["parameter_index"] - selected_param).abs()
    neighbours = summary[summary["candidate_id"] != candidate].sort_values("distance").head(2)
    selected_excess = float(summary.loc[summary["candidate_id"] == candidate, "mean_excess"].iloc[0])
    positive_neighbours = int((neighbours["mean_excess"] > 0).sum())
    stress_positive_neighbours = int((neighbours["stress_excess"] > 0).sum())
    median_neighbour = float(neighbours["mean_excess"].median()) if len(neighbours) else float("nan")
    spike_ratio = selected_excess / median_neighbour if median_neighbour > 0 else math.inf
    return {
        "valid": len(neighbours) >= 2,
        "family_id": family,
        "selected_parameter_index": selected_param,
        "selected_mean_excess": selected_excess,
        "neighbours": neighbours.to_dict(orient="records"),
        "positive_neighbours": positive_neighbours,
        "stress_positive_neighbours": stress_positive_neighbours,
        "spike_ratio": float(spike_ratio),
    }


def _seal_check(seal: dict[str, Any], *, lifecycle_hash: str, protocol_hash: str, lockbox_start: pd.Timestamp, candidate: str, market: str, candidate_count: int) -> list[str]:
    errors: list[str] = []
    if seal.get("schema") != "warroom.v96.anti_overfit_seal.v1":
        errors.append("seal schema mismatch")
    recorded = str(seal.get("seal_hash") or "").lower()
    body = {k: v for k, v in seal.items() if k != "seal_hash"}
    if recorded != hashlib.sha256(_canonical(body)).hexdigest():
        errors.append("seal self-hash mismatch")
    for field in ("model_hash", "code_snapshot_hash", "data_contract_hash"):
        if not HEX64.fullmatch(str(seal.get(field) or "")):
            errors.append(f"invalid seal hash: {field}")
    if str(seal.get("lifecycle_hash") or "").lower() != lifecycle_hash:
        errors.append("seal lifecycle hash mismatch")
    if str(seal.get("protocol_hash") or "").lower() != protocol_hash:
        errors.append("seal protocol hash mismatch")
    if str(seal.get("selected_candidate_id") or "") != candidate:
        errors.append("selected candidate not frozen in seal")
    if str(seal.get("market") or "").lower() != market:
        errors.append("seal market mismatch")
    try:
        if int(seal.get("global_trial_count")) != candidate_count:
            errors.append("seal global trial count mismatch")
    except Exception:
        errors.append("invalid seal global trial count")
    try:
        sealed_at = _time(seal.get("sealed_at"))
        if sealed_at >= lockbox_start:
            errors.append("seal was not created before lockbox")
    except Exception:
        errors.append("invalid seal timestamp")
    return errors


def evaluate(*, returns_path: Path, lifecycle_path: Path, protocol_path: Path, seal_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        frame = _load_returns(returns_path)
        lifecycle = replay_lifecycle(lifecycle_path)
        protocol = _json(protocol_path)
        seal = _json(seal_path)
    except Exception as exc:
        result = {
            "schema": SCHEMA, "market": None, "selected_candidate_id": None,
            "historical_blind_proven": False, "capital_permission": "BLOCKED",
            "errors": [f"input admission failed: {type(exc).__name__}: {exc}"],
        }
        result["report_hash"] = hashlib.sha256(_canonical(result)).hexdigest()
        return result

    if protocol.get("schema") != "warroom.v96.anti_overfit_protocol.v1":
        errors.append("protocol schema mismatch")
    if not lifecycle.get("valid"):
        errors.append("causal lifecycle invalid")
    market = str(protocol.get("market") or "").lower()
    if market not in {"us", "idx", "commodity", "fx", "crypto"}:
        errors.append("invalid market")
    selected = str(seal.get("selected_candidate_id") or "")
    candidates = sorted(frame["candidate_id"].unique().tolist())
    registered = []
    for program in (lifecycle.get("research") or {}).values():
        if str(program.get("market")) == market:
            registered.extend(program.get("candidates", {}).keys())
    registered = sorted(set(registered))
    if candidates != registered:
        errors.append("return matrix does not contain the complete registered candidate family")
    if selected not in candidates:
        errors.append("sealed selected candidate absent from return matrix")

    try:
        discovery_end = _time(protocol["periods"]["discovery_end"])
        validation_end = _time(protocol["periods"]["validation_end"])
        lockbox_end = _time(protocol["periods"]["lockbox_end"])
        if not discovery_end < validation_end < lockbox_end:
            raise ValueError("period order invalid")
        validation_start = discovery_end + pd.Timedelta(nanoseconds=1)
        lockbox_start = validation_end + pd.Timedelta(nanoseconds=1)
    except Exception as exc:
        errors.append(f"invalid period contract: {exc}")
        discovery_end = validation_end = lockbox_end = pd.Timestamp("1970-01-01", tz="UTC")
        validation_start = lockbox_start = discovery_end

    discovery = frame[frame["timestamp"] <= discovery_end]
    validation = frame[(frame["timestamp"] >= validation_start) & (frame["timestamp"] <= validation_end)]
    lockbox = frame[(frame["timestamp"] >= lockbox_start) & (frame["timestamp"] <= lockbox_end)]
    if discovery.empty or validation.empty or lockbox.empty:
        errors.append("discovery, validation and lockbox must all be non-empty")
    if frame["timestamp"].max() > lockbox_end:
        errors.append("return matrix contains outcomes beyond frozen lockbox end")

    protocol_hash = _sha(protocol_path); lifecycle_hash = _sha(lifecycle_path)
    errors.extend(_seal_check(
        seal, lifecycle_hash=lifecycle_hash, protocol_hash=protocol_hash,
        lockbox_start=lockbox_start, candidate=selected, market=market, candidate_count=len(registered),
    ))
    try:
        sealed_at_for_lifecycle = _time(seal.get("sealed_at"))
        lifecycle_times = [_time(row.get("registered_at")) for row in read_lifecycle_events(lifecycle_path)]
        if lifecycle_times and max(lifecycle_times) > sealed_at_for_lifecycle:
            errors.append("lifecycle contains events registered after anti-overfit seal")
        if lifecycle_times and max(lifecycle_times) >= lockbox_start:
            errors.append("lifecycle was not fully frozen before lockbox")
    except Exception as exc:
        errors.append(f"lifecycle chronology check failed: {type(exc).__name__}: {exc}")

    periods_per_year = int(protocol.get("periods_per_year") or 12)
    thresholds = protocol.get("thresholds") or {}
    bootstrap_repetitions = int(protocol.get("bootstrap_repetitions") or 2000)
    bootstrap_block = int(protocol.get("bootstrap_block_periods") or max(1, periods_per_year // 4))

    selection_metrics: dict[str, float] = {}
    if not validation.empty:
        for candidate in candidates:
            group = validation[validation["candidate_id"] == candidate]
            selection_metrics[candidate] = _metric(group["net_return"] - group["benchmark_return"], periods_per_year)
        if selection_metrics:
            validation_winner = max(selection_metrics, key=lambda c: (-math.inf if not math.isfinite(selection_metrics[c]) else selection_metrics[c], c))
            if selected != validation_winner:
                errors.append("sealed candidate was not the frozen validation winner")
    else:
        validation_winner = None

    family = pd.concat([discovery, validation], ignore_index=True)
    pbo = _pbo(family, candidates=candidates, periods_per_year=periods_per_year, blocks=int(protocol.get("pbo_blocks") or 8)) if candidates else {"valid": False}
    selected_validation = validation[validation["candidate_id"] == selected]
    selected_validation_diff = selected_validation["net_return"] - selected_validation["benchmark_return"]
    dsr = _deflated_sharpe(selected_validation_diff, periods_per_year=periods_per_year, n_trials=max(1, len(registered)))
    familywise = _familywise_max_stat(validation, candidates, block=bootstrap_block, repetitions=bootstrap_repetitions, seed=9601) if candidates else {"valid": False}
    walk_forward = _purged_walk_forward(
        family, candidate=selected, periods_per_year=periods_per_year,
        folds=int(protocol.get("walk_forward_folds") or 5), purge=int(protocol.get("purge_periods") or 1),
        embargo=int(protocol.get("embargo_periods") or 1),
    )
    selected_lockbox = lockbox[lockbox["candidate_id"] == selected]
    lockbox_diff = (selected_lockbox["net_return"] - selected_lockbox["benchmark_return"]).to_numpy(float)
    lockbox_bootstrap = _bootstrap_mean_pvalue(lockbox_diff, block=bootstrap_block, repetitions=bootstrap_repetitions, seed=9602)
    regime = _regime_stability(lockbox, selected, minimum_observations=int(protocol.get("minimum_observations_per_regime") or 4))
    concentration = _concentration(lockbox, selected)
    neighbourhood = _neighbourhood(validation, selected)

    lockbox_periods = int(selected_lockbox["timestamp"].nunique())
    selected_stress_mean = float((selected_lockbox["stress_return"] - selected_lockbox["benchmark_return"]).mean()) if not selected_lockbox.empty else float("nan")
    contamination = protocol.get("contamination_controls") or {}
    try:
        model_cutoff = _time(contamination.get("model_knowledge_cutoff"))
        post_cutoff_verified = lockbox_start > model_cutoff
    except Exception:
        post_cutoff_verified = False

    gates = {
        "causal_lifecycle_complete": bool(lifecycle.get("valid")) and len(registered) == len(candidates) and len(candidates) >= 3,
        "seal_precedes_lockbox": not any("seal" in e for e in errors),
        "selected_is_validation_winner": validation_winner == selected,
        "pbo_valid_and_at_most_limit": bool(pbo.get("valid")) and float(pbo.get("pbo", 1.0)) <= float(thresholds.get("pbo_max", 0.20)),
        "deflated_sharpe_probability": bool(dsr.get("valid")) and float(dsr.get("probability", 0.0)) >= float(thresholds.get("dsr_probability_min", 0.95)),
        "familywise_bootstrap": bool(familywise.get("valid")) and float(familywise.get("familywise_pvalue", 1.0)) <= float(thresholds.get("familywise_pvalue_max", 0.05)),
        "holm_selected": bool(familywise.get("valid")) and float((familywise.get("holm_adjusted_pvalues") or {}).get(selected, 1.0)) <= float(thresholds.get("holm_pvalue_max", 0.05)),
        "walk_forward_stable": bool(walk_forward.get("valid")) and int(walk_forward.get("folds", 0)) >= int(thresholds.get("walk_forward_min_folds", 4)) and float(walk_forward.get("positive_fraction", 0.0)) >= float(thresholds.get("walk_forward_positive_fraction_min", 0.70)) and float(walk_forward.get("stress_positive_fraction", 0.0)) >= float(thresholds.get("walk_forward_stress_positive_fraction_min", 0.60)),
        "untouched_lockbox_positive": bool(lockbox_bootstrap.get("valid")) and lockbox_periods >= int(thresholds.get("lockbox_min_periods", 12)) and float(lockbox_bootstrap.get("pvalue", 1.0)) <= float(thresholds.get("lockbox_pvalue_max", 0.05)) and float(lockbox_bootstrap.get("lower_95", -1.0)) > 0.0,
        "stress_cost_positive": math.isfinite(selected_stress_mean) and selected_stress_mean > float(thresholds.get("stress_mean_excess_min", 0.0)),
        "regime_consistency": int(regime.get("regimes", 0)) >= int(thresholds.get("minimum_regimes", 4)) and int(regime.get("positive_regimes", 0)) >= int(thresholds.get("minimum_positive_regimes", 3)) and int(regime.get("stress_positive_regimes", 0)) >= int(thresholds.get("minimum_stress_positive_regimes", 3)),
        "parameter_neighbourhood": bool(neighbourhood.get("valid")) and int(neighbourhood.get("positive_neighbours", 0)) >= 2 and int(neighbourhood.get("stress_positive_neighbours", 0)) >= 1 and float(neighbourhood.get("spike_ratio", math.inf)) <= float(thresholds.get("parameter_spike_ratio_max", 3.0)),
        "pnl_not_concentrated": float(concentration.get("single", math.inf)) <= float(thresholds.get("single_period_profit_concentration_max", 0.20)) and float(concentration.get("top5", math.inf)) <= float(thresholds.get("top5_period_profit_concentration_max", 0.55)),
        "global_trial_accounting_complete": _strict_bool(contamination.get("global_trial_accounting_complete", False)),
        "independent_custodian": _strict_bool(contamination.get("independent_data_custodian", False)),
        "post_model_cutoff_lockbox": post_cutoff_verified and _strict_bool(contamination.get("post_model_cutoff_holdout", False)),
        "low_contamination_holdout": _strict_bool(contamination.get("low_contamination_asset_holdout", False)),
    }
    statistical_gate_names = [
        "causal_lifecycle_complete", "seal_precedes_lockbox", "selected_is_validation_winner",
        "pbo_valid_and_at_most_limit", "deflated_sharpe_probability", "familywise_bootstrap",
        "holm_selected", "walk_forward_stable", "untouched_lockbox_positive", "stress_cost_positive",
        "regime_consistency", "parameter_neighbourhood", "pnl_not_concentrated",
    ]
    statistical_pass = all(gates[x] for x in statistical_gate_names)
    confirmatory_pass = statistical_pass and all(gates.values()) and not errors

    result = {
        "schema": SCHEMA,
        "release": "War Room OS V9.6 Causal Anti-Overfit Research Factory",
        "market": market or None,
        "selected_candidate_id": selected or None,
        "candidate_count": len(candidates),
        "registered_trial_count": len(registered),
        "periods": {
            "discovery_end": discovery_end.isoformat(),
            "validation_end": validation_end.isoformat(),
            "lockbox_start": lockbox_start.isoformat(),
            "lockbox_end": lockbox_end.isoformat(),
            "lockbox_periods": lockbox_periods,
        },
        "selection_metrics": selection_metrics,
        "validation_winner": validation_winner,
        "pbo": pbo,
        "deflated_sharpe": dsr,
        "familywise_bootstrap": familywise,
        "purged_walk_forward": walk_forward,
        "lockbox_bootstrap": lockbox_bootstrap,
        "regime_stability": regime,
        "parameter_neighbourhood": neighbourhood,
        "pnl_concentration": concentration,
        "stress_lockbox_mean_excess": selected_stress_mean,
        "contamination_controls": {**contamination, "post_cutoff_verified_from_dates": post_cutoff_verified},
        "gates": gates,
        "historical_statistical_pass": statistical_pass,
        "historical_blind_proven": confirmatory_pass,
        "capital_permission": "BLOCKED_PENDING_ACTUAL_FILL_PROOF",
        "errors": sorted(set(errors)),
        "artifact_hashes": {
            "returns": _sha(returns_path), "lifecycle": lifecycle_hash,
            "protocol": protocol_hash, "seal": _sha(seal_path),
        },
        "claim_limit": "Passing this report proves only a frozen historical exact-scope candidate. It cannot authorize capital without the separate prospective actual-fill, cost, capacity and drawdown proof run.",
    }
    result = _clean_json(result)
    result["report_hash"] = hashlib.sha256(_canonical(result)).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room OS V9.6 anti-overfit gate")
    parser.add_argument("--returns", required=True)
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--seal", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = evaluate(
        returns_path=Path(args.returns), lifecycle_path=Path(args.lifecycle),
        protocol_path=Path(args.protocol), seal_path=Path(args.seal),
    )
    Path(args.out).write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["historical_blind_proven"] else 2)


if __name__ == "__main__":
    main()

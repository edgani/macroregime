"""Fail-closed loader and derived proof objects for legacy Crashmeter v3 research."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_COMPONENTS = ("a1", "a2", "b1", "b2", "c")
_SCORE_COLUMNS = (
    "date",
    "t10y3m",
    "hy_oas",
    "cape",
    *_COMPONENTS,
    "score",
)
_CURVE_COLUMNS = ("date", "T10Y3M")
_HY_COLUMNS = ("date", "BAMLH0A0HYM2")
_SPX_COLUMNS = ("date", "SP500")
_EPISODE_COLUMNS = (
    "episode",
    "peak_date",
    "trough_date",
    "recovery_date",
    "drawdown_pct",
    "peak_to_trough_days",
    "recovery_days",
)
_FALSE_ALARM_KEYS = {"cluster_start", "worst_forward_12m_pct", "real_20pct_crash"}
_DATE_ONLY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_CLAIM_EPISODES = {
    "dotcom_2000": ("Dotcom 2000", pd.Timestamp("1999-01-01")),
    "gfc_2008": ("GFC 2008", pd.Timestamp("2006-01-01")),
    "covid_2020": ("COVID 2020", pd.Timestamp("2019-06-01")),
}


@dataclass(frozen=True)
class CrashmeterEvidence:
    """Validated frozen data plus reproducible derivatives and replication status."""

    score_frame: pd.DataFrame
    outcome_frame: pd.DataFrame
    risk_windows: pd.DataFrame
    claim_ledger: pd.DataFrame
    false_alarm_ledger: pd.DataFrame
    source_validation: pd.DataFrame
    checksums: dict[str, str]
    validation_issues: tuple[str, ...]
    claims_replicable: bool
    replication_verdict: str


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_numeric_csv(path: Path, expected_columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if list(frame.columns) != list(expected_columns):
        raise ValueError(
            f"{path.name} columns must exactly match: {', '.join(expected_columns)}"
        )
    if frame.empty:
        raise ValueError(f"{path.name} must contain at least one observation")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if frame["date"].isna().any() or not frame["date"].is_monotonic_increasing:
        raise ValueError(f"{path.name} dates must be valid and increasing")
    if not frame["date"].is_unique:
        raise ValueError(f"{path.name} dates must be unique")
    numeric_columns = [column for column in expected_columns if column != "date"]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(frame[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError(f"{path.name} contains non-finite values")
    return frame


def _load_episode_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if list(frame.columns) != list(_EPISODE_COLUMNS):
        raise ValueError(
            f"{path.name} columns must exactly match: {', '.join(_EPISODE_COLUMNS)}"
        )
    if frame.empty or not frame["episode"].is_unique:
        raise ValueError("Crisis episode identifiers must be present and unique")
    for column in ("peak_date", "trough_date", "recovery_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    numeric_columns = (
        "episode",
        "drawdown_pct",
        "peak_to_trough_days",
        "recovery_days",
    )
    frame[list(numeric_columns)] = frame[list(numeric_columns)].apply(
        pd.to_numeric, errors="raise"
    )
    if not np.isfinite(frame[list(numeric_columns)].to_numpy(dtype=float)).all():
        raise ValueError("Crisis episode artifact contains non-finite values")
    chronology_valid = (
        frame["peak_date"].le(frame["trough_date"])
        & frame["trough_date"].le(frame["recovery_date"])
    )
    if not chronology_valid.all() or not frame["drawdown_pct"].lt(0).all():
        raise ValueError("Crisis episode dates or drawdowns are invalid")
    return frame


def _validate_score_frame(frame: pd.DataFrame) -> None:
    for component in _COMPONENTS:
        if not frame[component].isin((0, 1)).all():
            raise ValueError(f"Crashmeter component {component} must be binary")
    expected_score = frame[list(_COMPONENTS)].sum(axis=1)
    if not expected_score.equals(frame["score"]):
        raise ValueError("Crashmeter score does not equal the component sum")


def _derive_outcomes(score_frame: pd.DataFrame, spx_frame: pd.DataFrame) -> pd.DataFrame:
    spx = spx_frame.rename(columns={"SP500": "spx"}).copy()
    if not spx["spx"].gt(0.0).all():
        raise ValueError("SP500 values must be positive")
    spx["drawdown_pct"] = (spx["spx"] / spx["spx"].cummax() - 1.0) * 100.0
    overlap = spx.loc[
        spx["date"].between(score_frame["date"].min(), score_frame["date"].max())
    ]
    outcomes = pd.merge_asof(
        overlap.sort_values("date"),
        score_frame[["date", "score"]].sort_values("date"),
        on="date",
        direction="backward",
    ).dropna(subset=["score"])
    outcomes["score"] = outcomes["score"].astype(int)
    return outcomes.reset_index(drop=True)


def _derive_risk_windows(score_frame: pd.DataFrame) -> pd.DataFrame:
    active = score_frame.loc[score_frame["score"].ge(2), ["date", "score"]].copy()
    if active.empty:
        return pd.DataFrame(columns=["start", "end", "max_score", "observations"])
    dates = [pd.Timestamp(value) for value in active["date"].tolist()]
    window_ids = [0]
    for previous, current in pairwise(dates):
        window_ids.append(window_ids[-1] + int((current - previous).days > 7))
    active["window"] = window_ids
    return (
        active.groupby("window", as_index=False)
        .agg(
            start=("date", "min"),
            end=("date", "max"),
            max_score=("score", "max"),
            observations=("score", "size"),
        )
        .drop(columns="window")
    )


def _compare_source_series(
    score_frame: pd.DataFrame,
    source_frame: pd.DataFrame,
    *,
    score_column: str,
    source_column: str,
    source_name: str,
) -> tuple[dict[str, object], list[str]]:
    merged = score_frame[["date", score_column]].merge(
        source_frame[["date", source_column]], on="date", how="left"
    )
    covered = merged[source_column].notna()
    mismatches = covered & ~np.isclose(
        merged[score_column].to_numpy(dtype=float),
        merged[source_column].fillna(0).to_numpy(dtype=float),
        atol=0.005,
        rtol=0.0,
    )
    uncovered_count = int((~covered).sum())
    mismatch_count = int(mismatches.sum())
    status = "PASS" if uncovered_count == 0 and mismatch_count == 0 else "FAIL"
    issues: list[str] = []
    if uncovered_count:
        issues.append(f"{source_name.upper()}_UNVERIFIED_DAILY_ROWS:{uncovered_count}")
    if mismatch_count:
        issues.append(f"{source_name.upper()}_VALUE_MISMATCHES:{mismatch_count}")
    return (
        {
            "source": source_name,
            "status": status,
            "daily_rows": len(score_frame),
            "exact_date_matches": int(covered.sum()),
            "unverified_daily_rows": uncovered_count,
            "value_mismatches": mismatch_count,
            "rule": "Exact-date values must match within 0.005; no fill is assumed.",
        },
        issues,
    )


def _metadata_value_matches(actual: object, expected: object) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return bool(np.isclose(float(actual), float(expected), atol=1e-9, rtol=0.0))
    return actual == expected


def _date_only(value: object, field: str) -> pd.Timestamp:
    if type(value) is not str or _DATE_ONLY_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a YYYY-MM-DD string")
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"{field} must be a real calendar date")
    return parsed


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite JSON number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be a finite JSON number")
    return float(value)


def _validate_snapshot_metadata(
    name: str, snapshot: object, latest: pd.Series
) -> None:
    if not isinstance(snapshot, dict) or set(snapshot) != set(_SCORE_COLUMNS):
        raise ValueError(f"Validation {name} must exactly match the score snapshot schema")
    _date_only(snapshot["date"], f"Validation {name}.date")
    for field in ("t10y3m", "hy_oas", "cape"):
        _finite_number(snapshot[field], f"Validation {name}.{field}")
    for field in (*_COMPONENTS, "score"):
        if type(snapshot[field]) is not int:
            raise ValueError(f"Validation {name}.{field} must be an integer")
    for component in _COMPONENTS:
        if snapshot[component] not in {0, 1}:
            raise ValueError(f"Validation {name}.{component} must be binary")
    if not 0 <= snapshot["score"] <= len(_COMPONENTS):
        raise ValueError(f"Validation {name}.score is outside the component range")
    actual = latest.to_dict()
    actual["date"] = pd.Timestamp(actual["date"]).strftime("%Y-%m-%d")
    for field in _SCORE_COLUMNS:
        if not _metadata_value_matches(actual[field], snapshot[field]):
            raise ValueError(f"Validation {name}.{field} does not match the score series")


def _validate_claim_metadata(validation: dict[str, Any]) -> None:
    claims = validation.get("claims")
    if not isinstance(claims, dict) or set(claims) != set(_CLAIM_EPISODES):
        raise ValueError("Validation claims must exactly match the expected episode identifiers")
    for claim_id, claim in claims.items():
        if not isinstance(claim, dict) or set(claim) != {"first_score_ge3"}:
            raise ValueError(f"Validation claim {claim_id} has an invalid schema")
        trigger = claim["first_score_ge3"]
        if trigger is not None:
            _date_only(trigger, f"Validation claim {claim_id}.first_score_ge3")


def _derive_false_alarm_ledger(
    validation: dict[str, Any], spx_frame: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    raw_records = validation.get("false_alarm_check")
    if not isinstance(raw_records, list):
        raise ValueError("Validation false_alarm_check must be a list")
    rows: list[dict[str, object]] = []
    issues: list[str] = []
    outcome_end = pd.Timestamp(spx_frame["date"].max())
    for index, record in enumerate(raw_records):
        if not isinstance(record, dict) or set(record) != _FALSE_ALARM_KEYS:
            raise ValueError(f"False-alarm record {index} has an invalid schema")
        cluster_start = _date_only(
            record["cluster_start"], f"False-alarm record {index}.cluster_start"
        )
        reported_worst = _finite_number(
            record["worst_forward_12m_pct"],
            f"False-alarm record {index}.worst_forward_12m_pct",
        )
        if type(record["real_20pct_crash"]) is not bool:
            raise ValueError(
                f"False-alarm record {index}.real_20pct_crash must be a boolean"
            )
        required_end = cluster_start + pd.DateOffset(months=12)
        window = spx_frame.loc[
            spx_frame["date"].between(cluster_start, min(required_end, outcome_end))
        ]
        if window.empty:
            raise ValueError(f"False-alarm record {index} has no SPX outcome observations")
        baseline = float(window.iloc[0]["SP500"])
        actual_worst = float((window["SP500"].min() / baseline - 1.0) * 100.0)
        actual_crash = actual_worst <= -20.0
        mature = outcome_end >= required_end
        status = "VALIDATED"
        if not mature:
            status = "PENDING_FORWARD_WINDOW"
            issues.append(f"FORWARD_WINDOW_INCOMPLETE:{cluster_start.date().isoformat()}")
        elif not np.isclose(
            actual_worst,
            reported_worst,
            atol=0.2,
            rtol=0.0,
        ) or actual_crash != bool(record["real_20pct_crash"]):
            status = "FAIL"
            issues.append(f"FALSE_ALARM_OUTCOME_MISMATCH:{cluster_start.date().isoformat()}")
        rows.append(
            {
                "cluster_start": cluster_start,
                "required_end": required_end,
                "available_outcome_end": outcome_end,
                "reported_worst_forward_12m_pct": reported_worst,
                "derived_worst_available_pct": round(actual_worst, 2),
                "status": status,
            }
        )
    return pd.DataFrame(rows), issues


def _validate_validation_metadata(
    validation: dict[str, Any], score_frame: pd.DataFrame, spx_frame: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    required_keys = {"claims", "false_alarm_check", "current", "score_rows", "latest"}
    if set(validation) != required_keys:
        raise ValueError("Crashmeter validation keys must exactly match the expected schema")
    if type(validation["score_rows"]) is not int:
        raise ValueError("Validation score_rows must be an integer")
    if validation["score_rows"] != len(score_frame):
        raise ValueError("Validation score_rows does not match the score series")
    latest = score_frame.iloc[-1]
    _validate_snapshot_metadata("current", validation["current"], latest)
    _validate_snapshot_metadata("latest", validation["latest"], latest)
    _validate_claim_metadata(validation)
    return _derive_false_alarm_ledger(validation, spx_frame)


def _derive_claim_ledger(
    score_frame: pd.DataFrame,
    spx_frame: pd.DataFrame,
    validation: dict[str, Any],
    source_consistent: bool,
) -> tuple[pd.DataFrame, bool]:
    earliest_score = pd.Timestamp(score_frame["date"].min())
    earliest_spx = pd.Timestamp(spx_frame["date"].min())
    historical_coverage = bool(
        earliest_score <= pd.Timestamp("1999-01-01")
        and earliest_spx <= pd.Timestamp("1999-01-01")
    )
    claims_replicable = historical_coverage and source_consistent
    claims = validation["claims"]
    rows: list[dict[str, object]] = []
    for claim_id, (episode, required_start) in _CLAIM_EPISODES.items():
        covered = earliest_score <= required_start and earliest_spx <= required_start
        rows.append(
            {
                "episode": episode,
                "required_start": required_start,
                "available_score_start": earliest_score,
                "available_spx_start": earliest_spx,
                "reported_trigger": claims[claim_id]["first_score_ge3"],
                "status": "REPRODUCIBLE" if covered and source_consistent else "UNREPLICABLE",
                "reason": (
                    "Source history and consistency checks cover the episode"
                    if covered and source_consistent
                    else "Source history begins after the episode and/or consistency checks fail"
                ),
            }
        )
    return pd.DataFrame(rows), claims_replicable


def load_crashmeter_evidence(data_dir: Path) -> CrashmeterEvidence:
    """Load frozen artifacts and fail closed on malformed or inconsistent evidence."""

    paths = {
        "score": data_dir / "crashmeter_v3_daily.csv",
        "validation": data_dir / "crashmeter_v3_validation.json",
        "yield_curve": data_dir / "T10Y3M.csv",
        "hy_oas": data_dir / "BAMLH0A0HYM2.csv",
        "spx": data_dir / "SP500.csv",
        "episodes": data_dir / "crisis_episodes.csv",
    }
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Crashmeter research artifacts: {', '.join(missing)}")

    score_frame = _load_numeric_csv(paths["score"], _SCORE_COLUMNS)
    _validate_score_frame(score_frame)
    curve_frame = _load_numeric_csv(paths["yield_curve"], _CURVE_COLUMNS)
    hy_frame = _load_numeric_csv(paths["hy_oas"], _HY_COLUMNS)
    spx_frame = _load_numeric_csv(paths["spx"], _SPX_COLUMNS)
    episodes = _load_episode_csv(paths["episodes"])
    def reject_nonfinite_json(value: str) -> None:
        raise ValueError(f"Non-finite JSON constant is forbidden: {value}")

    validation_raw = json.loads(
        paths["validation"].read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite_json,
    )
    if not isinstance(validation_raw, dict):
        raise ValueError("Crashmeter validation artifact must be an object")

    source_rows: list[dict[str, object]] = []
    issues: list[str] = []
    for source_frame, score_column, source_column, source_name in (
        (curve_frame, "t10y3m", "T10Y3M", "yield_curve"),
        (hy_frame, "hy_oas", "BAMLH0A0HYM2", "hy_oas"),
    ):
        row, row_issues = _compare_source_series(
            score_frame,
            source_frame,
            score_column=score_column,
            source_column=source_column,
            source_name=source_name,
        )
        source_rows.append(row)
        issues.extend(row_issues)
    source_rows.extend(
        (
            {
                "source": "cape",
                "status": "FAIL",
                "daily_rows": len(score_frame),
                "exact_date_matches": 0,
                "unverified_daily_rows": len(score_frame),
                "value_mismatches": 0,
                "rule": "No raw CAPE source series is stored; no reconstruction is permitted.",
            },
            {
                "source": "crisis_episodes",
                "status": "PASS",
                "daily_rows": len(episodes),
                "exact_date_matches": len(episodes),
                "unverified_daily_rows": 0,
                "value_mismatches": 0,
                "rule": "Schema, finite values, and peak/trough/recovery chronology validated.",
            },
        )
    )
    issues.append("CAPE_SOURCE_UNAVAILABLE")

    false_alarm_ledger, validation_issues = _validate_validation_metadata(
        validation_raw, score_frame, spx_frame
    )
    issues.extend(validation_issues)
    source_validation = pd.DataFrame(source_rows)
    source_consistent = bool(source_validation["status"].eq("PASS").all())
    outcome_frame = _derive_outcomes(score_frame, spx_frame)
    risk_windows = _derive_risk_windows(score_frame)
    claim_ledger, claims_replicable = _derive_claim_ledger(
        score_frame,
        spx_frame,
        validation_raw,
        source_consistent,
    )
    checksums = {name: _checksum(path) for name, path in paths.items()}
    if not source_consistent or validation_issues:
        verdict = "BLOCKED_SOURCE_DATA_INCONSISTENT"
    elif claims_replicable:
        verdict = "REPRODUCIBLE_FOR_STORED_EPISODES"
    else:
        verdict = "BLOCKED_MISSING_HISTORICAL_SOURCE_COVERAGE"
    return CrashmeterEvidence(
        score_frame=score_frame,
        outcome_frame=outcome_frame,
        risk_windows=risk_windows,
        claim_ledger=claim_ledger,
        false_alarm_ledger=false_alarm_ledger,
        source_validation=source_validation,
        checksums=checksums,
        validation_issues=tuple(issues),
        claims_replicable=claims_replicable,
        replication_verdict=verdict,
    )

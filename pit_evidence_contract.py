"""Canonical point-in-time evidence validation for V8.5."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "market", "security_id", "observation_at", "available_at", "source_id",
    "source_record_id", "field_id", "value", "unit", "revision_id", "ingested_at",
]


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def validate_frame(frame: pd.DataFrame, *, decision_at: str | pd.Timestamp | None = None) -> dict[str, Any]:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    errors: list[str] = []
    if missing:
        return {"valid": False, "rows": len(frame), "errors": [f"missing columns: {', '.join(missing)}"]}
    work = frame.copy()
    for column in ("observation_at", "available_at", "ingested_at"):
        work[column] = _utc(work[column])
        if work[column].isna().any():
            errors.append(f"invalid timestamp in {column}")
    if not errors:
        if (work["available_at"] < work["observation_at"]).any():
            errors.append("available_at precedes observation_at")
        if (work["ingested_at"] < work["available_at"]).any():
            errors.append("ingested_at precedes available_at")
        if decision_at is not None:
            decision = pd.Timestamp(decision_at)
            if decision.tzinfo is None:
                decision = decision.tz_localize("UTC")
            else:
                decision = decision.tz_convert("UTC")
            if (work["available_at"] > decision).any():
                errors.append("future information relative to decision_at")
    key = ["market", "security_id", "source_id", "source_record_id", "field_id", "revision_id"]
    if work.duplicated(key, keep=False).any():
        errors.append("duplicate point-in-time source record")
    if work[["market", "security_id", "source_id", "source_record_id", "field_id"]].astype(str).apply(lambda s: s.str.strip().eq("")).any().any():
        errors.append("blank identity field")
    numeric = pd.to_numeric(work["value"], errors="coerce")
    if numeric.isna().any():
        errors.append("non-numeric value")
    return {
        "valid": not errors,
        "rows": len(work),
        "markets": sorted(work["market"].astype(str).unique().tolist()),
        "securities": int(work["security_id"].astype(str).nunique()),
        "fields": int(work["field_id"].astype(str).nunique()),
        "errors": errors,
    }


def validate_file(path: str | Path, *, decision_at: str | None = None) -> dict[str, Any]:
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        frame = pd.read_parquet(p)
    elif p.suffix.lower() == ".csv":
        frame = pd.read_csv(p)
    else:
        raise ValueError("Only CSV and Parquet evidence files are supported")
    result = validate_frame(frame, decision_at=decision_at)
    result.update({"path": str(p), "sha256": file_sha256(p)})
    return result

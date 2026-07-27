"""Strict sealed outcome admission for V9.5."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_COLUMNS = {"forecast_id", "horizon_end", "realized_return", "max_adverse_excursion", "max_favorable_excursion"}
ROLE_BY_MARKET = {
    "us": {"outcome_prices", "delisting_outcomes"},
    "idx": {"outcome_prices", "delisting_outcomes"},
    "commodity": {"outcome_prices"},
    "fx": {"outcome_prices"},
    "crypto": {"outcome_prices"},
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(); root = root.resolve()
    if path != root and root not in path.parents:
        raise ValueError("path escapes manifest root")
    return path


def admit(manifest_path: str | Path, *, predictor_manifest_hash: str, forecast_seal_hash: str) -> dict[str, Any]:
    path = Path(manifest_path).resolve(); errors: list[str] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema": "warroom.v95.outcome_admission.v1", "valid": False, "errors": [f"manifest load failed: {type(exc).__name__}: {exc}"]}
    market = str(manifest.get("market") or "").lower()
    required = ROLE_BY_MARKET.get(market, set())
    if market not in ROLE_BY_MARKET:
        errors.append("unsupported market")
    if manifest.get("schema") != "warroom.v95.outcome_manifest.v1":
        errors.append("invalid outcome manifest schema")
    recorded_manifest_hash = str(manifest.get("manifest_hash") or "").lower()
    unhashed = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    actual_manifest_hash = hashlib.sha256(json.dumps(unhashed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if recorded_manifest_hash != actual_manifest_hash:
        errors.append("outcome manifest self-hash mismatch")
    if str(manifest.get("predictor_manifest_hash") or "").lower() != predictor_manifest_hash.lower():
        errors.append("predictor manifest mismatch")
    if str(manifest.get("forecast_seal_hash") or "").lower() != forecast_seal_hash.lower():
        errors.append("forecast seal mismatch")
    if not HEX64.fullmatch(str(manifest.get("custodian_hash") or "").lower()) or str(manifest.get("custodian_hash")).lower() == "0" * 64:
        errors.append("invalid custodian_hash")
    roles = manifest.get("roles") if isinstance(manifest.get("roles"), Mapping) else {}
    missing = sorted(required - set(roles))
    if missing:
        errors.append("missing outcome roles: " + ",".join(missing))
    audits: dict[str, Any] = {}; forecast_sets: list[set[str]] = []
    for role in sorted(required & set(roles)):
        try:
            spec = roles[role]; file = _resolve(path.parent, str(spec.get("path") or ""))
            expected = str(spec.get("sha256") or "").lower()
            if not file.is_file() or _sha(file) != expected:
                raise ValueError("file/hash mismatch")
            frame = pd.read_csv(file) if file.suffix.lower() == ".csv" else pd.read_parquet(file)
            missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
            if missing_columns:
                raise ValueError("missing columns: " + ",".join(missing_columns))
            if frame["forecast_id"].astype(str).duplicated().any():
                raise ValueError("duplicate forecast_id")
            horizon = pd.to_datetime(frame["horizon_end"], utc=True, errors="coerce")
            if horizon.isna().any():
                raise ValueError("invalid horizon_end")
            for column in ("realized_return", "max_adverse_excursion", "max_favorable_excursion"):
                if pd.to_numeric(frame[column], errors="coerce").isna().any():
                    raise ValueError(f"invalid {column}")
            ids = set(frame["forecast_id"].astype(str)); forecast_sets.append(ids)
            audits[role] = {"valid": True, "rows": len(frame), "sha256": expected, "forecast_ids": len(ids)}
        except Exception as exc:
            errors.append(f"{role}: {type(exc).__name__}: {exc}")
            audits[role] = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
    if len(forecast_sets) > 1 and any(s != forecast_sets[0] for s in forecast_sets[1:]):
        errors.append("outcome role forecast_id sets disagree")
    payload = {
        "schema": "warroom.v95.outcome_admission.v1",
        "valid": not errors,
        "market": market or None,
        "roles": audits,
        "forecast_ids": sorted(forecast_sets[0]) if forecast_sets else [],
        "errors": sorted(set(errors)),
    }
    payload["admission_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload

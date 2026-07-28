"""Separate, sealed outcome admission for V9.1."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re

import pandas as pd

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REGISTRY_PATH = Path(__file__).with_name("V90_SOURCE_ROUTE_REGISTRY.json")
OUTCOME_COLUMNS = {"forecast_id", "horizon_end", "realized_return", "max_adverse_excursion", "max_favorable_excursion"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    root = root.resolve()
    if path != root and root not in path.parents:
        raise ValueError("path escapes manifest root")
    return path


def admit(manifest_path: str | Path, *, predictor_manifest_hash: str, forecast_seal_hash: str) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    errors: list[str] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema": "warroom.v91.outcome_admission.v1", "valid": False, "errors": [f"manifest load failed: {type(exc).__name__}: {exc}"]}
    market = str(manifest.get("market") or "").lower()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if market not in registry["markets"]:
        errors.append("unsupported market")
        required = []
    else:
        required = list(registry["markets"][market]["outcome_roles"])
    if manifest.get("schema") != "warroom.v91.outcome_manifest.v1":
        errors.append("invalid outcome manifest schema")
    if str(manifest.get("forecast_seal_hash") or "").lower() != str(forecast_seal_hash).lower():
        errors.append("forecast seal mismatch")
    if not HEX64.fullmatch(str(manifest.get("custodian_hash") or "").lower()):
        errors.append("invalid custodian_hash")
    if not HEX64.fullmatch(str(predictor_manifest_hash).lower()):
        errors.append("invalid predictor_manifest_hash")
    roles = manifest.get("roles") if isinstance(manifest.get("roles"), Mapping) else {}
    missing = sorted(set(required) - set(roles))
    if missing:
        errors.append("missing outcome roles: " + ",".join(missing))
    role_audits = {}
    for role in sorted(set(required) & set(roles)):
        spec = roles[role]
        try:
            table_path = _resolve(path.parent, str(spec.get("path") or ""))
            expected = str(spec.get("sha256") or "").lower()
            if not table_path.exists() or _sha(table_path) != expected:
                raise ValueError("file/hash mismatch")
            frame = pd.read_csv(table_path) if table_path.suffix.lower() == ".csv" else pd.read_parquet(table_path)
            missing_cols = sorted(OUTCOME_COLUMNS - set(frame.columns))
            if missing_cols:
                raise ValueError("missing columns: " + ",".join(missing_cols))
            if frame["forecast_id"].astype(str).duplicated().any():
                raise ValueError("duplicate forecast_id")
            role_audits[role] = {"valid": True, "rows": len(frame), "sha256": expected}
        except Exception as exc:
            errors.append(f"{role}: {type(exc).__name__}: {exc}")
            role_audits[role] = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
    payload = {
        "schema": "warroom.v91.outcome_admission.v1",
        "valid": not errors,
        "market": market,
        "predictor_manifest_hash": predictor_manifest_hash,
        "forecast_seal_hash": forecast_seal_hash,
        "roles": role_audits,
        "errors": sorted(set(errors)),
        "claim_limit": "Outcome admission only proves sealed outcome identity. It does not prove model quality.",
    }
    payload["admission_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload

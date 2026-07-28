"""Forecast-local, market-scoped data admission for War Room OS V9.1.

This repairs four structural contradictions in V9.0:
1. outcomes are no longer required in a predictor manifest;
2. optional add-ons no longer block a core model;
3. a decision-times file replaces one impossible global decision_time;
4. evidence paths are portable, relative and clean-extract verifiable.

Admission proves data identity and point-in-time usability, not alpha.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re

import pandas as pd

from warroom.no_technical_policy import validate_feature_names

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
COMMON_COLUMNS = {
    "record_id", "instrument_id", "observation_at", "available_at", "source_id",
    "source_record_id", "field_id", "value", "unit", "revision_id",
}
DECISION_COLUMNS = {"forecast_id", "instrument_id", "decision_time", "model_hash"}
FORBIDDEN_PREDICTOR_ROLES = {"outcome_prices", "outcomes", "realized_returns", "future_returns", "delisting_outcomes"}
FORBIDDEN_FIELD_FRAGMENTS = ("realized_return", "forward_return", "future_return", "future_price", "outcome_price", "future_drawdown", "future_peak")
RECEIPT_FIELDS = (
    "universe_snapshot_hash", "security_master_hash", "global_trial_ledger_hash",
    "data_dictionary_hash", "data_custodian_receipt_hash", "source_license_receipt_hash",
    "code_snapshot_hash", "model_hash",
)

REGISTRY_PATH = Path(__file__).with_name("V90_SOURCE_ROUTE_REGISTRY.json")


@dataclass(frozen=True)
class RoleAudit:
    role: str
    valid: bool
    path: str | None
    rows: int
    instruments: int
    min_observation_at: str | None
    max_available_at: str | None
    forecast_coverage: float
    sha256: str | None
    errors: tuple[str, ...]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    raise ValueError(f"unsupported evidence format: {suffix}")


def _resolve_relative(root: Path, relative: str) -> Path:
    if not relative:
        raise ValueError("path missing")
    candidate = (root / relative).resolve()
    root = root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path escapes manifest root")
    return candidate


def _registry(market: str) -> tuple[list[str], list[str], list[str]]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    spec = payload["markets"][market]
    return list(spec["core_roles"]), list(spec["optional_addons"]), list(spec["outcome_roles"])


def _forecast_coverage(frame: pd.DataFrame, decisions: pd.DataFrame) -> float:
    if frame.empty or decisions.empty:
        return 0.0
    available = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
    valid = frame.loc[available.notna(), ["instrument_id"]].copy()
    valid["available_at"] = available[available.notna()]
    valid["instrument_id"] = valid["instrument_id"].astype(str)
    direct_groups = {key: values.sort_values().to_numpy() for key, values in valid.groupby("instrument_id")["available_at"]}
    global_times = direct_groups.get("GLOBAL")
    covered = 0
    for row in decisions.itertuples(index=False):
        inst = str(row.instrument_id)
        decision = row.decision_time
        candidates = direct_groups.get(inst)
        ok = bool(candidates is not None and len(candidates) and candidates.searchsorted(decision, side="right") > 0)
        if not ok and global_times is not None and len(global_times):
            ok = bool(global_times.searchsorted(decision, side="right") > 0)
        covered += int(ok)
    return covered / len(decisions)


def _audit_role(role: str, spec: Mapping[str, Any], root: Path, decisions: pd.DataFrame) -> RoleAudit:
    errors: list[str] = []
    relative = str(spec.get("path") or "").strip()
    expected_hash = str(spec.get("sha256") or "").lower()
    path: Path | None = None
    try:
        path = _resolve_relative(root, relative)
    except Exception as exc:
        errors.append(str(exc))
    if not HEX64.fullmatch(expected_hash) or expected_hash == "0" * 64:
        errors.append("invalid sha256")
    if path is None or not path.exists() or not path.is_file():
        errors.append("file missing")
        return RoleAudit(role, False, str(path) if path else None, 0, 0, None, None, 0.0, expected_hash or None, tuple(sorted(set(errors))))
    actual_hash = _sha256(path)
    if actual_hash != expected_hash:
        errors.append("sha256 mismatch")
    try:
        frame = _load_table(path)
    except Exception as exc:
        errors.append(f"load failed: {type(exc).__name__}: {exc}")
        return RoleAudit(role, False, str(path), 0, 0, None, None, 0.0, actual_hash, tuple(sorted(set(errors))))
    missing = sorted(COMMON_COLUMNS - set(frame.columns))
    if missing:
        errors.append("missing columns: " + ",".join(missing))
    rows = len(frame)
    instruments = int(frame["instrument_id"].astype(str).nunique()) if "instrument_id" in frame else 0
    min_observation = None
    max_available = None
    coverage = 0.0
    if rows <= 0:
        errors.append("empty evidence table")
    if not missing and rows:
        observed = pd.to_datetime(frame["observation_at"], utc=True, errors="coerce")
        available = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
        if observed.isna().any():
            errors.append("invalid observation_at")
        if available.isna().any():
            errors.append("invalid available_at")
        if (available < observed).fillna(False).any():
            errors.append("available_at precedes observation_at")
        if not observed.isna().all():
            min_observation = observed.min().isoformat()
        if not available.isna().all():
            max_available = available.max().isoformat()
        duplicate_cols = ["source_id", "source_record_id", "field_id", "available_at", "instrument_id"]
        if frame.duplicated(duplicate_cols).any():
            errors.append("duplicate point-in-time source record")
        numeric = pd.to_numeric(frame["value"], errors="coerce")
        if numeric.isna().all():
            errors.append("value column contains no numeric evidence")
        fields = frame["field_id"].astype(str).str.lower()
        if any(fields.str.contains(fragment, regex=False).any() for fragment in FORBIDDEN_FIELD_FRAGMENTS):
            errors.append("outcome/future field prohibited in predictor evidence")
        if "feature_domain" in frame.columns:
            domains = [str(x).strip().lower() for x in frame["feature_domain"].dropna().unique()]
            violations = validate_feature_names(domains)
            if violations:
                errors.append("technical predictor domain prohibited: " + "|".join(violations))
        if "synthetic" in frame.columns and frame["synthetic"].astype(bool).any():
            errors.append("synthetic evidence prohibited")
        if "test_fixture" in frame.columns and frame["test_fixture"].astype(bool).any():
            errors.append("test fixture prohibited")
        coverage = _forecast_coverage(frame, decisions)
        minimum_coverage = float(spec.get("minimum_forecast_coverage", 0.80))
        if coverage < minimum_coverage:
            errors.append(f"forecast coverage below minimum: {coverage:.4f} < {minimum_coverage:.4f}")
    minimum_rows = int(spec.get("minimum_rows") or 1)
    if rows < minimum_rows:
        errors.append(f"rows below manifest minimum: {rows} < {minimum_rows}")
    return RoleAudit(role, not errors, str(path), rows, instruments, min_observation, max_available, float(coverage), actual_hash, tuple(sorted(set(errors))))


def admit_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema": "warroom.v91.data_admission.v1", "valid": False, "errors": [f"manifest load failed: {type(exc).__name__}: {exc}"], "market": None}
    errors: list[str] = []
    market = str(manifest.get("market") or "").lower()
    if market not in MARKETS:
        errors.append("unsupported market")
        core_roles: list[str] = []
        optional_roles: list[str] = []
        outcome_roles: list[str] = []
    else:
        core_roles, optional_roles, outcome_roles = _registry(market)
    if manifest.get("schema") != "warroom.v91.predictor_manifest.v1":
        errors.append("invalid predictor manifest schema")
    if manifest.get("evidence_mode") != "REAL_POINT_IN_TIME_BLIND":
        errors.append("evidence_mode must be REAL_POINT_IN_TIME_BLIND")
    if manifest.get("synthetic_data") is not False:
        errors.append("synthetic_data must be false")
    if manifest.get("test_fixture") is not False:
        errors.append("test_fixture must be false")
    roles = manifest.get("roles") if isinstance(manifest.get("roles"), Mapping) else {}
    prohibited_roles = sorted(set(roles) & (FORBIDDEN_PREDICTOR_ROLES | set(outcome_roles)))
    if prohibited_roles:
        errors.append("outcome roles prohibited in predictor manifest: " + ",".join(prohibited_roles))
    missing_core = sorted(set(core_roles) - set(roles))
    if missing_core:
        errors.append("missing core roles: " + ",".join(missing_core))
    unknown_roles = sorted(set(roles) - set(core_roles) - set(optional_roles))
    if unknown_roles:
        errors.append("unknown roles for exact market scope: " + ",".join(unknown_roles))

    decisions = pd.DataFrame()
    decision_path = None
    try:
        decision_path = _resolve_relative(path.parent, str(manifest.get("decision_times_file") or ""))
        expected = str(manifest.get("decision_times_hash") or "").lower()
        if not HEX64.fullmatch(expected) or expected == "0" * 64:
            errors.append("invalid decision_times_hash")
        elif not decision_path.exists() or _sha256(decision_path) != expected:
            errors.append("decision_times hash/file mismatch")
        else:
            decisions = _load_table(decision_path)
            missing_decision = sorted(DECISION_COLUMNS - set(decisions.columns))
            if missing_decision:
                errors.append("decision file missing columns: " + ",".join(missing_decision))
            else:
                decisions["decision_time"] = pd.to_datetime(decisions["decision_time"], utc=True, errors="coerce")
                if decisions["decision_time"].isna().any():
                    errors.append("invalid decision_time rows")
                if decisions["forecast_id"].astype(str).duplicated().any():
                    errors.append("duplicate forecast_id")
                if not decisions["model_hash"].astype(str).str.fullmatch(r"[0-9a-f]{64}").fillna(False).all():
                    errors.append("invalid model_hash in decision file")
    except Exception as exc:
        errors.append(f"decision file invalid: {type(exc).__name__}: {exc}")

    audits: dict[str, dict[str, Any]] = {}
    if not decisions.empty:
        for role in sorted(set(roles)):
            audit = _audit_role(role, roles[role], path.parent, decisions)
            audits[role] = asdict(audit)
            if role in core_roles and not audit.valid:
                errors.extend(f"{role}: {message}" for message in audit.errors)

    history_start = pd.to_datetime(manifest.get("history_start"), utc=True, errors="coerce")
    history_end = pd.to_datetime(manifest.get("history_end"), utc=True, errors="coerce")
    history_years = 0.0
    if str(history_start) == "NaT" or str(history_end) == "NaT" or history_end <= history_start:
        errors.append("invalid history_start/history_end")
    else:
        history_years = (history_end - history_start).days / 365.25

    for field in RECEIPT_FIELDS:
        value = str(manifest.get(field) or "").lower()
        if not HEX64.fullmatch(value) or value == "0" * 64:
            errors.append(f"invalid {field}")

    collection_admitted = not errors
    decision_months = 0
    regimes = 0
    if not decisions.empty and "decision_time" in decisions:
        decision_months = int(decisions["decision_time"].dt.strftime("%Y-%m").nunique())
        regimes = int(decisions["regime"].astype(str).nunique()) if "regime" in decisions else 0
    historical_ready = bool(collection_admitted and history_years >= 8 and len(decisions) >= 200 and decision_months >= 24 and regimes >= 4)
    payload = {
        "schema": "warroom.v91.data_admission.v1",
        "valid": collection_admitted,
        "collection_admitted": collection_admitted,
        "historical_proof_ready": historical_ready,
        "market": market or None,
        "model_id": manifest.get("model_id"),
        "core_roles": core_roles,
        "optional_roles": optional_roles,
        "missing_core_roles": missing_core,
        "roles_audited": audits,
        "decision_forecasts": int(len(decisions)),
        "decision_months": decision_months,
        "decision_regimes": regimes,
        "history_years": history_years,
        "errors": sorted(set(errors)),
        "proof_ceiling": "HISTORICAL_BLIND_PROOF_READY" if historical_ready else "DATA_COLLECTION_ADMITTED" if collection_admitted else "BLOCKED_DATA",
        "claim_limit": "Admission proves portable, forecast-local PIT data usability only. Outcomes, target accuracy, profit factor and trading edge require separate sealed adjudication.",
    }
    payload["admission_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload

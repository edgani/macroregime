"""War Room OS V8.9 real-data admission gate.

A market dataset is not allowed into discovery, validation, or promotion merely because a CSV
exists.  Every required evidence role must be backed by an immutable file, a matching SHA-256,
point-in-time timestamps, and a nontechnical feature domain.  This gate validates data identity and
availability semantics only; it does not prove alpha.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import math
import re

import pandas as pd

from warroom.no_technical_policy import validate_feature_names

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
COMMON_COLUMNS = {
    "record_id", "instrument_id", "observation_at", "available_at", "source_id",
    "source_record_id", "field_id", "value", "unit", "revision_id",
}
REQUIRED_ROLES = {
    "us": {
        "security_master", "corporate_actions", "filing_fundamentals", "expectations",
        "bottleneck_transmission", "positioning_amplification", "valuation_snapshot",
        "execution_costs_capacity", "outcome_prices",
    },
    "idx": {
        "security_master", "corporate_actions", "issuer_fundamentals", "controller_free_float",
        "broker_inventory", "foreign_flow", "bottleneck_transmission", "valuation_snapshot",
        "execution_costs_capacity", "outcome_prices",
    },
    "commodity": {
        "contract_master", "stock_flow_balance", "inventory_surprise", "physical_basis",
        "freight_storage_capacity", "positioning", "expectations", "execution_costs_capacity",
        "outcome_prices",
    },
    "fx": {
        "pair_master", "relative_macro_vintages", "policy_expectations", "balance_of_payments",
        "reserves_intervention", "funding_positioning", "valuation_anchor",
        "execution_costs_capacity", "outcome_prices",
    },
    "crypto": {
        "asset_venue_master", "protocol_financials", "token_supply_unlocks", "stablecoin_liquidity",
        "entity_adjusted_flows", "funding_basis_oi_liquidations", "valuation_snapshot",
        "execution_costs_capacity", "counterparty_risk", "outcome_prices",
    },
}


@dataclass(frozen=True)
class RoleAudit:
    role: str
    valid: bool
    path: str | None
    rows: int
    min_observation_at: str | None
    max_available_at: str | None
    sha256: str | None
    errors: tuple[str, ...]


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


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _audit_role(role: str, spec: Mapping[str, Any], root: Path, decision_time: pd.Timestamp) -> RoleAudit:
    errors: list[str] = []
    relative = str(spec.get("path") or "").strip()
    expected_hash = str(spec.get("sha256") or "").lower()
    path = (root / relative).resolve() if relative else None
    if not relative:
        errors.append("path missing")
    if not HEX64.fullmatch(expected_hash):
        errors.append("invalid sha256")
    if path is not None and root.resolve() not in path.parents and path != root.resolve():
        errors.append("path escapes manifest root")
    if path is None or not path.exists() or not path.is_file():
        errors.append("file missing")
        return RoleAudit(role, False, str(path) if path else None, 0, None, None, expected_hash or None, tuple(sorted(set(errors))))
    actual_hash = _sha256(path)
    if actual_hash != expected_hash:
        errors.append("sha256 mismatch")
    try:
        frame = _load_table(path)
    except Exception as exc:
        errors.append(f"load failed: {type(exc).__name__}: {exc}")
        return RoleAudit(role, False, str(path), 0, None, None, actual_hash, tuple(sorted(set(errors))))
    missing = sorted(COMMON_COLUMNS - set(frame.columns))
    if missing:
        errors.append("missing columns: " + ",".join(missing))
    rows = len(frame)
    if rows <= 0:
        errors.append("empty evidence table")
    min_observation = None
    max_available = None
    if not missing:
        observed = pd.to_datetime(frame["observation_at"], utc=True, errors="coerce")
        available = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
        if observed.isna().any():
            errors.append("invalid observation_at")
        if available.isna().any():
            errors.append("invalid available_at")
        if not observed.isna().all():
            min_observation = observed.min().isoformat()
        if not available.isna().all():
            max_available = available.max().isoformat()
        if (available > decision_time).fillna(False).any():
            errors.append("future information relative to decision_time")
        duplicate_cols = ["source_id", "source_record_id", "field_id", "available_at", "instrument_id"]
        if frame.duplicated(duplicate_cols).any():
            errors.append("duplicate point-in-time source record")
        numeric = pd.to_numeric(frame["value"], errors="coerce")
        if numeric.isna().all():
            errors.append("value column contains no numeric evidence")
        if "feature_domain" in frame.columns:
            domains = [str(x).strip().lower() for x in frame["feature_domain"].dropna().unique()]
            violations = validate_feature_names(domains)
            if violations:
                errors.append("technical predictor domain prohibited: " + "|".join(violations))
        if "synthetic" in frame.columns and frame["synthetic"].astype(bool).any():
            errors.append("synthetic evidence prohibited")
        if "test_fixture" in frame.columns and frame["test_fixture"].astype(bool).any():
            errors.append("test fixture prohibited")
    minimum_rows = int(spec.get("minimum_rows") or 1)
    if rows < minimum_rows:
        errors.append(f"rows below manifest minimum: {rows} < {minimum_rows}")
    return RoleAudit(role, not errors, str(path), rows, min_observation, max_available, actual_hash, tuple(sorted(set(errors))))


def admit_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema": "warroom.v89.data_admission.v1", "valid": False, "errors": [f"manifest load failed: {type(exc).__name__}: {exc}"], "market": None}
    errors: list[str] = []
    market = str(manifest.get("market") or "").lower()
    if market not in MARKETS:
        errors.append("unsupported market")
    mode = str(manifest.get("evidence_mode") or "")
    if mode != "REAL_POINT_IN_TIME_BLIND":
        errors.append("evidence_mode must be REAL_POINT_IN_TIME_BLIND")
    if manifest.get("synthetic_data") is not False:
        errors.append("synthetic_data must be false")
    if manifest.get("test_fixture") is not False:
        errors.append("test_fixture must be false")
    decision_time = pd.to_datetime(manifest.get("decision_time"), utc=True, errors="coerce")
    if str(decision_time) == "NaT":
        errors.append("invalid decision_time")
    roles = manifest.get("roles") if isinstance(manifest.get("roles"), Mapping) else {}
    required = REQUIRED_ROLES.get(market, set())
    missing_roles = sorted(required - set(roles))
    if missing_roles:
        errors.append("missing required roles: " + ",".join(missing_roles))
    audits: dict[str, dict[str, Any]] = {}
    if str(decision_time) != "NaT":
        for role in sorted(required & set(roles)):
            audit = _audit_role(role, roles[role], path.parent, decision_time)
            audits[role] = asdict(audit)
            if not audit.valid:
                errors.extend(f"{role}: {message}" for message in audit.errors)
    history_start = pd.to_datetime(manifest.get("history_start"), utc=True, errors="coerce")
    history_end = pd.to_datetime(manifest.get("history_end"), utc=True, errors="coerce")
    if str(history_start) == "NaT" or str(history_end) == "NaT" or history_end <= history_start:
        errors.append("invalid history_start/history_end")
    else:
        years = (history_end - history_start).days / 365.25
        if years < 8:
            errors.append("less than eight years of declared history")
    for field in ("universe_snapshot_hash", "security_master_hash", "global_trial_ledger_hash", "data_dictionary_hash", "data_custodian_receipt_hash", "source_license_receipt_hash"):
        value = str(manifest.get(field) or "").lower()
        if not HEX64.fullmatch(value):
            errors.append(f"invalid {field}")
    payload = {
        "schema": "warroom.v89.data_admission.v1",
        "valid": not errors,
        "market": market or None,
        "decision_time": None if str(decision_time) == "NaT" else decision_time.isoformat(),
        "roles_required": sorted(required),
        "roles_audited": audits,
        "errors": sorted(set(errors)),
        "claim_limit": "Data admission validates real point-in-time identity and availability only; it does not prove a trading edge.",
    }
    payload["admission_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload

"""Fail-closed licensed-data and frozen-evaluation runners for V72.

The distributable release contains no proprietary Cboe records.  This module verifies a local,
licensed archive, binds license-permitted derived tables to that archive, and opens the historical
lockbox exactly once.  It cannot promote a component or authorize capital.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json

import pandas as pd

from dealer_gamma_research_v72 import (
    PROTOCOL_PATH,
    V72DataError,
    canonical,
    file_sha256,
    validate_source_manifest,
)
from v72_outcome_evaluator import SPEC_PATH, evaluate_all

ROOT = Path(__file__).resolve().parent
FROZEN_CALENDAR_PATH = ROOT / "research_v56" / "V72_C1_RTH_EXPECTED_CALENDAR.csv"
SOURCE_SCHEMA = "warroom.v72_licensed_source_manifest"
SOURCE_RECEIPT_SCHEMA = "warroom.v72_source_validation_receipt"
DERIVED_SCHEMA = "warroom.v72_derived_evaluation_manifest"
DERIVED_RECEIPT_SCHEMA = "warroom.v72_derived_validation_receipt"
LOCKBOX_OPEN_SCHEMA = "warroom.v72_lockbox_open_receipt"
HISTORICAL_RESULT_SCHEMA = "warroom.v72_historical_evaluation_release"
REQUIRED_PRODUCTS = ("TBT", "QUOTES", "UNDERLIER")
OPTIONAL_PRODUCTS = ("GRK",)
CLAIM_FILES = {
    "V72_C1_VERIFIED_GAMMA_RESPONSE": "c1",
    "V72_C2_INCREMENTAL_PIN_BREAK": "c2",
    "V72_C3_NET_GAMMA_SCALP": "c3",
}


class V72RunnerError(ValueError):
    """Raised whenever lineage, lockbox, or frozen-evaluation contracts are violated."""


def _strict_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise V72RunnerError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    except V72RunnerError:
        raise
    except Exception as exc:
        raise V72RunnerError(f"cannot read JSON {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise V72RunnerError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def _frozen_dates() -> list:
    if not FROZEN_CALENDAR_PATH.is_file():
        raise V72RunnerError("frozen expected calendar is missing")
    frame = pd.read_csv(FROZEN_CALENDAR_PATH)
    if "trading_dt" not in frame.columns:
        raise V72RunnerError("frozen expected calendar missing trading_dt")
    return _parse_dates(frame["trading_dt"].astype(str).tolist(), "frozen calendar")


def _manifest_row(path: Path, root: Path, product: str, trading_dt: str) -> dict[str, Any]:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except Exception as exc:
        raise V72RunnerError(f"source path escapes licensed root: {path}") from exc
    return {
        "path": rel,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "product": product,
        "trading_dt": trading_dt,
        "license_classification": "PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION",
    }


def generate_source_manifest(licensed_root: Path, *, include_grk: bool | None = None) -> dict[str, Any]:
    """Generate a deterministic V72 raw-source manifest from the frozen directory contract.

    The generator never guesses vendor filenames and never shortens the expected calendar.  GRK is
    optional, but when any GRK file is present the complete frozen calendar is required.
    """
    root = licensed_root.resolve()
    if not root.is_dir():
        raise V72RunnerError(f"licensed root is not a directory: {root}")
    dates = _frozen_dates()
    templates = {
        "TBT": "tbt/C1_TBT_{date}.zip",
        "QUOTES": "quotes/OPTION_QUOTES_SPX_1MIN_{date}.zip",
        "UNDERLIER": "underlier/SPX_ES_1MIN_{date}.csv",
        "GRK": "grk/C1_GRK_{date}.zip",
    }
    grk_present = any((root / templates["GRK"].format(date=d.isoformat())).is_file() for d in dates)
    use_grk = grk_present if include_grk is None else bool(include_grk)
    if include_grk is False and grk_present:
        raise V72RunnerError("GRK files are present but include_grk=False; ambiguous lineage is forbidden")

    rows: list[dict[str, Any]] = []
    products = [*REQUIRED_PRODUCTS, *(("GRK",) if use_grk else ())]
    for d in dates:
        ds = d.isoformat()
        for product in products:
            path = root / templates[product].format(date=ds)
            if not path.is_file():
                raise V72RunnerError(f"missing exact {product} source file for {ds}: {path.relative_to(root)}")
            if path.stat().st_size <= 0:
                raise V72RunnerError(f"empty exact {product} source file for {ds}: {path.relative_to(root)}")
            rows.append(_manifest_row(path, root, product, ds))

    payload: dict[str, Any] = {
        "schema": SOURCE_SCHEMA,
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "frozen_calendar_sha256": file_sha256(FROZEN_CALENDAR_PATH),
        "license_classification": "PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION",
        "expected_trading_dates": [d.isoformat() for d in dates],
        "files": sorted(rows, key=lambda r: (r["trading_dt"], r["product"], r["path"])),
        "raw_redistribution_permitted": False,
        "historical_outcomes_opened": False,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    payload["manifest_digest_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
    return payload


def generate_derived_manifest(derived_root: Path, source_receipt_path: Path,
                              *, filenames: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Seal the three frozen claim tables without opening or evaluating their outcomes."""
    root = derived_root.resolve()
    source_receipt_path = source_receipt_path.resolve()
    receipt = load_json(source_receipt_path)
    if receipt.get("schema") != SOURCE_RECEIPT_SCHEMA or receipt.get("status") != "PASS_READY_TO_DERIVE_FROZEN_TABLES":
        raise V72RunnerError("source receipt is not a passing V72 receipt")
    names = dict(filenames or {claim_id: f"{key}.csv" for claim_id, key in CLAIM_FILES.items()})
    if set(names) != set(CLAIM_FILES):
        raise V72RunnerError("derived filename map must contain the exact three V72 claim IDs")
    rows: list[dict[str, Any]] = []
    for claim_id, key in CLAIM_FILES.items():
        rel = _safe_relative(names[claim_id], "derived")
        path = root / rel
        if not path.is_file() or path.stat().st_size <= 0:
            raise V72RunnerError(f"missing or empty derived claim table: {rel}")
        lower = path.name.lower()
        if lower.endswith(".csv.gz"):
            fmt = "CSV_GZIP"
        elif lower.endswith(".csv"):
            fmt = "CSV"
        else:
            raise V72RunnerError(f"derived claim table must be CSV or CSV.GZ: {rel}")
        rows.append({
            "claim_id": claim_id,
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
            "format": fmt,
        })
    payload: dict[str, Any] = {
        "schema": DERIVED_SCHEMA,
        "source_receipt_sha256": file_sha256(source_receipt_path),
        "source_manifest_sha256": receipt["source_manifest_sha256"],
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "evaluator_spec_sha256": file_sha256(SPEC_PATH),
        "license_classification": "DERIVED_INTERNAL_RESEARCH_NO_RAW_REDISTRIBUTION",
        "lockbox_state": "SEALED_UNOPENED",
        "files": sorted(rows, key=lambda r: r["claim_id"]),
        "raw_records_in_release": False,
        "historical_outcomes_opened": False,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    payload["manifest_digest_sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
    return payload


def _parse_dates(values: Any, label: str) -> list:
    if not isinstance(values, list) or not values:
        raise V72RunnerError(f"{label} must be a non-empty list")
    parsed = pd.to_datetime(pd.Series(values, dtype="object"), errors="coerce").dt.date
    if parsed.isna().any():
        raise V72RunnerError(f"{label} contains invalid dates")
    dates = list(parsed)
    if len(dates) != len(set(dates)):
        raise V72RunnerError(f"{label} contains duplicate dates")
    if dates != sorted(dates):
        raise V72RunnerError(f"{label} must be sorted")
    return dates


def _manifest_coverage(manifest: Mapping[str, Any]) -> dict[str, set]:
    coverage = {p: set() for p in (*REQUIRED_PRODUCTS, *OPTIONAL_PRODUCTS)}
    for row in manifest.get("files") or []:
        if not isinstance(row, Mapping):
            raise V72RunnerError("source manifest file row must be an object")
        product = str(row.get("product") or "").upper()
        if product not in coverage:
            raise V72RunnerError(f"unsupported source product: {product}")
        dt = pd.to_datetime(row.get("trading_dt"), errors="coerce")
        if pd.isna(dt):
            raise V72RunnerError("source manifest contains invalid trading_dt")
        coverage[product].add(dt.date())
        if str(row.get("license_classification") or "") != "PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION":
            raise V72RunnerError("every raw source row must carry the proprietary no-redistribution license class")
    return coverage


def validate_licensed_source_package(manifest_path: Path, licensed_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    licensed_root = licensed_root.resolve()
    manifest = load_json(manifest_path)
    if manifest.get("schema") != SOURCE_SCHEMA:
        raise V72RunnerError("source manifest schema mismatch")
    if manifest.get("protocol_sha256") != file_sha256(PROTOCOL_PATH):
        raise V72RunnerError("source manifest protocol hash mismatch")
    if manifest.get("license_classification") != "PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION":
        raise V72RunnerError("source manifest license classification mismatch")
    expected_dates = _parse_dates(manifest.get("expected_trading_dates"), "expected_trading_dates")
    if not FROZEN_CALENDAR_PATH.is_file():
        raise V72RunnerError("frozen expected calendar is missing")
    frozen_calendar_hash = file_sha256(FROZEN_CALENDAR_PATH)
    protocol = load_json(PROTOCOL_PATH)
    frozen_spec = ((protocol.get("data_integrity") or {}).get("frozen_expected_calendar") or {})
    if frozen_spec.get("sha256") != frozen_calendar_hash:
        raise V72RunnerError("frozen expected calendar hash does not match protocol")
    frozen_dates = _parse_dates(pd.read_csv(FROZEN_CALENDAR_PATH)["trading_dt"].astype(str).tolist(), "frozen calendar")
    if expected_dates != frozen_dates:
        raise V72RunnerError("manifest expected_trading_dates must exactly match the frozen V72 RTH calendar")

    try:
        base = validate_source_manifest(manifest, base_dir=licensed_root, expected_dates=expected_dates)
    except V72DataError as exc:
        raise V72RunnerError(str(exc)) from exc
    coverage = _manifest_coverage(manifest)
    expected = set(expected_dates)
    for product in REQUIRED_PRODUCTS:
        if coverage[product] != expected:
            missing = sorted(expected - coverage[product])
            extra = sorted(coverage[product] - expected)
            raise V72RunnerError(
                f"{product} calendar must equal expected calendar; missing={len(missing)} extra={len(extra)}"
            )
    if coverage["GRK"] and coverage["GRK"] != expected:
        raise V72RunnerError("optional GRK must cover the complete expected calendar when supplied")

    files = manifest.get("files") or []
    by_product = {p: sum(1 for r in files if str(r.get("product") or "").upper() == p) for p in coverage}
    receipt = {
        "schema": SOURCE_RECEIPT_SCHEMA,
        "status": "PASS_READY_TO_DERIVE_FROZEN_TABLES",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_path": manifest_path.name,
        "source_manifest_sha256": file_sha256(manifest_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "expected_trading_dates": len(expected_dates),
        "frozen_calendar_sha256": frozen_calendar_hash,
        "calendar_start": expected_dates[0].isoformat(),
        "calendar_end": expected_dates[-1].isoformat(),
        "files_checked": int(base["files_checked"]),
        "files_by_product": by_product,
        "source_manifest_digest_sha256": base["manifest_digest_sha256"],
        "raw_redistribution_permitted": False,
        "historical_outcomes_opened": False,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    receipt["receipt_digest_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    return receipt


def _safe_relative(value: Any, label: str) -> str:
    rel = str(value or "")
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise V72RunnerError(f"unsafe {label} path: {rel}")
    return rel


def _read_derived(path: Path, file_format: str) -> pd.DataFrame:
    fmt = file_format.upper()
    if fmt == "CSV":
        return pd.read_csv(path)
    if fmt in {"CSV_GZIP", "CSV.GZ"}:
        return pd.read_csv(path, compression="gzip")
    raise V72RunnerError(f"unsupported derived format: {file_format}; only CSV/CSV_GZIP are frozen")


def validate_derived_package(derived_manifest_path: Path, derived_root: Path,
                             source_receipt_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    derived_manifest_path = derived_manifest_path.resolve()
    derived_root = derived_root.resolve()
    source_receipt_path = source_receipt_path.resolve()
    manifest = load_json(derived_manifest_path)
    source_receipt = load_json(source_receipt_path)
    if manifest.get("schema") != DERIVED_SCHEMA:
        raise V72RunnerError("derived manifest schema mismatch")
    if source_receipt.get("schema") != SOURCE_RECEIPT_SCHEMA or source_receipt.get("status") != "PASS_READY_TO_DERIVE_FROZEN_TABLES":
        raise V72RunnerError("source receipt is not a passing V72 receipt")
    if manifest.get("source_receipt_sha256") != file_sha256(source_receipt_path):
        raise V72RunnerError("derived manifest source receipt hash mismatch")
    if manifest.get("source_manifest_sha256") != source_receipt.get("source_manifest_sha256"):
        raise V72RunnerError("derived manifest source lineage mismatch")
    if manifest.get("protocol_sha256") != file_sha256(PROTOCOL_PATH):
        raise V72RunnerError("derived manifest protocol hash mismatch")
    if manifest.get("evaluator_spec_sha256") != file_sha256(SPEC_PATH):
        raise V72RunnerError("derived manifest evaluator hash mismatch")
    if manifest.get("license_classification") != "DERIVED_INTERNAL_RESEARCH_NO_RAW_REDISTRIBUTION":
        raise V72RunnerError("derived manifest license class mismatch")
    if manifest.get("lockbox_state") != "SEALED_UNOPENED":
        raise V72RunnerError("derived lockbox is not sealed and unopened")

    rows = manifest.get("files")
    if not isinstance(rows, list) or len(rows) != 3:
        raise V72RunnerError("derived manifest must contain exactly three claim tables")
    seen_claims: set[str] = set()
    paths: dict[str, Path] = {}
    checked: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise V72RunnerError("derived manifest file row must be an object")
        claim_id = str(row.get("claim_id") or "")
        if claim_id not in CLAIM_FILES or claim_id in seen_claims:
            raise V72RunnerError(f"unknown or duplicate derived claim: {claim_id}")
        seen_claims.add(claim_id)
        rel = _safe_relative(row.get("path"), "derived")
        path = derived_root / rel
        if not path.is_file():
            raise V72RunnerError(f"missing derived table: {rel}")
        if int(row.get("bytes", -1)) != path.stat().st_size:
            raise V72RunnerError(f"derived size mismatch: {rel}")
        if str(row.get("sha256") or "").lower() != file_sha256(path):
            raise V72RunnerError(f"derived hash mismatch: {rel}")
        fmt = str(row.get("format") or "")
        if fmt.upper() not in {"CSV", "CSV_GZIP", "CSV.GZ"}:
            raise V72RunnerError(f"unsupported derived format: {fmt}")
        paths[CLAIM_FILES[claim_id]] = path
        checked.append({"claim_id": claim_id, "path": rel, "bytes": path.stat().st_size, "sha256": file_sha256(path), "format": fmt.upper()})
    if seen_claims != set(CLAIM_FILES):
        raise V72RunnerError("derived claim table set is incomplete")

    receipt = {
        "schema": DERIVED_RECEIPT_SCHEMA,
        "status": "PASS_READY_FOR_ONE_TIME_FROZEN_EVALUATION",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "derived_manifest_sha256": file_sha256(derived_manifest_path),
        "source_receipt_sha256": file_sha256(source_receipt_path),
        "source_manifest_sha256": source_receipt["source_manifest_sha256"],
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "evaluator_spec_sha256": file_sha256(SPEC_PATH),
        "tables": checked,
        "raw_records_in_release": False,
        "historical_outcomes_opened": False,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    receipt["receipt_digest_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    return receipt, paths


def open_and_evaluate_lockbox(*, derived_manifest_path: Path, derived_root: Path,
                              source_receipt_path: Path, derived_receipt_path: Path,
                              open_receipt_path: Path, result_path: Path) -> dict[str, Any]:
    """Open the sealed historical lockbox once and run the frozen production evaluator.

    The function refuses to overwrite either the opening receipt or historical result.  A later
    reproducibility audit should compare hashes against these artifacts rather than opening a new
    lockbox under changed code.
    """
    for path in (open_receipt_path, result_path):
        if path.exists():
            raise V72RunnerError(f"one-time lockbox artifact already exists: {path}")
    derived_receipt, paths = validate_derived_package(derived_manifest_path, derived_root, source_receipt_path)
    write_json_atomic(derived_receipt_path, derived_receipt)

    open_receipt = {
        "schema": LOCKBOX_OPEN_SCHEMA,
        "status": "OPENED_ONCE_FOR_FROZEN_EVALUATION",
        "opened_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_receipt_sha256": file_sha256(source_receipt_path),
        "derived_receipt_sha256": file_sha256(derived_receipt_path),
        "derived_manifest_sha256": file_sha256(derived_manifest_path),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "evaluator_spec_sha256": file_sha256(SPEC_PATH),
        "evaluator_code_sha256": file_sha256(ROOT / "v72_outcome_evaluator.py"),
        "runner_code_sha256": file_sha256(Path(__file__).resolve()),
        "tables": {key: file_sha256(path) for key, path in sorted(paths.items())},
        "retuning_after_open": "FORBIDDEN",
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    open_receipt["receipt_digest_sha256"] = hashlib.sha256(canonical(open_receipt)).hexdigest()
    write_json_atomic(open_receipt_path, open_receipt)

    # Outcomes are read only after the immutable opening receipt exists.
    rows = load_json(derived_manifest_path)["files"]
    formats = {CLAIM_FILES[str(row["claim_id"])]: str(row["format"]) for row in rows}
    c1 = _read_derived(paths["c1"], formats["c1"])
    c2 = _read_derived(paths["c2"], formats["c2"])
    c3 = _read_derived(paths["c3"], formats["c3"])
    evaluation = evaluate_all(c1, c2, c3, fixture_mode=False)
    result = {
        "schema": HISTORICAL_RESULT_SCHEMA,
        "status": evaluation["status"],
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "open_receipt_sha256": file_sha256(open_receipt_path),
        "source_receipt_sha256": file_sha256(source_receipt_path),
        "derived_receipt_sha256": file_sha256(derived_receipt_path),
        "evaluation": evaluation,
        "historical_result_can_authorize_live_trading": False,
        "prospective_gate": "NOT_MATURED",
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    write_json_atomic(result_path, result)
    return result

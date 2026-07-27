"""Point-in-time US-equity data contract and fail-closed validator for War Room OS V7.8.

This module validates *data readiness*.  It does not calculate an alpha signal and it never
changes capital permission.  Production research must provide a licensed or otherwise lawful
survivor-bias-free panel outside the distributable ZIP.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "warroom.v78.us_pit_data_contract.v1"
CAPITAL_PERMISSION = "BLOCKED_DATA_VALIDATION_ONLY"

REQUIRED_FILES = {
    "source_manifest.json",
    "security_master.csv",
    "daily_prices.csv",
    "index_membership.csv",
    "corporate_actions.csv",
    "delistings.csv",
}

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "security_master.csv": {
        "permanent_id", "ticker", "effective_from", "effective_to", "security_type",
        "exchange", "currency", "source", "available_at_utc",
    },
    "daily_prices.csv": {
        "permanent_id", "observation_date", "open", "high", "low", "close", "adj_close",
        "volume", "source", "available_at_utc",
    },
    "index_membership.csv": {
        "index_id", "permanent_id", "member_from", "member_to", "source", "available_at_utc",
    },
    "corporate_actions.csv": {
        "permanent_id", "action_date", "action_type", "split_factor", "cash_dividend",
        "source", "available_at_utc",
    },
    "delistings.csv": {
        "permanent_id", "delisting_date", "delisting_return", "delisting_status",
        "source", "available_at_utc",
    },
}

ALLOWED_SECURITY_TYPES = {"COMMON_STOCK", "ADR", "REIT"}
ALLOWED_ACTION_TYPES = {"NONE", "SPLIT", "DIVIDEND", "SPINOFF", "MERGER", "SYMBOL_CHANGE", "OTHER"}
ALLOWED_DELISTING_STATUS = {"ACTIVE", "MERGED", "ACQUIRED", "BANKRUPT", "LIQUIDATED", "OTHER"}


@dataclass
class Issue:
    code: str
    file: str
    row: int | None
    detail: str
    severity: str = "ERROR"


class ContractError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ContractError(f"{field} must be YYYY-MM-DD: {value!r}") from exc


def _parse_optional_date(value: str, *, field: str) -> date | None:
    value = (value or "").strip()
    return _parse_date(value, field=field) if value else None


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ContractError(f"{field} must be ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field} must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def _finite(value: str, *, field: str, allow_blank: bool = False) -> float | None:
    value = (value or "").strip()
    if not value and allow_blank:
        return None
    try:
        number = float(value)
    except Exception as exc:
        raise ContractError(f"{field} must be numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise ContractError(f"{field} must be finite: {value!r}")
    return number


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ContractError("missing CSV header")
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def _availability_not_before_event(available: datetime, event_date: date) -> bool:
    # Exact release time may be after the event date.  It may never be timestamped before the
    # underlying event date, because that would encode a future fact into the past.
    return available.date() >= event_date


def validate_dataset(root: str | Path, *, as_of_utc: datetime | None = None) -> dict[str, Any]:
    root = Path(root)
    now = as_of_utc or datetime.now(timezone.utc)
    issues: list[Issue] = []
    stats: dict[str, Any] = {"files": {}, "rows": {}, "date_ranges": {}}

    if not root.is_dir():
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "capital_permission": CAPITAL_PERMISSION,
            "issues": [asdict(Issue("ROOT_NOT_FOUND", str(root), None, "dataset directory does not exist"))],
        }

    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    for name in missing:
        issues.append(Issue("MISSING_REQUIRED_FILE", name, None, "required point-in-time dataset file is absent"))
    if missing:
        return _report(root, issues, stats)

    manifest_path = root / "source_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(Issue("INVALID_MANIFEST_JSON", manifest_path.name, None, str(exc)))
        return _report(root, issues, stats)

    if manifest.get("schema") != "warroom.v78.us_pit_source_manifest.v1":
        issues.append(Issue("MANIFEST_SCHEMA", manifest_path.name, None, "unexpected manifest schema"))
    if manifest.get("capital_permission") != CAPITAL_PERMISSION:
        issues.append(Issue("MANIFEST_PERMISSION", manifest_path.name, None, "manifest must remain data-validation-only"))
    if manifest.get("survivor_bias_free") is not True:
        issues.append(Issue("SURVIVOR_BIAS_FLAG", manifest_path.name, None, "source must explicitly attest survivor-bias-free coverage"))
    if manifest.get("point_in_time") is not True:
        issues.append(Issue("POINT_IN_TIME_FLAG", manifest_path.name, None, "source must explicitly attest point-in-time timestamps"))
    if not str(manifest.get("provider") or "").strip():
        issues.append(Issue("PROVIDER_MISSING", manifest_path.name, None, "provider is required"))
    if not str(manifest.get("license_or_terms_reference") or "").strip():
        issues.append(Issue("LICENSE_REFERENCE_MISSING", manifest_path.name, None, "license/terms reference is required"))

    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    indexed = {str(item.get("path")): item for item in manifest_files if isinstance(item, dict)}
    for name in sorted(REQUIRED_FILES - {"source_manifest.json"}):
        path = root / name
        actual = sha256_file(path)
        stats["files"][name] = {"bytes": path.stat().st_size, "sha256": actual}
        item = indexed.get(name)
        if not item:
            issues.append(Issue("MANIFEST_FILE_MISSING", name, None, "file not declared in source manifest"))
            continue
        if str(item.get("sha256") or "").lower() != actual:
            issues.append(Issue("MANIFEST_HASH_MISMATCH", name, None, f"declared={item.get('sha256')} actual={actual}"))
        try:
            declared_bytes = int(item.get("bytes"))
        except Exception:
            declared_bytes = -1
        if declared_bytes != path.stat().st_size:
            issues.append(Issue("MANIFEST_SIZE_MISMATCH", name, None, f"declared={declared_bytes} actual={path.stat().st_size}"))

    tables: dict[str, list[dict[str, str]]] = {}
    for name, required in REQUIRED_COLUMNS.items():
        path = root / name
        try:
            fields, rows = _read_csv(path)
        except Exception as exc:
            issues.append(Issue("CSV_READ_ERROR", name, None, str(exc)))
            continue
        tables[name] = rows
        stats["rows"][name] = len(rows)
        absent = sorted(required - set(fields))
        if absent:
            issues.append(Issue("MISSING_COLUMNS", name, None, ",".join(absent)))

    security_ids: set[str] = set()
    ticker_intervals: dict[str, list[tuple[date, date | None, str]]] = {}
    for i, row in enumerate(tables.get("security_master.csv", []), 2):
        try:
            pid = row["permanent_id"].strip()
            ticker = row["ticker"].strip().upper()
            start = _parse_date(row["effective_from"], field="effective_from")
            end = _parse_optional_date(row["effective_to"], field="effective_to")
            available = _parse_utc(row["available_at_utc"], field="available_at_utc")
            if not pid or not ticker:
                raise ContractError("permanent_id and ticker are required")
            if end is not None and end < start:
                raise ContractError("effective_to precedes effective_from")
            if row["security_type"].strip().upper() not in ALLOWED_SECURITY_TYPES:
                raise ContractError(f"unsupported security_type {row['security_type']!r}")
            if available > now:
                raise ContractError("availability timestamp is in the future")
            if not _availability_not_before_event(available, start):
                raise ContractError("availability timestamp predates effective_from")
            security_ids.add(pid)
            ticker_intervals.setdefault(ticker, []).append((start, end, pid))
        except Exception as exc:
            issues.append(Issue("SECURITY_MASTER_ROW", "security_master.csv", i, str(exc)))

    # Same ticker may legitimately be reused over long history, but intervals may not overlap
    # for different permanent IDs without an explicit security-master disambiguation.
    for ticker, intervals in ticker_intervals.items():
        ordered = sorted(intervals)
        for left, right in zip(ordered, ordered[1:]):
            left_end = left[1] or date.max
            if right[0] <= left_end and right[2] != left[2]:
                issues.append(Issue("TICKER_INTERVAL_OVERLAP", "security_master.csv", None, f"{ticker}: {left} overlaps {right}"))

    price_keys: set[tuple[str, date]] = set()
    price_dates: list[date] = []
    for i, row in enumerate(tables.get("daily_prices.csv", []), 2):
        try:
            pid = row["permanent_id"].strip()
            obs = _parse_date(row["observation_date"], field="observation_date")
            available = _parse_utc(row["available_at_utc"], field="available_at_utc")
            values = {name: _finite(row[name], field=name) for name in ("open", "high", "low", "close", "adj_close", "volume")}
            if pid not in security_ids:
                raise ContractError("permanent_id absent from security_master")
            if available > now:
                raise ContractError("availability timestamp is in the future")
            if not _availability_not_before_event(available, obs):
                raise ContractError("availability timestamp predates observation_date")
            if min(values["open"], values["high"], values["low"], values["close"], values["adj_close"]) <= 0:
                raise ContractError("prices must be positive")
            if values["volume"] < 0:
                raise ContractError("volume must be non-negative")
            if values["high"] < max(values["open"], values["low"], values["close"]):
                raise ContractError("high is below another OHLC field")
            if values["low"] > min(values["open"], values["high"], values["close"]):
                raise ContractError("low is above another OHLC field")
            key = (pid, obs)
            if key in price_keys:
                raise ContractError("duplicate permanent_id/observation_date")
            price_keys.add(key)
            price_dates.append(obs)
        except Exception as exc:
            issues.append(Issue("DAILY_PRICE_ROW", "daily_prices.csv", i, str(exc)))

    membership_keys: set[tuple[str, str, date]] = set()
    member_dates: list[date] = []
    for i, row in enumerate(tables.get("index_membership.csv", []), 2):
        try:
            index_id = row["index_id"].strip().upper()
            pid = row["permanent_id"].strip()
            start = _parse_date(row["member_from"], field="member_from")
            end = _parse_optional_date(row["member_to"], field="member_to")
            available = _parse_utc(row["available_at_utc"], field="available_at_utc")
            if pid not in security_ids:
                raise ContractError("permanent_id absent from security_master")
            if end is not None and end < start:
                raise ContractError("member_to precedes member_from")
            if available > now:
                raise ContractError("availability timestamp is in the future")
            if not _availability_not_before_event(available, start):
                raise ContractError("availability timestamp predates member_from")
            key = (index_id, pid, start)
            if key in membership_keys:
                raise ContractError("duplicate membership interval")
            membership_keys.add(key)
            member_dates.extend([start] + ([end] if end else []))
        except Exception as exc:
            issues.append(Issue("MEMBERSHIP_ROW", "index_membership.csv", i, str(exc)))

    for i, row in enumerate(tables.get("corporate_actions.csv", []), 2):
        try:
            pid = row["permanent_id"].strip()
            action_date = _parse_date(row["action_date"], field="action_date")
            available = _parse_utc(row["available_at_utc"], field="available_at_utc")
            action = row["action_type"].strip().upper()
            split = _finite(row["split_factor"], field="split_factor", allow_blank=True)
            dividend = _finite(row["cash_dividend"], field="cash_dividend", allow_blank=True)
            if pid not in security_ids:
                raise ContractError("permanent_id absent from security_master")
            if action not in ALLOWED_ACTION_TYPES:
                raise ContractError(f"unsupported action_type {action!r}")
            if split is not None and split <= 0:
                raise ContractError("split_factor must be positive")
            if dividend is not None and dividend < 0:
                raise ContractError("cash_dividend must be non-negative")
            if available > now or not _availability_not_before_event(available, action_date):
                raise ContractError("invalid availability timestamp")
        except Exception as exc:
            issues.append(Issue("CORPORATE_ACTION_ROW", "corporate_actions.csv", i, str(exc)))

    delisting_ids: set[str] = set()
    for i, row in enumerate(tables.get("delistings.csv", []), 2):
        try:
            pid = row["permanent_id"].strip()
            event = _parse_optional_date(row["delisting_date"], field="delisting_date")
            available = _parse_utc(row["available_at_utc"], field="available_at_utc")
            status = row["delisting_status"].strip().upper()
            dret = _finite(row["delisting_return"], field="delisting_return", allow_blank=True)
            if pid not in security_ids:
                raise ContractError("permanent_id absent from security_master")
            if status not in ALLOWED_DELISTING_STATUS:
                raise ContractError(f"unsupported delisting_status {status!r}")
            if status == "ACTIVE" and event is not None:
                raise ContractError("ACTIVE row may not have delisting_date")
            if status != "ACTIVE" and event is None:
                raise ContractError("non-ACTIVE row requires delisting_date")
            if dret is not None and dret < -1.0:
                raise ContractError("delisting_return cannot be below -100%")
            if available > now:
                raise ContractError("availability timestamp is in the future")
            if event is not None and not _availability_not_before_event(available, event):
                raise ContractError("availability timestamp predates delisting_date")
            if pid in delisting_ids:
                raise ContractError("duplicate permanent_id in delistings")
            delisting_ids.add(pid)
        except Exception as exc:
            issues.append(Issue("DELISTING_ROW", "delistings.csv", i, str(exc)))

    # A complete master must explicitly classify every security as active or delisted; silence
    # is not treated as zero delisting return.
    missing_delisting_class = sorted(security_ids - delisting_ids)
    if missing_delisting_class:
        issues.append(Issue("DELISTING_COVERAGE", "delistings.csv", None, f"{len(missing_delisting_class)} permanent_ids lack explicit status"))

    if price_dates:
        stats["date_ranges"]["daily_prices.csv"] = {"min": min(price_dates).isoformat(), "max": max(price_dates).isoformat()}
    if member_dates:
        stats["date_ranges"]["index_membership.csv"] = {"min": min(member_dates).isoformat(), "max": max(member_dates).isoformat()}

    stats["unique_permanent_ids"] = len(security_ids)
    stats["unique_price_keys"] = len(price_keys)
    stats["membership_intervals"] = len(membership_keys)
    stats["explicit_delisting_statuses"] = len(delisting_ids)
    return _report(root, issues, stats)


def _report(root: Path, issues: Iterable[Issue], stats: dict[str, Any]) -> dict[str, Any]:
    issue_rows = [asdict(issue) for issue in issues]
    errors = [row for row in issue_rows if row["severity"] == "ERROR"]
    return {
        "schema": SCHEMA,
        "dataset_root": str(root),
        "status": "PASS" if not errors else "FAIL",
        "capital_permission": CAPITAL_PERMISSION,
        "proof_effect": "DATA_CONTRACT_VERIFIED_ONLY" if not errors else "NONE_FAIL_CLOSED",
        "issues": issue_rows,
        "stats": stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_dataset(args.dataset_root)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

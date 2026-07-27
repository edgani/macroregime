"""Collect raw official evidence according to a local configuration.

The collector writes immutable timestamped raw files plus a provenance manifest. It never creates
a score, direction, forecast or capital instruction.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from official_source_connectors import (
    fetch_cftc_socrata,
    fetch_eia_v2,
    fetch_fred_alfred_observations,
    fetch_sec_submissions,
    normalize_sec_recent_filings,
    fetch_deribit_book_summary,
    fetch_deribit_last_trades,
)
from pit_evidence_contract import validate_frame


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_raw(directory: Path, role: str, payload: Any, collected_at: str) -> dict[str, Any]:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = directory / f"{role}_{digest[:16]}.json"
    path.write_bytes(raw)
    return {"role": role, "path": str(path), "sha256": digest, "collected_at": collected_at}


def collect(config: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    collected_at = now.isoformat().replace("+00:00", "Z")
    directory = Path(output_dir) / now.strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=False)
    artifacts = []
    normalized_rows = []
    errors = []

    for cik in config.get("sec_ciks") or []:
        try:
            payload = fetch_sec_submissions(str(cik))
            artifacts.append(write_raw(directory, f"sec_submissions_CIK{int(cik):010d}", payload, collected_at))
            normalized_rows.extend(normalize_sec_recent_filings(payload, ingested_at=collected_at))
        except Exception as exc:
            errors.append({"source": "SEC", "identity": str(cik), "error": f"{type(exc).__name__}: {exc}"})

    for request in config.get("alfred") or []:
        try:
            payload = fetch_fred_alfred_observations(**request)
            artifacts.append(write_raw(directory, f"alfred_{request['series_id']}", payload, collected_at))
        except Exception as exc:
            errors.append({"source": "ALFRED", "identity": request.get("series_id"), "error": f"{type(exc).__name__}: {exc}"})

    for request in config.get("eia") or []:
        try:
            payload = fetch_eia_v2(**request)
            artifacts.append(write_raw(directory, "eia", payload, collected_at))
        except Exception as exc:
            errors.append({"source": "EIA", "identity": request.get("route"), "error": f"{type(exc).__name__}: {exc}"})

    for request in config.get("cftc") or []:
        try:
            payload = fetch_cftc_socrata(**request)
            artifacts.append(write_raw(directory, f"cftc_{request['dataset_id']}", payload, collected_at))
        except Exception as exc:
            errors.append({"source": "CFTC", "identity": request.get("dataset_id"), "error": f"{type(exc).__name__}: {exc}"})

    for request in config.get("deribit_book_summary") or []:
        try:
            payload = fetch_deribit_book_summary(**request)
            artifacts.append(write_raw(directory, f"deribit_book_{request['currency']}_{request.get('kind','all')}", payload, collected_at))
        except Exception as exc:
            errors.append({"source": "DERIBIT", "identity": request.get("currency"), "error": f"{type(exc).__name__}: {exc}"})

    for request in config.get("deribit_last_trades") or []:
        try:
            payload = fetch_deribit_last_trades(**request)
            artifacts.append(write_raw(directory, f"deribit_trades_{request['currency']}_{request.get('kind','all')}", payload, collected_at))
        except Exception as exc:
            errors.append({"source": "DERIBIT", "identity": request.get("currency"), "error": f"{type(exc).__name__}: {exc}"})

    normalized = None
    pit_validation = None
    if normalized_rows:
        frame = pd.DataFrame(normalized_rows)
        normalized = directory / "normalized_sec_filing_events.csv"
        frame.to_csv(normalized, index=False)
        pit_validation = validate_frame(frame)
        artifacts.append({
            "role": "normalized_sec_filing_events", "path": str(normalized),
            "sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(), "collected_at": collected_at,
        })

    manifest = {
        "schema": "warroom.v89.official_collection_manifest.v1",
        "collected_at": collected_at,
        "capital_permission": "BLOCKED",
        "artifacts": artifacts,
        "normalized_pit_validation": pit_validation,
        "errors": errors,
        "complete": not errors,
        "claim_limit": "Raw official evidence collection only; no projection or trading permission.",
    }
    manifest["manifest_hash"] = hashlib.sha256(canonical(manifest)).hexdigest()
    (directory / "collection_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="runtime/official_evidence")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = collect(config, args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["complete"] else 2)


if __name__ == "__main__":
    main()

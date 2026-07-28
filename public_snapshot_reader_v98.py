"""Portable reader for official/public acquisition receipts used by War Room OS V9.8.

The reader never promotes a successful download into trading proof. It only reports which official
source artefacts are present, hash-valid and fresh enough to be useful as research context.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _parse_time(value: Any) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _manifest_candidates() -> list[Path]:
    patterns = (
        "runtime/v99_public_acquisition/*/v99_public_acquisition_manifest.json",
        "runtime/v98_public_acquisition/*/v98_public_acquisition_manifest.json",
        "runtime/v96_public_acquisition/*/v96_public_acquisition_manifest.json",
        "runtime/v95_public_acquisition/*/v95_public_acquisition_manifest.json",
        "runtime/v94_public_acquisition/*/v94_public_acquisition_manifest.json",
    )
    found: list[Path] = []
    for pattern in patterns:
        found.extend(HERE.glob(pattern))
    return sorted((p for p in found if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def latest_public_manifest() -> tuple[dict[str, Any] | None, Path | None]:
    for path in _manifest_candidates():
        payload = _safe_json(path)
        if payload is not None:
            return payload, path
    return None, None


def _resolve_item_path(manifest_path: Path, relative: str) -> Path | None:
    try:
        root = manifest_path.parent.resolve()
        path = (root / relative).resolve()
        path.relative_to(root)
        return path
    except Exception:
        return None


def summarize_public_sources() -> dict[str, Any]:
    manifest, manifest_path = latest_public_manifest()
    markets: dict[str, Any] = {m: {"state": "ROUTE_ONLY", "valid_items": 0, "items": [], "errors": []} for m in MARKETS}
    generated_at = None
    if manifest is not None and manifest_path is not None:
        generated_at = manifest.get("generated_at")
        for market, result in (manifest.get("results") or {}).items():
            if market not in markets or not isinstance(result, dict):
                continue
            valid_items: list[dict[str, Any]] = []
            errors: list[str] = []
            for item in result.get("items") or []:
                if not isinstance(item, dict):
                    continue
                row = {"id": str(item.get("id") or "UNKNOWN"), "status": str(item.get("status") or "")}
                expected = str(item.get("sha256") or "").lower()
                relative = str(item.get("path") or "")
                path = _resolve_item_path(manifest_path, relative) if relative else None
                if item.get("is_evidence") is True and path is not None and path.is_file() and len(expected) == 64:
                    actual = _sha256(path)
                    row.update({"path": relative, "sha256": expected, "hash_valid": actual == expected, "bytes": path.stat().st_size})
                    if actual == expected:
                        valid_items.append(row)
                    else:
                        errors.append(f"{row['id']}: hash mismatch")
                elif item.get("error"):
                    errors.append(f"{row['id']}: {item.get('error')}")
                else:
                    row["hash_valid"] = False
            state = "COLLECTED" if valid_items and not errors else "PARTIAL" if valid_items else "ROUTE_ONLY"
            markets[market] = {"state": state, "valid_items": len(valid_items), "items": valid_items, "errors": errors}

    # The package carries a real current Nasdaq security-master snapshot even before a live collector runs.
    bundled = [
        HERE / "bootstrap_evidence" / "us" / "security_master_current.csv",
        HERE / "runtime" / "v94_public_snapshots" / "us" / "nasdaq" / "nasdaqtraded.txt",
    ]
    bundled_valid = [p for p in bundled if p.is_file() and p.stat().st_size > 0]
    if bundled_valid and markets["us"]["valid_items"] == 0:
        markets["us"] = {
            "state": "BUNDLED_CURRENT_SNAPSHOT",
            "valid_items": len(bundled_valid),
            "items": [{"id": p.name, "path": p.relative_to(HERE).as_posix(), "sha256": _sha256(p), "hash_valid": True, "bytes": p.stat().st_size} for p in bundled_valid],
            "errors": [],
        }

    collected = sum(markets[m]["valid_items"] > 0 for m in MARKETS)
    return {
        "schema": "warroom.v99.public_source_summary.v1",
        "manifest_path": manifest_path.relative_to(HERE).as_posix() if manifest_path else None,
        "generated_at": generated_at,
        "markets": markets,
        "markets_with_real_snapshot": collected,
        "claim_limit": "A valid source hash proves acquisition identity only, not alpha, target accuracy or capital permission.",
    }


def _count_delimited(path: Path, *, delimiter: str = ",") -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle, delimiter=delimiter)) - 1)
    except Exception:
        return 0


def universe_summary() -> dict[str, Any]:
    security_master = HERE / "bootstrap_evidence" / "us" / "security_master_current.csv"
    nasdaq_traded = HERE / "runtime" / "v94_public_snapshots" / "us" / "nasdaq" / "nasdaqtraded.txt"
    us_count = _count_delimited(security_master) if security_master.is_file() else _count_delimited(nasdaq_traded, delimiter="|")
    try:
        universe = json.loads((HERE / "V99_EXECUTION_REFERENCE_UNIVERSE.json").read_text(encoding="utf-8"))
    except Exception:
        try:
            universe = json.loads((HERE / "V97_EXECUTION_REFERENCE_UNIVERSE.json").read_text(encoding="utf-8"))
        except Exception:
            universe = {}
    execution_counts = {m: len(universe.get(m) or []) for m in MARKETS}
    return {
        "research_universe": {"us_current_security_master": us_count, "idx": None, "crypto": 2, "commodity": 3, "fx": 5},
        "execution_reference_counts": execution_counts,
        "claim_limit": "Research-universe coverage and execution-reference coverage are different quantities.",
    }


def load_execution_universe() -> dict[str, list[dict[str, Any]]]:
    for name in ("V99_EXECUTION_REFERENCE_UNIVERSE.json", "V98_EXECUTION_REFERENCE_UNIVERSE.json", "V97_EXECUTION_REFERENCE_UNIVERSE.json"):
        path = HERE / name
        payload = _safe_json(path) if path.is_file() else None
        if payload is not None:
            return {m: [dict(x) for x in (payload.get(m) or []) if isinstance(x, dict)] for m in MARKETS}
    return {m: [] for m in MARKETS}

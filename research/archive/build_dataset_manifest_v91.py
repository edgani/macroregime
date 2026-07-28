"""Build a V9.1 predictor manifest with forecast-local point-in-time semantics.

Predictor and outcome manifests are deliberately separate. Paths are stored relative to the
manifest directory so a clean extract can be verified deterministically.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping
import hashlib
import json

FORBIDDEN_ROLES = {"outcome_prices", "outcomes", "realized_returns", "future_returns", "delisting_outcomes"}
HEX_FIELDS = (
    "universe_snapshot_hash",
    "security_master_hash",
    "global_trial_ledger_hash",
    "data_dictionary_hash",
    "data_custodian_receipt_hash",
    "source_license_receipt_hash",
    "code_snapshot_hash",
    "model_hash",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    root = root.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"evidence file must live under manifest directory: {resolved}") from exc


def build(
    *,
    manifest_path: str | Path,
    market: str,
    model_id: str,
    decision_times_file: str | Path,
    role_files: Mapping[str, str | Path],
    history_start: str,
    history_end: str,
    receipts: Mapping[str, str],
    minimum_rows: Mapping[str, int] | None = None,
) -> dict:
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    root.mkdir(parents=True, exist_ok=True)
    market = str(market).lower().strip()
    overlap = FORBIDDEN_ROLES & {str(role).lower() for role in role_files}
    if overlap:
        raise ValueError(f"outcome role prohibited in predictor manifest: {sorted(overlap)}")
    decision_path = Path(decision_times_file).resolve()
    if not decision_path.exists():
        raise FileNotFoundError(decision_path)
    roles = {}
    minimum_rows = dict(minimum_rows or {})
    for role, raw_path in role_files.items():
        path = Path(raw_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        roles[str(role)] = {
            "path": _relative(path, root),
            "sha256": sha256(path),
            "minimum_rows": int(minimum_rows.get(str(role), 1)),
        }
    receipt_payload = {field: str(receipts.get(field) or "").lower() for field in HEX_FIELDS}
    payload = {
        "schema": "warroom.v91.predictor_manifest.v1",
        "market": market,
        "model_id": str(model_id),
        "evidence_mode": "REAL_POINT_IN_TIME_BLIND",
        "synthetic_data": False,
        "test_fixture": False,
        "decision_times_file": _relative(decision_path, root),
        "decision_times_hash": sha256(decision_path),
        "history_start": history_start,
        "history_end": history_end,
        "roles": roles,
        **receipt_payload,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload["manifest_hash"] = hashlib.sha256(canonical).hexdigest()
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="JSON build specification")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = build(manifest_path=args.out, **spec)
    print(json.dumps(result, indent=2))

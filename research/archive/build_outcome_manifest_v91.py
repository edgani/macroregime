"""Build a separate outcome manifest. Outcomes never enter the predictor manifest."""
from __future__ import annotations
from pathlib import Path
from typing import Mapping
import hashlib
import json


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"outcome file must live under manifest directory: {path.resolve()}") from exc


def build(*, manifest_path: str | Path, market: str, outcome_files: Mapping[str, str | Path], forecast_seal_hash: str, custodian_hash: str) -> dict:
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    root.mkdir(parents=True, exist_ok=True)
    roles = {}
    for role, raw in outcome_files.items():
        path = Path(raw).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        roles[str(role)] = {"path": _relative(path, root), "sha256": sha256(path)}
    payload = {
        "schema": "warroom.v91.outcome_manifest.v1",
        "market": str(market).lower().strip(),
        "roles": roles,
        "forecast_seal_hash": str(forecast_seal_hash).lower(),
        "custodian_hash": str(custodian_hash).lower(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["manifest_hash"] = hashlib.sha256(canonical).hexdigest()
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

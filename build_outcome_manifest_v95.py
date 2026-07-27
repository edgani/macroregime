"""Build an outcome manifest cryptographically bound to predictor data and forecast seal."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Mapping

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _relative(path: Path, root: Path) -> str:
    path = path.resolve(); root = root.resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("outcome files must live below the manifest directory") from exc


def build(*, manifest_path: str | Path, market: str, outcome_files: Mapping[str, str | Path],
          predictor_manifest: str | Path, forecast_seal: str | Path, custodian_hash: str) -> dict:
    manifest_path = Path(manifest_path).resolve(); root = manifest_path.parent
    root.mkdir(parents=True, exist_ok=True)
    predictor_manifest = Path(predictor_manifest).resolve(); forecast_seal = Path(forecast_seal).resolve()
    custodian_hash = str(custodian_hash).lower()
    if not HEX64.fullmatch(custodian_hash) or custodian_hash == "0" * 64:
        raise ValueError("invalid custodian_hash")
    roles = {}
    for role, raw in outcome_files.items():
        file = Path(raw).resolve()
        if not file.is_file():
            raise FileNotFoundError(file)
        roles[str(role)] = {"path": _relative(file, root), "sha256": sha256(file)}
    payload = {
        "schema": "warroom.v95.outcome_manifest.v1",
        "market": str(market).lower().strip(),
        "roles": roles,
        "predictor_manifest_hash": sha256(predictor_manifest),
        "forecast_seal_hash": sha256(forecast_seal),
        "custodian_hash": custodian_hash,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["manifest_hash"] = hashlib.sha256(canonical).hexdigest()
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

"""V9.2 provider onboarding and 5-market route readiness.

This module does not certify market edge. It converts vague blockers into exact missing
files and verifies that every supplied file exists, is non-empty and has a SHA-256 identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def resolve_value(name: str, env: dict[str, str]) -> str:
    return os.getenv(name, "").strip() or env.get(name, "").strip()


def audit_item(name: str, env: dict[str, str]) -> dict[str, Any]:
    raw = resolve_value(name, env)
    if not raw:
        return {"id": name, "ready": False, "reason": "path not configured"}
    path = Path(raw).expanduser()
    if not path.exists():
        return {"id": name, "ready": False, "path": str(path), "reason": "file or directory not found"}
    if path.is_file():
        size = path.stat().st_size
        if size <= 0:
            return {"id": name, "ready": False, "path": str(path), "reason": "empty file"}
        return {"id": name, "ready": True, "path": str(path.resolve()), "bytes": size, "sha256": sha256_file(path)}
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        return {"id": name, "ready": False, "path": str(path), "reason": "directory contains no files"}
    aggregate = hashlib.sha256()
    total = 0
    for file in files:
        digest = sha256_file(file)
        aggregate.update(str(file.relative_to(path)).encode("utf-8"))
        aggregate.update(digest.encode("ascii"))
        total += file.stat().st_size
    return {"id": name, "ready": True, "path": str(path.resolve()), "files": len(files), "bytes": total, "tree_sha256": aggregate.hexdigest()}


def audit_market(market: str, spec: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    for name in spec.get("required", []):
        items[name] = audit_item(name, env)
    alternatives = []
    for group_name, bundles in (spec.get("required_any_of") or {}).items():
        bundle_results = []
        for bundle in bundles:
            results = [audit_item(name, env) for name in bundle.get("files", [])]
            bundle_results.append({"id": bundle.get("id"), "ready": bool(results) and all(x["ready"] for x in results), "items": results})
        alternatives.append({"group": group_name, "ready": any(x["ready"] for x in bundle_results), "bundles": bundle_results})
    optional = {name: audit_item(name, env) for name in spec.get("optional", [])}
    required_ready = all(x["ready"] for x in items.values()) if items else True
    alternative_ready = all(x["ready"] for x in alternatives) if alternatives else True
    data_route_ready = required_ready and alternative_ready
    return {
        "market": market,
        "data_route_ready": data_route_ready,
        "required": items,
        "required_any_of": alternatives,
        "optional": optional,
        "next_stage": "BUILD_PIT_PANEL" if data_route_ready else "ACQUIRE_OR_EXPORT_MISSING_DATA",
        "trading_ready": False,
        "claim_limit": "Provider readiness is not historical proof or trading permission."
    }


def run(registry_path: Path, env_path: Path) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    env = load_env_file(env_path)
    markets = [audit_market(name, spec, env) for name, spec in registry["routes"].items()]
    return {
        "schema": "warroom.v92.provider_readiness.v1",
        "markets": markets,
        "data_route_ready_markets": sum(int(x["data_route_ready"]) for x in markets),
        "historical_blind_proven_markets": 0,
        "limited_production_ready_markets": 0,
        "fully_proven_markets": 0,
        "capital_permission": "BLOCKED",
        "claim_limit": "5/5 provider readiness only starts proof production; it never substitutes for sealed outcomes and real fills."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="V92_PROVIDER_ROUTE_REGISTRY.json")
    parser.add_argument("--env", default="V92_PROVIDER_ONBOARDING.env")
    parser.add_argument("--out", default="V92_CURRENT_5_OF_5_AUDIT.json")
    args = parser.parse_args()
    result = run(Path(args.registry), Path(args.env))
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

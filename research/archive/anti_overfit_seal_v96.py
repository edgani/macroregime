"""Create a V9.6 anti-overfit seal after validation selection and before lockbox outcomes."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from causal_research_lifecycle_v96 import replay


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create(*, market: str, candidate_id: str, lifecycle: Path, protocol: Path,
           model_hash: str, code_snapshot_hash: str, data_contract_hash: str,
           sealed_at: str | None = None) -> dict[str, Any]:
    lifecycle_state = replay(lifecycle)
    if not lifecycle_state.get("valid"):
        raise ValueError("lifecycle is invalid")
    candidates: set[str] = set()
    for program in (lifecycle_state.get("research") or {}).values():
        if str(program.get("market")) == market:
            candidates.update(program.get("candidates", {}).keys())
    if candidate_id not in candidates:
        raise ValueError("selected candidate is not registered for this market")
    for name, value in {
        "model_hash": model_hash,
        "code_snapshot_hash": code_snapshot_hash,
        "data_contract_hash": data_contract_hash,
    }.items():
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"{name} must be lowercase SHA-256")
    body = {
        "schema": "warroom.v96.anti_overfit_seal.v1",
        "market": market,
        "selected_candidate_id": candidate_id,
        "global_trial_count": len(candidates),
        "sealed_at": sealed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "model_hash": model_hash,
        "code_snapshot_hash": code_snapshot_hash,
        "data_contract_hash": data_contract_hash,
        "lifecycle_hash": sha(lifecycle),
        "protocol_hash": sha(protocol),
    }
    body["seal_hash"] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, choices=["us", "idx", "commodity", "fx", "crypto"])
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--model-hash", required=True)
    parser.add_argument("--code-snapshot-hash", required=True)
    parser.add_argument("--data-contract-hash", required=True)
    parser.add_argument("--sealed-at")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = create(
        market=args.market, candidate_id=args.candidate_id,
        lifecycle=Path(args.lifecycle), protocol=Path(args.protocol),
        model_hash=args.model_hash, code_snapshot_hash=args.code_snapshot_hash,
        data_contract_hash=args.data_contract_hash, sealed_at=args.sealed_at,
    )
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

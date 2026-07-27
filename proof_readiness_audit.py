"""Scan local real-evidence manifests and report exact all-market blockers."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from market_data_admission import admit_manifest

MARKETS = ("us", "idx", "commodity", "fx", "crypto")


def audit(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    by_market: dict[str, Any] = {}
    for market in MARKETS:
        manifest = root / market / "dataset_manifest.json"
        if manifest.exists():
            result = admit_manifest(manifest)
        else:
            result = {
                "schema": "warroom.v89.data_admission.v1",
                "valid": False,
                "market": market,
                "errors": ["dataset_manifest.json not found"],
                "roles_required": [],
                "roles_audited": {},
            }
        by_market[market] = result
    admitted = [market for market, result in by_market.items() if result.get("valid")]
    return {
        "schema": "warroom.v89.real_data_readiness.v1",
        "markets_admitted": admitted,
        "admitted_count": len(admitted),
        "all_markets_admitted": len(admitted) == len(MARKETS),
        "capital_permission": "BLOCKED",
        "by_market": by_market,
        "claim_limit": "Even five admitted datasets are not trading proof; blind projection, realized fills, drawdown, profit factor and independent review must still pass.",
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="runtime/market_evidence")
    parser.add_argument("--out", default="V89_CURRENT_REAL_DATA_AUDIT.json")
    args = parser.parse_args()
    result = audit(args.root)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

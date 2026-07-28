"""V9.1 readiness audit: data-plane progress, historical proof readiness and trading proof are distinct."""
from __future__ import annotations
from pathlib import Path
import argparse
import json

from market_data_admission_v91 import admit_manifest
from data_route_resolver_v90 import resolve

MARKETS = ("us", "idx", "commodity", "fx", "crypto")


def _manifest(root: Path, market: str) -> Path:
    return root / market / "predictor_manifest.json"


def audit(root: Path) -> dict:
    rows = []
    for market in MARKETS:
        path = _manifest(root, market)
        if not path.exists():
            bootstrap_roles = []
            bootstrap_dir = Path(__file__).with_name("bootstrap_evidence") / market
            if bootstrap_dir.exists():
                if any(bootstrap_dir.glob("security_master*.csv")):
                    bootstrap_roles.append("security_master")
            route = resolve(market, {"model_id": f"{market.upper()}_CORE", "roles": bootstrap_roles})
            rows.append({
                "market": market,
                "stage": "BOOTSTRAP_ONLY" if bootstrap_roles else "COLLECTION_NOT_RUN",
                "predictor_manifest": str(path),
                "bootstrap_roles": bootstrap_roles,
                "collection_admitted": False,
                "historical_proof_ready": False,
                "trading_ready": False,
                "missing_core_roles": route["missing_core"],
                "errors": ["predictor_manifest.json not found"],
            })
            continue
        result = admit_manifest(path)
        stage = "HISTORICAL_PROOF_READY" if result.get("historical_proof_ready") else "DATA_COLLECTION_ADMITTED" if result.get("collection_admitted") else "BLOCKED_DATA"
        rows.append({
            "market": market,
            "stage": stage,
            "predictor_manifest": str(path),
            "bootstrap_roles": [],
            "collection_admitted": bool(result.get("collection_admitted")),
            "historical_proof_ready": bool(result.get("historical_proof_ready")),
            "trading_ready": False,
            "missing_core_roles": result.get("missing_core_roles", []),
            "errors": result.get("errors", []),
            "admission_hash": result.get("admission_hash"),
        })
    payload = {
        "schema": "warroom.v91.current_readiness_audit.v1",
        "markets": rows,
        "collection_admitted_markets": sum(int(row["collection_admitted"]) for row in rows),
        "historical_proof_ready_markets": sum(int(row["historical_proof_ready"]) for row in rows),
        "trading_ready_markets": sum(int(row["trading_ready"]) for row in rows),
        "diagnosis": "V9.1 makes the proof plane executable, but no market is promoted without real PIT panels, sealed outcomes and actual fills.",
        "capital_permission": "BLOCKED",
    }
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="runtime/market_evidence")
    parser.add_argument("--out", default="V91_CURRENT_READINESS_AUDIT.json")
    args = parser.parse_args()
    result = audit(Path(args.root))
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

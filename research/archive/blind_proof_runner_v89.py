"""Run one exact-scope market proof from real point-in-time files.

This runner never creates trades, fills, or outcomes. It only adjudicates supplied immutable data.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json

import pandas as pd

from market_data_admission import admit_manifest
from market_projection_benchmark import evaluate as evaluate_projection
from realized_performance_gate import evaluate as evaluate_performance
from promotion_gate_v89 import evaluate as evaluate_promotion


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*, manifest: Path, projections: Path, trades: Path, equity: Path, receipt: Path) -> dict[str, Any]:
    admission = admit_manifest(manifest)
    errors: list[str] = []
    if not admission.get("valid"):
        errors.append("real dataset admission failed")
    try:
        projection_frame = pd.read_csv(projections)
        projection_result = evaluate_projection(projection_frame)
    except Exception as exc:
        projection_result = {"valid": False, "errors": [f"projection load/evaluation failed: {type(exc).__name__}: {exc}"], "all_markets_pass": False}
    try:
        performance_result = evaluate_performance(pd.read_csv(trades), pd.read_csv(equity))
    except Exception as exc:
        performance_result = {"all_risk_profit_gates_pass": False, "errors": [f"performance load/evaluation failed: {type(exc).__name__}: {exc}"]}
    try:
        receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    except Exception as exc:
        receipt_payload = {}
        errors.append(f"receipt load failed: {type(exc).__name__}: {exc}")
    receipt_payload["data_admission_pass"] = bool(admission.get("valid"))
    receipt_payload["data_admission_hash"] = admission.get("admission_hash")
    receipt_payload["dataset_manifest_hash"] = _sha(manifest)
    if not projection_result.get("all_markets_pass"):
        errors.append("projection benchmark did not pass for all represented markets")
    if not performance_result.get("all_risk_profit_gates_pass"):
        errors.append("realized risk/profit gate did not pass")
    promotion = evaluate_promotion(receipt_payload)
    if not promotion.get("eligible"):
        errors.append("promotion receipt rejected")
    result = {
        "schema": "warroom.v89.blind_proof_run.v1",
        "trading_ready": not errors,
        "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if not errors else "BLOCKED",
        "data_admission": admission,
        "projection_benchmark": projection_result,
        "realized_performance": performance_result,
        "promotion": promotion,
        "errors": sorted(set(errors)),
        "claim_limit": "Eligibility applies only to the exact market, universe, direction, horizon and execution method in the signed receipt.",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--projections", required=True)
    parser.add_argument("--trades", required=True)
    parser.add_argument("--equity", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = run(manifest=Path(args.manifest), projections=Path(args.projections), trades=Path(args.trades), equity=Path(args.equity), receipt=Path(args.receipt))
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["trading_ready"] else 2)


if __name__ == "__main__":
    main()

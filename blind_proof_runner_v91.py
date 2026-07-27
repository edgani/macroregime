"""Run one exact-market blind proof using separate predictor and outcome custody."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json

import pandas as pd

from market_data_admission_v91 import admit_manifest
from outcome_data_admission_v91 import admit as admit_outcomes
from market_projection_benchmark_v91 import evaluate_exact_market
from realized_performance_gate import evaluate as evaluate_performance
from promotion_gate_v89 import evaluate as evaluate_promotion


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*, predictor_manifest: Path, outcome_manifest: Path, projections: Path, trades: Path, equity: Path, receipt: Path, forecast_seal: Path) -> dict[str, Any]:
    predictor = admit_manifest(predictor_manifest)
    errors: list[str] = []
    if not predictor.get("historical_proof_ready"):
        errors.append("predictor data not historical-blind-proof ready")
    try:
        seal = json.loads(forecast_seal.read_text(encoding="utf-8"))
        seal_hash = _sha(forecast_seal)
        if seal.get("predictor_manifest_hash") != _sha(predictor_manifest):
            errors.append("forecast seal predictor manifest mismatch")
    except Exception as exc:
        seal = {}
        seal_hash = ""
        errors.append(f"forecast seal invalid: {type(exc).__name__}: {exc}")
    outcomes = admit_outcomes(outcome_manifest, predictor_manifest_hash=_sha(predictor_manifest), forecast_seal_hash=seal_hash)
    if not outcomes.get("valid"):
        errors.append("sealed outcome admission failed")
    market = str(predictor.get("market") or "")
    try:
        projection_result = evaluate_exact_market(pd.read_csv(projections), market)
    except Exception as exc:
        projection_result = {"valid": False, "market_pass": False, "errors": [f"projection load/evaluation failed: {type(exc).__name__}: {exc}"]}
    try:
        performance_result = evaluate_performance(pd.read_csv(trades), pd.read_csv(equity))
    except Exception as exc:
        performance_result = {"all_risk_profit_gates_pass": False, "errors": [f"performance load/evaluation failed: {type(exc).__name__}: {exc}"]}
    try:
        receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    except Exception as exc:
        receipt_payload = {}
        errors.append(f"receipt load failed: {type(exc).__name__}: {exc}")
    receipt_payload.update({
        "data_admission_pass": bool(predictor.get("historical_proof_ready")),
        "data_admission_hash": predictor.get("admission_hash"),
        "dataset_manifest_hash": _sha(predictor_manifest),
    })
    if not projection_result.get("market_pass"):
        errors.append("exact-market projection benchmark failed")
    if not performance_result.get("all_risk_profit_gates_pass"):
        errors.append("realized risk/profit gate failed")
    promotion = evaluate_promotion(receipt_payload)
    if not promotion.get("eligible"):
        errors.append("promotion receipt rejected")
    result = {
        "schema": "warroom.v91.blind_proof_run.v1",
        "market": market,
        "trading_ready": not errors,
        "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if not errors else "BLOCKED",
        "predictor_data_admission": predictor,
        "outcome_data_admission": outcomes,
        "projection_benchmark": projection_result,
        "realized_performance": performance_result,
        "promotion": promotion,
        "errors": sorted(set(errors)),
        "claim_limit": "Eligibility applies only to the exact market, universe, direction, horizon and execution method in the signed receipt.",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictor-manifest", required=True)
    parser.add_argument("--outcome-manifest", required=True)
    parser.add_argument("--projections", required=True)
    parser.add_argument("--trades", required=True)
    parser.add_argument("--equity", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--forecast-seal", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = run(
        predictor_manifest=Path(args.predictor_manifest), outcome_manifest=Path(args.outcome_manifest),
        projections=Path(args.projections), trades=Path(args.trades), equity=Path(args.equity),
        receipt=Path(args.receipt), forecast_seal=Path(args.forecast_seal),
    )
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["trading_ready"] else 2)

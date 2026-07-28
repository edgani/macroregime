"""Cryptographically bound exact-market proof runner for War Room OS V9.5.

The V9.1 runner could evaluate supplied CSVs while separately accepting manually asserted receipt
metrics and placeholder-looking artifact hashes. V9.5 binds every supplied artifact to the forecast
seal and signed receipt, matches forecast IDs across predictor decisions/projections/outcomes/trades,
and recomputes the metrics used for promotion.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from market_data_admission_v91 import admit_manifest
from market_projection_benchmark_v91 import evaluate_exact_market
from outcome_data_admission_v95 import admit as admit_outcomes
from proof_receipts import verify_receipt
from realized_performance_gate_v95 import evaluate as evaluate_performance

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")
    return raw


def _time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(dt.timezone.utc)


def _valid_hash(value: Any) -> bool:
    text = str(value or "").lower()
    return bool(HEX64.fullmatch(text) and text != "0" * 64)


def _decision_ids(predictor_manifest: Path) -> set[str]:
    manifest = _load_json(predictor_manifest)
    relative = str(manifest.get("decision_times_file") or "")
    root = predictor_manifest.parent.resolve(); path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise ValueError("decision_times_file escapes manifest root")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "forecast_id" not in frame:
        raise ValueError("decision file missing forecast_id")
    ids = set(frame["forecast_id"].astype(str))
    if len(ids) != len(frame):
        raise ValueError("duplicate forecast_id in decision file")
    return ids


def _artifact_bindings(receipt: dict[str, Any]) -> dict[str, str]:
    raw = receipt.get("runtime_bindings") or {}
    return {str(k): str(v).lower() for k, v in raw.items()} if isinstance(raw, dict) else {}


def _metric_close(actual: Any, claimed: Any, *, tolerance: float = 1e-9) -> bool:
    try:
        a = float(actual); c = float(claimed)
        return math.isfinite(a) and math.isfinite(c) and abs(a - c) <= tolerance * max(1.0, abs(a), abs(c))
    except (TypeError, ValueError):
        return False


def _crosscheck_signed_metrics(receipt: dict[str, Any], projection: dict[str, Any], performance: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    proof = receipt.get("proof") or {}
    claimed_projection = proof.get("projection_metrics") or {}
    actual_projection = projection.get("metrics") or {}
    projection_pairs = {
        "count": "count",
        "months": "months",
        "regimes": "regimes",
        "median_abs_log_error": "median_expected_abs_log_error",
        "error_improvement_vs_no_change": "error_improvement_vs_no_change",
        "interval_coverage": "interval_coverage",
        "scenario_brier": "scenario_brier",
        "direction_accuracy": "direction_accuracy",
        "projected_realized_rank_correlation": "spearman_projected_vs_realized_return",
        "severe_loss_rate": "severe_loss_rate",
    }
    for signed_name, actual_name in projection_pairs.items():
        if not _metric_close(actual_projection.get(actual_name), claimed_projection.get(signed_name)):
            reasons.append(f"signed projection metric mismatch: {signed_name}")
    claimed_realized = proof.get("realized_performance_metrics") or {}
    trade = performance.get("trade_ledger") or {}
    equity = performance.get("equity_ledger") or {}
    realized_pairs = {
        "closed_trades": trade.get("trades"),
        "months": trade.get("months"),
        "regimes": trade.get("regimes"),
        "real_net_profit_factor": trade.get("real_net_profit_factor"),
        "profit_factor_bootstrap_95pct_lower": (trade.get("profit_factor_bootstrap") or {}).get("lower_95"),
    }
    for name, actual in realized_pairs.items():
        if not _metric_close(actual, claimed_realized.get(name)):
            reasons.append(f"signed realized metric mismatch: {name}")
    if not _metric_close(equity.get("normal_max_drawdown"), proof.get("oos_max_drawdown")):
        reasons.append("signed drawdown mismatch: oos_max_drawdown")
    if not _metric_close(equity.get("stress_max_drawdown"), proof.get("stress_max_drawdown")):
        reasons.append("signed drawdown mismatch: stress_max_drawdown")
    return reasons


def run(*, predictor_manifest: Path, outcome_manifest: Path, projections: Path, trades: Path,
        equity: Path, signed_receipt: Path, forecast_seal: Path, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    errors: list[str] = []
    try:
        hashes = {
            "predictor_manifest": _sha(predictor_manifest),
            "outcome_manifest": _sha(outcome_manifest),
            "projections": _sha(projections),
            "trades": _sha(trades),
            "equity": _sha(equity),
            "forecast_seal": _sha(forecast_seal),
        }
    except Exception as exc:
        result = {
            "schema": "warroom.v95.blind_proof_run.v1", "market": None,
            "trading_ready": False, "capital_permission": "BLOCKED",
            "errors": [f"required artifact unavailable: {type(exc).__name__}: {exc}"],
            "claim_limit": "Missing or unreadable artifacts always fail closed.",
        }
        result["run_hash"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return result

    predictor = admit_manifest(predictor_manifest)
    if not predictor.get("historical_proof_ready"):
        errors.append("predictor data not historical-blind-proof ready")
    market = str(predictor.get("market") or "")

    try:
        seal = _load_json(forecast_seal)
        if seal.get("schema") != "warroom.v95.forecast_seal.v1":
            errors.append("forecast seal schema mismatch")
        recorded_seal_hash = str(seal.get("seal_hash") or "").lower()
        unhashed_seal = {k: v for k, v in seal.items() if k != "seal_hash"}
        actual_seal_hash = hashlib.sha256(json.dumps(unhashed_seal, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if recorded_seal_hash != actual_seal_hash:
            errors.append("forecast seal self-hash mismatch")
        expected = {
            "predictor_manifest_hash": hashes["predictor_manifest"],
            "projection_file_hash": hashes["projections"],
        }
        for field, value in expected.items():
            if str(seal.get(field) or "").lower() != value:
                errors.append(f"forecast seal mismatch: {field}")
        for field in ("model_hash", "code_snapshot_hash", "global_trial_ledger_hash"):
            if not _valid_hash(seal.get(field)):
                errors.append(f"forecast seal invalid: {field}")
        sealed_at = _time(seal.get("sealed_at"))
        if sealed_at > now:
            errors.append("forecast seal is future-dated")
    except Exception as exc:
        seal = {}; sealed_at = now
        errors.append(f"forecast seal invalid: {type(exc).__name__}: {exc}")

    outcomes = admit_outcomes(
        outcome_manifest,
        predictor_manifest_hash=hashes["predictor_manifest"],
        forecast_seal_hash=hashes["forecast_seal"],
    )
    if not outcomes.get("valid"):
        errors.append("sealed outcome admission failed")
    try:
        outcome_meta = _load_json(outcome_manifest)
        generated_at = _time(outcome_meta.get("generated_at"))
        if generated_at < sealed_at:
            errors.append("outcome manifest predates forecast seal")
    except Exception as exc:
        errors.append(f"outcome chronology invalid: {type(exc).__name__}: {exc}")

    try:
        projections_frame = pd.read_csv(projections)
        projection_result = evaluate_exact_market(projections_frame, market)
    except Exception as exc:
        projections_frame = pd.DataFrame()
        projection_result = {"valid": False, "market_pass": False, "errors": [f"projection load/evaluation failed: {type(exc).__name__}: {exc}"]}
    if not projection_result.get("market_pass"):
        errors.append("exact-market projection benchmark failed")

    try:
        trades_frame = pd.read_csv(trades); equity_frame = pd.read_csv(equity)
        performance_result = evaluate_performance(trades_frame, equity_frame, now=now, expected_market=market)
    except Exception as exc:
        trades_frame = pd.DataFrame()
        performance_result = {"all_risk_profit_gates_pass": False, "errors": [f"performance load/evaluation failed: {type(exc).__name__}: {exc}"]}
    if not performance_result.get("all_risk_profit_gates_pass"):
        errors.append("realized risk/profit gate failed")

    try:
        decision_ids = _decision_ids(predictor_manifest)
        projection_ids = set(projections_frame["forecast_id"].astype(str))
        outcome_ids = set(outcomes.get("forecast_ids") or [])
        trade_ids = set(trades_frame["forecast_id"].astype(str))
        if not projection_ids or projection_ids != decision_ids:
            errors.append("projection forecast IDs do not exactly match predictor decisions")
        if outcome_ids != projection_ids:
            errors.append("outcome forecast IDs do not exactly match projections")
        if not trade_ids.issubset(projection_ids):
            errors.append("trade ledger contains unknown forecast IDs")
    except Exception as exc:
        errors.append(f"forecast identity reconciliation failed: {type(exc).__name__}: {exc}")

    try:
        receipt = _load_json(signed_receipt)
        component = f"{market}_bottleneck_price_projection_v95"
        receipt_verification = verify_receipt(receipt, component=component, claim_type="CAPITAL_PERMISSION", now=now)
        if not receipt_verification.get("valid"):
            errors.append("signed proof receipt rejected")
        bindings = _artifact_bindings(receipt)
        for role, digest in hashes.items():
            if bindings.get(role) != digest:
                errors.append(f"signed runtime binding mismatch: {role}")
        errors.extend(_crosscheck_signed_metrics(receipt, projection_result, performance_result))
    except Exception as exc:
        receipt_verification = {"valid": False, "reasons": [f"receipt error: {type(exc).__name__}: {exc}"]}
        errors.append("signed proof receipt unreadable")

    result = {
        "schema": "warroom.v95.blind_proof_run.v1",
        "market": market or None,
        "trading_ready": not errors,
        "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if not errors else "BLOCKED",
        "predictor_data_admission": predictor,
        "outcome_data_admission": outcomes,
        "projection_benchmark": projection_result,
        "realized_performance": performance_result,
        "signed_receipt_verification": receipt_verification,
        "artifact_hashes": hashes,
        "errors": sorted(set(errors)),
        "claim_limit": "Eligibility is exact-market, exact-universe, exact-horizon, exact-account and exact-execution-source only.",
    }
    result["run_hash"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("predictor_manifest", "outcome_manifest", "projections", "trades", "equity", "signed_receipt", "forecast_seal", "out"):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    result = run(
        predictor_manifest=Path(args.predictor_manifest), outcome_manifest=Path(args.outcome_manifest),
        projections=Path(args.projections), trades=Path(args.trades), equity=Path(args.equity),
        signed_receipt=Path(args.signed_receipt), forecast_seal=Path(args.forecast_seal),
    )
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["trading_ready"] else 2)


if __name__ == "__main__":
    main()

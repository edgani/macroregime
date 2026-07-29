"""Evaluation report generator for the V95/V101 prospective shadow ledger.

Reads an append-only shadow ledger (warroom.v95.shadow_ledger_record.v1), joins
FORECAST -> ORDER_INTENT -> SHADOW_FILL -> OUTCOME, and emits an honest evaluation
report. A ledger with no matured outcomes produces an explicit
PROSPECTIVE_EVIDENCE_PENDING report — never a profitability claim.

Usage:
    python tools/paper_trading/evaluate_shadow_ledger.py [ledger_path] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shadow_execution_ledger_v95 import verify  # noqa: E402
from warroom.research.contamination_gates import evaluate_contamination  # noqa: E402

MANDATE_FORECAST_FIELDS = (
    "forecast_id", "trial_id", "market", "security_id", "generated_at", "decision_at",
    "outcome_start", "outcome_end", "horizon", "direction", "probability",
    "expected_return", "lower_confidence_bound_return", "expected_shortfall",
    "opportunity_cost_estimate", "target_price", "invalidation", "regime",
    "git_commit", "model_hash", "data_snapshot_hash", "code_snapshot_hash",
    "global_trial_ledger_hash", "projection_file_hash",
)
MANDATE_OUTCOME_FIELDS = (
    "forecast_id", "horizon_end", "realized_return",
    "max_adverse_excursion", "max_favorable_excursion", "outcome_source_hash",
    "exit_reason", "later_revision_impact",
)


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_evaluation(ledger_path: str | Path) -> dict:
    path = Path(ledger_path)
    verification = verify(path)
    rows = _rows(path)
    forecasts = {r["forecast_id"]: r for r in rows if r.get("record_type") == "FORECAST"}
    fills = {r["forecast_id"]: r for r in rows if r.get("record_type") == "SHADOW_FILL"}
    outcomes = {r["forecast_id"]: r for r in rows if r.get("record_type") == "OUTCOME"}

    field_coverage = {
        "forecast_fields_present": sorted({f for r in forecasts.values() for f in MANDATE_FORECAST_FIELDS if f in r}),
        "forecast_fields_missing_any": sorted({f for f in MANDATE_FORECAST_FIELDS if any(f not in r for r in forecasts.values())}),
        "outcome_fields_present": sorted({f for r in outcomes.values() for f in MANDATE_OUTCOME_FIELDS if f in r}),
        "outcome_fields_missing_any": sorted({f for f in MANDATE_OUTCOME_FIELDS if any(f not in r for r in outcomes.values())}),
    }

    matured = []
    for fid, outcome in outcomes.items():
        forecast = forecasts.get(fid)
        if not forecast:
            continue
        expected = float(forecast.get("expected_return") or 0.0)
        realized = float(outcome["realized_return"])
        direction = forecast.get("direction")
        sign_ok = (expected == 0 and realized == 0) or (expected > 0) == (realized > 0)
        matured.append({
            "forecast_id": fid,
            "market": forecast.get("market"),
            "security_id": forecast.get("security_id"),
            "direction": direction,
            "expected_return": expected,
            "lower_confidence_bound_return": forecast.get("lower_confidence_bound_return"),
            "realized_return": realized,
            "error": realized - expected,
            "abs_error": abs(realized - expected),
            "direction_hit": bool(sign_ok) if direction in ("LONG", "SHORT") else None,
            "max_adverse_excursion": float(outcome["max_adverse_excursion"]),
            "max_favorable_excursion": float(outcome["max_favorable_excursion"]),
            "exit_reason": outcome.get("exit_reason"),
            "later_revision_impact": outcome.get("later_revision_impact"),
        })

    n = len(matured)
    hits = [m["direction_hit"] for m in matured if m["direction_hit"] is not None]
    summary = {
        "forecasts_total": len(forecasts),
        "fills_total": len(fills),
        "outcomes_matured": n,
        "unmatured_forecasts": len(forecasts) - n,
        "mean_expected_return": (sum(m["expected_return"] for m in matured) / n) if n else None,
        "mean_realized_return": (sum(m["realized_return"] for m in matured) / n) if n else None,
        "mean_absolute_error": (sum(m["abs_error"] for m in matured) / n) if n else None,
        "direction_hit_rate": (sum(1 for h in hits if h) / len(hits)) if hits else None,
        "directional_observations": len(hits),
    }

    if n == 0:
        evidence_status = "PROSPECTIVE_EVIDENCE_PENDING"
        note = "No matured outcomes. No profitability, calibration, or edge claim is permitted."
    elif n < 30:
        evidence_status = "PROSPECTIVE_EVIDENCE_PENDING"
        note = f"Only {n} matured observations (<30). Descriptive statistics only; no claim permitted."
    else:
        evidence_status = "PROSPECTIVE_SAMPLE_FORMING"
        note = f"{n} matured observations. Still requires pre-registered evaluation window before any claim."

    return {
        "schema": "warroom.paper_trading.evaluation.v1",
        "ledger": str(path),
        "ledger_verification": verification,
        "evidence_status": evidence_status,
        "note": note,
        "capital_permission": "BLOCKED",
        "contamination": evaluate_contamination(path),
        "field_coverage": field_coverage,
        "summary": summary,
        "matured": matured,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", nargs="?", default=str(ROOT / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    report = build_evaluation(args.ledger)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

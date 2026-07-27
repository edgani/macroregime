"""Focused adversarial tests for the V7.8 proof-expansion checkpoint."""
from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import prospective_shadow_v78 as shadow_v78
from prospective_shadow_v78 import (
    ZERO_CAPITAL,
    append_forecast,
    append_outcome,
    summarize_matured,
    verify_forecast_ledger,
    verify_outcome_ledger,
)
from research_v78.data_acquisition.membership_guard_v78 import is_member, validate_membership_file
from research_v78.data_acquisition.pit_data_contract_v78 import validate_dataset

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, ok: bool, detail="") -> None:
    CHECKS.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:4000]})
    print(("PASS" if ok else "FAIL"), name)


def main() -> int:
    valid = validate_dataset(ROOT / "research_v78" / "fixtures" / "pit_contract_valid")
    check("valid_pit_fixture", valid.get("status") == "PASS", {"status": valid.get("status"), "proof_effect": valid.get("proof_effect"), "stats": valid.get("stats")})
    check("pit_fixture_never_grants_capital", valid.get("capital_permission") == "BLOCKED_DATA_VALIDATION_ONLY", valid.get("capital_permission"))

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad"
        shutil.copytree(ROOT / "research_v78" / "fixtures" / "pit_contract_valid", bad)
        rows = (bad / "daily_prices.csv").read_text(encoding="utf-8").splitlines()
        rows.append("PERM_AAA,2020-01-03,10.6,11.2,10.1,11,11,1200000,TEST_FIXTURE,2019-01-01T00:00:00Z")
        (bad / "daily_prices.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        report = validate_dataset(bad)
        codes = {x.get("code") for x in report.get("issues", [])}
        check("tampered_or_lookahead_panel_fails", report.get("status") == "FAIL" and {"MANIFEST_HASH_MISMATCH", "DAILY_PRICE_ROW"}.issubset(codes), sorted(codes))

    membership_path = ROOT / "research_v78" / "data" / "sp500_ticker_start_end.csv"
    membership = validate_membership_file(membership_path)
    check("membership_guard_integrity", membership.get("status") == "PASS" and membership.get("rows") == 1259, membership)
    check("membership_known_positive", is_member(membership_path, "AAPL", "2010-01-04") is True)
    check("membership_gap_not_current_list_backfill", is_member(membership_path, "AAL", "2010-01-04") is False)

    with tempfile.TemporaryDirectory() as tmp:
        forecast_path = Path(tmp) / "forecasts.jsonl"
        outcome_path = Path(tmp) / "outcomes.jsonl"
        now = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
        original_clock = shadow_v78._now
        shadow_v78._now = lambda: now
        common = dict(
            component_id="TEST_COMPONENT_ZERO_CAPITAL",
            market="US",
            instrument="AAA",
            orientation="LONG",
            decision_time_utc=(now - timedelta(seconds=1)).isoformat(),
            data_cutoff_utc=(now - timedelta(minutes=1)).isoformat(),
            horizon_days=1,
            outcome_definition={"metric": "close_to_close_return", "neutral_band": 0.0},
            feature_snapshot_sha256="1" * 64,
            data_snapshot_sha256="2" * 64,
            code_sha256="3" * 64,
            predicted_probability=0.6,
            regime="TEST_REGIME",
            forecast_id="test-current-forecast",
        )
        row = append_forecast(forecast_path, **common)
        check("forecast_append_zero_capital", row.get("capital_permission") == ZERO_CAPITAL, row)
        check("forecast_chain_valid", verify_forecast_ledger(forecast_path).get("valid") is True, verify_forecast_ledger(forecast_path))

        backfill_rejected = False
        try:
            append_forecast(forecast_path, **{**common, "forecast_id": "backfill", "created_at_utc": (now - timedelta(days=2)).isoformat()})
        except ValueError as exc:
            backfill_rejected = "backfilled" in str(exc)
        check("forecast_backfill_rejected", backfill_rejected)

        future_data_rejected = False
        try:
            append_forecast(
                forecast_path,
                **{**common, "forecast_id": "future-data", "data_cutoff_utc": (now + timedelta(minutes=1)).isoformat()},
            )
        except ValueError as exc:
            future_data_rejected = "data_cutoff" in str(exc)
        check("future_data_cutoff_rejected", future_data_rejected)

        decision_backfill_rejected = False
        try:
            append_forecast(
                forecast_path,
                **{**common, "forecast_id": "old-decision", "decision_time_utc": (now - timedelta(days=1)).isoformat(), "data_cutoff_utc": (now - timedelta(days=1, minutes=1)).isoformat()},
            )
        except ValueError as exc:
            decision_backfill_rejected = "decision timestamp" in str(exc)
        check("decision_timestamp_backfill_rejected", decision_backfill_rejected)

        early_outcome_rejected = False
        try:
            append_outcome(
                outcome_path,
                forecast_path,
                forecast_id=row["forecast_id"],
                realized_return=0.01,
                outcome_value=0.01,
                mae=-0.01,
                mfe=0.02,
            )
        except ValueError as exc:
            early_outcome_rejected = "before forecast maturity" in str(exc)
        check("premature_outcome_rejected", early_outcome_rejected)

        # Advance the test clock rather than backfilling a decision timestamp.  Production
        # callers cannot inject this clock; the test monkeypatch proves lawful maturation.
        matured_now = now
        matured = append_forecast(
            forecast_path,
            component_id="TEST_MATURED",
            market="US",
            instrument="BBB",
            orientation="SHORT",
            decision_time_utc=(matured_now - timedelta(seconds=1)).isoformat(),
            data_cutoff_utc=(matured_now - timedelta(minutes=1)).isoformat(),
            horizon_days=1,
            outcome_definition={"metric": "close_to_close_return", "neutral_band": 0.0},
            feature_snapshot_sha256="4" * 64,
            data_snapshot_sha256="5" * 64,
            code_sha256="6" * 64,
            predicted_probability=0.7,
            regime="TEST_REGIME_2",
            forecast_id="test-matured-forecast",
        )
        original_now = shadow_v78._now
        shadow_v78._now = lambda: matured_now + timedelta(days=2)
        try:
            out = append_outcome(
                outcome_path,
                forecast_path,
                forecast_id=matured["forecast_id"],
                realized_return=-0.03,
                outcome_value=-0.03,
                mae=-0.01,
                mfe=0.04,
                outcome_id="test-matured-outcome",
            )
        finally:
            shadow_v78._now = original_now
        check("outcome_append_zero_capital", out.get("capital_permission") == ZERO_CAPITAL, out)
        check("outcome_chain_valid", verify_outcome_ledger(outcome_path, forecast_path).get("valid") is True, verify_outcome_ledger(outcome_path, forecast_path))
        summary = summarize_matured(forecast_path, outcome_path)
        check("prospective_summary_never_auto_promotes", summary.get("automatic_promotion") is False and summary.get("capital_permission") == ZERO_CAPITAL, summary)
        shadow_v78._now = original_clock

    passed = sum(x["status"] == "PASS" for x in CHECKS)
    result = {"status": "PASS" if passed == len(CHECKS) else "FAIL", "passed": passed, "total": len(CHECKS), "checks": CHECKS}
    (ROOT / "V78_FOCUSED_TEST_RESULTS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "passed", "total")}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

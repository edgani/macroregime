"""Tests for reproducible legacy Crashmeter research evidence."""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from eros.research.crashmeter import load_crashmeter_evidence

DATA_DIR = Path(__file__).parents[2] / "data" / "macro_investigation"


def test_legacy_crashmeter_evidence_is_schema_valid_and_reproducible() -> None:
    evidence = load_crashmeter_evidence(DATA_DIR)

    assert len(evidence.score_frame) == 748
    assert evidence.score_frame["date"].is_monotonic_increasing
    assert evidence.score_frame["date"].is_unique
    assert set(evidence.score_frame[["a1", "a2", "b1", "b2", "c"]].stack()) <= {0, 1}
    component_sum = evidence.score_frame[["a1", "a2", "b1", "b2", "c"]].sum(axis=1)
    assert component_sum.equals(evidence.score_frame["score"])
    assert np.isfinite(evidence.score_frame.select_dtypes(include="number")).all().all()
    assert all(len(digest) == 64 for digest in evidence.checksums.values())


def test_outcome_and_risk_windows_are_derived_from_raw_series() -> None:
    evidence = load_crashmeter_evidence(DATA_DIR)

    assert not evidence.outcome_frame.empty
    assert evidence.outcome_frame["drawdown_pct"].le(0.0).all()
    assert np.isfinite(evidence.outcome_frame["drawdown_pct"]).all()
    assert not evidence.risk_windows.empty
    assert evidence.risk_windows["start"].le(evidence.risk_windows["end"]).all()


def test_historical_crisis_claims_fail_closed_when_source_history_is_missing() -> None:
    evidence = load_crashmeter_evidence(DATA_DIR)

    assert evidence.claims_replicable is False
    assert evidence.replication_verdict == "BLOCKED_SOURCE_DATA_INCONSISTENT"
    assert set(evidence.claim_ledger["status"]) == {"UNREPLICABLE"}
    assert set(evidence.claim_ledger["episode"]) == {
        "Dotcom 2000",
        "GFC 2008",
        "COVID 2020",
    }


def test_ancillary_series_and_validation_metadata_are_strictly_validated(tmp_path: Path) -> None:
    copied = tmp_path / "research"
    shutil.copytree(DATA_DIR, copied)
    curve_path = copied / "T10Y3M.csv"
    curve = pd.read_csv(curve_path)
    curve["unexpected"] = 1
    curve.to_csv(curve_path, index=False)

    with pytest.raises(ValueError, match="columns must exactly match"):
        load_crashmeter_evidence(copied)

    shutil.rmtree(copied)
    shutil.copytree(DATA_DIR, copied)
    validation_path = copied / "crashmeter_v3_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["score_rows"] = 1
    validation_path.write_text(json.dumps(validation), encoding="utf-8")

    with pytest.raises(ValueError, match="score_rows"):
        load_crashmeter_evidence(copied)


def test_source_mismatches_and_incomplete_forward_windows_block_replication() -> None:
    evidence = load_crashmeter_evidence(DATA_DIR)

    assert not evidence.source_validation.empty
    assert "FAIL" in set(evidence.source_validation["status"])
    assert "CAPE_SOURCE_UNAVAILABLE" in evidence.validation_issues
    assert evidence.replication_verdict == "BLOCKED_SOURCE_DATA_INCONSISTENT"
    assert "PENDING_FORWARD_WINDOW" in set(evidence.false_alarm_ledger["status"])
    assert "HY_OAS_UNVERIFIED_DAILY_ROWS:1" in evidence.validation_issues
    assert "FALSE_ALARM_OUTCOME_MISMATCH:2024-12-12" in evidence.validation_issues
    assert "FORWARD_WINDOW_INCOMPLETE:2026-02-10" in evidence.validation_issues


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["claims"]["dotcom_2000"].update(
            {"first_score_ge3": "NaT"}
        ),
        lambda value: value["false_alarm_check"][1].update(
            {"worst_forward_12m_pct": float("nan")}
        ),
        lambda value: value["false_alarm_check"][0].update(
            {"real_20pct_crash": "false"}
        ),
        lambda value: value["current"].update({"a2": True}),
        lambda value: value.update({"score_rows": 748.0}),
        lambda value: value["latest"].update(
            {"date": "2026-07-28T00:00:00"}
        ),
    ),
)
def test_validation_json_rejects_wrong_types_nonfinite_and_non_dates(
    tmp_path: Path,
    mutation: object,
) -> None:
    copied = tmp_path / "research"
    shutil.copytree(DATA_DIR, copied)
    validation_path = copied / "crashmeter_v3_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert callable(mutation)
    mutation(validation)
    validation_path.write_text(json.dumps(validation), encoding="utf-8")

    with pytest.raises(ValueError):
        load_crashmeter_evidence(copied)

"""Global trial counter tests (R9.2): chain verification, prospective
registration, structural hashing, content binding, fail-closed gates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom.research import trial_counter


def test_real_registries_verify_clean():
    """Both historical registries must verify: full hash recompute, not just linkage."""
    report = trial_counter.verify_all()
    assert report["valid"], report
    # 5 RESET0-era + 1 prospective V101 policy registration (flat),
    # 4 R7/R8-era (wrapped).
    assert report["total_entries"] == 10
    by_format = {r["format"]: r for r in report["registries"]}
    assert by_format["flat"]["valid"] and by_format["flat"]["entries"] == 6
    assert by_format["wrapped"]["valid"] and by_format["wrapped"]["entries"] == 4
    assert trial_counter.is_registered("V101_FIXED_ACTION_POLICY")


def test_register_appends_and_chain_stays_valid(tmp_path):
    registry = tmp_path / "trials.jsonl"
    first = trial_counter.register("TRIAL_A", {"operator": "momentum", "lookback": 20}, registry=registry)
    second = trial_counter.register("TRIAL_B", {"operator": "reversal", "lookback": 5}, registry=registry)
    assert second["previous_hash"] == first["entry_hash"]
    report = trial_counter.verify_flat(registry)
    assert report["valid"] and report["entries"] == 2
    assert trial_counter.is_registered("TRIAL_A", (registry,))
    assert not trial_counter.is_registered("TRIAL_C", (registry,))


def test_duplicate_registration_refused(tmp_path):
    registry = tmp_path / "trials.jsonl"
    trial_counter.register("TRIAL_A", {"x": 1}, registry=registry)
    with pytest.raises(trial_counter.DuplicateTrialRegistration):
        trial_counter.register("TRIAL_A", {"x": 2}, registry=registry)
    # The refused write must not have appended anything.
    assert trial_counter.verify_flat(registry)["entries"] == 1


def test_require_registered_fail_closed(tmp_path):
    registry = tmp_path / "trials.jsonl"
    with pytest.raises(trial_counter.TrialNotRegistered):
        trial_counter.require_registered("MISSING", (registry,))
    trial_counter.register("PRESENT", {"x": 1}, registry=registry)
    trial_counter.require_registered("PRESENT", (registry,))  # must not raise


def test_structural_hash_ignores_key_order_but_not_content():
    a = trial_counter.structural_hash({"operator": "mom", "lookback": 20, "field": "close"})
    b = trial_counter.structural_hash({"field": "close", "lookback": 20, "operator": "mom"})
    c = trial_counter.structural_hash({"operator": "mom", "lookback": 21, "field": "close"})
    assert a == b
    assert a != c


def test_content_hash_binds_registry_state(tmp_path):
    registry = tmp_path / "trials.jsonl"
    before = trial_counter.content_hash((registry,))
    trial_counter.register("TRIAL_A", {"x": 1}, registry=registry)
    after = trial_counter.content_hash((registry,))
    assert before != after
    assert after == trial_counter.content_hash((registry,))  # deterministic


def test_tamper_is_detected(tmp_path):
    registry = tmp_path / "trials.jsonl"
    trial_counter.register("TRIAL_A", {"x": 1}, registry=registry)
    lines = registry.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["outcome"] = "PROMOTED"  # silent edit
    registry.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    report = trial_counter.verify_flat(registry)
    assert not report["valid"]
    assert any("entry_hash mismatch" in e for e in report["errors"])

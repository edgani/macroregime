"""Anti-contamination promotion controls for quantitative research."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eros.research.contamination import ContaminationPolicy, load_contamination_policy

EXPECTED_CONTROLS = {
    "no_runtime_llm_truth_authority",
    "schema_isolated_frontier_model",
    "chronologically_clean_text_model",
    "orchestrator_as_of_token",
    "point_in_time_universe",
    "append_only_global_trial_counter",
    "structural_strategy_hash",
    "cpcv_purge_embargo",
    "probability_backtest_overfitting",
    "deflated_probabilistic_sharpe",
    "realistic_total_cost_model",
    "one_shot_sealed_lockbox",
    "prospective_paper_journal",
    "narrative_firewall",
    "signed_human_approval",
}


def _policy_path() -> Path:
    return Path(__file__).parents[2] / "config" / "contamination_policy.yaml"


def test_article_failure_modes_are_explicit_live_capital_gates() -> None:
    policy = load_contamination_policy(_policy_path())

    assert {item.control_id for item in policy.controls} == EXPECTED_CONTROLS
    assert policy.live_capital_ready is False
    assert policy.unresolved_blockers
    assert str(policy.source.url) == "https://www.writeverso.now/p/quant"


def test_policy_rejects_duplicate_control_ids() -> None:
    policy = load_contamination_policy(_policy_path())
    payload = policy.model_dump(mode="json")
    payload["controls"].append(payload["controls"][0])

    with pytest.raises(ValidationError, match="must be unique"):
        ContaminationPolicy.model_validate(payload)


def test_only_fully_enforced_blocking_policy_can_be_live_ready() -> None:
    policy = load_contamination_policy(_policy_path())
    payload = policy.model_dump(mode="json")
    for control in payload["controls"]:
        if control["blocks_live_capital"]:
            control["status"] = "ENFORCED"

    validated = ContaminationPolicy.model_validate(payload)

    assert validated.live_capital_ready is True
    assert validated.unresolved_blockers == []


def test_policy_rejects_forged_nonblocking_control_and_invalid_calendar_date() -> None:
    policy = load_contamination_policy(_policy_path())
    forged = policy.model_dump(mode="json")
    forged["controls"][0]["blocks_live_capital"] = 0
    with pytest.raises(ValidationError):
        ContaminationPolicy.model_validate(forged)

    malformed_date = policy.model_dump(mode="json")
    malformed_date["source"]["accessed_at"] = "2026-99-99"
    with pytest.raises(ValidationError):
        ContaminationPolicy.model_validate(malformed_date)

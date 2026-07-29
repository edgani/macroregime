"""warroom/research/contamination_gates.py — LLM contamination gates as code (R9.3).

Origin: the V84 anti-overfit audit revoked the V82/V83 confirmatory claim
because LLM contamination controls failed (memorized public factors, named
semantics visible to the model, incomplete trial ledger, no post-cutoff
holdout, no prospective outcomes). Those controls were a manual audit
checklist. This module makes them executable: every evaluation report can
carry a contamination verdict computed from the ledger and registry
themselves, plus a signed operator attestation for the gates that cannot be
automated.

Two tiers (defense-in-depth; a pass is necessary, never sufficient):

- SHADOW tier: required for prospective shadow evidence to count at all.
- CAPITAL tier: required before any capital discussion. Attestation gates
  that are false here keep capital BLOCKED by construction.

Gate kinds:
- verified: computed from the ledger / trial registry / policy dates. No
  trust required; recompute to check.
- attested: declared by the operator in config/contamination_policy.json.
  Recorded honestly; false attestations block the corresponding tier.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
DEFAULT_POLICY = HERE / "config" / "contamination_policy.json"

from shadow_execution_ledger_v95 import verify as verify_shadow_ledger  # noqa: E402
from warroom.research import trial_counter  # noqa: E402

UTC = dt.timezone.utc


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(UTC)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_policy(policy_path: Path) -> dict[str, Any] | None:
    try:
        policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return policy if isinstance(policy, dict) and policy.get("schema") == "warroom.contamination_policy.v1" else None


def _gate(gate_id: str, tier: str, kind: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"id": gate_id, "tier": tier, "kind": kind, "passed": bool(passed), "evidence": evidence}


def evaluate_contamination(
    ledger_path: str | Path,
    *,
    policy_path: str | Path = DEFAULT_POLICY,
    registries: Iterable[Path] = trial_counter.DEFAULT_REGISTRIES,
) -> dict[str, Any]:
    """Compute the contamination verdict for one shadow ledger."""
    ledger_path = Path(ledger_path)
    registries = tuple(registries)
    rows = _read_rows(ledger_path)
    forecasts = [r for r in rows if r.get("record_type") == "FORECAST"]
    outcomes = [r for r in rows if r.get("record_type") == "OUTCOME"]
    policy = _load_policy(Path(policy_path))
    attestations = (policy or {}).get("attestations") or {}

    gates: list[dict[str, Any]] = []

    # --- verified gates -------------------------------------------------
    ledger_verification = verify_shadow_ledger(ledger_path)
    gates.append(
        _gate(
            "ledger_append_only_valid",
            "shadow",
            "verified",
            bool(ledger_verification.get("valid")),
            f"rows={ledger_verification.get('rows', 0)} errors={len(ledger_verification.get('errors') or [])}",
        )
    )

    evidence_ok = all(
        r.get("evidence_class") == "PROSPECTIVE_SHADOW_ONLY" and r.get("capital_permission") == "BLOCKED"
        for r in forecasts
    ) and all(
        _parse(o["horizon_end"]) >= _parse(f["outcome_end"])
        for o in outcomes
        for f in forecasts
        if f["forecast_id"] == o["forecast_id"]
    )
    gates.append(
        _gate(
            "prospective_outcomes_primary",
            "shadow",
            "verified",
            bool(forecasts) and evidence_ok,
            "all forecasts PROSPECTIVE_SHADOW_ONLY + capital BLOCKED; outcomes never precede horizon",
        )
    )

    registry_report = trial_counter.verify_all(registries)
    trial_ids = {str(f.get("trial_id")) for f in forecasts if f.get("trial_id")}
    known_ids = trial_counter.registered_trial_ids(registries)
    unregistered = sorted(trial_ids - known_ids)
    gates.append(
        _gate(
            "complete_global_trial_ledger",
            "shadow",
            "verified",
            bool(registry_report["valid"]) and not unregistered,
            f"registries valid={registry_report['valid']} entries={registry_report['total_entries']} "
            f"unregistered_trials={unregistered or 'none'}",
        )
    )

    # Registration must precede the first OUTCOME of each trial (evaluation,
    # not necessarily the forecast, is what must be prospectively counted).
    prospective_ok = True
    prospective_evidence = []
    for trial_id in sorted(trial_ids):
        trial_outcomes = [o for o in outcomes if _trial_of(o, forecasts) == trial_id]
        if not trial_outcomes:
            prospective_evidence.append(f"{trial_id}: no outcomes yet, registration precedes evaluation")
            continue
        reg_time = _registration_time(trial_id, registries)
        first_outcome = min(str(o.get("recorded_at")) for o in trial_outcomes)
        ok = reg_time is not None and _parse(reg_time) <= _parse(first_outcome)
        prospective_ok = prospective_ok and ok
        prospective_evidence.append(f"{trial_id}: registered={reg_time} first_outcome={first_outcome} ok={ok}")
    gates.append(
        _gate(
            "trial_registration_prospective",
            "shadow",
            "verified",
            prospective_ok,
            "; ".join(prospective_evidence) or "no trials",
        )
    )

    cutoff = (policy or {}).get("assumed_max_model_training_cutoff")
    if cutoff and outcomes:
        min_outcome_end = min(_parse(f["outcome_end"]) for f in forecasts for o in outcomes if o["forecast_id"] == f["forecast_id"])
        cutoff_dt = dt.datetime.fromisoformat(str(cutoff)).replace(tzinfo=UTC)
        gates.append(
            _gate(
                "post_model_cutoff_holdout",
                "capital",
                "verified",
                min_outcome_end > cutoff_dt,
                f"earliest outcome_end={min_outcome_end.date()} > assumed cutoff {cutoff_dt.date()}",
            )
        )
    else:
        gates.append(
            _gate(
                "post_model_cutoff_holdout",
                "capital",
                "verified",
                False,
                "no matured outcomes yet" if policy else "no attestation policy",
            )
        )

    # --- attested gates ---------------------------------------------------
    def attested(gate_id: str, tier: str, required_value: bool) -> dict[str, Any]:
        if policy is None:
            return _gate(gate_id, tier, "attested", False, "UNATTESTED: no contamination policy file")
        value = attestations.get(gate_id)
        return _gate(
            gate_id,
            tier,
            "attested",
            value is required_value,
            f"policy declares {gate_id}={value!r} (required {required_value!r}), attested_by={(policy or {}).get('attested_by')}",
        )

    gates.append(attested("llm_in_signal_path", "shadow", False))
    gates.append(attested("named_factor_semantics_visible_to_llm", "capital", False))
    gates.append(attested("model_blind_signal_ids_used", "capital", True))
    gates.append(attested("independent_data_custodian_used", "capital", True))
    gates.append(attested("low_contamination_asset_holdout", "capital", True))

    shadow_pass = all(g["passed"] for g in gates if g["tier"] == "shadow")
    capital_pass = shadow_pass and all(g["passed"] for g in gates if g["tier"] == "capital")
    return {
        "schema": "warroom.contamination_verdict.v1",
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "ledger": str(ledger_path),
        "gates": gates,
        "shadow_pass": shadow_pass,
        "capital_pass": capital_pass,
        "note": (
            "Pass is necessary, never sufficient. Capital remains BLOCKED until the capital "
            "tier passes AND the prospective sample reaches its pre-registered evaluation window."
        ),
    }


def _trial_of(outcome: Mapping[str, Any], forecasts: list[dict[str, Any]]) -> str | None:
    for f in forecasts:
        if f["forecast_id"] == outcome["forecast_id"]:
            return str(f.get("trial_id"))
    return None


def _registration_time(trial_id: str, registries: Iterable[Path]) -> str | None:
    for path in registries:
        for entry in _read_rows(Path(path)):
            if str(entry.get("trial_id")) == str(trial_id):
                return str(entry.get("timestamp"))
            trial = entry.get("trial")
            if isinstance(trial, Mapping) and str(trial.get("trial_id") or trial.get("id")) == str(trial_id):
                return str(entry.get("recorded_at"))
    return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate LLM contamination gates for a shadow ledger")
    parser.add_argument("ledger", nargs="?", default=str(HERE / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    args = parser.parse_args()
    print(json.dumps(evaluate_contamination(args.ledger, policy_path=args.policy), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

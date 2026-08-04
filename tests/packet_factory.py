"""Shared canonical packet factories for EROS admission tests.

A single source of truth for what a *complete* qualified opportunity packet looks
like. Both unit-level contract tests and end-to-end UI proofs must use this factory
so the positive admission path cannot drift between layers.
"""

from __future__ import annotations


def qualified_packet() -> dict[str, object]:
    """Return a fully lineage-bearing packet that must pass canonical validation."""

    return {
        "opportunity_id": "OPP-TEST-1",
        "asset": "TEST",
        "country": "United States",
        "currency": "USD",
        "decision": "ENTER",
        "sizing": "2% NAV",
        "holding_horizon": "1-3 months",
        "entry_trigger": "Verified causal trigger",
        "invalidation": "Mechanism evidence reverses",
        "valuation_basis": "Point-in-time fundamental target",
        "alternative_action": "Hold cash",
        "mechanism_id": "MECH-TEST-1",
        "thesis_id": "TH-TEST-1",
        "model_id": "MODEL-TEST-1",
        "experiment_id": "EXPERIMENT-TEST-1",
        "data_snapshot_id": "DATA-SNAPSHOT-TEST-1",
        "evidence_ids": ["EVIDENCE-TEST-1", "EVIDENCE-TEST-2"],
        "competing_thesis_probabilities": {
            "null": 0.30,
            "mechanism": 0.50,
            "alternative": 0.20,
        },
        "probability_mechanism_true": 0.60,
        "probability_catalyst_within_horizon": 0.55,
        "probability_not_fully_priced": 0.65,
        "probability_trade_profitable_net": 0.58,
        "expected_value": {
            "gross_ev": 0.08,
            "total_cost": 0.01,
            "net_ev": 0.07,
            "conservative_ev": 0.04,
        },
        "expected_value_input": {
            "probability_win": 0.58,
            "expected_win": 0.20,
            "expected_loss": -0.08571428571428569,
            "costs": {
                "transaction": 0.01,
                "funding": 0.0,
                "borrow": 0.0,
                "tax": 0.0,
                "fx": 0.0,
                "liquidity_impact": 0.0,
            },
            "lower_confidence_adjustment": 0.01,
            "tail_risk_penalty": 0.01,
            "model_uncertainty_penalty": 0.01,
        },
        "costs": {
            "transaction": 0.01,
            "funding": 0.0,
            "borrow": 0.0,
            "tax": 0.0,
            "fx": 0.0,
            "liquidity_impact": 0.0,
        },
        "evidence_families": ["official_macro", "exchange_filing"],
        "missing_evidence": [],
        "evidence_label": "REPLICATED_OOS",
        "decision_snapshot_id": "DEC-TEST-1",
    }


def meters_snapshot(**overrides):
    """Return a minimal live MetersSnapshot for decision-surface tests."""

    from eros.meters.engines import MeterReading
    from eros.meters.snapshot import MetersSnapshot

    def reading(
        meter_id: str,
        label: str,
        value: float,
        *,
        status: str = "LIVE",
        evidence: str = "PROVEN",
        missing: list[str] | None = None,
    ) -> MeterReading:
        return MeterReading(
            meter_id=meter_id,
            label=label,
            value=value,
            status=status,
            components={},
            missing=missing or [],
            as_of="2026-07-31",
            evidence=evidence,
            note="",
        )

    base = {
        "fetched_at": "2026-07-31T00:00:00Z",
        "growth": reading("GROWTH", "Growth composite", 0.62, evidence="PROVEN_CONTEXT"),
        "inflation": reading("INFL", "Inflation composite", 0.48, evidence="PROVEN_CONTEXT"),
        "tilt": {"SPX": 0.25, "TLT": 0.25, "COMM": 0.25, "GLD": 0.25},
        "gold": reading("GOLD", "Gold Meter v2", 0.96),
        "dollar": reading("DOLLAR", "Dollar Meter v1", 0.60),
        "duration": reading("DURATION", "Duration Dial", 0.30),
        "bcm": reading("BCM", "BCM v3.2", 0.40, evidence="PROVEN_SCOPE_LIMITED"),
        "fragility_reading": reading(
            "FRAGILITY", "Fragility axis", 0.97, evidence="PROVEN_SCOPE_LIMITED"
        ),
        "exposure": 1.0,
        "fear_entry": False,
        "blocks": {
            "POLICY": 0.68,
            "STRESS": 0.19,
            "CREDIT": 0.36,
            "REAL": 0.27,
            "LIQ": 0.34,
            "VOL": 0.51,
        },
        "failures": {},
        "checksum_status": "MATCH",
        "checksum_note": "BCM port 0.4042 vs reference 0.388: delta 0.0162, tolerance 0.03.",
    }
    base.update(overrides)
    return MetersSnapshot(**base)

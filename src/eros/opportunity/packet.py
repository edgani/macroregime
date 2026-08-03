"""Strict opportunity packet contracts for research and capital admission."""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from eros.data.identifiers import validate_storage_identifier
from eros.opportunity.ev import (
    CostBreakdown,
    ExpectedValueInput,
    ExpectedValueResult,
    evaluate_expected_value,
)

QUALIFIED_EVIDENCE = {"REPLICATED_OOS", "PROVEN_SCOPE_LIMITED"}
PROBABILITY_FIELDS = {
    "probability_mechanism_true",
    "probability_catalyst_within_horizon",
    "probability_not_fully_priced",
    "probability_trade_profitable_net",
}
SIZING_PATTERN = re.compile(r"\s*(\d+(?:\.\d+)?)%\s*(?:NAV)?\s*")


class OpportunityPacket(BaseModel):
    """Research-stage packet; existence alone does not imply qualification."""

    opportunity_id: str
    asset: str
    direction: str
    country: str
    currency: str
    mechanism_id: str
    thesis_id: str
    competing_thesis_probabilities: dict[str, float]
    probability_mechanism_true: float = Field(ge=0.0, le=1.0)
    probability_catalyst_within_horizon: float = Field(ge=0.0, le=1.0)
    probability_not_fully_priced: float = Field(ge=0.0, le=1.0)
    probability_trade_profitable_net: float = Field(ge=0.0, le=1.0)
    expected_value: ExpectedValueResult
    horizon: str
    evidence_families: list[str]
    missing_evidence: list[str]
    target_basis: str
    invalidation: list[str]
    instrument_mapping: list[str]
    costs: CostBreakdown
    evidence_label: str
    execution_permission: str = "human_approval_required"


class QualifiedOpportunityPacket(BaseModel):
    """Canonical packet admitted to qualified decision surfaces."""

    model_config = ConfigDict(extra="forbid")

    opportunity_id: str
    asset: str
    country: str
    currency: str
    decision: Literal["ENTER", "TRIM"]
    sizing: str
    holding_horizon: str
    entry_trigger: str
    invalidation: str
    valuation_basis: str
    alternative_action: str
    mechanism_id: str
    thesis_id: str
    model_id: str
    experiment_id: str
    data_snapshot_id: str
    evidence_ids: list[str] = Field(min_length=2)
    competing_thesis_probabilities: dict[str, FiniteFloat]
    probability_mechanism_true: FiniteFloat = Field(ge=0.0, le=1.0)
    probability_catalyst_within_horizon: FiniteFloat = Field(ge=0.0, le=1.0)
    probability_not_fully_priced: FiniteFloat = Field(ge=0.0, le=1.0)
    probability_trade_profitable_net: FiniteFloat = Field(ge=0.0, le=1.0)
    expected_value: ExpectedValueResult
    expected_value_input: ExpectedValueInput
    costs: CostBreakdown
    evidence_families: list[str] = Field(min_length=2)
    missing_evidence: list[str]
    evidence_label: Literal["REPLICATED_OOS", "PROVEN_SCOPE_LIMITED"]
    decision_snapshot_id: str

    @field_validator(*PROBABILITY_FIELDS, mode="before")
    @classmethod
    def reject_boolean_probability(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("probabilities cannot be boolean")
        return value

    @field_validator("competing_thesis_probabilities", mode="before")
    @classmethod
    def validate_competing_probability_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if any(isinstance(item, bool) for item in value.values()):
            raise ValueError("competing thesis probabilities cannot be boolean")
        return value

    @field_validator("expected_value", "costs", mode="before")
    @classmethod
    def reject_boolean_numeric_payloads(cls, value: object) -> object:
        if isinstance(value, dict) and any(isinstance(item, bool) for item in value.values()):
            raise ValueError("numeric packet values cannot be boolean")
        return value

    @model_validator(mode="after")
    def enforce_admission_contract(self) -> QualifiedOpportunityPacket:
        text_fields = (
            self.opportunity_id,
            self.asset,
            self.country,
            self.currency,
            self.holding_horizon,
            self.entry_trigger,
            self.invalidation,
            self.valuation_basis,
            self.alternative_action,
            self.mechanism_id,
            self.thesis_id,
            self.model_id,
            self.experiment_id,
            self.data_snapshot_id,
            self.decision_snapshot_id,
        )
        if any(not value.strip() for value in text_fields):
            raise ValueError("qualified packet text fields must be nonblank")
        validate_storage_identifier(self.opportunity_id, "opportunity_id")
        validate_storage_identifier(self.mechanism_id, "mechanism_id")
        validate_storage_identifier(self.thesis_id, "thesis_id")
        validate_storage_identifier(self.model_id, "model_id")
        validate_storage_identifier(self.experiment_id, "experiment_id")
        validate_storage_identifier(self.data_snapshot_id, "data_snapshot_id")
        validate_storage_identifier(self.decision_snapshot_id, "decision_snapshot_id")
        if len(set(self.evidence_ids)) < 2:
            raise ValueError("qualified packet requires independent evidence IDs")
        for evidence_id in self.evidence_ids:
            validate_storage_identifier(evidence_id, "evidence_id")

        sizing_match = SIZING_PATTERN.fullmatch(self.sizing)
        if sizing_match is None or not 0 < float(sizing_match.group(1)) <= 100:
            raise ValueError("sizing must be a bounded positive percent of NAV")

        competing = self.competing_thesis_probabilities
        if not 3 <= len(competing) <= 7:
            raise ValueError("qualified packet requires three to seven competing theses")
        if not any("null" in name.casefold() for name in competing):
            raise ValueError("qualified packet requires a null thesis")
        if not math.isclose(sum(competing.values()), 1.0, abs_tol=1e-6):
            raise ValueError("competing thesis probabilities must sum to one")

        families = [family.strip() for family in self.evidence_families]
        if any(not family for family in families) or len(set(families)) < 2:
            raise ValueError("qualified packet requires independent evidence families")
        if self.missing_evidence:
            raise ValueError("qualified packet cannot retain missing evidence")

        if not math.isclose(
            self.expected_value_input.probability_win,
            self.probability_trade_profitable_net,
            abs_tol=1e-12,
        ):
            raise ValueError("EV win probability must match the qualified probability")
        if self.expected_value_input.costs != self.costs:
            raise ValueError("EV input costs must match the packet cost breakdown")
        recomputed_ev = evaluate_expected_value(self.expected_value_input)
        for field, recomputed in recomputed_ev.model_dump().items():
            submitted = getattr(self.expected_value, field)
            if not math.isclose(submitted, recomputed, abs_tol=1e-9):
                raise ValueError("expected value must match deterministic recomputation")
        if self.expected_value.conservative_ev <= 0:
            raise ValueError("qualified packet requires positive conservative EV")
        if self.expected_value.net_ev > self.expected_value.gross_ev:
            raise ValueError("net EV cannot exceed gross EV")
        if self.expected_value.conservative_ev > self.expected_value.net_ev:
            raise ValueError("conservative EV cannot exceed net EV")
        if not math.isclose(self.expected_value.total_cost, self.costs.total, abs_tol=1e-9):
            raise ValueError("expected-value costs must reconcile to the cost breakdown")
        return self


def validate_qualified_packet(payload: dict[str, Any]) -> QualifiedOpportunityPacket:
    """Validate an untrusted decision-surface payload against the full admission contract."""

    return QualifiedOpportunityPacket.model_validate(payload)

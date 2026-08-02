"""Typed, fixture-backed application state for the EROS decision interface."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

EvidenceLabel = Literal[
    "PROVEN_SCOPE_LIMITED",
    "REPLICATED_OOS",
    "PROSPECTIVE_PENDING",
    "HISTORICALLY_SUPPORTED",
    "CANDIDATE",
    "DATA_DEBT",
    "BUSTED_AS_TESTED",
    "UNKNOWN",
]
FeedStatus = Literal["LIVE", "PARTIAL", "STALE", "NO_DATA"]


class FeedState(BaseModel):
    name: str
    status: FeedStatus
    last_observation: str
    next_release: str
    vintage_status: str
    disabled_components: list[str] = Field(default_factory=list)


class DataHealthState(BaseModel):
    overall_status: FeedStatus
    as_of: str
    live_feeds: int = Field(ge=0)
    total_feeds: int = Field(gt=0)
    feeds: list[FeedState]


class ExecutionState(BaseModel):
    permission: Literal["LOCKED", "HUMAN_REVIEW", "APPROVED"]
    human_approval_required: bool
    reason: str


class RegimeDimension(BaseModel):
    name: str
    state: str
    evidence_label: EvidenceLabel
    uncertainty: Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
    interpretation: str


class ChangeItem(BaseModel):
    title: str
    delta: str
    evidence_label: EvidenceLabel
    decision_impact: str


class ThesisSummary(BaseModel):
    thesis_id: str
    claim: str
    status: str
    posterior: float = Field(ge=0.0, le=1.0)
    interval: str
    change: float
    evidence_label: EvidenceLabel
    missing_evidence: list[str]
    next_observation: str
    decision_permission: str


class CapitalFlow(BaseModel):
    source: str
    target: str
    mechanism: str
    status: EvidenceLabel


class Catalyst(BaseModel):
    date: str
    event: str
    decision: str
    status: str


class DashboardState(BaseModel):
    mode: Literal["SYNTHETIC_DEMO", "LIVE"]
    generated_at: str
    data_health: DataHealthState
    execution: ExecutionState
    regime_dimensions: list[RegimeDimension]
    changes: list[ChangeItem]
    theses: list[ThesisSummary]
    capital_flows: list[CapitalFlow]
    qualified_opportunities: list[dict[str, Any]]
    rejected_opportunities: list[dict[str, str]]
    unknowns: list[str]
    risks: list[str]
    catalysts: list[Catalyst]
    countries: list[dict[str, str]]
    asset_classes: list[dict[str, str]]
    mechanisms: list[dict[str, str]]
    scenarios: list[dict[str, str]]
    acceptance_gates: list[dict[str, str]]

    @property
    def is_synthetic(self) -> bool:
        """Compatibility flag used by the original application contract."""
        return self.mode == "SYNTHETIC_DEMO"

    @property
    def banner(self) -> str:
        """Return the explicit mode banner without hiding execution state."""
        return "SYNTHETIC DEMO — NO LIVE DECISION DATA — EXECUTION LOCKED"

    @property
    def execution_enabled(self) -> bool:
        """Execution is enabled only after explicit approval."""
        return self.execution.permission == "APPROVED"


@lru_cache(maxsize=1)
def load_dashboard_state() -> DashboardState:
    """Load the frozen demo snapshot; missing or invalid data fails closed."""
    root = Path(__file__).resolve().parents[3]
    path = root / "data" / "snapshots" / "demo_dashboard.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DashboardState.model_validate(payload)

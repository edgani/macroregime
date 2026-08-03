"""Typed, fixture-backed application state for the EROS decision interface."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from eros.data.public_markets import (
    EXPECTED_SYMBOLS_BY_GROUP,
    MARKET_GROUPS,
    MarketObservation,
    MarketSnapshot,
)

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
    expected_symbols: list[str] = Field(default_factory=list)
    observed_symbols: list[str] = Field(default_factory=list)
    live_symbols: list[str] = Field(default_factory=list)
    stale_symbols: list[str] = Field(default_factory=list)
    missing_symbols: list[str] = Field(default_factory=list)
    blocking_symbols: list[str] = Field(default_factory=list)


class DataHealthState(BaseModel):
    overall_status: FeedStatus
    as_of: str
    live_feeds: int = Field(ge=0)
    total_feeds: int = Field(gt=0)
    feeds: list[FeedState]


class ExecutionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission: Literal["LOCKED", "HUMAN_REVIEW", "APPROVED"]
    human_approval_required: bool
    reason: str
    approval_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_method: Literal["SIGNED_ATTESTATION"] | None = None
    approval_evidence_checksum: str | None = None

    @model_validator(mode="after")
    def enforce_approval_contract(self) -> ExecutionState:
        if not self.reason.strip():
            raise ValueError("execution reason must be nonblank")
        approval_values = (
            self.approval_id,
            self.approved_by,
            self.approved_at,
            self.approval_method,
            self.approval_evidence_checksum,
        )
        if self.permission == "APPROVED":
            if self.human_approval_required:
                raise ValueError("approved execution cannot retain human approval requirement")
            if any(value is None for value in approval_values):
                raise ValueError("approved execution requires complete approval evidence")
            assert self.approval_id is not None
            assert self.approved_by is not None
            assert self.approved_at is not None
            assert self.approval_evidence_checksum is not None
            if not self.approval_id.strip() or not self.approved_by.strip():
                raise ValueError("approval identity fields must be nonblank")
            if self.approved_at.tzinfo is None or self.approved_at.utcoffset() is None:
                raise ValueError("approval timestamp must be timezone-aware")
            if re.fullmatch(r"[0-9a-fA-F]{64}", self.approval_evidence_checksum) is None:
                raise ValueError("approval evidence checksum must be 64 hexadecimal characters")
        else:
            if not self.human_approval_required:
                raise ValueError("non-approved execution must require human approval")
            if any(value is not None for value in approval_values):
                raise ValueError("non-approved execution cannot retain approval evidence")
        return self


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
    date: date | Literal["UNKNOWN"]
    event: str
    decision: str
    status: str


class DashboardState(BaseModel):
    mode: Literal["SYNTHETIC_DEMO", "PUBLIC_DATA", "LIVE"]
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
    portfolio_positions: list[dict[str, Any]] = Field(default_factory=list)
    market_snapshot: list[MarketObservation] = Field(default_factory=list)
    feed_failures: dict[str, str] = Field(default_factory=dict)

    @property
    def is_synthetic(self) -> bool:
        """Compatibility flag used by the original application contract."""
        return self.mode == "SYNTHETIC_DEMO"

    @property
    def banner(self) -> str:
        """Return the explicit mode banner without hiding execution state."""
        if self.mode == "PUBLIC_DATA":
            return (
                "PUBLIC DATA + FROZEN SYNTHETIC RESEARCH FIXTURE — "
                "CAUSAL REGIME UNKNOWN — EXECUTION LOCKED"
            )
        return "SYNTHETIC DEMO — NO LIVE DECISION DATA — EXECUTION LOCKED"

    @property
    def contamination_policy_ready(self) -> bool:
        """Expose validated policy readiness without allowing caller mutation."""

        return _contamination_policy_ready()

    @property
    def execution_enabled(self) -> bool:
        """Execution is enabled only after explicit approval."""
        return (
            self.execution.permission == "APPROVED"
            and not self.execution.human_approval_required
            and self.contamination_policy_ready
        )


def _contamination_policy_ready() -> bool:
    """Resolve the repository policy at execution time and fail closed."""

    policy_path = Path(__file__).parents[3] / "config" / "contamination_policy.yaml"
    try:
        from eros.research.contamination import load_contamination_policy

        return load_contamination_policy(policy_path).live_capital_ready
    except (ImportError, OSError, ValueError):
        return False


def build_public_data_state(base: DashboardState, snapshot: MarketSnapshot) -> DashboardState:
    """Overlay public observations while preserving decision and evidence locks."""
    payload = base.model_dump(mode="json")
    feed_rows: list[dict[str, Any]] = []
    live_groups = 0
    for group in MARKET_GROUPS:
        rows = [item for item in snapshot.observations if item.market_group == group]
        live_rows = [item for item in rows if item.status == "LIVE"]
        expected_symbols = EXPECTED_SYMBOLS_BY_GROUP[group]
        observed_symbols = {item.symbol for item in rows}
        live_symbols = {item.symbol for item in live_rows}
        stale_symbols = {item.symbol for item in rows if item.status == "STALE"}
        missing_symbols = expected_symbols - observed_symbols
        blocking_symbols = expected_symbols - live_symbols
        complete = expected_symbols <= live_symbols
        if complete:
            live_groups += 1
        if complete:
            status: FeedStatus = "LIVE"
        elif rows:
            status = "PARTIAL" if live_rows else "STALE"
        else:
            status = "NO_DATA"
        latest = max((item.observed_at for item in rows), default="UNKNOWN")
        providers = ", ".join(sorted({item.provider for item in rows})) or "Unavailable"
        feed_rows.append(
            {
                "name": group,
                "status": status,
                "last_observation": latest,
                "next_release": "Provider dependent",
                "vintage_status": providers,
                "disabled_components": [
                    f"No current observation: {symbol}" for symbol in sorted(blocking_symbols)
                ],
                "expected_symbols": sorted(expected_symbols),
                "observed_symbols": sorted(observed_symbols),
                "live_symbols": sorted(live_symbols),
                "stale_symbols": sorted(stale_symbols),
                "missing_symbols": sorted(missing_symbols),
                "blocking_symbols": sorted(blocking_symbols),
            }
        )

    overall: FeedStatus
    if live_groups == len(MARKET_GROUPS) and not snapshot.failures:
        overall = "LIVE"
    elif snapshot.observations:
        overall = "PARTIAL"
    else:
        overall = "NO_DATA"

    payload["mode"] = "PUBLIC_DATA" if snapshot.observations else base.mode
    payload["generated_at"] = snapshot.fetched_at
    payload["data_health"] = {
        "overall_status": overall,
        "as_of": snapshot.fetched_at,
        "live_feeds": live_groups,
        "total_feeds": len(MARKET_GROUPS),
        "feeds": feed_rows,
    }
    payload["market_snapshot"] = [item.model_dump(mode="json") for item in snapshot.observations]
    payload["feed_failures"] = snapshot.failures
    live_symbols = {item.symbol for item in snapshot.observations if item.status == "LIVE"}
    country_groups = {"United States": "US", "Indonesia": "IHSG"}
    for country in payload["countries"]:
        country_group = country_groups.get(country["market"])
        if country_group is not None and EXPECTED_SYMBOLS_BY_GROUP[country_group] & live_symbols:
            country["coverage"] = "LIVE"
            country["access"] = "Public benchmark observation"
    asset_symbols = {
        "equities": {"^GSPC", "^IXIC", "^JKSE"},
        "sovereign_bonds": {"DGS10"},
        "fx": {"USDIDR", "EURUSD", "USDJPY"},
        "commodities": {"GC=F", "CL=F"},
        "crypto": {"BTC-USD", "ETH-USD"},
        "volatility_products": {"^VIX"},
    }
    for asset in payload["asset_classes"]:
        symbols = asset_symbols.get(asset["asset_class"], set())
        if symbols & live_symbols:
            asset["state"] = "OBSERVED"
            asset["coverage"] = "Public benchmark observations"
    if snapshot.observations:
        payload["changes"] = [
            {
                "title": "Public market snapshot refreshed",
                "delta": f"{len(snapshot.observations)} provider-labelled observations loaded",
                "evidence_label": "PROVEN_SCOPE_LIMITED",
                "decision_impact": (
                    "Monitoring only; price observations do not set causal regime state."
                ),
            },
            *payload["changes"],
        ]
    return DashboardState.model_validate(payload)


def _registry_rows(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    universe_path = root / "config" / "universe.yaml"
    universe = yaml.safe_load(universe_path.read_text(encoding="utf-8"))
    countries = [
        {
            "market": str(item["name"]),
            "region": str(item["region"]),
            "classification": str(item["classification"]).title(),
            "currency": str(item["currency"]),
            "coverage": "DATA_DEBT",
            "access": "Registry baseline",
        }
        for item in universe["markets"]
    ]
    asset_classes = [
        {
            "asset_class": str(name),
            "state": "UNKNOWN",
            "coverage": "Registry baseline",
        }
        for name in universe["asset_classes"]
    ]
    return countries, asset_classes


@lru_cache(maxsize=1)
def load_dashboard_state() -> DashboardState:
    """Load the frozen demo snapshot and the complete configured universe."""
    root = Path(__file__).resolve().parents[3]
    path = root / "data" / "snapshots" / "demo_dashboard.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    countries, asset_classes = _registry_rows(root)
    payload["countries"] = countries
    payload["asset_classes"] = asset_classes
    return DashboardState.model_validate(payload)

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Mapping
import math

class EvidenceStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"
    LIVE_ELIGIBLE = "LIVE_ELIGIBLE"

class DecisionStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    PAPER = "PAPER"
    LIVE = "LIVE"

class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

@dataclass(frozen=True)
class ComponentKey:
    component: str
    spec_id: str
    formula_hash: str
    asset: str
    timeframe: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

_FORBIDDEN_RESEARCH_KEYS = {
    "action", "direction", "directional_probability", "probability", "probability_interval",
    "entry", "entry_zone", "stop", "invalidation", "invalidation_price", "target", "targets",
    "size", "sizing", "position_size", "risk_budget", "risk_budget_pct", "net_ev", "setup",
}

def _find_forbidden_keys(value: Any, path: str="component_states") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized=str(key).strip().lower()
            child_path=f"{path}.{key}"
            if normalized in _FORBIDDEN_RESEARCH_KEYS:
                hits.append(child_path)
            hits.extend(_find_forbidden_keys(child, child_path))
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            hits.extend(_find_forbidden_keys(child, f"{path}[{i}]"))
    return hits

@dataclass(frozen=True)
class ResearchObservationTicket:
    observation_id: str
    asset: str
    timeframe: str
    as_of: str
    source_snapshot_hash: str
    component_states: Mapping[str, Any]
    component_evidence: Mapping[str, EvidenceStatus]
    claim_ceiling: str = "DESCRIPTIVE_ONLY"
    reason_codes: tuple[str, ...] = (
        "NO_CALIBRATED_PROBABILITY",
        "NO_EXECUTION_MAP",
    )

    def __post_init__(self) -> None:
        if self.claim_ceiling != "DESCRIPTIVE_ONLY":
            raise ValueError("Research observations must remain DESCRIPTIVE_ONLY")
        hits = _find_forbidden_keys(self.component_states)
        if hits:
            raise ValueError(f"research ticket contains execution fields: {hits}")
        if not self.component_evidence:
            raise ValueError("research ticket requires component evidence bindings")
        allowed={EvidenceStatus.NOT_EVALUATED,EvidenceStatus.RESEARCH_ONLY,EvidenceStatus.REJECTED,EvidenceStatus.UNAVAILABLE}
        bad={k:v for k,v in self.component_evidence.items() if v not in allowed}
        if bad:
            raise ValueError(f"research ticket cannot carry promoted evidence: {bad}")

@dataclass(frozen=True)
class GateResult:
    eligible: bool
    status: DecisionStatus
    reason_codes: tuple[str, ...]

_REQUIRED_ACTIONABLE_EVIDENCE={"mqa","momentum","mtf","decision_policy","portfolio_policy"}

@dataclass(frozen=True)
class DecisionTicket:
    decision_id: str
    asset: str
    timeframe: str
    as_of: str
    status: DecisionStatus
    direction: Direction = Direction.NONE
    probability: float | None = None
    probability_interval: tuple[float, float] | None = None
    entry_zone: tuple[float, float] | None = None
    invalidation_price: float | None = None
    targets: tuple[float, ...] = field(default_factory=tuple)
    risk_budget_pct: float | None = None
    net_ev: float | None = None
    evidence: Mapping[str, EvidenceStatus] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status == DecisionStatus.UNAVAILABLE:
            actionable=(self.direction != Direction.NONE or self.probability is not None or self.probability_interval is not None or
                        self.entry_zone is not None or self.invalidation_price is not None or bool(self.targets) or
                        self.risk_budget_pct is not None or self.net_ev is not None)
            if actionable:
                raise ValueError("UNAVAILABLE decision cannot contain actionable fields")
            return
        required = {
            "probability": self.probability,
            "probability_interval": self.probability_interval,
            "entry_zone": self.entry_zone,
            "invalidation_price": self.invalidation_price,
            "risk_budget_pct": self.risk_budget_pct,
            "net_ev": self.net_ev,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing or not self.targets or self.direction == Direction.NONE:
            raise ValueError(f"actionable decision missing required fields: {missing}")
        numeric=[self.probability,*self.probability_interval,*self.entry_zone,self.invalidation_price,*self.targets,self.risk_budget_pct,self.net_ev]
        if not all(math.isfinite(float(v)) for v in numeric):
            raise ValueError("actionable decision contains non-finite values")
        if not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError("probability must be in [0,1]")
        lo, hi = self.probability_interval
        if not (0.0 <= lo <= self.probability <= hi <= 1.0):
            raise ValueError("invalid probability interval")
        e0, e1 = self.entry_zone
        if e0 <= 0 or e1 < e0:
            raise ValueError("invalid entry zone")
        if any(t <= 0 for t in self.targets):
            raise ValueError("targets must be positive")
        if self.direction == Direction.LONG:
            if self.invalidation_price >= e0 or any(t <= e1 for t in self.targets):
                raise ValueError("LONG execution geometry is inconsistent")
        elif self.direction == Direction.SHORT:
            if self.invalidation_price <= e1 or any(t >= e0 for t in self.targets):
                raise ValueError("SHORT execution geometry is inconsistent")
        if not (0 < self.risk_budget_pct <= 2.0) or self.net_ev <= 0:
            raise ValueError("actionable decisions require bounded positive risk budget and positive net EV")
        missing_evidence=_REQUIRED_ACTIONABLE_EVIDENCE.difference(self.evidence)
        if missing_evidence:
            raise ValueError(f"missing required component evidence: {sorted(missing_evidence)}")
        required_grade = EvidenceStatus.LIVE_ELIGIBLE if self.status == DecisionStatus.LIVE else EvidenceStatus.PAPER_ELIGIBLE
        allowed=(EvidenceStatus.LIVE_ELIGIBLE,) if self.status == DecisionStatus.LIVE else (EvidenceStatus.PAPER_ELIGIBLE,EvidenceStatus.LIVE_ELIGIBLE)
        bad = {k: v for k, v in self.evidence.items() if v not in allowed}
        if bad:
            raise ValueError(f"component evidence does not meet {required_grade}: {bad}")

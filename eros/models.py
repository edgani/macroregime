from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class DataPoint:
    key: str
    value: Any
    as_of: str | None = None
    source: str = 'UNKNOWN'
    freshness: str = 'UNKNOWN'
    confidence: str = 'UNKNOWN'
    note: str = ''

@dataclass
class State:
    state_id: str
    label: str
    value: str
    direction: str = 'MIXED'
    confidence: str = 'UNKNOWN'
    as_of: str | None = None
    evidence: list[str] = field(default_factory=list)
    contradiction: list[str] = field(default_factory=list)
    next_data: list[str] = field(default_factory=list)

@dataclass
class Evidence:
    evidence_id: str
    event_type: str
    claim: str
    verified: bool
    source_class: str
    source: str
    as_of: str
    actor: str = 'UNKNOWN'
    incentive: str = 'UNKNOWN'
    constraint: str = 'UNKNOWN'
    direction: str = 'MIXED'
    magnitude: str = 'UNKNOWN'
    persistence: str = 'UNKNOWN'
    note: str = ''

@dataclass
class Scenario:
    scenario_id: str
    title: str
    status: str
    causal_chain: list[str]
    evidence_ids: list[str]
    confirming: list[str]
    contradicting: list[str]
    next_data: list[str]
    actors: list[str]
    incentives: list[str]
    constraints: list[str]
    probability: float | None = None
    probability_range: list[float] | None = None
    timing: str = 'UNKNOWN_UNCALIBRATED'
    duration: str = 'UNKNOWN_UNCALIBRATED'
    beneficiaries: list[str] = field(default_factory=list)
    losers: list[str] = field(default_factory=list)
    priced_in: str = 'UNKNOWN'
    action: str = 'RESEARCHING'
    caveat: str = ''

@dataclass
class TickerCandidate:
    ticker: str
    market: str
    scenario_id: str
    theme: str
    mechanism: str
    exposure_status: str
    fundamentals_status: str
    balance_sheet_status: str
    valuation_status: str
    priced_in_status: str
    catalyst: str
    evidence_level: str
    action: str
    rank_score: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


def dump(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return asdict(obj)
    return obj

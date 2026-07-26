"""Attach the V7.7 human-readable release contract to dashboard snapshots."""
from __future__ import annotations
from copy import deepcopy
from release_contract_v77 import release_contract


def attach_research_evidence_v77(desk: dict) -> dict:
    out = deepcopy(desk) if isinstance(desk, dict) else {}
    out["release_contract_v77"] = release_contract()
    return out

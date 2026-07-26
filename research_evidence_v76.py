"""Attach the V7.6 final release contract to every dashboard snapshot."""
from __future__ import annotations
from copy import deepcopy
from release_contract_v76 import release_contract


def attach_research_evidence_v76(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["release_contract_v76"] = release_contract()
    return out

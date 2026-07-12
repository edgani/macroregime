from __future__ import annotations
from collections.abc import Mapping
from .contracts import EvidenceStatus, DecisionStatus, GateResult

def evaluate_actionability(
    component_evidence: Mapping[str, EvidenceStatus],
    *,
    requested_status: DecisionStatus,
    data_available: bool,
    data_fresh: bool,
    mtf_ready: bool,
    probability_calibrated: bool,
    net_ev: float | None,
    capacity_ok: bool,
    kill_switch: bool,
) -> GateResult:
    reasons: list[str] = []
    if requested_status == DecisionStatus.UNAVAILABLE:
        reasons.append("NO_ACTION_REQUESTED")
    if not data_available: reasons.append("REQUIRED_DATA_UNAVAILABLE")
    if not data_fresh: reasons.append("STALE_DATA")
    if not mtf_ready: reasons.append("MTF_NOT_READY")
    if not probability_calibrated: reasons.append("PROBABILITY_NOT_CALIBRATED")
    if net_ev is None or net_ev <= 0: reasons.append("NET_EV_NOT_POSITIVE")
    if not capacity_ok: reasons.append("CAPACITY_BLOCKED")
    if kill_switch: reasons.append("KILL_SWITCH_ACTIVE")
    required = EvidenceStatus.LIVE_ELIGIBLE if requested_status == DecisionStatus.LIVE else EvidenceStatus.PAPER_ELIGIBLE
    for component, status in component_evidence.items():
        allowed = (EvidenceStatus.LIVE_ELIGIBLE,) if requested_status == DecisionStatus.LIVE else (EvidenceStatus.PAPER_ELIGIBLE, EvidenceStatus.LIVE_ELIGIBLE)
        if status not in allowed:
            reasons.append(f"SCOPE_EVIDENCE_BLOCKED:{component}:{status.value}")
    eligible = not reasons
    return GateResult(eligible=eligible, status=requested_status if eligible else DecisionStatus.UNAVAILABLE, reason_codes=tuple(reasons))

"""Value-of-waiting comparison."""

import math

from pydantic import BaseModel


class WaitingDecision(BaseModel):
    action: str
    selected_ev: float
    alternatives: dict[str, float]


def compare_waiting(
    trade_now_ev: float, wait_for_evidence_ev: float, alternative_ev: float, cash_ev: float
) -> WaitingDecision:
    values = (trade_now_ev, wait_for_evidence_ev, alternative_ev, cash_ev)
    if any(type(value) not in {int, float} or not math.isfinite(float(value)) for value in values):
        raise ValueError("waiting EV inputs must be finite non-boolean numbers")
    choices = {
        "TRADE_NOW": trade_now_ev,
        "WAIT": wait_for_evidence_ev,
        "ALTERNATIVE": alternative_ev,
        "CASH": cash_ev,
    }
    action = max(choices, key=choices.__getitem__)
    return WaitingDecision(action=action, selected_ev=choices[action], alternatives=choices)

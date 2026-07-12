from __future__ import annotations
from dataclasses import dataclass, asdict
from .hashing import canonical_hash

_ALLOWED={"BULLISH","BEARISH","NEUTRAL","UNAVAILABLE"}

@dataclass(frozen=True)
class MTFResearchState:
    structural: str
    trend: str
    tactical: str
    execution: str
    alignment_score: float
    conflict_codes: tuple[str,...]
    risk_multiplier_ceiling: float
    claim_ceiling: str = "DESCRIPTIVE_ONLY"

    @property
    def state_hash(self) -> str:
        return canonical_hash(asdict(self))


def fuse_mtf(*, structural: str, trend: str, tactical: str, execution: str) -> MTFResearchState:
    vals=[structural,trend,tactical,execution]
    if any(v not in _ALLOWED for v in vals): raise ValueError("invalid MTF state")
    conflicts=[]
    if "UNAVAILABLE" in vals:
        conflicts.append("MTF_INCOMPLETE"); risk=0.0
    elif structural != "NEUTRAL" and trend != "NEUTRAL" and structural != trend:
        conflicts.append("STRUCTURAL_TREND_CONFLICT"); risk=0.0
    elif trend != "NEUTRAL" and tactical != "NEUTRAL" and trend != tactical:
        conflicts.append("HIGHER_TACTICAL_CONFLICT"); risk=0.25
    elif tactical != "NEUTRAL" and execution != "NEUTRAL" and tactical != execution:
        conflicts.append("TACTICAL_EXECUTION_CONFLICT"); risk=0.5
    else:
        risk=1.0
    directional=[v for v in vals if v in ("BULLISH","BEARISH")]
    alignment=0.0 if not directional else max(directional.count("BULLISH"),directional.count("BEARISH"))/len(directional)
    return MTFResearchState(structural,trend,tactical,execution,alignment,tuple(conflicts),risk)

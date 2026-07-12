from __future__ import annotations
from dataclasses import dataclass, asdict
from math import isfinite
from typing import Sequence

from ..hashing import canonical_hash


@dataclass(frozen=True)
class MomentumAxes:
    as_of_index: int
    trend_context: float | None
    acceleration: float | None
    release_rank: float | None
    signed_persistence: float | None
    path_efficiency: float | None
    noise_ratio: float | None
    exhaustion_risk: float | None
    claim_ceiling: str = "DESCRIPTIVE_ONLY"

    @property
    def state_hash(self) -> str:
        return canonical_hash(asdict(self))


def _pct_rank(value: float, history: Sequence[float]) -> float | None:
    clean=[x for x in history if isfinite(x)]
    if not clean: return None
    return sum(x <= value for x in clean)/len(clean)


def compute_momentum_axes(close: Sequence[float], true_range: Sequence[float], *, lookback: int=20, rank_window: int=63) -> list[MomentumAxes]:
    if len(close) != len(true_range): raise ValueError("length mismatch")
    if lookback < 3 or rank_window < 10: raise ValueError("windows too short")
    for v in close:
        if not isfinite(v) or v <= 0: raise ValueError("invalid close")
    out=[]; velocities=[]; tr_means=[]
    for i,c in enumerate(close):
        trend=accel=release=persist=eff=noise=exhaust=None
        if i >= lookback:
            scale=sum(true_range[i-lookback+1:i+1])/lookback
            trend=(c-close[i-lookback])/scale if scale > 0 else 0.0
            path=sum(abs(close[j]-close[j-1]) for j in range(i-lookback+1,i+1))
            eff=0.0 if path == 0 else abs(c-close[i-lookback])/path
            noise=1.0-eff
            signs=[]
            for j in range(i-lookback+1,i+1):
                d=close[j]-close[j-1]
                signs.append(1 if d>0 else -1 if d<0 else 0)
            persist=sum(signs)/lookback
            current_tr=sum(true_range[i-lookback+1:i+1])/lookback
            release=_pct_rank(current_tr,tr_means[max(0,len(tr_means)-rank_window):])
            if velocities:
                accel=trend-velocities[-1]
            if accel is not None:
                strength=min(1.0,abs(trend)/3.0)
                opposing=max(0.0, -accel if trend>0 else accel)
                exhaust=min(1.0, strength * opposing / (1.0+abs(accel)))
            velocities.append(trend); tr_means.append(current_tr)
        out.append(MomentumAxes(i,trend,accel,release,persist,eff,noise,exhaust))
    return out

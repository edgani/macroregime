from __future__ import annotations
from dataclasses import dataclass, asdict
from math import isfinite
from typing import Sequence

from ..hashing import canonical_hash


@dataclass(frozen=True)
class MQABenchmarkState:
    as_of_index: int
    close: float
    atr: float | None
    fixed_lower: float | None
    fixed_upper: float | None
    conformal_lower: float | None
    conformal_upper: float | None
    volatility_percentile: float | None
    volatility_state: str
    prior_range_location: float | None
    claim_ceiling: str = "DESCRIPTIVE_ONLY"

    @property
    def state_hash(self) -> str:
        return canonical_hash(asdict(self))


def _quantile(values: Sequence[float], q: float) -> float:
    clean = sorted(float(v) for v in values if isfinite(v))
    if not clean:
        raise ValueError("quantile requires finite values")
    if len(clean) == 1: return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(pos); hi = min(lo + 1, len(clean) - 1); w = pos - lo
    return clean[lo] * (1 - w) + clean[hi] * w


def true_ranges(high: Sequence[float], low: Sequence[float], close: Sequence[float]) -> list[float]:
    if not (len(high) == len(low) == len(close)):
        raise ValueError("OHLC lengths differ")
    out=[]
    for i,(h,l,c) in enumerate(zip(high,low,close)):
        if not all(isfinite(x) and x > 0 for x in (h,l,c)) or h < l or h < c or l > c:
            raise ValueError("invalid OHLC")
        prev = close[i-1] if i else c
        out.append(max(h-l, abs(h-prev), abs(l-prev)))
    return out


def wilder_atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int=14) -> list[float | None]:
    if period < 2: raise ValueError("period must be >=2")
    tr=true_ranges(high,low,close); out=[None]*len(tr)
    if len(tr) < period: return out
    atr=sum(tr[:period])/period; out[period-1]=atr
    for i in range(period,len(tr)):
        atr=((period-1)*atr+tr[i])/period; out[i]=atr
    return out


def compute_mqa_benchmarks(
    high: Sequence[float], low: Sequence[float], close: Sequence[float], *,
    atr_period: int=14, fixed_multiplier: float=1.0, calibration_window: int=63,
    coverage: float=0.68, location_window: int=20,
) -> list[MQABenchmarkState]:
    if not 0 < coverage < 1: raise ValueError("coverage must be in (0,1)")
    if calibration_window < 10 or location_window < 2: raise ValueError("windows too short")
    atrs=wilder_atr(high,low,close,atr_period); states=[]; residual_ratios=[]
    for i,c in enumerate(close):
        atr=atrs[i]
        fixed_lo=fixed_hi=conf_lo=conf_hi=vol_pct=location=None
        vol_state="UNAVAILABLE"
        if atr is not None and atr > 0:
            fixed_lo=c-fixed_multiplier*atr; fixed_hi=c+fixed_multiplier*atr
            history=[x for x in atrs[max(0,i-calibration_window):i] if x is not None]
            if history:
                vol_pct=sum(x <= atr for x in history)/len(history)
                vol_state="COMPRESSION" if vol_pct <= .25 else "EXPANSION" if vol_pct >= .75 else "NORMAL"
            past=residual_ratios[max(0,len(residual_ratios)-calibration_window):]
            if len(past) >= max(10, calibration_window//3):
                mult=_quantile(past, coverage)
                conf_lo=c-mult*atr; conf_hi=c+mult*atr
        if i >= location_window:
            prior_hi=max(high[i-location_window:i]); prior_lo=min(low[i-location_window:i])
            width=prior_hi-prior_lo
            location=0.5 if width == 0 else (c-prior_lo)/width
        states.append(MQABenchmarkState(i,float(c),atr,fixed_lo,fixed_hi,conf_lo,conf_hi,vol_pct,vol_state,location))
        if i+1 < len(close) and atr is not None and atr > 0:
            residual_ratios.append(abs(close[i+1]-c)/atr)
    return states

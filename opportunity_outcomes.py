from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from opportunity_longitudinal import OUTCOME_HORIZONS, OpportunityMemory


def _series(x: pd.Series) -> pd.Series:
    s=pd.to_numeric(x,errors="coerce").dropna()
    if not isinstance(s.index,pd.DatetimeIndex):
        s.index=pd.to_datetime(s.index,utc=True,errors="coerce")
    elif s.index.tz is None:
        s.index=s.index.tz_localize("UTC")
    else:
        s.index=s.index.tz_convert("UTC")
    return s[~s.index.isna()].sort_index()


def path_outcome(asset: pd.Series, anchor_at: Any, *, benchmark: Optional[pd.Series]=None, sector: Optional[pd.Series]=None,
                 horizon_days: int=91) -> Dict[str, Any]:
    """Calculate path outcomes strictly from observations after an already-frozen event anchor."""
    a=_series(asset)
    if a.empty: return {}
    anchor=pd.Timestamp(anchor_at)
    anchor=anchor.tz_localize("UTC") if anchor.tzinfo is None else anchor.tz_convert("UTC")
    start=a.loc[a.index>=anchor]
    if start.empty: return {}
    p0=float(start.iloc[0]); start_dt=start.index[0]
    end_target=start_dt+pd.Timedelta(days=int(horizon_days))
    path=start.loc[start.index<=end_target]
    completed=bool(a.index.max()>=end_target)
    if path.empty or p0<=0: return {}
    pend=float(path.iloc[-1]); ret=pend/p0-1
    rel=path/p0-1
    mfe=float(rel.max()); mae=float(rel.min()); peak=mfe
    t_mfe=float((rel.idxmax()-start_dt).total_seconds()/86400)
    t_mae=float((rel.idxmin()-start_dt).total_seconds()/86400)
    # drawdown measured from path running peak, relative to that peak.
    dd=(path/path.cummax()-1.0)
    max_dd=float(dd.min())

    def barrier_before(up: float, down: float):
        up_hits=rel[rel>=up]
        dn_hits=rel[rel<=down]
        t_up=up_hits.index[0] if not up_hits.empty else None
        t_dn=dn_hits.index[0] if not dn_hits.empty else None
        success=bool(t_up is not None and (t_dn is None or t_up < t_dn))
        return success, (float((t_up-start_dt).total_seconds()/86400) if t_up is not None else math.nan), (float((t_dn-start_dt).total_seconds()/86400) if t_dn is not None else math.nan)
    b10=barrier_before(0.10,-0.05); b20=barrier_before(0.20,-0.10); b50=barrier_before(0.50,-0.15)

    def linked_return(s: Optional[pd.Series]) -> float:
        if s is None: return math.nan
        q=_series(s)
        q=q.loc[(q.index>=start_dt)&(q.index<=end_target)]
        if len(q)<2 or q.iloc[0]==0: return math.nan
        return float(q.iloc[-1]/q.iloc[0]-1)

    br=linked_return(benchmark); sr=linked_return(sector)
    return {
        "absolute_return":ret,
        "benchmark_return":br,
        "sector_return":sr,
        "relative_return": ret-br if math.isfinite(br) else math.nan,
        "alpha_vs_benchmark": ret-br if math.isfinite(br) else math.nan,
        "alpha_vs_sector": ret-sr if math.isfinite(sr) else math.nan,
        "mfe":mfe,"mae":mae,"time_to_mfe_days":t_mfe,"time_to_mae_days":t_mae,
        "peak_return":peak,"max_drawdown":max_dd,"time_to_peak_days":t_mfe,
        "success_plus10_before_minus5":b10[0],"time_to_plus10_days":b10[1],"time_to_minus5_days":b10[2],
        "success_plus20_before_minus10":b20[0],"time_to_plus20_days":b20[1],"time_to_minus10_days":b20[2],
        "success_plus50_before_minus15":b50[0],"time_to_plus50_days":b50[1],"time_to_minus15_days":b50[2],
        "completed":completed,"horizon_end_utc":end_target.isoformat(),"anchor_price_used":p0,"end_price_used":pend,
    }


def update_from_price_frames(memory: OpportunityMemory, event_id: str, asset_prices: pd.Series,
                             *, benchmark_prices: Optional[pd.Series]=None, sector_prices: Optional[pd.Series]=None) -> Dict[str, Dict[str, Any]]:
    event=memory.get_event(event_id)
    if not event: return {}
    out={}
    for h,days in OUTCOME_HORIZONS.items():
        result=path_outcome(asset_prices,event["first_seen_time"],benchmark=benchmark_prices,sector=sector_prices,horizon_days=days)
        if not result: continue
        memory.upsert_outcome(event_id,h,result,completed=bool(result.get("completed")),horizon_end_utc=result.get("horizon_end_utc"))
        out[h]=result
    return out

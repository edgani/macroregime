from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from opportunity_longitudinal import OUTCOME_HORIZONS, OpportunityMemory


def _utc_ts(x: Any) -> pd.Timestamp:
    t=pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _series(x: pd.Series) -> pd.Series:
    s=pd.to_numeric(x,errors="coerce").dropna().copy()
    idx=pd.to_datetime(s.index,errors="coerce")
    # Preserve timezone when supplied; otherwise treat generic inputs as UTC.
    if isinstance(idx,pd.DatetimeIndex):
        if idx.tz is None: idx=idx.tz_localize("UTC")
        else: idx=idx.tz_convert("UTC")
    s.index=idx
    s=s[~s.index.isna()].sort_index()
    return s[~s.index.duplicated(keep="last")]


def daily_bar_availability(index: pd.DatetimeIndex, market: str) -> pd.DatetimeIndex:
    """Conservatively convert daily bar labels to *when that close was knowable*.

    yfinance-style daily labels are session dates, not information timestamps.  Using
    midnight labels in a PIT audit can leak the same day's close into a pre-close event.
    This mapping intentionally adds a small post-close buffer.  It is a safety clock,
    not an exchange-microsecond timestamp model.
    """
    m=str(market or "")
    raw=pd.DatetimeIndex(index)
    dates=pd.DatetimeIndex([pd.Timestamp(x).date() for x in raw])
    if m=="Crypto":
        # A UTC daily crypto candle labelled D is only complete at D+1 00:00 UTC.
        return pd.DatetimeIndex([pd.Timestamp(d,tz="UTC")+pd.Timedelta(days=1) for d in dates])
    clocks={
        "US":("America/New_York",16,10),
        "IHSG":("Asia/Jakarta",16,20),
        "HK":("Asia/Hong_Kong",16,20),"Hong Kong":("Asia/Hong_Kong",16,20),
        "China":("Asia/Shanghai",15,20),"Taiwan":("Asia/Taipei",13,45),
        "Europe":("Europe/Berlin",17,45),
        "FX":("America/New_York",17,10),"Commodity":("America/New_York",17,10),
        "Index":("America/New_York",16,10),
    }
    tz,hour,minute=clocks.get(m,("UTC",23,59))
    z=ZoneInfo(tz)
    out=[]
    for d in dates:
        local=pd.Timestamp(year=d.year,month=d.month,day=d.day,hour=hour,minute=minute,tz=z)
        out.append(local.tz_convert("UTC"))
    return pd.DatetimeIndex(out)


def normalize_price_observations(series: pd.Series, market: str="", *, daily_labels: bool=False) -> pd.Series:
    s=_series(series)
    if s.empty: return s
    if daily_labels:
        s=s.copy(); s.index=daily_bar_availability(s.index,market)
        s=s[~s.index.duplicated(keep="last")].sort_index()
    return s


def _barrier_before(rel: pd.Series, start_dt: pd.Timestamp, up: float, down: float, completed: bool):
    up_hits=rel[rel>=up]; dn_hits=rel[rel<=down]
    t_up=up_hits.index[0] if not up_hits.empty else None
    t_dn=dn_hits.index[0] if not dn_hits.empty else None
    # Once either barrier is hit, order is known.  If neither is hit and the horizon is
    # still incomplete, UNKNOWN must remain None rather than becoming a false loss.
    if t_up is None and t_dn is None and not completed:
        success=None
    else:
        success=bool(t_up is not None and (t_dn is None or t_up<t_dn))
    return success, (float((t_up-start_dt).total_seconds()/86400) if t_up is not None else math.nan), (float((t_dn-start_dt).total_seconds()/86400) if t_dn is not None else math.nan)


def path_outcome(asset: pd.Series, anchor_at: Any, *, anchor_price: Any=math.nan,
                 benchmark: Optional[pd.Series]=None, sector: Optional[pd.Series]=None,
                 horizon_days: int=91) -> Dict[str, Any]:
    """PIT-safe path outcome from an immutable detection event.

    Key invariants:
    - use the frozen first-seen asset price when available;
    - never use a benchmark observation that occurred after detection as the anchor;
    - use the first observation on/after the requested horizon, so weekends/holidays do
      not silently turn +1D into a same-day 0% return;
    - expose `label_available_at_utc`, the latest timestamp needed to know the label.
    """
    a=_series(asset)
    if a.empty: return {}
    anchor=_utc_ts(anchor_at)
    ap=float(anchor_price) if anchor_price is not None else math.nan
    if not math.isfinite(ap) or ap<=0:
        # Fallback is first observation available after detection.  Its timestamp is
        # explicitly recorded so calibration cannot pretend the price was known earlier.
        after=a.loc[a.index>=anchor]
        if after.empty: return {}
        p0=float(after.iloc[0]); asset_anchor_obs=after.index[0]
    else:
        p0=ap; asset_anchor_obs=anchor
    target=anchor+pd.Timedelta(days=int(horizon_days))
    end_hits=a.loc[a.index>=target]
    completed=not end_hits.empty
    if completed:
        asset_end=end_hits.index[0]
        pend=float(end_hits.iloc[0])
        path=a.loc[(a.index>=anchor)&(a.index<=asset_end)]
    else:
        asset_end=a.index.max()
        if asset_end < anchor: return {}
        path=a.loc[a.index>=anchor]
        if path.empty: return {}
        pend=float(path.iloc[-1])
    # Add frozen anchor as time-zero point if history begins later than detection.
    if p0<=0: return {}
    anchor_series=pd.Series([p0],index=pd.DatetimeIndex([anchor]))
    path=pd.concat([anchor_series,path]).sort_index()
    path=path[~path.index.duplicated(keep="first")]
    rel=path/p0-1.0
    ret=pend/p0-1.0
    mfe=float(rel.max()); mae=float(rel.min())
    t_mfe=float((rel.idxmax()-anchor).total_seconds()/86400)
    t_mae=float((rel.idxmin()-anchor).total_seconds()/86400)
    dd=path/path.cummax()-1.0
    max_dd=float(dd.min())

    b10=_barrier_before(rel,anchor,0.10,-0.05,completed)
    b20=_barrier_before(rel,anchor,0.20,-0.10,completed)
    b50=_barrier_before(rel,anchor,0.50,-0.15,completed)

    required_times=[asset_end] if completed else []
    def linked_return(s: Optional[pd.Series]) -> Tuple[float, Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        if s is None: return math.nan,None,None
        q=_series(s)
        if q.empty: return math.nan,None,None
        # Start price must have been knowable no later than detection.
        starts=q.loc[q.index<=anchor]
        if starts.empty: return math.nan,None,None
        q0=float(starts.iloc[-1]); q0t=starts.index[-1]
        # End is first observation on/after target, exactly like asset horizon handling.
        ends=q.loc[q.index>=target]
        if ends.empty or q0==0: return math.nan,q0t,None
        q1=float(ends.iloc[0]); q1t=ends.index[0]
        return float(q1/q0-1.0),q0t,q1t

    br,b0t,b1t=linked_return(benchmark); sr,s0t,s1t=linked_return(sector)
    if b1t is not None: required_times.append(b1t)
    if s1t is not None: required_times.append(s1t)
    label_available=max(required_times) if completed and required_times else None
    # If a requested relative comparator exists but its endpoint has not matured yet,
    # the relative label is not complete even if the asset endpoint exists.
    relative_complete=completed
    if benchmark is not None and b1t is None: relative_complete=False
    if sector is not None and s1t is None: relative_complete=False
    label_available = max(required_times) if relative_complete and required_times else None

    return {
        "absolute_return":ret,
        "benchmark_return":br,
        "sector_return":sr,
        "relative_return": ret-br if math.isfinite(br) else math.nan,
        "alpha_vs_benchmark": ret-br if math.isfinite(br) else math.nan,
        "alpha_vs_sector": ret-sr if math.isfinite(sr) else math.nan,
        "mfe":mfe,"mae":mae,"time_to_mfe_days":t_mfe,"time_to_mae_days":t_mae,
        "peak_return":mfe,"max_drawdown":max_dd,"time_to_peak_days":t_mfe,
        "success_plus10_before_minus5":b10[0],"time_to_plus10_days":b10[1],"time_to_minus5_days":b10[2],
        "success_plus20_before_minus10":b20[0],"time_to_plus20_days":b20[1],"time_to_minus10_days":b20[2],
        "success_plus50_before_minus15":b50[0],"time_to_plus50_days":b50[1],"time_to_minus15_days":b50[2],
        "completed":completed,
        "relative_completed":relative_complete,
        "horizon_target_utc":target.isoformat(),
        "horizon_end_utc":asset_end.isoformat(),
        "label_available_at_utc":label_available.isoformat() if label_available is not None else None,
        "anchor_price_used":p0,"anchor_at_utc":anchor.isoformat(),"asset_anchor_observation_utc":asset_anchor_obs.isoformat(),
        "asset_end_observation_utc":asset_end.isoformat(),
        "benchmark_anchor_observation_utc":b0t.isoformat() if b0t is not None else None,
        "benchmark_end_observation_utc":b1t.isoformat() if b1t is not None else None,
        "sector_anchor_observation_utc":s0t.isoformat() if s0t is not None else None,
        "sector_end_observation_utc":s1t.isoformat() if s1t is not None else None,
        "end_price_used":pend,
    }


def update_from_price_frames(memory: OpportunityMemory, event_id: str, asset_prices: pd.Series,
                             *, benchmark_prices: Optional[pd.Series]=None, sector_prices: Optional[pd.Series]=None) -> Dict[str, Dict[str, Any]]:
    event=memory.get_event(event_id)
    if not event: return {}
    out={}
    for h,days in OUTCOME_HORIZONS.items():
        result=path_outcome(asset_prices,event["first_seen_time"],anchor_price=event.get("first_seen_price"),benchmark=benchmark_prices,sector=sector_prices,horizon_days=days)
        if not result: continue
        memory.upsert_outcome(event_id,h,result,completed=bool(result.get("completed")),horizon_end_utc=result.get("horizon_end_utc"))
        out[h]=result
    return out

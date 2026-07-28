"""Build row-level point-in-time feature snapshots. Outcome columns are forbidden."""
from __future__ import annotations
import hashlib, json
import pandas as pd

FORBIDDEN={"outcome_price","realized_return","forward_return","peak_return","future_drawdown"}

def build(evidence: pd.DataFrame, forecasts: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    req_e={"instrument_id","field_id","value","available_at","source_id","source_record_id"}
    req_f={"forecast_id","instrument_id","decision_time","model_hash"}
    if req_e-set(evidence): raise ValueError(f"missing evidence columns: {sorted(req_e-set(evidence))}")
    if req_f-set(forecasts): raise ValueError(f"missing forecast columns: {sorted(req_f-set(forecasts))}")
    bad=set(map(str.lower,evidence["field_id"].astype(str))) & FORBIDDEN
    if bad: raise ValueError(f"outcome fields in predictor evidence: {sorted(bad)}")
    ev=evidence.copy(); fc=forecasts.copy()
    ev["available_at"]=pd.to_datetime(ev["available_at"],utc=True,errors="raise")
    fc["decision_time"]=pd.to_datetime(fc["decision_time"],utc=True,errors="raise")
    rows=[]
    for r in fc.itertuples(index=False):
        eligible=ev[(ev.instrument_id==r.instrument_id)&(ev.available_at<=r.decision_time)].copy()
        if eligible.empty: continue
        eligible=eligible.sort_values(["field_id","available_at","source_record_id"]).drop_duplicates("field_id",keep="last")
        for e in eligible.itertuples(index=False):
            rows.append({"forecast_id":r.forecast_id,"instrument_id":r.instrument_id,"decision_time":r.decision_time.isoformat(),"model_hash":r.model_hash,"field_id":e.field_id,"value":e.value,"available_at":e.available_at.isoformat(),"source_id":e.source_id,"source_record_id":e.source_record_id})
    out=pd.DataFrame(rows)
    payload=out.to_json(orient="records",date_format="iso").encode()
    audit={"schema":"warroom.v90.asof_audit.v1","forecast_count":int(fc.forecast_id.nunique()),"snapshot_rows":len(out),"snapshot_hash":hashlib.sha256(payload).hexdigest(),"future_rows":int((pd.to_datetime(out.available_at,utc=True)>pd.to_datetime(out.decision_time,utc=True)).sum()) if len(out) else 0}
    if audit["future_rows"]: raise AssertionError("future rows survived as-of join")
    return out,audit

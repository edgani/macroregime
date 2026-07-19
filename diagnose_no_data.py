from __future__ import annotations
from pathlib import Path
import json
from runtime_store import read_snapshot, read_status, now_iso

HERE=Path(__file__).resolve().parent
snapshot=read_snapshot() or {}
worker=read_status() or {}
report={"generated":now_iso(),"worker":worker,"snapshot_present":bool(snapshot)}
report["markets"]={}
for market,row in (snapshot.get("markets") or {}).items():
    report["markets"][market]={
        "bias":row.get("bias"),
        "loaded":int((row.get("funnel") or {}).get("universe") or 0),
        "setups":len(row.get("setups") or []),
        "interpretation":"NO_SIGNAL" if int((row.get("funnel") or {}).get("universe") or 0)>0 and not row.get("setups") else row.get("bias") or "NO_DATA",
    }
report["liquidity"]=(snapshot.get("systemic") or {}).get("liquidity")
report["planes"]={
    "institutional":(snapshot.get("institutional") or {}).get("overall_state"),
    "derivatives":(snapshot.get("live_intelligence") or {}).get("overall_state"),
    "full_live_data":(snapshot.get("full_live_data") or {}).get("overall_state"),
}
report["tabs"]={}
for tab,cov in ((snapshot.get("full_live_data") or {}).get("tab_coverage") or {}).items():
    failures=[]
    for s in cov.get("provider_statuses") or []:
        if s.get("state") not in {"LIVE","STALE","PARTIAL","NO_SIGNAL","CASH_ONLY"}:
            failures.append({k:s.get(k) for k in ("provider","dataset","state","note")})
    report["tabs"][tab]={"state":cov.get("state"),"core_datasets":cov.get("core_datasets"),"optional_missing":cov.get("optional_missing"),"failures":failures}
report["exact_sources"]=[{k:s.get(k) for k in ("provider","dataset","state","records","note")} for s in (snapshot.get("data_health") or {}).get("sources") or []]
out=HERE/'runtime'/'NO_DATA_DIAGNOSTIC.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps(report,indent=2,default=str))
print(f"\nSaved: {out}")

"""Diagnose five-market readiness without conflating missing collection with model failure."""
from __future__ import annotations
from pathlib import Path
import argparse, json
from data_route_resolver_v90 import resolve

MARKETS=("us","idx","commodity","fx","crypto")

def _load_manifest(root: Path, market: str):
    candidates=[root/market/"dataset_manifest.json",root/f"{market}_dataset_manifest.json"]
    for p in candidates:
        if p.exists():
            try: return p,json.loads(p.read_text(encoding="utf-8")),None
            except Exception as e: return p,None,f"invalid manifest: {e}"
    return candidates[0],None,"dataset_manifest.json not found"

def audit(root: Path)->dict:
    rows=[]
    for market in MARKETS:
        path,m,err=_load_manifest(root,market)
        roles=[] if not m else sorted(set(m.get("roles",{}).keys())|set(m.get("admitted_roles",[])))
        route=resolve(market,{"model_id":(m or {}).get("model_id",f"{market.upper()}_CORE"),"roles":roles})
        if err:
            failure_class="COLLECTION_NOT_RUN" if "not found" in err else "MANIFEST_INVALID"
            empirical_model_failure=False
        elif route["missing_core"]:
            failure_class="CORE_DATA_INCOMPLETE"
            empirical_model_failure=False
        else:
            failure_class="DATA_ADMITTED_AWAITING_BLIND_PROOF"
            empirical_model_failure=False
        rows.append({
            "market":market,
            "manifest_path":str(path),
            "failure_class":failure_class,
            "empirical_model_failure":empirical_model_failure,
            "error":err,
            "present_roles":roles,
            "missing_core_roles":route["missing_core"],
            "optional_addons_present":route["optional_addons_present"],
            "data_admission_possible":route["data_admission_possible"],
            "next_action":("run provider collection and build a signed manifest" if failure_class=="COLLECTION_NOT_RUN" else
                           "acquire/normalize the listed missing core roles" if failure_class=="CORE_DATA_INCOMPLETE" else
                           "freeze model and run forecast-local blind proof")
        })
    return {
        "schema":"warroom.v90.current_route_audit.v1",
        "evidence_root":str(root),
        "data_admitted_markets":sum(int(x["data_admission_possible"]) for x in rows),
        "empirically_failed_models":sum(int(x["empirical_model_failure"]) for x in rows),
        "diagnosis":"0/5 currently means no market data plane was admitted; it is not evidence that five market models were tested and failed.",
        "markets":rows,
        "capital_permission":"BLOCKED"
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--root",default="runtime/market_evidence"); p.add_argument("--out",default="V90_CURRENT_ROUTE_AUDIT.json")
    a=p.parse_args(); result=audit(Path(a.root)); Path(a.out).write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result,indent=2))

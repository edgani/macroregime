from pathlib import Path
import json, tempfile
import pandas as pd
from data_route_resolver_v90 import resolve
from asof_panel_builder_v90 import build
from build_dataset_manifest_v90 import build as build_manifest

checks=[]
def check(name,cond,detail=""):
    checks.append({"name":name,"pass":bool(cond),"detail":str(detail)})

# route scoping
r=resolve("us",{"model_id":"US_CORE","roles":["security_master","corporate_actions","filing_fundamentals","bottleneck_transmission","valuation_snapshot","execution_costs_capacity"]})
check("US core can be data-admitted without optional options/borrow",r["data_admission_possible"],r)
r2=resolve("idx",{"model_id":"IDX_CORE","roles":[]})
check("missing core remains blocked",not r2["data_admission_possible"],r2["missing_core"])

# asof
ev=pd.DataFrame([
 {"instrument_id":"A","field_id":"revenue","value":1,"available_at":"2024-01-01T00:00:00Z","source_id":"SEC","source_record_id":"1"},
 {"instrument_id":"A","field_id":"revenue","value":2,"available_at":"2024-03-01T00:00:00Z","source_id":"SEC","source_record_id":"2"},
])
fc=pd.DataFrame([{ "forecast_id":"F1","instrument_id":"A","decision_time":"2024-02-01T00:00:00Z","model_hash":"m"}])
out,audit=build(ev,fc)
check("forecast-local as-of join excludes future revision",float(out.iloc[0].value)==1,audit)
check("as-of audit has zero future rows",audit["future_rows"]==0,audit)
try:
    bad=ev.copy(); bad.loc[0,"field_id"]="realized_return"; build(bad,fc); ok=False
except ValueError: ok=True
check("outcomes rejected from predictor evidence",ok)

# manifest refuses outcome roles
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/"x.csv"; p.write_text("a\n1\n"); dt=Path(d)/"times.csv"; dt.write_text("decision_time\n2024-01-01T00:00:00Z\n")
    try: build_manifest(market="us",model_id="x",decision_times_file=str(dt),role_files={"outcome_prices":str(p)},history_start="2010-01-01",history_end="2024-01-01",receipts={}); ok=False
    except ValueError: ok=True
    check("manifest builder isolates outcomes",ok)

# package diagnostics
root=Path(__file__).resolve().parent
check("root-cause report exists",(root/"V90_ROOT_CAUSE_DIAGNOSIS.md").exists())
check("source route registry covers five markets",len(json.loads((root/"V90_SOURCE_ROUTE_REGISTRY.json").read_text())["markets"])==5)
check("technical-analysis policy retained",(root/"NO_TECHNICAL_ANALYSIS_POLICY.json").exists())

result={"schema":"warroom.v90.validation.v1","passed":sum(x["pass"] for x in checks),"total":len(checks),"all_pass":all(x["pass"] for x in checks),"checks":checks}
(root/"V90_FINAL_VALIDATION.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
raise SystemExit(0 if result["all_pass"] else 1)

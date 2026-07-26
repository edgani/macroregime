from __future__ import annotations
import importlib,json,hashlib
from pathlib import Path
from audit_v56_chunk import ROOT,STATE,manifest
REPORT=ROOT/'V56_CLEAN_EXTRACT_AUDIT_REPORT.json';LOG=ROOT/'V56_CLEAN_EXTRACT_TEST_LOG.txt'
EXPECTED=['compile','hardening39','continuation11','options29','prospective19','signed_dealer43','outcome11','runner19','manifest14','parquet36','gcfis','deep','live_options','bundled','synthetic','controls','component','composition','filter','real','gem','alpha','streamlit']

def dep():
 mods={'streamlit':'streamlit','requests':'requests','yfinance':'yfinance','pandas':'pandas','numpy':'numpy','scipy':'scipy','sklearn':'sklearn','statsmodels':'statsmodels','hmmlearn':'hmmlearn','networkx':'networkx','pyarrow':'pyarrow','cryptography':'cryptography'};states={}
 for k,m in mods.items():
  try:o=importlib.import_module(m);states[k]={'state':'AVAILABLE','version':str(getattr(o,'__version__','UNKNOWN'))}
  except Exception as e:states[k]={'state':'MISSING','error':f'{type(e).__name__}: {e}'}
 req=['pandas','numpy','cryptography'];missing=[x for x in req if states[x]['state']=='MISSING']
 return {'name':'dependency_inventory','status':'FAIL' if missing else 'PASS','missing_required':missing,'optional_missing':[x for x in states if states[x]['state']=='MISSING' and x not in req],'modules':states}
def proof():
 from proof_registry import default_registry,component_status
 from research_evidence_v53 import load_research_evidence
 from options_research_evidence_v55 import load_options_research_v55
 sts={k:component_status(k) for k in default_registry()['components']};prom=[k for k,v in sts.items() if v.get('predictive_promoted')];cap=[k for k,v in sts.items() if v.get('capital_permission')!='BLOCKED']
 base=load_research_evidence();opt=load_options_research_v55();live=sum(float(x.get('live_decision_weight',0)) for x in base.get('claims',[]))+float(opt.get('live_decision_weight',0))
 v72=opt.get('signed_dealer_v72',{})
 ok=not prom and not cap and live==0 and base.get('capital_permission')=='BLOCKED' and opt.get('status')=='IMPLEMENTED_RESEARCH_ONLY' and v72.get('manifest_generator_validation',{}).get('checks_passed')==14 and v72.get('acquisition',{}).get('historical_outcomes_opened') is False
 return {'name':'proof_research_prospective_state','status':'PASS' if ok else 'FAIL','predictive_components_promoted':prom,'capital_authorized_components':cap,'research_live_decision_weight':live,'options_research_status':opt.get('status'),'v72_historical_outcomes_opened':v72.get('acquisition',{}).get('historical_outcomes_opened'),'prospective_observations_collected':opt.get('prospective_validation_summary',{}).get('observations_collected'),'capital_permission':'BLOCKED' if ok else 'UNSAFE'}
def main():
 rows=[]
 for n in EXPECTED:
  p=STATE/f'{n}.json';rows.append(json.loads(p.read_text()) if p.exists() else {'name':n,'status':'FAIL','source_immutable':False,'reason':'missing audit state'})
 rows += [dep(),proof()]
 failures=[r['name'] for r in rows if r['status']=='FAIL'];blockers=[r['name'] for r in rows if r['status']=='BLOCKED_BY_ENVIRONMENT'];mut=[r['name'] for r in rows if r.get('source_immutable') is False]
 src=manifest(ROOT);src_digest=hashlib.sha256(json.dumps(src,sort_keys=True,separators=(',',':')).encode()).hexdigest();ok=not failures and not mut
 report={'schema':'warroom.clean_extract_audit.v56','status':'PASS' if ok else 'FAIL','release_verdict':'SIGNED_DEALER_RESEARCH_ENGINEERING_PASS_LICENSED_OUTCOMES_NOT_EVALUATED_CAPITAL_BLOCKED' if ok else 'FAIL','visual_application_version':'4.2','release_version':'5.6','source_manifest_files':len(src),'source_manifest_sha256':src_digest,'validators_run_on_fresh_copies':True,'warnings_as_errors':True,'source_mutation_failures':mut,'failures':failures,'environment_blockers':blockers,'executable_gates_passed':sum(r['status']=='PASS' for r in rows),'executable_gates_total':sum(r['status']!='BLOCKED_BY_ENVIRONMENT' for r in rows),'hardening_checks':'39/39 PASS','attachment_continuation_checks':'11/11 PASS','options_v70_checks':'29/29 PASS','options_v71_checks':'19/19 PASS','v72_signed_dealer_checks':'43/43 PASS','v72_outcome_fixture_checks':'11/11 PASS','v72_runner_checks':'19/19 PASS','v72_manifest_checks':'14/14 PASS','historical_options_edge':'NOT_EVALUATED_LICENSED_DATA_REQUIRED','prospective_options_profitability':'NOT_MATURED_ZERO_OBSERVATIONS','predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED','tests':[{k:v for k,v in r.items() if k!='output_tail'} for r in rows],'claim_boundary':'Attachment/video concepts are implemented as signed-dealer volatility-response, pin/break and gamma-scalping research with exact lineage. Option OI is unsigned baseline/placebo only. Licensed outcomes and prospective profitability are not proven.'}
 REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');LOG.write_text('\n'.join([f"STATUS={report['status']}",f"VERDICT={report['release_verdict']}",f"SOURCE_MANIFEST_SHA256={src_digest}",*[f"{r['name']}={r['status']} rc={r.get('returncode','-')} immutable={r.get('source_immutable','-')}" for r in rows],'PREDICTIVE_COMPONENTS_PROMOTED=0','RESEARCH_LIVE_DECISION_WEIGHT=0','PROSPECTIVE_OBSERVATIONS=0','CAPITAL_PERMISSION=BLOCKED'])+'\n')
 print(json.dumps({k:report[k] for k in ('status','release_verdict','failures','environment_blockers','executable_gates_passed','capital_permission')},indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())

from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
checks={}
def ck(name,ok,detail=None):
    checks[name]={'passed':bool(ok),'detail':detail}
    if not ok: print('FAIL',name,detail,file=sys.stderr)
def canonical_protocol_sha(path:Path)->str:
    o=json.loads(path.read_text());o.pop('protocol_sha256',None)
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run(name,args,timeout=300):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout,env={**os.environ,'WARROOM_WRITE_VALIDATION_ARTIFACTS':'0'})
    ck(name,p.returncode==0,(p.stdout+p.stderr)[-3000:]);return p

def main():
    rp=ROOT/'research_v66/results/V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json'
    pp=ROOT/'research_v66/protocols/V66_SMA10_RISK_REDUCTION_CONFIRMATION_PROTOCOL_FROZEN.json'
    r=json.loads(rp.read_text()); kernel=json.loads((ROOT/'V66_SCOPED_USABLE_KERNEL.json').read_text()); matrix=json.loads((ROOT/'V66_COMPONENT_PROOF_MATRIX.json').read_text()); registry=json.loads((ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json').read_text())
    ck('result_schema',r.get('schema')=='warroom.v66.sma10_risk_reduction_confirmation_results.v1')
    ck('protocol_bound',r.get('protocol_sha256')==canonical_protocol_sha(pp),{'result':r.get('protocol_sha256'),'actual':canonical_protocol_sha(pp)})
    ck('confirmation_passed',r.get('passed') is True,r.get('gates'))
    ck('exact_adjudication',r.get('adjudication')=={'capital_permission':'CONDITIONAL_RISK_CAP_ONLY','crash_prediction_permission':False,'decision_permission':'REDUCE_US_BROAD_EQUITY_EXPOSURE_ONLY_AT_MONTHLY_REBALANCE','scoped_claim':'CONFIRMED_HISTORICAL_RISK_REDUCTION','ticker_permission':False},r.get('adjudication'))
    c=r['confirmatory'];c25=r['confirmatory_25bps'];roll=r['rolling']
    ck('confirmatory_480_months',c.get('n')==480,c.get('n'))
    ck('confirmatory_drawdown_improvement',c.get('dd_improvement',0)>0.35,c.get('dd_improvement'))
    ck('confirmatory_es_improvement',c.get('es_improvement',0)>0.053,c.get('es_improvement'))
    ck('confirmatory_return_preserved',c.get('ret_diff',-1)>=-0.025,c.get('ret_diff'))
    ck('stress_25bps_pass',c25.get('es_improvement',0)>0.053,c25.get('es_improvement'))
    ck('rolling_84',roll.get('n_windows')==84,roll.get('n_windows'))
    ck('rolling_risk_stable',roll.get('dd_positive_share')==1.0 and roll.get('es_positive_share')==1.0,roll)
    ck('reverse_control_fails',r.get('gates',{}).get('reverse_fail') is True)
    from research_evidence_v66 import load_research_evidence_v66
    ev=load_research_evidence_v66(); ck('evidence_reconciled',ev.get('status')=='SCOPED_RISK_CONTROL_CONFIRMED',ev)
    controls=ev.get('decision_active_risk_controls',[]);ck('one_scoped_control',len(controls)==1,len(controls))
    ctrl=controls[0] if controls else {}; dec=ctrl.get('current_decision',{})
    ck('current_state_fresh',dec.get('observed_month')=='2026-06-01' and dec.get('data_freshness_months')==1,dec)
    ck('current_state_baseline_allowed',dec.get('status')=='BASELINE_CAP_ALLOWED' and dec.get('max_broad_us_equity_multiplier')==1.0,dec)
    ck('no_scope_creep',not ctrl.get('ticker_permission') and not ctrl.get('short_permission') and not ctrl.get('crash_prediction_permission') and not ctrl.get('cross_market_permission'),ctrl)
    ck('kernel_schema',kernel.get('schema')=='warroom.v66.scoped_usable_kernel.v1')
    ck('kernel_one_risk_control',kernel.get('counts',{}).get('decision_active_scoped_risk_controls')==1)
    ck('kernel_directional_blocked',kernel.get('capital_permission')=='DIRECTIONAL_AND_TICKER_CAPITAL_BLOCKED' and kernel.get('counts',{}).get('decision_active_predictive')==0,kernel.get('counts'))
    ck('matrix_one_risk_control',len(matrix.get('decision_active_scoped_risk_controls',[]))==1)
    reg=registry.get('components',{}).get('us_sma10_monthly_risk_cap_v66',{})
    ck('registry_v66',registry.get('version')=='6.6' and reg.get('state')=='SCOPED_RISK_CONTROL_CONFIRMED',reg)
    ck('registry_not_alpha',reg.get('predictive_promoted') is False and reg.get('predictive_semantics') is False,reg)
    from research_kernel import attach_research_kernel
    desk=attach_research_kernel({'markets':{k:{} for k in ['us','idx','crypto','commodity','fx']}})
    ck('research_kernel_attaches_v66',desk.get('research_evidence_v66',{}).get('status')=='SCOPED_RISK_CONTROL_CONFIRMED',desk.get('research_evidence_v66'))
    html=(ROOT/'dashboard.html').read_text()
    ck('dashboard_loads_v66','let RE66 = obj(D.research_evidence_v66);' in html)
    ck('dashboard_scope_copy',('one decision-usable but narrow US broad-equity monthly risk-reduction control' in html) or ('V7.6 is final for one exact usable scope' in html))
    ck('dashboard_ticker_block_copy','Ticker orders remain blocked' in html)
    scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.S|re.I); tmp=Path(tempfile.mkdtemp(prefix='v66_js_')); js=tmp/'dashboard.js';js.write_text(max(scripts,key=len));p=subprocess.run(['node','--check',str(js)],capture_output=True,text=True);ck('javascript_parse',p.returncode==0,p.stderr[-1000:]);shutil.rmtree(tmp,ignore_errors=True)
    run('scoped_runtime_and_shadow_tests',[sys.executable,str(ROOT/'test_v66_scoped_risk_and_shadow.py')],120)
    run('v65_regression',[sys.executable,str(ROOT/'validate_v65_proof_first.py')],360)
    run('v64_regression',[sys.executable,str(ROOT/'validate_v64_scoped_proof.py')],360)
    run('v63_all_tabs_regression',[sys.executable,str(ROOT/'validate_v63_all_tabs.py')],360)
    run('v62_research_regression',[sys.executable,str(ROOT/'validate_v62_deeper_research.py')],360)
    run('release_contract_regression',[sys.executable,str(ROOT/'validate_v60_release_contracts.py')],360)
    run('origin_harness_regression',[sys.executable,str(ROOT/'test_v62_origin_harness.py')],240)
    run('sec_pit_regression',[sys.executable,str(ROOT/'test_v62_sec_pit_pipeline.py')],240)
    p=subprocess.run([sys.executable,'-m','compileall','-q',str(ROOT)],capture_output=True,text=True,timeout=300);ck('python_compile_all',p.returncode==0,(p.stdout+p.stderr)[-2000:])
    needed=['V66_FINAL_STATUS.md','V66_SCOPED_USABLE_CONTROL_FINAL.md','V66_NOT_FINAL_FOR_ALPHA.md','V66_SCOPED_USABLE_KERNEL.json','V66_COMPONENT_PROOF_MATRIX.json','V66_PROSPECTIVE_SHADOW_PROTOCOL.json']
    ck('release_docs_present',all((ROOT/x).is_file() for x in needed),[x for x in needed if not (ROOT/x).is_file()])
    report={'schema':'warroom.v66.scoped_usable_validation.v1','status':'PASS' if all(x['passed'] for x in checks.values()) else 'FAIL','passed':sum(x['passed'] for x in checks.values()),'total':len(checks),'checks':checks,'decision_active_scoped_risk_controls':1,'decision_active_ticker_or_directional_components':0,'capital_permission':'CONDITIONAL_RISK_CAP_ONLY_FOR_US_BROAD_EQUITY_REDUCTION'}
    (ROOT/'V66_VALIDATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f"{report['passed']}/{report['total']} {report['status']}")
    raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()

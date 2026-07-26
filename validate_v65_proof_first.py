from __future__ import annotations
import hashlib,json,os,re,subprocess,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED=['SMILE_ANN','SMILE_ONLY','SMILE_EXPECTATIONS_DIV']
checks={}
WRITE=os.environ.get('WARROOM_WRITE_VALIDATION_ARTIFACTS','1')=='1'

def ck(name,ok,detail=None):
    checks[name]={'passed':bool(ok),'detail':detail}
    if not ok: print('FAIL',name,detail,file=sys.stderr)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    info=json.loads((ROOT/'research_v65/results/V65_INFORMATION_ORIGIN_ENSEMBLE_RESULTS.json').read_text())
    glob=json.loads((ROOT/'research_v65/results/V65_GLOBAL_SELECTION_ADJUDICATION_RESULTS.json').read_text())
    stab=json.loads((ROOT/'research_v65/results/V65_STABILITY_FALSIFICATION_RESULTS.json').read_text())
    kernel=json.loads((ROOT/'V65_PROOF_FIRST_ACTIVE_KERNEL.json').read_text())
    matrix=json.loads((ROOT/'V65_COMPONENT_PROOF_MATRIX.json').read_text())
    registry=json.loads((ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json').read_text())

    ck('info_schema',info.get('schema')=='warroom.v65.information_origin_ensemble.results.v1',info.get('schema'))
    ck('global_schema',glob.get('schema')=='warroom.v65.global_selection_adjudication.results.v1',glob.get('schema'))
    ck('stability_schema',stab.get('schema')=='warroom.v65.stability_falsification.results.v1',stab.get('schema'))
    ck('info_protocol_bound',info.get('protocol_sha256')==sha(ROOT/'research_v65/protocols/V65_INFORMATION_ORIGIN_ENSEMBLE_PROTOCOL_FROZEN.json'))
    ck('global_protocol_bound',glob.get('protocol_sha256')==sha(ROOT/'research_v65/protocols/V65_GLOBAL_SELECTION_ADJUDICATION_PROTOCOL.json'))
    ck('stability_protocol_bound',stab.get('protocol_sha256')==sha(ROOT/'research_v65/protocols/V65_STABILITY_FALSIFICATION_PROTOCOL_FROZEN.json'))
    ck('global_family_216',glob.get('global_family_count')==216,glob.get('global_family_count'))
    ck('three_global_10bp_survivors',glob.get('hurdle_10bp_survivors')==EXPECTED,glob.get('hurdle_10bp_survivors'))
    ck('zero_global_25bp_survivors',glob.get('hurdle_25bp_survivors')==[],glob.get('hurdle_25bp_survivors'))
    ck('three_stability_survivors',stab.get('stability_survivors')==EXPECTED,stab.get('stability_survivors'))
    for cid in EXPECTED:
        gd=glob['details'][cid]; sd=stab['details'][cid]
        ck(cid+'_10bp_validation_lb_positive',gd['validation']['0.001']['global_216_simultaneous_lower_bound']>0,gd['validation']['0.001'])
        ck(cid+'_10bp_lockbox_lb_positive',gd['lockbox']['0.001']['global_216_simultaneous_lower_bound']>0,gd['lockbox']['0.001'])
        ck(cid+'_stability_pass',bool(sd.get('stability_pass')),sd)
        ck(cid+'_reverse_control_pass',bool(sd['validation'].get('reverse_sign_control_pass')) and bool(sd['lockbox'].get('reverse_sign_control_pass')),{'validation':sd['validation'].get('reverse_sign_control_pass'),'lockbox':sd['lockbox'].get('reverse_sign_control_pass')})

    from research_evidence_v65 import load_research_evidence_v65
    ev=load_research_evidence_v65()
    ck('evidence_module_reconciled',ev.get('status')=='PROOF_FIRST_KERNEL_RECONCILED',ev.get('reason'))
    ck('evidence_claims_exact', [x.get('claim_id') for x in ev.get('evidence_active_research_claims',[])]==EXPECTED)
    ck('evidence_exact_contracts',ev.get('all_evidence_active_claims_pass_exact_contract') is True)
    ck('evidence_decision_inactive',all(not x.get('decision_active') and x.get('live_decision_weight')==0 for x in ev.get('evidence_active_research_claims',[])))
    ck('evidence_capital_blocked',ev.get('capital_permission')=='BLOCKED' and ev.get('live_predictive_components_promoted')==0)

    ck('kernel_schema',kernel.get('schema')=='warroom.v65.proof_first_active_kernel.v1')
    ck('kernel_active_contracts',kernel.get('all_active_components_meet_their_own_contract') is True)
    ck('kernel_counts',kernel.get('counts')=={'active_operational':6,'evidence_active_research':3,'decision_active_predictive':0,'quarantined':23},kernel.get('counts'))
    ck('kernel_no_predictive_active',kernel.get('decision_active_predictive_components')==[])
    ck('kernel_capital_blocked',kernel.get('capital_permission')=='BLOCKED' and kernel.get('live_decision_weight')==0.0)
    ck('matrix_claims_exact',[x.get('component_id') for x in matrix.get('research_claims',[])]==EXPECTED)
    ck('matrix_all_research_inactive',all(not x.get('decision_active') and x.get('capital_permission')=='BLOCKED' for x in matrix.get('research_claims',[])))
    ck('matrix_all_operational_nonpredictive',all(x.get('component_class')=='ACTIVE_OPERATIONAL_VALIDATED' and not x.get('predictive_semantics') for x in matrix.get('operational',[])))

    regkeys=set(registry.get('components',{}))
    expected_reg={'smile_slope_archive_v65','smile_announcement_archive_v65','smile_expectations_div_archive_v65'}
    ck('proof_registry_has_v65',expected_reg<=regkeys,sorted(expected_reg-regkeys))
    ck('proof_registry_v65_not_promoted',all(registry['components'][k]['state']=='DESCRIPTIVE_CONTROL' and not registry['components'][k]['predictive_promoted'] for k in expected_reg))
    ck('proof_registry_version',registry.get('version') in {'6.5','6.6'},registry.get('version'))

    from research_kernel import attach_research_kernel
    desk=attach_research_kernel({'markets':{k:{} for k in ['us','idx','crypto','commodity','fx']}})
    ck('research_kernel_attaches_v65',desk.get('research_evidence_v65',{}).get('status')=='PROOF_FIRST_KERNEL_RECONCILED',desk.get('research_evidence_v65'))
    ck('research_kernel_capital_blocked',desk.get('research_kernel',{}).get('global_permission')=='CAPITAL_BLOCKED')

    html=(ROOT/'dashboard.html').read_text()
    ck('dashboard_re65_loaded','let RE65 = obj(D.research_evidence_v65);' in html)
    ck('dashboard_v65_validation_copy',('V6.5 activates only exact-scope evidence' in html) or ('V6.6 confirms one decision-usable' in html) or ('V7.6 is final for one exact usable scope' in html))
    ck('dashboard_zero_pit_copy',('0 PIT selectors' in html) or ('zero PIT ticker selectors' in html))
    scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.S|re.I)
    tmp=Path(tempfile.mkdtemp(prefix='warroom_v65_'))
    jsp=tmp/'dashboard.js';jsp.write_text(max(scripts,key=len))
    proc=subprocess.run(['node','--check',str(jsp)],capture_output=True,text=True)
    ck('javascript_parse',proc.returncode==0,proc.stderr[-1000:])
    shutil.rmtree(tmp,ignore_errors=True)

    pr=subprocess.run([sys.executable,'-m','compileall','-q',str(ROOT)],capture_output=True,text=True,timeout=240)
    ck('python_compile_all',pr.returncode==0,(pr.stdout+pr.stderr)[-2000:])

    needed=['V65_FINAL_STATUS.md','V65_PROOF_FIRST_BREAKTHROUGH_FINAL.md','V65_INSTITUTIONAL_ARCHITECTURE.md','V65_DATA_UPGRADE_BLUEPRINT.md','V65_PROOF_GAP_TO_LIVE_MATRIX.json','V65_SOURCE_MAP.json']
    ck('release_docs_present',all((ROOT/x).is_file() for x in needed),[x for x in needed if not (ROOT/x).is_file()])

    report={
      'schema':'warroom.v65.proof_first_validation.v1',
      'status':'PASS' if all(v['passed'] for v in checks.values()) else 'FAIL',
      'passed':sum(v['passed'] for v in checks.values()),'total':len(checks),'checks':checks,
      'active_operational_components':6,'evidence_active_research_components':3,
      'decision_active_predictive_components':0,'global_10bp_supported':3,'global_25bp_supported':0,
      'point_in_time_ticker_selectors_proven':0,'capital_permission':'BLOCKED'
    }
    if WRITE:(ROOT/'V65_VALIDATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f"{report['passed']}/{report['total']} {report['status']}")
    raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()

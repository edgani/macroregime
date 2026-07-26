from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VIEWS=["mc","macro","ew","alpha","co","us","ihsg","crypto","commod","fx","flow","inst","deriv","sc","kg","execution","research","rc","datahealth"]
checks={}
WRITE_ARTIFACTS=os.environ.get("WARROOM_WRITE_VALIDATION_ARTIFACTS","1")=="1"
def ck(name,ok,detail=None):
    checks[name]={'passed':bool(ok),'detail':detail}
    if not ok: print('FAIL',name,detail,file=sys.stderr)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    surv=json.loads((ROOT/'research_v64/results/V64_THREE_SURVIVOR_CONFIRMATION_RESULTS.json').read_text())
    modern=json.loads((ROOT/'research_v64/results/V64_MODERN_212_FACTOR_CONFIRMATION_RESULTS.json').read_text())
    tsm=json.loads((ROOT/'research_v64/results/V64_TSMOM_CRISIS_OVERLAY_RESULTS.json').read_text())
    trial=json.loads((ROOT/'V64_GLOBAL_TRIAL_ACCOUNTING.json').read_text())
    ck('survivor_protocol_bound',surv['protocol_sha256']==sha(ROOT/'research_v64/protocols/V64_THREE_SURVIVOR_CONFIRMATION_PROTOCOL_FROZEN.json'))
    ck('modern_protocol_bound',modern['protocol_sha256']==sha(ROOT/'research_v64/protocols/V64_MODERN_212_FACTOR_CONFIRMATION_PROTOCOL_FROZEN.json'))
    ck('modern_grid_bound',modern['grid_sha256']==sha(ROOT/'research_v64/protocols/V64_MODERN_212_FACTOR_GRID_FROZEN.csv'))
    ck('tsmom_protocol_bound',tsm['protocol_sha256']==sha(ROOT/'research_v64/protocols/V64_TSMOM_CRISIS_OVERLAY_PROTOCOL_FROZEN.json'))
    ck('three_historical_scoped_claims',surv['historical_gross_proven_count']==3 and all(x['historical_gross_proven'] for x in surv['claim_ledger']),surv['claim_ledger'])
    ck('historical_not_modern',surv['modern_all_stock_gross_proven_count']==0)
    ck('modern_universe_208',modern['candidate_count']==208)
    ck('smileslope_only_modern_survivor',modern['modern_gross_claims_passed']==1 and modern['survivors']==['SmileSlope'],modern['survivors'])
    ck('smileslope_not_10bp_familywise',modern['flat_10bp_hurdle_passed']==0 and not modern['details']['SmileSlope']['flat_10bp_hurdle_pass'])
    ck('smileslope_validation_lockbox_pass',modern['details']['SmileSlope']['validation']['0.0']['pass'] and modern['details']['SmileSlope']['lockbox']['0.0']['pass'])
    ck('smileslope_positive_adjusted_lbs',modern['details']['SmileSlope']['validation']['0.0']['simultaneous_lower_bound']>0 and modern['details']['SmileSlope']['lockbox']['0.0']['simultaneous_lower_bound']>0)
    ck('tsmom_overlay_not_proven',tsm.get('market_claim_status')=='NOT_PROVEN',tsm.get('market_claim_status'))
    ck('trial_accounting_exact',trial['total_empirical_claim_records']==233736 and trial['historical_gross_market_claims_proven']==3 and trial['modern_all_stock_claims_proven']==1)
    ck('no_independent_or_selector_proof',trial['independent_modern_claims_proven']==0 and trial['modern_non_micro_investable_claims_proven']==0 and trial['stock_level_pit_selectors_proven']==0)
    ck('capital_blocked',trial['live_predictive_components_promoted']==0 and trial['live_decision_weight']==0 and trial['capital_permission']=='BLOCKED')
    from research_evidence_v64 import load_research_evidence_v64
    ev=load_research_evidence_v64()
    ck('evidence_module_reconciled',ev.get('status')=='RECONCILED_SCOPED_PROOF',ev.get('reason'))
    ck('evidence_claims_four',len(ev.get('claims',[]))==4,[x.get('claim_id') for x in ev.get('claims',[])])

    html=(ROOT/'dashboard.html').read_text(); scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.S|re.I);js=scripts[-1]
    tmp=Path(tempfile.mkdtemp(prefix='warroom_v64_'))
    jsp=tmp/'dashboard.js';jsp.write_text(js)
    proc=subprocess.run(['node','--check',str(jsp)],capture_output=True,text=True)
    ck('javascript_parse',proc.returncode==0,proc.stderr[-1000:])
    fixture=tmp/'desk.json'
    proc=subprocess.run([sys.executable,'run.py','--synthetic','--markets','us,idx,crypto,commodity,fx','--out',str(fixture),'--html',str(tmp/'fixture.html')],cwd=ROOT,capture_output=True,text=True,timeout=240)
    ck('fixture_generation',proc.returncode==0,(proc.stdout+proc.stderr)[-1000:])
    desk=json.loads(fixture.read_text()) if fixture.exists() else {}
    ck('snapshot_v64_attached',desk.get('research_evidence_v64',{}).get('status')=='RECONCILED_SCOPED_PROOF',desk.get('research_evidence_v64'))
    us=desk.setdefault('markets',{}).setdefault('us',{});us['data_state']='LIVE';us['bias']='NEUTRAL';us['bias_state']='PARTIAL';us.setdefault('funnel',{})['universe']=2;us['funnel']['setups']=2
    us['setups']=[{'tk':'SPY','market':'us','act':'POSITIVE_PRICE_CONTEXT','dir':'long','setup_rank':99,'conv':99,'valid':False,'directional_permission':False,'capital_permission':'BLOCKED','why':'ETF guard'},{'tk':'AAPL','market':'us','act':'POSITIVE_PRICE_CONTEXT','dir':'long','setup_rank':80,'conv':80,'valid':False,'directional_permission':False,'capital_permission':'BLOCKED','why':'company guard'}]
    desk['macro_observations']={}
    fixture.write_text(json.dumps(desk,separators=(',',':')))
    anchor="document.querySelectorAll('.seg')";ck('dashboard_exposure_anchor',anchor in js)
    core=js.rsplit(anchor,1)[0]
    if not core.rstrip().endswith('\n'): core+='\n'
    core+="globalThis.__audit={setView:(v)=>{state.view=v;state.selected=null;state.selectedTicker=null;return getModel();}};\n})();\n"
    runner=tmp/'runner.js'
    runner.write_text("const fs=require('fs'),vm=require('vm');\n"+f"const D=JSON.parse(fs.readFileSync({json.dumps(str(fixture))},'utf8'));\n"+"const noop=()=>{};const el={innerHTML:'',textContent:'',dataset:{},classList:{toggle:noop,add:noop,remove:noop},addEventListener:noop};const document={getElementById:()=>el,querySelectorAll:()=>[],querySelector:()=>el};const localStorage={getItem:()=>null,setItem:noop};const window={DASHBOARD_DATA:D,parent:{location:{href:'http://localhost/app/'}},location:{href:'http://localhost/'}};const sandbox={window,document,localStorage,location:{search:''},URL,URLSearchParams,Date,Math,JSON,Number,String,Boolean,Array,Object,Set,Map,RegExp,console,setTimeout,clearTimeout,AbortController,fetch:async()=>{throw new Error('disabled')}};vm.createContext(sandbox);\n"+"vm.runInContext("+json.dumps(core)+",sandbox,{timeout:10000});\n"+f"const views={json.dumps(VIEWS)};const out={{}};for(const v of views)out[v]=sandbox.__audit.setView(v);console.log(JSON.stringify(out));\n")
    proc=subprocess.run(['node',str(runner)],capture_output=True,text=True,timeout=60)
    ck('all_tab_model_runner',proc.returncode==0,proc.stderr[-2000:])
    models=json.loads(proc.stdout) if proc.returncode==0 else {}
    if WRITE_ARTIFACTS: (ROOT/'V64_TAB_MODEL_AUDIT.json').write_text(json.dumps(models,indent=2,sort_keys=True)+'\n')
    ck('all_19_views',set(models)==set(VIEWS),sorted(models))
    ck('all_capital_blocked',all(m.get('proof',{}).get('capital')=='BLOCKED' for m in models.values()))
    ck('company_etf_guard',models.get('co',{}).get('rail',{}).get('title')=='AAPL',models.get('co',{}).get('rail',{}).get('title'))
    rt=json.dumps(models.get('research',{}));vt=json.dumps(models.get('rc',{}))
    for txt,name in [(rt,'research'),(vt,'validation')]:
        ck(name+'_shows_historical_claims',all(x in txt for x in ['AnalystRevision','AnnouncementReturn','DivYieldST']))
        ck(name+'_shows_smileslope','SmileSlope' in txt)
        ck(name+'_shows_233736','233736' in txt)
    ck('validation_no_production',models.get('rc',{}).get('rail',{}).get('confidence')==0,models.get('rc',{}).get('rail'))
    ck('validation_scope_text','modern archive-supported' in models.get('rc',{}).get('rail',{}).get('desc','').lower(),models.get('rc',{}).get('rail',{}).get('desc'))
    report={'schema':'warroom.v64.scoped_proof_validation.v1','status':'PASS' if all(x['passed'] for x in checks.values()) else 'FAIL','passed':sum(x['passed'] for x in checks.values()),'total':len(checks),'checks':checks,'historical_gross_market_claims_proven':3,'modern_all_stock_archive_claims_supported':1,'independent_modern_claims_proven':0,'stock_level_pit_selectors_proven':0,'live_predictive_components_promoted':0,'capital_permission':'BLOCKED'}
    if WRITE_ARTIFACTS: (ROOT/'V64_VALIDATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f"{report['passed']}/{report['total']} {report['status']}")
    shutil.rmtree(tmp,ignore_errors=True)
    raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()

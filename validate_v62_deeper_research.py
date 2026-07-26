from __future__ import annotations
import csv,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
checks={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(name,args,timeout=180):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    checks[name]=p.returncode==0
    if p.returncode: print(name,p.stdout,p.stderr,file=sys.stderr)

# Frozen protocols and grids.
for ver,prefix in [('v61','NETWORK_DIFFUSION'),('v62','EVENT_ORIGIN')]:
    base=ROOT/f'research_{ver}'/'protocols'
    pp=base/f'{ver.upper()}_{prefix}_PROTOCOL_FROZEN.json';gp=base/f'{ver.upper()}_{prefix}_CANDIDATE_GRID_FROZEN.csv'
    psha=next(x for x in [base/f'{pp.name}.sha256.txt',base/f'{pp.stem}.sha256',base/f'{pp.name}.sha256'] if x.exists())
    gsha=next(x for x in [base/f'{gp.name}.sha256.txt',base/f'{gp.stem}.sha256',base/f'{gp.name}.sha256'] if x.exists())
    expected=psha.read_text().split()[0];checks[f'{ver}_protocol_hash']=sha(pp)==expected
    expected=gsha.read_text().split()[0];checks[f'{ver}_grid_hash']=sha(gp)==expected
    proto=json.loads(pp.read_text());checks[f'{ver}_fail_closed']=proto['live_decision_weight']==0 and proto['capital_permission']=='BLOCKED'
# Result integrity.
net=json.loads((ROOT/'research_v61/results/V61_NETWORK_DIFFUSION_RESULTS.json').read_text());evt=json.loads((ROOT/'research_v62/results/V62_EVENT_ORIGIN_RESULTS.json').read_text())
checks['network_protocol_bound']=net['protocol_sha256']==sha(ROOT/'research_v61/protocols/V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json')
checks['event_protocol_bound']=evt['protocol_sha256']==sha(ROOT/'research_v62/protocols/V62_EVENT_ORIGIN_PROTOCOL_FROZEN.json')
for name,d,grid,ledger in [
 ('network',net,ROOT/'research_v61/protocols/V61_NETWORK_DIFFUSION_CANDIDATE_GRID_FROZEN.csv',ROOT/'research_v61/ledgers/V61_NETWORK_DIFFUSION_GLOBAL_LEDGER.csv'),
 ('event',evt,ROOT/'research_v62/protocols/V62_EVENT_ORIGIN_CANDIDATE_GRID_FROZEN.csv',ROOT/'research_v62/ledgers/V62_EVENT_ORIGIN_GLOBAL_LEDGER.csv')]:
    with grid.open() as f:g=sum(1 for _ in csv.DictReader(f))
    with ledger.open() as f:l=sum(1 for _ in csv.DictReader(f))
    checks[f'{name}_candidate_count']=d['candidate_count']==g
    checks[f'{name}_ledger_count']=d['registered_claims']==l==g*4
    checks[f'{name}_production_zero']=d['production_promoted_claims']==0 and d['live_decision_weight']==0 and d['capital_permission']=='BLOCKED'
acct=json.loads((ROOT/'V62_GLOBAL_TRIAL_ACCOUNTING.json').read_text())
checks['trial_accounting']=acct['total_empirical_claim_records']==215788+net['registered_claims']+evt['registered_claims'] and acct['production_proven_early_move_drivers']==0
reg=json.loads((ROOT/'V62_RESEARCH_EVIDENCE_REGISTRY.json').read_text());checks['registry_fail_closed']=reg['production_promoted']==0 and reg['capital_permission']=='BLOCKED'
run('origin_harness',[sys.executable,'test_v62_origin_harness.py'])
run('sec_pit_pipeline',[sys.executable,'test_v62_sec_pit_pipeline.py'])
run('v60_mechanical_regression',[sys.executable,'test_v60_mechanical_flow.py'])
run('v60_release_contracts',[sys.executable,'validate_v60_release_contracts.py'],300)
run('compileall',[sys.executable,'-m','compileall','-q','.'],300)
status='PASS' if all(checks.values()) else 'FAIL'
out={'schema':'warroom.v62.validation','status':status,'checks':checks,'passed':sum(checks.values()),'total':len(checks),'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
(ROOT/'V62_VALIDATION.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(f"{out['passed']}/{out['total']} {status}")
raise SystemExit(0 if status=='PASS' else 1)

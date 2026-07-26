from __future__ import annotations
import csv, hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'research_v58'
RES = R / 'results'
LED = R / 'ledgers'
DATA = R / 'data'
LED.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def load(name): return json.loads((RES/name).read_text())

def min_valid(*xs):
    vals=[float(x) for x in xs if x is not None]
    return min(vals) if vals else None

def copy_source(src: Path, dstname: str, provenance: dict):
    dst=DATA/dstname
    shutil.copy2(src,dst)
    prov={**provenance,'file':dstname,'sha256':sha(dst),'size_bytes':dst.stat().st_size}
    (DATA/(dstname+'.provenance.json')).write_text(json.dumps(prov,indent=2,sort_keys=True)+'\n')
    return prov

sources=[]
for src,dst,prov in [
    (Path('/mnt/data/SignalDoc.csv'),'SignalDoc.csv',{
        'source_role':'official predictor/placebo/drop definition catalog',
        'source_origin':'Open Source Asset Pricing official GitHub repository',
        'license_boundary':'public research metadata',
    }),
    (Path('/mnt/data/PredictorLSretWide.csv'),'PredictorLSretWide.csv',{
        'source_role':'maintained monthly long-short return series for all 212 predictor acronyms',
        'source_origin':'public GitHub mirror of the OpenAP-named current wide return file',
        'trust_boundary':'mirror file hash pinned; not independently authenticated as an official point-in-time archive',
        'license_boundary':'public research output; no stock-level point-in-time constituents',
    }),
]:
    if src.exists(): sources.append(copy_source(src,dst,prov))
for src in sorted(Path('/mnt/data').glob('*Monthly.xlsx')):
    sources.append(copy_source(src,src.name,{
        'source_role':'public maintained monthly research factor series',
        'source_origin':'AQR Data Library downloaded workbooks',
        'trust_boundary':'public research portfolio return series, not a live implementable portfolio audit',
    }))

openap=load('V58_OPENAP_212_POSTSAMPLE_RESULTS.json')
public=load('V58_PUBLIC_FACTOR_POSTSAMPLE_RESULTS.json')
pv=load('V58_PRICE_VOLUME_SWEEP_RESULTS.json')
macro=load('V58_MACRO_SWEEP_RESULTS.json')

GLOBAL_TESTS = 795
GLOBAL_Z = NormalDist().inv_cdf(1 - 0.05 / GLOBAL_TESTS)

rows=[]
def add(row):
    row.setdefault('live_decision_weight',0.0)
    row.setdefault('capital_permission','BLOCKED')
    rows.append(row)

for c in openap['claims']:
    cl=c['claim']; tier=c.get('tier','FAILED_OR_UNIDENTIFIABLE')
    add({
        'ledger_id':cl['claim_id'], 'study':'V58_OPENAP_212_POSTSAMPLE',
        'candidate':cl['series'], 'name':cl.get('name'), 'family':'openap_predictor',
        'registered_trial_count_family':212, 'evaluation_status':tier,
        'global_registered_trials':GLOBAL_TESTS,
        'global_validation_lb_gross':c['splits']['validation']['0.0']['mean_monthly'] - GLOBAL_Z*c['splits']['validation']['0.0']['hac_se'],
        'global_lockbox_lb_gross':(c['splits']['lockbox']['0.0'].get('mean_monthly') - GLOBAL_Z*c['splits']['lockbox']['0.0'].get('hac_se')) if c['splits']['lockbox']['0.0'].get('hac_se') is not None else None,
        'global_validation_lb_25bps':c['splits']['validation']['0.0025']['mean_monthly'] - GLOBAL_Z*c['splits']['validation']['0.0025']['hac_se'],
        'global_lockbox_lb_25bps':(c['splits']['lockbox']['0.0025'].get('mean_monthly') - GLOBAL_Z*c['splits']['lockbox']['0.0025'].get('hac_se')) if c['splits']['lockbox']['0.0025'].get('hac_se') is not None else None,
        'validation_lb_gross':c['splits']['validation']['0.0']['bonferroni_lower_bound'],
        'lockbox_lb_gross':c['splits']['lockbox']['0.0'].get('bonferroni_lower_bound'),
        'validation_lb_25bps':c['splits']['validation']['0.0025']['bonferroni_lower_bound'],
        'lockbox_lb_25bps':c['splits']['lockbox']['0.0025'].get('bonferroni_lower_bound'),
        'historical_support':bool(c.get('historical_support')),
        'proof_ceiling':'Maintained aggregate long-short return persistence only; requires fresh stock-level point-in-time replication, actual turnover/cost/borrow/capacity and untouched prospective evidence.',
        'protocol_sha256':openap['protocol_sha256'],
    })
for c in public['claims']:
    cl=c['claim']; tier=c.get('tier','FAILED_OR_UNIDENTIFIABLE')
    add({
        'ledger_id':cl['claim_id'], 'study':'V58_PUBLIC_FACTOR_POSTSAMPLE',
        'candidate':cl['series'], 'name':cl['claim_id'], 'family':cl['family'],
        'registered_trial_count_family':39, 'evaluation_status':tier,
        'validation_lb_gross':c['splits']['validation']['0.0']['bonferroni_lower_bound'],
        'lockbox_lb_gross':c['splits']['lockbox']['0.0'].get('bonferroni_lower_bound'),
        'historical_support':bool(c.get('historical_support')),
        'proof_ceiling':'Public maintained factor portfolio diagnostic; no strict simultaneous validation+lockbox survivor.',
        'protocol_sha256':public['protocol_sha256'],
    })
for c in pv['claims']:
    add({
        'ledger_id':c['claim_id'], 'study':'V58_PRICE_VOLUME_SWEEP',
        'candidate':c['feature'], 'name':c['claim_id'], 'family':c['family'],
        'registered_trial_count_family':200, 'evaluation_status':'SURVIVOR' if c['diagnostic_survivor'] else 'REJECTED',
        'validation_lb':min_valid(c['splits']['validation']['ic'].get('bonferroni_lb'),c['splits']['validation']['spread'].get('bonferroni_lb')),
        'lockbox_lb':min_valid(c['splits']['diagnostic_holdout']['ic'].get('bonferroni_lb'),c['splits']['diagnostic_holdout']['spread'].get('bonferroni_lb')),
        'is_placebo':c['family']=='placebo',
        'proof_ceiling':'Reused fixed 483-name panel diagnostic; even a survivor would require fresh point-in-time replication.',
        'protocol_sha256':pv['protocol_sha256'],
    })
for c in macro['claims']:
    add({
        'ledger_id':c['claim_id'], 'study':'V58_MACRO_SWEEP',
        'candidate':c['feature'], 'name':c['claim_id'], 'family':c['family'],
        'registered_trial_count_family':344, 'evaluation_status':'SURVIVOR' if c['diagnostic_survivor'] else 'REJECTED',
        'validation_lb':c['splits']['validation']['bonferroni_lb'],
        'lockbox_lb':c['splits']['diagnostic_holdout']['bonferroni_lb'],
        'is_placebo_or_interaction':c['family']=='interaction_or_placebo',
        'proof_ceiling':'Revised/reused monthly macro history diagnostic; not vintage point-in-time proof.',
        'protocol_sha256':macro['protocol_sha256'],
    })


for r in rows:
    if r['study']=='V58_OPENAP_212_POSTSAMPLE':
        vg=r.get('global_validation_lb_gross'); lg=r.get('global_lockbox_lb_gross')
        vc=r.get('global_validation_lb_25bps'); lc=r.get('global_lockbox_lb_25bps')
        if None not in (vc,lc) and vc>0 and lc>0:
            r['global_795_status']='SURVIVES_GLOBAL_25BPS'
        elif None not in (vg,lg) and vg>0 and lg>0:
            r['global_795_status']='SURVIVES_GLOBAL_GROSS_ONLY'
        else:
            r['global_795_status']='DOES_NOT_SURVIVE_GLOBAL_795'

study_counts={}
for r in rows:
    s=study_counts.setdefault(r['study'],{'registered':0,'survivors':0,'historical_support':0})
    s['registered']+=1
    if 'ROBUST' in r['evaluation_status'] or r['evaluation_status']=='SURVIVOR': s['survivors']+=1
    if r.get('historical_support'): s['historical_support']+=1

ledger={
    'schema':'warroom.global_trial_ledger.v58',
    'created_at_utc':NOW,
    'status':'COMPLETE_FOR_CURRENT_DATA_READY_BATTERIES',
    'research_universe_candidates':868,
    'registered_claims_in_v58_batteries':len(rows),
    'global_bonferroni_one_sided_z':GLOBAL_Z,
    'global_gross_survivors':[r['candidate'] for r in rows if r.get('global_795_status')=='SURVIVES_GLOBAL_GROSS_ONLY'],
    'global_25bps_survivors':[r['candidate'] for r in rows if r.get('global_795_status')=='SURVIVES_GLOBAL_25BPS'],
    'study_counts':study_counts,
    'global_rule':'Every tried claim, including placebos and rejected variants, remains registered. Family-level corrections are not interpreted as a universal 795-way final promotion.',
    'important_boundary':'The three OpenAP global-gross survivors are replication-queue candidates, not War Room live edge. No v58 result carries nonzero decision weight or capital permission.',
    'source_artifacts':sources,
    'rows':rows,
    'predictive_components_promoted_to_live':0,
    'research_live_decision_weight':0.0,
    'capital_permission':'BLOCKED',
}
out=LED/'V58_GLOBAL_TRIAL_LEDGER.json'
out.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
cols=sorted({k for r in rows for k in r})
with (LED/'V58_GLOBAL_TRIAL_LEDGER.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

# Data-readiness matrix: preserve every mapped candidate, annotate current stage.
universe=json.loads((R/'V58_RESEARCH_UNIVERSE.json').read_text())
openap_tiers={r['candidate']:r['evaluation_status'] for r in rows if r['study']=='V58_OPENAP_212_POSTSAMPLE'}
ready=[]
for c in universe['candidates']:
    x={k:c.get(k) for k in ['candidate_id','name','family','primary_role','market_scope','source_class','source_signal_class','data_required']}
    acronym=c['candidate_id'].replace('OAP_PREDICTOR_','').replace('OAP_PLACEBO_','').replace('OAP_DROP_','')
    # robust exact lookup is case-sensitive by stored acronym; find candidate name against OpenAP rows if predictor.
    exact=None
    if c.get('source_signal_class')=='PREDICTOR':
        for k,v in openap_tiers.items():
            if k.upper()==acronym: exact=v; break
    if exact:
        x.update({'data_readiness':'AGGREGATE_RETURN_SERIES_TESTED','current_evidence_status':exact,'next_valid_action':'fresh point-in-time stock-level replication if robust; otherwise retain failure/persistence diagnostic'})
    elif c.get('source_signal_class') in {'PLACEBO','DROP'}:
        x.update({'data_readiness':'DEFINITION_AVAILABLE_RAW_INPUTS_NOT_PRESENT','current_evidence_status':'NOT_DIRECTLY_RECONSTRUCTED','next_valid_action':'reconstruct from point-in-time stock-level source; keep in global trial budget'})
    else:
        x.update({'data_readiness':'MAPPING_COMPLETE_SOURCE_ACQUISITION_REQUIRED','current_evidence_status':'NOT_YET_EVALUATED_OR_ONLY_FAMILY_PROXY_TESTED','next_valid_action':'acquire exact causal source, freeze implementation, then test'})
    x['live_decision_weight']=0.0;x['capital_permission']='BLOCKED'
    ready.append(x)
readiness={'schema':'warroom.research_data_readiness.v58','created_at_utc':NOW,'candidate_count':len(ready),'rows':ready,'capital_permission':'BLOCKED'}
(R/'V58_DATA_READINESS_MATRIX.json').write_text(json.dumps(readiness,indent=2,sort_keys=True)+'\n')
with (R/'V58_DATA_READINESS_MATRIX.csv').open('w',newline='',encoding='utf-8') as f:
    cols=['candidate_id','name','family','primary_role','market_scope','source_class','source_signal_class','data_required','data_readiness','current_evidence_status','next_valid_action','live_decision_weight','capital_permission']
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for x in ready:
        y=dict(x)
        for k in ['market_scope','data_required']:
            if isinstance(y.get(k),list):y[k]='|'.join(map(str,y[k]))
        w.writerow({k:y.get(k) for k in cols})

summary={
 'ledger_sha256':sha(out),
 'ledger_csv_sha256':sha(LED/'V58_GLOBAL_TRIAL_LEDGER.csv'),
 'readiness_sha256':sha(R/'V58_DATA_READINESS_MATRIX.json'),
 'sources':sources,
 'study_counts':study_counts,
}
(LED/'V58_GLOBAL_TRIAL_LEDGER.sha256.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,indent=2))

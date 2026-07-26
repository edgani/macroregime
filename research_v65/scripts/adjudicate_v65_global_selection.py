from __future__ import annotations
import json, hashlib
from pathlib import Path
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'research_v65/results/V65_INFORMATION_ORIGIN_ENSEMBLE_RESULTS.json'
OUT=ROOT/'research_v65/results/V65_GLOBAL_SELECTION_ADJUDICATION_RESULTS.json'
LED=ROOT/'research_v65/ledgers/V65_GLOBAL_SELECTION_ADJUDICATION_LEDGER.csv'
P=ROOT/'research_v65/protocols/V65_GLOBAL_SELECTION_ADJUDICATION_PROTOCOL.json'
proto={
 'schema':'warroom.v65.global_selection_adjudication.protocol.v1',
 'created_at':'2026-07-26T00:00:00+07:00',
 'purpose':'Apply a conservative Bonferroni adjudication across the 208-factor modern screen and the 8 bounded follow-up candidates. This is stricter post-selection accounting, not a claim that the follow-up family was independently preregistered before SmileSlope selection.',
 'original_factor_candidates':208,
 'bounded_followup_candidates':8,
 'global_family_count':216,
 'familywise_alpha_one_sided':0.05,
 'hurdles_monthly_decimal':[0.0,0.001,0.0025],
 'source_results':'research_v65/results/V65_INFORMATION_ORIGIN_ENSEMBLE_RESULTS.json',
 'claim_limit':'Conservative maintained-archive aggregate all-stock adjudication only. Post-selection, non-independent, not non-micro, not ticker-level PIT, not operational, and not capital-ready.',
 'live_decision_weight':0.0,
 'capital_permission':'BLOCKED'
}
P.write_text(json.dumps(proto,indent=2,sort_keys=True)+'\n')
src=json.loads(SRC.read_text()); z=float(norm.ppf(1-proto['familywise_alpha_one_sided']/proto['global_family_count']))
rows=[]; detail={}
for cid,d in src['details'].items():
    dd={'definition':d['definition'],'validation':{},'lockbox':{}}
    passes={}
    for split in ['validation','lockbox']:
        for h,st in d[split].items():
            st2=dict(st)
            if 'alpha_monthly' in st2:
                lb=float(st2['alpha_monthly'])-z*float(st2['hac_se'])
                st2['global_216_simultaneous_lower_bound']=lb
                st2['global_216_pass']=bool(st2['alpha_monthly']>0 and lb>0)
            dd[split][h]=st2
    for h in ['0.0','0.001','0.0025']:
        passes[h]=bool(dd['validation'][h].get('global_216_pass',False) and dd['lockbox'][h].get('global_216_pass',False))
    dd['gross_pass_global_216']=passes['0.0']; dd['hurdle_10bp_pass_global_216']=passes['0.001']; dd['hurdle_25bp_pass_global_216']=passes['0.0025']
    detail[cid]=dd
    rows.append({'candidate':cid,'gross_pass_global_216':passes['0.0'],'hurdle_10bp_pass_global_216':passes['0.001'],'hurdle_25bp_pass_global_216':passes['0.0025'],
                 'validation_10bp_lb':dd['validation']['0.001'].get('global_216_simultaneous_lower_bound'),
                 'lockbox_10bp_lb':dd['lockbox']['0.001'].get('global_216_simultaneous_lower_bound'),
                 'validation_25bp_lb':dd['validation']['0.0025'].get('global_216_simultaneous_lower_bound'),
                 'lockbox_25bp_lb':dd['lockbox']['0.0025'].get('global_216_simultaneous_lower_bound'),
                 'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
import pandas as pd
led=pd.DataFrame(rows).sort_values(['hurdle_10bp_pass_global_216','lockbox_10bp_lb'],ascending=[False,False]); led.to_csv(LED,index=False)
out={'schema':'warroom.v65.global_selection_adjudication.results.v1','protocol_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
     'source_results_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'global_family_count':216,'global_zcrit':z,
     'candidate_count':len(rows),'gross_pass_count':int(led.gross_pass_global_216.sum()),
     'hurdle_10bp_pass_count':int(led.hurdle_10bp_pass_global_216.sum()),'hurdle_25bp_pass_count':int(led.hurdle_25bp_pass_global_216.sum()),
     'gross_survivors':led.loc[led.gross_pass_global_216,'candidate'].tolist(),
     'hurdle_10bp_survivors':led.loc[led.hurdle_10bp_pass_global_216,'candidate'].tolist(),
     'hurdle_25bp_survivors':led.loc[led.hurdle_25bp_pass_global_216,'candidate'].tolist(),
     'details':detail,'claim_limit':proto['claim_limit'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k] for k in ['global_family_count','global_zcrit','gross_pass_count','hurdle_10bp_pass_count','hurdle_25bp_pass_count','hurdle_10bp_survivors']},indent=2))
print(led.to_string(index=False))

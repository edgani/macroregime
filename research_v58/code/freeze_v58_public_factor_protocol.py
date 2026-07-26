from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/mnt/data/v58_work/research_v58')
DATA=Path('/mnt/data')

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
claims=[]
def add(dataset, series, family, orig_end, val_start, val_end, lock_start):
 for s in series:
  claims.append({'claim_id':f'{dataset}:{s}','dataset':dataset,'series':s,'family':family,
   'original_sample_end':orig_end,'validation_start':val_start,'validation_end':val_end,
   'lockbox_start':lock_start,'lockbox_end':'LATEST_IN_FROZEN_FILE','expected_sign':'positive'})
add('TSMOM',['TSMOM','TSMOM^CM','TSMOM^EQ','TSMOM^FI','TSMOM^FX'],'time_series_momentum','2009-12-31','2010-01-01','2017-12-31','2018-01-01')
add('VME',['VAL','MOM','VAL^SS','MOM^SS','VAL^AA','MOM^AA','VALLS_VME_US90','MOMLS_VME_US90','VALLS_VME_UK90','MOMLS_VME_UK90','VALLS_VME_ROE90','MOMLS_VME_ROE90','VALLS_VME_JP90','MOMLS_VME_JP90','VALLS_VME_EQ','MOMLS_VME_EQ','VALLS_VME_FX','MOMLS_VME_FX','VALLS_VME_FI','MOMLS_VME_FI','VALLS_VME_COM','MOMLS_VME_COM'],'value_momentum_everywhere','2011-12-31','2012-01-01','2018-12-31','2019-01-01')
agg=['USA','Global','Global Ex USA','Europe','North America','Pacific']
add('BAB',agg,'betting_against_beta','2012-03-31','2012-04-01','2018-12-31','2019-01-01')
add('QMJ',agg,'quality_minus_junk','2012-12-31','2013-01-01','2018-12-31','2019-01-01')
files={
'TSMOM':DATA/'Time-Series-Momentum-Factors-Monthly.xlsx',
'VME':DATA/'Value-and-Momentum-Everywhere-Factors-Monthly.xlsx',
'BAB':DATA/'Betting-Against-Beta-Equity-Factors-Monthly.xlsx',
'QMJ':DATA/'Quality-Minus-Junk-Factors-Monthly.xlsx'}
protocol={
 'schema':'warroom.v58.public_factor_postsample_protocol.v1',
 'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'purpose':'Independent post-original-sample persistence screen across all available aggregate/market factor series in four official AQR updated files; includes weak/failing series and does not select only expected winners.',
 'data_files':{k:{'path':str(v),'sha256':sha(v)} for k,v in files.items()},
 'claims':claims,'claim_count':len(claims),
 'primary_metric':'monthly mean excess return',
 'secondary_metrics':['annualized_mean','annualized_sharpe','HAC_t_stat_lag6','max_drawdown','positive_year_fraction','leave_one_year_out_min_mean'],
 'multiplicity':'one-sided Bonferroni 95% simultaneous lower bound across all registered claims, applied separately to validation and lockbox',
 'cost_sensitivity_monthly':[0.0,0.0025,0.0050],
 'promotion_tiers':{
   'ROBUST_GROSS_POSTSAMPLE':'validation and lockbox point means positive; Bonferroni lower bounds >0 in both; leave-one-year-out minimum mean >0 in both',
   'ROBUST_25BPS_POSTSAMPLE':'ROBUST_GROSS plus Bonferroni lower bounds after 25 bps/month >0 in both',
   'DIRECTIONALLY_PERSISTENT_ONLY':'point means positive in both but simultaneous proof gate not met',
   'FAILED_OR_UNIDENTIFIABLE':'sign failure, insufficient observations, or missing post-sample data'},
 'minimum_observations_per_split':36,
 'missing_data_policy':'series-level pairwise deletion; no interpolation; insufficient split is unidentifiable',
 'no_live_promotion':True,'live_decision_weight':0.0,'capital_permission':'BLOCKED',
 'claim_limit':'Historical factor-return persistence in AQR-maintained series; not independent trade implementation, current ticker selection, net executable alpha, or capital permission.',
 'trial_accounting':'All 39 registered claims count, including market-specific weak series. No survivor-only correction.',
 'forbidden':['change split after results','drop failed series','change costs after results','treat maintained reconstruction as untouched raw vintage','convert factor persistence directly into War Room direction']
}
text=json.dumps(protocol,sort_keys=True,indent=2)
out=ROOT/'protocols/V58_PUBLIC_FACTOR_POSTSAMPLE_PROTOCOL_FROZEN.json'; out.write_text(text)
(ROOT/'protocols/V58_PUBLIC_FACTOR_POSTSAMPLE_PROTOCOL_FROZEN.sha256.txt').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+out.name+'\n')
print(out); print('claims',len(claims)); print('sha',hashlib.sha256(text.encode()).hexdigest())

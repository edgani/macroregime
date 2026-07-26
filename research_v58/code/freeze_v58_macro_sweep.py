from __future__ import annotations
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/mnt/data/v58_work/research_v58')
features=[]
def add(n,f,form):features.append({'feature':n,'family':f,'formula':form})
for h in [1,3,6,12,24,36,60]:add(f'spx_mom_{h}','trend',f'spx pct change {h}m')
for h in [3,6,12,24,36,60]:add(f'spx_vol_{h}','volatility',f'spx monthly return rolling std {h}m')
for h in [12,24,60,120]:add(f'spx_drawdown_{h}','fragility',f'spx / rolling max {h}m - 1')
for h in [12,24,60,120]:add(f'cape_z_{h}','valuation',f'CAPE rolling z {h}m')
add('cape_level','valuation','CAPE level');add('cape_change_12','valuation','CAPE 12m change')
for x in ['cpi_yoy','rate10']:
 add(f'{x}_level','macro',f'{x} level')
 for h in [3,6,12,24]:add(f'{x}_change_{h}','macro',f'{x} change {h}m')
add('real_rate','macro','rate10-cpi_yoy');add('real_rate_change_12','macro','12m change of rate10-cpi_yoy')
for asset in ['gold','oil','gas','dxy']:
 for h in [1,3,6,12,24,36]:add(f'{asset}_mom_{h}','cross_asset',f'{asset} pct change {h}m')
 for h in [6,12,24]:add(f'{asset}_vol_{h}','cross_asset',f'{asset} monthly return rolling std {h}m')
for n,form in [
 ('oil_gold_ratio_mom12','oil/gold ratio 12m change'),('gas_oil_ratio_mom12','gas/oil ratio 12m change'),('commodity_dxy_divergence','mean gold/oil/gas 12m momentum minus dxy 12m momentum'),
 ('inflation_oil_gap','cpi_yoy minus oil 12m momentum'),('rate_inflation_gap','rate10 minus cpi_yoy'),('valuation_rate_interaction','cape z120 times rate10'),
 ('valuation_momentum_interaction','-cape z120 plus spx mom12'),('inflation_momentum_interaction','-cpi_yoy plus spx mom12'),('cross_asset_stress','dxy mom6 minus mean gold/oil/gas mom6'),
 ('commodity_dispersion','cross-sectional std gold/oil/gas 12m momentum'),('calendar_month_placebo','month number'),('linear_time_placebo','sequential month index'),
 ('fourier_7y_placebo','sinusoid 84m'),('fourier_10y_placebo','sinusoid 120m'),('deterministic_noise_placebo','fixed hash-like sine')]:add(n,'interaction_or_placebo',form)
targets=[{'name':'future_6m_return','horizon':6},{'name':'future_12m_return','horizon':12},{'name':'future_6m_drawdown_loss','horizon':6},{'name':'future_6m_realized_vol','horizon':6}]
p={'schema':'warroom.v58.macro_sweep_protocol.v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'dataset':'bundled revised monthly macro panel 1881-2023',
 'features':features,'feature_count':len(features),'targets':targets,'registered_claims':len(features)*len(targets),
 'splits':{'discovery':'1973-01/1994-12','validation':'1995-01/2007-12','diagnostic_holdout':'2008-01/2023-09'},
 'orientation':'sign chosen from discovery Spearman correlation and frozen','primary_metric':'monthly Spearman association with future target','HAC_lags':12,
 'multiplicity':'one-sided Bonferroni over all registered feature-target claims','status_limit':'REVISED_REUSED_MACRO_DIAGNOSTIC_ONLY; no vintage data and panel used in prior research',
 'live_decision_weight':0.0,'capital_permission':'BLOCKED','forbidden':['live promotion','retune holdout','claim realtime availability','ignore overlapping horizons','drop placebos']}
text=json.dumps(p,indent=2,sort_keys=True);o=ROOT/'protocols/V58_MACRO_SWEEP_PROTOCOL_FROZEN.json';o.write_text(text);(ROOT/'protocols/V58_MACRO_SWEEP_PROTOCOL_FROZEN.sha256.txt').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+o.name+'\n')
print('features',len(features),'claims',p['registered_claims'],'sha',hashlib.sha256(text.encode()).hexdigest())

from __future__ import annotations
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/mnt/data/v58_work/research_v58')
features=[]
def add(name,family,formula):features.append({'feature':name,'family':family,'formula':formula})
for h in [1,3,5,10,21,42,63,126,252]:add(f'mom_{h}','momentum',f'close/close.shift({h})-1')
for h in [1,3,5,10,21]:add(f'reversal_{h}','reversal',f'-(close/close.shift({h})-1)')
for long,skip in [(63,5),(126,21),(252,21)]:add(f'mom_{long}_skip_{skip}','momentum',f'close.shift({skip})/close.shift({long})-1')
for h in [5,10,21,42,63,126]:
 add(f'vol_{h}','volatility',f'ret.rolling({h}).std()');add(f'downvol_{h}','volatility',f'min(ret,0).rolling({h}).std()')
for h in [21,63]:
 add(f'skew_{h}','distribution',f'ret.rolling({h}).skew()');add(f'kurt_{h}','distribution',f'ret.rolling({h}).kurt()')
 add(f'maxret_{h}','distribution',f'ret.rolling({h}).max()');add(f'minret_{h}','distribution',f'ret.rolling({h}).min()')
for h in [21,63,126,252]:
 add(f'dist_high_{h}','breakout',f'close/close.rolling({h}).max()-1');add(f'dist_low_{h}','breakout',f'close/close.rolling({h}).min()-1')
for h in [5,10,21,42,63,126,252]:add(f'sma_dist_{h}','trend',f'close/close.rolling({h}).mean()-1')
for h in [10,21,42,63,126]:add(f'efficiency_{h}','path',f'abs(close/shift({h})-1)/sum(abs(ret),{h})')
for h in [5,21,63]:
 add(f'volume_z_{h}','volume',f'(log_volume-mean_{h})/std_{h}');add(f'dollar_volume_{h}','liquidity',f'rolling mean(close*volume,{h})')
 add(f'amihud_{h}','liquidity',f'rolling mean(abs(ret)/(close*volume),{h})');add(f'range_{h}','range',f'rolling mean((high-low)/close,{h})')
 add(f'clv_{h}','microstructure',f'rolling mean((close-low)/(high-low),{h})')
for a,b in [(5,21),(10,63),(21,63)]:add(f'volume_ratio_{a}_{b}','volume',f'mean_volume_{a}/mean_volume_{b}')
for h in [5,21,63]:add(f'intraday_{h}','session',f'rolling mean(close/open-1,{h})');add(f'overnight_{h}','session',f'rolling mean(open/prev_close-1,{h})')
for h in [21,63,126]:add(f'beta_{h}','market',f'rolling cov(ret,market_ret,{h})/rolling var(market_ret,{h})')
for h in [21,63,126]:add(f'residual_mom_{h}','market',f'mom_{h}-beta_{h}*market_mom_{h}')
# Explicit interactions and controversial/placebo features.
for n,fam,formula in [
 ('mom63_over_vol21','mom_vol','mom_63/vol_21'),('mom126_over_vol63','mom_vol','mom_126/vol_63'),('mom252_over_vol63','mom_vol','mom_252/vol_63'),
 ('mom63_x_volumez21','interaction','mom_63*volume_z_21'),('dist_high63_x_volumez21','interaction','dist_high_63*volume_z_21'),
 ('reversal5_x_amihud21','interaction','reversal_5*rank(amihud_21)'),('lowvol21_x_mom63','interaction','-vol_21+mom_63'),
 ('range21_x_mom21','interaction','range_21*mom_21'),('clv21_x_volumez21','interaction','clv_21*volume_z_21'),
 ('price_level','placebo','log(close)'),('alphabetical_ticker','placebo','ticker lexical rank'),('calendar_month','placebo','month number'),
 ('deterministic_hash_noise','placebo','sha256(ticker,date) mapped to uniform')]:add(n,fam,formula)
protocol={'schema':'warroom.v58.price_volume_sweep_protocol.v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'dataset':'bundled fixed 483-name US equity OHLCV panel 2013-02 to 2018-02','feature_count':len(features),'features':features,
 'targets':[{'name':'future_21d_return','horizon_days':21},{'name':'future_63d_return','horizon_days':63}],
 'registered_claims':len(features)*2,'sampling':'last available observation per calendar month','splits':{'discovery':'2014-01-01/2015-12-31','validation':'2016-01-01/2016-12-31','diagnostic_holdout':'2017-01-01/2018-02-28'},
 'orientation':'feature sign chosen only from discovery mean Spearman IC, then frozen for validation and diagnostic holdout',
 'primary_metric':'monthly cross-sectional Spearman IC','secondary_metric':'monthly top-minus-bottom quintile future return','multiplicity':'one-sided Bonferroni over all registered feature-target claims',
 'status_limit':'REUSED_FIXED_UNIVERSE_DIAGNOSTIC_ONLY; panel has survivorship/corporate-action limitations and has been used previously; no result is untouched proof',
 'live_decision_weight':0.0,'capital_permission':'BLOCKED','forbidden':['promotion to live','claim point-in-time universe','ignore placebos','drop negative trials','retune from diagnostic holdout']}
text=json.dumps(protocol,indent=2,sort_keys=True);p=ROOT/'protocols/V58_PRICE_VOLUME_SWEEP_PROTOCOL_FROZEN.json';p.write_text(text)
(ROOT/'protocols/V58_PRICE_VOLUME_SWEEP_PROTOCOL_FROZEN.sha256.txt').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+p.name+'\n')
print('features',len(features),'claims',len(features)*2,'sha',hashlib.sha256(text.encode()).hexdigest())

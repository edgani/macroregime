from pathlib import Path
import csv, json, hashlib
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'research_v62'; P=R/'protocols'; P.mkdir(parents=True,exist_ok=True)
event=[]
for base in ['pos_gapz_max','neg_gapz_max','pos_event_max','neg_event_max','pos_event_sum','neg_event_sum','pos_event_ema','neg_event_ema']:
    for h in [5,10,21]: event.append(f'{base}_{h}')
event += ['gap_directional_persistence_5','gap_directional_persistence_10','gap_directional_persistence_21',
          'event_volume_persistence_5','event_volume_persistence_10','event_volume_persistence_21',
          'gap_hold_5','gap_hold_10','gap_hold_21','gap_fill_pressure_5','gap_fill_pressure_10','gap_fill_pressure_21']
self_features=['self_ret_5','self_ret_21','self_ret_63','self_mom_252_21','self_atr_63','self_compression_20_63','self_volume_ratio_5_20','self_dist_high_63','self_range_loc_63']
rows=[]
for e in event:
    for eo in [1,-1]:
        rows.append({'candidate_id':f'single|{e}|{eo:+d}','kind':'single','event_feature':e,'event_orientation':eo,'self_feature':'','self_orientation':'','third_feature':'','third_orientation':''})
        for s in self_features:
            for so in [1,-1]:
                rows.append({'candidate_id':f'pair|{e}|{eo:+d}|{s}|{so:+d}','kind':'pair','event_feature':e,'event_orientation':eo,'self_feature':s,'self_orientation':so,'third_feature':'','third_orientation':''})
# Mechanistically constrained triples only: event impulse + underreaction/position + confirmation.
third=['self_volume_ratio_5_20','self_compression_20_63','self_range_loc_63']
for e in [x for x in event if ('event_max' in x or 'event_ema' in x or 'gapz_max' in x)]:
    for eo in [1,-1]:
        for s in ['self_ret_5','self_ret_21','self_dist_high_63']:
            for so in [1,-1]:
                for th in third:
                    for to in [1,-1]:
                        rows.append({'candidate_id':f'triple|{e}|{eo:+d}|{s}|{so:+d}|{th}|{to:+d}','kind':'triple','event_feature':e,'event_orientation':eo,'self_feature':s,'self_orientation':so,'third_feature':th,'third_orientation':to})
# dedupe
seen=set(); out=[]
for r in rows:
    if r['candidate_id'] not in seen: seen.add(r['candidate_id']);out.append(r)
grid=P/'V62_EVENT_ORIGIN_CANDIDATE_GRID_FROZEN.csv'
with grid.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
proto={
 'schema':'warroom.v62.event_origin_protocol.v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'dataset':'bundled fixed 483-name US equity OHLCV panel, 2013-02-08 through 2018-02-07',
 'claim':'recent discrete overnight-gap plus abnormal-volume impulses and their post-event hold/fade state may identify underreaction or overreaction before extreme future moves',
 'causal_limit':'OHLCV event proxy does not identify whether the event was earnings, guidance, M&A, litigation, macro, or corporate action',
 'splits':{'discovery':['2013-02-08','2015-12-31'],'validation':['2016-01-01','2016-12-31'],'lockbox':['2017-01-01','2018-02-07']},
 'features':event,'self_features':self_features,'candidate_count':len(out),
 'targets':[{'name':'up20_21','direction':'UP','threshold':.20,'horizon':21},{'name':'up30_63','direction':'UP','threshold':.30,'horizon':63},{'name':'up50_126','direction':'UP','threshold':.50,'horizon':126},{'name':'down20_63','direction':'DOWN','threshold':-.20,'horizon':63}],
 'selection':'top 5% cross-section daily; exact ceil(0.05*483)',
 'baselines':['12-1 momentum with target direction','ATR63/high-volatility'],
 'multiplicity':'one-sided Bonferroni over candidate x target x two baselines; validation and untouched lockbox adjusted lower bounds both >0 against both baselines',
 'minimum_events':10,'corporate_action_filter':'exclude +-45% jumps with split/spinoff reversal-like signature and surrounding 252/126-day contamination window',
 'status_limit':'DIAGNOSTIC_ONLY because fixed survivor-biased 2013-2018 panel lacks point-in-time membership, delistings, and event labels',
 'forbidden':['label proxy as earnings surprise','retune after lockbox','promote to live','ignore failed claims'],
 'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
pp=P/'V62_EVENT_ORIGIN_PROTOCOL_FROZEN.json';pp.write_text(json.dumps(proto,indent=2,sort_keys=True)+'\n')
(P/'V62_EVENT_ORIGIN_PROTOCOL_FROZEN.sha256').write_text(hashlib.sha256(pp.read_bytes()).hexdigest()+'  '+pp.name+'\n')
(P/'V62_EVENT_ORIGIN_CANDIDATE_GRID_FROZEN.sha256').write_text(hashlib.sha256(grid.read_bytes()).hexdigest()+'  '+grid.name+'\n')
print(json.dumps({'candidate_count':len(out),'registered_claims':len(out)*4,'protocol_sha256':hashlib.sha256(pp.read_bytes()).hexdigest()},indent=2))

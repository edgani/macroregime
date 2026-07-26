from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'research_v61'
network_features=[]
for method in ['cluster24','cluster48','corr20']:
    for h in [5,21,63]:
        network_features += [f'{method}_peer_ret_{h}', f'{method}_peer_breadth_{h}']
    network_features += [f'{method}_peer_accel_5_21',f'{method}_peer_accel_21_63',
                         f'{method}_peer_volume_ratio_5_20',f'{method}_peer_breakout_share_63',
                         f'{method}_follower_gap_5',f'{method}_follower_gap_21',f'{method}_follower_gap_63',
                         f'{method}_network_residual_21',f'{method}_network_residual_63']
# Fixed self contexts; all values known at t.
self_features=['self_ret_5','self_ret_21','self_ret_63','self_mom_252_21','self_atr_63',
               'self_compression_20_63','self_volume_ratio_5_20','self_dist_high_63','self_range_loc_63']
# Single network feature orientations.
rows=[]
for nf in network_features:
    for orient in [1,-1]:
        rows.append({'candidate_id':f'single|{nf}|{orient:+d}','kind':'single','network_feature':nf,'network_orientation':orient,
                     'self_feature':'','self_orientation':0,'third_feature':'','third_orientation':0})
# Causally constrained follower/leader interactions. Rank-average, never unrestricted multiplication.
pairs=[]
for nf in network_features:
    if any(x in nf for x in ['peer_ret_','peer_breadth_','peer_accel_','peer_volume','peer_breakout','follower_gap']):
        for sf in self_features:
            # Four explicitly registered orientation combinations.
            for no,so in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                pairs.append({'candidate_id':f'pair|{nf}|{no:+d}|{sf}|{so:+d}','kind':'pair','network_feature':nf,'network_orientation':no,
                              'self_feature':sf,'self_orientation':so,'third_feature':'','third_orientation':0})
# Small predeclared sequence family: peers lead, ticker is compressed/lagging, then own volume wakes.
triples=[]
for method in ['cluster24','cluster48','corr20']:
    for h in [21,63]:
        triples.append({'candidate_id':f'sequence|{method}|peer_lead_{h}|compression|volume_wake','kind':'triple',
                        'network_feature':f'{method}_follower_gap_{h}','network_orientation':1,
                        'self_feature':'self_compression_20_63','self_orientation':1,
                        'third_feature':'self_volume_ratio_5_20','third_orientation':1})
        triples.append({'candidate_id':f'exhaustion|{method}|self_lead_{h}|peer_weak|near_high','kind':'triple',
                        'network_feature':f'{method}_follower_gap_{h}','network_orientation':-1,
                        'self_feature':f'self_ret_{min(h,63)}','self_orientation':1,
                        'third_feature':'self_dist_high_63','third_orientation':1})
rows += pairs + triples
# deterministic de-dup
seen=set(); uniq=[]
for r in rows:
    if r['candidate_id'] not in seen:
        seen.add(r['candidate_id']);uniq.append(r)
rows=uniq
proto={
 'schema':'warroom.v61.network_diffusion_protocol','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'frozen_before_outcome_open':True,
 'question':'Can discovery-only peer/network diffusion states identify future extreme winners or losers before the ticker move and beat momentum plus volatility baselines in validation and untouched lockbox?',
 'data':'bundled research/sp500_panel.parquet; fixed 483-symbol 2013-2018 diagnostic panel',
 'claim_limit':'The panel is survivor-biased and ends in 2018. A pass is diagnostic replication only, not production proof.',
 'splits':{'discovery':['2013-02-08','2015-12-31'],'validation':['2016-01-01','2016-12-31'],'lockbox':['2017-01-01','2018-02-07']},
 'network_construction':{'fit_period':'discovery only','cluster_counts':[24,48],'correlation_neighbors':20,'linkage':'average','distance':'sqrt(0.5*(1-correlation))'},
 'targets':{'up20_21':'future max return >=20% within 21 sessions','up30_63':'future max return >=30% within 63 sessions','up50_126':'future max return >=50% within 126 sessions','down20_63':'future min return <=-20% within 63 sessions'},
 'selector':'top 5% cross-sectional candidate score each date',
 'baselines':['12-1 momentum with target orientation','ATR63 high-volatility capacity'],
 'score_rule':'daily percentile rank; pair/triple score is arithmetic mean of predeclared oriented ranks',
 'promotion_gate':['candidate contains network observable','validation adjusted lower bound >0 versus both baselines','lockbox adjusted lower bound >0 versus both baselines','minimum 10 selected events in validation and lockbox','no target or threshold retuning'],
 'multiple_testing':'Bonferroni-normal simultaneous bound across every candidate x target x baseline comparison; non-overlapping 21-session block SE',
 'corporate_actions':'same exclusion logic as V60; flags are never predictive features',
 'live_decision_weight':0.0,'capital_permission':'BLOCKED','candidate_count':len(rows)
}
(R/'protocols'/'V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json').write_text(json.dumps(proto,indent=2,sort_keys=True)+'\n')
with (R/'protocols'/'V61_NETWORK_DIFFUSION_CANDIDATE_GRID_FROZEN.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for p in [R/'protocols'/'V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json',R/'protocols'/'V61_NETWORK_DIFFUSION_CANDIDATE_GRID_FROZEN.csv']:
    p.with_suffix(p.suffix+'.sha256.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
print(json.dumps({'status':'FROZEN','candidate_count':len(rows),'protocol':str(R/'protocols'/'V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json')},indent=2))

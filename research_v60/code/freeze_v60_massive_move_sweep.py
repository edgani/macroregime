from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
features=[]
def add(name,family,formula,causal_role='candidate_proxy'):
    features.append({'feature':name,'family':family,'formula':formula,'causal_role':causal_role})

# Price path / trend / acceleration
for h in [1,2,3,5,10,15,21,42,63,84,126,189,252]: add(f'mom_{h}','price_path',f'close/close.shift({h})-1','direction_state')
for h in [1,2,3,5,10,15,21]: add(f'reversal_{h}','price_path',f'-(close/close.shift({h})-1)','short_horizon_reversal')
for a,b in [(3,10),(5,21),(10,42),(21,63),(21,126),(42,126),(63,252)]: add(f'mom_accel_{a}_{b}','price_acceleration',f'mom_{a}-mom_{b}','direction_change')
for long,skip in [(63,5),(126,10),(126,21),(252,21),(252,42)]: add(f'mom_{long}_skip_{skip}','price_path',f'close.shift({skip})/close.shift({long})-1','persistent_direction')

# Volatility, distribution and path shape
for h in [5,10,15,21,42,63,126]:
    add(f'vol_{h}','volatility',f'std(ret,{h})','fragility_or_expansion')
    add(f'downvol_{h}','volatility',f'std(min(ret,0),{h})','downside_fragility')
    add(f'upvol_{h}','volatility',f'std(max(ret,0),{h})','upside_expansion')
    add(f'range_{h}','range',f'mean((high-low)/close,{h})','realized_range')
for a,b in [(5,21),(10,42),(21,63),(21,126),(42,126)]:
    add(f'vol_ratio_{a}_{b}','compression',f'vol_{a}/vol_{b}','compression_expansion')
    add(f'range_ratio_{a}_{b}','compression',f'range_{a}/range_{b}','compression_expansion')
for h in [21,42,63,126]:
    add(f'skew_{h}','distribution',f'skew(ret,{h})','tail_asymmetry')
    add(f'kurt_{h}','distribution',f'kurt(ret,{h})','tail_concentration')
    add(f'maxret_{h}','distribution',f'max(ret,{h})','jump_history')
    add(f'minret_{h}','distribution',f'min(ret,{h})','crash_history')
for h in [10,21,42,63,126]:
    add(f'efficiency_{h}','path_shape',f'abs(return_{h})/sum(abs(ret),{h})','trend_efficiency')
    add(f'positive_day_share_{h}','path_shape',f'mean(ret>0,{h})','buying_persistence')
    add(f'negative_day_share_{h}','path_shape',f'mean(ret<0,{h})','selling_persistence')

# Breakout / recovery / drawdown
for h in [21,42,63,126,189,252]:
    add(f'dist_high_{h}','breakout',f'close/rolling_max(close,{h})-1','distance_to_supply')
    add(f'dist_low_{h}','breakout',f'close/rolling_min(close,{h})-1','distance_from_capitulation')
    add(f'drawdown_{h}','breakout',f'close/rolling_max(close,{h})-1','drawdown_state')
for h in [5,10,21,42,63,126,252]: add(f'sma_dist_{h}','trend',f'close/rolling_mean(close,{h})-1','trend_state')
for a,b in [(5,21),(10,42),(21,63),(21,126),(42,252)]: add(f'sma_spread_{a}_{b}','trend',f'sma_dist_{a}-sma_dist_{b}','trend_transition')

# Volume, dollar-flow and liquidity proxies
for h in [5,10,15,21,42,63,126]:
    add(f'volume_z_{h}','volume',f'zscore(log(volume),{h})','participation_shock')
    add(f'dollar_volume_{h}','liquidity',f'mean(close*volume,{h})','capacity')
    add(f'dollar_volume_z_{h}','liquidity',f'zscore(log(close*volume),{h})','capital_flow_proxy')
    add(f'amihud_{h}','liquidity',f'mean(abs(ret)/(close*volume),{h})','price_impact')
for a,b in [(3,21),(5,21),(5,63),(10,42),(21,63),(21,126)]:
    add(f'volume_ratio_{a}_{b}','volume',f'mean(volume,{a})/mean(volume,{b})','participation_acceleration')
    add(f'dollar_volume_ratio_{a}_{b}','liquidity',f'mean(dollar_volume,{a})/mean(dollar_volume,{b})','capital_acceleration')

# Signed OHLCV proxies: explicitly proxies, never called institutional flow.
for h in [5,10,21,42,63]:
    add(f'clv_{h}','signed_volume_proxy',f'mean(close_location_value,{h})','close_pressure_proxy')
    add(f'up_volume_share_{h}','signed_volume_proxy',f'sum(volume where ret>0)/sum(volume,{h})','up_day_volume_share')
    add(f'signed_volume_{h}','signed_volume_proxy',f'sum(sign(ret)*volume,{h})/sum(volume,{h})','tick_rule_flow_proxy')
    add(f'clv_volume_{h}','signed_volume_proxy',f'sum(clv*volume,{h})/sum(volume,{h})','accumulation_distribution_proxy')
    add(f'obv_slope_{h}','signed_volume_proxy',f'change(cumsum(sign(ret)*volume),{h})/mean(volume,{h})','obv_proxy')
    add(f'mfv_{h}','signed_volume_proxy',f'sum(money_flow_multiplier*volume,{h})/sum(volume,{h})','chaikin_proxy')

# Session decomposition and gap behavior
for h in [5,10,21,42,63]:
    add(f'intraday_{h}','session',f'mean(close/open-1,{h})','regular_session_demand')
    add(f'overnight_{h}','session',f'mean(open/prev_close-1,{h})','overnight_information')
    add(f'gap_abs_{h}','session',f'mean(abs(open/prev_close-1),{h})','information_jump')
    add(f'gap_followthrough_{h}','session',f'corr(overnight,intraday,{h})','gap_acceptance')

# Market-relative features
for h in [21,42,63,126,252]:
    add(f'beta_{h}','market_relative',f'rolling_beta(ret,market,{h})','market_loading')
    add(f'residual_mom_{h}','market_relative',f'mom_{h}-beta_{h}*market_mom_{h}','idiosyncratic_direction')
    add(f'rel_strength_{h}','market_relative',f'mom_{h}-market_mom_{h}','relative_strength')

# Mechanistically motivated interactions, not unrestricted pair mining.
interaction_specs=[]
for m in [5,10,21,42,63,126]:
    for v in [5,21,63]: interaction_specs.append((f'mom{m}_x_volumez{v}',f'mom_{m}*volume_z_{v}','price_volume_confirmation'))
for h in [21,42,63,126]:
    interaction_specs += [
      (f'breakout{h}_x_volumez21',f'dist_high_{h}*volume_z_21','breakout_participation'),
      (f'recovery{h}_x_clv21',f'dist_low_{h}*clv_21','recovery_pressure'),
      (f'mom{h}_over_vol21',f'mom_{h}/vol_21','risk_adjusted_direction'),
      (f'residualmom{h}_x_volumez21',f'residual_mom_{h}*volume_z_21','idiosyncratic_participation'),
    ]
for a,b in [(5,21),(10,42),(21,63),(21,126)]:
    interaction_specs += [
      (f'compression{a}_{b}_x_volumez{a}',f'-vol_ratio_{a}_{b}*volume_z_{a}','compression_release'),
      (f'rangecompression{a}_{b}_x_clv{a}',f'-range_ratio_{a}_{b}*clv_{a}','range_release'),
      (f'accel{a}_{b}_x_volumez21',f'mom_accel_{a}_{b}*volume_z_21','acceleration_participation'),
    ]
for h in [5,10,21,42,63]:
    interaction_specs += [
      (f'signedvolume{h}_x_volumez{h}',f'signed_volume_{h}*volume_z_{h}','signed_participation_proxy'),
      (f'clvvolume{h}_x_amihud21',f'clv_volume_{h}*rank(amihud_21)','pressure_vs_depth_proxy'),
      (f'upvolshare{h}_x_relstrength63',f'up_volume_share_{h}*rel_strength_63','relative_accumulation_proxy'),
    ]
for name,formula,role in interaction_specs: add(name,'interaction',formula,role)

# Explicit placebos / falsification controls.
for n,formula in [
 ('price_level','log(close)'),('alphabetical_ticker','ticker lexical rank'),('calendar_week','ISO week number'),
 ('deterministic_hash_noise_1','hash(ticker,date,1)'),('deterministic_hash_noise_2','hash(ticker,date,2)'),
 ('reverse_alphabetical','negative ticker lexical rank')]: add(n,'placebo',formula,'negative_control')

# Three warning breadths are separately registered claims.
targets=[
 {'name':'up_21d_30pct','direction':'UP','horizon_days':21,'threshold':0.30},
 {'name':'up_42d_50pct','direction':'UP','horizon_days':42,'threshold':0.50},
 {'name':'up_63d_80pct','direction':'UP','horizon_days':63,'threshold':0.80},
 {'name':'up_126d_100pct','direction':'UP','horizon_days':126,'threshold':1.00},
 {'name':'down_21d_20pct','direction':'DOWN','horizon_days':21,'threshold':-0.20},
 {'name':'down_42d_30pct','direction':'DOWN','horizon_days':42,'threshold':-0.30},
 {'name':'down_63d_50pct','direction':'DOWN','horizon_days':63,'threshold':-0.50},
]
top_fractions=[0.05,0.10,0.20]
claims=len(features)*len(targets)*len(top_fractions)
protocol={
 'schema':'warroom.v60.massive_move_precursor_protocol.v1',
 'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'dataset':'bundled fixed 483-name US equity OHLCV panel, 2013-02-08 through 2018-02-07',
 'sampling':'last available observation of each ISO week; feature at t predicts future extrema strictly after t',
 'features':features,'feature_count':len(features),'targets':targets,'top_fractions':top_fractions,
 'registered_claims':claims,
 'splits':{'discovery':'2013-08-01/2015-12-31','validation':'2016-01-01/2016-12-31','diagnostic_lockbox':'2017-01-01/2018-02-07'},
 'orientation':'feature sign chosen solely in discovery to maximize mean top-tail event-rate improvement; then frozen',
 'primary_metric':'weekly top-tail event-rate minus contemporaneous universe event-rate',
 'secondary_metrics':['precision lift','recall at selected tail','median lead time where identifiable','mean forward terminal return','MFE','MAE'],
 'multiplicity':'one-sided Bonferroni over every feature x target x top-fraction claim; both validation and diagnostic lockbox lower bounds must exceed zero',
 'baseline':'contemporaneous event prevalence; no-signal ranking',
 'status_limit':'DIAGNOSTIC_ONLY: reused fixed universe; survivorship, delisting, corporate-action and point-in-time membership limitations; cannot establish production proof',
 'cost_stress_bps_round_trip':[0,25,50],
 'live_decision_weight':0.0,'capital_permission':'BLOCKED',
 'forbidden':['rename OHLCV proxy as institutional accumulation','use diagnostic lockbox to retune','omit failed/placebo claims','promote to live','claim SNDK-specific proof from a panel that does not contain current SNDK']
}
text=json.dumps(protocol,indent=2,sort_keys=True)
p=ROOT/'protocols/V60_MASSIVE_MOVE_PRECURSOR_PROTOCOL_FROZEN.json';p.write_text(text)
h=hashlib.sha256(text.encode()).hexdigest();(p.with_suffix('.sha256.txt')).write_text(f'{h}  {p.name}\n')
print(json.dumps({'features':len(features),'targets':len(targets),'top_fractions':len(top_fractions),'claims':claims,'sha256':h},indent=2))

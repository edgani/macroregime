from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, math, collections
from datetime import datetime, timezone
B=Path('/mnt/data/warroom_v60_work/src');O=B/'research_v60'
for d in ['protocols','results','ledgers','reports']: (O/d).mkdir(parents=True,exist_ok=True)
P={'study_id':'V62_UNIFIED_GLOBAL_MULTIPLE_TESTING_ACCOUNTING','purpose':'Place all new data-ready V60 trials into one global discovery budget instead of correcting each attractive family in isolation.','batteries':{'absolute_extreme_winner':34322,'relative_top5_winner':34322,'absolute_extreme_loser':34322,'OpenAP_all_pair_signs':89464},'total_registered':192430,'correction':'Benjamini-Hochberg FDR across every available validation p-value from all four batteries','limits':['Different endpoints and data structures are pooled conservatively for accounting','Earlier V58 795 trials lack compatible per-claim validation p-values and are counted in cumulative trial history but not recomputed here','OpenAP maintained portfolio returns are not stock-level signals','Price-volume panel is fixed-universe 2013-2018 and likely survivorship-biased'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
pp=O/'protocols/V62_GLOBAL_MULTIPLE_TESTING_PROTOCOL_FROZEN.json';pp.write_text(json.dumps(P,indent=2,sort_keys=True));ph=hashlib.sha256(pp.read_bytes()).hexdigest()
frames=[]
def add(path,battery,pcol,idcol='candidate_id'):
 d=pd.read_csv(path);q=pd.DataFrame({'battery':battery,'candidate_id':d[idcol].astype(str),'validation_p':pd.to_numeric(d[pcol],errors='coerce').fillna(1.0)})
 if 'passes_full_gate' in d:q['battery_gate']=d.passes_full_gate.astype(str).str.lower().isin(['true','1'])
 elif 'passes_statistical_gate' in d:q['battery_gate']=d.passes_statistical_gate.astype(str).str.lower().isin(['true','1'])
 else:q['battery_gate']=False
 frames.append(q)
add(O/'ledgers/V60_MASSIVE_MOVE_GLOBAL_TRIAL_LEDGER.csv','absolute_extreme_winner','val_p_precision_improvement')
add(O/'ledgers/V60_RELATIVE_WINNER_GLOBAL_TRIAL_LEDGER.csv','relative_top5_winner','validation_p')
add(O/'ledgers/V60_ABSOLUTE_LOSER_GLOBAL_TRIAL_LEDGER.csv','absolute_extreme_loser','validation_p')
add(O/'ledgers/V60_OPENAP_PAIR_GLOBAL_LEDGER.csv','OpenAP_all_pair_signs','validation_p')
D=pd.concat(frames,ignore_index=True);assert len(D)==P['total_registered'],len(D)
p=D.validation_p.clip(0,1).to_numpy();order=np.argsort(p);q=np.empty_like(p);prev=1.0;m=len(p)
for rank,ix in reversed(list(enumerate(order,start=1))):
 val=min(prev,p[ix]*m/rank);q[ix]=val;prev=val
D['global_q_all_new_trials']=q;D['global_fdr_survivor']=D.global_q_all_new_trials<.05
rob=pd.read_csv(O/'ledgers/V61_OPENAP_PAIR_ROBUSTNESS_LEDGER.csv');strict=set(rob.loc[rob.passes_strict_robustness.astype(str).str.lower().isin(['true','1']),'candidate_id'])
cap=pd.read_csv(O/'ledgers/V61_OPENAP_CAPACITY_STRESS_LEDGER.csv');caps=set(cap.loc[cap.passes_capacity_stress.astype(str).str.lower().isin(['true','1']),'candidate_id'])
D['strict_robustness_survivor']=D.candidate_id.isin(strict)&(D.battery=='OpenAP_all_pair_signs');D['capacity_stress_survivor']=D.candidate_id.isin(caps)&(D.battery=='OpenAP_all_pair_signs')
D['research_candidate_only']=D.global_fdr_survivor&D.battery_gate&D.strict_robustness_survivor&D.capacity_stress_survivor
D['live_decision_weight']=0.0;D['capital_permission']='BLOCKED';D.to_csv(O/'ledgers/V62_UNIFIED_GLOBAL_TRIAL_LEDGER.csv',index=False)
by=D.groupby('battery').agg(registered=('candidate_id','size'),global_fdr_survivors=('global_fdr_survivor','sum'),battery_gate=('battery_gate','sum'),research_candidates=('research_candidate_only','sum')).reset_index()
S={'study_id':P['study_id'],'protocol_sha256':ph,'new_trials_registered':len(D),'prior_v58_trials_counted_not_recomputed':795,'cumulative_empirical_trial_count':len(D)+795,'global_fdr_survivors':int(D.global_fdr_survivor.sum()),'research_candidate_only_after_all_available_stresses':int(D.research_candidate_only.sum()),'by_battery':by.to_dict('records'),'claim_status':'RESEARCH_CANDIDATES_NOT_STOCK_LEVEL_PROOF','predictive_components_promoted_to_live':0,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
(O/'results/V62_UNIFIED_GLOBAL_RESULTS.json').write_text(json.dumps(S,indent=2,default=str))

# Finite scientific search grammar. Literal all formulas is infinite; register a bounded causal grammar instead.
U=pd.read_csv(B/'research_v58/V58_RESEARCH_UNIVERSE.csv')
transforms=['level','first_difference','percent_change','z_score','cross_sectional_percentile','acceleration','surprise_vs_expectation','dispersion','concentration','persistence']
horizons=['1d','5d','20d','63d','126d','252d']
targets=['direction_up','direction_down','relative_winner','relative_loser','extreme_up','extreme_down','volatility_transition','range_error','lead_time']
regimes=['unconditional','risk_on','risk_off','high_vol','low_vol','liquid','illiquid','macro_event','non_event','early_cycle','late_cycle']
operators=['additive_rank','AND_gate','interaction_product','residualized','lead_lag','threshold_state']
single=len(U)*len(transforms)*len(horizons)*len(targets)*len(regimes)
pair_base=len(U)*(len(U)-1)//2
pair_potential=pair_base*4*len(operators)*len(horizons)*len(targets)*len(regimes)
markets={
'US_STOCKS':['point_in_time_financials','earnings_surprises','analyst_revisions','guidance','order_backlog','customer_supplier_network','capacity_and_pricing','institutional_ownership','short_borrow','insider_buyback_issuance','ETF_fund_flow','options_surface_signed_flow','trade_order_book','news_attention'],
'IHSG':['point_in_time_financials','issuer_disclosures','broker_inventory_persistence','foreign_domestic_flow','crossing_adjustment','free_float_controller','corporate_actions','commodity_and_fx_exposure','customer_supplier_network','order_book_done_detail','SSF_futures'],
'COMMODITIES':['COT_TFF_disaggregated','exchange_OI_volume','signed_trade_flow','futures_curve','options_surface','inventory','physical_differentials','freight_storage','production_consumption','capacity_outage','weather','policy_geopolitics'],
'FX':['TFF_positioning','rate_OIS_surprise','real_rate_value','cross_currency_basis','options_skew_term_structure','reserve_intervention','external_debt_mismatch','terms_of_trade','trade_flow','order_book'],
'CRYPTO':['venue_OI','funding_basis','signed_liquidations','aggressor_flow','order_book_depth','options_surface','onchain_exchange_flow','stablecoin_impulse','token_unlock_emissions','protocol_revenue_usage','bridge_ME​V_flow','narrative_attention']}
G={'schema':'warroom.v62.causal_discovery_grammar.v1','base_candidates':len(U),'base_family_counts':U.family.value_counts().to_dict(),'transforms':transforms,'horizons':horizons,'targets':targets,'regimes':regimes,'interaction_operators':operators,'single_claim_potential':single,'pair_base_count':pair_base,'pair_claim_potential_if_naively_expanded':pair_potential,'scientific_rule':'Do not instantiate an infinite or outcome-driven formula zoo. Register bounded causal claims, data lineage and claim limits before outcomes; use hierarchical testing and untouched prospective evidence.','market_observable_families':markets,'data_ready_new_trials_completed':len(D),'cumulative_trials_including_v58':len(D)+795,'current_live_promotions':0,'capital_permission':'BLOCKED'}
(O/'results/V62_CAUSAL_DISCOVERY_GRAMMAR.json').write_text(json.dumps(G,indent=2,sort_keys=True))
# Market acquisition matrix
rows=[]
for market,fams in markets.items():
 for fam in fams:
  rows.append({'market':market,'observable_family':fam,'mapping_status':'REGISTERED','historical_data_status':'REQUIRES_EXACT_SOURCE_AUDIT','point_in_time_required':True,'signed_or_directional_lineage_required':fam in ['short_borrow','options_surface_signed_flow','trade_order_book','broker_inventory_persistence','foreign_domestic_flow','COT_TFF_disaggregated','signed_trade_flow','TFF_positioning','signed_liquidations','aggressor_flow'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
pd.DataFrame(rows).to_csv(O/'ledgers/V62_CROSS_MARKET_DATA_ACQUISITION_MATRIX.csv',index=False)
print(json.dumps(S,indent=2));print('grammar single',single,'pair potential',pair_potential)

from __future__ import annotations
import csv, json, hashlib, os, re
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT=Path('/mnt/data/v58_work')
OUT=ROOT/'research_v58'
SRC=Path('/mnt/data/SignalDoc.csv')

def sha256(p: Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def slug(s:str)->str:
    return re.sub(r'[^A-Z0-9]+','_',s.upper()).strip('_')

def role_for(row):
    econ=str(row.get('Cat.Economic','')).lower(); data=str(row.get('Cat.Data','')).lower(); desc=str(row.get('LongDescription','')).lower()
    if any(x in econ+desc for x in ['liquidity','short interest','volume','order','trading','turnover']): return 'execution_or_flow'
    if any(x in econ+desc for x in ['volatility','risk','beta','skew','tail']): return 'vulnerability_or_range'
    if any(x in econ+desc for x in ['earnings','profit','investment','accrual','quality','valuation']): return 'value_capture'
    if any(x in econ+desc for x in ['momentum','reversal','price trend']): return 'direction'
    if data=='options': return 'range_timing_or_transmission'
    if data in ('analyst','event','13f'): return 'information_flow_or_positioning'
    return 'cross_sectional_selection'

def mk(cid,family,name,thesis,role,markets,data_required,source_class='curated_primary_literature',status='MAPPED_NOT_TESTED',notes='',variants=None):
    return {
      'candidate_id':cid,'family':family,'name':name,'thesis':thesis,'primary_role':role,
      'market_scope':markets,'data_required':data_required,'source_class':source_class,
      'mapping_status':'COMPLETE','discovery_status':status,'validation_status':'NOT_STARTED',
      'lockbox_status':'NOT_OPENED','prospective_status':'NOT_STARTED','live_decision_weight':0.0,
      'capital_permission':'BLOCKED','claim_ceiling':'Candidate hypothesis only until frozen OOS/lockbox and prospective evidence.',
      'forbidden_shortcuts':['post-outcome retuning','survivor-only reporting','look-ahead','unlogged trials'],
      'notes':notes,'planned_variant_axes':variants or []
    }

# 331 signals, including predictors, placebos, and drops.
df=pd.read_csv(SRC)
items=[]
for i,row in df.iterrows():
    r=row.to_dict(); typ=str(r.get('Cat.Signal','UNKNOWN')).upper()
    cid=f"OAP_{typ}_{slug(str(r.get('Acronym','SIG')))}"
    items.append({
      'candidate_id':cid,'family':'open_source_cross_sectional_asset_pricing','name':str(r.get('LongDescription')),
      'thesis':str(r.get('Detailed Definition') if pd.notna(r.get('Detailed Definition')) else r.get('LongDescription')),
      'primary_role':role_for(r),'market_scope':['US_equities_cross_section'],
      'data_required':[str(r.get('Cat.Data'))],'source_class':'OpenSourceAP_SignalDoc_official',
      'source_signal_class':typ,'original_authors':str(r.get('Authors')),'original_year':None if pd.isna(r.get('Year')) else int(r.get('Year')),
      'original_sample_start':None if pd.isna(r.get('SampleStartYear')) else int(r.get('SampleStartYear')),
      'original_sample_end':None if pd.isna(r.get('SampleEndYear')) else int(r.get('SampleEndYear')),
      'reported_t_stat':None if pd.isna(r.get('T-Stat')) else float(r.get('T-Stat')),
      'economic_category':str(r.get('Cat.Economic')),'data_category':str(r.get('Cat.Data')),
      'mapping_status':'COMPLETE','discovery_status':'IMPORTED_NOT_RETESTED','validation_status':'NOT_STARTED',
      'lockbox_status':'NOT_OPENED','prospective_status':'NOT_STARTED','live_decision_weight':0.0,'capital_permission':'BLOCKED',
      'claim_ceiling':'Imported definition; original published evidence is not War Room proof.',
      'forbidden_shortcuts':['treating reported t-stat as replication','dropping placebos','ignoring publication sample','post-outcome retuning'],
      'notes':str(r.get('Notes')) if pd.notna(r.get('Notes')) else ''
    })

# Curated thesis grids. These include strong, weak, controversial, and likely-placebo candidates.
curated=[]
def add(family,names,role,markets,data,thesis_prefix='',variants=None,source='curated_primary_literature'):
    for n in names:
        curated.append(mk(f"CUR_{slug(family)}_{slug(n)}",family,n,
          (thesis_prefix+(' ' if thesis_prefix else '')+n).strip(),role,markets,data,source,variants=variants))

add('credit_leverage_fragility',[
 'credit_to_gdp_gap','debt_service_ratio','household_debt_service','corporate_interest_coverage','refinancing_wall',
 'credit_growth_x_asset_price_growth','nontradable_credit_allocation','leveraged_loan_stress','private_credit_mark_to_model_gap',
 'collateral_value_sensitivity','bank_wholesale_funding_dependence','maturity_mismatch','foreign_currency_debt_mismatch',
 'credit_impulse','lending_standards','delinquency_transition','bank_capital_buffer','shadow_bank_leverage','margin_debt',
 'housing_credit_boom','commercial_real_estate_refinancing','sovereign_bank_doom_loop','credit_dispersion','bank_concentration'
 ],'structural_vulnerability',['cross_market','US','IHSG','FX'],['BIS','FRED','central_bank','bank filings'])
add('funding_liquidity_spiral',[
 'repo_spread','cross_currency_basis','dealer_balance_sheet_capacity','treasury_basis_crowding','swap_spread_dislocation',
 'market_depth_per_unit_volatility','price_impact','bid_ask_stress','funding_liquidity_interaction','haircut_proxy',
 'margin_spiral_proxy','forced_deleveraging','liquidity_commonality','ETF_NAV_dislocation','cash_futures_basis',
 'fails_to_deliver','settlement_stress','collateral_scarcity','central_bank_reserve_scarcity','dollar_funding_stress',
 'liquidity_adjusted_correlation_spike','vol_control_deleveraging','risk_parity_deleveraging','CTA_liquidation_pressure'
 ],'trigger_or_amplification',['cross_market','US','FX','rates','crypto'],['market microstructure','funding','balance sheet'])
add('trend_momentum_reversal',[
 'canonical_12m_tsmom','multi_speed_tsmom','dual_momentum','cross_sectional_12_1_momentum','residual_momentum',
 'industry_momentum','factor_momentum','trend_strength_consistency','breakout_52week_high','moving_average_distance',
 'moving_average_slope','donchian_breakout','channel_breakout','time_series_reversal','short_term_reversal',
 'long_term_reversal','overnight_momentum','intraday_momentum','opening_range_breakout','post_gap_continuation',
 'post_gap_reversal','trend_x_volatility','trend_x_carry','trend_x_positioning','trend_x_macro_regime',
 'absolute_momentum','relative_momentum','path_length_efficiency','trend_entropy','Hurst_exponent','fractional_differencing_trend',
 'Kalman_trend','state_space_trend','trend_after_shock','anti_trend_crowding','moving_average_cross_placebo'
 ],'direction',['all_markets'],['price','returns','volatility'],variants=['lookback','holding','vol scaling','smoothing','cost'])
add('value_quality_investment',[
 'book_to_market','earnings_yield','cashflow_yield','enterprise_value_to_sales','replacement_cost_q','CAPE',
 'shareholder_yield','net_payout_yield','quality_minus_junk','profitability','gross_profitability','ROIC',
 'free_cash_flow_quality','accrual_quality','asset_growth','investment_to_assets','conservative_investment',
 'operating_leverage','financial_leverage_quality','margin_stability','reinvestment_runway','capital_efficiency',
 'intangible_adjusted_value','R_and_D_capitalization','organizational_capital','brand_intangible','value_spread',
 'value_x_momentum','quality_x_value','quality_x_momentum','distress_adjusted_value','sector_neutral_value'
 ],'value_capture',['equities'],['financial statements','prices','estimates'])
add('earnings_expectations_information',[
 'standardized_unexpected_earnings','revenue_surprise','gross_margin_surprise','guidance_revision','EPS_revision',
 'revenue_revision','target_price_revision','estimate_dispersion','dispersion_compression','analyst_breadth',
 'earnings_call_tone','earnings_call_topic_shift','management_language_uncertainty','PEAD','pre_announcement_drift',
 'post_guidance_drift','concurrent_announcement_attention','low_expectation_high_delivery','revision_acceleration',
 'revision_persistence','earnings_quality_x_surprise','capacity_backed_earnings_inflection','order_backlog_inflection',
 'book_to_bill_inflection','inventory_revenue_divergence','cash_conversion_inflection','insider_guidance_gap'
 ],'value_capture_or_information_flow',['equities'],['IBES/estimates','filings','transcripts','prices'])
add('volatility_options_distribution',[
 'variance_risk_premium','downside_variance_risk_premium','upside_variance_risk_premium','SVIX','skew_risk_premium',
 'vol_of_vol_premium','implied_correlation','dispersion_risk_premium','variance_term_structure','skew_term_structure',
 'risk_reversal','butterfly_convexity','event_volatility_premium','jump_risk_premium','tail_put_demand','call_demand',
 'option_volume_imbalance','signed_dealer_gamma','signed_dealer_vanna','signed_dealer_charm','liquidity_normalized_gamma',
 'pin_break_topology','gamma_scalping_breakeven','delta_hedged_option_return','straddle_implied_move','surface_dislocation',
 'local_vol_surface','stochastic_volatility_state','SABR_parameters','Heston_parameters','volatility_of_liquidity',
 'zero_DTE_inventory','expiry_concentration','gross_OI_GEX_placebo','call_wall_placebo','put_wall_placebo',
 'max_pain_placebo','IV_rank_placebo','put_call_ratio','option_open_close_flow','option_trade_direction_flow'
 ],'range_timing_or_transmission',['US_options','futures_options','crypto_options'],['option quotes','trades','OI','Greeks','underlying liquidity'])
add('microstructure_order_flow',[
 'order_book_imbalance','microprice','queue_imbalance','signed_trade_imbalance','Kyle_lambda','Amihud_illiquidity',
 'effective_spread','realized_spread','adverse_selection_component','VPIN','VPIN_placebo','order_flow_toxicity',
 'trade_size_distribution','hidden_liquidity','iceberg_detection','cancel_to_trade_ratio','quote_stuffing_proxy',
 'latency_arbitrage_pressure','closing_auction_imbalance','opening_auction_imbalance','ETF_creation_redemption_flow',
 'dark_pool_share','odd_lot_information','block_trade_follow_through','broker_inventory','dealer_inventory',
 'short_sale_volume','borrow_fee','utilization','lendable_supply','days_to_cover','fail_to_deliver',
 'retail_wholesaler_flow','market_maker_internalization','price_response_asymmetry','liquidity_replenishment',
 'order_flow_persistence','volume_synchronized_imbalance','LOB_resilience','spread_depth_convexity'
 ],'execution_or_short_horizon_flow',['liquid_electronic_markets'],['tick trades','quotes','book','lending'])
add('commodity_physical_curve',[
 'inventory_level','inventory_surprise','inventory_days_of_supply','convenience_yield','futures_basis','curve_slope',
 'curve_curvature','backwardation_persistence','contango_storage_arbitrage','producer_hedging_pressure',
 'consumer_hedging_pressure','managed_money_positioning','physical_premium','regional_basis','transport_bottleneck',
 'storage_capacity_utilization','refinery_utilization','crack_spread','calendar_spread','quality_spread','freight_rate',
 'weather_demand_shock','crop_condition','planting_progress','harvest_progress','mine_supply_disruption',
 'OPEC_compliance','spare_capacity','rig_count','decline_rate','capex_response_lag','substitution_elasticity',
 'recycling_response','inventory_financing_cost','commodity_currency_feedback','China_import_demand','trade_flow_rerouting',
 'sanctions_shipping_insurance','basis_x_momentum','inventory_x_curve','curve_x_positioning'
 ],'direction_range_or_value_capture',['commodities'],['physical balances','futures curve','CFTC','freight','weather'])
add('fx_carry_value_global_dollar',[
 'nominal_carry','real_carry','forward_discount','PPP_value','BEER_value','FEER_value','real_exchange_rate_gap',
 'FX_momentum','FX_reversal','dollar_smile','global_dollar_cycle','cross_currency_basis','reserve_adequacy',
 'external_debt_currency_mismatch','current_account','terms_of_trade','intervention_capacity','reserve_change',
 'policy_surprise','rate_path_revision','risk_reversal','vol_surface','carry_x_global_risk','carry_x_value',
 'carry_x_momentum','commodity_currency','capital_flow_pressure','balance_of_payments_pressure','NDF_onshore_basis',
 'FX_liquidity','fixing_pressure','month_end_rebalance','dealer_positioning','CTA_positioning','PPP_placebo_short_horizon'
 ],'direction_or_relative_value',['FX'],['rates','spot/forward','macro balances','options','flows'])
add('crypto_market_structure',[
 'stablecoin_supply_growth','stablecoin_net_issuance','stablecoin_exchange_flow','perp_funding','perp_basis','open_interest',
 'liquidation_density','liquidation_cascade_risk','collateral_quality','exchange_reserve','ETF_spot_flow','onchain_active_value',
 'realized_cap','MVRV','SOPR','spent_output_age','miner_revenue_stress','staking_unlock','token_emission','protocol_fee_capture',
 'real_yield','bridge_flow','cross_chain_flow','developer_activity','governance_capture','whale_concentration','holder_cohort_flow',
 'DEX_CEX_basis','AMM_liquidity_depth','DLMM_fee_to_IL','impermanent_loss_regime','MEV_pressure','oracle_risk',
 'smart_contract_exploit_risk','venue_fragmentation','funding_x_liquidation','basis_x_flow','narrative_attention',
 'social_velocity','token_unlock_supply','airdrop_farming_pressure','protocol_resource_bottleneck','sequencer_value_capture',
 'blobspace_demand','gas_fee_congestion','gross_OI_GEX_crypto_placebo'
 ],'direction_transmission_or_value_capture',['crypto'],['onchain','exchange','derivatives','protocol fundamentals'])
add('supply_chain_network_bottleneck',[
 'input_output_centrality','supplier_customer_return_spillover','single_source_dependency','qualification_bottleneck',
 'lead_time_extension','capacity_utilization','book_to_bill','order_backlog','inventory_buffer','substitution_elasticity',
 'pricing_power','margin_capture','transport_node_congestion','port_dwell_time','freight_capacity','semiconductor_node_capacity',
 'memory_cycle','advanced_packaging_capacity','power_grid_interconnection','transformer_lead_time','data_center_power_constraint',
 'critical_mineral_processing','refining_concentration','shipping_insurance_constraint','sanction_rerouting','component_shortage',
 'supplier_financial_distress','customer_concentration','network_shock_propagation','network_community_rotation','patent_chokepoint',
 'standard_setting_control','license_royalty_capture','regulatory_qualification','capex_response_lag','bottleneck_release_invalidation'
 ],'transmission_or_value_capture',['equities','commodities','macro'],['input-output tables','company supply chain','capacity','orders','shipping'])
add('ihsg_broker_controller_structure',[
 'foreign_flow','broker_accumulation_persistence','broker_cost_basis','broker_cluster_concentration','controller_inventory',
 'free_float_scarcity','crossing_detection','fake_retail_detection','done_detail_large_trade','big_volume_roll_up',
 'big_volume_roll_down','bid_offer_absorption','offer_wall_absorption','BOS_confirmation','false_breakout','auction_imbalance',
 'index_rebalance_flow','rights_issue_overhang','placement_overhang','pledged_share_risk','related_party_flow','import_dependency',
 'commodity_beta','rupiah_sensitivity','domestic_liquidity','margin_financing','short_sale_constraint','warrant_dilution',
 'free_float_adjusted_capacity','broker_rotation','retail_crowding','suspension_reopening','corporate_action_event','controller_support',
 'earnings_revision_IHSG','valuation_gap_IHSG','liquidity_adjusted_momentum','broker_flow_x_macro','full_universe_survivorship_guard'
 ],'flow_value_capture_or_execution',['IHSG'],['broker summary','done detail','order book','IDX filings','macro'])
add('event_news_sentiment',[
 'macro_surprise','central_bank_text_surprise','policy_path_surprise','geopolitical_event','earnings_news','filing_event',
 'insider_purchase','insider_sale','activist_entry','13F_change','buyback_announcement','issuance_announcement','M_and_A_probability',
 'regulatory_approval','clinical_trial_readout','patent_ruling','litigation_event','supply_disruption_news','management_change',
 'news_sentiment','news_novelty','news_volume','attention_spike','Google_trends','Wikipedia_attention','social_sentiment',
 'social_disagreement','narrative_coherence','rumor_confirmation','event_study_drift','overnight_news_gap','analyst_day_event',
 'investor_day_event','product_launch','government_contract','contract_backlog_announcement','headline_sentiment_placebo'
 ],'trigger_or_information_flow',['all_markets'],['timestamped news','filings','events','attention'])
add('statistical_complex_systems_challengers',[
 'Markov_switching','hidden_Markov_model','threshold_autoregression','smooth_transition_regression','cusp_catastrophe',
 'LPPLS','critical_slowing_down','variance_autocorrelation_early_warning','flickering','topological_data_analysis',
 'persistent_homology','recurrence_quantification','multifractal_spectrum','Hurst_regime','entropy_regime','transfer_entropy',
 'Granger_network','PCMCI_causal_graph','dynamic_factor_model','random_matrix_eigenvalue','correlation_network_fragility',
 'minimum_spanning_tree','change_point_detection','Bayesian_online_change_point','matrix_profile_anomaly','autoencoder_anomaly',
 'isolation_forest','one_class_SVM','reservoir_computing','Gaussian_process','neural_SDE','rough_volatility',
 'Hawkes_process','self_exciting_jump','agent_based_market','Ising_market','percolation_market','sandpile_SOC',
 'renormalization_scaling','wavelet_coherence','spectral_cycle','SSA_cycle','Fourier_cycle_placebo','astrology_cycle_placebo'
 ],'challenger_model_or_regime_detection',['all_markets'],['prices','macro','flows','network'],source='broad_hypothesis_sweep')
add('portfolio_construction_risk_premia',[
 'betting_against_beta','quality_minus_junk','value_everywhere','momentum_everywhere','carry_everywhere','defensive_equity',
 'minimum_variance','risk_parity','equal_risk_contribution','maximum_diversification','volatility_targeting','trend_risk_control',
 'factor_timing','factor_momentum','factor_value','factor_carry','factor_crowding','factor_dispersion','factor_crash_risk',
 'residual_factor','industry_neutral_factor','country_neutral_factor','capacity_adjusted_factor','liquidity_adjusted_factor',
 'transaction_cost_aware_factor','tax_aware_factor','drawdown_control','Kelly_fraction','CVaR_allocation','robust_optimization',
 'Black_Litterman','hierarchical_risk_parity','network_diversification','regime_conditional_allocation','equal_weight_baseline'
 ],'allocation_or_direction',['multi_asset','equities'],['factor returns','prices','costs','capacity'])

items.extend(curated)
# Deduplicate IDs and preserve all source signal definitions.
seen=set(); dedup=[]
for x in items:
    cid=x['candidate_id']
    if cid in seen:
        k=2
        while f'{cid}_{k}' in seen:k+=1
        x['candidate_id']=f'{cid}_{k}'
    seen.add(x['candidate_id']); dedup.append(x)
items=dedup

summary={
 'schema':'warroom.research_universe.v58','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'source_signal_doc_sha256':sha256(SRC),'candidate_count':len(items),
 'source_class_counts':{},'family_counts':{},'signal_class_counts':{},
 'governance':{
   'mapping_before_formula':True,'discovery_is_not_proof':True,'all_trials_logged':True,
   'placebos_retained':True,'failed_candidates_retained':True,'live_decision_weight':0.0,
   'capital_permission':'BLOCKED','literal_world_completeness_claimed':False,
   'scope_statement':'Versioned, extensible universe covering all OpenSourceAP definitions plus curated public-market thesis families; not a claim that every unpublished/proprietary idea worldwide is known.'
 }
}
for x in items:
    summary['source_class_counts'][x['source_class']]=summary['source_class_counts'].get(x['source_class'],0)+1
    summary['family_counts'][x['family']]=summary['family_counts'].get(x['family'],0)+1
    if 'source_signal_class' in x: summary['signal_class_counts'][x['source_signal_class']]=summary['signal_class_counts'].get(x['source_signal_class'],0)+1

(OUT/'V58_RESEARCH_UNIVERSE.json').write_text(json.dumps({'summary':summary,'candidates':items},indent=2,sort_keys=True),encoding='utf-8')
# Flatten key fields CSV
cols=['candidate_id','family','name','thesis','primary_role','market_scope','data_required','source_class','source_signal_class','mapping_status','discovery_status','validation_status','lockbox_status','prospective_status','live_decision_weight','capital_permission','claim_ceiling','notes']
with (OUT/'V58_RESEARCH_UNIVERSE.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for x in items:
        y={k:x.get(k,'') for k in cols}
        for k in ['market_scope','data_required']: y[k]='|'.join(y[k]) if isinstance(y[k],list) else y[k]
        w.writerow(y)
print(json.dumps(summary,indent=2))

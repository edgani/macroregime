from __future__ import annotations
import csv, hashlib, itertools, json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
R=ROOT/'research_v60'
(R/'protocols').mkdir(parents=True,exist_ok=True)
(R/'results').mkdir(parents=True,exist_ok=True)
(R/'ledgers').mkdir(parents=True,exist_ok=True)
(R/'reports').mkdir(parents=True,exist_ok=True)

MARKETS={
'us_equities':{
 'origins':['analyst_eps_revision','analyst_revenue_revision','guidance_surprise','earnings_surprise','revenue_surprise','gross_margin_inflection','customer_qualification','order_backlog_change','capacity_constraint','industry_contract_price','borrow_fee_shock','short_interest_change','insider_purchase','buyback_activation','etf_creation_flow','index_inclusion_flow','supplier_customer_shock','patent_product_event'],
 'vulnerabilities':['low_free_float','high_short_interest_to_float','high_borrow_utilization','high_days_to_cover','thin_depth','crowded_options_strikes','low_inventory_buffer','single_supplier_dependency','high_operating_leverage','high_expectation_dispersion'],
 'triggers':['earnings_release','guidance_update','customer_win','contract_price_reset','index_rebalance','borrow_recall','short_sale_constraint','breakout_with_signed_flow','macro_policy_surprise'],
 'transmissions':['signed_equity_order_flow','borrow_squeeze','dealer_hedging','etf_flow','analyst_revision_cascade','supply_chain_readthrough','retail_attention','liquidity_gap'],
 'horizons':['1d','5d','21d','63d','126d']},
'ihsg':{
 'origins':['broker_inventory_persistence','foreign_net_flow','controller_accumulation_proxy','earnings_revision','commodity_beta_inflection','import_cost_relief','export_price_shock','capacity_expansion','rights_issue_use_of_funds','corporate_action','order_backlog_change','sector_policy_change'],
 'vulnerabilities':['low_free_float','controller_concentration','thin_depth','broker_concentration','crossing_intensity','high_import_dependency','refinancing_need','small_market_cap','retail_crowding'],
 'triggers':['broker_flow_acceleration','foreign_flow_reversal','earnings_release','commodity_breakout','policy_release','corporate_action_date','failed_breakdown_with_absorption'],
 'transmissions':['broker_inventory_transfer','foreign_local_rotation','controller_float_squeeze','sector_peer_readthrough','retail_attention','liquidity_gap','margin_forced_flow'],
 'horizons':['1d','5d','20d','60d','120d']},
'commodity':{
 'origins':['inventory_surprise','production_outage','spare_capacity_change','demand_revision','export_disruption','import_surge','refinery_run_change','weather_shock','geopolitical_risk_repricing','physical_basis_change','freight_constraint','storage_constraint','producer_hedging_change','managed_money_position_change','curve_roll_yield','substitution_price'],
 'vulnerabilities':['low_inventory_days','steep_backwardation','concentrated_spare_capacity','thin_deliverable_supply','crowded_managed_money','high_open_interest_to_depth','refinery_bottleneck','transport_chokepoint','seasonal_demand_peak'],
 'triggers':['inventory_release','outage_confirmation','sanction_or_war_event','opec_policy','weather_realization','curve_break','signed_futures_flow','margin_change'],
 'transmissions':['physical_cash_market','futures_curve','producer_consumer_hedging','short_covering','long_liquidation','cross_commodity_substitution','shipping_and_insurance','equity_readthrough'],
 'horizons':['1d','5d','20d','60d','120d']},
'fx':{
 'origins':['policy_path_surprise','inflation_surprise','growth_surprise','terms_of_trade_change','reserve_change','intervention_signal','external_funding_stress','carry_change','real_exchange_rate_gap','capital_flow_change','cftc_tff_position_change','risk_reversal_change'],
 'vulnerabilities':['foreign_currency_debt','low_reserve_adequacy','crowded_carry','high_import_dependence','political_event_risk','thin_offshore_liquidity','high_open_interest_to_depth'],
 'triggers':['central_bank_decision','intervention','inflation_release','payroll_release','risk_off_shock','funding_basis_break','option_barrier_break'],
 'transmissions':['rate_differential','dollar_funding','carry_unwind','reserve_intervention','options_hedging','corporate_hedging','cross_border_portfolio_flow'],
 'horizons':['1d','5d','20d','60d','120d']},
'crypto':{
 'origins':['spot_exchange_inflow_outflow','stablecoin_supply_impulse','onchain_fee_demand','protocol_revenue_change','token_unlock','etf_flow','developer_or_usage_growth','narrative_attention','taker_flow','spot_perp_divergence','funding_change','basis_change','open_interest_change','whale_inventory_change'],
 'vulnerabilities':['high_oi_to_depth','extreme_funding','extreme_basis','liquidation_cluster_near_price','thin_order_book','high_exchange_concentration','token_unlock_overhang','high_leverage_estimate','crowded_top_trader_ratio'],
 'triggers':['spot_signed_flow','perp_signed_flow','liquidation_threshold_hit','listing_delisting','protocol_event','etf_creation_redemption','stablecoin_mint_burn','security_incident'],
 'transmissions':['short_liquidation','long_liquidation','cross_venue_arbitrage','market_maker_inventory','perp_spot_basis','social_reflexivity','onchain_bridge_flow','liquidity_gap'],
 'horizons':['15m','1h','6h','24h','72h','21d']},
}

SOURCE_MAP={
'analyst':'licensed point-in-time estimate history','earnings':'SEC/company filings point-in-time','guidance':'SEC/company filings point-in-time','revenue':'SEC/company filings point-in-time','gross_margin':'SEC/company filings point-in-time','customer':'company filings/customer disclosures/supply-chain evidence','order_backlog':'company filings','capacity':'company filings/industry capacity data','industry_contract':'specialized industry pricing','borrow':'securities-lending vendor; public reporting incomplete','short_interest':'FINRA/SRO snapshots; lending cost still needed','insider':'SEC Form 4','buyback':'filings and transaction disclosures','etf':'fund sponsor/exchange/vendor','index':'index provider announcements','supplier':'company filings and production network mapping','patent':'official patent/product disclosures',
'broker':'IDX broker summary/history acquisition','foreign':'IDX/market data history','controller':'ownership/free-float filings plus broker mapping','commodity_beta':'commodity and issuer exposure mapping','import':'trade data/company cost structure','export':'trade/physical price data','rights':'IDX issuer filings','corporate':'IDX issuer filings','sector_policy':'official regulation/policy',
'inventory':'EIA/official agencies/exchange stocks','production':'official agency/company/port data','spare':'official producer data and estimates','demand':'official agency forecast vintages','export_disruption':'customs/port/shipping','refinery':'official refinery/utilization','weather':'official meteorological vintages','geopolitical':'timestamped public events; not causal proof alone','physical_basis':'licensed physical cash market','freight':'shipping/freight data','storage':'official/vendor storage data','producer_hedging':'CFTC disaggregated COT','managed_money':'CFTC disaggregated COT','curve':'exchange futures settlements','substitution':'cross-commodity prices and input-output mapping',
'policy':'central bank official vintage','inflation':'official macro release vintage','growth':'official macro release vintage','terms':'trade and commodity indices','reserve':'central bank/IMF','intervention':'central bank and high-frequency inference','external_funding':'BIS/market basis','carry':'official rates and forwards','real_exchange':'official CPI/PPP','capital_flow':'balance-of-payments/EPFR vendor','cftc':'CFTC TFF','risk_reversal':'licensed options surface',
'spot_exchange':'exchange/on-chain tagged flows','stablecoin':'on-chain supply','onchain':'chain data','protocol':'chain/protocol disclosures','token_unlock':'official token schedules/chain data','developer':'repository and chain usage','narrative':'timestamped attention data','taker':'exchange signed taker volume','spot_perp':'exchange spot/perpetual prices','funding':'exchange funding history','basis':'exchange futures basis','open_interest':'exchange OI history; direction ambiguous alone','whale':'tagged on-chain balances',
}

def family_source(metric:str)->str:
    for prefix,src in SOURCE_MAP.items():
        if metric.startswith(prefix) or prefix in metric:return src
    return 'market-specific point-in-time source required'

primitives=[]
for market,cfg in MARKETS.items():
    for role in ['origins','vulnerabilities','triggers','transmissions']:
        for metric in cfg[role]:
            primitives.append({
                'primitive_id':f'{market}:{role[:-1]}:{metric}',
                'market':market,'causal_role':role[:-1],'metric':metric,
                'source_requirement':family_source(metric),'point_in_time_required':True,
                'directional_by_itself': metric not in {'open_interest_change','high_open_interest_to_depth','high_oi_to_depth','crowded_options_strikes'},
                'proof_status':'MAPPED_NOT_PROVEN','live_decision_weight':0.0,'capital_permission':'BLOCKED'
            })

# Register mechanistically ordered paths rather than arbitrary unrestricted formulas.
paths=[]
for market,cfg in MARKETS.items():
    for horizon in cfg['horizons']:
        # deterministic sampled full cross product; all origins get broad coverage without enormous package bloat
        allp=itertools.product(cfg['origins'],cfg['vulnerabilities'],cfg['triggers'],cfg['transmissions'])
        for i,(o,v,t,x) in enumerate(allp):
            if i % max(1, len(cfg['transmissions'])//2) != 0: continue
            paths.append({
                'path_id':hashlib.sha256(f'{market}|{o}|{v}|{t}|{x}|{horizon}'.encode()).hexdigest()[:20],
                'market':market,'origin':o,'vulnerability':v,'trigger':t,'transmission':x,'horizon':horizon,
                'claim':'origin precedes trigger; vulnerability and transmission alter move probability/magnitude',
                'status':'REGISTERED_DATA_REQUIRED','live_decision_weight':0.0,'capital_permission':'BLOCKED'
            })

# Data readiness rows.
readiness=[
('us_equities','OHLCV/corporate actions','AVAILABLE_BUNDLED_DIAGNOSTIC','daily','public/mixed','Existing fixed panel is not survivorship-safe or current.'),
('us_equities','SEC fundamentals/guidance/customer qualification','PUBLIC_ACQUIRABLE','event/daily','official','Fresh filing parser and vintage timestamps required.'),
('us_equities','analyst estimates/revisions','LICENSED_OR_SPECIALIZED','daily','vendor','Needed for expectation-gap replication and SNDK-like discovery.'),
('us_equities','short interest','PUBLIC_SPARSE','semi-monthly','FINRA/SRO','Snapshot is slow and omits borrow fee/utilization.'),
('us_equities','borrow fee/utilization/locates','LICENSED','intraday/daily','securities lending vendor','Required to distinguish negative information from squeeze scarcity.'),
('us_equities','signed options trades/dealer inventory','LICENSED','trade-by-trade','exchange/vendor','Gross OI shortcut forbidden.'),
('us_equities','full depth/signed equity flow','LICENSED','intraday','exchange/vendor','Execution/transmission horizon only.'),
('ihsg','broker summary','PUBLIC_CURRENT_HISTORY_NEEDED','daily','IDX','Historical ticker-by-broker inventory and crossing adjustments required.'),
('ihsg','foreign flow','PUBLIC_OR_VENDOR','daily','IDX/vendor','Point-in-time ticker history required.'),
('ihsg','done detail/order book','LICENSED_OR_PLATFORM','intraday','broker/platform','Needed for fake-retail/crossing and absorption tests.'),
('ihsg','ownership/free float/controller','PUBLIC_ACQUIRABLE','filing/event','IDX issuer filings','Vintage reconstruction required.'),
('commodity','CFTC disaggregated COT/TFF','PUBLIC_ACQUIRABLE','weekly','CFTC','Tuesday snapshot and publication lag; useful state, weak exact trigger.'),
('commodity','futures curve/OI/volume','PUBLIC_OR_EXCHANGE','daily/intraday','exchange','OI is non-directional without participant/signed flow.'),
('commodity','inventory/production/refinery','PUBLIC_ACQUIRABLE','weekly/monthly/event','EIA/official agencies','Vintage surprise and release timestamp required.'),
('commodity','physical basis/freight/storage','LICENSED_OR_SPECIALIZED','daily','physical market vendor','Core for scarcity and topping; currently absent.'),
('fx','CFTC TFF','PUBLIC_ACQUIRABLE','weekly','CFTC','Positioning state; lagged.'),
('fx','macro release vintages/rate path','PUBLIC_ACQUIRABLE','event/daily','official central banks/stat agencies','Surprise construction required.'),
('fx','options surface/risk reversal','LICENSED','intraday/daily','exchange/vendor','Needed for distribution and barrier/hedging tests.'),
('fx','OTC signed order flow','LICENSED_FRAGMENTED','intraday','dealer/platform','No universal consolidated tape.'),
('crypto','OI/funding/basis/top-trader ratios','PUBLIC_RECENT_LIMITED','5m+','exchange APIs','Binance endpoints generally expose only recent windows; archive must be collected prospectively.'),
('crypto','side-specific liquidations','PUBLIC_LIVE_RECENT_LIMITED','real-time','exchange streams/APIs','Realized liquidation is usually contemporaneous amplification.'),
('crypto','taker flow/order book depth','PUBLIC_LIVE','real-time','exchange APIs','Must archive continuously and normalize across venues.'),
('crypto','on-chain/stablecoin/exchange flows','PUBLIC_OR_VENDOR','block/daily','chain/vendor','Address tagging and revision policy required.'),
]
readiness_rows=[{'market':a,'dataset_family':b,'availability':c,'frequency':d,'source_class':e,'blocker_or_use':f,'live_decision_weight':0.0,'capital_permission':'BLOCKED'} for a,b,c,d,e,f in readiness]

# Write artifacts.
def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def dump(path,obj):path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')

write_csv(R/'V60_MECHANISM_UNIVERSE.csv',primitives)
dump(R/'V60_MECHANISM_UNIVERSE.json',{'schema':'warroom.v60.mechanism_universe','created_at_utc':datetime.now(timezone.utc).isoformat(),'primitive_count':len(primitives),'markets':MARKETS,'primitives':primitives,'claim_boundary':'This is a mapped candidate universe, not empirical proof and not literally every possible market thesis.'})
write_csv(R/'V60_CAUSAL_PATH_REGISTRY.csv',paths)
dump(R/'V60_CAUSAL_PATH_REGISTRY.json',{'schema':'warroom.v60.causal_path_registry','path_count':len(paths),'paths':paths,'claim_boundary':'Registered mechanistic paths are acquisition/test queue only.'})
write_csv(R/'V60_DATA_READINESS_MATRIX.csv',readiness_rows)
dump(R/'V60_DATA_READINESS_MATRIX.json',{'schema':'warroom.v60.data_readiness','rows':readiness_rows})

schema={
 'schema':'warroom.v60.derivatives_panel_schema','required_columns':['timestamp','market','symbol','close'],
 'candidate_columns':['open_interest','open_interest_notional','funding_rate','basis','taker_buy_notional','taker_sell_notional','long_liquidation_notional','short_liquidation_notional','depth_1pct_notional','participant_long','participant_short','inventory_surprise','physical_basis','earnings_revision','guidance_surprise','broker_net_flow','foreign_net_flow','stablecoin_flow','exchange_netflow'],
 'requirements':['timestamps must be event-time point-in-time','venue and contract identifiers retained','liquidation side uses position liquidated, not aggressor side','no forward-filled event releases before publication','delisted/dead instruments retained','fees/slippage handled only after predictive gate'],
 'minimum_history':'enough for discovery, validation and untouched lockbox with events in every split'
}
dump(R/'protocols'/'V60_DERIVATIVES_PANEL_SCHEMA.json',schema)
protocol={
 'schema':'warroom.v60.derivatives_driver_protocol','frozen_before_real_outcome_data':True,
 'primary_question':'Do origin, vulnerability, signed positioning and forced-flow variables improve calibrated prediction of future massive moves over simple price/volatility baselines?',
 'causal_order':['origin','vulnerability','trigger','transmission','realized liquidation','exhaustion'],
 'forbidden_shortcuts':['total OI as direction','price up plus OI up equals long accumulation','realized liquidation as proof of the original trigger','gross options OI as dealer sign','volume as institutional identity'],
 'candidate_families':['OI change/level normalized by depth','signed taker imbalance','participant long/short changes','funding and basis crowding','liquidation distance and side-specific forced flow','physical/fundamental/expectation origin','broker/foreign flow','interactions constrained by causal order'],
 'splits':'chronological discovery/validation/untouched lockbox','promotion_gate':['incremental validation improvement','incremental lockbox improvement','simultaneous lower bound above zero','calibration not worse','lead time positive and useful','baseline beaten','no-retuning replication','prospective evidence'],
 'live_decision_weight':0.0,'capital_permission':'BLOCKED'
}
dump(R/'protocols'/'V60_DERIVATIVES_DRIVER_PROTOCOL_FROZEN.json',protocol)
for p in [R/'protocols'/'V60_DERIVATIVES_DRIVER_PROTOCOL_FROZEN.json',R/'protocols'/'V60_DERIVATIVES_PANEL_SCHEMA.json']:
    p.with_suffix(p.suffix+'.sha256.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')

print(json.dumps({'status':'PASS','primitive_count':len(primitives),'registered_causal_paths':len(paths),'readiness_rows':len(readiness_rows)},indent=2))

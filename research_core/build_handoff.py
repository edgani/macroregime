from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, csv

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'FINAL_HANDOFF'; OUT.mkdir(parents=True,exist_ok=True)
BUNDLE=ROOT/'legacy_bundle'/'EROS_AGENT_COMPLETE_BUNDLE_v2'
DB=BUNDLE/'DATA_BUNDLE'

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

# 01 Engine registry: one canonical list for this self-run package.
engines = [
('SYSTEMIC_CRASH_RISK','SYSTEMIC','future drawdown probability/severity','FRAGILITY|EARLY_WARNING|TRIGGER|SEVERITY'),
('GROWTH_TRACKING','MACRO_STATE','future growth/state/acceleration','STATE|NOWCAST|LEADING'),
('RECESSION_DETECTION','MACRO_STATE','future recession state','STATE|LEADING|CONFIRMATION'),
('RECOVERY_REENTRY','MACRO_STATE','future stabilization/recovery state','RECOVERY|REENTRY'),
('INFLATION_TRACKING','INFLATION','future inflation level/persistence','STATE|NOWCAST|LEADING'),
('DISINFLATION_MONITOR','INFLATION','future disinflation state','STATE|CONFIRMATION'),
('DEFLATION_EARLY_WARNING','INFLATION','future deflation risk','EARLY_WARNING|SEVERITY'),
('MONETARY_POLICY_STANCE','POLICY','current policy restriction/easing state','STATE|POLICY_REACTION'),
('POLICY_PATH','POLICY','future policy path/surprise','LEADING|SCENARIO_DISCRIMINATOR'),
('INTEREST_RATE_LEVELS','RATES','future nominal/real yield distribution','STATE|ASSET_DRIVER'),
('YIELD_CURVE_ANALYSIS','RATES','future curve state','STATE|LEADING|RECOVERY'),
('TERM_PREMIUM_TRACKING','RATES','future term-premium state','STATE|FRAGILITY|ASSET_DRIVER'),
('CREDIT_CONDITIONS','CREDIT','future spread/default/credit-availability state','STATE|FRAGILITY|EARLY_WARNING'),
('BANKING_STRESS','CREDIT','future banking stress/lending impairment','FRAGILITY|TRIGGER|SEVERITY'),
('FUNDING_STRESS','FUNDING','future funding stress','STATE|EARLY_WARNING|TRIGGER'),
('FINANCIAL_PLUMBING','FUNDING','repo/reserve/collateral state','STATE|FRAGILITY'),
('LIQUIDITY_MEASUREMENT','LIQUIDITY','future liquidity expansion/contraction','STATE|ASSET_DRIVER'),
('GLOBAL_DOLLAR_LIQUIDITY','LIQUIDITY','future global USD availability','STATE|ASSET_DRIVER|FRAGILITY'),
('FISCAL_SUSTAINABILITY','FISCAL','future fiscal pressure/sustainability','STATE|FRAGILITY|ASSET_DRIVER'),
('SOVEREIGN_STRESS','FISCAL','future sovereign stress','FRAGILITY|TRIGGER'),
('HOUSEHOLD_STRESS','PRIVATE_SECTOR','future household stress/delinquency','STATE|FRAGILITY'),
('CORPORATE_STRESS','PRIVATE_SECTOR','future corporate stress/cashflow impairment','STATE|FRAGILITY'),
('VALUATION_FRAGILITY','VALUATION','future fragility conditional on valuation','FRAGILITY|CONTEXT_ONLY'),
('CAPITAL_FORMATION','FLOW','future investment/issuance/capex state','CAPITAL_FORMATION|FLOW'),
('POSITIONING_CROWDING','FLOW','future crowding/positioning state','POSITIONING|FRAGILITY'),
('FX_MACRO','FX','future FX payoff distribution from economic drivers','ASSET_DRIVER|SCENARIO_DISCRIMINATOR'),
('COMMODITY_MACRO','COMMODITY','future commodity payoff/physical state','ASSET_DRIVER|STATE'),
('GOLD_MACRO','COMMODITY','future gold payoff from non-price economic drivers','ASSET_DRIVER|SCENARIO_DISCRIMINATOR'),
('ENERGY_IMBALANCE','COMMODITY','future energy physical imbalance/payoff','PHYSICAL_CONSTRAINT|ASSET_DRIVER'),
('INDUSTRIAL_METALS','COMMODITY','future metals physical imbalance/payoff','PHYSICAL_CONSTRAINT|ASSET_DRIVER'),
('AGRICULTURE_SHOCK','COMMODITY','future agricultural supply shock','PHYSICAL_CONSTRAINT|EARLY_WARNING'),
('SHIPPING_LOGISTICS','PHYSICAL','future shipping/logistics stress','BOTTLENECK|EARLY_WARNING'),
('PHYSICAL_SUPPLY_DEMAND','PHYSICAL','future supply/demand imbalance','PHYSICAL_CONSTRAINT|STATE'),
('BOTTLENECK_CAPACITY','PHYSICAL','future capacity constraint','BOTTLENECK|SCENARIO_DISCRIMINATOR'),
('US_ECONOMIC_STATE','COUNTRY','US state vector','STATE'),
('CHINA_ECONOMIC_STATE','COUNTRY','China state vector','STATE'),
('INDONESIA_ECONOMIC_STATE','COUNTRY','Indonesia state vector','STATE'),
('JAPAN_ECONOMIC_STATE','COUNTRY','Japan state vector','STATE'),
('EUROZONE_ECONOMIC_STATE','COUNTRY','Eurozone state vector','STATE'),
('CRYPTO_SYSTEM_LIQUIDITY','CRYPTO','crypto liquidity/funding state','STATE|FRAGILITY'),
('BTC_MACRO_DRIVER','CRYPTO','BTC payoff from macro/non-price drivers','ASSET_DRIVER'),
('ETH_PLATFORM_ECONOMICS','CRYPTO','ETH/platform fundamental state','STATE|ASSET_DRIVER'),
('STABLECOIN_LIQUIDITY','CRYPTO','stablecoin supply/liquidity state','STATE|FLOW'),
('SCENARIO_DISCOVERY','SCENARIO','competing causal scenarios','SCENARIO_DISCRIMINATOR'),
('SCENARIO_PROBABILITY','SCENARIO','calibrated scenario probability','SCENARIO_DISCRIMINATOR'),
('SCENARIO_TIMING','SCENARIO','scenario start/materialization timing','SCENARIO_DISCRIMINATOR'),
('SCENARIO_DURATION','SCENARIO','scenario persistence/duration','SCENARIO_DISCRIMINATOR'),
('ASSET_TRANSMISSION','DECISION','conditional asset payoff distribution','ASSET_DRIVER'),
('PRICED_IN','DECISION','probability thesis not fully priced','PRICED_IN_CONTEXT'),
('TICKER_QUALIFICATION','TICKER','company mechanism qualification','TICKER_FILTER'),
('TICKER_FILTER_VALIDATION','TICKER','incremental filter value','TICKER_FILTER'),
('TICKER_RANKING','TICKER','PIT rank outcome','TICKER_FILTER'),
('EXPECTED_VALUE','DECISION','net expected value','DECISION'),
('PORTFOLIO_RISK','PORTFOLIO','portfolio scenario/tail exposure','PORTFOLIO_RISK'),
('PORTFOLIO_SIZING','PORTFOLIO','risk/capacity-aware sizing','PORTFOLIO_RISK'),
('RECOVERY_EXIT_REENTRY','PORTFOLIO','exit/reentry state','RECOVERY|REENTRY'),
('MARKET_STRUCTURE_TIMING','EXECUTION','short-horizon volatility/execution context only','MARKET_STRUCTURE_TIMING_MODIFIER|EXECUTION_CONTEXT'),
]
rows=[]
for i,(eid,cat,target,roles) in enumerate(engines,1):
    sci='SCIENTIFICALLY_TESTED_SCOPE_LIMITED' if eid=='SYSTEMIC_CRASH_RISK' else ('ACCEPTANCE_TESTED' if eid in ['SCENARIO_DISCOVERY','MARKET_STRUCTURE_TIMING'] else 'DATA_DEBT_OR_PROSPECTIVE')
    rows.append(dict(engine_id=eid,category=cat,target=target,valid_roles=roles,status=sci,canonical=True))
pd.DataFrame(rows).to_csv(OUT/'01_ENGINE_REGISTRY.csv',index=False)

# 02 Metric master: preserve broad 68-metric source map, annotate factual/test status.
metric=pd.read_csv(DB/'CORE_METRIC_SOURCE_MAP.csv')
metric['data_origin']='SOURCE_MAPPED'
metric['scientific_status']='UNTESTED'
metric['tests_completed']=''
metric['tests_pending']='PIT|ROLE_ROUTING|WF_OOS|ROBUSTNESS'
# map our factual local variables to conceptual core metrics where possible
local_test_map={'US_CPI':'inflation_yoy|inflation_accel_6m|inflation_abs', 'US_DGS10':'rate10_level|rate10_chg_6m|rate10_chg_12m',
                'US_VIX':'vix_avg|vix_max|vix_expanding_pct|vix_chg_3m'}
for mid,specs in local_test_map.items():
    m=metric.metric_id.astype(str).eq(mid)
    metric.loc[m,'data_origin']='FACTUAL_LOCAL_LEGACY_SOURCE'
    metric.loc[m,'scientific_status']='HISTORICALLY_TESTED_US_ONLY'
    metric.loc[m,'tests_completed']=specs
# append local research variables not guaranteed in source map
extras=[
('LOCAL_SHILLER_CAPE','VALUATION','Shiller CAPE','US','LEGACY_SHILLER','PE10','M','FRAGILITY|CONTEXT','Factual legacy Shiller series'),
('LOCAL_SHILLER_EARNINGS','CORPORATE','Shiller earnings','US','LEGACY_SHILLER','Earnings','M','STATE|FRAGILITY','Factual legacy Shiller series'),
('LOCAL_SHILLER_DIVIDEND','CORPORATE','Shiller dividend','US','LEGACY_SHILLER','Dividend','M','STATE|FRAGILITY','Factual legacy Shiller series'),
]
for x in extras:
    metric.loc[len(metric)]={'metric_id':x[0],'family':x[1],'metric_name':x[2],'geography':x[3],'source_id':x[4],
                            'source_series_or_dataset':x[5],'frequency':x[6],'candidate_roles':x[7],'notes':x[8],
                            'data_origin':'FACTUAL_LOCAL_LEGACY_SOURCE','scientific_status':'HISTORICALLY_TESTED_US_ONLY',
                            'tests_completed':'see experiment ledger','tests_pending':'cross-market|PIT-vintage enhancement'}
metric.to_csv(OUT/'02_METRIC_MASTER_REGISTRY.csv',index=False)

# 03/04 factual data inventory & coverage
inv=[]
for name in ['shiller.csv','vix.csv']:
    p=ROOT/'data/research'/name; d=pd.read_csv(p)
    inv.append(dict(dataset=name,source='LEGACY_BUNDLE (source identity documented; refresh official source pending)',container_path=str(p),
                    sha256=sha256(p),observations=len(d),factual=True,pit_quality='PARTIAL',scientific_usable='YES_SCOPE_LIMITED',
                    status='FACTUAL_READY_SCOPE_LIMITED'))
# Current evidence is factual snapshot but not historical panel.
p=ROOT/'data/current/evidence.json'; ev=json.loads(p.read_text())
inv.append(dict(dataset='current_evidence.json',source='Official/financial press sources enumerated per evidence item',container_path=str(p),
                sha256=sha256(p),observations=len(ev),factual=True,pit_quality='AS_OF_TIMESTAMPED',scientific_usable='SCENARIO_ACCEPTANCE_ONLY',status='FACTUAL_CURRENT_SNAPSHOT'))
pd.DataFrame(inv).to_csv(OUT/'03_FACTUAL_DATA_INVENTORY.csv',index=False)
coverage=pd.read_csv(DB/'DATA_REQUIREMENTS_MASTER.csv')
coverage['self_run_status']=np.where(coverage.dataset_id.isin(['LEGACY_SHILLER','LEGACY_VIX']),'FACTUAL_READY_SCOPE_LIMITED',
                                    np.where(coverage.dataset_id.isin(['LEGACY_SP500_PANEL','LEGACY_MACRO_PANEL']),'IN_BUNDLE_UNREADABLE_PARQUET_RUNTIME','DATA_DEBT_NOT_INGESTED'))
coverage.to_csv(OUT/'04_FACTUAL_DATA_COVERAGE.csv',index=False)

# 05 Target leakage audit
audit=[
('TL001','GOLD_SPOT_PRICE_YOY','GOLD_MACRO','past gold return','future gold return','SELF_TARGET_PRICE_MOMENTUM','NO','RESEARCH_DIAGNOSTIC_ONLY','Forbidden standalone directional price alpha'),
('TL002','CLASSIC_TECHNICAL_FEATURES','ASSET_TRANSMISSION','RSI/MACD/EMA/momentum/breakout','future same-asset direction','PRICE_DERIVED_DIRECTIONAL_ALPHA','NO','QUARANTINED','Forbidden by EROS doctrine'),
('TL003','GEX_OPTIONS_POSITIONING','MARKET_STRUCTURE_TIMING','dealer gamma estimate','short-horizon realized volatility/execution','PROVIDER_MODEL_DEPENDENCE','CONDITIONAL','RESEARCH_DIAGNOSTIC_ONLY','Allowed only as timing/fragility/execution after PIT OOS validation'),
('TL004','GEX_OPTIONS_POSITIONING','ASSET_TRANSMISSION','dealer gamma estimate','macro/asset direction','DIRECTIONAL_PROXY_RISK','NO','QUARANTINED','Never macro directional alpha by itself'),
('TL005','US_CPI_DERIVED','SYSTEMIC_CRASH_RISK','PIT-available CPI transforms','future SPX drawdown severity','NONE_IDENTIFIED','YES','TESTED_US_ONLY','Outcome is future market drawdown; feature is economic data'),
('TL006','US_DGS10_DERIVED','SYSTEMIC_CRASH_RISK','long-rate level/change','future SPX drawdown severity','NONE_IDENTIFIED','YES','TESTED_US_ONLY','Economic/rates feature vs future outcome'),
('TL007','VIX_STATE','SYSTEMIC_CRASH_RISK','VIX state/percentile','future SPX drawdown severity','MARKET_IMPLIED_SAME_MARKET_CONTEXT','YES_CONDITIONAL','TESTED_US_ONLY','Market-implied stress context allowed; not classic technical alpha'),
('TL008','SHILLER_CAPE','SYSTEMIC_CRASH_RISK','valuation state','future SPX drawdown severity','NONE_IDENTIFIED','YES','TESTED_US_ONLY','Valuation/fragility context allowed')]
pd.DataFrame(audit,columns=['audit_id','metric_id','engine_id','feature','target','leakage_type','allowed','status','reason']).to_csv(OUT/'05_TARGET_LEAKAGE_AUDIT.csv',index=False)

# 06 experiment ledger from generated test tables
u=pd.read_csv(OUT/'11_UNIVARIATE_US_LONGRUN_RESULTS.csv'); c=pd.read_csv(OUT/'12_MECHANISM_COMBO_US_LONGRUN_RESULTS.csv')
ledger=[]
for i,r in u.iterrows():
    ledger.append(dict(experiment_id=f'EXP_U_{i+1:04d}',kind='UNIVARIATE',spec=r.metric,horizon_m=r.horizon_m,target='future SPX max drawdown severity / >=20% crash',
                       data_origin='FACTUAL',dataset_hash=sha256(ROOT/'data/research/shiller.csv'),oos_method='chronological 60/40 + nonoverlap + block permutation + era splits',
                       oos_ic=r.oos_ic,nonoverlap_ic=r.nonoverlap_ic,nonoverlap_p=r.nonoverlap_p,block_perm_p=r.block_perm_p,fdr_q=r.fdr_q_nonoverlap,status=r.status))
for i,r in c.iterrows():
    ledger.append(dict(experiment_id=f'EXP_C_{i+1:04d}',kind='MECHANISM_COMBO',spec=r.composite,horizon_m=r.horizon_m,target='future SPX max drawdown severity / >=20% crash',
                       data_origin='FACTUAL',dataset_hash=sha256(ROOT/'data/research/shiller.csv'),oos_method='chronological 60/40 + nonoverlap + block permutation + era splits',
                       oos_ic=r.oos_ic,nonoverlap_ic=r.nonoverlap_ic,nonoverlap_p=r.nonoverlap_p,block_perm_p=r.block_perm_p,fdr_q=r.fdr_q_nonoverlap,status=r.status))
pd.DataFrame(ledger).to_csv(OUT/'06_COMPLETE_EXPERIMENT_LEDGER.csv',index=False)
# role engine matrix: currently only crash scientific testing is defensible.
role=pd.DataFrame([dict(spec=x['spec'],engine_id='SYSTEMIC_CRASH_RISK',role='FRAGILITY/SEVERITY',horizon_m=x['horizon_m'],status=x['status']) for x in ledger])
role.to_csv(OUT/'07_METRIC_ROLE_ENGINE_MATRIX.csv',index=False)

# 08 busted library
allres=pd.concat([u.assign(spec=u.metric,kind='UNIVARIATE'),c.assign(spec=c.composite,kind='COMBO')],ignore_index=True)
busted=allres[allres.status.eq('CONTEXT_ONLY')].copy()
if len(busted):
    busted[['spec','kind','horizon_m','nonoverlap_ic','nonoverlap_p','block_perm_p','fdr_q_nonoverlap','status']].assign(reason='Did not pass conservative US-only significance/dependence/era criteria; no production use').to_csv(OUT/'08_BUSTED_LIBRARY.csv',index=False)
else:
    pd.DataFrame(columns=['spec','kind','horizon_m','reason']).to_csv(OUT/'08_BUSTED_LIBRARY.csv',index=False)

# 09 Data debt
debt=[
('DD001','Cross-market factual macro/outcome panels','Required cross-market replication (US stocks, IHSG, commodities/futures, crypto, FX). Existing bundled panels are Parquet but runtime lacks parquet engine and network package install is unavailable.','All PROVEN statuses','BLOCKS_PROVEN_STATUS'),
('DD002','PIT/vintage macro history','ALFRED/official release-vintage panels not locally ingested in this runtime.','PIT scientific upgrades','BLOCKS_FULL_PIT_PROOF'),
('DD003','Indonesia official historical panels','BI/BPS/OJK/IDX/KSEI/BKPM full PIT datasets not locally ingested.','Indonesia engine/ticker ranking','BLOCKS_INDONESIA_PRODUCTION'),
('DD004','Company fundamental PIT panels','SEC/IDX filing-acceptance historical panels not locally ingested.','Ticker qualification/ranking/EV','BLOCKS_TICKER_PRODUCTION'),
('DD005','Historical GEX/options dealer positioning','No trustworthy provider-independent PIT GEX history available in local bundle.','Market-structure timing','BLOCKS_GEX_PRODUCTION'),
('DD006','Scenario outcome dataset','No preregistered historical event/scenario ontology outcome panel sufficient for probability/timing/duration calibration.','Scenario numeric probabilities/timing/duration','BLOCKS_NUMERIC_SCENARIO_CALIBRATION'),
('DD007','Institutional options/dealer datasets','Potentially licensed/proprietary; no verified local history.','Options positioning/dealer flow','OPTIONAL_DATA_DEBT'),
('DD008','Parquet conversion tooling','pyarrow/fastparquet/duckdb absent; installation failed due network/DNS limits.','Legacy panel audit','RUNTIME_TOOLING_LIMITATION')]
pd.DataFrame(debt,columns=['data_debt_id','missing_or_blocked','reason','affected_area','impact']).to_csv(OUT/'09_DATA_DEBT.csv',index=False)

# 10 GMIS - research-only, intentionally small and no vote counting.
surv=pd.read_csv(OUT/'13_SURVIVING_US_ONLY_CANDIDATES.csv')
# select representative mechanistic specs; never production approved here.
choice=['inflation_pressure_eq','inflation_rate_shock_eq','inflation_vix_eq','rate10_chg_6m','dividend_decel_6m']
g=[]
for spec in choice:
    d=surv[surv.spec.eq(spec)].sort_values(['status','nonoverlap_p'])
    if len(d):
        r=d.iloc[0]; g.append(dict(spec=spec,horizon_m=r.horizon_m,status=r.status,production_eligible='NO',role='US crash fragility research',reason='Representative of a distinct/partly distinct mechanism; final orthogonality requires cross-market data'))
pd.DataFrame(g).to_csv(OUT/'10_GMIS_FINAL.csv',index=False)

# 32 evidence + 33 contradiction history + 34 scenario CSV
sc=json.loads((OUT/'34_SCENARIO_REGISTRY.json').read_text())
flat=[]
for s in sc:
    flat.append(dict(scenario_id=s['scenario_id'],title=s['title'],probability=s['probability'],probability_status=s['probability_status'],timing=s['timing'],duration=s['duration'],
                     production_action=s['production_action'],roles='|'.join(s['roles']),evidence_ids='|'.join(s['evidence_ids']),analogue_status=s['analogue_status'],caveat=s['caveat']))
pd.DataFrame(flat).to_csv(OUT/'34_SCENARIO_REGISTRY.csv',index=False)
contr=[
('RC001','Weak housing/labor vs sticky inflation/hawkish dissent','A weak growth impulse conflicts with still-elevated inflation constraint','CONFLICTED_POLICY_STATE','Do not infer automatic dovish pivot'),
('RC002','Mega IPO valuation motive vs index methodology','Issuer valuation incentives exist, but index support is conditional/mechanical and no obligation to hold index up is evidenced','UNVERIFIED_MOTIVE_REJECTED','Model IPO supply + conditional passive flows'),
('RC003','Data-center securitization vs 2008 analogy','Leverage/opacity/maturity mismatch are analogous fragility channels, but no evidence yet of systemwide loss transmission comparable to 2008','ANALOGUE_CANDIDATE','Require underwriting deterioration + losses + forced transmission'),
('RC004','GEX directional narrative vs macro direction','GEX may influence short-horizon volatility/execution; it does not establish macro direction','ROLE_CONFLICT','Research-only timing modifier')]
pd.DataFrame(contr,columns=['record_id','conflict','reconciliation','status','production_rule']).to_csv(OUT/'33_REALITY_CONTRADICTION_HISTORY.csv',index=False)

# 42/43 opportunities: fail closed.
pd.DataFrame([dict(status='NO_QUALIFIED_OPPORTUNITY',as_of='2026-08-21',reason='Scenario probability/timing/duration and company/ticker PIT transmission are not calibrated/validated in this self-run scope; no forced trade.')]).to_csv(OUT/'42_CURRENT_QUALIFIED_OPPORTUNITIES.csv',index=False)
reject=[
('US hawkish survives weak housing','Macro/policy scenario','Scenario is plausible/conflicted, not a calibrated asset/ticker trade','No numeric calibrated probability; asset transmission not completed'),
('Mega AI IPO index support','Capital formation/index flow','Observable IPO/index mechanics are researchable','No evidence of an obligation to prop up index; IPO timing/valuation conditional'),
('2008 repeat from data-center ABS','Credit fragility','Real fragility channels warrant monitoring','No evidence yet of crisis trigger/systemwide loss transmission; analogy != equivalence'),
('QQQ GEX direction','Market structure','Potential volatility/execution modifier','No independent PIT/OOS GEX validation; directional use forbidden')]
pd.DataFrame(reject,columns=['candidate','category','what_passed','why_rejected_as_trade']).to_csv(OUT/'43_REJECTED_OPPORTUNITIES.csv',index=False)

# 48 prospective pending
pending=[
('PP001','Cross-market replication of US-only crash candidates','Seal current candidate list; evaluate on independently acquired US stocks/IHSG/commodities/futures/crypto/FX panels','PROVEN status prohibited until pass'),
('PP002','Scenario probability calibration','Build historical event ontology and seal scenario definitions before prospective evaluation','Current scenario probabilities remain UNKNOWN'),
('PP003','Scenario timing/duration calibration','Estimate historical lag/duration distributions by event family','Current timing/duration remain UNKNOWN'),
('PP004','GEX market-structure modifier','Acquire PIT provider-independent or raw-options-derived history; pre-register volatility/execution outcomes','GEX remains RESEARCH_DIAGNOSTIC_ONLY'),
('PP005','Mega IPO scenario','Evaluate actual filings/pricing/index inclusion/rebalance flows once events occur','No obligation motive claim allowed'),
('PP006','AI data-center credit fragility','Track issuance, covenants, spreads, defaults, lease/tenant concentration, refinancing','Analogue candidate only until losses/transmission observed')]
pd.DataFrame(pending,columns=['pending_id','model_or_hypothesis','prospective_test','production_restriction']).to_csv(OUT/'48_PROSPECTIVE_PENDING.csv',index=False)

print('generated handoff tables')

from pathlib import Path
import json, pandas as pd, subprocess, sys
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'FINAL_HANDOFF'
fail=[]; checks=[]
def ck(name,cond,detail=''):
    checks.append((name,bool(cond),detail));
    if not cond: fail.append(name)

required=[
'00_MASTER_REQUIREMENT_LEDGER.csv','01_ENGINE_REGISTRY.csv','02_METRIC_MASTER_REGISTRY.csv','03_FACTUAL_DATA_INVENTORY.csv',
'04_FACTUAL_DATA_COVERAGE.csv','05_TARGET_LEAKAGE_AUDIT.csv','06_COMPLETE_EXPERIMENT_LEDGER.csv','07_METRIC_ROLE_ENGINE_MATRIX.csv',
'08_BUSTED_LIBRARY.csv','09_DATA_DEBT.csv','10_GMIS_FINAL.csv','11_UNIVARIATE_US_LONGRUN_RESULTS.csv','12_MECHANISM_COMBO_US_LONGRUN_RESULTS.csv',
'13_SURVIVING_US_ONLY_CANDIDATES.csv','14_SCIENTIFIC_VALIDATION_SUMMARY.json','32_CURRENT_EVIDENCE.json','32_REALITY_RECONCILIATION_CURRENT.csv',
'33_REALITY_CONTRADICTION_HISTORY.csv','34_SCENARIO_REGISTRY.json','34_SCENARIO_REGISTRY.csv','35_SCENARIO_ACCEPTANCE_TEST.log',
'35_SCENARIO_PROBABILITY_VALIDATION.md','36_SCENARIO_TIMING_VALIDATION.md','37_SCENARIO_DURATION_VALIDATION.md','38_ASSET_THESIS_VALIDATION.csv',
'39_TICKER_THESIS_VALIDATION.csv','40_TICKER_FILTER_RESULTS.csv','41_TICKER_RANKING_REPLAY.csv','42_CURRENT_QUALIFIED_OPPORTUNITIES.csv',
'43_REJECTED_OPPORTUNITIES.csv','44_EXPECTED_VALUE_VALIDATION.md','45_WALK_FORWARD_OOS.md','46_ROBUSTNESS.md','47_PRODUCTION_PATCH_VERIFICATION.md',
'48_PROSPECTIVE_PENDING.csv','49_FINAL_AUDIT_PACKET.md','98_RED_TEAM_AUDIT.md','99_FINAL_ACCEPTANCE_SCORECARD.md','30_EVENT_ROUTER_ACCEPTANCE_TEST.log','31_ATTACHMENT_ACCEPTANCE_CASES.md','LEGACY_QUARANTINE.md']
for f in required: ck(f'file:{f}',(OUT/f).exists())

# Code tests
for p in [ROOT/'final_core/scientific_validation.py',ROOT/'final_core/scenario_discovery.py',ROOT/'final_core/build_handoff.py',ROOT/'final_core/production_entry.py',ROOT/'final_core/event_router.py']:
    r=subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True)
    ck(f'compile:{p.name}',r.returncode==0,r.stderr)
r=subprocess.run([sys.executable,str(ROOT/'tests/test_scenario_acceptance.py')],capture_output=True,text=True)
ck('scenario_acceptance_runtime',r.returncode==0,r.stdout+r.stderr)
r2=subprocess.run([sys.executable,str(ROOT/'tests/test_event_router.py')],capture_output=True,text=True)
ck('event_router_acceptance_runtime',r2.returncode==0,r2.stdout+r2.stderr)

# Science guards
s=json.loads((OUT/'14_SCIENTIFIC_VALIDATION_SUMMARY.json').read_text())
ck('science:no_false_positive_negative_controls',s['negative_control_false_positive_count']==0,str(s))
ck('science:no_premature_proven',s['production_proven_count']==0,str(s))
led=pd.read_csv(OUT/'06_COMPLETE_EXPERIMENT_LEDGER.csv')
ck('science:81_factual_experiments',len(led)==81 and (led.data_origin=='FACTUAL').all(),f'n={len(led)}')
ck('science:has_oos_methods',led.oos_method.str.contains('nonoverlap').all())

# Leakage guard
tl=pd.read_csv(OUT/'05_TARGET_LEAKAGE_AUDIT.csv')
for key in ['GOLD_SPOT_PRICE_YOY','CLASSIC_TECHNICAL_FEATURES']:
    d=tl[tl.metric_id.eq(key)]
    ck(f'leakage:{key}_forbidden',len(d)>0 and (d.allowed=='NO').all())
gexdir=tl[(tl.metric_id=='GEX_OPTIONS_POSITIONING') & (tl.engine_id=='ASSET_TRANSMISSION')]
ck('leakage:gex_direction_forbidden',len(gexdir)==1 and gexdir.iloc[0].allowed=='NO')

# Scenario guards
sc=json.loads((OUT/'34_SCENARIO_REGISTRY.json').read_text())
ids={x['scenario_id'] for x in sc}
need={'SCN_POLICY_CONFLICTED_REACTION_FUNCTION','SCN_MEGA_IPO_CAPITAL_SUPPLY_INDEX_REFLEXIVITY','SCN_AI_DATACENTER_LEVERAGE_FRAGILITY','SCN_DEALER_GAMMA_VOLATILITY_REGIME'}
ck('scenario:all_attachment_cases',need.issubset(ids),str(ids))
ck('scenario:no_fake_probability',all(x['probability'] is None and x['probability_status']=='UNKNOWN_UNCALIBRATED' for x in sc))
ck('scenario:no_forced_trade',all(x['production_action']=='RESEARCH_ONLY_NO_TRADE' for x in sc))
gex=[x for x in sc if x['scenario_id']=='SCN_DEALER_GAMMA_VOLATILITY_REGIME'][0]
ck('scenario:gex_roles_restricted',set(gex['roles'])=={'MARKET_STRUCTURE_TIMING_MODIFIER','FRAGILITY_MODIFIER','EXECUTION_CONTEXT'})
ai=[x for x in sc if x['scenario_id']=='SCN_AI_DATACENTER_LEVERAGE_FRAGILITY'][0]
ck('scenario:2008_analogue_not_equivalence',ai['analogue_status']=='2008_ANALOGUE_CANDIDATE_NOT_EQUIVALENCE')
ipo=[x for x in sc if x['scenario_id']=='SCN_MEGA_IPO_CAPITAL_SUPPLY_INDEX_REFLEXIVITY'][0]
ck('scenario:no_index_support_obligation_claim','obligation' in ipo['caveat'].lower() and 'unverified' in ipo['caveat'].lower())

# Fail-closed downstream
opp=pd.read_csv(OUT/'42_CURRENT_QUALIFIED_OPPORTUNITIES.csv')
ck('decision:no_qualified_opportunity',len(opp)==1 and opp.iloc[0].status=='NO_QUALIFIED_OPPORTUNITY')
dd=pd.read_csv(OUT/'09_DATA_DEBT.csv')
ck('scope:cross_market_data_debt',(dd.data_debt_id=='DD001').any())
ck('scope:gex_data_debt',(dd.data_debt_id=='DD005').any())

# Requirement ledger terminal-state guard
req=pd.read_csv(OUT/'00_MASTER_REQUIREMENT_LEDGER.csv')
forbidden={'TODO','PENDING','IN_PROGRESS','VALIDATION_PENDING','NEEDS_DATA','DESIGNED_NOT_EXECUTED','PENDING_INTERNAL'}
ck('requirements:no_unexplained_pending',not req.status.astype(str).isin(forbidden).any(),str(req[req.status.astype(str).isin(forbidden)].to_dict('records')))

# Legacy quarantine / production isolation
prod=(ROOT/'final_core/production_entry.py').read_text()
import re
ck('production:no_legacy_import',re.search(r'(^|\n)\s*(from\s+warroom|import\s+warroom)',prod,re.I) is None)
ck('production:legacy_quarantine',(OUT/'LEGACY_QUARANTINE.md').exists() and 'synthetic' in (OUT/'LEGACY_QUARANTINE.md').read_text().lower())
red=(OUT/'98_RED_TEAM_AUDIT.md').read_text()
ck('redteam:no_unresolved_internal_critical_high','NO UNRESOLVED INTERNAL CRITICAL/HIGH DEFECT' in red)

report={'pass':not fail,'checks':len(checks),'failed':fail,'details':[{'check':n,'pass':p,'detail':d[:300]} for n,p,d in checks]}
(OUT/'97_FINAL_ACCEPTANCE_RESULT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'pass':report['pass'],'checks':report['checks'],'failed':report['failed']},indent=2))
sys.exit(0 if report['pass'] else 1)

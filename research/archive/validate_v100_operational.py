"""Adversarial validation for V10.0 operational research and shadow system."""
from __future__ import annotations
import datetime as dt,hashlib,json,subprocess,tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
UTC=dt.timezone.utc
results=[]
def check(name,cond,detail=''):
 results.append({'name':name,'pass':bool(cond),'detail':detail});
 if not cond: print('FAIL',name,detail)

def fixture(now=None):
 now=now or dt.datetime.now(UTC);stamp=now.isoformat(timespec='seconds').replace('+00:00','Z')
 macro={'INDPRO':{'pct_change_12':.04},'PAYEMS':{'pct_change_12':.03},'CPIAUCSL':{'pct_change_12':.025},'PCEPI':{'pct_change_12':.024},'WALCL':{'pct_change_12':.05},'RRPONTSYD':{'pct_change_12':-.50},'WTREGEN':{'pct_change_12':-.10},'BAMLH0A0HYM2':{'change_3':-.20},'DFII10':{'change_3':-.20},'DTWEXBGS':{'pct_change_3':-.02},'DFF':{'value':4.0},'ECBDFR':{'value':3.0},'IRSTCI01JPM156N':{'value':.5},'IRSTCI01GBM156N':{'value':4.5},'IRSTCI01AUM156N':{'value':4.35},'IRSTCI01CAM156N':{'value':3.0},'WCESTUS1':{'pct_change_3':-.03}}
 peers={'NVDA':{'market_cap':1000,'shares_outstanding':10,'revenue_ttm':100,'net_income_ttm':25,'free_cash_flow_ttm':20,'stockholders_equity':40,'revenue_yoy':.30,'net_income_yoy':.40,'cash':50,'total_debt':10}}
 for i,(cap,rev,ni,fcf,equity) in enumerate([(1000,80,20,15,50),(800,100,10,10,60),(900,90,18,12,45),(700,70,14,9,35),(1200,100,30,25,55)],1):peers[f'P{i}']={'market_cap':cap,'revenue_ttm':rev,'net_income_ttm':ni,'free_cash_flow_ttm':fcf,'stockholders_equity':equity}
 assets={}
 for t,cap,fee,supply,price,g in [('BTCUSDT',1000,10,10,100,.15),('ETHUSDT',500,8,50,10,.20),('SOLUSDT',200,5,100,2,.30),('BNBUSDT',180,4,20,9,.05),('XRPUSDT',150,3,150,1,.10)]:assets[t]={'market_cap_usd':cap,'fees_30d_usd':fee,'revenue_30d_usd':fee*.7,'supply':supply,'price_usd':price,'active_addresses_30d_growth':g,'transactions_30d_growth':g*.8}
 return {'quotes':{'markets':{'us':{'NVDA':{'price':100,'validation':'VALID_CURRENT_REFERENCE','provider_timestamp':stamp}},'idx':{},'crypto':{'BTCUSDT':{'price':100,'validation':'VALID_CURRENT_REFERENCE','provider_timestamp':stamp}},'commodity':{'GOLD_REFERENCE':{'price':2500,'validation':'VALID_CURRENT_REFERENCE','provider_timestamp':stamp}},'fx':{'EURUSD_REFERENCE':{'price':1.15,'validation':'VALID_CURRENT_REFERENCE','provider_timestamp':stamp}}}},'macro':{'series':macro},'fundamentals':{'markets':{'us':peers,'idx':{}}},'crypto_network':{'assets':assets},'positioning':{'datasets':{}}}

def packet(m,t,research=None,proof=False):return {'market':m,'market_label':m.upper(),'ticker':t,'research_context':research or {},'decision':{},'quote':{},'projection':{},'risk_execution':{},'proof_data':{'market_proof_valid':proof},'causal_chain':[],'fundamental_value_capture':{}}

from action_engine_v100 import action_for_packet,enrich_packets,load_policy,macro_states,quote_state
policy=load_policy();cur=fixture();peers={'us':__import__('action_engine_v100')._equity_peer_table(cur,'us'),'idx':[]};macro=macro_states(cur)
a=action_for_packet(packet('us','NVDA',{'chains':[{'trigger_status':'ACTIVE'}]}),cur,policy,peers,macro)
check('US fixture produces LONG_BIAS',a['direction']=='LONG_BIAS',str(a['direction']))
check('US value bridge valid',a['projection']['valid'] is True)
check('US risk plan valid',a['risk_plan']['valid'] is True)
check('US shadow eligible',a['permissions']['shadow_trading']=='ELIGIBLE')
check('Systematic live proof gated',a['permissions']['systematic_live']=='PROOF_GATED')
check('Auto submit disabled',a['permissions']['auto_submit'] is False)
check('Data quality bounded',0<=a['data_quality']<=100)
check('Position risk fixed at or below 0.25%',float(a['risk_plan']['risk_fraction_of_equity'])<=.0025)
check('Position notional cap at or below 10%',float(a['risk_plan']['max_notional_fraction'])<=.10)
check('Reward/risk shadow gate respected',float(a['risk_plan']['reward_risk'])>=1.25)

stale=fixture(dt.datetime.now(UTC)-dt.timedelta(days=5));sa=action_for_packet(packet('us','NVDA',{'chains':[{'trigger_status':'ACTIVE'}]}),stale,policy,{'us':__import__('action_engine_v100')._equity_peer_table(stale,'us'),'idx':[]},macro_states(stale))
check('Stale quote rejected for shadow',sa['permissions']['shadow_trading']!='ELIGIBLE')
check('Stale quote still allows research action',sa['permissions']['research_action']=='ACTIVE')
missing=fixture();missing['fundamentals']['markets']['us']={};ma=action_for_packet(packet('us','NVDA'),missing,policy,{'us':[],'idx':[]},macro_states(missing))
check('Missing value bridge becomes WATCH',ma['direction']=='WATCH')
check('Missing current evidence does not become live',not ma['permissions']['systematic_live'].startswith('ELIGIBLE'))
ca=action_for_packet(packet('crypto','BTCUSDT',{'chains':[{'trigger_status':'ACTIVE'}]}),cur,policy,peers,macro)
check('Crypto current action exists',ca['direction'] in {'LONG_BIAS','SHORT_BIAS','WATCH'})
check('Crypto bridge has no chart input',ca['projection'].get('state') in {'CURRENT_PROTOCOL_VALUE_CAPTURE_BRIDGE','WATCH_VALUE_CAPTURE_INCOMPLETE'})
co=action_for_packet(packet('commodity','GOLD_REFERENCE'),cur,policy,peers,macro)
check('Commodity scenario produced',co['projection']['valid'] is True)
fx=action_for_packet(packet('fx','EURUSD_REFERENCE'),cur,policy,peers,macro)
check('FX scenario produced',fx['projection']['valid'] is True)

# Exact proof is the only systematic-live switch.
proofa=action_for_packet(packet('us','NVDA',{'chains':[{'trigger_status':'ACTIVE'}]},True),cur,policy,peers,macro)
check('Exact proof can make systematic-live eligible',proofa['permissions']['systematic_live'].startswith('ELIGIBLE'))
check('Experimental manual defaults disabled by environment',a['permissions']['experimental_manual']=='DISABLED_OR_NOT_ELIGIBLE')
check('Experimental risk cap at or below 0.10%',float(a['experimental_manual_risk_plan']['risk_fraction_of_equity'])<=.001)
check('Experimental exporter exists and cannot auto-submit',(HERE/'experimental_order_export_v100.py').is_file() and "broker_submission':'DISABLED" in (HERE/'experimental_order_export_v100.py').read_text())
check('Experimental mode is environment-gated','WARROOM_EXPERIMENTAL_LIVE' in (HERE/'experimental_order_export_v100.py').read_text() and 'I_ACCEPT_EXPERIMENTAL_UNPROVEN_ALPHA_RISK' in (HERE/'experimental_order_export_v100.py').read_text())

# Packet integration.
base={m:{} for m in ('us','idx','crypto','commodity','fx')};base['us']['NVDA']=packet('us','NVDA',{'chains':[{'trigger_status':'ACTIVE'}]})
out,state=enrich_packets(base,cur,policy)
p=out['us']['NVDA']
check('Unified V100 packet schema',p['schema']=='warroom.v100.unified_decision_packet.v1')
check('Projection remains ticker-bound',p['current_action']['ticker']=='NVDA' and p['projection']==p['current_action']['projection'])
check('Risk remains ticker-bound',p['risk_execution']['entry']==p['current_action']['risk_plan']['entry'])
check('Alpha Center separates shadow candidates',len(state['alpha_center']['shadow_candidates'])==1)

# Policy and static architecture.
pol=json.loads((HERE/'V100_ACTION_POLICY.json').read_text())
check('Technical features forbidden',pol['policy']['technical_features']=='FORBIDDEN')
check('Synthetic evidence forbidden',pol['policy']['synthetic_evidence']=='FORBIDDEN')
check('Manual override of systematic proof forbidden',pol['policy']['manual_override_of_systematic_proof']=='FORBIDDEN')
html=(HERE/'dashboard.html').read_text(encoding='utf-8')
check('Eight primary tabs',html.count("['mission','Mission Control']")==1 and all(x in html for x in ["['macro','Macro & Risk']","['alpha','Alpha Center']","['us','US Stocks']","['idx','IHSG']","['crypto','Crypto']","['commodity','Commodities']","['fx','FX']"]))
check('UI does not globally label everything BLOCKED','CAPITAL BLOCKED' not in html and '>BLOCKED<' not in html)
check('UI shows three permission layers',all(x in html for x in ['RESEARCH','SHADOW','SYSTEMATIC LIVE']))
check('Projection is inside ticker packet','TICKER-BOUND PROJECTION' in html and "['projection','Price Projection']" not in html)
check('Flow/causal/execution are not separate tabs',all(x not in html for x in ["['flow'","['causal'","['execution'","['validation'"]))
check('App uses V100 worker','warroom_data_worker_v100' in (HERE/'app.py').read_text())
check('App uses integrated data layer','data_layer_v100' in (HERE/'app.py').read_text())
check('Auto submit absent from dashboard','AUTO-SUBMIT OFF' in html)

# JavaScript and Python compile.
js='\n'.join(__import__('re').findall(r'<script>(.*?)</script>',html,__import__('re').S)[1:]);temp=HERE/'runtime'/'v100_validation_dashboard.js';temp.parent.mkdir(parents=True,exist_ok=True);temp.write_text(js)
try:
 r=subprocess.run(['node','--check',str(temp)],capture_output=True,text=True,timeout=30);check('Dashboard JavaScript parses',r.returncode==0,r.stderr)
except Exception as exc:check('Dashboard JavaScript parses',False,str(exc))
pyfiles=[p for p in HERE.rglob('*.py') if '.venv' not in p.parts]
fail=[]
for path in pyfiles:
 try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
 except Exception as exc:fail.append(f'{path.name}: {exc}')
check('All Python sources compile',not fail,' | '.join(fail[:10]))

# Shadow ledger prospective/hard chronology using a temporary ledger.
from shadow_execution_ledger_v95 import append_forecast,append_order_intent,append_shadow_fill,verify
with tempfile.TemporaryDirectory() as td:
 lp=Path(td)/'ledger.jsonl';now=dt.datetime.now(UTC);h='a'*64
 f={'forecast_id':'F95_V100_VALIDATION01','trial_id':'V100_FIXED','market':'us','security_id':'NVDA','generated_at':now.isoformat(),'decision_at':(now+dt.timedelta(seconds=1)).isoformat(),'outcome_start':(now+dt.timedelta(seconds=1)).isoformat(),'outcome_end':(now+dt.timedelta(days=30)).isoformat(),'horizon':'30D','direction':'LONG','probability':.6,'expected_return':.1,'expected_shortfall':-.08,'invalidation':'fundamental thesis fails','regime':'MIXED','model_hash':h,'data_snapshot_hash':h,'code_snapshot_hash':h,'global_trial_ledger_hash':h,'projection_file_hash':h}
 append_forecast(lp,f,now=now);od={'forecast_id':f['forecast_id'],'shadow_order_id':'S100_VALIDATION01','created_at':(now+dt.timedelta(seconds=1)).isoformat(),'instrument_id':'NVDA','side':'BUY','quantity':1,'order_type':'REFERENCE_MARKET','reference_price':100,'max_slippage_bps':25};append_order_intent(lp,od,now=now+dt.timedelta(seconds=1));fill={'forecast_id':f['forecast_id'],'shadow_order_id':od['shadow_order_id'],'filled_at':(now+dt.timedelta(seconds=2)).isoformat(),'quantity':1,'price':100,'commission':0,'fees':0,'spread_cost':0,'slippage_cost':0,'source_snapshot_hash':h};append_shadow_fill(lp,fill,now=now+dt.timedelta(seconds=2));v=verify(lp)
 check('Prospective shadow ledger verifies',v['valid'] and v['forecasts']==1 and v['shadow_fills']==1,str(v))
 try:
  f2=dict(f);f2['forecast_id']='F95_V100_BACKFILL01';f2['generated_at']=(now-dt.timedelta(days=1)).isoformat();append_forecast(lp,f2,now=now);blocked=False
 except Exception:blocked=True
 check('Backfilled forecast rejected',blocked)

# Offline desk must remain useful rather than all-blocked.
import data_layer_v100 as DL
from run import build_desk
desk=build_desk(DL.load_all(allow_live=False,allow_synthetic=False))
mc=desk.get('mission_control') or {}
check('Offline bundled research remains available',mc.get('research_data_status')=='AVAILABLE')
check('Offline research permission active',mc.get('research_permission')=='ACTIVE')
check('Offline systematic live named PROOF_GATED not global block',mc.get('systematic_live_permission')=='PROOF_GATED')
check('Five markets carry packets',all(len((desk.get('ticker_packets') or {}).get(m) or {})>0 for m in ('us','idx','crypto','commodity','fx')))
check('No synthetic data enabled',str((desk.get('meta') or {}).get('source'))!='SYNTHETIC')

passed=sum(r['pass'] for r in results);report={'schema':'warroom.v100.operational_validation.v1','generated_at':dt.datetime.now(UTC).isoformat(),'passed':passed,'total':len(results),'all_pass':passed==len(results),'results':results}
(HERE/'V100_FINAL_VALIDATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':passed,'total':len(results),'all_pass':report['all_pass']},indent=2))
raise SystemExit(0 if report['all_pass'] else 1)

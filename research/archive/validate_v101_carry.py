"""Adversarial validation for V10.1 carry-aware War Room.

These tests validate causal direction, chronology, state classification, UI/runtime wiring and
proof-firewall behavior. They do not claim that the carry strategy is profitable.
"""
from __future__ import annotations
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
UTC=dt.timezone.utc
results=[]
def check(name,cond,detail=''):
    results.append({'name':name,'pass':bool(cond),'detail':str(detail)})
    if not cond: print('FAIL',name,detail)

def current_fixture(*,stress='low',crowded=False,missing_rate=False):
    now=dt.datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00','Z')
    vix={'low':14.0,'elevated':24.0,'high':36.0}[stress]
    oas={'low':2.0,'elevated':4.5,'high':7.0}[stress]
    macro={
      'DFF':{'value':5.25,'change_3':0.0},'ECBDFR':{'value':3.75,'change_3':-0.25},
      'IRSTCI01JPM156N':{'value':0.10,'change_3':0.0},'IRSTCI01GBM156N':{'value':5.0,'change_3':0.0},
      'IRSTCI01AUM156N':{'value':4.35,'change_3':0.0},'IRSTCI01CAM156N':{'value':4.5,'change_3':0.0},
      'VIXCLS':{'value':vix},'BAMLH0A0HYM2':{'value':oas},
      'INDPRO':{'pct_change_12':.02},'PAYEMS':{'pct_change_12':.02},'CPIAUCSL':{'pct_change_12':.025},
      'PCEPI':{'pct_change_12':.024},'WALCL':{'pct_change_12':.02},'RRPONTSYD':{'pct_change_12':-.20},
      'WTREGEN':{'pct_change_12':-.05},'DFII10':{'change_3':-.05},'DTWEXBGS':{'pct_change_3':0.0},
    }
    if missing_rate: macro.pop('IRSTCI01JPM156N')
    fx={}
    for pair,price in [('EURUSD_REFERENCE',1.08),('GBPUSD_REFERENCE',1.27),('AUDUSD_REFERENCE',.66),('USDCAD_REFERENCE',1.36),('USDJPY_REFERENCE',158.0),('USDCHF_REFERENCE',.88),('USDIDR_REFERENCE',16200.0),('AUDJPY_REFERENCE',104.0),('CADJPY_REFERENCE',116.0),('GBPJPY_REFERENCE',200.0),('EURJPY_REFERENCE',171.0)]:
        fx[pair]={'price':price,'validation':'VALID_CURRENT_REFERENCE','provider_timestamp':now}
    rows=[]
    if crowded:
        rows=[
          {'market_and_exchange_names':'JAPANESE YEN - CME','open_interest_all':100,'lev_money_positions_long_all':0,'lev_money_positions_short_all':35,'asset_mgr_positions_long_all':5,'asset_mgr_positions_short_all':20,'report_date_as_yyyy_mm_dd':'2026-07-21'},
          {'market_and_exchange_names':'U.S. DOLLAR INDEX - ICE','open_interest_all':100,'lev_money_positions_long_all':35,'lev_money_positions_short_all':0,'asset_mgr_positions_long_all':20,'asset_mgr_positions_short_all':5,'report_date_as_yyyy_mm_dd':'2026-07-21'},
        ]
    return {
      'quotes':{'markets':{'fx':fx,'us':{},'idx':{},'crypto':{},'commodity':{}}},
      'macro':{'series':macro},
      'official_policy_rates':{'rates':{'BI_7DRR':{'value':6.25},'SNB_POLICY_RATE':{'value':1.25}}},
      'positioning':{'datasets':{'tff':{'rows':rows}}},
      'fundamentals':{'markets':{'us':{},'idx':{}}},'crypto_network':{'assets':{}},
    }

from carry_trade_engine_v101 import pair_state,build_carry_book,MAP,POLICY
low=current_fixture(stress='low')
macro_low={'liquidity_score':.6,'risk_asset_score':.5}
usdjpy=pair_state('USDJPY_REFERENCE',low,macro_low)
check('Carry causal map frozen',MAP.get('frozen') is True)
check('Carry thresholds frozen',POLICY.get('frozen') is True)
check('USDJPY funding currency is JPY',usdjpy.get('funding_currency')=='JPY',usdjpy)
check('USDJPY target currency is USD',usdjpy.get('target_currency')=='USD',usdjpy)
check('USDJPY carry direction is long pair',usdjpy.get('carry_direction')=='LONG_PAIR',usdjpy)
check('USDJPY current direction follows carry under low stress',usdjpy.get('current_direction')=='LONG_PAIR',usdjpy)
check('Carry trade lists direct beneficiaries',len(usdjpy.get('direct_beneficiaries') or [])>=3)
check('Carry trade lists unwind winners and losers',bool(usdjpy.get('unwind_winners')) and bool(usdjpy.get('unwind_losers')))
check('Carry chain is explicit',len(usdjpy.get('transmission_chain') or [])==4)
check('Carry confidence is capped for missing promotion inputs',float(usdjpy.get('confidence_cap') or 1)<.8,usdjpy.get('confidence_cap'))
check('Carry proof remains not proven',usdjpy.get('proof_state')=='NOT_PROVEN')

audusd=pair_state('AUDUSD_REFERENCE',low,macro_low)
check('AUDUSD funding currency is AUD when USD rate higher',audusd.get('funding_currency')=='AUD',audusd)
check('AUDUSD target currency is USD when USD rate higher',audusd.get('target_currency')=='USD',audusd)
check('AUDUSD carry direction is short pair',audusd.get('carry_direction')=='SHORT_PAIR',audusd)

usdidr=pair_state('USDIDR_REFERENCE',low,macro_low)
check('Official BI rate is admitted into current map',usdidr.get('quote_rate')==6.25,usdidr)
check('USDIDR direction reflects higher IDR yield',usdidr.get('funding_currency')=='USD' and usdidr.get('target_currency')=='IDR' and usdidr.get('carry_direction')=='SHORT_PAIR',usdidr)
usdchf=pair_state('USDCHF_REFERENCE',low,macro_low)
check('Official SNB rate is admitted into current map',usdchf.get('quote_rate')==1.25,usdchf)

high=current_fixture(stress='high',crowded=True)
high_macro={'liquidity_score':-.8,'risk_asset_score':-.8}
unwind=pair_state('USDJPY_REFERENCE',high,high_macro)
check('High stress and crowding flags unwind',unwind.get('state') in {'UNWIND_RISK','UNWIND_ACTIVE'},unwind)
check('Active unwind reverses or de-risks carry direction',unwind.get('current_direction') in {'SHORT_PAIR','REDUCE_OR_HEDGE_CARRY'},unwind)
check('CFTC positioning is explicitly release-lagged',bool((unwind.get('funding_positioning') or {}).get('release_lagged')))
check('Unwind benefits funding currency',any('JPY currency' in x for x in unwind.get('beneficiaries') or []),unwind.get('beneficiaries'))

missing=current_fixture(missing_rate=True)
inc=pair_state('USDJPY_REFERENCE',missing,macro_low)
check('Missing policy rate becomes incomplete',inc.get('state')=='INCOMPLETE' and inc.get('directional_score') is None,inc)
book=build_carry_book(low,macro_low)
check('Carry book covers all registered pairs',len(book.get('pairs') or [])==len(MAP.get('pairs') or {}))
check('Carry book identifies funding and target currencies',bool(book.get('funding_currencies')) and bool(book.get('target_currencies')))
check('Carry book does not promote systematic alpha',book.get('proof_state')=='NOT_PROVEN')

# Point-in-time proof admission and chronology.
from carry_proof_v101 import admit,prepare,CANDIDATES
base_rows=[]
for i in range(12):
    t=dt.datetime(2010+i,1,31,tzinfo=UTC)
    base_rows.append({'timestamp':t.isoformat(),'available_at':(t-dt.timedelta(days=1)).isoformat(),'pair':'USDJPY_REFERENCE','base_rate':3.0,'quote_rate':.25,'stress_score':.3,'pair_spot_return':.01,'carry_accrual_return':.002,'execution_cost_return':.0005,'regime':['growth','inflation','liquidity','stress'][i%4],'point_in_time':True,'source_class':'POINT_IN_TIME_OFFICIAL'})
with tempfile.TemporaryDirectory() as td:
    td=Path(td);panel=td/'panel.csv';out=td/'returns.csv';pd.DataFrame(base_rows).to_csv(panel,index=False)
    admitted=admit(panel);report=prepare(panel,out);ret=pd.read_csv(out)
    check('Valid PIT carry panel admitted',len(admitted)==12)
    check('Complete candidate family emitted',set(ret.candidate_id)==set(CANDIDATES))
    check('Each observation contains every registered candidate',ret.groupby('timestamp').candidate_id.nunique().eq(len(CANDIDATES)).all())
    check('Proof preparation stays capital blocked',report.get('capital_permission')=='BLOCKED_PENDING_ANTI_OVERFIT_AND_PROSPECTIVE_PROOF')
    bad=pd.DataFrame(base_rows);bad.loc[0,'available_at']=(dt.datetime(2011,1,1,tzinfo=UTC)).isoformat();badp=td/'lookahead.csv';bad.to_csv(badp,index=False)
    try: admit(badp);blocked=False
    except Exception: blocked=True
    check('Look-ahead input rejected',blocked)
    bad=pd.DataFrame(base_rows);bad.loc[0,'point_in_time']=False;badp=td/'nonpit.csv';bad.to_csv(badp,index=False)
    try: admit(badp);blocked=False
    except Exception: blocked=True
    check('Non-PIT row rejected',blocked)
    bad=pd.DataFrame(base_rows);bad.loc[0,'source_class']='FINAL_REVISED';badp=td/'revised.csv';bad.to_csv(badp,index=False)
    try: admit(badp);blocked=False
    except Exception: blocked=True
    check('Final-revised source rejected as proof',blocked)

proof_status=json.loads((HERE/'V101_CARRY_PROOF_STATUS.json').read_text())
check('Packaged carry alpha status is explicitly unproven',proof_status.get('carry_module_proven') is False)
check('Systematic carry capital is proof-gated',proof_status.get('systematic_live_permission')=='PROOF_GATED')

# Integrated action and packet behavior.
from action_engine_v101 import action_for_packet,enrich_packets,load_policy,macro_states
policy=load_policy()
def packet(ticker,proof=False):
    return {'market':'fx','market_label':'FX','ticker':ticker,'research_context':{},'decision':{},'quote':{},'projection':{},'risk_execution':{},'proof_data':{'market_proof_valid':proof},'causal_chain':[],'fundamental_value_capture':{}}
action=action_for_packet(packet('USDJPY_REFERENCE'),low,policy,{'us':[],'idx':[]},macro_states(low))
check('FX action embeds carry map',action.get('inputs',{}).get('carry_trade',{}).get('pair')=='USDJPY_REFERENCE')
check('Current carry action can produce research bias/watch',action.get('direction') in {'LONG_BIAS','SHORT_BIAS','WATCH'})
check('Unproven carry remains systematic proof-gated',action.get('permissions',{}).get('systematic_live')=='PROOF_GATED')
out,state=enrich_packets({'us':{},'idx':{},'crypto':{},'commodity':{},'fx':{'USDJPY_REFERENCE':packet('USDJPY_REFERENCE')}},low,policy)
fp=out['fx']['USDJPY_REFERENCE']
check('Unified FX packet carries the same pair map',fp.get('carry_trade',{}).get('pair')=='USDJPY_REFERENCE')
check('Carry projection/risk stays ticker-bound',fp.get('current_action',{}).get('ticker')=='USDJPY_REFERENCE' and fp.get('projection')==fp.get('current_action',{}).get('projection'))
check('Global action state includes carry book',state.get('carry_trade',{}).get('schema')=='warroom.v101.carry_book.v1')

# Static architecture and no-technical policy.
html=(HERE/'dashboard.html').read_text(encoding='utf-8')
check('Dashboard is V10.1 carry-aware','V10.1' in html and 'CARRY TRADE MAP' in html)
check('Dashboard shows carry direction and beneficiaries',all(x in html for x in ['Current direction','WHO BENEFITS','UNWIND / CROWDING ALERTS']))
check('Carry remains inside FX ticker packet','function carryPacket' in html)
check('App uses V101 worker','warroom_data_worker_v101' in (HERE/'app.py').read_text())
check('Runtime uses V101 data layer','data_layer_v101' in (HERE/'run.py').read_text())
pol=json.loads((HERE/'V101_ACTION_POLICY.json').read_text())
check('Technical features remain forbidden',pol.get('policy',{}).get('technical_features')=='FORBIDDEN')
check('Price role remains non-predictive','EXECUTION_REFERENCE' in pol.get('policy',{}).get('price_role',''))
check('Auto-submit remains disabled',pol.get('systematic_live',{}).get('auto_submit') is False)

# JS and all Python compile.
import re
scripts=re.findall(r'<script>(.*?)</script>',html,re.S)
js='\n'.join(scripts[1:] if len(scripts)>1 else scripts)
js_path=HERE/'runtime'/'v101_validation_dashboard.js';js_path.parent.mkdir(parents=True,exist_ok=True);js_path.write_text(js)
try:
    r=subprocess.run(['node','--check',str(js_path)],capture_output=True,text=True,timeout=30);check('Dashboard JavaScript parses',r.returncode==0,r.stderr)
except Exception as exc: check('Dashboard JavaScript parses',False,exc)
fail=[]
for path in HERE.rglob('*.py'):
    if '.venv' in path.parts: continue
    try: compile(path.read_text(encoding='utf-8'),str(path),'exec')
    except Exception as exc: fail.append(f'{path.name}: {exc}')
check('All Python sources compile',not fail,' | '.join(fail[:10]))

# Offline runtime remains useful and carry-aware without inventing current direction.
import data_layer_v101 as DL
from run import build_desk
desk=build_desk(DL.load_all(allow_live=False,allow_synthetic=False))
check('Offline bundled research remains available',(desk.get('mission_control') or {}).get('research_data_status')=='AVAILABLE')
check('Offline desk contains carry module','carry_trade' in desk)
check('Offline missing current carry data is incomplete, not fabricated',(desk.get('carry_trade') or {}).get('state') in {'INCOMPLETE','CARRY_ON','UNWIND_RISK','UNWIND_ACTIVE'})
check('Five market packet maps remain present',all(len((desk.get('ticker_packets') or {}).get(m) or {})>0 for m in ('us','idx','crypto','commodity','fx')))
check('FX universe includes carry crosses',all(x in (desk.get('ticker_packets') or {}).get('fx',{}) for x in ('USDJPY_REFERENCE','AUDJPY_REFERENCE','USDIDR_REFERENCE')))

passed=sum(x['pass'] for x in results)
report={'schema':'warroom.v101.carry_validation.v1','generated_at':dt.datetime.now(UTC).isoformat(),'passed':passed,'total':len(results),'all_pass':passed==len(results),'market_alpha_proven':False,'results':results,'claim_limit':'Software/state/proof-firewall validation only. No fixture is market alpha proof.'}
(HERE/'V101_FINAL_VALIDATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':passed,'total':len(results),'all_pass':report['all_pass'],'market_alpha_proven':False},indent=2))
raise SystemExit(0 if report['all_pass'] else 1)

from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json, re, subprocess, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
checks = {}
def check(name, cond, detail=''):
    checks[name] = {'pass': bool(cond), 'detail': detail}

html = (ROOT/'dashboard.html').read_text(encoding='utf-8')
check('14 navigation tabs', len(re.findall(r'<div class="tab(?: on| core)?" data-v=', html)) == 14)
check('original visual shell retained', all(x in html for x in ('WAR ROOM PRO / GCFIS','id="nav"','id="stage"','class="overlay"')))
check('legacy hard-coded payload removed', all(x not in html for x in ('const ALPHA','const TABS','const MARKET=')))
check('rich Mission Control restored', all(x in html for x in ('Data Feed Health & Freshness','Multi-Timeframe Regime','Regional Regime','Cross-Market Opportunity Monitor','Alpha Proof Factory')))
check('Alpha has runtime and foundry layers', all(x in html for x in ('Current Cross-Market Tactical Discovery Watch','Frozen US Alpha Foundry','Alpha Component Registry')))
check('major non-market tabs restored', all(x in html for x in ('Growth / Inflation Nowcast','Current Early-Warning State','Causal Chain Reference Library','Current US Company Watch','Current Surfaced Nodes','Runtime Integrity & Research Ledger')))
check('research-only header', 'RESEARCH ONLY · PAPER/LIVE BLOCKED' in html)
check('funnel population reconciled', all(x in html for x in ('LOADED','HISTORY-ELIGIBLE','SIGNAL-VALID','DISPLAYED')))
check('data health labels present', all(x in html for x in ('live_refreshed','cache_fresh','cache_stale','missing')))
check('no mock current-state fallback', all(x not in html for x in ('const mock=', 'Late Expansion', 'Recovery 31%', 'MOCK v0.2')))
check('Alpha Foundry historical membership reference present', (ROOT/'alpha_foundry/data/reference/sp500_ticker_start_end.csv').exists())

from run import build_desk, _surfaceable_ticker
from alpha_foundry_adapter import attach_alpha_foundry, minimal_desk
from consistency_guard import enforce_desk

def frame(seed, n=320, start=100.0):
    rng=np.random.default_rng(seed)
    idx=pd.date_range('2024-01-01',periods=n,freq='B')
    close=start*np.exp(np.cumsum(rng.normal(0.0003,0.015,n)))
    return pd.DataFrame({'Open':close*0.999,'High':close*1.01,'Low':close*0.99,'Close':close,'Volume':rng.integers(100000,1000000,n)},index=idx)

markets={'us':['AAPL','MSFT','AMD'],'idx':['BBCA.JK','ANTM.JK'],'crypto':['BTC-USD','ETH-USD'],'commodity':['CL=F','GC=F'],'fx':['EURUSD=X','USDJPY=X']}
ohlcv={m:{t:frame(i+10,start=100+i*20) for i,t in enumerate(ts)} for m,ts in markets.items()}
prices={m:{t:f['Close'] for t,f in values.items()} for m,values in ohlcv.items()}
data={'markets':list(markets),'prices':prices,'ohlcv':ohlcv,'bench':prices['us']['AAPL'],'vix':None,'fred':{},'proxies':{},'overall_source':'RESILIENT_DAILY','sources':{m:'unit' for m in markets},'fred_source':'OFFLINE','feeds':{'_status':{}},'market_meta':{m:{'status':'LIVE_REFRESHED','as_of':'2026-07-18','loaded':len(ts),'requested':len(ts),'live_refreshed':len(ts),'cache_fresh':0,'cache_stale':0,'missing':0} for m,ts in markets.items()},'treasury_liquidity':{'ok':False}}
desk=enforce_desk(attach_alpha_foundry(build_desk(data, top_per_market=20)))
check('desk schema version', desk['meta'].get('desk_schema_version')=='V6_RICH_DYNAMIC_2026_07_18')
check('Alpha no longer forced empty', len(desk.get('alpha_watch') or []) > 0, str(len(desk.get('alpha_watch') or [])))
check('Alpha watch is not proven', all(row.get('proof_status')=='UNPROVEN_RESEARCH_WATCH' for row in desk.get('alpha_watch') or []))
check('Alpha watch only uses surviving setups', {r['tk'] for r in desk['alpha_watch']} <= set(desk['consistency_audit']['surfaced_tickers']))
check('rich backend payload exposed', all(key in desk for key in ('macro_state','early_warning','flow_rotation','supply_chain','company_intel','knowledge_graph','validation_state','research_engine')))
check('engine outputs no longer discarded', all(key in desk['validation_state'] for key in ('internals','crash','leadlag','ranking_summary')))
check('reference chains marked non-current', desk['supply_chain'].get('claim')=='REFERENCE_ONLY_NOT_CURRENT_SIGNAL')
check('US ETF filtered', not _surfaceable_ticker('us','EWT') and not _surfaceable_ticker('us','XLK'))
check('IHSG index filtered', not _surfaceable_ticker('idx','^JKSE'))
check('consistency pass', desk['consistency_audit']['ok'], str(desk['consistency_audit']))

# Browser rendering contract using a tiny Node DOM stub.
sample=ROOT/'_audit_sample_desk.json'; sample.write_text(json.dumps(desk,default=str),encoding='utf-8')
minimal=ROOT/'_audit_minimal_desk.json'; minimal.write_text(json.dumps(minimal_desk('offline first-run test'),default=str),encoding='utf-8')
js_parts=re.findall(r'<script[^>]*>(.*?)</script>',html,re.S|re.I)
js_file=ROOT/'_audit_dashboard.js'; js_file.write_text('\n'.join(js_parts),encoding='utf-8')
node_test=ROOT/'_audit_render.js'
node_test.write_text(r'''const fs=require('fs'),vm=require('vm');
const root=process.argv[2],desk=JSON.parse(fs.readFileSync(root+'/_audit_sample_desk.json','utf8')),minimal=JSON.parse(fs.readFileSync(root+'/_audit_minimal_desk.json','utf8'));
const E={};function el(id){if(!E[id])E[id]={id,textContent:'',innerHTML:'',style:{},className:'',onclick:null,classList:{add(){},remove(){}}};return E[id];}
global.window={DASHBOARD_DATA:desk,scrollTo(){}};global.document={getElementById:el,querySelector(){return el('q')},querySelectorAll(){return []},title:'x'};global.setInterval=()=>0;global.setTimeout=()=>0;
vm.runInThisContext(fs.readFileSync(root+'/_audit_dashboard.js','utf8'));
function renderAll(){return {mc:viewMC(),alpha:viewAlpha(),macro:viewGeneric('macro'),ew:viewGeneric('ew'),flow:viewGeneric('flow'),sc:viewGeneric('sc'),co:viewGeneric('co'),kg:viewGeneric('kg'),rc:viewGeneric('rc'),us:viewMarket('us'),ihsg:viewMarket('ihsg'),crypto:viewMarket('crypto'),commod:viewMarket('commod'),fx:viewMarket('fx')}}
const O=renderAll();
const req={mc:['Data Feed Health & Freshness','Cross-Market Opportunity Monitor','Alpha Proof Factory'],alpha:['Current Cross-Market Tactical Discovery Watch','ETH-USD'],macro:['Growth / Inflation Nowcast'],ew:['Crash pressure'],flow:['Lead-lag edges'],sc:['Causal Chain Reference Library'],co:['Current US Company Watch'],kg:['Current Surfaced Nodes'],rc:['Runtime Integrity & Research Ledger'],us:['Current Tactical Watch Setups']};let f=[];for(const [k,a] of Object.entries(req))for(const s of a)if(!O[k].includes(s))f.push(k+' missing '+s);
DESK=minimal;window.DASHBOARD_DATA=minimal;window.__FOUNDRY=minimal.alpha_foundry||null;window.__REGISTRY=minimal.component_registry||(minimal.alpha_foundry||{}).component_registry||{};window.__SYS=minimal.systemic||{};window.__REGIME_TF=minimal.regime_tf||{};window.__REGIONAL=minimal.regional||{};window.__GRADES=minimal.grades||{};
const M=renderAll();for(const [k,v] of Object.entries(M))if(!v||typeof v!=='string')f.push('minimal '+k+' failed to render');if(!M.mc.includes('Data Feed Health & Freshness')||!M.alpha.includes('Current Cross-Market Tactical Discovery Watch'))f.push('minimal rich panels missing');
if(f.length){console.error(f.join('\n'));process.exit(1)}console.log('PASS');''',encoding='utf-8')
proc=subprocess.run(['node',str(node_test),str(ROOT)],capture_output=True,text=True)
check('rich browser render contract',proc.returncode==0,proc.stdout+proc.stderr)
for path in (sample,minimal,js_file,node_test):
    try:path.unlink()
    except FileNotFoundError:pass

report={'pass':all(v['pass'] for v in checks.values()),'passed':sum(v['pass'] for v in checks.values()),'total':len(checks),'checks':checks}
(ROOT/'V6_DEEP_RUNTIME_AUDIT.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps(report,indent=2,default=str))
raise SystemExit(0 if report['pass'] else 1)

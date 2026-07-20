from __future__ import annotations
import json, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
checks=[]
def check(name, cond, detail=''):
    checks.append({'name':name,'passed':bool(cond),'detail':detail})
    if not cond:
        raise AssertionError(f'{name}: {detail}')

try:
    dashboard=(ROOT/'dashboard.html').read_text()
    static=(ROOT/'static/dashboard_live.html').read_text()
    dl=(ROOT/'data_layer.py').read_text()
    loader=(ROOT/'data/loader.py').read_text()
    run=(ROOT/'run.py').read_text()

    check('dashboard version v2.8', 'v2.8 STAGED LIVE' in dashboard)
    check('static dashboard synchronized', dashboard==static)
    check('display FX symbols canonical', '"USDJPY=X"' in dl and '"USDIDR=X"' in dl and '"JPY=X"' not in re.search(r'"fx": \[(.*?)\]',dl,re.S).group(1))
    check('provider aliases preserved', '"USDJPY=X": "JPY=X"' in loader and '"USDIDR=X": "IDR=X"' in loader)
    check('full desk separates data and bias', '"data_state": "LIVE" if len(univ) else "NO_DATA"' in run and '"bias_state"' in run and '"driver_coverage"' in run)
    check('dedicated FX model', 'function modelFx(){' in dashboard and "case'fx':return modelFx();" in dashboard)
    check('FX price-only non-promotion', 'NO DIRECTIONAL TRADE FROM PRICE ALONE' in dashboard and 'do not rescue the falsified price-only FX family' in dashboard)
    check('Mission distinguishes FX price and macro context', 'SPOT LIVE · MACRO PENDING' in dashboard)
    check('strict neutral alignment', "if(bd==='neutral')return false;" in dashboard)
    check('FX fast price context cannot enter Alpha', "const fxMacroReady=marketId!=='fx'||String(m?.bias_state||'').toUpperCase()==='LIVE';" in dashboard and "const aligned=fxMacroReady&&isSetupAligned" in dashboard)
    check('Alpha staged funnel', 'ALPHA EVIDENCE FUNNEL' in dashboard and 'TACTICAL DISCOVERY POOL' in dashboard and 'CAPITAL PERMISSION' in dashboard)
    alpha=dashboard[dashboard.index('function modelAlpha(){'):dashboard.index('function modelInstitutional(){')]
    check('Alpha radial overlap removed', 'Math.cos' not in alpha and 'Math.sin' not in alpha)
    check('Alpha visible candidates capped', '.slice(0,5).map' in alpha)
    check('Alpha no live-alpha overclaim', 'LIVE ALPHA GATE' not in alpha and 'OBSERVED CANDIDATES' not in alpha and 'not probability' in alpha)
    check('market canvas candidate cap', "setups.slice(0,5).map" in dashboard)
    check('derivatives graph cap', "slice(0,6);" in dashboard and "crypto.slice(0,3).map" in dashboard)
    check('flow graph cap', 'optRot.slice(0,6).map' in dashboard and 'observedRot.slice(0,6).map' in dashboard)

    # Alias contract test: provider frames return under requested/user-facing symbols.
    import data.loader as L
    idx=pd.date_range('2025-01-01',periods=80,freq='B')
    frame=pd.DataFrame({'Open':1.0,'High':1.1,'Low':0.9,'Close':1.0+np.arange(80)*0.001,'Volume':100},index=idx)
    old_http=L._download_many_http; old_disk=L._DISK_CACHE; old_mem=dict(L._MEM)
    try:
        L._DISK_CACHE={}; L._MEM.clear()
        L._download_many_http=lambda providers,days:{p:frame for p in providers}
        got=L.load_bundle(['USDJPY=X','USDIDR=X'],days=80)
        check('FX alias runtime contract', set(got)=={'USDJPY=X','USDIDR=X'}, str(got.keys()))
    finally:
        L._download_many_http=old_http; L._DISK_CACHE=old_disk; L._MEM.clear(); L._MEM.update(old_mem)

    # Fast desk: six observed FX pairs cannot become NO_DATA.
    from run import build_fast_desk
    names=['EURUSD=X','USDJPY=X','GBPUSD=X','AUDUSD=X','USDIDR=X','DX-Y.NYB']
    frames={t:frame*(1+i*.01) for i,t in enumerate(names)}
    data={'prices':{'fx':{t:f['Close'] for t,f in frames.items()}},'ohlcv':{'fx':frames},'markets':['fx'],
          'sources':{'fx':'fixture live'},'fred':{},'fred_source':'NO_DATA','overall_source':'fixture',
          'treasury_liquidity':{},'proxies':{},'feeds':{}}
    desk=build_fast_desk(data,top_per_market=6)
    fx=desk['markets']['fx']
    check('FX observed state live with six pairs', fx['data_state']=='LIVE' and fx['funnel']['universe']==6, str(fx))
    check('FX breadth six', desk['market_breadth']['fx']['coverage']==6)

    subprocess.run([sys.executable,'-m','compileall','-q',str(ROOT)],check=True)
    check('Python compile', True)
    scripts=re.findall(r'<script>(.*?)</script>',dashboard,re.S)
    for i,script in enumerate(scripts):
        f=Path(tempfile.gettempdir())/f'warroom_v28_{i}.js'; f.write_text(script)
        subprocess.run(['node','--check',str(f)],check=True,capture_output=True,text=True)
    check('JavaScript syntax', True)

    status='PASS'
    error=None
except Exception as exc:
    status='FAIL'; error=f'{type(exc).__name__}: {exc}'

report={'version':'2.8','status':status,'passed':sum(x['passed'] for x in checks),'total':len(checks),'checks':checks,'error':error,
        'not_verified_here':['authenticated paid-provider responses without user credentials','public internet reachability from the deployment host','future provider schema changes']}
(ROOT/'V28_FX_ALPHA_VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if status=='PASS' else 1)

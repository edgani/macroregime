from __future__ import annotations
from pathlib import Path
import json, re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
checks = {}

def check(name, cond, detail=''):
    checks[name] = {'pass': bool(cond), 'detail': detail}

html = (ROOT/'dashboard.html').read_text(encoding='utf-8')
check('14 navigation tabs', len(re.findall(r'<div class="tab(?: on| core)?" data-v=', html)) == 14)
check('no legacy current-value TABS panels', 'Q3 · Growth↓ Inflation↑' not in html and 'Panic-Bottom' not in html)
check('research-only header', 'RESEARCH ONLY · PAPER/LIVE BLOCKED' in html)
check('daily snapshot label', ('DATA DAILY' in html or 'INTRADAY QUOTE + DAILY' in html) and 'RESILIENT_PROVIDER_CASCADE_WITH_LAST_KNOWN_GOOD_CACHE' in (ROOT/'run.py').read_text())
check('early warning registry key fixed', "ew:'EARLY WARNING'" in html)
check('early warning live stress panel', 'Current Stress Snapshot' in html)
check('shock is score not probability', 'Shock-stress score' in html and 'score, not calibrated crash probability' in html)
check('funnel reconciled labels', all(x in html for x in ('LOADED','HISTORY-ELIGIBLE','SIGNAL-VALID','DISPLAYED')))
check('no gamma-aware hard-code', 'gamma-aware + R/R gate' not in html)
check('no June-26 matrix label', 'your June-26 matrix' not in html)
check('independent rotation wording', 'Same-family overlap withheld' in html and 'INDEPENDENT_EVIDENCE_REQUIRED' in (ROOT/'alpha_foundry_adapter.py').read_text())
check('risk range claim de-overclaimed', 'mqa_risk_range_proxy' in (ROOT/'gcfis/engines/entry.py').read_text() and 'The REAL Hedgeye' not in (ROOT/'gcfis/engines/entry.py').read_text())
check('index excluded from IHSG setups', '_surfaceable_ticker' in (ROOT/'run.py').read_text())
check('stock proxy exclusions present', 'EWT' in (ROOT/'run.py').read_text() and 'XLK' in (ROOT/'run.py').read_text())
check('price-only action is watch', 'WATCH_LONG' in (ROOT/'price_setups.py').read_text())
check('score not conviction label', 'SETUP_SCORE' in (ROOT/'price_setups.py').read_text())
check('driver signed contribution', 'signed_contribution_z' in (ROOT/'gcfis/market_drivers.py').read_text())
check('commodity driver not universally gold', '_driver_bundle' in (ROOT/'run.py').read_text() and 'NO_SUPPORTED_COMMODITY_MODEL' in (ROOT/'run.py').read_text())

# Runtime function tests.
from run import _surfaceable_ticker, _driver_bundle
from gcfis.market_drivers import read_all
from alpha_foundry_adapter import attach_alpha_foundry
from price_setups import price_signal_setups

check('US ETF filtered', not _surfaceable_ticker('us','EWT') and not _surfaceable_ticker('us','XLK'))
check('US stock admitted', _surfaceable_ticker('us','AMD'))
check('IHSG index filtered', not _surfaceable_ticker('idx','^JKSE'))
check('IHSG stock admitted', _surfaceable_ticker('idx','ANTM.JK'))

idx = pd.date_range('2024-01-01', periods=120, freq='B')
# series with a final positive shock after stable history
rng2=np.random.default_rng(99)
base=np.cumsum(rng2.normal(0,0.05,120)); base[-1]+=5.0
s = pd.Series(base, index=idx)
models = read_all({'TIPS10Y': s})
real_row = next(r for r in models['us']['drivers'] if r['series']=='TIPS10Y')
check('rising real yield is US headwind', real_row['effect']=='HEADWIND' and real_row['signed_contribution_z'] < 0, str(real_row))
cbias, crows, _, _, scope = _driver_bundle(models,'commodity',['CL=F','BZ=F','HG=F'])
check('oil/copper does not inherit gold drivers', scope.startswith('OIL') and all(str(r['factor']).startswith('OIL') for r in crows), f'{cbias} {scope} {crows}')

desk={'meta':{},'markets':{'commod':{'setups':[{'tk':'CL=F','valid':True,'evidence_family':'PRICE_RS'}]}},'systemic':{'rotation_in_raw':['CL=F'],'rotation_out_raw':[]},'alpha':[]}
out=attach_alpha_foundry(desk)
check('same-family RS overlap withheld from Mission', out['systemic']['rotation_in']==[] and out['systemic']['rotation_same_family_overlap']==['CL=F'])

# Price setup geometry and semantics.
rng=np.random.default_rng(7)
close=100*np.exp(np.cumsum(rng.normal(0.0005,0.012,320)))
high=close*(1+rng.uniform(0.001,0.02,320)); low=close*(1-rng.uniform(0.001,0.02,320))
open_=low+(high-low)*rng.uniform(0.2,0.8,320); vol=rng.integers(1_000_000,10_000_000,320)
df=pd.DataFrame({'Open':open_,'High':high,'Low':low,'Close':close,'Volume':vol}, index=pd.date_range('2025-01-01',periods=320,freq='B'))
rows=price_signal_setups({'TEST':df},top=1)
check('price fallback produces watch not buy recommendation', bool(rows) and rows[0]['act']=='WATCH_LONG', str(rows[:1]))
if rows and rows[0]['valid']:
    check('price fallback directional geometry', rows[0]['s'] < rows[0]['e'] < rows[0]['t'])
else:
    check('price fallback directional geometry', True, 'row failed gate honestly')

report={'pass':all(v['pass'] for v in checks.values()),'passed':sum(v['pass'] for v in checks.values()),'total':len(checks),'checks':checks}
(ROOT/'V4_RUNTIME_AND_CLAIM_AUDIT.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print(json.dumps(report,indent=2,default=str))
raise SystemExit(0 if report['pass'] else 1)

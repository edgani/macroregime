from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np
from _stubs import install_streamlit_stub
install_streamlit_stub()
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('macro_embedded_test',root/'macro_embedded.py')
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)

# boundary/state sanity
g,_=m.growth_state(1.0,1.0,1.0); assert isinstance(g,str)
l,_=m.lead_state(-1.2); assert 'DOWNTURN' in l or 'BELOW' in l
inf,_,d=m.inflation_state(2.5,2.5,3.0,3.0); assert d in ('COOLING','MIXED','HEATING')
assert m.crash_state_name(80,80)[0]=='CRASH DANGER'
assert m.crash_state_name(30,75)[0]=='POWDER KEG'
assert 0<=m.fiscal_constraint_score(120,-6,4,1.5)<=100
assert 0<=m.energy_pressure_score(80,20,70)<=100

# fuzz bounds
rng=np.random.default_rng(123)
for _ in range(1000):
    vals=rng.normal(size=4)*50
    fs=m.fiscal_constraint_score(*vals)
    assert np.isfinite(fs) and 0<=fs<=100
    es=m.energy_pressure_score(*vals[:3])
    assert np.isfinite(es) and 0<=es<=100

# action engine supportive vs stressed
support=m.action_state_engine(plain_state='EXPANDING · MOMENTUM HEALTHY',growth='ABOVE TREND',lead_value=1.0,inflation_dir='COOLING',credit_tone='green',stress_score=20,fragility_score=20,fcig=-0.5,event_override=None,market_structure='BROAD ATH / BROADENING',rates_score=20,fiscal_score=20)
stress=m.action_state_engine(plain_state='SLOWING · STRESS BUILDING',growth='CONTRACTION',lead_value=-1.5,inflation_dir='HEATING',credit_tone='red',stress_score=85,fragility_score=85,fcig=1.0,event_override={'impact':'SEVERE','name':'War / energy stagflation'},market_structure='BREADTH DETERIORATING',rates_score=85,fiscal_score=85)
assert support['score'] < stress['score']
assert stress['label'] in ('CRISIS RISK-OFF','DEFENSIVE')

# scenarios must keep score bounds and explicit falsifiers
sc=m.adaptive_scenarios(growth='BELOW TREND',lead_value=-1.2,lead_delta=-0.2,wei=-0.5,inflation_dir='HEATING',claims=250,claims_3m=210,ebp_prob=40,hy=5,hy_3m=4,fcig=0.5,market_structure='BREADTH DETERIORATING',fiscal_score=80,rates_score=80,energy_score=80,funding_score=80,gpr_pct=90,gpr_change=10,gscpi=2,gscpi_delta=1,epu_pct=90,spy_ath=-0.5,interest_gdp=4,stress_score=80,fragility_score=80,credit_score=80)
assert sc and all(0<=x['score']<=100 and x['invalidates'] for x in sc)
print('TEST_MACRO_LOGIC_PASS',{'supportive_score':support['score'],'stress_score':stress['score'],'scenarios':len(sc)})

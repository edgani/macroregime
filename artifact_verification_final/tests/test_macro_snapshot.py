from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd
from _stubs import install_streamlit_stub
st=install_streamlit_stub()
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('macro_snapshot_test',root/'macro_embedded.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
idx=pd.date_range('2024-01-01',periods=36,freq='MS')
def ser(last, start=None):
    start=last if start is None else start
    return pd.Series(np.linspace(start,last,len(idx)),index=idx)

def payload(mode='healthy'):
    healthy=mode=='healthy'
    d={
      'BBKMGDP':ser(1.0 if healthy else -1.2), 'BBKMCOIX':ser(0.8 if healthy else -1.0), 'BBKMLEIX':ser(0.9 if healthy else -1.4), 'WEI':ser(2.0 if healthy else -2.0),
      'PCETRIM12M159SFRBDAL':ser(2.5 if healthy else 4.5,3.5 if healthy else 3.0), 'PCEPILFE':ser(120 if healthy else 140,100),
      'SAHMREALTIME':ser(0.2 if healthy else 0.8), 'ICSA':ser(210000 if healthy else 320000,230000 if healthy else 200000),
      'NFCIRISK':ser(-0.5 if healthy else 2.0,-0.2), 'VIXCLS':ser(14 if healthy else 45,18), 'BAMLH0A0HYM2':ser(3.0 if healthy else 7.0,3.5),
      'DGS10':ser(3.5 if healthy else 6.0,4.0), 'DGS2':ser(3.3 if healthy else 5.5,4.0), 'THREEFYTP10':ser(0.2 if healthy else 2.0,0.0), 'T5YIE':ser(2.2 if healthy else 3.5,2.0),
      'DCOILWTICO':ser(75 if healthy else 140,80), 'GFDEGDQ188S':ser(110 if healthy else 140), 'FYFSGDA188S':ser(-5 if healthy else -10), 'FYOIGDA188S':ser(3 if healthy else 5),
      'GSCPI':ser(0 if healthy else 2.5,0), 'USEPUINDXD':ser(100 if healthy else 400,100),
    }
    research={
      'EBP':pd.DataFrame({'ebp':[0.0,0.1 if healthy else 2.0],'est_prob':[0.05,0.08 if healthy else 0.5]}),
      'FCIG':pd.DataFrame({'FCI-G Index':[0.0,-0.5 if healthy else 1.2]})
    }
    mi=pd.date_range('2024-01-01',periods=36,freq='MS')
    market={
      'SPY':pd.Series(np.linspace(400,600 if healthy else 450,36),index=mi),
      'IWM':pd.Series(np.linspace(180,240 if healthy else 170,36),index=mi),
      'RSP':pd.Series(np.linspace(140,180 if healthy else 135,36),index=mi),
    }
    return d,research,market,pd.DataFrame(),40.0,pd.Timestamp('2026-08-01'),{}

m.load_all=lambda:payload('healthy')
h=m.compute_macro_gate_snapshot(False)
assert h['action_label']!='HOLD / MACRO GATED' and h['macro_data_coverage']>0.8
m.load_all=lambda:payload('crisis')
c=m.compute_macro_gate_snapshot(False)
assert c['action_score']>h['action_score'] and c['crash_state'] in ('WATCH','POWDER KEG','SHOCK / STRESS','CRASH DANGER')
# missing critical data -> fail closed
def missing():
    return {},{}, {},pd.DataFrame(),np.nan,None,{'all':'offline'}
m.load_all=missing
g=m.compute_macro_gate_snapshot(False)
assert g['action_label']=='HOLD / MACRO GATED' and g['crash_state']=='GATED' and g['credit_state']=='GATED'
print('TEST_MACRO_SNAPSHOT_PASS',{'healthy':h['action_label'],'crisis':c['action_label'],'missing':g['action_label']})

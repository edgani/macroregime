import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from engines.decision_engine import operational_posture, projection_guidance, company_gate_guidance
from engines.projection_engine import normalized_projection_path, opportunity_radar

sc=pd.DataFrame([
 {'type':'BASE','scenario':'base','supporting_evidence':'a; b','contradicting_evidence':'None in loaded subset'},
 {'type':'COMPETING','scenario':'comp','supporting_evidence':'a','contradicting_evidence':'None in loaded subset'},
 {'type':'TAIL','scenario':'tail','supporting_evidence':'None in loaded subset','contradicting_evidence':'None in loaded subset'},
])
p=operational_posture({},sc,{'active_phases':[],'watch_phases':[]})
assert p['posture']=='SELECTIVE RISK-ON RESEARCH'

stats=pd.DataFrame([
 {'horizon':'1M','p_positive':.6,'p_loss10':.1,'p10':-.08,'median':.03,'p90':.15},
 {'horizon':'3M','p_positive':.7,'p_loss10':.15,'p10':-.12,'median':.10,'p90':.30},
 {'horizon':'6M','p_positive':.7,'p_loss10':.2,'p10':-.15,'median':.15,'p90':.45},
 {'horizon':'12M','p_positive':.75,'p_loss10':.2,'p10':-.18,'median':.25,'p90':.70},
])
g=projection_guidance(stats,'3M')
assert '3M analog range' in g['read']
path=normalized_projection_path(stats)
assert list(path.month)==[0,1,3,6,12]
assert path.iloc[0]['median']==100

detail={'reason':'SEC confirms capture','chain':{'constraint_evidence':True,'demand_capture_evidence':True,'sec_revenue_capture':True,'sec_operating_capture':True,'monetization_language':True}}
cg=company_gate_guidance(detail,True)
assert cg['research_state']=='PRIORITY WATCHLIST'
assert cg['stages'][0][1]=='PASS' and cg['stages'][1][1]=='PASS'
print('v5.2 decision tests PASS')

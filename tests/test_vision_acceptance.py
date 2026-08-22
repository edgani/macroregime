from eros.state_engine import derive_states
from eros.scenario_engine import discover_verified, radar_from_news, radar_from_news_general
from eros.company_engine import generate_candidates

# factual-like deterministic fixture only validates logic, never scientific edge
macro={'as_of':'2026-08-01','series':{}}
def add(sid, vals):
    macro['series'][sid]={'last_date':'2026-08-01','last_value':vals[-1],'values':[[f'2026-{i+1:02d}-01',v] for i,v in enumerate(vals)]}
add('INDPRO',[100,100.5,100.3,99.8,99.5,99.2,99.0,98.8,98.6,98.4,98.3,98.2,98.0])
add('PAYEMS',[100,100.1,100.2,100.2,100.1,100.0,99.9,99.8,99.7,99.6,99.5,99.4,99.3])
add('UNRATE',[4.0,4.0,4.0,4.1,4.1,4.1,4.2,4.2,4.2,4.3,4.3,4.4,4.4])
add('ICSA',[220,221,223,225,228,232,236,241,246,252,258,265,272])
add('CPIAUCSL',[100,100.3,100.6,100.9,101.2,101.5,101.8,102.1,102.5,102.8,103.1,103.4,103.7])
add('CPILFESL',[100,100.3,100.6,100.9,101.2,101.5,101.8,102.1,102.4,102.7,103.0,103.3,103.6])
add('PPIACO',[100,100.4,100.7,101.1,101.4,101.8,102.1,102.5,102.9,103.3,103.7,104.1,104.5])
add('FEDFUNDS',[5.25]*13)
add('DGS2',[4.9]*13); add('DGS10',[4.4]*13); add('DFII10',[2.0]*13); add('T10YIE',[2.4]*13)
add('BAMLH0A0HYM2',[3.2,3.2,3.3,3.4,3.5,3.6,3.7,3.8,3.9,4.0,4.2,4.4,4.6])
add('WALCL',[100]*13); add('RRPONTSYD',[50,49,48,47,46,45,44,43,42,41,40,39,38]); add('WTREGEN',[20,21,22,23,24,25,26,27,28,29,30,31,32])
add('HOUST',[100,99,98,97,96,95,94,93,92,91,90,89,88]); add('PERMIT',[100,99,98,97,96,95,94,93,92,91,90,89,88])
data={'macro':macro,'treasury':{'status':'LIVE','debt':{'record_date':'2026-08-01','tot_pub_debt_out_amt':'40000000000000'}}}
states,ev=derive_states(data)
assert any(x.state_id=='INFLATION' and x.value=='HOT/STICKY' for x in states)
assert any(x.state_id=='LABOR' and x.value=='SOFTENING' for x in states)
sc=discover_verified(ev)
assert any(x.scenario_id=='SCN_POLICY_CONFLICT' for x in sc), [x.scenario_id for x in sc]
# General radar not hardcoded to only one attachment
radar=radar_from_news({'leads':[{'theme':'AI_CAPITAL','title':'x'},{'theme':'AI_CREDIT','title':'y'},{'theme':'CHINA_GOLD','title':'z'},{'theme':'INDONESIA','title':'q'}]})
assert len(radar)==4
gen=radar_from_news_general({'leads':[{'theme':'BROAD_DISCOVERY','title':'New export ban creates copper supply shortage as financing costs rise'}]})
assert gen, 'general scenario discovery failed'
# Candidate generation is automatic. In this environment yfinance may be absent; still must never become qualified BUY.
cand=generate_candidates(sc,radar,force=False)
assert cand
assert all(x.action not in ('BUY','SHORT','BUILD') for x in cand)
print('VISION_ACCEPTANCE_PASS',len(states),len(sc),len(radar),len(cand))

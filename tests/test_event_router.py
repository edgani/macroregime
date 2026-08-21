from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from final_core.event_router import route
cases={
'housing_policy':'CPI, PPI, NFP, retail sales, home data ga cukup juga buat bikin hilang hawkish?',
'openai_ipo':'OpenAI revenue run rate tops $40 billion ahead of IPO. Next mega IPO, Q1 2027.',
'anthropic_ipo':'Anthropic investors betting company could reach $2 trillion valuation in an October IPO; menjaga index supaya valuasi max.',
'datacenter_2008':'SEC made it easier for data center owners to sell asset-backed securities with fewer disclosures. 2008 in the making.',
'gex':'QQQ GEX positive gamma, put/call gamma, dealer positioning, VIX below 15.'}
expected={
'housing_policy':{'HOUSING','INFLATION_SHOCK','LABOR_SHOCK','POLICY'},
'openai_ipo':{'IPO','CAPITAL_FORMATION'},
'anthropic_ipo':{'IPO','CAPITAL_FORMATION','INDEX_MECHANICS'},
'datacenter_2008':{'REGULATORY_CHANGE','SECURITIZATION'},
'gex':{'MARKET_STRUCTURE'}}
for k,text in cases.items():
    got={x['event_type'] for x in route(text)['candidate_event_types']}
    assert expected[k].issubset(got),(k,expected[k],got)
    assert route(text)['production_eligible'] is False
print('PASS: event router classified all attachment narrative families and remains verification-gated')

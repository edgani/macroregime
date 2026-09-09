from decision_core import entry_decision, expression_decision

# hype/weak confirmation: never entry
r=entry_decision({'market':'US','research_action':'WATCH / NO FORCED TRADE','market_model_status':'RESEARCH READY / FUNDAMENTALS','data_quality':'HIGH','evidence_families':1,'deterioration_families':0,'price':100},{'valuation_confidence':'HIGH','expectation_gap':0.8,'fv_base':180},{'action_label':'RISK-ON','crash_state':'RESILIENT'})
assert r['entry_stage']=='DISCOVER'
# crypto revenue without holder capture must remain gated
r=entry_decision({'market':'Crypto','research_action':'BUILD CANDIDATE','market_model_status':'PARTIAL / ECONOMICS','data_quality':'HIGH','evidence_families':4,'deterioration_families':0,'price':10},{},{})
assert r['entry_stage']=='DISCOVER'
# identical peers cannot create top-decile evidence
from decision_core import neutral_percentile_rank
assert neutral_percentile_rank([1]*30,1)==0.5
print('TEST_NEGATIVE_CONTROLS_PASS')

from __future__ import annotations
import math
import pandas as pd
from story_optionality import story_optionality, analyst_revision_signal, apply_story_optionality

# Loss alone is not an edge: deteriorating economics must classify as bad loss.
bad={
    'market':'IHSG','eps_ttm':-10,'net_margin':-0.20,'revenue_growth_yoy':-0.15,
    'gross_margin_change':-0.04,'net_margin_change':-0.08,'fcf_ttm':-100,
    'fcf_growth_yoy':-0.40,'total_cash':50,'total_debt':200,'shares_change_yoy':0.15,
}
b=story_optionality(bad)
assert b['loss_type']=='STRUCTURAL / BAD LOSS', b
assert b['story_state']=='BAD LOSS / AVOID STORY BIAS', b
assert b['financing_risk']=='HIGH', b

# Improving loss + runway + investment intensity can become an early story candidate.
good={
    'market':'IHSG','eps_ttm':-2,'net_margin':-0.06,'revenue_growth_yoy':0.28,
    'gross_margin_change':0.045,'net_margin_change':0.07,'fcf_ttm':-20,
    'fcf_growth_yoy':0.60,'total_cash':100,'total_debt':20,'shares_change_yoy':0.01,
    'rd_to_revenue':0.02,'capex_to_revenue':0.14,
}
g=story_optionality(good)
assert g['loss_type'] in {'TURNAROUND LOSS','INVESTMENT-LED LOSS'}, g
assert g['story_optionality_score'] >= 65, g
assert g['financing_risk']!='HIGH', g

# US revision signal uses change + breadth, not headline narrative.
us={
    **good,'market':'US','eps_estimate_next_year':0.40,'eps_estimate_next_year_30d_ago':0.20,
    'eps_revisions_up_30d':8,'eps_revisions_down_30d':1,'analyst_count_next_year':12,
    'revenue_estimate_growth_next_year':0.24,
}
r=analyst_revision_signal(us)
assert r['expectation_revision_state']=='UPWARD REVISION', r
out=apply_story_optionality(pd.DataFrame([us]))
assert out.iloc[0]['expectation_optionality_state']=='INFLECTION + REVISIONS CONFIRM', out.iloc[0].to_dict()
print('TEST_STORY_OPTIONALITY_PASS')

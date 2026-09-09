from __future__ import annotations
import math, tempfile
from datetime import datetime
from pathlib import Path

from decision_core import *


def assert_close(a,b,tol=1e-9):
    assert abs(a-b)<=tol,(a,b)

# tie-neutral percentile
assert_close(neutral_percentile_rank([10,10,10,10],10),0.5)
assert neutral_percentile_rank([1,2,3,4],4) > 0.8

# detection != entry when valuation is gated
row={"market":"US","research_action":"BUILD CANDIDATE","market_model_status":"RESEARCH READY / FUNDAMENTALS","data_quality":"HIGH","vertical_status":"READY","evidence_families":4,"deterioration_families":0,"price":50}
r=entry_decision(row,{"valuation_confidence":"GATED"},{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"})
assert r["entry_stage"]=="DISCOVER" and "valuation" in " ".join(r["gates"]).lower()

# starter: exceptional asymmetry but only 2 evidence families
val={"valuation_confidence":"HIGH","expectation_gap":0.50,"fv_base":90}
r=entry_decision({**row,"evidence_families":2},val,{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"})
assert r["entry_stage"]=="STARTER",r

# core: 3 evidence families high quality
r=entry_decision({**row,"evidence_families":3},val,{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"})
assert r["entry_stage"]=="CORE",r

# add: fair value outruns price
prior={"price":50,"fv_base":70}
r=entry_decision({**row,"evidence_families":4,"price":55},{**val,"fv_base":90},{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"},prior)
assert r["entry_stage"]=="ADD" and r["revision_edge"]>0,r

# no chase: price outruns FV
r=entry_decision({**row,"evidence_families":4,"price":80},{**val,"fv_base":75},{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"},prior)
assert r["entry_stage"]=="NO CHASE",r

# macro risk-off sizes down core/add and disables leverage upgrade
r=entry_decision({**row,"evidence_families":4,"price":55},{**val,"fv_base":90},{"action_label":"DEFENSIVE","crash_state":"CRASH DANGER"},prior)
assert "MACRO" in r["entry_stage"] and "NO LEVERAGE" in r["entry_action"]

# IHSG never leverage/options
entry={"entry_stage":"CORE"}
e=expression_decision({"market":"IHSG","symbol":"BBCA.JK","data_quality":"HIGH","evidence_families":4,"research_action":"BUILD CANDIDATE","market_model_status":"RESEARCH READY","vertical_status":"READY"},entry,{})
assert not e["leverage_allowed"] and not e["option_allowed"] and "CASH" in e["best_expression"]

# FX/commodity fail closed until dedicated model says ready
for m in ("FX","Commodity"):
    e=expression_decision({"market":m,"symbol":"X","data_quality":"HIGH","evidence_families":4,"research_action":"BUILD CANDIDATE","market_model_status":"GATED"},entry,{})
    assert not e["leverage_allowed"],(m,e)

# US leverage when earned
us=expression_decision({"market":"US","symbol":"MU","data_quality":"HIGH","evidence_families":4,"research_action":"BUILD CANDIDATE","market_model_status":"RESEARCH READY / FUNDAMENTALS","vertical_status":"READY"},entry,{"action_label":"SELECTIVE RISK-ON","crash_state":"RESILIENT"})
assert us["leverage_allowed"]

# crypto options only BTC/ETH and only after live option check passes
for sym,expected in [("BTC-USD",True),("ETH-USD",True),("ZEC-USD",False)]:
    x=expression_decision({"market":"Crypto","symbol":sym,"data_quality":"HIGH","evidence_families":4,"research_action":"BUILD CANDIDATE","market_model_status":"RESEARCH READY / VALUE CAPTURE","vertical_status":"READY"},entry,{}, {"iv":0.6,"spread":0.05,"liquidity":"GOOD"})
    assert x["option_allowed"] is expected,(sym,x)

# checkpoint state isolation and previous revision memory
with tempfile.TemporaryDirectory() as td:
    p=Path(td)
    save_checkpoint("ABC",price=10,fv_base=12,entry_stage="STARTER",default_root=p)
    assert get_prior_checkpoint("ABC",p)["price"]==10
    save_checkpoint("ABC",price=11,fv_base=15,entry_stage="CORE",default_root=p)
    old=get_prior_checkpoint("ABC",p)
    assert old["price"]==10 and old["fv_base"]==12

# publication-time execution guard
from zoneinfo import ZoneInfo
ny=ZoneInfo("America/New_York")
a=earliest_executable_timestamp(datetime(2025,5,7,16,5,tzinfo=ny))
assert (a.year,a.month,a.day,a.hour,a.minute)==(2025,5,8,9,30),a
b=earliest_executable_timestamp(datetime(2025,5,7,8,0,tzinfo=ny))
assert (b.hour,b.minute)==(9,30)
c=earliest_executable_timestamp(datetime(2025,5,7,12,0,tzinfo=ny))
assert (c.hour,c.minute)==(12,0)

print('TEST_DECISION_CORE_PASS')

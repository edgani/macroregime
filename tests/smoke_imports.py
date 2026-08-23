
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from config.metric_registry_v4 import METRIC_FAMILIES
from engines import state_engine,scenario_engine,thesis_engine,crash_engine,projection_engine,cross_market_engine,bottleneck_engine,opportunity_engine,runway_engine,experiment_registry,decision_engine,visual_engine
assert len(METRIC_FAMILIES)==52
empty={'fred':{},'prices':{},'treasury':{},'crypto_native':{}}
s=state_engine.current_state(empty)
assert isinstance(s,dict)
assert len(scenario_engine.live_evidence(s))==4
assert len(crash_engine.crash_matrix(s))==5
print('SMOKE_IMPORTS_PASS')

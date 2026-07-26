from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research_evidence_v53 import load_research_evidence

def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ok(name, cond):
    if not cond: raise AssertionError(name)
    print('PASS',name)

def main():
    final=json.loads((ROOT/'V57_CUSP_RESEARCH_FINAL.json').read_text())
    reg=load_research_evidence()
    r73=json.loads((ROOT/'research_v57/results/V73_CUSP_HISTORICAL_RESULTS.json').read_text())
    r74=json.loads((ROOT/'research_v57/results/V74_BREADTH_CUSP_RESULTS.json').read_text())
    r75=json.loads((ROOT/'research_v57/results/V75_PRE1973_CUSP_RESULTS.json').read_text())
    ok('final_schema',final['schema']=='warroom.cusp_research_final.v57')
    ok('three_studies',len(final['studies'])==3)
    ok('all_not_proven',all(x['verdict'].startswith('NOT_PROVEN') for x in [r73,r74,r75]))
    ok('v73_predictive_gate_failed',not r73['gates']['all_four_point_improvements_positive'] and not r73['gates']['simultaneous_adjusted_lower_bounds_positive'])
    ok('v74_lockbox_zero_events',r74['positive_rows']['lockbox']==0 and not r74['gates']['simultaneous_lower_positive'])
    ok('v75_disjoint_gate_failed',not r75['historical_regime_support'] and not r75['gates']['simultaneous_lower_positive'])
    ok('result_hashes',h(ROOT/'research_v57/results/V73_CUSP_HISTORICAL_RESULTS.json')=='b89b6eb24e2d4405653ec9fed40bf9620c2ccf381baa1ed89ed2659279e0ff7c' and h(ROOT/'research_v57/results/V74_BREADTH_CUSP_RESULTS.json')=='a2497d8b08235fd1873d7c1b5e5ca3a27dc775ffed4c6b51a4c77f041451f206' and h(ROOT/'research_v57/results/V75_PRE1973_CUSP_RESULTS.json')=='e9e97691166c3c3497f82e205fcd83bc59affed0abd4e2bc1185898751f301f4')
    ok('protocol_hashes',h(ROOT/'research_v57/V73_CUSP_STRUCTURAL_FRAGILITY_PROTOCOL_FROZEN.json')=='6c3ab960c28f1fd81c80a2b8f23cbb2f6352ee6e331f24dcb8c99bca2628e3e9' and h(ROOT/'research_v57/V74_BREADTH_CUSP_VOL_TRANSITION_PROTOCOL_FROZEN.json')=='a952e77564aaf3e82581ead79d5854e5f6dace82bb5b3bce07aa9a443de9bfdf' and h(ROOT/'research_v57/V75_PRE1973_CUSP_PROTOCOL_FROZEN.json')=='530fff9e19dff52f3293b477ce2f675b1e391c4807e6e91a17eb2527d77b42fd')
    ok('source_hashes',h(ROOT/'research/macro_panel.parquet')=='3ee5d345976759c93e2f37ad77b7e110a891a05e5d36817204fa239768d5d802' and h(ROOT/'research/sp500_panel.parquet')=='db2a61d7f66d219354cfaad9dff01a5c9d5b01145ae11549cd11555588729420')
    cusp=[x for x in reg['claims'] if str(x.get('study','')).startswith(('V73_','V74_','V75_'))]
    ok('registry_three_claims',len(cusp)==3)
    ok('registry_zero_weight',all(x['live_decision_weight']==0.0 for x in cusp))
    ok('registry_capital_blocked',all(x['capital_permission']=='BLOCKED' and x['prospective_pass'] is False for x in cusp))
    ok('retired_from_crash_meter',reg['cusp_research_v57']['crash_meter_inclusion']=='REJECTED')
    ok('decision_test_sequential_stop',final['sequential_decision']['decision_value']=='NOT_RUN_BECAUSE_UPSTREAM_GATE_FAILED')
    ok('final_fail_closed',final['predictive_components_promoted']==0 and final['live_decision_weight']==0.0 and final['capital_permission']=='BLOCKED')
    print('V57_CUSP_RESEARCH_TESTS=15/15 PASS')
if __name__=='__main__': main()

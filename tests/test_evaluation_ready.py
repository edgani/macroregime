from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.evaluation import spearman, interval_score, evaluate_scope, build_evaluation_report

def ticket(i):
    return {'component_states':{'mqa_benchmarks':{'fixed_lower':99,'fixed_upper':101,'conformal_lower':99.2,'conformal_upper':100.8},
             'momentum_axes':{'trend_context':float(i),'acceleration':float(i),'release_rank':i/100,'signed_persistence':.2,
                              'path_efficiency':.5,'noise_ratio':.5,'exhaustion_risk':.1}}}
def outcome(i):
    return {'target_close':100+i/100,'forward_return':i/10000}

def test_spearman_perfect_monotonic(): assert abs(spearman([1,2,3],[10,20,30])-1)<1e-12
def test_interval_score_penalizes_miss(): assert interval_score(110,99,101)>interval_score(100,99,101)
def test_insufficient_scope_never_promotes():
    result=evaluate_scope([(ticket(i),outcome(i)) for i in range(10)],scope_id='BTCUSDT:1h',horizon=1,min_n=20)
    assert result.verdict=='INSUFFICIENT_PROSPECTIVE_DATA'
    assert 'PAPER_LIVE_NOT_AUTO_PROMOTED' in result.reason_codes
def test_empty_report_blocks_paper(tmp_path):
    (tmp_path/'runtime/observations').mkdir(parents=True); (tmp_path/'runtime/outcomes').mkdir(parents=True)
    report=build_evaluation_report(tmp_path)
    assert report['paper_eligible'] is False and report['live_eligible'] is False
    assert (tmp_path/'runtime/evaluation/latest.json').exists()

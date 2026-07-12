import unittest
from warroom_v3.contracts import EvidenceStatus,DecisionStatus
from warroom_v3.gates import evaluate_actionability

BASE=dict(requested_status=DecisionStatus.PAPER,data_available=True,data_fresh=True,mtf_ready=True,probability_calibrated=True,net_ev=.1,capacity_ok=True,kill_switch=False)
class GateTests(unittest.TestCase):
    def test_rejected_blocks(self):
        r=evaluate_actionability({'mqa':EvidenceStatus.REJECTED},**BASE); self.assertFalse(r.eligible); self.assertIn('SCOPE_EVIDENCE_BLOCKED:mqa:REJECTED',r.reason_codes)
    def test_not_evaluated_blocks(self):
        self.assertFalse(evaluate_actionability({'mqa':EvidenceStatus.NOT_EVALUATED},**BASE).eligible)
    def test_missing_data_blocks(self):
        x=dict(BASE);x['data_available']=False;self.assertFalse(evaluate_actionability({'mqa':EvidenceStatus.PAPER_ELIGIBLE},**x).eligible)
    def test_kill_switch_blocks(self):
        x=dict(BASE);x['kill_switch']=True;self.assertFalse(evaluate_actionability({'mqa':EvidenceStatus.PAPER_ELIGIBLE},**x).eligible)
    def test_positive_ev_required(self):
        x=dict(BASE);x['net_ev']=0;self.assertFalse(evaluate_actionability({'mqa':EvidenceStatus.PAPER_ELIGIBLE},**x).eligible)
    def test_paper_can_use_live_grade(self):
        self.assertTrue(evaluate_actionability({'mqa':EvidenceStatus.LIVE_ELIGIBLE},**BASE).eligible)
    def test_live_requires_live_grade(self):
        x=dict(BASE);x['requested_status']=DecisionStatus.LIVE;self.assertFalse(evaluate_actionability({'mqa':EvidenceStatus.PAPER_ELIGIBLE},**x).eligible)

import unittest
from warroom_v3.contracts import *

PAPER_EVIDENCE={k:EvidenceStatus.PAPER_ELIGIBLE for k in ('mqa','momentum','mtf','decision_policy','portfolio_policy')}
LIVE_EVIDENCE={k:EvidenceStatus.LIVE_ELIGIBLE for k in ('mqa','momentum','mtf','decision_policy','portfolio_policy')}

class ContractTests(unittest.TestCase):
    def test_research_ticket_has_no_execution_surface(self):
        t=ResearchObservationTicket("o1","BTCUSDT","1h","2026-07-12T00:00:00Z","abc",{"mqa":{"state":"EXPANSION"}},{"mqa":EvidenceStatus.NOT_EVALUATED})
        self.assertFalse(hasattr(t,"entry_zone")); self.assertFalse(hasattr(t,"probability")); self.assertFalse(hasattr(t,"targets"))
    def test_research_ticket_rejects_top_level_execution_fields(self):
        with self.assertRaises(ValueError): ResearchObservationTicket("o1","BTC","1h","x","h",{"entry":100},{"mqa":EvidenceStatus.RESEARCH_ONLY})
    def test_research_ticket_rejects_nested_execution_fields(self):
        with self.assertRaises(ValueError): ResearchObservationTicket("o1","BTC","1h","x","h",{"mqa":{"execution":{"entry_zone":[1,2]}}},{"mqa":EvidenceStatus.RESEARCH_ONLY})
    def test_research_ticket_rejects_promoted_evidence(self):
        with self.assertRaises(ValueError): ResearchObservationTicket("o1","BTC","1h","x","h",{"mqa":{"state":"X"}},{"mqa":EvidenceStatus.PAPER_ELIGIBLE})
    def test_unavailable_has_no_direction(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.UNAVAILABLE,direction=Direction.LONG)
    def test_unavailable_rejects_hidden_probability(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.UNAVAILABLE,probability=.6)
    def test_paper_requires_complete_execution(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,direction=Direction.LONG)
    def test_paper_requires_all_evidence_components(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.LONG,.6,(.5,.7),(99,101),95,(110,),.25,.1,{"mqa":EvidenceStatus.PAPER_ELIGIBLE})
    def test_long_geometry_enforced(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.LONG,.6,(.5,.7),(99,101),102,(110,),.25,.1,PAPER_EVIDENCE)
    def test_short_geometry_enforced(self):
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.SHORT,.6,(.5,.7),(99,101),95,(90,),.25,.1,PAPER_EVIDENCE)
    def test_paper_requires_paper_evidence(self):
        bad=dict(PAPER_EVIDENCE);bad['mqa']=EvidenceStatus.RESEARCH_ONLY
        with self.assertRaises(ValueError): DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.LONG,.6,(.5,.7),(99,101),95,(110,),.25,.1,bad)
    def test_valid_paper_ticket(self):
        t=DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.LONG,.6,(.5,.7),(99,101),95,(110,),.25,.1,PAPER_EVIDENCE);self.assertEqual(t.status,DecisionStatus.PAPER)
    def test_valid_short_ticket(self):
        t=DecisionTicket("d","BTC","1h","x",DecisionStatus.PAPER,Direction.SHORT,.6,(.5,.7),(99,101),105,(90,),.25,.1,PAPER_EVIDENCE);self.assertEqual(t.direction,Direction.SHORT)
    def test_live_requires_live_evidence(self):
        t=DecisionTicket("d","BTC","1h","x",DecisionStatus.LIVE,Direction.LONG,.6,(.5,.7),(99,101),95,(110,),.25,.1,LIVE_EVIDENCE);self.assertEqual(t.status,DecisionStatus.LIVE)

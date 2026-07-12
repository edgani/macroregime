import json,unittest
from datetime import datetime,timezone
from pathlib import Path
from warroom_v3.data import load_canonical_csv
from warroom_v3.mtf import fuse_mtf
from warroom_v3.pipeline import build_research_observation
ROOT=Path(__file__).resolve().parents[1]
class MTFPipelineTests(unittest.TestCase):
 def test_structural_conflict_blocks_risk(self):
  x=fuse_mtf(structural='BULLISH',trend='BEARISH',tactical='BULLISH',execution='BULLISH');self.assertEqual(x.risk_multiplier_ceiling,0);self.assertIn('STRUCTURAL_TREND_CONFLICT',x.conflict_codes)
 def test_tactical_conflict_caps_risk(self):
  x=fuse_mtf(structural='BULLISH',trend='BULLISH',tactical='BEARISH',execution='BULLISH');self.assertEqual(x.risk_multiplier_ceiling,.25)
 def test_execution_conflict_caps_half(self):
  x=fuse_mtf(structural='BULLISH',trend='BULLISH',tactical='BULLISH',execution='BEARISH');self.assertEqual(x.risk_multiplier_ceiling,.5)
 def test_incomplete_mtf_blocks(self):
  x=fuse_mtf(structural='BULLISH',trend='UNAVAILABLE',tactical='BULLISH',execution='BULLISH');self.assertEqual(x.risk_multiplier_ceiling,0)
 def test_aligned_is_descriptive_not_trade(self):
  x=fuse_mtf(structural='BULLISH',trend='BULLISH',tactical='BULLISH',execution='BULLISH');self.assertEqual(x.alignment_score,1);self.assertFalse(hasattr(x,'entry'))
 def test_pipeline_deterministic(self):
  bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc)); f=json.loads((ROOT/'evidence/formula_registry_active.json').read_text()); hashes={e['component']:e['formula_hash'] for e in f['entries']}; a=build_research_observation(bars,formula_hashes=hashes);b=build_research_observation(bars,formula_hashes=hashes);self.assertEqual(a.observation_id,b.observation_id)
 def test_pipeline_remains_descriptive(self):
  bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc)); f=json.loads((ROOT/'evidence/formula_registry_active.json').read_text());t=build_research_observation(bars,formula_hashes={e['component']:e['formula_hash'] for e in f['entries']});self.assertEqual(t.claim_ceiling,'DESCRIPTIVE_ONLY');self.assertFalse(hasattr(t,'entry_zone'))
 def test_pipeline_evidence_not_evaluated(self):
  bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc)); f=json.loads((ROOT/'evidence/formula_registry_active.json').read_text());t=build_research_observation(bars,formula_hashes={e['component']:e['formula_hash'] for e in f['entries']});self.assertTrue(all(v.value=='NOT_EVALUATED' for v in t.component_evidence.values()))

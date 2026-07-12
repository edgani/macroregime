import unittest
from datetime import datetime,timezone
from pathlib import Path
from warroom_v3.data import load_canonical_csv
from warroom_v3.sensors import true_ranges,compute_momentum_axes
from warroom_v3.causality import assert_prefix_invariant,assert_future_perturbation_invariant
ROOT=Path(__file__).resolve().parents[1]
def fixture():
 bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc)); h=[b.high for b in bars];l=[b.low for b in bars];c=[b.close for b in bars]
 return c,true_ranges(h,l,c)
class MomentumTests(unittest.TestCase):
 def test_axes_available_after_warmup(self):
  c,tr=fixture(); s=compute_momentum_axes(c,tr)[-1]; self.assertIsNotNone(s.trend_context);self.assertIsNotNone(s.path_efficiency)
 def test_efficiency_bounded(self):
  c,tr=fixture(); vals=[x.path_efficiency for x in compute_momentum_axes(c,tr) if x.path_efficiency is not None]; self.assertTrue(all(0<=x<=1 for x in vals))
 def test_noise_complements_efficiency(self):
  c,tr=fixture(); vals=[x for x in compute_momentum_axes(c,tr) if x.path_efficiency is not None]; self.assertTrue(all(abs(x.noise_ratio-(1-x.path_efficiency))<1e-12 for x in vals))
 def test_persistence_bounded(self):
  c,tr=fixture(); vals=[x.signed_persistence for x in compute_momentum_axes(c,tr) if x.signed_persistence is not None]; self.assertTrue(all(-1<=x<=1 for x in vals))
 def test_release_rank_bounded(self):
  c,tr=fixture(); vals=[x.release_rank for x in compute_momentum_axes(c,tr) if x.release_rank is not None]; self.assertTrue(all(0<=x<=1 for x in vals))
 def test_exhaustion_bounded(self):
  c,tr=fixture(); vals=[x.exhaustion_risk for x in compute_momentum_axes(c,tr) if x.exhaustion_risk is not None]; self.assertTrue(all(0<=x<=1 for x in vals))
 def test_prefix_invariance(self):
  c,tr=fixture(); assert_prefix_invariant(compute_momentum_axes,(c,tr),min_prefix=30)
 def test_future_perturbation_invariance(self):
  c,tr=fixture(); assert_future_perturbation_invariant(compute_momentum_axes,(c,tr),cutoff=100)
 def test_no_composite_score(self):
  c,tr=fixture(); s=compute_momentum_axes(c,tr)[-1]; self.assertFalse(hasattr(s,'score'));self.assertFalse(hasattr(s,'probability'));self.assertFalse(hasattr(s,'signal'))
 def test_invalid_length_fails(self):
  with self.assertRaises(ValueError): compute_momentum_axes([1,2],[1])

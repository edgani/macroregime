import unittest
from datetime import datetime,timezone
from pathlib import Path
from warroom_v3.data import load_canonical_csv
from warroom_v3.sensors.mqa import *
from warroom_v3.causality import assert_prefix_invariant, assert_future_perturbation_invariant
ROOT=Path(__file__).resolve().parents[1]

def fixture():
 bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc))
 return [b.high for b in bars],[b.low for b in bars],[b.close for b in bars]
class MQATests(unittest.TestCase):
 def test_true_range_gap_aware(self):
  tr=true_ranges([10,15],[8,14],[9,14.5]); self.assertEqual(tr[1],6)
 def test_atr_warmup(self):
  h,l,c=fixture(); a=wilder_atr(h,l,c,14); self.assertTrue(all(x is None for x in a[:13])); self.assertIsNotNone(a[13])
 def test_fixed_interval_ordered(self):
  h,l,c=fixture(); s=compute_mqa_benchmarks(h,l,c)[-1]; self.assertLess(s.fixed_lower,s.fixed_upper)
 def test_conformal_is_past_only_available_after_warmup(self):
  h,l,c=fixture(); s=compute_mqa_benchmarks(h,l,c)[-1]; self.assertIsNotNone(s.conformal_lower); self.assertIsNotNone(s.conformal_upper)
 def test_location_uses_prior_range(self):
  h,l,c=fixture(); s=compute_mqa_benchmarks(h,l,c)[-1]; self.assertIsNotNone(s.prior_range_location)
 def test_volatility_state_allowed(self):
  h,l,c=fixture(); allowed={'COMPRESSION','NORMAL','EXPANSION','UNAVAILABLE'}; self.assertTrue(all(s.volatility_state in allowed for s in compute_mqa_benchmarks(h,l,c)))
 def test_prefix_invariance(self):
  h,l,c=fixture(); assert_prefix_invariant(compute_mqa_benchmarks,(h,l,c),min_prefix=30)
 def test_future_perturbation_invariance(self):
  h,l,c=fixture(); assert_future_perturbation_invariant(compute_mqa_benchmarks,(h,l,c),cutoff=100)
 def test_invalid_lengths_fail(self):
  with self.assertRaises(ValueError): true_ranges([1],[1,2],[1])
 def test_no_execution_fields(self):
  h,l,c=fixture(); s=compute_mqa_benchmarks(h,l,c)[-1]; self.assertFalse(hasattr(s,'entry')); self.assertFalse(hasattr(s,'target')); self.assertFalse(hasattr(s,'probability'))

class MQAInputGeometryTests(unittest.TestCase):
 def test_close_above_high_rejected(self):
  with self.assertRaises(ValueError): true_ranges([10],[8],[11])
 def test_close_below_low_rejected(self):
  with self.assertRaises(ValueError): true_ranges([10],[8],[7])

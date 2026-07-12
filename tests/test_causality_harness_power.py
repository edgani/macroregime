import unittest
from dataclasses import dataclass
from warroom_v3.causality import assert_prefix_invariant,assert_future_perturbation_invariant

@dataclass(frozen=True)
class X: value:float

def causal(series):
 return [X(sum(series[:i+1])) for i in range(len(series))]
def leaky(series):
 total=sum(series)
 return [X(total) for _ in series]
class CausalityHarnessPowerTests(unittest.TestCase):
 def test_causal_formula_passes(self):
  x=[1.,2.,3.,4.,5.];assert_prefix_invariant(causal,(x,),min_prefix=1);assert_future_perturbation_invariant(causal,(x,),cutoff=2)
 def test_prefix_harness_catches_leakage(self):
  with self.assertRaises(AssertionError): assert_prefix_invariant(leaky,([1.,2.,3.,4.],),min_prefix=1)
 def test_future_harness_catches_leakage(self):
  with self.assertRaises(AssertionError): assert_future_perturbation_invariant(leaky,([1.,2.,3.,4.],),cutoff=1)

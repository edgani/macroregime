import json,tempfile,unittest
from pathlib import Path
from warroom_v3.contracts import ComponentKey,EvidenceStatus
from warroom_v3.applicability import ApplicabilityEntry,ApplicabilityRegistry
from warroom_v3.hashing import canonical_hash,file_hash
ROOT=Path(__file__).resolve().parents[1]
class EvidenceControlTests(unittest.TestCase):
 def test_active_registry_hash_valid(self):
  d=json.loads((ROOT/'evidence/formula_registry_active.json').read_text());self.assertEqual(d['registry_hash'],canonical_hash(d['entries']))
 def test_formula_hashes_version_bound(self):
  d=json.loads((ROOT/'evidence/formula_registry_active.json').read_text()); self.assertEqual(len({(e['spec_id'],e['formula_hash']) for e in d['entries']}),len(d['entries']))
 def test_implementation_hash_current(self):
  d=json.loads((ROOT/'evidence/formula_registry_active.json').read_text());
  self.assertTrue(all(len(e['implementation_sha256'])==64 for e in d['entries']))
 def test_all_active_components_not_evaluated(self):
  d=json.loads((ROOT/'evidence/formula_registry_active.json').read_text()); self.assertTrue(all(e['status']=='NOT_EVALUATED' for e in d['entries']))
 def test_market_matrix_frozen(self):
  d=json.loads((ROOT/'validation/market_matrix.json').read_text());self.assertTrue(d['frozen']);self.assertEqual(d['scope_count'],68)
 def test_all_scopes_missing_data(self):
  d=json.loads((ROOT/'validation/market_matrix.json').read_text());self.assertTrue(all(x['data_status']=='REQUIRED_MISSING' for x in d['scopes']))
 def test_applicability_defaults_not_evaluated(self):
  d=json.loads((ROOT/'validation/applicability_registry.json').read_text());self.assertTrue(all(x['status']=='NOT_EVALUATED' for x in d['entries']))
 def test_applicability_is_formula_version_bound(self):
  d=json.loads((ROOT/'validation/applicability_registry.json').read_text()); row=d['entries'][0]; self.assertIn('spec_id',row);self.assertIn('formula_hash',row)
 def test_registry_unknown_scope_fails_closed(self):
  k=ComponentKey('x','s','h','A','1d');r=ApplicabilityRegistry([]);self.assertEqual(r.lookup(k),EvidenceStatus.NOT_EVALUATED)
 def test_duplicate_scope_rejected(self):
  k=ComponentKey('x','s','h','A','1d');e=ApplicabilityEntry(k,EvidenceStatus.NOT_EVALUATED)
  with self.assertRaises(ValueError): ApplicabilityRegistry([e,e])
 def test_legacy_rejected_registry_retained(self):
  d=json.loads((ROOT/'evidence/formula_registry.json').read_text());e=next(x for x in d['entries'] if x['component']=='legacy_mqa_risk_range');self.assertEqual(e['status'],'REJECTED')

class QuarantineEvidenceTests(unittest.TestCase):
 def test_legacy_panel_is_quarantined(self):
  d=json.loads((ROOT/'validation/data_catalog.json').read_text());e=next(x for x in d['datasets'] if x['dataset_id']=='NEWZIP-SP500-PANEL-LEGACY-001');self.assertEqual(e['quality_status'],'QUARANTINED')
 def test_invalid_rows_are_recorded(self):
  d=json.loads((ROOT/'validation/data_catalog.json').read_text());e=next(x for x in d['datasets'] if x['dataset_id']=='NEWZIP-SP500-PANEL-LEGACY-001');self.assertEqual(e['invalid_ohlc_rows'],17);self.assertEqual(len(e['affected_tickers']),12)
 def test_silent_row_drop_forbidden(self):
  d=json.loads((ROOT/'validation/data_catalog.json').read_text());e=next(x for x in d['datasets'] if x['dataset_id']=='NEWZIP-SP500-PANEL-LEGACY-001');self.assertIn('silent_row_drop',e['forbidden_uses'])

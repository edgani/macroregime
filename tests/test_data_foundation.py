import json, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from warroom_v3.data import *
ROOT=Path(__file__).resolve().parents[1]
INGEST=datetime(2026,7,12,tzinfo=timezone.utc)

class DataFoundationTests(unittest.TestCase):
    def test_fixture_loads_and_quality_passes(self):
        bars,q=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        self.assertEqual(len(bars),180); self.assertTrue(q.accepted)
    def test_fixture_is_single_scope(self):
        bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        self.assertEqual({b.asset for b in bars},{'AAL'}); self.assertEqual({b.timeframe for b in bars},{'1d'})
    def test_timestamps_are_aware(self):
        bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        self.assertIsNotNone(bars[0].observed_at.utcoffset())
    def test_available_cannot_precede_observed(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): OHLCVBar('A','1d',t,t-timedelta(seconds=1),t,1,2,.5,1,0,'x')
    def test_ingested_cannot_precede_available(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): OHLCVBar('A','1d',t,t+timedelta(seconds=1),t,1,2,.5,1,0,'x')
    def test_impossible_ohlc_rejected(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): OHLCVBar('A','1d',t,t,t,2,1,.5,2,0,'x')
    def test_negative_volume_rejected(self):
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): OHLCVBar('A','1d',t,t,t,1,2,.5,1,-1,'x')
    def test_duplicate_timestamp_quality_rejected(self):
        bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        q=validate_bars([bars[0],bars[0]])
        self.assertFalse(q.accepted); self.assertIn('DUPLICATE_TIMESTAMPS',q.reason_codes)
    def test_unsorted_quality_rejected(self):
        bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        q=validate_bars([bars[1],bars[0]])
        self.assertIn('UNSORTED_TIMESTAMPS',q.reason_codes)
    def test_asof_violation_rejected(self):
        bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=INGEST)
        q=validate_bars(bars,as_of=bars[-2].available_at)
        self.assertIn('AS_OF_VIOLATION',q.reason_codes)
    def test_manifest_ceiling_enforced(self):
        with self.assertRaises(ValueError):
            DatasetManifest('x','a','b','c','d','A','1d',EvidenceTier.UNIT_FIXTURE,ClaimCeiling.PROSPECTIVE_ELIGIBLE,False,RevisionPolicy.LATEST_ONLY)
    def test_prospective_latest_only_rejected(self):
        with self.assertRaises(ValueError):
            DatasetManifest('x','a','b','c','d','A','1d',EvidenceTier.PROSPECTIVE,ClaimCeiling.PROSPECTIVE_ELIGIBLE,True,RevisionPolicy.LATEST_ONLY)
    def test_data_catalog_fixture_hash_matches(self):
        catalog=json.loads((ROOT/'validation/data_catalog.json').read_text())
        self.assertEqual(catalog['datasets'][0]['normalized_sha256'],__import__('hashlib').sha256((ROOT/'data/fixtures/aal_1d_engineering.csv').read_bytes()).hexdigest())

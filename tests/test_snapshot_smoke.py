from __future__ import annotations

import os
import unittest

from orchestration.build_snapshot import build_snapshot


class SnapshotSmokeTests(unittest.TestCase):
    def test_build_snapshot_offline_smoke(self) -> None:
        prev = os.environ.get('MRP_LIVE_FETCH')
        os.environ['MRP_LIVE_FETCH'] = '0'
        try:
            snap = build_snapshot(force_refresh=False, compact_mode=True, open_mode='smart_fresh')
        finally:
            if prev is None:
                os.environ.pop('MRP_LIVE_FETCH', None)
            else:
                os.environ['MRP_LIVE_FETCH'] = prev
        self.assertIsInstance(snap, dict)
        self.assertIn('meta', snap)
        self.assertIn('shared_core', snap)
        self.assertIn('us', snap)
        self.assertIn('crypto', snap)


if __name__ == '__main__':
    unittest.main()

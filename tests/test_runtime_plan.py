from __future__ import annotations

import unittest

from data.universe_loader import build_runtime_plan


class RuntimePlanTests(unittest.TestCase):
    def test_plan_returns_runtime_and_meta(self) -> None:
        runtime, meta = build_runtime_plan(compact_mode=True, shared_core=None)
        self.assertIn('us', runtime)
        self.assertIn('us', meta)
        self.assertGreater(len(runtime['us']), 0)
        self.assertEqual(meta['us']['runtime_count'], len(runtime['us']))


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import os
import unittest
import pandas as pd

from data.price_loader import load_display_quotes


class QuoteFallbackTests(unittest.TestCase):
    def test_quote_fallback_uses_last_close(self) -> None:
        prev = os.environ.get('MRP_LIVE_FETCH')
        os.environ['MRP_LIVE_FETCH'] = '0'
        try:
            series = {'SPY': pd.Series([100.0, 101.5], index=pd.to_datetime(['2026-04-08', '2026-04-09']))}
            out = load_display_quotes(['SPY'], base_series=series, force_refresh=False)
        finally:
            if prev is None:
                os.environ.pop('MRP_LIVE_FETCH', None)
            else:
                os.environ['MRP_LIVE_FETCH'] = prev
        q = out['quotes']['SPY']
        self.assertEqual(q['price_source'], 'historical_close')
        self.assertEqual(q['display_price'], 101.5)
        self.assertEqual(q['price_mode_badge'], 'Close')


if __name__ == '__main__':
    unittest.main()

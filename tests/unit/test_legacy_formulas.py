import pandas as pd

from eros.research.legacy import legacy_tilt_baseline, valuation_gap


def test_legacy_tilt_uses_floor_and_renormalizes() -> None:
    weights = legacy_tilt_baseline(0.9, 0.1)
    assert all(value >= 0.05 for value in weights.values())
    assert abs(sum(weights.values()) - 1.0) < 1e-12


def test_valuation_gap_obeys_filing_availability() -> None:
    filings = pd.DataFrame(
        {
            "filed_at": pd.to_datetime(
                ["2025-01-10", "2025-04-10", "2025-07-10", "2025-10-10", "2026-01-10"], utc=True
            ),
            "fundamental": [10.0, 11.0, 12.0, 13.0, 1000.0],
        }
    )
    result = valuation_gap(
        filings, pd.Timestamp("2025-12-31", tz="UTC"), 460.0, 10.0, 40.0, [8.0, 10.0, 12.0]
    )
    assert (result.ttm_fundamental, result.multiple, result.fair_value) == (46.0, 10.0, 46.0)

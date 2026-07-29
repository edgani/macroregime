"""Regression: attach_research_kernel deep-copies the desk, so per-market
enrichment (research_actions, shadow_candidates, current_quote_count,
permissions) must land on desk['markets'], not on a stale pre-copy dict.

Before the fix, every market row in the desk snapshot missed these fields and
the dashboard rendered 'current quotes 0' / 'shadow candidates 0' forever.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run import build_desk  # noqa: E402


def _minimal_data() -> dict:
    return {
        "markets": ["us"],
        "fred": {},
        "feeds": {"_status": {}},
        "quotes": {"markets": {"us": {}}},
        "public_sources": {"markets": {"us": {"state": "ROUTE_ONLY", "items": [], "valid_items": 0}}, "markets_with_real_snapshot": 0},
        "current_context": {"quotes": {"markets": {"us": {"AAA": {"price": 1.0}}}, "markets_with_quote": 1, "markets_with_fresh_quote": 1}},
        "universe_summary": {},
        "sources": {},
        "overall_source": "TEST",
    }


def test_market_rows_carry_enrichment_after_kernel_deepcopy():
    desk = build_desk(_minimal_data())
    row = desk["markets"]["us"]
    for field in ("research_actions", "shadow_candidates", "current_quote_count", "research_permission", "systematic_live_permission"):
        assert field in row, field
    assert row["current_quote_count"] == 1
    assert row["research_permission"] == "ACTIVE"


def test_mission_control_counts_present():
    desk = build_desk(_minimal_data())
    mc = desk["mission_control"]
    assert mc["fresh_quote_markets"] == 1
    assert "shadow_candidates" in mc

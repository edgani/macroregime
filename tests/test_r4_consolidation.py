"""R4 consolidation parity tests.

Parity by construction: every render function that powered one of the original
17 tabs must still be invoked exactly once in app.py. Plus integration boot:
11 tabs render, and section markers from every original tab are present.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# render calls that existed in the 17-tab app (R3 state, commit 8656461)
ORIGINAL_RENDER_CALLS = [
    "mission_control", "morning_brief", "briefing_embed", "command_center",
    "alpha", "cycle_rotation", "causal_chains", "us_stocks", "fair_value_cards",
    "crypto", "commodities", "fx", "ihsg", "flow", "bottleneck", "node_template",
    "market_state", "track_record", "validation_tab", "risk_health", "early_warning_tab",
]

FINAL_TABS = ["Mission Control", "Macro & Regime", "Alpha Center", "US Stocks",
              "Crypto", "Commodities", "FX", "IHSG", "Flow & Bottleneck",
              "Rotation & Chains", "Portfolio & Proof"]


def _app_source() -> str:
    return (ROOT / "app.py").read_text(encoding="utf-8")


def test_final_design_is_11_tabs():
    src = _app_source()
    for name in FINAL_TABS:
        assert f'"{name}"' in src, f"missing final tab: {name}"


def test_every_original_render_call_preserved_exactly_once():
    src = _app_source()
    for fn in ORIGINAL_RENDER_CALLS:
        calls = re.findall(rf"R\.{fn}\(", src)
        assert len(calls) == 1, f"{fn}: expected exactly 1 call, found {len(calls)}"


def test_no_render_call_duplicated():
    src = _app_source()
    calls = re.findall(r"R\.(\w+)\(", src)
    dupes = {c for c in calls if calls.count(c) > 1}
    assert not dupes, f"duplicated render calls (same panel in two tabs): {dupes}"


@pytest.mark.skipif(os.getenv("RUN_SLOW") != "1", reason="slow integration boot; RUN_SLOW=1 to enable")
def test_boot_11_tabs_all_original_sections_present():
    os.environ["WARROOM_OFFLINE"] = "1"
    os.environ["WARROOM_AUTO_SHADOW"] = "0"
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=280).run()
    assert not app.exception
    assert len(app.tabs) == 11
    md = " ".join(m.value for m in app.markdown).lower()
    # markers proving each original tab's content survived the merge
    markers = {
        "mission_control": "war room",
        "morning_brief": "morning brief",
        "command_center": "command center",
        "alpha": "alpha",
        "cycle_rotation": "rotation",
        "causal_chains": "chain",
        "us_stocks": "us stocks",
        "crypto": "crypto",
        "commodities": "commodit",
        "fx": "fx",
        "ihsg": "ihsg",
        "flow": "flow",
        "bottleneck": "bottleneck",
        "market_state": "market state",
        "track_record": "track record",
        "validation": "validation",
        "risk_health": "crash meter",
        "early_warning": "early warning",
        "quads": "structural",
        "carry": "carry",
    }
    missing = [k for k, m in markers.items() if m not in md]
    assert not missing, f"sections lost in consolidation: {missing}"

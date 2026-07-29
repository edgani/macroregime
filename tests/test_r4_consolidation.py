"""Single-page desk architecture tests (supersedes the R4 11-tab consolidation).

Architecture decision (operator request, 2026-07-29): app.py renders ONLY the
operational desk via desk_embed — one page, no stacked tab bars, no duplicate
UI.  The legacy warroom/render.py panels are no longer rendered in app.py;
their engines still feed the desk through warroom6_bridge in the data worker.
These tests lock that decision in:

  1. app.py has no st.tabs and renders the desk exactly once.
  2. The legacy render functions still EXIST in warroom/render.py (nothing
     deleted — they remain importable reference implementations).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEGACY_RENDER_FUNCTIONS = [
    "mission_control", "morning_brief", "briefing_embed", "command_center",
    "alpha", "cycle_rotation", "causal_chains", "us_stocks", "fair_value_cards",
    "crypto", "commodities", "fx", "ihsg", "flow", "bottleneck", "node_template",
    "market_state", "track_record", "validation_tab", "risk_health", "early_warning_tab",
]


def _app_source() -> str:
    return (ROOT / "app.py").read_text(encoding="utf-8")


def _render_source() -> str:
    return (ROOT / "warroom" / "render.py").read_text(encoding="utf-8")


def test_app_is_single_page_desk():
    src = _app_source()
    assert "st.tabs(" not in src, "app.py must not reintroduce stacked tab bars"
    assert "render_desk(" in src, "app.py must render the operational desk"
    calls = re.findall(r"render_desk\(", src)
    assert len(calls) == 1, f"render_desk must be invoked exactly once, found {len(calls)}"
    assert "R.mission_control(" not in src and "warroom" not in src.split("def main")[1], (
        "legacy WR6 render stack must not be invoked from app.main")


def test_legacy_render_functions_still_exist():
    src = _render_source()
    missing = [fn for fn in LEGACY_RENDER_FUNCTIONS if f"def {fn}(" not in src]
    assert not missing, f"legacy render functions deleted (must stay importable): {missing}"

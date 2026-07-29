"""warroom6_bridge tests: the desk must always get a market_intelligence
section — CURRENT with real War Room 6 outputs, or an honest UNAVAILABLE."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import warroom6_bridge  # noqa: E402


def test_bridge_returns_current_with_quad_and_crash_meter():
    mi = warroom6_bridge.build_market_intelligence()
    assert mi["state"] == "CURRENT"
    assert mi["proof_status"] == "RESEARCH_ONLY"
    assert mi["execution_eligible"] is False
    quad = mi["macro_quad"]
    assert quad and quad.get("quad")  # e.g. "Q2 Reflation"
    cm = mi["crash_meter"]
    assert cm is not None
    assert "value" in cm and "severity" in cm and "subcomponents" in cm
    assert cm.get("proof_status") == "RESEARCH_ONLY"
    assert cm.get("execution_eligible") is False
    # no synthetic subcomponents: every entry is either CURRENT with a value
    # or an honest NO_DATA
    for name, sub in cm["subcomponents"].items():
        assert sub["state"] in {"CURRENT", "NO_DATA"}, name
        if sub["state"] == "NO_DATA":
            assert sub["value"] is None


def test_bridge_failure_is_honest_unavailable(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("simulated compute failure")

    # patch the compute entrypoint itself (from-import caching makes a
    # sys.modules patch order-dependent)
    import warroom.compute

    monkeypatch.setattr(warroom.compute, "run", boom)
    mi = warroom6_bridge.build_market_intelligence()
    assert mi["state"] == "UNAVAILABLE"
    assert mi["macro_quad"] is None
    assert mi["crash_meter"] is None
    assert "error" in mi

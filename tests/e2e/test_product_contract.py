"""End-to-end product contract for the EROS v3 Streamlit application."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from eros.app.shell import MAIN_TABS, PRODUCT_NAME
from eros.app.state import load_dashboard_state

EXPECTED_TABS = (
    "Command Center",
    "Global Explorer",
    "Opportunity Engine",
    "Portfolio",
    "Research Lab",
)


def test_product_identity_and_exact_navigation_contract() -> None:
    assert PRODUCT_NAME == "EROS"
    assert MAIN_TABS == EXPECTED_TABS


def test_dashboard_fixture_preserves_uncertainty_and_execution_lock() -> None:
    state = load_dashboard_state()

    assert state.mode == "SYNTHETIC_DEMO"
    assert state.execution.permission == "LOCKED"
    assert state.execution.human_approval_required is True
    assert state.data_health.overall_status in {"PARTIAL", "STALE", "NO_DATA"}
    assert state.qualified_opportunities == []
    assert state.unknowns
    assert len(state.regime_dimensions) == 8


def test_streamlit_app_runs_with_five_decision_tabs() -> None:
    app_path = Path(__file__).parents[2] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    labels = tuple(tab.label for tab in app.tabs)
    assert all(labels.count(label) == 1 for label in EXPECTED_TABS)
    assert all(label in labels for label in EXPECTED_TABS)
    assert any("SYNTHETIC DEMO" in item.value for item in app.warning)
    assert any("NO QUALIFIED OPPORTUNITY" in item.value for item in app.warning)

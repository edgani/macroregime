"""End-to-end product contract for the EROS v3 Streamlit application."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from eros.app import shell
from eros.app.shell import MAIN_TABS, PRODUCT_NAME
from eros.app.state import build_public_data_state, load_dashboard_state
from eros.data.public_markets import MarketObservation, MarketPoint, MarketSnapshot

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


def test_streamlit_app_runs_with_five_decision_tabs(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    labels = tuple(tab.label for tab in app.tabs)
    assert all(labels.count(label) == 1 for label in EXPECTED_TABS)
    assert all(label in labels for label in EXPECTED_TABS)
    assert any("SYNTHETIC DEMO" in item.value for item in app.warning)
    assert any("NO QUALIFIED OPPORTUNITY" in item.value for item in app.warning)
    assert any("MECHANISM MAP" in item.value for item in app.markdown)


def test_public_market_snapshot_is_visible_in_command_center(monkeypatch) -> None:
    public_state = build_public_data_state(
        load_dashboard_state(),
        MarketSnapshot(
            fetched_at="2026-08-02T16:01:00Z",
            observations=[
                MarketObservation(
                    market_group="US",
                    instrument="S&P 500",
                    symbol="^GSPC",
                    value=7489.72,
                    currency="USD",
                    change_pct=0.8,
                    observed_at="2026-08-02T16:00:00Z",
                    fetched_at="2026-08-02T16:01:00Z",
                    provider="public-test",
                    status="LIVE",
                    history=[
                        MarketPoint(observed_at="2026-08-01T16:00:00Z", value=7400.0),
                        MarketPoint(observed_at="2026-08-02T16:00:00Z", value=7489.72),
                    ],
                )
            ],
        ),
    )
    monkeypatch.setattr(shell, "_load_runtime_state", lambda: public_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("LIVE CROSS-MARKET PULSE" in item.value for item in app.markdown)
    assert any("LIVE 5-DAY MARKET PATHS" in item.value for item in app.markdown)
    assert any("PUBLIC MARKET SNAPSHOT" in item.value for item in app.markdown)
    assert any("MARKET COVERAGE MAP" in item.value for item in app.markdown)
    assert any("GLOBAL COVERAGE OVERVIEW" in item.value for item in app.markdown)
    assert any("PUBLIC DATA" in item.value for item in app.warning)
    assert any("FROZEN SYNTHETIC RESEARCH FIXTURE" in item.value for item in app.warning)
    assert any("CAUSAL REGIME UNKNOWN" in item.value for item in app.warning)


def test_total_provider_outage_remains_visible_without_market_rows(monkeypatch) -> None:
    failed_state = build_public_data_state(
        load_dashboard_state(),
        MarketSnapshot(
            fetched_at="2026-08-02T16:01:00Z",
            failures={"Public providers": "all requests failed"},
        ),
    )
    monkeypatch.setattr(shell, "_load_runtime_state", lambda: failed_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("Provider failures isolated: Public providers" in item.value for item in app.warning)


def test_opportunity_tab_visualizes_admission_gates(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("ADMISSION GATE MAP" in item.value for item in app.markdown)


def test_research_tab_visualizes_evidence_status(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("RESEARCH EVIDENCE MAP" in item.value for item in app.markdown)

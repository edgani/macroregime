"""End-to-end product contract for the EROS v3 Streamlit application."""

from pathlib import Path

import pytest
from packet_factory import meters_snapshot, qualified_packet
from streamlit.testing.v1 import AppTest

from eros.app import command_center, shell
from eros.app.shell import MAIN_TABS, PRODUCT_NAME
from eros.app.state import ExecutionState, build_public_data_state, load_dashboard_state
from eros.data.public_markets import MarketObservation, MarketPoint, MarketSnapshot

EXPECTED_TABS = (
    "Command Center",
    "Global Explorer",
    "Opportunity Engine",
    "Portfolio",
    "Research Lab",
)


@pytest.fixture(autouse=True)
def _no_live_meter_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep AppTest runs deterministic; tests override when they need live meters."""

    monkeypatch.setattr(command_center, "_load_meters", lambda: (None, "SimulatedOutage: test"))


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
    monkeypatch.setattr(command_center, "_load_meters", lambda: (None, "SimulatedOutage: test"))
    app_path = Path(__file__).parents[2] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    labels = tuple(tab.label for tab in app.tabs)
    assert all(labels.count(label) == 1 for label in EXPECTED_TABS)
    assert all(label in labels for label in EXPECTED_TABS)
    assert any("SYNTHETIC DEMO" in item.value for item in app.warning)
    assert any("NO QUALIFIED OPPORTUNITY" in item.value for item in app.warning)
    assert any("MECHANISM MAP" in item.value for item in app.markdown)


def test_command_center_decision_first_contract_renders(monkeypatch) -> None:
    """The rebuilt Command Center must answer before it shows raw data."""

    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    monkeypatch.setattr(command_center, "_load_meters", lambda: (meters_snapshot(), None))
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    markdown = [item.value for item in app.markdown]
    assert any("HARI INI:" in item for item in markdown)
    assert any("TRIM EMAS" in item for item in markdown)
    assert any("CRASH GATE (BCM v3.2)" in item for item in markdown)
    assert any("ASSET METERS" in item for item in markdown)
    assert any("TILT ENGINE" in item for item in markdown)
    assert any("SKENARIO & SIKAP" in item for item in markdown)
    assert any("ACTION QUEUE" in item for item in markdown)
    assert any("FEAR-ENTRY" in item.label for item in app.metric)
    assert any("NO PROVEN SIGNAL" in str(item.value) for item in app.metric)
    assert any("BARBELL" in str(frame.value.to_dict()) for frame in app.dataframe)
    assert any("TRIM" in str(frame.value.to_dict()) for frame in app.dataframe)


def test_command_center_fails_closed_when_meter_engine_is_down(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    monkeypatch.setattr(command_center, "_load_meters", lambda: (None, "SimulatedOutage: test"))
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("TIDAK TERSEDIA" in item.value for item in app.markdown)
    assert any("NO_DATA" in item.value for item in app.error)


def test_opportunity_engine_positive_path_shows_complete_packet(monkeypatch) -> None:
    """A complete canonical packet must surface as qualified, never as zero."""

    qualified_state = load_dashboard_state().model_copy(
        update={
            "qualified_opportunities": [qualified_packet()],
            "execution": ExecutionState(
                permission="HUMAN_REVIEW",
                human_approval_required=True,
                reason="Qualified packet awaits approval.",
            ),
        }
    )
    monkeypatch.setattr(shell, "_load_runtime_state", lambda: qualified_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert all(
        "NO QUALIFIED OPPORTUNITY" not in item.value for item in app.warning
    )
    permission_frames = [
        frame.value
        for frame in app.dataframe
        if "Permission" in getattr(frame.value, "columns", [])
    ]
    assert any(
        (frame["Permission"] == "HUMAN_REVIEW").any() for frame in permission_frames
    )
    contract_frames = [
        frame.value
        for frame in app.dataframe
        if "Current value" in getattr(frame.value, "columns", [])
    ]
    assert any(
        (frame["Current value"] == "ENTER").any() for frame in contract_frames
    )


def test_approved_metadata_never_leaks_as_open_execution_when_policy_blocks(
    monkeypatch,
) -> None:
    blocked = load_dashboard_state().model_copy(
        update={
            "execution": ExecutionState(
                permission="APPROVED",
                human_approval_required=False,
                reason="Approved metadata reproduction.",
                approval_id="APPROVAL-E2E-1",
                approved_by="reviewer@example.test",
                approved_at="2026-08-03T06:00:00+00:00",
                approval_method="SIGNED_ATTESTATION",
                approval_evidence_checksum="a" * 64,
            )
        }
    )
    monkeypatch.setattr(shell, "_load_runtime_state", lambda: blocked)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("EXECUTION: LOCKED" in item.value for item in app.markdown)
    assert all("EXECUTION: APPROVED" not in item.value for item in app.markdown)
    assert any(
        "LOCKED — Anti-contamination policy blocks live-capital promotion." in item.value
        for item in app.error
    )


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
    assert any("HARI INI:" in item.value for item in app.markdown)
    assert any("DATA & BUKTI" in item.value for item in app.markdown)
    assert any("PUBLIC MARKET SNAPSHOT" in item.value for item in app.markdown)
    assert any("FEED ROOT CAUSE MATRIX" in item.value for item in app.markdown)
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
    assert any("SCENARIO HORIZON MATRIX" in item.value for item in app.markdown)
    assert any("QUALIFICATION FAILURE LEDGER" in item.value for item in app.markdown)
    assert any("TRIGGER / INVALIDATION / VALUATION CONTRACT" in item.value for item in app.markdown)


def test_portfolio_tab_exposes_fail_closed_input_and_rebalance_controls(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("PORTFOLIO INPUT CONTRACT" in item.value for item in app.markdown)
    assert any("SCENARIO HORIZON CONTROLS" in item.value for item in app.markdown)
    assert any("PORTFOLIO REBALANCE TRIPWIRES" in item.value for item in app.markdown)


def test_research_tab_visualizes_evidence_status(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("RESEARCH EVIDENCE MAP" in item.value for item in app.markdown)
    assert any(
        "ANTI-CONTAMINATION LIVE-CAPITAL GATES" in item.value
        for item in app.markdown
    )
    assert any("LIVE CAPITAL BLOCKED" in item.value for item in app.error)


def test_research_tab_labels_legacy_crashmeter_without_promoting_it_to_bcm(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("LEGACY CRASHMETER V3 SCORE TIMELINE" in item.value for item in app.markdown)
    assert any("LEGACY CRASHMETER V3 DRIVER ATTRIBUTION" in item.value for item in app.markdown)


def test_research_tab_renders_backtests_as_claim_exhibits(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert any("LEGACY BACKTEST CLAIM EXHIBITS" in item.value for item in app.markdown)
    assert any("ARITHMETIC DISCREPANCY" in item.value for item in app.error)


def test_research_tab_exposes_reproducible_crashmeter_proof_contract(monkeypatch) -> None:
    monkeypatch.setattr(shell, "_load_runtime_state", load_dashboard_state)
    app_path = Path(__file__).parents[2] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    headings = [item.value for item in app.markdown]
    assert any("LEGACY CRASHMETER THRESHOLD BANDS" in value for value in headings)
    assert any("DERIVED RISK WINDOWS" in value for value in headings)
    assert any("REPRODUCIBLE SPX DRAWDOWN OVERLAP" in value for value in headings)
    assert any("REPLICATION VERDICT" in value for value in headings)
    assert any("SOURCE CHECKSUMS" in value for value in headings)

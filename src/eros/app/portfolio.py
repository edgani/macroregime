"""Portfolio, scenario, and decision-journal interface."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import cast

import streamlit as st

from eros.app.components import section_header
from eros.app.opportunity_engine import _valid_qualified_packets
from eros.app.state import DashboardState
from eros.data.identifiers import validate_storage_identifier

HORIZONS = ("Now", "Week", "Month", "Quarter", "Year+")
REQUIRED_POSITION_FIELDS = {
    "instrument",
    "quantity",
    "cost_basis",
    "currency",
    "asset_class",
    "country",
    "account",
    "tax_treatment",
    "days_to_exit",
}
POSITION_ADMISSION_FIELDS = REQUIRED_POSITION_FIELDS | {
    "current_price",
    "market_value",
    "spread_bps",
    "estimated_slippage_bps",
    "tax_rate_pct",
    "broker_access",
    "settlement_days",
    "capacity_usd",
    "factor_exposures",
    "position_snapshot_id",
    "valuation_source_id",
    "liquidity_source_id",
    "risk_model_id",
    "decision_snapshot_id",
    "price_observed_at",
    "borrow_available",
    "borrow_rate_pct",
}
POSITION_TEXT_FIELDS = {
    "instrument",
    "currency",
    "asset_class",
    "country",
    "account",
    "tax_treatment",
}
VALIDATED_EVIDENCE = {"REPLICATED_OOS", "PROVEN_SCOPE_LIMITED"}


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return float(value)


def _positions_are_valid(positions: list[dict[str, object]]) -> bool:
    if not positions:
        return False
    for position in positions:
        if not isinstance(position, dict) or not set(position) >= REQUIRED_POSITION_FIELDS:
            return False
        if any(
            type(position.get(field)) is not str or not str(position[field]).strip()
            for field in POSITION_TEXT_FIELDS
        ):
            return False
        quantity = _finite_number(position.get("quantity"))
        cost_basis = _finite_number(position.get("cost_basis"))
        days_to_exit = _finite_number(position.get("days_to_exit"))
        if (
            quantity is None
            or quantity == 0
            or cost_basis is None
            or cost_basis < 0
            or days_to_exit is None
            or days_to_exit < 0
        ):
            return False
    return True


def _position_inputs_complete(positions: list[dict[str, object]]) -> bool:
    if not _positions_are_valid(positions):
        return False
    for position in positions:
        if not set(position) >= POSITION_ADMISSION_FIELDS:
            return False
        numeric_fields = {
            field: _finite_number(position.get(field))
            for field in (
                "quantity",
                "current_price",
                "market_value",
                "spread_bps",
                "estimated_slippage_bps",
                "tax_rate_pct",
                "capacity_usd",
                "borrow_rate_pct",
            )
        }
        if any(value is None for value in numeric_fields.values()):
            return False
        complete_numbers = cast(dict[str, float], numeric_fields)
        quantity = complete_numbers["quantity"]
        current_price = complete_numbers["current_price"]
        market_value = complete_numbers["market_value"]
        if (
            current_price <= 0
            or not math.isclose(market_value, quantity * current_price, rel_tol=1e-6)
            or complete_numbers["spread_bps"] < 0
            or complete_numbers["estimated_slippage_bps"] < 0
            or not 0 <= complete_numbers["tax_rate_pct"] <= 100
            or complete_numbers["capacity_usd"] < abs(market_value)
            or complete_numbers["borrow_rate_pct"] < 0
        ):
            return False
        if type(position.get("broker_access")) is not bool or not position["broker_access"]:
            return False
        settlement_days = position.get("settlement_days")
        if type(settlement_days) is not int or not 0 <= settlement_days <= 10:
            return False
        borrow_available = position.get("borrow_available")
        if type(borrow_available) is not bool or (quantity < 0 and not borrow_available):
            return False
        factors = position.get("factor_exposures")
        if not isinstance(factors, dict) or not factors:
            return False
        if any(
            type(name) is not str
            or not name.strip()
            or _finite_number(value) is None
            for name, value in factors.items()
        ):
            return False
        lineage_fields = (
            "position_snapshot_id",
            "valuation_source_id",
            "liquidity_source_id",
            "risk_model_id",
            "decision_snapshot_id",
        )
        if any(
            type(position.get(field)) is not str or not str(position[field]).strip()
            for field in (*lineage_fields, "price_observed_at")
        ):
            return False
        try:
            for field in lineage_fields:
                validate_storage_identifier(str(position[field]), field)
            observed_at = datetime.fromisoformat(
                str(position["price_observed_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            return False
        if (
            observed_at.tzinfo is None
            or observed_at.utcoffset() is None
            or observed_at.astimezone(UTC) > datetime.now(UTC)
        ):
            return False
    return True


def _scenario_text(value: object) -> str:
    if type(value) is str and value.strip():
        return value.strip()
    number = _finite_number(value)
    return f"{number:g}" if number is not None else "UNKNOWN"


def _scenarios_are_valid(
    positions: list[dict[str, object]], scenarios: Sequence[Mapping[str, object]]
) -> bool:
    if not scenarios or not _position_inputs_complete(positions):
        return False
    market_values = [_finite_number(position.get("market_value")) for position in positions]
    if any(value is None for value in market_values):
        return False
    complete_market_values = cast(list[float], market_values)
    gross_value = sum(abs(value) for value in complete_market_values)
    if gross_value <= 0:
        return False
    snapshot_ids = {str(position["decision_snapshot_id"]) for position in positions}
    if len(snapshot_ids) != 1:
        return False
    exposures: dict[str, float] = {}
    for position, market_value in zip(positions, complete_market_values, strict=True):
        weight = market_value / gross_value
        factors = position["factor_exposures"]
        assert isinstance(factors, dict)
        for factor, loading in factors.items():
            parsed_loading = _finite_number(loading)
            assert parsed_loading is not None
            exposures[str(factor)] = (
                exposures.get(str(factor), 0.0) + weight * parsed_loading
            )

    for scenario in scenarios:
        name = scenario.get("scenario")
        probability = _finite_number(scenario.get("probability"))
        impact = _finite_number(scenario.get("portfolio_impact_pct"))
        if type(name) is not str or not name.strip():
            return False
        if probability is None or not 0 <= probability <= 1 or impact is None:
            return False
        if scenario.get("evidence_status") not in VALIDATED_EVIDENCE:
            return False
        mechanism_id = scenario.get("mechanism_id")
        if type(mechanism_id) is not str or not mechanism_id.strip():
            return False
        if scenario.get("decision_snapshot_id") not in snapshot_ids:
            return False
        triggers = scenario.get("triggers")
        if not isinstance(triggers, list) or not triggers or any(
            type(trigger) is not str or not trigger.strip() for trigger in triggers
        ):
            return False
        shocks = scenario.get("factor_shocks")
        if not isinstance(shocks, dict) or not shocks:
            return False
        parsed_shocks: dict[str, float] = {}
        for factor, shock in shocks.items():
            parsed = _finite_number(shock)
            if type(factor) is not str or not factor.strip() or parsed is None:
                return False
            parsed_shocks[factor] = parsed
        computed_impact_pct = (
            sum(exposures.get(factor, 0.0) * shock for factor, shock in parsed_shocks.items())
            * 100
        )
        if not math.isclose(computed_impact_pct, impact, abs_tol=0.01):
            return False
    return True


def _scenario_rows(state: DashboardState) -> list[dict[str, str]]:
    ready = (
        _positions_are_valid(state.portfolio_positions)
        and bool(_valid_qualified_packets(state))
        and _scenarios_are_valid(state.portfolio_positions, state.scenarios)
        and state.execution_enabled
    )
    permission = "APPROVED FOR EXPLICIT REVIEW" if ready else "NO REBALANCE"
    return [
        {
            "Horizon": horizon,
            "Scenario": _scenario_text(scenario.get("scenario")),
            "Probability": _scenario_text(scenario.get("probability")),
            "Portfolio impact": _scenario_text(
                scenario.get("portfolio_impact_pct", scenario.get("portfolio_impact"))
            ),
            "Permission": permission,
        }
        for horizon in HORIZONS
        for scenario in state.scenarios
    ]


def _tripwire_rows(state: DashboardState) -> list[dict[str, str]]:
    """Derive rebalance blockers from holdings, evidence, and execution state."""

    holdings_loaded = _positions_are_valid(state.portfolio_positions)
    position_inputs_complete = _position_inputs_complete(state.portfolio_positions)
    qualified = bool(_valid_qualified_packets(state))
    scenario_validated = _scenarios_are_valid(state.portfolio_positions, state.scenarios)
    execution_open = state.execution_enabled
    approval_cleared = not state.execution.human_approval_required
    contamination_ready = state.contamination_policy_ready

    def status(passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    return [
        {
            "Tripwire": "Private holdings loaded",
            "Status": status(holdings_loaded),
            "Consequence": "Sizing enabled" if holdings_loaded else "No sizing",
        },
        {
            "Tripwire": "Qualified opportunity packet",
            "Status": status(qualified),
            "Consequence": "Candidate available" if qualified else "No suggested trade",
        },
        {
            "Tripwire": "Scenario mechanism validated",
            "Status": status(scenario_validated),
            "Consequence": (
                "Scenario impact available" if scenario_validated else "No hedge recommendation"
            ),
        },
        {
            "Tripwire": "Liquidity, tax, and access complete",
            "Status": status(position_inputs_complete),
            "Consequence": (
                "Position inputs complete" if position_inputs_complete else "No net-EV estimate"
            ),
        },
        {
            "Tripwire": "Execution permission",
            "Status": "APPROVED" if execution_open else "LOCKED",
            "Consequence": "Execution gate open" if execution_open else "Queue remains locked",
        },
        {
            "Tripwire": "Anti-contamination policy",
            "Status": status(contamination_ready),
            "Consequence": (
                "Research promotion controls enforced"
                if contamination_ready
                else "No live-capital promotion"
            ),
        },
        {
            "Tripwire": "Human approval",
            "Status": "NOT_REQUIRED" if approval_cleared else "REQUIRED",
            "Consequence": "Approval cleared" if approval_cleared else "No automatic execution",
        },
    ]


def render(state: DashboardState) -> None:
    section_header(
        "Capital under uncertainty",
        "Portfolio",
        "What do I own, what hidden risks overlap, and what is the value of waiting?",
    )
    positions_valid = _positions_are_valid(state.portfolio_positions)
    if positions_valid:
        st.success(f"{len(state.portfolio_positions)} private position records loaded in memory.")
    elif state.portfolio_positions:
        st.error("Private position records are malformed; portfolio permissions remain blocked.")
    else:
        st.info("No personal portfolio is loaded. Research data and portfolio data stay separated.")

    section_header(
        "Private holdings boundary",
        "PORTFOLIO INPUT CONTRACT",
        "These fields are required before exposure, liquidity, tax, or hedge outputs "
        "are permitted.",
    )
    position_status = "LOADED" if positions_valid else "MISSING"
    required_inputs = (
        ("Instrument identifier", position_status, "Needed for benchmark and instrument mapping"),
        ("Quantity and cost basis", position_status, "Needed for exposure and P&L"),
        ("Currency", position_status, "Needed for FX exposure"),
        ("Asset class and country", position_status, "Needed for factor decomposition"),
        ("Account and tax treatment", position_status, "Needed for net-EV and rebalance costs"),
        ("Liquidity / days-to-exit", position_status, "Needed for capacity and exit feasibility"),
    )
    st.dataframe(
        [
            {"Required input": name, "Status": status, "Why required": reason}
            for name, status, reason in required_inputs
        ],
        width="stretch",
        hide_index=True,
    )

    section_header(
        "Time-separated scenario controls",
        "SCENARIO HORIZON CONTROLS",
        "Scenario probability and portfolio impact remain UNKNOWN until evidence and "
        "holdings exist.",
    )
    st.dataframe(_scenario_rows(state), width="stretch", hide_index=True)

    section_header(
        "Capital action gates",
        "PORTFOLIO REBALANCE TRIPWIRES",
        "Every required condition must pass; a single failure keeps the queue locked.",
    )
    st.dataframe(_tripwire_rows(state), width="stretch", hide_index=True)

    sections = st.tabs(
        (
            "Current Portfolio",
            "Suggested Changes",
            "Exposure Decomposition",
            "Scenarios",
            "Liquidity",
            "Hedges",
            "Rebalance Queue",
            "Decision Journal",
        )
    )
    with sections[0]:
        if positions_valid:
            st.dataframe(state.portfolio_positions, width="stretch", hide_index=True)
        else:
            st.caption("EMPTY — connect a private portfolio store separately from research data.")
    with sections[1]:
        qualified_packets = _valid_qualified_packets(state)
        if qualified_packets:
            st.dataframe(qualified_packets, width="stretch", hide_index=True)
        else:
            st.warning("WAIT — no qualified opportunity packet.")
    with sections[2]:
        st.info(
            "UNKNOWN — growth, inflation, liquidity, credit, funding, country, currency, "
            "duration, commodity, policy, leverage, and counterparty overlap cannot be computed."
        )
    with sections[3]:
        st.dataframe(state.scenarios, width="stretch", hide_index=True)
    with sections[4]:
        st.info(
            "UNKNOWN — days-to-exit, spread, borrow, settlement, tax, and market access not loaded."
        )
    with sections[5]:
        st.info(
            "No hedge recommendation without position exposure and a validated scenario mechanism."
        )
    with sections[6]:
        ready_for_review = all(
            row["Status"] in {"PASS", "APPROVED", "NOT_REQUIRED"}
            for row in _tripwire_rows(state)
        )
        if ready_for_review:
            st.success("READY FOR EXPLICIT REVIEW — no automatic execution is performed here.")
        else:
            st.error("LOCKED — one or more rebalance tripwires have not passed.")
    with sections[7]:
        st.caption("No action or inaction has been recorded in this synthetic snapshot.")

    section_header(
        "Decision completeness", "Four Required Answers", "Absence of action needs a reason too"
    )
    rows = [
        {"Question": "Why buy?", "Current answer": "No evidence-qualified reason."},
        {"Question": "Why sell?", "Current answer": "No position context."},
        {"Question": "Why not buy?", "Current answer": "Data, proof, and net-EV gates fail."},
        {"Question": "Why not sell?", "Current answer": "No portfolio is loaded."},
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

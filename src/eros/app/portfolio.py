"""Portfolio, scenario, and decision-journal interface."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

import streamlit as st

from eros.app.components import section_header
from eros.app.opportunity_engine import _valid_qualified_packets
from eros.app.state import DashboardState

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
POSITION_TEXT_FIELDS = {
    "instrument",
    "currency",
    "asset_class",
    "country",
    "account",
    "tax_treatment",
}
PROBABILITY_PATTERN = re.compile(r"(?:0(?:\.\d+)?|1(?:\.0+)?)")
IMPACT_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?%")


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


def _scenario_text(value: object) -> str:
    return value.strip() if type(value) is str and value.strip() else "UNKNOWN"


def _scenarios_are_valid(scenarios: Sequence[Mapping[str, object]]) -> bool:
    if not scenarios:
        return False
    for scenario in scenarios:
        name = scenario.get("scenario")
        probability = scenario.get("probability")
        impact = scenario.get("portfolio_impact")
        if type(name) is not str or not name.strip():
            return False
        if (
            type(probability) is not str
            or PROBABILITY_PATTERN.fullmatch(probability.strip()) is None
        ):
            return False
        if type(impact) is not str or IMPACT_PATTERN.fullmatch(impact.strip()) is None:
            return False
        probability_number = float(probability)
        impact_number = float(impact.strip().removesuffix("%"))
        if not math.isfinite(probability_number) or not 0 <= probability_number <= 1:
            return False
        if not math.isfinite(impact_number):
            return False
    return True


def _scenario_rows(state: DashboardState) -> list[dict[str, str]]:
    ready = (
        _positions_are_valid(state.portfolio_positions)
        and bool(_valid_qualified_packets(state))
        and _scenarios_are_valid(state.scenarios)
        and state.execution.permission == "APPROVED"
        and not state.execution.human_approval_required
    )
    permission = "APPROVED FOR EXPLICIT REVIEW" if ready else "NO REBALANCE"
    return [
        {
            "Horizon": horizon,
            "Scenario": _scenario_text(scenario.get("scenario")),
            "Probability": _scenario_text(scenario.get("probability")),
            "Portfolio impact": _scenario_text(scenario.get("portfolio_impact")),
            "Permission": permission,
        }
        for horizon in HORIZONS
        for scenario in state.scenarios
    ]


def _tripwire_rows(state: DashboardState) -> list[dict[str, str]]:
    """Derive rebalance blockers from holdings, evidence, and execution state."""

    holdings_loaded = _positions_are_valid(state.portfolio_positions)
    position_inputs_complete = holdings_loaded
    qualified = bool(_valid_qualified_packets(state))
    scenario_validated = _scenarios_are_valid(state.scenarios)
    execution_open = state.execution.permission == "APPROVED"
    approval_cleared = not state.execution.human_approval_required

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
            "Status": state.execution.permission,
            "Consequence": "Execution gate open" if execution_open else "Queue remains locked",
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

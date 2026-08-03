"""Conservative opportunity interface."""

from __future__ import annotations

import math
import re

import pandas as pd
import streamlit as st

from eros.app.components import section_header
from eros.app.state import DashboardState

PACKET_FIELDS = (
    "Mechanism and competing thesis",
    "Four separate probabilities",
    "Expected win, loss, and tail",
    "Spread, slippage, funding, borrow, tax, FX, capacity",
    "Fundamental target and invalidation",
    "Crowding and capital formation",
    "Value of waiting and cash",
    "Decision snapshot and lineage",
)

HORIZONS = (
    ("Now", "0-5 days"),
    ("Week", "1-4 weeks"),
    ("Month", "1-3 months"),
    ("Quarter", "3-12 months"),
    ("Year+", ">12 months"),
)

NEXT_EVIDENCE_BY_GATE = {
    "Evidence completeness": "Admit funding, positioning, and catalyst source families.",
    "Mechanism validation": "Verify physical disruption and independent priced-in evidence.",
    "Legacy replication": "Reproduce the inherited claim on point-in-time source history.",
}

REQUIRED_PACKET_TEXT_FIELDS = {
    "holding_horizon",
    "entry_trigger",
    "invalidation",
    "valuation_basis",
    "alternative_action",
}
ALLOWED_QUALIFIED_DECISIONS = {"ENTER", "TRIM"}


def _valid_qualified_packets(state: DashboardState) -> list[dict[str, object]]:
    """Return only complete decision packets; malformed dicts remain inadmissible."""

    valid: list[dict[str, object]] = []
    for packet in state.qualified_opportunities:
        if not isinstance(packet, dict):
            continue
        decision = packet.get("decision")
        if (
            type(decision) is not str
            or decision.strip().upper() not in ALLOWED_QUALIFIED_DECISIONS
        ):
            continue
        if any(
            type(packet.get(field)) is not str or not str(packet[field]).strip()
            for field in REQUIRED_PACKET_TEXT_FIELDS
        ):
            continue
        sizing = packet.get("sizing")
        if type(sizing) is not str:
            continue
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)%\s*(?:NAV)?\s*", sizing)
        if match is None:
            continue
        sizing_value = float(match.group(1))
        if not math.isfinite(sizing_value) or not 0 < sizing_value <= 100:
            continue
        valid.append(packet)
    return valid


def _horizon_rows(state: DashboardState) -> list[dict[str, object]]:
    """Build horizon permissions from the actual candidate and execution state."""

    qualified_packets = _valid_qualified_packets(state)
    qualified_count = len(qualified_packets)
    permission: str
    if qualified_count:
        permission = state.execution.permission
        if permission == "APPROVED" and state.execution.human_approval_required:
            permission = "HUMAN_REVIEW"
        reason = (
            f"{qualified_count} qualified packet exists; execution state is "
            f"{state.execution.permission}."
        )
    else:
        permission = "WAIT / RESEARCH ONLY"
        reason = "No candidate passed evidence, mechanism, valuation, and execution gates."
    return [
        {
            "Horizon": name,
            "Window": window,
            "Qualified packets": qualified_count,
            "Permission": permission,
            "Reason": reason,
        }
        for name, window in HORIZONS
    ]


def _decision_contract_rows(state: DashboardState) -> list[dict[str, str]]:
    """Expose the first qualified packet without inventing absent fields."""

    qualified_packets = _valid_qualified_packets(state)
    packet = qualified_packets[0] if qualified_packets else {}
    qualified = bool(packet)

    def packet_value(field: str, empty_value: str) -> str:
        value = packet.get(field)
        if value is None or value == "":
            return "UNKNOWN — qualified packet field missing" if qualified else empty_value
        return str(value)

    return [
        {
            "Field": "Decision",
            "Current value": packet_value("decision", "WAIT / RESEARCH ONLY"),
        },
        {
            "Field": "Sizing",
            "Current value": packet_value("sizing", "0% EROS-generated allocation"),
        },
        {
            "Field": "Holding horizon",
            "Current value": packet_value("holding_horizon", "NONE — no qualified packet"),
        },
        {
            "Field": "Entry trigger",
            "Current value": packet_value(
                "entry_trigger",
                "Candidate passes evidence, mechanism, net-EV, and access gates",
            ),
        },
        {
            "Field": "Invalidation",
            "Current value": packet_value(
                "invalidation",
                "Any failed freshness, mechanism, valuation, or execution gate",
            ),
        },
        {
            "Field": "Valuation / target basis",
            "Current value": packet_value(
                "valuation_basis",
                "UNKNOWN — no point-in-time fundamental target admitted",
            ),
        },
        {
            "Field": "Alternative action",
            "Current value": packet_value(
                "alternative_action",
                "Preserve optionality and collect discriminating evidence",
            ),
        },
    ]


def render(state: DashboardState) -> None:
    section_header(
        "Thesis to trade",
        "Opportunity Engine",
        "Which opportunity has positive conservative EV after every friction?",
    )
    section_header(
        "Promotion evidence",
        "ADMISSION GATE MAP",
        "How many required gates pass, remain partial, or fail before capital is considered?",
    )
    gate_counts = (
        pd.DataFrame(state.acceptance_gates)
        .groupby("status", dropna=False)
        .size()
        .reset_index(name="Gates")
    )
    st.bar_chart(gate_counts, x="status", y="Gates", height=280)
    st.caption(
        "Gate counts come from the frozen research contract. They do not become live merely "
        "because public prices are available."
    )

    section_header(
        "Decision horizons",
        "SCENARIO HORIZON MATRIX",
        "Permission and required evidence stay separated across time horizons.",
    )
    st.dataframe(_horizon_rows(state), width="stretch", hide_index=True)

    section_header(
        "Candidate-level reasons",
        "QUALIFICATION FAILURE LEDGER",
        "Zero qualified opportunities is decomposed into the gate each candidate failed.",
    )
    failure_rows = [
        {
            **candidate,
            "decision": (
                "VETO" if candidate.get("failed_gate") == "Legacy replication" else "WAIT"
            ),
            "next_required_evidence": NEXT_EVIDENCE_BY_GATE.get(
                candidate.get("failed_gate", ""),
                "Resolve the documented failed gate with independent evidence.",
            ),
        }
        for candidate in state.rejected_opportunities
    ]
    if failure_rows:
        st.dataframe(failure_rows, width="stretch", hide_index=True)
    else:
        st.info("No rejected candidate record is available; candidate generation is not proven.")

    section_header(
        "Fail-closed decision packet",
        "TRIGGER / INVALIDATION / VALUATION CONTRACT",
        "The current WAIT decision remains explicit instead of filling missing fields "
        "with guesses.",
    )
    st.dataframe(_decision_contract_rows(state), width="stretch", hide_index=True)

    filters = st.tabs(
        (
            "Leaderboard",
            "Horizon",
            "Instrument Type",
            "Capital Formation",
            "Crowding",
            "Thesis Detail",
            "Rejected",
        )
    )
    with filters[0]:
        qualified_packets = _valid_qualified_packets(state)
        if not qualified_packets:
            st.warning("NO QUALIFIED OPPORTUNITY")
            st.caption("An empty result is valid when acceptance gates fail.")
        else:
            st.dataframe(qualified_packets, width="stretch", hide_index=True)
    with filters[1]:
        st.dataframe(_horizon_rows(state), width="stretch", hide_index=True)
    with filters[2]:
        st.info("Long / short / option / pair / hedge / wait mappings are evidence-gated.")
    with filters[3]:
        st.info("Capital-formation stage is UNKNOWN until independent flow families are admitted.")
    with filters[4]:
        st.info("Crowding and capacity cannot be inferred from attention or price action alone.")
    with filters[5]:
        rows = [{"Required field": field, "Status": "UNKNOWN"} for field in PACKET_FIELDS]
        st.dataframe(rows, width="stretch", hide_index=True)
    with filters[6]:
        st.dataframe(state.rejected_opportunities, width="stretch", hide_index=True)

    section_header("Acceptance", "Promotion Gate", "Why is capital still blocked?")
    st.error(state.execution.reason)

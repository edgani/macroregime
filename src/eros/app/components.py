"""Shared Streamlit components with explicit evidence and uncertainty semantics."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

STATUS_ICONS = {
    "PROVEN_SCOPE_LIMITED": "PROVEN / SCOPED",
    "REPLICATED_OOS": "REPLICATED OOS",
    "HISTORICALLY_SUPPORTED": "HISTORICAL",
    "PROSPECTIVE_PENDING": "PROSPECTIVE",
    "CANDIDATE": "CANDIDATE",
    "DATA_DEBT": "DATA DEBT",
    "BUSTED_AS_TESTED": "BUSTED",
    "UNKNOWN": "UNKNOWN",
    "LIVE": "LIVE",
    "PARTIAL": "PARTIAL",
    "STALE": "STALE",
    "NO_DATA": "NO DATA",
}


def evidence_badge(label: str) -> str:
    """Return a safe HTML badge for a controlled evidence label."""
    normalized = label if label in STATUS_ICONS else "UNKNOWN"
    css_class = normalized.lower().replace("_", "-")
    return f'<span class="evidence-badge {css_class}">{STATUS_ICONS[normalized]}</span>'


def section_header(kicker: str, title: str, question: str) -> None:
    st.markdown(
        f'<div class="section-heading"><span>{kicker}</span><h2>{title}</h2>'
        f"<p>{question}</p></div>",
        unsafe_allow_html=True,
    )


def status_card(title: str, value: str, detail: str, status: str = "UNKNOWN") -> None:
    badge = evidence_badge(status)
    st.markdown(
        f'<div class="status-card"><div class="card-top"><span>{title}</span>{badge}</div>'
        f"<strong>{value}</strong><p>{detail}</p></div>",
        unsafe_allow_html=True,
    )


def bullet_list(items: Iterable[str], empty: str = "No verified items.") -> None:
    values = list(items)
    if not values:
        st.caption(empty)
        return
    st.markdown(
        "".join(f'<div class="decision-row">{item}</div>' for item in values),
        unsafe_allow_html=True,
    )

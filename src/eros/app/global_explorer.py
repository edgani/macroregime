"""Registry-driven global explorer."""

from __future__ import annotations

import streamlit as st

from eros.app.components import section_header
from eros.app.state import DashboardState


def render(state: DashboardState) -> None:
    section_header(
        "Global ontology",
        "Global Explorer",
        "Move from mechanism to country, sector, supply chain, company, and instrument.",
    )
    sections = st.tabs(
        (
            "Countries",
            "Asset Classes",
            "Sectors",
            "Themes",
            "Physical Systems",
            "Supply Chains",
            "Mechanism Graph",
            "Search",
        )
    )

    with sections[0]:
        st.caption("Registry baseline. Scores remain horizon- and mechanism-specific.")
        st.dataframe(state.countries, width="stretch", hide_index=True)
    with sections[1]:
        st.caption("Global by default; no US-only inheritance.")
        st.dataframe(state.asset_classes, width="stretch", hide_index=True)
    with sections[2]:
        st.info("DATA DEBT — local sector economics and market mappings are not yet admitted.")
    with sections[3]:
        st.info(
            "Theme lifecycle: Discovery → Validation → Institutional Building → "
            "Acceleration → Consensus → Crowded → Distribution → Decay."
        )
    with sections[4]:
        st.info(
            "DATA DEBT — mines, grids, ports, routes, inventory, and capacity adapters pending."
        )
    with sections[5]:
        st.info(
            "Beneficiary ranking requires bottleneck severity, pricing power, expansion time, "
            "balance-sheet capacity, substitution risk, valuation, and investability."
        )
    with sections[6]:
        st.dataframe(state.mechanisms, width="stretch", hide_index=True)
        st.caption(
            "Solid edges require experiment lineage; this fixture contains no validated edges."
        )
    with sections[7]:
        query = st.text_input(
            "Search registry objects", placeholder="Country, mechanism, asset class…"
        )
        if query:
            needle = query.casefold()
            rows = state.countries + state.asset_classes + state.mechanisms
            matches = [row for row in rows if needle in " ".join(row.values()).casefold()]
            if matches:
                st.dataframe(matches, width="stretch", hide_index=True)
            else:
                st.info("No registry object matches this query.")

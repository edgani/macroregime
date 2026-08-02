"""Registry-driven global explorer."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from eros.app.shell import DemoState


def render(state: "DemoState") -> None:
    import streamlit as st
    st.title("Global Explorer")
    sections = st.tabs(("Countries", "Asset Classes", "Sectors", "Themes", "Physical Systems", "Supply Chains", "Mechanism Graph", "Search"))
    labels = ["Country registry covers developed, emerging, and frontier classifications.", "Equities, credit, FX, commodities, crypto, listed derivatives, and real assets.", "Local market mappings are required; US mappings are not transferred by default.", "Theme lifecycle remains evidence-gated.", "Mines, refineries, grids, ports, vessels, warehouses, fabs, data centers, and farms.", "Beneficiary ranking requires bottleneck, pricing power, capacity, balance-sheet, and valuation evidence.", "Edges are hypotheses until linked experiments validate their scope.", "Search returns registry objects only; no ticker-only thesis generation."]
    for section, label in zip(sections, labels, strict=True):
        with section:
            st.info(label)
            st.caption("DATA_DEBT — dossier fields remain unknown until verified adapters are admitted.")

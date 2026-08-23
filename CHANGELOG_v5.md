# v5 changes

- Reduced 11 tabs to 4 decision-oriented screens.
- Replaced table-heavy front end with KPI cards, heatmaps, shock bars, scenario evidence chart, crash-phase visualization, correlation matrices and scatter relationship explorer.
- Moved proof, lineage and system details behind one Research & Data tab.
- Integrated options context into the selected opportunity instead of a separate tab.
- Integrated forward distribution into opportunity inspection.
- Added macro↔asset forward-return correlation matrix and pair explorer.
- Added bundled long-run War Room macro panel as research-only relationship context.
- Fixed FRED cloud architecture: FRED API key → fredgraph → DBnomics; no synthetic fallback.
- If FRED is still unavailable, UI shows an explicit macro-feed error and setup guidance instead of empty tables masquerading as a valid state.

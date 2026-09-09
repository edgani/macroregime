# v3.2.3 Full UI/UX Audit

## Routed workspaces audited
1. CONTROL ROOM -> `_render_control_room`
2. OPPORTUNITIES -> `render_opportunity_tracker`
3. VERTICALS -> `_render_verticals`
4. MACRO & EVENTS -> `_render_macro_visual_room`
5. LEARNING / REPLAY -> `render_learning_lab`

## Removed from current product surface
- legacy Decision Desk route
- legacy v3.1 stylesheet in `app.py`
- legacy macro stylesheet and macro renderer UI
- visible `st.dataframe`
- visible `st.tabs`
- visible `st.metric`
- visible `st.sidebar`
- visible `st.expander`
- old/dead expression/detail renderer surfaces

## Unified visual components
- `mq-pagehead`
- `mq-kpirow`
- `mq-grid` / `mq-panel`
- `mq-vgrid` / `mq-vcard`
- `mq-table-wrap` / `mq-table`
- `mq-feed`
- `mq-note` / `mq-empty`
- unified native button/select/search/multiselect styling

## Regression guard
`tests/test_v323_unified_ui.py` fails the package if any retired surface token is reintroduced into the current app/UI modules or if any routed workspace loses its expected renderer.

## Verification
- Source package: 20 PASS / 0 NONPASS
- Fresh extracted package: 20 PASS / 0 NONPASS
- Browser-pixel smoke test: not claimed because Streamlit is unavailable in the build runtime and package installation is network-blocked.

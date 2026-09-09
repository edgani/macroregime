# UI verification

## Runtime status

- Streamlit server launch on `http://localhost:8501`: PASS.
- Streamlit reached the serving state without an import-time blank-page failure.
- True browser automation: BLOCKED. Installed Playwright could not create its Windows IPC pipe (`PermissionError: [WinError 5] Access is denied`). Direct headless Chromium also terminated before page creation with a Mojo platform-channel `Access is denied` failure.

## Static/structural checks

- Exactly five top-level routes remain: CONTROL ROOM, OPPORTUNITIES, VERTICALS, MACRO & EVENTS, LEARNING / REPLAY.
- Navigation uses native Streamlit buttons and session state.
- No Streamlit sidebar, tabs, dataframe, metric, or expander is exposed by the unified visible modules.
- Search and market scope now constrain both current radar data and tracked event choices.
- The selected opportunity includes immutable detection context, live price context, complete causal capture, component availability, and honest score gating.

## Screenshot evidence

No files were placed in `artifacts/ui_after/`. Screenshots cannot truthfully be captured without a functioning browser process. Route clicks, responsive widths, console errors, overlays, and spinner completion therefore remain **NOT VERIFIED**, and UI PASS is not claimed.

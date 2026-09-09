# UI verification

## Runtime status

- Streamlit server launch on `http://localhost:8501`: PASS.
- Streamlit reached the serving state without an import-time blank-page failure.
- True browser automation: BLOCKED. The final-verdict repair reproduced the failure through three independent launch paths: Python Playwright was denied Windows named-pipe creation (`WinError 5`), Node Playwright was denied spawning Chrome (`spawn EPERM`), and direct headless Chrome terminated at its Mojo platform-channel permission check (`Access denied`).

## Static/structural checks

- Exactly five top-level routes remain: CONTROL ROOM, OPPORTUNITIES, VERTICALS, MACRO & EVENTS, LEARNING / REPLAY.
- Navigation uses native Streamlit buttons and session state.
- No Streamlit sidebar, tabs, dataframe, metric, or expander is exposed by the unified visible modules.
- Search and market scope now constrain both current radar data and tracked event choices.
- The selected opportunity includes immutable detection context, live price context, complete causal capture, component availability, and honest score gating.

## Screenshot evidence

No files were placed in `artifacts/ui_after/`. Screenshots cannot truthfully be captured without a functioning browser process. Route clicks, responsive widths, console errors, overlays, and spinner completion therefore remain **NOT VERIFIED**, and UI PASS is not claimed.

`tests/browser_smoke.py` is a repeatable real-browser verifier for all five routes at 1440x1000 and 390x844. It now targets navigation buttons specifically, waits for Streamlit render/spinner completion, rejects empty renders and exception/status overlays, validates non-empty screenshots, and fails on browser console or page errors. `OIE_BROWSER_EXECUTABLE` optionally selects a runner-provided Chromium executable. It must be run in an environment that permits browser IPC.

## Independent second-pass evidence

- Streamlit server serving state on `http://localhost:8501`: PASS.
- Playwright retry: BLOCKED before Chromium launch by `PermissionError: [WinError 5] Access is denied` while creating the Windows IPC pipe.
- Streamlit runtime API initial render: zero application exceptions; all five route buttons plus search, market scope, refresh, and candidate selection were instantiated. This is runtime evidence, not browser/screenshot evidence.
- Scope consistency was repaired so search/market selection also constrains the Active KPI, lifecycle/alert/outcome fallback feeds, and theme clusters.

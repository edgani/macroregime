# War Room OS v7 — Deep Re-Audit of the Endless Refresh Screen

## Root cause

V6 executed `data_layer.load_all`, provider fallbacks, desk construction, quote attachment, consistency
checks, and Alpha adapter synchronously inside Streamlit's main request path. The `show_spinner` text
therefore remained on screen until every operation returned. A throttled or stalled provider could keep
the page from rendering indefinitely.

## Corrected architecture

- Streamlit never calls a provider or engine during page render.
- It reads `desk_v7.pkl` and renders the full dashboard immediately.
- If the desk does not yet exist, it renders the full fail-closed 14-tab state immediately.
- A detached supervisor runs the refresh worker.
- Fast seed timeout: 120 seconds.
- Full refresh timeout: 240 seconds.
- Provider timeout/retry defaults: 5 seconds / one retry; yfinance batch timeout 8 seconds.
- Refresh status and log are visible without blocking the dashboard.
- A stale supervisor/lock is automatically repaired.
- Timeout or provider failure preserves the last-known-good desk.
- Initial fast refresh uses a representative universe; the later full refresh expands coverage.
- Alpha Foundry launch is also detached from the Streamlit request.

## What this fixes

- No endless `Refreshing providers...` Streamlit spinner.
- No blank page while Yahoo, FRED, Binance, Stooq, IDX, or engines are slow.
- No global dashboard crash because a provider refresh timed out.
- No automatic loss of the last verified desk.
- No v6 desk/cache silently entering the v7 runtime.

## Honest limitation

A machine that has never completed a fetch and currently has no network cannot display real market
observations. It will still show the full interface and explicit initialization/timeout status. After one
successful seed, the last-known-good desk remains available during temporary outages.

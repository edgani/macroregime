# War Room OS v7 — Non-Blocking Refresh Fix

## Failure reproduced

The v6 Streamlit request path called the entire provider cascade and War Room engine synchronously
inside `@st.cache_data(show_spinner=...)`. A slow Yahoo/yfinance/FRED request therefore kept the page on
`Refreshing providers...` and prevented the existing dashboard from rendering.

## v7 contract

1. The Streamlit request path never calls `data_layer.load_all` or any market provider.
2. The latest verified desk is rendered immediately. If no desk exists, the complete 14-tab no-data
   state is rendered immediately.
3. Refresh runs in a detached supervisor/worker process.
4. Fast first-start refresh has a 120-second hard timeout; full refresh has a 240-second hard timeout.
5. Timeout/failure keeps the last-known-good desk active and writes an explicit status/log.
6. Fast start uses a representative universe; full refresh expands it later without blocking the UI.
7. Provider timeouts/retries are bounded and configurable.
8. Alpha Foundry also launches in the background and cannot freeze the dashboard.

## Honest boundary

A first run with no internet and no cache cannot display real market data. It will still render the full
interface and show that background initialization failed/timed out. After one successful fetch, the
last-known-good desk remains available through temporary provider outages.

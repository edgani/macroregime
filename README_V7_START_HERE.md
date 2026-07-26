# War Room OS v7 — Start Here

## The endless refresh bug is removed

`RUN_WARROOM.bat` now renders the dashboard immediately. Market providers and engines refresh in a
separate supervised process. A provider timeout can no longer hold the Streamlit page behind a spinner.

## First run

1. Extract the ZIP to a new folder.
2. Double-click `RUN_WARROOM.bat`.
3. The full interface appears immediately in an initializing/no-data state.
4. A fast background seed starts automatically.
5. The page polls every four seconds while the worker runs and switches to the verified desk when ready.

## Refresh controls

- **Fast refresh**: representative universe, 120-second hard timeout.
- **Full refresh**: configured universe, 240-second hard timeout.
- **RESET_REFRESH_STATE.bat**: clears a stale worker lock/status but preserves verified data caches.
- **CHECK_FEEDS.bat**: explicit provider diagnostic.

## Failure behavior

- Slow provider: background worker times out; UI stays visible.
- One ticker/market fails: other markets remain available.
- Current refresh fails after a prior success: last-known-good desk remains active.
- First run with no network and no cache: full UI remains visible with explicit no-data status.

PAPER and LIVE remain blocked until the separate proof gates pass.

# Start War Room OS v2.4 Stable

1. Double-click `RUN_STABLE_WARROOM.bat` (or `RUN_LIVE_WARROOM.bat`, which now calls the same stable launcher).
2. The Streamlit shell mounts one static dashboard iframe. It does not rerun or remount the iframe on each data refresh.
3. A single background worker writes complete snapshots atomically. The browser polls the static JSON and redraws only when the meaningful content hash changes.
4. Copy `.env.example` to `.env` and fill only the providers you are entitled to use.
5. Replace `WARROOM_SEC_USER_AGENT` with a descriptive application name and a real contact email before enabling SEC EDGAR.
6. Use `RESET_RUNTIME.bat` after upgrading from v2.3 so stale worker locks and old snapshots cannot be reused.

Status meanings are explicit: `LIVE`, `STALE`, `PARTIAL`, `NO_SIGNAL`, `ACTION_REQUIRED`, `NOT_ENTITLED`, `OFFLINE`, `NO_DATA`, and `ERROR`. Missing production data is never replaced with synthetic values.

The model layer is **research infrastructure**, not a proven autonomous alpha engine. Validation grades in `metric_grades.json` are conservative and supersede older historical reports in this folder.

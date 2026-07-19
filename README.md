# War Room OS — Stable Live Architecture v2.4

This build replaces the rerun/remount refresh path with a single static dashboard iframe, one leased background collector, atomic snapshot publication, stable content revisions, and explicit data-state semantics.

Run: `RUN_STABLE_WARROOM.bat`

Before first use:
- copy `.env.example` to `.env`;
- add only credentials you are entitled to use;
- replace `WARROOM_SEC_USER_AGENT` with a real application/contact identity;
- run `RESET_RUNTIME.bat` once when upgrading from v2.3.

Key documents:
- `START_HERE.md`
- `DEEP_REAUDIT_V24.md`
- `LIVE_DATA_ACTIVATION.md`
- `V24_STABILITY_TEST_REPORT.json`
- `metric_grades.json`

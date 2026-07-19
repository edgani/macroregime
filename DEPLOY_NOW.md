# Deploy War Room OS v2.6 — Hosted Worker Fix

This release fixes the permanent `INITIALIZING` state in v2.5.

1. Replace the deployed repository completely with the **contents** of this package.
2. Confirm these are at repository root:
   - `app.py`
   - `warroom_data_worker.py`
   - `runtime_store.py`
   - `dashboard.html`
   - `.streamlit/config.toml`
3. Keep the application entrypoint as `app.py`.
4. Clear the host build cache and redeploy. Do not overwrite only `app.py` on top of an older folder.
5. Do not set the entrypoint to `static/dashboard_live.html`.

## Expected startup

- The UI shell appears immediately.
- `SYNC BOOTING/COLLECTING_CORE` appears while the first price snapshot is built.
- On a healthy public-data connection, market panels should populate after the first polling cycles.
- If the first collector attempt fails or times out, the screen must leave `INITIALIZING` and show
  explicit `NO_DATA/DEGRADED` plus the collector error. It must not remain initializing forever.

## Diagnostics

The two files below now retain startup errors instead of discarding them:

- `runtime/worker_boot.log`
- `runtime/worker.log`

`runtime/worker_status.json` exposes `WORKER_FATAL`, `CORE_ERROR`, or `DEGRADED` when applicable.

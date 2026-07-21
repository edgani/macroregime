# Deploy War Room OS v3.3

Use a full clean replacement. Do not overlay v3.3 on an older deployment because stale
runtime snapshots, worker locks and static HTML can preserve prior logic or interface.

## Required root files

```text
app.py
warroom_data_worker.py
runtime_store.py
run.py
research_kernel.py
fx_pair_state.py
current_developments.py
official_source_radar.py
dashboard.html
data/current_developments.json
data/source_watchlist.json
static/dashboard_live.html
.streamlit/config.toml
requirements.txt
```

Use `app.py` as the Streamlit entrypoint and clear the hosting build cache.

## Secrets

Configure secrets in the hosting platform, never in the ZIP or git history. Relevant
variables are documented in `.env.example`, `DATA_CONNECTORS.md` and
`LIVE_DATA_ACTIVATION.md`.

No credential means the related source remains `ACTION_REQUIRED`, `NOT_CONFIGURED` or
`NOT_ENTITLED`. It must never be replaced with an invented event or direction.

## Official radar

The radar runs in a bounded background thread and does not block first paint. Configure:

```text
WARROOM_RADAR_REFRESH_SECONDS=3600
WARROOM_RADAR_INITIAL_DELAY_SECONDS=8
WARROOM_RADAR_HTTP_TIMEOUT=8
WARROOM_SEC_USER_AGENT="War Room OS your-email@example.com"
```

## Release verification

Run before deploy:

```bash
python validate_release_v33.py
```

Required result:

```text
status: PASS
operational_permission: READY_FOR_USER_REVIEW
capital_permission: CAPITAL_BLOCKED
```

Deployment readiness and predictive proof are deliberately separate.

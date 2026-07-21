# Deploy War Room OS v3.2

Use a full clean replacement. Do not overlay v3.2 on an older deployment because stale
runtime snapshots, worker locks and static HTML can keep the previous interface alive.

## Required root files

```text
app.py
warroom_data_worker.py
runtime_store.py
run.py
research_kernel.py
dashboard.html
static/dashboard_live.html
data/loader.py
.streamlit/config.toml
requirements.txt
```

Use `app.py` as the Streamlit entrypoint. Clear the hosting build cache before deploy.

## Secrets

Configure secrets in the hosting platform, never in the ZIP or git history. Relevant
variables are documented in `.env.example`, `DATA_CONNECTORS.md` and
`LIVE_DATA_ACTIVATION.md`.

No credential means the relevant source remains `ACTION_REQUIRED`, `NOT_CONFIGURED` or
`NOT_ENTITLED`; the system must not invent a substitute event.

## Release verification

Run before deploy:

```bash
python validate_release_v32.py
```

Required result:

```text
status: PASS
operational_permission: READY_FOR_USER_REVIEW
capital_permission: CAPITAL_BLOCKED
```

The last line is intentional. Deployment readiness and predictive proof are separate.

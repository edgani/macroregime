# Deploy War Room OS v2.5

1. Replace the deployed repository with the **contents** of `War_Room_OS_Deploy_Fix_v2_5`.
2. Confirm these items are at repository root:
   - `app.py`
   - `dashboard.html`
   - `.streamlit/config.toml`
   - `static/desk_snapshot.json`
3. Set the application entrypoint to `app.py`.
4. Clear the host build cache and redeploy. Do not reuse the v2.4 running container.
5. Do not configure the entrypoint as `static/dashboard_live.html`.

A successful initial render shows the War Room shell immediately. Until the background worker finishes,
its data status can say `INITIALIZING`; it must not show the literal text
`app/static/dashboard_live.html?...`.

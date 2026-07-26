# War Room OS v2.5 — Blank-screen deployment fix

## Root cause

The v2.4 entrypoint called `st.iframe("app/static/dashboard_live.html?..."`) without a leading slash.
In Streamlit 1.56+, that string is classified as raw HTML, so the URL itself appeared as tiny text.
Using `/app/static/dashboard_live.html` would still be incorrect because Streamlit intentionally
serves `.html` files from `static/` as `text/plain`.

## Fix

- `app.py` embeds `dashboard.html` as a local `Path` with `st.iframe`.
- Dashboard JSON requests resolve to Streamlit's supported `/app/static/*.json` endpoint.
- The resolver preserves an optional hosted `server.baseUrlPath`.
- A `components.html` fallback displays an explicit error instead of a silent blank screen.
- Server binding defaults to `0.0.0.0` for container deployment.
- Streamlit runtime is constrained to `>=1.56,<2`.

## Deployment

Deploy the repository root containing `app.py`, `dashboard.html`, `.streamlit/`, and `static/`.
The entrypoint must be `app.py`. Do not point the platform at `static/dashboard_live.html`.

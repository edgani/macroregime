# Start War Room OS v2.6

## Hosted deployment

Use the complete package and set `app.py` as the entrypoint. See `DEPLOY_NOW.md`.

## Windows local deployment

1. Copy `.env.example` to `.env`.
2. Add only API credentials and exchange entitlements you actually possess.
3. Run `RESET_RUNTIME.bat` once when upgrading from an older version.
4. Run `RUN_STABLE_WARROOM.bat`.

The first screen may briefly show `BOOTING` or `COLLECTING`, but it must either populate or switch to
an explicit degraded/error state. It must never remain permanently `INITIALIZING`.

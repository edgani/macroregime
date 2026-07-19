# Start War Room OS v2.7

## Hosted deployment

Replace the old repository completely and use `app.py` as the entrypoint. Follow `DEPLOY_NOW.md`.

v2.7 performs a bounded market bootstrap **before** rendering the dashboard. It then embeds that
committed snapshot into first paint and starts the embedded background collector. This removes the
v2.6 failure where the UI stayed on `INITIALIZING · R1` forever.

## Windows local deployment

1. Copy `.env.example` to `.env`.
2. Add only API credentials and entitlements you actually possess.
3. Run `RESET_RUNTIME.bat` when upgrading from an older release.
4. Run `RUN_STABLE_WARROOM.bat`.

## Expected states

- Market prices can be `LIVE`, `PARTIAL`, `STALE`, or explicit `NO_DATA`.
- A loaded market with no qualifying setup is `NO_SIGNAL`, not `NO_DATA`.
- Paid sources without entitlement are `NOT_ENTITLED`.
- SEC without a real user-agent is `ACTION_REQUIRED`.
- IHSG is cash `LONG_ONLY`; the system does not invent an IHSG derivatives feed.

No production path creates synthetic market data.

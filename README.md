# War Room OS — Hosted Live Architecture v2.6

The v2.6 deployment fixes the permanent `INITIALIZING` failure in v2.5 and hardens cold-start behavior.

Core architecture:

- one embedded dashboard document;
- one leased background collector process by default;
- embedded-thread fallback when detached processes cannot start;
- atomic JSON snapshots;
- a fast price-first initial plane;
- expanded macro, derivatives, institutional, and enrichment planes after the first usable snapshot;
- explicit `LIVE / PARTIAL / STALE / NO_DATA / DEGRADED / NOT_ENTITLED` semantics;
- no synthetic production fallback.

Deploy with `app.py` at repository root. Read `DEPLOY_NOW.md` and
`V26_INITIALIZING_ROOT_CAUSE.md` first.

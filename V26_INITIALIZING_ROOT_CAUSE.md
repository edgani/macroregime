# v2.6 Deep Re-audit — Permanent INITIALIZING Root Cause

## Exact failure in v2.5

`warroom_data_worker.py` called `read_status()` during worker startup but did not import it from
`runtime_store`.

That produced:

```text
NameError: name 'read_status' is not defined
```

The exception occurred immediately after the worker claimed its lease and before the previous
cleanup block. At the same time, `app.py` redirected worker stdout/stderr to `DEVNULL`. The visible
result was exactly the screenshot symptom:

- dashboard HTML loaded;
- static bootstrap snapshot remained revision 1;
- all nodes stayed `INITIALIZING` or `NO_DATA`;
- no useful error appeared in the hosting log or UI.

## Additional failure modes found

1. A first-core timeout/error did not publish any replacement snapshot, so `INITIALIZING` could
   remain forever even after the worker reported an error.
2. Startup only checked whether a PID briefly existed; it did not require a worker heartbeat/state.
3. Managed-host DNS/library hangs could hold network threads beyond nominal HTTP timeouts.
4. Hosted startup entered legacy yfinance cookie/crumb fallback after the bounded loader returned
   empty, reintroducing long cold-start stalls.
5. Event, slow, and expanded planes could start against a zero-observation degraded core.
6. A runtime path in `warroom/compute.py` referenced an undefined `_f` helper.

## v2.6 corrections

- Imported `read_status` and ran undefined-name static analysis over the package.
- Wrapped the complete collector lifecycle in fatal-error reporting and guaranteed lease cleanup.
- Preserved worker stderr/stdout in `runtime/worker_boot.log`.
- Defaulted hosted deployment to a worker process with an embedded-thread fallback.
- Added a fast price-first core; cached macro/liquidity may be used without blocking first paint.
- Added bounded direct Yahoo chart retrieval and disabled legacy yfinance fallback in hosted mode.
- Added a hard initial-core timeout.
- On first-core failure, publish a complete `NO_DATA / CORE_ERROR` snapshot instead of retaining
  bootstrap `INITIALIZING`.
- Added retry backoff so a failed core does not continuously respawn.
- Blocked derivatives/institutional/expanded planes until core observations actually exist.
- Fixed the undefined numeric conversion helper in `warroom/compute.py`.
- Added explicit `DEGRADED`, `CORE_ERROR`, `WORKER_FATAL`, and visible status-error messaging.

## What the validation does and does not prove

It proves collector startup, timeout recovery, snapshot publication, iframe rendering, and all-market
routing in controlled fixtures. It does not prove that a specific hosting provider permits every
public or paid data endpoint. Provider access, credentials, exchange licensing, rate limits, and
outbound-network policy still determine which datasets can become live.

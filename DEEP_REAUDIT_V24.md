# War Room OS v2.4 — Deep Re-Audit and Stability Fix

## Verdict

The flashing in v2.3 was real and architectural. It was not a cosmetic animation problem. The old path repeatedly reran Streamlit and remounted an iframe while data collectors and status objects were changing. That allowed a full-screen redraw even when only a heartbeat or provider state changed.

v2.4 replaces that path rather than adding another patch.

## Root causes found

1. **Iframe remount loop** — `st.fragment(run_every=...)` plus HTML component rendering could rebuild the complete embedded dashboard on refresh.
2. **Heartbeat-driven revisions** — generated timestamps, heartbeat fields, status ordering, and diagnostics could change a snapshot revision even when the visible market state was identical.
3. **Multiple worker race** — simultaneous Streamlit sessions or manual launches could write competing snapshots.
4. **Large multiprocessing result deadlock** — the parent joined a collector before draining a large queue payload.
5. **Collector timeout did not kill the child** — the child inherited the parent's graceful `SIGTERM` handler, so terminate could leave an orphan process.
6. **Non-atomic publication risk** — browser-visible data could be read while a write was incomplete.
7. **Synchronous first render** — the UI waited on network providers instead of reading an already-published snapshot.
8. **False `LIVE` market statuses** — provider-note text containing words such as “live” could label an empty market as live.
9. **`synthetic disabled` classification bug** — the word “synthetic” in a missing-data note could be misread as synthetic test data.
10. **Status conflation** — `NO_DATA`, `NO_SIGNAL`, `ACTION_REQUIRED`, `NOT_ENTITLED`, `OFFLINE`, and provider errors were mixed.
11. **Incorrect arrow activation** — inactive/no-data nodes were not blocked comprehensively from emitting edges.
12. **Derivative status loss** — commodity/FX/US derivatives could show generic `NO_DATA` instead of the actual provider state.
13. **Ticker routing defects** — crypto suffixes, `^JKSE`, and dollar-index aliases could be assigned to the wrong market.
14. **Validation overclaims** — old reports could still expose split-dependent momentum and an OHLCV US-sample proxy as if they were validated production/IHSG edges.

## Architecture after the fix

```text
Provider adapters / public sources / licensed bridges
                       ↓
        One leased background data worker
                       ↓
 Independent bounded collector processes
                       ↓
      Complete in-memory merged snapshot
                       ↓
 Atomic runtime JSON + atomic static mirror
                       ↓
 One persistent Streamlit iframe
                       ↓
 Browser polls JSON; redraw only on content-hash change
```

### Streamlit shell

- No `st.fragment` refresh loop.
- No `components.html` remount loop.
- Exactly one static iframe is mounted.
- Streamlit does not own live data collection.
- A compatibility `components.iframe` fallback exists only for older Streamlit versions.

### Browser update behavior

- Snapshot polling has an in-flight guard and bounded timeout.
- Heartbeats are read from a separate status JSON.
- A snapshot is accepted only if its stable content hash/revision changes.
- Every major section uses inner-HTML equality checks before replacement.
- Edge motion and tape marquee motion are disabled.
- Worker-status changes update only the small sync label and cannot redraw the graph.

### Worker and snapshot safety

- Atomic instance lock prevents two workers from owning the pipeline.
- Stale locks are reclaimed only after the recorded process is confirmed dead.
- Collector children use temporary pickle result files instead of queue transport.
- Child signal handlers are reset so a hard timeout actually terminates the process.
- Timed-out children are terminated, then killed if necessary, with temporary files removed.
- Runtime and static snapshots are published with `os.replace`.
- Last-good data is retained on transient provider failures, but `EMPTY`/`NO_SIGNAL` is not falsely treated as a live observation.
- Catastrophic market-coverage collapse is rejected rather than replacing a healthy snapshot with an empty one.

## Data-status contract

| State | Meaning |
|---|---|
| `LIVE` | Current usable observations exist. |
| `STALE` | Last-good observations exist but exceeded freshness policy. |
| `PARTIAL` | Core data exists; optional enrichment is incomplete. |
| `NO_SIGNAL` | Data exists but no event/setup passed the gate. |
| `ACTION_REQUIRED` | A public source needs local configuration, such as the SEC user agent. |
| `NOT_ENTITLED` | A paid/licensed provider credential or entitlement is absent. |
| `OFFLINE` | Network mode is disabled or the source is intentionally not contacted. |
| `NO_DATA` | The core provider returned no usable observation and no last-good cache exists. |
| `ERROR` | Adapter/provider failed and no valid fallback exists. |
| `CASH_ONLY` | The market is intentionally represented without a fabricated derivatives layer. |

An empty price dictionary can no longer be labeled `LIVE`. A note saying “synthetic disabled” can no longer be labeled `SYNTHETIC_TEST`.

## Arrow and lineage rules

- `NO_DATA`, `ERROR`, `NOT_CONFIGURED`, `NOT_ENTITLED`, `ACTION_REQUIRED`, `OFFLINE`, `INITIALIZING`, `EMPTY`, and `NO_SIGNAL` nodes do not emit active arrows.
- Mission Control candidates connect only to their actual market parent.
- No index/modulo routing remains.
- Commodity futures cannot be attached to IHSG.
- FX with no source does not generate an apparent rotation path.
- Derivatives are confirmation/context edges, not automatic causal direction.
- Structural supply-chain edges remain curated and visually separate from observed flow.

## Loading and responsiveness

- The page opens from a local static snapshot instead of waiting for providers.
- Fast core market/macro collection is separate from slow enrichments.
- Provider calls have hard process timeouts.
- Yahoo requests use batch loading, persistent cache, bounded retry, and correct FX aliases.
- Slow institutional/fundamental/physical-data providers cannot block the initial dashboard render.
- The browser does not redraw when only timestamps or heartbeat order changes.

## Derivatives and market tabs

- US options, crypto perps/options, commodity futures/COT, and FX futures/COT now preserve their actual availability state.
- `ACTION_REQUIRED`, `NOT_ENTITLED`, and `OFFLINE` are shown rather than collapsing everything into `NO_DATA`.
- IHSG remains `CASH_ONLY / LONG-ONLY`; no artificial short or derivatives context is generated.
- OI/COT/options records remain context. They do not identify the initiating side by themselves.

## Validation-status corrections

`metric_grades.json` now supersedes earlier historical reports:

- split-dependent momentum is `REJECTED`;
- panic-bottom evidence is descriptive/partial, not a contrarian BUY signal;
- crash and dollar-hub metrics are historical research context, not calibrated production probabilities;
- the reported bandarmetrics IC 0.173 is identified as a historical US OHLCV proxy, not a validated IHSG broker-flow edge;
- older reports are marked superseded.

## Tests completed

The deterministic v2.4 test suite passed:

- Streamlit AppTest: zero exceptions;
- exactly one iframe mounted;
- JavaScript syntax;
- Python package compile;
- stable content hash under timestamp/heartbeat/status-order changes;
- content hash changes on real visible-state changes;
- no false `LIVE` empty market;
- explicit synthetic remains test-only;
- FX/IDX/crypto/commodity/US symbol routing;
- 5 MB child-result transport;
- hard collector timeout and orphan-child check;
- arrow-lineage audit;
- options/Greeks/crypto-pressure parser fixtures;
- stale last-good failover;
- live-stack coverage contract.

See `V24_STABILITY_TEST_REPORT.json` for the machine-readable result.

## What cannot honestly be declared fixed without the user's credentials

The code path and status handling are tested, but these live responses cannot be authenticated from the packaging environment:

- Unusual Whales;
- Massive options/TRF;
- ORTEX/Intrinio;
- Nansen;
- Arkham;
- Databento/CME entitlements;
- licensed IDX broker/foreign/order-book feed;
- provider schema changes occurring after packaging.

Those sources should show `NOT_ENTITLED` or `ACTION_REQUIRED`, not a fake number and not a generic application error.

The packaging environment also blocks Chromium navigation to local/file pages by administrator policy. Therefore full browser E2E visual automation could not be executed here. The Streamlit component tree, JavaScript parser, single-iframe contract, static polling code, DOM-diff guards, and snapshot-revision behavior were tested independently.

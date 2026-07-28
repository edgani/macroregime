# War Room OS v2.7 — Deep Startup Re-audit

## User-visible failure reproduced

The v2.6 deployment could display the full UI while remaining permanently at:

```text
INITIALIZING · R1
US / IHSG / CRYPTO / COMMODITIES / FX = NO_DATA
SYNC COLLECTING
```

That state meant the browser was reading the bootstrap JSON while no collector had successfully
committed the first complete snapshot.

## Root causes

1. **Detached worker assumption** — the hosted app treated a recently updated PID/status as proof
   that the collector would complete. Managed hosts can terminate, sandbox, or starve detached
   processes.
2. **All-or-nothing first core** — the first commit waited for market prices, macro, liquidity,
   proxies, desk construction, and other context. One slow source held the whole UI at R1.
3. **Fork from an executor thread** — v2.6 could `fork` after requests/pandas/OpenBLAS had created
   locks. This is unsafe and can deadlock on Linux.
4. **Empty snapshot accepted as prior core** — a non-empty `markets` dictionary with zero actual
   observations could suppress a proper retry.
5. **Context starvation** — price-first mode read only cached macro/liquidity, but a new deployment
   had no cache and the full context refresh was deferred.
6. **Single-provider dependence** — a blocked Yahoo route could make an entire market appear empty.
7. **Late bootstrap race** — an overdue startup fetch could overwrite a newer snapshot unless its
   commit was separated from collection.

## Architectural correction

### Deterministic first paint

`app.py` now:

1. prepares static serving;
2. runs a small bounded market bootstrap in a daemon thread;
3. commits R2 itself only if collection completed within the startup budget;
4. otherwise commits an explicit R2 `NO_DATA/BOOTSTRAP_TIMEOUT` snapshot;
5. injects the committed snapshot into the iframe HTML;
6. mounts the iframe once;
7. starts the embedded collector for later planes.

The collection thread uses `commit=False`, so a late result cannot overwrite the timeout snapshot or
a newer worker revision.

### Staged data planes

- **Bootstrap plane:** small market anchors only.
- **Context plane:** FRED, Treasury/NY Fed liquidity, regime, and rotation.
- **Event plane:** options, derivatives, dark-pool/TRF, filings, and whale events.
- **Slow plane:** fundamentals, CFTC, EIA, on-chain, ownership, and licensed bridges.
- **Expanded plane:** larger market universes and heavier research calculations.

### Provider resilience

- US/IDX/FX/commodities: Yahoo query1 → Yahoo query2 → Stooq where supported.
- Crypto: Binance → OKX, followed by other configured paths outside bootstrap.
- FX aliases corrected to Yahoo canonical symbols.
- Price, FRED, liquidity, and snapshot caches use atomic unique temporary files.
- FRED cache falls back to pickle when parquet/pyarrow writing is unavailable.

### Truthful states

Zero observations can never be labeled `LIVE`. Missing optional credentials cannot blank core market
prices. `NO_SIGNAL`, `NOT_ENTITLED`, `ACTION_REQUIRED`, `NO_DATA`, and `ERROR` remain distinct.

## Validation completed

- Direct hosted bootstrap committed R2 with fixture observations for all five markets.
- Fresh `app.py` startup committed R2 before mounting its single iframe.
- Offline startup committed explicit R2 `NO_DATA` instead of remaining initializing.
- Background context loaded 19 macro observations and liquidity from real-shaped cached fixtures.
- Five-megabyte child payload completed without queue deadlock.
- Hard timeout terminated the child and left no orphan process.
- Python compile, dashboard JavaScript, arrow lineage, status hashing, and live-stack fixtures passed.

See:

- `V27_FULL_VALIDATION_REPORT.json`
- `V27_DEPLOYMENT_VALIDATION_REPORT.json`
- `V27_STARTUP_VALIDATION_REPORT.json`

## Boundary of the claim

This validates startup, data routing, state semantics, cache/failover, and offline provider parsers.
It does **not** prove that a paid API key has the correct entitlement, or that a specific hosting
account permits every public endpoint. Those conditions can only be verified with the user's actual
secrets and deployed network. When unavailable, the system must show the exact source failure rather
than synthetic data or permanent initialization.

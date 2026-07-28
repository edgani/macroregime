# War Room OS v3 — Sprint 1 Data Foundation Status

## Baseline

- Source of truth: `warroom_os_COMPLETE (6).zip`
- Source ZIP SHA-256: `92c670a92b3a594fb5775c45ce00c4fcaed4f9dcff14ac06e8c7acaf04886a9a`
- Legacy runtime is archive/research source only.
- No legacy evidence is inherited by active formulas.

## Validation result

- 86 discoverable unit tests passed.
- 9 fail-closed validation layers passed.
- Causality harness catches an intentionally leaky negative-control formula.
- Active formula registry, data catalog, market matrix, applicability registry, release manifest, not-armed prospective seal, and trial ledger are hash validated.

## Active research components

### MQA Benchmarks V1

Outputs only:

- Wilder ATR;
- fixed ATR interval;
- past-only conformal interval;
- volatility percentile/state;
- prior-range location.

Status: `NOT_EVALUATED`
Claim ceiling: `DESCRIPTIVE_ONLY`

No probability, entry, stop, target, or sizing is implemented.

### Momentum Axes V1

Separate outputs only:

- trend context;
- acceleration;
- release rank;
- signed persistence;
- path efficiency;
- noise ratio;
- exhaustion risk.

Status: `NOT_EVALUATED`
Claim ceiling: `DESCRIPTIVE_ONLY`

There is no weighted composite, alpha score, BUY/SELL, or probability.

### MTF Research V1

MTF fusion is descriptive and occurs before any future decision policy.
Conflict risk ceilings:

- structural/trend conflict: `0.00`;
- trend/tactical conflict: `0.25`;
- tactical/execution conflict: `0.50`;
- aligned: `1.00`.

These are ceilings for future policy research, not approved position sizes.

## Data foundation

Canonical OHLCV records require:

- `observed_at`;
- `available_at`;
- `ingested_at`;
- source record ID;
- revision ID;
- valid OHLC geometry;
- immutable normalized payload hash.

As-of violations, duplicate/unsorted timestamps, mixed scopes, impossible OHLC, and missing required volume fail closed.

## Bundled data quarantine finding

The bundled `sp500_panel.parquet` contains 17 invalid OHLC rows affecting 12 tickers:

`AOS, BBY, CHD, CHK, DHR, ES, IP, LNT, O, REGN, SPG, VRTX`

Observed defects include:

- NaN OHLC;
- high below body or below low;
- low above body;
- likely split/adjustment inconsistencies.

The whole legacy panel is cataloged as:

- evidence tier: `DEVELOPMENT`;
- quality status: `QUARANTINED`;
- point-in-time complete: `false`;
- silent row dropping: forbidden;
- hidden OOS, paper, live, and production calibration: forbidden.

A 180-bar AAL slice is retained only as an engineering fixture for contracts, causality, and smoke tests. It cannot support an edge claim.

## Development-only sensor diagnostic

After rejecting affected ticker scopes rather than silently dropping bad rows:

- 594,784 rows were processed;
- 10 ticker sensor scopes failed because high/low/close geometry was invalid;
- ATR readiness was about 98.97%;
- conformal readiness was about 97.30%;
- prior-range-location readiness was about 98.41%;
- Momentum axes were non-constant and finite on valid scopes.

This is an engineering/distribution diagnostic only. It does not use forward returns and establishes no predictive edge.

## Contract hardening

ResearchObservationTicket recursively rejects nested execution fields, including:

- probability;
- direction;
- entry/entry zone;
- stop/invalidation;
- target;
- sizing/risk budget;
- net EV;
- setup/action.

Actionable DecisionTicket requires all of:

- MQA evidence;
- Momentum evidence;
- MTF evidence;
- Decision Policy evidence;
- Portfolio Policy evidence;
- calibrated probability and interval;
- directionally consistent entry, invalidation, and targets;
- bounded positive risk budget;
- positive net EV.

`UNAVAILABLE` tickets cannot hide actionable fields.

## Market matrix

68 frozen scopes:

- 17 assets;
- 15m, 1h, 4h, and 1d.

Every scope currently remains:

- data: `REQUIRED_MISSING`;
- evidence: `NOT_EVALUATED`.

Applicability is bound to:

`component × spec_id × formula_hash × asset × timeframe`

Unknown scopes fail closed to `NOT_EVALUATED`.

## Prospective status

- Seal status: `NOT_ARMED`;
- prospective batches: `0`;
- paper/live eligible: `false`.

Reason codes:

- `NO_APPROVED_POINT_IN_TIME_PROVIDER`;
- `NO_PROSPECTIVE_DATASET`;
- `FORMULAS_NOT_EVALUATED`.

## Current scientific position

Engineering foundation: passed.
Predictive edge: not evaluated.
Paper decisions: blocked.
Live decisions: blocked.

The next valid build is provider governance and append-only prospective ingestion. It must not modify the frozen sensor formulas while collecting forward evidence.

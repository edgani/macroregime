# War Room OS Decision Intelligence v3.3.1 — Empty Board / Worker Hotfix

## User-reported failure fixed

1. The collector displayed `NameError: name 'disc' is not defined`, preventing fresh core snapshots.
2. BOARD mode only had explicit rows for market views, so Mission, Regime, Opportunities, Flow, Causal, Execution and Research often displayed `NO DECISION ROWS`.
3. Institutional/event views referenced missing JavaScript helpers and could throw page errors.

## Changes

- `run.py` now reads the discovery note from `alpha_meta`; the undefined `disc` reference is removed.
- Every one of the 19 subviews now has a deterministic workspace decision board. Explicit market/pair rows remain primary; non-market views use their queue or graph state rather than fake instrument claims.
- Added robust event description/state helpers.
- BOARD/MAP/EVIDENCE remain available. BOARD is the decision-first default.
- Runtime is shipped clean so an old error status is not carried into the new extraction.

## Validation

- Hotfix checks: 8/8 PASS.
- All 19 subviews: at least one decision row in BOARD mode.
- Browser page errors: 0.
- Fast core snapshot: no NameError.
- Full v3.3 operational regression: PASS, including Streamlit health, arrow lineage, live-stack fixtures and GCFIS synthetic correctness.

## Proof boundary

This proves the reported software regression is fixed. It does not prove predictive alpha. Capital permission remains BLOCKED until point-in-time WFA, lockbox and prospective evidence are satisfied.

## Installation

Do not overwrite the broken v3.3 folder. Extract this ZIP into a new folder, then run `CHECK_AND_RUN.bat`.

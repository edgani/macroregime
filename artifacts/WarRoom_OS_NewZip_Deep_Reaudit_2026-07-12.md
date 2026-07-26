# War Room OS Complete (6) — Deep Re-Audit from Zero

## Executive verdict

**STOP / REBUILD.** Treat this ZIP as a legacy source archive, not as a production trading system.

The new ZIP is not materially a new War Room. Of 216 files, 213 are byte-identical to the prior ZIP and only three files changed. The patch carries OHLCV into the entry engine and activates the legacy risk-range formula, but it does not repair decision ordering, evidence enforcement, canonical execution, testing, dashboard integrity, or data lineage.

The most important new result is adverse: on the bundled OOS window, the newly activated risk range is approximately **40.19% worse** than a calibrated ATR baseline by interval score, and it beats the local ATR baseline for **0 of 483 tickers**.

## Original product objective

The intended product remains:

1. MQA as a market context/range/state sensor.
2. Momentum as separate transition, release, persistence, exhaustion, and noise states.
3. MTF fusion before any decision.
4. A deterministic setup policy.
5. One canonical entry/invalidation/target/risk object.
6. Portfolio-level risk and capacity controls.
7. Version-bound evidence and point-in-time data.
8. A dashboard that only renders canonical tickets and never invents calculations.

The ZIP does not satisfy that objective yet.

## Archive and architecture

- ZIP SHA-256: `92c670a92b3a594fb5775c45ce00c4fcaed4f9dcff14ac06e8c7acaf04886a9a`
- 232 archive entries.
- 216 files.
- 168 Python modules.
- Static reachability from `app.py`: 61/168 modules.
- Static reachability from root `run.py`: 60/168 modules.
- Missing expected template: `dashboard.html`.
- Present template: `dashboard_live.html`.

The low reachability does not automatically mean unreachable modules are bad. It does mean file count cannot be used as evidence that those engines influence the actual output.

## Exact new additions

| `warroom_os/gcfis/engines/entry.py` | 5,441 | 9,061 | `c27f213f52662d96…` |
| `warroom_os/gcfis/orchestrator.py` | 17,222 | 17,330 | `84d38d49066434a0…` |
| `warroom_os/run.py` | 14,545 | 14,756 | `7be72e604375ef6d…` |

The patch adds useful mechanics:

- true-range ATR from OHLC;
- OHLC propagation into the entry engine;
- the concept of thesis-aware stop boundaries.

Those three ideas can be retained as research/engineering primitives. The concrete production integration must not be retained.

## P0 findings

### P0-01 — MTF still arrives after the decision

The root runner invokes `run_gcfis` with a fixed `{"chop": 1.0}` posterior. Only after that call does it compute the multi-timeframe posterior used for display. Therefore the displayed regime context and the regime used by the decision engine are different objects.

**Required fix:** MTF state must be computed, versioned, and passed to policy before any action, ranking, entry, or sizing is produced.

### P0-02 — Rejected MQA is now a production default

When OHLC data exists, `entry.py` calls `risk_range_hedgeye.compute_risk_range` automatically. There is no applicability registry, formula version check, asset/timeframe evidence gate, or claim ceiling.

The source file itself says the multipliers are in-sample and not OOS. A research candidate was therefore promoted simply because OHLC became available.

### P0-03 — The dashboard and decision use different execution maps

The orchestrator calls `run_entry` with OHLC, dealer context, and liquidity. The root runner later reconstructs setup data without those inputs. A demonstrated AAPL run produced:

- canonical/orchestrator branch: entry 159.54, stop 155.74, target 165.29, R/R 1.51;
- UI recomputation branch: entry 159.54, stop 154.50, target 174.03, R/R 2.87.

There must be one immutable execution object. UI code must never call an entry engine.

### P0-04 — EV is structurally broken

`TickerSignal` defines `entry_px`, but the orchestrator checks `sig.entry`. The exception is swallowed and EV becomes `None`. `final_desk.py` requires positive EV, so valid-looking upstream candidates can disappear or produce an empty desk for the wrong reason.

### P0-05 — Validation can falsely report completion

`validate_all.py` calls child validators without `check=True` and does not inspect their return codes. It prints `ALL VALIDATION LAYERS COMPLETE` regardless of child failure.

## P1 findings

### Test discovery and coverage

`pytest --collect-only` discovers zero tests in `gcfis/tests/test_all.py` because functions use the `t_*` naming convention. Running the file directly exercises old smoke checks, but the new OHLC entry branch is not passed OHLC and therefore is not tested.

### Key mismatch

The orchestrator exposes `liquidity_regime` and `cross_asset_regime`. Crash/surge engines read `liquidity` and `cross_asset`, falling back to neutral-like defaults. Perturbing the supplied keys therefore does not perturb the intended components.

### Metric grade theater

Metric grades are loaded for presentation, but there is no server-side serializer or policy gate that suppresses `REJECTED`, `FEED_GATED`, stale, or not-evaluated outputs. A badge is not enforcement.

### Dashboard boot failure

`app.py` reads `dashboard.html` both on the normal path and the exception path. That file is absent from the ZIP.

## Statistical re-audit

### Newly activated risk range

Bundled panel test:

- 483 tickers;
- 133,308 OOS ticker-date observations;
- 3 January 2017 through 6 February 2018;
- candidate coverage: 0.5030;
- calibrated ATR coverage: 0.6957;
- candidate interval score: 5.240431;
- ATR interval score: 3.738158;
- candidate/ATR ratio: 1.401875;
- tickers beating local ATR: 0/483;
- daily block-bootstrap candidate-minus-ATR CI95: [1.3039967748794135, 1.7394323071510887].

Lower interval score is better. The complete bootstrap interval is above zero, so the candidate's loss is not a small sample fluctuation in this bundle.

The fixed constituent panel is not point-in-time and is not a clean universal holdout. This result is sufficient to reject the formula as a production default; it is not sufficient to claim no possible range model can ever work.

### Factor momentum 126

The original IID t-test reports p=0.0117, but daily IC observations have lag-1 autocorrelation 0.9296. HAC p=0.4075, non-overlapping p=0.7077, and block-bootstrap p=0.4054. The `VALIDATED` label is unsupported.

### Crash pressure

Naive p=0.0095, but HAC p=0.2454, circular-shift p=0.4357, and block-bootstrap CI95=[-0.07133300082326137, 0.25329675018587283]. It may remain banded descriptive context, not a calibrated crash probability.

### Panic bottom

The 3-month historical difference is positive, but naive p=0.1004, circular-shift p=0.1970, non-overlapping p=0.1900, and Holm-adjusted p=0.3939. It remains research-only.

## Data constraints

### S&P panel

- 607,342 rows;
- 483 fixed constituents;
- 8 February 2013 through 7 February 2018;
- not a point-in-time membership universe.

### Macro panel

- 1881 through September 2023;
- oil missing 73.56%;
- gas missing 81.26%;
- DXY missing 63.05%;
- no vintage/release-time semantics.

### VIX

The VIX file extends to 1 July 2026, but its presence in the ZIP makes that history visible and therefore unsuitable as a future hidden holdout after this audit.

## Reset decisions

### Preserve

- true Wilder ATR helper as a tested primitive;
- OHLC plumbing concept;
- thesis-boundary concept;
- visual dashboard shell only;
- deterministic formulas that can pass parity and causality tests.

### Quarantine/archive

- legacy MQA/risk range;
- new entry integration;
- factor momentum `VALIDATED` claim;
- crash/panic numeric probabilities;
- asymmetric discovery and price fallback signals;
- all hardcoded dashboard claims.

### Rewrite

- pipeline ordering;
- contracts;
- point-in-time ingestion;
- MTF fusion;
- actionability gates;
- canonical ticket serialization;
- portfolio policy;
- validation runner;
- dashboard renderer.

## Reset Sprint 0 delivered

The clean repo does not import any legacy `gcfis`, `warroom`, or engine modules. It contains:

- `ResearchObservationTicket`, structurally unable to carry entry/target/stop/probability;
- strict `DecisionTicket` for PAPER/LIVE only;
- fail-closed evidence/data/MTF/calibration/EV/capacity/kill-switch gate;
- formula registry bound to actual source hashes;
- source manifest and migration map;
- deterministic release manifest;
- 18 discoverable tests.

Current production truth:

```text
Legacy ZIP: archive/research source
Research output: DESCRIPTIVE_ONLY
PAPER: blocked
LIVE: blocked
Default decision: UNAVAILABLE
```

## Correct next build order

1. Point-in-time OHLCV/macro contracts and immutable manifests.
2. Provider registry and quarantine behavior.
3. MQA benchmark sensor using ATR/conformal ranges only.
4. Momentum states as separate axes, no composite score.
5. MTF fusion before policy.
6. Single immutable execution map.
7. Version/asset/timeframe applicability registry.
8. Dependence-aware historical robustness.
9. Sealed prospective evidence collection.
10. Paper and limited live only after explicit promotion.

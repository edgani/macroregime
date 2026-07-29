# Paper Trading — Prospective Shadow Framework (Phase 7)

## Components

| Component | Path | Status |
|---|---|---|
| Append-only hash-chained ledger | `shadow_execution_ledger_v95.py` | VERIFIED (schema test) |
| Production recorder (V10.1 packets) | `shadow_runner_v101.py` | VERIFIED (dry-run + live; trial-gate enforced) |
| Outcome recorder (R9.1) | `shadow_outcome_recorder_v101.py` | VERIFIED (10 tests; live dry-run) |
| Global trial counter (R9.2) | `warroom/research/trial_counter.py` | VERIFIED (8 tests; both chains valid) |
| Contamination gates (R9.3) | `warroom/research/contamination_gates.py` | VERIFIED (7 tests; live verdict) |
| Daily cycle supervisor (R9.4) | `tools/worker_supervisor.py` | VERIFIED (5 tests; live cycle 4/4; scheduled 07:00) |
| Evaluation report generator | `tools/paper_trading/evaluate_shadow_ledger.py` | VERIFIED (carries contamination verdict) |
| Test suites | `tests/test_shadow_paper_trading.py`, `test_shadow_outcome_recorder.py`, `test_trial_counter.py`, `test_contamination_gates.py`, `test_worker_supervisor.py` | 33/33 PASS |

## Mandate field coverage (forecast record)

- append-only ledger: hash-chained (`previous_hash` + `record_hash` per row, verified on every append)
- decision-time snapshot: `data_snapshot_hash` (sha256 of current_context + generation marker)
- source and revision metadata: `source_snapshot_hash` on fills, `outcome_source_hash` on outcomes
- frozen config/model/module version: `model_hash` (V101_ACTION_POLICY.json), `code_snapshot_hash` (action_engine_v101.py), `global_trial_ledger_hash`, `projection_file_hash`
- Git commit: `git_commit` (added Phase 7; bound at record time via `git rev-parse HEAD`)
- asset/ticker, direction, entry (`reference_price`), target (`target_price`, added Phase 7),
  invalidation, horizon, confidence (`probability`), expected return,
  lower-confidence-bound return (`lower_confidence_bound_return`, added Phase 7),
  expected downside (`expected_shortfall`), opportunity cost (`opportunity_cost_estimate`, added Phase 7)
- outcome: realized_return, MAE (`max_adverse_excursion`), MFE (`max_favorable_excursion`),
  `exit_reason`, `later_revision_impact`

## Enforcement properties (tested)

- Anti-backfill / anti-future: timestamps must be within 300s of record time.
- Chronology: decision >= generated; outcome_start >= decision; outcome_end > outcome_start.
- NO_TRADE forecasts cannot create order intents; side must match direction.
- One order intent per forecast, one fill per order, one outcome per forecast.
- Outcomes cannot be recorded before maturity (`horizon_end >= outcome_end` and reached).
- Tamper-evident: any edit breaks `record_hash`/`previous_hash` verification.
- Every record carries `capital_permission: BLOCKED` and `evidence_class: PROSPECTIVE_SHADOW_ONLY`.
- Recorder is idempotent per ticker per day (no duplicate forecasts).

## Verification results (2026-07-28)

1. Schema test: `tests/test_shadow_paper_trading.py` — 10/10 PASS.
2. Dry-run (fixture snapshot): 1 forecast + order + fill created, ledger verifies, second run
   correctly idempotent. Covered by `test_shadow_runner_dry_run`.
3. Historical replay infrastructure test: 3 synthetic forecasts matured through outcome;
   evaluation reproduces exact statistics (hit rate 2/3, MAE/MFE joins). PASS.
4. Current prospective snapshot: **NOT RECORDED** — `runtime/desk_snapshot.json` is the
   INITIALIZING placeholder (no live collectors have run; no alpha_center.shadow_candidates).
   `shadow_runner_v101.py` live run returned `NO_SNAPSHOT`, ledger rows 0, verification valid.
   Honest blocker: requires a live data-worker cycle (network).
5. Evaluation report: on the empty/missing ledger the generator returns
   `evidence_status=PROSPECTIVE_EVIDENCE_PENDING`, capital BLOCKED — no profitability claim
   is possible until >=30 matured prospective observations exist.

## Verification results (2026-07-29, R9)

1. First live cycle committed (R9.0): 12 FORECAST + 12 ORDER_INTENT + 12 SHADOW_FILL,
   hash-chain verify valid, zero errors. First outcomes mature ~2027-01-25 (180D horizon, per V10.1 policy).
2. Outcome recorder (R9.1): 10/10 tests; live dry-run reports 12 pending unmatured, 0 created.
3. Trial counter (R9.2): both registry chains verify (full hash recompute);
   `V101_FIXED_ACTION_POLICY` registered prospectively (entry 6); shadow_runner refuses
   unregistered trials (fail-closed, zero rows written).
4. Contamination verdict (R9.3, live): shadow_pass=True, capital_pass=False; blocking capital
   gates are custodian / blind IDs / low-contamination holdout / post-cutoff holdout (the
   last passes automatically once outcomes mature).
5. Daily automation (R9.4): supervisor cycle 4/4 stages ok; Windows task `WarRoomDailyCycle`
   installed, daily 07:00 local, next run verified 2026-07-30.

## Rules

- Never real money. Never sign or broadcast a transaction. The framework has no broker path.
- Records are append-only; retroactive edits fail verification by construction.
- Prospective profitability remains PROSPECTIVE_EVIDENCE_PENDING until sufficient future
  observations accumulate (evaluator refuses claims below 30 matured outcomes).

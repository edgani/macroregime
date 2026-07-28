# Paper Trading — Prospective Shadow Framework (Phase 7)

## Components

| Component | Path | Status |
|---|---|---|
| Append-only hash-chained ledger | `shadow_execution_ledger_v95.py` | VERIFIED (schema test) |
| Production recorder (V10.1 packets) | `shadow_runner_v101.py` | VERIFIED (dry-run) |
| Evaluation report generator | `tools/paper_trading/evaluate_shadow_ledger.py` | VERIFIED |
| Test suite (10 tests) | `tests/test_shadow_paper_trading.py` | 10/10 PASS |

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

## Rules

- Never real money. Never sign or broadcast a transaction. The framework has no broker path.
- Records are append-only; retroactive edits fail verification by construction.
- Prospective profitability remains PROSPECTIVE_EVIDENCE_PENDING until sufficient future
  observations accumulate (evaluator refuses claims below 30 matured outcomes).

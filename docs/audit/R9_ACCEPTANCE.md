# R9 Acceptance — Prospective Accumulation Infrastructure (2026-07-29)

Scope: make the War Room accumulate prospective evidence automatically and
close the gaps identified against the WriteVerso LLM-contamination article
("LLMs that remember too much", Verso, Apr 2026) and the V84 revocation findings.

## Commits

| Commit | Scope | Evidence |
|---|---|---|
| 3919f10 | R9.0 first live prospective cycle | runtime/v101_current/* live (258 quotes, CFTC positioning, 36 fundamentals); 12 FORECAST + 12 ORDER + 12 FILL in runtime/v101_shadow/shadow_ledger.jsonl; verify valid |
| a2cd721 | R9.1 outcome recorder | shadow_outcome_recorder_v101.py; 10 tests; live dry-run 12 pending unmatured |
| 14de6aa | R9.2 global trial counter | warroom/research/trial_counter.py; V101_FIXED_ACTION_POLICY registered (registry entry 6); 8 tests |
| 576d942 | R9.3 contamination gates as code | warroom/research/contamination_gates.py + config/contamination_policy.json; 7 tests; live verdict shadow_pass=True capital_pass=False |
| 3768d90 | R9.4 daily supervisor + schedule | tools/worker_supervisor.py; live cycle 4/4 stages ok; WarRoomDailyCycle task verified (next 2026-07-30 07:00); 5 tests |

## Verified facts (reproduced, not claimed)

- pytest tests/: 230 passed, 2 skipped (was 200 at R9.0 start).
- Live collector blocker CLEARED: network-dependent collectors ran successfully
  (Yahoo chart API, Binance, CoinGecko, Coin Metrics, CFTC, FRED path).
- Operational finding: fast cycles skip fundamentals; the equity value bridge
  requires shares outstanding, so prospective cycles must run --once --full.
  Documented in the supervisor (it always runs full).
- Intermittent worker crash (EXIT=139, native lib on Windows) observed once in
  three cycles; mitigated by supervisor single-retry; root cause not yet
  isolated (tracked below).
- Shadow ledger: 36 rows, hash-chain verify valid, zero errors.
  capital_permission=BLOCKED on every record; evidence_class=PROSPECTIVE_SHADOW_ONLY.
- Contamination verdict (live): shadow_pass=True, capital_pass=False.
  Blocking capital gates: independent_data_custodian_used,
  model_blind_signal_ids_used, low_contamination_asset_holdout,
  post_model_cutoff_holdout (passes automatically once outcomes mature),
  named_factor_semantics_visible_to_llm (honest true).

## Article gap closure status

| Article requirement | Status after R9 |
|---|---|
| Prospective trial counter, append-only, counted from day one | DONE going forward (trial_counter + fail-closed gate in shadow_runner); historical search honestly unrecoverable (V84 note stands) |
| Immutable ledger, tamper-evident | DONE (hash chains, full recompute verification) |
| Purged walk-forward + embargo + lockbox | PRE-EXISTING (warroom/research/walkforward.py) |
| PBO / DSR vs true trial count | PARTIAL: local implementations exist (V84); DSR wired to global count is future work (R10 candidate) |
| Prospective outcomes primary | DONE (ledger + recorder; first outcomes mature ~2027-01-25) |
| LLM out of truth-bearing computation | DONE for V10.1 path (deterministic engine, attested, gate-enforced) |
| Schema isolation / clean model for text | NOT APPLICABLE yet (no LLM in signal path); required design constraint if an LLM is ever added (R10 candidate) |
| Human gate before capital | PRE-EXISTING + re-asserted (capital BLOCKED everywhere; no broker path) |

## What is NOT done (honest)

- No matured outcomes exist. First maturity ~2027-01-25 (180D horizon, per V10.1 policy).
- >=30 matured observations required before the evaluator permits even a
  forming-sample label; capital evaluation requires the capital tier of the
  contamination verdict plus a pre-registered evaluation window.
- Custodian / blind IDs / low-contamination holdout are NOT built. They are
  capital-tier blockers, correctly failing.
- Worker segfault root cause not isolated; supervisor retry is a mitigation,
  not a fix.
- Yahoo rate limits (HTTP 429) possible; collectors degrade honestly.

## Capital status

BLOCKED. Unchanged. The only change is that prospective evidence is now
accumulating on a schedule instead of being absent.

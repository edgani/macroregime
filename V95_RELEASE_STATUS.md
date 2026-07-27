# War Room OS V9.5 — Proof Firewall & Shadow Trading Runtime

## Final status

V9.5 is **5/5 operationally ready for prospective shadow trading** across US stocks, IHSG, commodities, FX and crypto.

It is **not 5/5 live-capital ready**. Current live-capital status remains **0/5 and BLOCKED** because no exact market lane has supplied a complete, genuine proof record containing admitted point-in-time history, sealed outcomes, at least 200 real closed trades over at least 24 months and four regimes, calibrated projections, actual costs/capacity, drawdown limits and a trusted signed approval.

This distinction is enforced in code; it is not merely a warning label.

## What V9.5 repaired

- Replaced mixed V9.0/V9.1/V9.4 runtime identity with one V9.5 release identity.
- Replaced the legacy dashboard promotion path with a V9.5 proof-run registry.
- Bound predictor manifest, forecast seal, projections, outcomes, live trades and equity ledger by actual SHA-256 hashes.
- Recomputed projection, profit-factor and drawdown metrics instead of trusting numbers typed into a receipt.
- Added strict live-fill validation: real source class, one account, one strategy, one market, one execution source, unique order hashes, no future fills, no paper/synthetic records and explicit borrow checks for shorts.
- Added trade-to-equity P&L reconciliation and exact account/source binding.
- Added forecast and outcome self-hashes plus forecast-ID reconciliation across decisions, projections, outcomes and fills.
- Added a tamper-evident prospective shadow ledger with backfill rejection.
- Made public collection source-isolated, atomic, hashed and portable. An IDX browser handoff is never counted as a real evidence snapshot.
- Kept every technical predictor inactive; price remains an execution reference, valuation denominator, outcome and risk-measurement input only.

## Current ladder

| Layer | Status |
|---|---:|
| Official/public routes defined | 5/5 |
| Public collectors implemented | 5/5 |
| Prospective shadow lanes operational | 5/5 |
| Proof firewalls implemented | 5/5 |
| Markets with bundled real public snapshot | 1/5 |
| Historical point-in-time admitted | 0/5 |
| Historical blind-proven | 0/5 |
| Limited production eligible | 0/5 |
| Fully live-capital ready | 0/5 |

## Authoritative files

- `V95_CURRENT_STATUS.json`
- `V95_FINAL_VALIDATION.json`
- `validate_v95_release.py`
- `autonomous_public_data_plane_v95.py`
- `shadow_execution_ledger_v95.py`
- `forecast_seal_v95.py`
- `blind_proof_runner_v95.py`
- `global_market_promotion_gate_v95.py`
- `component_registry_v95.json`

Historical V8.x–V9.4 reports remain in the package as an audit trail. They are not the V9.5 release authority and some legacy validators intentionally fail newer release identity checks.

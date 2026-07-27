# V9.1 Operator Runbook

1. Put each provider export under `runtime/market_evidence/<market>/`.
2. Normalize every role to the canonical evidence columns. Never invent `available_at`.
3. Create `decision_times.csv` before opening outcomes.
4. Build `predictor_manifest.json` with `build_dataset_manifest_v91.py`.
5. Run `market_data_admission_v91.py` through the V9.1 audit.
6. Freeze model, code, trial ledger, predictor manifest and forecast file in a custodian seal.
7. Store outcomes separately and build `outcome_manifest.json`.
8. Import actual filled trades and daily account equity.
9. Run `blind_proof_runner_v91.py` for one market only.
10. Repeat independently for US, IDX, commodity, FX and crypto.
11. Only five valid signed exact-scope receipts can unlock the global gate.

The current bundled Nasdaq snapshot is only a bootstrap example. It cannot be used for historical proof.

# V9.1 — Proof-Plane Structural Repair

## The decisive finding

V9.0 could not reach data admission even if complete provider files were supplied. Four contracts contradicted each other:

1. `market_data_admission.py` required `outcome_prices` inside the predictor manifest.
2. `build_dataset_manifest_v90.py` explicitly rejected all outcome roles from the predictor manifest.
3. the builder produced a `decision_times_file`, while the admission gate required a single missing global `decision_time`.
4. the builder stored absolute paths, while the admission gate rejected files outside the manifest directory.

The old 0/5 therefore mixed genuine missing data with a software state that was structurally unreachable.

## V9.1 repair

- Predictor and outcome custody are separate.
- Core and optional roles come from the exact market registry.
- Missing optional options/borrow/broker-flow data cannot block a separately registered core model.
- Forecast-local as-of joins replace one global decision timestamp.
- Evidence and decision paths are relative and clean-extract portable.
- Data collection admission, historical-proof readiness, model proof and trading readiness are four distinct states.
- One market is scored at a time; five independent exact-scope receipts are combined only at the global gate.
- Outcomes remain sealed until the model, code, data, forecasts and global trial ledger are frozen.

## What is real in this release

A current Nasdaq Trader security-master snapshot was downloaded and normalized:

- 13,055 distinct instruments
- 26,110 canonical evidence rows
- source file creation time: 2026-07-24 21:31 UTC

It is labelled `CURRENT_SNAPSHOT_BOOTSTRAP_ONLY`. It is not survivor-free history and is not proof of alpha.

## What still blocks 5/5

No code change can manufacture the following:

- historical active and inactive security/contract/venue masters;
- delisting, suspension and corporate-action outcomes;
- point-in-time company estimates and revisions;
- historical broker inventory for IDX;
- historical executable quotes, spread, depth and impact;
- securities-lending availability and fees;
- actual account fills, financing and taxes;
- 24 months / 200 matured prospective trades across four regimes.

Those must be imported from official/licensed providers and actual trading accounts. Backfilling them after outcomes are known would reproduce the overfitting and contamination failure that the project is designed to prevent.

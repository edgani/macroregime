# Validation results — v2.3 release freeze

Release freeze date: 2026-08-26

## Clean-source run

`11 PASS / 0 NONPASS / 11 TOTAL`

- `tests/self_test.py` — PASS
- `tests/final_contract.py` — PASS
- `tests/test_static_contract.py` — PASS
- `tests/test_decision_core.py` — PASS
- `tests/test_data_adapters.py` — PASS
- `tests/test_macro_logic.py` — PASS
- `tests/test_macro_snapshot.py` — PASS
- `tests/test_replay_timestamps.py` — PASS
- `tests/test_negative_controls.py` — PASS
- `tests/test_fuzz.py` — PASS (5,000 randomized entry/expression cases)
- `tests/test_walkforward.py` — PASS (purge/embargo/no-overlap + synthetic OOS machinery)

## Clean-extract run

The ZIP was extracted into a new empty directory and the same aggregate runner was executed from the extracted package.

`11 PASS / 0 NONPASS / 11 TOTAL`

This specifically checks that the distributed artifact contains the files required by its own validation suite and that validation is not depending on the working directory outside the package.

## Compile

`app.py`, `macro_embedded.py`, `decision_core.py`, `data_adapters.py`, and all bundled tests compile successfully under the release container's Python 3.13.5.

## What PASS does and does not mean

PASS here validates software contracts, fail-closed behavior, entry/expression separation, state isolation, timestamp safeguards, data parsers, macro mechanics, negative controls, fuzz/property behavior and walk-forward machinery.

It does **not** claim empirically proven market alpha. Full survivorship-safe PIT market panels, complete historical options surfaces, and several asset-class-specific historical datasets are not bundled; those paths remain gated in the product and are listed in `KNOWN_LIMITATIONS.md`.

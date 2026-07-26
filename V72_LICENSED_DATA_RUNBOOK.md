# V72 licensed-data runbook

The release never downloads or redistributes proprietary Cboe records. Run these commands only against a locally licensed archive.

## 1. Exact archive layout

```text
licensed_data/
  tbt/C1_TBT_YYYY-MM-DD.zip
  quotes/OPTION_QUOTES_SPX_1MIN_YYYY-MM-DD.zip
  grk/C1_GRK_YYYY-MM-DD.zip             # optional; all dates or none
  underlier/SPX_ES_1MIN_YYYY-MM-DD.csv
```

Option Quotes must be ordered as `^SPX`, one-minute, per-day, **Include Calcs + Include Open Interest**. Open interest is unsigned baseline/placebo data only.

## 2. Generate deterministic raw-source manifest

```bash
python generate_v72_source_manifest.py \
  --licensed-root licensed_data \
  --out licensed_data/manifests/source_manifest.json
```

The generator uses the frozen 1,440-session calendar and exact filenames. It cannot silently omit a day or exclude partially supplied GRK files.

## 3. Validate raw archive and create receipt

```bash
python validate_v72_licensed_package.py \
  --licensed-root licensed_data \
  --manifest licensed_data/manifests/source_manifest.json \
  --out licensed_data/manifests/source_validation_receipt.json
```

Passing this step means only `READY_TO_DERIVE_FROZEN_TABLES`. It does not open outcomes and grants no trading permission.

## 4. Produce the three license-permitted derived claim tables

The data processor must follow `V72_SPX_SIGNED_DEALER_PROTOCOL_FROZEN.json`, `V72_OUTCOME_EVALUATOR_SPEC_FROZEN.json`, and the canonical field contracts in `dealer_gamma_research_v72.py`.

Expected outputs:

```text
derived_v72/
  c1.csv   # verified gamma response features and 5/15/30m outcomes
  c2.csv   # preregistered approach events and pin/break outcome
  c3.csv   # ex-ante variance gap and executable net PnL
```

Raw Cboe records must not be copied into the War Room release.

## 5. Seal derived tables without opening the historical evaluator

```bash
python generate_v72_derived_manifest.py \
  --derived-root derived_v72 \
  --source-receipt licensed_data/manifests/source_validation_receipt.json \
  --out derived_v72/derived_manifest.json
```

## 6. One-time frozen historical evaluation

```bash
python run_v72_frozen_evaluation.py \
  --derived-root derived_v72 \
  --derived-manifest derived_v72/derived_manifest.json \
  --source-receipt licensed_data/manifests/source_validation_receipt.json \
  --derived-receipt derived_v72/derived_validation_receipt.json \
  --open-receipt derived_v72/LOCKBOX_OPENED_ONCE.json \
  --result derived_v72/V72_HISTORICAL_RESULT.json
```

The opening receipt is written before outcomes are parsed. If evaluation is interrupted, the same lockbox cannot be reopened under changed code.

## 7. Promotion boundary

Even a passing historical result remains research-only. Capital stays blocked until the separate signed prospective ledger reaches its frozen minimum observations and independent dates without retuning.

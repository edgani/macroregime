# How to validate War Room OS v4.2

## User-machine release check

On Windows, run:

```text
CHECK_EVERYTHING.bat
```

It installs dependencies in `.venv`, verifies the package manifest, compiles Python, runs the quarantined legacy compatibility suite, performs one offline worker cycle and checks a real Streamlit health endpoint.

Required output:

```text
status: PASS
software_permission: READY_FOR_USER_REVIEW
predictive_components_promoted: 0
capital_permission: BLOCKED
```

## Build-environment deep audit

```bash
python run_master_reaudit_v42.py
```

This additionally runs the 43-contract source/browser suite. It proves UI, code, capability and fail-closed semantics—not predictive edge.

## Predictive proof

Use the templates in `evidence_templates/` and follow `PROOF_PLAN.md`. No component can be promoted from a good backtest alone. Exact-scope point-in-time lineage, repeated purged walk-forward OOS, a strong baseline, multiple-testing correction, realistic costs/capacity, a one-time untouched lockbox, matured prospective outcomes and human approval are mandatory.

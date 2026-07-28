> Release continuation: v5.3. The visual application contract remains v4.2; v5.3 denotes hardening + research-evidence integration.

# How to validate War Room OS v5.2

## Windows user-machine gate

Run:

```text
CHECK_EVERYTHING.bat
```

The script creates `.venv`, installs `requirements.txt`, resets runtime state, and runs `validate_user_v53.py`.

The verifier checks:

- strict v5.2 package manifest;
- complete Python compilation;
- 39 adversarial hardening checks;
- GCFIS compatibility under warnings-as-errors;
- bundled data container integrity;
- statistical negative/positive controls;
- offline collector plus runtime snapshot integrity;
- actual Streamlit `/_stcore/health`;
- full legacy Parquet semantic batteries when `pyarrow` is installed;
- default zero-promotion/capital-blocked proof state.

A missing required dependency is `BLOCKED_BY_ENVIRONMENT`, not PASS.

## Build-environment deep audit

```bash
python run_v52_hardened_audit.py
```

Every executable validator is copied into its own fresh temporary package. The source is hashed before and after execution; any mutation fails the audit.

## Manifest-only check

```bash
python verify_manifest_v53.py
```

The verifier rejects unsafe paths, duplicate entries, missing files, unexpected protected files, byte-size changes, hash changes and a forged manifest row digest.

## Predictive proof

Software tests cannot create alpha. Follow `PROOF_PLAN.md`, then issue an exact-scope signed receipt only after the full proof path in `proof/receipts/README.md` is satisfied.

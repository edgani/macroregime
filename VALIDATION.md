# Validation status — v5.2 real-source hardening

Authoritative shipped reports:

- `V52_CLEAN_EXTRACT_AUDIT_REPORT.json`
- `V52_CLEAN_EXTRACT_TEST_LOG.txt`
- `V52_HARDENING_ADVERSARIAL_REPORT.json`
- `V52_BUNDLED_DATA_INTEGRITY_REPORT.json`
- `V52_DEEP_REAUDIT_FINAL.md`

Authoritative user-machine report after installation:

- `V52_USER_VALIDATION_REPORT.json`

Run:

```bash
python run_v52_hardened_audit.py
```

or on Windows:

```text
CHECK_EVERYTHING.bat
```

A software hardening PASS proves fail-closed implementation and test behavior only. It does not promote predictive components. The shipped default remains zero promoted components and capital blocked.

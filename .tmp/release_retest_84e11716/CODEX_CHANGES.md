# Codex changes

- `opportunity_ui.py` — made tracked events obey global search and market scope; added detection/current price and move; exposed the full causal/capture chain; added explicit total-score gating and component availability; added compact chain styling.
- `prospective_validation.py` — gated valuation and revision baselines on defensible PIT evidence; added a frozen Existing engine comparator restricted to READY/PARTIAL rows.
- `tests/test_opportunity_cockpit_contract_v33.py` — added regression coverage for shell filtering, complete chain, price context, and score gating.
- `tests/test_baseline_evidence_gates_v33.py` — added regression coverage for baseline evidence and readiness gates.
- `VERSION.txt` — advanced the audit candidate version to 3.3.0.
- `CODEX_AUDIT_BEFORE.md`, `CODEX_CHANGES.md`, `CODEX_LOGIC_VERIFICATION.md`, `CODEX_UI_VERIFICATION.md`, `CODEX_REMAINING_GAPS.md` — recorded evidence, changes, and honest release-gate status.

## Independent second pass

- `opportunity_longitudinal.py` — rejects backdated lifecycle writes and prevents terminal episode resurrection; recurrence must allocate a new immutable episode.
- `opportunity_ui.py` — applies active search/market scope consistently to KPI counts, event feeds, outcome fallback, alerts, and theme clusters.
- `tests/test_lifecycle_pit_guards_v33.py` — regression coverage for backdating, terminal immutability, and recurrence identity.
- `tests/test_opportunity_cockpit_contract_v33.py` — expanded scope-consistency regression coverage.
- `tests/run_all.py` — includes all v3.3 regressions and uses repository-local per-script state roots.

All changes are intentionally uncommitted and unpushed.

## Final-verdict repair

- `tests/_state_dir.py` and six SQLite-dependent test scripts now reuse the runner-provisioned unique state directory, eliminating inaccessible nested temporary directories without reducing isolation or assertions.
- `tests/browser_smoke.py` provides reproducible Chromium route, responsive, screenshot, render-completion, overlay, and console verification once browser IPC is permitted; the final-verdict repair removed the machine-specific Chrome path and made navigation assertions button-specific.
- The full repository and exact extracted-package logic suites now pass 26/26. UI verification remains truthfully blocked by the execution environment.

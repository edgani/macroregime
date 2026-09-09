# Codex changes

- `opportunity_ui.py` — made tracked events obey global search and market scope; added detection/current price and move; exposed the full causal/capture chain; added explicit total-score gating and component availability; added compact chain styling.
- `prospective_validation.py` — gated valuation and revision baselines on defensible PIT evidence; added a frozen Existing engine comparator restricted to READY/PARTIAL rows.
- `tests/test_opportunity_cockpit_contract_v33.py` — added regression coverage for shell filtering, complete chain, price context, and score gating.
- `tests/test_baseline_evidence_gates_v33.py` — added regression coverage for baseline evidence and readiness gates.
- `VERSION.txt` — advanced the audit candidate version to 3.3.0.
- `CODEX_AUDIT_BEFORE.md`, `CODEX_CHANGES.md`, `CODEX_LOGIC_VERIFICATION.md`, `CODEX_UI_VERIFICATION.md`, `CODEX_REMAINING_GAPS.md` — recorded evidence, changes, and honest release-gate status.

All changes are intentionally uncommitted and unpushed.

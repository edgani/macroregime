# Logic verification

## Invariants reviewed

- Mandatory capture: an Opportunity Score remains unavailable when capture evidence is unavailable.
- PIT outcomes: comparator anchors cannot occur after detection; endpoints use the first observable bar on/after the target; availability is the latest required observation.
- Walk-forward: training rows require both feature time and label-availability time before test cutoff.
- Lifecycle: first detection is immutable; terminal history is retained; a recurrence receives a new episode identity.
- Readiness: GATED/PARTIAL evidence caps lifecycle state.
- Discovery: stale/undated news is rejected and identical syndicated headlines receive one vote.
- Macro: missing critical inputs cannot upgrade risk posture.
- Baselines: selections are frozen prospectively; valuation/revision gates now fail closed; Existing engine is an explicit comparator.

## Results in this environment

- Python 3.12 compile check: PASS for 15 production modules.
- Exact extracted ZIP test run: 19 PASS / 6 environment-blocked / 25 total test scripts.
- The six blocked scripts were `test_decision_core.py`, `test_logic_hardening_v326.py`, `test_longitudinal_opportunity.py`, `test_opportunity_kernel.py`, `test_prospective_validation.py`, and `test_v32_acceptance.py`; each failed because the managed Windows sandbox denies SQLite access in directories created by Python `tempfile`.
- New regression scripts: 2 PASS / 0 FAIL.
- `git diff --check`: PASS (line-ending notices only).
- Exact ZIP static exclusion scan: 0 forbidden state/secret/cache matches across 95 entries.

These results are not described as a full-suite PASS because the environment prevented execution of tempfile/SQLite cases. No PIT/OOS performance superiority is claimed.

## Independent second-pass evidence

- Lifecycle persistence rejects timestamps earlier than first seen or earlier than the latest state, and rejects any different state after `INVALIDATED`/`RESOLVED`.
- Repository aggregate on Python 3.12: **20 PASS / 6 environment-blocked / 26 total**. The six nonpasses are the same nested-`TemporaryDirectory`/SQLite sandbox failures, not assertion failures.
- Three v3.3 regressions run directly against repository-local state: **3 PASS / 0 FAIL**.
- Production-module compile check: PASS.

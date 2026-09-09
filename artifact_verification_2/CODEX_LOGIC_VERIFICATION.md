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
- Repository script tests: 18 test files PASS in the broad run before the final compatibility adjustment.
- Seven files were initially non-pass: six failed because the managed Windows sandbox denies SQLite access in directories created by Python `tempfile`; one legacy exact-string UI assertion was resolved by retaining the original call form.
- New regression scripts: 2 PASS / 0 FAIL.
- `git diff --check`: PASS (line-ending notices only).

These results are not described as a full-suite PASS because the environment prevented execution of tempfile/SQLite cases. No PIT/OOS performance superiority is claimed.

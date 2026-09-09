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

- Repository aggregate on Python 3.12: **26 PASS / 0 NONPASS / 26 total test scripts**.
- The six formerly blocked SQLite suites now consume the aggregate harness's already unique `OIE_STATE_DIR` instead of creating an inaccessible nested Windows temporary directory.
- Python 3.12 production-module compile check: PASS.
- Exact extracted ZIP aggregate: **26 PASS / 0 NONPASS / 26 total test scripts**.
- `git diff --check`: PASS (line-ending notices only).
- Exact ZIP static exclusion scan: 0 forbidden state/secret/cache matches across 95 entries.

The full scripted logic suite passes. No PIT/OOS performance superiority is claimed.

## Independent second-pass evidence

- Lifecycle persistence rejects timestamps earlier than first seen or earlier than the latest state, and rejects any different state after `INVALIDATED`/`RESOLVED`.
- Repository aggregate on Python 3.12: **26 PASS / 0 NONPASS / 26 total**.
- Three v3.3 regressions run directly against repository-local state: **3 PASS / 0 FAIL**.
- Production-module compile check: PASS.

## Final-verdict repair rerun

- Repository aggregate on Python 3.12: **26 PASS / 0 NONPASS / 26 total**.
- Production-module compile check: PASS.
- `git diff --check`: PASS (line-ending notices only).
- Browser launch remains environment-blocked; no UI PASS is claimed.
- Rebuilt release ZIP: **97 entries**; the final SHA-256 is reported alongside the delivered artifact.
- Exact extracted rebuilt ZIP aggregate: **26 PASS / 0 NONPASS / 26 total**.
- Exact ZIP path scan: **0 forbidden cache, state, or credential files**.

## Independent final-audit repair

- Repository aggregate on Python 3.12: **27 PASS / 0 NONPASS / 27 total**, including the release-packaging regression.
- The builder computes the digest from the completed temporary ZIP, replaces the target, and then replaces its sidecar.
- The exact final ZIP is extracted to a fresh hash-keyed directory and the same 27-script suite is rerun there.
- The sidecar digest, independently computed digest, and hash-keyed extraction directory are required to agree.

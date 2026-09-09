# Remaining gaps

- Browser verification and screenshots are blocked by the managed Windows process/IPC policy. This prevents satisfying the actual-browser release gate in this environment.
- Six test files that create SQLite databases inside Python `TemporaryDirectory` are blocked by the managed filesystem policy. They are not recorded as product failures, but the exact full-suite pass count cannot be claimed.
- The handoff's original requirements file and visual-reference images are absent from the repository, so pixel/design comparison is unavailable.
- HK/Hong Kong, China, Europe, Taiwan, and Index remain architectural market routes without seeded universe/provider coverage in `data/universe.csv`; they must remain GATED until defensible data exists.
- Public provider availability and freshness depend on external endpoints. Missing families remain explicit and cannot support confidence or action upgrades.
- Mature prospective OOS history is still required before any performance-superiority claim.

Second-pass evidence: the aggregate harness now starts from repository-local state and includes 26 scripts, but six legacy scripts create an additional nested `TemporaryDirectory` that the managed Windows policy makes inaccessible to SQLite. Actual browser verification remains blocked at process IPC.

Release status: **candidate artifact only — release gate BLOCKED, not PASS**.

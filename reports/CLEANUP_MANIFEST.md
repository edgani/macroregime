# Repository Cleanup Manifest

The redesign started from a recoverable backup branch and removed artifacts that had no executable source or references in the EROS v3 package.

## Removed

- 360 committed `.pyc` files and all tracked `__pycache__` trees.
- Orphaned compiled-only legacy trees under former root, `engines/`, `gcfis/`, `warroom/`, and old test caches.
- Generated logs and runtime shadow-state snapshots.
- The unreferenced `cache/prices.parquet` runtime artifact.
- Six unreferenced legacy validation JSON files from superseded V55/V71/V72 paths.

## Preserved or rebuilt

- Tested economic contracts under `src/eros/`.
- Unit, integration, leakage, regression, and E2E tests.
- The package lockfile and reproducible Python 3.12 environment.
- A frozen synthetic dashboard fixture used only for deterministic UI validation.
- Requirement traceability, production-readiness, limitation, and cleanup reports.
- Configuration-driven global market and data-source registries.

## Recovery

The pre-redesign `main` state is retained in the local backup branch created before cleanup. Git history also preserves every removed tracked artifact.

No legacy compiled bytecode is treated as reusable source code. If an old engine must be recovered, it must be restored from source history, reviewed, and reintroduced with tests rather than imported from `.pyc` files.

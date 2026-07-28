# Dead Code and Bloat Report — Phase 2 cleanup (commit a60f413)

Classification method: `tools/audit/classify_files.py` produced
`docs/audit/cleanup_plan.json` with a per-file label and human-readable reason.
Safety proof before any removal/move: strict AST import-graph reachability from
entry points (`app.py`, `run.py`, `warroom_data_worker_v101.py`, `shadow_runner_v101.py`),
tests, and `src/` (`docs/audit/import_graph.json`, `production_reachable.json`),
plus static reference scan (`unreachable_refscan.json`) for dynamic imports,
Streamlit routing, config-driven loading, and string references.

## Labels

- A (22 files): production runtime surface — kept at root
- B (122 files): v3 package + tests + scripts — kept
- C (641 files): kept data/config/research bundles
- D (763 files): OBSOLETE for runtime, kept for research reproducibility — MOVED to `research/archive/`
- E (238 files): GENERATED_TEMPORARY / PROVEN_DEAD — DELETED

## Deleted (238) — every entry individually classified in cleanup_plan.json

| Category | Count | Examples | Justification |
|---|---|---|---|
| Compiled bytecode (`__pycache__/*.pyc`) | 224 | `__pycache__/app.cpython-313.pyc` | Bytecode must never be tracked |
| Generated run-output JSON | 6 | `LIVE_STACK_TEST_REPORT.json`, `V63/V64_TAB_MODEL_AUDIT.json` | Regenerable; superseded by docs/audit/TEST_RESULTS.md |
| Generated dashboard export | 1 | `dashboard_live.html` (7.2 MB) | Generated snapshot export; live mirror retained at `static/dashboard_live.html` |
| Synthetic demo outputs | 2 | `outputs/synthetic_demo/*` | Regenerable demo output |
| Cache dir | 2 | `.cache/` | Caches must not be tracked |
| Stray scratch JS | 2 | `_v.js`, `_v2.js` | Scratch files, unreferenced |
| Editor backup | 1 | `decision_packet_v98.py.bak` | Backup artifact |

## Moved to research/archive/ (763)

| Type | Count |
|---|---|
| Python (legacy versioned scripts v4–v101, validators, runners) | 276 |
| JSON (per-version reports, manifests, registries) | 229 |
| Markdown (per-version status/release notes) | 140 |
| .bat launchers | 79 |
| PNG previews | 11 |
| txt/log/example/csv/ps1/exitcode | 28 |

Notable: entire `legacy/`, `legacy_v42_audit/`, `legacy_v52_release/` trees moved under
`research/archive/`. No directory was deleted wholesale; every entry was individually
classified and recorded in cleanup_plan.json before staging.

## Corrections discovered after cleanup (Phase 3)

- `research_evidence_registry_v53.json` was misclassified D (archive) but is a LIVE registry
  consumed by kept `research_evidence_v53.py` — restored to root (commit 9ca1a8e).
- `artifacts/release_manifest_ready.json` (E, generated) is bound by
  `tests/test_release_ready.py` — regenerated and recommitted (commit 7925c41).
- The two historical status docs referenced by the release manifest generator were repointed
  to their `research/archive/` paths.

## Non-production residue kept deliberately (documented, not deleted)

- `data/resilient_market_data.py` — legacy cache helper with local `.pkl` cache strings;
  0 production references; allowlisted in the v52 static scan with a recorded finding.
- `static/dashboard_live.html` — live runtime mirror written by `runtime_store`; kept.
- `runtime/warroom_core_context_m757mhl8.pkl` — tracked runtime pickle; flagged as a smell.
  Not deleted in this audit because its writer/reader path was not fully traced; recorded
  here as PROSPECTIVE cleanup candidate pending owner confirmation.

## Size impact

- 1001 files changed in commit a60f413; 63,759 tracked lines removed from root surface.
- Tracked working tree no longer contains bytecode, caches, or scratch files (.gitignore added).

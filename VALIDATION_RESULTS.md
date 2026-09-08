
## v3.2.2 — Unified UI replacement
- Removed the legacy Decision Desk from the exposed product surface.
- Removed the old sidebar scanner UI; market scope/search/refresh now live in the unified top shell.
- All exposed workspaces use one dark-neon visual system: Control Room, Opportunities, Verticals, Macro & Events, Learning / Replay.
- Replaced nested/native tab mazes in exposed vertical/learning surfaces with persistent button sub-navigation.
- Core causal, macro, valuation, expression, longitudinal-memory and walk-forward logic is preserved; this is a UI/UX replacement, not an engine rewrite.
- No autotrading and no classic technical-indicator fallback.

# Validation Results — v3.2.1

Validated locally on the packaged source tree.

```text
19 PASS / 0 NONPASS / 19 TOTAL
```

The suite includes the original v3.1 regression tests plus:
- immutable first-seen event test;
- restart persistence test;
- first-high-conviction tracking;
- forward path / benchmark-alpha math;
- expanding chronological walk-forward ordering;
- 20/20 v3.2 structural acceptance contract.

This verifies software invariants. It does **not** claim that long-horizon opportunity alpha is already statistically proven; fresh longitudinal databases necessarily need prospective outcomes or correctly reconstructed PIT history.

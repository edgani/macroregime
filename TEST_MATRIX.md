
## v3.2.2 — Unified UI replacement
- Removed the legacy Decision Desk from the exposed product surface.
- Removed the old sidebar scanner UI; market scope/search/refresh now live in the unified top shell.
- All exposed workspaces use one dark-neon visual system: Control Room, Opportunities, Verticals, Macro & Events, Learning / Replay.
- Replaced nested/native tab mazes in exposed vertical/learning surfaces with persistent button sub-navigation.
- Core causal, macro, valuation, expression, longitudinal-memory and walk-forward logic is preserved; this is a UI/UX replacement, not an engine rewrite.
- No autotrading and no classic technical-indicator fallback.

# Test Matrix — v3.2.1

| Area | Status | Evidence |
|---|---|---|
| Existing v3.1 core regressions | PASS | original 16 tests preserved |
| Longitudinal event memory | PASS | immutable first detection + restart persistence |
| Lifecycle memory | PASS | state changes append; invalidated events retained |
| Outcome math | PASS | absolute, benchmark-relative, MFE/MAE path test |
| Walk-forward chronology | PASS | training years strictly precede test year |
| No random split | PASS | structural acceptance |
| No autotrading | PASS | structural acceptance |
| No primary classic-indicator dependency in new discovery layer | PASS | structural acceptance |
| Multi-market architecture | PASS | US/IHSG/HK/China/Europe/Taiwan/Crypto/FX/Commodity contracts |
| Insufficient-sample fail-closed behavior | PASS | empty/no-mature-outcome output remains gated |
| UI contract | PASS | dense tracker + dense three-column control room compile |
| Workspace navigation | PASS | native button router; persistent state; rendered before scan; nav rerun skips one stale refresh |
| Full historical alpha proof | NOT CLAIMED | requires matured prospective/PIT outcomes |

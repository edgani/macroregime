
## v3.2.2 — Unified UI replacement
- Removed the legacy Decision Desk from the exposed product surface.
- Removed the old sidebar scanner UI; market scope/search/refresh now live in the unified top shell.
- All exposed workspaces use one dark-neon visual system: Control Room, Opportunities, Verticals, Macro & Events, Learning / Replay.
- Replaced nested/native tab mazes in exposed vertical/learning surfaces with persistent button sub-navigation.
- Core causal, macro, valuation, expression, longitudinal-memory and walk-forward logic is preserved; this is a UI/UX replacement, not an engine rewrite.
- No autotrading and no classic technical-indicator fallback.

# v2.5 Simple Decision Board

## Why this release exists
v2.4 was visually rich but still too abstract for fast daily decisions. The evidence × asymmetry scatter and expression-coverage heatmap required the user to interpret model axes before knowing what to do.

v2.5 changes the default daily screen around one rule: **action first, model detail second**.

- Replaced the default opportunity scatter + coverage matrix with a plain **traffic-light board**: ACT NOW / WATCH / AVOID-DOWNSIDE / NOT READY.
- Added **Top opportunities now** cards with ticker, plain action, simple reason, confidence, supporting/negative evidence counts, and eligible trade modes.
- Added a compact **How it can be traded** strip showing how many stock / leverage / option / spot expressions are genuinely ready.
- Replaced the expression evidence chart as the default view with a simple ranked list: **action → reason → confidence → status**.
- Moved the full table, readiness gates, and evidence chart under **Advanced · all rows / model gates**.
- Simplified the hero legend to plain meanings: ACT NOW / WATCH / REDUCE-SHORT-SIDE / NOT ENOUGH DATA.
- Preserved the same fail-closed capital rules. No missing causal model is converted into a trade signal.

## Capital-safety behavior is unchanged
A visible row is not automatically actionable. `READY` means the existing decision engine has earned that expression. `WATCH` means interesting but not entry-ready. `DATA GATED` means the required causal/model inputs are incomplete.

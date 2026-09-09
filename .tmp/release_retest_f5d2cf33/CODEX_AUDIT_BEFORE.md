# Codex audit before changes

Audit date: 2026-09-09. Source of truth: this repository checkout.

## Defects found

- High — The Opportunities route's global search and market scope filtered the live radar but not the persistent tracked-opportunity list. A user could select a market scope and still see events outside it.
- High — The selected-opportunity surface omitted current price and move since immutable detection price, so it could not answer what happened after detection.
- High — The visible causal chain stopped at beneficiary. Revenue link, margin link, catalyst, and invalidation were stored but absent from the primary chain.
- High — The cockpit showed only four score cards and did not distinguish unavailable components from observed components. A missing total rendered as a dash instead of an explicit evidence gate.
- High — Prospective `Cheapest valuation` baselines accepted any positive forward P/E even when valuation confidence was GATED.
- High — Prospective analyst-revision baselines could select rows whose revision state was unavailable/gated.
- Medium — No prospective `Existing engine` comparator was frozen despite being required for honest baseline comparison.

## Second-pass defects found

- High — `record_state()` accepted backdated lifecycle observations and could reactivate a terminal episode under its old immutable event identity.
- High — Opportunities filtering was inconsistent: selector/radar were scoped, but the Active KPI, lifecycle/alert/outcome fallback feeds, and theme clusters could expose out-of-scope events.
- Medium — The aggregate test runner omitted the first-pass v3.3 regressions and failed before reporting results when system-temp cleanup was denied.

## Existing controls independently located

- Economic capture is mandatory for a numerical Opportunity Score.
- Macro contributes only when opportunity-specific alignment evidence exists.
- Terminal episodes are not resurrected; recurrence creates a new event ID.
- Outcome horizons include 1D, 3D, 1W, 2W, 1M, 3M, 6M, and 12M.
- Outcome labels preserve missing benchmark/sector alpha and record label availability.
- Walk-forward training filters on label availability before each test cutoff.
- News discovery rejects undated/stale observations and deduplicates syndicated headlines.
- Macro missing data fails closed.

## Missing handoff evidence

`ORIGINAL_REQUIREMENTS.txt`, `codex_refs/TARGET_UI_REFERENCE.png`, and all `codex_refs/CURRENT_*.png` were absent from this checkout. The master specification supplied in the task was used as binding guidance. No visual-reference comparison is claimed.

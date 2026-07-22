# Legacy Component Quarantine — v4.2

The repository retains older GCFIS engines and contracts for regression diagnostics, historical comparison and backward compatibility. Their successful unit tests prove only that their code paths execute according to their documented synthetic fixtures.

They are **not promoted predictive components** and may not directly emit capital actions in the v4.2 dashboard.

Quarantined outputs include, among others:

- legacy `BUILD_LONG` / `BUILD_SHORT` rankings;
- heuristic conviction, surge and crash scores;
- legacy opportunity price scenarios and final-desk picks;
- generic accumulation/distribution labels;
- market-mode classifications;
- old portfolio sizing and allocation suggestions.

The active v4.2 path exposes only descriptive price context unless an exact-scope component is promoted in the proof registry. The active `desk_picks` payload is empty and capital remains blocked.

Signed option positioning is also quarantined unless every contract row supplies explicit `dealer_sign`. Gross call/put open interest is never converted into dealer ownership by assumption.

A legacy component can leave quarantine only through the same promotion ladder as a new component: point-in-time data contract, frozen baseline, repeated walk-forward OOS, multiple-testing correction, costs/capacity, untouched lockbox, prospective evidence and human approval.

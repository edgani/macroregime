# Logic Audit v3.2.6

## Objective
Find high-conviction opportunities early without substituting price momentum for missing economics, then measure exactly what happened after detection without hindsight leakage.

## Verified design invariants
- first seen is immutable;
- recurring setup after terminal state is a new episode;
- historical event snapshot is not updated with future fundamentals;
- horizon endpoint is first observable bar on/after target date;
- daily close has an information-availability clock;
- benchmark/sector start must be observable by detection;
- relative label availability is the latest timestamp required by all requested comparators;
- WFO training labels must be available before the test cutoff;
- NaN alpha is UNKNOWN;
- economic capture is mandatory for numerical Opportunity Score;
- generic narrative/capex/market membership does not create causal archetypes;
- market-specific readiness caps actions and expressions;
- correlated fundamentals do not masquerade as four independent families;
- no automatic production-weight mutation;
- baseline and runner cohorts are frozen before future outcomes;
- runner recall denominator contains only matured prospectively audited runners.

## Remaining epistemic risk
The largest remaining risk is data coverage, not a known silent code shortcut. A clean test suite cannot create missing PIT history. The UI and learning outputs therefore expose GATED/PARTIAL states and sample counts rather than invented confidence.

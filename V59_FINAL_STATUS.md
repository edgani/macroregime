# War Room OS V5.9 — Position Lifecycle Continuation from V5.8

## Final verdict

`SOURCE_CONTINUATION_PASS / LIVE_ALPHA_NOT_PROVEN / CAPITAL_BLOCKED`

## Correct baseline

This release was built directly from the uploaded V5.8 package:

- Baseline SHA-256: `a3e24e9cc390bb572817aa260e1018bc50f6271b870431e81cca03cf87645601`
- V5.8 mapped candidates: 868
- V5.8 empirical claims tested: 795
- Gross globally corrected survivors: 3
- Survivors after 25 bps/month stress: 0
- Live predictive components: 0
- Capital permission: BLOCKED

Therefore existing ticker output is not certified as a forward-profitable selector.

## Fixed source defects

1. Surge was previously computed after signal/ranking serialization. It is now computed before the row is created.
2. Final desk was previously given the wrong ranking contract. It now receives the actual `master_long` and `master_short` rows.
3. Unproven surge previously contributed 15% of desk score. It now has zero selection weight and remains diagnostic only.
4. Missing signed-flow inputs no longer become apparent neutral evidence in the new lifecycle engine.
5. Opposite long/short changes are dominance-aware, so large short covering cannot be mislabeled as long accumulation.

## New capability

Cross-market descriptive position lifecycle:

- long/short building;
- short covering and long liquidation;
- mixed risk build and mixed deleveraging;
- pre-surge tightening;
- active physical or positioning surge;
- exhaustion risk;
- strict distribution/top confirmation.

Supported contracts: US equities/ETFs, IHSG/IDX, FX, commodities and crypto.

## Claim limits

The engine can detect observable state only when required data are present. It cannot currently prove:

- that a trader knew a war or event in advance;
- beneficial-owner identity from volume/OI;
- calibrated probability of a future surge or top;
- exact price target or timing;
- profitable long/short ticker selection;
- prospective profitability.

Every lifecycle output is `NOT_PROVEN`, live weight `0.0`, capital `BLOCKED`.

## Oil 2026 conclusion

- 17 February: bearish repositioning, not long accumulation.
- 24 February, the last COT snapshot before the 28 February conflict: both managed-money long and short books expanded, classified as mixed risk build.
- 3 March: mixed deleveraging.
- 10 March: the bullish positioning impulse was dominated by short covering.
- 21–24 July: physical crude and prompt premiums surged while managed-money long and short books both expanded only modestly; current state is active physical surge, not proven broad speculative accumulation.
- A top is not confirmed because current physical tightness persists and signed distribution plus failed follow-through plus fundamental weakening are not jointly established. EIA's forecast inventory builds for 4Q26/2027 are a medium-horizon downside scenario, not present top confirmation.

## Validation summary

The final clean-extract validation report is authoritative for exact counts. Core checks include:

- exact V5.8 ancestry hash;
- compile of release Python source;
- V5.8 exhaustive research validator;
- V4.2 deep re-audit regression;
- live-stack regression;
- GCFIS test suite;
- V5.9 lifecycle adversarial tests;
- dashboard JavaScript syntax;
- proof registry and formula register contracts;
- clean manifest and deterministic ZIP rebuild;
- source mutation check during clean validation.

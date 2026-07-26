# V6.5 Proof-First Breakthrough

## Why earlier work kept ending at “not proven”

The old objective silently bundled five different questions:

1. Does a market relationship exist historically?
2. Does it survive modern validation and a lockbox?
3. Can it be reconstructed point-in-time at stock level?
4. Does it survive capacity and actual implementation costs?
5. Does it remain profitable prospectively?

A component could pass the first two and still be rejected because the data feed for the final three was absent. Conversely, a component could be operationally available but have no market proof. V6.5 separates these layers.

## Exact test sequence

### Stage A — bounded information-origin ensemble

Eight combinations were frozen before outcome analysis. The components were chosen from the only modern maintained-archive survivor (`SmileSlope`) and historically supported information-origin families (`AnalystRevision`, `AnnouncementReturn`, `DivYieldST`) plus explicit risk controls.

### Stage B — global selection adjudication

The follow-up candidates were not allowed to use a local eight-candidate correction. They were adjudicated against a conservative family of:

- 208 original modern factor candidates;
- 8 bounded follow-up combinations;
- total family: **216**.

### Stage C — stability falsification

The candidates then had to survive:

- rolling 36-month windows;
- positive calendar-year share;
- leave-one-year-out refits;
- concentration in one dominant year;
- moving-block bootstrap;
- reverse-sign negative control.

## Results

### SMILE_ANN

Members: `SmileSlope + AnnouncementReturn`

- Validation alpha after 10 bps/month: **0.7075% monthly**
- Validation global-216 lower bound: **0.3945% monthly**
- Lockbox alpha after 10 bps/month: **0.3799% monthly**
- Lockbox global-216 lower bound: **0.0482% monthly**
- Validation rolling-positive share: **100.0%**
- Lockbox rolling-positive share: **98.39%**
- Lockbox moving-block bootstrap positive probability: **99.61%**

### SMILE_ONLY

Members: `SmileSlope`

- Validation alpha after 10 bps/month: **0.7849% monthly**
- Validation global-216 lower bound: **0.2577% monthly**
- Lockbox alpha after 10 bps/month: **0.6417% monthly**
- Lockbox global-216 lower bound: **0.0295% monthly**
- Validation rolling-positive share: **100.0%**
- Lockbox rolling-positive share: **98.39%**
- Lockbox moving-block bootstrap positive probability: **99.92%**

### SMILE_EXPECTATIONS_DIV

Members: `SmileSlope + AnalystRevision + AnnouncementReturn + DivYieldST`

- Validation alpha after 10 bps/month: **0.4273% monthly**
- Validation global-216 lower bound: **0.1937% monthly**
- Lockbox alpha after 10 bps/month: **0.1928% monthly**
- Lockbox global-216 lower bound: **0.0277% monthly**
- Validation rolling-positive share: **100.0%**
- Lockbox rolling-positive share: **98.39%**
- Lockbox moving-block bootstrap positive probability: **99.53%**

## What is now proven

The archive-level statistical relationship is supported within the frozen contract. This is stronger than V6.4 because:

- the family includes the original 208-factor search plus the eight follow-ups;
- the 10 bps hurdle survives both periods;
- the stability battery survives both periods;
- the inverse/reverse-sign control fails as required.

## What remains blocked

The proof is not yet sufficient for a ticker ranking engine because the maintained archive does not provide the exact stock-level point-in-time portfolio implementation needed to verify:

- option quote timestamp and surface quality;
- eligibility at each rebalance;
- stale/crossed quote exclusion;
- delisting and corporate-action handling;
- liquidity/capacity weighting;
- turnover and trade-level costs;
- short borrow availability and cost;
- 2023–2026 independent outcomes.

## System consequence

The three claims are now **evidence-active**. They can influence research priority and explain why option-implied tail asymmetry is worth reconstructing. They remain **decision-inactive** and have zero live weight.

The breakthrough is therefore not a cosmetic “PASS.” It is a strict narrowing of the production candidate set from hundreds of ideas to three exact contracts, while all unsupported components remain quarantined.

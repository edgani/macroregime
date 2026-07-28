# V5.9 Position Lifecycle Mapping — continuation from exact V5.8 source

## Scope

This continuation starts from the exact uploaded V5.8 package whose SHA-256 is:

`a3e24e9cc390bb572817aa260e1018bc50f6271b870431e81cca03cf87645601`

It does not replace the V5.8 research ledger and does not promote any ticker selector. It fixes two live wiring defects and adds a fail-closed, cross-market lifecycle diagnostic for observable position building, surge, exhaustion and distribution.

## V5.8 defects found in the actual source

1. `gcfis/orchestrator.py` serialized `sig.surge` before `run_surge()` was called. Ranking rows therefore received `None`, while the final desk converted missing surge to a neutral fallback. The displayed surge story could not actually represent the ticker state used when the row was built.
2. `build_final_desk()` received the raw regime-meta object even though it expects `master_long` and `master_short`. The internal final shortlist could therefore be empty even when actionable long/short rows had already been created.
3. `gcfis/meta/final_desk.py` allocated 15% of its desk score to surge even though `gcfis/engines/surge.py` explicitly says its weights are priors pending walk-forward validation.
4. The existing accumulation engine uses fixed-weight combinations of relative strength, volume, revisions, ownership and open interest. Those variables do not identify beneficial owner or informed intent and therefore cannot justify labels such as “smart money knew”.

## Correct causal separation

The lifecycle engine separates five questions that must not be collapsed:

1. **Position state** — are observable long/short books expanding, contracting or being covered?
2. **Surge state** — is price acceleration accompanied by physical/fundamental tightening or signed participation?
3. **Top risk** — are crowding, failed follow-through and weakening fundamentals appearing?
4. **Distribution confirmation** — is there signed selling plus failed follow-through plus weakening physical/fundamental evidence?
5. **Future edge** — does the exact state improve calibrated forward outcomes in validation, lockbox and prospective tests?

Only the first four are implemented as descriptive state. The fifth remains unproven.

## Position states

- `LONG_BUILDING`
- `SHORT_BUILDING`
- `SHORT_COVERING`
- `LONG_LIQUIDATION`
- `BULLISH_REPOSITIONING`
- `BEARISH_REPOSITIONING`
- `MIXED_RISK_BUILD`
- `MIXED_DELEVERAGING`
- `SIGNED_BUYING`
- `SIGNED_SELLING`
- Ambiguous price × OI states such as `LONG_BUILD_OR_NEW_RISK`
- `PRICE_ONLY_CONTEXT`
- `NO_POSITION_DATA`

A small change on one side cannot hide a much larger opposite-side move. For example, long +2,663 and short −21,074 is classified as `SHORT_COVERING`, not long accumulation.

## Surge states

- `POSITION_BUILDING_PRE_MOVE`
- `PRE_SURGE_TIGHTENING`
- `ACTIVE_POSITIONING_SURGE`
- `ACTIVE_PHYSICAL_SURGE`
- `PRICE_SURGE_UNATTRIBUTED`
- `NO_CONFIRMED_SURGE`

A price jump by itself is not accumulation. A physical surge can coexist with short covering or mixed speculative positioning.

## Top states

- `EARLY_TOP_RISK_ONLY`
- `EXHAUSTION_RISK`
- `DISTRIBUTION_TOP_CONFIRMED`
- `NO_TOP_EVIDENCE`

Crowding, overbought readings or a high RSI can never confirm a top. Confirmation requires all of:

- failed high or negative post-breakout follow-through;
- signed selling, long liquidation, short building or bearish repositioning;
- weakening curve, basis, inventory or other market-specific fundamental evidence.

## Market contracts

### Commodities

Required evidence families:

- disaggregated COT/TFF participant long and short changes;
- inventory and inventory surprises;
- futures curve/backwardation;
- physical basis or cash premium;
- shipping, storage and logistics constraints;
- options only where reliable signed/provenance-aware data exist.

Weekly COT is a state confirmation layer, not an intraday trigger and not proof that traders knew a war would occur.

### US stocks and ETFs

- signed or settled flow;
- point-in-time earnings/revenue revisions;
- ETF creation/redemption or verified flow;
- borrow demand/fee and lendable supply;
- next-day settled option OI and signed option flow where licensed;
- buyback/insider data with correct filing lag.

Raw volume, ownership level and gross option OI are not owner identity or intent.

### IHSG / IDX

- broker inventory persistence;
- foreign net flow;
- crossing/negotiated-trade adjustment;
- controller and free-float structure;
- broker reclassification risk;
- futures where applicable.

No direct options-gamma claims are created for IHSG.

### FX

- TFF leveraged-fund and asset-manager changes;
- policy-path surprise;
- cross-currency basis/funding pressure;
- risk reversal and volatility surface where liquid;
- reserve/intervention context;
- terms-of-trade and external-funding mismatch.

### Crypto

- venue-specific price and OI;
- aggressor flow;
- liquidation imbalance;
- funding and basis;
- exchange netflow and stablecoin impulse;
- unlock/supply events;
- on-chain demand where causal and point-in-time.

Price × OI remains ambiguous unless aggressor or liquidation data resolve the initiating side.

## Live integration policy

- Lifecycle is surfaced in per-ticker data, ranking rows and final desk diagnostics.
- Surge is computed before row serialization.
- Surge and lifecycle have **zero ranking weight**.
- Missing remains missing; no neutral `0.5` or fallback `50` is interpreted as observed evidence.
- Every lifecycle output carries:
  - `proof_state = NOT_PROVEN`
  - `live_decision_weight = 0.0`
  - `capital_permission = BLOCKED`

## Promotion protocol

Promotion requires a separate frozen protocol per market, state and horizon:

1. exact input lineage and publication lag;
2. pre-registered state rules and thresholds;
3. simple baseline and current War Room baseline;
4. walk-forward validation and untouched lockbox;
5. global multiple-testing correction;
6. calibration, false-alarm rate and useful lead time;
7. MAE, MFE, remaining return and invalidation behavior;
8. no-retuning replication across eras/assets;
9. prospective evidence;
10. only then non-zero live weight.

V5.9 implements the measurement and wiring layer needed for those tests. It does not claim the forward edge has passed them.

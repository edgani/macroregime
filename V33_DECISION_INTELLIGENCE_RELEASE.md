# War Room OS v3.3 — Decision Intelligence Release

## Design verdict

The v3.2 information architecture was directionally correct, but its graph-first default
did not maximize decision output. Large canvases delayed the answer to the questions a
trader actually needs: what state is this, which side is favored, what is missing, where
is the trigger, and what invalidates the path.

v3.3 therefore makes the decision board the default and retains maps as drill-downs.
This increases useful information density without deleting causal lineage.

## Main changes

### 1. Explicit pair-specific FX

FX no longer stops at `SPOT LIVE / MACRO INCOMPLETE`. Every pair has:

- explicit `LONG`, `SHORT`, `NEUTRAL` or `BLOCKED` orientation;
- action state;
- driver coverage;
- trigger and trade invalidation;
- event-risk downgrade;
- reason and freshness.

No aggregate FX call is permitted. Price-only context can never trigger.

### 2. Board / Map / Evidence

- **Board**: daily operating surface.
- **Map**: causal and flow path.
- **Evidence**: doctrine, uncertainty, failure piles and falsification.

The generic research dock is hidden in Board mode so screen space is reserved for
market-specific decisions and current structural changes.

### 3. Crypto structural radar

Crypto now tracks more than spot/perps:

- Robinhood/brokerage and DeFi convergence;
- tokenized securities and collateral;
- stablecoin policy, reserves, distribution and velocity;
- prediction-market licenses, clearing and liquidity;
- protocol revenue and token value capture;
- developer adoption;
- agentic execution and smart-contract/model risk;
- regulatory asset classification;
- unlocks, market makers and fragmented liquidity.

These are research categories, not automatic token recommendations.

### 4. Official-source radar

Official pages are hashed on a bounded cadence. Changes are labeled
`CHANGED_UNREVIEWED` and require human review before entering the dated inventory.
The system cannot guarantee that every future development is captured, but it makes
source coverage, freshness and review debt visible instead of silently using stale lore.

### 5. Alpha overclaim removed

The visual no longer displays fabricated 50–500x numeric headroom as if it were a target.
Numeric upside classes remain withheld until point-in-time value capture, dilution,
probability, pricing and remaining-return models exist.

## Tested operational contracts

- v3.3 decision/UI contract;
- pair-specific FX long/short/event-risk semantics;
- primary-source inventory and freshness;
- arrow lineage;
- live-stack parser fixtures and stale failover;
- GCFIS synthetic correctness;
- browser BOARD/MAP/EVIDENCE behavior;
- real Streamlit health startup;
- fail-closed capital permission.

## Proof boundary

This release is ready for operational user review. It does not claim that all trading
components have passed point-in-time WFA, untouched lockbox or mature prospective
validation. Capital remains blocked.

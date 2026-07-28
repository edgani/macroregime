# V6.2 Mechanism Gap Audit

## Scope

This continuation starts from the exact V6.0 package SHA-256:
`72fa075da84be8fbbab233eb9a30a8f07270cd67ff005a44b9adcd31fe69a5e3`.

It does not reset the V6.0 global trial ledger, does not promote any historical aggregate factor return, and does not give a live weight to new diagnostics.

## What V6.0 had not outcome-tested

1. **True production-network diffusion.** V6.0 contained causal mapping, but no dated customer-supplier graph. V6.1 tests whether price-derived peer networks can substitute for that missing graph.
2. **Discrete event underreaction.** Rolling gap and volume averages existed, but there was no frozen battery centered on recent discrete gap-volume impulses, hold/fade, and post-event underreaction.
3. **Point-in-time SEC accounting origins.** Filing-date availability, accession identity, amendments, duration normalization, and quarterly flow reconstruction were not implemented.
4. **Point-in-time expectations.** Analyst consensus, dispersion, revision breadth/velocity, and guidance deltas remain absent.
5. **Position scarcity.** Public short interest does not supply borrow fee, utilization, lendable supply, recalls, and locate constraints.
6. **Signed option inventory.** Gross option OI cannot identify customer/dealer buy/sell and open/close activity.
7. **IHSG inventory history.** Current broker summary is not a crossing-adjusted historical ticker-by-broker inventory panel.
8. **Venue-complete crypto leverage.** A venue API can expose OI and liquidation flags, but cross-venue historical snapshots are not bundled.

## New falsification batteries

### V6.1 Price-derived network diffusion

- Network fit is restricted to the discovery period.
- Agglomerative correlation clusters: 24 and 48 groups.
- Top-20 correlation-weighted neighbor network.
- Candidate states include peer return, breadth, acceleration, breakout share, volume wake, follower gap, and network residual.
- 1,506 candidates × 4 targets = 6,024 claims.
- Benchmarks: directional 12-1 momentum and ATR63.
- Promotion requires adjusted lower bound > 0 in validation and lockbox against both benchmarks.

**Result: 0 diagnostic survivors; 0 production survivors.**

The best raw pattern combined 63-day peer breakout breadth with high ATR. It materially beat momentum in 2016, but did not beat ATR and its simultaneous lower bound remained negative in the lockbox. This rejects generic price-correlation networks as a universal early-move detector. It does not reject a properly dated economic customer-supplier network.

### V6.2 Discrete event-origin proxy

- Positive/negative overnight gap z-scores.
- Abnormal-volume interaction.
- Event-day close location.
- Rolling event maximum, sum, and exponential decay.
- Gap directional persistence.
- Event-volume persistence.
- Gap hold and fill/fade pressure.
- Interaction with momentum, ATR, compression, volume persistence, range location, and distance from high.
- 2,664 candidates × 4 targets = 10,656 claims.
- Same validation, lockbox, benchmarks, multiplicity correction, corporate-action guard, and fail-closed live weight.

**Result: 0 diagnostic survivors; 0 production survivors.** The exact best candidate and lower bounds are recorded in `V62_RESEARCH_EVIDENCE_REGISTRY.json`. No result receives live weight because the proxy lacks event identity and point-in-time fundamental/expectation data.

## Point-in-time SEC pipeline added

`research_v62/code/build_sec_pit_fact_ledger.py`

- Consumes official local SEC `companyfacts.zip` and SEC ticker mapping.
- Records filing date, accession, form, fiscal period, fact tag, unit, start/end dates, and amendment status.
- Uses filing date as the first availability date.
- Does not use period end as availability.
- Keeps amendments distinguishable.

`research_v62/code/build_sec_pit_quarterly_features.py`

- Conservative quarterly-duration guard for flow facts.
- Revenue, gross profit, operating income, net income, inventory, capex, shares, debt, cash, and equity families.
- QoQ/YoY changes, gross/operating margin changes, inventory-versus-revenue gap, and share-supply change.
- No feature may appear before its filing date.

Synthetic pipeline validation: **5/5 PASS**.

Actual SEC bulk data were not acquired in this restricted runtime. Therefore no market result from SEC fundamentals is claimed.

## Claim limits

- A gap-volume event proxy is not an earnings surprise.
- A correlation cluster is not a customer-supplier network.
- Total OI is not directional inventory.
- Liquidation is usually a transmission observation, not necessarily the causal origin.
- Historical maintained factor portfolios are not point-in-time ticker-selection proof.
- Synthetic controls validate the harness, not market profitability.

## Research direction after V6.2

The highest-value unresolved test is a joined point-in-time panel:

`SEC filing origin + analyst expectation gap + customer/supplier qualification + pricing/capacity + borrow scarcity + signed options/flow + future remaining return`.

No substitute proxy is allowed to inherit the claim of a missing source.

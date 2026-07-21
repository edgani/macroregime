# War Room OS — Research-First Decision OS v3.2

This is the canonical integrated release built from `War_Room_OS_Decision_First_v2_9`.
It replaces the flat navigation with eight decision workspaces and embeds the same
research discipline into US stocks, IHSG, crypto, commodities and FX.

## Eight workspaces

1. **Mission** — You Are Here, Current Rain, recognition gap and decision queue.
2. **Regime & Risk** — macro nowcast, liquidity plumbing, credit and risk propagation.
3. **Opportunities** — structural asymmetry and company research inventory.
4. **Markets** — US, IHSG, crypto, commodities and FX adapters.
5. **Flow & Positioning** — cross-asset flow, options, TRF/dark pool, filings, broker routes and on-chain events.
6. **Causal Map** — supply chains, chokepoints, value capture and winner genealogy.
7. **Execution & Portfolio** — trigger, trade invalidation, thesis invalidation, exit state and capital gate.
8. **Research & Validation** — Study the Tape, prediction log, baseline, ablation, failure review and data lineage.

## Non-negotiable semantics

- Missing or stale feed never becomes a live claim.
- Observed, inferred, structural and unknown evidence remain distinct.
- Broker routes do not reveal beneficial owner or intent.
- Options prints, dark-pool prints and whale transfers are context, not automatic direction.
- Theme conviction is not probability.
- Hand-authored market-cap multiples are not accepted as EV, price targets or sizing.
- IHSG is cash long-only.
- A triggered watch is not an order.
- Engineering PASS does not prove predictive alpha.
- Capital permission remains `CAPITAL_BLOCKED` until market-specific point-in-time WFA,
  lockbox and prospective evidence earn promotion.

## Run locally on Windows

Double-click:

```text
CHECK_AND_RUN.bat
```

The script creates `.venv`, installs missing dependencies, runs the canonical release
validator and starts Streamlit only if the release checks pass.

To run without repeating the full validation:

```text
RUN_WARROOM.bat
```

## Canonical validation

```bash
python validate_release_v32.py
```

A passing report means the application is operationally ready for review. It does not
mean every component is profitable or proven. See `V32_RELEASE_VALIDATION_REPORT.json`.

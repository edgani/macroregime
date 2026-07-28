# War Room OS V10.1 Operator Guide

## First run

1. Extract the ZIP into a new folder.
2. Run `SETUP_V101.bat`.
3. Run `REFRESH_V101_NOW.bat`.
4. Run `RUN_V101_APP.bat`.

## Reading Carry Trade

Open **Macro & Risk** for the global carry map or **FX** for a pair-specific packet.

- **Funding currency**: lower-yield currency being borrowed/sold.
- **Target currency**: higher-yield currency or assets being owned.
- **Carry direction**: expression implied by the differential.
- **Current direction**: carry direction, de-risk instruction, or unwind direction after stress/crowding checks.
- **Stage**: dormant, early/mixed, active, late/crowded, exit warning, or active unwind.
- **Beneficiaries**: direct FX/local-bond/liquid-asset recipients and conditional secondary beneficiaries.
- **At risk**: assets vulnerable if the funding currency is bought back during deleveraging.
- **Confidence cap**: reduced when forward/basis, external balance, positioning or point-in-time history is missing.

CFTC positioning is release-lagged. Current policy pages and current-vintage macro data support research state only; they are not historical proof.

## Trading permissions

- **Research Action** may display current direction.
- **Shadow Trading** requires a fresh quote, valid ticker-bound projection and fixed risk gate.
- **Systematic Live** requires exact historical and prospective proof; it cannot be enabled by an environment flag.
- Broker auto-submit is off.

## Proof workflow

Complete `V101_CARRY_HISTORY_TEMPLATE.csv`, then drag it onto `PREPARE_V101_CARRY_PROOF.bat`. The output is only a candidate-return matrix. Continue through the V9.6 lifecycle, seal, anti-overfit and prospective-fill gates described in `V101_CARRY_PROOF_PLAN.md`.

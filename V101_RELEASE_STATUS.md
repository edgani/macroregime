# War Room OS V10.1 Release Status

## Delivered

- Causal carry-trade state machine for 11 FX references.
- Funding currency, target currency, carry direction, current direction, stage, crowding and unwind classification.
- Direct/secondary beneficiaries, unwind winners/losers, transmission path and invalidation.
- Current policy-rate collection for major currencies, plus official BI and SNB current-rate routes.
- Release-lagged CFTC positioning admission.
- Carry output integrated into Macro & Risk, Mission Control and the FX ticker decision packet.
- Point-in-time carry panel admission and registered three-candidate proof family.
- Look-ahead, final-revised evidence, incomplete trial family and capital promotion without proof remain blocked.

## Validation

V10.1 software/state/proof-firewall validation: 55/55 PASS.

## Proof status

Carry alpha is **NOT_PROVEN**. The package does not contain a fabricated point-in-time historical panel, untouched future lockbox, prospective outcomes or actual account fills. Systematic live remains `PROOF_GATED`.

The useful current output is the carry map: direction, beneficiaries, crowding, unwind risk and invalidation. This output can be recorded prospectively in shadow mode while proof accumulates.

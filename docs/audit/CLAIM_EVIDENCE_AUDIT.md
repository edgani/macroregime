# Claim Evidence Audit — Phase 5 (WriteVerso failure-mode audit)

Reference failure modes: https://www.writeverso.now/p/quant (12 modes).
Every claim below was located, its exact evidence read, and an honest terminal
label assigned. No claim keeps PROVEN merely because code or a past report says so.

## Evidence labels used

- RECONSTRUCTED_HISTORICAL_EVIDENCE — historical association reconstructed in-sample; NOT forecasting evidence
- HISTORICALLY_VALIDATED_OOS — historical out-of-sample / lockbox / WFA support, still not prospective
- CONDITIONAL — usable only inside stated scope/limits
- REJECTED — definitive negative result (acceptable terminal state)
- PROSPECTIVE_EVIDENCE_PENDING — implemented, awaiting sealed future observations
- PROSPECTIVELY_VALIDATED — (none in this repo)

## Claim-by-claim adjudication

### 1. US_BROAD_EQUITY_SMA10_LONG_CASH_V79 — monthly long/cash broad-US-equity sleeve
- Evidence: `research_v66/results/V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json`
  (passed=true, 12/12 gates: drawdown, expected-shortfall, return, up/down capture,
  bootstrap DD/ES, rolling DD/ES/ret, reverse-control-fails, 25bps cost confirmatory),
  protocol hash `7a4a91c8…`; V83 lockbox familywise@25bps pass; `WHAT_IS_AND_IS_NOT_PROVEN.md`.
- WriteVerso findings:
  - (3) MEMORIZED PUBLIC RELATIONSHIP: SMA-10-month timing is Faber (2007), one of the most
    published rules in existence. Selection was not blind. Applies in full.
  - (1) Outcome knowledge: the long-history result (survivor_count=0 in
    V66_LONG_HISTORY_EQUITY_RISK_GATE) means variants WERE tried and failed; the survivor is
    documented, so hidden-failed-variant risk is partially mitigated by the published ledgers.
  - (7) Cherry-picking: partially mitigated — reverse control + rolling + bootstrap gates all
    ran and passed, and the failed long-history variant is on record.
  - (10) Backtest reconstruction presented as forecasting: RISK — the claim text correctly
    limits itself to "historical drawdown and left-tail reduction". Acceptable only under
    that claim ceiling.
- Label: **HISTORICALLY_VALIDATED_OOS** for the narrow claim "historical DD/left-tail
  reduction of the frozen monthly rule at tested costs". Capital: BLOCKED (V83:
  real_trade_profit_factor FAIL_MISSING_TRADE_LEDGER; V84 contamination controls failed).
  Prospective profitability: **PROSPECTIVE_EVIDENCE_PENDING**.

### 2. V64 factor claims — AnalystRevision, AnnouncementReturn, DivYieldST
- Evidence: `research_v64/ledgers/V64_PROVEN_CLAIM_LEDGER.csv` (3 rows,
  proof_scope=HISTORICAL_GROSS_MARKET_CLAIM_PROVEN; modern=False, lockbox=False,
  capital=BLOCKED); scoped ledger: flat_10bp_hurdle pass, flat_25bp FAIL.
- WriteVerso: (3) memorized public relationship — all three are textbook published factors;
  (5/6) factor/threshold mining mitigated by frozen protocols + trial ledgers;
  (10) gross historical association only, decays under realistic costs (25bp fail).
- Label: **RECONSTRUCTED_HISTORICAL_EVIDENCE** (gross, in-sample-era, no net survivability).

### 3. V64 SmileSlope — MODERN_ALL_STOCK_AGGREGATE_GROSS_CLAIM_SUPPORTED
- Evidence: scoped ledger row 4: modern gross supported, but investable=False, lockbox=False,
  10bp hurdle FAIL. Label: **RECONSTRUCTED_HISTORICAL_EVIDENCE** (aggregate gross only).

### 4. Cusp fragility / Crash Meter family (V73, V74, V75)
- Evidence: `research_v57/results/V73_CUSP_HISTORICAL_RESULTS.json` verdict=NOT_PROVEN
  (4-point improvement gate fail, simultaneous adjusted lower bounds fail);
  V74 lockbox zero positive events; V75 disjoint gate fail; registry:
  `crash_meter_inclusion=REJECTED`; sequential stop honored (decision test NOT_RUN).
- This is a model example of honest negative documentation: frozen protocols, placebo
  controls (shift60/shuffle fail-to-pass), and a recorded stop.
- Label: **REJECTED** (definitive, well-evidenced negative). Crash Meter calibration:
  REJECTED as predictive component; retained only as descriptive context with zero weight.

### 5. V66 long-history equity risk gate (1871–2023, 1829 months)
- Evidence: survivor_count=0. Label: **REJECTED** (no variant survived full history).

### 6. V78 proof expansion (US vol12 risk cap, cross-market SMA10, cross-market TSMOM)
- Evidence: `V78_US_EQUITY_VOL12_RISK_CAP_RESULTS.json` status=NOT_PROMOTED (and siblings).
- Label: **REJECTED** for promotion; retained as research record.

### 7. V82/V83 FULL_CAUSAL_POSITIONED archive factor portfolio
- Evidence: V83 capital BLOCKED (no real trade ledger, validation familywise fail);
  **V84 confirmatory proof REVOKED** — LLM-memory contamination, incomplete global trial
  ledger, no post-model-cutoff holdout, no independent data custodian, causal grouping not
  incremental vs naive equal weight.
- Label: **REJECTED** as confirmatory proof; numeric stability may remain exploratory only.

### 8. Carry-trade engine V101 (`carry_trade_engine_v101.py`)
- Code labels itself `proof_state:'NOT_PROVEN'` with claim_limit requiring PIT historical +
  prospective proof. Functional in offline desk build. No validation study exists.
- Label: **PROSPECTIVE_EVIDENCE_PENDING**.

### 9. Quad transition / Chain Reaction / Bottleneck / Alpha Center / Timing / directional alpha
- Production surfaces carry `UNPROVEN_CURRENT_RESEARCH_BRIDGE`, `NOT_PROVEN`,
  `RESEARCH_CONTEXT_AVAILABLE_VALUE_BRIDGE_NOT_PROVEN`, `DESCRIPTIVE_ONLY` claim ceilings.
  No completed validation study found for any of these as predictive components.
- WriteVerso (12) LLM judgment replacing frozen falsifiable rules: these modules are
  heuristic narratives; they are NOT wired to capital (no_technical_policy gate +
  proof gates block them). Acceptable as descriptive UI, prohibited as evidence.
- Label: **PROSPECTIVE_EVIDENCE_PENDING** (descriptive-only until a frozen protocol study).

### 10. Options-derived outputs (v70 gamma, v71 prospective ledger, v72 signed dealer)
- Hardening evidence: capital_permission=BLOCKED enforced (expected and verified).
- Label: **CONDITIONAL** — infrastructure verified fail-closed; signals themselves
  PROSPECTIVE_EVIDENCE_PENDING.

## Production-claim sweep

Grep over all non-archive .py/.json/.md for PROVEN/production-ready/trading-ready/calibrated:
no inflated claims in production code. All predictive surfaces self-label NOT_PROVEN /
UNPROVEN / DESCRIPTIVE_ONLY. The single "Proven and decision-active" document claim is item 1,
downgraded here from "Proven" to HISTORICALLY_VALIDATED_OOS + PROSPECTIVE_EVIDENCE_PENDING
for capital purposes — consistent with its own V83/V84 blockers.

## Global WriteVerso notes

- (8) Repeated lockbox reuse: V83 reports lockbox familywise pass but validation familywise
  FAIL — evidence of selection pressure reaching the lockbox. Treated as contamination signal.
- (9) Hidden failed variants: mitigated better than typical — research_v5x–v8x keep frozen
  protocols, trial ledgers, and explicit NOT_PROVEN/REVOKED verdicts.
- (11) Correlation vs causality: causal grouping found NOT incremental vs naive equal weight
  (V84). No causal claim survives.
- (12) LLM judgment: V84 confirms LLM-contamination controls failed for the factor portfolio;
  this audit inherits that caution for every historical claim above.

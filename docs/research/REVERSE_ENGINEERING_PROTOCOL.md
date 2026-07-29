# Reverse-Engineering Protocol — Attachment Verdict (R10, 2026-07-29)

Assessment of the operator's "Reverse-Engineering Market Intelligence Agent"
mandate against the War Room architecture. Verdicts are per-layer: ADOPTED,
PARTIAL, REJECTED (with reason), or UNSUPPORTED (untestable with our data).

Operator constraints applied:
1. NO technical indicators in the War Room (no MA/RSI/MACD/chart-pattern
   signals or baselines built for entries).
2. Orderflow is out of scope here — it will be built in a separate system.

## Layer verdicts

| Attachment layer | Verdict | Reason / disposition |
|---|---|---|
| Mission discipline (falsify, label, OOS-or-reject) | ADOPTED | Already the War Room core doctrine (V84/V85, claim ladder, terminal labels). Vocabulary adopted: unsupported / rejected / candidate only / deployable. |
| L0 surface behavior (trend/range/compression from charts) | REJECTED | Chart-pattern reading = technical indicator territory; operator constraint. State estimation uses quantitative estimators only. |
| L1 price/volume/vol/time interactions | PARTIAL | Volatility estimation ADOPTED as statistics (warroom/research/vol_proxy.py). Volume-structure and session/cycle effects: candidate only, unproven, no data pipeline yet. |
| L2 orderflow & liquidity | OUT OF SCOPE | Operator decision: separate system. Nothing built here. |
| L3 options regime | PARTIAL (PROXY) | No options chain data source exists. vol_proxy.py provides expected move / extreme band / vol regime / squeeze risk, labeled PROXY_REALIZED_VOL_NO_OPTIONS_DATA. Implied vol, skew, gamma, dealer positioning, pinning: NOT MEASURABLE — listed explicitly in every output. Adding a real options feed is future work (candidate: Yahoo v7 options endpoint, unverified). |
| L4 dark pool / off-exchange | UNSUPPORTED | No data source; claims untestable. Not built. |
| L5 macro regime | ADOPTED (pre-existing) | current_context_v101 collectors (policy rates, yields, FRED path, CFTC). Live-verified 2026-07-29. |
| L6 cross-asset positioning | ADOPTED (pre-existing) | CFTC positioning collector live; vol-targeting/risk-parity/CTA inference remains candidate only. |
| L7 quantitative modeling (WF, purge/embargo, lockbox, MC, permutation, bootstrap) | PARTIAL | Purged walk-forward + embargo + lockbox pre-existing (warroom/research/walkforward.py). Monte Carlo / permutation / bootstrap exist in archived research, not in the active engine — future work if a signal reaches validation. |
| Manipulation / front-running detection | UNSUPPORTED | Not measurable with current data. Any such claim = candidate only, never deployable. |
| Behavior classification by intent | PARTIAL | Persistence/size/regime confirmation required by doctrine; no intent classifier built. Candidate only. |

## Required tests mapping

Already enforced in the active engine: no-look-ahead (chronology-validated
ledger), leakage (pre-registered artifact manifests), overlap/embargo
(walkforward.py), selection/trial counting (trial_counter.py), contamination
(contamination_gates.py), walk-forward + lockbox (walkforward.py).

Required before any signal promotion, currently future work: permutation
test, bootstrap CI, Monte Carlo stress, parameter sensitivity harness in the
active engine (they exist in archived research; porting = R11 candidate).

## Acceptance rule (binding)

Any new signal or policy change follows this exact order, enforced by code:

1. Register the trial in warroom/research/trial_counter.py (fail-closed:
   shadow_runner refuses unregistered trials).
2. Falsify (regime splits, costs, parameter perturbation) with results in the
   trial ledger entry.
3. OOS via purged walk-forward + lockbox.
4. Label: unsupported / rejected / candidate only / deployable.
5. deployable requires: contamination shadow tier pass + prospective shadow
   evidence (>=30 matured observations) + capital-tier gates for any capital
   discussion.

## What was added under this protocol (R10)

| Item | Path | Status |
|---|---|---|
| Options-free volatility layer (proxy-labeled) | warroom/research/vol_proxy.py | VERIFIED (tests) |
| Operator status CLI | tools/warroom_status.py | VERIFIED (tests + live) |
| This verdict document | docs/research/REVERSE_ENGINEERING_PROTOCOL.md | committed |

## What was deliberately NOT added

- Orderflow / liquidity-sweep / stop-hunt detection (operator scope decision).
- Dark pool analytics (no data — unsupported).
- Any technical-indicator signal or entry baseline (operator constraint).
- Any intent classifier claiming manipulation detection (unsupported).
- Any unlabeled proxy presented as truth.

## Addendum R11 — operator article verdicts (2026-07-29)

Article A ("OBBB + FOMC", Indonesian market letter, ~Aug 2025): MOSTLY ADOPTED.
- Facts verified against FRED: OBBB deficit math, Jul-2025 hold 4.25-4.50%,
  Waller+Bowman dissent, Q2'25 GDP 3.0% with weak final sales — accurate.
  Its cut prediction validated ex-post (DFF 3.63 by 2026-07-29).
- ADOPTED: (1) fiscal-liquidity channel as macro input (deficit/issuance
  series backlog: FYFSD, GFDEBTN) — mechanism is fiscal, NOT QE, the article's
  framing is corrected; (2) priced-vs-surprise principle -> policy expectation
  gap proxy DGS2-DFF (data already collected); (3) JPY carry funding US
  refinancing -> strengthens existing carry_trade_engine_v101 inputs.
- REJECTED: "UST 2Y issuance signals 0% by 2027" (weak inference), "10-year x
  100-year cycle crossing 2027" (numerology), conspiracy framing (unfalsifiable).

Article B ("History rhymes: years ending 00-01 / 07-08"): REJECTED as signal.
- Selection bias, multiple comparisons across 10 year-digit buckets, ad-hoc
  reclassification (1914->1917, 1929 counted as 27-28), and the author himself
  lists 1974-75 as a break. The NBER base rate (recession every ~6-7y) explains
  the "2027-2029 crisis" hit rate without numerology. Fails
  parameter-perturbation falsification by construction.
- KEPT (data-driven rebuild, not narrative): (1) crisis-episode database
  computed from SP500 history (all >=15% drawdown episodes: start, trough,
  depth, duration, recovery) -> crash-meter calibration reference;
  (2) Sep/Oct seasonality -> candidate only, requires a registered trial;
  (3) debt-crisis-2027+ thesis -> Bayesian scenario (Estimate) in the macro
  investigation, never a date.

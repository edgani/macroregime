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

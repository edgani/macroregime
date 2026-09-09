# Attachment Prompt Implementation Checklist — v3.2

Status meanings: **IMPLEMENTED**, **PRESERVED**, **GATED/PARTIAL**. GATED means the software path exists but the required PIT/live dataset is not bundled and the system refuses to fabricate it.

| Requirement | Status | Implementation |
|---|---|---|
| Automatic opportunity discovery | IMPLEMENTED | current multi-market universe auto-scans; meaningful detections freeze events |
| Economic transmission chain | IMPLEMENTED | driver → first order → second order → bottleneck → beneficiary → revenue/margin → catalyst/invalidation |
| Opportunity archetypes | IMPLEMENTED | multi-label classification |
| Immutable opportunity event | IMPLEMENTED | `opportunity_events`; first detection does not mutate |
| Relevant macro context at detection | IMPLEMENTED | frozen `macro_context_json` reuses existing macro engine |
| Fundamental level + change | IMPLEMENTED/PRESERVED | existing fundamentals + new event snapshot |
| Expectation / pricing state | IMPLEMENTED/PRESERVED | valuation gap + expectation state; missing data = UNKNOWN |
| Information vs price response | GATED/PARTIAL | schema/context ready; exact event-response requires timestamped event data |
| Bottleneck analysis | IMPLEMENTED | explicit causal bottleneck; unavailable physical evidence remains gated |
| Beneficiary mapping | IMPLEMENTED/PRESERVED | causal graph + theme exposure mapping + event beneficiary |
| Quality of exposure | IMPLEMENTED | capture, revenue/margin sensitivity, balance sheet, capital intensity, execution, valuation risk components |
| Opportunity score + components | IMPLEMENTED | transparent configurable research components; not a probability |
| Asymmetry | IMPLEMENTED/PRESERVED | bull/base/bear valuation cases where supported + expected upside/downside/asymmetry ratio |
| First detection memory | IMPLEMENTED | first seen / unusual / high conviction timestamps and prices |
| Lifecycle | IMPLEMENTED | discovered → emerging → proving → high conviction → pricing in → mature/crowded/invalidated/resolved |
| Persistent watching | IMPLEMENTED | SQLite watch registry survives restart |
| Outcome memory | IMPLEMENTED | 1D, 3D, 1W, 2W, 1M, 3M, 6M, 12M |
| Relative outcomes | IMPLEMENTED | benchmark/sector alpha fields; sector values remain missing when no real benchmark is available |
| Success definitions | IMPLEMENTED | +10/-5, +20/-10, +50/-15 barrier ordering stored from realized path |
| Time-to-thesis | IMPLEMENTED/PARTIAL | time-to-MFE/MAE/peak + barrier times; exact time-to-catalyst needs timestamped catalyst feed |
| False-positive learning | IMPLEMENTED | explicit failure taxonomy and retained invalidated events |
| Missed-winner analysis | IMPLEMENTED, DATA-EMPTY ON FRESH INSTALL | dedicated PIT-safe audit store; no hindsight backfill |
| Runner classes | IMPLEMENTED/PARTIAL | peak/path data stored; user can derive +25/+50/+100/+200/+500 classes without contaminating detection |
| Opportunity learning | IMPLEMENTED | pattern at t → completed outcome → expectancy tables |
| No self-modifying production logic | IMPLEMENTED | learning never rewrites production weights |
| Sample size / shrinkage | IMPLEMENTED | sample confidence + transparent parent shrinkage |
| Regime-specific learning | IMPLEMENTED | regime grouping from frozen macro context |
| Country / market conditioning | IMPLEMENTED | market hierarchy; HK/China/Europe/Taiwan contracts added |
| Catalyst learning | PARTIAL | catalyst stored; full pre/post catalyst statistics need mature timestamped catalyst history |
| Earnings learning | PRESERVED/PARTIAL | earnings/revision fields exist; long PIT history remains a data gate |
| Cross-asset confirmation | PRESERVED | existing causal/scenario engine; not made a mandatory correlation checklist |
| Causal family performance | IMPLEMENTED | theme-level expectancy tables |
| Opportunity clustering | IMPLEMENTED | theme cluster + best/second/alternative expression UI |
| Best expression logic | IMPLEMENTED/PRESERVED | cluster ranking + existing instrument expression engine |
| Cross-instrument expression | PRESERVED | stock/spot/leverage/options remain separate from thesis |
| Options context | PRESERVED | existing IV/skew/liquidity/catalyst gates; no options-only directional claim |
| True walk-forward | IMPLEMENTED | expanding chronological test; no shuffle |
| Point-in-time discipline | IMPLEMENTED/PRESERVED | event snapshots immutable; missing historical PIT features remain unavailable |
| Survivorship bias | GATED/PARTIAL | architecture allows dead/delisted events; full historical dead-universe dataset not bundled |
| Baselines | IMPLEMENTED, SOME DATA-GATED | current engine measured; PIT baselines refuse to fabricate unavailable historical features |
| Metrics | IMPLEMENTED/PARTIAL | continuous outcomes + path metrics; aggregate metrics appear after mature sample |
| Ranking output | IMPLEMENTED | radar + first seen + states + component scores + data quality |
| Opportunity detail UI | IMPLEMENTED | dense reference-style detail / causal / memory / feed layout |
| Active events | IMPLEMENTED | persistent active lifecycle registry |
| Alerts | IMPLEMENTED | deduplicated state/event alerts in local proof tape |
| Daily / weekly learning report | IMPLEMENTED | markdown reports generated from stored evidence only |
| Shared macro memory | IMPLEMENTED | reuses existing macro engine; does not duplicate macro DB |
| Crash/risk overlay | PRESERVED | macro risk is context, not universal suppressor |
| Explainable learning | IMPLEMENTED | sample N, outcomes, shrink parent, confidence, failure store |
| No autotrading | IMPLEMENTED | no order/private-key/broker execution added |
| Acceptance tests | IMPLEMENTED | original regressions + 20/20 v3.2 structural acceptance |
| Complete updated project | IMPLEMENTED | additive v3.2 package with run instructions/changelog/tests |

## Remaining data risks

The largest unresolved risk is **data completeness**, not missing code: full PIT analyst/ownership/corporate-action history, dead/delisted universes, broad exchange enumeration, physical commodity datasets, FX positioning/BoP/REER, and timestamped catalyst histories. v3.2 deliberately shows these as gated rather than using price momentum as a substitute.

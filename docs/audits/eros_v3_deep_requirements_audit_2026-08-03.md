# EROS v3 Deep Requirements Audit

**Audit date:** 2026-08-03
**Repository:** `macroregime`
**Branch:** `main`
**Public application:** `https://edgani.streamlit.app/`

## Executive verdict

EROS v3 is **not complete and not production-ready** against either the Kimi design context or `EROS_v3_FINAL_MASTER_PROMPT.pdf`.

The repository has a sound fail-closed shell, typed contracts, five Streamlit tabs, public benchmark monitoring, and explicit uncertainty labels. It does not yet have the required causal data system, validated BCM implementation, global opportunity discovery/ranking engine, portfolio allocation engine, point-in-time research pipeline, or proof center.

The public application opens all five tabs, but several tabs are primarily registries, static fixtures, or empty-state placeholders. Rendering a tab is not equivalent to satisfying its product contract.

## Authoritative sources inspected

1. `[private external master prompt PDF]` — 40 pages, extracted and read directly.
2. `[private Kimi design transcript]` — design and research conversation.
3. `[private BCM reference image]` — BCM GFC visual baseline.
4. Current `main` source code and configuration.
5. Backup branch `backup/pre-eros-v3-redesign-20260802-230549` legacy artifacts restored locally for inspection.
6. Public Streamlit deployment, inspected across all five tabs.

## Critical contradictions

### 1. Command Center price charts violate the master PDF

The PDF requires:

- Command Center to answer “What changed, what matters, and what should I do?”
- “No price chart and no technical overlay on Command Center.”
- Historical prices only in Proof/Outcome views without technical overlays.

Current implementation renders `LIVE 5-DAY MARKET PATHS` in Command Center. Although labelled monitoring-only, its placement violates the explicit UI contract. It should move to an Explorer or Proof/Outcome surface.

### 2. Legacy Crashmeter data is not BCM v3.2 evidence

The local dataset contains the article-style Crashmeter fields:

- `t10y3m`
- `hy_oas`
- `cape`
- binary `a1`, `a2`, `b1`, `b2`, `c`
- integer `score`

This is not the required continuous BCM stress/fragility system described in the Kimi research context. The PDF explicitly classifies BCM as a legacy candidate with scope limitations and requires exact replication from raw sources before promotion.

The current local Research Lab title `LEGACY BCM SCORE TIMELINE` is therefore misleading. It must be renamed to `LEGACY CRASHMETER V3 SCORE TIMELINE` unless an actual BCM dataset and replication report are supplied.

### 3. Public benchmark data is presented over a synthetic causal state

`build_public_data_state()` overlays public benchmark observations on `demo_dashboard.json`, whose causal dimensions, theses, scenarios, and acceptance gates are frozen synthetic fixtures. The public price data does not update causal regime, opportunities, or portfolio decisions.

This behavior is safe but means the application is a monitoring shell, not a live economic reasoning system.

## Data completeness audit

### Public benchmark contract

The public adapter expects 12 symbols across six groups:

| Group | Expected symbols | Current purpose |
|---|---:|---|
| US | 2 | Public benchmark monitoring |
| IHSG | 1 | Public benchmark monitoring |
| Crypto | 2 | Public spot snapshot monitoring |
| FX | 3 | ECB reference-level monitoring |
| Commodities | 2 | Public futures benchmark monitoring |
| Rates & Volatility | 2 | DGS10 and VIX monitoring |

The latest public deployment showed 11 observations and 5/6 complete groups. `FRED rates` failed, leaving `DGS10` unavailable while VIX remained available.

**Important:** `5/6` measures benchmark-group completeness only. It is not the health of all EROS data and must not be interpreted as 83% production readiness.

### Universe registry versus actual data

- 15 markets are registered.
- 19 asset classes are registered.
- Only the United States and Indonesia have a live country-level benchmark observation in the public Explorer.
- The other 13 markets are `DATA_DEBT`.
- Public Explorer reports 5 asset classes observed and 14 unknown, but “observed” means a benchmark exists, not that causal, opportunity, or investability evidence is complete.

### Missing required source families

No operational adapters were found for the majority of PDF-required families, including:

- ALFRED vintages and global macro panels
- IMF, BIS, World Bank, OECD
- global central-bank and official statistics data
- Treasury auction, TIC, and funding plumbing data
- SEC/IDX point-in-time corporate filings at production scale
- EIA/IEA/OPEC/JODI physical commodity data
- futures curves and physical inventories
- options IV, skew, dealer positioning, and borrow
- IDX broker summary and foreign flow
- stablecoin, ETF flow, funding/basis/open interest, and per-asset on-chain data
- shipping, freight, port, power, grid, and supply-chain data
- licensed source metadata and entitlement enforcement

No tracked `data/eros.duckdb` or equivalent populated research store was found.

## BCM / Crash Meter audit

### What exists locally

`data/macro_investigation/crashmeter_v3_daily.csv`:

- 748 rows
- 2023-07-31 through 2026-07-28
- no missing cells in the ten stored columns
- score values 1 through 4

`data/macro_investigation/crashmeter_v3_validation.json`:

- historical `first_score_ge3` fields for Dotcom, GFC, and COVID are `null`
- two recorded false-alarm clusters
- current/latest stored score is 2 on 2026-07-28

`assets/crashmeter_v3/backtests_b64.json`:

- Dotcom 2000 JPEG claim exhibit
- GFC 2008 JPEG claim exhibit
- COVID 2020 JPEG claim exhibit
- metric-definition JPEG

### What this does not prove

The CSV starts in 2023, so it cannot reproduce Dotcom, GFC, COVID, or 2022 episode behavior. The embedded JPEGs are claim exhibits, not raw point-in-time backtest data. There is no traceable event-level dataset connecting signal date, source vintage, SPX outcome, exit, re-entry, transaction cost, and false-positive definition.

### Required BCM implementation still missing

- validated continuous stress score
- validated fragility score
- exact BCM component blocks and weights
- raw-source point-in-time replication
- threshold bands with documented derivation
- exposure rule and scope limitation
- price/outcome panel in Research/Proof only
- risk-window shading
- warning, exit, and re-entry markers
- drawdown panel
- driver attribution matching the validated BCM blocks
- Dotcom, GFC, COVID, and 2022 replay from raw data
- false-positive and false-negative ledger
- era stability, plateau, bootstrap, holdout, and prospective tests
- replication checksums and discrepancy report

## Five-tab contract matrix

| Tab | Required by PDF | Current implementation | Verdict |
|---|---|---|---|
| Command Center | Data health, causal regime, capital map, changes, competing theses, ranked opportunities, action queue, risks, unknowns, catalysts; no price chart | Most headings exist; causal content remains synthetic; action is generic WAIT; price chart violates contract | **PARTIAL / CONTRADICTORY** |
| Global Explorer | Countries, assets, sectors, themes, physical systems, supply chains, mechanism graph, search, unified dossier | Country/asset registries and search exist; sectors, physical systems, and supply chains are placeholders; no unified dossier | **PARTIAL** |
| Opportunity Engine | Global leaderboard, horizons, instrument types, capital formation, crowding, full packets, rejected opportunities, conservative EV ordering | Gate-count chart, empty-state tabs, static rejected fixtures; no candidate generation or packets | **FAIL** |
| Portfolio | Holdings, suggested changes, exposure decomposition, scenarios, liquidity, hedges, rebalance queue, journal | No portfolio loaded; most tabs are empty messages; scenario fixture has unknown probabilities and no computed impact | **FAIL / SAFE EMPTY** |
| Research Lab | Research registries, experiments, prediction journal, failures, data health, model registry, agent IQ, proof center | Evidence-count chart, synthetic tables, local legacy Crashmeter timeline; no operational experiment/proof system | **PARTIAL** |

## Engine audit

The repository contains useful contracts and small pure functions:

- expected-value arithmetic
- opportunity packet schema
- point-in-time valuation helper
- exposure aggregation
- simple scenario impact
- value-of-waiting comparison
- experiment schemas

These are not connected into an operational pipeline. Missing operational engines include:

- multi-thesis discovery and Bayesian update pipeline
- narrative-to-evidence ingestion and source-chain de-duplication
- mechanism propagation and competing causal graphs
- point-in-time dataset registry and lineage replay
- trial ledger and multiple-testing controls
- walk-forward, holdout, placebo, permutation, and prospective validation runners
- global candidate generator
- priced-in estimator
- calibrated probability and payoff estimator
- instrument mapping, liquidity, tax, borrow, and capacity pipeline
- portfolio optimizer, conflict resolver, hedge designer, and rebalance journal
- sealed prediction journal and model-decay monitoring

## Test and release state

Current local test result:

- 41 passed
- 2 failed

Failures:

1. Missing decision explanation panel required by the new TDD contract.
2. Missing `LEGACY BACKTEST CLAIM EXHIBITS` renderer.

The working tree is not clean and contains uncommitted Research Lab/test changes plus untracked legacy artifacts and temporary audit files. The local revision is not release-ready.

## Public deployment findings

- All five tabs open.
- No browser-console errors were observed during the audit.
- Command Center reports 11 observations, 5/6 benchmark groups, `UNKNOWN` causal regime, zero qualified opportunities, and locked execution.
- Global Explorer exposes registry coverage but most countries remain data debt.
- Opportunity leaderboard is empty.
- Portfolio is empty.
- Public Research Lab does not contain the local Crashmeter timeline because those changes are not deployed.
- Public acceptance status itself reports Data FAIL, Historical Replay FAIL, Prospective FAIL, and several PARTIAL gates.

## Required remediation order

1. Remove/move Command Center price paths to a Proof/Outcome or Explorer view.
2. Finish the decision explanation contract without pretending a trade is qualified.
3. Rename legacy Crashmeter artifacts correctly and render them only as claim exhibits.
4. Build a raw-source, point-in-time BCM replication package before displaying BCM as validated.
5. Build causal macro adapters and exact data-health semantics per feed/dataset, not six benchmark groups only.
6. Build Global Explorer dossiers and admitted mechanism graphs.
7. Build a real candidate-generation and opportunity-packet pipeline.
8. Build portfolio ingestion and allocation/scenario engines.
9. Build Research Lab registries, trial ledger, checksums, holdouts, failure library, and prospective journal.
10. Run the full acceptance battery, independent review, clean commit/push, and public five-tab QA.

## Final audit classification

- **Architecture shell:** PARTIAL PASS
- **Fail-closed safety:** PASS
- **Public benchmark monitoring:** PARTIAL PASS
- **Causal economic reasoning:** FAIL / NOT IMPLEMENTED
- **Global data completeness:** FAIL
- **BCM replication:** FAIL
- **Opportunity discovery and ranking:** FAIL
- **Portfolio allocation:** FAIL
- **Research proof system:** FAIL
- **Production readiness:** FAIL

The correct current product label is:

> **Research and monitoring prototype with fail-closed execution — not a completed economic reasoning or capital-allocation system.**

## Post-audit implementation appendix

The following changes were implemented after the baseline findings above. The original findings
remain preserved to distinguish the audited public revision from the subsequent local release
candidate.

### Implemented and verified locally

- Added decision-first explanations for the default action, causal `UNKNOWN`, zero qualified
  opportunities, and six-group benchmark status.
- Moved historical provider paths out of Command Center into the Research Lab outcome surface.
- Added weekend-aware non-crypto freshness while preserving the three-hour crypto threshold and
  future-timestamp rejection.
- Current provider probe returned 12/12 expected benchmark symbols, 5/6 complete groups, and zero
  provider failures. Rates & Volatility remains partial because the stored DGS10 observation is not
  from the latest completed business date. This remains benchmark completeness only, not
  causal-data completeness.
- Added a strict Crashmeter research loader with schema, monotonic-date, binary-component,
  arithmetic-score, finite-value, and checksum validation.
- Strict source checks now report yield curve `PASS`, HY OAS `FAIL` for one unverified daily row,
  CAPE `FAIL` because no raw source is stored, one historical false-alarm outcome mismatch, and one
  `PENDING_FORWARD_WINDOW`; the resulting verdict is `BLOCKED_SOURCE_DATA_INCONSISTENT`.
- Added article threshold bands, derived risk windows, independently derived SPX drawdown overlap,
  corrected A1/A2/B1/B2/C attribution labels, claim ledger, and SHA-256 artifact identity.
- Historical Dotcom/GFC/COVID claims remain explicitly `UNREPLICABLE`; the release candidate reports
  `BLOCKED_SOURCE_DATA_INCONSISTENT` and keeps execution locked.
- Added candidate-level qualification failure reasons, five scenario horizons, and explicit trigger,
  invalidation, sizing, valuation, and alternative-action fields.
- Added portfolio input, scenario-horizon, and rebalance-tripwire contracts. Missing private holdings
  continue to block exposure, sizing, hedge, and rebalance outputs.
- Local quality gates passed: 74 tests, Ruff, MyPy over 35 source files, compileall, lock validation,
  and diff hygiene.
- Local browser QA opened all five tabs and confirmed every new product contract without JavaScript
  errors.

### Still intentionally blocked

- A point-in-time causal macro panel is not present; all eight causal regime dimensions remain
  `UNKNOWN`.
- The legacy Crashmeter is not promoted to BCM and is not execution eligible.
- Candidate generation and calibrated conservative-net-EV ranking are not operational.
- Private portfolio ingestion and account-specific allocation are not present.
- Automatic execution remains prohibited and human approval remains mandatory.
- Public deployment verification must occur after review, commit, push, and Streamlit redeploy.

The post-audit release candidate is usable as a **public-market monitoring and research-proof
interface**, not as an autonomous investment recommendation or execution system.

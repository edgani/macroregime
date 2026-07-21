# War Room OS — Decision Intelligence v3.3.2

This is the canonical integrated release built from the user-supplied
`War_Room_OS_Decision_First_v2_9(1).zip` lineage. It keeps the eight-workspace
research architecture, but changes the default experience from graph-first to
**decision-board first**.

## Why v3.3.2 exists

The v3.2 maps were honest but not sufficiently actionable. In particular, FX could
show live spot context while withholding a single direction, which was epistemically
correct but operationally unclear. Large graph canvases also used too much space before
answering the user’s immediate questions.

v3.3.2 therefore uses three explicit modes:

- **BOARD** — default decision surface: state, orientation, action, evidence, trigger,
  invalidation, reason, risk and freshness.
- **MAP** — causal/flow drill-down after the decision state is understood.
- **EVIDENCE** — research doctrine, failure review and falsification detail.

## Eight workspaces

1. **Mission** — You Are Here, Current Rain, recognition gap and decision queue.
2. **Regime & Risk** — macro nowcast, liquidity plumbing, credit and risk propagation.
3. **Opportunities** — structural asymmetry and value-capture research inventory.
4. **Markets** — US, IHSG, crypto, commodities and FX adapters.
5. **Flow & Positioning** — cross-asset context, options, TRF/dark pool, filings,
   broker routes and on-chain events.
6. **Causal Map** — supply chains, chokepoints, value capture and winner genealogy.
7. **Execution & Portfolio** — trigger, trade invalidation, thesis invalidation,
   opportunity cost, exit state and capital gate.
8. **Research & Validation** — Study the Tape, prediction log, baseline, ablation,
   failure review, data lineage and source-change review.

## FX is now pair-specific

There is deliberately no aggregate `FX LONG` or `FX SHORT`. Every pair receives one
of these explicit states:

- `TRIGGERED WATCH LONG`
- `TRIGGERED WATCH SHORT`
- `WATCH LONG`
- `WATCH SHORT`
- `WATCH LONG/SHORT · PRICE ONLY`
- `NO TRADE / TWO-SIDED WATCH`
- `WAIT / REASSESS AFTER EVENT`
- `BLOCKED / NO DATA`

Every row shows orientation, driver coverage, trigger, stop/invalidation, reason,
event risk and freshness. Price-only direction can never become a triggered state.

## Current-developments radar

The release includes:

- a dated structural-development inventory;
- automatic freshness expiry;
- a primary/official-source change detector;
- explicit `CHANGED_UNREVIEWED`, `UNCHANGED`, `ERROR` and `ACTION_REQUIRED` states;
- human review before any changed page enters the research inventory.

The source registry covers Robinhood, SEC, CFTC, Nasdaq, Federal Reserve, U.S. Treasury,
EIA, OPEC, CME, Bank Indonesia, IDX, OJK and BPK sources. A page change is never
translated automatically into long/short direction.

Crypto research now explicitly covers brokerage/onchain convergence, tokenized assets,
stablecoin economics, prediction markets, agentic execution, protocol revenue/value
capture, developer adoption, legal form, reserves, redemption, unlocks and market
microstructure—not just BTC/ETH/SOL price and perps.

## Non-negotiable semantics

- Missing or stale feed never becomes a current claim.
- Observed, inferred, structural, disputed and unknown evidence remain distinct.
- Broker routes do not reveal beneficial owner or intent.
- Options prints, dark-pool prints and whale transfers are context, not automatic direction.
- Theme conviction is not probability.
- Hand-authored upside classes are not EV, targets or sizing.
- IHSG is cash long-only.
- A triggered watch is not an autonomous order.
- Engineering PASS does not prove predictive alpha.
- Capital permission remains `CAPITAL_BLOCKED` until market-specific point-in-time WFA,
  untouched lockbox and prospective evidence earn promotion.

## Run locally on Windows

Double-click:

```text
CHECK_AND_RUN.bat
```

The script creates `.venv`, installs dependencies, runs the v3.3.2 master release suite
and starts Streamlit only when the operational checks pass.

For later starts:

```text
RUN_WARROOM.bat
```

To update only the official-source hashes/status:

```text
REFRESH_OFFICIAL_RADAR.bat
```

## Validation boundary

```bash
python validate_release_v33.py
```

A PASS means the integrated application is operationally ready for user review and that
its tested fail-closed/semantic contracts work. It does **not** mean every component has
predictive edge, live provider entitlements, or capital permission. See
`V33_MASTER_RELEASE_REPORT.json`.

# Market Opportunity OS v3.2.1

This release upgrades **Opportunity Intelligence Engine v2.6 — IHSG Transaction Intelligence** into one cross-market architecture with a shared intelligence kernel and market-specific verticals.

## Product structure

- **CONTROL ROOM** — cross-market posture, data readiness, Market Memory and change board.
- **OPPORTUNITIES** — the existing decision-first opportunity desk.
- **VERTICALS** — separate engines for On-chain, Crypto, US Stocks, IHSG, Forex and Commodities.
- **MACRO & EVENTS** — macro/risk context; it is a governor, not a universal alpha score.
- **RESEARCH / REPLAY** — validation, rejected signals, readiness and historical replay.

## Shared kernel

Every vertical uses the same research contract:

`VALIDATE → BASELINE → CHANGE → SEQUENCE → QUALITY → STATE → EARLINESS/CROWDING → PAYOFF/RISK → DECISION → OUTCOME → MARKET MEMORY`

The engine deliberately avoids a single giant Alpha Score. Independent evidence families and hard gates stay separate so a strong signal cannot hide missing causal data or a fatal risk flag.

## Vertical responsibilities

### On-chain
Free DeFiLlama chain radar: TVL, stablecoin supply, DEX activity, fees and revenue are independent confirmation families. Wallet/social/developer signals remain separate adapters and are not inferred from TVL.

### Liquid crypto
Value-capture economics are retained. Spot-flow / OI / funding / liquidation data are required before leverage can be promoted from research-gated status.

### US Stocks
Existing fundamentals, valuation and causal-chain logic remain. Full point-in-time analyst revisions and institutional-flow history are still required for production-alpha claims.

### IHSG
v2.6 broker/transaction intelligence is preserved: Index Alpha EOD broker attribution + Invezgo intraday/order-book when keys are configured. Broker evidence contributes at most one independent evidence-family vote. IHSG remains cash-only.

### Forex
Requires relative rates, macro surprise, central banks, positioning and valuation. Price-only history never becomes directional alpha.

### Commodities
Requires physical supply/demand, inventory, futures curve and positioning. Price-only history never becomes directional alpha.

## Market Memory

`state/market_memory.sqlite` stores timestamped snapshots. The current observation is evaluated against prior history **before** it is appended, so it cannot leak into its own baseline. Sequence signatures preserve the order of state transitions.

On a fresh deployment, `BASELINE BUILDING` is expected until enough snapshots accumulate.

## DeFiLlama

The default adapter uses the **free API** (`api.llama.fi`) and requires no API key. It uses official free endpoint families for chain TVL, stablecoins, DEX activity and fees/revenue. DeFiLlama Pro is not required for v3.1.

## IHSG API configuration

Optional server-side secrets:

```toml
INDEX_ALPHA_API_KEY = "..."
INVEZGO_API_KEY = "..."
```

Environment variables with the same names also work.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Windows: `run_windows.bat`  
Linux: `./run_linux.sh`

## Validation

```bash
python tests/run_all.py
```

Current package result: **19 PASS / 0 NONPASS** plus **20/20 v3.2 structural acceptance checks**.

UI hotfix: top workspace navigation is now native button routing rendered before the expensive scan path, and CONTROL ROOM uses the dense operator-dashboard shell. Browser-smoke is not claimed in the build environment because Streamlit itself is unavailable there.

See `V3_ARCHITECTURE.md`, `FINAL_AUDIT.md`, `TEST_MATRIX.md`, `VALIDATION_RESULTS.md`, `KNOWN_LIMITATIONS.md`, and `DEPLOY_FROM_ZERO.md`.


## v3.1 · Story / Expectation Optionality

US and IHSG now have a loss-making/turnaround research module. It never treats a loss as bullish by itself. IHSG uses fundamental inflection + financing survivability and keeps broker confirmation separate. US additionally uses current analyst EPS trend/revision breadth. Loss-making valuation falls back to same-sector Price/Sales only when at least four valid peers exist. See `STORY_OPTIONALITY_MODULE.md`.


## v3.2 · Longitudinal Opportunity Memory + Outcome Learning

v3.2 keeps the v3.1 decision core and adds a separate longitudinal research layer:

- automatic opportunity discovery over the configured multi-market universe;
- immutable first-detection `OPPORTUNITY_EVENT`;
- causal driver / bottleneck / beneficiary / revenue-margin capture fields;
- persistent lifecycle watching across restarts;
- 1D → 12M forward outcomes, relative alpha, MFE/MAE and time-to-thesis;
- false-positive + missed-runner stores;
- regime/market/theme expectancy and chronological walk-forward;
- daily/weekly learning reports;
- dense dark-cyan Opportunity Tracker UI;
- original v3.1 daily decision screen preserved under `DECISION DESK`.

Longitudinal state is stored in `state/opportunity_memory.sqlite`. First-detection rows are immutable. Future observations only mature lifecycle/outcome tables. No autotrading was added.

See `V3_2_IMPLEMENTATION.md` and `UPGRADE_FROM_V3_1.md`.

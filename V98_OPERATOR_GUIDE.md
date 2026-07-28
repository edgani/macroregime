# V9.8 Operator Guide

## Normal workflow

1. Mission Control tells you whether any ticker packet is promoted. It does not infer a trade from a
   quote or from source availability.
2. Open a market tab and select the ticker.
3. Read the same packet from top to bottom: decision, current quote, causal chain, flow/positioning,
   value bridge and target, risk/execution, then proof.
4. Open **Data & Proof** only when you need lineage, freshness, missing-domain or proof detail.
5. Do not export an order unless the packet is `LIMITED_PRODUCTION_ELIGIBLE` and the V9.8 control
   plane recomputes the exact proof, quote, account and risk state.

## Adding a research projection

Create `runtime/v98_decisions/<market>/<ticker>.json` from
`V98_TICKER_DECISION_TEMPLATE.json`. The file must contain three frozen scenarios, evidence IDs,
assumptions, allowed nontechnical feature domains and six valid hashes. The calculation may display a
research target, but remains capital-blocked until market proof and execution gates pass.

## Important distinctions

- Research universe coverage is not quote coverage.
- Quote coverage is not point-in-time evidence.
- Point-in-time evidence is not a winning strategy.
- A valid projection is not calibrated timing.
- Historical proof is not prospective fill proof.
- Software readiness is not permission to trade.

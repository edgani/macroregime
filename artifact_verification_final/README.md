# Market Opportunity OS v3.2.6 — Logic-Hardened Final

Cross-market **macro + opportunity intelligence** research system. It discovers and tracks opportunities, freezes what was knowable at first detection, matures forward outcomes, and learns prospectively without self-modifying production logic.

## Product surface

One unified UI only:
- **CONTROL ROOM** — cross-market readiness, macro/risk context, candidate inspection and radar.
- **OPPORTUNITIES** — immutable first-detection memory, lifecycle, causal chain, outcomes, alerts and theme clusters.
- **VERTICALS** — On-chain, Crypto, US Stocks, IHSG, Forex and Commodities with market-specific gates.
- **MACRO & EVENTS** — shared timing/risk context; it does not overwrite thesis quality.
- **LEARNING / REPLAY** — expectancy, leakage-embargoed walk-forward, prospective baselines, runner recall, failures and missed winners.

## Core research contract

`OBSERVABLE CHANGE → ECONOMIC TRANSMISSION → BOTTLENECK → BENEFICIARY → REVENUE/MARGIN OR VALUE CAPTURE → EXPECTATION GAP → CATALYST → OPPORTUNITY EVENT → FUTURE OUTCOME → LEARNING`

Classic RSI/MACD/stochastic/MA-cross stacks are not primary opportunity logic. Execution remains separate; there are no private keys, broker credentials or automatic orders.

## v3.2.6 hardening

This release rejects the previous v3.2.3 logic as a final baseline and closes the highest-risk correctness defects found in adversarial review:
- outcome endpoints use the first observable bar on/after the requested horizon, including weekends/holidays;
- daily bar labels are mapped to conservative market-close availability clocks;
- benchmark/sector anchors must be knowable at detection time;
- walk-forward training uses `label_available_at_utc`, not merely event year;
- missing relative alpha stays UNKNOWN instead of becoming a loss;
- first-seen episodes cannot be resurrected after INVALIDATED/RESOLVED;
- bounded outcome scheduling is fair to new events;
- opportunity score requires observable economic capture;
- generic narrative, market membership or company capex cannot manufacture an archetype;
- readiness gates cap actions/lifecycle and leverage/options fail closed;
- macro missing credit/stress data fails closed instead of becoming calm/neutral;
- IHSG negotiated-market contamination uses comparable gross-trade denominators;
- syndicated/stale news is deduplicated and freshness-gated;
- correlated fundamentals count as one evidence family, not four votes;
- crypto supply/dilution metrics do not double vote;
- valuation scenario dispersion is never invented from one input;
- prospective current-universe observations, simple baselines and scanned-universe runner cohorts are frozen before future outcomes exist;
- US sector-relative outcome uses sector ETF context where the sector mapping is defensible.

## Automatic breadth

The seed universe remains the stable core. For US and IHSG the app can fetch current issuer catalogs and rotate a bounded number of additional names into each half-hour scan. Catalog membership is accumulated **prospectively**; a provider outage never means a ticker was delisted.

This is not a claim of complete historical survivorship-safe exchange membership. See `KNOWN_LIMITATIONS.md`.

## Learning rules

- Event snapshot / first seen price / first seen time are immutable.
- Failed and invalidated opportunities remain in history.
- Forward outcomes: 1D, 3D, 1W, 2W, 1M, 3M, 6M, 12M.
- Relative labels stay missing when the comparator is unavailable.
- Walk-forward uses chronological expanding windows with a label-availability embargo.
- Small samples shrink toward broader parents; no LLM changes production weights.
- Baseline A–E selections are frozen prospectively from the scanned cross-section.
- Runner recall is reported only after prospectively frozen 3M cohorts mature.

## Start on Windows

Recommended: double-click `START_MARKET_OPPORTUNITY_OS.bat`.

It creates `.venv`, installs `requirements.txt`, then runs Streamlit. Optional IHSG transaction APIs can be configured in `.streamlit/secrets.toml` or environment variables:

```toml
INDEX_ALPHA_API_KEY = "..."
INVEZGO_API_KEY = "..."
```

Without those keys the relevant IHSG evidence stays GATED; it is not fabricated.

## Verification

Run:

```bash
python tests/run_all.py
```

Release-package gate for this build: **23 PASS / 0 NONPASS** before packaging, then the same suite is run again from a fresh extraction of the final ZIP.

Passing code tests means the tested invariants hold. It does **not** prove live alpha or statistically significant market outperformance. Those claims require matured PIT/OOS evidence.

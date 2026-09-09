# Market Opportunity OS

Macroregime is a research-only Streamlit application for cross-market macro and opportunity intelligence. It discovers and tracks opportunities, freezes what was knowable at first detection, matures forward outcomes, and learns prospectively without changing production ranking weights.

## Product surface

The application has one UI with five persistent workspaces:

- **CONTROL ROOM** - cross-market readiness, macro/risk context, candidate inspection, and radar.
- **OPPORTUNITIES** - immutable first-detection memory, lifecycle, causal chain, outcomes, alerts, and theme clusters.
- **VERTICALS** - On-chain, Crypto, US Stocks, IHSG, Forex, and Commodities with market-specific gates.
- **MACRO & EVENTS** - shared timing/risk context that does not overwrite thesis quality.
- **LEARNING / REPLAY** - expectancy, leakage-embargoed walk-forward analysis, prospective baselines, runner recall, failures, and missed winners.

Stable deep links use `?route=CONTROL_ROOM`, `OPPORTUNITIES`, `VERTICALS`, `MACRO_EVENTS`, or `LEARNING_REPLAY`.

## Research contract

`OBSERVABLE CHANGE -> ECONOMIC TRANSMISSION -> BOTTLENECK -> BENEFICIARY -> VALUE CAPTURE -> EXPECTATION GAP -> CATALYST -> OPPORTUNITY EVENT -> FUTURE OUTCOME -> LEARNING`

The system keeps event snapshots, first-seen prices, and first-seen timestamps immutable. Failed and invalidated opportunities remain in history. Missing or unavailable evidence remains `UNKNOWN` or `GATED`; it is not converted into a favorable signal. This is decision-support software, not an autotrading system.

## Run locally

On Windows, run `START_MARKET_OPPORTUNITY_OS.bat`. On other platforms:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
streamlit run app.py
```

Optional IHSG transaction APIs can be configured in the ignored `.streamlit/secrets.toml`, using `.streamlit/secrets.toml.example` as the safe template. Without those keys, the relevant evidence remains gated.

## Verification

Run `python tests/run_all.py`.

See `TEST_MATRIX.md` for coverage, `LOGIC_AUDIT.md` for the latest verified result, `ARCHITECTURE.md` for system boundaries, `KNOWN_LIMITATIONS.md` for explicit caveats, and `DEPLOY_FROM_ZERO.md` for deployment guidance.

Passing tests establish implementation invariants, not live alpha, complete point-in-time vendor coverage, survivorship-safe history, or statistically significant out-of-sample superiority.

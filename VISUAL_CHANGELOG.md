# v2.4 Visual Decision System

## Why this release exists
v2.3 was fail-closed, but that made FX, commodities and crypto disappear from the leverage/options screens whenever their dedicated causal model was not qualified. That was safe for capital but bad UX: a user could reasonably think those markets were missing.

v2.4 changes the presentation contract:

- **Visible is not the same as actionable.** Supported markets stay visible in the relevant expression desk.
- **Qualified rows show `● ACTION`.** Non-qualified rows show `○ WAIT` with the exact missing gate.
- Leverage now visibly covers **US / Crypto / FX / Commodity**; IHSG remains cash-only.
- Options now visibly covers **US + BTC/ETH Deribit**. Other crypto is never given a fake option surface.
- The daily page is visual-first: opportunity map, expression coverage heatmap, evidence/asymmetry chart, compact metrics and a decision stack.
- The long thesis/valuation/causal-chain text is moved under a collapsed **Deep dive** expander.
- Macro is visual-first: NOW→+4Q heatmap, pressure bars, five compact state metrics, max three paths. Raw readings are collapsed.

## Capital-safety behavior is unchanged
A WAIT/GATED row is **not** a trade recommendation. The app intentionally refuses to manufacture FX, commodity or crypto leverage merely to fill a table. The missing data families are shown instead of hiding the market.

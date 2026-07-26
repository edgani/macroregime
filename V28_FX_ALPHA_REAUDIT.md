# War Room OS v2.8 — FX and Alpha re-audit

## FX root cause

The screenshot showed **6 loaded FX series** and live CFTC rows while the headline still said `FX STATE NO_DATA`. The UI had conflated two different facts:

1. observed spot-price availability; and
2. availability of the macro-relative FX direction model.

The full research plane obtains market bias from the driver matrix. Most FX driver families (pair-specific rate differential, real-rate differential, BOP, terms of trade, central-bank reaction function and intervention risk) were not populated, so the driver bias correctly returned `NO_DATA`. The UI incorrectly presented this as if no FX prices existed.

v2.8 separates:

- `FX SPOT DATA` — observed price history;
- `USD / DXY CONTEXT` — price context only;
- `MACRO-RELATIVE MODEL` — driver coverage and availability;
- `FX FUTURES / COT` — positioning context;
- `PAIR DIRECTION GATE` — no directional output when macro-relative evidence is incomplete.

Display symbols are normalized to `USDJPY=X` and `USDIDR=X`; the provider adapter still queries Yahoo using `JPY=X` and `IDR=X`.

This preserves the previously frozen result that the **FX price-only family was falsified**. Price data can be live without becoming a directional signal.

## Alpha root cause

The previous radial constellation placed up to 16 cards of fixed 168px width on radii of 140–202px, guaranteeing overlap. It also labeled price/market-aligned setups as `LIVE ALPHA`, which overstated what had actually passed.

v2.8 replaces it with a staged funnel:

1. Tactical discovery pool;
2. Market-direction alignment;
3. Independent institutional/filed-fact evidence;
4. Capital permission, which remains blocked;
5. At most five visible research candidates.

Readiness values are explicitly descriptive, not probabilities. `BUILD_LONG`/`SHORT` actions are displayed as `LONG WATCH`/`SHORT WATCH` inside Alpha. Full details remain in the Evidence Ledger, so readability no longer requires showing every candidate on the graph.

## Additional layout hardening

- Generic market canvases show at most five ticker cards.
- Derivatives provider/target rows are capped on the graph; all records remain in the ledger.
- Flow & Rotation shows at most six bottom-rank cards.
- A neutral or missing market context no longer approves both long and short setups.

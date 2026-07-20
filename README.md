# War Room OS — Decision-First Live Architecture v2.9

v2.9 corrects the role of the main workspaces and removes the overlapping provider/node wall.

## What each workspace is for

- **Alpha Center**: extreme-asymmetry discovery. It searches structural bottlenecks, hidden value-capture nodes, expectation gaps and room-to-run. Headroom classes such as `10–50x`, `50–500x` and `500x+` are scenario-capacity buckets with falling base rates; they are not targets or probabilities.
- **Market tabs**: execution posture. Every visible ticker is labelled `BUILD LONG`, `WATCH LONG`, `BUILD SHORT`, `WATCH SHORT`, `REDUCE / AVOID`, or `NO TRADE` with trigger and stop context.
- **Institutional**: usable evidence domains and confirmed event clusters. Raw provider entitlement/errors remain in the ledger instead of covering the canvas.
- **Derivatives / Squeeze**: domain summaries for options, borrow, perps and crypto options. OI/funding/Greeks/squeeze scores are context, not probabilities.
- **Company Intel**: evidence trace for value capture, filed fundamentals, positioning, price state and thesis invalidation.
- **Validation Center**: fail-closed production gate. Research is never promoted solely because an in-sample result looks attractive.

## Architecture

- bounded inline market bootstrap before first paint;
- committed snapshot injected into the first render;
- one embedded background collector on managed hosting;
- independent market, macro/liquidity, event/derivatives, slow-enrichment and expanded-universe planes;
- atomic snapshot and last-good caches;
- multi-provider public-price fallback;
- explicit `LIVE / PARTIAL / STALE / NO_SIGNAL / NO_DATA / ACTION_REQUIRED / NOT_ENTITLED` states;
- no synthetic production fallback.

Deploy with `app.py` at repository root. Read `DEPLOY_NOW.md` and
`V29_DECISION_FIRST_REAUDIT.md` before deployment.

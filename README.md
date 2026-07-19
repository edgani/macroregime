# War Room OS — Deterministic Hosted Live Architecture v2.7

v2.7 removes the permanent `INITIALIZING · R1` failure by making the first market snapshot a
pre-render requirement instead of delegating it to an unverified detached process.

Core architecture:

- bounded inline market bootstrap before first paint;
- committed snapshot injected into the iframe on first render;
- one embedded background collector on managed hosting;
- independent market, macro/liquidity, event/derivatives, slow-enrichment, and expanded planes;
- atomic snapshot, price, FRED, and liquidity caches;
- multi-provider public price fallback;
- explicit `LIVE / PARTIAL / STALE / NO_SIGNAL / NO_DATA / ACTION_REQUIRED / NOT_ENTITLED` states;
- no synthetic production fallback.

Deploy with `app.py` at repository root. Read `DEPLOY_NOW.md` and
`V27_DEEP_STARTUP_REAUDIT.md` first.

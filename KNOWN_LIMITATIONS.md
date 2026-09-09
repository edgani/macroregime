# Known Limitations

- Public and locally supplied feeds do not provide complete historical point-in-time fundamentals, estimates, constituents, positioning, or survivorship-safe universes. Missing evidence remains `UNKNOWN` or `GATED`.
- Daily-bar point-in-time mapping uses conservative market-close availability. It cannot reconstruct every vendor's original publication latency.
- A fresh memory database has no mature forward outcomes. Expectancy, runner recall, and superiority claims remain unavailable until prospective labels mature.
- Macro, credit, options, crypto usage/leverage, FX external-balance, commodity physical, and IHSG broker evidence are feed-dependent and fail closed when absent.
- Catalog accumulation is prospective and bounded; it is not a complete historical delisting or constituent-membership database.
- Forward endpoints use the first observable bar on or after each horizon, so calendar horizons can differ from exact trading-day counts.
- Walk-forward and baseline outputs are diagnostics, not proof of causal alpha. Small samples and regime changes remain material risks.
- Third-party APIs can fail, rate-limit, or change schema. Those failures must remain visible and gated.
- Browser screenshots require an OS environment that permits launching Chromium; run `tests/browser_smoke.py` against a live app.
- The engine is research software only: no autotrading, broker execution, wallets, or private keys.

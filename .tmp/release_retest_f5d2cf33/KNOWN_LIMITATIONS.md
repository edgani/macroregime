# Known Limitations — v3.2.6

These are explicit gates, not hidden assumptions.

1. **No historical alpha claim yet.** The system has leakage-safe prospective learning machinery, but not a complete multi-year PIT dataset proving outperformance.
2. **Historical universe is not fully survivorship-safe.** Current US SEC reporting-issuer and IDX catalogs can be frozen prospectively. Historical delisted/bankrupt/dead-token membership is not reconstructed completely.
3. **US core evidence is often PARTIAL.** Full PIT institutional capital-flow and analyst-revision history is not universally available from the free/current adapters.
4. **IHSG core evidence is often PARTIAL/GATED.** Broker/foreign flow needs configured providers; complete corporate-action history is not yet a universal PIT adapter.
5. **Crypto leverage thesis remains gated** without reliable spot-flow, OI, funding, liquidations and liquidity evidence.
6. **FX and commodities remain data-gated** until dedicated relative-macro / physical-balance evidence exists. Price history does not substitute.
7. **Sector-relative outcome is strongest for US equities.** Other markets remain benchmark-relative unless a defensible sector index is available.
8. **Catalyst calibration is incomplete.** Catalyst text is stored, but sell-the-news/failure statistics require reliable PIT catalyst timestamps and mature cohorts.
9. **Baseline A–E are prospective scanned-universe baselines**, not claims about an exhaustive historical exchange universe.
10. **Runner recall is scanned-universe recall.** It cannot measure names the system never placed into a prospectively frozen scan cohort.
11. **Current issuer catalog is not identical to exchange membership.** SEC company tickers include reporting issuers; the app does not label this as a complete US exchange list.
12. **Third-party APIs can fail/rate-limit/change schema.** Such failures must remain visible/gated.
13. **No browser pixel-level smoke was run in the build container** because Streamlit is unavailable there. Static UI contract tests and source-level route checks pass.
14. **No autotrading.** The engine is research/decision support only.

# Attachment coverage matrix — v5.2

Source reviewed: `Pasted text(161).txt`, lines 1–296. The text contains both requirements and prior claimed results. A claim in the text is not treated as evidence unless its actual artifacts are present in the supplied ZIP.

| Attachment requirement / claim | v5.2 disposition | Evidence in this release |
|---|---|---|
| Read the attachment fully; no omissions (lines 1–9) | Covered | This matrix and the real-source patch ledger map each material item. |
| Harden the actual app, not only a toolkit/report (13, 59–63, 87) | Covered | The supplied v4.2 ZIP was extracted and its active `app.py → warroom_data_worker.py → run.py` path was patched. |
| Static capability verifier (17) | Covered | `market_capabilities.py` defines `STATIC_CAPABILITIES`; adversarial test checks it. |
| Validators run on copies and cannot mutate source (18, 44) | Covered | `run_v52_hardened_audit.py` hashes immutable source before/after every fresh-copy validator. |
| Remove persistent pickle/joblib/dill (19, 38–39) | Covered | Active caches/IPC use `safe_snapshot.py`; AST gate rejects imports and `.pkl` paths. |
| Boolean probability flag cannot unlock EV (20) | Covered | `scenario_valuation.py`; forged boolean adversarial test. |
| Registry booleans are not proof (21, 41–42) | Covered | `proof_registry.py` ignores editable pass flags; default promotion is zero. |
| Ed25519 exact-scope receipt with proof artifacts (21) | Strengthened | `proof_receipts.py` v2 adds out-of-band trust-root pin, role-bound hashes, matured prospective evidence and fail-closed revocation. |
| US listed options per instrument (22–23) | Covered | Requires exact contracts, valid non-crossed quote rows, provider and freshness. |
| IHSG options disabled (24) | Covered | Static and dynamic gates force disabled. |
| Crypto underlying and venue (25) | Covered | Missing venue fails. |
| Commodity exact futures contract (26) | Covered | Generic root such as `CL` fails; exact contract and option fields required. |
| FX listed option or valid vol surface; spot excluded (27) | Covered | Product-specific gate; spot/futures context cannot enable options. |
| Warnings become errors (28) | Covered | Strict runners set `PYTHONWARNINGS=error`; numerical divide/empty warnings were repaired. |
| Actual Streamlit health mandatory (29) | Covered as a gate; blocked here | `validate_streamlit_health_v52.py` checks `/_stcore/health`; current environment lacks Streamlit. |
| Direction requires exact-scope proof, freshness, lineage, rules and geometry (30) | Covered | `direction_authorization.py`; FX active path integrated; IHSG short blocked. |
| Separate technical target, fair value, scenario range and calibrated EV (31) | Covered | `scenario_valuation.py` and research-kernel claim boundaries. |
| Signature tamper/expiry/revocation/forged flags/stale/crossed quotes/etc. (44) | Covered and expanded | 39/39 adversarial checks, including runtime snapshot tampering and trust-root pinning. |
| Do not directly install article formulas (46–58) | Covered | `RESEARCH_IMPORT_POLICY.md`; external ideas remain process/challenger inputs only. |
| Wasserstein HMM is challenger (50) | Preserved | No promotion receipt; default blocked. |
| IC/DSR/neutralization/correlation/decay need real discovery ledger (51) | Preserved | Statistical protocol only; no survivor-only promotion. |
| Order-flow imbalance is horizon-limited (52) | Preserved | Not authorized as universal swing direction. |
| Jane Street ideas used for controls, not proprietary imitation (53) | Preserved | Fresh-copy, mutation, state/control and nonstationarity principles only. |
| Chokepoint mapping is market-specific (54) | Preserved | Mapping process retained; no universal capital score. |
| Nicholas Crown process vs proprietary claims (55) | Preserved | Process concepts allowed; weights/signals/dealer claims/performance excluded. |
| Current Robinhood/crypto developments are events, not direction (56) | Preserved | Event/source-review semantics remain non-directional. |
| Aleks Rosme not silently imported (57) | Covered | No technique promoted or claimed. |
| Real Wealth/Poverty Wedge out of scope (58) | Covered | Excluded from core proof claims. |
| Prior v5.1 data/results and hashes (91–296) | Not independently verified | The supplied ZIP contains research Parquet files, but not the cited v5.1 frozen protocols, pure-Python reader, trial ledger, result JSONs or continuation ZIP. Text-only claims are quarantined. |
| Do not retune an opened lockbox (280–282) | Enforced as policy | No failed claim is converted to PASS; promotion requires a one-time untouched lockbox artifact. |

## Coverage conclusion

All software-hardening requirements that can be implemented against the supplied source are integrated. Predictive claims whose complete evidence artifacts are absent remain unpromoted rather than being reconstructed from prose.

> **Current release: V7.7 Human-Readable Final.** It inherits the exact V7.6 proof boundary (`US_SMA10_MONTHLY_RISK_CAP` only), fixes RISK_ON/RISK_OFF display semantics, and makes the plain-language board the default. Ticker and directional capital remain blocked. See `V77_FINAL_STATUS.md`.

# v5.3 attachment continuation

This package now includes the reconciled v5.1 research ledger. Four narrow historical claims are visible as evidence only; V61 failed and V62 remains acquisition-blocked. Every such row has zero live decision weight and capital remains blocked. See `V53_ATTACHMENT_CONTINUATION_FINAL.md`.

# War Room OS v5.3 — v5.2 Real-Source Hardening + v5.1 Research Accounting

This package is the actual v4.2 application source with a v5.2 security, proof-governance, reproducibility and fail-closed hardening layer. The original visual design is preserved; the application header now reports `DECISION-INTELLIGENCE OS · v7.6 FINAL SAFE KERNEL`; the hardening base is v5.2 and the reconciled continuation release is v5.3.

## What changed materially

- Persistent pickle/joblib/dill paths were removed from active code and replaced with canonical, schema-bound JSON snapshots.
- Runtime snapshots are atomic and checked against a full SHA-256 content hash before the application accepts them.
- Editable registry booleans no longer count as proof.
- Predictive or capital promotion requires an Ed25519-signed exact-scope receipt, an out-of-band pinned trust-root hash, valid revocation state, role-bound artifact hashes, WFA, multiple-testing, costs/capacity, untouched lockbox, matured prospective evidence and human approval.
- Price context cannot become `LONG`/`SHORT` without fresh lineage, market rules, valid entry/stop/target geometry and an exact-scope capital receipt.
- Options capability is row-level and product-specific: US listed contracts; IHSG disabled; crypto requires underlying and venue; commodities require an exact futures-option contract; FX requires a listed option or valid vol-surface row. Spot cannot masquerade as options.
- Technical geometry, scenario range, fair value, calibrated probability and expected value are separate objects.
- Validators run with warnings-as-errors, check child return codes and timeouts, execute on fresh copies, and fail if they mutate immutable source.
- Statistical validation includes both a negative-control noise factor and a planted positive-control factor; the validator exits nonzero if either control behaves incorrectly.

## Default state

```text
predictive components promoted: 0
capital permission: BLOCKED
```

That state is deliberate. Software hardening is not evidence of forecast skill or profitability.

## Windows start

Run:

```text
CHECK_AND_RUN.bat
```

It installs the pinned runtime dependencies, verifies the v5.3 manifest, runs strict software/statistical tests, performs an offline collector cycle, checks the actual Streamlit `/_stcore/health` endpoint, and launches only after validation clears.

See `START_HERE.md`, `V53_ATTACHMENT_CONTINUATION_FINAL.md`, `V53_RELEASE_CLEAN_EXTRACT_VALIDATION.json`, and `WHAT_IS_AND_IS_NOT_PROVEN.md`.

## v5.5 options continuation

The supplied gamma-scalping video has been mapped into `options_volatility_flow.py` and a frozen V71 prospective protocol. Options output is volatility/range and mechanical-flow research only. Chain composition is not spot direction; public OI is unsigned; call/put concentration zones are not targets; capital remains blocked.

See `V55_OPTIONS_VOLATILITY_FLOW_FINAL_STATUS.md` and `V55_VIDEO_TO_IMPLEMENTATION_MATRIX.md`.

## V6.6 scoped usable control

V6.6 adds one decision-usable component: `US_SMA10_MONTHLY_RISK_CAP`. It may only cap or reduce an independently chosen broad-US-equity exposure at a completed monthly rebalance. It cannot create exposure, select tickers, short, set targets, predict crashes, or transfer to another market.

Run the bundled snapshot check with:

```bash
python run_v66_risk_cap.py --csv research_v66/data/sp500_monthly_shiller.csv --as-of 2026-07-26
```

Every future ticker or directional model must first write zero-capital forecasts to the V6.6 append-only prospective shadow ledger.

## V7.6 final release boundary

Run `python validate_v76_final.py` or `CHECK_FINAL_V76.bat`. The release is final for the exact confirmed broad-US-equity monthly exposure-cap scope. All ticker, directional, target, timing, leverage, crash-prediction, and cross-market capital permissions remain fail-closed.
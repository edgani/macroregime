# R7.1 Acceptance — Alpha Center Integrity Repair (2026-07-29)

Checkpoint tag: PRE_R7_1_ALPHA_INTEGRITY_REPAIR. Base: R7 45b9101 (pushed).

## Forensic archive (nothing deleted)

docs/audit/r7_1_forensics/: ARCHIVE_MANIFEST.json (exact commit 45b9101,
data-as-of, SHA-256 of compute.py/render.py/tracker.py/app.py), screenshots_pre_repair/
(tab_03_alpha_center.png), FIELD_TRACE.md (every displayed field traced to source,
formula, constant, violation).

## Violations found and fixed at root

| # | Violation | Root | Fix |
|---|---|---|---|
| V1 | Momentum/SMA score presented as alpha | compute.py `_rank()` rows → conviction/watchlist | conviction/watchlist now honest empty; pool preserved as legacy_momentum_scan alpha_weight 0 |
| V2 | US-only pool rendered as "cross-market competitive ranking" | render.alpha() header/cards | render.alpha() rewritten: five-market coverage board |
| V3 | RS63/momentum as selection rationale | watchlist rows "RS x% · entry" | removed from alpha tab |
| V4 | Generic ±3% stop/target bands (px*.97/px*1.03) | `_rank` fallback | confined to legacy scan; never reaches alpha output (test-enforced) |
| V5 | Technical-only Long/Short direction | trend+rs63 sign | no direction shown in alpha tab until proof-gated |
| V6 | Unproven momentum signals entering prospective DB | app.py TR.log_signals(d["conviction"]) | conviction now proof-gated only (empty) — DB receives nothing unproven |
| V7 | Same pool in two lists | conviction + watchlist from one pool | single canonical board; no duplicate tickers (test-enforced) |
| V8 | Confidence as probability / data quality as shadow key | not present in restored repo code (screenshot predates restore) | render now labels confidence uncalibrated; shadow infra separated from eligibility (test-enforced) |
| V9 | V10.1 branding | not present in restored repo (verified app.py/render.py/compute.py/config.py) | test-enforced absence |

## New Alpha Center content

Tradable Now: explicit NO TRADE + exact reason (no PROVEN_FOR_EXACT_CLAIM component;
47/48 families DATA_GATED, 1 preliminary with no edge).
Activation board: 10 research theses with traffic lights + gated-input counts.
Five-market coverage: families/gated/tested per market.
Excluded / missing data: per-family gating reasons.
Legacy scan: retained in compute output (pool_size shown), alpha weight 0, not rendered as signal.

## Tests

tests/test_r7_1_alpha_integrity.py — 8 tests covering every required check in the
master prompt Part III. Full suite: 192 passed + 2 slow-boot (RUN_SLOW=1 verified,
11 tabs render with new alpha board, 119s).

## Honest limits

Tradable Now is empty — that is the correct output today, not a placeholder wall:
the no-trade reason is specific and links to the exact gating artifacts. FX packet
upgraded to full canonical schema (sample_packets_r7.json regenerated). No formula
was tuned; no candidate was promoted; no prospective evidence fabricated.

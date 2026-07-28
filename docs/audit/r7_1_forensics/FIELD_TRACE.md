# R7.1 Field Trace — Alpha Center (pre-repair, commit 45b9101)

Every displayed field traced to source. Violations marked [V].

| Field | Source | Formula/Constant | Violation |
|---|---|---|---|
| Scanned | compute.py `_rank` input `D.US_NAMES` | len(US names) | OK (count only) |
| Ranked | compute.py line ~419 | len(pool) | OK (count only) |
| Conviction cards | compute.py `_rank()` rows[:4] | score = abs(rs63)*2.2 + abs(mom63) + abs(above50)*0.7 ± regime adj − crowding*0.45 | [V1] pure price momentum/SMA score as alpha; [V2] US-only yet rendered as "cross-market competitive ranking" (universal-score claim) |
| Watchlist rows | `_rank()` rows[4:12] | same score, disp = 10*score/dmax | [V1][V2] |
| RS% | `_rank` rs63 | 63d return − SPY 63d return | [V3] momentum displayed as selection rationale |
| entry | `_rr()` or fallback | px*0.97 / px*1.03 generic bands | [V4] generic ±3% stop/target when `_rr` missing — exactly the forbidden "generic multiplier" pattern |
| Direction Long/Short | trend+rs63 sign | SMA20/SMA50 + 63d RS | [V5] technical-only direction |
| Shadow/forward log | app.py `TR.log_signals(d["conviction"])` | logs momentum signals PIT into tracker DB | [V6] unproven momentum signals entering prospective pipeline without proof_state gate |
| Branding | render mission header | "WAR ROOM" | no V10.1 string found in restored repo (screenshot branding predates restore; verified absent) |
| Duplicate tickers | conviction + watchlist from same pool | — | [V7] same score pool renders in two lists; single canonical card rule violated |
| Confidence/expected return/R-R | R7 board has none; legacy cards show score only | — | the +50-128% expected-return / 15-21 R-R figures in the audited screenshot came from the pre-restore V10.x build; restored repo has no such fields (verified) — legacy violations still fixed at root |

## Repair actions (this commit)

1. `_rank` output disconnected from alpha conviction/watchlist; preserved as
   `legacy_momentum_scan` with alpha_weight 0 (functionality preserved, zero weight).
2. `conviction`/`watchlist` now sourced from the R7 alpha board: empty Tradable Now
   (explicit NO TRADE) — no momentum rows may appear.
3. `tracker.log_signals` receives only gated candidates (currently none) — unproven
   signals can no longer enter the prospective DB.
4. `render.alpha` rewritten: five-market coverage, activation board, excluded/missing
   data, explicit NO-TRADE, no score cards, no duplicate tickers.
5. Forensic archive: screenshots_pre_repair/ + ARCHIVE_MANIFEST.json (hashes, commit).

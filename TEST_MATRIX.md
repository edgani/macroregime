# Test Matrix — v3.2.1

| Area | Status | Evidence |
|---|---|---|
| Existing v3.1 core regressions | PASS | original 16 tests preserved |
| Longitudinal event memory | PASS | immutable first detection + restart persistence |
| Lifecycle memory | PASS | state changes append; invalidated events retained |
| Outcome math | PASS | absolute, benchmark-relative, MFE/MAE path test |
| Walk-forward chronology | PASS | training years strictly precede test year |
| No random split | PASS | structural acceptance |
| No autotrading | PASS | structural acceptance |
| No primary classic-indicator dependency in new discovery layer | PASS | structural acceptance |
| Multi-market architecture | PASS | US/IHSG/HK/China/Europe/Taiwan/Crypto/FX/Commodity contracts |
| Insufficient-sample fail-closed behavior | PASS | empty/no-mature-outcome output remains gated |
| UI contract | PASS | dense tracker + dense three-column control room compile |
| Workspace navigation | PASS | native button router; persistent state; rendered before scan; nav rerun skips one stale refresh |
| Full historical alpha proof | NOT CLAIMED | requires matured prospective/PIT outcomes |

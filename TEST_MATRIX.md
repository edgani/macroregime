# Test Matrix — v3.0

| Layer | Test | Status |
|---|---|---|
| syntax | app + all legacy/v3 modules compile | PASS |
| shared kernel | robust baseline/change | PASS |
| shared kernel | sequence order / duplicate compression | PASS |
| Market Memory | append/read chronology | PASS |
| vertical readiness | missing causal families fail closed | PASS |
| DeFiLlama | chain TVL/stablecoin/DEX/fees/revenue contract | PASS (mocked) |
| decision | entry != detection | PASS |
| expression | leverage/options fail closed | PASS |
| IHSG product | cash-only | PASS |
| IHSG transaction | missing API keys fail closed | PASS |
| IHSG transaction | broker concentration / persistence | PASS |
| IHSG transaction | negotiated-market contamination guard | PASS |
| IHSG transaction | bounded transaction evidence family | PASS |
| macro | missing critical feeds => MACRO GATED | PASS |
| replay | publication/execution timestamp contract | PASS |
| robustness | negative controls / fuzz | PASS |
| walk-forward | purge/embargo mechanics | PASS |
| visual | decision-first board contract | PASS |
| live DeFiLlama network | isolated build container has no reliable external network | NOT VERIFIED LIVE |
| live Index Alpha/Invezgo auth | user credentials required | GATED BY CREDENTIALS |
| full-universe real PIT/OOS alpha | historical datasets required | GATED |

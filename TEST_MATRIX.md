# Test Matrix — v2.6

| Layer | Test | Status |
|---|---|---|
| syntax | app / macro / decision / adapters / IHSG transaction | PASS |
| internal data | universe / causal graph / fixtures | PASS |
| decision | entry != detection | PASS |
| expression | leverage/options fail closed | PASS |
| expression UX | FX/Commodity/Crypto remain visible | PASS |
| IHSG product | no leverage/options | PASS |
| IHSG transaction | missing API keys fail closed | PASS |
| IHSG transaction | broker concentration / persistence | PASS |
| IHSG transaction | negotiated-market contamination guard | PASS |
| IHSG transaction | bounded transaction evidence family | PASS |
| IHSG microstructure | order-book imbalance / absorption guard | PASS |
| options | US + BTC/ETH support contract | PASS |
| macro | missing critical feeds => MACRO GATED | PASS |
| replay | publication/execution timestamp contract | PASS |
| robustness | negative controls / fuzz | PASS |
| walk-forward | purge/embargo mechanics | PASS |
| visual | simple board / top cards / mode strip / collapsed advanced view | PASS |
| live provider auth | requires user Index Alpha/Invezgo keys | GATED BY CREDENTIALS |
| full-universe real PIT/OOS alpha | historical datasets required | GATED |

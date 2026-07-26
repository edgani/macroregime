# Review Build — What Changed

This build uses the exact uploaded War Room ZIP as its base. The original `app.py` still renders the original `dashboard.html`, and all 14 original tabs remain in the same order.

Integrated results appear inside the existing interface:

- **Mission Control:** Alpha Proof Factory status strip.
- **Alpha:** proof state, real shadow shortlist when available, then the original structural cards.
- **US Stocks:** a separate Alpha Foundry selector panel; original tactical setup panel remains.
- **Validation:** CPI/Labor final-negative verdict, trial counts, claim ceiling, lockbox/prospective status.
- **Sidebar:** optional Quick pipeline runner.

No standalone Alpha Foundry UI replaces the War Room. If the real data pipeline has not run, the app shows `RUNNER_READY_NOT_EXECUTED` and zero shortlist rather than invented tickers.

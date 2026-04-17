# MacroRegime Pro — Refactored Run-Ready Build

This archive is a real refactor on top of the uploaded current repo.

What changed:
- `app.py` is replaced with the new control-tower + market-action entry
- legacy single-file app is preserved as `app_legacy_singlefile.py`
- new modules added: `ui/refactor_runtime.py`, `ui/refactor_pages.py`
- top navigation is now: Dashboard / US Stocks / IHSG / Forex / Commodities / Crypto / Risk / Diagnostics
- dashboard includes scenario stack, why-this-is-moving, and ticker attack matrix
- market pages are ticker-first
- IHSG is buy-only surface
- US / FX / Commodities / Crypto expose long + short surfaces

Run:
```bash
pip install -r requirements.txt
streamlit run app.py
```

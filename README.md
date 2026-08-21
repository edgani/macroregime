# EROS Final Software Build — Scope-Limited Scientific Evidence

This package is the portable EROS research/decision engine built from the audited Warroom/EROS work.

## Run

Linux/macOS:
```bash
python -m pip install -r requirements.txt
./run_eros.sh
```

Windows:
```bat
py -m pip install -r requirements.txt
run_eros.bat
```

Open `dashboard.html` for the five-tab static current-state view.

## What is production-safe now
- Fail-closed scenario/ticker behavior.
- General claim/event routing that requires verification before scenario formation.
- Generalized causal scenario discovery plus the user-supplied acceptance cases.
- Historical scope-limited multi-engine validation artifacts.
- No classic technical indicator as production directional alpha.
- No numeric probability if calibration is absent.
- No ticker recommendation if company/PIT/priced-in/EV evidence is absent.
- Public-source fetch adapters for BLS, World Bank, SEC, Treasury FiscalData and optional FRED.

## Scientific scope
`FINAL_HANDOFF/100_STRICT_ACCEPTANCE_RESULT.json` is authoritative.
Software acceptance passes. Full scientific scope remains blocked by documented data debt (notably full PIT-vintage global panels, IHSG/crypto/FX outcomes, modern PIT company fundamentals and calibrated ticker ranker history).

This package must not silently convert that missing evidence into a trade. Current output is `NO_QUALIFIED_OPPORTUNITY` until all ticker gates are factual and calibrated.

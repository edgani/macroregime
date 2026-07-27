@echo off
cd /d %~dp0
python validate_v91_proof_plane.py
python audit_all_markets_v91.py --root runtime\market_evidence --out V91_CURRENT_READINESS_AUDIT.json
pause

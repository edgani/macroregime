@echo off
python validate_v89_real_data_runner.py
python proof_readiness_audit.py --root runtime\market_evidence --out V89_CURRENT_REAL_DATA_AUDIT.json
pause

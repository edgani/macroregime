@echo off
python validate_v90_root_cause.py
python validate_v89_real_data_runner.py
python validate_v89_all_market_projection.py
python audit_all_markets_v90.py --root runtime\market_evidence --out V90_CURRENT_ROUTE_AUDIT.json
pause

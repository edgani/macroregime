@echo off
cd /d "%~dp0"
python validate_v98_limited_production.py
python validate_v98_unified_packet.py
pause

@echo off
setlocal
cd /d "%~dp0"
python validate_v97_limited_production.py
if errorlevel 1 exit /b 1
python trading_readiness_v97.py
if errorlevel 1 exit /b 1
echo V9.7 validation complete.

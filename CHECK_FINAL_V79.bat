@echo off
setlocal
cd /d "%~dp0"
echo Validating War Room OS V7.9 Final Proven Core...
set WARROOM_V79_DISABLE_LIVE_FETCH=1
python validate_v79_final_core.py
if errorlevel 1 (
  echo VALIDATION FAILED. DO NOT TRADE.
  pause
  exit /b 1
)
echo VALIDATION PASSED.
pause

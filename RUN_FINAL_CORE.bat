@echo off
setlocal
cd /d "%~dp0"
echo War Room OS V7.9 - FINAL EXACT-SCOPE TRADING CORE
echo Reads V7.9 settings from .env. No broker order is sent.
python run_v79_trading_core.py --live
if errorlevel 1 (
  echo.
  echo RUN FAILED. No order is authorized.
)
echo.
echo Receipt: runtime\v79_last_instruction.json
pause

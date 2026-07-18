@echo off
setlocal
cd /d "%~dp0\alpha_foundry"
powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap.ps1 -Mode quick
if errorlevel 1 (
  echo [Alpha Foundry] Quick pipeline failed. Review the console output and data/source receipts.
  pause
  exit /b 1
)
echo [Alpha Foundry] Pipeline complete. Refresh War Room to load the new shortlist/trial ledger.
pause
endlocal

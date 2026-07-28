@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found.
  exit /b 1
)
py validate_v88_all_market_projection.py
if errorlevel 1 (
  echo.
  echo VALIDATION FAILED. Do not use this package.
  pause
  exit /b 1
)
echo.
echo VALIDATION PASSED. This validates software gates only; capital remains blocked.
pause

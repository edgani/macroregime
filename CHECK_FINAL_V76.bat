@echo off
setlocal
cd /d "%~dp0"
python validate_v76_final.py
if errorlevel 1 (
  echo.
  echo V7.6 FINAL VALIDATION FAILED
  exit /b 1
)
echo.
echo V7.6 FINAL VALIDATION PASSED
endlocal

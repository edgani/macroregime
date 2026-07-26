@echo off
cd /d "%~dp0"
python validate_v77_final.py
if errorlevel 1 (
  echo V7.7 FINAL VALIDATION FAILED
  pause
  exit /b 1
)
echo V7.7 FINAL VALIDATION PASSED
pause

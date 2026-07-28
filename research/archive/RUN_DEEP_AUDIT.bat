@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run RUN_APP.bat once first so the Python environment is available.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python release_validate_v6.py
if errorlevel 1 (
  echo [War Room] Deep audit failed. Review RELEASE_VALIDATION_v6.json and console output.
  pause
  exit /b 1
)
echo [War Room] Deep audit passed.
pause
endlocal

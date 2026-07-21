@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.11 or newer and enable Add Python to PATH.
  pause
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python validate_release_v32.py
if errorlevel 1 goto :fail
echo.
echo ALL CANONICAL RELEASE CHECKS PASSED.
echo Review V32_RELEASE_VALIDATION_REPORT.json for exact scope and limitations.
pause
exit /b 0
:fail
echo.
echo VALIDATION FAILED. Do not use the build until the failing check is resolved.
pause
exit /b 1

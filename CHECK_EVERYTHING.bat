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
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
call RESET_RUNTIME.bat
python validate_user_v42.py
if errorlevel 1 goto :fail
echo.
echo ALL WAR ROOM OS v4.2 USER-MACHINE CHECKS PASSED.
echo Review V42_USER_VALIDATION_REPORT.json and V42_MASTER_REAUDIT_REPORT.json.
echo The application is ready for research review. Predictive promotion remains ZERO and capital remains BLOCKED.
pause
exit /b 0
:fail
echo.
echo VALIDATION FAILED. Do not rely on this build until the failing check is resolved.
pause
exit /b 1

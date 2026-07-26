@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (echo Python 3.11+ required.& pause& exit /b 2)
if not exist ".venv\Scripts\python.exe" (py -3 -m venv .venv || goto :fail)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail
call RESET_RUNTIME.bat
python validate_user_v59.py || goto :fail
echo.
echo ALL WAR ROOM OS V5.9 CHECKS PASSED.
echo Position lifecycle is descriptive only. Live alpha is not proven and capital remains BLOCKED.
pause
exit /b 0
:fail
echo.
echo VALIDATION FAILED. Do not rely on this build.
pause
exit /b 1

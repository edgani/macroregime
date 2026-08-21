@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py
) else (
  set PY=python
)
if not exist ".venv\Scripts\python.exe" (
  echo [EROS] Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat" || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail
echo.
echo [EROS] Setup complete.
exit /b 0
:fail
echo.
echo [EROS] Setup failed. See the error above.
exit /b 1

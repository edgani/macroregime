@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Market Opportunity OS v3.2

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python 3 not found.
    echo Install Python 3.11+ and enable "Add Python to PATH", then run this file again.
    pause
    exit /b 1
  )
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating isolated environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)

set "VPY=.venv\Scripts\python.exe"
echo [2/4] Checking pip...
"%VPY%" -m pip --version >nul 2>nul || goto :fail

echo [3/4] Installing/updating required packages...
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [4/4] Starting Market Opportunity OS v3.2...
echo Close this window or press Ctrl+C to stop the local server.
"%VPY%" -m streamlit run app.py
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [ERROR] Startup failed. Read the error above; the window will stay open.
pause
exit /b 1

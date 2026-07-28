@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11 or newer first.
  exit /b 1
)
py -m pip install --upgrade pip
if errorlevel 1 exit /b 1
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo.
echo V8.8 dependencies installed.
pause

@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run RUN_QUICK.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m src.open_lockbox
if errorlevel 1 pause & exit /b 1
pause

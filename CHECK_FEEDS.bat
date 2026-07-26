@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run RUN_APP.bat once first so the Python environment is installed.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python feed_doctor.py
pause

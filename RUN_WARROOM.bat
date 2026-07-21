@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run detected. Starting CHECK_AND_RUN.bat...
  call CHECK_AND_RUN.bat
  exit /b %ERRORLEVEL%
)
call .venv\Scripts\activate.bat
python -m streamlit run app.py --server.headless true --server.address 127.0.0.1
if errorlevel 1 (
  echo War Room failed to start. Run CHECK_EVERYTHING.bat for diagnostics.
  pause
  exit /b 1
)

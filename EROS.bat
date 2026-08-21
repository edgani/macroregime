@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call setup_windows.bat || goto :fail
)
call ".venv\Scripts\activate.bat" || goto :fail
python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
  python -m pip install -r requirements.txt || goto :fail
)
echo [EROS] Starting Warroom at http://localhost:8501
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
exit /b %errorlevel%
:fail
echo [EROS] Could not start. Read the error above.
pause
exit /b 1

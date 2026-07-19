@echo off
setlocal
cd /d "%~dp0"
if not exist ".env" if exist ".env.example" copy /Y ".env.example" ".env" >nul
python -c "import streamlit,yfinance,pandas,requests,dotenv" >nul 2>&1
if errorlevel 1 (
  echo Installing missing runtime dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
)
rem app.py owns the single background worker lease. Do not start a second worker here.
python -m streamlit run app.py --server.headless true --server.address 127.0.0.1
exit /b 0
:fail
echo Failed to install or start War Room OS.
pause
exit /b 1

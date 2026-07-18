@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [War Room] Creating local Python environment...
  python -m venv .venv
  if errorlevel 1 goto :venv_error
)

call ".venv\Scripts\activate.bat"

rem Do not reinstall packages on every launch. This keeps startup working during provider/PyPI outages.
python -c "import streamlit,pandas,numpy,requests,yfinance,sklearn,statsmodels,pyarrow" >nul 2>&1
if errorlevel 1 (
  echo [War Room] Installing missing dependencies once...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [War Room] Dependency install failed. Checking whether the runtime is already usable...
    python -c "import streamlit,pandas,numpy,requests,yfinance,sklearn,statsmodels,pyarrow" >nul 2>&1
    if errorlevel 1 goto :deps_error
  )
)

if not exist ".cache\market_v6" mkdir ".cache\market_v6"
set WARROOM_DAILY_REFRESH_MINUTES=30
set WARROOM_QUOTE_REFRESH_SECONDS=180
set WARROOM_REQUEST_TIMEOUT=12
set WARROOM_FEED_WORKERS=8

streamlit run app.py --server.fileWatcherType none
if errorlevel 1 goto :run_error
goto :end

:venv_error
echo [War Room] Could not create .venv. Install Python 3.11+ and ensure python is on PATH.
pause
exit /b 1

:deps_error
echo [War Room] Required Python packages are missing and could not be installed.
echo Connect once or install from requirements.txt, then launch again. Existing market caches are not deleted.
pause
exit /b 1

:run_error
echo [War Room] Streamlit stopped with an error. Run CHECK_FEEDS.bat for provider diagnostics.
pause
exit /b 1

:end
endlocal

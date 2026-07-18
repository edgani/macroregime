@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist ".cache\market_v5" mkdir ".cache\market_v5"
set WARROOM_DAILY_REFRESH_MINUTES=30
set WARROOM_QUOTE_REFRESH_SECONDS=180
set WARROOM_REQUEST_TIMEOUT=12
streamlit run app.py --server.fileWatcherType none
pause

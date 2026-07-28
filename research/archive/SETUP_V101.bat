@echo off
setlocal
cd /d "%~dp0"
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy V101_TRADING.env.example .env >nul
echo.
echo V10.1 setup complete.
echo Next: REFRESH_V101_NOW.bat then RUN_V101_APP.bat
pause

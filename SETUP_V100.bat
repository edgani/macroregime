@echo off
setlocal
cd /d "%~dp0"
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy V100_TRADING.env.example .env >nul
echo.
echo Setup complete. Edit .env only for account equity, refresh cadence, and optional API identity.
pause

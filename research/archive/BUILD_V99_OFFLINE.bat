@echo off
setlocal
cd /d "%~dp0"
set WARROOM_NETWORK_MODE=offline
python run.py --offline --out desk_data.json --html dashboard_live.html
if errorlevel 1 (echo Offline build gagal.& pause & exit /b 1)
echo Offline dashboard selesai: dashboard_live.html
pause

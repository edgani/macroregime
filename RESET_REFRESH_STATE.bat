@echo off
setlocal
cd /d "%~dp0"
if exist ".cache\refresh_v7.lock" del /q ".cache\refresh_v7.lock"
if exist ".cache\refresh_status_v7.json" del /q ".cache\refresh_status_v7.json"
if exist ".cache\refresh_v7.log" del /q ".cache\refresh_v7.log"
echo [War Room] Background refresh state reset. Verified desk and market caches were preserved.
pause
endlocal

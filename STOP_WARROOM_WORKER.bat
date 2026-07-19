@echo off
setlocal
cd /d "%~dp0"
if not exist runtime\worker.pid exit /b 0
set /p WPID=<runtime\worker.pid
taskkill /PID %WPID% /F >nul 2>&1
del /Q runtime\worker.pid >nul 2>&1
endlocal

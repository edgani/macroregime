@echo off
setlocal
cd /d "%~dp0"
if exist runtime\worker.pid (
  set /p WPID=<runtime\worker.pid
  taskkill /PID %WPID% /T /F >nul 2>&1
)
del /Q runtime\worker.pid runtime\worker.instance.lock runtime\worker_start.lock >nul 2>&1
endlocal

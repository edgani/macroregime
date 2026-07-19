@echo off
setlocal
cd /d "%~dp0"
call STOP_WARROOM_WORKER.bat
for %%F in (runtime\desk_snapshot.json runtime\worker_status.json runtime\force_refresh.flag static\desk_snapshot.json static\worker_status.json) do del /Q "%%F" >nul 2>&1
echo Runtime state reset. Price/provider last-good caches were preserved.
endlocal

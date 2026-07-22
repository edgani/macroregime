@echo off
setlocal
cd /d "%~dp0"
call STOP_WARROOM_WORKER.bat
for %%F in (
  runtime\desk_snapshot.json
  runtime\worker_status.json
  runtime\force_refresh.flag
  runtime\worker.instance.lock
  runtime\worker.pid
  runtime\worker_boot.log
  runtime\v42_fixture_desk.json
  runtime\v42_fixture_dashboard.html
  static\desk_snapshot.json
  static\worker_status.json
) do del /Q "%%F" >nul 2>&1
if not exist runtime mkdir runtime
if not exist static mkdir static
type nul > runtime\.gitkeep
type nul > static\.gitkeep
echo Runtime state reset. Price/provider last-good caches were preserved.
endlocal

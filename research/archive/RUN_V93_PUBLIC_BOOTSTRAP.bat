@echo off
setlocal
cd /d %~dp0
if not defined WARROOM_SEC_USER_AGENT (
  echo Set WARROOM_SEC_USER_AGENT to something like WarRoomOS your_email@example.com
  exit /b 2
)
python public_data_bootstrap_v93.py %*
endlocal

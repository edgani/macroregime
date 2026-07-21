@echo off
setlocal
cd /d "%~dp0"
call RESET_RUNTIME.bat
call CHECK_EVERYTHING.bat
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_WARROOM.bat

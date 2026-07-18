@echo off
setlocal
cd /d "%~dp0"
if not exist .env (
  echo [ERROR] Copy .env.example to .env and add your provider credentials first.
  pause
  exit /b 1
)
python validate_live_stack.py || goto :fail
python verify_live_connections.py --write-report
streamlit run app.py
exit /b 0
:fail
echo Validation failed. Check the output above.
pause
exit /b 1

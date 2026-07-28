@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set /p V100_TICKER=Ticker exactly as shown in War Room: 
set /p V100_APPROVER=Approved by: 
python experimental_order_export_v100.py --ticker "%V100_TICKER%" --approved-by "%V100_APPROVER%"
pause

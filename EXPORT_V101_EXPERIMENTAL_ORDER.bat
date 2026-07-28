@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set /p V101_TICKER=Ticker exactly as shown in War Room: 
set /p V101_APPROVER=Approved by: 
python experimental_order_export_v101.py --ticker "%V101_TICKER%" --approved-by "%V101_APPROVER%"
pause

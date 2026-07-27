@echo off
setlocal
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% shadow_execution_ledger_v95.py verify --ledger runtime/v95_shadow/shadow_ledger.jsonl
pause

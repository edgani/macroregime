@echo off
setlocal
if exist .venv\Scripts\streamlit.exe (set ST=.venv\Scripts\streamlit.exe) else (set ST=streamlit)
%ST% run app.py
pause

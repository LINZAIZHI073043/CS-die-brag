@echo off
cd /d "%~dp0"
set "PYW=C:\Users\qiqi\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" edit_excuses.py
) else (
    start "" pythonw edit_excuses.py
)

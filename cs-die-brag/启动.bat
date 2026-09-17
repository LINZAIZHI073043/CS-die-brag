@echo off
chcp 65001 >nul
title CS2 Auto Excuse
cd /d "%~dp0"
echo ============================================
echo   CS2 auto-excuse tool starting...
echo   Works automatically once you are in-game.
echo   Do NOT close this window while playing.
echo   Press Ctrl+C or close window when done.
echo ============================================
echo.

set "PYEXE=C:\Users\qiqi\AppData\Local\Python\pythoncore-3.14-64\python.exe"

if exist "%PYEXE%" (
    "%PYEXE%" cs_die_brag.py 2> "%~dp0debug.log"
) else (
    py -3 cs_die_brag.py 2> "%~dp0debug.log"
)

echo.
echo --------------------------------------------
echo Script exited. If it crashed, send me debug.log
echo Press any key to close...
pause >nul

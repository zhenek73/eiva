@echo off
chcp 65001 >nul
echo ========================================
echo   EIVA - AI Digital Twin Bot
echo ========================================
echo.

REM Try py launcher first, then full path, then python
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :run
)

"c:\Users\echir\AppData\Local\Programs\Python\Python311\python.exe" --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=c:\Users\echir\AppData\Local\Programs\Python\Python311\python.exe
    goto :run
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :run
)

echo ERROR: Python not found at any known location.
echo Try running manually:
echo   c:\Users\echir\AppData\Local\Programs\Python\Python311\python.exe bot.py
pause
exit /b 1

:run
echo Using: %PYTHON%
echo.
echo Installing dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet
%PYTHON% -m pip install tonsdk --quiet
echo.
echo Starting Eiva bot...
echo Open Telegram: @eivatonbot
echo Press Ctrl+C to stop
echo.
%PYTHON% bot.py
pause

@echo off
chcp 65001 >nul
echo ========================================
echo   EIVA - AI Digital Twin Bot
echo ========================================
echo.
echo Installing dependencies...
py -m pip install -r requirements.txt --quiet
echo.
echo Starting Eiva bot...
echo Open Telegram: @eivatonbot
echo Press Ctrl+C to stop
echo.
py bot.py
pause

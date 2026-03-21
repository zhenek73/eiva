@echo off
echo Starting Eiva Web Dashboard...
echo.

REM Try python3 first, then python
where python3 >nul 2>&1
if %errorlevel% == 0 (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    cd /d "%~dp0eiva-web"
    python3 -m http.server 8080
) else (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        echo Open http://localhost:8080 in your browser
        echo Press Ctrl+C to stop
        echo.
        cd /d "%~dp0eiva-web"
        python -m http.server 8080
    ) else (
        echo ERROR: Python not found!
        echo Please install Python from https://python.org
        pause
    )
)

@echo off
echo Starting Eiva Web Dashboard...
echo.
cd /d "%~dp0eiva-web"

REM Try py launcher first (most reliable on Windows)
where py >nul 2>&1
if %errorlevel% == 0 (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    py -m http.server 8080
    goto end
)

REM Try python3
where python3 >nul 2>&1
if %errorlevel% == 0 (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    python3 -m http.server 8080
    goto end
)

REM Try full path to python if installed via standard installer
if exist "C:\Python312\python.exe" (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    C:\Python312\python.exe -m http.server 8080
    goto end
)
if exist "C:\Python311\python.exe" (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    C:\Python311\python.exe -m http.server 8080
    goto end
)
if exist "C:\Python310\python.exe" (
    echo Open http://localhost:8080 in your browser
    echo Press Ctrl+C to stop
    echo.
    C:\Python310\python.exe -m http.server 8080
    goto end
)

echo ERROR: Python not found!
echo.
echo Please do ONE of the following:
echo  1. Install Python from https://python.org (check "Add to PATH")
echo  2. Or open PowerShell and run:  python -m http.server 8080
echo     from the eiva-web folder
echo.
pause

:end

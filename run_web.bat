@echo off
echo Starting Eiva Web Dashboard...
echo Open http://localhost:8080 in your browser
echo Press Ctrl+C to stop
echo.
cd /d "%~dp0eiva-web"
py -m http.server 8080

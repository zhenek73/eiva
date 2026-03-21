@echo off
echo Starting Eiva Web Dashboard...
echo Open http://localhost:8080 in your browser
cd eiva-web
python -m http.server 8080

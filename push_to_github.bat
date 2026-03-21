@echo off
echo Push to GitHub
echo.

if exist ".git\index.lock" del /f ".git\index.lock"

REM Read token from .env
for /f "tokens=2 delims==" %%a in ('findstr "GITHUB_TOKEN" .env') do set GH_TOKEN=%%a

if "%GH_TOKEN%"=="" (
    set /p GH_TOKEN="Token not found in .env. Paste it manually: "
)

git remote remove origin 2>nul
git remote add origin https://zhenek73:%GH_TOKEN%@github.com/zhenek73/eiva.git

git checkout --orphan fresh_main 2>nul
if errorlevel 1 (
    REM Already on fresh branch or orphan exists, just add files
    goto :addfiles
)

:addfiles
git add .gitignore .env.example README.md requirements.txt
git add config.py parser.py embeddings.py personality.py agent.py ton_identity.py bot.py
git add run.bat push_to_github.bat

git commit -m "feat: Eiva AI Digital Twin MVP — TON Hackathon 2026" 2>nul || git commit --allow-empty -m "update"

git branch -D main 2>nul
git branch -m main 2>nul

git push origin main --force

echo.
echo Done! https://github.com/zhenek73/eiva
pause

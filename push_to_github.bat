@echo off
echo Push to GitHub (fresh history, no secrets)
echo.

if exist ".git\index.lock" del /f ".git\index.lock"

set /p GH_TOKEN="Paste GitHub token: "

git remote remove origin 2>nul
git remote add origin https://zhenek73:%GH_TOKEN%@github.com/zhenek73/eiva.git

REM Create orphan branch = fresh history, zero old commits with tokens
git checkout --orphan fresh_main

git add .gitignore .env.example README.md requirements.txt
git add config.py parser.py embeddings.py personality.py agent.py ton_identity.py bot.py
git add run.bat push_to_github.bat

git commit -m "feat: Eiva AI Digital Twin MVP — TON Hackathon 2026"

REM Replace main with the clean branch
git branch -D main 2>nul
git branch -m main

git push origin main --force

echo.
echo Done! https://github.com/zhenek73/eiva
pause

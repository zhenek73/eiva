# Eiva Bot — PowerShell setup & run script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EIVA — AI Digital Twin Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Install from https://python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`n✅ All dependencies installed" -ForegroundColor Green
Write-Host "`n🚀 Starting Eiva bot..." -ForegroundColor Cyan
Write-Host "Open Telegram → @eivatonbot" -ForegroundColor White
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

python bot.py

Read-Host "Press Enter to exit"

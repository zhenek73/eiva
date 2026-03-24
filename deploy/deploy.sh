#!/bin/bash
# ═══════════════════════════════════════════════
#  EIVA — Deploy script (runs on server via CI)
#  Called by GitHub Actions on every push to main
# ═══════════════════════════════════════════════
set -e

APP_DIR="/var/www/eiva-bot/eiva-bot"
cd "$APP_DIR"

echo "[deploy] Pulling latest code..."
git pull origin main

echo "[deploy] Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt -q
pip install fastapi uvicorn[standard] python-multipart -q
deactivate

echo "[deploy] Restarting services..."
systemctl restart eiva-api
systemctl restart eiva-bot

echo "[deploy] Checking status..."
sleep 2
systemctl is-active eiva-api && echo "  eiva-api: OK" || echo "  eiva-api: FAILED"
systemctl is-active eiva-bot && echo "  eiva-bot: OK" || echo "  eiva-bot: FAILED"

echo "[deploy] Done! $(date)"

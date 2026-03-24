#!/bin/bash
# ═══════════════════════════════════════════════════════
#  EIVA — QuickStart (no systemd, no apt, no venv)
#  Works in FASTPANEL containers and restricted environments
#  curl -o qs.sh https://raw.githubusercontent.com/zhenek73/eiva/main/deploy/quickstart.sh && bash qs.sh
# ═══════════════════════════════════════════════════════

BOT_DIR="/var/www/eiva/eiva-bot"
LOG_DIR="$BOT_DIR/logs"
mkdir -p "$LOG_DIR"

cd "$BOT_DIR"

echo ""
echo "════════════════════════════════════"
echo "  EIVA QuickStart"
echo "════════════════════════════════════"

# ── Detect python ──
PY=$(command -v python3 || command -v python || echo "")
if [ -z "$PY" ]; then
    echo "[ERROR] Python not found!"
    exit 1
fi
echo "[OK] Python: $($PY --version 2>&1)"

# ── Detect pip ──
PIP=$(command -v pip3 || command -v pip || echo "")
if [ -z "$PIP" ]; then
    echo "[WARN] pip not found, trying to install..."
    $PY -m ensurepip --upgrade 2>/dev/null || true
    PIP=$(command -v pip3 || command -v pip || "$PY -m pip")
fi
echo "[OK] Pip: $($PIP --version 2>&1 | head -1)"

# ── Pull latest code ──
echo "[1] Pulling latest code..."
git -C "$BOT_DIR" pull 2>&1 | tail -3

# ── Install deps (user-level, no venv needed) ──
echo "[2] Installing Python packages..."
$PIP install --upgrade --user \
    python-telegram-bot==21.6 \
    openai chromadb aiohttp python-dotenv \
    fastapi "uvicorn[standard]" python-multipart \
    tonsdk pytoniq-core -q 2>&1 | tail -5
echo "  Packages installed"

# ── Check .env ──
if [ ! -f "$BOT_DIR/.env" ] || grep -q "FILL_IN" "$BOT_DIR/.env"; then
    echo "[!] .env missing or not filled — run step 2 from instructions!"
fi

# ── Kill old processes ──
echo "[3] Stopping old processes..."
pkill -f "uvicorn api:app" 2>/dev/null && sleep 1 && echo "  Stopped old API" || echo "  No old API running"
pkill -f "python bot.py"   2>/dev/null && sleep 1 && echo "  Stopped old bot" || echo "  No old bot running"
pkill -f "python3 bot.py"  2>/dev/null && sleep 1 || true

# ── Start API ──
echo "[4] Starting Eiva API on :8000..."
cd "$BOT_DIR"
nohup $PY -m uvicorn api:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!
echo "  API PID: $API_PID"
echo "$API_PID" > /tmp/eiva-api.pid

# ── Start Bot ──
echo "[5] Starting Telegram Bot..."
nohup $PY bot.py \
    > "$LOG_DIR/bot.log" 2>&1 &
BOT_PID=$!
echo "  Bot PID: $BOT_PID"
echo "$BOT_PID" > /tmp/eiva-bot.pid

# ── Wait and test ──
echo "[6] Testing API..."
sleep 4
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if echo "$HEALTH" | grep -q "ok"; then
    echo "  ✅ API is UP: $HEALTH"
else
    echo "  ⚠️  API not responding yet. Check: tail -20 $LOG_DIR/api.log"
    tail -10 "$LOG_DIR/api.log" 2>/dev/null || true
fi

# ── Crontab for persistence ──
echo "[7] Setting up auto-restart on reboot..."
CRON_API="@reboot cd $BOT_DIR && $PY -m uvicorn api:app --host 0.0.0.0 --port 8000 >> $LOG_DIR/api.log 2>&1 &"
CRON_BOT="@reboot cd $BOT_DIR && $PY bot.py >> $LOG_DIR/bot.log 2>&1 &"
(crontab -l 2>/dev/null | grep -v "eiva"; echo "$CRON_API"; echo "$CRON_BOT") | crontab -
echo "  Crontab updated (runs on reboot)"

echo ""
echo "════════════════════════════════════"
echo "  Done!"
echo "════════════════════════════════════"
echo "  API:  curl http://localhost:8000/health"
echo "  Logs: tail -f $LOG_DIR/api.log"
echo "        tail -f $LOG_DIR/bot.log"
echo ""

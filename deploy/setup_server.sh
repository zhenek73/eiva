#!/bin/bash
# ═══════════════════════════════════════════════════════
#  EIVA — One-time server setup script
#  Run once on your TimeWeb VPS:
#    bash setup_server.sh
# ═══════════════════════════════════════════════════════
set -e

REPO="https://github.com/zhenek73/eiva.git"
APP_DIR="/var/www/eiva-bot"
PYTHON_BIN="python3"
SERVICE_USER="root"

echo "════════════════════════════════════"
echo "  EIVA Server Setup"
echo "════════════════════════════════════"

# ── 1. System packages ──
echo "[1/8] Installing system packages..."
apt-get update -q
apt-get install -y -q \
    git curl wget \
    python3 python3-pip python3-venv \
    build-essential libssl-dev libffi-dev \
    sqlite3

# ── 2. Clone repo ──
echo "[2/8] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "  Already exists, pulling latest..."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi
cd "$APP_DIR/eiva-bot"

# ── 3. Python venv + deps ──
echo "[3/8] Setting up Python virtual environment..."
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
# Extra packages for API
pip install fastapi uvicorn[standard] python-multipart -q
deactivate

# ── 4. .env file (if not exists) ──
echo "[4/8] Checking .env file..."
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY_HERE
LLM_MODEL=openai/gpt-4o-mini
LLM_SMART_MODEL=openai/gpt-4o
EMBEDDING_MODEL=openai/text-embedding-3-small
TON_MNEMONIC=word1 word2 ... word24
TON_NETWORK=testnet
GITHUB_TOKEN=YOUR_GITHUB_PAT_HERE
ENVEOF
    echo "  ⚠️  IMPORTANT: Edit /var/www/eiva-bot/eiva-bot/.env with your real keys!"
else
    echo "  .env already exists, skipping"
fi

# ── 5. Create data directories ──
echo "[5/8] Creating data directories..."
mkdir -p data/chroma data/exports
chmod 755 data data/chroma data/exports

# ── 6. Systemd — Telegram Bot ──
echo "[6/8] Creating systemd service: eiva-bot..."
cat > /etc/systemd/system/eiva-bot.service << EOF
[Unit]
Description=Eiva Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR/eiva-bot
ExecStart=$APP_DIR/eiva-bot/venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=$APP_DIR/eiva-bot/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=eiva-bot

[Install]
WantedBy=multi-user.target
EOF

# ── 7. Systemd — FastAPI ──
echo "[7/8] Creating systemd service: eiva-api..."
cat > /etc/systemd/system/eiva-api.service << EOF
[Unit]
Description=Eiva FastAPI Backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR/eiva-bot
ExecStart=$APP_DIR/eiva-bot/venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
EnvironmentFile=$APP_DIR/eiva-bot/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=eiva-api

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable eiva-bot eiva-api
echo "  Services created. Start with: systemctl start eiva-bot eiva-api"

# ── 8. Nginx config ──
echo "[8/8] Creating nginx config..."
cat > /etc/nginx/conf.d/eiva-api.conf << 'NGINXEOF'
# Eiva API — reverse proxy
# Accessible at: http://YOUR_DOMAIN/api/
# or directly at port 8000 internally

server {
    listen 80;
    server_name api.eiva-app.com 83.217.220.81;  # TODO: replace with your domain

    # API backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        client_max_body_size 20m;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }

    # CORS preflight
    location ~ /api/(.*)$ {
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, X-Wallet-Address, X-Demo-Mode";
            return 204;
        }
    }
}
NGINXEOF

# Test nginx config
if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo "  Nginx reloaded OK"
else
    echo "  ⚠️  Nginx test failed — check /etc/nginx/conf.d/eiva-api.conf"
    echo "  FASTPANEL might use different config location, see deploy/README.md"
fi

echo ""
echo "════════════════════════════════════"
echo "  Setup complete!"
echo "════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit .env: nano $APP_DIR/eiva-bot/.env"
echo "  2. Start services: systemctl start eiva-bot eiva-api"
echo "  3. Check status:   systemctl status eiva-bot eiva-api"
echo "  4. View logs:      journalctl -u eiva-bot -f"
echo "                     journalctl -u eiva-api -f"
echo "  5. Test API:       curl http://localhost:8000/health"
echo ""

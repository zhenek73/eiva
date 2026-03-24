#!/bin/bash
# ═══════════════════════════════════════════════════════
#  EIVA — Server Setup (Ubuntu / CentOS / AlmaLinux)
#  curl -o setup.sh https://raw.githubusercontent.com/zhenek73/eiva/main/deploy/setup_server.sh
#  bash setup.sh
# ═══════════════════════════════════════════════════════
set -e

REPO="https://github.com/zhenek73/eiva.git"
APP_DIR="/var/www/eiva"
BOT_DIR="$APP_DIR/eiva-bot"

echo ""
echo "════════════════════════════════════"
echo "  EIVA Server Setup"
echo "════════════════════════════════════"

# ── Detect OS & package manager ──
if command -v apt-get &>/dev/null; then
    PKG="apt"
    echo "[OS] Debian/Ubuntu — using apt"
elif command -v dnf &>/dev/null; then
    PKG="dnf"
    echo "[OS] AlmaLinux/CentOS — using dnf"
elif command -v yum &>/dev/null; then
    PKG="yum"
    echo "[OS] CentOS — using yum"
else
    PKG="none"
    echo "[OS] Unknown — skipping package install"
fi

pkg_install() {
    case "$PKG" in
        apt) apt-get install -y -q "$@" ;;
        dnf) dnf install -y -q "$@" ;;
        yum) yum install -y -q "$@" ;;
    esac
}

# ── 1. System packages ──
echo "[1/7] Installing system packages..."
case "$PKG" in
    apt)
        apt-get update -q
        pkg_install git curl python3 python3-pip python3-venv build-essential libssl-dev libffi-dev
        ;;
    dnf|yum)
        pkg_install git curl python3 python3-pip gcc openssl-devel libffi-devel
        ;;
esac
echo "  OK — $(python3 --version)"

# ── 2. Clone or update repo ──
echo "[2/7] Setting up repository..."
mkdir -p /var/www
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR" && git pull && echo "  Updated"
else
    git clone "$REPO" "$APP_DIR" && echo "  Cloned"
fi
cd "$BOT_DIR"

# ── 3. Python venv + deps ──
echo "[3/7] Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install fastapi "uvicorn[standard]" python-multipart -q
deactivate
echo "  venv ready"

# ── 4. .env template ──
echo "[4/7] Creating .env template..."
if [ ! -f "$BOT_DIR/.env" ]; then
cat > "$BOT_DIR/.env" << 'ENVEOF'
TELEGRAM_BOT_TOKEN=FILL_IN
OPENROUTER_API_KEY=FILL_IN
LLM_MODEL=openai/gpt-4o-mini
LLM_SMART_MODEL=openai/gpt-4o
EMBEDDING_MODEL=openai/text-embedding-3-small
TON_MNEMONIC=FILL_IN
TON_NETWORK=testnet
GITHUB_TOKEN=FILL_IN
ENVEOF
    chmod 600 "$BOT_DIR/.env"
    echo "  Template created — fill with your keys (see instructions below)"
else
    echo "  .env already exists — skipping"
fi

# ── 5. Data dirs ──
echo "[5/7] Data directories..."
mkdir -p "$BOT_DIR/data/chroma" "$BOT_DIR/data/exports" "$BOT_DIR/logs"
echo "  OK"

# ── 6. Systemd services ──
echo "[6/7] Systemd services..."
if command -v systemctl &>/dev/null; then

cat > /etc/systemd/system/eiva-bot.service << EOF
[Unit]
Description=Eiva Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=$BOT_DIR/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=eiva-bot

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/eiva-api.service << EOF
[Unit]
Description=Eiva FastAPI Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
EnvironmentFile=$BOT_DIR/.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=eiva-api

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable eiva-bot eiva-api
    echo "  eiva-bot + eiva-api enabled"

else
    # No systemd — create start script
    cat > "$BOT_DIR/start.sh" << EOF
#!/bin/bash
cd $BOT_DIR && source venv/bin/activate
nohup python bot.py > logs/bot.log 2>&1 & echo \$! > /tmp/eiva-bot.pid
nohup uvicorn api:app --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 & echo \$! > /tmp/eiva-api.pid
echo "Started: bot=\$(cat /tmp/eiva-bot.pid) api=\$(cat /tmp/eiva-api.pid)"
EOF
    chmod +x "$BOT_DIR/start.sh"
    echo "  systemd not found — use: bash $BOT_DIR/start.sh"
fi

# ── 7. Nginx & firewall ──
echo "[7/7] Nginx reverse proxy (port 8001)..."
NGINX_CONF=""
[ -d /etc/nginx/conf.d ]     && NGINX_CONF="/etc/nginx/conf.d/eiva-api.conf"
[ -d /etc/nginx/sites-available ] && NGINX_CONF="/etc/nginx/sites-available/eiva-api.conf"

if [ -n "$NGINX_CONF" ]; then
cat > "$NGINX_CONF" << 'NGINXEOF'
server {
    listen 8001;
    server_name _;
    client_max_body_size 25m;

    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET,POST,OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type,X-Wallet-Address,X-Demo-Mode" always;

    location / {
        if ($request_method = OPTIONS) { return 204; }
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
NGINXEOF
    [ -d /etc/nginx/sites-enabled ] && \
        ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/eiva-api.conf 2>/dev/null || true
    nginx -t 2>/dev/null && (systemctl reload nginx 2>/dev/null || nginx -s reload 2>/dev/null)
    echo "  Nginx configured on :8001"
fi

# Open firewall
command -v firewall-cmd &>/dev/null && \
    firewall-cmd --permanent --add-port=8001/tcp 2>/dev/null && \
    firewall-cmd --reload 2>/dev/null && echo "  Port 8001 opened" || true

echo ""
echo "════════════════════════════════════"
echo "  Setup complete!"
echo "════════════════════════════════════"
echo ""
echo "  ⚠️  NEXT: fill in your .env keys:"
echo "     cat > $BOT_DIR/.env << 'EOF'"
echo "     TELEGRAM_BOT_TOKEN=..."
echo "     ... etc"
echo "     EOF"
echo ""
echo "  Then start:"
if command -v systemctl &>/dev/null; then
    echo "     systemctl start eiva-bot eiva-api"
    echo "     systemctl status eiva-bot eiva-api"
else
    echo "     bash $BOT_DIR/start.sh"
fi
echo ""
echo "  Test: curl http://localhost:8000/health"

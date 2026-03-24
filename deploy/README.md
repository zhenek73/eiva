# Eiva — Deploy Guide

## Архитектура

```
Vercel (фронт)          TimeWeb VPS (83.217.220.81)
eiva-app.vercel.app ──▶ nginx (FastPanel)
                         ├── PHP проект (твой существующий)
                         └── /api/* → uvicorn:8000 (FastAPI)

                         systemd services:
                         ├── eiva-bot  (Telegram бот)
                         └── eiva-api  (FastAPI backend)
```

---

## 1. Первый деплой на сервер

### Подключись по SSH
```bash
ssh root@83.217.220.81
```

### Скачай и запусти setup скрипт
```bash
curl -o setup.sh https://raw.githubusercontent.com/zhenek73/eiva/main/eiva-bot/deploy/setup_server.sh
bash setup.sh
```

### Заполни .env
```bash
nano /var/www/eiva-bot/eiva-bot/.env
```
Вставь реальные значения:
```
TELEGRAM_BOT_TOKEN=...
OPENROUTER_API_KEY=...
LLM_MODEL=openai/gpt-4o-mini
LLM_SMART_MODEL=openai/gpt-4o
EMBEDDING_MODEL=openai/text-embedding-3-small
TON_MNEMONIC=...
TON_NETWORK=testnet
GITHUB_TOKEN=...
```

### Запусти сервисы
```bash
systemctl start eiva-bot eiva-api
systemctl status eiva-bot eiva-api
```

### Проверь API
```bash
curl http://localhost:8000/health
# {"status":"ok","service":"eiva-api","version":"1.0.0"}
```

---

## 2. Nginx в FASTPANEL

FASTPANEL управляет nginx через свой интерфейс (http://83.217.220.81:8888).

**Вариант A — через FASTPANEL:**
1. Войди в панель → Сайты → Добавить сайт
2. Домен: `api.твойдомен.ru` (или используй IP)
3. В доп. настройках nginx добавь:
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    client_max_body_size 20m;
    proxy_read_timeout 120s;
}
location /health {
    proxy_pass http://127.0.0.1:8000/health;
}
```

**Вариант B — прямой доступ по IP:порту:**
Если домена нет, открой порт 8000 в файрволе и используй `http://83.217.220.81:8000`:
```bash
ufw allow 8000/tcp
```
Тогда в Vercel фронте VITE_API_URL=http://83.217.220.81:8000

---

## 3. Настройка GitHub Actions (auto-deploy)

В GitHub репо → Settings → Secrets → Actions → добавь:

| Secret | Value |
|--------|-------|
| `VPS_HOST` | `83.217.220.81` |
| `VPS_USER` | `root` |
| `VPS_PASSWORD` | твой root пароль |

После этого каждый `git push` в `main` автоматически деплоит на сервер.

---

## 4. Vercel (фронт)

1. Зайди на vercel.com → New Project → Import Git Repository
2. Выбери `zhenek73/eiva`
3. Framework Preset: **Other**
4. Root Directory: `eiva-bot/docs`
5. Build Command: *(пусто — статика)*
6. Output Directory: `.`
7. Add Environment Variable: `VITE_API_URL` = `http://83.217.220.81:8000` (или твой домен)
8. Deploy!

---

## 5. PHP проект — не трогаем

Твой PHP проект работает как обычно через FASTPANEL.
Python сервисы работают на других портах (8000).
nginx/FASTPANEL разруливает трафик по доменам.
Конфликтов нет.

---

## Команды управления

```bash
# Статус
systemctl status eiva-bot eiva-api

# Логи в реальном времени
journalctl -u eiva-api -f
journalctl -u eiva-bot -f

# Перезапуск
systemctl restart eiva-api
systemctl restart eiva-bot

# Ручной деплой (без CI)
cd /var/www/eiva-bot && bash eiva-bot/deploy/deploy.sh
```

---

## Мощности сервера

| Ресурс | Доступно | Нужно Eiva |
|--------|---------|------------|
| CPU | 4 × 3.3 GHz | ~0.5 core в idle |
| RAM | 8 GB | ~500 MB (бот+API+ChromaDB) |
| Disk | 52 GB free | ~2 GB (ChromaDB растёт с юзерами) |
| **Вывод** | **✅ Хватит на 100+ юзеров** | |

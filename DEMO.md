# EIVA — Demo Guide

> Try EIVA without uploading your own data using the Pavel Durov demo twin.

## 🌐 Web Demo (Fastest)

1. Open [eiva.space/app.html](https://eiva.space/app.html)
2. Click **"View Durov Demo Cabinet"** — no wallet needed
3. Go to the **💬 Chat** tab
4. Ask anything: *"What do you think about privacy?"*, *"Tell me about Telegram"*, *"What's your daily routine?"*

The demo twin responds in Durov's voice based on 60 real public posts and interviews.

---

## 🤖 Telegram Demo

Open [@eivatonbot](https://t.me/eivatonbot) and send `/demo`

---

## ⚡ API Demo

```bash
# Chat with Durov twin directly
curl -X POST https://api.eiva.space/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What do you think about AI and freedom?",
    "wallet_address": "demo",
    "demo_mode": true
  }'

# Get Durov profile
curl https://api.eiva.space/api/demo/profile
```

---

## 📦 Full Flow (Your Own Twin)

1. Export your Telegram: **Settings → Advanced → Export Telegram Data → JSON**
2. Open [eiva.space](https://eiva.space) → Connect TON wallet (Tonkeeper testnet)
3. Upload your JSON in the **My Cabinet** section
4. Wait ~60 seconds while your twin is built
5. Chat with your twin in the **💬 Chat** tab
6. Mint your Soul Certificate in **🎫 Soul Certificate**

---

## Load Demo Data on Server

```bash
cd /var/www/eiva
python3 demo_data/create_durov_demo.py
```

Indexes 60 messages, extracts personality via GPT-4o, saves to ChromaDB.

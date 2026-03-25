# EIVA — Embedded Intelligence Virtual Avatar

> *Reconstruct your personality from chat history. Own it as a TON Soulbound NFT.*

[![Live Demo](https://img.shields.io/badge/Live-eiva.space-00E5FF)](https://eiva.space)
[![API](https://img.shields.io/badge/API-api.eiva.space-brightgreen)](https://api.eiva.space/health)
[![Bot](https://img.shields.io/badge/Telegram-@eivatonbot-2CA5E0)](https://t.me/eivatonbot)
[![TON](https://img.shields.io/badge/TON-Testnet-0088CC)](https://testnet.tonscan.org)
[![Hackathon](https://img.shields.io/badge/TON%20AI-Hackathon%202026-FF4500)](https://identityhub.app)

---

## What is EIVA?

Every day you leave traces of yourself in chats — your jokes, your opinions, the way you explain things. That personality is never captured. It just disappears into message history.

**EIVA reconstructs you.**

Upload your Telegram history → connect your TON wallet → in minutes, an AI twin emerges that speaks in your voice, uses your humor, and references your actual memories. Not a generic assistant. A reflection of *you*, built from the conversations that shaped you.

Your twin is tied to your TON wallet address and anchored on-chain via a **Soulbound NFT** — proof that this AI is authentically yours.

---

## 🚀 Live Demo

| | |
|---|---|
| 🌐 **Web App** | [eiva.space](https://eiva.space) |
| 🤖 **Telegram Bot** | [@eivatonbot](https://t.me/eivatonbot) |
| ⚡ **API** | [api.eiva.space/health](https://api.eiva.space/health) |
| 🎭 **Try Demo** | [eiva.space/app.html](https://eiva.space/app.html) → "View Durov Demo" |

Try the Pavel Durov demo twin — **no wallet needed**. Open the cabinet and click **"View Durov Demo Cabinet"**.

---

## How It Works

```
Telegram Export (JSON)
        ↓
   Parser extracts your messages
        ↓
   LLM (GPT-4o) extracts personality profile
        ↓
   Messages embedded → ChromaDB vector store (RAG)
        ↓
   AI twin responds in your authentic voice
        ↓
   TON Soulbound NFT minted as Soul Certificate
```

1. **Export** — Download your Telegram history as JSON (Settings → Advanced → Export)
2. **Connect** — Authenticate with your TON wallet via TonConnect 2.0
3. **Upload** — JSON processed, free up to 3 MB
4. **Twin Ready** — AI responds in your style within ~60 seconds
5. **Mint** — Optional Soul Certificate on TON blockchain

---

## TON Integration

EIVA is built natively on TON:

| Component | Implementation |
|---|---|
| **Identity layer** | TonConnect 2.0 — wallet address = your identity |
| **Ownership proof** | Soulbound NFT (TEP-85, non-transferable) |
| **Tiered access** | Free 3 MB · paid upgrades in TON tokens |
| **Network** | Testnet live · mainnet-ready architecture |

The Soulbound NFT stores a SHA-256 hash of your personality profile on-chain. Your AI twin is **verifiably yours** — not a platform's property.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.10+) · TimeWeb Cloud VPS |
| **AI/LLM** | OpenRouter → GPT-4o (personality) + GPT-4o-mini (chat) |
| **Vector DB** | ChromaDB — per-user collections |
| **Frontend** | Vanilla JS · Particles.js · TonConnect 2.0 UI |
| **Bot** | python-telegram-bot · [@eivatonbot](https://t.me/eivatonbot) |
| **Blockchain** | tonsdk · tonutils · pytoniq-core |
| **Deploy** | Vercel (frontend) · GitHub Actions CI/CD |
| **Domain** | eiva.space · api.eiva.space (SSL via FASTPANEL) |

---

## Project Structure

```
eiva-bot/
├── api.py              ← FastAPI backend (main entry point)
├── bot.py              ← Telegram bot
├── parser.py           ← Telegram JSON export parser
├── embeddings.py       ← ChromaDB vector store + RAG
├── personality.py      ← GPT-4o personality extraction
├── agent.py            ← Digital twin chat engine
├── ton_identity.py     ← TON wallet + NFT integration
├── nft_contract.py     ← Soulbound NFT (TEP-85)
├── config.py           ← Configuration + env vars
├── demo_data/
│   ├── durov_demo.json         ← 60 seed messages for Durov demo
│   └── create_durov_demo.py    ← Script to pre-load demo twin
├── eiva-web/           ← Web app source (synced to docs/)
│   ├── index.html      ← Landing page
│   ├── app.html        ← Personal cabinet
│   ├── js/app.js       ← TonConnect + upload + NFT
│   ├── js/cabinet.js   ← Cabinet + chat + demo mode
│   └── js/i18n.js      ← EN/RU translations
└── docs/               ← GitHub Pages (mirror of eiva-web/)
```

---

## API Reference

**Base URL:** `https://api.eiva.space`

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service status |
| `/api/upload` | POST | Upload Telegram JSON, build twin |
| `/api/chat` | POST | Chat with digital twin |
| `/api/profile` | GET | Get twin profile for wallet |
| `/api/demo/profile` | GET | Durov demo profile (no auth) |
| `/api/stats` | GET | Platform stats |

**Example:**
```bash
# Check API
curl https://api.eiva.space/health

# Chat with Durov demo
curl -X POST https://api.eiva.space/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you think about AI?", "wallet_address": "demo", "demo_mode": true}'
```

---

## Quick Start (Local Dev)

```bash
git clone https://github.com/zhenek73/eiva
cd eiva/eiva-bot
cp .env.example .env       # Fill in TELEGRAM_BOT_TOKEN + OPENROUTER_API_KEY
pip install -r requirements.txt
uvicorn api:app --reload   # API → http://localhost:8000
python bot.py              # Telegram bot (separate terminal)
```

**Load Durov demo twin:**
```bash
python demo_data/create_durov_demo.py
```

### Required Environment Variables

```env
TELEGRAM_BOT_TOKEN=   # @BotFather (use @eivadevbot for local dev)
OPENROUTER_API_KEY=   # https://openrouter.ai (free tier available)
TON_MNEMONIC=         # 24-word wallet mnemonic (for NFT minting)
TON_NETWORK=testnet
```

---

## Privacy & Security

- **Raw messages** are never stored persistently — processed in memory, then discarded
- **Only embeddings** (numeric vectors) are saved in ChromaDB
- **External API** receives only a small anonymized sample for personality extraction
- **On-chain** stores only a SHA-256 hash — zero personal content on blockchain

Your twin will **never share**: passwords · emails · phone numbers · home address · bank/card data · passport/ID · API keys · medical info

Enforced at system prompt level — cannot be disabled.

---

## Roadmap

- [x] Telegram export → digital twin pipeline
- [x] TonConnect 2.0 wallet authentication  
- [x] Soulbound NFT minting (testnet)
- [x] Web cabinet with live chat interface
- [x] Demo twin (Pavel Durov) — try without wallet
- [x] CI/CD auto-deploy (GitHub Actions → Vercel + VPS)
- [ ] Voice message support (Whisper transcription)
- [ ] Multi-source merge (Telegram + Twitter/X + journal)
- [ ] TON mainnet deployment
- [ ] Paid tier upgrades via TON token payments
- [ ] Third-party API access to your twin

---

## Built for TON AI Hackathon 2026

🌐 [eiva.space](https://eiva.space) · 🤖 [@eivatonbot](https://t.me/eivatonbot) · 💻 [GitHub](https://github.com/zhenek73/eiva)

*MIT License*

# 🎭 Eiva — AI Digital Twin on TON

> *Your personality, preserved on the blockchain.*

![TON Testnet](https://img.shields.io/badge/TON-Testnet-blue?logo=ton)
![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Hackathon 2026](https://img.shields.io/badge/TON%20AI-Hackathon%202026-FF4500)

🤖 Bot: [@eivatonbot](https://t.me/eivatonbot)
🌐 Dashboard: [zhenek73.github.io/eiva](https://zhenek73.github.io/eiva/)

---

## What it does

Upload your Telegram chat export → Eiva builds a vector memory of your communication style → a digital twin responds like you → mint a Soul Certificate on the TON blockchain as proof.

1. **Upload** Telegram chat export (JSON from Telegram Desktop)
2. **AI extracts** your personality: tone, vocabulary, topics, humor
3. **Digital twin** answers anyone exactly like you would
4. **Soul Certificate** minted on TON — permanent, verifiable, on-chain

---

## Quick Start (Windows)

```bash
git clone https://github.com/zhenek73/eiva
cd eiva/eiva-bot
cp .env.example .env
# Fill in your API keys in .env
run.bat
```

Open Telegram → [@eivatonbot](https://t.me/eivatonbot) → `/setup`

### Running Web Dashboard Locally

```bash
run_web.bat      # Windows
./run_web.sh     # Linux/Mac
```

Open **http://localhost:8080**

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome + intro |
| `/setup` | Upload Telegram JSON → build your twin |
| `/add_source` | Add another chat export to deepen personality |
| `/settings` | Configure twin behaviour (tone, emoji, language) |
| `/profile` | View extracted personality |
| `/status` | Check twin status |
| `/ask <message>` | Chat with your twin directly |
| `/mint` | Anchor Soul Certificate on TON |
| `/avatar` | Generate AI avatar |
| `/wallet` | Link TON wallet |
| `/twins` | View your digital twins |
| `/demo` | See sample twin (no setup needed) |
| `/help` | All commands |

---

## Configuration (`.env`)

```env
TELEGRAM_BOT_TOKEN=       # From @BotFather
OPENROUTER_API_KEY=       # From openrouter.ai
TON_MNEMONIC=             # 24-word TON wallet mnemonic
TON_NETWORK=testnet
TON_API_KEY=              # Optional: toncenter.com
GITHUB_TOKEN=             # Optional: for NFT metadata hosting
```

---

## Project Structure

```
eiva-bot/
├── bot.py              — Telegram bot
├── parser.py           — Telegram JSON parser
├── embeddings.py       — ChromaDB vector store (RAG)
├── personality.py      — GPT-4o personality extraction
├── agent.py            — Digital twin chat engine
├── ton_identity.py     — TON wallet + Soul Certificate
├── nft_contract.py     — Soulbound NFT (TEP-85)
├── eiva-web/           — Web dashboard source
├── docs/               — GitHub Pages (synced from eiva-web/)
├── data/               — ChromaDB storage (local only)
└── metadata/           — Personality profiles (local only)
```

**Stack:** Python 3.10+, python-telegram-bot, ChromaDB, OpenRouter, tonsdk, tonutils

---

## Privacy

Raw messages stay on your machine. Only embeddings (local ChromaDB) and a short sample for personality extraction (via OpenRouter API) leave the device. On-chain: SHA-256 hash only — no messages, no personal data.

---

## License

MIT

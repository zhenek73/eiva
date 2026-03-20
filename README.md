# Eiva — AI Digital Twin on TON

> Build your AI double from your Telegram messages. Anchor it on the TON blockchain as a soulbound Soul Certificate.

## What it does

1. **Upload** your Telegram chat export (JSON)
2. **Eiva parses** your messages and builds a vector memory (ChromaDB)
3. **LLM extracts** your personality: tone, vocabulary, topics, humor
4. **Digital twin** responds to anyone exactly like you would
5. **TON NFT** mints your Soul Certificate — permanent, on-chain proof of identity

## Hackathon tracks
- ✅ **User-Facing AI Agents** — Telegram-native product
- ✅ **TON integration** — NFT mint + TON Storage

---

## Quick Start

### 1. Install dependencies
```bash
cd eiva-bot
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add:
#   OPENROUTER_API_KEY  ← from openrouter.ai
#   TON_MNEMONIC        ← 24-word testnet wallet mnemonic
```

### 3. Run
```bash
python bot.py
```

### 4. Use the bot
1. Open Telegram → find `@eivatonbot`
2. Send `/start`
3. Send `/setup` → upload your `result.json`
4. Chat! The bot responds as you
5. Send `/mint` → create your TON Soul Certificate

---

## How to export your Telegram chats

1. Open **Telegram Desktop**
2. Go to **Settings → Advanced → Export Telegram Data**
3. Select: ✅ Personal chats, ✅ Direct messages
4. Format: **JSON**
5. Export and upload `result.json` to the bot

---

## Project structure

```
eiva-bot/
├── bot.py           # Telegram bot (entry point)
├── config.py        # Config from .env
├── parser.py        # Telegram JSON export parser
├── embeddings.py    # ChromaDB vector store
├── personality.py   # LLM personality extraction
├── agent.py         # RAG-powered digital twin agent
├── ton_identity.py  # TON NFT mint + Storage
└── requirements.txt
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Bot   | python-telegram-bot 21 |
| LLM   | OpenRouter (GPT-4o / GPT-4o-mini) |
| Memory| ChromaDB + text-embedding-3-small |
| Blockchain | pytoniq → TON testnet/mainnet |
| Storage | TON Storage |

---

## TON integration details

- **Soul Certificate NFT** — TEP-62 compliant NFT minted per user
- **TON Storage** — personality JSON stored permanently as a bag
- **Personality hash** — SHA-256 fingerprint stored on-chain
- Runs on **testnet** by default; switch `TON_NETWORK=mainnet` when ready

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `OPENROUTER_API_KEY` | ✅ | From openrouter.ai |
| `TON_MNEMONIC` | For mint | 24-word wallet mnemonic |
| `TON_NETWORK` | No | `testnet` (default) or `mainnet` |
| `TON_API_KEY` | No | TonCenter API key (rate limits) |
| `LLM_MODEL` | No | Default: `openai/gpt-4o-mini` |
| `LLM_SMART_MODEL` | No | Default: `openai/gpt-4o` |

---

Made for [TON AI Hackathon 2026](https://ton.org) · $20,000 prize pool

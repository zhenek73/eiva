# Eiva — AI Digital Twin on TON

> *Your personality, immortalized on the blockchain. Your voice, available to everyone you choose.*

**TON AI Hackathon 2026** | Tracks: User-Facing AI Agents + TON Integration

🤖 Bot: [@eivatonbot](https://t.me/eivatonbot)
🌐 Dashboard: [zhenek73.github.io/eiva](https://zhenek73.github.io/eiva/)
📖 Whitepaper: [project-docs/WHITEPAPER.md](project-docs/WHITEPAPER.md)
💰 Monetization: [project-docs/MONETIZATION.md](project-docs/MONETIZATION.md)
📋 Changelog: [CHANGELOG.md](CHANGELOG.md)

---

## What it does

1. **Upload** your Telegram chat export (JSON from Telegram Desktop)
2. **Eiva parses** your messages and builds a vector memory (ChromaDB)
3. **GPT-4o extracts** your personality: tone, vocabulary, topics, humor style
4. **Digital twin** responds to anyone exactly like you would — RAG + LLM
5. **Soul Certificate** mints on TON blockchain — permanent, verifiable proof of your identity

---

## Quick Start (Windows)

```bash
git clone https://github.com/zhenek73/eiva
cd eiva/eiva-bot
cp .env.example .env
# Edit .env with your API keys (see .env.example)
run.bat
```

Then open Telegram → [@eivatonbot](https://t.me/eivatonbot) → `/setup`

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/setup` | Upload Telegram JSON export → build your twin |
| `/profile` | View your extracted personality profile |
| `/status` | Check twin status (messages indexed, etc.) |
| `/mint` | Anchor Soul Certificate on TON blockchain |
| `/avatar` | Generate AI avatar for your Soul Certificate |
| `/reset` | Clear all data and start over |

---

## Configuration (`.env`)

```env
TELEGRAM_BOT_TOKEN=       # From @BotFather
OPENROUTER_API_KEY=       # From openrouter.ai (free tier works)
TON_MNEMONIC=             # 24-word TON wallet mnemonic
TON_NETWORK=testnet       # testnet or mainnet
TON_API_KEY=              # Optional: toncenter.com API key for higher rate limits
```

---

## Architecture

```
Telegram Bot
  ├── parser.py       — Telegram JSON export → message list
  ├── embeddings.py   — ChromaDB + text-embedding-3-small (RAG)
  ├── personality.py  — GPT-4o personality extraction
  ├── agent.py        — Digital twin chat (RAG + GPT-4o-mini)
  └── ton_identity.py — TON wallet, Soul Certificate, storage
```

**Stack:** Python 3.10+, python-telegram-bot, ChromaDB, OpenRouter, tonsdk, aiohttp

---

## Soul Certificate

The Soul Certificate is an on-chain transaction anchoring your personality hash to the TON blockchain. It:
- Proves your digital twin existed at a specific timestamp
- Contains `Eiva:Soul:{personality_hash}` in the transaction comment
- Is visible on [testnet.tonscan.org](https://testnet.tonscan.org) (testnet) or [tonscan.org](https://tonscan.org) (mainnet)
- Serves as the **access token** for the planned NFT marketplace (see Monetization)

---

## Business Model

Three tiers (detailed in [project-docs/MONETIZATION.md](project-docs/MONETIZATION.md)):

**🥉 Bronze** — Communication style only → fans / light access ($5–20)
**🥈 Silver** — Full personality + memory → coaches, clients ($30–100)
**🥇 Gold** — Deep twin + expanded memory → family, enterprise ($200–500)

Creators mint Soul Certificates, fans buy access. Smart contract splits revenue 80/15/5 (creator / protocol / ecosystem).

---

## Why TON?

- Telegram distribution = zero acquisition cost
- TON Wallet built into Telegram = frictionless fan purchases
- Low gas fees = micropayment model viable
- Active NFT marketplace on Getgems

---

## Roadmap

- [x] MVP: bot + RAG twin + personality extraction + Soul Certificate
- [ ] AI-generated avatar (v1.1)
- [ ] Real NFT collection contract with TEP-64 metadata (v1.1)
- [ ] Access-control by NFT ownership (v1.2)
- [ ] Multi-tier certificates with supply limits (v1.2)
- [ ] Web admin panel + analytics (v1.3)
- [ ] TON Mini App marketplace (v1.3)

---

## Privacy

Raw messages never leave your machine. Only embeddings (local) and a 100-message sample (for personality extraction via OpenRouter) are processed externally. On-chain: SHA-256 hash only.

---

## License

MIT

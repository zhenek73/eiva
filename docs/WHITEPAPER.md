# Eiva — AI Digital Twin Protocol on TON

> *Your personality, immortalized on the blockchain. Your voice, available to everyone you choose.*

---

## What is Eiva?

Eiva is an AI Digital Twin protocol built on the TON blockchain. It lets any person transform their Telegram message history into a living, conversational replica of themselves — and anchor that identity permanently on-chain as a **Soul Certificate**.

The result: a Telegram bot that talks, jokes, and responds exactly like you — and can represent you, even when you are not there.

---

## The Problem

Every person leaves behind a unique linguistic fingerprint in their digital messages: word choices, humor, rhythm, emotional patterns, recurring topics. Today that fingerprint disappears. When someone dies, changes, or simply goes offline, everything that made their communication style distinctive is lost.

At the same time, creators, coaches, psychologists, and celebrities face a scaling problem: they can only talk to one person at a time. Their knowledge and personality cannot be in multiple places simultaneously.

Eiva solves both problems.

---

## How It Works

### Step 1 — Upload your Telegram history
Export your Telegram chat history (JSON format from Telegram Desktop). Eiva automatically detects which messages are yours and filters them.

### Step 2 — Build the vector memory
Each of your messages is embedded using OpenAI `text-embedding-3-small` and stored in a local ChromaDB vector database. This becomes the *semantic memory* of your twin — it knows what you've talked about, how you phrase things, what matters to you.

### Step 3 — Extract personality
GPT-4o analyzes a representative sample of your messages and extracts a structured personality profile:
- Communication style (formal/informal, verbose/concise)
- Emotional tone (warm, sarcastic, analytical...)
- Vocabulary patterns and favorite expressions
- Topics you care about
- How you handle humor, conflict, uncertainty

### Step 4 — The Digital Twin comes alive
From this point, your twin answers questions using a two-layer system:
1. **RAG retrieval** — finds the most semantically similar messages from your history to ground the response in real context
2. **LLM generation** — GPT-4o-mini, guided by your personality profile, generates a response in your voice

### Step 5 — Soul Certificate on TON
Your personality hash and profile are uploaded to TON Storage, and a **Soul Certificate** transaction is broadcast to the TON blockchain. This creates a permanent, tamper-proof, timestamped record that links your identity to your digital twin. The certificate is visible on tonscan.org.

---

## Technical Architecture

```
Telegram Bot (python-telegram-bot 21.6)
    │
    ├── Parser (parser.py)
    │     Telegram JSON → filtered message list
    │
    ├── Embeddings (embeddings.py)
    │     ChromaDB + text-embedding-3-small
    │     Cosine similarity retrieval
    │
    ├── Personality Extractor (personality.py)
    │     GPT-4o via OpenRouter
    │     Structured profile dict
    │
    ├── Agent (agent.py)
    │     Sliding window conversation history
    │     RAG retrieval → system prompt → GPT-4o-mini
    │
    └── TON Identity (ton_identity.py)
          tonsdk V4R2 wallet
          TON Storage (bag_id)
          Soul Certificate → testnet/mainnet
```

**LLM backend:** OpenRouter (supports any model, currently GPT-4o + GPT-4o-mini)
**Blockchain:** TON (testnet + mainnet ready)
**Vector DB:** ChromaDB (local, zero infra)
**Language:** Python 3.10+

---

## What Makes It Different

| Feature | Eiva | Typical chatbot |
|---|---|---|
| Trained on YOUR messages | ✅ | ❌ |
| Real personality extraction | ✅ | ❌ |
| On-chain identity proof | ✅ | ❌ |
| Runs inside Telegram | ✅ | Sometimes |
| No cloud data storage | ✅ | ❌ |
| Transferable/sellable identity | ✅ (roadmap) | ❌ |

---

## Use Cases

### Personal Continuity
A person wants their family to be able to talk to their "digital self" — their way of thinking, their advice, their humor — indefinitely. One setup, permanent access.

### Celebrity & Creator Access
An influencer, author, or musician creates their digital twin. Fans pay to have a private conversation with the "celebrity" at any time. The creator earns passively; the fan gets an intimate, personalized experience.

### Coaches & Psychologists
A life coach creates a twin trained on all their sessions, frameworks, and communication style. Clients get 24/7 access to coaching between real sessions. The professional scales without burning out.

### Enterprise Knowledge Preservation
A senior engineer or executive leaves the company. Their twin stays — answering questions about decisions made, reasoning used, institutional knowledge held.

### Language & Culture Preservation
Document the communication style and knowledge of elders, cultural figures, or community leaders. Keep their voice alive for future generations.

---

## Roadmap

### v1.0 (MVP — March 2026)
- [x] Telegram bot with full setup flow
- [x] RAG-based digital twin chat
- [x] Personality extraction
- [x] Soul Certificate on TON testnet
- [x] TON Storage integration (demo mode)

### v1.1 — Avatar & Visual Identity
- [ ] AI-generated avatar (DALL-E / Stable Diffusion) from personality profile
- [ ] NFT metadata standard (TEP-64) with avatar + personality hash
- [ ] Real TON NFT collection contract deploy

### v1.2 — Multi-user & Access Control
- [ ] Multiple Soul Certificates from one personality (family/fan copies)
- [ ] Access tiers: Bronze / Silver / Gold (see MONETIZATION.md)
- [ ] Soul Certificate as access token — only holders can chat with the twin

### v1.3 — Creator Dashboard
- [ ] Web admin panel for certificate holders
- [ ] Analytics: who talks to your twin, what they ask
- [ ] Memory expansion: upload more data sources (emails, docs, voice)

### v2.0 — Protocol
- [ ] Open Soul Certificate standard for other developers
- [ ] TON smart contract for trustless royalty distribution
- [ ] Cross-chain bridge (ETH/Solana)

---

## Privacy Model

All message processing happens **locally on your machine**. Your raw messages are never sent to any external server. What leaves your device:
- Message embeddings (anonymous vectors, not raw text) → ChromaDB (local)
- A sample of up to 100 messages → OpenRouter (LLM API call for personality extraction)
- Personality hash (SHA-256, not the profile itself) → TON blockchain

You control what you share. The Soul Certificate on-chain contains only the hash — not your actual messages or profile.

---

## The Team

Built for the TON AI Hackathon 2026 by [Evgeny].
Telegram: @eivatonbot

---

*"Your voice is worth preserving. Eiva makes sure it lasts."*

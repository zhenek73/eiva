# Eiva — Demo Guide for Hackathon Judges

> **Quick start**: 5–10 minutes to see the AI Digital Twin in action

---

## What to Expect

Eiva transforms your Telegram messages into a living, blockchain-anchored AI that responds exactly like you would. The demo shows:

1. Personality extraction from chat history
2. RAG-powered digital twin responses
3. Soul Certificate minting on TON blockchain
4. Multi-tier access control (Bronze / Silver / Gold)

---

## Quick Test (5 min)

### Step 1: Bot Setup in Telegram
1. Open **[@eivatonbot](https://t.me/eivatonbot)** in Telegram
2. Send `/start` → view welcome message
3. Send `/demo` → see a sample personality profile (no upload needed)
4. Send `/status` → check system status
5. Send `/help` → list all commands

### Step 2: View Your Dashboard
- Navigate to **[zhenek73.github.io/eiva](https://zhenek73.github.io/eiva/)**
- Click "How it works" to see the 4-step flow
- Connect your TON wallet (testnet)
- See Soul Certificate tiers and pricing

### Step 3: Optional — Upload & Mint (10 min)
If you want to see the full pipeline:
1. In Telegram: `/setup` → upload a sample Telegram export JSON
2. Wait for personality extraction (~2 min)
3. `/mint` → anchor Soul Certificate on TON testnet
4. View on [testnet.tonscan.org](https://testnet.tonscan.org) — search your wallet address

---

## Commands Reference

| Command | What it does |
|---------|---|
| `/start` | Welcome & info |
| `/setup` | Upload Telegram JSON export → build your twin |
| `/profile` | View extracted personality (tone, vocabulary, topics) |
| `/status` | Check twin status (indexed messages, ready to chat) |
| `/ask <message>` | Chat with your digital twin |
| `/mint` | Anchor Soul Certificate on TON blockchain |
| `/avatar` | Generate AI avatar for your Soul Certificate |
| `/reset` | Clear all data and start fresh |
| `/demo` | See a sample personality profile |
| `/help` | List all commands |
| `/twins` | Show your deployed twins |
| `/stats` | System statistics |

---

## What Happens at Each Step

### Upload Phase
- You export chat from Telegram Desktop (Settings → Advanced → Export Telegram Data)
- Upload JSON to bot
- Messages are parsed locally (stays on your device)
- ~100-message sample is sent to GPT-4o for personality extraction

### Personality Extraction
- **Tone & Vocabulary**: How you write (formal vs. casual, favorite phrases)
- **Topics & Interests**: What you talk about (inferred from embeddings)
- **Humor Style**: Funny patterns from your messages
- **Emotional Range**: Happy, sarcastic, thoughtful, etc.
- Results stored in ChromaDB vector database (local)

### Twin Goes Live
- Your personality profile is now active in the bot
- When someone messages your twin, it:
  1. Searches your memory (RAG)
  2. Generates response using GPT-4o-mini
  3. Mimics your tone and style
- Example: If you use lots of emojis, the twin will too

### Minting Soul Certificate
- Personality hash (SHA-256) is anchored on TON
- Transaction contains: `Eiva:Soul:{hash}` in comment
- Visible forever on blockchain
- Serves as ownership proof + access token for tier sales

---

## Tiers Explained

| Tier | Access Level | Price | Who's it for? |
|------|---|---|---|
| **Bronze** | Style only (tone, humor, vocabulary) | $5–20 | Casual fans, light interaction |
| **Silver** | Full personality + memories (RAG) | $30–100 | Coaches, close friends, clients |
| **Gold** | Deep twin + expanded context | $200–500 | Family, enterprise, heavy use |
| **Exclusive 1/1** | Unique NFT (auctions, celebrities) | Bids | Collectible, high-value personalities |

Buyers purchase NFT on Getgems/TON marketplace. Revenue split: 80% creator / 15% protocol / 5% ecosystem.

---

## Known Limitations (Testnet Only)

- **Testnet Only**: Running on TON testnet, not mainnet. Real transactions won't persist after testnet reset.
- **Rate Limits**: Free tier APIs (OpenRouter, TonCenter) have limits. May need patience between requests.
- **Avatar Generation**: Coming in v1.1. Currently placeholder.
- **Data Privacy**: Raw messages never leave your device; only embeddings + 100-sample are processed externally.
- **Personality Extraction**: Works best with 50+ messages. Fewer messages = generic profile.

---

## Links

| Link | Purpose |
|------|---|
| **[Bot](https://t.me/eivatonbot)** | @eivatonbot — start here |
| **[Dashboard](https://zhenek73.github.io/eiva/)** | Web UI (wallet, tiers, NFT gallery) |
| **[GitHub](https://github.com/zhenek73/eiva)** | Full source code |
| **[Testnet Explorer](https://testnet.tonscan.org)** | Browse transactions & Soul Certificates |
| **[TON Docs](https://ton.org/docs)** | Technical reference |

---

## Troubleshooting

**Bot not responding?**
- Send `/help` to verify connectivity
- Check your internet connection
- Try `/reset` if stuck

**Upload fails?**
- Ensure JSON is valid Telegram export (use `result.json` from Desktop app)
- Check file size (should be < 50MB)
- Try again; API rate limits may apply

**Wallet won't connect?**
- Use TON Wallet or Tonkeeper (testnet mode)
- Switch to testnet network
- Refresh dashboard page

**Can't mint?**
- Need ~0.5 TON testnet balance (claim from faucet: https://testnet.tonfaucet.com)
- Wallet must be connected first
- Check network status indicator on dashboard

---

## Questions?

- **Technical Issues**: File an issue on [GitHub](https://github.com/zhenek73/eiva/issues)
- **Feature Requests**: Reach out on Telegram or GitHub
- **General Info**: Check the [Whitepaper](https://github.com/zhenek73/eiva/blob/main/project-docs/WHITEPAPER.md)

---

**Made for TON AI Hackathon 2026** | [Github](https://github.com/zhenek73/eiva) | [@eivatonbot](https://t.me/eivatonbot)

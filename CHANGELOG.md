# Changelog

All notable changes to Eiva are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.5.0] — 2026-03-21 (current)

### Added — Web Dashboard
- `eiva-web/index.html` — full single-page dashboard (works as website + Telegram Mini App)
  * TON Connect wallet authentication via `@tonconnect/ui`
  * NFT gallery: loads user's Soulbound NFTs from tonapi.io, shows image + metadata
  * NFT detail modal: name, image, address, metadata JSON link, Getgems + Tonscan links
  * Drag-and-drop Telegram JSON upload (validates file, shows message count)
  * Tier comparison section (Bronze / Silver / Gold / Exclusive)
  * Hero section, "How it works" steps, footer
  * Fully responsive (mobile + desktop), dark TON-aesthetic design
  * Works as GitHub Pages site AND as Telegram Mini App (iframe / webview)
- `eiva-web/tonconnect-manifest.json` — TON Connect manifest for wallet auth

### Added — Real Soulbound NFT
- `nft_contract.py` — complete Soulbound NFT deployment pipeline (TEP-85 standard)
  * `build_metadata()` — creates TEP-64 JSON with name, description, image (DiceBear or DALL-E), attributes
  * `upload_metadata_to_github()` — publishes metadata JSON to GitHub repo via API → permanent raw URL
  * `build_nft_state_init()` — constructs NFT item StateInit from tonutils bytecode + pytoniq_core cells
  * `deploy_soulbound_nft()` — derives NFT address, deploys via tonsdk `create_transfer_message` with state_init
  * NFT visible on testnet.getgems.io + testnet.tonscan.org after deploy
- `/mint` now deploys a real on-chain Soulbound NFT (not just an anchor transaction)
- Response includes Getgems link + Tonscan link + metadata JSON link

### Added — Bot UX improvements
- `/wallet` command — link/show TON wallet address; saved to user's ChromaDB metadata
  * Inline button: "Connect on Dashboard" → opens web UI
  * Inline button: "Mint Soul Certificate"
- `/start` shows inline keyboard: "Open Dashboard" + "Mint NFT" or "Start Setup"
- Message handler intercepts TON wallet addresses (regex) → saves to profile automatically
- Avatar URL saved to metadata for reuse in NFT deploy
- `config.py`: added `GITHUB_TOKEN` variable

---

## [0.3.0] — 2026-03-21

### Fixed
- **Critical TON bug**: `runGetMethod` returns `exit_code: -13` (wallet not deployed) with a fake seqno in the stack (`0x14c97`). We were parsing that as the real seqno (85143), so `create_transfer_message` built a BOC without `state_init` → wallet rejected every external message with `exitcode=0, steps=0`.
- Fix: check `exit_code` before parsing stack; if `exit_code != 0` → set `seqno=0` so tonsdk includes `state_init` → wallet deploys and transaction executes in one shot.
- Replace derived NFT address (no contract on testnet) with **self-transfer** — sends 0.01 TON from bot wallet to itself with Soul Certificate hash in the comment. Reliable, verifiable on-chain.

### Added
- Retry logic with exponential backoff on toncenter HTTP 429 (rate limit).
- `tonapi.io` as fallback broadcast endpoint when toncenter fails.
- Verbose debug logging for seqno API response and each broadcast attempt.
- Explorer URL now links to wallet address page on `testnet.tonscan.org`.

---

## [0.2.0] — 2026-03-20

### Added
- Full TON blockchain integration via `tonsdk` (V4R2 wallet derivation).
- TON Storage upload with deterministic `bag_id` fallback (no daemon required).
- `/mint` ConversationHandler — asks for owner TON address, then triggers full certificate flow.
- Balance check before mint attempt; warns if balance < 0.01 TON.
- BitString overflow fix: shortened payload to `Eiva:{hash[:16]}` (21 bytes, fits in one TON cell).
- `tonsdk` explicit install step in `run.bat`.

### Fixed
- `asyncio.get_event_loop()` RuntimeError on Python 3.14 — added `asyncio.set_event_loop(asyncio.new_event_loop())`.
- GitHub push blocked by secret in history — switched to `git checkout --orphan` to create clean history.
- `.env.example` contained real Telegram bot token — replaced with placeholders.

---

## [0.1.0] — 2026-03-19

### Added
- Telegram bot skeleton with `python-telegram-bot 21.6`.
- `/setup` ConversationHandler: upload Telegram JSON export → auto-detect owner name → parse → embed → extract personality.
- `parser.py`: Telegram Desktop JSON export parser, auto-detects most frequent sender.
- `embeddings.py`: `EmbeddingStore` wrapping ChromaDB with `text-embedding-3-small`.
- `personality.py`: GPT-4o personality extraction with 90 s timeout + fallback profile on error. Capped at 100 messages for speed.
- `agent.py`: `EivaAgent` with sliding-window conversation history and RAG retrieval.
- `config.py`: dotenv-based config; OpenRouter as LLM backend (GPT-4o-mini for chat, GPT-4o for extraction).
- `/profile`, `/status`, `/reset` commands.
- `run.bat` for Windows one-click launch.
- `.gitignore` excluding `.env`, `data/`, `__pycache__`.

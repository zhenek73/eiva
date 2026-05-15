# Changelog

All notable changes to Eiva are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.7.0] — 2026-03-21 (current)

### Added — Multi-Source Personality + Tier System + Settings

#### Multi-Source Personality (Task 1)
- `/add_source` command — upload additional Telegram exports to augment existing personality (tier-limited)
- Tier system with limits:
  * **Bronze 🥉**: 1 source (default)
  * **Silver 🥈**: 3 sources
  * **Gold 🥇**: 5 sources
  * **Exclusive 💎**: 99 sources
- `merge_personality()` function in personality.py — intelligently merges new exports with existing profile
  * Combines signature phrases, topics, and traits (union of sets)
  * Blends communication style and response patterns
  * Preserves emotional tone and language
  * Adds new messages to ChromaDB without clearing existing ones
- Metadata methods in embeddings.py:
  * `get_source_count()` — read source count
  * `get_tier()` — read tier
  * `increment_source_count()` — increment by 1
- User state machine to distinguish `/setup` vs `/add_source` document uploads

#### Personality Settings Page (Task 2)
- `/settings` command with inline keyboard UI:
  * ✅ Signature phrases toggle
  * ✅ Formal mode toggle
  * ✅ Emoji in replies toggle
  * ✅ Humor toggle
  * ✅ Short responses toggle
  * 🌐 Language selector (auto/English/Russian)
  * 💾 Save button
- Settings stored in ChromaDB metadata as JSON
- `DEFAULT_SETTINGS` in config.py for new users
- Agent uses settings when generating responses — settings context injected into system prompt
- `_build_settings_notes()` helper in agent.py to format settings as system instructions

#### Settings Web UI (Task 2)
- Settings section added to eiva-web/index.html:
  * Toggle switches for each setting (HTML/CSS toggles)
  * Language dropdown
  * Save button
- JavaScript in app.js:
  * `loadSettings()` — load from localStorage with defaults
  * `saveSettings()` — persist to localStorage
  * `initSettings()` — wire up all controls
- Settings synced locally; future update will push to bot

#### Web Run Scripts (Task 3)
- `run_web.bat` — Windows script to run dashboard locally on port 8080
- `run_web.sh` — Linux/Mac script (executable) to run dashboard locally
- Updated README with "Running Web Dashboard Locally" section
- Synced eiva-web to docs/ directory for GitHub Pages

### Updated
- `config.py` — added `TIER_LIMITS` dict and `DEFAULT_SETTINGS` dict
- `embeddings.py` — added tier/source count management methods
- `personality.py` — added `merge_personality()` and `_merge_text_field()` functions
- `agent.py` — updated `reply()` to inject settings context; added `_build_settings_notes()` helper
- `bot.py`:
  * Added state machine: `AWAITING_SOURCE_DOC` state + `user_state` dict
  * New `/add_source` and `/settings` commands
  * Updated `handle_json_upload()` to support both `/setup` and `/add_source` flows
  * Updated `handle_inline_callback()` to handle settings toggles and language selector
  * Enhanced callback pattern to match `setting_*` callbacks
  * Added `/add_source` and `/settings` to conversation handler entry points
- `eiva-web/index.html` — added settings card with 6 toggles, language dropdown, save button
- `eiva-web/js/app.js` — added settings initialization and persistence functions
- `README.md` — added `/add_source` and `/settings` commands to table; added web dashboard local run instructions

### Testing
- All Python files compile without syntax errors ✅
- Settings toggles and language selector functional
- merge_personality() integrates with existing RAG pipeline
- Tier checks prevent exceeding source limits

---

## [0.6.0] — 2026-03-21

### Added — Enhanced Bot UX & New Features
- `/twins` command — view all digital twins the user has access to (own + future purchases from Getgems)
- `/stats` command (admin-only) — shows total users, twins built, and completion rate
- Inline keyboard buttons on /mint success — direct links to Tonscan and Getgems for NFT viewing
- Improved /start message — more compelling onboarding with clear value proposition and 3-step setup guide
- Better error resilience — /mint now gracefully falls back to Soul Certificate anchor if NFT deploy fails
- Enhanced /help command — updated with new commands

### Fixed
- NFT deploy error handling — catches import errors and falls back to original certificate mechanism
- Better user messaging on deployment failures — explains fallback to Soul Certificate anchor

### Tested
- `tonutils.contracts.codes.CONTRACT_CODES[ContractVersion.NFTItemSoulbound]` — confirmed available
- `pytoniq_core.begin_cell().store_snake_string()` — confirmed working
- All library imports validated and working correctly

---

## [0.5.0] — 2026-03-21

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

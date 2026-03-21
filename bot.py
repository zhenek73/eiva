"""
Eiva — bot.py
Main Telegram bot entry point.

User journey:
  1. /start       → welcome screen
  2. /setup       → upload Telegram JSON export → extract personality → ready
  3. Chat freely  → agent responds as digital twin
  4. /mint        → create TON Soul Certificate NFT
  5. /profile     → view extracted personality
  6. /reset       → clear conversation history
  7. /status      → show indexing stats
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

import config
from parser import parse_export, detect_owner_name
from embeddings import EmbeddingStore
from personality import extract_personality, build_system_prompt
from agent import EivaAgent
from ton_identity import create_soul_certificate

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("eiva")

# ── Conversation states ───────────────────────────────────────────────────────
AWAITING_JSON    = 1
AWAITING_NAME    = 2
AWAITING_TON_ADDR = 3

# ── In-memory registry: user_id → EivaAgent ───────────────────────────────────
agents: dict[int, EivaAgent] = {}


# ── Helper: get or create agent for user ─────────────────────────────────────

def get_agent(user_id: int) -> EivaAgent | None:
    return agents.get(user_id)


def _is_setup(user_id: int) -> bool:
    store = EmbeddingStore(str(user_id))
    return store.is_ready() and store.load_meta("system_prompt") is not None


def _load_agent(user_id: int) -> EivaAgent | None:
    """Load an existing agent from persisted data (after bot restart)."""
    if user_id in agents:
        return agents[user_id]
    store = EmbeddingStore(str(user_id))
    system_prompt = store.load_meta("system_prompt")
    if system_prompt and store.is_ready():
        agent = EivaAgent(str(user_id), system_prompt)
        agents[user_id] = agent
        return agent
    return None


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    already_setup = _is_setup(user.id)

    text = (
        f"👋 *Welcome to Eiva — Your AI Digital Twin*\n\n"
        f"I learn from your Telegram messages and become a version of *you* "
        f"that others can talk to — anchored on the TON blockchain.\n\n"
    )

    keyboard = None
    if already_setup:
        agent = _load_agent(user.id)
        if agent:
            agents[user.id] = agent
        text += "✅ Your twin is *already set up*! Just send a message and I'll respond as you.\n\n"
        text += "*/profile* — view personality\n"
        text += "*/wallet* — connect TON wallet\n"
        text += "*/mint* — mint Soul Certificate NFT\n"
        text += "*/avatar* — generate AI portrait\n"
        text += "*/status* — stats  ·  /reset — clear history"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Open Dashboard", url="https://zhenek73.github.io/eiva/eiva-web/"),
            InlineKeyboardButton("💎 Mint NFT", callback_data="start_mint"),
        ]])
    else:
        text += (
            "To get started, use /setup and upload your Telegram chat export.\n\n"
            "📖 *How to export your chats:*\n"
            "Telegram Desktop → Settings → Advanced → Export Telegram Data\n"
            "→ Select chats → Format: *JSON* → Export"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📂 Start Setup", callback_data="start_setup"),
            InlineKeyboardButton("🌐 Dashboard", url="https://zhenek73.github.io/eiva/eiva-web/"),
        ]])

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ── /setup ────────────────────────────────────────────────────────────────────

async def cmd_setup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 *Setup your Digital Twin*\n\n"
        "Send me your Telegram export JSON file (`result.json`).\n\n"
        "To export: *Telegram Desktop → Settings → Advanced → Export Telegram Data*\n"
        "Choose: ✅ Personal chats, Format: *JSON*\n\n"
        "Then upload the `result.json` file here 👇",
        parse_mode=ParseMode.MARKDOWN,
    )
    return AWAITING_JSON


async def handle_json_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Receive the JSON file, detect owner, ask for name confirmation."""
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Please send a .json file.")
        return AWAITING_JSON

    await update.message.reply_text("⏳ Downloading and analyzing your export...")
    await update.message.chat.send_action(ChatAction.TYPING)

    # Download to temp file
    tg_file = await ctx.bot.get_file(doc.file_id)
    tmp_path = Path(tempfile.mktemp(suffix=".json"))
    await tg_file.download_to_drive(tmp_path)

    # Store path in context
    ctx.user_data["export_path"] = str(tmp_path)

    # Auto-detect owner name
    detected = detect_owner_name(tmp_path)
    ctx.user_data["detected_name"] = detected

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Yes, that's me: {detected}", callback_data=f"name_confirm:{detected}")],
        [InlineKeyboardButton("✏️ Enter my name manually", callback_data="name_manual")],
    ]) if detected else None

    if detected:
        await update.message.reply_text(
            f"🔍 I detected the most active sender: *{detected}*\n\nIs that you?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return AWAITING_NAME
    else:
        await update.message.reply_text(
            "❓ Couldn't auto-detect your name.\n\nWhat is your name *exactly as it appears* in Telegram exports?",
            parse_mode=ParseMode.MARKDOWN,
        )
        return AWAITING_NAME


async def handle_name_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("name_confirm:"):
        name = query.data.split(":", 1)[1]
        await query.edit_message_text(f"✅ Got it! Processing as *{name}*...", parse_mode=ParseMode.MARKDOWN)
        await _process_export(update, ctx, name)
        return ConversationHandler.END
    elif query.data == "name_manual":
        await query.edit_message_text("✏️ Please type your name exactly as it appears in the export:")
        return AWAITING_NAME


async def handle_name_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    await update.message.reply_text(f"✅ Processing as *{name}*...", parse_mode=ParseMode.MARKDOWN)
    await _process_export(update, ctx, name)
    return ConversationHandler.END


async def _process_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE, owner_name: str):
    """The heavy lifting: parse → embed → extract personality → save."""
    user_id  = update.effective_user.id
    msg      = update.effective_message
    tmp_path = ctx.user_data.get("export_path")

    if not tmp_path:
        await msg.reply_text("❌ Export file not found. Please use /setup again.")
        return

    await msg.reply_text("📖 Parsing your messages...")

    from parser import parse_export
    messages = parse_export(tmp_path, owner_name)

    if len(messages) < config.MIN_MESSAGES_REQUIRED:
        await msg.reply_text(
            f"⚠️ Only found {len(messages)} messages from *{owner_name}*.\n"
            f"Need at least {config.MIN_MESSAGES_REQUIRED}.\n\n"
            f"Make sure the name matches exactly, or export more chats.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await msg.reply_text(f"✅ Found *{len(messages)}* messages. Building your memory bank...", parse_mode=ParseMode.MARKDOWN)

    # Index into ChromaDB
    store = EmbeddingStore(str(user_id))
    await msg.reply_text(f"⏳ Indexing {len(messages)} messages into vector memory (may take 1-2 min)...")
    log.info(f"[setup] Starting embedding for user {user_id}, {len(messages)} messages")
    added = store.add_messages(messages)
    log.info(f"[setup] Embedding done: {added} added")
    await msg.reply_text(f"🧠 Indexed *{added}* messages into memory.", parse_mode=ParseMode.MARKDOWN)

    # Extract personality
    await msg.reply_text("🔬 Analyzing your personality (sending 100 messages to GPT-4o, ~20 sec)...")
    log.info(f"[setup] Starting personality extraction for user {user_id}")
    try:
        profile = extract_personality(messages, str(user_id))
        log.info(f"[setup] Personality extracted: {profile.get('name')}, tone={profile.get('emotional_tone')}")
    except Exception as e:
        log.error(f"[setup] Personality extraction failed: {e}")
        await msg.reply_text(f"⚠️ Personality analysis failed: {e}\nUsing default profile.")
        profile = {"name": owner_name, "language": "Russian", "communication_style": "natural",
                   "vocabulary": "", "topics_of_interest": [], "emotional_tone": "neutral",
                   "response_patterns": "conversational", "humor": "none",
                   "unique_traits": [], "do_not_do": []}

    # Build system prompt
    system_prompt = build_system_prompt(profile, owner_name)

    # Persist
    store.save_meta("system_prompt", system_prompt)
    store.save_meta("personality",   profile)
    store.save_meta("owner_name",    owner_name)

    # Create agent
    agent = EivaAgent(str(user_id), system_prompt)
    agents[user_id] = agent

    # Clean up temp file
    try:
        Path(tmp_path).unlink()
    except Exception:
        pass

    await msg.reply_text(
        f"🎉 *Your Digital Twin is ready!*\n\n"
        f"Name: *{profile.get('name', owner_name)}*\n"
        f"Style: {profile.get('communication_style', '')[:100]}...\n"
        f"Topics: {', '.join(profile.get('topics_of_interest', [])[:4])}\n\n"
        f"Now just send a message — I'll respond as you! 🪄\n\n"
        f"Use /mint to create your TON Soul Certificate 🔗",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /profile ──────────────────────────────────────────────────────────────────

async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))
    profile = store.load_meta("personality")

    if not profile:
        await update.message.reply_text("❌ No profile yet. Use /setup first.")
        return

    traits = "\n".join(f"• {t}" for t in profile.get("unique_traits", [])[:5])
    topics = ", ".join(profile.get("topics_of_interest", [])[:6])

    text = (
        f"🧬 *Your Digital Twin Profile*\n\n"
        f"**Style:** {profile.get('communication_style', 'N/A')}\n\n"
        f"**Tone:** {profile.get('emotional_tone', 'N/A')}\n\n"
        f"**Vocabulary:** {profile.get('vocabulary', 'N/A')[:150]}\n\n"
        f"**Topics:** {topics}\n\n"
        f"**Unique traits:**\n{traits}\n\n"
        f"**Humor:** {profile.get('humor', 'N/A')}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── /status ───────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))
    count   = store.count()
    name    = store.load_meta("owner_name", "Unknown")

    await update.message.reply_text(
        f"📊 *Twin Status*\n\n"
        f"Owner: {name}\n"
        f"Messages in memory: {count}\n"
        f"Ready: {'✅' if store.is_ready() else '❌'}\n"
        f"Agent loaded: {'✅' if user_id in agents else '⚠️ (will load on next message)'}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /demo ──────────────────────────────────────────────────────────────────────

async def cmd_demo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show a demo interaction with a sample digital twin."""
    await update.message.reply_text(
        "🎬 *Welcome to Eiva Demo*\n\n"
        "Let me show you what your digital twin can do...\n\n"
        "This is a sample personality profile for a fictional tech enthusiast:",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Sample personality profile
    demo_profile = {
        "name": "Alex Chen",
        "communication_style": "casual and witty, loves technical deep dives",
        "emotional_tone": "enthusiastic and optimistic",
        "vocabulary": "uses a mix of technical jargon and casual expressions",
        "topics_of_interest": ["AI/ML", "blockchain", "startup culture", "science fiction"],
        "unique_traits": ["explains complex ideas simply", "dry humor", "asks questions to understand deeply"],
        "humor": "dry wit and clever puns"
    }

    profile_text = (
        f"👤 *{demo_profile['name']}*\n\n"
        f"*Communication Style:* {demo_profile['communication_style']}\n"
        f"*Tone:* {demo_profile['emotional_tone']}\n"
        f"*Topics:* {', '.join(demo_profile['topics_of_interest'][:4])}\n"
        f"*Special Traits:* {', '.join(demo_profile['unique_traits'][:3])}\n"
    )

    await update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)

    # Sample interaction
    await update.message.reply_text(
        "💬 *Sample Conversation:*\n\n"
        "*You:* What's your take on the current state of AI?\n\n"
        "*Twin (Alex):* Oh, we're in that fascinating phase where models "
        "are getting smarter but we're still figuring out how to use them wisely. "
        "It's like having a really powerful tool and slowly realizing what you can actually build with it. "
        "The real bottleneck now isn't the models — it's the data, the UX, and honestly, "
        "the human side of understanding when NOT to use AI.\n\n"
        "---\n\n"
        "*Ready to create your own?*\n"
        "Use /setup to upload your Telegram export and build YOUR digital twin! 🚀",
        parse_mode=ParseMode.MARKDOWN,
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📂 Start Setup", callback_data="start_setup"),
    ]])

    await update.message.reply_text(
        "This demo shows how your twin learns from your unique voice and responds in your style.",
        reply_markup=keyboard,
    )


# ── /help ──────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show a help message with all commands and dashboard link."""
    help_text = (
        "🆘 *Eiva Help*\n\n"
        "*Available Commands:*\n\n"
        "*/start* — Welcome screen and quick links\n"
        "*/setup* — Upload your Telegram export to create your digital twin\n"
        "*/profile* — View your personality profile\n"
        "*/status* — Check memory and readiness status\n"
        "*/wallet* — Link or view your TON wallet\n"
        "*/mint* — Create a Soulbound NFT Soul Certificate\n"
        "*/avatar* — Generate an AI portrait for your certificate\n"
        "*/demo* — See a sample interaction with Eiva\n"
        "*/reset* — Clear conversation history (keep long-term memory)\n"
        "*/help* — Show this message\n\n"
        "*Getting Started:*\n"
        "1. Use /setup to upload your Telegram chat export (JSON)\n"
        "2. I'll analyze your messages and create your digital twin\n"
        "3. Chat freely — I'll respond as you!\n"
        "4. Use /mint to immortalize your twin as an on-chain NFT\n\n"
        "🌐 *[Open Dashboard](https://zhenek73.github.io/eiva/eiva-web/)* — "
        "View your NFTs, manage settings, and connect your TON wallet\n\n"
        "Need help? Check out the project docs or ask in the dashboard."
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 Dashboard", url="https://zhenek73.github.io/eiva/eiva-web/"),
    ]])

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ── /reset ────────────────────────────────────────────────────────────────────

async def cmd_wallet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show or update the user's linked TON wallet address."""
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))
    saved   = store.load_meta("ton_wallet_address")

    from ton_identity import get_wallet_address
    bot_wallet = get_wallet_address()
    net = "testnet"  # from config

    if saved:
        tonscan = f"https://testnet.tonscan.org/address/{saved}" if net == "testnet" else f"https://tonscan.org/address/{saved}"
        text = (
            f"💳 *Your linked TON wallet:*\n"
            f"`{saved}`\n\n"
            f"[View on Tonscan]({tonscan})\n\n"
            f"To change, reply with your new TON address.\n"
            f"Or use /mint to create a Soul Certificate for this wallet."
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 View on Tonscan", url=tonscan),
            InlineKeyboardButton("💎 Mint NFT", callback_data="start_mint"),
        ]])
    else:
        text = (
            f"🔗 *Link your TON wallet*\n\n"
            f"Send your TON wallet address to link it with your twin.\n"
            f"This will be used as the owner address when minting your Soul Certificate NFT.\n\n"
            f"_Example:_ `UQDxxx...`\n\n"
            f"Or connect via the 🌐 [Eiva Dashboard](https://zhenek73.github.io/eiva/eiva-web/) with TON Connect."
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Connect on Dashboard", url="https://zhenek73.github.io/eiva/eiva-web/"),
        ]])

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    ctx.user_data["awaiting_wallet"] = True


async def handle_inline_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks."""
    query = update.callback_query
    await query.answer()
    if query.data == "start_setup":
        await query.message.reply_text(
            "📂 *Setup your Digital Twin*\n\n"
            "Send me your Telegram export JSON file (`result.json`).\n\n"
            "To export: *Telegram Desktop → Settings → Advanced → Export Telegram Data*\n"
            "Choose: ✅ Personal chats, Format: *JSON*\n\n"
            "Then upload the `result.json` file here 👇",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data == "start_mint":
        user_id = update.effective_user.id
        store   = EmbeddingStore(str(user_id))
        profile = store.load_meta("personality")
        name    = store.load_meta("owner_name", "Unknown")

        if not profile:
            await query.message.reply_text("❌ No profile yet. Use /setup first.")
            return

        # Show wallet info from config
        from ton_identity import get_wallet_address
        bot_wallet = get_wallet_address()

        wallet_info = ""
        if bot_wallet:
            wallet_info = (
                f"\n\n💳 *Bot signing wallet (V4R2):*\n"
                f"`{bot_wallet}`\n"
                f"⚠️ This wallet needs testnet TON to sign the mint tx.\n"
                f"Send from your W5 wallet in Tonkeeper → this address."
            )

        await query.message.reply_text(
            "💎 *Mint your Soul Certificate*\n\n"
            "Your personality profile will be:\n"
            "1️⃣ Uploaded to TON Storage (permanent)\n"
            "2️⃣ Minted as a soulbound NFT on TON blockchain\n"
            f"{wallet_info}\n\n"
            "Enter *your* TON wallet address to record as NFT owner\n"
            "(or /skip to use the bot wallet as owner):",
            parse_mode=ParseMode.MARKDOWN,
        )
        ctx.user_data["mint_name"]    = name
        ctx.user_data["mint_profile"] = profile


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent   = get_agent(user_id)
    if agent:
        agent.reset_history()
        await update.message.reply_text("🔄 Conversation history cleared. Long-term memory is intact.")
    else:
        await update.message.reply_text("No active twin loaded. Use /setup first.")


# ── /avatar ───────────────────────────────────────────────────────────────────

async def cmd_avatar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Generate an AI avatar for the Soul Certificate using personality profile."""
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))
    profile = store.load_meta("personality")
    name    = store.load_meta("owner_name", "Unknown")

    if not profile:
        await update.message.reply_text("❌ No profile yet. Run /setup first.")
        return

    await update.message.reply_text("🎨 Generating your Soul Certificate avatar...")
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

    try:
        import aiohttp, base64
        # Build a rich prompt from personality profile
        style      = profile.get("communication_style", "thoughtful and expressive")
        tone       = profile.get("emotional_tone", "warm")
        topics     = ", ".join(profile.get("key_topics", ["technology", "life"])[:3])
        prompt = (
            f"A beautiful, artistic portrait avatar for a digital soul certificate NFT. "
            f"The person named {name} has a {tone} and {style} personality. "
            f"They care deeply about: {topics}. "
            f"Style: glowing holographic portrait on a dark background, "
            f"digital art, futuristic, TON blockchain aesthetic, blue and violet tones, "
            f"minimalist, professional. No text."
        )

        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "openai/dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url",
        }

        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://openrouter.ai/api/v1/images/generations",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    image_url = data["data"][0]["url"]
                    # Download and send the image
                    async with s.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as img_r:
                        img_bytes = await img_r.read()

                    # Save locally for reference
                    avatars_dir = Path("avatars")
                    avatars_dir.mkdir(exist_ok=True)
                    avatar_path = avatars_dir / f"{user_id}_avatar.png"
                    avatar_path.write_bytes(img_bytes)

                    # Send to Telegram
                    await update.message.reply_photo(
                        photo=img_bytes,
                        caption=(
                            f"✨ *Soul Certificate Avatar*\n"
                            f"👤 *{name}*\n\n"
                            f"This avatar was generated from your personality profile "
                            f"and will be attached to your Soul Certificate NFT.\n\n"
                            f"_Traits: {tone} · {style}_"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    store.save_meta("avatar_generated", True)
                    store.save_meta("avatar_url", image_url)
                    log.info(f"[Avatar] Generated for user {user_id}")
                else:
                    error_text = await r.text()
                    log.warning(f"[Avatar] API error {r.status}: {error_text[:200]}")
                    await _avatar_fallback(update, name, profile)

    except Exception as e:
        log.error(f"[Avatar] Error: {e}")
        await _avatar_fallback(update, name, profile)


async def _avatar_fallback(update: Update, name: str, profile: dict):
    """Fallback: show DiceBear avatar (deterministic, no API needed)."""
    import hashlib
    seed = hashlib.md5(name.encode()).hexdigest()[:8]
    avatar_url = f"https://api.dicebear.com/9.x/pixel-art/png?seed={seed}&size=256&backgroundColor=1a1a2e"
    await update.message.reply_photo(
        photo=avatar_url,
        caption=(
            f"🎨 *Soul Certificate Avatar*\n"
            f"👤 *{name}*\n\n"
            f"_Pixel art avatar (AI generation unavailable)._\n"
            f"Your Soul Certificate is still valid on-chain."
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /mint ─────────────────────────────────────────────────────────────────────

async def cmd_mint(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))
    profile = store.load_meta("personality")
    name    = store.load_meta("owner_name", "Unknown")

    if not profile:
        await update.message.reply_text("❌ No profile yet. Use /setup first.")
        return

    # Show wallet info from config
    from ton_identity import get_wallet_address
    bot_wallet = get_wallet_address()

    wallet_info = ""
    if bot_wallet:
        wallet_info = (
            f"\n\n💳 *Bot signing wallet (V4R2):*\n"
            f"`{bot_wallet}`\n"
            f"⚠️ This wallet needs testnet TON to sign the mint tx.\n"
            f"Send from your W5 wallet in Tonkeeper → this address."
        )

    await update.message.reply_text(
        "💎 *Mint your Soul Certificate*\n\n"
        "Your personality profile will be:\n"
        "1️⃣ Uploaded to TON Storage (permanent)\n"
        "2️⃣ Minted as a soulbound NFT on TON blockchain\n"
        f"{wallet_info}\n\n"
        "Enter *your* TON wallet address to record as NFT owner\n"
        "(or /skip to use the bot wallet as owner):",
        parse_mode=ParseMode.MARKDOWN,
    )
    ctx.user_data["mint_name"]    = name
    ctx.user_data["mint_profile"] = profile
    return AWAITING_TON_ADDR


async def handle_ton_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text    = update.message.text.strip()
    user_id = update.effective_user.id

    ton_address = None if text.lower() in ("/skip", "skip") else text
    name        = ctx.user_data.get("mint_name", "Unknown")
    profile     = ctx.user_data.get("mint_profile", {})

    await update.message.reply_text(
        "⏳ *Creating your Soulbound NFT on TON...*\n\n"
        "1️⃣ Building metadata JSON\n"
        "2️⃣ Uploading to GitHub (public URL)\n"
        "3️⃣ Deploying NFT contract on-chain\n\n"
        "_This takes ~15 seconds..._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.message.chat.send_action(ChatAction.TYPING)

    # Step A: also anchor personality hash (original cert)
    result = await create_soul_certificate(
        user_id    = str(user_id),
        owner_name = name,
        personality= profile,
        ton_address= ton_address,
    )
    personality_hash = result["personality_hash"]

    # Step B: deploy real Soulbound NFT
    from nft_contract import deploy_soulbound_nft
    from ton_identity import get_wallet_address

    owner_addr = ton_address or get_wallet_address()
    nft_result = None
    if owner_addr and config.TON_MNEMONIC:
        # Retrieve avatar URL if generated
        store2 = EmbeddingStore(str(user_id))
        avatar_url = store2.load_meta("avatar_url")
        try:
            nft_result = await deploy_soulbound_nft(
                owner_address   = owner_addr,
                owner_name      = name,
                personality_hash= personality_hash,
                personality     = profile,
                avatar_url      = avatar_url,
            )
        except Exception as e:
            log.error(f"NFT deploy error: {e}")

    # Build response
    hash_short = personality_hash[:16] + "..."
    resp_lines = [
        "🎉 *Soul Certificate Created!*\n",
        f"👤 Owner: `{(owner_addr or 'N/A')[:24]}...`",
        f"🔐 Personality hash: `{hash_short}`",
        f"🌐 Network: {result['network']}",
    ]

    if nft_result and nft_result.get("tx_hash"):
        nft_addr = nft_result["nft_address"]
        resp_lines += [
            "",
            "✅ *Soulbound NFT deployed!*",
            f"📝 NFT address: `{nft_addr[:24]}...`",
            f"🔍 [View on Tonscan]({nft_result['explorer_url']})",
            f"🖼 [View on Getgems]({nft_result['getgems_url']})",
            f"📋 [Metadata JSON]({nft_result['metadata_url']})",
        ]
    elif nft_result:
        resp_lines += [
            "",
            "⚠️ NFT deploy tx failed — check terminal.",
            f"📝 NFT address (not yet deployed): `{nft_result.get('nft_address', 'N/A')[:24]}...`",
        ]
    elif not config.TON_MNEMONIC:
        resp_lines.append("\n⚠️ NFT skipped — TON_MNEMONIC not set in .env")
    else:
        bag_id = result.get("storage_bag_id", "N/A")
        resp_lines.append(f"\n📦 TON Storage bag: `{bag_id[:20]}...`")
        resp_lines.append("⚠️ NFT deploy failed — check terminal")

    await update.message.reply_text(
        "\n".join(resp_lines),
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


# ── Main message handler ──────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Route every plain text message to the digital twin agent."""
    user_id = update.effective_user.id
    text    = update.message.text.strip()

    # ── Intercept wallet address input ──────────────────────────────────────
    if ctx.user_data.get("awaiting_wallet"):
        import re
        # TON address: starts with UQ/EQ/0Q and has ~48 chars, or raw 0:hex
        ton_pattern = r'^(?:[UE0]Q[A-Za-z0-9_\-]{46,48}|0:[0-9a-fA-F]{64})$'
        if re.match(ton_pattern, text):
            store = EmbeddingStore(str(user_id))
            store.save_meta("ton_wallet_address", text)
            ctx.user_data["awaiting_wallet"] = False
            net = config.TON_NETWORK
            tonscan = f"https://testnet.tonscan.org/address/{text}" if net == "testnet" else f"https://tonscan.org/address/{text}"
            await update.message.reply_text(
                f"✅ *Wallet linked!*\n\n`{text}`\n\n"
                f"[View on Tonscan]({tonscan})\n\n"
                f"Now use /mint to create your Soul Certificate NFT.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Mint Soul Certificate", callback_data="start_mint"),
                ]]),
            )
            return
        # Not a wallet address — let it fall through to twin chat

    # Try to load persisted agent
    agent = _load_agent(user_id)
    if not agent:
        await update.message.reply_text(
            "👋 Your twin isn't set up yet. Use /setup to get started!\n\n"
            "Or connect your wallet with /wallet to view your existing Soul Certificates.",
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        reply = agent.reply(text)
        await update.message.reply_text(reply)
    except Exception as e:
        log.error(f"Agent error for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong. Make sure your OpenRouter API key is configured."
        )


# ── Application setup ─────────────────────────────────────────────────────────

def main():
    config.validate()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Setup conversation
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler("setup", cmd_setup)],
        states={
            AWAITING_JSON: [MessageHandler(filters.Document.ALL, handle_json_upload)],
            AWAITING_NAME: [
                CallbackQueryHandler(handle_name_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_text),
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )

    # Mint conversation
    mint_conv = ConversationHandler(
        entry_points=[CommandHandler("mint", cmd_mint)],
        states={
            AWAITING_TON_ADDR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ton_address),
                CommandHandler("skip", handle_ton_address),
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("demo",    cmd_demo))
    app.add_handler(CommandHandler("reset",   cmd_reset))
    app.add_handler(CommandHandler("avatar",  cmd_avatar))
    app.add_handler(CommandHandler("wallet",  cmd_wallet))
    app.add_handler(CallbackQueryHandler(handle_inline_callback, pattern="^(start_setup|start_mint)$"))
    app.add_handler(setup_conv)
    app.add_handler(mint_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("🚀 Eiva bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    # Python 3.10+ requires explicit event loop creation
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()

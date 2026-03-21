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
AWAITING_SOURCE_DOC = 4

# ── In-memory registry: user_id → EivaAgent ───────────────────────────────────
agents: dict[int, EivaAgent] = {}

# ── Document context state: which command triggered the upload ────────────────
user_state: dict[int, str] = {}  # {user_id: "setup" | "add_source"}


# ── Helper: get or create agent for user ─────────────────────────────────────

def get_agent(user_id: int) -> EivaAgent | None:
    return agents.get(user_id)


def _is_setup(user_id: int) -> bool:
    store = EmbeddingStore(str(user_id))
    return store.is_ready() and store.load_meta("system_prompt") is not None


def _load_agent(user_id: int) -> EivaAgent | None:
    """Load an existing agent from persisted data (after bot restart).
    Also loads wallet address from metadata if available."""
    if user_id in agents:
        return agents[user_id]
    store = EmbeddingStore(str(user_id))
    system_prompt = store.load_meta("system_prompt")
    if system_prompt and store.is_ready():
        agent = EivaAgent(str(user_id), system_prompt)
        agents[user_id] = agent
        # Preload wallet address from metadata (if previously saved)
        wallet_addr = store.load_meta("ton_wallet_address")
        if wallet_addr:
            log.info(f"[bot] Loaded wallet for user {user_id}: {wallet_addr[:20]}...")
        return agent
    return None


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    already_setup = _is_setup(user.id)

    text = (
        f"🎭 *Welcome to Eiva — Your Immortal Digital Twin*\n\n"
        f"Transform your unique voice and personality into an *AI-powered digital twin* that:\n"
        f"• Learns from your Telegram messages\n"
        f"• Responds in *your* authentic voice\n"
        f"• Mints as a *Soulbound NFT* on TON blockchain\n"
        f"• Lives forever on-chain\n\n"
    )

    keyboard = None
    if already_setup:
        agent = _load_agent(user.id)
        if agent:
            agents[user.id] = agent
        text += "✅ *Your twin is live!* Start chatting and I'll respond as you.\n\n"
        text += "*Commands:*\n"
        text += "💬 Chat freely — I'll respond as your digital twin\n"
        text += "👤 /profile — view extracted personality\n"
        text += "💎 /mint — create your Soul Certificate NFT\n"
        text += "🎨 /avatar — generate AI portrait\n"
        text += "💳 /wallet — link TON wallet\n"
        text += "📊 /status — twin indexing stats\n"
        text += "🔄 /reset — clear conversation history\n"
        text += "❓ /help — show all commands"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Web Dashboard", url="https://zhenek73.github.io/eiva/eiva-web/"),
            InlineKeyboardButton("💎 Mint NFT", callback_data="start_mint"),
        ]])
    else:
        text += (
            "To create your twin, upload a Telegram chat export and I'll extract your personality.\n\n"
            "*📝 3 Easy Steps:*\n"
            "1️⃣ *Export:* Telegram Desktop → Settings → Advanced → Export Telegram Data\n"
            "2️⃣ *Select:* Personal chats, JSON format\n"
            "3️⃣ *Upload:* Send the `result.json` file with /setup\n\n"
            "Then chat with your twin, mint it as an NFT, and share it with the world."
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
    """Receive the JSON file for /setup or /add_source."""
    user_id = update.effective_user.id
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Please send a .json file.")
        # Return to the appropriate state
        return AWAITING_JSON if user_state.get(user_id) == "setup" else AWAITING_SOURCE_DOC

    await update.message.reply_text("⏳ Downloading and analyzing your export...")
    await update.message.chat.send_action(ChatAction.TYPING)

    # Download to temp file
    tg_file = await ctx.bot.get_file(doc.file_id)
    tmp_path = Path(tempfile.mktemp(suffix=".json"))
    await tg_file.download_to_drive(tmp_path)

    # Check which command triggered this
    mode = user_state.get(user_id, "setup")

    if mode == "add_source":
        # For /add_source, use existing owner name and merge
        store = EmbeddingStore(str(user_id))
        owner_name = store.load_meta("owner_name", "Unknown")

        # Read the export text
        export_text = tmp_path.read_text(encoding="utf-8")

        # Call merge_personality
        from personality import merge_personality

        await update.message.reply_text("📖 Parsing your messages...")
        try:
            merge_personality(str(user_id), export_text, owner_name)

            # Increment source count
            count = store.increment_source_count()
            tier = store.get_tier()
            tier_info = config.TIER_LIMITS.get(tier, config.TIER_LIMITS["bronze"])

            await update.message.reply_text(
                f"✅ *Source {count}/{tier_info['sources']} added!*\n\n"
                f"Your twin now knows you even better! 🎭\n\n"
                f"Use /profile to see the updated personality, or just chat away!",
                parse_mode=ParseMode.MARKDOWN,
            )

            # Clear state
            user_state.pop(user_id, None)
            return ConversationHandler.END
        except Exception as e:
            log.error(f"[add_source] Merge failed for user {user_id}: {e}")
            await update.message.reply_text(
                f"⚠️ Merge failed: {e}\n\nPlease try again or use /setup for troubleshooting.",
            )
            user_state.pop(user_id, None)
            return ConversationHandler.END
        finally:
            # Clean up temp file
            try:
                tmp_path.unlink()
            except Exception:
                pass
    else:
        # Standard /setup flow
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
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    if query.data.startswith("name_confirm:"):
        name = query.data.split(":", 1)[1]
        await query.edit_message_text(f"✅ Got it! Processing as *{name}*...", parse_mode=ParseMode.MARKDOWN)
        user_state[user_id] = "setup"  # Mark this as setup flow
        await _process_export(update, ctx, name)
        user_state.pop(user_id, None)
        return ConversationHandler.END
    elif query.data == "name_manual":
        await query.edit_message_text("✏️ Please type your name exactly as it appears in the export:")
        return AWAITING_NAME


async def handle_name_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()
    await update.message.reply_text(f"✅ Processing as *{name}*...", parse_mode=ParseMode.MARKDOWN)
    user_state[user_id] = "setup"  # Mark this as setup flow
    await _process_export(update, ctx, name)
    user_state.pop(user_id, None)
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


# ── /add_source ────────────────────────────────────────────────────────────────

async def cmd_add_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Add another Telegram export to augment the personality (tier-limited)."""
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))

    # Check if setup is complete
    if not store.is_ready():
        await update.message.reply_text(
            "❌ You need to run /setup first to create your initial digital twin.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Check tier and source count
    tier = store.get_tier()
    source_count = store.get_source_count()
    tier_info = config.TIER_LIMITS.get(tier, config.TIER_LIMITS["bronze"])
    max_sources = tier_info["sources"]

    if source_count >= max_sources:
        # Build tier table for upgrade message
        tier_table = "*Available Tiers:*\n\n"
        for tier_key, tier_data in config.TIER_LIMITS.items():
            tier_table += f"{tier_data['label']} — {tier_data['sources']} sources\n"

        await update.message.reply_text(
            f"⚠️ You've reached your limit: *{source_count}/{max_sources}* sources\n\n"
            f"Your tier: {tier_info['label']}\n\n"
            f"{tier_table}\n"
            f"_Upgrade coming soon in the dashboard!_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Under limit — ask for upload
    user_state[user_id] = "add_source"
    await update.message.reply_text(
        "📂 *Add Another Personality Source*\n\n"
        f"Your current tier: {tier_info['label']} ({source_count}/{max_sources} sources used)\n\n"
        "Send me another Telegram export JSON file to merge with your existing personality.\n\n"
        "This will enrich your twin with new communication patterns and traits from a different context "
        "(e.g., work chats, family chats, friend groups).\n\n"
        "Upload the `result.json` file 👇",
        parse_mode=ParseMode.MARKDOWN,
    )
    return AWAITING_SOURCE_DOC


# ── /settings ──────────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show and edit personality response settings."""
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))

    # Check if setup is complete
    if not store.is_ready():
        await update.message.reply_text(
            "❌ You need to run /setup first to create your digital twin.",
        )
        return

    settings = store.load_meta("settings") or config.DEFAULT_SETTINGS
    ctx.user_data["editing_settings"] = True

    # Build keyboard with toggle buttons
    keyboard = _build_settings_keyboard(settings)

    await update.message.reply_text(
        "⚙️ *Personality Settings*\n\n"
        "Configure how your digital twin responds:\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


def _build_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Build an inline keyboard for settings toggles."""
    buttons = []

    # First row: signature_phrases, formal_mode
    buttons.append([
        InlineKeyboardButton(
            f"{'✅' if settings.get('signature_phrases') else '❌'} Signature phrases",
            callback_data="setting_toggle:signature_phrases"
        ),
        InlineKeyboardButton(
            f"{'✅' if settings.get('formal_mode') else '❌'} Formal mode",
            callback_data="setting_toggle:formal_mode"
        ),
    ])

    # Second row: emoji, humor
    buttons.append([
        InlineKeyboardButton(
            f"{'✅' if settings.get('emoji') else '❌'} Emoji in replies",
            callback_data="setting_toggle:emoji"
        ),
        InlineKeyboardButton(
            f"{'✅' if settings.get('humor') else '❌'} Humor",
            callback_data="setting_toggle:humor"
        ),
    ])

    # Third row: short_responses, language
    buttons.append([
        InlineKeyboardButton(
            f"{'✅' if settings.get('short_responses') else '❌'} Short responses",
            callback_data="setting_toggle:short_responses"
        ),
    ])

    # Language selector
    current_lang = settings.get("language", "auto")
    buttons.append([
        InlineKeyboardButton(
            f"🌐 Language: {current_lang.title()}",
            callback_data="setting_lang"
        ),
    ])

    # Save button
    buttons.append([
        InlineKeyboardButton("💾 Save Settings", callback_data="setting_save"),
    ])

    return InlineKeyboardMarkup(buttons)


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
        "*/twins* — View your digital twins (own + purchased)\n"
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


# ── /ask (direct twin chat) ────────────────────────────────────────────────────

async def cmd_feedback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Collect feedback from users (useful for hackathon judges).
    Usage: /feedback Your feedback message here
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Unknown"
    args = update.message.text[10:].strip()  # Skip "/feedback "

    if not args:
        await update.message.reply_text(
            "💬 *Share Your Feedback*\n\n"
            "Usage: `/feedback [your feedback]`\n\n"
            "Example: `/feedback The personality extraction was spot-on!`\n\n"
            "Your feedback helps us improve Eiva. Thank you!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Save feedback to local file
    feedback_dir = Path("data/feedback")
    feedback_dir.mkdir(exist_ok=True, parents=True)

    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    feedback_file = feedback_dir / "feedback.txt"

    feedback_entry = f"[{timestamp}] User {user_id} ({user_name}): {args}\n"
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(feedback_entry)

    log.info(f"[feedback] Collected from user {user_id}: {args[:80]}")

    # Try to send to admin via Telegram (if ADMIN_ID is set)
    try:
        ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
        if ADMIN_ID:
            admin_text = (
                f"📬 *Feedback from {user_name}* (ID: {user_id})\n\n"
                f"{args}"
            )
            await ctx.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        log.debug(f"[feedback] Could not send to admin: {e}")

    # Confirm to user
    await update.message.reply_text(
        "✅ *Thank you for your feedback!*\n\n"
        "Your message has been saved and will help us improve Eiva.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Direct chat with your digital twin.
    Usage: /ask How would you handle a difficult situation?
    """
    user_id = update.effective_user.id
    args = update.message.text[5:].strip()  # Skip "/ask "

    if not args:
        await update.message.reply_text(
            "💬 *Ask your Digital Twin*\n\n"
            "Usage: `/ask [your question]`\n\n"
            "Example: `/ask What's your take on AI?`\n\n"
            "Or just send a message — I'm always listening!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    agent = _load_agent(user_id)
    if not agent:
        await update.message.reply_text(
            "👋 Your twin isn't set up yet. Use /setup to get started!"
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        reply = agent.reply(args)
        await update.message.reply_text(reply)
    except Exception as e:
        log.error(f"Agent error in /ask for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong. Make sure your OpenRouter API key is configured."
        )


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
    """Handle inline keyboard button callbacks (setup, mint, settings)."""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    # ── Setup callback ────────────────────────────────────────────────────────
    if query.data == "start_setup":
        user_state[user_id] = "setup"
        await query.message.reply_text(
            "📂 *Setup your Digital Twin*\n\n"
            "Send me your Telegram export JSON file (`result.json`).\n\n"
            "To export: *Telegram Desktop → Settings → Advanced → Export Telegram Data*\n"
            "Choose: ✅ Personal chats, Format: *JSON*\n\n"
            "Then upload the `result.json` file here 👇",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── Mint callback ────────────────────────────────────────────────────────
    elif query.data == "start_mint":
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

    # ── Settings callbacks ────────────────────────────────────────────────────
    elif query.data.startswith("setting_toggle:"):
        store = EmbeddingStore(str(user_id))
        setting_name = query.data.split(":", 1)[1]
        settings = store.load_meta("settings") or config.DEFAULT_SETTINGS

        # Toggle the setting
        settings[setting_name] = not settings.get(setting_name, True)
        store.save_meta("settings", settings)

        # Update the keyboard
        keyboard = _build_settings_keyboard(settings)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif query.data == "setting_lang":
        store = EmbeddingStore(str(user_id))
        settings = store.load_meta("settings") or config.DEFAULT_SETTINGS
        current_lang = settings.get("language", "auto")

        # Cycle through languages
        langs = ["auto", "English", "Russian"]
        current_idx = langs.index(current_lang.title() if current_lang != "auto" else "auto")
        next_idx = (current_idx + 1) % len(langs)
        new_lang = langs[next_idx]

        settings["language"] = new_lang
        store.save_meta("settings", settings)

        # Update keyboard
        keyboard = _build_settings_keyboard(settings)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif query.data == "setting_save":
        store = EmbeddingStore(str(user_id))
        settings = store.load_meta("settings") or config.DEFAULT_SETTINGS

        await query.edit_message_text(
            "✅ *Settings Saved!*\n\n"
            "Your personality response settings have been updated. "
            "I'll use these preferences from now on.",
            parse_mode=ParseMode.MARKDOWN,
        )


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
        except ImportError as e:
            log.error(f"NFT deploy import error (fallback to cert): {e}")
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

    # Build inline keyboard for successful NFT deploy
    keyboard = None
    if nft_result and nft_result.get("tx_hash"):
        nft_addr = nft_result["nft_address"]
        resp_lines += [
            "",
            "✅ *Soulbound NFT deployed!*",
            f"📝 NFT address: `{nft_addr[:24]}...`",
            f"📋 [View metadata]({nft_result['metadata_url']})",
        ]
        # Add buttons for explorer links
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Tonscan", url=nft_result['explorer_url']),
                InlineKeyboardButton("🖼 Getgems", url=nft_result['getgems_url']),
            ],
        ])
    elif nft_result:
        resp_lines += [
            "",
            "⚠️ NFT deploy tx failed — falling back to Soul Certificate anchor.",
            f"📝 NFT address (not yet deployed): `{nft_result.get('nft_address', 'N/A')[:24]}...`",
        ]
    elif not config.TON_MNEMONIC:
        resp_lines.append("\n⚠️ NFT skipped — TON_MNEMONIC not set in .env")
    else:
        bag_id = result.get("storage_bag_id", "N/A")
        resp_lines.append(f"\n📦 TON Storage bag: `{bag_id[:20]}...`")
        resp_lines.append("⚠️ NFT deploy failed — Soul Certificate anchor recorded on-chain")

    await update.message.reply_text(
        "\n".join(resp_lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
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


# ── /twins (list user's digital twins) ─────────────────────────────────────────

async def cmd_twins(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show all digital twins the user has access to (own + purchased)."""
    user_id = update.effective_user.id
    store   = EmbeddingStore(str(user_id))

    # Check if user's own twin is set up
    is_ready = store.is_ready()
    owner_name = store.load_meta("owner_name", "Unknown")

    text = "🧬 *Your Digital Twins*\n\n"

    if is_ready:
        text += f"✅ *Your Own Twin: {owner_name}*\n"
        text += "Status: Ready to chat\n"
        text += "→ Start chatting or use /mint to create an NFT\n\n"
    else:
        text += "❌ No personal twin yet\n"
        text += "→ Use /setup to create your digital twin\n\n"

    text += "*Coming Soon:*\n"
    text += "Purchase others' digital twin NFTs on Getgems and chat with them here!"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 Explore Twins", url="https://testnet.getgems.io/collections?query=Eiva"),
    ]])

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ── /stats (admin only) ────────────────────────────────────────────────────────

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only command: show total users, twins built, NFTs minted."""
    user_id = update.effective_user.id

    # For now, only the bot owner (user_id 1234567890) can see stats
    # In production, you'd check against a list of admin IDs from config
    ADMIN_ID = 1234567890  # Replace with actual admin ID or read from config

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ This command is admin-only.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Count users by checking data directory (simplified)
    from pathlib import Path
    data_dir = Path("./data/embeddings")
    user_count = 0
    twins_built = 0

    if data_dir.exists():
        # Each user_id is a directory
        user_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
        user_count = len(user_dirs)

        # Count ready twins
        for user_dir in user_dirs:
            try:
                uid = user_dir.name
                store = EmbeddingStore(uid)
                if store.is_ready():
                    twins_built += 1
            except:
                pass

    text = (
        "📊 *Eiva Statistics*\n\n"
        f"👥 *Total Users:* {user_count}\n"
        f"🧬 *Twins Built:* {twins_built}\n"
        f"🎭 *Completion Rate:* {100 * twins_built // max(user_count, 1)}%\n\n"
        "_Stats update on demand. Check console logs for detailed metrics._"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── Application setup ─────────────────────────────────────────────────────────

def main():
    config.validate()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Setup & Add Source conversation (both handle JSON uploads)
    setup_conv = ConversationHandler(
        entry_points=[
            CommandHandler("setup", cmd_setup),
            CommandHandler("add_source", cmd_add_source),
        ],
        states={
            AWAITING_JSON: [MessageHandler(filters.Document.ALL, handle_json_upload)],
            AWAITING_NAME: [
                CallbackQueryHandler(handle_name_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_text),
            ],
            AWAITING_SOURCE_DOC: [MessageHandler(filters.Document.ALL, handle_json_upload)],
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

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("profile",  cmd_profile))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("add_source", cmd_add_source))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("demo",     cmd_demo))
    app.add_handler(CommandHandler("ask",      cmd_ask))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("reset",    cmd_reset))
    app.add_handler(CommandHandler("avatar",   cmd_avatar))
    app.add_handler(CommandHandler("wallet",   cmd_wallet))
    app.add_handler(CommandHandler("twins",    cmd_twins))
    app.add_handler(CommandHandler("stats",    cmd_stats))
    # Callback handlers: setup, mint, and settings
    app.add_handler(CallbackQueryHandler(handle_inline_callback, pattern="^(start_setup|start_mint|setting_)$"))
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

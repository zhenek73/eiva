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

    if already_setup:
        agent = _load_agent(user.id)
        if agent:
            agents[user.id] = agent
        text += "✅ Your twin is *already set up*! Just send a message and I'll respond as you.\n\n"
        text += "Commands: /profile · /mint · /reset · /status"
    else:
        text += (
            "To get started, use /setup and upload your Telegram chat export.\n\n"
            "📖 *How to export your chats:*\n"
            "Telegram Desktop → Settings → Advanced → Export Telegram Data\n"
            "→ Select chats → Format: *JSON* → Export"
        )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


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
    added = store.add_messages(messages)
    await msg.reply_text(f"🧠 Indexed *{added}* messages into memory.", parse_mode=ParseMode.MARKDOWN)

    # Extract personality
    await msg.reply_text("🔬 Analyzing your personality (this takes ~30 seconds)...")
    profile = extract_personality(messages, str(user_id))

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


# ── /reset ────────────────────────────────────────────────────────────────────

async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent   = get_agent(user_id)
    if agent:
        agent.reset_history()
        await update.message.reply_text("🔄 Conversation history cleared. Long-term memory is intact.")
    else:
        await update.message.reply_text("No active twin loaded. Use /setup first.")


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

    await update.message.reply_text("⏳ Creating your Soul Certificate on TON blockchain...")
    await update.message.chat.send_action(ChatAction.TYPING)

    result = await create_soul_certificate(
        user_id    = str(user_id),
        owner_name = name,
        personality= profile,
        ton_address= ton_address,
    )

    hash_short = result["personality_hash"][:16] + "..."
    bag_id     = result.get("storage_bag_id", "N/A")
    tx_hash    = result.get("tx_hash")
    explorer   = result.get("explorer_url")

    resp = (
        f"🎉 *Soul Certificate Created!*\n\n"
        f"🔐 Personality hash: `{hash_short}`\n"
        f"📦 TON Storage bag: `{bag_id[:20]}...`\n"
        f"🌐 Network: {result['network']}\n"
    )
    if tx_hash:
        resp += f"\n✅ NFT minted!\n🔍 [View on explorer]({explorer})"
    else:
        resp += "\nℹ️ NFT mint skipped (no wallet/mnemonic configured)."

    await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


# ── Main message handler ──────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Route every plain text message to the digital twin agent."""
    user_id = update.effective_user.id
    text    = update.message.text

    # Try to load persisted agent
    agent = _load_agent(user_id)
    if not agent:
        await update.message.reply_text(
            "👋 Your twin isn't set up yet. Use /setup to get started!",
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
    app.add_handler(CommandHandler("reset",   cmd_reset))
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

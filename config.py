"""
Eiva — AI Digital Twin
Configuration management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── LLM via OpenRouter ────────────────────────────────────────────────────────
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model used for chat / agent responses
LLM_MODEL           = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
# Model used for personality extraction (smarter)
LLM_SMART_MODEL     = os.getenv("LLM_SMART_MODEL", "openai/gpt-4o")
# Model used for embeddings (must be embedding-capable)
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

# ── TON ───────────────────────────────────────────────────────────────────────
# 24-word mnemonic for the wallet that will sign NFT mint transactions
TON_MNEMONIC        = os.getenv("TON_MNEMONIC", "")  # space-separated 24 words
TON_NETWORK         = os.getenv("TON_NETWORK", "testnet")   # "testnet" | "mainnet"
TON_API_KEY         = os.getenv("TON_API_KEY", "")    # toncenter.com API key (optional)

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN        = os.getenv("GITHUB_TOKEN", "")   # PAT for metadata upload

# ── Storage ───────────────────────────────────────────────────────────────────
BASE_DIR            = Path(__file__).parent
DATA_DIR            = BASE_DIR / "data"
CHROMA_DIR          = DATA_DIR / "chroma"
EXPORTS_DIR         = DATA_DIR / "exports"

DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ── Misc ──────────────────────────────────────────────────────────────────────
MAX_MESSAGES_FOR_PERSONALITY = 500   # messages sampled for personality extraction
MIN_MESSAGES_REQUIRED        = 50    # minimum to build a useful twin
CONTEXT_MESSAGES             = 8     # conversation turns kept in memory
TOP_K_SIMILAR                = 5     # similar messages retrieved from vector DB

def validate():
    """Raise if critical env vars are missing."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}\n"
            f"Copy .env.example → .env and fill in the values."
        )

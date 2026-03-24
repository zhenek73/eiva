"""
Eiva FastAPI Backend
Exposes HTTP API for the web frontend
"""
import os, json, uuid, asyncio, logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

import config
import parser as telegram_parser
from personality import extract_personality, build_system_prompt
from embeddings import EmbeddingStore
from agent import EivaAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Eiva API",
    description="AI Digital Twin on TON",
    version="1.0.0",
)

# ── CORS — allow Vercel + GitHub Pages + localhost ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eiva-app.vercel.app",
        "https://zhenek73.github.io",
        "http://localhost:8080",
        "http://localhost:3000",
        "*",  # TODO: remove in production, replace with real domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Models
# ─────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    wallet_address: str
    demo_mode: bool = False

class ChatResponse(BaseModel):
    reply: str
    confidence: str  # LOW / MEDIUM / HIGH
    twin_name: str

class UploadResponse(BaseModel):
    success: bool
    message: str
    profile_summary: Optional[str] = None
    messages_indexed: Optional[int] = None

class ProfileResponse(BaseModel):
    twin_name: str
    personality_summary: str
    communication_style: str
    topics: list
    messages_indexed: int
    sources: int
    tier: str
    mode: str
    nft_address: Optional[str] = None


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _user_id_from_wallet(wallet: str) -> str:
    """Use wallet address as user identifier"""
    return f"web_{wallet.replace(':', '_').replace('/', '_')[:32]}"

def _check_upload_limit(wallet: str, file_size: int, demo: bool = False) -> tuple[bool, str]:
    """Check if user can upload (tier-based limits)"""
    if demo:
        return True, "demo"

    # 3 MB free tier for wallet-connected users
    FREE_LIMIT = 3 * 1024 * 1024  # 3 MB
    if file_size <= FREE_LIMIT:
        return True, "bronze"

    # TODO: check paid tier from ChromaDB metadata
    return False, f"File too large. Free tier: 3 MB. Your file: {file_size // 1024 // 1024} MB. Upgrade in Telegram bot."


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "eiva-api", "version": "1.0.0"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_export(
    file: UploadFile = File(...),
    x_wallet_address: str = Header(..., description="TON wallet address"),
    x_demo_mode: bool = Header(False),
):
    """Upload Telegram JSON export and build digital twin"""
    try:
        contents = await file.read()
        file_size = len(contents)

        # Check limits
        ok, tier_or_msg = _check_upload_limit(x_wallet_address, file_size, x_demo_mode)
        if not ok:
            raise HTTPException(status_code=402, detail=tier_or_msg)

        # Validate JSON
        try:
            json.loads(contents.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON file")

        user_id = _user_id_from_wallet(x_wallet_address)

        # Save temp file
        uploads_dir = Path("data/exports")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        temp_path = uploads_dir / f"{user_id}_{uuid.uuid4().hex[:8]}.json"
        temp_path.write_bytes(contents)

        # Parse messages
        owner_name = telegram_parser.detect_owner_name(str(temp_path)) or "Unknown"
        messages = telegram_parser.parse_export(str(temp_path), owner_name)
        if not messages:
            raise HTTPException(status_code=422, detail="No messages found in export")

        # Extract personality (blocking GPT call → run in thread)
        profile = await asyncio.to_thread(extract_personality, messages, user_id)

        # Build system prompt and store in ChromaDB
        system_prompt = build_system_prompt(profile, owner_name)
        store = EmbeddingStore(user_id)
        added = await asyncio.to_thread(store.add_messages, messages)
        store.save_meta("owner_name", owner_name)
        store.save_meta("personality", profile)
        store.save_meta("personality_profile", json.dumps(profile, ensure_ascii=False))
        store.save_meta("system_prompt", system_prompt)
        store.save_meta("tier", tier_or_msg)

        # Cleanup temp
        temp_path.unlink(missing_ok=True)

        return UploadResponse(
            success=True,
            message=f"Twin created for {owner_name}",
            profile_summary=profile.get("communication_style", ""),
            messages_indexed=added,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send message to digital twin and get response"""
    try:
        if req.demo_mode:
            user_id = "demo_durov"
            twin_name = "Pavel Durov"
        else:
            user_id = _user_id_from_wallet(req.wallet_address)
            twin_name = "Your Twin"

        store = EmbeddingStore(user_id)
        if not store.is_ready():
            raise HTTPException(status_code=404, detail="Twin not found. Upload your Telegram export first.")

        # Load system prompt (built during upload)
        system_prompt = store.load_meta("system_prompt") or ""
        owner_name = store.load_meta("owner_name") or twin_name
        twin_name = owner_name if owner_name != "Unknown" else twin_name

        # Determine confidence from memory retrieval count
        similar = store.search(req.message, top_k=config.TOP_K_SIMILAR)
        count = len(similar)
        if count < 2:
            confidence = "LOW ⚠️"
        elif count < 5:
            confidence = "MEDIUM ✓"
        else:
            confidence = "HIGH ✅"

        # Generate reply
        agent = EivaAgent(user_id, system_prompt)
        reply = await asyncio.to_thread(agent.reply, req.message)

        return ChatResponse(reply=reply, confidence=confidence, twin_name=twin_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile")
async def get_profile(x_wallet_address: str = Header(...)):
    """Get digital twin profile for wallet"""
    try:
        user_id = _user_id_from_wallet(x_wallet_address)
        store = EmbeddingStore(user_id)

        if not store.is_ready():
            raise HTTPException(status_code=404, detail="Twin not found. Upload your Telegram export first.")

        profile = store.load_meta("personality") or {}
        owner_name = store.load_meta("owner_name") or "Unknown"

        return ProfileResponse(
            twin_name=owner_name,
            personality_summary=profile.get("emotional_tone", ""),
            communication_style=profile.get("communication_style", ""),
            topics=profile.get("topics_of_interest", []),
            messages_indexed=store.count(),
            sources=store.get_source_count(),
            tier=store.get_tier(),
            mode=store.load_meta("mode") or "personal",
            nft_address=store.load_meta("nft_address"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Profile error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo/profile")
async def get_demo_profile():
    """Get Durov demo profile"""
    store = EmbeddingStore("demo_durov")
    if store.is_ready():
        profile = store.load_meta("personality") or {}
        return {
            "twin_name": store.load_meta("owner_name") or "Pavel Durov",
            "personality_summary": profile.get("emotional_tone", "Tech visionary, privacy advocate"),
            "communication_style": profile.get("communication_style", "Direct, philosophical, minimalist."),
            "topics": profile.get("topics_of_interest", ["privacy", "freedom", "AI", "blockchain"]),
            "messages_indexed": store.count(),
            "sources": store.get_source_count(),
            "tier": "silver",
            "mode": "personal",
        }
    # Fallback static demo data
    return {
        "twin_name": "Pavel Durov",
        "personality_summary": "Tech visionary, privacy advocate, founder of Telegram and VK",
        "communication_style": "Direct, philosophical, minimalist. Speaks about freedom, technology, discipline.",
        "topics": ["privacy", "freedom", "AI", "blockchain", "Telegram", "discipline"],
        "messages_indexed": 20,
        "sources": 2,
        "tier": "silver",
        "mode": "personal",
    }


@app.get("/api/stats")
async def get_stats():
    """Platform stats"""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        collections = [c.name for c in client.list_collections()]
        user_count = len([c for c in collections if c.startswith("user_")])
        return {
            "total_twins": user_count,
            "demo_available": "demo_durov" in collections,
            "network": os.getenv("TON_NETWORK", "testnet"),
        }
    except Exception:
        return {"total_twins": 0, "demo_available": False, "network": "testnet"}


# ─────────────────────────────────────────
# Run
# ─────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=2,
    )

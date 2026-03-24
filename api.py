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

from config import Config
from parser import TelegramParser
from personality import PersonalityExtractor
from embeddings import EmbeddingsStore
from agent import DigitalTwinAgent

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

# ── Singleton services ──
embeddings_store: Optional[EmbeddingsStore] = None
personality_extractor: Optional[PersonalityExtractor] = None

@app.on_event("startup")
async def startup():
    global embeddings_store, personality_extractor
    embeddings_store = EmbeddingsStore()
    personality_extractor = PersonalityExtractor()
    logger.info("Eiva API started")


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
            data = json.loads(contents.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON file")

        user_id = _user_id_from_wallet(x_wallet_address)

        # Save temp file
        uploads_dir = Path("data/exports")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        temp_path = uploads_dir / f"{user_id}_{uuid.uuid4().hex[:8]}.json"
        temp_path.write_bytes(contents)

        # Parse messages
        parser = TelegramParser()
        messages, owner_name = parser.parse(str(temp_path))
        if not messages:
            raise HTTPException(status_code=422, detail="No messages found in export")

        # Extract personality (async GPT call)
        profile = await asyncio.to_thread(
            personality_extractor.extract, messages, owner_name
        )

        # Store in ChromaDB
        collection_name = f"user_{user_id}"
        await asyncio.to_thread(
            embeddings_store.store_messages, messages, profile, collection_name, tier_or_msg
        )

        # Cleanup temp
        temp_path.unlink(missing_ok=True)

        return UploadResponse(
            success=True,
            message=f"Twin created for {owner_name}",
            profile_summary=profile.get("personality_summary", ""),
            messages_indexed=len(messages),
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
            collection_name = "demo_durov"
            twin_name = "Pavel Durov"
        else:
            collection_name = f"user_{_user_id_from_wallet(req.wallet_address)}"
            twin_name = "Your Twin"

        agent = DigitalTwinAgent(embeddings_store, collection_name)
        reply, confidence = await asyncio.to_thread(agent.reply, req.message)

        return ChatResponse(
            reply=reply,
            confidence=confidence,
            twin_name=twin_name,
        )

    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile")
async def get_profile(x_wallet_address: str = Header(...)):
    """Get digital twin profile for wallet"""
    try:
        user_id = _user_id_from_wallet(x_wallet_address)
        collection_name = f"user_{user_id}"

        metadata = embeddings_store.get_collection_metadata(collection_name)
        if not metadata:
            raise HTTPException(status_code=404, detail="Twin not found. Upload your Telegram export first.")

        return ProfileResponse(
            twin_name=metadata.get("owner_name", "Unknown"),
            personality_summary=metadata.get("personality_summary", ""),
            communication_style=metadata.get("communication_style", ""),
            topics=metadata.get("topics", []),
            messages_indexed=metadata.get("source_count", 0),
            sources=len(metadata.get("sources", [])),
            tier=metadata.get("tier", "bronze"),
            mode=metadata.get("mode", "personal"),
            nft_address=metadata.get("nft_address"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Profile error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo/profile")
async def get_demo_profile():
    """Get Durov demo profile"""
    try:
        metadata = embeddings_store.get_collection_metadata("demo_durov")
        if not metadata:
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
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Platform stats"""
    try:
        collections = embeddings_store.list_collections()
        user_count = len([c for c in collections if c.startswith("user_")])
        return {
            "total_twins": user_count,
            "demo_available": "demo_durov" in collections,
            "network": os.getenv("TON_NETWORK", "testnet"),
        }
    except Exception as e:
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

"""
Eiva — embeddings.py
Stores messages in a ChromaDB vector database and retrieves
semantically similar messages for RAG-powered responses.
"""

import json
import hashlib
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

import config
from parser import Message


# ── OpenAI-compatible client pointed at OpenRouter ────────────────────────────
def _get_openai_client() -> OpenAI:
    return OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
    )


# ── ChromaDB setup ────────────────────────────────────────────────────────────
class EmbeddingStore:
    """
    Wraps ChromaDB + OpenRouter embeddings.
    Each user's messages live in a collection named after their user_id.
    """

    def __init__(self, user_id: str):
        self.user_id = str(user_id)
        self.client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name=f"eiva_{self.user_id}",
            metadata={"hnsw:space": "cosine"},
        )

    # ── Indexing ──────────────────────────────────────────────────────────────

    def add_messages(self, messages: list[Message], batch_size: int = 100) -> int:
        """
        Embed and store messages. Skips already-indexed ones.
        Returns number of newly added messages.
        """
        oai = _get_openai_client()
        added = 0

        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            texts  = [m.text for m in batch]
            ids    = [self._msg_id(m) for m in batch]
            metas  = [{"date": m.date, "chat": m.chat_name} for m in batch]

            # Skip IDs already in collection
            existing = set(self.collection.get(ids=ids)["ids"])
            new_indices = [j for j, mid in enumerate(ids) if mid not in existing]
            if not new_indices:
                continue

            new_texts  = [texts[j]  for j in new_indices]
            new_ids    = [ids[j]    for j in new_indices]
            new_metas  = [metas[j]  for j in new_indices]

            # Get embeddings from OpenRouter
            response = oai.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=new_texts,
            )
            embeddings = [e.embedding for e in response.data]

            self.collection.add(
                ids=embeddings and new_ids,
                embeddings=embeddings,
                documents=new_texts,
                metadatas=new_metas,
            )
            added += len(new_ids)
            print(f"  Indexed batch {i//batch_size + 1}: +{len(new_ids)} messages")

        return added

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = None) -> list[str]:
        """
        Return top_k most similar message texts from the user's history.
        """
        top_k = top_k or config.TOP_K_SIMILAR
        if self.collection.count() == 0:
            return []

        oai = _get_openai_client()
        response = oai.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=[query],
        )
        query_embedding = response.data[0].embedding

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
        )
        return results["documents"][0] if results["documents"] else []

    # ── Stats ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        return self.collection.count()

    def is_ready(self) -> bool:
        return self.collection.count() >= config.MIN_MESSAGES_REQUIRED

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _msg_id(m: Message) -> str:
        """Stable unique ID for a message."""
        raw = f"{m.chat_name}:{m.id}:{m.date}"
        return hashlib.md5(raw.encode()).hexdigest()

    def save_meta(self, key: str, value) -> None:
        """Persist arbitrary JSON metadata alongside the collection."""
        meta_file = config.DATA_DIR / f"meta_{self.user_id}.json"
        data = {}
        if meta_file.exists():
            data = json.loads(meta_file.read_text())
        data[key] = value
        meta_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_meta(self, key: str, default=None):
        meta_file = config.DATA_DIR / f"meta_{self.user_id}.json"
        if not meta_file.exists():
            return default
        data = json.loads(meta_file.read_text())
        return data.get(key, default)

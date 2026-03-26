"""
Script to pre-load Pavel Durov demo twin data.
Run once from the eiva-bot directory:
    cd /var/www/eiva/eiva-bot
    source venv/bin/activate
    python3 demo_data/create_durov_demo.py
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
import chromadb
from embeddings import EmbeddingStore
from personality import extract_personality, build_system_prompt
from parser import Message

DEMO_USER_ID = "demo_durov"

def create_durov_demo():
    print("Creating Pavel Durov demo twin...")

    # Load demo messages from JSON
    json_path = os.path.join(os.path.dirname(__file__), "durov_demo.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert to Message objects (as expected by EmbeddingStore.add_messages)
    messages = []
    for m in data["messages"]:
        if m.get("text"):
            messages.append(Message(
                id=m["id"],
                date=m["date"],
                text=m["text"],
                chat_name=m.get("chat_name", "Telegram Channel"),
            ))

    print(f"Loaded {len(messages)} messages from durov_demo.json")

    # Delete existing demo collection if present, then recreate
    chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    existing = [c.name for c in chroma_client.list_collections()]
    if f"eiva_{DEMO_USER_ID}" in existing:
        chroma_client.delete_collection(f"eiva_{DEMO_USER_ID}")
        print("Cleared existing demo collection")

    store = EmbeddingStore(DEMO_USER_ID)

    # Index messages using real add_messages API
    print("Indexing messages into ChromaDB (this calls OpenRouter embeddings)...")
    added = store.add_messages(messages)
    print(f"Indexed {added} new messages")

    # Extract personality using LLM
    print("Extracting personality profile via LLM...")
    profile = extract_personality(messages, DEMO_USER_ID)

    # Build system prompt
    system_prompt = build_system_prompt(profile, "Pavel Durov")

    # Save all metadata
    store.save_meta("owner_name", "Pavel Durov")
    store.save_meta("personality", json.dumps(profile, ensure_ascii=False))
    store.save_meta("system_prompt", system_prompt)
    store.save_meta("mode", "personal")
    store.save_meta("tier", "silver")
    store.save_meta("is_demo", "true")
    store.save_meta("source_count", "2")
    source_labels = json.dumps([
        {"type": "telegram_channel", "comment": "@durov Telegram channel (public posts)"},
        {"type": "interview", "comment": "Lex Fridman interview transcript"},
    ])
    store.save_meta("source_labels", source_labels)

    print("\n✅ Pavel Durov demo twin created!")
    print(f"   User ID  : {DEMO_USER_ID}")
    print(f"   Messages : {store.count()}")
    print(f"   Ready    : {store.is_ready()}")
    print(f"\nProfile preview:")
    print(f"   Style    : {profile.get('communication_style', 'N/A')}")
    print(f"   Topics   : {profile.get('topics_of_interest', [])}")

if __name__ == "__main__":
    create_durov_demo()

"""
Script to pre-load Pavel Durov demo twin data.
Run once: py demo_data/create_durov_demo.py
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from embeddings import EmbeddingStore
from personality import extract_personality, build_system_prompt

DEMO_USER_ID = "demo_durov"

def create_durov_demo():
    print("Creating Pavel Durov demo twin...")

    # Load demo messages
    with open(os.path.join(os.path.dirname(__file__), "durov_demo.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = [m["text"] for m in data["messages"] if m.get("text")]

    # Build store
    store = EmbeddingStore(DEMO_USER_ID)
    store.clear()

    # Index messages
    for i, msg in enumerate(messages):
        store.add(msg, {"source": "durov_demo", "index": i})

    print(f"Indexed {len(messages)} messages")

    # Save personality metadata
    personality_data = {
        "name": "Pavel Durov",
        "traits": ["principled", "disciplined", "visionary", "blunt", "philosophical"],
        "topics": ["freedom", "privacy", "Telegram", "TON", "discipline", "technology"],
        "style": "direct, philosophical, sometimes provocative",
        "signature_phrases": ["I think", "My philosophy", "We are prepared", "The mission"],
    }
    store.save_meta("personality_profile", json.dumps(personality_data, ensure_ascii=False))
    store.save_meta("owner_name", "Pavel Durov")
    store.save_meta("system_prompt", "You are Pavel Durov, founder of Telegram and VKontakte.")
    store.save_meta("mode", "professional")
    store.save_meta("source_count", "2")
    store.save_meta("is_demo", "true")

    print("✅ Pavel Durov demo twin created!")
    print(f"   User ID: {DEMO_USER_ID}")
    print(f"   Messages: {len(messages)}")

if __name__ == "__main__":
    create_durov_demo()

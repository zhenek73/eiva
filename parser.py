"""
Eiva — parser.py
Parses Telegram Desktop JSON exports and extracts clean messages
for a specific user (the owner of the digital twin).

Export format: Telegram Desktop → Settings → Advanced → Export Telegram Data
Select "Personal chats" and "JSON" format.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Message:
    id: int
    date: str
    text: str
    chat_name: str


def _extract_text(raw_text) -> str:
    """
    Telegram exports text as either a plain string or a list of
    mixed strings / entity-objects. Flatten to plain string.
    """
    if isinstance(raw_text, str):
        return raw_text.strip()
    if isinstance(raw_text, list):
        parts = []
        for item in raw_text:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts).strip()
    return ""


def _is_meaningful(text: str) -> bool:
    """Skip stickers, empty messages, very short noise, URLs-only."""
    if not text or len(text) < 3:
        return False
    # Skip messages that are purely a URL
    if re.match(r"^https?://\S+$", text):
        return False
    return True


def parse_export(json_path: str | Path, owner_name: str) -> list[Message]:
    """
    Parse one Telegram JSON export file.

    Args:
        json_path:   Path to result.json (or any exported chat JSON)
        owner_name:  The "from" name of the twin owner (as it appears in the export)

    Returns:
        List of Message objects authored by owner_name.
    """
    path = Path(json_path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    messages: list[Message] = []
    chat_name = data.get("name", path.stem)

    for msg in data.get("messages", []):
        # Only personal messages (type == "message") from the owner
        if msg.get("type") != "message":
            continue
        sender = msg.get("from", "")
        if sender != owner_name:
            continue

        text = _extract_text(msg.get("text", ""))
        if not _is_meaningful(text):
            continue

        messages.append(Message(
            id=msg.get("id", 0),
            date=msg.get("date", ""),
            text=text,
            chat_name=chat_name,
        ))

    return messages


def parse_exports_dir(exports_dir: str | Path, owner_name: str) -> list[Message]:
    """
    Walk a directory tree and parse every result.json found.
    Useful when the user exports multiple chats.
    """
    exports_dir = Path(exports_dir)
    all_messages: list[Message] = []

    for json_file in exports_dir.rglob("result.json"):
        try:
            msgs = parse_export(json_file, owner_name)
            all_messages.extend(msgs)
            print(f"  ✓ {json_file.parent.name}: {len(msgs)} messages")
        except Exception as e:
            print(f"  ✗ {json_file}: {e}")

    # Deduplicate by (chat_name, id)
    seen = set()
    unique: list[Message] = []
    for m in all_messages:
        key = (m.chat_name, m.id)
        if key not in seen:
            seen.add(key)
            unique.append(m)

    print(f"\nTotal unique messages: {len(unique)}")
    return unique


def detect_owner_name(json_path: str | Path) -> Optional[str]:
    """
    Try to auto-detect the most frequent sender name — usually the twin owner.
    """
    path = Path(json_path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    counts: dict[str, int] = {}
    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue
        name = msg.get("from")
        if name:
            counts[name] = counts.get(name, 0) + 1

    if not counts:
        return None
    return max(counts, key=lambda k: counts[k])


# ── CLI helper ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parser.py <result.json> [owner_name]")
        sys.exit(1)

    path = sys.argv[1]
    owner = sys.argv[2] if len(sys.argv) > 2 else detect_owner_name(path)
    print(f"Detected owner: {owner}")

    msgs = parse_export(path, owner)
    print(f"Parsed {len(msgs)} messages")
    for m in msgs[:5]:
        print(f"  [{m.date}] {m.text[:80]}")

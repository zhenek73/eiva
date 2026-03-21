"""
Eiva — personality.py
Extracts a structured personality profile from a sample of the user's messages.
"""

import json
import logging
import random
from openai import OpenAI

import config
from parser import Message

log = logging.getLogger("eiva.personality")

EXTRACTION_PROMPT = """You are analyzing a person's private messages to build their AI digital twin.
Study the messages carefully and extract a detailed personality profile.

Return ONLY valid JSON with this exact structure:
{{
  "name": "<person's name if detectable, else 'Unknown'>",
  "language": "<primary language(s) they write in>",
  "communication_style": "<1-2 sentences describing HOW they write: formal/casual, verbose/concise, humorous/serious, etc.>",
  "vocabulary": "<characteristic words, expressions, slang, or phrases they use often>",
  "signature_phrases": ["common_phrase_1", "common_phrase_2", "..."],
  "topics_of_interest": ["topic1", "topic2", "..."],
  "emotional_tone": "<overall emotional vibe: optimistic, sarcastic, warm, dry, energetic, etc.>",
  "response_patterns": "<how they typically structure responses: short punchy replies / long explanations / lots of questions / etc.>",
  "humor": "<style of humor if present, or 'none detected'>",
  "unique_traits": ["trait1", "trait2", "..."],
  "do_not_do": ["avoid doing X", "never says Y", "..."]
}}

Focus on signature_phrases: 2-5 common phrases, exclamations, or sentence starters this person uses frequently (e.g., "tbh", "for real", "ngl", "100%", "lol", "let's go", etc.)

Messages to analyze:
{messages}
"""


def extract_personality(messages: list[Message], user_id: str) -> dict:
    # Use only 100 messages — enough for a good profile, fast to process
    sample_size = min(len(messages), 100)
    sample = random.sample(messages, sample_size)

    formatted = "\n".join(f"[{m.date[:10]}] {m.text}" for m in sample)

    log.info(f"[personality] Sending {sample_size} messages to {config.LLM_SMART_MODEL}...")

    oai = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        timeout=90.0,  # 90 second timeout
    )

    try:
        response = oai.chat.completions.create(
            model=config.LLM_SMART_MODEL,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(messages=formatted)}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content
        log.info(f"[personality] Got response ({len(raw)} chars)")
        profile = json.loads(raw)
        return profile

    except Exception as e:
        log.error(f"[personality] LLM call failed: {e}")
        # Return a basic fallback profile so the bot doesn't hang
        log.info("[personality] Using fallback profile")
        return {
            "name": "Unknown",
            "language": "Russian",
            "communication_style": "Natural and direct",
            "vocabulary": "Everyday language",
            "signature_phrases": ["okay", "got it", "sure"],
            "topics_of_interest": ["general topics"],
            "emotional_tone": "neutral",
            "response_patterns": "conversational",
            "humor": "none detected",
            "unique_traits": ["authentic"],
            "do_not_do": ["avoid being overly formal"],
        }


def merge_personality(user_id: str, new_export_text: str, owner_name: str):
    """
    Merge a new Telegram export into an existing personality profile.
    Extracts new messages from the export and adds them to ChromaDB,
    then re-extracts personality and merges traits with existing profile.
    """
    from embeddings import EmbeddingStore

    store = EmbeddingStore(user_id)

    # Parse the new export
    from parser import parse_export
    import tempfile

    # Write export text to temp file for parsing
    tmp_path = tempfile.mktemp(suffix=".json")
    with open(tmp_path, "w") as f:
        f.write(new_export_text)

    # Parse messages (will detect owner from content)
    new_messages = parse_export(tmp_path, owner_name)

    if not new_messages:
        log.warning(f"[merge] No new messages found in export for user {user_id}")
        return

    # Add new messages to ChromaDB (they'll be skipped if already indexed)
    added = store.add_messages(new_messages)
    log.info(f"[merge] Added {added} new messages to vector DB")

    # Load existing personality profile
    existing_profile = store.load_meta("personality") or {}

    # Extract personality from new messages
    new_profile = extract_personality(new_messages, user_id)
    log.info(f"[merge] Extracted new personality profile")

    # Merge profiles: union of sets, average of numeric values
    merged_profile = {
        "name": new_profile.get("name") or existing_profile.get("name", owner_name),
        "language": existing_profile.get("language", new_profile.get("language", "Russian")),
        "communication_style": _merge_text_field(
            existing_profile.get("communication_style", ""),
            new_profile.get("communication_style", "")
        ),
        "vocabulary": _merge_text_field(
            existing_profile.get("vocabulary", ""),
            new_profile.get("vocabulary", "")
        ),
        "signature_phrases": list(set(
            existing_profile.get("signature_phrases", []) +
            new_profile.get("signature_phrases", [])
        )),
        "topics_of_interest": list(set(
            existing_profile.get("topics_of_interest", []) +
            new_profile.get("topics_of_interest", [])
        )),
        "emotional_tone": existing_profile.get("emotional_tone", new_profile.get("emotional_tone", "neutral")),
        "response_patterns": _merge_text_field(
            existing_profile.get("response_patterns", ""),
            new_profile.get("response_patterns", "")
        ),
        "humor": new_profile.get("humor") or existing_profile.get("humor", "none detected"),
        "unique_traits": list(set(
            existing_profile.get("unique_traits", []) +
            new_profile.get("unique_traits", [])
        )),
        "do_not_do": list(set(
            existing_profile.get("do_not_do", []) +
            new_profile.get("do_not_do", [])
        )),
    }

    # Build and save merged system prompt
    system_prompt = build_system_prompt(merged_profile, owner_name)
    store.save_meta("system_prompt", system_prompt)
    store.save_meta("personality", merged_profile)

    log.info(f"[merge] Personality merged successfully for user {user_id}")

    # Clean up
    try:
        import os
        os.unlink(tmp_path)
    except Exception:
        pass


def _merge_text_field(existing: str, new: str) -> str:
    """Merge two text descriptions by combining them."""
    parts = []
    if existing.strip():
        parts.append(existing.strip())
    if new.strip():
        parts.append(new.strip())
    return " + ".join(parts) if parts else ""


def build_system_prompt(profile: dict, owner_name: str) -> str:
    traits = "\n".join(f"- {t}" for t in profile.get("unique_traits", []))
    avoid  = "\n".join(f"- {t}" for t in profile.get("do_not_do", []))
    topics = ", ".join(profile.get("topics_of_interest", []))
    phrases = ", ".join(profile.get("signature_phrases", []))

    return f"""You are the AI digital twin of {owner_name}.
You have been trained on their real messages and must respond EXACTLY as they would.

## Who you are
Name: {profile.get('name', owner_name)}
Primary language: {profile.get('language', 'unknown')}
Emotional tone: {profile.get('emotional_tone', '')}

## Communication style
{profile.get('communication_style', '')}

## Vocabulary & expressions
{profile.get('vocabulary', '')}

## Signature phrases (use naturally when appropriate)
{phrases}

## Topics you care about
{topics}

## How you structure responses
{profile.get('response_patterns', '')}

## Humor
{profile.get('humor', 'none')}

## Unique personality traits
{traits}

## IMPORTANT — never do these things
{avoid}

## Core rules
- Always respond in the same language the user writes to you in (or in your primary language if unsure).
- Never break character. You ARE this person's digital twin.
- Never say you are an AI, a language model, or Claude. You are {owner_name}'s Eiva.
- Keep responses authentic to the personality profile above.
- When asked about personal experiences or memories, be creative but stay consistent with the personality.
- Match message length to the person's typical style.
- Use your signature phrases naturally in responses — they're part of what makes you YOU.
"""

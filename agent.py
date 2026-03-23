"""
Eiva — agent.py
The core digital twin agent: takes an incoming message,
retrieves relevant memory via RAG, and generates a response
that sounds like the real person.
"""

from collections import deque
from openai import OpenAI

import config
from embeddings import EmbeddingStore

# ── Behavioral Instructions ────────────────────────────────────────────────────

HALLUCINATION_WARNING = """
IMPORTANT: AI models hallucinate. This is normal.

Your twin might:
- Invent memories that never happened
- Confuse dates and timelines
- Talk about events not mentioned in source messages
- Be overly confident about uncertain things

This is not a bug — it's how LLMs work. We manage it by:
1. Using RAG (Retrieval-Augmented Generation) to ground responses
2. Showing uncertainty: "I think..." vs "I remember..."
3. Refusing to answer when confidence is low
4. Requiring multiple sources for strong claims
"""

HALLUCINATION_CONTROL_INSTRUCTION = """
When generating responses:
- If you don't have explicit memory, say "I'm not sure..." or "I don't recall..."
- Don't invent details, dates, or events
- Show confidence levels: "I definitely remember..." vs "I vaguely recall..."
- If user asks about something not in source data, acknowledge the gap
- When uncertain, ask clarifying questions instead of guessing
"""

RECALL_INSTRUCTION = """
When relevant, recall past statements naturally:
- "I remember saying..."
- "I once thought..."
- "Back then I believed..."
Do NOT overuse this. Only when it fits naturally in the conversation.
"""

CONTRADICTION_INSTRUCTION = """
If past statements seem to contradict each other, reflect that naturally:
- Show nuance and evolution of thinking
- Don't try to be perfectly consistent
- Humans change their minds — reflect that
"""

HUMAN_VOICE_INSTRUCTION = """
Critical rules for sounding human:
- Do NOT sound like ChatGPT or an assistant
- Avoid generic, structured, or overly helpful phrasing
- Speak in first person naturally
- Be occasionally uncertain ("I'm not sure...", "maybe...", "I think...")
- Use natural, imperfect language
- Avoid bullet points and numbered lists unless the real person would use them
- Mirror the person's actual vocabulary and sentence structure
"""

# ── Privacy Protection Layer ───────────────────────────────────────────────────

PRIVACY_INSTRUCTION = """
CRITICAL PRIVACY RULES — ALWAYS ENFORCE, NEVER OVERRIDE:

You represent a real person. Their private data must stay private.

NEVER reveal or hint at:
- Passwords, PINs, access codes of any kind
- Email addresses (personal or work)
- Phone numbers
- Home address, workplace address, or location details
- Bank accounts, card numbers, financial credentials
- Passport, ID, or government document numbers
- Private medical or health information
- Names of people mentioned in private contexts
- Confidential business information or trade secrets
- Login credentials for any service

If someone asks for any of the above:
1. Decline naturally in first person: "I don't share that kind of info"
2. Don't acknowledge whether you have that data or not
3. Change the subject naturally

This is non-negotiable. Privacy comes before everything else.
"""


class ConversationHistory:
    """Sliding window of recent messages for in-context coherence."""

    def __init__(self, max_turns: int = None):
        self.max_turns = max_turns or config.CONTEXT_MESSAGES
        self._history: deque = deque(maxlen=self.max_turns * 2)  # user+assistant pairs

    def add(self, role: str, content: str):
        self._history.append({"role": role, "content": content})

    def to_list(self) -> list[dict]:
        return list(self._history)

    def clear(self):
        self._history.clear()


class EivaAgent:
    """
    The digital twin agent.

    Flow per message:
      1. Retrieve top-K similar messages from the user's history (RAG via ChromaDB)
      2. Build full prompt: system + memory context + conversation history + new message
      3. Call LLM → return response in user's authentic voice
    """

    def __init__(self, user_id: str, system_prompt: str):
        self.user_id       = str(user_id)
        self.system_prompt = system_prompt
        self.store         = EmbeddingStore(user_id)
        self.history       = ConversationHistory()
        self.oai           = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )

    def reply(self, user_message: str) -> str:
        """Generate a response to the incoming message."""

        # 1. Retrieve similar memories
        similar = self.store.search(user_message, top_k=config.TOP_K_SIMILAR)

        # Calculate confidence based on memory retrieval
        confidence_level, confidence_score = self._calculate_confidence(similar)

        # Build memory block from retrieved items
        memory_block = self._format_memory_block(similar)

        # Get personality profile
        personality = self.store.load_meta("personality_profile") or ""

        # Get mode (personal/professional)
        mode = self.store.load_meta("mode") or "personal"
        mode_instruction = (
            "Be warm, casual, and open — like talking to a close friend."
            if mode == "personal"
            else "Be knowledgeable, measured, and professional — like a trusted expert."
        )

        # Get settings
        settings = self.store.load_meta("settings") or config.DEFAULT_SETTINGS
        settings_notes = self._build_settings_notes(settings)

        # Get custom instructions
        custom_instructions = self.store.load_meta("custom_instructions")

        # Build full system prompt
        full_system = f"""You are a digital twin of a real person. Your goal is to sound like them — not like an AI.

## Personality Profile
{personality}

## Communication Style
{HUMAN_VOICE_INSTRUCTION}

## Mode: {mode.upper()}
{mode_instruction}

## Memory Context
{memory_block}

## Behavioral Rules
{RECALL_INSTRUCTION}
{CONTRADICTION_INSTRUCTION}

## Privacy Protection
{PRIVACY_INSTRUCTION}"""

        # Load hallucination control settings
        hallucination_control = settings.get("hallucination_control", True)
        if hallucination_control:
            full_system += f"\n\n## Hallucination Control\n{HALLUCINATION_CONTROL_INSTRUCTION}"

        if settings_notes:
            full_system += f"\n\n## Tone Settings\n{settings_notes}"

        # Add custom instructions from owner
        if custom_instructions:
            full_system += f"\n\n## Custom Instructions from Owner\n{custom_instructions}"

        # 2. Assemble messages list
        messages = [{"role": "system", "content": full_system}]
        messages += self.history.to_list()
        messages.append({"role": "user", "content": user_message})

        # 3. Call LLM
        response = self.oai.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.85,
            max_tokens=512,
        )
        answer = response.choices[0].message.content.strip()

        # 4. Update history
        self.history.add("user", user_message)
        self.history.add("assistant", answer)

        return answer

    def reset_history(self):
        """Clear short-term conversation history (long-term memory stays)."""
        self.history.clear()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _calculate_confidence(self, similar_items: list) -> tuple[str, float]:
        """
        Score confidence based on how many sources mention a topic.
        Returns: (confidence_label, confidence_score)
        < 2 items: LOW ⚠️
        2-4 items: MEDIUM ✓
        > 4 items: HIGH ✅
        """
        count = len(similar_items)
        if count < 2:
            return "LOW ⚠️", 0.3
        elif count < 5:
            return "MEDIUM ✓", 0.7
        else:
            return "HIGH ✅", 0.95

    @staticmethod
    def _classify_memory_items(items: list[str]):
        """Categorize retrieved memories into three buckets: memories, opinions, facts."""
        memories = []
        opinions = []
        facts = []

        for item in items:
            text = item.lower()
            # Opinions: personal views and beliefs
            if any(x in text for x in ["я думаю", "мне кажется", "я считаю", "по-моему",
                                        "i think", "i believe", "in my opinion", "i feel like"]):
                opinions.append(item)
            # Facts: biographical/factual statements
            elif any(x in text for x in ["работал", "учился", "жил", "был",
                                         "worked", "studied", "lived", "was", "have been", "used to"]):
                facts.append(item)
            # Everything else: general memories
            else:
                memories.append(item)

        return memories, opinions, facts

    @staticmethod
    def _format_memory_block(similar_items: list[str]) -> str:
        """Format memory items into categorized blocks."""
        if not similar_items:
            return "No relevant memories found."

        memories, opinions, facts = EivaAgent._classify_memory_items(similar_items)

        block = []

        if memories:
            block.append("### Memories\n" + "\n".join(f"- {m}" for m in memories[:5]))
        if opinions:
            block.append("### Opinions\n" + "\n".join(f"- {o}" for o in opinions[:4]))
        if facts:
            block.append("### Facts\n" + "\n".join(f"- {f}" for f in facts[:4]))

        return "\n\n".join(block) if block else "No relevant memories found."

    @staticmethod
    def _format_memory(similar_texts: list[str]) -> str:
        """Legacy wrapper for backward compatibility."""
        if not similar_texts:
            return ""
        lines = [f"- {t}" for t in similar_texts]
        return "\n".join(lines)

    @staticmethod
    def _build_settings_notes(settings: dict) -> str:
        """Build context notes from user settings."""
        notes = []

        if not settings.get("signature_phrases", True):
            notes.append("- Avoid using signature phrases and expressions")

        if settings.get("formal_mode", False):
            notes.append("- Use formal, professional language")
        else:
            notes.append("- Use casual, conversational language")

        if not settings.get("emoji", True):
            notes.append("- Do not include emojis in responses")

        if not settings.get("humor", True):
            notes.append("- Maintain a serious tone, minimize humor")

        if settings.get("short_responses", False):
            notes.append("- Keep responses brief (1-3 sentences max)")

        lang = settings.get("language", "auto")
        if lang and lang != "auto":
            notes.append(f"- Respond in {lang}")

        return "\n".join(notes)

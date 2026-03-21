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
        memory_block = self._format_memory(similar)

        # 2. Build system message with injected memory
        system_with_memory = self.system_prompt
        if memory_block:
            system_with_memory += f"\n\n## Relevant things you said before\n{memory_block}"

        # 3. Assemble messages list
        messages = [{"role": "system", "content": system_with_memory}]
        messages += self.history.to_list()
        messages.append({"role": "user", "content": user_message})

        # 4. Call LLM
        response = self.oai.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.85,
            max_tokens=512,
        )
        answer = response.choices[0].message.content.strip()

        # 5. Update history
        self.history.add("user", user_message)
        self.history.add("assistant", answer)

        return answer

    def reset_history(self):
        """Clear short-term conversation history (long-term memory stays)."""
        self.history.clear()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _format_memory(similar_texts: list[str]) -> str:
        if not similar_texts:
            return ""
        lines = [f"- {t}" for t in similar_texts]
        return "\n".join(lines)

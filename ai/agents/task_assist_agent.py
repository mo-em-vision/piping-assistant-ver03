"""Conversational Q&A for an active engineering task — no workflow navigation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai.agents.base import BaseAgent
from ai.agents.source_utils import normalize_chat_sources
from ai.client import MissingAPIKeyError


@dataclass
class TaskAssistReply:
    reply: str
    sources: list[dict[str, Any]] = field(default_factory=list)


class TaskAssistAgent(BaseAgent):
    prompt_file = "task_assist.md"

    def reply(
        self,
        user_message: str,
        *,
        history: list[dict[str, str]] | None = None,
        context_brief: str = "",
        standards_context: str = "",
        retrieval_sources: list[dict[str, Any]] | None = None,
    ) -> TaskAssistReply:
        try:
            _ = self.client
        except MissingAPIKeyError:
            return TaskAssistReply(
                reply=(
                    "AI assistance requires an OpenAI API key. "
                    "Configure OPENAI_API_KEY to ask follow-up questions in the chat tab."
                ),
            )

        messages = list(history or [])
        messages.append({"role": "user", "content": user_message.strip()})

        extra_parts: list[str] = []
        if context_brief.strip():
            extra_parts.append(f"## Task context\n{context_brief.strip()}")
        if standards_context.strip():
            extra_parts.append(
                "## Retrieved standards sources\n"
                f"{standards_context.strip()}\n\n"
                "Rules:\n"
                "- Prefer retrieved sources over general knowledge when they answer the question.\n"
                "- Cite sources inline (e.g. ASME B31.3 §304.1.1, Table 304.1.1).\n"
                "- Do not invent table values not present in retrieved sources."
            )
        extra_system = "\n\n".join(extra_parts)

        payload = self.complete_json_messages(messages, extra_system=extra_system)
        reply = str(payload.get("reply", "")).strip()
        sources = normalize_chat_sources(payload.get("sources"), retrieval_sources or [])

        if reply:
            return TaskAssistReply(reply=reply, sources=sources)

        return TaskAssistReply(
            reply=(
                "I could not generate a response for that question. "
                "Try rephrasing or asking about a specific symbol, step, or output."
            ),
            sources=sources,
        )


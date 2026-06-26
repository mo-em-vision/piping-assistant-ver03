"""Educational explanations for highlighted workspace text — no workflow navigation."""



from __future__ import annotations



from dataclasses import dataclass, field

from typing import Any



from ai.agents.base import BaseAgent

from ai.agents.source_utils import normalize_chat_sources

from ai.client import MissingAPIKeyError





@dataclass

class SelectionExplainReply:

    explanation: str

    sources: list[dict[str, Any]] = field(default_factory=list)





class SelectionExplainAgent(BaseAgent):

    prompt_file = "selection_explanation.md"



    def explain(

        self,

        user_prompt: str,

        *,

        history: list[dict[str, str]] | None = None,

        context_brief: str = "",

        standards_context: str = "",

        retrieval_sources: list[dict[str, Any]] | None = None,

    ) -> SelectionExplainReply:

        try:

            _ = self.client

        except MissingAPIKeyError:

            return SelectionExplainReply(

                explanation=(

                    "AI explanations require an OpenAI API key. "

                    "Configure OPENAI_API_KEY to get definitions and examples for highlighted text."

                ),

            )



        messages = list(history or [])

        messages.append({"role": "user", "content": user_prompt.strip()})



        extra_parts: list[str] = []

        if context_brief.strip():

            extra_parts.append(f"## Task context\n{context_brief.strip()}")

        if standards_context.strip():

            extra_parts.append(

                "## Retrieved standards sources\n"

                f"{standards_context.strip()}\n\n"

                "Rules:\n"

                "- Prefer retrieved sources over general knowledge when they explain the selection.\n"

                "- Cite tables and nodes inline using markdown links "

                "(e.g. [Table 304.1.1](table:asme_b31.3_table_304_1_1)).\n"

                "- Do not invent table values not present in retrieved sources."

            )

        extra_system = "\n\n".join(extra_parts)



        payload = self.complete_json_messages(messages, extra_system=extra_system)

        explanation = str(payload.get("explanation", "")).strip()

        sources = normalize_chat_sources(payload.get("sources"), retrieval_sources or [])



        if explanation:

            return SelectionExplainReply(explanation=explanation, sources=sources)



        return SelectionExplainReply(

            explanation=(

                "I could not generate an explanation for the highlighted text. "

                "Try selecting a shorter phrase or ask again."

            ),

            sources=sources,

        )


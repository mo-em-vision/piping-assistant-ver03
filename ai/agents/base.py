"""Base agent utilities."""

from __future__ import annotations

import json
from typing import Any

from ai.client import LLMClient, OpenAIClient
from ai.prompts_loader import load_prompt


class BaseAgent:
    """Loads prompts and calls the configured LLM client."""

    prompt_file: str = ""

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            self._client = OpenAIClient.from_settings()
        return self._client

    def load_prompt(self) -> str:
        if not self.prompt_file:
            raise ValueError(f"{type(self).__name__} must define prompt_file")
        return load_prompt(self.prompt_file)

    def complete_json(self, user_prompt: str, *, extra_system: str = "") -> dict[str, Any]:
        system = self.load_prompt()
        if extra_system:
            system = f"{system}\n\n{extra_system}"
        return self.client.complete_json(system, user_prompt)

    def complete_json_messages(
        self,
        messages: list[dict[str, str]],
        *,
        extra_system: str = "",
    ) -> dict[str, Any]:
        system = self.load_prompt()
        if extra_system:
            system = f"{system}\n\n{extra_system}"
        return self.client.complete_json_messages(system, messages)

    @staticmethod
    def format_context(context: dict[str, Any] | None) -> str:
        if not context:
            return "{}"
        return json.dumps(context, indent=2, default=str)

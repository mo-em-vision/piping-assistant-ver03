"""OpenAI client wrapper for agent structured outputs."""

from __future__ import annotations

import json
from typing import Any, Protocol

from config.settings import Settings, settings
from engine.inspection.performance_trace import perf_span


class MissingAPIKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is not configured."""


class LLMClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        ...

    def complete_json_messages(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        ...


class OpenAIClient:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self.model = model

    @classmethod
    def from_settings(cls, cfg: Settings | None = None) -> OpenAIClient:
        cfg = cfg or settings
        if not cfg.openai_api_key:
            raise MissingAPIKeyError(
                "OPENAI_API_KEY is not set. Configure it in the environment or .env file."
            )
        return cls(
            cfg.openai_api_key,
            model=cfg.openai_model,
            base_url=cfg.openai_base_url,
        )

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        with perf_span("llm_completion", "llm", llm=True, notes="mode=complete_json"):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)

    def complete_json_messages(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        api_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in messages:
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            api_messages.append({"role": role, "content": content})
        with perf_span("llm_completion", "llm", llm=True, notes="mode=complete_json_messages"):
            response = self._client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)

"""Shared test helpers for agent behavioral tests."""

from __future__ import annotations

from typing import Any


class FakeLLMClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []
        self.message_calls: list[tuple[str, list[dict[str, str]]]] = []

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.calls.append((system_prompt, user_prompt))
        return self.response

    def complete_json_messages(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        self.message_calls.append((system_prompt, messages))
        return self.response

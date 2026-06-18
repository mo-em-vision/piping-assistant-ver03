"""Execution event logging."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models.event import Event, EventType


class EventLogger:
    """Record execution events for audit and report reconstruction."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def log(
        self,
        event_type: EventType,
        *,
        node: str | None = None,
        result: Any | None = None,
        decision: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            event=event_type,
            node=node,
            result=result,
            decision=decision,
            payload=payload or {},
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [asdict(event) for event in self._events]

    def clear(self) -> None:
        self._events.clear()

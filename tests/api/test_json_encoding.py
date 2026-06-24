"""Tests for API JSON encoding helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from api.json_encoding import dumps, json_safe


class _SampleStatus(str, Enum):
    ACTIVE = "active"


def test_json_safe_converts_datetime_and_enum() -> None:
    converted = json_safe(
        {
            "timestamp": datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc),
            "status": _SampleStatus.ACTIVE,
            "items": [{"created": datetime(2026, 1, 1, tzinfo=timezone.utc)}],
        }
    )

    assert converted["timestamp"] == "2026-06-25T12:00:00+00:00"
    assert converted["status"] == "active"
    assert converted["items"][0]["created"] == "2026-01-01T00:00:00+00:00"


def test_dumps_handles_nested_datetime() -> None:
    payload = dumps({"trace": [{"timestamp": datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)}]})
    assert '"timestamp": "2026-06-25T12:00:00+00:00"' in payload

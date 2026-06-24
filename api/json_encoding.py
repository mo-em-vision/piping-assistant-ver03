"""JSON helpers for desktop API responses."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def json_safe(value: Any) -> Any:
    """Recursively convert backend values into JSON-serializable data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return [json_safe(item) for item in value]
    return value


def json_default(value: Any) -> Any:
    """Fallback encoder for :func:`json.dumps` when values are not pre-sanitized."""
    converted = json_safe(value)
    if converted is value and not isinstance(value, (str, int, float, bool, type(None))):
        raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")
    return converted


def dumps(payload: Any, **kwargs: Any) -> str:
    return json.dumps(payload, default=json_default, **kwargs)

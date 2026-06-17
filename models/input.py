"""User and system input data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class InputSource(str, Enum):
    USER = "user"
    NODE = "node"
    TABLE = "table"
    DEFAULT = "default"
    SYSTEM = "system"


class InputStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DEFAULT_UNCONFIRMED = "default_unconfirmed"


@dataclass(frozen=True)
class InputLimits:
    min: float | None = None
    max: float | None = None


@dataclass
class EngineeringInput:
    input_id: str
    value: Any
    unit: str
    source: InputSource
    status: InputStatus = InputStatus.PENDING
    default: Any | None = None
    requires_confirmation: bool = False
    limits: InputLimits | None = None
    uncertainty: str | None = None
    original_value: Any | None = None
    original_unit: str | None = None

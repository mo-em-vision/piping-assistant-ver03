"""Rule validation data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ValidationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass(frozen=True)
class RuleValidation:
    rule: str
    condition: str
    result: ValidationResult

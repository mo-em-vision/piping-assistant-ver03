"""Calculation result and trace data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CalculationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class QuantityResult:
    symbol: str
    value: float
    unit: str


@dataclass
class CalculationStep:
    name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None


@dataclass
class CalculationResult:
    calculation_id: str
    inputs: dict[str, Any] = field(default_factory=dict)
    formula: dict[str, Any] = field(default_factory=dict)
    steps: list[CalculationStep] = field(default_factory=list)
    final_result: QuantityResult | None = None
    status: CalculationStatus | None = None

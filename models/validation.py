"""Validation Layer result data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComplianceStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNING = "PASS_WITH_WARNING"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationFinding:
    """Single validation check outcome."""

    rule: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    input_id: str | None = None
    node_id: str | None = None
    source: str | None = None
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ValidationOverride:
    """Recorded user override of an engineering rule."""

    rule: str
    user_decision: str
    reason: str | None = None
    approved: bool = True


@dataclass
class LayerValidationResult:
    """Aggregated validation outcome (doc 15 §22)."""

    status: ComplianceStatus
    errors: list[ValidationFinding] = field(default_factory=list)
    warnings: list[ValidationFinding] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    overrides: list[ValidationOverride] = field(default_factory=list)
    affected_nodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}

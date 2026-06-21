"""Standard knowledge node data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(str, Enum):
    CALCULATION = "calculation"
    LOOKUP = "lookup"
    REFERENCE = "reference"
    CONDITIONAL = "conditional"
    VALIDATION = "validation"


class OutputType(str, Enum):
    QUANTITY = "quantity"
    BOOLEAN = "boolean"
    TEXT = "text"
    TABLE = "table"
    OBJECT = "object"


class InputSourceType(str, Enum):
    USER = "user"
    NODE = "node"
    TABLE = "table"
    DEFAULT = "default"


@dataclass(frozen=True)
class NodeRequiredInput:
    symbol: str
    description: str
    unit: str
    source: InputSourceType


@dataclass(frozen=True)
class NodeProvidedOutput:
    symbol: str
    type: OutputType
    unit: str
    consumed_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class FormulaDefinition:
    formula_id: str
    name: str
    display: str
    steps: tuple[str, ...] = ()
    file: str | None = None
    execution_function: str | None = None


EquationDefinition = FormulaDefinition


@dataclass(frozen=True)
class StandardNode:
    id: str
    paragraph: str
    text: str
    formula: str | None = None
    notes: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    exceptions: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    dependency_types: tuple[DependencyType, ...] = ()
    requires: tuple[NodeRequiredInput, ...] = ()
    provides: tuple[NodeProvidedOutput, ...] = ()
    equations: tuple[EquationDefinition, ...] = ()
    formulas: tuple[FormulaDefinition, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

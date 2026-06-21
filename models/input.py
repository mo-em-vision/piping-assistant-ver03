"""User and system input data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    PROPOSED_DEFAULT = "proposed_default"
    USER_OVERRIDE = "user_override"
    DEFAULT_UNCONFIRMED = "proposed_default"  # backward-compatible alias


class ResolutionMethod(str, Enum):
    USER_INPUT = "user_input"
    TABLE_LOOKUP = "table_lookup"
    EQUATION = "equation"
    NODE_OUTPUT = "node_output"
    DEFAULT_CONFIRMED = "default_confirmed"
    SYSTEM = "system"


@dataclass(frozen=True)
class InputLimits:
    min: float | None = None
    max: float | None = None


@dataclass(frozen=True)
class ResolutionRef:
    """Provenance reference for how a parameter value was obtained."""

    table: str | None = None
    node_id: str | None = None
    equation_id: str | None = None
    subsection: str | None = None


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
    default_condition: str | None = None
    symbol: str | None = None
    description: str | None = None
    introduced_at_node: str | None = None
    resolved_at_node: str | None = None
    resolution_method: ResolutionMethod | None = None
    resolution_ref: ResolutionRef | None = None


@dataclass
class ParameterDescriptor:
    """Registry entry for a workflow parameter introduced at a definition node."""

    input_id: str
    symbol: str
    description: str
    introduced_at_node: str
    unit: str = "dimensionless"
    resolution_method: ResolutionMethod | None = None
    resolution_ref: ResolutionRef | None = None
    required_when_nodes: tuple[str, ...] = ()
    status: InputStatus = InputStatus.PENDING


def input_is_expansion_ready(inp: EngineeringInput) -> bool:
    """Return True when an input may satisfy graph expansion requirements."""
    return inp.status in {InputStatus.CONFIRMED, InputStatus.USER_OVERRIDE}


def proposed_default_input(
    input_id: str,
    value: Any,
    *,
    unit: str = "dimensionless",
    default: Any | None = None,
    default_condition: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    introduced_at_node: str | None = None,
    resolution_method: ResolutionMethod | None = None,
    resolution_ref: ResolutionRef | None = None,
) -> EngineeringInput:
    """Build a system-proposed default awaiting user confirmation."""
    return EngineeringInput(
        input_id=input_id,
        value=value,
        unit=unit,
        source=InputSource.DEFAULT,
        status=InputStatus.PROPOSED_DEFAULT,
        default=default if default is not None else value,
        requires_confirmation=True,
        default_condition=default_condition,
        symbol=symbol,
        description=description,
        introduced_at_node=introduced_at_node,
        resolution_method=resolution_method or ResolutionMethod.DEFAULT_CONFIRMED,
        resolution_ref=resolution_ref,
    )


def pending_parameter_input(
    descriptor: ParameterDescriptor,
) -> EngineeringInput:
    """Build a pending input placeholder from a parameter registry descriptor."""
    return EngineeringInput(
        input_id=descriptor.input_id,
        value=None,
        unit=descriptor.unit,
        source=InputSource.SYSTEM,
        status=InputStatus.PENDING,
        symbol=descriptor.symbol,
        description=descriptor.description,
        introduced_at_node=descriptor.introduced_at_node,
        resolution_method=descriptor.resolution_method,
        resolution_ref=descriptor.resolution_ref,
    )

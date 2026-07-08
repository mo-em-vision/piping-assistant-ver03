"""Thin API wrapper around engine equation display trace serialization."""

from __future__ import annotations

from engine.equation.display_trace_serializer import (
    enrich_equation_block,
    find_trace_for_equation,
    find_trace_in_execution_payload,
    trace_from_dict,
    trace_to_dict,
)

__all__ = [
    "enrich_equation_block",
    "find_trace_for_equation",
    "find_trace_in_execution_payload",
    "trace_from_dict",
    "trace_to_dict",
]

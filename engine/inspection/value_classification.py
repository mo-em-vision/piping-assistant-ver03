"""Classify task values for developer inspection projections (read-only)."""

from __future__ import annotations

from enum import Enum
from typing import Any

# Shared with api.serializers._OUTPUT_DEBUG_KEYS — planner blobs stored on task.outputs.
_PLANNER_DEBUG_OUTPUT_KEYS = frozenset(
    {
        "engineering_plan",
        "engineering_plan_view",
        "planner_inspector_summary",
        "graph_navigation",
    }
)

_TRACE_OUTPUT_KEYS = frozenset(
    {
        "_plan_edges",
        "_skipped_trace",
    }
)

_PLANNER_TRACE_OUTPUT_KEYS = frozenset(
    {
        "_planner_decisions",
    }
)

_CONTROL_OUTPUT_KEYS = frozenset(
    {
        "workflow",
        "selected_root",
        "graph_root",
        "graph_version",
        "_execution_trace",
        "_validation_trace",
        "_lifecycle_events",
        "_execution_events",
        "_replay_snapshot",
        "_inspection_breakpoint",
        "_provenance_warnings",
        "task_state_errors",
    }
)

INSPECTION_EXCLUDED_OUTPUT_KEYS = (
    _PLANNER_DEBUG_OUTPUT_KEYS
    | _TRACE_OUTPUT_KEYS
    | _PLANNER_TRACE_OUTPUT_KEYS
    | _CONTROL_OUTPUT_KEYS
)

_DERIVED_OUTPUT_FIELD_KEYS = frozenset(
    {
        "required_thickness",
        "required_wall_thickness",
        "minimum_required_thickness",
        "mawp",
        "allowable_stress",
        "calculation_report",
    }
)

_OUTPUT_SOURCES = frozenset(
    {
        "derived",
        "lookup",
        "equation",
        "calculation",
        "table_lookup",
    }
)


class InspectionValueDestination(str, Enum):
    MAIN_FACTS = "main_facts"
    OUTPUTS = "outputs"
    PLANNER_DEBUG = "planner_debug"
    TRACE = "trace"
    HIDE = "hide"


def is_inspection_excluded_output_key(field: str) -> bool:
    """True when a task.outputs key must not become a canonical engineering value."""
    if field in INSPECTION_EXCLUDED_OUTPUT_KEYS:
        return True
    if field.endswith("_lookup") or field.endswith("_unit"):
        return True
    return False


def has_approved_display_formatter(entry: dict[str, Any]) -> bool:
    """Scalar or pre-formatted display strings are safe for main inspector tables."""
    display = entry.get("display_value")
    if display is not None and not isinstance(display, (dict, list)):
        return True
    value = entry.get("value")
    return value is not None and not isinstance(value, (dict, list))


def classify_inspection_value(
    field: str,
    entry: dict[str, Any] | None = None,
    *,
    value: Any | None = None,
    source: str | None = None,
    parameter_node_id: str | None = None,
) -> InspectionValueDestination:
    """Route a value to the correct inspector surface."""
    if field in _TRACE_OUTPUT_KEYS:
        return InspectionValueDestination.TRACE
    if field in _PLANNER_TRACE_OUTPUT_KEYS or field in _PLANNER_DEBUG_OUTPUT_KEYS:
        return InspectionValueDestination.PLANNER_DEBUG
    if field in _CONTROL_OUTPUT_KEYS:
        return InspectionValueDestination.HIDE
    if field.startswith("_"):
        return InspectionValueDestination.PLANNER_DEBUG

    resolved_source = source
    resolved_value = value
    resolved_param_node = parameter_node_id
    if entry is not None:
        resolved_source = str(entry.get("source") or resolved_source or "")
        resolved_value = entry.get("value") if resolved_value is None else resolved_value
        resolved_param_node = entry.get("parameter_node_id") or resolved_param_node

    if entry is not None and not has_approved_display_formatter(entry):
        if resolved_param_node:
            # Structured fact payloads may still carry parameter_node_id; hide unless formatted.
            return InspectionValueDestination.HIDE
        return InspectionValueDestination.PLANNER_DEBUG

    if field in _DERIVED_OUTPUT_FIELD_KEYS:
        return InspectionValueDestination.OUTPUTS

    if resolved_source in _OUTPUT_SOURCES:
        if field in _DERIVED_OUTPUT_FIELD_KEYS or resolved_source in {
            "equation",
            "calculation",
        }:
            return InspectionValueDestination.OUTPUTS
        if resolved_source in {"lookup", "table_lookup"}:
            return InspectionValueDestination.MAIN_FACTS
        if isinstance(resolved_value, (dict, list)):
            return InspectionValueDestination.PLANNER_DEBUG
        return InspectionValueDestination.OUTPUTS

    if resolved_param_node or resolved_source in {
        "user_input",
        "default",
        "default_confirmed",
        "unknown",
        "",
    }:
        return InspectionValueDestination.MAIN_FACTS

    if isinstance(resolved_value, (dict, list)):
        return InspectionValueDestination.PLANNER_DEBUG

    return InspectionValueDestination.MAIN_FACTS


def inspection_main_fact_row(entry: dict[str, Any]) -> Any:
    """Pick the display-safe value for Facts / Inputs rows."""
    display = entry.get("display_value")
    if display is not None and not isinstance(display, (dict, list)):
        return display
    value = entry.get("value")
    if value is not None and not isinstance(value, (dict, list)):
        return value
    return None

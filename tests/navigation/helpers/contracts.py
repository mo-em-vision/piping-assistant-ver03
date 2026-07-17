"""Navigation ownership contract helpers — extract and compare layers only."""

from __future__ import annotations

from typing import Any

from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import build_canonical_task_state
from models.engineering_plan import EngineeringPlan, PlanRequirement
from models.fact import Fact
from models.task import Task

_LOOKUP_OUTPUT_METHODS = frozenset({"table_lookup", "catalog_lookup", "lookup"})
_DIRECT_INPUT_CLASSES = frozenset({"user_input", "branch_decision"})
_EXCLUDED_CLASSES = frozenset(
    {
        "equation_result",
        "derived_value",
        "report_output",
        "validation_check",
    }
)
_BLOCKED_STATUSES = frozenset({"blocked", "not_applicable", "resolved"})
_INACTIVE_ACTIVATION = frozenset({"conditional", "not_applicable"})


class LookupRoleAmbiguity(Exception):
    """Raised when a table_lookup requirement cannot be classified as key vs output."""


def format_set_diff(left: set[str], right: set[str], *, left_name: str, right_name: str) -> str:
    only_left = sorted(left - right)
    only_right = sorted(right - left)
    lines = [
        f"{left_name} only ({len(only_left)}): {only_left}",
        f"{right_name} only ({len(only_right)}): {only_right}",
    ]
    return "\n".join(lines)


def graph_active_direct_inputs(
    reader: StandardsReader,
    root_id: str,
    *,
    facts: dict[str, Fact],
) -> set[str]:
    graph = GraphTools(reader)
    return set(
        graph.required_user_inputs(
            root_id,
            existing_inputs=set(facts.keys()),
            task_inputs=facts,
        )
    )


def _is_lookup_output_requirement(req: PlanRequirement) -> bool:
    resolution = req.resolution or {}
    method = str(resolution.get("method") or "").strip()
    output_field = resolution.get("output_field")
    if output_field and str(output_field) == req.field:
        return True
    if method in _LOOKUP_OUTPUT_METHODS and resolution.get("role") == "lookup_output":
        return True
    if req.id.endswith("_lookup") and method in _LOOKUP_OUTPUT_METHODS:
        return True
    return False


def _is_lookup_key_requirement(req: PlanRequirement) -> bool | None:
    if req.requirement_class != "table_lookup":
        return None
    if _is_lookup_output_requirement(req):
        return False
    resolution = req.resolution or {}
    method = str(resolution.get("method") or "").strip()
    if method in {"", "user_input"}:
        return True
    if method in _LOOKUP_OUTPUT_METHODS:
        keys = resolution.get("keys")
        if isinstance(keys, list) and req.field in {str(item) for item in keys}:
            return True
        if req.field in str(resolution.get("anchor") or ""):
            return True
        return None
    return None


def is_planner_direct_input_requirement(req: PlanRequirement) -> str | None:
    """Classify an existing planner requirement as a direct input field, if applicable."""
    if req.requirement_class in _EXCLUDED_CLASSES:
        return None
    if req.activation_status in _INACTIVE_ACTIVATION:
        return None
    if req.status in _BLOCKED_STATUSES:
        return None
    if req.requirement_class in _DIRECT_INPUT_CLASSES:
        return req.field
    if req.requirement_class == "table_lookup":
        role = _is_lookup_key_requirement(req)
        if role is None:
            raise LookupRoleAmbiguity(req.id)
        return req.field if role else None
    return None


def planner_active_direct_inputs(plan: EngineeringPlan) -> set[str]:
    """Active gatherable direct inputs (phase-blocked fields remain gatherable)."""
    fields: set[str] = set()
    for req in plan.requirements.values():
        field = is_planner_direct_input_requirement(req)
        if field:
            fields.add(field)
    return fields


def planner_gate_and_path_fields(plan: EngineeringPlan) -> set[str]:
    """Expansion-gate and path-decision fields from an engineering plan."""
    gate_phases = frozenset({"expansion_assumptions", "path_decisions"})
    fields: set[str] = set()
    for req in plan.requirements.values():
        if req.phase not in gate_phases:
            continue
        field = is_planner_direct_input_requirement(req)
        if field:
            fields.add(field)
    return fields


def assert_graph_planner_gatherable_parity(
    reader: StandardsReader,
    root_id: str,
    *,
    facts: dict[str, Fact],
    plan: EngineeringPlan,
    expansion_open: bool = True,
) -> None:
    """Assert Graph required inputs match Planner gatherable direct inputs."""
    graph_fields = graph_active_direct_inputs(reader, root_id, facts=facts)
    try:
        planner_fields = planner_active_direct_inputs(plan)
    except LookupRoleAmbiguity as exc:
        raise AssertionError(f"lookup role ambiguity: {exc}") from exc

    if expansion_open:
        assert graph_fields == planner_fields, format_set_diff(
            graph_fields,
            planner_fields,
            left_name="graph",
            right_name="planner",
        )
        return

    gate_fields = planner_gate_and_path_fields(plan)
    assert graph_fields <= planner_fields
    assert planner_fields <= graph_fields | gate_fields, format_set_diff(
        graph_fields | gate_fields,
        planner_fields,
        left_name="graph+gate",
        right_name="planner",
    )


def planner_next_field(plan: EngineeringPlan) -> str | None:
    strategy = plan.input_strategy
    if strategy is None or not strategy.next_fields:
        return None
    return strategy.next_fields[0]


def planner_submittable_projection(plan: EngineeringPlan) -> list[str] | None:
    strategy = plan.input_strategy
    if strategy is None or strategy.submittable_fields is None:
        return None
    return list(strategy.submittable_fields)


def api_current_ask_parameter(
    task: Task,
    manager: TaskStateManager,
    *,
    reader: StandardsReader,
    planning: dict[str, Any] | None = None,
) -> str | None:
    resolved_planning = planning if planning is not None else planning_projection(task)
    canonical = build_canonical_task_state(task, manager, planning=resolved_planning, reader=reader)
    blocker = (canonical.get("execution") or {}).get("current_blocker") or {}
    field = blocker.get("field")
    if isinstance(field, str) and field.strip():
        return field
    progress = canonical.get("progress") or {}
    submittable = progress.get("submittable_parameters") or []
    if submittable:
        return str(submittable[0])
    return None


def api_submittable_projection(
    task: Task,
    manager: TaskStateManager,
    *,
    reader: StandardsReader,
    planning: dict[str, Any] | None = None,
) -> list[str]:
    resolved_planning = planning if planning is not None else planning_projection(task)
    canonical = build_canonical_task_state(task, manager, planning=resolved_planning, reader=reader)
    progress = canonical.get("progress") or {}
    return list(progress.get("submittable_parameters") or [])


def navigation_projection(
    task: Task,
    manager: TaskStateManager,
    reader: StandardsReader,
    *,
    root_id: str,
    facts: dict[str, Fact],
    plan: EngineeringPlan,
) -> dict[str, Any]:
    return {
        "graph_active_direct_inputs": sorted(graph_active_direct_inputs(reader, root_id, facts=facts)),
        "planner_next_field": planner_next_field(plan),
        "planner_submittable": planner_submittable_projection(plan),
        "api_current_ask": api_current_ask_parameter(task, manager, reader=reader),
        "api_submittable": api_submittable_projection(task, manager, reader=reader),
    }

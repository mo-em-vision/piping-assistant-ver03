"""Invariant checks for normalized engineering plan output."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.planner.pipe_wall_plan import req_id as requirement_id
from models.engineering_plan import EngineeringPlan

_MAX_GOAL_TITLE_LENGTH = 80
_MUTUALLY_EXCLUSIVE_DIAMETER_REQS = frozenset(
    {f"REQ-{key}" for key in ("outside_diameter", "nominal_pipe_size")}
)

_LOOKUP_INPUT_SOURCE_CLASSES = frozenset({"user_input", "derived_value"})


def _alternative_ids(requirements: dict) -> set[str]:
    alt_ids: set[str] = set()
    for req in requirements.values():
        for alt in req.alternatives or []:
            alt_ids.add(alt.id)
    return alt_ids


def _validate_dependency_edge(
    edge,
    *,
    requirements: dict,
    known_requirement_ids: set[str],
    alternative_ids: set[str],
    result: PlannerValidationResult,
) -> None:
    if edge.type == "activates":
        if edge.from_id not in alternative_ids:
            result.errors.append(
                f"activates edge source must be an alternative id: {edge.from_id}"
            )
            result.valid = False
        if edge.to_id not in known_requirement_ids:
            result.errors.append(f"activates edge target unknown requirement: {edge.to_id}")
            result.valid = False
        return

    if edge.from_id not in known_requirement_ids:
        result.errors.append(f"Dependency from unknown id: {edge.from_id}")
        result.valid = False
    if edge.to_id not in known_requirement_ids:
        result.errors.append(f"Dependency to unknown id: {edge.to_id}")
        result.valid = False

    if edge.type != "lookup_input":
        return

    if (
        edge.from_id == "REQ-diameter_resolution"
        and edge.to_id == "REQ-outside_diameter_lookup"
    ):
        result.errors.append(
            "REQ-diameter_resolution must not be a lookup_input source for outside diameter lookup."
        )
        result.valid = False

    source = requirements.get(edge.from_id)
    target = requirements.get(edge.to_id)
    if source is None or target is None:
        return

    if source.requirement_class not in _LOOKUP_INPUT_SOURCE_CLASSES:
        chained_lookup = (
            source.requirement_class == "table_lookup"
            and target.requirement_class == "table_lookup"
        )
        if not chained_lookup:
            result.errors.append(
                f"lookup_input source {edge.from_id} must be user_input or derived_value, "
                f"got {source.requirement_class!r}."
            )
            result.valid = False
    if target.requirement_class != "table_lookup":
        result.errors.append(
            f"lookup_input target {edge.to_id} must be table_lookup, got {target.requirement_class!r}."
        )
        result.valid = False


@dataclass
class PlannerValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _is_long_prompt_title(title: str) -> bool:
    text = str(title or "").strip()
    if len(text) > _MAX_GOAL_TITLE_LENGTH:
        return True
    lowered = text.lower()
    return lowered.startswith("to continue") or lowered.startswith("please provide")


def validate_engineering_plan(plan: EngineeringPlan) -> PlannerValidationResult:
    result = PlannerValidationResult()
    requirements = plan.requirements
    root = plan.root_goal
    known_ids = {root.id, *requirements.keys()}

    if not root.target_parameter:
        result.errors.append("Root calculation goal must have exactly one target parameter.")
        result.valid = False

    if _is_long_prompt_title(root.title):
        result.errors.append("Goal titles must not contain long user-facing prompt sentences.")
        result.valid = False

    for requirement_key, req in requirements.items():
        if req.question_spec:
            spec = req.question_spec
            missing = [
                name
                for name, value in (
                    ("field", spec.field),
                    ("label", spec.label),
                    ("expected_value_class", spec.expected_value_class),
                    ("priority", spec.priority),
                    ("ask_policy", spec.ask_policy),
                )
                if value is None or value == ""
            ]
            if missing:
                result.errors.append(
                    f"Requirement {requirement_key} question_spec missing: {', '.join(missing)}"
                )
                result.valid = False

    diameter_top_level = _MUTUALLY_EXCLUSIVE_DIAMETER_REQS.intersection(
        set(root.blocked_by)
    )
    if len(diameter_top_level) > 1:
        result.errors.append(
            "Root goal must not be blocked by both outside_diameter and nominal_pipe_size."
        )
        result.valid = False

    if (
        requirement_id("nominal_pipe_size") in requirements
        and "REQ-outside_diameter_lookup" in requirements
    ):
        lookup = requirements["REQ-outside_diameter_lookup"]
        if lookup.requirement_class != "table_lookup":
            result.errors.append("Outside diameter from NPS must use a table_lookup requirement.")
            result.valid = False

    for blocked_id in root.blocked_by:
        if blocked_id not in known_ids:
            result.errors.append(f"blocked_by references unknown requirement: {blocked_id}")
            result.valid = False

    for provisional_id in root.provisional_blocked_by:
        if provisional_id not in known_ids:
            result.errors.append(
                f"provisional_blocked_by references unknown requirement: {provisional_id}"
            )
            result.valid = False

    alternative_ids = _alternative_ids(requirements)
    for edge in plan.dependencies:
        _validate_dependency_edge(
            edge,
            requirements=requirements,
            known_requirement_ids=set(requirements.keys()),
            alternative_ids=alternative_ids,
            result=result,
        )

    if len(requirements) > 3 and not plan.dependencies:
        result.warnings.append("Dependency edges are empty despite existing requirements.")

    if "REQ-corrosion_allowance" not in requirements:
        result.errors.append(
            "Corrosion allowance must be present as a requirement for minimum required thickness."
        )
        result.valid = False

    user_input_coefficients = [
        rid
        for rid, req in requirements.items()
        if req.field
        in {
            "allowable_stress",
            "weld_joint_efficiency",
            "temperature_coefficient_Y",
            "weld_strength_reduction_factor_W",
        }
        and req.requirement_class == "user_input"
    ]
    if user_input_coefficients:
        result.warnings.append(
            "Coefficients should be lookup/derived requirements, not user_input: "
            + ", ".join(user_input_coefficients)
        )

    strategy = plan.input_strategy
    if strategy and strategy.mode == "single_next_question":
        if len(strategy.next_fields) > 1:
            result.errors.append(
                "input_strategy.next_fields must contain at most one field in single_next_question mode."
            )
            result.valid = False
        if strategy.next_fields:
            next_field = strategy.next_fields[0]
            phase_fields = {
                req.field for req in requirements.values() if req.phase == strategy.current_phase
            }
            if next_field not in phase_fields:
                result.errors.append(
                    "input_strategy.next_fields[0] must belong to input_strategy.current_phase "
                    f"({next_field!r} is not in phase {strategy.current_phase!r})."
                )
                result.valid = False

        active_phases = [phase for phase in plan.phases if phase.status == "active"]
        if len(active_phases) > 1:
            result.errors.append(
                "At most one plan phase may be active in single_next_question mode."
            )
            result.valid = False

    _validate_traversal_state(plan, result)

    return result


def _validate_traversal_state(plan: EngineeringPlan, result: PlannerValidationResult) -> None:
    traversal = plan.traversal
    if traversal is None:
        return

    active_id = traversal.current_active_node_id
    state_node_ids: set[str] = set()
    if traversal.current_active_node is not None:
        state_node_ids.add(traversal.current_active_node.node_id)
    state_node_ids.update(item.node_id for item in traversal.pending_expansion_nodes)
    state_node_ids.update(item.node_id for item in traversal.expanded_nodes)
    state_node_ids.update(item.node_id for item in traversal.candidate_next_nodes)
    for decision in traversal.branch_decisions:
        state_node_ids.update(decision.candidate_nodes)
        if decision.selected_node:
            state_node_ids.add(decision.selected_node)

    if active_id and active_id not in state_node_ids:
        result.errors.append(
            f"traversal.current_active_node_id {active_id!r} is not present in traversal state."
        )
        result.valid = False

    pending_ids = [item.node_id for item in traversal.pending_expansion_nodes]
    if len(pending_ids) != len(set(pending_ids)):
        result.errors.append("traversal.pending_expansion_nodes contains duplicate node ids.")
        result.valid = False

    expanded_ids = {item.node_id for item in traversal.expanded_nodes}
    pending_set = set(pending_ids)
    overlap = expanded_ids & pending_set
    if overlap:
        result.errors.append(
            "traversal expanded_nodes and pending_expansion_nodes overlap: "
            + ", ".join(sorted(overlap))
        )
        result.valid = False

    for decision in traversal.branch_decisions:
        if decision.status != "unresolved":
            continue
        for candidate in decision.candidate_nodes:
            if candidate in expanded_ids:
                result.errors.append(
                    f"Branch candidate {candidate!r} is expanded before branch "
                    f"{decision.field!r} is resolved."
                )
                result.valid = False
            if candidate == active_id:
                result.errors.append(
                    f"Branch candidate {candidate!r} is active before branch "
                    f"{decision.field!r} is resolved."
                )
                result.valid = False

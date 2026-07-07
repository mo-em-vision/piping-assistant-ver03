"""Invariant checks for normalized engineering plan output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.planner.pipe_wall_plan import PIPE_WALL_WORKFLOW, req_id as requirement_id
from models.engineering_plan import EngineeringPlan, LEGACY_REQUIREMENT_FIELD_NAMES
from engine.planner.plan_phases import strategy_field

_MAX_GOAL_TITLE_LENGTH = 80
_MUTUALLY_EXCLUSIVE_DIAMETER_REQS = frozenset(
    {f"REQ-{key}" for key in ("outside_diameter", "nominal_pipe_size")}
)

_LOOKUP_INPUT_SOURCE_CLASSES = frozenset({"user_input", "derived_value"})

_CANONICAL_TOP_LEVEL_KEYS = frozenset(
    {
        "plan_id",
        "task_id",
        "workflow_id",
        "root_goal",
        "requirements",
        "dependencies",
        "input_strategy",
        "phases",
        "graph",
        "traversal",
        "legacy_goal_map",
        "debug",
    }
)

_PIPE_WALL_LOOKUP_IDS = frozenset(
    {
        "REQ-allowable_stress_lookup",
        "REQ-weld_joint_efficiency_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_strength_reduction_factor_W_lookup",
        "REQ-metallurgical_group_lookup",
    }
)

_PIPE_WALL_EQUATION_IDS = frozenset(
    {
        "REQ-required_wall_thickness",
        "REQ-minimum_required_thickness_eq",
    }
)

_FRESH_PIPE_WALL_HARD_BLOCKED = frozenset(
    {
        "REQ-straight_pipe_section",
        "REQ-pressure_loading",
    }
)

_INTERNAL_PRESSURE_CONDITIONAL_IDS = frozenset(
    {
        "REQ-internal_design_gage_pressure",
        "REQ-allowable_stress_lookup",
        "REQ-weld_joint_efficiency_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_strength_reduction_factor_W_lookup",
        "REQ-required_wall_thickness",
        "REQ-minimum_required_thickness_eq",
    }
)

_DIAMETER_ALT_METHODS = frozenset({"direct_input", "lookup"})


@dataclass
class PlannerValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _alternative_ids(requirements: dict) -> set[str]:
    alt_ids: set[str] = set()
    for req in requirements.values():
        for alt in req.alternatives or []:
            alt_ids.add(alt.id)
    return alt_ids


def _is_long_prompt_title(title: str) -> bool:
    text = str(title or "").strip()
    if len(text) > _MAX_GOAL_TITLE_LENGTH:
        return True
    lowered = text.lower()
    return lowered.startswith("to continue") or lowered.startswith("please provide")


def _is_pipe_wall_workflow(workflow_id: str) -> bool:
    slug = workflow_id.replace("-", "_")
    return slug in {"pipe_wall_thickness", PIPE_WALL_WORKFLOW.replace("-", "_")}


def _validate_canonical_structure(plan: EngineeringPlan, result: PlannerValidationResult) -> None:
    if plan.root_goal is None or not plan.root_goal.id:
        result.errors.append("engineering_plan.root_goal is required.")
        result.valid = False
    if not plan.requirements:
        result.errors.append("engineering_plan.requirements must not be empty.")
        result.valid = False
    if plan.input_strategy is None:
        result.errors.append("engineering_plan.input_strategy is required.")
        result.valid = False
    if not plan.phases:
        result.errors.append("engineering_plan.phases must not be empty.")
        result.valid = False
    if plan.graph is None:
        result.errors.append("engineering_plan.graph is required.")
        result.valid = False
    if plan.traversal is None:
        result.errors.append("engineering_plan.traversal is required.")
        result.valid = False


def _validate_dependency_endpoint(
    endpoint: str,
    *,
    known_requirement_ids: set[str],
    root_goal_id: str,
    alternative_ids: set[str],
    edge_type: str,
    role: str,
    result: PlannerValidationResult,
) -> None:
    if endpoint in known_requirement_ids or endpoint == root_goal_id:
        return
    if edge_type == "activates" and endpoint in alternative_ids:
        return
    result.errors.append(
        f"Dependency {role} references unknown id {endpoint!r} "
        f"(must be requirement id, root goal id, or alternative id for activates edges)."
    )
    result.valid = False


def _validate_dependency_edge(
    edge,
    *,
    requirements: dict,
    root_goal_id: str,
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
        _validate_dependency_endpoint(
            edge.to_id,
            known_requirement_ids=known_requirement_ids,
            root_goal_id=root_goal_id,
            alternative_ids=alternative_ids,
            edge_type=edge.type,
            role="activates target",
            result=result,
        )
        return

    _validate_dependency_endpoint(
        edge.from_id,
        known_requirement_ids=known_requirement_ids,
        root_goal_id=root_goal_id,
        alternative_ids=alternative_ids,
        edge_type=edge.type,
        role="from",
        result=result,
    )
    _validate_dependency_endpoint(
        edge.to_id,
        known_requirement_ids=known_requirement_ids,
        root_goal_id=root_goal_id,
        alternative_ids=alternative_ids,
        edge_type=edge.type,
        role="to",
        result=result,
    )

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


def _validate_diameter_resolution_alternatives(
    requirements: dict,
    result: PlannerValidationResult,
) -> None:
    diameter = requirements.get("REQ-diameter_resolution")
    if diameter is None:
        return
    alternatives = diameter.alternatives or []
    if len(alternatives) != 2:
        result.errors.append(
            "REQ-diameter_resolution must expose exactly two alternatives "
            "(direct outside diameter and NPS lookup)."
        )
        result.valid = False
        return

    methods = {alt.method for alt in alternatives}
    if methods != _DIAMETER_ALT_METHODS:
        result.errors.append(
            "REQ-diameter_resolution alternatives must include direct_input and lookup methods."
        )
        result.valid = False

    alt_ids = {alt.id for alt in alternatives}
    if "ALT-direct-outside-diameter" not in alt_ids or "ALT-nps-lookup" not in alt_ids:
        result.errors.append(
            "REQ-diameter_resolution must include ALT-direct-outside-diameter and ALT-nps-lookup."
        )
        result.valid = False


def _validate_pipe_wall_workflow_invariants(
    plan: EngineeringPlan,
    result: PlannerValidationResult,
) -> None:
    if not _is_pipe_wall_workflow(plan.workflow_id):
        return

    requirements = plan.requirements
    missing_lookups = sorted(_PIPE_WALL_LOOKUP_IDS - set(requirements.keys()))
    if missing_lookups:
        result.errors.append(
            "Pipe wall plan missing lookup requirements: " + ", ".join(missing_lookups)
        )
        result.valid = False

    missing_equations = sorted(_PIPE_WALL_EQUATION_IDS - set(requirements.keys()))
    if missing_equations:
        result.errors.append(
            "Pipe wall plan missing equation requirements: " + ", ".join(missing_equations)
        )
        result.valid = False

    straight_req = requirements.get("REQ-straight_pipe_section")
    pressure_req = requirements.get("REQ-pressure_loading")
    straight_unresolved = (
        straight_req is not None and straight_req.status in {"missing", "ready"}
    )
    pressure_unresolved = (
        pressure_req is not None and pressure_req.status in {"missing", "ready"}
    )

    if pressure_unresolved:
        for req_id in _INTERNAL_PRESSURE_CONDITIONAL_IDS:
            req = requirements.get(req_id)
            if req is None:
                continue
            if req.activation_status != "conditional":
                result.errors.append(
                    f"{req_id} must be conditional before pressure_loading is resolved."
                )
                result.valid = False

    strategy = plan.input_strategy
    if straight_unresolved and pressure_unresolved:
        hard_blocked = set(plan.root_goal.blocked_by)
        if hard_blocked != _FRESH_PIPE_WALL_HARD_BLOCKED:
            result.errors.append(
                "Fresh pipe wall plan must hard-block only "
                "REQ-straight_pipe_section and REQ-pressure_loading; "
                f"got {sorted(hard_blocked)}."
            )
            result.valid = False

        if strategy is not None:
            if strategy.next_fields != ["straight_pipe_section"]:
                result.errors.append(
                    "Fresh pipe wall plan next field must be straight_pipe_section; "
                    f"got {strategy.next_fields!r}."
                )
                result.valid = False
            if strategy.current_phase != "expansion_assumptions":
                result.errors.append(
                    "Fresh pipe wall plan current_phase must be expansion_assumptions; "
                    f"got {strategy.current_phase!r}."
                )
                result.valid = False
    elif straight_unresolved is False and pressure_unresolved:
        if set(plan.root_goal.blocked_by) != {"REQ-pressure_loading"}:
            result.errors.append(
                "After straight_pipe_section is resolved, root goal must hard-block only "
                f"REQ-pressure_loading; got {plan.root_goal.blocked_by!r}."
            )
            result.valid = False
        if strategy is not None:
            if strategy.next_fields != ["pressure_loading"]:
                result.errors.append(
                    "After straight_pipe_section is resolved, next field must be pressure_loading; "
                    f"got {strategy.next_fields!r}."
                )
                result.valid = False
            if strategy.current_phase != "path_decisions":
                result.errors.append(
                    "After straight_pipe_section is resolved, current_phase must be path_decisions; "
                    f"got {strategy.current_phase!r}."
                )
                result.valid = False


def _validate_traversal_state(plan: EngineeringPlan, result: PlannerValidationResult) -> None:
    traversal = plan.traversal
    if traversal is None:
        return

    if traversal.current_active_node_id is None:
        result.errors.append("traversal.current_active_node_id is required.")
        result.valid = False
    if traversal.current_active_node is None:
        result.errors.append("traversal.current_active_node is required.")
        result.valid = False
    if not traversal.pending_expansion_nodes:
        result.warnings.append("traversal.pending_expansion_nodes is empty.")
    if not traversal.expanded_nodes:
        result.warnings.append("traversal.expanded_nodes is empty.")
    if not traversal.branch_decisions:
        result.warnings.append("traversal.branch_decisions is empty.")

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
            if candidate not in pending_set and candidate not in expanded_ids:
                result.warnings.append(
                    f"Branch candidate {candidate!r} is neither pending nor expanded "
                    f"while branch {decision.field!r} is unresolved."
                )


def validate_engineering_plan(plan: EngineeringPlan) -> PlannerValidationResult:
    result = PlannerValidationResult()
    _validate_canonical_structure(plan, result)

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

        req_dict = req.to_dict()
        legacy_fields = sorted(LEGACY_REQUIREMENT_FIELD_NAMES.intersection(req_dict.keys()))
        if legacy_fields:
            result.errors.append(
                f"Requirement {requirement_key} must not include legacy goal fields: "
                + ", ".join(legacy_fields)
            )
            result.valid = False
        if req_dict.get("question_spec") and "metadata" in req_dict:
            result.errors.append(
                f"Requirement {requirement_key} must expose question_spec directly, not in metadata."
            )
            result.valid = False
        if "edges" in req_dict:
            result.errors.append(
                f"Requirement {requirement_key} must not include edges; use engineering_plan.dependencies."
            )
            result.valid = False

    diameter_top_level = _MUTUALLY_EXCLUSIVE_DIAMETER_REQS.intersection(set(root.blocked_by))
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

    _validate_diameter_resolution_alternatives(requirements, result)

    alternative_ids = _alternative_ids(requirements)
    for edge in plan.dependencies:
        _validate_dependency_edge(
            edge,
            requirements=requirements,
            root_goal_id=root.id,
            known_requirement_ids=set(requirements.keys()),
            alternative_ids=alternative_ids,
            result=result,
        )

    if not plan.dependencies:
        result.errors.append("engineering_plan.dependencies must not be empty.")
        result.valid = False

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
                strategy_field(req)
                for req in requirements.values()
                if req.phase == strategy.current_phase
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

    _validate_pipe_wall_workflow_invariants(plan, result)
    _validate_traversal_state(plan, result)

    return result


def validate_engineering_plan_dict(raw: dict[str, Any]) -> PlannerValidationResult:
    """Validate serialized engineering_plan dict, including rejection of flat goal maps."""
    result = PlannerValidationResult()
    if not raw:
        result.errors.append("engineering_plan payload is empty.")
        result.valid = False
        return result

    flat_goal_keys = [key for key in raw if str(key).startswith(("GOAL-", "REQ-"))]
    if flat_goal_keys and "requirements" not in raw:
        result.errors.append(
            "Canonical engineering_plan must not be a flat top-level GOAL-*/REQ-* map."
        )
        result.valid = False
        return result

    missing_keys = sorted(
        key
        for key in (
            "root_goal",
            "requirements",
            "dependencies",
            "input_strategy",
            "phases",
            "graph",
            "traversal",
        )
        if key not in raw
    )
    if missing_keys:
        result.errors.append(
            "engineering_plan missing required sections: " + ", ".join(missing_keys)
        )
        result.valid = False

    unexpected_top_level = sorted(set(raw.keys()) - _CANONICAL_TOP_LEVEL_KEYS)
    if unexpected_top_level and "requirements" not in raw:
        result.errors.append(
            "engineering_plan has unexpected top-level keys: " + ", ".join(unexpected_top_level)
        )
        result.valid = False

    if not result.valid:
        return result

    from engine.planner.plan_inspector import engineering_plan_from_dict

    plan = engineering_plan_from_dict(raw)
    if plan is None:
        result.errors.append("engineering_plan could not be parsed into EngineeringPlan.")
        result.valid = False
        return result

    nested = validate_engineering_plan(plan)
    result.valid = nested.valid
    result.errors.extend(nested.errors)
    result.warnings.extend(nested.warnings)
    return result

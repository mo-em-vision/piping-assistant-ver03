"""Phased navigation question ordering for assumption-first workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.graph.assumption_checker import AssumptionEvaluation
from engine.graph.workflow_navigation import WorkflowNavigationConfig, load_workflow_navigation
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase


@dataclass
class PhasedNavigation:
    current_phase: NavigationPhase = NavigationPhase.EXPANSION_ASSUMPTIONS
    phase_missing: dict[str, list[str]] = field(default_factory=dict)
    phase_questions: dict[str, list[str]] = field(default_factory=dict)
    all_missing: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    block_messages: list[str] = field(default_factory=list)


def _ordered_missing(
    missing: list[str],
    order: tuple[str, ...],
) -> list[str]:
    ordered = [field_id for field_id in order if field_id in missing]
    for field_id in missing:
        if field_id not in ordered:
            ordered.append(field_id)
    return ordered


def _questions_for_fields(
    fields: list[str],
    question_map: dict[str, str],
) -> list[str]:
    return [question_map[field_id] for field_id in fields if field_id in question_map]


def _phase_field_set(config: WorkflowNavigationConfig, phase: NavigationPhase) -> frozenset[str]:
    return config.fields_for_phase(phase)


def build_workflow_phased_navigation(
    *,
    config: WorkflowNavigationConfig,
    assumption_eval: AssumptionEvaluation,
    expansion_eval: AssumptionEvaluation,
    user_inputs: list[str],
    execution_eval: AssumptionEvaluation,
    question_map: dict[str, str],
) -> PhasedNavigation:
    """Partition missing fields into ordered navigation phases from workflow config."""
    result = PhasedNavigation()

    if assumption_eval.blocked:
        result.blocked_nodes = [block.node_id for block in assumption_eval.blocked]
        result.block_messages = [block.message for block in assumption_eval.blocked]
        result.current_phase = NavigationPhase.EXPANSION_ASSUMPTIONS
        result.questions = result.block_messages[:1] or ["Workflow path is blocked."]
        return result

    expansion_fields = _phase_field_set(config, NavigationPhase.EXPANSION_ASSUMPTIONS)
    path_fields = _phase_field_set(config, NavigationPhase.PATH_DECISIONS)
    parameter_order = config.ordered_fields_for_phase(NavigationPhase.PARAMETER_GATHERING)
    coefficient_order = config.ordered_fields_for_phase(NavigationPhase.COEFFICIENT_RESOLUTION)
    execution_order = config.ordered_fields_for_phase(NavigationPhase.EXECUTION_ASSUMPTIONS)

    combined_assumption_missing = assumption_eval.missing_fields + expansion_eval.missing_fields

    phase1 = list(
        dict.fromkeys(field_id for field_id in combined_assumption_missing if field_id in expansion_fields)
    )
    phase2 = list(
        dict.fromkeys(field_id for field_id in combined_assumption_missing if field_id in path_fields)
    )
    phase3 = _ordered_missing(user_inputs, parameter_order)
    phase4_source = [
        field_id
        for field_id in list(expansion_eval.missing_fields) + list(execution_eval.missing_fields)
        if field_id not in expansion_fields and field_id not in path_fields
    ]
    phase4 = _ordered_missing(phase4_source, coefficient_order)
    phase5 = _ordered_missing(
        [field_id for field_id in execution_eval.missing_fields if field_id in execution_order],
        execution_order,
    )

    coefficient_set = set(coefficient_order)
    phase5 = [field_id for field_id in phase5 if field_id not in coefficient_set]

    definition_order = config.ordered_fields_for_phase(NavigationPhase.DEFINITION_EQUATION_COMPLETION)
    phase_definition = _ordered_missing(
        [field_id for field_id in execution_eval.missing_fields if field_id in definition_order],
        definition_order,
    )

    result.phase_missing = {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value: phase1,
        NavigationPhase.PATH_DECISIONS.value: phase2,
        NavigationPhase.PARAMETER_GATHERING.value: phase3,
        NavigationPhase.COEFFICIENT_RESOLUTION.value: phase4,
        NavigationPhase.EXECUTION_ASSUMPTIONS.value: phase5,
        NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: phase_definition,
    }

    phase_sequence = (
        NavigationPhase.EXPANSION_ASSUMPTIONS,
        NavigationPhase.PATH_DECISIONS,
        NavigationPhase.PARAMETER_GATHERING,
        NavigationPhase.COEFFICIENT_RESOLUTION,
        NavigationPhase.EXECUTION_ASSUMPTIONS,
        NavigationPhase.DEFINITION_EQUATION_COMPLETION,
    )

    for phase in phase_sequence:
        fields = result.phase_missing.get(phase.value, [])
        result.phase_questions[phase.value] = _questions_for_fields(fields, question_map)

    for phase in phase_sequence:
        fields = result.phase_missing.get(phase.value, [])
        if fields:
            result.current_phase = phase
            result.all_missing = fields
            result.questions = result.phase_questions[phase.value]
            break
    else:
        result.current_phase = NavigationPhase.READY
        result.all_missing = []
        result.questions = []

    return result


def build_phased_navigation(
    *,
    assumption_eval: AssumptionEvaluation,
    expansion_eval: AssumptionEvaluation,
    user_inputs: list[str],
    execution_eval: AssumptionEvaluation,
    question_map: dict[str, str],
    config: WorkflowNavigationConfig | None = None,
    reader: StandardsReader | None = None,
    workflow_id: str | None = None,
) -> PhasedNavigation:
    """Build pipe-wall-thickness phased navigation (config from reader when provided)."""
    if config is None:
        if reader is not None and workflow_id:
            config = load_workflow_navigation(reader, workflow_id)
        else:
            from engine.graph.workflow_navigation import _config_from_defaults

            config = _config_from_defaults("pipe_wall_thickness_design")
            if config is None:
                raise ValueError("navigation config unavailable")
    return build_workflow_phased_navigation(
        config=config,
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=user_inputs,
        execution_eval=execution_eval,
        question_map=question_map,
    )


def build_mawp_phased_navigation(
    *,
    assumption_eval: AssumptionEvaluation,
    expansion_eval: AssumptionEvaluation,
    user_inputs: list[str],
    execution_eval: AssumptionEvaluation,
    question_map: dict[str, str],
    config: WorkflowNavigationConfig | None = None,
    reader: StandardsReader | None = None,
    workflow_id: str | None = None,
) -> PhasedNavigation:
    """Build MAWP phased navigation (config from reader when provided)."""
    if config is None:
        if reader is not None and workflow_id:
            config = load_workflow_navigation(reader, workflow_id)
        else:
            from engine.graph.workflow_navigation import _config_from_defaults

            config = _config_from_defaults("mawp_design")
            if config is None:
                raise ValueError("navigation config unavailable")
    return build_workflow_phased_navigation(
        config=config,
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=user_inputs,
        execution_eval=execution_eval,
        question_map=question_map,
    )


def allowed_fields_for_phase(
    phase: NavigationPhase,
    *,
    workflow: str | None = None,
    config: WorkflowNavigationConfig | None = None,
    reader: StandardsReader | None = None,
) -> frozenset[str]:
    """Return input fields that may be extracted/stored during a navigation phase."""
    if config is None:
        from engine.graph.workflow_navigation import _config_from_defaults

        slug = workflow or "pipe_wall_thickness_design"
        if reader is not None:
            config = load_workflow_navigation(reader, slug)
        else:
            config = _config_from_defaults(slug) or _config_from_defaults("pipe_wall_thickness_design")
            if config is None:
                return frozenset()
    if phase == NavigationPhase.READY:
        return frozenset()
    return config.fields_for_phase(phase)

"""Phased navigation question ordering for assumption-first workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.graph.assumption_checker import AssumptionEvaluation, field_value
from engine.graph.workflow_navigation import (
    WorkflowNavigationConfig,
    _empty_navigation_config,
    load_workflow_navigation,
)
from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
from engine.reference.parameter_metadata import is_path_decision_parameter
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact, fact_is_expansion_ready
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


def _field_satisfied(field_id: str, existing_inputs: dict[str, Fact]) -> bool:
    fact = existing_inputs.get(field_id)
    if fact is None:
        return False
    if field_value(field_id, existing_inputs) is None:
        return False
    return fact_is_expansion_ready(fact)


def missing_fields_from_navigation(
    config: WorkflowNavigationConfig,
    existing_inputs: dict[str, Fact],
) -> dict[str, list[str]]:
    """Return nav-config fields that are not yet expansion-ready in task inputs."""
    result: dict[str, list[str]] = {}
    for phase, fields in config.phase_order:
        missing = [field_id for field_id in fields if not _field_satisfied(field_id, existing_inputs)]
        if missing:
            result[phase.value] = missing
    return result


_NAV_CONFIG_GATE_PHASES = frozenset(
    {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value,
        NavigationPhase.PATH_DECISIONS.value,
    }
)


def _gate_phase_missing_from_navigation(
    config: WorkflowNavigationConfig,
    existing_inputs: dict[str, Fact],
) -> dict[str, list[str]]:
    """Return only expansion/path gate fields from nav config — not path-specific parameters."""
    nav_missing = missing_fields_from_navigation(config, existing_inputs)
    return {
        phase: list(fields)
        for phase, fields in nav_missing.items()
        if phase in _NAV_CONFIG_GATE_PHASES
    }


def _merge_phase_missing(
    base: dict[str, list[str]],
    extra: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged = {phase: list(fields) for phase, fields in base.items()}
    for phase, fields in extra.items():
        combined = list(dict.fromkeys((merged.get(phase) or []) + list(fields)))
        merged[phase] = combined
    return merged


def _questions_for_fields(
    fields: list[str],
    question_map: dict[str, str],
) -> list[str]:
    return [question_map[field_id] for field_id in fields if field_id in question_map]


def _phase_field_set(config: WorkflowNavigationConfig, phase: NavigationPhase) -> frozenset[str]:
    return config.fields_for_phase(phase)


def _is_path_decision_field(field_id: str) -> bool:
    metadata = load_parameter_node_metadata(param_node_id_for_input(field_id))
    return is_path_decision_parameter(metadata)


def _metadata_driven_phase_fields(
    combined_assumption_missing: list[str],
    *,
    expansion_gate_fields: frozenset[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Split expansion/path missing fields using PARAM metadata — not workflow nav lists."""
    phase1: list[str] = []
    phase2: list[str] = []
    for field_id in combined_assumption_missing:
        if _is_path_decision_field(field_id):
            if field_id not in phase2:
                phase2.append(field_id)
        elif expansion_gate_fields is None or field_id in expansion_gate_fields:
            if field_id not in phase1:
                phase1.append(field_id)
    return phase1, phase2


def _nav_has_phase_fields(config: WorkflowNavigationConfig) -> bool:
    return any(fields for _, fields in config.phase_order)


def build_workflow_phased_navigation(
    *,
    config: WorkflowNavigationConfig,
    assumption_eval: AssumptionEvaluation,
    expansion_eval: AssumptionEvaluation,
    user_inputs: list[str],
    execution_eval: AssumptionEvaluation,
    question_map: dict[str, str],
    existing_inputs: dict[str, Fact] | None = None,
    post_thickness_outputs: dict[str, Any] | None = None,
    has_execution: bool = False,
    expansion_gate_fields: frozenset[str] | None = None,
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

    combined_assumption_missing = list(
        dict.fromkeys(assumption_eval.missing_fields + expansion_eval.missing_fields)
    )

    if _nav_has_phase_fields(config):
        phase1 = list(
            dict.fromkeys(
                field_id for field_id in combined_assumption_missing if field_id in expansion_fields
            )
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
    else:
        phase1, phase2 = _metadata_driven_phase_fields(
            combined_assumption_missing,
            expansion_gate_fields=expansion_gate_fields,
        )
        for field_id in user_inputs:
            if _is_path_decision_field(field_id) and field_id not in phase2:
                phase2.append(field_id)
        path_and_expansion = set(phase1) | set(phase2)
        phase3 = [
            field_id
            for field_id in user_inputs
            if field_id not in path_and_expansion and not _is_path_decision_field(field_id)
        ]
        phase4_source = [
            field_id
            for field_id in list(expansion_eval.missing_fields) + list(execution_eval.missing_fields)
            if field_id not in path_and_expansion and field_id not in phase3
        ]
        phase4 = list(dict.fromkeys(phase4_source))

    phase5 = _ordered_missing(
        [field_id for field_id in execution_eval.missing_fields if field_id in execution_order],
        execution_order,
    ) if execution_order else [
        field_id
        for field_id in execution_eval.missing_fields
        if field_id not in set(phase1) | set(phase2) | set(phase3) | set(phase4)
    ]

    coefficient_set = set(coefficient_order) if coefficient_order else set(phase4)
    phase5 = [field_id for field_id in phase5 if field_id not in coefficient_set]

    definition_order = config.ordered_fields_for_phase(NavigationPhase.DEFINITION_EQUATION_COMPLETION)
    phase_definition_source = [
        field_id for field_id in execution_eval.missing_fields if field_id in definition_order
    ]
    if (
        has_execution
        and post_thickness_outputs is not None
        and existing_inputs is not None
    ):
        thickness_ready = (
            post_thickness_outputs.get("t") is not None
            or post_thickness_outputs.get("required_thickness") is not None
        )
        minimum_thickness_done = (
            post_thickness_outputs.get("minimum_required_thickness") is not None
            or post_thickness_outputs.get("t_m") is not None
        )
        if thickness_ready and not minimum_thickness_done:
            for field_id in definition_order:
                if field_id in phase_definition_source:
                    continue
                if not _field_satisfied(field_id, existing_inputs):
                    phase_definition_source.append(field_id)
    phase_definition = _ordered_missing(phase_definition_source, definition_order)
    if not definition_order and not phase_definition:
        phase_definition = [
            field_id
            for field_id in execution_eval.missing_fields
            if field_id
            not in set(phase1) | set(phase2) | set(phase3) | set(phase4) | set(phase5)
        ]

    result.phase_missing = {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value: phase1,
        NavigationPhase.PATH_DECISIONS.value: phase2,
        NavigationPhase.PARAMETER_GATHERING.value: phase3,
        NavigationPhase.COEFFICIENT_RESOLUTION.value: phase4,
        NavigationPhase.EXECUTION_ASSUMPTIONS.value: phase5,
        NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: phase_definition,
    }

    if existing_inputs and _nav_has_phase_fields(config):
        result.phase_missing = _merge_phase_missing(
            result.phase_missing,
            _gate_phase_missing_from_navigation(config, existing_inputs),
        )

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
            config = _empty_navigation_config("pipe_wall_thickness_design")
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
            config = _empty_navigation_config("mawp_design")
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
        slug = workflow or "pipe_wall_thickness_design"
        if reader is not None:
            config = load_workflow_navigation(reader, slug)
        else:
            config = _empty_navigation_config(slug)
    if phase == NavigationPhase.READY:
        return frozenset()
    return config.fields_for_phase(phase)

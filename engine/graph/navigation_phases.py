"""Phased navigation question ordering for assumption-first workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.graph.assumption_checker import AssumptionEvaluation
from models.planning import NavigationPhase


_PHASE1_FIELDS = frozenset({"straight_pipe_section"})
_PHASE2_FIELDS = frozenset({"pressure_loading"})
_PHASE3_ORDER = (
    "design_pressure",
    "nominal_pipe_size",
    "outside_diameter",
    "material",
    "design_temperature",
    "external_design_pressure",
)
_PHASE4_ORDER = (
    "joint_category",
    "weld_joint_efficiency",
    "weld_strength_reduction",
    "temperature_coefficient",
)
_PHASE5_ORDER = ("corrosion_allowance",)


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


def build_phased_navigation(
    *,
    assumption_eval: AssumptionEvaluation,
    expansion_eval: AssumptionEvaluation,
    user_inputs: list[str],
    execution_eval: AssumptionEvaluation,
    question_map: dict[str, str],
) -> PhasedNavigation:
    """Partition missing fields into ordered navigation phases."""
    result = PhasedNavigation()

    if assumption_eval.blocked:
        result.blocked_nodes = [block.node_id for block in assumption_eval.blocked]
        result.block_messages = [block.message for block in assumption_eval.blocked]
        result.current_phase = NavigationPhase.EXPANSION_ASSUMPTIONS
        result.questions = result.block_messages[:1] or ["Workflow path is blocked."]
        return result

    phase1 = list(
        dict.fromkeys(
            field_id
            for field_id in assumption_eval.missing_fields + expansion_eval.missing_fields
            if field_id in _PHASE1_FIELDS
        )
    )
    phase2 = list(
        dict.fromkeys(
            field_id
            for field_id in assumption_eval.missing_fields + expansion_eval.missing_fields
            if field_id in _PHASE2_FIELDS
        )
    )

    phase3 = _ordered_missing(user_inputs, _PHASE3_ORDER)
    phase4_source = [
        field_id
        for field_id in list(expansion_eval.missing_fields) + list(execution_eval.missing_fields)
        if field_id not in _PHASE1_FIELDS and field_id not in _PHASE2_FIELDS
    ]
    phase4 = _ordered_missing(phase4_source, _PHASE4_ORDER)
    phase5 = _ordered_missing(
        [
            field_id
            for field_id in execution_eval.missing_fields
            if field_id in _PHASE5_ORDER
        ],
        _PHASE5_ORDER,
    )

    # Remove phase4 fields from phase5 duplicate handling
    phase4_set = set(_PHASE4_ORDER)
    phase5 = [field_id for field_id in phase5 if field_id not in phase4_set]

    result.phase_missing = {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value: phase1,
        NavigationPhase.PATH_DECISIONS.value: phase2,
        NavigationPhase.PARAMETER_GATHERING.value: phase3,
        NavigationPhase.COEFFICIENT_RESOLUTION.value: phase4,
        NavigationPhase.EXECUTION_ASSUMPTIONS.value: phase5,
    }

    for phase, fields in (
        (NavigationPhase.EXPANSION_ASSUMPTIONS, phase1),
        (NavigationPhase.PATH_DECISIONS, phase2),
        (NavigationPhase.PARAMETER_GATHERING, phase3),
        (NavigationPhase.COEFFICIENT_RESOLUTION, phase4),
        (NavigationPhase.EXECUTION_ASSUMPTIONS, phase5),
    ):
        result.phase_questions[phase.value] = _questions_for_fields(fields, question_map)

    for phase, fields in (
        (NavigationPhase.EXPANSION_ASSUMPTIONS, phase1),
        (NavigationPhase.PATH_DECISIONS, phase2),
        (NavigationPhase.PARAMETER_GATHERING, phase3),
        (NavigationPhase.COEFFICIENT_RESOLUTION, phase4),
        (NavigationPhase.EXECUTION_ASSUMPTIONS, phase5),
    ):
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


def allowed_fields_for_phase(phase: NavigationPhase) -> frozenset[str]:
    """Return input fields that may be extracted/stored during a navigation phase."""
    if phase == NavigationPhase.EXPANSION_ASSUMPTIONS:
        return _PHASE1_FIELDS
    if phase == NavigationPhase.PATH_DECISIONS:
        return _PHASE2_FIELDS
    if phase == NavigationPhase.PARAMETER_GATHERING:
        return frozenset(_PHASE3_ORDER)
    if phase == NavigationPhase.COEFFICIENT_RESOLUTION:
        return frozenset(_PHASE4_ORDER)
    if phase == NavigationPhase.EXECUTION_ASSUMPTIONS:
        return frozenset(_PHASE5_ORDER)
    return frozenset()

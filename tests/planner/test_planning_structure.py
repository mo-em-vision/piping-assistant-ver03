"""Unit tests for planning structure snapshots."""

from __future__ import annotations

from engine.graph.assumption_checker import AssumptionEvaluation
from engine.graph.navigation_phases import PhasedNavigation
from engine.planner.planning_structure import (
    STRUCTURAL_SIGNATURE_KEYS,
    build_planning_structure_snapshot,
    structure_unchanged_for_skip,
)
from models.execution import ExecutionPlan
from models.planning import NavigationPhase


def _snapshot(**overrides):
    base = build_planning_structure_snapshot(
        preview=ExecutionPlan(
            task_id="task-1",
            root="pipe_wall_thickness_design",
            nodes=("n1", "n2"),
            execution_order=("n1", "n2"),
        ),
        active_nodes=["n1"],
        phased=PhasedNavigation(
            current_phase=NavigationPhase.PARAMETER_GATHERING,
            phase_missing={"parameter_gathering": ["corrosion_allowance"]},
            all_missing=["corrosion_allowance"],
        ),
        path_decision={"field": "pressure_loading", "value": "internal_pressure"},
        expansion_eval=AssumptionEvaluation(),
        assumption_eval=AssumptionEvaluation(),
        execution_eval=AssumptionEvaluation(),
        missing_inputs=["corrosion_allowance"],
        expansion_gate_ready=True,
        lazy_plan=False,
        submittable_parameters=["corrosion_allowance"],
    )
    assert base is not None
    if overrides:
        base = {**base, **overrides}
    return base


def test_snapshot_includes_required_fields() -> None:
    snapshot = _snapshot()
    for key in (
        "execution_order",
        "active_nodes",
        "current_phase",
        "next_input",
        "missing_inputs",
        "missing_assumptions",
        "submittable_parameters",
        "blocked_requirement_ids",
        "active_branch_decisions",
        "expansion_gate_state",
        "path_decision_state",
    ):
        assert key in snapshot


def test_structure_unchanged_ignores_missing_inputs_delta() -> None:
    before = _snapshot()
    after = _snapshot(
        missing_inputs=["design_temperature"],
        submittable_parameters=["design_temperature"],
        next_input="design_temperature",
    )
    assert structure_unchanged_for_skip(before, after)


def test_structure_changed_when_execution_order_changes() -> None:
    before = _snapshot()
    after = _snapshot(execution_order=["n1", "n2", "n3"])
    assert not structure_unchanged_for_skip(before, after)


def test_structure_changed_when_branch_decision_changes() -> None:
    before = _snapshot()
    after = _snapshot(
        path_decision_state={"field": "pressure_loading", "value": "external_pressure"},
        active_branch_decisions=["pressure_loading"],
    )
    assert not structure_unchanged_for_skip(before, after)


def test_uncertainty_returns_none_for_empty_execution_order() -> None:
    snapshot = build_planning_structure_snapshot(
        preview=ExecutionPlan(
            task_id="task-1",
            root="pipe_wall_thickness_design",
            nodes=(),
            execution_order=(),
        ),
        active_nodes=[],
        phased=PhasedNavigation(),
        path_decision={},
        expansion_eval=AssumptionEvaluation(),
        assumption_eval=AssumptionEvaluation(),
        execution_eval=AssumptionEvaluation(),
        missing_inputs=[],
        expansion_gate_ready=False,
        lazy_plan=True,
    )
    assert snapshot is None


def test_structural_keys_are_subset_of_snapshot() -> None:
    snapshot = _snapshot()
    for key in STRUCTURAL_SIGNATURE_KEYS:
        assert key in snapshot

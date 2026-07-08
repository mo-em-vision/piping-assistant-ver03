"""Parametrized fact-progression tests for pipe wall engineering plans (Cases A–F)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from api.serializers import task_state
from api.workflow_bootstrap import bootstrap_new_task
from config.loader import CLIConfig
from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.plan_validation import validate_engineering_plan
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    external_pressure_assumption,
    internal_pressure_assumption,
    straight_section_assumption,
)

_INTERNAL_PRESSURE_ACTIVE_REQUIREMENT_IDS = (
    "REQ-internal_design_gage_pressure",
    "REQ-diameter_resolution",
    "REQ-material_grade",
    "REQ-design_temperature",
    "REQ-corrosion_allowance",
    "REQ-pipe_construction_type",
    "REQ-required_wall_thickness",
    "REQ-minimum_required_thickness_eq",
)

_EXTERNAL_INTERNAL_NOT_APPLICABLE_REQ_IDS = (
    "REQ-internal_design_gage_pressure",
    "REQ-diameter_resolution",
    "REQ-nominal_pipe_size",
    "REQ-outside_diameter_lookup",
    "REQ-required_wall_thickness",
    "REQ-minimum_required_thickness_eq",
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_pipe_wall_task(task_id: str = "progression-pwt"):
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _confirmed_input(input_id: str, value: Any, unit: str = "dimensionless") -> EngineeringInput:
    return EngineeringInput(
        input_id=input_id,
        value=value,
        unit=unit,
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )


def _store_inputs(
    manager: TaskStateManager,
    task_id: str,
    inputs: list[EngineeringInput],
):
    for inp in inputs:
        manager.store_fact(
            task_id,
            fact_from_engineering_input(
                inp,
                task_id=task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    return manager.get_task(task_id)


def _build_plan_from_inputs(inputs: list[EngineeringInput]):
    manager, task = _fresh_pipe_wall_task()
    task = _store_inputs(manager, task.task_id, inputs)
    existing = dict(task.fact_store.active_facts())
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=existing)
    return manager, task, plan


def _active_phase_ids(plan) -> list[str]:
    return [phase.id for phase in plan.phases if phase.status == "active"]


@dataclass(frozen=True)
class ProgressionExpectation:
    label: str
    inputs: tuple[EngineeringInput, ...]
    current_phase: str
    next_fields: tuple[str, ...]
    active_phases: tuple[str, ...]
    active_node_id: str | None
    internal_activation: str
    root_blocked_by: tuple[str, ...] | None = None
    expect_valid: bool = True
    branch_selected_node: str | None = None
    nps_status: str | None = None
    od_lookup_status: str | None = None


PROGRESSION_CASES: tuple[ProgressionExpectation, ...] = (
    ProgressionExpectation(
        label="A",
        inputs=(),
        current_phase="expansion_assumptions",
        next_fields=("straight_pipe_section",),
        active_phases=("expansion_assumptions",),
        active_node_id=param_node_id_for_input("straight_pipe_section"),
        internal_activation="conditional",
        root_blocked_by=("REQ-straight_pipe_section", "REQ-pressure_loading"),
    ),
    ProgressionExpectation(
        label="B",
        inputs=(straight_section_assumption(),),
        current_phase="path_decisions",
        next_fields=("pressure_loading",),
        active_phases=("path_decisions",),
        active_node_id=param_node_id_for_input("pressure_loading"),
        internal_activation="conditional",
        root_blocked_by=("REQ-pressure_loading",),
    ),
    ProgressionExpectation(
        label="C",
        inputs=(straight_section_assumption(), internal_pressure_assumption()),
        current_phase="parameter_gathering",
        next_fields=("internal_design_gage_pressure",),
        active_phases=("parameter_gathering",),
        active_node_id=param_node_id_for_input("internal_design_gage_pressure"),
        internal_activation="active",
        branch_selected_node="304.1.2-a",
    ),
    ProgressionExpectation(
        label="D",
        inputs=(straight_section_assumption(), external_pressure_assumption()),
        current_phase="ready",
        next_fields=(),
        active_phases=(),
        active_node_id=None,
        internal_activation="not_applicable",
        root_blocked_by=(),
        expect_valid=False,
    ),
    ProgressionExpectation(
        label="E",
        inputs=(
            straight_section_assumption(),
            internal_pressure_assumption(),
            _confirmed_input("d_input_mode", "direct_od"),
        ),
        current_phase="parameter_gathering",
        next_fields=("internal_design_gage_pressure",),
        active_phases=("parameter_gathering",),
        active_node_id=param_node_id_for_input("internal_design_gage_pressure"),
        internal_activation="active",
        branch_selected_node="304.1.2-a",
        nps_status="not_applicable",
        od_lookup_status="not_applicable",
    ),
    ProgressionExpectation(
        label="F",
        inputs=(
            straight_section_assumption(),
            internal_pressure_assumption(),
            _confirmed_input("d_input_mode", "nps_lookup"),
        ),
        current_phase="parameter_gathering",
        next_fields=("internal_design_gage_pressure",),
        active_phases=("parameter_gathering",),
        active_node_id=param_node_id_for_input("internal_design_gage_pressure"),
        internal_activation="active",
        branch_selected_node="304.1.2-a",
        nps_status="missing",
        od_lookup_status="blocked",
    ),
)


@pytest.mark.parametrize("case", PROGRESSION_CASES, ids=lambda case: case.label)
def test_pipe_wall_fact_progression_matrix(case: ProgressionExpectation) -> None:
    """Table-driven progression for pipe wall planner state (Cases A–F)."""
    _, _, plan = _build_plan_from_inputs(list(case.inputs))
    validation = validate_engineering_plan(plan)

    if case.expect_valid:
        assert validation.valid, validation.errors
    else:
        assert not validation.valid

    strategy = plan.input_strategy
    assert strategy is not None
    assert strategy.current_phase == case.current_phase
    assert tuple(strategy.next_fields) == case.next_fields
    assert tuple(_active_phase_ids(plan)) == case.active_phases

    internal = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal.activation_status == case.internal_activation

    if case.root_blocked_by is not None:
        assert tuple(plan.root_goal.blocked_by) == case.root_blocked_by

    traversal = plan.traversal
    if case.expect_valid:
        assert traversal is not None
        assert traversal.current_active_node_id == case.active_node_id
        assert traversal.current_active_node is not None
        assert traversal.current_active_node.node_id == case.active_node_id
    else:
        assert case.active_node_id is None
        assert any("traversal.current_active_node" in error for error in validation.errors)

    if case.label == "A":
        assert strategy.mode == "single_next_question"
        assert "pressure_loading" not in strategy.next_fields
        assert "pressure_loading" in strategy.blocked_fields
        assert len(_active_phase_ids(plan)) == 1

    if case.label == "C":
        assert internal.status == "missing"
        assert "REQ-diameter_resolution" in plan.root_goal.blocked_by
        for req_id in _INTERNAL_PRESSURE_ACTIVE_REQUIREMENT_IDS:
            assert plan.requirements[req_id].activation_status == "active", req_id
        assert case.branch_selected_node is not None
        pressure_decision = next(
            item for item in traversal.branch_decisions if item.field == "pressure_loading"
        )
        assert pressure_decision.status == "resolved"
        assert pressure_decision.value == "internal_pressure"
        assert pressure_decision.selected_node == case.branch_selected_node
        pending_ids = {item.node_id for item in traversal.pending_expansion_nodes}
        assert case.branch_selected_node not in pending_ids

    if case.label == "D":
        assert strategy.next_fields == []
        assert "internal_design_gage_pressure" not in strategy.next_fields
        for req_id in _EXTERNAL_INTERNAL_NOT_APPLICABLE_REQ_IDS:
            req = plan.requirements[req_id]
            assert req.activation_status == "not_applicable", req_id
            assert req.status == "not_applicable", req_id

    if case.nps_status is not None:
        assert plan.requirements["REQ-nominal_pipe_size"].status == case.nps_status
    if case.od_lookup_status is not None:
        assert plan.requirements["REQ-outside_diameter_lookup"].status == case.od_lookup_status

    if case.label in {"E", "F"}:
        assert plan.requirements["REQ-diameter_resolution"].status == "missing"
        if case.label == "E":
            assert "REQ-nominal_pipe_size" not in plan.root_goal.blocked_by
            assert "REQ-outside_diameter_lookup" not in plan.root_goal.blocked_by
        if case.label == "F":
            assert "REQ-nominal_pipe_size" in plan.root_goal.blocked_by
            assert "REQ-outside_diameter_lookup" in plan.root_goal.blocked_by

    if case.branch_selected_node and case.label in {"E", "F"}:
        pressure_decision = next(
            item for item in traversal.branch_decisions if item.field == "pressure_loading"
        )
        assert pressure_decision.selected_node == case.branch_selected_node


def test_direct_od_with_outside_diameter_resolves_diameter_requirement() -> None:
    _, _, plan = _build_plan_from_inputs(
        [
            straight_section_assumption(),
            internal_pressure_assumption(),
            _confirmed_input("d_input_mode", "direct_od"),
            _confirmed_input("outside_diameter", 10.0, unit="in"),
        ]
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    diameter = plan.requirements["REQ-diameter_resolution"]
    assert diameter.status == "resolved"
    assert "REQ-diameter_resolution" not in plan.root_goal.blocked_by


def test_diameter_input_mode_fact_alias_does_not_affect_plan() -> None:
    """UI/question field diameter_input_mode maps to runtime fact d_input_mode."""
    _, _, plan_with_alias = _build_plan_from_inputs(
        [
            straight_section_assumption(),
            internal_pressure_assumption(),
            _confirmed_input("diameter_input_mode", "nps_lookup"),
        ]
    )
    _, _, plan_with_canonical = _build_plan_from_inputs(
        [
            straight_section_assumption(),
            internal_pressure_assumption(),
            _confirmed_input("d_input_mode", "nps_lookup"),
        ]
    )

    assert plan_with_alias.requirements["REQ-nominal_pipe_size"].status == "not_applicable"
    assert plan_with_canonical.requirements["REQ-nominal_pipe_size"].status == "missing"


def test_bootstrap_task_state_exposes_fresh_canonical_engineering_plan(tmp_path: Path) -> None:
    """Case A via bootstrap → task_state API path."""
    root = Path(__file__).resolve().parents[2]
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("bootstrap-progression", status=TaskStatus.AWAITING_INPUT)
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)
    manager.replace_task(task.task_id, task)

    payload = task_state(task, manager, reader=reader, projection_mode="full")
    plan = payload.get("engineering_plan")
    assert isinstance(plan, dict)
    assert "requirements" in plan
    assert "REQ-straight_pipe_section" in plan["requirements"]
    assert plan["input_strategy"]["next_fields"] == ["straight_pipe_section"]
    assert plan["root_goal"]["blocked_by"] == [
        "REQ-straight_pipe_section",
        "REQ-pressure_loading",
    ]

    legacy = payload.get("legacy_goal_map")
    assert isinstance(legacy, dict)
    assert "GOAL-calculate-minimum-required-thickness" in legacy
    assert payload.get("goals") is None

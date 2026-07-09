"""Central phase and input strategy derivation."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_phases import derive_input_strategy, derive_plan_phases
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.planner.helpers import _reader
from tests.planner.plan_contract import PIPE_WALL_LOOKUP_IDS, WELD_W_FIELD
from engine.planner.graph_requirements import lookup_requirement_id


def _fresh_task():
    manager = TaskStateManager()
    task = manager.create_task("plan-phases", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    return task


def test_fresh_plan_phases_and_input_strategy() -> None:
    plan = build_engineering_plan(_fresh_task(), _reader())

    assert [phase.id for phase in plan.phases] == [
        "expansion_assumptions",
        "path_decisions",
        "parameter_gathering",
        "coefficient_resolution",
        "definition_equation_completion",
        "equation_execution",
        "reporting",
    ]
    assert [phase.order for phase in plan.phases] == [0, 1, 2, 3, 4, 5, 6]

    expansion = plan.phases[0]
    assert expansion.status == "active"
    assert expansion.requirement_ids == ["REQ-straight_pipe_section"]

    coefficient = plan.phases[3]
    assert coefficient.status == "blocked"
    assert coefficient.requirement_ids == [
        "REQ-pipe_construction_type",
        "REQ-metallurgical_group_lookup",
        "REQ-allowable_stress_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_joint_efficiency_lookup",
        lookup_requirement_id(WELD_W_FIELD),
    ]

    strategy = plan.input_strategy
    assert strategy is not None
    assert strategy.mode == "single_next_question"
    assert strategy.current_phase == "expansion_assumptions"
    assert strategy.next_fields == ["straight_pipe_section"]
    assert strategy.resolved_fields == []
    assert "pressure_loading" in strategy.blocked_fields
    assert "internal_design_gage_pressure" in strategy.blocked_fields
    assert "diameter_input_mode" in strategy.blocked_fields
    assert "allowable_stress" in strategy.blocked_fields
    assert "minimum_required_thickness" in strategy.blocked_fields
    assert "straight_pipe_section" not in strategy.blocked_fields


def test_derive_input_strategy_from_plan() -> None:
    plan = build_engineering_plan(_fresh_task(), _reader())
    derived = derive_input_strategy(plan)
    assert derived.next_fields == plan.input_strategy.next_fields
    assert derived.blocked_fields == plan.input_strategy.blocked_fields


def test_derive_plan_phases_skips_empty_validation() -> None:
    plan = build_engineering_plan(_fresh_task(), _reader())
    phases = derive_plan_phases(plan.requirements)
    assert all(phase.id != "validation" for phase in phases)

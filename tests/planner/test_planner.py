"""Planner layer tests."""

from __future__ import annotations

from pathlib import Path

from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, new_task, TaskStatus
from tests.acceptance.helpers import (
    confirmed_default_inputs,
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.helpers.facts import legacy_input, set_fact_from_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _store_input(state: TaskStateManager, task_id: str, inp: EngineeringInput) -> None:
    state.store_fact(
        task_id,
        fact_from_engineering_input(inp, task_id=task_id, workflow_id="pipe_wall_thickness_design"),
    )


def test_planner_pipe_wall_thickness_missing_inputs() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-thickness-plan", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(_reader(), state=state)

    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)

    assert plan.selected_root == "pipe_wall_thickness_design"
    assert any(
        node_id in plan.selected_nodes
        for node_id in ("asme-b313-table-A-1", "B313-lookup-allowable-stress", "B313-param-S")
    )
    assert "304.1.2-a" not in plan.selected_nodes
    assert "straight_pipe_section" in plan.missing_assumptions or (
        "straight_pipe_section" in (plan.phase_missing.get("expansion_assumptions") or [])
    )
    assert "pressure_loading" in plan.missing_assumptions or (
        "pressure_loading" in (plan.phase_missing.get("path_decisions") or [])
    )
    assert plan.missing_inputs == []
    assert plan.action == AgentAction.REQUEST_INPUT
    assert planning_projection(task)


def test_planner_does_not_execute_calculations() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-thickness-no-exec", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    planner.plan(intent, task)

    assert "required_thickness" not in task.outputs
    assert "_execution_trace" not in task.outputs


def test_planner_expands_external_pressure_path() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-external", status=TaskStatus.AWAITING_INPUT)
    _store_input(state, "pipe-wall-external", straight_section_assumption())
    _store_input(
        state,
        "pipe-wall-external",
        legacy_input(
            input_id="pressure_loading",
            value="external_pressure",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    task = state.get_task("pipe-wall-external")
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)

    assert plan.action == AgentAction.REQUEST_INPUT
    assert "B313-304.1.3" in plan.selected_nodes
    assert "304.1.2-a" not in plan.selected_nodes
    assert plan.path_decision == {
        "field": "pressure_loading",
        "value": "external_pressure",
        "selected_node": "B313-304.1.3",
    }


def test_planner_requests_default_confirmations_for_internal_path() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-defaults", status=TaskStatus.AWAITING_INPUT)
    _store_input(state, "pipe-wall-defaults", straight_section_assumption())
    _store_input(state, "pipe-wall-defaults", internal_pressure_assumption())
    _store_input(
        state,
        "pipe-wall-defaults",
        legacy_input("design_pressure", 500, "psi", source=InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-defaults",
        EngineeringInput(
            "d_input_mode", "direct_od", "dimensionless", InputSource.USER, status=InputStatus.CONFIRMED
        ),
    )
    _store_input(
        state,
        "pipe-wall-defaults",
        EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-defaults",
        EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-defaults",
        EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    )
    task = state.get_task("pipe-wall-defaults")
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)

    assert "weld_joint_efficiency" in plan.missing_execution_assumptions
    assert plan.action == AgentAction.REQUEST_INPUT


def test_planner_proposes_path_when_defaults_confirmed() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-ready", status=TaskStatus.AWAITING_INPUT)
    _store_input(state, "pipe-wall-ready", straight_section_assumption())
    _store_input(state, "pipe-wall-ready", internal_pressure_assumption())
    for engineering_input in confirmed_default_inputs().values():
        _store_input(state, "pipe-wall-ready", engineering_input)
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput(
            "d_input_mode",
            "direct_od",
            "dimensionless",
            InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput("design_pressure", 500, "psi", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput(
            input_id="joint_category",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    _store_input(
        state,
        "pipe-wall-ready",
        EngineeringInput(
            input_id="corrosion_allowance",
            value=0.5,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    task = state.get_task("pipe-wall-ready")
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)

    assert plan.action == AgentAction.PROPOSE_PATH
    assert "304.1.2-a" in plan.selected_nodes


def test_planner_ambiguous_integrity_request() -> None:
    state = TaskStateManager()
    task = new_task("ambiguous", status=TaskStatus.ACTIVE)
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent=None,
        domain="piping",
        confidence=0.3,
    )

    plan = planner.plan(intent, task, user_message="verify pipe integrity")

    assert plan.action == AgentAction.CLARIFY
    assert plan.alternative_paths

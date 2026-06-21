"""Tests for calculation-node formula parameter prompts."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.formula_parameter_prompt import (
    build_formula_parameter_prompt,
    classify_formula_parameters,
)
from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.input import EngineeringInput, InputSource, InputStatus
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task, TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def _plan_with_internal_pressure() -> NavigationPlan:
    state = TaskStateManager()
    task = state.create_task("formula-prompt-plan", status=TaskStatus.AWAITING_INPUT)
    state.store_input(task.task_id, straight_section_assumption())
    state.store_input(task.task_id, internal_pressure_assumption())
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )
    return planner.plan(intent, state.get_task(task.task_id))


def test_prompt_not_shown_during_expansion_assumptions() -> None:
    reader = _reader()
    task = Task(task_id="t1", status=TaskStatus.AWAITING_INPUT)
    plan = NavigationPlan(
        current_phase=NavigationPhase.EXPANSION_ASSUMPTIONS,
        selected_nodes=["B313-304.1.1"],
        missing_inputs=["straight_pipe_section"],
    )
    assert build_formula_parameter_prompt(reader=reader, task=task, navigation_plan=plan) is None


def test_prompt_shows_formula_and_missing_parameters() -> None:
    reader = _reader()
    plan = _plan_with_internal_pressure()
    task = Task(
        task_id="formula-prompt",
        status=TaskStatus.AWAITING_INPUT,
        inputs={
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=8.0,
                unit="bar",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
                original_value=8.0,
                original_unit="bar",
            ),
        },
    )

    prompt = build_formula_parameter_prompt(
        reader=reader,
        task=task,
        navigation_plan=plan,
        missing_input_ids=plan.missing_inputs,
    )

    assert prompt is not None
    assert "Formula:" in prompt
    assert "t = PD" in prompt
    assert "Known parameters:" in prompt
    assert "Missing parameters:" in prompt
    assert "P" in prompt
    assert "Value: 8 bar" in prompt
    assert "D" in prompt
    assert "Description:" in prompt
    assert "symbol-labeled values" in prompt.lower()


def test_classify_marks_unconfirmed_defaults_as_missing() -> None:
    reader = _reader()
    known, missing = classify_formula_parameters(
        reader,
        "B313-304.1.2",
        task_inputs={
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=500.0,
                unit="psi",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "nominal_pipe_size": EngineeringInput(
                input_id="nominal_pipe_size",
                value="10",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "d_input_mode": EngineeringInput(
                input_id="d_input_mode",
                value="nps_lookup",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "material": EngineeringInput(
                input_id="material",
                value="SA-106B",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                input_id="design_temperature",
                value=200.0,
                unit="F",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "weld_joint_efficiency": EngineeringInput(
                input_id="weld_joint_efficiency",
                value=1.0,
                unit="dimensionless",
                source=InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default=1.0,
                requires_confirmation=True,
            ),
        },
        missing_input_ids=["weld_joint_efficiency", "weld_strength_reduction", "temperature_coefficient"],
    )

    known_symbols = {item.symbol for item in known}
    missing_symbols = {item.symbol for item in missing}
    assert "P" in known_symbols
    assert "D" in known_symbols
    assert "E" in missing_symbols


def test_planner_phase_reaches_parameter_gathering() -> None:
    plan = _plan_with_internal_pressure()
    assert plan.current_phase == NavigationPhase.PARAMETER_GATHERING
    assert plan.action == AgentAction.REQUEST_INPUT
    assert "design_pressure" in (
        plan.missing_inputs
        + (plan.phase_missing.get(NavigationPhase.PARAMETER_GATHERING.value) or [])
    )

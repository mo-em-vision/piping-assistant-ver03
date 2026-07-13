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
from models.task import Task, new_task, TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.helpers.facts import legacy_input, populate_task_facts, facts_from_inputs
from engine.state.fact_migration import fact_from_engineering_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _plan_with_internal_pressure() -> NavigationPlan:
    state = TaskStateManager()
    task = state.create_task("formula-prompt-plan", status=TaskStatus.AWAITING_INPUT)
    state.store_input(task.task_id, fact_from_engineering_input(straight_section_assumption(), task_id=task.task_id))
    state.store_input(task.task_id, fact_from_engineering_input(internal_pressure_assumption(), task_id=task.task_id))
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
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)
    plan = NavigationPlan(
        current_phase=NavigationPhase.EXPANSION_ASSUMPTIONS,
        selected_nodes=["B313-304.1.1"],
        missing_inputs=["straight_pipe_section"],
    )
    assert build_formula_parameter_prompt(reader=reader, task=task, navigation_plan=plan) is None


def test_prompt_shows_formula_and_missing_parameters() -> None:
    reader = _reader()
    plan = _plan_with_internal_pressure()
    task = new_task(
        "formula-prompt",
        status=TaskStatus.AWAITING_INPUT,
    )
    populate_task_facts(
        task,
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
            "internal_design_gage_pressure": legacy_input(
                "internal_design_gage_pressure",
                8.0,
                "bar",
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
        "304.1.2-a",
        task_inputs=facts_from_inputs(
            {
                "internal_design_gage_pressure": legacy_input("internal_design_gage_pressure", 500.0, "psi"),
                "nominal_pipe_size": legacy_input("nominal_pipe_size", "10"),
                "d_input_mode": legacy_input("d_input_mode", "nps_lookup"),
                "material": legacy_input("material", "SA-106B"),
                "design_temperature": legacy_input("design_temperature", 200.0, "F"),
                "weld_joint_efficiency": legacy_input(
                    "weld_joint_efficiency",
                    1.0,
                    source=InputSource.DEFAULT,
                    status=InputStatus.PROPOSED_DEFAULT,
                    default=1.0,
                    requires_confirmation=True,
                ),
            },
            task_id="classify-test",
        ),
        missing_input_ids=["weld_joint_efficiency", "weld_joint_strength_reduction_factor_W", "temperature_coefficient_Y"],
    )

    known_symbols = {item.symbol for item in known}
    missing_symbols = {item.symbol for item in missing}
    assert "P" in known_symbols
    assert "D" in known_symbols
    assert "E_j" in missing_symbols


def test_planner_phase_reaches_parameter_gathering() -> None:
    plan = _plan_with_internal_pressure()
    assert plan.current_phase in (
        NavigationPhase.PARAMETER_GATHERING,
        NavigationPhase.COEFFICIENT_RESOLUTION,
    )
    assert plan.action == AgentAction.REQUEST_INPUT
    if plan.current_phase == NavigationPhase.COEFFICIENT_RESOLUTION:
        coeff_missing = plan.phase_missing.get(NavigationPhase.COEFFICIENT_RESOLUTION.value) or []
        assert "pipe_construction_type" in coeff_missing or "joint_category" in coeff_missing
        assert "weld_joint_efficiency" not in coeff_missing
    else:
        gathering_missing = plan.phase_missing.get(NavigationPhase.PARAMETER_GATHERING.value) or []
        combined = set(plan.missing_inputs + gathering_missing)
        assert combined
        assert "weld_joint_efficiency" not in combined
        assert "allowable_stress" not in combined

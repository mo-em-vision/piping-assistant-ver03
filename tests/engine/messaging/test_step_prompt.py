"""Tests for deterministic step prompts (assumptions and path decisions)."""

from __future__ import annotations

from pathlib import Path

from engine.messaging.step_prompt import build_step_prompt
from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import IntentResult
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task, new_task, TaskStatus
from tests.acceptance.helpers import straight_section_assumption
from engine.state.fact_migration import fact_from_engineering_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[3]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_straight_pipe_prompt_is_deterministic() -> None:
    reader = _reader()
    state = TaskStateManager()
    task = state.create_task("step-prompt", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(reader, state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )
    plan = planner.plan(intent, state.get_task(task.task_id))

    prompt = build_step_prompt(
        reader=reader,
        task=state.get_task(task.task_id),
        navigation_plan=plan,
        missing_input_ids=["straight_pipe_section"],
    )

    assert prompt is not None
    assert "straight pipe" in prompt.lower()
    assert "choose one" in prompt.lower()
    assert "1." in prompt
    assert plan.current_phase == NavigationPhase.EXPANSION_ASSUMPTIONS


def test_pressure_design_case_prompt_lists_numbered_options() -> None:
    reader = _reader()
    state = TaskStateManager()
    task = state.create_task("step-decision", status=TaskStatus.AWAITING_INPUT)
    state.store_input(task.task_id, fact_from_engineering_input(straight_section_assumption(), task_id=task.task_id))
    planner = Planner(reader, state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )
    plan = planner.plan(intent, state.get_task(task.task_id))

    prompt = build_step_prompt(
        reader=reader,
        task=state.get_task(task.task_id),
        navigation_plan=plan,
        missing_input_ids=["pressure_design_case"],
    )

    assert prompt is not None
    assert "1." in prompt
    assert "2." in prompt
    assert "internal pressure" in prompt.lower()
    assert "external pressure" in prompt.lower()
    assert plan.current_phase == NavigationPhase.PATH_DECISIONS


def test_formula_prompt_not_used_during_assumption_phase() -> None:
    reader = _reader()
    task = new_task("t1", status=TaskStatus.AWAITING_INPUT)
    plan = NavigationPlan(
        current_phase=NavigationPhase.EXPANSION_ASSUMPTIONS,
        selected_nodes=["B313-304.1.1"],
        phase_missing={NavigationPhase.EXPANSION_ASSUMPTIONS.value: ["straight_pipe_section"]},
    )
    assert build_step_prompt(reader=reader, task=task, navigation_plan=plan) is not None

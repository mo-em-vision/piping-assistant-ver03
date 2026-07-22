"""Tests for graph_navigation derived from engineering plans."""

from __future__ import annotations

from pathlib import Path

from api.workflow_bootstrap import bootstrap_new_task, refresh_task_planning
from config.loader import CLIConfig
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.graph_navigation import (
    build_graph_navigation_from_plan,
    unique_stable,
    validate_graph_navigation,
)
from engine.planner.plan_validation import validate_engineering_plan
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_task():
    state = TaskStateManager()
    task = state.create_task("graph-nav-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return state, task


def test_unique_stable_deduplicates_preserving_order() -> None:
    assert unique_stable(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_fresh_pipe_wall_graph_navigation_from_plan() -> None:
    _, task = _fresh_task()
    plan = build_engineering_plan(task, _reader())
    assert validate_engineering_plan(plan).valid

    nav = build_graph_navigation_from_plan(plan)
    assert not validate_graph_navigation(nav)

    assert nav["current_phase"] == "expansion_assumptions"
    assert nav["missing_expansion_assumptions"] == ["straight_pipe_section"]
    assert nav["missing_path_decisions"] == ["pressure_design_case"]
    assert nav["missing_user_inputs"] == []
    assert nav["missing_coefficient_inputs"] == []
    assert nav["missing_execution_assumptions"] == []
    assert nav["active_field"] == "straight_pipe_section"
    assert nav["active_requirement_id"] == "REQ-straight_pipe_section"
    assert "pressure_design_case" not in nav["missing_expansion_assumptions"]
    assert "straight_pipe_section" not in nav["missing_path_decisions"]

    phase_missing = nav["phase_missing"]
    assert phase_missing["expansion_assumptions"] == ["straight_pipe_section"]
    assert phase_missing["path_decisions"] == ["pressure_design_case"]
    parameter_gathering = phase_missing["parameter_gathering"]
    assert "material_grade" in parameter_gathering
    assert "design_temperature" in parameter_gathering
    # corrosion_allowance uses ask_later — excluded from phase_missing until equation phase
    assert "corrosion_allowance" not in parameter_gathering
    assert (
        "pipe_construction_type" in phase_missing.get("coefficient_resolution", [])
        or "pipe_construction_type" in parameter_gathering
    )
    assert phase_missing["equation_execution"] == []
    assert phase_missing["validation"] == []
    assert phase_missing["reporting"] == []


def test_straight_pipe_resolved_graph_navigation_advances_path_decision() -> None:
    state, task = _fresh_task()
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = state.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
    nav = build_graph_navigation_from_plan(plan)

    assert nav["current_phase"] == "path_decisions"
    assert nav["missing_expansion_assumptions"] == []
    assert nav["missing_path_decisions"] == ["pressure_design_case"]
    assert nav["active_field"] == "pressure_design_case"
    assert nav["active_requirement_id"] == "REQ-pressure_design_case"


def test_gates_resolved_graph_navigation_collects_parameter_gathering() -> None:
    state, task = _fresh_task()
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        state.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = state.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
    nav = build_graph_navigation_from_plan(plan)

    assert nav["current_phase"] == "parameter_gathering"
    assert nav["missing_user_inputs"] == ["design_temperature"]
    assert nav["active_field"] == "design_temperature"
    assert nav["missing_coefficient_inputs"] == []


def test_bootstrap_stores_engineering_plan_not_navigation_caches(tmp_path: Path) -> None:
    from engine.planner.graph_navigation import build_graph_navigation_from_plan, validate_graph_navigation
    from engine.planner.plan_selection import engineering_plan_for_task

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
    state = TaskStateManager()
    task = state.create_task("graph-nav-bootstrap", status=TaskStatus.AWAITING_INPUT)
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)

    assert "graph_navigation" not in task.outputs
    assert "engineering_plan_view" not in task.outputs
    plan = engineering_plan_for_task(task)
    assert plan is not None
    nav = build_graph_navigation_from_plan(plan)
    assert nav.get("active_field") == "straight_pipe_section"
    assert not validate_graph_navigation(nav)

    refresh_task_planning(task, _reader(), propose_defaults=False)
    assert "graph_navigation" not in task.outputs
    nav = build_graph_navigation_from_plan(engineering_plan_for_task(task))
    assert nav.get("current_phase") == "expansion_assumptions"

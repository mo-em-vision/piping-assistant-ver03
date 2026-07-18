"""Acceptance criteria §1–§2 and §25 — MVP workflow and final checklist."""

from __future__ import annotations

import pytest

from engine.executor.executor import execute_workflow
from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.reports.report_data import build_report_from_task
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.execution import ExecutionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    WALL_THICKNESS_NODE,
    create_task_with_inputs,
    internal_pressure_assumption,
    pipe_thickness_intent,
    plan_pipe_thickness,
    run_completed_workflow,
    sample_inputs,
    straight_section_assumption,
)
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


class TestMvpDefinition:
    """§1 MVP Definition — ASME B31.3 pipe wall thickness workflow."""

    def test_workflow_root_is_implemented(self, standards_reader) -> None:
        root = standards_reader.load(PIPE_WALL_THICKNESS_ROOT)
        assert root.metadata.get("engineering_intent") == PIPE_WALL_THICKNESS_ROOT
        depends_on = root.metadata.get("depends_on", [])
        dep_ids = [
            dep.get("node_id") if isinstance(dep, dict) else str(dep)
            for dep in depends_on
        ]
        assert "B313-304.1.1" in dep_ids or "B313-304.1.1" in root.depends_on

    def test_workflow_includes_calculation_and_lookup_nodes(self, standards_reader) -> None:
        plan = GraphEngine().build_plan(
            task_id="acceptance-mvp-nodes",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs={"pressure_design_case": internal_pressure_assumption()},
            reader=standards_reader,
        )
        assert MATERIAL_STRESS_NODE in plan.nodes
        assert WALL_THICKNESS_NODE in plan.nodes


class TestMvpReleaseGoal:
    """§2 MVP Release Goal — architecture flow Intent → Planner → Graph → Validation → Execution → Report."""

    def test_architecture_flow_produces_explainable_result(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task_id = "pipe-wall-thickness-design-acceptance-flow"
        task = create_task_with_inputs(state_manager, task_id)

        navigation = plan_pipe_thickness(standards_reader, state_manager, task)
        assert navigation.selected_root == PIPE_WALL_THICKNESS_ROOT
        assert WALL_THICKNESS_NODE in navigation.selected_nodes

        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.COMPLETED

        task = state_manager.get_task(task_id)
        report = build_report_from_task(task, standards_reader, user_request="Calculate pipe thickness")

        assert report.traversal
        assert report.sections
        assert report.traceability
        assert task.outputs.get("required_thickness") is not None
        assert task.outputs.get("_execution_trace")
        assert task.outputs.get("_validation_trace")


CHECKLIST_CRITERIA = [
    ("user_request_reaches_planner", "§25 User request reaches Planner"),
    ("planner_creates_correct_task", "§25 Planner creates correct task"),
    ("graph_finds_required_nodes", "§25 Graph finds required nodes"),
    ("dependencies_are_resolved", "§25 Dependencies are resolved"),
    ("validation_catches_problems", "§25 Validation catches problems"),
    ("execution_is_deterministic", "§25 Execution produces deterministic results"),
    ("trace_is_stored", "§25 Trace is stored"),
    ("reports_are_generated", "§25 Reports are generated"),
    ("state_can_resume", "§25 State can resume tasks"),
    ("changed_inputs_branch", "§25 Changed inputs create new branches"),
    ("results_are_reproducible", "§25 Results are reproducible"),
]


@pytest.mark.parametrize("criterion_id,description", CHECKLIST_CRITERIA, ids=[item[0] for item in CHECKLIST_CRITERIA])
def test_mvp_acceptance_checklist(
    criterion_id: str,
    description: str,
    standards_reader,
    state_manager,
    tmp_path,
) -> None:
    """§25 Final MVP Acceptance Checklist — one test per criterion."""
    if criterion_id == "user_request_reaches_planner":
        task = state_manager.create_task("acceptance-checklist-planner", status=TaskStatus.AWAITING_INPUT)
        plan = Planner(standards_reader, state=state_manager).plan(
            pipe_thickness_intent(),
            task,
            user_message="Calculate pipe thickness",
        )
        assert plan.selected_root == PIPE_WALL_THICKNESS_ROOT

    elif criterion_id == "planner_creates_correct_task":
        task = state_manager.create_task("acceptance-checklist-plan", status=TaskStatus.AWAITING_INPUT)
        plan = plan_pipe_thickness(standards_reader, state_manager, task)
        stored = state_manager.get_task(task.task_id)
        assert plan.missing_assumptions or plan.phase_missing.get("expansion_assumptions")
        assert planning_projection(stored)

    elif criterion_id == "graph_finds_required_nodes":
        plan = GraphEngine().build_plan(
            task_id="acceptance-checklist-graph",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs={
                "straight_pipe_section": straight_section_assumption(),
                "pressure_design_case": internal_pressure_assumption(),
            },
            reader=standards_reader,
        )
        assert MATERIAL_STRESS_NODE in plan.nodes
        assert WALL_THICKNESS_NODE in plan.nodes

    elif criterion_id == "dependencies_are_resolved":
        plan = GraphEngine().build_plan(
            task_id="acceptance-checklist-deps",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=sample_inputs(),
            reader=standards_reader,
        )
        assert plan.execution_order.index(MATERIAL_STRESS_NODE) < plan.execution_order.index(
            WALL_THICKNESS_NODE
        )
        assert plan.dependencies

    elif criterion_id == "validation_catches_problems":
        from models.input import EngineeringInput, InputSource

        task_id = "acceptance-checklist-validation"
        state_manager.create_task(task_id)
        for key, value in sample_inputs().items():
            if key == "design_pressure":
                state_manager.store_input(
                    task_id,
                    EngineeringInput(
                        input_id="design_pressure",
                        value="abc",
                        unit="psi",
                        source=InputSource.USER,
                    ),
                )
            else:
                state_manager.store_input(task_id, value)
        result = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert result.status == ExecutionStatus.ERROR

    elif criterion_id == "execution_is_deterministic":
        first = run_completed_workflow(
            state_manager,
            standards_reader,
            "acceptance-checklist-exec-a",
        )
        second = run_completed_workflow(
            TaskStateManager(),
            standards_reader,
            "acceptance-checklist-exec-b",
        )
        assert first.status == ExecutionStatus.COMPLETED
        assert second.status == ExecutionStatus.COMPLETED
        assert first.node_results[-1].outputs.get("required_thickness") == second.node_results[-1].outputs.get(
            "required_thickness"
        )

    elif criterion_id == "trace_is_stored":
        task_id = "acceptance-checklist-trace"
        run_completed_workflow(state_manager, standards_reader, task_id)
        task = state_manager.get_task(task_id)
        assert isinstance(task.outputs.get("_execution_trace"), list)
        assert isinstance(task.outputs.get("_validation_trace"), list)

    elif criterion_id == "reports_are_generated":
        task_id = "pipe-wall-thickness-design-acceptance-checklist-report"
        run_completed_workflow(state_manager, standards_reader, task_id)
        from engine.reports.report_generator import ReportGenerator

        report = build_report_from_task(state_manager.get_task(task_id), standards_reader)
        storage = ReportGenerator(standards_reader.standards_root).generate(
            report,
            tmp_path,
            formats=("markdown", "html", "pdf"),
        )
        assert storage.markdown_path
        assert storage.html_path

    elif criterion_id == "state_can_resume":
        task_id = "acceptance-checklist-resume"
        state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        state_manager.store_input(task_id, sample_inputs()["internal_design_gage_pressure"])
        paused = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert paused.status == ExecutionStatus.AWAITING_INPUT
        for engineering_input in sample_inputs().values():
            state_manager.store_input(task_id, engineering_input)
        resumed = execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=state_manager, reader=standards_reader)
        assert resumed.status == ExecutionStatus.COMPLETED

    elif criterion_id == "changed_inputs_branch":
        task_id = "acceptance-checklist-branch"
        run_completed_workflow(state_manager, standards_reader, task_id)
        first_stress = state_manager.get_task(task_id).outputs["allowable_stress"]
        state_manager.store_input(
            task_id,
            sample_inputs(temperature=400)["design_temperature"],
        )
        assert state_manager.get_task(task_id).conflicts
        run_completed_workflow(state_manager, standards_reader, task_id)
        second_stress = state_manager.get_task(task_id).outputs["allowable_stress"]
        assert first_stress != second_stress

    elif criterion_id == "results_are_reproducible":
        outputs_a = run_completed_workflow(
            TaskStateManager(),
            standards_reader,
            "acceptance-checklist-repro-a",
        )
        outputs_b = run_completed_workflow(
            TaskStateManager(),
            standards_reader,
            "acceptance-checklist-repro-b",
        )
        assert outputs_a.node_results[-1].outputs["required_thickness"] == outputs_b.node_results[-1].outputs[
            "required_thickness"
        ]

    else:
        pytest.fail(f"Unhandled checklist criterion: {criterion_id}")

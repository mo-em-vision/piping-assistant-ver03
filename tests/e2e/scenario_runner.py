"""Run engineering scenarios through planner, graph, validation, execution, and report."""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.executor.executor import execute_workflow
from engine.executor.unit_manager import convert_to_si
from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.reports.formatters import render_markdown
from engine.reports.report_data import build_report_from_task
from engine.reports.report_generator import ReportGenerator
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.agent import IntentResult
from models.execution import ExecutionPlan, ExecutionResult, ExecutionStatus
from tests.helpers.facts import fact_get_unit, fact_get_value, legacy_input
from models.planning import NavigationPlan
from models.task import Task, TaskStatus
from models.validation import ComplianceStatus

from tests.e2e.assertions import (
    assert_compliance_status,
    assert_conflict,
    assert_contains,
    assert_execution_status,
    assert_output_value,
    assert_task_status,
    assert_validation_rules,
)
from tests.e2e.scenario_loader import Scenario


@dataclass
class WorkflowSnapshot:
    navigation_plan: NavigationPlan | None = None
    execution_plan: ExecutionPlan | None = None
    validation_status: ComplianceStatus | None = None
    execution_result: ExecutionResult | None = None
    task: Task | None = None
    report_status: str | None = None
    report_markdown: str | None = None
    report_data: Any | None = None


@dataclass
class ScenarioRunResult:
    scenario: Scenario
    snapshots: list[WorkflowSnapshot] = field(default_factory=list)

    @property
    def final(self) -> WorkflowSnapshot:
        return self.snapshots[-1]


def expected_wall_thickness(task: Task) -> float:
    """Compute expected t from stored task outputs and inputs."""
    p_pa, _ = convert_to_si(float(fact_get_value(task, "design_pressure")), fact_get_unit(task, "design_pressure"))
    d_mm, _ = convert_to_si(float(fact_get_value(task, "outside_diameter")), fact_get_unit(task, "outside_diameter"))
    s_pa = float(task.outputs.get("allowable_stress", task.outputs.get("S", 0)))
    e = 1.0
    w = 1.0
    y = 0.4
    sew = s_pa * e * w
    py = p_pa * y
    return p_pa * d_mm / (2 * (sew + py))


class ScenarioRunner:
    """Run a declarative scenario against the engineering workflow stack."""

    def __init__(
        self,
        reader: StandardsReader,
        *,
        state: TaskStateManager | None = None,
    ) -> None:
        self.reader = reader
        self.state = state or TaskStateManager()
        self.planner = Planner(reader, state=self.state)
        self.graph = GraphEngine()
        self.validation = ValidationEngine(reader)

    def run(self, scenario: Scenario) -> ScenarioRunResult:
        self.state = TaskStateManager()
        self.planner = Planner(self.reader, state=self.state)

        task_id = f"pipe-wall-thickness-design-{scenario.name}-{uuid.uuid4().hex[:8]}"
        self.state.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        self._apply_given(scenario, task_id)

        result = ScenarioRunResult(scenario=scenario)

        if scenario.steps:
            for step in scenario.steps:
                snapshot = self._execute_step(scenario, task_id, step)
                result.snapshots.append(snapshot)
                step_expect = step.get("expect")
                if step_expect:
                    self._assert_expectations(scenario.name, snapshot, step_expect)
        else:
            snapshot = self._run_full_pipeline(scenario, task_id)
            result.snapshots.append(snapshot)

        self._assert_expectations(scenario.name, result.final, scenario.expected)
        self._assert_determinism(scenario)
        return result

    def _apply_given(self, scenario: Scenario, task_id: str) -> None:
        given = scenario.given
        for input_id, spec in given.get("inputs", {}).items():
            self.state.store_input(
                task_id,
                fact_from_engineering_input(
                    _engineering_input(input_id, spec),
                    task_id=task_id,
                ),
            )

        overrides = given.get("validation_overrides")
        if overrides:
            task = self.state.get_task(task_id)
            task.outputs["validation_overrides"] = list(overrides)

    def _execute_step(self, scenario: Scenario, task_id: str, step: dict[str, Any]) -> WorkflowSnapshot:
        action = step.get("action")
        if action == "execute":
            return self._run_full_pipeline(scenario, task_id, include_planner=False)
        if action == "update_input":
            for input_id, spec in step.get("inputs", {}).items():
                self.state.store_input(
                    task_id,
                    fact_from_engineering_input(
                        _engineering_input(input_id, spec),
                        task_id=task_id,
                    ),
                )
            return self._snapshot_task(task_id)
        raise ValueError(f"Unknown scenario step action: {action}")

    def _run_full_pipeline(
        self,
        scenario: Scenario,
        task_id: str,
        *,
        include_planner: bool = True,
    ) -> WorkflowSnapshot:
        snapshot = WorkflowSnapshot()
        task = self.state.get_task(task_id)
        when = scenario.when
        user_request = str(when.get("user_request", ""))

        if include_planner:
            intent_data = when.get("intent", {})
            intent = IntentResult(
                intent=intent_data.get("intent"),
                domain=intent_data.get("domain"),
                workflow=intent_data.get("workflow"),
                confidence=float(intent_data.get("confidence", 0.9)),
            )
            snapshot.navigation_plan = self.planner.plan(intent, task, user_message=user_request)

        task = self.state.get_task(task_id)
        root = (
            snapshot.navigation_plan.selected_root
            if snapshot.navigation_plan and snapshot.navigation_plan.selected_root
            else "pipe_wall_thickness_design"
        )

        plan = self.graph.build_plan(
            task_id=task_id,
            root_id=root,
            inputs=dict(task.fact_store.active_facts()),
            reader=self.reader,
        )
        snapshot.execution_plan = plan

        validation = self.validation.validate_plan(plan, task)
        snapshot.validation_status = validation.status

        snapshot.execution_result = execute_workflow(
            task_id,
            root,
            state=self.state,
            reader=self.reader,
        )
        task = self.state.get_task(task_id)
        snapshot.task = task

        report = build_report_from_task(task, self.reader, user_request=user_request)
        snapshot.report_data = report
        snapshot.report_status = report.status
        snapshot.report_markdown = render_markdown(report)
        return snapshot

    def _snapshot_task(self, task_id: str) -> WorkflowSnapshot:
        return WorkflowSnapshot(task=self.state.get_task(task_id))

    def _assert_determinism(self, scenario: Scenario) -> None:
        determinism = scenario.expected.get("determinism")
        if not determinism:
            return

        repeat = int(determinism.get("repeat", 2))
        compare_keys = list(determinism.get("compare", []))
        baseline = self.run(_clone_scenario_for_determinism(scenario))

        for _ in range(repeat - 1):
            candidate = self.run(_clone_scenario_for_determinism(scenario))
            for key in compare_keys:
                left = baseline.final.task.outputs.get(key) if baseline.final.task else None
                right = candidate.final.task.outputs.get(key) if candidate.final.task else None
                if key == "_execution_trace":
                    left = _normalize_trace(left)
                    right = _normalize_trace(right)
                if left != right:
                    from tests.e2e.assertions import _fail

                    _fail(
                        scenario.name,
                        "Determinism",
                        f"Repeated run mismatch for {key!r}",
                        trace={"baseline": left, "candidate": right},
                    )

    def _assert_expectations(
        self,
        scenario_name: str,
        snapshot: WorkflowSnapshot,
        expected: dict[str, Any],
    ) -> None:
        if planner_exp := expected.get("planner"):
            self._assert_planner(scenario_name, snapshot, planner_exp)

        if graph_exp := expected.get("graph"):
            self._assert_graph(scenario_name, snapshot, graph_exp)

        if validation_exp := expected.get("validation"):
            self._assert_validation(scenario_name, snapshot, validation_exp)

        if execution_exp := expected.get("execution"):
            self._assert_execution(scenario_name, snapshot, execution_exp)

        if state_exp := expected.get("state"):
            self._assert_state(scenario_name, snapshot, state_exp)

        if report_exp := expected.get("report"):
            self._assert_report(scenario_name, snapshot, report_exp)

    def _assert_planner(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        plan = snapshot.navigation_plan
        if plan is None:
            return

        if root := expected.get("selected_root"):
            assert plan.selected_root == root, f"{scenario}: planner root mismatch"

        if nodes := expected.get("selected_nodes_contains"):
            assert_contains(plan.selected_nodes, nodes, scenario=scenario, component="Planner")

        if missing := expected.get("missing_inputs"):
            assert plan.missing_inputs == missing, f"{scenario}: planner missing_inputs mismatch"

        if missing := expected.get("missing_inputs_contains"):
            assert_contains(plan.missing_inputs, missing, scenario=scenario, component="Planner")

        if missing := expected.get("missing_assumptions_contains"):
            assert_contains(plan.missing_assumptions, missing, scenario=scenario, component="Planner")

    def _assert_graph(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        plan = snapshot.execution_plan
        if plan is None:
            return

        exec_nodes = [
            node_id
            for node_id in plan.execution_order
            if str(self.reader.load(node_id).metadata.get("type", "")) not in {"root", "definition"}
        ]

        if order := expected.get("execution_order"):
            assert exec_nodes == order, (
                f"{scenario}: graph execution order mismatch: {exec_nodes} != {order}"
            )

        if nodes := expected.get("nodes_contains"):
            assert_contains(list(plan.nodes), nodes, scenario=scenario, component="Graph Engine")

    def _assert_validation(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        if status := expected.get("plan_status"):
            if snapshot.validation_status is not None:
                assert_compliance_status(snapshot.validation_status, status, scenario=scenario)

        if rules := expected.get("error_rules_contains"):
            task = snapshot.task or WorkflowSnapshot().task
            trace = []
            if snapshot.task:
                trace = snapshot.task.outputs.get("_validation_trace", [])
            assert_validation_rules(trace, rules, scenario=scenario)

    def _assert_execution(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        if status := expected.get("status"):
            assert snapshot.execution_result is not None
            assert_execution_status(snapshot.execution_result.status, status, scenario=scenario)

        task = snapshot.task
        if task and (outputs := expected.get("outputs")):
            for key, value in outputs.items():
                assert_output_value(task, key, value, scenario=scenario)

    def _assert_state(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        task = snapshot.task
        if task is None:
            return

        if status := expected.get("status"):
            assert_task_status(task.status, status, scenario=scenario)

        if expected.get("has_execution_trace"):
            assert "_execution_trace" in task.outputs, f"{scenario}: missing execution trace"

        if expected.get("has_validation_trace"):
            assert "_validation_trace" in task.outputs, f"{scenario}: missing validation trace"

        if expected.get("warnings_present"):
            assert task.warnings, f"{scenario}: expected warnings on task"

        if conflict := expected.get("conflicts_contains"):
            assert_conflict(task, conflict, scenario=scenario)

    def _assert_report(self, scenario: str, snapshot: WorkflowSnapshot, expected: dict[str, Any]) -> None:
        if status := expected.get("status"):
            assert snapshot.report_status == status, (
                f"{scenario}: report status {snapshot.report_status!r} != {status!r}"
            )

        report = snapshot.report_data
        if report is None:
            return

        if sections := expected.get("sections_contain"):
            section_nodes = [section.node for section in report.sections]
            assert_contains(section_nodes, sections, scenario=scenario, component="Report Generator")

        if missing := expected.get("missing_inputs_contains"):
            assert_contains(report.missing_inputs, missing, scenario=scenario, component="Report Generator")

        if expected.get("has_traversal"):
            assert report.traversal, f"{scenario}: report missing traversal"

        if expected.get("has_calculation_trace"):
            assert report.traceability, f"{scenario}: report missing traceability"

        if phrases := expected.get("markdown_contains"):
            markdown = snapshot.report_markdown or ""
            for phrase in phrases:
                assert phrase in markdown, f"{scenario}: report markdown missing {phrase!r}"


def _engineering_input(input_id: str, spec: dict[str, Any]):
    value = spec["value"]
    unit = str(spec.get("unit", "dimensionless"))
    return legacy_input(
        input_id,
        value,
        unit,
        original_value=value if isinstance(value, (int, float)) else None,
        original_unit=unit if unit != "dimensionless" else None,
    )


def _clone_scenario_for_determinism(scenario: Scenario) -> Scenario:
    cloned = copy.deepcopy(scenario)
    cloned.name = f"{scenario.name}-determinism-check"
    cloned.steps = []
    cloned.expected = {"execution": scenario.expected.get("execution", {}), "determinism": {}}
    return cloned


def _normalize_trace(trace: Any) -> str:
    if not isinstance(trace, list):
        return json.dumps(trace, sort_keys=True, default=str)

    cleaned: list[Any] = []
    for entry in trace:
        if isinstance(entry, dict):
            item = {
                key: value
                for key, value in entry.items()
                if key not in {"timestamp", "execution_id"}
            }
            cleaned.append(item)
        else:
            cleaned.append(entry)
    return json.dumps(cleaned, sort_keys=True, default=str)


def load_expected_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_golden_report(
    runner: ScenarioRunner,
    scenario: Scenario,
    output_dir: Path,
) -> Path:
    """Generate markdown/html/json report artifacts for golden comparison."""
    output_dir.mkdir(parents=True, exist_ok=True)
    result = runner.run(_clone_scenario_without_assertions(scenario))
    task_id = result.final.task.task_id if result.final.task else f"e2e-{scenario.name}"
    generator = ReportGenerator(runner.reader.standards_root)
    storage = generator.generate(result.final.report_data, output_dir, formats=("markdown", "html", "json"))
    return Path(storage.markdown_path)


def _clone_scenario_without_assertions(scenario: Scenario) -> Scenario:
    cloned = copy.deepcopy(scenario)
    cloned.expected = {}
    cloned.steps = []
    return cloned

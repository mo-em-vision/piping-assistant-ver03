"""Assertion helpers with trace-aware failure reporting."""

from __future__ import annotations

import json
from typing import Any

from models.execution import ExecutionStatus
from models.task import Task, TaskStatus
from models.validation import ComplianceStatus


class ScenarioAssertionError(AssertionError):
    """Failed scenario assertion with engineering trace context."""

    def __init__(
        self,
        scenario_name: str,
        component: str,
        reason: str,
        *,
        node: str | None = None,
        source: str | None = None,
        trace: Any | None = None,
    ) -> None:
        self.scenario_name = scenario_name
        self.component = component
        self.reason = reason
        self.node = node
        self.source = source
        self.trace = trace
        lines = [
            "Failure:",
            f"Scenario: {scenario_name}",
            f"Component: {component}",
            f"Reason: {reason}",
        ]
        if node:
            lines.append(f"Node: {node}")
        if source:
            lines.append(f"Source: {source}")
        if trace is not None:
            lines.append("Trace:")
            lines.append(json.dumps(trace, indent=2, default=str))
        super().__init__("\n".join(lines))


def _fail(
    scenario_name: str,
    component: str,
    reason: str,
    *,
    node: str | None = None,
    source: str | None = None,
    trace: Any | None = None,
) -> None:
    raise ScenarioAssertionError(
        scenario_name,
        component,
        reason,
        node=node,
        source=source,
        trace=trace,
    )


def assert_contains(actual: list[str], expected_items: list[str], *, scenario: str, component: str) -> None:
    missing = [item for item in expected_items if item not in actual]
    if missing:
        _fail(
            scenario,
            component,
            f"Missing expected items: {missing}",
            trace={"actual": actual, "expected": expected_items},
        )


def assert_status(actual: str, expected: str, *, scenario: str, component: str) -> None:
    normalized_actual = actual.lower().replace("_", " ")
    normalized_expected = expected.lower().replace("_", " ")
    if normalized_actual != normalized_expected:
        _fail(scenario, component, f"Expected status {expected!r}, got {actual!r}")


def assert_execution_status(actual: ExecutionStatus, expected: str, *, scenario: str) -> None:
    assert_status(actual.value, expected, scenario=scenario, component="Execution Layer")


def assert_task_status(actual: TaskStatus, expected: str, *, scenario: str) -> None:
    assert_status(actual.value, expected, scenario=scenario, component="State Manager")


def assert_compliance_status(actual: ComplianceStatus, expected: str, *, scenario: str) -> None:
    assert_status(actual.value, expected, scenario=scenario, component="Validation Layer")


def assert_output_value(
    task: Task,
    key: str,
    expected: Any,
    *,
    scenario: str,
    tolerance: float = 1e-6,
) -> None:
    actual = task.outputs.get(key)
    if isinstance(expected, dict) and expected.get("formula") in {
        "wall_thickness",
        "minimum_required_thickness",
    }:
        from tests.mvp.regression import (
            expected_minimum_required_thickness,
            expected_wall_thickness,
        )

        formula_tolerance = float(expected.get("tolerance", tolerance))
        if expected.get("formula") == "wall_thickness":
            expected_value = expected_wall_thickness(task)
            node = "304.1.2-a"
        else:
            expected_value = expected_minimum_required_thickness(task)
            node = "asme-b313-304-1-1-eq-2"
        if actual is None:
            _fail(scenario, "Execution Layer", f"Missing output {key!r}", trace=task.outputs)
        if abs(float(actual) - expected_value) > formula_tolerance:
            _fail(
                scenario,
                "Execution Layer",
                f"Output {key!r}: expected ~{expected_value}, got {actual}",
                node=node,
            )
        return

    if actual != expected:
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if abs(float(actual) - float(expected)) <= tolerance:
                return
        _fail(
            scenario,
            "Execution Layer",
            f"Output {key!r}: expected {expected!r}, got {actual!r}",
            trace=task.outputs,
        )


def assert_validation_rules(
    trace: list[dict[str, Any]],
    expected_rules: list[str],
    *,
    scenario: str,
) -> None:
    found: set[str] = set()
    for entry in trace:
        for finding in entry.get("errors", []):
            if isinstance(finding, dict) and finding.get("rule"):
                found.add(str(finding["rule"]))
    missing = [rule for rule in expected_rules if rule not in found]
    if missing:
        _fail(
            scenario,
            "Validation Layer",
            f"Expected validation rules not found: {missing}",
            trace=trace,
        )


def assert_conflict(task: Task, expected: dict[str, Any], *, scenario: str) -> None:
    for conflict in task.conflicts:
        if conflict.input_id == expected.get("input_id"):
            if expected.get("previous_value") is not None and conflict.previous_value != expected["previous_value"]:
                continue
            if expected.get("new_value") is not None and conflict.new_value != expected["new_value"]:
                continue
            return
    _fail(
        scenario,
        "State Manager",
        f"Expected input conflict not recorded: {expected}",
        trace=[vars(c) for c in task.conflicts],
    )

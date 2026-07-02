"""Validation Layer coordinator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.events.event_logger import EventLogger
from engine.reference.node_types import is_section_node
from engine.reference.standards_reader import StandardsReader
from models.event import EventType
from models.execution import ExecutionPlan
from models.fact import Fact
from models.task import Task
from models.validation import (
    ComplianceStatus,
    LayerValidationResult,
    ValidationFinding,
    ValidationOverride,
    ValidationSeverity,
)

from .conflict_validator import ConflictValidator
from .dependency_validator import DependencyValidator
from .engineering_validator import EngineeringValidator
from .input_validator import InputValidator
from .unit_validator import UnitValidator


class ValidationEngine:
    """Deterministic compliance gate before execution (doc 15)."""

    def __init__(self, reader: StandardsReader, *, events: EventLogger | None = None) -> None:
        self._reader = reader
        self._input = InputValidator()
        self._unit = UnitValidator()
        self._engineering = EngineeringValidator()
        self._dependency = DependencyValidator()
        self._conflict = ConflictValidator()
        self._events = events or EventLogger()

    def validate_plan(
        self,
        plan: ExecutionPlan,
        task: Task,
    ) -> LayerValidationResult:
        """Validate an execution plan before the Execution Layer runs."""
        results: list[LayerValidationResult] = [self._conflict.validate_task(task)]

        for node_id in plan.execution_order:
            record = self._reader.load(node_id)
            if is_section_node(record.metadata) or str(record.metadata.get("type", "")) in {"root", "definition"}:
                continue
            results.append(
                self._input.validate_node_inputs(
                    node_id,
                    reader=self._reader,
                    task_inputs=plan.inputs,
                    dependency_outputs={},
                    skip_dependency_inputs=True,
                )
            )
            results.append(
                self._unit.validate_node_inputs(
                    node_id,
                    reader=self._reader,
                    task_inputs=plan.inputs,
                )
            )
            results.append(
                self._engineering.validate_node(
                    node_id,
                    reader=self._reader,
                    task_inputs=plan.inputs,
                    overrides=self._override_rules(task),
                )
            )

        merged = _merge_results(results)
        _apply_incomplete_status(merged)

        self._log_result("execution_plan", merged, node=plan.root)
        return merged

    def validate_node(
        self,
        node_id: str,
        *,
        task_inputs: dict[str, Fact],
        dependency_outputs: dict[str, Any],
        prior_nodes_completed: set[str],
        overrides: list[str] | None = None,
    ) -> LayerValidationResult:
        """Validate whether a single node execution is allowed."""
        record = self._reader.load(node_id)
        if is_section_node(record.metadata) or str(record.metadata.get("type", "")) in {
            "root",
            "definition",
        }:
            return LayerValidationResult(status=ComplianceStatus.PASS)

        results = [
            self._input.validate_node_inputs(
                node_id,
                reader=self._reader,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
            ),
            self._unit.validate_node_inputs(
                node_id,
                reader=self._reader,
                task_inputs=task_inputs,
            ),
            self._engineering.validate_node(
                node_id,
                reader=self._reader,
                task_inputs=task_inputs,
                overrides=overrides,
            ),
            self._dependency.validate_node(
                node_id,
                reader=self._reader,
                task_inputs=task_inputs,
                dependency_outputs=dependency_outputs,
                prior_nodes_completed=prior_nodes_completed,
            ),
        ]
        merged = _merge_results(results)
        _apply_incomplete_status(merged)
        self._log_result("node_execution", merged, node=node_id)
        return merged

    @staticmethod
    def _override_rules(task: Task) -> list[str]:
        raw = task.outputs.get("validation_overrides", [])
        if isinstance(raw, list):
            return [str(item) for item in raw]
        return []

    def override_rules_for(self, task: Task) -> list[str]:
        return self._override_rules(task)

    def record_override(
        self,
        *,
        rule: str,
        user_decision: str,
        reason: str | None = None,
    ) -> ValidationOverride:
        return ValidationOverride(
            rule=rule,
            user_decision=user_decision,
            reason=reason,
            approved=True,
        )

    def _log_result(self, scope: str, result: LayerValidationResult, *, node: str | None) -> None:
        self._events.log(
            EventType.DECISION_CREATED,
            node=node,
            decision=result.status.value,
            payload={
                "scope": scope,
                "validation": asdict(result),
            },
        )

    def to_trace_entry(self, result: LayerValidationResult) -> dict[str, Any]:
        return {
            "status": result.status.value,
            "errors": [asdict(item) for item in result.errors],
            "warnings": [asdict(item) for item in result.warnings],
            "constraints": result.constraints,
            "overrides": [asdict(item) for item in result.overrides],
            "affected_nodes": result.affected_nodes,
        }


def _merge_results(results: list[LayerValidationResult]) -> LayerValidationResult:
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []
    constraints: list[str] = []
    overrides: list[ValidationOverride] = []
    affected: list[str] = []
    metadata: dict[str, Any] = {}

    statuses: list[ComplianceStatus] = []
    for result in results:
        statuses.append(result.status)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
        constraints.extend(result.constraints)
        overrides.extend(result.overrides)
        affected.extend(result.affected_nodes)
        metadata.update(result.metadata)

    if ComplianceStatus.FAIL in statuses:
        status = ComplianceStatus.FAIL
    elif ComplianceStatus.INCOMPLETE in statuses:
        status = ComplianceStatus.INCOMPLETE
    elif ComplianceStatus.PASS_WITH_WARNING in statuses or warnings:
        status = ComplianceStatus.PASS_WITH_WARNING
    else:
        status = ComplianceStatus.PASS

    return LayerValidationResult(
        status=status,
        errors=errors,
        warnings=[w for w in warnings if w.severity != ValidationSeverity.INFO],
        constraints=list(dict.fromkeys(constraints)),
        overrides=overrides,
        affected_nodes=list(dict.fromkeys(affected)),
        metadata=metadata,
    )


def _apply_incomplete_status(result: LayerValidationResult) -> None:
    if any(
        finding.rule in {"missing_input", "missing_dependency_output", "missing_assumption"}
        for finding in result.errors
    ):
        result.status = ComplianceStatus.INCOMPLETE
    elif result.errors:
        result.status = ComplianceStatus.FAIL

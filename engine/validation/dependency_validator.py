"""Dependency output availability validation."""

from __future__ import annotations

from typing import Any

from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput
from models.validation import ComplianceStatus, LayerValidationResult, ValidationFinding, ValidationSeverity


class DependencyValidator:
    """Verify required dependency outputs exist before node execution."""

    def validate_node(
        self,
        node_id: str,
        *,
        reader: StandardsReader,
        task_inputs: dict[str, EngineeringInput],
        dependency_outputs: dict[str, Any],
        prior_nodes_completed: set[str],
    ) -> LayerValidationResult:
        record = reader.load(node_id)
        errors: list[ValidationFinding] = []

        for dep_id in record.depends_on:
            if dep_id not in prior_nodes_completed and dep_id not in dependency_outputs:
                errors.append(
                    ValidationFinding(
                        rule="dependency_not_satisfied",
                        message=f"Required dependency output not available: {dep_id}",
                        severity=ValidationSeverity.ERROR,
                        node_id=node_id,
                    )
                )

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            if str(spec.get("source", "")) != "node_output":
                continue
            input_id = str(spec.get("id", ""))
            symbol = str(spec.get("name", input_id))
            if input_id in task_inputs:
                continue
            if symbol not in dependency_outputs and input_id not in dependency_outputs:
                if str(spec.get("name", "")) == "S" and "allowable_stress" in dependency_outputs:
                    continue
                if input_id == "allowable_stress" and (
                    "allowable_stress" in dependency_outputs or "S" in dependency_outputs
                ):
                    continue
                errors.append(
                    ValidationFinding(
                        rule="missing_dependency_output",
                        message=f"Node output required before execution: {input_id}",
                        severity=ValidationSeverity.ERROR,
                        input_id=input_id,
                        node_id=node_id,
                    )
                )

        status = ComplianceStatus.FAIL if errors else ComplianceStatus.PASS
        return LayerValidationResult(
            status=status,
            errors=errors,
            affected_nodes=[node_id] if errors else [],
        )

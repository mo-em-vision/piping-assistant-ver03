"""Input presence, type, and range validation."""

from __future__ import annotations

from typing import Any

from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput
from models.validation import ComplianceStatus, LayerValidationResult, ValidationFinding, ValidationSeverity


class InputValidator:
    """Validate required inputs and basic value constraints."""

    def validate_node_inputs(
        self,
        node_id: str,
        *,
        reader: StandardsReader,
        task_inputs: dict[str, EngineeringInput],
        dependency_outputs: dict[str, Any] | None = None,
        skip_dependency_inputs: bool = False,
    ) -> LayerValidationResult:
        dependency_outputs = dependency_outputs or {}
        record = reader.load(node_id)
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            if not input_id:
                continue
            required = bool(spec.get("required", True))
            source = str(spec.get("source", "user_input"))
            validation = str(spec.get("validation", ""))

            value: Any = None
            if source == "node_output":
                if skip_dependency_inputs:
                    continue
                symbol = str(spec.get("name", input_id))
                value = dependency_outputs.get(input_id) or dependency_outputs.get(symbol)
                if value is None and required:
                    errors.append(
                        ValidationFinding(
                            rule="missing_dependency_output",
                            message=f"Required node output not yet available: {input_id}",
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
                continue

            if input_id in task_inputs:
                value = task_inputs[input_id].value
            elif source == "default" and spec.get("default") is not None:
                value = spec.get("default")
                if bool(spec.get("requires_confirmation", False)):
                    warnings.append(
                        ValidationFinding(
                            rule="default_unconfirmed",
                            message=f"Default value for {input_id} should be confirmed by user.",
                            severity=ValidationSeverity.WARNING,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )

            if value is None and required:
                errors.append(
                    ValidationFinding(
                        rule="missing_input",
                        message=f"Required input missing: {input_id}",
                        severity=ValidationSeverity.ERROR,
                        input_id=input_id,
                        node_id=node_id,
                    )
                )
                continue

            if value is None:
                continue

            if validation == "positive":
                if not isinstance(value, (int, float)) or float(value) <= 0:
                    errors.append(
                        ValidationFinding(
                            rule="positive_value",
                            message=f"{input_id} must be a positive number",
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
            elif validation == "non_empty":
                if not str(value).strip():
                    errors.append(
                        ValidationFinding(
                            rule="non_empty",
                            message=f"{input_id} must not be empty",
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
            elif isinstance(value, str) and not _is_numeric_string(value) and validation not in ("non_empty",):
                errors.append(
                    ValidationFinding(
                        rule="invalid_type",
                        message=f"Unknown value for {input_id}: {value!r}",
                        severity=ValidationSeverity.ERROR,
                        input_id=input_id,
                        node_id=node_id,
                        suggestions=["Provide a numeric value with a valid unit"],
                    )
                )

        status = _status_from_findings(errors, warnings)
        if any(error.rule == "missing_input" for error in errors):
            status = ComplianceStatus.INCOMPLETE
        return LayerValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            affected_nodes=[node_id] if errors or warnings else [],
        )


def _is_numeric_string(value: str) -> bool:
    try:
        float(value.split()[0])
        return True
    except (ValueError, IndexError):
        return False


def _status_from_findings(
    errors: list[ValidationFinding],
    warnings: list[ValidationFinding],
) -> ComplianceStatus:
    if errors:
        return ComplianceStatus.FAIL
    if warnings:
        return ComplianceStatus.PASS_WITH_WARNING
    return ComplianceStatus.PASS

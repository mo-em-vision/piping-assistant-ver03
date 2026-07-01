"""Input presence, type, and range validation."""

from __future__ import annotations

from typing import Any

from engine.reference.node_types import is_section_node
from engine.reference.nomenclature_resolver import (
    enrich_input_spec,
    input_applies,
    load_nomenclature_for_node,
    spec_symbol,
    task_input_key,
)
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput, InputStatus, input_is_expansion_ready
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
        nomenclature = load_nomenclature_for_node(reader, record.metadata)
        section_node = is_section_node(record.metadata)

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            if section_node and str(spec.get("source", "")) == "node_output":
                continue
            spec = enrich_input_spec(spec, nomenclature if nomenclature else None)
            if not input_applies(spec, task_inputs):
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
                symbol = spec_symbol(spec, fallback=input_id)
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

            lookup_key = task_input_key(spec)

            if lookup_key in task_inputs:
                stored = task_inputs[lookup_key]
                if bool(spec.get("requires_confirmation", False)) and not input_is_expansion_ready(
                    stored
                ):
                    errors.append(
                        ValidationFinding(
                            rule="missing_assumption",
                            message=(
                                f"Required assumption for {input_id} must be confirmed "
                                f"before execution."
                            ),
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
                    continue
                value = stored.value
            elif source == "default" and spec.get("default") is not None:
                if bool(spec.get("requires_confirmation", False)) and required:
                    errors.append(
                        ValidationFinding(
                            rule="missing_assumption",
                            message=(
                                f"Default value for {input_id} must be confirmed "
                                f"before execution."
                            ),
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
                    continue
                value = spec.get("default")

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
        if any(error.rule in {"missing_input", "missing_assumption"} for error in errors):
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

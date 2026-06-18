"""Unit compatibility and conversion validation."""

from __future__ import annotations

from engine.executor.unit_manager import convert_to_si, normalize_unit
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput
from models.validation import ComplianceStatus, LayerValidationResult, ValidationFinding, ValidationSeverity


_SUPPORTED_UNITS = {
    "pa",
    "bar",
    "psi",
    "mm",
    "in",
    "f",
    "c",
    "k",
    "degf",
    "degc",
    "dimensionless",
    "1",
    "",
}


class UnitValidator:
    """Validate units against node metadata and conversion requirements."""

    def validate_node_inputs(
        self,
        node_id: str,
        *,
        reader: StandardsReader,
        task_inputs: dict[str, EngineeringInput],
    ) -> LayerValidationResult:
        record = reader.load(node_id)
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            input_id = str(spec.get("id", ""))
            if input_id not in task_inputs:
                continue

            engineering_input = task_inputs[input_id]
            allowed = spec.get("allowed_units") or [spec.get("unit", "")]
            allowed_normalized = {normalize_unit(str(u)) for u in allowed if u}
            unit = normalize_unit(engineering_input.unit)

            if allowed_normalized and unit not in allowed_normalized:
                convertible = _can_convert(unit, allowed_normalized)
                if not convertible:
                    errors.append(
                        ValidationFinding(
                            rule="unit_incompatible",
                            message=(
                                f"Unit '{engineering_input.unit}' is not allowed for {input_id}. "
                                f"Allowed: {', '.join(sorted(allowed_normalized))}"
                            ),
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )
                else:
                    warnings.append(
                        ValidationFinding(
                            rule="unit_converted",
                            message=f"{input_id} will be converted from {engineering_input.unit} for calculation.",
                            severity=ValidationSeverity.INFO,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )

            if isinstance(engineering_input.value, (int, float)):
                try:
                    convert_to_si(float(engineering_input.value), engineering_input.unit)
                except (ValueError, TypeError) as exc:
                    errors.append(
                        ValidationFinding(
                            rule="unit_conversion",
                            message=str(exc),
                            severity=ValidationSeverity.ERROR,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )

        status = ComplianceStatus.FAIL if errors else (
            ComplianceStatus.PASS_WITH_WARNING if warnings else ComplianceStatus.PASS
        )
        return LayerValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            affected_nodes=[node_id] if errors or warnings else [],
        )


def _can_convert(unit: str, allowed: set[str]) -> bool:
    if unit in _SUPPORTED_UNITS:
        return True
    for target in allowed:
        if target in _SUPPORTED_UNITS:
            return True
    return False

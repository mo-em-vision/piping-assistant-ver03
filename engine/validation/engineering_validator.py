"""Engineering limits and node rule validation."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import (
    evaluate_node_execution_assumptions,
    evaluate_node_expansion_assumptions,
)
from engine.executor.unit_manager import convert_to_si
from engine.reference.material_catalog_db import standards_root_from_pack_root
from engine.reference.material_resolver import resolve_material_table_key
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput
from models.validation import ComplianceStatus, LayerValidationResult, ValidationFinding, ValidationSeverity


class EngineeringValidator:
    """Validate engineering constraints from node limitations and tables."""

    def validate_node(
        self,
        node_id: str,
        *,
        reader: StandardsReader,
        task_inputs: dict[str, EngineeringInput],
        overrides: list[str] | None = None,
    ) -> LayerValidationResult:
        record = reader.load(node_id)
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []
        constraints: list[str] = []
        overrides = overrides or []

        for item in record.metadata.get("limitations", []) or []:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("id", "limitation"))
            condition = str(item.get("condition", ""))
            action = str(item.get("action", "warning"))
            if condition:
                constraints.append(condition)
            if action == "warning" and rule_id not in overrides:
                warnings.append(
                    ValidationFinding(
                        rule=rule_id,
                        message=condition or f"Limitation {rule_id} applies",
                        severity=ValidationSeverity.WARNING,
                        node_id=node_id,
                        source=str(record.metadata.get("paragraph", "")),
                    )
                )

        if node_id == "B313-material-stress":
            table_result = self._validate_table_temperature(reader, task_inputs, overrides)
            errors.extend(table_result.errors)
            warnings.extend(table_result.warnings)
            constraints.extend(table_result.constraints)

        node_type = str(record.metadata.get("type", ""))
        if node_type in {"calculation", "lookup"}:
            for evaluation in (
                evaluate_node_expansion_assumptions(record, existing_inputs=task_inputs),
                evaluate_node_execution_assumptions(record, existing_inputs=task_inputs),
            ):
                assumption_result = self._assumption_findings(record, evaluation)
                errors.extend(assumption_result.errors)
                warnings.extend(assumption_result.warnings)

        status = ComplianceStatus.FAIL if errors else (
            ComplianceStatus.PASS_WITH_WARNING if warnings else ComplianceStatus.PASS
        )
        return LayerValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            constraints=constraints,
            affected_nodes=[node_id] if errors or warnings else [],
        )

    def _assumption_findings(
        self,
        record,
        evaluation,
    ) -> LayerValidationResult:
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []

        for block in evaluation.blocked:
            errors.append(
                ValidationFinding(
                    rule=block.assumption_id,
                    message=block.message,
                    severity=ValidationSeverity.ERROR,
                    input_id=block.field,
                    node_id=block.node_id,
                    source=str(record.metadata.get("paragraph", "")),
                )
            )

        for field_id in evaluation.missing_fields:
            errors.append(
                ValidationFinding(
                    rule="missing_assumption",
                    message=(
                        f"Required assumption field '{field_id}' must be confirmed "
                        f"before executing {record.node_id}."
                    ),
                    severity=ValidationSeverity.ERROR,
                    input_id=field_id,
                    node_id=record.node_id,
                )
            )

        status = ComplianceStatus.FAIL if errors else ComplianceStatus.PASS
        return LayerValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            affected_nodes=[record.node_id] if errors else [],
        )

    def _validate_table_temperature(
        self,
        reader: StandardsReader,
        task_inputs: dict[str, EngineeringInput],
        overrides: list[str],
    ) -> LayerValidationResult:
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []
        constraints: list[str] = []

        if "design_temperature" not in task_inputs or "material" not in task_inputs:
            return LayerValidationResult(status=ComplianceStatus.PASS)

        if "temperature_table_bounds" in overrides:
            return LayerValidationResult(status=ComplianceStatus.PASS_WITH_WARNING)

        inp = task_inputs["design_temperature"]
        material = str(task_inputs["material"].value)
        if not isinstance(inp.value, (int, float)):
            return LayerValidationResult(status=ComplianceStatus.PASS)

        temp_f, _ = convert_to_si(float(inp.value), inp.unit, target_unit="f")
        try:
            table_data = reader.load_table("A-1")
        except FileNotFoundError:
            return LayerValidationResult(status=ComplianceStatus.PASS)
        material_key = resolve_material_table_key(
            table_data.get("materials", {}) or {},
            material,
            standards_root=standards_root_from_pack_root(reader.pack_root),
        )
        if material_key is None:
            errors.append(
                ValidationFinding(
                    rule="material_not_in_table",
                    message=f"Material not found in allowable stress table: {material}",
                    severity=ValidationSeverity.ERROR,
                    input_id="material",
                    node_id="B313-material-stress",
                )
            )
            return LayerValidationResult(
                status=ComplianceStatus.FAIL,
                errors=errors,
                affected_nodes=["B313-material-stress"],
            )

        rows = table_data.get("materials", {}).get(material_key, {}).get("rows", [])
        if not rows:
            return LayerValidationResult(status=ComplianceStatus.PASS)

        temps = [float(row["design_temperature"]) for row in rows]
        min_t, max_t = min(temps), max(temps)
        constraints.append(f"Table temperature range: {min_t}–{max_t} °F")

        if temp_f < min_t or temp_f > max_t:
            if "temperature_table_bounds" in overrides:
                warnings.append(
                    ValidationFinding(
                        rule="temperature_table_bounds",
                        message=(
                            f"Design temperature {temp_f}°F is outside table range "
                            f"({min_t}–{max_t}°F); user override accepted."
                        ),
                        severity=ValidationSeverity.WARNING,
                        input_id="design_temperature",
                        node_id="B313-material-stress",
                    )
                )
            else:
                errors.append(
                    ValidationFinding(
                        rule="temperature_table_bounds",
                        message=(
                            f"Design temperature {temp_f}°F exceeds table range "
                            f"({min_t}–{max_t}°F)."
                        ),
                        severity=ValidationSeverity.ERROR,
                        input_id="design_temperature",
                        node_id="B313-material-stress",
                    )
                )

        status = ComplianceStatus.FAIL if errors else (
            ComplianceStatus.PASS_WITH_WARNING if warnings else ComplianceStatus.PASS
        )
        return LayerValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            constraints=constraints,
        )

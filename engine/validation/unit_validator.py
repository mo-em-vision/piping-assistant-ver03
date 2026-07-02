"""Unit compatibility and conversion validation."""

from __future__ import annotations

from engine.executor.unit_manager import convert_to_si, normalize_unit
from engine.reference.relationship_taxonomy import PARAMETER_CONCEPT_TRAVERSAL_TYPES
from engine.reference.node_types import is_section_node
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact, fact_scalar_value, fact_unit
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


def validate_task_input_units(
    reader: StandardsReader,
    task_inputs: dict[str, Fact],
) -> LayerValidationResult:
    """Validate task inputs against micro-graph parameter unit metadata."""
    from engine.units.unit_registry import get_unit_registry

    store = reader.graph_store
    errors: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []
    registry = get_unit_registry()

    if not store.available:
        return LayerValidationResult(
            status=ComplianceStatus.PASS,
            errors=[],
            warnings=[],
            affected_nodes=[],
        )

    for node in store.list_nodes(node_type="parameter"):
        input_id = str(node.metadata.get("input_id", "")).strip()
        if not input_id or input_id not in task_inputs:
            continue

        fact = task_inputs[input_id]
        _, dimension, is_designation = _parameter_concept_for_validation(
            store,
            node.node_id,
        )
        allowed_symbols = registry.resolve_allowed_unit_symbols(
            param_meta=node.metadata,
            quantity_dimension=dimension,
            is_designation=is_designation,
        )
        if not allowed_symbols:
            continue

        unit = normalize_unit(fact_unit(fact))
        if unit not in allowed_symbols:
            convertible = _can_convert(unit, allowed_symbols)
            if not convertible:
                errors.append(
                    ValidationFinding(
                        rule="unit_incompatible",
                        message=(
                            f"Unit '{fact_unit(fact)}' is not allowed for {input_id}. "
                            f"Allowed: {', '.join(sorted(allowed_symbols))}"
                        ),
                        severity=ValidationSeverity.ERROR,
                        input_id=input_id,
                        node_id=node.node_id,
                    )
                )
            else:
                warnings.append(
                    ValidationFinding(
                        rule="unit_converted",
                        message=(
                            f"{input_id} will be converted from {fact_unit(fact)} "
                            "for calculation."
                        ),
                        severity=ValidationSeverity.INFO,
                        input_id=input_id,
                        node_id=node.node_id,
                    )
                )

        scalar = fact_scalar_value(fact)
        if isinstance(scalar, (int, float)):
            try:
                convert_to_si(float(scalar), fact_unit(fact))
            except (ValueError, TypeError) as exc:
                errors.append(
                    ValidationFinding(
                        rule="unit_conversion",
                        message=str(exc),
                        severity=ValidationSeverity.ERROR,
                        input_id=input_id,
                        node_id=node.node_id,
                    )
                )

    status = ComplianceStatus.FAIL if errors else (
        ComplianceStatus.PASS_WITH_WARNING if warnings else ComplianceStatus.PASS
    )
    affected = sorted({finding.node_id for finding in errors + warnings if finding.node_id})
    return LayerValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        affected_nodes=affected,
    )


def _parameter_concept_for_validation(
    store,
    param_node_id: str,
) -> tuple[str | None, str | None, bool]:
    from engine.reference.node_types import is_designation_node, is_quantity_node

    for edge in store.outgoing(param_node_id, edge_types=PARAMETER_CONCEPT_TRAVERSAL_TYPES | {"has_dimension"}):
        ref_meta = store.metadata(edge.to_id)
        ref_type = store.node_type(edge.to_id) or ""
        if is_quantity_node(ref_meta, ref_type):
            dimension = str(ref_meta.get("dimension", "")).strip() or None
            return edge.to_id, dimension, False
        if is_designation_node(ref_meta, ref_type):
            return edge.to_id, None, True
    return None, None, False


class UnitValidator:
    """Validate units against node metadata and conversion requirements."""

    def validate_node_inputs(
        self,
        node_id: str,
        *,
        reader: StandardsReader,
        task_inputs: dict[str, Fact],
    ) -> LayerValidationResult:
        record = reader.load(node_id)
        errors: list[ValidationFinding] = []
        warnings: list[ValidationFinding] = []
        section_node = is_section_node(record.metadata)

        for spec in record.metadata.get("inputs", []) or []:
            if not isinstance(spec, dict):
                continue
            if section_node and str(spec.get("source", "")) == "node_output":
                continue
            input_id = str(spec.get("id", ""))
            if input_id not in task_inputs:
                continue

            fact = task_inputs[input_id]
            allowed = spec.get("allowed_units") or [spec.get("unit", "")]
            allowed_normalized = {normalize_unit(str(u)) for u in allowed if u}
            unit = normalize_unit(fact_unit(fact))

            if allowed_normalized and unit not in allowed_normalized:
                convertible = _can_convert(unit, allowed_normalized)
                if not convertible:
                    errors.append(
                        ValidationFinding(
                            rule="unit_incompatible",
                            message=(
                                f"Unit '{fact_unit(fact)}' is not allowed for {input_id}. "
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
                            message=f"{input_id} will be converted from {fact_unit(fact)} for calculation.",
                            severity=ValidationSeverity.INFO,
                            input_id=input_id,
                            node_id=node_id,
                        )
                    )

            scalar = fact_scalar_value(fact)
            if isinstance(scalar, (int, float)):
                try:
                    convert_to_si(float(scalar), fact_unit(fact))
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
    try:
        from engine.units.unit_resolver import get_unit_resolver

        resolver = get_unit_resolver()
        from_id = resolver.resolve_unit_id(unit)
        if from_id is None:
            return False
        for target in allowed:
            to_id = resolver.resolve_unit_id(target)
            if to_id is None:
                continue
            try:
                resolver.convert_value(1.0, from_id, to_id)
                return True
            except ValueError:
                continue
        return False
    except (OSError, ImportError):
        pass

    if unit in _SUPPORTED_UNITS:
        return True
    for target in allowed:
        if target in _SUPPORTED_UNITS:
            return True
    return False

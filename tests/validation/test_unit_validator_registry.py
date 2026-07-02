"""Unit validation against micro-graph parameter registry."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_reader import StandardsReader
from engine.validation.unit_validator import validate_task_input_units
from models.validation import ComplianceStatus
from tests.helpers.facts import facts_from_inputs, legacy_input


def test_validate_task_input_units_uses_registry_for_pressure() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    result = validate_task_input_units(
        reader,
        facts_from_inputs(
            {"design_pressure": legacy_input("design_pressure", 500, "psi")},
            task_id="unit-registry-pressure",
        ),
    )
    assert result.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}


def test_validate_task_input_units_rejects_incompatible_unit() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    result = validate_task_input_units(
        reader,
        facts_from_inputs(
            {"design_pressure": legacy_input("design_pressure", 100, "mm")},
            task_id="unit-registry-incompatible",
        ),
    )
    assert result.status == ComplianceStatus.FAIL
    assert any(finding.rule == "unit_incompatible" for finding in result.errors)

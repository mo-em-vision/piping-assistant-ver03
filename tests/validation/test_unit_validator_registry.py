"""Unit validation against micro-graph parameter registry."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_reader import StandardsReader
from engine.validation.unit_validator import validate_task_input_units
from models.input import EngineeringInput, InputSource, InputStatus
from models.validation import ComplianceStatus


def test_validate_task_input_units_uses_registry_for_pressure() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    result = validate_task_input_units(
        reader,
        {
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=500,
                unit="psi",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
    )
    assert result.status in {ComplianceStatus.PASS, ComplianceStatus.PASS_WITH_WARNING}


def test_validate_task_input_units_rejects_incompatible_unit() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    result = validate_task_input_units(
        reader,
        {
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=100,
                unit="mm",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
    )
    assert result.status == ComplianceStatus.FAIL
    assert any(finding.rule == "unit_incompatible" for finding in result.errors)

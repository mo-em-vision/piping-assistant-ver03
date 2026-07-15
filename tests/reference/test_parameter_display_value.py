"""Tests for parameter display value formatting without direct table lookup."""

from __future__ import annotations

from pathlib import Path

from engine.reference.parameter_display_value import resolve_parameter_display_value
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import facts_from_legacy_inputs
from models.fact import FactClass, FactProvenance, FactSource, SourceType, ValidationStatus, build_numeric_fact
from models.input import InputSource, InputStatus
from tests.helpers.facts import legacy_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_outside_diameter_display_uses_fact_not_table_lookup() -> None:
    reader = _reader()
    store = facts_from_legacy_inputs(
        {
            "outside_diameter__resolution_branch": legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "nominal_pipe_size": legacy_input(
                "nominal_pipe_size",
                "2",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="display-od",
    )
    store.upsert_active(
        build_numeric_fact(
            key="outside_diameter",
            parameter="outside_diameter",
            amount=60.33,
            unit="mm",
            fact_class=FactClass.LOOKED_UP,
            source=FactSource(
                source_type=SourceType.TABLE_LOOKUP,
                source_id="B3610-table-2-1:by_nps",
                lookup_node="asme-b3610-nps-outside-diameter-lookup",
            ),
            provenance=FactProvenance(task_id="display-od", created_by="lookup"),
            validation_status=ValidationStatus.CONFIRMED,
        )
    )
    task_inputs = store.active_facts()
    display = resolve_parameter_display_value(reader, "outside_diameter", task_inputs)
    assert display is not None
    assert "60.33 mm" in display
    assert "NPS 2" in display

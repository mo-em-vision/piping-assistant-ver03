"""Tests for graph-driven parameter value reference resolution."""

from __future__ import annotations

from engine.reference.parameter_value_source import (
    build_value_provenance,
    resolve_input_value_reference,
    resolve_parameter_value_reference,
)
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def test_build_value_provenance_equation_output_pending(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-prov-t", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]

    provenance = build_value_provenance(
        standards_reader,
        "PARAM-required-wall-thickness",
        task,
        display_value="",
    )
    assert provenance["source_type"] == "equation_output"
    assert provenance["status"] == "pending_derived"
    assert provenance["label"] == "Defined in"


def test_required_wall_thickness_references_internal_pressure_paragraph(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-t", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-required-wall-thickness",
        task,
    )
    assert reference is not None
    assert reference["node_id"] == "304.1.2-a"
    assert reference["label"] == "ASME B31.3 §304.1.2"


def test_corrosion_allowance_has_no_value_reference(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-c", status=TaskStatus.AWAITING_INPUT)

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-corrosion-allowance",
        task,
    )
    assert reference is None


def test_resolve_input_value_reference_for_required_wall_thickness(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-input", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["304.1.2-a"]

    reference = resolve_input_value_reference(
        standards_reader,
        "required_wall_thickness",
        task,
    )
    assert reference is not None
    assert reference["label"] == "ASME B31.3 §304.1.2"
    assert reference.get("reference_kind") != "table"


def test_allowable_stress_value_reference_opens_table(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-s", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-A-1", "304.1.2-a"]

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-allowable-stress",
        task,
    )
    assert reference is not None
    assert reference["label"].startswith("ASME B31.3 Table A-1")
    assert reference["reference_kind"] == "table"
    assert reference["node_id"] == "asme_b31.3_A-1"
    assert standards_reader.tables_database.resolve_table_id(reference["node_id"]) is not None


def test_basic_casting_quality_factor_value_reference_opens_table(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-ec", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-A-2", "302.3.3-a"]

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-basic-casting-quality-factor",
        task,
    )
    assert reference is not None
    assert reference["label"].startswith("ASME B31.3 Table A-2")
    assert reference["reference_kind"] == "table"
    assert reference["node_id"] == "asme_b31.3_A-2"


def test_longitudinal_weld_joint_quality_factor_value_reference_opens_table(
    standards_reader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-ej", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-A-3", "304.1.2-a"]

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes",
        task,
    )
    assert reference is not None
    assert reference["label"].startswith("ASME B31.3 Table A-3")
    assert reference["reference_kind"] == "table"
    assert reference["node_id"] == "asme_b31.3_A-3"


def test_temperature_coefficient_value_reference_opens_table(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("value-ref-y", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-304-1-1-1", "304.1.2-a"]

    reference = resolve_parameter_value_reference(
        standards_reader,
        "PARAM-temperature-coefficient-y",
        task,
    )
    assert reference is not None
    assert reference["label"].startswith("ASME B31.3 Table 304.1.1-1")
    assert reference["reference_kind"] == "table"
    assert reference["node_id"] == "asme_b31.3_table_304_1_1_1"

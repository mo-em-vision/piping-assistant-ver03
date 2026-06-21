"""Node schema validation for active MVP workflow nodes."""

from __future__ import annotations

import pytest

from engine.reference.standards_reader import StandardsReader
from tests.acceptance.helpers import confirmed_default_inputs, internal_pressure_assumption


ROOT_NODES = ("pipe_wall_thickness_design",)
CALCULATION_NODES = ("B313-304.1.2",)
LOOKUP_NODES = ("B313-material-stress",)

REQUIRED_CALCULATION_FIELDS = (
    "id",
    "inputs",
    "outputs",
    "depends_on",
    "conditions",
    "report",
)

REQUIRED_LOOKUP_FIELDS = (
    "id",
    "inputs",
    "outputs",
    "depends_on",
    "report",
)


@pytest.mark.parametrize("node_id", ROOT_NODES)
def test_root_node_schema(node_id: str, standards_reader: StandardsReader) -> None:
    result = standards_reader.validate(node_id)
    assert result.passed, f"Node {node_id} failed validation: {[issue.message for issue in result.issues]}"

    metadata = standards_reader.load(node_id).metadata
    for field in ("id", "type", "depends_on", "report"):
        assert field in metadata, f"Root node {node_id} missing required field: {field}"


@pytest.mark.parametrize("node_id", CALCULATION_NODES)
def test_calculation_node_schema(node_id: str, standards_reader: StandardsReader) -> None:
    result = standards_reader.validate(node_id)
    assert result.passed, f"Node {node_id} failed validation: {[issue.message for issue in result.issues]}"

    metadata = standards_reader.load(node_id).metadata
    for field in REQUIRED_CALCULATION_FIELDS:
        assert field in metadata, f"Node {node_id} missing required field: {field}"


@pytest.mark.parametrize("node_id", LOOKUP_NODES)
def test_lookup_node_schema(node_id: str, standards_reader: StandardsReader) -> None:
    result = standards_reader.validate(node_id)
    assert result.passed, f"Node {node_id} failed validation: {[issue.message for issue in result.issues]}"

    metadata = standards_reader.load(node_id).metadata
    for field in REQUIRED_LOOKUP_FIELDS:
        assert field in metadata, f"Node {node_id} missing required field: {field}"


@pytest.mark.parametrize("node_id", ("B313-material-stress", "B313-304.1.2"))
def test_calculation_nodes_have_formula_or_lookup(node_id: str, standards_reader: StandardsReader) -> None:
    record = standards_reader.load(node_id)
    node_type = record.metadata.get("type")
    if node_type == "calculation":
        assert record.metadata.get("equations") or record.metadata.get("formulas"), (
            f"{node_id} missing equations"
        )
    if node_type == "lookup":
        assert record.metadata.get("lookups"), f"{node_id} missing lookups"


def test_graph_trace_structure_after_execution(standards_reader, state_manager) -> None:
    from engine.executor.executor import execute_workflow
    from models.input import EngineeringInput, InputSource, InputStatus

    task_id = "schema-trace"
    state_manager.create_task(task_id)
    inputs = {
        "pressure_loading": internal_pressure_assumption(),
        **confirmed_default_inputs(),
        "d_input_mode": EngineeringInput(
            "d_input_mode", "direct_od", "dimensionless", InputSource.USER, status=InputStatus.CONFIRMED
        ),
        "design_pressure": EngineeringInput("design_pressure", 500, "psi", InputSource.USER),
        "outside_diameter": EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
        "material": EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
        "design_temperature": EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    }
    for engineering_input in inputs.values():
        state_manager.store_input(task_id, engineering_input)

    execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    trace = state_manager.get_task(task_id).outputs.get("_execution_trace", [])

    assert trace
    for entry in trace:
        assert "node_id" in entry
        assert "status" in entry
        assert "trace" in entry

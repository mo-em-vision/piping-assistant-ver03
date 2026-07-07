"""Parameter registry seeding tests for GraphEngine."""

from __future__ import annotations

from engine.graph.lazy_expander import expand_workflow
from engine.reference.node_types import is_ui_parameter
from models.input import ParameterDescriptor
from tests.graph.conftest import PIPE_WALL_ROOT, gate_open_inputs


def test_parameter_registry_not_seeded_before_gate(b313_reader, graph_engine) -> None:
    registry = graph_engine.seed_parameter_registry(
        PIPE_WALL_ROOT,
        b313_reader,
        existing_inputs={},
    )
    assert registry == {}


def test_parameter_registry_not_seeded_with_partial_gate(b313_reader, graph_engine) -> None:
    from tests.acceptance.helpers import straight_section_assumption
    from tests.helpers.facts import facts_from_inputs

    inputs = facts_from_inputs(
        {"straight_pipe_section": straight_section_assumption()},
        task_id="partial-registry",
    )
    registry = graph_engine.seed_parameter_registry(
        PIPE_WALL_ROOT,
        b313_reader,
        existing_inputs=inputs,
    )
    assert registry == {}


def test_parameter_registry_uses_micro_graph_path(b313_reader, graph_engine) -> None:
    assert graph_engine.uses_micro_graph(b313_reader, PIPE_WALL_ROOT)


def test_parameter_registry_seeded_after_gate_from_active_param_nodes(
    b313_reader, graph_engine
) -> None:
    inputs = gate_open_inputs(task_id="registry-test")
    registry = graph_engine.seed_parameter_registry(
        PIPE_WALL_ROOT,
        b313_reader,
        existing_inputs=inputs,
    )
    assert registry
    assert all(isinstance(descriptor, ParameterDescriptor) for descriptor in registry.values())
    assert "material_grade" in registry or "internal_design_gage_pressure" in registry

    micro = graph_engine._micro_engine(b313_reader)
    assert micro is not None
    resolved = graph_engine._resolve_micro_root(PIPE_WALL_ROOT, b313_reader)
    expansion = expand_workflow(micro.store, resolved, inputs, lazy=False)

    expected_keys: set[str] = set()
    for node_id in expansion.active_nodes:
        node = micro.store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            continue
        input_id = str(node.metadata.get("input_id") or node.metadata.get("key") or "").strip()
        if input_id:
            expected_keys.add(input_id)

    assert set(registry.keys()) == expected_keys
    for input_id, descriptor in registry.items():
        assert descriptor.input_id == input_id
        assert descriptor.input_id in expected_keys

    material = registry.get("material_grade")
    assert material is not None
    assert material.symbol == "material"
    assert material.description == "Material Grade"
    assert material.introduced_at_node == "asme-b313-304-1-1-b"

    pressure = registry.get("internal_design_gage_pressure")
    assert pressure is not None
    assert pressure.symbol == "P"
    assert pressure.unit == "Pa"


def test_parameter_registry_not_canonical_legacy_nomenclature_only(
    b313_reader, graph_engine
) -> None:
    registry = graph_engine.seed_parameter_registry(
        PIPE_WALL_ROOT,
        b313_reader,
        existing_inputs=gate_open_inputs(task_id="not-legacy"),
    )
    assert registry
    # Micro-graph seeding traces to PARAM nodes (or their defined_in), not solely B313-304.1.1.
    assert any(
        descriptor.introduced_at_node.startswith("PARAM-")
        or not descriptor.introduced_at_node.startswith("B313-304.1.1")
        for descriptor in registry.values()
    )

"""Parameter collection priority resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_store import GraphStore
from engine.graph.param_priority import (
    normalize_require_ids,
    parameter_collection_priority,
    parameter_defined_in,
    require_target_id,
)
from engine.graph.relationship_resolver import resolve_priority_target
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_normalize_require_ids_accepts_dict_entries() -> None:
    requires = [
        {"node_id": "B313-param-t", "priority": 85},
        "B313-param-c",
        {"id": "B313-param-P", "priority": 40},
    ]
    assert normalize_require_ids(requires) == [
        "B313-param-t",
        "B313-param-c",
        "B313-param-P",
    ]


def test_require_target_id_aliases() -> None:
    assert require_target_id({"to": "B313-param-D"}) == "B313-param-D"
    assert require_target_id({"id": "B313-param-Y"}) == "B313-param-Y"
    assert require_target_id({"parameter": "PARAM-corrosion-allowance"}) == "PARAM-corrosion-allowance"


@pytest.fixture
def b313_store() -> GraphStore:
    reader = _reader()
    store = GraphStore(reader.pack_root)
    if not store.available:
        pytest.skip("No micro-graph nodes found under pack/nodes/")
    return store


def test_equation_requires_priority_used_for_direct_inputs(b313_store: GraphStore) -> None:
    active = {"B313-eq-wall-thickness", "B313-param-P"}
    assert parameter_collection_priority(b313_store, "B313-param-P", active) == 40
    assert "priority" not in b313_store.metadata("B313-param-P")


def test_lookup_keys_use_default_priority_without_equation_requires(b313_store: GraphStore) -> None:
    active = {"B313-lookup-allowable-stress", "B313-param-material"}
    assert parameter_collection_priority(b313_store, "B313-param-material", active) == 100
    assert "priority" not in b313_store.metadata("B313-param-material")


def test_equation_priority_wins_over_lookup_on_same_active_path(b313_store: GraphStore) -> None:
    active = {"B313-eq-wall-thickness", "B313-lookup-allowable-stress", "B313-param-P"}
    assert parameter_collection_priority(b313_store, "B313-param-P", active) == 40


def test_min_priority_when_multiple_equations_require_param(b313_store: GraphStore) -> None:
    active = {"B313-eq-wall-thickness", "B313-eq-mawp", "B313-param-D"}
    assert parameter_collection_priority(b313_store, "B313-param-D", active) == 50


def test_eq2_requires_have_priorities(b313_store: GraphStore) -> None:
    reader = _reader()
    record = reader.load("B313-eq-2")
    requires = record.metadata.get("requires") or []
    resolved = [resolve_priority_target(b313_store, item) for item in requires]
    assert resolved == ["B313-param-t", "B313-param-c"]
    priorities = [item["priority"] for item in requires if isinstance(item, dict)]
    assert priorities == [85, 90]


def test_parameter_defined_in_from_yaml(b313_store: GraphStore) -> None:
    meta = b313_store.metadata("B313-param-P")
    assert parameter_defined_in(meta) == ("304.1.1-b",)
    assert "priority" not in meta

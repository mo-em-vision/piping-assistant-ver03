"""Tests for global engineering concept ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.graph_edge_schema import edge_targets
from engine.reference.standards_markdown import split_frontmatter

_FORBIDDEN_FIELDS = frozenset(
    {
        "value",
        "unit",
        "source",
        "timestamp",
        "execution_id",
        "workflow_id",
        "project_id",
        "resolution",
        "formula",
        "calculation_result",
    }
)

_PHYSICAL_CLASSES = frozenset({"physical_quantity", "geometric_quantity"})


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _concepts_dir() -> Path:
    return _project_root() / "knowledge" / "global" / "concepts" / "nodes"


def test_concept_nodes_have_required_fields() -> None:
    for path in sorted(_concepts_dir().glob("CONCEPT-*.yaml")):
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "concept"
        assert str(meta["id"]).startswith("CONCEPT-")
        assert meta.get("key")
        assert meta.get("name")
        assert meta.get("concept_class")
        assert meta.get("description")
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r}"


def test_physical_concepts_reference_dimensions() -> None:
    for path in sorted(_concepts_dir().glob("CONCEPT-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        concept_class = str(meta.get("concept_class", "")).strip()
        if concept_class not in _PHYSICAL_CLASSES:
            continue
        dimension = meta.get("dimension")
        assert dimension and str(dimension).startswith("DIM-"), path.name
        assert edge_targets(meta, "has_dimension") == [str(dimension)]


def test_categorical_material_concept_has_no_dimension() -> None:
    path = _concepts_dir() / "CONCEPT-material.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("concept_class") == "material"
    assert meta.get("dimension") in {None, "null"}
    assert edge_targets(meta, "has_dimension") == []
    assert edge_targets(meta, "has_parameter") == ["PARAM-material-specification"]


def test_concept_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "global" / "concepts"
    graph = GraphBuilder(pack_root).build()
    expected = {
        "CONCEPT-pressure",
        "CONCEPT-wall-thickness",
        "CONCEPT-material",
        "CONCEPT-temperature",
        "CONCEPT-allowable-stress",
    }
    assert expected <= set(graph.nodes.keys())
    pressure = graph.nodes["CONCEPT-pressure"]
    assert pressure.node_type == "concept"
    assert pressure.metadata.get("concept_class") == "physical_quantity"
    assert pressure.metadata.get("dimension") == "DIM-pressure"
    has_param = [
        edge
        for edge in graph.edges
        if edge.from_id == "CONCEPT-pressure" and edge.edge_type == "has_parameter"
    ]
    assert len(has_param) == 0  # PARAM nodes live in a separate pack
    write_graph_cache(pack_root, graph)

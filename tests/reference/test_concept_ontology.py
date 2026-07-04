"""Tests for global engineering concept ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.graph_edge_schema import edge_targets
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.node_revision_metadata import validate_revision_metadata

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

_VALID_CONCEPT_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material",
        "fluid",
        "component",
        "condition",
        "coefficient",
        "factor",
        "selection",
        "failure_mode",
        "inspection_method",
        "authority_concept",
    }
)

_FORBIDDEN_CONCEPT_CLASSES = frozenset({"category", "categorical"})


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
        concept_class = str(meta.get("concept_class", "")).strip()
        assert concept_class in _VALID_CONCEPT_CLASSES, path.name
        assert concept_class not in _FORBIDDEN_CONCEPT_CLASSES, path.name
        assert meta.get("description")
        assert validate_revision_metadata(meta) == [], path.name
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
    assert edge_targets(meta, "has_parameter") == [
        "PARAM-material-grade",
        "PARAM-metallurgical-group",
    ]


def test_selection_concept_pipe_construction() -> None:
    path = _concepts_dir() / "CONCEPT-pipe-construction.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("concept_class") == "selection"
    assert meta.get("dimension") in {None, "null"}
    assert edge_targets(meta, "has_dimension") == []
    assert edge_targets(meta, "has_parameter") == ["PARAM-pipe-construction-type"]
    assert "asme-b313-table-A-3" in edge_targets(meta, "used_by")


def test_factor_concept_weld_joint_efficiency() -> None:
    path = _concepts_dir() / "CONCEPT-weld-joint-efficiency.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("concept_class") == "factor"
    assert meta.get("dimension") in {None, "null"}
    assert edge_targets(meta, "has_dimension") == []
    assert edge_targets(meta, "has_parameter") == ["PARAM-weld-joint-efficiency"]
    assert "asme-b313-table-A-2" in edge_targets(meta, "used_by")
    assert "asme-b313-table-A-3" in edge_targets(meta, "used_by")


def test_coefficient_concept_temperature_coefficient() -> None:
    path = _concepts_dir() / "CONCEPT-temperature-coefficient.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("concept_class") == "coefficient"
    assert meta.get("dimension") in {None, "null"}
    assert edge_targets(meta, "has_dimension") == []
    assert edge_targets(meta, "has_parameter") == ["PARAM-temperature-coefficient-Y"]
    assert "asme-b313-table-304-1-1-1" in edge_targets(meta, "used_by")


def test_concept_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "global" / "concepts"
    graph = GraphBuilder(pack_root).build()
    expected = {
        "CONCEPT-pressure",
        "CONCEPT-wall-thickness",
        "CONCEPT-corrosion",
        "CONCEPT-pipe-diameter",
        "CONCEPT-stress",
        "CONCEPT-material",
        "CONCEPT-temperature",
        "CONCEPT-allowable-stress",
        "CONCEPT-pipe-construction",
        "CONCEPT-weld-joint-efficiency",
        "CONCEPT-temperature-coefficient",
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

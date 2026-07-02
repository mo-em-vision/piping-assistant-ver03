"""Tests for global parameter ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.graph_edge_schema import edge_targets
from engine.reference.standards_markdown import split_frontmatter

_FORBIDDEN_FIELDS = frozenset(
    {
        "value",
        "unit",
        "resolution",
        "source",
        "timestamp",
        "execution_id",
        "workflow_id",
        "status",
    }
)

_VALID_PARAMETER_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material_designation",
        "coefficient",
        "factor",
        "categorical",
        "environmental_condition",
        "calculated_quantity",
        "selection",
    }
)

_DIMENSION_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material_designation",
        "environmental_condition",
        "calculated_quantity",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parameters_dir() -> Path:
    return _project_root() / "knowledge" / "global" / "parameters" / "nodes"


def test_parameter_nodes_have_required_fields() -> None:
    paths = sorted(_parameters_dir().glob("PARAM-*.yaml"))
    assert paths, "expected at least one PARAM-*.yaml under knowledge/global/parameters/nodes"
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "parameter", path.name
        assert str(meta["id"]).startswith("PARAM-"), path.name
        assert meta.get("key"), path.name
        assert meta.get("name"), path.name
        assert meta.get("parameter_class") in _VALID_PARAMETER_CLASSES, path.name
        assert meta.get("description"), path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r}"


def test_dimensional_parameters_reference_dimensions() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        parameter_class = str(meta.get("parameter_class", "")).strip()
        if parameter_class not in _DIMENSION_CLASSES:
            continue
        dimension = meta.get("dimension")
        assert dimension and str(dimension).startswith("DIM-"), path.name
        assert edge_targets(meta, "has_dimension") == [str(dimension)]


def test_introduced_by_edges_match_top_level_list() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        top_level = meta.get("introduced_by")
        if top_level is None:
            continue
        if isinstance(top_level, str):
            expected = [top_level.strip()]
        else:
            expected = [str(item).strip() for item in top_level if str(item).strip()]
        assert edge_targets(meta, "introduced_by") == expected, path.name


def test_parameter_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "global" / "parameters"
    graph = GraphBuilder(pack_root).build()
    expected = {
        "PARAM-design-pressure",
        "PARAM-corrosion-allowance",
        "PARAM-material-specification",
        "PARAM-design-temperature",
        "PARAM-allowable-stress",
    }
    assert expected <= set(graph.nodes.keys())
    param = graph.nodes["PARAM-design-pressure"]
    assert param.node_type == "parameter"
    assert param.metadata.get("parameter_class") == "physical_quantity"
    assert param.metadata.get("dimension") == "DIM-pressure"
    has_dim = [
        edge
        for edge in graph.edges
        if edge.from_id == "PARAM-design-pressure" and edge.edge_type == "has_dimension"
    ]
    assert len(has_dim) == 0  # DIM nodes live in a separate pack
    write_graph_cache(pack_root, graph)

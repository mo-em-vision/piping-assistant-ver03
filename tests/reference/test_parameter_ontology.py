"""Tests for global parameter ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.asme_b313_node_ids import resolve_pack_node_ref
from engine.reference.graph_edge_schema import edge_targets
from engine.reference.graph_compile import compile_metadata_edges
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.parameter_node_validator import validate_parameter_node

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


def _introduced_by_targets(meta: dict) -> list[str]:
    top_level = meta.get("introduced_by")
    if top_level is None:
        return []
    if isinstance(top_level, str):
        return [top_level.strip()]
    return [str(item).strip() for item in top_level if str(item).strip()]


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
        assert validate_parameter_node(meta) == [], path.name
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


def test_parameter_nodes_have_no_introduced_by_edges() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        assert edge_targets(meta, "introduced_by") == [], path.name


def test_introduced_by_compiles_to_graph_edges() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        expected = _introduced_by_targets(meta)
        if not expected:
            continue
        node_id = str(meta["id"])
        compiled = compile_metadata_edges(node_id, meta)
        graph_targets = [edge[1] for edge in compiled if edge[2] == "introduced_by"]
        expected_resolved = [
            resolve_pack_node_ref(target) or target for target in expected
        ]
        assert graph_targets == expected_resolved, path.name


def test_pipe_construction_type_parameter_is_selection() -> None:
    path = _parameters_dir() / "PARAM-pipe-construction-type.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "selection"
    assert meta.get("key") == "pipe_construction_type"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-2-a"]
    assert "asme-b313-table-A-2" in edge_targets(meta, "used_by")
    assert "asme-b313-table-A-3" in edge_targets(meta, "used_by")


def test_material_grade_parameter_is_categorical() -> None:
    path = _parameters_dir() / "PARAM-material-grade.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "categorical"
    assert meta.get("key") == "material_grade"
    assert meta.get("dimension") == "DIM-material-designation"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-table-A-1" in edge_targets(meta, "used_by")


def test_metallurgical_group_parameter_is_selection() -> None:
    path = _parameters_dir() / "PARAM-metallurgical-group.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "selection"
    assert meta.get("key") == "metallurgical_group"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-table-304-1-1-1" in edge_targets(meta, "used_by")


def test_weld_joint_efficiency_parameter_is_factor() -> None:
    path = _parameters_dir() / "PARAM-weld-joint-efficiency.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "factor"
    assert meta.get("key") == "weld_joint_efficiency"
    assert meta.get("canonical_symbol") == "E"
    assert meta.get("dimension") == "DIM-dimensionless"
    assert edge_targets(meta, "has_dimension") == ["DIM-dimensionless"]
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-table-A-2" in edge_targets(meta, "used_by")
    assert "asme-b313-table-A-3" in edge_targets(meta, "used_by")


def test_temperature_coefficient_y_parameter_is_coefficient() -> None:
    path = _parameters_dir() / "PARAM-temperature-coefficient-Y.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "coefficient"
    assert meta.get("key") == "temperature_coefficient_Y"
    assert meta.get("canonical_symbol") == "Y"
    assert meta.get("dimension") == "DIM-dimensionless"
    assert edge_targets(meta, "has_dimension") == ["DIM-dimensionless"]
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-table-304-1-1-1" in edge_targets(meta, "used_by")


def test_weld_strength_reduction_factor_w_parameter() -> None:
    path = _parameters_dir() / "PARAM-weld-strength-reduction-factor-W.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "factor"
    assert meta.get("canonical_symbol") == "W"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-table-302-3-5-1" in edge_targets(meta, "used_by")


def test_outside_diameter_parameter() -> None:
    path = _parameters_dir() / "PARAM-outside-diameter.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "geometric_quantity"
    assert meta.get("canonical_symbol") == "D"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "B3610-table-2-1" in edge_targets(meta, "used_by")


def test_design_pressure_introduced_by_304_1_1_b() -> None:
    path = _parameters_dir() / "PARAM-design-pressure.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-304-1-2-a" in edge_targets(meta, "used_by")


def test_required_wall_thickness_parameter() -> None:
    path = _parameters_dir() / "PARAM-required-wall-thickness.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "calculated_quantity"
    assert meta.get("canonical_symbol") == "t"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-b"]
    assert "asme-b313-304-1-1-a" in edge_targets(meta, "used_by")
    assert "asme-b313-304-1-2-a" in edge_targets(meta, "used_by")
    assert "asme-b313-304-1-2-b" in edge_targets(meta, "used_by")
    assert "asme-b313-304-1-2-eq-3a" in edge_targets(meta, "used_by")


def test_minimum_required_thickness_introduced_by_304_1_1_a() -> None:
    path = _parameters_dir() / "PARAM-minimum-required-thickness.yaml"
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("parameter_class") == "calculated_quantity"
    assert meta.get("canonical_symbol") == "t_m"
    assert _introduced_by_targets(meta) == ["asme-b313-304-1-1-a"]
    assert "PARAM-required-wall-thickness" in edge_targets(meta, "related_to")
    assert "asme-b313-304-1-1-eq-2" in edge_targets(meta, "used_by")


def test_parameter_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "global" / "parameters"
    graph = GraphBuilder(pack_root).build()
    expected = {
        "PARAM-design-pressure",
        "PARAM-corrosion-allowance",
        "PARAM-material-grade",
        "PARAM-metallurgical-group",
        "PARAM-design-temperature",
        "PARAM-allowable-stress",
        "PARAM-pipe-construction-type",
        "PARAM-weld-joint-efficiency",
        "PARAM-temperature-coefficient-Y",
        "PARAM-weld-strength-reduction-factor-W",
        "PARAM-outside-diameter",
        "PARAM-required-wall-thickness",
        "PARAM-minimum-required-thickness",
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

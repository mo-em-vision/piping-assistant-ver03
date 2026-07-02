"""Tests for ASME B31.3 paragraph ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.paragraph_node_validator import validate_paragraph_node

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "selected_for_execution",
        "active_in_context",
        "nomenclature",
        "assumptions",
        "interactions",
        "trace",
        "report",
        "ai_hints",
        "subsections",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paragraph_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "paragraph"
    )


def test_paragraph_nodes_have_required_template_fields() -> None:
    paths = sorted(_paragraph_dir().glob("*.yaml"))
    assert len(paths) == 11
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "paragraph"
        assert meta.get("authority") == "AUTH-ASME-B31.3"
        assert validate_paragraph_node(meta) == [], path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r}"


def test_paragraph_sidecars_load_nomenclature() -> None:
    from engine.reference.nomenclature_resolver import load_nomenclature
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    entries = load_nomenclature(reader, "304.1.1")
    assert "c" in entries
    assert entries["c"].input_id == "corrosion_allowance"


def test_paragraph_sidecars_load_execution_metadata() -> None:
    from engine.graph.node_interaction import load_node_interactions
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("304.1.1")
    assert record.metadata.get("interactions")
    assert record.metadata.get("assumptions")
    specs = load_node_interactions(record, reader)
    variables = {spec.variable for spec in specs}
    assert "pressure_loading" in variables


def test_b31_3_pack_compiles_paragraph_nodes() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from engine.reference.graph_cache import write_graph_cache

    pack_root = _project_root() / "knowledge" / "standards" / "asme" / "asme_b31.3"
    graph = GraphBuilder(pack_root).build()
    for node_id in ("304.1.1", "304.1.2", "302.3.5"):
        assert node_id in graph.nodes
        assert graph.nodes[node_id].node_type == "paragraph"
    write_graph_cache(pack_root, graph)
